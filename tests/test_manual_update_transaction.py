"""Temp-only behavioural gates for ``build_app.sh`` install/update transactions.

This module deliberately does *not* source or execute ``build_app.sh``.  It reads the
file as text, extracts the reviewed ``update_installed`` function (and, for one test,
one dispatch arm), and writes an isolated zsh fragment under a newly-created temporary
directory.  The two absolute tools used by the function are replaced exactly once with
temporary Python shims.  ``cp``, ``mv``, and ``rm`` are also wrapped by a helper that
rejects every operand outside that temporary directory.

The reviewed-source hash is a safety boundary, not a product assertion.  If
``build_app.sh`` changes, these behavioural tests refuse to execute any extracted shell
until a verifier has read the new function and updated the hash and exact-count anchors.
That makes a newly-added absolute command or destructive path a review event instead of
something this harness discovers by running it.

No test in this file may address /Applications, the real user home, a signing identity,
or a running application.  Signing, process stopping, launching, xattr, payload
verification, ditto, and PlistBuddy are all temp-local shims.
"""

from __future__ import annotations

import hashlib
import os
import plistlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO / "build_app.sh"
APP_SOURCE = REPO / "claude_pet.py"
REVIEWED_BUILD_APP_SHA256 = (
    "db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b"
)
REVIEWED_APP_SOURCE_SHA256 = (
    "26d8d041cdb4179e892847c7dbc6066ccd45181e4cf77ffb2193072fc70a963d"
)


def _current_app_version() -> str:
    text = APP_SOURCE.read_text()
    match = re.search(r'^APP_VERSION = "([^"]+)"', text, re.M)
    if not match:
        raise AssertionError("claude_pet.py has no literal APP_VERSION")
    return match.group(1)


APP_VERSION = _current_app_version()


def _replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"reviewed mutation anchor changed: expected {count} occurrence(s) of "
            f"{old!r}, found {actual}"
        )
    return text.replace(old, new, count)


def _extract_function(source: str, name: str) -> str:
    """Extract one zsh ``name() { ... }`` definition without evaluating it."""
    header = f"{name}() {{"
    if source.count(header) != 1:
        raise AssertionError(f"expected exactly one {header!r}")
    start = source.index(header)
    depth = 0
    saw_open = False
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
            saw_open = True
        elif char == "}":
            depth -= 1
            if saw_open and depth == 0:
                fragment = source[start : index + 1]
                if not fragment.rstrip().endswith("}"):
                    raise AssertionError(f"could not isolate {name}")
                return fragment
    raise AssertionError(f"unterminated function {name}")


def _extract_case_arm(source: str, label: str) -> str:
    anchor = f"\n  {label})\n"
    terminator = "\n    ;;\n"
    if source.count(anchor) != 1:
        raise AssertionError(f"expected exactly one {label!r} dispatch arm")
    remainder = source.split(anchor, 1)[1]
    if terminator not in remainder:
        raise AssertionError(f"unterminated {label!r} dispatch arm")
    return remainder.split(terminator, 1)[0]


def _reviewed_update_function(source: str, *, fail_publish: bool = False) -> str:
    fragment = _extract_function(source, "update_installed")

    # These are the only absolute executable paths in the reviewed function.  Never
    # let the extracted fragment call either real tool.
    fragment = _replace_exact(fragment, "/usr/bin/ditto", '"${TEST_DITTO}"')
    fragment = _replace_exact(
        fragment, "/usr/libexec/PlistBuddy", '"${TEST_PLISTBUDDY}"'
    )

    # The hook is inert except in the code-tamper and concurrency fixtures.  Anchors
    # are exact so a production reordering cannot silently change the test schedule.
    preflight_anchor = "\n  # ── 5. 바꾸기 '전에' 완성본을 확인한다"
    fragment = _replace_exact(
        fragment,
        preflight_anchor,
        '\n  txn_hook after_prepare "$dest" "$stage" "$backup" || return 1'
        + preflight_anchor,
    )
    finish_anchor = '\n  rm -rf "$backup"\n}'
    fragment = _replace_exact(
        fragment,
        finish_anchor,
        '\n  txn_hook before_finish "$dest" "$stage" "$backup" || return 1'
        + finish_anchor,
    )

    if fail_publish:
        fragment = _replace_exact(
            fragment,
            'if ! mv "$stage" "$dest"; then',
            'if ! test_fail_stage_publish "$stage" "$dest"; then',
        )

    # Hash pinning is the primary safety boundary; these rejects make the intended
    # blast radius readable in the test itself as well.
    code = "\n".join(line.split("#", 1)[0] for line in fragment.splitlines())
    forbidden = (
        "/Applications",
        "/Users/",
        "${HOME}",
        "$HOME",
        "~/",
        "source ",
        "eval ",
        "sudo ",
        "command ",
        "builtin ",
        "/usr/bin/ditto",
        "/usr/libexec/PlistBuddy",
    )
    found = [token for token in forbidden if token in code]
    if found:
        raise AssertionError(f"unsafe or unreviewed extracted shell token(s): {found}")
    return fragment


def _reviewed_install_arm(source: str) -> str:
    arm = _extract_case_arm(source, "__install_txn")
    # Inject a failed installation copy without ever addressing a real app.  This is
    # the reviewed arm's sole publish copy.  A refactor must be re-reviewed instead of
    # being guessed at by the harness.
    return _replace_exact(
        arm,
        'cp -R "$APP" "$DEST"',
        'test_fail_install_copy "$APP" "$DEST"',
    )


