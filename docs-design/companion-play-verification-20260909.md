# Timed cursor follow and inter-monitor jump — verification, 2026-09-09

Status: PASS on final source150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351.
Independent RED/GREEN, corrected separating-rival checks, full suite, native
integration, real follow/jump controls and normal development handoff are recorded below.
Actual OS multi-monitor transit remains unverified because only one display is connected.

Roles: Claude Developer; Mendel (/root/verifier) Verifier; Curie (/root/reviewer)
Reviewer; /root Coordinator. This Verifier has not edited production.

Baseline HEAD `dba49ef6fe66f16a6a63d5f981f76a0fd0121448`, source SHA256
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.
Tracked tree/index clean at initial read. Existing installed PID29528 and normal
no-trace development PID30313 were rechecked alive for this change.

Assigned new deliverables: tests/test_companion_play.py, this report,
docs-design/companion-play-live-20260909.jsonl and .png,
/tmp/claudepet-companion-play-20260909-qa.py and
/tmp/claudepet-companion-play-20260909-config.json.
Assigned tracked test migration: tests/test_companion_motion.py,
tests/test_free_roaming.py; source pins in tests/test_manual_update_transaction.py
and tests/test_upload_artifact_gate.py only after final source review.
All new paths were confirmed absent before creating this document. Earlier QA
artifacts and untracked user files are outside this assignment.

## Actual display inventory and verification boundary

Read-only AppKit NSScreen inventory measured 2026-09-09T07:59:50.654678Z:
**one active display** (one NSScreen entry), ID18, localized name
"화면 공유 가상 디스플레이", frame (0,0,1353,761), visible frame
(0,36,1353,695), backing scale2, not built-in. The same fresh process read
Reduce Motion=False. Source files read: claude_pet.py and tracked test/role
rules; inventory itself is AppKit/Quartz runtime data, with no app/window input.

There is no second active hardware/OS display available for a genuine
inter-monitor transit observation. Real-time follow and one-screen behavior can
be tested visibly. Multi-screen geometry/jump integration will require explicit
synthetic screen fixtures; those results must not be described as hardware
multi-monitor validation. No virtual display is created by this test assignment.

## Independent requirements and separating rivals (before API proposal)

The user asks for occasional random cursor-follow episodes lasting at least ten
seconds and autonomous jumps between monitors. Coordinator scopes natural
follow duration to10–20 seconds, preserving quiet cadence, cursor clearance and
immediate user-interaction suppression. Both activities end by resting at their
new location, without overwriting the manual saved placement.

| Requirement | Separating case / plausible incorrect behavior |
| --- | --- |
| Follow reacts to changing cursor | Move cursor vertically after an initially horizontal target; fixed-target approach continues horizontally while true follow gains a vertical component at its next permitted retarget |
| Follow has a single bounded episode deadline | Repeated cursor changes cannot extend a chosen12-second episode; an idle cursor cannot end natural follow before10seconds |
| Random selection remains occasional | Controlled draws on both sides of the agreed selection threshold; distinguish always-follow and never-follow |
| Quiet start and cooldown | Activity during initial rest does not start movement; repeated activity after an episode cannot bypass its cooldown |
| Clearance includes complete logical window | Radius60 plus approach clearance150 implies210point center separation in the independent fixture; sprite-only clearance and endpoint-only path tests differ |
| Interruption wins at every stage | Hover/menu/settings/drag/disabled/Reduce Motion at a follow retarget or jump-transfer boundary cancels or safely holds the activity; release cannot resume stale targets/deadlines |
| Jump chooses another screen | Two disjoint screen identities and rectangles; reject current-screen choice and all-identical-screen inventory |
| Each screen has its own safe bounds | Negative origin and different vertical offset distinguish target-screen safe rectangle from primary-origin or union-rectangle sampling |
| Landing survives adapter placement | Check actual window after the model transfer and next native tick; an old-screen clamp can undo an apparently correct pure jump |
| Missing/changed target display is handled | Remove or shrink target during jump; do not land in a vanished/gap rectangle or continue an old route |
| Display and persistence stay coherent | Compact motion/jump, safe full/summary restoration with preserved sprite anchor; no automatic x/y write, manual drag alone establishes restart position |

These are specification-derived hypotheses/fixtures, not measured feature results.
Exact API names, selection weights, animation timing, and retarget cadence will
be confirmed before gating assertions are authored. A symbol-absence RED will
be labeled separately from behavioral/numeric baseline failures.

Additional Coordinator-assigned native outputs: companion-play-native-20260909.json
and .png in docs-design. Screen fixtures will live in the assigned new test file.

Reviewer independently derived the following screen fixture before any new test
expected values existed; the Verifier recomputed it from rectangle arithmetic:
logical full300×220; A visible(-1600,80,1440,900)→safe(-1450,190,-310,870);
B visible(240,-200,1920,1080)→safe(390,-90,2010,770). Unit draws(.45,.2) in B
give landing(1119,82), full origin(969,-28). Wrong union bounds produce(107,102),
source bounds(-937,326), ignoring B origin(879,282), raw-visible sample then
clamp(1104,16), and applying the old A clamp after landing(-310,190). All differ
from the correct destination. The straight midpoint between start(-880,530) and
landing is(119.5,306), in the gap between the two screens, so a held tween there
would not be a reachable resting location. These formulas are fixture geometry;
the agreed jump-phase API will determine when source/target placement is expected.

A follow directional fixture can avoid depending on unspecified retarget distance:
start(400,300), cursor(1000,300), radius50. At55pt/s a quarter-second step is13.75pt
right. At the next permitted retarget, a cursor directly above the new x coordinate
makes a true follow step13.75pt upward; retaining the old horizontal target instead
moves another13.75pt right. No formula here assumes a final refresh cadence before
API agreement. A13-second duration selected once at t100 ends at t113; cursor
updates must not reset that deadline. Dense callbacks avoid confusing the separate
long-gap cancellation rule with episode expiration.

Coordinator follow/screen boundary intent: if a following cursor enters another
valid screen, continue via the same safe jump mechanism while retaining the
original episode deadline. The destination screen is fixed during a jump; cursor
updates must not cause per-tick source/target oscillation. A cursor in the gap or
on a missing screen causes safe waiting/cancellation at a reachable current
position. Exact cooldown/phase API remains pending. Fixtures must distinguish
restart-of-duration after transfer, changing jump destination mid-air, and
clamping a foreign-screen cursor to a union rectangle.

