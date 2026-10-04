"""Gates for docs-design/server-only-usage-20261005.md — Verifier (sou-verify), written
BEFORE any implementation exists. AGENTS.md §2 Condition A: the Developer must not touch
an assertion, an expected value or a fixture literal in this file.

What the spec decides (user, 2026-10-05, quoted in the spec's §0):

* "추정 로그치 적는건 이제 없애자!! 기능도 없애고" — the numbers on the pill are always the
  server's. The log estimate, calibration, absolute limits, the advanced-limits window,
  the weekly-reset weekday and the model-keyword setting are removed, with their copy.
* "로그로 급증감지만 살려놔 ! 그럼 코덱스도 로그로 급증감지가 되어야겠지!!" — the logs survive
  only as a spike detector, for Claude and (new) for Codex. The spike floor's ``limit`` is
  no longer typed by a person; it is learned from the server percentage (§3.3).
* the session-reset jump stays, on the server value (§4).
* per-provider settings: show/hide, Codex API cost mode, which gauges the pill shows (§2, §5).

The production interfaces these tests expect are listed in the commit message and in the
Verifier report; each test names the one it pins. A missing interface fails with
``missing production interface: <name>`` so the red run says exactly what is absent.

Discrimination (AGENTS.md §3): every fixture below carries, in its docstring, the plausible
wrong implementations and what each one returns for that fixture. Where two rivals would tie
with the expected value the fixture was changed until they do not.

Testing policy (CLAUDE.md): synthetic fixtures only. ``LOG_DIRS`` and the Codex sessions root
point at temporary directories; nothing reads ``~/.claude``, ``~/.codex`` or writes
``~/.claude_pet.json``; the network is a fake ``urlopen``; no Keychain, no SMAppService.

This module imports ``claude_pet`` the same way ``test_codex_usage.py`` does, so it can run on
the Windows CI runner too (the ``windows.win_core`` shim) — the workflow needs a step for it.
"""

import ast
import inspect
import io
import json
import math
import os
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import claude_pet  # noqa: E402
except ImportError:                                   # Windows: fcntl / CDLL(None)
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()

UTC = timezone.utc
SOURCE = (ROOT / "claude_pet.py").read_text(encoding="utf-8")


def need(test, name):
    """The production interface ``name`` — or a failure that names what is missing."""
    test.assertTrue(hasattr(claude_pet, name), f"missing production interface: {name}")
    return getattr(claude_pet, name)


def entry(ts, total, model="claude-opus-5", noncache=None):
    """One ``parse_usage_entries`` row: (timestamp, total, model, noncache)."""
    return (ts, float(total), model, float(total if noncache is None else noncache))


class _RuntimeGuard(unittest.TestCase):
    """Restores RUNTIME (and the learned-limit store, when it exists) after each test."""

    def setUp(self):
        saved = dict(claude_pet.RUNTIME)
        self.addCleanup(lambda: (claude_pet.RUNTIME.clear(), claude_pet.RUNTIME.update(saved)))
        store = getattr(claude_pet, "LEARNED_LIMITS", None)
        if isinstance(store, dict):
            saved_store = dict(store)
            self.addCleanup(lambda: (store.clear(), store.update(saved_store)))
            store.clear()


# ═════════════════════ §1 — the estimate is gone from what is shown ═════════════════════

class EstimateRemovedTests(_RuntimeGuard):
    """§1: no gauge numbers out of the logs, no estimate segment, no limit settings."""

    def test_compute_usage_returns_no_gauges_but_keeps_the_spike_contract(self):
        """``compute_usage()`` drops session/weekly/opus and keeps the spike inputs.

        Rivals: keeping the gauges (today — the three keys are present); dropping
        ``entries``/``burn_*``/``spikes`` along with them (the spike detector and the
        onboarding call site still read them)."""
        now = datetime.now(UTC)
        with mock.patch.object(claude_pet, "parse_usage_entries",
                               return_value=[entry(now - timedelta(minutes=1), 500.0)]):
            stats = claude_pet.compute_usage()
        self.assertEqual({"session", "weekly", "opus"} & set(stats), set(),
                         "compute_usage() still returns log-derived gauges")
        for key in ("entries", "last_activity", "burn_5m", "burn_5m_opus", "spikes", "now"):
            self.assertIn(key, stats, f"compute_usage() lost {key!r}")
        self.assertEqual(stats["entries"], 1)

    def test_the_estimate_vocabulary_is_gone(self):
        """``SUMMARY_APPROX`` and the amber estimate colour are removed (spec §1).

        Rival: leaving them defined but unused — the next change reaches for them again."""
        self.assertFalse(hasattr(claude_pet, "SUMMARY_APPROX"), "SUMMARY_APPROX still defined")
        self.assertNotIn("estimate", claude_pet.SUMMARY_COLORS)
        for gone in ("_calibration_percent_error", "GAUGE_LIMIT_KEYS", "fmt_limit_m",
                     "LIMIT_M_DECIMALS", "_weekly_window_start"):
            with self.subTest(symbol=gone):
                self.assertFalse(hasattr(claude_pet, gone), f"{gone} is still defined")

    def test_no_limit_or_model_or_weekly_reset_setting_survives_in_runtime(self):
        """RUNTIME carries no limit/model/weekly-reset keys and ``apply_config`` does not
        load them back from an old config file (spec §1: "읽지도 쓰지도 않는다").

        Rivals: keeping the 8M/60M/15M defaults; dropping the defaults but still copying
        the keys in ``apply_config`` (an old ``~/.claude_pet.json`` would resurrect them)."""
        old = ("session_limit", "weekly_limit", "opus_limit", "model_keyword",
               "weekly_reset_day", "weekly_reset_hour")
        self.assertEqual(set(old) & set(claude_pet.RUNTIME), set(),
                         "RUNTIME still has limit/model/weekly-reset keys")
        claude_pet.apply_config({"session_limit": 5, "weekly_limit": 6, "opus_limit": 7,
                                 "model_keyword": "opus", "weekly_reset_day": 2,
                                 "weekly_reset_hour": 9, "lang": claude_pet.L["lang"]})
        self.assertEqual(set(old) & set(claude_pet.RUNTIME), set(),
                         "apply_config loaded a removed setting from the config file")

    def test_the_limit_environment_variables_are_not_read(self):
        """``CLAUDE_PET_*_LIMIT`` and ``CLAUDE_PET_MODEL`` are no longer read (spec §1).
        Source-level: the names must not appear in ``claude_pet.py`` at all."""
        for name in ("CLAUDE_PET_SESSION_LIMIT", "CLAUDE_PET_WEEKLY_LIMIT",
                     "CLAUDE_PET_OPUS_LIMIT", "CLAUDE_PET_MODEL"):
            with self.subTest(env=name):
                self.assertNotIn(name, SOURCE)

    def test_no_server_rows_never_yields_numbers_from_the_log_snapshot(self):
        """Without server rows ``roam_summary`` answers with a status, never a segment
        built from ``stats`` — whatever the snapshot contains.

        Fixture: a snapshot shaped like the OLD compute_usage (gauges at 42/17/9 %, 5
        entries) so that an implementation which still reads the gauges has something to
        read. Rivals: today's ``("estimate", rows)``; an ``exact`` segment synthesised
        from the snapshot. Both are a non-status kind; the spec allows only a status."""
        old_shape = {"entries": 5, "session": {"pct": 42.0}, "weekly": {"pct": 17.0},
                     "opus": {"pct": 9.0}, "spikes": {}, "model_kw": "fable"}
        for auth_error in (False, True):
            with self.subTest(auth_error=auth_error):
                seg = claude_pet.roam_summary("sub", None, old_shape, None, None, False,
                                              auth_error=auth_error)
                self.assertEqual(seg[0], "status", f"numbers from logs reached the pill: {seg!r}")

    def test_a_rejected_token_is_token_expired_whatever_the_logs_hold(self):
        """§1: 401/403 → ``token_expired`` "로그 유무와 무관하게".

        Rival: today's rule (token_expired only when ``entries == 0``) — for ``entries=5``
        it returns the estimate. The pair 0/5 separates "decides on entries" from
        "decides on auth_error alone"."""
        for entries in (0, 5):
            with self.subTest(entries=entries):
                seg = claude_pet.roam_summary("sub", None, {"entries": entries, "spikes": {}},
                                              None, None, False, auth_error=True)
                self.assertEqual(seg, ("status", "token_expired"))

    def test_mood_is_idle_without_server_rows_and_survives_the_new_snapshot(self):
        """§1: "서버 행이 없으면 idle(급증이면 failed)". ``mood_for`` must accept the new
        compute_usage shape (no gauges) and answer idle.

        Rivals: today's ``worst_pct`` indexing ``stats["session"]`` (KeyError); deriving a
        mood from log usage."""
        stats = {"entries": 40, "spikes": {"session": False}, "burn_5m": 0.0,
                 "burn_5m_opus": 0.0, "last_activity": None, "now": datetime.now(UTC)}
        self.assertEqual(claude_pet.mood_for(stats), "idle")

    def test_report_prints_server_values_and_no_log_gauges(self):
        """``--report`` prints the server rows and nothing derived from log gauges.

        Rival: today's ``print_report`` indexes ``s["session"]`` and dies on the new
        snapshot (KeyError), or prints log percentages beside the server's."""
        stats = {"entries": 3, "spikes": {}, "burn_5m": 0.0, "burn_5m_opus": 0.0,
                 "last_activity": None, "now": datetime.now(UTC), "model_kw": "fable"}
        rows = [("SERVER-SESSION", 42.0, None, None)]
        out = io.StringIO()
        with mock.patch.object(claude_pet, "compute_usage", return_value=stats), \
                mock.patch.object(claude_pet, "fetch_exact_usage", return_value=rows), \
                mock.patch.object(claude_pet, "fetch_codex_usage", return_value=None), \
                mock.patch.object(claude_pet, "fetch_api_cost_today", return_value=None), \
                redirect_stdout(out):
            claude_pet.print_report()
        text = out.getvalue()
        self.assertIn("SERVER-SESSION", text)
        self.assertIn("42", text)
        self.assertNotIn("≈", text)


