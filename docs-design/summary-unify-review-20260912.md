# Review record — summary-pill unification (staged v0.24)

Reviewer: reviewer-v024 (Claude). Held no other role on this change: did not write the
production change (Developer: Claude, session 55c3dee4-727f-4a94-b960-66540b129014) and
did not write or run-first the gating tests (Verifier: verifier-v024). Read-only except
for this file, which is untracked and not committed by the Reviewer.

Window: 2026-09-12T12:55:52Z (first command) – 13:05:18Z (final snapshot), UTC. All
commands ran with cwd `/Users/yeongyu/claude-pet` unless a scratch cwd is stated. Output
excerpts are verbatim. Line numbers are approximate by CLAUDE.md's own rule; locate by
symbol.

**Verdict: FAIL — three blocking findings (§7), one in code, one in the staged release
note, one in CLAUDE.md. Everything else reviewed is sound; the Verifier's fixtures
discriminate (§5).**

## 1. What was reviewed

```
$ git rev-parse HEAD ; git log --oneline -3
92fe4ee5a67bf7a693a90e328c6c7e582ab63b38
92fe4ee docs: refresh Claude Pet Pages for v0.23 and search discovery
046d166 docs: record the v0.23 execution gate — clean-tree suite re-run at 81619b3e and Coordinator sign-off
81619b3 release: ClaudePet v0.23
$ git status --porcelain            # 12:55:52Z and again 13:05:18Z — identical
 M CLAUDE.md
 M README.es.md
 M README.ja.md
 M README.ko.md
 M README.md
 M RELEASE_NOTES.md
 M build_app.sh
 M claude_pet.py
 M preview.png
 M setup.py
 M tests/test_companion_motion.py
 M tests/test_manual_update_transaction.py
 M tests/test_settings_and_install.py
 M tests/test_upload_artifact_gate.py
 M tests/test_v023_release_contract.py
?? diag.py
?? docs-design/companion-play-live-20260909.jsonl
?? docs-design/companion-play-live-20260909.png
?? docs-design/companion-play-native-20260909.json
?? docs-design/companion-play-native-20260909.png
?? docs-design/free-roaming-live-20260909.jsonl
?? docs-design/free-roaming-live-20260909.png
?? docs-design/free-roaming-native-20260909.json
?? docs-design/free-roaming-native-20260909.png
?? docs-design/quiet-companion-compact-smoke.json
?? docs-design/quiet-companion-compact-smoke.png
?? docs-design/quiet-companion-live-contact.png
?? docs-design/quiet-companion-live-trace.jsonl
?? docs-design/quiet-companion-release-operator.md
?? docs-design/quiet-companion-smoke.json
?? docs-design/quiet-companion-smoke.png
?? docs-design/release-v022-operator-20260911.md
?? docs-design/release-v023-operator-20260911.md
?? docs-design/summary-unify-verification-20260912.md
?? fonts/
?? release/ClaudePet.iconset/
?? release/icon_1024.png
?? tests/test_nested_pets.py
?? tests/test_summary_pill.py
$ git diff --stat
 CLAUDE.md                               | 115 +++---
 README.es.md                            |  35 +-
 README.ja.md                            |  32 +-
 README.ko.md                            |  32 +-
 README.md                               |  33 +-
 RELEASE_NOTES.md                        |   6 +
 build_app.sh                            |  23 ++
 claude_pet.py                           | 689 +++++++++++++++++---------------
 preview.png                             | Bin 126986 -> 59588 bytes
 setup.py                                |   4 +-
 tests/test_companion_motion.py          | 202 +++++++---
 tests/test_manual_update_transaction.py |  20 +-
 tests/test_settings_and_install.py      |   4 +-
 tests/test_upload_artifact_gate.py      |   2 +-
 tests/test_v023_release_contract.py     |  99 ++++-
 15 files changed, 817 insertions(+), 479 deletions(-)
$ shasum -a 256 (12:56Z and 13:05Z — identical)
7b02316545644abc14f8d8cdbfca48ac82ce13556c8d2d4e94c736713421449b  claude_pet.py
fa7775db3795a58efbfc557b7e941beb28318d0df505bce42c68b6858cca2549  build_app.sh
007421e64d90db93cae6ac1d3e7d6a42f9348b970b63c9caff7a881abe0c22a4  setup.py
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69  verify_release_artifact.py
7127f72dbb6da01c8b996a238c61a85be40e72e96525672ca368722b7f6509a3  RELEASE_NOTES.md
14918d5899bf686a0de34c66a85416ccacb083ef86683f27e23d2ae77ae205f4  CLAUDE.md
57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b  <scratchpad>/claude_pet.pre-unify.py  (= git show HEAD:claude_pet.py)
c89bc43027dc7cde5726e96223376f8eec09302b2fc1f8147fd5b57cfc376118  fonts/Pretendard-SemiBold.otf (1583704 bytes, header OTTO)
b04538c9abec39a3db75108cf0af0fd9c77032fe8aa2cf38345b4d250e98e38e  fonts/LICENSE-Pretendard.txt (SIL OFL 1.1, Reserved Font Name Pretendard)
```

The production hashes match the Verifier's record (§1 there) at every point, so the
tree the Verifier ran and the tree I read are the same bytes. Read first-hand: the full
`git diff` of `claude_pet.py`, `CLAUDE.md`, `RELEASE_NOTES.md`, `setup.py`,
`build_app.sh`, `tests/`; the new `tests/test_summary_pill.py` and
`tests/test_nested_pets.py` in full; the Verifier's record in full; `AGENTS.md` in full;
and, by `sed`/`grep` on the current `claude_pet.py`: `bundled_font_path`, `_read_pet_json`,
`_is_pet_dir`, `_write_pets_readme`, `_PET_JUNK_DIRS`, `_nested_pet_dir`, `discover_pets`,
`_oauth_label`, `_rows_from_limits`, `_parse_oauth_usage`, `_fetch_cli_usage` tail,
`fetch_exact_usage`, `_label_order`, `fmt_countdown`, `fmt_reset`, `pill_h`, `RoamDisplay`
(all of it), `roam_summary`, `SUMMARY_*`, `summary_value_kind`, `_summary_segment_runs`,
`roam_summary_runs`, `roam_fit_runs`, `roam_pill_rect`, `roam_frame`, and inside
`run_gui`: `register_bundled_font`, `summary_font`, `F_SUMMARY*`, `geom`, `state` init,
`load_pet_frames`, the pet selection at startup, `spike_info`, `PetView.pillRect/pillTop/
pillLeft/petOrigin`, the chevron `mouseUp_` branch, `roam_env`, `roam_mode_now`,
`roam_summary_text`, `_draw_runs`, `draw_summary_pill`, `roam_apply_display`, the tick's
`disp.note(...)` call, `set_pet`, `open_user_pets_dir`. The README diffs and `preview.png`
were outside the assigned set; I read `README.ko.md`'s new pill section only to check it
against the source (it matches — §6.8).

## 2. Item 1 — correctness of the new pill (source, current tree)

Grouping key for the greps: one match line in `claude_pet.py`.

- **Removed names.** `grep -nE` over `draw_sub_pill|draw_exact_pill|draw_api_pill|
  draw_status_line|draw_onboard_pill|draw_sub_right|bar_color|ROW_H|STATUS_H|PILL_R|TRACK|
  CUR_PILL|apply_pill_rows|cur_rows_n|\.expanded|F_BOLD|F_SUB|C_TRACK|F_BIG|F_ALERT|F_TINY|
  F_STATUS|F_CHEV` → **0 matches**. Every pill draw now goes through one call site:
  `drawRect_` → `if roam_mode_now() in (DISPLAY_FULL, DISPLAY_SUMMARY): draw_summary_pill()`.
  A crude unbound-name scan (AST: every loaded `Name` minus every bound name and builtins)
  over the whole module reports only `__file__` (a module attribute, false positive) — so
  no removed name survives in a branch the suite never executes (e.g. `--report`).
- **Fallback geometry = display-layer geometry.** `PetView.pillRect()` returns
  `state["roam_rects"]["pill"]` when the display layer has run, else
  `roam_pill_rect(roam_mode_now(), petOnRight(), petOnBottom(), W, PW, PH, pill_h(), text_w, text_h)`
  with `text_w, text_h` from `roam_summary_text()`; `roam_apply_display()` calls
  `roam_frame(..., w_, h_, PW, PH, pill_h(), g["scale"], text_w, text_h)` where
  `(w_, h_) = roam_env()` = `state["roam_env"]` or the window frame, which before the
  display layer runs equals `(W, H)` from `geom()`. Same rule, same inputs.
  `roam_apply_display` passes `text_w, text_h` for every mode except folded
  (`mode != DISPLAY_FOLDED`), i.e. for `full` and `summary` alike.
- **`pill_h()` vs `text_h`.** `geom()` reserves `h = ph + GAP + pill_h() + 4` with
  `pill_h() = SUMMARY_H2 = 46`; `roam_pill_rect` clamps `h = min(pill_h, text_h)` and
  bottom-aligns inside the strip (`pill_h + 4 - h`); `petOrigin()`'s fallback uses
  `pill_h() + GAP`. Consistent: the logical strip is the two-line height, the drawn pill
  is `text_h`.
- **`⚠`.** Appended by `roam_summary_text()` only when `segment[0] == "estimate" and
  OAUTH_STATUS.get("auth_error")` — never on exact or cost rows.
- **Reset texts.** `roam_summary()` never touches a datetime: exact rows carry
  `row[2]` verbatim if it is a non-empty `str`, estimate rows take `reset_texts[gauge]`.
  The adapter builds them with **`fmt_countdown`** (`fmt_countdown(rdt, now_utc)` for
  exact rows with a datetime, `rtxt or None` otherwise; `fmt_countdown(reset, stats["now"])`
  per estimate gauge). `fmt_reset` is **no longer called anywhere** (`grep -n 'fmt_reset\b'`
  → only its `def`). See §3/§7-B3 for the documents that still say `fmt_reset`.
- **AppKit-free surface.** No top-level `from AppKit|Foundation|CoreText import` exists
  (all are inside functions); `bundled_font_path()` imports `Foundation` inside `try/except`
  and returns the sibling `fonts/` path first; `discover_pets`, `_nested_pet_dir`,
  `_read_pet_json`, `_write_pets_readme` use only `os`/`json`/`glob`. `import claude_pet`
  from a plain `python3` works (the suite does it).