Coordinator permits real-time follow selection probability to be1 in the isolated
QA fixture, retaining original step/clock/duration/speed/clearance. Default random
selection and cooldowns will be tested deterministically; forced selection is
not a sample of the production probability. The final no-trace handoff will use
production defaults. Synthetic two-screen native fixtures remain separate from
actual OS multi-screen evidence.

## Baseline follow behavioral RED

Source SHA f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a; UTC 2026-09-09T08:12:45.332930+00:00–2026-09-09T08:12:45.751598+00:00; measured at end. Command `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -v`; grouping unittest case/subtest. Read file set test_companion_play.py, companion pure AST loader, and baseline claude_pet.py. No app import or user data. Exit 1. New config values are deliberately ignored by baseline; actual phase, movement coordinates and presentation differ. Screens/jump API is not part of this run.

```text
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... 
  test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) (preference=False) ... FAIL
  test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) (preference=True) ... FAIL
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... 
  test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) (duration=10.0) ... FAIL
  test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) (duration=20.0) ... FAIL
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... 
  test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='enabled') ... FAIL
  test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='blocked') ... FAIL
  test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='busy') ... FAIL
  test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='dragging') ... FAIL
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... FAIL
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... FAIL
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... FAIL
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... FAIL
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... FAIL
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... 
  test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) (choice=0.349) ... FAIL

======================================================================
FAIL: test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) (preference=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 158, in test_follow_travel_folds_and_completion_look_gets_summary
    self.assertEqual(d.mode("look", preference), "summary")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'folded' != 'summary'
- folded
+ summary


======================================================================
FAIL: test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) (preference=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 156, in test_follow_travel_folds_and_completion_look_gets_summary
    self.assertEqual(d.mode("follow", preference), "folded")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'full' != 'folded'
- full
+ folded


======================================================================
FAIL: test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) (duration=10.0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 78, in test_duration_endpoints_do_not_finish_early_on_near_target_arrival
    self.assertEqual(out.phase, "follow", "near target arrival ended the timed episode early")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'follow'
- rest
+ follow
 : near target arrival ended the timed episode early

======================================================================
FAIL: test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) (duration=20.0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 78, in test_duration_endpoints_do_not_finish_early_on_near_target_arrival
    self.assertEqual(out.phase, "follow", "near target arrival ended the timed episode early")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'follow'
- rest
+ follow
 : near target arrival ended the timed episode early

======================================================================
FAIL: test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='enabled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 137, in test_every_hold_immediately_cancels_follow_without_stale_resume
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow


======================================================================
FAIL: test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='blocked')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 137, in test_every_hold_immediately_cancels_follow_without_stale_resume
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow


======================================================================
FAIL: test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='busy')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 137, in test_every_hold_immediately_cancels_follow_without_stale_resume
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow


======================================================================
FAIL: test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) (flag='dragging')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 137, in test_every_hold_immediately_cancels_follow_without_stale_resume
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow


======================================================================
FAIL: test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 49, in test_first_ordinary_eligibility_can_select_follow
    self.assertEqual(r.phase, "follow", "follow was delayed by an artificial initial cooldown")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow
 : follow was delayed by an artificial initial cooldown

======================================================================
FAIL: test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 125, in test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts
    self.assertEqual(starts, [100.0, 520.0],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
                     "follow eligibility or its 420-second cooldown is incorrect")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [] != [100.0, 520.0]

Second list contains 2 additional elements.
First extra element 0:
100.0

- []
+ [100.0, 520.0] : follow eligibility or its 420-second cooldown is incorrect

======================================================================
FAIL: test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 68, in test_follow_retargets_upward_instead_of_retaining_horizontal_target
    self.assertEqual(delta, (0.0, 11.25),
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
                     "latest vertical cursor movement did not replace the old horizontal target")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (13.75, 0.0) != (0.0, 11.25)

First differing element 0:
13.75
0.0

- (13.75, 0.0)
+ (0.0, 11.25) : latest vertical cursor movement did not replace the old horizontal target

======================================================================
FAIL: test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 55, in test_follow_uses_its_own_speed_and_capped_elapsed_time
    self.assertEqual(tuple(out.pos), (411.25, 300.0),
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "follow did not use 45pt/s for the first quarter-second")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (413.75, 300.0) != (411.25, 300.0)

First differing element 0:
413.75
411.25

- (413.75, 300.0)
?    ^ ^

+ (411.25, 300.0)
?    ^ ^
 : follow did not use 45pt/s for the first quarter-second

======================================================================
FAIL: test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 93, in test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'follow'
- rest
+ follow


======================================================================
FAIL: test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) (choice=0.349)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 112, in test_selection_threshold_has_both_follow_and_ordinary_branches
    self.assertEqual(out.phase, expected)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'follow'
- out
+ follow


----------------------------------------------------------------------
Ran 9 tests in 0.348s

FAILED (failures=14)
```

## Cursor disappearance/intrusion RED

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -k cursor -v`; SHA f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a; UTC 2026-09-09T08:15:17.644500+00:00–2026-09-09T08:15:17.762658+00:00; grouping selected unittest cases, same pure AST file set; measured at end. Exit 1. Cursor-induced proximity is external input, so the gate asserts no new movement into it rather than an impossible universal minimum distance.

```text
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... FAIL
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... FAIL

======================================================================
FAIL: test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 123, in test_cursor_entering_clearance_causes_no_new_movement_toward_it
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'follow'
- rest
+ follow


======================================================================
FAIL: test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 112, in test_missing_cursor_cancels_in_place_without_claiming_natural_completion
    self.assertEqual(tuple(out.pos), before, "missing cursor continued an obsolete follow target")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (427.5, 300.0) != (413.75, 300.0)

First differing element 0:
427.5
413.75

- (427.5, 300.0)
?   ^ -

+ (413.75, 300.0)
?   ^^^
 : missing cursor continued an obsolete follow target

----------------------------------------------------------------------
Ran 2 tests in 0.049s