class RemovedCopyTests(unittest.TestCase):
    """§1/§2: the removed settings' copy is gone and the new copy exists in all locales."""

    REMOVED_PREFIXES = ("s_calib", "s_limit_", "s_g_", "s_err_calib")
    REMOVED_EXACT = ("s_model_kw", "s_auto_detect", "s_weekly_reset", "s_rolling7",
                     "s_hour", "s_err_limit", "s_err_hour")
    NEW_KEYS = ("s_sec_claude", "s_sec_codex", "s_show_in_pill", "s_gauges",
                "s_gauge_session", "s_gauge_weekly", "s_gauge_model", "s_gauge_credit",
                "s_codex_mode_sub", "s_codex_mode_api", "s_openai_key", "s_codex_budget",
                "s_err_codex_budget", "no_providers", "codex_need_admin_key",
                "codex_api_key_rejected", "codex_api_unreachable",
                "menu_install_codex", "menu_login_codex")

    def test_removed_keys_are_gone_from_every_locale(self):
        for lang in claude_pet.SUPPORTED_LANGS:
            table = claude_pet.TR[lang]
            with self.subTest(lang=lang):
                left = sorted(k for k in table
                              if k in self.REMOVED_EXACT
                              or any(k.startswith(p) for p in self.REMOVED_PREFIXES))
                self.assertEqual(left, [], f"{lang} still carries removed settings copy")

    def test_new_keys_exist_non_empty_in_every_locale(self):
        for lang in claude_pet.SUPPORTED_LANGS:
            with self.subTest(lang=lang):
                missing = [k for k in self.NEW_KEYS
                           if not str(claude_pet.TR[lang].get(k, "")).strip()]
                self.assertEqual(missing, [], f"{lang} is missing new copy")

    def test_codex_copy_names_codex(self):
        """Codex strings are symmetric with Claude's: the menu items and the Codex status
        keys name Codex in every locale (memory codex-equal-to-claude)."""
        for lang in claude_pet.SUPPORTED_LANGS:
            for key in ("menu_install_codex", "menu_login_codex", "s_sec_codex",
                        "codex_need_admin_key"):
                with self.subTest(lang=lang, key=key):
                    self.assertIn("Codex", claude_pet.TR[lang].get(key, ""))

    def test_the_subscription_label_no_longer_mentions_logs(self):
        """§1: ``s_mode_sub`` stops saying "(Claude Code logs)". "로그인"/"ログイン"/"login"
        are allowed — they are the account, not the logs."""
        import re
        patterns = {"en": r"\blogs?\b", "ko": r"로그(?!인)", "ja": r"ログ(?!イン)",
                    "es": r"registros?"}
        for lang, pattern in patterns.items():
            with self.subTest(lang=lang):
                text = claude_pet.TR[lang]["s_mode_sub"]
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE),
                                  f"{lang} s_mode_sub still mentions logs: {text!r}")


# ═════════════════════ §3.1 / §3.3 — spike detection on learned limits ═════════════════════

class SpikePrimitiveTests(unittest.TestCase):
    """``is_spike(burn, base, limit, base_pct, mult=1.0)`` — module level now, same rule.

    floor = limit × base_pct × mult / 100; spike ⇔ burn ≥ floor and burn ≥ 2.5 × max(base, floor/5).
    With limit 1_000_000, base_pct 2: floor 20_000, 2.5 × floor/5 = 10_000.
    """

    def test_the_rule_and_its_no_limit_case(self):
        """Rivals: dropping the floor (15_000 would spike); dropping the 2.5× gate
        (base 30_000 would still spike); a default limit when none is learned (None
        would spike for any large burn)."""
        is_spike = need(self, "is_spike")
        self.assertTrue(is_spike(50_000, 0, 1_000_000, 2.0))
        self.assertFalse(is_spike(15_000, 0, 1_000_000, 2.0), "below the floor")
        self.assertFalse(is_spike(50_000, 30_000, 1_000_000, 2.0), "below 2.5× the base")
        self.assertTrue(is_spike(10_000, 0, 1_000_000, 2.0, mult=0.5), "mult scales the floor")
        for limit in (None, 0, -5):
            with self.subTest(limit=limit):
                self.assertFalse(is_spike(10 ** 12, 0, limit, 2.0),
                                 "no learned limit must mean no spike verdict")


class LearnedLimitMathTests(unittest.TestCase):
    """``learn_limit(prev, pct, total, alpha=0.3)`` → the new limit, or ``prev`` unchanged.

    limit = total / (pct/100); EMA: new = prev + 0.3 × (sample − prev).
    """

    def test_first_sample_is_the_plain_back_solve(self):
        learn_limit = need(self, "learn_limit")
        self.assertAlmostEqual(learn_limit(None, 25.0, 1_000.0), 4_000.0)

    def test_the_ema_weights_the_new_sample_by_point_three(self):
        """prev 1000, sample 2000 (pct 50, total 1000).

        | implementation                     | result |
        | ---------------------------------- | ------ |
        | no smoothing (replace)             | 2000   |
        | α on the previous value            | 1700   |
        | plain average                      | 1500   |
        | **α = 0.3 on the new sample**      | **1300** |
        """
        learn_limit = need(self, "learn_limit")
        self.assertAlmostEqual(learn_limit(1_000.0, 50.0, 1_000.0), 1_300.0)

    def test_below_five_percent_learns_nothing(self):
        """p < 5 → prev unchanged; p = 5 learns. Rivals: ``<=`` (5 would not learn);
        threshold 1 or none (4.99 would learn 20_040.08…)."""
        learn_limit = need(self, "learn_limit")
        self.assertIsNone(learn_limit(None, 4.99, 1_000.0))
        self.assertEqual(learn_limit(777.0, 4.99, 1_000.0), 777.0)
        self.assertAlmostEqual(learn_limit(None, 5.0, 1_000.0), 20_000.0)

    def test_zero_usage_learns_nothing(self):
        """T = 0 → prev unchanged. Rival: learning a zero limit, which would make every
        later burn a spike (floor 0)."""
        learn_limit = need(self, "learn_limit")
        self.assertIsNone(learn_limit(None, 40.0, 0.0))
        self.assertEqual(learn_limit(900.0, 40.0, 0.0), 900.0)

    def test_unusable_inputs_learn_nothing(self):
        learn_limit = need(self, "learn_limit")
        for pct, total in ((float("nan"), 10.0), (40.0, float("inf")), (40.0, -1.0),
                           (None, 10.0), (40.0, None), (True, 10.0)):
            with self.subTest(pct=pct, total=total):
                self.assertEqual(learn_limit(321.0, pct, total), 321.0)


