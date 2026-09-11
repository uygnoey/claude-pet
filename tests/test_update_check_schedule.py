#!/usr/bin/env python3
"""Update-check schedule and on-demand check gates — owned by agent
`verifier-v023` (2026-09-11); supersedes the `verifier-upd` draft of the same
day, which pinned the schedule-only change and was stopped when the scope grew.

What this pins
--------------
The user asked, in the Developer's session on 2026-09-11, for two things:
that the app stop checking GitHub for a new release when it starts and check
periodically instead (hourly), and that a user on any older version — "0.20
when the latest is 0.24" — be able to update to the latest release in one
step.  The Developer's change to `claude_pet.py` is pinned here by reading the
module *source* with `ast`; nothing here imports AppKit or calls `run_gui()`.

  1. `UPDATE_CHECK_SEC` is the literal `3600` at module level — not
     `6 * 3600`, and not the half-hour reading the user also offered.
  2. `run_gui()` no longer starts a thread — or anything else — that runs
     `_run_update_check` at launch.  Its top level stamps
     `_upd_cache["t"] = time.time()` before `AppHelper.runEventLoop()`, so the
     cooldown counts from launch and the first check falls one interval later.
  3. The refresh worker's gate is unchanged —
     `not state.get("update") and time.time() - _upd_cache["t"] > UPDATE_CHECK_SEC`
     → `_run_update_check()` → `poll_github_update(state)`.
  4. `_run_update_check` now *returns* the poll's status (`'update'`,
     `'current'`, `'failed'`) and `None` while a check is already running, and
     it clears its busy flag even when the poll raises.
  5. `_run_update_check` has exactly two call sites in the whole module: the
     worker gate, and `Handler.checkUpdate_` — the right-click "check for
     updates" action.  Both are located by AST and the list is closed: a third
     caller anywhere, or one of these moving, fails the gate.
  6. The context menu adds an item titled `t("menu_check_update")` with the
     selector `checkUpdate:`, targeted at the handler, after the version row.
  7. `Handler.checkUpdate_` runs the check off the main thread; on `'update'`
     it calls `install_github_update(url, expect_version=tag)` with the pending
     `(tag, url)` and asks the main thread to `quitApp:`; on every other
     outcome it hands one message to `showUpdateMessage:` on the main thread —
     `upd_install_failed`, `upd_current` (with the running version),
     `upd_busy` for `None`, `upd_failed` otherwise.  `showUpdateMessage_`
     shows `t("upd_title")` and the message in an `NSAlert`.
  8. The six new `TR` keys exist in all four locales, and the Korean menu
     label is exactly "⬆︎ 업데이트 확인…" — the string the v0.23 release notes
     tell users to look for.
  9. Direct-to-latest: with `APP_VERSION` patched to "0.20" and GitHub's
     `/releases/latest` answering "v0.24", `check_github_update` makes exactly
     one request, to that endpoint, and returns `('update', '0.24', url)`;
     the poll then publishes `('0.24', url)` and the menu action installs
     with `expect_version="0.24"`.  No intermediate version is fetched,
     computed or offered.

Rival implementations this module rules out.  Each was run as a scratch
mutant of `claude_pet.py` and made this module RED; the verbatim failures are
in docs-design/release-v023-verification-20260911.md.

  * The pre-change code (HEAD 6d47df5e): `UPDATE_CHECK_SEC = 6 * 3600` and
    `threading.Thread(target=_run_update_check, daemon=True).start()` at
    launch, no stamp, no menu action.
  * Restoring only the launch thread while keeping the stamp and 3600 — the
    "check at launch AND hourly" reading of the request.
  * `UPDATE_CHECK_SEC = 6 * 3600`, or `30 * 60`, with the rest intact.
  * Dropping the launch stamp: `_upd_cache["t"]` then stays at its module
    initialiser `0.0`, so the priming refresh checks at launch through the
    worker — which a test that only greps for `Thread` would pass.
  * A synchronous `_run_update_check()` (or `handler.checkUpdate_(None)`) at
    run_gui's top level — the same launch check without a thread.
  * A third `_run_update_check` caller anywhere in the module.
  * A `_run_update_check` that returns nothing (the pre-change `return`) or
    that reports `'failed'` while busy — the menu action would then show the
    wrong message, or install nothing without saying why.
  * A `checkUpdate_` that only reports and never installs, one that installs
    without `expect_version`, one that installs when no `(tag, url)` is
    pending, one that shows the alert from the worker thread, or one that
    maps a status to the wrong message key.
  * A locale missing one of the six keys, or a Korean label that does not
    match the release notes.
  * A `check_github_update` that steps to the next version instead of the
    latest, lists `/releases` instead of `/releases/latest`, or always
    answers `'update'`.

Fixtures: `claude_pet._upd_cache` is saved and restored around every case
that touches it; `urlopen`, `platform.machine`, `check_github_update`,
`install_github_update` and `threading.Thread` are stubs, so no network is
reached, no GitHub release is consulted, no bundle is downloaded and no thread
is started.  Nothing under `~` is read or written.
"""

