"""Gates for the minimum-macOS (minos) check on release artifacts.

The defect: every arm64 artifact since v0.24 was built with a pyenv Python compiled on
the build Mac, whose ``MACOSX_DEPLOYMENT_TARGET`` was 26.3. py2app ships that
interpreter's ``Python.framework`` and ``MacOS/python`` as-is, so the bundle refused to
launch below macOS 26.3 while the site promises 12.0. Signature, notarization,
architecture and payload checks all passed — none of them looks at a load command.

Two gates are pinned here:

* ``verify_release_artifact.check_minos`` (and its call from ``check_app``, and the
  ``minos`` CLI subcommand): every Mach-O slice in the bundle must carry a minimum
  macOS <= 12.0, read from ``LC_BUILD_VERSION`` *or* ``LC_VERSION_MIN_MACOSX``; an
  unreadable Mach-O, one with no min-OS load command, and a bundle with no Mach-O at
  all are refused rather than passed.
* ``release.sh``'s ``check_build_python`` and its ``PY`` default: the arm64 build
  interpreter is refused *before* py2app runs when its deployment target is > 12.0.

Every Mach-O below is compiled fresh with ``clang -mmacosx-version-min=...`` (and
rewritten with ``vtool`` / combined with ``lipo`` where a shape needs it) into a
temporary directory. Nothing is read from an installed app or a build directory.
``release.sh`` is never sourced or dispatched: the one function is brace-matched out of
its text and run under ``zsh -f`` with an allow-listed environment and a shim
interpreter.

Plausible wrong implementations, and the fixture that separates each from the correct
gate (every rival below returns a verdict different from the expected one on at least
one fixture):

====================================================  =============================
rival                                                 fixture that catches it
====================================================  =============================
no minos check (the pre-change gate)                  ``arm64-26.3`` bundle
checks only ``Contents/MacOS/<exe>``                  good exe + 26.3 nested dylib
checks only the first slice of a fat file             fat (x86_64 26.3, arm64 11.0)
checks only the host (arm64) slice                    fat (x86_64 26.3, arm64 11.0)
checks only the last slice                            fat (x86_64 11.0, arm64 26.3)
reads ``LC_BUILD_VERSION`` only                       ``LC_VERSION_MIN_MACOSX 13.0``
reads ``LC_VERSION_MIN_MACOSX`` only                  ``arm64-26.3`` (build version)
compares the major number only                        ``arm64-12.1``
strict ``<`` against the floor                        ``arm64-12.0`` must pass
missing load command counted as a pass                ``vtool -remove-build-version``
unparseable Mach-O skipped                            magic + garbage
unreadable file skipped                               mode 000 Mach-O
empty bundle passes vacuously                         bundle with text files only
refuses everything                                    ``arm64-11.0`` / fat 11.0 / 10.13
====================================================  =============================
"""

import atexit
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import verify_release_artifact

REPO = Path(__file__).resolve().parent.parent
RELEASE_SH = REPO / "release.sh"
CHECKOUT_SOURCE = Path(verify_release_artifact.__file__).resolve().with_name(
    "claude_pet.py")

C_SOURCE = "int main(void) { return 0; }\n"


def _skip_loudly(testcase_or_cls, reason):
    sys.stderr.write(f"\n[test_minos_gate] SKIPPED: {reason}\n")
    raise unittest.SkipTest(reason)


def _run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{argv[0]} failed: {proc.stderr.strip()[:400]}")


def _otool_minos(path):
    """What the fixture actually carries, read independently of the code under test."""
    out = subprocess.run(["/usr/bin/otool", "-arch", "all", "-l", str(path)],
                         capture_output=True, text=True).stdout
    found, cmd = [], None
    for line in out.splitlines():
        words = line.split()
        if words[:1] == ["cmd"]:
            cmd = words[1] if len(words) > 1 else None
        elif cmd == "LC_BUILD_VERSION" and words[:1] == ["minos"]:
            found.append(words[1])
        elif cmd == "LC_VERSION_MIN_MACOSX" and words[:1] == ["version"]:
            found.append(words[1])
    return found


