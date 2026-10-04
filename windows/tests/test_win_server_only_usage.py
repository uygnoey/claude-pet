"""Windows parity gates for docs-design/server-only-usage-20261005.md (§8).

Verifier-owned (sou-verify), written before the implementation. AGENTS.md §2 Condition A:
the Developer owns ``windows/claude_pet_win.py`` and ``claude_pet.py`` and must not touch
an assertion, an expected value or a fixture literal here.

Run from the worktree root:

    python3 -m unittest discover -s windows/tests -t . -v

Style follows the other port gates: the port cannot be imported on a host without PySide6,
so everything here reads ``windows/claude_pet_win.py`` by AST. No GUI, no registry, no
network, no real ``~/.claude`` / ``~/.codex``.

The spec (§8): "1–7 을 **똑같이**" — the macOS rules, the macOS core functions, the same
TR keys. What each gate pins, and the wrong port it rules out, is on the gate.
"""

import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PORT = os.path.join(ROOT, "windows", "claude_pet_win.py")
CORE = os.path.join(ROOT, "claude_pet.py")


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _tree(path):
    return ast.parse(_src(path))


def _class(tree, name):
    found = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name]
    return found[0] if found else None


def _method(cls, name):
    if cls is None:
        return None
    found = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name]
    return found[0] if found else None


def _t_keys(node):
    """Keys passed to ``t("…")`` / ``cp.t("…")`` (the port aliases ``t = cp.t``)."""
    out = set()
    for c in ast.walk(node):
        if not (isinstance(c, ast.Call) and c.args and isinstance(c.args[0], ast.Constant)
                and isinstance(c.args[0].value, str)):
            continue
        f = c.func
        if (isinstance(f, ast.Name) and f.id in ("t", "tw")) or \
                (isinstance(f, ast.Attribute) and f.attr == "t"):
            out.add(c.args[0].value)
    return out


def _str_consts(node):
    return {n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _called(node):
    out = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            if isinstance(c.func, ast.Name):
                out.add(c.func.id)
            elif isinstance(c.func, ast.Attribute):
                out.add(c.func.attr)
    return out


def _reach_core(node, depth=2):
    """Names called from a port method, following ``cp.<fn>`` into claude_pet.py."""
    core = {n.name: n for n in _tree(CORE).body if isinstance(n, ast.FunctionDef)}
    seen, frontier = set(), _called(node)
    for _ in range(depth + 1):
        seen |= frontier
        nxt = set()
        for name in frontier:
            if name in core:
                nxt |= _called(core[name]) - seen
        frontier = nxt
    return seen


class WinSettingsDialogParityTests(unittest.TestCase):
    """§2 on Windows: the same two provider sections, no calibration, no advanced window."""

    def setUp(self):
        self.tree = _tree(PORT)

    def test_the_advanced_limits_dialog_is_gone(self):
        """Rival: deleting the macOS window and leaving ``AdvancedLimitsDialog`` behind."""
        self.assertIsNone(_class(self.tree, "AdvancedLimitsDialog"))
        win = _class(self.tree, "PetWindow")
        for name in ("open_advanced_limits", "close_advanced", "adv_value"):
            with self.subTest(name=name):
                self.assertIsNone(_method(win, name), f"PetWindow.{name} still defined")
        self.assertNotIn("ADV_FIELD_KEYS", _src(PORT))

    def test_the_dialog_uses_the_same_new_copy_and_none_of_the_old(self):
        dlg = _class(self.tree, "SettingsDialog")
        self.assertIsNotNone(dlg)
        keys = _t_keys(dlg)
        for key in ("s_sec_claude", "s_sec_codex", "s_show_in_pill", "s_gauge_session",
                    "s_gauge_weekly", "s_gauge_model", "s_gauge_credit", "s_openai_key",
                    "s_codex_budget", "s_codex_mode_sub", "s_codex_mode_api"):
            with self.subTest(key=key):
                self.assertIn(key, keys)
        left = sorted(k for k in keys if k.startswith(("s_calib", "s_limit_", "s_g_"))
                      or k in ("s_model_kw", "s_auto_detect", "s_weekly_reset",
                               "s_rolling7", "s_hour"))
        self.assertEqual(left, [])

    def test_the_dialog_still_fits_768(self):
        """``PHT`` stays a class constant ≤ 656 (CLAUDE.md Danger zone)."""
        dlg = _class(self.tree, "SettingsDialog")
        pht = [n.value.elts[1].value for n in dlg.body
               if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple)
               and [getattr(e, "id", None) for e in n.targets[0].elts] == ["PWID", "PHT"]]
        self.assertEqual(len(pht), 1)
        self.assertLessEqual(pht[0], 656)

    def test_save_settings_sends_the_new_form_and_reads_no_usage(self):
        """The port builds the same form as macOS and plans it without a usage scan.

        Rivals: still sending ``session_pct``/``weekly_reset_hour`` (the core would ignore
        them, the dialog would still show them); still passing ``stats_for`` (a log scan
        on every save, for nothing)."""
        save = _method(_class(self.tree, "PetWindow"), "save_settings")
        self.assertIsNotNone(save)
        consts = _str_consts(save)
        for key in ("show_claude", "claude_gauges", "show_codex", "codex_mode",
                    "codex_gauges", "openai_admin_key", "codex_budget"):
            with self.subTest(key=key):
                self.assertIn(key, consts)
        for gone in ("model_keyword", "weekly_reset_day", "weekly_reset_hour",
                     "session_limit_m", "session_pct"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, consts)
        self.assertNotIn("compute_usage", _called(save),
                         "saving settings must not scan the logs any more")
        for call in (c for c in ast.walk(save) if isinstance(c, ast.Call)):
            if getattr(call.func, "attr", None) == "plan_settings_save":
                self.assertNotIn("stats_for", [kw.arg for kw in call.keywords])


