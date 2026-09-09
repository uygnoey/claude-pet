# Free-roaming verification — 2026-09-09

Status: PASS. Final source `f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a` passed 454 discovered tests (447 passed, seven existing opt-in skips), final native geometry/render checks, and real-time GUI samples described below. Baseline behavioral RED and the native fixture-reference failure are retained. No production file was edited by this Verifier.

Roles: user-designated Claude is Developer; `/root/verifier` owns these gates and
has edited no production file; `/root` coordinates; `/root/reviewer` reviews.

Assigned files: new `tests/test_free_roaming.py` and this report; tracked
`tests/test_companion_motion.py` and the reviewed app hash pins in
`tests/test_manual_update_transaction.py` / `tests/test_upload_artifact_gate.py`.
Additional assigned outputs: `docs-design/free-roaming-live-20260909.jsonl`,
`docs-design/free-roaming-live-20260909.png`,
`docs-design/free-roaming-native-20260909.json` and `.png`,
`/tmp/claudepet-free-roaming-20260909-qa.py` and
`/tmp/claudepet-free-roaming-20260909-config.json`.
The tracked `tests/test_v021_release_contract.py` hash-pin validation was also
assigned if needed; unrelated release assertions may not be weakened.
Other untracked files and previous GUI evidence are outside this assignment.

Baseline: HEAD `24731b0`, source SHA-256
`3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c`.
Tracked tree was clean. Live process inventory confirmed installed PID29528 and
development PID58849; those are observed for this run, not assumed from yesterday.

User contract: choose random destinations throughout the current monitor's
visible full-window-safe center bounds. Approach and wander both end in rest at
their destination, with no automatic return. Preserve calm timing/speed, cursor
clearance, interaction/Reduce Motion suppression, compact travel and arrival
summary. Natural completion restores the manual display preference at the new
position. Automatic positions are not persisted; manual drag is still persisted.

Independent rivals and separating cases:

| Rule | Expected | Plausible wrong behavior |
| --- | --- | --- |
| Approach/wander pause expires | Same destination, rest, naturally settled | Explicit home phase; teleport home; remain in look forever |
| Interrupted trip reaches a quiet eligibility check without an eligible new trip | Keep stopped position | Fallback trip to old manual home |
| Natural completion while away | Restore manual full/folded choice | Retain summary because away=True |
| Hover at arrival | Retain summary | Clear every rest summary regardless of completion cause |
| Whole monitor target | Far targets in independent x/y portions of safe bounds | Old 160pt home disk; 360pt cap; center-only/one-axis sampling; origin-zero bounds |

The baseline approach fixture starts at (-1500,700) with cursor (-750,700): the
existing unchanged approach limit yields (-1140,700), 360pt away. A 100pt/s test
clock gives an interrupted position (-1450,700) after two quarter-second ticks.
The full rest is tested before permitting any subsequent eligibility check.
These are synthetic pure-state fixtures, not runtime timing claims.

## Baseline completion/display RED

Grouping key: unittest case/subtest ID. Files: tests/test_free_roaming.py, tests/test_companion_motion.py pure loader, baseline claude_pet.py AST. Source SHA 3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c; UTC 2026-09-09T07:15:51.597286+00:00–2026-09-09T07:15:51.859514+00:00; measured at end. Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_free_roaming.py -v`; exit 1. Existing return/radius assertions have not been edited.

```text
test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) ... 
  test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) (kind='approach') ... FAIL
  test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) (kind='wander') ... FAIL
test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home) ... FAIL
test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) ... 
  test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) (preference=False, natural=True) ... FAIL
  test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) (preference=True, natural=True) ... FAIL

======================================================================
FAIL: test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) (kind='approach')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 54, in test_approach_and_wander_finish_at_their_destination_without_return
    self.assertEqual(out.phase, "rest", "arrival pause started an unwanted return leg")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'home' != 'rest'
- home
+ rest
 : arrival pause started an unwanted return leg

======================================================================
FAIL: test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) (kind='wander')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 54, in test_approach_and_wander_finish_at_their_destination_without_return
    self.assertEqual(out.phase, "rest", "arrival pause started an unwanted return leg")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'home' != 'rest'
- home
+ rest
 : arrival pause started an unwanted return leg

======================================================================
FAIL: test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 73, in test_interrupted_trip_does_not_fall_back_to_old_manual_home
    self.assertEqual(out.phase, "rest", "idle fallback resumed travel toward the old home")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'home' != 'rest'
- home
+ rest
 : idle fallback resumed travel toward the old home

======================================================================
FAIL: test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) (preference=False, natural=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 87, in test_natural_away_completion_restores_preference_but_hover_keeps_summary
    self.assertEqual(display.mode("rest", preference), expected,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "display confused natural completion away from home with hover")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'summary' != 'folded'
- summary
+ folded
 : display confused natural completion away from home with hover

======================================================================
FAIL: test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) (preference=True, natural=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 87, in test_natural_away_completion_restores_preference_but_hover_keeps_summary
    self.assertEqual(display.mode("rest", preference), expected,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "display confused natural completion away from home with hover")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'summary' != 'full'
- summary
+ full
 : display confused natural completion away from home with hover

----------------------------------------------------------------------
Ran 3 tests in 0.093s

FAILED (failures=5)
```

## Baseline full-rectangle/retry RED

Contract accepted before this run: wander_enabled=True, wander_tries=6; each attempt draws x then y uniformly from the supplied safe-center bounds, rejects min-trip<60, endpoint clearance<150+radius, or swept cursor clearance<radius+24. Home remains manual-only. Unit draw(.8,.25), safe rect(-1770,190,-470,970) gives(-730,385), versus old polar-home disk. Retry candidates(210,310),(820,510),(1400,700),(1400,150) respectively separate short-trip, endpoint, swept-path and valid destination rules. Invalid-six fixture repeats the current point and must terminate without fallback.

Grouping key unittest case/subtest ID. Files tests/test_free_roaming.py, test_companion_motion.py AST loader, baseline claude_pet.py. SHA 3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c; UTC 2026-09-09T07:21:54.995584+00:00–2026-09-09T07:21:55.200855+00:00; measured at end. Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_free_roaming.py -k FreeRoamingSamplingTests -v`; exit 1.

```text
test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) ... 
  test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(0.8, 0.25)) ... FAIL
  test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(0.0, 0.0)) ... FAIL
  test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(1.0, 1.0)) ... FAIL
test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure) ... FAIL
test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return) ... FAIL

======================================================================
FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(0.8, 0.25))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 53, in test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk
    self.assertEqual(actual, expected,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
                     "wander did not sample the whole safe center rectangle")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-1653.7335554781296, 799.160196114912) != (-730.0, 385.0)

First differing element 0:
-1653.7335554781296
-730.0

- (-1653.7335554781296, 799.160196114912)
+ (-730.0, 385.0) : wander did not sample the whole safe center rectangle

======================================================================
FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(0.0, 0.0))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 53, in test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk
    self.assertEqual(actual, expected,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
                     "wander did not sample the whole safe center rectangle")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-1620.0, 880.0) != (-1770.0, 190.0)

First differing element 0:
-1620.0
-1770.0

- (-1620.0, 880.0)
?    ^^     ^^

+ (-1770.0, 190.0)
?    ^^     ^^
 : wander did not sample the whole safe center rectangle

======================================================================
FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) (draws=(1.0, 1.0))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 53, in test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk
    self.assertEqual(actual, expected,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
                     "wander did not sample the whole safe center rectangle")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-1520.0, 880.0) != (-470.0, 970.0)

First differing element 0:
-1520.0
-470.0

- (-1520.0, 880.0)
+ (-470.0, 970.0) : wander did not sample the whole safe center rectangle

======================================================================
FAIL: test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 67, in test_retries_reject_short_endpoint_and_crossing_candidates_before_departure
    self.assertEqual(target, (1400.0, 150.0),
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
                     "unsafe candidate was used instead of retrying with the same bounds")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (275.95136462264367, 340.8711721382961) != (1400.0, 150.0)

First differing element 0:
275.95136462264367
1400.0

- (275.95136462264367, 340.8711721382961)
+ (1400.0, 150.0) : unsafe candidate was used instead of retrying with the same bounds

======================================================================
FAIL: test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_free_roaming.py", line 74, in test_six_invalid_candidates_stop_retrying_without_motion_or_return
    self.assertEqual(out.phase, "rest", "exhausted random search started an unintended trip")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'rest'
- out
+ rest
 : exhausted random search started an unintended trip

----------------------------------------------------------------------
Ran 3 tests in 0.125s

FAILED (failures=5)
```

## Existing gate migration after actual RED

After the two baseline RED runs, the Verifier migrated the old return/radius
expectations in the tracked motion tests: arrival now settles in place, leftward
travel still exercises swept cursor protection, and all supported moving/watching
phases still test every hold flag. Separate cooldown fixtures explicitly disable
wander via `wander_enabled=False`; the wander fixture alternates distant safe
rectangle targets and retains the 300-second spacing assertion. Manual home,
maximum approach distance, speed/dt limits, geometry recovery, display anchors,
interaction and persistence gates remain. Natural display completion is exercised
with `away=True`; hover remains `settled=False`.

The opt-in native smoke now waits at the new destination for ten synthetic seconds
after natural completion and verifies that manual home has not changed. Its
outputs belong to the new assigned free-roaming-native-20260909.json/.png paths;
previous quiet-companion artifacts remain unchanged. This is a real NSWindow
with controlled clock/input, distinct from the separately assigned real-time GUI
trace and screenshot paths. Mutation output is routed to this report.

## Focused free-roaming run (behavior frozen, documentation comments pending)

Command: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_*roaming.py -v`; source SHA f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288; UTC 2026-09-09T07:29:59.898181+00:00–2026-09-09T07:30:00.198763+00:00; measured at end. Grouping key unittest case; files new free-roaming tests, companion loader and source AST. Exit 0.

```text
test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) ... ok
test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home) ... ok
test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) ... ok
test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) ... ok
test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure) ... ok
test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.224s

OK
```

## Native compact arrival/no-return verification

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tests/test_companion_motion.py --native-smoke --compact-presentation-gate`; source f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288; UTC 2026-09-09T07:31:02.508848+00:00–2026-09-09T07:31:02.880644+00:00; measured at end. Fresh child HOME/TMPDIR/ZDOTDIR/CLAUDEPET_SMOKE_SANDBOX=/var/folders/dq/w9mxm3513csghc_7h8xg8wj40000gn/T/claudepet-free-roaming-native-0po5x6og with minimal PATH and empty CDPATH. Real NSWindow, synthetic time/cursor and workers blocked. Exit 1. Full tick geometry in free-roaming-native-20260909.json.

```text
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 1266, in <module>
    run_native_smoke()
    ~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 1137, in run_native_smoke
    app_module.run_gui()
    ~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/claude_pet.py", line 7336, in run_gui
    AppHelper.runEventLoop()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 1087, in loop
    raise AssertionError("completed trip drifted or replaced the saved manual home")
AssertionError: completed trip drifted or replaced the saved manual home
```

Native measurement correction: the first failure compared the pre-first-tick
manual fixture center to the post-initial-row-size home. A diagnostic rerun
showed destination pos and arrival both (953.1244560754362,528.3880258670152),
while home=(636,358) and pre-first-tick initial=(636.5,343.5). The row-size update
occurs during initial rest, before automatic departure. The revised assertion
records the manual home at departure and requires it to remain unchanged through
travel, arrival and the ten-second rest, alongside destination immobility. This
is a harness reference correction, not an established production regression.
The original failing assertion is preserved above.

## Corrected native measurement run

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tests/test_companion_motion.py --native-smoke --compact-presentation-gate`; source f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288; UTC 2026-09-09T07:32:37.083867+00:00–2026-09-09T07:32:37.597759+00:00; measured at end. Same isolated child environment, /var/folders/dq/w9mxm3513csghc_7h8xg8wj40000gn/T/claudepet-free-roaming-native-ce84c845. Exit 0.

```text
{
  "layout_midpoint": [
    676.5,
    383.5
  ],
  "synthetic_initial_center": [
    636.5,
    343.5
  ],
  "native_window_class": "<objective-c class NSWindow at 0x1f0708608>",
  "native_view_class": "<objective-c class PetView at 0x77089e190>",
  "runtime_roam_default": true,
  "defaults": {
    "rest_min_s": 45.0,
    "rest_max_s": 90.0,
    "approach_cooldown_s": 180.0,
    "wander_cooldown_s": 300.0,
    "walk_speed": 55.0,
    "approach_stop": 150.0,
    "approach_max": 360.0,
    "look_s": 6.0,
    "wander_enabled": true,
    "wander_tries": 6,
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,
    "cursor_move_px": 12.0,
    "cursor_sample_s": 1.0,
    "cursor_margin_px": 24.0,
    "max_dt_s": 0.25,
    "gap_s": 5.0,
    "min_trip_px": 60.0,
    "arrive_px": 2.0
  },
  "initial_roamer_cfg": {
    "rest_min_s": 45.0,
    "rest_max_s": 90.0,
    "approach_cooldown_s": 180.0,
    "wander_cooldown_s": 300.0,
    "walk_speed": 55.0,
    "approach_stop": 150.0,
    "approach_max": 360.0,
    "look_s": 6.0,
    "wander_enabled": true,
    "wander_tries": 6,
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,
    "cursor_move_px": 12.0,
    "cursor_sample_s": 1.0,
    "cursor_margin_px": 24.0,
    "max_dt_s": 0.25,
    "gap_s": 5.0,
    "min_trip_px": 60.0,
    "arrive_px": 2.0
  },
  "initial_radius": 190.21303845951255,
  "visible_screen": [
    0.0,
    36.0,
    1353.0,
    695.0
  ],
  "transitions": [
    {
      "t": 51.7,
      "phase": "out",
      "window": [
        506.0,
        240.0,
        128.0,
        108.0
      ],
      "sprite": [
        508.0,
        242.0
      ],
      "logical_center": [
        636.0,
        358.0
      ],
      "mode": "folded",
      "crop": [
        4,
        130,
        128,
        108
      ],
      "pos": [
        636.0,
        358.0
      ],
      "mood": "idle"
    },
    {
      "t": 58.25,
      "phase": "look",
      "window": [
        825.0,
        402.0,
        130.0,
        140.0
      ],
      "sprite": [
        829.0,
        404.0
      ],
      "logical_center": [
        957.0,
        520.0
      ],
      "mode": "summary",
      "crop": [
        2,
        98,
        130,
        140
      ],
      "pos": [
        957.1092300962879,
        520.7539933364747
      ],
      "mood": "running-right"
    },
    {
      "t": 64.25,
      "phase": "rest",
      "window": [
        823.0,
        400.0,
        268.0,
        240.0
      ],
      "sprite": [
        829.0,
        404.0
      ],
      "logical_center": [
        957.0,
        520.0
      ],
      "mode": "full",
      "crop": [
        0,
        0,
        268.0,
        240.0
      ],
      "pos": [
        957.1092300962879,
        520.7539933364747
      ],
      "mood": "review"
    }
  ],
  "manual_home_at_departure": [
    636.0,
    358.0
  ],
  "capture_states": [
    {
      "t": 51.75,
      "phase": "out",
      "window": [
        508.0,
        241.0,
        128.0,
        108.0
      ],
      "sprite": [
        510.0,
        243.0
      ],
      "logical_center": [
        638.0,
        359.0
      ],
      "mode": "folded",
      "crop": [
        4,
        130,
        128,
        108
      ],
      "pos": [
        638.4529177299021,
        359.24325967132023
      ],
      "mood": "running-right"
    },
    {
      "t": 58.300000000000004,
      "phase": "look",
      "window": [
        825.0,
        402.0,
        130.0,
        140.0
      ],
      "sprite": [
        829.0,
        404.0
      ],
      "logical_center": [
        957.0,
        520.0
      ],
      "mode": "summary",
      "crop": [
        2,
        98,
        130,
        140
      ],
      "pos": [
        957.1092300962879,
        520.7539933364747
      ],
      "mood": "review"
    },
    {
      "t": 64.3,
      "phase": "rest",
      "window": [
        823.0,
        400.0,
        268.0,
        240.0
      ],
      "sprite": [
        829.0,
        404.0
      ],
      "logical_center": [
        957.0,
        520.0
      ],
      "mode": "full",
      "crop": [
        0,
        0,
        268.0,
        240.0
      ],
      "pos": [
        957.1092300962879,
        520.7539933364747
      ],
      "mood": "idle"
    }
  ],
  "capture_column_phases": [
    "out",
    "look",
    "rest"
  ],
  "crossed_horizontal_midpoint": true,
  "crossed_vertical_midpoint": true,
  "max_native_model_axis_residual": 0.8746652024709647,
  "max_sprite_anchor_axis_residual": 0.8746652024709647,
  "native_visible_bounds_violations": 0,
  "start_utc": "2026-09-09T07:32:37.232220+00:00",
  "end_utc": "2026-09-09T07:32:37.573665+00:00",
  "measured_utc": "2026-09-09T07:32:37.573665+00:00",
  "source_sha256": "f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288",
  "grouping_key": "manually invoked native Ticker.tick_ callback",
  "sampled_ticks": 1485,
  "synthetic_time_start": 0.05,
  "synthetic_time_end": 74.25,
  "max_window_step": 4.47213595499958,
  "max_sprite_step": 3.605551275463989,
  "max_model_step": 2.75000000000025,
  "max_sprite_displacement_beyond_model": 0.9337852725899324,
  "forbidden_calls": [],
  "suppressed_background_workers": [
    "work",
    "_run_update_check"
  ],
  "config_writes": []
}
```

## Focused companion regression run

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_motion.py -v`; source f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288; UTC 2026-09-09T07:32:50.553984+00:00–2026-09-09T07:32:53.353038+00:00; measured at end. Grouping key unittest case, source AST and synthetic fixtures/native NSMenu only. Exit 0.

