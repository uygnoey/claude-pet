# Verification record — Track B "Start at sign-in", Windows half (v0.25 follow-ups)

Verifier: verifier-bw (Claude), VERIFIER role only on this track. Record opened
2026-09-13T14:45Z. Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD
`e098516` (Track C/D + `main` merged — `claude_pet.py` carries the macOS half and the six
`autostart_*` TR keys). This file is untracked and is not committed by the Verifier; the
Coordinator stages by named paths.

Inputs: the task brief (fixed design), the survey key `autostart` in the session scratchpad
`followups-survey.json`, AGENTS.md §2 / §3 / §5, CLAUDE.md § "Start at sign-in" (the UX the
Windows half mirrors), `windows/README.md`, `windows/claude_pet_win.py` (`_context_menu`, the
roam `QAction`, `_uninstall`, `_msgbox` / `_info`, `is_frozen` / `app_exe_path`,
`delete_run_value_if_ours`), `windows/win_update.py` (`install_kind` and its injected reader,
`log_update`, `uninstall_plan`, `run_value_is_ours`, `RUN_SUBKEY` / `RUN_VALUE_NAME`),
`windows/installer.iss` (`[Registry]` Run line), `windows/tests/test_win_update.py` (the fake
callables, the truth-table docstrings, the `CLAUDE_PET_WIN_PORT_SOURCE` convention),
`tests/test_autostart.py` (the macOS gates, for the AST helpers and the parity check),
`docs-design/track-b-verification-20260913.md` (format).

Files the Verifier wrote: `windows/tests/test_win_autostart.py` (new) and this record.
Nothing else. No production file was opened for writing — `windows/claude_pet_win.py`,
`windows/win_update.py`, `windows/installer.iss`, `windows/README.md` and `claude_pet.py`
hash identical to HEAD before, during and after the red run (§1, §3). No git write command
was run. The GUI was not run. No untracked file the Verifier did not create was touched
(this worktree had none). `~/.claude_pet.json` was neither read nor written: the config
guard redirects `cp.CONFIG_PATH`, `HOME` and `USERPROFILE` to a temp directory. The real
Windows registry cannot be reached from this host and no test tries: every registry access
goes through dict-backed fakes, and the adapter tests install a fake `winreg` module in
`sys.modules`. A scratch harness (§4) lived only in the session scratchpad and is discarded.

All commands ran with cwd `/Users/yeongyu/claude-pet-windows`. Times are UTC. Output blocks
are verbatim except where a line is marked `…` (elided).

## 1. The tree under verification (14:45Z)

```
$ git rev-parse --short HEAD ; git branch --show-current ; git status --porcelain
e098516
windows
                                       # clean — no untracked files before authoring
$ shasum -a 256 windows/claude_pet_win.py windows/win_update.py windows/installer.iss claude_pet.py windows/README.md
bb565b086f12a6a46e30049d7dd4f60cdf1a9ef161eec3e4ff3cc63885e5c6a4  windows/claude_pet_win.py
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
912b88681cbcc1f93b7907a3c50d5858e25d9b737a1240e58b20b0621737d014  windows/README.md
$ git show HEAD:windows/claude_pet_win.py | shasum -a 256 ; git show HEAD:claude_pet.py | shasum -a 256
bb565b086f12a6a46e30049d7dd4f60cdf1a9ef161eec3e4ff3cc63885e5c6a4  -
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  -
```

Host: Python 3.13.7 (python.org framework build). `import winreg`, `import PySide6`,
`import PIL` all raise `ModuleNotFoundError` here — note the port is **PySide6**, not PyQt6
(`windows/requirements.txt`: `PySide6==6.9.1`); either way it cannot be imported on this
host, so every pin on the port is an AST / text pin, the shape `test_win_update.py` already
uses (`PortWiringTests`, `LogUpdateCallShapeTests`).

Facts read from source (deterministic, cited, not "observed" — AGENTS.md §5):

- `_context_menu` (claude_pet_win.py, `grep -n "def _context_menu"`) builds a fresh
  `QMenu(self)` bound to `m` on every right-click; `roam = QAction(cp.t("menu_roam"), m,
  checkable=True)` … `m.addAction(roam)` is followed directly by
  `m.addAction(cp.t("menu_reset_size"), self._reset_scale)`. The docstring pins the item order
  as the macOS `rightMouseDown_` order. No `aboutToShow` is connected today.
- `is_frozen()` is `bool(getattr(sys, "frozen", False)) and _WIN32`; `app_exe_path()` is
  `os.path.abspath(sys.executable)` when frozen, else `None`. The brief's
  `is_frozen = getattr(sys, "frozen", False); exe = sys.executable` and these helpers both
  satisfy the handover pin (§2, D-W9).
- `_uninstall` calls `delete_run_value_if_ours(exe)` in its irreversible section (after the
  `popen_detached` launch of the uninstaller / helper), and that helper is guarded by
  `wu.run_value_is_ours(value, exe)` before `winreg.DeleteValue`. **`uninstall_plan` does not
  carry a registry step** — it is a file plan over `("delete", path)` / `("run", argv)` /
  `("helper", dir)`. The brief's premise ("the existing uninstall_plan already deletes the Run
  value") is therefore not what the code does; §2 D-W6 says what was pinned instead.