class WindowTotalTests(unittest.TestCase):
    """``window_total(entries, reset, window_seconds, model_kw=None)`` — the T of §3.3:
    the **total** (not noncache) of entries at or after ``reset − window``."""

    def test_window_starts_at_reset_minus_window_and_sums_totals(self):
        """reset = R, window 5h → start R−5h. Entries: R−5h30m (out), R−5h (in, boundary),
        R−1h (in). Totals 100/200/400, noncache 1/2/4.

        | implementation                        | result |
        | ------------------------------------- | ------ |
        | noncache instead of total             | 6      |
        | strict ``>`` at the boundary          | 400    |
        | everything (no window)                | 700    |
        | **total, start inclusive**            | **600** |
        """
        window_total = need(self, "window_total")
        R = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)
        entries = [entry(R - timedelta(hours=5, minutes=30), 100, noncache=1),
                   entry(R - timedelta(hours=5), 200, noncache=2),
                   entry(R - timedelta(hours=1), 400, noncache=4)]
        self.assertAlmostEqual(window_total(entries, R, 5 * 3600), 600.0)

    def test_the_model_lane_filters_by_keyword(self):
        window_total = need(self, "window_total")
        R = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)
        entries = [entry(R - timedelta(hours=2), 100, model="claude-fable-5"),
                   entry(R - timedelta(hours=2), 30, model="claude-sonnet-5")]
        self.assertAlmostEqual(window_total(entries, R, 7 * 86400, model_kw="fable"), 100.0)
        self.assertAlmostEqual(window_total(entries, R, 7 * 86400), 130.0)


class LearnLaneTests(unittest.TestCase):
    """``learn_lane(learned, lane, pct, reset, window_seconds, entries, model_kw=None)``
    updates ``learned[lane]`` in place and returns the value (or None)."""

    R = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)

    def entries(self, total):
        return [entry(self.R - timedelta(hours=1), total, noncache=total / 10)]

    def test_learns_from_total_and_smooths_on_the_second_call(self):
        """First call: T 2000 at 40 % → 5000. Second: T 4000 at 40 % → sample 10000,
        EMA → 6500. Rivals: noncache (first 500); no EMA (10000); α on prev (8500)."""
        learn_lane = need(self, "learn_lane")
        learned = {}
        self.assertAlmostEqual(learn_lane(learned, "session", 40.0, self.R, 5 * 3600,
                                          self.entries(2_000.0)), 5_000.0)
        self.assertAlmostEqual(learned["session"], 5_000.0)
        learn_lane(learned, "session", 40.0, self.R, 5 * 3600, self.entries(4_000.0))
        self.assertAlmostEqual(learned["session"], 6_500.0)

    def test_no_learning_leaves_no_key(self):
        """p < 5, T = 0, and an unknown reset each leave the store without the lane —
        a missing key is what makes "no spike before anything is learned" hold."""
        learn_lane = need(self, "learn_lane")
        learned = {}
        learn_lane(learned, "weekly", 4.0, self.R, 7 * 86400, self.entries(2_000.0))
        learn_lane(learned, "weekly", 40.0, self.R, 7 * 86400, [])
        learn_lane(learned, "weekly", 40.0, None, 7 * 86400, self.entries(2_000.0))
        self.assertNotIn("weekly", learned)

    def test_the_store_is_separate_from_runtime(self):
        """§3.3: learned values live in memory in a dict that is not RUNTIME and is never
        persisted. Rival: writing them into RUNTIME (they would be saved by the next
        settings save that copies RUNTIME, and an old limit key would be reborn)."""
        store = need(self, "LEARNED_LIMITS")
        self.assertIsInstance(store, dict)
        self.assertIsNot(store, claude_pet.RUNTIME)


class ClaudeSpikeOnLearnedLimitsTests(_RuntimeGuard):
    """``compute_usage`` judges Claude spikes only against ``LEARNED_LIMITS``.

    Fixture: 30_000 noncache in the last 5 minutes, nothing before (base 0). With a
    learned session limit of 1_000_000 the floor is 20_000 → spike. Without any learned
    limit → no spike, whatever the burn.
    """

    def run_compute(self, **kwargs):
        now = datetime.now(UTC)
        rows = [entry(now - timedelta(minutes=1), 60_000, model="claude-opus-5",
                      noncache=30_000)]
        with mock.patch.object(claude_pet, "parse_usage_entries", return_value=rows):
            return claude_pet.compute_usage(**kwargs)

    def test_no_learned_limit_means_no_spike(self):
        """Rivals: the old 8M/60M/15M defaults (8M × 2 % = 160_000 → no spike either, so
        the positive control below is what separates "default" from "learned"); a fixed
        fallback limit small enough to fire."""
        need(self, "LEARNED_LIMITS")
        stats = self.run_compute()
        self.assertEqual({k: v for k, v in stats["spikes"].items() if v}, {})

    def test_a_learned_session_limit_arms_only_the_session_lane(self):
        """Positive control. Rivals: reading RUNTIME["session_limit"] (absent → KeyError
        or default → no spike); arming every lane from one learned value (weekly/opus
        would turn True)."""
        store = need(self, "LEARNED_LIMITS")
        store["session"] = 1_000_000.0
        stats = self.run_compute()
        self.assertTrue(stats["spikes"]["session"])
        self.assertFalse(stats["spikes"].get("weekly"))
        self.assertFalse(stats["spikes"].get("opus"))

    def test_the_burn_is_noncache_not_total(self):
        """Learned session limit 2_000_000 → floor 40_000. Burn: noncache 30_000 (no
        spike), total 60_000 (would spike). Rival: weighing the burn by total."""
        store = need(self, "LEARNED_LIMITS")
        store["session"] = 2_000_000.0
        self.assertFalse(self.run_compute()["spikes"]["session"])

    def test_the_model_keyword_comes_from_the_caller_not_a_setting(self):
        """``compute_usage(model_keyword=...)``: the server's model row decides the model
        lane; without it, auto-detection (fable before opus). A ``model_keyword`` in the
        runtime snapshot is ignored.

        Rivals: honouring the removed setting ("mythos" → model_kw "mythos"); ignoring the
        caller's keyword (auto → "fable")."""
        now = datetime.now(UTC)
        rows = [entry(now - timedelta(minutes=1), 100, model="claude-opus-5"),
                entry(now - timedelta(minutes=2), 50, model="claude-fable-5")]
        snapshot = dict(claude_pet.RUNTIME, model_keyword="mythos", spike_mult=1.0)
        with mock.patch.object(claude_pet, "parse_usage_entries", return_value=rows):
            auto = claude_pet.compute_usage(runtime=snapshot)
            told = claude_pet.compute_usage(model_keyword="opus")
        self.assertEqual(auto["model_kw"], "fable")
        self.assertEqual(told["model_kw"], "opus")
        self.assertAlmostEqual(told["burn_5m_opus"], 100.0)

    def test_model_keyword_from_server_rows(self):
        """``model_keyword_from_rows(rows)`` → the family named by the server's model row
        (order 2 or 5), lowercased; None without one."""
        fn = need(self, "model_keyword_from_rows")
        self.assertEqual(fn([(claude_pet.t("session"), 10.0, None, None),
                             ("Fable", 20.0, None, None)]), "fable")
        self.assertEqual(fn([("Claude Opus 5 weekly", 20.0, None, None)]), "opus")
        self.assertIsNone(fn([(claude_pet.t("session"), 10.0, None, None),
                              (claude_pet.t("weekly"), 20.0, None, None)]))
        self.assertIsNone(fn(None))


