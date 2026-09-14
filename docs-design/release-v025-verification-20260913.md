# Verification record — ClaudePet v0.25 release preparation

- **Verifier:** `verifier-v025` (Claude Code subagent spawned from session
  `55c3dee4-727f-4a94-b960-66540b129014`). Held no other role on this release. Edited only
  files under `tests/` and created this file; ran no git write command, no `./release.sh`,
  no `./build_app.sh`, no GUI; touched no untracked file it did not create.
- **Written (UTC):** 2026-09-13T15:00Z, after the suite window below had closed.
- **Tree under test:** HEAD `36c211855059ccc86e6e408820dc4c36657177ff` (`Merge branch
  'autostart-fix'`) plus the uncommitted v0.25 preparation edits: `APP_VERSION` bumped to
  `"0.25"` (the only working-tree change to `claude_pet.py` — `git diff HEAD -- claude_pet.py`
  is that one line), the staged `**v0.25**` section in `RELEASE_NOTES.md`, and the
  documentation/site edits the Developer made. Tracked-tree modifications are listed in
  the snapshot under "Tree unchanged across the run".
- **Outside world (queried 2026-09-13T14:53:30Z):** `git tag --sort=-v:refname | head -1` →
  `v0.24`; `gh release list --limit 3` → `ClaudePet v0.24  Latest  v0.24  2026-09-12T15:55:00Z`,
  then v0.23, v0.22; `git ls-remote --tags origin | grep -c refs/tags/v0.25` → `0`. So v0.24
  is published and its notes section is frozen; the v0.25 section is staged.
- **Phase:** preparation (AGENTS.md §6). This is the pre-commit Verifier evidence for the
  v0.25 release commit; the execution-gate clean-tree re-run (item 2) is a separate run
  after that commit exists and is **not** this record.

## 1. Hashes (SHA-256, taken 2026-09-13T14:4xZ and unchanged through 14:59:35Z)

```
8d0ed11cafbc27ef00d31341e5499e447412963c0ceac02bd0a4fa9e8660eb0c  claude_pet.py          (working tree, APP_VERSION "0.25")
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh             (unchanged since the v0.24 pin)
34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6  verify_release_artifact.py (unchanged since the v0.24 pin)
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh           (unchanged since the v0.24 pin)
```

Lineage of `claude_pet.py`, for whoever re-derives the pin later:

```
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  git show a1f3d22:claude_pet.py  (v0.24 release commit — the bytes the old pin named)
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  git show HEAD:claude_pet.py     (36c2118 — Track A + Track B landed, APP_VERSION still "0.24")
8d0ed11cafbc27ef00d31341e5499e447412963c0ceac02bd0a4fa9e8660eb0c  claude_pet.py                   (working tree — HEAD + the one-line bump)
```

## 2. Pins re-derived

