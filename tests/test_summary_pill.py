"""Gates for the unified summary pill (staged v0.24).

Owner: Verifier (verifier-v024). The pill's content, colouring, fitting and geometry
are pure functions at module level, so this module takes them through a plain
``import claude_pet`` — the module launches nothing at import — and never creates a
window. The font/packaging gates read ``fonts/``, ``setup.py`` and ``build_app.sh`` as
bytes, AST and text; neither script is sourced or executed.

The tree under test is the one ``claude_pet`` was imported from, and every test checks
that it is the same tree the files are read from (``ROOT``). That is what lets the red
runs execute this very file from a scratch copy of the pre-change tree.

Rivals each fixture separates are listed on the test. Red/green evidence:
docs-design/summary-unify-verification-20260912.md.

User decisions pinned (2026-09-12, verbatim in CLAUDE.md / the change description):
one roaming summary pill for both ``full`` and ``summary``; the *value* run carries the
source colour (exact emerald, estimate amber, API cost coral) and the *label* run is
white, turning at 50 % and 85 % and on a spike; the reset times on a second line;
Pretendard bundled; extension by appending segments.

Round 2 (after the Reviewer's B1): a toggle during the arrival latch *dismisses* the
pill for that visit and leaves the stored preference alone — ``RoamDisplay.dismissed``
replaces the round-1 "clear the latch and flip" contract, which turned a folded
preference into an open one after every visit. The API cost segment gained the monthly
budget: ``("cost", (today, month | None, budget | None))``. The dead pill code and the
translation keys it alone used are gone from all four locales.

Round 3 (user, 2026-09-12: "세션이나 주간 이 텍스트랑 수치랑 색을 반대로 하자!"): the two
colour roles are swapped — the LABEL run (session/weekly/model, today/this month) takes
``summary_value_kind(pct, spiking)`` and the VALUE run (`` 42%``, ``$3.21``) takes the
source kind; in the cost line the word "this month" is coloured by the budget share and
the amounts are ``cost``. The bundled font is now the TrueType ``Pretendard-SemiBold.ttf``
(first four bytes ``00 01 00 00``); the CFF ``.otf`` is gone.
"""
from __future__ import annotations

import ast
import math
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import claude_pet

ROOT = Path(__file__).resolve().parents[1]


def tr(key):
    """A translation stub that is visibly not the identity for the keys the pill uses."""
    return {"reset_prefix": "reset ", "session": "세션", "weekly": "주간",
            "today": "Today", "this_month": "This month",
            "scanning": "scanning…", "loading": "loading…"}.get(key, key)


def text_of(runs):
    return "".join(text for text, _kind in runs)


def zsh_function(source, name):
    """One ``name() { ... }`` definition of a zsh script, as text, by brace matching."""
    header = f"{name}() {{"
    if source.count(header) != 1:
        raise AssertionError(f"expected exactly one {header!r} in build_app.sh")
    start = source.index(header)
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated function {name}")


class TreeConsistencyMixin:
    def assert_same_tree(self):
        self.assertEqual(Path(claude_pet.__file__).resolve(), (ROOT / "claude_pet.py").resolve(),
                         "claude_pet was imported from a different tree than the one being read")


class SummaryRowsTests(TreeConsistencyMixin, unittest.TestCase):
    """roam_summary(): which rows, in what shape."""

    def summary(self, **overrides):
        self.assert_same_tree()
        args = dict(mode="sub", oauth=None, stats=None, onboard=None,
                    cost_today=None, has_admin_key=False)
        args.update(overrides)
        return claude_pet.roam_summary(**args)

    def test_exact_keeps_three_gauge_rows_in_order_as_4_tuples(self):
        """Rivals: first two rows (the old contract); no cap (a fourth 'Credits' row);
        2-tuples; reset text dropped."""
        oauth = [("Session", 42.0, "in 3h"), ("Weekly", 67.5, "in 2d"),
                 ("Fable", 92.0, "in 2d"), ("Credits", 5.0, None)]
        self.assertEqual(self.summary(oauth=oauth),
                         ("exact", [("Session", 42.0, False, "in 3h"),
                                    ("Weekly", 67.5, False, "in 2d"),
                                    ("Fable", 92.0, False, "in 2d")]))

    def test_exact_spike_first_marks_only_the_first_given_row(self):
        """Rivals: spike on every row; spike ignored; spike moved onto the first *kept*
        row when the session row is invalid."""
        oauth = [("Session", 42.0, "in 3h"), ("Weekly", 67.5, "in 2d"), ("Fable", 92.0, None)]
        kind, rows = self.summary(oauth=oauth, spike_first=True)
        self.assertEqual(kind, "exact")
        self.assertEqual([row[2] for row in rows], [True, False, False])
        kind, rows = self.summary(oauth=oauth, spike_first=False)
        self.assertEqual([row[2] for row in rows], [False, False, False])
        invalid_session = [("Session", float("nan"), "x"), ("Weekly", 41.0, None),
                           ("Fable", 93.0, None), ("Credits", 5.0, None)]
        self.assertEqual(self.summary(oauth=invalid_session, spike_first=True),
                         ("exact", [("Weekly", 41.0, False, None), ("Fable", 93.0, False, None)]),
                         "an invalid session row must neither pull in the fourth row nor "
                         "hand its spike mark to the next row")

    def test_exact_reset_text_is_passed_through_verbatim_or_none(self):
        """Rivals: an empty string kept as ''; a missing third element raising; a
        non-string (datetime) passed through untouched."""
        oauth = [("Session", 1.0), ("Weekly", 2.0, ""), ("Fable", 3.0, "3시간 43분 후")]
        self.assertEqual(self.summary(oauth=oauth)[1],
                         [("Session", 1.0, False, None), ("Weekly", 2.0, False, None),
                          ("Fable", 3.0, False, "3시간 43분 후")])
        self.assertEqual(self.summary(oauth=[("Session", 1.0, object())])[1],
                         [("Session", 1.0, False, None)])

    def test_estimate_adds_the_model_row_with_capitalised_keyword_and_per_gauge_spikes(self):
        """Rivals: session+weekly only (old); label 'fable' uncapitalised; label 'opus'
        regardless of model_kw; spike flag from spike_first/any gauge; 2-tuples."""
        stats = {"session": {"pct": 42.0}, "weekly": {"pct": 67.5}, "opus": {"pct": 12.0},
                 "model_kw": "fable", "spikes": {"weekly": True}}
        self.assertEqual(self.summary(stats=stats),
                         ("estimate", [("session", 42.0, False, None),
                                       ("weekly", 67.5, True, None),
                                       ("Fable", 12.0, False, None)]))
        stats["spikes"] = {"opus": True}
        self.assertEqual([row[2] for row in self.summary(stats=stats)[1]], [False, False, True])
        stats["model_kw"] = "mythos"
        self.assertEqual(self.summary(stats=stats)[1][2][0], "Mythos")
        del stats["model_kw"]
        self.assertEqual(self.summary(stats=stats)[1][2][0], "Opus")

    def test_estimate_tolerates_missing_or_malformed_spikes_and_model_gauge(self):
        """Rivals: KeyError on a missing 'spikes'; a non-dict 'spikes' treated as truthy;
        an invalid model pct reported as 0."""
        base = {"session": {"pct": 42.0}, "weekly": {"pct": 17.0}, "model_kw": "fable"}
        self.assertEqual(self.summary(stats=dict(base))[1],
                         [("session", 42.0, False, None), ("weekly", 17.0, False, None)])
        for spikes in (None, [], "weekly", True):
            with self.subTest(spikes=repr(spikes)):
                rows = self.summary(stats=dict(base, spikes=spikes, opus={"pct": 3.0}))[1]
                self.assertEqual([row[2] for row in rows], [False, False, False])
        for invalid in (None, True, -1.0, float("inf"), "12"):
            with self.subTest(invalid=repr(invalid)):
                rows = self.summary(stats=dict(base, opus={"pct": invalid}))[1]
                self.assertEqual([row[0] for row in rows], ["session", "weekly"])

    def test_estimate_reset_texts_flow_through_by_gauge_key(self):
        """Rivals: reset text computed inside (a datetime leaking out); keyed by label
        instead of gauge ('Fable' vs 'opus'); '' kept instead of None; a non-dict raising."""
        stats = {"session": {"pct": 1.0}, "weekly": {"pct": 2.0}, "opus": {"pct": 3.0},
                 "model_kw": "fable"}
        resets = {"session": "in 3h", "weekly": "in 2d", "opus": "in 2d", "Fable": "WRONG"}
        self.assertEqual([row[3] for row in self.summary(stats=stats, reset_texts=resets)[1]],
                         ["in 3h", "in 2d", "in 2d"])
        self.assertEqual([row[3] for row in self.summary(stats=stats, reset_texts={"session": ""})[1]],
                         [None, None, None])
        self.assertEqual([row[3] for row in self.summary(stats=stats, reset_texts=["in 3h"])[1]],
                         [None, None, None])

    def test_cost_carries_today_month_and_budget_or_none(self):
        """Rivals: the old bare float; the round-1 2-tuple without the budget; the
        month or budget passed through unvalidated (nan, str, bool); a zero or
        negative budget kept (it would divide the month by zero downstream); the
        budget only accepted alongside a month."""
        api = dict(mode="api", has_admin_key=True)
        self.assertEqual(self.summary(cost_today=12.375, cost_month=27.5, cost_budget=50, **api),
                         ("cost", (12.375, 27.5, 50.0)))
        self.assertEqual(self.summary(cost_today=12.375, cost_month=27.5, **api),
                         ("cost", (12.375, 27.5, None)))
        self.assertEqual(self.summary(cost_today=12.375, **api), ("cost", (12.375, None, None)))
        self.assertEqual(self.summary(cost_today=12.375, cost_budget=50, **api),
                         ("cost", (12.375, None, 50.0)))
        self.assertEqual(self.summary(cost_today=0, cost_month=0, **api), ("cost", (0.0, 0.0, None)))
        for invalid in (float("nan"), float("inf"), -1.0, "27", True, None):
            with self.subTest(invalid_month=repr(invalid)):
                self.assertEqual(self.summary(cost_today=1.0, cost_month=invalid, **api),
                                 ("cost", (1.0, None, None)))
        for invalid in (float("nan"), float("inf"), -1.0, 0, 0.0, "50", True, None):
            with self.subTest(invalid_budget=repr(invalid)):
                self.assertEqual(self.summary(cost_today=1.0, cost_month=2.0, cost_budget=invalid, **api),
                                 ("cost", (1.0, 2.0, None)))
        self.assertEqual(self.summary(cost_today=None, cost_month=5.0, cost_budget=50, **api),
                         ("status", "loading"))
        self.assertEqual(self.summary(mode="api", cost_today=1.0, cost_month=5.0, cost_budget=50),
                         ("status", "need_admin_key"))


