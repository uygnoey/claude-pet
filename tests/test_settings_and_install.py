import ast
import io
import json
import errno
import inspect
import os
import plistlib
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.error import URLError
from unittest import mock

import claude_pet


# ──────────────── isolation, and the two escapes that are not files ────────
#
# Three tests in this file drive `install_github_update` and two run the
# replacement script for real. Between them they reach four things outside
# any temp directory, and only one of the four is a path this file used to
# watch:
#
#  * the **network** — production downloads through
#    `_download_update_zip(url, dest)`, which calls `urlopen`. Fixtures here
#    patched `urllib.request.urlretrieve`, a name production no longer calls,
#    so the real download ran against the fixture's URL.
#  * the **update lock**, taken at a path under the real `~`.
#  * `$HOME/claudepet_debug.log`, which the script's `cleanup()` appends to.
#  * `/Applications`, whose *parent* is written to when a test passes
#    `/Applications/ClaudePet.app` as the install path — the staging directory
#    is claimed beside it.
#
# The redirections below are installed at module level so they cover every
# test in the file, including ones added later. `tearDownModule` then checks
# that the real paths are unchanged, that nothing tried to open a socket, and
# that no fixture bundle got itself registered with LaunchServices.

REAL_HOME = os.path.expanduser("~")
REAL_LOCK_DIR = os.path.expanduser(claude_pet.UPDATE_LOCK_DIR)
REAL_DEBUG_LOG = os.path.expanduser("~/claudepet_debug.log")
REAL_APPS_DIR = "/Applications"
BUNDLE_ID = "me.yeongyu.claudepet"
LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")

NETWORK_ATTEMPTS = []
_LOOPBACK = ("localhost", "127.0.0.1", "::1", "")
_AF_UNIX = getattr(socket, "AF_UNIX", None)
_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_CONNECT = socket.socket.connect


class NetworkReached(AssertionError):
    """Raised in place of a socket to anywhere but loopback."""


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    if str(host) in _LOOPBACK:
        return _REAL_GETADDRINFO(host, port, *args, **kwargs)
    NETWORK_ATTEMPTS.append(f"getaddrinfo({host!r}, {port!r})")
    raise NetworkReached(f"a test tried to resolve {host!r}")


def _guarded_connect(self, address, *args, **kwargs):
    local = (_AF_UNIX is not None and self.family == _AF_UNIX) or (
        isinstance(address, tuple) and str(address[0]) in _LOOPBACK)
    if local:
        return _REAL_CONNECT(self, address, *args, **kwargs)
    NETWORK_ATTEMPTS.append(f"connect({address!r})")
    raise NetworkReached(f"a test tried to connect to {address!r}")


def take_network_attempts():
    attempts = list(NETWORK_ATTEMPTS)
    del NETWORK_ATTEMPTS[:]
    return attempts


def patch_download(side_effect=None, **kwargs):
    """Stand in for the seam `install_github_update` downloads through.

    Same two positionals as `_download_update_zip(zip_url, dest)`, which is
    also the shape the retired `urlretrieve` fixtures were written against.
    """
    if side_effect is None and not kwargs:
        kwargs = {"return_value": 0}
    return mock.patch.object(claude_pet, "_download_update_zip",
                             side_effect=side_effect, **kwargs)


# The replacement script has one launch command and one relaunch command. Both
# go through its `LAUNCH=open` variable, and their deliberately different shell
# grammar is a contract: replacing one must not accidentally replace the other.
# Exact-count checks are load-bearing here. A stale literal used to leave the
# real `open` command live while the test believed it had installed a stub.

LAUNCH_LITERAL = '$LAUNCH "$APP"'
RELAUNCH_LITERAL = '( $LAUNCH "$RESTORED" )'


def replace_launch_points(command, launcher=":", relauncher="( : )"):
    for literal, stand_in in ((LAUNCH_LITERAL, launcher),
                              (RELAUNCH_LITERAL, relauncher)):
        found = command.count(literal)
        if found != 1:
            raise AssertionError(
                f"the replacement script contains {found} occurrences of "
                f"{literal!r}, expected exactly one; this substitution would "
                "not safely identify its launch point")
        command = command.replace(literal, stand_in, 1)
    live = [line for line in command.split("\n")
            if re.search(r'(?:^|[;&|(\s])(?:open|\$LAUNCH)\s+"\$', line)]
    if live:
        raise AssertionError(
            "a live launch remains in a script about to be run:\n  "
            + "\n  ".join(live))
    return command


def path_identity(path):
    """The dev,inode spelling required by `_update_replace_script`."""
    st = os.lstat(path)
    return f"{st.st_dev},{st.st_ino}"