| File | Constant | Old (v0.24 pin) | New | Basis |
| --- | --- | --- | --- | --- |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_APP_SOURCE_SHA256` | `6f95bc8b…56d2e4` | `8d0ed11c…60eb0c` | diff review below |
| `tests/test_manual_update_transaction.py` | `REVIEWED_APP_SOURCE_SHA256` | `6f95bc8b…56d2e4` | `8d0ed11c…60eb0c` | diff review below |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_RELEASE_SHA256` | `a5b25686…146e23` | unchanged | file unchanged since a1f3d22 |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_VERIFIER_SHA256` | `34c4e57f…dd47c6` | unchanged — **but see §7(a)** | file unchanged since a1f3d22 |
| `tests/test_manual_update_transaction.py` | `REVIEWED_BUILD_APP_SHA256` | `db8e1ff9…dd96b` | unchanged | file unchanged since a1f3d22 |

Both module headers say what the re-pin is meant to follow: `test_manual_update_transaction.py`
— "these behavioural tests refuse to execute any extracted shell until a verifier has read
the new function and updated the hash"; `test_upload_artifact_gate.py`'s
`assert_reviewed_file` — "refusing to run it until a verifier reviews and repins the new
bytes". Each prints `expected … found …` on mismatch; the found value printed by the
Track-B round-2 run (`6e9f76eb…`, `0cd17cef…` in `docs-design/track-b-verification-20260913.md`)
predates the autostart-fix merge and the bump, so the value pinned here was recomputed from
the working tree, not copied from that record.

**Diff review (`git diff a1f3d22 -- claude_pet.py`, 451 insertions / 32 deletions).**
Definitions added or changed, from `grep -E "^[-+](def |class |[A-Za-z_]+ = )"` over that
diff: `APP_VERSION` (0.24 → 0.25); Track A — `OAUTH_FAIL_RETRY_SEC`, `_oauth_token_cache`
(three new keys), `OAUTH_STATUS` (`last_error`), `_credentials_path`, `_stat_sig`,
`_credentials_sig`, `_read_credentials_file`, `_token_from_file` (rewritten),
`_forget_oauth_token`, `_remember_oauth_token`, `_revalidate_oauth_token`; Track B —
`SM_STATUS_*` (4), `_AUTOSTART_STATE_BY_STATUS`, `autostart_state`, `autostart_service`,
`autostart_current`, `autostart_read_state`, `autostart_toggle`, `uninstall_autostart`,
`_autostart_err_summary`, `autostart_open_login_items`, plus the `uninstall_autostart`
step inside `do_uninstall` and the menu item/handler inside `run_gui`. The symbols the two
pinned harnesses depend on — `--with-update-lock`, `_acquire_update_lock`,
`UPDATE_LOCK_DIR`, `validate_update_app`, `_zip_members_are_safe`, `UPDATE_ASSET_NAMES`,
`INSTALLED_BUNDLE_NAME`, `BUNDLED_PET_*`, the CLI `argv` dispatch — do **not** appear in
the diff (`git diff a1f3d22 -- claude_pet.py | grep -n <those names>` is empty). The
harnesses' read of `APP_VERSION` is by regex at import time in both modules, so the bump
needs no anchor change. On that basis the new bytes are pinned as reviewed.

## 3. `tests/test_v024_release_contract.py` — decision

**It is not a v0.24-only historical contract; it is the per-release contract module, and
its own docstring says how it is carried forward:** "Lineage: test_v022 → test_v023 → this
file; each release renames the module with `git mv` and rewrites it for the version its
release commit carries." Two of its classes are explicitly *published-contract* classes
(v0.23's promises, kept after that release went out), and the release commit a1f3d22
did exactly this carry-forward (`tests/test_v023_release_contract.py | 419 ----`,
`tests/test_v024_release_contract.py | 656 ++++`, `verify_release_artifact.py | 19 +-` in
`git show a1f3d22 --stat`).

So the module was carried forward to `tests/test_v025_release_contract.py`, with these
rules applied to each test:

- **Tracks the current release → moved to 0.25.**
  `test_v024_version_and_final_source_pins_propagate` → `test_v025_…`: `APP_VERSION` must be
  `"0.25"`, the `--expect-version` usage example must read `0.25`, stale list is now
  `0.24 / 0.23 / 0.26`; the five pin cross-checks are unchanged.
  `test_v024_is_the_only_unpublished_heading…` → `test_v025_…above_v024`: `["0.25", "0.24"]`.
- **About v0.24 facts → kept true, status renamed.** `StagedV024NotesFormatTests` became
  `PublishedV024NotesContractTests`: the v0.24 section is published now (tag + release of
  2026-09-12T15:55Z), so its bytes are frozen and its promises are contracts. **Every
  assertion and every `test_v024_*` method name is byte-for-byte the v0.24 Verifier's**;
  only the class name and docstring changed. `PublishedV023NotesContractTests`,
  `ReleaseNotesPolicyTests` and `SummaryMemoContractTests` are untouched.
- **New for v0.25.** `PUBLISHED_V024_AND_OLDER_SHA256 =
  c38940804b5b94ef72bf49727ac41a82d672dc779d45e53a3436a2460a1cddb4` (suffix from `**v0.24**`
  through EOF, 19446 bytes of the 23826-byte `git show a1f3d22:RELEASE_NOTES.md`; identical
  in `HEAD:RELEASE_NOTES.md` and in the 24476-byte working tree, computed 2026-09-13T14:4xZ)
  with `test_published_v024_and_older_bytes_are_untouched`; and `StagedV025NotesFormatTests`
  (5 tests): the CLAUDE.md format gate for the v0.25 section (its normalized body is 290
  characters), and four claim↔source pairs — the quoted "로그인 시 자동 실행" against
  `TR["ko"]["menu_autostart"]` and the menu actually adding it; "시스템 설정 … 에서 끄면 메뉴에도
  꺼진 것으로 보입니다" against `autostart_read_state` calling `status()`, `autostart_toggle`
  re-reading after the call, none of the four autostart functions touching
  `RUNTIME`/config, and `run_gui`'s `autostart_read` hook; "재시작 없이 정확 모드로" against the
  rotation signal (`_credentials_sig`), re-validation, the forced re-read on 401/403, the
  `suspect` flag, and `OAUTH_FAIL_RETRY_SEC < OAUTH_CACHE_SEC` consulted by
  `fetch_exact_usage`; the quoted "완전 삭제…" against `TR["ko"]["menu_uninstall"]` and "내 펫
  폴더는 남깁니다" against `UNINSTALL_PATHS` naming `CONFIG_PATH` and `UPDATE_LOCK_DIR` but never
  `USER_PET_HOME` (by name or path text), with `do_uninstall` deleting only through
  `uninstall_targets`. The Windows halves of the v0.25 sentences are not checkable in this
  tree and are stated as such in the docstring, as v0.24 did for `claude-pet-win.zip`.
- **The rename was done with a filesystem `mv`, not `git mv`**, because this assignment
  forbids git write commands. The working tree therefore shows
  ` D tests/test_v024_release_contract.py` and `?? tests/test_v025_release_contract.py`.
  **Whoever stages the release commit must name both paths** —
  `git add tests/test_v024_release_contract.py tests/test_v025_release_contract.py` — so git
  records the rename (a1f3d22 recorded the v0.23→v0.24 step as delete + add for the same
  reason: similarity below 50 %). Staging only the new path leaves the deleted module in
  the index.

## 4. Red before green (AGENTS.md §3)

The new and changed gating tests were observed failing by mutation: for each, the file it
reads (`RELEASE_NOTES.md` or `claude_pet.py`) was copied to the session scratchpad with one
targeted change, the test module's path constant was pointed at the copy, and that single
test was run. Every needle is checked to occur exactly the expected number of times before
replacement (the `test_mutation_instruments.py` lesson), and nothing under the repository
was written. Instrument: scratchpad `mutate_v025.py`; log: scratchpad `mutants.log`
(66 lines, SHA-256 `080a1bdacd743b4c5efdbd4444a7a7206959fd02c1946417086beabd6b43bbd5`,
run 2026-09-13T14:53:21Z). Result: **21 mutants, 21 caught, 0 not caught**. Verbatim
(the instrument prints the last line of each failure):

```
RED    | notes: nested bullet inside v0.25
        StagedV025NotesFormatTests.test_v025_notes_follow_the_three_bullet_450_character_format
        - bullet 1 has 3 sentences; CLAUDE.md allows 1-2