class SummaryValueKindTests(unittest.TestCase):
    def test_thresholds_are_50_and_85_inclusive_and_spike_wins(self):
        """Rivals: strict '>' thresholds; 85 % as 'warn'; spiking ignored; spiking only
        above some percentage."""
        kind = claude_pet.summary_value_kind
        self.assertEqual([kind(p) for p in (0, 49, 49.9, 50, 84.9, 85, 100)],
                         ["value", "value", "value", "warn", "warn", "bad", "bad"])
        for pct in (0, 49, 50, 85):
            with self.subTest(pct=pct):
                self.assertEqual(kind(pct, spiking=True), "bad")
        self.assertEqual(kind(49, spiking=False), "value")


class SummaryRunsTests(unittest.TestCase):
    """roam_summary_runs(): the coloured pieces the renderer draws."""

    exact_rows = [("Session", 42.0, True, "in 3h"), ("Weekly", 67.5, False, "in 2d"),
                  ("Fable", 92.0, False, "in 2d")]

    def test_exact_rows_colour_labels_by_remaining_values_emerald_and_spike_prefix(self):
        """Round 3. Rivals: the round-2 assignment (label 'exact', value by remaining —
        every value below would read 'bad'/'warn'/'bad' and every label 'exact');
        both runs by source; both runs by remaining; the ▲ on the value run; the spike
        label coloured 'exact'; separator kind 'exact'; percentages unrounded."""
        main, sub = claude_pet.roam_summary_runs([("exact", self.exact_rows)], tr)
        self.assertEqual(main, [("▲Session", "bad"), (" 42%", "exact"), (" · ", "status"),
                                ("Weekly", "warn"), (" 68%", "exact"), (" · ", "status"),
                                ("Fable", "bad"), (" 92%", "exact")])
        self.assertEqual(text_of(main), "▲Session 42% · Weekly 68% · Fable 92%")
        self.assertEqual(claude_pet.roam_summary_line("exact", self.exact_rows, tr), text_of(main))
        self.assertEqual(claude_pet.SUMMARY_SPIKE, "▲")

    def test_estimate_rows_translate_gauge_keys_keep_model_label_and_mark_approx(self):
        """Rivals: labels untranslated; the model label passed through tr; no ≈; the
        round-2 assignment (label 'estimate', value white/warn/bad); value kind
        'exact'; a spiking label whose value run is also 'bad'."""
        rows = [("session", 42.0, False, None), ("weekly", 50.0, False, None),
                ("Fable", 12.0, True, None)]
        main, sub = claude_pet.roam_summary_runs([("estimate", rows)], tr)
        self.assertEqual(main, [("세션", "value"), (" ≈42%", "estimate"), (" · ", "status"),
                                ("주간", "warn"), (" ≈50%", "estimate"), (" · ", "status"),
                                ("▲Fable", "bad"), (" ≈12%", "estimate")])
        self.assertEqual(sub, [])
        self.assertEqual(claude_pet.roam_summary_line("estimate", rows, tr),
                         "세션 ≈42% · 주간 ≈50% · ▲Fable ≈12%")

    def test_second_line_has_the_prefix_once_and_collapses_consecutive_duplicates(self):
        """Rivals: prefix per row; all duplicates collapsed (a set); no collapsing;
        prefix on the first line; exact reset texts re-prefixed."""
        main, sub = claude_pet.roam_summary_runs([("exact", self.exact_rows)], tr)
        self.assertEqual(sub, [("reset ", "sub"), ("Session in 3h", "sub"),
                               (" · ", "sub"), ("Weekly in 2d", "sub")])
        self.assertEqual(claude_pet.roam_summary_reset_line("exact", self.exact_rows, tr),
                         "reset Session in 3h · Weekly in 2d")
        self.assertNotIn("reset", text_of(main))
        non_consecutive = [("session", 10.0, False, "3h"), ("weekly", 20.0, False, "2d"),
                           ("Fable", 30.0, False, "3h")]
        self.assertEqual(claude_pet.roam_summary_reset_line("estimate", non_consecutive, tr),
                         "reset 세션 3h · 주간 2d · Fable 3h")
        self.assertEqual(claude_pet.roam_summary_reset_line(
            "estimate", [("session", 1.0, False, None), ("weekly", 2.0, False, None)], tr), "")
        self.assertEqual(claude_pet.roam_summary_reset_line("status", "scanning", tr), "")
        self.assertEqual(claude_pet.roam_summary_reset_line("cost", (1.0, None), tr), "")

    def test_cost_runs_colour_the_month_word_by_budget_and_status_is_one_run(self):
        """Round 3: the words carry the remaining-amount colour, the amounts are coral.
        Rivals: the round-1 single 'cost' run for the whole line; the round-2
        assignment ('Today $12.38' one coral run, 'This month ' coral, the amount by
        budget share); 'Today ' coloured 'cost'; the budget suffix printed when there
        is none; the month kind taken from the absolute dollars rather than the share
        of the budget; the share compared with strict thresholds (25 of 50 is exactly
        50 → 'warn', 42.5 of 50 is exactly 85 → 'bad'); status translated on the
        'exact' kind; two decimals lost; a round-1 2-tuple payload raising."""
        runs = claude_pet.roam_summary_runs
        self.assertEqual(runs([("cost", (12.375, 27.5, None))], tr),
                         ([("Today ", "value"), ("$12.38", "cost"), (" · ", "status"),
                           ("This month ", "value"), ("$27.50", "cost")], []))
        self.assertEqual(runs([("cost", (12.375, 27.5, 50.0))], tr),
                         ([("Today ", "value"), ("$12.38", "cost"), (" · ", "status"),
                           ("This month ", "warn"), ("$27.50", "cost"), (" / $50", "cost")], []))
        self.assertEqual(claude_pet.roam_summary_line("cost", (12.375, 27.5, 50.0), tr),
                         "Today $12.38 · This month $27.50 / $50")
        for month, kind in ((20.0, "value"), (24.99, "value"), (25.0, "warn"), (42.49, "warn"),
                            (42.5, "bad"), (60.0, "bad")):
            with self.subTest(month=month):
                main, sub = runs([("cost", (1.0, month, 50.0))], tr)
                self.assertEqual(main[3], ("This month ", kind))
                self.assertEqual(main[4], (f"${month:.2f}", "cost"))
                self.assertEqual(main[5], (" / $50", "cost"))
                self.assertEqual(main[0], ("Today ", "value"), "today is never budget-coloured")
                self.assertEqual(sub, [])
        self.assertEqual(runs([("cost", (12.375, None, 50.0))], tr),
                         ([("Today ", "value"), ("$12.38", "cost")], []),
                         "no month → no budget suffix either")
        self.assertEqual(runs([("cost", (12.375, None, None))], tr),
                         ([("Today ", "value"), ("$12.38", "cost")], []))
        self.assertEqual(runs([("cost", (12.375, 27.5))], tr),
                         ([("Today ", "value"), ("$12.38", "cost"), (" · ", "status"),
                           ("This month ", "value"), ("$27.50", "cost")], []),
                         "a 2-tuple from an older caller must read as 'no budget'")
        self.assertEqual(runs([("status", "scanning")], tr),
                         ([("scanning…", "status")], []))

    def test_source_kind_sits_on_the_value_run_and_remaining_kind_on_the_label(self):
        """The round-3 swap, stated as an invariant over every row of every source:
        each run holding a percentage is coloured by its *source* and nothing else is;
        each label run is coloured by its *remaining amount* (white/warn/bad) and never
        by its source. Rivals: the round-2 assignment (exactly inverted — every
        assertion below fails); both runs by source (labels 'exact'); both runs by
        remaining (values never 'exact'/'estimate'); the swap applied to one source
        only; the cost line swapped the other way round (amounts 'value')."""
        rows = [("session", 0.0, False, None), ("weekly", 49.9, False, None),
                ("Fable", 50.0, False, None), ("Opus", 85.0, False, None),
                ("Mythos", 12.0, True, None)]
        remaining = ["value", "value", "warn", "bad", "bad"]
        for source in ("exact", "estimate"):
            with self.subTest(source=source):
                main, _sub = claude_pet.roam_summary_runs([(source, rows)], tr)
                values = [run for run in main if "%" in run[0]]
                labels = [run for run in main if "%" not in run[0] and run[0] != claude_pet.SUMMARY_SEP]
                self.assertEqual(len(values), 5)
                self.assertEqual([kind for _t, kind in values], [source] * 5)
                self.assertEqual([kind for _t, kind in labels], remaining)
                self.assertEqual([text.startswith(claude_pet.SUMMARY_SPIKE) for text, _k in labels],
                                 [False, False, False, False, True])
                self.assertTrue(all(not text.startswith(claude_pet.SUMMARY_SPIKE) for text, _k in values))
                self.assertEqual(sum(1 for _t, kind in main if kind == "status"), 4, "separators only")
        main, _sub = claude_pet.roam_summary_runs([("cost", (1.0, 45.0, 50.0))], tr)
        amounts = [run for run in main if run[0].startswith("$") or run[0].startswith(" / $")]
        words = [run for run in main if run[0] in ("Today ", "This month ")]
        self.assertEqual([kind for _t, kind in amounts], ["cost", "cost", "cost"])
        self.assertEqual(words, [("Today ", "value"), ("This month ", "bad")])

    def test_segments_append_on_the_same_line_and_empty_segments_vanish(self):
        """The extension point: a second provider is one more segment. Rivals: segments
        on separate lines; a leading separator before the first segment; an empty
        exact segment leaving a stray separator."""
        gpt = [("GPT", 10.0, False, "3h")]
        a_main, a_sub = claude_pet.roam_summary_runs([("exact", self.exact_rows)], tr)
        b_main, b_sub = claude_pet.roam_summary_runs([("estimate", gpt)], tr)
        main, sub = claude_pet.roam_summary_runs(
            [("exact", self.exact_rows), ("estimate", gpt)], tr)
        self.assertEqual(main, a_main + [(" · ", "status")] + b_main)

        # 둘째 줄은 **문자 그대로의 연결이 아니다.** 리셋 안내어는 줄 전체에 한 번만
        # 나온다 — 제공자가 둘이면 "리셋 … · 리셋 …" 이 되어 버리기 때문이다. 이
        # 계약은 Codex 행이 붙으면서 처음 눈에 보였고, CLAUDE.md 가 이 줄을 "리셋
        # 단어를 한 번 쓰고 그 다음 <라벨> <카운트다운>" 으로 규정한 것과 맞춘다.
        #
        # 그래도 이 테스트가 원래 막던 세 가지 오답은 그대로 막는다: 구간이 줄을
        # 나눠 찍히는 것, 맨 앞의 구분자, 빈 구간이 남기는 구분자.
        self.assertEqual(sub[:len(a_sub)], a_sub, "첫 구간은 혼자일 때와 같아야 한다")
        self.assertEqual(sub[len(a_sub)], (" · ", "sub"), "구간 사이 구분자가 없다")
        tail = sub[len(a_sub) + 1:]
        self.assertTrue(tail, "둘째 구간의 리셋 조각이 통째로 사라졌다")
        self.assertNotEqual(tail, b_sub,
                            "리셋 안내어가 구간마다 반복되고 있다")
        joined_tail = "".join(t for t, _ in tail)
        for text, _ in b_sub:
            bare = text.replace(tr("reset_prefix"), "").strip()
            if bare:
                self.assertIn(bare, joined_tail,
                              "안내어만 빼야 하는데 내용까지 사라졌다: %r" % bare)
        self.assertNotIn(tr("reset_prefix"), joined_tail,
                         "둘째 구간에 리셋 안내어가 또 붙었다")
        self.assertEqual(claude_pet.roam_summary_runs([("exact", []), ("status", "scanning")], tr),
                         ([("scanning…", "status")], []))
        self.assertEqual(claude_pet.roam_summary_runs([], tr), ([], []))

    def test_every_run_kind_has_a_colour_and_the_sources_differ(self):
        """Rivals: a kind the renderer cannot colour; exact/estimate/cost sharing a
        colour (the user's decision was three distinct colours); a non-white label
        default."""
        rows = [("session", 1.0, True, "x"), ("weekly", 60.0, False, "y"), ("Fable", 99.0, False, "y")]
        kinds = set()
        for segments in ([("exact", rows)], [("estimate", rows)], [("cost", (1.0, 2.0))],
                         [("status", "scanning")]):
            main, sub = claude_pet.roam_summary_runs(segments, tr)
            kinds |= {kind for _text, kind in main + sub}
        self.assertLessEqual(kinds, set(claude_pet.SUMMARY_COLORS))
        colours = claude_pet.SUMMARY_COLORS
        self.assertEqual(len({colours["exact"], colours["estimate"], colours["cost"]}), 3)
        self.assertEqual(colours["value"], claude_pet.TXT_MAIN)
        self.assertEqual(colours["warn"], claude_pet.COL_WARN)
        self.assertEqual(colours["bad"], claude_pet.COL_BAD)
        self.assertEqual(colours["sub"], claude_pet.TXT_SUB)
        for name in ("exact", "estimate", "cost"):
            self.assertRegex(colours[name], r"^#[0-9A-Fa-f]{6}$")


