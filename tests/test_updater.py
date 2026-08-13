"""v0.20 updater contract tests.

Scope: asset selection, update-preflight, the zip member scan, and the
replacement shell script. Every test here targets one of the eight v0.20
updater items. Tests that need the real macOS tools skip **loudly** (stderr +
skipTest) so a missing prerequisite can never be mistaken for coverage.

    python3 -m unittest tests.test_updater -v      # from the repo root

Two tests are deliberate *guards* rather than new requirements — they pass
against the current implementation and must keep passing after the change:
`test_framework_style_relative_symlink_inside_the_bundle_is_accepted` (a rule
of "no symlinks anywhere" would reject every py2app bundle and kill updates
permanently) and `test_script_keeps_the_literal_substrings_other_tests_pin`.
They are named in the class docstrings where they appear.
"""

import errno
import inspect
import json
import os
import platform
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from urllib.error import URLError

import claude_pet


XCRUN = "/usr/bin/xcrun"
INSTALLED_APP = "/Applications/ClaudePet.app"
# Apple-signed but **not** notarization-stapled: the negative case that proves
# `stapler validate` discriminates. Live-verified rc=65.
UNSTAPLED_APP = "/System/Applications/Calculator.app"
LIVE_UPDATER_TEST_ENV = "CLAUDEPET_RUN_LIVE_UPDATER_TESTS"


def _skip_loudly(test, why):
    print(f"\n[updater] SKIPPED: {why}", file=sys.stderr, flush=True)
    test.skipTest(why)


def _require_live_opt_in(test, what):
    """Keep machine-specific app/signing checks out of normal discovery."""
    if os.environ.get(LIVE_UPDATER_TEST_ENV) != "1":
        _skip_loudly(
            test,
            f"{what} is an opt-in live check; set "
            f"{LIVE_UPDATER_TEST_ENV}=1 to run it")


# ──────────────── isolation from the user's real home ────────────────
#
# A test that drives `install_github_update` takes a **real** `flock`, at a
# path computed from `~`. This suite once created
# `~/Library/Caches/me.yeongyu.claudepet/` and a lock file inside the user's
# own home, and that is the incident these fixtures exist to make
# unrepeatable.
#
# Three separate redirections are needed, and none of them substitutes for
# another:
#
#  * `claude_pet.UPDATE_LOCK_DIR` — read at call time by `_update_lock_path`,
#    so patching the constant is enough **in this process**. It reaches no
#    child, because a child re-imports the module and gets the shipped value.
#  * `HOME` — what a child process expands `~` against, and also what the
#    replacement script writes its retained-backup notice to: the `cleanup()`
#    function in `_update_replace_script` appends to `"$HOME/claudepet_debug.log"`.
#    No amount of lock redirection covers that line.
#  * `TMPDIR` / `ZDOTDIR` / `ENV` / `BASH_ENV` / `CDPATH` — every shell these
#    tests spawn reads some of these. An ambient `~/.zshrc` or a `CDPATH`
#    inherited from the developer's environment silently changes what runs.
#
# These are installed at **module** level, not in a base class, and that is
# deliberate. A base class only protects the classes that remember to inherit
# it; `setUpModule` protects every test in this file, including ones added
# later by someone who never read this comment. The base class below adds a
# per-test *alarm* on top, so a bypass is attributed to the test that caused
# it rather than to the module.

# Captured at import, before anything is patched: these are the real paths the
# alarm watches.
REAL_HOME = os.path.expanduser("~")
REAL_LOCK_DIR = os.path.expanduser(claude_pet.UPDATE_LOCK_DIR)
REAL_DEBUG_LOG = os.path.expanduser("~/claudepet_debug.log")


def dir_fingerprint(path):
    """Everything about a directory tree a stray write would change.

    Returns None when the directory does not exist, so "was absent, still
    absent" and "was present, unchanged" are both expressible as equality
    against a baseline. Walks the whole tree rather than one level, so a lock
    file dropped into a subdirectory is visible too.
    """
    if not os.path.isdir(path):
        return None
    out = {}
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            full = os.path.join(root, name)
            out[os.path.relpath(full, path)] = _stat_tuple(full)
    return out


def _stat_tuple(path):
    st = os.lstat(path)
    return (stat_mode_kind(st.st_mode), st.st_size, st.st_mtime_ns, st.st_ino)


def stat_mode_kind(mode):
    return mode & 0o170000


# The install path's *parent* is written to as well, and it is not under
# `~`: `install_github_update` claims its staging directory beside
# `app_path`. A test that passes `/Applications/ClaudePet.app` therefore
# creates real directories in `/Applications`, which no HOME redirection
# touches. Two such leftovers were already present when this alarm was
# written and are left in place as evidence, so the baseline includes them.
REAL_APPS_DIR = "/Applications"


def staging_fingerprint():
    """Our own leftovers beside the installed app, ignoring everything else.

    Scoped to the `.claudepet-` prefix on purpose: an unrelated application
    appearing in `/Applications` mid-run must not be reported as this suite
    having written something.
    """
    try:
        names = sorted(n for n in os.listdir(REAL_APPS_DIR)
                       if n.startswith(".claudepet-"))
    except OSError:
        return None
    return {n: _stat_tuple(os.path.join(REAL_APPS_DIR, n)) for n in names}


def file_fingerprint(path):
    """(size, mtime) of a file, or None when it does not exist."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


# ──────────────── the download seam, and the network under it ────────────────
#
# `install_github_update` downloads through `_download_update_zip(url, dest)`,
# which calls `urllib.request.urlopen(..., timeout=UPDATE_DOWNLOAD_TIMEOUT)`.
# It does **not** call `urllib.request.urlretrieve`; that function's docstring
# says why (there is nowhere to put a timeout).
#
# Every fixture in this file used to patch `urlretrieve`. Patching a name
# production never looks up is not a stand-in for anything: the mock records
# nothing, the real `urlopen` runs, and the test resolves and connects to
# whatever host the fixture's URL names. Four of them did exactly that.
#
# Two defences, because either one alone fails silently:
#
#   * `patch_download()` — patch the seam production actually calls. Fixtures
#     use this and nothing else, so the seam has one name in this file and
#     moving it again breaks every fixture at once instead of none of them.
#   * the socket guard — any connection to anywhere but loopback is refused
#     **and recorded**, and `IsolatedTest.tearDown` fails the test that caused
#     it. Recording is what makes it work: `install_github_update` ends in
#     `except Exception: return False`, so a guard that only raised would turn
#     "this test reached the network" into "this test returned False", which
#     is what several of these tests assert anyway.
#
# This is the first check in this file that watches something other than the
# filesystem, and it is scoped to that: it says nothing about paths, and the
# path alarms say nothing about sockets.

NETWORK_ATTEMPTS = []


class NetworkReached(AssertionError):
    """Raised in place of a socket to anywhere but loopback."""


_AF_UNIX = getattr(socket, "AF_UNIX", None)
_LOOPBACK = ("localhost", "127.0.0.1", "::1", "")
_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_CONNECT = socket.socket.connect


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    if str(host) in _LOOPBACK:
        return _REAL_GETADDRINFO(host, port, *args, **kwargs)
    NETWORK_ATTEMPTS.append(f"getaddrinfo({host!r}, {port!r})")
    raise NetworkReached(f"a test tried to resolve {host!r}")


def _guarded_connect(self, address, *args, **kwargs):
    # AF_UNIX addresses are paths, not hosts — the filesystem alarms cover
    # those, and blocking them here would break anything that talks to a local
    # socket for reasons unrelated to updates.
    local = (_AF_UNIX is not None and self.family == _AF_UNIX) or (
        isinstance(address, tuple) and str(address[0]) in _LOOPBACK)
    if local:
        return _REAL_CONNECT(self, address, *args, **kwargs)
    NETWORK_ATTEMPTS.append(f"connect({address!r})")
    raise NetworkReached(f"a test tried to connect to {address!r}")


def take_network_attempts():
    """Read and clear the recorded attempts.

    Clearing is part of reading so that a test which asserts on them cannot
    leave them behind for the next test's alarm to blame the wrong test.
    """
    attempts = list(NETWORK_ATTEMPTS)
    del NETWORK_ATTEMPTS[:]
    return attempts


# ──────────────── the escape that is not a path ────────────────
#
# The replacement script runs `/usr/bin/open` in two places, and `open` on a
# bundle **registers it with LaunchServices** — a machine-global database that
# outlives the fixture, the test run, and the temp directory. Every other
# alarm in this file watches the filesystem, so this one escaped all of them:
# nothing on disk changes, and the record survives the directory being
# deleted (the entries left by earlier runs read "Bundle node not found on
# disk" and are still there).
#
# The check is scoped to *this run's* temp root, which is created fresh in
# `setUpModule`. That scoping is what makes it safe as well as precise: a
# record under a root that did not exist before this run can only have been
# made by this run, so the check never has an opinion about pre-existing
# entries and never asks anyone to remove one.
#
# **Read-only.** `lsregister -dump` prints the database. `lsregister -u`,
# `-kill`, and every other mutating form are deliberately absent from this
# suite: the stale records already present are the user's to keep or clear.

LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")
BUNDLE_ID = "me.yeongyu.claudepet"
_RECORD_SEPARATOR = "-" * 80


def lsregister_dump():
    """The LaunchServices database as text, or None if it cannot be read."""
    if not os.path.exists(LSREGISTER):
        return None
    try:
        result = subprocess.run([LSREGISTER, "-dump"], capture_output=True,
                                text=True, errors="replace", timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout or None


def registrations_in(dump, bundle_id=None, under=None):
    """Paths of records in `dump`, optionally filtered by identifier and root.

    Kept a pure function of the text so it can be exercised against a
    synthetic dump — the discrimination of this check cannot be demonstrated
    by creating a real registration, since that would mean writing to
    machine-global state.
    """
    root = os.path.realpath(under) + os.sep if under else None
    found = []
    for record in (dump or "").split(_RECORD_SEPARATOR):
        ident = re.search(r"^identifier:\s+(\S+)", record, re.M)
        if ident is None:
            ident = re.search(r"^bundle id:\s+(\S+)", record, re.M)
        path = re.search(r"^path:\s+(.*?)(?:\s+\(0x[0-9a-fA-F]+\))?$",
                         record, re.M)
        if ident is None or path is None:
            continue
        if bundle_id is not None and ident.group(1) != bundle_id:
            continue
        if root is not None and not (os.path.realpath(path.group(1)) + os.sep
                                     ).startswith(root):
            continue
        found.append(path.group(1))
    return sorted(found)


def launch_registration_violations(under, dump=None):
    """Records claiming the production bundle id from inside `under`.

    A non-empty result means a fixture bundle was actually launched: the app
    identity users' machines know is now claimed by a path in a temp
    directory. The remedy is in the test that caused it — substitute *both*
    launch points — never in the database.
    """
    if dump is None:
        dump = lsregister_dump()
    if dump is None:
        return []
    return registrations_in(dump, BUNDLE_ID, under)


_ISOLATION = {}


def setUpModule():
    root = tempfile.mkdtemp(prefix="claudepet-updater-isolation-")
    home = os.path.join(root, "home")
    tmp = os.path.join(root, "tmp")
    # The fixture HOME must **exist**: a shell whose $HOME is a missing
    # directory still expands the path, and the `>>` redirect that appends the
    # retained-backup notice would then fail silently rather than landing
    # somewhere we can see.
    os.makedirs(home)
    os.makedirs(tmp)
    # NOT created here. Production creates it in `_acquire_update_lock`, and
    # a fixture that pre-creates it hides the case where it fails to.
    cache = os.path.join(root, "cache")
    env = mock.patch.dict(os.environ, {
        "HOME": home,
        "TMPDIR": tmp + os.sep,
        # zsh reads $ZDOTDIR/.zshrc; sh and bash read $ENV / $BASH_ENV. All
        # three are pointed inside the empty fixture home, where none exist.
        "ZDOTDIR": home,
        "ENV": os.path.join(home, ".no-such-rc"),
        "BASH_ENV": os.path.join(home, ".no-such-rc"),
        # An inherited CDPATH makes a bare `cd foo` land somewhere else.
        "CDPATH": "",
    })
    lock = mock.patch.object(claude_pet, "UPDATE_LOCK_DIR", cache)
    # Installed at module level for the same reason as the redirections above:
    # a base class only protects the classes that remember to inherit it.
    dns = mock.patch.object(socket, "getaddrinfo", _guarded_getaddrinfo)
    conn = mock.patch.object(socket.socket, "connect", _guarded_connect)
    env.start()
    lock.start()
    dns.start()
    conn.start()
    del NETWORK_ATTEMPTS[:]
    _ISOLATION.update(
        root=root, home=home, tmp=tmp, cache=cache,
        patches=(conn, dns, lock, env),
        cache_baseline=dir_fingerprint(REAL_LOCK_DIR),
        log_baseline=file_fingerprint(REAL_DEBUG_LOG),
        staging_baseline=staging_fingerprint(),
        upd_cache=dict(claude_pet._upd_cache))
    claude_pet._upd_cache.clear()


def tearDownModule():
    for patch in _ISOLATION["patches"]:
        patch.stop()
    claude_pet._upd_cache.clear()
    claude_pet._upd_cache.update(_ISOLATION["upd_cache"])
    # Asked **before** the tree is removed, and answered from the database
    # rather than the disk: a registration outlives the directory it names, so
    # the order does not actually matter here — but reading it first keeps the
    # reported paths resolvable for whoever has to find the offending test.
    registered = launch_registration_violations(_ISOLATION["root"])
    shutil.rmtree(_ISOLATION["root"], ignore_errors=True)
    # The net under the per-test alarm: a class that overrides tearDown and
    # forgets to call super() still gets caught here, just less precisely.
    problems = real_home_violations()
    if problems:
        raise AssertionError(
            "tests in this module reached the user's real home:\n  "
            + "\n  ".join(problems))
    if registered:
        raise AssertionError(
            f"a fixture bundle was launched: LaunchServices now records "
            f"{BUNDLE_ID} at these temp paths, and will keep recording them "
            f"after the directories are gone:\n  " + "\n  ".join(registered)
            + "\n  Substitute BOTH launch points — see replace_launch_points()."
        )


def real_home_violations():
    """Ways the real home differs from what it was when this module loaded.

    **The check is "unchanged", not "absent".** `~/Library/Caches/
    me.yeongyu.claudepet/` already exists on this machine — it is the artifact
    of the earlier incident and is being kept as evidence — so an assertion
    that it must not exist would fail every test for a reason that has nothing
    to do with the test.

    What this catches: the directory being created where it was absent, any
    entry appearing or disappearing, and any entry changing size, kind, inode
    or mtime. That covers a fresh lock file, a fresh cache directory, and any
    append to the debug log.

    What it does **not** catch: `flock`-ing a lock file that already exists.
    Opening an existing file with O_RDWR|O_CREAT and taking a `flock` changes
    no metadata at all, so no stat-based check can see it. That gap is covered
    from the other side instead, by
    `LockIsolationInstrumentTests.test_the_lock_lands_in_the_fixture_cache_not_the_real_one`,
    which shows the redirection is load-bearing rather than decorative.
    """
    problems = []
    now = dir_fingerprint(REAL_LOCK_DIR)
    if now != _ISOLATION["cache_baseline"]:
        problems.append(f"{REAL_LOCK_DIR}: {_ISOLATION['cache_baseline']!r} "
                        f"-> {now!r}")
    now_log = file_fingerprint(REAL_DEBUG_LOG)
    if now_log != _ISOLATION["log_baseline"]:
        problems.append(f"{REAL_DEBUG_LOG}: {_ISOLATION['log_baseline']!r} "
                        f"-> {now_log!r}")
    now_staging = staging_fingerprint()
    if now_staging != _ISOLATION["staging_baseline"]:
        problems.append(f"{REAL_APPS_DIR}/.claudepet-*: "
                        f"{_ISOLATION['staging_baseline']!r} -> "
                        f"{now_staging!r}")
    return problems


class IsolatedTest(unittest.TestCase):
    """Base for every test class in this file.

    Provides the per-test bypass alarm. A subclass that defines its own
    `tearDown` **must** call `super().tearDown()`; if it forgets, the
    module-level net in `tearDownModule` still fires.
    """

    # Set on a class that executes the replacement script for real. Reading
    # the LaunchServices database costs a couple of seconds, so it is asked
    # once per such class rather than once per test; `tearDownModule` asks it
    # again for the module as a whole, which is what covers a class that
    # starts running scripts without setting this.
    RUNS_THE_REPLACEMENT_SCRIPT = False

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if not cls.RUNS_THE_REPLACEMENT_SCRIPT:
            return
        registered = launch_registration_violations(_ISOLATION["root"])
        if registered:
            raise AssertionError(
                f"{cls.__name__} launched a fixture bundle: LaunchServices "
                f"now records {BUNDLE_ID} at\n  " + "\n  ".join(registered)
                + "\n  Both launch points must be substituted — see "
                  "replace_launch_points().")

    def tearDown(self):
        super().tearDown()
        # Read *and clear* first, unconditionally: an assertion below that
        # fires would otherwise leave these behind for the next test's alarm,
        # which would then blame a test that did nothing wrong.
        attempts = take_network_attempts()
        self.assertEqual(
            attempts, [],
            "this test tried to use the network; the download seam is "
            "`claude_pet._download_update_zip` and `patch_download()` is how "
            "to stand in for it:\n  " + "\n  ".join(attempts))
        # What happened is checked before why. Asserting the redirections
        # first would mask the violation behind a less informative failure —
        # "HOME was wrong" instead of "this is the file you wrote".
        problems = real_home_violations()
        self.assertEqual(
            problems, [],
            "this test wrote outside its fixture:\n  " + "\n  ".join(problems))
        self.assertEqual(
            os.environ.get("HOME"), _ISOLATION["home"],
            "HOME was left pointing outside the fixture; a later test would "
            "run against the real home")
        self.assertTrue(
            os.path.expanduser(claude_pet.UPDATE_LOCK_DIR).startswith(
                _ISOLATION["root"] + os.sep),
            "the update-lock redirection was left disabled: "
            f"{claude_pet.UPDATE_LOCK_DIR!r}")

    def script_env(self, **extra):
        """Environment for any shell or helper this suite spawns.

        `os.environ` already carries the module-level redirections, so this is
        about the per-test additions. Passing it explicitly (rather than
        relying on inheritance) also keeps the redirection visible at the call
        site, where someone adding a `subprocess.run` will see it.
        """
        env = dict(os.environ)
        env.update(extra)
        return env


# ─────────────────────────── fixtures ───────────────────────────

def patch_download(side_effect=None, **kwargs):
    """Stand in for the seam `install_github_update` actually downloads through.

    The stand-in keeps `_download_update_zip(zip_url, dest)`'s signature — the
    same two positionals the retired `urlretrieve` fixtures were written
    against — so a fixture's `fetch(url, path)` needs no change beyond being
    attached here.

    With no argument the download is a no-op that writes nothing, which is what
    a test wants when it expects the install to be refused before this point.
    """
    if side_effect is None and not kwargs:
        kwargs = {"return_value": 0}
    return mock.patch.object(claude_pet, "_download_update_zip",
                             side_effect=side_effect, **kwargs)


def make_pet_tree(root):
    """The bundled `.claude_pet` payload, exactly as the manifest expects."""
    root = Path(root)
    for name in claude_pet.BUNDLED_PET_README:
        (root / name).write_text(f"source {name}\n")
    for pet in claude_pet.BUNDLED_PET_IDS:
        p = root / "pets" / pet
        p.mkdir(parents=True)
        (p / "pet.json").write_text(json.dumps(
            {"id": pet, "spritesheetPath": "spritesheet.webp",
             "spriteVersionNumber": 2}))
        (p / "spritesheet.webp").write_bytes((pet + " sheet").encode())
        (p / "preview.png").write_bytes((pet + " preview").encode())


# A real Mach-O to stand in for the ordinary bundle binaries. Architecture-
# specific negative fixtures below are written as minimal headers in Python;
# they do not invoke the host's `lipo` and cannot inspect or modify a live app.
UNIVERSAL_BINARY = sys.executable
NATIVE_ARCH = platform.machine()
FOREIGN_ARCH = "x86_64" if NATIVE_ARCH != "x86_64" else "arm64"

_THIN_MACHO_CPU = {
    "x86_64": (0x01000007, 3),
    "arm64": (0x0100000C, 0),
    "arm64e": (0x0100000C, 2),
}


def put_binary(path, archs=None):
    """Install a Mach-O fixture without running a host architecture tool."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if archs is None:
        shutil.copyfile(UNIVERSAL_BINARY, path)
    else:
        try:
            cpu, subtype = _THIN_MACHO_CPU[str(archs)]
        except KeyError as exc:
            raise ValueError(f"unsupported fixture architecture: {archs}") from exc
        # MH_CIGAM_64 as read in big-endian order, followed by the little-endian
        # cputype/cpusubtype fields `_macho_arches` parses. The remaining header
        # bytes are irrelevant to that pure preflight and the file is never run.
        path.write_bytes(
            (0xCFFAEDFE).to_bytes(4, "big")
            + cpu.to_bytes(4, "little")
            + subtype.to_bytes(4, "little")
            + b"\0" * 20)
    path.chmod(0o755)
    return path


