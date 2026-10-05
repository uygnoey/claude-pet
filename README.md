# 🐱 Claude Pet

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Español](README.es.md)

A desktop pet that floats on your screen and watches your Claude Code or Codex usage, à la Codex Pets.
Rendered natively on macOS (AppKit) — no window frame, no background, no ghosting.

> 🧪 v0.24 — the macOS app is notarized; the Windows build ships as an installer and a zip (unsigned — see the Windows section).

![Claude Pet](preview.png)

## Supported platforms

|  | macOS | Windows |
| --- | --- | --- |
| OS | macOS 12 or later | Windows 10/11 (64-bit) |
| Chip | Apple Silicon and Intel (universal build) | x64 |
| Download | `ClaudePet.dmg` (Apple Silicon) · `ClaudePet-universal.dmg` (Intel) | `claude-pet-win-setup.exe` (installer) · `claude-pet-win.zip` (portable) |
| Signing | Developer ID signed, notarized by Apple | Unsigned — Windows asks once before the first run |
| Updates | In-app: checks every hour, installs from the right-click menu | In-app: checks every hour, installs from the right-click menu (installer or portable zip) |
| Start at sign-in | Right-click menu → “Start at sign-in” (macOS 13+; on macOS 12, System Preferences → Users & Groups → Login Items) | Right-click menu → “Start at sign-in” (also an installer option) |
| Claude Code | Reads the Claude Code credential (Keychain or credentials file) | Reads the Claude Code credentials file |
| Pets | Built-in cat + 4 bundled pets, plus your own in `~/.claude_pet/pets` | Same, under `%USERPROFILE%\.claude_pet\pets` |
| Uninstall | Right-click → Uninstall completely… | Settings → Apps → Uninstall |

## Download & Install (recommended)

**No Python needed** — it's bundled inside the app, which is **notarized by Apple**, so it opens with no Gatekeeper warning.

1. Download `ClaudePet.zip` from [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest) — on an **Intel Mac**, grab `ClaudePet-universal.zip` instead (available from v0.10)
2. Unzip → move `ClaudePet.app` to your **Applications** folder → double-click
3. macOS 12+ (Apple Silicon; Intel from v0.10 via the universal zip)

### Permissions (first launch)

The pet only reads **`~/.claude` (Claude Code logs, for spike alerts) and the OAuth token in your Keychain** — plus, if you use Codex, `~/.codex` (its sign-in file and session logs, also for spike alerts). It never touches other folders (Photos, Downloads, Documents, …). On first launch you'll see only these:

| Prompt | What | Choose |
|---|---|---|
| **Keychain** — "Claude Code-credentials" | OAuth token so the pet can fetch the server-computed % | **Always Allow** |
| **"data from other apps"** — `~/.claude` | reading logs for spike alerts (numbers only, on this computer) | **Allow** |

- The token is read **once per launch**, and because the app is signed the decision is remembered — you won't be asked again.
- **No Photos / Downloads / Music / Desktop / Documents / iCloud / Network-volume prompts appear.** (They used to, because the pet spawned the `claude` CLI as a child and its home scan was attributed to the app — that CLI call is now OFF by default.)
  - To supplement the per-model (Fable) row via the CLI, set `CLAUDE_PET_USE_CLI=1` — but then the folder prompts come back.

### Claude Code is required

The pet is a HUD for **Claude Code or Codex usage** — the numbers come from each tool's own sign-in (the server's %), and their local logs only feed spike alerts. So **subscription mode requires Claude Code or Codex to be installed and signed in.**

- If Claude Code isn't installed, the pet shows **"Claude Code not installed"** instead of the pill. **Right-click → "⬇︎ Install Claude Code…"** runs the official installer ([`claude.ai/install.sh`](https://claude.ai/install.sh)) in Terminal, then signs you in.
- If it's installed but not logged in, **right-click → "🔑 Sign in to Claude Code…"** starts the login.
- The Claude Code item is decided by the sign-in token, not the logs: no token → the item appears, even if there are recent logs.
- Codex works the same way, but only if you use Codex on this computer (the `codex` CLI or a `~/.codex` folder exists — otherwise nothing is added): while Codex is shown in the pill but not signed in, **right-click → "⬇︎ Install Codex…"** (`npm install -g @openai/codex`, then `codex login`, in Terminal) or **"🔑 Sign in to Codex…"** (`codex login`). On Windows these open a new PowerShell console.
- Once done, usage appears on the next refresh — no restart needed.
- Note: **API mode** (right-click → Settings → Admin API key; for Codex an OpenAI Admin API key) works without signing in.

