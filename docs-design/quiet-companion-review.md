# Quiet companion movement — independent review

Current decision: **Reviewer PASS** on final source SHA256
`3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c`.
The final sign-off below supersedes the earlier checkpoint holds. Source,
automated verification, actual UI evidence, and normal-run handoff were reviewed
separately. This is development correctness approval, not release authorization.

Reviewer: Codex `/root/reviewer`. Developer: the user's designated Claude agent.
Coordinator: Codex `/root`. Verification is assigned to a separate agent.
My only assigned deliverable is this document; I do not edit production files,
tests, fixtures, or assertions. This document is a review record, not a test gate.

Review began at `2026-09-08T04:39:45Z`, against base commit
`45a03c41b1e2fd3403ce52958a58956e12546086`. Final development review approval is
recorded at the end of this document; earlier pending statuses below describe
the checkpoints at which they were written.

## Scope and independent expectations

The requested experience is gentle movement and occasional attention near the
user's activity. The available input is the mouse position already polled through
`NSEvent.mouseLocation`; the feature must not imply that it reads screen contents
or understands typing. Screen capture, accessibility inspection, key logging,
and new capture permissions are outside the scope.

These expectations were derived from the user's request and the existing source
before reading any new gating assertions:

- Movement must have a rest period; continued cursor activity must not turn into
  continuous pursuit or continuous replanning.
- Pointer proximity must consider the whole window, including the usage pill;
  checking only the sprite can still cover the user's click target.
- Hover, drag, an open settings panel, disabled movement, and conflicting
  interactions must stop automatic movement promptly.
- Screen containment must use each screen's actual visible bounds, including
  negative origins, and account for window size. A screen smaller than the window
  must result in a defined safe fallback rather than invalid clamp bounds.
- Delayed timers and waking from sleep must not create a large catch-up jump.
- Automatic movement must not overwrite the user's saved manual location or
  repeatedly write configuration.
- The visible sprite must move continuously across screen-center boundaries,
  including the transition from travel to watching and then rest.

These are product requirements and deterministic source checks, not measured
frequency claims. Numerical tuning constants in the eventual specification are
product choices; they do not establish that the movement feels unobtrusive.

## Architecture findings before implementation

The existing `PetView.petOnRight` and `PetView.petOnBottom` choose the layout from
the window's center relative to the screen center. `PetView.petOrigin` then changes
the sprite's position inside the window. Consequently, crossing the horizontal
threshold changes the sprite position by `W - PW - 12`; crossing the vertical
threshold changes it by `pill_h() + GAP - 2`. Those changes occur in addition to
the window's own translation. This follows directly from the two branches of
`petOrigin`; no data sampling is involved.

Locking the layout only during travel postpones that jump until arrival. A design
must either preserve layout throughout automatic travel, watching, and rest, or
preserve the sprite's screen anchor when changing layout and reconcile that with
screen containment. Checking only the window origin's speed does not test the
visible sprite's speed.

The existing `mouseUp_` persists the manual window origin. A new movement loop
should leave that ownership intact. The existing view accepts a first mouse event,
so a window that moves over a cursor can intercept the next click even if only a
transparent part of its content rectangle covers the pointer.

## Rival behaviours to discriminate

| Requirement | Plausible wrong behaviour | Required discriminating scenario |
| --- | --- | --- |
| Occasional attention | Chase every cursor update; reset cooldown on every tick | Sustained input through approach, arrival, rest, and the next eligibility boundary |
| Stable travel | Replace destination whenever the cursor moves | Move the cursor after travel begins and inspect both destination and next position |
| Cursor clearance | Use sprite distance only; check destination only | Put the pointer in the pill region; place an otherwise-clear destination across the pointer's path |
| Immediate pause | Check blockers only when selecting a destination | Enable each blocker during a journey |
| Continuous sprite | Freeze layout only in travel; never account for layout | Cross each center threshold and enter watching/rest with both sprite and window coordinates tracked |
| Screen bounds | Assume origin zero; clamp only origin; select nearest screen without size check | Negative-origin screen, window at an edge, and window wider/taller than available bounds |
| No catch-up teleport | Multiply full elapsed time by speed | Advance the clock by a sleep-sized interval during travel |
| Manual ownership | Persist every automatic origin; snap to a stale pre-drag target | Complete a manual drag during the journey, then resume eligibility and inspect saved origin |

## Initial review status

Pending the completed implementation, independent red/green evidence, and full
suite result. No merge, release, build, installation, signing, or publication was
performed by this Reviewer.

## Proposed API review

The Coordinator supplied the proposed `Roamer` API before implementation:
`Roamer(home, now, rng=None, cfg=None, radius=0)`,
`step(now, cursor, bounds, enabled=True, dragging=False, blocked=False,
busy=False, activity=False)`, `set_home(pos, now)`, and
`release(now, pos, moved)`. Proposed phases are rest, held, out, look, and home.
This section evaluates that proposal; it does not claim the final code behaves
this way.

The coordinate contract must say whether `pos` and `home` denote the window
origin, window center, or sprite center. A sprite radius and bounds reduced by
sprite size cannot establish full-window cursor clearance. The runtime must
provide the whole window's dimensions, or a conservative radius covering the
whole window relative to the chosen anchor. Clearance must apply to the path
segment as well as its endpoint, on both outgoing and returning journeys.

Disabled movement, hover, dragging, and an open menu/settings panel must freeze
the current position in every active phase. Walking or snapping home is still
automatic movement and fails that contract. Elapsed time during a pause must be
discarded; capping an individual step does not suffice if elapsed-time debt is
carried into successive ticks.

`release(..., moved=False)` must not change the saved manual home. Existing
`mouseUp_` saves the current window origin before checking `_moved`, so direct
reuse would persist an automatic away position after an ordinary click,
double-click, or pill toggle. A real manual drag may establish a new home and
must cancel the old destination and return route. This is a source-derived
integration risk, identified before the new assertions were reviewed.

The Coordinator's proposed tuning values are specification choices, not
empirical proof of quietness. Visual inspection remains necessary to assess the
experience; passing planner tests alone cannot establish that it feels gentle.

## Independently reproduced implementation issues

These are synthetic, deterministic reproductions. Their `now` values are
injected simulation seconds, not real-world timestamps. The only source file
read was `claude_pet.py`, captured once as immutable bytes for this invocation,
with SHA256
`18c4890ededf34d59085cb2ff6365bc8029282d9c5f4fbfda67a986bd8c965cb`.
Real invocation bounds were `2026-09-08T05:11:39.809737Z` through
`2026-09-08T05:11:39.836107Z`; the output was recorded at the latter timestamp.
No Claude transcripts, live user activity, configuration, or network data were
read. Grouping unit for the suppression result is one injected suppression flag:
early movement occurred for all flags tested, numerator `4`, denominator `4`.
This establishes those synthetic cases, not a real-user frequency.

**Long interaction shortens the fresh rest.** The Verifier proposed the issue;
this Reviewer independently reproduced it with different coordinates and timing.
With an eight-second rest, the first unblocked tick is `29.25`, so a fresh rest
must last until `37.25`. Each flag instead permits movement at `30.75`. The
approach cooldown is deliberately zero to isolate rest gating; the default
cooldown would mask this example.

**Invalid bounds bypass suppression.** This Reviewer proposed the issue; the
Verifier independently reproduced it with gating assertions. The invalid-bounds
return precedes the suppression branch, leaving the active target and animation
intact even when movement is disabled. Restoring valid bounds resumes that target.

Reproduction command, run from the repository root against the source checkpoint
identified above (this is scratch review code, not an authored gating test):

```sh
python3 -B - <<'PY'
import ast, hashlib, math, random
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
print('run_start_utc=',datetime.now(timezone.utc).isoformat())
blob=Path('claude_pet.py').read_bytes(); source=blob.decode(); tree=ast.parse(source)
print('source_sha256=',hashlib.sha256(blob).hexdigest())
names={'ROAM_DEFAULTS','RoamOut','_roam_dist','_roam_clamp','_roam_seg_dist','Roamer'}
nodes=[n for n in tree.body if (isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
ns={'math':math,'random':random,'namedtuple':namedtuple}; exec(compile(ast.Module(body=nodes,type_ignores=[]),'claude_pet.py','exec'),ns)
for flag,value in [('enabled',False),('dragging',True),('blocked',True),('busy',True)]:
 r=ns['Roamer']((270,230),0,cfg={'rest_min_s':8,'rest_max_s':8,'approach_cooldown_s':0,'wander_radius':0,'walk_speed':40,'gap_s':100})
 b=(0,0,2000,1000); cursor=(950,230)
 r.step(8,cursor,b,activity=True)
 for i in range(1,43): r.step(8+i*.5,cursor,b,activity=True,**{flag:value})
 first=None
 for i in range(1,32):
  now=29+i*.25; out=r.step(now,cursor,b,activity=True)
  if out.moved: first=(now,out.pos); break
 print('longhold',flag,'expected_no_move_before=37.25','first_move=',first)
r=ns['Roamer']((100,100),0,cfg={'rest_min_s':0,'rest_max_s':0,'wander_radius':0})
b=(0,0,1000,1000); c=(600,100)
print('invalidbounds_plan=',r.step(0,c,b,activity=True))
print('invalidbounds_walk=',r.step(.1,c,b))
print('invalidbounds_disable=',r.step(.2,c,(300,0,200,1000),enabled=False))
print('invalidbounds_restore=',r.step(.3,c,b))
print('run_end_utc=',datetime.now(timezone.utc).isoformat())
PY
```

Actual output:

```text
run_start_utc= 2026-09-08T05:11:39.809737+00:00
source_sha256= 18c4890ededf34d59085cb2ff6365bc8029282d9c5f4fbfda67a986bd8c965cb
longhold enabled expected_no_move_before=37.25 first_move= (30.75, (280.0, 230.0))
longhold dragging expected_no_move_before=37.25 first_move= (30.75, (280.0, 230.0))
longhold blocked expected_no_move_before=37.25 first_move= (30.75, (280.0, 230.0))
longhold busy expected_no_move_before=37.25 first_move= (30.75, (280.0, 230.0))
invalidbounds_plan= RoamOut(pos=(100.0, 100.0), anim='running-right', moved=False, away=False, phase='out')
invalidbounds_walk= RoamOut(pos=(105.5, 100.0), anim='running-right', moved=True, away=True, phase='out')
invalidbounds_disable= RoamOut(pos=(105.5, 100.0), anim='running-right', moved=False, away=True, phase='out')
invalidbounds_restore= RoamOut(pos=(111.0, 100.0), anim='running-right', moved=True, away=True, phase='out')
run_end_utc= 2026-09-08T05:11:39.836107+00:00
```

Both issues were reported to the Coordinator before the Developer's correction.
Final resolution and sign-off remain pending the corrected source and the
Verifier's evidence.

### Resize while away retains the old route

The Verifier proposed this adapter issue and this Reviewer independently
reproduced it using a different home position. The Coordinator's accepted contract
requires a resize to pause the journey. The actual `roam_resync` updates the radius
but retains phase `out`. This was a synthetic source check of `claude_pet.py` only;
the file was captured once with SHA256
`83d41e7f6e38c322863363f37c2c48adfd2f5117d68a42b5edeaa050aa8193c0`.
Real run bounds were `2026-09-08T05:14:25.031279Z` through
`2026-09-08T05:14:25.058310Z`, recorded at the end. Grouping unit is a synthetic
resize invocation: the retained-route result occurred in `1 / 1` invocation.
The injected simulation clock uses `0`, `0.25`, and `0.5` seconds.

Exact scratch reproduction command:

```sh
python3 -B - <<'PY'
import ast, hashlib, math, random
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as N
print('run_start_utc=',datetime.now(timezone.utc).isoformat())
blob=Path('claude_pet.py').read_bytes(); tree=ast.parse(blob.decode())
print('source_sha256=',hashlib.sha256(blob).hexdigest())
names={'ROAM_DEFAULTS','RoamOut','_roam_dist','_roam_clamp','_roam_seg_dist','Roamer'}
nodes=[n for n in tree.body if (isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
ns={'math':math,'random':random,'namedtuple':namedtuple}; exec(compile(ast.Module(body=nodes,type_ignores=[]),'claude_pet.py','exec'),ns)
r=ns['Roamer']((200,200),0,cfg={'rest_min_s':0,'rest_max_s':0,'wander_radius':0},radius=math.hypot(50,50))
r.step(0,(1000,200),(50,50,950,650),activity=True); r.step(.25,(1000,200),(50,50,950,650))
f=N(origin=N(x=r.pos[0]-50,y=r.pos[1]-50),size=N(width=100,height=100))
def place(p): f.origin=N(x=p.x,y=p.y)
ns.update(win=N(frame=lambda:f,setFrameOrigin_=place),roamer=r,_time=N(monotonic=lambda:.5),NSMakePoint=lambda x,y:N(x=x,y=y))
gui=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_gui')
helpers=[n for n in gui.body if isinstance(n,ast.FunctionDef) and n.name in {'window_center','place_window_center','roam_resync'}]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'claude_pet.py','exec'),ns)
print('before_resize=',r.phase,r.pos,r.radius)
f.size=N(width=300,height=200)
ns['roam_resync']()
print('after_resize=',r.phase,r.pos,r.radius)
print('expected_phase=rest actual_phase=',r.phase)
print('run_end_utc=',datetime.now(timezone.utc).isoformat())
PY
```

Actual output:

```text
run_start_utc= 2026-09-08T05:14:25.031279+00:00
source_sha256= 83d41e7f6e38c322863363f37c2c48adfd2f5117d68a42b5edeaa050aa8193c0
before_resize= out (213.75, 200.0) 70.71067811865476
after_resize= out (213.75, 200.0) 180.27756377319946
expected_phase=rest actual_phase= out
run_end_utc= 2026-09-08T05:14:25.058310+00:00
```

The native-smoke draft also needed a discriminating layout fixture: starting at
the left margin and limiting travel does not guarantee crossing a screen
midpoint. I asked the Verifier to force and assert the crossing before reporting
sprite continuity, including watching, return, and rest. This is a test coverage
review, not a claim that a visual failure was observed.

## Review of the corrected source checkpoint

I read the complete core and GUI adapter diff at source SHA256
`146f4897acded4c2188bdccdf6ddf42485006fbbb9736d8f48a1ec39abdaca4f`.
The suppression branch now clears invalid active routes, a held rest is renewed,
an out-of-bounds center is brought into the visible area and stopped, and resizing
cancels the journey while refreshing the whole-window radius. The geometry
recovery is an explicit exception to ordinary walking speed, required to recover
an otherwise off-screen window after the display changes. It does not persist
automatic coordinates.

The following independent scratch run read only immutable bytes captured from
`claude_pet.py`. Real run bounds: `2026-09-08T05:17:43.985413Z` through
`2026-09-08T05:17:44.010221Z`, recorded at the latter timestamp. Injected times are
simulation seconds. For the longhold result, grouping unit is an injected
suppression flag: `0 / 4` flags produced movement in the sampled quiet interval
`29.25 <= now <= 36.75`. The invalid-bounds, display-shrink, and resize examples
each contain one invocation of the named operation; their actual values are
printed below. These are synthetic outcomes and do not estimate real-user rates.

```sh
python3 -B - <<'PY'
import ast, hashlib, math, random
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as N
print('run_start_utc=',datetime.now(timezone.utc).isoformat())
blob=Path('claude_pet.py').read_bytes(); tree=ast.parse(blob.decode())
print('source_sha256=',hashlib.sha256(blob).hexdigest())
names={'ROAM_DEFAULTS','RoamOut','_roam_dist','_roam_clamp','_roam_seg_dist','Roamer'}
nodes=[n for n in tree.body if (isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
ns={'math':math,'random':random,'namedtuple':namedtuple}; exec(compile(ast.Module(body=nodes,type_ignores=[]),'claude_pet.py','exec'),ns)
for flag,value in [('enabled',False),('dragging',True),('blocked',True),('busy',True)]:
 r=ns['Roamer']((270,230),0,cfg={'rest_min_s':8,'rest_max_s':8,'approach_cooldown_s':0,'wander_radius':0,'walk_speed':40,'gap_s':100})
 b=(0,0,2000,1000); cursor=(950,230)
 r.step(8,cursor,b,activity=True)
 for i in range(1,43): r.step(8+i*.5,cursor,b,activity=True,**{flag:value})
 early=[]
 for i in range(1,32):
  now=29+i*.25; out=r.step(now,cursor,b,activity=True)
  if out.moved: early.append((now,out.pos))
 print('longhold',flag,'early_movement=',early)
r=ns['Roamer']((100,100),0,cfg={'rest_min_s':0,'rest_max_s':0,'wander_radius':0})
b=(0,0,1000,1000); c=(600,100)
r.step(0,c,b,activity=True); r.step(.1,c,b)
print('invalidbounds_disable=',r.step(.2,c,(300,0,200,1000),enabled=False))
print('invalidbounds_restore=',r.step(.3,c,b))
r=ns['Roamer']((800,300),0,cfg={'rest_min_s':0,'rest_max_s':0,'wander_radius':0})
r.step(0,(1400,300),(50,50,950,650),activity=True); r.step(.25,(1400,300),(50,50,950,650))
print('display_shrink=',r.step(.5,(1400,300),(50,50,550,650)))
r=ns['Roamer']((200,200),0,cfg={'rest_min_s':0,'rest_max_s':0,'wander_radius':0},radius=math.hypot(50,50))
r.step(0,(1000,200),(50,50,950,650),activity=True); r.step(.25,(1000,200),(50,50,950,650))
f=N(origin=N(x=r.pos[0]-50,y=r.pos[1]-50),size=N(width=100,height=100))
screen=N(visibleFrame=lambda:N(origin=N(x=0,y=0),size=N(width=1000,height=700)))
def place(p): f.origin=N(x=p.x,y=p.y)
ns.update(win=N(frame=lambda:f,setFrameOrigin_=place,screen=lambda:screen),roamer=r,_time=N(monotonic=lambda:.5),NSMakePoint=lambda x,y:N(x=x,y=y))
gui=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_gui')
helpers=[n for n in gui.body if isinstance(n,ast.FunctionDef) and n.name in {'window_center','place_window_center','roam_resync','roam_bounds'}]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'claude_pet.py','exec'),ns)
f.size=N(width=300,height=200); ns['roam_resync']()
print('resize_phase=',r.phase,'resize_radius=',r.radius,'resize_pos=',r.pos)
print('run_end_utc=',datetime.now(timezone.utc).isoformat())
PY
```

Actual output:

```text
run_start_utc= 2026-09-08T05:17:43.985413+00:00
source_sha256= 146f4897acded4c2188bdccdf6ddf42485006fbbb9736d8f48a1ec39abdaca4f
longhold enabled early_movement= []
longhold dragging early_movement= []
longhold blocked early_movement= []
longhold busy early_movement= []
invalidbounds_disable= RoamOut(pos=(105.5, 100.0), anim=None, moved=False, away=True, phase='rest')
invalidbounds_restore= RoamOut(pos=(105.5, 100.0), anim='running-left', moved=False, away=True, phase='home')
display_shrink= RoamOut(pos=(550, 300.0), anim=None, moved=True, away=False, phase='rest')
resize_phase= rest resize_radius= 180.27756377319946 resize_pos= (213.75, 200.0)
run_end_utc= 2026-09-08T05:17:44.010221+00:00
```

No additional blocking production finding was identified in this checkpoint.
Final sign-off still awaits the Verifier's full result and final documentation
check. I did not author the gating assertions or edit production files.

## Final Reviewer sign-off

**APPROVED for development correctness and scope review**, recorded by Codex
Reviewer `/root/reviewer` at `2026-09-08T05:29:33Z`. This approves the reviewed
implementation and evidence. It is not a merge, commit, release, execution-gate,
installation, signing, or publication approval. None of those actions was
performed by this Reviewer.

The final reviewed application SHA256 is
`146f4897acded4c2188bdccdf6ddf42485006fbbb9736d8f48a1ec39abdaca4f`.
I also checked the finalized design document (SHA256
`c4c6ba5e61c19603be66a7fd8b8298f20521e64098acf5a5a1b6cb998eed1545`)
and `README.ko.md` (SHA256
`5c37e542a35b0ad93a941fcd8342b2ffb4f8dba7030f780accf850c3594cbb33`)
against the source. The final `tests/test_companion_motion.py` SHA256 is
`52614e4807633986dec54d714334765d905263133772df3420bf06efcbec79c2`.
The updates to existing manual-update and upload-artifact tests change only their
reviewed application source hash pins. I authored no gating assertion, fixture,
production code, or source-hash pin.

The Verifier's full suite output is recorded verbatim under “Final full suite”
in [quiet-companion-verification.md](quiet-companion-verification.md). It ran
from `2026-09-08T05:21:57.416541Z` through `2026-09-08T05:27:13.202346Z`, measured
at the end, with the same application hash at both bounds. Grouping key is
unittest case ID; the precise file/case set is enumerated in that output.
Result: `409 / 416` cases passed; `7 / 416` were explicit opt-in skips, with no
failure or error. The skipped live upgrade checks do not become coverage.
The recorded command was:

```sh
PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v
```

The independent initial REDs, subsequent regression REDs, corrected GREENs,
and in-memory rival failures are also preserved in that record. The initial
native assertion failure is retained and correctly described as a harness
assumption error: in that captured run the native window origins were rounded,
while the motion model retained fractional coordinates. Separating model speed
from sprite displacement relative to its window is the correct measurement;
this does not establish a universal AppKit rounding rule.

I opened the final [native contact sheet](quiet-companion-smoke.png) and
independently recalculated the final [native metadata](quiet-companion-smoke.json),
input SHA256 `28a516c9fa4575aa476a4f69723f91fe56b83f0c07c6c12d9024973424e8016f`.
The capture ran from `2026-09-08T05:28:02.071522Z` through
`2026-09-08T05:28:02.407979Z` on the final application hash. My recalculation was
measured at `2026-09-08T05:28:22.998500Z`. Grouping unit was an adjacent sampled
native tick pair: `0 / 1378` pairs had sprite displacement differing from window
displacement; the maximum difference was zero. Both screen midpoints were
actually crossed. The maximum model step was `2.7500000000006732` points, within
floating-point tolerance of the specified `55 * 0.05` step. The contact sheet
now captures the settled `running-right`, `review`, and `running-left` moods for
outgoing, watching, and home phases, respectively.

The left edge of the cat's face is clipped in the existing
`frames/running-left/00.png`, which I inspected directly after noticing the same
shape in the contact sheet. The sprite assets have no diff. This is a pre-existing
asset limitation, not an adapter regression, and this review does not claim that
all assets are visually flawless. The native smoke uses synthetic cursor/time
and disabled data workers; it does not establish real-user distraction rates or
validate every live system-settings interaction.

The discovered motion issues and the document accuracy issues are resolved in
the reviewed checkpoint. No blocking production or documentation finding remains
from this review. My sole written deliverable is this review record; the
Coordinator retains the merge decision and all release gates remain separate.

## Later actual-event-loop review: default wander cycle

At `2026-09-08T07:59:02Z`, I independently reviewed the live diagnostic launcher
`/tmp/claudepet-actual-ui-20260908-qa.py`, SHA256
`0a906d00f6db0a89299e131b0a9c5125184279b1c58ffdb85b6619010093a5f0`.
It calls the original `Roamer.step` once with the original time, cursor, bounds,
and keyword inputs and returns that same result unchanged. It adds observation
logging and selects a temporary configuration path, then calls normal
`run_gui()`. It does not advance a synthetic clock, alter motion defaults, or
inject a destination. This is instrumented actual execution, distinct from the
earlier synthetic native smoke. Logging can add overhead; this is not a timing
performance benchmark.

I read immutable bytes captured from
`docs-design/quiet-companion-live-trace.jsonl`, snapshot SHA256
`ca07de98a965970d1be109c19504398e7862e05a45cb98a7193146d1f3fe9d51`,
and selected `2026-09-08T07:56:58Z <= utc < 2026-09-08T07:57:05Z`. The
measurement timestamp was `2026-09-08T07:58:09.640636Z`. That subset contains
eighteen logged step records; the logger samples periodic records and transition
changes, so this is not the complete set of timer callbacks. The launch record
identifies PID `71387` and application source SHA256
`146f4897acded4c2188bdccdf6ddf42485006fbbb9736d8f48a1ec39abdaca4f`.

| Actual UTC timestamp | Transition | Model center |
| --- | --- | --- |
| `2026-09-08T07:56:59.098376Z` | rest to out, kind wander | `(252, 218)` |
| `2026-09-08T07:57:00.348357Z` | out to look, kind wander | `(294.8593642640554, 166.50403989952065)` |
| `2026-09-08T07:57:02.398442Z` | look to home | `(294.8593642640554, 166.50403989952065)` |
| `2026-09-08T07:57:03.648412Z` | home to rest | `(252, 218)` |

Grouping unit is an uninterrupted wander cycle in this selected interval:
`1 / 1` observed cycle completed its return to the same home. This confirms the
default motion logic executing on the real event loop for that cycle. The
wrapper records the model result before the GUI adapter places the window, so
actual NSWindow movement must additionally be supported by the Verifier's
separate native-window snapshots; the trace alone is not that measurement.
This is a wander cycle, not an approach or six-second review cycle. Menu,
drag, hover, and other input tests remain separate. I performed no GUI action,
launch, event injection, production edit, or test edit for this review.

## Second requirement: compact travel and arrival summary

The earlier approval applies to source `146f4897…`, before this requirement.
Review of the new presentation checkpoint is **pending correction and independent
verification**, not approved. The reviewed source SHA256 is
`3ffcde044008a262aa9afde2cfc92506f38b8bccddb5511413cc94eb8ac34208`;
it was still unchanged at `2026-09-08T09:06:04.152811Z`.
The Reviewer has not edited application source, test assertions, fixtures, or
source pins, and has performed no GUI input or launch.

### Independent geometry derivation

I derived this example before reading the new geometry implementation body or
the Verifier's expected values. These are stipulated fixture dimensions, not
measurements of the installed app: full `300 × 220`, sprite `80 × 60`,
`pill_h=152`, `scale=0.5`, measured-text input `text_w=130`. The contract uses
`BTN_R=13`, `GAP=6`, `PILL_PAD=13`, summary height `30`, width
`min(260, max(120, text_w + 26))`, and a two-point padded union clamped to full.
The summary pill is therefore `156 × 30`, at x `4`/`140` for left/right and
y `66`/`126` for top/bottom. Global coordinates are y-up; local crop coordinates
are flipped y-down. The screen origin is `(-1800,240)`, size `(1400,900)`.