FAILED (failures=2)
```

## Screen/effect API absence RED (not numeric jump behavior)

Command `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -k PlayApiTests -v`; SHA f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a; UTC 2026-09-09T08:16:07.998123+00:00–2026-09-09T08:16:08.125696+00:00; grouping selected unittest cases, same pure AST file set; measured at end. Exit 1. This demonstrates the old interface lacks screen descriptors and effects; it does not yet measure landing coordinates or fade rendering.

```text
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... FAIL
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... FAIL

======================================================================
FAIL: test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 36, in test_effect_field_is_appended_with_legacy_five_argument_default
    self.assertEqual(api["RoamOut"]._fields, ("pos", "anim", "moved", "away", "phase", "effect"))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: ('pos', 'anim', 'moved', 'away', 'phase') != ('pos', 'anim', 'moved', 'away', 'phase', 'effect')

Second tuple contains 1 additional elements.
First extra element 5:
'effect'

- ('pos', 'anim', 'moved', 'away', 'phase')
+ ('pos', 'anim', 'moved', 'away', 'phase', 'effect')
?                                         ++++++++++


======================================================================
FAIL: test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 28, in test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct
    api = pure_api(self, {"RoamScreen"})
  File "/Users/yeongyu/claude-pet/tests/test_companion_motion.py", line 40, in pure_api
    test.assertFalse(required - definitions.keys(),
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "quiet companion API missing: " + ", ".join(sorted(required - definitions.keys())))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'RoamScreen'} is not false : quiet companion API missing: RoamScreen

----------------------------------------------------------------------
Ran 2 tests in 0.046s

FAILED (failures=2)
```

## Monitor jump baseline RED

Source SHA256 `f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`; UTC 2026-09-09T08:24:49.102472+00:00 through 2026-09-09T08:24:49.977726+00:00. Command: `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -v -k Jump`.

Baseline compatibility removes only the unsupported `screens` keyword. The model receives its original A bounds; no movement, phase, RNG result, or assertion is replaced. Strict interface gates above independently reject missing screens/effect symbols. The one-screen/disabled case is a positive regression control, not claimed as new-feature RED.

```text
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... 
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='enabled') ... ERROR
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='blocked') ... ERROR
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='busy') ... ERROR
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='dragging') ... ERROR
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='enabled') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='blocked') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='busy') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='dragging') ... FAIL
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... FAIL
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... FAIL
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... FAIL
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... FAIL
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... 
  test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) (change='removed') ... FAIL
  test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) (change='shrunken') ... FAIL
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... FAIL

======================================================================
ERROR: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='enabled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 329, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
                      ^^^^^^^^^^
AttributeError: 'RoamOut' object has no attribute 'effect'

======================================================================
ERROR: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='blocked')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 329, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
                      ^^^^^^^^^^
AttributeError: 'RoamOut' object has no attribute 'effect'

======================================================================
ERROR: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='busy')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 329, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
                      ^^^^^^^^^^
AttributeError: 'RoamOut' object has no attribute 'effect'

======================================================================
ERROR: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='dragging')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 329, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
                      ^^^^^^^^^^
AttributeError: 'RoamOut' object has no attribute 'effect'

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='enabled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 326, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0)

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='blocked')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 326, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0)

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='busy')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 326, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0)

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='dragging')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 326, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0)

======================================================================
FAIL: test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 307, in test_cursor_covering_landing_is_rechecked_before_transfer
    self.assertEqual(tuple(out.pos), self.START, "jump transferred the window onto the latest cursor")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-903.6175363865841, 515.9123467167744) != (-880.0, 530.0)

First differing element 0:
-903.6175363865841
-880.0

- (-903.6175363865841, 515.9123467167744)
+ (-880.0, 530.0) : jump transferred the window onto the latest cursor

======================================================================
FAIL: test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 283, in test_destination_id_survives_inventory_reordering
    self.assertEqual(tuple(out.pos), self.LANDING)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0)

======================================================================
FAIL: test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 355, in test_jump_cooldown_starts_after_first_eligible_jump
    self.assertEqual(starts, [100.0, 700.0], "jump initial eligibility or 600-second cooldown is incorrect")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [] != [100.0, 700.0]

Second list contains 2 additional elements.
First extra element 0:
100.0

- []
+ [100.0, 700.0] : jump initial eligibility or 600-second cooldown is incorrect

======================================================================
FAIL: test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 241, in test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp
    self.assertEqual(tuple(out.pos), self.LANDING,
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "monitor jump did not use the independently derived target-screen destination")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)

First differing element 0:
-915.4263045798762
1119.0

- (-915.4263045798762, 508.86852007516165)
+ (1119.0, 82.0) : monitor jump did not use the independently derived target-screen destination

======================================================================
FAIL: test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) (change='removed')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 297, in test_missing_or_shrunk_target_cancels_before_transfer
    self.assertEqual(tuple(out.pos), self.START, "jump used an obsolete target screen/rectangle")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-903.6175363865841, 515.9123467167744) != (-880.0, 530.0)

First differing element 0:
-903.6175363865841
-880.0

- (-903.6175363865841, 515.9123467167744)
+ (-880.0, 530.0) : jump used an obsolete target screen/rectangle

======================================================================
FAIL: test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) (change='shrunken')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 297, in test_missing_or_shrunk_target_cancels_before_transfer
    self.assertEqual(tuple(out.pos), self.START, "jump used an obsolete target screen/rectangle")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-903.6175363865841, 515.9123467167744) != (-880.0, 530.0)

First differing element 0:
-903.6175363865841
-880.0

- (-903.6175363865841, 515.9123467167744)
+ (-880.0, 530.0) : jump used an obsolete target screen/rectangle

======================================================================
FAIL: test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 254, in test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'jump'
- out
+ jump


----------------------------------------------------------------------
Ran 8 tests in 0.802s

FAILED (failures=11, errors=4)
```

## Cross-screen follow baseline RED

Source `f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`, UTC 2026-09-09T08:25:10.783243+00:00 through 2026-09-09T08:25:11.228063+00:00. Command: `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -v -k FollowAcrossScreensTests`. Baseline lacks follow/jump phases, so deadline-specific assertions are initially blocked by the real jump-entry assertion; this is recorded as entry/precondition RED, not a baseline deadline calculation failure.

```text
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... FAIL
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... FAIL
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... FAIL
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... FAIL
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... FAIL