import ast
import copy
import json
import types
import unittest
from pathlib import Path
from unittest import mock

import claude_pet

REPO = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO / "claude_pet.py"

STARTER = "_run_update_check"
LAUNCH_STAMP = "_upd_cache['t'] = time.time()"
EVENT_LOOP = "AppHelper.runEventLoop()"
WORKER_GATE = ("not state.get('update') "
               "and time.time() - _upd_cache['t'] > UPDATE_CHECK_SEC")
EXPECTED_INTERVAL = 3600
LOCALES = ("en", "ko", "ja", "es")
NEW_TR_KEYS = ("menu_check_update", "upd_title", "upd_current", "upd_failed",
               "upd_install_failed", "upd_busy")
KO_CHECK_LABEL = "⬆︎ 업데이트 확인…"
MENU_SELECTOR = "checkUpdate:"
ALERT_SELECTOR = "showUpdateMessage:"
QUIT_SELECTOR = "quitApp:"
LATEST_URL = f"https://api.github.com/repos/{claude_pet.GITHUB_REPO}/releases/latest"

# A realistic launch instant. It must be far larger than the interval so that
# a missing stamp (`_upd_cache["t"]` left at `0.0`) makes the gate true at
# launch — that is exactly the rival the behavioural case has to see.
LAUNCH = 1_700_000_000.0


# ───────────────────────────── source extraction ─────────────────────────────

def _module_tree():
    return ast.parse(APP_SOURCE.read_text(encoding="utf-8"),
                     filename=str(APP_SOURCE))


def _run_gui(tree):
    found = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == "run_gui"]
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one module-level `def run_gui`, found {len(found)}")
    return found[0]


def _parents(tree):
    """child → parent for every node, so a reference can be placed in its
    enclosing defs and classes."""
    out = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            out[child] = parent
    return out


def _enclosing_names(node, parents):
    """Names of the defs/classes around `node`, innermost first."""
    chain = []
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(node.name)
    return chain


def _interval_assignments(tree):
    return [n for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "UPDATE_CHECK_SEC"]


def _launch_stamp_indices(run_gui):
    """Positions in run_gui's *direct* body of `_upd_cache['t'] = time.time()`.

    Direct body only: a stamp inside a nested function or class is not a
    launch stamp, so it is deliberately not found here.
    """
    return [i for i, stmt in enumerate(run_gui.body)
            if isinstance(stmt, ast.Assign) and ast.unparse(stmt) == LAUNCH_STAMP]


def _event_loop_indices(run_gui):
    return [i for i, stmt in enumerate(run_gui.body)
            if isinstance(stmt, ast.Expr) and ast.unparse(stmt) == EVENT_LOOP]


def _is_starter_call(stmt):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == STARTER)


def _worker_gates(scope):
    """Every `if` in `scope` whose direct body calls `_run_update_check()`."""
    return [n for n in ast.walk(scope)
            if isinstance(n, ast.If) and any(_is_starter_call(s) for s in n.body)]


def _nested_defs(scope, name):
    return [n for n in ast.walk(scope)
            if isinstance(n, ast.FunctionDef) and n.name == name]


