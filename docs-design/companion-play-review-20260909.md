# Timed cursor following and monitor jumps — independent review

Reviewer: Curie (`/root/reviewer`). Coordinator: `/root`. Developer: the
user-designated Claude agent. Verifier: Mendel (`/root/verifier`). This is a new
change, following the completed free-roaming/no-return change.

Status: **APPROVED — final source `150f5775…`, documentation, independently authored gates and recorded execution evidence. Actual OS/hardware multi-monitor transit remains unverified on this single-display machine.**

The sole writable Reviewer deliverable is this document. Its absence was
confirmed at `2026-09-09T08:00:11.196823Z`, before creation. Source and tests are
read-only for me; GUI operation belongs to the Verifier. Earlier untracked QA,
review and release artifacts are outside this assignment. No product/test edit,
GUI action, launch or release action has been performed by me for this change.
Any documentation commit is limited to this named deliverable after explicit GO.

Baseline source SHA256:
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.
Baseline HEAD: `dba49ef6fe66f16a6a63d5f981f76a0fd0121448`. The tracked tree was
clean at the initial inspection.

## User request and proposed scope

The user asks for randomly occurring cursor-following episodes lasting at
least ten seconds, plus autonomous movement between monitors, accepting a
jump as the transition. The Coordinator proposes episodes of 10–20 seconds,
quiet cooldowns and folded walking, with an explicit departure/landing jump
effect and safe placement on another monitor. The Developer API is pending;
the numerical intervals below are stipulated candidate contracts, not empirical
frequency or responsiveness claims.

The previous behavior remains the baseline: random whole-monitor wandering,
occasional fixed-target approach, safe cursor clearance, user interruption,
no automatic return and no automatic coordinate persistence.

## Independent correctness risks

- **A follow episode needs an immutable end time.** Sample duration once at
  entry. Refreshing the destination must not reset that deadline, or continuous
  cursor activity can produce indefinite following. Reaching the latest target
  should wait/retrack during the same episode rather than naturally finish
  before the minimum duration. User hold, Reduce Motion, invalid geometry or a
  long callback gap may cancel earlier; cancellation is not natural expiry.
- **Follow and fixed approach have different targeting contracts.** Follow
  refreshes its target at the agreed cadence; the existing approach should
  continue to use its departure target. Do not accidentally convert every
  activity into continuous pursuit, or make the new follow another one-shot
  approach. Close-pointer behavior should stop safely, not flee through the
  pointer or step past the safe target.
- **Interrupted work must not resume stale follow/jump state.** Clear the
  episode/transfer target and restore quiet rest. The normal delay after user
  interaction still applies. Natural completion rests at the current arrival;
  automatic activity must not reset or persist the manual placement reference.
- **Choose an individual eligible screen, never the union bounding box.**
  Monitor gaps and negative origins make a union rectangle unsafe. Exclude the
  current screen and screens that cannot contain the logical full window.
  No eligible destination must produce ordinary rest, not a forced self-jump.
- **Validate a jump destination at transfer time.** A screen selected before
  the visual departure may disappear, move or shrink before landing. Retain
  identity rather than relying on list order, and recompute full-window-safe
  bounds before the native move. Interruption must leave the pet on a real
  source/target screen, not abandon an interpolated position in a gap. Recovery
  if the source itself disappears must use valid remaining-screen geometry.
- **Keep target-screen geometry through the adapter.** An old-screen clamp,
  home-based resync, or stale `win.screen()` assumption can undo a valid jump.
  The actual crop must be placed from the destination logical full center;
  opening the full panel must remain safe there. Orientation changes must not
  create an unintended extra sprite jump beyond the intended monitor transfer.
- **Make the jump's visual contract observable.** Existing `set_override`
  restarts frames only when the animation name changes, and `roam_tick` updates
  the override only when `out.anim` changes. Two consecutive `jumping` strings
  do not independently restart departure and landing. If two separate effects
  are promised, phase/restart information must distinguish them; if one
  continuous animation is intended, document and test that instead. Owned jump
  overrides must clear after completion/cancellation and must not suppress
  themselves as an unrelated animation.
- **Keep explicit transfer distinct from ordinary walking.** A monitor jump
  can intentionally exceed a walking tick's distance. Exempt only its explicit
  transfer event, while retaining speed, cursor and bounds checks for follow
  and ordinary out phases. Define the response to a cursor moving to another
  monitor during follow; it must not become unbounded straight-line walking
  across screen gaps.

## Independent monitor-geometry oracle

These are exact stipulated inputs derived before any new gating expected
values were read. Coordinates are global AppKit points, y upward. The logical
full window is `W=300,H=220`; its circumradius is
`sqrt(150²+110²)=186.01075237738274`.

| Screen | Visible frame `(x,y,w,h)` | Allowed full-window center rectangle |
| --- | --- | --- |
| A, current | `(-1600,80,1440,900)` | `(-1450,190,-310,870)` |
| B, target | `(240,-200,1920,1080)` | `(390,-90,2010,770)` |

The horizontal gap is `-160 < x < 240`. Given target screen B and independent
normalized draws `(u,v)=(0.45,0.2)`, safe-center sampling gives:

```text
x = 390 + .45 × (2010 − 390) = 1119
y = −90 + .2 × (770 − (−90)) = 82
logical center = (1119,82)
full-window origin = (1119 − 150,82 − 110) = (969,−28)
```

| Rival | Result for the same draws |
| --- | --- |
| Correct B safe-center sampling | `(1119,82)` |
| Sample union of allowed-center rectangles | `(107,102)`, in the gap |
| Reuse source A bounds | `(-937,326)` |
| Ignore B's nonzero screen origin | `(879,282)` |
| Sample raw B visible frame, then clamp | `(1104,16)` |
| Clamp the correct landing against old A bounds | `(-310,190)` |

