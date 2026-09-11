# ClaudePet v0.22 — independent verification record (2026-09-11)

Verifier: **verifier-v022**, an independent agent (subagent of Claude Code session
`55c3dee4-727f-4a94-b960-66540b129014`) that held no other role on this release.
All timestamps below are UTC (`date -u`); 2026-09-10T23:40Z–23:54Z is the morning of
2026-09-11 in the maintainer's local time zone, which is the date this record carries.

## 1. Roles and clean hands

| Role | Party | Basis |
| --- | --- | --- |
| Developer | Claude, in session `55c3dee4-727f-4a94-b960-66540b129014` (as stated by the assignment) | Prepared, uncommitted: `claude_pet.py` `APP_VERSION` `"0.21"` → `"0.22"`, `verify_release_artifact.py` usage line `0.21` → `0.22`, new `**v0.22**` section in `RELEASE_NOTES.md`. |
| Verifier | verifier-v022 (this record) | Edited **no** production file. Edited only the three test files and this record (§2). |
| Reviewer / Coordinator / Release operator | not this agent | — |

Authorization context, as relayed by the assignment (not verified by me — an agent's
report is not authorization, AGENTS.md §6): the user typed, in the Developer's session
on 2026-09-11, `22 버전으로 릴리즈해`. The Coordinator must quote it verbatim in the
release commit / change description; nothing in this record grants or withholds it.

Developer diff reviewed before repinning (`git diff --stat` at 2026-09-10T23:39Z):

```
 RELEASE_NOTES.md           | 5 +++++
 claude_pet.py              | 2 +-
 verify_release_artifact.py | 2 +-
 3 files changed, 7 insertions(+), 2 deletions(-)
```

The `claude_pet.py` hunk is the single line `APP_VERSION = "0.21"` → `"0.22"`; the
`verify_release_artifact.py` hunk is the single usage line `--expect-version 0.21` →
`0.22`; the `RELEASE_NOTES.md` hunk is the five added lines of the `**v0.22**` section
above `**v0.21**`. Nothing else in those three files changed. These are the bytes the
new pins in §3 certify.

HEAD at verification: `0cc8a2b docs: record independent companion play review`.
v0.21 is published: `gh release list` shows `ClaudePet v0.21  Latest  v0.21  2026-09-09T01:27:59Z`,
and `git ls-remote --tags origin` has `refs/tags/v0.21`. So the `**v0.21**` section and
everything below it is frozen published text.

## 2. Files I edited (my only deliverables)

- `tests/test_upload_artifact_gate.py` — two pin literals only (§3).
- `tests/test_manual_update_transaction.py` — one pin literal only (§3).
- `tests/test_v021_release_contract.py` → `tests/test_v022_release_contract.py` via
  `git mv`, then rewritten for v0.22 (§5).
- `docs-design/release-v022-verification-20260911.md` — this file (confirmed absent before
  creation).

Not touched: `claude_pet.py`, `RELEASE_NOTES.md`, `verify_release_artifact.py`, `README*`,
`AGENTS.md`, `CLAUDE.md`, `release.sh`, `build_app.sh`, every other tracked file, every
untracked file (§8). No commit, no tag, no `git add`. No `./release.sh` or `./build_app.sh`
invocation. The installed app was not touched. No test read `~/.claude`; nothing wrote to
`~/.claude_pet`.

## 3. RED first — the pinned harnesses and the v0.21 contract fail closed on the bump

Pre-change hash, measured 2026-09-10T23:40:31Z:

```
$ shasum -a 256 claude_pet.py
04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266  claude_pet.py
```

HEAD blobs, for attribution of the RED to the bump and nothing else:

```
$ git show HEAD:claude_pet.py | shasum -a 256               → 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351
$ git show HEAD:verify_release_artifact.py | shasum -a 256  → 7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa
$ git show HEAD:release.sh | shasum -a 256                  → a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23   (unchanged in tree)
$ git show HEAD:build_app.sh | shasum -a 256                → 83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6   (unchanged in tree)
$ shasum -a 256 verify_release_artifact.py                  → 8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d   (bumped usage line)
```

