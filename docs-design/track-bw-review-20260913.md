# Review record — Track B-W "Start at sign-in", Windows half (v0.25 follow-ups)

Reviewer: reviewer-bw (Claude), REVIEWER role only on this track; independent of the
Developer and of verifier-bw. Worktree `/Users/yeongyu/claude-pet-windows`, branch
`windows`, HEAD `e098516`. This file is untracked and was created by the Reviewer; the
Coordinator stages by named paths.

Inputs: AGENTS.md §2 / §3 / §5 / §7 / §8; CLAUDE.md § "Start at sign-in" (the UX the
Windows half mirrors), § Privacy, § "Repo layout"; `docs-design/followups-v025-plan-20260913.md`
§ "Track B"; the survey key `autostart` in the session scratchpad `followups-survey.json`
(findings 6, 9, 10, 11, 12); the Verifier's record
`docs-design/track-bw-verification-20260913.md` (§1–§8, read in full);
`git status --porcelain`; `git diff -- windows/`; `windows/win_autostart.py`,
`windows/tests/test_win_autostart.py`, `windows/claude_pet_win.py` (`_context_menu`,
`_autostart_args`, `_sync_autostart_item`, `_toggle_autostart`, `_uninstall`,
`delete_run_value_if_ours`, `is_frozen`, `app_exe_path`, `_msgbox`), `windows/win_update.py`
(`RUN_SUBKEY`, `RUN_VALUE_NAME`, `run_value_is_ours`, `_norm_win`, `uninstall_plan`,
`log_update`), `windows/installer.iss`, `windows/README.md`, `claude_pet.py` (the six
`autostart_*` TR keys, `rightMouseDown_`, `toggleAutostart_`, `autostart_*` helpers).

Not done, by instruction: no git write command; `windows/claude_pet_win.py`,
`windows/win_autostart.py` and `claude_pet.py` were never opened for writing; no untracked
file was touched other than this one, which the Reviewer created; the GUI was not run; no
Windows registry was reached (this host has no `winreg`); `~/.claude_pet.json` was neither
read nor written (checked afterwards: mtime still `Sep 13 11:28`, before this review began).
Every mutation probe ran on a **copy** under the session scratchpad
(`…/scratchpad/reviewbw/`), never in the worktree. All commands ran with cwd at the worktree
root. Times are UTC. Output blocks are verbatim except where a line is marked `…` (elided).

---

## Review round 1 (22:19–22:26Z, 2026-09-13)

### Verdict: PASS — no blocking items

Four non-blocking items and a 13-entry hardware list are in §7 and §8.

### 1. The tree reviewed

```
$ git status --porcelain
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
?? docs-design/track-bw-verification-20260913.md
?? windows/tests/test_win_autostart.py
?? windows/win_autostart.py

$ date -u +%Y-%m-%dT%H:%M:%SZ ; shasum -a 256 windows/win_autostart.py windows/claude_pet_win.py \
    windows/build_win.py windows/README.md windows/tests/test_win_autostart.py \
    claude_pet.py windows/win_update.py windows/installer.iss
2026-09-13T22:22:43Z
9f3f8fb9d369326c171f369dbfdb18e56224db2659410d91f337fc4e8a0c33cb  windows/win_autostart.py
18accd8109b89f1bc65598b1dd55b969fafa16ab361af363b6cc1a91beb73b34  windows/claude_pet_win.py
63b389ef630cdf782b0b13a61a4ececfa1dc75d0a1dc3685818edc58337c5cfa  windows/build_win.py
407fe13d6b55c28a262325d49ad78fce5e22f837547b4857e999c5b5c3a78374  windows/README.md
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss
```

Three consequences read straight off those digests:

- **`claude_pet.py` is untouched** — `9dd9fb12…` is byte-identical to `git show HEAD:claude_pet.py`,
  and `git diff --quiet HEAD -- claude_pet.py` exits 0. So are `windows/win_update.py`
  (`0fd40d9a…`) and `windows/installer.iss` (`07fcf4c4…`). The six TR keys the Windows half
  uses are the merged macOS ones, not new ones.
