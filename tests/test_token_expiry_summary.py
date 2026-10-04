"""Gates for the expired-token summary: stop fabricating ``≈0%`` when there is no data.

Owner: Verifier. Written against the UNFIXED tree (red-before-green, AGENTS.md §3);
no production file is touched by this module.

The bug in two halves:

1. ``roam_summary()`` builds an ``("estimate", rows)`` segment out of gauges whose
   ``pct`` is ``0.0``, because ``_roam_valid_pct()`` accepts ``0.0``. Its own docstring
   says "데이터가 없으면 0% 를 지어내지 않고 상태 키를 준다" — it does fabricate. A user
   whose OAuth token has expired reads ``세션 ≈0% · 주간 ≈0%`` and concludes they have
   used nothing, when in fact nothing could be read at all.
2. ``_has_claude_logs()`` answers True for *any* ``*.jsonl`` ever written, with no age
   filter, while ``parse_usage_entries()`` only looks 7 days back. A months-old corpus
   therefore suppresses the onboarding hint forever while every gauge reads 0.

The specified behaviour these tests pin:

* ``compute_usage()`` gains ``"entries"`` — the number of usage entries inside the
  7-day parse window, as an ``int``, ``0`` when there are none.
* ``roam_summary()`` gains ``auth_error=False`` and this precedence, replacing the body
  after the API-mode branch: oauth rows → ``("exact", rows)``; else auth_error AND no
  data → ``("status", "token_expired")``; else onboard install/login →
  ``("status", "onb_" + onboard)``; else data AND at least one valid gauge row →
  ``("estimate", rows)``; else ``("status", "scanning")``. "No data" is decided ONLY by
  ``stats.get("entries") == 0`` on a dict ``stats``.
* ``roam_summary_text()`` passes ``auth_error=bool(OAUTH_STATUS.get("auth_error"))``.
* The ``compute_onboard_state()`` call site stops using ``_has_claude_logs()``, which is
  deleted, and uses the in-window entry count instead.

**The discrimination that matters most**, and the reason two of these fixtures differ in
exactly one integer: gauges reading 0 % because the user genuinely burned nothing, and
gauges reading 0 % because there is nothing to read, are the same picture. Any
implementation that decides "no data" by looking at the percentages collapses the two.
``SummaryNoDataFixtures`` holds them side by side — same gauges, same ``auth_error``,
``entries`` 0 vs 5 — so that rival is separated by construction and not by hope.

Fixtures are synthetic throughout (CLAUDE.md "Testing policy: synthetic fixtures only"):
``LOG_DIRS`` is repointed at a ``tempfile.TemporaryDirectory()`` for the duration of each
test that needs a tree, and nothing here reads ``~/.claude`` or writes ``~/.claude_pet``.
``roam_summary()`` is pure, so the rest is called directly with hand-built dicts and no
window is ever created.

``roam_summary_text()`` is a closure inside ``run_gui()`` and cannot be called without
AppKit, so item C is pinned by an AST check on its call site, in the style of
``tests/test_autostart.py``'s menu-wiring test. The same applies to the
``compute_onboard_state()`` call site, which lives inside the refresh worker's ``work()``
closure. Both AST checks are stated as such on the test.
"""
from __future__ import annotations

# ── 2026-10-05 revision (sou-verify, docs-design/server-only-usage-20261005.md) ──
# The estimate segment no longer exists. Without server rows the pill shows a status,
# and a rejected token is ``token_expired`` whatever the logs hold (§1: "로그 유무와
# 무관하게"). The tests below that pinned "auth_error + entries 5 → estimate" and the
# no-``entries``-key backward-compat estimate were rewritten to the new contract; the
# compute_usage entry-count tests keep their substance minus the removed gauge keys.

