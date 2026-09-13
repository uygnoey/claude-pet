# Track C/D — Windows in-app update / uninstall / signing scaffold: Reviewer record (2026-09-13)

Role: **Reviewer** (`reviewer-cd`, independent — held no Developer or Verifier role on this change).
Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD `d4050ee`, the Developer's work
uncommitted. Scope: the uncommitted change under `windows/` (`git status`: four tracked files modified,
`windows/win_update.py` and `windows/verify_win_artifact.py` new) against
`docs-design/followups-v025-plan-20260913.md` § "Track C/D", the survey record (key `windows`), the
Verifier's record `docs-design/track-cd-verification-20260913.md`, AGENTS.md §2/§3/§5 and CLAUDE.md's
updater contract and § Privacy. Nothing in this record was measured on a corpus; every number is a
test count or a probe result read from quoted output at the quoted UTC time.

## Review round 1

### Verdict: **FAIL** — three blocking items (B1–B3), all cheap; everything else holds

The pure surface is correct and well gated; the wiring is careful about ordering (every refusal
precedes every irreversible step on both kinds) and about privacy. What blocks the merge are three
behaviours the reviewed text itself promises and the code does not deliver: the ARM64 refusal
retries every 30 s instead of once an hour, the portable rollback can nest the old tree into the
install, and the lock does not cover the Inno installer's run. Each is a few lines and each is
gateable on macOS in round 2.

### What was reviewed, and at what state

Hashes at review time (`shasum -a 256`, `2026-09-13T02:59:16Z`) — identical to the Verifier's GREEN
(round 1) record for every Developer file and for the gating test file:

```
c0c6c6533446a4060877e4080ee493ebb3522336b97a93b1bc75a6def101d27a  windows/win_update.py
b7e0198fa0e850dc8547f08770f1d7d0f179b5eaf5b8fe230ca05c3a063b67ac  windows/verify_win_artifact.py
465bd076acc74a45a3f53f12bb6b2b10c786f30d615ce154976658b22cda8ebe  windows/claude_pet_win.py
125d91057ad4a512f0e7af4332324b798c2e73275d410446762fa0a73433488a  windows/build_win.py
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss
1ece3f3e8008356d41d7d2a35860b4914c86819570be9af887f7a61b33365f3f  windows/README.md
ce7699cad75ff3fd471773954f709ff9538bdcaa5aed5393e4a60492512b1d69  windows/tests/test_win_update.py
48764799ce3c07899fb4aa47424240bafe50afbd58d77cc70b57ed78a54047ca  windows/tests/__init__.py
```

The core is untouched: `git diff --stat -- claude_pet.py tests/ AGENTS.md CLAUDE.md` is empty, so
`claude_pet.py` in the worktree is HEAD's. (It differs from the *main checkout's* working copy at
`/Users/yeongyu/claude-pet`, which carries Track A's uncommitted OAuth changes — not this change's
concern; the port reaches the core only through `cp._ver_tuple`, `cp._zip_members_are_safe`,
`cp._download_update_zip`, `cp.UNINSTALL_PATHS`, `cp.UPDATE_LOCK_DIR`, `cp.CONFIG_PATH`,
`cp.GITHUB_REPO`, `cp.APP_VERSION`, `cp.UPDATE_CHECK_SEC`, `cp._upd_cache`, `cp.L`, `cp.t`,
`cp._dbg`, all of which exist in both.)

### AGENTS.md §2 — Condition A / B against the Verifier's record

- **Condition A holds.** The gating file's hash at review time equals the hash the Verifier recorded
  under RED-0 (`2026-09-13T02:00:43Z`) and again under GREEN (round 1). No assertion, expected value
  or fixture literal changed between RED and GREEN.
- **Condition B holds as recorded.** The Verifier's record lists exactly three files it created
  (`windows/tests/__init__.py`, `windows/tests/test_win_update.py`, the record) and states no
  production file was opened for writing; `git status` shows the four modified production files and
  the two new ones as the Developer's. This cannot be confirmed from `git log` until the commit
  exists — the trailers on the eventual commit must name the two parties as the record does.

### AGENTS.md §3 — red before green

- RED-0 is recorded verbatim: `Ran 71 tests … FAILED (failures=3, errors=73)` with the
  `ModuleNotFoundError` traceback and the three `installer.iss` assertion messages.
- A module-absent red proves the gates run, not that they discriminate; the Verifier addressed that
  with three rival modules (R1–R3) and a per-gate table. Two gates are green under every rival, both
  declared: the asset-name guard (its red observed separately by renaming the assets in a scratch
  copy, output quoted) and `test_internal_must_be_a_directory` (declared non-discriminating in its
  own docstring). That is the §3 remedy done correctly.
- Not covered by a rival: `BuildWinMarkerTests.test_marker_writer_and_validator_agree` (ERROR under
  all rivals because no rival `build_win.py` was built). Its assertions are direct equalities on the
  path, the `"version"` key, the validator's acceptance and `REQUIRED` membership, so a wrong path or
  key fails on its own line; acceptable, noted for completeness.
- The swap script's **rollback** text is not pinned (the Verifier says so); B2 below is exactly the
  kind of defect an unpinned rollback hides, and round 2 should pin it.

### Suites — re-run by the Reviewer from the worktree root

```
$ python3 -m unittest discover -s windows/tests -t . -v      # 2026-09-13T02:59Z
Ran 71 tests in 0.037s
OK                                                            # 71 ok, 0 FAIL, 0 ERROR, 0 skipped

$ python3 -m unittest discover -s tests -v                    # started 2026-09-13T03:00Z, finished 03:06Z
Ran 565 tests in 327.056s
OK (skipped=8)
exit=0                                                        # 0 FAIL/ERROR lines
```

