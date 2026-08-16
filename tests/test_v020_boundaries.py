#!/usr/bin/env python3
"""v0.20 upgrade-boundary verification — owned by agent `v020-boundary`.

Verification only. This module never edits production code and never touches
the installed bundle; it exercises copies inside a module-owned sandbox.

Ordinary unittest discovery is safe: the current module is imported only after
HOME/TMPDIR/ZDOTDIR have been redirected, and no real-home, installed-app, or
PID sentinel is read. The installed-v0.20 to checkout-v0.21 updater boundary is
a separate, explicitly opted-in class; set
CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1 to run it.
"""

import ast
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALLED_APP = "/Applications/ClaudePet.app"
INSTALLED_SRC = os.path.join(INSTALLED_APP, "Contents/Resources/claude_pet.py")
RUN_LIVE_V020_TO_V021 = (
    os.environ.get("CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES") == "1"
)


# ───────────────────────── module-owned sandbox ─────────────────────────

SANDBOX_HOME = None
claude_pet = None
_MODULE_STATE = {}


def _guard_module_paths():
    bad = []
    for name in ("CONFIG_PATH", "USER_PET_HOME", "USER_PETS_DIR"):
        val = getattr(claude_pet, name)
        if not val.startswith(SANDBOX_HOME):
            bad.append("%s=%s" % (name, val))
    for d in claude_pet.LOG_DIRS:
        if not d.startswith(SANDBOX_HOME):
            bad.append("LOG_DIRS entry %s" % d)
    if bad:
        raise AssertionError("module paths escaped sandbox: %s" % "; ".join(bad))


def _snap_path(path, depth=2):
    """(exists, ino, mtime_ns, size) plus a depth-limited child listing.

    Absence is recorded as None so that *creation* of a missing path is caught,
    not only growth of an existing one.
    """
    try:
        st = os.lstat(path)
    except OSError:
        return None
    node = [st.st_ino, st.st_mtime_ns, st.st_size, stat.S_IFMT(st.st_mode)]
    if stat.S_ISDIR(st.st_mode) and depth > 0:
        kids = []
        try:
            for name in sorted(os.listdir(path)):
                kids.append((name, _snap_path(os.path.join(path, name), depth - 1)))
        except OSError as e:
            kids.append(("<unreadable>", str(e)))
        node.append(kids)
    return node


