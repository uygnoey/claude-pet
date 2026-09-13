"""Gating tests for Track B — "Start at sign-in" on macOS (v0.25 follow-ups).

Verifier: verifier-b (Claude), Track B of docs-design/followups-v025-plan-20260913.md
and the survey report key "autostart" (session scratchpad, followups-survey.json).
Evidence record with the RED run verbatim: docs-design/track-b-verification-20260913.md.
The Developer lands production code until this module is GREEN and does not touch its
assertions or fixtures (AGENTS.md §2 Condition A).

Surface pinned here — module-level names the Developer provides in claude_pet.py:

  autostart_state(status, is_bundle) -> "on" | "off" | "approval" | "unavailable"
      SMAppService status ints: 0 NotRegistered, 1 Enabled, 2 RequiresApproval,
      3 NotFound.  For a bundle, 0 and 3 are both "off".  Hardware evidence
      (Coordinator, 2026-09-13, macOS 26 / Darwin 25.5, Developer-ID-signed bundle
      built by build_app.sh from 794c66f, probed from the bundle's own interpreter so
      NSBundle.mainBundle() was the app): a never-registered bundle reports 3,
      register from 3 returns (True, None) and the status then reads 1, unregister
      returns (True, None) and the status then reads 0.  So 3 is the fresh-install
      "off", not a fault — the `3 -> "unavailable"` mapping merged at 794c66f left
      every fresh install with a disabled item that could not be turned on.  Any
      other int (99, -1) -> "unavailable".  is_bundle False -> "unavailable"
      whatever the status.
  autostart_toggle(service, is_bundle) -> (new_state, error_key | None)
      Service reports off (status 0 or 3) -> service.registerAndReturnError_(None);
      on ->
      service.unregisterAndReturnError_(None).  The new state is read back from the
      service afterwards, so a register that lands on status 2 returns
      ("approval", None).  A call returning (False, err) leaves the state unchanged and
      returns (state, "autostart_fail").  From status 2 the toggle never unregisters and
      returns ("approval", None) — the handler then shows the approval alert.  Not a
      bundle: the service is not touched at all (no status() either) and the result is
      ("unavailable", None).  service None (macOS 12): ("unavailable", None).
  autostart_service() -> SMAppService.mainAppService(), or None when the
      ServiceManagement framework cannot be imported or has no SMAppService (macOS 12).
      Resolved at call time — the precedent is app_bundle_path()'s in-function
      `from Foundation import NSBundle` — and the only place mainAppService is called.
  uninstall_autostart(service) -> error_key | None
      Unregisters only when status is 1 or 2; None / 0 / 3 make no call and return
      None; (False, err) from unregister returns "autostart_fail".  do_uninstall()
      calls it after the update lock is held and before anything irreversible; a
      failure refuses the uninstall with nothing deleted and no helper spawned.  From
      source (no bundle) do_uninstall does not touch the service at all.
  TR keys, all four locales: menu_autostart, autostart_title, autostart_approval,
      autostart_open_settings, autostart_fail, autostart_unavailable.
  Menu: `t("menu_autostart")` sits between menu_roam and menu_reset_size in
      rightMouseDown_'s tuple list; its selector has a Handler method that goes through
      autostart_toggle; the Pets submenu insert index still follows Reset size.
  setup.py: "ServiceManagement" in the py2app `includes` list.

No config key.  The OS registration is the single source of truth: nothing is read
from or written to CONFIG_PATH, RUNTIME or SETTINGS_OWNED_KEYS for this feature.

Rivals (AGENTS.md §3) — each fixture's docstring carries the table that separates them:
  R1  non-zero status is "on"            R2  only 1 is "on", everything else "off"
  R3  is_bundle ignored                  R4  NotFound is "unavailable" (merged at 794c66f)
  R4b NotFound is "on"                   R15 unknown status falls through to "off"
  R5  state assumed after the call       R6  (False, err) swallowed
  R7  service touched from source        R8  persisted preference (config / RUNTIME)
  R9  inline / launch-time registration  R10 unconditional unregister on uninstall
  R11 unregister before the lock or after Popen, or a failure that still deletes
  R12 English pasted into ko/ja/es       R13 menu item without a handler
  R14 ServiceManagement missing from setup.py

Isolation: HOME, TMPDIR, CONFIG_PATH and UPDATE_LOCK_DIR point into a temp directory for
the whole module.  sys.modules["ServiceManagement"] is replaced by a tripwire whose
register / unregister raise, so no test can reach the real login-item registry even
through an unexpected code path.  The real ~/.claude_pet.json is stat'ed (never read)
at import and at teardown.  Nothing here runs the GUI.
"""
from __future__ import annotations

import ast
import copy
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import claude_pet

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "claude_pet.py"
SETUP_PY = REPO / "setup.py"

REAL_CONFIG = os.path.expanduser("~/.claude_pet.json")
REAL_ACQUIRE = claude_pet._acquire_update_lock
REAL_DISCARD = claude_pet._discard_owned_path

