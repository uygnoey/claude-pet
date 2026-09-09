# Free roaming without automatic return — independent review

Reviewer: Codex `/root/reviewer`. Coordinator: `/root`. Developer: the user's
designated Claude agent. Verifier: Mendel (`/root/verifier`). This is a new change,
separate from the previous quiet-companion implementation and release.

My only assigned writable deliverable is this document. Its absence was checked
before creation. Application source, tests, earlier review/QA artifacts, release
artifacts and GUI inputs are outside my ownership. No production or gating test
edit, GUI input, launch, commit or release operation has been performed by me.

Status: **APPROVED — final independent review complete**.
Approved source SHA256:
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.
The initial pre-implementation source examined at
`2026-09-09T07:13:45.573067Z` is SHA256
`3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c`,
with Coordinator-provided base HEAD `24731b0`. Tracked files were clean at the
initial inspection; existing untracked files were left untouched.

## Required behavior and concrete old-code hazards

The user requests random destinations across the current monitor and says the
pet need not return to its original place. The agreed scope preserves the calm
timing/speed, fixed destination per trip, cursor avoidance, interruption rules,
compact walking, arrival summary and manual display preference. Natural
completion rests at the arrival position and restores that preference. Automatic
motion must not save coordinates.

The following expectations were derived from that request and existing source
before reading any new gating test or fixture:

- **Remove both automatic return entry points.** Existing `Roamer.step` starts a
  home leg when an away look expires; existing `_plan` also starts a home leg
  when no new approach/wander is eligible. Removing only the first still returns
  after interruption, cooldown or candidate rejection. Neither natural
  completion nor a later idle planning attempt may move toward old home.
- **Keep manual home as a manual reference.** The Coordinator confirmed this
  scope after review. Natural completion should not use automatic `set_home`
  calls as a workaround. Current `pos` remains the arrival location; `home`
  stays the manual-placement reference, and `away` can consequently remain true.
- **Separate display restoration from distance to home.** Existing
  `RoamDisplay.note` clears a naturally completed summary only when
  `phase == rest and not away and settled`. Under the new behavior, rest with
  `settled=True` must restore manual full/folded display even when away is true.
  Hover and ordinary-click stops still use `settled=False` and retain the
  summary/expanded latch for the user to operate it. Real drag and explicit
  interruption retain their existing reset semantics.
- **Preserve safety in logical full-window coordinates.** Crop sizes are
  presentation geometry, not the new sampling envelope. The current
  `roam_bounds` uses `win.screen() or NSScreen.mainScreen()` and full logical
  dimensions; it does not select a screen from `roamer.home`. No unsupported
  monitor-selector change is requested. Negative origins, changed display
  bounds, full-window restoration and cursor clearance must keep working.
- **Use new bounds when replanning, discard interrupted targets.** Invalid
  bounds still freeze/cancel; recovery from a monitor shrink must put the full
  envelope inside the valid screen and cancel the obsolete trip. There is no
  later home fallback after recovery. The old manual home may remain metadata
  but must not constrain the random destination radius or direct movement.

## Independent random-geometry oracle

These are stipulated geometric inputs, not observations or a frequency claim.
The numeric oracle was derived before the sampling API was settled. The later
Developer/Coordinator proposal confirms independent uniform x/y draws over
allowed-center bounds, matching that assumption.

All coordinates are global AppKit points, y upward. Let the current monitor's
visible frame be `(-1920,80,1600,1000)`, and the logical full window be
`300 × 220`. The full-window-safe center rectangle is:

```text
x0 = -1920 + 150        = -1770
x1 = -1920 + 1600 - 150 =  -470
y0 =    80 + 110        =   190
y1 =    80 + 1000 - 110 =   970
span = (1300,780)
```

For normalized random draws `(u,v)=(0.8,0.25)`, independent x/y interpolation
gives destination `(-730,385)`. From current position `(-1680,880)`, that trip
has length `1071.2259332185718` points, discriminating both a lingering
160-point local radius and a mistakenly reused 360-point approach cap. At the
unchanged configured speed of 55 points/second, distance/speed is approximately
19.48 seconds under uninterrupted ideal callbacks; this is not a wall-clock
duration bound.