def make_update_app(root, version="99.0"):
    """A structurally complete .app: Info.plist, MacOS/, and the pet payload."""
    app = Path(root) / "ClaudePet.app"
    (app / "Contents" / "MacOS").mkdir(parents=True)
    put_binary(app / "Contents" / "MacOS" / "ClaudePet")
    put_binary(app / "Contents" / "MacOS" / "python")
    resources = app / "Contents" / "Resources"
    resources.mkdir(parents=True)
    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump({"CFBundleIdentifier": "me.yeongyu.claudepet",
                       "CFBundleExecutable": "ClaudePet",
                       "CFBundleVersion": version,
                       "CFBundleShortVersionString": version}, f)
    pet_root = resources / ".claude_pet"
    pet_root.mkdir()
    make_pet_tree(pet_root)
    return app


def add_framework_symlinks(app):
    """The four legitimate py2app/Apple framework symlinks: relative and inside."""
    versions = Path(app) / "Contents" / "Frameworks" / "Python.framework" / "Versions"
    (versions / "3.11" / "lib").mkdir(parents=True)
    (versions / "3.11" / "Python").write_text("mach-o")
    os.symlink("3.11", versions / "Current")
    os.symlink("Versions/Current/Python", versions.parent / "Python")
    return versions


# ── a Mach-O stand-in for the bundle's `python` ──
#
# The recording helper used to be a `#!/bin/sh` wrapper. That is the wrong
# fixture twice over: `/bin/sh` keeps the script file open while the atomic
# exchange swaps the directory out from under it (measured: the whole updater
# hangs), and production's helper is py2app's real Mach-O interpreter — which
# the preflight is about to require. A shell script would pass a fixture that
# production would refuse.

INSTRUMENTED_PYTHON_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* Records its arguments, then *becomes* the real interpreter.
   argv[0] is rewritten to the interpreter's own path: a framework Python
   locates its prefix from argv[0], and left pointing at this wrapper it
   would not start at all. */