- **Font registration.** `register_bundled_font()`: no file → `None`; CoreText import or
  registration raising → swallowed; the decision is `NSFont.fontWithName_size_(
  "Pretendard-SemiBold", 11) is not None`, and `summary_font()` falls back to
  `mono(size, True)` (bold system monospaced). The bundle path relies on
  `ATSApplicationFontsPath = fonts` (present in both `setup.py`'s plist and
  `build_app.sh`'s `write_plist`); a duplicate process-scope registration in the bundle
  only makes CoreText return an error that is ignored. `_summary_font_ok` is assigned
  before the first `summary_font()` call.
- **Nested pets.** `_nested_pet_dir(d)` lists `d`, skips dot-folders and `__MACOSX`,
  keeps `os.path.isdir(p) and not os.path.islink(p) and _is_pet_dir(p)`, returns the
  single candidate, else the one whose basename equals `d`'s basename, else `None`. An
  inner path is always `os.path.join(d, sub)` with `sub` from `os.listdir`, so it cannot
  leave `pets/<name>/` except through a symlink, which is excluded. (The **outer**
  `pets/<name>` being a symlink is followed — unchanged pre-existing behaviour at the flat
  level, not introduced here.) `discover_pets` keeps `id = name` (outer) and
  `dir = inner`; `set_pet(pet_id)` matches `x["id"] == pet_id` and loads `p["dir"]`;
  `load_pet_frames(pet_dir)` → `_read_pet_json(pet_dir)` and `_load_sheet_pet(pet_dir,
  meta)` resolves `spritesheetPath` relative to `pet_dir` (l.~6251). Startup does the
  same via `cfg.get("pet")`. So `cfg["pet"] = "hello-kitty"` with
  `dir = pets/hello-kitty/hello-kitty` works.
- **Encoding.** `grep -nE '\bopen\(|fdopen\('` (excluding `os.open`) → 16 call sites;
  8 binary (`"rb"`/`"wb"`: l.463, 608, 648, 3943, 4036, 4094, 4330, 4495) and 8 text-mode,
  **all** with `encoding="utf-8"`: l.802 (`pet.json` read), 869 (pets README write),
  1424 (`load_config`), 1457 (`save_config` fdopen), 1895 (log read, `errors="ignore"`),
  2172 (debug log append), 2181 (credentials file), 2614 (terminal script). `save_config`
  writes `json.dump(cfg, f)` with the default `ensure_ascii=True`, so the file is pure
  ASCII and readable by `load_config` under utf-8 or cp949, and a config written by an
  older build (platform default, ASCII content) still loads.
- **Extension contract.** `roam_summary_runs(segments, tr)` appends segments on one line
  with a `"status"`-kind separator, and second-line pieces with a `"sub"` separator;
  `roam_fit_runs` trims from the end and strips a trailing `SUMMARY_SEP`.

**One defect found here — the arrival-latch toggle (§7-B1).** Probe, current tree,
2026-09-12T13:00Z:

```
$ python3 - <<'PY'
import claude_pet as cp
for pref in (False, True):
    d = cp.RoamDisplay(); d.note("look","approach",True)
    new = d.toggle(pref)
    print(pref, "->", new, d.mode("look", new), d.mode("rest", new))
PY
False -> True folded full
True -> False folded folded
```

`RoamDisplay.toggle()` is `self.summary = False; return not show_panel`, and the chevron
handler stores that as `state["show_panel"]`. Two facts combine:

1. For a user whose preference is *folded* (`show_panel=False`), the pill appears only
   because of the arrival latch; the chevron is drawn in the **fold** direction
   (`is_open = roam_mode_now() in (FULL, SUMMARY)`); clicking it sets the preference to
   **open**. After the visit ends (`note("rest", settled=True)` → `reset()`), the pill is
   open and stays open. The docstring says the opposite of what the code does: "보이는 필을
   접는 것이 사용자의 뜻이다".
2. `note()` runs **every tick** (`disp.note(out.phase, roamer.kind, ...)` in the roam
   tick) and re-latches whenever `phase == "look" and kind in ("approach", "follow")`.
   So the `self.summary = False` in `toggle()` is undone on the next tick (50 ms): during
   the visit the click has no lasting visible effect at all, only the stored preference
   flips. The Verifier's pinned expectation `mode("look", flipped) == "folded"` right
   after `toggle()` is a state the app holds for at most one tick.

v0.23 did not have this: its toggle during the latch flipped `expanded` (which `note()`
never touched) and left `show_panel` alone. The stale comment at the chevron handler
(`# 요약 중엔 요약 ↔ 전체만 오가고 평소 선택은 그대로(RoamDisplay.toggle).`) still
describes that. This is the case the user is most likely in — they liked the pill that
appears *after the pet moves*, which is the folded-preference experience.

## 3. Item 2 — CLAUDE.md claims vs source

Checked line by line against the current `claude_pet.py` (`grep -n` for each symbol):

| Claim in the rewritten section | Source | Result |
| --- | --- | --- |
| drawn by `draw_summary_pill()` from `roam_summary()` / `roam_summary_runs()` | present, wired as stated | OK |
| first line `세션 42% · 주간 17% · Fable 12%` | `roam_summary_runs` (ko probe below) | OK |
| second line example **`세션 리셋 3시간 43분 후 · 주간 리셋 2일 4시간 후`** | probe: `리셋 세션 3시간 43분 후 · 주간 2일 4시간 후` — `tr("reset_prefix")` once at the start, then `<label> <text>` | **wrong** |
| no bars, no status line; `full`/`summary` same pill; `folded` pet-only | `RoamDisplay.mode`, `roam_pill_rect` | OK |
| `SUMMARY_H` one line, `SUMMARY_H2` two; `pill_h()` = two-line strip | `30`, `46`, `pill_h()` returns `SUMMARY_H2` | OK |
| table: exact = first three gauge rows, credits dropped via `_label_order` | adapter `if _label_order(label) > 2: continue`; `roam_summary` `[:3]` | OK, but see §6.1 (it drops more than credits) |
| estimate rows prefixed `SUMMARY_APPROX` (`≈`) | `approx = SUMMARY_APPROX if kind == "estimate"` | OK |
| cost: today, then this month when known | `("cost", (today, month|None))` | OK |
| `SUMMARY_COLORS["exact"]` emerald, `["estimate"]` amber, cost coral | `#50C878`, `#FFB300`, `#FF7F50` | OK |
| value white → `"warn"` at 50 → `"bad"` at 85, `summary_value_kind()` | `pct >= 85` → bad, `pct >= 50` → warn | OK |
| spiking label **prefixed with `spike_prefix`** | code prefixes `SUMMARY_SPIKE` (`"▲"`); the TR key `spike_prefix` (`"▲spike "`) is now referenced nowhere (`grep -c 't("spike_prefix"'` → 0) | **wrong** |
| second line kind `"sub"` | `SUMMARY_COLORS["sub"] = TXT_SUB` | OK |
| `⚠` trailing run appended by the adapter on estimate after `OAUTH_STATUS["auth_error"]` | `roam_summary_text` | OK |
| adapter pre-formats reset times with **`fmt_reset()`** | adapter calls `fmt_countdown()`; `fmt_reset` has no caller | **wrong** |
| passes `reset_texts`, `row[2]`, `spike_first` | as stated | OK |
| `roam_summary_runs(segments, t)` → `(main, sub)` of `(text, kind)`; `roam_fit_runs` trims from the end | as stated | OK |
| font: bundled Pretendard SemiBold, plist registers in bundle, CoreText from source, fallback system monospaced | as stated (fallback is the *bold* system mono) | OK |
| "The Windows port loads the same file through Qt" / fonts row "bundled so macOS and Windows draw the same glyphs" | no Windows port exists in this tree; `SUMMARY_FONT_FAMILY` is defined and unused (`grep -rn QFont` → only the comment) | **unverifiable in-tree** |
| paths where the estimate reaches exact mode: mood/overlay/greeting; session-reset greeting; API-mode guard | `current_mood`, `spike_info` (`None` in api mode), refresh worker | OK |
| fonts row: `setup.py` resource + `ATSApplicationFontsPath`; `build_app.sh` copies in `build()` and `update()` | `resources` list + plist key; `build()`→`build_body`→`copy_fonts "$APP"`; `update)`→`__update_txn`→`update_installed`→`copy_fonts "$stage"` before `write_plist`/`sign_app`/`stop_pet` | OK |
| "What this is": "a **one-line** usage summary pill" | the pill is one *or two* lines (the section itself says so) | inconsistent |

Probe for the ko strings (2026-09-12T13:04Z, `L["lang"] = "ko"`, real `t`):

```
ko exact line1: 세션 42% · 주간 17% · Fable 12%
ko exact line2: 리셋 세션 3시간 43분 후 · 주간 2일 4시간 후
ko estimate no-reset line1: 세션 ≈42% · 주간 ≈17% · ▲Fable ≈12%
ko estimate no-reset line2: '리셋 세션 -'
```

Stale sentences elsewhere in CLAUDE.md (`grep -nE 'bars?\b|draw_exact_pill|status line|
PILL_ROWS|CUR_PILL|...'` over the whole file): none of the removed symbols is named
anywhere else. Two places deserve a touch: the Weekly-window paragraph (l.~630–637) says
"both the weekly gauge and the per-model gauge render `-`" and "`fmt_reset()` maps a falsy
reset to `-`" — true of `fmt_reset`, but the pill's path is now `fmt_countdown` (also `-`)
and the `-` appears on the **reset line** (`주간 -`), not beside the percentage; and the
new section no longer states the spike asymmetry the old one did (a weekly or opus
estimator spike sets `spike_first`, which marks the exact **session** label `▲`, because
`spike_first=bool(spike_info(stats))` and `spike_info` is truthy for any of the three).
CLAUDE.md documents bundled-pet seeding but not user-pet discovery; the nested-folder
rule lives only in the `discover_pets`/`_nested_pet_dir` docstrings and `_PETS_README`
(§6.4 recommends a paragraph).

## 4. Item 3 — RELEASE_NOTES.md v0.24 (staged) and the published sections

```
$ python3 (bytes from the **v0.23** heading to EOF)
wt       18516  c7ddc40a8a25ce8e…
HEAD     18516  c7ddc40a8a25ce8e…
81619b3  18516  c7ddc40a8a25ce8e…
prefix before the staged heading identical to HEAD's prefix before **v0.23**: True
```

So the only change to `RELEASE_NOTES.md` is the six inserted lines of the v0.24 section;
every published byte (v0.23 and older) is identical to HEAD and to the v0.23 release
commit. The section (grouping key: a line starting `- `; sentences split on `.`):

```
top-level bullets: 3   nested: 0
normalized length: 394 (bullets only) / 404 (with the heading)   ≤ 450
bullet 1: 3 sentences   bullet 2: 3 sentences   bullet 3: 2 sentences
```

Claims audited against the tree: "요약 필 하나로 통일" (one draw path, §2); "첫 줄에
세션·주간·모델 … 둘째 줄에 리셋 시각" (`main`/`sub` runs); "API 모드에서는 오늘·이달 비용"
(`("cost", (today, month))`); "게이지 막대와 하단 상태줄은 사라졌습니다" (draw_* removed);
"정확 모드 에메랄드, 로그 추정 앰버·값 앞 ≈, API 비용 코랄" (`SUMMARY_COLORS`,
`SUMMARY_APPROX`); "50%부터 노란색, 85%부터 빨간색" (`summary_value_kind`); "급증하면 ▲와
함께 빨간색" (`SUMMARY_SPIKE`, kind `"bad"`); "토큰이 만료돼 추정으로 내려가면 줄 끝에 ⚠"
(`auth_error` run); "Pretendard(OFL)를 앱에 내장" (`fonts/`, OFL 1.1 licence, `setup.py`,
`build_app.sh`); "한 단계 더 깊어진 펫 폴더(pets/이름/이름/)도 인식" (`_nested_pet_dir`) —
**the nested-folder fix is already in bullet 3**, contrary to the assignment's premise.
No hash, source path, line number, test name, or magnitude/frequency word. The Windows
0-byte-README/encoding fix is not mentioned; it is invisible on the macOS artifact this
file ships with, so omitting it is fine. Not mentioned and user-visible: API mode no longer
shows the monthly-budget row/bar that `draw_api_pill` drew from `RUNTIME["api_budget"]`
(README.ko now says "월 예산 칸은 아직 필에 표시되지 않음"); the note's bullet 1 says only
that bars and the status line are gone.

The repo's own gate on this text is red — my run and the Verifier's agree (§5):
`bullet 1 has 3 sentences; CLAUDE.md allows 1-2`, `bullet 2 has 3 sentences; …`,
`remove internal identifier: 'Pretendard('`. Under CLAUDE.md step 2 the section is
staged and unpublished (`APP_VERSION` is still the literal `"0.23"`, the newest tag is
`v0.23`), so correcting it is ordinary work — but it must be corrected before the release
commit, because §8 item 5 requires a green suite.

## 5. Item 4 — do the Verifier's fixtures discriminate?

Independent full-suite run (same command as the Verifier, repo root):

```
start 2026-09-12T12:57:26Z   end 2026-09-12T13:03:01Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/rev/reviewer_suite.log 2>&1
Ran 551 tests in 334.861s
FAILED (failures=1, skipped=7)
rc=1
FAIL: test_v024_notes_follow_the_three_bullet_450_character_format (test_v023_release_contract.StagedV024NotesFormatTests…)
```

Same numerator/denominator as the Verifier's §5 (1 of 551 failing, 7 opt-in skips).

Revert-and-observe was already done by the Verifier against the pre-change file; I
instead built **ten mutants of the current file** — each a plausible wrong *new*
implementation that the pre-change file cannot stand in for — in scratch trees
`<scratchpad>/rev/mut/<name>/` (mutated `claude_pet.py` + copies of `setup.py`,
`build_app.sh`, `fonts/`, and the one test module; cwd = the scratch tree; the working
tree was never modified — `claude_pet.py` hashed `7b023165…` before and after). Driver:
`<scratchpad>/rev/mut/drive.py`; each mutation is a single `str.replace` asserted to match
exactly once. Grouping key: one unittest result header. Runs at 2026-09-12T13:02:21–23Z:

| mutant (what a wrong implementation would do) | module | result | failing test(s) — and only these |
| --- | --- | --- | --- |
| M1 `_nested_pet_dir` returns the first sorted candidate | nested (14) | FAILED failures=3 | `test_among_several_the_inner_folder_named_like_the_parent_wins`, `test_two_inner_pets_named_unlike_the_parent_are_refused`, `test_ordering_is_by_outer_name` |
| M2 drop `not os.path.islink(p)` | nested | FAILED failures=1 | `test_a_symlinked_inner_folder_is_not_followed` |
| M3 drop `sub in _PET_JUNK_DIRS` | nested | FAILED failures=1 | `test_a_single_inner_pet_wins_even_when_junk_looks_like_a_pet` |
| M4 README: `exists` only (no size check) | nested | FAILED failures=1 | `test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept` |
| M5 `_read_pet_json` without `encoding=` | nested | FAILED failures=1 (default locale); failures=1, errors=1 under `PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C LANG=C` | `test_every_text_mode_open_names_utf8`; + `test_pet_json_with_korean_and_emoji_display_name_reads_back` under the C locale |
| M6 `summary_value_kind`: `pct > 85` | summary (26) | FAILED failures=1 | `test_thresholds_are_50_and_85_inclusive_and_spike_wins` |
| M7 `roam_fit_runs` keeps a trailing separator | summary | FAILED failures=1 | `test_never_leaves_a_trailing_separator` |
| M8 `roam_pill_rect`: `h = text_h` (unclamped) | summary | FAILED failures=2 (subTests) | `test_full_and_summary_return_the_same_text_sized_rect` |
| M9 exact spike on the first *kept* row | summary | FAILED failures=1 | `test_exact_spike_first_marks_only_the_first_given_row` |
| M10 no consecutive-duplicate collapse on the reset line | summary | FAILED failures=1 | `test_second_line_has_the_prefix_once_and_collapses_consecutive_duplicates` |

Every mutant is caught, each by exactly the test whose docstring names that rival, and by
no other — the fixtures discriminate in both directions (they do not fail for unrelated
reasons). Logs: `<scratchpad>/rev/mut/<name>/run.<env>.log`.

Corpus safety: neither new module references `expanduser`, `HOME`, `~/` or a real
`~/.claude*` path (`grep`); `PetTreeCase` repoints `claude_pet.USER_PETS_DIR` and
`PET_DIR` into a `tempfile.TemporaryDirectory()` and restores them by `addCleanup`;
`BundledFontTests` patches `claude_pet.__file__` into a temp dir for the negative case;
`test_manual_update_transaction`'s new `fonts` helper writes only under `checked()` inside
its temp root. No test in the diff reads `~/.claude` or writes `~/.claude_pet*`.

Verifier's own re-pins: the three SHA256 re-pins (`57b24a28… → 7b023165…` twice,
`83eca429… → fa7775db…`) match the bytes I hashed; `release.sh`/`verify_release_artifact.py`
pins untouched and still true. The `test_v023_release_contract.py` premise fix is right
(`git tag --sort=-v:refname | head -1` → `v0.23`; the Verifier quoted `gh release list`).
The `copy_fonts` shim in the manual-update harness stubs the two files the real function
insists on — correct shape. The edited compact gate of the opt-in native smoke is, as the
Verifier says, *unverified red*; nothing in the suite depends on it.