======================================================================
FAIL: test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 428, in test_cross_dwell_restarts_when_foreign_screen_identity_changes
    self.assertEqual(out.phase, "follow", "dwell from B and C was incorrectly combined")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'look' != 'follow'
- look
+ follow
 : dwell from B and C was incorrectly combined

======================================================================
FAIL: test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 439, in test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'look' != 'jump'
- look
+ jump


======================================================================
FAIL: test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 411, in test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell
    self.assertEqual(out.phase, "follow")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'look' != 'follow'
- look
+ follow


======================================================================
FAIL: test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 392, in test_original_follow_deadline_is_also_checked_during_landing
    r, screens = self.prepare_deadline_jump()
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 376, in prepare_deadline_jump
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'jump'
- rest
+ jump


======================================================================
FAIL: test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 380, in test_original_follow_deadline_wins_before_late_takeoff_transfer
    r, screens = self.prepare_deadline_jump()
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 376, in prepare_deadline_jump
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'jump'
- rest
+ jump


----------------------------------------------------------------------
Ran 5 tests in 0.365s

FAILED (failures=5)
```

## Existing test fixture migration

After observed baseline RED, legacy approach/wander fixtures now explicitly set `follow_p=0.0` and `jump_enabled=False`; their geometry, cursor safety, timing, persistence, and display assertions remain unchanged. The old public tuple-shape assertion now includes `effect`, as agreed in API v2 and independently observed missing in the API RED above. The new API test separately preserves five-argument construction compatibility.

## Additional contract baseline replay

UTC 2026-09-09T08:32:04.261958+00:00 through 2026-09-09T08:32:04.591223+00:00; `git show dba49ef6fe66f16a6a63d5f981f76a0fd0121448:claude_pet.py` loaded into the AST loader in memory, verified source SHA f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a. Production working tree is not reverted. Selected cases: PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract, MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold, MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds, FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages. Defaults absence and jump-entry precondition are distinguished from manual-placement numeric failure.

```text
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... FAIL
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... 
  test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) (choice=0.499) ... FAIL
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... FAIL
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... 
  test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) (transferred=False) ... FAIL
  test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) (transferred=True) ... FAIL

======================================================================
FAIL: test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 39, in test_production_cadence_duration_and_jump_defaults_match_agreed_contract
    self.assertEqual({key: api["ROAM_DEFAULTS"].get(key) for key in expected}, expected)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'follow_p': None, 'follow_min_s': None, 'follow_max_s[254 chars]None} != {'follow_p': 0.35, 'follow_min_s': 10.0, 'follow_max_s[246 chars]': 6}
Diff is 1402 characters long. Set self.maxDiff to None to see it.

======================================================================
FAIL: test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) (choice=0.499)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 254, in test_jump_probability_has_both_branches_at_the_default_threshold
    self.assertEqual(out.phase, phase)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
AssertionError: 'out' != 'jump'
- out
+ jump


======================================================================
FAIL: test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 260, in test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds
    self.assertEqual(tuple(out.pos), self.LANDING, "new manual screen was clamped back to legacy A")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (-310.0, 190.0) != (1119.0, 82.0)

First differing element 0:
-310.0
1119.0

- (-310.0, 190.0)
+ (1119.0, 82.0) : new manual screen was clamped back to legacy A

======================================================================
FAIL: test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) (transferred=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 392, in test_cursor_none_cancels_follow_in_both_jump_stages
    r, screens = self.prepare_deadline_jump()
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 419, in prepare_deadline_jump
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'jump'
- rest
+ jump


======================================================================
FAIL: test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) (transferred=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 392, in test_cursor_none_cancels_follow_in_both_jump_stages
    r, screens = self.prepare_deadline_jump()
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 419, in prepare_deadline_jump
    self.assertEqual(out.phase, "jump")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'rest' != 'jump'
- rest
+ jump


----------------------------------------------------------------------
Ran 4 tests in 0.329s

FAILED (failures=5)
```

## Final API v2 and execution fixture boundaries

Coordinator/Reviewer agreed to `RoamScreen(id, frame, bounds)` with both
rectangles expressed as x0,y0,x1,y1, all screens included, physical-frame cursor
membership, and model-selected screen bounds after atomic transfer. `RoamOut`
adds an optional effect while preserving five-argument construction. The early
55pt/s exploratory follow arithmetic above was superseded by the agreed45pt/s
follow speed: quarter-step11.25pt, horizontally then vertically after retarget.
Ordinary walking remains55pt/s. The final30 pure cases use the45pt/s contract.

Production follow selection=.35, duration10–20s, cooldown420s; jump selection=.5,
cooldown600s, takeoff.75s/landing.5s. First eligibility follows the initial normal
rest. Follow cross-screen dwell is3s per target ID with at least5s left, one jump
maximum, and the original episode deadline applies during both jump stages.
New tests cover numeric motion/placement, strict API absence, and entry
preconditions separately; the baseline one-screen/disabled-jump control already
passed and is not represented as new-feature RED.

The assigned `/tmp/claudepet-companion-play-20260909-qa.py` will run normal
`run_gui` and real NSTimers with original monotonic time, original Roamer.step,
and production duration/speed/safety. Only follow selection is forced to1,
as explicitly authorized by Coordinator. Its normal data-worker calls receive
fabricated exact rows (`QA Session`32%, `QA Weekly`18%); compute_usage returnsNone,
network/auth/log calls and user-pet writes are excluded. An audit hook rejects
real user corpus/config/pet-path reads and network operations. This is an actual
GUI motion/input test with synthetic usage, not a measurement of user usage or
production selection frequency. The separate QA config starts at x220/y200,
scale.5, roamTrue, greetFalse, spike_mult2.0; normal handoff restores default
probability, greeting and sensitivity.

The opt-in `tests/test_companion_play.py --native-play` fixture uses the actual
NSWindow, product PetView, Ticker, Roamer, and display adapter with fabricated
screen IDs901/902, synthetic time/cursor/RNG, and disabled workers/timers. It
records full logical-envelope bounds, actual native frame, sprite anchor,
opacity and display mode. The two-screen output must remain labeled synthetic
inventory; the actual OS currently exposes one screen. This fixture writes only
this change's assigned companion-play-native JSON/PNG, preserving prior QA.

## Frozen-source focused run

Source 0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c, UTC 2026-09-09T08:37:39.870521+00:00 through 2026-09-09T08:37:45.094919+00:00. Commands (repository root, PYTHONDONTWRITEBYTECODE=1):

```text
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion*.py -v
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
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... ok
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... ok
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... ok
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... ok
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... ok
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... ok
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... ok
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... ok
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... ok
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... ok
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... ok
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... ok
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... ok
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... ok
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... ok
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... ok
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... ok
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... ok
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... ok
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... ok
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... ok
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... ok
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... ok
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... ok
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... ok
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... ok
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... ok
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... ok

----------------------------------------------------------------------
Ran 81 tests in 4.850s

OK

/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_free_roaming.py -v
test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) ... ok
test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home) ... ok
test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) ... ok
test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) ... ok
test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure) ... ok
test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.238s