SM_NOT_REGISTERED, SM_ENABLED, SM_REQUIRES_APPROVAL, SM_NOT_FOUND = 0, 1, 2, 3

TR_KEYS = ("menu_autostart", "autostart_title", "autostart_approval",
           "autostart_open_settings", "autostart_fail", "autostart_unavailable")
MESSAGE_KEYS = TR_KEYS[2:]          # the four that must differ from each other
MENU_TITLE_MAX = 24
CONFIG_BYTES = b'{"roam": true}\n'


def _stat_fingerprint(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns, st.st_ino)


# ─────────────────────────── fakes ───────────────────────────

class FakeError:
    """The `err` half of PyObjC's (ok, err): enough NSError surface to be printed."""

    def __init__(self, text="synthetic SMAppService failure"):
        self._text = text

    def localizedDescription(self):
        return self._text

    def code(self):
        return 1

    def domain(self):
        return "test.claudepet.autostart"

    def __str__(self):
        return self._text

    __repr__ = __str__


class FakeService:
    """Stands in for SMAppService.mainAppService().

    `status()` returns the current int.  register / unregister append to `calls`,
    demand the PyObjC out-param spelling (`None`), return the `(ok, err)` pair PyObjC
    returns for that spelling, and move the status the way the OS does: a register
    from 0 or 3 lands on `after_register` (1, or 2 to model RequiresApproval); a
    register while already at 2 stays at 2 (re-registering does not approve
    anything); an unregister lands on 0.  The 3 -> 1 (register) and 1 -> 0
    (unregister) transitions are the two observed on hardware (2026-09-13, see the
    module docstring); the rest model the framework's documented semantics.
    Unregistering something that is not registered (0 or 3) fails, as the OS does,
    so an unconditional unregister (R10) is visible both as an extra call and as an
    error — 3 stays in that set on purpose: it is "never registered", which is the
    same thing as 0 for both calls, and the toggle from 3 must register, never
    unregister.
    """

    def __init__(self, status, register_ok=True, unregister_ok=True,
                 after_register=SM_ENABLED, calls=None):
        self._status = status
        self.register_ok = register_ok
        self.unregister_ok = unregister_ok
        self.after_register = after_register
        self.calls = calls if calls is not None else []

    def status(self):
        self.calls.append("status")
        return self._status

    def registerAndReturnError_(self, err):
        self.calls.append("register")
        if err is not None:
            raise AssertionError("PyObjC out-parameter must be passed as None")
        if not self.register_ok:
            return (False, FakeError())
        if self._status != SM_REQUIRES_APPROVAL:
            self._status = self.after_register
        return (True, None)

    def unregisterAndReturnError_(self, err):
        self.calls.append("unregister")
        if err is not None:
            raise AssertionError("PyObjC out-parameter must be passed as None")
        if not self.unregister_ok or self._status in (SM_NOT_REGISTERED, SM_NOT_FOUND):
            return (False, FakeError())
        self._status = SM_NOT_REGISTERED
        return (True, None)

    def method_calls(self):
        """Calls that change anything — `status` reads are not counted here."""
        return [c for c in self.calls if c != "status"]


class RaisingStatusService(FakeService):
    """A service whose status() raises — the framework misbehaving, not a status."""

    def status(self):
        self.calls.append("status")
        raise RuntimeError("synthetic SMAppService.status() failure")


class TripwireService:
    """What sys.modules serves as the 'real' service while this module runs."""

    def status(self):
        return SM_NOT_FOUND

    def registerAndReturnError_(self, err):
        raise AssertionError("a test reached SMAppService.register on the real path")

    def unregisterAndReturnError_(self, err):
        raise AssertionError("a test reached SMAppService.unregister on the real path")


class TripwireSMAppService:
    @classmethod
    def mainAppService(cls):
        return TripwireService()

    @classmethod
    def openSystemSettingsLoginItems(cls):
        raise AssertionError("a test tried to open System Settings")


def _fake_framework(sm_class=TripwireSMAppService):
    mod = types.ModuleType("ServiceManagement")
    if sm_class is not None:
        mod.SMAppService = sm_class
    mod.SMAppServiceStatusNotRegistered = SM_NOT_REGISTERED
    mod.SMAppServiceStatusEnabled = SM_ENABLED
    mod.SMAppServiceStatusRequiresApproval = SM_REQUIRES_APPROVAL
    mod.SMAppServiceStatusNotFound = SM_NOT_FOUND
    return mod


# ───────────────────────── isolation ─────────────────────────

_ISOLATION = {}