For source center `(-880,530)`, the straight-line midpoint toward the correct
landing is `(119.5,306)`, also in the gap. It discriminates a transfer that is
cancelled halfway through an ordinary interpolated walk. The exact transfer
timing/animation may depend on the eventual API, but interruption cannot leave
the pet parked at this midpoint.

Crop placement still follows the established logical-to-native mapping: for
logical center `(X,Y)` and flipped logical crop `(cx,cy,cw,ch)`, native origin
is `(X−W/2+cx, Y+H/2−cy−ch)`. Crop width/height do not replace logical W/H when
choosing safe monitor bounds or preserving the global sprite anchor.

## Independent follow/deadline oracle

These inputs use the preserved candidate speed of 55 points/second and assume
a target refresh has become eligible under the eventual cadence contract;
they do not dictate a per-frame refresh cadence before the API is agreed.

Let radius be 50 and cursor stand-off be `150+50=200`. From position `(400,300)`
toward cursor `(1000,300)`, a refreshed target is `(800,300)`. One 0.25-second
walking step is `55×.25=13.75`, giving `(413.75,300)`. At the next permitted
refresh, put the cursor at `(413.75,1000)`. The target becomes `(413.75,800)`;
the next 0.25-second step goes to `(413.75,313.75)`. Keeping the old target
instead gives `(427.5,300)`, clearly distinct. Existing cursor clearance and
remaining-segment safety must still hold for either orientation.

For an episode starting at monotonic `100`, duration draw `.3` over `[10,20]`
means duration `13` and deadline `113`. A destination refresh at `108` must
leave that deadline unchanged, rather than making it `121` by adding the same
duration again. The episode should not naturally expire before its deadline
merely because its current destination was reached. Suppression/gap cancellation
is a separate cause and must discard the episode rather than resume its
remaining duration afterward.

## Evidence boundary

The Verifier reports one currently available native screen. Until that changes,
screen-pair/gap/disconnection behavior must be verified with independently
constructed multi-screen geometry and adapter fixtures. A real one-screen GUI
run can establish the fallback and visual/timing behavior it actually executes;
it cannot be described as an observed physical cross-monitor jump. The exact
native inventory and runtime results belong to the Verifier's new evidence
record. Final API review, observed baseline RED, implementation diff, test
discrimination review and frozen-source/runtime sign-off remain pending.

## Review of the initial Developer API proposal

I read `docs-design/companion-play-20260909.md` in its READ/PROPOSE state.
**API approval is pending the following bounded corrections.** These are
design findings, not claims that an implementation bug has been executed.

1. **Represent real screen identity and geometry.** Passing only other-screen
   safe-center rectangles and expanding each by the window circumradius cannot
   classify which monitor contains the cursor. For the stipulated B screen
   above (take its physical frame's x range to be the same `240..2160` as its
   visible frame), expanding its safe rectangle by `186.010752…` starts at
   x `203.989247…`. Cursor `(220,0)` is then incorrectly classified as B,
   although it is in the physical gap. Pass screen records with a stable ID,
   actual physical frame and full-window-safe bounds, including the current
   screen. Candidate filtering and actual cursor-screen membership are
   separate operations. Current-screen exclusion must use the record identity.
2. **Make the landing screen authoritative for bounds.** Resolve post-transfer
   R8 against the confirmed target screen, using the latest screen inventory,
   rather than depending on an immediate `win.screen()` update. The numeric
   oracle already distinguishes correct landing `(1119,82)` from an old A
   clamp `(-310,190)`. Screen disappearance/movement/resizing and the newest
   cursor clearance must be checked immediately before the atomic transfer.
   A cursor moving to the selected landing during the 0.75-second departure
   does not trigger hover on the still-distant source window.
3. **Apply the episode deadline inside jump as well as follow.** It remains
   the original deadline throughout the cross-screen jump. Expiry before
   transfer finishes the episode at the source; expiry after transfer must not
   re-enter following at the destination. An empty/cleared `_jump_next` must
   not fall through to a follow branch with missing target/state. Specify
   whether any already-started landing fade completes visually while tracking
   remains stopped; that must not renew the episode.
4. **Separate missing/invalid cursor from natural early completion.** The
   proposal's cursor-None natural-completion branch can finish before ten
   seconds. Treat it as explicit cancellation (`settled=False`) or a bounded
   safe wait under the same deadline. A cursor in the monitor gap cannot
   accumulate a cross-screen dwell or trigger a jump. The dwell timer belongs
   to a specific target screen ID, so B→C changes reset it; once the jump has
   begun, its chosen target stays fixed.
5. **Do not make startup behavior preserve old test RNG calls.** The proposed
   initial seven/ten-minute blackout exists to keep old fixtures unchanged.
   The Coordinator instead chose initial eligibility at creation time, with
   the normal first rest still applying and cooldowns starting at actual
   episode/jump entry. Existing approach/wander-only fixtures should explicitly
   disable the new optional selection paths. This isolates their subject
   without changing the product's initial user experience.

The proposed jump effect is one `jumping` departure with fade-out, followed by
`anim=None` and fade-in for landing. This does not promise two separately
restarted `jumping` animations, so the earlier same-animation restart concern
does not require an additional restart field under this contract. Alpha must
still restore to 1 on the first cancellation/completion tick; a check only
inside nonempty effects would strand a faded window.

The proposed follow speed is **45**, rather than the earlier provisional 55.
The first-principles orthogonal-refresh oracle therefore becomes:

```text
first target: (800,300)
stride = 45 × .25 = 11.25
first position: (411.25,300)
next eligible cursor refresh: (411.25,1000)
new target: (411.25,800)
next position: (411.25,311.25)
fixed-old-target rival: (422.5,300)
```