class FitRunsTests(unittest.TestCase):
    runs = [("AB", "exact"), (" 12%", "value"), (" · ", "status"), ("CD", "exact"), (" 34%", "value")]

    def fit(self, width):
        return claude_pet.roam_fit_runs(self.runs, width, len)

    def test_trims_whole_runs_from_the_end_then_ellipsises_the_last_survivor(self):
        """Rivals: trimming from the front; ellipsising the joined string (kinds lost);
        never ellipsising (drop or keep whole runs only)."""
        self.assertEqual(self.fit(15), self.runs)
        self.assertIsNot(self.fit(15), self.runs)
        self.assertEqual(self.fit(12), [("AB", "exact"), (" 12%", "value"), (" · ", "status"),
                                        ("CD", "exact"), ("…", "value")])
        self.assertEqual(self.fit(1), [("…", "exact")])
        self.assertEqual(self.fit(0), [])

    def test_never_leaves_a_trailing_separator(self):
        """Rival: dropping the last run and keeping the separator before it — at width
        9 that rival returns [AB, 12%, ' · ']."""
        self.assertEqual(self.fit(9), [("AB", "exact"), (" 12%", "value")])
        self.assertEqual(self.fit(6), [("AB", "exact"), (" 12%", "value")])
        for width in range(0, 16):
            with self.subTest(width=width):
                kept = self.fit(width)
                self.assertLessEqual(sum(len(text) for text, _kind in kept), width)
                if kept:
                    self.assertNotEqual(kept[-1][0], claude_pet.SUMMARY_SEP)
                self.assertTrue(all(kind in claude_pet.SUMMARY_COLORS for _t, kind in kept))


