"""Independent quiet-companion gates.

Owner: Verifier /root/verifier. Default unit tests use synthetic geometry/time
and compile only approved pure definitions or isolated GUI methods. The opt-in
native smoke imports the source app inside its explicit I/O-isolated fixture.

Rivals: absent/unwired API; move before rest; follow every cursor update;
uncapped delayed tick; disabled movement; stale pre-drag origin; wander with
no pause. Geometry/suppression integration gates are added after the contract
has been acknowledged, and any missing red evidence remains explicitly open.

Re-pinned for the staged v0.24 summary-pill unification (Verifier verifier-v024,
2026-09-12): ``roam_summary`` rows are ``(label, pct, spiking, reset_text)`` and exact
keeps three gauge rows; ``cost`` is ``(today, month | None, budget | None)``; ``full``
and ``summary`` are one text-sized pill and the ``full`` window is the union crop, not
the whole logical window. Round 2 (after the Reviewer's B1): ``RoamDisplay.toggle``
during the latch *dismisses* the pill for that visit and returns the preference
unchanged (``dismissed`` replaces round 1's clear-and-flip; there is no ``expanded``
state); the adapter keeps every exact row except credits and memoises its text per
input and 5-second window. Round 3: the colour roles are swapped — the label run
carries the remaining-amount kind and the value run the source kind; only the cost
assertion in the adapter test changes here. Evidence:
docs-design/summary-unify-verification-20260912.md.
"""
from __future__ import annotations

import ast
import collections
import copy
import math
import random
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "claude_pet.py"


def pure_api(test, required=None):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    definitions = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    definitions[target.id] = node
    required = set(required or {"ROAM_DEFAULTS", "RoamOut", "Roamer"})
    test.assertFalse(required - definitions.keys(),
                     "quiet companion API missing: " + ", ".join(sorted(required - definitions.keys())))
    selected = set(required)
    pending = list(required)
    while pending:
        node = definitions[pending.pop()]
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                name = child.id
                if name in definitions and name not in selected:
                    selected.add(name)
                    pending.append(name)
    nodes = [node for node in tree.body if any(definitions[name] is node for name in selected)]
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import) and all(alias.name in ("math", "random", "collections") for alias in node.names):
            imports.append(node)
        elif isinstance(node, ast.ImportFrom) and node.module in ("math", "random", "collections"):
            imports.append(node)
    nodes = imports + nodes
    scope = {"__name__": "_quiet_companion_pure_test", "math": math,
             "random": random, "collections": collections,
             "namedtuple": collections.namedtuple}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
    return scope


class MinimumRng:
    def uniform(self, low, high):
        return low


class CompanionApiTests(unittest.TestCase):
    def test_public_pure_motion_contract_exists(self):
        api = pure_api(self)
        self.assertEqual(api["RoamOut"]._fields,
                         ("pos", "anim", "moved", "away", "phase", "effect"))
        r = api["Roamer"]((400.0, 300.0), 0.0, rng=MinimumRng())
        self.assertEqual(tuple(r.pos), (400.0, 300.0))
        self.assertEqual(tuple(r.home), (400.0, 300.0))
        self.assertEqual(r.phase, "rest")
        self.assertTrue(callable(r.step))
        self.assertTrue(callable(r.set_home))
        self.assertTrue(callable(r.release))

    def test_initial_rest_does_not_move_for_early_activity(self):
        api = pure_api(self)
        r = api["Roamer"]((400.0, 300.0), 0.0, rng=MinimumRng(),
                          cfg={"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 10.0, "rest_max_s": 10.0})
        for now in (0.0, 0.25, 1.0, 3.0, 9.99):
            with self.subTest(now=now):
                out = r.step(now, (1000.0, 300.0), (0.0, 0.0, 2000.0, 1500.0), activity=True)
                self.assertEqual(tuple(out.pos), (400.0, 300.0))
                self.assertFalse(out.moved)
                self.assertEqual(out.phase, "rest")

    def test_disabled_start_remains_at_current_position(self):
        api = pure_api(self)
        r = api["Roamer"]((400.0, 300.0), 0.0, rng=MinimumRng())
        for now in (0.0, 1.0, 50.0, 1000.0):
            out = r.step(now, (1000.0, 300.0), (0.0, 0.0, 2000.0, 1500.0),
                         enabled=False, activity=True)
            self.assertEqual(tuple(out.pos), (400.0, 300.0))
            self.assertFalse(out.moved)

    def test_set_home_replaces_both_old_motion_origin_and_manual_home(self):
        api = pure_api(self)
        r = api["Roamer"]((400.0, 300.0), 0.0, rng=MinimumRng())
        r.set_home((270.0, 710.0), 20.0)
        self.assertEqual(tuple(r.pos), (270.0, 710.0))
        self.assertEqual(tuple(r.home), (270.0, 710.0))
        out = r.step(20.05, (1000.0, 300.0), (0.0, 0.0, 2000.0, 1500.0))
        self.assertEqual(tuple(out.pos), (270.0, 710.0))
        self.assertFalse(out.moved)


class CompanionMotionTests(unittest.TestCase):
    bounds = (0.0, 0.0, 2000.0, 1500.0)
    home = (400.0, 300.0)
    cursor = (1000.0, 300.0)

    def make(self, home=None, radius=0.0, **overrides):
        api = pure_api(self)
        cfg = {"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 10.0, "rest_max_s": 10.0,
               "approach_cooldown_s": 0.0, "wander_cooldown_s": 100000.0,
               "wander_enabled": False,
               "walk_speed": 40.0, "approach_stop": 150.0,
               "approach_max": 360.0, "look_s": 2.0,
               "max_dt_s": 0.25, "gap_s": 5.0}
        cfg.update(overrides)
        return api["Roamer"](home or self.home, 0.0, rng=MinimumRng(),
                             cfg=cfg, radius=radius)

    def depart(self, **overrides):
        r = self.make(**overrides)
        for tick in range(10):
            r.step(float(tick), self.cursor, self.bounds)
        out = r.step(10.0, self.cursor, self.bounds, activity=True)
        self.assertEqual(out.phase, "out", "eligible activity did not start approach")
        self.assertEqual(r.kind, "approach")
        return r, 10.0

    def test_eligible_activity_starts_approach_after_the_rest(self):
        r, now = self.depart()
        before = tuple(r.pos)
        out = r.step(now + 0.1, self.cursor, self.bounds)
        self.assertAlmostEqual(out.pos[0] - before[0], 4.0, places=6)
        self.assertAlmostEqual(out.pos[1], before[1], places=6)
        self.assertTrue(out.moved)
        self.assertEqual(out.anim, "running-right")

    def test_fixed_destination_does_not_chase_new_cursor_locations(self):
        r, now = self.depart()
        other = copy.deepcopy(r)
        for tick in range(1, 9):
            t = now + tick * 0.1
            a = r.step(t, self.cursor, self.bounds)
            b = other.step(t, (1100.0, 900.0 + tick), self.bounds, activity=True)
            self.assertEqual(tuple(a.pos), tuple(b.pos))
            self.assertEqual(a.phase, b.phase)

    def test_late_tick_caps_distance_without_using_full_elapsed_time(self):
        r, now = self.depart()
        before = tuple(r.pos)
        out = r.step(now + 1.0, self.cursor, self.bounds)
        self.assertAlmostEqual(math.dist(before, out.pos), 10.0, places=6)

    def test_sleep_gap_freezes_in_place_and_discards_old_journey(self):
        r, now = self.depart()
        r.step(now + 0.25, self.cursor, self.bounds)
        before = tuple(r.pos)
        out = r.step(now + 100.0, self.cursor, self.bounds, activity=True)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)
        after = r.step(now + 100.1, self.cursor, self.bounds, activity=True)
        self.assertEqual(tuple(after.pos), before)

    def test_each_interaction_freezes_an_inflight_approach_and_resumes_quietly(self):
        for flag, value in (("enabled", False), ("dragging", True),
                            ("blocked", True), ("busy", True)):
            with self.subTest(flag=flag):
                r, now = self.depart()
                r.step(now + 0.25, self.cursor, self.bounds)
                before = tuple(r.pos)
                out = r.step(now + 0.5, self.cursor, self.bounds,
                             activity=True, **{flag: value})
                self.assertEqual(tuple(out.pos), before)
                self.assertFalse(out.moved)
                out = r.step(now + 0.6, self.cursor, self.bounds, activity=True)
                self.assertEqual(tuple(out.pos), before)
                self.assertFalse(out.moved)

    def test_long_interaction_still_gets_full_fresh_rest_after_release(self):
        for flag, value in (("enabled", False), ("dragging", True),
                            ("blocked", True), ("busy", True)):
            with self.subTest(flag=flag):
                r, now = self.depart()
                before = tuple(r.pos)
                for half_tick in range(1, 51):
                    r.step(now + half_tick * 0.5, self.cursor, self.bounds,
                           activity=True, **{flag: value})
                for quarter_tick in range(1, 40):
                    out = r.step(35.0 + quarter_tick * 0.25, self.cursor,
                                 self.bounds, activity=True)
                    self.assertEqual(tuple(out.pos), before,
                                     "long interaction shortened the promised fresh rest")
                    self.assertFalse(out.moved)

    def test_disabled_after_arrival_does_not_snap_to_manual_home(self):
        r, now = self.depart()
        for tick in range(1, 200):
            now = 10.0 + tick * 0.25
            out = r.step(now, self.cursor, self.bounds)
            if out.phase == "rest" and r.settled:
                break
        self.assertEqual(out.phase, "rest", "arrival never settled at its destination")
        before = tuple(r.pos)
        self.assertGreater(math.dist(before, r.home), 60.0)
        out = r.step(now + 0.25, self.cursor, self.bounds, enabled=False)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)

    def test_approach_max_and_watch_hold_are_geometrically_bounded(self):
        r, now = self.depart()
        for tick in range(1, 200):
            now = 10.0 + tick * 0.25
            out = r.step(now, self.cursor, self.bounds)
            self.assertLessEqual(math.dist(self.home, out.pos), 360.0 + 1e-6)
            if out.phase == "look":
                break
        self.assertEqual(out.phase, "look", "approach never reached watch")
        self.assertAlmostEqual(out.pos[0], 760.0, delta=2.0)
        self.assertAlmostEqual(out.pos[1], 300.0, places=6)
        before = tuple(out.pos)
        for delta in (0.1, 0.5, 1.0, 1.9):
            watched = r.step(now + delta, self.cursor, self.bounds, activity=True)
            self.assertEqual(tuple(watched.pos), before)
            self.assertEqual(watched.phase, "look")
            self.assertFalse(watched.moved)

    def test_click_without_drag_preserves_manual_home_and_current_position(self):
        r, now = self.depart()
        r.step(now + 0.25, self.cursor, self.bounds)
        before = tuple(r.pos)
        self.assertNotEqual(before, self.home)
        r.release(now + 0.3, before, False)
        self.assertEqual(tuple(r.home), self.home)
        self.assertEqual(tuple(r.pos), before)
        out = r.step(now + 0.35, self.cursor, self.bounds, activity=True)
        self.assertEqual(tuple(out.pos), before)

    def test_real_drag_establishes_a_new_home_and_cancels_old_target(self):
        r, now = self.depart()
        r.release(now + 0.3, (920.0, 720.0), True)
        self.assertEqual(tuple(r.home), (920.0, 720.0))
        self.assertEqual(tuple(r.pos), (920.0, 720.0))
        out = r.step(now + 0.35, self.cursor, self.bounds, activity=True)
        self.assertEqual(tuple(out.pos), (920.0, 720.0))

    def test_cursor_on_outbound_segment_cancels_instead_of_crossing_it(self):
        r, now = self.depart(radius=50.0)
        before = tuple(r.pos)
        out = r.step(now + 0.25, (before[0] + 5.0, before[1]), self.bounds)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)

    def test_pointer_in_interior_of_full_leg_stops_before_next_step(self):
        r, now = self.depart()
        before = tuple(r.pos)
        pointer = ((before[0] + 760.0) / 2.0, 300.0)
        self.assertGreater(math.dist(before, pointer), 150.0)
        self.assertGreater(math.dist((760.0, 300.0), pointer), 150.0)
        out = r.step(now + 0.25, pointer, self.bounds)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)

    def test_cursor_on_leftward_outbound_segment_also_cancels(self):
        r = self.make(home=(1400.0, 300.0), radius=50.0)
        for now in range(10):
            r.step(now, self.cursor, self.bounds)
        now = 10.0
        out = r.step(now, self.cursor, self.bounds, activity=True)
        self.assertEqual(out.phase, "out")
        self.assertEqual(out.anim, "running-left")
        before = tuple(r.pos)
        out = r.step(now + 0.25, (before[0] - 5.0, before[1]), self.bounds)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)

    def test_nonzero_negative_monitor_origin_contains_every_position(self):
        r = self.make(home=(-450.0, 300.0))
        bounds = (-1700.0, 100.0, -300.0, 1100.0)
        cursor = (300.0, 300.0)
        for tick in range(1, 161):
            out = r.step(tick * 0.25, cursor, bounds, activity=tick >= 40)
            self.assertGreaterEqual(out.pos[0], -1700.0)
            self.assertLessEqual(out.pos[0], -300.0)
            self.assertGreaterEqual(out.pos[1], 100.0)
            self.assertLessEqual(out.pos[1], 1100.0)

    def test_activity_bursts_respect_approach_cooldown_without_starving_future_visits(self):
        r = self.make(approach_cooldown_s=180.0)
        departures = []
        previous = r.phase
        for tick in range(0, 1681):
            now = tick * 0.25
            out = r.step(now, self.cursor, self.bounds, activity=(tick % 4 == 0))
            if out.phase in ("out", "look") and previous == "rest" and r.kind == "approach":
                departures.append(now)
            previous = out.phase
        self.assertGreaterEqual(len(departures), 2,
                                "continuous input must not perpetually push back eligibility")
        for previous, current in zip(departures, departures[1:]):
            self.assertGreaterEqual(current - previous, 180.0)

    def test_wander_uses_monitor_bounds_pauses_and_respects_own_cooldown(self):
        r = self.make(wander_cooldown_s=300.0, wander_enabled=True)
        class OppositeDestinations:
            def __init__(self):
                self.i = 0
            def uniform(self, low, high):
                if low == high:
                    return low
                fraction = (0.8, 0.7, 0.2, 0.25)[self.i % 4]
                self.i += 1
                return low + fraction * (high - low)
        r.rng = OppositeDestinations()
        departures = []
        saw_pause = False
        max_distance = 0.0
        previous = r.phase
        for tick in range(0, 1441):
            now = tick * 0.25
            out = r.step(now, None, self.bounds)
            self.assertTrue(0 <= out.pos[0] <= 2000 and 0 <= out.pos[1] <= 1500)
            self.assertEqual(tuple(r.home), self.home)
            self.assertNotEqual(out.phase, "home")
            max_distance = max(max_distance, math.dist(self.home, out.pos))
            if out.phase == "out" and previous != "out" and r.kind == "wander":
                departures.append(now)
            if out.phase == "look":
                self.assertIsNone(out.anim)
                saw_pause = True
            previous = out.phase
        self.assertTrue(saw_pause, "wander never had its quiet pause")
        self.assertGreater(max_distance, 360.0)
        self.assertGreaterEqual(len(departures), 2)
        for first, second in zip(departures, departures[1:]):
            self.assertGreaterEqual(second - first, 300.0)

    def test_hold_on_every_trip_phase_freezes_outbound_and_look(self):
        for wanted in ("out", "look"):
            for flag, value in (("enabled", False), ("dragging", True),
                                ("blocked", True), ("busy", True)):
                with self.subTest(phase=wanted, flag=flag):
                    r, now = self.depart()
                    for tick in range(1, 200):
                        now = 10.0 + tick * 0.25
                        out = r.step(now, self.cursor, self.bounds)
                        if out.phase == wanted:
                            break
                    self.assertEqual(out.phase, wanted)
                    before = tuple(r.pos)
                    out = r.step(now + 0.25, self.cursor, self.bounds, **{flag: value})
                    self.assertEqual(tuple(out.pos), before)
                    self.assertFalse(out.moved)
                    after = r.step(now + 0.5, self.cursor, self.bounds, activity=True)
                    self.assertEqual(tuple(after.pos), before)
                    self.assertFalse(after.moved)

    def test_invalid_bounds_do_not_bypass_suppression_or_restore_stale_target(self):
        for flag, value in (("enabled", False), ("dragging", True),
                            ("blocked", True), ("busy", True)):
            with self.subTest(flag=flag):
                r, now = self.depart()
                before = tuple(r.pos)
                out = r.step(now + 0.25, self.cursor, (500.0, 600.0, 300.0, 200.0),
                             **{flag: value})
                self.assertEqual(tuple(out.pos), before)
                self.assertEqual(out.phase, "rest", "invalid bounds skipped cancellation")
                self.assertIsNone(out.anim)
                recovered = r.step(now + 0.5, self.cursor, self.bounds, activity=True)
                self.assertEqual(tuple(recovered.pos), before)
                self.assertFalse(recovered.moved)

    def test_invalid_center_bounds_freeze_without_reversed_clamp_jump(self):
        r, now = self.depart()
        before = tuple(r.pos)
        out = r.step(now + 0.25, self.cursor, (500.0, 600.0, 300.0, 200.0), activity=True)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)


