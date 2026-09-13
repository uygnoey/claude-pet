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