The proposal's assertion that cursor distance is always at least
`stop−slack` is not a possible invariant under externally controlled cursor
input. If the pet is at `(400,300)` and the user moves the cursor to `(405,300)`,
distance is 5 and the correct response is to stop safely. It should neither
flee nor teleport to manufacture the asserted distance. The correct movement
contract prohibits the pet from newly stepping into the cursor exclusion
region and requires no movement when the cursor already intrudes.

A distinct deadline/transfer boundary fixture is also available: episode
start `100`, sampled duration `13`, deadline `113`; cursor-screen B dwell
begins at `105`, so a jump may start at `108` after the stipulated three-second
dwell with five seconds remaining. Give the next callback at `113`. Its gap
is exactly 5 and therefore does not hit the existing `gap > 5` cancellation,
but its episode deadline has arrived. Correct behavior finishes at the source
without transfer; a branch that only checks the expired departure animation
will incorrectly move to the target. These values were derived from the
proposed rules and shared with the independent Verifier before reading new
gating assertions.

## API v2 structural approval

**APPROVED for implementation after independent RED**, at the API checkpoint
read on `2026-09-09T08:17:15.508659Z`. The proposal document SHA256 is
`fa29cbe03aa3c5935835134ee7948b4f168b5252149b79f3b9e45a0599ec6690`;
production remains the unchanged baseline `f3810b14…` above.

The revised `RoamScreen(id,frame,bounds)` inventory includes the current screen
and separates physical cursor membership from full-window center safety. The
model's confirmed current screen governs post-transfer bounds, avoiding the
old-screen clamp. Screen identity, newest landing bounds and cursor exclusion
are rechecked before transfer. Follow preserves its original deadline during
jump, explicit missing-cursor cancellation, gap waiting and per-screen dwell
are defined, and cancellation/completion restores alpha. Initial eligibility
now follows ordinary rest, with cooldowns counted from actual starts.

The chosen safety thresholds are intentionally distinct: landing candidates
are planned with `approach_stop + radius` stand-off; transfer-time validation
requires the latest cursor to be outside `radius + cursor_margin_px`. The
latter prevents footprint intrusion if the cursor moves closer during takeoff,
without claiming the original preferred stand-off remains invariant under
external cursor movement.

No structural conflict with the agreed user requirements remains in v2. The
implementation review will check the stated edge semantics—including no RNG
draw when `follow_p=0`, meaningful single-screen behavior for `screens=()`,
missing-cursor cancellation throughout a follow-owned jump, and clearing all
pending episode/transfer state—against actual code. These are implementation
checks of the contract, not additional requested API/features. Independent
baseline RED, frozen-source correctness and native/real-time evidence are
still required before final sign-off.

## Independent baseline RED replay

Curie independently executed Mendel's new gates against the immutable source
from `git show dba49ef6fe66f16a6a63d5f981f76a0fd0121448:claude_pet.py`.
The source was loaded in memory; the working-tree product, test files and GUI
were not modified. Both replay runs used Python `-B` and the helper
`tests/test_companion_motion.py`, SHA256
`ff04e8828b651d4cc4082b77ef0f4a2a749725ab5e6a9655066d29a8e50a022e`.
The source SHA256 in the baseline bytes and the working tree immediately
before and after each run was
`f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`.

The counted unit is a discovered unittest case; failure outcomes additionally
include failing subtests, so they are not a count of distinct cases. All input
files are precisely the Git source object above and the two test paths named
here. Absolute run bounds are also the measurement timestamps; test clocks
such as `100`, `113`, `520` and `700` are synthetic monotonic inputs, not UTC.

| Selection | UTC start | UTC end | Cases run | Failure outcomes | Errors | Skips |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `TimedFollowTests` | 2026-09-09T08:21:58.532397Z | 2026-09-09T08:21:58.941512Z | 10 | 14 | 0 | 0 |
| Complete `test_companion_play` module | 2026-09-09T08:25:18.259900Z | 2026-09-09T08:25:19.815072Z | 26 | 34 | 4 | 0 |

The first run read `tests/test_companion_play.py` SHA256
`159daa75d5f1612a3d599d7a053f0f39b65d6edd28bc9d84db6083b50517cf8d`.
The complete-module run read its later SHA256
`da033fedfc6bff7ce2e4a301e60008694917776a7de1ff3ba82a2f3f83729bac`.
The Verifier was still completing the jump cases between these two snapshots.
These hashes identify the exact captured test bytes; no claim is made that
the snapshots are identical.

### Reproduction command

Executed from `/Users/yeongyu/claude-pet`; the first run uses
`loadTestsFromTestCase(tests.TimedFollowTests)` in place of the module loader.
This command reads the test bytes once before compiling them, so subsequent
edits cannot alter the cases during that run. Its Git-backed `SOURCE` adapter
changes the helper's input in memory and does not replace any source file.

```sh
python3 -B - <<'PY'
import datetime,hashlib,io,pathlib,subprocess,sys,types,unittest
root=pathlib.Path.cwd(); sha=lambda b:hashlib.sha256(b).hexdigest()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
base=subprocess.check_output(['git','show','dba49ef6fe66f16a6a63d5f981f76a0fd0121448:claude_pet.py'])
helper_path=root/'tests/test_companion_motion.py'; test_path=root/'tests/test_companion_play.py'
hb=helper_path.read_bytes(); tb=test_path.read_bytes()
before=sha((root/'claude_pet.py').read_bytes())
helper=types.ModuleType('test_companion_motion'); helper.__file__=str(helper_path)
sys.modules[helper.__name__]=helper
exec(compile(hb,str(helper_path),'exec'),helper.__dict__)
class HeadSource:
 def read_text(self,encoding='utf-8'):return base.decode(encoding)
 def __str__(self):return 'git:dba49ef6fe66f16a6a63d5f981f76a0fd0121448:claude_pet.py'
helper.SOURCE=HeadSource()
tests=types.ModuleType('test_companion_play'); tests.__file__=str(test_path)
exec(compile(tb,str(test_path),'exec'),tests.__dict__)
suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
print('START_UTC',start);print('END_UTC',datetime.datetime.now(datetime.timezone.utc).isoformat())
print('BASE_SOURCE_SHA256',sha(base));print('HELPER_SHA256',sha(hb));print('PLAY_TEST_SHA256',sha(tb))
print('WORKTREE_SOURCE_BEFORE',before);print('WORKTREE_SOURCE_AFTER',sha((root/'claude_pet.py').read_bytes()))
print('CASES',result.testsRun,'FAILURE_OUTCOMES',len(result.failures),'ERRORS',len(result.errors),'SKIPS',len(result.skipped))
print(stream.getvalue())
PY
```