For a preserved sprite top-left global anchor `A=(-980,860)`, the formula is
`Oactual = Ofull + (crop.x, H - crop.y - crop.h)`. It gives:

| Frozen orientation | Folded crop | Summary crop | Full origin | Folded origin | Summary origin |
| --- | --- | --- | --- | --- | --- |
| left, top | `(4,0,112,64)` | `(2,0,160,98)` | `(-986,642)` | `(-982,798)` | `(-984,764)` |
| right, top | `(184,0,112,64)` | `(138,0,160,98)` | `(-1194,642)` | `(-1010,798)` | `(-1056,764)` |
| left, bottom | `(4,156,112,64)` | `(2,124,160,96)` | `(-986,798)` | `(-982,798)` | `(-984,798)` |
| right, bottom | `(184,156,112,64)` | `(138,124,160,96)` | `(-1194,798)` | `(-1010,798)` | `(-1056,798)` |

For each row and mode, adding the crop-local sprite offset back to the actual
origin recovers `A`. The unequal top/bottom summary heights follow from the
specified padding and full-height clamp. The current pure `roam_frame` formula
matches this independent derivation. Keeping the actual frame center fixed,
forgetting flipped-y conversion, or recomputing orientation after a screen-half
crossing produces different anchors. Native rounding remains a separate check.

### Findings at the 3ffc checkpoint

**Drag position overwritten during display restoration.** Using the actual
source `roam_tick`, `roam_apply_display`, `window_center`, `place_window_center`,
and geometry/core helpers with a fake NSWindow, I began folded `out` at logical
center `(500,400)`, moved the actual window by the same `(20,15)` displacement
that `mouseDragged_` applies, then ticked with `dragging=True`. The window had
logical center `(520,415)` and sprite anchor `(376,523)` before the tick, but
returned to `(500,400)` and `(356,508)` after it. The out-to-rest crop change calls
`place_window_center(roamer.pos)` before the release hook has synchronized that
position. This is a single constructed adapter case, not an actual GUI run.
Run UTC bounds: `2026-09-08T09:00:39.332477Z` through
`2026-09-08T09:00:39.333022Z`; measurement is the end. Actual output:

```text
before_drag folded (500.0, 400.0) (356.0, 508.0)
after_user_drag_before_tick (520.0, 415.0) (376.0, 523.0)
after_actual_roam_tick rest full (500.0, 400.0) (356.0, 508.0)
```

**Drop clamp and saved home use incompatible envelopes.** With a visible screen
`(0,0,1400,1000)`, the same full/sprite dimensions and a right/top folded crop,
I moved the actual `112 × 64` window to `(0,446)`. Actual source `mouseUp_`
calls `clamp_to_screen`, which accepts this small frame, then saves logical
origin `(-184,290)` and establishes home `(-34,400)`. On the next tick,
`hover=True` suppresses core bounds recovery while full display restoration
creates an off-screen full frame and sprite. The source methods for orientation,
mouseUp, clamp, release, tick and display were executed; the window was a fake,
and no real config was written (writes were captured in a list). This is one
constructed drop case. Run bounds: `2026-09-08T09:03:28.941872Z` through
`2026-09-08T09:03:28.943064Z`; measured at the end. Actual output:

```text
drop_actual_frame origin=(0,446.0), size=(112,64), logical=(-34.0,400.0)
saved [{'x': -184, 'y': 290.0}] home (-34.0, 400.0)
after_release_tick actual_rect (-184.0, 290.0, 300, 220)
sprite_anchor (-178.0, 352.0)
logical_bounds (150.0, 110.0, 1250.0, 890.0)
```

**Long summary text exceeds its drawing area.** The actual summary text helper
and pill geometry were executed with the same native monospaced font attributes
as `F_SUMMARY` (`11`, weight `0.4`). No native window was created. Source
`draw_summary_pill` centers the entire attributed string without fitting it,
while the pill width is capped at `260`. The English and Spanish API-key-needed
statuses already exceed that width; this does not depend on invented server
labels. Grouping unit is a language/status case, precisely the English and
Spanish `need_admin_key` strings in `claude_pet.py` at the stated hash.
Run bounds: `2026-09-08T09:01:42.749637Z` through
`2026-09-08T09:01:42.788390Z`; measured at the end. Both of the two measured
strings exceeded the pill. Actual measurements:

| Language | Native text width | Pill width | Text x interval relative to pill |
| --- | --- | --- | --- |
| en | `326.390625` | `260` | `[-33.1953125,293.1953125]` |
| es | `414.7880859375` | `260` | `[-77.39404296875,337.39404296875]` |

**Estimate provenance disappears in the summary.** In that same helper run,
Korean estimated session/weekly inputs `42`/`17` rendered `세션 42% · 주간 17%`;
exact rows labelled `세션`/`주간` with those values rendered the identical text.
The full panel has an estimate status marker, but the summary omitted it.
The Coordinator subsequently made the product contract explicit: estimated
percentages have `≈`, exact percentages do not. This is a required presentation
correction; the numeric estimator itself is unchanged.

These findings were sent to the Coordinator and independent Verifier before
Developer corrections. They remain proposed until the Verifier reproduces
them; passing this Reviewer-only scratch harness is not a gating test. The
previously reported in-place approach/hover latch issue was independently RED
at `e8bc7fb9…`; the new `settled` cause input correctly distinguishes it from
normal in-place look completion in the present source. Final sign-off awaits
the replacement source checkpoint, independent RED/GREEN results, and actual
input/render evidence.

### Corrected source review: 9d15 checkpoint

The Verifier independently reproduced the four findings on `3ffcde04…` during
`2026-09-08T09:08:20.410631Z` through `2026-09-08T09:08:20.858265Z`, using
different drag/drop coordinates and a variable-width drawing fixture. The raw
RED output is retained in [the verification record](quiet-companion-verification.md).
They are therefore established defects in that earlier checkpoint, rather than
Reviewer-only hypotheses.

Source review of their corrections **passes** at SHA256
`9d15b8790a4b414824ace0cb17ce72d9b7410a2cd948dcd9448d8aa85529dc99`.
I communicated this source approval before the Verifier updates source pins and
runs the full suite. Final development sign-off still awaits those results and
the native/actual-input evidence; it is not a release or merge decision.

The corrections preserve the pre-resize actual logical center in
`roam_apply_display`, clamp the logical full envelope before saving a drop,
fit summary text to the pill's inner width using the same unchanged font used
for drawing, and distinguish estimates with `≈`. Exact source labels are not
translated or marked as estimates. The crop geometry and motion safety envelope
remain the agreed full logical window. Sections 5 and 9 of the design document
now describe the corresponding coordinate and display contracts.

I reran the same constructed drag and edge-drop procedures on this source,
and remeasured the same two status strings with native font metrics. This run
read only `claude_pet.py` at the stated hash; it executed source AST definitions
with fake windows/config writers and performed native attributed-string
measurement without creating a window. Invocation was
`PYTHONDONTWRITEBYTECODE=1 python3 -` with the read-only AST harness described
above. Run bounds were `2026-09-08T09:18:13.590142Z` through
`2026-09-08T09:18:13.632827Z`; measurements were recorded at the end. The
grouping cases are exactly the earlier `(20,15)` drag, right/top drop at x=0,
English/Spanish API-key statuses, and paired Korean estimate/exact strings.
Actual output:

```text
source_sha256 9d15b8790a4b414824ace0cb17ce72d9b7410a2cd948dcd9448d8aa85529dc99
drag_center_before_after (520.0, 415.0) (520.0, 415.0)
edge_saved [{'x': 0, 'y': 290.0}] home (150.0, 400.0)
full_rect (0.0, 290.0, 300, 220) sprite_anchor (6.0, 352.0)
fit en 'Right-click → Settings to enter a…' width 231.193359375 available 234
fit es 'Clic derecho → Ajustes para intro…' width 231.193359375 available 234
estimate 세션 ≈42% · 주간 ≈17%
exact 세션 42% · 주간 17%
```

The drag displacement is retained, the saved home and restored full frame are
inside the stipulated screen, both fitted strings remain inside the stated
inner width, and exact/estimated output is visibly distinguishable. These
checks establish the fixes for the recorded counterexamples; they are not a
claim about every live input ordering or every display configuration.

### Independent review of final automated and actual-run evidence

I read the final focused/full raw outputs in
[quiet-companion-verification.md](quiet-companion-verification.md). The focused
file `tests/test_companion_motion.py` ran from
`2026-09-08T09:15:51.537795Z` through `2026-09-08T09:15:54.285723Z`:
`50 / 50` unittest case IDs passed. The full suite ran from
`2026-09-08T09:17:53.374563Z` through `2026-09-08T09:23:08.579184Z`, with
source `9d15b879…` at both bounds. Its grouping key is unittest case ID, and its
precise file/case set is the `tests/test_*.py` cases enumerated in that raw
output: `433 / 440` passed, `7 / 440` were existing explicit opt-in skips,
zero failures/errors, exit zero. The measurement is the recorded run end.
Command:

```sh
PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v
```

The two existing transaction/artifact test diffs change only their reviewed
application SHA pins to the same final source. I inspected those diffs and the
final Korean README; no additional blocking source/documentation finding was
identified. The design document hash at `2026-09-08T09:26:44.659797Z` was
`06b7d27f849f8e67557dc50bf567676982e3ce474f936fb2222045ed8a5ef836` and the
Korean README hash was
`331a63efd92b6bbfd29d0eba5a1d36ca4c2ae0c0fc2c3bcdb5b81314511af5b5`.

**Synthetic native rendering remains a separate evidence category.** I opened
the final [compact contact sheet](quiet-companion-compact-smoke.png) and read
[its metadata](quiet-companion-compact-smoke.json), SHA256
`f86c93fbbc8556d2c8cfb3e5e28b304d39fc436a52d657e92936bc34d3189581`.
The PNG hash was
`564749eef95d7129b3abdff41b4e138b10bc67efbd03d10801e6d4d7e4b291de`.
The real NSWindow/View capture, with synthetic clock/cursor and data workers
suppressed, ran from `2026-09-08T09:16:11.602897Z` through
`2026-09-08T09:16:11.867407Z`. My recalculation at
`2026-09-08T09:25:43.965708Z` covered all `1696` recorded native callbacks and
`1695` adjacent pairs: `0 / 1696` actual frames violated the stated visible
screen bounds, both screen midpoints were crossed, the maximum model step was
`2.7500000000006732` points, and the maximum per-axis sprite/model anchor
residual was `0.8729688998084839` points. The settled capture poses are walking
right, review, walking left. This supports continuity across the tested crop
transitions with the measured native rounding; it is not a universal AppKit
rounding guarantee. The previously noted unchanged left-facing asset clipping
is still visible and remains outside this code change.

**Actual event-loop execution.** I reread
`/tmp/claudepet-actual-ui-20260908-qa.py`, SHA256
`586c7cd84457f9bd39bc98995d2ddd7107b77166451f14ccb341b7715e758e19`.
It calls the original step once with unchanged arguments and returns the same
result. It reads native frame/sprite state for logging, selects a temporary
config, and starts normal `run_gui`; it does not replace the clock, defaults,
cursor polling, RNG, or targets. Its added logging means this is instrumented
actual execution, not a performance benchmark. The wrapper's `pre_native`
record precedes the model step, so native display changes appear in the next
record rather than necessarily alongside the phase-change result.

The final-source launch record identifies PID `33130` at
`2026-09-08T09:16:12.309060Z`. I read immutable bytes from
`quiet-companion-live-trace.jsonl` at `2026-09-08T09:24:30.743664Z`, snapshot
SHA256 `99a9d9d1c4454cf8608fd156faef3a2a0c4e706a98925c12da54d55d1942fb54`.
The selected PID had `932` logged step records between
`2026-09-08T09:16:12.532260Z` and `2026-09-08T09:24:30.235202Z`. The trace is
sampled and still being appended by the Verifier; these are logged records,
not a count of every timer callback or a measurement of ordinary-user activity.

The first uninterrupted actual approach cycle was independently recalculated
at `2026-09-08T09:29:46.575873Z`. The selected interval is inclusive
`2026-09-08T09:17:36.133230Z` through `2026-09-08T09:17:54.683243Z`, PID
`33130`, event `step`, exactly `41` records. The canonical JSON of this selected
list (`sort_keys=True,separators=(',',':'),ensure_ascii=False`, UTF-8) hashes to
`6806030ead4a1bb48829f92d60dcbaa47ad18156509a7ebaf1a27a907e907e07`.

| Actual UTC | Model phase | Native display in following recorded callback |
| --- | --- | --- |
| `09:17:36.133230` | out, approach | folded `128 × 108` |
| `09:17:42.382959` | look, approach | summary `143 × 140` |
| `09:17:48.383301` | home | folded `128 × 108` |
| `09:17:54.633160` | rest | full `268 × 240` |

Grouping unit is this uninterrupted approach/return cycle: `1 / 1` completed
return in the selected interval. Its monotonic look duration was
`6.000315583311021` seconds. Actual first/last frame was identically
`(634,401,268,240)` and actual sprite top-left identically `(640,509)`.
Across the `41` samples, maximum per-axis sprite/pre-step-model residual was
`0.8268386065502682` points. I also opened the actual
[arrival capture](quiet-companion-arrival.png), SHA256
`a8e3a55362f08b48ef331fa829fd7b3c262e0dd5ca7268529ab57801f0558970`,
which shows the compact exact-value summary and pet; the captured pose is not
used to assert that the entire six-second interval showed a single pose.