```text
test_display_shrink_recovers_full_window_and_cancels_old_trip (test_companion_motion.CompanionAdapterTests.test_display_shrink_recovers_full_window_and_cancels_old_trip) ... ok
test_resize_while_away_cancels_motion_and_recomputes_window_radius (test_companion_motion.CompanionAdapterTests.test_resize_while_away_cancels_motion_and_recomputes_window_radius) ... ok
test_disabled_start_remains_at_current_position (test_companion_motion.CompanionApiTests.test_disabled_start_remains_at_current_position) ... ok
test_initial_rest_does_not_move_for_early_activity (test_companion_motion.CompanionApiTests.test_initial_rest_does_not_move_for_early_activity) ... ok
test_public_pure_motion_contract_exists (test_companion_motion.CompanionApiTests.test_public_pure_motion_contract_exists) ... ok
test_set_home_replaces_both_old_motion_origin_and_manual_home (test_companion_motion.CompanionApiTests.test_set_home_replaces_both_old_motion_origin_and_manual_home) ... ok
test_actual_summary_draw_keeps_long_text_inside_pill_padding (test_companion_motion.CompanionCompactRegressionTests.test_actual_summary_draw_keeps_long_text_inside_pill_padding) ... ok
test_actual_summary_formatter_distinguishes_estimate_from_exact (test_companion_motion.CompanionCompactRegressionTests.test_actual_summary_formatter_distinguishes_estimate_from_exact) ... ok
test_crop_change_during_drag_preserves_actual_manual_displacement (test_companion_motion.CompanionCompactRegressionTests.test_crop_change_during_drag_preserves_actual_manual_displacement) ... ok
test_fit_contract_uses_measured_longest_prefix_and_tiny_width (test_companion_motion.CompanionCompactRegressionTests.test_fit_contract_uses_measured_longest_prefix_and_tiny_width) ... ok
test_folded_drop_clamps_logical_envelope_before_save_and_restore (test_companion_motion.CompanionCompactRegressionTests.test_folded_drop_clamps_logical_envelope_before_save_and_restore) ... ok
test_all_orientations_preserve_sprite_anchor_and_logical_home (test_companion_motion.CompanionCropGeometryTests.test_all_orientations_preserve_sprite_anchor_and_logical_home) ... ok
test_native_compact_size_includes_button_but_not_full_panel_hitbox (test_companion_motion.CompanionCropGeometryTests.test_native_compact_size_includes_button_but_not_full_panel_hitbox) ... ok
test_summary_text_width_is_bounded_and_origin_uses_same_side (test_companion_motion.CompanionCropGeometryTests.test_summary_text_width_is_bounded_and_origin_uses_same_side) ... ok
test_uncropped_window_logical_center_remains_native_center (test_companion_motion.CompanionCropGeometryTests.test_uncropped_window_logical_center_remains_native_center) ... ok
test_click_during_auto_away_does_not_persist_automatic_xy (test_companion_motion.CompanionGuiOwnershipTests.test_click_during_auto_away_does_not_persist_automatic_xy) ... ok
test_native_menu_validation_preserves_reduce_motion_disabled_item (test_companion_motion.CompanionGuiOwnershipTests.test_native_menu_validation_preserves_reduce_motion_disabled_item) ... ok
test_activity_bursts_respect_approach_cooldown_without_starving_future_visits (test_companion_motion.CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits) ... ok
test_approach_max_and_watch_hold_are_geometrically_bounded (test_companion_motion.CompanionMotionTests.test_approach_max_and_watch_hold_are_geometrically_bounded) ... ok
test_click_without_drag_preserves_manual_home_and_current_position (test_companion_motion.CompanionMotionTests.test_click_without_drag_preserves_manual_home_and_current_position) ... ok
test_cursor_on_leftward_outbound_segment_also_cancels (test_companion_motion.CompanionMotionTests.test_cursor_on_leftward_outbound_segment_also_cancels) ... ok
test_cursor_on_outbound_segment_cancels_instead_of_crossing_it (test_companion_motion.CompanionMotionTests.test_cursor_on_outbound_segment_cancels_instead_of_crossing_it) ... ok
test_disabled_after_arrival_does_not_snap_to_manual_home (test_companion_motion.CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home) ... ok
test_each_interaction_freezes_an_inflight_approach_and_resumes_quietly (test_companion_motion.CompanionMotionTests.test_each_interaction_freezes_an_inflight_approach_and_resumes_quietly) ... ok
test_eligible_activity_starts_approach_after_the_rest (test_companion_motion.CompanionMotionTests.test_eligible_activity_starts_approach_after_the_rest) ... ok
test_fixed_destination_does_not_chase_new_cursor_locations (test_companion_motion.CompanionMotionTests.test_fixed_destination_does_not_chase_new_cursor_locations) ... ok
test_hold_on_every_trip_phase_freezes_outbound_and_look (test_companion_motion.CompanionMotionTests.test_hold_on_every_trip_phase_freezes_outbound_and_look) ... ok
test_invalid_bounds_do_not_bypass_suppression_or_restore_stale_target (test_companion_motion.CompanionMotionTests.test_invalid_bounds_do_not_bypass_suppression_or_restore_stale_target) ... ok
test_invalid_center_bounds_freeze_without_reversed_clamp_jump (test_companion_motion.CompanionMotionTests.test_invalid_center_bounds_freeze_without_reversed_clamp_jump) ... ok
test_late_tick_caps_distance_without_using_full_elapsed_time (test_companion_motion.CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time) ... ok
test_long_interaction_still_gets_full_fresh_rest_after_release (test_companion_motion.CompanionMotionTests.test_long_interaction_still_gets_full_fresh_rest_after_release) ... ok
test_nonzero_negative_monitor_origin_contains_every_position (test_companion_motion.CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position) ... ok
test_pointer_in_interior_of_full_leg_stops_before_next_step (test_companion_motion.CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step) ... ok
test_real_drag_establishes_a_new_home_and_cancels_old_target (test_companion_motion.CompanionMotionTests.test_real_drag_establishes_a_new_home_and_cancels_old_target) ... ok
test_sleep_gap_freezes_in_place_and_discards_old_journey (test_companion_motion.CompanionMotionTests.test_sleep_gap_freezes_in_place_and_discards_old_journey) ... ok
test_wander_uses_monitor_bounds_pauses_and_respects_own_cooldown (test_companion_motion.CompanionMotionTests.test_wander_uses_monitor_bounds_pauses_and_respects_own_cooldown) ... ok
test_approach_summary_expansion_does_not_replace_manual_preference (test_companion_motion.CompanionPresentationTests.test_approach_summary_expansion_does_not_replace_manual_preference) ... ok
test_departure_folds_even_before_any_displacement (test_companion_motion.CompanionPresentationTests.test_departure_folds_even_before_any_displacement) ... ok
test_exact_summary_filters_only_first_two_rows_without_replacement (test_companion_motion.CompanionPresentationTests.test_exact_summary_filters_only_first_two_rows_without_replacement) ... ok
test_explicit_interruption_or_disable_clears_summary_and_expansion (test_companion_motion.CompanionPresentationTests.test_explicit_interruption_or_disable_clears_summary_and_expansion) ... ok
test_hover_stop_away_keeps_summary_available_for_expansion (test_companion_motion.CompanionPresentationTests.test_hover_stop_away_keeps_summary_available_for_expansion) ... ok
test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry (test_companion_motion.CompanionPresentationTests.test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry) ... ok
test_interruption_has_priority_over_same_call_arrival (test_companion_motion.CompanionPresentationTests.test_interruption_has_priority_over_same_call_arrival) ... ok
test_manual_toggle_and_reset_restore_ordinary_preference_behavior (test_companion_motion.CompanionPresentationTests.test_manual_toggle_and_reset_restore_ordinary_preference_behavior) ... ok
test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion (test_companion_motion.CompanionPresentationTests.test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion) ... ok
test_server_label_matching_translation_key_remains_an_exact_label (test_companion_motion.CompanionPresentationTests.test_server_label_matching_translation_key_remains_an_exact_label) ... ok
test_summary_invalid_values_are_not_reported_as_zero (test_companion_motion.CompanionPresentationTests.test_summary_invalid_values_are_not_reported_as_zero) ... ok
test_summary_keeps_first_two_source_labels_and_values_in_order (test_companion_motion.CompanionPresentationTests.test_summary_keeps_first_two_source_labels_and_values_in_order) ... ok
test_summary_onboarding_and_estimates_preserve_data_meaning (test_companion_motion.CompanionPresentationTests.test_summary_onboarding_and_estimates_preserve_data_meaning) ... ok
test_summary_unknown_zero_and_api_mode_are_distinct (test_companion_motion.CompanionPresentationTests.test_summary_unknown_zero_and_api_mode_are_distinct) ... ok
test_wander_pause_stays_folded_and_settlement_restores_manual_choice (test_companion_motion.CompanionPresentationTests.test_wander_pause_stays_folded_and_settlement_restores_manual_choice) ... ok

----------------------------------------------------------------------
Ran 51 tests in 2.709s

OK
```

## In-memory rival execution

Grouping key: rival implementation paired with its targeted test case. File set: tests/test_companion_motion.py and the frozen-in-memory claude_pet.py snapshot. Source SHA-256: f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a. Window start: 2026-09-09T07:35:02.209073+00:00; end: 2026-09-09T07:35:02.605126+00:00; measured: 2026-09-09T07:35:02.605126+00:00. Command: `PYTHONDONTWRITEBYTECODE=1 python3 tests/test_companion_motion.py --mutation-check`. Each unchanged positive control ran and passed before its rival. This is fault-injection evidence, separate from the actual pre-fix RED runs.

Rival: uncapped elapsed time; targeted case: `CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time`.

```text
test_late_tick_caps_distance_without_using_full_elapsed_time (__main__.CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time) ... FAIL

======================================================================
FAIL: test_late_tick_caps_distance_without_using_full_elapsed_time (__main__.CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 165, in test_late_tick_caps_distance_without_using_full_elapsed_time
    self.assertAlmostEqual(math.dist(before, out.pos), 10.0, places=6)
    ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 40.0 != 10.0 within 6 places (30.0 difference)

----------------------------------------------------------------------
Ran 1 test in 0.028s

FAILED (failures=1)
```

Rival: endpoint-only cursor safety; targeted case: `CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step`.

```text
test_pointer_in_interior_of_full_leg_stops_before_next_step (__main__.CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step) ... FAIL

======================================================================
FAIL: test_pointer_in_interior_of_full_leg_stops_before_next_step (__main__.CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 273, in test_pointer_in_interior_of_full_leg_stops_before_next_step
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (410.0, 300.0) != (400.0, 300.0)

First differing element 0:
410.0
400.0

- (410.0, 300.0)
?   ^

+ (400.0, 300.0)
?   ^


----------------------------------------------------------------------
Ran 1 test in 0.025s

FAILED (failures=1)
```

Rival: no geometry clamp; targeted case: `CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position`.

```text
test_nonzero_negative_monitor_origin_contains_every_position (__main__.CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position) ... FAIL

======================================================================
FAIL: test_nonzero_negative_monitor_origin_contains_every_position (__main__.CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 296, in test_nonzero_negative_monitor_origin_contains_every_position
    self.assertLessEqual(out.pos[0], -300.0)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
AssertionError: -290.0 not less than or equal to -300.0

----------------------------------------------------------------------
Ran 1 test in 0.024s

FAILED (failures=1)
```

Rival: no approach cooldown; targeted case: `CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits`.

```text
test_activity_bursts_respect_approach_cooldown_without_starving_future_visits (__main__.CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits) ... FAIL

======================================================================
FAIL: test_activity_bursts_respect_approach_cooldown_without_starving_future_visits (__main__.CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 313, in test_activity_bursts_respect_approach_cooldown_without_starving_future_visits
    self.assertGreaterEqual(current - previous, 180.0)
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 21.0 not greater than or equal to 180.0

----------------------------------------------------------------------
Ran 1 test in 0.027s

FAILED (failures=1)
```

Rival: watch never settles; targeted case: `CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home`.

```text
test_disabled_after_arrival_does_not_snap_to_manual_home (__main__.CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home) ... FAIL

======================================================================
FAIL: test_disabled_after_arrival_does_not_snap_to_manual_home (__main__.CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 215, in test_disabled_after_arrival_does_not_snap_to_manual_home
    self.assertEqual(out.phase, "rest", "arrival never settled at its destination")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'look' != 'rest'
- look
+ rest
 : arrival never settled at its destination

----------------------------------------------------------------------
Ran 1 test in 0.025s

FAILED (failures=1)
```