int main(int argc, char **argv) {
    const char *log = getenv("CLAUDEPET_TEST_EXCHANGE_LOG");
    if (log != NULL && log[0] != '\0') {
        FILE *f = fopen(log, "a");
        if (f != NULL) {
            int i;
            for (i = 1; i < argc; i++)
                fprintf(f, "%s%s", argv[i], (i + 1 < argc) ? " " : "");
            fputc('\n', f);
            fclose(f);
        }
    }
    argv[0] = (char *)PYTHON_PATH;
    execv(PYTHON_PATH, argv);
    return 127;
}
"""

# Always exits 1, and is a genuine Mach-O. Used where the fixture needs a
# bundled interpreter that is present and broken.
BROKEN_PYTHON = "/usr/bin/false"

_INSTRUMENTED = {}


def instrumented_python_binary(test):
    """Path to the compiled recording wrapper, built once per module run."""
    if "path" in _INSTRUMENTED:
        return _INSTRUMENTED["path"]
    cc = "/usr/bin/cc"
    if not os.path.exists(cc):
        _skip_loudly(test, f"no compiler at {cc}, so the Mach-O recording "
                           "helper cannot be built")
    src = os.path.join(_ISOLATION["root"], "instrumented_python.c")
    out = os.path.join(_ISOLATION["root"], "instrumented_python")
    with open(src, "w") as f:
        f.write(INSTRUMENTED_PYTHON_C)
    result = subprocess.run(
        [cc, "-O0", f'-DPYTHON_PATH="{sys.executable}"', "-o", out, src],
        capture_output=True, text=True)
    if result.returncode != 0:
        _skip_loudly(test, "cannot compile the Mach-O recording helper: "
                           f"{result.stderr.strip()!r}")
    _INSTRUMENTED["path"] = out
    return out


def fake_ditto(argv, *args, **kwargs):
    """A `ditto` stand-in, faithful in the one way that matters here.

    Real `ditto src dst` **merges into** an existing `dst`. `shutil.copytree`
    without `dirs_exist_ok=True` raises `FileExistsError` instead — and
    production deliberately *claims* its staging directory before calling
    ditto, so a stricter mock forces it to abandon a reservation the real tool
    would have accepted. The test would then be measuring the mock's rule.
    """
    argv = [str(a) for a in argv]
    src, dst = argv[-2], argv[-1]
    if "-x" in argv and "-k" in argv:
        with zipfile.ZipFile(src) as zf:
            zf.extractall(dst)
    else:
        shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    return mock.Mock(returncode=0, stdout="", stderr="")


class PreflightRunRecorder:
    """Stands in for subprocess.run inside validate_update_app.

    Dispatches on argv so a single tool can be failed while the others pass —
    a blanket returncode cannot tell "stapler was consulted" from "stapler was
    never run".
    """

    def __init__(self, rc_by_tool=None, raise_by_tool=None):
        self.rc_by_tool = rc_by_tool or {}
        self.raise_by_tool = raise_by_tool or {}
        self.calls = []

    @staticmethod
    def tool_of(argv):
        argv = [str(a) for a in argv]
        if not argv:
            return "other"
        executable = os.path.basename(argv[0])
        if (executable == "xcrun" and len(argv) > 1
                and argv[1] == "stapler"):
            return "stapler"
        if executable == "codesign":
            return "codesign"
        if executable == "spctl":
            return "spctl"
        return "other"

    # What the real tools print on success. Live-captured, not invented:
    # `spctl -vv` writes its assessment to **stderr**, and the origin line is
    # the only part that names the signer (tests/test_signing_contract.py
    # turns on exactly this).
    SPCTL_STDERR = ("{path}: accepted\n"
                    "source=Notarized Developer ID\n"
                    "origin=Developer ID Application: Yeongyu Yang "
                    "(%s)\n" % claude_pet.TEAM_ID)
    STAPLER_STDOUT = ("Processing: {path}\n"
                      "The validate action worked!\n")

    def __call__(self, argv, *args, **kwargs):
        tool = self.tool_of(argv)
        argv = [str(a) for a in argv]
        self.calls.append((tool, argv, kwargs))
        if tool in self.raise_by_tool:
            raise self.raise_by_tool[tool]
        rc = self.rc_by_tool.get(tool, 0)
        path = argv[-1]
        out, err = "", ""
        if rc == 0 and tool == "spctl":
            err = self.SPCTL_STDERR.format(path=path)
        elif rc == 0 and tool == "stapler":
            out = self.STAPLER_STDOUT.format(path=path)
        elif rc != 0 and tool == "spctl":
            err = f"{path}: rejected\n"
        elif rc != 0 and tool == "stapler":
            out = f"Processing: {path}\nThe validate action failed!\n"
        return mock.Mock(returncode=rc, stdout=out, stderr=err)

    def tools(self):
        return [tool for tool, _argv, _kw in self.calls]


# ───────────────── item 1: asset selection ─────────────────

class SelectUpdateAssetTests(IsolatedTest):
    """`select_update_asset(assets, machine) -> (url, name, arch) | None`.

    Exact-filename allow-list; unknown arch rejects; two assets normalizing to
    the same allowed name reject as ambiguous; the URL must be https with a
    non-empty netloc.
    """

    ARM = "https://example.test/ClaudePet.zip"
    UNI = "https://example.test/ClaudePet-universal.zip"

    def assets(self, *pairs):
        return [{"name": n, "browser_download_url": u} for n, u in pairs]

    def test_apple_silicon_prefers_the_arm_archive(self):
        got = claude_pet.select_update_asset(
            self.assets(("ClaudePet.zip", self.ARM),
                        ("ClaudePet-universal.zip", self.UNI)), "arm64")
        self.assertEqual(got, (self.ARM, "claudepet.zip", "arm64"))

    def test_apple_silicon_accepts_the_universal_archive_alone(self):
        got = claude_pet.select_update_asset(
            self.assets(("ClaudePet-universal.zip", self.UNI)), "arm64")
        self.assertEqual(got, (self.UNI, "claudepet-universal.zip", "arm64"))

    def test_intel_never_takes_the_arm_only_archive(self):
        self.assertIsNone(claude_pet.select_update_asset(
            self.assets(("ClaudePet.zip", self.ARM)), "x86_64"))

    def test_intel_takes_the_universal_archive(self):
        got = claude_pet.select_update_asset(
            self.assets(("ClaudePet.zip", self.ARM),
                        ("ClaudePet-universal.zip", self.UNI)), "x86_64")
        self.assertEqual(got, (self.UNI, "claudepet-universal.zip", "x86_64"))

    def test_unknown_architecture_is_rejected_rather_than_defaulted(self):
        for machine in ("aarch64", "ppc", "", None):
            with self.subTest(machine=machine):
                self.assertIsNone(claude_pet.select_update_asset(
                    self.assets(("ClaudePet-universal.zip", self.UNI)), machine))

    def test_names_are_matched_only_against_the_allow_list(self):
        for name in ("diagnostics.zip", "ClaudePet.zip.zip", "xClaudePet.zip",
                     "ClaudePet.dmg", "claudepet-universal.zip.txt"):
            with self.subTest(name=name):
                self.assertIsNone(claude_pet.select_update_asset(
                    self.assets((name, self.ARM)), "arm64"))

    def test_case_and_surrounding_whitespace_are_normalized(self):
        got = claude_pet.select_update_asset(
            self.assets(("  ClaudePet.ZIP  ", self.ARM)), "arm64")
        self.assertEqual(got, (self.ARM, "claudepet.zip", "arm64"))

    def test_two_assets_normalizing_to_one_allowed_name_are_ambiguous(self):
        """Two candidates for the same slot: we cannot know which is the app."""
        self.assertIsNone(claude_pet.select_update_asset(
            self.assets(("ClaudePet.zip", self.ARM),
                        ("claudepet.zip ", "https://example.test/other.zip")),
            "arm64"))

    def test_duplicate_unrelated_names_do_not_block_a_clean_choice(self):
        """Discrimination: the ambiguity rule is about the *allowed* name only."""
        got = claude_pet.select_update_asset(
            self.assets(("notes.zip", "https://example.test/a.zip"),
                        ("notes.zip", "https://example.test/b.zip"),
                        ("ClaudePet.zip", self.ARM)), "arm64")
        self.assertEqual(got, (self.ARM, "claudepet.zip", "arm64"))

    def test_a_non_https_or_hostless_url_is_never_selected(self):
        for url in ("http://example.test/ClaudePet.zip",
                    "file:///tmp/ClaudePet.zip",
                    "https:///ClaudePet.zip",
                    "ftp://example.test/ClaudePet.zip",
                    "/tmp/ClaudePet.zip", "", None):
            with self.subTest(url=url):
                self.assertIsNone(claude_pet.select_update_asset(
                    self.assets(("ClaudePet.zip", url)), "arm64"))

    def test_malformed_asset_entries_do_not_raise(self):
        for assets in ([], [{}], [{"name": None, "browser_download_url": None}],
                       [{"browser_download_url": "https://example.test/x.zip"}]):
            with self.subTest(assets=assets):
                self.assertIsNone(claude_pet.select_update_asset(assets, "arm64"))


class CheckGithubUpdateShapeTests(IsolatedTest):
    """The 3-tuple and `state["update"]` shapes are unchanged; the chosen asset
    and arch travel in `_upd_cache["choice"]` instead."""

    def setUp(self):
        self.old_cache = dict(claude_pet._upd_cache)
        claude_pet._upd_cache.clear()
        claude_pet._upd_cache["t"] = 0.0
        self.addCleanup(lambda: (claude_pet._upd_cache.clear(),
                                 claude_pet._upd_cache.update(self.old_cache)))

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    def payload(self, *names):
        return {"tag_name": "v99.0",
                "assets": [{"name": n,
                            "browser_download_url": f"https://example.test/{n}"}
                           for n in names]}

    def test_update_records_the_chosen_asset_and_arch_in_the_cache(self):
        """Per key, by name — `asset` and `arch` are bound through the
        transaction to the staged preflight (which verifies the architecture
        with `lipo`). A value carried under the wrong key, or one that silently
        defaults, breaks that binding while an object-level comparison still
        looks right.
        """
        with mock.patch.object(claude_pet.urllib.request, "urlopen",
                               return_value=self.FakeResponse(
                                   self.payload("ClaudePet.zip",
                                                "ClaudePet-universal.zip"))), \
             mock.patch("platform.machine", return_value="arm64"):
            self.assertEqual(
                claude_pet.check_github_update(),
                ("update", "99.0", "https://example.test/ClaudePet.zip"))
        choice = claude_pet._upd_cache.get("choice")
        self.assertIsInstance(choice, dict,
                              "choice must be the offer metadata mapping")
        self.assertEqual(choice.get("asset"), "claudepet.zip")
        self.assertEqual(choice.get("arch"), "arm64")

    # `choice` must not outlive the check that produced it: a stale choice can
    # attach the wrong asset/arch/tag to a later transaction, which defeats the
    # binding that expected_version, the lipo arch check and the staged
    # re-validation all depend on.
    def test_a_non_update_result_leaves_no_stale_choice_behind(self):
        claude_pet._upd_cache["choice"] = ("claudepet.zip", "arm64")
        current = {"tag_name": f"v{claude_pet.APP_VERSION}", "assets": []}
        with mock.patch.object(claude_pet.urllib.request, "urlopen",
                               return_value=self.FakeResponse(current)):
            self.assertEqual(claude_pet.check_github_update(),
                             ("current", None, None))
        self.assertIsNone(claude_pet._upd_cache.get("choice"))

    def test_a_failed_check_leaves_no_stale_choice_behind(self):
        claude_pet._upd_cache["choice"] = ("claudepet.zip", "arm64")
        with mock.patch.object(claude_pet.urllib.request, "urlopen",
                               side_effect=URLError("offline")):
            self.assertEqual(claude_pet.check_github_update(),
                             ("failed", None, None))
        self.assertIsNone(claude_pet._upd_cache.get("choice"))

    def test_poll_still_publishes_the_two_tuple_the_ui_reads(self):
        state = {"update": None}
        with mock.patch.object(claude_pet, "check_github_update",
                               return_value=("update", "99.0",
                                             "https://example.test/a.zip")):
            self.assertEqual(claude_pet.poll_github_update(state, now=1000.0),
                             "update")
        self.assertEqual(state["update"], ("99.0", "https://example.test/a.zip"))


# ───────────── item 2: expected_version is required ─────────────

class ExpectedVersionRequiredTests(IsolatedTest):
    """The `is not None` bypass is gone: no version, no install.

    A missing expectation used to skip the version comparison entirely, so any
    correctly-signed bundle of *any* version — including a downgrade — passed
    the preflight.
    """

    def test_preflight_rejects_a_missing_or_blank_expectation(self):
        for expect in (None, "", "   ", 0, False):
            with self.subTest(expect=expect), tempfile.TemporaryDirectory() as td:
                app = make_update_app(td)
                runner = PreflightRunRecorder()
                with mock.patch.object(claude_pet.subprocess, "run", runner):
                    self.assertFalse(claude_pet.validate_update_app(app, expect))
                self.assertEqual(
                    runner.tools(), [],
                    "a bundle with no expected version reached the signing "
                    "tools; it must be refused before that")

    def test_install_refuses_before_downloading_anything(self):
        for expect in (None, "", "   "):
            with self.subTest(expect=expect):
                with patch_download() as fetch, \
                     mock.patch.object(claude_pet.tempfile, "mkdtemp") as mkd:
                    self.assertFalse(claude_pet.install_github_update(
                        "https://example.test/a.zip",
                        app_path=str(Path(tempfile.gettempdir())
                                     / "no-such-ClaudePet.app"),
                        expect_version=expect))
                self.assertFalse(fetch.called,
                                 "downloaded before checking the expectation")
                self.assertFalse(mkd.called,
                                 "created a temp dir before checking the "
                                 "expectation")


# ───────────── item 3: containment walk + zip member scan ─────────────

class BundleContainmentTests(IsolatedTest):
    """Every entry's realpath stays inside the bundle; the `.claude_pet`
    subtree holds no symlink at all.

    NOTE: `test_framework_style_relative_symlink_inside_the_bundle_is_accepted`
    is a **guard**. It passes today and must keep passing — a blanket
    "no symlinks anywhere" rule would reject every py2app bundle (they ship
    four legitimate framework symlinks) and would permanently kill updates,
    including the update that would fix the rule.
    """

    def validate(self, app, rc_by_tool=None):
        runner = PreflightRunRecorder(rc_by_tool)
        with mock.patch.object(claude_pet.subprocess, "run", runner):
            return claude_pet.validate_update_app(app, "99.0")

    def test_framework_style_relative_symlink_inside_the_bundle_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            add_framework_symlinks(app)
            self.assertTrue(
                self.validate(app),
                "a normal py2app bundle was rejected — this rule would block "
                "every future update")

    def test_absolute_symlink_target_anywhere_in_the_bundle_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            versions = add_framework_symlinks(app)
            os.symlink("/etc/passwd", versions / "3.11" / "lib" / "config")
            self.assertFalse(
                self.validate(app),
                "a symlink pointing outside the bundle by absolute path was "
                "accepted")

    def test_relative_symlink_escaping_the_bundle_is_rejected(self):
        """Which rule does the work: the realpath containment one, and only it.

        Built with a **relative** target on purpose. An absolute target would
        be caught by the absolute-target rule, so the containment branch would
        never execute and the test would prove nothing about the thing it is
        named for — AGENTS.md §3 in its exact shape. The assertion below pins
        that: the target is relative, so the absolute rule cannot be what fails
        this bundle.
        """
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside"
            outside.mkdir()
            (outside / "secret").write_text("not ours")
            app = make_update_app(td)
            versions = add_framework_symlinks(app)
            link = versions / "3.11" / "out"
            depth = os.path.relpath(td, versions / "3.11")
            os.symlink(os.path.join(depth, "outside"), link)

            target = os.readlink(link)
            self.assertFalse(os.path.isabs(target),
                             "fixture is not exercising the containment rule: "
                             f"the target {target!r} is absolute, so the "
                             "absolute-target rule would catch it first")
            resolved = os.path.realpath(link)
            self.assertEqual(resolved, os.path.realpath(outside),
                             "fixture does not point where it claims to")
            self.assertFalse(
                resolved.startswith(os.path.realpath(app) + os.sep),
                "fixture does not actually escape the bundle")

            self.assertFalse(
                self.validate(app),
                "a `..` escape out of the bundle was accepted")

    def test_symlink_in_the_pet_subtree_is_rejected_even_when_contained(self):
        """Ours, and it legitimately contains zero symlinks — so any is a red flag."""
        res = ("Contents", "Resources", ".claude_pet")
        cases = {
            "extra file below a pet": ("pets/dog/extra.png", "preview.png"),
            "extra directory beside the pets": ("pets/spare", "dog"),
            "unlisted top-level entry": ("EXTRA.md", "README.md"),
        }
        for label, (rel, target) in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as td:
                app = make_update_app(td)
                link = Path(app).joinpath(*res, rel)
                link.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(target, link)
                self.assertFalse(
                    self.validate(app),
                    f"a symlink at .claude_pet/{rel} was accepted")

    def test_symlinked_ancestor_of_the_pet_subtree_is_rejected(self):
        for ancestor in (".claude_pet", ".claude_pet/pets",
                         ".claude_pet/pets/dog"):
            with self.subTest(ancestor=ancestor), tempfile.TemporaryDirectory() as td:
                app = make_update_app(td)
                res = Path(app) / "Contents" / "Resources"
                real = res / "real-payload"
                shutil.move(str(res / ".claude_pet"), str(real))
                if ancestor == ".claude_pet":
                    os.symlink("real-payload", res / ".claude_pet")
                else:
                    shutil.move(str(real), str(res / ".claude_pet"))
                    victim = res / ancestor
                    moved = victim.parent / (victim.name + "-real")
                    shutil.move(str(victim), str(moved))
                    os.symlink(moved.name, victim)
                self.assertFalse(self.validate(app),
                                 f"a symlinked {ancestor} ancestor was accepted")

    def test_missing_manifest_members_still_only_warn(self):
        """Policy guard: missing assets must not strand users on an old build."""
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            (app / "Contents" / "Resources" / ".claude_pet" / "pets" / "dog"
             / "preview.png").unlink()
            runner = PreflightRunRecorder()
            with mock.patch.object(claude_pet.subprocess, "run", runner), \
                 mock.patch("builtins.print") as printed:
                self.assertTrue(claude_pet.validate_update_app(app, "99.0"))
            self.assertTrue(printed.called, "manifest drift emitted no diagnostic")


class RequiredArchitectureTests(IsolatedTest):
    """A bundle that cannot run on this machine must be refused before it
    replaces one that can.

    The wrong-architecture case is not hypothetical: it is what the asset
    allow-list exists to prevent, and the allow-list works from a filename. A
    mislabelled or mis-built release passes that and is caught only here.
    """

    def validate(self, app):
        runner = PreflightRunRecorder()
        with mock.patch.object(claude_pet.subprocess, "run", runner):
            return claude_pet.validate_update_app(app, "99.0")

    def test_a_bundle_whose_executable_lacks_this_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            put_binary(app / "Contents" / "MacOS" / "ClaudePet", FOREIGN_ARCH)
            self.assertFalse(
                self.validate(app),
                f"a {FOREIGN_ARCH}-only executable was accepted on "
                f"{NATIVE_ARCH}; it cannot launch here")

    def test_a_bundled_interpreter_lacking_this_architecture_is_rejected(self):
        """The helper the swap itself runs — a mismatch breaks the update path."""
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            put_binary(app / "Contents" / "MacOS" / "python", FOREIGN_ARCH)
            self.assertFalse(
                self.validate(app),
                f"a {FOREIGN_ARCH}-only bundled interpreter was accepted on "
                f"{NATIVE_ARCH}")

    def test_a_native_and_a_universal_bundle_are_both_accepted(self):
        """Control: the check must not reject the two shapes we ship.

        Without this, a preflight that rejected *every* bundle would pass both
        tests above.
        """
        for label, archs in (("universal", None), ("native", NATIVE_ARCH)):
            with self.subTest(build=label), tempfile.TemporaryDirectory() as td:
                app = make_update_app(td)
                put_binary(app / "Contents" / "MacOS" / "ClaudePet", archs)
                put_binary(app / "Contents" / "MacOS" / "python", archs)
                self.assertTrue(
                    self.validate(app),
                    f"a {label} build was rejected — that is a shape we ship")

    def test_the_main_executable_and_info_plist_must_be_regular_files(self):
        """Both are read to decide identity; a symlink decides it elsewhere.

        A symlinked `Info.plist` lets the bundle present someone else's
        identity, and a symlinked executable means the thing that runs is not
        the thing that was signed and validated.
        """
        for label, rel in (("Info.plist", "Contents/Info.plist"),
                           ("main executable", "Contents/MacOS/ClaudePet")):
            with self.subTest(member=label), tempfile.TemporaryDirectory() as td:
                app = make_update_app(td)
                victim = app / rel
                # The link points at the *real* member, moved aside: relative,
                # inside the bundle, and perfectly readable through. So the
                # containment rule cannot be what rejects this, and neither can
                # "the plist wouldn't parse" — only a rule about the member
                # itself being a symlink. An earlier version pointed the plist
                # at the executable and passed because plistlib choked on a
                # Mach-O, which tested nothing.
                real = victim.parent / (victim.name + "-real")
                shutil.move(str(victim), str(real))
                os.symlink(real.name, victim)
                self.assertTrue(victim.is_symlink(), "fixture is not a symlink")
                self.assertTrue(victim.exists(),
                                "fixture link is dangling; it must resolve")
                self.assertFalse(
                    self.validate(app),
                    f"a symlinked {label} was accepted")


class SigningAuthorityPreflightTests(IsolatedTest):
    """Signer identity is established by two independent fail-closed gates.

    `codesign -R` binds the certificate Team ID; `spctl -vv` then proves that
    Gatekeeper attributed the accepted bundle to that signer.  A bundle path
    is deliberately allowed to contain our Team ID below: searching all of
    spctl's output would let that unrelated path line impersonate `origin=`.
    """

    EXPECTED_TEAM_ID = "RXGNVSLYF5"

    @staticmethod
    def _signing_tools(runner):
        return [tool for tool in runner.tools()
                if tool in ("codesign", "spctl", "stapler")]

    def _assert_spctl_origin_rejected(self, spctl_stderr, label):
        with tempfile.TemporaryDirectory() as td:
            deceptive_root = Path(td) / ("unrelated-path-" + self.EXPECTED_TEAM_ID)
            deceptive_root.mkdir()
            app = make_update_app(deceptive_root)
            runner = PreflightRunRecorder()
            runner.SPCTL_STDERR = spctl_stderr
            rendered = spctl_stderr.format(path=app)
            origin_lines = [line.strip() for line in rendered.splitlines()
                            if line.strip().startswith("origin=")]

            self.assertIn(
                self.EXPECTED_TEAM_ID, rendered,
                "fixture no longer distinguishes an origin-line parser from "
                "a whole-output Team-ID substring search")
            self.assertTrue(
                all(self.EXPECTED_TEAM_ID not in line for line in origin_lines),
                "the negative fixture accidentally names our Team in origin=")

            with mock.patch.object(claude_pet.subprocess, "run", runner):
                accepted = claude_pet.validate_update_app(app, "99.0")

            self.assertFalse(
                accepted,
                f"spctl rc=0 with {label} origin= was accepted because an "
                "unrelated path line contained our Team ID")
            self.assertEqual(
                self._signing_tools(runner), ["codesign", "spctl"],
                "the signer-origin rejection did not occur at the spctl gate")

    def test_spctl_success_without_origin_is_rejected_even_when_path_has_team_id(self):
        self._assert_spctl_origin_rejected(
            "{path}: accepted\nsource=Notarized Developer ID\n",
            "missing")

    def test_spctl_success_with_foreign_origin_is_rejected_even_when_path_has_team_id(self):
        self._assert_spctl_origin_rejected(
            "{path}: accepted\n"
            "source=Notarized Developer ID\n"
            "origin=Developer ID Application: Foreign Vendor (FOREIGN1234)\n",
            "foreign")

    def test_codesign_failure_rejects_before_gatekeeper_and_ticket(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            with (app / "Contents" / "Info.plist").open("rb") as f:
                plist = plistlib.load(f)
            self.assertEqual(plist["CFBundleIdentifier"], claude_pet.BUNDLE_ID)

            runner = PreflightRunRecorder({"codesign": 17})
            with mock.patch.object(claude_pet.subprocess, "run", runner):
                accepted = claude_pet.validate_update_app(app, "99.0")

            self.assertFalse(
                accepted,
                "a nonzero codesign result was ignored although bundle ID, "
                "Gatekeeper output, and ticket fixture were otherwise valid")
            self.assertEqual(
                self._signing_tools(runner), ["codesign"],
                "a failed Team/signature requirement did not stop preflight")

    def test_codesign_call_binds_the_exact_expected_team_requirement(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            runner = PreflightRunRecorder()
            with mock.patch.object(claude_pet.subprocess, "run", runner):
                self.assertTrue(claude_pet.validate_update_app(app, "99.0"))

            calls = [argv for tool, argv, _kwargs in runner.calls
                     if tool == "codesign"]
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0],
                ["/usr/bin/codesign", "--verify", "--deep", "--strict",
                 "-R", '=anchor apple generic and certificate leaf[subject.OU] = '
                       '"RXGNVSLYF5"', str(app)],
                "codesign was not given the exact certificate-Team "
                "requirement; a generic valid signature is not sufficient")


class RealBundleAcceptanceTests(IsolatedTest):
    """The permanent regression test against over-strict containment.

    Our shipped bundle carries internal framework symlinks. A rule of "no
    symlinks anywhere" rejects it — and the update that would fix such a rule
    is itself an update, so the mistake is not recoverable in the field. This
    test exists so a later, stricter rewrite of the walk fails here first.
    """

    def setUp(self):
        _require_live_opt_in(self, "the installed-app preflight")

    def test_the_real_installed_bundle_is_accepted_by_the_preflight(self):
        if not os.path.isdir(INSTALLED_APP):
            _skip_loudly(self, f"the installed app is not present at "
                               f"{INSTALLED_APP}")
        try:
            with open(os.path.join(INSTALLED_APP, "Contents", "Info.plist"),
                      "rb") as f:
                version = plistlib.load(f).get("CFBundleShortVersionString")
        except Exception as e:
            _skip_loudly(self, f"cannot read the installed Info.plist "
                               f"({type(e).__name__})")
        if subprocess.run(["/usr/bin/codesign", "--verify", INSTALLED_APP],
                          capture_output=True).returncode != 0:
            _skip_loudly(self, f"{INSTALLED_APP} is not validly signed "
                               "(a local unsigned build?)")
        if subprocess.run(["/usr/sbin/spctl", "--assess", "--type", "execute",
                           INSTALLED_APP], capture_output=True).returncode != 0:
            _skip_loudly(self, f"{INSTALLED_APP} is not notarized")
        self.assertTrue(
            claude_pet.validate_update_app(INSTALLED_APP, version),
            "the preflight rejected our own shipped, signed, notarized "
            "bundle — every future update would be refused, including the one "
            "that would fix this")

    def test_the_real_bundle_contains_the_symlinks_this_guard_is_about(self):
        """Discrimination: without an internal symlink the guard above is vacuous."""
        if not os.path.isdir(INSTALLED_APP):
            _skip_loudly(self, f"the installed app is not present at "
                               f"{INSTALLED_APP}")
        links = [os.path.join(root, name)
                 for root, dirs, files in os.walk(INSTALLED_APP)
                 for name in dirs + files
                 if os.path.islink(os.path.join(root, name))]
        self.assertTrue(
            links,
            "the installed bundle has no symlinks at all, so accepting it "
            "proves nothing about the containment rule")
        for link in links:
            self.assertFalse(
                os.path.isabs(os.readlink(link)),
                f"{link} points outside by absolute path — unexpected in a "
                "shipped bundle; the acceptance guard needs re-examining")


class LockIsolationInstrumentTests(IsolatedTest):
    """The fixtures that keep this suite out of the user's home, tested.

    An alarm that has never been seen firing is not evidence of anything, and
    a redirection that is never exercised is decorative. Both are checked
    here, against scratch paths — the alarm's real targets must not be
    disturbed to test it.
    """

    def setUp(self):
        self.td = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)

    def test_the_lock_lands_in_the_fixture_cache_not_the_real_one(self):
        """The redirection is load-bearing, not decorative.

        This is the half of the guarantee `real_home_violations()` cannot
        supply: taking a `flock` on an already-present file changes no
        metadata, so no stat-based alarm can see it. What can be shown is that
        the path production computes lands inside the fixture, which is the
        thing that keeps it away from the real file in the first place.
        """
        app = make_update_app(self.td)
        fd = claude_pet._acquire_update_lock(str(app))
        self.assertIsNotNone(
            fd, "the lock could not be taken at all, so where it would have "
                "landed is unknown")
        self.addCleanup(os.close, fd)

        lock = claude_pet._update_lock_path(str(app))
        self.assertTrue(os.path.isfile(lock),
                        f"no lock file was created at {lock}")
        self.assertTrue(
            lock.startswith(_ISOLATION["cache"] + os.sep),
            f"the lock landed at {lock}, outside the fixture cache "
            f"{_ISOLATION['cache']}")
        self.assertFalse(
            lock.startswith(REAL_HOME + os.sep),
            f"the lock landed inside the user's real home: {lock}")

    def test_a_child_process_computes_the_lock_path_from_the_fixture_home(self):
        """The constant patch does not cross a process boundary; HOME does.

        A child re-imports `claude_pet` and gets the shipped `UPDATE_LOCK_DIR`
        back, so the only thing keeping it out of the real home is the
        environment. Without this, an isolation that patched the constant
        alone would look complete.
        """
        probe = subprocess.run(
            [sys.executable, "-c",
             textwrap.dedent("""
                 import sys
                 sys.path.insert(0, sys.argv[1])
                 import claude_pet
                 print(claude_pet._update_lock_path("/nowhere/ClaudePet.app"))
             """), str(Path(claude_pet.__file__).parent)],
            capture_output=True, text=True, env=self.script_env(), timeout=60)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        path = probe.stdout.strip()
        self.assertTrue(
            path.startswith(_ISOLATION["home"] + os.sep),
            f"a child process resolved the lock path to {path}, outside the "
            f"fixture home {_ISOLATION['home']}")

    def test_the_bypass_alarm_notices_each_way_the_watched_paths_can_change(self):
        """Mutation-style check of the alarm's own discrimination.

        Every row here is a way a stray write shows up. If any of them reads
        as "unchanged", the tearDown alarm is green for a reason unrelated to
        the tests being clean.
        """
        watched = os.path.join(self.td, "cache")
        self.assertIsNone(dir_fingerprint(watched),
                          "an absent directory must not read as a state")
        os.makedirs(watched)
        empty = dir_fingerprint(watched)
        self.assertEqual(empty, {})
        self.assertNotEqual(
            empty, None,
            "a directory created where none existed is invisible to the alarm")

        lock = os.path.join(watched, "update-ClaudePet.app.lock")
        Path(lock).touch()
        created = dir_fingerprint(watched)
        self.assertNotEqual(created, empty,
                            "a new lock file is invisible to the alarm")

        with open(lock, "a") as f:
            f.write("grown")
        self.assertNotEqual(dir_fingerprint(watched), created,
                            "a file that grew is invisible to the alarm")

        os.makedirs(os.path.join(watched, "nested", "deeper"))
        with_nested = dir_fingerprint(watched)
        self.assertNotIn("nested/deeper", [k for k in with_nested
                                           if os.sep not in k])
        self.assertIn(os.path.join("nested", "deeper"), with_nested,
                      "the alarm only looks one level down, so a lock file "
                      "dropped in a subdirectory would go unseen")

        log = os.path.join(self.td, "claudepet_debug.log")
        self.assertIsNone(file_fingerprint(log),
                          "an absent log must not read as a state")
        Path(log).write_text("[update] one line\n")
        before = file_fingerprint(log)
        with open(log, "a") as f:
            f.write("[update] previous app kept for recovery: /x\n")
        self.assertNotEqual(file_fingerprint(log), before,
                            "an append to the debug log is invisible to the "
                            "alarm — which is exactly what the replacement "
                            "script's KEEP_BACKUP branch does")


class LaunchRegistrationInstrumentTests(IsolatedTest):
    """The LaunchServices check, tested the only way it can honestly be.

    The obvious control — register a fixture bundle, then see the check find
    it — is exactly the machine-global write this check exists to prevent, so
    it is not available. What is available splits in two, and both halves are
    needed: the parser is exercised against a synthetic dump, where every case
    including the ones that must *not* match can be written down; and it is
    exercised against the real database, which is what shows the record shape
    it parses is the shape `lsregister` actually prints.
    """

    SYNTHETIC = "\n".join((
        "bundle id:                  me.yeongyu.claudepet (0x1)",
        "path:                       /tmp/root/a/ClaudePet.app (0x1)",
        "identifier:                 me.yeongyu.claudepet",
        "-" * 80,
        "bundle id:                  me.yeongyu.claudepet (0x2)",
        "path:                       /tmp/elsewhere/ClaudePet.app (0x2)",
        "identifier:                 me.yeongyu.claudepet",
        "-" * 80,
        "bundle id:                  com.example.other (0x3)",
        "path:                       /tmp/root/b/Other.app (0x3)",
        "identifier:                 com.example.other",
        "-" * 80,
        "bundle id:                  me.yeongyu.claudepet (0x4)",
        "identifier:                 me.yeongyu.claudepet",
    ))

    def test_the_parser_selects_by_identifier_and_by_root(self):
        self.assertEqual(
            registrations_in(self.SYNTHETIC, BUNDLE_ID, "/tmp/root"),
            ["/tmp/root/a/ClaudePet.app"])

    def test_each_rejected_record_is_rejected_for_its_own_reason(self):
        """Without this, one over-broad filter would look like a clean pass."""
        all_ids = registrations_in(self.SYNTHETIC, None, "/tmp/root")
        self.assertEqual(all_ids,
                         ["/tmp/root/a/ClaudePet.app", "/tmp/root/b/Other.app"],
                         "the root filter is not what excluded the other app")
        anywhere = registrations_in(self.SYNTHETIC, BUNDLE_ID, None)
        self.assertEqual(anywhere,
                         ["/tmp/elsewhere/ClaudePet.app",
                          "/tmp/root/a/ClaudePet.app"],
                         "the identifier filter is not what excluded the "
                         "out-of-root record")
        self.assertEqual(
            len(registrations_in(self.SYNTHETIC)), 3,
            "the record with no path was counted, or a record was lost")

    def test_the_parser_reads_the_real_database(self):
        """The synthetic dump above proves nothing about the real format."""
        dump = lsregister_dump()
        if not dump:
            _skip_loudly(self, f"no readable LaunchServices dump at "
                               f"{LSREGISTER}")
        self.assertGreater(len(registrations_in(dump)), 100,
                           "the record separator or the field patterns do not "
                           "match what lsregister prints")
        self.assertIn(
            "/System/Applications/Calculator.app",
            registrations_in(dump, "com.apple.calculator"),
            "a record known to be present was not found, so an empty result "
            "for our own bundle id would mean nothing")

    def test_no_fixture_bundle_of_this_run_claims_the_production_identity(self):
        """The assertion itself, run early enough to attribute.

        `tearDownModule` asks the same question once more at the end. This one
        is scoped identically — to the temp root created by `setUpModule` — so
        it can only ever see registrations this run made.
        """
        self.assertEqual(
            launch_registration_violations(_ISOLATION["root"]), [])


class DownloadSeamInstrumentTests(IsolatedTest):
    """The download stand-in and the socket guard, tested as instruments.

    Neither is a claim about production. They are the two fixtures every
    install test in this file now rests on, and a fixture nobody has watched
    work is indistinguishable from one that does nothing — which is precisely
    what the retired `urlretrieve` patches were.
    """

    def setUp(self):
        self.td = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.app = os.path.join(self.td, "ClaudePet.app")
        if claude_pet.urllib.request.getproxies():
            _skip_loudly(self, "a proxy is configured, so a blocked request "
                               "would be routed somewhere this guard cannot "
                               "reason about")

    def install(self):
        return claude_pet.install_github_update(
            "https://example.test/a.zip", app_path=self.app,
            expect_version="99.0")

    def test_the_module_under_test_is_the_repository_copy(self):
        """Everything below reads production source; this says whose."""
        self.assertEqual(
            os.path.realpath(claude_pet.__file__),
            os.path.realpath(str(Path(__file__).resolve().parent.parent
                                 / "claude_pet.py")),
            f"claude_pet was imported from {claude_pet.__file__}")

    def test_production_downloads_through_the_name_the_fixtures_patch(self):
        source = inspect.getsource(claude_pet.install_github_update)
        self.assertIn("_download_update_zip(", source)
        self.assertNotIn("urlretrieve", source)

    def test_the_stand_in_intercepts_the_download(self):
        seen = []

        def fetch(url, dest):
            seen.append((url, dest))
            Path(dest).write_bytes(b"not a zip")

        with patch_download(fetch):
            self.assertFalse(self.install(),
                             "a bogus archive must not install")
        self.assertEqual(len(seen), 1, "the seam was not reached exactly once")
        self.assertEqual(seen[0][0], "https://example.test/a.zip")
        self.assertTrue(seen[0][1].endswith("u.zip"), seen[0][1])
        self.assertEqual(take_network_attempts(), [],
                         "the stand-in was in place and the network was still "
                         "reached")

    def test_patching_the_retired_name_intercepts_nothing_and_reaches_out(self):
        """The mutant: the fixture style this file used to use, run.

        This is the evidence that rewriting the call sites was necessary
        rather than tidy. `install_github_update` swallows the guard's
        exception in its `except Exception: return False`, so the return value
        says nothing — the recorded attempt is the whole finding.
        """
        with mock.patch.object(claude_pet.urllib.request,
                               "urlretrieve") as fetch:
            self.assertFalse(self.install())
        attempts = take_network_attempts()
        self.assertFalse(
            fetch.called,
            "production called urlretrieve after all; if this fails the seam "
            "moved back and the fixtures should follow it")
        self.assertTrue(
            attempts,
            "patching the retired name left the real download running, yet "
            "no outbound socket was recorded — the guard is not watching")
        self.assertIn("example.test", " ".join(attempts))

    def test_the_guard_records_and_refuses_a_direct_request(self):
        """Positive control: the guard fires when nothing is patched at all."""
        with self.assertRaises(NetworkReached):
            claude_pet.urllib.request.urlopen("https://example.test/a.zip",
                                              timeout=1)
        self.assertTrue(take_network_attempts(),
                        "the guard raised without recording, so the tearDown "
                        "alarm would never see it")

    def test_the_guard_lets_loopback_through(self):
        """Negative control: it blocks by destination, not by being a socket.

        Without this, a guard that refused *everything* would look identical,
        and the first test that needs a local server would be unexplainable.
        """
        server = socket.socket()
        self.addCleanup(server.close)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client = socket.create_connection(server.getsockname(), timeout=5)
        self.addCleanup(client.close)
        accepted, _ = server.accept()
        self.addCleanup(accepted.close)
        self.assertEqual(take_network_attempts(), [],
                         "a loopback connection was recorded as an escape")


class ConcurrentInstallTests(IsolatedTest):
    """Two updaters on one installed app must serialize.

    Unique staging names prevent a *path* collision and nothing more: two
    updaters still operate the same `$APP`, and one can swap while the other
    sits between its own swap and its cleanup.

    **Where the lock lives, and why these tests were rewritten.** They were
    written against a lock the replacement *script* took, and the script no
    longer takes one. It now lives in `install_github_update`:
    `_acquire_update_lock` opens the file `O_NOFOLLOW|O_NONBLOCK`, `fstat`s it
    for `S_ISREG` / our uid / not group-or-world-writable, takes
    `flock(LOCK_EX|LOCK_NB)`, and the descriptor is handed to the helper
    through `pass_fds`. The parent then closes **its own** copy in its
    `finally` — it must, because `flock` is released when the last descriptor
    on the open file description closes, and a parent that kept a copy would
    keep the lock alive after the helper died.

    That last detail is what made the old tests wrong rather than merely
    outdated: they mocked `subprocess.Popen`, so **nothing ever inherited the
    descriptor**, the parent's `finally` closed the only copy, and the lock
    was released the instant the first install returned. The second install
    then succeeded, and the test failed against correct production code.

    So the helper is spawned for real here — a process that does nothing but
    hold the inherited descriptor.
    """

    # Does not import claude_pet, and does not touch the descriptor: it holds
    # the lock purely by existing, which is exactly what the real helper does
    # between being spawned and finishing the swap.
    HOLDER = textwrap.dedent("""
        import sys, time
        sys.stdout.write("up\\n")
        sys.stdout.flush()
        time.sleep(300)
    """)

    def setUp(self):
        self.td = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.app = make_update_app(self.td)
        claude_pet._upd_cache.clear()

    @staticmethod
    def reap(child):
        if child.poll() is None:
            child.kill()
        child.wait(timeout=30)
        if child.stdout is not None:
            child.stdout.close()

    def install(self, spawn_helper=True, **kw):
        """One install, with the replacement helper swapped for a placeholder.

        Everything up to the spawn is production: the lock, the download, the
        member scan, both `ditto` calls, the staging reservation. Only the
        argv handed to `Popen` is replaced — `pass_fds` is passed through
        untouched, so the placeholder inherits the real descriptor at the real
        number.
        """
        work = tempfile.mkdtemp(dir=self.td)
        record = {"pass_fds": None, "child": None, "popen_calls": 0}

        def fetch(_url, path):
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("ClaudePet.app/Contents/Info.plist", "x")
                zf.writestr("ClaudePet.app/Contents/MacOS/ClaudePet", "x")

        real_popen = subprocess.Popen

        def popen(argv, *a, **kwargs):
            record["popen_calls"] += 1
            record["pass_fds"] = tuple(kwargs.get("pass_fds", ()))
            if not spawn_helper:
                return mock.Mock()
            child = real_popen(
                [sys.executable, "-c", self.HOLDER],
                stdout=subprocess.PIPE, text=True,
                pass_fds=record["pass_fds"], env=self.script_env())
            record["child"] = child
            self.addCleanup(self.reap, child)
            self.assertEqual(
                child.stdout.readline().strip(), "up",
                "the placeholder helper never started, so it cannot be "
                "holding anything")
            return child

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               return_value=work), \
             patch_download(fetch), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_ditto), \
             mock.patch.object(claude_pet, "validate_update_app",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "Popen", popen):
            ok = claude_pet.install_github_update(
                "https://example.test/a.zip", app_path=str(self.app),
                expect_version="99.0", **kw)
        return ok, record

    def reacquire(self, seconds=10):
        """Try to take the lock, briefly, since a kill is asynchronous."""
        deadline = time.monotonic() + seconds
        while True:
            fd = claude_pet._acquire_update_lock(str(self.app))
            if fd is not None or time.monotonic() > deadline:
                return fd
            time.sleep(0.05)

    def test_one_install_succeeds_and_schedules_exactly_one_helper(self):
        """Control: without it, an installer that always refused would pass."""
        ok, record = self.install()
        self.assertTrue(ok, "a lone install was refused")
        self.assertEqual(record["popen_calls"], 1,
                         "the update scheduled no replacement helper")

    def test_the_lock_changes_hands_and_is_released_by_the_kernel(self):
        """The whole handoff lifecycle, in one fixture.

        Three facts, and each is worthless without the others:

        1. **The parent lets go.** After a successful dispatch its own
           descriptor is closed (EBADF). A parent that kept it would keep the
           lock alive after the helper died, wedging every later update.
        2. **The helper holds.** Re-acquisition fails while the placeholder
           lives — so the lock genuinely travelled across the process
           boundary through `pass_fds`, rather than simply never existing.
        3. **The kernel releases.** Re-acquisition succeeds once the
           placeholder is killed. `flock` is released when the last descriptor
           closes, so a *crashed* updater cannot leave a stale lock — the
           property an `O_EXCL` lock file would not have.

        Split across three fixtures these are individually satisfiable by the
        wrong code: (1) alone passes if the lock was never taken, (3) alone
        passes if it is never held. Together they pin the handoff.
        """
        ok, record = self.install()
        self.assertTrue(ok, "the lone install was refused, so there is no "
                            "handoff to observe")
        self.assertEqual(
            len(record["pass_fds"]), 1,
            "the helper was spawned without exactly one inherited descriptor: "
            f"pass_fds={record['pass_fds']!r}")
        lock_fd = record["pass_fds"][0]

        # 1. The parent's copy is gone. (If the number had been recycled by a
        # later open, fstat would succeed and this fails loudly — it cannot
        # pass for the wrong reason.)
        with self.assertRaises(OSError) as caught:
            os.fstat(lock_fd)
        self.assertEqual(
            caught.exception.errno, errno.EBADF,
            "the installer kept its own copy of the lock descriptor; the "
            "lock would then outlive the helper that owns it")

        # 2. The helper holds it.
        self.assertIsNone(
            claude_pet._acquire_update_lock(str(self.app)),
            "the lock was available while the spawned helper was still "
            "running, so nothing serializes two updaters")

        # 3. The kernel releases it when that helper dies.
        self.reap(record["child"])
        fd = self.reacquire()
        self.assertIsNotNone(
            fd, "the lock was never released after its holder was killed; one "
                "crashed updater wedges every future update")
        os.close(fd)

    def test_a_second_install_is_refused_while_the_first_helper_lives(self):
        """The same property at the entry point the app actually calls."""
        first_ok, _first = self.install()
        self.assertTrue(first_ok, "the first install failed; nothing holds "
                                  "the lock, so the second proves nothing")
        second_ok, second = self.install()
        self.assertFalse(
            second_ok,
            "a second updater started while the first was still in flight; "
            "they operate the same app and can swap over each other")
        self.assertEqual(
            second["popen_calls"], 0,
            "the refused install still spawned a replacement helper")

    def test_an_install_is_possible_again_once_the_first_helper_exits(self):
        """Discrimination for the test above: the refusal is not permanent.

        Without this, an `install_github_update` that refused every call after
        the first — for any reason, lock or not — would pass the refusal test.
        """
        first_ok, first = self.install()
        self.assertTrue(first_ok)
        self.reap(first["child"])
        again_ok, again = self.install()
        self.assertTrue(
            again_ok,
            "no further update was possible after the first helper exited")
        self.assertEqual(again["popen_calls"], 1)


class ZipMemberScanTests(IsolatedTest):
    """The archive is screened *before* extraction.

    A member that escapes the temp directory is gone by the time a
    post-extraction walk of the bundle runs — the walk cannot see what is no
    longer inside the tree it walks.
    """

    def setUp(self):
        # The install path's parent is a real directory that gets written to:
        # production claims its staging reservation beside `app_path`. Pointed
        # at `/Applications` — as this class used to be — the reservation is
        # made in `/Applications` for real, and a run that dispatches leaves it
        # there. It belongs in a temp directory like everything else.
        self.parent = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.parent, True)
        # The final handoff now requires the identity of the installed app that
        # was examined while the update lock was held. A nonexistent pathname
        # makes the positive control fail at that later gate and can therefore
        # masquerade as a ZIP-scan result. Give every case a real temp-only
        # installed object; malicious archives must still stop before ditto.
        self.app = str(make_update_app(self.parent, version="0.19"))
        self.app_id = claude_pet._path_ident_str(self.app)
        self.assertTrue(self.app_id, "installed-app fixture has no identity")
        claude_pet._upd_cache.clear()

    def install(self, members, expect_version="99.0"):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        self.work_id = claude_pet._path_ident_str(td)
        self.assertTrue(self.work_id, "work fixture has no identity")

        def fetch(_url, path):
            with zipfile.ZipFile(path, "w") as zf:
                for name, data in members:
                    zf.writestr(name, data)

        # `fake_ditto` rather than a mkdir: real `ditto` merges into an
        # existing destination, and production hands it a staging directory it
        # has already claimed. See `fake_ditto`.
        run = mock.Mock(side_effect=fake_ditto)
        with mock.patch.object(claude_pet.tempfile, "mkdtemp", return_value=td), \
             patch_download(fetch), \
             mock.patch.object(claude_pet.subprocess, "run", run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            ok = claude_pet.install_github_update(
                "https://example.test/a.zip",
                app_path=self.app,
                expect_version=expect_version)
        return ok, run, popen

    def test_a_traversing_member_is_rejected_before_extraction(self):
        ok, run, popen = self.install([
            ("ClaudePet.app/Contents/Info.plist", "x"),
            ("../../../../Library/LaunchAgents/evil.plist", "x")])
        self.assertFalse(ok)
        self.assertFalse(run.called, "extraction ran despite a `..` member")
        self.assertFalse(popen.called)

    def test_an_absolute_member_is_rejected_before_extraction(self):
        ok, run, popen = self.install([
            ("ClaudePet.app/Contents/Info.plist", "x"),
            ("/tmp/claudepet-evil", "x")])
        self.assertFalse(ok)
        self.assertFalse(run.called, "extraction ran despite an absolute member")
        self.assertFalse(popen.called)

    def test_an_unreadable_archive_is_rejected_before_extraction(self):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        run = mock.Mock(return_value=mock.Mock(returncode=0))
        with mock.patch.object(claude_pet.tempfile, "mkdtemp", return_value=td), \
             patch_download(lambda _u, p: Path(p).write_bytes(b"not a zip")), \
             mock.patch.object(claude_pet.subprocess, "run", run):
            self.assertFalse(claude_pet.install_github_update(
                "https://example.test/a.zip",
                app_path=self.app,
                expect_version="99.0"))
        self.assertFalse(run.called, "extraction ran on an unreadable archive")

    def test_an_ordinary_archive_still_reaches_extraction(self):
        """Guard: the scan must not reject the archive we actually ship."""
        ok, run, popen = self.install([
            ("ClaudePet.app/Contents/Info.plist", "x"),
            ("ClaudePet.app/Contents/MacOS/ClaudePet", "x")])
        self.assertTrue(run.called, "a clean archive never reached extraction")
        self.assertTrue(ok)
        self.assertEqual(popen.call_count, 1,
                         "the clean archive never reached helper handoff")
        helper = popen.call_args.args[0][2]
        self.assertIn(f"APPID={self.app_id}", helper)
        self.assertIn(f"WORKID={self.work_id}", helper)


# ───────────── item 4: stapler in the preflight ─────────────

class StaplerPreflightTests(IsolatedTest):
    """`xcrun stapler validate <app>` joins codesign and spctl, fail-closed."""

    def test_preflight_consults_stapler(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            runner = PreflightRunRecorder()
            with mock.patch.object(claude_pet.subprocess, "run", runner):
                self.assertTrue(claude_pet.validate_update_app(app, "99.0"))
            self.assertIn("stapler", runner.tools(),
                          "the preflight never checked for a stapled ticket")
            stapler = next(argv for tool, argv, _kw in runner.calls
                           if tool == "stapler")
            self.assertIn("validate", stapler)
            self.assertIn(str(app), stapler)

    def test_an_unstapled_bundle_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            runner = PreflightRunRecorder({"stapler": 65})
            with mock.patch.object(claude_pet.subprocess, "run", runner):
                self.assertFalse(claude_pet.validate_update_app(app, "99.0"))

    def test_a_tool_that_cannot_run_fails_closed(self):
        for tool in ("codesign", "spctl", "stapler"):
            for exc in (OSError("no such tool"),
                        subprocess.TimeoutExpired(cmd=tool, timeout=60)):
                with self.subTest(tool=tool, exc=type(exc).__name__), \
                     tempfile.TemporaryDirectory() as td:
                    app = make_update_app(td)
                    runner = PreflightRunRecorder(raise_by_tool={tool: exc})
                    with mock.patch.object(claude_pet.subprocess, "run", runner):
                        self.assertFalse(
                            claude_pet.validate_update_app(app, "99.0"),
                            f"{tool} raising {type(exc).__name__} did not "
                            "reject the bundle")

    def test_every_preflight_tool_runs_under_a_timeout(self):
        """A hung signing tool must not wedge the update thread forever."""
        with tempfile.TemporaryDirectory() as td:
            app = make_update_app(td)
            runner = PreflightRunRecorder()
            with mock.patch.object(claude_pet.subprocess, "run", runner):
                claude_pet.validate_update_app(app, "99.0")
            self.assertTrue(runner.calls)
            for tool, _argv, kwargs in runner.calls:
                if tool in ("codesign", "spctl"):
                    self.assertEqual(kwargs.get("timeout"), 60,
                                     f"{tool} ran without timeout=60")
                else:
                    # The brief fixes 60 for codesign/spctl; for stapler it
                    # requires only that a hang cannot wedge the thread.
                    self.assertTrue(kwargs.get("timeout"),
                                    f"{tool} ran with no timeout at all")


class StaplerLiveContractTests(IsolatedTest):
    """The real binary, because a mock cannot validate an argument."""

    def setUp(self):
        _require_live_opt_in(self, "the real stapler contract")
        if not os.path.exists(XCRUN):
            _skip_loudly(self, f"xcrun is not present at {XCRUN}")

    def _run(self, argv):
        return subprocess.run(argv, capture_output=True, text=True)

    def test_stapler_reports_success_for_our_stapled_bundle(self):
        if not os.path.exists(INSTALLED_APP):
            _skip_loudly(self, f"the installed app is not present at "
                               f"{INSTALLED_APP}")
        result = self._run([XCRUN, "stapler", "validate", INSTALLED_APP])
        combined = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            _skip_loudly(self, "the installed app carries no stapled ticket "
                               f"({combined.strip()!r})")
        self.assertIn("The validate action worked", combined)

    def test_stapler_rejects_an_unstapled_bundle_with_rc_65(self):
        if not os.path.exists(UNSTAPLED_APP):
            _skip_loudly(self, f"no unstapled bundle at {UNSTAPLED_APP}")
        result = self._run([XCRUN, "stapler", "validate", UNSTAPLED_APP])
        self.assertEqual(result.returncode, 65,
                         "stapler did not reject a bundle with no ticket — "
                         "the check cannot discriminate")


# ───────────── items 5-8: the replacement script ─────────────

def script_for(app, newapp, workdir, **kwargs):
    """Generate a helper bound to the exact temp objects the caller owns."""
    app = os.path.realpath(str(app))
    newapp = os.path.realpath(str(newapp))
    workdir = os.path.realpath(str(workdir))
    app_id = claude_pet._path_ident_str(app)
    work_id = claude_pet._path_ident_str(workdir)
    if not app_id or not work_id:
        raise AssertionError(
            "replacement-script fixture requires existing APP and WORK objects")
    return claude_pet._update_replace_script(
        app, newapp, workdir, app_id=app_id, work_id=work_id, **kwargs)


# Production defines the launch primitive once and consumes it at two distinct
# call sites. Any script this module executes first pins that exact grammar,
# then changes the definition to `:` before it rewrites either call. This order
# is fail-closed: a renamed or duplicated call raises instead of letting the
# real LaunchServices `open` escape into a test run.
LAUNCH_DEFINITION = "LAUNCH=open"
LAUNCH_PRIMARY = '$LAUNCH "$APP"'
LAUNCH_RESTORE = '( $LAUNCH "$RESTORED" )'


def assert_launch_grammar(command):
    expected = {
        LAUNCH_DEFINITION: 1,
        LAUNCH_PRIMARY: 1,
        LAUNCH_RESTORE: 1,
    }
    for literal, count in expected.items():
        actual = command.count(literal)
        if actual != count:
            raise AssertionError(
                f"replacement script has {actual} copies of {literal!r}; "
                f"expected exactly {count}")
    if command.count("$LAUNCH") != 2:
        raise AssertionError("replacement script must consume $LAUNCH twice")


def replace_launch_points(command, launcher, relauncher="( : )"):
    """Pin, neutralize, then substitute both launch consumers exactly once."""
    assert_launch_grammar(command)
    command = command.replace(LAUNCH_DEFINITION, "LAUNCH=:", 1)
    command = command.replace(LAUNCH_PRIMARY, launcher, 1)
    command = command.replace(LAUNCH_RESTORE, relauncher, 1)
    if LAUNCH_DEFINITION in command:
        raise AssertionError("the live launch definition survived neutralization")
    assert_no_live_open(command)
    return command


def assert_no_live_open(command):
    """No `open` on a shell variable survived the substitution."""
    if "LAUNCH=open" in command:
        raise AssertionError("the replacement script still defines LAUNCH=open")
    live = [line for line in command.split("\n")
            if re.search(r'(?:^|[;&|(\s])open\s+"\$', line)]
    if live:
        raise AssertionError(
            "a live `open` remains in a script this suite is about to run:\n  "
            + "\n  ".join(live))


class ReplaceScriptTextTests(IsolatedTest):
    """Ordering and wiring that a single run cannot demonstrate.

    NOTE: `test_script_keeps_the_literal_substrings_other_tests_pin` is a
    **guard** — `tests/test_settings_and_install.py` matches those literals.
    """

    def setUp(self):
        self.td = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.app = Path(self.td) / "installed" / "ClaudePet.app"
        self.work = Path(self.td) / "work"
        self.newapp = self.work / "ClaudePet.app"
        self.app.mkdir(parents=True)
        self.newapp.mkdir(parents=True)
        self.command = script_for(self.app, self.newapp, self.work)

    def test_script_keeps_the_literal_substrings_other_tests_pin(self):
        for literal in ("sleep 1.5", "/usr/bin/ditto",
                        LAUNCH_DEFINITION, LAUNCH_PRIMARY, LAUNCH_RESTORE):
            self.assertIn(literal, self.command)

    def test_launch_grammar_is_one_definition_and_two_exact_consumers(self):
        assert_launch_grammar(self.command)

    def test_execution_harness_neutralizes_the_primitive_before_consumers(self):
        safe = replace_launch_points(self.command, ":")
        self.assertEqual(safe.count("LAUNCH=:"), 1)
        self.assertNotIn(LAUNCH_DEFINITION, safe)
        self.assertNotIn(LAUNCH_PRIMARY, safe)
        self.assertNotIn(LAUNCH_RESTORE, safe)

    def test_script_carries_the_callers_exact_app_and_work_identities(self):
        app_id = claude_pet._path_ident_str(str(self.app))
        work_id = claude_pet._path_ident_str(str(self.work))
        self.assertIn(f"APPID={app_id}", self.command)
        self.assertIn(f"WORKID={work_id}", self.command)
        self.assertNotEqual(app_id, work_id,
                            "fixture collapses the two identity channels")

    def test_constructor_refuses_to_invent_missing_caller_identities(self):
        base = (str(self.app), str(self.newapp), str(self.work))
        app_id = claude_pet._path_ident_str(str(self.app))
        work_id = claude_pet._path_ident_str(str(self.work))
        for kwargs in ({"app_id": app_id}, {"work_id": work_id}, {}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                claude_pet._update_replace_script(*base, **kwargs)

    # The device check, spelled in full. `'/usr/bin/stat -f %d'` on its own is
    # a **prefix of** `'/usr/bin/stat -f %d,%i'`, which the script uses in
    # `rollback()` and `discard()` — and those are defined near the top, so
    # `str.index` on the short form returned an offset inside `rollback()`
    # rather than the device check's own. Every ordering conclusion drawn from
    # that offset was about the wrong line.
    DEVICE_CHECK = '/usr/bin/stat -f %d "$STAGE"'

    def assert_device_check_sits_between_staging_and_swap(self, command):
        """Written against a command argument so a mutant can be fed to it."""
        self.assertIn(self.DEVICE_CHECK, command)
        self.assertIn('/usr/bin/stat -f %d "$APP"', command)
        stat_at = command.index(self.DEVICE_CHECK)
        self.assertGreater(stat_at, command.index("/usr/bin/ditto"),
                           "the device check runs before STAGE exists")
        self.assertLess(stat_at, command.index('$APP/Contents/MacOS/python'),
                        "the device check runs after the swap")

    def test_same_filesystem_is_checked_after_staging_and_before_the_swap(self):
        """A cross-device swap cannot be atomic, and mv would copy instead."""
        self.assert_device_check_sits_between_staging_and_swap(self.command)

    def test_the_ordering_check_notices_the_device_check_moving(self):
        """Control: the assertion above must be able to fail.

        It reads as an ordering check and was, until this run, comparing an
        offset that pointed into a different function entirely — which no
        amount of reading revealed and one mutation does. The mutant lifts the
        device-check line to just before `ditto`, where it would run against a
        STAGE that does not exist yet.
        """
        line = self.find_whole_line(self.command, self.DEVICE_CHECK)
        moved = self.command.replace(line + "\n", "")
        moved = moved.replace("/usr/bin/ditto", line + "\n/usr/bin/ditto", 1)
        with self.assertRaises(AssertionError):
            self.assert_device_check_sits_between_staging_and_swap(moved)

    @staticmethod
    def find_whole_line(command, needle):
        for line in command.split("\n"):
            if needle in line:
                return line
        raise AssertionError(f"no line containing {needle!r}")

    def test_swap_goes_through_the_bundled_interpreter(self):
        self.assertIn('"$APP/Contents/MacOS/python"', self.command)
        self.assertIn("renamex_np", self.command)

    def test_forward_replacement_is_atomic_only_and_fails_closed(self):
        """A failed exchange must not reopen the old two-move install window."""
        start = self.command.index(
            'if exchange "$APP/Contents/MacOS/python" "$STAGE" "$APP"')
        end = self.command.index('BEFORE="$SELFPID', start)
        forward = self.command[start:end]
        self.assertIn("else\n  exit 1\nfi", forward)
        for legacy in ('rmdir "$BACKUP"', 'mv "$APP" "$BACKUP"',
                       'mv "$STAGE" "$APP"'):
            self.assertNotIn(
                legacy, forward,
                f"forward replacement restored the non-atomic step {legacy!r}")

    def test_launch_is_acknowledged_by_a_process_match_not_by_opens_exit_code(self):
        """`open` returning 0 means dispatched, not running.

        Ordering is asserted behaviourally (see ReplaceScriptBehaviourTests),
        not by string index — an acknowledgement helper may legitimately be
        *defined* above the launch and *called* below it.
        """
        self.assertIn("/usr/bin/pgrep", self.command)
        self.assertIn(str(os.getpid()), self.command,
                      "the scheduling pid is not excluded from the process "
                      "match; the exiting old app would answer for the new one")

    def test_a_retained_backup_is_recorded_where_the_user_can_find_it(self):
        self.assertIn("claudepet_debug.log", self.command)
        self.assertIn("KEEP_BACKUP", self.command)

    def rollback_body(self, command=None):
        command = self.command if command is None else command
        marker = "rollback() {"
        self.assertIn(marker, command, "no rollback() function to inspect")
        body = command.split(marker, 1)[1]
        end = body.find("\n}")
        self.assertNotEqual(end, -1, "rollback() is not closed")
        return body[:end]

    def assert_rollback_uses_the_old_bundles_interpreter(self, command):
        body = self.rollback_body(command)
        self.assertNotIn(
            '"$APP/Contents/MacOS/python"', body,
            "rollback runs the interpreter of the bundle that just failed")
        self.assertNotIn(
            '"$STAGE/Contents/MacOS/python"', body,
            "rollback runs an interpreter out of the staged new bundle")
        self.assertIn(
            '"$OLD_PATH/Contents/MacOS/python"', body,
            "rollback does not use the known-good old bundle's interpreter")

    def test_rollback_never_reaches_for_the_new_bundles_interpreter(self):
        """Recovery must not depend on the thing it is recovering from.

        Rollback runs precisely when the new bundle turned out to be broken,
        so a recovery step that executes the *new* app's interpreter fails in
        the only situation it exists for.

        **`$OLD_PATH`, not `$BACKUP`.** On the only forward path, atomic
        exchange leaves the old app at `$STAGE`. Rollback may use `$BACKUP` as
        a last-resort recovery location after a failed reverse exchange, but
        forward replacement must never route through it.
        """
        self.assert_rollback_uses_the_old_bundles_interpreter(self.command)

    def test_the_rollback_check_notices_an_interpreter_from_the_new_bundle(self):
        """Control: substitute the failed bundle's interpreter and it fails."""
        mutant = self.command.replace('"$OLD_PATH/Contents/MacOS/python"',
                                      '"$APP/Contents/MacOS/python"')
        self.assertNotEqual(mutant, self.command, "the mutation was a no-op")
        with self.assertRaises(AssertionError):
            self.assert_rollback_uses_the_old_bundles_interpreter(mutant)