class PillGeometryTests(unittest.TestCase):
    """full and summary are one pill; the window is always the union crop."""

    def test_full_and_summary_return_the_same_text_sized_rect(self):
        """Rivals: the old full rect (PILL_W × pill_h at the panel corner); height =
        text_h unclamped; height = pill_h always; width ignoring text."""
        rect = claude_pet.roam_pill_rect
        for mode in ("full", "summary"):
            with self.subTest(mode=mode):
                self.assertEqual(rect(mode, False, False, 300, 80, 60, 46, text_w=130, text_h=46),
                                 (4, 66, 156, 46))
                self.assertEqual(rect(mode, True, True, 300, 80, 60, 46, text_w=130, text_h=30),
                                 (140, 20, 156, 30))
                self.assertEqual(rect(mode, False, True, 300, 80, 60, 46, text_w=130, text_h=60),
                                 (4, 4, 156, 46), "height must not exceed the pill strip")
                self.assertEqual(rect(mode, False, False, 300, 80, 60, 46, text_w=0)[2],
                                 claude_pet.SUMMARY_MIN_W)
                # The old line here asserted this equals PILL_W. It now asks only that a
                # very long line is capped by *something* no wider than the screen it was
                # given — the cap's value is gated against the screen in
                # PillWidthFollowsContentTests, not pinned to a constant here.
                self.assertLessEqual(rect(mode, False, False, 300, 80, 60, 46, text_w=900)[2],
                                     300)
        self.assertIsNone(rect("folded", False, False, 300, 80, 60, 46, text_w=130))
        self.assertEqual(rect("full", True, False, 300, 80, 60, 46, text_w=130, text_h=46),
                         rect("summary", True, False, 300, 80, 60, 46, text_w=130, text_h=46))

    def test_full_crop_is_the_union_not_the_whole_window_and_anchors_are_mode_free(self):
        """Rivals: full crop = (0, 0, W, H) (the old contract); text_h ignored by the
        crop; the sprite's global position moving between modes."""
        frame = claude_pet.roam_frame
        center = (-836.0, 752.0)
        args = (False, False, 300, 220, 80, 60, 152, 0.5)
        one = frame(center, "full", *args, text_w=130, text_h=30)
        self.assertEqual(tuple(one["crop"]), (2, 0, 160, 98))
        self.assertEqual(tuple(one["origin"]), (-984.0, 764.0))
        self.assertEqual(tuple(one["pill"]), (2, 66, 156, 30))
        two = frame(center, "full", *args, text_w=130, text_h=46)
        self.assertEqual(tuple(two["crop"]), (2, 0, 160, 114))
        self.assertEqual(tuple(two["origin"]), (-984.0, 748.0))
        for mode in ("full", "summary", "folded"):
            with self.subTest(mode=mode):
                f = frame(center, mode, *args, text_w=130, text_h=30)
                if mode != "folded":
                    self.assertEqual(f, one)
                sx, sy, sw, sh = f["sprite"]
                self.assertEqual((sw, sh), (80, 60))
                self.assertEqual((f["origin"][0] + sx, f["origin"][1] + f["size"][1] - sy),
                                 (-980.0, 860.0))
                bx, by, _bw, _bh = f["button"]
                self.assertEqual((f["origin"][0] + bx, f["origin"][1] + f["size"][1] - by),
                                 (-898.0, 847.0))
                cx, cy, cw, ch = f["crop"]
                self.assertTrue(cx >= 0 and cy >= 0 and cx + cw <= 300 and cy + ch <= 220)
        self.assertEqual(tuple(frame(center, "folded", *args)["crop"]), (4, 0, 112, 64))

    def test_pill_strip_height_is_the_two_line_height(self):
        """Rivals: the old PILL_PAD*2 + ROW_H*n formula; SUMMARY_H; a constant that
        cannot hold the two-line pill.

        ``assertEqual(claude_pet.PILL_W, 300)`` was removed from this test on 2026-09-20.
        It pinned the pill's width cap to a magic number, and that number turned out to
        be the whole problem: the pill is already variable-width
        (``min(PILL_W, max(SUMMARY_MIN_W, text_w + 2 * PILL_PAD))``), so the only thing
        making content get cut was this ceiling — which nobody had ever justified. A test
        asserting it equals 300 makes the arbitrary number load-bearing and blocks the
        fix, while proving nothing about behaviour. What the cap must actually do is
        gated by ``PillWidthFollowsContentTests`` below, in terms of the screen.
        """
        self.assertEqual(claude_pet.pill_h(), claude_pet.SUMMARY_H2)
        self.assertEqual((claude_pet.SUMMARY_H, claude_pet.SUMMARY_H2), (30, 46))
        for removed in ("bar_color", "ROW_H", "STATUS_H", "CUR_PILL", "PILL_R", "TRACK"):
            self.assertFalse(hasattr(claude_pet, removed), f"{removed} should be gone with the gauge pill")