class ProviderSpikingTests(_RuntimeGuard):
    """``provider_spiking(stats, provider, runtime=None)`` — per provider, API mode of
    THAT provider suppresses only that provider (§3.3)."""

    STATS = {"spikes": {"session": True, "weekly": False, "opus": False,
                        "codex_session": False, "codex_weekly": True}}

    def test_each_provider_reads_its_own_lanes(self):
        fn = need(self, "provider_spiking")
        rt = dict(claude_pet.RUNTIME, mode="sub", codex_mode="sub")
        self.assertTrue(fn(self.STATS, "claude", rt))
        self.assertTrue(fn(self.STATS, "codex", rt))
        quiet = {"spikes": {"session": False, "codex_session": False}}
        self.assertFalse(fn(quiet, "claude", rt))
        self.assertFalse(fn(quiet, "codex", rt))
        self.assertFalse(fn(None, "claude", rt))

    def test_api_mode_is_per_provider(self):
        """Rivals: one global ``mode == "api"`` check (would silence Codex too); ignoring
        ``codex_mode`` (Codex API users would see log spikes)."""
        fn = need(self, "provider_spiking")
        rt = dict(claude_pet.RUNTIME, mode="api", codex_mode="sub")
        self.assertFalse(fn(self.STATS, "claude", rt))
        self.assertTrue(fn(self.STATS, "codex", rt))
        rt = dict(claude_pet.RUNTIME, mode="sub", codex_mode="api")
        self.assertTrue(fn(self.STATS, "claude", rt))
        self.assertFalse(fn(self.STATS, "codex", rt))


# ═════════════════════ §4 — the session-reset jump, on server values ═════════════════════

class SessionResetJumpTests(unittest.TestCase):
    """``session_reset_jump(prev_claude, claude, prev_codex, codex)`` → bool.

    Claude's session row is the one with ``_label_order == 0``; Codex's is the row
    labelled ``"codex_session"``. Jump iff some provider went from > 5 to < 1.
    """

    def S(self, pct):
        return (claude_pet.t("session"), pct, None, None)

    def W(self, pct):
        return (claude_pet.t("weekly"), pct, None, None)

    def test_claude_session_crossing(self):
        """Rivals: ``>=`` 5 (5 → 0 would jump); ``<=`` 1 (40 → 1 would jump)."""
        jump = need(self, "session_reset_jump")
        self.assertTrue(jump([self.S(40.0)], [self.S(0.5)], None, None))
        self.assertFalse(jump([self.S(40.0)], [self.S(1.0)], None, None))
        self.assertFalse(jump([self.S(5.0)], [self.S(0.0)], None, None))
        self.assertFalse(jump(None, [self.S(0.0)], None, None))

    def test_only_the_session_row_counts(self):
        """Rival: the first row whatever it is. Fixture puts the WEEKLY row first and lets
        it cross while the session row does not."""
        jump = need(self, "session_reset_jump")
        self.assertFalse(jump([self.W(40.0), self.S(30.0)], [self.W(0.0), self.S(31.0)],
                              None, None))
        self.assertTrue(jump([self.W(40.0), self.S(30.0)], [self.W(41.0), self.S(0.0)],
                             None, None))

    def test_codex_alone_can_jump_and_its_weekly_row_cannot(self):
        """Rivals: Claude-only (Codex crossing ignored); Codex weekly treated as session."""
        jump = need(self, "session_reset_jump")
        cs = lambda p: ("codex_session", p, None, None)
        cw = lambda p: ("codex_weekly", p, None, None)
        self.assertTrue(jump([self.S(30.0)], [self.S(31.0)], [cs(30.0)], [cs(0.0)]))
        self.assertFalse(jump(None, None, [cw(30.0)], [cw(0.0)]))

    def test_the_jump_reads_no_log_percentage(self):
        """Source-level, both refresh paths: the old ``prev["session"]["pct"]`` comparison
        is gone and the server rule is called."""
        self.assertNotIn('["session"]["pct"]', SOURCE)
        win = ROOT / "windows" / "claude_pet_win.py"
        if win.exists():
            self.assertNotIn('["session"]["pct"]', win.read_text(encoding="utf-8"))


# ═════════════════════ §5 — gauge filtering, provider visibility ═════════════════════

class GaugeFilterTests(unittest.TestCase):
    """``claude_gauge_class(label)`` and ``filter_claude_rows(rows, gauges)`` /
    ``filter_codex_rows(rows, gauges)``.

    Classes by ``_label_order``: 0 session, 1 weekly, 2 and 5 model, 9 credit.
    """

    def rows(self):
        return [(claude_pet.t("session"), 10.0, None, None),
                (claude_pet.t("weekly"), 20.0, None, None),
                ("Fable", 30.0, None, None),
                ("Some Server Window", 40.0, None, None),
                (claude_pet.t("credit"), 50.0, None, None)]

    def test_classes(self):
        cls = need(self, "claude_gauge_class")
        self.assertEqual([cls(r[0]) for r in self.rows()],
                         ["session", "weekly", "model", "model", "credit"])

    def test_only_selected_classes_survive_in_order(self):
        """Rivals: order-5 rows dropped as unknown (the "model" selection would lose
        "Some Server Window"); filtering by label text instead of class; reordering."""
        flt = need(self, "filter_claude_rows")
        self.assertEqual([r[0] for r in flt(self.rows(), ["weekly", "credit"])],
                         [claude_pet.t("weekly"), claude_pet.t("credit")])
        self.assertEqual([r[0] for r in flt(self.rows(), ["model"])],
                         ["Fable", "Some Server Window"])
        self.assertEqual(flt(self.rows(), []), [])
        self.assertEqual(len(flt(self.rows(), ["session", "weekly", "model", "credit"])), 5)

    def test_codex_lanes_map_to_session_and_weekly(self):
        flt = need(self, "filter_codex_rows")
        rows = [("codex_session", 10.0, None, None), ("codex_weekly", 20.0, None, None)]
        self.assertEqual([r[0] for r in flt(rows, ["weekly"])], ["codex_weekly"])
        self.assertEqual([r[0] for r in flt(rows, ["session"])], ["codex_session"])
        self.assertEqual(flt(rows, []), [])
        self.assertIsNone(flt(None, ["session"]))


class ProviderDefaultsAndVisibilityTests(_RuntimeGuard):
    """New RUNTIME keys and ``provider_shown(runtime, provider)``."""

    def test_defaults(self):
        rt = claude_pet.RUNTIME
        expected = {"show_claude": True,
                    "claude_gauges": ["session", "weekly", "model", "credit"],
                    "show_codex": True, "codex_mode": "sub",
                    "codex_gauges": ["session", "weekly"],
                    "openai_admin_key": "", "codex_budget": 0.0}
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertIn(key, rt)
                self.assertEqual(rt[key], value)

    def test_apply_config_loads_the_new_keys(self):
        claude_pet.apply_config({"show_claude": False, "claude_gauges": ["weekly"],
                                 "show_codex": False, "codex_mode": "api",
                                 "codex_gauges": ["session"], "openai_admin_key": "sk-x",
                                 "codex_budget": 12.5, "lang": claude_pet.L["lang"]})
        rt = claude_pet.RUNTIME
        self.assertEqual((rt.get("show_claude"), rt.get("claude_gauges"), rt.get("show_codex"),
                          rt.get("codex_mode"), rt.get("codex_gauges"),
                          rt.get("openai_admin_key"), rt.get("codex_budget")),
                         (False, ["weekly"], False, "api", ["session"], "sk-x", 12.5))

    def test_a_provider_with_no_gauges_is_hidden(self):
        """§2: "게이지를 하나도 고르지 않은 제공자는 표시 꺼짐과 같다". Rival: only the
        show_* flag is consulted."""
        shown = need(self, "provider_shown")
        self.assertTrue(shown({"show_claude": True, "claude_gauges": ["weekly"]}, "claude"))
        self.assertFalse(shown({"show_claude": False, "claude_gauges": ["weekly"]}, "claude"))
        self.assertFalse(shown({"show_claude": True, "claude_gauges": []}, "claude"))
        self.assertTrue(shown({"show_codex": True, "codex_gauges": ["session"]}, "codex"))
        self.assertFalse(shown({"show_codex": True, "codex_gauges": []}, "codex"))
        self.assertFalse(shown({"show_codex": False, "codex_gauges": ["session"]}, "codex"))