| Candidate behavior | Destination for the same normalized draws |
| --- | --- |
| Correct safe-center rectangle | `(-730,385)` |
| Sample raw visible frame, then clamp | `(-640,330)` |
| Ignore screen origin | `(1190,305)` |
| Exchange x/y random draws | `(-1445,814)` |
| Reverse global y as though flipped view coordinates | `(-730,775)` |
| Use compact `112 × 64` dimensions for bounds | `(-673.6,346)` |

The endpoint controls are also exact: `(u,v)=(0,0)` gives center
`(-1770,190)` and full-window origin `(-1920,80)`; `(1,1)` gives center
`(-470,970)` and origin `(-620,860)`. Their full rectangles touch the stipulated
visible-frame edges without crossing them. The source/test fixture may choose
other draws, but must distinguish these plausible wrong coordinate systems
and old local-radius restrictions.

## Independent completion/interruption oracles

These are state-transition expectations, not empirically measured timings.

1. Start a valid trip with arrival different from manual home. After the
   approach's existing look duration or the wander pause expires, output must
   be `phase=rest`, unchanged arrival position, no walking animation,
   `settled=True`; manual home remains unchanged. The display is full when the
   manual preference is full, folded when it is folded, regardless of away.
2. Interrupt an away trip and hold long enough to pass the old rest deadline.
   Its position must remain fixed and its old destination must be discarded.
   At the next eligible planning time, keep both activity cooldowns unavailable:
   it must remain at rest and rearm, never enter `home`. Repeat with an unsafe
   or too-near random candidate so candidate rejection cannot hide a return.
3. Hover or an ordinary click during arrival summary still leaves
   `settled=False`, preserving summary/expanded state even after phase becomes
   rest. Natural rest completion clears that latch even though away remains
   true. Clearing all away summaries on every rest would fail this rival.
4. The next destination after natural completion must derive from the current
   monitor's full safe rectangle, not a radius around either initial home or
   the previous arrival. Fixed-target motion and segment-to-cursor checks still
   apply on every active step; sampling the whole monitor grants no exception
   to those guards.

The initial source therefore does not satisfy the new behavior by design.
Failure output, implementation fixes and final approval will be recorded only
after the independent Verifier's RED and final source review are available.

## Proposed API review

The Coordinator relayed this proposal: replace `wander_radius` with
`wander_enabled=True` and `wander_tries=6`; `_plan_wander(cursor,bounds)` draws
one x and one y per attempt over the full safe rectangle. Reject a candidate
when it is closer than `min_trip=60` to current position, closer than
`approach_stop + radius` to the cursor, or its whole segment comes within
`radius + cursor_margin` of the cursor. The existing cursor margin is 24.
Remove the home phase and both return entry points; retain manual home and
the existing screen/bounds adapter; reset display on `rest and settled`
regardless of away.

No unresolved structural blocker was found in that proposal. Final code review
must still confirm that exhausted retries return no destination and rearm rest
at the current position, accepted targets stay fixed, every active step retains
cursor safety, and natural completion clears walking/summary state. Neither an
invalid final candidate nor old home is an acceptable retry fallback. Approval
of this design is not implementation or runtime sign-off.

## Independent baseline RED replay

At the Coordinator's request, I independently executed the Verifier's new test
module against the pre-change source from Git. The source was read with
`git show` and supplied to the existing AST extractor in memory. No scratch
file, production edit, test edit, import of the application, GUI launch, or user
data/config access was needed. Python's `-B` flag suppressed bytecode writes.
The expected geometry/state values above had been independently derived
before I read this test module; this replay is not a separation exception.

