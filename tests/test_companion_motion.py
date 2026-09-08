"""Independent quiet-companion gates.

Owner: Verifier /root/verifier. Default unit tests use synthetic geometry/time
and compile only approved pure definitions or isolated GUI methods. The opt-in
native smoke imports the source app inside its explicit I/O-isolated fixture.

Rivals: absent/unwired API; move before rest; follow every cursor update;
uncapped delayed tick; disabled movement; stale pre-drag origin; wander with
no pause. Geometry/suppression integration gates are added after the contract
has been acknowledged, and any missing red evidence remains explicitly open.
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
                         ("pos", "anim", "moved", "away", "phase"))
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
                          cfg={"rest_min_s": 10.0, "rest_max_s": 10.0})
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
        cfg = {"rest_min_s": 10.0, "rest_max_s": 10.0,
               "approach_cooldown_s": 0.0, "wander_cooldown_s": 100000.0,
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

    def test_disabled_during_return_does_not_snap_to_manual_home(self):
        r, now = self.depart()
        for tick in range(1, 200):
            now = 10.0 + tick * 0.25
            out = r.step(now, self.cursor, self.bounds)
            if out.phase == "home":
                break
        self.assertEqual(out.phase, "home", "trip never entered return phase")
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

    def test_cursor_on_return_segment_also_cancels(self):
        r, now = self.depart(radius=50.0)
        for tick in range(1, 200):
            now = 10.0 + tick * 0.25
            out = r.step(now, self.cursor, self.bounds)
            if out.phase == "home":
                break
        self.assertEqual(out.phase, "home")
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
            if out.phase == "out" and previous != "out" and r.kind == "approach":
                departures.append(now)
            previous = out.phase
        self.assertGreaterEqual(len(departures), 2,
                                "continuous input must not perpetually push back eligibility")
        for previous, current in zip(departures, departures[1:]):
            self.assertGreaterEqual(current - previous, 180.0)

    def test_wander_is_bounded_pauses_quietly_returns_and_respects_own_cooldown(self):
        r = self.make(wander_cooldown_s=300.0, wander_radius=160.0)
        departures = []
        saw_pause = False
        previous = r.phase
        for tick in range(0, 1441):
            now = tick * 0.25
            out = r.step(now, None, self.bounds)
            self.assertLessEqual(math.dist(self.home, out.pos), 160.0)
            if out.phase == "out" and previous != "out" and r.kind == "wander":
                departures.append(now)
            if out.phase == "look":
                self.assertIsNone(out.anim)
                saw_pause = True
            previous = out.phase
        self.assertTrue(saw_pause, "wander never had its quiet pause")
        self.assertGreaterEqual(len(departures), 2)
        for first, second in zip(departures, departures[1:]):
            self.assertGreaterEqual(second - first, 300.0)

    def test_hold_on_every_trip_phase_freezes_look_and_return_too(self):
        for wanted in ("look", "home"):
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


def fake_rect(x, y, width, height):
    return SimpleNamespace(origin=SimpleNamespace(x=float(x), y=float(y)),
                           size=SimpleNamespace(width=float(width), height=float(height)))


class CompanionPresentationTests(unittest.TestCase):
    """User-derived presentation gates, authored before the compact implementation."""
    def display(self):
        return pure_api(self, {"RoamDisplay"})["RoamDisplay"]()

    def test_departure_and_return_fold_even_before_any_displacement(self):
        for preference in (False, True):
            for phase, kind, away in (("out", "approach", False),
                                      ("out", "wander", False),
                                      ("home", None, True)):
                with self.subTest(preference=preference, phase=phase, kind=kind):
                    d = self.display()
                    d.note(phase, kind, away)
                    self.assertEqual(d.mode(phase, preference), "folded")

    def test_approach_summary_expansion_does_not_replace_manual_preference(self):
        for preference in (False, True):
            for away in (False, True):
                with self.subTest(preference=preference, away=away):
                    d = self.display()
                    d.note("look", "approach", away)
                    self.assertEqual(d.mode("look", preference), "summary")
                    self.assertEqual(d.toggle(preference), preference)
                    self.assertEqual(d.mode("look", preference), "full")
                    self.assertEqual(d.toggle(preference), preference)
                    self.assertEqual(d.mode("look", preference), "summary")
                    d.note("home", None, True)
                    self.assertEqual(d.mode("home", preference), "folded")
                    d.note("rest", None, False)
                    self.assertEqual(d.mode("rest", preference),
                                     "full" if preference else "folded")

    def test_wander_pause_stays_folded_and_return_restores_manual_choice(self):
        for preference in (False, True):
            d = self.display()
            d.note("out", "wander", False)
            d.note("look", "wander", True)
            self.assertEqual(d.mode("look", preference), "folded")
            d.note("home", None, True)
            d.note("rest", None, False)
            self.assertEqual(d.mode("rest", preference),
                             "full" if preference else "folded")

    def test_hover_stop_away_keeps_summary_available_for_expansion(self):
        d = self.display()
        d.note("look", "approach", True)
        d.note("rest", None, True)  # ordinary hover stops motion; not explicit interruption
        self.assertEqual(d.mode("rest", False), "summary")
        self.assertFalse(d.toggle(False))
        self.assertEqual(d.mode("rest", False), "full")

    def test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry(self):
        api = pure_api(self, {"RoamDisplay", "Roamer"})
        for hover_stop in (False, True):
            with self.subTest(hover_stop=hover_stop):
                d = api["RoamDisplay"]()
                r = api["Roamer"]((400, 300), 0, rng=MinimumRng(),
                                  cfg={"rest_min_s": 0, "rest_max_s": 0,
                                       "wander_radius": 0, "look_s": 6})
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
                          cfg={"rest_min_s": 0, "rest_max_s": 0, "wander_radius": 0})
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
        self.assertFalse(d.toggle(False))
        self.assertEqual(d.mode(r.phase, False), "full")
        r.set_home((420, 360), 1.3)
        self.assertTrue(r.settled)
        d.reset()
        self.assertEqual(d.mode(r.phase, False), "folded")

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
                         ("cost", 0.0))
        self.assertEqual(self.summary(mode="api", has_admin_key=True, cost_today=12.375,
                                      oauth=[("Weekly", 87.0, None)]),
                         ("cost", 12.375))

    def test_summary_keeps_first_two_source_labels_and_values_in_order(self):
        rows = [("Current session", 17.25, None), ("週間", 63.5, None),
                ("Fable", 91.0, None)]
        self.assertEqual(self.summary(oauth=rows),
                         ("exact", [("Current session", 17.25), ("週間", 63.5)]))

    def test_summary_onboarding_and_estimates_preserve_data_meaning(self):
        self.assertEqual(self.summary(onboard="install"), ("status", "onb_install"))
        self.assertEqual(self.summary(onboard="login"), ("status", "onb_login"))
        self.assertEqual(self.summary(stats={"session": {"pct": 0.0},
                                             "weekly": {"pct": 67.5}}),
                         ("estimate", [("session", 0.0), ("weekly", 67.5)]))

    def test_summary_invalid_values_are_not_reported_as_zero(self):
        for invalid in (None, True, False, -1.0, float("nan"), float("inf"), "32"):
            with self.subTest(invalid=repr(invalid)):
                self.assertEqual(self.summary(mode="api", has_admin_key=True,
                                              cost_today=invalid), ("status", "loading"))
                self.assertEqual(self.summary(stats={"session": {"pct": invalid},
                                                     "weekly": {"pct": 23.75}}),
                                 ("estimate", [("weekly", 23.75)]))
                self.assertEqual(self.summary(oauth=[("Session", invalid, None)],
                                              stats={"session": {"pct": 99.0}}),
                                 ("status", "scanning"))

    def test_exact_summary_filters_only_first_two_rows_without_replacement(self):
        rows = [("Session", float("nan"), None), ("週間", 41.0, None),
                ("Fable", 93.0, None)]
        self.assertEqual(self.summary(oauth=rows), ("exact", [("週間", 41.0)]))

    def test_server_label_matching_translation_key_remains_an_exact_label(self):
        self.assertEqual(self.summary(oauth=[("session", 18.25, None)]),
                         ("exact", [("session", 18.25)]))
        self.assertEqual(self.summary(stats={"session": {"pct": 18.25}}),
                         ("estimate", [("session", 18.25)]))


class CompanionCropGeometryTests(unittest.TestCase):
    """Asymmetric negative-screen fixtures derived from anchor preservation."""
    def api(self):
        return pure_api(self, {"roam_frame", "roam_logical_center", "roam_pill_rect"})

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
            for mode, expected_crop, expected_origin in (
                    ("full", (0, 0, 300, 220), (center[0] - 150, center[1] - 110)),
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

    def test_native_compact_size_includes_button_but_not_full_panel_hitbox(self):
        api = self.api()
        f = api["roam_frame"]((650, 430), "folded", False, False,
                               300, 220, 80, 60, 152, 0.5)
        self.assertEqual(tuple(f["size"]), (112, 64))
        self.assertEqual(tuple(f["sprite"]), (2, 2, 80, 60))
        self.assertEqual(tuple(f["button"]), (84, 15, 26, 26))

    def test_summary_text_width_is_bounded_and_origin_uses_same_side(self):
        api = self.api()
        for right, expected_x in ((False, 4), (True, 140)):
            for bottom, expected_y in ((False, 66), (True, 126)):
                with self.subTest(right=right, bottom=bottom):
                    self.assertEqual(tuple(api["roam_pill_rect"](
                        "summary", right, bottom, 300, 80, 60, 152, text_w=130)),
                        (expected_x, expected_y, 156, 30))
        long_pill = api["roam_pill_rect"]("summary", True, False,
                                           300, 80, 60, 152, text_w=900)
        self.assertEqual(tuple(long_pill), (36, 66, 260, 30))
        self.assertIsNone(api["roam_pill_rect"]("folded", False, True,
                                               300, 80, 60, 152))

    def test_uncropped_window_logical_center_remains_native_center(self):
        api = self.api()
        self.assertEqual(tuple(api["roam_logical_center"]((-1200, 360), (300, 220),
                                                          None, (300, 220))),
                         (-1050, 470))


class CompanionAdapterTests(unittest.TestCase):
    def setup_adapter(self):
        api = pure_api(self)
        roamer = api["Roamer"]((800.0, 300.0), 0.0, rng=MinimumRng(),
                    cfg={"rest_min_s": 10.0, "rest_max_s": 10.0,
                         "approach_cooldown_s": 0.0, "wander_radius": 0.0,
                         "walk_speed": 40.0})
        world = {"screen": fake_rect(0, 0, 1000, 700), "frame": fake_rect(750, 250, 100, 100),
                 "now": 10.0, "moves": []}
        screen = SimpleNamespace(visibleFrame=lambda: world["screen"], frame=lambda: world["screen"])
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
        api = pure_api(self, {"Roamer", "RoamDisplay", "roam_frame"})
        world = {"frame": fake_rect(270, 240, 300, 220), "now": 0.1, "writes": []}
        screen = SimpleNamespace(visibleFrame=lambda: fake_rect(0, 0, 1400, 1000))
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
                           cfg={"rest_min_s": 0, "rest_max_s": 0, "wander_radius": 0})
        r.step(0, (1200, 350), (150, 110, 1250, 890), activity=True)
        self.assertEqual(r.phase, "out")
        scope = dict(api, win=win, view=view, state=state, roamer=r, ui={}, math=math,
                     RUNTIME={"roam": True}, _time=SimpleNamespace(monotonic=lambda: world["now"]),
                     roam_clock={"rm_at": 0}, _reduce_motion=lambda: False,
                     NSScreen=SimpleNamespace(screens=lambda: [screen], mainScreen=lambda: screen),
                     NSEvent=SimpleNamespace(mouseLocation=lambda: SimpleNamespace(x=1200, y=350)),
                     NSMakeRect=fake_rect, NSMakePoint=lambda x, y: SimpleNamespace(x=x, y=y),
                     PW=80, PH=60, W=300, H=220, g={"scale": 0.5}, pill_h=lambda: 152,
                     roam_summary_text=lambda: ("", 130), spike_info=lambda stats: None,
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
        self.assertEqual((f.size.width, f.size.height), (300, 220))

    def test_actual_summary_formatter_distinguishes_estimate_from_exact(self):
        api = pure_api(self, {"roam_summary", "roam_summary_line"})
        state = {"oauth": None, "stats": {"session": {"pct": 42}, "weekly": {"pct": 17}},
                 "cost": None}
        scope = dict(api, state=state, RUNTIME={"mode": "sub"}, F_SUMMARY=None,
                     t=lambda key: {"session": "세션", "weekly": "주간"}.get(key, key),
                     astr=lambda text, font: SimpleNamespace(size=lambda: SimpleNamespace(width=len(text))))
        gui_functions(self, ("roam_summary_text",), scope)
        self.assertEqual(scope["roam_summary_text"]()[0], "세션 ≈42% · 주간 ≈17%")
        state["oauth"] = [("session", 42, None), ("주간", 17, None)]
        self.assertEqual(scope["roam_summary_text"]()[0], "session 42% · 주간 17%")

    def test_actual_summary_draw_keeps_long_text_inside_pill_padding(self):
        draws = []
        text = "A server-provided usage label that exceeds the small summary pill 42%"
        def astr(value, font):
            width = sum(10 if char.isupper() else 7 for char in value)
            return SimpleNamespace(size=lambda: SimpleNamespace(width=width, height=13),
                    drawAtPoint_=lambda p: draws.append((value, p.x, p.x + width)))
        api = pure_api(self, {"roam_summary", "roam_fit_text"})
        scope = dict(api, state={"roam_rects": {"pill": (4, 66, 260, 30)}},
                     roam_summary_text=lambda: (text, astr(text, None).size().width),
                     astr=astr, F_SUMMARY=None, PILL_PAD=13,
                     C_PILL=SimpleNamespace(set=lambda: None), NSMakeRect=fake_rect,
                     NSMakePoint=lambda x, y: SimpleNamespace(x=x, y=y),
                     NSBezierPath=SimpleNamespace(bezierPathWithRoundedRect_xRadius_yRadius_=
                                                 lambda *args: SimpleNamespace(fill=lambda: None)))
        gui_functions(self, ("draw_summary_pill",), scope)
        scope["draw_summary_pill"]()
        self.assertEqual(len(draws), 1)
        self.assertGreaterEqual(draws[0][1], 17, "summary text overflows the pill's left padding")
        self.assertLessEqual(draws[0][2], 251, "summary text overflows the pill's right padding")

    def test_fit_contract_uses_measured_longest_prefix_and_tiny_width(self):
        api = pure_api(self, {"roam_fit_text", "roam_summary_line", "SUMMARY_APPROX"})
        fit = api["roam_fit_text"]
        measure = lambda value: sum({"W": 10, "i": 2, "…": 5}.get(c, 6) for c in value)
        self.assertEqual(fit("WiWi", 24, measure), "WiWi")
        self.assertEqual(fit("WiWi", 23, measure), "Wi…")
        self.assertEqual(fit("WiWi", 5, measure), "…")
        self.assertEqual(fit("WiWi", 4, measure), "")
        self.assertEqual(fit("", 0, measure), "")
        self.assertEqual(api["roam_summary_line"]("estimate", [("session", 42)],
                                                 lambda key: "세션"), "세션 ≈42%")
        self.assertEqual(api["roam_summary_line"]("exact", [("session", 42)],
                                                 lambda key: "세션"), "session 42%")


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
    artifact_stem = "quiet-companion-compact-smoke" if compact_gate else "quiet-companion-smoke"

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
                if compact_gate and roamer.phase in ("out", "home"):
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
                    if f.size.height >= initial_native_size[1]:
                        raise AssertionError("arrival summary kept the full panel height")
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
                    started = True
                expected_mood = {"out": "running-right", "look": "review", "home": "running-left"}.get(roamer.phase)
                if (expected_mood is not None and state["mood"] == expected_mood
                        and not any(item[0] == roamer.phase for item in captures)):
                    view.setNeedsDisplay_(True)
                    view.displayIfNeeded()
                    bitmap = view.bitmapImageRepForCachingDisplayInRect_(view.bounds())
                    view.cacheDisplayInRect_toBitmapImageRep_(view.bounds(), bitmap)
                    captures.append((roamer.phase, bitmap))
                    summary.setdefault("capture_states", []).append(sample)
                if started and roamer.phase == "rest":
                    completed = True
                    break
            if not started or not completed:
                raise AssertionError("native timer never completed an automatic trip")
            if config_writes:
                raise AssertionError("native automatic ticks wrote application configuration")
            if compact_gate and (state.get("roam_mode") != "full"
                                 or tuple(frames[-1]["window"][2:]) != initial_native_size):
                raise AssertionError("return did not restore the original expanded presentation")
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
        ("watch never returns home", "CompanionMotionTests.test_disabled_during_return_does_not_snap_to_manual_home",
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
        with (REPO / "docs-design/quiet-companion-verification.md").open("a") as report:
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