The 8 skips carry the same loud reasons the Verifier recorded: 3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`,
2 × preflight and 2 × stapler `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`, 1 × "no built bundle at …/dist/ClaudePet.app".
`PySide6` is not installed here (`ModuleNotFoundError`), so `claude_pet_win.py` was read, not imported —
as the assignment expects.

### Reviewer probes (scratchpad `review_probe.py`, temp dirs only, `2026-09-13T03:06Z`)

| probe | result |
| --- | --- |
| `build_swap_script` with parent `C:\Users\영규 O'Brien\AppData\Local\Programs` | every path appears only single-quoted (app 6/6, new 4/4, old 4/4, exe 6/6, log 1/1 occurrences quoted); `O''Brien` present, raw `O'Brien` absent; Korean survives untouched |
| same script, structure | `Move-Item` × 5, `Rename-Item` × 0, `Test-Path` × 0 — no existence check on `old_dir` (→ B2) |
| `log_update` with every field shape the port passes (check/download/verify/install/extract/layout/stage/swap/uninstall/cleanup) | 10 lines, each `^<utc> <step>( k=v)*$`; the home directory and the temp directory never appear |
| `leftover_dirs` on a synthetic parent | complete `.claudepet-old-v0.23` → listed; `.claudepet-old-v0.24` without its exe → **skipped**; empty `.claudepet-stage-99-dead` → **listed by prefix alone** (→ N1); empty `.claudepet-new-x` → skipped |
| `install_kind` with a symlinked `unins000.exe` | `portable` |
| `swap_names(parent, "0.24", tok)` for two tokens | `old_dir` is the same `.claudepet-old-v0.24` both times (deterministic → B2 precondition) |
| `inno_silent_args` | `[setup, /SILENT, /SUPPRESSMSGBOXES, /NORESTART, /CLOSEAPPLICATIONS, /FORCECLOSEAPPLICATIONS, /RESTARTAPPLICATIONS, /RELAUNCH=1, /LOG=…\setup.log]` |
| `verify_win_artifact.check_zip` on synthetic zips | good → `[]`; marker `0.25` vs `--version 0.26` → refused; two roots → refused; `ClaudePet\..\evil.txt` → refused by the scan before extraction; missing `claudepet.ico` → refused. `check_installer`: `MZ` → `[]`, a zip → "not a PE executable", absent → "missing" |
| `_home_user_files("/H")` | `.claude_pet.json`, `.claude_pet.json.lock`, `claudepet_debug.log` — the three home entries of `cp.UNINSTALL_PATHS`, nothing under `~/.claude_pet` |
| `run_value_is_ours` | quoted form, upper-case, trailing ` --restart` → True; another path, `None` → False |
| `check_github_update_win` for ARM64 / `x86` / kind `source` with a newer tag | `("error", "no-asset")`, `("error", "unknown-machine")`, `("error", "unknown-kind")` — all three are deterministic and all three are treated as `failed` by the port (→ B1) |

### Design points, one by one

| point | finding |
| --- | --- |
| `install_kind` rule | As planned: `inno` iff `unins000.exe` is a regular, non-symlinked file beside `sys.executable` **and** the Inno `InstallLocation` value equals the exe directory under `ntpath.normcase` with one trailing `\` stripped; a raising reader is `portable`. Source runs are `source` in the port and never update. ✓ |
| asset table | `UPDATE_ASSET_NAMES_WIN` keyed `(machine, kind)`; AMD64×inno → `claude-pet-win-setup.exe`, AMD64×portable → `claude-pet-win.zip`; ARM64 → `no-asset`; https + `github.com` host enforced; ambiguity refused. Lives under `windows/`, the core table untouched. ✓ (see N3 on ARM64 hosts) |
| hourly semantics | `main()` primes `cp._upd_cache["t"]` before `PetWindow` starts its first refresh; the refresh worker checks only when `not state["update"]` and `> UPDATE_CHECK_SEC` elapsed; `_run_update_check` stamps the cooldown only on `update`/`current`. Matches macOS for the success and transient-failure cases. **✗ for deterministic refusals — B1.** |
| size + digest refusal, missing digest | `verify_download`: `bool`/negative/non-int size refused; size compared by `stat` before any read; digest must be `sha256:` + 64 hex, missing or malformed refuses even on a size match. Tests and probe agree. ✓ |
| zip safety scan before extraction | `scan_update_zip(dest)` (delegating to `cp._zip_members_are_safe`, observable by patching the core) runs before `os.mkdir(stage)`/`extractall`; the artifact gate does the same before its temp extraction. ✓ |
| layout validation incl. version marker | exactly one root `ClaudePet/`, exe a file, `_internal/` a dir, every `PORTABLE_REQUIRED` entry present and not a symlink, marker parseable with `"version"` equal to the tag **as a string**; reasons carry archive-relative names and counts only. `build_win.REQUIRED` *is* `win_update.PORTABLE_REQUIRED`, so the build gate and the updater cannot disagree. ✓ |
| swap script: spaces / Korean | Quoting is complete (probe). Written as UTF-8 with BOM so PowerShell 5.1 reads it; launched from System32 PowerShell with `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File`. ✓ — **rollback correctness ✗, B2.** |
| Inno silent flags | The plan's five plus `/FORCECLOSEAPPLICATIONS` and `/RELAUNCH=1`; argv is a list, `/LOG=` bare. Both additions are documented in README and `installer.iss` and are defensible (a forced close cannot tear the config; `[Run] … Check: RelaunchRequested` is the relaunch path a silent install would otherwise skip). ✓ — the `/LOG=` value with a space in `%LOCALAPPDATA%` is a hardware item (H12). |
| `RegisterApplicationRestart` + mutex | `register_application_restart("--restart", NO_CRASH\|NO_HANG\|NO_REBOOT)` before `QApplication`; `Local\me.yeongyu.claudepet` mutex held for the process lifetime, second instance exits before creating a window; `closeEvent → quit` as a WM_CLOSE fallback (Qt itself quits on `WM_ENDSESSION`, which is what the Restart Manager sends). ✓ in source; the relaunch is hardware-only (H1–H3). |
| uninstall scope | `uninstall_plan` deletes the three home files + the cache dir, never `~/.claude_pet` or `~/.claude` (test + probe); `delete_run_value_if_ours` removes the HKCU Run value only when it names this exe; inno → `unins000.exe /SILENT`, portable → helper that deletes the folder only while it still holds our exe **and** marker; source → `unin_devmode` only. Order mirrors `do_uninstall`: the refusable launch first, deletes after. ✓ — but see **B3** (lock during a running install). |
| `build_win.py` | `write_release_marker` before `verify`; `sign(ClaudePet.exe)` before `make_zip` so both artifacts carry the signed exe; `sign(setup.exe)` after ISCC; `verify_win_artifact.check_all` last and fatal. Signing default `off` (one info line), `signtool_argv` pure per mode, `redact_argv` masks the `/p` value, nothing else prints argv; `_need` names the missing variable, never a value. ✓ |
| `installer.iss [UninstallDelete]` | `{app}\_internal` (filesandordirs), `{app}\ClaudePet.exe`, `{localappdata}\me.yeongyu.claudepet`; no bare `{app}` while `DisableDirPage=auto`; `[Code] RelaunchRequested` reads `/RELAUNCH=1`. ✓ |
| README accuracy | Mostly accurate and unusually specific. Three sentences are false against the code: "ARM64 … 다시 시도하지 않습니다" (B1), "업데이트와 완전 삭제는 같은 파일을 잡습니다 … 다른 쪽이 들고 있으면 시작하지 않습니다" for the inno path (B3), and "이름만 보고 지우지 않습니다" for `.claudepet-stage-*` (N1). |
| core untouched | `git diff -- claude_pet.py` empty; the port only reads core symbols. ✓ |
| log privacy | Every `wu.log_update` call site passes status tokens, counts, the tag, `platform.machine()` or `type(e).__name__`; the one free-text field (`validate_portable_layout`'s reason) is archive-relative; the helper's `Note` writes literal tokens; Inno's own `/LOG` is a separate `setup.log` that Inno fills with install paths (its file, removed on uninstall — H-pass must quote only status lines from it). Probe: no home or temp path in the written log. ✓ |

### Blocking items

**B1 — Deterministic refusals re-poll GitHub every 30 s, forever.** `check_github_update_win` returns
`("error", "no-asset")` for ARM64 (and `unknown-machine`, `unknown-kind`); `_run_update_check` maps
every error to `failed` and — mirroring `poll_github_update`'s rule for *transient* failures — never
stamps `_upd_cache["t"]`. With `state["update"]` unset, the refresh worker therefore calls
`api.github.com` on every 30-second refresh after the first hour (120/h against the unauthenticated
60/h limit, whose 403s are errors too). This contradicts the plan ("explicit 'no asset' status" — the
test docstring adds "so the UI can say so instead of retrying forever"), the README ("다시 시도하지
않습니다"), and the hourly design point. Fix: a pure `win_update` helper deciding which reasons stamp
the cooldown — everything except `fetch-failed:*` and `bad-payload` is a property of the published
release, not of the network, and the next hourly check sees a re-edited release just as well — and
have `_run_update_check` stamp on those. Round-2 gate: `no-asset` stamps, `fetch-failed:OSError`
does not.

**B2 — The portable rollback can nest the old tree into the install.** `swap_names()` makes `old_dir`
deterministic (`.claudepet-old-v<APP_VERSION>`), `_install_update` never checks it is absent, and
`build_swap_script` uses `Move-Item` for both renames (probe: 5 × `Move-Item`, 0 × `Rename-Item`,
0 × `Test-Path`). PowerShell's `Move-Item` with an *existing directory* as `-Destination` moves the
source **inside** it, so with a leftover `.claudepet-old-v<same version>` the first rename lands the
install at `.claudepet-old-v0.24\ClaudePet`, `$moved` is true, and both rollback branches then move
that tree to `ClaudePet\ClaudePet` — no pet, nested folders, and the old exe `Start-Process` fails.
The precondition is real: a *partially* removed old tree (a DLL held by AV during `Remove-Item`)
lacks the exe or marker, so `leftover_dirs()` skips it (probe) and it survives every launch. Fix
before anything irreversible: refuse in `_install_update` when `os.path.lexists(old_dir)` (log
`install status=refused reason=old-dir-exists`) and switch both renames to `Rename-Item`, which fails
on an existing destination — the no-overwrite primitive this repository prizes. Round-2 gates: the
refusal (pure, temp dirs) and a text pin that the script contains no `Move-Item`.
*Move-Item semantics are stated from PowerShell's documented behaviour; no PowerShell is installed on
this Mac, so H4 should include the "old dir pre-exists" case if the Developer keeps `Move-Item`.*

**B3 — The lock does not cover the Inno installer's run.** On the inno path `_install_update` closes
the share-none handle in its `finally` immediately after `popen_detached(setup.exe …)` (the handle is
`DELETE_ON_CLOSE`, so the lock file is gone too). `state["installing"]` blocks a second update but
`_uninstall` never consults it, so "완전 삭제…" during the installer's run takes the lock and launches
`unins000.exe /SILENT` beside a running setup. README's "다른 쪽이 들고 있으면 시작하지 않습니다" is
false for that window. Fix: `_uninstall` refuses with `unin_busy` while `state["installing"]`, and the
README sentence says which mechanism covers which kind (the handle for portable and the flag for inno).

### Non-blocking, to fix or decide in round 2

- **N1** `leftover_dirs` appends `.claudepet-stage-*` on the prefix alone (probe: an empty stage dir
  is listed) while its docstring and README say "never by name alone". Require
  `<stage>\ClaudePet\_internal\claudepet-release.json` (the marker sits one level down in a stage
  tree) or correct both texts.
- **N2** `open_update_lock`'s `os.makedirs` sits outside any `try`; an `OSError` there escapes
  `_install_update` on the worker thread (no message reaches the user) and `_uninstall` on the GUI
  thread. Wrap and log `status=failed error=<type>`.
- **N3** ARM64 hosts, a decision for the user rather than a defect: `installer.iss` sets
  `ArchitecturesAllowed=x64compatible`, which admits ARM64 Windows through x64 emulation, and the
  x64 build runs there; CPython ≥ 3.12's `platform.machine()` on Windows reports the *native*
  architecture through WMI even inside an emulated process (`platform._get_machine_win32`), so such
  a user is told "no build for this machine" (and, until B1, hammered GitHub). Either the table
  offers the AMD64 assets to `ARM64` (they are what the installer already accepted) or the README
  says ARM64 installs do not self-update. Unverifiable here — the user's machine is AMD64 (H11).
- **N4** `release/claude-pet-win-setup.exe` is not gitignored (`.gitignore` has `*.zip`/`*.dmg`
  only), so a Windows build leaves an untracked `.exe` in the mixed `release/` directory. Add `*.exe`
  (a `main`-branch file; note only).
- **N5** `state["installing"]` never clears. If the installer exits without closing the pet (a
  refused install, a crash), the "새 버전 vX 설치" item stays and every click answers
  `upd_install_failed`. Consider clearing it when the launched process exits with a non-zero code
  (`Popen.poll()` from the refresh worker) and logging `install … status=exited rc=<n>`.
- **N6** `sign()` looks for `signtool` before validating the mode, so `CLAUDE_PET_WIN_SIGN=typo` on a
  machine without the SDK reports "signtool not found". Validate the mode first.
- **N7** Two module objects for one file in the tests: `windows.build_win` imports `win_update`
  top-level (via `sys.path`), the tests import `windows.win_update`. Harmless today (file-based
  assertions), but a future `mock.patch.object(wu, …)` would not reach `build_win`'s copy.
- **N8** `InstallerScriptTests.setUp` opens two files without closing them (`ResourceWarning` in the
  run); the Verifier already scheduled the `with` fix for round 2 and a new hash.
- **N9** After an inno update the 56 MB `setup.exe` stays in the cache until the next update
  overwrites it or the uninstaller removes the folder. Bounded; fine, but say so in README.
- **N10** Parity memory: `TR_WIN` adds four Windows-only strings (`upd_no_asset`, `upd_source`,
  `upd_installing`, `unin_busy`) for situations macOS does not have. Not a UI break; list it as a
  deviation when the parity table is next updated.
- **N11** The 60 s `clean_update_leftovers` timer versus the helper's ≤ 23 s alive window (20 polls ×
  0.5 s + 3 s) is a deliberate margin; record it so neither side shortens it independently.

### Hardware-only verification (cannot be observed on macOS — for the later Windows pass)

Read `%LOCALAPPDATA%\me.yeongyu.claudepet\update.log` (tokens only) and `setup.log` (Inno's; quote
status lines only, it contains install paths). Any `update.log` line carrying a user path is a
Privacy defect regardless of what else passed.

- **H1** `setup.exe /SILENT … /CLOSEAPPLICATIONS` closes the Qt tool window gracefully (Qt quits on
  `WM_ENDSESSION`); `setup.log` shows no forced close, so `/FORCECLOSEAPPLICATIONS` never fires on a
  healthy pet.
- **H2** `RestartApplications=yes` + `RegisterApplicationRestart("--restart")` relaunches the pet and
  `[Run] … /RELAUNCH=1` plus the mutex leave exactly **one** `ClaudePet.exe`; `update.log` shows
  `check status=update`, `download … status=ok`, `verify … status=ok`, `install … status=launched`.
- **H3** A manual (non-silent) upgrade through the installer UI also relaunches the pet (commit
  `db1dedc`'s promise, never verified).
- **H4** Portable swap end to end: `swap begin pid=…`, `swapped=ok`, `new-app=running`,
  `old-tree=removed`, old folder gone; then an injected launch failure (rename the staged exe before
  the helper runs) → `failed=new-app-not-running rollback=start`, `rollback=ok`, old pet back. If
  `Move-Item` is kept (B2), add the pre-existing `.claudepet-old-v<version>` case.
- **H5** Lock: during the helper's run a second update reports `install status=refused
  reason=lock-busy`; after the helper exits the lock file is gone (`DELETE_ON_CLOSE`) and the next
  update is **not** `lock-busy` — i.e. `Start-Process` did not leak the inherited handle into the new pet.
- **H6** `verify_download` against the live release JSON's `size`/`digest` for both real assets.
- **H7** `install_kind` on a real Inno install (the registry `InstallLocation` value's exact form —
  trailing backslash, case) and on a portable extraction; a source run reports `upd_source`.
- **H8** Uninstall, inno: only `%USERPROFILE%\.claude_pet\` remains; Run value, Start-menu shortcut,
  Add/Remove entry, `{app}` and the cache dir are gone. Uninstall, portable: the folder is removed
  after exit and nothing else is.
- **H9** PowerShell helper under Constrained Language / AppLocker, and AV behaviour on an
  app-spawned `powershell.exe` with `-ExecutionPolicy Bypass`.
- **H10** SmartScreen on the downloaded `setup.exe` (urllib adds no Mark-of-the-Web): the silent
  install runs without a prompt.
- **H11** `platform.machine()` on an ARM64 host running the x64 build (N3) — record as unverified if
  no such machine is available.
- **H12** A user profile with a space and Korean characters end to end: the `-File` path, the
  `/LOG=` value (subprocess quotes the whole token; Inno's parser must still read it as one
  parameter), and every path inside the swap script.
- **H13** `clean_update_leftovers` 60 s after start: removes a planted complete
  `.claudepet-old-v0.0` tree, leaves an unrelated sibling folder, and never races the helper on a
  live swap.

### What round 2 needs

1. Developer: B1, B2, B3 (and N1/N2 if cheap), README sentences corrected to match.
2. Verifier: gates for B1 (cooldown by reason), B2 (refusal on an existing `old_dir`; no `Move-Item`
   in the script), B3 (`_uninstall` refuses while installing — pure if the check is factored into
   `win_update`), rollback text pins; the `setUp` file-handle fix with the new hash; RED observed
   against the current tree before the fixes land (they are all observable red today).
3. Reviewer: round 2 on the new hashes.

Reviewer's scratch instrument: `review_probe.py` under the session scratchpad — not part of the tree.

## Review round 2

Role unchanged: **Reviewer** (`reviewer-cd`, independent). Same worktree, branch `windows`, HEAD `d4050ee`,
nothing committed. Scope: the Developer's round-2 fixes for B1–B3 (+ N1, N2, N5, N9, N11), the Verifier's
"GREEN (post-review 1)" record with its 23 round-2 gates, and the whole change again against the design
points. Every number below is a test count, a hash or a probe result read from quoted output at the quoted
UTC time; nothing was measured on a corpus.

### Verdict: **FAIL** — one blocking item (B4), new and cheap; B1–B3 are fixed, wired and gated

The three round-1 blockers are closed in production code, in the README, and by Verifier-owned gates that
were observed red first. What blocks now is a defect that predates round 2 and that I missed in round 1:
both "could not launch the uninstaller/helper" handlers in `_uninstall` call `wu.log_update("uninstall",
kind=…, step=…, error=…)` — and `step` is `log_update`'s first positional parameter, so the handler raises
`TypeError` instead of logging and showing `unin_fail`. On a managed PC where AppLocker blocks
`powershell.exe` (exactly H9's scenario) the user confirms "완전 삭제…" and nothing visible happens.
Nothing is deleted on that path and the lock is released by the `finally`, so it is a reporting defect, not
a data one — but it is reproducible on macOS, one word per line to fix, and gateable.

### What was reviewed, and at what state

Hashes at review time (`shasum -a 256`, `2026-09-13T13:37:57Z`) — identical to the Verifier's
"GREEN (post-review 1)" record for every Developer file and for the gate file:

```
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py          (round 1: c0c6c653…)
5a5af83a5a7ad444be8d4d01b43df46d1fd516e2b301c6e200836a3d8a2aa978  windows/claude_pet_win.py      (round 1: 465bd076…)
411481c0a2ee2fc5ffa52ba913c6bb3541c45adc557cefbad695a58d1dff86cc  windows/README.md              (round 1: 1ece3f3e…)
b7e0198fa0e850dc8547f08770f1d7d0f179b5eaf5b8fe230ca05c3a063b67ac  windows/verify_win_artifact.py (unchanged)
125d91057ad4a512f0e7af4332324b798c2e73275d410446762fa0a73433488a  windows/build_win.py           (unchanged)
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss          (unchanged)
a65410c3f871f295d887c41adaf8dfe7a504fe8803adf620c534dccde5d5db86  windows/tests/test_win_update.py (round 1: ce7699ca…)
48764799ce3c07899fb4aa47424240bafe50afbd58d77cc70b57ed78a54047ca  windows/tests/__init__.py      (unchanged)
```

The core is still untouched: `git diff --stat -- claude_pet.py` is empty and `git status` lists the same
four modified tracked files and six untracked ones as round 1 (plus the two docs-design records). The port
reads `cp._ver_tuple`, `cp._zip_members_are_safe`, `cp._download_update_zip` (its `UPDATE_DOWNLOAD_MAX` is
400 MiB, so the 72 MB zip and 56 MB installer fit), `cp.UNINSTALL_PATHS`, `cp.UPDATE_LOCK_DIR`,
`cp.CONFIG_PATH`, `cp.GITHUB_REPO`, `cp.APP_VERSION`, `cp.UPDATE_CHECK_SEC`, `cp._upd_cache`, `cp.L`,
`cp.t`, `cp._dbg` — all present in HEAD's core.

### AGENTS.md §2 — Condition A / B, checked by diff this time

- **Condition A holds, and this round it is verified rather than inferred.** A copy of the round-1 gate
  file survives in the session scratchpad (`guardcopy/windows/tests/test_win_update.py`, hash
  `ce7699ca…` — the RED-0 / GREEN (round 1) file). `diff` against the current `a65410c3…` shows exactly
  **two removed lines**, the `open(...).read()` pair in `InstallerScriptTests.setUp`, replaced by two `with`
  blocks (the N8 file-handle fix, no assertion); every other hunk is additive (`24a25,33` the module
  docstring's round-2 surface, `1140a`/`1141a`/`1142a` the six new classes appended after
  `InstallerScriptTests`, 365 added lines in all). No round-1 assertion, expected value or fixture literal
  was edited or reordered.
- **Condition B holds as recorded.** The Verifier's record names the two files it edited this round (the
  gate file and its own record) and states no production file was opened for writing; the three Developer
  files that changed between rounds (`win_update.py`, `claude_pet_win.py`, `README.md`) are the ones the
  fix descriptions name. Still not confirmable from `git log` until the commit exists.

### AGENTS.md §3 — red before green, round 2

- The 23 round-2 gates were observed red against a scratch pre-fix tree, output quoted verbatim
  (`Ran 94 tests … FAILED (failures=6, errors=40)` with the six `FAIL` messages). The Verifier declares the
  one deviation plainly: the port and README copies round-tripped byte-exact to their round-1 hashes, but
  `win_update.py` did not (the `Move-Item` → `Rename-Item` rewrite was not in the patch script), so that
  file was restored **by behaviour** (`Move-Item 5 / Rename-Item 0 / Test-Path 0`, the four helpers
  absent) and the record says so. That is the §3 "revert and observe" remedy with its limits stated —
  acceptable.
- Discrimination: six rival modules (RA–RF) with a per-gate table; every gate fails on an assertion or an
  error raised inside a rival under at least one column, and `SwapRefusalTests.test_all_clear_is_none` is
  declared as the acceptance row that only the absent helper turns red. The `CooldownTests` truth table
  covers the rival I named in round 1 (stamp only on update/current) and the inverted one.
- The `SwapScriptRollbackTests` pins are the rollback-text pins I asked for: no `Move-Item`, `Test-Path`
  on `old_dir` before the first rename, both rollback branches rename old→app after new→app, the
  dead-new-app branch unwinds app→new first, and every rollback `Start-Process`es the old exe before its
  `exit`.

### Suites — re-run by the Reviewer from the worktree root

```
$ python3 -m unittest discover -s windows/tests -t . -v      # finished 2026-09-13T13:38:18Z
Ran 94 tests in 0.063s
OK                                                            # 94 ok, 0 FAIL/ERROR, 0 skipped, 0 ResourceWarning

