"""Independent timed-follow / monitor-jump gates; owned by /root/verifier.

Pure source extraction avoids application import, real configuration and logs.
Geometry/time/selection inputs are stipulated fixtures, not live observations.
"""
import ast
import collections
import inspect
import math
import unittest

from test_companion_motion import pure_api
import test_companion_motion as base_tests


class UnitDraws:
    """Record variable-range uniform calls and map supplied unit fractions."""
    def __init__(self, *units):
        self.units = units or (0.0,)
        self.calls = []

    def uniform(self, low, high):
        if low == high:
            return low
        index = len(self.calls)
        self.calls.append((low, high))
        return low + self.units[min(index, len(self.units) - 1)] * (high - low)


class PlayApiTests(unittest.TestCase):
    def test_production_cadence_duration_and_jump_defaults_match_agreed_contract(self):
        api = pure_api(self)
        expected = {"follow_p": .35, "follow_min_s": 10.0, "follow_max_s": 20.0,
                    "follow_cooldown_s": 420.0, "follow_speed": 45.0,
                    "follow_cross_s": 3.0, "follow_min_left_s": 5.0,
                    "follow_max_jumps": 1, "jump_enabled": True, "jump_p": .5,
                    "jump_cooldown_s": 600.0, "jump_prep_s": .75, "jump_land_s": .5,
                    "jump_tries": 6}
        self.assertEqual({key: api["ROAM_DEFAULTS"].get(key) for key in expected}, expected)

    def test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct(self):
        api = pure_api(self, {"RoamScreen"})
        screen = api["RoamScreen"]("B", (240, -200, 2160, 880), (390, -90, 2010, 770))
        self.assertEqual(screen.id, "B")
        self.assertEqual(tuple(screen.frame), (240, -200, 2160, 880))
        self.assertEqual(tuple(screen.bounds), (390, -90, 2010, 770))

    def test_effect_field_is_appended_with_legacy_five_argument_default(self):
        api = pure_api(self, {"RoamOut"})
        self.assertEqual(api["RoamOut"]._fields, ("pos", "anim", "moved", "away", "phase", "effect"))
        out = api["RoamOut"]((400, 300), None, False, False, "rest")
        self.assertIsNone(out.effect)