### Actual assertion excerpts and limits

The following are excerpts from the actual output, not reconstructed predicted
failures. Repeated diff explanations and traceback frames are omitted.

```text
test_follow_uses_its_own_speed_and_capped_elapsed_time:
AssertionError: Tuples differ: (413.75, 300.0) != (411.25, 300.0)
 : follow did not use 45pt/s for the first quarter-second

test_follow_retargets_upward_instead_of_retaining_horizontal_target:
AssertionError: Tuples differ: (13.75, 0.0) != (0.0, 11.25)
+ (0.0, 11.25) : latest vertical cursor movement did not replace the old horizontal target

test_follow_cooldown_does_not_starve_first_episode_or_allow_repeated_bursts:
AssertionError: Lists differ: [] != [100.0, 520.0]
+ [100.0, 520.0] : follow eligibility or its 420-second cooldown is incorrect

test_missing_cursor_cancels_in_place_without_claiming_natural_completion:
AssertionError: Tuples differ: (427.5, 300.0) != (413.75, 300.0)
 : missing cursor continued an obsolete follow target

test_jump_lands_on_target_rectangle_not_union_source_or_old_screen_clamp:
AssertionError: Tuples differ: (-915.4263045798762, 508.86852007516165) != (1119.0, 82.0)
+ (1119.0, 82.0) : monitor jump did not use the independently derived target-screen destination

test_jump_cooldown_starts_after_first_eligible_jump:
AssertionError: Lists differ: [] != [100.0, 700.0]
+ [100.0, 700.0] : jump initial eligibility or 600-second cooldown is incorrect

test_missing_or_shrunk_target_cancels_before_transfer (removed and shrunken):
AssertionError: Tuples differ: (-903.6175363865841, 515.9123467167744) != (-880.0, 530.0)
+ (-880.0, 530.0) : jump used an obsolete target screen/rectangle

test_effect_field_is_appended_with_legacy_five_argument_default:
AssertionError: Tuples differ: ('pos', 'anim', 'moved', 'away', 'phase') != ('pos', 'anim', 'moved', 'away', 'phase', 'effect')

test_screen_descriptor_keeps_identity_physical_frame_and_safe_bounds_distinct:
AssertionError: {'RoamScreen'} is not false : quiet companion API missing: RoamScreen

test_follow_travel_folds_and_completion_look_gets_summary (preference=False):
AssertionError: 'folded' != 'summary'

test_follow_travel_folds_and_completion_look_gets_summary (preference=True):
AssertionError: 'full' != 'folded'

Ran 10 tests in 0.365s
FAILED (failures=14)

Ran 26 tests in 1.506s
FAILED (failures=34, errors=4)
```

Four complete-module errors are the four pre-transfer user-hold subtests
reaching `self.assertIsNone(out.effect)` at test line 329:

```text
AttributeError: 'RoamOut' object has no attribute 'effect'
```

They demonstrate the absent API, not a numeric cancellation defect. Likewise,
the five `FollowAcrossScreensTests` cases fail at an expected follow/jump
phase before their intended cross-screen deadline/dwell branch. For example,
both deadline fixtures stop in `prepare_deadline_jump` at
`AssertionError: 'rest' != 'jump'`; the dwell case reports
`AssertionError: 'look' != 'follow'`. The follow hold fixtures also fail their
entry precondition (`'out' != 'follow'`) before testing cancellation. These
baseline runs establish that the unfixed source fails the new contract;
they do not by themselves prove that every rival implementation of a future
follow/jump branch is rejected. Rival-specific checks remain the Verifier's
later responsibility.

The existing-behavior control
`test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws`
passed on the baseline. It is deliberately not claimed as red-before-green
evidence for the added behavior.

Curie reported these independently reproduced results to the Coordinator and
Mendel before implementation review. This supplies the test-only commit's
non-author baseline-failure confirmation for the snapshots identified above;
final test-diff approval and GREEN remain pending.

The design document's ownership table still said `tests/` in full at this
checkpoint. The Coordinator confirmed that the actual assignment is limited
to named test paths and named QA artifacts, and reported a correction request
to Claude with implementation GO at `2026-09-09T08:25:30Z`. Final documentation
review will verify the corrected scope; this note grants no additional file
ownership.

### Four additional gates: independent old-source replay

At `2026-09-09T08:38:15.074904Z`–`2026-09-09T08:38:15.437792Z`, Curie
replayed the four subsequently added cases with the same Git-backed memory
loader above. The baseline source remained `f3810b14…`; working-tree source
SHA256 before and after the read-only replay was the Developer's frozen
`0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c`.
The enumerated input files were the Git source object above,
`tests/test_companion_motion.py` SHA256
`d7f500f4616dd583f13e9e52c45744b0756497f05513e3ea2d8ebdd520edd0f5`, and
`tests/test_companion_play.py` SHA256
`188761820e2c83de03788aa881cce094b41c736fe92e883ff29b2def07de5ecc`.
Selection was `unittest.defaultTestLoader.loadTestsFromNames(names, t)` with
these exact names (the captured module is `t`):

