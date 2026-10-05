"""v1.1.0 fix round — gating tests written before the fix (AGENTS.md §3).

The Windows real-device test of 4c088dc found three defects; this module gates them.
Verifier: rel110-verify.  Production files are not touched here.

1. **Codex token expiry is visible, at parity with Claude.**  A Codex 401/403 used to make
   ``fetch_codex_usage`` return None and the Codex block silently vanished.  Interfaces:

   * ``CODEX_STATUS`` — a module-level dict ``{"auth_error": bool, "last_error": ...}``
     mirroring ``OAUTH_STATUS``.  ``fetch_codex_usage`` sets ``auth_error`` True on 401/403,
     False after a successful fetch, and False when there is no Codex token at all (no
     credentials keeps the published v0.26 promise: no row, no status).  A transient failure
     (429, 5xx, network, parse) leaves ``auth_error`` as it was.
   * ``codex_summary_segment(runtime, rows, spiking=False, cost_today=None, cost_month=None,
     api_error=False, api_stale=False, auth_error=False)`` — new keyword ``auth_error``.
     With Codex shown, in subscription mode, no rows and ``auth_error`` → ``("status",
     "codex_token_expired")``.  Rows win over the flag (as Claude's ``roam_summary`` lets
     server rows win over ``auth_error``).  API mode and a hidden Codex ignore the flag.
   * ``TR[lang]["codex_token_expired"]`` in en/ko/ja/es, containing "Codex" and the
     lower-case command ``codex`` (the user is told to run it once to sign in again).
   * Both adapters' ``state["codex_summary"]`` hooks hand ``codex_summary_segment`` an
     ``auth_error=`` that comes from ``CODEX_STATUS["auth_error"]`` — directly, or through a
     ``codex_auth_error`` value the refresh worker copies from ``CODEX_STATUS``.

2. **Transient failures keep the last good server values**, for both providers.  After a
   successful fetch, a later fetch that fails with 429, 5xx, a network error or a parse
   error returns the last good rows (marking them stale is allowed, not required); 401/403
   still clears them so token_expired can show.  The fixtures discriminate the three
   plausible wrong implementations named in the brief:

   | sequence              | clear on any error | keep on 401 | never refresh | **design** |
   | --------------------- | ------------------ | ----------- | ------------- | ---------- |
   | A, then 500           | None ✗             | A           | A             | **A**      |
   | A, then 401           | None               | A ✗         | A ✗           | **None**   |
   | A, then B             | B                  | B           | A ✗           | **B**      |
   | A, 500, then B        | B                  | B           | A ✗           | **B**      |

   Each fetch below starts with the provider's cache timestamp reset to 0, standing in for
   the cache window having elapsed — the cache's own timing is gated in
   tests/test_oauth_token_cache.py and is not re-tested here.

   **Settings save does not force a refetch unless the change needs one.**  The seam is a
   new pure function ``settings_cache_resets(prev, new) -> (reset_oauth, reset_codex)``
   over two settings dicts (keys as in ``RUNTIME`` plus ``"lang"``), and both platforms'
   ``save_settings`` zero ``_oauth_cache["t"]`` / ``_codex_cache["t"]`` only under a guard
   on its result.  Truth table (the policy the Coordinator set, 2026-10-05): a language
   change resets the OAuth cache (its row labels are translated at parse time); a Claude
   mode switch or a changed Anthropic Admin key resets the OAuth cache; a Codex mode switch
   or a changed OpenAI Admin key resets the Codex cache; anything else (gauges, show
   toggles, budgets, sensitivity, greeting, pet) resets nothing.  Rivals: today's
   unconditional OAuth reset; never resetting; resetting both on any change.

3. **The Windows settings section titles match macOS styling**: macOS draws them with
   ``NSFont.boldSystemFontOfSize_(13)`` — bold at the ordinary label size (13 pt is the
   AppKit label default).  The port's ``section`` used ``setPointSize(13)`` on a Qt font
   whose default is smaller, so the titles rendered visibly larger.  Gate (AST — the port's
   Qt is not importable on the macOS runner): the title's font is made bold and its size is
   not set to anything but a regular label's size, and ``label()`` itself sets no font, so
   "a regular label's size" is the default the title keeps.

4. **No popup-length budget is added.**  A per-script character budget for
   ``s_mode_sub``/``s_codex_mode_sub``/``s_mode_api``/``s_codex_mode_api`` would need the
   rendered width of each glyph in the platform font at the popup's 220 pt, which a static
   test cannot measure; any character count chosen here would be a guess, so the check is
   skipped on purpose.

Nothing here touches the network, the keychain or the user's home: urlopen is replaced,
the Codex auth file is a synthetic one in a temp directory, and the token reader is stubbed.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()

REPO = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO / "claude_pet.py"
WIN_APP = REPO / "windows" / "claude_pet_win.py"


def _require(name):
    if not hasattr(claude_pet, name):
        raise AssertionError(f"missing production interface: {name}")
    return getattr(claude_pet, name)


# ─────────────────────────────── fake HTTP ───────────────────────────────

def _http(code):
    def make():
        return urllib.error.HTTPError("https://synthetic.invalid/", code, "synthetic", {}, None)
    make.label = f"HTTP {code}"
    return make


def _net():
    return urllib.error.URLError("synthetic name resolution failure")


_net.label = "URLError"


def _timeout():
    return socket.timeout("synthetic timed out")


_timeout.label = "socket timeout"

BAD_JSON = b"<html>502 upstream gateway</html>"

# (label, outcome) — everything the brief calls transient.
TRANSIENTS = (
    ("HTTP 429", _http(429)),
    ("HTTP 500", _http(500)),
    ("HTTP 503", _http(503)),
    ("URLError", _net),
    ("socket timeout", _timeout),
    ("invalid JSON", BAD_JSON),
)
AUTH_FAILURES = (("HTTP 401", _http(401)), ("HTTP 403", _http(403)))


class _Seq:
    """urlopen stand-in that answers each request from a queue of outcomes."""

    def __init__(self):
        self.queue = []
        self.requests = 0

    def __call__(self, req, *a, **kw):
        self.requests += 1
        if not self.queue:
            raise AssertionError("unexpected extra request")
        outcome = self.queue.pop(0)
        if callable(outcome):
            raise outcome()
        return io.BytesIO(outcome)


def claude_body(session, weekly):
    return json.dumps({"limits": [
        {"kind": "five_hour", "percent": session, "resets_at": None},
        {"kind": "seven_day", "percent": weekly, "resets_at": None},
    ]}).encode()


def codex_body(session, weekly):
    return json.dumps({"rate_limit": {
        "primary_window": {"used_percent": session, "limit_window_seconds": 5 * 3600,
                           "reset_at": None},
        "secondary_window": {"used_percent": weekly, "limit_window_seconds": 7 * 86400,
                             "reset_at": None},
    }}).encode()


def _pcts(rows):
    return None if rows is None else [round(float(r[1])) for r in rows]


class _Harness(unittest.TestCase):
    """Common patches: no network at all, a private debug sink."""

    def setUp(self):
        self.http = _Seq()
        for p in (mock.patch.object(claude_pet.urllib.request, "urlopen", new=self.http),
                  mock.patch.object(claude_pet, "_dbg", new=lambda *a: None),
                  mock.patch("socket.create_connection",
                             side_effect=AssertionError("a test tried to reach the network"))):
            p.start()
            self.addCleanup(p.stop)


class ClaudeHarness(_Harness):
    def setUp(self):
        super().setUp()
        tok = "synthetic-oauth-token"
        for p in (mock.patch.object(claude_pet, "_read_oauth_token",
                                    new=lambda force=False: None if force else tok),
                  mock.patch.object(claude_pet, "_forget_oauth_token", new=lambda *a, **k: None),
                  mock.patch.object(claude_pet, "_fetch_cli_usage", new=lambda *a, **k: None),
                  mock.patch.dict(claude_pet._oauth_token_cache),
                  mock.patch.dict(claude_pet.OAUTH_STATUS, {"auth_error": False, "last_error": None}),
                  mock.patch.dict(claude_pet._oauth_cache, {"t": 0.0, "gauges": None})):
            p.start()
            self.addCleanup(p.stop)

    def fetch(self, *outcomes):
        """One fetch per outcome, each after the cache window (t reset to 0)."""
        out = None
        for o in outcomes:
            self.http.queue.append(o)
            claude_pet._oauth_cache["t"] = 0.0
            out = claude_pet.fetch_exact_usage()
        return out


class CodexHarness(_Harness):
    def setUp(self):
        super().setUp()
        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(td.cleanup)
        self.auth = os.path.join(td.name, "auth.json")
        with open(self.auth, "w", encoding="utf-8") as f:
            json.dump({"tokens": {"access_token": "synthetic-codex-token",
                                  "account_id": "acct-synthetic"}}, f)
        status = _require("CODEX_STATUS")
        for p in (mock.patch.object(claude_pet, "codex_auth_path", new=lambda *a, **k: self.auth),
                  mock.patch.dict(claude_pet._codex_cache, {"t": 0.0, "rows": None}),
                  mock.patch.dict(status, {"auth_error": False, "last_error": None})):
            p.start()
            self.addCleanup(p.stop)
        self.status = status

    def fetch(self, *outcomes):
        out = None
        for o in outcomes:
            self.http.queue.append(o)
            claude_pet._codex_cache["t"] = 0.0
            out = claude_pet.fetch_codex_usage()
        return out


# ───────────────────── 2. last good values survive a transient failure ─────────────────────

class ClaudeKeepsLastGoodRowsTests(ClaudeHarness):
    def test_fixture_rows_parse(self):
        self.assertEqual(_pcts(self.fetch(claude_body(42, 17))), [42, 17])

    def test_transient_failure_after_success_keeps_the_last_good_rows(self):
        for label, outcome in TRANSIENTS:
            with self.subTest(failure=label):
                claude_pet._oauth_cache["gauges"] = None
                rows = self.fetch(claude_body(42, 17), outcome)
                self.assertEqual(_pcts(rows), [42, 17],
                                 f"{label} after a success dropped the server values")
                self.assertFalse(claude_pet.OAUTH_STATUS["auth_error"])

    def test_auth_failure_after_success_clears_the_rows(self):
        for label, outcome in AUTH_FAILURES:
            with self.subTest(failure=label):
                claude_pet._oauth_cache["gauges"] = None
                claude_pet.OAUTH_STATUS["auth_error"] = False
                rows = self.fetch(claude_body(42, 17), outcome)
                self.assertIsNone(rows, f"{label} kept the rows — token_expired cannot show")
                self.assertTrue(claude_pet.OAUTH_STATUS["auth_error"])

    def test_a_later_success_replaces_the_rows(self):
        self.assertEqual(_pcts(self.fetch(claude_body(42, 17), claude_body(55, 20))), [55, 20])
        self.assertEqual(_pcts(self.fetch(claude_body(42, 17), _http(500), claude_body(61, 23))),
                         [61, 23], "after a kept failure, the next success must refresh")


class CodexKeepsLastGoodRowsTests(CodexHarness):
    def test_fixture_rows_parse(self):
        self.assertEqual(_pcts(self.fetch(codex_body(12, 34))), [12, 34])

    def test_transient_failure_after_success_keeps_the_last_good_rows(self):
        for label, outcome in TRANSIENTS:
            with self.subTest(failure=label):
                claude_pet._codex_cache["rows"] = None
                rows = self.fetch(codex_body(12, 34), outcome)
                self.assertEqual(_pcts(rows), [12, 34],
                                 f"{label} after a success dropped the Codex values")
                self.assertFalse(self.status["auth_error"],
                                 f"{label} is not an auth failure")

    def test_auth_failure_after_success_clears_rows_and_records_auth_error(self):
        for label, outcome in AUTH_FAILURES:
            with self.subTest(failure=label):
                claude_pet._codex_cache["rows"] = None
                self.status["auth_error"] = False
                rows = self.fetch(codex_body(12, 34), outcome)
                self.assertIsNone(rows, f"{label} kept the rows")
                self.assertTrue(self.status["auth_error"],
                                f"{label} must set CODEX_STATUS['auth_error']")

    def test_a_later_success_replaces_rows_and_clears_auth_error(self):
        self.assertEqual(_pcts(self.fetch(codex_body(12, 34), codex_body(40, 50))), [40, 50])
        self.assertEqual(_pcts(self.fetch(codex_body(12, 34), _http(503), codex_body(41, 51))),
                         [41, 51], "after a kept failure, the next success must refresh")
        self.fetch(_http(401))
        self.assertTrue(self.status["auth_error"])
        self.assertEqual(_pcts(self.fetch(codex_body(5, 6))), [5, 6])
        self.assertFalse(self.status["auth_error"], "a successful fetch must clear the flag")

    def test_no_credentials_is_not_token_expiry(self):
        """No auth.json is the published v0.26 "no credentials, no row" case — not an
        expired token."""
        self.fetch(_http(401))
        self.assertTrue(self.status["auth_error"])
        os.remove(self.auth)
        claude_pet._codex_cache["t"] = 0.0
        self.assertIsNone(claude_pet.fetch_codex_usage())
        self.assertFalse(self.status["auth_error"],
                         "with no Codex token at all the flag must be down")
        self.assertEqual(self.http.requests, 1, "no request may be sent without a token")


# ───────────────────── 1. Codex token expiry is visible ─────────────────────

def _rt(**kw):
    rt = {"show_codex": True, "codex_mode": "sub", "codex_gauges": ["session", "weekly"],
          "openai_admin_key": "", "codex_budget": 0.0}
    rt.update(kw)
    return rt


ROWS = [("codex_session", 12.0, None, None), ("codex_weekly", 34.0, None, None)]


class CodexTokenExpiredSegmentTests(unittest.TestCase):
    def seg(self, rt, rows, **kw):
        return claude_pet.codex_summary_segment(rt, rows, **kw)

    def test_expired_token_shows_a_status_instead_of_vanishing(self):
        self.assertEqual(self.seg(_rt(), None, auth_error=True),
                         ("status", "codex_token_expired"))
        self.assertEqual(self.seg(_rt(), [], auth_error=True),
                         ("status", "codex_token_expired"))

    def test_without_the_flag_nothing_changes(self):
        self.assertIsNone(self.seg(_rt(), None, auth_error=False))
        self.assertIsNone(self.seg(_rt(), None))

    def test_rows_win_over_the_flag_as_on_the_claude_side(self):
        kind, payload = self.seg(_rt(), ROWS, auth_error=True)
        self.assertEqual(kind, "exact")
        self.assertEqual([round(r[1]) for r in payload], [12, 34])

    def test_hidden_codex_and_api_mode_ignore_the_flag(self):
        self.assertIsNone(self.seg(_rt(show_codex=False), None, auth_error=True))
        self.assertIsNone(self.seg(_rt(codex_gauges=[]), None, auth_error=True))
        api = _rt(codex_mode="api")
        self.assertEqual(self.seg(api, None, auth_error=True), self.seg(api, None),
                         "API mode must be unaffected by the subscription token")
        self.assertEqual(self.seg(api, None, auth_error=True),
                         ("status", "codex_need_admin_key"))

    def test_status_renders_the_translated_text(self):
        main, sub = claude_pet.roam_summary_runs([("status", "codex_token_expired")],
                                                 claude_pet.t)
        self.assertEqual(main, [(claude_pet.t("codex_token_expired"), "status")])
        self.assertNotEqual(claude_pet.t("codex_token_expired"), "codex_token_expired")

    def test_tr_key_in_every_language_names_codex_and_the_command(self):
        for lang in ("en", "ko", "ja", "es"):
            with self.subTest(lang=lang):
                text = claude_pet.TR[lang].get("codex_token_expired")
                self.assertIsInstance(text, str, f"TR[{lang!r}] lacks codex_token_expired")
                self.assertIn("Codex", text)
                self.assertRegex(text, r"(?<![A-Za-z])codex(?![A-Za-z])",
                                 "the text must tell the user to run `codex`")


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _hook_calls(tree, qual):
    """codex_summary_segment calls inside the state['codex_summary'] lambda."""
    out = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Subscript)
                and isinstance(n.targets[0].slice, ast.Constant)
                and n.targets[0].slice.value == "codex_summary"
                and isinstance(n.value, ast.Lambda)):
            for c in ast.walk(n.value):
                if isinstance(c, ast.Call):
                    f = c.func
                    if ((qual is None and isinstance(f, ast.Name)
                         and f.id == "codex_summary_segment")
                            or (qual and isinstance(f, ast.Attribute)
                                and f.attr == "codex_summary_segment")):
                        out.append(c)
    return out


class CodexAuthErrorWiringTests(unittest.TestCase):
    """Both adapters must hand the flag to the segment.  Accepted: an ``auth_error=``
    whose expression reads ``CODEX_STATUS``, or one that reads a ``codex_auth_error``
    value which the same file's refresh worker copies from ``CODEX_STATUS``."""

    def check(self, path, qual):
        tree = _tree(path)
        calls = _hook_calls(tree, qual)
        self.assertEqual(len(calls), 1, f"{path.name}: expected one codex_summary hook call")
        kws = [k.value for k in calls[0].keywords if k.arg == "auth_error"]
        self.assertEqual(len(kws), 1, f"{path.name}: the hook must pass auth_error=")
        text = ast.unparse(kws[0])
        if "CODEX_STATUS" in text and "auth_error" in text:
            return
        self.assertIn("codex_auth_error", text,
                      f"{path.name}: auth_error must come from CODEX_STATUS; got {text}")
        feeds = [ast.unparse(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Subscript)
                 and isinstance(t.slice, ast.Constant) and t.slice.value == "codex_auth_error"]
        self.assertTrue(any("CODEX_STATUS" in f for f in feeds),
                        f"{path.name}: codex_auth_error must be copied from CODEX_STATUS; "
                        f"got {feeds!r}")

    def test_macos_adapter(self):
        self.check(APP_SOURCE, None)

    def test_windows_call_site(self):
        self.check(WIN_APP, "cp")


