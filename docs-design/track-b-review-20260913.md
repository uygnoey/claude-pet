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
