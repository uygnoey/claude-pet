# ClaudePet v0.23 — independent Reviewer record

- **Reviewer:** agent `reviewer-v023` (Claude Code session
  `55c3dee4-727f-4a94-b960-66540b129014`, subagent). Held no other role on this
  release: wrote no production code, no test, no release note. Edited nothing in
  the repository except this file (confirmed absent before writing). Scratch
  work lives under the session scratchpad (`reviewer_mutants/`,
  `reviewer_full_suite.log`) and touches nothing in the checkout.
- **Developer:** Claude (same session, main thread). **Verifier:** `verifier-v023`
  (subagent), record `docs-design/release-v023-verification-20260911.md`.
- **Measured (UTC):** 2026-09-11T01:34:28Z (start) → 2026-09-11T01:43:52Z (end).
  Gate re-runs 01:36:36Z → 01:37:40Z; mutants 01:38:19Z → 01:38:25Z; full suite
  01:37:59Z → 01:43:37Z.
- **Tree under review:** HEAD `6d47df5e433fe39d6e84d2d4e2a5ead6ddc2c349` plus the
  uncommitted working tree. v0.22 is published — reproduced, not taken from the
  Context: `git tag --sort=-v:refname | head -1` → `v0.22`;
  `git ls-remote --tags origin v0.22` → `927e7808…  refs/tags/v0.22`;
  `gh release list --limit 3` → `ClaudePet v0.22  Latest  v0.22  2026-09-11T00:43:39Z`.
- **Source hashes (SHA-256, working tree, unchanged for the whole review):**
  - `claude_pet.py` `57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b`
    (HEAD: `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266`)
  - `verify_release_artifact.py` `fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69`
    (HEAD: `8de85e87dd8ba5c5dc254dfac33f7bcedfd19e2d681d2bf981df19b34e8eb82d`)
  - `release.sh` `a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23` (= HEAD)
  - `RELEASE_NOTES.md` `6e0b1cdfd988f878252aa12c694dafeb3b522783ffa7575b2f3d9145b716c07b`
- **Nothing outside this file was touched.** No `./release.sh`, no `./build_app.sh`,
  no commit, no tag, no `git add`, no `git clean`, no `rm -rf`; `~/.claude` and
  `~/.claude_pet` were not read or written by anything I ran (the suite's fixtures
  are synthetic; the mutants stub the network). `/Applications/ClaudePet.app`
  (v0.22) untouched; the live opt-in tests stayed skipped.

## Verdict: **PASS** — sign-off for the release commit (§8 item 4)

Two advisories, neither blocking, in §5. Everything the assignment asked me to
verify first-hand held; the Verifier's claims reproduced.

---

## 1. Working tree, read first-hand

`git status --porcelain`, tracked columns: `M CLAUDE.md`, `M RELEASE_NOTES.md`,
`M claude_pet.py`, `M tests/test_manual_update_transaction.py`,
`M tests/test_upload_artifact_gate.py`,
`RM tests/test_v022_release_contract.py -> tests/test_v023_release_contract.py`,
`M verify_release_artifact.py`. `git diff --cached --name-status` → only
`R100 tests/test_v022_release_contract.py tests/test_v023_release_contract.py`
(the `git mv`; the rewrite is unstaged on top). `ls tests/ | grep release_contract`
→ `test_v023_release_contract.py` only — no duplicate module.

Untracked, relevant: `tests/test_update_check_schedule.py`,
`docs-design/release-v023-verification-20260911.md`, this file. The user-owned
files and other agents' `docs-design/` records are present and untouched (§10).

`git diff --stat HEAD`: `CLAUDE.md` 3 (+2/−1), `RELEASE_NOTES.md` +5,
`claude_pet.py` 79 (+68/−11 by line, 10 hunks), the two repins (2 and 4),
the contract-test rename/rewrite, `verify_release_artifact.py` (+1/−1).

## 2. `claude_pet.py`, hunk by hunk (every hunk must be one of the eight allowed)