```python
names = [
 'PlayApiTests.test_production_cadence_duration_and_jump_defaults_match_agreed_contract',
 'MonitorJumpTests.test_jump_probability_has_both_branches_at_the_default_threshold',
 'MonitorJumpTests.test_manual_placement_uses_physical_target_screen_and_ignores_legacy_source_bounds',
 'FollowAcrossScreensTests.test_cursor_none_cancels_follow_in_both_jump_stages',
]
```

Actual output was **4 cases, 5 failing outcomes, 0 errors, 0 skips**. Actual
assertion excerpts, preserving the runner's own abbreviated dictionary diff:

```text
defaults:
AssertionError: {'follow_p': None, 'follow_min_s': None, 'follow_max_s[254 chars]None} != {'follow_p': 0.35, 'follow_min_s': 10.0, 'follow_max_s[246 chars]': 6}
Diff is 1402 characters long. Set self.maxDiff to None to see it.

jump probability (choice=0.499):
AssertionError: 'out' != 'jump'

manual placement:
AssertionError: Tuples differ: (-310.0, 190.0) != (1119.0, 82.0)
+ (1119.0, 82.0) : new manual screen was clamped back to legacy A

cursor None (transferred=False and transferred=True):
  File "/Users/yeongyu/claude-pet/tests/test_companion_play.py", line 419, in prepare_deadline_jump
    self.assertEqual(out.phase, "jump")
AssertionError: 'rest' != 'jump'

Ran 4 tests in 0.324s
FAILED (failures=5)
```

The cursor-None pair again failed the jump-entry precondition, not the later
cancellation branch. The manual-placement result independently matches the
old-screen-clamp rival derived before reading these assertions. Probability
choices `.5` and `.9` remained ordinary-wander control outcomes on baseline.

## First frozen-source review checkpoint

Reviewed source SHA256
`0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c`
against baseline `f3810b14…`. The follow deadline is fixed at entry and tested
through both jump stages; latest cursor input replaces the walking target;
transfer confirms the selected screen ID and latest target bounds/clearance.
Post-transfer R8 uses the model's screen. Display modes include follow/jump,
and the adapter calls effect handling on every result so cancellation restores
opacity. These are source facts, not actual multi-monitor runtime evidence.

One bounded contract mismatch was proposed to the Coordinator and independent
Verifier; source sign-off was held for its disposition. API v2 says the model
also ignores screens whose safe bounds are inverted. The adapter does filter
them, but the frozen model passes its raw `screens` tuple to `_resolve_screen`
and `_plan`, so a caller of the pure API can select an impossible screen.

Curie's first reproduction ran at
`2026-09-09T08:38:40.002378Z`–`2026-09-09T08:38:40.032231Z`, reading only
the frozen source and `tests/test_companion_motion.py` via `pure_api`. The
source hash was `0c2c53ba…` at both bounds. Inputs were A frame
`(0,0,1000,800)`, bounds `(150,110,850,690)`; tiny frame
`(1200,0,1250,100)`, bounds `(1350,110,1100,-10)`; starting center
`(400,300)`, `now=0`, radius `hypot(150,110)`, `rest_min_s=rest_max_s=0`,
`follow_p=0`, `jump_p=1`, and an RNG that returns each uniform lower bound.
The two actual pure calls and outputs were:

```text
step(0, None, A.bounds, screens=(A,tiny)):
RoamOut(pos=(400.0, 300.0), anim='jumping', moved=False, away=False, phase='jump', effect='takeoff')
pending target: tiny (1100.0, -10.0)

step(.75, None, A.bounds, screens=(A,tiny)):
RoamOut(pos=(400.0, 300.0), anim=None, moved=False, away=False, phase='rest', effect=None)
```

The specified behavior excludes tiny and plans local wandering, without
spending a jump on it. This finding is explicitly limited to the pure API
contract: the shipping GUI's existing screen filter prevents this particular
input. It remains a **proposed mismatch pending non-author reproduction** at
this checkpoint, not a claim of observed real-screen failure.

Read-only review of the Verifier's launch helpers found the advertised scopes
consistent with their calls: `run_native_play` uses a real AppKit window/view
and production adapter but synthetic screen inventory/time/cursor;
`/tmp/claudepet-companion-play-20260909-qa.py` keeps original event-loop,
monotonic timing and step output while changing selection probability only
(`follow_p=1`) and supplying explicit synthetic usage. It suppresses the
usage/OAuth/cost/update/seed/discovery inputs identified in the helper. Its
`pre_native` sample precedes the model call and must not be interpreted as
the native frame after the same row's output position. The live audit hook
is installed after module import, so its guarded-execution scope must not be
misrepresented as an audit of every process action since startup. No GUI
input or launch was performed by the Reviewer.

### Invalid-screen finding established and fixed

The Verifier independently reproduced the proposed mismatch with a different
tiny-screen fixture: frame `(1800,-50,1900,40)` and safe bounds
`(1950,60,1750,-70)`, on `0c2c53ba…`, from
`2026-09-09T08:40:18.153520Z` through `2026-09-09T08:40:18.273459Z`.
Curie read the original command and assertion in
[the verification record](companion-play-verification-20260909.md), under
“Established invalid-screen regression RED”:

```text
test_inverted_destination_bounds_are_excluded_before_jump_selection ... FAIL
AssertionError: 'jump' != 'out'
 : invalid monitor consumed a jump and began takeoff
Ran 1 test in 0.061s
FAILED (failures=1)
```