# ───────────────────── 2b. settings save does not force a refetch ─────────────────────

BASE = {"lang": "ko", "mode": "sub", "admin_key": "", "api_budget": 0.0, "spike_mult": 1.0,
        "greet": True, "show_claude": True, "claude_gauges": ["session", "weekly"],
        "show_codex": True, "codex_mode": "sub", "codex_gauges": ["session"],
        "openai_admin_key": "", "codex_budget": 0.0}


class SettingsCacheResetTests(unittest.TestCase):
    CASES = (
        ("nothing changed", {}, (False, False)),
        ("gauges", {"claude_gauges": ["session"], "codex_gauges": ["weekly"]}, (False, False)),
        ("show toggles", {"show_claude": False, "show_codex": False}, (False, False)),
        ("budgets", {"api_budget": 50.0, "codex_budget": 20.0}, (False, False)),
        ("sensitivity/greeting", {"spike_mult": 2.0, "greet": False}, (False, False)),
        ("language", {"lang": "en"}, (True, False)),
        ("Claude mode", {"mode": "api"}, (True, False)),
        ("Anthropic Admin key", {"admin_key": "sk-ant-admin-synthetic"}, (True, False)),
        ("Codex mode", {"codex_mode": "api"}, (False, True)),
        ("OpenAI Admin key", {"openai_admin_key": "sk-admin-synthetic"}, (False, True)),
        ("both", {"mode": "api", "codex_mode": "api"}, (True, True)),
    )

    def test_truth_table(self):
        fn = _require("settings_cache_resets")
        for label, change, expected in self.CASES:
            with self.subTest(change=label):
                new = dict(BASE, **change)
                got = tuple(bool(x) for x in fn(dict(BASE), new))
                self.assertEqual(got, expected, f"{label}: (reset_oauth, reset_codex)")


