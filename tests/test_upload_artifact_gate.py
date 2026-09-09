"""Behavioural tests for release.sh's `verify_upload_artifact` upload gate.

NOT RUN BY ITS AUTHOR. Written under an execution suspension and handed over
unexecuted - treat every expectation below as unverified until someone runs it.

ISOLATION
---------
The real repo script is never sourced, executed, or dispatched. Only the TEXT of
the single function under test is extracted by brace-matching from a copy, and
that fragment is sourced in a sandbox. A fragment has no `case` dispatch at all,
so this does not even depend on the source guard holding - there is nothing to
fall through to.

`ditto`, `hdiutil` and `$PY` are replaced by shims that fabricate the tree each
case needs, so nothing is extracted, mounted, signed or uploaded for real.

WHY THESE CASES
---------------
The gate's job is to refuse to upload something we cannot vouch for, and its
failure modes are all "cannot check" masquerading as "checked and fine":

* a MISSING artifact must fail, not pass - the comment in release.sh records
  that this used to `return 0`, which made "there was nothing to inspect"
  indistinguishable from "inspected and clean". That is the same shape as every
  vacuous assertion found on this release.
* a CORRUPT zip must fail rather than yield an empty tree that trivially has no
  app in it for the wrong reason.
* the DMG arm must create its mountpoint BEFORE `hdiutil attach`; without it
  attach fails and the gate reports a problem with the artifact when the problem
  is the harness.
* exactly one app AT THE ROOT: zero, two, or a nested one all mean we do not
  know what we are shipping, and picking one arbitrarily is how you ship the
  wrong bundle.
* an unknown extension must fail closed rather than skip.
"""

import ast
import hashlib
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RELEASE_SH = REPO / "release.sh"
RELEASE_VERIFIER = REPO / "verify_release_artifact.py"
APP_SOURCE = REPO / "claude_pet.py"
FUNCTION = "verify_upload_artifact"
REVIEWED_RELEASE_SHA256 = (
    "a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23"
)
REVIEWED_VERIFIER_SHA256 = (
    "7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa"
)
REVIEWED_APP_SOURCE_SHA256 = (
    "f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a"
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_reviewed_file(testcase, path, expected):
    actual = file_sha256(path)
    testcase.assertEqual(
        actual, expected,
        f"{path.name} changed after this executable harness was reviewed; "
        "refusing to run it until a verifier reviews and repins the new bytes")


def current_app_version():
    match = re.search(r'^APP_VERSION = "([^"]+)"', APP_SOURCE.read_text(), re.M)
    if not match:
        raise AssertionError("claude_pet.py has no literal APP_VERSION")
    return match.group(1)


def updater_asset_names():
    """Read UPDATE_ASSET_NAMES without importing the GUI application module."""
    tree = ast.parse(APP_SOURCE.read_text(), filename=str(APP_SOURCE))
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name)
                        and target.id == "UPDATE_ASSET_NAMES"
                        for target in node.targets)):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                break
            return value
    raise AssertionError("claude_pet.py has no literal UPDATE_ASSET_NAMES mapping")


CURRENT_APP_VERSION = current_app_version()


def extract_function(text, name):
    """Brace-match the named shell function out of the script text."""
    m = re.search(rf"^{re.escape(name)}\(\)\s*\{{", text, re.M)
    if not m:
        raise AssertionError(f"{name}() not found in release.sh")
    i, depth = m.end() - 1, 0
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1]
        i += 1
    raise AssertionError(f"unbalanced braces in {name}()")


def release_sh_asset_names():
    """The artifact basenames `release.sh` actually builds and uploads.

    Defined up here because `PublishBehaviourTests.PUBLISH_VARS` is built from
    it in a class body, which runs at import.
    """
    text = RELEASE_SH.read_text()
    out = {}
    for var in ("ZIP", "UZIP", "DMG", "UDMG"):
        m = re.search(r'^%s="([^"]+)"' % var, text, re.M)
        if m:
            out[var] = os.path.basename(m.group(1))
    return out


REAL_HOME = Path(os.path.expanduser("~"))

# Read-only sentinels. Every one of these is a path a sourced fragment could
# reach WITHOUT invoking `gh`, so they are checked after every case rather than
# trusted to the environment settings above.
SENTINELS = (REAL_HOME / "claudepet_debug.log",
             REAL_HOME / ".claude_pet.json",
             REAL_HOME / ".claude_pet",
             REAL_HOME / ".zshrc",
             REAL_HOME / ".zshenv",
             REAL_HOME / "Library" / "Caches" / "me.yeongyu.claudepet")

# Repo-root paths the build and release scripts create. These are named
# individually rather than by diffing the whole directory listing: this
# repository is worked on by several agents at once, so "a file appeared in the
# repo root" is not evidence that *this test* put it there, and an assertion
# that fires on someone else's scratch file teaches people to ignore it. Each
# path below is one only `build_app.sh` or `release.sh` writes, so a change to
# any of them means a fragment ran further than the harness intended.
REPO_ARTIFACTS = (REPO / "ClaudePet.app",
                  REPO / "build",
                  REPO / "dist",
                  REPO / "dist-universal",
                  REPO / "release" / "ClaudePet.zip",
                  REPO / "release" / "ClaudePet-universal.zip",
                  REPO / "release" / "ClaudePet.dmg",
                  REPO / "release" / "ClaudePet-universal.dmg")


def snapshot(paths):
    out = {}
    for p in paths:
        try:
            st = p.lstat()
            out[str(p)] = (True, st.st_size, st.st_mtime_ns)
        except OSError:
            out[str(p)] = (False, None, None)
    return out


class SandboxedShell(unittest.TestCase):
    """Base for every test that spawns a shell at a build or release script.

    ENVIRONMENT ISOLATION - why it is built rather than patched
    ----------------------------------------------------------
    An earlier revision isolated `PATH` and the `gh` credentials: it hardened
    the tool that was *expected* to be dangerous. That is the wrong shape. The
    fragments under test are shell, sourced into a real `zsh`, and the
    environment carries several other routes into the user's state that no
    tool-by-tool allow-list covers:

      HOME    - a helper on a failure path appends to `~/claudepet_debug.log`.
      TMPDIR  - `mktemp -d` inside the gate; extractions and mounts land
                wherever the ambient value points.
      ZDOTDIR - `zsh` would otherwise source the user's real startup files into
                the shell running the fragment. `-f` is passed as well, and the
                two are not redundant: `-f` is an argument a future call site
                can forget, while `ZDOTDIR` travels with the environment.
      CDPATH  - an ambient value silently redirects a bare `cd` inside a
                sourced fragment to a directory nobody chose. `release.sh` and
                `build_app.sh` both open with `cd "$(dirname "$0")"`.

    So the environment is **constructed from an allow-list**, not copied from
    `os.environ` and amended. Copy-and-amend protects against the variables
    someone thought of; building from nothing protects against the rest, and
    an unexpected variable becomes a visible failure instead of a silent
    inheritance.

    `SENTINELS` and `REPO_ARTIFACTS` then check the outcome directly after
    every test, because a setting that is merely believed to be correct is not
    evidence - and because the two failures this repository actually suffered
    (a sourced script running its dispatch, a bare invocation defaulting to
    `all`) both showed up as a *build artifact appearing*, which no environment
    variable would have prevented.

    This class lives in a test module rather than a helper module of its own
    because AGENTS.md 4 limits new files to the deliverables an assignment
    names; `tests/test_release_gate.py` imports it from here so that the two
    suites cannot drift into two different ideas of what "sandboxed" means.
    """

    #: Subclasses that need more (a `$PY` shim, `gh` credentials) extend this.
    def sandbox_env(self):
        """Built from nothing. Anything not listed here is not inherited."""
        return {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
            "ZDOTDIR": str(self.zdot),
            "CDPATH": "",
            "SHELL": "/bin/zsh",
            "LANG": "C",
            "LC_ALL": "C",
        }

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="gate-")).resolve()
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        self.assertNotEqual(self.td, REPO, "refusing to run in the repo")
        self.bin = self.td / "bin"
        self.home = self.td / "home"
        self.tmp = self.td / "tmp"
        self.zdot = self.td / "zdotdir"
        for d in (self.bin, self.home, self.tmp, self.zdot):
            d.mkdir()
        self.env = self.sandbox_env()
        self.assertSandboxed(self.env)
        self.before = snapshot(SENTINELS)
        self.before_repo = snapshot(REPO_ARTIFACTS)
        self.addCleanup(self.assertNothingEscaped)

    # ---------- environment ----------

    def assertSandboxed(self, env):
        for key in ("HOME", "TMPDIR", "ZDOTDIR"):
            value = Path(env[key])
            self.assertTrue(
                str(value).startswith(str(self.td) + os.sep),
                f"{key}={value} is outside the sandbox")
            self.assertNotEqual(value, REAL_HOME, f"{key} is the real home")
        self.assertEqual(env["CDPATH"], "", "CDPATH was not cleared")
        real = str(REAL_HOME)
        for key, value in env.items():
            if key == "PATH":
                continue
            self.assertNotIn(
                real, str(value),
                f"{key} still points into the real home directory")

    def assertNothingEscaped(self):
        after = snapshot(SENTINELS)
        for path, state in self.before.items():
            self.assertEqual(
                after[path], state,
                f"{path} changed while this test ran - something reached "
                "outside the sandbox")
        after_repo = snapshot(REPO_ARTIFACTS)
        for path, state in self.before_repo.items():
            self.assertEqual(
                after_repo[path], state,
                f"{path} changed while this test ran - a fragment built, "
                "packaged or installed something in the real repository")

    def zsh(self, script, cwd=None, env=None, timeout=60):
        """Run `script` in a no-rc zsh under the sandbox environment.

        `-f` (NO_RCS) is the point: the plain `/bin/zsh -c` this suite used
        before sources the user's real `~/.zshenv` into every fragment shell.
        """
        used = dict(env or self.env)
        # The check belongs HERE, not only in setUp. Asserting the environment
        # once at setup time verifies `self.env`; it says nothing about an env a
        # caller builds and passes in, and nothing about `self.env` after a test
        # has mutated it. Putting it at the single spawn point means no shell in
        # this module can start without the environment it will actually run
        # under having been checked. (`PublishBehaviourTests` previously rebuilt
        # `self.env` in its own setUp, so the checked object and the used object
        # were different ones - that is this failure mode, already observed.)
        self.assertSandboxed(used)
        return subprocess.run(
            ["/bin/zsh", "-f", "-c", script],
            cwd=str(cwd or self.td), env=used,
            capture_output=True, text=True, timeout=timeout)


