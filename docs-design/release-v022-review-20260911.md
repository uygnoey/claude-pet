# ClaudePet v0.22 — independent review record (2026-09-11)

Reviewer: **reviewer-v022**, an independent agent (subagent of Claude Code session
`55c3dee4-727f-4a94-b960-66540b129014`) that held no other role on this release: not
Developer, not Verifier, not Coordinator, not release operator. This file is the only
path I created or modified. All timestamps are UTC (`date -u`); 2026-09-10T23:57Z–
2026-09-11T00:10Z is the morning of 2026-09-11 in the maintainer's local time zone.

## Verdict

**PASS** — the v0.22 preparation (version bump, verifier usage line, new release-notes
section, repinned harnesses, renamed contract test, verification record) is correct,
in scope, and gated by discriminating tests. Findings for the Coordinator are in §12;
none of them blocks the release commit. This is a Reviewer sign-off on the
*preparation phase* only; the AGENTS.md §6 execution gate is evaluated after the
release commit and is not certified here.

## 1. What I did and did not do

Read first: `AGENTS.md` §0–§8 and `CLAUDE.md` (Release procedure, User-owned files,
`release/` is mixed). Then reviewed the uncommitted tree first-hand — every diff, hash
and count below was produced by my own commands, not copied from the Developer's or
Verifier's reports.

Not done: no `git add`, no commit, no tag, no push; no `./release.sh` or
`./build_app.sh` invocation; no `git clean`/`stash`/`reset`/`checkout .`/`rm -rf`; no
read of `~/.claude`; no write to `~/.claude_pet`; the installed app untouched; no
untracked file touched other than this record (§11).

## 2. Working tree, first-hand (HEAD `0cc8a2b`, 2026-09-10T23:57:55Z)

`git status --porcelain`, tracked entries only:

```
 M RELEASE_NOTES.md
 M claude_pet.py
 M tests/test_manual_update_transaction.py
 M tests/test_upload_artifact_gate.py
RM tests/test_v021_release_contract.py -> tests/test_v022_release_contract.py
 M verify_release_artifact.py
```

`git diff --cached --name-status -M` → `R100 tests/test_v021_release_contract.py
tests/test_v022_release_contract.py` (the `git mv` is the only staged entry; the
rewritten content is unstaged, as the `M` column says).

- `git diff -- claude_pet.py`: one hunk, one line —
  `-APP_VERSION = "0.21"` / `+APP_VERSION = "0.22"` (trailing comment unchanged).
  Nothing else in the file changed.
- `git diff -- verify_release_artifact.py`: one hunk, one line — the usage example
  `--expect-version 0.21` → `0.22`. Nothing else changed.
- `git diff -- RELEASE_NOTES.md`: `+5` lines, one hunk, inserted directly above
  `**v0.21**`: the `**v0.22**` heading, three `- ` bullets, one blank line. No
  deletions.
- `git diff -- tests/test_upload_artifact_gate.py`: exactly two literals changed
  (`REVIEWED_VERIFIER_SHA256`, `REVIEWED_APP_SOURCE_SHA256`).
- `git diff -- tests/test_manual_update_transaction.py`: exactly one literal changed
  (`REVIEWED_APP_SOURCE_SHA256`).
- `git diff HEAD -M --stat`: 6 files, `199 insertions(+), 111 deletions(-)`; the
  contract test rename accounts for `295` of the changed lines.
- `git diff --check` on all changed files: no whitespace errors; `RELEASE_NOTES.md`
  ends in `\n`.

Setting the version in one place is sufficient: `setup.py` extracts `APP_VERSION` from
`claude_pet.py` by regex for both `CFBundleVersion` and `CFBundleShortVersionString`,
and `build_app.sh` line 27 does the same with `sed`. No other file carries `0.21` as a
version (the only other `0.22` in `claude_pet.py` is an unrelated float in a pulse
expression).

## 3. Hashes, computed by me (2026-09-10T23:58:33Z)

| File | Working tree SHA-256 | HEAD blob SHA-256 |
| --- | --- | --- |
| `claude_pet.py` | `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266` | `150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351` |
| `verify_release_artifact.py` | `8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d` | `7f4e4887e532be3d576dbb478d08668a562a136de75d35ff6851d7731d1256fa` |
| `release.sh` | `a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23` | same (unchanged) |
| `build_app.sh` | `83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6` | same (unchanged) |

