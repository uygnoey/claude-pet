# Verification record — summary-pill unification (staged v0.24)

Verifier: verifier-v024 (Claude, independent of the Developer session
55c3dee4-727f-4a94-b960-66540b129014). Record opened 2026-09-12T12:06Z.
This file is untracked and is not committed by the Verifier.

Scope: uncommitted Developer edits on `main` (claude_pet.py, setup.py,
build_app.sh, CLAUDE.md, RELEASE_NOTES.md, new untracked `fonts/`). The
Verifier edits only `tests/` and this file. Production files were not
touched.

All commands below ran with cwd `/Users/yeongyu/claude-pet` unless stated.
Times are UTC. Output excerpts are verbatim.


Record continued 2026-09-12T12:26Z by the same Verifier role (a previous run of this
role stopped after writing the header above and before changing any test; `git status`
at 12:26Z showed no modification under `tests/`, so nothing of it was inherited).

Deliverables named by the assignment: files under `tests/` (re-pins of
`tests/test_companion_motion.py`, the SHA256 pins in `tests/test_upload_artifact_gate.py`
and `tests/test_manual_update_transaction.py`, new modules `tests/test_summary_pill.py`
and `tests/test_nested_pets.py`) and this record. Nothing else is touched; the user-owned
untracked files (`diag.py`, `release/ClaudePet.iconset/`, `release/icon_1024.png`) and
every other untracked path were not opened for writing.

## 1. What is under verification (read at 12:26–12:40Z)

```
$ git status --porcelain      # tracked part only
 M CLAUDE.md
 M RELEASE_NOTES.md
 M build_app.sh
 M claude_pet.py
 M setup.py
?? fonts/                                                     # new, Developer-created
$ git diff --stat
 CLAUDE.md        | 115 ++++++----
 RELEASE_NOTES.md |   6 +
 build_app.sh     |  23 ++
 claude_pet.py    | 689 +++++++++++++++++++++++++++++--------------------------
 setup.py         |   4 +-
 5 files changed, 461 insertions(+), 376 deletions(-)
$ shasum -a 256 claude_pet.py release.sh verify_release_artifact.py build_app.sh
7b02316545644abc14f8d8cdbfca48ac82ce13556c8d2d4e94c736713421449b  claude_pet.py
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69  verify_release_artifact.py
fa7775db3795a58efbfc557b7e941beb28318d0df505bce42c68b6858cca2549  build_app.sh
$ shasum -a 256 <scratchpad>/claude_pet.pre-unify.py ; git show HEAD:claude_pet.py | shasum -a 256
57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b  (both)
$ git show HEAD:build_app.sh | shasum -a 256
83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6
$ git log -3 --oneline ; git tag --sort=-v:refname | head -1 ; gh release list --limit 1
046d166 docs: record the v0.23 execution gate — clean-tree suite re-run at 81619b3e and Coordinator sign-off
81619b3 release: ClaudePet v0.23
6d47df5 docs: record the v0.22 execution gate — clean-tree suite re-run at f3acb47d and Coordinator sign-off
v0.23
ClaudePet v0.23	Latest	v0.23	2026-09-11T02:30:14Z
```

So the pre-change copy the assignment points at is byte-identical to `HEAD:claude_pet.py`
(same SHA256), which makes it a faithful revert target; `release.sh` and
`verify_release_artifact.py` still carry the hashes pinned in
`tests/test_upload_artifact_gate.py` (a5b25686…, fc0d38f6…), i.e. they are unchanged;
`build_app.sh` changed (83eca429… → fa7775db…), which the assignment did not mention but
which `tests/test_manual_update_transaction.py` pins too. **v0.23 is published** (tag on
origin, GitHub release "Latest"), so the `**v0.23**` section of `RELEASE_NOTES.md` is
frozen text now and the staged, unpublished section is `**v0.24**`.

Symbols read in `claude_pet.py` (by `grep -n`, current tree): `bundled_font_path` (l.100),
`SUMMARY_FONT_FILE/NAME/FAMILY` (95–97), `_read_pet_json` (800), `_is_pet_dir` (808),
`_PETS_README` (818), `_write_pets_readme` (859), `_PET_JUNK_DIRS` (875), `_nested_pet_dir`
(878), `discover_pets` (903), `APP_VERSION = "0.23"` (938), `PILL_W = 300` (5155),
`pill_h` (5158, returns `SUMMARY_H2`), `DISPLAY_FULL/FOLDED/SUMMARY` (5814–5816),
`RoamDisplay` (5819), `roam_summary` (5881), `SUMMARY_APPROX/COLORS/SEP/SPIKE` (5930–5945),
`summary_value_kind` (5948), `roam_summary_line` (5959), `roam_summary_reset_line` (5971),
`_summary_segment_runs`, `roam_summary_runs` (6004), `roam_fit_runs` (6026), `SUMMARY_H = 30`,
`SUMMARY_H2 = 46`, `SUMMARY_MIN_W = 120` (6068–6070), `roam_pill_rect` (6073), `roam_frame`
(6095); inside `run_gui`: `register_bundled_font`, `summary_font`, `F_SUMMARY*`,
`PetView.pillRect`, `roam_summary_text` (returns `(main_runs, sub_runs, width, height)`),
`_draw_runs`, `draw_summary_pill`, `roam_apply_display`. Removed, confirmed absent by grep:
`draw_sub_pill`, `draw_exact_pill`, `draw_api_pill`, `draw_status_line`, `draw_onboard_pill`,
`draw_sub_right`, `bar_color`, `ROW_H`, `STATUS_H`, `PILL_R`, `TRACK`, `CUR_PILL`,
`apply_pill_rows`, `cur_rows_n`, `RoamDisplay.expanded`. Line numbers are approximate by
CLAUDE.md's own rule; locate by symbol.

Byte check of the published notes (2026-09-12T12:41Z, cwd repo root, python3 over
`git show 81619b3:RELEASE_NOTES.md` and the working-tree file): bytes from the
`**v0.23**` heading to EOF — SHA256 `c7ddc40a8a25ce8eefac9867032a6a14f20425c6ae0368db41a86d859c96b562`,
18516 bytes — are identical in the v0.23 release commit and the working tree; from
`**v0.22**` to EOF, `6e284e4f…` (17994 bytes) in both, matching the pin already in
`tests/test_v023_release_contract.py`. The Developer did not touch a published entry.

## 2. Baseline full suite on the current tree (RED, as expected)

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T12:27:20Z   end: 2026-09-12T12:31:36Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver/suite1.log 2>&1 ; echo rc=$?
Ran 490 tests in 255.544s
FAILED (failures=74, errors=13, skipped=7)
rc=1
```

Grouping key: one `FAIL:`/`ERROR:` header in the unittest report (a subTest failure is
one header each). File set: every `tests/test_*.py` discovered from the repo root (19
modules). Per module: test_upload_artifact_gate 48 FAIL; test_companion_motion 23 FAIL +
5 ERROR; test_manual_update_transaction 8 ERROR (all `setUpClass`); test_v023_release_contract
2 FAIL; test_settings_and_install 1 FAIL. 87 of 490 non-skipped tests in total.

Expected by the assignment and observed:

- `test_companion_motion` — the old-contract pins: `test_summary_keeps_first_two_source_labels_and_values_in_order`,
  `test_exact_summary_filters_only_first_two_rows_without_replacement`,
  `test_summary_onboarding_and_estimates_preserve_data_meaning`,
  `test_summary_invalid_values_are_not_reported_as_zero` (×7 subTests),
  `test_server_label_matching_translation_key_remains_an_exact_label`,
  `test_summary_unknown_zero_and_api_mode_are_distinct` (cost float → tuple),
  `test_approach_summary_expansion_does_not_replace_manual_preference` (×4),
  `test_hover_stop_away_keeps_summary_available_for_expansion`,
  `test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion`,
  `test_all_orientations_preserve_sprite_anchor_and_logical_home` (×4, `mode='full'` only:
  `(0, 0, 300, 220) != (2, 0, 160, 98)` shape), `test_summary_text_width_is_bounded_and_origin_uses_same_side`;
  and 5 ERRORs in `CompanionCompactRegressionTests` whose adapter stubs return the old
  2-tuple from `roam_summary_text` / call the old `roam_summary_line` with 2-tuples.
- `test_upload_artifact_gate` — all 48 are the same assertion from `assert_reviewed_file`:
  `AssertionError: '7b02316545644abc14f8d8cdbfca48ac82ce13556c8d2d4e94c736713421449b' != '57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b'
   : claude_pet.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes`
- `test_manual_update_transaction` — 8 × `setUpClass` ERROR, verbatim:
  `AssertionError: build_app.sh changed after the verifier reviewed the extracted-shell harness: expected 83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6, found fa7775db3795a58efbfc557b7e941beb28318d0df505bce42c68b6858cca2549. Do not execute the new fragment until a verifier reviews and pins it.`
  (this trips before the `claude_pet.py` pin on the next lines, which would trip too).

Not listed by the assignment — reported as findings (§6), all in `tests/` (mine to
re-pin), none a product defect:

- `test_settings_and_install.PackagingContractTests.test_startup_seeds_bundled_pets_before_discovery_and_builds_ship_them`
  — `self.assertNotEqual(setup_mutant, setup_source)` fails: the test's own mutation
  anchor `'"resources": ["frames", ".claude_pet"],'` no longer occurs in `setup.py`
  (now `["frames", ".claude_pet", "fonts"]`), so the mutation is a no-op. Instrument
  anchor drift; the contract itself (`.claude_pet` declared) still holds.
- `test_v023_release_contract.PublishedNotesImmutabilityTests.test_v023_is_the_only_unpublished_heading_and_sits_directly_above_v022`
  — `Lists differ: ['0.24', '0.23'] != ['0.23', '0.22']`. Its premise (v0.23 unpublished)
  is stale since the v0.23 release on 2026-09-11; the staged section is v0.24.
- `test_v023_release_contract.VersionAndPinContractTests.test_v023_version_and_final_source_pins_propagate`
  — the two `REVIEWED_APP_SOURCE_SHA256` pins (57b24a28…) vs the final source (7b023165…);
  clears with step 4's re-pin. `APP_VERSION` is still the literal `"0.23"` (not bumped —
  correct for a staged section).

Skips (7), verbatim reasons: `'the installed-app preflight is an opt-in live check; set
CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2), `'the real stapler contract is an
opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2), `'live
installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'`
(×3). All opt-in live tests; none hides a prerequisite silently.

Nothing else failed: the estimator, seeding, updater, signing-contract, source-guard,
release-gate and update-schedule modules were green on this tree.

## 3. New gating tests and the re-pin of the old contract — red before green

All runs below: cwd as stated, `python3 -m unittest discover -s tests -p '<module>.py' -v`,
output in `<scratchpad>/ver/*.log`. Green runs are from the repo root against the working
tree (claude_pet.py 7b023165…). **Red runs are revert-and-observe (AGENTS.md §3):** a
scratch tree `<scratchpad>/ver/red/` holding `claude_pet.py` = the pre-change copy
(57b24a28…, byte-identical to `HEAD:claude_pet.py`), `setup.py` and `build_app.sh` from
`git show HEAD:…` (83eca429…), no `fonts/`, and a copy of the test module under
`red/tests/`; run with cwd `red/` so `import claude_pet` and `Path(__file__).parents[1]`
both resolve inside that tree. The production tree was never reverted.

### 3a. `tests/test_summary_pill.py` (new, 26 tests)

Covers assignment items (a)–(k). Grouping key: one test method (subTests fold into their
method). Expected values were derived by hand from the geometry/formatter rules and
checked against a scratch probe *before* being written into the fixtures; each test's
docstring names the rival implementations the fixture separates.

```
GREEN  cwd /Users/yeongyu/claude-pet   2026-09-12T12:45Z
Ran 26 tests in 0.004s
OK
rc=0
RED    cwd <scratchpad>/ver/red        2026-09-12T12:40:10Z–12:40:11Z
Ran 26 tests in 0.007s
FAILED (failures=7, errors=21)
rc=1
```

28 of 29 red results are failures/errors; the one `ok` is
`RoamDisplayToggleTests.test_toggle_without_a_latch_is_the_plain_flip`, a positive
control for behaviour that did not change (a plain toggle still flips), which by design
distinguishes nothing about this change. First message line of each red result, verbatim:

```
ERROR test_build_app_copies_fonts_in_both_arms_and_writes_the_plist_key   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_FONT_FILE'
ERROR test_bundled_font_path_finds_the_file_next_to_the_source_and_none_elsewhere   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_FONT_FILE'
ERROR test_font_file_and_its_licence_are_in_the_tree   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_FONT_FILE'
ERROR test_setup_py_ships_fonts_as_a_resource_and_registers_them   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_FONT_FILE'
ERROR test_never_leaves_a_trailing_separator   AttributeError: module 'claude_pet' has no attribute 'roam_fit_runs'. Did you mean: 'roam_fit_text'?
ERROR test_trims_whole_runs_from_the_end_then_ellipsises_the_last_survivor   AttributeError: module 'claude_pet' has no attribute 'roam_fit_runs'. Did you mean: 'roam_fit_text'?
ERROR test_full_and_summary_return_the_same_text_sized_rect (×3 subTests)   TypeError: roam_pill_rect() got an unexpected keyword argument 'text_h'. Did you mean 'text_w'?
ERROR test_full_crop_is_the_union_not_the_whole_window_and_anchors_are_mode_free   TypeError: roam_frame() got an unexpected keyword argument 'text_h'. Did you mean 'text_w'?
ERROR test_pill_strip_height_is_the_two_line_height   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_H2'. Did you mean: 'SUMMARY_H'?
ERROR test_cost_carries_today_and_month_or_none   TypeError: roam_summary() got an unexpected keyword argument 'cost_month'
ERROR test_estimate_reset_texts_flow_through_by_gauge_key   TypeError: roam_summary() got an unexpected keyword argument 'reset_texts'
ERROR test_exact_spike_first_marks_only_the_first_given_row   TypeError: roam_summary() got an unexpected keyword argument 'spike_first'
ERROR test_cost_and_status_are_single_runs_of_their_own_kind / test_estimate_rows_translate_gauge_keys_keep_model_label_and_mark_approx / test_every_run_kind_has_a_colour_and_the_sources_differ / test_exact_rows_colour_labels_emerald_values_by_kind_and_spike_prefix / test_second_line_has_the_prefix_once_and_collapses_consecutive_duplicates / test_segments_append_on_the_same_line_and_empty_segments_vanish   AttributeError: module 'claude_pet' has no attribute 'roam_summary_runs'. Did you mean: 'roam_summary_line'?
ERROR test_thresholds_are_50_and_85_inclusive_and_spike_wins   AttributeError: module 'claude_pet' has no attribute 'summary_value_kind'
FAIL  test_mode_is_summary_while_latched_whatever_the_preference   AssertionError: True is not false        (hasattr(d, "expanded"))
FAIL  test_toggle_during_the_latch_clears_it_and_flips_the_preference (×2)   AssertionError: False != True / True != False   (old toggle returned show_panel unchanged)
FAIL  test_estimate_adds_the_model_row_with_capitalised_keyword_and_per_gauge_spikes   AssertionError: Tuples differ: ('est[20 chars] 42.0), ('weekly', 67.5)]) != ('est[20 chars] 42.0, False, None), ('weekly', 67.5, True, No[30 chars]ne)])
FAIL  test_estimate_tolerates_missing_or_malformed_spikes_and_model_gauge   AssertionError: Lists differ: [('session', 42.0), ('weekly', 17.0)] != [('session', 42.0, False, None), ('weekly', 17.0, False, None)]
FAIL  test_exact_keeps_three_gauge_rows_in_order_as_4_tuples   AssertionError: Tuples differ: ('exa[17 chars] 42.0), ('Weekly', 67.5)]) != ('exa[17 chars] 42.0, False, 'in 3h'), ('Weekly', 67.5, False[40 chars]d')])
FAIL  test_exact_reset_text_is_passed_through_verbatim_or_none   AssertionError: Lists differ: [('Session', 1.0), ('Weekly', 2.0)] != [('Session', 1.0, False, None), ('Weekly', 2.0, False, No[35 chars] 후')]
```