| git hunk (approx. line) | What it is | Allowed category |
| --- | --- | --- |
| @@ 870 | `APP_VERSION = "0.22"` → `"0.23"`; `UPDATE_CHECK_SEC = 6 * 3600` → `3600` + new comment | APP_VERSION line; UPDATE_CHECK_SEC line |
| @@ 1006 (en), @@ 1098 (ko), @@ 1175 (ja), @@ 1257 (es) | six keys each: `menu_check_update`, `upd_title`, `upd_current`, `upd_failed`, `upd_install_failed`, `upd_busy` | six TR keys × four locales |
| @@ 6149 | `_run_update_check`: `return` → `return None`; `poll_github_update(state)` → `return poll_github_update(state)` | returns status/None |
| @@ 6612 | new `NSMenuItem` titled `t("menu_check_update")`, action `"checkUpdate:"`, `setTarget_(handler)`, `menu.addItem_` after `vitem` | the menu item |
| @@ 7514 | `Handler.checkUpdate_` and `Handler.showUpdateMessage_` | checkUpdate_/showUpdateMessage_ |
| @@ 7633 | worker comment rewritten; the condition line `if not state.get("update") and time.time() - _upd_cache["t"] > UPDATE_CHECK_SEC:` → `_run_update_check()` byte-identical | refresh-worker comment, condition unchanged |
| @@ 7690 | `threading.Thread(target=_run_update_check, daemon=True).start()` → `_upd_cache["t"] = time.time()` before `AppHelper.runEventLoop()` | launch Thread → stamp |

**Nothing else.** No hunk touches `check_github_update`, `poll_github_update`,
`install_github_update`, `_ver_tuple`, `select_update_asset`, `validate_update_app`,
`_acquire_update_lock`, or any estimator function — those are byte-identical to
HEAD, which is what the note's "한도 계산은 그대로" rests on.

Other files: `verify_release_artifact.py` usage line `--expect-version 0.22` →
`0.23`, nothing else. `CLAUDE.md`: one sentence, "every 6 hours" → "every hour
(never at launch — the first check comes one interval after start)". Both repins
change literals only. `RELEASE_NOTES.md`: one new `**v0.23**` section (§4).

## 3. Behavioural claims, verified from the source (not from the Verifier's record)

1. **No check at launch.** `run_gui`'s tail (locate by `AppHelper.runEventLoop()`)
   now reads `_upd_cache["t"] = time.time()`; the module-level initialiser is
   `{"t": 0.0, "busy": False}`, so without the stamp the priming refresh would
   check immediately (my mutant R09 confirms the tests see that). No
   `Thread(target=_run_update_check)` remains anywhere (`grep -n _run_update_check`
   → definition, worker call, `checkUpdate_` call only).
2. **First periodic check ≈ launch + 1 h, via the 30 s worker.** The gate in
   `Ticker.refresh_.work` is strict `>` against `UPDATE_CHECK_SEC = 3600`, and it
   runs at the end of each 30 s refresh, so the first check lands on the first
   refresh after 3600 s (launch + 3600 s + ≤ 30 s). `poll_github_update` stamps
   `_upd_cache["t"]` only when `status != "failed"`, so a failed check is retried
   on the following refreshes (pre-existing behaviour, unchanged) — "1시간마다" is
   the cadence between successful checks, and the notes/CLAUDE.md sentence read
   correctly at user granularity.
3. **Manual path installs immediately and quits for relaunch.** `checkUpdate_`
   starts one daemon thread; `_run_update_check()` → `poll_github_update(state)`;
   on `'update'` it reads the `(tag, url)` the poll just published and calls
   `install_github_update(upd[1], expect_version=upd[0])` — the same call shape as
   the existing `doUpdate_` — then `performSelectorOnMainThread_("quitApp:")`, and
   `quitApp_` is `NSApplication.terminate_`, so the replacement script relaunches
   exactly as for the menu's Install item. `install_github_update` refuses an empty
   `expect_version` before downloading, and `validate_update_app(..., expect_version)`
   checks the bundle's version — so the installed bundle is the tag that was offered.
4. **Alerts only on the main thread.** `checkUpdate_.work` never names `NSAlert`; it
   dispatches `"showUpdateMessage:"` with the message via
   `performSelectorOnMainThread_withObject_waitUntilDone_`. `showUpdateMessage_`
   builds the `NSAlert` and calls `runModal()` there. Status → message map:
   install failure → `upd_install_failed`; `'current'` → `upd_current` with
   `v=APP_VERSION`; `None` (busy) → `upd_busy`; anything else (`'failed'`) →
   `upd_failed`. `check_github_update` catches every exception and returns
   `'failed'`, so the worker thread cannot die silently on a network error.