This supplies the non-author reproduction required to establish the finding.
Claude then added `_roam_valid_rect`, filtered `screens` at the start of
`step`, and documented that filter. Final source SHA256 is
`24c9bfbfdac39e6b3af01e3fc89517c1f441116538bce96eb075c53483b2e1dc`.
Curie checked the change against the already reviewed frozen source: removing
that exact helper, restoring the prior tuple-conversion line and its adjacent
comments, and restoring the prior `step` docstring **in memory only** produces
exactly SHA256 `0c2c53bac0dc60ba42f4c3a8dd01840a2a9b01936683bbfa31163f011e1cbb9c`.
This verifies the stated limited patch rather than relying on an author claim.

Curie replayed the original A/tiny fixture above, with all inputs unchanged,
at `2026-09-09T08:43:50.181921Z`–`2026-09-09T08:43:50.216562Z`.
The source hash before and after was `24c9bfbf…`. Actual output:

```text
FIRST RoamOut(pos=(400.0, 300.0), anim='running-left', moved=False, away=False, phase='out', effect=None)
PENDING None None
TRANSFER_TIME RoamOut(pos=(389.05276983080734, 291.6801050714136), anim='running-left', moved=True, away=True, phase='out', effect=None)
```

The explicit assertion `out.phase == 'out' and r.kind == 'wander' and
r._jump_screen is None` passed. It plans local wandering and neither begins
nor spends a jump on the invalid screen. **Source correctness and scope are
APPROVED for `24c9bfbf…`.** The focused/full suite and runtime evidence remain
separate gates; this approval is not a release, installation or publication.

### Complete 31-case baseline replay

For the final test-only trailer, Curie also replayed the complete new module
using the Git-backed memory command already recorded. Run bounds:
`2026-09-09T08:45:53.165432Z`–`2026-09-09T08:45:55.558728Z`.
Files actually read: baseline Git `claude_pet.py` object (`f3810b14…`),
`tests/test_companion_motion.py` SHA256
`d7f500f4616dd583f13e9e52c45744b0756497f05513e3ea2d8ebdd520edd0f5`, and
`tests/test_companion_play.py` SHA256
`f4332ab5c5dadd8bc76a19d988bbb9b610c0fba1b4ce971272c3e2803f145113`.
Working-tree source remained `24c9bfbf…` at both bounds. Actual result:

```text
CASES 31 FAIL 39 ERROR 5 SKIP 0
Ran 31 tests in 2.351s
FAILED (failures=39, errors=5)
```

The failure assertions match the previously recorded baseline outputs,
including `(-310.0,190.0) != (1119.0,82.0)` for manual placement and
`(-915.4263045798762,508.86852007516165) != (1119.0,82.0)` for the chosen
jump landing. There is still one baseline-passing control case:
`test_single_screen_and_jump_off_use_local_wander_without_jump_selection_draws`.
The fifth error is the new inverted-destination case reaching an absent
`RoamOut.effect` field on the old baseline:

```text
test_companion_play.MonitorJumpTests.test_inverted_destination_bounds_are_excluded_before_jump_selection
AttributeError: 'RoamOut' object has no attribute 'effect'
```

Its local-wander behavior is already correct on the pre-feature baseline.
The meaningful RED for that newly introduced regression is therefore the
separate `0c2c53ba…` assertion `'jump' != 'out'`, established and fixed above.
Neither API errors nor earlier phase-entry failures are presented as a
substitute for rival-specific discrimination. Counts here use cases and
failure/error outcomes separately, not a synthetic “failure percentage.”

Review of the existing test diff found explicit `follow_p=0` and
`jump_enabled=False` fixture isolation, the appended `effect` API assertion,
and fake-screen fields/scope required by the new adapter inventory. Existing
motion safety, suppression, geometry, summary and save assertions were not
weakened. Final pin values and any subsequent verifier-owned additions will
be checked against the frozen source before the final sign-off.

### Final source and documentation approval

Final source SHA256:
`150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351`.
The only change after the approved `24c9bfbf…` version is the `_plan`
docstring's explanation of random-number draws. At
`2026-09-09T08:49:47.378204Z`–`2026-09-09T08:49:47.379043Z`, Curie
substituted the previously read docstring in memory and hashed the result:

```text
SOURCE_SHA 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351
INVERSE_DOCSTRING_SHA 24c9bfbfdac39e6b3af01e3fc89517c1f441116538bce96eb075c53483b2e1dc
```

The exact match establishes that executable statements were unchanged.
**Source approval carries forward to `150f5775…`.** The docstring now
distinguishes new-action selection from existing rest resampling, and
correctly distinguishes `follow_p=0`, `jump_enabled=False` and `jump_p=0`.

The Developer's final Markdown changes were read against the actual source.
README behavior/toggle descriptions, fixed follow deadline, current-screen
resolution, latest landing safety, folded/summary/full restoration and the
single-screen live-test limitation match the implementation and agreed scope.
The ownership table names the assigned test files instead of all `tests/`.
The stale diff-size claim was removed; `roam_resync`'s changed bounds source,
rest/hold random resampling, zero-probability behavior and invalid-screen
fallback are described correctly. **Documentation is APPROVED** at these
hashes, measured in the same inspection interval above:

| File | SHA256 |
| --- | --- |
| `README.md` | `04b14d28cddd0e07d25f02df6b783f62573ebf591a8655b35f89d6e817b15376` |
| `README.ko.md` | `abcc59ca35ca42808b82bee616fd18780addcf5c2918b7c300b0d692bd72d9fd` |
| `README.ja.md` | `69a5751a19a4135b572c3549135020b80dbcbf12e6bb9321fe2c394e11184e29` |
| `README.es.md` | `b48095478c4d184485f02630a2a331174e5a64670a43977ecf15fcff53480404` |
| `docs-design/quiet-companion.md` | `d78c5df968a1e9289da06982c84dc772a992d3c30747d293fb8d16aa71d6aea9` |
| `docs-design/companion-play-20260909.md` | `cf0afc7118d3d7707f20f705fa1487cb4c1ef31d343c127b272509f67d2a23f3` |

