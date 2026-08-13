"""Independent adversarial gates for the v0.20 updater transaction.

This module intentionally does not share fixtures with ``test_updater.py``.  The
fixtures model the safety properties from first principles and use only realpath
temporary directories.  No test reads or writes the installed app, the user's
HOME, or the real pet directory.

Plausible rivals ruled out by these fixtures:

* validate only the extracted app, then install a mutated post-ditto stage;
* accept any matching process, including one that existed before ``open``;
* accept a replacement PID after the PID originally acknowledged has died;
* let two helpers mutate one install path concurrently;
* trust an asset filename without checking the Mach-O architectures;
* follow a contained symlink for a security-critical bundle member; and
* exchange atomically, then lose the sole old copy in a second move.
"""

import os
import inspect
import plistlib
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

import claude_pet


REAL_MKDTEMP = tempfile.mkdtemp
REAL_POPEN = subprocess.Popen
REAL_OPEN = os.open
REAL_LSTAT = os.lstat
REAL_FSTAT = os.fstat
REAL_RMTREE = shutil.rmtree
REAL_EMPTY_DIR_AT = claude_pet._empty_dir_at
REAL_UPDATE_LOCK_DIR = claude_pet.UPDATE_LOCK_DIR


def install_python_macho(destination):
    """Install a real Mach-O Python without copying filesystem metadata.

    The updater executes this file for lock verification and atomic exchange;
    a shell-script stand-in can hang when its containing directory is swapped
    while ``/bin/sh`` is still reading it.  Prefer a hardlink to the resolved
    interpreter.  If the temp directory is on another volume, copy only bytes
    and then set executable mode -- deliberately not ``copy2``/``copystat``.
    """
    destination = Path(destination)
    source = Path(os.path.realpath(sys.executable))
    try:
        os.link(source, destination)
    except OSError:
        shutil.copyfile(source, destination)
        destination.chmod(0o755)


def make_app(path, marker, version="99.0", executable_kind="file"):
    """Create the smallest bundle needed by the updater safety checks."""
    app = Path(path)
    macos = app / "Contents" / "MacOS"
    resources = app / "Contents" / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    plist = {
        "CFBundleIdentifier": claude_pet.BUNDLE_ID,
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "CFBundleExecutable": "ClaudePet",
    }
    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump(plist, f)

    executable = macos / "ClaudePet"
    if executable_kind == "file":
        executable.write_text("#!/bin/sh\nexec /bin/sleep \"${1:-30}\"\n")
        executable.chmod(0o755)
    elif executable_kind == "directory":
        executable.mkdir()
    else:
        raise ValueError(executable_kind)

    # The exchange helper and architecture validator both need a regular,
    # executable path.  Individual process tests replace these with symlinks
    # where argv[0] must retain the bundle path.
    install_python_macho(macos / "python")
    (app / marker).write_text(marker)
    return app


def make_process_app(path, marker):
    """Bundle whose MacOS command is visible to anchored ``pgrep -f``."""
    app = make_app(path, marker)
    executable = app / "Contents" / "MacOS" / "ClaudePet"
    executable.unlink()
    os.symlink("/bin/sleep", executable)
    script = app / "Contents" / "Resources" / "claude_pet.py"
    script.write_text("import time\ntime.sleep(30)\n")
    return app


def inert_helper_launches(command):
    """Pin the helper launch grammar, then make both launch sites inert.

    These tests execute generated updater shell in temporary directories.  A
    production rename of the launch seam must fail closed here instead of
    silently falling through to LaunchServices.  There is exactly one command
    definition and exactly two consumers: initial launch and rollback
    relaunch.  Setting that one definition to ``:`` neutralizes both sites.
    """
    expected = {
        "LAUNCH=": 1,
        "LAUNCH=open": 1,
        "$LAUNCH ": 2,
        '$LAUNCH "$APP"': 1,
        '$LAUNCH "$RESTORED"': 1,
        'open "$APP"': 0,
        'open "$RESTORED"': 0,
    }
    actual = {needle: command.count(needle) for needle in expected}
    if actual != expected:
        raise AssertionError(
            "updater helper launch contract changed: %r != %r" %
            (actual, expected))
    command = command.replace("LAUNCH=open", "LAUNCH=:", 1)
    safe_expected = {
        "LAUNCH=": 1,
        "LAUNCH=:": 1,
        "$LAUNCH ": 2,
        '$LAUNCH "$APP"': 1,
        '$LAUNCH "$RESTORED"': 1,
    }
    safe_actual = {
        needle: command.count(needle) for needle in safe_expected}
    if safe_actual != safe_expected or "LAUNCH=open" in command:
        raise AssertionError("helper launch command was not made inert")
    return command


def discard_program_with_root_swap(target, displaced, sentinel, payload,
                                   inode_record):
    """Inject a pathname rival after _DISCARD_PY has verified its root fd."""
    source = claude_pet._DISCARD_PY
    needle = "\n".join((
        "            if ident(os.fstat(fd)) != want:",
        "                return 1",
        "            purge(fd)",
    ))
    if source.count(needle) != 1:
        raise AssertionError(
            "fd-bound directory discard identity seam changed")
    injected = "\n".join((
        "            if ident(os.fstat(fd)) != want:",
        "                return 1",
        "            if path == %r:" % str(target),
        "                os.rename(path, %r)" % str(displaced),
        "                os.mkdir(path, 0o700)",
        "                with open(%r, 'wb') as out:" % str(sentinel),
        "                    out.write(%r)" % bytes(payload),
        "                with open(%r, 'w') as out:" % str(inode_record),
        "                    out.write(str(os.lstat(%r).st_ino))" %
        str(sentinel),
        "            purge(fd)",
    ))
    return source.replace(needle, injected, 1)


def replace_helper_discard_program(command, source):
    """Pin and replace only the helper's standalone discard payload."""
    assignment = "DISCARD=" + shlex.quote(claude_pet._DISCARD_PY)
    if command.count(assignment) != 1:
        raise AssertionError("helper DISCARD assignment changed")
    command = command.replace(
        assignment, "DISCARD=" + shlex.quote(source), 1)
    if command.count("DISCARD=") != 1:
        raise AssertionError("helper has an ambiguous DISCARD assignment")
    return command


def fast_replace_script(app, newapp, workdir, **kwargs):
    """Keep the transaction real while shortening only its polling delays."""
    kwargs.setdefault("app_id", claude_pet._path_ident_str(app))
    kwargs.setdefault("work_id", claude_pet._path_ident_str(workdir))
    if not kwargs["app_id"] or not kwargs["work_id"]:
        raise AssertionError(
            "helper fixture must hand off existing APP and WORK identities")
    command = claude_pet._update_replace_script(
        str(app), str(newapp), str(workdir), **kwargs)
    command = inert_helper_launches(command)
    command = command.replace("sleep 1.5", ":")
    command = command.replace("while [ $i -lt 40 ]", "while [ $i -lt 8 ]")
    command = command.replace("  sleep 0.5", "  sleep 0.05")
    command = command.replace("sleep 3", "sleep 0.60")
    return command


class RealpathTempCase(unittest.TestCase):
    def setUp(self):
        self.td = Path(os.path.realpath(REAL_MKDTEMP()))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.test_home = self.td / "home"
        self.test_home.mkdir()
        self.lock_root = self.td / "owned-update-locks"
        lock_patch = mock.patch.object(
            claude_pet, "UPDATE_LOCK_DIR", str(self.lock_root))
        lock_patch.start()
        self.addCleanup(lock_patch.stop)

    def temporary_update_dir(self):
        return REAL_MKDTEMP(dir=self.td)

    def helper_env(self):
        env = os.environ.copy()
        env["HOME"] = str(self.test_home)
        return env


class StagedCopyRevalidationTests(RealpathTempCase):
    def test_post_ditto_mutation_is_seen_by_full_stage_revalidation(self):
        """Valid NEW plus invalid STAGE must not dispatch a replacement.

        The first validator call accepts the extracted bundle.  The copy seam
        then mutates only the same-parent staged copy.  A validate-once design
        returns True and dispatches; a full post-ditto validation sees the
        mutation and refuses before the helper can swap anything.
        """
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        calls = []
        copied_stage = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                # argv[4] is the extraction directory.
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                source, stage = Path(argv[1]), Path(argv[2])
                shutil.copytree(source, stage, symlinks=True,
                                dirs_exist_ok=True)
                copied_stage.append(stage)
                with (stage / "Contents" / "Info.plist").open("wb") as f:
                    plistlib.dump({"CFBundleIdentifier": "attacker.changed"}, f)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *_args, **_kwargs):
            path = Path(path)
            calls.append(path)
            with (path / "Contents" / "Info.plist").open("rb") as f:
                bundle_id = plistlib.load(f).get("CFBundleIdentifier")
            return bundle_id == claude_pet.BUNDLE_ID

        choice = {"asset": "claudepet-universal.zip", "arch": "x86_64",
                  "url": "https://example.invalid/ClaudePet-universal.zip",
                  "tag": "99.0"}
        with mock.patch.dict(claude_pet._upd_cache, {"choice": choice},
                             clear=False), \
             mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                choice["url"], app_path=str(installed),
                expect_version=choice["tag"])

        self.assertFalse(result,
                         "a post-ditto mutation was accepted for installation")
        self.assertFalse(popen.called,
                         "the replacement helper was dispatched after stage "
                         "validation failed")
        self.assertTrue(copied_stage,
                        "no same-parent staged copy was made; the test never "
                        "reached the post-ditto boundary")
        self.assertGreaterEqual(len(calls), 2,
                                "only the extracted app was validated")
        self.assertEqual(calls[-1], copied_stage[-1],
                         "the object validated last is not the object the "
                         "helper would swap into place")
        self.assertTrue((installed / "old-marker").is_file())