def setUpModule():
    global SANDBOX_HOME, claude_pet
    root = tempfile.mkdtemp(prefix="claudepet-v020-boundaries-", dir="/tmp")
    home = os.path.join(root, "home")
    tmp = os.path.join(root, "tmp")
    zdot = os.path.join(root, "zdot")
    for path in (home, tmp, zdot):
        os.makedirs(path)
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = tmp
    env_values = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": home,
        "TMPDIR": tmp + os.sep,
        "ZDOTDIR": zdot,
        "CDPATH": "",
        "LANG": "C",
        "LC_ALL": "C",
    }
    if RUN_LIVE_V020_TO_V021:
        env_values["CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES"] = "1"
    env = mock.patch.dict(os.environ, env_values, clear=True)
    env.start()
    try:
        module_name = "_claudepet_v020_boundary_current"
        spec = importlib.util.spec_from_file_location(
            module_name, os.path.join(REPO, "claude_pet.py"))
        if spec is None or spec.loader is None:
            raise AssertionError("could not create an isolated claude_pet module spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        SANDBOX_HOME = home
        claude_pet = module
        claude_pet.UPDATE_LOCK_DIR = os.path.join(
            home, "Library", "Caches", "sandbox.claudepet")
        _guard_module_paths()
    except Exception:
        sys.modules.pop("_claudepet_v020_boundary_current", None)
        env.stop()
        tempfile.tempdir = old_tempdir
        shutil.rmtree(root, ignore_errors=True)
        raise
    _MODULE_STATE.update(root=root, home=home, tmp=tmp, zdot=zdot,
                         env=env, module_name=module_name,
                         old_tempdir=old_tempdir)


def tearDownModule():
    sys.modules.pop(_MODULE_STATE.get("module_name"), None)
    env = _MODULE_STATE.get("env")
    if env is not None:
        env.stop()
    tempfile.tempdir = _MODULE_STATE.get("old_tempdir")
    root = _MODULE_STATE.get("root")
    if root:
        shutil.rmtree(root, ignore_errors=True)
    _MODULE_STATE.clear()


class SentinelCase(unittest.TestCase):
    """Every fixture path is allocated beneath the module sandbox."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b-", dir=_MODULE_STATE["tmp"])
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.assertTrue(self.tmp.startswith(_MODULE_STATE["tmp"] + os.sep),
                        "temp dir escaped the sandbox TMPDIR")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def file_identity(path):
    st = os.lstat(path)
    return (st.st_ino, st.st_mtime_ns, st.st_size, sha(path))


# ═══════════════════════ Boundary 1 — settings ═══════════════════════

_UI_TEXT = {"kw": "auto", "whour": "20", "bud": "0", "key": "",
            "ses": "8", "wk": "60", "op": "15", "cs": "", "cw": "", "cm": ""}


class FakeField:
    def __init__(self, v=""):
        self.v = str(v)

    def stringValue(self):
        return self.v

    def setStringValue_(self, s):
        self.v = str(s)


class FakePopup:
    def __init__(self, idx=0):
        self.idx = idx

    def indexOfSelectedItem(self):
        return self.idx


class FakeCheck:
    def __init__(self, s=1):
        self.s = s

    def state(self):
        return self.s


class FakePanel:
    def __init__(self):
        self.ordered_out = 0
        self.delegate = object()

    def setDelegate_(self, value):
        self.delegate = value

    def orderOut_(self, _):
        self.ordered_out += 1


class FakeTicker:
    def __init__(self):
        self.refreshes = 0

    def refresh_(self, _):
        self.refreshes += 1


class FakeView:
    def __init__(self):
        self.repaints = 0

    def setNeedsDisplay_(self, _):
        self.repaints += 1


def extract_nested_source(path, names):
    """Exact source segment of a nested def, e.g. ['run_gui', 'save_settings']."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    node = ast.parse(src)
    for name in names:
        node = next(n for n in ast.walk(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == name)
    seg = ast.get_source_segment(src, node)
    lines = src.splitlines()[node.lineno - 1:node.end_lineno]
    return textwrap.dedent(seg), node, "\n".join(lines)


class B1Settings(SentinelCase):
    """Boundary 1 — settings in log-estimate (subscription) mode."""

    def setUp(self):
        super().setUp()
        self.cfg_path = os.path.join(self.tmp, ".claude_pet.json")
        self._orig_cfg_path = claude_pet.CONFIG_PATH
        claude_pet.CONFIG_PATH = self.cfg_path
        self.addCleanup(setattr, claude_pet, "CONFIG_PATH", self._orig_cfg_path)
        self._runtime = dict(claude_pet.RUNTIME)
        self.addCleanup(self._restore_runtime)
        # a pre-existing config with keys the settings panel does NOT own
        self.base_disk = {"x": 11, "y": 22, "scale": 0.75, "pet": "dog",
                          "session_limit": 8_000_000, "weekly_limit": 60_000_000,
                          "opus_limit": 15_000_000}
        with open(self.cfg_path, "w") as f:
            json.dump(self.base_disk, f)

    def _restore_runtime(self):
        claude_pet.RUNTIME.clear()
        claude_pet.RUNTIME.update(self._runtime)

    def form(self, **over):
        f = {"pet": "dog", "lang": "en", "mode": "sub", "model_keyword": "auto",
             "weekly_reset_day": None, "weekly_reset_hour": "20",
             "api_budget": "0", "spike_mult": 1.0, "greet": True, "admin_key": "",
             "session_limit_m": "8", "weekly_limit_m": "60", "opus_limit_m": "15",
             "session_pct": "", "weekly_pct": "", "opus_pct": ""}
        f.update(over)
        return f

    # ── (a)+(b) direct limit: validates and reaches cfg/RUNTIME immediately ──
    def test_direct_limit_applies_immediately(self):
        cfg = dict(self.base_disk)
        plan, err = claude_pet.plan_settings_save(cfg, self.form(session_limit_m="12.5"))
        self.assertIsNone(err)
        # 12.5 M tokens: distinct from the prior 8_000_000, from a raw 12.5,
        # and from 12 (truncation) — no rival implementation lands here.
        self.assertEqual(plan["updates"]["session_limit"], 12_500_000)
        ok, merged = claude_pet.apply_settings_plan(plan, cfg,
                                                    apply_fn=claude_pet.apply_config)
        self.assertTrue(ok)
        self.assertEqual(cfg["session_limit"], 12_500_000, "cfg not updated")
        self.assertEqual(claude_pet.RUNTIME["session_limit"], 12_500_000,
                         "RUNTIME not updated")
        with open(self.cfg_path, encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk["session_limit"], 12_500_000, "file not updated")
        # keys the panel does not own survive (lost-update protection)
        for k in ("x", "y", "scale"):
            self.assertEqual(on_disk[k], self.base_disk[k])
        # untouched gauges keep their exact token counts through the M round-trip
        self.assertEqual(on_disk["weekly_limit"], 60_000_000)
        self.assertEqual(on_disk["opus_limit"], 15_000_000)

    # ── (a)+(b) calibration %: back-solves and reaches cfg/RUNTIME ──
    def test_calibration_pct_applies_immediately(self):
        cfg = dict(self.base_disk)
        stats = {"session": {"used": 4_000_000}, "weekly": {"used": 1},
                 "opus": {"used": 1}}
        # direct=1M and pct=25% of used=4M → 16M. Rivals: direct-wins → 1M,
        # ignore-pct → 8M (prior), used*pct → 1M, used → 4M. All distinct.
        plan, err = claude_pet.plan_settings_save(
            cfg, self.form(session_limit_m="1", session_pct="25%"),
            usage_stats=stats)
        self.assertIsNone(err)
        self.assertEqual(plan["updates"]["session_limit"], 16_000_000)
        ok, _ = claude_pet.apply_settings_plan(plan, cfg,
                                               apply_fn=claude_pet.apply_config)
        self.assertTrue(ok)
        self.assertEqual(cfg["session_limit"], 16_000_000)
        self.assertEqual(claude_pet.RUNTIME["session_limit"], 16_000_000)
        with open(self.cfg_path, encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk["session_limit"], 16_000_000)

    # ── (d) an invalid field rejects the WHOLE save, atomically ──
    def test_invalid_input_rejects_whole_save(self):
        cases = [
            ("hour out of range", {"weekly_reset_hour": "25"}),
            ("hour not a number", {"weekly_reset_hour": "eight"}),
            ("negative budget", {"api_budget": "-1"}),
            ("zero limit", {"opus_limit_m": "0"}),
            ("limit with percent sign", {"weekly_limit_m": "60%"}),
            ("pct over 100", {"weekly_pct": "150"}),
            ("pct is bare percent sign", {"opus_pct": "%"}),
            # one valid field alongside an invalid one: nothing may be applied
            ("valid limit + invalid hour",
             {"session_limit_m": "12.5", "weekly_reset_hour": "25"}),
            ("valid limit + invalid other limit",
             {"session_limit_m": "12.5", "opus_limit_m": "-3"}),
        ]
        stats = {"session": {"used": 4_000_000}, "weekly": {"used": 4_000_000},
                 "opus": {"used": 4_000_000}}
        for label, over in cases:
            with self.subTest(label):
                cfg = dict(self.base_disk)
                before_cfg = dict(cfg)
                before_rt = dict(claude_pet.RUNTIME)
                before_file = file_identity(self.cfg_path)
                plan, err = claude_pet.plan_settings_save(cfg, self.form(**over),
                                                          usage_stats=stats)
                self.assertIsNone(plan, "%s produced a plan" % label)
                self.assertTrue(err, "%s produced no error message" % label)
                ok, merged = claude_pet.apply_settings_plan(plan, cfg)
                self.assertFalse(ok)
                self.assertIsNone(merged)
                self.assertEqual(cfg, before_cfg, "cfg mutated by a rejected save")
                self.assertEqual(dict(claude_pet.RUNTIME), before_rt,
                                 "RUNTIME mutated by a rejected save")
                self.assertEqual(file_identity(self.cfg_path), before_file,
                                 "config file changed on a rejected save")
        # Blank direct input is not an invalid number: it means preserve the
        # existing exact-token limit.  Keep this beside the rejected rivals so
        # the boundary cannot drift back to treating blank as zero or error.
        cfg = dict(self.base_disk)
        plan, err = claude_pet.plan_settings_save(
            cfg, self.form(session_limit_m=""), usage_stats=stats)
        self.assertIsNone(err)
        self.assertEqual(
            plan["updates"]["session_limit"],
            self.base_disk["session_limit"],
        )
        # POSITIVE CONTROL — an implementation that refuses everything would pass
        # every subTest above. The same harness with a valid form must go through.
        cfg = dict(self.base_disk)
        before_file = file_identity(self.cfg_path)
        plan, err = claude_pet.plan_settings_save(
            cfg, self.form(session_limit_m="12.5"), usage_stats=stats)
        self.assertIsNone(err)
        ok, _ = claude_pet.apply_settings_plan(plan, cfg,
                                               apply_fn=claude_pet.apply_config)
        self.assertTrue(ok, "positive control: a valid save must succeed")
        self.assertNotEqual(file_identity(self.cfg_path), before_file,
                            "positive control: the config file must change")

    # ── (c) persistence across a real restart (fresh interpreter) ──
    def test_saved_limits_survive_restart(self):
        # use the sandbox HOME path, which is what a restarted app reads
        claude_pet.CONFIG_PATH = os.path.join(SANDBOX_HOME, ".claude_pet.json")
        if os.path.exists(claude_pet.CONFIG_PATH):
            os.remove(claude_pet.CONFIG_PATH)

        # CONTROL: with no config file, a fresh interpreter reports the defaults.
        defaults = self._restart_child()
        self.assertEqual(defaults["session_limit"], 8_000_000)
        self.assertEqual(defaults["weekly_limit"], 60_000_000)

        cfg = {}
        plan, err = claude_pet.plan_settings_save(
            cfg, self.form(session_limit_m="12.5", weekly_limit_m="77",
                           opus_limit_m="3.25", weekly_reset_hour="9",
                           model_keyword="opus"))
        self.assertIsNone(err)
        ok, _ = claude_pet.apply_settings_plan(plan, cfg,
                                               apply_fn=claude_pet.apply_config)
        self.assertTrue(ok)

        after = self._restart_child()
        self.assertEqual(after["session_limit"], 12_500_000)
        self.assertEqual(after["weekly_limit"], 77_000_000)
        self.assertEqual(after["opus_limit"], 3_250_000)
        self.assertEqual(after["weekly_reset_hour"], 9)
        self.assertEqual(after["model_keyword"], "opus")
        os.remove(claude_pet.CONFIG_PATH)

    def _restart_child(self):
        """A fresh interpreter doing exactly what run_gui() does at startup:
        cfg = load_config(); apply_config(cfg)."""
        code = (
            "import sys, json; sys.path.insert(0, %r);\n"
            "import claude_pet as p\n"
            "assert p.CONFIG_PATH.startswith(%r), p.CONFIG_PATH\n"
            "p.apply_config(p.load_config())\n"
            "print(json.dumps({k: p.RUNTIME[k] for k in "
            "('session_limit','weekly_limit','opus_limit','weekly_reset_hour',"
            "'model_keyword')}))\n" % (REPO, SANDBOX_HOME))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                             text=True, env=dict(os.environ), timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    # ── the seam: save_settings goes THROUGH plan/apply, not around ──
    def test_save_settings_uses_the_seam(self):
        _, node, raw = extract_nested_source(claude_pet.__file__,
                                             ["run_gui", "save_settings"])
        calls = [n.func.id for n in ast.walk(node)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("plan_settings_save", calls)
        self.assertIn("apply_settings_plan", calls)
        for around in ("save_config", "merge_config_updates", "prepare_settings_config"):
            self.assertNotIn(around, calls,
                             "save_settings calls %s directly, bypassing the seam"
                             % around)
        # no write to cfg/RUNTIME/state before apply_settings_plan has returned ok
        body = node.body
        apply_idx = next(i for i, s in enumerate(body)
                         if "apply_settings_plan" in ast.dump(s))
        for i, s in enumerate(body[:apply_idx]):
            for n in ast.walk(s):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) \
                        and n.value.id in ("cfg", "RUNTIME", "state") \
                        and isinstance(n.ctx, ast.Store):
                    self.fail("save_settings writes %s[...] before the plan is "
                              "applied (stmt %d)" % (n.value.id, i))
        # the two failure paths return without touching the panel: both `if`
        # statements before the success block end in a bare return.
        guards = [s for s in body[:apply_idx + 2] if isinstance(s, ast.If)]
        self.assertGreaterEqual(len(guards), 2)
        for g in guards[-2:]:
            self.assertTrue(any("settings_error" in ast.dump(x) for x in g.body))
            self.assertIsInstance(g.body[-1], ast.Return)

    # ── executing save_settings itself (widgets faked): state + panel ──
    @staticmethod
    def _install_save_helpers(namespace):
        # save_settings closes over these run_gui helpers in production.  The
        # extracted harness must execute the same definitions, in dependency
        # order, rather than reimplementing their behavior with lambdas.
        _, run_gui, _ = extract_nested_source(claude_pet.__file__, ["run_gui"])
        key_assignment = next(
            node for node in run_gui.body
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "ADV_FIELD_KEYS"))
        namespace["ADV_FIELD_KEYS"] = ast.literal_eval(key_assignment.value)
        for name in ("adv_value", "close_advanced", "close_main_panel"):
            segment, _, _ = extract_nested_source(
                claude_pet.__file__, ["run_gui", name])
            exec(compile(segment, claude_pet.__file__, "exec"), namespace)

    def _run_save_settings(self, ui_text=None, popups=None):
        seg, _, _ = extract_nested_source(claude_pet.__file__,
                                          ["run_gui", "save_settings"])
        ns = dict(claude_pet.__dict__)
        text = dict(_UI_TEXT)
        text.update(ui_text or {})
        pops = {"pet": 0, "lang": 0, "mode": 0, "wreset": 0, "sens": 1}
        pops.update(popups or {})
        panel = FakePanel()
        ui = {"pet_ids": ["dog", "fox"], "panel": panel,
              "greet": FakeCheck(1)}
        for k, v in text.items():
            ui[k] = FakeField(v)
        for k, v in pops.items():
            ui[k] = FakePopup(v)
        cfg = dict(self.base_disk)
        state = {"stats": None, "repaint": False}
        ticker, view = FakeTicker(), FakeView()
        errors = []
        harness = {"ui": ui, "cfg": cfg, "state": state, "ticker": ticker,
                   "view": view, "panel": panel, "errors": errors,
                   "set_pet_calls": []}
        ns.update({
            "ui": ui, "cfg": cfg, "state": state, "ticker": ticker, "view": view,
            "settings_error": lambda msg: errors.append(msg),
            "set_pet": lambda pid: harness["set_pet_calls"].append(pid),
        })
        self._install_save_helpers(ns)
        exec(compile(seg, claude_pet.__file__, "exec"), ns)
        ns["save_settings"]()
        return harness

    def test_save_settings_success_updates_state_and_closes_panel(self):
        h = self._run_save_settings({"ses": "12.5"})
        self.assertEqual(h["errors"], [])
        self.assertEqual(h["cfg"]["session_limit"], 12_500_000)
        self.assertEqual(claude_pet.RUNTIME["session_limit"], 12_500_000)
        self.assertIsNotNone(h["state"]["stats"], "state['stats'] not refreshed")
        self.assertTrue(h["state"]["repaint"])
        self.assertIsNone(h["ui"]["panel"], "panel not released on success")
        self.assertEqual(h["panel"].ordered_out, 1)
        self.assertEqual(h["ticker"].refreshes, 1)
        self.assertEqual([h["ui"][f].stringValue() for f in ("cs", "cw", "cm")],
                         ["", "", ""], "calibration fields not cleared")

    def test_save_settings_failure_keeps_panel_open_and_state_untouched(self):
        before_rt = dict(claude_pet.RUNTIME)
        before_file = file_identity(self.cfg_path)
        h = self._run_save_settings({"ses": "12.5", "whour": "25"})
        self.assertEqual(len(h["errors"]), 1, "no error alert was raised")
        self.assertIs(h["ui"]["panel"], h["panel"], "panel was released on failure")
        self.assertEqual(h["panel"].ordered_out, 0, "panel was closed on failure")
        self.assertIsNone(h["state"]["stats"])
        self.assertFalse(h["state"]["repaint"])
        self.assertEqual(h["cfg"], self.base_disk)
        self.assertEqual(dict(claude_pet.RUNTIME), before_rt)
        self.assertEqual(file_identity(self.cfg_path), before_file)
        self.assertEqual(h["ticker"].refreshes, 0)
        self.assertEqual(h["ui"]["cs"].stringValue(), "")

    def test_mutant_control_for_the_failure_path(self):
        """MUTANT: strip both `return`s from the rejection paths, so a rejected
        save falls through into the success block. The failure test above must
        be able to see that — otherwise it asserts nothing.

        (Removing only the first `return` is NOT observable: apply_settings_plan
        rejects a None plan and the second guard returns anyway. That is
        defence in depth in the production code, and it is why the mutant has
        to remove both.)
        """
        seg, _, _ = extract_nested_source(claude_pet.__file__,
                                          ["run_gui", "save_settings"])
        mutated, n = re.subn(r"\n( +)settings_error\(([^\n]*)\)([^\n]*)\n\1return\n",
                             lambda m: "\n%ssettings_error(%s)%s\n"
                                       % (m.group(1), m.group(2), m.group(3)),
                             seg)
        self.assertEqual(n, 2, "mutant instrument is broken: expected 2 rejection "
                               "paths with a bare return, found %d" % n)
        self.assertNotEqual(mutated, seg)
        ns = dict(claude_pet.__dict__)
        panel = FakePanel()
        ui = {"pet_ids": ["dog"], "panel": panel, "greet": FakeCheck(1)}
        text = dict(_UI_TEXT)
        text["whour"] = "25"                       # same rejected input as above
        for k, v in text.items():
            ui[k] = FakeField(v)
        for k in ("pet", "lang", "mode", "wreset", "sens"):
            ui[k] = FakePopup(0)
        state = {"stats": None, "repaint": False}
        cfg = dict(self.base_disk)
        ns.update({"ui": ui, "cfg": cfg, "state": state,
                   "ticker": FakeTicker(), "view": FakeView(),
                   "settings_error": lambda m: None, "set_pet": lambda p: None})
        self._install_save_helpers(ns)
        exec(compile(mutated, "<mutant>", "exec"), ns)
        ns["save_settings"]()
        # the mutant closes the panel and repaints on a REJECTED save — exactly
        # what test_save_settings_failure_keeps_panel_open asserts must not happen
        self.assertEqual(panel.ordered_out, 1,
                         "the mutant did not change observable behaviour, so the "
                         "failure test above is not discriminating")
        self.assertIsNone(ui["panel"])
        self.assertTrue(state["repaint"])


# ═══════════════════════ Boundary 2 — bundle + seeding ═══════════════════════

def expected_asset_set():
    """Every asset FILE, derived from the module constants, never hardcoded."""
    names = list(claude_pet.BUNDLED_PET_README)
    for pet in claude_pet.BUNDLED_PET_IDS:
        for f in claude_pet.BUNDLED_PET_FILES:
            names.append("pets/%s/%s" % (pet, f))
    return sorted(names)


def expected_report_units():
    """What seed_bundled_pet_assets() reports: READMEs by file, pets by folder."""
    return sorted(list(claude_pet.BUNDLED_PET_README)
                  + ["pets/" + p for p in claude_pet.BUNDLED_PET_IDS])


class B2Bundle(SentinelCase):
    """Boundary 2 — a v0.20-shaped bundle's payload, and missing-only seeding."""

    SRC = os.path.join(REPO, ".claude_pet")

    def test_expected_set_is_derived(self):
        exp = expected_asset_set()
        self.assertEqual(len(exp),
                         len(claude_pet.BUNDLED_PET_README)
                         + len(claude_pet.BUNDLED_PET_IDS)
                         * len(claude_pet.BUNDLED_PET_FILES))
        self.assertEqual(len(exp), len(set(exp)))

    def test_py2app_bundle_carries_every_asset(self):
        bundle = os.path.join(REPO, "dist/ClaudePet.app/Contents/Resources/.claude_pet")
        if not os.path.isdir(bundle):
            self.skipTest("no built bundle at %s" % bundle)
        missing, bad, mismatched = [], [], []
        for rel in expected_asset_set():
            p = os.path.join(bundle, rel)
            if os.path.islink(p):
                bad.append(rel + " (symlink)")
                continue
            if not os.path.isfile(p):
                missing.append(rel)
                continue
            if sha(p) != sha(os.path.join(self.SRC, rel)):
                mismatched.append(rel)
        self.assertEqual(missing, [], "bundle is missing assets")
        self.assertEqual(bad, [], "bundle assets are not regular files")
        self.assertEqual(mismatched, [],
                         "bundle assets differ from the repo source")
        # nothing extra crept in (e.g. .DS_Store)
        found = []
        for root, _dirs, files in os.walk(bundle):
            for f in files:
                found.append(os.path.relpath(os.path.join(root, f), bundle))
        self.assertEqual(sorted(found), expected_asset_set())

    def test_both_build_paths_declare_the_payload(self):
        """Source fact, not an artifact: both builders stage .claude_pet."""
        with open(os.path.join(REPO, "setup.py"), encoding="utf-8") as f:
            setup_src = f.read()
        res = re.search(r'"resources"\s*:\s*\[([^\]]*)\]', setup_src)
        self.assertIsNotNone(res, "py2app resources list not found")
        self.assertIn('".claude_pet"', res.group(1),
                      "py2app would ship no .claude_pet payload")
        with open(os.path.join(REPO, "build_app.sh"), encoding="utf-8") as f:
            build_src = f.read()
        self.assertIn('cp -R .claude_pet', build_src,
                      "build_app.sh stages no .claude_pet payload")
        # informational: what the on-disk artifacts actually contain right now
        for label, p in (("repo-root ClaudePet.app", "ClaudePet.app"),
                         ("dist/ClaudePet.app", "dist/ClaudePet.app")):
            full = os.path.join(REPO, p, "Contents/Resources/.claude_pet")
            sys.stderr.write("[b2] %s has .claude_pet: %s\n"
                             % (label, os.path.isdir(full)))

    # ── seeding ──
    def _seed(self, dest):
        return claude_pet.seed_bundled_pet_assets(source_root=self.SRC,
                                                  dest_root=dest)

    def test_seeding_into_empty_dest_creates_everything(self):
        """POSITIVE CONTROL for the never-clobber tests below."""
        dest = os.path.join(self.tmp, "home", ".claude_pet")
        report = self._seed(dest)
        self.assertEqual(report["errors"], [])
        # The report's public unit is one README file or one atomically
        # published pet directory. Disk completeness is a separate contract
        # and remains checked file-by-file below.
        self.assertEqual(sorted(report["copied"]), expected_report_units())
        for rel in expected_asset_set():
            p = os.path.join(dest, rel)
            self.assertFalse(os.path.islink(p), rel + " is a symlink")
            self.assertTrue(os.path.isfile(p), rel + " missing")
            self.assertEqual(sha(p), sha(os.path.join(self.SRC, rel)),
                             rel + " differs from source")

    def test_seeding_never_clobbers_edited_files(self):
        dest = os.path.join(self.tmp, "home", ".claude_pet")
        os.makedirs(os.path.join(dest, "pets", "dog"))
        edited = {
            os.path.join(dest, "README.md"): b"MY OWN README\n",
            os.path.join(dest, "pets", "dog", "pet.json"):
                b'{"id": "dog", "MINE": true}\n',
        }
        for p, data in edited.items():
            with open(p, "wb") as f:
                f.write(data)
        before = {p: file_identity(p) for p in edited}

        report = self._seed(dest)

        for p, data in edited.items():
            self.assertEqual(file_identity(p), before[p],
                             "seeding modified a user file: %s" % p)
            with open(p, "rb") as f:
                self.assertEqual(f.read(), data)
        # folder-level skip: dog's other files are NOT filled in
        for f in claude_pet.BUNDLED_PET_FILES:
            if f == "pet.json":
                continue
            self.assertFalse(os.path.exists(os.path.join(dest, "pets", "dog", f)),
                             "seeding reached into an existing pet folder")
        # everything absent WAS created, byte-identical
        created = sorted(report["copied"])
        expected_created_units = [r for r in expected_report_units()
                                  if r not in ("pets/dog", "README.md")]
        self.assertEqual(created, expected_created_units)
        expected_created_files = [r for r in expected_asset_set()
                                  if not r.startswith("pets/dog/")
                                  and r != "README.md"]
        for rel in expected_created_files:
            self.assertTrue(os.path.isfile(os.path.join(dest, rel)),
                            "missing file inside a reported pet: %s" % rel)
            self.assertEqual(sha(os.path.join(dest, rel)),
                             sha(os.path.join(self.SRC, rel)))
        self.assertIn("README.md", report["skipped"])
        self.assertIn("pets/dog", report["skipped"])

    def test_seeding_is_idempotent(self):
        dest = os.path.join(self.tmp, "home", ".claude_pet")
        self._seed(dest)
        ident = {rel: file_identity(os.path.join(dest, rel))
                 for rel in expected_asset_set()}
        report = self._seed(dest)
        self.assertEqual(report["copied"], [])
        for rel, was in ident.items():
            self.assertEqual(file_identity(os.path.join(dest, rel)), was,
                             "second seeding rewrote %s" % rel)

    def test_seeding_refuses_a_symlinked_dest_root(self):
        real = os.path.join(self.tmp, "elsewhere")
        os.makedirs(real)
        dest = os.path.join(self.tmp, "link")
        os.symlink(real, dest)
        report = self._seed(dest)
        self.assertIn("dest-root-is-symlink", report["errors"])
        self.assertEqual(os.listdir(real), [], "seeded through a symlink")


# ═════════════ Boundary 3 — installed v0.20 → checkout v0.21 ═════════════

INSTALLED_V020_SOURCE_SHA256 = (
    "d3d65ccd14b0cc88a31909d8dd14c675654e96979629d0d21d2869fb5d81ea4b"
)
V021_ASSET_URL = (
    "https://github.com/uygnoey/claude-pet/releases/download/v0.21/ClaudePet.zip"
)


def _literal_app_version(source_bytes, filename):
    tree = ast.parse(source_bytes.decode("utf-8"), filename=filename)
    values = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "APP_VERSION"
               for target in node.targets):
            values.append(ast.literal_eval(node.value))
    if len(values) != 1 or not isinstance(values[0], str):
        raise AssertionError("%s must have one literal APP_VERSION" % filename)
    return values[0]