Measured run window: **2026-09-09T07:26:53.831113Z through
2026-09-09T07:26:54.105878Z**. Grouping is discovered unittest case, with failed
subtests counted separately as failure outcomes: **6/6 cases had at least one
failure; 10 failure outcomes, 0 errors, 0 skips**. This is a deliberately RED
baseline replay, not a final implementation pass or a general test-coverage
claim. All file inputs are enumerated here:

| Input | SHA256 |
| --- | --- |
| `24731b064ce30bd7b6303a505abd4a32999696ed:claude_pet.py` from Git | `3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c` |
| `tests/test_companion_motion.py`, current extractor/helper | `1e8bf57d4240faf2d7339bc9b9f187db32dcd31bac8e2b272f9d969aeaf2e0b2` |
| `tests/test_free_roaming.py`, current gating module | `92f103ef1f61d7fa60fa861e03154642afa112d2d2968954286ce12b68d43e6c` |

The working-tree source was hashed only for preservation checking, not loaded
as the code under test. Its hash was
`09311a7cb0271e4fe528593fd1513d1ac5d29e1002ce8e0078a14b7cd140a6fc`
at both ends of this run. The Developer was implementing in parallel; this
hash is not a freeze or an approval.

Exact executed command (repository root):

```sh
python3 -B - <<'PY'
import datetime, hashlib, io, pathlib, subprocess, sys, types, unittest
root = pathlib.Path.cwd()
sha = lambda data: hashlib.sha256(data).hexdigest()
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
base = subprocess.check_output(['git', 'show', '24731b064ce30bd7b6303a505abd4a32999696ed:claude_pet.py'])
helper_path = root / 'tests/test_companion_motion.py'
test_path = root / 'tests/test_free_roaming.py'
helper_bytes = helper_path.read_bytes()
test_bytes = test_path.read_bytes()
source_before = sha((root / 'claude_pet.py').read_bytes())
helper = types.ModuleType('test_companion_motion')
helper.__file__ = str(helper_path)
sys.modules[helper.__name__] = helper
exec(compile(helper_bytes, str(helper_path), 'exec'), helper.__dict__)
class HeadSource:
    def read_text(self, encoding='utf-8'):
        return base.decode(encoding)
    def __str__(self):
        return 'git:24731b064ce30bd7b6303a505abd4a32999696ed:claude_pet.py'
helper.SOURCE = HeadSource()
tests = types.ModuleType('test_free_roaming')
tests.__file__ = str(test_path)
exec(compile(test_bytes, str(test_path), 'exec'), tests.__dict__)
suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
end = datetime.datetime.now(datetime.timezone.utc).isoformat()
print('START_UTC', start)
print('END_UTC', end)
print('BASE_SOURCE_SHA256', sha(base))
print('HELPER_SHA256', sha(helper_bytes))
print('FREE_TEST_SHA256', sha(test_bytes))
print('WORKTREE_SOURCE_BEFORE', source_before)
print('WORKTREE_SOURCE_AFTER', sha((root / 'claude_pet.py').read_bytes()))
print('CASES', result.testsRun, 'FAILURE_OUTCOMES', len(result.failures), 'ERRORS', len(result.errors), 'SKIPS', len(result.skipped))
print(stream.getvalue())
PY
```

Actual assertion output excerpts are retained below. Repeated traceback frames
are omitted; no assertion text or observed values have been inferred.