So the old pins (`150f5775…` for `claude_pet.py`, `7f4e4887…` for
`verify_release_artifact.py`) matched HEAD exactly; the mismatch is the Developer's bump.

### 3a. `python3 -m unittest discover -s tests -p test_upload_artifact_gate.py`
run from the repository root, 2026-09-10T23:41:01Z → 23:41:05Z, exit 1. First failure
block and summary, verbatim (all 48 failures are the same `setUp` refusal):

```
======================================================================
FAIL: test_a_clean_archive_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_clean_archive_is_accepted)
The control. Without it every rejection below could be a blanket no.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_upload_artifact_gate.py", line 1576, in setUp
    assert_reviewed_file(self, RELEASE_VERIFIER, REVIEWED_VERIFIER_SHA256)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_upload_artifact_gate.py", line 74, in assert_reviewed_file
    testcase.assertEqual(
    ~~~~~~~~~~~~~~~~~~~~^
        actual, expected,
        ^^^^^^^^^^^^^^^^^
        f"{path.name} changed after this executable harness was reviewed; "
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "refusing to run it until a verifier reviews and repins the new bytes")
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d' != '7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa'
- 8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d
+ 7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa
 : verify_release_artifact.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes
Ran 64 tests in 3.324s
FAILED (failures=48)
```

The verifier pin refuses first (line 377 of the harness precedes the app-source pin on
line 378), so the `claude_pet.py` pin is not exercised by this run. It was exercised
separately in §4 (stage A).

### 3b. `python3 -m unittest discover -s tests -p test_manual_update_transaction.py`
2026-09-10T23:41:05Z → 23:41:05Z, exit 5 (no test ran — every class refused in `setUpClass`).
First error block and summary, verbatim:

```
======================================================================
ERROR: setUpClass (test_manual_update_transaction.BackupPreservationTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_manual_update_transaction.py", line 742, in setUpClass
    raise AssertionError(
    ...<2 lines>...
    )
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, found 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266
Ran 0 tests in 0.003s
FAILED (errors=8)
```

### 3c. `python3 -m unittest discover -s tests -p test_v021_release_contract.py`
2026-09-10T23:41:05Z → 23:41:05Z, exit 1. Both failure blocks and summary, verbatim:

```
======================================================================
FAIL: test_v021_is_the_newest_heading_and_v022_is_gone (test_v021_release_contract.PublishedNotesImmutabilityTests.test_v021_is_the_newest_heading_and_v022_is_gone)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_v021_release_contract.py", line 235, in test_v021_is_the_newest_heading_and_v022_is_gone
    self.assertEqual(
    ~~~~~~~~~~~~~~~~^
        headings[:2],
        ^^^^^^^^^^^^^
    ...<2 lines>...
        f"published v0.20 heading; got {headings[:2]!r}",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: Lists differ: ['0.22', '0.21'] != ['0.21', '0.20']

First differing element 0:
'0.22'
'0.21'

- ['0.22', '0.21']
+ ['0.21', '0.20'] : the release was renumbered to v0.21, so v0.21 must sit directly above the published v0.20 heading; got ['0.22', '0.21']

======================================================================
FAIL: test_v021_version_and_final_source_pins_propagate (test_v021_release_contract.VersionAndPinContractTests.test_v021_version_and_final_source_pins_propagate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_v021_release_contract.py", line 213, in test_v021_version_and_final_source_pins_propagate
    self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ["APP_VERSION must be one literal '0.21', got ['0.22']", 'verify_release_artifact.py usage must show --expect-version 0.21', 'verify_release_artifact.py still advertises --expect-version 0.22', 'test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, final source is 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, final source is 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266', 'test_upload_artifact_gate.py:REVIEWED_VERIFIER_SHA256 pins 7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa, final source is 8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d'] is not false : 
- APP_VERSION must be one literal '0.21', got ['0.22']
- verify_release_artifact.py usage must show --expect-version 0.21
- verify_release_artifact.py still advertises --expect-version 0.22
- test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, final source is 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266
- test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351, final source is 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266
- test_upload_artifact_gate.py:REVIEWED_VERIFIER_SHA256 pins 7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa, final source is 8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d

----------------------------------------------------------------------
Ran 10 tests in 0.107s

FAILED (failures=2)
```