- **`tests/` is untouched** — `git diff --quiet HEAD -- tests/` exits 0.
- **The gating test file is byte-identical to the Verifier's handover hash.**
  `a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6` is the digest recorded
  in the Verifier's §3 (red run) and §7 (handoff). The Developer did not touch the gating
  assertions or fixtures after red — AGENTS.md §2 Condition A, checkable from the digest
  alone rather than from anyone's account of it.

### 2. §2 A/B against the RED record

**Condition A — the Developer did not touch the gating assertions.** Established by the
digest above: the file the Developer's tree gates on is bit-for-bit the file that was red
at `2026-09-13T15:00:04Z`, before `windows/win_autostart.py` existed (the Verifier's §3
records `ls windows/win_autostart.py` → `No such file or directory` in that same block).

**Condition B — the Verifier has clean hands on the production files.** The production
files of this change are `windows/win_autostart.py` (new), `windows/claude_pet_win.py` and
`windows/build_win.py`; `windows/README.md` is documentation. All three production files
hash at HEAD in the Verifier's §1 *and* §3 (`bb565b08…` for the port, `125d9105…` for the
builder as of HEAD), and the Verifier's record states plainly that no production file was
opened for writing and that the reference implementation used for the rival matrix lived
only under the session scratchpad, never in the worktree. The worktree's own history
corroborates it: the port and the builder still hashed at HEAD at the moment of the red run,
and changed only afterwards.

No §2 Condition C exception is declared, and none is needed.

**Roles.** Developer, Verifier and Reviewer are three different agents; no agent holds two
roles. There is no commit yet — the whole change sits in the working tree — so §7's trailers
are the Coordinator's step, not something this review can confirm from `git log`. §8 item 1
(both trailers present and different) is therefore **open by construction** and must be
satisfied when the commit is made; nothing in the change prevents it.

### 3. §3 red-before-green, and whether the fixtures discriminate

The Verifier's §3 carries a real red run, not a claim of one: 141 run, **8 FAIL + 32 ERROR**,
exit 1, with the 32 errors all `ModuleNotFoundError: No module named 'windows.win_autostart'`
and the 8 failures each on their own design assertion. Three tests were green at red and are
**declared** as such (`SharedKeysTests`, a precondition on the merged TR keys; the two
`UninstallPinTests` regression pins) — declaring them is the right handling, since a test
that was green before the change gates nothing and saying so is what stops it from reading
as evidence later.

Two authoring corrections are recorded *with their timestamps and their reason*, both before
any production file existed, and neither changed an expected value. That is the honest shape:
a red observed after the fixtures settled, not reconstructed.

**The Reviewer re-ran the discrimination independently**, on a scratch copy of the tree
(`…/scratchpad/reviewbw/`, never the worktree), rather than taking the Verifier's rival table
on trust. Seven mutations of `windows/win_autostart.py` and five variants of the port
(`CLAUDE_PET_WIN_PORT_SOURCE`):

| mutation (module) | Reviewer's result | caught by |
| --- | --- | --- |
| IGN-SA — `_state_of` returns `"on"` without consulting StartupApproved | FAILED (failures=3) | `ReadStateTests` ×2, `ToggleTests.test_disabled_in_task_manager…` |
| CASE — compare the unquoted path case-sensitively | FAILED (failures=1) | `ReadStateTests.test_state_table` (row 3) |
| BARE — `run_value_for` returns the path unquoted | FAILED (failures=9) | `RunValueTests` ×3, `ToggleTests` ×4, … |
| KEEP-SA — enabling leaves a disabled StartupApproved entry in place | FAILED (failures=3) | `ToggleTests` ×3 |
| SWALLOW — a writer failure reports the *flipped* state | FAILED (failures=2) | `ToggleTests.test_writer_failure_turning_on/off…` |
| NOFRZ — ignore `is_frozen` | FAILED (failures=4) | `ReadStateTests.test_source_run…`, `ToggleTests.test_source_run_touches_nothing` |
| NE3 — `startup_approved_enabled` as `blob[0] != 0x03` | FAILED (failures=1, errors=2) | `StartupApprovedTests.test_table` |