$ python3 -m unittest discover -s tests -v                    # started 2026-09-13T13:38:23Z, finished 13:43:57Z
Ran 565 tests in 334.118s
OK (skipped=8)
exit=0                                                        # 0 FAIL:/ERROR: lines
```

The 8 skips are the same loud reasons as every earlier run: 3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`,
2 × preflight and 2 × stapler `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`, 1 × "no built bundle at …/dist/ClaudePet.app".
`PySide6` is still not installed here; `claude_pet_win.py` was read, not imported.

### B1–B3, read from the round-2 source

| item | what the code does now | verdict |
| --- | --- | --- |
| **B1** | `transient_check_reason()` is true only for `bad-payload` and `fetch-failed:*`; `stamps_cooldown()` is true for `update`/`current` and every non-transient `error`, false (never raising) for a malformed result. `_run_update_check` computes `stamped = wu.stamps_cooldown(got)` before branching and logs `check status=error reason=<r> cooldown=<0|1>`. Probe: all eight reason tokens the check can emit (`ambiguous-asset`, `bad-payload`, `bad-url`, `missing-asset`, `no-asset`, `no-tag`, `unknown-kind`, `unknown-machine`) plus `fetch-failed:OSError` classify as the README says. | fixed ✓ |
| **B2** | `swap_refusal()` (`old-dir-exists` → `new-dir-exists` → `app-dir-missing` → `not-siblings`, `lexists`/`islink` semantics) is asked in `_install_update` **before the lock and before `_download_update_zip`**, and again after the layout check. `build_swap_script` uses `Rename-Item -LiteralPath <full> -NewName <basename>` for all five renames, `Move-Item` × 0, and opens with `Test-Path -LiteralPath '<old_dir>'` → `refused=old-dir-exists`, drop staging, start old exe, `exit 6`. Probe with parent `C:\Users\영규 O'Brien\AppData\Local\Programs`: new 4/4, old 4/4, exe 7/7, log 1/1 occurrences single-quoted, app dir quoted in all 3 stand-alone occurrences (its other 7 substring hits are inside the exe path); every `-NewName` value is a bare quoted basename; `O''Brien` present, raw `O'Brien` absent, Korean intact; `Test-Path(old)` at offset 881 precedes the first `Rename-Item` at 1416. | fixed ✓ |
| **B3** | `uninstall_refusal(state)` → `"installing"`; `_uninstall` asks it on entry (before the confirm box) and again after it, then takes the share-none lock; `_install_update` refuses with `reason=installing` while `self._installer` is alive and `_reap_installer()` (30 s worker) clears the flag and logs `install kind=inno status=exited rc=<n>` when the installer exits without closing the pet (N5). README's lock paragraph now says which mechanism covers which kind. | fixed ✓ |
| N1 | `leftover_dirs` lists `.claudepet-stage-*` only when `set(listdir) <= {"ClaudePet"}`; `-new-*`/`-old-*` still need exe + marker; symlinked entries skipped. README and both docstrings match. | fixed ✓ |
| N2 | `open_update_lock`'s `makedirs` wrapped; logs `lock status=failed error=<type>` and returns `None`. | fixed ✓ |

