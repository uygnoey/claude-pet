# CLAUDE.md — ClaudePet facts

This file holds facts about **this** repository: paths, symbols, commands, constants,
and the domain invariants of the log parsers behind spike detection.

The process rules that govern how agents work here — roles, Developer–Verifier
separation, red-before-green, evidence standards, the merge checklist, the release gate,
commit trailers — are in [AGENTS.md](AGENTS.md) and are not repeated here. Read both.

Rules below carry one of three tags, all defined in
[AGENTS.md §0](AGENTS.md#0-how-to-read-the-prohibitions):

- **[NEVER]** — no path exists; do not ask.
- **[ASK]** — permitted only with explicit authorization from the party named.
- **[ASK-OP]** — everything [ASK] requires, **plus** all gates recorded first **plus**
  execution by a release operator (§1) who held no other role on the release. That last
  condition is absolute and no authorization lifts it. **`[ASK-OP]` is a single tag** —
  reading it as a plain [ASK] with a trailing comment drops the part that matters.

Untagged text is guidance, or a correctness fact (see §0) — the tags govern permission,
never whether a number comes out right.

---

## What this is

ClaudePet is a macOS desktop pet that displays your Claude Code and Codex usage — always
the percentages the providers' own servers report, or the API cost in API mode. It is an
`LSUIElement` app (no Dock icon, no menu bar item — it draws a borderless always-on-top
window with an animated sprite and a compact one- or two-line usage summary pill), written in Python against PyObjC
(AppKit/Foundation), and shipped as a self-contained, Developer ID-signed and
Apple-notarized `.app` bundle built with py2app.

**`claude_pet.py` is essentially the whole app** — a single module holding config,
i18n (en/ko/ja/es), log parsing for spike detection (Claude Code and Codex), the learned
spike limits, OAuth/keychain token reading, the Codex usage reader, the Admin API clients
(Anthropic and OpenAI), the AppKit UI, the settings panel, the updater, and the uninstaller.
The Windows port (`windows/claude_pet_win.py`, PySide6) imports this module and calls
the same core functions; it implements only the window, drawing, menu and settings dialog.
There is no package structure to navigate. Use `grep -n` on symbol names; line numbers
in any document (including this one) drift as the file changes, so treat every line
number as approximate and locate code by symbol. For the same reason this file quotes no
length for it: any figure written down here is stale by the next change, and a stale one
invites the reader to reason from it.

---

## Repo layout

| Path | What it is |
| --- | --- |
| `claude_pet.py` | The application. Everything below the UI layer lives here too. |
| `tests/test_log_estimate.py` | Unit tests for the Claude Code log parser that spike detection stands on (`parse_usage_entries`, `_weigh_usage`, `compute_usage`'s spike snapshot). The name is historical: nothing it covers produces a displayed number any more. |
| `tests/test_codex_usage.py` | Codex usage rows, the Codex session-log parser (`parse_codex_entries`), `codex_spikes`, and the OpenAI cost client (`fetch_codex_cost`). It is in the Windows CI job's list, so it runs on real Windows too. |
| `tests/test_server_only_usage.py` | Gates for the server-only change: no estimate anywhere, learned spike limits (`learn_limit`, `learn_lane`, `learn_server_limits`), per-provider spikes and API mode, the server-value reset jump, gauge filters, the two-section settings plan, the Codex menu items. |
| `tests/test_settings_and_install.py` | Counterexample tests for the settings transaction, the bundled-pet seed, and the updater. Most are written to fail against a specific wrong implementation — read the test before changing the code it pins. |
| `tests/test_updater.py` | Updater contract tests: asset selection, the update preflight, the zip-member scan, and the generated replacement shell script. Tests that need the real macOS tools skip **loudly** (stderr + `skipTest`) so a missing prerequisite cannot read as coverage. |
| `tests/test_updater_adversarial.py` | Adversarial gates for the updater transaction, deliberately sharing no fixtures with `test_updater.py`. Its header lists the plausible wrong implementations each fixture rules out. |
| `tests/test_mutation_instruments.py` | Tests the updater tests' *instruments*, not the app: whether the `str.replace` fault injections still find their needles in the generated script. `str.replace` cannot fail, so a reworded script would silently turn those tests into no-ops. |
| `tests/test_manual_update_transaction.py` | Behavioural gates for `build_app.sh`'s install/update transactions. It never sources or executes the script — it extracts the reviewed function as text, pins it by source hash, and runs the fragment under a temporary directory with shimmed tools. |
| `tests/test_upload_artifact_gate.py` | Behavioural gates for `release.sh`'s `verify_upload_artifact` — that a missing, corrupt, or unknown-extension artifact fails rather than passing vacuously, and that an upload must contain exactly one `.app` at the root. The script is never sourced or dispatched: only that one function's text is brace-matched out of a copy and sourced as a fragment, which has no `case` to fall through to. `ditto`, `hdiutil`, `mktemp`, `$PY` and the signing tools are replaced by shims ahead of `/usr/bin` on a sandbox `PATH`, with `HOME`/`TMPDIR` under a temp directory and `CDPATH` cleared, so nothing is extracted, mounted, signed or uploaded for real. It pins the reviewed SHA256 of `release.sh`, `verify_release_artifact.py` and `claude_pet.py`, and refuses to run when any of the three has changed. |
| `tests/test_release_gate.py` | Packaging-gate tests built from real trees on disk rather than substring greps over the build scripts, each written so that deleting the check it targets makes it fail. |
| `tests/test_release_artifact_preflight.py` | Gates for `verify_release_artifact`'s delegation and its local code-leaf check. Signing and notarization are represented by a fake `validate_update_app`; no signing tool or release shell is invoked. |
| `tests/test_signing_contract.py` | Live contract tests for the argv handed to the macOS signing tools — they run the real binary against a real bundle, because a mocked `subprocess.run` cannot validate an *argument*. |
| `tests/test_source_guard.py` | Behavioural tests for the zsh source guards in both scripts. Each script is copied to a temp directory and its bottom dispatch replaced by a marker, so no destructive arm is ever reached. |
| `tests/test_partial_copy_seeding.py` | Seeding tests for a copy that dies *midway through a file*, a different state from one that never starts. |
| `tests/test_seeding_identity.py` | Identity-bound cleanup gates for bundled-pet seeding. Both roots are passed explicitly and live under a realpath temp directory; `USER_PET_HOME` and the process `HOME` are never consulted. |
| `tests/test_v020_boundaries.py` | Upgrade-boundary verification for v0.20. Fail-closed: it refuses to run unless launched with the allow-list environment its header specifies. |
| `tests/test_autostart.py` | Gating tests for the "Start at sign-in" menu item: the status table, the toggle's truth table, the `do_uninstall()` ordering, the TR keys, and the menu wiring (by AST, no GUI). Every service is a fake; `sys.modules["ServiceManagement"]` is a tripwire for the duration of the module. |
| `verify_pet_payload.py` | Build gate: checks that the bundled `.claude_pet` payload actually landed in an artifact and matches the repo source byte for byte. It reads the expected file list out of `claude_pet.py`'s `BUNDLED_PET_README` / `BUNDLED_PET_IDS` / `BUNDLED_PET_FILES` via AST rather than importing it, so adding a pet cannot leave a hardcoded count checking the wrong number. Called by `release.sh` (`build`, and per-artifact before upload) and by `build_app.sh`. |
| `verify_release_artifact.py` | Release gate: inspects the zip/dmg **that will be uploaded**, not a build directory. `scan` checks archive safety before any byte is extracted, `app` checks that the bundle's `Contents/Resources/claude_pet.py` is byte-identical to this checkout's and then hands the bundle to the updater's own preflight, `assets` checks the upload list against the updater's asset-name table. The code-hash check is the one the updater cannot do — it has no original to compare against, and a signature says *who built it*, never *what is inside*: a stale bundle re-signed today passes every other check. It **calls** `claude_pet`'s `_zip_members_are_safe` and `validate_update_app` rather than reimplementing them — which is why its diagnostics carry an `[update]` prefix. |
| `build_app.sh` | Fast local build: assembles `ClaudePet.app` from `claude_pet.py` + `frames/` + `.claude_pet/`. **It does sign** — `sign_app` uses the Developer ID when one is present, ad-hoc otherwise. `build` / `install` / `update` subcommands; anything else prints usage and exits 1. |
| `release.sh` | Real release: py2app build → Developer ID sign → notarize → staple → zip/dmg. |
| `setup.py` | py2app configuration. |
| `launcher.c` | Tiny Mach-O launcher — the bundle executable must be Mach-O to be code-signable. |
| `entitlements.plist` | Hardened-runtime entitlements for signing. |
| `frames/` | Sprite frames for the built-in pet, plus `frames-manifest.json`. |
| `fonts/` | `Pretendard-SemiBold.ttf` (OFL 1.1, licence beside it; the TrueType build, because the CFF build rendered roughly at small sizes on Windows) — the summary pill's typeface, bundled so every machine draws the same glyphs (the intent is that the Windows port, developed on the `windows` branch, loads the same file). `setup.py` ships it as a resource with `ATSApplicationFontsPath`, `build_app.sh` copies it in both `build()` and `update()`, and `verify_release_artifact.py` refuses an artifact without it. |
| `.claude_pet/` | The pets shipped **inside the app**: four `README*.md` plus `pets/{dog,elephant,fox,scorpion}/{pet.json,spritesheet.webp,preview.png}` — 16 tracked files. `setup.py` ships it as a resource and `build_app.sh` copies it in both `build()` and `update()`, so a code-only refresh does **not** leave the bundled tree stale. Distinct from `~/.claude_pet/`, the user's own directory this one seeds into. |
| `make_icon.py` | Generates the app icon. |
| `RELEASE_NOTES.md` | User-facing changelog, in Korean, newest first. Consumed by `release.sh` as the GitHub release body. |
| `README.md`, `README.ko.md`, `README.ja.md`, `README.es.md` | User docs. |
| `docs/` | The GitHub Pages site (`docs/index.html`, assets, `CNAME`). |
| `docs-design/` | Design notes for long-horizon work (e.g. `self-login-oauth.md`). |
| `build/`, `dist/`, `dist-universal/` | Build output, fully gitignored (`build/`, `dist/`, `dist-universal/` entries in `.gitignore`). |
| `release/` | **Mixed, and NOT gitignored as a directory.** See the warning below — this is the one path in the repo that punishes a directory-wide delete. |

### `release/` is mixed — never delete it as a directory

**[NEVER] run `rm -rf release` or any directory-wide delete of `release/`.** Unlike
`build/` and `dist/`, this directory is not gitignored and is not purely generated. It
holds four different kinds of file at once:

| Path | Status | If deleted |
| --- | --- | --- |
| `release/icon.icns` | **tracked** | Recoverable from git, but still an unintended change. |
| `release/ClaudePet.iconset/` | untracked, **not** ignored, **user-owned** | **Unrecoverable.** |
| `release/icon_1024.png` | untracked, **not** ignored, **user-owned** | **Unrecoverable.** |
| `release/*.zip`, `release/*.dmg` | ignored by the `*.zip` / `*.dmg` patterns in `.gitignore` | Regenerable by `release.sh`. |

So `rm -rf build dist release` — which looks like ordinary build hygiene, and is the
shape of command an agent reaches for when told to start from a clean state — destroys
two user-owned files that no git operation can restore. `release.sh` manages its own
outputs; there is no task that requires you to clear this directory by hand.

### User-owned files

**[ASK]** These untracked files are the user's. No agent may modify, add, or delete them
on its own authority, and **no assignment can license it** — under
[AGENTS.md §4](AGENTS.md#4-preserving-untracked-work) an assignment may only name paths
that do not yet exist or that the assigning party created, so naming one of these grants
nothing. Only the user can authorize touching them, directly, per file.

- **`diag.py`**
- **`release/ClaudePet.iconset/`**
- **`release/icon_1024.png`**

This list is not the definition and is not exhaustive: an untracked path missing from it
is still off-limits. Do not infer that anything absent here is fair game.

These files are expected to stay untracked forever, so this repository's working tree
permanently shows `??` entries. That is the normal state and does **not** mean the tree
is dirty — see [AGENTS.md §6](AGENTS.md#what-clean-tree-means-here) for why that matters
before a release, and why `git clean` is never the way to get a clean tree here.

---

## Run, test, build

### Run

```sh
python3 claude_pet.py            # runs the GUI (needs pyobjc)
python3 claude_pet.py --report   # CLI usage report, no GUI
CLAUDE_PET_DEBUG=1 python3 claude_pet.py   # logs token-read path to ~/claudepet_debug.log
```

### Test

```sh
python3 -m unittest discover -s tests -v
```

**Run it from the repository root.** `python3 -m unittest` puts the current working
directory on `sys.path`, which is the only reason `import claude_pet` inside the tests
resolves.

Known issue: **`tests/` has no `__init__.py`**, so it is not an importable package. The
command above works from the repo root, but three nearby invocations fail, and the
failures look like problems with the code when they are not:

- from any other directory (`python3 -m unittest discover -s /path/to/claude-pet/tests`)
  → `ModuleNotFoundError: No module named 'claude_pet'`
- with an explicit top-level dir (`python3 -m unittest discover -s tests -t .`)
  → `ImportError: Start directory is not importable: 'tests'`
- running the file directly (`python3 tests/test_log_estimate.py`)
  → `ModuleNotFoundError: No module named 'claude_pet'`

**[ASK]** Do not create `tests/__init__.py` to fix this. `tests/` is not yours to
restructure unless that change is explicitly assigned to you.

This list covers only failures caused by the missing `__init__.py`. It is not a general
troubleshooting guide: a `ModuleNotFoundError` naming a package other than `claude_pet`
is a missing dependency (`pyobjc`), and an import error raised from inside
`claude_pet.py` itself is a real code problem. Match the exact message before assuming
this is your cause.

### Build

```sh
./build_app.sh build      # build ClaudePet.app in the repo. Nothing else.
./build_app.sh install    # local build → /Applications → restart. For day-to-day testing.
./build_app.sh update     # refresh the installed bundle in one transaction, restart.
./release.sh build        # py2app build only, unsigned. Safe to run.
```

**Both build Pythons must import `ServiceManagement`.** `build_app.sh` takes the first
`python3` it finds (pyenv on the maintainer's Mac). `release.sh` builds with the python.org
universal2 Python, `UPY`, and `PY` now defaults to that same interpreter (still overridable);
the arm64 build runs it as arm64 and thins the bundle to arm64. The "Start at sign-in" toggle
imports the `ServiceManagement` framework at call time and `setup.py` lists it for py2app. A
bundle built from a Python that lacks `pyobjc-framework-ServiceManagement` shows the menu item
disabled on every machine — that happened on 2026-09-13 with pyenv's Python.
`check_build_python()` in `release.sh` refuses, before building, an interpreter that cannot
import `py2app`, `objc` and `ServiceManagement`.

**The release build Python's deployment target must be ≤ macOS 12.0.** py2app ships the
building interpreter's own `Python.framework` and extension modules, so their minimum macOS
becomes the app's. pyenv's Python is compiled on the maintainer's Mac and carries that Mac's
macOS as its target (26.3), and `release.sh` used to default `PY` to it: the arm64 artifacts
through v1.0.0 (from at least v0.24) opened only on macOS 26.3+, while the site promises 12+.
`check_build_python()` now refuses an interpreter whose `MACOSX_DEPLOYMENT_TARGET` is above
`MIN_MACOS` (12.0), and `verify_release_artifact.py minos` — run after each build and inside
the upload gate's `app` check — rejects a bundle in which any Mach-O slice has an
`LC_BUILD_VERSION` minos or `LC_VERSION_MIN_MACOSX` above 12.0. `build_app.sh` (local
installs only) has no such check.

**`update` is a whole-bundle transaction: either all of it lands, or the installed
bundle is exactly what it was.** It refreshes four things that have to move together —
`claude_pet.py`, the bundled `.claude_pet` tree, the `Info.plist` version, and the
signature — and a bundle carrying some of the four is a state no per-piece rollback
restores, because each piece is individually where it belongs. So the new bundle is
assembled and verified beside the installed one and swapped in at the end. **`install` is
the same kind of transaction**, over the whole bundle rather than those four pieces: the
existing installation is moved aside rather than deleted, and moved back if anything
fails.

Two consequences worth knowing. First, **every step that can reject runs before the pet is
stopped** — a rejection therefore costs the user nothing, and a failure after that point
restores the previous bundle and relaunches the pet. (Do not reorder a check to sit after
`stop_pet`: that is the shape this already had once, where the failure mode was "kill the
pet, refuse, and end with nothing improved".) Second, if a run is killed between the two
renames the previous bundle is left under a fixed name next to it, which the following run
moves back before it cleans anything up. State these as properties; the primitives that
implement them are an implementation detail and have already changed once.

**Both arms run under the same lock object the in-app updater takes**, and that is the
only reason a manual transaction and an in-app update cannot swap the same bundle at once.
They used to be able to: each locked correctly, they just locked different things — the
script's own destination and repo-tree locks are known only to the script, while the
updater's lock is a `flock` on `~/Library/Caches/me.yeongyu.claudepet/update-<bundle>.lock`
(`_acquire_update_lock()`). The shell cannot hold that one: macOS has no `flock(1)`, and
re-opening it by name is exactly the unchecked open `_acquire_update_lock()` declines to
do. So Python holds the lock and the shell runs inside it as a child —
`claude_pet.py --with-update-lock <APP> -- <command>` — which is what `build_app.sh` wraps
around its internal `__install_txn` / `__update_txn` arms. Two things follow that a change
here must preserve:

- **There is exactly one lock order, outermost first: update-lock → txn → build.** Code
  that takes them the other way round deadlocks.
- **The wrapper owns exit statuses 100 and 101** — another updater holds the lock, and the
  lock site cannot be trusted, respectively. The inner arms must not use those two values
  for their own purposes, because nothing downstream could tell the two meanings apart.

**Both scripts take a subcommand, and anything else — including no argument — prints
usage and exits 1.** `build_app.sh` used to build on an unrecognised or absent argument,
and `build()` ends in `sign_app`, so a typo reached `codesign`. Do not restore either
fall-through; see [the sourceability note](#these-scripts-are-entry-points-not-libraries--source-runs-them).

`build_app.sh` signs with whatever identity is available (Developer ID if present, else
ad-hoc), so "unsigned and local" describes its *artifact's destination*, not its
mechanism — it is local because it installs to your own machine, not because it skips
`codesign`.

**[NEVER] run bare `./release.sh`.** **The ban is not about signing** — an authorized
release operator may run those same actions individually. It is that a combined command
destroys the per-step recording and stop-on-failure the authorization is conditioned on,
so it stays forbidden for everyone, operator included. Same ground as `all` and `ship`
below.

**The bare form no longer defaults to `all`** — with no argument the script now prints
usage and exits 1, the same as an unrecognized argument (`case "${1:-}"`, with `""|*)`
sharing the usage branch). It used to default to `all` and run build, sign, notarize,
universal and dmg from one wordless invocation. **The rule above stands anyway, and the
default must not be restored**: the prohibition is what keeps the steps separately
recorded, and a future edit that reinstates `${1:-all}` would silently re-arm a command
no rule would then forbid. A default that only serves a forbidden path is not a
convenience.

The subcommands are **not** uniformly forbidden. Four tiers, with full effects and the
exact conditions under [Release procedure](#release-procedure) step 3:

- **`build`** — unsigned local build. Ordinary work for development, run it freely. As
  *the release's* artifact build (step 3) it is still ordinary work by tag, but it sits in
  the execution phase and waits for the gate like everything else there.
- **`publish`** — **[ASK]**. Writes to the user's GitHub releases via their `gh` auth and
  performs no signing, so the user can authorize it, per-instance. It is not a bare upload:
  it runs the artifact gate first (see [Release procedure](#release-procedure) step 3) and
  uploads nothing if any check fails.
- **`sign`, `notarize`, `universal`, `dmg`** — **[ASK-OP]**. Each
  reaches a `codesign` or notarization step, so all three conditions apply: user
  authorization for this artifact, every §6 gate recorded first, and **[NEVER]** run by an
  agent that held any other role on this release — Developer, Verifier, Reviewer, or
  Coordinator.
- **`all`, `ship`, bare `./release.sh`** — **[NEVER]**, for everyone including the release
  operator. They collapse several gated steps into one invocation and destroy the per-step
  recording the authorization depends on. **`ship` is the worst**: it pushes a commit and
  tag to GitHub *before it builds anything*.

Read step 3 before invoking anything from `release.sh`.

### These scripts are entry points, not libraries — a guard is what keeps `source` inert

The prohibition above governs how the script is **invoked**. It does not cover the other
way in: loading the file by any mechanism runs the bottom of it, so **without a guard
`source ./release.sh` would execute the file** and reach the dispatch with no argument.
Both scripts now carry that guard, so **sourcing today returns before the dispatch and does
nothing** — that is the current behaviour, and the rest of this section is why it must stay.
Both scripts also answer a bare or unrecognized argument with usage and exit 1, but that is
**not** what makes sourcing safe — it is a second line of defence. `release.sh`
used to read `case "${1:-all}"`, so sourcing it meant `all` — build, sign, notarize,
universal, dmg — and `build_app.sh`'s `*)` used to run `build()`, which ends in `sign_app`.
Both of those actually happened. **The guard, not the default, is what makes sourcing
inert**: a default only helps while the dispatch has nothing dangerous to reach.

**Why it looks safe.** Sourcing reads as "import these functions" — which is exactly what
a test or a harness wants, and exactly what these files are not. Each **contains
reusable-looking functions but is not a library**: the functions are at the top, the
dispatch is at the bottom, and **without the guard, loading the file by any mechanism would
run that bottom.** `zsh -c 'source ./release.sh; f'` is the natural way to reach one helper
for a test, and before the guard existed that command would have started a release.

**Both scripts carry the guard** on the line immediately preceding the bottom `case`
dispatch in each file. **Locate it by that `case` block** — `grep -n ZSH_EVAL_CONTEXT`
finds it in one step. No line number is quoted here on purpose: line numbers in these
scripts drift as the files change, and a stale number sends the reader to the wrong
construct.

```sh
case "${ZSH_EVAL_CONTEXT}" in *:file*) return 0 ;; esac
```

**Do not replace this with the bash idiom.** These are `#!/bin/zsh` scripts, and
`(return 0 2>/dev/null)` — the usual bash sourced-detection — **inverts here**:

| | `ZSH_EVAL_CONTEXT` | `(return 0 2>/dev/null)` | the guard above |
| --- | --- | --- | --- |
| executed | `toplevel` | true → "sourced" ✗ | "executed" ✓ |
| sourced | `cmdarg:file` | true → "sourced" ✓ | "sourced" ✓ |

So the bash idiom reports *sourced* in both contexts, which does not fail loudly — it
**silently disables the dispatch**, and `./release.sh build` then does nothing while
looking correctly guarded. Verify any change to this line against real `zsh` in both
contexts; the obvious fix is the wrong one and it fails quietly.

**To confirm the dispatch is still reachable, pass an unrecognized argument** —
`./release.sh __guardcheck__` hits the `*)` usage branch and exits 1, exercising the same
`case` with no build and no signing. Never bare, and not `build` either: `build` is
ordinary work for development but it is not the cheap way to test a guard.

The general shape, which outlives this file: **anything that dispatches on load can be
entered without being invoked.** A rule that names forbidden commands protects the
commands it names. If a third script is added with a `case` at the bottom, it needs this
guard too.

---

## Testing policy: synthetic fixtures only

**Tests must never read the real `~/.claude` or `~/.codex` corpus.** `tests/test_log_estimate.py`
builds every fixture by hand, writes it into a `tempfile.TemporaryDirectory()`, and
points `claude_pet.LOG_DIRS` at that directory for the duration of the test (restoring
it via `addCleanup`). The Codex parser is tested the same way: `parse_codex_entries()`
takes `root=`, and `codex_sessions_root()` / `codex_auth_path()` take `env=` / `home=`, so
a test passes a temporary directory and never consults `$CODEX_HOME` or the real home.

The reason is not tidiness. A suite that reads live logs **passes or fails according to
how much agent traffic the developer happened to generate that day.** The same code
would go green on a quiet morning and red after a busy afternoon, and neither result
would be about the code. It is also the exact situation
[AGENTS.md §5](AGENTS.md#never-measure-a-corpus-your-own-session-is-writing) rules out —
an agent running this suite is itself writing to `~/.claude` while it runs (and a Codex
agent to `~/.codex/sessions`).

Any new test that needs a log shape adds a record to the `usage_record()` helper's
parameters. If a hypothesis genuinely requires the real corpus, that is an
investigation, not a test: do it in a scratch script, report it under the evidence
standard, and keep it out of `tests/`.

**[NEVER]** point `LOG_DIRS` at a real `~/.claude` path, or `parse_codex_entries()` at a real
`~/.codex/sessions`, from a test, and never copy real transcript content into a fixture
(see Privacy below).

---

## JSONL invariants

Claude Code writes newline-delimited JSON transcripts under the directories in
`LOG_DIRS` (`~/.claude/projects`, `~/.config/claude/projects`), discovered recursively
by `_iter_log_files()`. Nothing parsed from them is displayed any more — the pill's numbers
are server values — but **spike detection and the learned spike limits rest entirely on the
following properties of those files** (see [Spike detection](#spike-detection--logs-only-limits-learned-from-the-server)).
Each one has been the cause of a real miscount, and a miscount now shows up as a phantom or
missing spike alert rather than as a wrong percentage.

These are **correctness facts, not permission rules** — they carry no `[NEVER]`/`[ASK]`
tag (see [AGENTS.md §0](AGENTS.md#0-how-to-read-the-prohibitions)). "Wrong" here means
the number comes out incorrect, which no authorization can fix.

Invariants 1–6 are Claude Code's. Codex's session logs have a different shape and their
own four, numbered C1–C4 after them.

**1. Rows sharing `(message.id, requestId)` are streaming snapshots of ONE request.**
Claude Code writes a line per content block, so the same request appears several times,
each line carrying a *cumulative* usage object from a different point during streaming.

- **Keep the maximum.** `parse_usage_entries()` keeps the row with the largest weighted
  total. The comparison is `(total, ts) > (prev_total, prev_ts)`, so **among rows of
  equal weighted total the later timestamp wins** — see the tie-break note below.
- **Summing them is wrong** — that multiplies one request's cost by its block count.
- **Keeping the first is wrong** — the earliest line is the most partial snapshot, so
  first-wins systematically *undercounts*.
- **Keeping the last is wrong** — this is the one to watch for, because it is what you get
  from a plain `seen[key] = row` dict overwrite, which is the most natural way to write
  this loop and therefore the most likely accidental implementation. It is wrong because
  the final line for a request is not guaranteed to be the largest snapshot; nothing in
  the format promises the cumulative usage is monotonic across the lines as written.

**The tie-break is deliberate, and is not the same thing as last-wins.** Last-wins picks
the final row unconditionally; this code picks the largest row and only consults the
timestamp when two totals are exactly equal. Preferring the later row there is a
tiebreaker among equals, so it cannot undercount.

Because the tie-break branch only executes on exactly-equal totals, **no fixture built
from distinct values ever reaches it.** Covering it needs its own fixture: two rows with
identical weighted totals and different timestamps, asserting the later survives. See
[AGENTS.md §3](AGENTS.md#the-non-discriminating-test-hazard) before writing any fixture
for this invariant — the obvious ones test nothing, and that section works through this
exact case.

**2. Partial snapshots and `/subagents/` files.** Written in the three slots
[AGENTS.md §5](AGENTS.md#observations-and-invariants-are-different-claims--never-let-one-become-the-other)
requires, because the first is much weaker than the other two and an earlier version of
this entry stated it as a universal negative:

**Observed.** Every partial snapshot examined during the v0.19 investigation was in a
`*/subagents/*.jsonl` file; on the main transcripts the duplicate rows carried identical
usage, so first-wins and max-wins agreed there. **This is an observation, not a
measurement** — it was not quantified under §5, and no §5-conforming record of it exists
to cite. It says what that sample contained and nothing more.

**Therefore the code must** — and this does *not* follow from the observation, it follows
from the absence of any guarantee to the contrary — **handle partial snapshots regardless
of which file they came from. Path must never gate dedup behaviour.**
`parse_usage_entries()` applies the same max-wins rule to every record. Nothing in the
JSONL format promises partials cannot appear in a main transcript, and an observation is
not a source for an invariant.

Concretely, this is the change to refuse:

```python
if "/subagents/" in path:      # never do this
    dedup_carefully()
else:
    fast_path()
```

It would look documented, pass every existing test — the tests were built from the same
sample — and under-count silently the first time a partial appeared on a main transcript.
The observation above is not evidence for it.

**Therefore a validator must** — independently of whether the observation holds —
**include `*/subagents/*.jsonl` in any check of deduplication behaviour.** Validating
against main transcripts alone produces a **false all-clear**, because that is where the
bug is hardest to see. This instruction does not weaken if the observation turns out
false; it was never resting on it.

**3. Filter by record timestamp *before* consulting the dedup set.** `parse_usage_entries()`
parses the timestamp and applies `if ts < since: continue` *before* it looks the
`(message.id, requestId)` key up in `seen`. If the order were reversed, an out-of-window
row would claim the key first, and the in-window row for the same message would then be
dropped as a duplicate — silently deleting real usage from the window.

**4. Do not write down any relationship between the nested `cache_creation` fields and the
flat field. `_weigh_usage()` assumes none.** State it as the contract the code implements,
which holds for every input without appealing to what the logs have been seen to contain:

- The nested `ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens` are each weighed
  **independently**, at their own rates. Neither is derived from the flat field.
- A **positive** difference `flat − 5m − 1h` is weighed as an unclassified remainder at the
  5m rate.
- If the nested fields **exceed** the flat field, all of the nested weight is still kept and
  the remainder contributes **nothing** — it is clamped at zero, never negative.

So no arrangement of the three numbers can lose nested tokens or subtract from the total.

State it as two separate obligations, because writing down any relationship between the
fields is what makes one of them look removable. **The positive remainder term is
load-bearing whenever the flat field exceeds the nested fields this code knows about** —
if a future category is included in the flat field but carries no nested key this code
recognizes, the remainder is the only thing that still counts it. **The nested fields
are weighed independently even when they exceed the flat field** — that case adds no
remainder, and it removes nothing. Neither obligation depends on the two ever agreeing,
which is why neither can be dropped even if a sample happens to show agreement.

Older logs have no `cache_creation` dict at all; those weigh the flat field as a whole.

**5. Sidechain usage is real billed usage and is always included.** Rows with
`isSidechain: true`, and the nested `<session-id>/subagents/*.jsonl` files, are counted
like any other. Subagent tokens are billed; excluding them would understate usage by
however much of the work was delegated.

**6. The file-mtime check is a prefilter only.** `parse_usage_entries()` skips files
whose mtime predates `since` purely to avoid opening them. It is an optimization, not a
correctness boundary — **the per-record timestamp check is the real gate.** A file
touched recently can hold ancient records, so never treat "the file is recent" as
evidence that its records are in the window.

### Codex session logs

The Codex CLI writes `$CODEX_HOME/sessions/**/*.jsonl`, or `~/.codex/sessions/**/*.jsonl`
when `CODEX_HOME` is unset — `codex_sessions_root()`, the same root rule as
`codex_auth_path()`, on Windows too (`%CODEX_HOME%` or the profile's `.codex`).
`parse_codex_entries(since, root=None)` reads only lines of the shape
`{"type": "event_msg", "timestamp": ISO, "payload": {"type": "token_count", "info": {"last_token_usage": {...}, "total_token_usage": {...}}}}`
and returns `(timestamp, total, "codex", noncache)` tuples — the same shape as Claude's
entries, so `_burn_windows()` / `is_spike()` / `window_total()` serve both.

**C1. `info: null` is skipped.** Codex writes `token_count` events before anything has been
counted; such a line carries no usage and is not a zero-usage row.

**C2. Deduplicate on `total_token_usage.total_tokens`, within one file.** Codex sometimes
writes the same `token_count` event twice. Two events in **the same file** with the same
cumulative `total_tokens` are one event; the same value in a **different file** is a
different session and counts. An event without a usable `total_tokens` cannot be judged a
duplicate and is counted. The dedup set is per file — a global set would delete a second
session's first event whenever two sessions happened to reach the same running total.

**C3. Filter by record timestamp before consulting the dedup set** — the same reason as
invariant 3: an out-of-window event that claimed the key would delete the in-window one.
A line that cannot be weighed is likewise dropped *before* it can claim a key. The file
mtime is a prefilter only, as in invariant 6.

**C4. `reasoning_output_tokens` is not added.** The weight is taken from `last_token_usage`
at Claude's rates — `max(0, input_tokens − cached_input_tokens)` ×1, `cached_input_tokens`
×0.1, `cache_write_input_tokens` ×1.25, `output_tokens` ×5 — and `noncache` is that total
minus the cached term. Reasoning tokens appear to be included in `output_tokens`; that is
an **observation, not a guarantee**, so leaving them out is the conservative choice: adding
them would double-count if the observation holds, and the cost of being wrong the other way
is only a slightly higher learned limit. Any value that is not a finite non-negative number
drops the whole line, as in `_weigh_usage()`.

---

## User pets

`discover_pets()` lists the built-in cat plus every folder under `~/.claude_pet/pets/` that
`_is_pet_dir()` accepts, and it is called on every right-click and settings open, so a new folder
appears without a restart. Two rules are worth knowing: a folder that is not a pet itself is
searched **one level down** (`_nested_pet_dir()`), so a zip extracted as `pets/<name>/<name>/`
still works — the entry keeps `id = <name>` (outer folder) with `dir` pointing at the inner one,
exactly one candidate wins (or the one named like its parent), dot-folders and `__MACOSX`
(`_PET_JUNK_DIRS`) are ignored, inner symlinks are not followed, and two levels down is not
searched; and every text file the app reads or writes (`pet.json`, the pets README, the config,
the debug log) is opened with an explicit `encoding="utf-8"`, because the Windows default
(cp949) left a 0-byte README and would garble non-ASCII pet names — `_write_pets_readme()`
therefore also rewrites an empty README, and `run_gui()` calls it at startup.

## Seeding the bundled pets

`seed_bundled_pet_assets()` copies the app's own `.claude_pet/` tree into the user's
`~/.claude_pet/` on every launch, **missing-only**. It runs in `run_gui()` before the first
`discover_pets()`, so a pet it publishes appears in that same session's menu.

These are correctness-and-safety facts, not permission rules — "wrong" here means a user loses
data or ends up with a broken pet that no later launch can repair.

**1. Publishing is fail-closed. There is no degraded mode, and adding one is the trap.**
Files publish with `os.link`, directories with `renameatx_np(..., RENAME_EXCL)` — both refuse,
in the kernel, when the destination already exists. If a primitive is unavailable the seed
**reports an error and publishes nothing by that route**. It does not fall back.

**The property, stated so it survives a change of primitive: no *partial* artifact is ever
published — each README and each pet lands completely or not at all.** That is not the same
as "nothing is published", and the difference is user-visible: **"fail-closed" is not
all-or-nothing, because the two kinds fail independently.** Files need hardlinks; directories
need `RENAME_EXCL`, and those are separate filesystem capabilities. On a filesystem with the
first and not the second — an NFS-mounted home is the realistic case — **four `README*.md`
land and zero pets do.**

So anyone writing about this, in a comment or in a release note, must not say "the app
installs nothing": a user in exactly that state is looking at four new files sitting in
`~/.claude_pet/` and will conclude the warning is about somebody else. That sentence has
already shipped once and had to be corrected, and this is not hypothetical caution — it
reached a frozen release-notes draft, written by the people with the best model of the
system, because a log line read `4 copied` and nobody asked *which four*. Reproduce the
state with `mock.patch.object(claude_pet, "_RENAMEATX_NP", None)` before writing anything
about this case.

The change to refuse, in the shape it will actually arrive — someone reports "seeding doesn't
work on my NFS home", and this looks like a reasonable portability fix:

```python
if not os.path.lexists(dst):    # never do this
    os.rename(stage, dst)       # nor shutil.copytree, nor mkdir-then-populate
```

It is wrong for two independent reasons, and both have already been shipped and reverted here:

- **Check-then-act destroys the user's data in the window.** Between `lexists` and `rename`,
  a pet folder created by the user or another instance is silently replaced. A narrower window
  is not a fix — `renameatx_np` exists precisely because the check cannot be made safe.
- **Anything that creates the destination before the content is complete enshrines a partial
  pet.** `mkdir`-then-populate and `O_CREAT|O_EXCL`-then-write both fail here even though each
  claims the name atomically: a failure mid-write leaves a half-made pet, which invariant 2
  then protects forever.

The property that generalizes: **stage the complete artifact elsewhere, then publish it with a
primitive that cannot overwrite.** A pet that fails to appear is recoverable on the next launch;
one that is silently wrong or half-written is not.

**2. The whole-directory skip is load-bearing, and it is why the source is validated before
staging.** An existing `~/.claude_pet/pets/<id>` is skipped without being looked inside — that is
what protects a pet the user edited. The cost is that **anything published once is permanent**:
`_is_pet_dir()` accepts a directory on the strength of `pet.json` alone, so a pet missing its
sheet still lists in the menu and fails to load, and every later launch skips it as "already
there". Only a manual `rm -rf` clears it.

So `_seed_pets()` validates the **source** completely before staging: all three files present as
regular files (no symlinks), and `_bad_pet_metadata()` satisfied — parseable `pet.json`, `id`
matching the folder, and `spritesheetPath` exactly `BUNDLED_PET_SHEET`. Any failure means the pet
is **not staged at all** and the reason lands in `errors`. Read this as one rule rather than a
list, because the list will keep growing: **if anything about a bundled pet is not exactly as the
contract specifies, publish nothing and report it.**

**3. No path string survives the safe open.** The destination root is opened once with
`O_NOFOLLOW|O_DIRECTORY`, and everything after that — creating and opening `pets`, staging,
copying, publishing, cleanup — is `dir_fd`-relative. This is structural, not defensive:

- **A check is not a substitute for holding the fd — but one of the four `_same_dir()` calls
  is a gate, and it is not optional.** The call **immediately after the root is opened** is a
  **fail-closed write gate**: on mismatch it returns then and there and publishes nothing. A
  mismatch at that instant means the name was swapped as we opened it, so nothing that follows
  can be said to happen in the directory the user named. The other three — the one after `pets`
  is opened, and the two after seeding finishes — only append to `report["errors"]` and continue;
  by then the writes have already landed safely inside fds we hold, and the open question is not
  *safety* but *whether this is where the user expected it*. The source docstring states this
  split; do not flatten it back to "diagnostic only", because that phrasing invites the next
  reader to delete the first call as redundant, and it is carrying an irreversible early return.
- **What the fd buys you is that no *further* check is needed.** Re-validation added *after* the
  root gate is defeated by moving the swap one instruction later, which is exactly how this was
  found — that is why the three later calls report rather than gate.
- **An absolute path silently overrides `dir_fd`.** Passing a joined path alongside a `dir_fd`
  produces code that reads as fd-relative and is not. Pass bare component names.
- `tempfile.mkstemp`/`mkdtemp` and `shutil.copy2` take **no** `dir_fd`, which is why
  `_copy_into_fd()` stages through a private scratch and writes the destination through
  `os.open(..., dir_fd=...)`. That rewrite is the work; a conversion that leaves one of these
  call sites path-based reopens the whole hole while looking finished.

**Never write to `~/.claude_pet/` or `~/.claude_pet.json` from a test or a probe.** The user's
pets live there alongside the four stock ones. Seeding tests pass `source_root=` and `dest_root=`
and point both at `tempfile` directories.

---

## Start at sign-in

A checkable right-click item, `t("menu_autostart")`, between "Roam the screen" and "Reset size",
backed by `SMAppService.mainAppService()` (the `ServiceManagement` framework; the class exists on
macOS 13 and later). It lives in the menu and not in the settings panel because that panel is a
fixed-height view (see [Danger zone](#danger-zone)).

**There is no config key.** Nothing about this feature is read from or written to
`~/.claude_pet.json`, `RUNTIME`, `SETTINGS_OWNED_KEYS` or `apply_config`. The OS registration is
the only source of truth: the checkmark is re-read from `service.status()` every time the menu
opens, so a change the user makes in System Settings → General → Login Items shows as-is and is
never re-applied behind their back. Do not add a persisted preference and "reconcile" it at launch.

Four module-level functions carry the logic, so tests never reach the real registry:

- `autostart_state(status, is_bundle)` — `0 → "off"`, `1 → "on"`, `2 → "approval"`,
  `3 → "off"`; any other int → `"unavailable"`; `is_bundle` False → `"unavailable"` whatever
  the status. Pure. **`3` (`NotFound`) is `"off"`, not `"unavailable"`, and the first
  implementation got that wrong.** The SDK header describes `NotFound` as "an error occurred
  and no such service could be found", so the mapping merged at `794c66f` sent it to
  `"unavailable"` — and every fresh install then showed a disabled item that could not be
  turned on, observed on screen in the built bundle. The hardware finding (Coordinator,
  2026-09-13, macOS 26.5 / Darwin 25.5, a Developer-ID-signed bundle probed from its own
  interpreter — one machine, one probe): **a never-registered bundle reports `NotFound` and
  registers fine from it** (`register` returned `(True, None)` and the status then read `1`;
  `unregister` then returned `(True, None)` and it read `0`). Whether some other macOS
  reports `0` in that state is not settled by that sample, which is why `0` and `3` map to
  the same state rather than one being special. If a `3` ever is the header's error, the
  click now fails loudly through the `autostart_fail` alert instead of leaving an item that
  can never be turned on. `"unavailable"` remains the answer for a non-bundle, a `None`
  service (macOS 12 / framework missing), a `status()` that raises, and an int outside
  `0`–`3` — never offer register or unregister for a value nobody understands.
- `autostart_service()` — `SMAppService.mainAppService()`, or `None` when the framework cannot
  be imported or has no `SMAppService`. It imports the framework **at call time** (the same
  in-function import `app_bundle_path()` uses) and is the **only** call site of `mainAppService`.
  `autostart_current()` pairs it with `app_bundle_path()` into the `(service, is_bundle)` the
  two functions below take — `(None, False)` from source, so nothing there ever calls the
  service — and is the one place the menu and the handler both pick the service through.
- `autostart_toggle(service, is_bundle)` → `(new_state, "autostart_fail" | None)`. Off
  (status `0` or `3`) → `registerAndReturnError_(None)`, on → `unregisterAndReturnError_(None)`;
  the new state is
  **read back** from the service afterwards because a register can land on `2`. From `2` nothing
  is called and `("approval", None)` comes back — the handler shows the `autostart_approval`
  alert, whose default button calls `SMAppService.openSystemSettingsLoginItems()`. A
  `(False, err)` leaves the state unchanged. Not a bundle, or `service is None` →
  `("unavailable", None)` **without touching the service, `status()` included** — from source
  `mainAppService()` is Python.app's own service, not ours. (From `2`, and on a failure,
  `status()` has still been read; it is register/unregister that is not called.)
- `uninstall_autostart(service)` → `"autostart_fail" | None`. Unregisters only when the status
  is `1` or `2`; `None` makes no call at all, and `0` / `3` read `status()` and stop there.
  `do_uninstall()` calls it **after** the update lock is held and **before** the deletion shell
  is spawned, only for an installed bundle, and a failure refuses the whole uninstall with
  nothing deleted — the state this avoids is a login item pointing at a bundle that no longer
  exists.

In the menu, `"unavailable"` (from source, or no `SMAppService`) shows the item disabled with the
`autostart_unavailable` title; `"approval"` shows the mixed state (`-1`). `rightMouseDown_` does
not call these functions by name: it reads `state["autostart_read"]`, a hook installed in the
`state` dict as `lambda: autostart_read_state(*autostart_current())`, and treats a missing hook
as `"unavailable"`. That is the same shape as `roam_interrupt` / `roam_release` — the `state`
comment says why: the view's methods are executed in window-less tests with a hand-built
`state`, and a hook that is simply absent there keeps every such test's scope stable when an
item gains an OS-backed collaborator. Do not reach for the module-level functions from
`rightMouseDown_` directly; put new collaborators of a view method behind a `state` hook. The
handler, `Handler.toggleAutostart_`, calls `autostart_toggle(*autostart_current())` by name —
that one is pinned by the AST test. `setup.py` lists
`ServiceManagement` in the py2app `includes` — without it the bundle's item is permanently
unavailable while the from-source run works, which is the failure `tests/test_autostart.py`
pins. Six TR keys in en/ko/ja/es: `menu_autostart`, `autostart_title`, `autostart_approval`,
`autostart_open_settings`, `autostart_fail`, `autostart_unavailable`.

**[NEVER]** call `registerAndReturnError_` / `unregisterAndReturnError_` on the real service from
a test or a probe, and never call `mainAppService()` from a test. `tests/test_autostart.py` passes
fake service objects and installs a tripwire in `sys.modules["ServiceManagement"]` whose register
and unregister raise; a from-source run is never a bundle, so `autostart_current()` hands the
helpers `(None, False)` and nothing there consults the real service at all.

---

## Cost weighting

`_weigh_usage(usage)` converts a Claude Code usage object into a **cost-weighted** number,
using weights proportional to API list pricing. (`_weigh_codex_usage()` applies the same
rates to Codex's `last_token_usage` — invariant C4.) Nothing weighted here is displayed;
the weighted numbers feed spike detection and the learned spike limits only.

| Token kind | Weight |
| --- | --- |
| `input_tokens` | ×1 |
| `output_tokens` | ×5 |
| cache write, 5-minute TTL (`ephemeral_5m_input_tokens`) | ×1.25 |
| cache write, 1-hour TTL (`ephemeral_1h_input_tokens`) | ×2.0 |
| cache write, unclassified remainder (`flat − 5m − 1h`, when the nested dict is present but does not account for the whole flat field) | ×1.25 |
| cache write, flat field with no nested `cache_creation` dict at all (legacy logs) | ×1.25 |
| `cache_read_input_tokens` | ×0.1 |

The TTL split is only taken when `usage["cache_creation"]` is a dict. Otherwise the flat
`cache_creation_input_tokens` is weighted ×1.25 as a whole. The remainder term exists so
that a nested dict which does not sum to the flat field cannot silently drop tokens; it
is clamped at zero, so a nested sum larger than the flat field contributes no negative.

It returns `(total, noncache)` where `noncache` excludes the cache-read term — or **`None`
when the row's numbers are unusable**. Read the following as examples, **not** as a closed
list — the guard is "unusable", and enumerating cases here invites someone to implement the
enumeration instead: a value that is not a real number (a string, or a `bool`, since `True`
is an `int` in Python), one that is `nan`/`inf`, a negative count, an integer too large to
convert to a float, or a value that only overflows once it has been multiplied by its
weight. Claude Code writes these files
and we only read them, so a malformed row is a case to handle, not an impossibility — one such
row used to raise `TypeError` out of the multiply and kill the whole aggregation.
`parse_usage_entries()` skips a `None` row **before** it consults the dedup set, so the bad row
cannot claim a `(message.id, requestId)` key and delete the good row for the same message.
An absent field is still `0`, not a skip.
`noncache` is what spike detection uses — cache reads are large and constant enough that
including them produced false spike alerts.

**The weighted total is a cost-weighted quantity, not a raw token count.** Do not
display it as "tokens used", do not compare it against a raw token figure from another
tool, and do not "simplify" it back to a sum of token counts. Weighting is what keeps a
learned spike limit stable when the user's cache-hit ratio changes: the limit is
`weighted total ÷ server %`, and the server's percentage tracks cost, so an unweighted total
would make the learned limit — and therefore the spike floor — drift with usage pattern even
at constant real cost.

---

## Spike detection — logs only, limits learned from the server

**The app shows no log-derived number.** Since 2026-10-05 ("추정 로그치 적는건 이제 없애자!!
기능도 없애고") every percentage on the pill is a server value, and with no server value the
pill shows a status instead. `compute_usage()` no longer produces gauges: it returns a spike
snapshot — `burn_5m`, `burn_5m_opus`, `spikes`, `model_kw`, `last_activity`, `entries` (a
count), `rows` (the parsed entries, which the refresh worker pops after learning) and `now`.
Do not reintroduce session/weekly/per-model percentages, limits, resets or a "≈" line from
it. The 5-hour tiled session blocks, the configured-weekday weekly window
(`_weekly_window_start`) and the model-keyword setting went with the gauges.

What the logs still do is say "you are suddenly using much more than a moment ago", for
**both providers**:

- **Claude Code** — `parse_usage_entries(now − 7 days)` (the JSONL invariants above), lanes
  `session`, `weekly` and `opus` (`claude_spikes()`). `opus` is the historical key of the
  per-model lane: its entries are those whose lowercased model string contains `model_kw`,
  which comes from the server's per-model row label (`model_keyword_from_rows()`), and only
  when there is none from `_detect_model_keyword()` over `PREMIUM_FAMILIES = ["fable",
  "mythos", "opus"]`, newest first, falling back to `"opus"`.
- **Codex** — `parse_codex_entries(now − 7 days)` (invariants C1–C4), lanes `codex_session`
  and `codex_weekly` (`codex_spikes()`). The refresh worker reads these files only while
  Codex is shown and not in API mode, and only once there are Codex server rows or a learned
  Codex limit — a user who does not use Codex costs nothing.

### Spike windows

Every lane uses the same two windows over its entries (`_burn_windows()`): the **last 5
minutes** of `noncache` (cache reads excluded — they are large and constant enough to cause
false alerts) against a baseline built from the **preceding 25 minutes**, split into five
5-minute buckets. Only buckets with activity are averaged — including idle zeros would drag
the baseline below real activity and make the 2.5× gate fire during ordinary use.
`is_spike(burn, base, limit, base_pct, mult)` fires when `burn ≥ limit × base_pct × mult /
100` **and** `burn ≥ SPIKE_GATE (2.5) × max(base, floor / 5)`. `SPIKE_BASE` is 2.0 % for the
session lanes and the per-model lane, 0.5 % for the weekly lanes; `mult` is the
sensitivity setting (`spike_mult`: 0.5 / 1 / 2).

### Learned limits

The `limit` in that floor is **learned, never typed**. `learn_server_limits()` runs on every
refresh (and in `--report`) and, for each lane whose server row carries a reset time `R`,
computes `T = window_total(entries, R, W)` — the **total** weighted usage (not `noncache`:
the server's percentage looks cost-based) since `R − W` — and learns
`limit = T ÷ (p / 100)` through `learn_limit()`, smoothed against the previous value by an
exponential moving average (`LEARN_ALPHA = 0.3`). `W` is 5 h / 7 d / 7 d for Claude
session / weekly / per-model (`CLAUDE_LANE_WINDOWS`), and for Codex the server's
`limit_window_seconds` (`codex_window_seconds()`, falling back to `CODEX_LANE_WINDOWS`).

- **Nothing is learned below `LEARN_MIN_PCT = 5` %, or from `T = 0`** — a tiny denominator
  makes the quotient explode, and a zero limit would make every burn a spike.
- **A lane with no learned limit never spikes** (`is_spike` returns False for a missing
  limit). The old default limits (8M / 60M / 15M) were unsourced guesses and are gone; no
  alert beats a wrong alert. `learn_lane()` creates no key when there is nothing to learn,
  and that absence is what carries the rule.
- `LEARNED_LIMITS` lives **in memory only**, outside `RUNTIME`, and is never saved — putting
  it in `RUNTIME` would let a settings save write it to disk and resurrect the removed limit
  keys. A restart starts unlearned, so spikes are off until the first refresh with a server
  row at ≥ 5 %.
- **API mode switches a provider's spikes off, per provider** (`provider_spiking()` checks
  `mode` for Claude and `codex_mode` for Codex). Claude in API mode does not silence Codex.

## Where the numbers come from

Every number on the pill comes from a server, per provider and per data source:

- **Claude Code, subscription** (`mode = "sub"`) — `fetch_exact_usage()`, backed by the
  OAuth token. The server returns percentages it computed itself, and they are shown
  verbatim. `_read_oauth_token()` tries three sources in a deliberate order — credentials
  **file**, then the `security` **CLI**, then the **native** Keychain API — because only the
  last one can raise a Keychain prompt, and a background `LSUIElement` app that cannot show
  UI dies silently on it (`-25308`). Do not reorder these.
- **Claude Code, API cost** (`mode = "api"`) — `fetch_api_cost_today()` /
  `fetch_api_cost_month()` against the Anthropic Admin API with `admin_key`.
- **Codex, subscription** (`codex_mode = "sub"`) — `fetch_codex_usage()`, the
  `chatgpt.com/backend-api/wham/usage` endpoint with the token from Codex's own `auth.json`
  (`codex_auth_path()`), read only — refreshing it is the Codex CLI's job, and there is no
  Codex token auto-recovery. When Codex is shown, not in API mode, has no token **and is in
  use on this machine** — the CLI is found (→ sign in) or, without a CLI, the Codex home
  (`codex_home_exists()`: `$CODEX_HOME`, else `~/.codex`) exists (→ install) —
  `compute_codex_onboard_state()` puts **Install Codex…** / **Sign in to Codex…**
  (`menu_install_codex` / `menu_login_codex`) at the top of the right-click menu, under the
  Claude Code item: on macOS `start_codex_install()` / `start_codex_login()` open Terminal
  with `npm install -g @openai/codex` / `codex login`, on Windows `_install_codex` /
  `_login_codex` open a new PowerShell console like `_install_claude` / `_login_claude`.
  With neither a CLI nor a Codex home nothing is offered, so a user who has never used
  Codex sees no Codex item at all.
- **Codex, API cost** (`codex_mode = "api"`) — `fetch_codex_cost_today()` /
  `fetch_codex_cost_month()`: `GET https://api.openai.com/v1/organization/costs` with
  `Authorization: Bearer <openai_admin_key>`, summing `data[].results[].amount.value` across
  `has_more` / `next_page` pages. Failures land in `CODEX_API_STATUS["last_error"]` with the
  same vocabulary as `API_STATUS` and are split by the same `api_error_kind()` (401/403 →
  key rejected, anything else — including running into `CODEX_COST_MAX_PAGES` with pages
  left, which returns None rather than a truncated sum — → unreachable). "Today" and "this
  month" start at **UTC** midnight and the **UTC** 1st, for both providers, because the
  Anthropic and OpenAI cost APIs bucket by UTC day; a local-midnight start would cut a
  bucket in half.

Both Admin keys (`admin_key`, `openai_admin_key`) are stored in plain text in
`~/.claude_pet.json`, and the debug log carries status codes and exception class names
only, never key bytes.

**There is no fallback to the logs.** With no server value the pill shows a status:
`token_expired` when the server rejected the OAuth token (401/403 — whatever the logs
hold), onboarding (`onb_install` / `onb_login`) when there is no Claude OAuth token,
`loading` / `scanning` while waiting for the first answer, `no_providers` when both
providers are hidden. The JSONL logs feed spike detection only (above).

**Onboarding is decided by the token, not by the logs.** `compute_onboard_state(oauth,
has_token)` returns None in API mode, when there are server rows, or when a Claude OAuth
token exists — a token without rows is an outage, and telling that user to sign in would be
false. Otherwise it returns `"login"` when the `claude` CLI is found and `"install"` when it
is not, **even if recent logs exist** (logs say nothing about whether the numbers can be
fetched). Both refresh paths pass `has_token=claude_token_present()`, which looks only at
the already-cached token and the credentials file — never the Keychain API, which could
prompt on a 30-second timer. The refresh fetches usage first, so a Keychain user's token is
already cached by then.

**`learn_server_limits()` learns once per server reading.** The refresh runs every 30 s but
the OAuth and Codex responses are cached for 180 s, so the worker passes
`claude_fetch=_oauth_cache["t"]` and `codex_fetch=_codex_cache["t"]`; a provider whose key
equals the one recorded at its last learning is skipped, and the EMA is not re-applied to a
cached row. `None` (as `--report` passes) always learns. With no server rows at all,
`--report` prints `r_no_server_rows`.

**The token cache is source-aware and re-validates without prompting.** `_oauth_token_cache`
records where the token came from (`src`: `file`, `cli`, `native`), the credentials file's
`(st_mtime_ns, st_size, st_ino)` signature when it came from the file (`file_sig`;
`_credentials_path()` / `_credentials_sig()`), and a `suspect` flag. A file-sourced token is
re-checked against that signature on every read: a changed or vanished file drops the cached
token and reads afresh, which is how a rotated `~/.claude/.credentials.json` is picked up
without a restart — and the only rotation signal the Windows port has, since the file is its
only source there. A fetch that fails for any reason other than 401/403 — 5xx, 429, a network
error, an unparseable body — keeps the token but marks it `suspect`; the next read re-validates
through **prompt-free sources only** (the file, then the `security` CLI if the token came from
the CLI) and never enters the native Keychain reader, which is the one path that can prompt. A
replacement token replaces the cache; none keeps the cached one; `suspect` clears either way.
A 401/403 still runs the forced walk (which may reach the native reader once, unless the user
declined); if that walk finds nothing, the dead token is **cleared** rather than re-served
during the cooldown, and `OAUTH_STATUS["auth_error"]` is set. `OAUTH_STATUS["last_error"]`
records the class of the last failure (`http:<code>`, `net`, `parse`; `None` after a success)
and is not rendered — the pill's memo key is unchanged. `fetch_exact_usage()` caches a failed
fetch for `OAUTH_FAIL_RETRY_SEC` (60 s) instead of `OAUTH_CACHE_SEC` (180 s), **except** after
`http:429`, which keeps the full 180 s because avoiding over-calling is why the cache exists.
The `_dbg` lines on this path carry status codes, exception class names and booleans only —
never token bytes.

### The `claude -p /usage` CLI fallback is opt-in and OFF by default

`_fetch_cli_usage()` returns `None` immediately unless `CLAUDE_PET_USE_CLI=1` is set in
the environment. **It does not run for ordinary users**, so do not describe the Claude subscription data source as
"OAuth, falling back to the CLI" without that qualifier.

The reason is in its docstring: the `claude` CLI launches the whole Claude Code Node app
as a child process, which scans the home directory, project directories, and other
folders. macOS attributes that access to the **parent** — ClaudePet — which then triggers
protected-folder prompts (Downloads, Photos, network volumes). Since OAuth already
supplies session, weekly, per-model, and credit rows, the CLI buys nothing and costs a
wall of permission dialogs. Leave it off.

### Token auto-recovery runs the CLI detached, in a private folder, once per attempt

Token auto-recovery (`recovery_tick` → `run_token_refresh`, both platforms) and, on macOS
only, the pill's login click (`start_claude_login_background`) run the `claude` CLI by
default, and **both go through `_run_refresh_job`, which never makes the CLI our child**.
Recovery is the Windows port's only use of `_run_refresh_job`. The other ways the CLI runs:
the opt-in `_fetch_cli_usage()` above (both platforms, same environment variable), and
user-visible console paths — on macOS the Terminal paths `start_claude_login` /
`start_claude_install`, on Windows the context-menu items `_login_claude` / `_install_claude`
in `windows/claude_pet_win.py`, which run it in a new PowerShell console.
`recovery_spawn_argv` / `login_spawn_argv` return only the program the job runs — on macOS its
`argv[0]` is the CLI itself, which is fine: detachment is a property of `_run_refresh_job`,
not of an argv's shape.

- **macOS** — a one-shot launchd job: `_launchd_job_spec()` written as a plist and
  bootstrapped into `gui/<uid>`, with `WorkingDirectory = recovery_cli_cwd()` and `KeepAlive`
  false. `_launchctl_bootout()` runs before (a stale job with the same label — v0.26's, after
  an update — makes `bootstrap` fail) and after. `clear_stale_launchd_jobs()`, started once by
  `run_gui()` on a daemon thread, also boots out both labels at launch — the recovery one only
  when no attempt holds `_recovery_busy` — so a v0.26 job orphaned by an update or a quit
  mid-attempt does not wait for the next attempt to be cleared.
- **Windows** (recovery only) — WMI `Win32_Process.Create` (`_win_wmi_create`) with
  `CurrentDirectory = recovery_cli_cwd()` and `ProcessStartupInformation =
  Win32_ProcessStartup{ShowWindow=0}`.

Three changes to refuse:

- **`launchctl submit`.** It has no working-directory option (launchctl(1)), so the CLI
  started in `/`, and launchd keeps re-running the job (observed below). v0.26 shipped it.
- **Starting the CLI in `/`, the home directory, or wherever the app happens to be** (the
  installed bundle's own working directory is its `Contents/Resources`). Always
  `recovery_cli_cwd()`.
- **`CreateFlags` = `CREATE_NO_WINDOW` (0x08000000) on the WMI call**, added "to be safe": WMI
  rejects it with ReturnValue 21 and nothing spawns. `_spawn_no_window_flags()` is for our
  own helper subprocesses only.

**Observed** — scoped samples, not invariants:

- 2026-09-30, one Mac, Claude Code CLI 2.1.284, launched by launchd with the token hours from
  expiry: started in `/`, it tried to read `~/Music`, `~/Pictures`, `/Volumes`, `/home` and a
  path under `~/Documents` within 5 s. Started in a private folder it requested no protected
  location — four runs with the TCC log checked: three in an empty folder (a scratch folder
  once, the app's own `cli` folder twice) and one in a non-empty scratch folder; the only TCC
  request in those windows was a non-prompting `DeveloperTool` preflight by `syspolicyd`, in
  one run. (That `/` run was sandboxed with every service already granted, so it could not
  prompt.) The prompts that did appear came from v0.26's own recovery jobs, which also ran the
  CLI in `/`: the tccd log for 05:28–06:52 holds 14 `AUTHREQ_PROMPTING` lines from 7 PIDs of
  the token-refresh job (CLI 2.1.284). TCC attributed them to the CLI itself and keyed them to
  its **versioned install path** — this Mac holds separate rows for four versions (2.1.271,
  2.1.278, 2.1.283, 2.1.284) — so an answer for one version did not carry to the next. Hence
  the fix is to not trigger the reads, not to get the user to answer once.
- Same day, same Mac: launchd re-ran `submit` jobs after a clean `exit(0)`, although
  launchctl(1) says only "in the event of failure" — one logged v0.26 attempt spawned the CLI
  three times, and a probe `submit` of `/usr/bin/true` ran three times in 24 s.
- One Windows 11 machine (10.0.26200), Windows Terminal as the default terminal: without
  `ShowWindow=0` a visible terminal window appeared for the CLI's run in 5/5 spawns; with it,
  0/2.
- Not observed: a private-folder run that actually refreshes the token (it cannot be forced),
  other CLI versions, other Windows versions or default terminals, and the login shape through
  `_run_refresh_job` (macOS only — the Windows port never takes it). The full record is in
  `_win_wmi_create` and the comment block above `REFRESH_MARGIN_SEC`.

**To see what a process touches without prompting anyone:** a `sandbox-exec` deny on a path
short-circuits TCC (a sandboxed `ls ~/Downloads` made no `tccd` request; the same `ls`
unsandboxed did), so deny the protected locations and read the kernel's `Sandbox: … deny` log
lines.

### Timing: what recomputes when

Two `NSTimer`s are registered on the same `Ticker` object, and conflating them is the
usual source of wrong statements about this app:

| Timer | Interval | What it does |
| --- | --- | --- |
| `tick:` | `TICK = 0.05` (20 Hz) | **Renders only.** `tick_()` reads `state["stats"]`, picks a mood, advances the animation frame. It never calls `compute_usage()`. |
| `refresh:` | `REFRESH_SEC = 30` | Spawns a daemon thread whose `work()` calls `fetch_exact_usage()` and `fetch_codex_usage()`, then `compute_usage()` (the Claude spike snapshot) and, when Codex is shown, `parse_codex_entries()`; then `learn_server_limits()`, `claude_spikes()` / `codex_spikes()`, the cost calls for whichever provider is in API mode, `compute_codex_onboard_state()`, and finally sets `state["repaint"]`. |

So: **server values and the spike snapshot are refreshed once per 30 seconds on a background
thread; the 20 Hz tick only renders the last result.** The refresh also runs on two one-off
paths — a priming `refresh_(None)` at startup and a manual refresh on double-click — and a
settings save starts one. Saving settings itself reads no logs (there is no limit to
back-solve any more). The Windows port's `PetWindow.refresh()` runs the same sequence on a
`QTimer` and hands the result to the GUI thread through `_apply_pending()`.

When this document or a changelog says "the previous tick" — for instance in the
session-reset jump below — it means **the previous 30-second refresh**, not the
previous animation frame. The distinction matters: across 16 ms nothing changes, while
across 30 s a session boundary can pass.

### The pill is one summary line per provider, and where the logs still reach it

Since v0.24 the pet carries **one** pill, drawn by `draw_summary_pill()` from
`roam_summary()` / `roam_summary_runs()`: a first line such as `세션 42% · 주간 17% ·
Fable 12%` and, when any gauge has a reset time, a smaller second line with the reset
times (`리셋 세션 3시간 43분 후 · 주간 2일 4시간 후` — the reset word once, then `<label> <countdown>`,
consecutive duplicate countdowns collapsed).
There are no gauge bars and no mode/version status line any more — the user unified the
display on the roaming summary ("그거로 통일하자", 2026-09-12). `full` and `summary` in
`RoamDisplay` are the **same pill**; they differ only in what switched it on (the user's
`show_panel` preference vs. the arrival latch), and `folded` is pet-only. The pill is
`SUMMARY_H` tall with one line and `SUMMARY_H2` with two; `pill_h()` is the two-line strip
the logical window reserves.

What a provider's line contains is decided by pure functions: `roam_summary()` for Claude
Code and `codex_summary_segment()` (→ `roam_summary_codex()` / `roam_summary_codex_cost()`)
for Codex. Each returns one `(kind, payload)` segment or nothing:

| kind | when | line |
| --- | --- | --- |
| `exact` | server rows exist for that provider | the chosen gauge rows, server labels verbatim, values in emerald |
| `cost` | that provider is in API mode with its Admin key and a cost | today's cost, then this month's when known (`/ $budget` when a budget is set) |
| `status` | otherwise | one translated status key — `token_expired`, `onb_install` / `onb_login`, `scanning` / `loading`, `need_admin_key` / `api_key_rejected` / `api_unreachable`, and for Codex `codex_need_admin_key` / `codex_api_key_rejected` / `codex_api_unreachable` |

**There is no `estimate` kind.** `SUMMARY_APPROX` (`≈`), `SUMMARY_COLORS["estimate"]`
(amber) and the trailing `⚠` the adapter used to append after a token rejection were all
removed on 2026-10-05. A rejected token now reads `token_expired` whatever the logs hold.

**The user's choices filter the rows, in the adapter.** `provider_shown(runtime, provider)`
is `show_claude` / `show_codex` **and** at least one chosen gauge — a provider with no gauge
ticked is the same as a hidden one. Hand-edited values are coerced (`config_bool()`,
`provider_gauges()`, and `apply_config()` stores the result): `"false"`, `"0"`, `"no"`, `0`
and `False` mean off, and a `*_gauges` value that is not a list falls back to the default
rather than hiding the provider. Claude rows are classified by `claude_gauge_class()`
(from `_label_order`: 0 session, 1 weekly, 9 credit, anything else — 2 for a family row,
5 for an unrecognised server window — is per-model) and filtered by `filter_claude_rows()`
against `claude_gauges`; Codex rows (`codex_session` / `codex_weekly`) by
`filter_codex_rows()` against `codex_gauges`. Rows not chosen are hidden, and so are their
resets. `roam_summary()` still takes only the first `SUMMARY_GAUGE_ROWS` gauge rows by
position, while a credit row passes outside that cap (with `credit_text` in money mode).
Both providers hidden gives the single status `no_providers`, whose click opens Settings.

**Colour carries two things, on two different runs.** The *value* run says where the
number came from: `SUMMARY_COLORS["exact"]` is emerald (server percentages) and API cost
amounts are coral. The *label* run (session/weekly/model, today/this month) is white
(`"value"`) and turns `"warn"` at 50 % and `"bad"` at 85 % — `summary_value_kind()` — or
`"bad"` outright when that provider is spiking, in which case the label is also prefixed
with `SUMMARY_SPIKE` (`▲`). (The user first asked for the opposite assignment and then
swapped it the same day: "텍스트랑 수치랑 색을 반대로 하자".) The second line is `"sub"` (the
dim text colour). In API mode the line is `오늘 $x · 이번 달 $y / $budget` with the words
"이번 달" coloured by this month's share of the budget. `roam_summary()` stays pure: the
adapter pre-formats reset times with `fmt_countdown()` and passes them in (`row[2]`), and
passes `spike_first` and `credit_text`. The adapter, `roam_summary_text()`, memoises its
result per input and 5-second window because it runs on every 20 Hz tick while the pill is
visible.

**Runs are the extension point.** `roam_summary_runs(segments, t)` turns a list of
segments into two run lists, `(main, sub)`, each `[(text, kind), ...]`; the renderer draws
each run in its kind's colour and `roam_fit_runs()` trims a line from the end when it
exceeds the pill. Adding another
provider (GPT, Gemini) means appending a segment — no drawing code changes.

**Font.** The line is set in the bundled Pretendard SemiBold (`fonts/`, OFL 1.1). Inside
the app bundle `ATSApplicationFontsPath` registers it; from source, `run_gui()` registers
it with CoreText. If neither works the summary falls back to the system monospaced font.
The Windows port on the `windows` branch is meant to load the same file through Qt so the two
platforms draw identical glyphs; nothing in this tree depends on that.

**Where the logs still reach the screen.** The numbers are server values, but three visible
paths are driven by the log-based spike signal (and, for path 3, by nothing from the logs
at all). Re-derive this list from the source before relying on it — it has been wrong
before, including once in v0.24's own draft.

1. **A provider's session label turns red with ▲ — inside the pill itself.** For Claude the
   adapter passes `spike_first=provider_spiking(stats, "claude")`, `roam_summary()` marks
   the first row (never a credit row), and `_summary_segment_runs()` prefixes that label with `SUMMARY_SPIKE` and
   colours it `"bad"`; Codex gets the same through `codex_summary_segment(..., spiking=
   provider_spiking(stats, "codex"))`. The value beside it is untouched and still emerald.
   Note the asymmetry: a weekly or per-model spike of a provider marks **that provider's
   first (session) label** — and never the other provider's.
2. **Spike → the pet, and it outranks the server.** `current_mood()` consults
   `spike_info(state["stats"])` — true when a *shown* provider is spiking — and returns
   `"failed"` *before* it reaches `mood_for(None, rows, codex_rows=...)`, which derives a
   mood from the highest server percentage among the **shown providers' selected gauges**
   only (each provider's rows filtered by its own gauge choice; credits excluded; no server
   rows → `"idle"`, never a mood from the logs). So a false spike overrides a perfectly good server
   reading. Four further effects hang off that same signal: `tick_()` forces a repaint for
   as long as a spike is live; the pet is tinted by a pulsing spike-coloured overlay that
   exists on no other path; the **mouse-proximity greeting is suppressed**, since its guard
   includes `not spike_info(state["stats"])`; and `roam_tick()` folds a live spike into
   `busy`, so the pet neither sets out on a walk nor keeps its arrival latch while a spike
   shows. A spike of a hidden provider moves none of this — there would be no ▲ on screen
   to explain it.
3. **The session-reset jump uses server values.** `session_reset_jump(prev_claude, claude,
   prev_codex, codex)` compares the previous refresh's server session row with this one —
   Claude's `_label_order` 0 row and Codex's `codex_session` row, each on its own — and the
   pet jumps once when either crosses from above 5 % to below 1 %. No log percentage is
   involved, and it has no mode guard: it fires in API mode too whenever server rows exist.

**API mode is per provider.** `provider_spiking()` returns False for Claude when `mode ==
"api"` and for Codex when `codex_mode == "api"`, so paths 1 and 2 go quiet for that
provider only. Path 3 is unaffected.

The practical consequence: a parsing, weighting or learning regression shows up as an
alarmed, tinted pet, or as an alert that never comes — never as wrong numbers on the pill,
whose values are server-derived and drawn emerald.

---

## Danger zone

Two things make changes to spike detection and to the settings panel higher-risk than they
look.

**1. The learned limits are only meaningful relative to the parser that produced them.**
There are no limit constants any more. The old `session_limit` / `weekly_limit` /
`opus_limit` defaults (8M / 60M / 15M) were never officially published, and they are gone
together with their `CLAUDE_PET_*_LIMIT` / `CLAUDE_PET_MODEL` environment variables; the code
reads none of them. Each lane's limit is `weighted log total ÷ server %` for the same window
(`learn_server_limits()`, see [Learned limits](#learned-limits)). That makes the limit, and
with it the spike floor, a function of everything the JSONL invariants and the cost weights
govern:

- Any change to parsing, deduplication, weighting or the window arithmetic moves `T`, so the
  learned limit moves with it and every alert threshold shifts. Because nothing is
  persisted, it re-learns within a refresh or two. A systematic bias, though — a parser
  that double-counts, say — is learned *into* the limit: the floor scales with it while the
  burn it is compared against may not, so a broken parser can produce alerts that look
  plausible and still be wrong. Test the parser, not the alerts.
- The learning is an inference, not a fact. It assumes the server's percentage tracks the
  same cost-weighted quantity, over the same window, that the local logs record. Where that
  is false, the learned limit is too small or too large and alerts come early or late:
  usage from another machine that these logs never saw, a server window that does not start
  at `R − W`, a Codex window length the server did not report. The `p ≥ 5` and `T > 0`
  gates and the EMA bound the damage; they do not remove it. Do not present a learned limit
  as "your limit" anywhere in the UI.
- A provider whose server rows never carry a reset time, or never reach 5 %, never gets a
  limit and so never spikes. That is the intended failure mode — no alert beats a wrong
  alert — and it must not be "fixed" by putting a default limit back.

**2. The settings panel is a fixed-height view with hand-placed coordinates.** It has two
provider sections of the same shape — `s_sec_claude` and `s_sec_codex`, each with
`s_show_in_pill` (`show_claude` / `show_codex`), a data-source popup (`mode` /
`codex_mode`), gauge checkboxes (`claude_gauges` over `CLAUDE_GAUGES` in a 2 × 2 grid,
`codex_gauges` over `CODEX_GAUGES`), the Admin key (`admin_key` / `openai_admin_key`) and
the monthly budget (`api_budget` / `codex_budget`). Spike sensitivity and the greeting come
next, then Save and the version label. The Windows `SettingsDialog` copies the same
coordinates (Qt flips y), the same keys and the same `PHT`.

**The content height is 568 and must stay ≤ 656.** The minimum supported screen is
1366×768, which leaves roughly 673 points once the menu bar and Dock are removed. An
earlier version reserved space for hidden fields and reached 732, pushing Save and the
title bar off a 768-tall screen. Every widget is placed by hand, so adding a row means
recomputing every widget below it.

The following are gone, with their TR keys: the calibration fields, the absolute-limit
fields, the advanced-limits window (`open_advanced_limits()` and Windows
`AdvancedLimitsDialog`), the weekly reset weekday and hour, and the model-keyword field.
**The old keys are neither read nor deleted.** `session_limit`, `weekly_limit`,
`opus_limit`, `model_keyword`, `weekly_reset_day` and `weekly_reset_hour` are not in
`SETTINGS_OWNED_KEYS` or `_RUNTIME_CONFIG_KEYS`. So `apply_config()` never loads them, and
`merge_config_updates()` leaves them on disk untouched — a user's file is not rewritten
behind their back.

**The save is still one transaction.** It runs `plan_settings_save(base_cfg, form)` →
`apply_settings_plan()` → `merge_config_updates()`, and it reads no logs (there is nothing
to back-solve). A budget that is not a non-negative number rejects the *whole* save, with
`s_err_budget` for Claude and `s_err_codex_budget` for Codex. Gauge lists are normalised to
the allowed names in canonical order. An empty list is valid and means that provider is
hidden (`provider_shown()`). Hiding both providers is allowed, and the pill then reads
`no_providers`.

Teardown has one path: `close_main_panel()`. Save and the X both route there, through
`Handler.windowWillClose_` on macOS and `SettingsDialog.closeEvent` on Windows. The panel
sets `setReleasedWhenClosed_(False)` so that `ui`'s explicit references never point at an
object Cocoa freed on close. It sets `setHidesOnDeactivate_(False)` because an
`LSUIElement` app has no Dock icon to bring a vanished panel back.

---

## Privacy

The app reads users' Claude Code transcripts and, for Codex users, the Codex CLI's session
logs (`codex_sessions_root()` — `$CODEX_HOME/sessions` or `~/.codex/sessions`), both
locally and only for spike detection. It must never expose their contents. The Codex
parser takes numbers only: timestamps and the token counts of `token_count` events. It
also reads Codex's `auth.json` for the usage token, read only and never written.

**[NEVER] print, log, or write out message bodies, project paths, or session IDs** — not
to stdout, not to the debug log (`~/claudepet_debug.log`, enabled by
`CLAUDE_PET_DEBUG=1`), not into an error message, not into a crash report, not into a
test fixture derived from real data. There is no authorization path for this and no
debugging need that justifies it; log counts and shapes instead.

The only things that may leave either parser are the aggregates it is built to produce:
timestamps, weighted totals, and the lowercased model string (the constant `"codex"` for
Codex). `parse_codex_entries()`'s debug line carries file, row and skip counts only. Note that log **file
paths encode project directory names**, so a path is identifying information — an
exception message that interpolates a path is a leak. When debugging, log counts and
shapes ("42 rows, 3 files"), never contents.

---

## Release procedure

> **[ASK] Stop. Every step below is separately authorized.**
>
> This is a reference for what the steps *are*, not a runbook to execute on being told
> "release it". Being asked to release is not authorization for these steps; each one is
> requested individually — by the user, or by the Coordinator **for the local and
> reversible steps only** (bump, commit, local tag); everything outward-facing takes the
> user's own authorization — and you stop after each. A human
> may lift the per-step asking in advance, but only under the four guards in
> [AGENTS.md](AGENTS.md#blanket-authorization-of-the-release-sequence) — and doing so
> changes nothing about the gate below.
>
> **The steps below run in two phases, and the gate sits between them.** The gate is
> [AGENTS.md §6](AGENTS.md#6-release-gate), which states the boundary in these same
> words:
>
> > **The release commit is the phase boundary.**
> >
> > - **Preparation.** The version bump, the release notes, the named-path staging, and the
> >   release commit itself. These run *before* the gate is evaluated, because they are what
> >   produces the thing the gate judges. The release commit carries the `Developer:` and
> >   `Verifier:` trailers, so the merge checklist becomes evaluable the moment that commit
> >   exists — and not one step earlier.
> > - **Execution gate.** Evaluated *after* the release commit, when the tracked tree is
> >   clean: the Verifier re-runs the full suite from that clean tree and records the command
> >   and its output, the release notes are checked, the Coordinator's sign-off is recorded,
> >   and an eligible release operator is named with their eligibility stated.
> > - **Only once the execution gate is GREEN** may the release's artifact build, signing,
> >   notarization, local tag, push, and publication run. No preparation step waits on the
> >   gate; no step after it begins before the gate is GREEN.
>
> Mapped onto the numbered steps below: **steps 1 and 2 are preparation** — the bump, the
> notes, the staging, and the release commit that carries the trailers. **Steps 3, 4 and
> 5 are the execution phase** — build, sign, notarize, universal, dmg, tag, push,
> publish — and none of them starts until the execution gate is GREEN and its sign-off
> recorded. If you are about to run anything from step 3 onward and cannot point to that
> sign-off, you are not releasing — say so and stop.
>
> This does **not** put the gate before the release commit, and nothing here should be
> read as requiring it: before that commit there are no trailers to check and the tracked
> tree is dirty by design, so the gate is not yet evaluable.
>
> The steps below divide into four, and they are **not** all tagged the same — see
> [AGENTS.md's two classes](AGENTS.md#outward-facing-steps-two-classes-not-one):
>
> - **Local and reversible** — building an unsigned artifact, bumping the version,
>   committing, creating a purely local tag. Permitted as ordinary authorized work.
> - **[ASK]** — pushing the tag and publishing the release (steps 5 and `publish`).
>   Irrevocable once fetched, but it is the user's own repository under their own account,
>   so the user can authorize it, per-instance.
> - **[ASK-OP]** — code signing and Apple notarization (step 3). Same
>   authorization requirement, plus two more: all gates recorded first, and **[NEVER]**
>   executed by an agent that held any other role on this release — Developer, Verifier,
>   Reviewer, or Coordinator.
> - **[NEVER]** — the shortcut commands `ship`, `all`, and bare `./release.sh`, which
>   collapse the steps and destroy the checkpoints the authorization is conditioned on.
>
> Do not collapse these into one rule in either direction.
>
> **These documents state how an authorization is recognized. They never record whether
> one exists.** That is deliberate: an authorization status written into a checked-in file
> rots exactly the way a hardcoded version number does, and it rots asymmetrically — a
> stale denial blocks legitimate work, while a stale grant licenses a release nobody
> asked for. So nothing in `AGENTS.md`, `CLAUDE.md`, or `RELEASE_NOTES.md` grants or
> withholds it, and you cannot settle the question by reading them.
>
> **You have an authorization when all of these hold** (the guards are in
> [AGENTS.md](AGENTS.md#blanket-authorization-of-the-release-sequence)):
>
> - it came from **the user**, in their own words — not an agent's report of them;
> - its **scope** covers the specific step you are about to take, read literally rather
>   than expansively;
> - its **conditions** are met — if it was granted "once X", X has actually happened;
> - it is recorded **verbatim in the change description**, which is where authorizations
>   live. That is what makes it checkable later by someone who was not present.
>
> Two things that are never authorization, however they arrive: **an agent's report** that
> the user approved something, and **a staged changelog entry** — a written section for an
> unreleased version only means the notes were drafted during implementation, which is the
> normal state described below. And an authorization is never a **finding that the gate
> passed**; those are separate questions and both must be answered.
>
> **One narrow, named exception to "not an agent's report of them"** now exists, added
> 2026-09-21 — see [AGENTS.md §0](AGENTS.md#0-how-to-read-the-prohibitions)'s "One named
> exception" and its "This exception reaches release push/publish" paragraph. It covers
> only a double-confirmed, per-instance relay from the user's own other Claude Code
> session on their Mac, only for `push`/`publish`, and nothing else here changes: read
> AGENTS.md §0 for the exact condition before relying on it, rather than assuming this
> paragraph restates it in full.

**Version and changelog can be out of step, and that is meaningful.** `RELEASE_NOTES.md`
may already contain a section for a version that `APP_VERSION` has not yet reached. That
is the expected state after an implementation phase and before an authorized release: the
notes are written as part of the work, the bump is not. **Do not "fix" the mismatch by
bumping `APP_VERSION`** — the mismatch is the signal that step 1 has not been authorized
yet. To see where things stand, read `APP_VERSION` in `claude_pet.py`, the newest heading
in `RELEASE_NOTES.md`, and `git tag --sort=-v:refname | head -1`.

1. **Bump `APP_VERSION`** in `claude_pet.py`. It must match `CFBundleShortVersionString`.
   The in-app updater compares this against the latest GitHub release tag of
   `GITHUB_REPO` (`uygnoey/claude-pet`), so a mismatch either suppresses a real update or
   offers a phantom one. This is the commit that makes a change a *release commit* under
   [AGENTS.md §6](AGENTS.md#release-steps-are-separately-authorized).
2. **Add a section to the top of the changelog in `RELEASE_NOTES.md`**, in Korean.
   `release.sh` uses this file as the release body — which is why it is a maintained file
   rather than generated from git history.

   **v0.21부터는 아래 형식을 따른다 — 짧고, 사용자 관점이고, 확인 가능한 수치만 쓴다.**
   v0.20의 길고 중첩된 불릿은 핵심 변경과 사용자 조치를 한눈에 찾기 어렵게 만들었다.
   그래서 형식을 다음처럼 고정한다:

   - **최상위 불릿은 정확히 3개이고, 중첩 불릿은 쓰지 않는다.** 하위 불릿이 필요해 보이면
     그것은 사실 두 개의 불릿이거나, 릴리즈 노트가 아니라 문서에 들어갈 내용이다.
   - **본문 전체가 450 글자 이하**(공백을 하나로 정규화한 기준), 불릿마다 1~2 문장.
   - **사용자가 할 행동과 그 결과를 쓴다.** 사용자가 해야 할 일이 없으면 없다고 적고,
     내부에서 어떻게 구현했는지는 서술하지 않는다.
   - **수치는 릴리즈 커밋 시점의 트리에서 감사할 수 있거나, AGENTS.md §5 기록으로 근거가
     남아 있을 때만 쓴다.** 둘 다 아니면 그 수치는 빼고, 크기나 빈도를 뭉뚱그린 표현으로
     바꿔 적지 않는다 — AGENTS.md 는 릴리즈 노트에 그런 정량 표현을 금지한다.
   - **넣지 않는 것: 해시, 내부 식별자, 소스 경로와 줄 번호, 테스트 이름·개수·매트릭스.**
     사용자가 행동으로 옮길 수도, 스스로 확인할 수도 없는 것들이다.
   - 이 형식은 아직 게시되지 않은 맨 위 섹션에만 적용된다. 이미 published 된 섹션은
     한 글자도 건드리지 않는다.

   **[ASK] Do not rewrite or drop a *published* entry.** Once an entry has gone out, this
   file is the only record of what those users received, and editing it rewrites history
   people have already acted on. No agent may do this on its own initiative; the user can
   ask for a correction to a published entry (a typo, a wrong fact), and that is
   legitimate — which is why this is [ASK] and not [NEVER].

   **An entry is published when the tag is pushed and the GitHub release exists with that
   entry as its body** — not when `APP_VERSION` is bumped. The bump is a local edit that
   reaches no user, and it can be reverted or abandoned; publication is the irreversible
   step. Freezing at the bump would permanently lock an entry for a release that was
   started and then abandoned, with no un-ship path, and it would contradict this rule's
   own rationale, which is about what users received.

   **The operational test is the tag and the published releases, not the constant:**

   ```sh
   git tag --sort=-v:refname | head -1   # newest tag — NOT `git tag | tail -1`,
                                         # which sorts lexically and answers v0.9
   gh release list --limit 5          # what actually exists publicly
   ```

   These are authoritative because they describe the outside world. `APP_VERSION` only
   describes this checkout — it may be ahead of what shipped (a staged bump) or behind it.

   **While an entry is unpublished it is staged, and correcting it is ordinary work** —
   not rewriting history — **whatever `APP_VERSION` reads locally**. Fix errors in it
   freely, and prefer editing the wrong sentence over appending a correction beside it,
   since a reader meets the wrong sentence first.

   **[ASK] When you are genuinely unsure whether an entry has been published, treat it as
   published.** The looser trigger is not a loophole: the cost of wrongly treating a
   staged entry as frozen is that you ask before fixing a typo, while the cost of wrongly
   treating a published entry as staged is silently rewriting what users were told. Those
   are not comparable, so the tie goes to frozen.

   **Staging the release commit.** Steps 1 and 2 are edits; one commit carries them, plus
   whatever else the release changed. **Never stage by sweeping. Name every path, then
   read back what you staged:**

   ```sh
   git add <every path this release changed>
   git diff --cached --name-only   # must list exactly those paths, and nothing else
   ```

   Derive that path list from `git status --porcelain` for the release in hand, not from
   this document — **the set differs per release.** For v0.19 that set is five paths,
   which is the shape to expect from a change that reaches the estimator:

   ```sh
   git add claude_pet.py RELEASE_NOTES.md AGENTS.md CLAUDE.md tests/test_log_estimate.py
   ```

   — the bump, the new notes section, both process documents, and the estimator tests. A
   release that touches only code stages fewer, and staging an unchanged file because it
   appears on this line is its own error. The read-back is not ceremony: it is the only
   step that catches a path you did not intend, and it belongs before the commit, not
   after.

   **[NEVER] `git add -A`, or `git add .`, for this commit.** The three paths under
   [User-owned files](#user-owned-files) are untracked and **not** gitignored —
   `git check-ignore diag.py release/ClaudePet.iconset release/icon_1024.png` names none
   of them and exits 1 — so either command sweeps all three into the release commit.
   Committing them is precisely the act that section places behind **[ASK]**: reachable
   only with the user's own per-file authorization, which a sweep by construction does not
   have. The ban here is on the indiscriminate command, in the same shape as bare
   `./release.sh`: forbidden outright, while the individual actions it would bundle stay
   reachable through their own gates.

   The commit carries both `Developer:` / `Verifier:` trailers, filled in per
   [AGENTS.md §7](AGENTS.md#7-commit-trailers) — including for a documentation-only
   commit. Follow what is written there; do not invent a variant.

   **[NEVER] make this commit with `release.sh`.** `bump_version()` runs
   `git add claude_pet.py` and nothing else before its `git commit`, so the notes, both
   documents, and the tests would silently be left out of the release commit — and it
   continues into `git tag` and `git push && git push --tags` before you could look. Its
   only caller is `ship`, which is already **[NEVER]** above; there is no subcommand that
   reaches `bump_version` alone. Stage and commit by hand.
3. **Build, sign, notarize.** This step opens the execution phase, so **nothing here runs
   until the execution gate is GREEN** — including the unsigned build, which is ordinary
   work by tag but is still a step of the release. (A development build outside a release,
   under [Build](#build), is not a release step and is unaffected.)
   ```sh
   ./release.sh build        # OK for an agent: py2app build only, unsigned, current arch

   ./release.sh sign         # [ASK-OP] Developer ID signing
   ./release.sh notarize     # [ASK-OP] notarize + staple + zip
   ./release.sh universal    # [ASK-OP] build_universal; sign; notarize
   ./release.sh dmg          # [ASK-OP] make_dmg → notary_submit + stapler
   ./release.sh publish      # [ASK]    gh release create/upload/edit — no signing
   ./release.sh all          # [NEVER]  build; sign; notarize; maybe_universal; make_dmg
   ./release.sh ship [ver]   # [NEVER]  bump_version; build; sign; notarize;
                             #          maybe_universal; make_dmg; publish
                             #          — the ENTIRE release in one command
   ./release.sh              # [NEVER]  bare form. Prints usage and exits 1 now;
                             #          it used to default to `all`. Still [NEVER].
   ```

   **`[ASK-OP]` means the release-operator gate**: user authorization for this artifact,
   all §6 gates recorded first, and executed only by an agent that held **no other role on
   this release — not Developer, not Verifier, not Reviewer, and not Coordinator**. The
   four `[ASK-OP]` subcommands each reach a `codesign` or notarization step, which is what
   puts them in that class.

   **`build` and `publish` are the only two that avoid signing**, and they are not
   equivalent: `build` is ordinary local work, `publish` is [ASK] because it writes to the
   user's GitHub releases.

   **`publish` runs the artifact gate before it uploads, and the gate can refuse.** Being
   authorized to publish is not a prediction that publishing will happen. What it checks,
   in order (`verify_upload_artifact` and `check_assets`, both in `release.sh`, delegating
   to `verify_release_artifact.py`):

   - **The upload set is all four files** — `ClaudePet.zip`, `ClaudePet-universal.zip`,
     `ClaudePet.dmg`, `ClaudePet-universal.dmg` — and their names match the updater's own
     `UPDATE_ASSET_NAMES` table. A missing file is a refusal, not a silent omission: a
     release without the universal zip leaves Intel users with nothing to download, and a
     name that drifts from the updater's table makes every installed copy retry forever
     without signalling anyone.
   - **Each file is opened as a file**, not as the build directory it came from — the
     archive is scanned for unsafe members *before* extraction, must contain exactly one
     top-level `ClaudePet.app` and no other `.app` anywhere inside, and the bundle inside
     is then checked for pet payload, code identity, version, architecture, signature,
     notarization and staple.
   - **The architecture requirement comes from the artifact's filename, never from this
     machine.** `-universal` means `arm64,x86_64`, the plain name means `arm64`, and an
     artifact whose name settles neither is refused rather than measured against
     `uname -m`. Asking the build machine is how a universal artifact that lost its
     `x86_64` slice passes on the maintainer's Mac and fails only for Intel users.

   The same asymmetry applies as everywhere else here: the gate refusing costs a rerun,
   the gate passing something wrong reaches every user the updater serves.

   **`all`, `ship`, and bare stay [NEVER] even for the release operator.** They are not
   forbidden because of what they touch — the operator may run those same actions
   individually — but because they run several gated steps in one invocation, which
   destroys the per-step recording and stop-on-failure the authorization is conditioned
   on. A shortcut through an authorized sequence is not authorized.

   **Against an existing release, `publish` overwrites rather than creates — and it
   replaces the downloads, not just the text.** Both halves, from the `gh release view`
   branch of `publish()`:

   - `gh release upload "$TAG" "${files[@]}" **--clobber**` — **replaces the published
     assets**: the `.zip` and `.dmg` files users actually download, including the ones the
     in-app updater fetches. This is the user-visible half.
   - `gh release edit "$TAG" --notes-file` — replaces the release **body** with freshly
     generated notes.

   So re-running `publish` on an already-published release is a *rewrite of published
   material*, not a fresh publication. It needs **two** authorizations, not one — both
   [ASK] and per-instance, so neither implies the other:

   1. to rewrite the published entry (step 2's freeze), and
   2. to publish.

   Keep the objects distinct when reasoning about this. The **frozen** object is the
   v-section in `RELEASE_NOTES.md`. The **overwritten** objects are the GitHub release
   body — a published copy derived from it by `gen_release_notes` — and the release
   assets, which have no local counterpart at all. Editing the local file touches neither
   of them, and replacing an asset users have already downloaded does not recall the copy
   they have.

   Two of these deserve singling out:

   - **[NEVER] run `ship`.** It bumps `APP_VERSION`, builds, signs, notarizes, builds the
     dmg, and publishes to GitHub — every separately authorized step in this document, in
     one invocation, with no pause between them. It is the single most dangerous command
     in this repository.

     **It publishes before it builds.** `bump_version()` ends with
     `git push && git push --tags`, and it is the **first** call in the chain — so `ship`
     puts the commit and tag on GitHub before a single line has been compiled. If the
     build then fails, the tag is already public and the updater is already offering a
     version that does not exist. The checkpoints are not merely collapsed here; they run
     in the wrong order.

     **This prohibition does not relax when the individual steps are authorized — that is
     precisely when it matters.** Every action `ship` performs is now reachable by an
     authorized release operator running the steps individually, which makes `ship` the
     command such an operator would plausibly reach for, and the one that must still be
     refused. The authorization is conditioned on the checkpoints *between* the steps:
     seeing the build succeed before it is signed, seeing the right version tagged before
     it is pushed, recording each outcome, stopping on the first failure. `ship` deletes
     every one of those while appearing to do the same work. **What the user authorizes is
     the sequence, not a shortcut through it** — so "I was authorized to do all of these"
     is not authorization to do them this way. See
     [AGENTS.md](AGENTS.md#sequencing-is-part-of-the-authorization).
   - **Bare `./release.sh` prints usage and exits 1** — no argument and an unrecognized
     argument share the same branch (`case "${1:-}"` … `""|*)`). It did **not** always:
     the dispatch was `case "${1:-all}"`, so omitting the argument ran `all` — build,
     sign, notarize, universal, dmg — from a command that looked like it did nothing.
     The `[NEVER]` above is unchanged by the safer default, and **the default must not be
     put back**; see [Run, test, build](#run-test-build).

   Do not treat this list as closed. `release.sh` is the authority on what these do;
   check its `case` statement before running anything from it, and assume an
   undocumented subcommand is prohibited until you have read its function body.
   Signing uses the `Developer ID Application: Yeongyu Yang (RXGNVSLYF5)` identity with
   `entitlements.plist`; notarization uses the stored `claudepet-notary` credential
   profile.

   **[ASK-OP] Signing and notarization.** Signing binds **Yeongyu
   Yang's Developer ID** to a binary and notarization submits it to **Apple under their
   account**. The artifact then carries that assertion permanently — anyone inspecting it
   later is told this person vouched for these contents — which is why this step is gated
   harder than pushing the tag, even though the push reaches users faster. All three
   conditions must hold, per
   [AGENTS.md's second class](AGENTS.md#outward-facing-steps-two-classes-not-one):

   1. **The user has explicitly authorized signing this artifact**, per-instance.
   2. **Every gate in [AGENTS.md §6](AGENTS.md#6-release-gate) has passed and been
      recorded** — before this step, not alongside it.
   3. **[NEVER] performed by an agent that held any other role on this release —
      Developer, Verifier, Reviewer, or Coordinator.** Only a dedicated release operator,
      and no authorization lifts this — it is separation of duties, not permission. The
      Coordinator is excluded because §6 makes its sign-off the certification that the
      release is ready; certifying and signing must be different parties.

   The operator records the result of each step as it completes and **stops on the first
   failure**. Succeeding at a command is not evidence you were the right party to run it.

   If any condition is unmet: build the unsigned artifact if asked, then stop and hand it
   to the maintainer, saying plainly what remains.
4. **Both release builds need the `universal2` Python** from python.org (pyenv's Python
   is single-architecture, and its deployment target is this Mac's macOS). `release.sh`
   checks the universal one with `lipo -archs`, and both builds' deployment target against
   12.0, and refuses otherwise.
5. **Tag and push.** The tag is the version with a `v` prefix — `vX.Y` for `APP_VERSION`
   `"X.Y"` — since the tag is what the updater compares against.

   **[ASK] Push the tag or publish the release only on the user's explicit, per-instance
   authorization.** This is the step that makes the release real: `check_github_update()`
   polls the repo's latest release tag every hour (never at launch — the first check
   comes one interval after start), so pushing it causes **every
   installed copy of the app** to start offering the update. That reaches users directly
   and cannot be recalled from anyone who has already fetched it — deleting the tag
   afterwards does not un-ship it.

   It is [ASK] rather than [NEVER] because it is a push to the user's own repository under
   their own account, which is theirs to authorize —
   [AGENTS.md's first class](AGENTS.md#outward-facing-steps-two-classes-not-one). The
   irreversibility is unchanged; what the tag settles is only *who can lift it*. So:

   - The authorization must come from the **user**, not from another agent reporting one.
   - It is **per-instance**. Approval for one release is not approval for the next.
   - It does not license skipping or reordering any gate — see
     [AGENTS.md §6](AGENTS.md#6-release-gate). An authorization is not a finding that the
     gate has passed.
   - Absent that authorization, prepare it, state the exact command, and hand it over.