def _save_settings_fns():
    mac = [n for n in ast.walk(_tree(APP_SOURCE))
           if isinstance(n, ast.FunctionDef) and n.name == "save_settings"]
    win = [n for n in ast.walk(_tree(WIN_APP))
           if isinstance(n, ast.FunctionDef) and n.name == "save_settings"]
    return (("claude_pet.py", mac), ("claude_pet_win.py", win))


class SaveSettingsGuardsTheRefetchTests(unittest.TestCase):
    CACHE_T = re.compile(r"^(?:cp\.)?_(oauth|codex)_cache\[['\"]t['\"]\]$")

    def test_cache_resets_in_save_settings_are_guarded_by_settings_cache_resets(self):
        for name, fns in _save_settings_fns():
            with self.subTest(file=name):
                self.assertEqual(len(fns), 1, f"{name}: expected one save_settings")
                fn = fns[0]
                parents = {id(c): p for p in ast.walk(fn) for c in ast.iter_child_nodes(p)}
                bound = set()
                calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
                         and ast.unparse(c.func).split(".")[-1] == "settings_cache_resets"]
                self.assertTrue(calls, f"{name}: save_settings must ask settings_cache_resets")
                for c in calls:
                    holder = parents.get(id(c))
                    if isinstance(holder, ast.Assign):
                        for t in holder.targets:
                            bound |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
                resets = [n for n in ast.walk(fn) if isinstance(n, ast.Assign)
                          and any(self.CACHE_T.match(ast.unparse(t)) for t in n.targets)]
                kinds = {self.CACHE_T.match(ast.unparse(t)).group(1)
                         for n in resets for t in n.targets if self.CACHE_T.match(ast.unparse(t))}
                self.assertIn("oauth", kinds, f"{name}: a language change still needs the "
                                              "OAuth cache reset (guarded)")
                for n in resets:
                    guards, cur = [], n
                    while id(cur) in parents:
                        cur = parents[id(cur)]
                        if isinstance(cur, (ast.If, ast.IfExp)):
                            guards.append(cur.test)
                    ok = any((bound & {x.id for x in ast.walk(g) if isinstance(x, ast.Name)})
                             or "settings_cache_resets" in ast.unparse(g) for g in guards)
                    self.assertTrue(ok, f"{name}: `{ast.unparse(n)}` runs on every save — it "
                                        "must be guarded by settings_cache_resets")


