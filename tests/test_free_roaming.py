"""Independent free-roaming gates; Verifier /root/verifier only.

Desired behavior: random destinations across the visible monitor's safe center
rectangle, then rest at that destination. Only manual placement is persisted.
These tests compile pure definitions; no GUI, user data, config, or workers run.
"""
import math
import unittest

from test_companion_motion import MinimumRng, pure_api


class FractionRng:
    """A supplied unit draw scales into each requested interval; fixed rest is free."""
    def __init__(self, fractions):
        self.fractions = iter(fractions)
        self.calls = []

    def uniform(self, low, high):
        if low == high:
            return low
        self.calls.append((low, high))
        fraction = next(self.fractions)
        return low + fraction * (high - low)


class FreeRoamingSamplingTests(unittest.TestCase):
    def make(self, start, fractions, radius=0.0):
        api = pure_api(self)
        rng = FractionRng(fractions)
        r = api["Roamer"](start, 0, rng=rng, radius=radius, cfg={
            "follow_p": 0.0, "jump_enabled": False,
            "rest_min_s": 0, "rest_max_s": 0, "wander_enabled": True,
            "wander_tries": 6, "walk_speed": 100})
        return r, rng

    def destination(self, r, bounds, cursor=None):
        out = r.step(0, cursor, bounds)
        self.assertEqual(out.phase, "out")
        for tick in range(1, 401):
            out = r.step(tick * 0.25, cursor, bounds)
            if out.phase == "look":
                return tuple(out.pos)
        self.fail("sampled destination was never reached")

    def test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk(self):
        bounds = (-1770.0, 190.0, -470.0, 970.0)
        for fractions, expected in (((0.8, 0.25), (-730.0, 385.0)),
                                    ((0.0, 0.0), (-1770.0, 190.0)),
                                    ((1.0, 1.0), (-470.0, 970.0))):
            with self.subTest(draws=fractions):
                r, rng = self.make((-1680.0, 880.0), fractions)
                actual = self.destination(r, bounds)
                self.assertEqual(actual, expected,
                                 "wander did not sample the whole safe center rectangle")
                self.assertEqual(rng.calls, [(-1770.0, -470.0), (190.0, 970.0)])
                self.assertEqual(tuple(r.home), (-1680.0, 880.0))
                self.assertGreater(math.dist(actual, r.home), 360)

    def test_retries_reject_short_endpoint_and_crossing_candidates_before_departure(self):
        bounds = (100.0, 100.0, 1500.0, 900.0)
        # Candidates: (210,310) is too short; (820,510) overlaps pointer
        # clearance; (1400,700) crosses pointer(800,500); (1400,150) is safe.
        fractions = (110 / 1400, 210 / 800, 720 / 1400, 410 / 800,
                     1300 / 1400, 600 / 800, 1300 / 1400, 50 / 800)
        r, rng = self.make((200.0, 300.0), fractions, radius=60)
        target = self.destination(r, bounds, cursor=(800.0, 500.0))
        self.assertEqual(target, (1400.0, 150.0),
                         "unsafe candidate was used instead of retrying with the same bounds")
        self.assertEqual(rng.calls, [(100.0, 1500.0), (100.0, 900.0)] * 4)

    def test_six_invalid_candidates_stop_retrying_without_motion_or_return(self):
        r, rng = self.make((200.0, 300.0), (100 / 1400, 200 / 800) * 6)
        out = r.step(0, None, (100.0, 100.0, 1500.0, 900.0))
        self.assertEqual(out.phase, "rest", "exhausted random search started an unintended trip")
        self.assertFalse(out.moved)
        self.assertEqual(tuple(out.pos), (200.0, 300.0))
        self.assertEqual(rng.calls, [(100.0, 1500.0), (100.0, 900.0)] * 6)