def shell_assignment(command, name):
    """Decode one generated `NAME=<shell-quoted value>` assignment."""
    prefix = name + "="
    lines = [line for line in command.splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise AssertionError(
            f"expected one {name} assignment in generated script, found "
            f"{len(lines)}")
    word = shlex.split(lines[0])
    if len(word) != 1 or not word[0].startswith(prefix):
        raise AssertionError(f"could not decode generated assignment: {lines[0]!r}")
    return word[0].split("=", 1)[1]


def shorten_update_waits(command):
    """Keep failure-path updater tests fast, failing if a seam drifts."""
    substitutions = (
        ("sleep 1.5", ":"),
        (f"while [ $i -lt {claude_pet.UPDATE_ACK_POLLS} ]; do",
         "while [ $i -lt 1 ]; do"),
        (f"  sleep {'%g' % claude_pet.UPDATE_ACK_INTERVAL}", "  :"),
        (f"sleep {'%g' % claude_pet.UPDATE_ACK_SETTLE}", ":"),
    )
    for literal, stand_in in substitutions:
        found = command.count(literal)
        if found != 1:
            raise AssertionError(
                f"expected one updater wait seam {literal!r}, found {found}")
        command = command.replace(literal, stand_in, 1)
    return command


def lsregister_dump():
    if not os.path.exists(LSREGISTER):
        return None
    try:
        result = subprocess.run([LSREGISTER, "-dump"], capture_output=True,
                                text=True, errors="replace", timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout or None


def registrations_in(dump, bundle_id=None, under=None):
    """Paths of records in a dump, optionally filtered by identifier and root.

    Read-only throughout: `lsregister -dump` prints the database, and no
    mutating form of that tool is used anywhere in this suite. Records left by
    earlier runs are the user's to keep or clear.
    """
    root = os.path.realpath(under) + os.sep if under else None
    found = []
    for record in (dump or "").split("-" * 80):
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


def dir_fingerprint(path):
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
    return (st.st_mode & 0o170000, st.st_size, st.st_mtime_ns, st.st_ino)


def file_fingerprint(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


def staging_fingerprint():
    """Our own leftovers beside the installed app, ignoring everything else."""
    try:
        names = sorted(n for n in os.listdir(REAL_APPS_DIR)
                       if n.startswith(".claudepet-"))
    except OSError:
        return None
    return {n: _stat_tuple(os.path.join(REAL_APPS_DIR, n)) for n in names}


def real_home_violations():
    """How the watched real paths differ from what they were at import.

    "Unchanged", not "absent": `~/Library/Caches/me.yeongyu.claudepet/` and two
    `/Applications/.claudepet-*` leftovers already exist on this machine, from
    the incident these checks were written for. Requiring them to be gone would
    fail every test for a reason unrelated to the test — and removing them is
    not this suite's to do.
    """
    problems = []
    for label, now, before in (
            (REAL_LOCK_DIR, dir_fingerprint(REAL_LOCK_DIR),
             _ISOLATION.get("cache_baseline")),
            (REAL_DEBUG_LOG, file_fingerprint(REAL_DEBUG_LOG),
             _ISOLATION.get("log_baseline")),
            (f"{REAL_APPS_DIR}/.claudepet-*", staging_fingerprint(),
             _ISOLATION.get("staging_baseline"))):
        if now != before:
            problems.append(f"{label}: {before!r} -> {now!r}")
    return problems


_ISOLATION = {}


def setUpModule():
    root = tempfile.mkdtemp(prefix="claudepet-settings-isolation-", dir="/tmp")
    home = os.path.join(root, "home")
    tmp = os.path.join(root, "tmp")
    os.makedirs(home)
    os.makedirs(tmp)
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = tmp
    # Not created here: production creates it in `_acquire_update_lock`, and a
    # fixture that pre-creates it hides the case where it fails to.
    cache = os.path.join(root, "cache")
    env = mock.patch.dict(os.environ, {
        "HOME": home,
        "TMPDIR": tmp + os.sep,
        "ZDOTDIR": home,
        "ENV": os.path.join(home, ".no-such-rc"),
        "BASH_ENV": os.path.join(home, ".no-such-rc"),
        "CDPATH": "",
    })
    lock = mock.patch.object(claude_pet, "UPDATE_LOCK_DIR", cache)
    config = mock.patch.object(
        claude_pet, "CONFIG_PATH", os.path.join(home, ".claude_pet.json"))
    pet_home = mock.patch.object(
        claude_pet, "USER_PET_HOME", os.path.join(home, ".claude_pet"))
    pets = mock.patch.object(
        claude_pet, "USER_PETS_DIR", os.path.join(home, ".claude_pet", "pets"))
    logs = mock.patch.object(claude_pet, "LOG_DIRS", [
        os.path.join(home, ".claude", "projects"),
        os.path.join(home, ".config", "claude", "projects"),
    ])
    dns = mock.patch.object(socket, "getaddrinfo", _guarded_getaddrinfo)
    conn = mock.patch.object(socket.socket, "connect", _guarded_connect)
    for patch in (env, lock, config, pet_home, pets, logs, dns, conn):
        patch.start()
    del NETWORK_ATTEMPTS[:]
    _ISOLATION.update(
        root=root, home=home, tmp=tmp, cache=cache,
        old_tempdir=old_tempdir,
        patches=(conn, dns, logs, pets, pet_home, config, lock, env),
        cache_baseline=dir_fingerprint(REAL_LOCK_DIR),
        log_baseline=file_fingerprint(REAL_DEBUG_LOG),
        staging_baseline=staging_fingerprint())


def tearDownModule():
    registered = registrations_in(lsregister_dump(), BUNDLE_ID,
                                  _ISOLATION["root"])
    for patch in _ISOLATION["patches"]:
        patch.stop()
    tempfile.tempdir = _ISOLATION["old_tempdir"]
    shutil.rmtree(_ISOLATION["root"], ignore_errors=True)
    problems = real_home_violations()
    attempts = take_network_attempts()
    if problems:
        raise AssertionError(
            "tests in this module wrote outside their fixtures:\n  "
            + "\n  ".join(problems))
    if attempts:
        raise AssertionError(
            "tests in this module tried to use the network; the download seam "
            "is `claude_pet._download_update_zip`:\n  " + "\n  ".join(attempts))
    if registered:
        raise AssertionError(
            f"a fixture bundle was launched: LaunchServices now records "
            f"{BUNDLE_ID} at these temp paths, and keeps recording them after "
            f"the directories are gone:\n  " + "\n  ".join(registered))


class IsolationCheckedTest(unittest.TestCase):
    """Attributes a bypass to the test that caused it, not to the module."""

    def tearDown(self):
        super().tearDown()
        attempts = take_network_attempts()
        problems = real_home_violations()
        self.assertEqual(
            attempts, [],
            "this test tried to use the network; patch_download() is how to "
            "stand in for the download:\n  " + "\n  ".join(attempts))
        self.assertEqual(
            problems, [],
            "this test wrote outside its fixture:\n  " + "\n  ".join(problems))


LIMITS = {
    "session_limit": 12_345_678,
    "weekly_limit": 98_765_432,
    "opus_limit": 23_456_789,
}


def usage_stats(session=1_000_000, weekly=5_000_000, opus=2_000_000):
    return {
        "session": {"used": session},
        "weekly": {"used": weekly},
        "opus": {"used": opus},
    }


class SettingsConfigTests(unittest.TestCase):
    def prepare(self, direct=None, calibration=None, stats=None):
        base = {"mode": "sub", **LIMITS}
        before = dict(base)
        candidate, error = claude_pet.prepare_settings_config(
            base,
            direct
            or {"session": "12.345678", "weekly": "98.765432", "opus": "23.456789"},
            calibration or {"session": "", "weekly": "", "opus": ""},
            stats or usage_stats(),
        )
        self.assertEqual(base, before, "the validator must not mutate live config")
        return candidate, error

    def test_exact_token_limits_survive_an_unchanged_settings_round_trip(self):
        displayed = {
            gauge: claude_pet.fmt_limit_m(LIMITS[config_key])
            for gauge, config_key in claude_pet.GAUGE_LIMIT_KEYS
        }
        candidate, error = self.prepare(direct=displayed)
        self.assertIsNone(error)
        self.assertEqual(
            {key: candidate[key] for key in LIMITS},
            LIMITS,
        )

    def test_valid_direct_limits_are_stored_as_integer_tokens(self):
        candidate, error = self.prepare(
            direct={"session": "8.5", "weekly": "60", "opus": "15.000001"}
        )
        self.assertIsNone(error)
        self.assertEqual(candidate["session_limit"], 8_500_000)
        self.assertEqual(candidate["weekly_limit"], 60_000_000)
        self.assertEqual(candidate["opus_limit"], 15_000_001)

    def test_calibration_overrides_only_its_matching_direct_limit(self):
        candidate, error = self.prepare(
            direct={"session": "8", "weekly": "60", "opus": "15"},
            calibration={"session": "25", "weekly": "", "opus": "50"},
            stats=usage_stats(session=2_000_000, weekly=4_000_000, opus=3_000_000),
        )
        self.assertIsNone(error)
        self.assertEqual(candidate["session_limit"], 8_000_000)
        self.assertEqual(candidate["weekly_limit"], 60_000_000)
        self.assertEqual(candidate["opus_limit"], 6_000_000)

    def test_invalid_direct_limit_rejects_the_whole_candidate(self):
        for invalid in (
            "",
            "abc",
            "0",
            "-2.5",
            "nan",
            "inf",
            "-inf",
            "1e999999999",
            "1%2",
            "8,5",
            "8%",
        ):
            with self.subTest(invalid=invalid):
                candidate, error = self.prepare(
                    direct={"session": invalid, "weekly": "60", "opus": "15"}
                )
                self.assertTrue(error)
                self.assertEqual(candidate, {"mode": "sub", **LIMITS})

    def test_invalid_calibration_rejects_the_whole_candidate(self):
        for invalid in (
            "abc",
            "0",
            "-1",
            "100.0001",
            "nan",
            "inf",
            "-inf",
            "1e-999999999",
            "1%2%",
            "%",
            "%%",
            " % ",
            " % % ",
        ):
            with self.subTest(invalid=invalid):
                candidate, error = self.prepare(
                    calibration={"session": invalid, "weekly": "", "opus": ""}
                )
                self.assertTrue(error)
                self.assertEqual(candidate, {"mode": "sub", **LIMITS})

    def test_calibration_rejects_a_gauge_with_zero_usage(self):
        for invalid_used in (0, float("nan"), float("inf"), "not-a-number"):
            with self.subTest(used=invalid_used):
                candidate, error = self.prepare(
                    calibration={"session": "25", "weekly": "", "opus": ""},
                    stats=usage_stats(session=invalid_used),
                )
                self.assertTrue(error)
                self.assertEqual(candidate, {"mode": "sub", **LIMITS})

    def test_calibration_rejects_a_positive_result_that_rounds_to_zero_tokens(self):
        candidate, error = self.prepare(
            calibration={"session": "100", "weekly": "", "opus": ""},
            stats=usage_stats(session=0.1),
        )
        self.assertTrue(error)
        self.assertEqual(candidate, {"mode": "sub", **LIMITS})

    def test_atomic_config_write_preserves_old_json_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            old = {"session_limit": 8_000_000}
            new = {"session_limit": 42_000_000}
            with mock.patch.object(claude_pet, "CONFIG_PATH", str(path)):
                self.assertTrue(claude_pet.save_config(old))
                with mock.patch.object(claude_pet.os, "replace", side_effect=OSError("disk full")):
                    self.assertFalse(claude_pet.save_config(new))
            self.assertEqual(json.loads(path.read_text()), old)

    def test_merge_config_updates_preserves_fresh_keys_owned_by_other_paths(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            latest = {
                "x": 99.0,
                "scale": 0.75,
                "external": "fresh",
                "session_limit": 8_000_000,
            }
            path.write_text(json.dumps(latest))
            with mock.patch.object(claude_pet, "CONFIG_PATH", str(path)):
                ok, merged = claude_pet.merge_config_updates(
                    {"session_limit": 42_000_000}
                )
            self.assertTrue(ok)
            self.assertEqual(merged["session_limit"], 42_000_000)
            self.assertEqual(merged["x"], 99.0)
            self.assertEqual(merged["scale"], 0.75)
            self.assertEqual(merged["external"], "fresh")
            self.assertEqual(json.loads(path.read_text()), merged)

    def test_merge_retries_instead_of_losing_a_write_between_read_and_save(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            path.write_text(json.dumps({"x": 1, "external": "old"}))
            real_save = claude_pet.save_config
            injected = False

            def inject_late_write(*args, **kwargs):
                nonlocal injected
                if not injected:
                    injected = True
                    path.write_text(json.dumps({"x": 99, "external": "late"}))
                return real_save(*args, **kwargs)

            with mock.patch.object(claude_pet, "CONFIG_PATH", str(path)), mock.patch.object(
                claude_pet, "save_config", side_effect=inject_late_write
            ):
                ok, merged = claude_pet.merge_config_updates({"scale": 0.7})

            self.assertTrue(ok)
            self.assertTrue(injected)
            self.assertEqual(merged["x"], 99)
            self.assertEqual(merged["external"], "late")
            self.assertEqual(merged["scale"], 0.7)
            self.assertEqual(json.loads(path.read_text()), merged)

    def test_compute_usage_uses_the_supplied_runtime_snapshot(self):
        runtime = dict(claude_pet.RUNTIME)
        runtime.update(LIMITS)
        original = dict(claude_pet.RUNTIME)
        claude_pet.RUNTIME.update(
            session_limit=1,
            weekly_limit=2,
            opus_limit=3,
        )
        self.addCleanup(lambda: (claude_pet.RUNTIME.clear(), claude_pet.RUNTIME.update(original)))
        with mock.patch.object(claude_pet, "parse_usage_entries", return_value=[]):
            stats = claude_pet.compute_usage(runtime=runtime)
        self.assertEqual(stats["session"]["limit"], LIMITS["session_limit"])
        self.assertEqual(stats["weekly"]["limit"], LIMITS["weekly_limit"])
        self.assertEqual(stats["opus"]["limit"], LIMITS["opus_limit"])

    def test_other_numeric_settings_require_finite_in_range_values(self):
        valid, error = claude_pet.prepare_settings_numbers("23", "12.50")
        self.assertIsNone(error)
        self.assertEqual(valid, {"weekly_reset_hour": 23, "api_budget": 12.5})

        invalid_pairs = (
            ("nan", "0"),
            ("inf", "0"),
            ("1.5", "0"),
            ("-1", "0"),
            ("24", "0"),
            ("20", "nan"),
            ("20", "inf"),
            ("20", "-0.01"),
            ("20", "1%2"),
        )
        for hour, budget in invalid_pairs:
            with self.subTest(hour=hour, budget=budget):
                values, error = claude_pet.prepare_settings_numbers(hour, budget)
                self.assertEqual(values, {})
                self.assertTrue(error)

    def valid_settings_form(self, **overrides):
        form = {
            "pet": "dog",
            "lang": "ko",
            "mode": "sub",
            "model_keyword": "opus",
            "weekly_reset_day": 2,
            "weekly_reset_hour": "20",
            "api_budget": "0",
            "spike_mult": 1.0,
            "greet": True,
            "admin_key": "",
            "session_limit_m": "8",
            "weekly_limit_m": "60",
            "opus_limit_m": "15",
            "session_pct": "25",
            "weekly_pct": "",
            "opus_pct": "",
        }
        form.update(overrides)
        return form

    def test_settings_transaction_rejects_invalid_input_before_any_apply(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        before = dict(base)
        plan, error = claude_pet.plan_settings_save(
            base,
            self.valid_settings_form(session_limit_m="0"),
            usage_stats=usage_stats(),
        )
        self.assertIsNone(plan)
        self.assertTrue(error)
        self.assertEqual(base, before)

    def test_direct_only_settings_save_does_not_scan_usage(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        stats_for = mock.Mock(
            side_effect=AssertionError(
                "direct limits do not need log usage or calibration stats"
            )
        )

        plan, error = claude_pet.plan_settings_save(
            base,
            self.valid_settings_form(
                session_pct="", weekly_pct="", opus_pct=""
            ),
            stats_for=stats_for,
        )

        self.assertIsNone(error)
        self.assertEqual(plan["updates"]["session_limit"], 8_000_000)
        self.assertEqual(plan["updates"]["weekly_limit"], 60_000_000)
        self.assertEqual(plan["updates"]["opus_limit"], 15_000_000)
        stats_for.assert_not_called()

    def test_calibration_usage_scan_failure_is_a_settings_error(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        cases = (
            ({"session_pct": "25", "weekly_pct": "", "opus_pct": ""},
             "session"),
            ({"session_pct": "", "weekly_pct": "25", "opus_pct": ""},
             "weekly"),
        )
        for calibration, gauge in cases:
            with self.subTest(gauge=gauge):
                plan, error = claude_pet.plan_settings_save(
                    base,
                    self.valid_settings_form(**calibration),
                    stats_for=mock.Mock(
                        side_effect=TypeError("malformed usage row")
                    ),
                )

                self.assertIsNone(plan)
                self.assertEqual(
                    error,
                    claude_pet.t(
                        "s_err_calib_used",
                        field=claude_pet.t("s_g_" + gauge),
                    ),
                )

    def test_settings_transaction_write_failure_keeps_memory_and_callbacks_untouched(self):
        cfg = {"mode": "sub", "scale": 0.75, **LIMITS}
        before = dict(cfg)
        plan, error = claude_pet.plan_settings_save(
            cfg, self.valid_settings_form(), usage_stats=usage_stats()
        )
        self.assertIsNone(error)
        apply_fn = mock.Mock()
        set_pet_fn = mock.Mock()
        with mock.patch.object(
            claude_pet, "merge_config_updates", return_value=(False, None)
        ):
            ok, merged = claude_pet.apply_settings_plan(
                plan,
                cfg,
                apply_fn=apply_fn,
                set_pet_fn=set_pet_fn,
                prev_pet="cat",
            )
        self.assertFalse(ok)
        self.assertIsNone(merged)
        self.assertEqual(cfg, before)
        apply_fn.assert_not_called()
        set_pet_fn.assert_not_called()

    def test_settings_transaction_applies_calibration_and_preserves_fresh_disk_keys(self):
        cfg = {"mode": "sub", "scale": 0.5, **LIMITS}
        plan, error = claude_pet.plan_settings_save(
            cfg,
            self.valid_settings_form(),
            usage_stats=usage_stats(session=2_000_000),
        )
        self.assertIsNone(error)
        self.assertEqual(plan["updates"]["session_limit"], 8_000_000)
        merged = {**plan["updates"], "scale": 0.9, "x": 123}
        apply_fn = mock.Mock()
        set_pet_fn = mock.Mock()
        with mock.patch.object(
            claude_pet, "merge_config_updates", return_value=(True, merged)
        ):
            ok, result = claude_pet.apply_settings_plan(
                plan,
                cfg,
                apply_fn=apply_fn,
                set_pet_fn=set_pet_fn,
                prev_pet="cat",
            )
        self.assertTrue(ok)
        self.assertEqual(result, merged)
        self.assertEqual(cfg, merged)
        self.assertEqual(cfg["scale"], 0.9)
        apply_fn.assert_called_once_with(cfg)
        set_pet_fn.assert_called_once_with("dog")

    def test_gui_save_path_uses_the_tested_transaction_and_commits_before_close(self):
        source = inspect.getsource(claude_pet.run_gui)
        plan_at = source.index("plan_settings_save(cfg, form")
        apply_at = source.index("apply_settings_plan(plan, cfg")
        commit_at = source.index("commit_refresh_result(state, gen")
        close_at = source.index('ui["panel"].orderOut_(None)')
        self.assertLess(plan_at, apply_at)
        self.assertLess(apply_at, commit_at)
        self.assertLess(commit_at, close_at)
        self.assertIn("panel.setHidesOnDeactivate_(False)", source)


def make_pet_source(root):
    root = Path(root)
    for name in ("README.md", "README.ko.md", "README.ja.md", "README.es.md"):
        (root / name).write_text(f"source {name}\n")
    for pet in ("dog", "elephant", "fox", "scorpion"):
        p = root / "pets" / pet
        p.mkdir(parents=True)
        (p / "pet.json").write_text(
            json.dumps(
                {
                    "id": pet,
                    "spritesheetPath": "spritesheet.webp",
                    "spriteVersionNumber": 2,
                }
            )
        )
        (p / "spritesheet.webp").write_bytes((pet + " sheet").encode())
        (p / "preview.png").write_bytes((pet + " preview").encode())


def snapshot_tree(root):
    root = Path(root)
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


class BundledPetSeedTests(unittest.TestCase):
    def test_empty_destination_receives_the_full_distributed_tree(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)

            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            for rel in (
                "README.md",
                "README.ko.md",
                "README.ja.md",
                "README.es.md",
            ):
                self.assertEqual((dst / rel).read_bytes(), (src / rel).read_bytes())
            for pet in ("dog", "elephant", "fox", "scorpion"):
                for name in ("pet.json", "spritesheet.webp", "preview.png"):
                    rel = Path("pets") / pet / name
                    self.assertEqual((dst / rel).read_bytes(), (src / rel).read_bytes())

    def test_upgrade_preserves_every_existing_path_and_adds_only_missing_pets(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            (dst / "pets" / "dog").mkdir(parents=True)
            (dst / "pets" / "dog" / "custom-only.txt").write_text("never overwrite")
            (dst / "pets" / "elephant").mkdir()
            (dst / "pets" / "elephant" / "pet.json").write_text("user partial")
            (dst / "pets" / "rabbit").mkdir()
            (dst / "pets" / "rabbit" / "pet.json").write_text("custom rabbit")
            (dst / "README.md").write_text("user readme")
            before_existing = snapshot_tree(dst)

            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            after = snapshot_tree(dst)
            for rel, value in before_existing.items():
                self.assertEqual(after[rel], value, rel)
            self.assertFalse((dst / "pets" / "dog" / "pet.json").exists())
            self.assertFalse((dst / "pets" / "elephant" / "spritesheet.webp").exists())
            self.assertTrue((dst / "pets" / "fox" / "preview.png").is_file())
            self.assertTrue((dst / "pets" / "scorpion" / "preview.png").is_file())
            self.assertEqual((dst / "README.md").read_text(), "user readme")
            self.assertTrue((dst / "README.ko.md").is_file())

    def test_second_seed_is_byte_and_mtime_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)
            first = snapshot_tree(dst)
            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)
            self.assertEqual(snapshot_tree(dst), first)

    def test_destination_root_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            outside = Path(td) / "outside"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            outside.mkdir()
            dst.parent.mkdir()
            make_pet_source(src)
            try:
                os.symlink(outside, dst)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_source_pet_is_not_copied(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            external = Path(td) / "external-dog"
            src.mkdir(parents=True)
            make_pet_source(src)
            for child in (src / "pets" / "dog").iterdir():
                child.unlink()
            (src / "pets" / "dog").rmdir()
            external.mkdir()
            (external / "pet.json").write_text("external")
            os.symlink(external, src / "pets" / "dog")

            claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertFalse((dst / "pets" / "dog").exists())
            self.assertTrue((dst / "pets" / "fox").is_dir())

    def test_pet_with_a_missing_required_file_is_never_published(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            (src / "pets" / "dog" / "preview.png").unlink()

            report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertFalse((dst / "pets" / "dog").exists())
            self.assertTrue(any("pets/dog" in error for error in report["errors"]))

    def test_pet_with_a_symlinked_required_file_is_never_published(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            outside = Path(td) / "outside-preview.png"
            src.mkdir(parents=True)
            make_pet_source(src)
            outside.write_bytes(b"outside")
            preview = src / "pets" / "dog" / "preview.png"
            preview.unlink()
            try:
                os.symlink(outside, preview)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertFalse((dst / "pets" / "dog").exists())
            self.assertTrue(any("pets/dog" in error for error in report["errors"]))

    def test_malformed_or_traversing_pet_metadata_is_never_published(self):
        invalid_documents = (
            "not json",
            json.dumps(
                {
                    "id": "dog",
                    "spritesheetPath": "../outside.webp",
                    "spriteVersionNumber": 2,
                }
            ),
            json.dumps(
                {
                    "id": "not-dog",
                    "spritesheetPath": "spritesheet.webp",
                    "spriteVersionNumber": 2,
                }
            ),
            json.dumps(
                {
                    "id": "dog",
                    "spritesheetPath": "missing.webp",
                    "spriteVersionNumber": 2,
                }
            ),
            json.dumps(
                {
                    "id": "dog",
                    "spritesheetPath": "spritesheet.webp",
                    "spriteVersionNumber": "not-an-int",
                }
            ),
            json.dumps(
                {
                    "id": "dog",
                    "spritesheetPath": "spritesheet.webp",
                    "spriteVersionNumber": 999,
                }
            ),
        )
        for document in invalid_documents:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as td:
                src = Path(td) / "source" / ".claude_pet"
                dst = Path(td) / "home" / ".claude_pet"
                src.mkdir(parents=True)
                make_pet_source(src)
                (src / "pets" / "dog" / "pet.json").write_text(document)

                report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

                self.assertFalse((dst / "pets" / "dog").exists())
                self.assertTrue(any("pets/dog" in error for error in report["errors"]))

    def test_pet_metadata_must_reference_the_distributed_spritesheet(self):
        for sheet in ("alternate.webp", "preview.png", "pet.json"):
            with self.subTest(sheet=sheet), tempfile.TemporaryDirectory() as td:
                src = Path(td) / "source" / ".claude_pet"
                dst = Path(td) / "home" / ".claude_pet"
                src.mkdir(parents=True)
                make_pet_source(src)
                dog = src / "pets" / "dog"
                if sheet == "alternate.webp":
                    (dog / sheet).write_bytes(b"valid but not in the bundle manifest")
                (dog / "pet.json").write_text(
                    json.dumps(
                        {
                            "id": "dog",
                            "spritesheetPath": sheet,
                            "spriteVersionNumber": 2,
                        }
                    )
                )

                report = claude_pet.seed_bundled_pet_assets(
                    source_root=src, dest_root=dst
                )

                self.assertFalse((dst / "pets" / "dog").exists())
                self.assertTrue(any("pets/dog" in error for error in report["errors"]))

    def test_readme_created_during_publish_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            real_link = claude_pet.os.link
            injected = False
            user_inode = None

            def create_user_readme_before_publish(source, destination, *args, **kwargs):
                nonlocal injected, user_inode
                dest_fd = kwargs.get("dst_dir_fd")
                if destination == "README.md" and dest_fd is not None and not injected:
                    injected = True
                    fd = os.open(
                        destination,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o644,
                        dir_fd=dest_fd,
                    )
                    with os.fdopen(fd, "w") as user_file:
                        user_file.write("late-user-write")
                    user_inode = os.stat(destination, dir_fd=dest_fd).st_ino
                return real_link(source, destination, *args, **kwargs)

            with mock.patch.object(
                claude_pet.os, "link", side_effect=create_user_readme_before_publish
            ):
                report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertTrue(injected)
            self.assertEqual((dst / "README.md").read_text(), "late-user-write")
            self.assertEqual((dst / "README.md").stat().st_ino, user_inode)
            self.assertIn("README.md", report["skipped"])
            self.assertFalse(any(path.name.startswith(".seed-") for path in dst.iterdir()))

    def test_missing_atomic_file_publish_primitive_never_leaves_a_partial_readme(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)

            with mock.patch.object(
                claude_pet.os,
                "link",
                side_effect=OSError(errno.EXDEV, "hard links unavailable"),
            ):
                report = claude_pet.seed_bundled_pet_assets(
                    source_root=src, dest_root=dst
                )

            for name in ("README.md", "README.ko.md", "README.ja.md", "README.es.md"):
                self.assertFalse((dst / name).exists())
            self.assertTrue(report["errors"] or report["skipped"])
            self.assertFalse(any(path.name.startswith(".seed-") for path in dst.iterdir()))

    def test_pet_directory_created_during_publish_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            real_publish = claude_pet._publish_dir_noreplace
            injected = False
            user_inode = None

            def create_user_pet_before_publish(dir_fd, source, destination, *args, **kwargs):
                nonlocal injected, user_inode
                if destination == "dog" and not injected:
                    injected = True
                    user_path = dst / "pets" / "dog"
                    user_path.mkdir()
                    user_inode = user_path.stat().st_ino
                return real_publish(dir_fd, source, destination, *args, **kwargs)

            with mock.patch.object(
                claude_pet,
                "_publish_dir_noreplace",
                side_effect=create_user_pet_before_publish,
            ):
                report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertTrue(injected)
            self.assertEqual((dst / "pets" / "dog").stat().st_ino, user_inode)
            self.assertEqual(list((dst / "pets" / "dog").iterdir()), [])
            self.assertIn("pets/dog", report["skipped"])
            self.assertFalse(
                any(path.name.startswith(".seed-") for path in (dst / "pets").iterdir())
            )

    def test_pets_symlink_inserted_during_destination_creation_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            outside = Path(td) / "outside"
            src.mkdir(parents=True)
            outside.mkdir()
            make_pet_source(src)
            real_mkdir = claude_pet.os.mkdir
            injected = False

            def insert_symlink_before_mkdir(path, *args, **kwargs):
                nonlocal injected
                dir_fd = kwargs.get("dir_fd")
                if path == "pets" and dir_fd is not None and not injected:
                    injected = True
                    os.symlink(str(outside), "pets", dir_fd=dir_fd)
                return real_mkdir(path, *args, **kwargs)

            try:
                with mock.patch.object(
                    claude_pet.os, "mkdir", side_effect=insert_symlink_before_mkdir
                ):
                    report = claude_pet.seed_bundled_pet_assets(
                        source_root=src, dest_root=dst
                    )
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            self.assertTrue(injected)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertTrue(report["errors"])

    def test_root_symlink_inserted_during_destination_creation_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            outside = Path(td) / "outside"
            src.mkdir(parents=True)
            outside.mkdir()
            dst.parent.mkdir()
            make_pet_source(src)
            real_makedirs = claude_pet.os.makedirs
            injected = False
            moved = Path(td) / "opened-root"

            def replace_root_after_creation(path, *args, **kwargs):
                nonlocal injected
                result = real_makedirs(path, *args, **kwargs)
                if Path(path) == dst and not injected:
                    injected = True
                    dst.rename(moved)
                    os.symlink(outside, dst)
                return result

            try:
                with mock.patch.object(
                    claude_pet.os, "makedirs", side_effect=replace_root_after_creation
                ):
                    report = claude_pet.seed_bundled_pet_assets(
                        source_root=src, dest_root=dst
                    )
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            self.assertTrue(injected)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertTrue(report["errors"])

    def test_destination_root_replaced_after_safe_open_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            moved = Path(td) / "moved-user-root"
            outside = Path(td) / "outside"
            src.mkdir(parents=True)
            outside.mkdir()
            outside_mtime = outside.stat().st_mtime_ns
            make_pet_source(src)
            real_same_dir = claude_pet._same_dir
            injected = False

            def replace_root_after_validation(fd, path):
                nonlocal injected
                same = real_same_dir(fd, path)
                if Path(path) == dst and same and not injected:
                    injected = True
                    dst.rename(moved)
                    os.symlink(outside, dst)
                return same

            try:
                with mock.patch.object(
                    claude_pet, "_same_dir", side_effect=replace_root_after_validation
                ):
                    report = claude_pet.seed_bundled_pet_assets(
                        source_root=src, dest_root=dst
                    )
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink replacement unavailable")

            self.assertTrue(injected)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(outside.stat().st_mtime_ns, outside_mtime)
            self.assertTrue(report["errors"] or report["skipped"])

    def test_destination_root_replaced_after_pets_open_keeps_readmes_fd_anchored(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            moved = Path(td) / "moved-user-root"
            outside = Path(td) / "outside"
            src.mkdir(parents=True)
            outside.mkdir()
            outside_mtime = outside.stat().st_mtime_ns
            make_pet_source(src)
            real_seed_readmes = claude_pet._seed_readmes
            injected = False

            def replace_root_before_readmes(source, root_fd, report):
                nonlocal injected
                if not injected:
                    injected = True
                    dst.rename(moved)
                    os.symlink(outside, dst)
                return real_seed_readmes(source, root_fd, report)

            try:
                with mock.patch.object(
                    claude_pet, "_seed_readmes", side_effect=replace_root_before_readmes
                ):
                    report = claude_pet.seed_bundled_pet_assets(
                        source_root=src, dest_root=dst
                    )
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink replacement unavailable")

            self.assertTrue(injected)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(outside.stat().st_mtime_ns, outside_mtime)
            self.assertTrue((moved / "README.md").is_file())
            self.assertTrue(report["errors"])

    def test_pets_directory_replaced_after_safe_open_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            moved = Path(td) / "moved-user-pets"
            outside = Path(td) / "outside"
            src.mkdir(parents=True)
            outside.mkdir()
            outside_mtime = outside.stat().st_mtime_ns
            make_pet_source(src)
            real_seed_pets = claude_pet._seed_pets
            injected = False

            def replace_pets_after_open(source, pets_fd, report):
                nonlocal injected
                if not injected:
                    injected = True
                    (dst / "pets").rename(moved)
                    os.symlink(outside, dst / "pets")
                return real_seed_pets(source, pets_fd, report)

            try:
                with mock.patch.object(
                    claude_pet, "_seed_pets", side_effect=replace_pets_after_open
                ):
                    report = claude_pet.seed_bundled_pet_assets(
                        source_root=src, dest_root=dst
                    )
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink replacement unavailable")

            self.assertTrue(injected)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(outside.stat().st_mtime_ns, outside_mtime)
            self.assertTrue(report["errors"])
            self.assertTrue((moved / "dog" / "pet.json").is_file())
            self.assertFalse(
                any(path.name.startswith(".seed-") for path in moved.iterdir())
            )

    def test_copy_failure_never_publishes_a_partial_pet_directory(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)
            real_copy2 = claude_pet.shutil.copy2

            def fail_on_dog_sheet(source, destination, *args, **kwargs):
                if Path(source).name == "spritesheet.webp" and Path(source).parent.name == "dog":
                    raise OSError("simulated disk failure")
                return real_copy2(source, destination, *args, **kwargs)

            with mock.patch.object(claude_pet.shutil, "copy2", side_effect=fail_on_dog_sheet):
                report = claude_pet.seed_bundled_pet_assets(source_root=src, dest_root=dst)

            self.assertFalse((dst / "pets" / "dog").exists())
            self.assertFalse(
                any(path.name.startswith(".seed-") for path in (dst / "pets").iterdir())
            )
            self.assertTrue(report["errors"])
            self.assertTrue((dst / "pets" / "fox").is_dir())

    def test_missing_atomic_directory_publish_primitive_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source" / ".claude_pet"
            dst = Path(td) / "home" / ".claude_pet"
            src.mkdir(parents=True)
            make_pet_source(src)

            with mock.patch.object(claude_pet, "_RENAMEATX_NP", None):
                report = claude_pet.seed_bundled_pet_assets(
                    source_root=src, dest_root=dst
                )

            for pet in ("dog", "elephant", "fox", "scorpion"):
                self.assertFalse((dst / "pets" / pet).exists())
            self.assertTrue(report["errors"])
            self.assertFalse(
                any(path.name.startswith(".seed-") for path in (dst / "pets").iterdir())
            )


class PreflightRun:
    """A `subprocess.run` stand-in for `validate_update_app`.

    `mock.Mock(returncode=0)` is not enough, and the way it fails is
    misleading: `spctl -vv` writes its assessment to **stderr**, and
    production reads the `origin=` line from there to confirm the signer is
    us. A mock with no stderr is therefore rejected with "Gatekeeper reported
    no origin" — which reads as a fact about the bundle rather than about the
    fixture, and made three tests here look like preflight regressions.

    One `returncode` for every tool is deliberate: this file's tests either
    accept a good bundle or reject on identity, and the per-tool dispatch that
    tells "stapler was consulted" from "stapler never ran" lives in
    `tests/test_updater.py`, which is where that distinction is tested.
    """

    def __init__(self, returncode=0):
        self.returncode = returncode
        self.calls = []

    def __call__(self, argv, *args, **kwargs):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        joined = " ".join(argv)
        rc = self.returncode
        out = err = ""
        if rc == 0 and "spctl" in joined:
            err = (f"{argv[-1]}: accepted\n"
                   f"source=Notarized Developer ID\n"
                   f"origin=Developer ID Application: Yeongyu Yang "
                   f"({claude_pet.TEAM_ID})\n")
        elif rc == 0 and "stapler" in joined:
            out = f"Processing: {argv[-1]}\nThe validate action worked!\n"
        elif rc != 0 and "spctl" in joined:
            err = f"{argv[-1]}: rejected\n"
        return mock.Mock(returncode=rc, stdout=out, stderr=err)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class GithubUpdateTests(IsolationCheckedTest):
    def setUp(self):
        self.old_cache = dict(claude_pet._upd_cache)
        claude_pet._upd_cache.clear()
        claude_pet._upd_cache["t"] = 0.0
        self.addCleanup(
            lambda: (claude_pet._upd_cache.clear(), claude_pet._upd_cache.update(self.old_cache))
        )

    def install_parent(self):
        """A temp stand-in for `/Applications`.

        `install_github_update` claims its staging directory **beside**
        `app_path`, so a test that passes `/Applications/ClaudePet.app` writes
        into `/Applications` — which no HOME redirection covers, and which
        two leftovers in this repository's tree already attest to. The install
        path is a real fixture directory because the updater binds APPID to the
        installed object's dev+inode before it hands the transaction to Popen.
        A nonexistent path stops before that handoff and cannot test launch or
        cleanup behaviour.
        """
        parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, True)
        app = Path(parent) / "ClaudePet.app"
        app.mkdir()
        (app / "installed-sentinel").write_text("original installed app")
        return str(app)

    def test_update_check_distinguishes_current_from_network_failure(self):
        current = {"tag_name": f"v{claude_pet.APP_VERSION}", "assets": []}
        with mock.patch.object(claude_pet.urllib.request, "urlopen", return_value=FakeResponse(current)):
            self.assertEqual(claude_pet.check_github_update(), ("current", None, None))
        with mock.patch.object(
            claude_pet.urllib.request, "urlopen", side_effect=URLError("offline")
        ):
            self.assertEqual(claude_pet.check_github_update(), ("failed", None, None))

    def test_update_check_returns_the_selected_release_asset(self):
        payload = {
            "tag_name": "v99.0",
            "assets": [
                {"name": "ClaudePet.zip", "browser_download_url": "https://example/arm.zip"},
                {
                    "name": "ClaudePet-universal.zip",
                    "browser_download_url": "https://example/universal.zip",
                },
            ],
        }
        with mock.patch.object(claude_pet.urllib.request, "urlopen", return_value=FakeResponse(payload)), mock.patch(
            "platform.machine", return_value="arm64"
        ):
            self.assertEqual(
                claude_pet.check_github_update(),
                ("update", "99.0", "https://example/arm.zip"),
            )

    def test_intel_never_falls_back_to_an_arm_only_archive(self):
        payload = {
            "tag_name": "v99.0",
            "assets": [
                {"name": "ClaudePet.zip", "browser_download_url": "https://example/arm.zip"},
            ],
        }
        with mock.patch.object(
            claude_pet.urllib.request, "urlopen", return_value=FakeResponse(payload)
        ), mock.patch("platform.machine", return_value="x86_64"):
            self.assertEqual(claude_pet.check_github_update(), ("failed", None, None))

    def test_apple_silicon_never_falls_back_to_an_unrelated_zip(self):
        payload = {
            "tag_name": "v99.0",
            "assets": [
                {
                    "name": "diagnostics.zip",
                    "browser_download_url": "https://example/diagnostics.zip",
                },
            ],
        }
        with mock.patch.object(
            claude_pet.urllib.request, "urlopen", return_value=FakeResponse(payload)
        ), mock.patch("platform.machine", return_value="arm64"):
            self.assertEqual(claude_pet.check_github_update(), ("failed", None, None))

    def test_replace_script_does_not_destroy_the_installed_app_before_copy_succeeds(self):
        with tempfile.TemporaryDirectory(dir=_ISOLATION["tmp"]) as td:
            installed = Path(td) / "Installed.app"
            workdir = Path(td) / "update-work"
            new_app = workdir / "ClaudePet.app"
            installed.mkdir()
            workdir.mkdir()
            command = claude_pet._update_replace_script(
                str(installed), str(new_app), str(workdir),
                app_id=path_identity(installed),
                work_id=path_identity(workdir),
            )
            ditto_at = command.index("/usr/bin/ditto")
            self.assertNotIn(f"rm -rf {installed}", command[:ditto_at])
            self.assertTrue(
                "set -e" in command or "&&" in command,
                "a failed copy must stop before launch and cleanup",
            )

    def test_replace_script_preserves_the_installed_app_when_copy_fails(self):
        with tempfile.TemporaryDirectory() as td:
            installed = Path(td) / "Installed.app"
            workdir = Path(td) / "update-work"
            new_app = workdir / "ClaudePet.app"
            installed.mkdir()
            (new_app / "Contents" / "MacOS").mkdir(parents=True)
            shutil.copyfile(sys.executable,
                            new_app / "Contents" / "MacOS" / "python")
            (new_app / "Contents" / "MacOS" / "python").chmod(0o755)
            marker = installed / "user-install-marker"
            marker.write_text("old app remains recoverable")
            reached = Path(td) / "ditto-failure-reached"
            # NEW is deliberately valid. Fail the exact copy operation, and
            # leave a witness outside WORK so cleanup cannot erase the proof
            # that the intended failure seam was actually reached.
            command = replace_launch_points(
                shorten_update_waits(claude_pet._update_replace_script(
                    str(installed), str(new_app), str(workdir),
                    app_id=path_identity(installed),
                    work_id=path_identity(workdir),
                )))
            copy_line = '/usr/bin/ditto "$NEW" "$STAGE"'
            self.assertEqual(command.count(copy_line), 1,
                             "copy-failure injection seam drifted")
            command = command.replace(
                copy_line,
                f"printf reached > {shlex.quote(str(reached))}; false",
                1,
            )

            result = subprocess.run(
                ["/bin/sh", "-c", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(reached.read_text(), "reached",
                             "the fixture failed before the injected copy fault")
            self.assertTrue(marker.is_file(), "copy failure deleted the installed app")
            if marker.is_file():
                self.assertEqual(marker.read_text(), "old app remains recoverable")
            self.assertFalse(workdir.exists(), "copy failure leaked the update work directory")

    def test_replace_script_rolls_back_when_the_replacement_cannot_launch(self):
        with tempfile.TemporaryDirectory() as td:
            installed = Path(td) / "Installed.app"
            workdir = Path(td) / "update-work"
            new_app = workdir / "ClaudePet.app"
            installed.mkdir()
            (new_app / "Contents" / "MacOS").mkdir(parents=True)
            shutil.copyfile(sys.executable,
                            new_app / "Contents" / "MacOS" / "python")
            (new_app / "Contents" / "MacOS" / "python").chmod(0o755)
            old_marker = installed / "old-marker"
            old_marker.write_text("original")
            (new_app / "new-marker").write_text("replacement")
            # `false` stands in for the launch, so the acknowledgement never
            # comes and the script rolls back — which is precisely the path
            # that calls `relaunch()`, the second `open`. Substituting only
            # the first literal left a real `/usr/bin/open` on a fixture
            # bundle in every run of this test.
            command = replace_launch_points(
                shorten_update_waits(claude_pet._update_replace_script(
                    str(installed), str(new_app), str(workdir),
                    app_id=path_identity(installed),
                    work_id=path_identity(workdir),
                )),
                launcher="false")

            subprocess.run(
                ["/bin/sh", "-c", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )

            self.assertTrue(old_marker.is_file(), "launch failure did not restore the old app")
            self.assertFalse((installed / "new-marker").exists())
            self.assertFalse(workdir.exists())

    def make_update_app(self, root, version="99.0"):
        """A structurally complete bundle, as the preflight now defines one.

        The two binaries and `CFBundleExecutable` are not decoration. The
        preflight requires the main executable *and* `Contents/MacOS/python`
        to be regular files, and reads their Mach-O headers for the
        architecture check — it does not take `lipo`'s word for it, so a
        placeholder text file is refused whatever the mocked `subprocess.run`
        returns. Without them every test built on this fixture was refused
        with "main executable is not a regular file", one step into a
        validation whose later steps it claimed to cover.

        A copy of the running interpreter is used because it is a real
        universal Mach-O; nothing about it is executed here.
        """
        app = Path(root) / "ClaudePet.app"
        macos = app / "Contents" / "MacOS"
        resources = app / "Contents" / "Resources"
        macos.mkdir(parents=True)
        resources.mkdir(parents=True)
        for name in ("ClaudePet", "python"):
            shutil.copyfile(sys.executable, macos / name)
            (macos / name).chmod(0o755)
        with (app / "Contents" / "Info.plist").open("wb") as f:
            plistlib.dump(
                {
                    "CFBundleIdentifier": "me.yeongyu.claudepet",
                    "CFBundleExecutable": "ClaudePet",
                    "CFBundleVersion": version,
                    "CFBundleShortVersionString": version,
                },
                f,
            )
        pet_root = resources / ".claude_pet"
        pet_root.mkdir()
        make_pet_source(pet_root)
        return app

    def test_update_app_preflight_accepts_the_expected_signed_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            app = self.make_update_app(td)
            with mock.patch.object(
                claude_pet.subprocess,
                "run",
                side_effect=PreflightRun(),
            ) as run:
                self.assertTrue(claude_pet.validate_update_app(app, "99.0"))
            self.assertTrue(any("codesign" in str(call.args[0]) for call in run.call_args_list))

    def test_update_app_preflight_rejects_identity_version_and_signature_failures(self):
        variants = (
            "bundle-id",
            "bundle-version",
            "short-version",
            "symlink",
            "signature",
        )
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as td:
                app = self.make_update_app(td)
                plist_path = app / "Contents" / "Info.plist"
                signature_returncode = 0
                if variant in ("bundle-id", "bundle-version", "short-version"):
                    with plist_path.open("rb") as f:
                        plist = plistlib.load(f)
                    if variant == "bundle-id":
                        plist["CFBundleIdentifier"] = "com.example.not-claudepet"
                    elif variant == "bundle-version":
                        plist["CFBundleVersion"] = "98.0"
                    else:
                        plist["CFBundleShortVersionString"] = "98.0"
                    with plist_path.open("wb") as f:
                        plistlib.dump(plist, f)
                elif variant == "symlink":
                    target = (
                        app
                        / "Contents"
                        / "Resources"
                        / ".claude_pet"
                        / "pets"
                        / "dog"
                        / "preview.png"
                    )
                    target.unlink()
                    os.symlink("spritesheet.webp", target)
                else:
                    signature_returncode = 1

                with mock.patch.object(
                    claude_pet.subprocess,
                    "run",
                    side_effect=PreflightRun(signature_returncode),
                ):
                    self.assertFalse(claude_pet.validate_update_app(app, "99.0"))

    def test_update_app_preflight_warns_but_does_not_strand_on_missing_manifest_member(self):
        with tempfile.TemporaryDirectory() as td:
            app = self.make_update_app(td)
            target = (
                app
                / "Contents"
                / "Resources"
                / ".claude_pet"
                / "pets"
                / "dog"
                / "preview.png"
            )
            target.unlink()
            with mock.patch.object(
                claude_pet.subprocess,
                "run",
                side_effect=PreflightRun(),
            ), mock.patch("builtins.print") as printed:
                self.assertTrue(claude_pet.validate_update_app(app, "99.0"))
            self.assertTrue(printed.called, "manifest drift must emit a diagnostic")

    def test_failed_poll_does_not_consume_the_retry_cooldown(self):
        state = {"update": None}
        with mock.patch.object(
            claude_pet, "check_github_update", return_value=("failed", None, None)
        ):
            self.assertEqual(claude_pet.poll_github_update(state, now=1000.0), "failed")
        self.assertEqual(claude_pet._upd_cache["t"], 0.0)

    def test_valid_poll_records_cooldown_and_an_update_becomes_pending(self):
        state = {"update": None}
        with mock.patch.object(
            claude_pet,
            "check_github_update",
            return_value=("update", "99.0", "https://example/app.zip"),
        ):
            self.assertEqual(claude_pet.poll_github_update(state, now=1000.0), "update")
        self.assertEqual(claude_pet._upd_cache["t"], 1000.0)
        self.assertEqual(state["update"], ("99.0", "https://example/app.zip"))

    # A structurally safe archive, because `_zip_members_are_safe` runs for
    # real before extraction: a fixture that writes `b"zip"` is refused as
    # unreadable, and every test below would then stop one step after the
    # download while claiming to cover what follows it.
    @staticmethod
    def update_zip_bytes():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("ClaudePet.app/Contents/Info.plist", "x")
            zf.writestr("ClaudePet.app/Contents/MacOS/ClaudePet", "x")
        return buf.getvalue()

    def downloads_a_zip(self):
        return patch_download(
            lambda _url, path: Path(path).write_bytes(self.update_zip_bytes()))

    def test_download_failure_removes_the_new_temporary_directory(self):
        app = self.install_parent()
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        with mock.patch.object(claude_pet.tempfile, "mkdtemp", return_value=td), \
                patch_download(URLError("offline")):
            self.assertFalse(
                claude_pet.install_github_update(
                    "https://example.test/app.zip", app_path=app,
                    expect_version="99.0",
                )
            )
        self.assertFalse(os.path.exists(td))

    def test_launch_failure_removes_the_new_temporary_directory(self):
        app = self.install_parent()
        app_id = path_identity(app)
        sentinel = Path(app) / "installed-sentinel"
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        observed = {}

        def fake_run(*args, **kwargs):
            (Path(td) / "ClaudePet.app").mkdir(exist_ok=True)
            return mock.Mock(returncode=0)

        def fail_popen(args, **kwargs):
            command = args[-1]
            stage = shell_assignment(command, "STAGE")
            observed.update(
                command=command,
                kwargs=kwargs,
                work_id=path_identity(td),
                stage=stage,
                stage_id=path_identity(stage),
            )
            raise OSError("cannot launch")

        with mock.patch.object(claude_pet.tempfile, "mkdtemp", return_value=td), \
                self.downloads_a_zip(), \
                mock.patch.object(claude_pet.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(claude_pet, "validate_update_app", return_value=True), \
                mock.patch.object(claude_pet.subprocess, "Popen",
                                  side_effect=fail_popen) as popen:
            self.assertFalse(
                claude_pet.install_github_update(
                    "https://example.test/app.zip", app_path=app,
                    expect_version="99.0",
                )
            )
        popen.assert_called_once()
        command = observed["command"]
        self.assertEqual(shell_assignment(command, "APPID"), app_id)
        self.assertEqual(shell_assignment(command, "WORK"), td)
        self.assertEqual(shell_assignment(command, "WORKID"), observed["work_id"])
        self.assertEqual(shell_assignment(command, "STAGE"), observed["stage"])
        self.assertEqual(shell_assignment(command, "STAGEID"), observed["stage_id"])
        pass_fds = observed["kwargs"].get("pass_fds")
        self.assertIsInstance(pass_fds, tuple)
        self.assertEqual(len(pass_fds), 1)
        self.assertEqual(command.count(f"{pass_fds[0]}>&-"), 3,
                         "the inherited lock fd is not closed at every child seam")
        self.assertFalse(os.path.exists(td))
        self.assertFalse(os.path.exists(observed["stage"]))
        self.assertEqual(sentinel.read_text(), "original installed app")

    def test_successful_launch_transfers_temp_cleanup_to_the_detached_script(self):
        app = self.install_parent()
        app_id = path_identity(app)
        sentinel = Path(app) / "installed-sentinel"
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)

        def fake_run(*args, **kwargs):
            (Path(td) / "ClaudePet.app").mkdir(exist_ok=True)
            return mock.Mock(returncode=0)

        with mock.patch.object(claude_pet.tempfile, "mkdtemp", return_value=td), \
                self.downloads_a_zip(), \
                mock.patch.object(claude_pet.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(claude_pet, "validate_update_app", return_value=True), \
                mock.patch.object(claude_pet.subprocess, "Popen",
                                  return_value=mock.Mock()) as popen:
            self.assertTrue(
                claude_pet.install_github_update(
                    "https://example.test/app.zip", app_path=app,
                    expect_version="99.0",
                )
            )
        popen.assert_called_once()
        command = popen.call_args.args[0][-1]
        stage = shell_assignment(command, "STAGE")
        self.assertEqual(shell_assignment(command, "APPID"), app_id)
        self.assertEqual(shell_assignment(command, "WORK"), td)
        self.assertEqual(shell_assignment(command, "WORKID"), path_identity(td))
        self.assertEqual(shell_assignment(command, "STAGEID"), path_identity(stage))
        pass_fds = popen.call_args.kwargs.get("pass_fds")
        self.assertIsInstance(pass_fds, tuple)
        self.assertEqual(len(pass_fds), 1)
        self.assertEqual(command.count(f"{pass_fds[0]}>&-"), 3,
                         "the inherited lock fd is not closed at every child seam")
        self.assertTrue(os.path.isdir(td),
                        "WORK was not handed to the detached cleanup owner")
        self.assertTrue(os.path.isdir(stage),
                        "STAGE was not handed to the detached cleanup owner")
        self.assertEqual(sentinel.read_text(), "original installed app")
        # The script would have removed these; it was never really spawned.
        shutil.rmtree(td)


class RefreshGenerationTests(unittest.TestCase):
    def test_only_the_newest_refresh_generation_can_commit(self):
        state = {"stats": "initial", "refresh_generation": 0}
        old_generation = claude_pet.begin_refresh_generation(state)
        new_generation = claude_pet.begin_refresh_generation(state)

        self.assertFalse(
            claude_pet.commit_refresh_result(
                state, old_generation, {"stats": "old", "oauth": "old-oauth"}
            )
        )
        self.assertEqual(state["stats"], "initial")
        self.assertTrue(
            claude_pet.commit_refresh_result(
                state, new_generation, {"stats": "new", "oauth": "new-oauth"}
            )
        )
        self.assertEqual(state["stats"], "new")
        self.assertEqual(state["oauth"], "new-oauth")

    def test_generation_check_and_state_update_are_atomic(self):
        old_update_entered = threading.Event()
        release_old_update = threading.Event()

        class InterleavingState(dict):
            def update(self, values, *args, **kwargs):
                if values.get("stats") == "old":
                    old_update_entered.set()
                    self.assert_release(release_old_update)
                return super().update(values, *args, **kwargs)

            @staticmethod
            def assert_release(event):
                if not event.wait(2):
                    raise AssertionError("timed out waiting to release old commit")

        state = InterleavingState(stats="initial", refresh_generation=0)
        old_generation = claude_pet.begin_refresh_generation(state)
        old_result = []
        new_result = []

        old_thread = threading.Thread(
            target=lambda: old_result.append(
                claude_pet.commit_refresh_result(state, old_generation, {"stats": "old"})
            )
        )
        old_thread.start()
        self.assertTrue(old_update_entered.wait(2))

        def run_new_refresh():
            generation = claude_pet.begin_refresh_generation(state)
            new_result.append(
                claude_pet.commit_refresh_result(state, generation, {"stats": "new"})
            )

        new_thread = threading.Thread(target=run_new_refresh)
        new_thread.start()
        # With a correct lock this thread waits for the old atomic commit. Without
        # one it commits now, after which the paused old update overwrites it.
        new_thread.join(0.1)
        release_old_update.set()
        old_thread.join(2)
        new_thread.join(2)

        self.assertFalse(old_thread.is_alive())
        self.assertFalse(new_thread.is_alive())
        self.assertEqual(old_result, [True])
        self.assertEqual(new_result, [True])
        self.assertEqual(state["stats"], "new")


def extract_zsh_function(script, name):
    """Return one top-level zsh function without sourcing the entry point."""
    match = re.search(
        rf"(?ms)^{re.escape(name)}\(\) \{{\n.*?^\}}[ \t]*$", script)
    if match is None:
        raise AssertionError(f"top-level function {name}() was not found")
    return match.group(0)


def extract_zsh_case_arm(script, label):
    """Return one bottom-dispatch arm without executing the script."""
    match = re.search(
        rf"(?ms)^  {re.escape(label)}\)\n(.*?)^    ;;[ \t]*$", script)
    if match is None:
        raise AssertionError(f"dispatch arm {label}) was not found")
    return match.group(1)


def operational_zsh(block):
    """Discard comment-only lines so comments cannot satisfy a contract."""
    return "\n".join(
        line for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


class _RunGuiCallVisitor(ast.NodeVisitor):
    """Calls executed by run_gui itself, excluding deferred nested bodies."""

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        self.calls.append(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # A nested callback is defined during run_gui but its body is deferred.
        return

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef


def startup_pet_payload_contract(app_source, setup_source, build_source):
    """Return contract failures; comments and deferred callbacks cannot count."""
    failures = []
    app_tree = ast.parse(app_source)
    run_gui = next(
        (node for node in app_tree.body
         if isinstance(node, ast.FunctionDef) and node.name == "run_gui"),
        None,
    )
    if run_gui is None:
        failures.append("run_gui-missing")
    else:
        visitor = _RunGuiCallVisitor()
        for statement in run_gui.body:
            visitor.visit(statement)

        def named_call(node, name):
            return (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == name)

        seed_lines = []
        discover_lines = []
        for call in visitor.calls:
            if named_call(call, "discover_pets"):
                discover_lines.append((call.lineno, call.col_offset))
            if (named_call(call, "_log_seed_report")
                    and len(call.args) == 1
                    and not call.keywords
                    and named_call(call.args[0], "seed_bundled_pet_assets")
                    and not call.args[0].args
                    and not call.args[0].keywords):
                seed_lines.append((call.lineno, call.col_offset))
        if len(seed_lines) != 1:
            failures.append("startup-seed-call-count")
        if not discover_lines:
            failures.append("startup-discovery-missing")
        if (len(seed_lines) == 1 and discover_lines
                and not seed_lines[0] < min(discover_lines)):
            failures.append("startup-seed-after-discovery")

    setup_tree = ast.parse(setup_source)
    setup_call = next(
        (node for node in ast.walk(setup_tree)
         if isinstance(node, ast.Call)
         and isinstance(node.func, ast.Name)
         and node.func.id == "setup"),
        None,
    )

    def dict_value(node, key):
        if not isinstance(node, ast.Dict):
            return None
        for k, value in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == key:
                return value
        return None

    options = None
    if setup_call is not None:
        options = next((kw.value for kw in setup_call.keywords
                        if kw.arg == "options"), None)
    py2app = dict_value(options, "py2app")
    resources = dict_value(py2app, "resources")
    declared = (isinstance(resources, (ast.List, ast.Tuple))
                and any(isinstance(item, ast.Constant)
                        and item.value == ".claude_pet"
                        for item in resources.elts))
    if not declared:
        failures.append("py2app-payload-missing")

    build = operational_zsh(extract_zsh_function(build_source, "build"))
    build_body = operational_zsh(
        extract_zsh_function(build_source, "build_body"))
    wrapper_calls = re.findall(r"(?m)^\s*if build_body; then\s*$", build)
    payload_calls = re.findall(
        r'(?m)^\s*if ! copy_pet_assets "\$APP"; then\s*$', build_body)
    if len(wrapper_calls) != 1 or len(payload_calls) != 1:
        failures.append("manual-build-payload-missing")
    return failures


def manual_update_refresh_contract(script):
    """Whether the public update path stages and verifies bundled pets."""
    public = operational_zsh(extract_zsh_case_arm(script, "update"))
    internal = operational_zsh(extract_zsh_case_arm(script, "__update_txn"))
    update_fn = operational_zsh(extract_zsh_function(script, "update_installed"))

    if public.count('run_under_update_lock "$DEST" __update_txn') != 1:
        return False
    if 'update_installed "$DEST" || exit 1' not in internal:
        return False

    required = (
        '/usr/bin/ditto "$dest" "$stage"',
        'copy_pet_assets "$stage"',
        'verify_pet_payload.py',
        '"$stage/Contents/Resources/.claude_pet" --quiet',
        "stop_pet",
    )
    try:
        positions = [update_fn.index(token) for token in required]
    except ValueError:
        return False
    return positions == sorted(positions)


class PackagingContractTests(unittest.TestCase):
    def test_startup_seeds_bundled_pets_before_discovery_and_builds_ship_them(self):
        root = Path(__file__).parents[1]
        app_source = (root / "claude_pet.py").read_text()
        setup_source = (root / "setup.py").read_text()
        build_source = (root / "build_app.sh").read_text()
        self.assertEqual(
            startup_pet_payload_contract(
                app_source, setup_source, build_source),
            [],
            "bundled pets are not seeded before startup discovery or are not "
            "declared by both build paths",
        )

        seed_line = "    _log_seed_report(seed_bundled_pet_assets())\n"
        discover_line = "    pet_list = discover_pets()\n"
        self.assertEqual(app_source.count(seed_line), 1)
        self.assertGreaterEqual(app_source.count(discover_line), 1)
        removed = app_source.replace(seed_line, "", 1)
        moved = app_source.replace(seed_line, "", 1).replace(
            discover_line, discover_line + seed_line, 1)
        self.assertIn(
            "startup-seed-call-count",
            startup_pet_payload_contract(removed, setup_source, build_source),
        )
        self.assertIn(
            "startup-seed-after-discovery",
            startup_pet_payload_contract(moved, setup_source, build_source),
        )

        setup_mutant = setup_source.replace(
            '"resources": ["frames", ".claude_pet"],',
            '"resources": ["frames"],',
            1,
        )
        self.assertNotEqual(setup_mutant, setup_source)
        self.assertIn(
            "py2app-payload-missing",
            startup_pet_payload_contract(app_source, setup_mutant, build_source),
        )

        build_needle = 'copy_pet_assets "$APP"'
        self.assertEqual(build_source.count(build_needle), 1)
        build_mutant = build_source.replace(
            build_needle, "true # omitted bundled-pet copy", 1)
        self.assertIn(
            "manual-build-payload-missing",
            startup_pet_payload_contract(app_source, setup_source, build_mutant),
        )

    def test_manual_update_refreshes_bundled_pet_resources(self):
        script = (Path(__file__).parents[1] / "build_app.sh").read_text()
        self.assertTrue(
            manual_update_refresh_contract(script),
            "the public update wrapper no longer reaches a transaction that "
            "stages and verifies bundled pet assets before stopping the app",
        )

        # Mutation control: a comment mentioning `.claude_pet`, and even the
        # later verifier, must not make a missing copy step look covered.
        needle = 'copy_pet_assets "$stage"'
        self.assertEqual(script.count(needle), 1,
                         "mutation seam drifted; expected one operational copy")
        mutant = script.replace(needle, "true # bundled-pet copy removed", 1)
        self.assertFalse(
            manual_update_refresh_contract(mutant),
            "the packaging contract accepted an update transaction that never "
            "copies the bundled pet payload",
        )

    def test_manual_bundle_versions_are_not_hard_coded(self):
        script = (Path(__file__).parents[1] / "build_app.sh").read_text()
        self.assertNotIn(
            "<key>CFBundleVersion</key><string>1.0</string>", script
        )
        self.assertNotIn(
            "<key>CFBundleShortVersionString</key><string>1.0</string>", script
        )
        self.assertIn("APP_VERSION", script)

    def test_readmes_do_not_offer_a_recursive_overwrite_command(self):
        root = Path(__file__).parents[1] / ".claude_pet"
        for readme in root.glob("README*.md"):
            with self.subTest(readme=readme.name):
                text = readme.read_text()
                self.assertNotIn("cp -R dog fox scorpion elephant", text)


if __name__ == "__main__":
    unittest.main()
