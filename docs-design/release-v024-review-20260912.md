# Review record — ClaudePet v0.24 release commit (round 7)

**Verdict: PASS — no blocking finding. Eleven non-blocking recommendations (§6), the first
of which should land as a docs-only commit before `git push origin main`.**

- **Reviewer:** `reviewer-v024`, round 7 (Claude Code workflow subagent, spawned by the
  Developer session `55c3dee4-727f-4a94-b960-66540b129014`). Held no other role on this
  release — not Developer, Verifier, Coordinator or Operator. Read-only throughout; the only
  file created is this record. No `git` write command, no build or release script, no GUI
  launch, no read of `~/.claude`, no write under `~/.claude_pet*`. One read-only network
  action: `git fetch origin windows`.
- **Why this round exists** (Coordinator gate record, item 1-6): the round-6 PASS covered
  `claude_pet.py` at sha256 `c148fd7f…`; the committed source is `6f95bc8b…` after seven
  Developer hunks, and the `docs/` site, `preview.png` and the four READMEs' later edits had
  not been reviewed first-hand.
- **UTC window:** 2026-09-12T15:17:48Z (first command) → 2026-09-12T15:28Z (record written).
- **cwd:** `/Users/yeongyu/claude-pet` (absolute paths in every command; the sandbox resets
  cwd between calls).
- **Tree under review:** HEAD `a1f3d22ad6a2e4ea2ce53362dddc74b6f61f7559` (`release: ClaudePet
  v0.24`, authored 2026-09-12T23:56:14+09:00). `git status --porcelain` at 15:17:48Z: no
  `M`/`A`/`D`/`R` for any tracked path; 23 `??` entries (`diag.py`, `release/ClaudePet.iconset/`,
  `release/icon_1024.png`, and 20 `docs-design/` captures and records). Trailers
  `Developer: Claude (session 55c3dee4-…)` / `Verifier: verifier-v024` / `Reviewer:
  reviewer-v024` — three distinct parties.
- **Hashes at 15:18Z** (`shasum -a 256`): `claude_pet.py`
  `6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4`;
  `verify_release_artifact.py` `34c4e57f62079be9ae1d7a70e6a74badc4244fc9c0045d6109760206fedd47c6`;
  `RELEASE_NOTES.md` `a01f2e4cd77439c095248875bb86cf3b4e2711ee12722f22ea0fa115c194513b`;
  `preview.png` = `docs/assets/preview.png` =
  `a79a93bb440e8fee4e27085bd85a9f0ad1fd76f50184d1c519e7e3764e66e52c` (`cmp` equal; 378×228
  RGBA). Both test harnesses (`tests/test_manual_update_transaction.py:45`,
  `tests/test_upload_artifact_gate.py:63`) pin `REVIEWED_APP_SOURCE_SHA256` = `6f95bc8b…`,
  i.e. the committed bytes.
- **Outside world at 15:20Z:** `git branch -r --contains HEAD` → `origin/windows` only
  (`origin/main` is at `92fe4ee`); `git tag --sort=-v:refname | head -1` → `v0.23`. No v0.24
  tag exists; the v0.24 notes section is staged, not published.
- **Suite:** not re-run by this Reviewer (read-only mandate). Cited from the Verifier's
  execution-gate record `docs-design/release-v024-verification-20260912.md`: `python3 -m
  unittest discover -s tests -v` from the clean tree at `a1f3d22…`, 14:57:56Z–15:03:20Z,
  `Ran 565 tests in 324.620s` / `OK (skipped=7)`, exit 0.

Process documents read first: AGENTS.md §1, §5, §7, §8; CLAUDE.md "Release procedure"
(in context), "Cost weighting", "Windows", "exact vs estimate".

---

## 1. Item (a) — the seven hunks between the round-6 bytes and HEAD

Source of the hunk list: the Verifier's record `docs-design/summary-unify-verification-20260912.md`
§F1 (reconstructed diff `ver4/round5_to_final.diff`, 7 hunks). I did not reconstruct the
round-6 bytes again; I read each hunk **in HEAD by symbol** and checked its consistency with
the rest of the file.

| # | Hunk | Read at | Finding |
| --- | --- | --- | --- |
| 1 | `APP_VERSION = "0.24"` | `claude_pet.py:937` | Present. `setup.py` derives `CFBundleShortVersionString` from it by regex; `verify_release_artifact.py:28` usage example says `0.24` (item b). |
| 2–5 | `TR[en/ko/ja/es]["menu_toggle"]` | lines 1057, 1138, 1215, 1297 | AST `literal_eval` of `TR` at 15:21Z: four locales, **99 keys each, key sets identical to `en`**. Values: en `Show/hide the usage pill`, ko `사용량 필 접기/펴기`, ja `使用量ピルの表示/非表示`, es `Mostrar/ocultar la píldora` — exactly the assignment's strings. |
| 6 | `roam_summary_text()` memo key | lines 6795–6836 | Key is `(RUNTIME["mode"], L["lang"], state.get("onboard"), id(stats), id(oauth), state["cost"], state["cost_month"], RUNTIME.get("api_budget"), bool(OAUTH_STATUS.get("auth_error")), int(_time.time()/5))`. |
| 7 | `draw_summary_pill()` docstring | line 6849 | `첫 줄 = 라벨(잔여량 색)+수치(출처 색)` — matches the code path: `_summary_segment_runs` (5945–5952) emits the label with `summary_value_kind(pct, spiking)` and the value with `kind` (`exact`/`estimate`); `F_SUMMARY_BY_KIND` (6168) maps every `SUMMARY_COLORS` key to its hex. |

**Hunk 2–5 consistency.** The only consumer of the key is the context-menu builder
(`t("menu_toggle")`, line 6572). `grep -rn -i 'collapse/expand|expand gauges|게이지 접기|ゲージの折りたたみ|expandir medidores'` over `claude_pet.py`, `tests/`, `docs/index.html`,
`docs/llms*.txt`, the four READMEs and `CLAUDE.md` at 15:27Z: **no match**. The only test
naming the key is `tests/test_v024_release_contract.py` (lines 595–615), which pins the
*new* wording ("every locale's toggle must name the pill", ko must contain `접기/펴기`).
The READMEs' Controls line says "Show or hide the pill" / "접기·펴기" / "表示・非表示" /
"Mostrar u ocultar", consistent with the new labels.

**Hunk 6 correctness — can the memo serve stale text across a language change?** No.
`L["lang"]` changes only in `set_lang()` (line 1026), whose sole caller is `apply_config()`
(1006), reached at start-up and from the settings-save path (7802). `t()` reads `L["lang"]`,
so every translated run (`session`/`weekly`, `reset_prefix`, `today`, status keys) depends on
it; with `L["lang"]` in the key a save that changes the language misses the memo on the next
tick. `state["onboard"]` is a `str`/`None` (hashable) set by `commit_refresh_result` together
with `stats`/`oauth`/`cost` (7684–7692), so including it is belt-and-braces but correct.

One input to `roam_summary()` is **not** in the key: `bool(RUNTIME.get("admin_key"))`
(line 6826), which `apply_config` can also change at runtime. Effect: in API mode, after
entering an Admin key without changing mode, the pill can keep showing the
`need_admin_key` status until the next 5-second bucket (`int(_time.time()/5)`), i.e. ≤ 5 s;
the following refresh also replaces `state["cost"]`, which is in the key. The same 5-second
bound applies to the pre-existing `id(stats)`/`id(oauth)` reuse risk. Bounded, invisible in
practice, and unchanged by this hunk's intent → recommendation R9, not a defect.

## 2. Item (b) — `verify_release_artifact.py` and the font gate

- `verify_release_artifact.py:28`: `verify_release_artifact.py app <app_path>
  --expect-version 0.24 --arches arm64,x86_64` — moved with `APP_VERSION`, as every release
  commit since v0.21 did (Verifier §F1 deviation, now resolved).
- Font gate (`check_app`, lines 121–138): requires `Contents/Resources/fonts/Pretendard-SemiBold.ttf`
  and `…/LICENSE-Pretendard.txt` as regular non-symlink files, then reads 4 bytes and
  rejects unless `b"\x00\x01\x00\x00"` (TrueType); only then delegates to
  `validate_update_app`.
- Tree: `fonts/` holds exactly the two files (both tracked; `git ls-files fonts/`);
  `xxd -l 8 fonts/Pretendard-SemiBold.ttf` → `0001 0000 000e 0080` (TrueType magic);
  licence header `Copyright (c) 2021, Kil Hyung-jin … Reserved Font Name Pretendard` (OFL).
- `setup.py`: `"resources": ["frames", ".claude_pet", "fonts"]` and plist
  `"ATSApplicationFontsPath": "fonts"`. `build_app.sh`: plist line 46 carries the same key;
  `copy_fonts()` (54–68) stages `fonts/` beside the destination, checks both files exist,
  then swaps in; called from `build` (331) and `update` (635). `bundled_font_path()` (99–113)
  resolves `<script dir>/fonts/<file>` first, then `NSBundle.mainBundle().resourcePath()/fonts`.
  **Coherent end to end.**

