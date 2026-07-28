# `.claude_pet/pets` — example companion set

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Español](README.es.md)

Ready-to-use custom pets for **claude-pet (v0.18)**.
Four companions are included: **Dog · Fox · Scorpion · Elephant**.

> ⚠️ **Important — the app does not read this folder directly.**
> claude-pet loads custom pets from your home directory, `~/.claude_pet/pets/`.
> The `.claude_pet/pets/` inside this repository is a **distributable example set** that you copy
> into that home folder — the app never auto-copies or references this repo path.
>
> Note this is also different from the settings file `~/.claude_pet.json` (a JSON file, not a folder).

---

## Quick start (install)

```bash
mkdir -p ~/.claude_pet/pets
cp -R dog fox scorpion elephant ~/.claude_pet/pets/
```

After copying, **right-click the menu-bar icon → pick a pet** and the new companions appear.
The menu re-scans the folder every time it opens, so **no app restart is needed**.

The app's "Open pets folder" menu creates `~/.claude_pet/pets/` if it is missing and drops a
usage guide (`README.txt`) there before opening it in Finder.

---

## Folder layout

```
<pet-name>/
├── pet.json          # metadata + sprite convention (required)
├── spritesheet.webp  # sprite sheet (required — the only image actually loaded)
└── preview.png       # preview image (optional, not used at runtime — docs/gallery only)
```

- **A pet's internal ID is its folder name** — not the `id` field in `pet.json`.
- Only `pet.json` and `spritesheet.webp` are read at runtime.
  `preview.png` is not referenced by the code (it exists for repository previews).

---

## `pet.json` schema

```json
{
  "id": "dog",
  "displayName": "Dog",
  "description": "A friendly dog companion …",
  "spriteVersionNumber": 2,
  "spritesheetPath": "spritesheet.webp"
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | Recommended | For identification. The app actually uses the **folder name** as the ID. |
| `displayName` | Recommended | Name shown in the right-click menu. Falls back to the folder name. |
| `description` | Optional | Documentation only; unused at runtime. |
| `spriteVersionNumber` | Recommended | Sprite-sheet grid convention. Only **2** is defined today; unknown values fall back to v2. |
| `spritesheetPath` | Optional | Relative path to the sheet. Defaults to `"spritesheet.webp"`. |

---

## Sprite-sheet convention (spriteVersionNumber 2)

The sheet is sliced on a **fixed 8-column × 11-row grid**.

- Cell size = `sheet width / 8` × `sheet height / 11`
- The bundled pets are all **1536 × 2288** → cells of **192 × 208**
- Each animation state fills a given **row** from column 0, left → right, for a fixed frame count.

| Row | State | Frames |
|---|---|---|
| 0 | `idle` | 7 |
| 1 | `running-right` | 8 |
| 2 | `running-left` | 8 |
| 3 | `waving` | 4 |
| 4 | `jumping` | 5 |
| 5 | `failed` | 8 |
| 6 | `waiting` | 6 |
| 7 | `running` | 6 |
| 8 | `review` | 6 |
| 9–10 | (reserved, unused) | — |

- **`idle` is required.** A pet with no usable `idle` frames is treated as invalid.
- Keep each cell's margins/background transparent (alpha).

### Animation timing

Instead of a fixed fps, each state has a **per-frame duration (ms)** (approximate):

| State | Per-frame | Playback |
|---|---|---|
| `idle` | 430 ms | loops (~25 s pause between loops) |
| `waiting` | 340 ms | loops |
| `review` | 360 ms | loops |
| `failed` | 260 ms | loops |
| `waving` | 200 ms | plays once |
| `jumping` | 150 ms | plays once |
| `running` / `running-left` / `running-right` | 90 ms | loops (≈ 11 fps) |

States not listed use the default of 400 ms, looping.

---

## Make your own pet

1. Create `~/.claude_pet/pets/<name>/`.
2. Lay out `spritesheet.webp` on the 8×11 grid above (at minimum the `idle` row).
3. Write `pet.json` (`spriteVersionNumber: 2`).
4. Reopen the right-click menu and your pet shows up.

> Legacy format is also supported — instead of `pet.json`, a pet can be **per-state subfolders of PNG
> sequences** (`idle/`, `running/`, …). The built-in cat uses this. New pets should use the sheet format.

---

## When the folder is missing

The app runs fine without `~/.claude_pet/pets/`, and the default is the **built-in cat (Cat 🐱)**.
If a saved pet disappears or gets corrupted, it automatically falls back to this built-in pet.

---

> 🛍️ **Coming soon:** a pet marketplace to browse and add new companions in a click.