class EnvironmentIsolationLimitsTests(SandboxedShell):
    """What the allow-list CANNOT close, demonstrated rather than described.

    The environment allow-list rests on an assumption nobody stated: that code
    finds the user's home by *reading a variable*. Plenty of it does not.
    `getpwuid` reads the password database, which no environment can influence,
    and several macOS frameworks resolve the home directory that way regardless
    of `HOME`. So a fragment that shells out to such a tool reaches the real
    home while every environment assertion in this file passes.

    These tests exist so that fact is **pinned by a failing-if-wrong assertion**
    instead of living in a comment someone later deletes as obvious. They are
    also the justification for `SENTINELS`: outcome checks are the only control
    that survives a bypass of the environment, and if the bypass below ever
    stopped being real, the sentinels could be argued away.
    """

    def test_the_password_database_ignores_our_HOME(self):
        """The bypass, shown end to end in a shell we ourselves sandboxed."""
        r = self.zsh('/usr/bin/python3 -c '
                     '"import os,pwd;print(os.environ[\'HOME\']);'
                     'print(pwd.getpwuid(os.getuid()).pw_dir)"')
        self.assertEqual(r.returncode, 0, r.stderr)
        env_home, pw_home = r.stdout.split()
        self.assertTrue(env_home.startswith(str(self.td)),
                        f"HOME did not reach the child as sandboxed: {env_home}")
        self.assertEqual(
            pw_home, str(REAL_HOME),
            "the password database no longer reports the real home, so the "
            "documented bypass has changed shape - re-examine whether the "
            "environment allow-list is now sufficient on its own")

    def test_sentinels_would_notice_a_path_that_did_not_exist_before(self):
        """`assertNothingEscaped` must catch CREATION, not only growth.

        Today's incident created a directory that had never existed, so a
        check comparing sizes of files present at setUp would have reported
        nothing. Asserted against `snapshot` directly rather than by making a
        real escape happen.
        """
        victim = self.td / "not-there-yet"
        before = snapshot([victim])
        self.assertEqual(before[str(victim)], (False, None, None))
        victim.mkdir()
        self.assertNotEqual(
            snapshot([victim])[str(victim)], before[str(victim)],
            "creating a path that was absent at setUp produced an identical "
            "snapshot - every sentinel is blind to creation")


