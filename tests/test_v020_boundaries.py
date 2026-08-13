#!/usr/bin/env python3
"""v0.20 upgrade-boundary verification — owned by agent `v020-boundary`.

Verification only. This module never edits production code and never touches
the installed bundle; it exercises copies inside a module-owned sandbox.

Ordinary unittest discovery is safe: the current module is imported only after
HOME/TMPDIR/ZDOTDIR have been redirected, and no real-home, installed-app, or
PID sentinel is read. The historical live-v0.19 checks are a separate,
explicitly opted-in class; set CLAUDEPET_RUN_LIVE_V019_BOUNDARIES=1 to run them.
"""

import ast
import hashlib
import importlib.util
import io
import json
import os
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
RUN_LIVE_V019 = os.environ.get("CLAUDEPET_RUN_LIVE_V019_BOUNDARIES") == "1"


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
    if RUN_LIVE_V019:
        env_values["CLAUDEPET_RUN_LIVE_V019_BOUNDARIES"] = "1"
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
            ("empty limit", {"session_limit_m": ""}),
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


# ═══════════════════════ Boundary 3 — the v0.19 updater ═══════════════════════

def load_installed_v019(tmp):
    """Import a COPY of the installed v0.19 module. Never the original."""
    import importlib.util
    copy = os.path.join(tmp, "v019_claude_pet.py")
    shutil.copy2(INSTALLED_SRC, copy)
    spec = importlib.util.spec_from_file_location("v019_claude_pet", copy)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["v019_claude_pet"] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeNSBundle:
    path = None

    @classmethod
    def mainBundle(cls):
        return cls

    @classmethod
    def bundlePath(cls):
        return cls.path


class FakeFoundation:
    NSBundle = FakeNSBundle


def make_app(root, name="ClaudePet.app", marker="new", version="0.20",
             broken=False):
    app = os.path.join(root, name)
    os.makedirs(os.path.join(app, "Contents", "MacOS"), exist_ok=True)
    os.makedirs(os.path.join(app, "Contents", "Resources"), exist_ok=True)
    with open(os.path.join(app, "Contents", "Resources", "marker"), "w") as f:
        f.write(marker)
    if not broken:
        exe = os.path.join(app, "Contents", "MacOS", "ClaudePet")
        with open(exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(exe, 0o755)
    plist = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
             '"-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/'
             'PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
             '<key>CFBundleExecutable</key><string>ClaudePet</string>'
             '<key>CFBundleIdentifier</key>'
             '<string>sandbox.v020boundary.test</string>'
             '<key>CFBundleShortVersionString</key><string>%s</string>'
             '</dict></plist>\n' % version)
    with open(os.path.join(app, "Contents", "Info.plist"), "w") as f:
        f.write(plist)
    return app


def zip_tree(src_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w") as z:
        for root, dirs, files in os.walk(src_dir):
            for d in dirs:
                p = os.path.join(root, d)
                z.write(p, os.path.relpath(p, src_dir) + "/")
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, src_dir))
    return zip_path


