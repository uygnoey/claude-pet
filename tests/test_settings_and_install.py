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
            (direct if direct is not None else
             {"session": "12.345678", "weekly": "98.765432", "opus": "23.456789"}),
            (calibration if calibration is not None else
             {"session": "", "weekly": "", "opus": ""}),
            stats if stats is not None else usage_stats(),
        )
        self.assertEqual(base, before, "the validator must not mutate live config")
        return candidate, error

    @staticmethod
    def _open_settings_ast():
        tree = ast.parse(inspect.getsource(claude_pet.run_gui))
        matches = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "open_settings"
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"run_gui defines {len(matches)} open_settings functions, expected one"
            )
        return tree, matches[0]

    @staticmethod
    def _name_assignments(scope):
        result = {}
        for node in ast.walk(scope):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                result[node.targets[0].id] = node
        return result

    @classmethod
    def _boolean_setter_names(cls, scope, setter, value):
        """Names that an actual setter call sets, including tuple/list loops."""
        assignments = cls._name_assignments(scope)

        def literal_names(node, resolving=()):
            if isinstance(node, ast.Name):
                if node.id in assignments and node.id not in resolving:
                    return literal_names(
                        assignments[node.id].value, resolving + (node.id,)
                    )
                return {node.id}
            if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                result = set()
                for item in node.elts:
                    result.update(literal_names(item, resolving))
                return result
            return set()

        names = set()
        for call in (n for n in ast.walk(scope) if isinstance(n, ast.Call)):
            if (isinstance(call.func, ast.Attribute)
                    and call.func.attr == setter
                    and isinstance(call.func.value, ast.Name)
                    and len(call.args) == 1
                    and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value is value):
                names.add(call.func.value.id)
        for loop in (n for n in ast.walk(scope) if isinstance(n, ast.For)):
            if not isinstance(loop.target, ast.Name):
                continue
            loop_var = loop.target.id
            sets_value = any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == setter
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == loop_var
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value is value
                for statement in loop.body
                for call in ast.walk(statement)
                if isinstance(call, ast.Call)
            )
            if sets_value:
                names.update(literal_names(loop.iter))
        return names

    @staticmethod
    def _local_nodes(scope):
        """Walk executable nodes in one function without entering nested scopes."""
        def descend(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef, ast.Lambda)):
                return
            yield node
            for child in ast.iter_child_nodes(node):
                yield from descend(child)

        for statement in scope.body:
            yield from descend(statement)

    @classmethod
    def _local_name_assignments(cls, scope):
        result = {}
        for node in cls._local_nodes(scope):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                result[node.targets[0].id] = node
        return result

    @staticmethod
    def _translated_keys(scope):
        return {
            call.args[0].value
            for call in (node for node in ast.walk(scope)
                         if isinstance(node, ast.Call))
            if (isinstance(call.func, ast.Name) and call.func.id == "t"
                and call.args and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str))
        }

    @classmethod
    def _advanced_panel_creator(cls, tree, open_settings):
        candidates = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node is open_settings:
                continue
            has_panel = any(
                isinstance(child, ast.Name) and child.id == "NSPanel"
                for child in cls._local_nodes(node)
            )
            if has_panel and "s_limit_current" in cls._translated_keys(node):
                candidates.append(node)
        return candidates

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

    def test_blank_limit_and_percentage_fields_preserve_existing_limits_without_usage_scan(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        before = dict(base)
        stats_for = mock.Mock(side_effect=AssertionError(
            "blank settings must not scan log usage"
        ))
        form = self.valid_settings_form(
            session_limit_m="", weekly_limit_m="", opus_limit_m="",
            session_pct="", weekly_pct="", opus_pct="",
        )

        plan, error = claude_pet.plan_settings_save(
            base, form, stats_for=stats_for
        )

        self.assertIsNone(error)
        self.assertIsNotNone(plan)
        self.assertEqual(
            {key: plan["updates"][key] for key in LIMITS}, LIMITS
        )
        self.assertEqual(base, before)
        stats_for.assert_not_called()

        cfg = dict(base)
        merged = {**cfg, **plan["updates"]}
        with mock.patch.object(
            claude_pet, "merge_config_updates", return_value=(True, merged)
        ):
            ok, saved = claude_pet.apply_settings_plan(plan, cfg)
        self.assertTrue(ok)
        self.assertEqual(saved, merged)
        self.assertEqual({key: cfg[key] for key in LIMITS}, LIMITS)

    def test_session_percentage_only_backsolves_session_and_preserves_other_limits(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        before = dict(base)
        stats_for = mock.Mock(return_value=usage_stats(
            session=2_000_000,
            weekly=88_888_888,
            opus=77_777_777,
        ))
        form = self.valid_settings_form(
            session_limit_m="", weekly_limit_m="", opus_limit_m="",
            session_pct="25", weekly_pct="", opus_pct="",
        )

        plan, error = claude_pet.plan_settings_save(
            base, form, stats_for=stats_for
        )

        self.assertIsNone(error)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["updates"]["session_limit"], 8_000_000)
        self.assertEqual(plan["updates"]["weekly_limit"], LIMITS["weekly_limit"])
        self.assertEqual(plan["updates"]["opus_limit"], LIMITS["opus_limit"])
        self.assertEqual(base, before)
        stats_for.assert_called_once()

    def test_zero_percentage_has_a_distinct_actionable_atomic_rejection(self):
        base = {"mode": "sub", "scale": 0.75, **LIMITS}
        cfg = dict(base)
        before = dict(base)
        stats_for = mock.Mock(side_effect=AssertionError(
            "0% is invalid input and must be rejected before a usage scan"
        ))
        form = self.valid_settings_form(
            session_limit_m="", weekly_limit_m="", opus_limit_m="",
            session_pct="0", weekly_pct="", opus_pct="",
        )

        with mock.patch.dict(claude_pet.L, {"lang": "en"}):
            plan, error = claude_pet.plan_settings_save(
                base, form, stats_for=stats_for
            )
            generic_input_error = claude_pet.t(
                "s_err_calib", field=claude_pet.t("s_g_session")
            )
            zero_usage_error = claude_pet.t(
                "s_err_calib_zero", field=claude_pet.t("s_g_session")
            )

        self.assertIsNone(plan)
        self.assertIsInstance(error, str)
        self.assertIn("0%", error)
        self.assertIn("Nothing was saved", error)
        self.assertNotEqual(error, generic_input_error)
        self.assertNotEqual(error, zero_usage_error)
        self.assertEqual(base, before)
        stats_for.assert_not_called()

        merge = mock.Mock(side_effect=AssertionError(
            "a rejected plan must never reach the config writer"
        ))
        with mock.patch.object(claude_pet, "merge_config_updates", merge):
            ok, merged = claude_pet.apply_settings_plan(plan, cfg)
        self.assertFalse(ok)
        self.assertIsNone(merged)
        self.assertEqual(cfg, before)
        merge.assert_not_called()

    def test_blank_limit_fields_do_not_override_environment_fallbacks(self):
        base = {"mode": "sub", "scale": 0.75}
        before = dict(base)
        stats_for = mock.Mock(side_effect=AssertionError(
            "blank settings must not scan log usage"
        ))
        form = self.valid_settings_form(
            session_limit_m="", weekly_limit_m="", opus_limit_m="",
            session_pct="", weekly_pct="", opus_pct="",
        )

        plan, error = claude_pet.plan_settings_save(
            base, form, stats_for=stats_for
        )

        self.assertIsNone(error)
        self.assertIsNotNone(plan)
        for _gauge, config_key in claude_pet.GAUGE_LIMIT_KEYS:
            self.assertNotIn(
                config_key, plan["updates"],
                "a blank field must not turn an environment/default value into "
                "a persisted config override",
            )
        self.assertEqual(base, before)
        stats_for.assert_not_called()

    def test_percentage_fields_are_primary_and_all_limit_inputs_default_blank(self):
        tree, open_settings = self._open_settings_ast()
        assignments = self._local_name_assignments(open_settings)
        percentage_names = ("f_cs", "f_cw", "f_cm")

        # Calibration is the primary path: each percentage input is created
        # directly, before the advanced helper is called, and starts blank.
        for name in percentage_names:
            self.assertIn(name, assignments, f"settings must create {name}")
            call = assignments[name].value
            self.assertIsInstance(call, ast.Call)
            self.assertIsInstance(call.func, ast.Name)
            self.assertEqual(call.func.id, "field")
            self.assertGreaterEqual(len(call.args), 4)
            self.assertIsInstance(
                call.args[3], ast.Constant,
                f"{name} must use a literal blank default",
            )
            self.assertEqual(
                call.args[3].value, "",
                f"{name} must submit blank until the user explicitly types a value",
            )

        # The primary panel keeps its old height budget. The longer exact-mode
        # warning is a real multiline NSTextField, not a clipped one-line label.
        panel_sizes = []
        for node in self._local_nodes(open_settings):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Tuple)
                    and isinstance(node.value, ast.Tuple)):
                continue
            names = [item.id for item in node.targets[0].elts
                     if isinstance(item, ast.Name)]
            if names == ["PWID", "PHT"] and len(node.value.elts) == 2:
                panel_sizes.append(node.value.elts)
        self.assertEqual(len(panel_sizes), 1)
        self.assertTrue(all(isinstance(value, ast.Constant)
                            for value in panel_sizes[0]))
        main_width, main_height = [value.value for value in panel_sizes[0]]
        self.assertEqual(main_width, 420)
        self.assertEqual(
            main_height, 612,
            "separate advanced controls must restore the compact main-panel budget",
        )
        self.assertLessEqual(main_height, 656)

        for lang in claude_pet.SUPPORTED_LANGS:
            self.assertIn("\n", claude_pet.TR[lang]["s_limit_note2"], lang)
        label_helpers = [node for node in ast.walk(open_settings)
                         if isinstance(node, ast.FunctionDef)
                         and node.name == "label"]
        self.assertEqual(len(label_helpers), 1)
        required_setters = {
            "setUsesSingleLineMode_": False,
            "setWraps_": True,
            "setLineBreakMode_": 0,
            "setTruncatesLastVisibleLine_": False,
        }
        observed_setters = {}
        for call in (node for node in ast.walk(label_helpers[0])
                     if isinstance(node, ast.Call)):
            if (isinstance(call.func, ast.Attribute)
                    and call.func.attr in required_setters and call.args
                    and isinstance(call.args[0], ast.Constant)):
                observed_setters[call.func.attr] = call.args[0].value
        self.assertEqual(observed_setters, required_setters)

        # Follow only the top-level numeric y cursor. This is enough to prove
        # that the three notes do not overlap and that the final budget row is
        # still above the fixed save controls; nested helper bodies are ignored.
        y = None
        semantic_rows = {}
        for statement in open_settings.body:
            if (isinstance(statement, ast.Assign)
                    and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == "y"):
                value = statement.value
                if (isinstance(value, ast.BinOp)
                        and isinstance(value.left, ast.Name)
                        and value.left.id == "PHT"
                        and isinstance(value.op, ast.Sub)
                        and isinstance(value.right, ast.Constant)):
                    y = main_height - value.right.value
            elif (isinstance(statement, ast.AugAssign)
                  and isinstance(statement.target, ast.Name)
                  and statement.target.id == "y"
                  and isinstance(statement.op, ast.Sub)
                  and isinstance(statement.value, ast.Constant)):
                y -= statement.value.value
            if y is None or isinstance(statement, (ast.FunctionDef, ast.ClassDef)):
                continue
            for call in (node for node in ast.walk(statement)
                         if isinstance(node, ast.Call)):
                if (isinstance(call.func, ast.Name) and call.func.id == "label"
                        and call.args and isinstance(call.args[0], ast.Call)
                        and isinstance(call.args[0].func, ast.Name)
                        and call.args[0].func.id == "t" and call.args[0].args
                        and isinstance(call.args[0].args[0], ast.Constant)):
                    height = next((kw.value.value for kw in call.keywords
                                   if kw.arg == "h"
                                   and isinstance(kw.value, ast.Constant)), 20)
                    semantic_rows[call.args[0].args[0].value] = (y, height, call)

        note1_y, _note1_h, _note1 = semantic_rows["s_limit_note1"]
        note2_y, note2_h, _note2 = semantic_rows["s_limit_note2"]
        note3_y, note3_h, note3 = semantic_rows["s_limit_note3"]
        budget_y, _budget_h, _budget = semantic_rows["s_budget"]
        self.assertGreaterEqual(note2_h, 52)
        self.assertLessEqual(note2_y + note2_h, note1_y - 4)
        self.assertLessEqual(note3_y + note3_h, note2_y - 4)
        self.assertGreaterEqual(budget_y, 46)

        precedence_words = {
            "en": ("wins", "priority", "precedence"),
            "ko": ("우선",),
            "ja": ("優先",),
            "es": ("manda", "prioridad", "precedencia"),
        }
        for lang in claude_pet.SUPPORTED_LANGS:
            with self.subTest(copy="note3", lang=lang):
                note3_copy = claude_pet.TR[lang]["s_limit_note3"]
                self.assertIn("%", note3_copy)
                self.assertTrue(any(word in note3_copy.lower()
                                    for word in precedence_words[lang]))
                self.assertLessEqual(
                    len(note3_copy), 40,
                    f"{lang} precedence note must fit its 240px allocation",
                )
        for lang in claude_pet.SUPPORTED_LANGS:
            with self.subTest(copy="advanced_button", lang=lang):
                self.assertIn("s_limit_advanced_button", claude_pet.TR[lang])
                self.assertLessEqual(
                    len(claude_pet.TR[lang]["s_limit_advanced_button"]), 20,
                    f"{lang} advanced button title must fit 132px",
                )

        # One real button shares note3's row and sits to its right.
        disclosure = {
            call.func.value.id for call in self._local_nodes(open_settings)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "setTitle_"
                and isinstance(call.func.value, ast.Name) and call.args
                and isinstance(call.args[0], ast.Call)
                and self._translated_keys(call.args[0]) == {
                    "s_limit_advanced_button"})
        }
        self.assertEqual(len(disclosure), 1)
        disclosure_assignment = assignments[next(iter(disclosure))]
        rects = [node for node in ast.walk(disclosure_assignment.value)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "NSMakeRect"]
        self.assertEqual(len(rects), 1)
        button_x, button_y, _button_w, button_h = rects[0].args
        self.assertIsInstance(button_x, ast.Constant)
        self.assertIsInstance(button_h, ast.Constant)
        self.assertGreaterEqual(button_x.value, note3.args[1].value + note3.args[3].value)
        self.assertTrue(
            isinstance(button_y, ast.Name) and button_y.id == "y"
            or (isinstance(button_y, ast.BinOp)
                and isinstance(button_y.left, ast.Name) and button_y.left.id == "y"
                and isinstance(button_y.right, ast.Constant)
                and button_y.right.value <= 3)
        )
        self.assertLessEqual(button_h.value, 24)

        creators = self._advanced_panel_creator(tree, open_settings)
        self.assertEqual(
            len(creators), 1,
            "absolute inputs must live in one separate advanced NSPanel creator",
        )

    def test_absolute_limit_fields_are_collapsed_but_enabled_behind_advanced_disclosure(self):
        tree, open_settings = self._open_settings_ast()
        assignments = self._local_name_assignments(open_settings)
        direct_fields = {"f_ses", "f_wk", "f_op"}
        percentage_fields = {"f_cs", "f_cw", "f_cm"}

        creators = self._advanced_panel_creator(tree, open_settings)
        self.assertEqual(
            len(creators), 1,
            "absolute limit rows must be owned by one separate NSPanel",
        )
        advanced = creators[0]
        advanced_assignments = self._local_name_assignments(advanced)
        helper_functions = {
            node.name: node for node in advanced.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue({"alabel", "afield"} <= helper_functions.keys())
        afield = helper_functions["afield"]
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "setStringValue_" and call.args
            and isinstance(call.args[0], ast.Constant) and call.args[0].value == ""
            for call in ast.walk(afield) if isinstance(call, ast.Call)
        ), "every newly built advanced input must start blank")
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "setEditable_" and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value is False
            for call in ast.walk(helper_functions["alabel"])
            if isinstance(call, ast.Call)
        ), "current-limit text must be rendered by a read-only label")

        row_loops = []
        for loop in (node for node in self._local_nodes(advanced)
                     if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple)):
            rows = []
            for row in loop.iter.elts:
                if not (isinstance(row, ast.Tuple) and len(row.elts) == 2
                        and isinstance(row.elts[0], ast.Constant)
                        and isinstance(row.elts[1], ast.Subscript)
                        and isinstance(row.elts[1].value, ast.Name)
                        and row.elts[1].value.id == "RUNTIME"
                        and isinstance(row.elts[1].slice, ast.Constant)):
                    break
                rows.append((row.elts[0].value, row.elts[1].slice.value))
            if len(rows) == 3:
                row_loops.append((loop, rows))
        self.assertEqual(len(row_loops), 1)
        row_loop, rows = row_loops[0]
        self.assertEqual(rows, [
            ("s_limit_session", "session_limit"),
            ("s_limit_weekly", "weekly_limit"),
            ("s_limit_model", "opus_limit"),
        ])
        row_source = ast.unparse(row_loop).replace("'", '"')
        self.assertIn("made.append(afield(", row_source)
        self.assertIn(
            'alabel(t("s_limit_current", value=fmt_limit_m(tokens))',
            row_source,
        )
        rendered_limit = claude_pet.fmt_limit_m(98_765_432)
        self.assertEqual(rendered_limit, "98.765432")
        self.assertEqual(
            {
                lang: claude_pet.TR[lang]["s_limit_current"].format(
                    value=rendered_limit
                )
                for lang in claude_pet.SUPPORTED_LANGS
            },
            {
                "en": "now: 98.765432M",
                "ko": "현재: 98.765432M",
                "ja": "現在: 98.765432M",
                "es": "ahora: 98.765432M",
            },
            "the exact-token display must survive in every supported locale",
        )
        self.assertFalse(direct_fields & assignments.keys())

        disclosure_receivers = {
            call.func.value.id for call in self._local_nodes(open_settings)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "setAction_"
                and isinstance(call.func.value, ast.Name) and call.args
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value == "openAdvancedLimits:")
        }
        self.assertEqual(len(disclosure_receivers), 1)
        disclosure = next(iter(disclosure_receivers))
        self.assertIn(disclosure, assignments)
        self.assertTrue(
            any(isinstance(node, ast.Name) and node.id == "NSButton"
                for node in ast.walk(assignments[disclosure].value)),
            "the advanced disclosure must be a concrete NSButton",
        )
        control_calls = [call for call in self._local_nodes(open_settings)
                         if isinstance(call, ast.Call)
                         and isinstance(call.func, ast.Attribute)
                         and isinstance(call.func.value, ast.Name)
                         and call.func.value.id == disclosure]
        self.assertTrue(any(call.func.attr == "setTarget_" and call.args
                            and isinstance(call.args[0], ast.Name)
                            and call.args[0].id == "handler"
                            for call in control_calls))
        selectors = [call.args[0].value for call in control_calls
                     if call.func.attr == "setAction_" and call.args
                     and isinstance(call.args[0], ast.Constant)
                     and isinstance(call.args[0].value, str)]
        self.assertEqual(len(selectors), 1)
        handler_name = selectors[0].replace(":", "_")
        handlers = [node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == handler_name]
        self.assertEqual(len(handlers), 1)
        self.assertTrue(any(
            isinstance(call.func, ast.Name) and call.func.id == advanced.name
            for call in self._local_nodes(handlers[0]) if isinstance(call, ast.Call)
        ), "the selector handler must open the advanced panel")

        def ui_get_key(call):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "ui" and call.func.attr == "get"
                    and call.args and isinstance(call.args[0], ast.Constant)):
                return call.args[0].value
            return None

        # Find the advanced panel object and its UI key without prescribing
        # local symbol names.
        panel_vars = [
            name for name, assignment in advanced_assignments.items()
            if any(isinstance(node, ast.Name) and node.id == "NSPanel"
                   for node in ast.walk(assignment.value))
        ]
        self.assertEqual(len(panel_vars), 1)
        panel_var = panel_vars[0]
        panel_rects = [
            node for node in ast.walk(advanced_assignments[panel_var].value)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "NSMakeRect")
        ]
        self.assertEqual(len(panel_rects), 1)
        self.assertGreaterEqual(len(panel_rects[0].args), 4)
        constants = {}
        for node in self._local_nodes(advanced):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    constants[target.id] = node.value.value
                elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for target, value in zip(target.elts, node.value.elts):
                        if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                            constants[target.id] = value.value

        def resolve_constant(node):
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                return constants.get(node.id)
            return None

        def call_dimension(call, helper, position):
            parameter = helper.args.args[position].arg
            keyword = next((item.value for item in call.keywords
                            if item.arg == parameter), None)
            if keyword is not None:
                return resolve_constant(keyword)
            if len(call.args) > position:
                return resolve_constant(call.args[position])
            default_index = position - (
                len(helper.args.args) - len(helper.args.defaults)
            )
            if default_index >= 0:
                return resolve_constant(helper.args.defaults[default_index])
            return None

        panel_width, panel_height = [
            resolve_constant(node) for node in panel_rects[0].args[2:4]
        ]
        self.assertIsNotNone(panel_width)
        self.assertIsNotNone(panel_height)
        loop_calls = [
            node for node in self._local_nodes(row_loop)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in {"alabel", "afield"}
        ]
        row_label_calls = [
            call for call in loop_calls
            if (call.func.id == "alabel" and call.args
                and isinstance(call.args[0], ast.Call)
                and isinstance(call.args[0].func, ast.Name)
                and call.args[0].func.id == "t" and call.args[0].args
                and isinstance(call.args[0].args[0], ast.Name))
        ]
        current_label_calls = [
            call for call in loop_calls
            if (call.func.id == "alabel" and call.args
                and self._translated_keys(call.args[0]) == {"s_limit_current"})
        ]
        field_calls = [call for call in loop_calls if call.func.id == "afield"]
        self.assertEqual(len(row_label_calls), 1)
        self.assertEqual(len(current_label_calls), 1)
        self.assertEqual(len(field_calls), 1)

        row_label = row_label_calls[0]
        current_label = current_label_calls[0]
        input_field = field_calls[0]
        row_x = call_dimension(row_label, helper_functions["alabel"], 1)
        row_w = call_dimension(row_label, helper_functions["alabel"], 3)
        field_x = call_dimension(input_field, helper_functions["afield"], 0)
        field_w = call_dimension(input_field, helper_functions["afield"], 2)
        current_x = call_dimension(current_label, helper_functions["alabel"], 1)
        current_w = call_dimension(current_label, helper_functions["alabel"], 3)
        dimensions = {
            "AW": panel_width,
            "AH": panel_height,
            "row_x": row_x,
            "row_w": row_w,
            "field_x": field_x,
            "field_w": field_w,
            "current_x": current_x,
            "current_w": current_w,
        }
        self.assertTrue(
            all(isinstance(value, (int, float)) for value in dimensions.values()),
            f"advanced-panel geometry must resolve statically: {dimensions}",
        )
        row_gap = field_x - row_x - row_w
        current_gap = current_x - field_x - field_w
        right_margin = panel_width - current_x - current_w
        checks = (
            (panel_width >= 500, f"AW {panel_width} < 500"),
            (panel_height <= 220, f"AH {panel_height} > 220"),
            (row_w >= 170, f"row label width {row_w} < 170"),
            (current_w >= 180, f"current label width {current_w} < 180"),
            (12 <= row_x <= 24, f"left margin {row_x} outside 12..24"),
            (0 <= row_gap <= 24, f"row/input gap {row_gap} outside 0..24"),
            (field_w >= 80, f"input width {field_w} < 80"),
            (0 <= current_gap <= 24,
             f"input/current gap {current_gap} outside 0..24"),
            (12 <= right_margin <= 48,
             f"right margin {right_margin} outside 12..48"),
        )
        violations = [message for passed, message in checks if not passed]
        self.assertFalse(
            violations,
            "advanced-panel width budget clips exact current limits: "
            + "; ".join(violations),
        )
        panel_keys = {
            node.targets[0].slice.value
            for node in ast.walk(advanced)
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "ui"
                and isinstance(node.targets[0].slice, ast.Constant)
                and isinstance(node.value, ast.Name)
                and node.value.id == panel_var)
        }
        self.assertEqual(len(panel_keys), 1)
        panel_key = next(iter(panel_keys))
        panel_calls = [
            call for call in ast.walk(advanced)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == panel_var)
        ]
        self.assertTrue(any(
            call.func.attr == "setTitle_" and call.args
            and self._translated_keys(call.args[0]) == {"s_limit_advanced"}
            for call in panel_calls
        ), "the auxiliary panel keeps the descriptive advanced title")
        self.assertTrue(any(
            call.func.attr == "setHidesOnDeactivate_" and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value is False for call in panel_calls
        ))
        self.assertTrue(any(
            call.func.attr == "setReleasedWhenClosed_" and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value is False for call in panel_calls
        ), "the child must remain alive until its close delegate clears UI refs")
        self.assertTrue(any(
            call.func.attr == "setDelegate_" and call.args
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == "handler" for call in panel_calls
        ))

        existing_assignments = {
            name for name, assignment in advanced_assignments.items()
            if ui_get_key(assignment.value) == panel_key
        }
        reuse_branches = []
        for branch in (node for node in self._local_nodes(advanced)
                       if isinstance(node, ast.If)):
            tested_names = {node.id for node in ast.walk(branch.test)
                            if isinstance(node, ast.Name)}
            inline_lookup = any(
                ui_get_key(call) == panel_key
                for call in ast.walk(branch.test) if isinstance(call, ast.Call)
            )
            if not (tested_names & existing_assignments or inline_lookup):
                continue
            returns = any(isinstance(node, ast.Return)
                          for statement in branch.body for node in ast.walk(statement))
            reopens = any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "makeKeyAndOrderFront_"
                for statement in branch.body for call in ast.walk(statement)
                if isinstance(call, ast.Call)
            )
            if returns and reopens:
                reuse_branches.append(branch)
        self.assertEqual(
            len(reuse_branches), 1,
            "an existing advanced panel must be reopened and returned before allocation",
        )
        parent_assignments = {
            name for name, assignment in advanced_assignments.items()
            if ui_get_key(assignment.value) == "panel"
        }
        self.assertEqual(len(parent_assignments), 1)
        parent_name = next(iter(parent_assignments))
        self.assertTrue(any(
            isinstance(branch.test, ast.UnaryOp)
            and isinstance(branch.test.op, ast.Not)
            and isinstance(branch.test.operand, ast.Name)
            and branch.test.operand.id == parent_name
            and any(isinstance(node, ast.Return)
                    for statement in branch.body for node in ast.walk(statement))
            for branch in self._local_nodes(advanced) if isinstance(branch, ast.If)
        ), "the auxiliary panel must not open without its main parent")
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == parent_name
            and call.func.attr == "addChildWindow_ordered_"
            and call.args and isinstance(call.args[0], ast.Name)
            and call.args[0].id == panel_var
            for call in self._local_nodes(advanced) if isinstance(call, ast.Call)
        ), "a rebuilt advanced panel must be attached to the main panel")

        field_key_assignments = [
            node for node in ast.walk(tree)
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "ADV_FIELD_KEYS"
                and isinstance(node.value, (ast.Tuple, ast.List)))
        ]
        self.assertEqual(len(field_key_assignments), 1)
        field_keys = tuple(
            item.value for item in field_key_assignments[0].value.elts
            if isinstance(item, ast.Constant)
        )
        self.assertEqual(field_keys, ("ses", "wk", "op"))
        publish_loops = []
        for loop in (node for node in self._local_nodes(advanced)
                     if isinstance(node, ast.For) and isinstance(node.iter, ast.Call)):
            if not (isinstance(loop.iter.func, ast.Name)
                    and loop.iter.func.id == "zip" and len(loop.iter.args) == 2
                    and isinstance(loop.iter.args[0], ast.Name)
                    and loop.iter.args[0].id == "ADV_FIELD_KEYS"
                    and isinstance(loop.iter.args[1], ast.Name)
                    and loop.iter.args[1].id == "made"):
                continue
            if any(
                isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "ui"
                for statement in loop.body for node in ast.walk(statement)
            ):
                publish_loops.append(loop)
        self.assertEqual(
            len(publish_loops), 1,
            "the three freshly built fields must publish to the three UI keys",
        )

        def cleared_ui_keys(function):
            cleared = set()
            for node in self._local_nodes(function):
                if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.value, ast.Constant)
                        and node.value.value is None):
                    continue
                target = node.targets[0]
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "ui"
                    and isinstance(target.slice, ast.Constant)):
                    cleared.add(target.slice.value)
            for loop in (node for node in self._local_nodes(function)
                         if isinstance(node, ast.For)):
                if not (isinstance(loop.target, ast.Name)
                        and isinstance(loop.iter, ast.Name)
                        and loop.iter.id == "ADV_FIELD_KEYS"):
                    continue
                if any(
                    isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.value, ast.Constant)
                    and node.value.value is None
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name)
                    and node.targets[0].value.id == "ui"
                    and isinstance(node.targets[0].slice, ast.Name)
                    and node.targets[0].slice.id == loop.target.id
                    for statement in loop.body for node in ast.walk(statement)
                ):
                    cleared.update(field_keys)
            for call in (node for node in self._local_nodes(function)
                         if isinstance(node, ast.Call)):
                if not (isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "ui" and call.func.attr == "update"
                        and call.args and isinstance(call.args[0], ast.Dict)):
                    continue
                for key, value in zip(call.args[0].keys, call.args[0].values):
                    if (isinstance(key, ast.Constant)
                            and isinstance(value, ast.Constant)
                            and value.value is None):
                        cleared.add(key.value)
            return cleared

        lifecycle = [
            function for function in ast.walk(tree)
            if (isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and {panel_key, *field_keys} <= cleared_ui_keys(function)
                and {"orderOut_", "removeChildWindow_"} <= {
                    call.func.attr for call in self._local_nodes(function)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)})
        ]
        self.assertEqual(
            len(lifecycle), 1,
            "one lifecycle helper must hide the panel and clear panel/field refs",
        )
        lifecycle_name = lifecycle[0].name
        child_cleanup = lifecycle[0]
        delegate_none_lines = [
            call.lineno for call in self._local_nodes(child_cleanup)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "setDelegate_" and call.args
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value is None)
        ]
        child_out_lines = [
            call.lineno for call in self._local_nodes(child_cleanup)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "orderOut_")
        ]
        self.assertTrue(delegate_none_lines and child_out_lines)
        self.assertLess(min(delegate_none_lines), min(child_out_lines))

        closing_assignments = []
        for node in self._local_nodes(child_cleanup):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name)
                    and node.targets[0].value.id == "ui"
                    and isinstance(node.targets[0].slice, ast.Constant)
                    and node.targets[0].slice.value == "adv_closing"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, bool)):
                continue
            closing_assignments.append((node.value.value, node.lineno))
        self.assertIn(True, {value for value, _line in closing_assignments})
        self.assertIn(False, {value for value, _line in closing_assignments})
        guard_branches = [
            branch for branch in self._local_nodes(child_cleanup)
            if (isinstance(branch, ast.If)
                and any(ui_get_key(call) == "adv_closing"
                        for call in ast.walk(branch.test)
                        if isinstance(call, ast.Call))
                and any(isinstance(node, ast.Return)
                        for statement in branch.body
                        for node in ast.walk(statement)))
        ]
        self.assertEqual(len(guard_branches), 1)
        self.assertLess(
            min(line for value, line in closing_assignments if value is True),
            min(delegate_none_lines),
        )
        self.assertGreater(
            max(line for value, line in closing_assignments if value is False),
            max(child_out_lines),
        )
        save_functions = [node for node in ast.walk(tree)
                          if isinstance(node, ast.FunctionDef)
                          and node.name == "save_settings"]
        self.assertEqual(len(save_functions), 1)
        save = save_functions[0]

        form_assignments = [
            node for node in self._local_nodes(save)
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "form"
                and isinstance(node.value, ast.Dict))
        ]
        self.assertEqual(len(form_assignments), 1)
        form_values = {
            key.value: value
            for key, value in zip(form_assignments[0].value.keys,
                                  form_assignments[0].value.values)
            if isinstance(key, ast.Constant)
        }
        direct_form_keys = {
            "session_limit_m": "ses",
            "weekly_limit_m": "wk",
            "opus_limit_m": "op",
        }
        value_helper_names = set()
        for form_key, ui_key in direct_form_keys.items():
            self.assertIn(form_key, form_values)
            value = form_values[form_key]
            self.assertIsInstance(value, ast.Call)
            self.assertIsInstance(value.func, ast.Name)
            self.assertEqual(len(value.args), 1)
            self.assertIsInstance(value.args[0], ast.Constant)
            self.assertEqual(value.args[0].value, ui_key)
            value_helper_names.add(value.func.id)
        self.assertEqual(len(value_helper_names), 1)
        value_helper_name = next(iter(value_helper_names))
        value_helpers = [node for node in ast.walk(tree)
                         if isinstance(node, ast.FunctionDef)
                         and node.name == value_helper_name]
        self.assertEqual(len(value_helpers), 1)
        value_helper = value_helpers[0]
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "ui" and call.func.attr == "get"
            for call in ast.walk(value_helper) if isinstance(call, ast.Call)
        ))
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "stringValue"
            for call in ast.walk(value_helper) if isinstance(call, ast.Call)
        ))
        self.assertTrue(any(
            isinstance(node, ast.Constant) and node.value == ""
            for returned in (node for node in ast.walk(value_helper)
                             if isinstance(node, ast.Return))
            for node in ast.walk(returned)
        ), "an unopened advanced panel must submit an empty direct value")

        named_local_functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        def direct_named_calls(scope):
            return {
                call.func.id for call in self._local_nodes(scope)
                if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id in named_local_functions)
            }

        def is_ordered_main_cleanup(scope):
            direct_calls = [
                call for call in self._local_nodes(scope)
                if isinstance(call, ast.Call)
            ]
            child_lines = [call.lineno for call in direct_calls
                           if isinstance(call.func, ast.Name)
                           and call.func.id == lifecycle_name]
            delegate_lines = [call.lineno for call in direct_calls
                              if isinstance(call.func, ast.Attribute)
                              and call.func.attr == "setDelegate_" and call.args
                              and isinstance(call.args[0], ast.Constant)
                              and call.args[0].value is None]
            out_lines = [call.lineno for call in direct_calls
                         if isinstance(call.func, ast.Attribute)
                         and call.func.attr == "orderOut_"]
            return bool(
                child_lines and delegate_lines and out_lines
                and "panel" in cleared_ui_keys(scope)
                and min(child_lines) < min(delegate_lines) < min(out_lines)
            )

        main_cleanup_helpers = {
            name for name, function in named_local_functions.items()
            if is_ordered_main_cleanup(function)
        }
        self.assertEqual(
            len(main_cleanup_helpers), 1,
            "one local helper must clean child then main delegate/window/ref",
        )
        self.assertTrue(
            is_ordered_main_cleanup(save)
            or bool(direct_named_calls(save) & main_cleanup_helpers),
            "save must use the ordered main cleanup directly or through one helper",
        )
        close_handlers = [node for node in ast.walk(tree)
                          if isinstance(node, ast.FunctionDef)
                          and node.name == "windowWillClose_"]
        self.assertEqual(len(close_handlers), 1)
        close_handler = close_handlers[0]

        def branch_ui_keys(branch):
            return {
                ui_get_key(call) for call in ast.walk(branch.test)
                if isinstance(call, ast.Call) and ui_get_key(call) is not None
            }

        close_branches = {
            key: branch
            for branch in ast.walk(close_handler)
            if isinstance(branch, ast.If)
            for key in branch_ui_keys(branch)
            if key in {panel_key, "panel"}
        }
        self.assertEqual(set(close_branches), {panel_key, "panel"})
        for key, branch in close_branches.items():
            compared_object = any(
                (isinstance(call.func, ast.Attribute)
                 and call.func.attr == "object")
                for call in ast.walk(branch.test) if isinstance(call, ast.Call)
            ) or any(
                isinstance(node, ast.Name) and node.id in {
                    name for name, assignment in
                    self._local_name_assignments(close_handler).items()
                    if any(isinstance(call.func, ast.Attribute)
                           and call.func.attr == "object"
                           for call in ast.walk(assignment.value)
                           if isinstance(call, ast.Call))
                }
                for node in ast.walk(branch.test)
            )
            self.assertTrue(
                compared_object,
                f"windowWillClose_ must distinguish the {key} notification object",
            )
            branch_calls = direct_named_calls(branch)
            if key == panel_key:
                self.assertIn(
                    lifecycle_name, branch_calls,
                    "child X must immediately clear the child and field refs",
                )
            else:
                self.assertTrue(
                    is_ordered_main_cleanup(branch)
                    or bool(branch_calls & main_cleanup_helpers),
                    "main X must use the verified child-first main cleanup",
                )
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "setDelegate_" and call.args
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == "handler"
            for call in ast.walk(open_settings) if isinstance(call, ast.Call)
        ), "the main close button must reach windowWillClose_")

        limit_field_names = direct_fields | percentage_fields | {"f"}
        for scope in (open_settings, advanced):
            for call in (node for node in ast.walk(scope)
                         if isinstance(node, ast.Call)):
                if not (isinstance(call.func, ast.Attribute)
                        and call.func.attr == "setEnabled_" and len(call.args) == 1
                        and isinstance(call.args[0], ast.Constant)
                        and call.args[0].value is False):
                    continue
                receiver = call.func.value
                self.assertFalse(
                    isinstance(receiver, ast.Name)
                    and receiver.id in limit_field_names,
                    "calibration and advanced limit fields must not be disabled",
                )

    def test_exact_mode_note_explains_server_calibration_and_estimate_spike_split(self):
        semantic_needles = {
            "en": (("exact",), ("server",), ("calibrat",), ("spike",),
                   ("estimat",), ("limit",)),
            "ko": (("정확",), ("서버",), ("보정",), ("급증",),
                   ("추정",), ("한도",)),
            "ja": (("正確",), ("サーバ",), ("補正",), ("急増",),
                   ("推定",), ("上限",)),
            "es": (("exact",), ("servidor",), ("calibr",), ("pico",),
                   ("estim",), ("límite", "limite")),
        }
        for lang, concepts in semantic_needles.items():
            with self.subTest(lang=lang):
                note = claude_pet.TR[lang]["s_limit_note2"].lower()
                for alternatives in concepts:
                    self.assertTrue(
                        any(needle.lower() in note for needle in alternatives),
                        f"{lang} exact-mode note omits {alternatives!r}: {note!r}",
                    )

    def test_new_usage_settings_locale_keys_exist_in_every_supported_language(self):
        required = {
            "s_calib1", "s_calib2", "s_calib_session",
            "s_calib_weekly_all", "s_calib_weekly_model",
            "s_limit_session", "s_limit_weekly", "s_limit_model",
            "s_limit_note1", "s_limit_note2", "s_limit_note3",
            "s_limit_advanced", "s_limit_advanced_button", "s_limit_current",
            "s_err_calib_zero_pct",
        }
        self.assertEqual(set(claude_pet.SUPPORTED_LANGS), {"en", "ko", "ja", "es"})
        for lang in claude_pet.SUPPORTED_LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(
                    required - set(claude_pet.TR[lang]), set(),
                    f"{lang} is missing new settings copy",
                )

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
        tree = ast.parse(source)
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue({"save_settings", "close_main_panel", "close_advanced"}
                        <= functions.keys())

        def named_call_lines(scope, name):
            return [
                call.lineno for call in self._local_nodes(scope)
                if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == name)
            ]

        save = functions["save_settings"]
        save_order = [
            named_call_lines(save, name)
            for name in ("plan_settings_save", "apply_settings_plan",
                         "commit_refresh_result", "close_main_panel")
        ]
        self.assertTrue(all(len(lines) == 1 for lines in save_order))
        self.assertEqual([lines[0] for lines in save_order],
                         sorted(lines[0] for lines in save_order))

        close_main = functions["close_main_panel"]
        child_lines = named_call_lines(close_main, "close_advanced")
        main_out_lines = [
            call.lineno for call in self._local_nodes(close_main)
            if (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "orderOut_")
        ]
        panel_clear_lines = [
            node.lineno for node in self._local_nodes(close_main)
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "ui"
                and isinstance(node.targets[0].slice, ast.Constant)
                and node.targets[0].slice.value == "panel"
                and isinstance(node.value, ast.Constant)
                and node.value.value is None)
        ]
        self.assertTrue(child_lines and main_out_lines and panel_clear_lines)
        self.assertLess(min(child_lines), min(main_out_lines))
        self.assertLess(min(main_out_lines), min(panel_clear_lines))

        open_settings = functions["open_settings"]
        self.assertTrue(any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "setHidesOnDeactivate_" and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value is False
            for call in self._local_nodes(open_settings)
            if isinstance(call, ast.Call)
        ))


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
            '"resources": ["frames", ".claude_pet", "fonts"],',
            '"resources": ["frames", "fonts"],',
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
