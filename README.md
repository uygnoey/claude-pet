# 🐱 Claude Pet (Patch Edition)

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Español](README.es.md)

A desktop pet — Patch floats on your screen and watches your Claude token usage, à la Codex Pets.
Rendered natively on macOS (AppKit) — no window frame, no background, no ghosting.

> 🧪 Currently **v0.1 (beta)** — experimental; behavior and labels may change.

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

### Updates

On launch the app checks the latest GitHub release; if a newer version exists, **right-click → "⬆︎ Install new version"** downloads, replaces, and relaunches automatically.

---

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

./release.sh               # distributable self-contained app (py2app) + Developer ID sign + notarize + zip
```
`release.sh` needs notarization credentials stored once (see the comment at the top of the script).

## Behavior

- **Idle by default** — first frame frozen; a breath/blink only once every 25s
- **When the mouse comes close** — waves hello (30s cooldown)
- **Grab & drag** — runs in the drag direction; **double-click** = jump + **instant usage refresh** (cache-busting refetch)
- **When token usage spikes** — warning-color pulse + panic face + ▲spike on the gauge:
  - 🔴 session spike / 🟣 model (Fable/Opus) spike / 🟠 weekly spike
- **When a session reset is detected** — jumps for joy

## Controls

- **Scroll (over the pet)**: resize (0.3×–2.0×, saved; default 0.5×)
- **Click (⌄ button)**: collapse/expand the gauge panel
- **Drag**: move (position saved)
- **Right-click**: menu — Settings / Collapse / Reset size / Quit

## Three gauges (subscription mode)

Session (5h) / weekly total / weekly per-model — each with %, remaining tokens, reset countdown.
The per-model gauge **auto-detects** the top tier from the logs (fable → mythos → opus).

## Settings (right-click → Settings)

- **Data source**: subscription (Claude Code logs) / API (Admin API cost — today, this month, monthly-budget gauge)
- **🔧 Calibration (most important!)**: the token limits are private to Anthropic, so nobody knows them.
  Instead, type the % shown in the Claude app's **Settings > Usage** and save — the app back-solves
  `limit = current usage ÷ %`. Only the fields you enter are applied.
- **Weekly reset day/time**: if the app says "resets Sat 8:00 PM", set Saturday/20:00. Rolling 7 days if unset.
- Model keyword (auto recommended), spike sensitivity, mouse-greeting on/off, Admin API key, monthly budget

All settings, size, and position are saved in `~/.claude_pet.json`.

## Limits (honestly)

- Data is based on Claude Code's local logs — web/desktop chat usage is not included. So it can read lower than the app's %; recalibrate periodically to stay accurate.
- Admin API cost is your Console organization's, separate from the subscription limit.
- The Admin API key is stored in plaintext in `~/.claude_pet.json`, so use it only on a personal machine.