class TimedFollowTests(unittest.TestCase):
    bounds = (0.0, 0.0, 1600.0, 1200.0)
    home = (400.0, 300.0)
    initial = 100.0

    def make(self, rng=None, **changes):
        api = pure_api(self)
        cfg = {"rest_min_s": 0.0, "rest_max_s": 0.0,
               "follow_p": 1.0, "follow_min_s": 10.0, "follow_max_s": 20.0,
               "follow_cooldown_s": 420.0, "follow_speed": 45.0,
               "approach_cooldown_s": 100000.0,
               "wander_enabled": False, "jump_enabled": False}
        cfg.update(changes)
        return api["Roamer"](self.home, self.initial, rng=rng or UnitDraws(0.0, 0.3),
                              cfg=cfg, radius=50.0)

    def start(self, **changes):
        r = self.make(**changes)
        r.step(self.initial, (1000.0, 300.0), self.bounds, activity=True)
        return r

    def test_first_ordinary_eligibility_can_select_follow(self):
        r = self.start()
        self.assertEqual(r.phase, "follow", "follow was delayed by an artificial initial cooldown")
        self.assertEqual(r.kind, "follow")

    def test_follow_uses_its_own_speed_and_capped_elapsed_time(self):
        r = self.start()
        out = r.step(100.25, (1000.0, 300.0), self.bounds)
        self.assertEqual(tuple(out.pos), (411.25, 300.0),
                         "follow did not use 45pt/s for the first quarter-second")
        before = tuple(out.pos)
        out = r.step(101.0, (1000.0, 300.0), self.bounds)
        self.assertAlmostEqual(math.dist(before, out.pos), 11.25, places=7,
                               msg="late follow tick used uncapped elapsed time")

    def test_follow_retargets_upward_instead_of_retaining_horizontal_target(self):
        r = self.start()
        first = r.step(100.25, (1000.0, 300.0), self.bounds)
        before = tuple(first.pos)
        out = r.step(100.50, (before[0], 1000.0), self.bounds)
        delta = (out.pos[0] - before[0], out.pos[1] - before[1])
        self.assertEqual(delta, (0.0, 11.25),
                         "latest vertical cursor movement did not replace the old horizontal target")

    def test_duration_endpoints_do_not_finish_early_on_near_target_arrival(self):
        for fraction, duration in ((0.0, 10.0), (1.0, 20.0)):
            with self.subTest(duration=duration):
                r = self.make(rng=UnitDraws(0.0, fraction))
                r.step(100.0, (650.0, 300.0), self.bounds, activity=True)
                for tick in range(1, int(duration * 4)):
                    out = r.step(100.0 + tick * 0.25, (650.0, 300.0), self.bounds)
                self.assertEqual(out.phase, "follow", "near target arrival ended the timed episode early")
                before = tuple(out.pos)
                out = r.step(100.0 + duration, (650.0, 300.0), self.bounds)
                self.assertEqual(out.phase, "look")
                self.assertEqual(r.kind, "follow")
                self.assertEqual(out.anim, "review")
                self.assertEqual(tuple(out.pos), before)

    def test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest(self):
        rng = UnitDraws(0.0, 0.3)  # selected duration = 10 + .3 * 10 = 13 seconds
        r = self.make(rng=rng)
        r.step(100.0, (1100.0, 300.0), self.bounds, activity=True)
        for tick in range(1, 52):
            out = r.step(100.0 + tick * 0.25,
                         (1100.0, 300.0 if tick % 2 else 900.0), self.bounds)
        self.assertEqual(out.phase, "follow")
        out = r.step(113.0, (1100.0, 900.0), self.bounds)
        self.assertEqual(out.phase, "look", "cursor retarget extended the original 13-second deadline")
        self.assertEqual(r.kind, "follow")
        arrived = tuple(out.pos)
        for tick in range(1, 25):
            out = r.step(113.0 + tick * 0.25, (1100.0, 900.0), self.bounds)
        self.assertEqual(out.phase, "rest")
        self.assertTrue(r.settled)
        self.assertEqual(tuple(out.pos), arrived)
        self.assertEqual(tuple(r.home), self.home)
        self.assertEqual(rng.calls, [(0, 1), (10.0, 20.0)],
                         "follow drew random choices during per-tick updates")

    def test_missing_cursor_cancels_in_place_without_claiming_natural_completion(self):
        r = self.start()
        out = r.step(100.25, (1000.0, 300.0), self.bounds)
        before = tuple(out.pos)
        out = r.step(100.50, None, self.bounds)
        self.assertEqual(tuple(out.pos), before, "missing cursor continued an obsolete follow target")
        self.assertEqual(out.phase, "rest")
        self.assertFalse(r.settled, "missing cursor was mislabeled as a ten-second natural episode")

    def test_cursor_entering_clearance_causes_no_new_movement_toward_it(self):
        r = self.start()
        out = r.step(100.25, (1000.0, 300.0), self.bounds)
        before = tuple(out.pos)
        out = r.step(100.50, (before[0] + 1.0, before[1]), self.bounds)
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)
        self.assertEqual(out.phase, "follow")
        self.assertEqual(out.anim, "review")
        # The cursor itself may enter the window radius: no universal distance
        # inequality can survive that external input. The pet must not move in.

    def test_selection_threshold_has_both_follow_and_ordinary_branches(self):
        for choice, expected in ((0.349, "follow"), (0.35, "out"), (0.9, "out")):
            with self.subTest(choice=choice):
                r = self.make(rng=UnitDraws(choice, 0.3), follow_p=0.35)
                out = r.step(100.0, (1000.0, 300.0), self.bounds, activity=True)
                self.assertEqual(out.phase, expected)
                self.assertEqual(r.kind, "follow" if expected == "follow" else "approach")

    def test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts(self):
        r = self.make()
        starts = []
        previous = r.phase
        for tick in range(0, 1681):
            now = 100.0 + tick * 0.25
            out = r.step(now, (1100.0, 600.0), self.bounds, activity=True)
            if out.phase == "follow" and previous != "follow":
                starts.append(now)
            previous = out.phase
        self.assertEqual(starts, [100.0, 520.0],
                         "follow eligibility or its 420-second cooldown is incorrect")

    def test_every_hold_immediately_cancels_follow_without_stale_resume(self):
        for flag, value in (("enabled", False), ("blocked", True),
                            ("busy", True), ("dragging", True)):
            with self.subTest(flag=flag):
                r = self.start(rest_min_s=5.0, rest_max_s=5.0)
                # The new rest fixture starts at105 and then progresses one tick.
                for tick in range(1, 21):
                    r.step(100.0 + tick * 0.25, (1000.0, 300.0), self.bounds, activity=True)
                out = r.step(105.25, (1000.0, 300.0), self.bounds)
                self.assertEqual(out.phase, "follow")
                before = tuple(out.pos)
                out = r.step(105.50, (1000.0, 300.0), self.bounds, **{flag: value})
                self.assertEqual(out.phase, "rest")
                self.assertFalse(r.settled)
                self.assertEqual(tuple(out.pos), before)
                for tick in range(1, 20):
                    out = r.step(105.50 + tick * 0.25, (1000.0, 300.0), self.bounds)
                    self.assertEqual(tuple(out.pos), before)
                    self.assertEqual(out.phase, "rest")