Pins in the tree, read with `grep -n -A1 'REVIEWED_[A-Z_]*SHA256 = ('`:

- `tests/test_upload_artifact_gate.py`: `REVIEWED_RELEASE_SHA256` = `a5b25686…6e23` ✓,
  `REVIEWED_VERIFIER_SHA256` = `8de85e87…b82d` ✓, `REVIEWED_APP_SOURCE_SHA256` =
  `04d016e8…6266` ✓.
- `tests/test_manual_update_transaction.py`: `REVIEWED_BUILD_APP_SHA256` =
  `83eca429…00d6` ✓, `REVIEWED_APP_SOURCE_SHA256` = `04d016e8…6266` ✓.

Every pin equals the current bytes of the file it guards; the old pins equalled HEAD's
blobs exactly, so the RED the Verifier recorded is attributable to the bump alone.

## 4. Published text is byte-identical

v0.21 is published: `git tag --sort=-v:refname | head -1` → `v0.21`;
`git ls-remote --tags origin` has `refs/tags/v0.21` (→ `24731b0`, an ancestor of HEAD);
`gh release list --limit 5` → `ClaudePet v0.21  Latest  v0.21  2026-09-09T01:27:59Z`.

SHA-256 of `RELEASE_NOTES.md` from the single `**v0.21**` heading to EOF:

```
working tree  323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75  (17273 bytes)
HEAD          323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75  (17273 bytes)
```

Identical. `**v0.21**` occurs exactly once in both. The bytes *before* the new
`**v0.22**` heading in the working tree equal the bytes before `**v0.21**` in HEAD, so
the whole change to this file is the inserted section and nothing else.

## 5. The v0.22 section against CLAUDE.md step 2

Section as it stands (from the working tree):

```
**v0.22**
- 펫이 산책할 때 화면 아무 데나 골라 걸어가고, 도착한 자리에서 그대로 쉽니다. 원래 자리로 돌아오지 않으며, 옮겨 둔 자리는 직접 드래그했을 때만 기억합니다.
- 쉬다가 마우스가 움직이면 무작위로 10~20초 동안 거리를 두고 천천히 따라다닌 뒤 바라보고, 멈춘 자리에서 쉽니다. 잡거나 메뉴를 열면 그 자리에 멈춥니다.
- 모니터가 두 대 이상이면 산책 중 다른 화면의 안전한 자리로 점프해 건너갑니다. 우클릭 메뉴 "화면 돌아다니기"를 끄면 따라다니기와 점프도 함께 멈추고, 한도 계산은 그대로라 다시 보정할 필요가 없습니다.
```

| Rule | Measured | Result |
| --- | --- | --- |
| exactly 3 top-level bullets, no nesting | 3 lines matching `^- `; 0 indented lines | ✓ |
| ≤ 450 chars, whitespace normalised | 299 (bullet lines, as the test measures); 293 bullet text only; 309 with the heading | ✓ |
| 1–2 sentences per bullet | 2 / 2 / 2 | ✓ |
| user perspective, action + result | each bullet describes what the pet does and what the user does (drag, grab, open the menu, switch the item off); the user action needed is stated as none ("다시 보정할 필요가 없습니다") | ✓ |
| no hashes / identifiers / paths / line numbers / test prose | regex scans for 7+ hex, `.py`/`.sh`/`tests/`, UUIDs, `line N`, `테스트`: none | ✓ |
| no unquantified magnitude/frequency words | none of 대폭·훨씬·엄청·매우·대부분·대다수·많이·자주·종종·드물게·가끔·항상·완전히·상당히 | ✓ |
| figures auditable in the tree | the only digits are `10~20초`; see below | ✓ |

**Cross-checks against the source** (AST/grep on the working-tree `claude_pet.py`):

- `10~20초` ↔ `ROAM_DEFAULTS["follow_min_s"] == 10.0`, `["follow_max_s"] == 20.0`
  (`ast.literal_eval` of the single `ROAM_DEFAULTS` assignment), and the `follow_p`
  branch of `Roamer._plan` sets `self._follow_until = now + self.rng.uniform(
  self.cfg["follow_min_s"], self.cfg["follow_max_s"])` — the sentence's "무작위로" is
  literally that `uniform`.
- `"화면 돌아다니기"` ↔ `TR["ko"]["menu_roam"] == "화면 돌아다니기"` (literal_eval of
  `TR`; all four locales carry `menu_roam`), wired to `toggleRoam:` in the context menu.