OK
```

## Established invalid-screen regression RED

Reviewer proposed core screen filtering failure; independently reproduced with a different100x90 screen at(1800,-50), logical300x220 producing inverted safe bounds(1950,60,1750,-70). Correct behavior excludes it before chance selection and performs local wander. Source 0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c, UTC 2026-09-09T08:40:18.153520+00:00 through 2026-09-09T08:40:18.273459+00:00. Command: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion_play.py -v -k inverted_destination`.

```text
test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection) ... FAIL

======================================================================
FAIL: test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 254, in test_inverted_destination_bounds_are_excluded_before_jump_selection
    self.assertEqual(out.phase, "out", "invalid monitor consumed a jump and began takeoff")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'jump' != 'out'
- jump
+ out
 : invalid monitor consumed a jump and began takeoff

----------------------------------------------------------------------
Ran 1 test in 0.061s

FAILED (failures=1)
```

## Native AppKit result and input-fixture correction

The first `PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tests/test_companion_play.py --native-play` execution stopped at:

```text
AssertionError: hover failed to cancel jump and restore native opacity
```

The fixture directly set state.hover, but Ticker recalculates that flag from NSEvent.mouseLocation and the native window frame. The corrected fixture places its synthetic pointer inside the actual window before the tick. Production and expected cancellation remain unchanged; this was a fixture-input correction, not a product defect.

Corrected source 0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c, UTC 2026-09-09T08:38:15.459135+00:00 through 2026-09-09T08:38:15.740707+00:00, 95 native Ticker samples; config writes0, forbidden calls0. Actual NSWindow/PetView, logical268×210, synthetic screen IDs901/902, landing(1117.4,79), max native/model axis residual0.40000000000009095pt. This accelerated synthetic-clock run validates effect/placement values, not elapsed animation duration. [Raw native JSON](companion-play-native-20260909.json), [native product render](companion-play-native-20260909.png). These mutable artifact paths now contain the subsequent24c9 repeat at2026-09-09T08:44:34.288890–08:44:34.581876Z (same95samples); the preceding0c2c run is retained here as historical evidence, not as the current artifact SHA.

## Real event-loop follow on source0c2c53

Live PID14581/window1789, source0c2c53, normal NSTimer/original step with the documented probability-only and synthetic-usage fixture. One episode: start2026-09-09T08:40:17.346083Z, look08:40:33.695939Z, rest/full08:40:39.745024Z. Chosen interval16.304191290866584s, observed phase interval16.349856s;64 recorded follow samples. Start(551.089392624663,404.591688198113), final(990.4118126365519,427.7879714310746), straight displacement439.9343772438411pt. Cursor was moved above/below the pet during follow; actual_cursor_move rows record actual OS input separately from model observations.

The [actual contact sheet](companion-play-live-20260909.png) retains native-size ScreenCaptureKit pixels for folded follow, arrival-summary transition, and restored full panel. Arrival is explicitly a transition picture, not evidence of a settled review pose. QA Session32%/QA Weekly18% are fabricated usage. The pre_native fields precede each step and are not simultaneous post-move coordinates. Source screenshot paths and timestamps are retained in the live JSONL.

## Final filtered-source focused run

Source 24c9bfbfdac39e6b3af01e3fc89517c1f441116538bce96eb075c53483b2e1dc, UTC 2026-09-09T08:44:28.497692+00:00 through 2026-09-09T08:44:34.098133+00:00. Command: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p test_companion*.py -v` with PYTHONDONTWRITEBYTECODE=1.

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
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... ok
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... ok
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... ok
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... ok
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... ok
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... ok
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... ok
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... ok
test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection) ... ok
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... ok
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... ok
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... ok
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... ok
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... ok
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... ok
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... ok
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... ok
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... ok
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... ok
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... ok
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... ok
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... ok
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... ok
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... ok
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... ok
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... ok
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... ok
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... ok
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... ok

----------------------------------------------------------------------
Ran 82 tests in 5.522s

OK
```

## Interrupted full suite (not a final gate)