### Design points re-checked (only what round 2 touched; the rest stands as in round 1)

- **hourly semantics** — now correct for every outcome: `main()` primes `cp._upd_cache["t"]` before `PetWindow`,
  the worker checks only after `UPDATE_CHECK_SEC` and only while no update is known, and deterministic
  refusals wait the hour. This is a deliberate, documented divergence from `poll_github_update` (which
  never stamps on `failed`) and it is the right one for the reason B1 gave. ✓
- **swap script, spaces + Korean** — see the B2 row. `-NewName` takes a name, and every name here is
  `ClaudePet`, `.claudepet-old-v<ver>` or `.claudepet-new-<pid>-<hex>`; the one user-controlled name is the
  installed folder's basename, which is whatever the user extracted to. ✓ (H4 covers the live rename.)
- **uninstall scope** — unchanged: `_home_user_files("/H")` → the three home entries of `cp.UNINSTALL_PATHS`,
  the cache dir, never `~/.claude_pet` or `~/.claude`; Run value deleted only when it names this exe. ✓
- **README accuracy** — the three round-1 falsehoods are corrected in place. One new clause is false (N12
  below); everything else I re-read matches the code, including the new `old-dir-exists`, `status=exited`,
  cache-retention and cleanup sentences.
- **log privacy** — every `wu.log_update` call site (28 in the port, enumerated by grep) passes status
  tokens, counts, the tag, `platform.machine()`, `rc`, or `type(e).__name__`; the only free text is
  `validate_portable_layout`'s reason, which the probe confirms carries archive-relative names
  (`required entry missing: _internal/frames`) and exception class names, never the extraction path. 24
  log lines written with every call-site shape match `^<utc> <step>( k=v)*$` and contain neither the home
  nor the temp directory. The helper's `Note` strings are 14 literal tokens. ✓ — except that two of the
  28 call sites never execute (B4).