def setUpModule():
    root = tempfile.mkdtemp(prefix="claudepet-autostart-isolation-")
    root = os.path.realpath(root)
    home = os.path.join(root, "home")
    tmp = os.path.join(root, "tmp")
    os.makedirs(home)
    os.makedirs(tmp)
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = tmp
    env = mock.patch.dict(os.environ, {"HOME": home, "TMPDIR": tmp + os.sep})
    config = mock.patch.object(claude_pet, "CONFIG_PATH",
                               os.path.join(home, ".claude_pet.json"))
    lock = mock.patch.object(claude_pet, "UPDATE_LOCK_DIR",
                             os.path.join(root, "cache"))
    framework = mock.patch.dict(sys.modules,
                                {"ServiceManagement": _fake_framework()})
    patches = [env, config, lock, framework]
    # A Developer who bound the class at import time would bypass sys.modules; cover
    # that spelling too, without asserting it exists.
    if hasattr(claude_pet, "SMAppService"):
        patches.append(mock.patch.object(claude_pet, "SMAppService",
                                         TripwireSMAppService))
    for p in patches:
        p.start()
    _ISOLATION.update(root=root, home=home, tmp=tmp, old_tempdir=old_tempdir,
                      patches=patches,
                      config_baseline=_stat_fingerprint(REAL_CONFIG))


def tearDownModule():
    for p in reversed(_ISOLATION["patches"]):
        p.stop()
    tempfile.tempdir = _ISOLATION["old_tempdir"]
    shutil.rmtree(_ISOLATION["root"], ignore_errors=True)
    before = _ISOLATION["config_baseline"]
    after = _stat_fingerprint(REAL_CONFIG)
    if (before is None) != (after is None):
        raise AssertionError(
            f"a test created or deleted the real {REAL_CONFIG}: {before!r} -> {after!r}")
    if before != after:
        # A running pet rewrites its config on a drag or a menu toggle, so a changed
        # stat during a long run is not proof of a leak here — but it must be looked
        # at, and it must not pass silently.
        sys.stderr.write(
            f"\n[test_autostart] WARNING: the real {REAL_CONFIG} changed during this "
            f"run ({before!r} -> {after!r}); check that no test wrote it.\n")


def _require(test, *names):
    missing = [n for n in names if not hasattr(claude_pet, n)]
    if missing:
        test.fail("claude_pet does not define: " + ", ".join(missing))
    got = [getattr(claude_pet, n) for n in names]
    return got[0] if len(got) == 1 else got


class ConfigGuard:
    """Everything a persisted-preference rival (R8) could write, snapshotted.

    The temp CONFIG_PATH gets known bytes, RUNTIME is deep-copied, and the two
    config writers are replaced by recorders.  `check()` asserts the bytes, the
    RUNTIME contents and the recorders are all as they were.
    """

    def __init__(self, test):
        self.test = test
        self.path = Path(claude_pet.CONFIG_PATH)
        self.path.write_bytes(CONFIG_BYTES)
        self.runtime = copy.deepcopy(claude_pet.RUNTIME)
        self.merge = mock.patch.object(claude_pet, "merge_config_updates")
        self.save = mock.patch.object(claude_pet, "save_config")
        self.merge_mock = self.merge.start()
        self.save_mock = self.save.start()
        test.addCleanup(self.merge.stop)
        test.addCleanup(self.save.stop)

    def check(self):
        self.test.assertEqual(
            (self.path.read_bytes(), claude_pet.RUNTIME,
             self.merge_mock.call_count, self.save_mock.call_count),
            (CONFIG_BYTES, self.runtime, 0, 0),
            "(config bytes, RUNTIME, merge_config_updates calls, save_config calls) "
            "— the toggle must persist nothing (R8)")


# ─────────────────────── autostart_state ───────────────────────

STATE_TABLE = (
    ((SM_NOT_REGISTERED, True), "off"),
    ((SM_ENABLED, True), "on"),
    ((SM_REQUIRES_APPROVAL, True), "approval"),
    ((SM_NOT_FOUND, True), "off"),
    ((99, True), "unavailable"),
    ((-1, True), "unavailable"),
    ((SM_NOT_REGISTERED, False), "unavailable"),
    ((SM_ENABLED, False), "unavailable"),
    ((SM_REQUIRES_APPROVAL, False), "unavailable"),
    ((SM_NOT_FOUND, False), "unavailable"),
)