- "끄면 따라다니기와 점프도 함께 멈추고" ↔ one switch gates the whole roamer:
  `enabled = bool(RUNTIME.get("roam")) and not state["reduce_motion"]`;
  `toggleRoam_` flips `RUNTIME["roam"]` and persists only `{"roam": value}`.
- "원래 자리로 돌아오지 않으며" ↔ `Roamer._plan` ends `self.kind = None … (귀가 없음)`
  and `toggleRoam_`'s comment `집으로 되돌리지 않는다`. (Wording-level check; the
  Verifier notes in their §9.5 that this negative is not pinned by an assertion, which
  I confirm and accept — the contract test does pin that nothing in `Roamer` persists
  a position, which is the user-visible half.)
- "옮겨 둔 자리는 직접 드래그했을 때만 기억합니다" ↔ the module's only
  `merge_config_updates({"x": …, "y": …})` is inside `mouseUp_` under `if moved:`.
- "모니터가 두 대 이상이면 … 점프" ↔ the jump branch of `_plan` runs only when
  `others = [s for s in screens if s.id != self.screen]` is non-empty and
  `jump_enabled` (default `True`).
- "한도 계산은 그대로라" ↔ `git diff v0.21..HEAD -- claude_pet.py` touches only the
  module docstring, `ROAM_DEFAULTS`, `class RoamDisplay`, `class Roamer`,
  `_roam_seg_dist`, `DISPLAY_SUMMARY`, a comment block after `gauge_rows`, and
  `run_gui()`; no hunk adds or removes a line mentioning `parse_usage_entries`,
  `_weigh_usage`, `compute_usage`, `_weekly_window_start`, `spike_info`, `is_spike`,
  the three `*_limit` keys, `prepare_settings_config` or `plan_settings_save`. The
  release commit's own hunk is the version literal. So the calibrated limits stay
  meaningful and the sentence is true.

The same label `"화면 돌아다니기"` also appears in the published v0.21 bullet; that is
consistent, not a defect.

## 6. Contract test `tests/test_v022_release_contract.py` — read in full, then mutated

Read all 512 lines. It imports nothing from the app, sources no shell, touches no
network or home directory; it parses tracked text/bytes with `ast`/`re`/`hashlib`.
`FORBIDDEN_NOTE_PATTERNS` is byte-identical to the v0.21 version (`diff` of the two
blocks: empty). The 11 cases and what each discriminates were checked against the
source (§5); the assertions are specific (exact list/float/string equality, exact
counts), not existence checks.

**My own mutation run**, independent of the Verifier's driver: scratch tree
`/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/review/mut/<mutant>/`,
each holding a copy of `claude_pet.py`, `verify_release_artifact.py`,
`RELEASE_NOTES.md`, `CLAUDE.md` and the three test files with exactly one edit, run
with `python3 -m unittest discover -s tests -p test_v022_release_contract.py` from that
root. Grouping key: one mutant = one scratch tree. Measured 2026-09-11T00:01:47Z →
00:01:52Z (m00–m14) and 00:02:48Z (m15). Control green; **15 / 15 mutants RED**:

```
m00_control                   exit=0 | Ran 11 tests | OK
m01_fourth_bullet             exit=1 | 4 != 3 : v0.22 must have exactly 3 top-level bullets, got 4
m02_nested_bullet             exit=1 | Lists differ: ['  - 하위 불릿입니다.'] != []
m03_frequency_word (자주)      exit=1 | ["remove unsupported magnitude/frequency: '자주'"] is not false
m04_app_version_0_21          exit=1 | ["APP_VERSION must be one literal '0.22', got ['0.21']", …pins…]
m05_published_v021_byte       exit=1 | 'fc54fce3…adc54' != '323664ae…0a75'  (published suffix)
m06_follow_max_25 (source)    exit=1 | Lists differ: [10.0, 25.0] != [10.0, 20.0]  (+ pin mismatch)
m07_notes_range_10_30 (notes) exit=1 | Lists differ: [10.0, 30.0] != [10.0, 20.0]
m08_menu_label_reworded       exit=1 | '"화면 돌아다니기"' not found in …
m09_pin_off_by_one            exit=1 | test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins …6267, final source is …6266
m10_roam_gate_removed         exit=1 | unexpectedly None : the roamer must be enabled only by RUNTIME["roam"] and not Reduce Motion
m11_roamer_persists_xy        exit=1 | 2 != 1 : expected exactly one x/y save, found 2
m12_over_450_chars (padding)  exit=1 | 3 not less than or equal to 2 : each bullet must have at most 2 sentences
m13_source_path_in_notes      exit=1 | ["remove source path: ' 계산(claude_pet.py)은'", "remove internal identifier: 'claude_pet'"]
m14_verifier_usage_0_21       exit=1 | ['verify_release_artifact.py usage must show --expect-version 0.22', …]
m15_over_450_single_sentence  exit=1 | 459 not less than or equal to 450 : v0.22 Korean body is 459 Unicode characters; max is 450
```