The two reviewed-source pins in `tests/test_manual_update_transaction.py`
and `tests/test_upload_artifact_gate.py` were read and both name `150f5775…`.
Their diffs change that hash literal alone; neither test semantics nor other
artifact pins were relaxed. The tracked test diff, defined precisely as
`git diff -- tests/test_companion_motion.py tests/test_free_roaming.py
tests/test_manual_update_transaction.py tests/test_upload_artifact_gate.py`,
had SHA256
`a333866973829f1e10822eec0cc2e1c930b52510bddc587fd0c7ec7316cb457c`
at the inspection above. The new untracked test module is separately hashed
in the baseline replay record and will be rechecked after Verifier completion.

The native/live contact sheets were also inspected. They show the documented
folded movement, summary transition and restored full gauge. A cached NSView
image is not proof of the enclosing NSWindow's composited alpha; fade
verification belongs to the native alpha values, separately from image
inspection. The actual-usage rows are explicitly QA fixtures. Actual hardware
multi-monitor transit remains outside the available single-screen live
evidence. The final suite and completed runtime record are still pending at
this approval checkpoint.

## Final separating-fixture correction and independent confirmation

The Verifier's planned mutation checks found a non-discriminating case: the
original episode-cap test also passed when its maximum-jump condition was
removed. Its return cursor `(-450,600)` was too near screen A's right edge;
clamping the landing candidate violated cursor clearance and independently
prevented a second jump. The unfavorable mutant PASS is retained verbatim in
the verification record, under “Non-discriminating jump-cap fixture.”

Curie independently checked the geometry before the corrected fixture was
accepted, using the frozen `150f5775…` source, its pure helper and explicit
synthetic tick/cursor inputs, at
`2026-09-09T08:53:22.118064Z`–`2026-09-09T08:53:22.148812Z`. Source
positions were inputs to an independently computed formula
`C + (P-C)/|P-C| * (150 + hypot(150,110))`, then an explicit A-bounds clamp;
the implementation's `_standoff` was not used to calculate the oracle.

| Cursor | Position at synthetic t=108.25 | Raw candidate | Clamped candidate | Cursor distance |
| --- | --- | --- | --- | ---: |
| `(-450,600)` | `(687.23980997,237.30694902)` | `(-129.87541011,497.90459041)` | `(-310,497.90459041)` | `173.27282724` |
| `(-1200,600)` | `(692.25027599,242.85145862)` | `(-869.81893990,537.68071513)` | unchanged | `336.01075238` |

Clearance is `hypot(150,110)+24 = 210.01075238`; the corrected cursor clears
this unrelated guard. The Verifier changed the two post-landing cursor input
literals; the assertions remain intact. The corrected new test module SHA256
is `62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e`.

Curie then independently **executed** the corrected case against both the
cap-free rival and unchanged source, at
`2026-09-09T08:56:10.123773Z`–`2026-09-09T08:56:10.269203Z`.
Files read were `claude_pet.py` (`150f5775…` at both bounds), the corrected
test module above, and `tests/test_companion_motion.py` (`d7f500f4…`).
The same memory loader used above ran
`FollowAcrossScreensTests.test_follow_resumes_after_one_jump_but_never_restarts_duration_or_jumps_back`.
The rival was exactly one in-memory replacement of
`self._follow_jumps < int(self.cfg["follow_max_jumps"])` with `True`;
the replacement needle was checked to occur once. Actual output:

```text
VARIANT cap_removed CASES 1 FAIL 1 ERROR 0
AssertionError: 'jump' == 'jump' : a second jump began in the same follow episode
Ran 1 test in 0.053s
FAILED (failures=1)

VARIANT unchanged CASES 1 FAIL 0 ERROR 0
Ran 1 test in 0.051s
OK
```

This is independent confirmation of the corrected gate's discrimination, not
merely re-running its GREEN. No source, test or fixture file was edited by
Curie. It completes the test-only commit's non-author failure confirmation
for the final fixture as well as the earlier baseline snapshots.

## Final frozen evidence review and sign-off

Curie reviewed the final Verifier record, SHA256
`55a9cb066bafca660dee12aaa0be1884102edd95565e97484d4b50de0787147a`,
including its original test output, retained unsuccessful runs, native/live
scope and exact normal-launch code. Source remains `150f5775…`; the corrected
test module remains `62930be3…`; the tracked-test diff hash remains
`a3338669…` as specified above. `git diff --check` passed.

**Test evidence accepted.** The full suite ran on source `150f5775…` at both
ends, UTC `2026-09-09T08:49:46.346913Z`–`2026-09-09T08:55:14.446273Z`:
**485 discovered unittest cases, 478 PASS, 7 existing opt-in skips, no failures
or errors**. Its exact command and output are in “Final full suite on150f
source,” ending `Ran 485 tests in 327.916s` and `OK (skipped=7)`. The skips
are two installed-app preflight, two real-stapler and three old-installed-version
boundary cases. The interrupted earlier suite is not counted as a final gate.

The full suite loaded the prior `f4332ab5…` cursor fixture. The strengthened
**entire 31-case play module** separately passed on unchanged final source
during the Verifier's UTC `2026-09-09T08:54:41.336430Z`–
`2026-09-09T08:54:44.005246Z` mutation/GREEN run. In that same bounded run,
four explicitly enumerated in-memory rivals—jump-deadline removal, mixed
foreign-screen dwell, episode-cap removal and retained cancellation effect—
produced **12 failing assertion outcomes across four rivals, zero errors**
(respectively 2, 1, 1 and 8 outcomes). This distinction preserves which test
bytes each run actually executed; it does not claim the final fixture was
already present in the running full suite.