class ZipSymlinkPreExtractionTests(RealpathTempCase):
    """A lexical member-name scan is not a symlink-target scan.

    Each archive contains only lexically innocent names.  The first member is
    a Unix symlink whose *payload* escapes; the second sits below that symlink
    prefix and is therefore written outside the extraction root by extractors
    that honor Unix links.  Checking only ``..`` in member names accepts both
    archives and reaches ditto.
    """

    def make_symlink_zip(self, target):
        archive = self.td / ("absolute.zip" if target.startswith("/")
                             else "parent.zip")
        link = zipfile.ZipInfo("ClaudePet.app/Contents/Resources/redirect")
        link.create_system = 3
        link.external_attr = ((stat.S_IFLNK | 0o777) << 16)
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr(link, target)
            zf.writestr(
                "ClaudePet.app/Contents/Resources/redirect/payload", b"owned")
        return archive

    def assert_rejected_before_extraction(self, target):
        archive = self.make_symlink_zip(target)
        safe = claude_pet._zip_members_are_safe(archive)

        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")

        def retrieve(_url, destination):
            shutil.copyfile(archive, destination)

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet.subprocess, "run") as run, \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0")

        actual = (safe, run.called, popen.called, result)
        expected = (False, False, False, False)
        self.assertEqual(
            actual, expected,
            "(member_scan_safe, extraction_called, helper_called, install_result) "
            "for escaping Unix symlink target %r" % target)
        self.assertTrue((installed / "old-marker").is_file())

    def test_absolute_unix_symlink_target_with_child_member_is_rejected(self):
        self.assert_rejected_before_extraction("/tmp/claudepet-escape")

    def test_parent_unix_symlink_target_with_child_member_is_rejected(self):
        self.assert_rejected_before_extraction("../../../../../tmp/escape")