Source 24c9bfbfdac39e6b3af01e3fc89517c1f441116538bce96eb075c53483b2e1dc; source SHA after 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351. UTC 2026-09-09T08:45:48.472108+00:00 through 2026-09-09T08:49:03.088443+00:00. Repository-root command with PYTHONDONTWRITEBYTECODE=1 and normal process HOME (individual gated tests create their own allow-listed temp fixtures): `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v`. Exit -2.

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
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... ok
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... ok
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... ok
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... ok
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... ok
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... ok
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... ok
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... ok
test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection) ... ok
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... ok
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... ok
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... ok
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... ok
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... ok
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... ok
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... ok
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... ok
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... ok
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... ok
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... ok
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... ok
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... ok
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... ok
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... ok
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... ok
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... ok
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... ok
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... ok
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... ok
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
The anchor test: a third-party process mentioning the path. ... Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/__main__.py", line 18, in <module>
    main(module=None)
    ~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/main.py", line 104, in __init__
    self.runTests()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/main.py", line 270, in runTests
    self.result = testRunner.run(self.test)
                  ~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/runner.py", line 240, in run
    test(result)
    ~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 84, in __call__
    return self.run(*args, **kwds)
           ~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 122, in run
    test(result)
    ~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 84, in __call__
    return self.run(*args, **kwds)
           ~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 122, in run
    test(result)
    ~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 84, in __call__
    return self.run(*args, **kwds)
           ~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/suite.py", line 122, in run
    test(result)
    ~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/case.py", line 707, in __call__
    return self.run(*args, **kwds)
           ~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/case.py", line 651, in run
    self._callTestMethod(testMethod)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/unittest/case.py", line 606, in _callTestMethod
    if method() is not None:
       ~~~~~~^^
  File "/Users/yeongyu/claude-pet/tests/test_updater.py", line 2496, in test_an_unrelated_process_mentioning_the_path_is_not_an_acknowledgement
    self.run_script('/bin/sh -c "sleep 45; true # '
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    '$APP/Contents/MacOS/ClaudePet" &')
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_updater.py", line 2362, in run_script
    return subprocess.run(
           ~~~~~~~~~~~~~~^
        ["/bin/sh", "-c",
        ^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        env=self.script_env(), timeout=120, check=False)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/subprocess.py", line 556, in run
    stdout, stderr = process.communicate(input, timeout=timeout)
                     ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/subprocess.py", line 1222, in communicate
    stdout, stderr = self._communicate(input, endtime, timeout)
                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/subprocess.py", line 2154, in _communicate
    self.wait(timeout=self._remaining_time(endtime))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/subprocess.py", line 1280, in wait
    return self._wait(timeout=timeout)
           ~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/subprocess.py", line 2060, in _wait
    time.sleep(delay)
    ~~~~~~~~~~^^^^^^^
KeyboardInterrupt

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
[gate] rejected: the bundled claude_pet.py is not this checkout's (53def4313b53… != 24c9bfbfdac3…)
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
```

The preceding run was explicitly stopped by Coordinator after a production docstring correction changed the source hash. Verifier sent SIGINT only to its unittest childPID28554; exit-2/KeyboardInterrupt is intentional. No passing full-suite claim is made from that interrupted run.

## Non-discriminating jump-cap fixture: unfavorable result and correction

UTC 2026-09-09T08:54:41.336430+00:00 through 2026-09-09T08:54:44.005246+00:00, production source 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351 unchanged. Original test SHA f4332ab5c5dadd8bc76a19d988bbb9b610c0fba1b4ce971272c3e2803f145113, corrected test SHA 62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e. Mutation removes only the episode cap condition in an in-memory source. The original cursor(-450,600) produced a clamped standoff distance173.27282724pt, less than clearance210.01075238, so the unrelated safety gate blocked the second jump and the incorrect cap-free model passed:

```text
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.055s

OK
```

Reviewer independently recomputed the corrected interior cursor(-1200,600): standoff(-869.81893990,537.68071513), distance336.01075238pt, safely above210.01075238. Only the two post-landing cursor input literals changed; all assertions remain intact. This separates the cap from pointer safety.

### Rival omit_jump_deadline

Exactly one in-memory replacement: `'if now >= self._follow_until:'` → `'if False:'`.

```text
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... FAIL
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... FAIL

======================================================================
FAIL: test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 439, in test_original_follow_deadline_wins_before_late_takeoff_transfer
    self.assertEqual(tuple(out.pos), before)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (783.0855202816326, 591.957113157993) != (-656.7988376890726, 557.4815913929189)

First differing element 0:
783.0855202816326
-656.7988376890726

- (783.0855202816326, 591.957113157993)
+ (-656.7988376890726, 557.4815913929189)

======================================================================
FAIL: test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 454, in test_original_follow_deadline_is_also_checked_during_landing
    self.assertEqual(out.phase, "look")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: 'jump' != 'look'
- jump
+ look


----------------------------------------------------------------------
Ran 2 tests in 0.100s

FAILED (failures=2)
```

### Rival combine_foreign_screen_dwell

Exactly one in-memory replacement: `'self._cross is None or self._cross[0] != cs'` → `'self._cross is None'`.

```text
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... FAIL

======================================================================
FAIL: test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 483, in test_cross_dwell_restarts_when_foreign_screen_identity_changes
    self.assertEqual(out.phase, "follow", "dwell from B and C was incorrectly combined")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'jump' != 'follow'
- jump
+ follow
 : dwell from B and C was incorrectly combined

----------------------------------------------------------------------
Ran 1 test in 0.049s

FAILED (failures=1)
```

### Rival remove_episode_jump_cap

Exactly one in-memory replacement: `'self._follow_jumps < int(self.cfg["follow_max_jumps"])'` → `'True'`.

```text
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... FAIL

======================================================================
FAIL: test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 500, in test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back
    self.assertNotEqual(out.phase, "jump", "a second jump began in the same follow episode")
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'jump' == 'jump' : a second jump began in the same follow episode

----------------------------------------------------------------------
Ran 1 test in 0.051s

FAILED (failures=1)
```

### Rival retain_effect_after_cancel

Exactly one in-memory replacement: `'        self._effect = None\n\n    def _begin'` → `'        pass  # rival retains effect\n\n    def _begin'`.

```text
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... 
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='enabled') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='blocked') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='busy') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='dragging') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='enabled') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='blocked') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='busy') ... FAIL
  test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='dragging') ... FAIL

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='enabled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'takeoff' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='blocked')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'takeoff' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='busy')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'takeoff' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=False, flag='dragging')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'takeoff' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='enabled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'landing' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='blocked')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'landing' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='busy')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'landing' is not None

======================================================================
FAIL: test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) (transferred=True, flag='dragging')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 371, in test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume
    self.assertIsNone(out.effect)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: 'landing' is not None

----------------------------------------------------------------------
Ran 1 test in 0.405s

FAILED (failures=8)
```

### Corrected full play module GREEN

The running full suite had already loaded the earlier fixture SHA; Coordinator directed it to finish, followed by this strengthened entire31-case module run against unchanged final150f source.

```text
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... ok
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... ok
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... ok
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... ok
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... ok
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... ok
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... ok
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... ok
test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection) ... ok
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... ok
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... ok
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... ok
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... ok
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... ok
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... ok
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... ok
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... ok
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... ok
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... ok
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... ok
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... ok
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... ok
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... ok
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... ok
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... ok
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... ok
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... ok
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... ok
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... ok