class CodexSegmentSpikeTests(unittest.TestCase):
    """``roam_summary_codex(payload, spiking=False)`` marks the Codex session label (§3.3)."""

    def test_spiking_marks_only_the_first_row(self):
        """Rivals: today's hard-wired False; every row marked."""
        rows = [("codex_session", 30.0, None, None), ("codex_weekly", 60.0, None, None)]
        kind, out = claude_pet.roam_summary_codex(rows, spiking=True)
        self.assertEqual(kind, "exact")
        self.assertEqual([r[2] for r in out], [True, False])
        kind, out = claude_pet.roam_summary_codex(rows)
        self.assertEqual([r[2] for r in out], [False, False])


class CodexCostSegmentTests(unittest.TestCase):
    """``roam_summary_codex_cost(has_admin_key, cost_today, cost_month=None,
    cost_budget=None, api_error=False, api_stale=False)`` — the Claude cost branch, mirrored
    with the Codex status keys (§5)."""

    def test_status_keys_and_cost_shape(self):
        """Rivals: the Claude keys reused (need_admin_key …), which would tell a Codex user
        to fix their Anthropic key; loading after a rejection; a zero budget kept."""
        fn = need(self, "roam_summary_codex_cost")
        self.assertEqual(fn(False, None), ("status", "codex_need_admin_key"))
        self.assertEqual(fn(False, 3.0), ("status", "codex_need_admin_key"))
        self.assertEqual(fn(True, None, api_error=True), ("status", "codex_api_key_rejected"))
        self.assertEqual(fn(True, None, api_stale=True), ("status", "codex_api_unreachable"))
        self.assertEqual(fn(True, None, api_error=True, api_stale=True),
                         ("status", "codex_api_key_rejected"))
        self.assertEqual(fn(True, None), ("status", "loading"))
        self.assertEqual(fn(True, 1.5, 20.0, 50.0), ("cost", (1.5, 20.0, 50.0)))
        self.assertEqual(fn(True, 1.5, 20.0, 0), ("cost", (1.5, 20.0, None)))
        self.assertEqual(fn(True, 1.5), ("cost", (1.5, None, None)))
        self.assertEqual(fn(True, 1.5, float("nan")), ("cost", (1.5, None, None)))


# ═════════════════════ §2 — the settings plan ═════════════════════

NEW_OWNED = ("pet", "lang", "mode", "admin_key", "api_budget", "spike_mult", "greet",
             "show_claude", "claude_gauges", "show_codex", "codex_mode", "codex_gauges",
             "openai_admin_key", "codex_budget")
OLD_KEYS = ("session_limit", "weekly_limit", "opus_limit", "model_keyword",
            "weekly_reset_day", "weekly_reset_hour")


def new_form(**over):
    form = {"pet": "dog", "lang": "ko", "mode": "sub", "admin_key": "", "api_budget": "0",
            "spike_mult": 1.0, "greet": True,
            "show_claude": True, "claude_gauges": ["session", "weekly"],
            "show_codex": False, "codex_mode": "api", "codex_gauges": ["weekly"],
            "openai_admin_key": "sk-admin-test", "codex_budget": "30"}
    form.update(over)
    return form


class SettingsPlanTests(_RuntimeGuard):
    """``plan_settings_save(base_cfg, form)`` with the new form; the transaction is the
    old one (plan → apply → merge_config_updates)."""

    def test_owned_keys_are_the_new_set(self):
        """Rivals: keeping the limit keys owned (a save would rewrite them from the
        snapshot); forgetting a Codex key (it would never be saved)."""
        owned = set(claude_pet.SETTINGS_OWNED_KEYS)
        self.assertEqual(set(NEW_OWNED) - owned, set(), "new keys not owned by the panel")
        self.assertEqual(set(OLD_KEYS) & owned, set(), "removed keys still owned")

    def test_a_new_form_plans_without_any_removed_field(self):
        """No weekly-reset hour, no limits, no % — the plan goes through. Today it fails
        on the missing hour (``s_err_hour``)."""
        plan, err = claude_pet.plan_settings_save({}, new_form())
        self.assertIsNone(err)
        upd = plan["updates"]
        self.assertEqual(upd["show_claude"], True)
        self.assertEqual(upd["claude_gauges"], ["session", "weekly"])
        self.assertEqual(upd["show_codex"], False)
        self.assertEqual(upd["codex_mode"], "api")
        self.assertEqual(upd["codex_gauges"], ["weekly"])
        self.assertEqual(upd["openai_admin_key"], "sk-admin-test")
        self.assertEqual(upd["codex_budget"], 30.0)
        self.assertEqual(upd["api_budget"], 0.0)
        self.assertEqual(set(OLD_KEYS) & set(upd), set())

    def test_budgets_are_validated_separately(self):
        """Rivals: one shared message (a bad Codex budget reported as the Claude one);
        the Codex budget not validated at all; coercing a bad value to 0."""
        bad = ("-1", "abc", "nan", "inf", "1%2")
        for raw in bad:
            with self.subTest(codex_budget=raw):
                plan, err = claude_pet.plan_settings_save({}, new_form(codex_budget=raw))
                self.assertIsNone(plan)
                self.assertEqual(err, claude_pet.t("s_err_codex_budget"))
            with self.subTest(api_budget=raw):
                plan, err = claude_pet.plan_settings_save({}, new_form(api_budget=raw))
                self.assertIsNone(plan)
                self.assertEqual(err, claude_pet.t("s_err_budget"))
        plan, err = claude_pet.plan_settings_save({}, new_form(codex_budget="12.50"))
        self.assertIsNone(err)
        self.assertEqual(plan["updates"]["codex_budget"], 12.5)

    def test_both_providers_off_is_a_valid_save(self):
        plan, err = claude_pet.plan_settings_save({}, new_form(show_claude=False,
                                                               show_codex=False))
        self.assertIsNone(err)
        self.assertFalse(plan["updates"]["show_claude"])
        self.assertFalse(plan["updates"]["show_codex"])

    def test_old_limit_keys_stay_in_the_file_and_never_reach_runtime(self):
        """§1: old keys are neither read nor deleted. A real save through the transaction
        against a temp config file.

        Rivals: deleting the old keys on save (rewrites the user's file); copying them
        into the update (they would be owned again); ``apply_config`` loading them."""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, ".claude_pet.json")
            disk = {"x": 5, "session_limit": 12_345_678, "weekly_limit": 98_765_432,
                    "opus_limit": 23_456_789, "model_keyword": "opus",
                    "weekly_reset_day": 2, "weekly_reset_hour": 9}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(disk, f)
            with mock.patch.object(claude_pet, "CONFIG_PATH", path):
                cfg = dict(disk)
                plan, err = claude_pet.plan_settings_save(cfg, new_form())
                self.assertIsNone(err)
                self.assertEqual(set(OLD_KEYS) & set(plan["updates"]), set())
                ok, merged = claude_pet.apply_settings_plan(plan, cfg,
                                                            apply_fn=claude_pet.apply_config)
                self.assertTrue(ok)
            with open(path, encoding="utf-8") as f:
                on_disk = json.load(f)
        for key in OLD_KEYS:
            self.assertEqual(on_disk[key], disk[key], f"{key} was rewritten or deleted")
        self.assertEqual(on_disk["codex_budget"], 30.0)
        self.assertEqual(set(OLD_KEYS) & set(claude_pet.RUNTIME), set())

    def test_the_plan_never_scans_logs(self):
        """There is nothing left to back-solve, so planning must not read usage."""
        with mock.patch.object(claude_pet, "compute_usage",
                               side_effect=AssertionError("settings save read the logs")), \
                mock.patch.object(claude_pet, "parse_usage_entries",
                                  side_effect=AssertionError("settings save read the logs")):
            plan, err = claude_pet.plan_settings_save({}, new_form())
        self.assertIsNone(err)