def _reviewed_public_lock_fragment(source: str, label: str) -> tuple[str, str]:
    """Public install/update wrapper with the Python entrypoint redirected.

    The returned text has no bottom dispatch and cannot build or install by
    itself.  If it wins the lock it can only execute ``$SELF``, which each
    fixture points at a temp-local marker/barrier helper.
    """
    if label not in {"install", "update"}:
        raise AssertionError(f"unsupported public lock arm: {label}")
    wrapper = _extract_function(source, "run_under_update_lock")
    wrapper = _replace_exact(
        wrapper,
        '"${PYCHECK:-python3}" claude_pet.py \\\n',
        '"${PYCHECK:-python3}" "$TEST_APP_SOURCE" \\\n',
    )
    note = _extract_function(source, "lock_rc_note")
    arm = _extract_case_arm(source, label)
    fragment = wrapper + "\n" + note + "\n" + arm
    code = "\n".join(line.split("#", 1)[0] for line in fragment.splitlines())
    for forbidden in ("/Applications", "sudo ", "security ", "codesign ",
                      "open ", "gh ", "curl "):
        if forbidden in code:
            raise AssertionError(f"unsafe public wrapper token: {forbidden}")
    return wrapper + "\n" + note + "\n", arm


def _reviewed_build_lock_fragment(source: str) -> str:
    names = ("build_lock_path", "acquire_build_lock",
             "release_build_lock", "build")
    fragment = "\n".join(_extract_function(source, name) for name in names)
    code = "\n".join(line.split("#", 1)[0] for line in fragment.splitlines())
    for forbidden in ("/Applications", "sudo ", "security ", "codesign ",
                      "open ", "source ", "eval "):
        if forbidden in code:
            raise AssertionError(f"unsafe build-lock fragment token: {forbidden}")
    return fragment


def _reviewed_sign_function(source: str) -> str:
    fragment = _extract_function(source, "sign_app")
    code = "\n".join(line.split("#", 1)[0] for line in fragment.splitlines())
    for forbidden in ("/Applications", "sudo ", "open ", "gh ", "curl "):
        if forbidden in code:
            raise AssertionError(f"unsafe sign fragment token: {forbidden}")
    return fragment


SAFE_OPS = r'''#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(os.environ["TEST_ROOT"]).resolve()

def checked(value):
    path = Path(value)
    if not path.is_absolute():
        path = Path.cwd() / path
    lexical = Path(os.path.abspath(path))
    resolved = Path(os.path.realpath(path))
    for candidate in (lexical, resolved):
        try:
            common = Path(os.path.commonpath((str(root), str(candidate))))
        except ValueError:
            raise SystemExit(f"path escaped temp root: {value}")
        if common != root:
            raise SystemExit(f"path escaped temp root: {value}")
    return path

operation, *arguments = sys.argv[1:]
paths = [value for value in arguments if not value.startswith("-")]
for value in paths:
    checked(value)

if operation in {"cp", "mv", "rm", "mkdir", "cat"}:
    executable = {"cp": "/bin/cp", "mv": "/bin/mv", "rm": "/bin/rm",
                  "mkdir": "/bin/mkdir", "cat": "/bin/cat"}[operation]
    raise SystemExit(subprocess.run([executable, *arguments], check=False).returncode)

if operation == "ditto":
    if len(arguments) != 2:
        raise SystemExit("ditto shim expects source and destination")
    source, destination = map(checked, arguments)
    if destination.exists() or destination.is_symlink():
        raise SystemExit("ditto destination already exists")
    shutil.copytree(source, destination, symlinks=True)
    raise SystemExit(0)

raise SystemExit(f"unknown safe operation: {operation}")
'''