The same selected trace independently supports the following actual UI
outcomes, each scoped to the Verifier's controlled input sequence: roam OFF
and ON, a folded edge drop establishing a bounded home, settings open/close,
and a second approach whose summary survives hover. At
`2026-09-08T09:23:21.034396Z`, that second approach is stopped/resting with
`summary_latched=True`, `summary_expanded=True`, native full frame
`268 × 240`, and the original manual `show_panel=False` unchanged. A later
chevron click returns to summary at `09:24:16.434908Z`; the menu interruption
clears the latch and returns to the original folded mode at `09:24:17.434659Z`.
These are actual-window/input results, distinct from the synthetic smoke.
OS Reduce Motion restoration and the final uninstrumented launch are the
remaining Verifier handoff items at this review checkpoint.

### Actual OS integration reopened the menu gate

The source approval above is **reopened pending a menu correction**. The
Verifier's actual OS test confirmed motion suppression with Reduce Motion ON
and restoration to the original OFF setting, but the menu item's actual
`AXEnabled` value remained true. The Verifier proposed that NSMenu automatic
validation overwrites the explicit `setEnabled_(False)` call.

I independently reproduced that cause without displaying a menu, starting an
event loop, or sending input. An initial probe without an NSApplication context
left both variants disabled; it ran from `2026-09-08T09:32:53.308547Z` through
`2026-09-08T09:32:53.314148Z`. That missing app context was an instrument
limitation, not a successful reproduction or a refutation. The corrected probe
below ran from `2026-09-08T09:33:24.927255Z` through
`2026-09-08T09:33:25.013980Z`, measured at the end. Grouping key is the two
stipulated `autoenablesItems` settings of native NSMenu instances with a valid
action target. Application source `9d15b879…` was read to confirm it has the
manual `setEnabled_` call and no `validateMenuItem` or auto-enable override.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from AppKit import NSApplication, NSApplicationActivationPolicyProhibited, NSMenu, NSMenuItem
from Foundation import NSObject
class ReviewerMenuTarget(NSObject):
    def toggleRoam_(self, sender):
        pass
app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
target = ReviewerMenuTarget.alloc().init()
for auto in (True, False):
    menu = NSMenu.alloc().initWithTitle_('review-only-not-displayed')
    if not auto:
        menu.setAutoenablesItems_(False)
    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Roam', 'toggleRoam:', '')
    item.setTarget_(target)
    item.setEnabled_(False)
    menu.addItem_(item)
    print('before_update', menu.autoenablesItems(), item.isEnabled())
    menu.update()
    print('after_update', menu.autoenablesItems(), item.isEnabled())