5. **Direct to latest — 0.20 → 0.24 in one step.** `check_github_update` builds
   exactly one request, to `https://api.github.com/repos/{GITHUB_REPO}/releases/latest`,
   reads that response's `tag_name`, returns `'current'` when
   `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)` and otherwise
   `('update', tag, url)` for the asset `select_update_asset` picks for this
   machine. Nothing lists `/releases`, nothing walks versions, and the installer
   verifies against that same tag. The function is unchanged from HEAD (§2).

## 4. Release notes

- Bytes from the `**v0.22**` heading to EOF: SHA-256
  `6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239` in both the
  working tree and `git show HEAD:RELEASE_NOTES.md` (heading occurs once in each;
  suffix byte-equal; the prefix above the v0.23 section is byte-equal to HEAD's
  prefix above v0.22). No published byte moved.
- `**v0.23**` section: **3** top-level bullets, **0** nested, **222** characters
  with whitespace normalised (≤ 450), **2** sentences per bullet, Korean, user
  perspective (what happens at launch / what to click / what not to redo). No
  hash, path, line, identifier, or test prose; no magnitude/frequency word — the
  contract test's `FORBIDDEN_NOTE_PATTERNS` scan passes and I re-ran it.
- Figures: "1시간" ↔ `UPDATE_CHECK_SEC = 3600` (auditable in the tree; the contract
  test compares them in seconds). Quoted label `"업데이트 확인…"` equals
  `TR["ko"]["menu_check_update"]` = `"⬆︎ 업데이트 확인…"` minus its glyph.
- The Danger-zone recalibration warning is correctly absent: no estimator
  function changed (§2), and the third bullet says so.

## 5. Findings

Blocking: **none**.

Advisory A — **the launch stamp sits two statements after the priming refresh.**
`ticker.refresh_(None)` (which starts the priming worker) runs before
`_upd_cache["t"] = time.time()`. The worker only reaches the gate after
`compute_usage()`, `fetch_exact_usage()`, `fetch_api_cost_today()` and
`compute_onboard_state()`, every one of which does file or network I/O and so
yields the GIL, while the main thread has only `set_override("waving")` and the
stamp left to run — so in practice the stamp always lands first and I could not
construct a realistic schedule where a launch check slips through. It is still an
ordering the code does not enforce. Moving the stamp above `ticker.refresh_(None)`
would make it unconditional; the schedule test would still pass (one stamp, before
the event loop). Not required for this release; recorded so the next change to
that tail knows the ordering matters.

Advisory B — **`showUpdateMessage_` does not activate the app before `runModal()`.**
The uninstall alert calls `NSApplication.sharedApplication().activateIgnoringOtherApps_(True)`
first; `settings_error` does not. This is an `LSUIElement` app, so if the user
switches to another app during the (network-bound) check, the result alert may
appear without keyboard focus. Cosmetic; the alert still shows. The Verifier's
record already notes that no live GUI run was done.

Not findings, noted for completeness: a manual check that races the hourly one
reports `upd_busy` (documented and localised); a manual check that fails on the
network while an Install item is already pending says `upd_failed` rather than
pointing at the pending item — correct, if slightly conservative.

## 6. The two test modules, read in full

- `tests/test_update_check_schedule.py` (22 cases): source pins by AST — literal
  `3600`; no scheduler handed `_run_update_check`, no top-level call at launch
  (bare or attribute, incl. `checkUpdate_`/`doUpdate_`); a **closed list of exactly
  two** `_run_update_check` references located by parent chain
  (`Ticker.refresh_.work` gate, `Handler.checkUpdate_.work` assignment to `status`);
  stamp once, before the event loop, the only write to `_upd_cache['t']` in
  `run_gui`; the gate text, strict `>`, `UPDATE_CHECK_SEC`; the closure's two
  returns; menu item wiring and ordering after the version row; six keys × four
  locales with distinct labels. Executed-out-of-AST cases for the closure (busy →
  `None`, status pass-through, busy cleared on raise), for `checkUpdate_` (install
  with `expect_version`, quit-only on success, each message key, no `NSAlert` on
  the worker, selector set exactly `{showUpdateMessage:, quitApp:}`), for
  `showUpdateMessage_`; direct-to-latest with `APP_VERSION` patched to `0.20` and a
  stubbed `urlopen` answering `v0.24` (one request, to `/releases/latest`; the
  same payload is `'current'` at 0.24 and 0.25, which kills an always-`'update'`
  rival); a fake-clock cadence gate (not due at +0/+30/+3599/+3600, due at +3601,
  then one interval later, never once an update is pending). `_upd_cache` is saved
  and restored; nothing under `~` is read.