## Final source native run

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tests/test_companion_motion.py --native-smoke --compact-presentation-gate`; SHA f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a; UTC 2026-09-09T07:37:19.532584+00:00–2026-09-09T07:37:20.111081+00:00; measured at end. Same child allow-list /var/folders/dq/w9mxm3513csghc_7h8xg8wj40000gn/T/claudepet-free-roaming-native-final-89xw_6eb. Exit 0. Native JSON/PNG now hold this final source run; earlier outputs remain inline above.

```text
{
  "layout_midpoint": [
    676.5,
    383.5
  ],
  "synthetic_initial_center": [
    636.5,
    343.5
  ],
  "native_window_class": "<objective-c class NSWindow at 0x1f0708608>",
  "native_view_class": "<objective-c class PetView at 0xa8449d6e0>",
  "runtime_roam_default": true,
  "defaults": {
    "rest_min_s": 45.0,
    "rest_max_s": 90.0,
    "approach_cooldown_s": 180.0,
    "wander_cooldown_s": 300.0,
    "walk_speed": 55.0,
    "approach_stop": 150.0,
    "approach_max": 360.0,
    "look_s": 6.0,
    "wander_enabled": true,
    "wander_tries": 6,
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,
    "cursor_move_px": 12.0,
    "cursor_sample_s": 1.0,
    "cursor_margin_px": 24.0,
    "max_dt_s": 0.25,
    "gap_s": 5.0,
    "min_trip_px": 60.0,
    "arrive_px": 2.0
  },
  "initial_roamer_cfg": {
    "rest_min_s": 45.0,
    "rest_max_s": 90.0,
    "approach_cooldown_s": 180.0,
    "wander_cooldown_s": 300.0,
    "walk_speed": 55.0,
    "approach_stop": 150.0,
    "approach_max": 360.0,
    "look_s": 6.0,
    "wander_enabled": true,
    "wander_tries": 6,
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,
    "cursor_move_px": 12.0,
    "cursor_sample_s": 1.0,
    "cursor_margin_px": 24.0,
    "max_dt_s": 0.25,
    "gap_s": 5.0,
    "min_trip_px": 60.0,
    "arrive_px": 2.0
  },
  "initial_radius": 190.21303845951255,
  "visible_screen": [
    0.0,
    36.0,
    1353.0,
    695.0
  ],
  "transitions": [
    {
      "t": 72.7,
      "phase": "out",
      "window": [
        506.0,
        240.0,
        128.0,
        108.0
      ],
      "sprite": [
        508.0,
        242.0
      ],
      "logical_center": [
        636.0,
        358.0
      ],
      "mode": "folded",
      "crop": [
        4,
        130,
        128,
        108
      ],
      "pos": [
        636.0,
        358.0
      ],
      "mood": "idle"
    },
    {
      "t": 79.25,
      "phase": "look",
      "window": [
        821.0,
        410.0,
        130.0,
        140.0
      ],
      "sprite": [
        825.0,
        412.0
      ],
      "logical_center": [
        953.0,
        528.0
      ],
      "mode": "summary",
      "crop": [
        2,
        98,
        130,
        140
      ],
      "pos": [
        953.1244560754362,
        528.3880258670152
      ],
      "mood": "running-right"
    },
    {
      "t": 85.25,
      "phase": "rest",
      "window": [
        819.0,
        408.0,
        268.0,
        240.0
      ],
      "sprite": [
        825.0,
        412.0
      ],
      "logical_center": [
        953.0,
        528.0
      ],
      "mode": "full",
      "crop": [
        0,
        0,
        268.0,
        240.0
      ],
      "pos": [
        953.1244560754362,
        528.3880258670152
      ],
      "mood": "review"
    }
  ],
  "manual_home_at_departure": [
    636.0,
    358.0
  ],
  "capture_states": [
    {
      "t": 72.75,
      "phase": "out",
      "window": [
        508.0,
        241.0,
        128.0,
        108.0
      ],
      "sprite": [
        510.0,
        243.0
      ],
      "logical_center": [
        638.0,
        359.0
      ],
      "mode": "folded",
      "crop": [
        4,
        130,
        128,
        108
      ],
      "pos": [
        638.4224784839095,
        359.3015751975952
      ],
      "mood": "running-right"
    },
    {
      "t": 79.30000000000001,
      "phase": "look",
      "window": [
        821.0,
        410.0,
        130.0,
        140.0
      ],
      "sprite": [
        825.0,
        412.0
      ],
      "logical_center": [
        953.0,
        528.0
      ],
      "mode": "summary",
      "crop": [
        2,
        98,
        130,
        140
      ],
      "pos": [
        953.1244560754362,
        528.3880258670152
      ],
      "mood": "review"
    },
    {
      "t": 85.30000000000001,
      "phase": "rest",
      "window": [
        819.0,
        408.0,
        268.0,
        240.0
      ],
      "sprite": [
        825.0,
        412.0
      ],
      "logical_center": [
        953.0,
        528.0
      ],
      "mode": "full",
      "crop": [
        0,
        0,
        268.0,
        240.0
      ],
      "pos": [
        953.1244560754362,
        528.3880258670152
      ],
      "mood": "idle"
    }
  ],
  "capture_column_phases": [
    "out",
    "look",
    "rest"
  ],
  "crossed_horizontal_midpoint": true,
  "crossed_vertical_midpoint": true,
  "max_native_model_axis_residual": 0.8724590893816639,
  "max_sprite_anchor_axis_residual": 0.8724590893816639,
  "native_visible_bounds_violations": 0,
  "start_utc": "2026-09-09T07:37:19.688436+00:00",
  "end_utc": "2026-09-09T07:37:20.072234+00:00",
  "measured_utc": "2026-09-09T07:37:20.072234+00:00",
  "source_sha256": "f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a",
  "grouping_key": "manually invoked native Ticker.tick_ callback",
  "sampled_ticks": 1905,
  "synthetic_time_start": 0.05,
  "synthetic_time_end": 95.25,
  "max_window_step": 4.47213595499958,
  "max_sprite_step": 3.605551275463989,
  "max_model_step": 2.7500000000006457,
  "max_sprite_displacement_beyond_model": 0.9062716514167944,
  "forbidden_calls": [],
  "suppressed_background_workers": [
    "work",
    "_run_update_check"
  ],
  "config_writes": []
}
```

## Final frozen-source full suite

Command `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v` from repository root; SHA before f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a and after f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a; UTC 2026-09-09T07:34:23.460831+00:00–2026-09-09T07:39:47.202068+00:00; measured at end. Normal top-level HOME; module-owned temporary fixtures use their own allow-list. File set tests/test_*.py, source/release scripts and module synthetic fixtures; grouping key unittest case. Exit 0. Source hash pins were refreshed only after AST comparison showed production definitions changed only in Roamer/RoamDisplay; updater/signing/upload bodies unchanged.

```text
test_display_shrink_recovers_full_window_and_cancels_old_trip (test_companion_motion.CompanionAdapterTests.test_display_shrink_recovers_full_window_and_cancels_old_trip) ... ok
test_resize_while_away_cancels_motion_and_recomputes_window_radius (test_companion_motion.CompanionAdapterTests.test_resize_while_away_cancels_motion_and_recomputes_window_radius) ... ok
test_disabled_start_remains_at_current_position (test_companion_motion.CompanionApiTests.test_disabled_start_remains_at_current_position) ... ok
test_initial_rest_does_not_move_for_early_activity (test_companion_motion.CompanionApiTests.test_initial_rest_does_not_move_for_early_activity) ... ok
test_public_pure_motion_contract_exists (test_companion_motion.CompanionApiTests.test_public_pure_motion_contract_exists) ... ok
test_set_home_replaces_both_old_motion_origin_and_manual_home (test_companion_motion.CompanionApiTests.test_set_home_replaces_both_old_motion_origin_and_manual_home) ... ok
test_actual_summary_draw_keeps_long_text_inside_pill_padding (test_companion_motion.CompanionCompactRegressionTests.test_actual_summary_draw_keeps_long_text_inside_pill_padding) ... ok
test_actual_summary_formatter_distinguishes_estimate_from_exact (test_companion_motion.CompanionCompactRegressionTests.test_actual_summary_formatter_distinguishes_estimate_from_exact) ... ok
test_crop_change_during_drag_preserves_actual_manual_displacement (test_companion_motion.CompanionCompactRegressionTests.test_crop_change_during_drag_preserves_actual_manual_displacement) ... ok
test_fit_contract_uses_measured_longest_prefix_and_tiny_width (test_companion_motion.CompanionCompactRegressionTests.test_fit_contract_uses_measured_longest_prefix_and_tiny_width) ... ok
test_folded_drop_clamps_logical_envelope_before_save_and_restore (test_companion_motion.CompanionCompactRegressionTests.test_folded_drop_clamps_logical_envelope_before_save_and_restore) ... ok
test_all_orientations_preserve_sprite_anchor_and_logical_home (test_companion_motion.CompanionCropGeometryTests.test_all_orientations_preserve_sprite_anchor_and_logical_home) ... ok
test_native_compact_size_includes_button_but_not_full_panel_hitbox (test_companion_motion.CompanionCropGeometryTests.test_native_compact_size_includes_button_but_not_full_panel_hitbox) ... ok
test_summary_text_width_is_bounded_and_origin_uses_same_side (test_companion_motion.CompanionCropGeometryTests.test_summary_text_width_is_bounded_and_origin_uses_same_side) ... ok
test_uncropped_window_logical_center_remains_native_center (test_companion_motion.CompanionCropGeometryTests.test_uncropped_window_logical_center_remains_native_center) ... ok
test_click_during_auto_away_does_not_persist_automatic_xy (test_companion_motion.CompanionGuiOwnershipTests.test_click_during_auto_away_does_not_persist_automatic_xy) ... ok
test_native_menu_validation_preserves_reduce_motion_disabled_item (test_companion_motion.CompanionGuiOwnershipTests.test_native_menu_validation_preserves_reduce_motion_disabled_item) ... ok
test_activity_bursts_respect_approach_cooldown_without_starving_future_visits (test_companion_motion.CompanionMotionTests.test_activity_bursts_respect_approach_cooldown_without_starving_future_visits) ... ok
test_approach_max_and_watch_hold_are_geometrically_bounded (test_companion_motion.CompanionMotionTests.test_approach_max_and_watch_hold_are_geometrically_bounded) ... ok
test_click_without_drag_preserves_manual_home_and_current_position (test_companion_motion.CompanionMotionTests.test_click_without_drag_preserves_manual_home_and_current_position) ... ok
test_cursor_on_leftward_outbound_segment_also_cancels (test_companion_motion.CompanionMotionTests.test_cursor_on_leftward_outbound_segment_also_cancels) ... ok
test_cursor_on_outbound_segment_cancels_instead_of_crossing_it (test_companion_motion.CompanionMotionTests.test_cursor_on_outbound_segment_cancels_instead_of_crossing_it) ... ok
test_disabled_after_arrival_does_not_snap_to_manual_home (test_companion_motion.CompanionMotionTests.test_disabled_after_arrival_does_not_snap_to_manual_home) ... ok
test_each_interaction_freezes_an_inflight_approach_and_resumes_quietly (test_companion_motion.CompanionMotionTests.test_each_interaction_freezes_an_inflight_approach_and_resumes_quietly) ... ok
test_eligible_activity_starts_approach_after_the_rest (test_companion_motion.CompanionMotionTests.test_eligible_activity_starts_approach_after_the_rest) ... ok
test_fixed_destination_does_not_chase_new_cursor_locations (test_companion_motion.CompanionMotionTests.test_fixed_destination_does_not_chase_new_cursor_locations) ... ok
test_hold_on_every_trip_phase_freezes_outbound_and_look (test_companion_motion.CompanionMotionTests.test_hold_on_every_trip_phase_freezes_outbound_and_look) ... ok
test_invalid_bounds_do_not_bypass_suppression_or_restore_stale_target (test_companion_motion.CompanionMotionTests.test_invalid_bounds_do_not_bypass_suppression_or_restore_stale_target) ... ok
test_invalid_center_bounds_freeze_without_reversed_clamp_jump (test_companion_motion.CompanionMotionTests.test_invalid_center_bounds_freeze_without_reversed_clamp_jump) ... ok
test_late_tick_caps_distance_without_using_full_elapsed_time (test_companion_motion.CompanionMotionTests.test_late_tick_caps_distance_without_using_full_elapsed_time) ... ok
test_long_interaction_still_gets_full_fresh_rest_after_release (test_companion_motion.CompanionMotionTests.test_long_interaction_still_gets_full_fresh_rest_after_release) ... ok
test_nonzero_negative_monitor_origin_contains_every_position (test_companion_motion.CompanionMotionTests.test_nonzero_negative_monitor_origin_contains_every_position) ... ok
test_pointer_in_interior_of_full_leg_stops_before_next_step (test_companion_motion.CompanionMotionTests.test_pointer_in_interior_of_full_leg_stops_before_next_step) ... ok
test_real_drag_establishes_a_new_home_and_cancels_old_target (test_companion_motion.CompanionMotionTests.test_real_drag_establishes_a_new_home_and_cancels_old_target) ... ok
test_sleep_gap_freezes_in_place_and_discards_old_journey (test_companion_motion.CompanionMotionTests.test_sleep_gap_freezes_in_place_and_discards_old_journey) ... ok
test_wander_uses_monitor_bounds_pauses_and_respects_own_cooldown (test_companion_motion.CompanionMotionTests.test_wander_uses_monitor_bounds_pauses_and_respects_own_cooldown) ... ok
test_approach_summary_expansion_does_not_replace_manual_preference (test_companion_motion.CompanionPresentationTests.test_approach_summary_expansion_does_not_replace_manual_preference) ... ok
test_departure_folds_even_before_any_displacement (test_companion_motion.CompanionPresentationTests.test_departure_folds_even_before_any_displacement) ... ok
test_exact_summary_filters_only_first_two_rows_without_replacement (test_companion_motion.CompanionPresentationTests.test_exact_summary_filters_only_first_two_rows_without_replacement) ... ok
test_explicit_interruption_or_disable_clears_summary_and_expansion (test_companion_motion.CompanionPresentationTests.test_explicit_interruption_or_disable_clears_summary_and_expansion) ... ok
test_hover_stop_away_keeps_summary_available_for_expansion (test_companion_motion.CompanionPresentationTests.test_hover_stop_away_keeps_summary_available_for_expansion) ... ok
test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry (test_companion_motion.CompanionPresentationTests.test_in_place_arrival_distinguishes_hover_stop_from_normal_watch_expiry) ... ok
test_interruption_has_priority_over_same_call_arrival (test_companion_motion.CompanionPresentationTests.test_interruption_has_priority_over_same_call_arrival) ... ok
test_manual_toggle_and_reset_restore_ordinary_preference_behavior (test_companion_motion.CompanionPresentationTests.test_manual_toggle_and_reset_restore_ordinary_preference_behavior) ... ok
test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion (test_companion_motion.CompanionPresentationTests.test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion) ... ok
test_server_label_matching_translation_key_remains_an_exact_label (test_companion_motion.CompanionPresentationTests.test_server_label_matching_translation_key_remains_an_exact_label) ... ok
test_summary_invalid_values_are_not_reported_as_zero (test_companion_motion.CompanionPresentationTests.test_summary_invalid_values_are_not_reported_as_zero) ... ok
test_summary_keeps_first_two_source_labels_and_values_in_order (test_companion_motion.CompanionPresentationTests.test_summary_keeps_first_two_source_labels_and_values_in_order) ... ok
test_summary_onboarding_and_estimates_preserve_data_meaning (test_companion_motion.CompanionPresentationTests.test_summary_onboarding_and_estimates_preserve_data_meaning) ... ok
test_summary_unknown_zero_and_api_mode_are_distinct (test_companion_motion.CompanionPresentationTests.test_summary_unknown_zero_and_api_mode_are_distinct) ... ok
test_wander_pause_stays_folded_and_settlement_restores_manual_choice (test_companion_motion.CompanionPresentationTests.test_wander_pause_stays_folded_and_settlement_restores_manual_choice) ... ok
test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) ... ok
test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home) ... ok
test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) ... ok
test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) ... ok
test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure) ... ok
test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return) ... ok
test_rolling_week_has_no_single_reset_timestamp (test_log_estimate.ComputeUsageTests.test_rolling_week_has_no_single_reset_timestamp) ... ok
test_cache_creation_uses_ttl_specific_weights (test_log_estimate.ParseUsageEntriesTests.test_cache_creation_uses_ttl_specific_weights) ... ok
test_distinct_request_ids_are_counted_separately (test_log_estimate.ParseUsageEntriesTests.test_distinct_request_ids_are_counted_separately) ... ok
test_equal_timestamp_duplicates_keep_the_largest_complete_snapshot (test_log_estimate.ParseUsageEntriesTests.test_equal_timestamp_duplicates_keep_the_largest_complete_snapshot) ... ok
test_equal_weight_duplicates_keep_the_later_timestamp (test_log_estimate.ParseUsageEntriesTests.test_equal_weight_duplicates_keep_the_later_timestamp) ... ok
test_legacy_cache_creation_without_breakdown_uses_5m_fallback (test_log_estimate.ParseUsageEntriesTests.test_legacy_cache_creation_without_breakdown_uses_5m_fallback) ... ok
test_malformed_usage_numbers_skip_only_the_bad_rows (test_log_estimate.ParseUsageEntriesTests.test_malformed_usage_numbers_skip_only_the_bad_rows) ... ok
test_nested_cache_breakdown_above_flat_total_is_clamped (test_log_estimate.ParseUsageEntriesTests.test_nested_cache_breakdown_above_flat_total_is_clamped) ... ok
test_nested_sidechain_agent_usage_is_included (test_log_estimate.ParseUsageEntriesTests.test_nested_sidechain_agent_usage_is_included) ... ok
test_record_before_since_does_not_hide_a_later_snapshot (test_log_estimate.ParseUsageEntriesTests.test_record_before_since_does_not_hide_a_later_snapshot) ... ok
test_records_without_dedup_keys_are_counted_independently (test_log_estimate.ParseUsageEntriesTests.test_records_without_dedup_keys_are_counted_independently) ... ok
test_streaming_duplicates_keep_an_interior_maximum (test_log_estimate.ParseUsageEntriesTests.test_streaming_duplicates_keep_an_interior_maximum) ... ok
test_streaming_duplicates_keep_the_final_usage_snapshot (test_log_estimate.ParseUsageEntriesTests.test_streaming_duplicates_keep_the_final_usage_snapshot) ... ok
test_unclassified_cache_creation_remainder_uses_5m_fallback (test_log_estimate.ParseUsageEntriesTests.test_unclassified_cache_creation_remainder_uses_5m_fallback) ... ok
test_backup_symlink_and_its_target_are_preserved (test_manual_update_transaction.BackupPreservationTests.test_backup_symlink_and_its_target_are_preserved) ... ok
test_regular_backup_is_not_deleted_when_installed_app_exists (test_manual_update_transaction.BackupPreservationTests.test_regular_backup_is_not_deleted_when_installed_app_exists) ... ok
test_regular_backup_is_not_renamed_away_when_installed_app_is_absent (test_manual_update_transaction.BackupPreservationTests.test_regular_backup_is_not_renamed_away_when_installed_app_is_absent) ... ok
test_direct_build_cannot_remove_shared_app_while_build_lock_is_held (test_manual_update_transaction.BuildLockCoverageTests.test_direct_build_cannot_remove_shared_app_while_build_lock_is_held) ... ok
test_install_outer_build_lock_survives_inner_build_and_preflight_consumption (test_manual_update_transaction.BuildLockCoverageTests.test_install_outer_build_lock_survives_inner_build_and_preflight_consumption) ... ok
test_failed_adhoc_nested_fallback_stops_before_outer_signing (test_manual_update_transaction.NestedSigningFailureTests.test_failed_adhoc_nested_fallback_stops_before_outer_signing) ... ok
test_local_nested_failure_falls_back_as_a_pair_not_outer_only (test_manual_update_transaction.NestedSigningFailureTests.test_local_nested_failure_falls_back_as_a_pair_not_outer_only) ... ok
test_failed_publish_restores_and_relaunches_the_old_application (test_manual_update_transaction.RollbackAndInstallTests.test_failed_publish_restores_and_relaunches_the_old_application) ... ok
test_install_copy_failure_preserves_the_existing_application (test_manual_update_transaction.RollbackAndInstallTests.test_install_copy_failure_preserves_the_existing_application) ... ok
test_in_app_holder_blocks_public_install_and_update_before_child_mutation (test_manual_update_transaction.SharedUpdateLockTests.test_in_app_holder_blocks_public_install_and_update_before_child_mutation) ... ok
test_manual_holder_blocks_a_simulated_in_app_acquire (test_manual_update_transaction.SharedUpdateLockTests.test_manual_holder_blocks_a_simulated_in_app_acquire) ... ok
test_code_symlink_is_rejected_before_its_target_is_mutated (test_manual_update_transaction.StagedContainmentTests.test_code_symlink_is_rejected_before_its_target_is_mutated) ... ok
test_info_plist_symlink_is_rejected_before_its_target_is_mutated (test_manual_update_transaction.StagedContainmentTests.test_info_plist_symlink_is_rejected_before_its_target_is_mutated) ... ok
test_resources_symlink_is_rejected_before_its_target_is_mutated (test_manual_update_transaction.StagedContainmentTests.test_resources_symlink_is_rejected_before_its_target_is_mutated) ... ok
test_both_bundle_version_keys_must_equal_the_source_version (test_manual_update_transaction.StagedPreflightTests.test_both_bundle_version_keys_must_equal_the_source_version) ... ok
test_executable_must_be_a_regular_nonlink_file (test_manual_update_transaction.StagedPreflightTests.test_executable_must_be_a_regular_nonlink_file) ... ok
test_staged_application_code_must_match_the_checkout_code_hash (test_manual_update_transaction.StagedPreflightTests.test_staged_application_code_must_match_the_checkout_code_hash) ... ok
test_second_update_cannot_clean_or_prepare_until_first_transaction_finishes (test_manual_update_transaction.WholeTransactionConcurrencyTests.test_second_update_cannot_clean_or_prepare_until_first_transaction_finishes) ... ok
test_every_literal_needle_still_occurs_in_the_generated_script (test_mutation_instruments.InjectionNeedlesStillMatchTests.test_every_literal_needle_still_occurs_in_the_generated_script) ... ok
test_the_generator_produces_something_to_search (test_mutation_instruments.InjectionNeedlesStillMatchTests.test_the_generator_produces_something_to_search)
Discrimination: an empty script would make every check below vacuous. ... ok
test_the_needles_are_not_so_generic_that_they_hit_everywhere (test_mutation_instruments.InjectionNeedlesStillMatchTests.test_the_needles_are_not_so_generic_that_they_hit_everywhere)
A needle matching many places replaces more than the test intends. ... ok
test_generating_a_script_creates_nothing (test_mutation_instruments.LockPathIsolationTests.test_generating_a_script_creates_nothing)
`_update_lock_path` must be pure: asking is not making. ... ok
test_the_redirect_actually_took_effect (test_mutation_instruments.LockPathIsolationTests.test_the_redirect_actually_took_effect)
Otherwise the isolation is theatre and the check above is vacuous. ... ok
test_dynamic_needle_sites_are_reported_rather_than_silently_skipped (test_mutation_instruments.ScopeIsVisibleTests.test_dynamic_needle_sites_are_reported_rather_than_silently_skipped) ... ok
test_a_symlink_planted_at_the_staging_name_is_not_written_through (test_partial_copy_seeding.CopyPrimitiveRefusesAnExistingNameTests.test_a_symlink_planted_at_the_staging_name_is_not_written_through) ... ok
test_the_plant_is_actually_in_the_way (test_partial_copy_seeding.CopyPrimitiveRefusesAnExistingNameTests.test_the_plant_is_actually_in_the_way)
Discrimination: if the fixture missed, the test above proves nothing. ... ok
test_a_pet_that_died_midway_is_repaired_by_the_next_run (test_partial_copy_seeding.PartialPetCopyTests.test_a_pet_that_died_midway_is_repaired_by_the_next_run)
The failure must not be sticky. ... ok
test_a_pet_whose_sheet_dies_midway_is_not_published (test_partial_copy_seeding.PartialPetCopyTests.test_a_pet_whose_sheet_dies_midway_is_not_published) ... ok
test_the_first_file_dying_midway_is_handled_the_same_way (test_partial_copy_seeding.PartialPetCopyTests.test_the_first_file_dying_midway_is_handled_the_same_way)
pet.json is what `_is_pet_dir` keys on, so a truncated one is worst. ... ok
test_the_other_pets_are_still_seeded_whole (test_partial_copy_seeding.PartialPetCopyTests.test_the_other_pets_are_still_seeded_whole)
One pet dying must not cost the rest - and must not half-cost them. ... ok
test_a_readme_that_died_midway_is_repaired_by_the_next_run (test_partial_copy_seeding.PartialReadmeCopyTests.test_a_readme_that_died_midway_is_repaired_by_the_next_run) ... ok
test_a_readme_that_dies_midway_is_not_linked_into_place (test_partial_copy_seeding.PartialReadmeCopyTests.test_a_readme_that_dies_midway_is_not_linked_into_place) ... ok
test_the_other_readmes_still_land_whole (test_partial_copy_seeding.PartialReadmeCopyTests.test_the_other_readmes_still_land_whole) ... ok
test_cli_forwards_exact_version_and_ordered_arches_to_validator (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_cli_forwards_exact_version_and_ordered_arches_to_validator) ... ok
test_code_leaf_must_be_regular_present_and_not_a_symlink (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_code_leaf_must_be_regular_present_and_not_a_symlink) ... ok
test_exact_checkout_code_leaf_reaches_validator (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_exact_checkout_code_leaf_reaches_validator) ... ok
test_missing_arches_fails_before_validator_delegation (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_missing_arches_fails_before_validator_delegation) ... ok
test_missing_file_or_symlink_app_is_rejected_before_validator (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_missing_file_or_symlink_app_is_rejected_before_validator) ... ok
test_stale_regular_code_leaf_is_rejected_before_validator (test_release_artifact_preflight.ReleaseArtifactAppPreflightTests.test_stale_regular_code_leaf_is_rejected_before_validator) ... ok
test_a_symlinked_member_in_both_is_still_reported (test_release_gate.ChecksThatOnlyFireWhenSourceAndArtifactAgreeTests.test_a_symlinked_member_in_both_is_still_reported) ... ok
test_wrong_sheet_name_in_both_is_still_reported (test_release_gate.ChecksThatOnlyFireWhenSourceAndArtifactAgreeTests.test_wrong_sheet_name_in_both_is_still_reported) ... ok
test_wrong_sprite_version_in_both_is_still_reported (test_release_gate.ChecksThatOnlyFireWhenSourceAndArtifactAgreeTests.test_wrong_sprite_version_in_both_is_still_reported) ... ok
test_constants_are_read_without_importing_the_app (test_release_gate.ExpectedSetTests.test_constants_are_read_without_importing_the_app)
BUNDLED_PET_FILES references BUNDLED_PET_SHEET, so plain literal_eval fails. ... ok
test_expected_members_are_derived_not_hardcoded (test_release_gate.ExpectedSetTests.test_expected_members_are_derived_not_hardcoded)
A literal 16 would silently check a subset once a fifth pet ships. ... ok
test_an_id_disagreeing_with_its_folder_is_refused (test_release_gate.InstallerRefusalsAreMirroredTests.test_an_id_disagreeing_with_its_folder_is_refused)
The installer refuses this pet; shipping it would certify a dud. ... ok
test_every_installer_refusal_has_a_gate_counterpart (test_release_gate.InstallerRefusalsAreMirroredTests.test_every_installer_refusal_has_a_gate_counterpart)
The surface is closed: each rejection below is caught by both. ... ok
test_a_copy_that_fails_midway_leaves_the_old_payload_intact (test_release_gate.ManualBuildAssetSwapTests.test_a_copy_that_fails_midway_leaves_the_old_payload_intact)
Different state from a copy that fails at the start. ... ok
test_a_failing_copy_leaves_the_existing_tree_untouched (test_release_gate.ManualBuildAssetSwapTests.test_a_failing_copy_leaves_the_existing_tree_untouched)
The assertion a destroy-then-copy implementation cannot pass. ... ok
test_a_failing_final_move_preserves_the_old_payload (test_release_gate.ManualBuildAssetSwapTests.test_a_failing_final_move_preserves_the_old_payload)
Fault at the second rename — stage→final. Old payload must survive. ... ok
test_a_failing_restore_keeps_the_backup_and_says_so (test_release_gate.ManualBuildAssetSwapTests.test_a_failing_restore_keeps_the_backup_and_says_so)
The case the old code lied about: restore fails, it claimed success. ... ok
test_assets_are_installed_into_a_fresh_bundle (test_release_gate.ManualBuildAssetSwapTests.test_assets_are_installed_into_a_fresh_bundle) ... ok
test_no_staging_or_backup_residue_is_left_behind (test_release_gate.ManualBuildAssetSwapTests.test_no_staging_or_backup_residue_is_left_behind) ... ok
test_recovery_moves_the_crashed_out_backup_itself (test_release_gate.ManualBuildAssetSwapTests.test_recovery_moves_the_crashed_out_backup_itself)
Recovery must restore *that* directory, not produce a look-alike. ... ok
test_the_next_ordinary_run_self_heals_and_completes (test_release_gate.ManualBuildAssetSwapTests.test_the_next_ordinary_run_self_heals_and_completes)
After the crash, an unmutated run recovers and finishes the job. ... ok
test_a_pristine_payload_passes (test_release_gate.PayloadVerificationTests.test_a_pristine_payload_passes) ... ok
test_cli_exits_non_zero_and_names_the_member (test_release_gate.PayloadVerificationTests.test_cli_exits_non_zero_and_names_the_member) ... ok
test_contents_differing_from_source_are_reported (test_release_gate.PayloadVerificationTests.test_contents_differing_from_source_are_reported) ... ok
test_entirely_absent_payload_is_reported (test_release_gate.PayloadVerificationTests.test_entirely_absent_payload_is_reported) ... ok
test_member_replaced_by_a_symlink_is_reported (test_release_gate.PayloadVerificationTests.test_member_replaced_by_a_symlink_is_reported) ... ok
test_missing_member_is_reported (test_release_gate.PayloadVerificationTests.test_missing_member_is_reported) ... ok
test_missing_readme_is_reported (test_release_gate.PayloadVerificationTests.test_missing_readme_is_reported) ... ok
test_symlink_anywhere_in_the_subtree_is_reported (test_release_gate.PayloadVerificationTests.test_symlink_anywhere_in_the_subtree_is_reported) ... ok
test_unexpected_extra_file_is_reported (test_release_gate.PayloadVerificationTests.test_unexpected_extra_file_is_reported) ... ok
test_wrong_sheet_name_in_metadata_is_reported (test_release_gate.PayloadVerificationTests.test_wrong_sheet_name_in_metadata_is_reported) ... ok
test_wrong_sprite_version_in_metadata_is_reported (test_release_gate.PayloadVerificationTests.test_wrong_sprite_version_in_metadata_is_reported) ... ok
test_a_missing_expected_directory_is_reported (test_release_gate.TreeShapeTests.test_a_missing_expected_directory_is_reported) ... ok
test_a_symlinked_expected_directory_is_refused (test_release_gate.TreeShapeTests.test_a_symlinked_expected_directory_is_refused) ... ok
test_a_symlinked_payload_root_is_refused (test_release_gate.TreeShapeTests.test_a_symlinked_payload_root_is_refused)
os.walk follows the link and cleanly verifies the wrong tree. ... ok
test_an_unexpected_empty_directory_is_reported (test_release_gate.TreeShapeTests.test_an_unexpected_empty_directory_is_reported)
A file-only comparison cannot see a directory with nothing in it. ... ok
test_both_version_keys_equal_app_version (test_release_gate.WritePlistTests.test_both_version_keys_equal_app_version) ... ok
test_replacement_at_temporary_pet_folder_survives_cleanup (test_seeding_identity.SeedingTemporaryIdentityTests.test_replacement_at_temporary_pet_folder_survives_cleanup)
Cleanup must not follow a replaced staging-folder name. ... ok
test_replacement_at_temporary_readme_name_is_not_published_or_cleaned (test_seeding_identity.SeedingTemporaryIdentityTests.test_replacement_at_temporary_readme_name_is_not_published_or_cleaned)
Publish and cleanup must remain bound to the staged README inode. ... ok
test_replacement_between_pet_stage_mkdir_and_open_is_not_used (test_seeding_identity.SeedingTemporaryIdentityTests.test_replacement_between_pet_stage_mkdir_and_open_is_not_used)
Opening and publishing must stay bound to the mkdir-created stage. ... ok
test_copy_failure_never_publishes_a_partial_pet_directory (test_settings_and_install.BundledPetSeedTests.test_copy_failure_never_publishes_a_partial_pet_directory) ... ok
test_destination_root_replaced_after_pets_open_keeps_readmes_fd_anchored (test_settings_and_install.BundledPetSeedTests.test_destination_root_replaced_after_pets_open_keeps_readmes_fd_anchored) ... ok
test_destination_root_replaced_after_safe_open_is_not_followed (test_settings_and_install.BundledPetSeedTests.test_destination_root_replaced_after_safe_open_is_not_followed) ... ok
test_destination_root_symlink_is_not_followed (test_settings_and_install.BundledPetSeedTests.test_destination_root_symlink_is_not_followed) ... ok
test_empty_destination_receives_the_full_distributed_tree (test_settings_and_install.BundledPetSeedTests.test_empty_destination_receives_the_full_distributed_tree) ... ok
test_malformed_or_traversing_pet_metadata_is_never_published (test_settings_and_install.BundledPetSeedTests.test_malformed_or_traversing_pet_metadata_is_never_published) ... ok
test_missing_atomic_directory_publish_primitive_fails_closed (test_settings_and_install.BundledPetSeedTests.test_missing_atomic_directory_publish_primitive_fails_closed) ... ok
test_missing_atomic_file_publish_primitive_never_leaves_a_partial_readme (test_settings_and_install.BundledPetSeedTests.test_missing_atomic_file_publish_primitive_never_leaves_a_partial_readme) ... ok
test_pet_directory_created_during_publish_is_never_replaced (test_settings_and_install.BundledPetSeedTests.test_pet_directory_created_during_publish_is_never_replaced) ... ok
test_pet_metadata_must_reference_the_distributed_spritesheet (test_settings_and_install.BundledPetSeedTests.test_pet_metadata_must_reference_the_distributed_spritesheet) ... ok
test_pet_with_a_missing_required_file_is_never_published (test_settings_and_install.BundledPetSeedTests.test_pet_with_a_missing_required_file_is_never_published) ... ok
test_pet_with_a_symlinked_required_file_is_never_published (test_settings_and_install.BundledPetSeedTests.test_pet_with_a_symlinked_required_file_is_never_published) ... ok
test_pets_directory_replaced_after_safe_open_is_not_followed (test_settings_and_install.BundledPetSeedTests.test_pets_directory_replaced_after_safe_open_is_not_followed) ... ok
test_pets_symlink_inserted_during_destination_creation_is_not_followed (test_settings_and_install.BundledPetSeedTests.test_pets_symlink_inserted_during_destination_creation_is_not_followed) ... ok
test_readme_created_during_publish_is_preserved (test_settings_and_install.BundledPetSeedTests.test_readme_created_during_publish_is_preserved) ... ok
test_root_symlink_inserted_during_destination_creation_is_not_followed (test_settings_and_install.BundledPetSeedTests.test_root_symlink_inserted_during_destination_creation_is_not_followed) ... ok
test_second_seed_is_byte_and_mtime_idempotent (test_settings_and_install.BundledPetSeedTests.test_second_seed_is_byte_and_mtime_idempotent) ... ok
test_symlinked_source_pet_is_not_copied (test_settings_and_install.BundledPetSeedTests.test_symlinked_source_pet_is_not_copied) ... ok
test_upgrade_preserves_every_existing_path_and_adds_only_missing_pets (test_settings_and_install.BundledPetSeedTests.test_upgrade_preserves_every_existing_path_and_adds_only_missing_pets) ... ok
test_apple_silicon_never_falls_back_to_an_unrelated_zip (test_settings_and_install.GithubUpdateTests.test_apple_silicon_never_falls_back_to_an_unrelated_zip) ... ok
test_download_failure_removes_the_new_temporary_directory (test_settings_and_install.GithubUpdateTests.test_download_failure_removes_the_new_temporary_directory) ... ok
test_failed_poll_does_not_consume_the_retry_cooldown (test_settings_and_install.GithubUpdateTests.test_failed_poll_does_not_consume_the_retry_cooldown) ... ok
test_intel_never_falls_back_to_an_arm_only_archive (test_settings_and_install.GithubUpdateTests.test_intel_never_falls_back_to_an_arm_only_archive) ... ok
test_launch_failure_removes_the_new_temporary_directory (test_settings_and_install.GithubUpdateTests.test_launch_failure_removes_the_new_temporary_directory) ... ok
test_replace_script_does_not_destroy_the_installed_app_before_copy_succeeds (test_settings_and_install.GithubUpdateTests.test_replace_script_does_not_destroy_the_installed_app_before_copy_succeeds) ... ok
test_replace_script_preserves_the_installed_app_when_copy_fails (test_settings_and_install.GithubUpdateTests.test_replace_script_preserves_the_installed_app_when_copy_fails) ... ok
test_replace_script_rolls_back_when_the_replacement_cannot_launch (test_settings_and_install.GithubUpdateTests.test_replace_script_rolls_back_when_the_replacement_cannot_launch) ... ok
test_successful_launch_transfers_temp_cleanup_to_the_detached_script (test_settings_and_install.GithubUpdateTests.test_successful_launch_transfers_temp_cleanup_to_the_detached_script) ... ok
test_update_app_preflight_accepts_the_expected_signed_bundle (test_settings_and_install.GithubUpdateTests.test_update_app_preflight_accepts_the_expected_signed_bundle) ... ok
test_update_app_preflight_rejects_identity_version_and_signature_failures (test_settings_and_install.GithubUpdateTests.test_update_app_preflight_rejects_identity_version_and_signature_failures) ... ok
test_update_app_preflight_warns_but_does_not_strand_on_missing_manifest_member (test_settings_and_install.GithubUpdateTests.test_update_app_preflight_warns_but_does_not_strand_on_missing_manifest_member) ... ok
test_update_check_distinguishes_current_from_network_failure (test_settings_and_install.GithubUpdateTests.test_update_check_distinguishes_current_from_network_failure) ... ok
test_update_check_returns_the_selected_release_asset (test_settings_and_install.GithubUpdateTests.test_update_check_returns_the_selected_release_asset) ... ok
test_valid_poll_records_cooldown_and_an_update_becomes_pending (test_settings_and_install.GithubUpdateTests.test_valid_poll_records_cooldown_and_an_update_becomes_pending) ... ok
test_manual_bundle_versions_are_not_hard_coded (test_settings_and_install.PackagingContractTests.test_manual_bundle_versions_are_not_hard_coded) ... ok
test_manual_update_refreshes_bundled_pet_resources (test_settings_and_install.PackagingContractTests.test_manual_update_refreshes_bundled_pet_resources) ... ok
test_readmes_do_not_offer_a_recursive_overwrite_command (test_settings_and_install.PackagingContractTests.test_readmes_do_not_offer_a_recursive_overwrite_command) ... ok
test_startup_seeds_bundled_pets_before_discovery_and_builds_ship_them (test_settings_and_install.PackagingContractTests.test_startup_seeds_bundled_pets_before_discovery_and_builds_ship_them) ... ok
test_generation_check_and_state_update_are_atomic (test_settings_and_install.RefreshGenerationTests.test_generation_check_and_state_update_are_atomic) ... ok
test_only_the_newest_refresh_generation_can_commit (test_settings_and_install.RefreshGenerationTests.test_only_the_newest_refresh_generation_can_commit) ... ok
test_absolute_limit_fields_are_collapsed_but_enabled_behind_advanced_disclosure (test_settings_and_install.SettingsConfigTests.test_absolute_limit_fields_are_collapsed_but_enabled_behind_advanced_disclosure) ... ok
test_atomic_config_write_preserves_old_json_when_replace_fails (test_settings_and_install.SettingsConfigTests.test_atomic_config_write_preserves_old_json_when_replace_fails) ... ok
test_blank_limit_and_percentage_fields_preserve_existing_limits_without_usage_scan (test_settings_and_install.SettingsConfigTests.test_blank_limit_and_percentage_fields_preserve_existing_limits_without_usage_scan) ... ok
test_blank_limit_fields_do_not_override_environment_fallbacks (test_settings_and_install.SettingsConfigTests.test_blank_limit_fields_do_not_override_environment_fallbacks) ... ok
test_calibration_overrides_only_its_matching_direct_limit (test_settings_and_install.SettingsConfigTests.test_calibration_overrides_only_its_matching_direct_limit) ... ok
test_calibration_rejects_a_gauge_with_zero_usage (test_settings_and_install.SettingsConfigTests.test_calibration_rejects_a_gauge_with_zero_usage) ... ok
test_calibration_rejects_a_positive_result_that_rounds_to_zero_tokens (test_settings_and_install.SettingsConfigTests.test_calibration_rejects_a_positive_result_that_rounds_to_zero_tokens) ... ok
test_calibration_usage_scan_failure_is_a_settings_error (test_settings_and_install.SettingsConfigTests.test_calibration_usage_scan_failure_is_a_settings_error) ... ok
test_compute_usage_uses_the_supplied_runtime_snapshot (test_settings_and_install.SettingsConfigTests.test_compute_usage_uses_the_supplied_runtime_snapshot) ... ok
test_direct_only_settings_save_does_not_scan_usage (test_settings_and_install.SettingsConfigTests.test_direct_only_settings_save_does_not_scan_usage) ... ok
test_exact_mode_note_explains_server_calibration_and_estimate_spike_split (test_settings_and_install.SettingsConfigTests.test_exact_mode_note_explains_server_calibration_and_estimate_spike_split) ... ok
test_exact_token_limits_survive_an_unchanged_settings_round_trip (test_settings_and_install.SettingsConfigTests.test_exact_token_limits_survive_an_unchanged_settings_round_trip) ... ok
test_gui_save_path_uses_the_tested_transaction_and_commits_before_close (test_settings_and_install.SettingsConfigTests.test_gui_save_path_uses_the_tested_transaction_and_commits_before_close) ... ok
test_invalid_calibration_rejects_the_whole_candidate (test_settings_and_install.SettingsConfigTests.test_invalid_calibration_rejects_the_whole_candidate) ... ok
test_invalid_direct_limit_rejects_the_whole_candidate (test_settings_and_install.SettingsConfigTests.test_invalid_direct_limit_rejects_the_whole_candidate) ... ok
test_merge_config_updates_preserves_fresh_keys_owned_by_other_paths (test_settings_and_install.SettingsConfigTests.test_merge_config_updates_preserves_fresh_keys_owned_by_other_paths) ... ok
test_merge_retries_instead_of_losing_a_write_between_read_and_save (test_settings_and_install.SettingsConfigTests.test_merge_retries_instead_of_losing_a_write_between_read_and_save) ... ok
test_new_usage_settings_locale_keys_exist_in_every_supported_language (test_settings_and_install.SettingsConfigTests.test_new_usage_settings_locale_keys_exist_in_every_supported_language) ... ok
test_other_numeric_settings_require_finite_in_range_values (test_settings_and_install.SettingsConfigTests.test_other_numeric_settings_require_finite_in_range_values) ... ok
test_percentage_fields_are_primary_and_all_limit_inputs_default_blank (test_settings_and_install.SettingsConfigTests.test_percentage_fields_are_primary_and_all_limit_inputs_default_blank) ... ok
test_session_percentage_only_backsolves_session_and_preserves_other_limits (test_settings_and_install.SettingsConfigTests.test_session_percentage_only_backsolves_session_and_preserves_other_limits) ... ok
test_settings_transaction_applies_calibration_and_preserves_fresh_disk_keys (test_settings_and_install.SettingsConfigTests.test_settings_transaction_applies_calibration_and_preserves_fresh_disk_keys) ... ok
test_settings_transaction_rejects_invalid_input_before_any_apply (test_settings_and_install.SettingsConfigTests.test_settings_transaction_rejects_invalid_input_before_any_apply) ... ok
test_settings_transaction_write_failure_keeps_memory_and_callbacks_untouched (test_settings_and_install.SettingsConfigTests.test_settings_transaction_write_failure_keeps_memory_and_callbacks_untouched) ... ok
test_valid_direct_limits_are_stored_as_integer_tokens (test_settings_and_install.SettingsConfigTests.test_valid_direct_limits_are_stored_as_integer_tokens) ... ok
test_zero_percentage_has_a_distinct_actionable_atomic_rejection (test_settings_and_install.SettingsConfigTests.test_zero_percentage_has_a_distinct_actionable_atomic_rejection) ... ok
test_requirement_accepts_our_own_signed_app (test_signing_contract.CodesignRequirementContractTests.test_requirement_accepts_our_own_signed_app) ... ok
test_requirement_is_parsed_as_a_requirement_not_a_filename (test_signing_contract.CodesignRequirementContractTests.test_requirement_is_parsed_as_a_requirement_not_a_filename)
The exact failure that shipped: codesign reading it as a path. ... ok
test_requirement_rejects_a_bundle_signed_by_someone_else (test_signing_contract.CodesignRequirementContractTests.test_requirement_rejects_a_bundle_signed_by_someone_else)
A requirement that accepted everything would also return 0 here. ... ok
test_requirement_rejects_another_developer_id_signature (test_signing_contract.CodesignRequirementContractTests.test_requirement_rejects_another_developer_id_signature)
Closer case: a real third-party Developer ID, not Apple's own. ... ok
test_assessment_alone_does_not_identify_the_signer (test_signing_contract.GatekeeperAssessmentContractTests.test_assessment_alone_does_not_identify_the_signer)
Why the team check above matters: spctl accepts other vendors too. ... ok
test_assessment_reports_notarization_and_our_team_for_our_app (test_signing_contract.GatekeeperAssessmentContractTests.test_assessment_reports_notarization_and_our_team_for_our_app) ... ok
test_stapler_rejects_a_bundle_with_no_stapled_ticket (test_signing_contract.StaplerContractTests.test_stapler_rejects_a_bundle_with_no_stapled_ticket)
Discrimination: stapler must fail on something unstapled. ... ok
test_stapler_validates_the_installed_app (test_signing_contract.StaplerContractTests.test_stapler_validates_the_installed_app) ... ok
test_the_real_installed_app_passes_the_whole_preflight (test_signing_contract.ValidateUpdateAppLiveTests.test_the_real_installed_app_passes_the_whole_preflight)
End-to-end, unmocked: the path a real update actually takes. ... ok
test_direct_execution_reaches_dispatch_exactly_once (test_source_guard.SourceGuardTests.test_direct_execution_reaches_dispatch_exactly_once) ... ok
test_guarded_source_is_inert_and_defines_functions (test_source_guard.SourceGuardTests.test_guarded_source_is_inert_and_defines_functions) ... ok
test_removing_the_guard_makes_source_reach_dispatch_once (test_source_guard.SourceGuardTests.test_removing_the_guard_makes_source_reach_dispatch_once) ... ok
test_absolute_symlink_target_anywhere_in_the_bundle_is_rejected (test_updater.BundleContainmentTests.test_absolute_symlink_target_anywhere_in_the_bundle_is_rejected) ... ok
test_framework_style_relative_symlink_inside_the_bundle_is_accepted (test_updater.BundleContainmentTests.test_framework_style_relative_symlink_inside_the_bundle_is_accepted) ... ok
test_missing_manifest_members_still_only_warn (test_updater.BundleContainmentTests.test_missing_manifest_members_still_only_warn)
Policy guard: missing assets must not strand users on an old build. ... ok
test_relative_symlink_escaping_the_bundle_is_rejected (test_updater.BundleContainmentTests.test_relative_symlink_escaping_the_bundle_is_rejected)
Which rule does the work: the realpath containment one, and only it. ... ok
test_symlink_in_the_pet_subtree_is_rejected_even_when_contained (test_updater.BundleContainmentTests.test_symlink_in_the_pet_subtree_is_rejected_even_when_contained)
Ours, and it legitimately contains zero symlinks — so any is a red flag. ... ok
test_symlinked_ancestor_of_the_pet_subtree_is_rejected (test_updater.BundleContainmentTests.test_symlinked_ancestor_of_the_pet_subtree_is_rejected) ... ok
test_a_failed_check_leaves_no_stale_choice_behind (test_updater.CheckGithubUpdateShapeTests.test_a_failed_check_leaves_no_stale_choice_behind) ... ok
test_a_non_update_result_leaves_no_stale_choice_behind (test_updater.CheckGithubUpdateShapeTests.test_a_non_update_result_leaves_no_stale_choice_behind) ... ok
test_poll_still_publishes_the_two_tuple_the_ui_reads (test_updater.CheckGithubUpdateShapeTests.test_poll_still_publishes_the_two_tuple_the_ui_reads) ... ok
test_update_records_the_chosen_asset_and_arch_in_the_cache (test_updater.CheckGithubUpdateShapeTests.test_update_records_the_chosen_asset_and_arch_in_the_cache)
Per key, by name — `asset` and `arch` are bound through the ... ok
test_a_second_install_is_refused_while_the_first_helper_lives (test_updater.ConcurrentInstallTests.test_a_second_install_is_refused_while_the_first_helper_lives)
The same property at the entry point the app actually calls. ... ok
test_an_install_is_possible_again_once_the_first_helper_exits (test_updater.ConcurrentInstallTests.test_an_install_is_possible_again_once_the_first_helper_exits)
Discrimination for the test above: the refusal is not permanent. ... ok
test_one_install_succeeds_and_schedules_exactly_one_helper (test_updater.ConcurrentInstallTests.test_one_install_succeeds_and_schedules_exactly_one_helper)
Control: without it, an installer that always refused would pass. ... ok
test_the_lock_changes_hands_and_is_released_by_the_kernel (test_updater.ConcurrentInstallTests.test_the_lock_changes_hands_and_is_released_by_the_kernel)
The whole handoff lifecycle, in one fixture. ... ok
test_patching_the_retired_name_intercepts_nothing_and_reaches_out (test_updater.DownloadSeamInstrumentTests.test_patching_the_retired_name_intercepts_nothing_and_reaches_out)
The mutant: the fixture style this file used to use, run. ... ok
test_production_downloads_through_the_name_the_fixtures_patch (test_updater.DownloadSeamInstrumentTests.test_production_downloads_through_the_name_the_fixtures_patch) ... ok
test_the_guard_lets_loopback_through (test_updater.DownloadSeamInstrumentTests.test_the_guard_lets_loopback_through)
Negative control: it blocks by destination, not by being a socket. ... ok
test_the_guard_records_and_refuses_a_direct_request (test_updater.DownloadSeamInstrumentTests.test_the_guard_records_and_refuses_a_direct_request)
Positive control: the guard fires when nothing is patched at all. ... ok
test_the_module_under_test_is_the_repository_copy (test_updater.DownloadSeamInstrumentTests.test_the_module_under_test_is_the_repository_copy)
Everything below reads production source; this says whose. ... ok
test_the_stand_in_intercepts_the_download (test_updater.DownloadSeamInstrumentTests.test_the_stand_in_intercepts_the_download) ... ok
test_a_missing_operand_fails_loudly_rather_than_creating_anything (test_updater.ExchangeHelperTests.test_a_missing_operand_fails_loudly_rather_than_creating_anything) ... ok
test_two_directories_are_exchanged_in_place (test_updater.ExchangeHelperTests.test_two_directories_are_exchanged_in_place) ... ok
test_wrong_argument_count_is_an_error (test_updater.ExchangeHelperTests.test_wrong_argument_count_is_an_error) ... ok
test_install_refuses_before_downloading_anything (test_updater.ExpectedVersionRequiredTests.test_install_refuses_before_downloading_anything) ... ok
test_preflight_rejects_a_missing_or_blank_expectation (test_updater.ExpectedVersionRequiredTests.test_preflight_rejects_a_missing_or_blank_expectation) ... ok
test_each_rejected_record_is_rejected_for_its_own_reason (test_updater.LaunchRegistrationInstrumentTests.test_each_rejected_record_is_rejected_for_its_own_reason)
Without this, one over-broad filter would look like a clean pass. ... ok
test_no_fixture_bundle_of_this_run_claims_the_production_identity (test_updater.LaunchRegistrationInstrumentTests.test_no_fixture_bundle_of_this_run_claims_the_production_identity)
The assertion itself, run early enough to attribute. ... ok
test_the_parser_reads_the_real_database (test_updater.LaunchRegistrationInstrumentTests.test_the_parser_reads_the_real_database)
The synthetic dump above proves nothing about the real format. ... ok
test_the_parser_selects_by_identifier_and_by_root (test_updater.LaunchRegistrationInstrumentTests.test_the_parser_selects_by_identifier_and_by_root) ... ok
test_a_child_process_computes_the_lock_path_from_the_fixture_home (test_updater.LockIsolationInstrumentTests.test_a_child_process_computes_the_lock_path_from_the_fixture_home)
The constant patch does not cross a process boundary; HOME does. ... ok
test_the_bypass_alarm_notices_each_way_the_watched_paths_can_change (test_updater.LockIsolationInstrumentTests.test_the_bypass_alarm_notices_each_way_the_watched_paths_can_change)
Mutation-style check of the alarm's own discrimination. ... ok
test_the_lock_lands_in_the_fixture_cache_not_the_real_one (test_updater.LockIsolationInstrumentTests.test_the_lock_lands_in_the_fixture_cache_not_the_real_one)
The redirection is load-bearing, not decorative. ... ok
test_the_real_bundle_contains_the_symlinks_this_guard_is_about (test_updater.RealBundleAcceptanceTests.test_the_real_bundle_contains_the_symlinks_this_guard_is_about)
Discrimination: without an internal symlink the guard above is vacuous. ... 
[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
test_the_real_installed_bundle_is_accepted_by_the_preflight (test_updater.RealBundleAcceptanceTests.test_the_real_installed_bundle_is_accepted_by_the_preflight) ... 
[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
test_a_completed_update_never_leaves_the_install_path_empty (test_updater.ReplaceScriptBehaviourTests.test_a_completed_update_never_leaves_the_install_path_empty)
There is no instant at which the app is absent from its own path. ... ok
test_a_launch_that_is_never_acknowledged_rolls_back (test_updater.ReplaceScriptBehaviourTests.test_a_launch_that_is_never_acknowledged_rolls_back)
`open` exiting 0 is a dispatch, not a health signal. ... ok
test_a_launch_visible_only_to_the_fallback_pattern_is_acknowledged (test_updater.ReplaceScriptBehaviourTests.test_a_launch_visible_only_to_the_fallback_pattern_is_acknowledged)
The fallback branch must actually be reachable. ... ok
test_a_process_running_before_the_update_never_acknowledges_it (test_updater.ReplaceScriptBehaviourTests.test_a_process_running_before_the_update_never_acknowledges_it)
The false ACK that matters in practice. ... ok
test_a_process_that_dies_during_the_settle_delay_rolls_back (test_updater.ReplaceScriptBehaviourTests.test_a_process_that_dies_during_the_settle_delay_rolls_back)
A bundle that starts and immediately crashes is not a live app. ... ok
test_a_python_process_running_before_the_update_never_acknowledges_it (test_updater.ReplaceScriptBehaviourTests.test_a_python_process_running_before_the_update_never_acknowledges_it)
Same contract on the fallback pattern, which is a separate branch. ... ok
test_a_rollback_that_cannot_move_the_new_app_aside_keeps_the_old_one (test_updater.ReplaceScriptBehaviourTests.test_a_rollback_that_cannot_move_the_new_app_aside_keeps_the_old_one)
The nesting hole, made deterministic. ... ok
test_a_stage_tampered_with_after_ditto_is_never_installed (test_updater.ReplaceScriptBehaviourTests.test_a_stage_tampered_with_after_ditto_is_never_installed)
The installer's second validation rejects the exact staged copy. ... ok
test_a_stale_process_cannot_cover_for_one_that_died_during_settle (test_updater.ReplaceScriptBehaviourTests.test_a_stale_process_cannot_cover_for_one_that_died_during_settle)
The settle check must confirm *that* pid, not re-scan for any match. ... ok
test_an_acknowledged_launch_completes_the_swap_atomically (test_updater.ReplaceScriptBehaviourTests.test_an_acknowledged_launch_completes_the_swap_atomically)
The atomic path specifically — the branch every real machine takes. ... ok
test_an_unrelated_process_mentioning_the_path_is_not_an_acknowledgement (test_updater.ReplaceScriptBehaviourTests.test_an_unrelated_process_mentioning_the_path_is_not_an_acknowledgement)
The anchor test: a third-party process mentioning the path. ... ok
test_an_unrelated_process_mentioning_the_resources_path_is_not_an_ack (test_updater.ReplaceScriptBehaviourTests.test_an_unrelated_process_mentioning_the_resources_path_is_not_an_ack)
The fallback pattern must not match loosely either. ... ok
test_atomic_exchange_failure_never_starts_a_move_fallback (test_updater.ReplaceScriptBehaviourTests.test_atomic_exchange_failure_never_starts_a_move_fallback)
Both exchange helpers fail; exact old APP remains and no backup moves. ... ok
test_rollback_survives_a_new_bundle_with_a_broken_interpreter (test_updater.ReplaceScriptBehaviourTests.test_rollback_survives_a_new_bundle_with_a_broken_interpreter)
The only time rollback runs is when the new bundle is bad. ... ok
test_the_old_app_survives_a_rollback_on_the_atomic_path (test_updater.ReplaceScriptBehaviourTests.test_the_old_app_survives_a_rollback_on_the_atomic_path)
Old-copy preservation on the exchange path specifically. ... ok
test_the_swap_fails_closed_without_any_bundled_interpreter (test_updater.ReplaceScriptBehaviourTests.test_the_swap_fails_closed_without_any_bundled_interpreter)
No atomic helper means no update; APP stays the exact old object. ... ok
test_a_retained_backup_is_recorded_where_the_user_can_find_it (test_updater.ReplaceScriptTextTests.test_a_retained_backup_is_recorded_where_the_user_can_find_it) ... ok
test_constructor_refuses_to_invent_missing_caller_identities (test_updater.ReplaceScriptTextTests.test_constructor_refuses_to_invent_missing_caller_identities) ... ok
test_execution_harness_neutralizes_the_primitive_before_consumers (test_updater.ReplaceScriptTextTests.test_execution_harness_neutralizes_the_primitive_before_consumers) ... ok
test_forward_replacement_is_atomic_only_and_fails_closed (test_updater.ReplaceScriptTextTests.test_forward_replacement_is_atomic_only_and_fails_closed)
A failed exchange must not reopen the old two-move install window. ... ok
test_launch_grammar_is_one_definition_and_two_exact_consumers (test_updater.ReplaceScriptTextTests.test_launch_grammar_is_one_definition_and_two_exact_consumers) ... ok
test_launch_is_acknowledged_by_a_process_match_not_by_opens_exit_code (test_updater.ReplaceScriptTextTests.test_launch_is_acknowledged_by_a_process_match_not_by_opens_exit_code)
`open` returning 0 means dispatched, not running. ... ok
test_rollback_never_reaches_for_the_new_bundles_interpreter (test_updater.ReplaceScriptTextTests.test_rollback_never_reaches_for_the_new_bundles_interpreter)
Recovery must not depend on the thing it is recovering from. ... ok
test_same_filesystem_is_checked_after_staging_and_before_the_swap (test_updater.ReplaceScriptTextTests.test_same_filesystem_is_checked_after_staging_and_before_the_swap)
A cross-device swap cannot be atomic, and mv would copy instead. ... ok
test_script_carries_the_callers_exact_app_and_work_identities (test_updater.ReplaceScriptTextTests.test_script_carries_the_callers_exact_app_and_work_identities) ... ok
test_script_keeps_the_literal_substrings_other_tests_pin (test_updater.ReplaceScriptTextTests.test_script_keeps_the_literal_substrings_other_tests_pin) ... ok
test_swap_goes_through_the_bundled_interpreter (test_updater.ReplaceScriptTextTests.test_swap_goes_through_the_bundled_interpreter) ... ok
test_the_ordering_check_notices_the_device_check_moving (test_updater.ReplaceScriptTextTests.test_the_ordering_check_notices_the_device_check_moving)
Control: the assertion above must be able to fail. ... ok
test_the_rollback_check_notices_an_interpreter_from_the_new_bundle (test_updater.ReplaceScriptTextTests.test_the_rollback_check_notices_an_interpreter_from_the_new_bundle)
Control: substitute the failed bundle's interpreter and it fails. ... ok
test_a_bundle_whose_executable_lacks_this_architecture_is_rejected (test_updater.RequiredArchitectureTests.test_a_bundle_whose_executable_lacks_this_architecture_is_rejected) ... ok
test_a_bundled_interpreter_lacking_this_architecture_is_rejected (test_updater.RequiredArchitectureTests.test_a_bundled_interpreter_lacking_this_architecture_is_rejected)
The helper the swap itself runs — a mismatch breaks the update path. ... ok
test_a_native_and_a_universal_bundle_are_both_accepted (test_updater.RequiredArchitectureTests.test_a_native_and_a_universal_bundle_are_both_accepted)
Control: the check must not reject the two shapes we ship. ... ok
test_the_main_executable_and_info_plist_must_be_regular_files (test_updater.RequiredArchitectureTests.test_the_main_executable_and_info_plist_must_be_regular_files)
Both are read to decide identity; a symlink decides it elsewhere. ... ok
test_a_non_https_or_hostless_url_is_never_selected (test_updater.SelectUpdateAssetTests.test_a_non_https_or_hostless_url_is_never_selected) ... ok
test_apple_silicon_accepts_the_universal_archive_alone (test_updater.SelectUpdateAssetTests.test_apple_silicon_accepts_the_universal_archive_alone) ... ok
test_apple_silicon_prefers_the_arm_archive (test_updater.SelectUpdateAssetTests.test_apple_silicon_prefers_the_arm_archive) ... ok
test_case_and_surrounding_whitespace_are_normalized (test_updater.SelectUpdateAssetTests.test_case_and_surrounding_whitespace_are_normalized) ... ok
test_duplicate_unrelated_names_do_not_block_a_clean_choice (test_updater.SelectUpdateAssetTests.test_duplicate_unrelated_names_do_not_block_a_clean_choice)
Discrimination: the ambiguity rule is about the *allowed* name only. ... ok
test_intel_never_takes_the_arm_only_archive (test_updater.SelectUpdateAssetTests.test_intel_never_takes_the_arm_only_archive) ... ok
test_intel_takes_the_universal_archive (test_updater.SelectUpdateAssetTests.test_intel_takes_the_universal_archive) ... ok
test_malformed_asset_entries_do_not_raise (test_updater.SelectUpdateAssetTests.test_malformed_asset_entries_do_not_raise) ... ok
test_names_are_matched_only_against_the_allow_list (test_updater.SelectUpdateAssetTests.test_names_are_matched_only_against_the_allow_list) ... ok
test_two_assets_normalizing_to_one_allowed_name_are_ambiguous (test_updater.SelectUpdateAssetTests.test_two_assets_normalizing_to_one_allowed_name_are_ambiguous)
Two candidates for the same slot: we cannot know which is the app. ... ok
test_unknown_architecture_is_rejected_rather_than_defaulted (test_updater.SelectUpdateAssetTests.test_unknown_architecture_is_rejected_rather_than_defaulted) ... ok
test_codesign_call_binds_the_exact_expected_team_requirement (test_updater.SigningAuthorityPreflightTests.test_codesign_call_binds_the_exact_expected_team_requirement) ... ok
test_codesign_failure_rejects_before_gatekeeper_and_ticket (test_updater.SigningAuthorityPreflightTests.test_codesign_failure_rejects_before_gatekeeper_and_ticket) ... ok
test_spctl_success_with_foreign_origin_is_rejected_even_when_path_has_team_id (test_updater.SigningAuthorityPreflightTests.test_spctl_success_with_foreign_origin_is_rejected_even_when_path_has_team_id) ... ok
test_spctl_success_without_origin_is_rejected_even_when_path_has_team_id (test_updater.SigningAuthorityPreflightTests.test_spctl_success_without_origin_is_rejected_even_when_path_has_team_id) ... ok
test_stapler_rejects_an_unstapled_bundle_with_rc_65 (test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65) ... 
[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
test_stapler_reports_success_for_our_stapled_bundle (test_updater.StaplerLiveContractTests.test_stapler_reports_success_for_our_stapled_bundle) ... 
[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
test_a_tool_that_cannot_run_fails_closed (test_updater.StaplerPreflightTests.test_a_tool_that_cannot_run_fails_closed) ... ok
test_an_unstapled_bundle_is_refused (test_updater.StaplerPreflightTests.test_an_unstapled_bundle_is_refused) ... ok
test_every_preflight_tool_runs_under_a_timeout (test_updater.StaplerPreflightTests.test_every_preflight_tool_runs_under_a_timeout)
A hung signing tool must not wedge the update thread forever. ... ok
test_preflight_consults_stapler (test_updater.StaplerPreflightTests.test_preflight_consults_stapler) ... ok
test_a_traversing_member_is_rejected_before_extraction (test_updater.ZipMemberScanTests.test_a_traversing_member_is_rejected_before_extraction) ... ok
test_an_absolute_member_is_rejected_before_extraction (test_updater.ZipMemberScanTests.test_an_absolute_member_is_rejected_before_extraction) ... ok
test_an_ordinary_archive_still_reaches_extraction (test_updater.ZipMemberScanTests.test_an_ordinary_archive_still_reaches_extraction)
Guard: the scan must not reject the archive we actually ship. ... ok
test_an_unreadable_archive_is_rejected_before_extraction (test_updater.ZipMemberScanTests.test_an_unreadable_archive_is_rejected_before_extraction) ... ok
test_universal_named_arm_only_bundle_is_rejected_via_lipo (test_updater_adversarial.ArchitectureBindingTests.test_universal_named_arm_only_bundle_is_rejected_via_lipo) ... ok
test_atomic_branch_never_moves_old_stage_to_a_backup_name (test_updater_adversarial.AtomicExchangeRecoveryTests.test_atomic_branch_never_moves_old_stage_to_a_backup_name) ... ok
test_fault_immediately_after_exchange_restores_or_retains_old_app (test_updater_adversarial.AtomicExchangeRecoveryTests.test_fault_immediately_after_exchange_restores_or_retains_old_app) ... ok
test_info_plist_must_be_a_regular_non_symlink (test_updater_adversarial.CriticalMemberTypeTests.test_info_plist_must_be_a_regular_non_symlink) ... ok
test_main_executable_directory_is_not_a_regular_file (test_updater_adversarial.CriticalMemberTypeTests.test_main_executable_directory_is_not_a_regular_file) ... ok
test_main_executable_must_be_a_regular_non_symlink (test_updater_adversarial.CriticalMemberTypeTests.test_main_executable_must_be_a_regular_non_symlink) ... ok
test_nonexecutable_regular_macho_helper_is_rejected_before_popen (test_updater_adversarial.CriticalMemberTypeTests.test_nonexecutable_regular_macho_helper_is_rejected_before_popen) ... ok
test_only_a_pid_created_after_launch_can_ack (test_updater_adversarial.LaunchAcknowledgementTests.test_only_a_pid_created_after_launch_can_ack) ... ok
test_preexisting_macos_and_resources_pids_cannot_ack (test_updater_adversarial.LaunchAcknowledgementTests.test_preexisting_macos_and_resources_pids_cannot_ack) ... ok
test_same_ack_pid_must_survive_even_if_a_replacement_pid_exists (test_updater_adversarial.LaunchAcknowledgementTests.test_same_ack_pid_must_survive_even_if_a_replacement_pid_exists) ... ok
test_cleanup_does_not_follow_stage_name_substitution (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_cleanup_does_not_follow_stage_name_substitution) ... ok
test_empty_dir_at_does_not_follow_directory_child_after_lstat_swap (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_empty_dir_at_does_not_follow_directory_child_after_lstat_swap) ... ok
test_empty_dir_at_does_not_unlink_file_child_after_lstat_swap (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_empty_dir_at_does_not_unlink_file_child_after_lstat_swap) ... ok
test_exchange_failure_keeps_exact_old_app_without_forward_mv_backup (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_exchange_failure_keeps_exact_old_app_without_forward_mv_backup)
Atomic exchange failure must stop before any forward-path move. ... ok
test_fd_bound_discard_preserves_root_replaced_after_fstat (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_fd_bound_discard_preserves_root_replaced_after_fstat)
The standalone discard must keep using its verified directory fd. ... ok
test_fifo_lock_leaf_fails_closed_without_blocking (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_fifo_lock_leaf_fails_closed_without_blocking) ... ok
test_fifo_lock_root_fails_closed_without_blocking (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_fifo_lock_root_fails_closed_without_blocking) ... ok
test_helper_binds_installed_app_identity_handed_off_by_python (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_helper_binds_installed_app_identity_handed_off_by_python)
A rival APP substituted after Popen handoff must never be swapped. ... ok
test_helper_refuses_stage_replaced_after_handoff_before_exchange (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_helper_refuses_stage_replaced_after_handoff_before_exchange)
The app installed by exchange must be the exact claimed STAGE. ... ok
test_helper_work_cleanup_uses_fd_bound_discard_and_preserves_rival (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_helper_work_cleanup_uses_fd_bound_discard_and_preserves_rival)
Detached cleanup binds WORKID through the standalone fd helper. ... ok
test_lock_residue_is_under_complete_uninstall_owned_root (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_lock_residue_is_under_complete_uninstall_owned_root) ... ok
test_lock_root_symlink_is_refused_without_outside_creation (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_lock_root_symlink_is_refused_without_outside_creation) ... ok
test_manual_replacement_appid_mismatch_refuses_cross_path_swap (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_manual_replacement_appid_mismatch_refuses_cross_path_swap)
A manual replacement racing the updater is an APPID mismatch. ... ok
test_owned_private_lock_root_has_normal_acquire_release_lifecycle (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_owned_private_lock_root_has_normal_acquire_release_lifecycle) ... ok
test_partial_stage_copy_failure_removes_only_owned_candidate (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_partial_stage_copy_failure_removes_only_owned_candidate) ... ok
test_preexisting_backup_name_is_never_changed_or_deleted (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_preexisting_backup_name_is_never_changed_or_deleted) ... ok
test_preexisting_stage_name_collision_never_deletes_the_sentinel (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_preexisting_stage_name_collision_never_deletes_the_sentinel) ... ok
test_prehandoff_cleanup_binds_stage_beneath_open_parent (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_prehandoff_cleanup_binds_stage_beneath_open_parent)
A stage rival inserted after parent-open must not be traversed. ... ok
test_public_sibling_regular_file_is_never_selected_or_changed (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_public_sibling_regular_file_is_never_selected_or_changed) ... ok
test_python_failure_cleanup_does_not_follow_work_name_substitution (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_python_failure_cleanup_does_not_follow_work_name_substitution)
Failure cleanup must delete the claimed WORK, never its pathname. ... ok
test_replaced_lock_root_cannot_create_a_second_lock_domain (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_replaced_lock_root_cannot_create_a_second_lock_domain)
One app must not acquire two locks through two same-named roots. ... ok
test_rival_reclaim_after_claim_release_is_never_consumed_or_deleted (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_rival_reclaim_after_claim_release_is_never_consumed_or_deleted)
Covers the separate mkdir-then-rmdir staging-name race. ... ok
test_symlink_lock_leaf_fails_closed_without_target_change (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_symlink_lock_leaf_fails_closed_without_target_change) ... ok
test_world_writable_lock_root_is_refused (test_updater_adversarial.LockAndTemporaryNameSafetyTests.test_world_writable_lock_root_is_refused) ... ok
test_post_ditto_mutation_is_seen_by_full_stage_revalidation (test_updater_adversarial.StagedCopyRevalidationTests.test_post_ditto_mutation_is_seen_by_full_stage_revalidation)
Valid NEW plus invalid STAGE must not dispatch a replacement. ... ok
test_background_descendant_cannot_retain_lock_after_return (test_updater_adversarial.UpdateLockCommandWrapperTests.test_background_descendant_cannot_retain_lock_after_return)
Only the wrapper owns the fd; a surviving grandchild cannot. ... ok
test_busy_lock_returns_100_without_starting_child (test_updater_adversarial.UpdateLockCommandWrapperTests.test_busy_lock_returns_100_without_starting_child) ... ok
test_child_return_code_is_passed_through_exactly (test_updater_adversarial.UpdateLockCommandWrapperTests.test_child_return_code_is_passed_through_exactly) ... ok
test_child_signal_is_mapped_to_128_plus_signal (test_updater_adversarial.UpdateLockCommandWrapperTests.test_child_signal_is_mapped_to_128_plus_signal) ... ok
test_exec_failure_returns_127_and_releases_lock (test_updater_adversarial.UpdateLockCommandWrapperTests.test_exec_failure_returns_127_and_releases_lock) ... ok
test_untrusted_lock_root_returns_101_without_outside_write (test_updater_adversarial.UpdateLockCommandWrapperTests.test_untrusted_lock_root_returns_101_without_outside_write) ... ok
test_usage_errors_return_2_without_lock_or_child (test_updater_adversarial.UpdateLockCommandWrapperTests.test_usage_errors_return_2_without_lock_or_child) ... ok
test_complete_uninstall_waits_for_active_update_transaction (test_updater_adversarial.UpdateLockLifecycleTests.test_complete_uninstall_waits_for_active_update_transaction) ... ok
test_install_hands_lock_to_child_and_serializes_real_transactions (test_updater_adversarial.UpdateLockLifecycleTests.test_install_hands_lock_to_child_and_serializes_real_transactions)
Distinguishes early close, missing lock, and parent fd leakage. ... ok
test_mkdtemp_exception_releases_lock_before_any_io (test_updater_adversarial.UpdateLockLifecycleTests.test_mkdtemp_exception_releases_lock_before_any_io) ... ok
test_uninstall_popen_failure_preserves_app_and_all_settings (test_updater_adversarial.UpdateLockLifecycleTests.test_uninstall_popen_failure_preserves_app_and_all_settings)
Preparing the deletion helper must precede every destructive step. ... ok
test_absolute_unix_symlink_target_with_child_member_is_rejected (test_updater_adversarial.ZipSymlinkPreExtractionTests.test_absolute_unix_symlink_target_with_child_member_is_rejected) ... ok
test_parent_unix_symlink_target_with_child_member_is_rejected (test_updater_adversarial.ZipSymlinkPreExtractionTests.test_parent_unix_symlink_target_with_child_member_is_rejected) ... ok
test_a_clean_archive_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_clean_archive_is_accepted)
The control. Without it every rejection below could be a blanket no. ... ok
test_a_contained_relative_symlink_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_contained_relative_symlink_is_accepted) ... ok
test_a_missing_artifact_is_rejected_rather_than_skipped (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_missing_artifact_is_rejected_rather_than_skipped) ... ok
test_a_symlink_member_escaping_the_archive_is_rejected (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_symlink_member_escaping_the_archive_is_rejected)
The member kind a name-only scan cannot see. ... ok
test_a_traversing_member_is_rejected (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_traversing_member_is_rejected) ... ok
test_an_absolute_member_is_rejected (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_an_absolute_member_is_rejected) ... ok
test_the_symlink_fixture_really_is_a_symlink (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_the_symlink_fixture_really_is_a_symlink)
Discrimination: if the entry is a plain file, the test above is a lie. ... ok
test_every_name_the_updater_accepts_is_one_release_builds (test_upload_artifact_gate.AssetNameCouplingTests.test_every_name_the_updater_accepts_is_one_release_builds)
The other direction, which is a different failure. ... ok
test_every_zip_release_builds_is_one_the_updater_will_accept (test_upload_artifact_gate.AssetNameCouplingTests.test_every_zip_release_builds_is_one_the_updater_will_accept) ... ok
test_this_module_reads_the_real_names_rather_than_its_own_copy (test_upload_artifact_gate.AssetNameCouplingTests.test_this_module_reads_the_real_names_rather_than_its_own_copy)
My own blindness to the same coupling, pinned. ... ok
test_detach_failure_is_gate_failure_and_retains_the_named_mount (test_upload_artifact_gate.DmgArmTests.test_detach_failure_is_gate_failure_and_retains_the_named_mount) ... ok
test_dmg_is_detached_after_a_successful_check (test_upload_artifact_gate.DmgArmTests.test_dmg_is_detached_after_a_successful_check) ... ok
test_dmg_mountpoint_exists_before_attach (test_upload_artifact_gate.DmgArmTests.test_dmg_mountpoint_exists_before_attach)
The regression this arm was fixed for: attach needs the dir first. ... ok
test_dmg_that_fails_to_attach_fails_the_gate (test_upload_artifact_gate.DmgArmTests.test_dmg_that_fails_to_attach_fails_the_gate) ... ok
test_dmg_with_a_wrongly_named_app_fails_and_still_detaches (test_upload_artifact_gate.DmgArmTests.test_dmg_with_a_wrongly_named_app_fails_and_still_detaches)
A rejection must not leave the image mounted. ... ok
test_dmg_with_two_root_apps_fails_and_still_detaches (test_upload_artifact_gate.DmgArmTests.test_dmg_with_two_root_apps_fails_and_still_detaches)
Now constructible, and the detach path must hold for it too. ... ok
test_sentinels_would_notice_a_path_that_did_not_exist_before (test_upload_artifact_gate.EnvironmentIsolationLimitsTests.test_sentinels_would_notice_a_path_that_did_not_exist_before)
`assertNothingEscaped` must catch CREATION, not only growth. ... ok
test_the_password_database_ignores_our_HOME (test_upload_artifact_gate.EnvironmentIsolationLimitsTests.test_the_password_database_ignores_our_HOME)
The bypass, shown end to end in a shell we ourselves sandboxed. ... ok
test_the_gate_fragment_is_self_contained (test_upload_artifact_gate.FragmentCompletenessTests.test_the_gate_fragment_is_self_contained) ... ok
test_the_publish_fragment_is_self_contained (test_upload_artifact_gate.FragmentCompletenessTests.test_the_publish_fragment_is_self_contained) ... ok
test_this_check_can_actually_detect_a_missing_callee (test_upload_artifact_gate.FragmentCompletenessTests.test_this_check_can_actually_detect_a_missing_callee)
Discrimination: otherwise a broken regex reports self-contained. ... ok
test_an_unconfigured_ditto_is_poisoned_rather_than_real (test_upload_artifact_gate.HarnessContainmentTests.test_an_unconfigured_ditto_is_poisoned_rather_than_real)
Forgetting `setup_ditto` must be loud, not plausible. ... ok
test_an_unconfigured_hdiutil_is_poisoned_rather_than_real (test_upload_artifact_gate.HarnessContainmentTests.test_an_unconfigured_hdiutil_is_poisoned_rather_than_real) ... ok
test_mktemp_refuses_to_run_without_a_TMPDIR (test_upload_artifact_gate.HarnessContainmentTests.test_mktemp_refuses_to_run_without_a_TMPDIR)
The failure mode the shim exists for, exercised directly. ... ok
test_temporary_allocation_stays_inside_the_sandbox (test_upload_artifact_gate.HarnessContainmentTests.test_temporary_allocation_stays_inside_the_sandbox) ... ok
test_the_gate_allocates_at_all (test_upload_artifact_gate.HarnessContainmentTests.test_the_gate_allocates_at_all)
Discrimination: `assertAllocationsWereContained` is vacuous if not. ... ok
test_hdiutil_failure_quarantines_partial_dmg_and_removes_stage (test_upload_artifact_gate.OneDmgPackagingTests.test_hdiutil_failure_quarantines_partial_dmg_and_removes_stage) ... ok
test_notary_failure_quarantines_dmg_and_removes_stage (test_upload_artifact_gate.OneDmgPackagingTests.test_notary_failure_quarantines_dmg_and_removes_stage) ... ok
test_staple_failure_quarantines_dmg_and_removes_stage (test_upload_artifact_gate.OneDmgPackagingTests.test_staple_failure_quarantines_dmg_and_removes_stage) ... ok
test_success_runs_create_notary_staple_validate_in_exact_order (test_upload_artifact_gate.OneDmgPackagingTests.test_success_runs_create_notary_staple_validate_in_exact_order) ... ok
test_validate_failure_text_with_zero_status_is_still_failure (test_upload_artifact_gate.OneDmgPackagingTests.test_validate_failure_text_with_zero_status_is_still_failure) ... ok
test_validate_nonzero_quarantines_dmg_and_removes_stage (test_upload_artifact_gate.OneDmgPackagingTests.test_validate_nonzero_quarantines_dmg_and_removes_stage) ... ok
test_a_later_artifact_failing_stops_every_upload (test_upload_artifact_gate.PublishBehaviourTests.test_a_later_artifact_failing_stops_every_upload)
The one a first-file-only gate would pass. ... ok
test_all_artifacts_good_does_reach_gh (test_upload_artifact_gate.PublishBehaviourTests.test_all_artifacts_good_does_reach_gh) ... ok
test_assets_subcommand_blocks_a_missing_file_before_any_artifact_opens (test_upload_artifact_gate.PublishBehaviourTests.test_assets_subcommand_blocks_a_missing_file_before_any_artifact_opens) ... ok
test_assets_subcommand_blocks_a_wrong_four_name_set (test_upload_artifact_gate.PublishBehaviourTests.test_assets_subcommand_blocks_a_wrong_four_name_set) ... ok
test_assets_subcommand_receives_exactly_the_four_release_names (test_upload_artifact_gate.PublishBehaviourTests.test_assets_subcommand_receives_exactly_the_four_release_names) ... ok
test_detach_failure_retains_the_mount_and_blocks_gh (test_upload_artifact_gate.PublishBehaviourTests.test_detach_failure_retains_the_mount_and_blocks_gh) ... ok
test_every_artifact_is_verified_before_the_first_gh_call (test_upload_artifact_gate.PublishBehaviourTests.test_every_artifact_is_verified_before_the_first_gh_call) ... ok
test_no_gh_call_when_the_archive_scan_fails (test_upload_artifact_gate.PublishBehaviourTests.test_no_gh_call_when_the_archive_scan_fails) ... ok
test_no_gh_call_when_the_artifact_carries_an_extra_app (test_upload_artifact_gate.PublishBehaviourTests.test_no_gh_call_when_the_artifact_carries_an_extra_app) ... ok
test_no_gh_call_when_the_artifact_is_corrupt (test_upload_artifact_gate.PublishBehaviourTests.test_no_gh_call_when_the_artifact_is_corrupt) ... ok
test_no_gh_call_when_the_payload_check_fails (test_upload_artifact_gate.PublishBehaviourTests.test_no_gh_call_when_the_payload_check_fails) ... ok
test_publish_stops_at_the_first_bad_artifact (test_upload_artifact_gate.PublishBehaviourTests.test_publish_stops_at_the_first_bad_artifact)
`|| exit 1`, not a status collected and ignored to the end. ... ok
test_the_upload_carries_every_artifact (test_upload_artifact_gate.PublishBehaviourTests.test_the_upload_carries_every_artifact)
A gate that verifies four files and uploads three is still wrong. ... ok
test_publish_aborts_on_a_failed_verification (test_upload_artifact_gate.PublishWiringTests.test_publish_aborts_on_a_failed_verification) ... ok
test_publish_verifies_before_it_uploads (test_upload_artifact_gate.PublishWiringTests.test_publish_verifies_before_it_uploads) ... ok
test_contained_symlink_is_a_positive_control_and_reaches_ditto (test_upload_artifact_gate.RealScannerGateWiringTests.test_contained_symlink_is_a_positive_control_and_reaches_ditto) ... ok
test_escaping_symlink_bytes_fail_before_ditto_and_cannot_touch_outside (test_upload_artifact_gate.RealScannerGateWiringTests.test_escaping_symlink_bytes_fail_before_ditto_and_cannot_touch_outside) ... ok
test_a_second_root_app_is_rejected (test_upload_artifact_gate.VerifyUploadArtifactTests.test_a_second_root_app_is_rejected)
Flipped from documenting the gap to requiring it be closed. ... ok
test_an_app_hidden_inside_the_bundle_is_rejected (test_upload_artifact_gate.VerifyUploadArtifactTests.test_an_app_hidden_inside_the_bundle_is_rejected)
The nested scan, which no other case reaches. ... ok
test_clean_zip_with_one_root_app_passes (test_upload_artifact_gate.VerifyUploadArtifactTests.test_clean_zip_with_one_root_app_passes) ... ok
test_corrupt_zip_fails (test_upload_artifact_gate.VerifyUploadArtifactTests.test_corrupt_zip_fails) ... ok
test_every_artifact_passes_the_exact_current_version_and_arch_contract (test_upload_artifact_gate.VerifyUploadArtifactTests.test_every_artifact_passes_the_exact_current_version_and_arch_contract)
The defect an all-passing shim hid completely. ... ok
test_failing_archive_scan_fails_before_extraction (test_upload_artifact_gate.VerifyUploadArtifactTests.test_failing_archive_scan_fails_before_extraction)
The scan runs before `ditto`, and order is the whole point. ... ok
test_failing_bundle_check_fails_the_gate (test_upload_artifact_gate.VerifyUploadArtifactTests.test_failing_bundle_check_fails_the_gate)
The `app` branch, unreachable until the shim learned subcommands. ... ok
test_failing_payload_check_fails_the_gate (test_upload_artifact_gate.VerifyUploadArtifactTests.test_failing_payload_check_fails_the_gate) ... ok
test_missing_artifact_fails_rather_than_passing_unchecked (test_upload_artifact_gate.VerifyUploadArtifactTests.test_missing_artifact_fails_rather_than_passing_unchecked) ... ok
test_nested_app_is_not_accepted_as_a_root_app (test_upload_artifact_gate.VerifyUploadArtifactTests.test_nested_app_is_not_accepted_as_a_root_app) ... ok
test_the_plain_archive_pins_arm64_from_the_contract_not_the_host (test_upload_artifact_gate.VerifyUploadArtifactTests.test_the_plain_archive_pins_arm64_from_the_contract_not_the_host)
Asserted against `UPDATE_ASSET_NAMES`, deliberately not `uname -m`. ... ok
test_the_two_archive_kinds_are_not_given_the_same_arches (test_upload_artifact_gate.VerifyUploadArtifactTests.test_the_two_archive_kinds_are_not_given_the_same_arches)
Discrimination: if both produced one value, one test above is dead. ... ok
test_the_universal_archive_pins_BOTH_architectures (test_upload_artifact_gate.VerifyUploadArtifactTests.test_the_universal_archive_pins_BOTH_architectures)
Both, exactly - not "at least one", which is the whole point. ... ok
test_unknown_extension_fails_closed (test_upload_artifact_gate.VerifyUploadArtifactTests.test_unknown_extension_fails_closed) ... ok
test_zip_with_no_app_fails (test_upload_artifact_gate.VerifyUploadArtifactTests.test_zip_with_no_app_fails) ... ok
test_calibration_pct_applies_immediately (test_v020_boundaries.B1Settings.test_calibration_pct_applies_immediately) ... ok
test_direct_limit_applies_immediately (test_v020_boundaries.B1Settings.test_direct_limit_applies_immediately) ... ok
test_invalid_input_rejects_whole_save (test_v020_boundaries.B1Settings.test_invalid_input_rejects_whole_save) ... ok
test_mutant_control_for_the_failure_path (test_v020_boundaries.B1Settings.test_mutant_control_for_the_failure_path)
MUTANT: strip both `return`s from the rejection paths, so a rejected ... ok
test_save_settings_failure_keeps_panel_open_and_state_untouched (test_v020_boundaries.B1Settings.test_save_settings_failure_keeps_panel_open_and_state_untouched) ... ok
test_save_settings_success_updates_state_and_closes_panel (test_v020_boundaries.B1Settings.test_save_settings_success_updates_state_and_closes_panel) ... ok
test_save_settings_uses_the_seam (test_v020_boundaries.B1Settings.test_save_settings_uses_the_seam) ... ok
test_saved_limits_survive_restart (test_v020_boundaries.B1Settings.test_saved_limits_survive_restart) ... ok
test_both_build_paths_declare_the_payload (test_v020_boundaries.B2Bundle.test_both_build_paths_declare_the_payload)
Source fact, not an artifact: both builders stage .claude_pet. ... [b2] repo-root ClaudePet.app has .claude_pet: False
[b2] dist/ClaudePet.app has .claude_pet: True
ok
test_expected_set_is_derived (test_v020_boundaries.B2Bundle.test_expected_set_is_derived) ... ok
test_py2app_bundle_carries_every_asset (test_v020_boundaries.B2Bundle.test_py2app_bundle_carries_every_asset) ... ok
test_seeding_into_empty_dest_creates_everything (test_v020_boundaries.B2Bundle.test_seeding_into_empty_dest_creates_everything)
POSITIVE CONTROL for the never-clobber tests below. ... ok
test_seeding_is_idempotent (test_v020_boundaries.B2Bundle.test_seeding_is_idempotent) ... ok
test_seeding_never_clobbers_edited_files (test_v020_boundaries.B2Bundle.test_seeding_never_clobbers_edited_files) ... ok
test_seeding_refuses_a_symlinked_dest_root (test_v020_boundaries.B2Bundle.test_seeding_refuses_a_symlinked_dest_root) ... ok
test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_published_v020_and_older_bytes_are_untouched (test_v021_release_contract.PublishedNotesImmutabilityTests.test_published_v020_and_older_bytes_are_untouched) ... ok
test_v021_is_the_newest_heading_and_v022_is_gone (test_v021_release_contract.PublishedNotesImmutabilityTests.test_v021_is_the_newest_heading_and_v022_is_gone) ... ok
test_reduce_motion_and_the_roam_default_are_where_the_notes_say (test_v021_release_contract.ReleaseNotesContractTests.test_reduce_motion_and_the_roam_default_are_where_the_notes_say) ... ok
test_v021_look_duration_governs_the_approach_watch (test_v021_release_contract.ReleaseNotesContractTests.test_v021_look_duration_governs_the_approach_watch)
look_s must be the approach branch's dwell, not the wander pause. ... ok
test_v021_look_duration_matches_the_source_default (test_v021_release_contract.ReleaseNotesContractTests.test_v021_look_duration_matches_the_source_default)
The notes' "6초" must be the look constant the source actually uses. ... ok
test_v021_menu_label_is_quoted_exactly_as_the_korean_source_string (test_v021_release_contract.ReleaseNotesContractTests.test_v021_menu_label_is_quoted_exactly_as_the_korean_source_string)
The quoted menu item must be TR["ko"]["menu_roam"], read out of the source. ... ok
test_v021_notes_follow_the_three_bullet_450_character_format (test_v021_release_contract.ReleaseNotesContractTests.test_v021_notes_follow_the_three_bullet_450_character_format) ... ok
test_v021_notes_state_the_user_facing_behaviour_and_nothing_internal (test_v021_release_contract.ReleaseNotesContractTests.test_v021_notes_state_the_user_facing_behaviour_and_nothing_internal) ... ok
test_claude_has_durable_user_facing_release_note_policy (test_v021_release_contract.ReleaseNotesPolicyTests.test_claude_has_durable_user_facing_release_note_policy) ... ok
test_v021_version_and_final_source_pins_propagate (test_v021_release_contract.VersionAndPinContractTests.test_v021_version_and_final_source_pins_propagate) ... ok

----------------------------------------------------------------------
Ran 454 tests in 323.611s

OK (skipped=7)

[instruments] 14 injection site(s) use a computed needle and are NOT checked here:
  test_updater.py:2018  replace(LAUNCH_DEFINITION, ...)
  test_updater.py:2019  replace(LAUNCH_PRIMARY, ...)
  test_updater.py:2020  replace(LAUNCH_RESTORE, ...)
  test_updater.py:2119  replace(line + '\n', ...)
  test_updater.py:2344  replace(line, ...)
  test_updater.py:2347  replace(line, ...)
  test_updater_adversarial.py:183  replace(assignment, ...)
  test_updater_adversarial.py:393  replace(launch_call, ...)
  test_updater_adversarial.py:1010  replace(exchange_boundary, ...)
  test_updater_adversarial.py:1270  replace(post_exchange, ...)
  test_updater_adversarial.py:1841  replace(stage_identity_gate, ...)
  test_updater_adversarial.py:1854  replace(post_exchange, ...)
  test_updater_adversarial.py:2200  replace(needle, ...)
  test_updater_adversarial.py:1167  replace(post_exchange, ...)
[gate] rejected: Contents/Resources/claude_pet.py is missing or is not a regular file
[gate] rejected: Contents/Resources/claude_pet.py is missing or is not a regular file
[gate] rejected: Contents/Resources/claude_pet.py is missing or is not a regular file
[gate] rejected: --arches is required (what the artifact claims to support, not what this machine happens to be)
[gate] rejected: the app is not a real directory
[gate] rejected: the app is not a real directory
[gate] rejected: the app is not a real directory
[gate] rejected: the bundled claude_pet.py is not this checkout's (53def4313b53… != f3810b141423…)
[update] rejected: bundle identifier does not match
[update] rejected: CFBundleVersion does not match the release tag
[update] rejected: CFBundleShortVersionString does not match the release tag
[update] rejected: bundled path is a symlink (pets/dog/preview.png)
[update] rejected: signature missing, invalid, or not ours
[update] asset=claudepet.zip arch=arm64
[update] rejected: absolute symlink target in bundle
[update] rejected: bundle path resolves outside the bundle
[update] rejected: bundled path is a symlink (pets/dog/extra.png)
[update] rejected: bundled path is a symlink (pets/spare)
[update] rejected: bundled path is a symlink (EXTRA.md)
[update] rejected: bundled path is a symlink (.claude_pet)
[update] rejected: bundled path is a symlink (pets)
[update] rejected: bundled path is a symlink (pets/dog)
[update] asset=claudepet.zip arch=arm64
[update] rejected: unreadable archive (BadZipFile)
[update] refused: no expected version to verify against
[update] refused: no expected version to verify against
[update] refused: no expected version to verify against
[update] rejected: no expected version to verify against
[update] rejected: no expected version to verify against
[update] rejected: no expected version to verify against
[update] rejected: no expected version to verify against
[update] rejected: no expected version to verify against
[update] rejected: bundled path is a symlink (pets/dog/preview.png)
[update] rejected: the staged copy does not match what was validated
[update] rejected: bundle has no arm64 slice
[update] rejected: bundle has no arm64 slice
[update] rejected: Info.plist is not a regular file
[update] rejected: main executable is not a regular file
[update] rejected: claudepet.zip is not served over https
[update] rejected: claudepet.zip is not served over https
[update] rejected: claudepet.zip is not served over https
[update] rejected: claudepet.zip is not served over https
[update] rejected: claudepet.zip is not served over https
[update] rejected: two assets normalize to 'claudepet.zip'
[update] rejected: unknown architecture ('aarch64')
[update] rejected: unknown architecture ('ppc')
[update] rejected: unknown architecture ('')
[update] rejected: unknown architecture (None)
[update] rejected: signature missing, invalid, or not ours
[update] rejected: Gatekeeper did not attribute the app to us
[update] rejected: Gatekeeper reported no origin
[update] rejected: codesign could not run (OSError)
[update] rejected: signature missing, invalid, or not ours
[update] rejected: codesign could not run (TimeoutExpired)
[update] rejected: signature missing, invalid, or not ours
[update] rejected: spctl could not run (OSError)
[update] rejected: not notarized / rejected by Gatekeeper
[update] rejected: spctl could not run (TimeoutExpired)
[update] rejected: not notarized / rejected by Gatekeeper
[update] rejected: xcrun could not run (OSError)
[update] rejected: no stapled notarization ticket
[update] rejected: xcrun could not run (TimeoutExpired)
[update] rejected: no stapled notarization ticket
[update] rejected: no stapled notarization ticket
[update] rejected: archive member escapes the archive root
[update] rejected: archive member is an absolute path
[update] rejected: unreadable archive (BadZipFile)
[update] rejected: bundle has no x86_64 slice
[update] rejected: Info.plist is not a regular file
[update] rejected: main executable is not a regular file
[update] rejected: main executable is not a regular file
[update] bundled pet assets incomplete (16 paths); seeding will skip them
[update] rejected: bundled exchange helper (Contents/MacOS/python) is not executable
[update] rejected: the staged copy does not match what was validated
[update] rejected: the staged copy does not match what was validated
[update] refused: the update lock directory is not a plain directory we can own
[update] refused: could not claim a staging name
[update] rejected: the staged copy does not match what was validated
[update] refused: the update lock path is not a plain file we can own
[update] refused: the update lock directory is not a private directory we own
[update] rejected: the staged copy does not match what was validated
[update] refused: the update lock directory is not a plain directory we can own
usage: claude_pet.py --with-update-lock <APP_PATH> -- <COMMAND> [ARGS...]
usage: claude_pet.py --with-update-lock <APP_PATH> -- <COMMAND> [ARGS...]
usage: claude_pet.py --with-update-lock <APP_PATH> -- <COMMAND> [ARGS...]
usage: claude_pet.py --with-update-lock <APP_PATH> -- <COMMAND> [ARGS...]
[update] rejected: archive symlink points to an absolute path
[update] rejected: archive symlink points to an absolute path
[update] rejected: archive symlink escapes the archive root
[update] rejected: archive symlink escapes the archive root
```

## Real-time GUI evidence and final handoff

The observed GUI launched at 2026-09-09T07:30:21.958774Z as PID10294 from source
`f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288`.
Reviewer independently reconstructed that source from final `f3810b14…` by
reversing only five comment/docstring changes; executable behavior is unchanged.
The trace helper `/tmp/claudepet-free-roaming-20260909-qa.py` calls the original
`Roamer.step` exactly once with unchanged arguments/result, and calls normal
`run_gui` with its workers, timer, real monotonic clock and default unseeded RNG.
It samples observable state at most every 0.5 seconds plus transitions; it does
not drive the clock, choose random destinations, or directly invoke UI callbacks.
`pre_native` is the real NSWindow geometry before that motion callback's adapter
update, so settled next-tick samples are used for mode/frame comparisons.

Only CONFIG_PATH was isolated to
`/tmp/claudepet-free-roaming-20260909-config.json`. Initial contents were
`{"x":118,"y":98,"scale":0.5,"roam":true,"greet":false,"spike_mult":2.0,"lang":"ko"}`.
Greeting was disabled and spike sensitivity set to the supported lower-sensitivity
value to keep these isolated functional observations from being preempted;
motion timing, cooldowns, speed and RNG were product defaults. Existing user
configuration was not changed. Normal live usage/OAuth workers remained active;
this is not the I/O-isolated synthetic native fixture.

Raw artifact: [free-roaming-live-20260909.jsonl](free-roaming-live-20260909.jsonl),
SHA256 `a19cb52f46c40a2d1e17d388d19067c46ea0fa5ab31900578b334399eef37961`.
Recorded window: 2026-09-09T07:30:21.958774Z through
2026-09-09T07:40:39.348469Z. Grouping: trace record, 1113 records total,
including 1105 sampled original motion calls; measured after process stop.
Of those 1105 native frame samples, zero crossed the current visible screen
`(0,36,1353,695)` using a one-point native-quantization tolerance. This sample
claim is not a proof about every screen or every possible random path.

| Actual normal event-loop sample | Random wander | Activity-triggered approach |
| --- | --- | --- |
| Departure UTC | 07:31:41.357616Z | 07:33:18.353418Z |
| Arrival UTC | 07:31:48.406973Z | 07:33:24.903566Z |
| Natural rest UTC | 07:31:50.406958Z | 07:33:30.952605Z |
| Start logical center | (252,248) | (600.0410568973914,414.9764612100694) |
| Arrival logical center | (600.0410568973914,414.9764612100694) | (938.4210261925689,537.8544347439569) |
| Distance | 386.02294735480564pt | 360pt |
| Pause measured with original monotonic inputs | 2.000015s | 6.049323s |
| Native travel frame | 128×108, folded | 128×108, folded |
| Settled arrival frame | 128×108, folded | 143×140, summary |
| Natural rest frame | 268×240, full | 268×240, full |

All times above are on 2026-09-09, and each column is one observed trip. The
wander exceeded both the old 160pt local radius and 360pt approach cap; its
unseeded destination is one sample, not a measured distribution. Whole-screen
sampling is established by the independent deterministic rectangle/retry gates.
The approach was elicited by actual OS cursor moves between desktop (1250,80)
and (1250,110) at 1.2-second intervals; the helper did not force activity flags.
Both trips stayed at their arrival through natural rest. Manual home stayed
(252,248), and config x/y stayed (118,98) until the explicit manual drag below.

[The actual screenshot contact sheet](free-roaming-live-20260909.png) composes
three original 536×480 window screenshots without resizing; captions give
absolute desktop-window coordinates and capture UTC. It shows initial full
window, wander rest and approach rest; it does not depict continuous travel.
Original capture paths and captions are recorded in the trace. In contrast,
[the final synthetic native contact sheet](free-roaming-native-20260909.png)
shows settled walking/review/rest poses with scanning placeholders. Its
[1905 native tick samples](free-roaming-native-20260909.json) correspond to
2026-09-09T07:37:19.688436Z–07:37:20.072234Z, final source f3810b14…,
and synthetic time 0.05–95.25s: zero bounds violations, maximum sprite/model
axis residual 0.872459pt, maximum model step 2.750000000000646pt, both midpoint
crossings, destination immobility for ten seconds, unchanged departure home,
and zero intercepted config writes. Those native counts apply to that fixture.

Actual input checks on PID10294 were recorded separately:

- 07:35:27.384845Z: click without drag at desktop (860,290) left config unchanged.
- 07:35:36Z: actual right-click exposed the native context menu, including
  Settings, gauge fold, roam, size and pet controls. The installed app was not targeted.
- 07:36:03.888078Z: selecting roam OFF wrote only the isolated roam preference;
  the next original step read enabled=False and retained position.
- 07:36:34.487178Z: selecting roam ON restored that preference and enabled=True.
- 07:36:51.349411Z: actual OS drag (860,290)→(760,290) moved the native full
  window by -100pt x. This action changed saved x/y to (704,417) and home to
  (838,537). The following hover samples remained blocked/rest at that home.

This change did not repeat yesterday's OS Reduce Motion setting toggle or every
settings-screen interaction. The unchanged adapter and those behaviors remain
covered by the full regression suite, with the previous actual OS evidence kept
separately. No new OS setting was modified in this run.

At 2026-09-09T07:40:39.348469Z the final trace event was written and only PID10294
was stopped. Sensitivity was restored to 1.0 and the temporary greet override
removed (the ordinary product default applies). The cursor was restored to its
initial observed desktop location (49,4). Installed PID29528 stayed running.
The final normal development process, PID30313, started at
2026-09-09T07:40:39.492846Z with final source f3810b14… and the same isolated
CONFIG_PATH, **without any trace wrapper**. Its actual NSWindow1782 rendered
at desktop (704,74), size268×240 at 07:40:46Z. Startup's existing first-row
resize preserves the initial top and adjusts native y by30pt; saved config
remains (704,417), the explicit manual choice, and does not use either automatic
arrival. This existing size initialization is separate from automatic travel.

The exact final stdin launch sequence after process/config/cursor cleanup was:

```python
import claude_pet as pet
pet.CONFIG_PATH = str(cfg)  # cfg is Path('/tmp/claudepet-free-roaming-20260909-config.json')
print('FINAL_UNWRAPPED_PID', os.getpid(), 'SOURCE_SHA',
      hashlib.sha256(Path('claude_pet.py').read_bytes()).hexdigest(),
      'CONFIG', pet.CONFIG_PATH, 'UTC',
      datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
pet.run_gui()
```

It ran via `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -`
from the repository root. The final process is intentionally left visible for
the user; the trace file has stopped growing. No build, signing, installed-app
replacement, update, release or push was performed. The seven suite skips are
preexisting opted-in live/release checks, not skipped new feature gates.