# ═════════════════════ §7 — Codex onboarding (core half) ═════════════════════

class CodexOnboardTests(_RuntimeGuard):
    """``compute_codex_onboard_state(show_codex, codex_mode, has_token, cli_present,
    codex_home_exists)`` and the two Terminal helpers.

    Round 2 (Coordinator, 2026-10-05): the Codex items appear only when Codex is in use —
    the CLI is found or the Codex home directory exists. Neither → None even when shown.
    CLI absent + home present → "install"; CLI present + no token → "login".
    """

    def test_truth_table(self):
        """Rivals: the round-1 four-argument rule (no CLI, no home → "install" — offers
        Codex to every user who never touched it); "login" without a CLI; offering
        anything when hidden, in API mode, or with a token."""
        fn = need(self, "compute_codex_onboard_state")
        self.assertIsNone(fn(False, "sub", False, True, True))
        self.assertIsNone(fn(True, "api", False, True, True))
        self.assertIsNone(fn(True, "sub", True, True, True))
        self.assertIsNone(fn(True, "sub", False, False, False),
                          "Codex not in use (no CLI, no ~/.codex) must offer nothing")
        self.assertEqual(fn(True, "sub", False, False, True), "install")
        self.assertEqual(fn(True, "sub", False, True, False), "login")
        self.assertEqual(fn(True, "sub", False, True, True), "login")

    def test_codex_home_exists_follows_the_root_rule(self):
        """``codex_home_exists(env=None, home=None)`` — the directory ``codex_auth_path``
        lives in ($CODEX_HOME, else <home>/.codex) is a directory."""
        fn = need(self, "codex_home_exists")
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(fn(env={}, home=td))
            os.mkdir(os.path.join(td, ".codex"))
            self.assertTrue(fn(env={}, home=td))
            other = os.path.join(td, "cx")
            self.assertFalse(fn(env={"CODEX_HOME": other}, home=td),
                             "$CODEX_HOME wins over ~/.codex")
            os.mkdir(other)
            self.assertTrue(fn(env={"CODEX_HOME": other}, home=td))
            with open(os.path.join(td, "afile"), "w") as f:
                f.write("x")
            self.assertFalse(fn(env={"CODEX_HOME": os.path.join(td, "afile")}, home=td))

    def test_terminal_commands(self):
        """macOS runs the official npm package and ``codex login`` in Terminal, the same
        way ``start_claude_install`` does. Nothing is executed: ``_run_in_terminal`` is
        replaced by a recorder."""
        install = need(self, "start_codex_install")
        login = need(self, "start_codex_login")
        seen = []
        with mock.patch.object(claude_pet, "_run_in_terminal", side_effect=seen.append):
            install()
            login()
        self.assertEqual(len(seen), 2)
        self.assertIn("npm install -g @openai/codex", seen[0])
        self.assertIn("codex login", seen[1])

    def test_codex_token_is_never_refreshed_by_us(self):
        """§7: no Codex auto-refresh. Source-level: nothing posts to the OpenAI token
        endpoint and nothing opens ``auth.json`` for writing."""
        self.assertNotIn("auth.openai.com/oauth/token", SOURCE)


# ═════════════════════ macOS GUI wiring (AST only) ═════════════════════

def _run_gui_tree():
    tree = ast.parse(SOURCE)
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_gui")


def _nested(tree, name):
    found = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return found[0] if len(found) == 1 else None


def _t_keys(node):
    return {c.args[0].value for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "t"
            and c.args and isinstance(c.args[0], ast.Constant)
            and isinstance(c.args[0].value, str)}


def _str_consts(node):
    return {n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _called_names(node):
    out = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            if isinstance(c.func, ast.Name):
                out.add(c.func.id)
            elif isinstance(c.func, ast.Attribute):
                out.add(c.func.attr)
    return out


def _reachable_module_calls(node, depth=2):
    """Names called from ``node``, following module-level functions ``depth`` levels."""
    tree = ast.parse(SOURCE)
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    seen, frontier = set(), _called_names(node)
    for _ in range(depth + 1):
        seen |= frontier
        nxt = set()
        for name in frontier:
            if name in module_fns:
                nxt |= _called_names(module_fns[name]) - seen
        frontier = nxt
    return seen


class MacGuiWiringTests(unittest.TestCase):
    """Source-level checks of the ``run_gui`` closures, in the style of
    ``tests/test_autostart.py``. They cannot run without AppKit, so they read the code."""

    def test_the_settings_panel_has_two_provider_sections_and_fits_768(self):
        """§2. Rivals: keeping the calibration/limit rows; a panel taller than 656."""
        run_gui = _run_gui_tree()
        open_settings = _nested(run_gui, "open_settings")
        self.assertIsNotNone(open_settings)
        keys = _t_keys(open_settings)
        for key in ("s_sec_claude", "s_sec_codex", "s_show_in_pill", "s_gauge_session",
                    "s_gauge_weekly", "s_gauge_model", "s_gauge_credit", "s_openai_key",
                    "s_codex_budget", "s_codex_mode_sub", "s_codex_mode_api"):
            with self.subTest(key=key):
                self.assertIn(key, keys)
        left = sorted(k for k in keys if k.startswith(("s_calib", "s_limit_", "s_g_"))
                      or k in ("s_model_kw", "s_weekly_reset", "s_rolling7", "s_hour"))
        self.assertEqual(left, [])
        heights = [n.value.elts[1].value for n in ast.walk(open_settings)
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple)
                   and [getattr(e, "id", None) for e in n.targets[0].elts] == ["PWID", "PHT"]
                   and isinstance(n.value, ast.Tuple)
                   and isinstance(n.value.elts[1], ast.Constant)]
        self.assertEqual(len(heights), 1, "open_settings must size its panel as PWID, PHT")
        self.assertLessEqual(heights[0], 656)

    def test_the_advanced_limits_window_is_gone(self):
        run_gui = _run_gui_tree()
        for name in ("open_advanced_limits", "close_advanced", "adv_value"):
            with self.subTest(name=name):
                self.assertIsNone(_nested(run_gui, name), f"{name} still defined")

    def test_save_settings_collects_the_new_keys(self):
        save = _nested(_run_gui_tree(), "save_settings")
        self.assertIsNotNone(save)
        consts = _str_consts(save)
        for key in ("show_claude", "claude_gauges", "show_codex", "codex_mode",
                    "codex_gauges", "openai_admin_key", "codex_budget"):
            with self.subTest(key=key):
                self.assertIn(key, consts)

    def test_the_context_menu_offers_codex_install_and_login(self):
        """§7. ``rightMouseDown_`` builds the items from ``state["codex_onboard"]``;
        ``Handler.installCodex_`` / ``loginCodex_`` call the two Terminal helpers."""
        run_gui = _run_gui_tree()
        menu = _nested(run_gui, "rightMouseDown_")
        self.assertIsNotNone(menu)
        self.assertLessEqual({"menu_install_codex", "menu_login_codex"}, _t_keys(menu))
        self.assertLessEqual({"installCodex:", "loginCodex:", "codex_onboard"}, _str_consts(menu))
        for handler, helper in (("installCodex_", "start_codex_install"),
                                ("loginCodex_", "start_codex_login")):
            with self.subTest(handler=handler):
                fn = _nested(run_gui, handler)
                self.assertIsNotNone(fn, f"Handler.{handler} missing")
                self.assertIn(helper, _called_names(fn))

    def test_the_refresh_worker_learns_jumps_and_prices_codex(self):
        """The 30-second worker: learns limits (``learn_lane``, directly or through a
        module helper), jumps on ``session_reset_jump``, fetches the Codex cost in Codex
        API mode, and computes the Codex onboarding state."""
        refresh = _nested(_run_gui_tree(), "refresh_")
        self.assertIsNotNone(refresh)
        reach = _reachable_module_calls(refresh)
        for name in ("learn_lane", "session_reset_jump", "fetch_codex_cost_today",
                     "compute_codex_onboard_state", "parse_codex_entries", "codex_spikes"):
            with self.subTest(name=name):
                self.assertIn(name, reach)