----------------------------------------------------------------------
Ran 31 tests in 2.002s

OK
```

## Final full suite on150f source

UTC 2026-09-09T08:49:46.346913+00:00 through 2026-09-09T08:55:14.446273+00:00, startSHA 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, endSHA 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, exit0. Command from repository root with PYTHONDONTWRITEBYTECODE=1, normal HOME and individual test temp isolation: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v`.

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
test_cross_dwell_restarts_when_foreign_screen_identity_changes (test_companion_play.FollowAcrossScreensTests.test_cross_dwell_restarts_when_foreign_screen_identity_changes) ... ok
test_cursor_none_cancels_follow_in_both_jump_stages (test_companion_play.FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages) ... ok
test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back (test_companion_play.FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back) ... ok
test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell (test_companion_play.FollowAcrossScreensTests.test_gap_cursor_is_not_mistaken_for_radius_expanded_screen_and_resets_dwell) ... ok
test_original_follow_deadline_is_also_checked_during_landing (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_is_also_checked_during_landing) ... ok
test_original_follow_deadline_wins_before_late_takeoff_transfer (test_companion_play.FollowAcrossScreensTests.test_original_follow_deadline_wins_before_late_takeoff_transfer) ... ok
test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume (test_companion_play.MonitorJumpTests.test_all_user_holds_cancel_takeoff_and_landing_without_teleport_or_stale_resume) ... ok
test_cursor_covering_landing_is_rechecked_before_transfer (test_companion_play.MonitorJumpTests.test_cursor_covering_landing_is_rechecked_before_transfer) ... ok
test_destination_id_survives_inventory_reordering (test_companion_play.MonitorJumpTests.test_destination_id_survives_inventory_reordering) ... ok
test_inverted_destination_bounds_are_excluded_before_jump_selection (test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection) ... ok
test_jump_cooldown_starts_after_first_eligible_jump (test_companion_play.MonitorJumpTests.test_jump_cooldown_starts_after_first_eligible_jump) ... ok
test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp (test_companion_play.MonitorJumpTests.test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp) ... ok
test_jump_probability_has_both_branches_at_the_default_threshold (test_companion_play.MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold) ... ok
test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds (test_companion_play.MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds) ... ok
test_missing_or_shrunk_target_cancels_before_transfer (test_companion_play.MonitorJumpTests.test_missing_or_shrunk_target_cancels_before_transfer) ... ok
test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws (test_companion_play.MonitorJumpTests.test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws) ... ok
test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions (test_companion_play.MonitorJumpTests.test_takeoff_transfer_landing_and_rest_have_reachable_discrete_positions) ... ok
test_effect_field_is_appended_with_legacy_five_argument_default (test_companion_play.PlayApiTests.test_effect_field_is_appended_with_legacy_five_argument_default) ... ok
test_production_cadence_duration_and_jump_defaults_match_agreed_contract (test_companion_play.PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract) ... ok
test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct (test_companion_play.PlayApiTests.test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct) ... ok
test_follow_travel_folds_and_completion_look_gets_summary (test_companion_play.PlayPresentationTests.test_follow_travel_folds_and_completion_look_gets_summary) ... ok
test_cursor_entering_clearance_causes_no_new_movement_toward_it (test_companion_play.TimedFollowTests.test_cursor_entering_clearance_causes_no_new_movement_toward_it) ... ok
test_duration_endpoints_do_not_finish_early_on_near_target_arrival (test_companion_play.TimedFollowTests.test_duration_endpoints_do_not_finish_early_on_near_target_arrival) ... ok
test_every_hold_immediately_cancels_follow_without_stale_resume (test_companion_play.TimedFollowTests.test_every_hold_immediately_cancels_follow_without_stale_resume) ... ok
test_first_ordinary_eligibility_can_select_follow (test_companion_play.TimedFollowTests.test_first_ordinary_eligibility_can_select_follow) ... ok
test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts (test_companion_play.TimedFollowTests.test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts) ... ok
test_follow_retargets_upward_instead_of_retaining_horizontal_target (test_companion_play.TimedFollowTests.test_follow_retargets_upward_instead_of_retaining_horizontal_target) ... ok
test_follow_uses_its_own_speed_and_capped_elapsed_time (test_companion_play.TimedFollowTests.test_follow_uses_its_own_speed_and_capped_elapsed_time) ... ok
test_missing_cursor_cancels_in_place_without_claiming_natural_completion (test_companion_play.TimedFollowTests.test_missing_cursor_cancels_in_place_without_claiming_natural_completion) ... ok
test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest (test_companion_play.TimedFollowTests.test_retargets_do_not_restart_deadline_and_finish_with_summary_then_rest) ... ok
test_selection_threshold_has_both_follow_and_ordinary_branches (test_companion_play.TimedFollowTests.test_selection_threshold_has_both_follow_and_ordinary_branches) ... ok
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
Ran 485 tests in 327.916s

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
[gate] rejected: the bundled claude_pet.py is not this checkout's (53def4313b53… != 150f57757483…)
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

## Final real-time controls and jump

All entries below are original event-loop steps with actual OS mouse input,
recorded in companion-play-live-20260909.jsonl. Usage is fabricated and probability
selection is forced as documented; elapsed time, movement speed, phase durations,
original step return and native adapter remain unchanged.

- Source24c9/PID27202: actual hover result at2026-09-09T08:46:05.408587Z reports
  rest, blockedTrue, settledFalse, fixed position and native alpha1.0. This stopped
  the active follow before its chosen deadline rather than claiming natural expiry.
- Actual menu off at08:47:53.167838Z reports enabledFalse and roamFalse in the
  isolated config; on at08:47:54.115436Z reports enabledTrue/roamTrue. The popup
  was identified by actual CGWindow layer101 and AXMenuItem hit-testing before
  clicking. Settings at08:47:55.058048Z reports busyTrue/settings_openTrue.
  Closing the settings dialog clears settings_open.
- Actual drag at08:48:56.586805Z moves desktop(376,418)→(316,388), and changes
  isolated config from x220/y200 to x252/y319; manual home becomes(386,424).
  The preceding automatic movement, hover and toggle operations left x/y unchanged.
  Config differences are recorded with each input, not inferred from source text.