def _class_in(scope, name):
    found = [n for n in scope.body if isinstance(n, ast.ClassDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(f"expected exactly one `class {name}` in run_gui, found {len(found)}")
    return found[0]


def _method_of(cls, name):
    found = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(f"expected exactly one `def {name}` in class {cls.name}, found {len(found)}")
    return found[0]


def _calls_passing(scope, name):
    """Calls anywhere in `scope` that hand `name` over as a bare argument —
    `threading.Thread(target=name)`, `Timer(0, name)`, and every other
    scheduling shape look the same from here."""
    hits = []
    for call in ast.walk(scope):
        if not isinstance(call, ast.Call):
            continue
        operands = list(call.args) + [kw.value for kw in call.keywords]
        if any(isinstance(a, ast.Name) and a.id == name for a in operands):
            hits.append(ast.unparse(call))
    return hits


def _top_level_calls_to(run_gui, names):
    """Calls to any of `names` — as a bare name or as a method/attribute —
    made directly at run_gui's top level, i.e. at launch, not inside a nested
    def or class (those run later, if ever)."""
    hits = []
    for stmt in run_gui.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for call in ast.walk(stmt):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            callee = (func.id if isinstance(func, ast.Name)
                      else func.attr if isinstance(func, ast.Attribute) else None)
            if callee in names:
                hits.append(ast.unparse(call))
    return hits


def _compile_statement(stmt):
    return compile(ast.Module(body=[stmt], type_ignores=[]), str(APP_SOURCE), "exec")


def _compile_expression(expr):
    return compile(ast.Expression(body=expr), str(APP_SOURCE), "eval")


def _exec_def(node, scope):
    """Execute one extracted `def` in `scope` and return the function.

    Same shape as tests/test_companion_motion.py's `gui_method`: the real
    body, compiled against the real filename, with the collaborators it
    reaches for supplied by the test instead of by AppKit.
    """
    node = copy.deepcopy(node)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(APP_SOURCE), "exec"), scope)
    return scope[node.name]


def _tr_literal(tree):
    found = [n for n in tree.body
             if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "TR"]
    if len(found) != 1:
        raise AssertionError(f"expected exactly one module-level `TR = ...`, found {len(found)}")
    return ast.literal_eval(found[0].value)


def _fake_t(key, **kw):
    """A `t()` stand-in whose output names the key and every format argument,
    so a wrong key or a missing `v=` is visible in the assertion message."""
    return f"<{key}>" + ("" if not kw else ":" + ",".join(
        f"{k}={v}" for k, v in sorted(kw.items())))


class _SyncThread:
    """`threading.Thread` stand-in: `.start()` runs the target here and now
    and records that a daemon thread was asked for."""
    started = []

    def __init__(self, target=None, daemon=None, **kw):
        self.target = target
        self.daemon = daemon

    def start(self):
        type(self).started.append(self.daemon)
        self.target()


class _MainThreadProxy:
    """The `self` handed to an extracted Handler method: records every
    `performSelectorOnMainThread:` the worker asks for."""

    def __init__(self):
        self.dispatched = []

    def performSelectorOnMainThread_withObject_waitUntilDone_(self, sel, obj, wait):
        self.dispatched.append((sel, obj, wait))


class _FakeResponse:
    """The object `urlopen` returns, as tests/test_settings_and_install.py
    builds it, plus a record of the URL that was asked for."""
    requested = []

    def __init__(self, payload):
        self.payload = payload

    def __call__(self, req, timeout=None):
        url = getattr(req, "full_url", req)
        type(self).requested.append(url)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def _release_payload(tag):
    return {"tag_name": f"v{tag}",
            "assets": [{"name": "ClaudePet.zip",
                        "browser_download_url": "https://example.test/ClaudePet.zip"},
                       {"name": "ClaudePet-universal.zip",
                        "browser_download_url": "https://example.test/ClaudePet-universal.zip"}]}


def _preserve_upd_cache(test):
    saved = dict(claude_pet._upd_cache)
    claude_pet._upd_cache.clear()
    claude_pet._upd_cache.update({"t": 0.0, "busy": False})
    test.addCleanup(lambda: (claude_pet._upd_cache.clear(),
                             claude_pet._upd_cache.update(saved)))


# ───────────────────────────── structural gates ─────────────────────────────

class UpdateCheckScheduleSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = _module_tree()
        cls.run_gui = _run_gui(cls.tree)
        cls.parents = _parents(cls.tree)

    def test_update_check_sec_is_the_literal_3600(self):
        assignments = _interval_assignments(self.tree)
        self.assertEqual(
            len(assignments), 1,
            "UPDATE_CHECK_SEC must be assigned exactly once at module level")
        value = assignments[0].value
        self.assertIsInstance(
            value, ast.Constant,
            f"UPDATE_CHECK_SEC must be a bare literal, not "
            f"`{ast.unparse(value)}` — `6 * 3600` and `30 * 60` are the rivals")
        self.assertIs(type(value.value), int)
        self.assertEqual(
            value.value, EXPECTED_INTERVAL,
            f"UPDATE_CHECK_SEC is {value.value}, not the hourly {EXPECTED_INTERVAL}")
        self.assertEqual(claude_pet.UPDATE_CHECK_SEC, EXPECTED_INTERVAL)

    def test_nothing_at_launch_reaches_the_update_check(self):
        run_gui = self.run_gui
        # (a) The thread the change removed, in every scheduling shape.
        self.assertEqual(
            _calls_passing(self.tree, STARTER), [],
            "something still hands _run_update_check to a scheduler — the "
            "launch-time `threading.Thread(target=_run_update_check, ...)` "
            "was removed on purpose")
        # (b) No direct call at run_gui's top level either — the same launch
        #     check without a thread, including one routed through the menu
        #     action's method.
        self.assertEqual(
            _top_level_calls_to(
                run_gui, {STARTER, "poll_github_update", "check_github_update",
                          "checkUpdate_", "doUpdate_"}),
            [],
            "run_gui's top level runs an update check at launch")

    def test_the_starter_has_exactly_two_callers_the_worker_gate_and_the_menu_action(self):
        run_gui = self.run_gui
        refs = [n for n in ast.walk(self.tree)
                if isinstance(n, ast.Name) and n.id == STARTER]
        self.assertEqual(
            len(refs), 2,
            f"{len(refs)} references to {STARTER}; the worker gate's call and "
            "Handler.checkUpdate_'s call must be the only two — a third caller "
            "is a new schedule and needs its own gate")
        # One is the worker gate's `_run_update_check()` statement …
        gates = _worker_gates(run_gui)
        self.assertEqual(len(gates), 1, "expected exactly one worker gate")
        gate_call = next(s for s in gates[0].body if _is_starter_call(s)).value
        gate_ref = [r for r in refs if r is gate_call.func]
        self.assertEqual(len(gate_ref), 1, "the worker gate's call is not among the references")
        self.assertEqual(
            _enclosing_names(gate_ref[0], self.parents)[:3], ["work", "refresh_", "Ticker"],
            "the worker gate must sit in Ticker.refresh_'s `work`")
        # … the other is `status = _run_update_check()` inside the `work`
        # closure of Handler.checkUpdate_, and nothing else.
        (other,) = [r for r in refs if r is not gate_call.func]
        call = self.parents[other]
        self.assertIsInstance(call, ast.Call, "the second reference must be a call")
        self.assertEqual(ast.unparse(call), f"{STARTER}()")
        assign = self.parents[call]
        self.assertIsInstance(assign, ast.Assign,
                              "the menu action must keep the status the check returns")
        self.assertEqual([ast.unparse(t) for t in assign.targets], ["status"])
        self.assertEqual(
            _enclosing_names(other, self.parents),
            ["work", "checkUpdate_", "Handler", "run_gui"],
            "the second caller must be the worker closure of Handler.checkUpdate_")

    def test_launch_stamps_the_cooldown_origin_before_the_event_loop(self):
        run_gui = self.run_gui
        stamps = _launch_stamp_indices(run_gui)
        self.assertEqual(
            len(stamps), 1,
            f"run_gui's top level must contain exactly one `{LAUNCH_STAMP}`; "
            f"found {len(stamps)} — without it _upd_cache['t'] stays 0.0 and "
            "the priming refresh checks at launch through the worker")
        loops = _event_loop_indices(run_gui)
        self.assertEqual(len(loops), 1, f"expected exactly one `{EVENT_LOOP}`")
        self.assertLess(
            stamps[0], loops[0],
            "the launch stamp must precede AppHelper.runEventLoop() — after "
            "it, it never runs")
        # No other assignment to _upd_cache['t'] anywhere in run_gui: a later
        # reset would silently undo the stamp.
        writes = [n for n in ast.walk(run_gui)
                  if isinstance(n, ast.Assign)
                  and any(ast.unparse(t) == "_upd_cache['t']" for t in n.targets)]
        self.assertEqual(len(writes), 1,
                         [ast.unparse(w) for w in writes])

    def test_refresh_worker_gate_and_its_chain_are_intact(self):
        run_gui = self.run_gui
        refresh = _nested_defs(run_gui, "refresh_")
        self.assertEqual(len(refresh), 1, "expected exactly one `refresh_`")
        work = _nested_defs(refresh[0], "work")
        self.assertEqual(len(work), 1, "expected exactly one `work` in refresh_")
        gates = _worker_gates(work[0])
        self.assertEqual(
            len(gates), 1,
            "the refresh worker must gate _run_update_check() behind exactly one `if`")
        self.assertEqual(
            _worker_gates(run_gui), gates,
            "an update-check gate exists outside the refresh worker")
        gate = gates[0]
        self.assertEqual(ast.unparse(gate.test), WORKER_GATE)
        # Component-wise, so a wrong comparison names itself.
        compare = gate.test.values[1]
        self.assertIsInstance(compare, ast.Compare)
        self.assertEqual([type(op) for op in compare.ops], [ast.Gt],
                         "the cooldown comparison must be strict `>`")
        self.assertEqual(ast.unparse(compare.comparators[0]), "UPDATE_CHECK_SEC",
                         "the cooldown must compare against UPDATE_CHECK_SEC")
        # The chain below the gate: _run_update_check → return poll_github_update(state).
        starter = [n for n in run_gui.body
                   if isinstance(n, ast.FunctionDef) and n.name == STARTER]
        self.assertEqual(len(starter), 1,
                         f"expected exactly one `def {STARTER}` directly in run_gui")
        returns = [ast.unparse(r.value) for r in ast.walk(starter[0])
                   if isinstance(r, ast.Return) and r.value is not None]
        self.assertEqual(
            returns, ["None", "poll_github_update(state)"],
            "_run_update_check must return None while busy and the poll's "
            "status otherwise — the menu action reads that value")

    def test_context_menu_offers_check_for_updates_wired_to_the_handler(self):
        run_gui = self.run_gui
        items = [c for c in ast.walk(run_gui)
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                 and c.func.attr == "initWithTitle_action_keyEquivalent_"
                 and len(c.args) >= 2
                 and isinstance(c.args[1], ast.Constant) and c.args[1].value == MENU_SELECTOR]
        self.assertEqual(len(items), 1,
                         f"expected exactly one menu item with action {MENU_SELECTOR!r}")
        item = items[0]
        self.assertEqual(ast.unparse(item.args[0]), "t('menu_check_update')",
                         "the item's title must be the localized menu_check_update string")
        assign = self.parents[item]
        self.assertIsInstance(assign, ast.Assign, "the item must be bound to a name")
        (target,) = assign.targets
        self.assertIsInstance(target, ast.Name)
        body = self.parents[assign]
        siblings = [ast.unparse(s) for s in getattr(body, "body", [])]
        at = siblings.index(ast.unparse(assign))
        after = siblings[at + 1:]
        self.assertIn(f"{target.id}.setTarget_(handler)", after,
                      "the item must be targeted at the handler")
        self.assertIn(f"menu.addItem_({target.id})", after,
                      "the item must be added to the context menu")
        version_rows = [i for i, s in enumerate(siblings) if s == "menu.addItem_(vitem)"]
        self.assertEqual(len(version_rows), 1, "expected exactly one version row in the menu")
        self.assertLess(version_rows[0], at,
                        "the check item must follow the version row")
        # The selector must resolve to real handler methods.
        handler = _class_in(run_gui, "Handler")
        _method_of(handler, "checkUpdate_")
        _method_of(handler, "showUpdateMessage_")

    def test_new_translation_keys_exist_in_all_four_locales(self):
        table = _tr_literal(self.tree)
        for lang in LOCALES:
            with self.subTest(locale=lang):
                missing = [k for k in NEW_TR_KEYS
                           if not isinstance(table.get(lang, {}).get(k), str)
                           or not table[lang][k].strip()]
                self.assertEqual(missing, [], f"TR[{lang!r}] lacks {missing}")
                self.assertIn("{v}", table[lang]["upd_current"],
                              "upd_current must carry the running version")
                # The runtime table is the literal one.
                for k in NEW_TR_KEYS:
                    self.assertEqual(claude_pet.TR[lang][k], table[lang][k])
        self.assertEqual(table["ko"]["menu_check_update"], KO_CHECK_LABEL,
                         "the v0.23 notes quote this Korean label")
        labels = {table[lang]["menu_check_update"] for lang in LOCALES}
        self.assertEqual(len(labels), len(LOCALES),
                         "each locale must carry its own menu_check_update label")