class LaunchAcknowledgementTests(RealpathTempCase):
    def setUp(self):
        super().setUp()
        self.installed = make_process_app(
            self.td / "ClaudePet.app", "old-marker")
        self.processes = []
        self.addCleanup(self._stop_processes)

    def _stop_processes(self):
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        subprocess.run(["/usr/bin/pkill", "-f", str(self.td)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)

    def _new_work(self, name="work"):
        work = self.td / name
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        return work, newapp

    def _run(self, launcher, work=None, newapp=None):
        if work is None or newapp is None:
            work, newapp = self._new_work()
        command = fast_replace_script(self.installed, newapp, work)
        launch_call = '$LAUNCH "$APP"'
        self.assertEqual(command.count(launch_call), 1,
                         "primary helper launch seam changed")
        command = command.replace(launch_call, launcher, 1)
        self.assertNotIn(launch_call, command,
                         "an unmatched primary $LAUNCH call remains")
        self.assertEqual(command.count("LAUNCH=:"), 1,
                         "rollback relaunch is not pinned to the inert command")
        return subprocess.run(["/bin/sh", "-c", command],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              env=self.helper_env(), timeout=30,
                              check=False)

    def _wait_for_match(self, pattern):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            found = subprocess.run(["/usr/bin/pgrep", "-f", pattern],
                                   capture_output=True, text=True).stdout.split()
            if found:
                return found
            time.sleep(0.05)
        return []

    def test_preexisting_macos_and_resources_pids_cannot_ack(self):
        mac = subprocess.Popen(
            [str(self.installed / "Contents" / "MacOS" / "ClaudePet"), "30"],
            env=self.helper_env())
        resource = subprocess.Popen(
            [sys.executable,
             str(self.installed / "Contents" / "Resources" / "claude_pet.py")],
            env=self.helper_env())
        self.processes.extend((mac, resource))

        mac_pattern = "^%s/Contents/MacOS/" % self.installed
        resource_pattern = ("^[^ ]*[Pp]ython[^ ]* %s/Contents/Resources/"
                            "claude_pet.py" % self.installed)
        self.assertIn(str(mac.pid), self._wait_for_match(mac_pattern),
                      "MacOS pre-existing PID fixture is not visible")
        self.assertIn(str(resource.pid), self._wait_for_match(resource_pattern),
                      "Resources fallback PID fixture is not visible")

        result = self._run(":")
        self.assertNotEqual(result.returncode, 0,
                            "pre-existing matching PIDs acknowledged a launch")
        self.assertTrue((self.installed / "old-marker").is_file())
        self.assertFalse((self.installed / "new-marker").exists())

    def test_only_a_pid_created_after_launch_can_ack(self):
        launcher = '"$APP/Contents/MacOS/ClaudePet" 5 &'
        result = self._run(launcher)
        self.assertEqual(result.returncode, 0,
                         "a newly launched, surviving PID was not accepted")
        self.assertTrue((self.installed / "new-marker").is_file())
        self.assertFalse((self.installed / "old-marker").exists())

    def test_same_ack_pid_must_survive_even_if_a_replacement_pid_exists(self):
        # First PID lives long enough for the 50ms poll to ACK it, then dies.
        # A second matching PID appears before the 600ms settle check.  A
        # rescan-any implementation passes; checking kill -0 on the original
        # ACK PID fails and rolls back.
        launcher = (
            '"$APP/Contents/MacOS/ClaudePet" 0.25 & '
            '(sleep 0.32; "$APP/Contents/MacOS/ClaudePet" 5 &) &')
        result = self._run(launcher)
        self.assertNotEqual(
            result.returncode, 0,
            "a different matching PID replaced the PID that was acknowledged")
        self.assertTrue((self.installed / "old-marker").is_file())
        self.assertFalse((self.installed / "new-marker").exists())


class UpdateLockLifecycleTests(RealpathTempCase):
    """The real installer acquires and transfers the transaction lock."""

    @staticmethod
    def install_patches(popen_side_effect, downloads):
        def retrieve(_url, destination):
            downloads.append(destination)
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        return (
            mock.patch.object(claude_pet, "_download_update_zip",
                              side_effect=retrieve),
            mock.patch.object(claude_pet, "_zip_members_are_safe",
                              return_value=True),
            mock.patch.object(claude_pet.subprocess, "run",
                              side_effect=fake_run),
            mock.patch.object(claude_pet, "validate_update_app",
                              return_value=True),
            mock.patch.object(claude_pet.subprocess, "Popen",
                              side_effect=popen_side_effect),
        )

    def test_install_hands_lock_to_child_and_serializes_real_transactions(self):
        """Distinguishes early close, missing lock, and parent fd leakage."""
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        handed_fd, children, downloads = [], [], []

        def spawn(_argv, **kwargs):
            passed = tuple(kwargs.get("pass_fds") or ())
            self.assertEqual(len(passed), 1,
                             "Popen did not receive exactly one lock fd")
            handed_fd.append(passed[0])
            proc = REAL_POPEN(
                [sys.executable, "-c", "import time; time.sleep(1.2)"],
                pass_fds=passed, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=self.helper_env())
            children.append(proc)
            return proc

        with ExitStack() as stack:
            for patch in self.install_patches(spawn, downloads):
                stack.enter_context(patch)
            first = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))
            self.assertTrue(first, "control install never reached Popen")
            self.assertEqual(len(downloads), 1)
            fd = handed_fd[0]
            with self.assertRaises(OSError) as closed:
                os.fstat(fd)
            self.assertEqual(closed.exception.errno, 9,
                             "parent still owns the transferred fd")
            second = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))
            self.assertFalse(second,
                             "second real transaction entered while child held lock")
            self.assertEqual(len(downloads), 1,
                             "rejected transaction downloaded before locking")

        children[0].wait(timeout=5)
        reacquired = claude_pet._acquire_update_lock(str(installed))
        self.assertIsNotNone(reacquired,
                             "child exited but transaction lock remained held")
        os.close(reacquired)

    def test_mkdtemp_exception_releases_lock_before_any_io(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        captured = []
        real_acquire = claude_pet._acquire_update_lock

        def acquire(path):
            fd = real_acquire(path)
            captured.append(fd)
            return fd

        with mock.patch.object(claude_pet, "_acquire_update_lock",
                               side_effect=acquire), \
             mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=OSError("synthetic mkdtemp failure")), \
             mock.patch.object(claude_pet,
                               "_download_update_zip") as retrieve, \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            raised = None
            try:
                result = claude_pet.install_github_update(
                    "https://example.invalid/ClaudePet.zip",
                    app_path=str(installed), expect_version="99.0",
                    expect_arches=("arm64",))
            except Exception as exc:
                raised = type(exc).__name__
                result = None

        self.assertTrue(captured and captured[0] is not None)
        try:
            os.fstat(captured[0])
            original_closed = False
        except OSError as exc:
            original_closed = exc.errno == 9
        reacquired = real_acquire(str(installed))
        reacquire_ok = reacquired is not None
        if reacquired is not None:
            os.close(reacquired)
        if not original_closed:
            # Preserve the RED evidence above, then keep a buggy implementation
            # from contaminating every later test with its leaked flock/fd.
            os.close(captured[0])
        self.assertEqual(
            (raised, result, retrieve.called, popen.called,
             original_closed, reacquire_ok),
            (None, False, False, False, True, True),
            "(raised, result, downloaded, spawned, original_fd_closed, "
            "reacquired)")

    def test_complete_uninstall_waits_for_active_update_transaction(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        installed_identity = (os.lstat(installed).st_dev,
                              os.lstat(installed).st_ino)
        fd = claude_pet._acquire_update_lock(str(installed))
        self.assertIsNotNone(fd)
        lock = Path(claude_pet._update_lock_path(str(installed)))
        root_identity = (os.lstat(self.lock_root).st_dev,
                         os.lstat(self.lock_root).st_ino)
        lock_identity = (os.lstat(lock).st_dev, os.lstat(lock).st_ino)
        child = REAL_POPEN(
            [sys.executable, "-c", "import time; time.sleep(1.2)"],
            pass_fds=(fd,), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env())
        os.close(fd)

        with mock.patch.object(claude_pet, "UNINSTALL_PATHS",
                               (str(self.lock_root),)), \
             mock.patch.object(claude_pet, "app_bundle_path",
                               return_value=str(installed)), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            first = claude_pet.do_uninstall()

        root_same = (self.lock_root.exists() and
                     (os.lstat(self.lock_root).st_dev,
                      os.lstat(self.lock_root).st_ino) == root_identity)
        lock_same = (lock.exists() and
                     (os.lstat(lock).st_dev, os.lstat(lock).st_ino)
                     == lock_identity)
        busy_app_same = (
            installed.exists()
            and (installed / "old-marker").is_file()
            and (os.lstat(installed).st_dev, os.lstat(installed).st_ino)
            == installed_identity)
        second_fd = claude_pet._acquire_update_lock(str(installed))
        still_blocked = second_fd is None
        if second_fd is not None:
            os.close(second_fd)
        child.wait(timeout=5)

        deletion_helpers = []

        def spawn_deletion(argv, **kwargs):
            proc = REAL_POPEN(
                argv, env=self.helper_env(), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, **kwargs)
            deletion_helpers.append(proc)
            return proc

        with mock.patch.object(claude_pet, "UNINSTALL_PATHS",
                               (str(self.lock_root),)), \
             mock.patch.object(claude_pet, "app_bundle_path",
                               return_value=str(installed)), \
             mock.patch.object(claude_pet.subprocess, "Popen",
                               side_effect=spawn_deletion):
            after = claude_pet.do_uninstall()
        self.assertEqual(len(deletion_helpers), 1,
                         "idle uninstall did not launch one deletion helper")
        deletion_helpers[0].wait(timeout=6)

        self.assertEqual(
            (first, popen.called, root_same, lock_same, busy_app_same,
             still_blocked, after, len(deletion_helpers),
             installed.exists(), self.lock_root.exists()),
            ((False, "update in progress"), False, True, True, True, True,
             (True, None), 1, False, False),
            "(busy_result, busy_spawned, root_same, lock_same, busy_app_same, "
            "second_acquire_blocked, idle_result, idle_helper_count, "
            "app_present_after_helper, root_present_after_helper)")

    def test_uninstall_popen_failure_preserves_app_and_all_settings(self):
        """Preparing the deletion helper must precede every destructive step.

        A Popen failure is a normal pre-handoff failure: no detached process
        exists to finish the transaction.  Deleting settings before that
        boundary leaves a half-uninstalled application, so every configured
        target and the exact installed bundle must remain recoverable.
        """
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        app_stat = REAL_LSTAT(installed)

        settings = self.td / "settings"
        preferences = self.td / "preferences"
        saved_state = self.td / "saved-state"
        settings.mkdir()
        preferences.mkdir()
        saved_state.mkdir()
        self.lock_root.mkdir(mode=0o700)

        configured_files = (
            settings / "claude-pet.json",
            settings / "claude-pet.json.lock",
            settings / "claudepet-debug.log",
            preferences / "me.yeongyu.claudepet.plist",
        )
        for index, path in enumerate(configured_files):
            path.write_bytes(("settings-sentinel-%d\n" % index).encode())
        state_sentinel = saved_state / "window-state"
        state_sentinel.write_bytes(b"saved-state-sentinel\n")
        lock_sentinel = self.lock_root / "owned-cache-sentinel"
        lock_sentinel.write_bytes(b"lock-root-sentinel\n")

        def file_state(path):
            try:
                st = REAL_LSTAT(path)
                if not stat.S_ISREG(st.st_mode):
                    return None
                return (Path(path).read_bytes(), st.st_dev, st.st_ino)
            except OSError:
                return None

        file_sentinels = configured_files + (state_sentinel, lock_sentinel)
        before_files = {str(p): file_state(p) for p in file_sentinels}
        before_dirs = {
            str(saved_state): (REAL_LSTAT(saved_state).st_dev,
                               REAL_LSTAT(saved_state).st_ino),
            str(self.lock_root): (REAL_LSTAT(self.lock_root).st_dev,
                                  REAL_LSTAT(self.lock_root).st_ino),
        }

        uninstall_paths = tuple(str(p) for p in configured_files) + (
            str(saved_state), str(self.lock_root))
        with mock.patch.object(claude_pet, "UNINSTALL_PATHS",
                               uninstall_paths), \
             mock.patch.object(claude_pet, "app_bundle_path",
                               return_value=str(installed)), \
             mock.patch.object(
                 claude_pet.subprocess, "Popen",
                 side_effect=OSError("synthetic uninstall helper failure")) \
                as popen:
            result = claude_pet.do_uninstall()

        after_files = {str(p): file_state(p) for p in file_sentinels}
        after_dirs = {}
        for path in (saved_state, self.lock_root):
            try:
                st = REAL_LSTAT(path)
                after_dirs[str(path)] = (st.st_dev, st.st_ino)
            except OSError:
                after_dirs[str(path)] = None
        try:
            current_app = REAL_LSTAT(installed)
            after_app = ((current_app.st_dev, current_app.st_ino),
                         (installed / "old-marker").read_bytes())
        except OSError:
            after_app = None

        self.assertEqual(result,
                         (False, "synthetic uninstall helper failure"))
        popen.assert_called_once()
        self.assertEqual(
            after_app,
            ((app_stat.st_dev, app_stat.st_ino), b"old-marker"),
            "a failed deletion-helper handoff changed the installed app")
        self.assertEqual(
            (after_files, after_dirs), (before_files, before_dirs),
            "a failed deletion-helper handoff partially deleted settings, "
            "configuration, saved state, or lock-root sentinels")


class UpdateLockCommandWrapperTests(RealpathTempCase):
    """Public manual-installer wrapper: one lock path and exact exit codes."""

    def setUp(self):
        super().setUp()
        home_patch = mock.patch.dict(
            os.environ, {"HOME": str(self.test_home)}, clear=False)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        self.app = self.td / "Manual ClaudePet.app"

    def wrapper_argv(self, *command):
        return ["claude_pet.py", "--with-update-lock", str(self.app), "--",
                *map(str, command)]

    def test_usage_errors_return_2_without_lock_or_child(self):
        malformed = (
            ["claude_pet.py"],
            ["claude_pet.py", "--with-update-lock"],
            ["claude_pet.py", "--with-update-lock", str(self.app)],
            ["claude_pet.py", "--with-update-lock", str(self.app), "--"],
            ["claude_pet.py", "--with-update-lock", str(self.app),
             "not-a-separator", "/usr/bin/true"],
        )
        with mock.patch.object(claude_pet, "_acquire_update_lock") as acquire, \
             mock.patch.object(claude_pet.subprocess, "call") as child:
            results = [claude_pet._run_with_update_lock(argv)
                       for argv in malformed]

        self.assertEqual(results, [2] * len(malformed))
        acquire.assert_not_called()
        child.assert_not_called()

    def test_busy_lock_returns_100_without_starting_child(self):
        held = claude_pet._acquire_update_lock(str(self.app))
        self.assertIsNotNone(held, "control lock acquisition failed")
        try:
            with mock.patch.object(claude_pet.subprocess, "call") as child:
                rc = claude_pet._run_with_update_lock(
                    self.wrapper_argv("/usr/bin/true"))
        finally:
            os.close(held)

        self.assertEqual(rc, 100)
        child.assert_not_called()

    def test_untrusted_lock_root_returns_101_without_outside_write(self):
        outside = self.td / "untrusted-root-target"
        outside.mkdir()
        os.symlink(outside, self.lock_root)
        with mock.patch.object(claude_pet.subprocess, "call") as child:
            rc = claude_pet._run_with_update_lock(
                self.wrapper_argv("/usr/bin/true"))

        self.assertEqual(rc, 101)
        child.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [],
                         "untrusted root caused an outside lock-file write")

    def test_exec_failure_returns_127_and_releases_lock(self):
        missing = self.td / "definitely-no-command"
        rc = claude_pet._run_with_update_lock(self.wrapper_argv(missing))
        reacquired = claude_pet._acquire_update_lock(str(self.app))
        try:
            self.assertEqual(rc, 127)
            self.assertIsNotNone(
                reacquired, "exec failure leaked the wrapper's transaction lock")
        finally:
            if reacquired is not None:
                os.close(reacquired)

    def test_child_return_code_is_passed_through_exactly(self):
        rc = claude_pet._run_with_update_lock(
            self.wrapper_argv(sys.executable, "-c", "raise SystemExit(37)"))
        self.assertEqual(rc, 37)

    def test_child_signal_is_mapped_to_128_plus_signal(self):
        code = ("import os,signal; "
                "os.kill(os.getpid(), signal.SIGTERM)")
        rc = claude_pet._run_with_update_lock(
            self.wrapper_argv(sys.executable, "-c", code))
        self.assertEqual(rc, 128 + signal.SIGTERM)

    def test_background_descendant_cannot_retain_lock_after_return(self):
        """Only the wrapper owns the fd; a surviving grandchild cannot.

        The direct child creates a benign descendant and exits immediately.
        A wrapper that passes its lock fd to that child appears to have
        returned, yet a second transaction remains busy until the descendant
        dies.  The correct wrapper closes nonstandard fds at exec, so the
        second acquire succeeds while the recorded descendant is still alive.
        """
        pid_file = self.td / "background-descendant.pid"
        stop_file = self.td / "stop-background-descendant"
        # fork(), rather than another subprocess.Popen(), is deliberate.  The
        # grandchild must inherit every fd the wrapper accidentally handed to
        # its direct child; a second Popen(close_fds=True) would hide that bug.
        child_code = "\n".join((
            "from pathlib import Path",
            "import os,sys,time",
            "pid=os.fork()",
            "if pid == 0:",
            "    stop=Path(sys.argv[1])",
            "    deadline=time.monotonic()+20",
            "    while not stop.exists() and time.monotonic()<deadline:",
            "        time.sleep(0.02)",
            "    os._exit(0)",
            "Path(sys.argv[2]).write_text(str(pid))",
        ))

        descendant_pid = None
        second = None
        try:
            rc = claude_pet._run_with_update_lock(self.wrapper_argv(
                sys.executable, "-c", child_code, stop_file, pid_file))
            self.assertTrue(pid_file.is_file(),
                            "control child did not record its descendant")
            descendant_pid = int(pid_file.read_text())
            os.kill(descendant_pid, 0)
            second = claude_pet._acquire_update_lock(str(self.app))
            self.assertEqual(
                (rc, second is not None), (0, True),
                "a background descendant inherited the wrapper lock fd")
        finally:
            if second is not None:
                os.close(second)
            stop_file.write_bytes(b"stop\n")
            if descendant_pid is not None:
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    try:
                        os.kill(descendant_pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.02)
                else:
                    try:
                        os.kill(descendant_pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass


class LockAndTemporaryNameSafetyTests(RealpathTempCase):
    @staticmethod
    def path_bytes_and_inode(path):
        path = Path(path)
        if not path.is_file():
            return None
        return (path.read_bytes(), path.stat().st_ino)

    def test_python_failure_cleanup_does_not_follow_work_name_substitution(self):
        """Failure cleanup must delete the claimed WORK, never its pathname.

        The fstat seam covers an fd-bound cleanup: the name is replaced after
        the updater has read the identity of its open directory.  The rmtree
        seam covers the unsafe path-only implementation at the exact recursive
        deletion boundary.  In either design the assertion is the same: the
        rival now at WORK is not updater-owned and must survive byte-for-byte.
        """
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        work = self.td / "python-owned-work"
        work.mkdir(mode=0o700)
        (work / "owned-partial").write_bytes(b"owned temporary bytes")
        owned_stat = REAL_LSTAT(work)
        owned_identity = (owned_stat.st_dev, owned_stat.st_ino)
        displaced = self.td / "python-displaced-work"
        sentinel = work / "post-identity-work-rival"
        original = b"rival replaces WORK after cleanup identity read\n"
        rival_inode = []

        def substitute_work():
            work.rename(displaced)
            work.mkdir(mode=0o700)
            sentinel.write_bytes(original)
            rival_inode.append(sentinel.stat().st_ino)

        def fstat_then_substitute(fd):
            st = REAL_FSTAT(fd)
            if ((st.st_dev, st.st_ino) == owned_identity and
                    not rival_inode):
                substitute_work()
            return st

        def rmtree_then_substitute(path, *args, **kwargs):
            if (os.path.abspath(os.fspath(path)) == str(work) and
                    not rival_inode):
                substitute_work()
            return REAL_RMTREE(path, *args, **kwargs)

        def download(_url, destination):
            Path(destination).write_bytes(b"not inspected after safe reject")

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               return_value=str(work)), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=download), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=False), \
             mock.patch.object(claude_pet.os, "fstat",
                               side_effect=fstat_then_substitute), \
             mock.patch.object(claude_pet.shutil, "rmtree",
                               side_effect=rmtree_then_substitute), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertFalse(result)
        popen.assert_not_called()
        self.assertTrue(rival_inode,
                        "cleanup never reached an identity/delete boundary")
        self.assertEqual(self.path_bytes_and_inode(sentinel),
                         (original, rival_inode[0]),
                         "Python failure cleanup recursively deleted the "
                         "post-identity WORK rival")
        self.assertTrue(displaced.exists(),
                        "the displaced owned WORK was not safely retained")

    def test_helper_work_cleanup_uses_fd_bound_discard_and_preserves_rival(self):
        """Detached cleanup binds WORKID through the standalone fd helper."""
        parameters = inspect.signature(
            claude_pet._update_replace_script).parameters
        self.assertIn(
            "work_id", parameters,
            "Python cannot hand the claimed WORK identity to the helper")

        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        work = self.td / "detached-owned-work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        work_stat = REAL_LSTAT(work)
        work_id = "%d,%d" % (work_stat.st_dev, work_stat.st_ino)
        stage = self.td / ".work-cleanup-stage.app"
        shutil.copytree(newapp, stage, symlinks=True)
        stage_stat = REAL_LSTAT(stage)
        stage_id = "%d,%d" % (stage_stat.st_dev, stage_stat.st_ino)
        displaced = self.td / "helper-displaced-work"
        sentinel = work / "post-stat-work-rival"
        original = b"rival replaces WORK after discard fd verification\n"
        inode_record = self.td / "helper-work-rival-inode"
        discard_source = discard_program_with_root_swap(
            work, displaced, sentinel, original, inode_record)

        command = fast_replace_script(
            installed, newapp, work, staged=str(stage), stage_id=stage_id,
            work_id=work_id)
        self.assertEqual(command.count('discard "$WORK" "$WORKID"'), 2,
                         "not every helper cleanup branch is bound to WORKID")
        self.assertNotIn('rm -rf "$WORK"', command,
                         "helper retained path-only WORK deletion")
        self.assertNotIn('/usr/bin/stat -f %d,%i "$1"', command,
                         "helper retained shell stat-to-rm discard")
        command = replace_helper_discard_program(command, discard_source)
        exchange_boundary = 'test "$(/usr/bin/stat -f %d "$STAGE")" = '
        self.assertEqual(command.count(exchange_boundary), 1,
                         "cannot pin the helper's pre-exchange failure")
        command = command.replace(exchange_boundary,
                                  "false\n" + exchange_boundary, 1)

        result = subprocess.run(
            ["/bin/sh", "-c", command], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env(), timeout=20,
            check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(inode_record.is_file(),
                        "helper never cleaned WORK through _DISCARD_PY")
        self.assertEqual(
            self.path_bytes_and_inode(sentinel),
            (original, int(inode_record.read_text().strip())),
            "fd-bound helper discard deleted the post-verification WORK rival")
        self.assertTrue(displaced.exists(),
                        "the displaced owned WORK was unexpectedly lost")
        self.assertTrue((installed / "old-marker").is_file())

    def test_empty_dir_at_does_not_follow_directory_child_after_lstat_swap(self):
        root = self.td / "directory-child-cleanup"
        child = root / "child"
        displaced = root / "owned-directory-child"
        sentinel = child / "rival-sentinel"
        original = b"rival directory child after lstat\n"
        child.mkdir(parents=True)
        (child / "owned-marker").write_bytes(b"owned")
        injected = []
        root_fd = REAL_OPEN(root, os.O_RDONLY | os.O_DIRECTORY)

        def lstat_then_swap(path, *args, **kwargs):
            dir_fd = kwargs.get("dir_fd")
            st = REAL_LSTAT(path, *args, **kwargs)
            if path == "child" and dir_fd == root_fd and not injected:
                os.rename("child", displaced.name,
                          src_dir_fd=root_fd, dst_dir_fd=root_fd)
                os.mkdir("child", 0o700, dir_fd=root_fd)
                fd = REAL_OPEN(
                    "child/rival-sentinel",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600, dir_fd=root_fd)
                with os.fdopen(fd, "wb") as out:
                    out.write(original)
                injected.append((
                    REAL_LSTAT("child", dir_fd=root_fd).st_ino,
                    REAL_LSTAT("child/rival-sentinel",
                               dir_fd=root_fd).st_ino))
            return st

        try:
            with mock.patch.object(claude_pet.os, "lstat",
                                   side_effect=lstat_then_swap):
                claude_pet._empty_dir_at(root_fd)
        finally:
            os.close(root_fd)

        self.assertTrue(injected,
                        "directory child was not swapped after lstat")
        self.assertEqual(
            (child.is_dir(), child.stat().st_ino if child.is_dir() else None,
             self.path_bytes_and_inode(sentinel), displaced.exists()),
            (True, injected[0][0], (original, injected[0][1]), True),
            "cleanup opened or removed the rival directory child after "
            "checking the displaced child")

    def test_empty_dir_at_does_not_unlink_file_child_after_lstat_swap(self):
        root = self.td / "file-child-cleanup"
        root.mkdir()
        child = root / "leaf"
        displaced = root / "owned-file-child"
        child.write_bytes(b"owned")
        original = b"rival file child after lstat\n"
        injected = []
        root_fd = REAL_OPEN(root, os.O_RDONLY | os.O_DIRECTORY)

        def lstat_then_swap(path, *args, **kwargs):
            dir_fd = kwargs.get("dir_fd")
            st = REAL_LSTAT(path, *args, **kwargs)
            if path == "leaf" and dir_fd == root_fd and not injected:
                os.rename("leaf", displaced.name,
                          src_dir_fd=root_fd, dst_dir_fd=root_fd)
                fd = REAL_OPEN(
                    "leaf", os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600, dir_fd=root_fd)
                with os.fdopen(fd, "wb") as out:
                    out.write(original)
                injected.append(REAL_LSTAT("leaf", dir_fd=root_fd).st_ino)
            return st

        try:
            with mock.patch.object(claude_pet.os, "lstat",
                                   side_effect=lstat_then_swap):
                claude_pet._empty_dir_at(root_fd)
        finally:
            os.close(root_fd)

        self.assertTrue(injected, "file child was not swapped after lstat")
        self.assertEqual(
            (self.path_bytes_and_inode(child), displaced.read_bytes()),
            ((original, injected[0]), b"owned"),
            "cleanup unlinked the rival file child after checking the "
            "displaced file")

    def test_helper_binds_installed_app_identity_handed_off_by_python(self):
        """A rival APP substituted after Popen handoff must never be swapped."""
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        old_stat = REAL_LSTAT(installed)
        app_id = "%d,%d" % (old_stat.st_dev, old_stat.st_ino)
        retained = self.td / "retained-original-app"
        incoming_rival = make_process_app(
            self.td / "incoming-rival.app", "rival-marker")
        rival_stat = REAL_LSTAT(incoming_rival)
        rival_marker = incoming_rival / "rival-marker"
        rival_bytes = rival_marker.read_bytes()
        rival_marker_inode = rival_marker.stat().st_ino
        evidence = self.td / "unclaimed-app-was-exchanged"
        commands = []
        children = []
        work_dirs = []
        expected_work_ids = []

        def claim_work():
            path = Path(self.temporary_update_dir())
            work_dirs.append(path)
            return str(path)

        def download(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_process_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def spawn_after_app_substitution(argv, **kwargs):
            command = str(argv[2])
            commands.append(command)
            self.assertEqual(len(work_dirs), 1)
            work_stat = REAL_LSTAT(work_dirs[0])
            expected_work_ids.append(
                "%d,%d" % (work_stat.st_dev, work_stat.st_ino))
            installed.rename(retained)
            incoming_rival.rename(installed)
            command = inert_helper_launches(command)
            command = command.replace("sleep 1.5", ":")
            command = command.replace("while [ $i -lt 40 ]",
                                      "while [ $i -lt 8 ]")
            command = command.replace("  sleep 0.5", "  sleep 0.05")
            command = command.replace("sleep 3", "sleep 0.60")
            post_exchange = 'fi\nBEFORE="$SELFPID'
            if post_exchange in command:
                command = command.replace(
                    post_exchange,
                    "\n".join((
                        "fi",
                        'if [ -e "$APP/new-marker" ]; then : > %s; fi' %
                        shlex.quote(str(evidence)),
                        "false",
                        'BEFORE="$SELFPID',
                    )), 1)
            passed = tuple(kwargs.get("pass_fds") or ())
            proc = REAL_POPEN(
                ["/bin/sh", "-c", command], pass_fds=passed,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=self.helper_env())
            children.append(proc)
            return proc

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=claim_work), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=download), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "Popen",
                               side_effect=spawn_after_app_substitution):
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertTrue(result, "install never handed a helper transaction off")
        self.assertEqual(len(children), 1)
        children[0].wait(timeout=20)
        self.assertEqual(len(commands), 1)
        self.assertIn(
            "APPID=%s" % app_id, commands[0],
            "Python did not hand the original installed APP identity to the "
            "replacement helper")
        self.assertIn(
            "WORKID=%s" % expected_work_ids[0], commands[0],
            "Python did not hand the exact claimed WORK identity to the "
            "replacement helper")
        self.assertFalse(evidence.exists(),
                         "the helper exchanged an unclaimed replacement APP")
        installed_identity = None
        if installed.is_dir():
            st = REAL_LSTAT(installed)
            installed_identity = (st.st_dev, st.st_ino)
        retained_identity = None
        if retained.is_dir():
            st = REAL_LSTAT(retained)
            retained_identity = (st.st_dev, st.st_ino)
        self.assertEqual(
            (installed_identity,
             self.path_bytes_and_inode(installed / "rival-marker"),
             retained_identity,
             (retained / "old-marker").is_file()),
            ((rival_stat.st_dev, rival_stat.st_ino),
             (rival_bytes, rival_marker_inode),
             (old_stat.st_dev, old_stat.st_ino), True),
            "the rival APP was altered or the exact original APP was not "
            "retained for recovery")

    def test_manual_replacement_appid_mismatch_refuses_cross_path_swap(self):
        """A manual replacement racing the updater is an APPID mismatch.

        This exercises the detached helper independently of lock acquisition:
        both updater and manual paths may be individually serialized yet still
        meet at the installed pathname.  The helper may replace only the exact
        APP object Python observed before handoff.
        """
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        original_stat = REAL_LSTAT(installed)
        original_id = "%d,%d" % (original_stat.st_dev, original_stat.st_ino)
        retained = self.td / "manual-retained-original"
        manual = make_process_app(
            self.td / "manual-replacement.app", "manual-marker")
        manual_stat = REAL_LSTAT(manual)
        manual_marker = manual / "manual-marker"
        manual_marker_state = (manual_marker.read_bytes(),
                               manual_marker.stat().st_ino)

        work = self.td / "manual-race-work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        work_stat = REAL_LSTAT(work)
        work_id = "%d,%d" % (work_stat.st_dev, work_stat.st_ino)
        stage = self.td / ".manual-race-stage.app"
        shutil.copytree(newapp, stage, symlinks=True)
        stage_stat = REAL_LSTAT(stage)
        stage_id = "%d,%d" % (stage_stat.st_dev, stage_stat.st_ino)
        evidence = self.td / "appid-mismatch-crossed-exchange"

        command = fast_replace_script(
            installed, newapp, work, staged=str(stage), stage_id=stage_id,
            app_id=original_id, work_id=work_id)
        self.assertIn("APPID=%s" % original_id, command)
        post_exchange = 'fi\nBEFORE="$SELFPID'
        self.assertIn(post_exchange, command,
                      "cannot observe the APPID-to-exchange boundary")
        command = command.replace(
            post_exchange,
            "\n".join((
                "fi",
                'if [ -e "$APP/new-marker" ]; then : > %s; fi' %
                shlex.quote(str(evidence)),
                "false",
                'BEFORE="$SELFPID',
            )), 1)

        installed.rename(retained)
        manual.rename(installed)
        result = subprocess.run(
            ["/bin/sh", "-c", command], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env(), timeout=20,
            check=False)

        current_stat = REAL_LSTAT(installed)
        retained_stat = REAL_LSTAT(retained)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            evidence.exists(),
            "the helper crossed the exchange boundary after APPID changed")
        self.assertEqual(
            ((current_stat.st_dev, current_stat.st_ino),
             self.path_bytes_and_inode(installed / "manual-marker"),
             (retained_stat.st_dev, retained_stat.st_ino),
             (retained / "old-marker").read_bytes()),
            ((manual_stat.st_dev, manual_stat.st_ino), manual_marker_state,
             (original_stat.st_dev, original_stat.st_ino), b"old-marker"),
            "the helper altered the manual replacement or lost the exact "
            "original app after an APPID mismatch")

    def test_owned_private_lock_root_has_normal_acquire_release_lifecycle(self):
        installed = self.td / "ClaudePet.app"
        self.lock_root.mkdir(mode=0o700)
        first = claude_pet._acquire_update_lock(str(installed))
        self.assertIsNotNone(first)
        lock = Path(claude_pet._update_lock_path(str(installed)))
        self.assertEqual(lock.parent, self.lock_root)
        self.assertTrue(stat.S_ISREG(os.lstat(lock).st_mode))
        self.assertIsNone(claude_pet._acquire_update_lock(str(installed)))
        os.close(first)
        second = claude_pet._acquire_update_lock(str(installed))
        self.assertIsNotNone(second)
        os.close(second)

    def test_replaced_lock_root_cannot_create_a_second_lock_domain(self):
        """One app must not acquire two locks through two same-named roots."""
        installed = self.td / "ClaudePet.app"
        self.lock_root.mkdir(mode=0o700)
        displaced_root = self.td / "original-owned-update-locks"
        first = None
        second = None
        evidence = {}
        try:
            first = claude_pet._acquire_update_lock(str(installed))
            self.assertIsNotNone(first, "control lock acquisition failed")
            lock_name = Path(
                claude_pet._update_lock_path(str(installed))).name
            first_root_stat = os.lstat(self.lock_root)
            first_lock_stat = os.lstat(self.lock_root / lock_name)

            self.lock_root.rename(displaced_root)
            self.lock_root.mkdir(mode=0o700)
            second_root_stat = os.lstat(self.lock_root)
            self.assertNotEqual(first_root_stat.st_ino,
                                second_root_stat.st_ino)

            second = claude_pet._acquire_update_lock(str(installed))
            evidence = {
                "second_blocked": second is None,
                "first_fd_lock": (os.fstat(first).st_dev,
                                  os.fstat(first).st_ino),
                "first_root": (os.lstat(displaced_root).st_dev,
                               os.lstat(displaced_root).st_ino),
                "first_lock": (
                    os.lstat(displaced_root / lock_name).st_dev,
                    os.lstat(displaced_root / lock_name).st_ino),
                "second_root": (os.lstat(self.lock_root).st_dev,
                                os.lstat(self.lock_root).st_ino),
            }
            expected = {
                "second_blocked": True,
                "first_fd_lock": (first_lock_stat.st_dev,
                                  first_lock_stat.st_ino),
                "first_root": (first_root_stat.st_dev,
                               first_root_stat.st_ino),
                "first_lock": (first_lock_stat.st_dev,
                               first_lock_stat.st_ino),
                "second_root": (second_root_stat.st_dev,
                                second_root_stat.st_ino),
            }
        finally:
            if second is not None:
                os.close(second)
            if first is not None:
                os.close(first)

        self.assertEqual(
            evidence, expected,
            "root replacement created a split-lock domain or changed one "
            "of the preserved root/lock identities")

    def test_public_sibling_regular_file_is_never_selected_or_changed(self):
        installed = self.td / "ClaudePet.app"
        sibling = self.td / ".claudepet-update-ClaudePet.app.lock"
        original = b"unrelated regular sibling\n"
        sibling.write_bytes(original)
        inode = sibling.stat().st_ino
        fd = claude_pet._acquire_update_lock(str(installed))
        self.assertIsNotNone(fd)
        os.close(fd)
        actual = Path(claude_pet._update_lock_path(str(installed)))
        self.assertNotEqual(actual, sibling)
        self.assertEqual(actual.parent, self.lock_root)
        self.assertEqual(self.path_bytes_and_inode(sibling), (original, inode))

    def test_lock_root_symlink_is_refused_without_outside_creation(self):
        installed = self.td / "ClaudePet.app"
        outside = self.td / "outside"
        outside.mkdir()
        os.symlink(outside, self.lock_root)
        fd = claude_pet._acquire_update_lock(str(installed))
        if fd is not None:
            os.close(fd)
        self.assertIsNone(fd, "a symlink lock root was trusted")
        self.assertEqual(list(outside.iterdir()), [],
                         "the symlink root caused an outside lock-file write")

    def test_world_writable_lock_root_is_refused(self):
        installed = self.td / "ClaudePet.app"
        self.lock_root.mkdir(mode=0o700)
        self.lock_root.chmod(0o777)
        fd = claude_pet._acquire_update_lock(str(installed))
        if fd is not None:
            os.close(fd)
        self.assertIsNone(fd, "a world-writable lock root was trusted")

    def test_fifo_lock_root_fails_closed_without_blocking(self):
        installed = self.td / "ClaudePet.app"
        os.mkfifo(self.lock_root, 0o600)
        inode = os.lstat(self.lock_root).st_ino
        code = (
            "import claude_pet,sys;"
            "claude_pet.UPDATE_LOCK_DIR=sys.argv[1];"
            "fd=claude_pet._acquire_update_lock(sys.argv[2]);"
            "sys.exit(0 if fd is None else 3)")
        proc = REAL_POPEN([sys.executable, "-c", code, str(self.lock_root),
                           str(installed)], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, env=self.helper_env())
        try:
            rc = proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
            self.fail("FIFO lock root acquisition blocked")
        after = os.lstat(self.lock_root)
        self.assertEqual((rc, stat.S_ISFIFO(after.st_mode), after.st_ino),
                         (0, True, inode))

    def test_symlink_lock_leaf_fails_closed_without_target_change(self):
        installed = self.td / "ClaudePet.app"
        self.lock_root.mkdir(mode=0o700)
        lock = Path(claude_pet._update_lock_path(str(installed)))
        target = self.td / "outside-target"
        original = b"must not be opened or truncated\n"
        target.write_bytes(original)
        inode = target.stat().st_ino
        os.symlink(target, lock)
        fd = claude_pet._acquire_update_lock(str(installed))
        if fd is not None:
            os.close(fd)
        self.assertIsNone(fd)
        self.assertEqual(self.path_bytes_and_inode(target), (original, inode))

    def test_fifo_lock_leaf_fails_closed_without_blocking(self):
        installed = self.td / "ClaudePet.app"
        self.lock_root.mkdir(mode=0o700)
        lock = Path(claude_pet._update_lock_path(str(installed)))
        os.mkfifo(lock, 0o600)
        inode = os.lstat(lock).st_ino
        code = (
            "import claude_pet,sys;"
            "claude_pet.UPDATE_LOCK_DIR=sys.argv[1];"
            "fd=claude_pet._acquire_update_lock(sys.argv[2]);"
            "sys.exit(0 if fd is None else 3)")
        proc = REAL_POPEN([sys.executable, "-c", code, str(self.lock_root),
                           str(installed)], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, env=self.helper_env())
        try:
            rc = proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
            self.fail("FIFO lock acquisition blocked")
        self.assertEqual(rc, 0)
        after = os.lstat(lock)
        self.assertTrue(stat.S_ISFIFO(after.st_mode))
        self.assertEqual(after.st_ino, inode)

    def test_preexisting_stage_name_collision_never_deletes_the_sentinel(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        random_bytes = b"\xab" * 4
        collision = self.td / (".claudepet-new-%d-%s.app" %
                               (os.getpid(), random_bytes.hex()))
        collision.mkdir()
        sentinel = collision / "user-sentinel"
        original = b"preexisting directory contents\n"
        sentinel.write_bytes(original)
        inode = sentinel.stat().st_ino
        extracted_validations = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                # A safe implementation either refuses this already-existing
                # destination or chooses a different exclusively-created one.
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *_args, **_kwargs):
            extracted_validations.append(Path(path))
            return True

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen"):
            claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0")

        self.assertTrue(extracted_validations,
                        "the install never reached the stage-name seam")
        self.assertTrue(sentinel.is_file(),
                        "the colliding pre-existing directory was recursively "
                        "deleted")
        self.assertEqual((sentinel.read_bytes(), sentinel.stat().st_ino),
                         (original, inode),
                         "the collision sentinel was replaced or rewritten")

    def test_rival_reclaim_after_claim_release_is_never_consumed_or_deleted(self):
        """Covers the separate mkdir-then-rmdir staging-name race.

        A directory that existed before the claim is the preceding test.  This
        fixture instead lets production create the name successfully, then
        inserts a rival immediately if production releases that claim with
        ``rmdir``.  Secure implementations keep ownership until ditto has
        populated the stage, so no rival is inserted and installation may
        continue.  A released-claim implementation must fail closed and must
        not let its cleanup recursively delete the rival's sentinel.
        """
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        random_bytes = b"\xcd" * 4
        candidate = self.td / (".claudepet-new-%d-%s.app" %
                               (os.getpid(), random_bytes.hex()))
        sentinel = candidate / "post-claim-rival"
        original = b"created after the updater released its claim\n"
        real_rmdir = os.rmdir
        rival_inserted = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def rmdir_then_rival(path, *args, **kwargs):
            result = real_rmdir(path, *args, **kwargs)
            if (not rival_inserted and not args and not kwargs and
                    os.path.abspath(os.fspath(path)) == str(candidate)):
                candidate.mkdir()
                sentinel.write_bytes(original)
                rival_inserted.append(sentinel.stat().st_ino)
            return result

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *_args, **_kwargs):
            # A rival marker makes the stage an object the updater never
            # exclusively owned, so the second preflight must reject it.
            return not (Path(path) / sentinel.name).exists()

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes), \
             mock.patch.object(claude_pet.os, "rmdir",
                               side_effect=rmdir_then_rival), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0")

        if not rival_inserted:
            self.assertTrue(result,
                            "an exclusively retained empty stage was not usable")
            self.assertTrue(popen.called)
            return

        self.assertFalse(result,
                         "the updater consumed a name reclaimed by a rival")
        popen.assert_not_called()
        self.assertTrue(sentinel.is_file(),
                        "cleanup recursively deleted the post-claim rival")
        self.assertEqual((sentinel.read_bytes(), sentinel.stat().st_ino),
                         (original, rival_inserted[0]),
                         "the post-claim rival sentinel was altered")

    def test_partial_stage_copy_failure_removes_only_owned_candidate(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        occupied_bytes, selected_bytes = b"\xaa" * 4, b"\xbb" * 4
        occupied = self.td / (".claudepet-new-%d-%s.app" %
                              (os.getpid(), occupied_bytes.hex()))
        selected = self.td / (".claudepet-new-%d-%s.app" %
                              (os.getpid(), selected_bytes.hex()))
        occupied.mkdir()
        sentinel = occupied / "preexisting-sentinel"
        original = b"preexisting collision survives partial copy\n"
        sentinel.write_bytes(original)
        inode = sentinel.stat().st_ino

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                Path(argv[2], "partial-copy-marker").write_bytes(b"partial")
                raise subprocess.CalledProcessError(71, argv)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet.os, "urandom",
                               side_effect=[occupied_bytes, selected_bytes]), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertFalse(result)
        popen.assert_not_called()
        self.assertFalse(selected.exists(),
                         "partial owned staging tree survived a copy failure")
        self.assertEqual(self.path_bytes_and_inode(sentinel), (original, inode))

    def test_cleanup_does_not_follow_stage_name_substitution(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        random_bytes = b"\xcc" * 4
        stage = self.td / (".claudepet-new-%d-%s.app" %
                           (os.getpid(), random_bytes.hex()))
        displaced = self.td / "displaced-owned-stage"
        sentinel = stage / "rival-sentinel"
        original = b"rival replaces stage name before cleanup\n"
        rival_inode = []
        validations = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *_args, **_kwargs):
            validations.append(Path(path))
            if Path(path) == stage:
                stage.rename(displaced)
                stage.mkdir()
                sentinel.write_bytes(original)
                rival_inode.append(sentinel.stat().st_ino)
                return False
            return True

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertFalse(result)
        popen.assert_not_called()
        self.assertIn(stage, validations)
        self.assertEqual(self.path_bytes_and_inode(sentinel),
                         (original, rival_inode[0]))
        self.assertTrue(displaced.exists(),
                        "safe cleanup unexpectedly removed displaced owned tree")

    def test_prehandoff_cleanup_binds_stage_beneath_open_parent(self):
        """A stage rival inserted after parent-open must not be traversed.

        ``_discard_owned_dir`` first pins the parent directory with a nofollow
        fd and then opens the claimed child relative to it.  The fixture swaps
        that child name after the parent fd is open but immediately before the
        child open.  The rival has a different inode, so cleanup must neither
        descend into nor recursively delete it.
        """
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        random_bytes = b"\xee" * 4
        stage = self.td / (".claudepet-new-%d-%s.app" %
                           (os.getpid(), random_bytes.hex()))
        displaced = self.td / "python-cleanup-owned-stage"
        sentinel = stage / "post-lstat-rival"
        original = b"rival installed after cleanup identity read\n"
        rival_inode = []
        cleanup_parent_opened = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *_args, **_kwargs):
            # Reject only the same-parent copy so Python enters its pre-handoff
            # cleanup.  The extracted bundle remains a valid input fixture.
            return Path(path) != stage

        def open_parent_then_swap(path, *args, **kwargs):
            fd = REAL_OPEN(path, *args, **kwargs)
            absolute = (os.path.abspath(os.fspath(path))
                        if isinstance(path, (str, bytes, os.PathLike)) else None)
            if (absolute == str(self.td) and not rival_inode and
                    stage.exists()):
                cleanup_parent_opened.append(fd)
                stage.rename(displaced)
                stage.mkdir()
                sentinel.write_bytes(original)
                rival_inode.append(sentinel.stat().st_ino)
            return fd

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.os, "open",
                               side_effect=open_parent_then_swap), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertFalse(result)
        popen.assert_not_called()
        self.assertTrue(cleanup_parent_opened,
                        "cleanup never opened the stage parent")
        self.assertEqual(self.path_bytes_and_inode(sentinel),
                         (original, rival_inode[0]),
                         "cleanup deleted a rival substituted after lstat")
        self.assertTrue(displaced.exists(),
                        "the displaced updater-owned stage was unexpectedly lost")

    def test_helper_refuses_stage_replaced_after_handoff_before_exchange(self):
        """The app installed by exchange must be the exact claimed STAGE."""
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        work = self.td / "work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        stage = self.td / ".claimed-stage.app"
        shutil.copytree(newapp, stage, symlinks=True)
        claimed = REAL_LSTAT(stage)
        stage_id = "%d,%d" % (claimed.st_dev, claimed.st_ino)
        displaced = self.td / "displaced-claimed-stage"
        evidence = self.td / "rival-reached-installed-path"
        app_identity_record = self.td / "post-exchange-app-identity"
        inode_record = self.td / "rival-sentinel-inode"
        sentinel = stage / "post-handoff-rival"
        original = b"rival substituted before exchange\n"

        command = fast_replace_script(
            installed, newapp, work, staged=str(stage), stage_id=stage_id)
        stage_identity_gate = (
            'test "$(/usr/bin/stat -f %d,%i "$STAGE" '
            '2>/dev/null || true)" = "$STAGEID"')
        self.assertEqual(
            command.count(stage_identity_gate), 1,
            "pre-exchange STAGEID gate is absent or ambiguous")
        replacement = "\n".join((
            'mv "$STAGE" %s' % shlex.quote(str(displaced)),
            'mkdir "$STAGE"',
            "printf 'rival substituted before exchange\\n' > "
            '"$STAGE/post-handoff-rival"',
            '/usr/bin/stat -f %%i "$STAGE/post-handoff-rival" > %s' %
            shlex.quote(str(inode_record)),
            stage_identity_gate,
        ))
        command = command.replace(stage_identity_gate, replacement, 1)
        post_exchange = 'fi\nBEFORE="$SELFPID'
        self.assertIn(post_exchange, command,
                      "cannot inject proof immediately after exchange")
        proof = "\n".join((
            "fi",
            '/usr/bin/stat -f %%d,%%i "$APP" > %s' %
            shlex.quote(str(app_identity_record)),
            'if [ -e "$APP/post-handoff-rival" ]; then : > %s; fi' %
            shlex.quote(str(evidence)),
            "false",
            'BEFORE="$SELFPID',
        ))
        command = command.replace(post_exchange, proof, 1)

        result = subprocess.run(
            ["/bin/sh", "-c", command], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env(), timeout=20,
            check=False)

        self.assertNotEqual(result.returncode, 0,
                            "the substituted stage was not rejected before "
                            "exchange")
        self.assertTrue(inode_record.is_file(),
                        "the fixture never substituted the claimed stage")
        if app_identity_record.is_file():
            self.assertEqual(
                app_identity_record.read_text().strip(), stage_id,
                "post-exchange APP was not the exact stage inode handed off "
                "by Python")
        self.assertFalse(evidence.exists(),
                         "a different inode than the claimed stage reached APP")
        self.assertTrue((installed / "old-marker").is_file(),
                        "the helper did not retain or restore the old app")
        self.assertFalse((installed / "post-handoff-rival").exists())
        self.assertEqual(
            self.path_bytes_and_inode(sentinel),
            (original, int(inode_record.read_text().strip())),
            "rollback/cleanup altered the substituted rival")
        self.assertTrue(displaced.exists(),
                        "the originally claimed stage was unexpectedly deleted")

    def test_fd_bound_discard_preserves_root_replaced_after_fstat(self):
        """The standalone discard must keep using its verified directory fd."""
        owned = self.td / "discard-owned-root"
        owned.mkdir()
        (owned / "owned-leaf").write_bytes(b"owned temporary data\n")
        claimed = REAL_LSTAT(owned)
        claimed_id = "%d,%d" % (claimed.st_dev, claimed.st_ino)
        displaced = self.td / "discard-displaced-root"
        sentinel = owned / "discard-rival"
        original = b"rival substituted after discard root fstat\n"
        inode_record = self.td / "discard-rival-inode"
        source = discard_program_with_root_swap(
            owned, displaced, sentinel, original, inode_record)

        result = subprocess.run(
            [sys.executable, "-c", source, str(owned), claimed_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env(), timeout=20,
            check=False)

        self.assertNotEqual(result.returncode, 0,
                            "discard accepted a different root identity")
        self.assertTrue(inode_record.is_file(),
                        "discard never reached its post-fstat injection seam")
        self.assertEqual(
            self.path_bytes_and_inode(sentinel),
            (original, int(inode_record.read_text().strip())),
            "fd-bound discard followed the pathname to a post-fstat rival")
        self.assertTrue(displaced.exists(),
                        "the displaced owned root was unexpectedly lost")

    def test_exchange_failure_keeps_exact_old_app_without_forward_mv_backup(self):
        """Atomic exchange failure must stop before any forward-path move."""
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        old_stat = REAL_LSTAT(installed)
        old_identity = (old_stat.st_dev, old_stat.st_ino)
        work = self.td / "work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        stage = self.td / ".backup-race-stage.app"
        shutil.copytree(newapp, stage, symlinks=True)
        claimed = REAL_LSTAT(stage)
        stage_id = "%d,%d" % (claimed.st_dev, claimed.st_ino)
        random_bytes = b"\xef" * 4
        backup = self.td / (".claudepet-old-%d-%s" %
                            (os.getpid(), random_bytes.hex()))

        with mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes):
            command = fast_replace_script(
                installed, newapp, work, staged=str(stage),
                stage_id=stage_id)
        # Make both atomic exchange attempts fail.  The only safe forward
        # behavior is to stop while the exact old APP is still in place.
        command = command.replace("exchange() {",
                                  "exchange() {\n  return 1", 1)
        forward_moves = (
            '\n  rmdir "$BACKUP"\n',
            '\n  mv "$APP" "$BACKUP"\n',
            '\n  mv "$STAGE" "$APP"\n',
        )
        for old_fallback_line in forward_moves:
            self.assertNotIn(
                old_fallback_line, command,
                "non-atomic forward replacement fallback is still present")
        relaunch_guard = (
            'if [ "$(/usr/bin/stat -f %d,%i "$APP" '
            '2>/dev/null || true)" != "$APPID" ]; then return 0; fi')
        self.assertEqual(command.count(relaunch_guard), 1,
                         "relaunch is not bound to the handed-off APPID")
        self.assertLess(command.index(relaunch_guard),
                        command.index('$LAUNCH "$RESTORED"'))

        result = subprocess.run(
            ["/bin/sh", "-c", command], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=self.helper_env(), timeout=20,
            check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((installed / "old-marker").is_file(),
                        "the old app was not left at the installed path")
        self.assertFalse((installed / "new-marker").exists())
        self.assertEqual(
            (REAL_LSTAT(installed).st_dev, REAL_LSTAT(installed).st_ino),
            old_identity,
            "exchange failure did not preserve the exact old installed app")
        self.assertFalse(backup.exists(),
                         "exchange failure left a reserved backup directory")
        self.assertEqual(list(self.td.glob(".claudepet-old-*")), [],
                         "exchange failure retained a backup copy or residue")

    def test_preexisting_backup_name_is_never_changed_or_deleted(self):
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        work = self.td / "work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        random_bytes = b"\xdd" * 4
        backup = self.td / (".claudepet-old-%d-%s" %
                            (os.getpid(), random_bytes.hex()))
        backup.mkdir()
        sentinel = backup / "preexisting-backup-sentinel"
        original = b"must not be treated as updater-owned backup\n"
        sentinel.write_bytes(original)
        inode = sentinel.stat().st_ino
        with mock.patch.object(claude_pet.os, "urandom",
                               return_value=random_bytes):
            command = fast_replace_script(installed, newapp, work)
        subprocess.run(["/bin/sh", "-c", command],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       env=self.helper_env(), timeout=15, check=False)
        refused = ((installed / "old-marker").is_file() and
                   not (installed / "new-marker").exists())
        self.assertTrue(refused,
                        "a preexisting backup collision did not fail closed")
        self.assertEqual(self.path_bytes_and_inode(sentinel), (original, inode))

    def test_lock_residue_is_under_complete_uninstall_owned_root(self):
        app = self.td / "Applications Space" / "ClaudePet.app"
        app.parent.mkdir()
        fd = claude_pet._acquire_update_lock(str(app))
        self.assertIsNotNone(fd)
        os.close(fd)
        lock_path = os.path.abspath(claude_pet._update_lock_path(str(app)))
        self.assertEqual(os.path.dirname(lock_path), str(self.lock_root))
        owned_roots = [os.path.abspath(os.path.expanduser(p))
                       for p in claude_pet.UNINSTALL_PATHS]
        production_root = os.path.abspath(os.path.expanduser(
            REAL_UPDATE_LOCK_DIR))
        self.assertTrue(
            any(production_root == root or
                production_root.startswith(root + os.sep)
                for root in owned_roots),
            "stable update lock is outside every complete-uninstall root")


class ArchitectureBindingTests(RealpathTempCase):
    def test_universal_named_arm_only_bundle_is_rejected_via_lipo(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        lipo_calls = []

        def retrieve(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/lipo":
                lipo_calls.append(argv)
                return subprocess.CompletedProcess(
                    argv, 0, stdout="arm64\n", stderr="")
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                shutil.copytree(argv[1], argv[2], symlinks=True,
                                dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        choice = {"asset": "claudepet-universal.zip", "arch": "x86_64",
                  "url": "https://example.invalid/ClaudePet-universal.zip",
                  "tag": "99.0"}
        with mock.patch.dict(claude_pet._upd_cache, {"choice": choice},
                             clear=False), \
             mock.patch("platform.machine", return_value="x86_64"), \
             mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=retrieve), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "_signature_is_ours",
                               return_value=True), \
             mock.patch.object(claude_pet, "_signed_by_us", return_value=True), \
             mock.patch.object(claude_pet, "_ticket_is_stapled",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                choice["url"], app_path=str(installed),
                expect_version=choice["tag"])

        self.assertTrue(lipo_calls,
                        "the selected asset/architecture was never bound to "
                        "the Mach-O contents with lipo")
        self.assertFalse(result,
                         "an arm64-only bundle passed as a universal asset")
        self.assertFalse(popen.called)


class CriticalMemberTypeTests(RealpathTempCase):
    def _accepting_signatures(self):
        stack = ExitStack()
        stack.enter_context(mock.patch.object(
            claude_pet, "_signature_is_ours", return_value=True))
        stack.enter_context(mock.patch.object(
            claude_pet, "_signed_by_us", return_value=True))
        stack.enter_context(mock.patch.object(
            claude_pet, "_ticket_is_stapled", return_value=True))
        return stack

    def test_info_plist_must_be_a_regular_non_symlink(self):
        app = make_app(self.td / "plist-link" / "ClaudePet.app", "marker")
        plist = app / "Contents" / "Info.plist"
        real = plist.with_name("Info.real.plist")
        plist.rename(real)
        os.symlink(real.name, plist)       # contained link: containment alone accepts it

        with self._accepting_signatures():
            accepted = claude_pet.validate_update_app(app, "99.0")
        self.assertFalse(accepted,
                         "a symlinked Info.plist was followed and accepted")

    def test_main_executable_must_be_a_regular_non_symlink(self):
        app = make_app(self.td / "exec-link" / "ClaudePet.app", "marker")
        executable = app / "Contents" / "MacOS" / "ClaudePet"
        real = executable.with_name("ClaudePet.real")
        executable.rename(real)
        os.symlink(real.name, executable)

        with self._accepting_signatures():
            accepted = claude_pet.validate_update_app(app, "99.0")
        self.assertFalse(accepted,
                         "a symlinked CFBundleExecutable was accepted")

    def test_main_executable_directory_is_not_a_regular_file(self):
        app = make_app(self.td / "exec-dir" / "ClaudePet.app", "marker",
                       executable_kind="directory")
        with self._accepting_signatures():
            accepted = claude_pet.validate_update_app(app, "99.0")
        self.assertFalse(accepted,
                         "a directory at CFBundleExecutable was accepted")

    def test_nonexecutable_regular_macho_helper_is_rejected_before_popen(self):
        installed = make_app(self.td / "ClaudePet.app", "old-marker",
                             version="0.19")
        staged_helpers = []
        validation_modes = []
        real_validate = claude_pet.validate_update_app

        def download(_url, destination):
            Path(destination).write_bytes(b"synthetic archive")

        def fake_run(argv, *args, **kwargs):
            argv = [str(x) for x in argv]
            if len(argv) >= 5 and argv[:3] == ["/usr/bin/ditto", "-x", "-k"]:
                make_app(Path(argv[4]) / "ClaudePet.app", "new-marker")
                return subprocess.CompletedProcess(argv, 0)
            if argv and argv[0] == "/usr/bin/ditto" and len(argv) == 3:
                source, stage = Path(argv[1]), Path(argv[2])
                shutil.copytree(source, stage, symlinks=True,
                                dirs_exist_ok=True)
                helper = stage / "Contents" / "MacOS" / "python"
                self.assertTrue(stat.S_ISREG(os.lstat(helper).st_mode))
                arches = claude_pet._macho_arches(str(helper))
                self.assertTrue(arches,
                                "fixture helper is not a regular Mach-O")
                helper.chmod(0o644)
                staged_helpers.append(helper)
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        def validate(path, *args, **kwargs):
            helper = Path(path) / "Contents" / "MacOS" / "python"
            validation_modes.append((Path(path), os.lstat(helper).st_mode))
            return real_validate(path, *args, **kwargs)

        with mock.patch.object(claude_pet.tempfile, "mkdtemp",
                               side_effect=self.temporary_update_dir), \
             mock.patch.object(claude_pet, "_download_update_zip",
                               side_effect=download), \
             mock.patch.object(claude_pet, "_zip_members_are_safe",
                               return_value=True), \
             mock.patch.object(claude_pet.subprocess, "run",
                               side_effect=fake_run), \
             mock.patch.object(claude_pet, "_has_required_arches",
                               return_value=True), \
             self._accepting_signatures(), \
             mock.patch.object(claude_pet, "validate_update_app",
                               side_effect=validate), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen:
            result = claude_pet.install_github_update(
                "https://example.invalid/ClaudePet.zip",
                app_path=str(installed), expect_version="99.0",
                expect_arches=("arm64",))

        self.assertTrue(staged_helpers,
                        "install never constructed the staged helper fixture")
        self.assertGreaterEqual(len(validation_modes), 2,
                                "the staged bundle was not validated")
        self.assertFalse(
            validation_modes[-1][1]
            & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
            "the staged helper unexpectedly retained an execute bit")
        self.assertFalse(result,
                         "a non-executable exchange helper was accepted")
        popen.assert_not_called()


class AtomicExchangeRecoveryTests(RealpathTempCase):
    def test_atomic_branch_never_moves_old_stage_to_a_backup_name(self):
        installed = make_process_app(
            self.td / "ClaudePet.app", "old-marker")
        work = self.td / "work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        command = fast_replace_script(installed, newapp, work)
        self.assertNotIn(
            'mv "$STAGE" "$BACKUP"', command,
            "the atomic exchange has a second fallible move of the sole old copy")

    def test_fault_immediately_after_exchange_restores_or_retains_old_app(self):
        installed = make_process_app(self.td / "ClaudePet.app", "old-marker")
        work = self.td / "work"
        newapp = make_process_app(work / "ClaudePet.app", "new-marker")
        command = fast_replace_script(installed, newapp, work)
        needle = 'fi\nBEFORE="$SELFPID'
        self.assertIn(needle, command,
                      "cannot inject the post-exchange failure boundary")
        command = command.replace(needle, 'fi\nfalse\nBEFORE="$SELFPID', 1)

        result = subprocess.run(["/bin/sh", "-c", command],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                env=self.helper_env(), timeout=20,
                                check=False)
        retained = [p for p in self.td.glob(".claudepet-*")
                    if (p / "old-marker").is_file()]
        self.assertNotEqual(result.returncode, 0,
                            "the injected post-exchange fault was not reached")
        self.assertTrue(
            (installed / "old-marker").is_file() or retained,
            "the atomic exchange fault destroyed the only recoverable old app")


if __name__ == "__main__":
    unittest.main()
