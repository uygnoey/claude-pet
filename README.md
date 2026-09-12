# 🐱 Claude Pet (Patch Edition)

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Español](README.es.md)

A desktop pet — Patch floats on your screen and watches your Claude token usage, à la Codex Pets.
Rendered natively on macOS (AppKit) — no window frame, no background, no ghosting.

> 🧪 v0.24 — the macOS app is notarized; the Windows build is a beta (unsigned).

![Patch](preview.png)

## Download & Install (recommended)

**No Python needed** — it's bundled inside the app, which is **notarized by Apple**, so it opens with no Gatekeeper warning.

1. Download `ClaudePet.zip` from [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest) — on an **Intel Mac**, grab `ClaudePet-universal.zip` instead (available from v0.10)
2. Unzip → move `ClaudePet.app` to your **Applications** folder → double-click
3. macOS 12+ (Apple Silicon; Intel from v0.10 via the universal zip)

### Permissions (first launch)

The pet only reads **`~/.claude` (usage logs) and the OAuth token in your Keychain**. It never touches other folders (Photos, Downloads, Documents, …). On first launch you'll see only these:

| Prompt | What | Choose |
|---|---|---|
| **Keychain** — "Claude Code-credentials" | OAuth token so Exact mode can fetch server-computed % | **Always Allow** |
| **"data from other apps"** — `~/.claude` | reading usage logs | **Allow** |

- The token is read **once per launch**, and because the app is signed the decision is remembered — you won't be asked again.
- **No Photos / Downloads / Music / Desktop / Documents / iCloud / Network-volume prompts appear.** (They used to, because the pet spawned the `claude` CLI as a child and its home scan was attributed to the app — that CLI call is now OFF by default.)
  - To supplement the per-model (Fable) row via the CLI, set `CLAUDE_PET_USE_CLI=1` — but then the folder prompts come back.

### Claude Code is required

The pet is a HUD for **Claude Code usage** — the usage data (logs and token) comes from Claude Code itself. So **subscription mode requires Claude Code to be installed.**

- If Claude Code isn't installed, the pet shows **"Claude Code not installed"** instead of the pill. **Right-click → "⬇︎ Install Claude Code…"** runs the official installer ([`claude.ai/install.sh`](https://claude.ai/install.sh)) in Terminal, then signs you in.
- If it's installed but not logged in, **right-click → "🔑 Sign in to Claude Code…"** starts the login.
- Once done, usage appears on the next refresh — no restart needed.
- Note: **API mode** (right-click → Settings → Admin API key) works without Claude Code.

### Updates

Every hour after launch (never at launch) the app checks the latest GitHub release; if a newer version exists, **right-click → "⬆︎ Install new version"** downloads, replaces, and relaunches automatically. **Right-click → "⬆︎ Check for updates…"** checks right now and installs straight to the latest version.

---

## Windows (beta)

Windows 10/11 (64-bit) gets the same pill, roaming, settings and pets. Two files are published with every release:

- **`claude-pet-win-setup.exe`** — installer. Installs for the current user (no admin rights), adds a Start Menu entry and an "Apps & features" uninstall entry, and offers **Start Claude Pet when I sign in**.
- **`claude-pet-win.zip`** — portable/update build. Unzip anywhere and run `ClaudePet\ClaudePet.exe`.

**About the SmartScreen warning.** The Windows build is not code-signed yet, so the first time you run the installer or `ClaudePet.exe`, Windows shows *"Windows protected your PC"*. Click **More info**, then **Run anyway**. This appears once per file; it is Windows' notice that the publisher is unknown, not a detection of anything harmful. If your browser or Edge flags the download the same way, choose **Keep** → **Keep anyway**. Code signing will remove the warning in a later release.

Sign in to Claude Code on Windows first (`claude`), then launch Claude Pet: Exact mode reads the Claude Code credential file and the estimate reads Claude Code logs under `%USERPROFILE%\.claude`. Your own pets go in `%USERPROFILE%\.claude_pet\pets\<name>\` (right-click → Pets → Add a pet… opens it). The tray icon sits in the taskbar overflow (`^`) by default; drag it out to keep it visible. Right-click → Uninstall completely… removes the settings and logs; the installer's uninstaller (Apps & features) removes the program.

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
- **When token usage spikes** — warning-color pulse + panic face, and that gauge turns red with ▲ in the pill:
  - 🔴 session spike / 🟣 model (Fable/Opus) spike / 🟠 weekly spike
- **When a session reset is detected** — jumps for joy

## Controls

- **Scroll (over the pet)**: resize (0.3×–2.0×, saved; default 0.5×)
- **Click (⌄ button)**: show/hide the usage pill
- **Drag**: move (position saved)
- **Right-click**: menu — Settings / Show or hide the pill / Roam the screen (on/off) / Reset size / Pets (pick or add your own) / Uninstall / Quit / Check for updates

## The usage pill

One small pill next to the pet, two lines:

- **Line 1 — usage**: `Session 42% · Weekly 17% · Fable 12%` — session (5h) / weekly total / weekly per-model. The per-model
  gauge **auto-detects** the top tier from the logs (fable → mythos → opus). In API mode it shows cost instead:
  `Today $3.21 · This month $27.50`.
- **Line 2 — resets**: `reset Session in 3h 42m · Weekly in 2d 3h` (weekly shows `-` on a rolling window).
- **Number colour says where it comes from**: emerald = Exact mode (server-computed %), amber = log estimate (values
  carry ≈), coral = API cost. If the Claude Code token has expired, the estimate line ends with ⚠.
- **Label colour says how much is left**: white, yellow from 50 %, red from 85 % — and red with ▲ while that gauge is spiking.
- The text is set in the bundled **Pretendard** typeface (SIL Open Font License), so it looks the same on every machine.

## Your own pets

Right-click → **Pets** lists the built-in cat plus every folder under `~/.claude_pet/pets/`; **Add a pet…** opens that
folder with a README describing the format. A pet is a folder holding `pet.json` + `spritesheet.webp` (the README has the
sheet layout). The list is re-read every time you open the menu, so a new folder shows up without restarting. A zip
extracted one level too deep (`pets/name/name/pet.json`) is recognized too, and `__MACOSX` is ignored.

## Settings (right-click → Settings)

- **Data source**: subscription (Claude Code logs) / API (Admin API cost — today and this month; with a monthly budget set the pill reads `This month $27.50 / $50` and the "This month" label turns yellow/red by the share used while the amounts stay coral)
- **🔧 Calibration (most important!)**: the token limits are private to Anthropic, so nobody knows them.
  Instead, type the % shown in the Claude app's **Settings > Usage** and save — the app back-solves
  `limit = current usage ÷ %`. Only the fields you enter are applied.
- **Weekly reset day/time**: if the app says "resets Sat 8:00 PM", set Saturday/20:00. Rolling 7 days if unset.
- Model keyword (auto recommended), spike sensitivity, mouse-greeting on/off, Admin API key, monthly budget

- **Roam the screen**: toggle with the check item in the right-click menu (on by default); it also covers following the
  mouse and hopping between monitors. If macOS Accessibility **Reduce Motion** is on, the pet does not move.
  Positions it wanders or hops to are not saved; only where you drag it is remembered.

All settings, size, and position are saved in `~/.claude_pet.json`.

## Limits (honestly)

- Data is based on Claude Code's local logs — web/desktop chat usage is not included. So it can read lower than the app's %; recalibrate periodically to stay accurate.
- Admin API cost is your Console organization's, separate from the subscription limit.
- The Admin API key is stored in plaintext in `~/.claude_pet.json`, so use it only on a personal machine.