# ───────────────────── 3. Windows section title font ─────────────────────

class WinSectionTitleFontTests(unittest.TestCase):
    SIZE_SETTERS = {"setPointSize", "setPointSizeF", "setPixelSize"}

    def _settings_nested(self, name):
        tree = _tree(WIN_APP)
        dlg = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SettingsDialog"]
        self.assertEqual(len(dlg), 1)
        found = [n for n in ast.walk(dlg[0]) if isinstance(n, ast.FunctionDef) and n.name == name]
        self.assertEqual(len(found), 1, f"SettingsDialog must define one nested {name}()")
        return found[0]

    def test_section_title_is_bold_at_the_regular_label_size(self):
        section = self._settings_nested("section")
        problems = []
        for n in ast.walk(section):
            if not isinstance(n, ast.Call):
                continue
            attr = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            if attr in self.SIZE_SETTERS and not any(
                    "pointSize" in ast.unparse(a) for a in n.args):
                problems.append(f"the title size is set explicitly: {ast.unparse(n)}")
            if attr == "QFont" and len(n.args) >= 2:
                problems.append(f"a fresh QFont with its own size: {ast.unparse(n)}")
            if attr == "setStyleSheet" and "font" in ast.unparse(n).lower():
                problems.append(f"a stylesheet font: {ast.unparse(n)}")
        text = ast.unparse(section)
        if not (re.search(r"setBold\(True\)", text) or re.search(r"setWeight\([^)]*Bold", text)):
            problems.append("the section title must be bold")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_regular_label_keeps_the_default_font(self):
        label = self._settings_nested("label")
        setters = [ast.unparse(n) for n in ast.walk(label) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute)
                   and n.func.attr in self.SIZE_SETTERS | {"setFont", "setStyleSheet"}]
        self.assertEqual(setters, [], "label() must keep the default font — it is the size "
                                      "the section title is measured against")


if __name__ == "__main__":
    unittest.main()