class PillWidthFollowsContentTests(unittest.TestCase):
    """The pill is variable-width. What must be true of how it varies.

    **Why this class exists, stated plainly because the omission is the lesson.** For two
    rounds the whole team — Reviewer, Coordinator, and me — measured content against a
    274pt budget (``PILL_W 300 - 2*PILL_PAD``) and designed folding underneath it. Nobody
    asked where 300 came from. The user did:

        "아니 뭐가 자꾸 잘린다는거야! 안짤리게 잘하면 되는거 아니냐고!! 폭이 가변이면
         안짤릴거 아니야!"

    And they were right. ``roam_pill_rect`` already reads
    ``min(PILL_W, max(SUMMARY_MIN_W, text_w + 2 * PILL_PAD))`` — the pill *already* grows
    with its text. The only thing cutting content was the ceiling, an inherited constant
    with a comment calling it "요약 필 최대 너비" and no derivation behind it. We treated it
    as a law of physics and gated everything against it.

    So these tests deliberately assert **no number**. They assert relationships: the cap
    tracks the screen it is given, the pill grows when content grows, and it hugs short
    content instead of floating a wide bar around a few characters ("유려하게", the user's
    word). A test that pins a width is how the last one of these got missed.
    """

    # The window width production actually passes. **Not a screen.** `geom()` computes
    # `W = max(pw + BTN_R*2 + 16, PILL_W + 8)` and hands that to `roam_pill_rect`; it is
    # 308 whatever the pet's size, so the pill's ceiling is 300 and its text area 256.
    #
    # This constant replaces a helper whose parameter was named `screen_w`. That name was
    # the whole defect: it encoded my assumption into the fixture, and after that no test
    # in this class could see the assumption. Two tests here asserted that the ceiling
    # tracks "the screen it was given" — true of the function, and about an input
    # production never supplies. They were removed rather than repaired, because there
    # was nothing to repair: the relationship held and the premise was fiction.
    #
    # The invariant that actually matters — that the fold budget equals the width the
    # pill gives — is in tests/test_summary_layout.py's FoldBudgetMatchesTheActualPillTests,
    # which derives BOTH ends by calling production's own `geom()` and `_pill_text_budget()`
    # rather than restating either formula here.
    # A window width chosen **as a test input**, wide enough that these relationship
    # tests are not accidentally measuring the ceiling. It is deliberately NOT production's
    # value: an earlier revision of this class computed
    #     PRODUCTION_W = max(80 + BTN_R*2 + 16, PILL_W + 8)
    # which restated `geom()`'s formula here — the very defect this class's docstring
    # diagnoses, reintroduced one line below the diagnosis. A fixture that recites a
    # production formula cannot see that formula change, and under the adaptive width it
    # froze the pre-measurement snapshot (308) as though it were the answer.
    #
    # Nothing in this class asks whether the window is big enough; that is a property of
    # `geom()`, not of `roam_pill_rect`, and it is asserted by
    # tests/test_summary_layout.py's FoldBudgetMatchesTheActualPillTests, which calls
    # `geom()` and `_pill_text_budget()` instead of repeating either.
    TEST_WINDOW_W = 2000

    RECT_ARGS = dict(PW=80, PH=60, pill_h=46)

    def width(self, text_w, window_w=None, mode="full"):
        """Pill width for `text_w` at a given logical window width."""
        return claude_pet.roam_pill_rect(
            mode, False, False, self.TEST_WINDOW_W if window_w is None else window_w,
            self.RECT_ARGS["PW"], self.RECT_ARGS["PH"],
            self.RECT_ARGS["pill_h"], text_w=text_w, text_h=46)[2]

    def test_the_ceiling_is_derived_from_the_window_it_is_given(self):
        """What is actually true of `roam_pill_rect`: the ceiling comes from its `W`
        argument, not from a constant inside it.

        This is deliberately a weaker claim than the one it replaces. Whether that `W`
        is big enough is **not a property of this function** — it is decided by `geom()`,
        and asserting it here is what let the real defect hide. Rival: a `min(PILL_W, …)`
        ceiling that ignores `W` entirely.
        """
        narrow = self.width(text_w=100_000, window_w=400)
        wide = self.width(text_w=100_000, window_w=1200)
        self.assertGreater(wide, narrow,
                           "the ceiling ignores W — it is an internal constant again")
        for window_w in (400, 800, 1200):
            with self.subTest(window_w=window_w):
                self.assertLessEqual(self.width(text_w=100_000, window_w=window_w), window_w)

    def test_the_pill_widens_as_its_content_grows(self):
        """Monotonic in the content width, and strictly so across the ordinary range.

        Rivals: a fixed-width pill; a pill that snaps between two or three sizes, which
        reads as jumpy rather than 유려한; growth that stops early and starts cutting.
        """
        screen_w = 1920
        widths = [self.width(text_w=t) for t in range(0, 900, 25)]
        for earlier, later in zip(widths, widths[1:]):
            self.assertLessEqual(earlier, later, "the pill narrowed as its content grew")
        self.assertGreater(widths[-1], widths[0], "the pill never grew at all")

    def test_a_short_line_gets_a_narrow_pill_not_a_wide_one(self):
        """Short content must hug, not float in a wide bar — the user's "유려하게" cuts
        both ways, and a half-empty pill around three characters is the least fluent
        outcome of all.

        Rivals: always drawing the maximum width; padding short content up to some
        'tidy' width; a minimum so large that every short status line looks identical.
        """
        screen_w = 1920
        snug = self.width(text_w=40)
        self.assertLess(
            snug, self.width(text_w=400),
            "a short line gets the same pill as a long one")
        self.assertLessEqual(
            snug, max(claude_pet.SUMMARY_MIN_W, 40 + 2 * claude_pet.PILL_PAD),
            "a short line is being given more width than its content plus padding needs")

    def test_the_pill_never_shrinks_below_the_minimum(self):
        """Rival: a pill that collapses to nothing on an empty line, which flickers on
        every refresh that briefly has no text."""
        for text_w in (0, 1, 5, 20):
            with self.subTest(text_w=text_w):
                self.assertGreaterEqual(self.width(text_w=text_w),
                                        claude_pet.SUMMARY_MIN_W)

    # RETIRED 2026-09-20: test_the_widest_realistic_line_is_not_capped_on_a_supported_screen
    #
    # It asked the right question — does the widest real line fit the pill it is drawn in —
    # and asked it of the wrong object. `roam_pill_rect` cannot answer it: the answer
    # depends on the `W` it is handed, so the test had to supply one, and supplying one
    # meant restating `geom()`. That restatement is what this class's docstring identifies
    # as the root of the W1 defect, and under the adaptive width it additionally pinned the
    # pre-measurement snapshot.
    #
    # The question now lives where both ends can be taken from production:
    # tests/test_summary_layout.py :: FoldBudgetMatchesTheActualPillTests, which calls
    # `geom()` and `_pill_text_budget()` and compares every line `summary_lines` produces
    # against the pill `roam_pill_rect` returns for that same content.