class _Gate(SandboxedShell):
    """`release.sh` upload-gate sandbox: `SandboxedShell` plus tool shims."""

    #: `verify_upload_artifact` calls `cur_version` to build the version the
    #: bundle must claim. It is defined at the top level of `release.sh`, so a
    #: brace-matched fragment does not carry it; without this stub the gate
    #: passes an EMPTY `--expect-version`, which is the one value the updater's
    #: preflight rejects outright - and the suite would be exercising a
    #: never-reached branch while reporting green.
    #: Derived from `claude_pet.py`, not hardcoded. The real `cur_version`
    #: greps `APP_VERSION` out of that file, so a literal "0.19" here would
    #: silently stop matching production at the next version bump - and the
    #: only test that reads this value asserts it is non-empty, which a stale
    #: literal satisfies perfectly. Deriving it means the stub cannot drift.
    PRELUDE = 'cur_version() { echo %s; }\n' % CURRENT_APP_VERSION

    def setUp(self):
        super().setUp()
        # Hash and extract from one byte snapshot.  These tests source shell
        # text, so a concurrent production edit must be a fail-closed review
        # event, never something the harness discovers by executing it.
        release_bytes = RELEASE_SH.read_bytes()
        self.assertEqual(
            hashlib.sha256(release_bytes).hexdigest(), REVIEWED_RELEASE_SHA256,
            "release.sh changed after the fragment harness was reviewed")
        assert_reviewed_file(self, RELEASE_VERIFIER, REVIEWED_VERIFIER_SHA256)
        assert_reviewed_file(self, APP_SOURCE, REVIEWED_APP_SOURCE_SHA256)
        self.release_text = release_bytes.decode()
        self.calls = self.td / "calls.log"
        self.calls.write_text("")
        self.fragment = self.td / "fragment.sh"
        self.fragment.write_text(
            extract_function(self.release_text, FUNCTION) + "\n")
        self.shim_signing_tools()
        self.shim_mktemp()
        # POISON BY DEFAULT. `setup_ditto` / `setup_hdiutil` overwrite these.
        # A test that forgets to call them must fail loudly here rather than
        # reach `/usr/bin/ditto` or `/usr/bin/hdiutil` and get a *plausible*
        # answer - a real ditto would extract a real archive, and a real
        # hdiutil would attach a real image, either of which produces a green
        # test that exercised the machine instead of the fixture.
        self.poison("ditto")
        self.poison("hdiutil")

    def sandbox_env(self):
        env = super().sandbox_env()
        env.update({
            "PY": str(self.bin / "pyshim"),
            # Even an escapee must be unauthenticated and offline.
            "GH_TOKEN": "",
            "GH_ENTERPRISE_TOKEN": "",
            "GH_CONFIG_DIR": str(self.td / "ghconfig"),
            "GH_NO_UPDATE_NOTIFIER": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        return env

    # ---------- shims ----------

    def shim_signing_tools(self):
        """Signing tools are shimmed even though nothing calls them yet.

        `verify_upload_artifact` is growing a codesign / signature / version /
        arch preflight. `self.bin` precedes `/usr/bin` on the sandbox PATH, so
        these must exist BEFORE that lands - otherwise the first run after it
        lands quietly invokes the real `/usr/bin/codesign` on a fake bundle.
        Default is success; a test that needs a failure re-shims the one tool.
        """
        for tool in ("codesign", "spctl", "xcrun", "stapler", "lipo", "plutil"):
            self.shim(tool, "exit 0\n")

    #: Exit status of a poison shim. Distinctive so it cannot be confused with
    #: a tool's own failure code, which is what a plain `exit 1` would be.
    POISON_RC = 97
    POISON_MARK = "POISONED-TOOL-REACHED"

    def poison(self, name):
        """A tool that must never be reached unconfigured, made to shout."""
        self.shim(name, f'echo "{self.POISON_MARK} {name} $*" >&2\n'
                        f'echo "{self.POISON_MARK} {name}" >> "{self.calls}"\n'
                        f"exit {self.POISON_RC}\n")

    def shim_mktemp(self):
        """`mktemp` must allocate inside the sandbox, not wherever it likes.

        The gate opens with `tmp=$(mktemp -d)` and `publish` takes a
        `$(mktemp)` for its notes. Real `mktemp` follows `TMPDIR` *as it is at
        that moment* - so this is the same class as the environment gaps, one
        layer down in the shell: if `TMPDIR` is ever unset, cleared by a
        fragment, or ignored, allocation silently moves to `/tmp` and the
        extraction and mount land outside everything this harness controls.

        Rather than trusting the variable, the shim refuses to run without it
        and allocates under it explicitly. `assertAllocationsWereContained`
        then checks the paths it handed out.
        """
        self.shim("mktemp", f'''
: "${{TMPDIR:?{self.POISON_MARK} mktemp ran with no TMPDIR}}"
n=0
while :; do
  p="$TMPDIR/mktemp.$$.$n"
  [ -e "$p" ] || break
  n=$((n + 1))
done
case "$1" in
  -d|-dt) mkdir -p "$p" ;;
  *)      : > "$p" ;;
esac
# Record what was handed out, not just that we were called. The gate deletes
# its temp tree on the way out, so by assertion time the directory is gone -
# a check that looked for surviving paths would find nothing and pass.
echo "mktemp-> $p" >> "{self.calls}"
printf '%s\\n' "$p"
''')

    def arches_passed(self):
        """The `--arches` values the gate handed the bundle check."""
        out = []
        for line in self.logged().splitlines():
            if line.startswith("pyshim ") and "--arches" in line:
                rest = line.split("--arches", 1)[1].split()
                out.append(rest[0] if rest else "")
        return out

    def versions_passed(self):
        """The exact ``--expect-version`` values sent to app preflight."""
        out = []
        for line in self.logged().splitlines():
            if line.startswith("pyshim ") and " app " in line:
                rest = line.split("--expect-version", 1)
                if len(rest) == 2:
                    values = rest[1].split()
                    out.append(values[0] if values else "")
        return out

    def py_gate_phases(self):
        """Classify verifier calls without treating extraction as verification."""
        phases = []
        for line in self.logged().splitlines():
            if not line.startswith("pyshim "):
                continue
            if "verify_release_artifact.py assets " in line:
                phases.append("assets")
            elif "verify_release_artifact.py scan " in line:
                phases.append("scan")
            elif "verify_pet_payload.py " in line:
                phases.append("pet")
            elif "verify_release_artifact.py app " in line:
                phases.append("app")
        return phases

    def allocations(self):
        """Paths the mktemp shim handed out, read back from its call log."""
        return [l.split("mktemp-> ", 1)[1]
                for l in self.logged().splitlines() if l.startswith("mktemp-> ")]

    def assertAllocationsWereContained(self):
        for line in self.logged().splitlines():
            if line.startswith(self.POISON_MARK):
                self.fail(f"a poisoned tool was reached: {line}")
        allocated = self.allocations()
        self.assertTrue(
            allocated,
            "the mktemp shim was never called, so this says nothing about "
            f"where allocation happened: {self.logged()!r}")
        for p in allocated:
            self.assertTrue(
                p.startswith(str(self.td) + os.sep),
                f"mktemp allocated outside the sandbox: {p}")

    def shim(self, name, body):
        p = self.bin / name
        p.write_text("#!/bin/sh\n"
                     f'echo "{name} $*" >> "{self.calls}"\n' + body)
        p.chmod(0o755)

    def app_maker(self, layout):
        """Shell that builds `layout` under $DEST. layout: list of relpaths;
        a trailing '/' means a directory (an .app bundle)."""
        lines = []
        for rel in layout:
            if rel.endswith("/"):
                lines.append(f'mkdir -p "$DEST/{rel.rstrip("/")}/Contents/Resources/.claude_pet"')
            else:
                lines.append(f'mkdir -p "$(dirname "$DEST/{rel}")"; : > "$DEST/{rel}"')
        return "\n".join(lines) + "\n"

    def setup_ditto(self, layout=None, fail=False):
        if fail:
            self.shim("ditto", "exit 1\n")
            return
        body = ('DEST=""\nfor a in "$@"; do DEST="$a"; done\n'
                + self.app_maker(layout or ["ClaudePet.app/"]) + "exit 0\n")
        self.shim("ditto", body)

    def setup_hdiutil(self, layout=None, attach_fails=False, detach_fails=False):
        if attach_fails:
            self.shim("hdiutil", 'case "$1" in attach) exit 1 ;; esac\nexit 0\n')
            return
        maker = self.app_maker(layout or ["ClaudePet.app/"])
        body = (
            'if [ "$1" = "attach" ]; then\n'
            '  DEST=""; prev=""\n'
            '  for a in "$@"; do [ "$prev" = "-mountpoint" ] && DEST="$a"; prev="$a"; done\n'
            # the mountpoint must already exist - that is the behaviour under test
            '  [ -d "$DEST" ] || { echo "MOUNTPOINT_MISSING" >> "%s"; exit 1; }\n'
            % self.calls
            + "  " + maker.replace("\n", "\n  ") + "\nfi\n"
            + ('[ "$1" = "detach" ] && exit 88\n' if detach_fails else '')
            + "exit 0\n"
        )
        self.shim("hdiutil", body)

    def setup_py(self, payload_ok=True, scan_ok=True, app_ok=True,
                 real_scan=False, real_assets=False):
        """`$PY` serves THREE distinct checks; each must fail on its own.

        The gate calls, in order:
          `$PY verify_release_artifact.py scan <archive>`   (pre-extraction)
          `$PY verify_release_artifact.py app  <bundle> ...` (identity/sig/arch)
          `$PY verify_pet_payload.py <tree>`                (payload)

        Two rounds of the same mistake, both worth keeping written down because
        the shim looked adequate each time:

        1. One status for everything: `payload_ok=False` failed at the *scan*.
           The gate still rejected, the test still went green, and the payload
           branch was never reached.
        2. Dispatch on the script basename only: `verify_release_artifact.py`
           serves both `scan` and `app`, so `scan_ok=False` failed both and the
           **`app` branch was uncoverable** - no fixture could reach it, so no
           assertion about it could ever fail.

        So dispatch on the subcommand in `$2` as well. The general lesson: a
        shim must be at least as discriminating as the interface it stands in
        for, or it silently merges branches the tests believe are separate.
        """
        python = shlex.quote(sys.executable)
        verifier = shlex.quote(str(RELEASE_VERIFIER))
        # release.sh passes a repository-relative script name.  The harness
        # intentionally runs from a temp cwd, so replace only that argv[0]
        # while preserving the real subcommand and all following arguments.
        real = f'shift; exec {python} -I -B {verifier} "$@"'
        self.shim("pyshim",
                  'case "$(basename "$1") $2" in\n'
                  '  "verify_release_artifact.py scan") %s ;;\n'
                  '  "verify_release_artifact.py app") exit %d ;;\n'
                  '  "verify_release_artifact.py assets") %s ;;\n'
                  'esac\n'
                  'case "$(basename "$1")" in\n'
                  '  verify_pet_payload.py) exit %d ;;\n'
                  'esac\n'
                  'exit 0\n'
                  % (real if real_scan else f'exit {0 if scan_ok else 1}',
                     0 if app_ok else 1,
                     real if real_assets else 'exit 0',
                     0 if payload_ok else 1))

    def run_gate(self, artifact):
        cmd = (f'source {self.fragment}; '
               f'{FUNCTION} "{artifact}"; echo "RC=$?"')
        r = self.zsh(f"setopt FUNCTION_ARGZERO; {self.PRELUDE}\n{cmd}",
                     timeout=30)
        rc = None
        for line in r.stdout.splitlines():
            if line.startswith("RC="):
                rc = int(line[3:])
        return rc, r.stdout + r.stderr

    def logged(self):
        return self.calls.read_text()

    def make_artifact(self, name):
        p = self.td / name
        p.write_bytes(b"artifact")
        return p


class VerifyUploadArtifactTests(_Gate):
    def test_missing_artifact_fails_rather_than_passing_unchecked(self):
        self.setup_ditto(); self.setup_py()
        rc, out = self.run_gate(self.td / "nope.zip")
        self.assertEqual(rc, 1, out)
        self.assertNotIn("ditto", self.logged(),
                         "must fail before trying to inspect anything")

    def test_clean_zip_with_one_root_app_passes(self):
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.zip"))
        self.assertEqual(rc, 0, out)

    def test_corrupt_zip_fails(self):
        self.setup_ditto(fail=True); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("bad.zip"))
        self.assertEqual(rc, 1, out)

    def test_unknown_extension_fails_closed(self):
        self.setup_ditto(); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("mystery.tar.gz"))
        self.assertEqual(rc, 1, out)

    def test_zip_with_no_app_fails(self):
        self.setup_ditto(["README.txt"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("empty.zip"))
        self.assertEqual(rc, 1, out)

    def test_a_second_root_app_is_rejected(self):
        """Flipped from documenting the gap to requiring it be closed.

        The gate used to glob `"$root"/ClaudePet.app(N)` - an exact filename,
        not a pattern - so `${#apps[@]}` could only ever be 0 or 1 and the
        `-ne 1` arm was dead code, despite its message "(${#apps[@]}개)"
        expecting >1. It counted presence, not uniqueness. The fix counts all
        root `*.app` entries and checks the name separately, which makes that
        arm reachable and its message true.

        Two root apps means we do not know what we are shipping, so it must
        fail. The count branch has to be the one that fires - a name check
        alone would also reject this fixture while leaving a two-ClaudePet.app
        artifact (unconstructible, but that is an accident of naming) unjudged
        - so the message is asserted, not just the return code.
        """
        self.setup_ditto(["ClaudePet.app/", "Other.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("extra.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn("정확히 하나가 아님 (2개)", out,
                      "rejected, but not by the root-app count branch")

    def test_nested_app_is_not_accepted_as_a_root_app(self):
        self.setup_ditto(["inner/ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("nested.zip"))
        self.assertEqual(rc, 1, out)

    def test_an_app_hidden_inside_the_bundle_is_rejected(self):
        """The nested scan, which no other case reaches.

        One correctly-named app at the root, so both earlier branches are
        satisfied; the only thing that can fail this fixture is the `**/`
        walk. Asserting the message keeps it that way - a future change that
        rejects this for some other reason must not read as coverage of the
        nested scan.
        """
        self.setup_ditto(["ClaudePet.app/",
                          "ClaudePet.app/Contents/Frameworks/Python.app/"])
        self.setup_py()
        rc, out = self.run_gate(self.make_artifact("hidden.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn("설명되지 않는 .app", out,
                      "rejected, but not by the nested-app scan")

    def test_failing_payload_check_fails_the_gate(self):
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py(payload_ok=False)
        rc, out = self.run_gate(self.make_artifact("badpayload.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn("펫 자산 검사 실패", out,
                      "rejected, but not by the payload check")

    def test_failing_bundle_check_fails_the_gate(self):
        """The `app` branch, unreachable until the shim learned subcommands."""
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py(app_ok=False)
        rc, out = self.run_gate(self.make_artifact("ClaudePet.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn("번들 검사 실패", out,
                      "rejected, but not by the bundle identity check")

    def test_every_artifact_passes_the_exact_current_version_and_arch_contract(self):
        """The defect an all-passing shim hid completely.

        `cur_version` lives at `release.sh` top level, so a brace-matched
        fragment does not carry it. Unstubbed it expands to the empty string
        and the gate passes `--expect-version ''` - the one value
        `validate_update_app` rejects outright. Every run was green on an
        argument that would fail in production, because `pyshim` exits 0
        whatever it is handed.

        Asserting the recorded argv is the only way to see it: the return code
        cannot, by construction.
        """
        contracts = {
            "ClaudePet.zip": "arm64",
            "ClaudePet-universal.zip": "arm64,x86_64",
            "ClaudePet.dmg": "arm64",
            "ClaudePet-universal.dmg": "arm64,x86_64",
        }
        for name, arches in contracts.items():
            with self.subTest(artifact=name):
                self.calls.write_text("")
                self.setup_ditto(["ClaudePet.app/"])
                self.setup_hdiutil(["ClaudePet.app/"])
                self.setup_py()
                rc, out = self.run_gate(self.make_artifact(name))
                self.assertEqual(rc, 0, out)
                self.assertEqual(
                    self.versions_passed(), [CURRENT_APP_VERSION],
                    f"{name} did not pass the checkout's exact APP_VERSION")
                self.assertEqual(
                    self.arches_passed(), [arches],
                    f"{name} did not pass its exact architecture contract")

    def test_the_plain_archive_pins_arm64_from_the_contract_not_the_host(self):
        """Asserted against `UPDATE_ASSET_NAMES`, deliberately not `uname -m`.

        I first wrote this as `platform.machine()`, which is wrong in a way
        worth keeping written down: `release.sh` currently derives this value
        from `uname -m`, so a test reading `uname -m` agrees with the broken
        implementation and the fixed one **equally**, on every machine. It
        cannot fail. The contract is that `ClaudePet.zip` is the arm64 asset -
        `UPDATE_ASSET_NAMES["arm64"]` lists `claudepet.zip`, and `x86_64` does
        not - so `arm64` is what the gate must require, whatever host it runs
        on. On an Intel machine the host-reading version would demand `x86_64`
        of an artifact that is arm-only and pass.
        """
        asset_names = updater_asset_names()
        self.assertIn("claudepet.zip", asset_names["arm64"],
                      "the contract this test reads has changed shape")
        self.assertNotIn("claudepet.zip",
                         asset_names["x86_64"],
                         "the plain zip is no longer arm-only, so this "
                         "expectation needs rederiving")
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.zip"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.arches_passed(), ["arm64"],
                         "the plain archive was not pinned to arm64 - if this "
                         f"reads {platform.machine()!r} the gate is deriving "
                         "the requirement from the host rather than from the "
                         "asset-name contract")

    def test_the_universal_archive_pins_BOTH_architectures(self):
        """Both, exactly - not "at least one", which is the whole point.

        A universal artifact that only carries `arm64` is precisely the
        mis-packaging the arch check exists to catch. An assertion that
        accepted either value would pass on it, so this compares the set.
        """
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet-universal.zip"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.arches_passed(), ["arm64,x86_64"],
                         "the universal archive did not require both slices")

    def test_the_two_archive_kinds_are_not_given_the_same_arches(self):
        """Discrimination: if both produced one value, one test above is dead.

        The two assertions differ only in the artifact name, so a gate that
        ignored the name entirely would still satisfy one of them. Only
        comparing the two runs proves the name is what selects the value.
        """
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        self.run_gate(self.make_artifact("ClaudePet.zip"))
        single = self.arches_passed()
        self.calls.write_text("")
        self.run_gate(self.make_artifact("ClaudePet-universal.zip"))
        universal = self.arches_passed()
        self.assertNotEqual(single, universal,
                            "the artifact name does not affect the required "
                            "architectures")

    def test_failing_archive_scan_fails_before_extraction(self):
        """The scan runs before `ditto`, and order is the whole point.

        A member that escapes the archive root is already written outside the
        temp directory by the time an after-the-fact walk looks, so a scan
        moved below the extraction stops preventing anything.
        """
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py(scan_ok=False)
        rc, out = self.run_gate(self.make_artifact("unsafe.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn("아카이브 안전성 검사 실패", out,
                      "rejected, but not by the archive scan")
        self.assertNotIn("ditto", self.logged(),
                         "the archive was extracted despite failing the scan")


class DmgArmTests(_Gate):
    def test_dmg_mountpoint_exists_before_attach(self):
        """The regression this arm was fixed for: attach needs the dir first."""
        self.setup_hdiutil(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.dmg"))
        self.assertNotIn("MOUNTPOINT_MISSING", self.logged(),
                         "hdiutil attach was called before the mountpoint existed")
        self.assertEqual(rc, 0, out)

    def test_dmg_is_detached_after_a_successful_check(self):
        self.setup_hdiutil(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.dmg"))
        self.assertEqual(rc, 0, out)
        self.assertIn("hdiutil detach", self.logged())

    def test_dmg_that_fails_to_attach_fails_the_gate(self):
        self.setup_hdiutil(attach_fails=True); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("bad.dmg"))
        self.assertEqual(rc, 1, out)

    def test_detach_failure_is_gate_failure_and_retains_the_named_mount(self):
        self.setup_hdiutil(["ClaudePet.app/"], detach_fails=True)
        self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.dmg"))

        self.assertEqual(rc, 1, out)
        self.assertIn("마운트 해제 실패", out)
        retained = [Path(path) for path in self.allocations() if Path(path).exists()]
        self.assertEqual(len(retained), 1, self.logged())
        self.assertTrue((retained[0] / "mnt").is_dir())
        self.assertIn(str(retained[0] / "mnt"), out)

    def test_dmg_with_a_wrongly_named_app_fails_and_still_detaches(self):
        """A rejection must not leave the image mounted.

        One root .app, so the count branch is satisfied and the *name* branch
        is what rejects this - asserted, because under the old glob this
        fixture failed the count branch instead and the two are easy to
        confuse now that both are reachable.
        """
        self.setup_hdiutil(["Other.app/", "README.txt"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("noapp.dmg"))
        self.assertEqual(rc, 1, out)
        self.assertIn("이름이 ClaudePet.app 이 아님", out,
                      "rejected, but not by the app-name branch")
        self.assertIn("hdiutil detach", self.logged(),
                      "a failed check must not leave the image mounted")

    def test_dmg_with_two_root_apps_fails_and_still_detaches(self):
        """Now constructible, and the detach path must hold for it too."""
        self.setup_hdiutil(["ClaudePet.app/", "Other.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("twoapps.dmg"))
        self.assertEqual(rc, 1, out)
        self.assertIn("정확히 하나가 아님 (2개)", out,
                      "rejected, but not by the root-app count branch")
        self.assertIn("hdiutil detach", self.logged(),
                      "a failed check must not leave the image mounted")


class OneDmgPackagingTests(SandboxedShell):
    """The release DMG transaction, with every mutator replaced by a shim.

    This is deliberately separate from :class:`DmgArmTests`.  That class opens
    an already-built DMG immediately before upload; this class proves that
    ``one_dmg`` cannot leave a half-created file under the canonical publish
    name when create/notary/staple/validate fails.

    Only the two function texts are sourced.  The absolute ditto invocation and
    the drag-install symlink target are mechanically replaced exactly once,
    and every command capable of changing the filesystem resolves to the one
    temp-root-enforcing Python helper below.  No app is built, mounted, signed,
    notarized, stapled, or validated by a macOS tool.
    """

    MUTATORS = ("mktemp", "ditto", "mkdir", "rm", "mv", "ln",
                "hdiutil", "xcrun", "du")

    SAFE_OPS = r'''#!/usr/bin/python3
import os
import shutil
import sys
import tempfile

root = os.path.realpath(os.environ["TEST_ROOT"])
calls = os.environ["TEST_CALLS"]
tool = os.path.basename(sys.argv[0])
args = sys.argv[1:]

def record(line):
    with open(calls, "a", encoding="utf-8") as out:
        out.write(line + "\n")

def checked(path, *, allow_missing=True):
    raw = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
    resolved = os.path.realpath(raw)
    try:
        inside = os.path.commonpath((root, resolved)) == root
    except ValueError:
        inside = False
    if not inside:
        raise SystemExit("OUTSIDE-TEMP: " + path)
    if not allow_missing and not os.path.lexists(raw):
        raise SystemExit("MISSING: " + path)
    return os.path.abspath(raw)

record(tool + (" " + " ".join(args) if args else ""))

if tool == "mktemp":
    path = tempfile.mkdtemp(prefix="one-dmg-", dir=os.environ["TEST_TMP"])
    record("mktemp-> " + path)
    print(path)
elif tool == "ditto":
    src, dst = checked(args[-2], allow_missing=False), checked(args[-1])
    shutil.copytree(src, dst, symlinks=True)
elif tool == "mkdir":
    paths = [a for a in args if not a.startswith("-")]
    for path in paths:
        os.makedirs(checked(path), exist_ok="-p" in args)
elif tool == "rm":
    recursive = any("r" in a for a in args if a.startswith("-"))
    for path in (a for a in args if not a.startswith("-")):
        target = checked(path)
        if not os.path.lexists(target):
            continue
        if os.path.isdir(target) and not os.path.islink(target):
            if not recursive:
                raise SystemExit("REFUSE-DIR-RM: " + path)
            shutil.rmtree(target)
        else:
            os.unlink(target)
elif tool == "mv":
    paths = [a for a in args if not a.startswith("-")]
    if len(paths) != 2:
        raise SystemExit("BAD-MV-ARGV")
    src = checked(paths[0], allow_missing=False)
    dst = checked(paths[1])
    os.replace(src, dst)
elif tool == "ln":
    paths = [a for a in args if not a.startswith("-")]
    if len(paths) != 2 or "-s" not in args:
        raise SystemExit("BAD-LN-ARGV")
    target = checked(paths[0], allow_missing=False)
    os.symlink(target, checked(paths[1]))
elif tool == "hdiutil":
    if not args or args[0] != "create":
        raise SystemExit("UNEXPECTED-HDIUTIL")
    dmg = checked(args[-1])
    os.makedirs(os.path.dirname(dmg), exist_ok=True)
    with open(dmg, "wb") as out:
        out.write(b"synthetic dmg\n")
    if os.environ.get("TEST_MODE") == "hdiutil_fail":
        raise SystemExit(41)
elif tool == "xcrun":
    if args[:2] == ["stapler", "staple"]:
        checked(args[2], allow_missing=False)
        if os.environ.get("TEST_MODE") == "staple_fail":
            raise SystemExit(42)
    elif args[:2] == ["stapler", "validate"]:
        checked(args[2], allow_missing=False)
        mode = os.environ.get("TEST_MODE")
        if mode == "validate_rc_fail":
            print("synthetic validation rc failure")
            raise SystemExit(43)
        if mode == "validate_text_fail":
            print("The validate action failed!")
        else:
            print("synthetic validation success")
    else:
        raise SystemExit("UNEXPECTED-XCRUN")
elif tool == "du":
    checked(args[-1], allow_missing=False)
    print("1K\t" + args[-1])
else:
    raise SystemExit("UNKNOWN-SAFE-OP: " + tool)
'''

    def setUp(self):
        super().setUp()
        release_bytes = RELEASE_SH.read_bytes()
        self.assertEqual(
            hashlib.sha256(release_bytes).hexdigest(), REVIEWED_RELEASE_SHA256,
            "release.sh changed after the one_dmg harness was reviewed")
        text = release_bytes.decode()
        quarantine = extract_function(text, "quarantine_dmg")
        one_dmg = extract_function(text, "one_dmg")

        old_ditto = '/usr/bin/ditto "$app" "$stage/ClaudePet.app"'
        new_ditto = '"$TEST_DITTO" "$app" "$stage/ClaudePet.app"'
        self.assertEqual(one_dmg.count(old_ditto), 1,
                         "ditto instrumentation target changed")
        one_dmg = one_dmg.replace(old_ditto, new_ditto, 1)

        old_link = 'ln -s /Applications "$stage/Applications"'
        new_link = 'ln -s "$TEST_APPLICATIONS" "$stage/Applications"'
        self.assertEqual(one_dmg.count(old_link), 1,
                         "Applications-link instrumentation target changed")
        one_dmg = one_dmg.replace(old_link, new_link, 1)

        # No dispatcher and no credential-bearing or install command survives
        # into the sourced fragment.  These assertions fail closed on drift.
        fragment = quarantine + "\n" + one_dmg + "\n"
        for forbidden in ("/usr/bin/ditto", "ln -s /Applications", "gh ",
                          "notarytool", "codesign", "spctl", "open ",
                          "/Applications/ClaudePet.app"):
            self.assertNotIn(forbidden, fragment)
        self.fragment = self.td / "one-dmg-functions.zsh"
        self.fragment.write_text(fragment)

        self.calls = self.td / "one-dmg-calls.log"
        self.calls.write_text("")
        safe_ops = self.td / "safe-one-dmg-ops.py"
        safe_ops.write_text(self.SAFE_OPS)
        safe_ops.chmod(0o755)
        for tool in self.MUTATORS:
            os.symlink(safe_ops, self.bin / tool)

        self.work = self.td / "work"
        self.app = self.work / "dist" / "ClaudePet.app"
        self.app.mkdir(parents=True)
        (self.app / "marker").write_text("old app bytes\n")
        self.fake_applications = self.td / "fake-Applications"
        self.fake_applications.mkdir()
        self.dmg = self.work / "release" / "ClaudePet.dmg"
        self.failed_dmg = self.work / "release" / "ClaudePet-failed.dmg"
        self.env.update({
            "TEST_ROOT": str(self.td),
            "TEST_TMP": str(self.tmp),
            "TEST_CALLS": str(self.calls),
            "TEST_DITTO": str(self.bin / "ditto"),
            "TEST_APPLICATIONS": str(self.fake_applications),
            "TEST_MODE": "success",
        })

    def run_one_dmg(self, mode="success"):
        env = dict(self.env)
        env["TEST_MODE"] = mode
        script = (
            'notary_submit() {\n'
            '  print -r -- "notary $*" >> "$TEST_CALLS"\n'
            '  [ -f "$1" ] || return 97\n'
            '  [ "$TEST_MODE" != notary_fail ]\n'
            '}\n'
            f"source {shlex.quote(str(self.fragment))}\n"
            f"one_dmg {shlex.quote(str(self.app))} "
            f"{shlex.quote(str(self.dmg))}\n"
            "rc=$?\nprint -r -- RC=$rc\n")
        result = self.zsh(script, cwd=self.work, env=env, timeout=30)
        match = re.search(r"^RC=(\d+)$", result.stdout, re.M)
        self.assertIsNotNone(match, result.stdout + result.stderr)
        return int(match.group(1)), result.stdout + result.stderr

    def logged(self):
        return self.calls.read_text().splitlines()

    def allocated_stages(self):
        return [Path(line.split("mktemp-> ", 1)[1])
                for line in self.logged() if line.startswith("mktemp-> ")]

    def assert_failure_quarantined_and_stage_removed(self, mode):
        rc, out = self.run_one_dmg(mode)
        self.assertNotEqual(rc, 0, out)
        self.assertFalse(self.dmg.exists(),
                         "failed output remained under the publish name")
        self.assertTrue(self.failed_dmg.is_file(),
                        "failed bytes were neither quarantined nor retained")
        stages = self.allocated_stages()
        self.assertEqual(len(stages), 1, self.logged())
        self.assertFalse(stages[0].exists(),
                         f"failed transaction left its stage: {stages[0]}")

    def test_hdiutil_failure_quarantines_partial_dmg_and_removes_stage(self):
        self.assert_failure_quarantined_and_stage_removed("hdiutil_fail")

    def test_notary_failure_quarantines_dmg_and_removes_stage(self):
        self.assert_failure_quarantined_and_stage_removed("notary_fail")
        self.assertFalse(any(line.startswith("xcrun ") for line in self.logged()),
                         "stapling ran after notarization failed")

    def test_staple_failure_quarantines_dmg_and_removes_stage(self):
        self.assert_failure_quarantined_and_stage_removed("staple_fail")
        self.assertFalse(any(line.startswith("xcrun stapler validate")
                             for line in self.logged()),
                         "validation ran after staple failed")

    def test_validate_nonzero_quarantines_dmg_and_removes_stage(self):
        self.assert_failure_quarantined_and_stage_removed("validate_rc_fail")

    def test_validate_failure_text_with_zero_status_is_still_failure(self):
        self.assert_failure_quarantined_and_stage_removed("validate_text_fail")

    def test_success_runs_create_notary_staple_validate_in_exact_order(self):
        rc, out = self.run_one_dmg()
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.dmg.is_file())
        self.assertFalse(self.failed_dmg.exists())
        self.assertEqual(len(self.allocated_stages()), 1, self.logged())
        self.assertFalse(self.allocated_stages()[0].exists())
        phases = []
        for line in self.logged():
            if line.startswith("hdiutil create"):
                phases.append("create")
            elif line.startswith("notary "):
                phases.append("notary")
            elif line.startswith("xcrun stapler staple"):
                phases.append("staple")
            elif line.startswith("xcrun stapler validate"):
                phases.append("validate")
        self.assertEqual(phases, ["create", "notary", "staple", "validate"])


class PublishBehaviourTests(_Gate):
    """`publish` RUN, not read: the claim is "no `gh` call happened".

    The text checks below can hold while the runtime path still reaches `gh` -
    a `set +e` in scope, a status swallowed by a subshell, a second `gh` call
    no assertion covers. Only running says otherwise, so these cases execute
    the real `publish` wired to the real `verify_upload_artifact` and count
    invocations of a `gh` shim.

    THE REAL `gh` IS NEVER REACHABLE, by four independent means - a single
    guard would be one typo away from writing to the user's releases:
      1. `PATH` is the sandbox bin plus /usr/bin:/bin only. Homebrew's prefixes,
         where the real gh lives, are not on it.
      2. `setUp` asserts that `command -v gh` resolves inside the sandbox and
         that no other gh is on the constructed PATH - asserted, not assumed,
         so a PATH change cannot silently re-expose it.
      3. `GH_TOKEN`/`GH_ENTERPRISE_TOKEN` are emptied and `GH_CONFIG_DIR`
         points into the sandbox, so an escapee would be unauthenticated.
      4. `GH_NO_UPDATE_NOTIFIER=1` keeps even a stray real invocation from
         reaching the network.

    Those four isolate the tool we EXPECTED to be dangerous, and that is not
    the same as isolating the sandbox. `_Gate` supplies the rest - a built
    environment (`HOME`, `TMPDIR`, `ZDOTDIR`, `CDPATH`) and the `SENTINELS`
    check that runs after every case - because the routes out of a sourced
    shell fragment are not enumerable by naming tools.

    Ordering is read off `ditto`/`hdiutil` markers rather than an injected
    probe: those are the real gate opening the real artifact, so "verified
    before the first gh call" is observed from the code under test, not from
    scaffolding that could agree with a broken implementation.
    """

    # `publish` needs these from release.sh's top level and from functions it
    # does not define itself. Stubbed, and no stub can pass the gate for a
    # file: verify_upload_artifact is the real one.
    #: Kept apart from `_Gate.PRELUDE` (which is literal shell) because this
    #: half goes through `str.format`, where a literal `{` would be read as a
    #: field. The two are concatenated in `run_publish`.
    #: Generated from `release.sh`'s own ZIP/UZIP/DMG/UDMG rather than
    #: re-declared here. Re-declaring them made this class blind to the exact
    #: coupling `AssetNameCouplingTests` exists to catch: a rename in
    #: `release.sh` would leave these tests green while the real publish
    #: uploaded something the updater cannot match. A suite written to catch a
    #: bug should not contain it.
    PUBLISH_VARS = "".join(
        '%s="{td}/release/%s"\n' % (var, name)
        for var, name in release_sh_asset_names().items()
    ) + 'gen_release_notes() {{ echo "notes" > "$1"; }}\n'

    def setUp(self):
        super().setUp()
        (self.td / "release").mkdir()
        self.shim("gh", "exit 0\n")
        self.fragment.write_text(
            extract_function(self.release_text, FUNCTION) + "\n"
            + extract_function(self.release_text, "publish") + "\n")
        # The environment is `_Gate`'s, unmodified. It was rebuilt here in an
        # earlier revision, which meant the sandbox this class ran under was
        # not the sandbox `_Gate.assertSandboxed` had checked - the guard and
        # the thing guarded had drifted apart.
        self.assertSandboxed(self.env)
        # Guard 2: prove the shim is what `gh` resolves to, before any test
        # body can rely on it.
        which = shutil.which("gh", path=self.env["PATH"])
        self.assertEqual(which, str(self.bin / "gh"),
                         f"`gh` on the sandbox PATH is {which!r}, not the shim "
                         "- refusing to run anything that calls gh")
        for d in self.env["PATH"].split(os.pathsep):
            p = Path(d) / "gh"
            if p.exists():
                self.assertEqual(str(p), str(self.bin / "gh"),
                                 f"a second gh is reachable at {p}")

    def artifacts(self, *names):
        for n in names:
            (self.td / "release" / n).write_bytes(b"artifact")

    def run_publish(self, publish_vars=None):
        cmd = (f'source {self.fragment}; '
               '( publish ); echo "RC=$?"')
        variables = self.PUBLISH_VARS if publish_vars is None else publish_vars
        prelude = self.PRELUDE + variables.format(td=self.td)
        r = self.zsh(f"setopt FUNCTION_ARGZERO; {prelude}\n{cmd}", timeout=60)
        rc = None
        for line in r.stdout.splitlines():
            if line.startswith("RC="):
                rc = int(line[3:])
        return rc, r.stdout + r.stderr

    def gh_calls(self):
        return [l for l in self.logged().splitlines() if l.startswith("gh ")]

    def opens(self):
        """Lines showing the gate actually opened an artifact."""
        return [l for l in self.logged().splitlines()
                if l.startswith("ditto ") or l.startswith("hdiutil attach")]

    # ---------- the reject cases: zero gh invocations ----------

    def test_assets_subcommand_blocks_a_missing_file_before_any_artifact_opens(self):
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg")
        self.setup_ditto(); self.setup_hdiutil(); self.setup_py(real_assets=True)
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertEqual(self.py_gate_phases(), ["assets"])
        self.assertEqual(self.opens(), [])
        self.assertEqual(self.gh_calls(), [],
                         "publish called gh with nothing to upload")

    def test_assets_subcommand_blocks_a_wrong_four_name_set(self):
        wrong_vars = self.PUBLISH_VARS.replace(
            "ClaudePet-universal.dmg", "Wrong-universal.dmg")
        self.assertNotEqual(wrong_vars, self.PUBLISH_VARS,
                            "the wrong-set fixture did not change a name")
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg", "Wrong-universal.dmg")
        self.setup_ditto(); self.setup_hdiutil(); self.setup_py(real_assets=True)

        rc, out = self.run_publish(publish_vars=wrong_vars)

        self.assertEqual(rc, 1, out)
        self.assertEqual(self.py_gate_phases(), ["assets"])
        self.assertEqual(self.opens(), [])
        self.assertEqual(self.gh_calls(), [])

    def test_no_gh_call_when_the_artifact_is_corrupt(self):
        self.artifacts("ClaudePet.zip")
        self.setup_ditto(fail=True); self.setup_py()
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertEqual(self.gh_calls(), [], "a corrupt zip reached gh")

    def test_no_gh_call_when_the_payload_check_fails(self):
        self.artifacts("ClaudePet.zip")
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py(payload_ok=False)
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertIn("펫 자산 검사 실패", out,
                      "stopped, but not by the payload check")
        self.assertEqual(self.gh_calls(), [], "a bad payload reached gh")

    def test_no_gh_call_when_the_archive_scan_fails(self):
        self.artifacts("ClaudePet.zip")
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py(scan_ok=False)
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertIn("아카이브 안전성 검사 실패", out,
                      "stopped, but not by the archive scan")
        self.assertEqual(self.gh_calls(), [],
                         "an archive that failed the safety scan reached gh")

    def test_no_gh_call_when_the_artifact_carries_an_extra_app(self):
        self.artifacts("ClaudePet.zip")
        self.setup_ditto(["ClaudePet.app/", "Other.app/"]); self.setup_py()
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertEqual(self.gh_calls(), [], "an extra root app reached gh")

    def test_a_later_artifact_failing_stops_every_upload(self):
        """The one a first-file-only gate would pass.

        The zip is fine and the universal zip is not. A loop that verified the
        first file and uploaded, or that let a later failure set a status
        nothing reads, would upload all four files here. The assertion is that
        `gh` was never reached at all - one good artifact does not buy a
        publish.
        """
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip")
        self.setup_py()
        # ditto succeeds for the first artifact and fails for the second, by
        # name, so the failure is genuinely the *later* file.
        self.shim("ditto", (
            'DEST=""; SRC=""\nfor a in "$@"; do SRC="$DEST"; DEST="$a"; done\n'
            'case "$SRC" in *universal*) exit 1 ;; esac\n'
            + self.app_maker(["ClaudePet.app/"]) + "exit 0\n"))
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertEqual(len(self.opens()), 2,
                         f"the second artifact was never opened: {self.logged()!r}")
        self.assertEqual(self.gh_calls(), [],
                         "a failure on the second artifact still uploaded")

    def test_publish_stops_at_the_first_bad_artifact(self):
        """`|| exit 1`, not a status collected and ignored to the end."""
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg")
        self.setup_ditto(fail=True); self.setup_hdiutil(["ClaudePet.app/"])
        self.setup_py()
        rc, out = self.run_publish()
        self.assertEqual(rc, 1, out)
        self.assertEqual(len(self.opens()), 1,
                         "publish kept inspecting after the first failure")
        self.assertEqual(self.gh_calls(), [])

    # ---------- the control: without it, every case above is vacuous ----------

    def test_all_artifacts_good_does_reach_gh(self):
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg", "ClaudePet-universal.dmg")
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_hdiutil(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_publish()
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.gh_calls(),
                        "publish never called gh even with four clean "
                        "artifacts - the zero-call assertions above would "
                        "then pass for the wrong reason")

    def test_assets_subcommand_receives_exactly_the_four_release_names(self):
        expected = sorted(release_sh_asset_names().values(), key=str.lower)
        self.assertEqual(len(expected), 4)
        self.assertEqual(len({name.lower() for name in expected}), 4)
        self.artifacts(*expected)
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_hdiutil(["ClaudePet.app/"])
        self.setup_py(real_assets=True)

        rc, out = self.run_publish()

        self.assertEqual(rc, 0, out)
        calls = [line for line in self.logged().splitlines()
                 if "verify_release_artifact.py assets " in line]
        self.assertEqual(len(calls), 1, self.logged())
        argv = shlex.split(calls[0])
        self.assertEqual(sorted((Path(value).name for value in argv[3:]),
                                key=str.lower), expected)

    def test_every_artifact_is_verified_before_the_first_gh_call(self):
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg", "ClaudePet-universal.dmg")
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_hdiutil(["ClaudePet.app/"]); self.setup_py(real_assets=True)
        rc, out = self.run_publish()
        self.assertEqual(rc, 0, out)
        lines = self.logged().splitlines()
        first_gh = next(i for i, l in enumerate(lines) if l.startswith("gh "))
        opened = [l for l in lines[:first_gh]
                  if l.startswith("ditto ") or l.startswith("hdiutil attach")]
        self.assertEqual(len(opened), 4,
                         f"only {len(opened)} of 4 artifacts were opened "
                         f"before the first gh call: {lines!r}")
        self.assertEqual(
            self.py_gate_phases(),
            ["assets"] + ["scan", "pet", "app"] * 4,
            "each artifact must complete scan -> pet -> app, in that order, "
            "before the first gh call")

    def test_detach_failure_retains_the_mount_and_blocks_gh(self):
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg", "ClaudePet-universal.dmg")
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_hdiutil(["ClaudePet.app/"], detach_fails=True)
        self.setup_py(real_assets=True)

        rc, out = self.run_publish()

        self.assertEqual(rc, 1, out)
        self.assertEqual(self.gh_calls(), [])
        retained = [Path(path) for path in self.allocations() if Path(path).exists()]
        self.assertEqual(len(retained), 1, self.logged())
        self.assertTrue((retained[0] / "mnt").is_dir())
        self.assertIn(str(retained[0] / "mnt"), out)

    def test_the_upload_carries_every_artifact(self):
        """A gate that verifies four files and uploads three is still wrong."""
        self.artifacts("ClaudePet.zip", "ClaudePet-universal.zip",
                       "ClaudePet.dmg", "ClaudePet-universal.dmg")
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_hdiutil(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_publish()
        self.assertEqual(rc, 0, out)
        upload = next((l for l in self.gh_calls()
                       if " release upload " in l or " release create " in l), "")
        for name in ("ClaudePet.zip", "ClaudePet-universal.zip",
                     "ClaudePet.dmg", "ClaudePet-universal.dmg"):
            self.assertIn(name, upload, f"{name} was verified but not uploaded")


class HarnessContainmentTests(_Gate):
    """The harness checked as a subject, not trusted as scaffolding.

    Three of the defects on this release were in instruments rather than in
    code, so the shims and the allocation path get the same treatment as
    `release.sh` does: an assertion that fails if they stop working.
    """

    def test_an_unconfigured_ditto_is_poisoned_rather_than_real(self):
        """Forgetting `setup_ditto` must be loud, not plausible.

        Without the poison default this reaches `/usr/bin/ditto`, which would
        genuinely try to extract the fixture archive. The gate would then fail
        for a real-ish reason and the test would look fine - the machine
        answering a question the fixture was supposed to answer.
        """
        self.setup_py()                       # deliberately no setup_ditto
        rc, out = self.run_gate(self.make_artifact("unconfigured.zip"))
        self.assertEqual(rc, 1, out)
        self.assertIn(self.POISON_MARK, self.logged(),
                      "an unconfigured `ditto` did not hit the poison shim - "
                      "the real tool may have run")

    def test_an_unconfigured_hdiutil_is_poisoned_rather_than_real(self):
        self.setup_py()                       # deliberately no setup_hdiutil
        rc, out = self.run_gate(self.make_artifact("unconfigured.dmg"))
        self.assertEqual(rc, 1, out)
        self.assertIn(self.POISON_MARK, self.logged(),
                      "an unconfigured `hdiutil` did not hit the poison shim")

    def test_temporary_allocation_stays_inside_the_sandbox(self):
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        rc, out = self.run_gate(self.make_artifact("ClaudePet.zip"))
        self.assertEqual(rc, 0, out)
        self.assertAllocationsWereContained()

    def test_the_gate_allocates_at_all(self):
        """Discrimination: `assertAllocationsWereContained` is vacuous if not.

        Every containment assertion above is a statement about a list. If the
        gate stopped calling `mktemp` - or the shim stopped being reached - the
        list would be empty and 'nothing landed outside the sandbox' would be
        trivially true. Pin that the allocation actually happens.
        """
        self.setup_ditto(["ClaudePet.app/"]); self.setup_py()
        self.run_gate(self.make_artifact("ClaudePet.zip"))
        self.assertTrue(
            any(l.startswith("mktemp ") for l in self.logged().splitlines()),
            f"the gate never invoked mktemp: {self.logged()!r}")

    def test_mktemp_refuses_to_run_without_a_TMPDIR(self):
        """The failure mode the shim exists for, exercised directly.

        Real `mktemp` with no `TMPDIR` silently falls back to `/tmp`. That is
        the quiet version of this bug, so the shim must fail loudly instead -
        asserted here rather than assumed from reading the `:?` expansion.

        This invokes the shim directly instead of going through `self.zsh`,
        and the reason is worth stating: `zsh()` asserts the environment is
        sandboxed, and an environment with no `TMPDIR` is exactly what that
        guard is supposed to reject. Routed through `zsh()` this test would
        die inside `assertSandboxed` - passing for a reason that has nothing
        to do with `mktemp`, while appearing to cover it. The guard is right;
        the fixture has to go around it.
        """
        env = dict(self.env)
        env.pop("TMPDIR")
        r = subprocess.run([str(self.bin / "mktemp"), "-d"],
                           env=env, cwd=str(self.td),
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0,
                            f"mktemp allocated with no TMPDIR set: {r.stdout!r}")
        self.assertEqual(r.stdout.strip(), "",
                         "mktemp printed a path despite having no TMPDIR")


class RealScannerGateWiringTests(_Gate):
    """Run real archive bytes through the real scanner *from the gate*.

    The extraction command remains a temp-only shim.  This is the missing link
    between the scanner's unit fixtures and the shell gate's shimmed ordering:
    actual malicious bytes must be rejected before the ditto marker appears.
    """

    CLEAN = [("ClaudePet.app/Contents/Info.plist", b"plist"),
             ("ClaudePet.app/Contents/MacOS/ClaudePet", b"executable")]

    def build_zip(self, name, members=(), symlinks=()):
        path = self.td / name
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in self.CLEAN + list(members):
                archive.writestr(member, data)
            for member, target in symlinks:
                info = zipfile.ZipInfo(member)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, target)
        return path

    def test_escaping_symlink_bytes_fail_before_ditto_and_cannot_touch_outside(self):
        outside = self.td / "outside-sentinel"
        outside.write_bytes(b"outside must not change\n")
        before = snapshot([outside])
        artifact = self.build_zip(
            "ClaudePet.zip",
            symlinks=[("ClaudePet.app/Contents/Resources/out",
                       "../../../../outside-sentinel")])
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_py(real_scan=True)

        rc, out = self.run_gate(artifact)

        self.assertEqual(rc, 1, out)
        self.assertEqual(self.py_gate_phases(), ["scan"])
        self.assertFalse(any(line.startswith("ditto ")
                             for line in self.logged().splitlines()),
                         "malicious bytes reached extraction before rejection")
        self.assertEqual(snapshot([outside]), before)

    def test_contained_symlink_is_a_positive_control_and_reaches_ditto(self):
        artifact = self.build_zip(
            "ClaudePet.zip",
            symlinks=[("ClaudePet.app/Contents/Resources/python-link",
                       "../MacOS/ClaudePet")])
        with zipfile.ZipFile(artifact) as archive:
            info = archive.getinfo(
                "ClaudePet.app/Contents/Resources/python-link")
        self.assertTrue(stat.S_ISLNK(info.external_attr >> 16),
                        "positive-control member is not a Unix symlink")
        self.setup_ditto(["ClaudePet.app/"])
        self.setup_py(real_scan=True)

        rc, out = self.run_gate(artifact)

        self.assertEqual(rc, 0, out)
        self.assertEqual(self.py_gate_phases(), ["scan", "pet", "app"])
        self.assertTrue(any(line.startswith("ditto ")
                            for line in self.logged().splitlines()),
                        "a safe contained symlink never reached extraction")


class ArchiveScannerRealFixtureTests(SandboxedShell):
    """The scanner against real archive bytes, not a shimmed verdict.

    Everywhere else in this module `$PY` is a shim, which is right: those tests
    are about the *gate's wiring* - which check runs, in what order, with what
    arguments - and a shim is the only way to drive each branch. But the
    scanner's entire job is reading an archive. Handing it a pre-computed
    answer tests the harness and nothing else.

    So this class runs the real `verify_release_artifact.py scan` against
    archives crafted here, member by member. No shell and no gate fragment is
    involved: the subject is the scanner.

    Safe to run: every artifact is written inside a temp directory, and `scan`
    reads the archive without extracting it - that is the property under test.
    """

    def setUp(self):
        super().setUp()
        assert_reviewed_file(self, RELEASE_VERIFIER, REVIEWED_VERIFIER_SHA256)
        assert_reviewed_file(self, APP_SOURCE, REVIEWED_APP_SOURCE_SHA256)

    def scan(self, artifact):
        self.assertSandboxed(self.env)
        return subprocess.run(
            [sys.executable, "-I", "-B", str(RELEASE_VERIFIER),
             "scan", str(artifact)],
            cwd=str(self.td), env=self.env,
            capture_output=True, text=True, timeout=60)

    def build_zip(self, name, members, symlinks=()):
        path = self.td / name
        with zipfile.ZipFile(path, "w") as zf:
            for member, data in members:
                zf.writestr(member, data)
            for member, target in symlinks:
                info = zipfile.ZipInfo(member)
                # The high bits are what make this a symlink rather than a
                # file. Writing the target as the member's *content* is how a
                # zip stores a link, so a scanner that only looks at names
                # cannot see where this points.
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(info, target)
        return path

    CLEAN = [("ClaudePet.app/Contents/Info.plist", "x"),
             ("ClaudePet.app/Contents/MacOS/ClaudePet", "x")]

    def test_a_clean_archive_is_accepted(self):
        """The control. Without it every rejection below could be a blanket no."""
        r = self.scan(self.build_zip("clean.zip", self.CLEAN))
        self.assertEqual(r.returncode, 0,
                         f"a clean archive was rejected: {r.stdout}{r.stderr}")

    def test_a_traversing_member_is_rejected(self):
        r = self.scan(self.build_zip("traverse.zip", self.CLEAN + [
            ("../../../../Library/LaunchAgents/evil.plist", "x")]))
        self.assertNotEqual(r.returncode, 0,
                            "an archive escaping via `..` was accepted")

    def test_an_absolute_member_is_rejected(self):
        r = self.scan(self.build_zip("absolute.zip", self.CLEAN + [
            ("/tmp/claudepet-evil", "x")]))
        self.assertNotEqual(r.returncode, 0,
                            "an archive with an absolute member was accepted")

    def test_a_symlink_member_escaping_the_archive_is_rejected(self):
        """The member kind a name-only scan cannot see.

        The name `ClaudePet.app/Contents/Resources/out` is entirely innocent;
        the escape is in the *content*, which is the link target. This is the
        case that separates a scanner reading entries from one reading names.
        """
        r = self.scan(self.build_zip(
            "symlink.zip", self.CLEAN,
            symlinks=[("ClaudePet.app/Contents/Resources/out",
                       "../../../../../../etc/passwd")]))
        self.assertNotEqual(r.returncode, 0,
                            "an archive carrying an escaping symlink was "
                            "accepted")

    def test_a_contained_relative_symlink_is_accepted(self):
        r = self.scan(self.build_zip(
            "contained-symlink.zip", self.CLEAN,
            symlinks=[("ClaudePet.app/Contents/Resources/python-link",
                       "../MacOS/ClaudePet")]))
        self.assertEqual(r.returncode, 0,
                         f"a contained bundle symlink was rejected: "
                         f"{r.stdout}{r.stderr}")

    def test_the_symlink_fixture_really_is_a_symlink(self):
        """Discrimination: if the entry is a plain file, the test above is a lie.

        `external_attr` is easy to get wrong, and a rejection would then come
        from something else entirely - or the archive would be clean and the
        assertion would fail for the right-looking wrong reason. Read the mode
        bits back out of the archive.
        """
        path = self.build_zip(
            "symlink.zip", self.CLEAN,
            symlinks=[("ClaudePet.app/Contents/Resources/out", "../../etc")])
        with zipfile.ZipFile(path) as zf:
            info = zf.getinfo("ClaudePet.app/Contents/Resources/out")
        self.assertTrue(
            stat.S_ISLNK(info.external_attr >> 16),
            "the fixture entry is not stored as a symlink, so the rejection "
            "test above proves nothing about symlink handling")

    def test_a_missing_artifact_is_rejected_rather_than_skipped(self):
        r = self.scan(self.td / "nope.zip")
        self.assertNotEqual(r.returncode, 0,
                            "a nonexistent artifact passed the scan")


class AssetNameCouplingTests(unittest.TestCase):
    """`release.sh` and `claude_pet.py` hardcode the same filenames separately.

    `release.sh` names what it uploads (`ZIP`, `UZIP`); `UPDATE_ASSET_NAMES` in
    `claude_pet.py` names what the updater will accept. **Nothing checks that
    the two agree**, and they are edited by different people for different
    reasons.

    The failure is silent and total. Rename one side and `select_update_asset`
    matches nothing, `check_github_update` returns `'failed'`, and `'failed'`
    deliberately does not burn the poll cooldown - so **every installed copy
    retries every six hours, forever, and no diagnostic is produced anywhere**.
    Nobody gets an error; updates simply stop existing.

    This is the cheapest possible check for one of the most expensive possible
    outcomes, which is the argument for it existing at all.
    """

    def test_every_zip_release_builds_is_one_the_updater_will_accept(self):
        accepted = {n.lower()
                    for names in updater_asset_names().values()
                    for n in names}
        built = release_sh_asset_names()
        for var in ("ZIP", "UZIP"):
            with self.subTest(var=var):
                self.assertIn(
                    built[var].lower(), accepted,
                    f"release.sh uploads {built[var]!r} as {var}, which is not "
                    f"in UPDATE_ASSET_NAMES ({sorted(accepted)}). Every "
                    "installed copy would poll forever and find nothing, with "
                    "no error shown to anyone.")

    def test_every_name_the_updater_accepts_is_one_release_builds(self):
        """The other direction, which is a different failure.

        An accepted name nobody builds is not silent-forever, but it means the
        updater's allow-list describes an artifact that does not exist - so a
        reader cannot use it to learn what ships, and a future `select` change
        can pick a name that will never appear.
        """
        built = {n.lower() for n in release_sh_asset_names().values()}
        for arch, names in updater_asset_names().items():
            for name in names:
                with self.subTest(arch=arch, name=name):
                    self.assertIn(
                        name.lower(), built,
                        f"UPDATE_ASSET_NAMES accepts {name!r} but release.sh "
                        "never builds an artifact by that name")

    def test_this_module_reads_the_real_names_rather_than_its_own_copy(self):
        """My own blindness to the same coupling, pinned.

        `PublishBehaviourTests.PUBLISH_VARS` used to re-declare `ZIP`/`UZIP`/
        `DMG`/`UDMG` as literals. That made the publish tests pass regardless of
        what `release.sh` actually names - the suite written to catch this bug
        contained it. The prelude is now generated from `release.sh`, and this
        asserts it stays that way.
        """
        built = release_sh_asset_names()
        prelude = PublishBehaviourTests.PUBLISH_VARS
        for var, name in built.items():
            with self.subTest(var=var):
                self.assertIn(
                    name, prelude,
                    f"the publish prelude does not carry release.sh's {var} "
                    f"({name!r}), so these tests would not notice a rename")


class FragmentCompletenessTests(unittest.TestCase):
    """The brace-match technique's blind spot, checked as a class of defect.

    Extracting one function by brace-matching gives us the code under test
    without `release.sh`'s dispatch - that is the whole point, and it is what
    keeps this suite from ever reaching `sign` or `notarize`. The cost is that
    **everything the function calls from the top level comes along as nothing
    at all.**

    A missing shell function does not raise. `$(cur_version)` with no
    `cur_version` defined expands to the empty string, and the gate then passed
    `--expect-version ''` - the one value the updater's preflight rejects
    outright - while every test stayed green, because the checker was a shim
    that exits 0 whatever it is handed. A whole suite green on an argument that
    would fail in production.

    Fixing that one instance fixes one instance. This test asks the general
    question instead: **is every top-level function the fragments call either
    carried in the fragment or stubbed in the prelude?** It fails on the next
    one before anybody has to notice it by hand.
    """

    #: Callees that are deliberately absent, with the reason. A name here is a
    #: decision that the fragment must NOT reach it.
    ALLOWED_ABSENT = {}

    def top_level_functions(self):
        return set(re.findall(r"^([a-z_][a-z0-9_]*)\(\)", RELEASE_SH.read_text(),
                              re.M))

    @staticmethod
    def strip_comments(text):
        """Whole-line comments only - `#` inside a string is not a comment."""
        return "\n".join(l for l in text.splitlines()
                         if not l.lstrip().startswith("#"))

    def callees(self, fragment, defined):
        """Top-level function names invoked from `fragment` but not defined in it."""
        body = self.strip_comments(fragment)
        found = set()
        for name in self.top_level_functions() - defined:
            # In command position: start of line/command, or inside $( ).
            if re.search(r"(?:^|[;&|(]|\$\(|\s)%s(?:\s|$|\))" % re.escape(name),
                         body, re.M):
                found.add(name)
        return found

    def assertFragmentIsSelfContained(self, names, prelude, label):
        text = RELEASE_SH.read_text()
        fragment = "\n".join(extract_function(text, n) for n in names)
        stubbed = set(re.findall(r"^([a-z_][a-z0-9_]*)\(\)", prelude, re.M))
        missing = self.callees(fragment, set(names)) - stubbed
        missing -= set(self.ALLOWED_ABSENT)
        self.assertEqual(
            missing, set(),
            f"the {label} fragment calls {sorted(missing)}, which "
            f"`release.sh` defines at top level but the fragment does not "
            "carry and the prelude does not stub. A missing shell function is "
            "not an error - it expands to nothing - so these run as empty "
            "values and the tests stay green.")

    def test_the_gate_fragment_is_self_contained(self):
        self.assertFragmentIsSelfContained(
            [FUNCTION], _Gate.PRELUDE, "verify_upload_artifact")

    def test_the_publish_fragment_is_self_contained(self):
        self.assertFragmentIsSelfContained(
            [FUNCTION, "publish"],
            _Gate.PRELUDE + PublishBehaviourTests.PUBLISH_VARS,
            "publish")

    def test_this_check_can_actually_detect_a_missing_callee(self):
        """Discrimination: otherwise a broken regex reports self-contained.

        The two tests above pass when the preludes are right AND when this
        detector is blind - identical results, opposite meanings. So drop the
        stub from a copy of the prelude and require the detector to notice.
        """
        text = RELEASE_SH.read_text()
        fragment = extract_function(text, FUNCTION)
        self.assertIn(
            "cur_version", self.callees(fragment, {FUNCTION}),
            "the detector cannot see `cur_version` being called from "
            "verify_upload_artifact, so it would not have caught the defect it "
            "was written for")


class PublishWiringTests(unittest.TestCase):
    """`publish` must gate every file before any `gh` call.

    Text-only, and kept as a cheap structural pin *in addition to*
    `PublishBehaviourTests`, which is what actually establishes the claim.
    Text cannot see a status swallowed at runtime; these two assertions would
    hold for an implementation that still reached `gh`.
    """

    def setUp(self):
        self.text = RELEASE_SH.read_text()

    def test_publish_verifies_before_it_uploads(self):
        pub = extract_function(self.text, "publish")
        verify_at = pub.find(FUNCTION)
        gh_at = pub.find("gh release")
        self.assertNotEqual(verify_at, -1, "publish does not gate its uploads")
        self.assertNotEqual(gh_at, -1)
        self.assertLess(verify_at, gh_at,
                        "publish uploads before verifying the artifacts")

    def test_publish_aborts_on_a_failed_verification(self):
        pub = extract_function(self.text, "publish")
        line = next((l for l in pub.splitlines() if FUNCTION in l), "")
        self.assertTrue(
            "||" in line and ("exit" in line or "return" in line),
            f"a failed verification must stop the publish, got: {line.strip()!r}")


if __name__ == "__main__":
    unittest.main()