class Binaries:
    """Compiled once per process; each attribute is a path to a real Mach-O."""

    _dir = None

    @classmethod
    def build(cls):
        if cls._dir is not None:
            return cls
        for tool in ("/usr/bin/clang", "/usr/bin/lipo", "/usr/bin/vtool",
                     "/usr/bin/otool"):
            if not os.access(tool, os.X_OK):
                raise unittest.SkipTest(f"{tool} not available")
        d = Path(os.path.realpath(tempfile.mkdtemp(prefix="minos-bin-")))
        atexit.register(shutil.rmtree, d, True)
        src = d / "m.c"
        src.write_text(C_SOURCE)

        def cc(name, arch, minos):
            out = d / name
            _run(["/usr/bin/clang", "-arch", arch, f"-mmacosx-version-min={minos}",
                  "-o", str(out), str(src)])
            return out

        cls.arm64_11 = cc("arm64-11.0", "arm64", "11.0")
        cls.arm64_12 = cc("arm64-12.0", "arm64", "12.0")
        cls.arm64_121 = cc("arm64-12.1", "arm64", "12.1")
        cls.arm64_263 = cc("arm64-26.3", "arm64", "26.3")
        cls.x86_11 = cc("x86_64-11.0", "x86_64", "11.0")
        cls.x86_263 = cc("x86_64-26.3", "x86_64", "26.3")
        cls.x86_1013 = cc("x86_64-10.13", "x86_64", "10.13")  # LC_VERSION_MIN_MACOSX

        cls.fat_x86new = d / "fat-x86_64-26.3-arm64-11.0"
        _run(["/usr/bin/lipo", "-create", str(cls.x86_263), str(cls.arm64_11),
              "-output", str(cls.fat_x86new)])
        cls.fat_armnew = d / "fat-x86_64-11.0-arm64-26.3"
        _run(["/usr/bin/lipo", "-create", str(cls.x86_11), str(cls.arm64_263),
              "-output", str(cls.fat_armnew)])
        cls.fat_ok = d / "fat-11.0"
        _run(["/usr/bin/lipo", "-create", str(cls.x86_11), str(cls.arm64_11),
              "-output", str(cls.fat_ok)])

        cls.vmin_13 = d / "x86_64-versionmin-13.0"
        _run(["/usr/bin/vtool", "-set-version-min", "macos", "13.0", "13.0",
              "-replace", "-output", str(cls.vmin_13), str(cls.x86_1013)])
        cls.vmin_11 = d / "x86_64-versionmin-11.0"
        _run(["/usr/bin/vtool", "-set-version-min", "macos", "11.0", "11.0",
              "-replace", "-output", str(cls.vmin_11), str(cls.x86_1013)])

        cls.no_min = d / "arm64-no-min-command"
        _run(["/usr/bin/vtool", "-remove-build-version", "macos",
              "-output", str(cls.no_min), str(cls.arm64_11)])

        cls.garbage = d / "garbage-macho"
        cls.garbage.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x07\x00\x00\x01" + b"\xff" * 40)
        cls._dir = d
        return cls


