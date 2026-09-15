# ClaudePet v0.25 — Reviewer record for the release commit (AGENTS.md §1, §8 item 4)

## Verdict: **FAIL** — 2 blocking items (B1, B2), both one-line documentation defects
## introduced by this commit; no defect found in the production change, the notes, the
## CLAUDE.md paragraph, the test rename, or the trailers.

- **Reviewer:** `reviewer-v025` — a Claude Code subagent spawned for this review. Held **no
  other role on this release**: not Developer, not Verifier, not Coordinator, not the gate
  verifier (`gate-verifier-v025`, `docs-design/release-v025-gate-20260914.md`). It edited no
  tracked file, ran no git write command, ran nothing from `release.sh` or `build_app.sh`,
  started no GUI, read no `~/.claude` transcript, wrote nothing under `~/.claude_pet/`, and
  touched no untracked file other than creating this one. Having now reviewed the release, it
  is **not** eligible to operate it (§1).
- **Written (UTC):** 2026-09-14T04:05Z.
- **Subject:** exactly what the gate record named unreviewed — `git show aaf0ca6` ("release:
  ClaudePet v0.25"), branch `main`, tracked tree clean (`git status --porcelain
  --untracked-files=no` → 0 lines).
- **Mutation work** was done in a throwaway tree built with `git archive aaf0ca6 | tar -x -C
  <scratchpad>`; the worktree was never modified. `shasum -a 256 claude_pet.py` in the
  worktree after the review: `8d0ed11cafbc27ef00d31341e5499e447412963c0ceac02bd0a4fa9e8660eb0c`
  — the value the pins name.

---

## Blocking items

### B1 — `README.es.md` quotes a "Start at sign-in" menu label the app does not have

`README.es.md:21`, both cells of the row this commit rewrote:

```
| Inicio al iniciar sesión | Menú contextual → “Iniciar al iniciar sesión” | Menú contextual → “Iniciar al iniciar sesión” (también como opción del instalador) |
```

The Spanish menu item is **`"Abrir al iniciar sesión"`** — `TR["es"]["menu_autostart"]`,
`claude_pet.py:1318` (and `autostart_title` / `autostart_unavailable` beside it use the same
verb). The Windows port draws the same string: `windows/claude_pet_win.py` builds the item
from `cp.t("menu_autostart")`, so the mismatch is on both platforms.

The other three locales quote their source string exactly — `README.md` "Start at sign-in" =
`TR["en"]`, `README.ko.md` "로그인 시 자동 실행" = `TR["ko"]`, `README.ja.md`
"サインイン時に自動起動" = `TR["ja"]` — so this is also the inter-README inconsistency review
item (c) asks about: three READMEs name the button, one names a button that is not there.

Nothing catches it: `tests/test_v025_release_contract.py` pins only `KO_AUTOSTART_LABEL`
against `TR["ko"]`, and `test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string`
checks the other locales for *key presence*, never for the README text.

**Fix:** either change the two cells to “Abrir al iniciar sesión”, or change
`TR["es"]["menu_autostart"]` (and `autostart_title`, `autostart_unavailable`) — but the second
is a production edit and would re-pin three reviewed hashes, so the README edit is the cheap
and correct one.

### B2 — the rewritten row promises the menu toggle to macOS 12 users, where it is disabled

All four READMEs, same row. The macOS cell now reads (EN) "Right-click menu → “Start at
sign-in”", and the **System Settings → General → Login Items** path it replaced is gone from
the table.

The same table's OS row says **"macOS 12 or later"**. `SMAppService` does not exist on macOS
12 — the source says so itself (`claude_pet.py:5186`, "macOS 12 에는 SMAppService 클래스가
없고"), `autostart_service()` returns `None` on the import failure (`claude_pet.py:5182-5198`),
`autostart_read_state()` then returns `"unavailable"`, and the menu retitles the item
`autostart_unavailable` and calls `setEnabled_(False)` (`claude_pet.py:6968-6973`). So a macOS
12 user reads an instruction for a greyed-out item reading "Start at sign-in (not available
here)", and the row no longer tells them the one path that does work for them.

This is a regression the rewrite introduced: the previous cell was accurate for every OS
version the table claims to support.

**Fix:** qualify the macOS cell (e.g. "Right-click menu → “Start at sign-in” (macOS 13+;
on macOS 12, System Settings → General → Login Items)"), in all four languages — or narrow
the OS row. Either is a documentation-only edit.

---

## What was checked, and what held

### (a) The production change is exactly two lines, and nothing rode along — **PASS**

`git show aaf0ca6 --name-status` lists 14 paths. Of them exactly two are production files
under CLAUDE.md's repo layout, and each is a one-line change:

| file | change | effect |
| --- | --- | --- |
| `claude_pet.py:937` | `APP_VERSION = "0.24"` → `"0.25"` | the single version literal; `setup.py` derives both plist keys from it by regex, so `CFBundleShortVersionString` follows without a second literal |
| `verify_release_artifact.py:28` | usage example `--expect-version 0.24` → `0.25` | **inside the module docstring.** No behaviour: `--expect-version` is `required=True` at `:188` and `release.sh:141` passes `$(cur_version)`, which greps `APP_VERSION` out of `claude_pet.py`. |

The other twelve paths are four READMEs, `RELEASE_NOTES.md`, `CLAUDE.md`, three `docs-design/`
records, and three test files (the rename plus two hash re-pins). `git grep` for `0.24` /
`0.25` over tracked `*.py`/`*.sh`/`*.plist` outside `tests/` and `windows/` returns only those
two lines plus an unrelated `"max_dt_s": 0.25`. No production file other than these two was
touched, and neither `setup.py`, `release.sh`, `build_app.sh`, `entitlements.plist`,
`launcher.c` nor anything under `frames/`, `fonts/`, `.claude_pet/` appears in the commit.

The three re-pinned hashes were re-derived here with `shasum -a 256` at 04:00Z and all match
the tree: `claude_pet.py` `8d0ed11c…60eb0c` (pinned twice), `verify_release_artifact.py`
`2223ee44…3fdcb3`, and the two unchanged pins `release.sh` `a5b25686…146e23`, `build_app.sh`
`db8e1ff9…dd96b`. `python3 -m unittest tests.test_v025_release_contract
tests.test_manual_update_transaction tests.test_upload_artifact_gate` → `Ran 108 tests … OK`,
i.e. the fail-closed modules ran rather than refusing.

### (b) The three notes claims — each traced, with its evidence class named — **PASS with a scope caveat**

The staged section:

```
- Claude Code가 토큰을 갱신하거나 서버 응답이 잠깐 실패해도 재시작 없이 정확 모드로 돌아옵니다. 추정 모드(≈)에 갇히던 문제가 사라졌고, 따로 할 일은 없습니다.
- 우클릭 메뉴에 "로그인 시 자동 실행"이 생겼습니다. Mac과 Windows 모두 여기서 켜고 끌 수 있고, 시스템 설정이나 작업 관리자에서 끄면 메뉴에도 꺼진 것으로 보입니다.
- Windows도 앱 안에서 새 버전을 확인해 설치합니다(설치 파일형·무설치 zip 모두). "완전 삭제…"는 설정과 캐시까지 지우고 내 펫 폴더는 남깁니다.
```

**Bullet 1 — token-cache recovery. Evidence: source read in this tree** (the strongest class;
deterministic and checkable by anyone, so it is cited, not "observed" — AGENTS.md §5).
`_read_oauth_token()` (`claude_pet.py:~2360`) drops a cached `src=="file"` token when
`_credentials_sig()` changes (rotation), re-validates a `suspect` token through
`_revalidate_oauth_token()` — file and `security` CLI only, never the prompting native path —
and forgets a token the server rejected. `_fetch_oauth_usage()` (`:2650`) re-reads once with
`force=True` on 401/403, calls `_forget_oauth_token` when no replacement exists, and sets
`c["suspect"] = True` on 5xx / net / parse. `fetch_exact_usage()` (`:2875`) rewinds
`_oauth_cache["t"]` so a failed fetch expires after `OAUTH_FAIL_RETRY_SEC = 60` instead of
`OAUTH_CACHE_SEC = 180`, with `http:429` excluded. Every clause of the bullet lands on code in
this commit's tree. The bullet claims no magnitude and no frequency, and quotes no number.

**Bullet 2 — the sign-in menu item. macOS half: source read plus one hardware exercise.**
Source: the item is built in `run_gui`'s context menu (`claude_pet.py:6948`), its checkmark
comes from the `autostart_read` hook (`:6677` → `autostart_read_state(*autostart_current())`)
which is re-evaluated **every time the menu is built**, so a change made in System Settings is
reflected; no autostart function writes the config or `RUNTIME` (pinned by the contract test,
and I re-checked the four function bodies). Exercise: `docs-design/track-b-verification-20260913.md`,
the addendum this commit adds — a bundle built by `./build_app.sh build` from `f09c97d`,
launched with a scratch `HOME`, driven with synthetic Quartz events, menu captured per step,
`status()` read from the bundle's own interpreter: 3 (NotFound) → enabled/unchecked → checked
→ 0 (NotRegistered). That is **one machine, one run, correctly labelled as such in the
record** — it establishes that the path works, not how often it works (§5), which is all the
bullet needs. B2 above is the one place this bullet's *README* counterpart overreaches; the
notes bullet itself does not name an OS version and is not overstated.

**Bullet 2 Windows half and bullet 3 — true of the `windows` branch, not of this tree.**
`origin/windows` (`6d94c4d`) contains `aaf0ca6`. There: the menu item is rebuilt on
`aboutToShow` and read through `win_autostart.autostart_read_state`
(`windows/claude_pet_win.py:1099-1103, 1156-1167`) — the Task-Manager claim; the hourly check
is `time.time() - cp._upd_cache["t"] > cp.UPDATE_CHECK_SEC` with no check at launch
(`:888-893`); `win_update.verify_download()` checks **size first, then SHA-256, and refuses a
missing or malformed digest even when the size matches** (`windows/win_update.py:357-384`);
`uninstall_plan()` (`:742-759`) deletes the per-user files and `cache_dir(home)`, appends the
kind step, and **never names `home\.claude_pet`** — bullet 3's "내 펫 폴더는 남깁니다", stated
in the docstring and asserted in the Windows suite; `delete_run_value_if_ours(exe)`
(`windows/claude_pet_win.py:278, 1331`) removes the Run value on uninstall. Track F
(`docs-design/track-f-verification-20260914.md`, `track-f-review-20260914.md`) records the
hardware pass on the user's Windows 11 machine and a reviewer verdict of **PASS** at round 4
after three FAIL rounds.

**The caveat, and it is the gate's W1, not a new finding.** Nothing in *this* tree ships
Windows behaviour, and the two Windows files sitting in `release/` are byte-identical to the
v0.24 build. Bullets 2 and 3 become true for Windows users only when Windows artefacts built
from `windows` at `6d94c4d` or later are the ones uploaded. The notes are not overstated *as
notes* — they describe v0.25 — but publishing them beside v0.24 Windows binaries would make
them false, which is exactly what W1 blocks.

### (c) The four README rows — **FAIL (B1, B2)**; everything else in the rows is consistent

The Updates row is uniform across the four languages and matches the source: macOS
`UPDATE_CHECK_SEC = 3600` with no check at launch, install from the right-click menu; Windows
the same cadence, now qualified "(installer or portable zip)" / "(설치 파일형·무설치 zip
모두)" / "（インストーラー版・ポータブル zip 版とも）" / "(instalador o zip portátil)". The
Windows cell no longer says "download the new installer from the releases page", which was
the pre-v0.25 behaviour — correctly removed. The Start-at-sign-in row is uniform in shape
(menu on both platforms, installer option noted for Windows) and correct in three locales;
B1 is its Spanish text and B2 its macOS-12 scope.

### (d) The CLAUDE.md paragraph — **PASS**, one imprecision worth a later touch-up

Claim by claim: `release.sh:22,24` set `PY="${PY:-$HOME/.pyenv/shims/python3}"` and
`UPY="${UPY:-/Library/Frameworks/Python.framework/Versions/Current/bin/python3}"` — the pyenv
one and the python.org universal2 one, as stated. The toggle imports the framework **at call
time**: `from ServiceManagement import SMAppService` inside `autostart_service()`
(`claude_pet.py:5191`) and inside `autostart_open_login_items()` (`:5299`) — no module-level
import. `setup.py:36` lists `"ServiceManagement"` in py2app `includes`, with a comment saying
what happens if it is missing. The stated consequence is exactly what the code does: an
`ImportError` → `autostart_service()` returns `None` → `"unavailable"` → the menu item is
retitled and disabled, on every machine, because the missing framework is baked into the
bundle. The remedy the paragraph gives was executed here read-only and both interpreters pass
today:

```
$HOME/.pyenv/shims/python3 -c 'import ServiceManagement'                      → ok
/Library/Frameworks/.../Versions/Current/bin/python3 -c 'import ServiceManagement' → ok
```

Placement is right: it sits immediately under the four build commands in **Run, test, build**,
which is the block a reader opens before a release build — the moment the check is actionable.

*Imprecision (non-blocking):* "`build_app.sh` takes the first `python3` it finds" — `find_py()`
(`build_app.sh:393-406`) takes the first candidate that **also imports `AppKit`**, pyenv first.
The paragraph's conclusion is unaffected (a Python with AppKit but without ServiceManagement is
precisely the 2026-09-13 case), but the sentence would be more useful as "the first `python3`
that imports AppKit".

### (e) The contract-module rename — **PASS**; the v0.24 assertions survive and two new ones were shown to discriminate

**Preserved.** `git show aaf0ca6^:tests/test_v024_release_contract.py` → class
`StagedV024NotesFormatTests` with seven test methods. In the renamed file that class is
`PublishedV024NotesContractTests` with the **same seven method names**, and a line-by-line diff
of the two class bodies shows the only change is the docstring (staged → published). Every
`self.assert…` line is byte-identical. Nothing was dropped, relaxed or reordered. The rename
additionally *adds* a freeze: `test_published_v024_and_older_bytes_are_untouched` pins the
sha256 of everything from `**v0.24**` to EOF, and
`test_v025_is_the_only_unpublished_heading_and_sits_directly_above_v024` pins the ordering.
The v0.23 classes and `ReleaseNotesPolicyTests` are likewise carried over unchanged.

**Discriminating.** Three mutants, in the throwaway tree only, each run against the single test
it should break (AGENTS.md §3 — a rival that collapses onto the correct answer proves nothing):

| mutant (the rival it embodies) | test | observed failure |
| --- | --- | --- |
| `OAUTH_FAIL_RETRY_SEC = 60` → `180` — "a retry constant no shorter than the cache, which changes nothing" | `test_v025_exact_mode_recovery_is_backed_by_the_token_cache` | `AssertionError: 180 not less than 180 : OAUTH_FAIL_RETRY_SEC=180 must be shorter than OAUTH_CACHE_SEC=180` |
| `autostart_read_state` returns a stored `RUNTIME["autostart"]` flag when present, falling through to `status()` otherwise — "a stored flag that goes stale the moment System Settings turns the item off" | `test_v025_autostart_state_is_read_from_the_os_and_never_stored` | `AssertionError: - ['RUNTIME'] + [] : autostart_read_state must not touch the config or RUNTIME: ['RUNTIME']` |
| `USER_PET_HOME` prepended to `UNINSTALL_PATHS` — "the pet home added to the list to clean up completely" | `test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it` | `AssertionError: 'USER_PET_HOME' unexpectedly found in {'CONFIG_PATH', 'UPDATE_LOCK_DIR', 'USER_PET_HOME'} : UNINSTALL_PATHS must never name the user's pet home` |

Note the second mutant is the interesting one: it keeps `status()` at exactly one call site, so
the count assertion still passes — the `forbidden`-names assertion is what catches it. The
unmutated tree runs all five `StagedV025NotesFormatTests` green.

### (f) Privacy — **PASS**

The whole diff contains six lines matching `\.claude/projects|sessionId|\.jsonl|/Users/`. Three
are **removed** lines in the Track E deferral, naming other tools' log *locations* with
wildcards (`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, `~/.grok/logs/unified.jsonl`,
`~/.gemini/tmp/*/chats/*.jsonl`) — no real path, no id, and they are being deleted. Three are
`/Users/yeongyu/claude-pet` — the repository root itself, in a verification record's `cwd` and
a traceback. No transcript path, no project directory name, no session id from `~/.claude`, no
message body, no token, no fixture derived from real data. The added
`docs-design/release-v025-verification-20260913.md` (477 lines) logs counts, hashes and
assertion text only.

*Observation, not a finding:* the commit trailers carry this coding session's own UUID and a
`claude.ai/code/session_…` URL. That is the harness's required attribution and matches every
recent commit here; it is not the app writing out a user's transcript id, which is what
CLAUDE.md §Privacy governs.

### (g) Authorization quote and trailers — **PASS on form; one thing I cannot verify**

**Trailers (§7).** `Developer: Claude (session 55c3dee4-…), with developer-a / developer-b /
developer-f on the tracks` and `Verifier: verifier-a / verifier-b … and the
release-preparation verifier …`. Present, and they name **different parties** — §7's hard
block is satisfied. The `Verifier:` line also points at the records that back it
(`docs-design/track-{a,b}-*-20260913.md`, `release-v025-verification-20260913.md`), and I
confirmed all three exist and describe the work claimed. No §2 Condition C exception is
declared, and none appears needed: `verify-v025`'s record states it edited only files under
`tests/`, disjoint from the two production files.

**The quote.** The body records, verbatim and in the user's own language: `"그거 다되면,
릴리즈까지 마무리 해놔라! 그리고 세션 모두 종료해!"` and `"다 되면 릴리즈하고 세션 모두
종료해~!"`. Form is right — AGENTS.md §6 requires exactly this (human's own words, quoted
verbatim, in the change description), and this is a blanket authorization of the sequence,
which that section permits.

**What I could not check, stated plainly.** No record in this repository corroborates the
words: `grep -rn` for either string across `docs-design/` returns nothing, and the commit body
is their only copy. A Reviewer reading `git log` months from now is in the same position. That
is not a defect in the commit — §6 asks for the quote to be recorded, and it is — but it means
**no agent may treat this record, or the commit body, as the authorization itself** (§6 guard
3). Two consequences for whoever runs step 3 onward:

- The quote's scope, read literally, is "finish through the release". It names no artefact and
  does not mention signing or notarization, which CLAUDE.md gates `[ASK-OP]` as "explicitly
  authorized signing **this artifact**, per-instance". A blanket grant is allowed to cover it,
  but the operator should satisfy itself of that with the user rather than inferring it here.
- Blanket authorization changes **only** who must be asked between steps: every execution-gate
  item must still be true and recorded first, and it makes no ineligible agent eligible.

---

## Non-blocking notes

- **N1 — the README banner still reads v0.24.** Line 8 of all four READMEs: "🧪 v0.24 — the
  macOS app is notarized; …". Its substance is still true, only the version label is stale;
  v0.24's own preparation updated this line (`217c351`), so leaving it now breaks that
  practice and the repo front page will announce v0.24 for a v0.25 release. Nothing asserts
  it. One-word edit, in the same four files B1 and B2 touch.
- **N2 — the main session holds Coordinator and Developer on this release.** §1 caps an agent
  at one role per change, and the gate record's §5-2 lists the session under both. The
  practical consequence (ineligible to operate) is already recorded and no §2 separation is
  harmed — the Verifier is a different party — but the commit body does not mention the
  doubling. Worth a line from the Coordinator rather than a fix.
- **N3 — the two merge commits carry no trailers** (the gate's M1). Neither introduces content
  of its own and every merge in this repository's history is the same shape. Recorded, not
  blocking, and unchanged by this review.
- **N4 — `docs-design/release-v025-gate-20260914.md` and this file are untracked.** Every
  release v0.22–v0.24 has its gate, verification and review records tracked. If that practice
  continues, the Coordinator stages these two by name — never by a sweep, per CLAUDE.md's ban
  on `git add -A` for a release commit, with `diag.py`, `release/ClaudePet.iconset/` and
  `release/icon_1024.png` untracked and un-ignored.

---

## What this review did and did not do

Ran: `git` read commands (`show`, `log`, `status`, `ls-files`, `ls-tree`, `branch`,
`archive`, `diff`), `shasum -a 256`, `grep`/`sed`/`cat` over tracked files, two
`python3 -c 'import ServiceManagement'` probes, `python3 -m unittest` on three modules in the
worktree (read-only) and on single tests in the throwaway tree.

Did not: edit or create any tracked file; run any git write command; run anything from
`release.sh` or `build_app.sh`; start the GUI; read `~/.claude`; write `~/.claude_pet/` or
`~/.claude_pet.json`; touch `diag.py`, `release/ClaudePet.iconset/`, `release/icon_1024.png`,
or any other untracked file. The only path this task created is this one.

**Bearing on the gate:** this record closes **R1** for everything except B1 and B2 — i.e. the
release commit has now been read by a Reviewer with no other role, and the finding is two
documentation defects. **C4** (the Coordinator's recorded sign-off), **C5** (a named eligible
operator) and **W1** (the Windows artefacts) are untouched by this review and remain
outstanding. Nothing from CLAUDE.md release step 3 onward may run until all of them are closed
and recorded.