RED    | notes: a hash-shaped token in v0.25
        StagedV025NotesFormatTests.test_v025_notes_follow_the_three_bullet_450_character_format
        - remove hash: 'a1f3d22'
RED    | notes: one byte of the published v0.24 section changed
        PublishedNotesImmutabilityTests.test_published_v024_and_older_bytes_are_untouched
         : published v0.24-and-older bytes were rewritten or dropped
RED    | notes: v0.25 quotes a reworded autostart label
        StagedV025NotesFormatTests.test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string
        AssertionError: Regex didn't match: '우클릭\\s*메뉴에\\s*\\"로그인\\ 시\\ 자동\\ 실행\\"' not found in '…'
RED    | source: TR ko menu_autostart reworded
        StagedV025NotesFormatTests.test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string
         : the v0.25 notes quote this context-menu label
RED    | source: menu no longer adds menu_autostart
        StagedV025NotesFormatTests.test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string
        AssertionError: 'menu_autostart' not found in {…}
RED    | source: autostart_read_state answers from a stored flag, no status()
        StagedV025NotesFormatTests.test_v025_autostart_state_is_read_from_the_os_and_never_stored
        AssertionError: 0 != 1 : autostart_read_state must ask the service for status() exactly once
RED    | source: autostart_toggle assumes registered means on (no re-read)
        StagedV025NotesFormatTests.test_v025_autostart_state_is_read_from_the_os_and_never_stored
        AssertionError: 1 != 2 : autostart_toggle must read the state before and re-read it after the call
RED    | source: autostart_toggle persists the state into RUNTIME
        StagedV025NotesFormatTests.test_v025_autostart_state_is_read_from_the_os_and_never_stored
        + [] : autostart_toggle must not touch the config or RUNTIME: ['RUNTIME']
