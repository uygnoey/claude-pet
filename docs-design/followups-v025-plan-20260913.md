# v0.25 follow-ups — plan (2026-09-13)

User directive (verbatim, 2026-09-13): "남은 후속 작업 … 이것들도 수정하고" — the five
items I had listed after v0.24: Windows code signing, Windows in-app update and uninstall
cleanup, an in-app "start at sign-in" setting on both platforms, Codex/Gemini/Grok usage
segments, and the stale-OAuth-token bug. Survey reports (read-only, four readers) are in the
session scratchpad as `followups-survey.json`; the decisions below are taken from them.

Process: AGENTS.md roles. Per track the **Verifier** writes the gating tests first and
records them RED, the **Developer** lands production code until GREEN without touching
gating assertions, the Verifier records GREEN from a full-suite run, and an independent
**Reviewer** passes the track. Nothing is committed by agents; the Coordinator (this
session) stages by named paths. Windows hardware verification runs through the Remote
Control peer session on the user's Windows 11 machine after the code lands.

## Track A — stale OAuth token (claude_pet.py, both platforms)

Bug: `_oauth_token_cache["tok"]` is served unconditionally once set; only a 401/403 forces a
re-read, and even then the dead token is never cleared. Non-auth failures (5xx, 429, network,
JSON) leave the token and the 180 s gauge cache untouched, so a rotated token or a transport
blip parks the pill in amber estimate mode until restart.

Design (survey option B + the 401 clearing, plus a bounded version of option C):

- `_oauth_token_cache` gains `src` (`file|cli|native|None`), `file_sig`
  (`(st_mtime_ns, st_size, st_ino)` of the credentials file when `src == "file"`), and
  `suspect` (bool). New helpers `_credentials_path()` and `_credentials_sig()`.
- `_read_oauth_token()` with a cached token: if `src == "file"` and the signature changed or
  the file vanished → drop the cached token and read afresh. If `suspect` → re-validate
  through **prompt-free** sources only (file, then the `security` CLI when the token came
  from cli); the native Keychain path is never entered by automatic re-validation. A
  replacement token replaces the cache; none found keeps the cached token. `suspect`
  clears either way.
- `_fetch_oauth_usage()`: success → `suspect = False`, `auth_error = False`. 401/403 with no
  replacement after the forced walk → clear `tok`, `auth_error = True`. Every other failure
  (HTTPError ≠ 401/403, URLError/timeout, JSON/parse) → `suspect = True`, and
  `OAUTH_STATUS["last_error"]` records the class (`"http:<code>"`, `"net"`, `"parse"`).
  `_dbg` lines carry status codes and booleans only — never token bytes.
- `fetch_exact_usage()`: a failed fetch is cached for `OAUTH_FAIL_RETRY_SEC = 60` instead of
  180, **except** `http:429`, which keeps the full `OAUTH_CACHE_SEC` (the inline comment
  "과호출 시 429 → 3분 캐시 필수" is why the cache exists).
- Nothing new is rendered on the pill; the `roam_summary_text` memo key is unchanged.
- Windows inherits everything (the port reuses these functions; the file is its only source).

Gating tests: `tests/test_oauth_token_cache.py`, synthetic (HOME patched to a temp dir, CLI
and native readers patched, `urlopen` patched). Rotation picked up without restart;
non-auth failure re-validates prompt-free only; 401 without replacement stops serving the
dead token; 429 keeps 180 s while 5xx/net retry in 60 s; success clears `suspect`.

## Track B — "Start at sign-in" (both platforms, identical UX)

- A checkable right-click menu item `menu_autostart` right after "Roam the screen", on
  both platforms. OS state is the source of truth; **no config key** is persisted (a user
  who turns it off in System Settings / Task Manager must see it off).
- macOS: `SMAppService.mainAppService()` (ServiceManagement is importable in this PyObjC).
  `status()` → checkmark; `registerAndReturnError_` / `unregisterAndReturnError_` on click;
  `RequiresApproval` → alert `autostart_approval` with a button that calls
  `SMAppService.openSystemSettingsLoginItems()`. Gated on `app_bundle_path()`: from source,
  or on macOS 12 (no SMAppService), the item is shown disabled (`autostart_unavailable`).
  `do_uninstall()` unregisters before its irreversible section. `setup.py` includes
  `ServiceManagement`. Pure helpers (`autostart_state(status, is_bundle)` and the toggle
  decision) take the service object as a parameter so tests never register anything.