class WinRefreshParityTests(unittest.TestCase):
    """§3/§4/§6 on Windows go through the same core functions as macOS."""

    def setUp(self):
        self.win = _class(_tree(PORT), "PetWindow")

    def test_refresh_learns_prices_codex_and_detects_codex_spikes(self):
        refresh = _method(self.win, "refresh")
        self.assertIsNotNone(refresh)
        reach = _reach_core(refresh)
        for name in ("learn_lane", "fetch_codex_cost_today", "compute_codex_onboard_state",
                     "parse_codex_entries", "codex_spikes"):
            with self.subTest(name=name):
                self.assertIn(name, reach)

    def test_the_reset_jump_is_the_server_rule(self):
        """Rival: the old ``prev["session"]["pct"]`` comparison (log percentages)."""
        apply_pending = _method(self.win, "_apply_pending")
        self.assertIsNotNone(apply_pending)
        self.assertIn("session_reset_jump", _called(apply_pending))
        self.assertNotIn('["session"]["pct"]', _src(PORT))

    def test_spike_display_is_per_provider(self):
        """The port's ``spike_info`` / mood consult the core's ``provider_spiking`` so a
        Codex-only spike and per-provider API mode behave as on macOS. Rival: the old
        ``RUNTIME["mode"] == "api"`` global gate (silences Codex in Claude API mode)."""
        self.assertIn("provider_spiking", _called(_tree(PORT)))


class WinContextMenuParityTests(unittest.TestCase):
    """§7 on Windows: Codex install/login items, same TR keys, new PowerShell console."""

    def setUp(self):
        self.win = _class(_tree(PORT), "PetWindow")

    def test_the_menu_offers_codex_items_from_codex_onboard(self):
        menu = _method(self.win, "_context_menu")
        self.assertIsNotNone(menu)
        self.assertLessEqual({"menu_install_codex", "menu_login_codex"}, _t_keys(menu))
        self.assertIn("codex_onboard", _str_consts(menu))
        self.assertLessEqual({"_install_codex", "_login_codex"},
                             {n.attr for n in ast.walk(menu) if isinstance(n, ast.Attribute)})

    def test_the_console_commands(self):
        """Same commands as macOS, in a new console like ``_install_claude``. Rivals: a
        hidden subprocess (the user cannot finish ``codex login``); a different package."""
        for name, needle in (("_install_codex", "npm install -g @openai/codex"),
                             ("_login_codex", "codex login")):
            with self.subTest(method=name):
                fn = _method(self.win, name)
                self.assertIsNotNone(fn, f"PetWindow.{name} missing")
                self.assertIn("_run_in_console", _called(fn))
                self.assertTrue(any(needle in s for s in _str_consts(fn)),
                                f"{name} does not run {needle!r}")


class WinRound2CallSiteTests(unittest.TestCase):
    """Round 2 (Coordinator decisions after review, 2026-10-05), Windows call sites."""

    def setUp(self):
        self.win = _class(_tree(PORT), "PetWindow")
        self.refresh = _method(self.win, "refresh")

    def _calls(self, node, name):
        return [c for c in ast.walk(node) if isinstance(c, ast.Call)
                and (getattr(c.func, "attr", None) == name or getattr(c.func, "id", None) == name)]

    def test_claude_onboarding_flag_is_token_derived(self):
        """R2-1. Rival: ``bool(values["stats"].get("entries"))`` (logs hide the sign-in)."""
        calls = self._calls(self.refresh, "compute_onboard_state")
        self.assertEqual(len(calls), 1)
        flag = " ".join([ast.unparse(a) for a in calls[0].args[1:]]
                        + [ast.unparse(k.value) for k in calls[0].keywords])
        self.assertNotIn("entries", flag)
        self.assertIn("token", flag.lower(), flag)

    def test_codex_onboarding_knows_whether_codex_is_in_use(self):
        """R2-2: five arguments (or the ``codex_home_exists`` keyword), fed by the core's
        ``codex_home_exists``."""
        calls = self._calls(self.refresh, "compute_codex_onboard_state")
        self.assertEqual(len(calls), 1)
        c = calls[0]
        self.assertTrue(len(c.args) == 5 or "codex_home_exists" in [k.arg for k in c.keywords])
        self.assertIn("codex_home_exists", _reach_core(self.refresh))

    def test_learning_passes_fetch_keys(self):
        """R2-4: non-constant ``claude_fetch=`` and ``codex_fetch=``."""
        calls = self._calls(self.refresh, "learn_server_limits")
        self.assertEqual(len(calls), 1)
        kws = {k.arg: k.value for k in calls[0].keywords}
        for key in ("claude_fetch", "codex_fetch"):
            with self.subTest(key=key):
                self.assertIn(key, kws)
                self.assertNotIsInstance(kws[key], ast.Constant)

    def test_mood_passes_codex_rows_separately(self):
        """R2-6b: Claude and Codex rows go in separately so each is filtered by its own
        gauge selection."""
        calls = self._calls(_method(self.win, "current_mood"), "mood_for")
        self.assertEqual(len(calls), 1)
        self.assertIn("codex_rows", [k.arg for k in calls[0].keywords])


if __name__ == "__main__":
    unittest.main()