FIXTURE_HELPER = r'''#!/usr/bin/env python3
import os
import plistlib
import shutil
import sys
import time
from pathlib import Path

root = Path(os.environ["TEST_ROOT"]).resolve()

def checked(value):
    path = Path(value)
    if not path.is_absolute():
        path = Path.cwd() / path
    lexical = Path(os.path.abspath(path))
    resolved = Path(os.path.realpath(path))
    for candidate in (lexical, resolved):
        if Path(os.path.commonpath((str(root), str(candidate)))) != root:
            raise SystemExit(f"path escaped temp root: {value}")
    return path

def touch_event(name):
    event = checked(Path(os.environ["TEST_EVENTS"]) / name)
    event.parent.mkdir(parents=True, exist_ok=True)
    event.write_text(name + "\n")

def wait_for(name):
    target = checked(Path(os.environ["TEST_EVENTS"]) / name)
    deadline = time.monotonic() + 12
    while not target.exists():
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for {name}")
        time.sleep(0.02)

action, *arguments = sys.argv[1:]

if action == "seed":
    app = checked(arguments[0])
    payload = checked(app / "Contents/Resources/.claude_pet")
    if payload.is_symlink() or payload.is_file():
        payload.unlink()
    elif payload.exists():
        shutil.rmtree(payload)
    (payload / "pets/dog").mkdir(parents=True)
    (payload / "README.md").write_text("bundled pet payload\n")
    (payload / "pets/dog/pet.json").write_text('{"id":"dog"}\n')
    raise SystemExit(0)

if action == "fonts":
    # Stand-in for build_app.sh's copy_fonts(): the staged bundle gets a fonts/
    # directory with the two files the real function insists on.  Nothing is
    # copied from the repository, so the harness stays inside the temp root.
    app = checked(arguments[0])
    fonts = checked(app / "Contents/Resources/fonts")
    if fonts.is_symlink() or fonts.is_file():
        fonts.unlink()
    elif fonts.exists():
        shutil.rmtree(fonts)
    fonts.mkdir(parents=True)
    # TrueType magic (00 01 00 00): the same file shape verify_release_artifact.py accepts.
    (fonts / "Pretendard-SemiBold.ttf").write_bytes(b"\x00\x01\x00\x00 stub font\n")
    (fonts / "LICENSE-Pretendard.txt").write_text("OFL stub\n")
    raise SystemExit(0)

if action == "write-plist":
    app = checked(arguments[0])
    mode = os.environ.get("TEST_PLIST_MODE", "correct")
    short = os.environ["TEST_APP_VERSION"]
    build = os.environ["TEST_APP_VERSION"]
    if mode == "bad-short":
        short = "wrong-short-version"
    elif mode == "bad-build":
        build = "wrong-build-version"
    elif mode != "correct":
        raise SystemExit(f"unknown plist mode: {mode}")
    path = checked(app / "Contents/Info.plist")
    with path.open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleExecutable": "ClaudePet",
                "CFBundleIdentifier": "me.yeongyu.claudepet",
                "CFBundleShortVersionString": short,
                "CFBundleVersion": build,
            },
            handle,
        )
    raise SystemExit(0)

if action == "ident":
    path = checked(arguments[0])
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise SystemExit(1)
    print(f"{info.st_dev}:{info.st_ino}")
    raise SystemExit(0)

if action == "verify":
    path = checked(arguments[0])
    raise SystemExit(0 if path.is_dir() and not path.is_symlink() else 1)

if action == "append":
    touch_event(arguments[0])
    raise SystemExit(0)

if action == "hold":
    touch_event(arguments[0])
    wait_for(arguments[1])
    raise SystemExit(0)

if action == "hook":
    label, app, stage, backup = arguments
    checked(app); checked(stage); checked(backup)
    role = os.environ.get("TEST_ROLE", "single")
    mode = os.environ.get("TEST_HOOK_MODE", "none")
    if mode == "tamper-code" and label == "after_prepare":
        code = checked(Path(stage) / "Contents/Resources/claude_pet.py")
        code.write_text("tampered staged code\n")
    if mode in {"tamper-exe-symlink", "tamper-exe-directory"} \
            and label == "after_prepare":
        executable = checked(Path(stage) / "Contents/MacOS/ClaudePet")
        executable.unlink()
        if mode == "tamper-exe-symlink":
            target = checked(Path(os.environ["TEST_ROOT"]) / "contained-exe-target")
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o700)
            executable.symlink_to(target)
        else:
            executable.mkdir()
            executable.chmod(0o700)
    if mode == "concurrency" and role == "A" and label == "before_finish":
        touch_event("A.before_finish")
        wait_for("allow.A.finish")
    raise SystemExit(0)

raise SystemExit(f"unknown fixture action: {action}")
'''


DITTO_SHIM = r'''#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from pathlib import Path

events = Path(os.environ["TEST_EVENTS"])
role = os.environ.get("TEST_ROLE", "single")
mode = os.environ.get("TEST_HOOK_MODE", "none")

if mode == "concurrency":
    (events / f"{role}.ditto").write_text(role + "\n")
    allow = events / f"allow.{role}.ditto"
    deadline = time.monotonic() + 12
    while not allow.exists():
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for {allow.name}")
        time.sleep(0.02)

raise SystemExit(
    subprocess.run(
        [os.environ["TEST_PYTHON"], os.environ["TEST_SAFE_OPS"],
         "ditto", *sys.argv[1:]],
        check=False,
    ).returncode
)
'''


PLISTBUDDY_SHIM = r'''#!/usr/bin/env python3
import os
import plistlib
import sys
from pathlib import Path

root = Path(os.environ["TEST_ROOT"]).resolve()
if len(sys.argv) != 4 or sys.argv[1] != "-c" or not sys.argv[2].startswith("Print :"):
    raise SystemExit("unexpected PlistBuddy invocation")
path = Path(sys.argv[3])
resolved = Path(os.path.realpath(path))
if Path(os.path.commonpath((str(root), str(resolved)))) != root:
    raise SystemExit("plist path escaped temp root")
with path.open("rb") as handle:
    value = plistlib.load(handle)[sys.argv[2].split(":", 1)[1]]
print(value)
'''


SHELL_PRELUDE = r'''
set -e
setopt NO_GLOBAL_RCS
CDPATH=""
APP_VERSION="$TEST_APP_VERSION"

safe_op() { "$TEST_PYTHON" "$TEST_SAFE_OPS" "$@"; }
cp() { safe_op cp "$@"; }
mv() { safe_op mv "$@"; }
rm() { safe_op rm "$@"; }
mkdir() { safe_op mkdir "$@"; }
cat() { safe_op cat "$@"; }
# The reviewed lock loops only use signal 0.  Treat every recorded holder as
# alive without signalling an ambient process; disappearance of the temp-local
# lock directory is what permits the waiter to continue.
kill() { [ "$1" = "-0" ] || return 97; return 0; }

copy_pet_assets() { "$TEST_PYTHON" "$TEST_HELPER" seed "$1"; }
copy_fonts() { "$TEST_PYTHON" "$TEST_HELPER" fonts "$1"; }
write_plist() { "$TEST_PYTHON" "$TEST_HELPER" write-plist "$1"; }
sign_app() { "$TEST_PYTHON" "$TEST_HELPER" append sign; }
stop_pet() { "$TEST_PYTHON" "$TEST_HELPER" append stop; }
path_ident() { "$TEST_PYTHON" "$TEST_HELPER" ident "$1"; }
txn_hook() {
  "$TEST_PYTHON" "$TEST_HELPER" hook "$1" "$2" "$3" "$4"
}
test_fail_stage_publish() { return 86; }
test_fail_install_copy() { return 87; }
build() { "$TEST_PYTHON" "$TEST_HELPER" append build; }
acquire_build_lock() {
  CLAUDEPET_BUILD_LOCK="$TEST_ROOT/stub-build.lock"; return 0
}
release_build_lock() { CLAUDEPET_BUILD_REENTRY=0; CLAUDEPET_BUILD_LOCK=""; }
require_update_lock() { [ "$CLAUDEPET_UPDATE_LOCK_HELD" = "1" ]; }
open() { "$TEST_PYTHON" "$TEST_HELPER" append "launch.$1"; }
xattr() { "$TEST_PYTHON" "$TEST_HELPER" append xattr; }

# If an extracted fragment unexpectedly reaches any of these, fail closed.  The real
# tools are never invoked.
sudo() { return 97; }
security() { return 97; }
codesign() { return 97; }
pkill() { return 97; }
killall() { return 97; }
curl() { return 97; }
gh() { return 97; }
osascript() { return 97; }
'''