class MinosFixtureSelfCheck(unittest.TestCase):
    """The fixtures are what their names say, read by otool rather than trusted."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.b = Binaries.build()
        except unittest.SkipTest as exc:
            _skip_loudly(cls, str(exc))

    def test_fixture_minos_values(self):
        b = self.b
        self.assertEqual(_otool_minos(b.arm64_11), ["11.0"])
        self.assertEqual(_otool_minos(b.arm64_12), ["12.0"])
        self.assertEqual(_otool_minos(b.arm64_121), ["12.1"])
        self.assertEqual(_otool_minos(b.arm64_263), ["26.3"])
        self.assertEqual(sorted(_otool_minos(b.fat_x86new)), ["11.0", "26.3"])
        self.assertEqual(sorted(_otool_minos(b.fat_armnew)), ["11.0", "26.3"])
        out = subprocess.run(["/usr/bin/otool", "-l", str(b.vmin_13)],
                             capture_output=True, text=True).stdout
        self.assertIn("LC_VERSION_MIN_MACOSX", out)
        self.assertNotIn("LC_BUILD_VERSION", out)
        self.assertRegex(out, r"version 13\.0")
        out = subprocess.run(["/usr/bin/otool", "-l", str(b.no_min)],
                             capture_output=True, text=True).stdout
        self.assertNotIn("LC_BUILD_VERSION", out)
        self.assertNotIn("LC_VERSION_MIN_MACOSX", out)
        lipo = subprocess.run(["/usr/bin/lipo", "-archs", str(b.fat_x86new)],
                              capture_output=True, text=True).stdout.split()
        self.assertEqual(lipo[0], "x86_64", "the too-new slice must be the FIRST here")
        lipo = subprocess.run(["/usr/bin/lipo", "-archs", str(b.fat_armnew)],
                              capture_output=True, text=True).stdout.split()
        self.assertEqual(lipo[-1], "arm64", "the too-new slice must be the LAST here")


class CheckMinosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.b = Binaries.build()
        except unittest.SkipTest as exc:
            _skip_loudly(cls, str(exc))

    def setUp(self):
        self.td = Path(os.path.realpath(tempfile.mkdtemp(prefix="minos-app-")))
        self.addCleanup(shutil.rmtree, self.td, True)

    def bundle(self, name, exe=None, extra=()):
        """A bundle with text files, an optional main executable and extra Mach-Os.

        ``extra`` is ``(relative path, source binary)``; the layout mirrors where py2app
        puts the interpreter pieces, which is where the 26.3 slices actually were.
        """
        app = self.td / name
        (app / "Contents" / "Resources").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_text("<plist/>\n")
        (app / "Contents" / "Resources" / "claude_pet.py").write_text("# stub\n")
        if exe is not None:
            (app / "Contents" / "MacOS").mkdir()
            shutil.copyfile(exe, app / "Contents" / "MacOS" / "ClaudePet")
        for rel, src in extra:
            dst = app / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        return app

    def minos(self, app):
        buf = StringIO()
        with redirect_stdout(buf):
            ok = verify_release_artifact.check_minos(str(app))
        return ok, buf.getvalue()

    FRAMEWORK = "Contents/Frameworks/Python.framework/Versions/3.13/Python"

    # -- rejections ---------------------------------------------------------------

    def test_main_executable_built_for_26_3_is_rejected_and_named(self):
        app = self.bundle("new-ClaudePet.app", exe=self.b.arm64_263)
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn(os.path.join("Contents", "MacOS", "ClaudePet"), out,
                      "the rejection must name the offending file")
        self.assertIn("26.3", out)

    def test_nested_framework_built_for_26_3_is_rejected_when_the_exe_is_fine(self):
        """The real v0.24 shape: the launcher is fine, the shipped Python.framework is not."""
        app = self.bundle("nested-ClaudePet.app", exe=self.b.arm64_11,
                          extra=[(self.FRAMEWORK, self.b.arm64_263)])
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn(self.FRAMEWORK.replace("/", os.sep), out)
        self.assertNotIn(os.path.join("Contents", "MacOS", "ClaudePet") + " [", out,
                         "the good executable must not be reported as too new")

    def test_fat_binary_with_one_slice_too_new_is_rejected_whichever_slice_it_is(self):
        for label, fat in (("first slice (x86_64) too new", self.b.fat_x86new),
                           ("last slice (arm64) too new", self.b.fat_armnew)):
            with self.subTest(label):
                app = self.bundle(f"fat-{fat.name}.app", exe=fat)
                ok, out = self.minos(app)
                self.assertFalse(ok, out)
                self.assertIn("26.3", out)

    def test_lc_version_min_macosx_above_the_floor_is_rejected(self):
        app = self.bundle("vmin13-ClaudePet.app", exe=self.b.vmin_13)
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn("13.0", out)

    def test_minor_version_above_the_floor_is_rejected(self):
        app = self.bundle("m121-ClaudePet.app", exe=self.b.arm64_121)
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn("12.1", out)

    def test_macho_without_a_min_os_load_command_is_rejected(self):
        app = self.bundle("nomin-ClaudePet.app", exe=self.b.arm64_11,
                          extra=[("Contents/Resources/lib/nomin.so", self.b.no_min)])
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn("nomin.so", out)

    def test_unparseable_macho_is_rejected(self):
        app = self.bundle("garbage-ClaudePet.app", exe=self.b.arm64_11,
                          extra=[("Contents/Resources/lib/garbage.so", self.b.garbage)])
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn("garbage.so", out)

    def test_unreadable_file_is_rejected(self):
        if os.geteuid() == 0:
            _skip_loudly(self, "running as root: mode 000 does not make a file unreadable")
        app = self.bundle("unreadable-ClaudePet.app", exe=self.b.arm64_11,
                          extra=[("Contents/Resources/lib/locked.so", self.b.arm64_11)])
        locked = app / "Contents" / "Resources" / "lib" / "locked.so"
        os.chmod(locked, 0)
        self.addCleanup(os.chmod, locked, stat.S_IRUSR | stat.S_IWUSR)
        ok, out = self.minos(app)
        self.assertFalse(ok, out)
        self.assertIn("locked.so", out)

    def test_bundle_with_no_macho_is_rejected_not_passed_vacuously(self):
        app = self.bundle("empty-ClaudePet.app", exe=None)
        ok, out = self.minos(app)
        self.assertFalse(ok, out)

    def test_symlinked_or_missing_app_root_is_rejected(self):
        real = self.bundle("real-ClaudePet.app", exe=self.b.arm64_11)
        link = self.td / "link-ClaudePet.app"
        os.symlink(real, link)
        for app in (link, self.td / "missing-ClaudePet.app"):
            with self.subTest(app=app.name):
                self.assertFalse(self.minos(app)[0])

    # -- acceptances (positive controls: a gate that refuses everything fails these) --

    def test_bundle_built_for_11_0_passes(self):
        app = self.bundle("ok-ClaudePet.app", exe=self.b.arm64_11,
                          extra=[(self.FRAMEWORK, self.b.arm64_11),
                                 ("Contents/Resources/lib/ok.so", self.b.arm64_11)])
        ok, out = self.minos(app)
        self.assertTrue(ok, out)

    def test_exactly_the_floor_passes(self):
        app = self.bundle("m120-ClaudePet.app", exe=self.b.arm64_12)
        ok, out = self.minos(app)
        self.assertTrue(ok, out)

    def test_fat_binary_all_slices_old_enough_passes(self):
        app = self.bundle("fatok-ClaudePet.app", exe=self.b.fat_ok)
        ok, out = self.minos(app)
        self.assertTrue(ok, out)

    def test_lc_version_min_macosx_below_the_floor_passes(self):
        for src in (self.b.x86_1013, self.b.vmin_11):
            with self.subTest(src=src.name):
                app = self.bundle(f"vmin-{src.name}.app", exe=src)
                ok, out = self.minos(app)
                self.assertTrue(ok, out)

    def test_symlink_to_a_too_new_macho_outside_the_bundle_is_not_followed(self):
        """ditto preserves symlinks; Python.framework is full of them. A link is not a
        separate Mach-O, and following one out of the bundle would judge a file that is
        not shipped."""
        app = self.bundle("link-ok-ClaudePet.app", exe=self.b.arm64_11)
        os.symlink(self.b.arm64_263, app / "Contents" / "MacOS" / "outside")
        ok, out = self.minos(app)
        self.assertTrue(ok, out)

    # -- CLI -------------------------------------------------------------------------

    def test_minos_subcommand_exit_status(self):
        bad = self.bundle("cli-bad-ClaudePet.app", exe=self.b.arm64_263)
        good = self.bundle("cli-good-ClaudePet.app", exe=self.b.arm64_11)
        with redirect_stdout(StringIO()):
            self.assertEqual(verify_release_artifact.main(["minos", str(bad)]), 1)
            self.assertEqual(verify_release_artifact.main(["minos", str(good)]), 0)


class FakeClaudePet:
    SUMMARY_LOGO_DIR = "logos"
    SUMMARY_LOGO_FILES = {"claude": "claude.svg", "codex": "openai.svg"}

    def __init__(self):
        self.calls = []

    def validate_update_app(self, app_path, expect_version, **kwargs):
        self.calls.append((app_path, expect_version, kwargs))
        return True


class CheckAppInvokesMinosTests(unittest.TestCase):
    """``check_app`` — the gate ``release.sh publish`` runs on each uploaded artifact —
    must refuse a too-new bundle before delegating to the updater's validator.

    Every other local check is satisfied (checkout-identical code leaf, TrueType font,
    licence, both logos), so the Mach-O is the only thing that can refuse."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.b = Binaries.build()
        except unittest.SkipTest as exc:
            _skip_loudly(cls, str(exc))

    def setUp(self):
        self.td = Path(os.path.realpath(tempfile.mkdtemp(prefix="minos-chk-")))
        self.addCleanup(shutil.rmtree, self.td, True)

    def full_bundle(self, name, exe):
        app = self.td / name
        res = app / "Contents" / "Resources"
        (res / "fonts").mkdir(parents=True)
        (res / "logos").mkdir()
        shutil.copyfile(CHECKOUT_SOURCE, res / "claude_pet.py")
        (res / "fonts" / "Pretendard-SemiBold.ttf").write_bytes(
            b"\x00\x01\x00\x00" + b"\0" * 60)
        (res / "fonts" / "LICENSE-Pretendard.txt").write_text("stub\n")
        for fn in FakeClaudePet.SUMMARY_LOGO_FILES.values():
            (res / "logos" / fn).write_bytes(
                b'<svg xmlns="http://www.w3.org/2000/svg"></svg>\n')
        (app / "Contents" / "MacOS").mkdir()
        shutil.copyfile(exe, app / "Contents" / "MacOS" / "ClaudePet")
        return app

    def check(self, app):
        fake = FakeClaudePet()
        buf = StringIO()
        with mock.patch.object(verify_release_artifact, "_load_app", return_value=fake), \
                redirect_stdout(buf):
            ok = verify_release_artifact.check_app(str(app), "9.9", ["arm64"])
        return ok, fake.calls, buf.getvalue()

    def test_too_new_bundle_is_refused_before_the_validator(self):
        app = self.full_bundle("new-ClaudePet.app", self.b.arm64_263)
        ok, calls, out = self.check(app)
        self.assertEqual((ok, calls), (False, []),
                         "a bundle needing macOS 26.3 passed check_app:\n" + out)
        self.assertIn(os.path.join("Contents", "MacOS", "ClaudePet"), out)

    def test_old_enough_bundle_reaches_the_validator(self):
        app = self.full_bundle("ok-ClaudePet.app", self.b.arm64_11)
        ok, calls, out = self.check(app)
        self.assertTrue(ok, out)
        self.assertEqual(len(calls), 1)