# ───────────────────── the closure and the menu action ──────────────────────

class RunUpdateCheckClosureTests(unittest.TestCase):
    """`_run_update_check`, executed out of run_gui's AST with stub collaborators."""

    def setUp(self):
        run_gui = _run_gui(_module_tree())
        (node,) = [n for n in run_gui.body
                   if isinstance(n, ast.FunctionDef) and n.name == STARTER]
        self.cache = {"t": 0.0, "busy": False}
        self.state = {"update": None}
        self.poll = mock.Mock(name="poll_github_update")
        self.scope = {"_upd_cache": self.cache, "state": self.state,
                      "poll_github_update": self.poll}
        self.run_check = _exec_def(node, self.scope)

    def test_returns_none_and_skips_the_poll_while_busy(self):
        self.cache["busy"] = True
        self.assertIsNone(self.run_check())
        self.poll.assert_not_called()
        self.assertTrue(self.cache["busy"], "a busy check must not be un-busied by a bystander")

    def test_returns_the_poll_status_and_clears_busy(self):
        for status in ("update", "current", "failed"):
            with self.subTest(status=status):
                self.poll.reset_mock()
                self.poll.return_value = status
                self.assertEqual(self.run_check(), status)
                self.poll.assert_called_once_with(self.state)
                self.assertFalse(self.cache["busy"])

    def test_busy_is_cleared_even_when_the_poll_raises(self):
        self.poll.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            self.run_check()
        self.assertFalse(self.cache["busy"])