**What the tests do not catch (and pin instead): B1.** `test_summary_pill.RoamDisplayToggleTests.
test_toggle_during_the_latch_clears_it_and_flips_the_preference` and, in
`test_companion_motion.py`, `test_approach_summary_toggle_clears_the_latch_and_flips_the_preference`,
`test_hover_stop_away_keeps_summary_until_the_user_toggles`,
`test_no_drag_click_does_not_turn_in_place_summary_stop_into_completion` assert
`toggle(pref) == not pref` and `mode("rest", not pref) == "full" if not pref …` — i.e.
they pin the inversion described in §2. Their rival lists ("clearing without flipping;
flipping without clearing") never include "fold the visible pill", so the fixture could
not see it. After the fix they need re-pinning by the Verifier (AGENTS.md §2 Condition A
forbids the Developer doing it).

## 6. Non-blocking recommendations (for the Developer / Coordinator to decide)

1. **Adapter drops more than credits.** `roam_summary_text()` skips exact rows with
   `_label_order(label) > 2`. `_label_order` returns `2` only when `label.lower()` is
   exactly one of `fable|mythos|opus|sonnet|haiku`, and `5` otherwise;
   `_rows_from_limits` passes the server's `scope.model.display_name`/`id` **verbatim**
   ("서버 표기를 가공하지 않는다"). Probe: `_label_order("Claude Fable 5") == 5`,
   `_label_order("claude-fable-5-1") == 5`. The old `draw_exact_pill` drew such a row; the
   new pill hides it, so the model gauge the user asked for would be missing in exact mode
   whenever the server's display name is not a bare family word. I could not determine
   the real server string in-tree (no fixture or record quotes it). Suggest dropping only
   order 9 (credits), or keeping the first three rows `fetch_exact_usage` already sorted.
2. **`-` on the reset line.** `fmt_countdown(None, …)` returns `"-"` and the adapter passes
   it through, so an estimate with no current session block or rolling weekly shows
   `리셋 세션 -` / `주간 -` (probe above). README.ko documents "롤링 7일이면 주간은 `-`", so
   it is deliberate; passing `None` for a missing reset would list only real reset times
   and drop the line when there are none.
3. **The font is not release-gated.** `verify_release_artifact.py app` checks pets, code
   identity, version, arch, signature — not `Contents/Resources/fonts/Pretendard-SemiBold.otf`.
   The fallback to the system mono is silent, so a py2app `resources` regression would
   ship unnoticed. Adding the font (and licence) to the artifact gate means re-pinning its
   SHA256 in `tests/test_upload_artifact_gate.py`.
4. **CLAUDE.md additions** (recommend, not edited): a "User pets" paragraph — id = outer
   folder, dir = inner, one level only, `_PET_JUNK_DIRS`, inner symlinks not followed,
   outer symlink followed (pre-existing), whole-folder skip unchanged; restate the spike
   asymmetry (§3); in the Weekly-window paragraph name `fmt_countdown` and say the `-`
   now appears on the reset line; change "one-line" in *What this is* to "compact
   (one- or two-line)"; reword the two Windows-port sentences as intent
   (`SUMMARY_FONT_FAMILY` is reserved for a Qt port that is not in this tree).
5. **Dead code left by the change** (safe to remove or keep, but say which): `fmt_reset()`
   (and `WEEKDAYS`, `reset_at`, `am`/`pm` exist for it), `gauge_rows()`,
   `PetView.pillTop()/pillLeft()` (no callers), TR keys `spike_prefix`, `left`,
   `exact_mode`, `log_estimate`, `budget`, `need_budget` (0 `t("…")` uses each, all four
   locales), `SUMMARY_FONT_FAMILY`. Stale comments: the chevron handler (§2) and
   `roam_summary`'s docstring ("호출자가 fmt_reset 으로 만든 문자열").
6. **Budget row gone in API mode** — `RUNTIME["api_budget"]` is still a setting; either
   mention the loss in the note (bullet 1 has room once it is shortened) or plan its
   return.
7. **Per-tick measurement.** `roam_apply_display` now calls `roam_summary_text()` (about
   ten `NSAttributedString.size()` calls plus `datetime.now`) on every 20 Hz tick when not
   folded, where v0.23 did so only in summary mode. Probably negligible; noting it.
8. **Outside the reviewed set.** `README.md`/`.ko`/`.ja`/`.es` and `preview.png` changed
   during verification (Verifier §5). I checked only `README.ko.md`'s new pill section:
   its example lines, colours, thresholds, `⚠`, `-` and the nested-folder sentence match
   the source. The other three READMEs and the image were not reviewed.
9. **Separation is claimed, not yet checkable.** Nothing is committed, so §2 Conditions
   A/B cannot be read off `git log`. The Verifier's record states the tests were untouched
   at 12:26Z before it started and that it edited only `tests/` and its record; the
   Developer's set is the production/docs diff. Consistent with what I see, but the
   trailers will be the first checkable evidence.

## 7. Blocking findings — must fix before the release commit

- **B1 (code)** `RoamDisplay.toggle()` during the arrival latch flips `show_panel` instead
  of folding, and `note()` re-latches on the next tick during `look`, so the chevron
  cannot dismiss the visiting pill and a folded-preference user ends every visit with the
  pill permanently open (§2, probe quoted). Requirement: a toggle on a visible latched pill
  folds it for the rest of that visit and does not turn a folded preference into an open
  one. The four tests listed in §5 pin the wrong behaviour and need re-pinning by the
  Verifier after the fix; the chevron-handler comment is stale.
- **B2 (release note)** The staged v0.24 section fails the repo's own format gate: bullets
  1 and 2 have three sentences (limit 1–2) and `Pretendard(OFL)` trips the identifier
  heuristic (write `Pretendard (OFL)`). Published bytes are untouched (§4). The suite is
  not green until this is fixed (§8 item 5).
- **B3 (CLAUDE.md)** Three wrong claims in the rewritten pill section: the spike label is
  prefixed with `SUMMARY_SPIKE` (`▲`), not `spike_prefix`; the adapter uses
  `fmt_countdown()`, not `fmt_reset()`; the second-line example must read
  `리셋 세션 3시간 43분 후 · 주간 2일 4시간 후` (prefix once, at the start). A documentation
  commit's `Verifier:` must be able to find the claims accurate (AGENTS.md §7), which
  these are not.

## 8. Untracked work and process

```
diag.py                          2026-07-22T12:07:01  (before and after)
release/icon_1024.png            2026-07-13T23:46:36  (before and after)
release/ClaudePet.iconset/*      2026-07-13T23:46:36  (14 files, before and after)
```

mtimes taken at 12:55:52Z and 13:05:18Z: unchanged. Every untracked path present is
listed in §1's `git status`; the only one this role created is this file. No git write
command was run (only `status`, `diff`, `rev-parse`, `log`, `show`); nothing was
committed, tagged, pushed, signed, built or installed; `./release.sh` and `./build_app.sh`
were not invoked; no GUI was launched; the dev instance (PID 6902, `python3 claude_pet.py`,
elapsed 39:05 at 13:05Z) was not touched; no test or probe read `~/.claude` or wrote
`~/.claude_pet*`. Scratch files are under `<scratchpad>/rev/` only.

## 9. Provenance summary (AGENTS.md §5)

- Grouping key: one unittest result header (suite, mutants); one grep match line
  (symbol scans); one bullet line / one `.`-terminated sentence (release note).
- Window: 2026-09-12T12:55:52Z – 13:05:18Z, UTC.
- File set read: listed in §1; the pre-change copy `<scratchpad>/claude_pet.pre-unify.py`
  was used only for its hash (revert-and-observe was the Verifier's; I ran forward mutants).
- Numerators/denominators: suite 1 failing / 551; mutants 10 caught / 10 built, each by
  the single intended test; text-mode opens 8 with `encoding="utf-8"` / 8; removed-symbol
  grep 0 / 23 patterns; release note 394 chars / 450, 3 bullets / 3, 3+3+2 sentences.
- Measured at: the timestamps quoted beside each command.

---

# Continuation — round 3 review (same Reviewer role, record resumed 2026-09-12T13:50Z)

Rounds 1's verdict above was FAIL (B1/B2/B3). The Developer landed round 2 (B1 →
`RoamDisplay.dismissed`, the cost budget, the credits-only adapter filter and memo, dead
code removed, startup README seeding, the font gate in `verify_release_artifact.py`, the
docs) and round 3 (the user's "세션이나 주간 이 텍스트랑 수치랑 색을 반대로 하자!" — colour
roles swapped — and the font changed from the CFF `.otf` to the TrueType `.ttf`); the
Verifier's record carries its rounds 2–3 continuation (§C1–C8). This continuation reviews
the tree as it stands after round 3. Same role, same constraints: read-only except this
file; nothing committed, tagged, pushed, signed, built, installed or launched.

Window: 2026-09-12T13:51:55Z (first recorded timestamp; the opening `git status` ran
about a minute earlier) – 13:58:15Z (post-suite hash check), UTC. cwd
`/Users/yeongyu/claude-pet` unless a scratch cwd is stated; scratch under
`<scratchpad>/rev3/`. Output excerpts verbatim. Line numbers approximate by CLAUDE.md's
own rule — locate by symbol.

**Verdict: FAIL — no product defect; three documentation defects block the commit
(§R7): the stale `preview.png`, a false README sentence in all four locales, and a wrong
path count in CLAUDE.md's pill section. Everything else reviewed is sound; the
Verifier's fixtures discriminate (§R5).**

## R1. What was reviewed

```
$ git status --porcelain   (tracked part; identical at 13:50Z and 13:58Z)
 M CLAUDE.md  M README.es.md  M README.ja.md  M README.ko.md  M README.md  M RELEASE_NOTES.md
 M build_app.sh  M claude_pet.py  M preview.png  M setup.py  M verify_release_artifact.py
 M tests/test_companion_motion.py  M tests/test_manual_update_transaction.py
 M tests/test_release_artifact_preflight.py  M tests/test_settings_and_install.py
 M tests/test_upload_artifact_gate.py  M tests/test_v023_release_contract.py
$ shasum -a 256   (13:51:55Z, and identical at 13:58:15Z — <scratchpad>/rev3_hashes_{before,after}.txt)
c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00  claude_pet.py
db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b  build_app.sh
007421e64d90db93cae6ac1d3e7d6a42f9348b970b63c9caff7a881abe0c22a4  setup.py
a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23  release.sh
5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324  verify_release_artifact.py
dded11568245aacfabf44245d40b4ab01ddf0aae18a8f8b7a12e68c4bc73b54c  CLAUDE.md
00f0fd33ff4d3556012729c9e9055976ef7bb09916ae189b9b01c3e647828503  RELEASE_NOTES.md
48bfe83fd8b1b4c45367c93fddec106e8dd8f5ed1a3cf20a37a0bc30b80b0e84  README.md
c7744844bdc60afde1b5016d22c29bf3d621d082352fdbe31818cab23e73dfbd  README.ko.md
278852771367095d445b69bd9a602f73104f789d282811fc6da5715086e2f47a  README.ja.md
a7c40c1d940a04d270a078d29797983b824d935fd5398d2b6be2c65e25a6623f  README.es.md
fbc7ff9a0feac5c9cdb8803ff5634ee294a296753be635eb9081aafb937faffe  preview.png
5e1c548732af70873103066c16e1369b9a8a871f0b38c321a1d5bc73e43cea2d  fonts/Pretendard-SemiBold.ttf
b04538c9abec39a3db75108cf0af0fd9c77032fe8aa2cf38345b4d250e98e38e  fonts/LICENSE-Pretendard.txt
```

The five production hashes equal the Verifier's §C1 and the pins in
`tests/test_upload_artifact_gate.py` / `tests/test_manual_update_transaction.py`, so the
Verifier's runs, the pinned bytes and the tree I read are the same bytes. Read first-hand:
`AGENTS.md` in full; the round-1 record above; the Verifier's record in full (§1–§7 and
§C1–§C8); the full `git diff` of `claude_pet.py` (1145 lines, `<scratchpad>/rev_diff_claude_pet.patch`),
`setup.py`, `build_app.sh`, `verify_release_artifact.py`, `RELEASE_NOTES.md`, `CLAUDE.md`,
the four READMEs and every test module in the diff; `tests/test_summary_pill.py` and
`tests/test_nested_pets.py` in full; `preview.png` (rendered, and decoded pixel by pixel via
`sips → bmp`, §R3); and by `grep -n`/`sed` on the current `claude_pet.py`: `bundled_font_path`,
`_pet_json_path`/`_read_pet_json`/`_is_pet_dir`, `_write_pets_readme`, `_PET_JUNK_DIRS`,
`_nested_pet_dir`, `discover_pets`, `_oauth_label`, `_label_order`, `fetch_exact_usage` tail,
`fmt_countdown`, `pill_h`, `RoamDisplay` (all of it), `roam_summary`, `SUMMARY_*`,
`summary_value_kind`, `_summary_segment_runs`, `roam_summary_runs`, `roam_fit_runs`,
`roam_pill_rect`, `roam_frame`; inside `run_gui`: `geom`, `register_bundled_font`,
`summary_font`, `F_SUMMARY*`, `spike_info`, `PetView.pillRect/petOrigin`, the menu builder,
`load_pet_frames` and the startup pet selection, `set_pet`, `open_user_pets_dir`,
`roam_env`, `roam_summary_text`, `_draw_runs`, `draw_summary_pill`, `roam_apply_display`,
the refresh worker's state writes, and the startup README seeding.