### Blocking item

**B4 — `_uninstall`'s two launch-failure handlers raise `TypeError` instead of logging and telling the user.**
`wu.log_update(step, path=None, **fields)` takes `step` positionally; `claude_pet_win.py` calls
`wu.log_update("uninstall", kind=kind, step="run-uninstaller", error=type(e).__name__)` (inno,
`popen_detached(argv)` failed) and `… step="run-helper" …` (portable, writing or launching the PowerShell
helper failed). Both raise `TypeError: log_update() got multiple values for argument 'step'` — reproduced
here with the exact kwargs (`2026-09-13T13:43Z`; the log file was not even created). The exception leaves
the handler before `self._info(unin_title, unin_fail)`, escapes the Qt slot on the GUI thread (a traceback
to the invisible stderr of a windowed exe), and the `finally` releases the lock. So the *safety* half of
the comment above it ("Popen 이 실패하면 아직 아무것도 지우지 않았다") holds, and the *reporting* half does
not: no message, no `update.log` line. The realistic trigger is H9 — a managed PC whose AppLocker policy
blocks `powershell.exe` — where "완전 삭제…" then silently does nothing. Both lines exist unchanged in the
round-1 port (`465bd076…`, lines 1260/1271); I did not run those two shapes through my round-1 probe, so
this is a round-1 miss, not a regression. Fix: rename the keyword (`at=` / `phase=`) or pass the step in the
positional slot. Round-3 gate (Verifier, pure): parse every `wu.log_update(` call in the port with `ast`,
substitute a token for each value, and call `win_update.log_update` with those kwargs into a temp file —
which catches this whole class (`step=`/`path=` collisions), not only these two lines.

### Non-blocking, new this round

