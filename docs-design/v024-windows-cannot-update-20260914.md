# Shipped v0.24 Windows copies can never see an update (found 2026-09-14)

The v0.25 end-to-end upgrade check on the user's Windows 11 machine could not be
performed, and the reason is a defect in **v0.24**, not in v0.25. Recorded here because it
is permanent for anyone already running that build, and because it changes what the v0.25
release notes' third bullet means for those users.

## What was observed

The Windows session removed v0.25, reinstalled the real published v0.24 assets (hashes
matching the release: setup `cf743a5f…`, zip `386679f9…`), and pressed "⬆ 업데이트 확인…"
on both install kinds:

| install kind | result |
| --- | --- |
| installer (Inno) | "업데이트를 확인하지 못했습니다. 잠시 후 다시 시도하세요." |
| portable zip | the same box, the same wording |

No new-version notice, and no releases page opened. At the same moment that machine got
HTTP 200 and `tag_name: v0.25` from `api.github.com/repos/uygnoey/claude-pet/releases/latest`,
so it is not the network.

This also refutes something I had written down and repeated: that a v0.24 Windows copy
opens the releases page when you press the update item. It does not; it shows a failure
box and nothing else.

## Why — confirmed here against the published tag

`git show v0.24:claude_pet.py` line 2726:

```python
UPDATE_ASSET_NAMES = {
    "arm64": ("claudepet.zip", "claudepet-universal.zip"),
    "x86_64": ("claudepet-universal.zip",),
}
```

The keys are macOS `platform.machine()` values only. On Windows `platform.machine()` is
`'AMD64'`, so the lookup misses, `select_update_asset()` prints
`[update] rejected: unknown architecture ('AMD64')` and returns `None`,
`check_github_update()` returns `('failed', None, None)`, and the menu shows the failure
box. **No asset upload can fix this**, because the check never reaches the asset list.

Two consequences follow from the same tag:

- **`poll_github_update` deliberately does not stamp the cooldown when the status is
  `failed`** (v0.24 line 4372: `if status != "failed": _upd_cache["t"] = …`). Since a
  Windows copy's check always fails, `_upd_cache["t"]` never moves, so after the first
  hour every 30-second refresh issues another request to `api.github.com`. This is the
  problem v0.25 fixes by stamping a cooldown on failure too — and it cannot be delivered
  in-app for exactly the reason above.
- **The v0.24 tag ships no `windows/` tree at all** (`git ls-tree -r v0.24 -- windows/`
  returns nothing; `win_update.py` first appears in `f4130b3`, 2026-09-13). So a shipped
  v0.24 Windows copy writes no `update.log`, creates no
  `%LOCALAPPDATA%\me.yeongyu.claudepet`, and has no release marker — there are no log
  lines to quote for this failure, and the Windows session confirmed none were created.

## Blast radius

From the GitHub API on 2026-09-14: v0.24's `claude-pet-win-setup.exe` has 2 downloads and
`claude-pet-win.zip` has 1. The Windows session's own testing accounts for some of those.
So this affects at most a couple of installations, one of which is the maintainer's — but
it is unbounded in time for each of them.

## What v0.25's updater does correctly

The real upgrade could not run, so the Windows session drove v0.25's decision functions
against the **live** v0.25 release JSON instead:

- `select_update_asset_win(assets, "AMD64", "inno")` → `claude-pet-win-setup.exe` with the
  published size 56,054,985 and digest `sha256:e1c39d76…`
- `select_update_asset_win(assets, "AMD64", "portable")` → `claude-pet-win.zip`, size
  72,507,793, digest `sha256:98f440b3…`
- `"ARM64"` → `(None, 'no-asset')`; `"x86"` → `(None, 'unknown-machine')`
- `check_github_update_win(…, "0.24")` → `('update', '0.25', …)` for both kinds;
  `(…, "0.25")` → `('current', '0.25')`
- `verify_download()` → `True` for both real files against the release's own size and digest

That closes the hardware check for size/digest against a real release. What remains
unexercised is the actual replacement, which needs a version above 0.25 to exist — so it
belongs to the v0.26 cycle, on a v0.25 install.

## What follows

Anyone already on Windows v0.24 must download v0.25 by hand; the installer upgrades in
place and keeps their pets and settings (the Windows session overwrote v0.24 with v0.25
several times during this work and `%USERPROFILE%\.claude_pet` — seven pets — and
`.claude_pet.json` survived every time).

Telling them so would mean editing published material: the v0.25 release body, and the
`RELEASE_NOTES.md` section that is now frozen because the tag is pushed and the release
exists with that entry as its body. Under CLAUDE.md that is the user's call, not an
agent's. It was put to the user on 2026-09-14 with the download counts above, and the
answer was to leave it: "냅둬 24버전 다운받은 사람 없을거야". So nothing published was
edited, and this file is the record of why.

If a v0.24 Windows user does turn up, the fix on their side is to download v0.25's
installer and run it over the existing install; their pets and settings survive.
