# Verification record — Track B "Start at sign-in", macOS half (v0.25 follow-ups)

Verifier: verifier-b (Claude), VERIFIER role only on this track. Record opened
2026-09-13T01:50Z. Worktree `/Users/yeongyu/claude-pet-autostart`, branch `autostart`,
HEAD `13710db` — not `/Users/yeongyu/claude-pet`. This file is untracked and is not
committed by the Verifier; the Coordinator stages by named paths.

Inputs: `docs-design/followups-v025-plan-20260913.md` § "Track B" (read in
`/Users/yeongyu/claude-pet`; not in this worktree), the survey report key `autostart` in
the session scratchpad `followups-survey.json`, AGENTS.md §2 / §3 / §5, CLAUDE.md (Danger
zone — the settings panel is a fixed-height 612 pt view, so the toggle lives in the
right-click menu; Privacy).

Files the Verifier wrote: `tests/test_autostart.py` (new) and this record. Nothing else.
Production files were not opened for writing; the user-owned untracked files (`diag.py`,
`release/ClaudePet.iconset/`, `release/icon_1024.png`) were not touched. No git write
command was run. The GUI was not run. Nothing was registered with or unregistered from
the real `SMAppService` — tests use fake service objects and the module installs a
tripwire in `sys.modules["ServiceManagement"]` whose register / unregister raise.
`~/.claude_pet.json` was neither read nor written (the module only `stat`s it at import
and teardown; `CONFIG_PATH` and `HOME` are redirected to a temp directory).

All commands ran with cwd `/Users/yeongyu/claude-pet-autostart`. Times are UTC.
Output blocks are verbatim.

## 1. The tree under verification (01:50–01:57Z)

```
$ git rev-parse --short HEAD ; git branch --show-current ; git status --porcelain
13710db
autostart
?? tests/test_autostart.py            # (after authoring; empty before)
$ shasum -a 256 claude_pet.py setup.py ; git show HEAD:claude_pet.py | shasum -a 256
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py
007421e64d90db93cae6ac1d3e7d6a42f9348b970b63c9caff7a881abe0c22a4  setup.py
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -   (HEAD:claude_pet.py)
```

`claude_pet.py` is byte-identical to HEAD before, during and after the red run
(re-hashed at 01:54Z, 01:56Z and 01:57Z — same digest), so the red below is against the
unfixed code (AGENTS.md §3 step 2).

Symbols located by `grep -n` (line numbers approximate by CLAUDE.md's own rule):
`TR` l.1042 with `"en"` 1043 / `"ko"` 1124 / `"ja"` 1201 / `"es"` 1283 and `menu_roam` in
each block; `t()` l.1028 falls back to English for a missing key; `RUNTIME` l.978;
`apply_config` l.1001 (fixed copy list, no `autostart`); `SETTINGS_OWNED_KEYS` l.1446;
`CONFIG_PATH` l.1389; `merge_config_updates` l.1490; `save_config` l.1410;
`_acquire_update_lock` l.3077; `_lock_root_fd` l.3024; `UPDATE_LOCK_DIR` l.3181;
`UNINSTALL_PATHS` l.4890; `uninstall_targets` l.4904; `app_bundle_path` l.4921
(in-function `from Foundation import NSBundle`); `do_uninstall` l.4979 (lock → identity
→ `subprocess.Popen` of the deletion shell → `_discard_owned_path` loop; docstring: every
step that can still refuse comes before the irreversible section); `rightMouseDown_`
l.6559 (tuple list `menu_settings, menu_toggle, menu_roam, menu_reset_size, None,
menu_uninstall, menu_quit`; roam item sets `setState_` / `setEnabled_`; Pets submenu
`insertItem_atIndex_(pet_item, 4)` "after Reset size"); `Handler.toggleRoam_` l.7476
(`merge_config_updates({"roam": value})` — the shape Track B must **not** copy);
`Handler.uninstallApp_` l.7506 (shows `t("unin_fail")` when `do_uninstall` returns a
truthy error). `setup.py` l.34: `"includes": ["Foundation", "AppKit", "Quartz"]` — no
`ServiceManagement`. Grep for `ServiceManagement|autostart|SMAppService` in
`claude_pet.py`: no hits.

ServiceManagement probe (import and attribute checks only — `mainAppService()` was not
called):

```
$ python3 -c 'import ServiceManagement as SM, objc; ...'
True 0 1 2 3          # SMAppService present; NotRegistered/Enabled/RequiresApproval/NotFound
mainAppService True / registerAndReturnError_ True / unregisterAndReturnError_ True / status True / openSystemSettingsLoginItems True
pyobjc 12.2.1
```

## 2. Surface pinned, and the decisions taken where the design left a choice

Module-level names in `claude_pet.py` (the full contract is in the module docstring of
`tests/test_autostart.py`; this is the Developer's checklist):

| name | contract |
| --- | --- |
| `autostart_state(status, is_bundle)` | `0→"off"`, `1→"on"`, `2→"approval"`, `3→"unavailable"`; `is_bundle` False → `"unavailable"` for every status. Pure. |
| `autostart_toggle(service, is_bundle)` | `(new_state, error_key\|None)`. Off → `service.registerAndReturnError_(None)`; on → `service.unregisterAndReturnError_(None)`; the new state is **read back** via `service.status()`, so a register that lands on 2 returns `("approval", None)`. `(False, err)` → `(unchanged_state, "autostart_fail")`. Not a bundle → `("unavailable", None)` with **no** call on the service, not even `status()`. `service is None` → `("unavailable", None)`. |
| `autostart_service()` | `SMAppService.mainAppService()`, or `None` when `ServiceManagement` cannot be imported or lacks `SMAppService`. Resolved **at call time** (precedent: `app_bundle_path()`'s in-function import) — a module-level binding would defeat the test's `sys.modules` patching and the tripwire. The **only** call site of `mainAppService`. |
| `uninstall_autostart(service)` | `error_key\|None`. Unregisters only when `status()` is 1 or 2; `None` / 0 / 3 → no call, `None`. `(False, err)` → `"autostart_fail"`. |
| `do_uninstall()` | calls `uninstall_autostart(autostart_service())` **after** the update lock is held and **before** `Popen` / any `_discard_owned_path`; only when `app_bundle_path()` is truthy. |
| TR keys | `menu_autostart`, `autostart_title`, `autostart_approval`, `autostart_open_settings`, `autostart_fail`, `autostart_unavailable` in en/ko/ja/es. |
| menu | `t("menu_autostart")` between `menu_roam` and `menu_reset_size` in `rightMouseDown_`'s tuple list; the Pets `insertItem_atIndex_` constant becomes `index(menu_reset_size)+1` (= 5); the selector names a `Handler` method that reaches `autostart_toggle` by name; `openSystemSettingsLoginItems` referenced somewhere (the approval alert's button). |
| `setup.py` | `"ServiceManagement"` in the py2app `includes` list. |

Decisions on the survey's open questions, taken by the Verifier so that the tests pin one
behaviour each. The Coordinator can override any of them; an override changes an
assertion, so it goes back through the Verifier (§2 Condition A), not the Developer.

- **D1 — uninstall when unregister fails: refuse.** `do_uninstall()` returns
  `(False, <non-empty str>)`, spawns no deletion helper and deletes nothing. Ground:
  `do_uninstall`'s own contract ("every step that can still refuse comes before the
  irreversible section"); refusing leaves a consistent installation (app + login item,
  both present) that the user can repair from System Settings and retry, whereas
  proceeding leaves a login item pointing at a deleted bundle. The existing
  `uninstallApp_` alert path already shows `unin_fail` for any truthy error.
- **D2 — toggle from status 2 (RequiresApproval): never unregister**; return
  `("approval", None)` so the handler shows the approval alert. Re-registering is
  permitted (the fake keeps status 2 across a re-register, as the OS does until the user
  approves). The rival "non-zero is on → unregister" would silently remove a pending
  registration when the user clicked to enable.
- **D3 — `uninstall_autostart` skips 0 and 3.** An unconditional unregister fails for
  every user who never enabled the item, and under D1 that failure would refuse *their*
  uninstall. The fake's unregister fails from 0 / 3 as the OS does, so this rival is
  visible as an error and not only as an extra call.
- **D4 — from source, neither the toggle nor `do_uninstall` touches the service**
  (`status()` included). `mainAppService()` from source is Python.app's own service;
  the design's `app_bundle_path()` gate applies to the whole feature.
- **D5 — no persisted key.** `SETTINGS_OWNED_KEYS`, `apply_config`,
  `merge_config_updates`, `save_config`, the config bytes and `RUNTIME` are all asserted
  untouched across every toggle (design X; survey rival Y rejected by the plan).
- **D6 — locale strings:** per key the four locale strings are pairwise distinct
  (English pasted into ko/ja/es passes `t()`'s fallback and would otherwise be invisible);
  the four message keys are pairwise distinct within each locale; `menu_autostart` and
  `autostart_title` **may** coincide (the survey's suggested strings do); `menu_autostart`
  is 1–24 characters; all six keys are used through `t("…")` somewhere in the source.
- **D7 — macOS 12:** `autostart_service()` is `None` when `SMAppService` is absent and
  `autostart_toggle(None, True)` is `("unavailable", None)` — the disabled-item option
  from the plan, no LaunchAgent fallback.

## 3. Red run (AGENTS.md §3 step 2)

Two fixture corrections were made while authoring, both before any production change,
both recorded here so the red is not retrospective:

1. 01:53:27Z first run: 28 tests, 26 failures. `test_menu_title_fits_the_menu` passed
   **vacuously** (no key → empty string ≤ 24) — the §3 non-discriminating hazard. Changed
   to require the key's presence in every locale as well as the length bound.
2. 01:56Z scratch harness (§4) showed `test_busy_lock_refuses_before_touching_the_service`
   failing under the *reference* implementation: the fake shares its `calls` list with
   the event recorders, so `method_calls()` saw the `"lock"` event. The assertion now
   filters by event name, as the other two ordering tests already did.

Final red run, `claude_pet.py` at 6f95bc8b…, `setup.py` at 007421e6…,
`tests/test_autostart.py` at 6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; python3 -m unittest tests.test_autostart -v ; echo "exit=$?"
2026-09-13T01:57:06Z
test_each_key_is_translated_not_copied_across_locales (tests.test_autostart.AutostartLocalizationTests.test_each_key_is_translated_not_copied_across_locales)
R12: a string pasted into ko/ja/es unchanged would pass t()'s fallback. ... FAIL
test_every_locale_defines_every_key (tests.test_autostart.AutostartLocalizationTests.test_every_locale_defines_every_key) ... FAIL
test_menu_title_fits_the_menu (tests.test_autostart.AutostartLocalizationTests.test_menu_title_fits_the_menu)
Present in every locale and at most MENU_TITLE_MAX characters. ... FAIL
test_message_keys_differ_within_each_locale (tests.test_autostart.AutostartLocalizationTests.test_message_keys_differ_within_each_locale)
approval / open_settings / fail / unavailable are four different messages. ... FAIL
test_framework_without_smappservice_yields_none (tests.test_autostart.AutostartServiceTests.test_framework_without_smappservice_yields_none) ... FAIL
test_missing_framework_yields_none (tests.test_autostart.AutostartServiceTests.test_missing_framework_yields_none) ... FAIL
test_returns_the_main_app_service_object (tests.test_autostart.AutostartServiceTests.test_returns_the_main_app_service_object) ... FAIL
test_no_config_key_exists_for_the_feature (tests.test_autostart.AutostartStateTests.test_no_config_key_exists_for_the_feature)
Nothing in the settings contract or apply_config carries "autostart". ... ok
test_persisted_preference_does_not_influence_state (tests.test_autostart.AutostartStateTests.test_persisted_preference_does_not_influence_state)
OS is the source of truth (design X); a stored preference is not (R8). ... FAIL
test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
The whole 4 × 2 table at once, so the diff shows every wrong cell. ... FAIL
test_from_requires_approval_never_unregisters (tests.test_autostart.AutostartToggleTests.test_from_requires_approval_never_unregisters) ... FAIL
test_missing_framework_is_unavailable_without_error (tests.test_autostart.AutostartToggleTests.test_missing_framework_is_unavailable_without_error) ... FAIL
test_off_registers_and_reads_the_new_state_back (tests.test_autostart.AutostartToggleTests.test_off_registers_and_reads_the_new_state_back) ... FAIL
test_on_unregisters (tests.test_autostart.AutostartToggleTests.test_on_unregisters) ... FAIL
test_register_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_register_failure_is_reported_not_swallowed) ... FAIL
test_register_that_lands_on_requires_approval_reports_approval (tests.test_autostart.AutostartToggleTests.test_register_that_lands_on_requires_approval_reports_approval) ... FAIL
test_source_run_never_touches_the_service (tests.test_autostart.AutostartToggleTests.test_source_run_never_touches_the_service) ... FAIL
test_unregister_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_unregister_failure_is_reported_not_swallowed) ... FAIL
test_every_new_key_is_used_through_t (tests.test_autostart.AutostartWiringTests.test_every_new_key_is_used_through_t) ... FAIL
test_menu_item_follows_roam_and_precedes_reset_size (tests.test_autostart.AutostartWiringTests.test_menu_item_follows_roam_and_precedes_reset_size)
Placement A: `t("menu_autostart")` directly after Roam, before Reset size. ... FAIL
test_menu_item_has_a_handler_that_uses_the_pure_toggle (tests.test_autostart.AutostartWiringTests.test_menu_item_has_a_handler_that_uses_the_pure_toggle)
R13: an item whose selector no Handler method implements does nothing. ... FAIL
test_registration_calls_live_only_in_the_pure_helpers (tests.test_autostart.AutostartWiringTests.test_registration_calls_live_only_in_the_pure_helpers)
R9: no register / unregister inside run_gui or do_uninstall, one service seam. ... FAIL
test_setup_py_bundles_servicemanagement (tests.test_autostart.AutostartWiringTests.test_setup_py_bundles_servicemanagement)
R14: py2app only ships listed frameworks; without this the bundle's item is ... FAIL
test_busy_lock_refuses_before_touching_the_service (tests.test_autostart.DoUninstallOrderingTests.test_busy_lock_refuses_before_touching_the_service) ... FAIL
test_source_run_uninstall_does_not_touch_the_service (tests.test_autostart.DoUninstallOrderingTests.test_source_run_uninstall_does_not_touch_the_service) ... FAIL
test_unregister_failure_refuses_with_nothing_deleted (tests.test_autostart.DoUninstallOrderingTests.test_unregister_failure_refuses_with_nothing_deleted) ... FAIL
test_unregister_runs_after_the_lock_and_before_the_irreversible_section (tests.test_autostart.DoUninstallOrderingTests.test_unregister_runs_after_the_lock_and_before_the_irreversible_section) ... FAIL
test_helper_table (tests.test_autostart.UninstallAutostartHelperTests.test_helper_table)
uninstall_autostart(service) -> error_key | None. ... FAIL

======================================================================
FAIL: test_each_key_is_translated_not_copied_across_locales (tests.test_autostart.AutostartLocalizationTests.test_each_key_is_translated_not_copied_across_locales)
R12: a string pasted into ko/ja/es unchanged would pass t()'s fallback.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 633, in test_each_key_is_translated_not_copied_across_locales
    self.assertEqual(copied, [])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: Lists differ: [('menu_autostart', [None, None, None, Non[250 chars]ne])] != []

First list contains 6 additional elements.
First extra element 0:
('menu_autostart', [None, None, None, None])

+ []
- [('menu_autostart', [None, None, None, None]),
-  ('autostart_title', [None, None, None, None]),
-  ('autostart_approval', [None, None, None, None]),
-  ('autostart_open_settings', [None, None, None, None]),
-  ('autostart_fail', [None, None, None, None]),
-  ('autostart_unavailable', [None, None, None, None])]

======================================================================
FAIL: test_every_locale_defines_every_key (tests.test_autostart.AutostartLocalizationTests.test_every_locale_defines_every_key)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 621, in test_every_locale_defines_every_key
    self.assertEqual(missing, [])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
AssertionError: Lists differ: [('en', 'menu_autostart'), ('en', 'autosta[661 chars]le')] != []

First list contains 24 additional elements.
First extra element 0:
('en', 'menu_autostart')

Diff is 785 characters long. Set self.maxDiff to None to see it.

======================================================================
FAIL: test_menu_title_fits_the_menu (tests.test_autostart.AutostartLocalizationTests.test_menu_title_fits_the_menu)
Present in every locale and at most MENU_TITLE_MAX characters.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 658, in test_menu_title_fits_the_menu
    self.assertEqual(bad, {}, f"menu_autostart missing or longer than {MENU_TITLE_MAX}")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'en': None, 'ko': None, 'ja': None, 'es': None} != {}