class AutostartStateTests(unittest.TestCase):
    def test_status_and_bundle_table(self):
        """The whole table at once, so the diff shows every wrong cell.

        (3, True) -> "off" is the hardware-derived cell (module docstring): a
        never-registered bundle reports 3 and register from 3 succeeds, so the menu
        must show it unchecked and enabled.  The two unknown-int rows exist for R15:
        a bare else-branch that sends everything not 1/2 to "off" is the easiest way
        to write the fix and would offer "register" for a status nobody understands.

        | (status, is_bundle) | expected    | R1 non-zero=on | R2 1=on else off | R3 ignore bundle | R4 3=unavailable | R4b 3=on      | R15 else=off |
        | (0, True)           | off         | off            | off              | off              | off              | off           | off          |
        | (1, True)           | on          | on             | on               | on               | on               | on            | on           |
        | (2, True)           | approval    | on ✗           | off ✗            | approval         | approval         | approval      | approval     |
        | (3, True)           | off         | on ✗           | off              | off              | unavailable ✗    | on ✗          | off          |
        | (99, True)          | unavailable | on ✗           | off ✗            | unavailable      | unavailable      | unavailable   | off ✗        |
        | (-1, True)          | unavailable | on ✗           | off ✗            | unavailable      | unavailable      | unavailable   | off ✗        |
        | (0, False)          | unavailable | off ✗          | off ✗            | off ✗            | unavailable      | unavailable   | unavailable  |
        | (1, False)          | unavailable | on ✗           | on ✗             | on ✗             | unavailable      | unavailable   | unavailable  |
        | (2, False)          | unavailable | on ✗           | off ✗            | approval ✗       | unavailable      | unavailable   | unavailable  |
        | (3, False)          | unavailable | on ✗           | off ✗            | off ✗            | unavailable      | unavailable   | unavailable  |

        Every rival column differs from `expected` in at least one row.  R2 now
        ties on (3, True) and is separated by (2, True) and the unknown rows; R4 —
        the mapping merged at 794c66f — is separated only by (3, True), which is
        the row this fix is about.
        """
        fn = _require(self, "autostart_state")
        got = {args: fn(*args) for args, _ in STATE_TABLE}
        self.assertEqual(got, dict(STATE_TABLE))

    def test_persisted_preference_does_not_influence_state(self):
        """OS is the source of truth (design X); a stored preference is not (R8).

        Both places a preference could live are seeded: the (temp) config file and
        RUNTIME.  Two rows, because each R8 variant ties on one of them alone:

        | fixture                                  | expected | R8 config wins | R8 OR | R8 AND |
        | status 0, config/RUNTIME autostart True  | off      | on ✗           | on ✗  | off    |
        | status 1, config/RUNTIME autostart False | on       | off ✗          | on    | off ✗  |
        """
        fn = _require(self, "autostart_state")
        cfg = Path(claude_pet.CONFIG_PATH)
        results = []
        for status, stored in ((SM_NOT_REGISTERED, True), (SM_ENABLED, False)):
            cfg.write_text('{"autostart": %s}\n' % ("true" if stored else "false"),
                           encoding="utf-8")
            with mock.patch.dict(claude_pet.RUNTIME, {"autostart": stored}):
                results.append(fn(status, True))
        self.assertEqual(results, ["off", "on"])

    def test_no_config_key_exists_for_the_feature(self):
        """Nothing in the settings contract or apply_config carries "autostart".

        Rival: adding the key to SETTINGS_OWNED_KEYS or to apply_config's copy list —
        the Design-Y shape the plan rejects.  `L` is restored because apply_config
        re-derives the language as a side effect.
        """
        self.assertNotIn("autostart", claude_pet.SETTINGS_OWNED_KEYS)
        with mock.patch.dict(claude_pet.RUNTIME), mock.patch.dict(claude_pet.L):
            claude_pet.apply_config({"autostart": True, "roam": True})
            self.assertNotIn("autostart", claude_pet.RUNTIME)


# ─────────────────────── autostart_read_state ───────────────────────

class AutostartReadStateTests(unittest.TestCase):
    def test_read_state_table(self):
        """autostart_read_state(service, is_bundle) — the value the menu hook shows.

        autostart_state is pure over an int; this is the function the right-click
        menu reaches through state["autostart_read"], so the fresh-install claim
        ("unchecked and enabled") is pinned where the menu reads it.  The other
        three rows are the "unavailable" cases the fix must leave alone.

        | fixture                    | expected    | calls    | R4 3=unavailable | rival: status() error propagates | R7 no bundle gate |
        | status 3, bundle           | off         | [status] | unavailable ✗    | off                              | off               |
        | status() raises, bundle    | unavailable | [status] | unavailable      | RuntimeError ✗                   | unavailable       |
        | status 3, not a bundle     | unavailable | []       | unavailable      | unavailable                      | off ✗ / [status] ✗|
        | service None, bundle       | unavailable | —        | unavailable      | unavailable                      | AttributeError ✗  |
        """
        fn = _require(self, "autostart_read_state")
        rows = (
            (FakeService(SM_NOT_FOUND), True, "off", ["status"]),
            (RaisingStatusService(SM_NOT_FOUND), True, "unavailable", ["status"]),
            (FakeService(SM_NOT_FOUND), False, "unavailable", []),
            (None, True, "unavailable", None),
        )
        got = [(fn(svc, bundle), svc.calls if svc is not None else None)
               for svc, bundle, _, _ in rows]
        want = [(state, calls) for _, _, state, calls in rows]
        self.assertEqual(got, want)


# ─────────────────────── autostart_toggle ───────────────────────