Rivals that the old file cannot stand in for (they are not "the old code" but a plausible
wrong new one) are separated by fixture construction rather than by a mutant run; the
decisive fixtures are stated so a reader can check the truth table without running
anything: `summary_value_kind` at exactly 50 and 85 (strict-vs-inclusive), 49 with
`spiking=True` (spike ignored); `roam_fit_runs` at width 9 over
`[AB, ' 12%', ' · ', CD, ' 34%']` (a rival that drops the last run but keeps the
separator returns `[AB, ' 12%', ' · ']`; the code returns `[AB, ' 12%']`); the sub line
over `['3h', '2d', '3h']` (collapse-all-duplicates vs collapse-consecutive) and over
`['in 3h', 'in 2d', 'in 2d']` (no-collapse vs collapse); the exact fixture with an
invalid session row and `spike_first=True` (a rival that marks the first *kept* row
marks Weekly; the code marks nothing); `roam_pill_rect` with `text_h=60 > pill_h=46`
(unclamped height); `roam_frame` with `text_h=30` vs `46` (crop `(2,0,160,98)` vs
`(2,0,160,114)`, so the height reaches the crop). The font gates read `fonts/`,
`setup.py` (AST, walked by key because the plist holds the `APP_VERSION` name) and
`build_app.sh` (text, function bodies brace-matched): in the red tree all four error on
the missing `SUMMARY_FONT_FILE` before reaching the files; the `setup.py`/`build_app.sh`
copies there are the HEAD versions without `fonts`, and `fonts/` is absent, so a rival
that only defines the constant would still fail on every one of those assertions.

### 3b. `tests/test_nested_pets.py` (new, 14 tests)

Covers items (l) and (m). Pet trees are built under `tempfile`; `claude_pet.USER_PETS_DIR`
and `PET_DIR` are pointed into it and restored by `addCleanup`; `~/.claude_pet` is never
consulted. Encoding fixtures write with `encoding="utf-8", ensure_ascii=False`.

```
GREEN  cwd /Users/yeongyu/claude-pet   2026-09-12T12:40:05Z
Ran 14 tests in 0.048s
OK
rc=0
RED    cwd <scratchpad>/ver/red        2026-09-12T12:40:11Z
Ran 14 tests in 0.047s
FAILED (failures=8, errors=1)
rc=1
```

Red messages, verbatim (first line):

```
ERROR test_nested_pet_dir_helper_contract   AttributeError: module 'claude_pet' has no attribute '_nested_pet_dir'
FAIL  test_a_single_inner_pet_wins_even_when_junk_looks_like_a_pet   AssertionError: Tuples differ: ({}, []) != ({'j': ('Inner', 'pets/j/inner')}, ['j'])
FAIL  test_among_several_the_inner_folder_named_like_the_parent_wins   AssertionError: Tuples differ: ({}, []) != ({'pick': ('Picked', 'pets/pick/pick')}, ['pick'])
FAIL  test_junk_and_dot_folders_are_skipped_at_both_levels   AssertionError: Tuples differ: ({'__MACOSX': ('__MACOSX', 'pets/__MACOSX')}, ['__MACOSX']) != ({}, [])
FAIL  test_ordering_is_by_outer_name   AssertionError: Lists differ: ['a'] != ['a', 'j', 'k', 'pick']
FAIL  test_zip_unpacked_one_level_deep_keeps_outer_id_and_inner_dir   AssertionError: Tuples differ: ({}, []) != ({'k': ('Kitty', 'pets/k/k')}, ['k'])
FAIL  test_a_fresh_readme_is_utf8_and_mentions_the_nested_layout   AssertionError: 'pets/dog/dog/pet.json' not found in 'Claude Pet — 펫 추가하는 법 / How to add a pet…
FAIL  test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept   AssertionError: 0 not greater than 0
FAIL  test_every_text_mode_open_names_utf8   AssertionError: Lists differ: [2549, 776, 836, 1359, 1392, 2107, 2116] != []
```

Five tests are `ok` against the old file — `test_flat_pet_folder_still_works`,
`test_two_inner_pets_named_unlike_the_parent_are_refused`, `test_two_levels_deep_is_not_recognised`,
`test_a_symlinked_inner_folder_is_not_followed`, `test_pet_json_with_korean_and_emoji_display_name_reads_back`.
The first four are *refusal* fixtures: the old code refuses everything nested, so they
cannot distinguish it, and are kept because they separate the plausible wrong new
implementations (recursive descent; first/last-sorted candidate; `os.path.isdir`
without `islink`), each of which returns a listed pet where the code returns none. The
fifth needs a non-UTF-8 default encoding to go red, which macOS does not have by default
— so it was run under a C locale, where Python's preferred encoding here is US-ASCII
(`PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C python3 -c "import locale; print(locale.getpreferredencoding(False))"` → `US-ASCII`;
the default run prints `UTF-8`). That is the same class of failure as the Windows cp949
observation of 2026-09-12 — a platform default that cannot encode the README / decode
the pet.json:

```
RED   cwd <scratchpad>/ver/red, env PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C LANG=C
      python3 -m unittest discover -s tests -p 'test_nested_pets.py' -v -k TextEncodingTests
Ran 4 tests
FAILED (failures=3, errors=1)
  test_pet_json_with_korean_and_emoji_display_name_reads_back   TypeError: 'NoneType' object is not subscriptable   (old _read_pet_json returned None)
  test_a_fresh_readme_is_utf8_and_mentions_the_nested_layout   AssertionError: '' != 'Claude Pet — 펫 추가하는 법 / How to add a pet\[1204 chars]).\n'   (old open(path, "w") produced a 0-byte README — the Windows symptom reproduced)
  test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept   AssertionError: 0 not greater than 0
  test_every_text_mode_open_names_utf8   AssertionError: Lists differ: [2549, 776, 836, 1359, 1392, 2107, 2116] != []
GREEN cwd /Users/yeongyu/claude-pet, same env, same command
Ran 4 tests
OK
rc=0
```

(A first attempt at the C-locale green was accidentally run with cwd still in the red
tree and therefore reproduced the red; it was discarded and rerun from the repo root —
the run quoted above.) The AST scan finds 8 text-mode `open()`/`os.fdopen()` calls in
the current file, all with `encoding="utf-8"`, and requires at least 8 so an empty scan
cannot pass; the seven line numbers in the red message are the pre-change call sites.

### 3c. `tests/test_companion_motion.py` re-pinned (51 tests)

Nineteen anchored edits (`<scratchpad>/ver/patch_a.py`; every anchor had to occur
exactly once). What changed and why, by test:

- `roam_summary` pins → 4-tuples `(label, pct, spiking, reset_text)`; exact keeps three
  gauge rows (`…first_three_…`, with a fourth `Credits` row added to each fixture so
  "no cap" is ruled out too); `cost` → `(today, None)`.
- `RoamDisplay` pins → `toggle()` during the latch clears it and returns `not show_panel`
  (`test_approach_summary_toggle_clears_the_latch_and_flips_the_preference`,
  `test_hover_stop_away_keeps_summary_until_the_user_toggles`,
  `test_no_drag_click_…`); afterwards `look` folds and `rest` follows the flipped
  preference.
- Geometry → `full` takes the summary crop/origin in all four orientations and its
  `pill` is not None; `roam_pill_rect` equal for `summary` and `full`; the widest pill
  fixture now uses `W = 308` (`= PILL_W + 8`, the app's own `geom()` — with the old
  `W = 300` and the new `PILL_W = 300` the fixture put the pill at `x = -4`, an
  artefact of the fixture, not of the app, where `W ≥ PILL_W + 8` always holds).
- Adapter regression tests → the `roam_summary_text` stub returns the new 4-tuple
  `(main, sub, width, height)`; the restored `full` presentation is `(160, 98)` (the union
  crop for a right-side layout with `text_w=130`, one line), not `(300, 220)`.
- `test_actual_summary_formatter_distinguishes_estimate_from_exact` rewritten as an
  adapter-wiring gate: credits dropped via `_label_order`, `⚠` appended only on an
  estimate after `OAUTH_STATUS["auth_error"]`, reset texts pre-formatted into the second
  line and the height switching to `SUMMARY_H2`, `spike_first` wired from `spike_info`.
- `test_actual_summary_draw_keeps_long_text_inside_pill_padding` rewritten for runs:
  ellipsised inside the padding, per-kind fonts, second line only in a two-line pill and
  drawn below the first, nothing drawn without a pill rect.
- The opt-in native smoke's compact gate (not part of the suite, not run here — it
  creates a real window) no longer demands that the arrival window be shorter than the
  expanded one, since the two are the same pill; it now demands a crop below the logical
  window height.

```
GREEN  cwd /Users/yeongyu/claude-pet   2026-09-12T12:46:12Z–12:46:15Z
Ran 51 tests in 2.926s
OK
rc=0
RED    cwd <scratchpad>/ver/red        (same module copied to red/tests/)
Ran 51 tests in 2.649s
FAILED (failures=30, errors=1)
rc=1
   1 ERROR: test_fit_contract_uses_measured_longest_prefix_and_tiny_width   ValueError: too many values to unpack (expected 2)
   1 FAIL: test_actual_summary_draw_keeps_long_text_inside_pill_padding
   1 FAIL: test_actual_summary_formatter_distinguishes_estimate_from_exact   AssertionError: … quiet companion API missing: SUMMARY_H2, roam_summary_runs
   4 FAIL: test_all_orientations_preserve_sprite_anchor_and_logical_home   AssertionError: Tuples differ: (0, 0, 300, 220) != (2, 0, 160, 98)
   4 FAIL: test_approach_summary_toggle_clears_the_latch_and_flips_the_preference   AssertionError: False != True
   1 FAIL: test_exact_summary_filters_only_first_three_rows_without_replacement
   1 FAIL: test_folded_drop_clamps_logical_envelope_before_save_and_restore   AssertionError: Tuples differ: (300.0, 220.0) != (160, 98)
   1 FAIL: test_hover_stop_away_keeps_summary_until_the_user_toggles
   1 FAIL: test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion
   1 FAIL: test_server_label_matching_translation_key_remains_an_exact_label
   7 FAIL: test_summary_invalid_values_are_not_reported_as_zero
   1 FAIL: test_summary_keeps_first_three_source_labels_and_values_in_order   AssertionError: Tuples differ: ('exa[26 chars]17.25), ('週間', 63.5)]) != ('exa[26 chars]17.25, False, None), ('週間', 63.5, False, None)[27 chars]ne)])
   1 FAIL: test_summary_onboarding_and_estimates_preserve_data_meaning
   5 FAIL: test_summary_text_width_is_bounded_and_origin_uses_same_side
   1 FAIL: test_summary_unknown_zero_and_api_mode_are_distinct   AssertionError: Tuples differ: ('cost', 0.0) != ('cost', (0.0, None))
```

The 20 tests that stay green against the old file are the motion, adapter-geometry,
menu-ownership and interruption tests whose behaviour this change does not touch.

## 4. Hash re-pins and instrument fixes in existing tests

Old → new, all in `tests/`:

| file | constant | old | new |
| --- | --- | --- | --- |
| `test_upload_artifact_gate.py` | `REVIEWED_APP_SOURCE_SHA256` | `57b24a28…4b` | `7b023165…9b` |
| `test_manual_update_transaction.py` | `REVIEWED_APP_SOURCE_SHA256` | `57b24a28…4b` | `7b023165…9b` |
| `test_manual_update_transaction.py` | `REVIEWED_BUILD_APP_SHA256` | `83eca429…d6` | `fa7775db…49` |

(full values in §1.) `REVIEWED_RELEASE_SHA256` and `REVIEWED_VERIFIER_SHA256` were not
touched: `release.sh` and `verify_release_artifact.py` hash to the pinned values
(§1). RED for all three pins is the baseline run in §2 (48 + 8 results carrying the exact
"changed after … reviewed" message).