def _load_installed_v020(tmp, source_bytes):
    """Import only the SHA-pinned copy written inside the module sandbox."""
    copy = os.path.join(tmp, "v020_claude_pet.py")
    with open(copy, "wb") as f:
        f.write(source_bytes)
    spec = importlib.util.spec_from_file_location("v020_claude_pet", copy)
    if spec is None or spec.loader is None:
        raise AssertionError("could not create installed-v0.20 module spec")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["v020_claude_pet"] = mod
    spec.loader.exec_module(mod)
    return mod


def _tree_fingerprint(root):
    """Content + lstat shape, without following a symlink outside ``root``."""
    rows = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            st = os.lstat(path)
            row = [rel, stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode),
                   st.st_size, st.st_mtime_ns]
            if stat.S_ISREG(st.st_mode):
                row.append(sha(path))
            elif stat.S_ISLNK(st.st_mode):
                row.append(os.readlink(path))
            rows.append(row)
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def _write_macho_arm64(path):
    # Thin little-endian Mach-O: magic, CPU_TYPE_ARM64, CPU subtype 0.
    with open(path, "wb") as f:
        f.write(b"\xcf\xfa\xed\xfe\x0c\x00\x00\x01\x00\x00\x00\x00")
    os.chmod(path, 0o755)