class AutostartToggleTests(unittest.TestCase):
    """autostart_toggle(service, is_bundle) -> (new_state, error_key | None).

    Truth table (calls exclude `status` reads; "—" means the row is not reached):

    | fixture (status, bundle, call, after) | expected                 | calls        | R1 non-zero=on | R5 assumed  | R6 swallowed | R7 no gate  |
    | (0, T, register ok, 1)                | ("on", None)             | [register]   | same           | same        | same         | same        |
    | (3, T, register ok, 1)                | ("on", None)             | [register]   | see below ✗    | same        | same         | same        |
    | (1, T, unregister ok, 0)              | ("off", None)            | [unregister] | same           | same        | same         | same        |
    | (0, T, register ok, 2)                | ("approval", None)       | [register]   | ("on") ✗       | ("on") ✗    | same         | same        |
    | (2, T)                                | ("approval", None)       | no unregister| [unregister] ✗ | —           | —            | —           |
    | (0, T, register (False, err))         | ("off", "autostart_fail")| [register]   | —              | ("on") ✗    | ("off", None)✗| —          |
    | (1, T, unregister (False, err))       | ("on", "autostart_fail") | [unregister] | —              | ("off") ✗   | ("on", None) ✗| —          |
    | (1, F)                                | ("unavailable", None)    | []           | —              | —           | —            | [unregister]✗|
    | (None service, T)                     | ("unavailable", None)    | —            | —              | —           | —            | AttributeError ✗ |

    The (3, T) row is the fresh-install click (hardware: status 3 before any
    registration, 1 after register).  It separates the two NotFound rivals by the
    call list as well as by the result: R4 (3 = "unavailable", merged at 794c66f)
    returns ("unavailable", None) with no call at all — the item cannot be turned
    on; R1 / R4b (3 = "on") call unregister, which the fake refuses from 3, giving
    ("on", "autostart_fail") and [unregister].

    Every row also runs under ConfigGuard: config bytes, RUNTIME and the two config
    writers must be untouched (R8).
    """

    def setUp(self):
        self.guard = ConfigGuard(self)

    def toggle(self, service, is_bundle=True):
        fn = _require(self, "autostart_toggle")
        return fn(service, is_bundle)

    def test_off_registers_and_reads_the_new_state_back(self):
        svc = FakeService(SM_NOT_REGISTERED)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("on", None), ["register"]))
        self.guard.check()

    def test_never_registered_bundle_registers_from_not_found(self):
        """Status 3 is where every fresh install starts; the click must register."""
        svc = FakeService(SM_NOT_FOUND)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("on", None), ["register"]))
        self.guard.check()

    def test_on_unregisters(self):
        svc = FakeService(SM_ENABLED)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("off", None), ["unregister"]))
        self.guard.check()

    def test_register_that_lands_on_requires_approval_reports_approval(self):
        svc = FakeService(SM_NOT_REGISTERED, after_register=SM_REQUIRES_APPROVAL)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("approval", None), ["register"]))
        self.guard.check()

    def test_from_requires_approval_never_unregisters(self):
        svc = FakeService(SM_REQUIRES_APPROVAL)
        result = self.toggle(svc)
        self.assertEqual((result, "unregister" in svc.calls),
                         (("approval", None), False))
        self.guard.check()

    def test_register_failure_is_reported_not_swallowed(self):
        svc = FakeService(SM_NOT_REGISTERED, register_ok=False)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("off", "autostart_fail"), ["register"]))
        self.guard.check()

    def test_unregister_failure_is_reported_not_swallowed(self):
        svc = FakeService(SM_ENABLED, unregister_ok=False)
        self.assertEqual((self.toggle(svc), svc.method_calls()),
                         (("on", "autostart_fail"), ["unregister"]))
        self.guard.check()

    def test_source_run_never_touches_the_service(self):
        svc = FakeService(SM_ENABLED)
        self.assertEqual((self.toggle(svc, is_bundle=False), svc.calls),
                         (("unavailable", None), []))
        self.guard.check()

    def test_missing_framework_is_unavailable_without_error(self):
        self.assertEqual(self.toggle(None, is_bundle=True), ("unavailable", None))
        self.guard.check()


# ─────────────────────── autostart_service ───────────────────────

class AutostartServiceTests(unittest.TestCase):
    """autostart_service() resolves the framework at call time.

    | sys.modules["ServiceManagement"]      | expected            | rival: import error propagates | rival: returns the class |
    | None (import fails)                   | None                | ImportError ✗                  | —                        |
    | module without SMAppService (macOS 12)| None                | AttributeError ✗               | —                        |
    | module whose mainAppService -> obj    | that obj (identity) | obj                            | the class ✗              |
    """

    def test_missing_framework_yields_none(self):
        fn = _require(self, "autostart_service")
        with mock.patch.dict(sys.modules, {"ServiceManagement": None}):
            self.assertIsNone(fn())

    def test_framework_without_smappservice_yields_none(self):
        fn = _require(self, "autostart_service")
        with mock.patch.dict(sys.modules,
                             {"ServiceManagement": _fake_framework(sm_class=None)}):
            self.assertIsNone(fn())

    def test_returns_the_main_app_service_object(self):
        fn = _require(self, "autostart_service")
        sentinel = FakeService(SM_NOT_REGISTERED)

        class SM:
            @classmethod
            def mainAppService(cls):
                return sentinel

        with mock.patch.dict(sys.modules,
                             {"ServiceManagement": _fake_framework(sm_class=SM)}):
            self.assertIs(fn(), sentinel)