@unittest.skipUnless(
    RUN_LIVE_V019,
    "live installed-v0.19 boundary requires "
    "CLAUDEPET_RUN_LIVE_V019_BOUNDARIES=1",
)
class B3Updater(SentinelCase):
    """Boundary 3 — what the ALREADY-INSTALLED v0.19 updater actually does."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(INSTALLED_SRC):
            raise unittest.SkipTest("no installed v0.19 source at %s" % INSTALLED_SRC)
        cls.holder = tempfile.mkdtemp(prefix="v019-", dir=_MODULE_STATE["tmp"])
        cls.v019 = load_installed_v019(cls.holder)
        import inspect
        sys.stderr.write("\n[b3] module under test: %s\n" % cls.v019.__file__)
        sys.stderr.write("[b3] APP_VERSION=%r\n" % cls.v019.APP_VERSION)
        sys.stderr.write("[b3] install_github_update source:\n%s\n"
                         % inspect.getsource(cls.v019.install_github_update))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.holder, ignore_errors=True)
        sys.modules.pop("v019_claude_pet", None)

    def setUp(self):
        super().setUp()
        self.assertEqual(self.v019.APP_VERSION, "0.19")
        # the "installed" app this test may destroy: a copy, in the sandbox
        self.app_path = make_app(self.tmp, marker="old", version="0.19")
        self.assertTrue(self.app_path.startswith(self.tmp))

    def _call_install(self, zip_url, app_path=None):
        """Run v0.19 with real extraction and only the swap Popen captured."""
        scheduled_swaps = []

        class P:
            def __init__(self, args, **kw):
                scheduled_swaps.append((args, kw))

        class SubprocessProxy:
            """Delegate extraction to the real module without patching it globally."""

            Popen = P

            def __getattr__(self, name):
                return getattr(real_subprocess, name)

        FakeNSBundle.path = self.app_path if app_path is None else app_path
        orig_foundation = sys.modules.get("Foundation")
        real_subprocess = self.v019.subprocess
        sys.modules["Foundation"] = FakeFoundation
        self.v019.subprocess = SubprocessProxy()
        try:
            rv = self.v019.install_github_update(zip_url)
        finally:
            self.v019.subprocess = real_subprocess
            if orig_foundation is None:
                sys.modules.pop("Foundation", None)
            else:
                sys.modules["Foundation"] = orig_foundation
        return rv, scheduled_swaps

    def _zip_url(self, fixture_name, **app_kwargs):
        stage = os.path.join(self.tmp, "stage-" + fixture_name)
        os.makedirs(stage, exist_ok=True)
        make_app(stage, **app_kwargs)
        zp = zip_tree(stage, os.path.join(self.tmp, fixture_name + ".zip"))
        return "file://" + zp, zp

    # ── harness controls first: prove the instrument is live ──
    def test_control_good_zip_is_accepted(self):
        url, _ = self._zip_url("good")
        rv, calls = self._call_install(url)
        self.assertTrue(rv, "v0.19 rejected a well-formed update (harness broken?)")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], "/bin/sh")

    def test_control_non_app_bundle_path_is_refused(self):
        url, _ = self._zip_url("good2")
        rv, calls = self._call_install(url, app_path=os.path.join(self.tmp, "notanapp"))
        self.assertFalse(rv)
        self.assertEqual(calls, [], "swap was scheduled for a non-.app path")

    # ── what v0.19 refuses ──
    def test_refusals_happen_before_anything_is_swapped(self):
        before = _snap_path(self.app_path, depth=3)
        cases = []

        # (1) archive contains no top-level ClaudePet.app
        url, _ = self._zip_url("wrongname", name="Something.app")
        cases.append(("wrong bundle name", url))

        # (2) not a zip at all
        junk = os.path.join(self.tmp, "junk.zip")
        with open(junk, "w") as f:
            f.write("not a zip")
        cases.append(("corrupt archive", "file://" + junk))

        # (3) the URL does not resolve
        cases.append(("missing file", "file://" + os.path.join(self.tmp, "nope.zip")))

        for label, url in cases:
            with self.subTest(label):
                rv, calls = self._call_install(url)
                self.assertFalse(rv, "%s was accepted" % label)
                self.assertEqual(calls, [], "%s scheduled a swap" % label)
                self.assertEqual(_snap_path(self.app_path, depth=3), before,
                                 "%s touched the installed bundle" % label)

    def test_v019_accepts_bundles_it_cannot_validate(self):
        """These are the ones it does NOT refuse. Recorded as behaviour."""
        accepted = []
        for label, kw in (("no executable, no Resources", dict(broken=True)),
                          ("version downgrade to 0.01", dict(version="0.01")),
                          ("tampered payload", dict(marker="TAMPERED"))):
            url, _ = self._zip_url(label.replace(" ", "_").replace(",", ""), **kw)
            rv, calls = self._call_install(url)
            accepted.append((label, bool(rv), len(calls)))
        sys.stderr.write("\n[b3] v0.19 acceptance: %r\n" % (accepted,))
        for label, rv, n in accepted:
            self.assertTrue(rv, label)
            self.assertEqual(n, 1, label)

    def test_v019_swap_script_has_no_verification_or_rollback(self):
        url, _ = self._zip_url("shape")
        rv, calls = self._call_install(url)
        self.assertTrue(rv)
        script = calls[0][0][2]
        sys.stderr.write("\n[b3] swap script: %s\n" % script)
        self.assertIn("rm -rf", script)
        self.assertIn("/usr/bin/ditto", script)
        # destructive first, no copy of the old bundle kept anywhere
        self.assertLess(script.index("rm -rf"), script.index("/usr/bin/ditto"))
        for token in ("||", "&&", "if ", "cp -R", ".bak", "mv "):
            self.assertNotIn(token, script,
                             "unexpected control flow/backup token %r" % token)

    def test_v019_install_destroys_the_old_app_with_no_rollback(self):
        """Run the captured script verbatim, with a failing launch."""
        url, _ = self._zip_url("real", marker="new", broken=True)
        rv, calls = self._call_install(url)
        self.assertTrue(rv)
        script = calls[0][0][2]

        # shim `open`/`xattr` (the script calls them unqualified; ditto is
        # absolute and stays real). `open` exits 1 = the new app fails to launch.
        binn = os.path.join(self.tmp, "bin")
        os.makedirs(binn, exist_ok=True)
        log = os.path.join(self.tmp, "open.log")
        for name, rc in (("open", 1), ("xattr", 0)):
            p = os.path.join(binn, name)
            with open(p, "w") as f:
                f.write('#!/bin/sh\necho "%s $@" >> %s\nexit %d\n' % (name, log, rc))
            os.chmod(p, 0o755)

        old_marker = os.path.join(self.app_path, "Contents/Resources/marker")
        with open(old_marker, encoding="utf-8") as f:
            self.assertEqual(f.read(), "old")
        env = {"PATH": binn + ":/usr/bin:/bin", "HOME": os.environ["HOME"],
               "TMPDIR": os.environ["TMPDIR"], "ZDOTDIR": os.environ["ZDOTDIR"],
               "CDPATH": ""}
        out = subprocess.run(["/bin/sh", "-c", script], env=env,
                             capture_output=True, text=True, timeout=120)
        sys.stderr.write("[b3] script rc=%d err=%s\n" % (out.returncode, out.stderr))

        # the launch step ran and failed — and nothing reacted to it
        self.assertTrue(os.path.exists(log), "the shimmed `open` never ran")
        with open(log, encoding="utf-8") as f:
            self.assertIn("open ", f.read())
        # the swap happened: the new (broken) bundle is now installed
        with open(old_marker, encoding="utf-8") as f:
            self.assertEqual(f.read(), "new",
                             "the swap did not happen; this test proves nothing")
        self.assertFalse(os.path.exists(
            os.path.join(self.app_path, "Contents/MacOS/ClaudePet")),
            "the installed app has an executable; the fixture is not broken")
        # no rollback, and no backup of the old bundle anywhere in the sandbox
        leftovers = []
        for root, dirs, files in os.walk(self.tmp):
            for f in files:
                p = os.path.join(root, f)
                if p == old_marker:
                    continue
                try:
                    with open(p, encoding="utf-8") as source:
                        prefix = source.read(16)
                    if prefix == "old":
                        leftovers.append(p)
                except Exception:
                    pass
        self.assertEqual(leftovers, [],
                         "a copy of the old bundle survived: %r" % leftovers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