RED    | source: OAUTH_FAIL_RETRY_SEC no shorter than the cache
        StagedV025NotesFormatTests.test_v025_exact_mode_recovery_is_backed_by_the_token_cache
        AssertionError: 180 not less than 180 : OAUTH_FAIL_RETRY_SEC=180 must be shorter than OAUTH_CACHE_SEC=180
RED    | source: non-auth failures no longer mark the token suspect (all three sites)
        StagedV025NotesFormatTests.test_v025_exact_mode_recovery_is_backed_by_the_token_cache
        AssertionError: "c['suspect'] = True" not found in 'def _fetch_oauth_usage(): …'
RED    | source: 401 no longer forces a re-read
        StagedV025NotesFormatTests.test_v025_exact_mode_recovery_is_backed_by_the_token_cache
        AssertionError: 0 != 1 : _fetch_oauth_usage must re-read the token once with force=True
RED    | source: rotation signal removed from _read_oauth_token
        StagedV025NotesFormatTests.test_v025_exact_mode_recovery_is_backed_by_the_token_cache
        AssertionError: [] is not true : _read_oauth_token must compare the credentials file signature (rotation signal)
RED    | source: fetch_exact_usage caches every failure for the full interval
        StagedV025NotesFormatTests.test_v025_exact_mode_recovery_is_backed_by_the_token_cache
        AssertionError: 'OAUTH_FAIL_RETRY_SEC' not found in {…} : fetch_exact_usage must cache a failure for OAUTH_FAIL_RE…
RED    | source: UNINSTALL_PATHS gains the pet home
        StagedV025NotesFormatTests.test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it
        AssertionError: 'USER_PET_HOME' unexpectedly found in {'CONFIG_PATH', 'UPDATE_LOCK_DIR', 'USER_PET_HOME'} : UNINSTALL_PATHS must never name the user's pet home
RED    | source: UNINSTALL_PATHS gains the pet home as path text
        StagedV025NotesFormatTests.test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it
        AssertionError: '.claude_pet/' unexpectedly found in '~/.claude_pet/pets' : UNINSTALL_PATHS reaches into the pet home: '~/.claude_pet/pets'
RED    | source: UNINSTALL_PATHS drops the cache directory
        StagedV025NotesFormatTests.test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it
        AssertionError: 'UPDATE_LOCK_DIR' not found in {'CONFIG_PATH'} : UNINSTALL_PATHS must delete the cache directory
RED    | source: do_uninstall removes the pet home directly
        StagedV025NotesFormatTests.test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it
        AssertionError: 'USER_PET_HOME' unexpectedly found in {…} : do_uninstall must not reach for the pet home directly
RED    | notes: v0.25 quotes the uninstall label without its ellipsis
        StagedV025NotesFormatTests.test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it
        AssertionError: '"완전 삭제…"' not found in '…'
RED    | source: APP_VERSION back at 0.24
        VersionAndPinContractTests.test_v025_version_and_final_source_pins_propagate
        - test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 8d0ed11c…, final claude_pet_mut.py is 9dd9fb12…
RED    | notes: a v0.26 heading staged above v0.25
        PublishedNotesImmutabilityTests.test_v025_is_the_only_unpublished_heading_and_sits_directly_above_v024
        + ['0.25', '0.24'] : the unpublished v0.25 section must sit directly above the published v0.24 heading, with nothing newer above it; got ['0.26', '0.25']

21 mutants, 21 caught, 0 NOT caught
```

The `APP_VERSION back at 0.24` mutant's full problem list, re-run separately, begins with
`- APP_VERSION must be one literal '0.25', got ['0.24']` (then the two `--expect-version`
lines and the two pin lines for the mutant copy) — the version assertion itself
discriminates, not only the pin side effect. The re-pinned constants in the two harness
modules were observed red by the Track-B Verifier on the pre-bump bytes
(`docs-design/track-b-verification-20260913.md` §9–§10: 48 FAIL + 8 setUpClass ERROR + 1
derived FAIL, `expected 6f95bc8b… found …`) — that is the red run for the pin family, and
this record does not repeat it.

**One test is red on the real tree, by design — see §5 and §7(a).**

## 5. Full suite

```
cwd: /Users/yeongyu/claude-pet (repository root)
python3 -m unittest discover -s tests -v
python3 --version → Python 3.13.7 (/Library/Frameworks/Python.framework/Versions/3.13/bin/python3)
CLAUDEPET_* in the launching environment: none (the two opt-in live classes stay off — they
  inspect /Applications/ClaudePet.app, which this assignment forbids touching)