# ─────────────────────── uninstall ───────────────────────

class UninstallAutostartHelperTests(unittest.TestCase):
    def test_helper_table(self):
        """uninstall_autostart(service) -> error_key | None.

        | service                 | expected         | calls        | R10 unconditional          | R6 swallowed |
        | None                    | None             | —            | AttributeError ✗           | —            |
        | status 0                | None             | []           | [unregister] -> fail ✗     | —            |
        | status 3                | None             | []           | [unregister] -> fail ✗     | —            |
        | status 1, ok            | None             | [unregister] | same                       | same         |
        | status 2, ok            | None             | [unregister] | same                       | same         |
        | status 1, (False, err)  | "autostart_fail" | [unregister] | same                       | None ✗       |

        The 0 / 3 rows carry the user-visible stake: an app whose sign-in item was
        never enabled must still uninstall cleanly.  The fake's unregister fails from
        0 / 3 as the OS does, so R10 shows up as an error and not only as a call.
        """
        fn = _require(self, "uninstall_autostart")
        rows = (
            (None, None, []),
            (FakeService(SM_NOT_REGISTERED), None, []),
            (FakeService(SM_NOT_FOUND), None, []),
            (FakeService(SM_ENABLED), None, ["unregister"]),
            (FakeService(SM_REQUIRES_APPROVAL), None, ["unregister"]),
            (FakeService(SM_ENABLED, unregister_ok=False), "autostart_fail",
             ["unregister"]),
        )
        got = [(fn(svc), svc.method_calls() if svc is not None else None)
               for svc, _, _ in rows]
        want = [(err, calls if svc is not None else None) for svc, err, calls in rows]
        self.assertEqual(got, want)


class DoUninstallOrderingTests(unittest.TestCase):
    """do_uninstall() unregisters after the lock and before anything irreversible.

    Call-recording over the real do_uninstall with every external effect replaced:
    the lock is acquired for real under a temp UPDATE_LOCK_DIR, Popen is a recorder
    (nothing is spawned), _discard_owned_path records then runs for real on temp
    sentinels, app_bundle_path returns a temp bundle, autostart_service returns the
    fake.  The fake's `calls` list is the same list the recorders append to, so the
    event order is one sequence.

    | fixture                       | expected result           | event order / calls                    | R11 variants                                  |
    | status 1, unregister ok       | (True, None)              | lock < unregister < popen < discard    | unregister before lock; or after popen ✗      |
    | status 1, unregister fails    | (False, <non-empty str>)  | no popen, no discard, sentinel intact  | proceeds and deletes ✗ / (True, None) ✗       |
    | lock already held elsewhere   | (False, "update in progress") | no service call                    | unregister first ✗ ([unregister])             |
    | no bundle (source run)        | (False, None)             | no service call                        | R7: [status, unregister] ✗                    |
    """

    def setUp(self):
        self.td = Path(os.path.realpath(tempfile.mkdtemp(
            prefix="autostart-uninstall-", dir=_ISOLATION["tmp"])))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.lock_root = self.td / "owned-update-locks"
        self._patch(mock.patch.object(claude_pet, "UPDATE_LOCK_DIR",
                                      str(self.lock_root)))
        self.app = self.td / "ClaudePet.app"
        (self.app / "Contents" / "MacOS").mkdir(parents=True)
        self.sentinel = self.td / "settings-sentinel.json"
        self.sentinel.write_bytes(CONFIG_BYTES)
        self._patch(mock.patch.object(claude_pet, "UNINSTALL_PATHS",
                                      (str(self.sentinel), str(self.lock_root))))
        self.events = []

    def _patch(self, patcher):
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_uninstall(self, fake, bundle=True):
        _require(self, "autostart_service", "uninstall_autostart")

        def acquire(*a, **k):
            self.events.append("lock")
            return REAL_ACQUIRE(*a, **k)

        def popen(*a, **k):
            self.events.append("popen")
            return mock.MagicMock()

        def discard(path):
            self.events.append("discard")
            return REAL_DISCARD(path)

        with mock.patch.object(claude_pet, "_acquire_update_lock", side_effect=acquire), \
             mock.patch.object(claude_pet.subprocess, "Popen", side_effect=popen), \
             mock.patch.object(claude_pet, "_discard_owned_path", side_effect=discard), \
             mock.patch.object(claude_pet, "app_bundle_path",
                               return_value=str(self.app) if bundle else None), \
             mock.patch.object(claude_pet, "autostart_service", return_value=fake):
            return claude_pet.do_uninstall()

    def test_unregister_runs_after_the_lock_and_before_the_irreversible_section(self):
        fake = FakeService(SM_ENABLED, calls=self.events)
        result = self.run_uninstall(fake)
        order = [e for e in self.events if e != "status"]
        self.assertEqual(result, (True, None))
        self.assertEqual(order.count("unregister"), 1, order)
        self.assertEqual(
            [order.index("lock") < order.index("unregister"),
             order.index("unregister") < order.index("popen"),
             order.index("unregister") < order.index("discard")],
            [True, True, True],
            f"(lock<unregister, unregister<popen, unregister<discard) in {order}")

    def test_unregister_failure_refuses_with_nothing_deleted(self):
        fake = FakeService(SM_ENABLED, unregister_ok=False, calls=self.events)
        result = self.run_uninstall(fake)
        self.assertEqual(
            (result[0], isinstance(result[1], str) and bool(result[1]),
             "popen" in self.events, "discard" in self.events,
             self.sentinel.read_bytes() if self.sentinel.exists() else None,
             self.app.is_dir()),
            (False, True, False, False, CONFIG_BYTES, True),
            "(quitting, error is a non-empty string, helper spawned, discard ran, "
            "sentinel bytes, app still present)")

    def test_busy_lock_refuses_before_touching_the_service(self):
        held = REAL_ACQUIRE(str(self.app))
        self.assertIsNotNone(held, "control lock acquisition failed")
        self.addCleanup(os.close, held)
        fake = FakeService(SM_ENABLED, calls=self.events)
        result = self.run_uninstall(fake)
        self.assertEqual((result, [e for e in self.events if e in
                                   ("status", "register", "unregister")]),
                         ((False, "update in progress"), []))

    def test_source_run_uninstall_does_not_touch_the_service(self):
        fake = FakeService(SM_ENABLED, calls=self.events)
        result = self.run_uninstall(fake, bundle=False)
        self.assertEqual((result, [e for e in self.events if e in
                                   ("status", "register", "unregister")]),
                         ((False, None), []))