```text
FAIL: test_approach_and_wander_finish_at_their_destination_without_return (kind='approach')
AssertionError: 'home' != 'rest'
- home
+ rest
 : arrival pause started an unwanted return leg

FAIL: test_approach_and_wander_finish_at_their_destination_without_return (kind='wander')
AssertionError: 'home' != 'rest'
- home
+ rest
 : arrival pause started an unwanted return leg

FAIL: test_interrupted_trip_does_not_fall_back_to_old_manual_home
AssertionError: 'home' != 'rest'
- home
+ rest
 : idle fallback resumed travel toward the old home

FAIL: test_natural_away_completion_restores_preference_but_hover_keeps_summary (preference=False, natural=True)
AssertionError: 'summary' != 'folded'
- summary
+ folded
 : display confused natural completion away from home with hover

FAIL: test_natural_away_completion_restores_preference_but_hover_keeps_summary (preference=True, natural=True)
AssertionError: 'summary' != 'full'
- summary
+ full
 : display confused natural completion away from home with hover

FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (draws=(0.8, 0.25))
AssertionError: Tuples differ: (-1653.7335554781296, 799.160196114912) != (-730.0, 385.0)

FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (draws=(0.0, 0.0))
AssertionError: Tuples differ: (-1620.0, 880.0) != (-1770.0, 190.0)

FAIL: test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (draws=(1.0, 1.0))
AssertionError: Tuples differ: (-1520.0, 880.0) != (-470.0, 970.0)

FAIL: test_retries_reject_short_endpoint_and_crossing_candidates_before_departure
AssertionError: Tuples differ: (275.95136462264367, 340.8711721382961) != (1400.0, 150.0)

FAIL: test_six_invalid_candidates_stop_retrying_without_motion_or_return
AssertionError: 'out' != 'rest'
- out
+ rest
 : exhausted random search started an unintended trip

----------------------------------------------------------------------
Ran 6 tests in 0.223s

FAILED (failures=10)
```

This independently reproduces the Verifier's claimed old-behavior failures.
It does not by itself discriminate every rival mutant; the sampling and state
oracles identify those additional checks, and final test-diff review remains
pending the frozen implementation.

## Provisional implementation and gating-diff review

Reviewed the current production diff and complete relevant definitions, plus
the tracked test diff and new test file, during
`2026-09-09T07:28:44.291807Z`–`2026-09-09T07:29:41.272975Z`.
Production SHA256 was unchanged at both endpoints:
`f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288`.
The exact bytes of `git diff -- tests` hashed to
`56b5c9e66c57d83bd8f2b70524288e75819b47a477284c3d8e6436f7b6eff346`
at both endpoints. That tracked diff excludes the new untracked
`tests/test_free_roaming.py`, whose separate hash remains
`92f103ef1f61d7fa60fa861e03154642afa112d2d2968954286ce12b68d43e6c`.
These pins identify a provisional review checkpoint, not the final freeze.

**Production behavior: no correctness blocker found in this checkpoint.**
`_plan_wander` samples the full safe-center rectangle using independent x/y
uniform draws, rejects short, endpoint-overlapping and cursor-crossing trips,
and returns `None` after its bounded search. No approach cap or home-distance
cap constrains these random destinations. `_plan` cannot start a home trip;
look expiry calls `_stop(...,settled=True)` at current position; the remaining
active leg only uses the fixed target. Every active tick still checks cursor
clearance. Display restoration now depends on natural settlement, preserving
the hover/click latch when `settled=False`. Logical crop, drag persistence,
monitor selection/recovery, Reduce Motion and other suppression code retain
their previous behavior.

The legacy `wander_radius` compatibility check only disables wandering when
that internal config value is zero. Positive values no longer supply a
distance or affect the sampled rectangle. This branch does not narrow default
roaming, and the key is not a persisted user preference. It is not a blocker.

**Test changes: no unrelated weakening found.** Return-phase requirements are
replaced by arrival rest, with disabled-after-arrival immobility and leftward
outbound cursor protection retained. The approach-cooldown counter now counts
in-place looks as visits, which becomes necessary when subsequent activity
starts from the prior arrival. The old local-radius assertion is replaced by
safe-rectangle membership, travel beyond the old cap, manual-home preservation
and no-home-phase checks; the existing cooldown/pause requirements remain.
`wander_enabled=False` isolates approach-only fixtures that could otherwise
start a newly expanded random walk. Presentation fixtures explicitly state the
natural/hover completion reason. Native assertions now verify arrival remains
fixed and full presentation returns there; artifact paths are redirected to
newly assigned deliverables. Safety geometry/hold/drag assertions are retained.
The release source-hash pins had not yet been updated at this checkpoint;
their final diff will need a separate equality-only check.