- **N12** README "ARM64 는 … 매시간 확인만 계속합니다(자산이 나중에 올라오면 그때 잡힙니다)" — the
  parenthetical is false: `UPDATE_ASSET_NAMES_WIN[("ARM64", *)]` is `()`, so `select_update_asset_win`
  returns `no-asset` before it reads the asset list (probe: an `ARM64` check against a release carrying a
  hypothetical `claude-pet-win-arm64.zip` is still `(None, "no-asset")`). An ARM64 build would need a new
  app version with the table extended, which an ARM64 user can only get by manual install. Say that.
- **N13** `clean_update_leftovers` (60 s one-shot, GUI thread) runs without the lock. An update started
  in the first minute of a run can have its `.claudepet-stage-*` removed mid-extract or its complete
  `.claudepet-new-<token>` removed between the rename and the pet's exit; the outcomes are `extract failed`
  or the helper's `failed=new-to-app rollback=start` → old pet relaunched — a wasted update, never a
  corrupted one. Cheap fix: `open_update_lock`, skip when `None`, close after.
- **N14** `_check_update` collapses every `_install_update` refusal into `upd_install_failed`; the token
  (`old-dir-exists`, `lock-busy`, `installing`) reaches only `update.log`, so the README's "delete that
  folder" advice has no UI counterpart. A TR string for `old-dir-exists` would close the loop.
- **N15** Portable install under an unwritable parent (Program Files) is discovered at `os.mkdir(stage)`,
  *after* the 72 MB download. Creating the stage directory before `_download_update_zip` (and extracting
  into it) moves that refusal in front of the download at no cost.
- **N16** `_uninstall` (inno) lists `exe_dir` in the confirm box while the uninstaller removes only
  `_internal`, `ClaudePet.exe` and what it installed — a slight overstatement when the user installed into
  a shared folder. Cosmetic.

Open from round 1, unchanged files: **N3** (ARM64 hosts running the x64 build — user decision), **N4**
(`*.exe` in `.gitignore`, a `main` file), **N6** (`sign()` finds `signtool` before validating the mode),
**N7** (two module objects for `win_update` in the tests), **N10** (four Windows-only TR strings — parity
memory).

### Hardware-only verification (for the later Windows pass) — H1–H13 stand; add:

- **H14** Plant `.claudepet-old-v<current>` beside the app, click "업데이트 확인…" → `install … status=refused
  reason=old-dir-exists` with **no** `download` line before it; delete the folder → the update proceeds. Plant
  it again *while the helper is waiting for the pid* → `swap refused=old-dir-exists`, staging gone, old pet back.
- **H15** Cancel the silent installer (or let it refuse) → within 30 s `install kind=inno status=exited rc=<n>`,
  the "새 버전 vX 설치" item still present, and a second click launches setup again.
- **H16** While setup.exe is running and waiting to close the pet: "완전 삭제…" → `uninstall status=refused
  reason=installing` and the `unin_busy` box; a second "업데이트 확인…" → `install status=refused reason=installing`.
- **H17** Cooldown lines: with the network down `check status=error reason=fetch-failed:… cooldown=0` on
  every 30 s refresh; on ARM64 (if available) `reason=no-asset cooldown=1` once an hour.
- **H18** `Rename-Item` under AV: the 40 × 500 ms retry on app→old succeeds after a scanner releases a DLL;
  `failed=app-to-old` + old pet relaunched when it never does.