| port variant | Reviewer's result | caught by |
| --- | --- | --- |
| the item moved after "Reset size" | FAILED (failures=1) | `test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos` |
| the state read at construction, no `aboutToShow` | FAILED (failures=1) | `test_the_menu_rereads_the_state_when_it_opens` |
| the `autostart_fail` box removed | FAILED (failures=2) | `test_the_click_toggles…`, `test_no_config_key_and_no_local_override` |
| a plain (non-checkable) `QAction` | FAILED (failures=1) | `test_the_autostart_action_is_checkable` |
| roam-style `merge_config_updates({"autostart": …})` | FAILED (failures=1) | `test_no_config_key_and_no_local_override` |

Every result matches the Verifier's §4 table, including the failure *counts*. The module was
restored from a pristine copy after each probe and the suite re-run green, so nothing leaked
between probes.

One entry in the Verifier's table deserves the credit it takes: **ASSUME** ("report the
flipped state without re-reading") passes every row, and the Verifier says so in the record
and removed the claim from the `ToggleTests` docstring rather than leaving a rival listed
that nothing catches. Under this writer contract a write either lands or raises, so
re-reading and assuming are genuinely indistinguishable — the honest conclusion is that it is
not a rival, not that the fixture is weak. `test_the_returned_state_is_what_the_registry_now_reads`
still pins that the two functions agree on every transition, which is the property that
matters.

### 4. The design, point by point