# ─────────────────────── localisation ───────────────────────

class AutostartLocalizationTests(unittest.TestCase):
    """TR blocks are inspected directly, not through t(), which falls back to English."""

    def test_every_locale_defines_every_key(self):
        missing = [(lang, key) for lang in claude_pet.SUPPORTED_LANGS
                   for key in TR_KEYS
                   if not isinstance(claude_pet.TR[lang].get(key), str)
                   or not claude_pet.TR[lang][key].strip()]
        self.assertEqual(missing, [])

    def test_each_key_is_translated_not_copied_across_locales(self):
        """R12: a string pasted into ko/ja/es unchanged would pass t()'s fallback.

        Per key the four locale strings must be pairwise distinct.
        """
        copied = []
        for key in TR_KEYS:
            values = [claude_pet.TR[lang].get(key) for lang in claude_pet.SUPPORTED_LANGS]
            if len(set(values)) != len(values):
                copied.append((key, values))
        self.assertEqual(copied, [])

    def test_message_keys_differ_within_each_locale(self):
        """approval / open_settings / fail / unavailable are four different messages.

        menu_autostart and autostart_title may legitimately coincide (the survey's
        suggested strings do), so they are not in this set.
        """
        dupes = []
        for lang in claude_pet.SUPPORTED_LANGS:
            values = [claude_pet.TR[lang].get(key) for key in MESSAGE_KEYS]
            if len(set(values)) != len(values):
                dupes.append((lang, values))
        self.assertEqual(dupes, [])

    def test_menu_title_fits_the_menu(self):
        """Present in every locale and at most MENU_TITLE_MAX characters.

        Presence is asserted here too: on a tree without the key an "only too-long
        titles fail" check passes vacuously, which §3 rules out.
        """
        bad = {lang: claude_pet.TR[lang].get("menu_autostart")
               for lang in claude_pet.SUPPORTED_LANGS
               if not isinstance(claude_pet.TR[lang].get("menu_autostart"), str)
               or not 0 < len(claude_pet.TR[lang]["menu_autostart"]) <= MENU_TITLE_MAX}
        self.assertEqual(bad, {}, f"menu_autostart missing or longer than {MENU_TITLE_MAX}")


# ─────────────────────── wiring (AST, no GUI) ───────────────────────

def _tree(path=SOURCE):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_def(tree, name, within=None):
    for node in ast.walk(tree):
        if within is None:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        elif isinstance(node, ast.ClassDef) and node.name == within:
            for sub in ast.walk(node):
                if isinstance(sub, ast.FunctionDef) and sub.name == name:
                    return sub
    return None