class ReplaceScriptBehaviourTests(IsolatedTest):
    """The script actually run in a temp directory with launch neutralized.

    `replace_launch_points()` first pins the one `LAUNCH=open` definition and
    its two exact `$LAUNCH` consumers, then changes the definition to `:` before
    either consumer is rewritten. The primary consumer gets a stand-in that
    either does or does not leave a process under `<APP>/Contents/MacOS/`, which
    is exactly what acknowledgement polls for; the restore consumer remains an
    inert subshell on every failure path.
    """

    RUNS_THE_REPLACEMENT_SCRIPT = True

    def setUp(self):
        # realpath, not the raw mkdtemp result. On macOS mkdtemp returns
        # /var/… while a process's command line reports /private/var/… for the
        # same directory, so an anchored `pgrep -f "^$APP/…"` built from the
        # raw path cannot match a process genuinely running from it — every
        # ack test would then measure the wrong thing.
        self.td = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        # Reap only what this test started: processes launched from this
        # bundle's executable path, plus the Popen handles we hold. A blanket
        # `pkill -f <tempdir>` was killing the test runner itself partway
        # through the class.
        self.addCleanup(subprocess.run,
                        ["/usr/bin/pkill", "-f",
                         f"^{Path(self.td) / 'ClaudePet.app'}/Contents/MacOS/"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        check=False)
        self.installed = Path(self.td) / "ClaudePet.app"
        self.workdir = Path(self.td) / "update-work"
        self.newapp = self.workdir / "ClaudePet.app"
        self.exchange_log = Path(self.td) / "exchange-invocations.log"
        (self.installed / "Contents" / "MacOS").mkdir(parents=True)
        (self.installed / "old-marker").write_text("original")
        (self.newapp / "Contents" / "MacOS").mkdir(parents=True)
        (self.newapp / "new-marker").write_text("replacement")
        # A real executable at the launch path, so the started process's
        # command line *begins* with <APP>/Contents/MacOS/ — what a real app
        # launch looks like, and what an anchored match requires.
        for app in (self.installed, self.newapp):
            # A **symlink** to /bin/sleep, not a copy: macOS SIGKILLs a copied
            # platform binary on exec (verified: "Killed: 9"), so a copy would
            # make every launch look like a crash. Through the symlink the
            # process's argv[0] is still <APP>/Contents/MacOS/ClaudePet — which
            # is what a real launch looks like to a process match.
            os.symlink("/bin/sleep", app / "Contents" / "MacOS" / "ClaudePet")

    @staticmethod
    def _clear(path):
        """make_update_app installs a real `python`; replace it in place."""
        if path.exists() or path.is_symlink():
            path.unlink()
        return path

    def with_bundled_python(self, app):
        helper = self._clear(Path(app) / "Contents" / "MacOS" / "python")
        os.symlink(sys.executable, helper)

    def with_instrumented_python(self, app):
        """A working `python` that records every invocation.

        The exchange runs **at** the swap. Production tries the old installed
        app's helper first, then the validated staged bundle's helper. There is
        no forward two-step move fallback: if neither helper can perform the
        exchange, the transaction must fail before APP changes. Recording the
        invocation proves a successful fixture reached the atomic primitive.

        **The wrapper is a compiled Mach-O, not a shell script.** Two separate
        reasons, and either alone is enough:

        * A `#!/bin/sh` wrapper deadlocks. `/bin/sh` still has the script file
          open when the exchange swaps the containing directory out from under
          it, and the helper never returns — measured, the whole updater hangs.
        * Production's helper is py2app's real Mach-O `python`, and the
          preflight is about to require that. A script helper would let a
          fixture pass where the shipped code would refuse.

        It is symlinked in from outside the bundle, so the swap moves the link
        rather than the image. The log destination travels in the environment
        (`CLAUDEPET_TEST_EXCHANGE_LOG`, set by `script_env`) rather than being
        compiled in, so one binary serves every test.
        """
        helper = self._clear(Path(app) / "Contents" / "MacOS" / "python")
        os.symlink(instrumented_python_binary(self), helper)
        return helper

    def exchange_invocations(self):
        if not self.exchange_log.exists():
            return []
        return [ln for ln in self.exchange_log.read_text().splitlines() if ln]

    def assert_atomic_branch_ran(self):
        calls = self.exchange_invocations()
        self.assertTrue(
            calls,
            "the atomic exchange never ran — the old app's bundled "
            "interpreter was never invoked")

    def with_broken_bundled_python(self, app):
        """A helper that is present, is a real Mach-O, and fails every call.

        `/usr/bin/false` rather than a `#!/bin/sh\\nexit 1` script, for the
        same two reasons as the instrumented wrapper above: a script helper
        can wedge the exchange, and it is a shape production is about to
        refuse outright — a fixture that only fails because it is a script
        would stop testing "the new bundle's interpreter is broken".
        """
        helper = self._clear(Path(app) / "Contents" / "MacOS" / "python")
        os.symlink(BROKEN_PYTHON, helper)

    def find_line(self, command, needle, what):
        """Locate a step by substring, or skip **loudly**.

        Fault injection has to attach to a real step. If the step a test
        injects into no longer exists, the loss path it covers is gone too —
        that is a skip with an explanation, never a silent pass.
        """
        for line in command.split("\n"):
            if needle in line:
                return line
        _skip_loudly(self, f"no step matching {needle!r} in the replacement "
                           f"script, so {what} cannot be injected; the path "
                           "this test covers may no longer exist")

    def build_command(self, launcher, sabotage=None, trailing=None,
                      after=None, break_step=None, newapp=None, workdir=None):
        command = script_for(self.installed, newapp or self.newapp,
                             workdir or self.workdir)
        command = command.replace("sleep 1.5", ":")
        replacement = launcher if sabotage is None else f"{launcher}\n{sabotage}"
        command = replace_launch_points(command, replacement)
        if after is not None:
            needle, extra = after
            line = self.find_line(command, needle, "the follow-up step")
            command = command.replace(line, f"{line}\n{extra}", 1)
        if break_step is not None:
            line = self.find_line(command, break_step, "the failure")
            command = command.replace(line, "false", 1)
        return f"{command}\n{trailing}" if trailing else command

    def script_env(self, **extra):
        """The module's redirections, plus where the helper should log.

        `$HOME` matters here specifically: the script's `cleanup()` appends
        its retained-backup notice to `"$HOME/claudepet_debug.log"`, and this
        is what keeps that append inside the fixture.
        """
        return super().script_env(
            CLAUDEPET_TEST_EXCHANGE_LOG=str(self.exchange_log), **extra)

    def run_script(self, launcher, sabotage=None, trailing=None, after=None,
                   break_step=None):
        return subprocess.run(
            ["/bin/sh", "-c",
             self.build_command(launcher, sabotage, trailing, after,
                                break_step)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=self.script_env(), timeout=120, check=False)

    def start_script(self, launcher, sabotage=None, trailing=None):
        proc = subprocess.Popen(
            ["/bin/sh", "-c", self.build_command(launcher, sabotage, trailing)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=self.script_env())
        self.addCleanup(proc.poll)
        return proc

    def old_app_is_recoverable(self):
        """The contract, stated without reference to any mechanism.

        The old app must be findable somewhere a person or a recovery step
        would look: back at the install path, or retained under a named
        leftover beside it. Written this way it stays valid whether recovery
        restores by exchange, by move, or by leaving the copy in place.
        """
        if (self.installed / "old-marker").is_file():
            return "restored to the install path"
        for leftover in sorted(Path(self.td).glob(".claudepet-*")):
            if (leftover / "old-marker").is_file():
                return f"retained at {leftover.name}"
        return None

    def assert_old_app_not_destroyed(self):
        nested = list(Path(self.installed).glob(".claudepet-*"))
        self.assertEqual(nested, [],
                         "a leftover was moved *inside* the installed app; "
                         "nothing looks for it there")
        where = self.old_app_is_recoverable()
        self.assertIsNotNone(
            where,
            "the only copy of the old app is gone: neither at the install "
            "path nor retained beside it")

    # The two patterns under test. Only the caret separates them.
    def unanchored(self):
        return f"{self.installed}/Contents/MacOS/"

    def anchored(self):
        return f"^{self.installed}/Contents/MacOS/"

    @staticmethod
    def pgrep(pattern):
        return subprocess.run(["/usr/bin/pgrep", "-f", pattern],
                              capture_output=True, text=True).stdout.split()

    def wait_for_pgrep(self, pattern, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            hits = self.pgrep(pattern)
            if hits:
                return hits
            time.sleep(0.1)
        return []

    def start_decoy(self):
        """A process that *mentions* the app path without being the app.

        `sh -c "<one simple command>"` is not a decoy: the shell execs the
        command and the path leaves argv entirely (verified — the process shows
        up as bare `sleep`, invisible to any `-f` match). Two commands keep the
        shell alive with its full `-c` string in argv, which is what makes the
        anchored/unanchored distinction observable at all.
        """
        proc = subprocess.Popen(
            ["/bin/sh", "-c",
             f"sleep 60; true # {self.installed}/Contents/MacOS/ClaudePet"],
            env=self.script_env())

        def stop():
            proc.kill()
            proc.wait(timeout=10)

        self.addCleanup(stop)
        return proc

    LAUNCH_OK = '"$APP/Contents/MacOS/ClaudePet" 45 &'
    # Must outlive the first 0.5s ack poll and die inside the 3s settle. At
    # 0.3s it dies before the first poll, so the test exercises "never
    # appeared" and never reaches the settle branch its name claims.
    LAUNCH_DIES = '"$APP/Contents/MacOS/ClaudePet" 1.2 &'
    LAUNCH_NONE = ':'

    def backups_in(self, parent):
        return sorted(p for p in Path(parent).glob(".claudepet-old-*"))

    def test_a_launch_that_is_never_acknowledged_rolls_back(self):
        """`open` exiting 0 is a dispatch, not a health signal."""
        self.with_bundled_python(self.newapp)
        self.run_script(self.LAUNCH_NONE)
        self.assertTrue((self.installed / "old-marker").is_file(),
                        "the old app was discarded although nothing came up")
        self.assertFalse((self.installed / "new-marker").exists())
        self.assertFalse(self.workdir.exists())

    def test_a_process_that_dies_during_the_settle_delay_rolls_back(self):
        """A bundle that starts and immediately crashes is not a live app."""
        self.with_bundled_python(self.newapp)
        self.run_script(self.LAUNCH_DIES)
        self.assertTrue((self.installed / "old-marker").is_file(),
                        "a process that exited straight away counted as a "
                        "successful launch")
        self.assertFalse((self.installed / "new-marker").exists())

    # A previous test here asserted that a script cannot see its own shell in a
    # `pgrep -f` match. It was removed rather than repaired: one of its
    # assertions compared `str(probe.args)` — an argv *list* — against a
    # collection of pid strings, which can never be equal and therefore could
    # never fail, and another pinned an exact match count that any unrelated
    # process on the machine would flip. It is not evidence that the ack is
    # safe and was never cited as such. The two properties that matter —
    # anchoring, and the pre-`open` pid snapshot — are covered behaviourally
    # below, and each is mutation-checked against the rule it names.

    def test_an_unrelated_process_mentioning_the_path_is_not_an_acknowledgement(self):
        """The anchor test: a third-party process mentioning the path.

        Started **by the script, at the launch point**, so the pre-`open` pid
        snapshot does not already exclude it. An earlier version started the
        decoy beforehand and passed against an unanchored mutant — the
        snapshot was doing the work and the anchor was untested. In this form
        it is discriminating: remove the `^` from the script's pattern and
        this goes red.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)

        self.run_script('/bin/sh -c "sleep 45; true # '
                        '$APP/Contents/MacOS/ClaudePet" &')

        self.assert_decoy_distinguishes_the_patterns(self.unanchored())
        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "a process that merely mentions the app path counted as the app "
            "having started")
        self.assertFalse((self.installed / "new-marker").exists())

    def start_stale_app_process(self):
        """The user's already-running copy, started before the update.

        Its command line genuinely *begins* with the app executable path, so
        the anchor does not exclude it. Only a snapshot taken before `open`
        can, which is the point: after the exchange the path is unchanged, so
        the old process satisfies the match in exactly the situation the ack
        exists to detect.
        """
        exe = self.installed / "Contents" / "MacOS" / "ClaudePet"
        proc = subprocess.Popen([str(exe), "90"], env=self.script_env())

        def stop():
            proc.kill()
            proc.wait(timeout=10)

        self.addCleanup(stop)
        self.assertIn(str(proc.pid), self.wait_for_pgrep(self.anchored()),
                      "fixture is inert: the stale process is not visible to "
                      "the anchored match, so nothing here could false-ack")
        return proc

    def start_stale_python_process(self):
        """The same, on the *fallback* pattern: python running claude_pet.py.

        The fallback match is a separate branch. A decoy aimed at the
        `Contents/MacOS/` pattern never reaches it, so it is tested on its own.
        """
        script = self.installed / "Contents" / "Resources" / "claude_pet.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("import time\ntime.sleep(90)\n")
        proc = subprocess.Popen([sys.executable, str(script)],
                                env=self.script_env())

        def stop():
            proc.kill()
            proc.wait(timeout=10)

        self.addCleanup(stop)
        self.assertTrue(
            self.wait_for_pgrep(f"{script}"),
            "fixture is inert: the stale python process is not visible")
        return proc

    def test_a_process_running_before_the_update_never_acknowledges_it(self):
        """The false ACK that matters in practice.

        The exchange swaps in place, so the install path is unchanged and the
        user's already-running app keeps matching. Only a pre-`open` pid
        snapshot distinguishes it from something this update started.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        self.start_stale_app_process()

        self.run_script(self.LAUNCH_NONE)

        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "a process that predates the update acknowledged it: nothing was "
            "launched, yet the new bundle was kept")
        self.assertFalse((self.installed / "new-marker").exists())

    def test_a_launch_visible_only_to_the_fallback_pattern_is_acknowledged(self):
        """The fallback branch must actually be reachable.

        A bundle started as `python …/Contents/Resources/claude_pet.py` puts no
        process under the `Contents/MacOS/` pattern, so only the fallback match
        can see it. If that branch never runs, this update is rolled back
        despite having launched perfectly.

        This is the positive control for the two fallback tests either side of
        it: a branch that never executes cannot false-ack either, so those
        would pass without it while verifying nothing.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        script = self.newapp / "Contents" / "Resources" / "claude_pet.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("import time\ntime.sleep(45)\n")

        self.run_script('"$APP/Contents/MacOS/python" '
                        '"$APP/Contents/Resources/claude_pet.py" &')

        self.assertTrue(
            (self.installed / "new-marker").is_file(),
            "a bundle that launched as a python process was rolled back: the "
            "fallback match never acknowledged it")

    def test_a_python_process_running_before_the_update_never_acknowledges_it(self):
        """Same contract on the fallback pattern, which is a separate branch.

        The positive control above proves this pattern is reachable. Both pgrep
        arms are fail-soft (`|| true`), so when the MacOS pattern has no match
        the Resources/claude_pet.py arm still executes. Removing the BEFORE
        snapshot therefore makes this stale pid keep the new bundle, while the
        correct script rolls it back.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        self.start_stale_python_process()

        self.run_script(self.LAUNCH_NONE)

        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "a pre-existing python process matching the fallback pattern "
            "acknowledged an update that launched nothing")
        self.assertFalse((self.installed / "new-marker").exists())

    def assert_decoy_distinguishes_the_patterns(self, loose):
        """The decoy must be visible loosely and invisible when anchored.

        Checked after the run, while it is still alive — a decoy started by
        the script cannot be inspected before it exists.
        """
        self.assertTrue(self.pgrep(loose),
                        "fixture is inert: the decoy was not running, or is "
                        "not visible to a loose match")
        self.assertEqual(self.pgrep(f"^{loose}"), [],
                         "fixture is inert: an anchored match already sees "
                         "the decoy, so it is not a decoy")

    def test_an_unrelated_process_mentioning_the_resources_path_is_not_an_ack(self):
        """The fallback pattern must not match loosely either.

        The decoy is started **by the script, at the launch point**, so it is
        new relative to the pre-`open` snapshot. That is what makes this test
        about the anchor: a decoy started earlier is excluded by the snapshot
        no matter how loose the pattern is, and the test then passes without
        the anchor doing anything — measured, not assumed.

        Both pgrep arms carry `|| true`, so a miss in the first arm cannot
        abort the second under `set -e`. Removing the second pattern's anchor
        makes this newly-created decoy acknowledge the update; keeping the
        anchor makes the script roll back.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        resources = f"{self.installed}/Contents/Resources/claude_pet.py"

        self.run_script(f'/bin/sh -c "sleep 45; true # {resources}" &')

        self.assert_decoy_distinguishes_the_patterns(resources)
        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "a process merely mentioning the claude_pet.py path counted as "
            "the app having started")
        self.assertFalse((self.installed / "new-marker").exists())

    def test_a_stale_process_cannot_cover_for_one_that_died_during_settle(self):
        """The settle check must confirm *that* pid, not re-scan for any match.

        A launched process that dies inside the settle window, with the user's
        old process still running, is the case a re-scan gets wrong: it finds
        the stale match and calls the update healthy. Confirming the same pid
        is what separates the two.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        self.start_stale_app_process()

        self.run_script(self.LAUNCH_DIES)

        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "the launched process died during the settle delay and a stale "
            "process was accepted in its place")
        self.assertFalse((self.installed / "new-marker").exists())

    # A shell-level interleaving test lived here. It was correct when the
    # replacement script took the update lock itself, and it caught a mutant
    # with that lock removed. The lock has since moved to the point where the
    # helper is *spawned*, and is handed to the helper so it outlives the app
    # that quits right after — so the script no longer takes a lock, and no
    # test driving the script directly can observe serialization. The property
    # is covered at the layer that owns it, in ConcurrentInstallTests. Do not
    # reinstate this here without first checking which layer holds the lock.

    def test_rollback_survives_a_new_bundle_with_a_broken_interpreter(self):
        """The only time rollback runs is when the new bundle is bad.

        Here the new bundle's `python` exists and fails on every invocation.
        Recovery must still put the old app back — it has a known-good
        interpreter of its own in the backup.
        """
        old_id = claude_pet._path_ident_str(str(self.installed))
        self.with_bundled_python(self.installed)
        self.with_broken_bundled_python(self.newapp)
        self.run_script(self.LAUNCH_NONE)
        self.assertEqual(
            claude_pet._path_ident_str(str(self.installed)), old_id,
            "rollback restored the old marker under a different APP object")
        self.assertTrue(
            (self.installed / "old-marker").is_file(),
            "rollback failed when the new bundle was broken — the one "
            "circumstance it exists for")
        self.assertFalse((self.installed / "new-marker").exists())
        # Cleanup deliberately uses the validated NEW python and retains owned
        # objects if that helper cannot run. A retained WORK is acceptable; an
        # old-app copy inside it would mean rollback lost provenance.
        self.assertFalse(
            (self.newapp / "old-marker").exists(),
            "retained WORK contains the old app's only recoverable copy")

    def test_an_acknowledged_launch_completes_the_swap_atomically(self):
        """The atomic path specifically — the branch every real machine takes."""
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        result = self.run_script(self.LAUNCH_OK)
        self.assertEqual(result.returncode, 0)
        self.assert_atomic_branch_ran()
        self.assertTrue((self.installed / "new-marker").is_file(),
                        "the acknowledged update did not take effect")
        self.assertFalse((self.installed / "old-marker").exists())
        self.assertEqual(self.backups_in(self.td), [],
                         "a completed update left its backup behind")
        self.assertFalse(self.workdir.exists())

    def test_the_swap_fails_closed_without_any_bundled_interpreter(self):
        """No atomic helper means no update; APP stays the exact old object."""
        old_id = claude_pet._path_ident_str(str(self.installed))
        result = self.run_script(self.LAUNCH_OK)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.exchange_invocations(), [],
                         "fixture error: something invoked a helper that was "
                         "never installed")
        self.assertEqual(claude_pet._path_ident_str(str(self.installed)), old_id)
        self.assertTrue((self.installed / "old-marker").is_file())
        self.assertFalse((self.installed / "new-marker").exists())
        for backup in self.backups_in(self.td):
            self.assertFalse(
                (backup / "old-marker").exists(),
                "fail-closed exchange moved the old app into a backup")

    def test_a_rollback_that_cannot_move_the_new_app_aside_keeps_the_old_one(self):
        """The nesting hole, made deterministic.

        `mv "$APP" "$STAGE"` fails when STAGE exists and is non-empty. The old
        code then ran `mv "$BACKUP" "$APP"`, which *succeeds by nesting* the
        backup inside the still-present APP: rollback reports success, the
        KEEP_BACKUP flag is never set, and the old app is no longer at any path
        anyone looks for.
        """
        self.with_bundled_python(self.newapp)
        self.run_script(self.LAUNCH_NONE,
                        sabotage='mkdir -p "$STAGE/occupied"')

        nested = list(Path(self.installed).glob(".claudepet-old-*"))
        self.assertEqual(nested, [],
                         "the backup was moved *inside* the installed app; "
                         "nothing looks for it there")

        restored = (self.installed / "old-marker").is_file()
        retained = [b for b in self.backups_in(self.td)
                    if (b / "old-marker").is_file()]
        self.assertTrue(
            restored or retained,
            "the only copy of the old app is gone: it was neither restored to "
            "the install path nor retained as a named backup")

    def test_the_old_app_survives_a_rollback_on_the_atomic_path(self):
        """Old-copy preservation on the exchange path specifically.

        Atomic exchange leaves the old app wherever the exchange put it.
        Instrumented so the branch is *known* to have run rather than inferred
        from the final marker.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        self.run_script(self.LAUNCH_NONE)
        self.assert_atomic_branch_ran()
        self.assert_old_app_not_destroyed()
        self.assertFalse((self.installed / "new-marker").exists(),
                         "the update stayed in place although nothing launched")

    def test_atomic_exchange_failure_never_starts_a_move_fallback(self):
        """Both exchange helpers fail; exact old APP remains and no backup moves."""
        self.with_broken_bundled_python(self.installed)
        self.with_broken_bundled_python(self.newapp)
        old_id = claude_pet._path_ident_str(str(self.installed))
        result = self.run_script(self.LAUNCH_OK)
        self.assertNotEqual(
            result.returncode, 0,
            "two failing exchange helpers were treated as a successful swap")
        self.assertEqual(claude_pet._path_ident_str(str(self.installed)), old_id,
                         "exchange failure replaced the installed APP object")
        self.assertTrue((self.installed / "old-marker").is_file())
        self.assertFalse((self.installed / "new-marker").exists(),
                         "the update took effect although the swap failed")
        for backup in self.backups_in(self.td):
            self.assertFalse(
                (backup / "old-marker").exists(),
                "exchange failure moved the old app into a backup")

    def test_a_stage_tampered_with_after_ditto_is_never_installed(self):
        """The installer's second validation rejects the exact staged copy.

        Production always hands the helper a Python-created `staged=` tree; it
        never uses the helper's test-only unstaged ditto arm. This fixture puts
        the symlink into the second ditto destination and lets the real
        `validate_update_app` reject it before Popen. The original APP identity
        therefore cannot change.
        """
        pet = "Contents/Resources/.claude_pet/pets/dog/preview.png"
        old_id = claude_pet._path_ident_str(str(self.installed))
        validations = []
        ditto_calls = []
        real_validate = claude_pet.validate_update_app

        def signing(argv):
            joined = " ".join(str(a) for a in argv)
            if "/usr/bin/lipo" in joined:
                return (0, "arm64 x86_64")
            if "/usr/sbin/spctl" in joined:
                return (0, "origin=Developer ID Application: fixture "
                           f"({claude_pet.TEAM_ID})")
            if "stapler" in joined:
                return (0, "The validate action worked!")
            return (0, "")

        def fetch(_url, path):
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("ClaudePet.app/Contents/Info.plist", "placeholder")

        def ditto(argv, *args, **kwargs):
            argv = [str(a) for a in argv]
            ditto_calls.append(tuple(argv))
            dst = Path(argv[-1])
            if "-x" in argv and "-k" in argv:
                app = make_update_app(dst, version="99.0")
                (app / "new-marker").write_text("replacement")
            else:
                fake_ditto(argv, *args, **kwargs)
                victim = dst / pet
                victim.unlink()
                os.symlink("spritesheet.webp", victim)
            return mock.Mock(returncode=0, stdout="", stderr="")

        def validate(path, version, expect_arches=None):
            path = Path(path)
            tampered = (path / pet).is_symlink()
            result = real_validate(
                path, version, run=signing, expect_arches=expect_arches)
            validations.append((str(path), tampered, result))
            return result

        with patch_download(fetch), \
             mock.patch.object(claude_pet.subprocess, "run", side_effect=ditto), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            ok = claude_pet.install_github_update(
                "https://example.test/a.zip", app_path=str(self.installed),
                expect_version="99.0")

        self.assertFalse(ok, "a tampered staged copy was accepted")
        self.assertEqual(len(ditto_calls), 2,
                         "fixture did not reach the stage-copy ditto")
        self.assertEqual([v[1:] for v in validations],
                         [(False, True), (True, False)],
                         "the real validator did not distinguish extracted and "
                         "symlink-tampered staged trees")
        self.assertEqual(popen.call_count, 0,
                         "replacement helper started after stage rejection")
        self.assertEqual(
            claude_pet._path_ident_str(str(self.installed)), old_id,
            "stage rejection replaced the original APP object")
        self.assertTrue((self.installed / "old-marker").is_file())
        self.assertFalse(
            (self.installed / "new-marker").is_file(),
            "a rejected staged bundle was installed")

    def setUp_full_bundle(self):
        """Re-make both bundles as complete, validatable apps."""
        shutil.rmtree(self.installed, ignore_errors=True)
        shutil.rmtree(self.workdir, ignore_errors=True)
        self.exchange_log.unlink(missing_ok=True)
        for app, marker in ((self.installed, "old-marker"),
                            (self.newapp, "new-marker")):
            app.parent.mkdir(parents=True, exist_ok=True)
            make_update_app(app.parent, version="99.0")
            (app / marker).write_text(marker)
            exe = app / "Contents" / "MacOS" / "ClaudePet"
            exe.unlink()
            os.symlink("/bin/sleep", exe)
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)

    def test_a_completed_update_never_leaves_the_install_path_empty(self):
        """There is no instant at which the app is absent from its own path.

        Instrumented on the old bundle so this measures the atomic exchange.
        A fixture without either helper must fail closed and cannot satisfy the
        completed-update control.
        """
        self.with_instrumented_python(self.installed)
        self.with_bundled_python(self.newapp)
        watcher = f"""