Only documentation/comment accuracy issues were sent to the Coordinator:
the source and new design document say no behavior uses `away`, although
`roam_resync` still reads it; that claim should be narrowed to automatic
planning/display restoration. The core docstring retains an obsolete
`out/home` description, and display priority still says home rest. The new
design document initially links previous-change review/verification files and
lists Developer test totals without reproducible run metadata. These are
pending corrections, not new production-feature requests. Final source/doc
approval awaits the official freeze, the resulting comment/doc diff and the
Verifier's final evidence.

## Native fixture baseline correction review

The Verifier's preserved native run at
`2026-09-09T07:31:02.508848Z`–`2026-09-09T07:31:02.880644Z` failed the newly
added comparison of completed-trip manual home with the pre-first-tick
synthetic center. That is the Verifier's runtime observation, recorded in
`free-roaming-verification-20260909.md`; I did not rerun or control a GUI.

Independent source inspection explains why those two baselines need not be
equal. `CUR_PILL` begins at four rows, whereas the smoke's initial
`state.oauth=None` makes `cur_rows_n()` return three. At the beginning of the
first `Ticker.tick_`, `apply_pill_rows` reduces full height by one `ROW_H=30`,
preserves the top, calls `roam_env_update`, then `roam_resync`. Because no trip
has begun and `away=False`, the latter calls `set_home` with the actual resized
window center. Algebraically, top-preserving height reduction by 30 raises
the center by 15 points before automatic departure. These are deterministic
source facts, and that adapter path is unchanged by this feature.

The reported native values—requested pre-first-tick `(636.5,343.5)` and later
home `(636,358)`—are consistent with that 15-point shift plus the native
fractional-origin quantization already observed in this fixture. This is a
consistency check of the reported run, not an independent native measurement
or a universal AppKit rounding guarantee.

Recording actual manual home at departure and comparing the completed trip
against it is the appropriate fixture reference for automatic-motion
preservation. The original failure remains evidence of a harness-baseline
mistake; it does not establish a production regression. The corrected native
run must still pass destination immobility, unchanged departure home, display
restoration and no automatic config writes. No production fix is requested.

## Final source approval and independent GREEN replay

**Source-only approval: APPROVED** on
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.
At `2026-09-09T07:34:12.269017Z`, I rehashed that source and reread its complete
production diff. At `2026-09-09T07:34:51.033210Z`, an in-memory reversal of only
the five updated comment/docstring passages reconstructed the prior reviewed
SHA `f61851d00c58ec258f78c57458c449c483984031cea65359718c253ef70a3288`
exactly. The passages were the `away` output comment, the obsolete two-leg
description, the display's home-versus-arrival description, display priority,
and the `note` completion-reason description. This exact-byte reconstruction
confirms the final source delta since that checkpoint contains those textual
corrections only. Nothing was written back to application source.

I then independently reran the same new module that failed in the baseline
replay. Measured window:
**2026-09-09T07:35:41.106656Z–2026-09-09T07:35:41.382297Z**.
Grouping is unittest case: **6/6 passed**, no failures, errors or skips; measured
at run end. Source hash at both ends was the approved `f3810b14…` value above.
Read file set: `claude_pet.py` via the pure AST extractor,
`tests/test_free_roaming.py` SHA
`92f103ef1f61d7fa60fa861e03154642afa112d2d2968954286ce12b68d43e6c`,
and `tests/test_companion_motion.py` SHA
`ff04e8828b651d4cc4082b77ef0f4a2a749725ab5e6a9655066d29a8e50a022e`.
The new test module is byte-identical to my RED replay. The helper's intervening
changes were in the already-reviewed existing-gate/native migration; the
`pure_api` and `MinimumRng` definitions used by these six tests were unchanged.