### Updates

Every hour after launch (never at launch) the app checks the latest GitHub release; if a newer version exists, **right-click → "⬆︎ Install new version"** downloads, replaces, and relaunches automatically. **Right-click → "⬆︎ Check for updates…"** checks right now and installs straight to the latest version.

---

## Windows

Windows 10/11 (64-bit) gets the same pill, roaming, settings and pets. Two files are published with every release:

- **`claude-pet-win-setup.exe`** — installer. Installs for the current user (no admin rights), adds a Start Menu entry and an "Apps & features" uninstall entry, and offers **Start Claude Pet when I sign in**.
- **`claude-pet-win.zip`** — portable/update build. Unzip anywhere and run `ClaudePet\ClaudePet.exe`.

**About the SmartScreen warning.** The Windows build is not code-signed yet, so the first time you run the installer or `ClaudePet.exe`, Windows shows *"Windows protected your PC"*. Click **More info**, then **Run anyway**. On PCs where SmartScreen's app checking is off you get the classic *"Open File - Security Warning"* (Unknown publisher) instead — click **Run**. With the installer either prompt appears once; with the portable zip the classic dialog may return on every launch until you untick *Always ask before opening this file* (or Unblock the zip in its Properties before extracting); it is Windows' notice that the publisher is unknown, not a detection of anything harmful. If your browser or Edge flags the download the same way, choose **Keep** → **Keep anyway**. Code signing will remove the warning in a later release.

Sign in to Claude Code or Codex on Windows first (`claude` / `codex login`), then launch Claude Pet: the usage numbers come from the credential file under `%USERPROFILE%\.claude` (or `%USERPROFILE%\.codex`), and the logs there are read only for spike alerts. Your own pets go in `%USERPROFILE%\.claude_pet\pets\<name>\` (right-click → Pets → Add a pet… opens it). The tray icon sits in the taskbar overflow (`^`) by default; drag it out to keep it visible. Right-click → Uninstall completely… removes the settings and logs; the installer's uninstaller (Apps & features) removes the program.

## Build from source (developers)

To build from source you need a **framework build of Python**:

- **Homebrew**: `brew install python@3.13` (already a framework build)
- **pyenv**: install with `--enable-framework`
  ```bash
  PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.13.14 && pyenv global 3.13.14
  ```
  > ⚠️ Don't use the system Python (`/usr/bin/python3`, 3.9) — pyobjc fails to build there.

```bash
./build_app.sh install     # local build+sign → install to /Applications and run
python3 claude_pet.py --report   # terminal report only, no GUI