start-utc: 2026-09-13T14:53:22Z   (runner-stamped)
end:       2026-09-13T14:59:02Z   (mtime of the captured log; see the runner defect below)
```

Result lines, verbatim from the captured output (scratchpad `suite.log`, 968 lines,
126049 bytes, SHA-256 `2b5be5a47ee736a35f588963d32c0380b23b55f971ff3270c1e7e763884743c7`;
not checked in):

```
----------------------------------------------------------------------
Ran 612 tests in 339.746s

FAILED (failures=1, skipped=7)
```

**§5 provenance.** Grouping key: one unittest case as discovered by `unittest discover` (one
`test_*` method); the verbose output carries 612 distinct `(module.Class.method)` ids on 612
id lines. File set: the 23 `tests/test_*.py` modules whose hashes are in §6, cases per
module: test_autostart 30, test_companion_motion 51, test_companion_play 31,
test_free_roaming 6, test_log_estimate 14, test_manual_update_transaction 18,
test_mutation_instruments 6, test_nested_pets 15, test_oauth_token_cache 11,
test_partial_copy_seeding 9, test_release_artifact_preflight 8, test_release_gate 31,
test_seeding_identity 3, test_settings_and_install 66, test_signing_contract 9,
test_source_guard 3, test_summary_pill 31, test_update_check_schedule 22, test_updater 92,
test_updater_adversarial 48, test_upload_artifact_gate 64, test_v020_boundaries 18,
test_v025_release_contract 26 — sum 612. (Corrected at 15:1xZ: the first tally of this
line read `test_upload_artifact_gate 61` and its numbers summed to 609, because the regex
that grouped ids by module accepted only lowercase names and missed
`test_the_password_database_ignores_our_HOME`, `test_mktemp_refuses_to_run_without_a_TMPDIR`
and `test_the_universal_archive_pins_BOTH_architectures`; recounted with `\w+` from the same
log, 612 ids, sum 612.) Window: 2026-09-13T14:53:22Z – 14:59:02Z.
Numerator / denominator: **604 of 612 passed, 7 of 612 skipped, 1 of 612 failed, 0 errored**
(token tally of the verbose output: 604 `ok`, 7 `skipped`, 1 `FAIL`, 0 `ERROR`; one `ok`
sits alone on its line after an interleaved stderr line, so a naive `... ok$` count reads
603). Measured from the captured log at 2026-09-13T14:59:4xZ.

### The one failure, verbatim

```
test_v025_version_and_final_source_pins_propagate (test_v025_release_contract.VersionAndPinContractTests.test_v025_version_and_final_source_pins_propagate) ... FAIL