## R2. Item 1 — correctness of the new pill (source, current tree)

Grouping key for greps: one match line in `claude_pet.py`.

- **Removed names.** `grep -nE` over `draw_sub_pill|draw_exact_pill|draw_api_pill|draw_status_line|
  draw_onboard_pill|draw_sub_right|bar_color|ROW_H|STATUS_H|PILL_R|TRACK|CUR_PILL|apply_pill_rows|
  cur_rows_n|\.expanded|F_BOLD|F_SUB|C_TRACK|F_BIG|F_ALERT|F_TINY|F_STATUS|F_CHEV|fmt_reset|gauge_rows|
  pillTop|pillLeft|SUMMARY_FONT_FAMILY|WEEKDAYS|spike_prefix|"left"|exact_mode"|log_estimate|"budget"|
  need_budget|reset_at|"am"|"pm"|OTTO|\.otf` → 4 lines, none a survivor: l.1121 (`"r_left"`, the
  `--report` table), l.2057 (`"left"` key of a gauge dict), l.2440 (`obj.get("reset_at")`, a server
  JSON key), l.2637 (a regex group compared to `"pm"`). Every pill draw is one call site:
  `drawRect_` → `if roam_mode_now() in (DISPLAY_FULL, DISPLAY_SUMMARY): draw_summary_pill()`.
  `PILL_ROWS` survives only as the fetch cap in `_parse_oauth_usage`/`fetch_exact_usage`.
- **Fallback geometry = display-layer geometry.** `PetView.pillRect()` returns
  `state["roam_rects"]["pill"]` when the display layer has run, else
  `roam_pill_rect(roam_mode_now(), petOnRight(), petOnBottom(), W, PW, PH, pill_h(), text_w, text_h)`
  with `(text_w, text_h)` from `roam_summary_text()[2:]`; `roam_apply_display()` computes
  `text_w, text_h = roam_summary_text()[2:] if mode != DISPLAY_FOLDED else (0.0, SUMMARY_H)` —
  so **full and summary alike** — and calls `roam_frame(..., w_, h_, PW, PH, pill_h(), scale,
  text_w, text_h)` with `(w_, h_) = roam_env()` = `state["roam_env"]` or the window frame, which
  before the display layer runs equals `(W, H)` from `geom()`. Same rule, same inputs.
  `draw_summary_pill()` draws into `view.pillRect()` (its only caller, l.~6853).
