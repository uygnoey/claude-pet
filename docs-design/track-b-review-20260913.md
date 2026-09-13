# Review record — Track B "Start at sign-in", macOS half (v0.25 follow-ups)

Reviewer: reviewer-b (Claude), REVIEWER role only on this track; independent of the
Developer and of verifier-b. Worktree `/Users/yeongyu/claude-pet-autostart`, branch
`autostart`, HEAD `13710db` — not `/Users/yeongyu/claude-pet`. This file is untracked and
was created by the Reviewer; the Coordinator stages by named paths.

Inputs: AGENTS.md §2 / §3 / §5; CLAUDE.md (Danger zone, Privacy, and the new "Start at
sign-in" section in the diff); `docs-design/followups-v025-plan-20260913.md` § "Track B"
(read in `/Users/yeongyu/claude-pet`); the survey report key `autostart` in the session
scratchpad `followups-survey.json`; the Verifier's record
`docs-design/track-b-verification-20260913.md` (§1–§10, read in full);
`git diff -- claude_pet.py setup.py CLAUDE.md`; `tests/test_autostart.py` (read in full).

Not done, by instruction: no git write command; nothing registered with or unregistered
from the real `SMAppService` (every probe ran under a `sys.modules["ServiceManagement"]`
tripwire installed before `claude_pet` was imported); `~/.claude_pet.json` neither read
nor written (`HOME` and `CONFIG_PATH` redirected to a temp directory in the probe); the
GUI not run; no untracked file touched other than this one, which the Reviewer created;
`REVIEWED_APP_SOURCE_SHA256` not re-pinned. All commands ran with cwd at the worktree
root. Times are UTC. Output blocks are verbatim.

## Review round 1 (02:43–02:50Z, 2026-09-13)

### Verdict: PASS — no blocking items

### 1. The tree reviewed is the tree the Verifier recorded GREEN on

```
$ git status --porcelain
 M CLAUDE.md
 M claude_pet.py
 M setup.py
?? docs-design/track-b-verification-20260913.md
?? tests/test_autostart.py
$ shasum -a 256 tests/test_autostart.py claude_pet.py setup.py CLAUDE.md
6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2  tests/test_autostart.py
0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0  claude_pet.py
5719a2077b2f25f84d5e73f519a6efd7c8294c25550ed7d5eadfb6a38a9599d6  setup.py
c5f2bcbea869c4a0577e915cdf415d94ecdda2f489e0fa5a4095664f9e00aec8  CLAUDE.md
```

All four digests equal the ones in the Verifier's §10 (round 2) block. `git diff --stat`:
CLAUDE.md +64, claude_pet.py +230 −1, setup.py +4 −2; no other tracked file changed.

Modification times (UTC, from `stat -f %m`): `tests/test_autostart.py` 01:57:06 (the
minute of the red run in the record's §3), `setup.py` 02:06:01, `claude_pet.py` 02:26:30,
`CLAUDE.md` 02:28:14, verification record 02:41:27.

### 2. AGENTS.md §2 — Developer–Verifier separation

- **Condition A (Developer does not touch gating assertions).** The gating module's
  SHA256 today (`6de0e056…`) is byte-identical to the digest the record's §3 red run was
  taken against and to the §8 / §10 green runs; its mtime (01:57:06Z) predates every
  production edit. No assertion, fixture or fixture order changed after red. The round-2
  fix for the `test_companion_motion` `NameError` was production-side (the
  `state["autostart_read"]` hook); `tests/test_companion_motion.py` is byte-identical to
  HEAD per the record's §10 hashes (`f6404f64…` both ways) — checked: it is not in
  `git status`. **Holds.**
- **Condition B (Verifier has clean hands on production files).** The record states the
  Verifier wrote only `tests/test_autostart.py` and the record; the production edits all
  postdate the red run and the record's own hashes track them round by round. From an
  uncommitted tree authorship is not provable by the Reviewer; it is consistent with every
  artefact available, and the §7 trailers on the eventual commit are where it becomes
  checkable. **No contrary evidence; treated as holding.**
- **Condition C.** No exception declared; none needed.

### 3. AGENTS.md §3 — red before green

- Red run recorded verbatim (§3 of the record) with `claude_pet.py` at `6f95bc8b…` =
  `git show HEAD:claude_pet.py`, re-hashed before, during and after: 28 tests,
  27 FAIL, 1 ok, `exit=1`, with each assertion message (missing names, `[None, None,
  None, None]` locale rows, the seven-item menu list, `['Foundation', 'AppKit',
  'Quartz']`).
- The one test green at HEAD (`test_no_config_key_exists_for_the_feature`, an absence
  guard) has its red shown by rival injection in §4 (`R8 key in owned/apply_config →
  FAIL`) — the scratch-copy form §3 asks for when the pre-fix state is green by nature.
- The §4 discrimination table shows every rival R1–R11 failing at least one test and the
  reference passing all 19 pure tests; the fixtures are tables (4 × 2 status table, both
  R8 rows, the 0/1/2/3 uninstall rows), not single values. The non-discriminating
  `test_menu_title_fits_the_menu` (vacuous pass with no key) was caught and corrected
  before the red run, and the correction is recorded.
- Round-2 red/green pair: the §9 verbatim `NameError: name 'app_bundle_path' is not
  defined` against `6e9f76eb…`, then 51/51 against `0cd17cef…` with the test file unchanged.

**Holds.** Nothing is presented as red-before-green without an observed red.

### 4. AGENTS.md §5 — evidence standard in the record

Every count carries its denominator and its arithmetic (575 = 593 − 18 not-run,
57 = 48 + 8 + 1, 565 baseline + 28 = 593), each run has start/end timestamps in UTC,
the file set is the worktree root, and the full logs the record cites exist in the
session scratchpad (checked with `ls`: `rivals_check.py`, `full-suite-red-stage.txt`,
`track-b-full-suite-round1.log`, `track-b-full-suite-round2.log`, `round2_ast_check.py`,
`round2_hook_check.py`, `companion_scope_check.py`, `baseline-full-suite.log`,
`baseline-13710db/`). Source facts are cited as source facts; the one thing the
Verifier did not check (the Developer's stated reason for the Spanish label) is labelled
as unchecked. **Holds.**

### 5. Design points (plan § Track B, survey "autostart"), each read from the diff

| point | where | verdict |
| --- | --- | --- |
| Checkable item right after "Roam the screen", before "Reset size" | `rightMouseDown_` tuple list: settings, toggle, roam, **autostart**, reset_size, sep, uninstall, quit; Pets submenu `insertItem_atIndex_(pet_item, 5)` = index(reset_size)+1, comment still "after Reset size" | OK |
| OS state is the source of truth, no config key | checkmark from `state["autostart_read"]` → `autostart_read_state(*autostart_current())` on every right-click; nothing added to `RUNTIME`, `apply_config`, `SETTINGS_OWNED_KEYS`; `ConfigGuard` rows green; a System Settings change is re-read, never re-applied | OK |
| `SMAppService.mainAppService()`; `status()` → checkmark; register/unregister on click | `autostart_service()` is the sole `mainAppService` site (AST-pinned); `autostart_toggle` off→`registerAndReturnError_(None)`, on→`unregisterAndReturnError_(None)`, new state read back | OK |
| `RequiresApproval` → alert with a button calling `openSystemSettingsLoginItems()` | `Handler.toggleAutostart_`: on `"approval"` an `NSAlert` with `autostart_approval`, first (default) button `autostart_open_settings` → `autostart_open_login_items()`, second `unin_cancel`; `1000` = first button. Register landing on 2 also reaches it because the state is read back | OK |
| Gated on `app_bundle_path()`; from source or macOS 12 the item is disabled with `autostart_unavailable` | `autostart_current()` → `(None, False)` from source without calling the service; `autostart_service()` → `None` when the import or the class is missing; menu branch sets title `autostart_unavailable` and `setEnabled_(False)`; `setAutoenablesItems_(False)` already keeps it disabled | OK |
| `do_uninstall()` unregisters before its irreversible section | `uninstall_autostart(autostart_service())` inside `if app:` after `_path_ident_str` and before `subprocess.Popen`; truthy error → `(False, err)` with nothing deleted; docstring step 2½; `uninstallApp_` appends `autostart_fail` to `unin_fail` | OK |
| `setup.py` includes `ServiceManagement` | `"includes": ["Foundation", "AppKit", "Quartz", "ServiceManagement"]` | OK (see N1) |
| Six TR keys in en/ko/ja/es | all six in all four blocks; pairwise distinct across locales and the four messages distinct within each; `menu_autostart` 1–24 chars in every locale; all six used through `t()` | OK |
| Pure helpers take the service as a parameter | `autostart_state`, `autostart_read_state`, `autostart_toggle`, `uninstall_autostart` all take `service` / `is_bundle`; tests pass fakes | OK |
| Privacy | the two `_dbg` lines log a state word and `_autostart_err_summary(err)` = `domain/code` or the exception type name; no `localizedDescription`, no path, no message text | OK |
| Settings panel untouched | no change to `open_settings`, `PWID/PHT`, `plan_settings_save` | OK |

CLAUDE.md's new section was read against the code sentence by sentence: the call-site
claims (`mainAppService` only in `autostart_service`; `(None, False)` from source; `0`/`3`
read `status()` and stop; the hook shape and the missing-hook default; the Pets index)
all match the diff. The repo-layout row for `tests/test_autostart.py` is accurate.

### 6. macOS 12 / missing-framework probe — the menu path cannot raise

Scratch `reviewb_macos12_sim.py` (session scratchpad, not in the repository): the
tripwire module is installed in `sys.modules` before `claude_pet` is imported;
`app_bundle_path` is patched to a string (`/Applications/ClaudePet.app`, never touched)
to model an installed bundle; the `elif action == "toggleAutostart:"` body is extracted
from `rightMouseDown_` by AST and `exec`'d against a recording `mi` and a hand-built
`state`, with the real `t`.

```
$ python3 <scratchpad>/reviewb_macos12_sim.py ; echo "exit=$?"
== hook / toggle under each shape ==
  12: import fails (module None), bundle     hook='unavailable' toggle=('unavailable', None)
  12: module without SMAppService, bundle    hook='unavailable' toggle=('unavailable', None)
  mainAppService raises, bundle              hook='unavailable' toggle=('unavailable', None)
  status() raises, bundle                    hook='unavailable' toggle=('unavailable', None)
  source: framework present, no bundle       hook='unavailable' toggle=('unavailable', None)
  source: service calls made                 []
  source: framework missing, no bundle       hook='unavailable' toggle=('unavailable', None)
== menu branch (exec of the elif body) ==
  hook missing (window-less test state)      [('title', '로그인 시 자동 실행 (여기서는 사용 불가)'), ('enabled', False)]
  hook -> unavailable                        [('title', '로그인 시 자동 실행 (여기서는 사용 불가)'), ('enabled', False)]
  hook -> off                                [('state', 0)]
  hook -> on                                 [('state', 1)]
  hook -> approval                           [('state', -1)]
  hook = real lambda, macOS 12, bundle       [('title', '로그인 시 자동 실행 (여기서는 사용 불가)'), ('enabled', False)]
real config touched: False
exit=0
```

No shape raised; from source the fake service received zero calls (`status()` included);
the tripwire never fired. (`from ServiceManagement import SMAppService` on macOS 12 goes
through PyObjC's lazy `__getattr__`, which raises `AttributeError` → `ImportError`; both are
caught by `autostart_service()`'s `except Exception`.)

### 7. Full suite re-run (this Reviewer)

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"     # cwd = worktree root
2026-09-13T02:43:17Z … 02:47:41Z  (log: session scratchpad reviewb-suite.log)
Ran 575 tests in 263.314s
FAILED (failures=49, errors=8, skipped=8)
exit=1
```

`FAIL:` / `ERROR:` headers by module: `test_upload_artifact_gate` 48 FAIL,
`test_manual_update_transaction` 8 ERROR (`setUpClass`; its 18 tests did not run, hence
575), `test_v024_release_contract` 1 FAIL — all three the `REVIEWED_APP_SOURCE_SHA256`
family (`expected 6f95bc8b… found 0cd17cef…`), expected and not re-pinned. The filter
`grep '^FAIL:\|^ERROR:' | grep -v 'test_upload_artifact_gate\|test_manual_update_transaction\|test_v024_release_contract'`
is empty. `tests.test_autostart`: 28 test headers in the log, 0 not-ok; run alone at
02:46:55Z: `Ran 28 tests … OK`, `exit=0`. No `[test_autostart] WARNING`, no tripwire
line. The 8 skips are the pre-existing loud ones (4 in `test_updater`, 4 in
`test_v020_boundaries`), the same set and count as the record's §6 / §10. Counts
identical to the Verifier's round 2.

### 8. Blocking items

None.

### 9. Non-blocking notes (for the Coordinator; none changes a Track B assertion)

- **N1 — py2app inclusion is pinned textually only.** `ServiceManagement` is a package
  whose `__init__` builds the bridge lazily (`objc.createFrameworkDirAndGetattr`,
  `from . import _metadata` inside `_setup()`), the same shape as `Foundation` / `AppKit`
  / `Quartz`, which `includes` already ships, so it is expected to land. The artefact-side
  check (`test_v020_boundaries.B2Bundle`, or a look at
  `dist/ClaudePet.app/Contents/Resources/lib/python3.13/`) needs a built bundle and
  belongs to the release's `build` step; worth one line in the release record.
- **N2 — `uninstall_autostart` refuses when `status()` raises** (D1: "do not delete
  without knowing the registration state"). The user then sees `unin_fail` +
  `autostart_fail`, which says to drag the app to the Trash — actionable. Stated here so
  the policy is on record as intended, not accidental.
- **N3 — the uninstall confirmation lists files, not the login item.** Cosmetic; the item is
  removed before anything is deleted.
- **N4 — ko / ja `autostart_approval` lack the final period that en / es carry.** Cosmetic;
  the strings are otherwise consistent with the survey's suggestions and with each other.
- **N5 — release-time obligations already named by the plan:** the v0.25 notes must say
  the item is unavailable on macOS 12 (D7, disabled item, no fallback) without a magnitude
  claim; README*.md and the site's spec table still point to System Settings — a
  documentation-only commit after both halves land.
- **N6 — the re-pin touches three modules, not one:** `tests/test_upload_artifact_gate.py`
  and `tests/test_manual_update_transaction.py` carry `REVIEWED_APP_SOURCE_SHA256`, and
  `tests/test_v024_release_contract.py` derives from both; all clear together against
  `0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0` (a Verifier edit the
  Coordinator schedules). A later production change to `claude_pet.py` (e.g. Track A merged
  ahead) moves that digest again.

Review round 1 closed 2026-09-13T02:50Z.

---

## Review: NotFound mapping fix

Reviewer: reviewer-b (Claude), REVIEWER role only on this fix; independent of the Developer
and of verifier-b. **Worktree `/Users/yeongyu/claude-pet-autostart-fix`, branch
`autostart-fix`, HEAD `794c66f`** (= `main` with Track A and Track B merged). All commands ran
with cwd at the worktree root; times are UTC; output blocks are verbatim. Not done, by
instruction: no git write command; nothing registered with or unregistered from the real
`SMAppService` (the gating module's `sys.modules` tripwire was in force for every run below,
and the scratch copies use fake service objects only); the GUI not run; no untracked file
touched (the worktree has none; this file is tracked and is the only file this review wrote);
the hardware probe not repeated (**[NEVER]** for a test or probe). Review window
13:47Z–14:05Z, 2026-09-13.

Inputs: AGENTS.md §2 / §3 / §5; CLAUDE.md "Start at sign-in" (worktree version, with the
diff); `git diff -- claude_pet.py CLAUDE.md tests/test_autostart.py docs-design/`; the
Verifier's record `docs-design/track-b-verification-20260913.md` §11–§12 (read in full);
`tests/test_autostart.py` (read in full); the autostart block, the `rightMouseDown_` menu
branch, `Handler.toggleAutostart_` and the `state["autostart_read"]` hook in `claude_pet.py`
(read from the tree, not from the diff alone).

### Verdict: PASS — no blocking items

Two items are handed to the Coordinator in §7 because only the Coordinator's own dispatch
record can settle them; neither is a defect in the code, the tests, or the documents.

### 1. The tree reviewed

```
$ git status --porcelain
 M CLAUDE.md
 M claude_pet.py
 M docs-design/track-b-verification-20260913.md
 M tests/test_autostart.py
$ git diff --numstat
21	5	CLAUDE.md
36	8	claude_pet.py
598	0	docs-design/track-b-verification-20260913.md
104	23	tests/test_autostart.py
$ shasum -a 256 claude_pet.py CLAUDE.md tests/test_autostart.py
ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4  claude_pet.py
12be8e264363787a7db7afe6c70a4fd5c09d89ce08c656cd9109dd07d80a03b3  CLAUDE.md
ff7be7d53056ec4e2ec513c419afb1b1db30cb996a29261d6b16e1ba22a9759c  tests/test_autostart.py
$ git show HEAD:claude_pet.py | shasum -a 256
3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461  -
```

All three digests equal the ones in the Verifier's §12.1; the gating file's digest equals the
one in §11.5 (the RED run). Modification times (UTC): `tests/test_autostart.py` 03:24:24,
`claude_pet.py` 13:29:50, `CLAUDE.md` 13:30:18, verification record 13:45:26. Worktree
checkout 03:20Z (HEAD committed 03:10:13Z). No untracked file in the worktree
(`git status --porcelain --untracked-files=all | grep '^??'` is empty). Machine:
`sw_vers` 26.5.2 (25F84), `uname -r` 25.5.0, Python 3.13.7 — the machine the Coordinator's
probe names (`/Users/yeongyu/Applications/ClaudePet.app`).

### 2. The Verifier's re-derivation — recorded, evidence-cited, **not** "before reading"

What the assignment asked this review to confirm, checked clause by clause:

- **Recorded:** yes — §11.4 is a cell-by-cell table over `(status, is_bundle)`, plus the
  toggle-from-3 row, plus the three non-int "unavailable" cases.
- **Derived from the evidence:** yes — every cell names its source: a quoted line of the
  Coordinator's probe (`status before: 3`, `register: True | err: None`, `status after
  register: 1`, `status after unregister: 0`) or a quoted line of `SMAppService.h` from the
  26.5 SDK (read from disk, no framework call). The three §5 slots (observed / invariant /
  consequence) are kept in separate numbered sentences in §11.3, the observation is labelled
  "one machine, one bundle, one probe" and "not reproduced here", and the header's "an error
  occurred" wording is quoted as the reason the `794c66f` mapping looked right.
- **Stated before reading the old expected values:** **no.** §11.2 says so in plain words:
  establishing the provenance of the uncommitted test diff required `git diff`, which shows
  both the HEAD values and the new ones, so §11.4 "was written **after** both had been seen,
  and this record does **not** claim the 'derived before reading' property." The deviation is
  declared, not discovered; the ordering was avoidable in principle (derive first from the
  evidence in the assignment, then diff), and the Verifier did not take that route.

Why this is not blocking, stated so it can be disagreed with: the property guards against a
re-deriver anchoring on the existing expected values. The HEAD value for the one cell in
question is `"unavailable"`, which is exactly what the fix rejects — anchoring on it would
produce the wrong answer, not the right one. The new value is forced by the probe (a status
from which `register` returns `(True, None)` and the status then reads `1` is the unregistered
state), and this review reproduces the RED against the genuine HEAD file and executes the
rivals independently (§4). What the missing property would have added — an answer produced
without sight of either table — no agent who has now read the diff can supply, this Reviewer
included; §7 says who could.

This Reviewer's own derivation, from the probe and the header alone, written here *after*
having read the diff (so it carries the same caveat): `3` on a bundle → unchecked and enabled,
click → `register`; `0` → the same; `1` → checked, click → `unregister`; `2` → mixed, click →
no call, approval alert; any int outside 0–3, a non-bundle, a `None` service, a `status()`
that raises → disabled item, no call. Matches §11.4 in every cell.

### 3. AGENTS.md §2 — Developer–Verifier separation

- **Condition A.** The gating file is byte-identical across the Verifier's RED (13:17:35Z,
  `ff7be7d5…`), the Verifier's GREEN (13:37:46Z) and this review; its mtime 03:24:24Z predates
  the production writes (`claude_pet.py` 13:29:50Z, `CLAUDE.md` 13:30:18Z) by ten hours. So
  whoever wrote the fix did not touch an assertion, an expected value or a fixture after the
  RED run. The `STATE_TABLE` change is one value (`(3, True)`) plus two inserted rows; no row
  was reordered, and the assertion is a dict comparison, so order is not load-bearing.
  **Holds for the Developer's write.** The 03:24Z edit itself is of unproven authorship — see
  §7.
- **Condition B.** The Verifier states (§11, §12) that it wrote only `tests/test_autostart.py`
  and the record; `claude_pet.py` was written at 13:29:50Z, between the Verifier's RED pass
  (closed 13:26Z) and GREEN pass (opened 13:37:42Z), which is the red-then-fix-then-green
  shape §3 requires. From an uncommitted tree authorship is not provable by the Reviewer; it is
  consistent with every artefact available, and the §7 trailers on the eventual commit are where
  it becomes checkable. **No contrary evidence; treated as holding.**
- **Condition C.** No exception is declared, because the Verifier treats the 03:24Z diff as its
  own earlier, unfinished pass (an inference, labelled as one in §11.2). If that inference is
  wrong, Condition A is breached for the gating assertions and Condition C's re-derivation is
  required from a Reviewer or a no-role agent — see §7.

### 4. AGENTS.md §3 — red before green, reproduced by this Reviewer

The Verifier's RED (§11.7, verbatim, 3 FAIL on the `(3, True)` cell, log `red-autostart.log`
in the session scratchpad, mtime 13:17:35Z) and GREEN (§12.3, 30/30, `green-autostart.txt`,
13:37:46Z) were both observed with the gating file held constant. This review re-derived the
red state independently, the §3 "revert and observe" way: scratch copies under the session
scratchpad (`reviewb-notfound/<variant>/`), each holding `setup.py`, the current
`tests/test_autostart.py` (`ff7be7d5…`) and one `claude_pet.py`, run as
`python3 -m unittest tests.test_autostart` from the copy's root (13:59Z). Fault injections
assert their needle occurs exactly once before replacing it. Output filtered to the
`FAIL:` / `AssertionError` / diff / summary lines:

```
=============== VARIANT fixed : claude_pet.py ce7564b1e3595ecf…  test ff7be7d53056ec4e…
Ran 30 tests in 0.076s
OK
=============== VARIANT head : claude_pet.py 3bc33466ff97e04f…  test ff7be7d53056ec4e…   (git show HEAD:claude_pet.py)
FAIL: test_read_state_table (tests.test_autostart.AutostartReadStateTests.test_read_state_table)
AssertionError: Lists differ: [('unavailable', ['status']), ('unavailable'[53 chars]one)] != [('off', ['status']), ('unavailable', ['stat[45 chars]one)]
FAIL: test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
-  (3, True): 'unavailable',
+  (3, True): 'off',
FAIL: test_never_registered_bundle_registers_from_not_found (tests.test_autostart.AutostartToggleTests.test_never_registered_bundle_registers_from_not_found)
AssertionError: Tuples differ: (('unavailable', None), []) != (('on', None), ['register'])
Ran 30 tests in 0.080s
FAILED (failures=3)
=============== VARIANT r4b : SM_STATUS_NOT_FOUND: "on"
FAIL: test_read_state_table ...   - [('on', ['status']),  + [('off', ['status']),
FAIL: test_status_and_bundle_table ...   -  (3, True): 'on',  +  (3, True): 'off',
FAIL: test_never_registered_bundle_registers_from_not_found
AssertionError: Tuples differ: (('on', 'autostart_fail'), ['unregister']) != (('on', None), ['register'])
Ran 30 tests in 0.080s
FAILED (failures=3)
=============== VARIANT r15 : _AUTOSTART_STATE_BY_STATUS.get(status, "off")
FAIL: test_status_and_bundle_table
- {(-1, True): 'off',      + {(-1, True): 'unavailable',
-  (99, True): 'off'}      +  (99, True): 'unavailable'}
Ran 30 tests in 0.081s
FAILED (failures=1)
```

Reading: against the genuine pre-fix file the same three tests fail with the same messages the
Verifier recorded, and every failure is the `(3, True)` cell — the shipped behaviour is visible
in full as `(('unavailable', None), [])`, the click that cannot turn the feature on. R4b is
separated on the toggle by the call list *and* the error, as the class docstring predicts (the
fake refuses `unregister` from 3); R15 is separated by exactly the two unknown-int rows the
docstring says were added for it. The truth tables in the test docstrings are therefore
executed fact, not prose. The fixed tree is 30/30 in the same harness.

### 5. Mapping, docstrings and CLAUDE.md — consistent, and the "unavailable" cases intact

Read from the tree, not the diff:

- `_AUTOSTART_STATE_BY_STATUS[3] == "off"`; `autostart_state` is `if not is_bundle:
  "unavailable"` then `.get(status, "unavailable")` — so `99` / `-1` / non-int → `"unavailable"`
  and the four `is_bundle=False` rows are untouched. The Korean block above the table keeps
  observation ("기기 하나, 조사 한 번"), reasoning ("0 과 3 이 같은 상태로 간다") and
  consequence in separate sentences. The `autostart_state` docstring's "3 은 모르는 값이
  아니다" and the `autostart_toggle` docstring's "(상태 0 또는 3) 등록 … (1) 해제" match the code.
- `autostart_read_state`: `not is_bundle or service is None → "unavailable"` before any call;
  `status()` raising → `"unavailable"`. **From source `autostart_current()` yields `(None,
  False)` and no method on the service is called; macOS 12 / missing framework →
  `autostart_service()` is `None` → `"unavailable"`.** Both pinned green by
  `test_read_state_table`, `test_source_run_never_touches_the_service`,
  `test_missing_framework_is_unavailable_without_error` and the `AutostartServiceTests` rows.
- `autostart_toggle`: unchanged code; `"off"` from 3 reaches the `else` branch →
  `registerAndReturnError_(None)` → state read back (`("on", None)` with the fake moving
  3 → 1 as the hardware did). Early return on `("unavailable", "approval")` still makes no
  call for unknown ints and from 2.
- `uninstall_autostart`: no hunk; 0 / 3 read `status()` and stop (`test_helper_table` row
  `status 3 → None, []` still green) — a never-enabled user still uninstalls cleanly.
- `rightMouseDown_`: no hunk; only the `"unavailable"` branch calls `setEnabled_(False)`;
  `"off"` → `setState_(0)` on an item whose enabled state is the NSMenuItem default (YES), and
  `setAutoenablesItems_(False)` keeps it that way. So the fresh-install item renders
  **unchecked and enabled**. Its comment listing the `"unavailable"` cases (소스 실행, macOS 12,
  서비스 없음) is still accurate.
- CLAUDE.md "Start at sign-in": the `autostart_state` bullet (`3 → "off"`, any other int →
  `"unavailable"`, the four surviving `"unavailable"` cases, the finding labelled one machine /
  one probe), the `autostart_toggle` bullet ("Off (status `0` or `3`)"), the
  `uninstall_autostart` bullet ("`0` / `3` read `status()` and stop there"), the menu paragraph
  ("`"unavailable"` (from source, or no `SMAppService`)") and the closing **[NEVER]** paragraph
  (which no longer says a from-source run "would report `NotFound` anyway") all match the code.
  "macOS 26.5 / Darwin 25.5" matches this machine's `sw_vers` / `uname -r`; the Coordinator's
  block says "macOS 26", and the test docstring quotes that — both true, differing only in
  precision.

### 6. Full suite from the worktree root (this Reviewer) — 13:51:14Z to 13:55:51Z, exit 1

```
$ python3 -m unittest discover -s tests -v      # log: session scratchpad reviewb-fix-suite.log
Ran 588 tests in 276.467s
FAILED (failures=49, errors=8, skipped=8)
```

`FAIL:` / `ERROR:` headers by module: `test_upload_artifact_gate` 48 FAIL,
`test_manual_update_transaction` 8 ERROR (`setUpClass`; its 18 tests did not run),
`test_v024_release_contract` 1 FAIL — all the `REVIEWED_APP_SOURCE_SHA256` family:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4
```

The filter `grep '^FAIL:\|^ERROR:' | grep -v 'test_upload_artifact_gate\|test_manual_update_transaction\|test_v024_release_contract'`
is empty. The 8 skips are the pre-existing loud ones: four in `test_updater` (two
"installed-app preflight", two "real stapler contract", each with its `[updater] SKIPPED:`
stderr line, opt-in via `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`) and four in
`test_v020_boundaries` (`B2Bundle` no built bundle under `dist/`; three `B3Updater` live tests).
`grep -c 'WARNING\|reached SMAppService\|tried to open System Settings'` over the log: `0`.
Counts identical to the Verifier's §12.4 (588 / 49 / 8 / 8). Standalone, 13:56:48Z:
`python3 -m unittest tests.test_autostart -v` → `Ran 30 tests in 0.077s` / `OK`.

The Verifier's cited scratch files exist in the session scratchpad with mtimes matching the
record: `red-autostart.log` 13:17:35Z (3 FAIL, the same three tests),
`discriminate_notfound.py` 13:17:52Z, `green-autostart.txt` 13:37:46Z, `green-full.txt`
13:42:19Z (`Ran 588` / `failures=49, errors=8, skipped=8`).

### 7. Items for the Coordinator (not blocking; the first becomes blocking if it cannot be settled)

- **C1 — authorship of the 03:24:24Z edit to `tests/test_autostart.py`.** The Verifier
  treats it as its own earlier, unfinished pass (§11.2), on the strength of the module header
  and the content. Nothing in the shared scratchpad from 03:20–03:30Z names `test_autostart`
  (the files there from that window are Windows-port patches and a suite baseline). Only the
  Coordinator's dispatch record can say which agent held the tree at 03:24Z. If it was a
  verifier-b session, §2 holds with no exception and the "before reading" property is moot —
  the values were authored, not re-derived. If it was any other agent, Condition A is breached
  for the gating assertions and a Condition C re-derivation is required from a Reviewer or a
  no-role agent **who has not seen the diff** — which now excludes verifier-b and this
  Reviewer; a fresh agent handed only the probe block and the header excerpt could produce it
  in minutes, and §2 of this review is what its answer should match.
- **C2 — the "derived before reading" property is absent and declared absent** (§11.2). If the
  Coordinator wants it on record regardless of C1, C1's remedy is the only way to obtain it.

### 8. Non-blocking notes

- **N1 — "fails loudly" has a precondition.** CLAUDE.md and the code comment say that if a `3`
  ever is the header's error, the click "fails loudly through the `autostart_fail` alert". That
  holds when `registerAndReturnError_` returns `(False, err)` or raises. A register that
  returned `(True, None)` while the status stayed `3` would read back as `"off"` and return
  `("off", None)` — no alert, item still unchecked. Whether the framework can do that is not
  known; the sentence would be exact with "…fails through the `autostart_fail` alert whenever
  `register` reports failure". Documentation wording only; no test asserts the hypothetical.
- **N2 — CLAUDE.md repo-layout row for `tests/test_autostart.py`** lists the status table, the
  toggle table, the uninstall ordering, the TR keys and the menu wiring; the module now also
  pins `autostart_read_state`'s table. Not written as exhaustive, so not wrong (the Verifier's
  §12.6 says the same).
- **N3 — `main` is at `f3c4780`** (one commit past `794c66f`, touching `claude_pet.py` line 6
  and docs); the fix's hunks are elsewhere, so it applies cleanly, but the pin family must be
  re-pinned on the merged tree's digest, not on `ce7564b1…`.
- **N4 — descriptor precision** ("macOS 26" in the test docstring, "macOS 26.5" in the code
  comment and CLAUDE.md): both true of the probe machine; harmless.

Review closed 2026-09-13T14:05Z.