class JumpFixtures(unittest.TestCase):
    """Legacy baseline calls omit its unsupported screens keyword only.

    Screen/effect exports are separately checked strictly by PlayApiTests. This
    compatibility call observes old numeric behavior without altering product
    source or pretending a TypeError is a measured landing-coordinate failure.
    """
    A_FRAME = (-1600.0, 80.0, -160.0, 980.0)
    A_BOUNDS = (-1450.0, 190.0, -310.0, 870.0)
    B_FRAME = (240.0, -200.0, 2160.0, 880.0)
    B_BOUNDS = (390.0, -90.0, 2010.0, 770.0)
    START = (-880.0, 530.0)
    LANDING = (1119.0, 82.0)

    def world(self, **changes):
        tree = ast.parse(base_tests.SOURCE.read_text(encoding="utf-8"))
        declared = any(isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "RoamScreen" for t in n.targets)
            for n in tree.body)
        names = {"Roamer", "RoamOut", "ROAM_DEFAULTS"}
        if declared:
            names.add("RoamScreen")
        api = pure_api(self, names)
        Screen = api.get("RoamScreen", collections.namedtuple("LegacyScreenFixture", "id frame bounds"))
        a = Screen("A", self.A_FRAME, self.A_BOUNDS)
        b = Screen("B", self.B_FRAME, self.B_BOUNDS)
        cfg = {"rest_min_s": 0.0, "rest_max_s": 0.0, "follow_p": 0.0,
               "jump_enabled": True, "jump_p": 1.0, "jump_prep_s": 0.75,
               "jump_land_s": 0.5, "jump_cooldown_s": 600.0,
               "wander_cooldown_s": 300.0, "wander_pause_s": 2.0}
        cfg.update(changes)
        rng = UnitDraws(0.0, 0.0, 0.45, 0.2)
        r = api["Roamer"](self.START, 100.0, rng=rng, cfg=cfg,
                           radius=math.hypot(150.0, 110.0))
        return r, (a, b), rng

    def call(self, r, now, screens, cursor=None, **flags):
        if "screens" in inspect.signature(r.step).parameters:
            flags["screens"] = screens
        return r.step(now, cursor, self.A_BOUNDS, **flags)

    def jump_to_transfer(self, r, screens):
        self.call(r, 100.0, screens)
        self.call(r, 100.25, screens)
        self.call(r, 100.50, screens)
        return self.call(r, 100.75, screens)