## 3. Item (c) — `RELEASE_NOTES.md` `**v0.24**` (staged) and the published sections

Python check at 15:24Z on the file bytes:

- Staged section = 3 top-level `- ` bullets, **no nested bullet**, 2 sentences each
  (split on `.`/`。`), **435 characters** after whitespace normalisation (≤ 450).
- No hash, no source path or line number, no test name or count, no magnitude word. The
  only path-like token is `pets/이름/이름/`, a user folder layout, not a source path.
- **Published tail unchanged:** from `**v0.23**` to EOF is 18 516 bytes, byte-equal to the
  same suffix of `git show 81619b3:RELEASE_NOTES.md`, sha256
  `c7ddc40a8a25ce8eefac9867032a6a14f20425c6ae0368db41a86d859c96b562` = the existing pin.
- Claims vs source: bullet 1 (one pill, line 1 session·weekly·model %, line 2 reset,
  API mode today/month + budget) — `roam_summary`/`_summary_segment_runs`; bullet 2
  (value = source colour emerald/amber+≈/coral; label white → 50 % yellow → 85 % red;
  spike ▲ red; ⚠ on token expiry) — `SUMMARY_COLORS`, `summary_value_kind` (`>= 85` bad,
  `>= 50` warn), `SUMMARY_APPROX`, `SUMMARY_SPIKE`, `roam_summary_text`'s `" ⚠"` append on
  `auth_error`; bullet 3 (Pretendard OFL bundled; `pets/<name>/<name>/` recognised;
  Windows trial zip unsigned; nothing for existing users to do) — item (b), `_nested_pet_dir`
  (round-6 review), and the `windows` branch below.

**The Windows sentence.** "Windows용 시험판(claude-pet-win.zip, 서명 없음)이 처음으로 함께
올라갑니다" — is it honest as a release-notes claim?

- The asset exists as a build product of `origin/windows` (fetched read-only at 15:22Z;
  tip `db1dedc`, whose ancestry includes `5c396b9 merge main (release: ClaudePet v0.24)`,
  i.e. HEAD). `windows/build_win.py` writes `release/claude-pet-win.zip` (line 31) and
  `release/claude-pet-win-setup.exe` (32, via `windows/installer.iss`,
  `OutputBaseFilename=claude-pet-win-setup`); its docstring and `installer.iss` line 2 both
  say unsigned.
- It is **not** in the macOS updater's table: `UPDATE_ASSET_NAMES` (`claude_pet.py:2726`)
  lists only `claudepet.zip` / `claudepet-universal.zip`, so no installed Mac copy will ever
  select it (correct — it is not a Mac bundle). `release.sh publish` uploads exactly
  `("$ZIP" "$UZIP" "$DMG" "$UDMG")` (line 543) after `check_assets` requires that set and
  nothing else (`verify_release_artifact.py:171–177`), so the Windows files must be uploaded
  in a **separate** `gh release upload` after `publish`, from the `windows` branch.
- Judgement: the sentence is a claim about **the GitHub release's assets**, and the release
  commit body records that plan verbatim ("windows 브랜치에서 빌드해 같은 릴리즈에 올린다").
  It is honest **conditionally**: it becomes true when the operator's separate upload lands
  on the same `v0.24` release, and it is auditable there (`gh release view v0.24`). Nothing
  in the macOS gate checks or guarantees it. If the Windows upload is skipped or fails, the
  published body is false and correcting it would then be an [ASK] rewrite of a published
  entry. So: **not a defect in the notes; an obligation on the operator's record** (R2).
  Two smaller points: the note names only the zip while the READMEs promise both the zip
  and `claude-pet-win-setup.exe` "with every release" (R3); and "처음으로" is accurate — no
  earlier release carried a Windows asset (`gh release list` per the Verifier's record).

## 4. Item (d) — `docs/`, `preview.png`, and the four READMEs

### 4a. `docs/index.html` (1 512 lines) — machine checks (node v22.22.2, 15:25Z)

- Two `<script>` tags. The `application/ld+json` block **parses** (`JSON.parse`); the
  41 573-character plain script **parses** (`new Function(body)`).
- JSON-LD `SoftwareApplication`: `softwareVersion "0.24"`; `operatingSystem "macOS 12.0 or
  later (Apple Silicon and Intel); Windows 10/11 (beta)"`; `releaseNotes
  …/releases/tag/v0.24`; `downloadUrl …/releases/latest/download/ClaudePet.dmg`;
  `featureList` (7 items) names the single pill with reset countdowns, hourly update checks
  after launch, and the Windows beta (unsigned zip); `dateModified 2026-09-12`.
- **FAQ:** the JSON-LD `FAQPage` (7 Q/A) is **identical, string for string, to
  `I18N.en.faq`** (the array the script renders into `#faq-list`, line 1234). The static
  `<details>` fallback at lines 754–760 lags on Q2 (no Windows sentence) — only visible
  without JavaScript (R6). Q3 and Q5 carry the same answer text in both places (R7).
- Download targets present: `releases/latest/download/ClaudePet.dmg` (nav, hero, pet-hint,
  JSON-LD), `ClaudePet-universal.dmg` (pet-hint, Korean section), `claude-pet-win.zip`
  (hero CTA, pet-hint, install step 4, Korean section, `llms.txt`). `claude-pet-win-setup.exe`
  appears nowhere on the site (R3).
- Pill description and colour rules (`#gauges` section, 684–700): demo values
  `Session 55% · Weekly 10% · Fable 18%` with `.lbl.warn` on Session, `.val` on the numbers;
  CSS `.pill-demo .val{color:#50C878}` = `SUMMARY_COLORS["exact"]`, `.lbl.warn{#FFD60A}` =
  `COL_WARN`, `.lbl.bad{#FF453A}` = `COL_BAD`, base `#F2F2F7` = `TXT_MAIN`, line 2 `#98989F`
  = `TXT_SUB`. Legend `en`/`ko`: value colour = source (emerald / amber with ≈ / coral),
  label colour = remaining (white, 50 % yellow, 85 % red, ▲) — matches `summary_value_kind`.
- Example strings vs `TR`: `reset Session in 59m · Weekly in 6d 20h` ↔ `reset_prefix` `"reset "`,
  `cd_m` `"in {m}m"`, `cd_days` `"in {d}d {h}h"` (en); ko `리셋 세션 59분 후 · 주간 6일 20시간 후`
  ↔ `"리셋 "`, `"{m}분 후"`, `"{d}일 {h}시간 후"`. Both correct.
- Roadmap (`gauges.roadmap`, four locales): "Coming next: the same pill will also show Codex
  usage first, then Gemini, Grok and other AI services" / "추가할 계획이에요" / "次の予定" /
  "Próximamente" — worded as a plan in every locale; the Korean overview paragraph (783)
  likewise "추가할 예정이에요". `roam_summary_runs` is segment-based, so the claim is
  structurally plausible but nothing is shipped — the wording does not say otherwise.
- Update card: "Checks GitHub every hour after launch. Right-click → Check for updates…" ↔
  `UPDATE_CHECK_SEC = 3600` (line 939, "시작 시엔 확인하지 않고") and `menu_check_update`.
- **Defect found — `ja` and `es` i18n not updated for the pill section.** Key-set
  comparison: `en`/`ko` 57 keys; `ja`/`es` 60 keys, the extra three being the old panel keys
  `gauges.reset2`, `gauges.model` ("週間 · Opus" / "Semanal · Opus"), `gauges.reset3`. Worse,
  four keys the new markup **does** bind (`data-i18n` on 693–699) still hold the v0.23 panel
  strings in `ja`/`es` — verified against `git show 92fe4ee:docs/index.html` lines 1029–1035
  and 1114–1120, byte-identical:
  - `gauges.reset1` ja `2時間14分後にリセット` / es `se reinicia en 2h 14m` (old one-line format;
    the app's ja format is `リセット セッション 59分後 · 週間 6日20時間後`);
  - `gauges.remaining` ja `使用量の例` / es `Ejemplo de uso` — rendered as the **first legend
    bullet**, where the colour-source rule should be;
  - `gauges.remaining2` ja `(土) 午後8時にリセット` / es `se reinicia sáb 20:00` — the second
    legend bullet, where the label-colour rule should be;
  - `gauges.autodetect` ja `アカウントで提供される場合` / es `Cuando esté disponible en tu cuenta`.
  A Japanese or Spanish visitor therefore sees three meaningless legend lines and no colour
  rule at all, while `gauges.sub`, `gauges.roadmap`, the feature cards, install steps and
  FAQ in those locales *were* updated. Only `en` and `ko` legends are correct. → **R1.**
- **Stale v0.23 link:** hero pet-hint row, line 638, `<a href="…/releases/tag/v0.23">v0.23
  release notes</a>`. Static (no `data-i18n`); the GitHub fetch block (1423–1439) rewrites
  only `#app-version`, `#arch-support` and the DMG hrefs, never this anchor. The Korean
  section (785) and JSON-LD already say v0.24. → **R4.**
- Other "gauges" occurrences: CSS `.gauge-panel/.gauge-row/…` (404–416) is now unreferenced
  by any markup (R10); section id `#gauges` and i18n key prefix `gauges.*` are internal names;
  the legend's "that gauge" / "per-model gauge" refer to the three measures, as the READMEs
  and `CLAUDE.md` do. No user-facing "gauge panel" wording remains in `en`/`ko`.

### 4b. `docs/llms.txt`, `docs/llms-full.txt`

- `llms.txt`: v0.24, "published 2026-09-12" (forward-dated to the intended release day),
  Windows 10/11 beta unsigned zip, roadmap sentence as a plan, hourly checks after launch,
  Windows beta ZIP link. Consistent with the site.
- `llms-full.txt`: **"Version publication date: 2026-09-11"** — v0.23's date, not updated
  (R5). A mechanical "gauges → usage pill" replacement left two broken sentences: "do not
  promise a fixed number of always-visible usage pill or exact remaining token counts" and
  "usage pill tucks away during movement." (lower-case sentence start) (R5). It mentions
  neither the Windows beta nor the roadmap, unlike `llms.txt` (R5).

### 4c. `preview.png` = `docs/assets/preview.png` (pixel decode, pure Python zlib, 15:26Z)

378×228 RGBA. Opaque bbox x 4–371, y 4–219. Line-1 band y 22–43, colour runs left→right by
loose class (white = all channels > 200; yellow = R>200, G>150, B<120; green = G>140 and
G ≥ R+30 and G ≥ B+30):
`yellow 30–65 · green 74–118 · white 127–130 · white 138–174 · green 181–222 · white 231–234 ·
white 242–295 · green 303–344` — i.e. **label (yellow, session > 50 %) · value (green) · sep ·
label (white) · value (green) · sep · label (white) · value (green)**. Totals in the band:
yellow 283 px, white 664 px, green 933 px, red 0 px. Line 2 (grey `#98989F`-class pixels)
occupies y 44–79. Quantised yellow is `(224,192,32)`, slightly darker than `#FFD60A` (a
colour-profile artefact of the screenshot; the strict ±28 palette match missed it, the loose
class did not). Visual read of the file (Read tool): `세션 55% · 주간 10% · Fable 18%` /
`리셋 세션 59분 후 · 주간 6일 20시간 후`, cat sprite on the right — the Korean pill in Exact
mode (no ≈), the same example values the site's demo uses. The site caption "session label
is yellow because that gauge is past 50 %" is true of the image. **Confirmed the new pill
screenshot; label runs white/yellow, value runs green.**

### 4d. READMEs (`README.md`, `.ko`, `.ja`, `.es`)

- **Windows (beta) sections** — read in full in all four; consistent with each other and
  with `origin/windows:windows/installer.iss`: per-user install
  (`DefaultDirName={localappdata}\Programs\ClaudePet`, `PrivilegesRequired=lowest`), Start
  Menu entry (`{autoprograms}`), Apps & features uninstall entry (`UninstallDisplayName`/`Icon`),
  "Start Claude Pet when I sign in" task (`[Tasks] startup` → `HKCU\…\Run`, `checkedonce`),
  Windows 10/11 64-bit (`MinVersion=10.0`, `x64compatible`), unsigned + SmartScreen "More
  info → Run anyway" (installer.iss line 2). Portable zip → `ClaudePet\ClaudePet.exe`
  (`build_win.py` docstring). Tray icon (`QSystemTrayIcon`, `claude_pet_win.py:1434`);
  "Uninstall completely… removes the settings and logs" (`UNINSTALL_PATHS_WIN` = config,
  lock, debug log, line 89); Exact mode "reads the credential file" — the port calls
  `cp.fetch_exact_usage()` (660), whose `_read_oauth_token` tries
  `~/.claude/.credentials.json` first (2265). All four say "two files are published with
  every release" (zip + setup.exe) — see R3.
- **Pill section** ×4: examples `Session 42% · Weekly 17% · Fable 12%`, `reset Session in
  3h 42m · Weekly in 2d 3h` (ko `3시간 42분 후`, ja `3時間42分後`, es `en 3h 42m`) match
  `cd_hm`/`cd_days` per locale; "weekly shows `-` on a rolling window" ↔ `fmt_countdown`
  returns `"-"` for a `None` reset; colour rules ↔ §1 above; `This month $27.50 / $50` ↔
  `f" / ${budget:.0f}"`. Correct.
- **Controls / menu** ×4: order "Settings / toggle / Roam / Reset size / Pets / Uninstall /
  Quit / Check for updates" matches the builder (6572–6622; Pets inserted at index 4, check
  item last). "Click (⌄ button)" — a button does exist (`BTN_R`, `btnOrigin`, hit-test in
  `mouseUp_` 6550–6556); the line is inherited from v0.23 and only reworded.
- **Inherited inaccuracies, not introduced by this release** (present verbatim in
  `92fe4ee:README.md`): "On launch the app checks the latest GitHub release" (all four
  locales; the source checks one hour after start, never at launch, and `llms.txt` says so
  correctly); the `> 🧪 Currently v0.1 (beta)` banner; the bare `./release.sh` line in
  "Build from source" (now prints usage and exits 1, and is [NEVER]); "instead of gauges" in
  "Claude Code is required". → R8.

## 5. What was **not** done

- No reconstruction of the round-6 bytes; the Verifier's §F1 hunk list was taken as the map
  and every hunk read in HEAD.
- No test run (read-only mandate); the Verifier's clean-tree run is cited.
- `CLAUDE.md`'s pill/fonts sections were not re-reviewed (round 6 covered B4; the gate did
  not reopen them).