# ---------------------------------------------------------------------------------
# release.sh: check_build_python and the PY default
# ---------------------------------------------------------------------------------

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


def assignment_line(text, var):
    m = re.search(rf'^{var}="[^\n]*$', text, re.M)
    if not m:
        raise AssertionError(f"no top-level {var}= line in release.sh")
    return m.group(0)


SHIM = """#!/bin/sh
# A build interpreter that reports FAKE_TARGET as its deployment target. The version
# comparison check_build_python delegates to "$py -c" runs on the real python3 so the
# shim does not decide the verdict itself; the py2app/objc/ServiceManagement import
# probe is answered "installed" so only the deployment target can refuse.
case "$2" in
  *sysconfig*) printf '%s\\n' "$FAKE_TARGET"; exit 0 ;;
  *py2app*) exit 0 ;;
esac
exec "$REAL_PY" "$@"
"""


class CheckBuildPythonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.access("/bin/zsh", os.X_OK):
            _skip_loudly(cls, "/bin/zsh not available")
        cls.text = RELEASE_SH.read_text()

    def setUp(self):
        self.td = Path(os.path.realpath(tempfile.mkdtemp(prefix="minos-sh-")))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.home = self.td / "home"
        self.home.mkdir()
        self.shim = self.td / "fakepy"
        self.shim.write_text(SHIM)
        self.shim.chmod(0o755)

    def env(self, **extra):
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(self.home),
               "TMPDIR": str(self.td), "ZDOTDIR": str(self.home), "LANG": "C.UTF-8",
               "REAL_PY": os.path.realpath(sys.executable)}
        env.update(extra)
        return env

    def run_fragment(self, body, **extra):
        return subprocess.run(["/bin/zsh", "-f", "-c", body], capture_output=True,
                              text=True, env=self.env(**extra), cwd=self.td, timeout=60)

    def check(self, target):
        fn = extract_function(self.text, "check_build_python")
        min_line = assignment_line(self.text, "MIN_MACOS")
        body = (f"{min_line}\nUPY=/nonexistent/upy\n{fn}\n"
                f'check_build_python "{self.shim}"\n')
        return self.run_fragment(body, FAKE_TARGET=target)

    def test_the_floor_constant_is_12_0(self):
        self.assertRegex(assignment_line(self.text, "MIN_MACOS"), r'^MIN_MACOS="12\.0"')
        self.assertEqual(verify_release_artifact.MIN_MACOS, (12, 0))

    def test_interpreter_targeting_26_3_is_refused(self):
        p = self.check("26.3")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("26.3", p.stdout)

    def test_too_new_or_unknown_targets_are_refused(self):
        for target in ("12.1", "13", "15.0", ""):
            with self.subTest(target=target):
                p = self.check(target)
                self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_old_enough_targets_are_accepted(self):
        """Positive control, and the python.org universal2 build's own value (11.0)."""
        for target in ("10.13", "11.0", "12", "12.0"):
            with self.subTest(target=target):
                p = self.check(target)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_missing_interpreter_is_refused(self):
        fn = extract_function(self.text, "check_build_python")
        body = (f"{assignment_line(self.text, 'MIN_MACOS')}\n{fn}\n"
                f'check_build_python "{self.td}/no-such-python"\n')
        p = self.run_fragment(body)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)

    def test_py_default_is_the_universal2_python_not_pyenv(self):
        """With neither PY nor UPY in the environment, the arm64 build interpreter
        resolves to the python.org framework path — never ``~/.pyenv``."""
        body = (f"{assignment_line(self.text, 'UPY')}\n"
                f"{assignment_line(self.text, 'PY')}\n"
                'print -r -- "$PY"\n')
        p = self.run_fragment(body)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = p.stdout.strip()
        self.assertNotIn(".pyenv", got)
        self.assertEqual(
            got, "/Library/Frameworks/Python.framework/Versions/Current/bin/python3")

    def test_build_checks_the_interpreter_before_running_py2app(self):
        build = extract_function(self.text, "build")
        check = build.find('check_build_python "$PY"')
        py2app = build.find("setup.py py2app")
        self.assertNotEqual(check, -1, "build() never calls check_build_python")
        self.assertNotEqual(py2app, -1)
        self.assertLess(check, py2app, "the interpreter must be checked before py2app")
        self.assertIn("verify_release_artifact.py minos", build,
                      "build() must run the minos gate on what it built")


if __name__ == "__main__":
    unittest.main()