======================================================================
FAIL: test_v025_version_and_final_source_pins_propagate (test_v025_release_contract.VersionAndPinContractTests.test_v025_version_and_final_source_pins_propagate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_v025_release_contract.py", line 317, in test_v025_version_and_final_source_pins_propagate
    self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ['verify_release_artifact.py usage must show --expect-version 0.25', 'verify_release_artifact.py still advertises --expect-version 0.24'] is not false : 
- verify_release_artifact.py usage must show --expect-version 0.25
- verify_release_artifact.py still advertises --expect-version 0.24
```

This is **not** the pin family and was not "fixed": `verify_release_artifact.py` is a
production file, and its line 28 usage example still reads `--expect-version 0.24`. Every
release commit since v0.21 moved that example with `APP_VERSION` (a1f3d22 did; the module
docstring cites `git log -S'--expect-version 0.22'`), `release.sh` passes
`$(cur_version)`, and the test exists precisely so a stale version literal cannot survive
a release. All five pin cross-checks in the same test pass (the two `APP_SOURCE` pins, the
build-script pin, the verifier pin, the release-script pin) — the failure list above is
complete. **The other 25 tests in the module pass**, including all v0.23 and v0.24
published-contract tests against the current source.

### Skipped cases — all seven, verbatim with their loud stderr companions

```
525:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
526:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
528:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
529:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
606:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
607:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
609:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
610:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
792:test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
793:test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
794:test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
```

The same seven cases, for the same reasons, as the v0.24 execution-gate run
(`docs-design/release-v024-verification-20260912.md`). The two `[updater] SKIPPED` cases at
525/528 are `test_updater.RealBundleAcceptanceTests`, the two at 606/609 are
`test_updater.StaplerLiveContractTests` (their id lines precede the stderr line, as before).

### Runner defect, stated so the record is not read as tidier than the run

The runner (scratchpad `run_suite.zsh`) assigned `status=$?` after the suite — `status` is a
read-only variable in zsh — so it aborted there: the `exit-status:` and `end-utc:` lines were
not written and the after-snapshot did not run at exit. The suite itself had already
completed and its full output was captured (the `Ran`/`FAILED` lines are in the log; the
log's mtime, 14:59:02Z, is the end time given above). unittest returns 1 on `FAILED`; that
status is inferred from the summary line, not recorded. The after-snapshot was taken by a
corrected script at 14:59:35Z, 33 s after the log closed, and is compared below.

## 6. Tree unchanged across the run

`snapshot-before.txt` (14:53:21Z) and `snapshot-after.txt` (14:59:35Z) differ in exactly one
line, their own `captured-at:`. Both show HEAD `36c2118…`, the same 15 modified tracked
paths (`CLAUDE.md`, four `README*.md`, `RELEASE_NOTES.md`, `claude_pet.py`, two
`docs-design/*.md`, three `docs/*`, the two re-pinned test modules) plus
` D tests/test_v024_release_contract.py`, the same 25 `??` entries (`diag.py`,
`release/ClaudePet.iconset/`, `release/icon_1024.png`, `release/claude-pet-win-setup.exe`,
19 earlier `docs-design/` captures and records, and `tests/test_v025_release_contract.py`),
the same `git diff --stat`, and byte-identical hashes for `claude_pet.py`,
`RELEASE_NOTES.md`, `release.sh`, `verify_release_artifact.py`, `build_app.sh` and all 23
test modules:

```
8d0ed11cafbc27ef00d31341e5499e447412963c0ceac02bd0a4fa9e8660eb0c  claude_pet.py
b5ed7a0a4f4d8bc73c6e0dc0d6fe24da33f9c4d277af78c08f4fe0079d61cec3  RELEASE_NOTES.md
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6  verify_release_artifact.py
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh
ff7be7d53056ec4e2ec513c419afb1b1db30cb996a29261d6b16e1ba22a9759c  tests/test_autostart.py
f6404f64187023e4fa040aeb7cbd8bb59e07611af2115fc191739eb883cb4918  tests/test_companion_motion.py
62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e  tests/test_companion_play.py
e8e0255a8b47366f2cd5e8de93f9b86b47cf5a09102d007a4d1ab357870e3e6b  tests/test_free_roaming.py
cabd3c5706399e5afb4c4ecd4fc8cc15c520d30008ae5bb433ca4ca43c8258f3  tests/test_log_estimate.py
e06674aaef18cd3baddb44015f669e19d1e77ed80d3efa62ccd7b051c32ec889  tests/test_manual_update_transaction.py
52a08268fcd0c9766d07f5e4a61e7400a28a26875c1711fcce75bd0be60fa1e7  tests/test_mutation_instruments.py
b1ee9ab19574e7664c1a5bb0af93052aefef9cf9e605244a2d58981220281e22  tests/test_nested_pets.py
1adccf00f5d6aa3342851d88b44290cc0069b5a83c1eba7dd722b47c7aa7d3f5  tests/test_oauth_token_cache.py
25af166a3f79ad20927383ba58d52cf568ae0652f4ca63345e03a4f433deb241  tests/test_partial_copy_seeding.py
e99ad0f45480fd0bc1d46ca5ed6ebca66ea9a57d71a2dba4c7e7b2312d76c976  tests/test_release_artifact_preflight.py
6f690f135e8d32cd97bf69d7257f792f5cf647cde6ea4dd454951fc0dfdcb8e5  tests/test_release_gate.py
729925398ed1c6f955fd704ca5f786bd1b420dff24fa215ddce872cd2ebc54de  tests/test_seeding_identity.py
b635aa67c614210ae999e9747f91403315dd32ddba19216fdc3dbf184d2491c4  tests/test_settings_and_install.py
99b8bce3039e9fca165b6ab48aae6ccc7b8d91c93ecfa297b71a5a37191520f8  tests/test_signing_contract.py
f26897087305f52e037567156547a8f27bde5afb240ec02acb540f00f0642ed1  tests/test_source_guard.py
8128240e7a85b9b3c0b8459366500dcd51d5825084b3ea35bdabcebde2c4c485  tests/test_summary_pill.py
15e469024daf9e3ab4a70a04b1828747342255b52701a63cc3719dd9e1280b2a  tests/test_update_check_schedule.py
6b8a5bae7857f78554de63b418c7759966ef047a96051e054ddfd6b62532a58d  tests/test_updater_adversarial.py
d4f82ae2074d17b2c6823f09e2e752fe644357b1088f9196cd646b78e79f510f  tests/test_updater.py
da0a5324c804cf5d4fa83cff580300701d05033b958eaf3ac6a3ae139b2b0e2c  tests/test_upload_artifact_gate.py
47a761442d992ab7a12d1533696ccd6432f8584edc9a1395125dea5366021bb0  tests/test_v020_boundaries.py
3c87547a83d7278953c3f2f783e679b282e15fd4b7518cba3f706432848be264  tests/test_v025_release_contract.py
```

mtimes (epoch seconds), identical before and after: `claude_pet.py` 1789310584,
`RELEASE_NOTES.md` 1789310561; user-owned untracked files untouched — `diag.py` 1784689621,
`release/icon_1024.png` 1783953996, `release/ClaudePet.iconset` 1783953996 (the same values
the v0.24 gate record reports).

After this record was written, `git status --porcelain` gains exactly one line,
`?? docs-design/release-v025-verification-20260913.md`.

## 7. Open items for the Coordinator / Developer (none of them mine to do)

- **(a) `verify_release_artifact.py` line 28 must move to `--expect-version 0.25`** —
  **resolved, see §9** (the Developer made the edit; the real hash equals the prediction
  below and the pin was re-derived from the real bytes). Kept as written for the history: a
  production edit, so the Developer's, and part of the release commit as it was in a1f3d22.
  After it lands, `REVIEWED_VERIFIER_SHA256` in `tests/test_upload_artifact_gate.py` must be
  re-derived by a verifier. **If the edit is exactly that one substitution and nothing
  else**, the file hashes to
  `2223ee442c6d163e04c102f7bd2f7de8ec5a2a8bb3a71259d4a9a5c5903fdcb3` (computed here from
  `sed 's/--expect-version 0\.24/--expect-version 0.25/'` over the current file — a
  prediction to be confirmed against the real bytes, not a pin; the pin in the tree is
  deliberately left at the current `34c4e57f…` because those are the bytes that exist).
  With that edit and re-pin, `test_v025_version_and_final_source_pins_propagate` goes green
  and the suite reads `OK (skipped=7)`.
- **(b) The `claude_pet.py` pin is for the bytes `8d0ed11c…`.** Any further change to
  `claude_pet.py` before the release commit — one byte — re-opens both harness pins and the
  propagation test; re-derive, do not carry forward.
- **(c) Stage the rename as two paths** (§3): `tests/test_v024_release_contract.py` (deleted)
  and `tests/test_v025_release_contract.py` (new), plus the two re-pinned modules.
- **(d)** The runner wrote its log to the session scratchpad as `suite.log`, overwriting a
  file of that name from the v0.24 execution-gate run (the v0.24 record cites that file's
  hash; the record is unaffected, the scratch copy is gone). Session-local only.

## 8. What was not done

No `./release.sh` (any subcommand), no `./build_app.sh`, no commit, no tag, no push, no
`git add`/`git mv`/`git clean`, no delete of anything tracked or user-owned, no GUI;
`~/.claude`, `~/.claude_pet` and `~/.claude_pet.json` were never read or written (every
fixture is synthetic; the mutation copies live in the session scratchpad). No production
file was edited — `claude_pet.py`, `release.sh`, `verify_release_artifact.py`, `build_app.sh`
carry the hashes in §1 before and after this work. Nothing from CLAUDE.md release step 3
onward was started; the §6 execution gate (clean-tree re-run after the release commit,
notes check, Coordinator sign-off, operator named) remains ahead.

## 9. Addendum — `verify_release_artifact.py` re-pin (2026-09-13T15:04Z–15:05Z)

- **Trigger:** a Coordinator message (an agent's message, not user input; it authorizes
  nothing outward-facing and none was taken) reporting that the Developer had made exactly
  the substitution §7(a) named — line 28 now reads `--expect-version 0.25`, nothing else in
  the file changed — and asking for the real hash, the re-pin, a run of the three modules
  named below, and this addendum. Same rules as before: test files and this record only, no
  git write commands.
- **Checked, not taken on report:** `git diff HEAD -- verify_release_artifact.py` at
  15:04:02Z is one hunk, `-  … --expect-version 0.24 …` / `+  … --expect-version 0.25 …` at
  line 28 of the usage docstring, and nothing else. `claude_pet.py`, `release.sh` and
  `build_app.sh` still hash to their §1 values at the same instant, so no other pin reopened.
- **Real SHA-256 of the edited file:**

  ```
  2223ee442c6d163e04c102f7bd2f7de8ec5a2a8bb3a71259d4a9a5c5903fdcb3  verify_release_artifact.py
  ```

  identical to the §7(a) prediction — which was a prediction; the pin below was derived
  from these bytes, and the match is what confirms the edit was exactly that substitution.
- **Pins of that file, found by `grep -rn "REVIEWED_VERIFIER_SHA256\|34c4e57f…" tests/`:**
  exactly one literal, `tests/test_upload_artifact_gate.py:60` `REVIEWED_VERIFIER_SHA256`
  (asserted at lines 377 and 1576). `tests/test_v025_release_contract.py:300` cross-checks
  that constant by name against the file and carries no literal of its own.
  **Edited:** `tests/test_upload_artifact_gate.py` — `REVIEWED_VERIFIER_SHA256`
  `34c4e57f…dd47c6` → `2223ee44…fdcb3`. That module now hashes to
  `68d182bec93306fd4b23e98d890ba40acd879bc1ae57b11e8f55f481ba37647d` (`git diff --stat HEAD`
  for it: 2 insertions, 2 deletions — this pin and the `claude_pet.py` pin of §2).
  `tests/test_manual_update_transaction.py` (`e06674aa…`) and
  `tests/test_v025_release_contract.py` (`3c87547a…`) are unchanged from §6.
- **Command and result** (from the repository root; `tests/` has no `__init__.py`, and this
  dotted form is not one of the three invocations CLAUDE.md lists as failing — it resolved
  `tests` as a namespace package and `claude_pet` from the cwd, ids printed as
  `tests.test_<module>.<Class>.<method>`):

  ```
  start-utc: 2026-09-13T15:04:22Z
  cwd: /Users/yeongyu/claude-pet
  head: 36c211855059ccc86e6e408820dc4c36657177ff
  cmd: python3 -m unittest tests.test_v025_release_contract tests.test_upload_artifact_gate tests.test_release_artifact_preflight -v
  …
  Ran 98 tests in 58.177s

  OK
  …
  exit-status: 0
  end-utc: 2026-09-13T15:05:20Z
  ```

  Captured log: scratchpad `repin.log`, 170 lines, 21909 bytes, SHA-256
  `2e46d0bfb545ecf30d59047953ccf3cb96a6b3b370c0b97bdd15747cfd59f8da` (not checked in); the
  lines elided above are the id lines and the `usage: …` / `[update] rejected: …` stderr the
  gate tests emit while proving they refuse. §5 provenance: grouping key one unittest case;
  98 distinct ids on 98 id lines — test_release_artifact_preflight 8,
  test_upload_artifact_gate 64, test_v025_release_contract 26; **98 of 98 passed, 0 failed,
  0 errored, 0 skipped** (98 `ok` tokens, no `FAIL`/`ERROR`/`skipped`/`SKIPPED` token);
  exit status 0, recorded by the runner this time (`rc=$?`, not zsh's read-only `status`).
  `test_v025_version_and_final_source_pins_propagate`, the one failure in §5, is among the
  98 and passes: all five pin cross-checks and both `--expect-version` checks hold.
- **What this does and does not establish.** These three modules are fully green against
  the current bytes. The full suite was **not** re-run for this addendum (the instruction
  named three modules); §5's run had exactly one failure, in one of these three modules,
  and the other 20 modules read the files that changed since (`verify_release_artifact.py`,
  `tests/test_upload_artifact_gate.py`) only through the pin this addendum re-derived — so
  the expectation for the next full run is `Ran 612 … OK (skipped=7)`, stated as an
  expectation. The §6 execution-gate re-run after the release commit is where that is
  recorded, not inferred.
- **Tree after this addendum** (`git status --porcelain`, 15:05Z): tracked modifications
  as in §6 plus ` M verify_release_artifact.py` (the Developer's edit); ` D
  tests/test_v024_release_contract.py`; untracked as in §6 plus this record. No production
  file was edited by this Verifier; `verify_release_artifact.py` was hashed and diffed only.