def gui_method(test, class_name, method_name, scope):
    """Execute the actual method body with synthetic window/state collaborators."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    gui = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_gui")
    cls = next(node for node in gui.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = copy.deepcopy(next(node for node in cls.body
                                if isinstance(node, ast.FunctionDef) and node.name == method_name))
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), "exec"), scope)
    return scope[method_name]


def gui_functions(test, names, scope):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    gui = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_gui")
    definitions = {node.name: node for node in gui.body if isinstance(node, ast.FunctionDef)}
    test.assertFalse(set(names) - definitions.keys(), "requested GUI adapter is missing")
    # All sibling helpers stay in one scope, just as in the application's closure.
    selected = set(names)
    pending = list(names)
    while pending:
        for node in ast.walk(definitions[pending.pop()]):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in definitions and node.id not in selected and node.id not in scope:
                    selected.add(node.id)
                    pending.append(node.id)
    nodes = [copy.deepcopy(node) for node in gui.body
             if isinstance(node, ast.FunctionDef) and node.name in selected]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
    return scope


def claude_pet_const(name):
    """One module-level constant, read from the source without importing the app.

    This module deliberately never imports claude_pet — it drives AST-extracted code in
    hand-built scopes. So a constant the extracted code reads has to be fetched the same
    way, not hardcoded here: a literal copy is the restatement defect that has already
    cost this release twice.
    """
    import ast as _ast
    tree = _ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and any(
                isinstance(x, _ast.Name) and x.id == name for x in node.targets):
            return _ast.literal_eval(
                _ast.Expression(body=node.value)) if isinstance(
                    node.value, _ast.Constant) else eval(  # noqa: S307
                        compile(_ast.Expression(body=node.value), "<const>", "eval"),
                        {"SUMMARY_LINE_H": claude_pet_const("SUMMARY_LINE_H")})
    raise AssertionError(f"claude_pet.py has no module-level {name}")


def fake_rect(x, y, width, height):
    return SimpleNamespace(origin=SimpleNamespace(x=float(x), y=float(y)),
                           size=SimpleNamespace(width=float(width), height=float(height)))


class CompanionPresentationTests(unittest.TestCase):
    """User-derived presentation gates, authored before the compact implementation."""
    def display(self):
        return pure_api(self, {"RoamDisplay"})["RoamDisplay"]()

    def test_departure_folds_even_before_any_displacement(self):
        for preference in (False, True):
            for phase, kind, away in (("out", "approach", False),
                                      ("out", "wander", False)):
                with self.subTest(preference=preference, phase=phase, kind=kind):
                    d = self.display()
                    d.note(phase, kind, away)
                    self.assertEqual(d.mode(phase, preference), "folded")

    def test_approach_summary_toggle_dismisses_the_visit_and_keeps_the_preference(self):
        """One pill: a toggle during the arrival latch folds the visiting pill for the
        rest of that visit and leaves the stored preference alone — the visit ends the
        way it began. Rivals: the round-1 toggle (cleared the latch and returned
        ``not preference``, so a folded user ended every visit with the pill open, and
        the next tick's re-latch hid the click); the v0.23 'expanded' toggle (preference
        unchanged but the full panel shown); a re-latch that clears the dismissal."""
        for preference in (False, True):
            for away in (False, True):
                with self.subTest(preference=preference, away=away):
                    d = self.display()
                    d.note("look", "approach", away)
                    self.assertEqual(d.mode("look", preference), "summary")
                    kept = d.toggle(preference)
                    self.assertEqual(kept, preference)
                    self.assertEqual(d.mode("look", kept), "folded")
                    d.note("look", "approach", away)            # every tick re-notes
                    self.assertEqual(d.mode("look", kept), "folded")
                    self.assertEqual(d.toggle(kept), kept)
                    self.assertEqual(d.mode("look", kept), "summary")
                    d.note("rest", None, True, settled=True)
                    self.assertEqual(d.mode("rest", kept),
                                     "full" if kept else "folded")
                    d.note("look", "approach", away)
                    self.assertEqual(d.mode("look", kept), "summary",
                                     "the next visit must arrive undismissed")

    def test_wander_pause_stays_folded_and_settlement_restores_manual_choice(self):
        for preference in (False, True):
            d = self.display()
            d.note("out", "wander", False)
            d.note("look", "wander", True)
            self.assertEqual(d.mode("look", preference), "folded")
            d.note("rest", None, True, settled=True)
            self.assertEqual(d.mode("rest", preference),
                             "full" if preference else "folded")

    def test_hover_stop_away_keeps_summary_until_the_user_dismisses_it(self):
        d = self.display()
        d.note("look", "approach", True)
        d.note("rest", None, True, settled=False)  # ordinary hover, not natural completion
        self.assertEqual(d.mode("rest", False), "summary")
        self.assertFalse(d.toggle(False), "dismissing the visiting pill is not a preference flip")
        self.assertEqual(d.mode("rest", False), "folded")
        d.note("rest", None, True, settled=False)  # still hovering
        self.assertEqual(d.mode("rest", False), "folded")
        self.assertFalse(d.toggle(False))
        self.assertEqual(d.mode("rest", False), "summary")

    def test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry(self):
        api = pure_api(self, {"RoamDisplay", "Roamer"})
        for hover_stop in (False, True):
            with self.subTest(hover_stop=hover_stop):
                d = api["RoamDisplay"]()
                r = api["Roamer"]((400, 300), 0, rng=MinimumRng(),
                                  cfg={"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 0, "rest_max_s": 0,
                                       "wander_enabled": False, "look_s": 6})
                out = r.step(1, (450, 300), (0, 0, 1200, 900), activity=True)
                self.assertEqual(out.phase, "look")
                self.assertFalse(out.away)
                d.note(out.phase, r.kind, out.away, settled=r.settled)
                self.assertEqual(d.mode(out.phase, True), "summary")
                times = (1.25,) if hover_stop else (2, 3, 4, 5, 6, 7)
                for now in times:
                    out = r.step(now, (450, 300), (0, 0, 1200, 900),
                                 blocked=hover_stop)
                    d.note(out.phase, r.kind, out.away, settled=r.settled)
                self.assertEqual(out.phase, "rest")
                self.assertEqual(d.mode(out.phase, True),
                                 "summary" if hover_stop else "full",
                                 "in-place hover cleared the arrival summary before expansion")

    def test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion(self):
        api = pure_api(self, {"RoamDisplay", "Roamer"})
        r = api["Roamer"]((400, 300), 0, rng=MinimumRng(),
                          cfg={"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 0, "rest_max_s": 0, "wander_enabled": False})
        self.assertTrue(hasattr(r, "settled"), "motion completion cause is not exposed")
        self.assertTrue(r.settled)
        d = api["RoamDisplay"]()
        out = r.step(1, (450, 300), (0, 0, 1200, 900), activity=True)
        d.note(out.phase, r.kind, out.away, settled=r.settled)
        out = r.step(1.1, (450, 300), (0, 0, 1200, 900), dragging=True)
        self.assertFalse(r.settled)
        d.note(out.phase, r.kind, out.away, settled=r.settled)
        r.release(1.2, r.pos, False)
        self.assertFalse(r.settled, "ordinary click was confused with natural arrival completion")
        d.note(r.phase, r.kind, r.away, settled=r.settled)
        self.assertEqual(d.mode(r.phase, False), "summary")
        self.assertFalse(d.toggle(False), "a click on the visiting pill keeps the folded preference")
        self.assertEqual(d.mode(r.phase, False), "folded")
        r.set_home((420, 360), 1.3)
        self.assertTrue(r.settled)
        d.reset()
        self.assertEqual(d.mode(r.phase, False), "folded")
        self.assertTrue(d.toggle(False), "after the visit the toggle is the plain flip again")

    def test_explicit_interruption_or_disable_clears_summary_and_expansion(self):
        for flags in ({"interrupted": True}, {"enabled": False}):
            for preference in (False, True):
                with self.subTest(flags=flags, preference=preference):
                    d = self.display()
                    d.note("look", "approach", True)
                    d.toggle(preference)
                    d.note("rest", None, True, **flags)
                    self.assertEqual(d.mode("rest", preference),
                                     "full" if preference else "folded")
                    self.assertEqual(d.toggle(preference), not preference)

    def test_interruption_has_priority_over_same_call_arrival(self):
        for flags in ({"interrupted": True}, {"enabled": False}):
            d = self.display()
            d.note("look", "approach", True, **flags)
            d.note("rest", None, True)
            self.assertEqual(d.mode("rest", True), "full")
            self.assertTrue(d.toggle(False))

    def test_manual_toggle_and_reset_restore_ordinary_preference_behavior(self):
        d = self.display()
        self.assertTrue(d.toggle(False))
        self.assertFalse(d.toggle(True))
        d.note("look", "approach", True)
        d.toggle(False)
        d.reset()
        self.assertEqual(d.mode("rest", True), "full")
        self.assertEqual(d.mode("rest", False), "folded")

    def summary(self, **overrides):
        fn = pure_api(self, {"roam_summary"})["roam_summary"]
        args = dict(mode="sub", oauth=None, stats=None, onboard=None,
                    cost_today=None, has_admin_key=False)
        args.update(overrides)
        return fn(**args)

    def test_summary_unknown_zero_and_api_mode_are_distinct(self):
        self.assertEqual(self.summary(), ("status", "scanning"))
        self.assertEqual(self.summary(mode="api"), ("status", "need_admin_key"))
        self.assertEqual(self.summary(mode="api", has_admin_key=True),
                         ("status", "loading"))
        self.assertEqual(self.summary(mode="api", has_admin_key=True, cost_today=0),
                         ("cost", (0.0, None, None)))
        self.assertEqual(self.summary(mode="api", has_admin_key=True, cost_today=12.375,
                                      oauth=[("Weekly", 87.0, None)]),
                         ("cost", (12.375, None, None)))
        self.assertEqual(self.summary(mode="api", has_admin_key=True, cost_today=12.375,
                                      cost_month=27.5, cost_budget=50),
                         ("cost", (12.375, 27.5, 50.0)))

    def test_summary_keeps_first_three_source_labels_and_values_in_order(self):
        rows = [("Current session", 17.25, None), ("週間", 63.5, None),
                ("Fable", 91.0, None), ("Credits", 3.0, None)]
        self.assertEqual(self.summary(oauth=rows),
                         ("exact", [("Current session", 17.25, False, None),
                                    ("週間", 63.5, False, None),
                                    ("Fable", 91.0, False, None)]))

    def test_summary_onboarding_and_estimates_preserve_data_meaning(self):
        self.assertEqual(self.summary(onboard="install"), ("status", "onb_install"))
        self.assertEqual(self.summary(onboard="login"), ("status", "onb_login"))
        self.assertEqual(self.summary(stats={"session": {"pct": 0.0},
                                             "weekly": {"pct": 67.5}}),
                         ("estimate", [("session", 0.0, False, None),
                                       ("weekly", 67.5, False, None)]))

    def test_summary_invalid_values_are_not_reported_as_zero(self):
        for invalid in (None, True, False, -1.0, float("nan"), float("inf"), "32"):
            with self.subTest(invalid=repr(invalid)):
                self.assertEqual(self.summary(mode="api", has_admin_key=True,
                                              cost_today=invalid), ("status", "loading"))
                self.assertEqual(self.summary(stats={"session": {"pct": invalid},
                                                     "weekly": {"pct": 23.75}}),
                                 ("estimate", [("weekly", 23.75, False, None)]))
                self.assertEqual(self.summary(oauth=[("Session", invalid, None)],
                                              stats={"session": {"pct": 99.0}}),
                                 ("status", "scanning"))

    def test_exact_summary_filters_only_first_three_rows_without_replacement(self):
        rows = [("Session", float("nan"), None), ("週間", 41.0, None),
                ("Fable", 93.0, None), ("Credits", 7.0, None)]
        self.assertEqual(self.summary(oauth=rows),
                         ("exact", [("週間", 41.0, False, None), ("Fable", 93.0, False, None)]))

    def test_server_label_matching_translation_key_remains_an_exact_label(self):
        self.assertEqual(self.summary(oauth=[("session", 18.25, None)]),
                         ("exact", [("session", 18.25, False, None)]))
        self.assertEqual(self.summary(stats={"session": {"pct": 18.25}}),
                         ("estimate", [("session", 18.25, False, None)]))


class CompanionCropGeometryTests(unittest.TestCase):
    """Asymmetric negative-screen fixtures derived from anchor preservation."""
    def api(self):
        # PILL_W and SUMMARY_EDGE are requested so the geometry assertions can be
        # *derived* from the same constants production uses rather than written
        # down as numbers — a pinned 300 here is what previously agreed with the
        # truncation while another module disagreed, both green.
        return pure_api(self, {"roam_frame", "roam_logical_center", "roam_pill_rect",
                               "PILL_W", "SUMMARY_EDGE"})

    def test_all_orientations_preserve_sprite_anchor_and_logical_home(self):
        api = self.api()
        # Values derive from A=(-980,860), sprite80x60, full300x220, scale.5.
        fixtures = [
            (False, False, (-836.0, 752.0),
             (4, 0, 112, 64), (-982, 798), (2, 0, 160, 98), (-984, 764)),
            (True, False, (-1044.0, 752.0),
             (184, 0, 112, 64), (-1010, 798), (138, 0, 160, 98), (-1056, 764)),
            (False, True, (-836.0, 908.0),
             (4, 156, 112, 64), (-982, 798), (2, 124, 160, 96), (-984, 798)),
            (True, True, (-1044.0, 908.0),
             (184, 156, 112, 64), (-1010, 798), (138, 124, 160, 96), (-1056, 798)),
        ]
        for right, bottom, center, fold_crop, fold_origin, sum_crop, sum_origin in fixtures:
            # full and summary are the same pill since v0.24, so both take the summary
            # crop; the old full crop was the whole (0, 0, 300, 220) window.
            for mode, expected_crop, expected_origin in (
                    ("full", sum_crop, sum_origin),
                    ("folded", fold_crop, fold_origin),
                    ("summary", sum_crop, sum_origin)):
                with self.subTest(right=right, bottom=bottom, mode=mode):
                    f = api["roam_frame"](center, mode, right, bottom,
                                           300, 220, 80, 60, 152, 0.5, text_w=130)
                    self.assertEqual(tuple(f["crop"]), expected_crop)
                    self.assertEqual(tuple(f["origin"]), expected_origin)
                    self.assertEqual(tuple(f["size"]), expected_crop[2:])
                    sx, sy, sw, sh = f["sprite"]
                    self.assertEqual((sw, sh), (80, 60))
                    self.assertEqual((f["origin"][0] + sx,
                                      f["origin"][1] + f["size"][1] - sy), (-980, 860))
                    self.assertEqual(tuple(api["roam_logical_center"](
                        f["origin"], f["size"], f["crop"], (300, 220))), center)
                    cx, cy, cw, ch = f["crop"]
                    self.assertGreaterEqual(cx, 0)
                    self.assertGreaterEqual(cy, 0)
                    self.assertLessEqual(cx + cw, 300)
                    self.assertLessEqual(cy + ch, 220)
                    if mode == "folded":
                        self.assertIsNone(f["pill"])
                    else:
                        self.assertIsNotNone(f["pill"])

    def test_native_compact_size_includes_button_but_not_full_panel_hitbox(self):
        api = self.api()
        f = api["roam_frame"]((650, 430), "folded", False, False,
                               300, 220, 80, 60, 152, 0.5)
        self.assertEqual(tuple(f["size"]), (112, 64))
        self.assertEqual(tuple(f["sprite"]), (2, 2, 80, 60))
        self.assertEqual(tuple(f["button"]), (84, 15, 26, 26))

    def test_summary_text_width_is_bounded_and_origin_uses_same_side(self):
        api = self.api()
        for mode in ("summary", "full"):
            for right, expected_x in ((False, 4), (True, 140)):
                for bottom, expected_y in ((False, 66), (True, 126)):
                    with self.subTest(mode=mode, right=right, bottom=bottom):
                        self.assertEqual(tuple(api["roam_pill_rect"](
                            mode, right, bottom, 300, 80, 60, 152, text_w=130)),
                            (expected_x, expected_y, 156, 30))
        # The app's logical window is PILL_W + 8 wide (geom()), so the widest pill keeps
        # its SUMMARY_EDGE margin on the pet's side. The width is derived from that
        # window, **not written down as 300**: pinning the number here is what made this
        # assertion quietly defend the truncation. It agreed with
        # tests/test_summary_pill.py that the ceiling was fine while
        # tests/test_summary_layout.py was folding against the screen — two green tests
        # feeding the same function different worlds and contradicting each other.
        #
        # Whether this ceiling is WIDE ENOUGH is not asked here and must not be: that is
        # FoldBudgetMatchesTheActualPillTests' question, and it answers it by calling
        # geom() and _pill_text_budget() rather than by restating either.
        # A window width supplied **as a test input**, not copied from production. The
        # earlier `PILL_W + 8` here recited `geom()`'s formula, and under the adaptive
        # width that formula no longer yields a fixed answer — so the assertion pinned a
        # snapshot taken before the adapter measures anything, and called it the ceiling.
        #
        # What this test is for is *placement*: whatever the window, the widest pill keeps
        # its SUMMARY_EDGE margin on the pet's side and is bounded by that window. Whether
        # production's window is large enough is a property of `geom()` and belongs to
        # tests/test_summary_layout.py :: FoldBudgetMatchesTheActualPillTests, which reads
        # both ends from production instead of restating either.
        edge = api["SUMMARY_EDGE"]
        for window_w in (308, 420, 600):
            with self.subTest(window_w=window_w):
                long_pill = api["roam_pill_rect"]("summary", True, False,
                                                   window_w, 80, 60, 152, text_w=9000)
                self.assertEqual(tuple(long_pill),
                                 (edge, 66, window_w - 2 * edge, 30),
                                 "the widest pill must fill its window minus both margins")
        self.assertIsNone(api["roam_pill_rect"]("folded", False, True,
                                               300, 80, 60, 152))

    def test_uncropped_window_logical_center_remains_native_center(self):
        api = self.api()
        self.assertEqual(tuple(api["roam_logical_center"]((-1200, 360), (300, 220),
                                                          None, (300, 220))),
                         (-1050, 470))


class CompanionAdapterTests(unittest.TestCase):
    def setup_adapter(self):
        api = pure_api(self, {"Roamer", "RoamScreen"})
        roamer = api["Roamer"]((800.0, 300.0), 0.0, rng=MinimumRng(),
                    cfg={"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 10.0, "rest_max_s": 10.0,
                         "approach_cooldown_s": 0.0, "wander_enabled": False,
                         "walk_speed": 40.0})
        world = {"screen": fake_rect(0, 0, 1000, 700), "frame": fake_rect(750, 250, 100, 100),
                 "now": 10.0, "moves": []}
        screen = SimpleNamespace(visibleFrame=lambda: world["screen"], frame=lambda: world["screen"],
                                 deviceDescription=lambda: {"NSScreenNumber": 11})
        def place(point):
            world["frame"].origin = SimpleNamespace(x=point.x, y=point.y)
            world["moves"].append((point.x, point.y))
        window = SimpleNamespace(frame=lambda: world["frame"], screen=lambda: screen, setFrameOrigin_=place)
        state = {"hover": False, "override": None, "roam_anim": None, "roam_layout": None,
                 "menu_open": False, "roam_hold": False, "stats": None,
                 "dragging": False, "reduce_motion": False}
        def override(name, **kwargs):
            state["override"] = name
        def clear():
            state["override"] = None
        scope = {"win": window, "roamer": roamer, "state": state, "ui": {},
                 "RoamScreen": api["RoamScreen"],
                 "RUNTIME": {"roam": True}, "math": math,
                 "_time": SimpleNamespace(monotonic=lambda: world["now"]),
                 "roam_clock": {"rm_at": 0.0}, "_reduce_motion": lambda: False,
                 "NSScreen": SimpleNamespace(mainScreen=lambda: screen, screens=lambda: [screen]),
                 "NSEvent": SimpleNamespace(mouseLocation=lambda: SimpleNamespace(x=1400.0, y=300.0)),
                 "NSMakePoint": lambda x, y: SimpleNamespace(x=x, y=y),
                 "view": SimpleNamespace(petOnRight=lambda: True, petOnBottom=lambda: True),
                 "spike_info": lambda stats: None, "set_override": override, "clear_sticky": clear}
        gui_functions(self, ("roam_tick", "roam_resync", "roam_bounds", "window_center"), scope)
        for now in range(10):
            roamer.step(float(now), (1400.0, 300.0), (50.0, 50.0, 950.0, 650.0))
        roamer.step(10.0, (1400.0, 300.0), (50.0, 50.0, 950.0, 650.0), activity=True)
        self.assertEqual(roamer.phase, "out")
        return world, scope

    def test_display_shrink_recovers_full_window_and_cancels_old_trip(self):
        world, scope = self.setup_adapter()
        world["now"] = 10.25
        scope["roam_tick"]()
        world["screen"] = fake_rect(0, 0, 600, 700)
        world["now"] = 10.5
        scope["roam_tick"]()
        frame = world["frame"]
        self.assertLessEqual(frame.origin.x + frame.size.width, 600.0,
                             "automatic walk continued outside the changed visible display")
        self.assertGreaterEqual(frame.origin.x, 0.0)
        self.assertEqual(scope["roamer"].phase, "rest")
        before = scope["window_center"]()
        world["now"] = 10.75
        scope["roam_tick"]()
        self.assertEqual(scope["window_center"](), before)

    def test_resize_while_away_cancels_motion_and_recomputes_window_radius(self):
        world, scope = self.setup_adapter()
        world["now"] = 10.25
        scope["roam_tick"]()
        world["frame"].size = SimpleNamespace(width=300.0, height=200.0)
        world["now"] = 10.5
        scope["roam_resync"]()
        self.assertEqual(scope["roamer"].phase, "rest", "resize left the previous trip active")
        self.assertAlmostEqual(scope["roamer"].radius, math.hypot(150.0, 100.0))
        frame = world["frame"]
        self.assertGreaterEqual(frame.origin.x, 0.0)
        self.assertLessEqual(frame.origin.x + frame.size.width, 1000.0)



class CompanionCompactRegressionTests(unittest.TestCase):
    def adapter(self, right=False):
        api = pure_api(self, {"Roamer", "RoamDisplay", "roam_frame", "RoamScreen"})
        world = {"frame": fake_rect(270, 240, 300, 220), "now": 0.1, "writes": []}
        screen = SimpleNamespace(visibleFrame=lambda: fake_rect(0, 0, 1400, 1000),
                                 frame=lambda: fake_rect(0, 0, 1400, 1000),
                                 deviceDescription=lambda: {"NSScreenNumber": 12})
        def place(p):
            world["frame"].origin = SimpleNamespace(x=p.x, y=p.y)
        def resize(rect, display):
            world["frame"] = rect
        win = SimpleNamespace(frame=lambda: world["frame"], screen=lambda: screen,
                              setFrameOrigin_=place, setFrame_display_=resize)
        view = SimpleNamespace(petOnRight=lambda: right, petOnBottom=lambda: False,
                               setFrame_=lambda rect: None, window=lambda: win,
                               setNeedsDisplay_=lambda value: None, _moved=True)
        state = {"hover": False, "override": None, "roam_anim": None, "roam_layout": (right, False),
                 "menu_open": False, "roam_hold": False, "stats": None, "dragging": False,
                 "reduce_motion": False, "show_panel": True, "roam_display": api["RoamDisplay"](),
                 "roam_env": (300, 220), "roam_crop": None, "roam_rects": None}
        r = api["Roamer"]((420, 350), 0, rng=MinimumRng(),
                           cfg={"follow_p": 0.0, "jump_enabled": False, "rest_min_s": 0, "rest_max_s": 0, "wander_enabled": False})
        r.step(0, (1200, 350), (150, 110, 1250, 890), activity=True)
        self.assertEqual(r.phase, "out")
        scope = dict(api, win=win, view=view, state=state, roamer=r, ui={}, math=math,
                     RUNTIME={"roam": True}, _time=SimpleNamespace(monotonic=lambda: world["now"]),
                     roam_clock={"rm_at": 0}, _reduce_motion=lambda: False,
                     NSScreen=SimpleNamespace(screens=lambda: [screen], mainScreen=lambda: screen),
                     NSEvent=SimpleNamespace(mouseLocation=lambda: SimpleNamespace(x=1200, y=350)),
                     NSMakeRect=fake_rect, NSMakePoint=lambda x, y: SimpleNamespace(x=x, y=y),
                     PW=80, PH=60, W=300, H=220, g={"scale": 0.5}, pill_h=lambda lines=2: 152,
                     # v0.26 shape: (provider blocks, text width incl. the mark indent, height)
                     roam_summary_text=lambda: ([], 130, 30),
                     spike_info=lambda stats: None,
                     set_override=lambda name, **kw: state.update(override=name),
                     clear_sticky=lambda: state.update(override=None), cfg={},
                     merge_config_updates=lambda values: world["writes"].append(values))
        gui_functions(self, ("roam_tick", "roam_apply_display", "window_center", "clamp_to_screen"), scope)
        state["roam_release"] = lambda moved: (state["roam_display"].reset(),
                                                r.release(world["now"], scope["window_center"](), moved))
        scope["roam_apply_display"]("out")
        return world, scope

    def test_crop_change_during_drag_preserves_actual_manual_displacement(self):
        world, s = self.adapter()
        world["frame"].origin.x += 37
        world["frame"].origin.y -= 19
        before = s["window_center"]()
        self.assertEqual(before, (457, 331))
        s["state"]["dragging"] = True
        s["roam_tick"]()
        self.assertEqual(s["window_center"](), (457, 331),
                         "presentation restoration discarded the user's actual drag delta")
        self.assertEqual(tuple(s["roamer"].home), (420, 350))
        self.assertEqual(world["writes"], [])

    def test_folded_drop_clamps_logical_envelope_before_save_and_restore(self):
        world, s = self.adapter(right=True)
        # Right/top crop begins 184pt into the virtual full frame. A native x=7
        # is visible as a folded window, but its virtual left edge is -177.
        world["frame"].origin.x = 7
        world["frame"].origin.y = 396
        s["state"]["dragging"] = True
        gui_method(self, "PetView", "mouseUp_", s)(s["view"], SimpleNamespace())
        self.assertEqual(world["writes"], [{"x": 0.0, "y": 240.0}],
                         "folded drag persisted a full window outside the visible display")
        self.assertEqual(tuple(s["roamer"].home), (150, 350))
        s["state"]["hover"] = True
        s["roam_tick"]()
        f = world["frame"]
        self.assertGreaterEqual(f.origin.x, 0)
        # The restored 'full' presentation is the text-sized pill's union crop
        # (right layout, text_w=130, one line), never the whole 300x220 window.
        self.assertEqual((f.size.width, f.size.height), (160, 98))
        self.assertEqual(s["state"]["roam_mode"], "full")

    def test_actual_summary_formatter_distinguishes_estimate_from_exact(self):
        """The GUI adapter's wiring around the pure formatter: every exact row except
        credits (``_label_order`` 9) is handed on — a server model label that is not a
        bare family word ("Claude Fable 5", order 5) must survive; reset texts are
        pre-formatted into the second line; the spike flag lands on the exact session
        row; the ⚠ suffix appears on an estimate after a token error; the height is
        two lines when a reset line exists; the API budget reaches the cost segment;
        and the text is memoised per input and 5-second window.

        Rivals: credits row kept; the round-1 ``> 2`` filter (drops "Claude Fable 5");
        no reset line at all; spike_first never passed; ⚠ on exact rows; one-line
        height with a second line present; no memo (every tick re-measures); a memo
        keyed without the auth error, the cost, the budget or the time window (stale
        text after a refresh); a memo keyed without the language or the onboarding
        state (stale labels after a language change, or the onboarding line lingering
        after onboarding ends — ``t()`` reads the module-level ``L["lang"]``, so the
        scope below supplies ``L`` the way the application's globals do)."""
        from datetime import datetime, timezone
        # v0.26: roam_summary_text now folds through summary_lines and returns
        # (blocks, text_w, height) instead of (main, sub, w, h). The pure helpers it
        # reaches have to come along, and the screen-derived budget is stubbed below so
        # this stays a formatter test rather than a geometry one.
        api = pure_api(self, {"roam_summary", "roam_summary_runs", "SUMMARY_H",
                              "SUMMARY_H2", "summary_lines", "SUMMARY_LOGO_W",
                              "SUMMARY_LINE_H", "pill_h"})
        now = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        state = {"oauth": None, "stats": {"session": {"pct": 42}, "weekly": {"pct": 17}},
                 "cost": None, "cost_month": None}
        oauth_status = {"auth_error": False}
        spikes = {"value": None}
        clock = {"now": 1000.0}
        measured = []
        runtime = {"mode": "sub", "api_budget": None, "admin_key": None}
        lang_table = {"lang": "ko"}   # the module-level L that t() reads; a memo input too

        def astr(text, font):
            measured.append(text)
            return SimpleNamespace(size=lambda: SimpleNamespace(width=len(text)))

        scope = dict(api, state=state, RUNTIME=runtime, L=lang_table, F_SUMMARY=None,
                     F_SUMMARY_SUB=None,
                     OAUTH_STATUS=oauth_status, datetime=datetime, timezone=timezone,
                     spike_info=lambda stats: spikes["value"],
                     fmt_countdown=lambda reset, at: "in 3h" if reset else "-",
                     # INERT, and left only because removing it is a separate change:
                     # `_label_order` is consulted from inside `roam_summary`, which is a
                     # module-level function whose globals are pure_api's namespace — not
                     # this scope, which is only the globals of the nested functions
                     # `gui_functions` extracts. The **real** `_label_order` is what runs.
                     # Do not reason about this test's row selection from this stub; a
                     # reader who did got a wrong answer once already.
                     _label_order=lambda label: {"session": 0, "주간": 1, "Fable": 2,
                                                 "Credits": 9}.get(label, 5),
                     _summary_memo={"key": None, "value": None},
                     _time=SimpleNamespace(time=lambda: clock["now"]),
                     t=lambda key: {"session": "세션", "weekly": "주간", "reset_prefix": "reset ",
                                    "today": "Today", "this_month": "This month"}.get(key, key),
                     # A budget far wider than any fixture here: this test is about which
                     # runs come out and what the memo is keyed on, not about folding.
                     # Production derives this from the screen (_pill_text_budget).
                     _pill_text_budget=lambda: 10_000.0,
                     astr=astr)
        # ``summary_lines`` is a module-level function, so it translates through the
        # module-level ``t`` in ``pure_api``'s namespace — not through the stub in the
        # scope below, which only reaches the nested functions extracted by
        # ``gui_functions``. Before v0.26 all the translating happened inside
        # ``roam_summary_text`` and the scope stub was enough; folding moved it out.
        # Inject the same stub into that namespace so this stays a test of *which keys*
        # reach the line rather than of the Korean strings they resolve to.
        api["t"] = scope["t"]
        gui_functions(self, ("roam_summary_text",), scope)
        text = scope["roam_summary_text"]

        def lines():
            """(first-line text, reset-line text, width, height) from the new shape.

            ``roam_summary_text`` returns provider blocks now. Everything below still
            asks the old two questions — what is on the gauge line and what is on the
            reset line — so they are recovered here: within a provider the reset line is
            the trailing line whose runs are all ``sub``.
            """
            blocks, width, height = text()
            rows = [line for _pid, block in blocks for line in block]
            # A reset line is one that *opens* with a ``sub`` run. Classifying by "every
            # run is sub" breaks the moment a marker is appended to it, which is exactly
            # the bug below — and a helper that silently reclassifies a line is how that
            # bug would have stayed invisible.
            main = [r for line in rows if not (line and line[0][1] == "sub") for r in line]
            sub = [r for line in rows if line and line[0][1] == "sub" for r in line]
            return ("".join(t for t, _k in main), "".join(t for t, _k in sub), width, height)

        def fresh():
            """Defeat the memo the way a refresh does: a new stats object, a new window."""
            state["stats"] = dict(state["stats"])
            clock["now"] += 5

        self.assertEqual(lines(), ("세션 ≈42% · 주간 ≈17%", "", 17 + api["SUMMARY_LOGO_W"], api["SUMMARY_H"]))
        # memo: the same inputs inside the 5-second window measure nothing again and
        # return the very same object; a flipped auth error, a new stats object, or the
        # next 5-second window each recompute.
        first = text()
        measured.clear()
        clock["now"] += 4.9
        self.assertIs(text(), first)
        self.assertEqual(measured, [], "a second call in the same window re-measured the text")
        oauth_status["auth_error"] = True
        # ``text()[0]`` is the provider blocks now, not a flat run list. The ⚠ still
        # belongs at the end of the Claude segment.
        #
        # **It must stay a bare marker run.** The v0.24 contract (CLAUDE.md) is "the old
        # status line's ⚠ survives as a trailing run appended by the adapter" — a run,
        # not a gauge row. Appending it as a row instead makes the estimate renderer give
        # it a value, and the pill reads `… Fable ≈12% · ⚠ ≈0%`. That fabricated 0% is
        # the exact lie this repository refuses everywhere else ("0% 를 지어내지 않는다"),
        # and here it is stapled to a warning, where a user reading "0%" would conclude
        # they had used almost nothing.
        claude_block = dict(text()[0])["claude"]
        gauge_lines = [ln for ln in claude_block if not (ln and ln[0][1] == "sub")]
        reset_lines = [ln for ln in claude_block if ln and ln[0][1] == "sub"]
        rendered = "".join(t for ln in gauge_lines for t, _k in ln)
        self.assertNotIn(
            "0%", rendered,
            f"the ⚠ is being rendered as a gauge row with an invented percentage: "
            f"{rendered!r} — it must be a trailing marker run, not a row")
        # CLAUDE.md: "토큰 만료(401 지속)로 추정치로 내려간 상태는 **첫 줄 끝** ⚠".
        # It marks the *numbers* as estimates, so it belongs beside them — not on the
        # dim reset line, where it reads as a comment about the reset time and is drawn
        # in the sub colour. Appending to the block's last line puts it there whenever a
        # reset line exists, which is the common case.
        self.assertEqual(
            gauge_lines[-1][-1], (" ⚠", "status"),
            f"the auth-error marker is not at the end of the gauge line: {rendered!r}")
        for line in reset_lines:
            self.assertNotIn(
                "⚠", "".join(t for t, _k in line),
                "the ⚠ landed on the reset line — it marks the numbers, not the reset time")
        self.assertTrue(measured, "an auth-error flip must invalidate the memo")
        measured.clear()
        clock["now"] += 5
        self.assertIsNot(text(), first)
        self.assertTrue(measured, "the next 5-second window must recompute")
        # The language and the onboarding state are memo inputs too — t() reads
        # L["lang"], and roam_summary turns the onboarding state into a status line —
        # so either changing inside the same 5-second window, with the same stats
        # object, must recompute rather than hand back the memoised text.
        before = text()
        measured.clear()
        lang_table["lang"] = "en"
        self.assertIsNot(text(), before, "a language change inside the window returned the memoised text")
        self.assertTrue(measured, "a language change must invalidate the memo")
        before = text()
        measured.clear()
        state["onboard"] = "install"
        self.assertIn("onb_install", lines()[0], "the onboarding state must reach the status line")
        self.assertIsNot(text(), before, "an onboarding change inside the window returned the memoised text")
        self.assertTrue(measured, "an onboarding change must invalidate the memo")
        state["onboard"] = None
        measured.clear()
        self.assertEqual(lines()[0], "세션 ≈42% · 주간 ≈17% ⚠",
                         "clearing the onboarding state must bring the gauges back")
        self.assertTrue(measured, "clearing the onboarding state must invalidate the memo")
        fresh()
        state["stats"]["now"] = now
        state["stats"]["session"] = {"pct": 42, "reset": now}
        state["stats"]["weekly"] = {"pct": 17, "reset": now}
        self.assertEqual(lines(), ("세션 ≈42% · 주간 ≈17% ⚠", "reset 세션 in 3h", 19 + api["SUMMARY_LOGO_W"], api["SUMMARY_H2"]))
        state["oauth"] = [("session", 42, None, None), ("주간", 17, None, None),
                          ("Claude Fable 5", 12, None, None), ("Credits", 5, None, None)]
        self.assertEqual(lines(), ("session 42% · 주간 17% · Claude Fable 5 12%", "", 41 + api["SUMMARY_LOGO_W"], api["SUMMARY_H"]),
                         "only credits are dropped; a non-family model label is kept")
        state["oauth"] = [("session", 42, now, None), ("주간", 17, None, "next Monday")]
        self.assertEqual(lines()[1], "reset session in 3h · 주간 next Monday")
        self.assertEqual(lines()[3], api["SUMMARY_H2"])
        spikes["value"] = {"session": True}
        fresh()
        self.assertEqual(dict(text()[0])["claude"][0][0], ("▲session", "bad"))
        self.assertNotIn("⚠", lines()[0])
        # API mode: the budget from RUNTIME reaches the cost segment and colours the month.
        runtime.update(mode="api", admin_key="k", api_budget=50)
        state.update(cost=12.375, cost_month=27.5)
        fresh()
        # Same shape change as above: provider blocks, not a flat (main, sub) pair.
        # API mode produces one cost line and no reset line, so the Claude block is a
        # single line and `sub` is empty — asserted below rather than assumed.
        blocks, width, height = text()
        claude_lines = dict(blocks)["claude"]
        main = [r for ln in claude_lines if not (ln and ln[0][1] == "sub") for r in ln]
        sub = [r for ln in claude_lines if ln and ln[0][1] == "sub" for r in ln]
        self.assertEqual("".join(t for t, _k in main), "Today $12.38 · This month $27.50 / $50")
        # Round 3 swapped the roles: the word "this month" carries the budget share
        # colour and the amount is plain cost-coloured.
        self.assertEqual(main[3:5], [("This month ", "warn"), ("$27.50", "cost")])
        self.assertEqual(main[0:2], [("Today ", "value"), ("$12.38", "cost")])
        self.assertEqual((sub, height), ([], api["SUMMARY_H"]))
        runtime["api_budget"] = None
        fresh()
        self.assertEqual(lines()[0], "Today $12.38 · This month $27.50")

    def test_the_adapter_gives_summary_lines_the_full_inner_width_not_the_text_width(self):
        """어댑터가 `summary_lines` 에 넘기는 예산이 **필 안쪽 전체 폭**인가.

        훅(`_pill_budget_for`)이 돌려주는 것은 **글자 자리** 폭이고, `summary_lines` 는
        받은 예산에서 `SUMMARY_LOGO_W` 를 스스로 뺀다. 그래서 어댑터는 넘기기 전에 로고
        폭을 되돌려 줘야 한다. 그 한 줄이 없으면 예산이 두 번 깎이고, 가장 긴 줄이 **딱
        로고 폭만큼** 넘쳐서 접힌다 — 화면에서는 마지막 게이지의 라벨과 값이 서로 다른
        줄로 갈라지는 것으로 보인다.

        **폭 게이트로는 안 잡힌다.** 너무 이르게 접힌 줄은 어떤 예산에도 들어가고 아무것도
        잘리지 않는다. "넘치지 않는가"가 아니라 "접힐 필요가 없는데 접혔는가"를 물어야
        하고, 그건 실제 어댑터를 돌려야 보인다 — 예산 계산을 테스트가 다시 적으면 그
        재현이 생산의 뺄셈을 대신해 버려 변이가 보이지 않는다(실제로 그렇게 놓쳤다).

        Rivals: 어댑터가 로고 폭을 되돌려 주지 않는 구현(이 테스트가 잡는 것);
        `summary_lines` 가 뺄셈을 그만두는 구현(예산이 넓어져 필 밖으로 나간다 —
        tests/test_summary_layout.py 의 EveryLineFitsTests 가 잡는다).
        """
        from datetime import datetime, timezone
        api = pure_api(self, {"roam_summary", "roam_summary_runs", "SUMMARY_H",
                              "SUMMARY_H2", "summary_lines", "SUMMARY_LOGO_W",
                              "SUMMARY_LINE_H", "pill_h"})
        widths = {}

        def astr(text, _font=None):
            return SimpleNamespace(size=lambda: SimpleNamespace(
                width=sum(widths.get(c, 7.0) for c in text)))

        # A budget that is *exactly* the widest line's text width. With the logo width
        # handed back the line fits on one; without it the budget is 18pt short and the
        # last gauge splits off.
        rows = [("Session", 42.0, None, None), ("Weekly", 17.0, None, None),
                ("Fable", 12.0, None, None), ("Credit", 66.0, None, None)]
        claude_pet_t = lambda key: {"credit": "Credit", "reset_prefix": "reset "}.get(key, key)
        # Install the stub **before** building the segment: `roam_summary` decides whether
        # a row is the credit row via `_label_order`, which compares against `t("credit")`
        # in pure_api's namespace. Setting it afterwards silently dropped the credit row
        # from the fixture's own measurement, so the fixture and the adapter disagreed by
        # the width of that row — the fixture's fault, not production's.
        api["t"] = claude_pet_t
        state = {"oauth": rows, "stats": None, "cost": None, "cost_month": None,
                 "onboard": None, "credit_text": "$100.66", "codex": None,
                 "api_error": False, "api_stale": False, "codex_summary": None}
        segment = api["roam_summary"]("sub", [(r[0], r[1], None) for r in rows],
                                      None, None, None, False, None,
                                      credit_text="$100.66")
        main, _sub = api["roam_summary_runs"]([segment], claude_pet_t)
        widest = sum(astr(txt).size().width for txt, _k in main)

        # Characterise the contract first: `summary_lines` subtracts the logo width, so a
        # budget that is exactly the text width folds, and one with the logo width added
        # back does not. This is the seam the adapter has to get right.
        for give_back, expect_lines, why in (
                (True, 1, "로고 폭을 되돌려 주면 한 줄에 들어간다"),
                (False, 2, "되돌려 주지 않으면 딱 로고 폭만큼 넘쳐 갈라진다")):
            with self.subTest(gives_logo_width_back=give_back):
                budget = widest + (api["SUMMARY_LOGO_W"] if give_back else 0)
                lines = api["summary_lines"]([("claude", [segment])],
                                             lambda s: astr(s).size().width, budget)
                gauge = [ln for pid, block in lines for ln in block
                         if any(k != "sub" for _t, k in ln)]
                self.assertEqual(len(gauge), expect_lines, why)

        # Now the actual gate: drive the **real adapter** with a hook that returns exactly
        # the text width, and require the line to survive on one. If the adapter stops
        # handing the logo width back, the budget is 18pt short and this splits.
        clock = {"now": 1000.0}
        scope = dict(api, state=state, RUNTIME={"mode": "sub", "api_budget": None,
                                                "admin_key": None},
                     L={"lang": "en"}, F_SUMMARY=None, F_SUMMARY_SUB=None,
                     OAUTH_STATUS={"auth_error": False},
                     datetime=datetime, timezone=timezone,
                     spike_info=lambda stats: None,
                     fmt_countdown=lambda reset, at: "-",
                     _label_order=lambda label: 9 if label == "Credit" else 0,
                     _summary_memo={"key": None, "value": None},
                     _time=SimpleNamespace(time=lambda: clock["now"]),
                     t=claude_pet_t, astr=astr,
                     _stable_w=lambda text, _font=None: astr(text).size().width,
                     _pill_text_budget=lambda: widest)
        state["pill_budget"] = lambda need: widest
        gui_functions(self, ("roam_summary_text",), scope)
        blocks, _tw, _th = scope["roam_summary_text"]()
        gauge = [ln for _pid, block in blocks for ln in block
                 if any(k != "sub" for _t, k in ln)]
        self.assertEqual(
            len(gauge), 1,
            "어댑터가 훅의 글자-자리 예산에 로고 폭을 되돌려 주지 않는다 — 가장 긴 줄이 "
            f"로고 폭만큼 넘쳐 갈라진다: {[''.join(x for x, _k in ln) for ln in gauge]}")

    def _drive_draw(self):
        """실제 `draw_summary_pill` 을 구동할 scope. (설정, draws, logos) 를 돌려준다."""
        draws, logos = [], []

        def astr(value, font):
            width = sum(10 if char.isupper() else 7 for char in value)
            return SimpleNamespace(size=lambda: SimpleNamespace(width=width, height=13),
                    drawAtPoint_=lambda p: draws.append((value, p.x, p.y, font)))

        blocks = {"value": []}
        pill = {"rect": (4, 66, 260, 46)}
        api = pure_api(self, {"roam_summary", "SUMMARY_H2", "SUMMARY_LINE_H",
                              "SUMMARY_LOGO_W"})
        scope = dict(api, view=SimpleNamespace(pillRect=lambda: pill["rect"]),
                     roam_summary_text=lambda: (blocks["value"], 999, pill["rect"][3]),
                     draw_summary_logo=lambda pid, lx, ly: logos.append((pid, lx)),
                     astr=astr, F_SUMMARY="main-font", F_SUMMARY_SUB="sub-font",
                     F_SUMMARY_BY_KIND={"exact": "exact-font"},
                     F_SUMMARY_SUB_BY_KIND={"sub": "sub-kind-font"}, PILL_PAD=13,
                     SUMMARY_RADIUS=claude_pet_const("SUMMARY_RADIUS"),
                     C_PILL=SimpleNamespace(set=lambda: None), NSMakeRect=fake_rect,
                     NSMakePoint=lambda x, y: SimpleNamespace(x=x, y=y),
                     NSBezierPath=SimpleNamespace(bezierPathWithRoundedRect_xRadius_yRadius_=
                                                 lambda *args: SimpleNamespace(fill=lambda: None)))
        gui_functions(self, ("draw_summary_pill",), scope)

        def render(value):
            draws.clear(); logos.clear()
            blocks["value"] = value
            scope["draw_summary_pill"]()
            return list(draws), list(logos)

        return render

    CLAUDE_BLOCK = ("claude", [[("Session", "exact"), (" 42%", "value")],
                               [("reset Session 3h", "sub")]])
    CODEX_BLOCK = ("codex", [[("Weekly", "exact"), (" 68%", "value")]])

    def test_every_provider_combination_draws_its_marks_symmetrically(self):
        """**네 경우 전부** — 사용자가 못 박은 요구다:

            "코덱스만 표시되거나 클로드만 표시되거나 할때도 로고는 표시 되어야한다!"

        `summary_lines` 는 제공자를 모르는 규칙이라 구조 대칭이 공짜로 나오지만, **그리기
        층은 공짜가 아니다.** 이 릴리즈에서 로딩 행렬이 `if claude … else` 로 Claude 를
        특권적으로 놓았다가 정정된 적이 있으므로, 대칭을 단언으로 박아 둔다.

        Claude 쪽만 확인하고 넘어가면 Codex 쪽만 안 그리는 변이가 그대로 지나간다 —
        이 테스트 이전에는 실제로 그랬다.

        Rivals: 제공자가 둘일 때만 마크를 그리는 구현; Claude 만 특별 취급하는 구현;
        블록 순서에 따라 첫 블록만 그리는 구현; 없는 제공자에게 마크를 그리는 구현.
        """
        render = self._drive_draw()
        cases = {
            "claude only": ([self.CLAUDE_BLOCK], ["claude"]),
            "codex only": ([self.CODEX_BLOCK], ["codex"]),
            "both": ([self.CLAUDE_BLOCK, self.CODEX_BLOCK], ["claude", "codex"]),
            "neither": ([], []),
        }
        starts = {}
        for name, (value, want_marks) in cases.items():
            with self.subTest(case=name):
                draws, logos = render(value)
                self.assertEqual(
                    [pid for pid, _x in logos], want_marks,
                    f"{name}: 그려진 마크가 {[p for p, _ in logos]} — 기대는 {want_marks}")
                if want_marks:
                    self.assertTrue(draws, f"{name}: 글자가 하나도 안 그려졌다")
                    starts[name] = draws[0][1]
                    self.assertEqual(
                        len({x for _pid, x in logos}), 1,
                        f"{name}: 마크들이 같은 왼쪽 끝에서 시작하지 않는다")
                else:
                    self.assertEqual((draws, logos), ([], []),
                                     "제공자가 없으면 아무것도 그리지 않는다")

        self.assertEqual(
            len(set(starts.values())), 1,
            f"제공자 조합에 따라 글자 시작점이 달라진다: {starts} — 로그인 하나로 줄이 "
            "옆으로 밀린다")

    def test_every_line_of_a_provider_block_starts_at_the_same_x(self):
        """왼쪽 정렬. 사용자: "로고가 왼쪽에 있는데 글시가 가운데 정렬하니까 뭔가 이상해".

        가운데 정렬(`cx = x + (w - total) / 2`)에서는 줄마다 폭이 달라 시작점이 제각각
        움직이고, **가장 긴 줄에서만 우연히 마크와 맞아 보인다.** 짧은 줄일수록 안쪽으로
        떠서 마크에서 멀어진다.

        "보기 좋은가"는 단언할 수 없지만 **위치는 단언할 수 있다** — 한 블록의 모든 줄이
        같은 x 에서 시작한다. 길이가 다른 줄을 일부러 섞어 두므로, 가운데 정렬로 되돌아가면
        시작점이 갈라져 실패한다.

        마크 없는 전역 상태 줄의 정렬은 아직 결정이 안 났으므로 여기서 단언하지 않는다.
        """
        render = self._drive_draw()
        block = ("claude", [
            [("Session", "exact"), (" 42%", "value"), (" · ", "status"),
             ("Weekly", "exact"), (" 17%", "value")],      # long
            [("reset Session 3h", "sub")],                  # much shorter
            [("W", "exact")],                               # shortest possible
        ])
        draws, _logos = render([block])
        self.assertTrue(draws, "아무것도 안 그려졌다")

        # 줄별 첫 run 의 x. `_draw_runs` 는 한 줄의 run 들을 이어 그리므로 줄의 시작점은
        # 그 줄에서 가장 작은 x 다.
        by_line = {}
        for _text, x, y, _font in draws:
            by_line[round(y, 3)] = min(by_line.get(round(y, 3), x), x)
        self.assertEqual(len(by_line), 3, f"3줄이 그려져야 한다: {by_line}")
        starts = set(round(v, 3) for v in by_line.values())
        self.assertEqual(
            len(starts), 1,
            f"한 블록의 줄들이 서로 다른 x 에서 시작한다: {sorted(starts)} — 가운데 "
            "정렬이면 짧은 줄이 안쪽으로 떠서 마크와 어긋난다")

    def test_actual_summary_draw_draws_every_provider_line_and_cuts_nothing(self):
        """The real ``draw_summary_pill``, executed. Rewritten 2026-09-20.

        It used to assert the opposite of what it now asserts, and that is the point
        worth recording. Its old name ended ``keeps_long_text_inside_pill_padding`` and
        its final check was ``self.assertTrue(draws[0][0].endswith("…"))`` — it *required*
        the overflowing label to be ellipsised, because at the time the drawing function
        called ``roam_fit_runs`` itself. So the one test that actually ran the drawing
        path was pinning the truncation, and it stayed green through every round in which
        the Codex row was being cut off the screen.

        The contract is now the reverse: ``summary_lines`` has already split the lines,
        and **the drawing function trims nothing**. Anything it is handed, it draws.

        Rivals: drawing through a fitter again (nothing would be ellipsised only because
        the fixture is short — so the fixture here is deliberately wider than the pill);
        drawing only the first provider; repeating a provider's mark on its folded
        continuation lines; drawing a mark for a provider with no lines; drawing with no
        pill rect.
        """
        draws = []
        logos = []
        long_label = "A server-provided usage label that exceeds the small summary pill"

        def astr(value, font):
            width = sum(10 if char.isupper() else 7 for char in value)
            return SimpleNamespace(size=lambda: SimpleNamespace(width=width, height=13),
                    drawAtPoint_=lambda p: draws.append((value, p.x, p.x + width, p.y, font)))

        blocks = {"value": [("claude", [[(long_label, "exact"), (" 42%", "value")]])]}
        pill = {"rect": (4, 66, 260, 46)}
        api = pure_api(self, {"roam_summary", "SUMMARY_H2", "SUMMARY_LINE_H",
                              "SUMMARY_LOGO_W"})
        scope = dict(api, view=SimpleNamespace(pillRect=lambda: pill["rect"]),
                     roam_summary_text=lambda: (blocks["value"], 999, pill["rect"][3]),
                     draw_summary_logo=lambda pid, lx, ly: logos.append((pid, lx, ly)),
                     astr=astr, F_SUMMARY="main-font", F_SUMMARY_SUB="sub-font",
                     F_SUMMARY_BY_KIND={"exact": "exact-font"},
                     F_SUMMARY_SUB_BY_KIND={"sub": "sub-kind-font"}, PILL_PAD=13,
                     C_PILL=SimpleNamespace(set=lambda: None), NSMakeRect=fake_rect,
                     SUMMARY_RADIUS=claude_pet_const("SUMMARY_RADIUS"),
                     NSMakePoint=lambda x, y: SimpleNamespace(x=x, y=y),
                     NSBezierPath=SimpleNamespace(bezierPathWithRoundedRect_xRadius_yRadius_=
                                                 lambda *args: SimpleNamespace(fill=lambda: None)))
        gui_functions(self, ("draw_summary_pill",), scope)

        scope["draw_summary_pill"]()
        self.assertTrue(draws, "nothing was drawn")
        self.assertEqual([d[0] for d in draws], [long_label, " 42%"],
                         "the drawing path altered the text it was handed — it must not "
                         "trim, ellipsise or re-fit anything")
        for text, _x0, _x1, _y, _font in draws:
            self.assertFalse(text.endswith("\u2026"),
                             f"{text!r} was ellipsised while drawing; folding is "
                             "summary_lines' job and the renderer must not re-cut")
        self.assertEqual(draws[0][4], "exact-font")
        self.assertEqual([pid for pid, _lx, _ly in logos], ["claude"],
                         "the provider mark must be drawn exactly once")

        # Two providers, one of them folded onto two lines: every line is drawn, the
        # mark appears once per provider (not once per line), and the folded
        # continuation is indented like its first line.
        draws.clear(); logos.clear()
        blocks["value"] = [
            ("claude", [[("Session", "exact"), (" 42%", "value")],
                        [("Weekly", "exact"), (" 17%", "value")]]),
            ("codex", [[("Weekly", "exact"), (" 68%", "value")]]),
        ]
        pill["rect"] = (4, 66, 260, 3 * api["SUMMARY_LINE_H"] + 14)
        scope["draw_summary_pill"]()
        self.assertEqual([d[0] for d in draws],
                         ["Session", " 42%", "Weekly", " 17%", "Weekly", " 68%"],
                         "a folded line or a whole provider was dropped")
        self.assertEqual([pid for pid, _lx, _ly in logos], ["claude", "codex"],
                         "the mark must be drawn once per provider, not once per line")
        # Lines are **left-aligned** inside the indented box as of 2026-09-20. This block
        # previously asserted the opposite — that every line shares a *centre* — which was
        # right while `_draw_runs` centred, and is now exactly backwards. The user's
        # objection was that centring breaks the relationship with the mark: the mark is
        # pinned left and the text floats, so only the longest line happens to line up.
        #
        # So: one shared left edge, and it begins after the pill padding plus the mark's
        # width, so no line can run under the logo.
        by_line = {}
        for text, x0, _x1, y, _font in draws:
            by_line[round(y, 3)] = min(by_line.get(round(y, 3), x0), x0)
        self.assertEqual(len(by_line), 3, f"expected 3 drawn lines, got {by_line}")
        lefts = {round(v, 3) for v in by_line.values()}
        self.assertEqual(len(lefts), 1,
                         f"provider lines do not share a left edge: {sorted(lefts)}")
        box_left = 4 + 13 + api["SUMMARY_LOGO_W"]
        self.assertAlmostEqual(lefts.pop(), box_left, places=3,
                               msg="text does not start after the padding and the mark")

        draws.clear(); logos.clear()
        blocks["value"] = []
        scope["draw_summary_pill"]()
        self.assertEqual((draws, logos), ([], []),
                         "no lines means no marks either — a mark alone is a provider "
                         "row with nothing in it")

        draws.clear(); logos.clear()
        pill["rect"] = None
        scope["draw_summary_pill"]()
        self.assertEqual((draws, logos), ([], []))

    def test_fit_contract_uses_measured_longest_prefix_and_tiny_width(self):
        api = pure_api(self, {"roam_fit_text", "roam_summary_line", "SUMMARY_APPROX"})
        fit = api["roam_fit_text"]
        measure = lambda value: sum({"W": 10, "i": 2, "…": 5}.get(c, 6) for c in value)
        self.assertEqual(fit("WiWi", 24, measure), "WiWi")
        self.assertEqual(fit("WiWi", 23, measure), "Wi…")
        self.assertEqual(fit("WiWi", 5, measure), "…")
        self.assertEqual(fit("WiWi", 4, measure), "")
        self.assertEqual(fit("", 0, measure), "")
        self.assertEqual(api["roam_summary_line"]("estimate", [("session", 42, False, None)],
                                                 lambda key: "세션"), "세션 ≈42%")
        self.assertEqual(api["roam_summary_line"]("exact", [("session", 42, False, None)],
                                                 lambda key: "세션"), "session 42%")


class CodexOnboardingSuppressionTests(unittest.TestCase):
    """Codex-ready users must not see Claude's onboarding nag, but every other Claude
    status must keep showing regardless of Codex. Exercises the real
    ``roam_summary_text`` closure end to end, the same way
    ``CompanionCompactRegressionTests.test_actual_summary_formatter_distinguishes_estimate_from_exact``
    does — the suppression (``claude_onboarding_suppressed``) is a local of that closure,
    so a bare ``roam_summary()`` call can never see it.

    Rivals this rules out:

    - suppressing *every* Claude status whenever Codex has data (would hide
      token_expired/scanning/etc, which is unrelated to onboarding and must still be
      shown regardless of what Codex is doing);
    - suppressing onb_install/onb_login unconditionally, Codex or not (breaks the much
      larger population of users who do not use Codex at all — this is the original,
      pre-fix behaviour and must not regress);
    - gating on ``codex_seg`` truthiness alone without checking its ``kind`` — a Codex
      *status* segment (loading/absent) is not "real" data and must not suppress
      anything, only an ``("exact", rows)`` segment counts;
    - leaving ``state["summary_status"]`` set to the suppressed key, which would make a
      click on invisible text act as though the (unshown) onboarding line was clicked.
    """

    def _harness(self, auth_error=False, stats=None):
        """Build the actual ``roam_summary_text`` closure with a minimal stub scope.

        Mirrors ``CompanionCompactRegressionTests``'s harness for the same closure:
        the required pure API, a hand-built ``state``/``RUNTIME``/``L``, and the
        ``t()``/``astr`` stubs the closure and its module-level collaborators
        (``summary_lines`` in particular) read through. Each call returns a *fresh*
        closure with its own ``_summary_memo``, so callers that need two distinct
        readings build two harnesses rather than fight the 5-second memo — the memo key
        does not include the ad-hoc ``codex_summary`` hook used here (production keys
        on ``id(state["codex"])`` instead, one level below the hook), so mutating the
        hook between two calls on the same harness would silently return stale text.
        """
        from datetime import datetime, timezone
        api = pure_api(self, {"roam_summary", "roam_summary_runs", "SUMMARY_H",
                              "SUMMARY_H2", "summary_lines", "SUMMARY_LOGO_W",
                              "SUMMARY_LINE_H", "pill_h"})
        state = {"oauth": None, "stats": {} if stats is None else stats, "cost": None,
                 "cost_month": None, "onboard": None}
        oauth_status = {"auth_error": auth_error}
        runtime = {"mode": "sub", "api_budget": None, "admin_key": None}
        lang_table = {"lang": "ko"}
        clock = {"now": 1000.0}

        def astr(text, font):
            return SimpleNamespace(size=lambda: SimpleNamespace(width=len(text)))

        # Distinctive, non-overlapping markers rather than the real translations, so a
        # substring match below can't accidentally pass for the wrong reason.
        tr_table = {"onb_install": "ONBOARD-INSTALL-MARK",
                    "onb_login": "ONBOARD-LOGIN-MARK",
                    "token_expired": "TOKEN-EXPIRED-MARK",
                    "scanning": "SCANNING-MARK",
                    "reset_prefix": "reset "}
        scope = dict(api, state=state, RUNTIME=runtime, L=lang_table, F_SUMMARY=None,
                     F_SUMMARY_SUB=None, OAUTH_STATUS=oauth_status,
                     datetime=datetime, timezone=timezone,
                     spike_info=lambda stats: None,
                     fmt_countdown=lambda reset, at: "in 3h" if reset else "-",
                     _label_order=lambda label: {"session": 0, "주간": 1}.get(label, 5),
                     _summary_memo={"key": None, "value": None},
                     _time=SimpleNamespace(time=lambda: clock["now"]),
                     t=lambda key: tr_table.get(key, key),
                     _pill_text_budget=lambda: 10_000.0,
                     astr=astr)
        # summary_lines() is module-level, so it translates through pure_api's own
        # namespace, not this scope (see the precedent and full explanation in
        # CompanionCompactRegressionTests.test_actual_summary_formatter_distinguishes_estimate_from_exact).
        api["t"] = scope["t"]
        gui_functions(self, ("roam_summary_text",), scope)
        return scope["roam_summary_text"], state

    @staticmethod
    def _rendered(blocks):
        return "".join(text for _pid, lines in blocks for line in lines for text, _kind in line)

    def test_codex_ready_suppresses_onb_install(self):
        text, state = self._harness()
        state["onboard"] = "install"
        state["codex_summary"] = lambda: ("exact", [("세션", 40.0, False, "in 3h")])
        blocks, _width, _height = text()
        pids = dict(blocks)
        self.assertNotIn(None, pids,
                         "onb_install must not appear as a global status line once "
                         "Codex has real data")
        self.assertNotIn("ONBOARD-INSTALL-MARK", self._rendered(blocks))
        self.assertIn("codex", pids, "Codex's own block must still render")
        self.assertIsNone(state["summary_status"],
                          "a suppressed status must not stay clickable")

    def test_codex_ready_suppresses_onb_login(self):
        # roam_summary_text checks `segment[1] in ("onb_install", "onb_login")` as one
        # condition — both keys share the exact same branch (see the diff), so one case
        # each is enough to prove neither key was left out of that tuple; there is no
        # separate code path for "login" to exercise independently.
        text, state = self._harness()
        state["onboard"] = "login"
        state["codex_summary"] = lambda: ("exact", [("세션", 40.0, False, "in 3h")])
        blocks, _width, _height = text()
        pids = dict(blocks)
        self.assertNotIn(None, pids,
                         "onb_login must not appear as a global status line once "
                         "Codex has real data")
        self.assertNotIn("ONBOARD-LOGIN-MARK", self._rendered(blocks))
        self.assertIsNone(state["summary_status"])

    def test_onb_install_still_shows_without_codex(self):
        """Non-overreach: a user who does not use Codex (hook absent, or present but
        empty) must keep seeing the onboarding line exactly as before this fix.

        The third case is the one that actually exercises ``codex_seg[0] != "status"``:
        a hook that returns something *truthy* but is itself a Codex-side status (still
        loading, not real data yet) — a plausible real state during the same refresh
        cycle that also finds Claude unonboarded. ``bool(codex_seg)`` alone is True
        here, so a mutant that dropped the ``!= "status"`` conjunct from
        ``claude_onboarding_suppressed`` would suppress the onboarding line in this
        case too, even though Codex has nothing real to show — the first two cases
        alone (hook absent / hook returns None) both leave ``codex_seg`` falsy, so
        neither one reaches that conjunct at all. This case must stay in the loop for
        that reason, not merely for symmetry."""
        for label, install_hook in (
            ("codex_summary hook never set", None),
            ("codex_summary hook returns None", lambda: None),
            ("codex_summary hook returns a Codex-side status (loading), not real data",
             lambda: ("status", "loading")),
        ):
            with self.subTest(case=label):
                text, state = self._harness()
                state["onboard"] = "install"
                if install_hook is not None:
                    state["codex_summary"] = install_hook
                blocks, _width, _height = text()
                pids = dict(blocks)
                self.assertIn(None, pids,
                             "a non-Codex-ready user must still see the onboarding line")
                self.assertIn("ONBOARD-INSTALL-MARK", self._rendered(blocks))
                self.assertEqual(state["summary_status"], "onb_install")
                self.assertNotIn("codex", pids,
                                 "a Codex status segment must not produce its own block")

    def test_scanning_shows_regardless_of_ready_codex(self):
        """Non-overreach: a status other than onb_install/onb_login is never
        suppressed, Codex or not — it means 'something is unresolved with Claude Code
        right now', which has nothing to do with whether Codex is configured.

        The default harness state (no oauth rows, empty stats, no onboarding) already
        falls through ``roam_summary()`` to ``("status", "scanning")``."""
        text, state = self._harness()
        state["codex_summary"] = lambda: ("exact", [("세션", 40.0, False, "in 3h")])
        blocks, _width, _height = text()
        pids = dict(blocks)
        self.assertIn(None, pids, "scanning must not be suppressed by a ready Codex row")
        self.assertIn("SCANNING-MARK", self._rendered(blocks))
        self.assertEqual(state["summary_status"], "scanning")
        self.assertIn("codex", pids)

    def test_token_expired_shows_regardless_of_ready_codex(self):
        """Same non-overreach claim as scanning, for the other non-onboarding status
        this fix must leave untouched: the server rejected the token and the parsed
        window is genuinely empty (``stats["entries"] == 0``)."""
        text, state = self._harness(auth_error=True, stats={"entries": 0})
        state["codex_summary"] = lambda: ("exact", [("세션", 40.0, False, "in 3h")])
        blocks, _width, _height = text()
        pids = dict(blocks)
        self.assertIn(None, pids,
                      "token_expired must not be suppressed by a ready Codex row")
        self.assertIn("TOKEN-EXPIRED-MARK", self._rendered(blocks))
        self.assertEqual(state["summary_status"], "token_expired")
        self.assertIn("codex", pids)


class CompanionGuiOwnershipTests(unittest.TestCase):
    def test_native_menu_validation_preserves_reduce_motion_disabled_item(self):
        # NSMenu performs its own validation when presented. Checking only the
        # setEnabled_ call misses Cocoa re-enabling an item with a valid target.
        import AppKit
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(
            AppKit.NSApplicationActivationPolicyProhibited)
        class QuietCompanionMenuTarget(AppKit.NSObject):
            def toggleRoam_(self, sender):
                pass
        target = QuietCompanionMenuTarget.alloc().init()
        observed = []
        class MenuFactory:
            @staticmethod
            def alloc():
                return AppKit.NSMenu.alloc()
            @staticmethod
            def popUpContextMenu_withEvent_forView_(menu, event, view):
                menu.update()  # Real AppKit validation, with no menu displayed.
                observed.append(bool(menu.itemWithTitle_("menu_roam").isEnabled()))
        state = {"reduce_motion": True}
        scope = {"NSMenu": MenuFactory, "NSMenuItem": AppKit.NSMenuItem,
                 "handler": target, "state": state, "RUNTIME": {"roam": True},
                 "t": lambda key, **kw: key, "discover_pets": lambda: [],
                 "cfg": {}, "APP_VERSION": "test"}
        method = gui_method(self, "PetView", "rightMouseDown_", scope)
        method(None, None)
        state["reduce_motion"] = False
        method(None, None)
        self.assertEqual(observed, [False, True],
                         "native menu validation re-enabled the Reduce Motion-blocked action")

    def test_click_during_auto_away_does_not_persist_automatic_xy(self):
        writes = []
        cfg = {"x": 400.0, "y": 300.0}
        frame = SimpleNamespace(origin=SimpleNamespace(x=550.0, y=450.0),
                                size=SimpleNamespace(width=300.0, height=200.0))
        window = SimpleNamespace(frame=lambda: frame)
        view = SimpleNamespace(window=lambda: window, _moved=False,
                               setNeedsDisplay_=lambda value: None,
                               convertPoint_fromView_=lambda pos, _: pos,
                               btnOrigin=lambda: (1000.0, 1000.0))
        event = SimpleNamespace(clickCount=lambda: 1,
                                locationInWindow=lambda: SimpleNamespace(x=0.0, y=0.0))
        scope = {"state": {"dragging": True, "show_panel": True}, "cfg": cfg,
                 "clear_sticky": lambda: None, "clamp_to_screen": lambda: None,
                 "merge_config_updates": lambda value: writes.append(value),
                 "BTN_R": 8, "set_override": lambda *args, **kwargs: None,
                 "_oauth_cache": {}}
        gui_method(self, "PetView", "mouseUp_", scope)(view, event)
        self.assertEqual(writes, [], "an ordinary click persisted the autonomous position")
        self.assertEqual(cfg, {"x": 400.0, "y": 300.0})


def run_native_smoke():
    """Opt-in real NSWindow render, driven with synthetic time/input and no workers."""
    import contextlib
    import datetime
    import hashlib
    import json
    import os
    import pwd
    import socket
    import sys
    import time
    from PyObjCTools import AppHelper
    import AppKit

    compact_gate = "--compact-presentation-gate" in sys.argv
    artifact_stem = "free-roaming-native-20260909"

    sandbox = Path(os.environ["CLAUDEPET_SMOKE_SANDBOX"]).resolve()
    for key in ("HOME", "TMPDIR", "ZDOTDIR"):
        if not Path(os.environ[key]).resolve().is_relative_to(sandbox):
            raise AssertionError(f"{key} escaped the explicitly created smoke sandbox")
    sys.path.insert(0, str(REPO))
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    forbidden_calls, workers, frames, captures = [], [], [], []
    real_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    forbidden_paths = [real_home / name for name in
                       (".claude", ".claude.json", ".claude_pet.json", ".claude_pet")]

    def audit(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            if any(path == item or path.is_relative_to(item) for item in forbidden_paths):
                forbidden_calls.append("real user input open")
                raise AssertionError("native smoke attempted to open real user input")
        if event in ("socket.connect", "socket.getaddrinfo"):
            forbidden_calls.append(event)
            raise AssertionError("native smoke attempted network access")

    sys.addaudithook(audit)
    import claude_pet as app_module

    def forbidden(name):
        def fail(*args, **kwargs):
            forbidden_calls.append(name)
            raise AssertionError("forbidden native smoke dependency: " + name)
        return fail

    class NoWorker:
        def __init__(self, target=None, *args, **kwargs):
            self.target = target
        def start(self):
            workers.append(getattr(self.target, "__name__", "unknown"))
        def is_alive(self):
            return False

    timers = []
    class NoTimer:
        @staticmethod
        def scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(*args):
            timer = SimpleNamespace(invalidate=lambda: None)
            timers.append(args)
            return timer

    screen = AppKit.NSScreen.mainScreen().visibleFrame()
    clock = {"now": 0.0}
    pointer = {"x": screen.origin.x + screen.size.width - 60.0,
               "y": screen.origin.y + screen.size.height - 20.0}
    settings = {"x": screen.origin.x + 36.0, "y": screen.origin.y + 100.0,
                "scale": 0.5, "roam": True, "greet": False}
    config_writes = []
    summary = {}

    def record_config(updates):
        config_writes.append(dict(updates))
        settings.update(updates)
        return True, dict(settings)

    def loop():
        import inspect
        local = inspect.currentframe().f_back.f_locals
        window, view, state = local["win"], local["view"], local["state"]
        candidates = list(local.values()) + list(state.values())
        roamer = next(value for value in candidates if isinstance(value, app_module.Roamer))
        ticker = state["ticker"]
        # A default-corner trip may never cross a layout threshold. Explicitly
        # begin just below/left of both midpoints, with a far upper-right pointer.
        # This synthetic manual placement is not written to configuration.
        midpoint = (screen.origin.x + screen.size.width / 2,
                    screen.origin.y + screen.size.height / 2)
        initial_center = (midpoint[0] - 40.0, midpoint[1] - 40.0)
        f = window.frame()
        initial_native_size = (float(f.size.width), float(f.size.height))
        window.setFrameOrigin_(AppKit.NSMakePoint(initial_center[0] - f.size.width / 2,
                                                  initial_center[1] - f.size.height / 2))
        roamer.set_home(initial_center, 0.0)
        state["roam_layout"] = None
        summary["layout_midpoint"] = list(midpoint)
        summary["synthetic_initial_center"] = list(initial_center)
        state["override"] = None
        summary["native_window_class"] = str(type(window))
        summary["native_view_class"] = str(type(view))
        summary["runtime_roam_default"] = app_module.RUNTIME.get("roam")
        summary["defaults"] = dict(app_module.ROAM_DEFAULTS)
        summary["initial_roamer_cfg"] = dict(roamer.cfg)
        summary["initial_radius"] = roamer.radius
        summary["visible_screen"] = [float(screen.origin.x), float(screen.origin.y),
                                     float(screen.size.width), float(screen.size.height)]
        started = False
        completed = False
        previous_phase = roamer.phase
        try:
            for index in range(1, 6001):
                clock["now"] = index * 0.05
                pointer["y"] = screen.origin.y + screen.size.height - 20.0 - (20.0 if int(clock["now"]) % 2 else 0.0)
                ticker.tick_(None)
                f = window.frame()
                if roamer.phase == "rest" and not started:
                    initial_native_size = (float(f.size.width), float(f.size.height))
                if compact_gate and roamer.phase == "out":
                    actual_size = (float(f.size.width), float(f.size.height))
                    if not (actual_size[0] < initial_native_size[0]
                            and actual_size[1] < initial_native_size[1]):
                        raise AssertionError(
                            f"travel kept native frame {actual_size}; expected both dimensions "
                            f"smaller than expanded {initial_native_size} on phase {roamer.phase}")
                    if state.get("roam_mode") != "folded":
                        raise AssertionError("travel did not select folded presentation")
                if compact_gate and roamer.phase == "look":
                    if state.get("roam_mode") != "summary":
                        raise AssertionError("approach arrival did not select the usage summary")
                    if not state.get("roam_rects", {}).get("pill"):
                        raise AssertionError("arrival summary has no native pill rectangle")
                    # full and summary are one pill since v0.24, so the arrival window
                    # equals the expanded one; it must still be a crop of the logical window.
                    if f.size.height >= state["roam_env"][1]:
                        raise AssertionError("arrival summary window was not cropped below the logical window height")
                px, py = view.petOrigin()
                sample = {"t": clock["now"], "phase": roamer.phase,
                          "window": [float(f.origin.x), float(f.origin.y),
                                     float(f.size.width), float(f.size.height)],
                          "sprite": [float(f.origin.x + px), float(f.origin.y + f.size.height - py - local["PH"])],
                          "logical_center": list(local["window_center"]()),
                          "mode": state.get("roam_mode"),
                          "crop": state.get("roam_crop"),
                          "pos": [float(value) for value in roamer.pos],
                          "mood": state["mood"]}
                frames.append(sample)
                if roamer.phase != previous_phase:
                    summary.setdefault("transitions", []).append(sample)
                    previous_phase = roamer.phase
                if roamer.phase == "out":
                    if not started:
                        manual_home_at_departure = tuple(roamer.home)
                        summary["manual_home_at_departure"] = list(manual_home_at_departure)
                    started = True
                expected_mood = {"out": "running-right", "look": "review", "rest": "idle" if started else None}.get(roamer.phase)
                if (expected_mood is not None and state["mood"] == expected_mood
                        and not any(item[0] == roamer.phase for item in captures)):
                    view.setNeedsDisplay_(True)
                    view.displayIfNeeded()
                    bitmap = view.bitmapImageRepForCachingDisplayInRect_(view.bounds())
                    view.cacheDisplayInRect_toBitmapImageRep_(view.bounds(), bitmap)
                    captures.append((roamer.phase, bitmap))
                    summary.setdefault("capture_states", []).append(sample)
                if started and roamer.phase == "rest":
                    if not completed:
                        completed = True
                        completed_at = clock["now"]
                        arrival_position = tuple(roamer.pos)
                        if math.dist(arrival_position, manual_home_at_departure) < 60.0:
                            raise AssertionError("arrival returned to the old manual home")
                    if tuple(roamer.pos) != arrival_position or tuple(roamer.home) != manual_home_at_departure:
                        raise AssertionError(f"completed trip drifted/home changed: pos={roamer.pos}, arrival={arrival_position}, home={roamer.home}, departure_home={manual_home_at_departure}, phase={roamer.phase}, t={clock['now']}")
                    if clock["now"] - completed_at >= 10.0:
                        break
            if not started or not completed:
                raise AssertionError("native timer never completed an automatic trip")
            if config_writes:
                raise AssertionError("native automatic ticks wrote application configuration")
            if compact_gate and (state.get("roam_mode") != "full"
                                 or tuple(frames[-1]["window"][2:]) != initial_native_size):
                raise AssertionError("arrival completion did not restore the original expanded presentation")
            # A real native content view is rendered into a contact sheet; the desktop
            # and other applications are never captured.
            width = max(int(bitmap.pixelsWide()) for _, bitmap in captures)
            height = max(int(bitmap.pixelsHigh()) for _, bitmap in captures)
            sheet = AppKit.NSImage.alloc().initWithSize_(AppKit.NSMakeSize(width * len(captures), height))
            sheet.lockFocus()
            try:
                AppKit.NSColor.colorWithCalibratedWhite_alpha_(0.10, 1.0).set()
                AppKit.NSRectFill(AppKit.NSMakeRect(0, 0, width * len(captures), height))
                for index, (_, bitmap) in enumerate(captures):
                    bitmap.drawInRect_(AppKit.NSMakeRect(
                        index * width + (width - bitmap.pixelsWide()) / 2, 0,
                        bitmap.pixelsWide(), bitmap.pixelsHigh()))
            finally:
                sheet.unlockFocus()
            bitmap = AppKit.NSBitmapImageRep.imageRepWithData_(sheet.TIFFRepresentation())
            png = bitmap.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
            if not png.writeToFile_atomically_(str(REPO / "docs-design" / (artifact_stem + ".png")), True):
                raise AssertionError("native PNG write failed")
            summary["capture_column_phases"] = [phase for phase, _ in captures]
        finally:
            window.setReleasedWhenClosed_(False)
            window.orderOut_(None)
            window.close()

    with contextlib.ExitStack() as patches:
        patches.enter_context(mock.patch.object(app_module, "threading", SimpleNamespace(Thread=NoWorker)))
        patches.enter_context(mock.patch.object(AppKit, "NSTimer", NoTimer))
        patches.enter_context(mock.patch.object(AppKit, "NSEvent", SimpleNamespace(
            mouseLocation=lambda: AppKit.NSMakePoint(pointer["x"], pointer["y"]))))
        patches.enter_context(mock.patch.object(time, "monotonic", lambda: clock["now"]))
        patches.enter_context(mock.patch.object(AppHelper, "runEventLoop", loop))
        patches.enter_context(mock.patch.object(app_module, "load_config", lambda: dict(settings)))
        patches.enter_context(mock.patch.object(app_module, "merge_config_updates", record_config))
        patches.enter_context(mock.patch.object(app_module, "seed_bundled_pet_assets", lambda: {}))
        patches.enter_context(mock.patch.object(app_module, "_log_seed_report", lambda value: None))
        for name in ("parse_usage_entries", "compute_usage", "fetch_exact_usage", "fetch_api_cost_today",
                     "poll_github_update", "_read_oauth_token", "_token_from_file", "_token_from_cli",
                     "_keychain_token_native"):
            patches.enter_context(mock.patch.object(app_module, name, forbidden(name)))
        app_module.run_gui()
    end = datetime.datetime.now(datetime.timezone.utc).isoformat()
    window_steps = [math.dist(a["window"][:2], b["window"][:2]) for a, b in zip(frames, frames[1:])]
    sprite_steps = [math.dist(a["sprite"], b["sprite"]) for a, b in zip(frames, frames[1:])]
    model_steps = [math.dist(a["pos"], b["pos"]) for a, b in zip(frames, frames[1:])]
    sprite_extra_steps = [math.hypot((b["sprite"][0] - a["sprite"][0]) - (b["pos"][0] - a["pos"][0]),
                                     (b["sprite"][1] - a["sprite"][1]) - (b["pos"][1] - a["pos"][1]))
                          for a, b in zip(frames, frames[1:])]
    initial_sprite_offset = [frames[0]["sprite"][axis] - frames[0]["pos"][axis] for axis in (0, 1)]
    sprite_anchor_residual = max(abs(sample["sprite"][axis] - sample["pos"][axis]
                                    - initial_sprite_offset[axis])
                                 for sample in frames for axis in (0, 1))
    native_model_residual = max(abs(sample["pos"][axis] -
                                      sample["logical_center"][axis])
                                for sample in frames for axis in (0, 1))
    native_bounds_violations = sum(
        sample["window"][0] < screen.origin.x - 1.0 or
        sample["window"][1] < screen.origin.y - 1.0 or
        sample["window"][0] + sample["window"][2] > screen.origin.x + screen.size.width + 1.0 or
        sample["window"][1] + sample["window"][3] > screen.origin.y + screen.size.height + 1.0
        for sample in frames)
    mid_x, mid_y = summary["layout_midpoint"]
    crossed_x = any(sample["pos"][0] > mid_x for sample in frames)
    crossed_y = any(sample["pos"][1] > mid_y for sample in frames)
    summary.update(crossed_horizontal_midpoint=crossed_x, crossed_vertical_midpoint=crossed_y,
                   max_native_model_axis_residual=native_model_residual,
                   max_sprite_anchor_axis_residual=sprite_anchor_residual,
                   native_visible_bounds_violations=native_bounds_violations,
                   start_utc=start, end_utc=end, measured_utc=end,
                   source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                   grouping_key="manually invoked native Ticker.tick_ callback",
                   sampled_ticks=len(frames), synthetic_time_start=frames[0]["t"],
                   synthetic_time_end=frames[-1]["t"], max_window_step=max(window_steps),
                   max_sprite_step=max(sprite_steps), max_model_step=max(model_steps),
                   max_sprite_displacement_beyond_model=max(sprite_extra_steps), forbidden_calls=forbidden_calls,
                   suppressed_background_workers=workers, config_writes=config_writes,
                   samples=frames)
    (REPO / "docs-design" / (artifact_stem + ".json")).write_text(json.dumps(summary, indent=2))
    print(json.dumps({key: value for key, value in summary.items() if key != "samples"}, indent=2))
    if not crossed_x or not crossed_y:
        raise AssertionError("native continuity smoke did not cross both layout midpoints")
    if native_model_residual > 1.0 + 1e-6 or native_bounds_violations:
        raise AssertionError("native window escaped its model position or visible screen bounds")
    if max(model_steps) > app_module.ROAM_DEFAULTS["walk_speed"] * 0.05 + 1e-6:
        raise AssertionError("motion model exceeded its per-tick speed budget")
    if sprite_anchor_residual > 1.0 + 1e-6:
        raise AssertionError("native sprite anchor jumped relative to the motion model across a crop/layout boundary")


def run_mutation_checks():
    """Reproducible in-memory rival checks; production bytes are never changed."""
    import datetime
    import hashlib
    import io
    import sys
    global SOURCE
    source_path = SOURCE
    baseline = source_path.read_text(encoding="utf-8")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    class TextSource:
        def __init__(self, text):
            self.text = text
        def read_text(self, **kwargs):
            return self.text
        def __str__(self):
            return "<in-memory-quiet-companion-rival>"

    def replace_once(old, new):
        if baseline.count(old) != 1:
            raise AssertionError("mutation anchor no longer occurs exactly once: " + old)
        return baseline.replace(old, new, 1)

    def replace_function(name, statement):
        tree = ast.parse(baseline)
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        if len(nodes) != 1:
            raise AssertionError("mutation function is not unique: " + name)
        nodes[0].body = ast.parse(statement).body
        return ast.unparse(ast.fix_missing_locations(tree))

    cases = [
        ("uncapped elapsed time", "CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time",
         lambda: replace_once('dt = min(max(gap, 0.0), self.cfg["max_dt_s"])', 'dt = max(gap, 0.0)')),
        ("endpoint-only cursor safety", "CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step",
         lambda: replace_function("_roam_seg_dist", "return min(_roam_dist(p, a), _roam_dist(p, b))")),
        ("no geometry clamp", "CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position",
         lambda: replace_function("_roam_clamp", "return (float(p[0]), float(p[1]))")),
        ("no approach cooldown", "CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits",
         lambda: replace_once('self._approach_ok_at = now + self.cfg["approach_cooldown_s"]', 'self._approach_ok_at = now')),
        ("watch never settles", "CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home",
         lambda: replace_once('if now >= self._look_until:', 'if False:')),
    ]
    records = []
    try:
        for name, selected, mutate in cases:
            SOURCE = source_path
            control_stream = io.StringIO()
            control = unittest.TextTestRunner(stream=control_stream, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromName(selected, sys.modules[__name__]))
            if not control.wasSuccessful():
                raise AssertionError("mutation positive control failed: " + control_stream.getvalue())
            SOURCE = TextSource(mutate())
            output = io.StringIO()
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromName(selected, sys.modules[__name__]))
            records.append((name, selected, output.getvalue()))
            if result.wasSuccessful() or result.errors:
                raise AssertionError("rival was not killed by a behavioral assertion: " + name + "\n" + output.getvalue())
    finally:
        SOURCE = source_path
        ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (REPO / "docs-design/free-roaming-verification-20260909.md").open("a") as report:
            report.write("\n## In-memory rival execution\n\nGrouping key: rival implementation paired with its targeted test case. "
                         "File set: tests/test_companion_motion.py and the frozen-in-memory claude_pet.py snapshot. "
                         "Source SHA-256: " + hashlib.sha256(baseline.encode()).hexdigest() + ". "
                         "Window start: " + started + "; end: " + ended + "; measured: " + ended + ". "
                         "Command: `PYTHONDONTWRITEBYTECODE=1 python3 tests/test_companion_motion.py --mutation-check`. "
                         "Each unchanged positive control ran and passed before its rival. "
                         "This is fault-injection evidence, separate from the actual pre-fix RED runs.\n")
            for name, selected, output in records:
                report.write("\nRival: " + name + "; targeted case: `" + selected + "`.\n\n```text\n" + output + "```\n")
    print(f"Killed {len(records)} / {len(cases)} in-memory rivals with behavioral assertion failures; "
          "all targeted unchanged controls passed.")


if __name__ == "__main__":
    import sys
    if "--native-smoke" in sys.argv:
        run_native_smoke()
    elif "--mutation-check" in sys.argv:
        run_mutation_checks()
    else:
        unittest.main()