m12's padding was caught by the sentence rule before the length rule, so m15 was added
to show the 450 check fires on its own. Each mutant's full output is in
`<scratch>/review/mut/<mutant>/run.txt`; the summary in `<scratch>/review/mut/summary.txt`.

## 7. The three gates, re-run by me from the repository root

```
$ python3 -m unittest discover -s tests -p test_upload_artifact_gate.py      # 2026-09-10T23:59:56Z → 2026-09-11T00:00:45Z, exit 0
Ran 64 tests in 48.954s
OK
$ python3 -m unittest discover -s tests -p test_manual_update_transaction.py # 00:00:45Z → 00:00:59Z, exit 0
Ran 18 tests in 13.567s
OK
$ python3 -m unittest discover -s tests -p test_v022_release_contract.py     # 00:00:59Z → 00:00:59Z, exit 0
Ran 11 tests in 0.248s
OK
```

Outputs kept at `<scratch>/review/gate-<module>.txt`. Counts match the Verifier's
(64 / 18 / 11).

## 8. Full suite (AGENTS.md §5 form)

- Command: `python3 -m unittest discover -s tests -v` (cwd `/Users/yeongyu/claude-pet`), started by me
  in the background at 2026-09-11T00:01:11Z on the same dirty preparation tree as §2.
- Grouping key: one unittest case as reported by the runner. File set: the 18 `test*.py`
  modules under `tests/` listed in §9. Output: `<scratch>/review/full_suite.txt`.
- **Still running when this record was closed** at 2026-09-11T00:06:12Z (the Verifier's complete run took
  328 s; mine had not reached the summary line). Interim count at 2026-09-11T00:06:12Z, from the `-v` output:
  **427 cases `ok`, 4 skipped (opt-in live checks), 0 FAIL/ERROR lines** — no failure or error observed in the part
  that had run. Per the assignment the full suite was "if time allows"; the three gates in §7 were run to
  completion by me. The complete full-suite evidence for the preparation phase is the Verifier's run
  (`Ran 486 tests in 328.034s` / `OK (skipped=7)`, 2026-09-10T23:48:07Z → 23:53:35Z), whose §5 fields I checked
  in §9, and the execution gate requires the Verifier to re-run the suite from the clean tree after the
  release commit in any case (§12.1). The background process was left to finish; its complete output lands in
  the file named above and can be inspected by the Coordinator.

## 9. The verification record, checked against what I observe

`docs-design/release-v022-verification-20260911.md` (untracked, the Verifier's
deliverable; read, not modified):

- §5-form fields for the full suite are all present in its §7: command with cwd,
  grouping key (one unittest case), file set (the 18 `test*.py` modules — I count 18
  in `tests/`, same names), window start/end, measured-at, verbatim result lines,
  numerator/denominator (486 ran, 0 fail, 0 error, 7 skipped, 479 passed) and the
  seven skip lines with their reasons.
- Quoted lines I can reproduce all match: HEAD `0cc8a2b`; every SHA-256 in its §3/§4
  equals my §3; its `git status --porcelain` block equals my §2; the `gh release list`
  and `ls-remote` lines equal mine; `Ran 64` / `Ran 18` / `Ran 11` equal my §7; its
  published-suffix hash equals my §4; its "actual: 299" equals my count; the mutant
  assertion strings it quotes are the ones my mutants produced for the same edits.
- Its RED evidence (§3) is verbatim runner output, not a claim; the Stage A run shows
  the app-source pin is live independently of the verifier pin.
- One imprecision, not a defect: its §3a says "line 377 of the harness precedes the
  app-source pin on line 378" while the quoted traceback is from lines 1576/1577. Both
  pairs exist in `test_upload_artifact_gate.py` (two `setUp`s call
  `assert_reviewed_file` in the same verifier-then-app order), so the statement is
  true of the file; only the line cited differs from the traceback shown.