- Source150f/PID39717 uses two synthetic screen partitions within the single
  actual display: frameA(0,0,650,761), frameB(703,0,1353,761), actual visible
  y36–731. Stable fixture IDs9001/9002 flow through the real adapter. Default
  real-clock takeoff begins08:51:05.797646Z at(386,484); atomic transfer is at
 08:51:06.548016Z to(866.9134822424894,569.7074731387336), look at08:51:07.097774Z,
  rest at08:51:09.098025Z. Observed takeoff interval0.750370s and landing0.549758s
  include timer scheduling. Seven recorded jump-step samples include actual
  native alpha1→0.15→0.6593489695; subsequent rest opacity0.99941541245 is within
  the adapter's1e-3 update tolerance of1. Native source/landing compact frames
  are(256,481,128,108) and(737,566,128,108). The transfer row's pre_native still
  belongs to source; the following08:51:06.597800Z sample shows the target frame.
  A separate screenshot observer began too late at08:51:17.183195Z and captured
  no jump; that unfavorable capture result is retained, not represented as video.
- Source150f/PID49689: actual native takeoff alpha0.7724403739 was queried at
 08:56:51.363177Z; OS hover was posted inside that actual compact frame at
 08:56:51.363704Z. Result at08:56:52.167949Z is rest/effectNone, source position
 (386,484), screen9001 and native alpha1.0. The actual screenshot path is in the
  raw event. This verifies real-clock cancellation, separately from natural completion.

These are sampled GUI episodes, not estimates of production occurrence frequency.
They do not establish hardware/OS inter-monitor transit. That boundary remains open
until another actual display is connected; synthetic negative-origin geometry,
stable screen IDs and real NSWindow placement are covered independently.

## Final source connection and full-suite coverage

Final150f differs from24c9 only in the `_plan` docstring. Verifier independently
replaced the exact new five-line paragraph with its prior three-line paragraph
in memory and obtained SHA25624c9bfbfdac39e6b3af01e3fc89517c1f441116538bce96eb075c53483b2e1dc.
Thus the24c9 native/control evidence exercises identical executable code to150f.
The earlier0c2c→24c9 correction filters invalid safe rectangles; all real GUI
screen fixtures in the0c2c follow episode were valid.

Final full suite:485 unittest cases,478 passing and7 existing opt-in skips,
UTC2026-09-09T08:49:46.346913Z–08:55:14.446273Z, source150f at both bounds.
The7 skips are2 installed-app preflight,2 real stapler, and3 old-installed-version
boundary cases; no live install/sign/release permission was exercised. The full
suite had loaded the pre-correction jump-cap cursor fixture. After the fixture
was strengthened, the entire31-case play module passed on150f at
08:54:41.336430Z–08:54:44.005246Z; its SHA is
62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e.
The source and assertions were not relaxed to obtain those results.

## Frozen live trace and normal handoff

Measured2026-09-09T08:59:00.921799Z from only the assigned live JSONL,
grouping one recorded Roamer.step observation (sampling, not every timer callback):

| PID/source | Absolute UTC observation bounds | Recorded steps | Positions outside all supplied safe bounds |
| --- | --- | ---: | ---: |
|14581/0c2c|2026-09-09T08:38:26.696719Z–08:44:51.396847Z|1391|0|
|27202/24c9|2026-09-09T08:44:51.738029Z–08:50:08.886719Z|796|0|
|39717/150f|2026-09-09T08:50:09.647553Z–08:55:24.899546Z|1131|0|
|49689/150f|2026-09-09T08:55:25.482313Z–08:57:42.581991Z|494|0|

Raw trace SHA2562bbcc33b4708de9da67beb9f7f918d31fc6ee04a47c3b7bdf8b633b06af7f235,
4437143bytes,3812recorded steps total. It had the same SHA at08:58:24Z and
08:59:00.921799Z after all instrumented GUI processes stopped. This checks trace
cessation; no claim is made about all possible future coordinates.

QA PIDs14581,27202,39717,49689 and prior owned development PID30313 were stopped
by exact PID after checking their executable/argv. Installed PID29528 remains
`/Applications/ClaudePet.app/Contents/MacOS/ClaudePet`; that bundle was unchanged.
Only the assigned temporary config was restored: x252/y319, scale.5, roamTrue,
spike_mult1.0, langko, and the temporary greet override removed. No test wrote
actual user config. Selection/cooldown/duration overrides were never persisted.

Final normal development PID55054 started2026-09-09T08:57:42.796370Z from source
150f with the following exact stdin launch (PYTHONDONTWRITEBYTECODE=1,
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3):

```python
import os,sys,hashlib,datetime
sys.path.insert(0,'/Users/yeongyu/claude-pet')
import claude_pet as pet
pet.CONFIG_PATH='/tmp/claudepet-companion-play-20260909-config.json'
pet.apply_config(pet.load_config())
print('NORMAL_DEV_PID',os.getpid(),'UTC',datetime.datetime.now(datetime.timezone.utc).isoformat(),'SOURCE',hashlib.sha256(open('/Users/yeongyu/claude-pet/claude_pet.py','rb').read()).hexdigest(),'CONFIG',pet.CONFIG_PATH,'FOLLOW_P',pet.ROAM_DEFAULTS['follow_p'],'JUMP_P',pet.ROAM_DEFAULTS['jump_p'],flush=True)
pet.run_gui()
```

This fresh normal process has no synthetic usage, virtual screens, trace wrapper,
or probability/timing override: follow_p.35 and jump_p.5 are production defaults.
It is the user's development handoff, not a real-user-log test. At08:58:24.606Z,
Orca confirmed its visible, non-minimized window1819 at desktop(252,172,268,240);
only installed29528 and normal-dev55054 remain among the checked app PIDs.
The actual screenshot is `/var/folders/dq/w9mxm3513csghc_7h8xg8wj40000gn/T/orca-computer-use/a9fbdc4f-83f3-4cc1-832a-a7179e9e080f-screenshot.png`.
Original desktop pointer(49,0) was restored after testing.

No production files were edited by Verifier. Commit/staging remains Coordinator-gated.
Assigned local QA JSON/PNG/helper/config remain local evidence; the intended test
commit contains the five named test paths plus this verification document only.