class RoamDisplayToggleTests(unittest.TestCase):
    """The arrival latch and the chevron. The app calls ``note()`` on every tick, so a
    visit is a *sequence* of ``note("look", "approach")`` calls, not one; every gate
    here re-notes after the toggle for that reason."""

    def test_mode_is_summary_while_latched_whatever_the_preference(self):
        """Rivals: 'full' when show_panel is True; an 'expanded' sub-state; a latch
        that starts dismissed."""
        d = claude_pet.RoamDisplay()
        self.assertFalse(d.dismissed)
        d.note("look", "approach", True)
        for phase in ("look", "rest"):
            for preference in (False, True):
                with self.subTest(phase=phase, preference=preference):
                    self.assertEqual(d.mode(phase, preference), "summary")
        self.assertFalse(hasattr(d, "expanded"))
        self.assertFalse(d.dismissed)

    def test_toggle_during_the_latch_dismisses_for_the_visit_and_keeps_the_preference(self):
        """The Reviewer's B1 gate. With a folded preference the pill is on screen only
        because of the latch, the chevron is drawn in the fold direction, and clicking
        it must fold *this* pill and not turn the preference into 'open'.

        Rivals: the round-1 toggle (clears the latch and returns ``not show_panel`` —
        a folded user ends the visit with the pill permanently open, and the next tick's
        ``note()`` re-latches so the click has no lasting visible effect); dismiss *and*
        flip; the next tick's re-latch clearing the dismissal; a second toggle not
        bringing the pill back; the dismissal surviving the visit's natural end (the
        next visit would arrive folded)."""
        for preference in (False, True):
            with self.subTest(preference=preference):
                d = claude_pet.RoamDisplay()
                d.note("look", "approach", True)
                self.assertEqual(d.mode("look", preference), "summary")
                self.assertEqual(d.toggle(preference), preference,
                                 "a toggle during the latch must not flip the stored preference")
                self.assertTrue(d.summary, "the latch itself is not cleared by a dismissal")
                self.assertTrue(d.dismissed)
                self.assertEqual(d.mode("look", preference), "folded")
                d.note("look", "approach", True)             # next tick, still visiting
                self.assertEqual(d.mode("look", preference), "folded",
                                 "the per-tick re-latch must not undo the dismissal")
                d.note("rest", None, True, settled=False)   # hover stop, still visiting
                self.assertEqual(d.mode("rest", preference), "folded")
                self.assertEqual(d.toggle(preference), preference)
                self.assertEqual(d.mode("rest", preference), "summary",
                                 "a second toggle shows the visiting pill again")
                self.assertEqual(d.toggle(preference), preference)
                self.assertEqual(d.mode("rest", preference), "folded")
                d.note("rest", None, True, settled=True)    # natural completion
                self.assertFalse(d.summary)
                self.assertFalse(d.dismissed)
                self.assertEqual(d.mode("rest", preference), "full" if preference else "folded",
                                 "after the visit the preference is what it was before it")
                d.note("look", "approach", True)             # the next visit
                self.assertEqual(d.mode("look", preference), "summary",
                                 "a dismissal is per visit; the next visit arrives open")

    def test_every_latch_end_clears_the_dismissal(self):
        """Rivals: ``reset()`` clearing only the latch; movement, interruption or
        disabling leaving ``dismissed`` set so the *next* visit arrives folded."""
        ends = {"reset": lambda d: d.reset(),
                "walk": lambda d: d.note("out", "wander", False),
                "jump": lambda d: d.note("jump", "approach", False),
                "follow": lambda d: d.note("follow", "follow", False),
                "interrupted": lambda d: d.note("look", "approach", True, interrupted=True),
                "disabled": lambda d: d.note("look", "approach", True, enabled=False),
                "completion": lambda d: d.note("rest", None, True, settled=True)}
        for name, end in ends.items():
            for preference in (False, True):
                with self.subTest(end=name, preference=preference):
                    d = claude_pet.RoamDisplay()
                    d.note("look", "approach", True)
                    self.assertEqual(d.toggle(preference), preference)
                    self.assertTrue(d.dismissed)
                    end(d)
                    self.assertEqual((d.summary, d.dismissed), (False, False))
                    self.assertEqual(d.mode("rest", preference), "full" if preference else "folded")
                    self.assertEqual(d.toggle(preference), not preference,
                                     "outside a visit the toggle is the plain preference flip")

    def test_toggle_without_a_latch_is_the_plain_flip(self):
        d = claude_pet.RoamDisplay()
        self.assertTrue(d.toggle(False))
        self.assertFalse(d.toggle(True))
        self.assertFalse(d.dismissed, "a plain flip is not a dismissal")
        self.assertEqual(d.mode("rest", True), "full")
        self.assertEqual(d.mode("rest", False), "folded")


class DeadPillCodeTests(unittest.TestCase):
    """What the unification removed must stay removed, in every locale at once."""

    REMOVED_TR_KEYS = ("spike_prefix", "left", "exact_mode", "log_estimate", "budget",
                       "need_budget", "reset_at", "am", "pm")
    LIVE_TR_KEYS = ("reset_prefix", "today", "this_month", "credit", "session", "weekly",
                    "need_admin_key", "loading", "scanning", "onb_install", "onb_login")

    def test_removed_helpers_and_constants_are_gone(self):
        """Rivals: fmt_reset/gauge_rows kept 'for later' (they and WEEKDAYS were the
        only users of the removed keys); SUMMARY_FONT_FAMILY kept for a port that is
        not in this tree."""
        for name in ("fmt_reset", "gauge_rows", "WEEKDAYS", "SUMMARY_FONT_FAMILY"):
            self.assertFalse(hasattr(claude_pet, name), f"{name} still exists")
        self.assertTrue(callable(claude_pet.fmt_countdown), "the reset-time formatter the pill uses")

    def test_removed_translation_keys_are_gone_from_all_four_locales_which_still_agree(self):
        """Rivals: keys dropped from one locale only (the sets would differ); a removed
        key still referenced by ``t("…")`` somewhere in the source; the live keys
        removed along with them."""
        table = claude_pet.TR
        self.assertEqual(sorted(table), ["en", "es", "ja", "ko"])
        key_sets = {lang: set(keys) for lang, keys in table.items()}
        for lang, keys in key_sets.items():
            with self.subTest(lang=lang):
                self.assertEqual(keys, key_sets["en"], f"{lang} keys differ from en")
                self.assertEqual(keys & set(self.REMOVED_TR_KEYS), set())
                self.assertLessEqual(set(self.LIVE_TR_KEYS), keys)
        source = Path(claude_pet.__file__).read_text(encoding="utf-8")
        for key in self.REMOVED_TR_KEYS:
            with self.subTest(key=key):
                self.assertNotRegex(source, rf'\bt\(\s*"{re.escape(key)}"')

    def test_pet_view_lost_its_pill_top_and_pill_left_helpers(self):
        """Read as AST; run_gui is never called. Rival: the two callerless methods
        kept beside pillRect."""
        tree = ast.parse(Path(claude_pet.__file__).read_text(encoding="utf-8"))
        run_gui = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_gui")
        pet_view = next(n for n in run_gui.body if isinstance(n, ast.ClassDef) and n.name == "PetView")
        methods = {n.name for n in pet_view.body if isinstance(n, ast.FunctionDef)}
        self.assertIn("pillRect", methods)
        self.assertEqual(methods & {"pillTop", "pillLeft"}, set())