class CheckUpdateActionTests(unittest.TestCase):
    """`Handler.checkUpdate_` and `Handler.showUpdateMessage_`, executed out of
    the Handler class's AST with the check, the installer, `t`, and
    `threading.Thread` all stubbed."""

    @classmethod
    def setUpClass(cls):
        run_gui = _run_gui(_module_tree())
        handler = _class_in(run_gui, "Handler")
        cls.check_update_node = _method_of(handler, "checkUpdate_")
        cls.show_message_node = _method_of(handler, "showUpdateMessage_")

    def run_action(self, status, pending=None, install_result=False):
        _SyncThread.started = []
        state = {"update": pending}
        starter = mock.Mock(name=STARTER, return_value=status)
        install = mock.Mock(name="install_github_update", return_value=install_result)
        scope = {STARTER: starter, "state": state, "install_github_update": install,
                 "t": _fake_t, "APP_VERSION": claude_pet.APP_VERSION,
                 "threading": types.SimpleNamespace(Thread=_SyncThread)}
        action = _exec_def(self.check_update_node, scope)
        proxy = _MainThreadProxy()
        action(proxy, None)
        starter.assert_called_once_with()
        self.assertEqual(_SyncThread.started, [True],
                         "the check must run on one daemon thread, not on the main thread")
        return proxy.dispatched, install

    def test_update_available_installs_the_pending_release_and_quits(self):
        pending = ("0.24", "https://example.test/ClaudePet.zip")
        dispatched, install = self.run_action("update", pending, install_result=True)
        install.assert_called_once_with(pending[1], expect_version=pending[0])
        self.assertEqual(dispatched, [(QUIT_SELECTOR, None, False)],
                         "after a successful install the app must quit so the "
                         "replacement script can relaunch it — and show no alert")

    def test_update_that_fails_to_install_reports_install_failed(self):
        pending = ("0.24", "https://example.test/ClaudePet.zip")
        dispatched, install = self.run_action("update", pending, install_result=False)
        install.assert_called_once_with(pending[1], expect_version=pending[0])
        self.assertEqual(dispatched, [(ALERT_SELECTOR, _fake_t("upd_install_failed"), False)])

    def test_update_status_without_a_pending_tuple_installs_nothing(self):
        dispatched, install = self.run_action("update", None, install_result=True)
        install.assert_not_called()
        self.assertEqual(dispatched, [(ALERT_SELECTOR, _fake_t("upd_install_failed"), False)])

    def test_current_reports_the_running_version(self):
        dispatched, install = self.run_action("current")
        install.assert_not_called()
        self.assertEqual(dispatched,
                         [(ALERT_SELECTOR, _fake_t("upd_current", v=claude_pet.APP_VERSION), False)])

    def test_busy_and_failed_report_their_own_messages(self):
        for status, key in ((None, "upd_busy"), ("failed", "upd_failed")):
            with self.subTest(status=status):
                dispatched, install = self.run_action(status)
                install.assert_not_called()
                self.assertEqual(dispatched, [(ALERT_SELECTOR, _fake_t(key), False)])

    def test_the_alert_is_never_built_on_the_worker_thread(self):
        names = {n.id for n in ast.walk(self.check_update_node) if isinstance(n, ast.Name)}
        self.assertNotIn("NSAlert", names,
                         "checkUpdate_ must hand the message to the main thread, "
                         "not run an NSAlert from its worker")
        selectors = {c.value for c in ast.walk(self.check_update_node)
                     if isinstance(c, ast.Constant) and isinstance(c.value, str)
                     and c.value.endswith(":")}
        self.assertEqual(selectors, {ALERT_SELECTOR, QUIT_SELECTOR})

    def test_show_update_message_presents_title_and_message(self):
        calls = []

        class FakeAlert:
            @classmethod
            def alloc(cls):
                return cls()

            def init(self):
                return self

            def setMessageText_(self, text):
                calls.append(("title", text))

            def setInformativeText_(self, text):
                calls.append(("body", text))

            def runModal(self):
                calls.append(("modal",))

        scope = {"NSAlert": FakeAlert, "t": _fake_t}
        show = _exec_def(self.show_message_node, scope)
        show(object(), "hello")
        self.assertEqual(calls, [("title", _fake_t("upd_title")), ("body", "hello"), ("modal",)])


