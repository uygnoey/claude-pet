# Verification record — ClaudePet v0.24 release

This file did not exist before the section below was appended (created by that append at
2026-09-12T15:05:45Z). The pre-commit Verifier evidence for v0.24 (red-before-green, re-pins,
final pin runs) is the untracked `docs-design/summary-unify-verification-20260912.md`,
cited by the release commit body; it was not modified by this record.

## v0.24 release — execution gate: clean-tree suite re-run at commit a1f3d22ad6a2e4ea2ce53362dddc74b6f61f7559

- **Gate item:** AGENTS.md §6 execution gate, item 2 — the full suite re-run by the
  Verifier from a clean tracked tree, with the command and its output recorded rather
  than summarized. Items 3–5 (release-notes check, the Coordinator's recorded sign-off,
  naming the release operator with eligibility) are outside this record.
- **Verifier:** `verifier-v024` (Claude Code workflow subagent, spawned by the Developer
  session `55c3dee4-727f-4a94-b960-66540b129014`). Held no other role on this release.
  Ran only read-only `git` / `stat` / `shasum` / `gh release list` commands plus the test
  command below; edited only this file, and only after the suite window closed.
- **Record appended (UTC):** 2026-09-12T15:05:45Z
- **Tree under test:** HEAD `a1f3d22ad6a2e4ea2ce53362dddc74b6f61f7559` (`release: ClaudePet
  v0.24`, authored 2026-09-12T23:56:14+09:00; trailers `Developer: Claude (session
  55c3dee4-…)` / `Verifier: verifier-v024` / `Reviewer: reviewer-v024`, all distinct).
  `APP_VERSION = "0.24"` at that commit. Tracked tree clean per §6's definition:
  `git status --porcelain` at 2026-09-12T14:57:56Z (immediately before the suite) and
  again at 15:03:20Z (immediately after) set no `M`/`A`/`D`/`R` column for any tracked
  path, and `git diff --stat` was empty both times — only 22 `??` entries (`diag.py`,
  `release/ClaudePet.iconset/`, `release/icon_1024.png`, and 19 `docs-design/` captures
  and records from earlier work), the same 22 lines both times.
- **Outside world at run time:** `git tag --sort=-v:refname | head -1` → `v0.23`;
  `gh release list --limit 3` (queried 2026-09-12T14:58:15Z) →
  `ClaudePet v0.23  Latest  v0.23  2026-09-11T02:30:14Z` first, then v0.22, v0.21. No
  `v0.24` tag or release exists locally or remotely; the v0.24 notes section is therefore
  staged, not published.