(First observation of the same three RED states: 23:40:33Z–23:40:37Z, identical assertion
text; the tee'd re-run above is the copy kept on disk.)

## 4. Repins — old → new, per file

| File | Constant | Old | New |
| --- | --- | --- | --- |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_VERIFIER_SHA256` | `7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa` | `8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d` |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_APP_SOURCE_SHA256` | `150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351` | `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266` |
| `tests/test_upload_artifact_gate.py` | `REVIEWED_RELEASE_SHA256` | `a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23` | unchanged (`release.sh` unchanged) |
| `tests/test_manual_update_transaction.py` | `REVIEWED_APP_SOURCE_SHA256` | `150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351` | `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266` |
| `tests/test_manual_update_transaction.py` | `REVIEWED_BUILD_APP_SHA256` | `83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6` | unchanged (`build_app.sh` unchanged) |

`git diff` of the two harness files after the repin — exactly three changed literals:

```
diff --git a/tests/test_manual_update_transaction.py b/tests/test_manual_update_transaction.py
index c9c188f..1d4616d 100644
--- a/tests/test_manual_update_transaction.py
+++ b/tests/test_manual_update_transaction.py
@@ -43,7 +43,7 @@ REVIEWED_BUILD_APP_SHA256 = (
     "83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6"
 )
 REVIEWED_APP_SOURCE_SHA256 = (
-    "150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351"
+    "04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266"
 )
 
 
diff --git a/tests/test_upload_artifact_gate.py b/tests/test_upload_artifact_gate.py
index 215203d..71b530d 100644
--- a/tests/test_upload_artifact_gate.py
+++ b/tests/test_upload_artifact_gate.py
@@ -58,10 +58,10 @@ REVIEWED_RELEASE_SHA256 = (
     "a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23"
 )
 REVIEWED_VERIFIER_SHA256 = (
-    "7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa"
+    "8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d"
 )
 REVIEWED_APP_SOURCE_SHA256 = (
-    "150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351"
+    "04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266"
 )
```

**Stage A (verifier pin only, 23:41:28Z → 23:41:31Z, exit 1)** — repinning only
`REVIEWED_VERIFIER_SHA256` moves the upload gate's refusal onto the `claude_pet.py` pin,
which shows that pin is live on its own:

```
======================================================================
FAIL: test_a_clean_archive_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_clean_archive_is_accepted)
The control. Without it every rejection below could be a blanket no.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_upload_artifact_gate.py", line 1577, in setUp
    assert_reviewed_file(self, APP_SOURCE, REVIEWED_APP_SOURCE_SHA256)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_upload_artifact_gate.py", line 74, in assert_reviewed_file
    testcase.assertEqual(
    ~~~~~~~~~~~~~~~~~~~~^
        actual, expected,
        ^^^^^^^^^^^^^^^^^
        f"{path.name} changed after this executable harness was reviewed; "
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "refusing to run it until a verifier reviews and repins the new bytes")
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266' != '150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351'
- 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266
+ 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351
 : claude_pet.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes
Ran 64 tests in 3.206s
FAILED (failures=48)
```

**Stage B (both app-source pins, exit 0):**

```
$ python3 -m unittest discover -s tests -p test_upload_artifact_gate.py        # 23:41:48Z → 23:42:38Z
Ran 64 tests in 49.406s
OK
$ python3 -m unittest discover -s tests -p test_manual_update_transaction.py   # 23:42:38Z → 23:42:51Z
Ran 18 tests in 13.291s
OK
```

## 5. Contract test: `tests/test_v022_release_contract.py`

`git mv tests/test_v021_release_contract.py tests/test_v022_release_contract.py`, then
rewritten. Style preserved: no `import claude_pet`, no shell sourcing, no network, no home
directory — only tracked text/bytes parsed by AST/regex. `FORBIDDEN_NOTE_PATTERNS` kept
verbatim. 11 cases:

| Case | Pins |
| --- | --- |
| `VersionAndPinContractTests.test_v022_version_and_final_source_pins_propagate` | `APP_VERSION` is exactly one literal `"0.22"`; `verify_release_artifact.py` usage shows `--expect-version 0.22` and not `0.21`/`0.20`/`0.23`; both harness `REVIEWED_APP_SOURCE_SHA256` literals equal the current SHA-256 of `claude_pet.py`; the upload gate's `REVIEWED_VERIFIER_SHA256` equals the current SHA-256 of `verify_release_artifact.py` (propagation). |
| `PublishedNotesImmutabilityTests.test_published_v021_and_older_bytes_are_untouched` | SHA-256 of `RELEASE_NOTES.md` bytes from the single `**v0.21**` heading to EOF == `323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75`. Computed from the working tree and confirmed byte-identical to the same suffix of `git show HEAD:RELEASE_NOTES.md` (equal → True, 2026-09-10T23:39Z). |
| `PublishedNotesImmutabilityTests.test_v022_is_the_only_unpublished_heading_and_sits_directly_above_v021` | Heading order `["0.22", "0.21", …]`, `0.22` exactly once. |
| `ReleaseNotesContractTests.test_v022_notes_follow_the_three_bullet_450_character_format` | Exactly 3 top-level bullets, zero nested, body ≤ 450 chars after whitespace normalisation (actual: 299), each bullet Korean and 1–2 sentences. |
| `ReleaseNotesContractTests.test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal` | Wander-anywhere / rest-on-arrival / no-return / drag-only-remembered; follow-at-a-distance for a `N~M초` range, look, rest where stopped, grab/menu stops; multi-display jump; the context-menu switch also stops following and jumping; limits unchanged so no recalibration; none of `FORBIDDEN_NOTE_PATTERNS`. |
| `ReleaseNotesContractTests.test_v022_follow_range_matches_the_source_defaults` | AST: `ROAM_DEFAULTS["follow_min_s"] == 10.0`, `["follow_max_s"] == 20.0`; the notes contain exactly one `N~M초` range and it equals those bounds; no other `N초` figure. |
| `ReleaseNotesContractTests.test_v022_follow_episode_is_drawn_from_those_defaults_and_ends_in_a_look` | AST: the `follow_p` branch of `Roamer._plan` reads `follow_min_s`/`follow_max_s`/`follow_cooldown_s` and enters phase `"follow"`; `Roamer._watch` gives follow and approach the same `look_s` review, and the wander pause does not use `look_s`. |
| `ReleaseNotesContractTests.test_v022_menu_label_is_quoted_exactly_as_the_korean_source_string` | AST: `TR["ko"]["menu_roam"] == "화면 돌아다니기"`, present in all four locales, and quoted verbatim (with quotes) in the notes. |
| `ReleaseNotesContractTests.test_the_roam_switch_gates_the_whole_roamer_and_reduce_motion_is_honoured` | `accessibilityDisplayShouldReduceMotion` present; `RUNTIME["roam"]` defaults on via `CLAUDE_PET_ROAM`; the roamer is enabled by `bool(RUNTIME.get("roam")) and not state["reduce_motion"]` (one switch gates wander, follow and jump); `jump_enabled` and `wander_enabled` default `True`. |
| `ReleaseNotesContractTests.test_only_a_real_drag_persists_the_position` | AST: exactly one `merge_config_updates({"x": …, "y": …})` in the module, it sits under `mouseUp_`'s `if moved:` branch, and class `Roamer` contains none. |
| `ReleaseNotesPolicyTests.test_claude_has_durable_user_facing_release_note_policy` | Unchanged from v0.21: CLAUDE.md step 2 still states the format rule. |

Run (repository root), 2026-09-10T23:46:36Z:

```
$ python3 -m unittest discover -s tests -p test_v022_release_contract.py -v
Ran 11 tests in 0.236s

OK
```

(A first run at 23:46:29Z errored on a typo of mine — an unbalanced `)` in one regex —
fixed before the run above; that error was in the test, not in the tree under test.)

## 6. Mutation check (scratch directory only, never inside `tests/`)

Driver: `/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/mut/drive.py`.
For each mutant it copies `claude_pet.py`, `verify_release_artifact.py`, `RELEASE_NOTES.md`,
`CLAUDE.md`, `tests/test_manual_update_transaction.py`, `tests/test_upload_artifact_gate.py`
and `tests/test_v022_release_contract.py` into `<scratch>/mut/<mutant>/` with the same
layout, so the test's own `REPO = Path(__file__).resolve().parents[1]` resolves to the
scratch copy — no edit to the test was needed. Each mutant then runs
`python3 -m unittest discover -s tests -p test_v022_release_contract.py` from its own root.
Grouping key: one mutant = one scratch tree with exactly one edit. Measured
2026-09-10T23:47:50Z → 23:47:54Z. Control (no edit) green; **14 / 14 mutants RED**:

```
measured-at 2026-09-10T23:47:50Z
00_control exit=0 | Ran 11 tests in 0.240s | OK
01_fourth_bullet exit=1 | Ran 11 tests in 0.243s | FAILED (failures=1)
    FAIL: test_v022_notes_follow_the_three_bullet_450_character_format
     AssertionError: 4 != 3 : v0.22 must have exactly 3 top-level bullets, got 4
02_nested_bullet exit=1 | Ran 11 tests in 0.239s | FAILED (failures=1)
    FAIL: test_v022_notes_follow_the_three_bullet_450_character_format
     AssertionError: Lists differ: ['  - 하위 불릿입니다.'] != []
03_over_450_chars exit=1 | Ran 11 tests in 0.237s | FAILED (failures=1)
    FAIL: test_v022_notes_follow_the_three_bullet_450_character_format
     AssertionError: 484 not less than or equal to 450 : v0.22 Korean body is 484 Unicode characters; max is 450
04_forbidden_word exit=1 | Ran 11 tests in 0.235s | FAILED (failures=1)
    FAIL: test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal
     AssertionError: ["remove unsupported magnitude/frequency: '가끔'"] is not false : 
05_hash_in_notes exit=1 | Ran 11 tests in 0.237s | FAILED (failures=1)
    FAIL: test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal
     AssertionError: ["remove hash: '0123456789abcdef0123456789abcdef01234567'"] is not false : 
06_app_version_0_21 exit=1 | Ran 11 tests in 0.243s | FAILED (failures=1)
    FAIL: test_v022_version_and_final_source_pins_propagate
     AssertionError: ["APP_VERSION must be one literal '0.22', got ['0.21']", 'test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266, final source is 150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2
07_wrong_harness_pin exit=1 | Ran 11 tests in 0.236s | FAILED (failures=1)
    FAIL: test_v022_version_and_final_source_pins_propagate
     AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66267, final source is 04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266'] is not false : 
08_published_v021_byte exit=1 | Ran 11 tests in 0.239s | FAILED (failures=1)
    FAIL: test_published_v021_and_older_bytes_are_untouched
     AssertionError: 'fc54fce3383db984b299deaaba7019fd4ca4f7f1daa5921033ab1dc072cadc54' != '323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75'
09_follow_max_25 exit=1 | Ran 11 tests in 0.243s | FAILED (failures=2)
    FAIL: test_v022_follow_range_matches_the_source_defaults
    FAIL: test_v022_version_and_final_source_pins_propagate
     AssertionError: Lists differ: [10.0, 25.0] != [10.0, 20.0]
10_menu_label_reworded exit=1 | Ran 11 tests in 0.241s | FAILED (failures=1)
    FAIL: test_v022_menu_label_is_quoted_exactly_as_the_korean_source_string
     AssertionError: '"화면 돌아다니기"' not found in '펫이 산책할 때 화면 아무 데나 골라 걸어가고, 도착한 자리에서 그대로 쉽니다. 원래 자리로 돌아오지 않으며, 옮겨 둔 자리는 직접 드래그했을 때만 기억합니다.\n쉬다가 마우스가 움직이면 무작위로 10~20초 동안 거리를 두고 천천히 따라다닌 뒤 바라보고, 멈춘 자리에서 쉽니다. 잡거나 메뉴를 열면 그 자리에 멈춥니다.\n모니터가 두 대 이상이면 산책 중 다른 화면의 안전한 자리로 점프해 건너갑니다. 우클릭 메뉴 "화면 돌아 다니기"를 끄면 따라다니기와 점프도 함께 멈추고, 한도 계산은 그대로라 다시 보정할 필요가 없습니다.' : the v0.22 notes must quote the Korean menu label '화면 돌아다니
11_verifier_usage_0_21 exit=1 | Ran 11 tests in 0.239s | FAILED (failures=1)
    FAIL: test_v022_version_and_final_source_pins_propagate
     AssertionError: ['verify_release_artifact.py usage must show --expect-version 0.22', 'verify_release_artifact.py still advertises --expect-version 0.21', 'test_upload_artifact_gate.py:REVIEWED_VERIFIER_SHA256 pins 8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d, final source is 7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa'] is not false : 
12_three_sentences exit=1 | Ran 11 tests in 0.238s | FAILED (failures=1)
    FAIL: test_v022_notes_follow_the_three_bullet_450_character_format
     AssertionError: 3 not less than or equal to 2 : each bullet must have at most 2 sentences
13_notes_range_drift exit=1 | Ran 11 tests in 0.244s | FAILED (failures=1)
    FAIL: test_v022_follow_range_matches_the_source_defaults
     AssertionError: Lists differ: [10.0, 30.0] != [10.0, 20.0]
14_top_heading_v023 exit=1 | Ran 11 tests in 0.037s | FAILED (failures=8)
    FAIL: test_v022_is_the_only_unpublished_heading_and_sits_directly_above_v021
    FAIL: test_only_a_real_drag_persists_the_position
    FAIL: test_the_roam_switch_gates_the_whole_roamer_and_reduce_motion_is_honoured
    FAIL: test_v022_follow_episode_is_drawn_from_those_defaults_and_ends_in_a_look
    FAIL: test_v022_follow_range_matches_the_source_defaults
    FAIL: test_v022_menu_label_is_quoted_exactly_as_the_korean_source_string
    FAIL: test_v022_notes_follow_the_three_bullet_450_character_format
    FAIL: test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal
     AssertionError: Lists differ: ['0.23', '0.21'] != ['0.22', '0.21']
RED 14 / 14 mutants
measured-at 2026-09-10T23:47:54Z
```

Mutants 01–08 are the eight the assignment required (4th bullet; nested bullet; > 450
chars; forbidden word 가끔; a 40-hex hash in the notes; `APP_VERSION` back to `0.21`;
wrong harness pin; altered published v0.21 byte). 09–14 are extras: source
`follow_max_s` → 25.0; menu label reworded in the notes; verifier usage back to 0.21;
three sentences in one bullet; notes range drifted to `10~30초` with the source untouched;
top heading renamed to `**v0.23**`. The full output of every mutant run is kept at
`<scratch>/mut/<mutant>/run.txt`.

## 7. Full suite from the repository root (AGENTS.md §5 form)

- Command: `python3 -m unittest discover -s tests -v` (cwd `/Users/yeongyu/claude-pet`)
- Grouping key: one unittest case as reported by the runner.
- File set: the 18 modules discovered under `tests/` by the default `test*.py` pattern —
  `test_companion_motion.py`, `test_companion_play.py`, `test_free_roaming.py`, `test_log_estimate.py`, `test_manual_update_transaction.py`, `test_mutation_instruments.py`, `test_partial_copy_seeding.py`, `test_release_artifact_preflight.py`, `test_release_gate.py`, `test_seeding_identity.py`, `test_settings_and_install.py`, `test_signing_contract.py`, `test_source_guard.py`, `test_updater.py`, `test_updater_adversarial.py`, `test_upload_artifact_gate.py`, `test_v020_boundaries.py`, `test_v022_release_contract.py`.
- Window: start 2026-09-10T23:48:07Z → exit=0 end 2026-09-10T23:53:35Z
- Measured-at: 2026-09-10T23:53:35Z (end of run).
- Result lines, verbatim:

```
Ran 486 tests in 328.034s

OK (skipped=7)
```

- Numerator/denominator: 486 cases ran; 0 failures, 0 errors, 7 skipped, 479 passed.
- The 7 skipped cases (all opt-in live checks that skip loudly with their reason):

```
test_the_real_bundle_contains_the_symlinks_this_guard_is_about (test_updater.RealBundleAcceptanceTests.test_the_real_bundle_contains_the_symlinks_this_guard_is_about)
test_the_real_installed_bundle_is_accepted_by_the_preflight (test_updater.RealBundleAcceptanceTests.test_the_real_installed_bundle_is_accepted_by_the_preflight) ...
test_stapler_rejects_an_unstapled_bundle_with_rc_65 (test_updater.StaplerLiveContractTests.test_stapler_rejects_an_unstapled_bundle_with_rc_65) ...
test_stapler_reports_success_for_our_stapled_bundle (test_updater.StaplerLiveContractTests.test_stapler_reports_success_for_our_stapled_bundle) ...
test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
```

  - `test_v020_boundaries.B3Updater` (3): require `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`.
  - `test_updater.RealBundleAcceptanceTests` (2) and `test_updater.StaplerLiveContractTests` (2):
    require `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`.

Full `-v` output kept at `/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/full_suite.txt`.

## 8. Untracked files: untouched

`stat -f '%m %N'` before (2026-09-10T23:39Z) and after (2026-09-10T23:53:51Z), identical:

```
before:
1784689621 diag.py
1783953996 release/icon_1024.png
1783953996 release/ClaudePet.iconset
after:
1784689621 diag.py
1783953996 release/icon_1024.png
1783953996 release/ClaudePet.iconset
```

Other people's untracked records under `docs-design/` (`*-live-*`, `*-smoke.*`, `*-native-*`,
`quiet-companion-release-operator.md`) were neither read for this work nor modified; their
mtimes at 23:53:51Z predate this session (e.g. `1788917320 docs-design/quiet-companion-release-operator.md`,
`1788944262 docs-design/companion-play-live-20260909.jsonl`). No `git add -A`, `git add .`,
`git clean`, `git stash`, `rm -rf`, or `git reset/checkout/restore` was run.

