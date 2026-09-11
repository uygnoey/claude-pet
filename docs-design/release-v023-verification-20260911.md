# ClaudePet v0.23 — independent verification record

- **Verifier:** agent `verifier-v023` (Claude Code session
  `55c3dee4-727f-4a94-b960-66540b129014`, subagent). Held no other role on this
  release. Edited none of the production files (§2 Condition B): `claude_pet.py`,
  `verify_release_artifact.py`, `RELEASE_NOTES.md`, `CLAUDE.md`, `README*` were read
  only.
- **Developer:** Claude (same session, main thread) — prepared the uncommitted
  v0.23 change described below.
- **Measured (UTC):** 2026-09-11T01:13:54Z (start) → 2026-09-11T01:31:14Z (end).
  Suite window: 2026-09-11T01:25:27Z → 2026-09-11T01:31:01Z.
- **Tree under test:** HEAD `6d47df5e433fe39d6e84d2d4e2a5ead6ddc2c349` (v0.22
  published: `git tag --sort=-v:refname | head -1` → `v0.22`; `gh release list`
  → `ClaudePet v0.22  Latest  v0.22  2026-09-11T00:43:39Z`) plus the Developer's
  uncommitted working-tree changes.
- **Source hashes (SHA-256, working tree, unchanged for the whole run):**
  - `claude_pet.py` `57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b`
  - `verify_release_artifact.py` `fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69`
  - `release.sh` `a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23` (unchanged from HEAD)
  - `RELEASE_NOTES.md` `6e0b1cdfd988f878252aa12c694dafeb3b522783ffa7575b2f3d9145b716c07b`
- **Deliverables this record licenses (§4), all created or already owned by the
  Verifier role:** `tests/test_update_check_schedule.py` (revised; the earlier
  `verifier-upd` draft is superseded), `tests/test_v023_release_contract.py`
  (`git mv` from `tests/test_v022_release_contract.py`, then rewritten),
  `tests/test_upload_artifact_gate.py` and `tests/test_manual_update_transaction.py`
  (pin literals only), this file. `docs-design/update-check-schedule-verification-20260911.md`
  did not exist (checked before writing; `ls` → "No such file or directory"), so
  nothing was folded or deleted.
- **Nothing else was touched.** No `./release.sh`, no `./build_app.sh`, no commit,
  no tag, no `git add -A`/`.`, no `git clean`, no `rm -rf release`; `~/.claude`
  and `~/.claude_pet` were never read or written by any test (all fixtures are
  synthetic; network calls are stubbed). `/Applications/ClaudePet.app` (v0.22) was
  not touched.

The §6 execution gate — the suite re-run from a **clean tracked tree** — is
evaluated after the release commit exists and is **not** part of this record.
This record is the pre-commit Verifier evidence (§8 items 3 and 5) for the
release commit.

---

## 1. RED first — the gates fail closed against the prepared tree

Run from the repository root before any Verifier edit. Verbatim lines:

`python3 -m unittest discover -s tests -p test_upload_artifact_gate.py`

```
AssertionError: 'fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69' != '8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d'
 : verify_release_artifact.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes
Ran 64 tests in 3.597s
FAILED (failures=48)
```