import os, sys, time
missing = 0
deadline = time.time() + 60
while time.time() < deadline:
    if not os.path.lexists({str(self.installed)!r}):
        missing += 1
    if os.path.isfile({str(self.installed / 'new-marker')!r}):
        break
    time.sleep(0.001)
sys.stdout.write(str(missing))
"""
        proc = subprocess.Popen([sys.executable, "-c", watcher],
                                stdout=subprocess.PIPE, text=True,
                                env=self.script_env())
        try:
            self.run_script(self.LAUNCH_OK)
        finally:
            out, _ = proc.communicate(timeout=90)
        self.assertTrue((self.installed / "new-marker").is_file(),
                        "the update did not complete; the window check is moot")
        self.assert_atomic_branch_ran()
        self.assertEqual(out.strip(), "0",
                         "the install path was empty during the swap — a "
                         "launch or a Finder look in that window sees no app")


def exchange_helper_source():
    """The Python source the script hands to the bundled interpreter.

    The brief fixes the shell side (`"$APP/Contents/MacOS/python" -c
    "$EXCHANGE_PY" "$STAGE" "$APP"`) but not the Python-side symbol name, so
    both the public and private spellings are accepted. Returns None when no
    such constant exists — an absent seam, which the tests report as a failure
    rather than a skip.
    """
    for name in ("EXCHANGE_PY", "_EXCHANGE_PY"):
        source = getattr(claude_pet, name, None)
        if isinstance(source, str) and source.strip():
            return source
    return None


class ExchangeHelperTests(IsolatedTest):
    """renamex_np(RENAME_SWAP) via ctypes, run by the bundled interpreter
    because `launcher.c` forwards no argv to the app itself."""

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.source = exchange_helper_source()
        if self.source is None:
            self.fail("no module-level exchange helper source (EXCHANGE_PY / "
                      "_EXCHANGE_PY); the script has nothing to hand the "
                      "bundled interpreter")

    def run_helper(self, *paths):
        return subprocess.run([sys.executable, "-c", self.source,
                               *[str(p) for p in paths]],
                              capture_output=True, text=True,
                              env=self.script_env(), timeout=30)

    def test_two_directories_are_exchanged_in_place(self):
        a, b = Path(self.td) / "a", Path(self.td) / "b"
        a.mkdir(), b.mkdir()
        (a / "which").write_text("a")
        (b / "which").write_text("b")
        result = self.run_helper(a, b)
        self.assertEqual(result.returncode, 0,
                         f"exchange failed: {result.stderr.strip()!r}")
        self.assertEqual((a / "which").read_text(), "b")
        self.assertEqual((b / "which").read_text(), "a")

    def test_a_missing_operand_fails_loudly_rather_than_creating_anything(self):
        a = Path(self.td) / "a"
        a.mkdir()
        (a / "which").write_text("a")
        missing = Path(self.td) / "gone"
        result = self.run_helper(a, missing)
        self.assertNotEqual(result.returncode, 0,
                            "exchanging with a nonexistent path reported "
                            "success")
        self.assertEqual((a / "which").read_text(), "a")
        self.assertFalse(missing.exists())

    def test_wrong_argument_count_is_an_error(self):
        self.assertNotEqual(self.run_helper(Path(self.td)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