- Its stat values for the three user-owned files equal mine (§11).
- Roles: it states the Verifier edited no production file, and `git diff` confirms the
  Verifier's changes are confined to `tests/` and its own record. The Developer's diff
  touches no test. §2 Conditions A and B hold on the evidence in the tree.

## 10. Privacy scan

Scanned `RELEASE_NOTES.md` (whole file), `tests/test_v022_release_contract.py` and the
verification record for `/Users/`, `~/.claude`, `projects/-`, UUIDs, `.jsonl`, and
JSON message keys. Findings: no transcript content, no Claude Code project path, no
log file path. The only session id is the Developer's session
`55c3dee4-727f-4a94-b960-66540b129014`, used as an identity (allowed). The `~/.claude`
mentions in `RELEASE_NOTES.md` are pre-existing published text about permission
prompts. The verification record contains repository-relative tracebacks with the
absolute repo path `/Users/yeongyu/claude-pet/…` — the maintainer's checkout path,
not a transcript or project-log path; the same appears in five earlier tracked
`docs-design/*` records, so it is established practice here and not a leak under
CLAUDE.md's Privacy rule. The v0.22 notes contain no path of any kind.

## 11. Untracked files untouched

`stat -f '%m %N'` at 2026-09-10T23:58:33Z and again at the end of this review
(2026-09-11T00:06:12Z), identical, and equal to the Verifier's before/after values:

```
1784689621 diag.py
1783953996 release/icon_1024.png
1783953996 release/ClaudePet.iconset
```

Other untracked records under `docs-design/` (`*-live-*`, `*-smoke.*`, `*-native-*`,
`quiet-companion-release-operator.md`, and the Verifier's
`release-v022-verification-20260911.md`) were not modified; the verification record
was read only. `git status --porcelain` at the end shows the same six tracked entries
as §2 plus this file as the only new `??`.

## 12. Findings for the Coordinator (none blocking)

1. **This is a preparation-phase sign-off.** The AGENTS.md §6 execution gate — the
   Verifier's clean-tree full-suite re-run with command and output recorded, the notes
   check, the Coordinator's recorded sign-off, and a named eligible release operator —
   is evaluated **after** the release commit. Nothing from CLAUDE.md step 3 onward may
   start before it is GREEN and recorded.
2. **Release-commit paths**, derived from `git status --porcelain` (name each; never
   `git add -A` / `git add .`; read back `git diff --cached --name-only` before
   committing): `claude_pet.py`, `RELEASE_NOTES.md`, `verify_release_artifact.py`,
   `tests/test_upload_artifact_gate.py`, `tests/test_manual_update_transaction.py`,
   `tests/test_v022_release_contract.py` (the rename is already in the index; adding
   the path stages the rewritten content), `docs-design/release-v022-verification-20260911.md`,
   and this file `docs-design/release-v022-review-20260911.md`. The read-back must list
   exactly those eight and nothing else — in particular none of `diag.py`,
   `release/ClaudePet.iconset/`, `release/icon_1024.png`, or the other `docs-design/`
   untracked records.
3. **Authorization.** The user's words `22 버전으로 릴리즈해` reached me only via the
   assignment. I did not see them and this record does not certify them. Per AGENTS.md
   §6 they must be quoted verbatim in the release commit / change description by the
   party who saw them; an agent's relay (including this one) is not authorization for
   the push, publish, sign or notarize steps.
4. **Trailers** for the release commit, from the evidence in the tree: `Developer:`
   the Claude session `55c3dee4-727f-4a94-b960-66540b129014`; `Verifier:`
   verifier-v022. They differ, as §7 requires. Reviewer sign-off: reviewer-v022 (this
   record). None of these three parties, nor the Coordinator, is eligible to be the
   release operator for the `[ASK-OP]` steps.
5. `tests/test_v020_boundaries.py` hard-wires a `"0.21"` checkout and an installed
   v0.20 bundle; it is `skipUnless(CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1)` and
   skipped in every run here. It will refuse if someone opts in against a 0.22
   checkout. Historical; not part of this release's gate; left unchanged.
6. Earlier `docs-design/` records refer to `tests/test_v021_release_contract.py` by
   its old name. They are records of past runs; leave them.
7. After the release commit the execution-gate re-run should be recorded by the
   Verifier from the then-clean tracked tree; the `RM` entry in §2 will have become an
   `R` in history and the tree will show only `??` entries, which AGENTS.md §6 defines
   as clean.