import ast
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import claude_pet


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def usage_record(*, timestamp, message_id, request_id, output_tokens):
    """One assistant row. Only the fields the estimator reads are filled in."""
    return {
        "type": "assistant",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "requestId": request_id,
        "message": {
            "id": message_id,
            "model": "claude-opus-5",
            "role": "assistant",
            "usage": {
                "input_tokens": 0,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }


class LogTreeMixin:
    """A synthetic ``LOG_DIRS`` root. Never the real corpus."""

    def setUpLogTree(self):
        self.assertEqual(Path(claude_pet.__file__).resolve(), (ROOT / "claude_pet.py").resolve(),
                         "claude_pet was imported from a different tree than the one under test")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        original = claude_pet.LOG_DIRS
        claude_pet.LOG_DIRS = [self.temp_dir.name]
        self.addCleanup(setattr, claude_pet, "LOG_DIRS", original)

    def write_log(self, records, relative_path="session.jsonl", mtime=None):
        path = Path(self.temp_dir.name, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record) + "\n")
        if mtime is None:
            os.utime(path, None)
        else:
            os.utime(path, (mtime.timestamp(), mtime.timestamp()))
        return path


class ComputeUsageEntryCountTests(LogTreeMixin, unittest.TestCase):
    """A. ``compute_usage()["entries"]`` — deduplicated rows inside the 7-day window."""

    def setUp(self):
        self.setUpLogTree()

    def test_entries_counts_deduplicated_in_window_rows_and_nothing_else(self):
        """One file, six rows, deliberately chosen so every plausible counter differs:

        two rows are older than the 7-day window, three rows are streaming snapshots of
        one in-window message, and one row is a second in-window message.

        | counter                                  | value |
        | ---------------------------------------- | ----- |
        | JSONL lines in the tree                  | 6     |
        | lines inside the window (no dedup)       | 4     |
        | files read                               | 1     |
        | gauges in the snapshot                   | 3     |
        | **deduplicated in-window entries**       | **2** |

        No two coincide, so a green result cannot come from counting lines, files, or
        gauges. The file's mtime is *now* while two of its rows are ancient, which is
        the case CLAUDE.md's JSONL invariant 6 names: the mtime prefilter must not be
        read as evidence about the records.

        Rivals also separated: the key being absent altogether (today's behaviour — a
        ``KeyError``), and ``True`` standing in for a count, which ``assertIsInstance``
        plus the ``bool`` exclusion rejects even though ``True == 1``.
        """
        now = datetime.now(UTC)
        stale = now - timedelta(days=30)
        fresh = now - timedelta(hours=2)
        self.write_log([
            usage_record(timestamp=stale, message_id="old-1", request_id="r-old-1",
                         output_tokens=10),
            usage_record(timestamp=stale + timedelta(minutes=1), message_id="old-2",
                         request_id="r-old-2", output_tokens=10),
            usage_record(timestamp=fresh, message_id="new-a", request_id="r-a",
                         output_tokens=3),
            usage_record(timestamp=fresh + timedelta(seconds=1), message_id="new-a",
                         request_id="r-a", output_tokens=40),
            usage_record(timestamp=fresh + timedelta(seconds=2), message_id="new-a",
                         request_id="r-a", output_tokens=250),
            usage_record(timestamp=fresh + timedelta(minutes=5), message_id="new-b",
                         request_id="r-b", output_tokens=7),
        ])

        stats = claude_pet.compute_usage()

        self.assertIn("entries", stats, "compute_usage() must report the in-window entry count")
        self.assertNotIsInstance(stats["entries"], bool)
        self.assertIsInstance(stats["entries"], int)
        self.assertEqual(stats["entries"], 2)

    def test_entries_is_zero_for_a_tree_whose_only_logs_are_older_than_the_window(self):
        """D, at the level it can be tested honestly: a months-old corpus is not data.

        Two stale files, one with an ancient mtime (skipped by the prefilter) and one
        touched just now (so only the per-record timestamp gate can reject it). Rivals:
        counting files (2), counting lines (2), ``_has_claude_logs()``'s answer for this
        same tree (True, i.e. 1 under any truthiness-based count) — all differ from 0.
        """
        now = datetime.now(UTC)
        ancient = now - timedelta(days=200)
        self.write_log([usage_record(timestamp=ancient, message_id="m1", request_id="r1",
                                     output_tokens=100)],
                       relative_path="p1/old-untouched.jsonl", mtime=ancient)
        self.write_log([usage_record(timestamp=ancient, message_id="m2", request_id="r2",
                                     output_tokens=100)],
                       relative_path="p2/old-but-touched.jsonl")

        stats = claude_pet.compute_usage()

        self.assertEqual(stats["entries"], 0)

    def test_entries_is_zero_for_an_empty_tree_and_the_other_keys_are_unchanged(self):
        """An empty tree still produces the full snapshot; ``entries`` is 0, not absent.

        Rivals: ``None`` for "unknown" (``assertEqual(0)`` rejects it, since ``None != 0``);
        omitting the key when there is nothing to count; dropping or renaming a sibling
        key while adding this one.
        """
        stats = claude_pet.compute_usage()

        self.assertEqual(stats["entries"], 0)
        for key in ("burn_5m", "burn_5m_opus", "spikes", "last_activity", "now"):
            self.assertIn(key, stats, f"compute_usage() lost the {key!r} key")


def stats_snapshot(entries=None, session_pct=None, weekly_pct=None, opus_pct=None):
    """A hand-built ``compute_usage()``-shaped snapshot.

    ``entries=None`` means *the key is absent*. Passing any ``*_pct`` adds the OLD gauge
    keys, so a test can hand an implementation that still reads them something to read —
    the new contract is that nothing reaches the pill from them.
    """
    def gauge(pct):
        return {"used": 0, "limit": 1, "left": 1, "pct": pct, "reset": None}

    snapshot = {
        "burn_5m": 0,
        "burn_5m_opus": 0,
        "spikes": {"session": False, "weekly": False, "opus": False},
        "model_kw": "fable",
        "last_activity": None,
        "now": datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    }
    for key, pct in (("session", session_pct), ("weekly", weekly_pct), ("opus", opus_pct)):
        if pct is not None:
            snapshot[key] = gauge(pct)
    if entries is not None:
        snapshot["entries"] = entries
    return snapshot


class SummaryNoDataFixtures(unittest.TestCase):
    """B. ``roam_summary(auth_error=...)`` and the precedence that replaces the zeros.

    Every test here calls the pure function directly; no window, no timers, no AppKit.
    """

    def summary(self, **overrides):
        args = dict(mode="sub", oauth=None, stats=None, onboard=None,
                    cost_today=None, has_admin_key=False)
        args.update(overrides)
        return claude_pet.roam_summary(**args)

    # ---- the pair that separates "genuinely zero" from "nothing to read" ----

    def test_expired_token_with_no_data_reports_token_expired_not_zero_percent(self):
        """auth_error + ``entries == 0`` → ``("status", "token_expired")``.

        Paired with the next test, which is byte-identical except ``entries=5``.
        Rivals and what each returns for THIS fixture:

        | implementation                                   | result |
        | ------------------------------------------------ | ------------------------- |
        | today (no ``auth_error`` parameter at all)        | ``TypeError`` |
        | decide "no data" from the gauge percentages       | ("status","token_expired") — ties here, separated by the next test |
        | decide "no data" from ``not stats``               | ("estimate", 0 % rows) — a non-empty dict is truthy |
        | ignore ``entries``, trust ``auth_error`` alone    | ("status","token_expired") — ties here, separated by the next test |
        | ignore ``auth_error``, trust ``entries`` alone    | ("status","scanning") — separated by ``..._without_auth_error_...`` |
        | **specified**                                     | **("status","token_expired")** |

        No single fixture separates all of them, which is the point: the two ties are
        broken by the sibling tests named in the table, and the truth table is what shows
        that they had to exist.
        """
        segment = self.summary(stats=stats_snapshot(entries=0), auth_error=True)

        self.assertEqual(segment, ("status", "token_expired"))

    def test_expired_token_with_real_data_is_still_token_expired(self):
        """auth_error + ``entries == 5`` → ``token_expired`` (rewritten 2026-10-05).

        Before: the estimate. Now (spec §1): a rejected token is ``token_expired`` "로그
        유무와 무관하게" — there is no estimate to show. The fixture carries old-shape gauges
        so an implementation that still reads them has something to read. Rival: today's
        rule (entries decides) → ``("estimate", …)``.
        """
        segment = self.summary(stats=stats_snapshot(entries=5, session_pct=0.0,
                                                    weekly_pct=0.0, opus_pct=0.0),
                               auth_error=True)

        self.assertEqual(segment, ("status", "token_expired"))

    def test_no_data_without_auth_error_scans_instead_of_fabricating_zeros(self):
        """``entries == 0``, no auth error → ``("status","scanning")``.

        This is defect 1 in its plainest form: today this returns
        ``("estimate", [("session",0.0,…),("weekly",0.0,…),("Fable",0.0,…)])`` and the
        pill reads ``세션 ≈0% · 주간 ≈0%``. Rivals: returning the estimate anyway
        (today); returning ``token_expired`` without an auth error (separated here);
        returning ``("status","loading")`` or another key (``assertEqual`` pins the key).
        """
        segment = self.summary(stats=stats_snapshot(entries=0), auth_error=False)

        # 2026-10-05: the spec lets the waiting state be "scanning" or "loading" (§1:
        # "scanning 은 서버 응답을 기다리는 상태로만 남거나 없앤다"). Either is a status.
        self.assertEqual(segment[0], "status")
        self.assertIn(segment[1], ("scanning", "loading"))

    def test_entries_not_the_percentages_decides_whether_there_is_data(self):
        """``entries == 0`` with *non-zero* gauges → still ``scanning``.

        The mirror image of the pair above: here the percentages say "plenty of data"
        and ``entries`` says none. Specified rule 4 requires there to BE data, so the
        rows are not built. An implementation that consults ``entries`` only inside the
        ``auth_error`` branch returns ``("estimate", …)`` here.
        """
        segment = self.summary(stats=stats_snapshot(entries=0, session_pct=42.0,
                                                    weekly_pct=17.0, opus_pct=9.0),
                               auth_error=False)

        self.assertEqual(segment[0], "status")
        self.assertIn(segment[1], ("scanning", "loading"))

    # ---- precedence ----

    def test_server_rows_win_over_an_expired_token_flag(self):
        """Rule 1 before rule 2: oauth rows present → ``("exact", rows)`` regardless.

        ``auth_error`` can still be set from an earlier failure while a cached or newly
        fetched row set is in hand. Rival: testing ``auth_error`` first, which would blank
        a perfectly good exact reading into ``token_expired``.
        """
        segment = self.summary(oauth=[("Session", 42.0, "in 3h")],
                               stats=stats_snapshot(entries=0), auth_error=True)

        self.assertEqual(segment, ("exact", [("Session", 42.0, False, "in 3h")]))

    def test_expired_token_wins_over_the_onboarding_hint(self):
        """Rule 2 before rule 3: auth_error + no data + ``onboard="login"`` →
        ``token_expired``.

        The user has Claude Code installed and once had a token; telling them to log in
        from scratch is the wrong instruction, and ``token_expired``'s text ("run Claude
        Code once to restore Exact mode") is the right one. Rival: keeping today's order,
        where the ``onboard`` branch sits above everything and returns ``onb_login``.
        """
        segment = self.summary(stats=stats_snapshot(entries=0), onboard="login",
                               auth_error=True)

        self.assertEqual(segment, ("status", "token_expired"))

    def test_onboarding_still_wins_when_there_is_no_auth_error(self):
        """Rule 3 unchanged: no auth error, ``onboard="install"`` → ``onb_install``.

        Rival: an over-eager rewrite that lets ``scanning`` or ``token_expired`` swallow
        the onboarding hint.
        """
        segment = self.summary(stats=stats_snapshot(entries=0), onboard="install",
                               auth_error=False)

        self.assertEqual(segment, ("status", "onb_install"))

    def test_auth_error_defaults_to_false_so_existing_callers_are_unchanged(self):
        """The parameter is keyword-with-default: called positionally as today,
        ``entries == 0`` yields ``scanning`` and never ``token_expired``.

        Rival: making ``auth_error`` required (every existing call site breaks) or
        defaulting it to ``True``.
        """
        segment = claude_pet.roam_summary("sub", None, stats_snapshot(entries=0), None,
                                          None, False)

        self.assertEqual(segment[0], "status")
        self.assertIn(segment[1], ("scanning", "loading"))

    # ---- backward compatibility of a snapshot with no "entries" key ----

    def test_a_snapshot_without_an_entries_key_never_yields_numbers(self):
        """No ``"entries"`` key, old-shape gauges (rewritten 2026-10-05).

        Before: the estimate rows, auth_error or not. Now: with auth_error →
        ``token_expired``; without → a waiting status. Rival: today's estimate segment
        built from the gauges (42/17/9)."""
        numbers = stats_snapshot(session_pct=42.0, weekly_pct=17.0, opus_pct=9.0)
        expired = claude_pet.roam_summary("sub", None, numbers, None, None, False,
                                          auth_error=True)
        self.assertEqual(expired, ("status", "token_expired"))
        waiting = claude_pet.roam_summary("sub", None, numbers, None, None, False)
        self.assertEqual(waiting[0], "status")
        self.assertIn(waiting[1], ("scanning", "loading"))

    def test_a_missing_snapshot_with_a_rejected_token_is_token_expired(self):
        """``stats=None`` + auth_error → ``token_expired`` (rewritten 2026-10-05).

        Before, a missing snapshot meant "first refresh not landed" → ``scanning``. But
        ``auth_error`` is only ever set by a finished fetch, and the spec now ties
        ``token_expired`` to the rejection alone. Rival: keeping the snapshot condition."""
        segment = self.summary(stats=None, auth_error=True)

        self.assertEqual(segment, ("status", "token_expired"))

    def test_api_mode_is_untouched_by_the_flag(self):
        """The API branch runs before any of this. Rival: inserting the auth_error test
        above the ``mode == "api"`` branch, which would hide the cost line from an API
        user whose unrelated OAuth token happens to be dead."""
        segment = self.summary(mode="api", has_admin_key=True, cost_today=1.23,
                               stats=stats_snapshot(entries=0), auth_error=True)

        self.assertEqual(segment, ("cost", (1.23, None, None)))


class TokenExpiredStatusKeyTests(unittest.TestCase):
    """The status key ``roam_summary`` now returns has to render in all four locales."""

    def test_token_expired_renders_as_one_status_run_in_every_locale(self):
        """NOT A GATE — green against the unfixed tree, because all four locales already
        carry ``token_expired`` (it is used elsewhere). It is recorded here as a
        *precondition* check for the new status key, not as evidence about the change,
        and §3 is satisfied for the change by the tests above, which were observed red.

        Rivals: returning a key no locale defines (``roam_summary_runs`` would draw
        the raw key); defining it in ``en`` only; a key that renders empty, which would
        show the user a blank pill and read as "nothing to report"."""
        for lang, table in claude_pet.TR.items():
            with self.subTest(lang=lang):
                self.assertIn("token_expired", table)
                self.assertTrue(table["token_expired"].strip())

        main, sub = claude_pet.roam_summary_runs(
            [("status", "token_expired")], lambda key: {"token_expired": "토큰 만료"}[key])
        self.assertEqual(main, [("토큰 만료", "status")])
        self.assertEqual(sub, [])


def module_ast():
    return ast.parse((ROOT / "claude_pet.py").read_text(encoding="utf-8"))


def calls_to(tree, name):
    return [node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == name]


class AdapterWiringTests(unittest.TestCase):
    """C and D's call site — AST only.

    Both call sites are closures inside ``run_gui()``: ``roam_summary_text()`` measures
    glyph widths through AppKit and the ``compute_onboard_state()`` call lives in the
    refresh worker. Neither can be executed without a GUI, and faking one would test the
    fake. So these tests read the source instead, in the style of
    ``tests/test_autostart.py``'s menu-wiring test, and are stated as source-level checks
    rather than behavioural ones.
    """

    def test_the_summary_adapter_passes_the_auth_error_flag_through(self):
        """C. Inside ``roam_summary_text``, the ``roam_summary(...)`` call carries an
        ``auth_error=`` keyword derived from ``OAUTH_STATUS``.

        Rivals: the keyword missing entirely (today — the expired-token state never
        reaches the pure function, so nothing above can ever fire in the app); a
        hardcoded ``auth_error=False`` or ``=True``; passing some unrelated flag, which
        the ``OAUTH_STATUS``/``auth_error`` reference in the expression rules out.
        """
        adapters = [node for node in ast.walk(module_ast())
                    if isinstance(node, ast.FunctionDef) and node.name == "roam_summary_text"]
        self.assertEqual(len(adapters), 1, "expected exactly one roam_summary_text definition")

        calls = calls_to(adapters[0], "roam_summary")
        self.assertEqual(len(calls), 1, "expected exactly one roam_summary call in the adapter")
        keywords = {kw.arg: ast.unparse(kw.value) for kw in calls[0].keywords}
        self.assertIn("auth_error", keywords,
                      "the adapter must pass auth_error through to roam_summary")
        expression = keywords["auth_error"]
        self.assertIn("OAUTH_STATUS", expression)
        self.assertIn("auth_error", expression)

    def test_the_onboarding_call_site_uses_a_token_flag(self):
        """D, revised 2026-10-05 round 2 (sou-verify; Coordinator decision after review):
        onboarding depends on whether a Claude OAuth token exists, not on log entries. The
        old version of this test required ``entries`` in the flag; that is now the rival —
        a user whose token is gone but whose logs are recent would never be offered the
        sign-in. Each call site's flag must be token-derived and must not mention entries.
        """
        tree = module_ast()
        calls = calls_to(tree, "compute_onboard_state")
        self.assertEqual(len(calls), 1, "expected exactly one compute_onboard_state call site")
        flag = " ".join([ast.unparse(a) for a in calls[0].args[1:]]
                        + [ast.unparse(k.value) for k in calls[0].keywords])
        self.assertNotIn("entries", flag)
        self.assertIn("token", flag.lower(), f"the onboarding flag is not token-derived: {flag!r}")
        self.assertNotIn("_has_claude_logs", flag)

    def test_has_claude_logs_is_gone_from_the_module(self):
        """D. The helper is deleted, not merely unused — a definition left behind is the
        one a later change reaches for again, and it is wrong for the same reason.

        Rivals: deleting the call but keeping the ``def``; renaming it; leaving a call
        anywhere else in the module.
        """
        tree = module_ast()
        self.assertEqual([node.name for node in ast.walk(tree)
                          if isinstance(node, ast.FunctionDef) and node.name == "_has_claude_logs"],
                         [])
        self.assertEqual(calls_to(tree, "_has_claude_logs"), [])
        self.assertFalse(hasattr(claude_pet, "_has_claude_logs"))


class OnboardStateContractTests(LogTreeMixin, unittest.TestCase):
    """D, revised 2026-10-05 round 2: ``compute_onboard_state(oauth, has_token)``. Logs —
    recent or stale — no longer suppress onboarding; only a token (or server rows) does.
    The keyword ``has_token`` is used so the old ``stats_have_logs`` signature fails."""

    def setUp(self):
        self.setUpLogTree()
        env = dict(os.environ)
        env.pop("CLAUDE_PET_FORCE_ONBOARD", None)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        original_mode = claude_pet.RUNTIME.get("mode")
        claude_pet.RUNTIME["mode"] = "sub"
        self.addCleanup(claude_pet.RUNTIME.__setitem__, "mode", original_mode)

    def test_recent_logs_without_a_token_still_reach_onboarding(self):
        """A tree with in-window entries and no token → onboarding. Rival: round 1's
        entries flag (5 entries → None)."""
        recent = datetime.now(UTC) - timedelta(minutes=5)
        self.write_log([usage_record(timestamp=recent, message_id="m", request_id="r",
                                     output_tokens=500)], relative_path="proj/new.jsonl")
        stats = claude_pet.compute_usage()
        self.assertEqual(stats["entries"], 1)
        self.assertIn(claude_pet.compute_onboard_state(None, has_token=False),
                      ("install", "login"))

    def test_a_token_suppresses_onboarding_even_without_rows(self):
        self.assertIsNone(claude_pet.compute_onboard_state(None, has_token=True))
        self.assertIsNone(claude_pet.compute_onboard_state([("Session", 1.0, None, "")],
                                                           has_token=False))
        self.assertIn(claude_pet.compute_onboard_state(None, has_token=False),
                      ("install", "login"))


if __name__ == "__main__":
    unittest.main()