def _make_update_candidate(root, source_bytes, name="ClaudePet.app", version="0.21",
                           marker="signed-v021", main_executable=True):
    app = os.path.join(root, name)
    macos = os.path.join(app, "Contents", "MacOS")
    resources = os.path.join(app, "Contents", "Resources")
    os.makedirs(macos)
    os.makedirs(resources)
    if main_executable:
        _write_macho_arm64(os.path.join(macos, "ClaudePet"))
    _write_macho_arm64(os.path.join(macos, "python"))
    with open(os.path.join(resources, "claude_pet.py"), "wb") as f:
        f.write(source_bytes)
    with open(os.path.join(resources, "signature.marker"), "w", encoding="utf-8") as f:
        f.write(marker)
    plist = {
        "CFBundleExecutable": "ClaudePet",
        "CFBundleIdentifier": "me.yeongyu.claudepet",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
    }
    with open(os.path.join(app, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump(plist, f)
    return app


def _zip_tree(src_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for root, dirs, files in os.walk(src_dir):
            dirs.sort()
            files.sort()
            for name in dirs:
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, src_dir) + "/")
            for name in files:
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, src_dir))
    return zip_path


@unittest.skipUnless(
    RUN_LIVE_V020_TO_V021,
    "live installed-v0.20 to checkout-v0.21 boundary requires "
    "CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1",
)
class B3Updater(SentinelCase):
    """The released v0.20 updater must gate a v0.21 handoff in a sandbox."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(INSTALLED_SRC):
            raise AssertionError("installed source is missing: %s" % INSTALLED_SRC)
        with open(INSTALLED_SRC, "rb") as source:
            installed_bytes = source.read()
        installed_sha = hashlib.sha256(installed_bytes).hexdigest()
        if installed_sha != INSTALLED_V020_SOURCE_SHA256:
            raise AssertionError(
                "installed source is not the reviewed v0.20: %s" % installed_sha)
        checkout_path = os.path.join(REPO, "claude_pet.py")
        with open(checkout_path, "rb") as source:
            cls.checkout_source_bytes = source.read()
        cls.checkout_source_sha = hashlib.sha256(
            cls.checkout_source_bytes).hexdigest()
        checkout_version = _literal_app_version(
            cls.checkout_source_bytes, checkout_path)
        if checkout_version != "0.21":
            raise AssertionError("checkout APP_VERSION is %r, expected '0.21'"
                                 % checkout_version)
        with open(os.path.join(INSTALLED_APP, "Contents", "Info.plist"), "rb") as f:
            installed_plist = plistlib.load(f)
        installed_versions = (
            installed_plist.get("CFBundleShortVersionString"),
            installed_plist.get("CFBundleVersion"),
        )
        if installed_versions != ("0.20", "0.20"):
            raise AssertionError("installed plist versions are %r"
                                 % (installed_versions,))

        cls.real_identities = (
            file_identity(INSTALLED_SRC),
            file_identity(os.path.join(INSTALLED_APP, "Contents", "Info.plist")),
            _snap_path(INSTALLED_APP, depth=2),
        )
        cls.holder = tempfile.mkdtemp(prefix="v020-to-v021-",
                                      dir=_MODULE_STATE["tmp"])
        try:
            cls.v020 = _load_installed_v020(cls.holder, installed_bytes)
            if cls.v020.APP_VERSION != "0.20":
                raise AssertionError("reviewed installed module is not v0.20")
            cls.v020.UPDATE_LOCK_DIR = os.path.join(
                SANDBOX_HOME, "Library", "Caches", "v020-boundary-lock")
            for name in ("CONFIG_PATH", "USER_PET_HOME", "USER_PETS_DIR"):
                if not getattr(cls.v020, name).startswith(SANDBOX_HOME):
                    raise AssertionError("installed module path escaped: %s" % name)
            for path in cls.v020.LOG_DIRS:
                if not path.startswith(SANDBOX_HOME):
                    raise AssertionError("installed LOG_DIRS escaped: %s" % path)
            cls.app_path = os.path.join(cls.holder, "ClaudePet.app")
            shutil.copytree(INSTALLED_APP, cls.app_path, symlinks=True,
                            copy_function=shutil.copy2)
        except Exception:
            sys.modules.pop("v020_claude_pet", None)
            shutil.rmtree(cls.holder, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        identity_error = None
        lock_error = None
        try:
            after = (
                file_identity(INSTALLED_SRC),
                file_identity(os.path.join(
                    INSTALLED_APP, "Contents", "Info.plist")),
                _snap_path(INSTALLED_APP, depth=2),
            )
            if after != cls.real_identities:
                identity_error = "live boundary changed the real installed app"
        finally:
            # _acquire_update_lock caches a directory fd for the process lifetime.
            # This imported copy is short-lived, so it must not retain either the
            # sandbox fd or its deleted path after the class has gone away.
            with cls.v020._LOCK_ROOT_MUTEX:
                lock_fd = cls.v020._LOCK_ROOT.get("fd")
                if lock_fd is not None:
                    try:
                        os.close(lock_fd)
                    except OSError:
                        pass
                cls.v020._LOCK_ROOT["fd"] = None
                cls.v020._LOCK_ROOT["path"] = None
                if cls.v020._LOCK_ROOT != {"path": None, "fd": None}:
                    lock_error = "installed module lock-root cache was not cleared"
            shutil.rmtree(cls.holder, ignore_errors=True)
            sys.modules.pop("v020_claude_pet", None)
        if lock_error:
            raise AssertionError(lock_error)
        if identity_error:
            raise AssertionError(identity_error)

    def setUp(self):
        super().setUp()
        self.archives = {}
        self.assertTrue(self.app_path.startswith(_MODULE_STATE["tmp"] + os.sep))

    def _archive(self, label, **candidate):
        root = os.path.join(self.tmp, "archive-" + label)
        os.makedirs(root)
        _make_update_candidate(root, self.checkout_source_bytes, **candidate)
        path = _zip_tree(root, os.path.join(self.tmp, label + ".zip"))
        self.archives[V021_ASSET_URL] = path
        return V021_ASSET_URL

    def _malformed_archive(self):
        path = os.path.join(self.tmp, "malformed.zip")
        with open(path, "wb") as f:
            f.write(b"not a zip")
        self.archives[V021_ASSET_URL] = path
        return V021_ASSET_URL

    def _call_install(self, url=V021_ASSET_URL, *, asset="ClaudePet.zip",
                      arches=("arm64",), tamper_stage=False):
        downloads = []
        validations = []
        validation_sources = []
        signing = []
        handoffs = []
        unexpected = []
        real_subprocess = self.v020.subprocess
        real_download = self.v020._download_update_zip
        real_validate = self.v020.validate_update_app
        real_signing = self.v020._run_signing_tool

        def inside(path):
            absolute = os.path.abspath(str(path))
            root = os.path.abspath(_MODULE_STATE["root"])
            real = os.path.realpath(absolute)
            real_root = os.path.realpath(root)
            return ((absolute == root or absolute.startswith(root + os.sep))
                    and (real == real_root or real.startswith(real_root + os.sep)))

        def download(source_url, destination):
            downloads.append((str(source_url), str(destination)))
            source = self.archives.get(str(source_url))
            if source is None:
                raise FileNotFoundError(str(source_url))
            if not inside(source) or not inside(destination):
                raise AssertionError("download shim escaped the sandbox")
            shutil.copyfile(source, destination)

        def signing_tool(argv, timeout=60):
            del timeout
            argv = list(argv)
            signing.append(argv)
            tool = argv[0]
            if tool == "/usr/bin/lipo":
                if not inside(argv[-1]):
                    unexpected.append(("lipo-path", argv))
                    return (None, "")
                return (0, "arm64")
            app = str(argv[-1])
            if not inside(app):
                unexpected.append(("signing-path", argv))
                return (None, "")
            marker = os.path.join(app, "Contents", "Resources", "signature.marker")
            if tool == "/usr/bin/codesign":
                try:
                    with open(marker, encoding="utf-8") as f:
                        marker_valid = f.read() == "signed-v021"
                    embedded = os.path.join(
                        app, "Contents", "Resources", "claude_pet.py")
                    source_valid = sha(embedded) == self.checkout_source_sha
                except OSError:
                    marker_valid = source_valid = False
                valid = marker_valid and source_valid
                return (0, "") if valid else (1, "invalid signature")
            if tool == "/usr/sbin/spctl":
                return (0, "origin=Developer ID Application (RXGNVSLYF5)\n")
            if tool == "/usr/bin/xcrun":
                return (0, "The validate action worked")
            unexpected.append(("signing", argv))
            return (None, "")

        def validate(app_path, expect_version, run=None, expect_arches=None):
            validations.append((str(app_path), str(expect_version),
                                tuple(expect_arches or ())))
            if not inside(app_path):
                unexpected.append(("validation-path", str(app_path)))
                return False
            embedded = os.path.join(
                str(app_path), "Contents", "Resources", "claude_pet.py")
            try:
                embedded_sha = sha(embedded)
            except OSError:
                embedded_sha = None
            validation_sources.append(embedded_sha)
            return real_validate(app_path, expect_version, run=run,
                                 expect_arches=expect_arches)

        class SubprocessProxy:
            def run(proxy_self, argv, **kwargs):
                del proxy_self
                argv = list(argv)
                if not argv or argv[0] != "/usr/bin/ditto":
                    unexpected.append(("run", argv))
                    raise AssertionError("only sandbox ditto is allowed")
                extracting = argv[1:3] == ["-x", "-k"] and len(argv) == 5
                copying = len(argv) == 3
                paths = argv[3:5] if extracting else argv[1:3]
                if not (extracting or copying):
                    unexpected.append(("ditto-shape", argv))
                    raise AssertionError("unreviewed ditto command shape")
                if len(paths) != 2 or not all(inside(path) for path in paths):
                    unexpected.append(("ditto-path", argv))
                    raise AssertionError("ditto escaped the sandbox")
                result = real_subprocess.run(argv, **kwargs)
                if tamper_stage and copying:
                    embedded = os.path.join(argv[2], "Contents", "Resources",
                                            "claude_pet.py")
                    with open(embedded, "ab") as f:
                        f.write(b"\n# TAMPERED-AFTER-FIRST-VALIDATION\n")
                return result

            def Popen(proxy_self, argv, **kwargs):
                del proxy_self
                argv = list(argv)
                if (argv[:2] != ["/bin/sh", "-c"] or len(argv) != 3
                        or self.app_path not in argv[2]
                        or INSTALLED_APP in argv[2]):
                    unexpected.append(("handoff", argv))
                handoffs.append((argv, dict(kwargs)))
                return object()

            def __getattr__(proxy_self, name):
                del proxy_self
                return getattr(real_subprocess, name)

        before = _tree_fingerprint(self.app_path)
        self.v020._download_update_zip = download
        self.v020._run_signing_tool = signing_tool
        self.v020.validate_update_app = validate
        self.v020.subprocess = SubprocessProxy()
        try:
            result = self.v020.install_github_update(
                url, app_path=self.app_path, expect_version="0.21",
                expect_arches=arches, expect_asset=asset)
        finally:
            self.v020.subprocess = real_subprocess
            self.v020.validate_update_app = real_validate
            self.v020._run_signing_tool = real_signing
            self.v020._download_update_zip = real_download
        self.assertEqual(_tree_fingerprint(self.app_path), before,
                         "captured handoff changed the sandbox installed copy")
        self.assertEqual(unexpected, [], "harness saw an unapproved tool call")
        if tamper_stage:
            self.assertEqual(len(validation_sources), 2)
            self.assertEqual(validation_sources[0], self.checkout_source_sha)
            self.assertNotEqual(validation_sources[1], self.checkout_source_sha)
        else:
            self.assertTrue(
                all(value == self.checkout_source_sha
                    for value in validation_sources),
                "candidate validation did not inspect the frozen checkout source")
        return result, downloads, validations, signing, handoffs

    def test_github_choice_binds_v021_tag_asset_and_arch_without_network(self):
        import platform

        api_url = (
            "https://api.github.com/repos/uygnoey/claude-pet/releases/latest"
        )
        real_urlopen = self.v020.urllib.request.urlopen
        real_machine = platform.machine
        absent = object()
        old_choice = self.v020._upd_cache.get("choice", absent)

        class Response:
            def __init__(self, payload):
                self.payload = json.dumps(payload).encode("utf-8")

            def read(self):
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, _type, _value, _traceback):
                return False

        def check(payload):
            calls = []

            def urlopen(request, timeout=0):
                calls.append((request.full_url, timeout))
                return Response(payload)

            try:
                with mock.patch.object(
                        self.v020.urllib.request, "urlopen", side_effect=urlopen), \
                     mock.patch.object(platform, "machine", return_value="arm64"):
                    result = self.v020.check_github_update()
                    choice = self.v020._upd_cache.get("choice")
            finally:
                self.assertIs(self.v020.urllib.request.urlopen, real_urlopen)
                self.assertIs(platform.machine, real_machine)
            self.assertEqual(calls, [(api_url, 10)])
            return result, choice

        try:
            result, choice = check({
                "tag_name": "v0.21",
                "assets": [{
                    "name": "ClaudePet.zip",
                    "browser_download_url": V021_ASSET_URL,
                }],
            })
            self.assertEqual(result, ("update", "0.21", V021_ASSET_URL))
            self.assertEqual(choice, {
                "asset": "claudepet.zip",
                "arch": "arm64",
                "url": V021_ASSET_URL,
                "tag": "0.21",
            })

            with self.subTest("current release is not offered"):
                result, choice = check({
                    "tag_name": "v0.20",
                    "assets": [{
                        "name": "ClaudePet.zip",
                        "browser_download_url": V021_ASSET_URL,
                    }],
                })
                self.assertEqual(result, ("current", None, None))
                self.assertIsNone(choice)

            with self.subTest("missing canonical asset fails closed"):
                result, choice = check({
                    "tag_name": "v0.21",
                    "assets": [{
                        "name": "diagnostics.zip",
                        "browser_download_url": (
                            "https://github.com/uygnoey/claude-pet/releases/"
                            "download/v0.21/diagnostics.zip"
                        ),
                    }],
                })
                self.assertEqual(result, ("failed", None, None))
                self.assertIsNone(choice)
        finally:
            if old_choice is absent:
                self.v020._upd_cache.pop("choice", None)
            else:
                self.v020._upd_cache["choice"] = old_choice

    def test_well_formed_v021_reaches_one_sandbox_handoff(self):
        url = self._archive("good")
        result, downloads, validations, _signing, handoffs = self._call_install(url)
        self.assertTrue(result)
        self.assertEqual(len(downloads), 1)
        self.assertEqual(len(validations), 2,
                         "extracted and staged apps were not both validated")
        self.assertEqual([item[1:] for item in validations],
                         [("0.21", ("arm64",)), ("0.21", ("arm64",))])
        self.assertNotEqual(validations[0][0], validations[1][0])
        self.assertEqual(len(handoffs), 1)
        argv, kwargs = handoffs[0]
        self.assertEqual(argv[:2], ["/bin/sh", "-c"])
        self.assertEqual(len(argv), 3)
        self.assertIn(self.app_path, argv[2])
        self.assertNotIn(INSTALLED_APP, argv[2])
        self.assertEqual(len(kwargs.get("pass_fds", ())), 1)

    def test_invalid_candidates_are_refused_before_handoff(self):
        cases = [
            ("binding mismatch", lambda: self._archive("binding"),
             {"arches": ("x86_64",)}, 0),
            ("malformed archive", self._malformed_archive, {}, 0),
            ("missing archive", lambda: V021_ASSET_URL, {}, 0),
            ("wrong bundle name", lambda: self._archive(
                "wrong-name", name="Something.app"), {}, 0),
            ("version downgrade", lambda: self._archive(
                "downgrade", version="0.20"), {}, 1),
            ("tampered candidate", lambda: self._archive(
                "tampered", marker="TAMPERED"), {}, 1),
            ("missing executable", lambda: self._archive(
                "no-executable", main_executable=False), {}, 1),
            ("tampered staged copy", lambda: self._archive("stage-tamper"),
             {"tamper_stage": True}, 2),
        ]
        for label, prepare, kwargs, expected_validations in cases:
            with self.subTest(label):
                self.archives.clear()
                url = prepare()
                result, downloads, validations, _signing, handoffs = self._call_install(
                    url, **kwargs)
                self.assertFalse(result, "%s was accepted" % label)
                self.assertEqual(handoffs, [], "%s scheduled a handoff" % label)
                self.assertEqual(len(validations), expected_validations,
                                 "%s missed its intended rejection seam" % label)
                if label == "binding mismatch":
                    self.assertEqual(downloads, [],
                                     "binding mismatch reached the downloader")


if __name__ == "__main__":
    unittest.main(verbosity=2)