class MonitorJumpTests(JumpFixtures):
    def test_inverted_destination_bounds_are_excluded_before_jump_selection(self):
        r, screens, rng = self.world()
        # A100x90 screen cannot contain a300x220 logical window. Its safe
        # center rectangle is inverted in BOTH axes and is not a destination.
        tiny = type(screens[0])("tiny", (1800, -50, 1900, 40), (1950, 60, 1750, -70))
        out = self.call(r, 100.0, (screens[0], tiny))
        self.assertEqual(out.phase, "out", "invalid monitor consumed a jump and began takeoff")
        self.assertIsNone(out.effect)
        self.assertEqual(r.kind, "wander")
        self.assertEqual(rng.calls, [(self.A_BOUNDS[0], self.A_BOUNDS[2]),
                                    (self.A_BOUNDS[1], self.A_BOUNDS[3])])

    def test_jump_probability_has_both_branches_at_the_default_threshold(self):
        for choice, phase in ((.499, "jump"), (.5, "out"), (.9, "out")):
            with self.subTest(choice=choice):
                r, screens, _ = self.world(jump_p=.5)
                r.rng = UnitDraws(choice, 0.0, .45, .2)
                out = self.call(r, 100.0, screens)
                self.assertEqual(out.phase, phase)

    def test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds(self):
        r, screens, _ = self.world(rest_min_s=5.0, rest_max_s=5.0)
        r.set_home(self.LANDING, 100.0)
        out = self.call(r, 100.0, screens)
        self.assertEqual(tuple(out.pos), self.LANDING, "new manual screen was clamped back to legacy A")
        self.assertEqual(getattr(r, "screen", None), "B")
        r.release(101.0, self.START, True)
        out = self.call(r, 101.0, screens)
        self.assertEqual(tuple(out.pos), self.START)
        self.assertEqual(getattr(r, "screen", None), "A")
        self.assertEqual(tuple(r.home), self.START)

    def test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp(self):
        r, screens, rng = self.world()
        out = self.jump_to_transfer(r, screens)
        self.assertEqual(tuple(out.pos), self.LANDING,
                         "monitor jump did not use the independently derived target-screen destination")
        self.assertEqual(getattr(r, "screen", None), "B")
        self.assertEqual(tuple(r.home), self.START)
        self.assertEqual(rng.calls, [(0, 1), (0, 1), (390.0, 2010.0), (-90.0, 770.0)])
        # The legacy bounds argument intentionally remains A after transfer.
        out = self.call(r, 101.0, screens)
        self.assertEqual(tuple(out.pos), self.LANDING, "stale win.screen bounds undid the landing")
        self.assertEqual(getattr(r, "screen", None), "B")

    def test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions(self):
        r, screens, _ = self.world()
        out = self.call(r, 100.0, screens)
        self.assertEqual(out.phase, "jump")
        self.assertEqual(out.anim, "jumping")
        self.assertEqual(out.effect, "takeoff")
        for now in (100.25, 100.50):
            out = self.call(r, now, screens)
            self.assertEqual(tuple(out.pos), self.START)
            self.assertFalse(out.moved)
        out = self.call(r, 100.75, screens)
        self.assertEqual(tuple(out.pos), self.LANDING)
        self.assertTrue(out.moved)
        self.assertEqual(out.effect, "landing")
        self.assertIsNone(out.anim)
        out = self.call(r, 101.25, screens)
        self.assertEqual(out.phase, "look")
        self.assertIsNone(out.effect)
        self.assertEqual(r.kind, "wander")
        for tick in range(1, 9):
            out = self.call(r, 101.25 + tick * 0.25, screens)
        self.assertEqual(out.phase, "rest")
        self.assertTrue(r.settled)
        self.assertEqual(tuple(out.pos), self.LANDING)
        self.assertEqual(tuple(r.home), self.START)

    def test_destination_id_survives_inventory_reordering(self):
        r, screens, _ = self.world()
        self.call(r, 100.0, screens)
        self.call(r, 100.25, screens[::-1])
        self.call(r, 100.50, screens[::-1])
        out = self.call(r, 100.75, screens[::-1])
        self.assertEqual(tuple(out.pos), self.LANDING)
        self.assertEqual(getattr(r, "screen", None), "B")

    def test_missing_or_shrunk_target_cancels_before_transfer(self):
        for change in ("removed", "shrunken"):
            with self.subTest(change=change):
                r, screens, _ = self.world()
                self.call(r, 100.0, screens)
                self.call(r, 100.25, screens)
                if change == "removed":
                    changed = screens[:1]
                else:
                    changed = (screens[0], screens[1]._replace(bounds=(1500, 300, 2010, 770)))
                out = self.call(r, 100.75, changed)
                self.assertEqual(tuple(out.pos), self.START, "jump used an obsolete target screen/rectangle")
                self.assertEqual(out.phase, "rest")
                self.assertFalse(r.settled)
                self.assertIsNone(out.effect)

    def test_cursor_covering_landing_is_rechecked_before_transfer(self):
        r, screens, _ = self.world()
        self.call(r, 100.0, screens)
        self.call(r, 100.25, screens)
        out = self.call(r, 100.75, screens, cursor=self.LANDING)
        self.assertEqual(tuple(out.pos), self.START, "jump transferred the window onto the latest cursor")
        self.assertEqual(out.phase, "rest")
        self.assertFalse(r.settled)
        self.assertIsNone(out.effect)

    def test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume(self):
        for transferred in (False, True):
            for flag, value in (("enabled", False), ("blocked", True),
                                ("busy", True), ("dragging", True)):
                with self.subTest(transferred=transferred, flag=flag):
                    r, screens, _ = self.world(rest_min_s=5.0, rest_max_s=5.0)
                    for tick in range(21):
                        self.call(r, 100.0 + tick * 0.25, screens)
                    if transferred:
                        for now in (105.25, 105.50, 105.75):
                            self.call(r, now, screens)
                    before = self.LANDING if transferred else self.START
                    at = 106.0 if transferred else 105.25
                    out = self.call(r, at, screens, **{flag: value})
                    self.assertEqual(tuple(out.pos), before)
                    self.assertEqual(out.phase, "rest")
                    self.assertFalse(r.settled)
                    self.assertIsNone(out.effect)
                    for tick in range(1, 20):
                        out = self.call(r, at + tick * 0.25, screens)
                        self.assertEqual(tuple(out.pos), before)
                        self.assertEqual(out.phase, "rest")

    def test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws(self):
        for mode in ("single", "off"):
            with self.subTest(mode=mode):
                r, screens, rng = self.world(jump_enabled=(mode != "off"))
                out = self.call(r, 100.0, screens[:1] if mode == "single" else screens)
                self.assertEqual(out.phase, "out")
                self.assertEqual(r.kind, "wander")
                self.assertIsNone(getattr(out, "effect", None))
                self.assertEqual(rng.calls, [(-1450.0, -310.0), (190.0, 870.0)])

    def test_jump_cooldown_starts_after_first_eligible_jump(self):
        r, screens, _ = self.world()
        starts = []
        previous = r.phase
        for tick in range(2401):
            now = 100.0 + tick * 0.25
            out = self.call(r, now, screens)
            if out.phase == "jump" and previous != "jump":
                starts.append(now)
            previous = out.phase
        self.assertEqual(starts, [100.0, 700.0], "jump initial eligibility or 600-second cooldown is incorrect")