- `tests/test_v023_release_contract.py` (11 cases): `APP_VERSION == ["0.23"]`;
  verifier usage shows 0.23 and none of 0.21/0.22/0.24; the three pins equal the
  current hashes; published-suffix pin; v0.23 directly above v0.22 and unique;
  format rule (3 bullets, no nesting, ≤ 450, 1–2 sentences, Korean); the three
  user-facing claims present; forbidden-pattern scan; `1시간` ↔ `UPDATE_CHECK_SEC`
  both ways with no stray 분/초 figure; label ↔ `TR["ko"]`; `run_gui` top level
  stamps once and never reaches the check; `check_github_update` reads exactly
  `/releases/latest` and compares `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)`;
  CLAUDE.md says "every hour"/"never at launch" and no longer "every 6 hours";
  the durable release-note policy test carried over.

Both modules build every fixture by hand and never touch the real corpus or
`~/.claude_pet` (CLAUDE.md testing policy).

## 7. Gates re-run by the Reviewer (repository root, 2026-09-11T01:36:36Z → 01:37:40Z)

```
python3 -m unittest discover -s tests -p test_update_check_schedule.py      → Ran 22 tests in 0.334s / OK
python3 -m unittest discover -s tests -p test_v023_release_contract.py      → Ran 11 tests in 0.135s / OK
python3 -m unittest discover -s tests -p test_upload_artifact_gate.py       → Ran 64 tests in 48.822s / OK
python3 -m unittest discover -s tests -p test_manual_update_transaction.py  → Ran 18 tests in 13.849s / OK
```

Repins: `tests/test_upload_artifact_gate.py` `REVIEWED_APP_SOURCE_SHA256` and
`tests/test_manual_update_transaction.py` `REVIEWED_APP_SOURCE_SHA256` both equal
the current `claude_pet.py` hash `57b24a28…`; `REVIEWED_VERIFIER_SHA256` equals the
current `verify_release_artifact.py` hash `fc0d38f6…`; `REVIEWED_RELEASE_SHA256`
still equals `release.sh` (unchanged). The upload gate ran its 64 cases rather
than refusing, which is the operative proof.

## 8. Reviewer's own mutants — 11 of 11 RED

Scratch only (`…/scratchpad/reviewer_mutants/`, driver `run_mutants.py`). Grouping
key: one mutant = one fresh copy of the eight files the two modules read, with one
textual change whose needle occurs exactly once, run with `python3 -m unittest
discover -s tests -p <module>` from the mutant root (baseline first confirmed
`import claude_pet` resolves to the mutant copy). Measured
2026-09-11T01:38:19Z → 01:38:25Z. Baselines: schedule `Ran 22 tests` / `OK`;
contract `Ran 11 tests` / `OK`.

| # | Mutant | Module | Verbatim failing line |
| --- | --- | --- | --- |
| R01 | restore `threading.Thread(target=_run_update_check, daemon=True).start()` in place of the stamp | schedule | `AssertionError: True is not false : an update check is due at launch+0s; _upd_cache['t']=0.0` (failures=4) |
| R02 | `UPDATE_CHECK_SEC = 30 * 60` | schedule | `AssertionError: True is not false : an update check is due at launch+3599s; _upd_cache['t']=1700000000.0` (failures=2) |
| R02b | same mutant | contract | `AssertionError: claude_pet.py:UPDATE_CHECK_SEC must remain a literal` (failures=2) |
| R03 | `checkUpdate_` installs without `expect_version` | schedule | `AssertionError: expected call not found.` (failures=3) |
| R04 | 4th top-level bullet in v0.23 | contract | `AssertionError: 4 != 3 : v0.23 must have exactly 3 top-level bullets, got 4` |
| R05 | `check_github_update` reads `/releases` instead of `/releases/latest` | schedule | `AssertionError: Lists differ: ['https://api.github.com/repos/uygnoey/claude-pet/releases'] != ['https://api.github.com/repos/uygnoey/claude-pet/releases/latest']` (failures=2) |
| R06 | worker gate `>=` instead of `>` | schedule | `AssertionError: True is not false : an update check is due at launch+3600s; _upd_cache['t']=1700000000.0` (failures=2) |
| R07 | CLAUDE.md back to "every 6 hours" | contract | `AssertionError: "polls the repo's latest release tag every hour" not found in …` |
| R08 | busy (`None`) mapped to `upd_failed` | schedule | `AssertionError: Lists differ: [('showUpdateMessage:', '<upd_failed>', False)] != [('showUpdateMessage:', '<upd_busy>', False)]` |
| R09 | launch stamp dropped | schedule | `AssertionError: True is not false : an update check is due at launch+0s; _upd_cache['t']=0.0` (failures=2) |
| R10 | one published v0.22 byte altered | contract | `AssertionError: 'b33ff14b…' != '6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239'` |