- {'en': None, 'es': None, 'ja': None, 'ko': None}
+ {} : menu_autostart missing or longer than 24

======================================================================
FAIL: test_message_keys_differ_within_each_locale (tests.test_autostart.AutostartLocalizationTests.test_message_keys_differ_within_each_locale)
approval / open_settings / fail / unavailable are four different messages.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 646, in test_message_keys_differ_within_each_locale
    self.assertEqual(dupes, [])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^
AssertionError: Lists differ: [('en', [None, None, None, None]), ('ko', [89 chars]ne])] != []

First list contains 4 additional elements.
First extra element 0:
('en', [None, None, None, None])

+ []
- [('en', [None, None, None, None]),
-  ('ko', [None, None, None, None]),
-  ('ja', [None, None, None, None]),
-  ('es', [None, None, None, None])]

======================================================================
FAIL: test_framework_without_smappservice_yields_none (tests.test_autostart.AutostartServiceTests.test_framework_without_smappservice_yields_none)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 456, in test_framework_without_smappservice_yields_none
    fn = _require(self, "autostart_service")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service

======================================================================
FAIL: test_missing_framework_yields_none (tests.test_autostart.AutostartServiceTests.test_missing_framework_yields_none)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 451, in test_missing_framework_yields_none
    fn = _require(self, "autostart_service")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service

======================================================================
FAIL: test_returns_the_main_app_service_object (tests.test_autostart.AutostartServiceTests.test_returns_the_main_app_service_object)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 462, in test_returns_the_main_app_service_object
    fn = _require(self, "autostart_service")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service

======================================================================
FAIL: test_persisted_preference_does_not_influence_state (tests.test_autostart.AutostartStateTests.test_persisted_preference_does_not_influence_state)
OS is the source of truth (design X); a stored preference is not (R8).
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 340, in test_persisted_preference_does_not_influence_state
    fn = _require(self, "autostart_state")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_state

======================================================================
FAIL: test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
The whole 4 × 2 table at once, so the diff shows every wrong cell.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 326, in test_status_and_bundle_table
    fn = _require(self, "autostart_state")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_state