- `installer.iss` `[Registry]`: `Root: HKCU; Subkey:
  "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ClaudePet";
  ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup` — in Inno's
  quoting one pair of double quotes around the path.
- `wu.RUN_SUBKEY` / `wu.RUN_VALUE_NAME` are the same two literals; `wu.run_value_is_ours`
  strips one pair of quotes and compares with `ntpath.normcase`.
- `TR_WIN` in the port holds Windows-only keys (`upd_no_asset`, `upd_source`,
  `upd_installing`, `unin_busy`) and `tw()` falls back to `cp.t()`; none of the six
  `autostart_*` keys is there. `cp.TR[loc]` defines all six for en/ko/ja/es (merged from `main`).

Windows-suite baseline before authoring:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; python3 -m unittest discover -s windows/tests -t . ; echo "exit=$?"
2026-09-13T14:45:32Z
…
Ran 98 tests in 0.116s

OK
exit=0
```

## 2. Surface pinned, and the decisions taken where the design left a choice

The module docstring of `windows/tests/test_win_autostart.py` carries the full contract; this
is the Developer's checklist. `windows/win_autostart.py`, importable on this host as
`windows.win_autostart` and by the port as `win_autostart`:

| name | contract |
| --- | --- |
| `run_value_for(exe)` | `'"' + exe + '"'` — byte-identical to the installer line's expansion. |
| `startup_approved_enabled(blob)` | `True` iff `blob` is bytes with first byte `0x02`; `0x03`, `b""`, `None`, a `str` → `False`, never an exception. |
| `autostart_read_state(reader, exe, is_frozen)` | `"on"` iff frozen ∧ Run value present ∧ its unquoted path equals `exe` under `ntpath.normcase` ∧ StartupApproved absent or enabled. Absent / foreign path / disabled → `"off"`. Not frozen → `"unavailable"` with **no** registry call. `reader is None` or no exe → `"unavailable"`, no call. Reader raises → `"unavailable"`. Never writes. |
| `autostart_toggle(reader, writer, exe, is_frozen)` | `("on"/"off", None)` on success, `(state-before, "autostart_fail")` when the writer raises, `("unavailable", None)` when not frozen / no reader or writer / reader raises — with nothing written. From on: delete Run; delete StartupApproved if present. From off: write `run_value_for(exe)` (overwriting a foreign path); delete a *disabled* StartupApproved entry. Exact writer call lists are pinned for the two plain transitions. |
| `RUN_SUBKEY`, `RUN_VALUE_NAME`, `STARTUP_APPROVED_SUBKEY` | equal to `wu.RUN_SUBKEY`, `wu.RUN_VALUE_NAME`, and `Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run`. |
| `registry_reader(subkey, name)` / `registry_writer(subkey, name, data)` | the thin adapter; `import winreg` **inside** the function; reader returns the value (not the `(value, type)` pair), `None` on `FileNotFoundError` from either the key or the value, lets any other `OSError` out; writer `SetValueEx(…, REG_SZ, data)` on a `str`, `DeleteValue` on `None`. |
| `real_registry()` | `(registry_reader, registry_writer)` when `sys.platform == "win32"` **read at call time**, else `(None, None)`. |

The seam: `reader(subkey, name) -> value | None` (absent) and `writer(subkey, name, data)`
(`str` sets, `None` deletes), both positional. The fakes key their dicts on the literal
installer locations, so a module reading anywhere else sees an empty registry.

The port, by AST: a checkable `QAction(cp.t("menu_autostart"), …)` whose `m.addAction`
comes directly after `m.addAction(roam)` and before `menu_reset_size` — the quintet
`menu_settings, menu_toggle, menu_roam, menu_autostart, menu_reset_size` must equal the
macOS `rightMouseDown_` slice; `m.aboutToShow.connect(<slot>)` where the reachable code calls
`autostart_read_state` and `setChecked` / `setEnabled` / `setText` and uses
`t("autostart_unavailable")`; `<action>.triggered.connect(<slot>)` where the reachable code
calls `autostart_toggle`, uses `t("autostart_title")` and `t("autostart_fail")`, and reaches
`_msgbox` or `_info`; the reachable code of both slots references the frozen flag
(`is_frozen` or the `"frozen"` literal), the executable (`sys.executable` or
`app_exe_path`), and `real_registry` (or both adapter names); no `"autostart"` string
constant anywhere in the port, no `merge_config_updates` / `save_config` / `RUNTIME` in the
slots; none of the six keys defined in `TR_WIN`; `menu_autostart`, `autostart_unavailable`,
`autostart_title`, `autostart_fail` used through a `t`-call. "Reachable" follows nested
defs of `_context_menu`, `self.<method>` and module-level functions, bounded, so a helper
method between the slot and the pure call is fine.

Decisions taken by the Verifier so that each test pins one behaviour. The Coordinator can
override any; an override changes an assertion and goes back through the Verifier (§2 A).

- **D-W1 — the seam's absence convention.** `install_kind`'s reader "returns or raises" is
  not enough here: the fixed design needs "absent → off" and "raised → unavailable" to
  differ, and `winreg` reports absence by raising. So the reader returns `None` for absent
  and the adapter owns that translation (`RegistryAdapterTests`).
- **D-W2 — adapter names and guard.** `registry_reader` / `registry_writer` /
  `real_registry()`; the platform guard lives in `real_registry()` and is read at call time
  (`mock.patch.object(sys, "platform", …)` must flip it); the adapters themselves do not
  check the platform, so a fake `winreg` in `sys.modules` exercises them on macOS.
- **D-W3 — the byte check is fail-safe.** Only `0x02` reads enabled. Degenerate inputs
  (`b""`, `None`, a `str`) read "not enabled" and never raise; first bytes other than
  `0x02` / `0x03` are **not** pinned — that is the hardware question. Rationale in the class
  docstring: an unreadable blob read as "off" self-heals on the next click (the entry is
  deleted; absent = enabled); read as "on" it shows a checkmark Windows does not honour
  with no click that fixes it.
- **D-W4 — `exe` falsy or `reader is None` → `"unavailable"`, no call** (mirrors the macOS
  `service is None` rule).
- **D-W5 — a foreign Run value is overwritten on enable, never deleted on its own**, per the
  fixed design and the survey's "repairs a stale portable-zip path". On disable, only a value
  that reads as ours is ever deleted (the state is `"off"` otherwise, so the click enables).
- **D-W6 — uninstall pins the real mechanism.** `uninstall_plan` is asserted to be a file plan
  with no registry location; `_uninstall` is asserted to call `delete_run_value_if_ours(`
  *after* the launch, and that helper to keep `run_value_is_ours(` + `DeleteValue(`; and the
  gate proper: `wu.run_value_is_ours(wa.run_value_for(EXE), EXE)` is `True` (also for the
  upper-cased exe), `False` for another exe. The first two are regression pins and were green
  in the red run — said so in the docstring.
- **D-W7 — README is a documentation pin**, tolerant: `StartupApproved`, both `0x02` and
  `0x03`, `작업 관리자` or `Task Manager`, and the ko menu string or the key name.
- **D-W8 — no local strings.** The port may reach the key through `cp.t(` or `tw(` (which
  falls back to `cp.t`), but `TR_WIN` must not define any of the six keys — a local override
  would break "both halves read identically".
- **D-W9 — handover is pinned by name, not by expression**: `is_frozen()` (the port's helper,
  which already ANDs `_WIN32`) or `getattr(sys, "frozen", …)` both pass; likewise
  `app_exe_path()` or `sys.executable`.
- **D-W10 — "report the flipped state without re-reading" is not a rival.** Under this
  writer contract a write either lands or raises, so it is indistinguishable from re-reading;
  the harness (§4) confirmed it passes every row. The consistency test that was going to
  "catch" it is kept as what it is — the two functions agreeing on every transition — and
  the docstring says so. A test that claims to discriminate a rival it cannot is the §3
  hazard in another form.

## 3. Red run (AGENTS.md §3 step 2)

Two corrections while authoring, both before any production change, both recorded so the
red is not retrospective:

1. 14:52Z first run (43 tests: 32 errors, 8 failures, 3 ok): the README pin used
   `assertIn("StartupApproved", text)`, whose failure message dumps the whole README. Changed to
   `assertTrue(… in text, "the README never names StartupApproved")`. No expected value changed.
2. 14:57Z, from the scratch harness (§4): the `ASSUME` rival passed every row. Its claim was
   removed from the `ToggleTests` docstring (D-W10). No assertion changed.

Final red run. `windows/win_autostart.py` does not exist; the five production files hash as
in §1; `windows/tests/test_win_autostart.py` at
`a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6`:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; git rev-parse --short HEAD ; git status --porcelain
2026-09-13T15:00:04Z
e098516
?? windows/tests/test_win_autostart.py

$ shasum -a 256 windows/tests/test_win_autostart.py windows/claude_pet_win.py windows/win_update.py windows/installer.iss windows/README.md claude_pet.py ; ls windows/win_autostart.py
a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6  windows/tests/test_win_autostart.py
bb565b086f12a6a46e30049d7dd4f60cdf1a9ef161eec3e4ff3cc63885e5c6a4  windows/claude_pet_win.py
0fd40d9a7b16fc8ef93c1c666740655b7df76b3307f870d8b60b8142fbc8d65d  windows/win_update.py
07fcf4c4b534891220ec0b8be33a587503b21fe6a4cec6a274094992bdb8afc0  windows/installer.iss
912b88681cbcc1f93b7907a3c50d5858e25d9b737a1240e58b20b0621737d014  windows/README.md
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
ls: windows/win_autostart.py: No such file or directory

$ python3 -m unittest discover -s windows/tests -t . -v ; echo "exit=$?"
…                                   # the 98 pre-existing test_win_update tests, every one "ok"
test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos (windows.tests.test_win_autostart.PortWiringTests.test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos) ... FAIL
test_no_config_key_and_no_local_override (windows.tests.test_win_autostart.PortWiringTests.test_no_config_key_and_no_local_override) ... FAIL
test_the_autostart_action_is_checkable (windows.tests.test_win_autostart.PortWiringTests.test_the_autostart_action_is_checkable) ... FAIL
test_the_click_toggles_and_a_failure_reaches_the_message_box (windows.tests.test_win_autostart.PortWiringTests.test_the_click_toggles_and_a_failure_reaches_the_message_box) ... FAIL
test_the_menu_rereads_the_state_when_it_opens (windows.tests.test_win_autostart.PortWiringTests.test_the_menu_rereads_the_state_when_it_opens) ... FAIL
test_the_wiring_hands_over_the_frozen_flag_the_exe_and_the_real_registry (windows.tests.test_win_autostart.PortWiringTests.test_the_wiring_hands_over_the_frozen_flag_the_exe_and_the_real_registry) ... FAIL
test_no_reader_or_no_exe_is_unavailable_without_a_call (windows.tests.test_win_autostart.ReadStateTests.test_no_reader_or_no_exe_is_unavailable_without_a_call) ... ERROR
test_persisted_preference_does_not_win (windows.tests.test_win_autostart.ReadStateTests.test_persisted_preference_does_not_win)
CFG: the OS registration is the only source of truth (no config key). ... ERROR
test_reader_failure_is_unavailable_not_off_and_not_raised (windows.tests.test_win_autostart.ReadStateTests.test_reader_failure_is_unavailable_not_off_and_not_raised) ... ERROR
test_reads_only_the_installers_two_locations (windows.tests.test_win_autostart.ReadStateTests.test_reads_only_the_installers_two_locations) ... ERROR
test_source_run_is_unavailable_and_reads_nothing (windows.tests.test_win_autostart.ReadStateTests.test_source_run_is_unavailable_and_reads_nothing) ... ERROR
test_state_table (windows.tests.test_win_autostart.ReadStateTests.test_state_table) ... ERROR
test_readme_names_the_toggle_and_the_hardware_checks (windows.tests.test_win_autostart.ReadmeTests.test_readme_names_the_toggle_and_the_hardware_checks) ... FAIL
test_importable_the_way_the_port_imports_it (windows.tests.test_win_autostart.RegistryAdapterTests.test_importable_the_way_the_port_imports_it)
The port runs with ``windows/`` first on sys.path and imports ``win_autostart`` bare. ... FAIL
test_reader_lets_a_denied_open_out (windows.tests.test_win_autostart.RegistryAdapterTests.test_reader_lets_a_denied_open_out) ... ERROR
test_reader_returns_none_for_an_absent_value_and_an_absent_key (windows.tests.test_win_autostart.RegistryAdapterTests.test_reader_returns_none_for_an_absent_value_and_an_absent_key) ... ERROR
test_reader_returns_the_value_not_the_pair (windows.tests.test_win_autostart.RegistryAdapterTests.test_reader_returns_the_value_not_the_pair) ... ERROR
test_real_registry_is_decided_by_the_platform_at_call_time (windows.tests.test_win_autostart.RegistryAdapterTests.test_real_registry_is_decided_by_the_platform_at_call_time) ... ERROR
test_winreg_is_imported_inside_the_adapter_only (windows.tests.test_win_autostart.RegistryAdapterTests.test_winreg_is_imported_inside_the_adapter_only) ... ERROR
test_writer_deletes_on_none (windows.tests.test_win_autostart.RegistryAdapterTests.test_writer_deletes_on_none) ... ERROR
test_writer_sets_a_reg_sz_named_value (windows.tests.test_win_autostart.RegistryAdapterTests.test_writer_sets_a_reg_sz_named_value) ... ERROR
test_matches_the_installer_registry_line (windows.tests.test_win_autostart.RunValueTests.test_matches_the_installer_registry_line) ... ERROR
test_quoted_once_with_double_quotes (windows.tests.test_win_autostart.RunValueTests.test_quoted_once_with_double_quotes) ... ERROR
test_shares_the_updaters_registry_names (windows.tests.test_win_autostart.RunValueTests.test_shares_the_updaters_registry_names) ... ERROR
test_what_the_toggle_writes_the_uninstaller_recognises (windows.tests.test_win_autostart.RunValueTests.test_what_the_toggle_writes_the_uninstaller_recognises) ... ERROR
test_every_locale_defines_every_key (windows.tests.test_win_autostart.SharedKeysTests.test_every_locale_defines_every_key) ... ok
test_table (windows.tests.test_win_autostart.StartupApprovedTests.test_table) ... ERROR
test_a_foreign_path_is_overwritten_not_deleted (windows.tests.test_win_autostart.ToggleTests.test_a_foreign_path_is_overwritten_not_deleted) ... ERROR
test_a_foreign_path_with_a_disabled_entry (windows.tests.test_win_autostart.ToggleTests.test_a_foreign_path_with_a_disabled_entry) ... ERROR
test_disabled_in_task_manager_is_off_and_the_click_unblocks_it (windows.tests.test_win_autostart.ToggleTests.test_disabled_in_task_manager_is_off_and_the_click_unblocks_it) ... ERROR
test_never_a_config_key (windows.tests.test_win_autostart.ToggleTests.test_never_a_config_key)
PERSIST: no preference is read or written — design X, the macOS contract. ... ERROR
test_no_registry_is_unavailable (windows.tests.test_win_autostart.ToggleTests.test_no_registry_is_unavailable) ... ERROR
test_off_to_on_writes_exactly_the_installers_value (windows.tests.test_win_autostart.ToggleTests.test_off_to_on_writes_exactly_the_installers_value) ... ERROR
test_on_to_off_also_removes_a_present_startup_approved_entry (windows.tests.test_win_autostart.ToggleTests.test_on_to_off_also_removes_a_present_startup_approved_entry) ... ERROR
test_on_to_off_deletes_the_run_value_only (windows.tests.test_win_autostart.ToggleTests.test_on_to_off_deletes_the_run_value_only) ... ERROR
test_reader_failure_is_unavailable_and_writes_nothing (windows.tests.test_win_autostart.ToggleTests.test_reader_failure_is_unavailable_and_writes_nothing) ... ERROR
test_source_run_touches_nothing (windows.tests.test_win_autostart.ToggleTests.test_source_run_touches_nothing) ... ERROR
test_the_returned_state_is_what_the_registry_now_reads (windows.tests.test_win_autostart.ToggleTests.test_the_returned_state_is_what_the_registry_now_reads)
The state reported is the state a fresh read sees, and a second click flips it back. ... ERROR
test_writer_failure_turning_off_reports_and_leaves_on (windows.tests.test_win_autostart.ToggleTests.test_writer_failure_turning_off_reports_and_leaves_on) ... ERROR
test_writer_failure_turning_on_reports_and_leaves_off (windows.tests.test_win_autostart.ToggleTests.test_writer_failure_turning_on_reports_and_leaves_off) ... ERROR
test_the_port_deletes_the_run_value_after_the_point_of_no_return (windows.tests.test_win_autostart.UninstallPinTests.test_the_port_deletes_the_run_value_after_the_point_of_no_return) ... ok
test_uninstall_plan_is_a_file_plan_with_no_registry_step (windows.tests.test_win_autostart.UninstallPinTests.test_uninstall_plan_is_a_file_plan_with_no_registry_step) ... ok
test_what_the_toggle_writes_is_what_the_uninstaller_recognises (windows.tests.test_win_autostart.UninstallPinTests.test_what_the_toggle_writes_is_what_the_uninstaller_recognises) ... ERROR

======================================================================
ERROR: test_no_reader_or_no_exe_is_unavailable_without_a_call (windows.tests.test_win_autostart.ReadStateTests.test_no_reader_or_no_exe_is_unavailable_without_a_call)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_autostart.py", line 455, in test_no_reader_or_no_exe_is_unavailable_without_a_call
    wa = _mod()
  File "/Users/yeongyu/claude-pet-windows/windows/tests/test_win_autostart.py", line 120, in _mod
    return importlib.import_module(MODULE)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  …
ModuleNotFoundError: No module named 'windows.win_autostart'
…                                   # the other 31 ERROR blocks end in the same line (32 in total)

FAIL: test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos (…PortWiringTests…)
AssertionError: Lists differ: ['men[14 chars]menu_toggle', 'menu_roam', 'menu_reset_size', '<submenu>'] != ['men[14 chars]menu_toggle', 'menu_roam', 'menu_autostart', 'menu_reset_size']
FAIL: test_no_config_key_and_no_local_override (…PortWiringTests…)
AssertionError: 0 != 1 : expected exactly one action built from t('menu_autostart') in _context_menu, found []
FAIL: test_the_autostart_action_is_checkable (…PortWiringTests…)
AssertionError: 0 != 1 : expected exactly one action built from t('menu_autostart') in _context_menu, found []
FAIL: test_the_click_toggles_and_a_failure_reaches_the_message_box (…PortWiringTests…)
AssertionError: 0 != 1 : expected exactly one action built from t('menu_autostart') in _context_menu, found []
FAIL: test_the_menu_rereads_the_state_when_it_opens (…PortWiringTests…)
AssertionError: [] is not true : no m.aboutToShow.connect(...) in _context_menu (CONSTRUCT-ONLY)
FAIL: test_the_wiring_hands_over_the_frozen_flag_the_exe_and_the_real_registry (…PortWiringTests…)
AssertionError: 0 != 1 : expected exactly one action built from t('menu_autostart') in _context_menu, found []
FAIL: test_readme_names_the_toggle_and_the_hardware_checks (…ReadmeTests…)
AssertionError: False is not true : the README never names StartupApproved
FAIL: test_importable_the_way_the_port_imports_it (…RegistryAdapterTests…)
AssertionError: 1 != 0 : ["ModuleNotFoundError: No module named 'win_autostart'"]

----------------------------------------------------------------------
Ran 141 tests in 0.164s

FAILED (failures=8, errors=32)
exit=1
```

Reading the red: 141 = 98 pre-existing (all `ok`, so the new module disturbs nothing) + 43
new. Of the 43: **32 ERROR**, every one `ModuleNotFoundError: No module named
'windows.win_autostart'` (the module does not exist); **8 FAIL** on the port / README / bare
import, each on its own design assertion; **3 ok** — `SharedKeysTests` (a precondition on the
merge, declared so) and the two `UninstallPinTests` regression pins (declared so). The order
failure's message shows the extractor read the current menu correctly —
`['menu_settings', 'menu_toggle', 'menu_roam', 'menu_reset_size', '<submenu>']` — so that red
is the design's, not the extractor's (every `PortWiringTests` message distinguishes the two).

The full 825-line output is retained at
`/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/red-final.txt`
for as long as the session scratchpad lives.

## 4. Scratch harness — the fixtures are satisfiable, and each rival is caught (14:53–14:59Z)

§3 asks that every rival yield a distinct result; the cheapest honest check is to run the
rivals. A copy of `claude_pet.py`, `windows/*.py`, `windows/installer.iss`,
`windows/README.md` and `windows/tests/{__init__,test_win_autostart}.py` was made under the
session scratchpad (`…/scratchpad/harness/`); there — **never in the worktree** — a
reference `win_autostart.py` (with `CPW_RIVAL=<name>` switches) and a patched port copy
(`patch_port.py`, plus eight variant copies) were written. Nothing from the harness lands:
the Developer implements from the contract, not from this file, and §2 Condition B is kept
by the worktree's hashes (§1, §3). Harness hashes: reference module
`c0beaa3d…4ed9c0`, wired port copy `5e3b4c7d…72596f`, pristine port copy `bb565b08…5c6a4`
(= HEAD).

Reference implementation, same test file (`a217c549…dada6`):

```
$ python3 -m unittest windows.tests.test_win_autostart        # cwd = the harness copy
…
Ran 43 tests in 0.087s

OK
```

Pure-function rivals (`CPW_RIVAL=<name> python3 -m unittest windows.tests.test_win_autostart`;
the verdict line and the test names that caught it, subTest rows collapsed):

| rival | what it does | verdict | caught by |
| --- | --- | --- | --- |
| BARE | `run_value_for` returns the path unquoted | FAILED (failures=9) | RunValueTests ×3, ToggleTests ×4, RegistryAdapterTests.test_importable… (the subprocess printed the bare path) |
| UNQ | compare the raw value, quotes and all | FAILED (failures=17) | ReadStateTests.test_state_table rows 2/3/7, test_reads_only…, ToggleTests ×9 |
| CASE | case-sensitive compare | FAILED (failures=1) | ReadStateTests.test_state_table (row 3) |
| PRESENT | any Run value is "on" | FAILED (failures=7) | ReadStateTests ×2, ToggleTests ×3 |
| IGN-SA | ignore StartupApproved | FAILED (failures=5) | ReadStateTests ×4 (row 6, the two-locations pin, …), ToggleTests.test_disabled_in_task_manager… |
| NOFRZ | ignore `is_frozen` | FAILED (failures=4) | ReadStateTests.test_source_run…, ToggleTests.test_source_run_touches_nothing |
| RAISE | let the reader's exception out | FAILED (errors=3) | ReadStateTests.test_reader_failure…, ToggleTests.test_reader_failure… |
| NE3 | `blob[0] != 0x03` | FAILED (failures=1, errors=2) | StartupApprovedTests.test_table (`b""` → IndexError, `None` → TypeError, `"\x02"` → True) |
| KEEP-SA | rewrite Run but leave the disabled entry | FAILED (failures=3) | ToggleTests.test_disabled_in_task_manager…, test_a_foreign_path_with_a_disabled_entry, test_the_returned_state… |
| SWALLOW | writer failure reports the new state | FAILED (failures=2) | ToggleTests.test_writer_failure_turning_on/off… |
| TUPLE | reader returns `(value, type)` | FAILED (failures=1) | RegistryAdapterTests.test_reader_returns_the_value_not_the_pair |
| NF-RAISE | adapter lets `FileNotFoundError` out | FAILED (errors=1) | RegistryAdapterTests.test_reader_returns_none_for_an_absent… |
| ALL-NONE | adapter swallows every `OSError` | FAILED (failures=1) | RegistryAdapterTests.test_reader_lets_a_denied_open_out |
| EXPAND | writer uses `REG_EXPAND_SZ` | FAILED (failures=1) | RegistryAdapterTests.test_writer_sets_a_reg_sz_named_value |
| ASSUME | report the flipped state without re-reading | **OK** | nothing — not a rival under the contract; see D-W10 |

The persisted-config rival (CFG / PERSIST) is not a switch in the reference: it is caught
structurally — the `_ConfigGuard` plants `"autostart": true` in the config file and in
`RUNTIME`, and a module that consulted either would read "on" on row 1 or change the file's
bytes; the text pin additionally refuses `RUNTIME`, `merge_config_updates`, `save_config`,
`load_config`, `CONFIG_PATH`, `SETTINGS_OWNED_KEYS`, `apply_config` in the module source.

Port variants (`CLAUDE_PET_WIN_PORT_SOURCE=…/variants/<name>.py python3 -m unittest
windows.tests.test_win_autostart.PortWiringTests windows.tests.test_win_autostart.UninstallPinTests`;
the override is announced on stderr with the variant's SHA-256):

| variant | verdict | caught by |
| --- | --- | --- |
| before-roam (item added before the roam action) | FAILED (failures=1) | test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos |
| after-reset (item added after Reset size) | FAILED (failures=1) | test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos |
| plain (no `checkable=True`) | FAILED (failures=1) | test_the_autostart_action_is_checkable |
| construct-only (state read when built, no `aboutToShow`) | FAILED (failures=1) | test_the_menu_rereads_the_state_when_it_opens |
| silent-fail (error key dropped) | FAILED (failures=2) | test_the_click_toggles_and_a_failure_reaches_the_message_box, test_no_config_key_and_no_local_override |
| config (roam-style `merge_config_updates({"autostart": …})`) | FAILED (failures=1) | test_no_config_key_and_no_local_override |
| from-source (frozen flag hard-coded `True`, exe from `sys.argv[0]`) | FAILED (failures=1) | test_the_wiring_hands_over_the_frozen_flag_the_exe_and_the_real_registry |
| local-tr (`menu_autostart` redefined in `TR_WIN`) | FAILED (failures=1) | test_no_config_key_and_no_local_override |

(`silent-fail` trips the no-config pin as well because its variant also drops the
`t("autostart_title")` use that pin requires — a second, independent way it is visible.)

## 5. The macOS suite from the same tree (14:45:36Z – 14:50:06Z)

Required by the brief; the tree's `claude_pet.py` (9dd9fb12…) is not the one the
release-time hash pins were reviewed against (6f95bc8b…), so the pin family is expected red.

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"
2026-09-13T14:45:36Z
…
Ran 588 tests in 270.292s

FAILED (failures=49, errors=8, skipped=8)
exit=1
2026-09-13T14:50:06Z
```

Every failure and error is that family, and nothing else failed:

- 48 × `FAIL` in `test_upload_artifact_gate` — each carrying
  `… changed after this executable harness was reviewed; refusing to run it until a verifier
  reviews and repins the new bytes` (96 occurrences of that message across the 48).
- 8 × `ERROR: setUpClass` in `test_manual_update_transaction` — each
  `AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found
  9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61`.
- 1 × `FAIL: test_v024_version_and_final_source_pins_propagate` in `test_v024_release_contract` —
  listing exactly those two `REVIEWED_APP_SOURCE_SHA256` pins against the same two digests.
- 8 skips are the loud opt-in live checks (`CLAUDEPET_RUN_LIVE_UPDATER_TESTS`,
  `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES`, and "no built bundle at …/dist/ClaudePet.app").

Full output retained at `…/scratchpad/mac-suite.txt`. `tests/test_autostart.py` (the macOS
half's gates) passed in full in this run.

## 6. What the Developer lands, and what stays open

Developer (Track B-W), from the contract in §2 and the test module docstring:

1. `windows/win_autostart.py` — the seven names in the table, pure, importable on macOS with
   no `winreg` at module level, importable both as `windows.win_autostart` and bare
   `win_autostart` (if it needs `win_update`, the import must work both ways; the subprocess
   test runs it the way `pythonw windows\claude_pet_win.py` does).
2. `windows/claude_pet_win.py` — the wiring in §2 (the harness's shape — a checkable
   `QAction` added right after `m.addAction(roam)`, `m.aboutToShow` → a slot that re-reads
   and sets checked/enabled/text, `triggered` → a slot that toggles and shows `_msgbox` /
   `_info` with `autostart_title` / `autostart_fail` — is one shape that passes; any other
   that satisfies the pins does too). Update the `_context_menu` docstring's item order.
3. `windows/README.md` — one paragraph: the toggle; that Task Manager › Startup apps
   (작업 관리자 › 시작 앱) shows ClaudePet; that disabling it there makes the item read off;
   the `StartupApproved` first byte `0x02` / `0x03` to confirm on hardware.
4. Then `python3 -m unittest discover -s windows/tests -t . -v` from the worktree root → 141
   tests, 0 failures; the Verifier re-runs it and records the green.

Open for the Coordinator:

- **The brief's `uninstall_plan` premise is wrong** (§1, D-W6). If the Coordinator wants the
  Run-value step *in* the plan rather than in `_uninstall`, that is a design change: say so
  and the Verifier re-pins; otherwise the current mechanism is what is gated.
- **PySide6, not PyQt6** — the brief's "no PyQt6" is true but the port's dependency is PySide6
  (`windows/requirements.txt`). No effect on the tests; worth correcting in the plan text.
- **StartupApproved bytes other than `0x02` / `0x03`** are deliberately unpinned (D-W3). The
  hardware run should record what a fresh enable, a Task Manager disable and a re-enable each
  write; if a third value appears (some builds are said to write `0x06`), `startup_approved_enabled`
  and `StartupApprovedTests.test_table` change together.
- **From-source semantics** — the port's `is_frozen()` already ANDs `_WIN32`, so on this host
  the item would read unavailable even under a frozen flag; the pure functions take the flag
  as given and the pins do not depend on which expression the port passes (D-W9).
- **`delete_run_value_if_ours` and the new adapter overlap** (both open the Run key with
  `winreg`). Whether the Developer routes the uninstall's delete through `registry_writer` is
  their call; the pin only requires the identity guard and the delete to stay in `_uninstall`'s
  irreversible section.

## 7. Handoff

- `windows/tests/test_win_autostart.py` — 43 tests, `a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6`.
- This record — `docs-design/track-bw-verification-20260913.md`.
- Commands: `python3 -m unittest discover -s windows/tests -t . -v` (RED recorded above: 141
  run, failures=8, errors=32, exit 1) and `python3 -m unittest discover -s tests -v` (588 run,
  failures=49, errors=8, skipped=8 — all the hash-pin family).
- Green is not yet observed and is not claimed. It is observed by re-running the first command
  on the Developer's tree, by the Verifier, and appended here as §8.

## 8. GREEN (round 1)

Re-run by the Verifier on the Developer's tree, 2026-09-14. Worktree
`/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD still `e098516`; no git write
command was run, no production file was opened for writing by the Verifier, the GUI was not
run, and `~/.claude_pet.json` was neither read nor written (the config guard redirects
`cp.CONFIG_PATH`, `HOME` and `USERPROFILE` to a temp directory).

**Windows suite — green.**

```
$ python3 -m unittest discover -s windows/tests -t . -v
Ran 141 tests in 0.301s

OK
```

All 43 gates in `windows/tests/test_win_autostart.py` pass, and the 98 pre-existing
`test_win_update.py` tests stay green. RED for comparison (§7): 141 run, failures=8,
errors=32, exit 1.

**macOS suite — unchanged from the recorded baseline.**

```
$ python3 -m unittest discover -s tests -v
Ran 588 tests in 270.617s

FAILED (failures=49, errors=8, skipped=8)
```

Identical counts to the §5 baseline, and the same set: 48 `test_upload_artifact_gate`
failures + 1 `test_v024_release_contract` failure + 8 `test_manual_update_transaction`
`setUpClass` errors, every one carrying a hash-pin message (155 occurrences of "reviews and
repins the new bytes" / "changed after the shared-lock/version harness was reviewed" /
`REVIEWED_APP_SOURCE_SHA256` in the run). This is the pre-existing family that clears at
release-time re-pinning; nothing else fails. `tests/test_autostart.py` (the macOS half's
gates, 30 lines in the verbose log) passed in full. Full output retained at
`…/scratchpad/mac-suite-round1.txt`.

**Extra checks required by the round-1 brief.**

- `python3 -c "import sys; sys.path.insert(0,'windows'); import win_autostart"` → imports,
  and reports `RUN_SUBKEY = Software\Microsoft\Windows\CurrentVersion\Run`,
  `RUN_VALUE_NAME = ClaudePet`, `real_registry() = (None, None)` on this host.
- `python3 -m py_compile windows/claude_pet_win.py` → clean.

**Tree state observed.**

- `windows/tests/test_win_autostart.py` —
  `a217c549683dfbe42b11a0e05bb81c3c5bd03ba66b76bea7c2b4c43e8a8dada6`, byte-identical to the
  hash handed over in §7: the Developer did not touch the Verifier's tests.
- `claude_pet.py`, `windows/win_update.py`, `windows/installer.iss`, `tests/test_autostart.py`
  — identical to HEAD (`git diff --quiet HEAD -- <path>`).
- Changed by the Developer: `windows/claude_pet_win.py` (M), `windows/README.md` (M),
  `windows/build_win.py` (M — the `win_autostart` hidden-import), `windows/win_autostart.py`
  (new, `9f3f8fb9d369326c171f369dbfdb18e56224db2659410d91f337fc4e8a0c33cb`). No untracked file
  the Verifier did not create was touched.

**Read against the implementation, beyond the gates.**

- Menu parity holds in the source as well as in the AST pin: the Windows item is
  `QAction(cp.t("menu_autostart"), m, checkable=True)` added immediately after
  `m.addAction(roam)` and before `m.addAction(cp.t("menu_reset_size"), …)`, which is the macOS
  `rightMouseDown_` order (`menu_roam`, `menu_autostart`, `menu_reset_size`). Same TR key,
  same position, no `TR_WIN` override.
- `m.aboutToShow` is connected before `m.exec(gpos)` (the menu is shown with `exec`, which
  emits the signal), so the state is re-read from the registry on every open.
- `_toggle_autostart` takes no `checked` argument, matching the existing `_toggle_roam`
  precedent for a PySide6 `triggered` connection.
- `wu.log_update("startup", status=…, error=…)` logs a state word and an error key only — no
  path, no identifier (CLAUDE.md § Privacy).
- The `uninstall_plan` premise correction from §1/D-W6 still holds and is pinned: the plan is
  a file plan, the Run-value delete stays in `_uninstall`'s irreversible section behind
  `run_value_is_ours`.

**Verdict: GREEN (round 1).** The open items in §6 are unchanged — the StartupApproved byte
encoding (`0x02` / `0x03`) is still the one fact only the hardware run can settle, and
`windows/README.md`'s "실기에서 확인할 것" list now carries it.