`build_app.sh` review before re-pinning (the pin's stated precondition): the diff adds
`copy_fonts()` — staged as `Resources/fonts.new.$$`, both files required, then
`rm -rf final && mv stage final`, same shape as `copy_pet_assets` — the plist key
`ATSApplicationFontsPath = fonts` in `write_plist`, a `copy_fonts "$APP"` guard in
`build_body`, and `|| ! copy_fonts "$stage" \` inside `update_installed`'s staging
chain, before `write_plist`/`sign_app` and before `stop_pet`. Nothing else in the script
changed. The reviewed fragment the harness executes therefore now calls `copy_fonts`,
which the harness prelude did not define. Observed:

```
cwd /Users/yeongyu/claude-pet   2026-09-12T12:46:30Z–12:46:43Z   (pins updated, no shim)
Ran 18 tests in 13.228s
FAILED (failures=2)
  FAIL: test_failed_publish_restores_and_relaunches_the_old_application   AssertionError: False is not true
  FAIL: test_second_update_cannot_clean_or_prepare_until_first_transaction_finishes   AssertionError: False is not true : first updater never reached its final pre-cleanup checkpoint
```

— i.e. the staging chain failed at the undefined `copy_fonts` and the transaction
correctly refused, which is the right product behaviour and the wrong harness. Fix
(test-side): `copy_fonts() { "$TEST_PYTHON" "$TEST_HELPER" fonts "$1"; }` next to the
`copy_pet_assets` shim, and a `fonts` action in `FIXTURE_HELPER` that creates
`Contents/Resources/fonts/{Pretendard-SemiBold.otf,LICENSE-Pretendard.txt}` stubs inside
the `checked()` temp root (nothing copied from the repository).

```
cwd /Users/yeongyu/claude-pet   2026-09-12T12:46:43Z–12:46:57Z   (with shim)
Ran 18 tests in 13.553s
OK
rc=0
```

`test_settings_and_install.py`: mutation anchor
`'"resources": ["frames", ".claude_pet"],'` → `'"resources": ["frames", ".claude_pet", "fonts"],'`
(mutant drops `.claude_pet`, keeps `fonts`). RED = §2's baseline failure; GREEN:
`-k PackagingContractTests` → `Ran 4 tests … OK`. `test_upload_artifact_gate.py` after
the re-pin: `Ran 64 tests in 47.890s / OK`.

`test_v023_release_contract.py`: v0.23 is published, so the module now (i) pins the
bytes from `**v0.23**` to EOF (`PUBLISHED_V023_AND_OLDER_SHA256 = c7ddc40a…`, computed
from the release commit blob and confirmed identical in the working tree, §1) next to the
existing v0.22 pin; (ii) expects the headings `['0.24', '0.23']`; (iii) adds
`StagedV024NotesFormatTests`, the same CLAUDE.md step-2 format rule that gated v0.23,
applied to the staged v0.24 section, plus a cross-check that the percentages the note
quotes (50 %, 85 %) are the integers `summary_value_kind` compares against and that the
`▲`/`≈`/`⚠` markers it names are `SUMMARY_SPIKE`, `SUMMARY_APPROX` and a string `run_gui`
draws. Result on the current tree:

```
cwd /Users/yeongyu/claude-pet   2026-09-12T12:47Z
Ran 14 tests
FAILED (failures=1)
FAIL: test_v024_notes_follow_the_three_bullet_450_character_format
AssertionError: ['bullet 1 has 3 sentences; CLAUDE.md allows 1-2', 'bullet 2 has 3 sentences; CLAUDE.md allows 1-2', "remove internal identifier: 'Pretendard('"] is not false
```

The other 13 pass, including the new v0.23 byte pin, the heading order, the threshold/
marker cross-check, and the source-pin propagation test that failed in §2. The single
failure is a finding about the staged note (§6), not about the code, and it is left red
on purpose: the note is Developer-owned text, and papering over it would be the
non-discriminating-test hazard in reverse.

## 5. Final full suite

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T12:48:23Z   end: 2026-09-12T12:53:45Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver/suite2.log 2>&1 ; echo rc=$?
Ran 551 tests in 321.679s
FAILED (failures=1, skipped=7)
rc=1
FAIL: test_v024_notes_follow_the_three_bullet_450_character_format (test_v023_release_contract.StagedV024NotesFormatTests.test_v024_notes_follow_the_three_bullet_450_character_format)
AssertionError: ['bullet 1 has 3 sentences; CLAUDE.md allows 1-2', 'bullet 2 has 3 sentences; CLAUDE.md allows 1-2', "remove internal identifier: 'Pretendard('"] is not false
```

Grouping key: one unittest result header. File set: the 21 modules under `tests/`
(19 pre-existing + `test_summary_pill.py` + `test_nested_pets.py`). 550 of 551 results are
`ok` or an opt-in skip; 1 of 551 fails, and that one is the new documentation gate on the
staged v0.24 release note (§4, §6 finding 1) — **no test that exercises code fails.**
Compared with §2 (490 tests): +61 tests = 40 new (26 + 14) + 3 added methods in
`test_v023_release_contract.py` + the 18 `test_manual_update_transaction.py` tests the
baseline never counted because their `setUpClass` errored on the stale hash pin;
`test_companion_motion.py` keeps 51 methods (renames and re-pins only). 87 → 1 failing
results.

Skip reasons, verbatim, each an opt-in live check and each printed loudly:
`live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1` (×3),
`the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it` (×2),
`the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it` (×2).

Tree stability during verification: `claude_pet.py` = 7b023165…, `build_app.sh` =
fa7775db…, `setup.py` = 007421e6…, `release.sh` = a5b25686…, `verify_release_artifact.py`
= fc0d38f6… at 12:26Z, 12:48:45Z and 12:53:48Z (after the run); `RELEASE_NOTES.md` =
7127f72d… and `CLAUDE.md` = 14918d58… at 12:53:48Z. **Another party edited this checkout
while I worked**: `README.md`, `README.ko.md`, `README.ja.md`, `README.es.md` (mtime
21:30:32 local = 12:30:32Z, +96/−36 lines in total) and `preview.png` (12:31:31Z,
126986 → 59588 bytes) turned up as modified between my 12:26Z `git status` and 12:48Z.
None of them is read by any test, none is a production file under AGENTS.md §2, and I
did not open any of them for writing; they are outside this verification and the
Coordinator should know the Developer's diff is larger than the one I read in §1.

The dev instance of the app (PID in `<scratchpad>/dev_run.pid`) was not touched; no GUI
was launched; the opt-in native smoke in `test_companion_motion.py` was not run (it
creates a real window) — its compact gate was edited textually only (§3c) and is
therefore *unverified red* in AGENTS.md §3 terms; nothing in the suite depends on it.

## 6. Findings for the Developer / Coordinator

1. **Staged v0.24 release note breaks CLAUDE.md's step-2 format — the only red in the
   suite.** Bullets 1 and 2 each carry three sentences (the rule: 1–2 per bullet), and
   `Pretendard(OFL)` matches the same call-like "internal identifier" heuristic the v0.23
   gate used (the name is user-checkable, so this half is a heuristic hit; writing
   `Pretendard (OFL)` clears it). Everything else about the section passes: 3 top-level
   bullets, no nesting, 394 normalized characters (≤ 450), Korean, no hashes/paths/test
   prose/magnitude words, and the thresholds and markers it quotes match the source
   (`test_v024_thresholds_and_markers_match_the_source` is green). Developer-owned text;
   I did not edit it. Once reworded, the suite is expected to end OK with no other change.
2. **`build_app.sh` changed, which the assignment did not list.** `copy_fonts()` +
   plist key + calls in both arms (reviewed in §4, sound: staged beside, both files
   required, swapped in with `mv`, ordered before `stop_pet`). The manual-update harness
   pins the script's hash and shims its collaborators; it needed a `copy_fonts` shim, and
   the two transaction tests that failed without it show the product refusing correctly
   when a staging step is missing.
3. **Two instrument-drift failures in existing tests**, both re-pinned:
   `test_settings_and_install`'s `setup.py` mutation anchor (now includes `"fonts"`), and
   `test_v023_release_contract`'s premise that v0.23 is unpublished (it shipped
   2026-09-11; the module now pins the v0.23 bytes — identical to the release commit's,
   so no published entry was touched — and expects v0.24 on top).
4. **Contract ambiguities, pinned as implemented or deliberately left unpinned; decide
   before extending:** (a) with two segments, `roam_summary_runs` repeats
   `tr("reset_prefix")` per segment on the second line (`reset Session in 3h · reset GPT
   3h`) — "prefix once" holds per segment, not per line; unpinned. (b) A row without a
   reset text between two rows with equal texts collapses the later one against the
   earlier (`['3h', None, '3h']` → one entry), because the last shown text carries across;
   unpinned. (c) `spike_first` is bound to the *input's* row 0: when the session row is
   invalid nothing is marked — pinned, since moving the ▲ onto the next gauge would
   misattribute a spike. (d) In rolling weekly mode `fmt_countdown` yields `-`, so the
   second line reads e.g. `주간 -`; the README the Developer is editing documents this.
5. **Concurrent edits** (README ×4, preview.png) landed during verification — see §5.
   Not verified here.

## 7. Provenance summary (AGENTS.md §5)

- Grouping key: one unittest result header per test method or subTest.
- Window: 2026-09-12T12:26:11Z (first command) – 12:53:48Z (post-run hash check), UTC.
- File set read: the tracked diff at 12:26Z (`CLAUDE.md`, `RELEASE_NOTES.md`,
  `build_app.sh`, `claude_pet.py`, `setup.py`), untracked `fonts/`, all of `tests/`,
  `AGENTS.md`, the pre-change copy `<scratchpad>/claude_pet.pre-unify.py`, and
  `git show HEAD:{claude_pet.py,setup.py,build_app.sh}` / `81619b3:RELEASE_NOTES.md`.
- Numerators/denominators: baseline 87 failing results / 490 tests (§2); new gates red
  against the pre-change tree 28/29 (`test_summary_pill`), 9/14 (`test_nested_pets`, +4/4
  under the C locale), 31/51 (`test_companion_motion`); final 1 failing / 551 (§5).
- Measured at: the timestamps quoted beside each run.
- Files this role created or modified: `tests/test_summary_pill.py` (new),
  `tests/test_nested_pets.py` (new), `tests/test_companion_motion.py`,
  `tests/test_manual_update_transaction.py`, `tests/test_settings_and_install.py`,
  `tests/test_upload_artifact_gate.py`, `tests/test_v023_release_contract.py`, and this
  record. No production file, no documentation file, no other untracked file. No git
  command other than `status`, `diff`, `log`, `tag`, `show` was run; nothing was
  committed.

---

# Continuation — rounds 2 and 3 (same Verifier role, record resumed 2026-09-12T13:33Z)

The record above covers round 1 (12:26–12:53Z). After it the Reviewer returned FAIL
(B1 arrival-latch toggle, B2 staged note format, B3 CLAUDE.md claims —
`docs-design/summary-unify-review-20260912.md`), the Developer landed round 2 (about
13:15Z: `RoamDisplay.dismissed`, the cost budget, the adapter's credits-only filter and
memo, dead code removed, `run_gui` seeding the pets README, the font gate in
`verify_release_artifact.py`, the docs), a round-2 verification run edited the tests
under `tests/` between 13:24Z and 13:27Z and was stopped before it wrote anything here
(its scratch under `<scratchpad>/ver2/` is not cited as evidence; every run below is
mine), and the Developer then landed round 3 (13:30–13:32Z: the colour roles swapped
per the user's "세션이나 주간 이 텍스트랑 수치랑 색을 반대로 하자!", and the bundled font
changed from the CFF `.otf` to the TrueType `.ttf`). This continuation verifies the tree
as it stands after round 3, inheriting the round-2 test edits as mine to keep or fix.

All commands: cwd `/Users/yeongyu/claude-pet` unless stated; times UTC; output verbatim.
Scratch for this continuation: `<scratchpad>/ver3/`.

## C1. What is under verification now (read 13:33–13:45Z)

```
$ git log -1 --format='%H %s'
92fe4ee5a67bf7a693a90e328c6c7e582ab63b38 docs: refresh Claude Pet Pages for v0.23 and search discovery
$ git status --porcelain            # tracked part; untracked as in the review record §1 plus fonts/, the two new test modules, this file
 M CLAUDE.md
 M README.es.md
 M README.ja.md
 M README.ko.md
 M README.md
 M RELEASE_NOTES.md
 M build_app.sh
 M claude_pet.py
 M preview.png
 M setup.py
 M tests/test_companion_motion.py
 M tests/test_manual_update_transaction.py
 M tests/test_release_artifact_preflight.py
 M tests/test_settings_and_install.py
 M tests/test_upload_artifact_gate.py
 M tests/test_v023_release_contract.py
 M verify_release_artifact.py
?? fonts/                      (Pretendard-SemiBold.ttf 2671468 bytes, LICENSE-Pretendard.txt 4419 bytes)
?? tests/test_nested_pets.py
?? tests/test_summary_pill.py
$ git diff --stat (tracked)
 CLAUDE.md 139 | README.es.md 35 | README.ja.md 32 | README.ko.md 32 | README.md 33 | RELEASE_NOTES.md 6
 build_app.sh 23 | claude_pet.py 782 | preview.png Bin | setup.py 4 | verify_release_artifact.py 17
 tests/test_companion_motion.py 268 | tests/test_manual_update_transaction.py 20
 tests/test_release_artifact_preflight.py 82 | tests/test_settings_and_install.py 4
 tests/test_upload_artifact_gate.py 4 | tests/test_v023_release_contract.py 99
$ shasum -a 256   (13:33Z)
c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00  claude_pet.py
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh          (unchanged: = HEAD, = pin)
5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324  verify_release_artifact.py
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh
007421e64d90db93cae6ac1d3e7d6a42f9348b970b63c9caff7a881abe0c22a4  setup.py            (unchanged since round 1)
dded11568245aacfabf44245d40b4ab01ddf0aae18a8f8b7a12e68c4bc73b54c  CLAUDE.md
00f0fd33ff4d3556012729c9e9055976ef7bb09916ae189b9b01c3e647828503  RELEASE_NOTES.md
57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b  <scratchpad>/claude_pet.pre-unify.py  (= git show HEAD:claude_pet.py)
$ xxd -l 4 fonts/Pretendard-SemiBold.ttf
00000000: 0001 0000                                ....
$ head -c 120 fonts/LICENSE-Pretendard.txt
Copyright (c) 2021, Kil Hyung-jin (https://github.com/orioncactus/pretendard),
with Reserved Font Name Pretendard.
```

mtimes (local, UTC+9): round-3 production edits at 22:30:34 (README ×4,
RELEASE_NOTES.md) and 22:32:06 (claude_pet.py, build_app.sh, CLAUDE.md,
verify_release_artifact.py, fonts/Pretendard-SemiBold.ttf); round-2 test edits at
22:24–22:27 (test_summary_pill.py, test_nested_pets.py, test_release_artifact_preflight.py,
test_companion_motion.py, test_manual_update_transaction.py, test_upload_artifact_gate.py);
test_settings_and_install.py / test_v023_release_contract.py unchanged since round 1
(21:45–21:47). The dev instance (PID 43658 per `<scratchpad>/dev_run.pid`) was not touched.