`python3 -m unittest discover -s tests -p test_manual_update_transaction.py`

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 22215568f15ad9f7c898f576d93ca38bb16ca7580c41de729ad2b0240c8a4a67, found 57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b
Ran 0 tests in 0.003s
FAILED (errors=8)
```

(The `22215568…` value is the stale intermediate repin the stopped `verifier-upd`
run left behind; HEAD's pin is `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266`.)

`python3 -m unittest discover -s tests -p test_v022_release_contract.py`

```
AssertionError: Lists differ: ['0.23', '0.22'] != ['0.22', '0.21']
AssertionError: ["APP_VERSION must be one literal '0.22', got ['0.23']", 'verify_release_artifact.py usage must show --expect-version 0.22', 'verify_release_artifact.py still advertises --expect-version 0.23', ...
Ran 11 tests in 0.257s
FAILED (failures=2)
```

`python3 -m unittest discover -s tests -p test_update_check_schedule.py` (the
`verifier-upd` draft)

```
FAIL: test_nothing_at_launch_reaches_the_update_check (test_update_check_schedule.UpdateCheckScheduleSourceTests.test_nothing_at_launch_reaches_the_update_check)
AssertionError: 2 != 1 : 2 references to _run_update_check; the worker gate's call must be the only one
Ran 6 tests in 0.173s
FAILED (failures=1)
```

The second reference is `status = _run_update_check()` inside
`Handler.checkUpdate_.work` — the user-triggered call site the scope grew to
include. The draft's closed list of one caller was therefore wrong for the final
behaviour, and it is revised below to a closed list of two.

## 2. Diff review against the assignment

`git diff --stat HEAD` lists exactly six tracked files: `CLAUDE.md` (+2/−1),
`RELEASE_NOTES.md` (+5), `claude_pet.py` (+79/−11 … 6 hunks), `verify_release_artifact.py`
(+1/−1), and the two stale test repins. Hunk by hunk, `claude_pet.py`:

| Hunk | Matches the Context description |
| --- | --- |
| `APP_VERSION = "0.22"` → `"0.23"`; `UPDATE_CHECK_SEC = 6 * 3600` → `3600` with a new comment | yes |
| `TR` en/ko/ja/es: six new keys `menu_check_update`, `upd_title`, `upd_current`, `upd_failed`, `upd_install_failed`, `upd_busy` | yes, all four locales |
| `_run_update_check`: `return` → `return None` when busy; `poll_github_update(state)` → `return poll_github_update(state)` | yes |
| context menu: new `NSMenuItem` titled `t("menu_check_update")`, action `"checkUpdate:"`, target `handler`, appended right after the disabled version row | yes |
| `Handler.checkUpdate_` (daemon thread: `_run_update_check()` → on `'update'` `install_github_update(upd[1], expect_version=upd[0])` then `quitApp:` on the main thread; else `showUpdateMessage:` with `upd_install_failed` / `upd_current` / `upd_busy` / `upd_failed`) and `Handler.showUpdateMessage_` (`NSAlert`, `t("upd_title")`, `runModal`) | yes |
| refresh worker: comment only; the gate `if not state.get("update") and time.time() - _upd_cache["t"] > UPDATE_CHECK_SEC: _run_update_check()` is byte-identical | yes |
| `run_gui` tail: `threading.Thread(target=_run_update_check, daemon=True).start()` replaced by `_upd_cache["t"] = time.time()` before `AppHelper.runEventLoop()` | yes |

`verify_release_artifact.py`: usage example `--expect-version 0.22` → `0.23`
only. `RELEASE_NOTES.md`: one new `**v0.23**` section with three top-level bullets
above the published `**v0.22**`; no published byte changed (see §4).
`CLAUDE.md`: the single sentence "polls the repo's latest release tag every
6 hours" → "every hour (never at launch — the first check comes one interval after
start)". **No change outside the description was found.** No estimator function
(`_weigh_usage`, `parse_usage_entries`, `compute_usage`, `_weekly_window_start`,
`spike_info`) is in any hunk, which is what backs the notes' "한도 계산은 그대로".

**Direct-to-latest, verified from the source (not an observation):**
`check_github_update()` builds exactly one request, to
`https://api.github.com/repos/{GITHUB_REPO}/releases/latest`, reads that one
`tag_name`, and returns `'current'` when `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)`
and otherwise `('update', tag, url)` for the asset `select_update_asset` picks.
`poll_github_update` publishes `(tag, url)` unchanged and `install_github_update`
verifies the downloaded bundle against `expect_version=tag`. Nothing enumerates
releases or steps through versions, so an installed 0.20 that finds 0.24 as the
latest release is offered and installs 0.24 directly. The updater code is
unchanged by v0.23; the new menu action only calls into it. Two facts read from
the same source, stated for accuracy: (a) after a `'failed'` poll the cooldown is
not stamped (pre-existing, by design), so the worker retries on the following
30-second refreshes until a check succeeds — "1시간마다" is the cadence between
successful checks; (b) the first periodic check runs on the first 30-second
refresh after the hour has elapsed, i.e. at launch + 3600 s + up to 30 s.

## 3. `tests/test_update_check_schedule.py` — revised, 22 cases → OK

`python3 -m unittest discover -s tests -p test_update_check_schedule.py` →
`Ran 22 tests in 0.326s` / `OK`.

- `UpdateCheckScheduleSourceTests` (7): literal `3600`; nothing at launch reaches
  the check (no `Thread(target=_run_update_check)` anywhere; no top-level call to
  `_run_update_check`/`poll_github_update`/`check_github_update`/`checkUpdate_`/`doUpdate_`,
  bare or via attribute); **exactly two** `_run_update_check` references in the
  whole module — the worker gate's call in `Ticker.refresh_.work` and
  `status = _run_update_check()` in `Handler.checkUpdate_.work`, both located by
  AST parent chain; launch stamp exactly once, before `AppHelper.runEventLoop()`,
  and the only write to `_upd_cache['t']` in `run_gui`; the worker gate text,
  strict `>`, comparison against `UPDATE_CHECK_SEC`, and `_run_update_check`'s two
  returns (`None`, `poll_github_update(state)`); the menu item (title
  `t('menu_check_update')`, action `checkUpdate:`, `setTarget_(handler)`,
  `menu.addItem_`, after the version row) and both handler methods; the six TR
  keys in all four locales, `{v}` in `upd_current`, `TR["ko"]["menu_check_update"] == "⬆︎ 업데이트 확인…"`.
- `RunUpdateCheckClosureTests` (3): the closure executed out of the AST — `None`
  and no poll while busy; the poll's status otherwise with `busy` cleared; `busy`
  cleared when the poll raises.
- `CheckUpdateActionTests` (7): `Handler.checkUpdate_` executed out of the AST with
  stubbed check/installer/`t`/`threading.Thread` — installs `(url, expect_version=tag)`
  and dispatches only `quitApp:`; install failure → `upd_install_failed`; `'update'`
  with no pending tuple installs nothing; `'current'` → `upd_current` with
  `v=APP_VERSION`; `None` → `upd_busy`; `'failed'` → `upd_failed`; no `NSAlert` in
  the worker and only the `showUpdateMessage:`/`quitApp:` selectors;
  `showUpdateMessage_` sets `t("upd_title")`, the message, and runs modal.
- `DirectToLatestTests` (3): `APP_VERSION` patched to `"0.20"`, `urlopen` stubbed to
  answer `v0.24` with `ClaudePet.zip`/`ClaudePet-universal.zip`, `platform.machine`
  → `arm64`: `check_github_update() == ('update', '0.24', 'https://example.test/ClaudePet.zip')`
  with exactly one request, to `…/releases/latest`; the same payload is `'current'`
  at `0.24` and `0.25` (guards against an always-`'update'` rival); the real
  closure + real `poll_github_update` + extracted `checkUpdate_` publish
  `('0.24', url)` and call `install_github_update(url, expect_version='0.24')`
  then `quitApp:` — one hop, one request.
- `UpdateCheckScheduleBehaviourTests` (2): fake clock over the extracted launch
  stamp and worker gate — not due at launch, +30 s, +3599 s, +3600 s; due at
  +3601 s; then not until a further 3600 s; never once an update is pending.

## 4. `tests/test_v023_release_contract.py` — 11 cases → OK

`git mv tests/test_v022_release_contract.py tests/test_v023_release_contract.py`,
then rewritten. `python3 -m unittest discover -s tests -p test_v023_release_contract.py`
→ `Ran 11 tests in 0.132s` / `OK`.

- `APP_VERSION == ["0.23"]`; verifier usage shows `--expect-version 0.23` and none
  of 0.22/0.21/0.24; both harness pins equal the current `claude_pet.py` SHA-256 and
  the upload gate's verifier pin equals the current `verify_release_artifact.py`.
- Published suffix pin: SHA-256 of `RELEASE_NOTES.md` from `**v0.22**` to EOF =
  `6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239`, computed from
  the working file **and** from `git show HEAD:RELEASE_NOTES.md` — identical
  (`**v0.22**` occurs once in each; the v0.21-and-older suffix
  `323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75` is likewise
  unchanged from the v0.22 contract test). Headings `[:2] == ["0.23", "0.22"]`.
- v0.23 section: 3 top-level bullets, no nesting, **222** normalised characters
  (≤ 450), 2 sentences per bullet, Korean, none of `FORBIDDEN_NOTE_PATTERNS` (dict
  kept verbatim), and the three claims present: no launch check + hourly + install
  item at the top of the context menu; `"업데이트 확인…"` gained, press → check now →
  download, install, relaunch; straight to the latest release, no recalibration.
- Cross-checks: `1시간` ↔ `UPDATE_CHECK_SEC == 3600` (one hours figure, 1 × 3600 = 3600,
  no stray 분/초 figure); `"업데이트 확인…"` ↔ `TR["ko"]["menu_check_update"]` with
  its `⬆︎` glyph removed (both directions); `run_gui` top level stamps once and
  never reaches the check; `check_github_update` reads exactly
  `…/releases/latest` and compares `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)`;
  `CLAUDE.md` says "every hour" / "never at launch" and no longer "every 6 hours".
- `ReleaseNotesPolicyTests` carried over unchanged.

## 5. Mutation check — 25 mutants, 25 RED

Scratch only (`…/scratchpad/mutants/`, driver `run_mutants.py`, per-mutant
`run.log`); nothing under `tests/` or the repo was mutated. Each mutant copies the
files the module reads, applies one change (needle asserted to occur exactly once),
and runs the module from the mutant root. Baselines first: schedule
`Ran 22 tests in 0.303s` / `OK`; contract `Ran 11 tests in 0.132s` / `OK`.

| # | Mutant (file) | Module | Verbatim failing line |
| --- | --- | --- | --- |
| S01 | restore `threading.Thread(target=_run_update_check, daemon=True).start()` at launch (claude_pet.py) | schedule | `AssertionError: Lists differ: ['threading.Thread(target=_run_update_check, daemon=True)'] != []` |
| S02 | `UPDATE_CHECK_SEC = 6 * 3600` | schedule | `AssertionError: <ast.BinOp object at 0x114412090> is not an instance of <class 'ast.Constant'> : UPDATE_CHECK_SEC must be a bare literal, not \`6 * 3600\` — \`6 * 3600\` and \`30 * 60\` are the rivals` (failures=3) |
| S03 | remove the launch stamp | schedule | `AssertionError: True is not false : an update check is due at launch+0s; _upd_cache['t']=0.0` |
| S04 | add `_run_update_check()` at run_gui top level | schedule | `AssertionError: Lists differ: ['_run_update_check()'] != []` |
| S05 | drop `TR["ko"]["upd_busy"]` | schedule | `AssertionError: Lists differ: ['upd_busy'] != []` (subTest locale='ko') |
| S06 | `checkUpdate_` never installs (`if False:`) | schedule | `AssertionError: Expected 'install_github_update' to be called once. Called 0 times.` (failures=3) |
| S07 | busy returns `'failed'` instead of `None` | schedule | `AssertionError: 'failed' is not None` |
| S08 | `check_github_update` offers the next version instead of the latest | schedule | `AssertionError: Tuples differ: ('update', '0.21', 'https://example.test/ClaudePet.zip') != ('update', '0.24', 'https://example.test/ClaudePet.zip')` |
| S09 | stamp moved after `AppHelper.runEventLoop()` | schedule | `AssertionError: 124 not less than 123 : the launch stamp must precede AppHelper.runEventLoop() — after it, it never runs` |
| S10 | `install_github_update(upd[1])` without `expect_version` | schedule | `Expected: install_github_update('https://example.test/ClaudePet.zip', expect_version='0.24')` / `  Actual: install_github_update('https://example.test/ClaudePet.zip')` |
| S11 | `handler.checkUpdate_(None)` at run_gui top level | schedule | `AssertionError: Lists differ: ['handler.checkUpdate_(None)'] != []` |
| S12 | alert built on the worker thread (`self.showUpdateMessage_(msg)`) | schedule | `FAIL: test_the_alert_is_never_built_on_the_worker_thread … AssertionError: Items in the second set but not the first:` (failures=1, errors=5) |
| C01 | 4th top-level bullet (RELEASE_NOTES.md) | contract | `AssertionError: 4 != 3 : v0.23 must have exactly 3 top-level bullets, got 4` |
| C02 | nested bullet | contract | `AssertionError: Lists differ: ['  - 설치 후 자동으로 다시 켜집니다.'] != []` |
| C03 | body padded past 450 | contract | `AssertionError: 552 not less than or equal to 450 : v0.23 Korean body is 552 Unicode characters; max is 450` |
| C04 | "가끔" inserted | contract | `AssertionError: ["remove unsupported magnitude/frequency: '가끔'"] is not false :` |
| C05 | hash `6d47df5e` inserted | contract | `AssertionError: ["remove hash: '6d47df5e'"] is not false :` |
| C06 | `APP_VERSION = "0.22"` (claude_pet.py) | contract | `AssertionError: ["APP_VERSION must be one literal '0.23', got ['0.22']", …` |
| C07 | upload-gate app pin → `0000…` | contract | `AssertionError: ['test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 0000000000000000000000000000000000000000000000000000000000000000, final source is 57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b'] is not false :` |
| C08 | one published v0.22 byte altered | contract | `AssertionError: '2fc0c2509f18b7394a72be137593c08ab78a4f8a3edf99100b6a16059a018327' != '6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239'` |
| C09 | notes say "30분마다" | contract | `AssertionError: 0 != 1 : expected exactly one duration in hours in the notes, got []` |
| C10 | notes quote `"업데이트 확인"` without the ellipsis | contract | `AssertionError: '"업데이트 확인…"' not found in '새 버전 확인을 …` |
| C11 | CLAUDE.md reverted to "every 6 hours" | contract | `AssertionError: "polls the repo's latest release tag every hour" not found in '# CLAUDE.md — ClaudePet facts…` |
| C12 | source label drifts to `"⬆︎ 업데이트 확인"` | contract | `AssertionError: '⬆︎ 업데이트 확인' != '⬆︎ 업데이트 확인…'` |
| C13 | verifier usage still `--expect-version 0.22` | contract | `AssertionError: ['verify_release_artifact.py usage must show --expect-version 0.23', 'verify_release_artifact.py still advertises --expect-version 0.22', …` |

Grouping key: one mutant = one scratch copy with one textual change; 25 of 25
mutants RED, 0 GREEN; measured 2026-09-11T01:24:49Z → 2026-09-11T01:24:58Z.

## 6. Repins (old → new)

Reviewed bytes are the working-tree `claude_pet.py` and `verify_release_artifact.py`
whose diffs are itemised in §2.

| File | Literal | HEAD value | stale `verifier-upd` value | now |
| --- | --- | --- | --- | --- |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_APP_SOURCE_SHA256` | `04d016e8…f66266` | `22215568…8a4a67` | `57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b` |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_VERIFIER_SHA256` | `8de85e87…eb82d` | (unchanged) | `fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69` |
| `tests/test_manual_update_transaction.py` | `REVIEWED_APP_SOURCE_SHA256` | `04d016e8…f66266` | `22215568…8a4a67` | `57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b` |

`REVIEWED_RELEASE_SHA256` (release.sh) and `REVIEWED_BUILD_APP_SHA256`
(build_app.sh) untouched — both scripts are unchanged from HEAD. After repin:
`test_upload_artifact_gate.py` → `Ran 64 tests in 48.152s` / `OK`;
`test_manual_update_transaction.py` → `Ran 18 tests in 14.178s` / `OK`. (The repin
was applied before the §4 run so that step could be recorded green; the mutation
check in §5 used scratch copies and is independent of the repo pins.)

## 7. Full suite from the repository root

```
python3 -m unittest discover -s tests -v
start 2026-09-11T01:25:27Z
Ran 508 tests in 333.600s
OK (skipped=7)
rc=0
end 2026-09-11T01:31:01Z
```

Skipped (all opt-in live checks, each skipping loudly by design):

- `test_updater.RealBundleAcceptanceTests.test_the_real_bundle_contains_the_symlinks_this_guard_is_about` — `skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
- `test_updater.RealBundleAcceptanceTests.test_the_real_installed_bundle_is_accepted_by_the_preflight` — same reason
- `test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65` — `skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
- `test_updater.StaplerLiveContractTests.test_stapler_reports_success_for_our_stapled_bundle` — same reason
- `test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network` — `skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'`
- `test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff` — same reason
- `test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff` — same reason

The live variants were deliberately not enabled: they would inspect the installed
v0.22 bundle, which this assignment forbids touching.

## 8. Untouched-file proof and working-tree state

`stat -f '%m %N'` before (01:13:54Z) and after (01:31:14Z), identical:

```
1784689621 diag.py
1783953996 release/icon_1024.png
1783953996 release/ClaudePet.iconset
```

`git status --porcelain` at the end (tracked columns only): `M CLAUDE.md`,
`M RELEASE_NOTES.md`, `M claude_pet.py`, `M tests/test_manual_update_transaction.py`,
`M tests/test_upload_artifact_gate.py`, `RM tests/test_v022_release_contract.py -> tests/test_v023_release_contract.py`,
`M verify_release_artifact.py`; untracked: `tests/test_update_check_schedule.py`,
this file, and the pre-existing `??` entries (user-owned files and other agents'
docs-design records), none of which were touched. `git diff --cached --name-only`
→ `tests/test_v023_release_contract.py` (the `git mv` rename only; the rewrite is
an unstaged modification on top of it).

For whoever stages the release commit by name (CLAUDE.md step 2): the Verifier's
paths are `tests/test_update_check_schedule.py`,
`tests/test_v023_release_contract.py` (rename from `tests/test_v022_release_contract.py`),
`tests/test_upload_artifact_gate.py`, `tests/test_manual_update_transaction.py`,
`docs-design/release-v023-verification-20260911.md`.

## 9. Not covered here

- No live GUI run: `NSAlert.runModal` from `showUpdateMessage_` in an `LSUIElement`
  app, and the menu item's appearance, were verified structurally (AST) and by
  executing the extracted method bodies with stubs, not by opening the app.
- The real download/replace path of `install_github_update` is unchanged by v0.23
  and is covered by the existing `test_updater*` / `test_settings_and_install`
  gates, which ran green above.
- The §6 clean-tree re-run, the Reviewer's sign-off, the Coordinator's sign-off,
  and the naming of an eligible release operator remain to be done after the
  release commit.

---

## v0.23 release — execution gate: clean-tree suite re-run at commit 81619b3e305d7c45e3aec02ba13d3becd1dee6f3

- **Gate item:** AGENTS.md §6 execution gate, item 2 — the full suite re-run by the
  Verifier from a clean tracked tree, with the command and its output recorded rather
  than summarized. Items 3–5 (release-notes check, the Coordinator's recorded sign-off,
  naming the release operator with eligibility) are outside this record.
- **Verifier:** `verifier-v023` (Claude Code workflow subagent, session
  `55c3dee4-727f-4a94-b960-66540b129014`). Held no other role on this release. Ran only
  read-only `git` / `stat` / `shasum` / `gh release list` commands plus the test command
  below; edited only this file, and only after the suite window closed.
- **Record appended (UTC):** 2026-09-11T02:12:05Z
- **Tree under test:** HEAD `81619b3e305d7c45e3aec02ba13d3becd1dee6f3` (`release: ClaudePet
  v0.23`; trailers `Developer: Claude (session 55c3dee4-…)` / `Verifier: verifier-v023`,
  distinct). Tracked tree clean per §6's definition: `git status --porcelain` at
  2026-09-11T02:02:17Z and again at 02:08:48Z set no `M`/`A`/`D`/`R` column for any
  tracked path — only 19 `??` entries (`diag.py`, `release/ClaudePet.iconset/`,
  `release/icon_1024.png`, and 16 `docs-design/` captures and records from earlier work),
  the same 19 both times.
- **Outside world at run time:** `git tag --sort=-v:refname | head -1` → `v0.22`;
  `gh release list --limit 3` → `ClaudePet v0.22  Latest  v0.22  2026-09-11T00:43:39Z`
  first. No `v0.23` tag or release exists locally or remotely.
- **User authorization, as carried in the release commit body** (typed by the user
  first-hand in the Developer's session on 2026-09-11 and quoted there verbatim):
  "23으로 배포해! 그리고 최신버전이 있으면 한방에 최신버전으로 업데이트 가능하게 하고".
  This Verifier did not see it first-hand; it is cited from the commit, not asserted.

### Command and environment

```
cwd: /Users/yeongyu/claude-pet (repository root)
python3 -m unittest discover -s tests -v
python3 --version → Python 3.13.7 (/Library/Frameworks/Python.framework/Versions/3.13/bin/python3)
CLAUDEPET_RUN_LIVE_UPDATER_TESTS and CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES: unset
```

The two opt-in live classes were left off by design: they inspect
`/Applications/ClaudePet.app`, which this assignment forbids touching.

### §5 provenance

- **Grouping key:** one unittest test case as discovered by `unittest discover` — one
  `test_*` method; the verbose output carries 508 distinct `(module.Class.method)` ids.
- **File set:** the 19 `tests/test_*.py` modules at HEAD 81619b3e, with cases per
  module: test_companion_motion 51, test_companion_play 31, test_free_roaming 6,
  test_log_estimate 14, test_manual_update_transaction 18, test_mutation_instruments 6,
  test_partial_copy_seeding 9, test_release_artifact_preflight 6, test_release_gate 31,
  test_seeding_identity 3, test_settings_and_install 66, test_signing_contract 9,
  test_source_guard 3, test_update_check_schedule 22, test_updater 92,
  test_updater_adversarial 48, test_upload_artifact_gate 64, test_v020_boundaries 18,
  test_v023_release_contract 11 — sum 508. Content hashes are listed under "Tree
  unchanged" below.
- **Window:** start 2026-09-11T02:02:50Z, end 2026-09-11T02:08:30Z (wall clock around
  the single invocation; unittest's own elapsed figure is in the raw lines).
- **Measured at:** result lines read from the captured log at 2026-09-11T02:08:34Z; tree
  re-snapshotted at 02:08:48Z.
- **Numerator / denominator:** 501 of 508 cases passed, 7 of 508 skipped, 0 of 508
  failed, 0 of 508 errored. Per-token tally of the verbose output: 501 `ok`, 7
  `skipped`, 0 `FAIL`, 0 `ERROR`. Five of those result tokens sit on the line *after* a
  loud stderr message instead of on the id line (four `skipped`, one `ok`), so a plain
  `grep ' \.\.\. ok$'` reads 500 and `grep ' \.\.\. skipped'` reads 3; the per-id count
  and the summary line agree at 508.
- **Exit status:** 0.

### Raw result lines (verbatim from the captured output)

```
START_UTC=2026-09-11T02:02:50Z
CWD=/Users/yeongyu/claude-pet
HEAD=81619b3e305d7c45e3aec02ba13d3becd1dee6f3
CMD=python3 -m unittest discover -s tests -v
…
----------------------------------------------------------------------
Ran 508 tests in 339.092s

OK (skipped=7)
…
EXIT=0
END_UTC=2026-09-11T02:08:30Z
```

Full captured output: 759 lines, 101276 bytes, SHA-256
`3e490153be6b064f11217f0101dea00f24954e687dd961508b988c8ea48449b1` (session scratchpad
`v023-gate-suite.log`; not checked in). Lines 649 and 651 are the `Ran` and `OK` lines;
the text between them and `EXIT=0` is the instruments report and the `[gate]` /
`[update]` rejection lines the gate tests emit on stderr while proving they refuse.

### Skipped cases — all seven, verbatim with their loud stderr companions

```
359:test_the_real_bundle_contains_the_symlinks_this_guard_is_about (test_updater.RealBundleAcceptanceTests.test_the_real_bundle_contains_the_symlinks_this_guard_is_about)
360:Discrimination: without an internal symlink the guard above is vacuous. ...
361:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
362:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
363:test_the_real_installed_bundle_is_accepted_by_the_preflight (test_updater.RealBundleAcceptanceTests.test_the_real_installed_bundle_is_accepted_by_the_preflight) ...
364:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
365:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
441:test_stapler_rejects_an_unstapled_bundle_with_rc_65 (test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65) ...
442:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
443:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
444:test_stapler_reports_success_for_our_stapled_bundle (test_updater.StaplerLiveContractTests.test_stapler_reports_success_for_our_stapled_bundle) ...
445:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
446:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
628:test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
629:test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
630:test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
```

Same seven cases, same reasons, as the pre-commit run in §7 above and the Reviewer's
and Coordinator's runs cited in the release commit body.

### Tree unchanged across the run

- HEAD `81619b3e305d7c45e3aec02ba13d3becd1dee6f3` before (02:02:17Z) and after (02:08:48Z).
- `git status --porcelain`: the identical 19-line `??` list before and after; no tracked
  column set either time.
- SHA-256 of `claude_pet.py`, `RELEASE_NOTES.md` and all 19 `tests/test_*.py`, taken at
  02:02:41Z and again at 02:08:48Z: byte-identical, 21 of 21 files.

```
57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b  claude_pet.py
6e0b1cdfd988f878252aa12c694dafeb3b522783ffa7575b2f3d9145b716c07b  RELEASE_NOTES.md
d7f500f4616dd583f13e9e52c45744b0756497f05513e3ea2d8ebdd520edd0f5  tests/test_companion_motion.py
62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e  tests/test_companion_play.py
e8e0255a8b47366f2cd5e8de93f9b86b47cf5a09102d007a4d1ab357870e3e6b  tests/test_free_roaming.py
cabd3c5706399e5afb4c4ecd4fc8cc15c520d30008ae5bb433ca4ca43c8258f3  tests/test_log_estimate.py
73e72d339ffb211e28fa9891b21739e5ab031d126b0408b713527d8e8f5aa420  tests/test_manual_update_transaction.py
52a08268fcd0c9766d07f5e4a61e7400a28a26875c1711fcce75bd0be60fa1e7  tests/test_mutation_instruments.py
25af166a3f79ad20927383ba58d52cf568ae0652f4ca63345e03a4f433deb241  tests/test_partial_copy_seeding.py
8f24182bd580b3fac9fb271e35c21d26285a37ea5ccc476d50575d0dab749d73  tests/test_release_artifact_preflight.py
6f690f135e8d32cd97bf69d7257f792f5cf647cde6ea4dd454951fc0dfdcb8e5  tests/test_release_gate.py
729925398ed1c6f955fd704ca5f786bd1b420dff24fa215ddce872cd2ebc54de  tests/test_seeding_identity.py
771595380771e6acb1980ceeb09b9799a7a814ad9d44800103556893dfe8f60e  tests/test_settings_and_install.py
99b8bce3039e9fca165b6ab48aae6ccc7b8d91c93ecfa297b71a5a37191520f8  tests/test_signing_contract.py
f26897087305f52e037567156547a8f27bde5afb240ec02acb540f00f0642ed1  tests/test_source_guard.py
15e469024daf9e3ab4a70a04b1828747342255b52701a63cc3719dd9e1280b2a  tests/test_update_check_schedule.py
6b8a5bae7857f78554de63b418c7759966ef047a96051e054ddfd6b62532a58d  tests/test_updater_adversarial.py
d4f82ae2074d17b2c6823f09e2e752fe644357b1088f9196cd646b78e79f510f  tests/test_updater.py
fcebcbc706846c4a58ff598a11ae261fc9f3e6f8c8d5eec20e883cc2de90d636  tests/test_upload_artifact_gate.py
47a761442d992ab7a12d1533696ccd6432f8584edc9a1395125dea5366021bb0  tests/test_v020_boundaries.py
f2972afd2995c783d170cd72f0f6a241b7ed99c6fe53964e647d52f6adbba26a  tests/test_v023_release_contract.py
```

  `claude_pet.py` is the same bytes the pre-commit record above and both executable
  harnesses pin.
- mtimes (epoch seconds), identical before and after: `claude_pet.py` 1789089135,
  `RELEASE_NOTES.md` 1789089135, the 19 test modules (range 1786578183 … 1789089762; the
  hashes above are the stronger claim, so the per-file list is not repeated). User-owned
  untracked files untouched: `diag.py` 1784689621, `release/icon_1024.png` 1783953996,
  `release/ClaudePet.iconset` 1783953996 — the same values §8 above and the release
  commit body report. This file's own mtime was 1789090431 at both snapshots; it changed
  only with this append.
- After this append the tracked tree shows exactly one modification,
  `M docs-design/release-v023-verification-20260911.md`, made after the suite window
  closed; the suite itself ran against the clean tree. Committing this record is the
  Coordinator's or Developer's call, as it was for the v0.22 gate record (`6d47df5`).

### What was not done

No `./release.sh` (any subcommand), no `./build_app.sh`, no commit, no tag, no push, no
`git add`, no `git clean`, no delete of anything; `~/.claude` and `~/.claude_pet` were
never read or written (all fixtures are synthetic). Nothing from CLAUDE.md step 3
onward was started. §6 items 3–5 remain for the Coordinator: the release-notes check,
the recorded sign-off, and naming `operator-v023` with eligibility stated.