**Native and live evidence accepted within their stated scope.** Curie's
independent frozen-artifact check ran at
`2026-09-09T09:03:00.698852Z`–`2026-09-09T09:03:00.747517Z`.
The enumerated files actually read and hashed were `claude_pet.py`,
`tests/test_companion_play.py`, the final verification Markdown, and these
assigned QA artifacts:

| Artifact | SHA256 |
| --- | --- |
| `companion-play-live-20260909.jsonl` | `2bbcc33b4708de9da67beb9f7f918d31fc6ee04a47c3b7bdf8b633b06af7f235` |
| `companion-play-native-20260909.json` | `95e241b03a20e919623fabb717c87258b899b3b5fe4efc57a2d1383e28798c0b` |
| `companion-play-native-20260909.png` | `18d58913c88203fc0f1cd9d38c2cdcfc740e1d1f942966c16cc24c234b210b0b` |
| `companion-play-live-20260909.png` | `0e84f6c25125d2ad61b2c5dc20f550592c549c62c2e030537c814090fe8733a7` |

These artifact paths are all under `docs-design/`. The frozen JSONL parsed
strictly, contains **3,916 records**, and has **3,812 recorded step observations**
(sampled steps, not all timer callbacks). The grouped counts, absolute
observation bounds and out-of-supplied-safe-bounds numerators were independently
recomputed, matching the Verifier:

| PID / source | UTC first recorded step | UTC last recorded step | Outside / recorded steps |
| --- | --- | --- | ---: |
| 14581 / `0c2c53…` | 2026-09-09T08:38:26.696719Z | 2026-09-09T08:44:51.396847Z | 0 / 1391 |
| 27202 / `24c9bf…` | 2026-09-09T08:44:51.738029Z | 2026-09-09T08:50:08.886719Z | 0 / 796 |
| 39717 / `150f57…` | 2026-09-09T08:50:09.647553Z | 2026-09-09T08:55:24.899546Z | 0 / 1131 |
| 49689 / `150f57…` | 2026-09-09T08:55:25.482313Z | 2026-09-09T08:57:42.581991Z | 0 / 494 |

For each recorded model position, the check used that row's supplied screen
safe rectangles (or the legacy bounds if no inventory). These zero numerators
describe this frozen sample and do not establish a universal invariant. The
trace hash was identical before and after Curie's read.

The recorded natural follow on `0c2c53…` starts at
`08:40:17.346083Z`, changes to look at `08:40:33.695939Z`, and rests at
`08:40:39.745024Z` on 2026-09-09. The 64 recorded follow samples and endpoint
displacement `439.9343772438411pt` match Curie's recomputation. This was real
event-loop timing and actual cursor input with forced follow selection and
fabricated usage; valid screen records mean the subsequent invalid-screen
filter does not change this exercised path.

The accelerated native artifact uses actual NSWindow/PetView with synthetic
negative-origin screens, clock and cursor. Its 95 samples cover
`2026-09-09T08:44:34.288890Z`–`2026-09-09T08:44:34.581876Z` on `24c9bf…`;
the separately derived landing `(1117.4,79)` and maximum measured native/model
axis residual `0.40000000000009095pt` match the raw JSON. `24c9bf…` and final
`150f57…` differ only in the verified docstring change. The earlier failed
hover simulation was correctly retained as a fixture-input mistake: Ticker
overwrote the manually set hover flag from its cursor input. The corrected
fixture supplies the actual native-frame-relative cursor input instead.

The **real-clock** jump on final `150f57…` uses two synthetic partitions of
one physical display, keeping normal timers and original step outputs.
Its recorded transitions are takeoff `08:51:05.797646Z`, atomic transfer
`08:51:06.548016Z`, look `08:51:07.097774Z`, rest `08:51:09.098025Z`, all
on 2026-09-09. Curie recomputed this sequence from the trace. Target native
frame is recorded on the next step, not falsely attributed to the transfer
row's `pre_native`. Natural rest opacity `0.99941541245` is within the
adapter's `1e-3` update tolerance; it is not presented as exact 1. The late
screenshot observer that missed this jump remains an unsuccessful capture,
not a video. A separate actual-hover cancellation record preserves source
position, cancels the effect and restores native alpha 1.0.

Actual hover, menu OFF/ON, settings, and drag event records were read against
their embedded model/native observations and isolated config snapshots.
The drag record at `2026-09-09T08:48:56.586805Z` changes isolated x/y from
`220/200` to `252/319`, with manual home `(386,424)`; automatic motion and
preceding toggles preserve x/y. These are sampled GUI tests with explicit
synthetic usage, not measurements of user usage or default occurrence rates.
**Actual OS/hardware inter-monitor transit is still unverified because the
machine exposes only one actual display.** Synthetic geometry, native placement
and real-clock rendering do not remove that limitation.

The normal handoff launcher was read: it starts final source with the assigned
temporary config and calls ordinary `run_gui`, without synthetic usage,
screen/step wrappers, or probability/timing overrides. The Verifier records
normal PID 55054 starting at `2026-09-09T08:57:42.796370Z`, visible window
1819 and restored pointer/config settings. Curie's subsequent read-only
`ps -p 29528,55054,14581,27202,39717,49689,30313 -o pid=,command=` returned
only installed PID 29528 and normal Python PID 55054 among those named PIDs.
No Reviewer GUI operation or process mutation was used to confirm this.

**Final Reviewer sign-off: APPROVED.** Curie approves correctness, scope,
documentation, independent test evidence and the accurately bounded runtime
record for source `150f5775…` and test `62930be3…`. No blocking finding
remains. This is development/merge approval, with the actual multi-monitor
hardware-test limitation stated above; it is not release or installation
authorization. Production and gating-test ownership stayed separate. Curie's
only writable deliverable for this change is this review document, and its
eventual named-path documentation commit remains subject to Coordinator GO
and non-author verification of these recorded claims.