======================================================================
FAIL: test_from_requires_approval_never_unregisters (tests.test_autostart.AutostartToggleTests.test_from_requires_approval_never_unregisters)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 411, in test_from_requires_approval_never_unregisters
    result = self.toggle(svc)
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_missing_framework_is_unavailable_without_error (tests.test_autostart.AutostartToggleTests.test_missing_framework_is_unavailable_without_error)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 435, in test_missing_framework_is_unavailable_without_error
    self.assertEqual(self.toggle(None, is_bundle=True), ("unavailable", None))
                     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_off_registers_and_reads_the_new_state_back (tests.test_autostart.AutostartToggleTests.test_off_registers_and_reads_the_new_state_back)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 393, in test_off_registers_and_reads_the_new_state_back
    self.assertEqual((self.toggle(svc), svc.method_calls()),
                      ~~~~~~~~~~~^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_on_unregisters (tests.test_autostart.AutostartToggleTests.test_on_unregisters)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 399, in test_on_unregisters
    self.assertEqual((self.toggle(svc), svc.method_calls()),
                      ~~~~~~~~~~~^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_register_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_register_failure_is_reported_not_swallowed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 418, in test_register_failure_is_reported_not_swallowed
    self.assertEqual((self.toggle(svc), svc.method_calls()),
                      ~~~~~~~~~~~^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_register_that_lands_on_requires_approval_reports_approval (tests.test_autostart.AutostartToggleTests.test_register_that_lands_on_requires_approval_reports_approval)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 405, in test_register_that_lands_on_requires_approval_reports_approval
    self.assertEqual((self.toggle(svc), svc.method_calls()),
                      ~~~~~~~~~~~^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_source_run_never_touches_the_service (tests.test_autostart.AutostartToggleTests.test_source_run_never_touches_the_service)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 430, in test_source_run_never_touches_the_service
    self.assertEqual((self.toggle(svc, is_bundle=False), svc.calls),
                      ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_unregister_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_unregister_failure_is_reported_not_swallowed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 424, in test_unregister_failure_is_reported_not_swallowed
    self.assertEqual((self.toggle(svc), svc.method_calls()),
                      ~~~~~~~~~~~^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 388, in toggle
    fn = _require(self, "autostart_toggle")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_toggle

======================================================================
FAIL: test_every_new_key_is_used_through_t (tests.test_autostart.AutostartWiringTests.test_every_new_key_is_used_through_t)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 808, in test_every_new_key_is_used_through_t
    self.assertEqual([k for k in TR_KEYS if k not in used], [])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: ['menu_autostart', 'autostart_title', 'aut[82 chars]ble'] != []

First list contains 6 additional elements.
First extra element 0:
'menu_autostart'

+ []
- ['menu_autostart',
-  'autostart_title',
-  'autostart_approval',
-  'autostart_open_settings',
-  'autostart_fail',
-  'autostart_unavailable']

======================================================================
FAIL: test_menu_item_follows_roam_and_precedes_reset_size (tests.test_autostart.AutostartWiringTests.test_menu_item_follows_roam_and_precedes_reset_size)
Placement A: `t("menu_autostart")` directly after Roam, before Reset size.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 758, in test_menu_item_follows_roam_and_precedes_reset_size
    self.assertIn("menu_autostart", keys, keys)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'menu_autostart' not found in ['menu_settings', 'menu_toggle', 'menu_roam', 'menu_reset_size', None, 'menu_uninstall', 'menu_quit'] : ['menu_settings', 'menu_toggle', 'menu_roam', 'menu_reset_size', None, 'menu_uninstall', 'menu_quit']

======================================================================
FAIL: test_menu_item_has_a_handler_that_uses_the_pure_toggle (tests.test_autostart.AutostartWiringTests.test_menu_item_has_a_handler_that_uses_the_pure_toggle)
R13: an item whose selector no Handler method implements does nothing.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 775, in test_menu_item_has_a_handler_that_uses_the_pure_toggle
    self.assertTrue(isinstance(selector, str) and selector.endswith(":"),
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    f"menu_autostart selector: {selector!r}")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : menu_autostart selector: None

======================================================================
FAIL: test_registration_calls_live_only_in_the_pure_helpers (tests.test_autostart.AutostartWiringTests.test_registration_calls_live_only_in_the_pure_helpers)
R9: no register / unregister inside run_gui or do_uninstall, one service seam.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 792, in test_registration_calls_live_only_in_the_pure_helpers
    self.assertEqual(
    ~~~~~~~~~~~~~~~~^
        (sites["mainAppService"],
        ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<9 lines>...
        "openSystemSettingsLoginItems referenced, do_uninstall uses "
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        f"uninstall_autostart) — sites: {sites}")
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (set(), False, set(), False, set(), False, False) != ({'autostart_service'}, True, set(), True, set(), True, True)

First differing element 0:
set()
{'autostart_service'}

- (set(), False, set(), False, set(), False, False)
+ ({'autostart_service'}, True, set(), True, set(), True, True) : (mainAppService sites, register called anywhere, register in GUI/uninstall, unregister called anywhere, unregister in GUI/uninstall, openSystemSettingsLoginItems referenced, do_uninstall uses uninstall_autostart) — sites: {'mainAppService': set(), 'registerAndReturnError_': set(), 'unregisterAndReturnError_': set(), 'openSystemSettingsLoginItems': set()}

======================================================================
FAIL: test_setup_py_bundles_servicemanagement (tests.test_autostart.AutostartWiringTests.test_setup_py_bundles_servicemanagement)
R14: py2app only ships listed frameworks; without this the bundle's item is
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 813, in test_setup_py_bundles_servicemanagement
    self.assertIn("ServiceManagement", _setup_includes() or [])
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'ServiceManagement' not found in ['Foundation', 'AppKit', 'Quartz']

======================================================================
FAIL: test_busy_lock_refuses_before_touching_the_service (tests.test_autostart.DoUninstallOrderingTests.test_busy_lock_refuses_before_touching_the_service)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 598, in test_busy_lock_refuses_before_touching_the_service
    result = self.run_uninstall(fake)
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 546, in run_uninstall
    _require(self, "autostart_service", "uninstall_autostart")
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service, uninstall_autostart

======================================================================
FAIL: test_source_run_uninstall_does_not_touch_the_service (tests.test_autostart.DoUninstallOrderingTests.test_source_run_uninstall_does_not_touch_the_service)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 605, in test_source_run_uninstall_does_not_touch_the_service
    result = self.run_uninstall(fake, bundle=False)
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 546, in run_uninstall
    _require(self, "autostart_service", "uninstall_autostart")
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service, uninstall_autostart

======================================================================
FAIL: test_unregister_failure_refuses_with_nothing_deleted (tests.test_autostart.DoUninstallOrderingTests.test_unregister_failure_refuses_with_nothing_deleted)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 583, in test_unregister_failure_refuses_with_nothing_deleted
    result = self.run_uninstall(fake)
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 546, in run_uninstall
    _require(self, "autostart_service", "uninstall_autostart")
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service, uninstall_autostart

======================================================================
FAIL: test_unregister_runs_after_the_lock_and_before_the_irreversible_section (tests.test_autostart.DoUninstallOrderingTests.test_unregister_runs_after_the_lock_and_before_the_irreversible_section)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 570, in test_unregister_runs_after_the_lock_and_before_the_irreversible_section
    result = self.run_uninstall(fake)
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 546, in run_uninstall
    _require(self, "autostart_service", "uninstall_autostart")
    ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: autostart_service, uninstall_autostart

======================================================================
FAIL: test_helper_table (tests.test_autostart.UninstallAutostartHelperTests.test_helper_table)
uninstall_autostart(service) -> error_key | None.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 493, in test_helper_table
    fn = _require(self, "uninstall_autostart")
  File "/Users/yeongyu/claude-pet-autostart/tests/test_autostart.py", line 261, in _require
    test.fail("claude_pet does not define: " + ", ".join(missing))
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: claude_pet does not define: uninstall_autostart

----------------------------------------------------------------------
Ran 28 tests in 0.065s

FAILED (failures=27)
exit=1
```

28 tests: 27 FAIL, 1 ok. The one green is `test_no_config_key_exists_for_the_feature`, an
absence guard ("autostart" must never enter `SETTINGS_OWNED_KEYS` / `apply_config`); its
red state is obtained against the rival in §4 (row "R8 key in owned/apply_config"). Every
other test fails on the missing names or the missing strings / menu entry / include —
the first red the survey predicted (test item 11). The discriminating reds — status
table, OS-is-truth, identity guard, ordering — are demonstrated by execution in §4
rather than only by the tables in the docstrings.

## 4. Discrimination check by execution (scratch, 01:55–01:57Z)

`<scratchpad>/rivals_check.py` (not in the repository) imports `tests.test_autostart`
and, **in its own process only**, binds a scratch *reference* implementation and then
each named rival onto the imported `claude_pet` module with `setattr`, running the
pure-function test classes under each. `do_uninstall` variants are produced by inserting
the `uninstall_autostart(autostart_service())` call into `inspect.getsource(do_uninstall)`
at three anchors (before the lock / after the identity read, before `Popen` / before the
delete loop) and `exec`-ing the result into the module namespace of that process; the file
on disk is untouched (hash unchanged at 01:57Z). The reference is scratch code, not a
proposal for the production shape.

```
$ python3 <scratchpad>/rivals_check.py ; echo "exit=$?"
== AutostartStateTests ==
reference                          ok    ok    ok      (3 run, 0 not ok)
  columns: [1] test_no_config_key_exists_for_the_feature, [2] test_persisted_preference_does_not_influence_state, [3] test_status_and_bundle_table
R1 non-zero is on                  ok    ok    FAIL    (3 run, 1 not ok)
R2 only 1 is on                    ok    ok    FAIL    (3 run, 1 not ok)
R3 is_bundle ignored               ok    ok    FAIL    (3 run, 1 not ok)
R4 NotFound -> off                 ok    ok    FAIL    (3 run, 1 not ok)
R8 preference wins                 ok    FAIL  FAIL    (3 run, 2 not ok)
R8 preference OR os                ok    FAIL  ok      (3 run, 1 not ok)
R8 key in owned/apply_config       FAIL  ok    ok      (3 run, 1 not ok)

== AutostartToggleTests ==
reference                          ok    ok    ok    ok    ok    ok    ok    ok      (8 run, 0 not ok)
  columns: [1] test_from_requires_approval_never_unregisters, [2] test_missing_framework_is_unavailable_without_error, [3] test_off_registers_and_reads_the_new_state_back, [4] test_on_unregisters, [5] test_register_failure_is_reported_not_swallowed, [6] test_register_that_lands_on_requires_approval_reports_approval, [7] test_source_run_never_touches_the_service, [8] test_unregister_failure_is_reported_not_swallowed
R1 non-zero is on                  FAIL  ok    ok    ok    ok    FAIL  ok    ok      (8 run, 2 not ok)
R5 state assumed                   ok    ok    ok    ok    ok    FAIL  ok    ok      (8 run, 1 not ok)
R6 errors swallowed                ok    ok    ok    ok    FAIL  ok    ok    FAIL    (8 run, 2 not ok)
R7 no bundle gate                  ok    ok    ok    ok    ok    ok    FAIL  ok      (8 run, 1 not ok)
R8 persists preference             ok    ok    FAIL  FAIL  ok    ok    ok    ok      (8 run, 2 not ok)

== AutostartServiceTests ==
reference                          ok    ok    ok      (3 run, 0 not ok)
  columns: [1] test_framework_without_smappservice_yields_none, [2] test_missing_framework_yields_none, [3] test_returns_the_main_app_service_object

== UninstallAutostartHelperTests ==
reference                          ok      (1 run, 0 not ok)
  columns: [1] test_helper_table
R10 unconditional                  ERROR   (1 run, 1 not ok)
R6 errors swallowed                FAIL    (1 run, 1 not ok)

== DoUninstallOrderingTests ==
reference (after id, before Popen) ok    ok    ok    ok      (4 run, 0 not ok)
  columns: [1] test_busy_lock_refuses_before_touching_the_service, [2] test_source_run_uninstall_does_not_touch_the_service, [3] test_unregister_failure_refuses_with_nothing_deleted, [4] test_unregister_runs_after_the_lock_and_before_the_irreversible_section
R11 before the lock                FAIL  ok    ok    FAIL    (4 run, 2 not ok)
R11 after Popen                    ok    ok    FAIL  FAIL    (4 run, 2 not ok)
R11 failure ignored                ok    ok    FAIL  ok      (4 run, 1 not ok)
R7 no bundle gate (before lock)    FAIL  FAIL  ok    FAIL    (4 run, 3 not ok)
R7 no bundle gate (after Popen)    ok    FAIL  FAIL  FAIL    (4 run, 3 not ok)
unchanged do_uninstall (HEAD)      ok    ok    FAIL  FAIL    (4 run, 2 not ok)
exit=0
```

Reading: the reference is green on all 19 pure tests across the five classes; each rival
fails at least one test, and the rivals a single-value fixture would let through (R1 at
status 1, R2 at status 0, R8-OR with a True preference, "state assumed" with a register
that succeeds and lands on 1) are each caught by a different row. The unchanged HEAD
`do_uninstall` fails the refusal and ordering tests and passes the two "does not touch the
service" tests — as it should, since it touches nothing.

The AST / TR / `setup.py` tests (`AutostartLocalizationTests`, `AutostartWiringTests`)
read the source and cannot be exercised by injection; their red is the missing strings,
the missing menu entry (`['menu_settings', 'menu_toggle', 'menu_roam', 'menu_reset_size',
None, 'menu_uninstall', 'menu_quit']`), the missing selector, the empty call-site sets and
`['Foundation', 'AppKit', 'Quartz']`, all in §3.

## 5. Isolation of the module (what it can and cannot reach)

- `setUpModule` redirects `HOME`, `TMPDIR`, `claude_pet.CONFIG_PATH` and
  `claude_pet.UPDATE_LOCK_DIR` into a realpath temp directory; `tempfile.tempdir` too.
- `sys.modules["ServiceManagement"]` is a fake module whose `SMAppService.mainAppService()`
  returns a tripwire (register / unregister raise `AssertionError`); if the Developer
  binds `claude_pet.SMAppService` at import, that name is patched to the tripwire as well.
  The three `AutostartServiceTests` swap in their own fake module per test.
- `DoUninstallOrderingTests` takes the update lock for real under the temp
  `UPDATE_LOCK_DIR`, replaces `subprocess.Popen` with a recorder (nothing spawned),
  wraps `_discard_owned_path` (real deletion of temp sentinels only) and patches
  `app_bundle_path` / `autostart_service`.
- The real `~/.claude_pet.json` is `stat`ed at import and teardown: created / deleted →
  hard failure; a changed stat → loud stderr warning (a running pet rewrites its config on
  a drag, so a hard failure there would misattribute).
- Suite-wide: `tests/test_upload_artifact_gate.py` pins the SHA256 of `claude_pet.py`
  and will refuse once the Developer changes it — expected; the Verifier re-pins it at the
  GREEN stage after reading the diff, not before.

## 6. Full-suite baseline with the new module present

Run from the worktree root (CLAUDE.md: `python3 -m unittest` needs cwd on `sys.path`),
started 2026-09-13T01:55:03Z, finished 02:00:28Z, `claude_pet.py` still at 6f95bc8b… when
it ended:

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"
… (593 test lines; full output kept in the session scratchpad as full-suite-red-stage.txt)
Ran 593 tests in 325.141s
FAILED (failures=27, skipped=8)
exit=1
```

Failures by module (from the `FAIL:` / `ERROR:` headers): `test_autostart` 27 — every
one of the 27 is in the new module, none elsewhere, so the module's `sys.modules` /
`HOME` / `CONFIG_PATH` / `UPDATE_LOCK_DIR` patching disturbs no other module and the
tree's baseline is green apart from Track B. `tests/test_upload_artifact_gate.py` (23
tests) passed because `claude_pet.py` is unchanged; it refuses once the Developer edits
the file, by design.

The 8 skips are the pre-existing loud ones, unrelated to Track B:

```
skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'
test_py2app_bundle_carries_every_asset (test_v020_boundaries.B2Bundle.test_py2app_bundle_carries_every_asset) ... skipped 'no built bundle at /Users/yeongyu/claude-pet-autostart/dist/ClaudePet.app/Contents/Resources/.claude_pet'
test_github_choice_binds_v021_tag_asset_and_arch_without_network (test_v020_boundaries.B3Updater.test_github_choice_binds_v021_tag_asset_and_arch_without_network) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_invalid_candidates_are_refused_before_handoff (test_v020_boundaries.B3Updater.test_invalid_candidates_are_refused_before_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
test_well_formed_v021_reaches_one_sandbox_handoff (test_v020_boundaries.B3Updater.test_well_formed_v021_reaches_one_sandbox_handoff) ... skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'
```

No `[test_autostart] WARNING` line was printed (the real `~/.claude_pet.json` stat was
unchanged across the run) and no tripwire assertion fired: nothing reached the real
`SMAppService`.

## 7. What remains (not done here)

- **Developer** (a different agent, §2 Condition B): land `claude_pet.py` and `setup.py`
  against the surface in §2 until `python3 -m unittest tests.test_autostart -v` is green,
  without touching assertions or fixtures in `tests/test_autostart.py`. If a decision
  D1–D7 is overridden by the Coordinator, the corresponding assertion comes back to the
  Verifier.
- **Verifier** (this role): after the Developer's edits, re-run the module and the full
  suite from the worktree root, record GREEN verbatim here, and re-pin the `claude_pet.py`
  SHA256 in `tests/test_upload_artifact_gate.py` after reading the diff — the pin is a
  Verifier edit and is not made in advance.
- Docs follow-up named by the plan (README*.md and the site's spec table) is a
  separate documentation-only commit after both halves land; not part of this gate.

## 8. GREEN (round 1) — the gating module against the Developer's tree (02:09–02:17Z)

Round opened 2026-09-13T02:09Z, same worktree and HEAD. The Developer (a different agent)
landed `claude_pet.py`, `setup.py` and a CLAUDE.md section; `git status --porcelain` shows
exactly those three modified and the two untracked files this Verifier created. No test file
under `tests/` is modified.

**§2 Condition A** — `tests/test_autostart.py` hashes `6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2`,
byte-identical to the file the red run in §3 was recorded against. The Developer did not
touch an assertion, a fixture or the file. **Condition B** — this Verifier edited no
production file in either round; the only edits are this record and the test module.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; git rev-parse --short HEAD ; git status --porcelain ; shasum -a 256 claude_pet.py setup.py tests/test_autostart.py
2026-09-13T02:17:09Z
13710db
 M CLAUDE.md
 M claude_pet.py
 M setup.py
?? docs-design/track-b-verification-20260913.md
?? tests/test_autostart.py
6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d  claude_pet.py
5719a2077b2f25f84d5e73f519a6efd7c8294c25550ed7d5eadfb6a38a9599d6  setup.py
6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2  tests/test_autostart.py

$ python3 -m unittest tests.test_autostart -v ; echo "exit=$?"
test_each_key_is_translated_not_copied_across_locales (tests.test_autostart.AutostartLocalizationTests.test_each_key_is_translated_not_copied_across_locales)
R12: a string pasted into ko/ja/es unchanged would pass t()'s fallback. ... ok
test_every_locale_defines_every_key (tests.test_autostart.AutostartLocalizationTests.test_every_locale_defines_every_key) ... ok
test_menu_title_fits_the_menu (tests.test_autostart.AutostartLocalizationTests.test_menu_title_fits_the_menu)
Present in every locale and at most MENU_TITLE_MAX characters. ... ok
test_message_keys_differ_within_each_locale (tests.test_autostart.AutostartLocalizationTests.test_message_keys_differ_within_each_locale)
approval / open_settings / fail / unavailable are four different messages. ... ok
test_framework_without_smappservice_yields_none (tests.test_autostart.AutostartServiceTests.test_framework_without_smappservice_yields_none) ... ok
test_missing_framework_yields_none (tests.test_autostart.AutostartServiceTests.test_missing_framework_yields_none) ... ok
test_returns_the_main_app_service_object (tests.test_autostart.AutostartServiceTests.test_returns_the_main_app_service_object) ... ok
test_no_config_key_exists_for_the_feature (tests.test_autostart.AutostartStateTests.test_no_config_key_exists_for_the_feature)
Nothing in the settings contract or apply_config carries "autostart". ... ok
test_persisted_preference_does_not_influence_state (tests.test_autostart.AutostartStateTests.test_persisted_preference_does_not_influence_state)
OS is the source of truth (design X); a stored preference is not (R8). ... ok
test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
The whole 4 × 2 table at once, so the diff shows every wrong cell. ... ok
test_from_requires_approval_never_unregisters (tests.test_autostart.AutostartToggleTests.test_from_requires_approval_never_unregisters) ... ok
test_missing_framework_is_unavailable_without_error (tests.test_autostart.AutostartToggleTests.test_missing_framework_is_unavailable_without_error) ... ok
test_off_registers_and_reads_the_new_state_back (tests.test_autostart.AutostartToggleTests.test_off_registers_and_reads_the_new_state_back) ... ok
test_on_unregisters (tests.test_autostart.AutostartToggleTests.test_on_unregisters) ... ok
test_register_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_register_failure_is_reported_not_swallowed) ... ok
test_register_that_lands_on_requires_approval_reports_approval (tests.test_autostart.AutostartToggleTests.test_register_that_lands_on_requires_approval_reports_approval) ... ok
test_source_run_never_touches_the_service (tests.test_autostart.AutostartToggleTests.test_source_run_never_touches_the_service) ... ok
test_unregister_failure_is_reported_not_swallowed (tests.test_autostart.AutostartToggleTests.test_unregister_failure_is_reported_not_swallowed) ... ok
test_every_new_key_is_used_through_t (tests.test_autostart.AutostartWiringTests.test_every_new_key_is_used_through_t) ... ok
test_menu_item_follows_roam_and_precedes_reset_size (tests.test_autostart.AutostartWiringTests.test_menu_item_follows_roam_and_precedes_reset_size)
Placement A: `t("menu_autostart")` directly after Roam, before Reset size. ... ok
test_menu_item_has_a_handler_that_uses_the_pure_toggle (tests.test_autostart.AutostartWiringTests.test_menu_item_has_a_handler_that_uses_the_pure_toggle)
R13: an item whose selector no Handler method implements does nothing. ... ok
test_registration_calls_live_only_in_the_pure_helpers (tests.test_autostart.AutostartWiringTests.test_registration_calls_live_only_in_the_pure_helpers)
R9: no register / unregister inside run_gui or do_uninstall, one service seam. ... ok
test_setup_py_bundles_servicemanagement (tests.test_autostart.AutostartWiringTests.test_setup_py_bundles_servicemanagement)
R14: py2app only ships listed frameworks; without this the bundle's item is ... ok
test_busy_lock_refuses_before_touching_the_service (tests.test_autostart.DoUninstallOrderingTests.test_busy_lock_refuses_before_touching_the_service) ... ok
test_source_run_uninstall_does_not_touch_the_service (tests.test_autostart.DoUninstallOrderingTests.test_source_run_uninstall_does_not_touch_the_service) ... ok
test_unregister_failure_refuses_with_nothing_deleted (tests.test_autostart.DoUninstallOrderingTests.test_unregister_failure_refuses_with_nothing_deleted) ... ok
test_unregister_runs_after_the_lock_and_before_the_irreversible_section (tests.test_autostart.DoUninstallOrderingTests.test_unregister_runs_after_the_lock_and_before_the_irreversible_section) ... ok
test_helper_table (tests.test_autostart.UninstallAutostartHelperTests.test_helper_table)
uninstall_autostart(service) -> error_key | None. ... ok

----------------------------------------------------------------------
Ran 28 tests in 0.073s

OK
exit=0

$ python3 -c 'import claude_pet; print(claude_pet.APP_VERSION)' ; echo "exit=$?"
0.24
exit=0
$ python3 -c 'import ServiceManagement; print(hasattr(ServiceManagement, "SMAppService"))' ; echo "exit=$?"
True
exit=0
```

28 of 28 pass, exit 0 (the 27 that were red in §3 plus the absence guard that was already
green). `import claude_pet` and `import ServiceManagement` both succeed from source, and the
framework carries `SMAppService`. No `[test_autostart] WARNING` line (the real
`~/.claude_pet.json` stat was unchanged) and no tripwire assertion fired: nothing reached the
real `SMAppService` during the round.

### Diff review (read, not edited): `git diff -- claude_pet.py setup.py CLAUDE.md`

Checked against the surface in §2, the plan's Track B and CLAUDE.md:

- Names and contracts: `SM_STATUS_*` (0/1/2/3), `_AUTOSTART_STATE_BY_STATUS`,
  `autostart_state`, `autostart_service` (in-function `from ServiceManagement import
  SMAppService`, the only `mainAppService` site — pinned by the AST test),
  `autostart_read_state`, `autostart_toggle`, `uninstall_autostart`,
  `_autostart_err_summary`, `autostart_open_login_items`. Unknown status → `"unavailable"`
  (a superset of the 4×2 table; the table test still discriminates R1–R4).
- No config key: nothing added to `RUNTIME`, `apply_config`, `SETTINGS_OWNED_KEYS`,
  `merge_config_updates`; `ConfigGuard` rows all green.
- `do_uninstall()`: `uninstall_autostart(autostart_service())` sits inside `if app:` after
  `_path_ident_str` and before `subprocess.Popen` — the "2½" step the docstring now lists;
  a truthy error returns `(False, err)` with nothing deleted (D1). From source (`app` is
  None) the block is not entered (D4). The `uninstallApp_` alert appends
  `t("autostart_fail")` to `unin_fail` for that error key.
- Menu: tuple list `settings, toggle, roam, autostart, reset_size, None, uninstall, quit`;
  the Pets `insertItem_atIndex_` constant moved 4 → 5 (= index(reset_size)+1); the item
  reads `autostart_read_state(autostart_service() if is_bundle else None, is_bundle)` on
  every right-click, shows `t("autostart_unavailable")` disabled for `"unavailable"`, state
  1/0 for on/off and `-1` (mixed) for `"approval"`. `Handler.toggleAutostart_` goes through
  `autostart_toggle`, shows `autostart_fail` (critical alert) on an error key, and on
  `"approval"` shows `autostart_approval` with `autostart_open_settings` as the first
  (default) button and `unin_cancel` (present in all four locales) as the second.
- TR: six keys × four locales, pairwise distinct per key, `menu_autostart` ≤ 24 chars in
  every locale (es `Abrir al iniciar sesión` = 23; the survey's 25-char string was
  shortened — the Developer's stated reason, macOS's own Spanish label, is not something
  this Verifier checked).
- `setup.py`: `"includes": ["Foundation", "AppKit", "Quartz", "ServiceManagement"]`.
- Privacy (CLAUDE.md): the two `_dbg` lines log the state word and
  `_autostart_err_summary(err)` = `domain/code` only, or the exception type name — no
  `localizedDescription`, no path.
- CLAUDE.md wording nit, non-blocking: "From `2` nothing is called" and "`None` / `0` / `3`
  make no call" are true of register/unregister but `status()` is still read in those
  rows (the tests count calls excluding `status`). Worth one clause if the section is
  touched again; not a gate.

## 9. Full suite (round 1) — RED: one Track-B-induced error outside the pin family

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"     # cwd = worktree root
2026-09-13T02:09:38Z … 02:13:55Z  (full output: session scratchpad track-b-full-suite-round1.log)
Ran 575 tests in 254.527s
FAILED (failures=49, errors=9, skipped=8)
exit=1
```

By module (from the `FAIL:` / `ERROR:` headers), 58 not-ok in four modules:

| module | count | class | why |
| --- | --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | **pin, expected** | `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…` (HEAD) ≠ `6e9f76eb…` (Developer's `claude_pet.py`). Not re-pinned this round, per the Coordinator's instruction. |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`) | **pin, same family** | the same constant in that file; its 18 tests did not run, which is why the count is 575 and not 593. Re-pin together with the one above. |
| `test_v024_release_contract` | 1 FAIL | **pin, derived** | `test_v024_version_and_final_source_pins_propagate` compares both pins with the final source; green once both are re-pinned. |
| `test_companion_motion` | 1 ERROR | **not a pin — Track B introduced it** | see below. |

Verbatim, one representative of each:

```
======================================================================
ERROR: setUpClass (test_manual_update_transaction.BackupPreservationTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_manual_update_transaction.py", line 759, in setUpClass
    raise AssertionError(
    ...<2 lines>...
    )
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found 6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d

======================================================================
FAIL: test_v024_version_and_final_source_pins_propagate (test_v024_release_contract.VersionAndPinContractTests.test_v024_version_and_final_source_pins_propagate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_v024_release_contract.py", line 259, in test_v024_version_and_final_source_pins_propagate
    self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d'] is not false : 
- test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d
- test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 6e9f76eb8b3f410d747b133ae7657c3cdaa1dab89b66b54073f742b4a7d59f8d

======================================================================
ERROR: test_native_menu_validation_preserves_reduce_motion_disabled_item (test_companion_motion.CompanionGuiOwnershipTests.test_native_menu_validation_preserves_reduce_motion_disabled_item)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_companion_motion.py", line 1083, in test_native_menu_validation_preserves_reduce_motion_disabled_item
    method(None, None)
    ~~~~~~^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet-autostart/claude_pet.py", line 6758, in rightMouseDown_
    is_bundle = bool(app_bundle_path())
                     ^^^^^^^^^^^^^^^
NameError: name 'app_bundle_path' is not defined
```

### The companion-motion error

`CompanionGuiOwnershipTests.test_native_menu_validation_preserves_reduce_motion_disabled_item`
executes the real `rightMouseDown_` body through `gui_method()` with a hand-built scope
(`NSMenu`, `NSMenuItem`, `handler`, `state`, `RUNTIME`, `t`, `discover_pets`, `cfg`,
`APP_VERSION`) and checks that AppKit's own `menu.update()` keeps the Reduce-Motion-disabled
Roam item disabled. The Track B branch in `rightMouseDown_` now loads three module-level
names that scope does not carry — `app_bundle_path`, `autostart_service`,
`autostart_read_state` — so the method raises `NameError` before the menu is validated.

- At HEAD (a `git archive HEAD` copy in the session scratchpad, `claude_pet.py` at
  `6f95bc8b…`): `python3 -m unittest tests.test_companion_motion -v` → `Ran 51 tests … OK`.
  In the worktree: `Ran 51 tests … FAILED (errors=1)`, this one. So it is introduced by the
  Track B production change, not pre-existing.
- It is a harness-scope gap, not a runtime defect: all three names exist at module level in
  `claude_pet.py` (`import claude_pet` succeeds; the gating AST and handler tests pass).
- Scratch check (`<scratchpad>/companion_scope_check.py`, nothing on disk edited): the same
  test body with the three names added to the scope — `app_bundle_path=lambda: None` (a
  from-source run), a recording `autostart_service`, and the real
  `claude_pet.autostart_read_state` — gives `observed == [False, True]` (the test's own
  assertion holds), the service recorder is never called, and the validated menu reads
  `[('menu_settings', 0, True), ('menu_toggle', 0, True), ('menu_roam', 1, False),
  ('autostart_unavailable', 0, False), ('menu_reset_size', 0, True), ('', 0, False),
  ('menu_uninstall', 0, True), ('menu_quit', 0, True), ('', 0, False), ('ClaudePet vtest',
  0, False), ('menu_check_update', 0, True)]` — the new item disabled, titled
  `autostart_unavailable`, at index 3, and Pets absent because `discover_pets` is empty.
- Resolution is test-side: three scope entries in `tests/test_companion_motion.py`, the same
  shape as the `discover_pets` entry already there. That file is not a Track B gating test
  and was not authored by this Verifier, so the edit is not made here; the Coordinator
  assigns it (Verifier or an uninvolved agent — it changes no Track B assertion). A
  production-side alternative (making `rightMouseDown_` avoid the module-level names) has
  no merit and is not proposed.

### Baseline for comparison

A `git archive HEAD | tar -x` copy of the tree (no untracked files, so no
`tests/test_autostart.py`; `claude_pet.py` at `6f95bc8b…`) in the session scratchpad, run
with cwd at that copy's root:

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"
2026-09-13T02:14:22Z … 02:19:46Z  (full output: session scratchpad baseline-full-suite.log)
Ran 565 tests in 324.072s
OK (skipped=8)
exit=0
```

565 + 28 (the gating module) = 593, the count in §6; 593 − 18 (`test_manual_update_transaction`
not run) = 575, the count above. So every not-ok in the round-1 suite is either the pin
family or the one companion-motion error, and nothing else in the tree changed state
between HEAD and the Developer's tree.

### Verdict, round 1

- **Gating module `tests/test_autostart.py`: GREEN, 28/28, exit 0**, against a test file
  byte-identical to the red run's.
- **Full suite: RED.** 57 of the 58 not-ok are the `claude_pet.py` SHA256 pin family
  (three test modules) and clear together when the pin is re-derived after review; **1 is
  a Track-B-introduced harness error in `test_companion_motion`** with a three-line
  test-side fix identified above. The 8 skips are the pre-existing loud ones (§6).
- Not done here, by instruction: re-pinning `REVIEWED_APP_SOURCE_SHA256` in
  `tests/test_upload_artifact_gate.py` and `tests/test_manual_update_transaction.py`; the
  Coordinator decides when. Nothing was registered with the real `SMAppService`; the GUI
  was not run; `~/.claude_pet.json` was neither read nor written; no git write command.

## 10. GREEN (round 2) — the Track-B-introduced companion-motion error is gone (02:33–02:41Z)

Round opened 2026-09-13T02:33:58Z, same worktree (`/Users/yeongyu/claude-pet-autostart`,
branch `autostart`, HEAD `13710db`). The Developer's report: a production-only fix —
`rightMouseDown_` no longer loads `app_bundle_path` / `autostart_service` /
`autostart_read_state` (the three names the round-1 `NameError` in §9 was about); a new
module-level `autostart_current() -> (service, is_bundle)` that is `(None, False)` from source;
the `state` literal in `run_gui` gains `"autostart_read": lambda:
autostart_read_state(*autostart_current())` beside the roam hooks; `rightMouseDown_` reads
`state.get("autostart_read")` and treats a missing hook as `"unavailable"`;
`Handler.toggleAutostart_` calls `autostart_toggle(*autostart_current())`; CLAUDE.md's
"Start at sign-in" section describes the hook. No test file was touched. This Verifier
edited no production file in any round (§2 Condition B); the only edits are this record and
`tests/test_autostart.py` (unchanged since §3).

```
$ date -u +%Y-%m-%dT%H:%M:%SZ ; git rev-parse --short HEAD ; git branch --show-current ; git status --porcelain ; shasum -a 256 claude_pet.py setup.py CLAUDE.md tests/test_autostart.py tests/test_companion_motion.py ; git show HEAD:tests/test_companion_motion.py | shasum -a 256
2026-09-13T02:33:58Z
13710db
autostart
 M CLAUDE.md
 M claude_pet.py
 M setup.py
?? docs-design/track-b-verification-20260913.md
?? tests/test_autostart.py
0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0  claude_pet.py
5719a2077b2f25f84d5e73f519a6efd7c8294c25550ed7d5eadfb6a38a9599d6  setup.py
c5f2bcbea869c4a0577e915cdf415d94ecdda2f489e0fa5a4095664f9e00aec8  CLAUDE.md
6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2  tests/test_autostart.py
f6404f64187023e4fa040aeb7cbd8bb59e07611af2115fc191739eb883cb4918  tests/test_companion_motion.py
f6404f64187023e4fa040aeb7cbd8bb59e07611af2115fc191739eb883cb4918  -
```

**§2 Condition A.** `tests/test_companion_motion.py` is byte-identical to HEAD's copy
(`f6404f64…` both ways) and `tests/test_autostart.py` is byte-identical to the file the red
run in §3 was recorded against (`6de0e056…`). `claude_pet.py` moved `6e9f76eb…` (round 1) →
`0cd17cef…`; `setup.py` is unchanged from round 1 (`5719a207…`).

**Red-before-green for this fix (§3).** The red run is §9's verbatim `NameError: name
'app_bundle_path' is not defined` from `rightMouseDown_`, recorded against `claude_pet.py`
`6e9f76eb…` with the same test file. The same test, unmodified, against `0cd17cef…`:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ && python3 -m unittest tests.test_companion_motion -v 2>&1 | tail -25 ; echo "exit=${pipestatus[1]}"
2026-09-13T02:34:00Z
…
test_wander_pause_stays_folded_and_settlement_restores_manual_choice (tests.test_companion_motion.CompanionPresentationTests.test_wander_pause_stays_folded_and_settlement_restores_manual_choice) ... ok

----------------------------------------------------------------------
Ran 51 tests in 2.986s

OK
exit=0

$ date -u +%Y-%m-%dT%H:%M:%SZ && python3 -m unittest tests.test_autostart -v 2>&1 | tail -12 ; echo "exit=${pipestatus[1]}"
2026-09-13T02:34:03Z
…
test_helper_table (tests.test_autostart.UninstallAutostartHelperTests.test_helper_table)
uninstall_autostart(service) -> error_key | None. ... ok

----------------------------------------------------------------------
Ran 28 tests in 0.069s

OK
exit=0

$ python3 -c 'import claude_pet; print(claude_pet.APP_VERSION)' ; echo "exit=$?" ; python3 -c 'import ServiceManagement; print(hasattr(ServiceManagement, "SMAppService"))' ; echo "exit=$?"
0.24
exit=0
True
exit=0
```

51/51 in the round-2 gating file (the round-1 error was the only not-ok there), 28/28 in the
Track B gating module against the unchanged test file, both imports succeed.

### Diff review (read, not edited): `git diff -- claude_pet.py setup.py CLAUDE.md`

Read against §2 and the round-1 review in §8; only the round-2 delta is listed.

- `autostart_current()` is module-level, directly after `autostart_service()`; from source
  `app_bundle_path()` is `None`, so it returns `(None, False)` **without** calling
  `autostart_service()` — `mainAppService` still has exactly one call site (`autostart_service`,
  line 5014 of the current file), which the AST test R9 pins.
- `state` literal: `"autostart_read": lambda: autostart_read_state(*autostart_current())`, with
  a comment in the file's own hook convention (window-less tests carry no hook → the item is
  disabled as `autostart_unavailable`).
- `rightMouseDown_`: `read = state.get("autostart_read")`; `a_state = read() if read is not None
  else "unavailable"`; the rest of the branch (disabled + `autostart_unavailable` title, state
  `1`/`0`/`-1`) is as in round 1. Tuple order and the Pets insert index (5) are unchanged.
- `Handler.toggleAutostart_`: `autostart_toggle(*autostart_current())` — still reaches the pure
  toggle by name (wiring test R13 green).
- CLAUDE.md: the section gains the `autostart_current()` sentence and a paragraph on the
  `state["autostart_read"]` hook; the round-1 wording nit about `status()` in the `2` / `0` / `3`
  rows now carries the qualifying clause. `setup.py` unchanged.
- Privacy: no new `_dbg` line; nothing logs a path.

Read-only AST check (session scratchpad `round2_ast_check.py`, nothing on disk edited):

```
rightMouseDown_ loads any of ['app_bundle_path', 'autostart_current', 'autostart_read_state', 'autostart_service'] -> []
rightMouseDown_ state.get keys: ['roam_interrupt', 'update', 'onboard', 'autostart_read']
toggleAutostart_ loads: ['autostart_current', 'autostart_open_login_items', 'autostart_toggle']
state literal carries 'autostart_read': True
module-level autostart_current: True
mainAppService sites (lines): [5014]
```

No test in the tree executes the hook lambda's body itself (the companion-motion scope has no
`autostart_read` key, so `state.get` yields `None` there). Executed once from source in a scratch
script (`round2_hook_check.py`) under a `sys.modules["ServiceManagement"]` tripwire whose
`mainAppService` raises — the same composition as the lambda, the same call the handler makes:

```
app_bundle_path() from source: None
autostart_current(): (None, False)
hook(): unavailable
autostart_toggle(*autostart_current()): ('unavailable', None)
service calls: []
exit=0
```

The tripwire was never reached: from source neither the menu read nor the toggle touches the
service, `status()` included (D4). Nothing was registered with or unregistered from the real
`SMAppService`; the GUI was not run.

### Full suite (round 2)

```
$ python3 -m unittest discover -s tests -v ; echo "exit=$?"     # cwd = worktree root
2026-09-13T02:34:26Z … 02:38:51Z  (full output: session scratchpad track-b-full-suite-round2.log)
Ran 575 tests in 264.849s
FAILED (failures=49, errors=8, skipped=8)
exit=1
```

57 not-ok (round 1: 58), by module from the `FAIL:` / `ERROR:` headers; the filter
`grep '^FAIL:\|^ERROR:' | grep -v 'test_upload_artifact_gate\|test_manual_update_transaction\|test_v024_release_contract'`
is **empty**:

| module | count | class |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | pin, expected — `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…` (HEAD) ≠ `0cd17cef…`. Not re-pinned, per instruction. |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`) | pin, same family; its 18 tests did not run (575 = 593 − 18, as in round 1). |
| `test_v024_release_contract` | 1 FAIL | pin, derived from the two above. |
| `test_companion_motion` | **0** | the round-1 error is gone: line 59 of the log reads `test_native_menu_validation_preserves_reduce_motion_disabled_item … ok`. |

Verbatim, one representative of each pin module (note the new hash on the right-hand side):

```
ERROR: setUpClass (test_manual_update_transaction.BackupPreservationTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_manual_update_transaction.py", line 759, in setUpClass
    raise AssertionError(
    ...<2 lines>...
    )
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found 0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0

FAIL: test_v024_version_and_final_source_pins_propagate (test_v024_release_contract.VersionAndPinContractTests.test_v024_version_and_final_source_pins_propagate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_v024_release_contract.py", line 259, in test_v024_version_and_final_source_pins_propagate
    self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0'] is not false :
- test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0
- test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0

FAIL: test_a_clean_archive_is_accepted (test_upload_artifact_gate.ArchiveScannerRealFixtureTests.test_a_clean_archive_is_accepted)
The control. Without it every rejection below could be a blanket no.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart/tests/test_upload_artifact_gate.py", line 1577, in setUp
    assert_reviewed_file(self, APP_SOURCE, REVIEWED_APP_SOURCE_SHA256)
```

The 8 skips are the pre-existing loud ones (§6, same count): four in `test_updater` (two
"installed-app preflight" and two "real stapler contract", both opt-in via
`CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`) and four in `test_v020_boundaries`
(`B2Bundle.test_py2app_bundle_carries_every_asset` — no built bundle under `dist/`; and the
three `B3Updater` live-boundary tests gated on `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`).
No `[test_autostart] WARNING` line and no tripwire assertion in the log (`grep -c` = 0): the
real `~/.claude_pet.json` stat was unchanged and nothing reached the real `SMAppService`.

### Verdict, round 2 — GREEN

- **Round-2 gating file `tests/test_companion_motion.py`: GREEN, 51/51, exit 0**, byte-identical
  to HEAD; the §9 error is the observed red for this fix.
- **Track B gating module `tests/test_autostart.py`: GREEN, 28/28, exit 0**, byte-identical to
  the §3 red run.
- **Full suite: 575 run, 57 not-ok, every one of them the `claude_pet.py` SHA256 pin family**
  (48 + 8 + 1 across three modules), which clears together when `REVIEWED_APP_SOURCE_SHA256` is
  re-derived in `tests/test_upload_artifact_gate.py` and `tests/test_manual_update_transaction.py`
  against `0cd17cef7c5075ad3d472a8a453b413981c1d93f21bf732617c4451ca2d50ad0` — a Verifier edit
  the Coordinator schedules; not done here, per instruction. Nothing outside the pin family
  failed or errored.
- Not done, by instruction: the re-pin; any git write; the GUI; anything against the real
  `SMAppService`; `~/.claude_pet.json` was neither read nor written; no untracked file other
  than this record and `tests/test_autostart.py` was touched.

Record closed 2026-09-13T02:41:27Z.

---

## 11. FIX: NotFound mapping — RED

Verifier: verifier-b (Claude), VERIFIER role only, on the Track B fix. Reopened
2026-09-13T13:17Z. **Worktree `/Users/yeongyu/claude-pet-autostart-fix`, branch
`autostart-fix`, HEAD `794c66f`** (= `main` with Track A and Track B merged) — a different
worktree from §§1–10. All commands below ran with cwd there; times are UTC; output blocks are
verbatim. No git write command was run; the GUI was not run; nothing reached the real
`SMAppService` (fake service objects only, plus the module's `sys.modules` tripwire); the
user-owned untracked files were not touched; `~/.claude_pet.json` was neither read nor written.
Files written in this pass: `tests/test_autostart.py` (see §11.2 for what was already there)
and this record.

### 11.1 The defect this pass gates

At `794c66f`, `_AUTOSTART_STATE_BY_STATUS` in `claude_pet.py` maps status `3`
(`SM_STATUS_NOT_FOUND`) to `"unavailable"`, and `rightMouseDown_` renders `"unavailable"` as a
disabled item titled `autostart_unavailable` (`(여기서는 사용 불가)`). The Coordinator's
hardware probe (quoted verbatim in §11.3) shows that a real, never-registered bundle reports
`3`, so on every fresh install the item is disabled and the feature cannot be turned on. That
was observed on screen in the built bundle (Coordinator's report; not reproduced here — a
GUI run is outside this role's allowed actions).

### 11.2 State of the tree when this pass opened, and the provenance of the uncommitted diff

```
$ git rev-parse --short HEAD ; git branch --show-current ; git status --porcelain
794c66f
autostart-fix
 M tests/test_autostart.py
```

```
$ stat -f "%Sm %N" tests/test_autostart.py docs-design/track-b-verification-20260913.md claude_pet.py
Sep 13 12:24:24 2026 tests/test_autostart.py
Sep 13 12:20:23 2026 docs-design/track-b-verification-20260913.md
Sep 13 12:20:23 2026 claude_pet.py
```

The gating file already carried an uncommitted modification when this pass opened, written
four minutes after the worktree checkout (12:20:23 local = 03:20Z; the edit 12:24:24 local =
03:24Z), with this record and `claude_pet.py` untouched since checkout. Its content quotes
this assignment's hardware evidence nearly word for word under the module header that names
verifier-b, and it does exactly what this assignment specifies and nothing else. It is
therefore treated as an earlier, unfinished pass of this same assignment by this role, which
stopped before the RED run and before writing this section. It was **reviewed cell by cell,
not accepted** (§11.5); nothing in it needed changing, so the file as run is that diff.

**Deviation from the requested ordering, stated plainly.** The assignment asks that the
mapping be derived from the hardware evidence and written here *before* the existing
expected values are read, in the sense of AGENTS.md §2 Condition C. Establishing whose diff
was sitting in the working tree required reading `git diff tests/test_autostart.py`, which
shows both the old expected values (`(3, True) → "unavailable"`) and the new ones. So the
derivation in §11.4 was written **after** both had been seen, and this record does **not**
claim the "derived before reading" property. What it does claim: every cell in §11.4 is
justified by a quoted line of the hardware evidence or of the SDK header, not by the prior
diff, and the reader can check each justification without trusting this role.

### 11.3 Hardware evidence (Coordinator's, quoted verbatim; not reproduced here)

Provided by the Coordinator with the assignment. It is a single probe on a single machine,
and this role may not repeat it (calling `registerAndReturnError_` on the real service is
**[NEVER]** for a test or probe), so under §5 it stays an *observation* that this role has not
independently reproduced:

```
HARDWARE EVIDENCE (Coordinator, 2026-09-13, macOS 26 / Darwin 25.5, bundle built by
build_app.sh from 794c66f, signed Developer ID team RXGNVSLYF5, copied to
~/Applications/ClaudePet.app, probed from the bundle's own interpreter
Contents/MacOS/ClaudePet_py so NSBundle.mainBundle() was the app):
  bundle: /Users/yeongyu/Applications/ClaudePet.app
  status before: 3
  register: True | err: None
  status after register: 1
  unregister: True | err: None
  status after unregister: 0
The same bundle inside a git worktree directory also reported status 3 before any
registration.
```

Documentary source, read from disk (a static file read, no framework call) —
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk` → `MacOSX26.5.sdk`
(`SDKSettings.plist` `Version` = `26.5`), file
`System/Library/Frameworks/ServiceManagement.framework/Headers/SMAppService.h`, lines 13–35:

```
 * @abstract The values returned by SMAppService:status
 *
 * @const SMAppServiceNotRegistered
 * A service has not been registered with ServiceManagement or that the service was unregistered
 * after it was already registered.
 *
 * @const SMAppServiceEnabled
 * A service has been successfully registered and is eligible to run
 *
 * @const SMAppServiceRequiresApproval
 * A service has been successfully registered, but the user needs to take action in System Settings
 * before the service is eligible to run. This status will be returned if the user revokes consent for the service
 * to run in System Settings
 *
 * @const SMAppServiceNotFound
 * An error occurred and no such service could be found
 */
typedef NS_ENUM(NSInteger, SMAppServiceStatus) {
	SMAppServiceStatusNotRegistered,
	SMAppServiceStatusEnabled,
	SMAppServiceStatusRequiresApproval,
	SMAppServiceStatusNotFound,
} NS_SWIFT_NAME(SMAppService.Status);
```

The header fixes the four ints (0, 1, 2, 3 in declaration order) — that part is a
specification. Its description of `NotFound` ("an error occurred") is what the `794c66f`
mapping followed, and it is the reason that mapping looked right. The three §5 slots, kept
apart:

1. **Observed** (one machine, one bundle, one probe, 2026-09-13, macOS 26.5.2 / Darwin 25.5.0,
   by the Coordinator): a never-registered main-app service reads `3`, not `0`; `register`
   from `3` returns `(True, None)` and the status then reads `1`; `unregister` from `1`
   returns `(True, None)` and the status then reads `0`. Whether a never-registered bundle
   *always* reads `3`, or reads `0` on some other macOS version, is not established by this
   sample and is not claimed.
2. **Invariant** (from the header): the status ints are 0–3 with the names above; nothing in
   the header promises that a never-registered main-app service reads `NotRegistered` rather
   than `NotFound`, so no documented guarantee is contradicted by the observation — the
   header simply does not settle the fresh-install case.
3. **Consequence for the code**: for an installed bundle, `3` must render as `"off"` —
   unchecked and enabled — so that the click calls `register`, which the observation shows
   succeeds from `3`. Ints outside 0–3, a non-bundle run, a `None` service and a `status()`
   that raises stay `"unavailable"`. If a `3` ever is the header's "an error occurred", the
   user now sees an enabled item whose click returns `(False, err)` and surfaces the
   `autostart_fail` alert — a loud failure, instead of an item that can never be turned on.
   `uninstall_autostart` is unchanged: from `3` it reads `status()` and makes no call.

### 11.4 The mapping, re-derived cell by cell (see §11.2 for when this was written)

| `(status, is_bundle)` | derived | from |
| --- | --- | --- |
| `(0, True)` | `off` | header: NotRegistered, "unregistered after it was already registered"; hardware: `status after unregister: 0` |
| `(1, True)` | `on` | header: Enabled; hardware: `status after register: 1` |
| `(2, True)` | `approval` | header: RequiresApproval, "user needs to take action in System Settings" |
| `(3, True)` | **`off`** | hardware: `status before: 3` on a never-registered bundle, then `register: True \| err: None` — a state from which registering works is the unregistered state |
| `(99, True)`, `(-1, True)` | `unavailable` | not in the header's enum; do not offer register or unregister for a value nobody understands |
| `(any, False)` | `unavailable` | from source `mainAppService()` is Python.app's service, not ours (CLAUDE.md "Start at sign-in"); the status is not about this app |
| `service is None`, bundle | `unavailable` | macOS 12 / framework missing — no status exists to map |
| `status()` raises, bundle | `unavailable` | the framework misbehaving is not a status |

Toggle from `3`, bundle: `"off"` → `registerAndReturnError_(None)` → state read back; with the
fake moving `3 → 1` as the hardware did, the result is `("on", None)` and the call list is
`["register"]`. Unregister from `3` is refused by the fake (as from `0`): "never registered"
is the same thing as `0` for both calls, and keeping `3` in that set is what makes the
`3 = "on"` rival visible as an error and not only as a wrong call (§11.6).

These match the values in the working-tree diff (§11.2). The values at HEAD `794c66f` differ
in exactly one cell: `(3, True)` was `"unavailable"`.

### 11.5 What `tests/test_autostart.py` pins now (the diff reviewed, not accepted)

`git diff --stat`: `tests/test_autostart.py | 127 +++++++++++++++++++++++++++++++++++++++---------`
(104 insertions, 23 deletions). SHA256 of the file as run:
`ff7be7d53056ec4e2ec513c419afb1b1db30cb996a29261d6b16e1ba22a9759c`; of the HEAD version, for
contrast: `6de0e0560d0998b67449af257d9caee98e6658f37b82d26bf7896e769aac15a2`. `claude_pet.py`
is byte-identical to HEAD: `3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461`.

- `STATE_TABLE` (`AutostartStateTests.test_status_and_bundle_table`): `(SM_NOT_FOUND, True)`
  → `"off"`; two new rows `(99, True)` and `(-1, True)` → `"unavailable"`; the four
  `is_bundle=False` rows unchanged at `"unavailable"`. The docstring's truth table gained
  three rival columns — **R4 `3 = "unavailable"`** (the shipped mapping), **R4b `3 = "on"`**,
  and **R15 "bare else branch → off"** (the easiest way to write the fix, which would offer
  register for `99`). Each column was checked by hand against the derivation above and then
  by execution (§11.6).
- `AutostartReadStateTests.test_read_state_table` (**new**): pins `autostart_read_state`,
  the function the menu actually reaches through `state["autostart_read"]`, so the
  fresh-install claim is pinned where the menu reads it — `(FakeService(3), bundle)` →
  `"off"` with `["status"]`; `status()` raising → `"unavailable"` with `["status"]`
  (new `RaisingStatusService` fake); `(FakeService(3), not a bundle)` → `"unavailable"`
  with `[]`; `(None, bundle)` → `"unavailable"`.
- `AutostartToggleTests.test_never_registered_bundle_registers_from_not_found` (**new**):
  `FakeService(SM_NOT_FOUND)`, bundle → `(("on", None), ["register"])` under `ConfigGuard`.
  The class docstring's table gained the `(3, T, register ok, 1)` row and a paragraph on how
  it separates R4 (returns `("unavailable", None)` with no call) from R1/R4b (call
  unregister, which the fake refuses from `3`).
- `FakeService`: `registerAndReturnError_` already moved any status other than `2` to
  `after_register`, so a register from `3` lands on `1` with no code change; the docstring
  now says so and names the two transitions the hardware showed (`3 → 1`, `1 → 0`).
  `unregisterAndReturnError_` still refuses from `(SM_NOT_REGISTERED, SM_NOT_FOUND)`
  (line 177) — **kept deliberately**, consistent with `UninstallAutostartHelperTests`'s
  `status 3 → None, []` row and with the toggle row above.
- Module docstring: the `autostart_state` and `autostart_toggle` contracts updated; the
  rival list gained R4b and R15 and re-labels R4 as "NotFound is unavailable (merged at
  794c66f)".
- Everything else — service resolution, uninstall helper and ordering, localisation,
  AST wiring — untouched, and all of it stayed green in the RED run below.

### 11.6 Discrimination check by execution (scratch, 13:22:50Z)

Scratch script `discriminate_notfound.py` in the session scratchpad, run as
`PYTHONPATH=/Users/yeongyu/claude-pet-autostart-fix python3 <script>` (a first attempt with
a bare `python3 <path>` failed on `import claude_pet` — `python3 <file>` puts the script's
own directory on `sys.path`, not the cwd — and was rerun). It implements each rival mapping
as a function, runs all of them plus HEAD's `autostart_state` over `STATE_TABLE`, and then
drives the **real** `autostart_toggle` on `FakeService(3)` with `autostart_state` patched to
each rival in turn. Nothing touches the real service.

```
(status,bund) expected     R1           R2           R3           R4           R4b          R15          HEAD
(0,T)         off          off          off          off          off          off          off          off
(1,T)         on           on           on           on           on           on           on           on
(2,T)         approval     on X         off X        approval     approval     approval     approval     approval
(3,T)         off          on X         off          off          unavailable Xon X         off          unavailable X
(99,T)        unavailable  on X         off X        unavailable  unavailable  unavailable  off X        unavailable
(-1,T)        unavailable  on X         off X        unavailable  unavailable  unavailable  off X        unavailable
(0,F)         unavailable  off X        off X        off X        unavailable  unavailable  unavailable  unavailable
(1,F)         unavailable  on X         on X         on X         unavailable  unavailable  unavailable  unavailable
(2,F)         unavailable  on X         off X        approval X   unavailable  unavailable  unavailable  unavailable
(3,F)         unavailable  on X         off X        off X        unavailable  unavailable  unavailable  unavailable

expected  separated by 0 row(s): []
R1        separated by 8 row(s): [(2, True), (3, True), (99, True), (-1, True), (0, False), (1, False), (2, False), (3, False)]
R2        separated by 7 row(s): [(2, True), (99, True), (-1, True), (0, False), (1, False), (2, False), (3, False)]
R3        separated by 4 row(s): [(0, False), (1, False), (2, False), (3, False)]
R4        separated by 1 row(s): [(3, True)]
R4b       separated by 1 row(s): [(3, True)]
R15       separated by 2 row(s): [(99, True), (-1, True)]
HEAD      separated by 1 row(s): [(3, True)]
every rival separated: True

real autostart_toggle on FakeService(3), is_bundle=True, under each mapping:
  expected  -> ('on', None)  calls=['register']  status now 1
  R1        -> ('on', 'autostart_fail')  calls=['unregister']  status now 3
  R2        -> ('on', None)  calls=['register']  status now 1
  R3        -> ('on', None)  calls=['register']  status now 1
  R4        -> ('unavailable', None)  calls=[]  status now 3
  R4b       -> ('on', 'autostart_fail')  calls=['unregister']  status now 3
  R15       -> ('on', None)  calls=['register']  status now 1
  HEAD      -> ('unavailable', None)  calls=[]  status now 3
```

Reading: the executed matrix matches the docstring table in the test cell for cell. R4 and
HEAD coincide everywhere (HEAD *is* R4) and are separated by exactly one row, `(3, True)` —
the row this fix is about — and by the toggle (no call, `"unavailable"`). R4b and R1 are
separated on the toggle by the call list *and* the error (`["unregister"]`,
`"autostart_fail"`), which is why the fake keeps refusing unregister from `3`. R2, R3 and R15
tie with `expected` on the toggle row and are separated in the state table, as the test
docstring says.

### 11.7 RED run (AGENTS.md §3 step 2) — 13:17:35Z, exit 1

```
$ python3 -m unittest tests.test_autostart -v
```

30 tests ran; 27 `ok`; the three below `FAIL`. Verbatim, the failure section through the
summary (the 27 `ok` lines are omitted here; the full log is in the session scratchpad,
`red-autostart.log`):

```
======================================================================
FAIL: test_read_state_table (tests.test_autostart.AutostartReadStateTests.test_read_state_table)
autostart_read_state(service, is_bundle) — the value the menu hook shows.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart-fix/tests/test_autostart.py", line 426, in test_read_state_table
    self.assertEqual(got, want)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^
AssertionError: Lists differ: [('unavailable', ['status']), ('unavailable'[53 chars]one)] != [('off', ['status']), ('unavailable', ['stat[45 chars]one)]

First differing element 0:
('unavailable', ['status'])
('off', ['status'])

- [('unavailable', ['status']),
+ [('off', ['status']),
   ('unavailable', ['status']),
   ('unavailable', []),
   ('unavailable', None)]

======================================================================
FAIL: test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
The whole table at once, so the diff shows every wrong cell.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart-fix/tests/test_autostart.py", line 364, in test_status_and_bundle_table
    self.assertEqual(got, dict(STATE_TABLE))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {(0, [61 chars]e): 'unavailable', (99, True): 'unavailable', [129 chars]ble'} != {(0, [61 chars]e): 'off', (99, True): 'unavailable', (-1, Tru[121 chars]ble'}
  {(-1, True): 'unavailable',
   (0, False): 'unavailable',
   (0, True): 'off',
   (1, False): 'unavailable',
   (1, True): 'on',
   (2, False): 'unavailable',
   (2, True): 'approval',
   (3, False): 'unavailable',
-  (3, True): 'unavailable',
+  (3, True): 'off',
   (99, True): 'unavailable'}

======================================================================
FAIL: test_never_registered_bundle_registers_from_not_found (tests.test_autostart.AutostartToggleTests.test_never_registered_bundle_registers_from_not_found)
Status 3 is where every fresh install starts; the click must register.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet-autostart-fix/tests/test_autostart.py", line 474, in test_never_registered_bundle_registers_from_not_found
    self.assertEqual((self.toggle(svc), svc.method_calls()),
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     (("on", None), ["register"]))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (('unavailable', None), []) != (('on', None), ['register'])

First differing element 0:
('unavailable', None)
('on', None)

- (('unavailable', None), [])
+ (('on', None), ['register'])

----------------------------------------------------------------------
Ran 30 tests in 0.086s

FAILED (failures=3)
exit=1
```

Each failure is the `(3, True)` cell and nothing else: the state table differs in one key
(`- (3, True): 'unavailable'` / `+ (3, True): 'off'`), the read-state table in its first
element only, and the toggle row shows the shipped behaviour in full — `("unavailable",
None)` with an empty call list, i.e. the click that cannot turn the feature on. The three
`"unavailable"` rows that must survive the fix (status raises, not a bundle, `None` service)
already pass, so a fix that over-corrects them will turn one of these green tests red.

### 11.8 Full suite from the worktree root — 13:17:57Z to 13:22:28Z, exit 1

```
$ python3 -m unittest discover -s tests -v
Ran 588 tests in 270.801s

FAILED (failures=52, errors=8, skipped=8)
```

| module | not-ok | reason |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | pin, expected — `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…` ≠ `3bc33466…` (this HEAD's `claude_pet.py`). Not re-pinned, per instruction. |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`) | pin, same family; its 18 tests did not run. |
| `test_v024_release_contract` | 1 FAIL | pin, derived from the two above. |
| `test_autostart` | **3 FAIL** | **this pass's RED** — the same three tests, same messages as §11.7 (log lines 892–950). |

Verbatim, the pin family's messages (one per module; note the right-hand hash is now this
HEAD's, not round 2's `0cd17cef…`):

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found 3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461
```

```
AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is 3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461'] is not false :
```

52 = 48 + 1 + 3; 8 = the `setUpClass` errors. **Nothing outside the pin family and the three
intended RED tests failed or errored.** The 8 skips are the pre-existing loud ones (§6, §10):
four in `test_updater` (two "installed-app preflight", two "real stapler contract", opt-in via
`CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`) and four in `test_v020_boundaries`
(`B2Bundle.test_py2app_bundle_carries_every_asset`, no built bundle under `dist/`; three
`B3Updater` live tests gated on `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`). `grep -c` for
`WARNING`, `reached SMAppService`, `tried to open System Settings` over the log: `0` — the
real `~/.claude_pet.json` stat was unchanged and no test reached the tripwire.

Test count 588 against round 2's 575: `git diff --stat 13710db 794c66f -- tests/` lists two
files, `tests/test_autostart.py` (the Track B module itself) and
`tests/test_oauth_token_cache.py` (Track A, new at the merge); this run counts 11 tests in
`test_oauth_token_cache` and 30 in `test_autostart` (28 in §10), so 575 + 11 + 2 = 588.

### 11.9 What remains (not done here)

- **Developer**: change `_AUTOSTART_STATE_BY_STATUS[SM_STATUS_NOT_FOUND]` to `"off"` (and
  the `autostart_state` docstring, which says unknown values are `"unavailable"` — still true
  — but must stop implying `3` is one of them). CLAUDE.md "Start at sign-in" currently reads
  `` `3 → "unavailable"` `` in the `autostart_state` bullet and needs the same correction;
  this role did not edit it. The `rightMouseDown_` comment listing the `"unavailable"` cases
  (source run, macOS 12, no service) stays correct.
- **Verifier, after the Developer's tree lands**: rerun `python3 -m unittest
  tests.test_autostart -v` with the gating file byte-identical to
  `ff7be7d53056ec4e2ec513c419afb1b1db30cb996a29261d6b16e1ba22a9759c` (30/30 expected), then
  the full suite (only the pin family may remain not-ok), and read — not edit — the
  production diff.
- The `claude_pet.py` SHA256 re-pin stays scheduled separately by the Coordinator.
- Not done, by instruction and by role: no git write; no GUI; nothing against the real
  `SMAppService`; no reproduction of the hardware probe (it would call `register` on the real
  service, which is **[NEVER]** from a test or probe) — §11.3 therefore rests on the
  Coordinator's single observation, labelled as such.

Record closed 2026-09-13T13:26Z.

## 12. FIX: NotFound mapping — GREEN

Verifier: verifier-b (Claude), VERIFIER role only, on the Track B fix. Reopened
2026-09-13T13:37:42Z, same worktree as §11: `/Users/yeongyu/claude-pet-autostart-fix`, branch
`autostart-fix`, HEAD `794c66f`. All commands ran with cwd there; times are UTC; output blocks are
verbatim. No git write command was run; the GUI was not run; nothing reached the real
`SMAppService` (fake service objects only, plus the module's `sys.modules` tripwire); the
user-owned untracked files were not touched; `~/.claude_pet.json` was neither read nor written.
**Files written in this pass: this record, and nothing else.** `claude_pet.py`, CLAUDE.md and
`tests/test_autostart.py` were read (diffs and hashes below), not opened for writing. Machine:
macOS 26.5.2 (25F84), Darwin 25.5.0, Python 3.13.7.

### 12.1 The tree, and what changed since the RED run

```
$ git rev-parse --short HEAD ; git status --porcelain
794c66f
 M CLAUDE.md
 M claude_pet.py
 M docs-design/track-b-verification-20260913.md
 M tests/test_autostart.py
$ shasum -a 256 claude_pet.py tests/test_autostart.py CLAUDE.md
ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4  claude_pet.py
ff7be7d53056ec4e2ec513c419afb1b1db30cb996a29261d6b16e1ba22a9759c  tests/test_autostart.py
12be8e264363787a7db7afe6c70a4fd5c09d89ce08c656cd9109dd07d80a03b3  CLAUDE.md
$ git show HEAD:claude_pet.py | shasum -a 256
3bc33466ff97e04fcbd33160c60bc2cf6c90c070ac9d1d8b4a0212c059853461  -
$ git diff --numstat
21	5	CLAUDE.md
36	8	claude_pet.py
394	0	docs-design/track-b-verification-20260913.md   # §11, before this section
104	23	tests/test_autostart.py
$ stat -f "%Sm %N" claude_pet.py tests/test_autostart.py CLAUDE.md
Sep 13 22:29:50 2026 claude_pet.py          # local (UTC+9) = 13:29:50Z
Sep 13 12:24:24 2026 tests/test_autostart.py # unchanged since §11.2 (03:24Z)
Sep 13 22:30:18 2026 CLAUDE.md               # 13:30:18Z
```

Two facts this pins, both checkable from the hashes alone:

- **The gating file is byte-identical to the one that produced the RED run.** §11.5 recorded
  `ff7be7d5…` for `tests/test_autostart.py` as run at 13:17:35Z; it is `ff7be7d5…` now, and
  its mtime (03:24Z) predates the Developer's write to `claude_pet.py` (13:29:50Z). So the
  Developer did not touch the assertions or fixtures (§2 Condition A), and the only variable
  between §11.7 (RED) and §12.3 (GREEN) is `claude_pet.py`: `3bc33466…` (= HEAD) then,
  `ce7564b1…` now.
- **This role has clean hands on the production file** (§2 Condition B): `claude_pet.py` was
  last written at 13:29:50Z, before this pass opened (13:37:42Z), and this pass wrote only
  this record.

### 12.2 The production diff, read (not edited)

`git diff -U0 -- claude_pet.py | grep '^@@'` — six hunks, all inside the autostart block
(old lines 5145–5216; nothing else in the file moved):

```
@@ -5145,0 +5146,12 @@ SM_STATUS_NOT_FOUND = 3
@@ -5150 +5162 @@ _AUTOSTART_STATE_BY_STATUS = {
@@ -5157,3 +5169,7 @@ def autostart_state(status, is_bundle):
@@ -5196,2 +5212,8 @@ def autostart_read_state(service, is_bundle):
@@ -5210 +5232,6 @@ def autostart_toggle(service, is_bundle):
@@ -5216 +5243,2 @@ def autostart_toggle(service, is_bundle):
```

One line of behaviour changed: `_AUTOSTART_STATE_BY_STATUS[SM_STATUS_NOT_FOUND]` reads
`"off"` where HEAD has `"unavailable"`. Every other hunk is a comment or a docstring: a
Korean block above the table carrying the hardware finding (labelled "기기 하나, 조사 한 번" —
one machine, one probe — with the observation, the "0 and 3 map to the same state" reasoning,
and the operational consequence in separate sentences, per §5), and updated docstrings on
`autostart_state`, `autostart_read_state` and `autostart_toggle`. Checked against §11.4 cell by
cell:

- `autostart_state`: `if not is_bundle: return "unavailable"` then
  `_AUTOSTART_STATE_BY_STATUS.get(status, "unavailable")` — unchanged code, so `99` / `-1`
  still fall to `"unavailable"` (R15 rejected) and the four `is_bundle=False` rows are
  untouched (R3 rejected).
- `autostart_read_state`: `not is_bundle or service is None → "unavailable"` before any
  call, `status()` raising → `"unavailable"` — unchanged code.
- `autostart_toggle`: unchanged code; it branches on the state `autostart_read_state`
  returns, so `3 → "off"` reaches the `else` branch and calls `registerAndReturnError_(None)`,
  then reads the state back. The `("unavailable", "approval")` early return still makes no
  call for unknown ints and from `2`.
- `uninstall_autostart`: no hunk; from `0` / `3` it still reads `status()` and stops.
- `rightMouseDown_` (no hunk): `"unavailable"` → disabled item with the
  `autostart_unavailable` title; anything else → `setState_({"on": 1, "off": 0}.get(a_state, -1))`,
  so `"off"` renders unchecked and enabled. Its comment listing the `"unavailable"` cases
  (source run, macOS 12, no service) is still accurate, as §11.9 said.

CLAUDE.md, three hunks (`@@ -581`, `@@ -588,2`, `@@ -623,2`), all in "Start at sign-in": the
`autostart_state` bullet now reads `3 → "off"`, `any other int → "unavailable"`, states the
hardware finding as one machine / one probe, and names the four surviving `"unavailable"`
cases; the `autostart_toggle` bullet says "Off (status `0` or `3`)"; the closing **[NEVER]**
paragraph no longer says a from-source run "would report `NotFound` anyway" (which the fix
makes misleading) and says instead that `autostart_current()` hands the helpers
`(None, False)`. §11.9's open item on CLAUDE.md is therefore closed. The machine descriptor it
quotes ("macOS 26.5 / Darwin 25.5") matches this machine's `sw_vers` / `uname -r`; the probe
itself is still the Coordinator's single observation and was not reproduced here (§11.3).

### 12.3 GREEN run (AGENTS.md §3 step 4) — 13:37:46Z, exit 0

```
$ python3 -m unittest tests.test_autostart -v
```

30 tests ran, 30 `ok`, exit 0. The three tests that were RED in §11.7, verbatim from this
run (the full 48-line log is in the session scratchpad, `green-autostart.txt`; it contains no
`WARNING`, `reached SMAppService` or `tried to open System Settings` line):

```
test_read_state_table (tests.test_autostart.AutostartReadStateTests.test_read_state_table)
autostart_read_state(service, is_bundle) — the value the menu hook shows. ... ok
test_status_and_bundle_table (tests.test_autostart.AutostartStateTests.test_status_and_bundle_table)
The whole table at once, so the diff shows every wrong cell. ... ok
test_never_registered_bundle_registers_from_not_found (tests.test_autostart.AutostartToggleTests.test_never_registered_bundle_registers_from_not_found)
Status 3 is where every fresh install starts; the click must register. ... ok
```

and the tail:

```
test_helper_table (tests.test_autostart.UninstallAutostartHelperTests.test_helper_table)
uninstall_autostart(service) -> error_key | None. ... ok

----------------------------------------------------------------------
Ran 30 tests in 0.077s

OK
EXIT=0
```

Red → green with the gating file held constant (§12.1): the RED run at 13:17:35Z failed
exactly these three on the `(3, True)` cell against `claude_pet.py` `3bc33466…`; this run
passes all 30 against `ce7564b1…`. The three `"unavailable"` rows that had to survive the fix
(`status()` raises, not a bundle, `None` service — §11.7) are inside `test_read_state_table`
and `test_status_and_bundle_table`, which pass, so the fix did not over-correct them.

### 12.4 Full suite from the worktree root — 13:37:48Z to 13:42:19Z, exit 1

```
$ python3 -m unittest discover -s tests -v
Ran 588 tests in 270.871s

FAILED (failures=49, errors=8, skipped=8)
```

| module | not-ok | reason |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | pin, expected — `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…` ≠ `ce7564b1…` (this tree's `claude_pet.py`). Not re-pinned, per instruction. |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`) | pin, same family; its 18 tests did not run. |
| `test_v024_release_contract` | 1 FAIL | pin, derived from the two above. |
| `test_autostart` | **0** | **was 3 FAIL in §11.8** — all 30 `ok` in this run (log lines 1–43). |

Verbatim, the pin family's messages (one per module; the right-hand hash is now the fixed
tree's, not §11.8's `3bc33466…`):

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, found ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4
```

```
AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4', 'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4, final claude_pet.py is ce7564b1e3595ecf75365634642acf3837bdd8871e79cb8c1826e4ef88291db4'] is not false :
```

49 = 48 + 1; 8 = the `setUpClass` errors; §11.8's 52 − 3 = 49. **Nothing outside the pin
family failed or errored.** Counted from the log with `grep -E '^(FAIL|ERROR): '`: 48 `FAIL:`
lines name `test_upload_artifact_gate`, 1 names `test_v024_release_contract`, all 8 `ERROR:`
lines are `setUpClass (test_manual_update_transaction.*)`, and no `FAIL:` / `ERROR:` line
names any other module. The 8 skips are the same pre-existing loud ones as §11.8: four in
`test_updater` (opt-in via `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`) and four in
`test_v020_boundaries` (`B2Bundle` — no built bundle under `dist/`; three `B3Updater` live
tests gated on `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`). `grep -c` for `WARNING`,
`reached SMAppService`, `tried to open System Settings` over the log: `0`. Test count 588,
unchanged from §11.8, as expected with no test file changed since. Full log in the session
scratchpad, `green-full.txt`.

### 12.5 Verdict — GREEN

- The gating module is 30/30 against the Developer's tree, with the gating file byte-identical
  to its RED run (§3 steps 2 and 4 both observed, fix as the only variable).
- The full suite has no not-ok result outside the `claude_pet.py` SHA256 pin family, which
  stays scheduled for release-time re-pinning.
- The production diff is one mapping cell plus comments and docstrings; every `"unavailable"`
  path named in the assignment (not a bundle, `None` service, `status()` raising, ints outside
  0–3) is unchanged in code and pinned by a passing test.

### 12.6 What remains (not done here)

- **`main` has moved.** `git worktree list` shows `/Users/yeongyu/claude-pet` at `f3c4780`
  (one commit past `794c66f`: "docs: drop the "Patch" name everywhere"). It touches
  `claude_pet.py` at line 6 (the module docstring) and the READMEs / `make_icon.py`; it does
  not touch the autostart hunks, `tests/test_autostart.py`, CLAUDE.md or this record, so the
  fix applies cleanly — but the final `claude_pet.py` hash will differ from `ce7564b1…` once
  merged, so the pin family must be re-pinned on the merged tree, not on this one.
- The `claude_pet.py` SHA256 re-pin itself stays with the Coordinator (release-time).
- Optional, not blocking: CLAUDE.md's repo-layout row for `tests/test_autostart.py` lists
  "the status table, the toggle's truth table, the `do_uninstall()` ordering, the TR keys, and
  the menu wiring"; the module now also pins `autostart_read_state`'s table. The row is not
  wrong (it is not written as exhaustive); a Developer may add it.
- Not done, by instruction and by role: no git write; no GUI; nothing against the real
  `SMAppService`; no reproduction of the hardware probe (**[NEVER]** for a test or probe), so
  the fresh-install-reads-3 claim still rests on the Coordinator's single observation, labelled
  as such in the code comment, CLAUDE.md, the test docstring and §11.3.
Record closed 2026-09-13T13:45Z.

## Hardware check on the merged code (Coordinator, 2026-09-13, macOS 26.5 / Darwin 25.5)

Bundle built by `./build_app.sh build` from f09c97d (the NotFound-mapping fix) in a detached
worktree, launched with `open -n … --env HOME=<scratch>` so the user's config was untouched,
driven with synthetic Quartz events (right-click on the pet, Down ×4, Return), the menu
captured after each step with `screencapture -R`, and the service status read from the
bundle's own interpreter (`Contents/MacOS/ClaudePet_py`, so `NSBundle.mainBundle()` was
the app):

| step | menu | `SMAppService.mainAppService().status()` |
| --- | --- | --- |
| fresh bundle, before launch | — | 3 (NotFound) |
| first right-click | "로그인 시 자동 실행" enabled, unchecked | — |
| after selecting it once | ✓ checked | (registered) |
| after selecting it again | unchecked | 0 (NotRegistered) |

The item was disabled with "(여기서는 사용 불가)" on the pre-fix build of 794c66f from the
same location; two causes were found and fixed that day — the pyenv build Python lacked
`pyobjc-framework-ServiceManagement` (installed), and status 3 was mapped to
"unavailable" (f09c97d). Screenshots: session scratchpad `autostart_1_menu.png`,
`autostart_3_after_on.png`, `autostart_4_after_off.png` (not committed).