- The `windows` branch was read only for `installer.iss`, `build_win.py` and greps of
  `claude_pet_win.py`; its code was not reviewed.

## 6. Findings

### Blocking (would require a new release commit)

**None.** Every defect found lives in `docs/` (the GitHub Pages site) or in inherited README
wording — outside the app bundle, the artifacts, and the updater's contract — and is fixable
by a docs-only commit on top of `a1f3d22…`, exactly as `92fe4ee` followed `81619b3` for
v0.23. The release commit's code, the verifier, the fonts wiring, the staged notes and the
screenshot are correct.

### Non-blocking recommendations (Developer / Coordinator to decide)

1. **`docs/index.html` `ja`/`es` pill legend — fix before `git push origin main`.** Rewrite
   `gauges.reset1`, `gauges.remaining`, `gauges.remaining2`, `gauges.autodetect` for `ja` and
   `es` to the pill wording (mirror `en`/`ko`; the app's ja reset format is
   `リセット セッション 59分後 · 週間 6日20時間後`), and delete the dead keys
   `gauges.reset2`/`gauges.model`/`gauges.reset3`. Pages deploys from `main`, so as committed
   the Japanese and Spanish pages will show three meaningless legend bullets and no colour
   rule the moment `main` is pushed. A docs-only commit after the release commit does not
   disturb the tag.
2. **Operator obligation for the Windows sentence.** The notes promise `claude-pet-win.zip`
   on the v0.24 release; `publish` neither uploads nor checks it. The operator's record
   should show the separate `gh release upload v0.24 claude-pet-win.zip …` and
   `gh release view v0.24` listing it, **before** the release is declared done; if that
   upload cannot happen, stop and say so rather than publish a body that is false.