# ───────────────────────────── direct to latest ─────────────────────────────

class DirectToLatestTests(unittest.TestCase):
    """A 0.20 install offered a 0.24 latest release goes straight to 0.24.

    `check_github_update` reads GitHub's `/releases/latest` — one request, one
    tag — and compares that tag against `APP_VERSION`; nothing walks the
    versions in between.  The fixture patches `APP_VERSION` to "0.20" on the
    module (the function reads the global at call time) and answers "v0.24"."""

    def setUp(self):
        _preserve_upd_cache(self)
        _FakeResponse.requested = []
        self.response = _FakeResponse(_release_payload("0.24"))
        for patcher in (mock.patch.object(claude_pet, "APP_VERSION", "0.20"),
                        mock.patch("platform.machine", return_value="arm64"),
                        mock.patch.object(claude_pet.urllib.request, "urlopen", self.response),
                        mock.patch("builtins.print")):   # `[update] asset=…` diagnostics
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_check_asks_only_for_the_latest_release_and_offers_that_tag(self):
        self.assertEqual(claude_pet.APP_VERSION, "0.20")
        self.assertEqual(
            claude_pet.check_github_update(),
            ("update", "0.24", "https://example.test/ClaudePet.zip"),
            "the offered tag must be the latest release, not the next version up")
        self.assertEqual(_FakeResponse.requested, [LATEST_URL],
                         "exactly one request, to /releases/latest — no release list, "
                         "no per-version walk")
        self.assertEqual(claude_pet._upd_cache["choice"]["tag"], "0.24")

    def test_the_same_answer_is_current_once_the_app_is_on_that_tag(self):
        # Guards the fixture: a check that always says 'update' would pass the
        # test above.
        with mock.patch.object(claude_pet, "APP_VERSION", "0.24"):
            self.assertEqual(claude_pet.check_github_update(), ("current", None, None))
        with mock.patch.object(claude_pet, "APP_VERSION", "0.25"):
            self.assertEqual(claude_pet.check_github_update(), ("current", None, None))

    def test_poll_and_menu_action_install_the_latest_tag_in_one_hop(self):
        run_gui = _run_gui(_module_tree())
        (starter_node,) = [n for n in run_gui.body
                           if isinstance(n, ast.FunctionDef) and n.name == STARTER]
        state = {"update": None}
        # The real closure, the real poll, the stubbed network.
        closure_scope = {"_upd_cache": claude_pet._upd_cache, "state": state,
                         "poll_github_update": claude_pet.poll_github_update}
        run_check = _exec_def(starter_node, closure_scope)
        install = mock.Mock(name="install_github_update", return_value=True)
        _SyncThread.started = []
        handler = _class_in(run_gui, "Handler")
        action_scope = {STARTER: run_check, "state": state, "install_github_update": install,
                        "t": _fake_t, "APP_VERSION": claude_pet.APP_VERSION,
                        "threading": types.SimpleNamespace(Thread=_SyncThread)}
        action = _exec_def(_method_of(handler, "checkUpdate_"), action_scope)
        proxy = _MainThreadProxy()
        action(proxy, None)
        self.assertEqual(state["update"], ("0.24", "https://example.test/ClaudePet.zip"))
        install.assert_called_once_with("https://example.test/ClaudePet.zip",
                                        expect_version="0.24")
        self.assertEqual(proxy.dispatched, [(QUIT_SELECTOR, None, False)])
        self.assertEqual(_FakeResponse.requested, [LATEST_URL])
        self.assertFalse(claude_pet._upd_cache["busy"])