PY
```

```text
before_update True False
after_update True True
before_update False False
after_update False False
```

The Verifier then recorded an actual-production-menu regression RED during
`2026-09-08T09:33:43.558Z` through `2026-09-08T09:33:43.849Z`:
`CompanionGuiOwnershipTests.test_native_menu_validation_preserves_reduce_motion_disabled_item`
expected `[False, True]` for Reduce Motion ON/OFF but obtained `[True, True]`.
Their actual `AXEnabled=True` measurement was at `09:32:13.923Z`. The native
cause reproduction, source path, and actual UI symptom agree, establishing the
finding. The earlier full-suite success did not cover this missing native menu
validation behavior, and cannot be presented as evidence that this menu worked.

### Menu correction source approval: 3a961 checkpoint

Source review **passes** for
`3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c`.
The production correction consists of `menu.setAutoenablesItems_(False)`
immediately after menu creation plus its three comment lines. I removed exactly
those four added lines in memory and hashed the result: it is exactly
`9d15b8790a4b414824ace0cb17ce72d9b7410a2cd948dcd9448d8aa85529dc99`.
Consequently, the preceding motion, crop, summary, clamp, and actual-cycle
evidence applies to byte-identical code paths; the changed menu behavior needs
its own new evidence, supplied below and by the Verifier's actual OS run.

I extracted the actual `rightMouseDown_` menu construction and initial item loop
from the final source AST and executed them with native NSMenu/NSMenuItem,
an NSApplication context with activation prohibited, and a valid NSObject
target exposing the listed selectors. No menu was displayed, event loop run,
or input sent. After `menu.update()`, the Reduce Motion ON case retained
`menu_roam=False`; the OFF case retained `menu_roam=True`. In both cases the
settings, panel toggle, reset size, uninstall and quit items remained enabled.
Only enabled states were inspected; no action was invoked.

This run covered the stipulated two Reduce Motion states and their six ordinary
root menu items, not every possible native menu context. It read only the final
`claude_pet.py` and ran from `2026-09-08T09:36:52.122036Z` through
`2026-09-08T09:36:52.218532Z`, measured at the end. Actual output:

```text
source_sha256 3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c
remove_exact_four_added_lines_sha256 9d15b8790a4b414824ace0cb17ce72d9b7410a2cd948dcd9448d8aa85529dc99
reduce_motion True autoenables False
after_update [('menu_settings', True), ('menu_toggle', True), ('menu_roam', False), ('menu_reset_size', True), ('menu_uninstall', True), ('menu_quit', True)]
reduce_motion False autoenables False
after_update [('menu_settings', True), ('menu_toggle', True), ('menu_roam', True), ('menu_reset_size', True), ('menu_uninstall', True), ('menu_quit', True)]
```

The Coordinator was informed that the source gate passed so the Verifier could
refresh the source pins and run the final suite while completing actual OS
checks. Final overall sign-off remains contingent on those final results and
restoration/handoff records, rather than being inferred from this isolated
native reproduction.

## Final development sign-off

**Approved at `2026-09-08T09:48:33Z`** for source
`3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c`.
All concrete findings from this review are resolved. I retain only the Reviewer
role and authored no production or gating test change. The sole written
deliverable I modified is this review record.

I read the final Verifier PASS record, raw focused/full outputs, actual OS menu
events, restoration record, and exact normal-run launcher. The focused suite
passed `51 / 51` case IDs from `tests/test_companion_motion.py` during
`2026-09-08T09:36:18.985914Z`–`2026-09-08T09:36:21.757336Z`.
The final full suite ran during
`2026-09-08T09:38:16.301325Z`–`2026-09-08T09:43:35.791215Z` with the final
source hash identical at both bounds. Grouping key is unittest case ID; file
and case set is `tests/test_*.py` as enumerated in the raw output. Result:
`434 / 441` passed, `7 / 441` existing explicit opt-in skips, zero failures or
errors, exit zero, measured at the run end. The recorded command remains:

```sh
PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -v
```

The final synthetic native artifact was also independently recalculated at
`2026-09-08T09:42:12.631530Z`. It ran on final source from
`2026-09-08T09:37:40.249029Z` through `2026-09-08T09:37:40.553535Z`.
The complete `1315` manually invoked native callback records (`1314` adjacent
pairs) have `0 / 1315` visible-bound violations, cross both screen midpoints,
and retain a maximum model step of `2.7500000000006315` points. Maximum per-axis
sprite/model residual is `0.8747334539777967` points. Metadata SHA256:
`d21282f562e8883d761fd4ffd0e3ddd2e124d9aa5f735b3c3c2bdd73c958c562`.
The settled contact-sheet PNG remains byte-identical to the image already
inspected above (`564749ee…`). These native results retain the stated synthetic
clock/cursor scope; the separate actual event-loop evidence is not replaced
by them.

For the final actual menu check, I read the two `final_os_menu_validation`
events for PID `49172` directly. At `2026-09-08T09:40:46.132305Z`, OS Reduce
Motion ON gives `화면 돌아다니기: AXEnabled=False`. At
`2026-09-08T09:40:49.485623Z`, OFF gives `AXEnabled=True`. In each observation,
the four named ordinary items—settings, gauge toggle, reset size, quit—remain
enabled (`4 / 4` per state). The actual accessibility snapshots agree with
those values. Motion suppression itself was already observed in the preceding
actual OS run; only the native menu setting differs between those sources,
as verified by the exact byte comparison above.

The Verifier restored OS Reduce Motion to False, normal sensitivity to `1.0`,
and the pre-existing System Settings Storage view. I confirmed the final trace
ends with `reduce_motion=False`, `enabled=True`, and no open settings/menu.
The trace is now stopped and strictly JSONL: the Verifier explicitly records
normalizing the non-finite no-activity sentinels to null, with finite positions,
times, and event rows retained. At my final read,
`2026-09-08T09:47:18.681994Z`, its frozen SHA256 was
`1829600a0f1134d401b39438bdf1ff95ed3fc7fd47641fe8f76623d618df5a00`,
last step `2026-09-08T09:44:02.825143Z`. Earlier trace hashes in this document
identify earlier snapshots, before that final normalization.

The normal-run handoff record at `2026-09-08T09:44:54.321876Z` identifies PID
`58849`. I inspected its recorded stdin launcher: it imports the final module,
sets only the isolated CONFIG_PATH, checks `roam=True` and `spike_mult=1.0`,
prints the source identity, and calls normal `pet.run_gui()`. It installs no
step/ticker wrapper, cursor generator, or trace writer. Its output pins the
same final source hash. A read-only process check confirmed the instrumented
PID `49172` is gone, normal development PID `58849` remains, and original
installed PID `29528` remains. I opened the recorded window `1531` screenshot
and confirmed the normal full-panel pet is displayed. That screenshot verifies
rendering, not the accuracy of the displayed usage calculation.

The final design document, checked against source at
`2026-09-08T09:41:24.422897Z` and rechecked at `09:47:18.681994Z`, has SHA256
`fea117cd02e55c79fba06b4a645226095de621609af7fd9be728cb7f482633da`.
Its implementation state, crop/summary/menu contracts, and links to the
independent verification records are consistent. Checklists are distinguished
from execution results. No further source or documentation change is requested.

The actual tested flows cover default-time approach/watch/return, compact and
summary/full transitions, hover and expansion, manual placement and screen-edge
recovery, menu OFF/ON, settings open/close, and actual OS Reduce Motion behavior.
The common movement/crop/summary source is byte-identical between the detailed
actual-cycle run and the final menu fix. This evidence supports the requested
development result within those tested flows; it makes no empirical claim
about distraction rates or every possible monitor/input configuration.
No commit, merge, build, installation, signing, publication or release was
performed by this Reviewer. Those operations remain outside this sign-off;
they are not uncompleted correctness checks for this development task.

## v0.22 release — pre-commit review

**Verdict: PASS** for the v0.22 release commit, with three non-blocking findings
(F1–F3) and three informational notes (F4–F6). This is a pre-commit correctness
and scope review only. It is **not** release authorization, **not** a finding
that the §6 execution gate passed — that gate is not yet evaluable, because the
release commit does not exist — and **not** a Coordinator sign-off.

Reviewer: `reviewer-v022`. I held no role on this change before this review.
I edited only this document. I ran no git write command, launched no GUI, built
nothing, and touched no user-owned untracked path.

Reviewed at `2026-09-08`, against base commit `45a03c41b1e2fd3403ce52958a58956e12546086`.
The four files whose content this review turns on were byte-stable across the
whole review; I hashed them at the start and again at the end:

```text
c3d343439c812804154b02ce8cd1959d385c576256a471204af589996e8dcaf9  claude_pet.py
8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d  verify_release_artifact.py
9d56cd606a2f1768b6c43f05d52004a30b785cab3fbeca45cecb00a488f4a27e  RELEASE_NOTES.md
331a63efd92b6bbfd29d0eba5a1d36ca4c2ae0c0fc2c3bcdb5b81314511af5b5  README.ko.md
```

### 1. Hash reconstruction — both reconstruct exactly

The claim under test was that the only production edits since the previously
reviewed source are the `APP_VERSION` literal and the usage line in the release
verifier. I copied each file to a scratch directory, replaced only that one
literal, and hashed the result.

| File | Occurrences of the changed literal | Reconstructed SHA256 | Previously reviewed/pinned | Result |
|---|---|---|---|---|
| `claude_pet.py` (`APP_VERSION = "0.22"` → `"0.21"`) | 1 | `3a96147a2e4658eec7182662d85ccbb669e5449b244caa689e7b669138d9768c` | `3a96147a…` | **MATCH** |
| `verify_release_artifact.py` (`--expect-version 0.22` → `0.21`) | 1 | `7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa` | `7f4e4887…` | **MATCH** |

Each literal occurs exactly once, so the substitution is unambiguous and the
reconstruction is a complete proof, not a sample. The claim holds byte for byte:
every line of both files other than those two is identical to the source that
carried the Reviewer PASS at `2026-09-08T09:48:33Z`. The whole body of prior
verification and review evidence therefore applies to byte-identical code, and
nothing in the v0.22 diff needs that evidence re-derived.

### 2. Tracked diff — correctness and scope

I read the entire `git diff`, including all 984 changed lines of `claude_pet.py`,
and mapped every `git diff -U0` hunk to its enclosing top-level construct rather
than judging scope by eye. The complete set of top-level constructs containing a
changed line is: `APP_VERSION`, `RUNTIME`, `apply_config`, `TR`, the append point
after `gauge_rows` (whose body is unchanged — the new block is pure addition
after its `return`), the new quiet-companion module-level symbols, and `run_gui`.

**The estimator is untouched.** `_weigh_usage` (1752), `parse_usage_entries`
(1792), `_weekly_window_start` (1881), `_detect_model_keyword` (1903) and
`compute_usage` (1913, which contains `is_spike` at 1983) all lie inside the
unchanged span between the last `TR` hunk and line 5090. `spike_info` (5869) is
likewise unchanged. `RUNTIME`'s only edit is the added `"roam"` line at 923 — the
three limit constants at 916–918 and the weight table are byte-identical.
**Consequence: no calibrated user's `%` moves, and v0.22 requires no
recalibration warning** under CLAUDE.md's Danger zone.

**The updater, lock and transaction code is untouched.** `_acquire_update_lock`
(3018), `validate_update_app` (4219) and `_zip_members_are_safe` (4323) sit in
the same unchanged span. So do `seed_bundled_pet_assets` (318),
`prepare_settings_config` (1545), `plan_settings_save` (1638),
`SETTINGS_OWNED_KEYS` (1387), `merge_config_updates` (1431), `_read_oauth_token`,
`_fetch_cli_usage` and `fetch_exact_usage`.

**No new logging of anything.** Grepping every added line for `print(`, `dbg`,
`debug`, `log`, `write(` and `open(` returns nothing. The only new datum the
feature reads is `NSEvent.mouseLocation()`, which is passed straight into a pure
state machine that has no file, network or subprocess access. No path, transcript
body or session identifier reaches any sink.

**The new config key.** `RUNTIME["roam"]` (`claude_pet.py:923`) is
`os.environ.get("CLAUDE_PET_ROAM", "1") != "0"` — **roaming is ON by default**,
which matches README.ko.md's "기본 켜짐". It is listed in `apply_config` (936) so a
saved `false` is restored at launch, and `Handler.toggleRoam_` persists it with
`merge_config_updates({"roam": value})` — its own key only, the same discipline
as `x`/`y`/`scale`/`pet`. It is deliberately **not** in `SETTINGS_OWNED_KEYS`, and
since `merge_config_updates` merges onto the on-disk dict rather than replacing
it, a settings-panel save cannot drop the key. The frozen
`prepare_settings_config` / `plan_settings_save` contract is untouched.

**Reduce Motion is real, and it gates in two independent places.**
`_reduce_motion()` (6498) calls
`NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion()` inside a
`try/except` that returns `False` on failure. `roam_tick()` re-reads it at **1 Hz**
(`if now - roam_clock["rm_at"] >= 1.0`) into `state["reduce_motion"]`, then
computes `enabled = bool(RUNTIME.get("roam")) and not state["reduce_motion"]`.
So (a) **movement is suppressed** — `enabled=False` is part of `hold`, which stops
any in-flight leg in place rather than sending the pet home — and (b) **the menu
item is disabled**, via `mi.setEnabled_(not state["reduce_motion"])`. (b) only
works because `menu.setAutoenablesItems_(False)` was added; that is the four-line
correction the prior Reviewer approved at the `3a961` checkpoint. I re-verified
the two things that setting could have broken: `vitem.setEnabled_(False)` is
explicit, so the version item stays disabled without relying on auto-validation,
and every other root item and every pet-submenu item has `setTarget_(handler)`
and is intended to be enabled.

**Autonomous positions are never saved.** `mouseUp_` (6223–6224) is the only
writer of `x`/`y` anywhere in the file, and it is now inside `if moved:` — a real
drag, not a click and not an automatic move. It also converts a folded window's
origin back to the **logical full-window** origin before storing, so a pet dropped
while compact reopens in the same place. Roaming itself performs no config write
at all. README.ko.md's "스스로 돌아다닌 자리는 저장하지 않고, 드래그해 놓은 자리만
기억함" is exact. The pre-feature RED for precisely this is preserved in the
verification record as `AssertionError: Lists differ: [{'x': 550.0, 'y': 450.0}] != []`.

**The pre-existing interaction paths still work.**

- *Hover greeting.* Its guard is unchanged: `RUNTIME.get("greet") and not
  state["dragging"] and state["override"] is None and not spike_info(...)`.
  `roam_tick()` runs after the greeting check within the same tick, and `blocked`
  includes `state["hover"]`, so bringing the cursor to the pet stops it and clears
  the roam override; the greeting then fires on the following tick (≤ 50 ms later).
  The one edit inside that block —
  `cy = f.origin.y + (f.size.height - py - PH / 2)` — is a correction, not a
  regression: `petOrigin()` now returns *actual* (possibly cropped) window
  coordinates, so continuing to mix it with the logical `H` would have been the bug.
- *Spike.* `spike_info` is unchanged and is added to `busy`, so the pet holds
  still during a spike. All three paths by which the estimator reaches visible
  behaviour in exact mode (red session bar, mood/tint/greeting suppression,
  session-reset jump) are untouched.
- *Drag.* `dragging` is passed to `step()`; `mouseUp_` calls the `roam_release`
  hook — `moved=True` → `set_home` plus `RoamDisplay.reset()`, `moved=False` →
  stop in place with `settled=False` and no config write.
- *Double-click refresh.* Intact and reached: `set_override("jumping")`,
  `_oauth_cache["t"] = 0.0`, `tk.refresh_(None)`.

**Translations are complete.** `menu_roam` appears exactly 4× (en/ko/ja/es), as do
`today` and all five status keys the summary can emit (`need_admin_key`,
`loading`, `onb_install`, `onb_login`, `scanning`).

**One scoping detail I checked because it would have failed silently.** All three
window-resize paths (`set_scale`, `apply_pill_rows`, `set_pet`) declare
`nonlocal PW, PH, W, H` (6571, 6595, 6611), so the `roam_env_update()` they each
call afterwards reads the *new* `W`/`H` from `run_gui`'s scope rather than stale
values.

### 3. Release notes (v0.22)

**PASS** against CLAUDE.md step 2 and AGENTS.md §6.

- **Pure insertion, verified by bytes, not by reading the diff.** I deleted the
  811-byte `**v0.22**` block from the working file and compared the result with
  `git show HEAD:RELEASE_NOTES.md`: byte-identical. v0.21 and every older section
  are untouched, which matters because v0.21 was never tagged or published and is
  therefore still staged, while v0.20 and older are frozen.
- **Exactly 3 top-level bullets, 0 nested bullets.**
- **341 characters** of bullet body after normalizing whitespace to single spaces
  (351 including the `**v0.22**` heading) — under the 450 limit. Per bullet:
  109 / 121 / 109 characters, two sentences each.
- **No hashes, paths, internal identifiers, or test names/counts/matrices.**
- **No magnitude or frequency words.** Checked for 대폭·훨씬·매우·크게·많이·
  대부분·자주·가끔·항상·거의·종종: none present. (README.ko.md does use "가끔", which
  is fine — §6's ban is scoped to release notes.)
- **Every number is auditable in the release-commit tree.** "6초" ←
  `ROAM_DEFAULTS["look_s"] = 6.0` at `claude_pet.py:5113`, consumed at
  `Roamer._watch` (5249) only when `kind == "approach"`. "한 번 다가와" ← the
  approach target is fixed once at departure (`_begin`) and never recomputed, so
  the pet does not chase the cursor. "세션·주간" ← `roam_summary` takes the first two
  `_label_order`-sorted server rows, or the `("session", "weekly")` pair from the
  estimate.

Claim-by-claim against the source, all confirmed:

| Claim | Source |
|---|---|
| rests in place, approaches when the mouse is moving | `Roamer._plan` requires `_active(now)` and a cursor for the approach branch; `_note`/`_active` with `cursor_move_px` 12 pt per 1 Hz sample, `activity_window_s` 20 s |
| approaches once, watches 6 s, returns | `_begin("approach", …)` fixes the target; `_watch` sets `look_until = now + look_s` (6.0); on expiry `if self.away: self._begin("home")` |
| never walks over the cursor | `_roam_seg_dist(cursor, pos, leg) < radius + cursor_margin_px` → `_stop`, on **both** legs; plus `_plan_approach` stops `approach_stop + radius` short and `_plan_wander` rejects targets near the cursor |
| stops on grab / hover / menu / settings | `hold = (not enabled) or dragging or blocked or busy`; `blocked` = hover or a foreign override; `busy` = settings panel, `menu_open`, `roam_hold`, spike |
| gauges folded while walking | `RoamDisplay.mode`: `if phase in ("out","home"): return DISPLAY_FOLDED` |
| one-line session·weekly summary on arrival | `roam_summary` + `roam_summary_line`; `draw_summary_pill` |
| `≈` on log-estimated values only | `SUMMARY_APPROX = "≈"` (5524), applied in the `estimate` branch; the `exact` branch has no marker |
| `⌄` expands to full gauges | button hit test → `state["roam_toggle"]` → `RoamDisplay.toggle` flips `expanded` while latched → `mode()` returns `DISPLAY_FULL` |
| returns to the previous fold state | `note()` resets the latch on `out`/`home`, and `toggle()` never mutates `show_panel` while latched, so the standing choice survives intact |
| menu toggle labelled "화면 돌아다니기" | `TR["ko"]["menu_roam"]` |
| Reduce Motion stops it | `_reduce_motion()` → `enabled=False`; menu item disabled |
| v0.21's calibration ships in this version | v0.21 was never tagged or published; its section remains directly below |

### 4. README.ko.md

All six claims check out against the source: "가끔 스스로 돌아다님",
"잡거나 메뉴·설정을 열면 그 자리에서 멈춤", "⌄ 버튼", "기본 켜짐", "동작 줄이기", and
"스스로 돌아다닌 자리는 저장하지 않고 드래그해 놓은 자리만 기억함". The right-click
menu line matches the real item order (settings, toggle, roam, reset size, …).

**"가끔" is acceptable here.** AGENTS.md §6's frequency ban applies to release
notes, not to user documentation, and the word is accurate rather than a smuggled
measurement: `rest_min_s`/`rest_max_s` are 45–90 s, `approach_cooldown_s` is 180 s
and `wander_cooldown_s` is 300 s, so the behaviour genuinely is intermittent. The
release notes correctly avoid the word.

One cosmetic note, not a finding: the new "화면 돌아다니기" settings bullet is
separated by blank lines from the list above it, so it renders as its own
single-item list.

### 5. docs-design/quiet-companion.md

**No statement contradicted by the source.** I checked §4's R1–R11 against
`Roamer` line by line (planning order, in-place approach, the segment guard
preceding the bounds check, the single R8 clamp jump, `last_active = -inf`,
`release` semantics, the no-persistence rule), §5's adapter table against the
actual functions and flags, §6 against `RUNTIME`/`apply_config`/
`SETTINGS_OWNED_KEYS`/`TR`, and §9.1–9.3 against `RoamDisplay`, `roam_summary`,
`roam_summary_line`, `roam_fit_text`, `roam_pill_rect`, `roam_frame` and
`roam_logical_center`. Names and signatures match exactly, including
`apply_pill_rows` and `set_override(name, sticky_flag=False)`.

Its SHA256 is `fea117cd02e55c79fba06b4a645226095de621609af7fd9be728cb7f482633da`,
identical to the value recorded in the preceding sign-off, so the document has not
moved since that check. Only F3 below.

### 6. Separation and red-before-green

**Condition A (Developer did not author the gating assertions) — satisfied on the
record.** `tests/test_companion_motion.py` opens with "Owner: Verifier
/root/verifier"; `quiet-companion-verification.md:26` records "Role: independent
Verifier `/root/verifier`; production editor: user-designated Claude;
Coordinator: `/root`", and line 28 lists the test file among that Verifier's
assigned deliverables. The preceding Reviewer sign-off states "I retain only the
Reviewer role and authored no production or gating test change."

**Condition B (Verifier has clean hands on production files) — satisfied on the
record.** Stated twice: "No production file was changed by Verifier" (line 18) and
"No production files edited." (line 28). **This one I take on record rather than
verifying.** The test file is untracked, so `git log` cannot corroborate
authorship or non-authorship for either condition; that is a limit of the evidence
available to me, not a doubt about the claim.

**Red-before-green — genuinely observed, with real failure text.** The record does
not merely assert redness; it preserves the assertion messages, and it
distinguishes API-absence redness from behavioural redness rather than letting the
former stand in for the latter. Sections and one actual message each:

- **"Initial new-feature RED before production edits"** —
  `AssertionError: {'Roamer', 'ROAM_DEFAULTS', 'RoamOut'} is not false : quiet companion API missing: ROAM_DEFAULTS, RoamOut, Roamer`.
  The section itself says this observes only missing API and that "later
  rival/mutation evidence must be reported separately from this initial
  absent-feature RED" — the correct caveat, and the reason the next section exists.
- **"Complete pre-feature source replay for final test cases"** — the final test
  file run against the exact
  `git show 45a03c41b1e2fd3403ce52958a58956e12546086:claude_pet.py` bytes
  substituted in memory, yielding behavioural failures such as
  `AssertionError: Lists differ: [{'x': 550.0, 'y': 450.0}] != []` (the pre-feature
  unconditional `x`/`y` write on every mouse-up).
- **"In-memory rival execution"** — 5 killed of 5 injected rivals, each with its
  unchanged positive control run and passing first, e.g.
  `AssertionError: 40.0 != 10.0 within 6 places (30.0 difference)` and
  `AssertionError: 'look' != 'home'`.
- **"Compact adapter regression RED before second fix"** —
  `AssertionError: '세션 42% · 주간 17%' != '세션 ≈42% · 주간 ≈17%'` (the `≈` marker)
  and `AssertionError: -109.0 not greater than or equal to 17 : summary text overflows the pill's left padding`.
- **"Actual OS Reduce Motion menu RED"** —
  `AssertionError: Lists differ: [True, True] != [False, True]`, the AXEnabled
  regression that produced the `setAutoenablesItems_(False)` correction.
- Further RED sections in the same record: "Observed compact API RED before
  implementation", "Observed native compact behavior RED", "Adapter geometry
  behavioral RED", "Observed behavioral RED: invalid bounds and long interaction",
  "Translation-key collision and completion-cause boundary RED", "Additional
  cooldown RED", "GUI ownership behavioral RED".

**§5 conformance of the prior records' quantitative claims — met.** Each
measurement section states its grouping key ("unittest case ID"; for the mutation
work, "rival implementation paired with its targeted test case"), both window
bounds as absolute UTC timestamps plus a separate "measured" timestamp, the file
set, and raw numerator and denominator rather than a bare percentage: `434 / 441`
passed with `7 / 441` explicit opt-in skips, `51 / 51` focused, `0 / 1315`
visible-bound violations across `1314` adjacent pairs, `5 killed / 5 injected`.
The records also mark their own limits honestly — the native smoke is labelled
synthetic-clock/cursor and kept separate from the actual event-loop runs, and both
records decline to infer distraction or usage accuracy from the GUI's appearance.

### 7. Privacy and publishability of the deliverables

**Clear to publish.** No transcript bodies, no `~/.claude/projects` paths, no
Claude Code session IDs, no credentials and no email addresses appear in
`quiet-companion.md`, `quiet-companion-verification.md`,
`quiet-companion-review.md`, `quiet-companion-arrival.png` or
`tests/test_companion_motion.py`. Item by item, for the three categories that
looked alarming on a first grep:

- **351 `/Users/yeongyu/…` occurrences in the verification record** — 345 are
  traceback frames for `tests/test_companion_motion.py`, 2 for `claude_pet.py`,
  1 for `tests/test_upload_artifact_gate.py`, and 3 are the bare home or repo root.
  These are the repository's own source paths. CLAUDE.md's Privacy rule targets
  paths that encode *project directory names* in Claude Code's transcript tree;
  a repo source path is not that, and the home-directory name is already public
  through the repository's own Developer ID and documentation. **Acceptable.**
- **17 `/var/folders/…` paths, 7 of them carrying a UUID** — the UUIDs are
  `orca-computer-use/<uuid>-screenshot.png` temp filenames written by the QA
  tooling, **not** session identifiers, and the surrounding token is a machine-local
  darwin user-dir name. No rule reaches them. **Acceptable**, though they carry no
  value to a reader (F6).
- **10 "password" hits** — every one is the pre-existing test name
  `test_the_password_database_ignores_our_HOME`, about the Unix passwd database
  (`pwd.getpwuid`). No credential material. **Acceptable.**
- **The QA cursor-coordinate table** records positions of a cursor the harness
  itself drove; it reveals nothing the user typed or read. **Acceptable.**
- **`quiet-companion-arrival.png`** — I viewed it. Pet sprite plus a dark rounded
  pill reading "세션 28% · 주간 27%" on plain white; no other window, chrome or
  filename. It also independently corroborates the exact-mode render path: server
  rows, correctly with no `≈`. **Acceptable**; see F5.
- **`tests/test_companion_motion.py` exceeds the repository's testing policy.** Its
  native smoke installs a `sys.addaudithook` that raises on any `open` of
  `~/.claude`, `~/.claude.json`, `~/.claude_pet.json` or `~/.claude_pet` and on any
  `socket.connect`/`getaddrinfo`, and asserts `HOME`/`TMPDIR`/`ZDOTDIR` all resolve
  inside an explicitly created sandbox. It never touches `LOG_DIRS`.

### Findings, by severity

**F1 — Medium — `README.md`, `README.ja.md` and `README.es.md` describe a
right-click menu that no longer exists.** Line 81 of each still reads
`Settings / Collapse / Reset size / Quit` (and its ja/es equivalents), omitting the
roam toggle that now sits between "Collapse" and "Reset size" in
`rightMouseDown_`'s item tuple. None of the three describes the feature at all,
while `README.ko.md` gained three sections. The app's menu *is* localized in all
four languages (`menu_roam` is present 4×), so this is a documentation gap, not a
product gap. The design document declares it out of scope explicitly
(`quiet-companion.md:318`: "README.md/README.ja.md/README.es.md 는 이 과제의 산출물
목록에 없다(필요하면 별도 배정)"), so it is an unassigned task rather than a defect
by the Developer. `docs/index.html` does not enumerate the menu and needs nothing.
*Recommendation: **fix before the release commit** if a Developer/Verifier pair can
be assigned the three one-line menu corrections — that line is actively wrong now,
whereas the missing feature paragraphs are merely absent. Otherwise defer to a
follow-up and record the decision. Either way, **not a blocker**.*

**F2 — Low — two documents that will be committed link to five artifacts that will
not be.** `quiet-companion-verification.md` and `quiet-companion-review.md` carry
relative Markdown links to `quiet-companion-smoke.json`,
`quiet-companion-smoke.png`, `quiet-companion-compact-smoke.json`,
`quiet-companion-compact-smoke.png` and (verification only)
`quiet-companion-live-contact.png`. None is in the stated commit set, so every one
of those links 404s on GitHub and the §5 backing evidence becomes unreachable to a
reader who follows them. Combined size is ~2.3 MB
(591,719 + 509,897 + 183,713 + 394,617 + 637,216 bytes). I scanned both JSON files:
pure geometry and state metadata, zero `/Users/` or `.claude` strings.
`quiet-companion-live-trace.jsonl` (9,354,299 bytes) is referenced only in prose,
never linked, so it need not be added. All five are named as the Verifier's
assigned deliverables (`quiet-companion-verification.md:28`), so committing them
is within the licensed deliverable set — but staging is the Coordinator's call.
*Recommendation: **add the five paths to the staging list** (my preference: ~2.3 MB
makes the record self-contained), or leave the links knowingly broken. Not a blocker.*

**F3 — Low — `quiet-companion.md` §8's scope counts are understated after §9.**
§8 says the `run_gui()` change is "`state` 키 6개" and "어댑터 함수 6개". After the
second requirement the source carries 13 new `state` keys (`roam_layout`,
`roam_anim`, `roam_hold`, `menu_open`, `reduce_motion`, `roam_release`,
`roam_display`, `roam_env`, `roam_crop`, `roam_rects`, `roam_mode`, `roam_toggle`,
`roam_interrupt`) and more adapter functions than six (`roam_env`, `roam_crop_now`,
`roam_logical_origin`, `roam_env_update`, `roam_mode_now`, `roam_summary_text`,
`draw_summary_pill`, `roam_apply_display` on top of the original set). §9 states
its own scope, so no sentence is false read in isolation; the problem is that §8
presents itself as the change's complete scope table and no longer is. Its *file*
list (claude_pet.py, README.ko.md, quiet-companion.md) remains correct.
*Recommendation: **defer**. A design-note nit with no user-facing effect.*

**F4 — Informational — the release notes do not mention wandering.** `_plan()`
starts a wander leg on `wander_radius > 0 and now >= wander_ok_at` with **no
activity precondition** — only the approach branch requires `_active(now)`. So the
pet also takes short strolls (up to `wander_radius` 160 pt from home, at least
`wander_cooldown_s` 300 s apart, pausing `wander_pause_s` 2 s with no animation)
while the mouse is completely idle. Nothing in the notes is false — bullet 2's
"걷는 동안에는 게이지를 접어 펫만 움직이고" covers how a stroll looks, and
README.ko.md's "가끔 스스로 돌아다님" covers the behaviour — but a user who sees the
pet stroll while reading will find no bullet describing it.
*Recommendation: **leave as written**. A fourth bullet would break the fixed
3-bullet format, and the natural Korean phrasing for "occasionally strolls" reaches
for exactly the frequency vocabulary §6 bans in release notes.*

**F5 — Informational — the arrival screenshot publishes the user's own usage
numbers.** `quiet-companion-arrival.png` shows "세션 28% · 주간 27%". These are the
aggregates the app exists to display, not transcript content, project paths or
session identifiers, so no Privacy rule is engaged. Raised only so the user knows
their own account state at one instant is going into a public repository.

**F6 — Informational — machine-local temp identifiers in the verification record.**
See §7 above. Acceptable to publish; not worth an edit.

### Observed in flight, resolved — not a finding

When I began, the tracked diff repinned both test files to `3a96147a…` /
`7f4e4887…`, the **pre-bump** hashes. Those pins are compared against the *live*
files, which now contain `0.22`, so both gates would have refused to run. While
this review was in progress `verifier-v022` corrected them, and I confirm the
current values are right against the live bytes:

```text
REVIEWED_APP_SOURCE_SHA256  c3d343439c812804154b02ce8cd1959d385c576256a471204af589996e8dcaf9  = claude_pet.py
REVIEWED_VERIFIER_SHA256    8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d  = verify_release_artifact.py
REVIEWED_RELEASE_SHA256     a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  = release.sh (unchanged)
REVIEWED_BUILD_APP_SHA256   83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6  = build_app.sh (unchanged)
```

`tests/test_v021_release_contract.py` is now also modified. Per my assignment I
have **not** reviewed `verifier-v022`'s test changes; that review is a separate
follow-up once the Coordinator says they are complete.

### What I re-verified versus what I took on record

**Re-verified myself, from the tree:** both hash reconstructions; the entire
tracked diff and the mechanical hunk-to-construct mapping; that the estimator,
updater/lock/transaction, seeding and settings contracts are untouched; the
absence of new logging; the `roam` key's default, `apply_config` membership and
`SETTINGS_OWNED_KEYS` non-membership together with the merge semantics that make
that safe; the Reduce Motion call, its 1 Hz cadence and both of its gates,
including the `setAutoenablesItems_(False)` interaction with `vitem` and the pet
submenu; the `nonlocal` declarations that make `roam_env_update()` read fresh
geometry; that `x`/`y` is written only on a real drag and converted to the logical
origin; the greeting, spike, drag and double-click paths; all four translation
tables; the release notes' format, character count, bullet structure,
pure-insertion byte identity and every factual claim; README.ko.md's claims;
`quiet-companion.md` §4/§5/§6/§9 against the source and its SHA against the
previous sign-off; the privacy scan of all five deliverables, including viewing the
PNG; the three stale README lines; and the current SHA pins.

**Taken on record, not independently reproduced:** Conditions A and B — the test
file is untracked, so git cannot corroborate authorship either way; the actual
OS/GUI observations (default-timing approach, the six-second watch, the real
Reduce Motion switch, AXEnabled menu values, PIDs, restoration and handoff), since
I launched no GUI; the focused and full suite results (`51 / 51`, `434 / 441`),
which are §6 item 2 and belong to the Verifier from a clean tree after the release
commit; the native smoke measurements; and the previous Reviewer's historical
checkpoint findings, whose resolution I confirmed by reading the current source
rather than by reproducing the original failures.

### Release-gate reminders for the Coordinator

Not findings against the diff — conditions that follow from AGENTS.md §6 and
CLAUDE.md's release procedure:

- The **execution gate is not yet evaluable**: there is no release commit, so
  there are no trailers and the tracked tree is dirty by design. Nothing from
  step 3 onward — including `./release.sh build` as *the release's* artifact
  build — may begin until §6's five items are recorded.
- **Stage by naming every path, then read back `git diff --cached --name-only`.**
  `git add -A` and `git add .` are forbidden for this commit:
  `git check-ignore diag.py release/ClaudePet.iconset release/icon_1024.png`
  matches none of them, so either command would sweep all three user-owned paths in.
- The **release commit's trailers** must name the user-designated Claude as
  `Developer:` and `/root/verifier` as `Verifier:`, different parties, per §7.
- I am the **Reviewer** on this release and am therefore permanently ineligible to
  be its release operator, as is the Coordinator. No authorization lifts that.

reviewer-v022 (Claude Code subagent, spawned by coordinator-v022, 2026-09-08)

### Follow-up: Verifier test diff

**Verdict: PASS.** No blocking findings. The three test edits are correct,
discriminating, and confined to test files; no production byte moved. Three
informational notes (FU-1 – FU-3) and one carry-over gate step below.

Reviewed `2026-09-08` at `tests/test_v021_release_contract.py` SHA256
`9bb09107e43e4edcd4ca24d35d5daa15eaef4da81acb512139ddb5e14aa956c9`.

**Tree state and production immutability.** `git status --porcelain` shows exactly
the expected set: the Verifier's three files `M`
(`test_v021_release_contract.py`, `test_upload_artifact_gate.py`,
`test_manual_update_transaction.py`) and `docs-design/quiet-companion-verification.md`
still `??`. Re-hashing confirms **no production file changed** since my first review —
`claude_pet.py` `c3d34343…`, `verify_release_artifact.py` `8de85e87…`,
`release.sh` `a5b25686…`, `build_app.sh` `83eca429…`, and
`RELEASE_NOTES.md` `9d56cd60…` / `README.ko.md` `331a63ef…` are byte-identical to the
values I recorded above.

**Repins — all three equal the live bytes.**
`REVIEWED_APP_SOURCE_SHA256` = `c3d34343…` in both harnesses,
`REVIEWED_VERIFIER_SHA256` = `8de85e87…`, and the two pins that should *not* move —
`REVIEWED_RELEASE_SHA256` `a5b25686…` and `REVIEWED_BUILD_APP_SHA256` `83eca429…` —
are untouched and still correct. This closes the in-flight issue I recorded above,
and the Verifier captured the pre-repin state as genuine RED ("Observed RED before
any edit — the v0.21 contract against a v0.22 tree" and "— the two pinned executable
harnesses"), quoting the stale `3a96147a…` / `7f4e4887…` values in the failure output
and confirming both harnesses **fail loudly rather than skip**.

**v0.21 gate intact.** `PUBLISHED_V020_AND_OLDER_SHA256` is unchanged
(`6d734564…`), still pinned from the `**v0.20**` heading through EOF, and
`text.count("**v0.20**") == 1`, `text.count("**v0.21**") == 1`, the
`assertLess(index(v0.21), index(v0.20))` ordering check and the
`split("**v0.21**")[1].split("**v0.20**")[0]` block extraction all survive verbatim.
The one v0.21 edit is that its inline `forbidden` dict moved to module scope as
`FORBIDDEN_NOTE_PATTERNS`; I diffed the six entries line by line and they are
**identical**, so the v0.21 scan discriminates exactly what it did before.

**Version expectations now read 0.22, and strictly.** `APP_VERSION` must be the single
literal `"0.22"`; `--expect-version 0.22` must be present and **both** `0.21` and
`0.20` absent (a strengthening — the previous gate only excluded `0.20`); the newest
heading check became `headings[:2] == ["0.22", "0.21"]`, which pins not just that
v0.22 is newest but that the never-tagged v0.21 stays directly beneath it.

**Format rules match CLAUDE.md step 2.** Exactly 3 top-level bullets, `nested == []`,
`len(bullets) == 3`, whitespace-normalized body `<= 450`, each bullet Korean and
`<= 2` sentences, and the same six-pattern forbidden scan including the
magnitude/frequency list. `_bullet_shape` raises on any non-bullet preamble, so prose
cannot be smuggled in above the bullets.

**Nothing can pass vacuously.** Every entry point raises rather than silently
succeeding when its subject is missing: `_notes_block` on a heading that is absent,
duplicated or out of order; `_bullet_shape` on preamble; `_module_def` when `_watch`
or `roam_summary_line` is missing or duplicated; `_branch_on` when the keyed branch is
gone; `_literal_assignments`/`_one_literal_string` when the constant is absent or no
longer a literal. `setUp` itself calls `_notes_block`, so a missing v0.22 section
errors all three of that class's tests rather than passing them.

**I/O surface.** Imports are `ast`, `hashlib`, `re`, `unittest`, `pathlib` and nothing
else; the only `os.` occurrence in the file is inside a regex *string*. All six paths
are tracked repo files under `REPO`. No home directory, no network, no subprocess, no
shell, no GUI, no installed-bundle inspection.

**I ran the module and then attacked it.** On the live tree: `10 / 10` OK in 0.142 s.
I then copied `claude_pet.py`, `verify_release_artifact.py`, `RELEASE_NOTES.md`,
`CLAUDE.md` and the three test files into an isolated scratch tree (control: `10 / 10`
OK) and injected rivals there, one at a time, restoring between each. The repository
was never modified — I re-hashed `claude_pet.py`, `RELEASE_NOTES.md` and
`test_v021_release_contract.py` afterwards and all three are unchanged.

**`18 / 18` rivals observed RED**, independent of the Verifier's own 25:

| # | Rival | Result |
|---|---|---|
| 1 | source `look_s` 6.0 → 8.0, notes untouched | RED `8.0 != 6.0 : ROAM_DEFAULTS["look_s"] is 8.0; the v0.22 notes promise 6 seconds` |
| 2 | notes "6초" → "8초", source untouched | RED `8.0 != 6.0 : notes say 8초 but ROAM_DEFAULTS["look_s"] is 6.0` |
| 3 | both changed to 8 consistently | RED (see FU-1) |
| 4 | `look_s` / `wander_pause_s` swapped in `Roamer._watch` | RED `'look_s' not found in {'review', 'wander_pause_s'}` |
| 5 | `SUMMARY_APPROX` added to the exact branch | RED `'SUMMARY_APPROX' unexpectedly found …` |
| 6 | `menu_roam` removed from the `ja` locale | RED `Lists differ: ['ja'] != []` |
| 7 | fourth top-level bullet | RED `4 != 3` |
| 8 | nested bullet added | RED `Lists differ: ['  - 중첩된 항목입니다.'] != []` |
| 9 | extra sentences appended to a bullet | RED `10 not less than or equal to 2` |
| 9b | body pushed past 450 with **no** new sentence | RED `509 not less than or equal to 450` |
| 10 | magnitude word `훨씬` inserted | RED `remove unsupported magnitude/frequency: '훨씬'` |
| 11 | the `≈` sentence deleted | RED `say ≈ marks log-estimated values` |
| 12 | `APP_VERSION` reverted to `0.21` | RED (version + all three pins) |
| 13 | upload-gate pin reverted to `e26e0f63…` | RED `pins e26e0f63…, final source is c3d34343…` |
| 14 | a line inserted into the published v0.20 bytes | RED `'5a8006ba…' != '6d734564…'` |
| 15 | `RUNTIME["roam"]` default flipped to off | RED `unexpectedly None : RUNTIME["roam"] must default on …` |
| 16 | `accessibilityDisplayShouldReduceMotion` call removed | RED `not found in …` |
| 17 | v0.21 heading moved above v0.22 | RED `Lists differ: ['0.21', '0.22'] != ['0.22', '0.21']` |

Rivals 9 and 9b are listed separately on purpose. My first attempt to breach the
450-character limit appended whole sentences, so it went red on the `<= 2 sentences`
rule and never exercised the character check at all — a non-discriminating probe of my
own making, not of the test's. Re-running it with a long clause carrying no sentence
terminator drove the character assertion directly (`509 not less than or equal to 450`),
which is what actually confirms that rule discriminates.

**The `look_s` ↔ "6초" cross-check is genuinely bidirectional** — the specific question
asked. Rivals 1 and 2 are the two one-sided edits and both go red, so neither the
constant nor the sentence can drift alone. Rival 4 additionally rules out the wrong
implementation that would keep `look_s == 6.0` while making the sentence false: moving
the six-second dwell onto the wander pause. The `assertEqual(len(stated), 1)` guard
also stops a second duration being introduced into the notes unnoticed.

**Verification record (§5).** The new section
`## v0.22 release — pre-commit verification` meets the standard. It carries the command
verbatim (`python3 -m unittest discover -s tests -v 2>&1 | tee <scratch>/full_suite.txt`),
absolute UTC start and end (`2026-09-08T11:42:34Z` – `11:47:57Z`), the grouping key
("one unittest discovered test case"), the enumerated 16-file set, and raw numerator and
denominator — `441 / 448` passed, `7 / 448` skipped, `0 / 448` failures, `0 / 448`
errors — with the `+7` denominator shown to be exactly the seven new cases against the
previous `434 / 441` baseline. The figures appear as **raw output**, not only as prose:
the `Ran 448 tests in 322.224s` / `OK (skipped=7)` block is quoted verbatim, as are the
ten `test_v021_release_contract` case lines, all seven skip reasons, and the pre-edit
RED tracebacks. The mutation work is likewise raw, one `-> RED` line per mutant,
`25 / 25` observed RED with `0` non-discriminating and the runner named. Scope limits
are stated rather than implied: no GUI launched, no build or release script invoked, no
process killed, no git write, no `CLAUDEPET_RUN_LIVE_*` set, nothing written to
`~/.claude_pet*` or `~/.claude`.

#### Notes

**FU-1 — informational — the look-duration test is deliberately over-pinned.**
Alongside the cross-check it also asserts `float(look_s) == 6.0` literally, so rival 3
— source *and* notes changed consistently to 8 — still goes red. For a gate on *this*
release's notes that is correct and the failure message says exactly what to change.
Flagging it so that whoever retunes `look_s` in a later release knows this test must be
updated too, and does not read its failure as a defect.

**FU-2 — informational — `test_reduce_motion_and_the_roam_default_are_where_the_notes_say`
proves reference, not behaviour.** It is a bare substring search for
`accessibilityDisplayShouldReduceMotion` plus a regex for the `RUNTIME["roam"]` default
literal. It would still pass if the call existed but were never wired to `enabled`.
That is the right scope for a release-notes claim gate — the behavioural coverage lives
in `tests/test_companion_motion.py` and in the Verifier's actual-OS Reduce Motion run —
but the assertion message ("the notes promise macOS Reduce Motion is honoured") reads
stronger than what the check establishes. No change requested; recorded so nobody later
mistakes this gate for the behavioural one. Rivals 15 and 16 confirm it does catch
removal of either the call or the default.

**FU-3 — my earlier F2 is resolved as a documented decision, not a repair.** The new
section "Artifacts referenced but intentionally not committed" lists all six QA captures
with sizes and SHA-256s, and separates the measurement from the Coordinator's staging
decision. Two of the hashes match values I recorded independently
(`quiet-companion-arrival.png` `a8e3a553…`, the frozen trace `1829600a…`). The Markdown
links in both committed records still resolve to nothing on GitHub, but a reader who
follows a dead link now finds the provenance table in the same document, which is a
reasonable resolution. I withdraw F2 as an open finding.

**FU-4 — informational — the shared forbidden-pattern dict cuts both ways.** The module
docstring says the *structural* helpers are deliberately not shared between the v0.21
and v0.22 gates, while the forbidden *patterns* now are. That asymmetry is defensible —
data versus logic, and adding a pattern only tightens both gates. But the finished v0.21
gate now depends on a constant a future release may edit, so **loosening**
`FORBIDDEN_NOTE_PATTERNS` would silently weaken it. Today the entries are byte-identical
to what v0.21 shipped with, so nothing has changed; this is a note for the next editor.

#### Carry-over gate step

The full suite was run from a **dirty tracked tree**, which is correct at this phase —
the release commit does not exist yet. §6 item 2 still requires the Verifier to re-run
the suite **from the clean tree after the release commit** and record that command and
output. This follow-up does not satisfy it, and the `441 / 448` figures above are
preparation-phase evidence, not the execution gate.

reviewer-v022 (Claude Code subagent, spawned by coordinator-v022, 2026-09-08)

### Follow-up: README en/ja/es (F1) diff

**Verdict: PASS. F1 is closed.** The three locale READMEs now mirror README.ko.md
exactly, no claim was added or dropped, every menu label equals its `TR` string, and
every Reduce Motion setting name matches what macOS itself ships. No blocking findings;
four observations and one cosmetic nit, none requiring a change.

**Production files did not move.** Re-hashed after the edit:
`claude_pet.py` `c3d343439c812804154b02ce8cd1959d385c576256a471204af589996e8dcaf9`,
`verify_release_artifact.py` `8de85e87…`, `RELEASE_NOTES.md` `9d56cd60…` — all identical
to the values recorded earlier in this section. `README.ko.md` is also byte-unchanged at
`331a63ef…`, so the Developer mirrored *from* it without re-touching it.

**Scope — exactly three regions per file, at identical offsets in all four locales.**
I compared each file against `git show HEAD:<file>` with line-level opcodes rather than
reading the patch, which is the check that can actually rule out an incidental edit
elsewhere. Every file yields precisely three non-equal regions and nothing else:

| Region | Operation | en | ja | es | ko (reference) |
|---|---|---|---|---|---|
| behaviour bullets | `insert` at HEAD[70:70] | +4 | +4 | +4 | +4 |
| right-click menu line | `replace` HEAD[80:81] → cur[84:85] | −1 +1 | −1 +1 | −1 +1 | −1 +1 |
| settings paragraph | `insert` at HEAD[96:96] | +3 | +3 | +3 | +3 |

Identical structure, identical line numbers, one replaced line each (the menu), and the
`+3` includes the trailing blank line in every locale. Nothing outside these three
regions differs in any of the four files.

**Fidelity — all fourteen of README.ko.md's claims survive in all three locales.**
Checked claim by claim rather than paragraph by paragraph:

| # | ko claim | en | ja | es |
|---|---|---|---|---|
| 1 | roams on its own occasionally | now and then | ときどき | de vez en cuando |
| 2 | normally rests in place | rests in place | 普段はその場で休み | descansa en su sitio |
| 3 | approaches once while the mouse is moving | walks over once | 一度近づいて | se acerca una vez |
| 4 | watches briefly | watches for a moment | しばらく見つめて | mira un momento |
| 5 | returns to its place | and returns | 元の場所へ戻る | y vuelve |
| 6 | never walks over the cursor | never walks onto the cursor | カーソルの上には歩いて行かず | Nunca camina sobre el cursor |
| 7 | stops in place on grab / menu / settings | stops where it is … | その場で止まる | se detiene donde está … |
| 8 | folds the gauges while walking, only the pet moves | ✓ | ✓ | ✓ |
| 9 | on arrival, one-line session·weekly % summary | ✓ | ✓ | ✓ |
| 10 | ⌄ expands the full gauges | ✓ | ✓ | ✓ |
| 11 | on return, restores the prior fold state | ✓ | ✓ | ✓ |
| 12 | toggled by the right-click check item, on by default | ✓ | ✓ | ✓ |
| 13 | macOS Reduce Motion stops it moving | ✓ | ✓ | ✓ |
| 14 | autonomous positions not saved, dragged position remembered | ✓ | ✓ | ✓ |

Nothing was added either — no locale asserts anything README.ko.md does not.

**Menu wording equals each locale's `menu_roam` verbatim.** Read out of `claude_pet.py`'s
`TR` tables and compared against the rendered menu line:

| Locale | `TR[lang]["menu_roam"]` | README menu line contains |
|---|---|---|
| en | `Roam the screen` | `Roam the screen (on/off)` |
| ko | `화면 돌아다니기` | `화면 돌아다니기(켜기·끄기)` |
| ja | `画面を歩き回る` | `画面を歩き回る（オン・オフ）` |
| es | `Pasear por la pantalla` | `Pasear por la pantalla (activar/desactivar)` |

Each is the exact `TR` string with a parenthetical toggle hint appended — the pattern
README.ko.md already established. The item's position in the list (after Collapse,
before Reset size) matches `rightMouseDown_`'s item tuple in every locale, and the
settings paragraph re-uses the same localized label as its own heading.

**Reduce Motion names — verified against macOS, not assumed.** I expected to have to
hedge here, but the strings are readable on this machine, so this is evidence rather
than recollection. From
`/System/Library/ExtensionKit/Extensions/AccessibilitySettingsExtension.appex/Contents/Resources/`
on macOS `26.5.2` build `25F84`, key `display.reduceMotion` in `Localizable.loctable`
and `CFBundleDisplayName` in `InfoPlist.loctable`:

| Locale | macOS pane name | macOS `display.reduceMotion` | README writes |
|---|---|---|---|
| en | `Accessibility` | `Reduce motion` | "macOS Accessibility **Reduce Motion**" |
| ko | `손쉬운 사용` | `동작 줄이기` | "macOS 손쉬운 사용의 **동작 줄이기**" |
| ja | `アクセシビリティ` | `視差効果を減らす` | "macOS アクセシビリティの**視差効果を減らす**" |
| es | `Accesibilidad` | `Reducir movimiento` | "en Accesibilidad de macOS está activado **Reducir movimiento**" |

ko, ja and es are character-for-character correct, pane name included. The Japanese one
was the entry most worth checking, since `視差効果を減らす` ("reduce the parallax
effect") is not a literal translation of "Reduce motion" and a plausible-looking
invention such as `動きを減らす` would have sent users hunting for a setting that does not
exist. It is Apple's actual string. This also confirms the app is naming the right
control: `_reduce_motion()` reads `accessibilityDisplayShouldReduceMotion()`, which is
the toggle this key labels, and it lives under Accessibility → Display as the READMEs say.

**Language quality.** No mistranslation, and no sentence whose meaning diverges from the
Korean. Spanish keeps grammatical gender consistent with the file's existing feminine
"la mascota" (`la agarras`, `la dejas`, `arrastrarla`) and uses the progressive
"cuando el ratón se está moviendo" for ko's "움직이고 있으면", which is the right aspect —
the condition is that the mouse *is moving*, not that it moved once. English reads
naturally. All three preserve the house style of the surrounding bullets: no trailing
period on a bullet, sentence periods inside it, and the same bold-lead-in shape.

**Frequency wording is acceptable and accurate.** "now and then" / "ときどき" /
"de vez en cuando" render ko's "가끔". Under the reasoning recorded earlier in this
section, AGENTS.md §6's magnitude/frequency ban is scoped to *release notes*; these are
user documentation, and the release notes themselves remain free of such wording —
`RELEASE_NOTES.md` is byte-unchanged. The characterization is also true rather than a
smuggled measurement: `rest_min_s`/`rest_max_s` put 45–90 s between decisions,
`approach_cooldown_s` is 180 s and `wander_cooldown_s` is 300 s, so at most one approach
per three minutes and one stroll per five, and only when the rest timer has expired with
no interaction holding it. No quantity is asserted, so no §5 backing record is owed.

**No test impact.** `tests/test_v021_release_contract.py` reads only `claude_pet.py`,
`verify_release_artifact.py`, `RELEASE_NOTES.md`, `CLAUDE.md` and the two pinned
harnesses — no README — so the forbidden-pattern scan that rejects `가끔` cannot see these
files. Re-ran the gate after the edit: `10 / 10` OK.

#### Observations (none is a finding)

**FR-1 — English casing.** macOS ships `Reduce motion`; README.md writes
`Reduce Motion`. One character, in a phrase already bolded as a proper name. Mentioned
only because I had the localization table open; I do not recommend an edit.

**FR-2 — en and es are slightly *more* precise than ko and ja on claim 11.** ko says
"평소에 접어 두었던 대로 되돌아감" and ja mirrors it ("普段畳んでいた状態に戻る"), which reads
as "returns to the folded state you had". en and es say "whatever you had collapsed **or
expanded**" / "lo que tenías plegado **o desplegado**". The source supports the wider
phrasing: `RoamDisplay.reset()` clears the latch and `mode()` then returns
`DISPLAY_FULL if show_panel else DISPLAY_FOLDED`, so a user who normally keeps the panel
open gets it back open. en/es add precision rather than a claim, and ko/ja are looser but
not false. I do not recommend changing ko or ja. Flagging it in case the concurrent
claims-vs-source check reads this as a ko↔en divergence: it is the English that is right,
and the Korean is not wrong.

**FR-3 — the exclusive particle is kept in ja, dropped in en/es.** ko "요약**만** 작게"
and ja "サマリー**だけ**を小さく" say *only* the summary is shown; en "a small one-line
summary" and es "un pequeño resumen" omit the "only". A nuance, not a claim — nothing
false results, since neither says anything else is shown.

**FR-4 — a Japanese style nit, explicitly not a claim error.** "つかんだりメニュー・設定を
開くと" uses a single 〜たり without its usual pair. It is ordinary in casual writing and
the meaning ("if you grab it, or open the menu or Settings") is unambiguous. Recording it
only so a later reader does not mistake it for a mistranslation.

**Carry-over — the cosmetic list break is now uniform.** The settings bullet sits after a
blank line, so it renders as its own single-item list. I noted this for ko earlier; the
mirror reproduces it identically in all four files, which is at least consistent. No
action.

#### Consequence for staging

The release commit's named-path list grows by three: `README.md`, `README.ja.md` and
`README.es.md` join `README.ko.md`. `docs/index.html` is unaffected — it never
enumerated the right-click menu, so nothing on the site is now stale.

reviewer-v022 (Claude Code subagent, spawned by coordinator-v022, 2026-09-08)

### Follow-up: release-notes bullet 3 wording (execution gate)

**Verdict: PASS.** The edit is one line, it removes a genuine defect that would have
reached every reader of the GitHub release, the replacement sentence is true against both
the source and the v0.21 section it summarizes, and the block still satisfies CLAUDE.md
step 2. No findings. This is a §6 item 3 re-check of the release notes only; it changes
nothing else I have signed off, and it does not by itself make the execution gate GREEN.

**The defect was real, and it was invisible in the file.** `release.sh`'s
`gen_release_notes()` prints the preamble, then the changelog heading, then keeps lines
only while `keep=(trim($0)==ver)` — so the GitHub release body contains the `**v0.22**`
block and nothing below it. Reading `RELEASE_NOTES.md` in the repository, "아래 v0.21의
% 보정 설정도…" points at a section sitting immediately underneath; in the body users
actually receive, it pointed at nothing. That is the kind of error only reproduction
catches, which is why item 4 below matters more than re-reading the sentence.

**(1) Scope — exactly one line, published bytes untouched.** Line-level opcodes against
`HEAD:RELEASE_NOTES.md` give **one** non-equal region, `replace HEAD[84:85] -> cur[84:85]`,
and nothing else anywhere in the file:

```text
- - 우클릭 메뉴의 "화면 돌아다니기"로 끄고 켤 수 있고, macOS 손쉬운 사용의 동작 줄이기가 켜져 있으면 움직이지 않습니다. 아래 v0.21의 % 보정 설정도 이 버전에 함께 들어 있습니다.
+ - 우클릭 메뉴의 "화면 돌아다니기"로 끄고 켤 수 있고, macOS 손쉬운 사용의 동작 줄이기가 켜져 있으면 움직이지 않습니다. v0.21로 준비했던 % 보정 설정(세션·주간·모델 게이지를 Claude 앱에 보이는 %로 맞추기)도 이 버전에 함께 들어 있습니다.
```

The frozen regions are byte-identical, checked by hash rather than by eye:

| Region | HEAD | working tree |
|---|---|---|
| `**v0.20**` heading count | 1 | 1 |
| v0.20-and-older suffix (heading → EOF) | `6d73456411eac4d7b2aa9b7556bb185fc43f84417ce8e91969dd8b91caf52ee1` | identical |
| v0.21 block (between its heading and `**v0.20**`) | `ce349dbbe513cbaccdf07340fb239c5f46a9bf1086a2ab14e5dfad50efe07f4c` | identical |

The suffix hash is exactly the value `PUBLISHED_V020_AND_OLDER_SHA256` pins, so the
published-bytes gate is untouched. Only `RELEASE_NOTES.md` is modified in the tree.

**(2) CLAUDE.md step 2 — still satisfied.** 3 top-level bullets, 0 nested, **379 / 450**
normalized characters (confirming the Developer's figure), 2 sentences in each bullet
(bullet lengths 109 / 121 / 147). The six forbidden-pattern classes were re-scanned over
the new text: **no hits** — no hash, source path, line reference, internal identifier,
test prose, or magnitude/frequency word. The only numeral added is a version string.

**(3) Truthful, and natural without the deictic.** The sentence makes three claims and
each holds:

- *"v0.21로 준비했던"* — v0.21 was committed as `45a03c4` but never tagged or published,
  so it was prepared and not shipped. True.
- *"% 보정 설정(세션·주간·모델 게이지를 Claude 앱에 보이는 %로 맞추기)"* — a faithful
  compression of the v0.21 section's own first bullet, "세션·주간·모델 3개 게이지를
  Claude 앱에 보이는 %로 보정합니다", and correct against the source: `GAUGE_LIMIT_KEYS`
  is exactly the three pairs session/weekly/opus, whose Korean panel labels are
  세션 한도 / 주간 한도 / 모델 한도, and the calibration input is the percentage the user
  reads in Claude's own usage screen.
- *"도 이 버전에 함께 들어 있습니다"* — true for the same reason v0.21 is unpublished.

It reads naturally in Korean and, unlike the original, is self-contained: nothing in it
refers to a location in a document the reader may not have. The parenthetical is a gloss
in the same explanatory register the v0.21 section already uses.

**(4) Regenerated body, reproduced without sourcing or executing `release.sh`.** I copied
the `awk` program out of `gen_release_notes()` into a scratch script with
`ver='**v0.22**'` and ran it over both files. `release.sh` was never sourced, dispatched,
or executed — which matters here, because sourcing it is precisely the move the
`ZSH_EVAL_CONTEXT` guard exists to make inert, and reaching for it to test one helper is
the documented trap.

Against the committed bytes the changelog part of the body ended:

```text
- 우클릭 메뉴의 "화면 돌아다니기"로 끄고 켤 수 있고, macOS 손쉬운 사용의 동작 줄이기가 켜져 있으면 움직이지 않습니다. 아래 v0.21의 % 보정 설정도 이 버전에 함께 들어 있습니다.
```

— with no v0.21 section anywhere beneath it. Against the working tree, the changelog part
of the generated body is now, verbatim:

```text
### 📝 변경 내역 / Changelog
**v0.22**
- 펫이 제자리에서 쉬다가 마우스가 움직이고 있으면 한 번 다가와 6초 바라보고 제자리로 돌아옵니다. 커서 위로는 걸어가지 않고, 잡거나 마우스를 올리거나 메뉴·설정을 열면 그 자리에서 멈춥니다.
- 걷는 동안에는 게이지를 접어 펫만 움직이고, 다가와서는 세션·주간 %를 한 줄로 요약해 보여 주며 로그 추정치에는 ≈가 붙습니다. ⌄ 버튼을 누르면 전체 게이지가 펼쳐지고, 돌아오면 접어 두었던 대로 되돌아갑니다.
- 우클릭 메뉴의 "화면 돌아다니기"로 끄고 켤 수 있고, macOS 손쉬운 사용의 동작 줄이기가 켜져 있으면 움직이지 않습니다. v0.21로 준비했던 % 보정 설정(세션·주간·모델 게이지를 Claude 앱에 보이는 %로 맞추기)도 이 버전에 함께 들어 있습니다.
```

Three bullets, no dangling reference, and the calibration work is described where the
reader can see it rather than pointed at.

**(5) No other file moved.** `claude_pet.py` is still
`c3d343439c812804154b02ce8cd1959d385c576256a471204af589996e8dcaf9`, and
`git status --porcelain` shows `M RELEASE_NOTES.md` as the only tracked modification.

**Gate re-run.** `tests/test_v021_release_contract.py`: `10 / 10` OK after the edit. The
three assertions this sentence could have broken all still hold — the `_has_all` clause
requiring `v0.21` together with `보정` and one of 함께/같이/포함/들어, the `<= 450`
character limit at 379, and the "exactly one duration in seconds" check, since the new
clause introduces no `초`.

**Consequence for the release commit.** The v0.22 release commit `7865af5d` carries
`RELEASE_NOTES.md` at `9d56cd60…`; this fix supersedes those bytes, so the follow-up
commit that carries it must be in place before anything generates the release body. The
§6 item 3 finding "release notes checked" now attaches to the corrected file, not to the
bytes in `7865af5d`.

reviewer-v022 (Claude Code subagent, spawned by coordinator-v022, 2026-09-08)