3. **Decide the Windows asset set and align three documents.** READMEs ×4: zip + setup.exe
   "with every release"; `RELEASE_NOTES.md` and the site/`llms.txt`: zip only. Either upload
   both (and add the installer to the site's Windows step and `llms.txt`), or drop the
   installer from the READMEs' Windows sections for now.
4. **`docs/index.html:638`** — change the static `v0.23 release notes` anchor to v0.24 (or
   have the fetch block rewrite it from `rel.html_url`).
5. **`docs/llms-full.txt`** — set "Version publication date" to the v0.24 date; repair the
   two mangled sentences ("…always-visible usage pill…", "usage pill tucks away…"); add the
   Windows beta and roadmap lines that `llms.txt` already has.
6. Sync the static `<details>` FAQ fallback (lines 754–760) with `I18N.en.faq`/JSON-LD so
   the no-JS view matches the structured data (Q2 lacks the Windows sentence).
7. FAQ Q3 ("How does Claude Pet track…") and Q5 ("Does Claude Pet include web or desktop
   chat usage?") share one answer verbatim in JSON-LD and `en`; give Q3 its own answer.
8. READMEs ×4, inherited: "On launch the app checks…" → hourly after launch; remove or
   update the `v0.1 (beta)` banner; replace the bare `./release.sh` example with
   `./release.sh build`; "instead of gauges" → "in the pill".
9. `roam_summary_text` memo key: add `bool(RUNTIME.get("admin_key"))` for completeness
   (≤ 5 s stale `need_admin_key` after saving a key in API mode; harmless today).
10. Drop the unreferenced `.gauge-panel/.gauge-row/.gauge-*` CSS (404–416).
11. Module docstring `claude_pet.py:5–7` still describes "게이지 3종 … 막대"; refresh to the
    pill when convenient.

## 7. Provenance summary (AGENTS.md §5)

Every number above is a count over a stated set at a stated time: `TR` key counts (AST
literal, 4 locales × 99, 15:21Z); notes length (435 chars, whitespace-normalised bullets,
15:24Z); notes tail (18 516 bytes vs `81619b3`, sha256 `c7ddc40a…`, 15:24Z); i18n key counts
(57/57/60/60 by locale, 15:25Z, `new Function` over the 41 573-char script body); PNG pixel
classes (378×228 RGBA decoded with zlib, band y 22–43: yellow 283 / white 664 / green 933 /
red 0, 15:26Z); hashes (`shasum -a 256`, 15:18Z). No hypothesis is asserted as established
by this Reviewer alone; the one sample-derived statement (screenshot colour-profile artefact)
is labelled as such. Nothing in this record was measured from `~/.claude`.

---

# Round 8 — 2026-09-13 KST (post-publish docs refresh, uncommitted working tree over `3190ce6`)

**Verdict: FAIL — two blocking defects, both inside the new Windows branch of
`applyDownloadLinks()` in `docs/index.html`; everything else the brief asked for checks out.
Both fixes are a few lines in that one function and do not touch the release, the tag, or
the artifacts.**

- **Reviewer:** `reviewer-v024`, round 8. Read-only; the only file edited is this record. No
  `git` write command, no build/release script, no GUI launch, no read of `~/.claude`, no
  write under `~/.claude_pet*`, no untracked file touched (`release/claude-pet-win-setup.exe`
  and `release/claude-pet-win.zip` were only `ls -l`'d). Read-only network: `gh release view
  v0.24`, `gh release list --limit 3`.
- **UTC window:** 2026-09-12T16:14:38Z (first command) → 2026-09-12T16:19Z (record written).
- **Tree under review:** HEAD `3190ce67dd2b5009fd63cbac684946de11ac0247` (`docs: record the
  v0.24 execution gate …`, 2026-09-13T00:47:31+09:00). `git cat-file -t v0.24` → `tag`;
  `git rev-parse v0.24^{commit}` → `3190ce6…`. `gh release list --limit 3`: `v0.24 Latest
  2026-09-12T15:55:00Z` (= 2026-09-13 00:55 KST), not draft, not prerelease, target `main`.
- **Working tree:** `git status --porcelain` shows exactly seven ` M` paths — `README.md`,
  `README.ko.md`, `README.ja.md`, `README.es.md`, `docs/index.html`, `docs/llms-full.txt`,
  `docs/sitemap.xml` — plus `??` entries only (`diag.py`, `release/ClaudePet.iconset/`,
  `release/icon_1024.png`, `release/claude-pet-win-setup.exe`, 20 `docs-design/` captures and
  records). `git diff --numstat`: 1/1 for each of the six text files, 26/15 for
  `docs/index.html`. `git diff --check`: clean.
- **Working-tree hashes at 16:17Z** (`shasum -a 256`): `docs/index.html` `a1f5c389…`;
  `README.md` `9491e0b8…`; `README.ko.md` `008c0b6b…`; `README.ja.md` `8e5a5a1b…`;
  `README.es.md` `72cd72a7…`; `docs/llms-full.txt` `e9bee346…`; `docs/sitemap.xml`
  `a08a4cd6…`. A later fix changes at least the first of these; re-review is against the
  new bytes, not this list.

## 8.1 Hunk map — every hunk belongs to items 1–4

`git diff -U0 -- docs/index.html` yields 15 hunks; the six text files one each. Mapped:

| Hunks | Item |
| --- | --- |
| `index.html` `-6,2`, `-16,2`, `-28,2` (`<title>`, `description`, `og:title`, `og:description`, `twitter:title`, `twitter:description`) | 2 |
| `index.html` `-716` (static install step), `-773` (Korean overview) | 3 |
| `index.html` `-827,0` / `-916,0` / `-1003,0` / `-1090,0` (insert `hero.cta.alt.winzip` en/ko/ja/es) | 1 |
| `index.html` `-887` / `-976` / `-1063` / `-1150` (install-step string, 4 locales) | 3 |
| `index.html` `-1291,3` (`applyDownloadLinks` Windows branch) | 1 |
| `index.html` `-1404,0` (asset scan: `claude-pet-win-setup.exe`, `claude-pet-win.zip`) | 1 |
| `README*.md` ×4 line 55 | 3 |
| `docs/llms-full.txt` line 68 | 3 |
| `docs/sitemap.xml` `<lastmod>` 2026-09-12 → 2026-09-13 | 4 |

Nothing outside items 1–4. `&amp;` escaping in the three `<title>`/`og`/`twitter` titles is
preserved.

## 8.2 Parse checks

- `node -e` over every `<script>` block: block #2 (line 812, the page script, 42 246 chars)
  → `new Function(body)` OK; block #1 (line 32, JSON-LD, 4 944 chars) → `JSON.parse` OK, shape
  `{@context, @graph:[SoftwareApplication, WebSite, FAQPage]}`. Two blocks total, no
  external `src`.

## 8.3 Keys, DL entries, and the macOS paths

- `"hero.cta.alt.winzip"` present in all four `I18N` blocks: lines 828 (en), 918 (ko), 1006
  (ja), 1094 (es). `"hero.cta.windows"` present ×4 (826/916/1004/1092, pre-existing).
- `t["hero.cta.windows"]` is written as a `.dl-main` label at exactly one site, line 1297,
  inside `if(dlArch === "other"){ if(/Windows/.test(navigator.userAgent)){ … } }`. Its only
  other reference is the pre-existing hero ghost button (line 621, `data-i18n`), which is not
  `.dl-main`.
- `DL.win` (line 1280) and `DL.winSetup` (line 1281) exist with the `releases/latest/download/`
  URLs; the fetch callback (1414–1415) compares `a.name.toLowerCase()` against
  `"claude-pet-win-setup.exe"` / `"claude-pet-win.zip"`.
- `applyLang()` (1222–1243) re-applies `data-i18n` (which resets the hero primary to
  `hero.cta.primary`) and **then** calls `applyDownloadLinks()` (1242), so a language switch
  on Windows keeps the Windows label. Initial load: `detectDlArch().then(… applyDownloadLinks())`
  (1370) and again after the release fetch (1420).
- macOS visitors: the `intel` and `arm` branches (1303–1316), `DL.arm`, `DL.universal`, and
  the static hrefs at 608/620/626 are byte-identical to HEAD; the only hunk in the function is
  the `other` branch.

## 8.4 Published assets ↔ links

`gh release view v0.24 --json assets`: `claude-pet-win-setup.exe` 56 012 818 B,
`claude-pet-win.zip` 72 459 838 B, `ClaudePet-universal.dmg` 41 320 380 B,
`ClaudePet-universal.zip` 38 062 587 B, `ClaudePet.dmg` 34 586 302 B, `ClaudePet.zip`
32 120 389 B — six assets. The two Windows names match the `DL` URLs, the fetch-scan
literals, the `pet-hint` links (626), the Korean overview links (773), and the READMEs'
file names exactly (case included). Local `release/claude-pet-win-setup.exe` and
`release/claude-pet-win.zip` have the same byte sizes as the published assets (`ls -l`,
not hashed — sizes only).

## 8.5 Security-dialog wording vs. the Windows session's observation

Observed (per the round-8 brief; no on-disk record of it was found under `docs-design/`):
title `파일 열기 - 보안 경고`, body `게시자를 확인하지 못했습니다`, buttons `실행` / `취소`.

- `README.ko.md:55` and `docs/index.html` 773 / 978 carry the title verbatim — hyphen-minus,
  single spaces — and name the button `실행`. The parenthetical `(알 수 없는 게시자)` is the
  dialog's publisher field, not the observed body sentence; both describe the same dialog and
  neither contradicts the observation.
- No text claims SmartScreen always appears. The site step (716 and ×4), the Korean overview
  (773), and `llms-full.txt:68` say "Windows asks once … SmartScreen (…) **or** the classic
  …". The READMEs ×4 state the SmartScreen prompt first and then "on PCs where SmartScreen's
  app checking is off you get the classic … **instead**" — qualified, acceptable (R6 below
  suggests the tighter phrasing).
- Locale titles: `ja` 「ファイルを開く - セキュリティの警告」 matches Windows' Japanese string;
  `en` uses an en dash (`Open File – Security Warning`, in README, site ×2, llms-full) where
  Windows prints a hyphen; `es` uses a colon (`Abrir archivo: advertencia de seguridad`)
  where Windows prints ` - Advertencia`. Cosmetic → R4.

## 8.6 The four README paragraphs say the same thing

Each locale's line 55 adds the same three propositions and nothing else: (i) the condition
— SmartScreen's app checking is off (`SmartScreen의 앱 검사가 꺼진 PC` / `SmartScreen の
アプリ確認がオフの PC` / `comprobación de aplicaciones de SmartScreen desactivada`); (ii) the
classic dialog by name, "(unknown publisher)", and click **Run** (`실행` / `実行` /
`Ejecutar`); (iii) "either prompt appears once per file" (`어느 쪽이든 파일마다 한 번만` /
`どちらもファイルごとに一度だけ` / `Cualquiera de los dos avisos aparece una vez por
archivo`). The surrounding sentences are unchanged in all four.

## 8.7 Sitemap date

`docs/sitemap.xml` `<lastmod>2026-09-13</lastmod>`; the release's `publishedAt` is
2026-09-12T15:55:00Z = 2026-09-13 00:55 KST. Equal. `llms-full.txt:7` already reads
"Version publication date: 2026-09-13"; `llms.txt:5` still reads "Reference updated:
2026-09-12" (pre-existing, gate note n2) → R3.

## 8.8 Findings

### Blocking (fix before this docs commit is made / `git push origin main`)

**B1 — Windows visitors get two identical hero buttons.** `applyDownloadLinks()` now sets
the hero primary (`.dl-main`, line 620) to `href = DL.winSetup`, text `⬇ Windows beta
(installer)`. The ghost button immediately beside it (line 621) is the pre-existing
`data-i18n="hero.cta.windows"` link whose `href` is the same
`…/releases/latest/download/claude-pet-win-setup.exe` (confirmed by string comparison
against `DL.winSetup`) and whose text `applyLang()` sets to the same key. Result on every
Windows browser: primary and ghost, side by side, same label, same target, with the alt row
underneath pointing at the zip. Certain from the markup; no browser needed. Fix: on the
Windows branch hide the ghost (give it an id and `style.display="none"`, restoring it on the
other branches), or repurpose it as the zip link and drop the alt row — one of the two, not
both.

**B2 — the nav download button loses its markup and its mobile collapse.** `#nav-download`
(line 608) is `<span class="dl-icon">⬇</span><span class="dl-label" data-i18n="nav.download">Download</span>`;
`a.textContent = …` on every `.dl-main` replaces both spans with a bare text node. CSS: `.dl-icon{display:none}`
(498) at desktop and, at `max-width:640px` (502–512), `.dl-label{display:none}`,
`.dl-icon{display:inline-block}`, `.nav-actions .btn{width:38px;height:38px;padding:0;border-radius:50%}`;
`.btn` is `white-space:nowrap` with no overflow rule (283). So on a Windows browser at
≤ 640 px the nav button is a 38 px circle containing the nowrap string `⬇ Windows beta
(installer)`, which overflows it — the icon-only nav from `a90befa` is undone for exactly
the platform this change targets — and at desktop widths the arrow that the CSS hides is
now visible text. Certain from the CSS; the pixel extent of the overflow was not measured
(no browser run). Fix: relabel only `a.querySelector(".dl-label")` (or skip the nav button
and change only its `href`), keep the spans, and keep `applyLang()`'s `aria-label` line as
is. `hero.cta.windows` carries its own `⬇`, so a nav-specific key without the arrow (or the
existing `nav.download`) is the right label for the nav.

### Non-blocking recommendations

1. `hero.cta.alt.windows` (827/917/1005/1093) is now unreferenced in all four locales —
   delete it, or use it for B1's ghost.
2. **"Once per file" is unverified for the classic dialog — a hypothesis, not a finding.**
   The classic `Open File - Security Warning` on an Internet-zone (MOTW) executable
   re-prompts on **every** launch while its "Always ask before opening this file" box stays
   ticked; files Explorer extracts from a downloaded zip inherit the mark, files Inno Setup
   writes do not. If that holds, the sentence is right for the installer route and wrong
   for the portable-zip route (`ClaudePet\ClaudePet.exe`). Not testable from this Mac: ask
   the Windows session to launch the zip's `ClaudePet.exe` twice with app checking off and
   record whether the prompt repeats and whether the checkbox was present. If it repeats,
   reword "once per file" for the classic case in READMEs ×4, the site ×5, `llms-full.txt`.
3. `docs/llms.txt:10` still says only "SmartScreen: More info → Run anyway", and `:5`
   "Reference updated: 2026-09-12" — align both with `llms-full.txt` in the same commit.
4. Dialog-title punctuation for searchability: `en` `Open File - Security Warning`
   (hyphen, as Windows prints it) in README, site ×2 and llms-full; `es` `Abrir archivo -
   Advertencia de seguridad`.
5. `<title>` is now 81 characters ("Claude Pet — Free desktop companion & Claude usage
   monitor for macOS and Windows"); SERPs truncate around 60. Optional trim, e.g. drop
   "Free".
6. READMEs ×4: the first sentence still states the SmartScreen prompt unconditionally
   before the "instead" qualifier; the site's "Windows asks once … SmartScreen (…) or the
   classic (…)" is the tighter form.
7. Note only (pre-existing): Windows visitors see `⬇ Download for macOS` until
   `detectDlArch()` resolves (`dlArch` initialises to `"arm"`, 1286); the swap happens on
   the next tick and again after the release fetch.

## 8.9 What was not done

- No browser run, no layout measurement; B1/B2 are derived from the markup and CSS as
  written (a static simulation over the two `.dl-main` elements and the ghost's `href` was
  run in `node`, output recorded above).
- No Windows verification of the dialog's frequency (recommendation 2 is labelled as a
  hypothesis for that reason).
- No test run: the change is docs-only and touches no test-pinned file
  (`claude_pet.py`, `release.sh`, `verify_release_artifact.py` are not in the diff).

## 8.10 Provenance (AGENTS.md §5)

Counts above are over stated sets at stated times: hunk count 15 (`git diff -U0`, 16:16Z);
script bodies 42 246 / 4 944 chars (`new Function` / `JSON.parse`, 16:14Z); key line numbers
(`grep -n`, 16:14–16:17Z); asset names and sizes (`gh release view v0.24 --json assets`,
16:15Z); local Windows file sizes (`ls -l`, 16:17Z); hashes (`shasum -a 256`, 16:17Z). The
one unverified claim (recommendation 2) is labelled as a hypothesis. Nothing was measured
from `~/.claude`.

---

# Round 9 — 2026-09-13 KST (re-review of the round-8 fixes, uncommitted working tree over `3190ce6`)

**Verdict: FAIL — one blocking defect remains. B2 is fixed. B1 is fixed in the JavaScript
and not in effect: `ghostWin.hidden = true` sets the attribute, but the page's own
`.btn{display:inline-flex}` rule out-cascades the user-agent `[hidden]{display:none}`, so
the ghost button still renders and Windows visitors still see two identical installer
buttons. The fix is one CSS line; everything else the brief asked for checks out.**

- **Reviewer:** `reviewer-v024`, round 9. Read-only; the only file edited is this record. No
  `git` write command, no build/release script, no ClaudePet GUI launch, no read of
  `~/.claude`, no write under `~/.claude_pet*`, no untracked file touched. No network: the
  one browser run was headless Chrome on a *scratchpad copy* of the page with every host
  name mapped to NOTFOUND (`--host-resolver-rules="MAP * ~NOTFOUND"`) and a throwaway
  profile directory, so no request left the machine.
- **UTC window:** 2026-09-12T16:21Z (first command) → 16:37Z (record written).
- **Tree under review:** HEAD `3190ce67dd2b5009fd63cbac684946de11ac0247`. `git status
  --porcelain`: ` M` on `README.md`, `README.ko.md`, `README.ja.md`, `README.es.md`,
  `docs/index.html`, `docs/llms.txt`, `docs/llms-full.txt`, `docs/sitemap.xml`, and this
  record; `??` entries only otherwise. `git diff --check`: clean (exit 0, no output).
- **Working-tree hashes at 16:22:12Z** (`shasum -a 256`): `docs/index.html` `b13d8e9b…`;
  `README.md` `0be50d0e…`; `README.ko.md` `70e27dde…`; `README.ja.md` `071cd3c5…`;
  `README.es.md` `9b27a8c8…`; `docs/llms.txt` `3656f323…`; `docs/llms-full.txt`
  `25fda5c5…`; `docs/sitemap.xml` `a08a4cd6…` (unchanged since round 8). The B1 fix below
  changes at least `docs/index.html`; re-review is against the new bytes.

## 9.1 What changed since round 8 (`git diff -U0`, 16 hunks in `index.html`, one per text file)

| Hunks | Item |
| --- | --- |
| `index.html` `-6,2`, `-16,2`, `-28,2` | `<title>`/`og:title`/`twitter:title` shortened (R5); descriptions reworded |
| `index.html` `-716`, `-773`, `-887`, `-976`, `-1063`, `-1150` | install-step / Korean-overview wording: hyphenated dialog title (R4), "asks once … may repeat for the zip" (R2) |
| `index.html` `-827`, `-916`, `-1003`, `-1090` | `hero.cta.alt.windows` → `hero.cta.alt.winzip` in en/ko/ja/es (R1) |
| `index.html` `-1289,0 +1290,2`, `-1291,3 +1293,13` | `applyDownloadLinks()`: `ghostWin` lookup + un-hide; Windows branch (B1/B2) |
| `index.html` `-1404,0 +1417,2` | release-asset scan adds the two Windows names (round 8, unchanged) |
| `README*.md` ×4 line 55, `llms-full.txt:68` | two-prompt wording (R2, R4, R6) |
| `llms.txt:5`, `:10` | "Reference updated: 2026-09-13"; SmartScreen-or-classic wording (R3) |
| `sitemap.xml` | `<lastmod>2026-09-13</lastmod>` (round 8, unchanged) |

Function-level diff of `applyDownloadLinks()` (HEAD vs working tree, `diff -u` over the
`awk`-extracted function): the only changed lines are the two `ghostWin` lines at the top
and the `dlArch === "other"` branch. The `intel` and `arm` branches are byte-identical to
HEAD. `.dl-main` occurs on exactly two elements (`#nav-download`, line 608; the hero
primary, line 620); the ghost (line 621, `data-i18n="hero.cta.windows"`) is not `.dl-main`
and `#nav-download` carries no `data-i18n` attribute (its inner `.dl-label` span does), so
`a.hasAttribute("data-i18n")` selects the hero primary alone — as the brief states.

## 9.2 Parse and key checks (node v22.22.2, 16:22Z)

- `<script>` blocks: 2, no external `src`. Block #1 (line 32, JSON-LD, 6 232 chars) →
  `JSON.parse` OK, `@graph` = `SoftwareApplication, WebSite, FAQPage`. Block #2 (line 812,
  page script, 42 559 chars) → `new Function(body)` OK.
- `I18N` evaluated: en/ko/ja/es each **52 flat string keys**, key sets identical to `en`
  (missing 0, extra 0), duplicate keys 0 per locale block. (Round 8's "57" counted with a
  different extractor; both agree the four sets are equal.) `hero.cta.alt.winzip` present ×4;
  `hero.cta.alt.windows` present in **none**.
- `grep -rn "hero\.cta\.alt\.windows"` over the working tree: zero hits outside
  `docs-design/` records (this file's round-8 section and the gate record quote the old
  name historically). HEAD still has 5 (4 keys + the old `showAlt` call) — all gone.
- Titles: `<title>`, `og:title`, `twitter:title` are all `Claude Pet — Claude usage monitor
  pet for macOS &amp; Windows` — 61 characters as written, 57 once `&amp;` is decoded. ≤ 65
  (R5 done). The three are identical to one another.
- Static install step (line 716) and `I18N.en` install string (887) are equal after
  HTML-unescaping the former.

## 9.3 Behaviour: headless Chrome on a probe copy (Chrome 152.0.7977.83, 16:31–16:34Z)

Method: `docs/index.html` copied to the scratchpad with a `<script>` appended before
`</body>` that, on `load`, records for each `.dl-main` its `href`, `innerHTML`, span count,
computed `display` and bounding box; the ghost's `hidden` attribute/property, computed
`display` and box; the list of `.hero-ctas .btn` whose computed `display !== "none"`; and
the alt row. Runs: `--headless=new --dump-dom`, UA strings for Windows 10, Linux and Intel
Mac, window sizes 1280×900 and 390×844, all DNS mapped to NOTFOUND.

**Spoof caveat, stated so the next reviewer does not trip on it:** `--user-agent` changes
`navigator.userAgent` only; `navigator.platform` still reads `MacIntel` here, so
`isMacBrowser()` stays true and `detectDlArch()` resolves `"arm"` under every UA on this
Mac. A real Windows browser reports `Win32` and reaches `"other"`. The probe therefore
forces `dlArch = "other"` and calls `applyDownloadLinks()` under the Windows UA string —
which is exactly the state a Windows visitor is in after `detectDlArch()` resolves — and
then calls `applyLang("ko")` and `applyLang("en")` to exercise the language-switch path.

Results, Windows UA, `dlArch = "other"` (identical at 1280 and 390 widths except where noted):

| Element | Observed |
| --- | --- |
| `#nav-download` | `href` → `claude-pet-win-setup.exe`; `innerHTML` still `<span class="dl-icon">⬇</span><span class="dl-label" data-i18n="nav.download">Download</span>` (2 spans); 97×38 at 1280, **38×38 at 390** (the icon-only circle from `a90befa` is intact). **B2 fixed.** |
| hero primary | `href` → `claude-pet-win-setup.exe`; text `⬇ Windows beta (installer)`; 238×52 |
| ghost `a[data-i18n="hero.cta.windows"]` | `hidden` attribute **present**, `.hidden === true` — **and computed `display: flex`, box 238×52** |
| `.hero-ctas .btn` with `display !== none` | **`["⬇ Windows beta (installer)", "⬇ Windows beta (installer)", "View source on GitHub"]` — three, not two** |
| alt row | `display: block`, `href` → `claude-pet-win.zip`, text `Prefer no installer? Download the portable zip (unsigned)` |
| after `applyLang("ko")` | primary `⬇ Windows 베타 (설치 파일)` (re-applied after the `data-i18n` reset — the applyLang → applyDownloadLinks order works); nav spans intact, label `다운로드`; alt `설치 없이 쓰시려면 무설치 zip 다운로드(서명 없음)`; ghost still `hidden` **and still 232×52** |
| after `applyLang("en")` | back to the first row; ghost unchanged |

Other branches, same probe: Linux UA + `"other"` → both `.dl-main` → `releases/latest`,
primary text `⬇ Download for macOS` (untouched), alt `Browse all releases (macOS builds and
the Windows beta)`, ghost `hidden=false` and visible — HEAD behaviour. `"intel"` → mains →
`ClaudePet-universal.dmg`, alt → `ClaudePet.dmg` / `hero.cta.alt.arm`, ghost `hidden=false`.
`"arm"` → mains → `ClaudePet.dmg`, alt → universal / `hero.cta.alt.intel`, ghost
`hidden=false`. The un-hide at the top of the function does restore the attribute on every
non-Windows branch and on language switch, as the brief describes.

**Why the attribute does nothing here.** The `hidden` attribute hides an element only through
the user-agent stylesheet rule `[hidden]{display:none}`. The cascade orders by origin before
specificity, so any author declaration of `display` on the same element wins — and `.btn`
(line 283–287, unchanged from HEAD) declares `display:inline-flex`. The page already
carries the correct pattern for its other `hidden` element — `.ad-section[hidden]{display:none}`
at line 493 — and nothing equivalent exists for `.btn`. Demonstrated in isolation as well
(`mini.html`, same Chrome): `<a class="btn" hidden>` under `.btn{display:inline-flex}`
computes `inline-flex`; the same element with no author `display` rule computes `none`.
(In the page the ghost computes `flex` rather than `inline-flex` because it is a flex item
of `.hero-ctas`; either way it is laid out.) This is engine-independent — it is the
cascade, not a Chrome quirk — and the element also stays in the accessibility tree, since
`hidden` without `display:none` does not remove it.

## 9.4 Wording (R2, R3, R4, R6)

- **Dialog title punctuation (R4):** `Open File - Security Warning` in `README.md:55`,
  `index.html` 716 and 887, `llms.txt:10`, `llms-full.txt:68`; `Abrir archivo - Advertencia
  de seguridad` in `README.es.md:55` and `index.html:1150`; ko/ja titles unchanged and
  hyphenated. No en-dash or colon form remains (`grep "Open File – \|Abrir archivo: "` → 0).
- **Two-prompt wording (R2/R6):** the four READMEs' line 55 each carry the same four
  propositions — SmartScreen first; the classic dialog on PCs with app checking off, click
  Run; with the installer either prompt appears once; with the portable zip the classic
  dialog may repeat until "Always ask before opening this file" is unticked (or the zip is
  Unblocked before extraction). The site install step (716 + I18N ×4) and `llms-full.txt:68`
  say the same with the zip caveat in a parenthesis. They agree.
- Every other "once"-family hit in the READMEs (ko 44/80/82, ja 44/82, es 29/76/80/82) is an
  unrelated sentence (update install, breathing cadence, token read) — checked in context.
- Two summaries say "asks once" scoped to the first run with **no** zip caveat: the Korean
  overview paragraph (`index.html:773`, "처음 실행 때 Windows가 한 번 묻습니다") and
  `llms.txt:10` ("on first run Windows asks once"). True for the first run, silent about later
  ones → R1 below, non-blocking.
- `llms.txt:5` now reads `Reference updated: 2026-09-13` (R3 done); `sitemap.xml`
  `<lastmod>` 2026-09-13.

## 9.5 Findings

### Blocking (fix before this docs commit is made / `git push origin main`)

**B1 (carried from round 8, still open in effect) — Windows visitors still get two identical
hero buttons.** The JavaScript now sets `hidden` on the ghost, but `.btn{display:inline-flex}`
overrides the user-agent `[hidden]{display:none}`, so the ghost is laid out at 238×52 beside
the relabelled primary; the headless run lists three visible `.hero-ctas .btn`, two of them
reading `⬇ Windows beta (installer)` with the same `href`. **Fix (one line of CSS):** add
`.btn[hidden]{display:none}` next to `.ad-section[hidden]{display:none}` (line 493), or a
page-wide `[hidden]{display:none!important}`. No change to `applyDownloadLinks()` is needed;
its un-hide/hide logic is correct once the attribute has effect. **Re-check:** the same
probe must report the ghost at `display:none` / 0×0 and exactly two visible hero buttons
(`⬇ Windows beta (installer)`, `View source on GitHub`) on the Windows branch, and three on
every other branch.

### Non-blocking recommendations

1. `index.html:773` (Korean overview) and `llms.txt:10` say "asks once" without the zip
   caveat; one clause ("무설치 zip은 매번 물을 수 있음" / "the portable zip may re-prompt")
   would align them with the READMEs and the install step. Both are scoped to the first run,
   so they are incomplete rather than wrong.
2. `README.ko.md:55`: "…항상 확인*을 끄거나(또는 zip 속성에서 차단 해제 후 풀기) 전까지" doubles
   the "or" (`-거나` + `또는`) and leaves "끄거나 … 전까지" ungrammatical; "끄기(또는 zip
   속성에서 차단 해제 후 풀기) 전까지" reads cleanly.
3. Pre-existing, not in this diff: `llms.txt:3` still opens "a free macOS desktop companion"
   and the JSON-LD `WebSite.description` still says "a macOS desktop pet" while the
   `SoftwareApplication` entry, `<title>` and `og:description` now name the Windows beta.
   Optional alignment in the same commit.
4. For whoever re-reviews B1: do not rely on `--user-agent` alone to reach the Windows
   branch from a Mac (see the spoof caveat in 9.3); force `dlArch = "other"` or run on a
   Windows browser.

## 9.6 What was not done

- No run on a real Windows browser; the Windows branch was exercised by forcing `dlArch` under
  a Windows UA string in headless Chrome on this Mac. The cascade result does not depend on
  the platform.
- No test run: the diff touches no test-pinned file (`claude_pet.py`, `release.sh`,
  `verify_release_artifact.py` are not in `git status`).
- No `gh`/network call this round; asset names were checked against the round-8 record, not
  re-fetched.

## 9.7 Provenance (AGENTS.md §5)

Counts above are over stated sets at stated times: hunk count 16 (`git diff -U0`, 16:24Z);
script bodies 42 559 / 6 232 chars (`new Function` / `JSON.parse`, 16:22Z); I18N key counts
52 ×4 (node evaluation of the extracted `const I18N`, 16:24Z); title lengths 61/57 (python
over the file, 16:21Z); element boxes and computed styles from headless Chrome 152.0.7977.83
`--dump-dom` at 16:31Z (three UAs, 1280×900) and 16:34Z (Windows UA, 1280×900 and 390×844);
hashes (`shasum -a 256`, 16:22Z). Probe files and per-run outputs are in the session
scratchpad (`probe.html`, `probe2.html`, `mini.html`, `probe-*.out`), not in the repo.
Nothing was measured from `~/.claude`.

---

# Round 10 — 2026-09-12 (UTC) / 2026-09-13 KST — re-review of the B1 fix and the round-9 wording items

**Verdict: PASS — B1 is closed; no blocking finding. Two non-blocking notes (§10.5).**

- **Reviewer:** `reviewer-v024`, round 10 (Claude Code workflow subagent, spawned by the
  Developer session `55c3dee4-…`). Held no other role on this release. Read-only: the only
  file edited is this record (this section appended). No `git` write command, no build or
  release script, no GUI launch, no network call, no read of `~/.claude`, no write under
  `~/.claude_pet*`.
- **UTC window:** 2026-09-12T16:38:37Z (first command) → 16:51:41Z (this section written).
- **cwd:** `/Users/yeongyu/claude-pet`; absolute paths in every command.
- **Tree under review:** HEAD `3190ce67dd2b5009fd63cbac684946de11ac0247` (unchanged since
  round 9). `git status --porcelain`: ` M` on the same nine tracked paths as round 9
  (`README.md`, `README.ko.md`, `README.ja.md`, `README.es.md`, `docs/index.html`,
  `docs/llms.txt`, `docs/llms-full.txt`, `docs/sitemap.xml`, this record); `??` only
  otherwise. **`git diff --check`: clean** (exit 0, no output) at 16:38Z and again at 16:50Z.
- **Working-tree hashes at 16:38:37Z** (`shasum -a 256`). Changed since round 9:
  `docs/index.html` `5d4e5436417166a4deec90c88fba6e27c2f73c2abc8a250c64bce42e3c9efe09`
  (was `b13d8e9b…`); `README.ko.md` `992a3789…` (was `70e27dde…`); `docs/llms.txt`
  `9b65cf1a…` (was `3656f323…`). Byte-identical to round 9: `README.md` `0be50d0e…`,
  `README.ja.md` `071cd3c5…`, `README.es.md` `9b27a8c8…`, `docs/llms-full.txt` `25fda5c5…`,
  `docs/sitemap.xml` `a08a4cd6…`.

## 10.1 What changed since round 9 (`git diff -U0 HEAD`, 16:51Z)

`docs/index.html` now carries **18 hunks** against HEAD (round 9 counted 16). The three new
ones, all outside the page script (which starts at line 813):

| Hunk | Change |
| --- | --- |
| `-95 +95` | JSON-LD `WebSite.description`: "a macOS desktop pet…" → "a free desktop pet for macOS (with a Windows beta) that shows Claude usage in one small pill." (round-9 R3) |
| `-493,0 +494` | **`.btn[hidden]{display:none}`** added directly under `.ad-section[hidden]{display:none}`, with a Korean comment stating why (the B1 fix, exactly as recommended) |
| `-773 +774` | Korean overview paragraph: "처음 실행 때 SmartScreen 안내가 뜨면…" → the two-dialog wording with "설치 파일은 한 번, 무설치 zip은 … 끄기 전까지 매번 물을 수 있어요" (round-9 R1) |

Every other hunk is the round-9 hunk shifted down one line; `applyDownloadLinks()`
(lines 1285–1321) is unchanged from round 9 — `ghostWin` lookup, unconditional un-hide,
Windows branch sets `hidden = true`. `README.ko.md` and `docs/llms.txt`: 4 hunks between
them — `README.ko.md:55` (one line), `llms.txt:3`, `:5`, `:10`; `:5` and `:10` are the
round-9 bytes, `:3` is new (R3).

## 10.2 Parse and key checks (node v22.22.2, 16:39Z; `r10-parse.js` in the scratchpad)

- `<script>` blocks: 2, no external `src`. Block #1 (line 32, JSON-LD, 6 269 chars) →
  `JSON.parse` OK; `@graph` = `SoftwareApplication, WebSite, FAQPage`;
  `WebSite.description` as quoted above; `SoftwareApplication.description` and
  `.operatingSystem` unchanged and already name Windows. Block #2 (line 813, page script,
  **42 559 chars — the round-9 length**) → `new Function(body)` OK; consistent with the hunk
  map, which puts no change inside the script since round 9.