class BundledFontTests(TreeConsistencyMixin, unittest.TestCase):
    """fonts/ is shipped by both build paths and registered by the plist."""

    def setUp(self):
        self.assert_same_tree()
        self.font = ROOT / "fonts" / claude_pet.SUMMARY_FONT_FILE
        self.licence = ROOT / "fonts" / "LICENSE-Pretendard.txt"

    def test_font_file_and_its_licence_are_in_the_tree(self):
        """Round 3: the TrueType build. Rivals: the round-2 CFF ``.otf`` (constant and
        file); the CFF bytes (``OTTO``) under the ``.ttf`` name; an empty or tiny
        placeholder under the right name; a licence file that is not the OFL; a
        leftover ``.otf`` beside it (two fonts shipped, one of them dead)."""
        self.assertEqual(claude_pet.SUMMARY_FONT_FILE, "Pretendard-SemiBold.ttf")
        self.assertTrue(self.font.is_file() and not self.font.is_symlink(), f"{self.font} is missing")
        head = self.font.read_bytes()
        self.assertEqual(head[:4], b"\x00\x01\x00\x00", "not a TrueType (sfnt 1.0) font")
        self.assertNotEqual(head[:4], b"OTTO")
        self.assertGreater(len(head), 100_000)
        self.assertFalse((ROOT / "fonts" / "Pretendard-SemiBold.otf").exists(),
                         "the CFF build must not be shipped beside the TrueType one")
        self.assertEqual(sorted(p.name for p in (ROOT / "fonts").iterdir() if not p.name.startswith(".")),
                         ["LICENSE-Pretendard.txt", "Pretendard-SemiBold.ttf"])
        self.assertIn("SIL Open Font License", self.licence.read_text(encoding="utf-8"))

    def test_bundled_font_path_finds_the_file_next_to_the_source_and_none_elsewhere(self):
        """Rivals: None from source; a bundle-only lookup; a path that ignores
        SUMMARY_FONT_FILE."""
        found = claude_pet.bundled_font_path()
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).resolve(), self.font.resolve())
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(claude_pet, "__file__", os.path.join(tmp, "claude_pet.py")):
                self.assertIsNone(claude_pet.bundled_font_path(),
                                  "a tree without fonts/ must fall back to None, not invent a path")

    def test_setup_py_ships_fonts_as_a_resource_and_registers_them(self):
        """Read as AST; never executed. Rivals: fonts missing from resources; the plist
        key absent or pointing elsewhere."""
        tree = ast.parse((ROOT / "setup.py").read_text(encoding="utf-8"))
        setup_call = next(node for node in ast.walk(tree)
                          if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup")
        options = next(kw.value for kw in setup_call.keywords if kw.arg == "options")

        def item(node, key):
            self.assertIsInstance(node, ast.Dict)
            for k, value in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == key:
                    return value
            self.fail(f"setup.py: no {key!r} entry")

        py2app = item(options, "py2app")
        resources = ast.literal_eval(item(py2app, "resources"))
        self.assertIn("fonts", resources)
        self.assertIn(".claude_pet", resources)
        self.assertEqual(ast.literal_eval(item(item(py2app, "plist"), "ATSApplicationFontsPath")),
                         "fonts")

    def test_build_app_copies_fonts_in_both_arms_and_writes_the_plist_key(self):
        """Read as text; never sourced. Rivals: copy_fonts defined but unused; called by
        build only (an update would leave the installed bundle without the font);
        the plist key missing from the hand-written plist; the round-2 script still
        requiring the ``.otf`` (a build would then refuse the ``.ttf`` tree)."""
        source = (ROOT / "build_app.sh").read_text(encoding="utf-8")
        copy_fonts = zsh_function(source, "copy_fonts")
        self.assertIn('"$stage/Pretendard-SemiBold.ttf"', copy_fonts)
        self.assertNotIn(".otf", copy_fonts, "the script must not still look for the CFF build")
        self.assertIn("LICENSE-Pretendard.txt", copy_fonts)
        self.assertRegex(copy_fonts, r"return 1")
        build_body = zsh_function(source, "build_body")
        update = zsh_function(source, "update_installed")
        self.assertEqual(len(re.findall(r'(?m)^\s*if ! copy_fonts "\$APP"; then\s*$', build_body)), 1)
        self.assertEqual(len(re.findall(r'(?m)^\s*\|\| ! copy_fonts "\$stage" \\\s*$', update)), 1)
        self.assertLess(update.index('copy_fonts "$stage"'), update.index("stop_pet"),
                        "fonts must be staged before the pet is stopped")
        plist = zsh_function(source, "write_plist")
        self.assertIn("<key>ATSApplicationFontsPath</key><string>fonts</string>", plist)


# ───────────────────────── v0.26: the Codex row must actually fit ─────────────────────────
#
# Added by the Verifier after the Reviewer found that the v0.26 headline feature does not
# reach the screen.  The tests above gate what the pill *contains*; none of them gates how
# *wide* it comes out, and the pill is a hard-capped strip.  A segment that is assembled
# correctly, coloured correctly and then sliced off by `roam_fit_runs` is, to the user,
# a feature that was not shipped.
#
# Why the existing coverage missed it, stated plainly because it is the lesson rather than
# the bug: tests/test_codex_usage.py paired the Codex segment with `("status", "scanning")`,
# which is the shortest Claude segment there is and — in Korean — the only realistic pairing
# that fits.  That is AGENTS.md §3's non-discriminating fixture exactly: green, evidence-
# shaped, and blind to every case that ships.  test_v026_release_contract.py reading "같은
# 줄" as "the same `exact` segment kind" has the same shape: structurally true, and false to
# the user looking at the pill.  So these tests assert on *rendered width*, not structure.
#
# The budget was originally derived here as `PILL_W - 2*PILL_PAD`, on the reasoning that
# deriving from a constant beats writing 274 down.  That was half right: it did track the
# constant, but the constant was the bug.  Deriving from the wrong thing fails exactly as
# quietly as hardcoding — the derivation kept pointing at PILL_W after PILL_W stopped being
# the pill's cap and became settings-panel geometry.  Nothing in this file needs a width
# budget any more; tests/test_summary_layout.py derives one from the screen.

# Advance widths of Pretendard-SemiBold at 11 pt — the pill's only font (SUMMARY_FONT_FILE /
# SUMMARY_FONT_NAME, the size draw_summary_pill passes to summary_font).  MEASURED, not
# modelled: produced 2026-09-20 on macOS 26.5 / Darwin 25.5 from this checkout's
# fonts/Pretendard-SemiBold.ttf, registered with CTFontManagerRegisterFontsForURL at process
# scope, by taking NSAttributedString(string:attributes:).size().width of each single
# character — the same call draw_summary_pill measures with.
#
# The table exists so this gate runs on Windows CI and anywhere else without AppKit; the
# real-font companion below re-derives it on macOS and fails if it has drifted, so it cannot
# quietly go stale.  Summing per-character advances ignores kerning, which costs at most
# 1.05 % against the real measurement across the fixture strings here (worst case
# "Credit $100.66": 77.01 summed vs 76.21 real) — three orders of magnitude smaller than the
# 11 %–81 % overflows it is used to detect, and it errs *high*, so it can only make the pill
# look tighter than it is, never roomier.
_ADVANCES = {
    ' ': 2.6104, '!': 3.1904, '"': 4.1465, '#': 6.7783, '$': 6.8428, '%': 10.2051, '&': 6.9824,
    "'": 2.1914, '(': 4.1143, ')': 4.1143, '*': 5.6826, '+': 7.0898, ',': 3.0508, '-': 4.8770,
    '.': 2.9971, '/': 3.9424, '0': 7.0254, '1': 5.0488, '2': 6.6279, '3': 6.9502, '4': 7.1006,
    '5': 6.7891, '6': 6.9609, '7': 6.2412, '8': 6.9395, '9': 6.9609, ':': 2.9971, ';': 2.9971,
    '<': 7.0898, '=': 7.0898, '>': 7.0898, '?': 5.7041, '@': 9.6357, 'A': 7.6270, 'B': 6.9395,
    'C': 7.8525, 'D': 7.6484, 'E': 6.4023, 'F': 6.1660, 'G': 7.9707, 'H': 7.8633, 'I': 2.8467,
    'J': 5.8975, 'K': 7.1436, 'L': 5.9512, 'M': 9.5928, 'N': 7.8311, 'O': 8.1855, 'P': 6.7891,
    'Q': 8.1963, 'R': 6.8643, 'S': 6.8428, 'T': 6.9502, 'U': 7.7559, 'V': 7.6270, 'W': 10.6777,
    'X': 7.2725, 'Y': 7.4229, 'Z': 6.8750, '[': 4.1143, '\\': 3.9424, ']': 4.1143, '^': 5.0488,
    '_': 4.8984, '`': 5.2207, 'a': 6.0479, 'b': 6.6494, 'c': 6.0801, 'd': 6.6494, 'e': 6.2412,
    'f': 3.9316, 'g': 6.5850, 'h': 6.4561, 'i': 2.6855, 'j': 2.6855, 'k': 5.9834, 'l': 2.6855,
    'm': 9.5068, 'n': 6.4238, 'o': 6.4023, 'p': 6.5850, 'q': 6.5850, 'r': 4.1465, 's': 5.7686,
    't': 3.9639, 'u': 6.4023, 'v': 6.0693, 'w': 8.8623, 'x': 5.9189, 'y': 6.0693, 'z': 5.8975,
    '{': 4.1143, '|': 3.7275, '}': 4.1143, '~': 7.0898, '·': 2.9971, '…': 8.9912, '≈': 7.0898,
    '▲': 10.9570, '⚠': 10.6885, '≒': 6.9556,
}
# Every Hangul syllable in this font has the same advance — checked over a 400-character
# sample drawn from the whole U+AC00..U+D7A3 block, which returned exactly one value.  It is
# a rule rather than 11,172 table rows so that a Korean relabel cannot fall off the table.
_HANGUL_ADVANCE = 9.5068
_CJK_ADVANCE = 9.5150           # 使用量, for the ja locale, measured the same way


def pretendard_width(text):
    """Width of ``text`` in the pill's font, from the measured advances above.

    Fail-closed on anything unmeasured: a character with no advance raises rather than
    contributing zero.  A silent zero is how a width gate turns into a test of nothing —
    a relabel into an unmeasured script would make every line look narrower and the gate
    would go green on a pill that overflows worse than before.
    """
    total = 0.0
    for char in text:
        advance = _ADVANCES.get(char)
        if advance is None:
            if "가" <= char <= "힣":
                advance = _HANGUL_ADVANCE
            elif "一" <= char <= "鿿" or "぀" <= char <= "ヿ":
                advance = _CJK_ADVANCE
            else:
                raise AssertionError(
                    f"no measured advance for {char!r} (U+{ord(char):04X}); re-derive the "
                    "table from fonts/Pretendard-SemiBold.ttf rather than guessing a width")
        total += advance
    return total


# The realistic-pairing fixtures (CODEX_ROWS / CLAUDE_ROWS / ESTIMATE_STATS) and the
# CodexFitMixin that drove them were removed together with the two retired tests below —
# they had no other caller, and a fixture nothing asserts on is the same "looks like
# coverage" hazard the retired tests were written to expose.  Their successors live in
# tests/test_summary_layout.py, parameterised over provider count and row count rather
# than pinned to one shape.

# ─────────────────────── RETIRED 2026-09-20: the tail-protection gate ───────────────────────
#
# Two tests lived here and no longer do:
#
#     CodexRowFitsThePillTests.test_codex_row_survives_beside_every_realistic_claude_segment
#     CodexRowFitsThePillRealFontTests....._real_font
#
# **Why they were retired.** They called ``roam_fit_runs(main, budget, measure)`` directly
# and asserted the Codex runs survived as the *tail* of the result.  Under the provider-line
# layout that shipped the same day, ``roam_fit_runs`` is no longer on the pill's path at all:
# ``summary_lines`` folds, and nothing trims.  Making these two pass would have meant
# teaching ``roam_fit_runs`` to protect its tail — and on a single line that protection has
# to take the space from somewhere, so **Claude's runs would be cut instead**.  Same data
# loss, different victim.  On one line it is unavoidable: the English Claude line with the
# credit row already overflows by 7.2pt with no Codex segment present at all.
#
# **What took over.** tests/test_summary_layout.py — ``NothingIsEverTruncatedTests`` and
# ``EveryLineFitsTests``, which assert on folding instead of on trimming.
#
# **This was not taken on trust.** Retiring a gate because "something else covers it" is the
# standard way protection is quietly lost, so the transfer was measured before the delete.
# Three mutations of ``summary_lines`` in a scratch copy, layout gate run against each:
#
#     M1  folding disabled, everything on one line   RED  every_produced_line_fits,
#                                                          line_that_only_fits_without_the_logo
#     M2  trims instead of folding (the OLD bug)     RED  no_content_is_lost_in_any_provider_
#                                                          combination, ..._with_the_credit_row,
#                                                          folding_never_ellipsises,
#                                                          english_claude_line_with_credit,
#                                                          line_that_only_fits_without_the_logo
#     M3  SUMMARY_LOGO_W declared, never subtracted  RED  every_produced_line_fits
#
# M2 is the one that matters: it reinstates precisely the behaviour these retired tests were
# written to catch, and the new gate refuses it on five separate assertions.  The protection
# moved; it was not dropped.  If a future reader finds no Codex width test here, that is why,
# and tests/test_summary_layout.py is where to look.
#
# **Deliberately kept below**, because the layout gate depends on them and nothing supersedes
# them: ``pretendard_width`` and ``_ADVANCES`` (imported by test_summary_layout),
# ``test_the_measured_advance_table_still_matches_the_bundled_font`` (the only thing stopping
# that table from silently going stale against a bumped font), the fail-closed measure test,
# and the PILL_W cap test that makes any width budget binding at all.


class CodexRowFitsThePillTests(unittest.TestCase):
    """What survives of the width gate after the tail-protection tests were retired above."""

    def setUp(self):
        self.addCleanup(claude_pet.set_lang, claude_pet.L.get("lang"))

    # RETIRED 2026-09-20: test_the_pill_cannot_be_widened_to_make_room.
    #
    # It asserted `roam_pill_rect(...)[2] <= PILL_W` — "the pill cannot grow past its cap,
    # so the budget is binding".  Every word was true when written and the whole premise
    # was wrong: PILL_W was an inherited constant with no derivation, and it was the only
    # thing cutting content.  I wrote this test to establish that the 274pt budget was
    # binding, which is the opposite of the question worth asking — *why* 274?  The user
    # asked it, and the cap is now the screen.
    #
    # This is worth leaving as a marker rather than a clean delete: a test that pins an
    # arbitrary constant does not look wrong, it looks rigorous, and it actively defends
    # the bug.  It went green for two rounds while the feature it was "protecting" never
    # reached the screen.
    #
    # Replaced by PillWidthFollowsContentTests above, which asserts relationships (the cap
    # tracks the screen, the pill grows with content, short content gets a narrow pill) and
    # deliberately pins no width at all.

    def test_the_measure_refuses_a_character_it_has_not_measured(self):
        """The fake measure is only evidence while it is fail-closed. Rival: `.get(c, 0)`,
        under which an unmeasured script renders as zero width and the gate passes on a
        pill that is overflowing."""
        self.assertAlmostEqual(pretendard_width("세션"), 2 * _HANGUL_ADVANCE, places=4)
        with self.assertRaises(AssertionError):
            pretendard_width("الع")          # Arabic: never measured


class CodexRowFitsThePillRealFontTests(unittest.TestCase):
    """The same gate, against the real font through AppKit. macOS-only, skips loudly.

    Two jobs. It re-runs the width assertion with the measurement draw_summary_pill itself
    performs, so the verdict does not rest on the table; and it re-derives the table and
    fails if the bundled font has moved under it, which is what stops the CI-safe gate above
    from silently becoming fiction after a font bump.
    """

    def setUp(self):
        if sys.platform != "darwin":
            self._skip("the real-font measurement needs macOS AppKit/CoreText")
        try:
            from AppKit import NSFont, NSFontAttributeName, NSAttributedString
            import CoreText
            import Foundation
        except ImportError as exc:
            self._skip(f"pyobjc is not importable here ({exc.__class__.__name__})")
        font_path = ROOT / "fonts" / claude_pet.SUMMARY_FONT_FILE
        if not font_path.is_file():
            self._skip(f"fonts/{claude_pet.SUMMARY_FONT_FILE} is missing from this tree")
        CoreText.CTFontManagerRegisterFontsForURL(
            Foundation.NSURL.fileURLWithPath_(str(font_path)),
            CoreText.kCTFontManagerScopeProcess, None)
        font = NSFont.fontWithName_size_(claude_pet.SUMMARY_FONT_NAME, 11)
        if font is None:
            self._skip(f"{claude_pet.SUMMARY_FONT_NAME} did not register in this process")
        attrs = {NSFontAttributeName: font}
        self.measure = lambda s: (NSAttributedString.alloc()
                                  .initWithString_attributes_(s, attrs).size().width)
        self.addCleanup(claude_pet.set_lang, claude_pet.L.get("lang"))

    def _skip(self, why):
        print(f"\n[summary-pill] SKIPPED: {why}", file=sys.stderr, flush=True)
        self.skipTest(why)

    def test_the_measured_advance_table_still_matches_the_bundled_font(self):
        """Rival: the font is bumped, the table keeps yesterday's numbers, and the CI-safe
        gate goes on reporting on a font nobody ships any more."""
        drift = []
        for char, expected in sorted(_ADVANCES.items()):
            actual = self.measure(char)
            if abs(actual - expected) > 0.01:
                drift.append(f"{char!r} table {expected:.4f} vs font {actual:.4f}")
        for char, expected in (("가", _HANGUL_ADVANCE), ("힣", _HANGUL_ADVANCE),
                               ("用", _CJK_ADVANCE)):
            actual = self.measure(char)
            if abs(actual - expected) > 0.01:
                drift.append(f"{char!r} table {expected:.4f} vs font {actual:.4f}")
        self.assertEqual(drift, [], "re-derive _ADVANCES from the bundled font:\n  "
                                    + "\n  ".join(drift))

    # test_codex_row_survives_beside_every_realistic_claude_segment_real_font retired
    # 2026-09-20 with its portable twin — see the retirement note above.  The table-drift
    # test above is the reason this class still exists: tests/test_summary_layout.py measures
    # with _ADVANCES, and without this check a font bump would leave that gate reporting on
    # metrics nobody ships.


if __name__ == "__main__":
    unittest.main()