class FollowAcrossScreensTests(JumpFixtures):
    def test_cursor_none_cancels_follow_in_both_jump_stages(self):
        for transferred in (False, True):
            with self.subTest(transferred=transferred):
                r, screens = self.prepare_deadline_jump()
                if transferred:
                    self.call(r, 108.75, screens, cursor=(1119.0, 600.0))
                before = tuple(r.pos)
                out = self.call(r, 109.0 if transferred else 108.25, screens, cursor=None)
                self.assertEqual(tuple(out.pos), before)
                self.assertEqual(out.phase, "rest")
                self.assertFalse(r.settled)
                self.assertIsNone(out.effect)

    def follow_world(self, duration=20.0, **changes):
        r, screens, _ = self.world(follow_p=1.0, follow_min_s=duration, follow_max_s=duration,
                                   jump_cooldown_s=0.0, **changes)
        r.rng = UnitDraws(0.0)
        self.call(r, 100.0, screens, cursor=(-450.0, 600.0), activity=True)
        return r, screens

    def advance(self, r, screens, start, end, cursor):
        for tick in range(1, round((end - start) * 4) + 1):
            out = self.call(r, start + tick * 0.25, screens, cursor=cursor)
        return out

    def prepare_deadline_jump(self):
        r, screens = self.follow_world(duration=13.0)
        self.advance(r, screens, 100.0, 104.75, (-450.0, 600.0))
        self.call(r, 105.0, screens, cursor=(1119.0, 600.0))
        out = self.advance(r, screens, 105.0, 108.0, (1119.0, 600.0))
        self.assertEqual(out.phase, "jump")
        return r, screens

    def test_original_follow_deadline_wins_before_late_takeoff_transfer(self):
        r, screens = self.prepare_deadline_jump()
        before = tuple(r.pos)
        # Exactly5s is NOT the gap>5 cancellation branch, but deadline113 is due.
        out = self.call(r, 113.0, screens, cursor=(1119.0, 600.0))
        self.assertEqual(tuple(out.pos), before)
        self.assertFalse(out.moved)
        self.assertEqual(out.phase, "look")
        self.assertEqual(r.kind, "follow")
        self.assertIsNone(out.effect)
        self.assertEqual(getattr(r, "screen", None), "A")

    def test_original_follow_deadline_is_also_checked_during_landing(self):
        r, screens = self.prepare_deadline_jump()
        self.call(r, 108.25, screens, cursor=(1119.0, 600.0))
        out = self.call(r, 112.75, screens, cursor=(1119.0, 600.0))
        self.assertEqual(out.effect, "landing")
        before = tuple(out.pos)
        out = self.call(r, 113.0, screens, cursor=(1119.0, 600.0))
        self.assertEqual(tuple(out.pos), before)
        self.assertEqual(out.phase, "look")
        self.assertIsNone(out.effect)
        self.assertEqual(getattr(r, "screen", None), "B")

    def test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell(self):
        r, screens = self.follow_world()
        self.advance(r, screens, 100.0, 100.75, (-450.0, 600.0))
        self.call(r, 101.0, screens, cursor=self.LANDING)
        self.advance(r, screens, 101.0, 103.25, self.LANDING)
        before = tuple(r.pos)
        out = self.call(r, 103.50, screens, cursor=(220.0, 0.0))
        self.assertEqual(tuple(out.pos), before, "cursor in screen gap was assigned to an expanded safe rectangle")
        self.assertEqual(out.phase, "follow")
        self.call(r, 104.0, screens, cursor=self.LANDING)
        out = self.advance(r, screens, 104.0, 106.75, self.LANDING)
        self.assertEqual(out.phase, "follow", "gap failed to reset the other-screen dwell")
        out = self.call(r, 107.0, screens, cursor=self.LANDING)
        self.assertEqual(out.phase, "jump")

    def test_cross_dwell_restarts_when_foreign_screen_identity_changes(self):
        r, screens = self.follow_world()
        c = type(screens[0])("C", (2500, 300, 4000, 1500), (2650, 410, 3850, 1390))
        screens = screens + (c,)
        self.advance(r, screens, 100.0, 100.75, (-450.0, 600.0))
        self.call(r, 101.0, screens, cursor=self.LANDING)
        self.advance(r, screens, 101.0, 102.75, self.LANDING)
        self.call(r, 103.0, screens, cursor=(3100.0, 800.0))
        self.advance(r, screens, 103.0, 104.75, (3100.0, 800.0))
        out = self.call(r, 105.0, screens, cursor=self.LANDING)
        self.assertEqual(out.phase, "follow", "dwell from B and C was incorrectly combined")
        out = self.advance(r, screens, 105.0, 107.75, self.LANDING)
        self.assertEqual(out.phase, "follow")
        out = self.call(r, 108.0, screens, cursor=self.LANDING)
        self.assertEqual(out.phase, "jump")

    def test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back(self):
        r, screens = self.follow_world()
        self.advance(r, screens, 100.0, 100.75, (-450.0, 600.0))
        self.call(r, 101.0, screens, cursor=self.LANDING)
        out = self.advance(r, screens, 101.0, 104.0, self.LANDING)
        self.assertEqual(out.phase, "jump")
        self.advance(r, screens, 104.0, 105.25, self.LANDING)
        self.assertEqual(r.phase, "follow")
        self.assertEqual(getattr(r, "screen", None), "B")
        for tick in range(1, 59):
            out = self.call(r, 105.25 + tick * 0.25, screens, cursor=(-1200.0, 600.0))
            self.assertNotEqual(out.phase, "jump", "a second jump began in the same follow episode")
        self.assertEqual(out.phase, "follow")
        self.assertEqual(getattr(r, "screen", None), "B", "episode exceeded its one-jump cap despite cooldown0")
        out = self.call(r, 120.0, screens, cursor=(-1200.0, 600.0))
        self.assertEqual(out.phase, "look", "cross-screen jump reset the original follow deadline")
        self.assertEqual(tuple(r.home), self.START)