## 9. Full suite, run by the Reviewer from the repository root

```
python3 -m unittest discover -s tests -v
start 2026-09-11T01:37:59Z
Ran 508 tests in 338.454s
OK (skipped=7)
rc=0
end 2026-09-11T01:43:37Z
```

Verbose log kept in the scratchpad (`reviewer_full_suite.log`); no `FAIL`/`ERROR`
line in it. The seven skips are the same seven the Verifier recorded, all opt-in
live checks that skip loudly by design and would otherwise inspect the installed
v0.22 bundle, which this assignment forbids:

- `test_updater.RealBundleAcceptanceTests` × 2 — `skipped 'the installed-app preflight is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
- `test_updater.StaplerLiveContractTests` × 2 — `skipped 'the real stapler contract is an opt-in live check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it'`
- `test_v020_boundaries.B3Updater` × 3 (`test_github_choice_binds_v021_tag_asset_and_arch_without_network`, `test_invalid_candidates_are_refused_before_handoff`, `test_well_formed_v021_reaches_one_sandbox_handoff`) — `skipped 'live installed-v0.20 to checkout-v0.21 boundary requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1'`

The Reviewer's own mutants (§8) ran in scratch copies while this suite was
running from the checkout; the two never shared a file. Source hashes after the
run: `claude_pet.py` `57b24a28…`, `verify_release_artifact.py` `fc0d38f6…`,
`RELEASE_NOTES.md` `6e0b1cdf…` — unchanged. `git status --porcelain` at the end is
identical to §1.

This is the Reviewer's pre-commit run. It does **not** stand in for §6 item 2 —
the Verifier's re-run from the clean tracked tree after the release commit.

## 10. Verifier record, privacy, untracked files

- **§5 fields in `docs-design/release-v023-verification-20260911.md`:** UTC start/end
  and a separate suite window; source hashes (all four reproduced above, including
  `RELEASE_NOTES.md` `6e0b1cdf…`); RED evidence quoted verbatim per module with
  `Ran`/`FAILED` lines; the mutation table with grouping key, 25/25 as numerator and
  denominator, and a measurement window; the seven skips named with their skip
  reasons; `stat` before/after for the user-owned files. Direct-to-latest is stated
  as a source fact, not an observation (AGENTS.md §5 slot rule). No claim in the
  record failed to reproduce.
- **Privacy:** every added line of `claude_pet.py` was grepped for `print(`, `log(`,
  `_dbg`, `path`, `session` — none. The only new user-visible strings are the 24 TR
  entries; `showUpdateMessage_` shows `str(msg)` where `msg` is always a `t()`
  string. No transcript content, project path or session id can reach the alert,
  stdout, or the debug log through this change.
- **User-owned files:** `stat -f '%m %N'` at 01:34:28Z and at the end (§9) identical:
  `1784689621 diag.py`, `1783953996 release/icon_1024.png`,
  `1783953996 release/ClaudePet.iconset`. No other agent's `docs-design/` record was
  opened for writing.

## 11. What remains (not this record's to do)

For whoever stages the release commit **by name** (CLAUDE.md step 2 — never
`git add -A`/`.`), the paths this release changed are: `claude_pet.py`,
`verify_release_artifact.py`, `RELEASE_NOTES.md`, `CLAUDE.md`,
`tests/test_update_check_schedule.py`, `tests/test_v023_release_contract.py`
(rename from `tests/test_v022_release_contract.py`, already staged as `R100`),
`tests/test_upload_artifact_gate.py`, `tests/test_manual_update_transaction.py`,
`docs-design/release-v023-verification-20260911.md`, and this file. Read back
`git diff --cached --name-only` before committing. The commit carries
`Developer:` / `Verifier:` trailers naming different parties (§7).

After the release commit: the §6 execution gate — the Verifier's suite re-run from
the clean tracked tree, the Coordinator's recorded sign-off, and a named release
operator who held **no** role on this release. I held the Reviewer role and am
therefore ineligible to operate it.