- **`pill_h()` vs `text_h`.** `pill_h()` returns `SUMMARY_H2` (46); `geom()` reserves
  `h = ph + GAP + pill_h() + 4`; `roam_pill_rect` clamps `h = min(pill_h, text_h)` and
  bottom-aligns in the strip (`pill_h + 4 - h`); `petOrigin()`'s fallback uses `pill_h() + GAP`.
  Consistent: the logical strip is two lines, the drawn pill is the text height.
- **`⚠`.** Appended by `roam_summary_text()` only under
  `segment[0] == "estimate" and OAUTH_STATUS.get("auth_error")` — never on exact or cost.
- **Reset texts.** The adapter builds them: `fmt_countdown(rdt, now_utc)` for an exact row with a
  datetime, `rtxt or None` otherwise; `{g: fmt_countdown(stats[g]["reset"], stats["now"])}` per
  estimate gauge. `roam_summary()` only copies `row[2]` (if a non-empty `str`) or
  `reset_texts[gauge]`; it never touches a datetime. `fmt_reset` has no definition left
  (`grep -c 'fmt_reset'` → 0).
- **AppKit-free surface.** No top-level `from AppKit|Foundation|CoreText import` (all inside
  functions); `bundled_font_path()` imports `Foundation` inside `try/except` after checking the
  sibling `fonts/`; `discover_pets`, `_nested_pet_dir`, `_read_pet_json`, `_write_pets_readme` use
  `os`/`json`/`glob` only. Every probe below did `import claude_pet` from a plain `python3`.
- **Font registration.** `register_bundled_font()`: no file → `None`; a CoreText import or
  registration error is swallowed; the decision is `NSFont.fontWithName_size_("Pretendard-SemiBold",
  11) is not None`; `_summary_font_ok = {"ok": …}` is bound before the first `summary_font()`
  call and `summary_font()` falls back to `mono(size, True)`. In the bundle `bundled_font_path()`
  finds `Contents/Resources/fonts/…` through its first branch (`__file__` sits in `Resources`),
  and the plist's `ATSApplicationFontsPath = fonts` (in both `setup.py` and `write_plist`) has
  already registered it; the duplicate process-scope registration only returns an ignored error.
- **Nested pets.** `_nested_pet_dir(d)`: `sorted(os.listdir(d))`, skip `.`-prefixed and
  `_PET_JUNK_DIRS`, keep `os.path.isdir(p) and not os.path.islink(p) and _is_pet_dir(p)`; one
  candidate wins, else the one whose basename equals `d`'s, else `None`. An inner path is always
  `os.path.join(d, sub)` with `sub` from `os.listdir`, so it cannot leave `pets/<name>/` except by
  a symlink, which is excluded; the **outer** `pets/<name>` symlink is followed — pre-existing at
  the flat level, unchanged here. `discover_pets` keeps `id = name`, `dir = inner`; `set_pet(pet_id)`
  matches `x["id"] == pet_id` and loads `p["dir"]`; startup does
  `sel = next(p for p in pet_list if p["id"] == cfg.get("pet"))` → `load_pet_frames(sel["dir"])`
  → `_read_pet_json(pet_dir)` / `_load_sheet_pet(pet_dir, meta)`, which resolves `spritesheetPath`
  against `pet_dir` (l.~6206–6209). So `cfg["pet"] = "hello-kitty"` with `dir =
  pets/hello-kitty/hello-kitty` loads. `__MACOSX` is also skipped at the top level.
- **Encoding.** `grep -nE '(^|[^.a-z_])open\(|fdopen\('` → 16 call sites (`os.open` excluded):
  8 binary (`"rb"`/`"wb"`: l.462, 607, 647, 3912, 4005, 4063, 4299, 4464) and 8 text-mode, **8 of 8**
  with `encoding="utf-8"`: l.801 (`pet.json`), 868 (pets README), 1393 (`load_config`), 1426
  (`save_config` fdopen), 1864 (log read, `errors="ignore"`), 2141 (debug log), 2150 (credentials
  file), 2583 (terminal script). `save_config` writes `json.dump(cfg, f)` with the default
  `ensure_ascii=True`, so `~/.claude_pet.json` is pure ASCII and `load_config` reads it under
  utf-8 or cp949 alike, including a file written by an older build; `merge_config_updates` goes
  through `save_config`.
- **Adapter filter.** `_oauth_label()` returns `(t("credit"), 9)` for `extra`/`credit` keys, so
  `_label_order(label) >= 9` drops exactly that row; a server model label that is not a bare family
  word (`_label_order("Claude Fable 5") == 5`, probe 13:53Z) is now kept. (`_label_order` compares
  against the *translated* labels `_oauth_label` produced — consistent within one language.)
- **Memo.** Key = `(mode, id(stats), id(oauth), cost, cost_month, api_budget, auth_error,
  int(time/5))`. Each refresh builds a new stats dict (`commit_refresh_result(state, gen,
  {"stats": compute_usage()})`, l.~7456; `values = {"stats": s, "oauth": oauth, …}`, l.~7684), so
  the ids change. Not in the key: `L["lang"]` and `state["onboard"]`; and CPython may reuse a freed
  dict's address. All three are bounded by the 5-second window (§R6.3).

**B1 re-probed (current tree, 2026-09-12T13:53Z):**

```
$ python3 - <<'PY'
import claude_pet as cp
for pref in (False, True):
    d = cp.RoamDisplay(); d.note("look","approach",True)
    r1 = d.toggle(pref); m1 = d.mode("look", r1)
    d.note("look","approach",True); m2 = d.mode("look", r1)
    r2 = d.toggle(r1); m3 = d.mode("look", r2)
    d.note("rest","approach",True, settled=True); m4 = d.mode("rest", r2)
    print(...)
PY
pref=False: toggle->False mode=folded; relatch mode=folded; toggle->False mode=summary; natural end mode=folded; dismissed=False summary=False
pref=True: toggle->True mode=folded; relatch mode=folded; toggle->True mode=summary; natural end mode=full; dismissed=False summary=False
```

Exactly the gate the round-1 verdict asked for: the preference never flips during a visit,
the per-tick re-latch keeps the dismissal, a second toggle brings the pill back, natural
completion returns to the preference (folded / open). `note()` sets only `self.summary` on
`look`; `reset()` clears both flags. **B1 is resolved.** The chevron comment now reads
"요약(래치) 중엔 그 방문 동안 접기 ↔ 펴기만 오가고 평소 선택은 그대로" — accurate.

Other probes (13:53Z, real `t`, `L["lang"] = "ko"`):

```
SUMMARY_COLORS {'exact': '#50C878', 'estimate': '#FFB300', 'cost': '#FF7F50', 'value': '#F2F2F7',
                'warn': '#FFD60A', 'bad': '#FF453A', 'sub': '#98989F', 'status': '#F2F2F7'}
SUMMARY_H/H2/PILL_W/pill_h 30 46 300 46
summary_value_kind (0,49.9,50,84.9,85,100) → value value warn warn bad bad ; (1, spiking) → bad
ko exact main: [('▲세션','bad'),(' 42%','exact'),(' · ','status'),('주간','value'),(' 17%','exact'),(' · ','status'),('Fable','bad'),(' 92%','exact')]
ko exact sub : [('리셋 ','sub'),('세션 3시간 43분 후','sub'),(' · ','sub'),('주간 2일 4시간 후','sub')]
line2: 리셋 세션 3시간 43분 후 · 주간 2일 4시간 후
est  : ('estimate', [('session',42.0,False,'3시간 후'),('weekly',17.0,False,'-'),('Fable',12.0,True,'-')])
est sub: [('리셋 ','sub'),('세션 3시간 후','sub'),(' · ','sub'),('주간 -','sub')]
cost : ('cost', (3.21, 27.5, 50.0)) → [('오늘 ','value'),('$3.21','cost'),(' · ','status'),('이번 달 ','warn'),('$27.50','cost'),(' / $50','cost')]
cost, budget 0 → ('cost', (3.21, 27.5, None)) → … ('이번 달 ','value'),('$27.50','cost')   (no suffix)
TR sizes {'en': 99, 'ko': 99, 'ja': 99, 'es': 99} identical: True
```

## R3. Item 2 — CLAUDE.md, the READMEs and `preview.png` against the source