- Windows: `winreg` on `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value
  `ClaudePet` = `"<sys.executable>"` — the same name and quoting the installer writes, so the
  installer checkbox, the in-app toggle and `uninsdeletevalue` share one value. State =
  value present ∧ path equals `sys.executable` ∧ `StartupApproved\Run\ClaudePet` not
  disabled (encoding to be confirmed on hardware). From source (not `sys.frozen`) the item
  is disabled, as on macOS. The Windows uninstall path deletes the value.
- TR keys (en/ko/ja/es): `menu_autostart`, `autostart_title`, `autostart_approval`,
  `autostart_open_settings`, `autostart_fail`, `autostart_unavailable`.
- Docs follow-up after both halves land: README*.md and the site's spec table currently
  point to System Settings / the installer option.

Track B (macOS half) runs in the `autostart` worktree (`/Users/yeongyu/claude-pet-autostart`)
in parallel with Track A and is merged into main afterwards; the Windows half runs on the
`windows` branch once main is merged there (it needs the TR keys from `claude_pet.py`).

## Track C/D — Windows in-app update, uninstall cleanup, signing scaffold (`windows` branch)

- `install_kind()` → `inno` when `unins000.exe` sits beside `sys.executable` and the Inno
  `InstallLocation` registry value equals the exe directory; otherwise `portable`.
- Windows asset table keyed machine × kind (`AMD64` only is published; `ARM64` → explicit
  "no asset" status). `check_github_update_win` reuses `cp._ver_tuple`, keeps `size` and
  `digest` from the release JSON, records the choice; polls hourly with the macOS semantics
  (never at launch; first check one interval after start).
- Update, Inno kind: download `claude-pet-win-setup.exe` to
  `%LOCALAPPDATA%\me.yeongyu.claudepet\`, verify size + `sha256:` digest (a missing or
  malformed digest **refuses**), run
  `/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /LOG=…`.
  The app registers `RegisterApplicationRestart` and holds a single-instance mutex.
- Update, portable kind: download `claude-pet-win.zip`, verify size + digest, scan with
  `cp._zip_members_are_safe`, extract to a sibling staging dir, validate the layout (exactly
  one root `ClaudePet/`, `ClaudePet.exe`, `_internal/`, `_internal/claudepet-release.json`
  whose version equals the tag), then hand over to a generated PowerShell helper that waits
  for the process to exit, swaps the folders (old kept as `.claudepet-old-<tag>` until the
  new one launches), and relaunches.
- `build_win.py` writes `_internal/claudepet-release.json` before packaging, gains a
  signing step selected by `CLAUDE_PET_WIN_SIGN=off|pfx|store|trusted` (signtool; `off` is
  the default until the user holds a certificate — **no agent can obtain or use one**), and
  runs a new `windows/verify_win_artifact.py` gate over the zip and the installer.
- `installer.iss`: scope `[UninstallDelete]` to what the installer put there plus the
  `{localappdata}\me.yeongyu.claudepet` cache; `%USERPROFILE%\.claude_pet` stays (parity with
  macOS). In-app "Uninstall completely…" mirrors macOS's `UNINSTALL_PATHS` and then runs the
  Inno uninstaller silently (Inno kind) or a helper that removes the app folder after exit
  (portable kind).
- Gating tests on macOS: pure parts only (asset selection, check shape with the network
  stubbed, size/digest verification, zip layout validation, helper generation, kind
  detection with temp dirs and an injected registry reader).

## Track E — Codex, Gemini, Grok segments (after A and B merge)

- Contract: `ProviderUsage` = `{"provider", "kind": "exact"|"estimate", "rows":
  [(label, pct, reset_dt|None)], "as_of", "stale", "error"}`; per provider two pure
  functions `discover_<p>(home=None)` and `read_<p>_usage(now, home=None)`; a pure
  `provider_segment(usage, now)` produces the `(kind, [(label, pct, False, reset_text)])`
  segment the pill already understands. Value colour keeps its v0.24 meaning (emerald =
  server-computed, amber ≈ = local estimate).
- Layout: provider rows go on a **third pill line** (`SUMMARY_H3`), their reset countdowns
  are appended to the reset line after Claude's (trimmed from the end if too long).
  `RoamDisplay`/`roam_frame`/renderer on both platforms grow accordingly.
- Codex (first): newest `token_count.rate_limits` snapshot from
  `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (both `primary` and `secondary`; label from
  `window_minutes`; drop rows whose `resets_at` passed; `limit_id == "premium"` ignored);
  exact. Grok (second): newest `billing: fetched credits config` line in
  `~/.grok/logs/unified.jsonl` (`creditUsagePercent`, `currentPeriod.end`); exact. Gemini
  (third): no local quota record exists, so an **estimate** — requests today counted from
  `~/.gemini/tmp/*/chats/*.jsonl` against a configurable daily limit (default 1000, the
  documented free-tier figure), amber ≈, reset `-`. **No network calls** to any provider.
- Discovered providers show by default; a right-click checkbox per discovered provider
  hides it (`RUNTIME["providers"]`, persisted).
- Privacy: parsers read only the fields above; tests assert that sentinel session ids,
  paths and message text never reach the result.

## Release

All tracks ship together as v0.25 under the usual gate; the release notes entry is written
at release time (three bullets, ≤ 450 chars). Windows assets are rebuilt on the Windows
machine and verified there before upload.
