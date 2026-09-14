# Track F — hardware fixes F1–F5: Verifier record, RED (2026-09-14)

Role: **Verifier** (`verifier-f`). Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`,
HEAD `f876e40ee8de3e7e80aa5dac8c5cd331b276630d`, tracked tree clean. This record covers the
**red** half of AGENTS.md §3 only: the gating tests exist, they have been run against the
**unfixed** tree, and every failure below is quoted from that run. No production file was opened
for writing.

**Deliverables (AGENTS.md §4).** Exactly two paths, both created by this task and neither
previously existing:

- `windows/tests/test_win_hardware_fixes.py`
- `docs-design/track-f-verification-20260914.md` (this file)

`git status --porcelain` at record time lists one entry, `?? windows/tests/test_win_hardware_fixes.py`
— this record is written after it. Nothing else in the worktree was created, modified or deleted;
`claude_pet.py`, `tests/` and the two existing Windows test modules are untouched (hashes below).

**Roles.** The Developer of F1–F5 owns `windows/win_core.py` (new), `windows/win_update.py`,
`windows/win_autostart.py`, `windows/claude_pet_win.py`, `windows/build_win.py`,
`windows/verify_win_artifact.py`, `windows/installer.iss` and `windows/README.md`. Under §2
Condition A they must not touch an assertion, an expected value or a fixture literal in the gating
file. Under Condition B this Verifier has clean hands on all of them.

---

## 1. Command and result

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s windows/tests -t . -v
…
Ran 179 tests in 0.888s

FAILED (failures=30, errors=3)
```

Run at **2026-09-13T23:19Z** (local 2026-09-14) on macOS 25.5.0, CPython 3.13
(`/Library/Frameworks/Python.framework/Versions/3.13`). 179 tests = 146 from the two existing
Windows modules (unchanged, all green) + 33 new gates, of which **33 are red** and the remainder of
the new file (the instrument probes and the regression pins, listed in §4) are green by design.

### File hashes at the RED run (`shasum -a 256`, 2026-09-13T23:19:49Z)

```
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py
9f3f8fb9d369326c171f369dbfdb18e56224db2659410d91f337fc4e8a0c33cb  windows/win_autostart.py
18accd8109b89f1bc65598b1dd55b969fafa16ab361af363b6cc1a91beb73b34  windows/claude_pet_win.py
63b389ef630cdf782b0b13a61a4ececfa1dc75d0a1dc3685818edc58337c5cfa  windows/build_win.py
b7e0198fa0e850dc8547f08770f1d7d0f179b5eaf5b8fe230ca05c3a063b67ac  windows/verify_win_artifact.py
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss
407fe13d6b55c28a262325d49ad78fce5e22f837547b4857e999c5b5c3a78374  windows/README.md
6542145c7af58746269220b6c6f56da706f4ac4fe1aa0b082ca3c49c42f80a08  windows/compat/fcntl.py
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
63cfe9b99e07da65b6d47fe2b83891a06eb70853e45de967633248f82ae28d28  windows/tests/test_win_update.py
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
```

The gating file's hash must be **unchanged** at the GREEN run. That is what makes Condition A
checkable without trusting anyone's account of it.

### The macOS suite

```
$ python3 -m unittest discover -s tests -v
```

Run from the same clean tree; result recorded in §7. It is **not** green — and it was already not
green at `HEAD~1`, for a reason that has nothing to do with Track F. §7 gives the cause, the git
evidence that it predates this change, and why it is not this Verifier's to fix.

---

## 2. RED — every failure, with its assertion line

Quoted from the run above; grouped by finding, not by class.

### F1 — `win_update` / `verify_win_artifact` / `build_win` cannot import on Windows

```
FAIL: SimulatedWindowsImportTests.test_win_update_imports
AssertionError: 1 != 0 : win_update does not import under a Windows-like environment:
  File "/Users/yeongyu/claude-pet-windows/windows/win_update.py", line 40, in <module>
    import claude_pet as cp  # noqa: E402  — the core; attribute access on purpose …
  File "/Users/yeongyu/claude-pet-windows/claude_pet.py", line 31, in <module>
    import fcntl
ModuleNotFoundError: No module named 'fcntl'

FAIL: SimulatedWindowsImportTests.test_verify_win_artifact_imports
AssertionError: 1 != 0 : verify_win_artifact does not import under a Windows-like environment:
… ModuleNotFoundError: No module named 'fcntl'

FAIL: SimulatedWindowsImportTests.test_build_win_imports
AssertionError: 1 != 0 : build_win does not import under a Windows-like environment:
… ModuleNotFoundError: No module named 'fcntl'

FAIL: OneOwnerForTheCoreImportTests.test_the_helper_module_exists_and_exposes_import_core
AssertionError: False is not true : windows/win_core.py is missing — nothing owns the core import

FAIL: OneOwnerForTheCoreImportTests.test_only_win_core_names_the_core
AssertionError:
- {'claude_pet_win.py': [(78, 'import_module("claude_pet")'),
-                        (92, 'import_module("claude_pet")')],
-  'win_update.py': [(40, 'import claude_pet')]} != {}
  : these modules reach claude_pet without the helper

ERROR: OneOwnerForTheCoreImportTests.test_win_core_actually_imports_the_core
FileNotFoundError: [Errno 2] No such file or directory:
  '/Users/yeongyu/claude-pet-windows/windows/win_core.py'

ERROR: OneOwnerForTheCoreImportTests.test_the_helper_is_a_no_op_on_this_host
ModuleNotFoundError: No module named 'windows.win_core'

ERROR: OneOwnerForTheCoreImportTests.test_every_windows_entry_point_still_imports_here
  (module='windows.win_core')
ModuleNotFoundError: No module named 'windows.win_core'
```

The first three reproduce the hardware's first failure **verbatim and deterministically on macOS**,
at the same line of the same file the Windows session named. The AST gate reports all **three**
call sites, two of which a text search for `import claude_pet` would not find — that is the GREP
rival in the class docstring, and it is not hypothetical: both `importlib.import_module` sites are
real, in `claude_pet_win._import_core`.

### F2 — the Inno uninstall subkey

```
FAIL: InnoUninstallKeyTests.test_the_constant_is_the_key_inno_writes
AssertionError: 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{me.yeongyu.claudepet}_is1'
             != 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{me.yeongyu.claudepet}}_is1'

FAIL: InnoUninstallKeyTests.test_a_real_installed_copy_reads_as_inno
AssertionError: 'portable' != 'inno'

FAIL: InnoUninstallKeyTests.test_every_other_spelling_of_the_key_agrees
AssertionError: {'win_update.py': [(53, 'INNO_UNINSTALL_SUBKEY = …')],
                 'claude_pet_win.py': [(285, '"""HKCU\\…\\Uninstall\\{me.yeongyu.claudepet}_is1 …')],
                 'README.md': [(45, '`HKCU\\…\\Uninstall\\{me.yeongyu.claudepet}_is1\\InstallLocation` …')]} != {}
  : these spell the uninstall key the old way
```

The expected value is **derived in the test from `installer.iss`'s own `AppId`**, not transcribed
from the hardware log, so the constant and the installer cannot drift apart again.

### F3 — the StartupApproved first byte

```
FAIL: StartupApprovedByteRuleTests.test_table (case='re-enabled through the UI (12 zero bytes)')
AssertionError: False is not True
FAIL: StartupApprovedByteRuleTests.test_table (case='04 … (even, extrapolated)')
AssertionError: False is not True
FAIL: StartupApprovedByteRuleTests.test_table (case='one byte 00')
AssertionError: False is not True
FAIL: StartupApprovedByteRuleTests.test_table (case='bytearray 00')
AssertionError: False is not True

FAIL: StartupApprovedByteRuleTests.test_the_whole_range_of_the_first_byte
AssertionError: Lists differ: ['0x0', '0x4', '0x6', '0x8', '0xa', '0xc', … '0xfe'] != []
  : 127 first bytes disagree with the even/odd rule, starting at
    ['0x0', '0x4', '0x6', '0x8', '0xa', '0xc', '0xe', '0x10']

FAIL: AutostartSymptomTests.test_read_state_table
  (run='"C:\\Users\\x\\AppData\\Local\\Programs\\ClaudePet\\ClaudePet.exe"',
   approved=b'\x00'*12, frozen=True)
AssertionError: 'off' != 'on'

FAIL: AutostartSymptomTests.test_one_click_from_the_reported_state_turns_it_off
AssertionError: 'on' != 'off'

FAIL: StartupApprovedByteRuleTests.test_the_docstring_records_which_half_is_observed
AssertionError: False is not true : the docstring must state the even/odd rule

FAIL: StartupApprovedDocTests.test_readme_states_the_even_odd_rule_with_its_provenance
AssertionError: False is not true : README does not state the even/odd rule
```

`test_read_state_table` is the reported symptom itself, end to end: Run value ours,
StartupApproved twelve zero bytes → the menu shows the item unchecked today. The toggle row is its
consequence: the one click that should turn autostart *off* leaves it on.

### F4 — uninstalling while the pet is running

```
FAIL: InstallerClosesTheAppTests.test_there_is_an_uninstall_run_step_that_closes_the_app
AssertionError: [] is not true : installer.iss has no [UninstallRun] section

FAIL: InstallerClosesTheAppTests.test_the_step_runs_before_file_removal_and_tolerates_absence
AssertionError: [] is not true : no [UninstallRun] entry names ClaudePet.exe — nothing to order

FAIL: InstallerClosesTheAppTests.test_the_kill_step_deletes_nothing
AssertionError: [] is not true : no [UninstallRun] entry names ClaudePet.exe — nothing to inspect

FAIL: InstallerClosesTheAppTests.test_a_comment_names_the_mechanism_relied_on
AssertionError: '' is not true : [UninstallRun] carries no comment

FAIL: InAppInnoUninstallOrderTests.test_the_uninstaller_is_not_launched_while_the_app_is_still_running
AssertionError: 1368 not less than 1326 : the uninstaller is launched at line 1326, before the app
  is told to quit at line 1368 — the files are still open

FAIL: InAppInnoUninstallOrderTests.test_a_moment_is_given_for_the_process_to_exit
AssertionError: [] is not true : nothing waits between quit() and the launch; quit() only posts an
  event, so the uninstaller still starts against a live process
```

The last two are the in-app half of H20, read out of the source: `popen_detached(argv)` at
`claude_pet_win.py:1326`, `QApplication.instance().quit()` at `:1368`, and no wait construct
anywhere in `_uninstall`.

### F5 — the exe's version resource

```
FAIL: VersionResourceTests.test_the_fixed_strings_are_present
FAIL: VersionResourceTests.test_the_version_comes_from_the_argument
FAIL: VersionResourceTests.test_the_file_is_a_parseable_pyinstaller_version_resource
AssertionError: False is not true : build_win.write_version_resource(path, version) is missing

FAIL: VersionResourceTests.test_the_build_passes_it_to_pyinstaller_and_derives_the_version
AssertionError: False is not true : build_win never hands the version resource to PyInstaller

FAIL: ArtifactGateKnowsTheVersionResourceTests.test_a_file_without_a_version_resource_is_never_a_silent_pass
FAIL: ArtifactGateKnowsTheVersionResourceTests.test_a_missing_file_never_raises
AssertionError: False is not true : verify_win_artifact.check_version_resource(exe_path) is missing

FAIL: ArtifactGateKnowsTheVersionResourceTests.test_the_gate_actually_calls_it
AssertionError: neither check_all nor check_zip calls check_version_resource
```

---

## 3. Discrimination runs (AGENTS.md §3)

Each fixture was checked against the plausible rivals by computing what each rival returns, not by
reasoning about it. The commands below were run at 2026-09-13T23:1xZ from the worktree root.

### F1 — the simulation is the instrument, so the instrument is tested

The child process supplies **no** work-around. Two probes prove it still reproduces the two
hardware failures, in order; without them a future stdlib change could make every F1 gate green
while testing nothing (the hazard `tests/test_mutation_instruments.py` exists for in the macOS
suite).

```
probe-bare       (import claude_pet, nothing else)
  → ModuleNotFoundError: No module named 'fcntl'                       [hardware failure 1]
probe-path-only  (windows/compat on sys.path, then import)
  → TypeError: LoadLibrary() argument 1 must be str, not None          [hardware failure 2]
scratch probe: compat on sys.path AND CDLL(None) wrapped to raise OSError
  → OK 0.24 None True     (core imported, _RENAMEATX_NP is None, fcntl from windows/compat)
```

| rival | row that kills it |
| --- | --- |
| ONLY-BW — "fix build_win.py, where the report started" | `test_win_update_imports`, `test_verify_win_artifact_imports` |
| PATH-ONLY — "insert `windows/compat` on `sys.path`" | every import row; the probe above shows the TypeError one import later |
| HELPER-UNUSED — "add `win_core.py`, leave the old import" | `test_only_win_core_names_the_core` (3 sites found) and every import row |
| GREP — a text search for `import claude_pet` | misses the two `importlib.import_module` sites at `claude_pet_win.py:78,92` |

The third probe row is why `renameatx_is_none` is asserted in the payload: it is the observable
that separates "the CDLL detour ran" from "the CDLL call was never reached".

### F2 — the hardware's two-spelling experiment, reproduced on macOS

```
AppId          : {{me.yeongyu.claudepet}}
derived key    : {me.yeongyu.claudepet}}_is1
expected subkey: Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
constant       : Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}_is1
equal?         : False
install_kind via the constant : portable
install_kind via the real key : inno
```

Same result the Windows session reported, from the constant and the .iss alone. Rivals: ONE-BRACE
(the shipped constant) and LITERAL (`{{…}}` carried through unchanged, giving three closing
braces) — they tie on the reader rows, which is why row 1 asserts the derived string on its own.

### F3 — the rival table, computed

```
blob          EQ2    TABLE  NE3    NE13   EVEN   shipped  expected
00 x12        False  True   True   True   True   False    True
01+FILETIME   False  False  True   False  False  False    False
02 …          True   True   True   True   True   True     True
03 …          False  False  False  False  False  False    False
04 …          False  False  True   True   True   False    True
05 …          False  False  True   True   False  False    False
```

`EQ2` is the shipped rule and dies on row 1. `TABLE` (`blob[0] in (0x00, 0x02)`) is the four-value
lookup someone writes straight off the hardware report: **it agrees with the correct answer on
every observed byte** and dies only on row 5 (`0x04`). `NE3`/`NE13` die on row 6 (`0x05`). No two
rivals coincide with the expected value on all rows, and rows 5–6 are the discriminating pair no
fixture drawn from `0x00`–`0x03` can supply. `test_the_whole_range_of_the_first_byte` extends the
same check to all 256 first bytes in one assertion (127 disagree today).

End to end: `autostart_read_state(Run=ours, approved=00 ×12)` returns `"off"` today — the reported
symptom.

**§5 note.** `0x00`/`0x01` (and `0x02` on third-party entries) are **observed**, on one machine.
`0x04`/`0x05` are **extrapolation** from the peer's hypothesis (low bit of the first byte), not
observation, and the hypothesis has not been reproduced by a second party. The gates say so, and
`test_the_docstring_records_which_half_is_observed` requires the production docstring to keep the
two apart so a later hardware run can refute the extrapolation without disturbing the observed
half.

### F4 — the ordering, read out of the AST

```
inno-branch calls        : [(1322,'isfile'), (1323,'_info'), (1326,'popen_detached'),
                            (1328,'log_update'), (1329,'_info')]
launches in inno branch  : [(1326,'popen_detached')]
quit/exit in _uninstall  : [(1368,'quit')]
waits in _uninstall      : []
deletes in _uninstall    : [(1353,'rmtree'), (1355,'remove'), (1362,'rmtree')]
prechecks in inno branch : [(1322,'isfile')]
os.getpid() in inno br.  : []
```

Rivals: RM-ONLY ("keep/extend `CloseApplications=yes` + `RestartApplications=yes`") is refused by
construction, because **those two directives were already in `installer.iss` at `f876e40`, the
commit the failure was observed on**, and the uninstall log carried no Restart Manager step; a gate
that accepted them would be satisfied by the tree that failed. POSTUNINST (an `[UninstallRun]`
entry flagged `postuninstall`) runs after file removal and would reproduce the failure while
looking like a fix — that flag is the ordering pin.

One AST subtlety worth recording, because it silently disarmed two gates on the first run: the
`if kind == "inno":` node's `orelse` holds the `elif kind == "portable":` branch, whose helper
*does* call `os.getpid()`. Walking the `If` node whole read the portable branch's PID wait as if
the inno branch had one, and both ordering gates skipped instead of failing. The gate now walks
`node.body` only, and says why.

### F5

No discrimination table applies to an absent function; the rivals named in the class docstring
(HARDCODED, TEMPLATE-ONLY, SILENT-SKIP) are killed by the stub-version row and by the
`problems or stderr` assertion, and become checkable once the Developer lands the two callables.

---

## 4. What in the new file is *not* a gate

Declared so a green result is not over-read (§3: a test that passes before the fix proves nothing —
these are not claimed to prove anything about F1–F5):