`git status --porcelain` at the end of this work (tracked entries only):

```
 M RELEASE_NOTES.md
 M claude_pet.py
 M tests/test_manual_update_transaction.py
 M tests/test_upload_artifact_gate.py
RM tests/test_v021_release_contract.py -> tests/test_v022_release_contract.py
 M verify_release_artifact.py
```

(the `R` is the `git mv` index entry; nothing else is staged.)

## 9. Findings and notes for the Coordinator

1. **The execution-gate re-run is not this run.** AGENTS.md §6: the Verifier's clean-tree
   re-run of the full suite happens **after** the release commit, from a tree with no
   uncommitted tracked modifications. The run in §7 was made on the dirty preparation tree
   and gates the preparation only. Re-run and record it again once the release commit exists.
2. **Paths for the release commit** (derived from `git status --porcelain`, not from any
   document): `claude_pet.py`, `RELEASE_NOTES.md`, `verify_release_artifact.py`,
   `tests/test_upload_artifact_gate.py`, `tests/test_manual_update_transaction.py`,
   `tests/test_v022_release_contract.py` (the rename is already in the index),
   `docs-design/release-v022-verification-20260911.md`. Name every path; read back
   `git diff --cached --name-only` before committing.
3. **`tests/test_v020_boundaries.py` is hard-wired to a `"0.21"` checkout** (its `B3Updater.setUpClass`
   raises unless `APP_VERSION == "0.21"`, and it also requires an installed v0.20 bundle).
   It is `skipUnless(CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1)`, so it skips in the
   ordinary suite and does not affect the gate; it is simply a historical v0.20→v0.21 gate
   that will refuse if someone opts in against a v0.22 checkout. Not my file; not changed.
4. **Historical records** under `docs-design/` refer to `tests/test_v021_release_contract.py`
   by its old name. They are records of past runs and were left as they are.
5. **What the contract test cross-checks against source is limited to what the source
   states literally**: the `10~20초` range, the menu label, the single switch, the
   drag-only persistence, and that follow ends in the same review look as approach. The
   sentence "원래 자리로 돌아오지 않으며" (no return home) is checked in the notes' wording
   only; `Roamer._plan` ends by resting in place (`self.kind = None … 귀가 없음`) but that
   negative is not pinned by an assertion.
6. Calibration: the v0.22 notes state that the limit computation is unchanged and no
   recalibration is needed. The Developer's `claude_pet.py` hunk is the version literal
   alone, so nothing in this release commit touches the estimator; the feature commits
   below HEAD are outside this verification's scope and were gated by their own records.