- **H19** `clean_update_leftovers` at 60 s after a swap does not race the helper's `Remove-Item` of the old
  tree (both delete the same tree; N13's window is the in-flight update case, not this one).
- **H20** `unins000.exe /SILENT` launched while the pet is still alive for a few ms: the uninstall completes
  (Inno's own Restart Manager handling in uninstall mode), no "some elements could not be removed" box,
  and Restart Manager does not try to relaunch a deleted exe.
- **H21** After B4 is fixed: block `powershell.exe` (AppLocker or rename it in a VM) and run "완전 삭제…" on a
  portable install → `unin_fail` box, `uninstall kind=portable … error=<type>` in `update.log`, nothing deleted.

### What round 3 needs

1. Developer: B4 (two keywords), and N12 (one README clause); N13/N15 if cheap.
2. Verifier: the `ast`-driven `log_update` call-shape gate described under B4, observed red against the
   current port text before the fix; a text pin that the README's ARM64 sentence no longer promises a
   later pickup is optional.
3. Reviewer: round 3 on the new hashes. Everything else in this change is ready.

Reviewer's scratch instrument this round: `review_probe_r2.py` under the session scratchpad — not part of
the tree. The macOS suite log is `macos_suite_r2.log` beside it.

## Review round 3

Role unchanged: **Reviewer** (`reviewer-cd`, independent — held no Developer or Verifier role on this change).
Same worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD `d4050ee`, nothing committed.
Python 3.13.7, `Darwin 25.5.0`. Scope: the Developer's B4 fix, the README bullet that came with it, the
Verifier's "GREEN (post-review 2)" and "ROUND 3" records with their two new gate classes, and a regression
check of everything else against my round-2 hashes. Every number below is a test count, a hash, a line
count or a probe result read from quoted output at the quoted UTC time; nothing was measured on a corpus.
Scratch instruments and logs for this round live under the session scratchpad at `rev3/` and are not part
of the tree.

### Verdict: **PASS** — B4 is closed at both call sites, gated red-before-green, and nothing else moved

The two handlers now bind (`status="failed", at="run-uninstaller"` / `at="run-helper"`), each one logs one
well-formed line, tells the user and returns before anything is deleted. The round-3 gate I asked for exists
in the shape I asked for, I observed it red myself on the pre-fix bytes — reconstructed from the worktree by
my own script and matched by hash to the retained copy and to my round-2 record — and it is green on the
worktree. Both suites are green. The five other production files are byte-identical to round 2. No blocking
item remains; the open N-items are listed below and none of them gates this merge.

### What was reviewed, and at what state

Hashes at review time (`shasum -a 256`, `2026-09-13T14:32:34Z`), against my round-2 record:

```
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py          (unchanged since round 2)
bb565b086f12a6a46e30049d7dd4f60cdf1a9ef161eec3e4ff3cc63885e5c6a4  windows/claude_pet_win.py      (round 2: 5a5af83a…)
912b88681cbcc1f93b7907a3c50d5858e25d9b737a1240e58b20b0621737d014  windows/README.md              (round 2: 411481c0…)
b7e0198fa0e850dc8547f08770f1d7d0f179b5eaf5b8fe230ca05c3a063b67ac  windows/verify_win_artifact.py (unchanged)
125d91057ad4a512f0e7af4332324b798c2e73275d410446762fa0a73433488a  windows/build_win.py           (unchanged)
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss          (unchanged)
63cfe9b99e07da65b6d47fe2b83891a06eb70853e45de967633248f82ae28d28  windows/tests/test_win_update.py (round 2: a65410c3…, via 421fd118…)
48764799ce3c07899fb4aa47424240bafe50afbd58d77cc70b57ed78a54047ca  windows/tests/__init__.py      (unchanged)
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py                  (HEAD's; `git diff --stat -- claude_pet.py tests/ AGENTS.md CLAUDE.md` is empty)
```

Identical to the hashes in the Verifier's ROUND 3 record. `git status --porcelain --untracked-files=all`
(minus `__pycache__`) lists the same four ` M` and six `??` entries as round 2. **Exactly three files changed
since round 2, and each by exactly what was announced**, read by `diff` against retained copies whose hashes
I checked first:

- `windows/claude_pet_win.py` (`5a5af83a…` → `bb565b08…`): lines 1286 and 1297 only —
  `kind=kind, step="run-uninstaller", error=…` → `kind=kind, status="failed", at="run-uninstaller", error=…`,
  and the same for `run-helper`. `diff … | wc` = two `c` hunks, nothing else.
- `windows/README.md` (`411481c0…` → `912b8868…`): one bullet, three lines, added after line 150 in the
  hardware-check list (`150a151,153`) — the H21 scenario with the tokens as the port now writes them. Nothing
  else; in particular the N12 clause on line 48 is unchanged.
- `windows/tests/test_win_update.py`: two purely additive steps. `a65410c3…` → `421fd118…` (the Verifier's
  post-review-2 file) is 137 added lines, 0 removed (`32a33,38` docstring, `63a70` `import ast`,
  `1575a1583,1610` helpers, `1577a1613,1714` `LogUpdateCallShapeTests`); `421fd118…` → `63cfe9b9…` is 132
  added, 0 removed (`38a39,42` docstring, `72a77` `import inspect`, `1711a…1846` `_port_source`,
  `_log_update_sites`, `_count_lines`, `LogUpdateKeywordBindingTests`). No `<` line in either diff, so no
  round-1 or round-2 assertion, expected value or fixture literal was edited or reordered.

### AGENTS.md §2 — Condition A / B

- **Condition A holds, by diff.** The Developer's change touches no test file: the gate file the Verifier
  read before editing (`a65410c3…`) is the one my round 2 read, and both diffs from there are additive-only
  (above).
- **Condition B holds as recorded.** The Verifier names its two edited files (the gate file and its record);
  the seven production hashes it re-read after its runs are the ones I read. As in rounds 1–2, this is
  confirmable from `git log` only once the commit exists.

### AGENTS.md §3 — red before green, observed by the Reviewer

I did not rely on the Verifier's RED. From the worktree's `bb565b08…` port my own script (`rev3/`, asserting
each current line occurs exactly once) put the two old lines back; the result hashes
`5a5af83a5a7ad444be8d4d01b43df46d1fd516e2b301c6e200836a3d8a2aa978` — `cmp`-identical to the retained
`vcd3/rivals/R0/windows/claude_pet_win.py` and equal to the `claude_pet_win.py` hash in my round-2 record —
with `step="run-…"` at 1286/1297. Then, from the worktree root, `2026-09-13T14:33:49Z`–`14:33:50Z`:

```
$ CLAUDE_PET_WIN_PORT_SOURCE=…/rev3/prefix/claude_pet_win.py \
    python3 -m unittest discover -s windows/tests -t . -v -k LogUpdateKeywordBindingTests
[CLAUDE_PET_WIN_PORT_SOURCE] gating …/rev3/prefix/claude_pet_win.py sha256=5a5af83a5a7ad444be8d4d01b43df46d1fd516e2b301c6e200836a3d8a2aa978
test_every_call_site_binds_and_writes_exactly_one_line (…) ... FAIL
test_no_call_site_hides_or_misroutes_its_field_names (…) ... ok
AssertionError: Lists differ: ["line 1286: bind: TypeError: multiple val[353 chars]d 1'] != []
- ["line 1286: bind: TypeError: multiple values for argument 'step'",
-  'line 1286: call: TypeError: log_update() got multiple values for argument '
-  "'step'",
-  'line 1286: the log gained 0 lines, expected 1',
-  "line 1297: bind: TypeError: multiple values for argument 'step'",
-  'line 1297: call: TypeError: log_update() got multiple values for argument '
-  "'step'",
-  'line 1297: the log gained 0 lines, expected 1']
Ran 2 tests in 0.023s
FAILED (failures=1)                                          exit=1
```

The same six findings, verbatim, against the retained R0 copy (`5a5af83a…`) and — at lines 1260/1271 —
against the round-1 port (`vcd2/prefix/…`, `465bd076…`, my round-1 hash). Logs: `rev3/red_*.log`. All three
layers agree per line (signature refuses, real call raises, log gains nothing), which is the whole of B4 —
the missing log line included — seen rather than inferred.

**Discrimination.** The eight retained rivals (`vcd3/rivals/RA`–`RH`, the worktree port with one edit each;
their `win_update.py` copies all hash `0fd40d9a…`, the worktree's), through the same override,
`2026-09-13T14:34:40Z`, T1 = names test, T2 = bind test: RA (`path="run-…"`) T1 FAIL `[1286, 1297] != []`,
T2 ok; RF (no positional step) T1 ok, T2 FAIL `missing a required argument: 'step'`; RH (`**dict` splat)
T1 FAIL `[1286] != []`, T2 ok; RB, RC, RD, RE, RG both ok — as the class docstring's table says, those five
change what a handler does, not how it binds. From each rival's own directory (`PYTHONPATH=` the worktree,
gate file `421fd118…`), the post-review-2 `LogUpdateCallShapeTests` is red on all nine (`14:34:44Z`: R0
failures=3, RA 1, RB 1, RC 2, RD 2, RE 2, RF 2, RG 2, RH 2). So the two classes together are red on every
rival and neither alone is, and each of the round-3 tests is the sole discriminator for at least one rival —
the Verifier's table holds under my runs.

### B4, read from the source and probed outside the gate

Both handlers at 1284–1288 and 1295–1299 have the same four-line shape: `wu.log_update("uninstall",
kind=kind, status="failed", at=<where>, error=type(e).__name__)` → `self._info(cp.t("unin_title"),
cp.t("unin_fail"))` → `return`, inside the `try` that precedes the irreversible section, with the `finally`
still releasing the lock. The 28 `wu.log_update(` sites (grep and `ast` agree) use the field names `at bytes
cooldown deleted error kind machine rc reason removed status tag` — no `step`, no `path`, no splat. A direct
probe (`14:34:50Z`, `windows.win_update` imported from the worktree, a temp log) with the two exact call
shapes wrote two lines — `uninstall kind=inno status=failed at=run-uninstaller error=E` and
`uninstall kind=portable status=failed at=run-helper error=E`, neither carrying the temp path — and the old
shape raised `TypeError: log_update() got multiple values for argument 'step'` twice and wrote nothing. The
README's new bullet quotes exactly that line shape, in that field order, and says plainly that only the call
shape is verified on macOS. ✓

### Suites — re-run by the Reviewer from the worktree root

```
$ python3 -m unittest discover -s windows/tests -t . -v                       # 2026-09-13T14:32:54Z
Ran 98 tests in 0.113s
OK                                                # 98 ok, 0 FAIL/ERROR, 0 skipped
$ python3 -W error::ResourceWarning -m unittest discover -s windows/tests -t . -v   # 14:35:28Z
Ran 98 tests in 0.122s
OK                                                # 98 ok, 0 ResourceWarning, no [CLAUDE_PET_WIN_PORT_SOURCE] line
$ python3 -m unittest discover -s tests -v            # started 2026-09-13T14:32:41Z, finished 14:38:14Z (background)
Ran 565 tests in 332.148s
OK (skipped=8)
exit=0                                            # 0 FAIL:/ERROR: headers
```

The 8 skips are the same loud reasons as every earlier run: 3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`,
2 × preflight and 2 × stapler `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`, 1 × "no built bundle at …/dist/ClaudePet.app".
The macOS run reads nothing under `windows/`, and the only file I changed after it started is this record.
`CLAUDE_PET_WIN_PORT_SOURCE` was unset in the environment of every suite run (`env | grep -c` = 0). The
trailing `[update] rejected:` lines are the core's own stderr from the zip-scan gates, as in every round.

### Design points, round 3

- **`CLAUDE_PET_WIN_PORT_SOURCE`** (the Verifier flagged it for me): an override that lets the binding gate
  read a file other than the worktree's port is a way to make one class look green against something it did
  not gate. Three things keep it acceptable: the override prints the path and SHA-256 to stderr on every run,
  so a record of a green run with the variable set names the bytes; it reaches only `_port_source()` —
  `LogUpdateCallShapeTests` and `PortWiringTests` read `ROOT/windows/claude_pet_win.py` directly, and the
  CallShape replay raises the same `TypeError` on a `step=`/`path=` collision, so the collision class stays
  gated on the real port even if the variable is set; and the suite logs quoted above contain no override
  line. Fine as is. Anyone recording a GREEN for this file must quote the absence of that stderr line.
- **README bullet** — accurate against the code (above). It is the only README change; the round-2 N12
  clause was not corrected.

### Non-blocking, carried forward (none gates this merge)

- **N12** (README line 48) still promises that an ARM64 asset uploaded later "will be picked up then";
  `UPDATE_ASSET_NAMES_WIN[("ARM64", *)]` is `()`, so the check returns `no-asset` before reading the asset
  list, and only a new app version with the table extended — a manual install for an ARM64 user — can change
  that. One clause; fix it in the same commit if there is a moment, or leave it for the hardware pass.
- **N13** (`clean_update_leftovers` runs without the lock), **N14** (refusal tokens reach only `update.log`),
  **N15** (unwritable parent discovered after the download), **N16** (confirm box overstates the inno scope),
  and from round 1 **N3**, **N4**, **N6**, **N7**, **N10** — all as recorded there, unchanged.

### Hardware-only verification (for the later Windows pass) — the full H-list, re-stated

Read `%LOCALAPPDATA%\me.yeongyu.claudepet\update.log` (tokens only) and `setup.log` (Inno's; quote status
lines only, it contains install paths). Any `update.log` line carrying a user path is a Privacy defect
regardless of what else passed.

- **H1** `setup.exe /SILENT … /CLOSEAPPLICATIONS` closes the Qt tool window gracefully (Qt quits on
  `WM_ENDSESSION`); `setup.log` shows no forced close, so `/FORCECLOSEAPPLICATIONS` never fires on a healthy pet.
- **H2** `RestartApplications=yes` + `RegisterApplicationRestart("--restart")` relaunches the pet and
  `[Run] … /RELAUNCH=1` plus the mutex leave exactly **one** `ClaudePet.exe`; `update.log` shows
  `check status=update`, `download … status=ok`, `verify … status=ok`, `install … status=launched`.
- **H3** A manual (non-silent) upgrade through the installer UI also relaunches the pet (commit `db1dedc`'s
  promise, never verified).
- **H4** Portable swap end to end: `swap begin pid=…`, `swapped=ok`, `new-app=running`, `old-tree=removed`,
  old folder gone; then an injected launch failure (rename the staged exe before the helper runs) →
  `failed=new-app-not-running rollback=start`, `rollback=ok`, old pet back. Includes the pre-existing
  `.claudepet-old-v<version>` case (see H14).
- **H5** Lock: during the helper's run a second update reports `install status=refused reason=lock-busy`;
  after the helper exits the lock file is gone (`DELETE_ON_CLOSE`) and the next update is **not** `lock-busy`
  — i.e. `Start-Process` did not leak the inherited handle into the new pet.
- **H6** `verify_download` against the live release JSON's `size`/`digest` for both real assets.
- **H7** `install_kind` on a real Inno install (the registry `InstallLocation` value's exact form — trailing
  backslash, case) and on a portable extraction; a source run reports `upd_source`.
- **H8** Uninstall, inno: only `%USERPROFILE%\.claude_pet\` remains; Run value, Start-menu shortcut,
  Add/Remove entry, `{app}` and the cache dir are gone. Uninstall, portable: the folder is removed after exit
  and nothing else is.
- **H9** PowerShell helper under Constrained Language / AppLocker, and AV behaviour on an app-spawned
  `powershell.exe` with `-ExecutionPolicy Bypass`.
- **H10** SmartScreen on the downloaded `setup.exe` (urllib adds no Mark-of-the-Web): the silent install runs
  without a prompt.
- **H11** `platform.machine()` on an ARM64 host running the x64 build (N3) — record as unverified if no such
  machine is available.
- **H12** A user profile with a space and Korean characters end to end: the `-File` path, the `/LOG=` value
  (subprocess quotes the whole token; Inno's parser must still read it as one parameter), and every path
  inside the swap script.
- **H13** `clean_update_leftovers` 60 s after start: removes a planted complete `.claudepet-old-v0.0` tree,
  leaves an unrelated sibling folder, and never races the helper on a live swap.
- **H14** Plant `.claudepet-old-v<current>` beside the app, click "업데이트 확인…" → `install … status=refused
  reason=old-dir-exists` with **no** `download` line before it; delete the folder → the update proceeds. Plant
  it again *while the helper is waiting for the pid* → `swap refused=old-dir-exists`, staging gone, old pet back.
- **H15** Cancel the silent installer (or let it refuse) → within 30 s `install kind=inno status=exited rc=<n>`,
  the "새 버전 vX 설치" item still present, and a second click launches setup again.
- **H16** While setup.exe is running and waiting to close the pet: "완전 삭제…" → `uninstall status=refused
  reason=installing` and the `unin_busy` box; a second "업데이트 확인…" → `install status=refused reason=installing`.
- **H17** Cooldown lines: with the network down `check status=error reason=fetch-failed:… cooldown=0` on every
  30 s refresh; on ARM64 (if available) `reason=no-asset cooldown=1` once an hour.
- **H18** `Rename-Item` under AV: the 40 × 500 ms retry on app→old succeeds after a scanner releases a DLL;
  `failed=app-to-old` + old pet relaunched when it never does.
- **H19** `clean_update_leftovers` at 60 s after a swap does not race the helper's `Remove-Item` of the old
  tree (both delete the same tree; N13's window is the in-flight update case, not this one).
- **H20** `unins000.exe /SILENT` launched while the pet is still alive for a few ms: the uninstall completes
  (Inno's own Restart Manager handling in uninstall mode), no "some elements could not be removed" box, and
  Restart Manager does not try to relaunch a deleted exe.
- **H21** (B4, now fixed — tokens as the port writes them) Block `powershell.exe` (AppLocker, or rename it in a
  VM) and run "완전 삭제…" on a portable install → the `unin_fail` box, one line `uninstall kind=portable
  status=failed at=run-helper error=<ExceptionType>` in `update.log`, nothing deleted, lock released (a second
  "완전 삭제…" is not `lock-busy`). On inno, block `unins000.exe` → the same with `kind=inno … at=run-uninstaller`.
  Only the call shape and the handler text are verified on macOS; the box appearing is hardware-only.

### What remains

Nothing for round 4. The change is ready for the Developer/Verifier trailers and the commit; N12 is the one
sentence I would still correct before it ships, and it is not a gate.

Reviewer's scratch for this round: `rev3/` under the session scratchpad (`prefix/claude_pet_win.py` — my
reconstruction, `red_*.log`, `kb_*.log`, `cs_*.log`, `windows_suite_r3*.log`, `macos_suite_r3.log`).