class FreeRoamingCompletionTests(unittest.TestCase):
    bounds = (-1700.0, 100.0, -100.0, 1000.0)
    start = (-1500.0, 700.0)
    cursor = (-750.0, 700.0)

    def make(self, wander=False):
        api = pure_api(self, {"Roamer", "RoamDisplay"})
        r = api["Roamer"](self.start, 0, rng=MinimumRng(), cfg={
            "follow_p": 0.0, "jump_enabled": False,
            "rest_min_s": 10.0, "rest_max_s": 10.0,
            "approach_cooldown_s": 180.0, "wander_cooldown_s": 300.0,
            "wander_enabled": wander,
            "walk_speed": 100.0, "look_s": 2.0, "wander_pause_s": 1.0})
        for now in range(10):
            r.step(now, None, self.bounds)
        out = r.step(10, None if wander else self.cursor, self.bounds,
                     activity=not wander)
        self.assertEqual(out.phase, "out")
        self.assertEqual(r.kind, "wander" if wander else "approach")
        return api, r

    def arrive(self, r, cursor):
        for tick in range(1, 301):
            now = 10 + tick * 0.25
            out = r.step(now, cursor, self.bounds)
            if out.phase == "look":
                self.assertGreater(math.dist(out.pos, self.start), 50)
                return now, tuple(out.pos)
        self.fail("the planned trip never reached its quiet destination pause")

    def test_approach_and_wander_finish_at_their_destination_without_return(self):
        for wander in (False, True):
            with self.subTest(kind="wander" if wander else "approach"):
                _, r = self.make(wander)
                cursor = None if wander else self.cursor
                arrived, destination = self.arrive(r, cursor)
                self.assertEqual(tuple(r.home), self.start,
                                 "automatic arrival replaced the saved manual-placement reference")
                pause = 1.0 if wander else 2.0
                for tick in range(1, int(pause * 4)):
                    out = r.step(arrived + tick * 0.25, cursor, self.bounds)
                    self.assertEqual(out.phase, "look")
                    self.assertEqual(tuple(out.pos), destination)
                out = r.step(arrived + pause, cursor, self.bounds)
                self.assertEqual(out.phase, "rest", "arrival pause started an unwanted return leg")
                self.assertEqual(tuple(out.pos), destination)
                self.assertTrue(r.settled)
                self.assertEqual(tuple(r.home), self.start)
                for tick in range(1, 40):
                    out = r.step(arrived + pause + tick * 0.25, cursor, self.bounds)
                    self.assertEqual(tuple(out.pos), destination)
                    self.assertFalse(out.moved)
                    self.assertEqual(out.phase, "rest")

    def test_interrupted_trip_does_not_fall_back_to_old_manual_home(self):
        _, r = self.make()
        r.step(10.25, self.cursor, self.bounds)
        r.step(10.5, self.cursor, self.bounds)
        stopped = tuple(r.pos)
        self.assertEqual(stopped, (-1450.0, 700.0))
        out = r.step(10.75, self.cursor, self.bounds, busy=True)
        self.assertEqual(tuple(out.pos), stopped)
        for tick in range(1, 45):
            out = r.step(10.75 + tick * 0.25, self.cursor, self.bounds)
            self.assertEqual(out.phase, "rest", "idle fallback resumed travel toward the old home")
            self.assertEqual(tuple(out.pos), stopped)
            self.assertFalse(out.moved)

    def test_natural_away_completion_restores_preference_but_hover_keeps_summary(self):
        api = pure_api(self, {"RoamDisplay"})
        for preference in (False, True):
            for natural in (False, True):
                with self.subTest(preference=preference, natural=natural):
                    display = api["RoamDisplay"]()
                    display.note("look", "approach", True, settled=False)
                    self.assertEqual(display.mode("look", preference), "summary")
                    display.note("rest", None, True, settled=natural)
                    expected = ("full" if preference else "folded") if natural else "summary"
                    self.assertEqual(display.mode("rest", preference), expected,
                                     "display confused natural completion away from home with hover")


if __name__ == "__main__":
    unittest.main()