Read first-hand: the full `git diff` of `claude_pet.py` (1145 diff lines, saved as
`<scratchpad>/ver3/claude_pet.diff`), `setup.py`, `build_app.sh`, `verify_release_artifact.py`,
`CLAUDE.md`, `RELEASE_NOTES.md`, all of `tests/` (diff plus the two new modules in full);
by `grep -n`/`sed` on the current `claude_pet.py`: `SUMMARY_FONT_FILE/NAME` (95–96),
`bundled_font_path` (99), `_read_pet_json` (799), `_is_pet_dir` (807), `_write_pets_readme`
(858), `_PET_JUNK_DIRS` (874), `_nested_pet_dir` (877), `discover_pets` (902),
`APP_VERSION = "0.23"` (937), `_label_order` (2487), `fmt_countdown` (5080), `PILL_W` (5108),
`pill_h` (5111), `DISPLAY_*` (5762–5764), `RoamDisplay` (5767, all of it), `roam_summary`
(5835), `SUMMARY_APPROX/COLORS/SEP/SPIKE` (5885–5901), `summary_value_kind` (5904),
`roam_summary_line` (5915), `roam_summary_reset_line` (5927), `_summary_segment_runs` (5932),
`roam_summary_runs` (5962), `roam_fit_runs` (5984), `SUMMARY_H/H2/MIN_W` (6026–6028),
`roam_pill_rect` (6031), `roam_frame` (6053); inside `run_gui`: `register_bundled_font`
(6143), `summary_font` (6158), `spike_info` (6344), `roam_summary_text` (6795, all of it),
`_draw_runs`, `draw_summary_pill` (6847), `roam_apply_display`. Absent by grep (0 matches):
`fmt_reset`, `gauge_rows`, `pillTop`, `pillLeft`, `SUMMARY_FONT_FAMILY`, `WEEKDAYS` (only
`WEEKDAYS_FULL` remains), the TR keys `spike_prefix/left/exact_mode/log_estimate/budget/
need_budget/reset_at/am/pm`, `.expanded`, `draw_sub_pill/draw_exact_pill/draw_api_pill`,
`bar_color`, `CUR_PILL`, `OTTO`, `.otf`. Line numbers approximate (CLAUDE.md's rule).

What round 3 changed in the code, read from the source (not observed — §5 slot 1 does
not apply): in `_summary_segment_runs` the **label** run now carries
`summary_value_kind(pct, spiking)` (with the `▲` prefix when spiking) and the **value**
run carries the source kind (`exact`/`estimate`); the cost line is
`(tr('today')+' ', 'value')`, `('$x', 'cost')`, separator, `(tr('this_month')+' ',
month_kind)`, `('$y', 'cost')`, `(' / $budget', 'cost')` with `month_kind =
summary_value_kind(min(100, month/budget*100))` when a budget exists and `'value'`
otherwise. `SUMMARY_FONT_FILE = "Pretendard-SemiBold.ttf"`; `build_app.sh copy_fonts`
requires `Pretendard-SemiBold.ttf` + the licence; `verify_release_artifact.py check_app`
requires both files as regular non-symlink files and the font's first four bytes to be
`00 01 00 00`. One stale docstring noticed: `draw_summary_pill()` still says
"첫 줄 = 라벨(출처 색)+수치(잔여량 색)" — the pre-swap assignment (finding, §C7).

## C2. Baseline full suite on the round-3 tree, with the round-2 tests (RED, as expected)

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T13:34:12Z   end: 2026-09-12T13:38:36Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver3/suite1.log 2>&1 ; echo rc=$?
Ran 540 tests in 263.893s
FAILED (failures=58, errors=8, skipped=7)
rc=1
```

Grouping key: one `FAIL:`/`ERROR:` header (a subTest failure is one header each). File
set: the 21 `tests/test_*.py` modules discovered from the repo root. Per module:
test_upload_artifact_gate 48 FAIL, test_manual_update_transaction 8 ERROR (`setUpClass`),
test_summary_pill 5 FAIL, test_release_artifact_preflight 3 FAIL, test_companion_motion
1 FAIL, test_v023_release_contract 1 FAIL — 66 of 540. Every one is a round-3 pin, verbatim
first message line:

- hash pins (round 3 changed the three pinned production files):
  `test_upload_artifact_gate` ×48 — `AssertionError: '5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324' != '6f2153987592c4141b3155499b9483d253ea53939502320cd88bb239aec1f093'` (verify_release_artifact.py; the claude_pet.py pin on the next line would trip too);
  `test_manual_update_transaction` ×8 — `AssertionError: build_app.sh changed after the verifier reviewed the extracted-shell harness: expected fa7775db3795a58efbfc557b7e941beb28318d0df505bce42c68b6858cca2549, found db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b. Do not execute the new fragment until a verifier reviews and pins it.`;
  `test_v023_release_contract.test_v023_version_and_final_source_pins_propagate` — `['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins b994c986…, final source is c148fd7f…', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins b994c986…, final source is c148fd7f…']`.
- the colour swap (round 3):
  `test_summary_pill.test_exact_rows_colour_labels_emerald_values_by_kind_and_spike_prefix` — `Lists differ: [('▲S[22 chars]%', 'exact'), (' · ', 'status'), ('Weekly', 'w[76 chars]ct')] != [('▲S[22 chars]%', 'bad'), (' · ', 'status'), ('Weekly', 'exa[74 chars]ad')]`;
  `…test_estimate_rows_translate_gauge_keys_keep_model_label_and_mark_approx` — `Lists differ: [('세션', 'value'), (' ≈42%', 'estimate'), …] != [('세션', 'estimate'), (' ≈42%', 'value'), …]`;
  `…test_cost_runs_colour_the_month_by_budget_and_status_is_one_run` — `Tuples differ: ([('Today ', 'value'), ('$12.38', 'cost'), (' · ', [56 chars], []) != ([('Today $12.38', 'cost'), (' · ', 'status'), ('Th[40 chars], [])`;
  `test_companion_motion.test_actual_summary_formatter_distinguishes_estimate_from_exact` — `Tuples differ: ('This month ', 'warn') != ('$27.50', 'warn')`.
- the font file (round 3, `.otf` → `.ttf`):
  `test_summary_pill.test_font_file_and_its_licence_are_in_the_tree` — `'Pretendard-SemiBold.ttf' != 'Pretendard-SemiBold.otf'`;
  `…test_build_app_copies_fonts_in_both_arms_and_writes_the_plist_key` — `'Pretendard-SemiBold.otf' not found in 'copy_fonts() {…[ ! -f "$stage/Pretendard-SemiBold.ttf" ]…`;
  `test_release_artifact_preflight` ×3 (`test_cli_forwards_exact_version_and_ordered_arches_to_validator` `1 != 0`, `test_exact_checkout_code_leaf_reaches_validator` `False is not true`, `test_font_check_runs_after_the_code_leaf_check_and_needs_only_the_magic` `(False, 0) != (True, 1)`) — the round-2 fixture's "ok" font is `OTTO…`, which the round-3 gate now refuses as "not a TrueType file".

Skips (7), verbatim, all opt-in live checks: `'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'` ×3, `'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` ×2, `'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` ×2.

Nothing else failed: the round-2 gates that round 3 did not touch — `RoamDisplay.dismissed`
(test_summary_pill, test_companion_motion), the adapter's credits-only filter and memo,
dead code, the nested pets and encoding module (14/14), the staged v0.24 note format gate
(`test_v024_notes_follow_the_three_bullet_450_character_format … ok` — B2 is cleared),
the v0.23 byte pin, the estimator, seeding, updater, signing, source-guard, release-gate
and schedule modules — were green. No failure outside the four pin classes above, so no
product finding from this run.

## C3. Round-3 re-pins and new gates in `tests/` — green, then red by revert-and-observe

Patch scripts (every anchor asserted to occur exactly once): `<scratchpad>/ver3/patch_tests_r3.py`
(13:41Z) and `<scratchpad>/ver3/patch_preflight_r3.py` (13:41Z). What changed, by file:

- `tests/test_summary_pill.py` (round 2's 26 → 31 tests; +1 new method here, the other
  four were round 2's `every_latch_end`, `cost … budget`, `DeadPillCodeTests` ×3 minus
  renames): the three colour fixtures re-pinned to the swapped roles —
  `test_exact_rows_colour_labels_by_remaining_values_emerald_and_spike_prefix` expects
  `[("▲Session","bad"), (" 42%","exact"), sep, ("Weekly","warn"), (" 68%","exact"), sep, ("Fable","bad"), (" 92%","exact")]`,
  the estimate fixture `[("세션","value"), (" ≈42%","estimate"), …, ("▲Fable","bad"), (" ≈12%","estimate")]`,
  and `test_cost_runs_colour_the_month_word_by_budget_and_status_is_one_run` expects
  `[("Today ","value"), ("$12.38","cost"), sep, ("This month ", <budget kind>), ("$27.50","cost"), (" / $50","cost")]`
  with the budget-share table `20→value, 24.99→value, 25→warn, 42.49→warn, 42.5→bad, 60→bad`
  (25 of 50 is exactly 50, 42.5 of 50 exactly 85 — strict thresholds would differ) now on
  the *word*; **new** `test_source_kind_sits_on_the_value_run_and_remaining_kind_on_the_label`
  states the swap as an invariant over five rows spanning every threshold for both
  sources and the cost line (every `%` run carries its source kind, every label run its
  remaining kind, the ▲ only on a label, separators only `status`). Font gates:
  `SUMMARY_FONT_FILE == "Pretendard-SemiBold.ttf"`, first four bytes `00 01 00 00` and not
  `OTTO`, > 100 000 bytes, no leftover `.otf`, `fonts/` holds exactly the two files;
  `copy_fonts` must test `"$stage/Pretendard-SemiBold.ttf"` and contain no `.otf`.
- `tests/test_release_artifact_preflight.py`: `FONT_FILE` → `.ttf`, the "ok" fixture is
  TrueType magic + padding; shapes now `absent-dir, no-font, no-licence, cff (OTTO under
  the .ttf name), otf-only (the round-2 bundle), ttf-bytes-under-otf-name, empty,
  font-is-dir, font-symlink, licence-symlink`, all refused before the validator; the
  positive control (`test_font_check_runs_after_the_code_leaf_check_and_needs_only_the_magic`)
  accepts the TrueType stub. **Note on the inherited round-2 version:** on the round-3
  tree its refusal test passed *vacuously* — every shape wrote the font under the `.otf`
  name, the gate looked for `.ttf`, so every shape was refused for the wrong reason, and
  only the positive control (which failed, §C2) revealed it. Rewriting the shapes around
  the `.ttf` name is what makes the refusal test discriminate again.
- `tests/test_manual_update_transaction.py`: the `fonts` helper stub now writes
  `Pretendard-SemiBold.ttf` with the TrueType magic; the two hash pins (§C4).
- `tests/test_upload_artifact_gate.py`: the two hash pins (§C4).
- `tests/test_companion_motion.py`: in the adapter-wiring test the API-mode assertion
  becomes `main[3:5] == [("This month ", "warn"), ("$27.50", "cost")]` and
  `main[0:2] == [("Today ", "value"), ("$12.38", "cost")]`; header docstring notes round 3.
- `tests/test_nested_pets.py`, `tests/test_settings_and_install.py`,
  `tests/test_v023_release_contract.py`: unchanged this round (green as inherited).

### Green on the working tree (cwd repo root, `python3 -m unittest discover -s tests -p '<m>.py' -v`)

```
test_summary_pill                 13:41:58Z   Ran 31 tests in 0.058s   OK   rc=0
test_nested_pets                  13:41:58Z   Ran 15 tests in 0.076s   OK   rc=0
test_release_artifact_preflight   13:41:59Z   Ran 8 tests in 0.038s    OK   rc=0
test_companion_motion             13:41:59Z   Ran 51 tests in 2.868s   OK   rc=0
test_v023_release_contract        13:42:02Z   Ran 14 tests in 0.224s   OK   rc=0
test_settings_and_install         13:42:02Z   Ran 66 tests in 4.006s   OK   rc=0
test_manual_update_transaction    13:42:15Z   Ran 18 tests in 13.992s  OK   rc=0
test_upload_artifact_gate         13:42:29Z   Ran 64 tests in 48.362s  OK   rc=0
TextEncodingTests under PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C LANG=C (preferred
encoding US-ASCII), cwd repo root, 13:44:15Z   Ran 5 tests in 0.069s   OK   rc=0
```

Logs: `<scratchpad>/ver3/green_<module>.log`, `green_nested_clocale.log`.

### Red by revert-and-observe (AGENTS.md §3)

Scratch tree `<scratchpad>/ver3/red_pre/`: `claude_pet.py` = `<scratchpad>/claude_pet.pre-unify.py`
(57b24a28…, = `HEAD:claude_pet.py`), `setup.py`/`build_app.sh`/`verify_release_artifact.py`
from `git show HEAD:…` (473bd1f1…/83eca429…/fc0d38f6…), **no** `fonts/`, and the four
modules copied from `tests/` after the edits above. cwd `red_pre/`, same command. The
working tree was never reverted (hashes in §C1 re-checked after every run — unchanged).

```
RED test_summary_pill                13:43:17Z–13:43:18Z   Ran 31 tests   FAILED (failures=18, errors=42)   rc=1
    31 of 31 methods red; no method passes against the pre-change file.
RED test_nested_pets                 13:43:18Z            Ran 15 tests   FAILED (failures=9, errors=1)     rc=1
    10 of 15 red; the 5 ok are the refusal/positive-control fixtures named in round 1 §3b
    (flat folder, two unlike-named inner pets, two levels deep, inner symlink, Korean
    pet.json under a UTF-8 locale) — each separated from a plausible wrong new
    implementation by a forward mutant instead (§C5: nested_first_sorted, and round 1's
    reviewer mutants M2/M5).
RED test_nested_pets -k TextEncodingTests, C locale   13:43:2xZ   Ran 5 tests   FAILED (failures=4, errors=1)   rc=1
RED test_companion_motion            13:43:18Z–13:43:20Z   Ran 51 tests   FAILED (failures=30, errors=1)    rc=1
    15 of 51 methods red (31 headers); the 36 ok are the motion/geometry/menu tests this
    change does not touch (list in <scratchpad>/ver3/red_pre_test_companion_motion.log).
RED test_release_artifact_preflight  13:43:21Z            Ran 8 tests    FAILED (failures=10)               rc=1
    1 of 8 red — the refusal test, all 10 shapes (the HEAD gate has no font check, so
    every shape reaches the validator: `Tuples differ: (True, [('/private/var/folders/…', '0.20', {…})]) != (False, [])`);
    the 7 ok are the pre-existing code-leaf gates and the positive control.
```

First message line of each red method, verbatim (`<scratchpad>/ver3/red_pre_<module>.log`):

```
test_summary_pill
  ERROR test_build_app_copies_fonts_in_both_arms_and_writes_the_plist_key / test_bundled_font_path_finds_the_file_next_to_the_source_and_none_elsewhere / test_font_file_and_its_licence_are_in_the_tree / test_setup_py_ships_fonts_as_a_resource_and_registers_them   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_FONT_FILE'
  ERROR test_cost_carries_today_month_and_budget_or_none   TypeError: roam_summary() got an unexpected keyword argument 'cost_month'
  ERROR test_cost_runs_colour_the_month_word_by_budget_and_status_is_one_run / test_estimate_rows_translate_gauge_keys_keep_model_label_and_mark_approx / test_every_run_kind_has_a_colour_and_the_sources_differ / test_exact_rows_colour_labels_by_remaining_values_emerald_and_spike_prefix / test_second_line_has_the_prefix_once_and_collapses_consecutive_duplicates / test_segments_append_on_the_same_line_and_empty_segments_vanish / test_source_kind_sits_on_the_value_run_and_remaining_kind_on_the_label   AttributeError: module 'claude_pet' has no attribute 'roam_summary_runs'. Did you mean: 'roam_summary_line'?
  FAIL  test_estimate_adds_the_model_row_with_capitalised_keyword_and_per_gauge_spikes   AssertionError: Tuples differ: ('est[20 chars] 42.0), ('weekly', 67.5)]) != ('est[20 chars] 42.0, False, None), ('weekly', 67.5, True, No[30 chars]ne)])
  ERROR test_estimate_reset_texts_flow_through_by_gauge_key   TypeError: roam_summary() got an unexpected keyword argument 'reset_texts'
  FAIL  test_estimate_tolerates_missing_or_malformed_spikes_and_model_gauge   AssertionError: Lists differ: [('session', 42.0), ('weekly', 17.0)] != [('session', 42.0, False, None), ('weekly', 17.0, False, None)]
  ERROR test_every_latch_end_clears_the_dismissal / test_mode_is_summary_while_latched_whatever_the_preference / test_toggle_during_the_latch_dismisses_for_the_visit_and_keeps_the_preference / test_toggle_without_a_latch_is_the_plain_flip   AttributeError: 'RoamDisplay' object has no attribute 'dismissed'
  FAIL  test_exact_keeps_three_gauge_rows_in_order_as_4_tuples   AssertionError: Tuples differ: ('exa[17 chars] 42.0), ('Weekly', 67.5)]) != ('exa[17 chars] 42.0, False, 'in 3h'), ('Weekly', 67.5, False[40 chars]d')])
  FAIL  test_exact_reset_text_is_passed_through_verbatim_or_none   AssertionError: Lists differ: [('Session', 1.0), ('Weekly', 2.0)] != [('Session', 1.0, False, None), ('Weekly', 2.0, False, No[35 chars] 후')]
  ERROR test_exact_spike_first_marks_only_the_first_given_row   TypeError: roam_summary() got an unexpected keyword argument 'spike_first'
  ERROR test_full_and_summary_return_the_same_text_sized_rect   TypeError: roam_pill_rect() got an unexpected keyword argument 'text_h'. Did you mean 'text_w'?
  ERROR test_full_crop_is_the_union_not_the_whole_window_and_anchors_are_mode_free   TypeError: roam_frame() got an unexpected keyword argument 'text_h'. Did you mean 'text_w'?
  ERROR test_never_leaves_a_trailing_separator / test_trims_whole_runs_from_the_end_then_ellipsises_the_last_survivor   AttributeError: module 'claude_pet' has no attribute 'roam_fit_runs'. Did you mean: 'roam_fit_text'?
  FAIL  test_pet_view_lost_its_pill_top_and_pill_left_helpers   AssertionError: 'pillRect' not found in {'pillLeft', 'btnOrigin', … 'pillTop', …}
  ERROR test_pill_strip_height_is_the_two_line_height   AttributeError: module 'claude_pet' has no attribute 'SUMMARY_H2'. Did you mean: 'SUMMARY_H'?
  FAIL  test_removed_helpers_and_constants_are_gone   AssertionError: True is not false : fmt_reset still exists
  FAIL  test_removed_translation_keys_are_gone_from_all_four_locales_which_still_agree   AssertionError: Items in the first set but not the second: …
  ERROR test_thresholds_are_50_and_85_inclusive_and_spike_wins   AttributeError: module 'claude_pet' has no attribute 'summary_value_kind'
test_nested_pets
  FAIL  test_a_fresh_readme_is_utf8_and_mentions_the_nested_layout   AssertionError: 'pets/dog/dog/pet.json' not found in 'Claude Pet — 펫 추가하는 법 / How to add a pet…
  FAIL  test_a_single_inner_pet_wins_even_when_junk_looks_like_a_pet   AssertionError: Tuples differ: ({}, []) != ({'j': ('Inner', 'pets/j/inner')}, ['j'])
  FAIL  test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept   AssertionError: 0 not greater than 0
  FAIL  test_among_several_the_inner_folder_named_like_the_parent_wins   AssertionError: Tuples differ: ({}, []) != ({'pick': ('Picked', 'pets/pick/pick')}, ['pick'])
  FAIL  test_every_text_mode_open_names_utf8   AssertionError: Lists differ: [2549, 776, 836, 1359, 1392, 2107, 2116] != []
  FAIL  test_junk_and_dot_folders_are_skipped_at_both_levels   AssertionError: Tuples differ: ({'__MACOSX': ('__MACOSX', 'pets/__MACOSX')}, ['__MACOSX']) != ({}, [])
  ERROR test_nested_pet_dir_helper_contract   AttributeError: module 'claude_pet' has no attribute '_nested_pet_dir'
  FAIL  test_ordering_is_by_outer_name   AssertionError: Lists differ: ['a'] != ['a', 'j', 'k', 'pick']
  FAIL  test_run_gui_seeds_the_pets_readme_at_startup_not_only_from_the_menu   AssertionError: '_write_pets_readme(USER_PETS_DIR)' not found in ["print('macOS 네이티브 렌더링에 pyobjc가 필요합니다. 설치:', file=sys.stderr)", …]
  FAIL  test_zip_unpacked_one_level_deep_keeps_outer_id_and_inner_dir   AssertionError: Tuples differ: ({}, []) != ({'k': ('Kitty', 'pets/k/k')}, ['k'])
  C locale: ERROR test_pet_json_with_korean_and_emoji_display_name_reads_back   TypeError: 'NoneType' object is not subscriptable
            FAIL  test_a_fresh_readme_is_utf8_and_mentions_the_nested_layout   AssertionError: '' != 'Claude Pet — 펫 추가하는 법 / How to add a pet\[1204 chars]).\n'   (the 0-byte README of the Windows observation, reproduced)
            FAIL  test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept   AssertionError: 0 not greater than 0
            FAIL  test_every_text_mode_open_names_utf8 / test_run_gui_seeds_the_pets_readme_at_startup_not_only_from_the_menu   (as above)
test_companion_motion
  FAIL  test_actual_summary_draw_keeps_long_text_inside_pill_padding   AssertionError: {'SUMMARY_H2', 'roam_fit_runs'} is not false : quiet companion API missing: SUMMARY_H2, roam_fit_runs
  FAIL  test_actual_summary_formatter_distinguishes_estimate_from_exact   AssertionError: {'roam_summary_runs', 'SUMMARY_H2'} is not false : quiet companion API missing: SUMMARY_H2, roam_summary_runs
  FAIL  test_all_orientations_preserve_sprite_anchor_and_logical_home (×4)   AssertionError: Tuples differ: (0, 0, 300, 220) != (2, 0, 160, 98)
  FAIL  test_approach_summary_toggle_dismisses_the_visit_and_keeps_the_preference (×4)   AssertionError: 'full' != 'folded'
  FAIL  test_exact_summary_filters_only_first_three_rows_without_replacement   AssertionError: Tuples differ: ('exact', [('週間', 41.0)]) != ('exact', [('週間', 41.0, False, None), ('Fable', 93.0, False, None)])
  ERROR test_fit_contract_uses_measured_longest_prefix_and_tiny_width   ValueError: too many values to unpack (expected 2)
  FAIL  test_folded_drop_clamps_logical_envelope_before_save_and_restore   AssertionError: Tuples differ: (300.0, 220.0) != (160, 98)
  FAIL  test_hover_stop_away_keeps_summary_until_the_user_dismisses_it   AssertionError: 'full' != 'folded'
  FAIL  test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion   AssertionError: 'full' != 'folded'
  FAIL  test_server_label_matching_translation_key_remains_an_exact_label   AssertionError: Tuples differ: ('exact', [('session', 18.25)]) != ('exact', [('session', 18.25, False, None)])
  FAIL  test_summary_invalid_values_are_not_reported_as_zero (×7)   AssertionError: Tuples differ: ('estimate', [('weekly', 23.75)]) != ('estimate', [('weekly', 23.75, False, None)])
  FAIL  test_summary_keeps_first_three_source_labels_and_values_in_order   AssertionError: Tuples differ: ('exa[26 chars]17.25), ('週間', 63.5)]) != ('exa[26 chars]17.25, False, None), ('週間', 63.5, False, None)[27 chars]ne)])
  FAIL  test_summary_onboarding_and_estimates_preserve_data_meaning   AssertionError: Tuples differ: ('estimate', [('session', 0.0), ('weekly', 67.5)]) != ('estimate', [('session', 0.0, False, None), ('weekly', 67.5, False, None)])
  FAIL  test_summary_text_width_is_bounded_and_origin_uses_same_side (×5)   AssertionError: Tuples differ: (4, 66, 260, 152) != (4, 66, 156, 30)
  FAIL  test_summary_unknown_zero_and_api_mode_are_distinct   AssertionError: Tuples differ: ('cost', 0.0) != ('cost', (0.0, None, None))
```

The pre-change file is the *old* contract; it cannot stand in for a plausible wrong *new*
implementation (in particular the round-2 colour assignment, which is the one rival the
round-3 fixtures exist to separate). Those are shown red by forward mutants in §C5.

## C4. Hash re-pins (old → new), with the RED before them

| file | constant | old (round-2 pin) | new (bytes reviewed in §C1) |
| --- | --- | --- | --- |
| `test_upload_artifact_gate.py` | `REVIEWED_VERIFIER_SHA256` | `6f215398…f093` | `5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324` |
| `test_upload_artifact_gate.py` | `REVIEWED_APP_SOURCE_SHA256` | `b994c986…af92` | `c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00` |
| `test_manual_update_transaction.py` | `REVIEWED_BUILD_APP_SHA256` | `fa7775db…2549` | `db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b` |
| `test_manual_update_transaction.py` | `REVIEWED_APP_SOURCE_SHA256` | `b994c986…af92` | `c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00` |

`REVIEWED_RELEASE_SHA256` untouched: `release.sh` = `a5b25686…` (§C1) = the pin. RED is the
baseline run in §C2 (48 + 8 + 1 results carrying the exact "changed after … reviewed" /
"pins … final source is …" messages). The pins are computed by `shasum -a 256` at
13:41Z and asserted again inside the patch script before it wrote them.

Review before re-pinning (the pins' stated precondition), from the `git diff` against
HEAD (`<scratchpad>/ver3/build_files.diff`, 103 lines, read in full): `build_app.sh` —
`copy_fonts()` stages `Resources/fonts.new.$$` with `cp -R fonts`, requires
`Pretendard-SemiBold.ttf` and `LICENSE-Pretendard.txt` in the stage, then `rm -rf final &&
mv stage final` (the `copy_pet_assets` shape); `write_plist` gains
`ATSApplicationFontsPath = fonts`; `build_body` calls `copy_fonts "$APP"` after `frames`
and before `copy_pet_assets`; `update_installed` adds `|| ! copy_fonts "$stage" \` to the
staging chain before `write_plist`/`sign_app`, i.e. before `stop_pet`. Nothing else in the
script changed. `verify_release_artifact.py` — 17 added lines in `check_app()` after the
code-identity check and before `_load_app()`: both files must be regular non-symlink
files, the font readable, first four bytes `00 01 00 00`, each failure printing a
`[gate] rejected:` line and returning False. `claude_pet.py` — the full 1145-line diff
(§C1); the parts this round changed are the two kind assignments in
`_summary_segment_runs`, the cost-line runs, and `SUMMARY_FONT_FILE`.

## C5. Forward mutants of the current tree (plausible wrong *new* implementations)

Driver `<scratchpad>/ver3/mutants.py` (written by this role; the round-2 scratch driver
was not reused). Each mutant is a scratch tree `<scratchpad>/ver3/mut/<name>/` holding
copies of the **current** `claude_pet.py`, `setup.py`, `build_app.sh`,
`verify_release_artifact.py` and `fonts/`, one or more `str.replace` edits each asserted
to match exactly once (or, for `font_cff_bytes`, the font's first four bytes overwritten),
and copies of the test modules to run; cwd = the scratch tree; same discover command.
The working tree was not modified (`claude_pet.py` c148fd7f…, `build_app.sh` db8e1ff9…,
`verify_release_artifact.py` 5ba2cee2… hashed after the run). Window
2026-09-12T13:43:21Z–13:43:41Z. Grouping key: one unittest result header; the "failing
tests" column lists the methods that fail and **only** those.

| mutant (the wrong implementation) | module(s) | result | failing tests — and only these |
| --- | --- | --- | --- |
| `swap_back` — the round-2 assignment: label run by source, value run by remaining; cost `'Today $x'` one coral run, amount by budget | summary (31) / motion (51) | FAILED failures=6 / failures=1 | summary: `test_cost_runs_colour_the_month_word_by_budget_and_status_is_one_run`, `test_estimate_rows_translate_gauge_keys_keep_model_label_and_mark_approx`, `test_exact_rows_colour_labels_by_remaining_values_emerald_and_spike_prefix`, `test_source_kind_sits_on_the_value_run_and_remaining_kind_on_the_label`; motion: `test_actual_summary_formatter_distinguishes_estimate_from_exact` |
| `spike_prefix_on_value` — `▲` moved onto the value run | summary | FAILED failures=4 | the three colour fixtures above except the cost one |
| `sep_kind_source` — separators coloured by the source kind | summary | FAILED failures=4 | same three |
| `month_kind_abs` — the month word coloured by absolute dollars, not the budget share | summary | FAILED failures=2 | `test_cost_runs_colour_the_month_word_…`, `test_source_kind_sits_on_the_value_run_…` |
| `budget_zero_kept` — a zero/negative budget passed through (division by zero downstream) | summary | FAILED failures=2 (subTests) | `test_cost_carries_today_month_and_budget_or_none` |
| `toggle_flip` — round 1's toggle: clear the latch and return `not show_panel` (the Reviewer's B1) | summary / motion | FAILED failures=16 / failures=6 | summary: `test_every_latch_end_clears_the_dismissal`, `test_toggle_during_the_latch_dismisses_for_the_visit_and_keeps_the_preference`; motion: `test_approach_summary_toggle_dismisses_the_visit_and_keeps_the_preference`, `test_hover_stop_away_keeps_summary_until_the_user_dismisses_it`, `test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion` |
| `relatch_clears_dismissed` — `note("look", "approach")` resets `dismissed` every tick | summary / motion | FAILED failures=2 / failures=4 | summary: `test_toggle_during_the_latch_dismisses_…`; motion: `test_approach_summary_toggle_dismisses_…` |
| `label_order_gt2` — the adapter's round-1 filter `_label_order(label) > 2` (drops "Claude Fable 5") | motion | FAILED failures=1 | `test_actual_summary_formatter_distinguishes_estimate_from_exact` |
| `no_memo` — `roam_summary_text` re-measures on every call | motion | FAILED failures=1 | same |
| `memo_without_auth` — memo key without `auth_error` (stale ⚠ after a token error) | motion | FAILED failures=1 | same |
| `font_otf_name` — `SUMMARY_FONT_FILE = ".otf"` and `copy_fonts` requiring `.otf` (the round-2 names on the round-3 tree) | summary | FAILED failures=3 | `test_build_app_copies_fonts_in_both_arms_and_writes_the_plist_key`, `test_bundled_font_path_finds_the_file_next_to_the_source_and_none_elsewhere`, `test_font_file_and_its_licence_are_in_the_tree` |
| `font_cff_bytes` — the CFF bytes (`OTTO`) under the `.ttf` name | summary | FAILED failures=1 | `test_font_file_and_its_licence_are_in_the_tree` |
| `gate_otto` — `verify_release_artifact.py` requiring `OTTO` (the round-2 gate) | preflight (8) | FAILED | `test_bundle_without_the_font_or_with_a_non_truetype_file_is_rejected_before_validator` (the `cff` shape is accepted), plus the three positive controls `test_cli_forwards_…`, `test_exact_checkout_…`, `test_font_check_runs_after_…` (the TrueType "ok" fixture is refused) |
| `gate_no_font_check` — the font block neutralised (HEAD's behaviour on the new file) | preflight | FAILED | `test_bundle_without_the_font_…` only (all 10 shapes reach the validator) |
| `no_startup_readme` — `run_gui` no longer seeds the pets README | nested (15) | FAILED failures=1 | `test_run_gui_seeds_the_pets_readme_at_startup_not_only_from_the_menu` |
| `nested_first_sorted` — `_nested_pet_dir` returns the first sorted candidate | nested | FAILED failures=3 | `test_among_several_the_inner_folder_named_like_the_parent_wins`, `test_ordering_is_by_outer_name`, `test_two_inner_pets_named_unlike_the_parent_are_refused` |

16 mutants built, 16 caught; every failing set is the one the test docstrings name, and
no unrelated test fails in any mutant (the fixtures discriminate in both directions).
Logs: `<scratchpad>/ver3/mut/<name>/run_<module>.log`; summary `<scratchpad>/ver3/mutants.out`.

## C6. Findings for the Developer / Coordinator (this continuation)

1. **No product defect found in rounds 2–3.** Every baseline failure (§C2) was a pin of
   the round-2 contract that round 3 changed on purpose; after the re-pins every module
   is green (§C3) and the full suite is recorded in §C7.
2. **Stale docstring, comment-only:** `draw_summary_pill()` in `run_gui` still says
   "첫 줄 = 라벨(출처 색)+수치(잔여량 색)" — the pre-swap assignment. The code, the
   `SUMMARY_COLORS` comment block, CLAUDE.md and RELEASE_NOTES say the swapped roles.
   Developer-owned; not edited.
3. **The inherited round-2 preflight fixture passed vacuously on the round-3 tree** (§C3):
   its ten refusal shapes were all refused for the wrong reason (no `.ttf` present), and
   only the positive control caught the drift. Rewritten around the `.ttf` name; the
   `gate_otto`/`gate_no_font_check` mutants now show both directions.
4. **Contract points pinned as implemented / left unpinned (carried from round 1 §6.4,
   still true in the current source):** (a) with two segments the reset word repeats per
   segment on the second line; (b) a row without a reset text between two rows with equal
   texts collapses the later one; (c) `spike_first` marks the input's row 0 only (pinned);
   (d) rolling weekly shows `주간 -` on the reset line (CLAUDE.md now says so). Also,
   `SUMMARY_COLORS["status"]` and `["value"]` are the same colour (`TXT_MAIN`) — the
   separators and status text are white like an untouched label; harmless, noting it.
5. **Outside this role's scope, not verified here:** `README.md`/`.ko`/`.ja`/`.es`,
   `preview.png`, and the prose of `CLAUDE.md` / `RELEASE_NOTES.md` beyond what the suite
   cross-checks (`test_v024_thresholds_and_markers_match_the_source`,
   `test_v024_notes_follow_the_three_bullet_450_character_format`, both green — the
   Reviewer's B2 is cleared by the test the repo already carries). The Windows worktree
   was not opened.
6. **Locale tables:** `TR` has 99 keys in each of `en/ko/ja/es` and the four key sets are
   identical (probe 13:45Z, `import claude_pet`) — the round-2 claim holds after round 3.

## C7. Final full suite (the assignment's step 5)

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T13:44:27Z   end: 2026-09-12T13:49:52Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver3/suite2.log 2>&1 ; echo rc=$?
Ran 559 tests in 324.348s
OK (skipped=7)
rc=0
```

Grouping key: one unittest result header. File set: the 21 modules under `tests/`
(19 pre-existing + `test_summary_pill.py` + `test_nested_pets.py`). 552 of 559 results
`ok`, 7 skipped, 0 failing. Compared with §C2 (540 tests, 66 failing): +19 tests = the 18
`test_manual_update_transaction` tests the baseline never counted (their `setUpClass`
errored on the stale hash pin) + 1 new method in `test_summary_pill.py`
(`test_source_kind_sits_on_the_value_run_and_remaining_kind_on_the_label`).

Skip reasons, verbatim, each an opt-in live check that prints loudly:
`'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'` (×3),
`'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2),
`'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2).

Tree stability: `shasum -a 256` of `claude_pet.py`, `build_app.sh`, `verify_release_artifact.py`,
`setup.py`, `release.sh`, `RELEASE_NOTES.md`, `CLAUDE.md` taken immediately before
(13:44:27Z) and after (13:49:52Z) the run are identical to each other and to §C1
(`<scratchpad>/ver3/hashes_{before,after}_suite2.txt`). No other party edited the
production or documentation files during this continuation. The opt-in native smoke in
`test_companion_motion.py` was not run (it creates a window); it stays *unverified red*
as stated in round 1 §5.

## C8. Untracked work, process, provenance (AGENTS.md §4, §5)

- Files this role created or modified in this continuation: `tests/test_summary_pill.py`,
  `tests/test_release_artifact_preflight.py`, `tests/test_manual_update_transaction.py`,
  `tests/test_upload_artifact_gate.py`, `tests/test_companion_motion.py`, and this record.
  `tests/test_nested_pets.py`, `tests/test_settings_and_install.py`,
  `tests/test_v023_release_contract.py` were read and re-run but not edited this round.
  No production file, no documentation file, no README, no `fonts/` file, no Windows
  worktree, and no other untracked file was opened for writing. User-owned untracked
  files unchanged: `diag.py` (mtime 2026-07-22 12:07:01), `release/icon_1024.png`
  and `release/ClaudePet.iconset/*` (2026-07-13 23:46:36), checked at 13:45Z.
- Git commands run: `status`, `diff`, `log`, `show` only. Nothing committed, tagged,
  pushed, signed, built, installed or released; `./release.sh` and `./build_app.sh` were
  not invoked (the scripts were only read as text and copied into scratch trees where the
  tests read them as text); no GUI launched; `~/.claude` never read by a test or probe,
  `~/.claude_pet*` never written (every pet tree under `tempfile`, `USER_PETS_DIR`/`PET_DIR`
  repointed and restored by `addCleanup`); the dev instance (PID 43658) untouched.
- Grouping key: one unittest result header (suite, module and mutant runs); one grep
  match line (symbol scans); one file (hashes).
- Window: 2026-09-12T13:33:13Z (first command) – 13:49:52Z (post-suite hash check), UTC.
- File set read: the tracked diff at 13:33Z (17 paths, §C1), untracked `fonts/`, all of
  `tests/`, `AGENTS.md`, `CLAUDE.md`, the round-1 record above and the Reviewer's record,
  the pre-change copy `<scratchpad>/claude_pet.pre-unify.py`, and
  `git show HEAD:{claude_pet.py,setup.py,build_app.sh,verify_release_artifact.py}`.
- Numerators/denominators: baseline 66 failing results / 540 tests (§C2); module greens
  31/31, 15/15, 8/8, 51/51, 14/14, 66/66, 18/18, 64/64, C-locale 5/5 (§C3); red against
  the pre-change tree 31/31 methods (`test_summary_pill`), 10/15 (+5/5 under the C
  locale) (`test_nested_pets`), 15/51 methods = 31 headers (`test_companion_motion`),
  1/8 = 10 subTests (`test_release_artifact_preflight`) (§C3); mutants 16 caught / 16
  built (§C5); final 0 failing / 559, 7 opt-in skips (§C7).
- Measured at: the timestamps quoted beside each command.


---

## F. Final pin run (2026-09-12, Verifier verifier-v024)

Assignment: after round 5 (§C7, 559 tests GREEN) and the Reviewer's round-6 pass, the
Developer made the release bump and three last edits; this run re-pins the harnesses,
renames and rewrites the release-contract module for v0.24, and re-runs the suite. Same
constraints as before: only `tests/` and this record are edited; the one git write is
`git mv tests/test_v023_release_contract.py tests/test_v024_release_contract.py`; no
build, sign, tag, push, install, GUI launch, `~/.claude` read or `~/.claude_pet*` write.
All commands ran with cwd `/Users/yeongyu/claude-pet` unless stated; times UTC; output
excerpts verbatim; scratch files under `<scratchpad>/ver4/`.

### F1. What changed since round 5 (read 14:21–14:27Z)

```
$ shasum -a 256 claude_pet.py build_app.sh verify_release_artifact.py release.sh   (14:21Z)
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh
5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324  verify_release_artifact.py
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
```

Only `claude_pet.py` differs from the round-5 pins (`c148fd7f…` in both harnesses, §C4);
`build_app.sh`, `verify_release_artifact.py` and `release.sh` are byte-identical to the
values pinned in `tests/test_manual_update_transaction.py` and
`tests/test_upload_artifact_gate.py`.

**The round-5 source bytes were reconstructed, not taken on report.** `git show
HEAD:claude_pet.py > ver4/round5_recon.py; patch round5_recon.py < ver3/claude_pet.diff`
(my own round-5 diff) hashes to `c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00`
— exactly the round-5 pin — so `diff -u ver4/round5_recon.py claude_pet.py`
(`ver4/round5_to_final.diff`, 7 hunks) is the complete Developer delta since round 5:

1. `APP_VERSION = "0.23"` → `"0.24"` (the release bump).
2–5. `TR[en|ko|ja|es]["menu_toggle"]`: `Collapse/expand gauges` → `Show/hide the usage pill`,
   `게이지 접기/펴기` → `사용량 필 접기/펴기`, `ゲージの折りたたみ` → `使用量ピルの表示/非表示`,
   `Contraer/expandir medidores` → `Mostrar/ocultar la píldora`.
6. `roam_summary_text` memo key: `(RUNTIME["mode"], id(stats), …)` →
   `(RUNTIME["mode"], L["lang"], state.get("onboard"), id(stats), …)`.
7. `draw_summary_pill` docstring: `라벨(출처 색)+수치(잔여량 색)` → `라벨(잔여량 색)+수치(출처 색)`.

Nothing else. `RELEASE_NOTES.md`: the staged `**v0.24**` section (bullet 3 now names
`claude-pet-win.zip, 서명 없음`; 435 whitespace-normalised characters, 3 bullets, 2
sentences each); from `**v0.23**` to EOF is 18516 bytes and byte-identical to the same
suffix of `git show 81619b3:RELEASE_NOTES.md` (22896 bytes), sha256
`c7ddc40a8a25ce8eefac9867032a6a14f20425c6ae0368db41a86d859c96b562` = the existing pin
(checked with a Python byte comparison at 14:22Z, `equal: True`). `TR` key sets: en/ko/ja/es
each 99 keys, all identical to en (AST literal, 14:22Z).

**Deviation noticed at 14:23Z:** `verify_release_artifact.py:28` still reads
`--expect-version 0.23`. `git log --oneline -S'--expect-version 0.22' -- verify_release_artifact.py`
lists 7865af5, 13675f5, f3acb47, 81619b3 — every release commit since v0.21 moved that
usage example with `APP_VERSION`, and 81619b3's message says so ("APP_VERSION becomes
"0.23", the verify_release_artifact.py usage example follows"). The v0.23 contract module
gated it (`"--expect-version 0.23" in verifier_text`, stale 0.22/0.21/0.24 forbidden), so
the faithful v0.24 gate requires `0.24`. See F6-1; the pin is not relaxed.

### F2. Baseline full suite on the current tree, tests as of round 5 (RED)

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T14:23:04Z   end: 2026-09-12T14:27:25Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver4/baseline.log 2>&1 ; echo rc=$?
Ran 541 tests in 261.075s
FAILED (failures=49, errors=9, skipped=7)
rc=1
```

Grouping key: one unittest result header; file set: the 21 modules under `tests/`.
Failing/erroring results by module: `test_upload_artifact_gate` 48, `test_manual_update_transaction`
8 (`setUpClass` errors, so its 18 methods were not counted), `test_v023_release_contract` 1,
`test_companion_motion` 1. The first three are the expected re-pin/bump reds; the fourth
was not expected and is analysed below. Verbatim:

```
FAIL: test_a_clean_archive_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_clean_archive_is_accepted)
AssertionError: '6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4' != 'c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00'
 : claude_pet.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes
   (the same message on all 48)

ERROR: setUpClass (test_manual_update_transaction.BackupPreservationTests)
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00, found 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4
   (×8 classes)

FAIL: test_v023_version_and_final_source_pins_propagate (test_v023_release_contract.VersionAndPinContractTests.test_v023_version_and_final_source_pins_propagate)
AssertionError: ["APP_VERSION must be one literal '0.23', got ['0.24']", 'test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins c148fd7f…, final source is 6f95bc8b…', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins c148fd7f…, final source is 6f95bc8b…'] is not false

ERROR: test_actual_summary_formatter_distinguishes_estimate_from_exact (test_companion_motion.CompanionCompactRegressionTests.test_actual_summary_formatter_distinguishes_estimate_from_exact)
  File "/Users/yeongyu/claude-pet/claude_pet.py", line 6807, in roam_summary_text
    key = (RUNTIME["mode"], L["lang"], state.get("onboard"), id(stats), id(oauth), state["cost"],
                            ^
NameError: name 'L' is not defined
```

Skips, verbatim (the same seven as §C7):
`'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'` (×3),
`'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2),
`'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'` (×2).

**The `NameError` is a harness gap, not an application defect.** `L` is a module-level
global (`claude_pet.py:1023 L = {"lang": _system_lang()}`; `t()` at 1028–1029 reads
`L["lang"]`), so the application resolves it. `test_companion_motion.gui_functions`
executes the nested `roam_summary_text` inside a hand-built scope (`pure_api` + fakes)
that supplied a fake `t` but no `L`; the Developer's memo-key edit (hunk 6) added a
legitimate dependency on the global the harness never provided. The harness is mine
(`tests/`), so the fix is mine (F4). The edit itself is correct: `t()` keys its
translation on `L["lang"]`, so a memo keyed without it would hand back stale labels after
a language change, and `roam_summary` turns `onboard` into a status line, so a memo keyed
without it would let the onboarding line linger.

### F3. Hash re-pins (old → new) — the RED is F2

| File | Constant | old (round 5) | new |
| --- | --- | --- | --- |
| `tests/test_upload_artifact_gate.py:63` | `REVIEWED_APP_SOURCE_SHA256` | `c148fd7f…aa00` | `6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4` |
| `tests/test_manual_update_transaction.py:45` | `REVIEWED_APP_SOURCE_SHA256` | `c148fd7f…aa00` | `6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4` |

Applied by `sed -i ''` at 14:29:24Z (one occurrence each, read back). The other pins
(`REVIEWED_BUILD_APP_SHA256` db8e1ff9…, `REVIEWED_VERIFIER_SHA256` 5ba2cee2…,
`REVIEWED_RELEASE_SHA256` a5b25686…) already match the current bytes and are untouched.
Green after the re-pin (cwd repo root, `python3 -m unittest discover -s tests -p '<m>.py' -v`):

```
test_manual_update_transaction   14:35:13Z–14:35:26Z   Ran 18 tests in 13.384s   OK   rc=0
test_upload_artifact_gate        14:35:26Z–14:36:14Z   Ran 64 tests in 48.140s   OK   rc=0
```

### F4. `tests/test_companion_motion.py` — the harness fix and the memo gates it carries

Edit (14:31:36Z), inside `test_actual_summary_formatter_distinguishes_estimate_from_exact`
only: `lang_table = {"lang": "ko"}` added to the scope as `L`; the docstring's rival list
gains "a memo keyed without the language or the onboarding state"; after the existing
5-second-window assertions, four new checks: a language change inside the window with the
same stats object must return a different object and re-measure; `state["onboard"] =
"install"` must put `onb_install` on the first line, return a different object and
re-measure; clearing it must bring `세션 ≈42% · 주간 ≈17% ⚠` back and re-measure.

Rivals and the fixture's answer (AGENTS.md §3): (a) harness scope without `L` on the
current source → the F2 `NameError` (that baseline run is the observed red for the scope
fix); (b) memo key without the language (the round-5 key) → language assertion fails;
(c) memo key with the language but without the onboarding state → onboarding assertion
fails; (d) the final key → all pass. (b) and (c) were observed on scratch trees, never
by reverting the working file:

```
scratch <scratchpad>/ver4/red_memo/: claude_pet.py = ver4/round5_recon.py (c148fd7f…),
tests/test_companion_motion.py = the edited working copy; cwd red_memo/, 14:36:31Z
$ python3 -m unittest discover -s tests -p test_companion_motion.py -k test_actual_summary_formatter_distinguishes_estimate_from_exact -v
AssertionError: unexpectedly identical: ([('세션', 'value'), (' ≈42%', 'estimate'), (' · ', 'status'), ('주간', 'value'), (' ≈17%', 'estimate'), (' ⚠', 'status')], [], 19, 30) : a language change inside the window returned the memoised text
Ran 1 test in 0.049s / FAILED (failures=1) / rc=1

scratch <scratchpad>/ver4/red_memo_onboard/: claude_pet.py = current source with
`state.get("onboard"), ` removed from the key (one match asserted); same test; 14:37:10Z
AssertionError: 'onb_install' not found in '세션 ≈42% · 주간 ≈17% ⚠' : the onboarding state must reach the status line
Ran 1 test in 0.071s / FAILED (failures=1) / rc=1

working tree, cwd repo root, 14:35:10Z
$ python3 -m unittest discover -s tests -p test_companion_motion.py -v
Ran 51 tests in 2.872s / OK / rc=0
```

### F5. `tests/test_v023_release_contract.py` → `tests/test_v024_release_contract.py`

`git mv` at 14:29:50Z (`git status --porcelain`: `RM tests/test_v023_release_contract.py -> tests/test_v024_release_contract.py`);
the file was then rewritten (14:33:50Z, 656 lines, 20 tests in 7 classes). What it holds,
following the module's own v0.22→v0.23→v0.24 lineage:

- `VersionAndPinContractTests` (1): `APP_VERSION == ["0.24"]`; `verify_release_artifact.py`
  usage shows `--expect-version 0.24` and none of 0.23/0.22/0.25; five pins equal the
  current bytes — `REVIEWED_APP_SOURCE_SHA256` (both harnesses), `REVIEWED_BUILD_APP_SHA256`,
  `REVIEWED_VERIFIER_SHA256`, `REVIEWED_RELEASE_SHA256` (the last three are new to the gate).
- `PublishedNotesImmutabilityTests` (3): v0.22 pin (unchanged), v0.23 pin `c7ddc40a…`
  (now described as published), headings `["0.24", "0.23"]` with `0.24` once.
- `PublishedV023NotesContractTests` (5, was `ReleaseNotesContractTests`): the frozen v0.23
  prose still held to `UPDATE_CHECK_SEC`, `TR["ko"]["menu_check_update"]`, `run_gui`'s
  top level and the single `/releases/latest` endpoint — a published promise outlives its
  release.
- `ReleaseNotesPolicyTests` (2): unchanged.
- `StagedV024NotesFormatTests` (8): the format gate and the 50/85 · ▲ · ≈ · ⚠ cross-checks
  as in round 5, plus new: `Pretendard`/`OFL` in the note ↔ `SUMMARY_FONT_FILE` starts
  with `Pretendard`, `fonts/<file>` a regular non-symlink file, `fonts/LICENSE-Pretendard.txt`
  contains "SIL Open Font License", `setup.py` `"resources"` lists `"fonts"`, `build_app.sh`
  names the same file; `pets/이름/이름/` in the note ↔ `discover_pets` calls the module-level
  `_nested_pet_dir` exactly once; `claude-pet-win.zip … 서명 없음` present ↔ the mac
  `UPDATE_ASSET_NAMES` table does **not** contain it (the Windows asset is not gated by
  this tree; only wording is pinned, as assigned); every locale's `menu_toggle` contains
  its pill word (`pill`/`필`/`ピル`/`píldora`), the four TR key sets are identical and
  exactly en/es/ja/ko, and the note's `접기/펴기` is in `TR["ko"]["menu_toggle"]`;
  `수치는 출처`/`라벨은 흰색` in the note ↔ `draw_summary_pill`'s docstring says
  `라벨(잔여량 색)` and `수치(출처 색)` and not the swapped pair.
- `SummaryMemoContractTests` (1): `roam_summary_text` builds one tuple `key` containing
  `RUNTIME['mode']`, `L['lang']`, `state.get('onboard')`, `id(stats)`, `id(oauth)`,
  `bool(OAUTH_STATUS.get('auth_error'))`, and compares `_summary_memo['key'] == key`.

On the working tree (cwd repo root, 14:35:09Z): `Ran 20 tests in 0.392s / FAILED (failures=1)`,
the one failure verbatim:

```
FAIL: test_v024_version_and_final_source_pins_propagate (test_v024_release_contract.VersionAndPinContractTests.test_v024_version_and_final_source_pins_propagate)
AssertionError: ['verify_release_artifact.py usage must show --expect-version 0.24', 'verify_release_artifact.py still advertises --expect-version 0.23'] is not false :
- verify_release_artifact.py usage must show --expect-version 0.24
- verify_release_artifact.py still advertises --expect-version 0.23
```

**Red by revert-and-observe and forward mutants, on scratch trees only**
(`<scratchpad>/ver4/mutants.py`, 14:36:14Z–14:36:30Z, logs `ver4/mut/<tree>/run.log`; the
working tree was never reverted — production hashes re-checked after every run, F7).
Each tree copies the seven text files, the three test modules and hard-links the two
`fonts/` files; every mutation asserts exactly one match, so none can be a no-op. Tree
`W` is the working tree as-is; tree `B` is `W` + the one Developer fix the gate waits on
(usage `0.23`→`0.24`, and the copied upload harness re-pinned to those bytes); each mutant
is `B` + one substitution. Grouping key: one unittest result header per tree, 20 tests
each.

```
W  working tree as-is                              FAILED (failures=1)  [propagation: the usage example]  (as expected)
B  W + usage 0.24 + verifier re-pin                OK
m01 APP_VERSION "0.23"                             FAILED  propagation
m02/m03 REVIEWED_APP_SOURCE_SHA256 → round-5 value  FAILED  propagation (manual / upload)
m04 REVIEWED_VERIFIER_SHA256 → stale               FAILED  propagation
m05 REVIEWED_BUILD_APP_SHA256 one digit            FAILED  propagation
m06 REVIEWED_RELEASE_SHA256 one digit              FAILED  propagation
m07 usage 0.23 with a matching verifier pin        FAILED  propagation (only the usage clauses)
m08 published v0.23 bullet, one space              FAILED  test_published_v023_and_older_bytes_are_untouched
m09 published v0.22 bullet "10~20초"→"10~30초"      FAILED  v0.22 and v0.23 pins
m10 **v0.24** → **v0.25**                          FAILED  heading test (+ the 7 v0.24 setUps, which cannot find the section)
m11 fourth bullet / m12 nested bullet / m13 "훨씬" / m14 "tests/test_win.py" / m15 third sentence / m16 body > 450
                                                   FAILED  test_v024_notes_follow_the_three_bullet_450_character_format (each)
m17 "50%"→"60%" in the note / m18 `pct >= 85`→`80` in the source / m19 ▲ / m20 ≈ / m21 ⚠ dropped from the note / m22 SUMMARY_SPIKE "△"
                                                   FAILED  test_v024_thresholds_and_markers_match_the_source (each)
m23 "프리텐다드" / m24 fonts/Pretendard-SemiBold.ttf removed / m25 SUMMARY_FONT_FILE "Pretendard-Medium.ttf" / m26 setup.py resources without "fonts"
                                                   FAILED  test_v024_font_claim_is_backed_by_the_bundled_files_and_both_packagers (each)
m27 "(pets/이름/이름/)" dropped / m28 discover_pets no longer calls _nested_pet_dir
                                                   FAILED  test_v024_nested_layout_claim_is_backed_by_discover_pets (each)
m29 "claude-pet-windows.zip" / m30 Windows zip added to UPDATE_ASSET_NAMES["x86_64"]
                                                   FAILED  test_v024_windows_beta_wording_is_present_and_marked_unsigned (each)
m31 en toggle "Collapse/expand gauges" / m32 ko menu_toggle key removed / m33 ko "사용량 필 열기/닫기"
                                                   FAILED  test_v024_toggle_wording_matches_every_locale_and_locales_share_one_key_set (each)
m34 memo key without L["lang"], state.get("onboard")  FAILED  test_summary_memo_key_covers_mode_language_and_onboarding
m35 docstring roles swapped                        FAILED  test_v024_pill_docstring_and_notes_agree_on_label_and_value_colours
m36 UPDATE_CHECK_SEC 1800                          FAILED  test_v023_cadence_matches_update_check_sec
m37 CLAUDE.md "never at launch" → "never at start"  FAILED  test_claude_states_the_hourly_never_at_launch_cadence
```

37 of 37 mutants caught by the test named for them (source mutants m18/m22/m25/m28/m30–m36
also trip the propagation pin, as they must — the copied harness pins `B`'s source bytes).
The driver's own summary line reads `SOME MISS` only because it labelled `W` with the
prose "propagation only" instead of a test name; `W`'s failing list is exactly
`['test_v024_version_and_final_source_pins_propagate']` (`ver4/mutants.out`).

### F6. Findings for the Developer / Coordinator

1. **Blocking (suite RED): `verify_release_artifact.py:28` usage example still says
   `--expect-version 0.23`.** Every release commit since v0.21 moved it with `APP_VERSION`
   (F1), the v0.23 contract gated it, and `release.sh` passes `$(cur_version)` so the
   example is the only place a stale version literal survives a release. The v0.24 gate
   therefore requires `0.24` and is red on this tree — I did not relax it. Remedy, in the
   Developer's file: change that one token. If the change is exactly that substitution, the
   file hashes to `34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6`
   (measured on `ver4/mut/B/verify_release_artifact.py`, `diff` = line 28 only); the pin
   `REVIEWED_VERIFIER_SHA256` at `tests/test_upload_artifact_gate.py:61` (the only pin site
   in the repo, `grep -rn 5ba2cee2…`) then needs re-pinning **from the actual bytes**, which
   I will do and re-run — it must not be pre-pinned from this prediction.
2. **`fonts/` is still untracked** (`?? fonts/`). `setup.py` ships it as a resource,
   `build_app.sh` stages it, and the new font gate reads both files. The release commit
   must stage them by name (`git add fonts/Pretendard-SemiBold.ttf fonts/LICENSE-Pretendard.txt`),
   or a fresh checkout at the tag builds without the font the notes promise.
3. The harness gap (F2/F4) needed no production change; recorded so the `NameError` in the
   baseline log is not misread as an application bug.
4. Windows beta: not gated by this tree, as assigned; the mac `UPDATE_ASSET_NAMES` table
   excludes `claude-pet-win.zip` and the gate now pins that (`select_update_asset` skips
   names outside the table, so an extra release asset cannot reach a Mac).

### F7. Full suite after the test edits

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T14:37:05Z   end: 2026-09-12T14:42:25Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver4/suite1.log 2>&1 ; echo rc=$?
Ran 565 tests in 319.817s
FAILED (failures=1, skipped=7)
rc=1
```

Grouping key: one unittest result header; file set: the 21 modules under `tests/` (the
renamed contract module counted once, the old name gone). 557 of 565 results `ok`, 7
skipped (the same seven opt-in skips as F2, verbatim above), **1 failing — exactly**
`test_v024_release_contract.VersionAndPinContractTests.test_v024_version_and_final_source_pins_propagate`,
with the F5 message (`--expect-version 0.24` absent, `0.23` still advertised). No other
failure, no error. Compared with F2 (541 tests): +18 `test_manual_update_transaction`
methods the baseline never counted (their `setUpClass` errored on the stale pin), +6 in the
contract module (14 → 20). The suite therefore does **not** end OK: this run's status is
RED, on F6-1 alone, and it turns GREEN with the one-token Developer fix plus the verifier
re-pin I will make from the fixed bytes and a re-run. Nothing was relaxed to reach a
number. The opt-in native smoke in `test_companion_motion.py` was not run (it creates a
window); it stays *unverified red* as stated in round 1 §5.

Tree stability: `shasum -a 256` of `claude_pet.py`, `build_app.sh`, `verify_release_artifact.py`,
`release.sh`, `setup.py`, `RELEASE_NOTES.md`, `CLAUDE.md` immediately before and after the run
(`ver4/hashes_{before,after}_suite1.txt`) — identical to each other and to F1 (`diff` empty).

### F8. Untracked work, process, provenance (AGENTS.md §4, §5)

- Files this role edited: `tests/test_upload_artifact_gate.py` (one pin literal),
  `tests/test_manual_update_transaction.py` (one pin literal), `tests/test_companion_motion.py`
  (one test method: scope + four assertions + docstring), `tests/test_v024_release_contract.py`
  (git mv + rewrite), and this record. No production file, no documentation file, no README,
  no `fonts/` file, no Windows worktree, no other agent's record (`summary-unify-review-20260912.md`
  mtime 23:17:12 KST, `release-v023-operator-20260911.md`, `quiet-companion-release-operator.md`
  unchanged) and no user-owned file was opened for writing: `diag.py` 2026-07-22 12:07:01,
  `release/icon_1024.png` and `release/ClaudePet.iconset` 2026-07-13 23:46:36, checked at
  14:36Z. `APP_VERSION` was not touched.
- Git commands: `status`, `diff`, `log`, `show`, and the one permitted `git mv`. Nothing
  committed, tagged, pushed, signed, built, installed or released; no GUI launched (the dev
  instance PID 43658 untouched); `~/.claude` never read by a test or probe; `~/.claude_pet*`
  never written.
- Grouping key: one unittest result header (suite, module, scratch and mutant runs); one
  diff hunk (F1); one file (hashes).
- Window: 2026-09-12T14:21:22Z (first command) – 2026-09-12T14:42:25Z (post-suite hash check), UTC.
- File set read: the tracked diff at 14:21Z (21 paths), `ver3/claude_pet.diff`,
  `git show 81619b3:RELEASE_NOTES.md`, `git show HEAD:claude_pet.py`, all of `tests/`,
  `AGENTS.md`, `CLAUDE.md`, `fonts/`, the round-1–5 sections above.
- Numerators/denominators: baseline 58 failing results / 541 tests (F2); module greens
  18/18, 64/64, 51/51, 19/20 on the working tree (F3–F5); red on the round-5 source 1/1,
  red on the onboarding-only mutant 1/1 (F4); mutants 37 caught / 37 built, B 0 failing /
  20 (F5); final 1 failing / 565, 7 opt-in skips, 557 ok (F7).
- Measured at: the timestamps quoted beside each command.

## G. Final pin run — part 2 (2026-09-12, Verifier verifier-v024)

Continuation of §F. F7 ended RED on exactly one test
(`test_v024_release_contract.VersionAndPinContractTests.test_v024_version_and_final_source_pins_propagate`,
finding F6-1: `verify_release_artifact.py:28` still advertised `--expect-version 0.23`). The
Developer has since changed that token. This section re-measures the tree, re-pins the one
harness that hashes the file, and re-runs the suite. Same role, same rules: `tests/` and this
record only; no git write; no build, sign, install, GUI, `~/.claude` read or `~/.claude_pet*` write.

### G1. What changed since F (read 14:44Z)

```
$ shasum -a 256 claude_pet.py build_app.sh release.sh verify_release_artifact.py   (14:44Z)
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6  verify_release_artifact.py
```

`claude_pet.py`, `build_app.sh` and `release.sh` are byte-identical to F1 (and to
`ver4/hashes_after_suite1.txt`). **Only `verify_release_artifact.py` moved**, `5ba2cee2…` →
`34c4e57f…`. That the delta is exactly the one token was established three independent ways,
not taken from the assignment text:

1. **Reconstruction.** `sed 's/--expect-version 0.24 --arches/--expect-version 0.23 --arches/'`
   over today's bytes hashes to `5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324`
   — the F1 value and the pin the harness carried until now. So today's file differs from the
   pinned bytes in that token and nothing else.
2. **Identity with the F5 mutant.** `diff ver4/mut/B/verify_release_artifact.py verify_release_artifact.py`
   is empty. Mutant B was built in F5 as "W + usage 0.24 + verifier re-pin" and ran the contract
   module 20/20 OK; the working tree now *is* that file.
3. **Token census.** `grep -n '0\.23\|0\.24' verify_release_artifact.py` returns one line, 28,
   reading `--expect-version 0.24`. No `0.23` remains anywhere in the file.

**About `git diff verify_release_artifact.py`:** against HEAD (`45a03c4`, the v0.21 release
commit) it shows **two** hunks, `+18 −1` — the token on line 28 and the 17-line bundled-font
gate in `check_app` (`Contents/Resources/fonts/Pretendard-SemiBold.ttf` + `LICENSE-Pretendard.txt`,
TrueType magic `00 01 00 00`). The font block is **inside the `5ba2cee2…` bytes** — it was already
in the tree at F1 and was reviewed then — so "only the one-token hunk" holds against the
*pinned* bytes (check 1), which is the comparison that matters for the pin. Against HEAD the
statement would be false, and I record that rather than let the two baselines blur.

### G2. Re-pin (old → new), with the RED before it and beside it

- `tests/test_upload_artifact_gate.py:61` `REVIEWED_VERIFIER_SHA256`
  `5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324` →
  `34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6`, at 14:45:19Z, by `sed` on
  the exact 64-character literal. This is the **only holder**: `grep -rn REVIEWED_VERIFIER_SHA256 tests/`
  gives line 61 (the literal), lines 377 and 1576 (`assert_reviewed_file` reads it), and
  `tests/test_v024_release_contract.py:242` (reads it *by name* from the other module's source; holds
  no copy). No other file under the repo carries `5ba2cee2…` except the two records in
  `docs-design/`, which are history and stay as written. The other two pins in that file
  (`REVIEWED_RELEASE_SHA256` = `a5b25686…`, `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…`) already
  equal the bytes and were not touched. Post-edit hash of the test module:
  `93b91c6e59c3ddc5fb44bea5dc644921600fa5603a8e6344113378a638fa0453`.
- **RED before it:** F7 — 1 failing / 565 on the old bytes + old pin, the contract test, message
  "`--expect-version 0.24` absent, `0.23` still advertised".
- **RED beside it (revert-and-observe, AGENTS.md §3), on scratch, not on the working tree.**
  `ver4/mut/G` = `ver4/mut/B` + the working tree's `tests/test_upload_artifact_gate.py` and
  `tests/test_v024_release_contract.py` (both `diff -q` identical to the working tree) + the
  verifier reverted to `0.23` (hash re-measured: `5ba2cee2…`). So: **new pin, pre-fix bytes.**
  `cd ver4/mut/G`, 14:53:04–14:53:08Z:
  - `python3 -m unittest discover -s tests -p 'test_v024_release_contract.py' -v` →
    `Ran 20 tests in 0.394s` / `FAILED (failures=1)`, the one failure listing three problems
    verbatim: `verify_release_artifact.py usage must show --expect-version 0.24`;
    `verify_release_artifact.py still advertises --expect-version 0.23`;
    `test_upload_artifact_gate.py:REVIEWED_VERIFIER_SHA256 pins 34c4e57f…, final verify_release_artifact.py is 5ba2cee2…`.
  - `… -p 'test_upload_artifact_gate.py' -v` → `Ran 64 tests in 3.004s` / `FAILED (failures=48)`;
    all 48 `FAIL:` headers carry the same refusal, `verify_release_artifact.py changed after this
    executable harness was reviewed; refusing to run it until a verifier reviews and repins the new
    bytes` (48 occurrences, = the 48 failures). The 16 `ok` are the classes that hash nothing
    (`AssetNameCouplingTests` 1, `FragmentCompletenessTests` 2, `OneDmgPackagingTests` 6,
    `PublishWiringTests` 2, and 5 docstring-labelled methods of the same set). Logs:
    `ver4/red_G_contract.log`, `ver4/red_G_upload.log`.
  The working tree was re-hashed after the mutant run: `verify_release_artifact.py` `34c4e57f…`,
  the test module `93b91c6e…` — untouched.
- **GREEN on the working tree, 14:45Z**, cwd repo root:
  `test_v024_release_contract.py` → `Ran 20 tests in 0.413s` / `OK`;
  `test_upload_artifact_gate.py` → `Ran 64 tests in 50.050s` / `OK`
  (`ver4/green2_test_v024_release_contract.log`, `ver4/green2_test_upload_artifact_gate.log`).

### G3. Full suite

```
cwd: /Users/yeongyu/claude-pet
start: 2026-09-12T14:46:19Z   end: 2026-09-12T14:51:40Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/ver4/suite2.log 2>&1 ; echo rc=$?
Ran 565 tests in 320.230s
OK (skipped=7)
rc=0
```

Grouping key: one unittest result header; file set: the 21 modules under `tests/` (same set as
F7, listed by `ls tests/*.py`). **558 ok, 7 skipped, 0 `FAIL:`/`ERROR:` headers** — 558 = 557
lines ending `... ok` + 1 bare `ok` (log line 713, `test_v020_boundaries.B2Bundle.test_both_build_paths_declare_the_payload`,
whose own `[b2] …` stdout lines split its result line); the arithmetic 558 + 7 = 565 reconciles.
The F7 failure is now `... ok` at log line 754. The seven skips are the same seven opt-in live
checks as F2/F7, verbatim:

- `test_updater.RealBundleAcceptanceTests` ×2 —
  `skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
  (log lines 455, 458; the second is `test_the_real_installed_bundle_is_accepted_by_the_preflight`).
- `test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65` and
  `…test_stapler_reports_success_for_our_stapled_bundle` —
  `skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
  (log lines 536, 539).
- `test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network`,
  `…test_invalid_candidates_are_refused_before_handoff`, `…test_well_formed_v021_reaches_one_sandbox_handoff` —
  `skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'`
  (log lines 721–723).

Each is `stderr + skipTest`, loud, and none of the three environment variables was set. The
opt-in native smoke in `test_companion_motion.py` was again not run (it creates a window) and
stays *unverified red*, as stated in round 1 §5.

Tree stability: `shasum -a 256` of `claude_pet.py`, `build_app.sh`, `verify_release_artifact.py`,
`release.sh`, `setup.py`, `RELEASE_NOTES.md`, `CLAUDE.md`, `tests/test_upload_artifact_gate.py`
immediately before and after the run (`ver4/hashes_{before,after}_suite2.txt`) — `diff` empty, and
the four production values equal G1. `git status --porcelain` after the run is line-for-line the
pre-run listing (21 tracked entries, 25 untracked); the suite created nothing in the repo.

### G4. Findings for the Developer / Coordinator

1. **F6-1 is closed.** The one-token change is in the tree, the pin is re-taken from the bytes,
   and the pin discriminates (G2's mutant G). Nothing was relaxed to reach green.
2. **Status: GREEN.** 565 tests, 558 ok, 7 opt-in skips, 0 failures, rc=0, from the repo root.
   The tree is at the four hashes in G1 (`6f95bc8b…`, `db8e1ff9…`, `a5b25686…`, `34c4e57f…`) and
   the result is a statement about exactly those bytes.
3. **Staging list for the release commit** — for the Developer; I staged nothing. Derived from
   `git status --porcelain` at 14:51Z, not from the documents. `git check-ignore -v` over the four
   paths to add and the three user-owned paths names none and exits 1, so a sweep (`-A`, `.`)
   would take the user-owned three: name every path.

   Tracked, modified — 20:
   `CLAUDE.md` `README.md` `README.ko.md` `README.ja.md` `README.es.md` `RELEASE_NOTES.md`
   `build_app.sh` `claude_pet.py` `setup.py` `verify_release_artifact.py` `preview.png`
   `docs/index.html` `docs/llms.txt` `docs/llms-full.txt` `docs/assets/preview.png`
   `tests/test_companion_motion.py` `tests/test_manual_update_transaction.py`
   `tests/test_release_artifact_preflight.py` `tests/test_settings_and_install.py`
   `tests/test_upload_artifact_gate.py`

   Rename, already in the index as `R100 tests/test_v023_release_contract.py -> tests/test_v024_release_contract.py`
   (porcelain `RM`: the rename is staged, the worktree edits are not) — 1:
   `tests/test_v024_release_contract.py` (adding it stages the edits; the old name's deletion is
   already staged and needs no separate command).

   Untracked, to add by name — 4:
   `fonts/Pretendard-SemiBold.ttf` `fonts/LICENSE-Pretendard.txt`
   `tests/test_nested_pets.py` `tests/test_summary_pill.py`

   Stay untracked — not to be staged: `diag.py`, `release/ClaudePet.iconset/`,
   `release/icon_1024.png` (user-owned, [ASK] per CLAUDE.md), and the 20 `docs-design/` entries
   (this record, the review record, the two operator records, and the 16 smoke/trace
   `.json`/`.jsonl`/`.png` files).

   Expected read-back: `git diff --cached --name-status` = 25 lines — 20 `M`, 1 `R100`, 4 `A` —
   and nothing else. One `git add` naming those 25 paths reaches it.
4. Unchanged from F6: the harness gap in F4 needed no production change; Windows beta not gated
   by this tree.

### G5. Untracked work, process, provenance (AGENTS.md §4, §5)

- Files this role edited: `tests/test_upload_artifact_gate.py` (one 64-character literal, line 61)
  and this record. No production file, no documentation file, no README, no `fonts/` file
  (`Pretendard-SemiBold.ttf` 22:32:06, `LICENSE-Pretendard.txt` 20:54:31 KST — unchanged), no other
  agent's record (`summary-unify-review-20260912.md` 23:17:12, `release-v023-operator-20260911.md`
  Sep 11 11:31:02, `quiet-companion-release-operator.md` Sep 9 10:28:40 — unchanged), no user-owned
  file (`diag.py` 2026-07-22 12:07:01, `release/icon_1024.png` and `release/ClaudePet.iconset`
  2026-07-13 23:46:36 — unchanged, checked at 14:51Z). `APP_VERSION` not touched.
- Git commands: `status --porcelain`, `diff`, `diff --stat`, `diff --cached --name-status`,
  `check-ignore` — all read-only. Nothing added, committed, moved, tagged, pushed, signed, built,
  installed or released; no GUI launched (dev instance PID 43658 alive at 14:51Z, etime 01:19:10,
  untouched); `~/.claude` never read by a test or probe; `~/.claude_pet*` never written. Scratch
  work under `ver4/` only (`mut/G`, `green2_*.log`, `red_G_*.log`, `suite2*`, `hashes_*_suite2.txt`).
- Grouping key: one unittest result header (suite, module and mutant runs); one file (hashes).
- Window: ≈14:44Z (first `shasum`; not stamped) – 2026-09-12T14:53:08Z (mutant G end, stamped), UTC.
  The suite itself 14:46:19Z–14:51:40Z.
- File set read: the four production files, `tests/test_upload_artifact_gate.py`,
  `tests/test_v024_release_contract.py` (lines 225–275), `setup.py`/`build_app.sh` `fonts` references,
  `git diff verify_release_artifact.py`, `ver4/hashes_{before,after}_suite1.txt`, `ver4/mutants.out`,
  `ver4/suite1.log`, §F above.
- Numerators/denominators: production files changed 1 / 4 (G1); pin sites re-pinned 1 / 1 (G2);
  green modules 20/20 and 64/64 (G2); mutant G red 1 failing / 20 and 48 failing / 64, refusals
  48 / 48 failures (G2); final 0 failing / 565, 558 ok, 7 opt-in skips (G3); staging list
  25 to name / 46 porcelain entries (G4).
- Measured at: the timestamps quoted beside each command.