def _menu_tuple_items(fn):
    """[(tr_key | None, selector | None)] from `for title, action in ((...), ...)`."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple)
                and node.iter.elts
                and all(isinstance(e, ast.Tuple) and len(e.elts) == 2
                        for e in node.iter.elts)):
            items = []
            for pair in node.iter.elts:
                title, action = pair.elts
                key = None
                if (isinstance(title, ast.Call) and isinstance(title.func, ast.Name)
                        and title.func.id == "t" and title.args
                        and isinstance(title.args[0], ast.Constant)):
                    key = title.args[0].value
                selector = action.value if isinstance(action, ast.Constant) else None
                items.append((key, selector))
            return items
    return None


def _pet_insert_index(fn):
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "insertItem_atIndex_" and len(node.args) == 2
                and isinstance(node.args[0], ast.Name) and node.args[0].id == "pet_item"):
            idx = node.args[1]
            return idx.value if isinstance(idx, ast.Constant) else ast.dump(idx)
    return None


def _attribute_sites(tree, attrs):
    """{attr: {enclosing top-level def / class name, or "<module>"}}."""
    sites = {a: set() for a in attrs}
    for node in tree.body:
        owner = node.name if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else "<module>"
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr in sites:
                sites[sub.attr].add(owner)
    return sites


def _t_keys(tree):
    return {n.args[0].value for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "t" and n.args and isinstance(n.args[0], ast.Constant)}


def _names_loaded(fn):
    return {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}


def _setup_includes():
    for node in ast.walk(_tree(SETUP_PY)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "includes"
                        and isinstance(value, (ast.List, ast.Tuple))):
                    return [e.value for e in value.elts if isinstance(e, ast.Constant)]
    return None


class AutostartWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = _tree()

    def test_menu_item_follows_roam_and_precedes_reset_size(self):
        """Placement A: `t("menu_autostart")` directly after Roam, before Reset size.

        The Pets submenu is inserted by constant index "after Reset size"; adding a
        row above it without moving that constant puts Pets between the new item and
        Reset size, so the constant must equal index(menu_reset_size) + 1.
        """
        fn = _find_def(self.tree, "rightMouseDown_")
        self.assertIsNotNone(fn, "rightMouseDown_ not found")
        items = _menu_tuple_items(fn)
        self.assertIsNotNone(items, "menu tuple list not found in rightMouseDown_")
        keys = [k for k, _ in items]
        self.assertIn("menu_autostart", keys, keys)
        i = keys.index("menu_autostart")
        self.assertEqual(
            (keys[i - 1], keys[i + 1], _pet_insert_index(fn)),
            ("menu_roam", "menu_reset_size", keys.index("menu_reset_size") + 1),
            f"(before, after, pets insert index) with items {keys}")

    def test_menu_item_has_a_handler_that_uses_the_pure_toggle(self):
        """R13: an item whose selector no Handler method implements does nothing.

        The Handler method must reach autostart_toggle by name — the decision logic
        lives in the pure helper, not inline in the GUI.
        """
        fn = _find_def(self.tree, "rightMouseDown_")
        self.assertIsNotNone(fn, "rightMouseDown_ not found")
        items = dict(_menu_tuple_items(fn) or [])
        selector = items.get("menu_autostart")
        self.assertTrue(isinstance(selector, str) and selector.endswith(":"),
                        f"menu_autostart selector: {selector!r}")
        method = _find_def(self.tree, selector.replace(":", "_"), within="Handler")
        self.assertIsNotNone(method, f"Handler.{selector.replace(':', '_')} not defined")
        self.assertIn("autostart_toggle", _names_loaded(method))

    def test_registration_calls_live_only_in_the_pure_helpers(self):
        """R9: no register / unregister inside run_gui or do_uninstall, one service seam.

        `mainAppService` is called only in autostart_service, so patching that one
        name isolates every test from the OS.  do_uninstall reaches the service only
        through uninstall_autostart.  The approval alert can open Login Items.
        """
        sites = _attribute_sites(self.tree, (
            "mainAppService", "registerAndReturnError_",
            "unregisterAndReturnError_", "openSystemSettingsLoginItems"))
        do_uninstall = _find_def(self.tree, "do_uninstall")
        self.assertEqual(
            (sites["mainAppService"],
             bool(sites["registerAndReturnError_"]),
             sites["registerAndReturnError_"] & {"run_gui", "do_uninstall", "<module>"},
             bool(sites["unregisterAndReturnError_"]),
             sites["unregisterAndReturnError_"] & {"run_gui", "do_uninstall", "<module>"},
             bool(sites["openSystemSettingsLoginItems"]),
             "uninstall_autostart" in _names_loaded(do_uninstall)),
            ({"autostart_service"}, True, set(), True, set(), True, True),
            "(mainAppService sites, register called anywhere, register in GUI/uninstall, "
            "unregister called anywhere, unregister in GUI/uninstall, "
            "openSystemSettingsLoginItems referenced, do_uninstall uses "
            f"uninstall_autostart) — sites: {sites}")

    def test_every_new_key_is_used_through_t(self):
        used = _t_keys(self.tree)
        self.assertEqual([k for k in TR_KEYS if k not in used], [])

    def test_setup_py_bundles_servicemanagement(self):
        """R14: py2app only ships listed frameworks; without this the bundle's item is
        permanently 'unavailable' while the from-source run works."""
        self.assertIn("ServiceManagement", _setup_includes() or [])


if __name__ == "__main__":
    unittest.main()