# ═════════════════════ Round 2 (Coordinator decisions after review, 2026-10-05) ═════════════════════

class ClaudeOnboardOnTokenTests(_RuntimeGuard):
    """R2-1: ``compute_onboard_state(oauth, has_token)`` — onboarding depends on whether a
    Claude OAuth token exists, not on log entries. A token with no server rows (outage)
    shows no onboarding. The parameter is named ``has_token``; tests pass it by keyword so
    the round-1 ``stats_have_logs`` signature fails loudly."""

    def setUp(self):
        super().setUp()
        env = dict(os.environ)
        env.pop("CLAUDE_PET_FORCE_ONBOARD", None)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        claude_pet.RUNTIME["mode"] = "sub"

    def test_truth_table(self):
        with mock.patch.object(claude_pet, "_find_claude_cli", return_value="/x/claude"):
            self.assertEqual(claude_pet.compute_onboard_state(None, has_token=False), "login")
            self.assertIsNone(claude_pet.compute_onboard_state(None, has_token=True),
                              "a token without server rows is an outage, not a sign-in")
            self.assertIsNone(claude_pet.compute_onboard_state(
                [("Session", 1.0, None, None)], has_token=True))
        with mock.patch.object(claude_pet, "_find_claude_cli", return_value=None):
            self.assertEqual(claude_pet.compute_onboard_state(None, has_token=False), "install")
        claude_pet.RUNTIME["mode"] = "api"
        self.assertIsNone(claude_pet.compute_onboard_state(None, has_token=False))

    def test_the_mac_call_site_passes_a_token_flag_not_entries(self):
        """Rival: round 1's ``bool(s.get("entries"))`` — logs suppress the sign-in item for
        a user whose token is gone."""
        refresh = _nested(_run_gui_tree(), "refresh_")
        calls = [c for c in ast.walk(refresh) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", None) == "compute_onboard_state"]
        self.assertEqual(len(calls), 1)
        args = [ast.unparse(a) for a in calls[0].args[1:]] + \
               [ast.unparse(k.value) for k in calls[0].keywords]
        flag = " ".join(args)
        self.assertNotIn("entries", flag)
        self.assertIn("token", flag.lower(), f"onboarding flag is not token-derived: {flag!r}")


class CodexParsePrefilterTests(unittest.TestCase):
    """R2-3: a line without the substring ``"token_count"`` never reaches ``json.loads``."""

    def test_non_token_lines_are_not_decoded(self):
        now = datetime.now(UTC)
        ts = (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
        token = {"type": "event_msg", "timestamp": ts,
                 "payload": {"type": "token_count",
                             "info": {"last_token_usage": {"input_tokens": 0,
                                                           "cached_input_tokens": 0,
                                                           "output_tokens": 4},
                                      "total_token_usage": {"total_tokens": 9}}}}
        noise = {"type": "response_item", "timestamp": ts,
                 "payload": {"type": "message", "content": "x" * 200}}
        with tempfile.TemporaryDirectory() as td:
            root = os.path.join(td, "sessions")
            os.makedirs(os.path.join(root, "2026"))
            with open(os.path.join(root, "2026", "r.jsonl"), "w", encoding="utf-8") as f:
                for i in range(60):
                    f.write(json.dumps(noise) + "\n")
                    if i in (10, 40):
                        token["payload"]["info"]["total_token_usage"]["total_tokens"] = 9 + i
                        f.write(json.dumps(token) + "\n")
            real = json.loads
            calls = []
            with mock.patch.object(claude_pet.json, "loads",
                                   side_effect=lambda *a, **k: calls.append(1) or real(*a, **k)):
                rows = claude_pet.parse_codex_entries(now - timedelta(days=7), root=root)
        self.assertEqual([r[1] for r in rows], [20.0, 20.0])
        self.assertEqual(len(calls), 2, f"json.loads ran {len(calls)} times for 2 token lines")


class LearnOnlyOnFreshReadingTests(_RuntimeGuard):
    """R2-4: ``learn_server_limits(oauth_rows, codex_rows, entries, codex_entries,
    learned=None, model_kw=None, claude_fetch=None, codex_fetch=None)``.

    ``claude_fetch`` / ``codex_fetch`` identify the server reading (the fetch time of the
    cached response). A provider whose key equals the one recorded at its last learning is
    skipped — the EMA is not re-applied to a cached row. ``None`` means "always learn"
    (one-shot callers such as ``--report``). Keys are per provider.
    """

    R = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)

    def rows(self):
        return [(claude_pet.t("session"), 40.0, self.R, None)]

    def codex(self):
        return [("codex_session", 40.0, self.R, None)]

    def entries(self, total):
        return [entry(self.R - timedelta(hours=1), total, model="claude-x")]

    def codex_entries(self, total):
        return [(self.R - timedelta(hours=1), float(total), "codex", float(total))]

    def test_the_same_reading_is_not_learned_twice(self):
        """First reading: T 2000 at 40 % → 5000. The same cached reading again with T 4000:
        unchanged (rival: re-applying the EMA → 6500). A new reading: 6500."""
        fn = claude_pet.learn_server_limits
        learned = {}
        fn(self.rows(), None, self.entries(2_000), [], learned=learned, claude_fetch=100.0)
        self.assertAlmostEqual(learned["session"], 5_000.0)
        fn(self.rows(), None, self.entries(4_000), [], learned=learned, claude_fetch=100.0)
        self.assertAlmostEqual(learned["session"], 5_000.0, msg="EMA re-applied to a cached row")
        fn(self.rows(), None, self.entries(4_000), [], learned=learned, claude_fetch=280.0)
        self.assertAlmostEqual(learned["session"], 6_500.0)

    def test_keys_are_per_provider(self):
        """Same Claude reading, new Codex reading → only Codex learns again."""
        fn = claude_pet.learn_server_limits
        learned = {}
        fn(self.rows(), self.codex(), self.entries(2_000), self.codex_entries(2_000),
           learned=learned, claude_fetch=1.0, codex_fetch=1.0)
        fn(self.rows(), self.codex(), self.entries(4_000), self.codex_entries(4_000),
           learned=learned, claude_fetch=1.0, codex_fetch=2.0)
        self.assertAlmostEqual(learned["session"], 5_000.0)
        self.assertAlmostEqual(learned["codex_session"], 6_500.0)

    def test_none_always_learns(self):
        """NOT A GATE — green against 67c7312 (it always learns). Guards the one-shot
        caller contract while the fetch keys are added."""
        fn = claude_pet.learn_server_limits
        learned = {}
        fn(self.rows(), None, self.entries(2_000), [], learned=learned)
        fn(self.rows(), None, self.entries(4_000), [], learned=learned)
        self.assertAlmostEqual(learned["session"], 6_500.0)

    def test_the_refresh_worker_passes_both_fetch_keys(self):
        """macOS ``refresh_`` passes non-constant ``claude_fetch=`` and ``codex_fetch=``."""
        refresh = _nested(_run_gui_tree(), "refresh_")
        calls = [c for c in ast.walk(refresh) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", None) == "learn_server_limits"]
        self.assertEqual(len(calls), 1)
        kws = {k.arg: k.value for k in calls[0].keywords}
        for key in ("claude_fetch", "codex_fetch"):
            with self.subTest(key=key):
                self.assertIn(key, kws)
                self.assertNotIsInstance(kws[key], ast.Constant)


class SpikeMarkNeverOnCreditTests(unittest.TestCase):
    """R2-6a: the Claude spike marks the first visible row (the adapter filters hidden
    gauges first), but never the credit row."""

    def test_credit_row_is_never_marked(self):
        credit = claude_pet.t("credit")
        kind, rows = claude_pet.roam_summary("sub", [(credit, 30.0, None)], None, None,
                                             None, False, spike_first=True)
        self.assertEqual(kind, "exact")
        self.assertEqual([r[2] for r in rows], [False])

    def test_first_visible_gauge_row_is_marked_when_session_is_hidden(self):
        """NOT A GATE — green against 67c7312 (the adapter already filters before
        ``roam_summary``). Regression guard for the "first visible row" half of R2-6a."""
        credit, weekly = claude_pet.t("credit"), claude_pet.t("weekly")
        kind, rows = claude_pet.roam_summary("sub", [(weekly, 30.0, None), (credit, 5.0, None)],
                                             None, None, None, False, spike_first=True)
        self.assertEqual([r[2] for r in rows], [True, False])


class MoodOnShownGaugesTests(_RuntimeGuard):
    """R2-6b: ``mood_for(stats, rows=None, runtime=None, codex_rows=None)`` — ``rows`` are
    Claude server rows, ``codex_rows`` Codex rows; only shown providers' selected gauges
    count."""

    RT = {"mode": "sub", "codex_mode": "sub", "show_claude": True, "show_codex": True,
          "claude_gauges": ["weekly"], "codex_gauges": ["weekly"]}

    def claude_rows(self):
        return [(claude_pet.t("session"), 90.0, None, None),
                (claude_pet.t("weekly"), 10.0, None, None)]

    def test_hidden_claude_gauge_does_not_drive_the_mood(self):
        """Rival: worst over every row → "failed" from the hidden 90 % session row."""
        self.assertEqual(claude_pet.mood_for(None, self.claude_rows(), dict(self.RT)), "idle")
        rt = dict(self.RT, claude_gauges=["session", "weekly"])
        self.assertEqual(claude_pet.mood_for(None, self.claude_rows(), rt), "failed")
        rt = dict(self.RT, claude_gauges=["session"], show_claude=False)
        self.assertEqual(claude_pet.mood_for(None, self.claude_rows(), rt), "idle")

    def test_codex_rows_are_filtered_by_codex_gauges(self):
        codex = [("codex_session", 90.0, None, None), ("codex_weekly", 55.0, None, None)]
        self.assertEqual(claude_pet.mood_for(None, [], dict(self.RT), codex_rows=codex),
                         "waiting")
        rt = dict(self.RT, codex_gauges=["session", "weekly"])
        self.assertEqual(claude_pet.mood_for(None, [], rt, codex_rows=codex), "failed")

    def test_current_mood_passes_codex_rows_separately(self):
        cm = _nested(_run_gui_tree(), "current_mood")
        calls = [c for c in ast.walk(cm) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", None) == "mood_for"]
        self.assertEqual(len(calls), 1)
        self.assertIn("codex_rows", [k.arg for k in calls[0].keywords])


class ConfigCoercionTests(_RuntimeGuard):
    """R2-6c: "false"/"0"/False/0 are false for ``show_*``; a non-list ``*_gauges`` falls
    back to the default, in ``provider_shown`` and in ``apply_config``."""

    def test_provider_shown_coerces(self):
        for false in ("false", "False", "0", False, 0, "no"):
            with self.subTest(value=false):
                self.assertFalse(claude_pet.provider_shown(
                    {"show_claude": false, "claude_gauges": ["weekly"]}, "claude"))
        for true in (True, "true", "1", 1):
            with self.subTest(value=true):
                self.assertTrue(claude_pet.provider_shown(
                    {"show_codex": true, "codex_gauges": ["weekly"]}, "codex"))
        for junk in ("weekly", 5, None, {"weekly": True}):
            with self.subTest(gauges=junk):
                self.assertTrue(claude_pet.provider_shown(
                    {"show_claude": True, "claude_gauges": junk}, "claude"),
                    "a non-list gauge setting must fall back to the default, not hide")

    def test_apply_config_normalises(self):
        lang = claude_pet.L["lang"]
        claude_pet.apply_config({"show_claude": "false", "show_codex": "0",
                                 "claude_gauges": "weekly", "codex_gauges": 7, "lang": lang})
        rt = claude_pet.RUNTIME
        self.assertIs(rt["show_claude"], False)
        self.assertIs(rt["show_codex"], False)
        self.assertEqual(rt["claude_gauges"], ["session", "weekly", "model", "credit"])
        self.assertEqual(rt["codex_gauges"], ["session", "weekly"])
        claude_pet.apply_config({"show_claude": "true", "claude_gauges": ["weekly"],
                                 "lang": lang})
        self.assertIs(rt["show_claude"], True)
        self.assertEqual(rt["claude_gauges"], ["weekly"])


class CodexCostPageCapTests(_RuntimeGuard):
    """R2-6d: running into ``CODEX_COST_MAX_PAGES`` is an error, not a partial success."""

    def test_the_page_cap_reports_an_error(self):
        claude_pet.RUNTIME["openai_admin_key"] = "sk-admin-SYNTHETIC"
        status = claude_pet.CODEX_API_STATUS
        saved = dict(status)
        self.addCleanup(lambda: (status.clear(), status.update(saved)))
        status["last_error"] = None
        page = {"data": [{"results": [{"amount": {"value": 1.0}}]}],
                "has_more": True, "next_page": "more"}
        calls = []

        def fake(req, timeout=None):
            calls.append(req)
            return io.BytesIO(json.dumps(page).encode())

        with mock.patch.object(claude_pet, "CODEX_COST_MAX_PAGES", 3), \
                mock.patch.object(claude_pet.urllib.request, "urlopen", side_effect=fake), \
                mock.patch.object(claude_pet, "_dbg"):
            value = claude_pet.fetch_codex_cost(datetime(2026, 10, 1, tzinfo=UTC))
        self.assertEqual(len(calls), 3)
        self.assertIsNone(value, "a truncated sum was reported as the cost")
        self.assertIsNotNone(status["last_error"])
        self.assertEqual(claude_pet.api_error_kind(status["last_error"]), "transient")


class ReportReasonTests(_RuntimeGuard):
    """R2-6e: ``--report`` with no server rows prints a reason line,
    ``t("r_no_server_rows")`` (new TR key, all four locales)."""

    def test_reason_line(self):
        for lang in claude_pet.SUPPORTED_LANGS:
            with self.subTest(lang=lang):
                self.assertTrue(str(claude_pet.TR[lang].get("r_no_server_rows", "")).strip())
        stats = {"entries": 0, "spikes": {}, "burn_5m": 0.0, "burn_5m_opus": 0.0,
                 "last_activity": None, "now": datetime.now(UTC), "model_kw": "opus",
                 "rows": []}
        out = io.StringIO()
        with mock.patch.object(claude_pet, "compute_usage", return_value=stats), \
                mock.patch.object(claude_pet, "fetch_exact_usage", return_value=None), \
                mock.patch.object(claude_pet, "fetch_codex_usage", return_value=None), \
                mock.patch.object(claude_pet, "fetch_api_cost_today", return_value=None), \
                mock.patch.object(claude_pet, "parse_codex_entries", return_value=[]), \
                redirect_stdout(out):
            claude_pet.print_report()
        self.assertIn(claude_pet.t("r_no_server_rows"), out.getvalue())


class MacCodexOnboardCallSiteTests(unittest.TestCase):
    """R2-2, macOS call site: five arguments (or ``codex_home_exists=``), and the refresh
    worker reaches ``codex_home_exists``."""

    def test_call_site(self):
        refresh = _nested(_run_gui_tree(), "refresh_")
        calls = [c for c in ast.walk(refresh) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", None) == "compute_codex_onboard_state"]
        self.assertEqual(len(calls), 1)
        c = calls[0]
        self.assertTrue(len(c.args) == 5 or "codex_home_exists" in [k.arg for k in c.keywords])
        self.assertIn("codex_home_exists", _reachable_module_calls(refresh))


if __name__ == "__main__":
    unittest.main()