- `I18N` evaluated: en/ko/ja/es each **57 keys** by this extractor (round 8's figure; round
  9's extractor counted 52 — both agree the four sets are equal), missing 0 / extra 0 vs
  `en`. `hero.cta.alt.winzip` present ×4; `hero.cta.alt.windows` present in none; `grep -rn`
  over `*.html *.md *.txt *.py` outside `docs-design/` → 0 hits.

## 10.3 Behaviour: headless Chrome on a probe copy (Chrome 152.0.7977.83, 16:40–16:46Z)

**Method — the round-9 method, re-run on the new bytes.** `docs/index.html` copied to the
scratchpad as `r10-probe.html` (`shasum` of the copy **before** the probe was appended =
`5d4e5436…`, i.e. the working-tree bytes), then a `<script>` appended before `</body>` that
records, per snapshot: for each `.dl-main` its `href`, `innerHTML`, span count, computed
`display` and box; the ghost's `hidden` attribute and property, computed `display`,
`visibility`, box and `offsetParent === null`; every `.hero-ctas .btn` whose computed
`display !== "none"` (text → href) plus the total count; and the alt row. Snapshots, in
order: `initial`; `applyLang("ko")`; `applyLang("en")` + `dlArch = "other"` +
`applyDownloadLinks()`; `applyLang("ko")`; `applyLang("ja")`; `applyLang("en")`;
`dlArch = "intel"`; `dlArch = "arm"`; `dlArch = "other"` again. Chrome flags:
`--headless=new --disable-gpu --disable-extensions --host-resolver-rules="MAP * ~NOTFOUND"
--virtual-time-budget=8000 --dump-dom`, a fresh `--user-data-dir` per run. Four runs:
Windows 10 UA at `--window-size=1280,900` and `390,844`, Linux UA at 1280×900, Intel-Mac UA
at 1280×900. Each dump is complete (117 KB, 9 PROBE records, no `PROBE ERR`).

Two operational notes. Chrome did not exit after the dump (it spawns Google Updater
children; round 9's `.err` files show the same), so the runner scripts timed out after the
dumps had landed and the four Chrome trees were killed by their `r10-chrome-*`
`--user-data-dir` names — no run was repeated. And `--window-size=390,844` produces
`innerWidth` **500** (Chrome's minimum window width on this Mac), so that run exercises the
`≤640px` media block but not `≤420`/`≤340`; those are covered statically below.

**Spoof caveat (unchanged from round 9):** `navigator.platform` reads `MacIntel` under every
UA string, so `detectDlArch()` resolves `"arm"` on load; the Windows branch is reached by
forcing `dlArch = "other"` under the Windows UA, which is the state a real Windows visitor is
in after `detectDlArch()` returns `"other"`.

**Results — Windows UA, `dlArch = "other"`** (identical at both widths except the nav box):

| Element | Observed |
| --- | --- |
| `#nav-download` | `href` → `claude-pet-win-setup.exe`; **2 spans** kept (`dl-icon`, `dl-label` `data-i18n="nav.download"`); 97×38 at 1280, **38×38** at the 500-px run (icon-only circle intact); label `Download` / `다운로드` / `ダウンロード` after the language switches |
| hero primary (`.dl-main[data-i18n]`) | `href` → `claude-pet-win-setup.exe`; text `⬇ Windows beta (installer)` (238×52) / `⬇ Windows 베타 (설치 파일)` (232×52) / `⬇ Windows ベータ (インストーラー)` (301×52) |
| ghost `a[data-i18n="hero.cta.windows"]` | `hidden` attribute **present**, `.hidden === true`, computed **`display: none`**, box **0×0**, `offsetParent === null` — in every Windows-branch snapshot: `forced-other`, after `applyLang("ko")`, `("ja")`, `("en")`, and `forced-other-again` |
| `.hero-ctas .btn` with `display !== none` | **exactly two of three**: `⬇ Windows beta (installer) → …/claude-pet-win-setup.exe`, `View source on GitHub → …/claude-pet` (ko: `⬇ Windows 베타 (설치 파일)`, `GitHub에서 소스 보기`; ja: `⬇ Windows ベータ (インストーラー)`, `GitHub でソースを見る`) |
| alt row | `display: block`, `href` → `claude-pet-win.zip`, text `hero.cta.alt.winzip` in each language (`Prefer no installer? Download the portable zip (unsigned)` / `설치 없이 쓰시려면 무설치 zip 다운로드(서명 없음)` / `インストール不要なら ポータブル zip をダウンロード（未署名）`) |

This is the re-check round 9 asked for — ghost at `display:none` / 0×0 and exactly two
visible hero buttons on the Windows branch. **B1 is closed.** The Developer's reported probe
(`["⬇ Windows 베타 (설치 파일) → …/claude-pet-win-setup.exe", "GitHub에서 소스 보기"]`, ghost
`none`, nav 2 spans, alt = zip) is reproduced first-hand.

**Other branches — three visible buttons, ghost visible** (`hidden` attribute absent,
`.hidden === false`, computed `display: flex`, 238×52 en / 232×52 ko / 301×52 ja):

- **non-Windows `"other"`** (Linux UA and Intel-Mac UA): both `.dl-main` → `releases/latest`;
  primary `⬇ Download for macOS`; ghost visible → `claude-pet-win-setup.exe`; alt →
  `releases/latest`, `Browse all releases (macOS builds and the Windows beta)` (ko `전체
  릴리즈 보기 (macOS 빌드와 Windows 베타)`, ja `リリース一覧を見る（macOS ビルドと Windows
  ベータ）`). HEAD behaviour, unchanged.
- **`"intel"`**: mains → `ClaudePet-universal.dmg`; alt → `ClaudePet.dmg`, `Apple Silicon?
  Download the smaller Apple Silicon build`; ghost visible.
- **`"arm"`**: mains → `ClaudePet.dmg`; alt → `ClaudePet-universal.dmg`, `Intel Mac? Download
  the universal build`; ghost visible.
- Returning to `"other"` under the Windows UA after `"arm"` re-hides the ghost (attribute
  back, `display: none`): the un-hide at the top of the function and the hide in the
  Windows branch both take effect on every call now that the CSS honours the attribute.

**Probe artifact, not a finding.** Under the Windows UA, the `forced-intel` / `forced-arm`
snapshots show the hero primary still reading `⬇ Windows beta (installer)` (its `href`
correctly → the dmg) beside the now-visible ghost with the same label. That is the probe
switching `dlArch` without passing through `applyLang()`: only the Windows branch writes the
primary's text, and nothing in `applyDownloadLinks()` restores it. A real page load resolves
`dlArch` once (`detectDlArch().then(… applyDownloadLinks())`) and never moves from `"other"`
to `"intel"`/`"arm"` within a load, and every language switch goes through `applyLang()`,
which rewrites every `[data-i18n]` element's `innerHTML` **before** calling
`applyDownloadLinks()` (lines 1219–1242). The Linux and Intel-Mac runs, which never enter the
Windows branch, show the intel/arm branches with three distinctly labelled buttons.

**Cascade check for the new rule at widths the probe could not reach** (static, over
`<style>` lines 171–534): `.btn[hidden]{display:none}` at line 494 is the last `display`
declaration that can match a hero button. The only later `display` rules naming `.btn` are
`.nav-actions .btn-ghost{display:none}` (line 504, `≤640px`, nav only) and the
`.dl-label`/`.dl-icon` span rules (509–510); the `≤420px` block sets sizes and font only, the
`≤340px` block hides `.brand-name` only. `.hero-ctas .btn` (line 330, the same (0,2,0)
specificity) declares padding and font-size, no `display`. So no author rule at any width
out-cascades the new one, and the 500-px run (`≤640px` block active) confirms the icon-only
nav circle coexists with it.

## 10.4 Wording — round-9 R1, R2, R3

- **R1 done.** `index.html:774` (Korean overview) now: "둘 다 서명이 없어 처음 실행 때 Windows가
  묻습니다: SmartScreen이면 "추가 정보 → 실행", "파일 열기 - 보안 경고"면 "실행"을 누르세요(설치 파일은
  한 번, 무설치 zip은 "이 파일을 열기 전에 항상 확인"을 끄기 전까지 매번 물을 수 있어요)." — the same
  four propositions as the READMEs' line 55 (SmartScreen; the classic dialog; installer once;
  zip may repeat until the checkbox is unticked); the hyphenated ko title matches
  `README.ko.md:55` and the `I18N.ko` install string (line 977). `llms.txt:10` now ends
  "…the installer asks once, the portable zip may re-prompt until "Always ask before opening
  this file" is unticked" — same propositions, same hyphenated title.
- **R2 done.** `README.ko.md:55` reads "…*이 파일을 열기 전에 항상 확인*을 끄기(또는 zip 속성에서 차단
  해제 후 풀기) 전까지 실행할 때마다 물을 수 있으며…" — the doubled `-거나`/`또는` is gone and
  "끄기 … 전까지" parses. It is the only changed line in the file; the other three READMEs'
  line 55 are the round-9 bytes (hashes above) and still carry the four propositions.
- **R3 done.** `llms.txt:3` opens "a free desktop companion and Claude usage monitor for macOS
  (with a Windows beta)"; JSON-LD `WebSite.description` names the Windows beta (§10.2).
  `<title>`, `og:*`, `twitter:*` and `<meta name="description">` are the round-9 bytes and
  already name Windows.
- `llms.txt:5` "Reference updated: 2026-09-13" and `sitemap.xml` `<lastmod>2026-09-13` —
  unchanged, still consistent with each other.

## 10.5 Findings

### Blocking

None. B1 (rounds 8–9) is closed by `.btn[hidden]{display:none}`; the Windows branch now
renders two hero buttons, and every other branch three, first-hand (§10.3).

### Non-blocking

1. **Optional, pre-existing, same class as round-9 R3:** the static `<p class="hero-sub">` at
   `index.html:619` still reads "A free, source-available desktop pet for macOS." with no
   Windows mention, while the four `I18N` `hero.sub` strings (lines 825/914/1001/1088) say
   "with a Windows beta" and replace it in `applyLang()` on load. Only a no-JS reader ever
   sees the static sentence. Align it if the file is touched again; not worth a commit on its
   own.
2. **For the next reviewer, method notes:** (a) Chrome 152 `--headless=new --dump-dom` does
   not exit here because of its updater children — the dump is complete once the `.out` file
   stops growing (~117 KB), and the tree can be killed by `--user-data-dir` name; (b)
   `--window-size` cannot take `innerWidth` below 500, so the `≤420px`/`≤340px` blocks need a
   static read or device emulation, not a narrower window.

## 10.6 What was not done

- No real Windows browser (as in rounds 8–9); the fix is a cascade rule, and the cascade
  result does not depend on the platform.
- No test run: the diff touches no test-pinned file (`claude_pet.py`, `release.sh`,
  `verify_release_artifact.py` are not in `git status`).
- No `gh`/network call; the asset names were checked against the round-8 record, not
  re-fetched.

## 10.7 Provenance (AGENTS.md §5)

Counts above are over stated sets at stated times: hunk counts 18 / 4 (`git diff -U0 HEAD`,
16:51Z); script bodies 6 269 / 42 559 chars and I18N 57 ×4 (`r10-parse.js`, node v22.22.2,
16:39Z); PROBE records 9 per run × 4 runs, element boxes and computed styles from headless
Chrome 152.0.7977.83 `--dump-dom` — `.out` mtimes 16:40Z (Windows 1280×900), 16:42Z
(Windows 390×844 → innerWidth 500), 16:44Z (Linux), 16:46Z (Intel Mac); hashes (`shasum -a
256`, 16:38:37Z). Probe files and per-run outputs are in the session scratchpad
(`r10-probe.html`, `r10-snippet.html`, `r10-run.sh`, `r10-parse.js`, `r10-summ.py`,
`r10-summary.txt`, `r10-<run>.out` / `.err`), not in the repo. Nothing was measured from
`~/.claude`.