Exact test command from repository root:

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -B -m unittest discover -s tests -p test_free_roaming.py -v
```

Actual output, exit 0:

```text
test_approach_and_wander_finish_at_their_destination_without_return (test_free_roaming.FreeRoamingCompletionTests.test_approach_and_wander_finish_at_their_destination_without_return) ... ok
test_interrupted_trip_does_not_fall_back_to_old_manual_home (test_free_roaming.FreeRoamingCompletionTests.test_interrupted_trip_does_not_fall_back_to_old_manual_home) ... ok
test_natural_away_completion_restores_preference_but_hover_keeps_summary (test_free_roaming.FreeRoamingCompletionTests.test_natural_away_completion_restores_preference_but_hover_keeps_summary) ... ok
test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk (test_free_roaming.FreeRoamingSamplingTests.test_random_xy_spans_negative_origin_safe_rectangle_not_old_home_disk) ... ok
test_retries_reject_short_endpoint_and_crossing_candidates_before_departure (test_free_roaming.FreeRoamingSamplingTests.test_retries_reject_short_endpoint_and_crossing_candidates_before_departure) ... ok
test_six_invalid_candidates_stop_retrying_without_motion_or_return (test_free_roaming.FreeRoamingSamplingTests.test_six_invalid_candidates_stop_retrying_without_motion_or_return) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.212s

OK
```

The exact equality pin replacement in `tests/test_upload_artifact_gate.py`
was also inspected: only the reviewed app-source hash changed from baseline
to the approved source hash. Final release-contract pin and complete test-diff
hash review remain pending, along with the final full-suite/live evidence and
documentation corrections. This section approves source correctness and
independently confirms the new tests' RED-to-GREEN behavior; it is not a
commit, merge, release or installation operation.

## Final documentation and test-diff approval

**Documentation and test changes: APPROVED**, checked at
`2026-09-09T07:38:56.965950Z`. Source still hashes to the approved `f3810b14…`.
The complete tracked test diff (`git diff -- tests`) is pinned by SHA256
`156e27fecb77302bb4b0c13b64a7552d4c441eeb2a1540c531f0c19780379ff1`.
The separate new test file is still SHA
`92f103ef1f61d7fa60fa861e03154642afa112d2d2968954286ce12b68d43e6c`.
This includes the native departure-home reference correction described above;
no unrelated assertion or fixture weakening was found. The checks removed or
replaced concern the explicitly removed return phase and local wander radius.
Existing safety and manual-choice requirements continue to be asserted.

The only pin-file changes are the exact reviewed application SHA in
`tests/test_manual_update_transaction.py` and
`tests/test_upload_artifact_gate.py`. Their final file hashes are respectively
`a32b901d527de8fabd9895265d31756bcedaaf9dff2e14154c96ef9637618f9f`
and `7b911da45a9f9ed6bbaf342fc983d48faf00671318c62a031bee1eb3ee3d489e`.
`tests/test_v021_release_contract.py` is unchanged; its existing logic reads
those pin constants and compares them to actual source bytes, so no separate
assertion or pin edit there is necessary. The final companion test file is
`ff04e8828b651d4cc4082b77ef0f4a2a749725ab5e6a9655066d29a8e50a022e`.

Reviewed documentation files: `README.md`, `README.ko.md`, `README.ja.md`,
`README.es.md`, `docs-design/quiet-companion.md` and
`docs-design/free-roaming-20260909.md`. The technical documents at this
checkpoint hash respectively to
`812411a9410619be9a33c7e133610162a85eb9599c97ff8294e1f79571746702`
and `e3d95053f1040c13e8411113631fa46f7d4905546705c897d44328f0a4d27fb0`.
R5/R7 and D1/D4 now describe only outbound movement, resting at arrival and
completion-reason-based display restoration. The mode/boundary descriptions
were brought into the same contract. The new design document points to this
change's independent records and distinguishes its internal legacy OFF key
from radius-based travel. Developer-local test totals are no longer presented
as independent verification evidence. No further documentation correction is
required for this change.

## Final independent verification evidence inspected

I directly read the Verifier's commands, raw output and source pins in
[free-roaming-verification-20260909.md](free-roaming-verification-20260909.md),
including its "Final frozen-source full suite" section. The Verifier ran:

```sh
PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v
```

The run window was **2026-09-09T07:34:23.460831Z through
2026-09-09T07:39:47.202068Z**, measured at its end. Grouping is discovered
unittest case; file set is `tests/test_*.py`, the source/release scripts and
the modules' synthetic fixtures, as recorded by the Verifier. The exact output
ends:

```text
Ran 454 tests in 323.611s