./release.sh build         # distributable self-contained app (py2app); sign / notarize / universal / dmg / publish are separate subcommands
```
`release.sh` needs notarization credentials stored once (see the comment at the top of the script).

## Behavior

- **Idle by default** — first frame frozen; a breath/blink only once every 25s
- **When the mouse comes close** — waves hello (30s cooldown)
- **Roams on its own now and then** — rests in place; when the mouse is moving it walks over once and watches
  for a moment, otherwise it picks a random spot anywhere on the screen, walks there and rests where it arrives
  (it does not come back). It never walks onto the cursor and stops where it is if you grab it or open the menu or Settings
- **Sometimes follows the mouse** for 10–20 seconds, slowly and at a distance, then looks at you and rests where it stopped.
  **With more than one monitor it hops between them** now and then: a little jump, a fade, and it lands on a safe spot of the other screen
- **Folds the pill while walking** so only the pet moves. On arrival it shows the usage pill for a moment even if you
  keep it folded, then goes back to whatever you had
- **Grab & drag** — runs in the drag direction; **double-click** = jump + **instant usage refresh** (cache-busting refetch)
- **When token usage spikes** — warning-color pulse + panic face, and that provider's session label turns red with ▲ in the pill:
  - 🔴 session (or Codex) spike / 🟣 model (Fable/Opus) spike / 🟠 weekly spike
  - Spikes are read from the local logs of Claude Code and Codex. The threshold uses a limit the pet **learns from the server's %** —
    nothing to set up; until it has learned one there are no spike alerts (and none for a provider in API mode)
- **When a session reset is detected** (the server's session % drops from above 5 % to below 1 %) — jumps for joy

## Controls

- **Scroll (over the pet)**: resize (0.3×–2.0×, saved; default 0.5×)
- **Click (⌄ button)**: show/hide the usage pill
- **Drag**: move (position saved)
- **Right-click**: menu — (Install / Sign in to Claude Code or Codex, when needed) / Settings / Show or hide the pill / Roam the screen (on/off) / Reset size / Pets (pick or add your own) / Uninstall / Quit / Check for updates

## The usage pill

One small pill next to the pet, two lines:

- **Line 1 — usage**: `Session 42% · Weekly 17% · Fable 12%` — session (5h) / weekly total / weekly per-model, exactly as the
  server reports them. Codex gets its own block (with its own mark) next to Claude's. In API mode a provider shows cost instead:
  `Today $3.21 · This month $27.50`.
- **Line 2 — resets**: `reset Session in 3h 42m · Weekly in 2d 3h`.
- **Numbers are always the server's**: emerald = server-computed %, coral = API cost. The pet never shows a number estimated
  from logs — with no server value the pill shows a status instead (e.g. "Token expired — run Claude Code once to restore usage",
  a sign-in prompt, or "Nothing to show" when both providers are hidden). An expired Codex sign-in shows its own status:
  "Codex token expired — run codex once to restore usage".
- **A brief server hiccup does not blank the pill**: if a refresh fails with a rate limit, a server error, a network error or a
  garbled answer, the last values received stay on screen until the next successful refresh. Only a rejected token clears them.
  Saving settings redraws from the values already fetched; only a new language, data source or Admin key fetches again.
- **Label colour says how much is left**: white, yellow from 50 %, red from 85 % — and red with ▲ while that gauge is spiking.
- The text is set in the bundled **Pretendard** typeface (SIL Open Font License), so it looks the same on every machine.

## Your own pets

Right-click → **Pets** lists the built-in cat plus every folder under `~/.claude_pet/pets/`; **Add a pet…** opens that
folder with a README describing the format. A pet is a folder holding `pet.json` + `spritesheet.webp` (the README has the
sheet layout). The list is re-read every time you open the menu, so a new folder shows up without restarting. A zip
extracted one level too deep (`pets/name/name/pet.json`) is recognized too, and `__MACOSX` is ignored.

## Settings (right-click → Settings)

- **Claude Code** and **Codex** each get their own section, laid out the same way:
  - **Show in the pill** on/off
  - **Data source**: subscription (signed-in account) / API (Admin API cost — today and this month; with a monthly budget set the pill reads `This month $27.50 / $50` and the "This month" label turns yellow/red by the share used while the amounts stay coral)
  - **Gauges** to show — Claude Code: session / weekly / per model / credit; Codex: session / weekly
  - **Admin API key** and **monthly budget** — Codex uses an **OpenAI Admin API key**
- Then spike sensitivity and mouse-greeting on/off. There is nothing to calibrate: limits for spike alerts are learned from the server's %.

- **Roam the screen**: toggle with the check item in the right-click menu (on by default); it also covers following the
  mouse and hopping between monitors. If macOS Accessibility **Reduce Motion** is on, the pet does not move.
  Positions it wanders or hops to are not saved; only where you drag it is remembered.

All settings, size, and position are saved in `~/.claude_pet.json`.

## Limits (honestly)

- The numbers are the server's own %, so they match Claude's and Codex's own usage screens. Spike alerts come from local logs, which do not include web/desktop chat.
- Admin API cost is your Console organization's, separate from the subscription limit.
- The Admin API keys (Anthropic and OpenAI) are stored in plaintext in `~/.claude_pet.json`, so use them only on a personal machine.

## License

[MIT](LICENSE) © 2026 Yeongyu Yang. The bundled Pretendard typeface is under the SIL Open Font License (`fonts/`).