**B3 re-read.** The three sentences now say `SUMMARY_SPIKE` (`▲`), `fmt_countdown()`, and the
second-line example `리셋 세션 3시간 43분 후 · 주간 2일 4시간 후` — each matches the probe above.
**B3 is resolved.** "What this is" says "a compact one- or two-line usage summary pill" — matches
`SUMMARY_H`/`SUMMARY_H2`. The Windows sentences are worded as intent ("the intent is that the
Windows port, developed on the `windows` branch, loads the same file"; "nothing in this tree
depends on that") and a `windows` branch exists locally and on `origin` (`git branch -a`). The
Weekly-window paragraph names `fmt_countdown()` and `주간 -` on the reset line — matches the
`est sub` probe. The spike asymmetry is stated ("a weekly or per-model *estimator* spike marks the
exact **session** label") — matches `spike_first=bool(spike_info(stats))` and `spike_info()` being
truthy for any of the three.

Every other claim of the rewritten pill section, checked by symbol (grouping key: one claim):
`draw_summary_pill()` / `roam_summary()` / `roam_summary_runs()` wiring ✓; the first-line example ✓;
no bars, no status line ✓ (grep); `full`/`summary` the same pill, `folded` pet-only ✓
(`RoamDisplay.mode`, `roam_pill_rect`); `SUMMARY_H`/`SUMMARY_H2`/`pill_h()` ✓; the four-row table
(exact = first three gauge rows, credits dropped via `_label_order`; estimate with `SUMMARY_APPROX`;
cost today then month; status) ✓; emerald/amber/coral on the value run, white → `warn` at 50 →
`bad` at 85 on the label run via `summary_value_kind()`, `▲` prefix ✓; `"sub"` second line ✓; `⚠` ✓;
`reset_texts` / `row[2]` / `spike_first` / `>= 9` ✓; `roam_summary_runs(segments, t)` → `(main, sub)`
and `roam_fit_runs()` trims from the end ✓; font: bundled, plist in the bundle, CoreText from source,
system monospaced fallback ✓; fonts row: `.ttf`, OFL 1.1, `setup.py` resource + `ATSApplicationFontsPath`,
`build_app.sh` in `build()` (`build_body` → `copy_fonts "$APP"`) and `update()` (`update_installed`
→ `|| ! copy_fonts "$stage"` before `write_plist`/`sign_app`/`stop_pet`), `verify_release_artifact.py`
refuses without it ✓; the new "User pets" section: `discover_pets()` at the right-click menu build
(l.~6590) and at settings open (l.~7108) ✓, one level down ✓, `id`/`dir` ✓, single candidate or the
one named like the parent ✓, dot-folders and `__MACOSX` ✓, inner symlinks ✓, two levels not searched
✓, the encoding list and the empty-README rewrite ✓, `run_gui()` seeding at startup (inside `try`,
l.~7744) ✓.

Three things are **not** right:

1. **The path list is wrong again, in the way the section itself warns about.** "Where the
   estimate still reaches in exact mode … two visible paths … v0.24 removed a third path (the red
   session bar) along with the bars." The bar is gone, but its successor is in the pill: the adapter
   passes `spike_first=bool(spike_info(stats))`, `roam_summary()` marks the exact **session** row,
   and `_summary_segment_runs` prefixes that label with `▲` and colours it
   `summary_value_kind(pct, True) == "bad"` — an estimator signal repainting a label whose number
   came from the server (probe: `('▲세션','bad'), (' 42%','exact')`). The colour paragraph twelve
   lines above says exactly this ("Note the asymmetry in exact mode…"), so the section contradicts
   itself; and the closing "never as wrong numbers on a logged-in user's pill" is true only of the
   numbers. In API mode `spike_info()` returns `None` → `spike_first=False`, so this path is
   suppressed there like path 1. → **B4 (§R7).**
2. The API-mode example `오늘 $x · 이달 $y / $budget` and "the word "이달"": `TR["ko"]["this_month"]`
   is `"이번 달"`, so the rendered line is `오늘 $3.21 · 이번 달 $27.50 / $50` (probe). Wording only —
   §R6.
3. "It memoises the result per input and 5-second window" follows a sentence whose subject is
   `roam_summary()`, which is pure; the memo is in the adapter `roam_summary_text()`. Ambiguity —
   §R6.

Stale sentences elsewhere in CLAUDE.md: `grep -nE 'bars?\b|draw_exact_pill|draw_sub_pill|
draw_api_pill|status line|PILL_ROWS|CUR_PILL|fmt_reset|bar_color|gauge pill|spike_prefix|expanded|
\.otf|OTTO|one-line'` → 8 lines: l.28 (`menu bar`), l.871/874/920 (a screen's menu bar / title bar),
and l.737/758/764/786 — the new section's own historical references ("no gauge bars … any more",
"the old bars used", "the old status line's `⚠`", "removed a third path (the red session bar)").
None describes bars, `draw_exact_pill`, the status line, `PILL_ROWS` as display rows, or `CUR_PILL`
as current behaviour. Nested pet folders are now documented ("User pets"); recommend two additions
(§R6.4).

**READMEs (en/ko/ja/es), pill / pets / menu sections** — checked against the source
(grouping key: one sentence, four locales each):

- Line-1 examples (`Session 42% · Weekly 17% · Fable 12%` and the three translations) ✓; API
  example without a budget (`Today $3.21 · This month $27.50`) ✓ (probe with budget 0).
- Line-2 examples: en `reset Session in 3h 42m · Weekly in 2d 3h` = `reset_prefix` + `cd_hm`
  (`in {h}h {m}m`) + `cd_days` (`in {d}d {h}h`); ko `리셋 세션 3시간 42분 후 · 주간 2일 3시간 후`; ja
  `リセット セッション 3時間42分後 · 週間 2日3時間後`; es `reinicio Sesión en 3h 42m · Semanal en 2d 3h`
  — all four match `TR`; "weekly shows `-` on a rolling window" ✓ (`fmt_countdown(None)` → `-`).
- "Number colour says where it comes from … emerald / amber (≈) / coral … estimate line ends with
  ⚠" ✓; "Label colour says how much is left: white, yellow from 50 %, red from 85 % — red with ▲
  while spiking" ✓ (`summary_value_kind`, inclusive thresholds); Pretendard, SIL Open Font License ✓.
- Spike bullet "that gauge turns red with ▲ in the pill" ✓ per gauge on estimate rows; on exact rows
  it is always the session label (§R3.1) — the README does not distinguish, acceptable for users.
- Menu order: code builds Settings, toggle, Roam, Reset size, then inserts the **Pets** submenu at
  index 4, then separator, Uninstall, Quit, separator, version, Check for updates (l.~6571–6620) —
  the README order matches. The item the README calls "Show or hide the pill" is still
  `TR[*]["menu_toggle"]` = "Collapse/expand gauges" / "게이지 접기/펴기" / "ゲージの折りたたみ" /
  "Contraer/expandir medidores" — the strings name a thing that no longer exists (§R6.5).
- "Your own pets": Pets submenu lists the cat plus `~/.claude_pet/pets/` folders ✓ (`discover_pets`
  puts the built-in first); "Add a pet…" = `pet_add` ("➕ Add a pet… (open folder)") →
  `open_user_pets_dir()` writes the README and opens the folder ✓; re-read on every menu open ✓;
  one level deep and `__MACOSX` ✓.
- **Wrong in all four:** the Settings bullet says "(Admin API cost — today, this month; the monthly-budget
  field is not shown in the pill yet)" / "월 예산 칸은 아직 필에 표시되지 않음" / "月次予算の欄はまだピルに
  表示されません" / "el campo de presupuesto mensual aún no se muestra en la píldora". Since round 2 the
  budget **is** in the pill: `roam_summary("api", …, cost_budget=RUNTIME["api_budget"])` returns
  `(today, month, budget)`, and the line reads `오늘 $3.21 · 이번 달 $27.50 / $50` with "이번 달"
  coloured by `month / budget` (probe; `test_cost_runs_colour_the_month_word_by_budget…` green). The
  staged release note says the opposite of the README ("오늘·이번 달 비용을 월 예산과 함께 보여 줍니다")
  and the note is the one that is right. → **B5 (§R7).**

**`preview.png`** (the screenshot the README opens with). Rendered and decoded
(`sips -s format bmp` → BMP, 408×228, 32 bpp; per-column majority colour over rows 8–40 of the
first text line, classes white/green/yellow/red; script inline in the record's command log,
13:54Z):

```
line1 runs: [('green', 55, 98), ('white', 99, 161), ('green', 162, 205), ('white', 206, 256),
             ('green', 257, 317), ('white', 318, 348)]
line2 runs: []          (the reset line is the dim 'sub' grey — no class)
```

Read against the image: `세션`(green) `24%`(white) · `주간`(green) `4%`(white) · `Fable`(green)
`6%`(white). That is the **round-1/2 assignment** — labels in the source colour, values white. The
shipped code, the README text beside the image, RELEASE_NOTES bullet 2 and CLAUDE.md all say the
reverse (labels white, values emerald). `stat`: `preview.png` 21:31:31 local (12:31:31Z), i.e. from
round 1; the round-3 swap landed at 22:30–22:32 local. → **B6 (§R7).** Regenerating it needs the
GUI, which this role may not launch.

## R4. Item 3 — RELEASE_NOTES.md v0.24 (staged) and the published sections

```
$ python3 (bytes from the **v0.23** heading to EOF; prefix before **v0.24**)
published tail identical to HEAD: True     sha256 c7ddc40a8a25ce8e…   (= the v0.23 release commit's, Verifier §1)
prefix identical to HEAD's prefix before **v0.23**: True
top-level bullets: 3   nested: 0   normalized length (bullets): 372 ≤ 450
sentences per bullet: 2 / 2 / 2
$ python3 -m unittest tests.test_v023_release_contract -v   (13:54Z)
Ran 14 tests in 0.237s   OK      — including test_v024_notes_follow_the_three_bullet_450_character_format
                                   and test_v024_thresholds_and_markers_match_the_source
```

**B2 is resolved**, by the repo's own gate and by hand (bullets 1 and 2 are two sentences each;
`Pretendard (OFL)` with the space). Claims audited in the tree: one pill (`draw_summary_pill`, the
only draw path); first line session·weekly·model %, second line reset time (`main`/`sub` runs); API
mode today · this month with the monthly budget (`(today, month, budget)`, ` / $50`); value colour by
source (`SUMMARY_COLORS`, `SUMMARY_APPROX`); label white → yellow at 50 → red at 85
(`summary_value_kind`, inclusive), `▲` + red on a spike (`SUMMARY_SPIKE`, `"bad"`); `⚠` at the end of
the estimate line after a token expiry (`auth_error` run); Pretendard (OFL) bundled (`fonts/`, OFL 1.1
licence, `setup.py`, `build_app.sh`, `verify_release_artifact.py`); one-level-deeper pet folders
(`_nested_pet_dir`); "따로 할 일은 없고, 접기/펴기·크기 조절·설정은 그대로" (the chevron, wheel and
settings paths are unchanged in the diff). No hash, source path, line number, test name, or
magnitude/frequency word (the gate's forbidden-pattern scan is green). **The nested-pet-folder fix is
already in bullet 3** ("zip을 풀어 한 단계 더 깊어진 펫 폴더(pets/이름/이름/)도 인식합니다"), so the
assignment's premise that it is missing does not hold; nothing needs adding. Not mentioned and not
needed: the Windows 0-byte-README/encoding fix (invisible on the macOS artifact) and the startup
README seeding (a user-invisible repair path).

## R5. Item 4 — do the Verifier's fixtures discriminate?

Independent full-suite run (the assignment's exact command, repo root):

```
start 2026-09-12T13:51:55Z   end 2026-09-12T13:57:18Z
$ python3 -m unittest discover -s tests -v > <scratchpad>/rev3_suite.log 2>&1 ; echo rc=$?
Ran 559 tests in 322.614s
OK (skipped=7)
rc=0
```

Grouping key: one unittest result header; file set: the 21 modules under `tests/`. 0 `FAIL:`/`ERROR:`
headers; the 7 skips are the same opt-in live checks the Verifier quotes (`…V020_TO_V021_BOUNDARIES=1`
×3, `…RUN_LIVE_UPDATER_TESTS=1` preflight ×2, stapler ×2). Same numbers as the Verifier's §C7
(559 / OK / skipped=7). The working-tree hashes are identical before and after the run (§R1).

**Nine forward mutants of the CURRENT file**, each a plausible wrong new implementation and
deliberately **different** from the Verifier's 16 (§C5) and the round-1 Reviewer's 10 (§5 above);
driver `<scratchpad>/rev3/mutants.py`, scratch trees `<scratchpad>/rev3/mut/<name>/` (copies of the
current `claude_pet.py`, `setup.py`, `build_app.sh`, `verify_release_artifact.py`, `fonts/` and the
test module under `tests/`; one `str.replace` asserted to match exactly once; cwd = the tree; the
working tree untouched — hashes in §R1). Window 13:56:19Z–13:56:32Z. Grouping key: one unittest
result header; the last column lists the failing methods and **only** those.

| mutant (the wrong implementation) | module (n) | result | failing — and only these |
| --- | --- | --- | --- |
| N1 `_nested_pet_dir` descends recursively (two levels accepted) | nested (15) | FAILED failures=2 | `test_two_levels_deep_is_not_recognised`, `test_nested_pet_dir_helper_contract` |
| N2 `discover_pets` no longer skips `__MACOSX` at the top level | nested | FAILED failures=1 | `test_junk_and_dot_folders_are_skipped_at_both_levels` |
| N3 `_write_pets_readme` rewrites every time (early return dropped) | nested | FAILED failures=1 | `test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept` |
| S1 `summary_value_kind`: a spike counts only at ≥ 50 % | summary (31) | FAILED failures=6 (4 methods) | `test_thresholds_are_50_and_85_inclusive_and_spike_wins`, and the three colour fixtures whose spiking rows sit below 50 % |
| S2 `RoamDisplay.toggle` sets `dismissed = True` (never un-dismisses) | summary / motion (51) | failures=2 / failures=5 | summary: `test_toggle_during_the_latch_dismisses_for_the_visit_and_keeps_the_preference`; motion: `test_approach_summary_toggle_dismisses_…`, `test_hover_stop_away_keeps_summary_until_the_user_dismisses_it` |
| S3 adapter passes `spike_first=False` | motion | FAILED failures=1 | `test_actual_summary_formatter_distinguishes_estimate_from_exact` |
| S4 month share computed as a fraction (`month / budget`, no ×100) | summary / motion | failures=2 / failures=1 | summary: `test_cost_runs_colour_the_month_word_by_budget_…`, `test_source_kind_sits_on_the_value_run_…`; motion: the adapter test |
| G1 `roam_apply_display` measures text for `summary` only (`full` gets `0.0, SUMMARY_H`) | motion | FAILED failures=1 | `test_folded_drop_clamps_logical_envelope_before_save_and_restore` (the restored `full` window is no longer `(160, 98)`) |
| F1 `verify_release_artifact.py` accepts `OTTO` as well as `00 01 00 00` | preflight (8) | FAILED failures=1 | `test_bundle_without_the_font_or_with_a_non_truetype_file_is_rejected_before_validator` (the `cff` shape) |

9 built, 9 caught, each by the tests whose docstrings name that rival and by no unrelated test —
the fixtures discriminate in both directions. Logs: `<scratchpad>/rev3/mut/<name>/run_<module>.log`,
summary `<scratchpad>/rev3/mutants.out`.

Corpus safety: `grep -nE 'expanduser|HOME|~/|\.claude_pet|\.claude/'` over `test_summary_pill.py`,
`test_nested_pets.py`, `test_release_artifact_preflight.py` → 0 matches outside `claude_pet.`
attribute references; `test_companion_motion.py` touches `pwd.getpwuid` only inside the opt-in native
smoke, which was not run. `PetTreeCase` repoints `claude_pet.USER_PETS_DIR` and `PET_DIR` into a
`tempfile.TemporaryDirectory()` and restores them by `addCleanup`; `BundledFontTests` patches
`claude_pet.__file__` into a temp dir for its negative case; the manual-update harness's `fonts` stub
writes under `checked()` inside its temp root and copies nothing from `fonts/`; the preflight fixtures
write a 64-byte magic-plus-padding font. No test in the diff reads `~/.claude` or writes `~/.claude_pet*`.

Hash re-pins: the four new values (`5ba2cee2…`, `c148fd7f…` ×2, `db8e1ff9…`) equal the bytes I hashed
(§R1); `release.sh` unchanged (`a5b25686…` = its pin). The round-3 re-pins of the colour fixtures are
the swapped roles the user asked for, and the round-2 `.otf`/`OTTO` fixtures were rewritten around
`.ttf`/`00 01 00 00` (the Verifier's own §C3 note about the vacuous pass is correct and the rewrite
is what my F1 mutant exercises). `test_settings_and_install`'s anchor now includes `"fonts"`;
`test_v023_release_contract` pins the v0.23 bytes (`c7ddc40a…`, matches §R4) and expects
`['0.24', '0.23']`. The opt-in native smoke's edited compact gate stays *unverified red*, as both
records say; nothing in the suite depends on it.

## R6. Non-blocking recommendations

1. **`draw_summary_pill()` docstring** still says "첫 줄 = 라벨(출처 색)+수치(잔여량 색)" (l.~6848) —
   the pre-swap assignment; the code, `SUMMARY_COLORS`' comment, CLAUDE.md and the note say the
   reverse. Comment-only.
2. **CLAUDE.md wording** (§R3.2–3): `이달` → `이번 달` in the API-mode example; make the memo sentence's
   subject the adapter (`roam_summary_text()`), not `roam_summary()`.
3. **Memo key** in `roam_summary_text()` omits `L["lang"]` and `state["onboard"]`, and relies on
   `id(stats)`/`id(oauth)` (an address CPython may reuse). All bounded by the 5-second window — at
   worst a pill in the previous language, or the previous refresh's text, for ≤ 5 s after a change.
   Adding `L["lang"]` and `state.get("onboard")` to the key costs nothing.
4. **CLAUDE.md "User pets" additions**: say that the outer `pets/<name>` symlink is followed
   (pre-existing, unchanged) while inner symlinks are not; and that the whole-folder skip of the
   seeding section does not apply to user pets (they are re-read on every menu open, never copied).
5. **`menu_toggle` strings** in all four locales still say "gauges" (게이지 / ゲージ / medidores) —
   the menu item now shows/hides the summary pill, and the READMEs describe it as such. A four-string
   change; the READMEs' menu line would then quote the real item.
6. **Windows-facing claims** ("the CFF build rendered roughly at small sizes on Windows", the `windows`
   branch loading the same file through Qt) are unverifiable in this tree; they are worded as reason
   and intent, which is fine — do not harden them into invariants here.
7. **Separation is still claimed, not yet checkable**: nothing is committed, so §2 Conditions A/B
   will first be readable from the trailers of the commit. What I see is consistent with the records:
   production/doc files carry the Developer's mtimes (22:30–22:32 local), tests the Verifier's
   (22:24–22:27 and 21:45–21:47).

## R7. Blocking findings — must fix before the commit

- **B4 (CLAUDE.md)** The rewritten pill section's list "Where the estimate still reaches in exact
  mode" counts **two** paths and says "v0.24 removed a third path (the red session bar)". The path
  survives in the pill: `spike_first=bool(spike_info(stats))` → `▲` + `"bad"` on the exact **session**
  label (§R3.1, probe `('▲세션','bad'), (' 42%','exact')`). List it as path 1 (suppressed in API mode
  because `spike_info()` returns `None`), keep "never as wrong **numbers**". The section's own preface
  says this list "has been wrong before" for exactly this omission; a documentation commit's
  `Verifier:` could not find it accurate (AGENTS.md §7).
- **B5 (README ×4)** "the monthly-budget field is not shown in the pill yet" (and its ko/ja/es forms)
  is false since round 2: the pill shows `… · 이번 달 $27.50 / $50` with the month word coloured by the
  budget share (§R3). Replace with what the release note already says.
- **B6 (preview.png)** The screenshot shows the round-1/2 colouring — labels emerald, values white
  (pixel runs in §R3; mtime 12:31:31Z, before the round-3 swap) — the opposite of the README text
  beside it, the release note and the code. Regenerate from the current pill (needs the GUI; not this
  role's to run).

No code defect was found in rounds 2–3; the Verifier's "no product defect" finding stands.

## R8. Untracked work and process

```
diag.py                          2026-07-22T12:07:01  (13:50Z and 13:58Z)
release/icon_1024.png            2026-07-13T23:46:36  (both)
release/ClaudePet.iconset/*      2026-07-13T23:46:36  (14 files, both)
```

Untracked paths present (`git status --porcelain --untracked-files=all`, 38 entries): the three
user-owned paths above (16 files); `fonts/Pretendard-SemiBold.ttf`, `fonts/LICENSE-Pretendard.txt`;
`tests/test_nested_pets.py`, `tests/test_summary_pill.py`; under `docs-design/`: the eight
`companion-play-*`/`free-roaming-*` files, the six `quiet-companion-*` files,
`release-v022-operator-20260911.md`, `release-v023-operator-20260911.md`,
`summary-unify-verification-20260912.md`, and this file. The only untracked path this role wrote is
this file (appended; the round-1 text above is unchanged). No git write command was run (`status`,
`diff`, `show`, `branch -a` only); nothing committed, tagged, pushed, signed, built, installed or
released; `./release.sh` and `./build_app.sh` not invoked (read as text; copied into scratch trees
only for the tests that read them as text); no GUI launched; the dev instance (PID 43658,
`python3 claude_pet.py`, elapsed 25:31 at 13:58Z) untouched; `~/.claude` never read by a test or
probe, `~/.claude_pet*` never written; the pre-change copy `<scratchpad>/claude_pet.pre-unify.py` was
not used this round (its revert-and-observe runs are the Verifier's §C3; mine are forward mutants).
Scratch under `<scratchpad>/rev3/` and `<scratchpad>/rev3_*.{log,txt}` only.

## R9. Provenance summary (AGENTS.md §5)

- Grouping key: one unittest result header (suite, mutants); one grep match line (symbol scans);
  one claim / one sentence per locale (documents); one bullet line and one `.`-terminated sentence
  (release note); one image column (preview.png).
- Window: 2026-09-12T13:51:55Z – 13:58:15Z, UTC (opening `git status` about a minute earlier).
- File set read: §R1.
- Numerators/denominators: suite 0 failing / 559, 7 opt-in skips; mutants 9 caught / 9 built, each by
  the intended tests only; text-mode opens 8 with `encoding="utf-8"` / 8; removed-symbol grep 0
  survivors / 4 lines matched / 40 patterns; release note 372 chars / 450, 3 bullets / 3, 2+2+2
  sentences; CLAUDE.md pill-section claims 3 wrong / ~35 checked; README wrong sentences 1 per
  locale / 4 locales; preview.png first-line runs 6, alternating green/white.
- Measured at: the timestamps beside each command.

---

# Round 6 — 2026-09-12, 14:10Z–14:16Z (reviewer-v024, re-check of B4/B5/B6 only)

Assignment: confirm first-hand that the three round-5 blocking items are fixed, that the
Developer changed no code or test (so the Verifier's round-5 GREEN and hash pins stand), and run
the fast contract module. Read-only; this section is the only write.

## S1. Code and tests are the round-5 tree

`shasum -a 256` (14:10Z): `claude_pet.py` c148fd7f8a46f39bbf89cca11658ca13191bb5b85717b883b41c94150548aa00,
`build_app.sh` db8e1ff994a05614daa72c21c5e4436ff7e218ce5286cb4c95590a3f306dd96b,
`verify_release_artifact.py` 5ba2cee236a3c624254e6deac166644f919792f6b9d831a07a53c14c36a63324 —
all three equal the Verifier's pins (verification record §C1 l.590–593, §C7). Source mtimes
13:32:06Z, unchanged since round 5.

`git status --porcelain`: 17 modified (the same 17 as round 5: CLAUDE.md, README ×4,
RELEASE_NOTES.md, build_app.sh, claude_pet.py, preview.png, setup.py, six `tests/*.py`,
verify_release_artifact.py) and 38 untracked (`--untracked-files=all`), the same set as §R8: the
three user-owned paths (16 files), `fonts/` (2), `tests/test_nested_pets.py`,
`tests/test_summary_pill.py`, and 19 `docs-design/` files including this one. **No test file
changed since the Verifier's final suite**: the eight test files in the diff (six modified, two
new) are exactly the eight the Verifier's record names, with mtimes ≤ 13:41:58Z — before the
Verifier's C7 run (13:44:27Z–13:49:52Z, 559 tests OK) and before my round 5 (13:51Z–13:58Z).
What did change after round 5: CLAUDE.md and the four READMEs (14:03:29Z) and `preview.png`
(14:10:26Z). `RELEASE_NOTES.md` (13:30:34Z) and `setup.py` (11:55Z) untouched.

`python3 -m unittest discover -s tests -p "test_v023_release_contract.py"`
→ `Ran 14 tests in 0.250s — OK` (14:10Z).

## S2. B4 — CLAUDE.md pill section: resolved

The paragraph "Where the estimate still reaches in exact mode" (l.785–813) now lists **three**
paths, each checked against the source by symbol:

1. *Exact session label turns red with ▲ inside the pill.* `roam_summary_text()` passes
   `spike_first=bool(spike_info(stats))` (l.6826); `roam_summary()` marks row 0 only —
   `bool(spike_first) and i == 0` (l.5866); `_summary_segment_runs()` prefixes the label with
   `SUMMARY_SPIKE` and colours it `summary_value_kind(pct, spiking)` → `"bad"` (l.5942, l.5904–5908)
   while the value run keeps kind `"exact"` (emerald). Probe (system `python3`, `import claude_pet`):
   `roam_summary("sub", [("세션",42,None),("주간",17,None),("Fable",12,None)], …, spike_first=True)`
   → `[('▲세션','bad'), (' 42%','exact'), (' · ','status'), ('주간','value'), (' 17%','exact'), …]`.
   The asymmetry is stated in path 1 and again in the colour paragraph (l.760–762): `spike_info()`
   is truthy for session, opus **or** weekly (l.6348–6353), and only row 0 is marked. The
   "values untouched" claim matches. ✓
2. *Spike → the pet.* `current_mood()` returns `"failed"` on `spike_info(stats)` before the
   `state["oauth"]` branch (l.6356–6364); `tick_()` sets `dirty` while a spike is live (l.7663);
   the pulsing `SourceAtop` tint (l.6455–6460); the greeting guard `not spike_info(state["stats"])`
   (l.7646). ✓
3. *Session-reset greeting.* `if prev and prev["session"]["pct"] > 5 and s["session"]["pct"] < 1:
   set_override("jumping")` (l.7694), `prev = state["stats"]`, `s` from `compute_usage()`, and the
   only mode test in that block is the `cost_month` fetch above it — no mode guard on the
   comparison. ✓

API-mode paragraph (l.809–813): "Paths 1 and 2 are suppressed there by one mechanism:
`spike_info()` returns `None` outright when `RUNTIME["mode"] == "api"`" — l.6345
`if not stats or RUNTIME["mode"] == "api": return None` ✓; "the API line has no session row
anyway" — the `api` branch of `roam_summary()` returns a `cost` segment ✓; "Path 3 has no guard and
still fires in API mode" ✓. Closing sentence: "never as wrong **numbers** on a logged-in user's
pill" ✓. Residue grep for `two visible paths|removed a third|red session bar|draw_exact_pill|이달`
→ 0 lines.

The two wording fixes: l.763 now reads `오늘 $x · 이번 달 $y / $budget` with "이번 달"
(`TR["ko"]["this_month"] == "이번 달"`, probe) ✓; l.769 "The adapter, `roam_summary_text()`,
memoises its result per input and 5-second window" — `_summary_memo` keyed on
`int(_time.time() / 5)` in that function (l.6808–6812) ✓.

## S3. B5 — README "Data source" bullet ×4: resolved

The false sentence is gone from all four (grep `not shown|not yet|아직|まだ|aún|todavía` on the
bullet → 0). The replacement, against the pure functions (probe: `roam_summary("api", None, None,
None, 3.21, True, cost_month=27.5, cost_budget=50.0)` → `roam_summary_runs` with
`tr = TR[lang].get`):

| locale | README example | rendered line | month-word run |
| --- | --- | --- | --- |
| en (l.112) | `This month $27.50 / $50` | `Today $3.21 · This month $27.50 / $50` | `('This month ', 'warn')` |
| ko (l.110) | `이번 달 $27.50 / $50` | `오늘 $3.21 · 이번 달 $27.50 / $50` | `('이번 달 ', 'warn')` |
| ja (l.111) | `今月 $27.50 / $50` | `今日 $3.21 · 今月 $27.50 / $50` | `('今月 ', 'warn')` |
| es (l.114) | `Este mes $27.50 / $50` | `Hoy $3.21 · Este mes $27.50 / $50` | `('Este mes ', 'warn')` |

Every example is a substring of its rendered line. At 55 % of budget the month word is `warn`
(`COL_WARN` #FFD60A, yellow); at 90 % `bad` (`COL_BAD` #FF453A, red); amounts are `cost` (coral)
and `today` is `value`; without a budget the line ends at the month amount. "turn yellow/red by the
share used" (and 노랑·빨강 / 黄・赤 / amarillo/rojo) matches `summary_value_kind(min(100,
month/budget*100))` at l.5952. The sentences validated in round 5 elsewhere in the READMEs (line-1
and line-2 examples, label-colour thresholds, ▲, Pretendard) are still present in all four
(anchor grep: 5 hits per locale).

## S4. B6 — `preview.png`: resolved

`stat`: 14:10:26Z, 54 241 bytes (HEAD's: 126 986 bytes, 520×472). `sips`/`file`: 378×228, 8-bit RGBA,
144 dpi both axes (Retina 2×); corners fully transparent, pill ground (33,33,36,244). Embedded
metadata (PIL `im.info`): Apple ICC display profile with description **"LG ULTRAWIDE"** (a monitor
profile — the mark of a macOS screen capture, which the Windows offscreen render would not carry),
EXIF with 144 dpi, XMP `exif:UserComment` = `Screenshot`. Visual read of the file: a Mac cat sprite
on a transparent ground, Pretendard glyphs, first line `세션 55% · 주간 10% · Fable 18%`, second
line `리셋 세션 59분 후 · 주간 6일 20시간 후`.

Per-column majority class over rows 23–42 (first line; classes by hue on pixels with α ≥ 128 and
max channel > 120; runs separated by ≤ 8 px merged), scratchpad `winvenv` PIL 11.2.1:

```
line1: yellow 30–66 | green 75–118 | white 127–174 | green 181–222 | white 231–295 | green 303–344
line2 (rows 64–80): grey 40–335
```

Read against the image: `세션`(yellow, 55 % ≥ 50) `55%`(green) · `주간`(white) `10%`(green) ·
`Fable`(white) `18%`(green); reset line grey. That is the shipped assignment — labels white/yellow
by remaining share, values emerald — the reverse of round 5's runs (§R3: green/white alternating,
labels green). Sampled colours vs. the app's constants converted sRGB → Display P3 (the closest
standard space to a monitor profile): green (111,196,133) vs emerald `#50C878` → (114,197,128)
[not `COL_OK` `#32D74B` → (107,212,95)]; yellow (250,215,62) vs `COL_WARN` → (248,216,74); white
(243,243,247) vs `TXT_MAIN` (242,242,247); grey (159,159,165) vs `TXT_SUB` → (152,152,158). The
screenshot is of the current pill.

## S5. Verdict and non-blocking recommendations

**PASS.** B4, B5 and B6 are resolved, the three hash pins hold, no test changed after the
Verifier's GREEN, and the contract module is OK. The staged v0.24 note is unchanged since round 5
(3 bullets, 0 nested, 372 normalised chars, no hashes/paths/test names).

Recommendations (none blocking; the first two are in files this commit touches, the rest carry
over from §R6):

1. CLAUDE.md path 2 says "Three further effects hang off that same signal"; there are four.
   `roam_tick()` folds a live spike into `busy` (l.6950–6951), which is passed to
   `roamer.step(busy=…)` and to `disp.note(interrupted=… busy …)` — so a phantom spike also keeps
   the pet from setting out on a walk and interrupts the roam display latch. The count predates
   v0.24 (it was "three" before free roaming existed), so it is an inherited undercount, not a
   regression; still, a sentence the section tells the reader to re-derive should count right.
2. README ×4 "the words turn yellow/red" — say which words: the *This month* label turns
   yellow/red; the amounts stay coral. As written a reader may expect the `$` figures to change.
3. CLAUDE.md l.760 is a ~150-column line (the quoted Korean decision); wrap to the file's width.
4. Carried from §R6.5: `TR[*]["menu_toggle"]` still reads "Collapse/expand gauges" /
   "게이지 접기/펴기" / "ゲージの折りたたみ" / "Contraer/expandir medidores" for the item that now
   shows or hides the pill — a code string, so a later release, not this doc-only fix.

## S6. Process and provenance (AGENTS.md §4, §5)

No git write command was run (`status`, `ls-files`, `diff --stat`, `show HEAD:preview.png` into
the scratchpad, `log -1 -- preview.png` only); nothing committed, tagged, pushed, built, signed,
installed or released; neither shell script invoked; no GUI launched — the dev instance (PID 43658,
`python3 claude_pet.py`, elapsed 40:38 at 14:12Z) untouched; `~/.claude` never read, `~/.claude_pet*`
never written; no untracked file other than this one modified. Scratch: `<scratchpad>/preview_head.png`.

- Grouping key: one claim (CLAUDE.md), one sentence per locale (READMEs), one image column
  (preview.png), one unittest result header, one `shasum` line.
- Window: 2026-09-12T14:10Z–14:16Z UTC (`date -u` at the last command: 14:15:50Z).
- File set read: CLAUDE.md l.728–818; README.md l.105–120, README.{ko,ja,es}.md Data-source
  bullets and the round-5 anchor lines; RELEASE_NOTES.md l.82–88; claude_pet.py l.5835–5985,
  6344–6364, 6450–6460, 6795–6840, 6936–6975, 7640–7700 and the grep lines quoted; preview.png
  (whole); the Verifier's record §C1/§C4/§C7 lines quoted; this record §R3/§R7–R9.
- Numerators/denominators: hashes 3 match / 3; CLAUDE.md path list 3 correct / 3 paths, API
  paragraph 3 claims / 3, wording fixes 2 / 2; README sentences 4 correct / 4 locales; preview
  first-line runs 6 (3 label + 3 value), label classes yellow/white/white, value classes
  green ×3, second-line runs 1 (grey); test module 14 / 14 OK; test files changed after the
  Verifier's GREEN 0 / 8; untracked paths 38 (unchanged).
- Measured at: the timestamps beside each item.