| test | why it is green today |
| --- | --- |
| `SimulationInstrumentTests` (2) | instrument pins: they assert the *unfixed* path still fails, and with which exception. |
| `InnoUninstallKeyTests.test_the_derivation_itself` | pins the Inno `{{`-rule the expected value is built from. |
| `InnoUninstallKeyTests.test_a_portable_copy_still_reads_as_portable` | regression pin. |
| `InnoUninstallKeyTests.test_the_inno_uninstall_plan_still_runs_the_uninstaller` | regression pin (the task's "uninstall_plan for the inno kind contains the unins000.exe step"). |
| `PreservedUserFilesTests` (2) | regression pins on the preserved user files. |
| `InAppInnoUninstallOrderTests.test_the_refusable_precheck_still_precedes_every_irreversible_delete` | regression pin **in the opposite direction** — see the caveat below. |
| `OneOwnerForTheCoreImportTests.test_every_windows_entry_point_still_imports_here` | red only because `windows.win_core` is absent; the other four modules import fine today. |

---

## 5. Two things the Developer should read before starting

**(a) F4's ordering gate is in tension with "refusable steps first", deliberately.** The reason
`popen_detached` sits first today is that a `Popen` failure must cost the user nothing — nothing has
been deleted yet. Moving the launch after the quit means a launch failure now happens *after* the
user files are gone. The gate therefore also pins that the `os.path.isfile(unins000.exe)` precheck
stays ahead of the first irreversible delete, so the refusable part of the step does not move with
the launch. If a better shape exists, the second accepted implementation is spelled out in the
class docstring: hand the launch to a helper that waits on `os.getpid()`, the way the portable
branch already does, and the ordering requirement is met differently. The gate detects that and
skips the two ordering assertions.

**(b) `.claude_pet.json` is deleted on purpose by the in-app uninstall.** The task's regression pin
("`%USERPROFILE%\.claude_pet` and `.claude_pet.json` absent from every delete list") is scoped here
to the **installer's** delete sections, which is where the hardware observed them surviving. It is
deliberately *not* applied to `win_update.uninstall_plan`: the in-app "완전 삭제…" deletes the
config in parity with the macOS `UNINSTALL_PATHS`, and a gate that forbade it would break that
parity while looking like a safety improvement. Only the pets directory is off-limits to both, and
that half is asserted for the plan too.

---

## 6. Collisions with the existing Windows test modules

Checked before writing, as §2 Condition A requires the Developer not to resolve such a collision
themselves:

- **No existing *assertion* encodes a fact F1–F4 refutes.** `test_win_autostart.py`'s
  `StartupApprovedTests.test_table` uses only `0x02`, `0x03`, `b""`, `None` and a `str`; every one
  of those rows returns the same value under the even/odd rule, so the table stays green after the
  fix. Its `ReadStateTests`/toggle fixtures use the same two blobs and are likewise unaffected. No
  fixture anywhere uses `0x00`, `0x01`, `0x04` or `0x05`.
- **`ReadmeTests.test_readme_names_the_toggle_and_the_hardware_checks`** requires `0x02` and `0x03`
  to appear in `windows/README.md`. The corrected section still names both bytes (the new gate
  requires `0x00`, `0x01`, `0x02` and `0x03`), so the two gates are compatible. If the Developer
  rewrites that section in a way that drops `0x02`/`0x03`, the *older* test fails — that is a real
  signal, not a collision to route around.
- **What is stale but not asserted:** the class docstrings of `StartupApprovedTests` and
  `ReadStateTests`, and the module docstring of `win_autostart.py`, all describe the refuted
  "`0x02` enabled / `0x03` disabled" encoding as the rule. Docstrings are not gating assertions, so
  no existing test file was edited for this change (`test_win_update.py` and
  `test_win_autostart.py` hashes above are HEAD's). Correcting the two test docstrings is a
  Verifier-owned follow-up once the fix lands and the new file is GREEN; correcting the production
  docstring is the Developer's, and `test_the_docstring_records_which_half_is_observed` gates it.
- **`InstallerScriptTests.test_restart_applications_is_backed_by_a_registration_in_the_port`**
  already requires `RegisterApplicationRestart` in the port whenever `RestartApplications=yes` is
  present. F4's fix must not drop that registration while adding the `[UninstallRun]` step.

---

## 7. macOS suite

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s tests -v
…
Ran 588 tests in 269.195s

FAILED (failures=49, errors=8, skipped=8)
```

**The macOS suite is RED on this branch, and it was red before Track F existed.** Recording it
plainly rather than reporting a green I did not see (§3's `[NEVER]`).

**All 57 failures have one cause**, and it is a hash pin, not a behaviour:

```
ERROR: setUpClass (test_manual_update_transaction.BackupPreservationTests)
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

Distribution: 8 errors in `test_manual_update_transaction` (all `setUpClass`), 48 failures in
`test_upload_artifact_gate` (all its `setUp`, via `assert_reviewed_file`), 1 failure in
`test_v024_release_contract.test_v024_version_and_final_source_pins_propagate`, which exists
precisely to report the same drift for both modules. No other module fails.

**Why it is not this change, established from git rather than asserted:**

- `shasum -a 256 claude_pet.py` in the worktree = `9dd9fb12…` = `git show HEAD:claude_pet.py`. The
  file is HEAD's; `git status --porcelain` reports no modification to it.
- The pinned value `6f95bc8b…` is `claude_pet.py` as it stood from `a1f3d22` ("release: ClaudePet
  v0.24") through `f4130b3` — the last Windows-branch commit before the merge.
- `e098516` ("Merge branch 'main' into windows") brought main's newer `claude_pet.py` (`9dd9fb12…`,
  from `36c2118` "Merge branch 'autostart-fix'") onto this branch **without updating the two
  `REVIEWED_APP_SOURCE_SHA256` constants**. The suite has therefore been red since `e098516`, which
  is `HEAD~1`.
- Track F added one untracked file under `windows/tests/`, which `discover -s tests` never loads,
  and edited nothing else.

**Not fixable by this Verifier, and not by a bump.** Both constants live under `tests/`, which this
task must not touch, and both are guarding a *review*: `test_upload_artifact_gate.py`'s header says
it "refuses to run when any of the three has changed", so re-pinning them without re-reviewing
`release.sh`, `verify_release_artifact.py` and `claude_pet.py` against the harness would convert a
loud refusal into a silent pass — the exact failure mode those pins exist to prevent. It needs an
agent assigned to re-review the harness against the merged `claude_pet.py` and re-pin, and it
blocks §8 item 5 for anything merging off this branch, Track F included.

The 8 skips are the suite's ordinary loud opt-in skips (`CLAUDEPET_RUN_LIVE_UPDATER_TESTS`,
`CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, and one for an absent built bundle). The brief
expected 7; the eighth is `test_v020_boundaries.B2Bundle.test_py2app_bundle_carries_every_asset`,
skipped because `dist/ClaudePet.app` is not built in this worktree. That difference is a property
of the worktree, not of any change.

---

## 8. Status

**RED recorded. Not mergeable and not claimed to be**, and note that §8 item 5 ("the full suite is
green") cannot be satisfied on this branch by anyone until the stale `REVIEWED_APP_SOURCE_SHA256`
pins in §7 are re-reviewed and re-pinned — that is a separate assignment, and it blocks the merge
of Track F even after Track F itself is GREEN. The green half, the Reviewer's sign-off and
the commit trailers (`Developer:` / `Verifier:`, different parties, §7) come after the fix lands.
The gating file's hash must be identical at the GREEN run to the one in §1; if it is not, §2
Condition A was not met and the run does not count.

---

# GREEN (round 1) — 2026-09-14

Same Verifier (`verifier-f`), same worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`,
`git rev-parse HEAD` = `f876e40ee8de3e7e80aa5dac8c5cd331b276630d` (unchanged — the fix is in the
working tree, uncommitted). Run at **2026-09-13T23:46Z–23:51Z** (local 2026-09-14) on macOS
26.5.2, CPython 3.13.7. No production file was opened for writing in this round either; the two
paths this task owns are unchanged from §1's list.

## 9. The gating file is byte-identical to the RED run

```
$ shasum -a 256 windows/tests/test_win_hardware_fixes.py
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
```

Identical to §1. So AGENTS.md §2 Condition A held: the Developer landed the fix without touching an
assertion, an expected value or a fixture literal in the file that judges it. Also unchanged from
§1, and for the same reason (they are not this change's to edit):

```
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
63cfe9b99e07da65b6d47fe2b83891a06eb70853e45de967633248f82ae28d28  windows/tests/test_win_update.py
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
```

Production files as they stood at this run (`shasum -a 256`, 2026-09-13T23:51:30Z) — every one of
them moved, and `win_core.py` is new:

```
a3e323c85093e2cd436730113708e7fadd915764e20934da1a610ddd07e46733  windows/win_core.py          (new)
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
3c26fbffc723ba43f430225cf508dacd1218efbd1ea64d9036f6a2bea3363222  windows/win_autostart.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
9ba6fb64739e390e0ebce047ca15a06bee474cb7f54b641593e4e9a86fbac756  windows/build_win.py
3464a7c943b3fadecab5eb891c7acaa09fdae00e5469ff51d4d3c09069dadd49  windows/verify_win_artifact.py
3d92f68236816e472d0e3866c4a789209d8f0e35a78ee0d603b7d0d01ac52616  windows/installer.iss
069e13cd322021c1ebdc52602d7c8309bc33185e97d96fde52b41e3faf5b55eb  windows/README.md
6542145c7af58746269220b6c6f56da706f4ac4fe1aa0b082ca3c49c42f80a08  windows/compat/fcntl.py       (untouched)
```

`git status --porcelain` at this run — seven modified tracked files, three untracked paths, and
nothing else. The two untracked paths this task owns are §1's declared deliverables; the third
(`windows/win_core.py`) is the Developer's, named in their own deliverable list:

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/win_core.py
```

## 10. The Windows suite — GREEN

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s windows/tests -t . -v
…
----------------------------------------------------------------------
Ran 179 tests in 1.100s

OK (skipped=2)
```

Same 179 tests as the RED run, same three modules
(`test_win_hardware_fixes` 38 + `test_win_update` 98 + `test_win_autostart` 43 = 179, counted from
the verbose output). Every one of the 33 gates that was red in §2 is green, and the two existing
modules stayed green throughout — including
`ReadmeTests.test_readme_names_the_toggle_and_the_hardware_checks` and
`InstallerScriptTests.test_restart_applications_is_backed_by_a_registration_in_the_port`, the two
§6 predicted a rewrite could break.

### The two skips, and why they are not a silent pass

Both are in `InAppInnoUninstallOrderTests`, and both are the **declared alternative branch** of
F4's gate (§5(a) named it in advance, before the Developer started):

```
test_the_uninstaller_is_not_launched_while_the_app_is_still_running … skipped
  'PID-WAIT implementation: os.getpid() is handed to the launched helper'
test_a_moment_is_given_for_the_process_to_exit … skipped
  'PID-WAIT implementation: the helper waits on the pid instead'
```

A skip is not evidence, so the PID-WAIT claim was checked against the source rather than taken from
the skip message. `_uninstall`'s inno branch now writes
`wu.build_inno_uninstall_script(argv, os.getpid())` to a `.ps1` under `%TEMP%` and launches
*that* through `powershell_exe()`; the generated text waits on the pid before it touches the
uninstaller. Exercised directly (2026-09-13T23:50Z, `build_inno_uninstall_script([r"C:\Program
Files\Claude Pet\unins000.exe", "/SILENT"], 4321)`):

```
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id 4321 -Timeout 120 -ErrorAction Stop } catch { }
if (Get-Process -Id 4321 -ErrorAction SilentlyContinue) { exit 2 }
if (Test-Path -LiteralPath 'C:\Program Files\Claude Pet\unins000.exe') {
  try { Start-Process -FilePath 'C:\Program Files\Claude Pet\unins000.exe' -ArgumentList '/SILENT' } catch { exit 3 }
}
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }
exit 0
```

That is line-for-line the shape of the already-shipped `build_uninstall_script` (the portable twin):
same `Wait-Process -Timeout 120` → `Get-Process … exit 2` refusal → guarded action → self-delete.
A path carrying an embedded single quote is doubled, not emitted raw
(`'C:\it''s\unins000.exe'`), so the helper inherits the portable helper's quoting contract too.
The third row of the F4 table — the refusable `os.path.isfile(unins000.exe)` precheck staying ahead
of the first irreversible delete — is **not** skipped and is green.

## 11. The macOS suite — unchanged, and unchanged is *red*

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s tests -v
…
----------------------------------------------------------------------
Ran 588 tests in 272.191s

FAILED (failures=49, errors=8, skipped=8)
```

**Identical to the RED run in §7 — 49 failures, 8 errors, 8 skips, the same 588 tests** — so Track F
changed nothing here in either direction. Distribution, re-counted from this run's output:
8 `setUpClass` errors in `test_manual_update_transaction`, 48 failures in
`test_upload_artifact_gate` (all via `setUp` → `assert_reviewed_file`, `tests/test_upload_artifact_gate.py:74`),
1 in `test_v024_release_contract`. One cause, a stale review pin, not a behaviour:

```
tests/test_manual_update_transaction.py:759, in setUpClass
  AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
    expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
    found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

§7 established from git — not from assertion — that this predates Track F: `claude_pet.py` in this
worktree is byte-identical to `git show HEAD:claude_pet.py`, and the pin went stale at `e098516`
(`HEAD~1`, "Merge branch 'main' into windows"), which brought main's newer core onto this branch
without updating the two `REVIEWED_APP_SOURCE_SHA256` constants. Nothing in this round touched
`claude_pet.py`, `tests/`, or anything those modules read.

**The brief's expectation ("the macOS suite currently passes with 7 loud skips") does not hold in
this worktree, and did not hold before Track F either.** Recorded plainly rather than reported as a
green nobody saw (§3's `[NEVER]`). The 8 skips are the ordinary loud opt-in ones —
3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, 4 × `CLAUDEPET_RUN_LIVE_UPDATER_TESTS`, and
1 for `dist/ClaudePet.app` not being built in this worktree (the eighth; it is a property of the
worktree, not of any change).

## 12. Checks outside the two suites

### (a) `py_compile` on every changed `windows/*.py`

```
$ python3 -m py_compile windows/win_core.py windows/win_update.py windows/win_autostart.py \
      windows/claude_pet_win.py windows/build_win.py windows/verify_win_artifact.py
py_compile OK (6 files)
```

### (b) Every windows module imported under a simulated no-`fcntl` Windows

Run with a **second, independently written instrument** (scratch script, not committed), not the
gating file's child: it blocks `fcntl` with its own meta-path finder unless `windows/compat` is on
`sys.path`, makes `ctypes.CDLL(None)` raise `TypeError` the way Windows does, stubs `msvcrt`,
pre-imports the stdlib the targets pull in and only then sets `sys.platform = "win32"`. The child
supplies no work-around of its own. One `RESULT` line per module, 2026-09-13T23:49Z:

```
win_core            imported=true
win_update          imported=true  core=true app_version=0.24 renameatx_is_none=true fcntl_from_compat=true
win_autostart       imported=true  core=true app_version=0.24 renameatx_is_none=true fcntl_from_compat=true
build_win           imported=true  core=true app_version=0.24 renameatx_is_none=true fcntl_from_compat=true
verify_win_artifact imported=true  core=true app_version=0.24 renameatx_is_none=true fcntl_from_compat=true
claude_pet_win      imported=false ModuleNotFoundError: No module named 'PIL'
                    …core=true app_version=0.24 renameatx_is_none=true fcntl_from_compat=true
```

`claude_pet_win` is the one that does not finish, and the payload says why it does not matter here:
it got **through** `win_core.import_core()` — the core is loaded, the CDLL detour ran
(`_RENAMEATX_NP is None`), `fcntl` resolved to `windows/compat` — and then died at `from PIL import
Image`, a third-party dependency absent on this host. That is an environment limit, not a Windows
detour failure; `PIL`/`PySide6` are unavailable here by construction (the brief: no PyQt/PySide on
this machine).

**The instrument discriminates.** Against the pre-fix files (`git show HEAD:windows/win_update.py`,
`…/verify_win_artifact.py`, `…/build_win.py` copied into a scratch root beside this checkout's
`claude_pet.py` and `windows/compat`), the same script reports:

```
win_update           imported=false  ImportError: No module named 'fcntl'
verify_win_artifact  imported=false  ImportError: No module named 'fcntl'
build_win            imported=false  ImportError: No module named 'fcntl'
```

— the hardware's first failure, reproduced under an instrument that has never seen the gating file.

### (c) The three constants and the two new generators, exercised directly

Not gates — direct observation of the shipped code, recorded so the numbers in §2 have a
counterpart in the fixed tree (2026-09-13T23:50Z):

```
F2  INNO_UNINSTALL_SUBKEY = Software\…\Uninstall\{me.yeongyu.claudepet}}_is1
    installer.iss AppId   = {{me.yeongyu.claudepet}}   → derived {me.yeongyu.claudepet}}_is1
    constant ends with the derived key : True
    a one-brace spelling anywhere else in windows/ : none (grep 'claudepet}_is1')
    the removed constants _STARTUP_APPROVED_ENABLED/_DISABLED : no references left

F3  startup_approved_enabled over all 256 possible first bytes
    disagreements with "even = enabled, odd = disabled" : []      (127 at the RED run)
    guards: None→False  b""→False  "02"→False  bytearray(b"\x00")→True  memoryview(b"\x00")→False
            — nothing raised

F5  build_win.write_version_resource(<tmp>, "0.25") →
      filevers=(0, 25, 0, 0)  prodvers=(0, 25, 0, 0)
      CompanyName 'Yeongyu Yang' · FileDescription 'Claude Pet' · FileVersion '0.25'
      · InternalName 'ClaudePet' · LegalCopyright 'Copyright (c) Yeongyu Yang'
      · OriginalFilename 'ClaudePet.exe' · ProductName 'Claude Pet' · ProductVersion '0.25'
    the version appears only where the argument put it; the file is written into a mkdtemp the
    build removes in a `finally`, so nothing is committed and nothing can go stale.
```

## 13. Findings — two, neither of them a regression

**(i) `build_inno_uninstall_script` is new production code that no test asserts anything about.**
F4's two ordering gates *skip* on the PID-WAIT branch (§10), and the helper text itself is gated by
nothing: `grep build_inno_uninstall_script windows/tests/` finds no hit. Stated with its context so
it is not over-read — `grep build_uninstall_script windows/tests/` finds no hit either, so the new
function sits at exactly the coverage level of the portable twin it was modelled on, and the
residual risks it carries (pid reuse inside the wait window; a pet that takes >120 s to exit, both
ending in `exit 2` with the user files already deleted and the ARP entry still present) are
inherited from that twin rather than introduced here. This is a **gap to assign**, not a defect
found: it is the Verifier-owned follow-up of writing gates for both builders, and it cannot be
closed inside this round without changing the gating file's hash (§9) and losing the Condition A
evidence.

**(ii) §8 item 5 ("the full suite is green") is unsatisfiable on this branch by anyone, Track F
included.** Unchanged from §7/§8: the stale `REVIEWED_APP_SOURCE_SHA256` pins under `tests/` need an
agent assigned to re-review the harness against the merged `claude_pet.py` and re-pin. Re-pinning
without re-reviewing would convert a loud refusal into a silent pass, which is the failure mode those
pins exist to prevent.

Two things checked and **not** found: no stale one-brace spelling of the uninstall subkey survives
anywhere in `windows/` (§12c), and no reference to the two deleted StartupApproved constants
survives.

## 14. Status

**GREEN (round 1) for Track F's gating suite.** `windows/tests` is fully green (179 tests,
`OK (skipped=2)`, both skips the declared PID-WAIT branch, verified against the source rather than
taken from the skip message); the gating file's hash is byte-identical to the RED run, so §2
Condition A held; every one of §2's 33 red gates is now green; `py_compile` and the independent
simulated-Windows import of all six modules pass, and the same instrument still reproduces the
hardware's first failure against the pre-fix files.

**The macOS suite is red and was red before Track F existed** — same 588/49/8/8 as §7, one stale
review-pin cause, established from git. **Not mergeable yet on that account alone** (§8 item 5),
independently of anything Track F did. Still outstanding for merge: the Reviewer's sign-off (an
agent that is neither this Verifier nor the Developer), the commit trailers naming two different
parties (§7), and finding (i) assigned.

---

# GREEN (round 2) — re-run on unchanged bytes, 2026-09-14T00:29Z

Role unchanged: **Verifier** (`verifier-f`). Worktree `/Users/yeongyu/claude-pet-windows`, branch
`windows`, HEAD `f876e40ee8de3e7e80aa5dac8c5cd331b276630d`. **No production file was opened for
writing in this round, and no file at all was written except this record.** Deliverables are the
same two paths declared in §1; nothing was added to that list.

## R2.1 What this round re-runs, and why it is not a second measurement

The Developer reported making no new edits this turn. That is checkable, not a claim to take on
trust, so every file hashed in §9 was re-hashed first:

```
$ shasum -a 256 windows/tests/test_win_hardware_fixes.py claude_pet.py \
    windows/tests/test_win_update.py windows/tests/test_win_autostart.py \
    windows/win_core.py windows/win_update.py windows/win_autostart.py \
    windows/claude_pet_win.py windows/build_win.py windows/verify_win_artifact.py \
    windows/installer.iss windows/README.md windows/compat/fcntl.py
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
63cfe9b99e07da65b6d47fe2b83891a06eb70853e45de967633248f82ae28d28  windows/tests/test_win_update.py
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
a3e323c85093e2cd436730113708e7fadd915764e20934da1a610ddd07e46733  windows/win_core.py
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
3c26fbffc723ba43f430225cf508dacd1218efbd1ea64d9036f6a2bea3363222  windows/win_autostart.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
9ba6fb64739e390e0ebce047ca15a06bee474cb7f54b641593e4e9a86fbac756  windows/build_win.py
3464a7c943b3fadecab5eb891c7acaa09fdae00e5469ff51d4d3c09069dadd49  windows/verify_win_artifact.py
3d92f68236816e472d0e3866c4a789209d8f0e35a78ee0d603b7d0d01ac52616  windows/installer.iss
069e13cd322021c1ebdc52602d7c8309bc33185e97d96fde52b41e3faf5b55eb  windows/README.md
6542145c7af58746269220b6c6f56da706f4ac4fe1aa0b082ca3c49c42f80a08  windows/compat/fcntl.py
```

**Every one is byte-identical to §9.** So this round confirms reproducibility of the round-1 result
on the same bytes; it is **not** independent evidence about a new state of the tree, and nothing
below should be read as such. The gating file's hash also still matches the RED run of §1, so
AGENTS.md §2 Condition A continues to hold.

`git status --porcelain` at this run — the same seven modified tracked files and three untracked
paths as §9, and nothing else:

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/win_core.py
```

## R2.2 `py_compile` on every changed `windows/*.py`

```
$ python3 -m py_compile windows/win_core.py windows/claude_pet_win.py windows/win_update.py \
    windows/win_autostart.py windows/build_win.py windows/verify_win_artifact.py \
    windows/tests/test_win_hardware_fixes.py
PY_COMPILE OK
$ python3 --version
Python 3.13.7
```

## R2.3 The gating file alone

```
$ python3 -m unittest discover -s windows/tests -t . -p 'test_win_hardware_fixes.py' -v
…
Ran 38 tests in 0.831s

OK (skipped=2)
```

The two skips are the declared PID-WAIT branch of `InAppInnoUninstallOrderTests`, and they are the
*same* two as round 1:

```
test_a_moment_is_given_for_the_process_to_exit … skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_uninstaller_is_not_launched_while_the_app_is_still_running … skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'
```

Checked against the source rather than taken from the skip message: `_uninstall`'s `kind == "inno"`
branch writes `wu.build_inno_uninstall_script(argv, os.getpid())` to a `.ps1` and launches it
detached, so the uninstaller is started by a helper that waits on our pid — the PID-WAIT
implementation the gate's docstring names, not an evasion of the ordering assertion. The third test
in that class (`test_the_refusable_precheck_still_precedes_every_irreversible_delete`) does **not**
skip and passes: the `os.path.isfile(argv[0])` refusal still precedes the first `rmtree`/`remove`.

## R2.4 Full Windows suite

```
$ python3 -m unittest discover -s windows/tests -t . -v
…
Ran 179 tests in 1.071s

OK (skipped=2)
```

179 = 98 (`test_win_update.py`) + 43 (`test_win_autostart.py`) + 38 (the gating file), each
module counted separately to confirm the sum rather than asserting it; the two pre-existing modules
are unchanged (hashes in R2.1) and green. Same two skips as R2.3; no other skip, failure or error.

## R2.5 Independent simulated-Windows import of every `windows/*.py`

A probe written for this round (in the session scratchpad, **not** in the repository) reproduces a
Windows import environment and applies **no work-around of its own**: `fcntl` resolves only through
`windows/compat` and otherwise raises `ModuleNotFoundError`, `ctypes.CDLL(None)` raises the
hardware's `TypeError`, `sys.platform` reads `win32`. Anything that imports does so because the
module under test performed both detours itself.

```
$ for m in win_core win_update win_autostart build_win verify_win_artifact claude_pet_win; do \
      python3 <scratchpad>/probe_nofcntl.py /Users/yeongyu/claude-pet-windows $m; done
OK   win_core               core=None APP_VERSION=None renameatx=missing fcntl=None
OK   win_update             core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   win_autostart          core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   build_win              core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   verify_win_artifact    core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
STOPPED AT: No module named 'PIL'
   core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
```

Read these rows carefully, because two of them say something other than "it worked":

- **`win_core` importing the core is not expected.** `import win_core` only makes `import_core()`
  available; it is the *call* that imports the core. `core=None` is the correct answer and is what
  keeps the helper a no-op for a module that merely imports it.
- **`claude_pet_win` stops at `from PIL import Image`**, a genuine third-party dependency absent on
  this macOS host (neither Pillow nor PySide6 is installed here, by the track's own constraint). It
  is **past** `cp = win_core.import_core()` when it stops: the same line reports
  `core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat`, so the two Windows detours both
  ran. Nothing about the Qt half of that module is verified by this probe, and nothing here claims
  otherwise.
- `renameatx=None` on the four core-importing rows is the substantive result: the `CDLL(None)`
  detour actually executed and the core took its own `_RENAMEATX_NP = None` fallback, rather than
  the probe having quietly stopped simulating Windows.

## R2.6 The macOS suite — still red, still for the reason that pre-dates Track F

```
$ python3 -m unittest discover -s tests -v
…
Ran 588 tests in 268.650s

FAILED (failures=49, errors=8, skipped=8)
```

Grouped, every one of the 57 non-green results is in three files:

```
   8 ERROR test_manual_update_transaction     (setUpClass, all six classes)
  48 FAIL  test_upload_artifact_gate
   1 FAIL  test_v024_release_contract
```

and all 57 have **one** cause, quoted from the run:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

**This is a property of commit `f876e40` itself, not of the working tree and not of Track F.**
Established from git objects only, so it does not depend on anything in the checkout:

```
$ git show f876e40:claude_pet.py | shasum -a 256
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
$ git show f876e40:tests/test_upload_artifact_gate.py | grep -o '[0-9a-f]\{64\}'   # REVIEWED_APP_SOURCE_SHA256
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4
```

The pin and the file it pins disagree **at the commit**, before any Track F edit exists. And Track F
modified no pinned path: the pins cover `claude_pet.py`, `build_app.sh`, `release.sh` and
`verify_release_artifact.py`, while `git status --porcelain` (R2.1) lists only files under
`windows/` plus this record. `claude_pet.py` in the worktree hashes identically to
`git show HEAD:claude_pet.py`, i.e. it is untouched.

For completeness: the same stale-pin state exists in the sibling checkout on `main`
(`/Users/yeongyu/claude-pet`), where `claude_pet.py` **and** the two `REVIEWED_APP_SOURCE_SHA256`
constants have both moved together (to `8d0ed11c…`) in an uncommitted working tree belonging to
another track. That is where the "macOS suite is green" expectation comes from; it does not describe
this commit. Nothing was written to that checkout — it was read only.

### R2.6a The rest of the macOS suite, run module by module

To separate "red because of the stale pins" from "red for any other reason", every macOS module
except those three was run individually (`discover -s tests -p '<name>.py'`, which is the only
invocation that works here — `tests/` has no `__init__.py`, per CLAUDE.md):

```
$ for f in tests/test_*.py; do n=$(basename "$f"); case "$n" in \
      test_upload_artifact_gate.py|test_manual_update_transaction.py|test_v024_release_contract.py) continue;; esac
    python3 -m unittest discover -s tests -p "$n" -v; done
…
modules_ok=20  modules_failed=0  tests=504  skipped=8
```

All 20 remaining modules are `OK`; the 8 skips are 4 in `test_updater.py` and 4 in
`test_v020_boundaries.py` — the loud, tool-dependent skips CLAUDE.md describes. So the only red in
the macOS suite is the three pin-blocked modules, and nothing Track F touched is implicated.

**This does not make the release gate satisfiable.** AGENTS.md §8 item 5 requires the *full* suite
green, and it is not. The remedy is unchanged from §14 of round 1: an agent must re-review the
pinned harnesses against the merged `claude_pet.py` and re-pin. Re-pinning without re-reviewing
would turn a loud refusal into a silent pass, which is the exact failure those pins exist to
prevent, and it is not this Verifier's to do.

## R2.7 Findings carried forward, unchanged

- **(i) `win_update.build_inno_uninstall_script` and `build_uninstall_script` have no test of their
  own.** Nothing in `windows/tests` names either builder. This matters more now than in round 1:
  because the inno branch is the PID-WAIT implementation, the two gates in R2.3 skip, so the helper
  text — the `Wait-Process -Id <pid> -Timeout 120`, the `exit 2` refusal when the pet is still
  alive, the `Start-Process` of `unins000.exe` — is pinned by **no** assertion anywhere. A rewrite
  that dropped the wait would keep the whole suite green. Still a **gap to assign**, not a defect
  found; closing it inside this round would change the gating file's hash and destroy the Condition
  A evidence in R2.1.
- **(ii) §8 item 5 is unsatisfiable on this branch by anyone**, per R2.6.

## R2.8 Status

**GREEN (round 2).** On bytes identical to round 1: `windows/tests` fully green
(179 tests, `OK (skipped=2)`, both skips the declared PID-WAIT branch and verified against the
source); the gating file alone green (38 tests, `OK (skipped=2)`); `py_compile` clean on all six
changed modules plus the gating file; and all five Windows entry points import under a simulated
Windows host that supplies no work-around of its own.

**The macOS suite is red, was red at `f876e40` before Track F existed, and its 57 failures have a
single cause that no Track F file is party to** (R2.6). Every macOS module outside the three
pin-blocked ones is green (504 tests, 8 loud skips).

**Not mergeable yet**, on grounds that are not Track F's doing and are unchanged from round 1:
§8 item 5 (full suite green) blocked by the stale review pins; the Reviewer's sign-off outstanding
(an agent that is neither this Verifier nor the Developer); the commit trailers must name two
different parties (§7); and finding (i) needs assigning.

---

# GREEN (post-review 1) — the reviewer's N1–N4, 2026-09-14T01:28Z–01:34Z

Role unchanged: **Verifier** (`verifier-f`). Worktree `/Users/yeongyu/claude-pet-windows`, branch
`windows`, `git rev-parse HEAD` = `f876e40ee8de3e7e80aa5dac8c5cd331b276630d` (the work is still
uncommitted in the tree). Deliverables are the same two paths declared in §1 and nothing was added
to that list; **no production file was opened for writing in this round**, and the only file written
in the repository is this record. The Reviewer's own untracked record
(`docs-design/track-f-review-20260914.md`) appeared since round 2 and was **read only** — it is not
this task's to touch (AGENTS.md §4).

## PR1.1 What moved, and what did not

The Developer reports addressing the review's four non-blocking notes (N1–N4) and nothing else.
Checkable, so every file hashed in R2.1 was re-hashed first (`shasum -a 256`, 2026-09-14T01:28:12Z).
**Five files moved; eight are byte-identical to round 2.**

| path | round 2 (R2.1) | now | |
| --- | --- | --- | --- |
| `windows/tests/test_win_hardware_fixes.py` | `53b3582b…` | `53b3582b…` | **unchanged — §2 Condition A** |
| `claude_pet.py` | `9dd9fb12…` | `9dd9fb12…` | unchanged |
| `windows/tests/test_win_update.py` | `63cfe9b9…` | `63cfe9b9…` | unchanged |
| `windows/tests/test_win_autostart.py` | `a217c549…` | `a217c549…` | unchanged |
| `windows/win_update.py` | `e2de9ad5…` | `e2de9ad5…` | unchanged |
| `windows/win_autostart.py` | `3c26fbff…` | `3c26fbff…` | unchanged |
| `windows/claude_pet_win.py` | `7315a6c6…` | `7315a6c6…` | unchanged |
| `windows/compat/fcntl.py` | `6542145c…` | `6542145c…` | unchanged |
| `windows/win_core.py` | `a3e323c8…` | **`61e08df2…`** | N1 |
| `windows/build_win.py` | `9ba6fb64…` | **`45d1a677…`** | N4 (comment) |
| `windows/verify_win_artifact.py` | `3464a7c9…` | **`912bd9fe…`** | N3 |
| `windows/installer.iss` | `3d92f682…` | **`7b4753a7…`** | N2 (comment) |
| `windows/README.md` | `069e13cd…` | **`45ab79fc…`** | N1/N3/N4 |

Full hashes, in the order above:

```
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
63cfe9b99e07da65b6d47fe2b83891a06eb70853e45de967633248f82ae28d28  windows/tests/test_win_update.py
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
3c26fbffc723ba43f430225cf508dacd1218efbd1ea64d9036f6a2bea3363222  windows/win_autostart.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
6542145c7af58746269220b6c6f56da706f4ac4fe1aa0b082ca3c49c42f80a08  windows/compat/fcntl.py
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  windows/win_core.py
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py
912bd9feb6b9b4e9559358a467889cc8765a1a4495ea3882fe6048808550eb08  windows/verify_win_artifact.py
7b4753a7ef75ffa6aaeca19498824b89688880207521666b78ae8a342b63e1a5  windows/installer.iss
45ab79fc562a9ea57324dc080815168fa9a218ff6883a12f63ea0e272118d273  windows/README.md
```

**Two consequences, and they point in opposite directions.** (a) The gating file is *still* byte-identical
to the RED run of §1, three rounds on, so AGENTS.md §2 Condition A held through the review fix as
well: the Developer changed production code without touching an assertion, an expected value or a
fixture literal in the file that judges it. (b) Unlike round 2, this round is **not** a re-run on
identical bytes — three production modules and two documents moved, so the suite results below are a
new measurement, not a reproducibility check.

`git status --porcelain` at this run — seven modified tracked files and **four** untracked paths, the
fourth being the Reviewer's record:

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-review-20260914.md
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/win_core.py
```

## PR1.2 `py_compile`

```
$ python3 --version
Python 3.13.7
$ python3 -m py_compile windows/win_core.py windows/claude_pet_win.py windows/win_update.py \
    windows/win_autostart.py windows/build_win.py windows/verify_win_artifact.py \
    windows/tests/test_win_hardware_fixes.py
PY_COMPILE OK
```

## PR1.3 The gating file alone

```
$ python3 -m unittest discover -s windows/tests -t . -p 'test_win_hardware_fixes.py' -v
…
Ran 38 tests in 0.857s

OK (skipped=2)
```

Same two skips as rounds 1 and 2, and for the same declared reason — the PID-WAIT branch of
`InAppInnoUninstallOrderTests`:

```
test_a_moment_is_given_for_the_process_to_exit … skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_uninstaller_is_not_launched_while_the_app_is_still_running … skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'
```

Nothing in this round changed `claude_pet_win.py` or `win_update.py` (hashes above), so the branch
those two skip on is the same code R2.3 checked against the source. The third test in that class
(`test_the_refusable_precheck_still_precedes_every_irreversible_delete`) again does not skip and passes.

## PR1.4 Full Windows suite

```
$ python3 -m unittest discover -s windows/tests -t . -v
…
Ran 179 tests in 1.030s

OK (skipped=2)
```

179 = 98 (`test_win_update.py`) + 43 (`test_win_autostart.py`) + 38 (the gating file). Both
pre-existing modules are unchanged bytes (PR1.1) and green; the only two non-ok results in the whole
suite are the two skips above. In particular the three gates that read the two files the Developer
edited are green on the new bytes: `ArtifactGateKnowsTheVersionResourceTests` (all three),
`VersionResourceTests` (all four), and `OneOwnerForTheCoreImportTests` (all four, including
`test_only_win_core_names_the_core`).

## PR1.5 The four notes, checked against the source rather than against the report

A green suite does not show that N1–N4 were *addressed* — none of the four is gated by an assertion
(they were filed as non-blocking nits). Each was therefore re-derived here.

**N1 — the scope of "adds no path" now sits on the call, and the sentence is true of it.** The
docstring reads "`import_core()` adds no path and wraps no builtin … The scope belongs on the call,
not on the file: the *module body* below does insert the repository root into `sys.path`, on every
platform". Measured on this host rather than read (2026-09-14T01:33Z):

```
module body inserted the repo root : True
import_core() changed sys.path     : False   (delta: [])
import_core() changed ctypes.CDLL  : False
windows/compat on sys.path         : False
```

So both halves of the corrected sentence hold: the unconditional insertion is the module body's, and
the call itself adds nothing on macOS. The `win32` branch is unchanged.

**N2 — recorded, not changed, which is what the note asked for.** The `[UninstallRun]` line is
byte-identical to the one quoted in the review (`track-f-review-20260914.md:353`):

```
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ClaudePet.exe /F"; RunOnceId: "CloseClaudePet"; Flags: runhidden skipifdoesntexist
```

Only the comment above it grew: it now states both halves of N2 — that `/IM` is name-matched and why
an installer cannot target a pid, and that `/F` ends the pet without a graceful shutdown — and hands
the second to hardware (H26). The F4 mechanism the review passed is untouched.

**N3 — the gate now reads the builder, and the read fails loudly.** `VERSION_RESOURCE_STRINGS` is
gone; `_version_resource_strings()` reads `build_win.VERSION_STRINGS`. The import is inside the
function, not at module top — which is deliberate and is the right call: a module-level
`import build_win` would change what `SimulatedWindowsImportTests` measures (its child preloads from
each target's *module-level* imports, and the ONLY-BW rival row of that test's table turns on
`verify_win_artifact` not reaching the core through `build_win`). Exercised directly, 2026-09-14T01:36Z:

```
build_win.VERSION_STRINGS      = {'FileDescription': 'Claude Pet', 'CompanyName': 'Yeongyu Yang', 'OriginalFilename': 'ClaudePet.exe'}
_version_resource_strings()    = ('Claude Pet', 'Yeongyu Yang', 'ClaudePet.exe')
hand-copied constant present?   False
module-level build_win import?  False
```

The discriminating run — move the **builder's** value and see whether the gate follows it, which a
hand-copy could not:

```
exe carrying the CURRENT strings        -> []   (+ the loud macOS stderr line)
after build_win.VERSION_STRINGS['CompanyName'] = 'Someone Else Ltd'
                                        -> ["exe has no version resource string 'Someone Else Ltd': ClaudePet.exe …"]
builder made unreadable (RuntimeError)  -> ['cannot read build_win.VERSION_STRINGS (RuntimeError): the gate has no strings to look for in ClaudePet.exe']
a plain MZ file with no resource        -> 4 problems, and stderr not empty
a path that does not exist              -> ['exe missing, cannot check its version resource: ClaudePet.exe']   (no raise)
```

The third line is the one that matters for "not a silent pass": an unreadable builder yields a
*problem*, so a gate with nothing to look for refuses rather than returns `[]`. Both import shapes
resolve the builder — as `windows.verify_win_artifact` (the suite, `-t .` from the root) via
`from . import build_win`, and bare as `verify_win_artifact` (the build's last step and a direct
`python windows\verify_win_artifact.py` run) via `import build_win`; both were run and both returned
the same triple.

**N4 — the provenance sentence no longer names a screen.** `build_win.VERSION_STRINGS`' comment,
`check_version_resource`'s docstring and `windows/README.md` now say that the report reaches only as
far as "설정/작업 관리자" and that **which page it was is not recorded**, state that the fix is the same
either way (startup lists read the exe's `FileDescription`/`CompanyName`; Settings › Apps reads Inno's
ARP values, whose `AppPublisher` is already set), and hand the naming to the next hardware round
(H29, listed in the README's 실기에서 확인할 것). That is the §5 split the note asked for: the
observation keeps its scope, the consequence does not depend on it.

## PR1.6 The three constants and the generator, re-exercised on the new bytes

Not gates — direct observation, recorded because three of the files under them moved
(2026-09-14T01:36Z):

```
F2  installer.iss AppId       = {{me.yeongyu.claudepet}}  → derived  {me.yeongyu.claudepet}}_is1
    win_update.INNO_UNINSTALL_SUBKEY =
        Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
    constant ends with the derived key : True

F3  startup_approved_enabled over all 256 possible first bytes
    disagreements with "even = enabled, odd = disabled" : []
    guards: None→False   b""→False   "02"→False   bytearray(b"\x00")→True   — nothing raised

F5  build_win.write_version_resource(<tmp>, "0.25")
    filevers=(0, 25, 0, 0)   prodvers=(0, 25, 0, 0)
    "0.25" appears twice, "0.24" not at all — the version comes only from the argument
```

## PR1.7 Independent simulated-Windows import, re-run

The same probe as R2.5 (session scratchpad, not in the repository; it supplies **no** work-around of
its own — `fcntl` resolves only through `windows/compat`, `ctypes.CDLL(None)` raises the hardware's
`TypeError`, `sys.platform` reads `win32`). Re-run because `win_core.py`, `build_win.py` and
`verify_win_artifact.py` all moved:

```
OK   win_core               core=None APP_VERSION=None renameatx=missing fcntl=None
OK   win_update             core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   win_autostart          core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   build_win              core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   verify_win_artifact    core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
STOPPED AT: No module named 'PIL'
   core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
```

Identical to R2.5, and read the same way: `win_core`'s `core=None` is correct (importing the module
only makes `import_core()` available; the *call* imports the core), and `claude_pet_win` stops at
`from PIL import Image` — line 77, four lines past `cp = win_core.import_core()` on line 73 — with
the core already loaded, the `CDLL` detour already taken (`renameatx=None`) and `fcntl` resolved to
the compat shim. That is this host lacking Pillow, not a detour failing. Nothing about the Qt half of
that module is verified by this probe.

## PR1.8 The macOS suite — the same red, from the same single cause that pre-dates Track F

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s tests -v
…
Ran 588 tests in 269.593s

FAILED (failures=49, errors=8, skipped=8)
```

Started 2026-09-14T01:28:34Z, ended 01:33:04Z. **The same 588 / 49 / 8 / 8 as §7, §11 and R2.6** —
this round changed it in neither direction, which is what the hashes in PR1.1 predict: nothing under
`tests/` and nothing in `claude_pet.py` moved, and none of the five files that did moved is a path
those pins cover. Grouped, every one of the 57 non-green results is in the same three modules:

```
  48 FAIL  test_upload_artifact_gate          (all via setUp → assert_reviewed_file, tests/test_upload_artifact_gate.py:74)
   8 ERROR test_manual_update_transaction     (setUpClass, all six classes)
   1 FAIL  test_v024_release_contract
```

and all 57 carry the one cause, quoted from this run:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

R2.6 established from git objects alone — not from an assertion — that the pin and the file it pins
already disagree **at commit `f876e40`**, before any Track F edit exists. Nothing in this round
weakens or strengthens that; it is restated here only so this round's red is not read as new.

The 8 skips are the ordinary loud opt-in ones, unchanged:
3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, 2 × the installed-app preflight and 2 × the real
stapler contract (`CLAUDEPET_RUN_LIVE_UPDATER_TESTS`), and 1 for `dist/ClaudePet.app` not being built
in this worktree.

**The brief's expectation ("the macOS suite currently passes with 7 loud skips") still does not hold
in this worktree**, and did not hold before Track F. Recorded plainly rather than reported as a green
nobody saw (AGENTS.md §3's `[NEVER]`).

## PR1.9 Findings

**(i) `win_update.build_inno_uninstall_script` and `build_uninstall_script` still have no test of
their own — unchanged, and it is the review's B2.** Re-checked this round:
`grep -rn "build_inno_uninstall_script\|build_uninstall_script" windows/tests/` returns **0** hits.
Because the inno branch is the PID-WAIT implementation, the two ordering gates skip (PR1.3), so the
helper text — the `Wait-Process -Id <pid> -Timeout 120`, the `exit 2` refusal while the pet is alive,
the `Start-Process` of `unins000.exe` — is pinned by no assertion anywhere, and a rewrite dropping the
wait would keep the whole suite green. The review assigns this to the Verifier, **in a new file** so
the gating file's hash pin survives, with a recorded red run against a scratch copy that drops the
wait. It is not closed by this round and is not closable inside it.

**(ii) AGENTS.md §8 item 5 ("the full suite is green") remains unsatisfiable on this branch by
anyone** — the review's B1, per PR1.8. Not Track F's, and it blocks anything merging off this branch.

**(iii) New, small, and not a regression: N3's single-source property is itself ungated.** No test in
`windows/tests` names `VERSION_STRINGS` or `_version_resource_strings`
(`grep -rn` → 0 hits), so a future edit that re-introduced a hand-copied string table in
`verify_win_artifact.py` would pass all 179 tests. The discrimination that the gate now *reads* the
builder rests on this round's probe (PR1.5), recorded above rather than pinned by an assertion.
Stated with its context so it is not over-read: the pre-N3 hand-copy was ungated in exactly the same
way — N3 removed a drift risk and added no coverage — so this is a **gap to assign**, naturally
alongside (i), not a defect found. Closing it inside this round would change the gating file's hash
and destroy the Condition A evidence in PR1.1.

## PR1.10 Status

**GREEN (post-review 1).** On bytes that moved in five files since round 2: the gating file alone is
green (38 tests, `OK (skipped=2)`); the full Windows suite is green (179 tests, `OK (skipped=2)`, both
skips the declared PID-WAIT branch); `py_compile` is clean on all six changed modules plus the gating
file; all five Windows entry points still import under a simulated Windows host that supplies no
work-around of its own; and the gating file is byte-identical to the RED run of §1 for the third
round running, so AGENTS.md §2 Condition A held through the review fix.

**All four non-blocking notes were addressed, and each was re-derived here rather than taken from the
report** (PR1.5): N1's scope correction is measured true on this host; N2 is recorded in a comment with
the directive unchanged from the reviewed line; N3's gate reads `build_win.VERSION_STRINGS` under both
import shapes and turns an unreadable builder into a problem rather than a silent pass, with the
drift run to discriminate it; N4's provenance sentence no longer names a screen and hands the naming
to H29. **No gating assertion, fixture or expected value was touched** by the Developer or by this
Verifier.

**The macOS suite is red, identically to rounds 1 and 2, for a cause that exists at `f876e40` and
that no Track F file is party to** (PR1.8).

**Not mergeable yet**, on grounds unchanged and none of them this round's doing: B1/(ii) — §8 item 5
blocked by the stale review pins; B2/(i) — the two uninstall-script builders need a gate in a new
file, with a recorded red run; the Reviewer's re-sign-off after this fix (an agent that is neither
this Verifier nor the Developer); and the commit trailers must name two different parties (§7).
Finding (iii) to be assigned with (i).

---

## PR2.1 What moved, and what did not

The Developer reports one change this round: the `[UninstallRun]` comment in
`windows/installer.iss`, the Developer's half of the review's **B3** (R2.9 item 2) — text only, no
mechanism change. Checkable, so every file hashed in PR1.1 was re-hashed first
(`shasum -a 256`, 2026-09-14T02:03:36Z). **Two files moved; eleven are byte-identical to
post-review 1.**

| path | post-review 1 (PR1.1) | now | |
| --- | --- | --- | --- |
| `windows/tests/test_win_hardware_fixes.py` | `53b3582b…` | `53b3582b…` | **unchanged — §2 Condition A, fourth round** |
| `claude_pet.py` | `9dd9fb12…` | `9dd9fb12…` | unchanged |
| `windows/tests/test_win_update.py` | `63cfe9b9…` | `63cfe9b9…` | unchanged |
| `windows/tests/test_win_autostart.py` | `a217c549…` | `a217c549…` | unchanged |
| `windows/win_update.py` | `e2de9ad5…` | `e2de9ad5…` | unchanged |
| `windows/win_autostart.py` | `3c26fbff…` | `3c26fbff…` | unchanged |
| `windows/claude_pet_win.py` | `7315a6c6…` | `7315a6c6…` | unchanged |
| `windows/compat/fcntl.py` | `6542145c…` | `6542145c…` | unchanged |
| `windows/win_core.py` | `61e08df2…` | `61e08df2…` | unchanged |
| `windows/build_win.py` | `45d1a677…` | `45d1a677…` | unchanged |
| `windows/verify_win_artifact.py` | `912bd9fe…` | `912bd9fe…` | unchanged |
| `windows/installer.iss` | `7b4753a7…` | **`8d51b49f…`** | B3 (comment) |
| `windows/README.md` | `45ab79fc…` | **`2e9f2b67…`** | B3 (prose) |

Full hashes for the two that moved:

```
8d51b49fb0e1bbd62ddf2c9da823e21c7ed0cc7157500a6da8407f1314ef65ac  windows/installer.iss
2e9f2b67f01e35e08454c1092edf8879eb2409bf4cb873ae98b03636dba5aecc  windows/README.md
```

**Two things follow, and one of them is a correction to the report.** (a) **No `.py` file moved at
all**, so "no mechanism change" is not a claim to be taken on trust in the Python half — it is
settled by the hashes, and every behavioural result below is therefore a reproducibility check on
PR1's bytes rather than a new measurement. (b) **`windows/README.md` moved as well**, which the
Developer's report did not name. It is in scope — R2.9 item 2 assigns the Developer *both* shipped
texts, `installer.iss` **and** `windows/README.md` — so this is a report that under-states what it
did, not an out-of-scope edit. Recorded because the report and the tree disagreed about which paths
were touched, and the tree is the authority.

`git status --porcelain` at this run — the same seven modified tracked files and four untracked
paths as PR1.1, and nothing else:

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-review-20260914.md
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/win_core.py
```

## PR2.2 "Text only" — checked against the file, not against the report

`installer.iss`'s `[UninstallRun]` section now holds **27 comment lines and exactly one directive**,
and that directive is byte-identical to the entry the review quoted at
`track-f-review-20260914.md:353` before this round:

```
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ClaudePet.exe /F"; RunOnceId: "CloseClaudePet"; Flags: runhidden skipifdoesntexist
```

Every non-comment, non-blank line of the whole file was listed and read (`grep -vE '^\s*;|^\s*$'`):
`[Setup]` through `[Code]` is what R2.5 described, `CloseApplications=yes` / `RestartApplications=yes`
are still there, and `[UninstallDelete]` still names only `{app}\_internal\claudepet-release.json`,
`{app}\_internal`, `{app}\{#MyAppExeName}` and `{localappdata}\me.yeongyu.claudepet`. **Nothing under
`%USERPROFILE%` appears in any delete section** — the single occurrence of `USERPROFILE` in the file
is in the pre-existing `[UninstallDelete]` comment naming what is *preserved*. So F4's guarantee
about `%USERPROFILE%\.claude_pet` and `.claude_pet.json` is untouched, and
`PreservedUserFilesTests` (green, PR2.5) pins it independently of this reading.

A comment that lost its leading `;` would have surfaced here as a second directive line. It did not.

## PR2.3 The corrected text, checked against the primary source rather than against the review

B3 is a claim about what Inno Setup's documentation says, so taking the fix from the review's
quotation would verify nothing. The two pages were fetched independently
(between 2026-09-14T02:05Z and 02:12Z; `jrsoftware.org/ishelp/topic_runsection.htm` and
`topic_scriptevents.htm`, plus Microsoft's `taskkill` command reference at
`learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill`).

| claim now shipped in `installer.iss` / `README.md` | status |
| --- | --- |
| "The [UninstallRun] section … specifies any number of programs to execute as the first step of *uninstallation*." | **verbatim on the page** |
| "By default, when processing a [Run]/[UninstallRun] entry, Setup/Uninstall will wait until the program has terminated before proceeding to the next one, unless the nowait, shellexec, or waituntilidle flags are used." | **verbatim on the page** — and note it is *closer* to the source than R2.5's own paraphrase of the same sentence, so the difference in wording from the review is the fix being right, not drifting |
| the 19-value `Flags` list quoted in the comment | **all 19, in the page's order**; checked mechanically, none missing, none invented |
| `postuninstall` is not one of them | **confirmed**: the page carries no such flag |
| "post-uninstall" is `[Code]`'s `CurUninstallStepChanged` / `usPostUninstall`, not a `[UninstallRun]` flag | **confirmed**: `topic_scriptevents.htm` documents `CurUninstallStepChanged(CurUninstallStep: TUninstallStep)` with values `usAppMutexCheck, usUninstall, usPostUninstall, usDone` |
| `skipifdoesntexist` requires `Filename` to be an absolute path, and `{sys}\taskkill.exe` is one | **confirmed**: "When this flag is used, Filename must be an absolute path." (still unpinned by a test — the review's N6) |
| `waituntilterminated` is the default | **confirmed**: "this is the default behavior (i.e. you don't need to specify this flag) unless you're using shellexec flag" |

So the ordering guarantee is now stated unconditionally and sourced, the three flags that can
actually defeat it are named in both texts, and the refuted sentence is called out as wrong in both
rather than silently deleted. **The Developer's half of B3 is done**, in both files R2.9 item 2
names. Two claims in the same comment are **not** covered by any of this — see N7 below.

## PR2.4 py_compile, the constants, and the simulated-Windows import — reproducibility

No `.py` moved, so these re-runs confirm reproducibility on identical bytes; they are not new
evidence, and nothing below should be read as such.

```
$ python3 -m py_compile windows/{win_core,win_update,win_autostart,claude_pet_win,build_win,verify_win_artifact}.py \
    windows/tests/test_win_hardware_fixes.py
py_compile OK
```

The three constants, re-derived (2026-09-14T02:04Z) — F2's derivation reads `installer.iss`, which
*did* move, so this one is a fresh measurement:

```
F2  installer.iss AppId       = {{me.yeongyu.claudepet}}  → derived  {me.yeongyu.claudepet}}_is1
    win_update.INNO_UNINSTALL_SUBKEY ends with the derived key : True
F3  startup_approved_enabled over all 256 first bytes
    disagreements with "even = enabled, odd = disabled" : []
    guards: None→False   b""→False   "02"→False   bytearray(b"\x00")→True   — nothing raised
F5  write_version_resource(<tmp>/ver.txt, "0.25")
    filevers=(0, 25, 0, 0)  prodvers=(0, 25, 0, 0)   "0.25" ×2, "0.24" ×0
```

The independent simulated-Windows import probe (Verifier's own, in the session scratchpad, not in
the repository; it supplies no work-around of its own — `fcntl` resolves only through
`windows/compat`, `ctypes.CDLL(None)` raises the hardware's `TypeError`, `sys.platform` reads
`win32`, and `msvcrt` is a stub because the compat shim imports it):

```
OK   win_core               core=None APP_VERSION=None renameatx=missing fcntl=None
OK   win_update             core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   win_autostart          core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   build_win              core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
OK   verify_win_artifact    core=claude_pet APP_VERSION=0.24 renameatx=None fcntl=compat
STOPPED AT: claude_pet_win  ModuleNotFoundError: No module named 'PIL'
```

Identical to PR1.7 and R2.5, and read the same way: `claude_pet_win` stops at `from PIL import
Image` with the core already loaded and both detours already taken — this host lacking Pillow, not a
detour failing. Nothing about the Qt half of that module is verified by this probe.

## PR2.5 Suites

**Gating file alone — green.** `python3 -m unittest discover -s windows/tests -t . -p
'test_win_hardware_fixes.py' -v`, 2026-09-14T02:04:53Z:

```
Ran 38 tests in 0.793s

OK (skipped=2)
```

**Full Windows suite — green.** `python3 -m unittest discover -s windows/tests -t . -v`,
2026-09-14T02:04:57Z, Python 3.13.7, Darwin 25.5.0, from the worktree root:

```
Ran 179 tests in 1.071s

OK (skipped=2)
```

The two skips are B2's declared pair, unchanged and quoted from this run:

```
test_a_moment_is_given_for_the_process_to_exit … skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_uninstaller_is_not_launched_while_the_app_is_still_running … skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'
```

No other skip, failure or error. `InstallerClosesTheAppTests` — the five gates that read
`installer.iss` directly, including `test_a_comment_names_the_mechanism_relied_on` — is green on the
rewritten comment, and `PreservedUserFilesTests` is green on the unchanged delete sections.

**macOS suite — red, identically to rounds 1, 2 and post-review 1, for a cause that exists at
`f876e40` before Track F.** `python3 -m unittest discover -s tests -v`, started
2026-09-14T02:05:07Z, ended 02:09:37Z:

```
Ran 588 tests in 269.730s

FAILED (failures=49, errors=8, skipped=8)
```

The same 588 / 49 / 8 / 8, and grouped from this run's own output the same three modules:

```
  48 FAIL  test_upload_artifact_gate          (all via setUp → assert_reviewed_file; three setUp sites)
   8 ERROR test_manual_update_transaction     (setUpClass, all six classes)
   1 FAIL  test_v024_release_contract         (test_v024_version_and_final_source_pins_propagate)
```

48 + 8 + 1 = 57, and all 57 carry one cause. One of them — the `v024` contract test — names both
stale pins explicitly rather than tripping over one, quoted from this run:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61

AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b…,
  final claude_pet.py is 9dd9fb12…', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins
  6f95bc8b…, final claude_pet.py is 9dd9fb12…'] is not false
```

R2.6 established from git objects alone that the pin and the file it pins already disagree **at
`f876e40`**. Nothing this round weakens or strengthens that; the hashes in PR2.1 predict exactly
this result, since nothing under `tests/` and nothing in `claude_pet.py` moved and neither file that
did is a path those pins cover. The 8 skips are the ordinary loud opt-in ones, unchanged
(3 × `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, 2 + 2 × `CLAUDEPET_RUN_LIVE_UPDATER_TESTS`, and 1
for `dist/ClaudePet.app` not being built in this worktree).

**The brief's expectation ("the macOS suite currently passes with 7 loud skips") still does not hold
in this worktree**, and did not hold before Track F. Recorded plainly rather than reported as a green
nobody saw (AGENTS.md §3's `[NEVER]`).

## PR2.6 Findings

**(i) B2 — unchanged, still open.** `grep -rn "build_inno_uninstall_script\|build_uninstall_script"
windows/tests/` returns **0** hits. `win_update.py` is byte-identical to PR1, so this is the same
gap in the same state: the inno branch is the PID-WAIT implementation, the two ordering gates skip,
and the helper text — the `Wait-Process -Id <pid> -Timeout 120`, the `exit 2` refusal while the pet
is alive, the `Start-Process` of `unins000.exe` — is pinned by no assertion anywhere. Verifier-owned,
in a **new** file, with a recorded red run against a scratch copy that drops the wait.

**(ii) B3's assertion half is still open, and the false Inno fact now survives in a third place that
the Developer could not reach.** The two *shipped* texts are corrected (PR2.3). The gating file's
`InstallerClosesTheAppTests` docstring still presents **POSTUNINST** as a rival it rules out and
still says "That flag is the ordering pin", and
`assertNotIn("postuninstall", flags, …)` still cannot fail, because no `installer.iss` that ISCC will
compile can carry a flag Inno does not define. That text is now **inconsistent with the file it
judges**. It is deliberately left alone: correcting it in place would move
`test_win_hardware_fixes.py` and destroy the Condition A evidence that has held for four rounds, which
is why R2.9 item 1 puts the replacement — `assertNotIn` on each of `nowait`, `shellexec`,
`waituntilidle`, plus N6's absolute-path pin — in a new file. **Until that file exists, nothing in the
suite would catch `Flags: runhidden skipifdoesntexist nowait`**, which re-creates H20 in one word.

**(iii) N7 (new, non-blocking) — two sentences in the corrected comment are still unsourced, and one
of them disagrees with the README's own wording.** `installer.iss` now reads "펫이 떠 있지 않으면
taskkill 이 **128** 을 돌려주지만 Inno 는 **종료 코드를 보지 않고**". Neither half is covered by the
citations the rest of the block carries:

- `topic_runsection.htm` **never mentions exit codes, error codes or result codes** for
  `[Run]`/`[UninstallRun]` (checked explicitly this round). "Inno does not look at the exit code" is
  an inference from the absence of documented handling, not a documented fact.
- Microsoft's `taskkill` command reference **documents no return codes at all**, so the specific
  value `128` has no vendor source, and it was not among the values the hardware session reported.
- `windows/README.md`, corrected in the same round, states the same thing as "0 이 아닌 값" — the
  claim that is actually supported. **The two shipped texts now differ in precision on the one
  sentence in the block that has no citation.**

Nothing behavioural hangs on it: the entry is correct whatever `taskkill` returns, because
`skipifdoesntexist` covers the missing-tool case and the exit code is not consulted by anything we
control. It is recorded because it is the same *class* of defect B3 was — a written-down fact with no
source sitting in the comment a future maintainer reads first — and the cheap fix is to soften
`installer.iss` to the README's wording or cite a source for `128`. Whether `128` predates this round
is **not determinable from an uncommitted tree**; R2.5's paraphrase of the same sentence read
"non-zero", which suggests it is new, and that is as far as the evidence goes.

**(iv) N5 — unchanged and still to assign** (`VERSION_STRINGS` / `_version_resource_strings` have 0
hits in `windows/tests/`), naturally alongside (i) and (ii) in the same new file.

**(v) B1 — unchanged, and not Track F's.** AGENTS.md §8 item 5 ("the full suite is green") remains
unsatisfiable on this branch by anyone until the two `REVIEWED_APP_SOURCE_SHA256` constants under
`tests/` are re-reviewed and re-pinned against the merged `claude_pet.py`.

## PR2.7 Status

**GREEN (post-review 2).** On the two files that moved since post-review 1: the Developer's half of
**B3 is done in both texts R2.9 item 2 names** — `windows/installer.iss` and `windows/README.md` —
and every documentation claim in them was re-derived here from the primary sources rather than taken
from the review (PR2.3). The change is **text only**, settled by hash rather than by report: no `.py`
file moved, the `[UninstallRun]` section holds one directive and it is byte-identical to the reviewed
entry, and the delete sections are untouched, so F4's mechanism and its `%USERPROFILE%` guarantee are
exactly what they were. The gating file alone is green (38 tests, `OK (skipped=2)`); the full Windows
suite is green (179 tests, `OK (skipped=2)`, both skips the declared PID-WAIT branch); `py_compile` is
clean; all five Windows entry points still import under a simulated Windows host that supplies no
work-around of its own; and the gating file is byte-identical to the RED run of §1 for the **fourth**
round running, so AGENTS.md §2 Condition A held again. **No gating assertion, fixture or expected
value was touched** by the Developer or by this Verifier.

**The macOS suite is red, identically to all previous rounds, for a cause that exists at `f876e40`
and that no Track F file is party to** (PR2.5).

**Not mergeable yet**, on grounds unchanged and none of them this round's doing: **B1** — §8 item 5
blocked by the stale review pins; **B2** — the two uninstall-script builders still have no gate;
**B3's assertion half** — `nowait`/`shellexec`/`waituntilidle` are still pinned by nothing, and the
gating file's docstring still carries the refuted framing that only the new file can correct; the
Reviewer's re-sign-off after this fix (an agent that is neither this Verifier nor the Developer); and
the commit trailers must name two different parties (§7). **N5 and the new N7 to be assigned with
B2/B3.**

---

# CLOSING ROUND — B2/B3

*verifier-f2 (VERIFIER), 2026-09-14T02:19Z–02:25Z. Worktree `/Users/yeongyu/claude-pet-windows`,
branch `windows`, HEAD `f876e40` with the uncommitted Track F change. No git write command was run;
no untracked file this round did not create was modified.*

## CR.0 What this round closes, and what it does not touch

Two carried blocking items from `track-f-review-20260914.md` §R2.9, plus the two non-blocking notes
that R2.9 item 2 folds into the same file:

| item | status after this round |
| --- | --- |
| **B2** — the two uninstall-helper builders are gated by nothing, and the in-app ordering coverage skips itself | **closed** — CR.2(a), CR.2(b), CR.3, CR.5 |
| **B3 (second half)** — retire the vacuous `postuninstall` assertion, pin `nowait` / `shellexec` / `waituntilidle` | **closed** — CR.2(c), CR.4, CR.5 |
| **N5** — the `VERSION_STRINGS` single-source property is ungated | **closed** — CR.2(d), CR.5 |
| **N6** — `skipifdoesntexist`'s absolute-`Filename` condition is unpinned | **closed** — CR.2(c) |
| **N7** — two unsourced sentences in the `installer.iss` comment (`128`, "Inno 는 종료 코드를 보지 않고") | **still open, untouched.** It is a comment-text/citation matter in a Developer-owned file; nothing in this round's file gates it and nothing in this round should be read as closing it. |
| **B1** — the two stale `REVIEWED_APP_SOURCE_SHA256` pins under the repo-root `tests/` | **still open, and not Track F's.** Unchanged. |

**Deliverable:** one new file, `windows/tests/test_win_uninstall_contract.py` (38 tests). Nothing else
in the worktree was written to. In particular `windows/tests/test_win_hardware_fixes.py` is
**byte-identical to the hash this record has pinned in four previous rounds**:

```
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
```

— which is why the two tests CR.3 shows to be vacuous are **superseded rather than deleted**. They
still run, and they still skip; the new file re-states their obligation without a skip and closes the
hole the skip left. Anyone merging this should read CR.3 before deciding whether to keep them.

## CR.1 Environment, and every hash this round rests on

```
$ python3 -VV
Python 3.13.7 (v3.13.7:bcee1c32211, Aug 14 2025, 19:10:51) [Clang 16.0.0 (clang-1600.0.26.6)]
$ uname -srm
Darwin 25.5.0 arm64
$ git rev-parse --short HEAD
f876e40
```

Worktree files under test, `shasum -a 256`, taken 2026-09-14T02:24:49Z — the same bytes for every RED
run and for the GREEN run below:

```
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
8d51b49fb0e1bbd62ddf2c9da823e21c7ed0cc7157500a6da8407f1314ef65ac  windows/installer.iss
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  windows/win_core.py
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
3791adc9a364069e1beb84ca6d3ec1bdcb0829118e91ea05162643c04b7f1c3f  windows/tests/test_win_uninstall_contract.py   ← new
```

The new file's hash was taken **after** the last rival run and again after the final green run and is
the same value both times, so no assertion was adjusted between red and green (AGENTS.md §3).

The thirteen scratch rivals, under
`…/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/rivals/` — outside the worktree, never on a git
path:

```
b61ac99c5e7a8c63615130419b2c52bf18909d6dd4c7ca9b12aab6ed5ef8d50a  R1/windows/win_update.py
807fa0462e5cbe7b4b679baf3032666146c35f1594914c571edcc7e05981945b  R2/windows/win_update.py
0197713fea99cd09938483346a30250105c461fdd81d6e89fa0d64ecc418405a  R3/windows/win_update.py
a937921dcaed4d8c73ee367a324eb406f81c98eaa5fdd1e3b898fbad7f4da8e8  R4/windows/win_update.py
9bba02461eaadca1e70a31b03b8254d6bf707e90178e3130a3f9c21f3ea815bf  R5/windows/build_win.py
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  R5/windows/win_core.py     (unmutated copy)
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  R5/windows/win_update.py   (unmutated copy)
73ef49adc7eb2352f2eb206de1563a6057d7db1d472b7fff4845b8485bbe2783  P1/windows/claude_pet_win.py
af7626fb815850105cad961f6051f81fa2f5adc1575ae3f1290e627e99fadeac  P2/windows/claude_pet_win.py
ecdfa89d5f85a17170ebc8bf8b10668bf6859ac1bba2b394fcc22ef61d3d1c2b  P3/windows/claude_pet_win.py
5b46c83b36aabfca2282a3bebf0d697f6b18e3617985b90afd7a94bf85875f85  I1/windows/installer.iss
7f2c8a9749ccf597a66e12993b4a0a12ccf6b5c2fafefdedaf437ea9475fbc7d  I2/windows/installer.iss
067ad4c0021fca67ca548aa68818455bca9ce78c9044a708ad3986de9ca833ba  I3/windows/installer.iss
c8868163a3b372b94331d28db14aa186e98987daa809e0492f3882444d669b4b  I4/windows/installer.iss
b8a0f3e1e796d4fbc624c6b381a9c614037defdf8371baf2806a35245d9ef9e3  I5/windows/installer.iss
```

The two unmutated copies in `R5/` are there because `build_win.py` puts its own directory on
`sys.path` and imports `win_core` / `win_update` bare; without them the R5 run would have died on
`ModuleNotFoundError: No module named 'win_core'` and a **collection error would have been recorded
as a discrimination it is not**. It did, on the first attempt, and was fixed before anything was
written down — noted because that is exactly the failure mode a rival run hides.

### The rival seam, and the two instruments that keep a rival run honest

The assertions must run against wrong implementations, and neither `win_update.py` nor
`claude_pet_win.py` nor `installer.iss` may be edited to produce them. So every source the new file
reads — module or text — goes through `_src()` / `_wu()` / `_bw()`, which consult
`CLAUDE_PET_WIN_RIVAL_ROOT`: a scratch mirror carrying one broken copy. `windows` is a namespace
package, so a mirror at the front of `sys.path` supplies `windows.win_update` while everything it
does not carry still resolves from the worktree.

The variable is **unset in the suite**. `python3 -m unittest discover -s windows/tests -t .` takes no
branch on it, so the suite gates the working tree unconditionally. Two instruments:

- setting it prints a two-line banner to **stderr** (`*** RIVAL RUN — … ***`), so a rival run cannot
  be mistaken for a real one in a transcript;
- `_mirrored()` **raises** when the mirror holds a file and the thing actually loaded came from the
  worktree. Without it, a mirror that silently failed to take effect would produce 38 green tests and
  be recorded as a discrimination. This is the same hazard `tests/test_mutation_instruments.py`
  guards for the updater, in a different costume.

The rival builder asserts the occurrence count of every `str.replace` needle before replacing
(`sub(text, old, new, expect, what)`); `str.replace` cannot fail, so a reworded source would
otherwise have produced a rival byte-identical to the tree.

## CR.2 What the new file asserts

38 tests in four classes. Every class docstring carries its own AGENTS.md §3 truth table, with the
ties marked as ties rather than counted as evidence.

### (a) `InnoUninstallHelperTextTests` (9) and `PortableUninstallHelperTextTests` (8)

`win_update.build_inno_uninstall_script(argv, pid)` and `build_uninstall_script(app_dir, pid)` are
called directly with synthetic values — `pid = 424242`, and paths carrying a distinctive token
(`C:\ZZFIXTUREZZ Files\…`) and, in a second fixture, an apostrophe (`C:\Apps\Claude's Pet\…`). The
contract is asserted as an **order over every machine-touching PowerShell verb**, not over the one
call each builder happens to make:

```
nothing in {Start-Process, Remove-Item, Rename-Item, Stop-Process, Move-Item, New-Item,
            Copy-Item, Expand-Archive}
  → Wait-Process -Id <our pid> with a positive -Timeout
    → a Get-Process check on the same pid that exits non-zero (and, separately, exactly 2)
      → the builder's own irreversible act (launch / folder removal)
```

Stating it over the whole verb set is deliberate: an assertion written only about `Start-Process`
would pass a rewrite that moved a `Remove-Item` ahead of the wait.

Quoting is pinned twice, because one check alone is defeatable: `ps_quote(item) in text` for every
interpolated value, **and** the distinctive token must not survive in
`_outside_quotes(text)` — the script with every single-quoted span blanked, i.e. what PowerShell would
parse as code. A separate fixture pins that an embedded `'` is **doubled** (`Claude''s`) and not
backslash-escaped, which is a shell idiom PowerShell does not have.

### (b) `InAppInnoUninstallOrderTests` (9) — no self-skip

`claude_pet_win.py` is parsed with `ast` and only the `kind == "inno"` **branch body** is read (not
the whole `If`: its `orelse` carries the portable branch, whose helper already waits, so walking the
node entire reads the portable branch's wait as if it were the inno branch's). Asserted, with no
predicate that can excuse any of it:

1. the branch calls `build_inno_uninstall_script` **exactly once**;
2. one of that call's arguments is a `Call` to **`getpid`** — the pid is followed to its destination,
   not merely observed somewhere in the branch (CR.3 is why this distinction is the whole finding);
3. no launch call's source segment mentions `argv` — the uninstaller is never started directly;
4. the launched path is the same local name the helper text was written to;
5. the `os.path.isfile` precheck precedes both the helper build and the first irreversible delete;
6. every `rmtree` / `remove` / `unlink` in `_uninstall` comes **after** the launch;
7. `quit()` comes after every delete;
8. **the file contains no `skipTest` / `skip` / `skipIf` / `skipUnless` call at all** — checked over
   its own AST, so the docstring may quote the superseded predicate without defeating the check.

Points 2 and (a) together are what actually close B2: "the pid was handed over" and "the helper waits
on that pid" are now two assertions that fail separately, instead of one assumption.

### (c) `InstallerUninstallRunTests` (7) — and N6

`installer.iss` is parsed into sections; the `[UninstallRun]` entry is split on `;` outside double
quotes into `Filename` / `Parameters` / `RunOnceId` / `Flags`. Asserted:

- exactly one `[UninstallRun]` entry, `Filename` = `{sys}\taskkill.exe`, parameters `/IM ClaudePet.exe`
  and `/F`, and **no `/T`** (the in-app "완전 삭제…" makes the uninstaller a child of the pet, so `/T`
  would cut its own branch);
- **none of `nowait`, `shellexec`, `waituntilidle`** appears in `Flags` — the three flags Inno
  documents as removing the `waituntilterminated` default;
- an allow-list assertion on the *whole* flag set, so a fourth flag nobody has considered fails loudly
  rather than passing because it is not one of the three;
- **N6** — `skipifdoesntexist` is present, and `Filename` is absolute: either `X:\…` or a `{constant}`
  from the list of Inno constants that expand to an absolute path. `{sys}` is one;
- `[Code]` contains no `DeleteFile` / `DelTree` / `RemoveDir` / `DelayDeleteFile` /
  `CurUninstallStepChanged`. Inno documents the order of its own sections and documents nothing about
  where a `[Code]` deletion lands relative to `[UninstallRun]`, so a deletion there is an ordering
  this file could no longer state;
- `CloseApplications=yes` / `RestartApplications=yes` are pinned as **present and explicitly not
  credited** with the ordering — F4's finding is that both were already set when the files survived.

One assertion is labelled in its own docstring as a readability pin rather than a mechanism:
`[UninstallRun]` appearing before `[UninstallDelete]` in the file. Inno's execution order comes from
the sections' definitions, not their position, and the test says so, so the next reader is not invited
to infer the opposite.

### (d) `VersionResourceSingleSourceTests` (5) — N5

`build_win.write_version_resource(path, "9.87")` is called with `build_win.VERSION_STRINGS`
**monkey-patched to a sentinel table**, and the emitted resource must carry the sentinels and must
**not** carry the real strings. That is the only way to test derivation: the existing gate
(`test_win_hardware_fixes.VersionResourceTests`) keeps its own hard-coded copy of the expected strings
in `FIXED_STRINGS`, so it agrees with a generator that hard-codes them too, and shares the fault it is
meant to catch. Four further assertions pin that `FileVersion` / `ProductVersion` / `filevers` /
`prodvers` all come from the *argument*, that `FileVersion` is not in the fixed table (it would freeze
at the committed value), and that a second call rewrites the file.

*Naming note:* the review's `_version_resource_strings` does not exist in `windows/build_win.py`. The
symbols are `VERSION_STRINGS` (the table) and `write_version_resource(path, version)` (the generator);
the property is the same and this record uses the real names.

## CR.3 Why the superseded predicate was vacuous — the measurement

The Reviewer's claim was that
`test_win_hardware_fixes.InAppInnoUninstallOrderTests._pid_wait()` is "satisfied by any implementation
that hands `os.getpid()` to a helper, including one that never waits". Reproduced here, and it is
worse than that. The predicate, verbatim:

```python
def _pid_wait(self):
    return any(name == "getpid" for _ln, name, _n in self._branch_calls())
```

Applied to three sources (scratch script, AST only, 2026-09-14T02:22Z):

```
working tree         _pid_wait() = True   (os.getpid() at lines [1309, 1312])  -> old gate SKIPS
P1 pid->literal 0    _pid_wait() = True   (os.getpid() at lines [1309])        -> old gate SKIPS
P3 no precheck       _pid_wait() = True   (os.getpid() at lines [1306, 1309])  -> old gate SKIPS
```

**Rival P1 is the case that settles it.** P1 changes exactly one call —
`wu.build_inno_uninstall_script(argv, os.getpid())` → `…(argv, 0)` — so the generated helper waits on
**pid 0**, not on the pet, and the race the whole finding is about is back in full. `_pid_wait()`
still returns `True`, because `os.getpid()` survives at line 1309 in the *helper's file name*
(`f"claudepet-uninstall-inno-{os.getpid()}.ps1"`). The old gate skips; the new gate fails:

```
FAIL: InAppInnoUninstallOrderTests.test_the_pid_handed_to_the_helper_is_this_process
AssertionError: [] is not true : build_inno_uninstall_script is not called with os.getpid(); the
helper would wait on something other than the process holding the files open.
args=["Name(id='argv', ctx=Load())", 'Constant(value=0)']
```

And the superseded class, run against the working tree as it stands:

```
$ python3 -m unittest windows.tests.test_win_hardware_fixes.InAppInnoUninstallOrderTests -v
test_a_moment_is_given_for_the_process_to_exit ... skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_refusable_precheck_still_precedes_every_irreversible_delete ... ok
test_the_uninstaller_is_not_launched_while_the_app_is_still_running ... skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'

Ran 3 tests in 0.032s

OK (skipped=2)
```

Two of the three tests report a *declared implementation choice* and run nothing, and the skip message
asserts as fact ("the helper waits on the pid") the very thing nothing checked: before this round,
`grep -rln 'build_inno_uninstall_script\|build_uninstall_script' windows/tests/` returned **no file**
(re-run this round, 0 hits before, 1 after — `windows/tests/test_win_uninstall_contract.py`). The skip
message was the only place in the repository where the helper's wait was asserted, and a skip message
is not an assertion.

**Operational consequence, separately from the observation above:** the two skips remain in the suite
(`OK (skipped=2)`, CR.6) because the file is hash-pinned and may not be edited. They are now
redundant, not load-bearing. Whoever is assigned that file next should delete the predicate and the
two skips, and this section is the evidence for doing so.

## CR.4 Retiring `assertNotIn("postuninstall", flags)`

**Retired, and not replaced by a weaker version of itself.** `postuninstall` is absent from the Flags
list that Inno Setup 6 documents for `[Run]` / `[UninstallRun]`
(https://jrsoftware.org/ishelp/topic_runsection.htm — the Developer verified this in round 2 and the
list is quoted in `installer.iss`'s own comment). A flag Inno does not define cannot appear in a
`.iss` that `ISCC` compiles, so no implementation this suite could be handed would ever fail that
assertion. Under AGENTS.md §3 it is not a weak test; it is a test of nothing, and it is dangerous
precisely because it is green in the final state.

What replaces it is the set of flags that **can** break the entry, each of which Inno documents as
removing the wait: `nowait`, `shellexec`, `waituntilidle`. The failure they produce is invisible in
the one artifact a maintainer would check — the uninstall log's step order is unchanged, only the
waiting disappears — which is why it has to be an assertion and not a review item. Rivals I1–I3 in
CR.5 are exactly those three, and each fails two assertions.

## CR.5 RED — rival by rival, verbatim assertion lines

Each run is `CLAUDE_PET_WIN_RIVAL_ROOT=<rival> python3 -m unittest
windows.tests.test_win_uninstall_contract`, from the worktree root, 2026-09-14T02:24Z. The class name
is folded into the test name for width; nothing else is edited, and long value dumps are cut at 230
columns (marked by the line ending mid-string). The stderr rival banner is omitted from each block.

**R1 — no `Wait-Process` at all** (all three occurrences removed from `win_update.py`; only the two in
the uninstall builders are read by any assertion here, so the discrimination is attributable to them
alone):

```
FAIL: InnoUninstallHelperTextTests.test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: InnoUninstallHelperTextTests.test_it_waits_on_the_apps_pid_with_a_bounded_timeout
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: InnoUninstallHelperTextTests.test_nothing_touches_the_machine_before_the_wait
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: InnoUninstallHelperTextTests.test_the_refusal_uses_the_documented_exit_code_two
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: InnoUninstallHelperTextTests.test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: PortableUninstallHelperTextTests.test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: PortableUninstallHelperTextTests.test_it_waits_on_the_apps_pid_with_a_bounded_timeout
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: PortableUninstallHelperTextTests.test_nothing_touches_the_machine_before_the_wait
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: PortableUninstallHelperTextTests.test_the_app_folder_is_removed_only_after_the_wait_and_the_refusal
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
FAIL: PortableUninstallHelperTextTests.test_the_refusal_uses_the_documented_exit_code_two
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
Ran 38 tests in 0.152s
FAILED (failures=10)
```

**R2 — `Wait-Process` kept, the still-alive refusal dropped.** This is the rival the wait assertion
alone cannot catch, and the reason the refusal has its own two tests: a 120-second `Wait-Process` that
times out returns normally, so without the `Get-Process` check a hung pet is indistinguishable from an
exited one.

```
FAIL: InnoUninstallHelperTextTests.test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
FAIL: InnoUninstallHelperTextTests.test_the_refusal_uses_the_documented_exit_code_two
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
FAIL: InnoUninstallHelperTextTests.test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
FAIL: PortableUninstallHelperTextTests.test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
FAIL: PortableUninstallHelperTextTests.test_the_app_folder_is_removed_only_after_the_wait_and_the_refusal
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
FAIL: PortableUninstallHelperTextTests.test_the_refusal_uses_the_documented_exit_code_two
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
Ran 38 tests in 0.151s
FAILED (failures=6)
```

**R3 — the uninstaller is launched before the wait** (the `Test-Path` + `Start-Process` block moved
above `Wait-Process` in the inno builder). Note that this rival keeps the wait *and* the refusal, so
it is caught only by the ordering assertions:

```
FAIL: InnoUninstallHelperTextTests.test_nothing_touches_the_machine_before_the_wait
AssertionError: Lists differ: [] != [(3, "  try { Start-Process -FilePath 'C:\[106 chars] }")]
FAIL: InnoUninstallHelperTextTests.test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal
AssertionError: 5 not less than 3 : 'Start-Process' is at line 3, before the wait at line 5
Ran 38 tests in 0.146s
FAILED (failures=2)
```

**R4 — an unquoted path** (`exe_q = q(items[0])` → `exe_q = items[0]` in the inno builder;
`{q(app_dir)}` → `{app_dir}` in the portable builder's `Remove-Item`):

```
FAIL: InnoUninstallHelperTextTests.test_an_apostrophe_in_the_path_is_doubled_not_escaped
AssertionError: "Claude''s Pet" not found in "# ClaudePet inno uninstall helper — generated by windows/win_update.py.\n$ErrorActionPreference = 'Stop'\ntry { Wait-Process -Id 424242 -Timeout 120 -ErrorAction Stop } catch { }\nif (
FAIL: InnoUninstallHelperTextTests.test_every_interpolated_argument_is_single_quoted
AssertionError: "'C:\\ZZFIXTUREZZ Files\\ClaudePet\\unins000.exe'" not found in "# ClaudePet inno uninstall helper — generated by windows/win_update.py.\n$ErrorActionPreference = 'Stop'\ntry { Wait-Process -Id 424242 -Timeout 120
FAIL: InnoUninstallHelperTextTests.test_no_interpolated_path_reaches_the_script_as_bare_code
AssertionError: 'ZZFIXTUREZZ' unexpectedly found in "# ClaudePet inno uninstall helper — generated by windows/win_update.py.\n$ErrorActionPreference = ''\ntry { Wait-Process -Id 424242 -Timeout 120 -ErrorAction Stop } catch { }\ni
FAIL: PortableUninstallHelperTextTests.test_it_removes_nothing_unless_the_folder_still_carries_our_exe_and_marker
AssertionError: -1 not greater than or equal to 0
FAIL: PortableUninstallHelperTextTests.test_no_interpolated_path_reaches_the_script_as_bare_code
AssertionError: 'ZZFIXTUREZZ' unexpectedly found in "# ClaudePet portable uninstall helper — generated by windows/win_update.py.\n$ErrorActionPreference = ''\ntry { Wait-Process -Id 424242 -Timeout 120 -ErrorAction Stop } catch {
FAIL: PortableUninstallHelperTextTests.test_the_folder_it_removes_is_the_one_it_was_given
AssertionError: "Remove-Item -LiteralPath 'C:\\ZZFIXTUREZZ Files\\ClaudePet'" not found in "# ClaudePet portable uninstall helper — generated by windows/win_update.py.\n$ErrorActionPreference = 'Stop'\ntry { Wait-Process -Id 42424
Ran 38 tests in 0.149s
FAILED (failures=6)
```

**R5 — the version resource stops reading `VERSION_STRINGS`** (`strings = dict(VERSION_STRINGS)`
replaced by a literal table with today's values). Exactly one test fails, and it is the derivation
one — the other four in that class tie with the tree by construction and are marked as ties in the
class docstring:

```
FAIL: VersionResourceSingleSourceTests.test_the_emitted_table_follows_a_mutated_VERSION_STRINGS
AssertionError: "StringStruct('CompanyName', 'ZZ-Rival-Company')" not found in "# ClaudePet Windows version resource — generated by windows/build_win.py. Do not edit or commit.\nVSVersionInfo(\n  ffi=FixedFileInfo(\n    filevers=(
Ran 38 tests in 0.145s
FAILED (failures=1)
```

**P1 — the helper is handed a literal instead of this process's pid** (see CR.3; the old gate skips
here):

```
FAIL: InAppInnoUninstallOrderTests.test_the_pid_handed_to_the_helper_is_this_process
AssertionError: [] is not true : build_inno_uninstall_script is not called with os.getpid(); the helper would wait on something other than the process holding the files open. args=["Name(id='argv', ctx=Load())", 'Constant(value=0)
Ran 38 tests in 0.147s
FAILED (failures=1)
```

**P2 — the uninstaller `argv` is launched directly, no helper** (H20's original shape):

```
FAIL: InAppInnoUninstallOrderTests.test_the_branch_builds_its_helper_from_win_update
AssertionError: 1 != 0 : the inno branch must build its helper text exactly once; found []
FAIL: InAppInnoUninstallOrderTests.test_the_branch_launches_the_helper_and_not_the_uninstaller
AssertionError: 'argv' unexpectedly found in 'popen_detached(argv)' : line 1313 launches the uninstaller argv directly, while this process is still running and holding ClaudePet.exe and _internal\ open: popen_detached(argv)
FAIL: InAppInnoUninstallOrderTests.test_the_launched_file_is_the_one_the_helper_text_was_written_to
AssertionError: False is not true : the launch does not reference the file the helper text was written to; written=['script'] launched='popen_detached(argv)'
FAIL: InAppInnoUninstallOrderTests.test_the_pid_handed_to_the_helper_is_this_process
AssertionError: 1 != 0 : the inno branch must build its helper text exactly once; found []
FAIL: InAppInnoUninstallOrderTests.test_the_refusable_precheck_precedes_the_helper_and_every_delete
AssertionError: 1 != 0 : the inno branch must build its helper text exactly once; found []
Ran 38 tests in 0.166s
FAILED (failures=5)
```

**P3 — the refusable `unins000.exe` precheck removed** (the regression pin in the other direction: a
step that can fail must stay ahead of the first irreversible delete):

```
FAIL: InAppInnoUninstallOrderTests.test_the_refusable_precheck_precedes_the_helper_and_every_delete
AssertionError: [] is not true : the inno branch no longer checks that unins000.exe is there
Ran 38 tests in 0.144s
FAILED (failures=1)
```

**I1 / I2 / I3 — each of the three flags that removes Inno's documented wait**, appended to the live
entry's `Flags: runhidden skipifdoesntexist`. Each fails the targeted assertion *and* the allow-list
assertion, independently:

```
── I1 (nowait) ──
FAIL: InstallerUninstallRunTests.test_no_flag_removes_inno_s_documented_wait
AssertionError: Lists differ: [] != ['nowait']
FAIL: InstallerUninstallRunTests.test_the_entry_is_flagged_only_in_ways_that_keep_the_wait
AssertionError: Lists differ: [] != ['nowait']
Ran 38 tests in 0.147s
FAILED (failures=2)

── I2 (shellexec) ──
FAIL: InstallerUninstallRunTests.test_no_flag_removes_inno_s_documented_wait
AssertionError: Lists differ: [] != ['shellexec']
FAIL: InstallerUninstallRunTests.test_the_entry_is_flagged_only_in_ways_that_keep_the_wait
AssertionError: Lists differ: [] != ['shellexec']
Ran 38 tests in 0.148s
FAILED (failures=2)

── I3 (waituntilidle) ──
FAIL: InstallerUninstallRunTests.test_no_flag_removes_inno_s_documented_wait
AssertionError: Lists differ: [] != ['waituntilidle']
FAIL: InstallerUninstallRunTests.test_the_entry_is_flagged_only_in_ways_that_keep_the_wait
AssertionError: Lists differ: [] != ['waituntilidle']
Ran 38 tests in 0.150s
FAILED (failures=2)
```

**I4 — a relative `Filename` under `skipifdoesntexist`** (N6's rival):

```
FAIL: InstallerUninstallRunTests.test_the_entry_kills_the_pet_with_taskkill
AssertionError: '{sys}\\taskkill.exe' != 'taskkill.exe'
FAIL: InstallerUninstallRunTests.test_the_filename_is_absolute_as_skipifdoesntexist_requires
AssertionError: False is not true : skipifdoesntexist requires an absolute Filename; 'taskkill.exe' is not one, so the flag's behaviour is undefined for this entry
Ran 38 tests in 0.145s
FAILED (failures=2)
```

**I5 — a `[Code]` deletion whose order relative to `[UninstallRun]` Inno does not document**:

```
FAIL: InstallerUninstallRunTests.test_nothing_in_code_can_delete_a_file_ahead_of_the_kill_step
AssertionError: Lists differ: [] != ['DeleteFile', 'CurUninstallStepChanged']
Ran 38 tests in 0.161s
FAILED (failures=1)
```

**Every rival failed at least one assertion; thirteen of thirteen.** No rival passed, and no rival
failed only on an import or collection error.

## CR.6 GREEN — the working tree

The gating file alone, 2026-09-14T02:25:16Z, no `CLAUDE_PET_WIN_RIVAL_ROOT` in the environment:

```
$ python3 -m unittest windows.tests.test_win_uninstall_contract
----------------------------------------------------------------------
Ran 38 tests in 0.161s

OK
```

No skips — that is the point of the class in CR.2(b), and `test_this_file_never_skips_itself` keeps it
that way.

The full Windows suite, from the worktree root, 2026-09-14T02:25:18Z:

```
$ python3 -m unittest discover -s windows/tests -t .
Ran 217 tests in 1.111s

OK (skipped=2)
```

**217 = 179 (previous rounds) + 38 (this file).** The two skips are unchanged and are exactly the two
CR.3 dissects, in the hash-pinned `test_win_hardware_fixes.py`; no test in the new file skips. Also
run: `python3 -m py_compile windows/tests/test_win_uninstall_contract.py` — clean.

`grep -rln 'build_inno_uninstall_script\|build_uninstall_script' windows/tests/` now returns
`windows/tests/test_win_uninstall_contract.py`, where before this round it returned nothing.

The macOS suite was **not** re-run and is unchanged from PR2.5: still red, for the B1 cause that
pre-dates Track F and that no file in this round is party to. Nothing this round touched can move it.

## CR.7 What this file does **not** gate — read before trusting it

Stated so the next reader does not mistake 38 green tests for more coverage than they are:

- **Nothing here executes PowerShell, `ISCC`, Inno, PyInstaller or a PE parser**, none of which exists
  on this host. The helper scripts are gated as *text*; that `powershell.exe` interprets that text the
  way the assertions assume is a separate claim and remains hardware-only (H22, H26, H27). In
  particular, **that `ISCC` rejects an unknown `Flags` value was not executed**, exactly as the
  Reviewer noted in R2.10; the allow-list assertion in CR.2(c) rests on the documented flag list, not
  on compiler behaviour.
- **`build_swap_script` is not gated by this file.** R1 removed its wait too, but no assertion here
  reads it, so its wait remains covered only by whatever `test_win_update.py` already does.
- **`_uninstall` is read structurally, never run.** Qt is not importable here. An ordering that is
  correct in the AST and wrong at runtime — a callback, a deferred send — would pass.
- **N7 is untouched** (CR.0). It is a citation defect in a comment, and no assertion in this file
  bears on it.
- The `[UninstallRun]`-before-`[UninstallDelete]` assertion is a **readability** pin and says so in
  its own docstring; Inno's ordering comes from the section definitions.

## CR.8 Findings

1. **(blocking, closed) B2.** The gate now exists and is discriminating: R1–R4 and P1–P3 each fail it.
   The specific hole the Reviewer identified — a helper handed `os.getpid()` that never waits — is
   caught by P1, which the superseded predicate skips (CR.3).
2. **(blocking, closed) B3 second half.** `nowait` / `shellexec` / `waituntilidle` are pinned, each
   demonstrated failing (I1–I3); the vacuous `postuninstall` assertion is retired with its reason
   recorded (CR.4) and deliberately **not** replaced by a variant of itself.
3. **(non-blocking, closed) N5, N6.** Both pinned, both with a failing rival (R5, I4).
4. **(new, non-blocking) N8 — the two superseded skips are now dead weight and should be deleted by
   whoever is next assigned `test_win_hardware_fixes.py`.** They cannot be removed here: the file is
   hash-pinned in this record and the Verifier may not edit it. Until then the suite will keep
   reporting `OK (skipped=2)`, and a reader who does not have CR.3 in front of them will reasonably
   read that as a declared implementation choice rather than as a retired gate. The evidence for the
   deletion is CR.3; the risk of leaving it is only cosmetic, because the obligation is now asserted
   elsewhere.
5. **(new, non-blocking) N9 — the rival seam is a permanent, if narrow, surface.**
   `CLAUDE_PET_WIN_RIVAL_ROOT` lets any process point this file's assertions at a different tree. It
   is unset in the suite, announces itself on stderr, and fails closed when the mirror does not take
   effect, so it cannot silently weaken a normal run; but it is one environment variable, and anyone
   reviewing this file should satisfy themselves that the default path takes no branch on it. The
   alternative — copying the whole worktree per rival — was rejected as slower and no safer.

## CR.9 Status

**GREEN.** The working tree passes the new gating file (38 tests, `OK`, no skips) and the full Windows
suite (217 tests, `OK (skipped=2)`, both skips pre-existing and now redundant). **All thirteen rivals
failed**, each on the assertion it was built to fail and none on a collection error. B2, B3's
assertion half, N5 and N6 are closed; N7, N8, N9 are recorded as non-blocking; **B1 is unchanged and
still blocks merge**, and is not Track F's to close.

AGENTS.md §2 Condition A held: this Verifier authored the new gating file and edited no production
file. Condition B held: the set of files this Verifier wrote is `{windows/tests/test_win_uninstall_contract.py}`,
disjoint from every production file of this change. No git write command was run, and no untracked
file this round did not create was modified — `windows/tests/test_win_hardware_fixes.py` still hashes
to `53b3582b…`, `diag.py` and the two `release/` user-owned paths were never touched.

---

# CLOSING ROUND — B4

**Verifier:** verifier-f2. **Worktree:** `/Users/yeongyu/claude-pet-windows`, branch `windows`,
HEAD `f876e40`, Track F change uncommitted. **Window:** 2026-09-14T03:06:27Z – 2026-09-14T03:12Z,
all timestamps UTC, all commands run from the worktree root. **No git write command was run in this
round.** Files this round changed: `windows/tests/test_win_uninstall_contract.py` and
`windows/tests/test_win_hardware_fixes.py` — both authored by this Verifier — and this record. No
production file was touched (hashes in B4.7 prove it), and `diag.py`, `release/ClaudePet.iconset/`
and `release/icon_1024.png` were never read or written.

## B4.0 What the closing Reviewer found, and what this round does about it

Quoted from the closing review (CR-R.4):

> the helper-text gate in `windows/tests/test_win_uninstall_contract.py` cannot tell PowerShell code
> from a PowerShell comment. `_wait_index()` takes the first line containing the substring
> `Wait-Process` anywhere, and `_refusal()` scans for `Get-Process -Id <pid>` and then `exit <n>` the
> same way, so a generated helper whose wait (rival MR6) or whose still-alive refusal (rival MR8) is
> COMMENTED OUT passes all 38 tests.

That is the AGENTS.md §3 collapse in its plainest form, and it collapses on exactly the sentence B2
was raised about: a rewrite that drops the wait keeps the whole suite green, which is H20's race
reported as `OK`.

**Remedy, as the Reviewer validated it:** add a code-vs-comment helper and route the five text scans
through it. Implemented here, then both rivals rebuilt from scratch and recorded red.

## B4.1 The change to the gating file

`windows/tests/test_win_uninstall_contract.py`, Verifier-owned. One new module-level helper beside
`_outside_quotes`:

```python
def _ps_code(line):
    """One line of the generated helper, reduced to what PowerShell would
    actually **execute**: any trailing ``#`` comment removed.
    ...
    """
    masked = _PS_STRING.sub(lambda m: " " * len(m.group(0)), line)
    i = masked.find("#")
    return line[:i] if i >= 0 else line
```

Routed through it, exactly the five sites the Reviewer named:

| site | before | after |
| --- | --- | --- |
| `_first(lines, needle, start)` | `if needle in lines[i]` | `if needle in _ps_code(lines[i])` |
| `assert_waits_on_our_pid` | `line = lines[i]` | `line = _ps_code(lines[i])` |
| `assert_nothing_happens_before_the_wait` | `_outside_quotes(ln)` | `_outside_quotes(_ps_code(ln))` |
| `_refusal` — the `Get-Process` scan | `"Get-Process" in lines[n] and re.search(…, lines[n])` | same two tests against `code = _ps_code(lines[n])` |
| `_refusal` — the `exit` blob | `"\n".join(lines[j:j + 8])` | `"\n".join(_ps_code(ln) for ln in lines[j:j + 8])` |
| `assert_action_comes_after_the_refusal` | `_outside_quotes(ln)` | `_outside_quotes(_ps_code(ln))` |

The name is `_ps_code`, **not** `_code`: `assert_action_comes_after_the_refusal` already binds a
local `_code` from `self._refusal(text)`, and shadowing it raises
`TypeError: 'int' object is not callable`. The Reviewer hit that first and said so; it was not
re-discovered here, it was avoided.

Docstrings updated in the same file so the record is in the code and not only here: `_HelperTextMixin`
states that every scan reads `_ps_code(line)`, and both §3 truth tables gain the two rivals as
columns (`R6 wait commented`, `R8 refusal commented`) with the cells each one loses.

### One deliberate deviation from the Reviewer's literal snippet, and the evidence it changes nothing

The review's snippet blanks quoted spans with `_PS_STRING.sub("''", line)` and then slices the
**original** line at the `#` found in the **shortened** copy. Those two strings have different
lengths, so the slice index is left-shifted by however much the quoting removed, and a line that
quotes a path *before* its comment gets live code cut off. This version masks each quoted span with
the same number of spaces instead, so the index refers to the real line. The intent — "blank quoted
spans, then drop any trailing `#` comment" — is the Reviewer's, unchanged.

Measured, rather than asserted (`…/scratchpad/ver-f2-b4/ps_code_variants.py`, 2026-09-14T03:11Z).
Grouping key: one line of generated helper text. File set: the six helper texts this gate reads —
`build_inno_uninstall_script` and `build_uninstall_script` from the working tree, from `MR6` and from
`MR8`, on the fixtures `argv = [EXE_SPACE, "/SILENT", "/SUPPRESSMSGBOXES"]` / `app_dir = DIR_SPACE`,
`pid = 424242`:

```
lines compared: 63 ; lines where the two variants differ: 0
synthetic line: "Start-Process -FilePath 'C:\\Program Files\\ClaudePet\\unins000.exe' # note"
  literal: "Start-Process -FilePath 'C:"
  shipped: "Start-Process -FilePath 'C:\\Program Files\\ClaudePet\\unins000.exe' "
```

63 of 63 lines identical, so **no count below is attributable to the deviation**; the synthetic line
is the case that separates them and is why the shipped form is the one kept. No helper the tree emits
today has that shape, which is precisely why this is recorded as a deviation rather than as a defect
the review missed.

## B4.2 The rival mirrors

Five scratch copies of `windows/win_update.py`, built from the worktree bytes by an
occurrence-counted `str.replace` script that asserts its needle count before and after. **None is on
a git path**; all live under
`/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/ver-f2-b4/<name>/windows/win_update.py`.

| mirror | mutation | sha256 |
| --- | --- | --- |
| `MR1` | the `Wait-Process` line **deleted** from the two uninstall builders only (`build_swap_script`'s copy left intact, so any failure is attributable to those two) | `2b8d97ff063b1667ba733bfacc572e391a7da33ee65eec9b9984480cc6f2ba73` |
| `MR3` | the inno helper launches first, then waits | `0197713fea99cd09938483346a30250105c461fdd81d6e89fa0d64ecc418405a` |
| `MR4` | interpolated paths stop going through `ps_quote` (both builders) | `fdd2c892fb130257c78def8080804b92949c1ee67e6b2bb456331bbbb62dd3f6` |
| **`MR6`** | the wait is **commented out** in both uninstall builders, real pid and timeout kept in the comment | `bacbe720bbee7196328111fdd18a490c312404ce8522ce06701f0a9636ae4dca` |
| **`MR8`** | the still-alive refusal is **commented out**, likewise | `7b668009b436a5016472b41508b0f6cc9f343d69d49e3f1dc0b031f1c0aa3c09` |

`MR3` came out byte-identical (`0197713f…`) to the closing Reviewer's `MR3` and to the earlier
round's `R3`, though it was rebuilt here from the source text without consulting either — an
incidental cross-check of that rival, not of the two that matter.

The emitted line MR6 produces is byte-identical to the script the Reviewer quoted:

```
# Wait-Process -Id 424242 -Timeout 120 -- disabled while debugging
```

MR8's is `# if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }`.

## B4.3 RED — the defect reproduced, before the fix

`windows/tests/test_win_uninstall_contract.py` at `3791adc9a364069e1beb84ca6d3ec1bdcb0829118e91ea05162643c04b7f1c3f`
(the bytes the Reviewer read), 2026-09-14T03:07Z:

```
$ for m in MR1 MR3 MR4 MR6 MR8; do CLAUDE_PET_WIN_RIVAL_ROOT=$SP/$m \
      python3 -m unittest windows.tests.test_win_uninstall_contract; done
===== PRE-FIX MR1 =====   Ran 38 tests in 0.186s   FAILED (failures=10)
===== PRE-FIX MR3 =====   Ran 38 tests in 0.152s   FAILED (failures=2)
===== PRE-FIX MR4 =====   Ran 38 tests in 0.149s   FAILED (failures=7)
===== PRE-FIX MR6 =====   Ran 38 tests in 0.152s   OK
===== PRE-FIX MR8 =====   Ran 38 tests in 0.150s   OK
```

**MR6 and MR8 pass all 38.** B4 reproduces exactly as reported, on an independently built pair of
mirrors. This is the red state for the fix that follows — observed, not reconstructed.

## B4.4 GREEN — after the fix

`windows/tests/test_win_uninstall_contract.py` at `efd33cff182b72ad01aca417240c099c06cb144740d7502fe688f80f5e66f9c3`,
2026-09-14T03:08:48Z:

```
$ python3 -m unittest windows.tests.test_win_uninstall_contract
Ran 38 tests in 0.186s
OK

$ python3 -m unittest discover -s windows/tests -t .
Ran 217 tests in 1.154s
OK (skipped=2)
```

The working tree is unchanged in behaviour: same 38, still `OK`, no skips in that module. (The 217/2
line is the suite *before* B4.6's deletion of the two dead skips; B4.6 records the after.)

```
$ for m in MR1 MR3 MR4 MR6 MR8; do CLAUDE_PET_WIN_RIVAL_ROOT=$SP/$m \
      python3 -m unittest windows.tests.test_win_uninstall_contract; done
===== POST-FIX MR1 =====   Ran 38 tests in 0.158s   FAILED (failures=10)
===== POST-FIX MR3 =====   Ran 38 tests in 0.150s   FAILED (failures=2)
===== POST-FIX MR4 =====   Ran 38 tests in 0.149s   FAILED (failures=7)
===== POST-FIX MR6 =====   Ran 38 tests in 0.148s   FAILED (failures=10)
===== POST-FIX MR8 =====   Ran 38 tests in 0.150s   FAILED (failures=6)
```

| mirror | pre-fix | post-fix | the Reviewer predicted |
| --- | --- | --- | --- |
| `MR6` | **OK (38)** ✗ | **FAILED (failures=10)** | 10 |
| `MR8` | **OK (38)** ✗ | **FAILED (failures=6)** | 6 |
| `MR1` | FAILED (10) | FAILED (10) | 10, unchanged |
| `MR3` | FAILED (2) | FAILED (2) | 2, unchanged |
| `MR4` | FAILED (7) | FAILED (7) | 7, unchanged |
| working tree | OK (38) | **OK (38)** | 38, `OK` |

Every count matches the prediction, and the three pre-existing rivals kept exactly the discrimination
they had — the fix tightened the two ties and loosened nothing.

## B4.5 The two new red runs, verbatim

MR6 — the 10 failures are, by class and method:

```
FAIL: test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive (…InnoUninstallHelperTextTests…)
FAIL: test_it_waits_on_the_apps_pid_with_a_bounded_timeout (…InnoUninstallHelperTextTests…)
FAIL: test_nothing_touches_the_machine_before_the_wait (…InnoUninstallHelperTextTests…)
FAIL: test_the_refusal_uses_the_documented_exit_code_two (…InnoUninstallHelperTextTests…)
FAIL: test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal (…InnoUninstallHelperTextTests…)
FAIL: test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive (…PortableUninstallHelperTextTests…)
FAIL: test_it_waits_on_the_apps_pid_with_a_bounded_timeout (…PortableUninstallHelperTextTests…)
FAIL: test_nothing_touches_the_machine_before_the_wait (…PortableUninstallHelperTextTests…)
FAIL: test_the_app_folder_is_removed_only_after_the_wait_and_the_refusal (…PortableUninstallHelperTextTests…)
FAIL: test_the_refusal_uses_the_documented_exit_code_two (…PortableUninstallHelperTextTests…)
```

and the first of them in full, including the helper the suite used to accept:

```
FAIL: test_it_waits_on_the_apps_pid_with_a_bounded_timeout (windows.tests.test_win_uninstall_contract.InnoUninstallHelperTextTests.test_it_waits_on_the_apps_pid_with_a_bounded_timeout)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 437, in test_it_waits_on_the_apps_pid_with_a_bounded_timeout
    self.assert_waits_on_our_pid(self.text)
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 333, in assert_waits_on_our_pid
    i = self._wait_index(lines)
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 327, in _wait_index
    self.assertGreaterEqual(
        i, 0, "the generated helper never waits for the app to exit:\n" + "\n".join(lines))
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
# ClaudePet inno uninstall helper — generated by windows/win_update.py.
$ErrorActionPreference = 'Stop'
# Wait-Process -Id 424242 -Timeout 120 -- disabled while debugging
if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }
if (Test-Path -LiteralPath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe') {
  try { Start-Process -FilePath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe' -ArgumentList '/SILENT', '/SUPPRESSMSGBOXES' } catch { exit 3 }
}
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }
exit 0
```

MR8 — the 6 failures:

```
FAIL: test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive (…InnoUninstallHelperTextTests…)
FAIL: test_the_refusal_uses_the_documented_exit_code_two (…InnoUninstallHelperTextTests…)
FAIL: test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal (…InnoUninstallHelperTextTests…)
FAIL: test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive (…PortableUninstallHelperTextTests…)
FAIL: test_the_app_folder_is_removed_only_after_the_wait_and_the_refusal (…PortableUninstallHelperTextTests…)
FAIL: test_the_refusal_uses_the_documented_exit_code_two (…PortableUninstallHelperTextTests…)
```

and the first in full:

```
FAIL: test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive (windows.tests.test_win_uninstall_contract.InnoUninstallHelperTextTests.test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 443, in test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive
    self.assert_refuses_when_still_alive(self.text)
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 370, in assert_refuses_when_still_alive
    _j, code = self._refusal(text)
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_uninstall_contract.py", line 360, in _refusal
    self.assertGreaterEqual(
        j, 0,
        "nothing checks whether the pid is still alive after the wait, so a wait that "
        "times out is indistinguishable from one that succeeded:\n" + "\n".join(lines))
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive after the wait, so a wait that times out is indistinguishable from one that succeeded:
# ClaudePet inno uninstall helper — generated by windows/win_update.py.
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id 424242 -Timeout 120 -ErrorAction Stop } catch { }
# if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }
if (Test-Path -LiteralPath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe') {
  try { Start-Process -FilePath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe' -ArgumentList '/SILENT', '/SUPPRESSMSGBOXES' } catch { exit 3 }
}
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }
exit 0
```

**Read the cascade correctly.** MR6 fails ten assertions, not one, because the wait index is the
anchor every later assertion is measured from; the ten are five per builder, and they are ten
*reports* of one defect. That is not ten independent discriminations, and it is written down here so
nobody counts it as such.

The fail-closed mirror instrument was re-exercised this round, by pre-importing
`windows.win_update` from the worktree so the mirror is set but does not take effect:

```
RuntimeError: rival run is vacuous: windows/win_update.py resolved to
/Users/yeongyu/claude-pet-windows/windows/win_update.py, not to the mirror copy at
…/ver-f2-b4/MR6/windows/win_update.py
```

It raises rather than reporting green, so none of the runs above can be a silent worktree run.

## B4.6 N8 — `windows/tests/test_win_hardware_fixes.py`, corrected by its author

The closing Reviewer recorded two non-blocking residues in this file. Both are fixed here. **This
Verifier wrote that file**, and this round's assignment names it, which is what makes the edit
permissible — AGENTS.md §4 permits an agent to modify a file it created and its assignment names.
CR.8 item 4 of the previous round said the file could not be touched "because it is hash-pinned in
this record"; that reason is retired by this section, which updates the pin.

**(a) The refuted sentence.** `InstallerClosesTheAppTests`'s docstring carried a `POSTUNINST` rival
column and the sentence

> That flag is the ordering pin: without it, an `[UninstallRun]` entry runs at the start of the
> uninstall, before file removal.

Round 2 (R2.5) refuted it: `postuninstall` is not an Inno Setup flag — it is absent from the complete
Flags list on <https://jrsoftware.org/ishelp/topic_runsection.htm>, and the post-uninstall concept
exists only as the `usPostUninstall` `TUninstallStep` constant reached from `CurUninstallStepChanged`
in `[Code]`. The rival therefore cannot be written, its table row proved nothing, and the ordering it
described as *conditional* is unconditional ("as the first step of *uninstallation*"). The column and
the sentence are removed; a **Correction** paragraph replaces them, states the unconditional guarantee
with its citation, says the retained `assertNotIn("postuninstall", flags)` line is **not** the
ordering pin, and points at
`windows/tests/test_win_uninstall_contract.InstallerUninstallRunTests` for the flags that can
actually defeat the fix (`nowait` / `shellexec` / `waituntilidle`, plus the whole-flag-set
allow-list). The assertion itself is untouched.

**(b) The two dead skips — deleted, not re-expressed.** `InAppInnoUninstallOrderTests` carried

```python
    def test_the_uninstaller_is_not_launched_while_the_app_is_still_running(self):
        ...
        if self._pid_wait():
            self.skipTest("PID-WAIT implementation: os.getpid() is handed to the launched helper")

    def test_a_moment_is_given_for_the_process_to_exit(self):
        if self._pid_wait():
            self.skipTest("PID-WAIT implementation: the helper waits on the pid instead")
```

Both skipped on every run against the tree, which is the `OK (skipped=2)` this record has carried
since its first round. They are deleted, together with the members that existed only for them
(`WAITS`, `QUITS`, `_launches()`, `_pid_wait()`). **Deleted rather than re-expressed** because an
unconditional re-expression would be a second, weaker statement of a rule now asserted with no
predicate in `windows/tests/test_win_uninstall_contract.py` — the pid hand-over and the helper launch
in `InAppInnoUninstallOrderTests` there, and that the helper actually waits and refuses in
`InnoUninstallHelperTextTests` — and two statements of one rule, one of them weaker, is the state
that hid this hole in the first place. The class docstring now records what was deleted, why, and
where the obligation lives; the one test that never skipped,
`test_the_refusable_precheck_still_precedes_every_irreversible_delete`, stays, and the class's truth
table is reduced to the single row it still gates.

Suite after the deletion, 2026-09-14T03:10:57Z:

```
$ python3 -m unittest discover -s windows/tests -t .
Ran 215 tests in 1.107s
OK
```

**217 → 215, and `skipped=2` → no skips.** The two tests removed are exactly the two that were
skipping; nothing else changed count, and no test that ever executed was removed. A `-v` run
confirms the only remaining line containing "skipped" is the *name* of an unrelated passing test
(`test_win_update.LeftoverDirsTests.test_listed_and_skipped`).

**Hash pin update.** `windows/tests/test_win_hardware_fixes.py` is pinned as `53b3582b…` at eight
places earlier in this record (§ "File hashes at the RED run", R2.1, the fourth-round table, CR.6 and
the CR.9 closing statement). Those pins describe the bytes at the time each was taken and remain
correct as history. **From this round forward the file is
`392f9bc3eb6f2ae020ddfeb686ba7d1c9372845952c090b038076f4027f5d84d`**, changed by verifier-f2 — the
file's author — under this round's assignment, for the two reasons in (a) and (b) and for nothing
else. No assertion in the file was added, removed, reordered or relaxed apart from the two whole
tests named in (b); no fixture literal was touched.

## B4.7 File hashes at the end of this round

`shasum -a 256`, 2026-09-14T03:11:40Z, worktree root:

```
efd33cff182b72ad01aca417240c099c06cb144740d7502fe688f80f5e66f9c3  windows/tests/test_win_uninstall_contract.py   ← changed this round (B4.1)
392f9bc3eb6f2ae020ddfeb686ba7d1c9372845952c090b038076f4027f5d84d  windows/tests/test_win_hardware_fixes.py       ← changed this round (B4.6), was 53b3582b…
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
3d8308152c3293de36451ebac2224494b82f9b3435e19614d666b9d86527483e  windows/installer.iss
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py
```

The four production files carry the same hashes they had at the start of this round —
`windows/win_update.py` in particular is `e2de9ad5…` both before and after — so **AGENTS.md §2
Condition B holds**: the set of files this Verifier edited is
`{windows/tests/test_win_uninstall_contract.py, windows/tests/test_win_hardware_fixes.py,
docs-design/track-f-verification-20260914.md}`, disjoint from every production file of this change.
Condition A holds for the same reason it did before: no Developer touched either gating file.

`git status --porcelain` at the same moment, unchanged in shape from the start of the round (the
three user-owned paths are absent from it because this worktree does not carry them; nothing here
read or wrote them):

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-review-20260914.md
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/tests/test_win_uninstall_contract.py
?? windows/win_core.py
```

## B4.8 What this round still does not gate

Carried forward from CR.7 and extended, so the next reader does not over-read 38 green tests:

- **`_ps_code` itself has no test in the suite.** It is exercised only by the MR6/MR8 rival runs
  recorded above, which are not part of `python3 -m unittest discover -s windows/tests -t .`. If a
  later edit broke `_PS_STRING` or the helper, the working tree would stay green and the two ties
  would silently come back; only re-running the mirrors would show it. A three-assertion instrument
  test would close this — trailing comment dropped, `#` inside a quoted path kept, index unshifted —
  and was deliberately **not** added this round so that the counts above stay directly comparable to
  the Reviewer's validated remedy (`Ran 38 … OK`). Recorded here as the residue it is, in the same
  spirit as the repo-root `tests/test_mutation_instruments.py`.
- **Nothing here executes PowerShell**, so "PowerShell treats `#` outside a quoted span as starting a
  comment" is a claim about the language, not a measured behaviour of this host. It is the reason the
  helper is correct, and it is untested here exactly as the rest of the helper-text gating is.
  Block comments (`<# … #>`) and a `#` inside a double-quoted or here-string span are not handled —
  no builder emits either, and a builder that started to would need this helper extended.
- Everything else in CR.7 stands unchanged: no `ISCC`, no Inno, no PyInstaller, no PE parser;
  `build_swap_script` is still not gated by this file; `_uninstall` is still read structurally and
  never run; N7 is still untouched.

## B4.9 Status

**GREEN.**

- B4 is closed. The two rivals it was raised about were rebuilt independently, **observed passing all
  38 tests before the fix** and failing **10** (MR6) and **6** (MR8) after it; MR1/MR3/MR4 keep their
  previous discrimination at **10 / 2 / 7**; the working tree is **`Ran 38 … OK`** throughout.
- N8 is closed: the refuted sentence is corrected with its citation and the two dead skips are gone.
  The Windows suite is now **`Ran 215 … OK`** with no skips.
- **B1 is unchanged and still blocks merge**, and is still not Track F's to close: the two stale
  `REVIEWED_APP_SOURCE_SHA256` pins under the repo-root `tests/` are a mismatch `main` carries too.
  Nothing in this round touched `claude_pet.py` or the repo-root `tests/`.