- **User authorization, as carried in the release commit body** (typed by the user
  first-hand in the Developer's session on 2026-09-12 and quoted there verbatim):
  "검증 통과하면 커밋하고 windows merge해서 푸시해 그리고 릴리즈하고 windows도 이번에
  다운로드 할 수 있게 추가해주고 web도 업데이트 해라". This Verifier did not see it
  first-hand; it is cited from the commit, not asserted. Its condition ("검증 통과하면")
  is what this record speaks to for item 2 only.

### Command and environment

```
cwd: /Users/yeongyu/claude-pet (repository root)
python3 -m unittest discover -s tests -v
python3 --version → Python 3.13.7 (/Library/Frameworks/Python.framework/Versions/3.13/bin/python3)
CLAUDEPET_RUN_LIVE_UPDATER_TESTS and CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES: unset
(no CLAUDEPET_* variable was set in the launching environment)
```

The two opt-in live classes were left off by design: they inspect
`/Applications/ClaudePet.app`, which this assignment forbids touching. The suite was
launched by a zsh runner in the session scratchpad that snapshotted the tree (HEAD,
`git status --porcelain`, `git diff --stat`, SHA-256 of `claude_pet.py`, mtimes of the
file set) immediately before and immediately after the single invocation, with stdout
and stderr captured to one log.

### §5 provenance

- **Grouping key:** one unittest test case as discovered by `unittest discover` — one
  `test_*` method; the verbose output carries 565 distinct `(module.Class.method)` ids.
- **File set:** the 21 `tests/test_*.py` modules at HEAD a1f3d22a, with cases per
  module: test_companion_motion 51, test_companion_play 31, test_free_roaming 6,
  test_log_estimate 14, test_manual_update_transaction 18, test_mutation_instruments 6,
  test_nested_pets 15, test_partial_copy_seeding 9, test_release_artifact_preflight 8,
  test_release_gate 31, test_seeding_identity 3, test_settings_and_install 66,
  test_signing_contract 9, test_source_guard 3, test_summary_pill 31,
  test_update_check_schedule 22, test_updater 92, test_updater_adversarial 48,
  test_upload_artifact_gate 64, test_v020_boundaries 18, test_v024_release_contract 20 —
  sum 565. Content hashes are listed under "Tree unchanged" below.
- **Window:** start 2026-09-12T14:57:56Z, end 2026-09-12T15:03:20Z (wall clock around
  the single invocation, stamped by the runner; unittest's own elapsed figure is in the
  raw lines).
- **Measured at:** result lines read from the captured log at 2026-09-12T15:03:28Z; tree
  re-snapshotted at 15:03:20Z and re-hashed at 15:03:39Z.
- **Numerator / denominator:** 558 of 565 cases passed, 7 of 565 skipped, 0 of 565
  failed, 0 of 565 errored. Per-token tally of the verbose output: 558 `ok`, 7
  `skipped`, 0 `FAIL`, 0 `ERROR`. Four of the seven `skipped` tokens sit on the line
  *after* a loud `[updater] SKIPPED:` stderr message instead of on the id line (see the
  block below); the per-id count and the summary line agree at 565.
- **Exit status:** 0.

### Raw result lines (verbatim from the captured output)

```
start-utc: 2026-09-12T14:57:56Z
cwd: /Users/yeongyu/claude-pet
head: a1f3d22ad6a2e4ea2ce53362dddc74b6f61f7559
cmd: python3 -m unittest discover -s tests -v
…
----------------------------------------------------------------------
Ran 565 tests in 324.620s

OK (skipped=7)
…
exit-status: 0
end-utc: 2026-09-12T15:03:20Z
```

Full captured output: 876 lines, 115592 bytes, SHA-256
`3ef16a34d2126b53c0b7c59ec104b7ddcf26952b99df66acf6036b5b48d035c8` (session scratchpad
`suite.log`; not checked in). Lines 757 and 759 are the `Ran` and `OK` lines; the text
after them is the `usage: claude_pet.py --with-update-lock …` and `[update] rejected: …`
lines the gate tests emit on stderr while proving they refuse.

### Skipped cases — all seven, verbatim with their loud stderr companions

```
452:test_the_real_bundle_contains_the_symlinks_this_guard_is_about (test_updater.RealBundleAcceptanceTests.test_the_real_bundle_contains_the_symlinks_this_guard_is_about)
453:Discrimination: without an internal symlink the guard above is vacuous. ...
454:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
455:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
456:test_the_real_installed_bundle_is_accepted_by_the_preflight (test_updater.RealBundleAcceptanceTests.test_the_real_installed_bundle_is_accepted_by_the_preflight) ...
457:[updater] SKIPPED: the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
458:skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
534:test_stapler_rejects_an_unstapled_bundle_with_rc_65 (test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65) ...
535:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
536:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
537:test_stapler_reports_success_for_our_stapled_bundle (test_updater.StaplerLiveContractTests.test_stapler_reports_success_for_our_stapled_bundle) ...
538:[updater] SKIPPED: the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it
539:skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
721:test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
722:test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
723:test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
```

Same seven cases, same reasons, as the v0.23 execution-gate run
(`docs-design/release-v023-verification-20260911.md`) and as the "Ran 565 tests … OK
(skipped=7)" the release commit body cites from the pre-commit run.

### Tree unchanged across the run

- HEAD `a1f3d22ad6a2e4ea2ce53362dddc74b6f61f7559` before (14:57:56Z) and after (15:03:20Z).
- `git status --porcelain`: the identical 22-line `??` list before and after; no tracked
  column set either time; `git diff --stat` empty both times. The two snapshots differ
  only in their own `captured-at` line.
- SHA-256 of `claude_pet.py`, `RELEASE_NOTES.md` and all 21 `tests/test_*.py`, taken at
  2026-09-12T14:58:13Z (17 s into the run) and again at 15:03:39Z (after it): byte-identical,
  23 of 23 files. `claude_pet.py`'s hash was additionally taken by the runner at
  14:57:56Z (before) and 15:03:20Z (after) — the same value all four times.

```
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py
a01f2e4cd77439c095248875bb86cf3b4e2711ee12722f22ea0fa115c194513b  RELEASE_NOTES.md
f6404f64187023e4fa040aeb7cbd8bb59e07611af2115fc191739eb883cb4918  tests/test_companion_motion.py
62930be3662cbf7b026b5fac41a2bfde160a8caf431692abbc448f2aa0e7069e  tests/test_companion_play.py
e8e0255a8b47366f2cd5e8de93f9b86b47cf5a09102d007a4d1ab357870e3e6b  tests/test_free_roaming.py
cabd3c5706399e5afb4c4ecd4fc8cc15c520d30008ae5bb433ca4ca43c8258f3  tests/test_log_estimate.py
95241e183341f050653d43921474848bab3cf41e1017665ddac30d8770e47a71  tests/test_manual_update_transaction.py
52a08268fcd0c9766d07f5e4a61e7400a28a26875c1711fcce75bd0be60fa1e7  tests/test_mutation_instruments.py
b1ee9ab19574e7664c1a5bb0af93052aefef9cf9e605244a2d58981220281e22  tests/test_nested_pets.py
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
93b91c6e59c3ddc5fb44bea5dc644921600fa5603a8e6344113378a638fa0453  tests/test_upload_artifact_gate.py
47a761442d992ab7a12d1533696ccd6432f8584edc9a1395125dea5366021bb0  tests/test_v020_boundaries.py
beaeb30f39656923bb66acc5016ef1fb3f8b76786afe99e96f3f33698559245e  tests/test_v024_release_contract.py
```

- mtimes (epoch seconds), identical before (14:57:56Z) and after (15:03:20Z):
  `claude_pet.py` 1789222811 (2026-09-12T14:20:11Z), `RELEASE_NOTES.md` 1789222841
  (2026-09-12T14:20:41Z), the 21 test modules (range 1786578183 … 1789224319; the hashes
  above are the stronger claim, so the per-file list is not repeated). User-owned
  untracked files untouched: `diag.py` 1784689621, `release/icon_1024.png` 1783953996,
  `release/ClaudePet.iconset` 1783953996 — the same values before, during and after the
  run, and the same values the v0.23 gate record reports.
- After this append the tracked tree shows no modification; `git status --porcelain`
  gains exactly one line, `?? docs-design/release-v024-verification-20260912.md` (this
  file, new and untracked), made after the suite window closed; the suite itself ran
  against the clean tree. Committing this record is the Coordinator's or Developer's
  call, as it was for the v0.22 and v0.23 gate records.

### What was not done

No `./release.sh` (any subcommand), no `./build_app.sh`, no commit, no tag, no push, no
`git add`, no `git clean`, no delete of anything; `~/.claude` and `~/.claude_pet` were
never read or written (all fixtures are synthetic). Nothing from CLAUDE.md step 3
onward was started. §6 items 3–5 remain for the Coordinator: the release-notes check,
the recorded sign-off, and naming the release operator with eligibility stated.