OK (skipped=7)
```

Thus **447/454 discovered cases passed; 7 were explicitly skipped; no failure
or error; exit 0**. Those skips are the existing opt-in installed-app,
stapler and installed-version-boundary checks. They are not counted as passes.
The Verifier's recorded source SHA before and after is the approved
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.

I also inspected the final native JSON and rendered PNG. This is the real
NSWindow/PetView with controlled clock/pointer and blocked background workers,
not the real-time GUI run. The native command's outer run window in the report
is `2026-09-09T07:37:19.532584Z`–`2026-09-09T07:37:20.111081Z`; the JSON's inner
measurement window is `2026-09-09T07:37:19.688436Z`–`2026-09-09T07:37:20.072234Z`.
The JSON SHA256 I read is
`48a22cedd513ad141a6cd469e422d0feb2580405c832f0051696b0828a590e1d`.
Its complete measured file set is that JSON and corresponding
`free-roaming-native-20260909.png`, produced from the approved source by
`tests/test_companion_motion.py --native-smoke --compact-presentation-gate`.

Grouping is manually invoked native tick: **1905 samples**, synthetic time
`0.05`–`95.25`. The recorded transition sequence is out at `72.7`, look at
`79.25`, rest at `85.25`, followed by ten synthetic seconds at the arrival.
Departure home is `(636,358)`, arrival model position is
`(953.1244560754362,528.3880258670152)`, and the last sample retains that arrival.
The native frame changes `128×108 → 130×140 → 268×240`, consistent with walking,
summary and restored full display. Both midpoint crossings occurred. The
record reports **0/1905 native visible-bounds violations**, no forbidden I/O
calls and no config writes for this controlled run. These are scoped fixture
observations; they do not assert universal native fractional rounding or
real-world behavior frequency. The rendered columns depict walking, looking
with the scan-status summary, then idle with the full panel, matching those
states.

The Verifier's five targeted rival runs also retain actual failing assertions
after passing unchanged controls (UTC
`2026-09-09T07:35:02.209073Z`–`2026-09-09T07:35:02.605126Z`, same approved source).
Grouping is rival paired with targeted test, files are the companion test
module and an in-memory source snapshot: **5/5 proposed rivals were killed**.
This is fault-injection evidence, not a claim that a sample proves all
possible incorrect implementations absent. The full-rectangle, no-return and
natural-away failures are separately established by the actual baseline RED
runs and my independent RED/GREEN replay above.

## Real-time evidence review and final sign-off

I read the sealed Verifier report (SHA256
`dc376aaef488ae8c58454a931b12e440fa27fb53d59797a473fa739ef9009ce0`),
the live helper, the live trace and both image artifacts. At
`2026-09-09T07:44:20.964897Z`, I independently rehashed the stopped live trace
to `a19cb52f46c40a2d1e17d388d19067c46ea0fa5ab31900578b334399eef37961`.
Parsing that exact snapshot confirms **1113 total records, including 1105
sampled original motion calls**, across the absolute window
**2026-09-09T07:30:21.958774Z–2026-09-09T07:40:39.348469Z**.
Grouping is trace record or sampled original call, as stated; the complete
data file is `free-roaming-live-20260909.jsonl`. Independently comparing each
sample's native frame with the reported visible frame `(0,36,1353,695)` and
the stated one-point rounding tolerance gives **0/1105 bounds violations**.
This is scoped evidence from that stopped run, not an invariant about every
monitor or a random-destination distribution measurement.

The helper invokes the original `Roamer.step` once with the same inputs and
returns its result unchanged. The normal GUI timer, real monotonic clock and
default unseeded motion RNG remain active. Only the config path and observing
wrapper are replaced. Its `pre_native` values precede the adapter update, so
the report correctly uses settled later samples for the crop/frame claims.
The isolated functional configuration disabled greeting and lowered spike
sensitivity; the motion speed, cadence and cooldown defaults were preserved.
The source used for the traced GUI is `f61851d0…`, whose executable equivalence
to final `f3810b14…` was independently established above. The separate final
native fixture and unwrapped handoff use final `f3810b14…` directly.

The raw transitions match the report's two explicitly scoped observed trips:
random wander departed at `07:31:41.357616Z`, arrived at `07:31:48.406973Z`,
and naturally rested at `07:31:50.406958Z`; activity-triggered approach departed
at `07:33:18.353418Z`, arrived at `07:33:24.903566Z`, and rested at
`07:33:30.952605Z` (all 2026-09-09). Both stayed at the new destination, and
the approach began from the wander's arrival. The manual reference remained
`(252,248)` during these trips. The report's configuration snapshots preserve
`(x,y)=(118,98)` through the no-drag click and OFF/ON toggles, then change to
`(704,417)` on the explicitly recorded manual drag. This distinction matches
the requirement that automatic movement not persist positions.

The actual screenshot contact sheet contains full-window snapshots before and
after the trips; it supports those rest-state renderings and does not claim
continuous movement footage. The final native contact sheet separately shows
walking, arrival summary and idle/full restoration. The report clearly states
that this change did not repeat every settings interaction or the prior day's
actual OS Reduce Motion toggle. Their unchanged paths retain regression
coverage; those earlier UI runs are not mislabeled as new runs.

The Verifier's final handoff records traced PID10294 stopped, installed PID29528
preserved, and unwrapped normal development PID30313 started at
`2026-09-09T07:40:39.492846Z`, rendered at `07:40:46Z`. I read its recorded
stdin launcher: normal `run_gui` with the isolated config path and no tracing
wrapper. This is a development execution handoff, not installation or release
verification. I did not launch or manipulate those processes myself.

**Final decision: APPROVED**, signed by Codex `/root/reviewer` at 2026-09-09 07:45:30 UTC.
Production source remains
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`,
and the last rechecked tracked test-diff SHA remains
`156e27fecb77302bb4b0c13b64a7552d4c441eeb2a1540c531f0c19780379ff1`.
No unresolved correctness, test-discrimination or scope blocker was found for
the requested whole-monitor random roaming and removal of automatic return.
Production and gating tests were authored by their separate assigned owners;
my writes are confined to this review document. The observed baseline
failures, native harness correction and limitations remain preserved above.
This is development correctness approval. No commit, merge, build, signing,
release, installation or push was performed by me in reaching this decision.

## Recorded commit handoff metadata

After the Coordinator's merge-gate approval, I read the following completed
commits at `2026-09-09T07:49:10.713635Z`:

- `9f8ba130f8f7b19ea9d526034f407331069f7353` — the Verifier's tests and
  verification report, with Mendel as test author and Curie (`/root/reviewer`)
  as the independent baseline-RED reproducer in the required trailers.
- `147004de79dc1a42afd5218fc98daec8fddf8c80` — Claude's production and design/
  README documentation, with Claude as Developer, Mendel as Verifier and
  Curie as Reviewer. No gating test file is part of this production commit.

The committed source remains the approved
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.
The new design document's now-committed status removes the obsolete
`(미커밋)` marker; its final SHA256 is
`7948d75775d610fb6fc7e3d6188ba14a8fbbc2824b31e7c7724201239b01de15`.
That status-only update was separately approved and does not alter behavior
or quantitative evidence. The tracked tree and index were clean when read.
This metadata does not change the substantive review decision or represent
a release authorization. The review document itself will be committed only
after its final metadata is independently checked and the Coordinator gives
the separate named-path commit instruction.