# ───────────────────────────── behavioural gate ─────────────────────────────

class UpdateCheckScheduleBehaviourTests(unittest.TestCase):
    """Runs the extracted launch stamp and worker gate against a fake clock."""

    def setUp(self):
        _preserve_upd_cache(self)
        self.tree = _module_tree()
        self.run_gui = _run_gui(self.tree)
        self.clock = {"now": LAUNCH}
        self.state = {"update": None}
        # The namespace the extracted code runs in: the worker's real
        # collaborators, with `time` replaced by the fake clock.
        self.namespace = {
            "state": self.state,
            "time": types.SimpleNamespace(time=lambda: self.clock["now"]),
            "_upd_cache": claude_pet._upd_cache,
            "UPDATE_CHECK_SEC": claude_pet.UPDATE_CHECK_SEC,
        }

    def launch(self):
        """Run whatever launch stamp run_gui's top level has. If it has
        none, nothing runs and `_upd_cache['t']` stays 0.0 — the rival."""
        for index in _launch_stamp_indices(self.run_gui):
            exec(_compile_statement(self.run_gui.body[index]), self.namespace)

    def due(self):
        gates = _worker_gates(self.run_gui)
        self.assertEqual(len(gates), 1, "expected exactly one worker gate")
        return bool(eval(_compile_expression(gates[0].test), self.namespace))

    def at(self, offset):
        self.clock["now"] = LAUNCH + offset

    def test_first_check_is_one_interval_after_launch_then_periodic(self):
        self.launch()
        polls = mock.Mock(return_value=("current", None, None))
        with mock.patch.object(claude_pet, "check_github_update", polls):
            for offset in (0, 30, 3599, 3600):
                self.at(offset)
                self.assertFalse(
                    self.due(),
                    f"an update check is due at launch+{offset}s; "
                    f"_upd_cache['t']={claude_pet._upd_cache['t']!r}")
            self.assertEqual(polls.call_count, 0)

            self.at(3601)
            self.assertTrue(self.due(), "no update check is due at launch+3601s")
            # What _run_update_check does once the gate opens.
            self.assertEqual(
                claude_pet.poll_github_update(self.state, now=self.clock["now"]),
                "current")
            self.assertEqual(polls.call_count, 1)
            self.assertEqual(claude_pet._upd_cache["t"], LAUNCH + 3601)
            self.assertIsNone(self.state["update"])

            # Periodic: the next check is one interval after the last one,
            # not on the next refresh.
            self.at(3601 + 30)
            self.assertFalse(self.due(), "re-checked on the very next refresh")
            self.at(3601 + 3600)
            self.assertFalse(self.due(), "re-checked at exactly one interval")
            self.at(3601 + 3601)
            self.assertTrue(self.due(), "second check never became due")
            claude_pet.poll_github_update(self.state, now=self.clock["now"])
            self.assertEqual(polls.call_count, 2)

    def test_a_pending_update_stops_further_checks(self):
        self.launch()
        url = "https://example.invalid/ClaudePet.zip"
        with mock.patch.object(claude_pet, "check_github_update",
                               return_value=("update", "99.0", url)):
            self.at(3601)
            self.assertTrue(self.due())
            self.assertEqual(
                claude_pet.poll_github_update(self.state, now=self.clock["now"]),
                "update")
        self.assertEqual(self.state["update"], ("99.0", url))
        self.at(3601 + 100_000)
        self.assertFalse(self.due(), "an update is pending; nothing to re-check")


if __name__ == "__main__":
    unittest.main()
