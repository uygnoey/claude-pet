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