class PlayPresentationTests(unittest.TestCase):
    def test_follow_travel_folds_and_completion_look_gets_summary(self):
        api = pure_api(self, {"RoamDisplay"})
        for preference in (False, True):
            with self.subTest(preference=preference):
                d = api["RoamDisplay"]()
                d.note("follow", "follow", False)
                self.assertEqual(d.mode("follow", preference), "folded")
                d.note("look", "follow", True)
                self.assertEqual(d.mode("look", preference), "summary")
                d.note("rest", None, True, settled=True)
                self.assertEqual(d.mode("rest", preference), "full" if preference else "folded")


def run_native_play():
    """Real NSWindow/view/adapter, synthetic two-screen inventory and tick inputs.

    This opt-in run is not evidence of OS/hardware multi-monitor operation.
    Only this change's explicitly assigned native JSON/PNG are written.
    """
    import contextlib
    import datetime
    import hashlib
    import json
    import os
    from pathlib import Path
    import sys
    import time
    from types import SimpleNamespace
    from unittest import mock
    import AppKit
    from PyObjCTools import AppHelper

    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    repo = base_tests.REPO
    real_home = Path.home()
    protected = [real_home / name for name in
                 (".claude", ".claude.json", ".claude_pet", ".claude_pet.json")]
    forbidden_calls = []
    def audit(event, args):
        if event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            if any(path == item or path.is_relative_to(item) for item in protected):
                forbidden_calls.append(event)
                raise AssertionError("native play attempted real user data access")
        if event in ("socket.connect", "socket.getaddrinfo"):
            forbidden_calls.append(event)
            raise AssertionError("native play attempted network access")
    sys.addaudithook(audit)
    sys.path.insert(0, str(repo))
    import claude_pet as pet

    def screen(identity, x, y, w, h):
        return SimpleNamespace(deviceDescription=lambda: {"NSScreenNumber": identity},
                               frame=lambda: AppKit.NSMakeRect(x, y, w, h),
                               visibleFrame=lambda: AppKit.NSMakeRect(x, y, w, h))
    source = screen(901, -1600, 80, 1440, 900)
    target = screen(902, 240, -200, 1920, 1080)
    screens = [source, target]
    clock = {"now": 0.0}
    pointer = {"pos": (-5000.0, -5000.0)}
    records, captures, writes = [], [], []
    output = {}

    class NoWorker:
        def __init__(self, *args, **kwargs): pass
        def start(self): pass
        def is_alive(self): return False
    class NoTimer:
        @staticmethod
        def scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(*args):
            return SimpleNamespace(invalidate=lambda: None)

    def loop():
        local = sys._getframe(1).f_locals
        win, view, state = local["win"], local["view"], local["state"]
        r = local["roamer"]
        ticker = state["ticker"]
        state["oauth"] = [("QA Session", 32.0, None, ""), ("QA Weekly", 18.0, None, "")]
        ticker.tick_(None)  # settle the source's initial pill-row resize first
        env = tuple(state["roam_env"])
        output.update(native_window_class=str(type(win)), native_view_class=str(type(view)),
                      logical_environment=env, real_os_screen_count=len(actual_screens),
                      synthetic_screens=[{"id": s.deviceDescription()["NSScreenNumber"],
                                          "frame": [s.frame().origin.x, s.frame().origin.y,
                                                    s.frame().size.width, s.frame().size.height]}
                                         for s in screens])
        r.cfg.update(rest_min_s=0.0, rest_max_s=0.0, follow_p=0.0, jump_p=1.0)
        last_out = {}
        original = r.step
        def observe(*args, **kwargs):
            result = original(*args, **kwargs)
            last_out["value"] = result
            return result
        r.step = observe

        def reset(now):
            clock["now"] = now
            pointer["pos"] = (-5000.0, -5000.0)
            state.update(hover=False, dragging=False, override=None, roam_anim=None,
                         roam_layout=(False, False), menu_open=False, roam_hold=False)
            state["roam_display"].reset()
            r.rng = UnitDraws(0.0, 0.0, 0.45, 0.2)
            r.set_home(JumpFixtures.START, now)
            local["place_window_center"](r.pos)
            local["roam_apply_display"]("rest")
            state["override"] = None

        def tick(now, label=None):
            clock["now"] = now
            ticker.tick_(None)
            out = last_out["value"]
            f = win.frame()
            center = local["window_center"]()
            px, py = view.petOrigin()
            record = dict(t=now, phase=out.phase, effect=out.effect, screen=r.screen,
                          pos=list(r.pos), home=list(r.home), center=list(center),
                          frame=[f.origin.x, f.origin.y, f.size.width, f.size.height],
                          sprite=[f.origin.x + px, f.origin.y + f.size.height - py],
                          alpha=float(win.alphaValue()), mode=state.get("roam_mode"),
                          mood=state["mood"], label=label)
            records.append(record)
            if math.dist(center, r.pos) > 1.5:
                raise AssertionError("native frame disagrees with selected-screen model: " + repr(record))
            selected = next(s for s in screens if s.deviceDescription()["NSScreenNumber"] == r.screen)
            vf = selected.visibleFrame()
            x, y = center[0] - env[0] / 2, center[1] - env[1] / 2
            if not (vf.origin.x - 1 <= x and x + env[0] <= vf.origin.x + vf.size.width + 1
                    and vf.origin.y - 1 <= y and y + env[1] <= vf.origin.y + vf.size.height + 1):
                raise AssertionError("native logical envelope escaped selected screen: " + repr(record))
            if label:
                view.displayIfNeeded()
                bitmap = view.bitmapImageRepForCachingDisplayInRect_(view.bounds())
                view.cacheDisplayInRect_toBitmapImageRep_(view.bounds(), bitmap)
                captures.append((label, bitmap))
            return record
        try:
            reset(1.0)
            for i in range(71):
                t = 1.0 + i * 0.05
                tick(t, {3: "takeoff", 17: "landing", 29: "wander-look", 69: "rest"}.get(i))
            target_bounds = (240 + env[0] / 2, -200 + env[1] / 2,
                             2160 - env[0] / 2, 880 - env[1] / 2)
            expected = (target_bounds[0] + .45 * (target_bounds[2] - target_bounds[0]),
                        target_bounds[1] + .2 * (target_bounds[3] - target_bounds[1]))
            output["independent_landing"] = expected
            if r.screen != 902 or math.dist(r.pos, expected) > 1e-8:
                raise AssertionError("native jump destination/target screen mismatch")
            if r.phase != "rest" or state["roam_mode"] != "full":
                raise AssertionError("natural jump completion failed to restore full display")
            if any(record["pos"] not in [list(JumpFixtures.START), list(expected)] for record in records):
                raise AssertionError("jump interpolated a position between screens")
            if min(record["alpha"] for record in records) > .25:
                raise AssertionError("native window never faded for jump")
            for transferred in (False, True):
                base = 1000.0 if not transferred else 2000.0
                reset(base)
                tick(base)
                for i in range(1, 4 if not transferred else 18):
                    tick(base + i * .05)
                before = tuple(r.pos)
                current = win.frame()
                pointer["pos"] = (current.origin.x + current.size.width / 2,
                                  current.origin.y + current.size.height / 2)
                row = tick(base + (.25 if not transferred else .9))
                if r.phase != "rest" or tuple(r.pos) != before or abs(row["alpha"] - 1) > 1e-8:
                    raise AssertionError("hover failed to cancel jump and restore native opacity")
            if writes:
                raise AssertionError("automatic native jump persisted configuration")
            width = max(int(rep.pixelsWide()) for _, rep in captures)
            height = max(int(rep.pixelsHigh()) for _, rep in captures)
            sheet = AppKit.NSImage.alloc().initWithSize_(AppKit.NSMakeSize(width * len(captures), height))
            sheet.lockFocus()
            try:
                AppKit.NSColor.colorWithCalibratedWhite_alpha_(.12, 1).set()
                AppKit.NSRectFill(AppKit.NSMakeRect(0, 0, width * len(captures), height))
                for i, (_, rep) in enumerate(captures):
                    rep.drawInRect_(AppKit.NSMakeRect(i * width, 0, rep.pixelsWide(), rep.pixelsHigh()))
            finally:
                sheet.unlockFocus()
            rep = AppKit.NSBitmapImageRep.imageRepWithData_(sheet.TIFFRepresentation())
            png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
            assert png.writeToFile_atomically_(str(repo / "docs-design/companion-play-native-20260909.png"), True)
        finally:
            win.setReleasedWhenClosed_(False)
            win.orderOut_(None)
            win.close()

    actual_screens = list(AppKit.NSScreen.screens())
    with contextlib.ExitStack() as patches:
        patch = lambda obj, name, value: patches.enter_context(mock.patch.object(obj, name, value))
        patch(AppKit, "NSScreen", SimpleNamespace(screens=lambda: screens, mainScreen=lambda: source))
        patch(AppKit, "NSTimer", NoTimer)
        patch(AppKit, "NSEvent", SimpleNamespace(mouseLocation=lambda: AppKit.NSMakePoint(*pointer["pos"])))
        patch(pet, "threading", SimpleNamespace(Thread=NoWorker))
        patch(time, "monotonic", lambda: clock["now"])
        patch(AppHelper, "runEventLoop", loop)
        patch(pet, "load_config", lambda: {"x": -1014, "y": 410, "scale": .5, "roam": True, "greet": False})
        patch(pet, "merge_config_updates", lambda values: writes.append(values))
        patch(pet, "seed_bundled_pet_assets", lambda: {})
        patch(pet, "_log_seed_report", lambda report: None)
        patch(pet, "discover_pets", lambda: [{"id": "default", "name": "QA cat", "dir": pet.PET_DIR}])
        pet.run_gui()
    output.update(source_sha256=hashlib.sha256((repo / "claude_pet.py").read_bytes()).hexdigest(),
                  start_utc=start, end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  scope="real AppKit window/render/adapter; synthetic screen inventory/time/cursor; no hardware transit claim",
                  samples=records, sample_count=len(records), config_writes=writes,
                  forbidden_calls=forbidden_calls, capture_columns=[name for name, _ in captures])
    (repo / "docs-design/companion-play-native-20260909.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "samples"}, indent=2))


if __name__ == "__main__":
    import sys
    if "--native-play" in sys.argv:
        run_native_play()
    else:
        unittest.main()