| design point | verdict | where |
| --- | --- | --- |
| quoting identical to `installer.iss` | **ok** | `run_value_for(exe)` is `'"' + exe + '"'`; `RunValueTests.test_matches_the_installer_registry_line` expands the real `[Registry]` line (`ValueData: """{app}\{#MyAppExeName}"""`, Inno's `""` → a literal quote) and compares byte for byte. No normalisation on the way in — correct, because the installer writes the path as-is too. |
| path comparison normalisation | **ok** | one comparator for both halves: `wu.run_value_is_ours` strips one leading quote pair and compares through `wu._norm_win` = `ntpath.normcase` (+ one trailing separator). `ntpath`, not `os.path` — so the rule reads the same on this host as on the target, where `posixpath.normcase` would be the identity. Row 3 of the state table (upper-cased exe) is what makes that load-bearing. |
| StartupApproved isolated | **ok** | `startup_approved_enabled(blob)` is the only place `0x02` / `0x03` appear, as two module constants; both the module docstring and the README say the encoding is from memory and must be confirmed on hardware. The fail-safe direction is right: anything unreadable reads *not enabled*, so the item shows unchecked and the next click deletes the entry (absent = enabled) — self-healing. The opposite default would show a checkmark Windows does not honour, with no click that fixes it. |
| from-source disabled | **ok** | `autostart_read_state` / `autostart_toggle` return `"unavailable"` **before any registry call** when `is_frozen` is falsy (`ReadStateTests.test_source_run_is_unavailable_and_reads_nothing` asserts `reg.calls == []`). The port passes `is_frozen()`, which is `getattr(sys,"frozen",False) and _WIN32` — stricter than the brief's expression and correct on both counts. `pythonw.exe` is never registered. |
| no config key | **ok** | nothing in `win_autostart.py` mentions `RUNTIME`, `merge_config_updates`, `save_config`, `load_config`, `CONFIG_PATH`, `SETTINGS_OWNED_KEYS` or `apply_config` (text pin), the port carries no `"autostart"` string anywhere (AST pin over the whole module), and `_ConfigGuard` plants a rogue `"autostart": true` in both the config file and `RUNTIME` and fails if either is read or rewritten. This is CLAUDE.md § "Start at sign-in"'s central rule and it holds on both halves. |
| menu position and `aboutToShow` re-read | **ok** | `QAction(cp.t("menu_autostart"), m, checkable=True)` is added immediately after `m.addAction(roam)` and before `m.addAction(cp.t("menu_reset_size"), …)`. The order pin does not hard-code the quintet only on the Windows side: it extracts the macOS `rightMouseDown_` tuple list by AST and asserts the two five-item windows are **equal**, so the two halves cannot drift apart in either direction. `m.aboutToShow` is connected before `m.exec(gpos)`, and `exec` emits it — the state is re-read from HKCU on every open, which is what makes a Task Manager change show up. |
| failure box via the TR keys | **ok** | `_toggle_autostart` → `self._msgbox(QMessageBox.Critical, cp.t("autostart_title"), cp.t("autostart_fail"))` + `addButton(QMessageBox.Ok)` + `exec()` — the existing helper, the same shape as `settings_error`, and `QMessageBox.Critical` matches the macOS `NSAlertStyleCritical`. |
| `uninstall_plan` still deletes the value | **ok, and the brief was wrong** | `uninstall_plan` is a *file* plan (`delete` / `run` / `helper` over paths) and never carried a registry step. The registry step is the port's own `delete_run_value_if_ours(exe)` inside `_uninstall`'s irreversible section, guarded by `run_value_is_ours`. The Verifier did not quietly satisfy the brief's wording: it recorded the discrepancy (§1, §6) and pinned the **real** mechanism three ways — the plan contains no registry path, the delete sits after the launch and keeps its identity guard, and what the toggle writes is what the uninstaller recognises. That is the right call; see §7 N1. |

### 5. UX parity with the macOS half

Read against `claude_pet.py`'s `rightMouseDown_` / `toggleAutostart_` and CLAUDE.md
§ "Start at sign-in":

- **Same TR keys, no local override.** The port defines none of the six `autostart_*` keys in
  its own `TR_WIN` table (pinned), so the menu text comes from `claude_pet.py` in all four
  locales and the two halves are identical string-for-string by construction.
- **Same position.** `menu_roam` → `menu_autostart` → `menu_reset_size` on both, asserted
  against the macOS source itself rather than against a copy of the order.
- **Same disabled text.** `"unavailable"` → `setText(cp.t("autostart_unavailable"))` +
  `setEnabled(False)` + unchecked, which is what `rightMouseDown_` does with
  `mi.setTitle_(t("autostart_unavailable"))` / `mi.setEnabled_(False)`.
- **Same contract shape.** `(new_state, "autostart_fail" | None)`; the new state is **read
  back** after the write rather than assumed; a failure leaves the state as it was; not
  installed → `"unavailable"` without touching the OS at all.
- **No `"approval"` on Windows, correctly.** That state is an SMAppService concept with no
  registry analogue, so `autostart_approval` / `autostart_open_settings` go unused on this
  half. That is not a parity gap: the states a platform can be in are the platform's.
- **One deliberate structural divergence.** CLAUDE.md tells the macOS view method to reach
  its OS collaborator through a `state` hook (`state["autostart_read"]`) so window-less tests
  keep a stable scope. The port calls `wa.autostart_read_state` from `_sync_autostart_item`
  directly. That rule is about the macOS test pattern; the port cannot be imported on any
  machine this suite runs on and is pinned by AST instead, so a hook would buy nothing and
  add a layer. Consistent with how the port already handles `roam`. Recorded, not a finding.

### 6. Suites re-run by the Reviewer

**Windows suite — green.**

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; python3 -m unittest discover -s windows/tests -t . ; echo "exit=$?"
2026-09-13T22:21:59Z
Ran 141 tests in 0.293s
OK
exit=0
```

141 = 98 pre-existing `test_win_update` + 43 new. Same counts as the Verifier's §8. Run
separately, `windows.tests.test_win_autostart` is 43 tests, OK.

**macOS suite — the declared pin family only.**

```
$ date -u +%Y-%m-%dT%H:%M:%SZ                       # start
2026-09-13T22:19:23Z
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"
Ran 588 tests in 269.102s
FAILED (failures=49, errors=8, skipped=8)
exit=1
2026-09-13T22:23:52Z                                 # end
```

Identical counts to the Verifier's §5 baseline and §8 re-run. Classified by module, the
failing set is exactly three modules and nothing else:

```
$ grep -E "^(FAIL|ERROR): " … | sed -E 's/^(FAIL|ERROR): [^ ]+ \(([^.]+)\..*/\1 \2/' | sort | uniq -c
   8 ERROR test_manual_update_transaction      # setUpClass, every one
  48 FAIL  test_upload_artifact_gate
   1 FAIL  test_v024_release_contract
```

and the single `test_v024_release_contract` failure names the cause outright:

```
AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61', …]
```

`9dd9fb12…` is HEAD's `claude_pet.py`, untouched by this track (§1), so the family is the
pre-existing release-time re-pin and not a consequence of this change. 155 lines in the run
carry one of the three pin messages. The 8 skips are the loud opt-in live checks
(`CLAUDEPET_RUN_LIVE_UPDATER_TESTS`, `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, "no built
bundle"). **`tests/test_autostart.py` — the macOS half's own gates — reported zero FAIL and
zero ERROR** (`grep -cE "test_autostart\..*\.\.\. (FAIL|ERROR)"` → 0).

**Two extra checks the Reviewer ran.**

```
$ python3 -c "import sys; sys.path.insert(0,'windows'); import win_autostart as wa; print(wa.RUN_SUBKEY, wa.RUN_VALUE_NAME, wa.real_registry(), wa.run_value_for(r'C:\Program Files\Claude Pet\ClaudePet.exe'))"
Software\Microsoft\Windows\CurrentVersion\Run ClaudePet (None, None) "C:\Program Files\Claude Pet\ClaudePet.exe"
                                                        # 'winreg' in sys.modules → False
$ python3 -m py_compile windows/claude_pet_win.py windows/win_autostart.py windows/build_win.py
                                                        # clean
```

The bare import is the one the frozen bundle uses (`pythonw windows\claude_pet_win.py` puts
`windows/` first on `sys.path`), and it works with no `winreg` on the host — `winreg` is
imported inside the two adapter functions and `real_registry()` decides by platform at call
time, so importing the module can never be what fails.

**Privacy.** The one new log line is
`wu.log_update("startup", status=<on|off|unavailable>, error=<none|autostart_fail>)` — two
closed vocabularies, no path, no identifier. It is also replayed by the pre-existing
`LogUpdateCallShapeTests`, which executes every `wu.log_update(` call site in the port and
fails on a malformed line or a leaked path. CLAUDE.md § Privacy holds.

### 7. Non-blocking items (for the Coordinator, none of them gate the merge)

- **N1 — the brief's `uninstall_plan` premise is wrong, and the record says so.** No action
  needed on the code. If the Coordinator wants the Run-value delete moved *into*
  `uninstall_plan`, that is a design change that goes back through the Verifier; the current
  mechanism (`_uninstall` → `delete_run_value_if_ours`, identity-guarded, in the irreversible
  section) is what is gated today and it is the safer of the two, since the plan is
  deliberately path-only.
- **N2 — user-facing docs still describe Windows autostart as installer-only.**
  `README.md:21` ("Installer option “Start when I sign in”"), `README.ko.md:21`, and
  `docs/index.html` (the spec-table rows and their `en` / `ko` string tables) also still send
  macOS users to System Settings. The v0.25 plan already defers this to a docs follow-up
  "after both halves land", and the brief named only `windows/README.md`, so this is out of
  this track's scope — but it should not ship with the release. A documentation-only commit
  needs both trailers (AGENTS.md §7).
- **N3 — "Uninstall completely" leaves a StartupApproved crumb.** `delete_run_value_if_ours`
  removes the Run value; nothing removes
  `…\Explorer\StartupApproved\Run\ClaudePet`. A user who disabled the app in Task Manager and
  then uninstalled leaves a `0x03` entry behind, and a later *installer* enable would write
  the Run value that Windows then silently ignores. It is recoverable — one click on the menu
  item deletes the entry — and the Inno `uninsdeletevalue` has the same blind spot, so this
  is pre-existing rather than introduced here. Worth a decision after H4/H11 settle the
  encoding, not before.
- **N4 — the `build_win.py` hidden-import is ungated.** `--hidden-import win_autostart` is
  correct and matches the existing `win_update` line, but no test pins either of them, so a
  future drop would only surface on a Windows build. Informational; it is the same exposure
  the packaging step already has.

### 8. Hardware-only checks (the Windows pass)

Nothing below can be settled on macOS. H4 is the one that can change code.

- **H1.** Install with the installer's "Windows 로그인 시 자동 실행" task checked → right-click
  shows 로그인 시 자동 실행 **checked**, and `reg query "HKCU\…\Run" /v ClaudePet` returns
  `"<{app}\ClaudePet.exe>"` with exactly one pair of quotes.
- **H2.** Click the item off → Task Manager › 시작 앱 no longer lists ClaudePet, the Run value
  is gone, and `update.log` gains `startup status=off error=none`.
- **H3.** Click it on again → the entry returns; the Run value is byte-identical to
  `run_value_for(sys.executable)`; `startup status=on error=none`.
- **H4. The byte encoding — the only fact that can change the code.** Disable ClaudePet in
  Task Manager › 시작 앱 and dump
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run` → record the
  **whole blob**, not just the first byte, for: (a) never touched, (b) disabled, (c)
  re-enabled. Expected `0x03` disabled / `0x02` enabled. If a third first byte appears (some
  builds are reported to write `0x06`), `startup_approved_enabled` **and**
  `StartupApprovedTests.test_table` change together and nothing else does.
- **H5.** With Task Manager set to 사용 안 함, open the right-click menu → the item reads
  **off** (unchecked, enabled), not checked. This is the bug the whole StartupApproved branch
  exists to prevent.
- **H6.** From that state, click the item on → the StartupApproved entry is **deleted** (not
  rewritten as `0x02`), the Run value is present, and the pet actually launches at the next
  real sign-in. Sign out and back in — a registry read is not the property under test here.
- **H7.** Run from source (`pythonw windows\claude_pet_win.py`) → the item reads
  "로그인 시 자동 실행 (여기서는 사용 불가)" and is greyed. Export the Run key before and after
  opening the menu and clicking the disabled item: the two exports must be identical.
- **H8.** Portable zip build → the item is enabled (the exe is frozen) and the Run value points
  at the extracted folder. Move the folder, launch from the new path, click on → the **same**
  value is overwritten with the new path; no second value appears.
- **H9.** Failure path: deny the current user *Set Value* on `HKCU\…\Run`, then click the item
  → the critical box appears with 로그인 시 자동 실행 / "로그인 시 자동 실행 설정을 바꾸지
  못했습니다.", the state is unchanged, and `update.log` gains
  `startup status=<unchanged> error=autostart_fail`.
- **H10.** Screenshot the right-click menu beside the macOS one: the item sits directly under
  화면 돌아다니기 and above 크기 원래대로, with identical wording.
- **H11.** "완전 삭제…" → the Run value is gone. **Also record whether a StartupApproved entry
  survives** (today nothing deletes it) and report back — that is the evidence N3 needs.
- **H12.** In-app update of an Inno install that had autostart on (setup re-run `/SILENT`) →
  the Run value survives the upgrade and still names the same `{app}` path.
- **H13.** Switch the app language to en / ja / es and confirm the item and the failure box
  render without truncation in the Windows menu (the strings come from `claude_pet.py`, but
  only a real menu shows the width).