class TransactionSandbox:
    def __init__(self, source: str):
        self.source = source
        self._temporary = tempfile.TemporaryDirectory(prefix="manual-update-txn-")
        self.root = Path(self._temporary.name).resolve()
        self.home = self.root / "home"
        self.tmp = self.root / "tmp"
        self.zdot = self.root / "zdot"
        self.apps = self.root / "apps"
        self.events = self.root / "events"
        for path in (self.home, self.tmp, self.zdot, self.apps, self.events):
            path.mkdir()

        self.source_code = self.root / "claude_pet.py"
        self.source_code.write_text(
            f'APP_VERSION = "{APP_VERSION}"\nBUILD_TOKEN = "expected-new-code"\n'
        )
        (self.root / "verify_pet_payload.py").write_text("# shim target only\n")

        self.safe_ops = self._tool("safe_ops.py", SAFE_OPS)
        self.helper = self._tool("fixture_helper.py", FIXTURE_HELPER)
        self.ditto = self._tool("ditto.py", DITTO_SHIM)
        self.plistbuddy = self._tool("plistbuddy.py", PLISTBUDDY_SHIM)
        self.pycheck = self._tool(
            "pycheck.py",
            '#!/usr/bin/env python3\nimport os, subprocess, sys\n'
            'raise SystemExit(subprocess.run([os.environ["TEST_PYTHON"], '
            'os.environ["TEST_HELPER"], "verify", sys.argv[2]], '
            'check=False).returncode)\n',
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._temporary.cleanup()

    def _tool(self, name: str, content: str) -> Path:
        path = self.root / name
        rendered = textwrap.dedent(content).lstrip()
        if rendered.startswith("#!/usr/bin/env python3\n"):
            rendered = f"#!{sys.executable}\n" + rendered.split("\n", 1)[1]
        path.write_text(rendered)
        path.chmod(0o700)
        return path

    def environment(self, **overrides: str) -> dict[str, str]:
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.home),
            "TMPDIR": f"{self.tmp}/",
            "ZDOTDIR": str(self.zdot),
            "CDPATH": "",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYCHECK": str(self.pycheck),
            "TEST_APP_VERSION": APP_VERSION,
            "TEST_APP_SOURCE": str(APP_SOURCE),
            "TEST_DITTO": str(self.ditto),
            "TEST_EVENTS": str(self.events),
            "TEST_HELPER": str(self.helper),
            "TEST_HOOK_MODE": "none",
            "TEST_PLISTBUDDY": str(self.plistbuddy),
            "TEST_PLIST_MODE": "correct",
            "TEST_PYTHON": sys.executable,
            "TEST_ROOT": str(self.root),
            "TEST_SAFE_OPS": str(self.safe_ops),
        }
        environment.update({key: str(value) for key, value in overrides.items()})
        return environment

    def make_bundle(self, path: Path, *, code: bytes = b"old installed code\n") -> Path:
        resources = path / "Contents/Resources"
        macos = path / "Contents/MacOS"
        (resources / ".claude_pet/pets/dog").mkdir(parents=True)
        macos.mkdir(parents=True)
        (resources / "claude_pet.py").write_bytes(code)
        (resources / ".claude_pet/README.md").write_text("old payload\n")
        (resources / ".claude_pet/pets/dog/pet.json").write_text('{"id":"dog"}\n')
        with (path / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump(
                {
                    "CFBundleExecutable": "ClaudePet",
                    "CFBundleIdentifier": "me.yeongyu.claudepet",
                    "CFBundleShortVersionString": "0.19",
                    "CFBundleVersion": "0.19",
                },
                handle,
            )
        executable = macos / "ClaudePet"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        (path / "old-install.marker").write_text("old install\n")
        return path

    def write_update_script(
        self, *, fail_publish: bool = False, with_update_dispatch: bool = False
    ) -> Path:
        function = _reviewed_update_function(self.source, fail_publish=fail_publish)
        body = [SHELL_PRELUDE, function]
        if with_update_dispatch:
            arm = _extract_case_arm(self.source, "update")
            body.append(
                '\nDEST="$1"\ncase update in\n  update)\n'
                + arm
                + "\n    ;;\nesac\n"
            )
        else:
            body.append('\nupdate_installed "$1"\n')
        return self._tool("run_update.zsh", "\n".join(body))

    def write_install_script(self, app: Path) -> Path:
        arm = _reviewed_install_arm(self.source)
        return self._tool(
            "run_install.zsh",
            SHELL_PRELUDE
            + f"\nAPP={self._shell_quote(str(app))}\n"
            + 'CLAUDEPET_UPDATE_LOCK_HELD=1\n'
            + 'DEST="$1"\ncase install in\n  install)\n'
            + arm
            + "\n    ;;\nesac\n",
        )

    def write_public_lock_script(self, label: str, child: Path) -> Path:
        functions, arm = _reviewed_public_lock_fragment(self.source, label)
        return self._tool(
            f"run_public_{label}.zsh",
            "set -e\nsetopt NO_GLOBAL_RCS\nCDPATH=\"\"\n"
            + functions
            + f"SELF={self._shell_quote(str(child))}\n"
            + 'DEST="$1"\n'
            + f"case {label} in\n  {label})\n"
            + arm
            + "\n    ;;\nesac\n",
        )

    def write_lock_child(self, name: str, *, hold: bool) -> Path:
        if hold:
            command = (
                '"$TEST_PYTHON" "$TEST_HELPER" hold manual.held allow.manual\n'
            )
        else:
            command = f'"$TEST_PYTHON" "$TEST_HELPER" append {name}\n'
        return self._tool(name + ".zsh", "#!/bin/zsh\nset -e\n" + command)

    def popen_cli_lock_holder(
        self, destination: Path, held: str, release: str
    ) -> subprocess.Popen[str]:
        self._assert_temp_path(destination)
        return subprocess.Popen(
            [sys.executable, "-I", "-B", str(APP_SOURCE),
             "--with-update-lock", str(destination), "--",
             str(self.helper), "hold", held, release],
            cwd=self.root,
            env=self.environment(PYCHECK=sys.executable),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

    @staticmethod
    def _shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    def run_script(
        self, script: Path, destination: Path, **environment: str
    ) -> subprocess.CompletedProcess[str]:
        self._assert_temp_path(destination)
        return subprocess.run(
            ["/bin/zsh", "-f", str(script), str(destination)],
            cwd=self.root,
            env=self.environment(**environment),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def popen_update(
        self, script: Path, destination: Path, *, role: str
    ) -> subprocess.Popen[str]:
        self._assert_temp_path(destination)
        return subprocess.Popen(
            ["/bin/zsh", "-f", str(script), str(destination)],
            cwd=self.root,
            env=self.environment(TEST_HOOK_MODE="concurrency", TEST_ROLE=role),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

    def event(self, name: str) -> Path:
        return self.events / name

    def release(self, name: str) -> None:
        self.event(name).write_text(name + "\n")

    def wait_event(self, name: str, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        path = self.event(name)
        while time.monotonic() < deadline:
            if path.exists():
                return True
            time.sleep(0.02)
        return path.exists()

    def _assert_temp_path(self, path: Path) -> None:
        candidate = Path(os.path.abspath(path))
        common = Path(os.path.commonpath((str(self.root), str(candidate))))
        if common != self.root:
            raise AssertionError(f"test path escaped its temp root: {path}")


def _tree_snapshot(path: Path):
    """Include type, link target, bytes, and metadata to detect outside writes."""
    entries = []
    if not path.exists() and not path.is_symlink():
        return tuple(entries)
    roots = [path]
    if path.is_dir() and not path.is_symlink():
        roots.extend(sorted(path.rglob("*")))
    for entry in roots:
        info = entry.lstat()
        relative = "." if entry == path else str(entry.relative_to(path))
        kind = stat.S_IFMT(info.st_mode)
        target = os.readlink(entry) if entry.is_symlink() else None
        content = entry.read_bytes() if entry.is_file() and not entry.is_symlink() else None
        entries.append(
            (relative, kind, stat.S_IMODE(info.st_mode), info.st_ino, info.st_mtime_ns,
             target, content)
        )
    return tuple(entries)


class ReviewedBuildScriptMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Hash and execute from the same immutable byte snapshot.  A developer may be
        # editing the shared working tree while this verifier suite starts; reading the
        # path once avoids a hash/read TOCTOU window.
        source_bytes = BUILD_SCRIPT.read_bytes()
        actual = hashlib.sha256(source_bytes).hexdigest()
        if actual != REVIEWED_BUILD_APP_SHA256:
            raise AssertionError(
                "build_app.sh changed after the verifier reviewed the extracted-shell "
                f"harness: expected {REVIEWED_BUILD_APP_SHA256}, found {actual}. "
                "Do not execute the new fragment until a verifier reviews and pins it."
            )
        cls.source = source_bytes.decode()
        app_hash = hashlib.sha256(APP_SOURCE.read_bytes()).hexdigest()
        if app_hash != REVIEWED_APP_SOURCE_SHA256:
            raise AssertionError(
                "claude_pet.py changed after the shared-lock/version harness was "
                f"reviewed: expected {REVIEWED_APP_SOURCE_SHA256}, found {app_hash}"
            )


class SharedUpdateLockTests(ReviewedBuildScriptMixin, unittest.TestCase):
    """Manual install/update and the in-app updater contend on one flock."""

    def test_in_app_holder_blocks_public_install_and_update_before_child_mutation(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            before = _tree_snapshot(destination)
            holder = box.popen_cli_lock_holder(
                destination, "inapp.held", "allow.inapp"
            )
            try:
                self.assertTrue(box.wait_event("inapp.held"),
                                "in-app lock holder never acquired the lock")
                for label in ("install", "update"):
                    with self.subTest(label=label):
                        marker = f"manual.{label}.mutated"
                        child = box.write_lock_child(marker, hold=False)
                        script = box.write_public_lock_script(label, child)
                        result = box.run_script(
                            script, destination, PYCHECK=sys.executable
                        )
                        self.assertEqual(result.returncode, 100,
                                         result.stdout + result.stderr)
                        self.assertFalse(box.event(marker).exists(),
                                         "manual transaction child ran while the "
                                         "in-app lock was held")
                        self.assertEqual(_tree_snapshot(destination), before)
            finally:
                box.release("allow.inapp")
                try:
                    out, err = holder.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(holder.pid, signal.SIGTERM)
                    out, err = holder.communicate(timeout=2)
                self.assertEqual(holder.returncode, 0, out + err)

    def test_manual_holder_blocks_a_simulated_in_app_acquire(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            before = _tree_snapshot(destination)
            child = box.write_lock_child("manual-child", hold=True)
            script = box.write_public_lock_script("update", child)
            manual = subprocess.Popen(
                ["/bin/zsh", "-f", str(script), str(destination)],
                cwd=box.root,
                env=box.environment(PYCHECK=sys.executable),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                self.assertTrue(box.wait_event("manual.held"),
                                "manual wrapper never acquired the shared lock")
                competing = subprocess.run(
                    [sys.executable, "-I", "-B", str(APP_SOURCE),
                     "--with-update-lock", str(destination), "--",
                     str(box.helper), "append", "inapp.mutated"],
                    cwd=box.root,
                    env=box.environment(PYCHECK=sys.executable),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(competing.returncode, 100,
                                 competing.stdout + competing.stderr)
                self.assertFalse(box.event("inapp.mutated").exists())
                self.assertEqual(_tree_snapshot(destination), before)
            finally:
                box.release("allow.manual")
                try:
                    out, err = manual.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(manual.pid, signal.SIGTERM)
                    out, err = manual.communicate(timeout=2)
                self.assertEqual(manual.returncode, 0, out + err)


class BuildLockCoverageTests(ReviewedBuildScriptMixin, unittest.TestCase):
    """The repo bundle is serialized for direct build and install consumption."""

    def test_direct_build_cannot_remove_shared_app_while_build_lock_is_held(self):
        with TransactionSandbox(self.source) as box:
            app = box.make_bundle(box.root / "ClaudePet.app")
            locks = _reviewed_build_lock_fragment(self.source)
            holder = box._tool(
                "hold_build_lock.zsh",
                SHELL_PRELUDE + "\n" + locks + "\n"
                + 'acquire_build_lock\n'
                + '"$TEST_PYTHON" "$TEST_HELPER" hold build.held allow.build\n'
                + 'release_build_lock\n',
            )
            direct = box._tool(
                "direct_build.zsh",
                SHELL_PRELUDE + "\n" + locks + "\n"
                + f"APP={box._shell_quote(str(app))}\n"
                + 'build_body() {\n'
                + '  "$TEST_PYTHON" "$TEST_HELPER" append direct.build.enter\n'
                + '  rm -rf "$APP"\n'
                + '}\n'
                + 'if build; then exit 0; else exit $?; fi\n',
            )
            owner = subprocess.Popen(
                ["/bin/zsh", "-f", str(holder)], cwd=box.root,
                env=box.environment(), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, start_new_session=True,
            )
            builder = None
            try:
                self.assertTrue(box.wait_event("build.held"),
                                "holder never acquired the repo build lock")
                builder = subprocess.Popen(
                    ["/bin/zsh", "-f", str(direct)], cwd=box.root,
                    env=box.environment(), stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, start_new_session=True,
                )
                entered_while_held = box.wait_event("direct.build.enter", 0.8)
                self.assertFalse(entered_while_held,
                                 "direct build entered build_body under another lock")
                self.assertTrue((app / "old-install.marker").is_file(),
                                "direct build removed the shared app while blocked")
                box.release("allow.build")
                owner_out, owner_err = owner.communicate(timeout=5)
                self.assertEqual(owner.returncode, 0, owner_out + owner_err)
                build_out, build_err = builder.communicate(timeout=8)
                self.assertEqual(builder.returncode, 0, build_out + build_err)
                self.assertTrue(box.event("direct.build.enter").exists())
                self.assertFalse(app.exists(),
                                 "positive control: direct build never performed its rm")
            finally:
                box.release("allow.build")
                for process in (owner, builder):
                    if process is not None and process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.communicate(timeout=2)

    def test_install_outer_build_lock_survives_inner_build_and_preflight_consumption(self):
        with TransactionSandbox(self.source) as box:
            app = box.make_bundle(
                box.root / "ClaudePet.app", code=box.source_code.read_bytes()
            )
            destination = box.apps / "ClaudePet.app"
            locks = _reviewed_build_lock_fragment(self.source)
            arm = _extract_case_arm(self.source, "__install_txn")
            consume_anchor = "\n    # 펫은 여기서 처음 멈춘다."
            arm = _replace_exact(
                arm,
                consume_anchor,
                '\n    "$TEST_PYTHON" "$TEST_HELPER" hold '
                'install.consuming allow.install\n'
                '    exit 0'
                + consume_anchor,
            )
            common = (
                SHELL_PRELUDE + "\n" + locks + "\n"
                + f"APP={box._shell_quote(str(app))}\n"
                + 'build_body() {\n'
                + '  if [ "$TEST_ROLE" = install ]; then\n'
                + '    "$TEST_PYTHON" "$TEST_HELPER" append install.inner_build\n'
                + '  else\n'
                + '    "$TEST_PYTHON" "$TEST_HELPER" append direct.build.enter\n'
                + '    rm -rf "$APP"\n'
                + '  fi\n'
                + '}\n'
            )
            install = box._tool(
                "outer_install_lock.zsh",
                common
                + 'CLAUDEPET_UPDATE_LOCK_HELD=1\nDEST="$1"\n'
                + 'case install in\n  install)\n' + arm + '\n    ;;\nesac\n',
            )
            direct = box._tool(
                "direct_during_install.zsh",
                common + 'if build; then exit 0; else exit $?; fi\n',
            )
            installer = subprocess.Popen(
                ["/bin/zsh", "-f", str(install), str(destination)],
                cwd=box.root, env=box.environment(TEST_ROLE="install"),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True,
            )
            builder = None
            try:
                self.assertTrue(box.wait_event("install.consuming"),
                                "install never consumed the built bundle")
                self.assertTrue(box.event("install.inner_build").exists(),
                                "inner build was not the reentrant lock path")
                builder = subprocess.Popen(
                    ["/bin/zsh", "-f", str(direct)], cwd=box.root,
                    env=box.environment(TEST_ROLE="direct"),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    start_new_session=True,
                )
                entered_while_consuming = box.wait_event("direct.build.enter", 0.8)
                self.assertFalse(
                    entered_while_consuming,
                    "inner build released the outer lock before install consumption",
                )
                self.assertTrue((app / "old-install.marker").is_file())
                box.release("allow.install")
                install_out, install_err = installer.communicate(timeout=5)
                self.assertEqual(installer.returncode, 0,
                                 install_out + install_err)
                direct_out, direct_err = builder.communicate(timeout=8)
                self.assertEqual(builder.returncode, 0,
                                 direct_out + direct_err)
                self.assertTrue(box.event("direct.build.enter").exists())
                self.assertFalse(app.exists(),
                                 "positive control: direct build did not remove APP")
            finally:
                box.release("allow.install")
                for process in (installer, builder):
                    if process is not None and process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.communicate(timeout=2)


class NestedSigningFailureTests(ReviewedBuildScriptMixin, unittest.TestCase):
    SIGN_SHIMS = r'''
security() { return 0; }
codesign() {
  print -r -- "$*" >> "$TEST_EVENTS/codesign.log"
  local last="${@[-1]}"
  if [ "$last" = "$APP/Contents/MacOS/ClaudePet_py" ] \
     && [[ "$*" = *"--sign ClaudePet Local"* ]]; then
    return 71
  fi
  if [ "$TEST_SIGN_MODE" = "adhoc_nested_fail" ] \
     && [ "$last" = "$APP/Contents/MacOS/ClaudePet_py" ] \
     && [[ "$*" = *"--sign -"* ]]; then
    return 72
  fi
  return 0
}
'''

    def _run_sign(self, box: TransactionSandbox, mode: str):
        app = box.make_bundle(box.root / "SignMe.app")
        pybin = app / "Contents/MacOS/ClaudePet_py"
        pybin.write_text("synthetic nested executable\n")
        pybin.chmod(0o700)
        fragment = _reviewed_sign_function(self.source)
        script = box._tool(
            "run_sign.zsh",
            "setopt NO_GLOBAL_RCS\nCDPATH=\"\"\n"
            + fragment + "\n" + self.SIGN_SHIMS
            + f"APP={box._shell_quote(str(app))}\n"
            + 'if sign_app; then rc=0; else rc=$?; fi\nexit $rc\n',
        )
        result = box.run_script(
            script, app, TEST_SIGN_MODE=mode
        )
        log = box.events / "codesign.log"
        calls = log.read_text().splitlines() if log.exists() else []
        return result, calls, app, pybin

    def test_local_nested_failure_falls_back_as_a_pair_not_outer_only(self):
        with TransactionSandbox(self.source) as box:
            result, calls, app, pybin = self._run_sign(box, "fallback_success")
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertEqual(len(calls), 3, calls)
            self.assertIn("--sign ClaudePet Local", calls[0])
            self.assertTrue(calls[0].endswith(str(pybin)))
            self.assertIn("--sign -", calls[1])
            self.assertTrue(calls[1].endswith(str(pybin)))
            self.assertIn("--sign -", calls[2])
            self.assertTrue(calls[2].endswith(str(app)))
            self.assertNotIn("ClaudePet Local", calls[2],
                             "outer bundle kept the local identity after nested failed")

    def test_failed_adhoc_nested_fallback_stops_before_outer_signing(self):
        with TransactionSandbox(self.source) as box:
            result, calls, app, _ = self._run_sign(box, "adhoc_nested_fail")
            self.assertNotEqual(result.returncode, 0,
                                result.stdout + result.stderr)
            self.assertEqual(len(calls), 2, calls)
            self.assertFalse(any(line.endswith(str(app)) for line in calls),
                             "outer bundle was signed after nested fallback failed")


class StagedContainmentTests(ReviewedBuildScriptMixin, unittest.TestCase):
    def test_resources_symlink_is_rejected_before_its_target_is_mutated(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            resources = destination / "Contents/Resources"
            outside = box.root / "outside-resources"
            resources.rename(outside)
            resources.symlink_to(outside, target_is_directory=True)
            before = _tree_snapshot(outside)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(_tree_snapshot(outside), before)
            self.assertTrue(resources.is_symlink())

    def test_info_plist_symlink_is_rejected_before_its_target_is_mutated(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            plist = destination / "Contents/Info.plist"
            outside = box.root / "outside-info.plist"
            plist.rename(outside)
            plist.symlink_to(outside)
            before = _tree_snapshot(outside)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(_tree_snapshot(outside), before)
            self.assertTrue(plist.is_symlink())

    def test_code_symlink_is_rejected_before_its_target_is_mutated(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            code = destination / "Contents/Resources/claude_pet.py"
            outside = box.root / "outside-code.py"
            code.rename(outside)
            code.symlink_to(outside)
            before = _tree_snapshot(outside)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(_tree_snapshot(outside), before)
            self.assertTrue(code.is_symlink())


class BackupPreservationTests(ReviewedBuildScriptMixin, unittest.TestCase):
    def test_regular_backup_is_not_deleted_when_installed_app_exists(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            backup = box.apps / ".ClaudePet.app.previous"
            backup.write_bytes(b"do not delete this wrong-type backup\n")
            before = _tree_snapshot(backup)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(_tree_snapshot(backup), before)
            self.assertEqual(
                (destination / "Contents/Resources/claude_pet.py").read_bytes(),
                b"old installed code\n",
            )

    def test_regular_backup_is_not_renamed_away_when_installed_app_is_absent(self):
        with TransactionSandbox(self.source) as box:
            destination = box.apps / "ClaudePet.app"
            backup = box.apps / ".ClaudePet.app.previous"
            backup.write_bytes(b"only remaining backup\n")
            before = _tree_snapshot(backup)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(destination.exists() or destination.is_symlink())
            self.assertEqual(_tree_snapshot(backup), before)

    def test_backup_symlink_and_its_target_are_preserved(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            target = box.root / "outside-backup-target"
            box.make_bundle(target)
            backup = box.apps / ".ClaudePet.app.previous"
            backup.symlink_to(target, target_is_directory=True)
            target_before = _tree_snapshot(target)
            link_before = _tree_snapshot(backup)

            result = box.run_script(box.write_update_script(), destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(_tree_snapshot(backup), link_before)
            self.assertEqual(_tree_snapshot(target), target_before)


class StagedPreflightTests(ReviewedBuildScriptMixin, unittest.TestCase):
    def test_both_bundle_version_keys_must_equal_the_source_version(self):
        for mode in ("bad-short", "bad-build"):
            with self.subTest(mode=mode), TransactionSandbox(self.source) as box:
                destination = box.make_bundle(box.apps / "ClaudePet.app")

                result = box.run_script(
                    box.write_update_script(), destination, TEST_PLIST_MODE=mode
                )

                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(
                    (destination / "Contents/Resources/claude_pet.py").read_bytes(),
                    b"old installed code\n",
                )
                self.assertFalse(box.event("stop").exists())

    def test_executable_must_be_a_regular_nonlink_file(self):
        for kind in ("symlink", "directory"):
            with self.subTest(kind=kind), TransactionSandbox(self.source) as box:
                destination = box.make_bundle(box.apps / "ClaudePet.app")

                result = box.run_script(
                    box.write_update_script(), destination,
                    TEST_HOOK_MODE=f"tamper-exe-{kind}",
                )

                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(box.event("stop").exists())
                executable = destination / "Contents/MacOS/ClaudePet"
                self.assertTrue(executable.is_file())
                self.assertFalse(executable.is_symlink())

    def test_staged_application_code_must_match_the_checkout_code_hash(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")

            result = box.run_script(
                box.write_update_script(),
                destination,
                TEST_HOOK_MODE="tamper-code",
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                (destination / "Contents/Resources/claude_pet.py").read_bytes(),
                b"old installed code\n",
            )
            self.assertFalse(box.event("stop").exists())


class RollbackAndInstallTests(ReviewedBuildScriptMixin, unittest.TestCase):
    def test_failed_publish_restores_and_relaunches_the_old_application(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            script = box.write_update_script(
                fail_publish=True
            )

            result = box.run_script(script, destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                (destination / "Contents/Resources/claude_pet.py").read_bytes(),
                b"old installed code\n",
            )
            self.assertTrue((destination / "old-install.marker").is_file())
            self.assertTrue(box.event("stop").exists())
            self.assertTrue(
                box.event(f"launch.{destination}").exists(),
                "a failed update restored the old app but left the stopped app down",
            )

    def test_install_copy_failure_preserves_the_existing_application(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            built = box.make_bundle(
                box.root / "ClaudePet.app", code=box.source_code.read_bytes()
            )
            script = box.write_install_script(built)

            result = box.run_script(script, destination)

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((destination / "old-install.marker").is_file())
            self.assertEqual(
                (destination / "Contents/Resources/claude_pet.py").read_bytes(),
                b"old installed code\n",
            )


class WholeTransactionConcurrencyTests(ReviewedBuildScriptMixin, unittest.TestCase):
    def test_second_update_cannot_clean_or_prepare_until_first_transaction_finishes(self):
        with TransactionSandbox(self.source) as box:
            destination = box.make_bundle(box.apps / "ClaudePet.app")
            script = box.write_update_script()
            first = box.popen_update(script, destination, role="A")
            second = None
            try:
                self.assertTrue(box.wait_event("A.ditto"), "first updater never prepared")

                # This appears after A's cleanup.  A whole-transaction lock keeps B
                # from deleting it until A has published and released the lock.
                foreign_stage = box.apps / ".ClaudePet.app.new.foreign"
                foreign_stage.mkdir()
                (foreign_stage / "sentinel").write_text("must survive while A runs\n")

                second = box.popen_update(script, destination, role="B")
                b_entered_during_first_prepare = box.wait_event("B.ditto", timeout=0.8)
                foreign_survived_second_start = foreign_stage.exists()

                box.release("allow.A.ditto")
                self.assertTrue(
                    box.wait_event("A.before_finish"),
                    "first updater never reached its final pre-cleanup checkpoint",
                )
                b_entered_before_first_finish = box.event("B.ditto").exists()

                box.release("allow.A.finish")
                first_stdout, first_stderr = first.communicate(timeout=8)

                # Only now may B clean the foreign stage and enter its own ditto.
                self.assertTrue(box.wait_event("B.ditto"), "second updater stayed blocked")
                box.release("allow.B.ditto")
                second_stdout, second_stderr = second.communicate(timeout=8)

                self.assertEqual(first.returncode, 0, first_stdout + first_stderr)
                self.assertEqual(second.returncode, 0, second_stdout + second_stderr)
                self.assertFalse(
                    b_entered_during_first_prepare,
                    "a concurrent updater entered preparation while A held the transaction",
                )
                self.assertTrue(
                    foreign_survived_second_start,
                    "B ran stale cleanup while A's transaction was still preparing",
                )
                self.assertFalse(
                    b_entered_before_first_finish,
                    "the transaction lock was released before A's final backup cleanup",
                )
            finally:
                # Release only this test's temp-local barriers, then stop only the two
                # child PIDs owned by this test if an assertion interrupted the schedule.
                for event in ("allow.A.ditto", "allow.A.finish", "allow.B.ditto"):
                    box.release(event)
                for process in (first, second):
                    if process is not None and process.poll() is None:
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.communicate(timeout=2)
                        except subprocess.TimeoutExpired:
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.communicate(timeout=2)


if __name__ == "__main__":
    unittest.main()
