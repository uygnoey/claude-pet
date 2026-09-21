# CLAUDE.md — ClaudePet facts

This file holds facts about **this** repository: paths, symbols, commands, constants,
and the domain invariants of the usage estimator.

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

ClaudePet is a macOS desktop pet that displays your Claude Code token usage. It is an
`LSUIElement` app (no Dock icon, no menu bar item — it draws a borderless always-on-top
window with an animated sprite and a compact one- or two-line usage summary pill), written in Python against PyObjC
(AppKit/Foundation), and shipped as a self-contained, Developer ID-signed and
Apple-notarized `.app` bundle built with py2app.

**`claude_pet.py` is essentially the whole app** — a single module holding config,
i18n (en/ko/ja/es), log parsing, the usage estimator, OAuth/keychain token reading, the
Admin API client, the AppKit UI, the settings panel, the updater, and the uninstaller.
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
| `tests/test_log_estimate.py` | Unit tests for the log estimator (`parse_usage_entries`, `compute_usage`). |
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
`python3` it finds (pyenv on the maintainer's Mac) and `release.sh` uses that one as `PY` and
the python.org universal2 one as `UPY`; the "Start at sign-in" toggle imports the
`ServiceManagement` framework at call time and `setup.py` lists it for py2app. A bundle built
from a Python that lacks `pyobjc-framework-ServiceManagement` shows the menu item disabled on
every machine — that happened on 2026-09-13 with pyenv's Python. Check
`python3 -c 'import ServiceManagement'` for each interpreter before a release build.

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

**Tests must never read the real `~/.claude` corpus.** `tests/test_log_estimate.py`
builds every fixture by hand, writes it into a `tempfile.TemporaryDirectory()`, and
points `claude_pet.LOG_DIRS` at that directory for the duration of the test (restoring
it via `addCleanup`).

The reason is not tidiness. A suite that reads live logs **passes or fails according to
how much agent traffic the developer happened to generate that day.** The same code
would go green on a quiet morning and red after a busy afternoon, and neither result
would be about the code. It is also the exact situation
[AGENTS.md §5](AGENTS.md#never-measure-a-corpus-your-own-session-is-writing) rules out —
an agent running this suite is itself writing to `~/.claude` while it runs.

Any new test that needs a log shape adds a record to the `usage_record()` helper's
parameters. If a hypothesis genuinely requires the real corpus, that is an
investigation, not a test: do it in a scratch script, report it under the evidence
standard, and keep it out of `tests/`.

**[NEVER]** point `LOG_DIRS` at a real `~/.claude` path from a test, and never copy real
transcript content into a fixture (see Privacy below).

---

## JSONL invariants

Claude Code writes newline-delimited JSON transcripts under the directories in
`LOG_DIRS` (`~/.claude/projects`, `~/.config/claude/projects`), discovered recursively
by `_iter_log_files()`. The estimator's correctness rests entirely on the following
properties of those files. Each one has been the cause of a real miscount.

These are **correctness facts, not permission rules** — they carry no `[NEVER]`/`[ASK]`
tag (see [AGENTS.md §0](AGENTS.md#0-how-to-read-the-prohibitions)). "Wrong" here means
the number comes out incorrect, which no authorization can fix.

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

`_weigh_usage(usage)` converts a usage object into a **cost-weighted** number, using
weights proportional to API list pricing:

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
user's calibrated `%` stable when their cache-hit ratio changes; an unweighted total
would drift with usage pattern even at constant real cost.

---

## Windows: what each gauge measures

`compute_usage()` produces three gauges — **session**, **weekly**, and **opus**
(per-model) — over three different windows. They are easy to confuse, and a change to
one usually is not a change to the others.

Everything starts from one parse: `compute_usage()` calls
`parse_usage_entries(now - 7 days)`, so **no gauge can ever see anything older than 7
days**. That 7-day bound is the outer limit for all three, including the session gauge.

### Session window — 5-hour tiled blocks

`SESSION_HOURS = 5`. Sessions are not "the last 5 hours"; they are **fixed 5-hour blocks
tiled forward from activity**:

- Walking the entries in time order, a new block opens at the first entry at or after the
  current block's end. Its start is that entry's timestamp **snapped down to the hour**
  (`replace(minute=0, second=0, microsecond=0)`), and it runs 5 hours from there.
- The session gauge reports the **current** block only: if `now` is past the last block's
  end, `session_tokens` is `0` and `session_reset` is `None`. Otherwise it sums entries
  in `[block_start, block_end)` and `session_reset` is `block_end`.

The hour snap and the tiling both exist to match how Claude's own UI blocks sessions —
continuous use resets exactly every 5 hours rather than sliding, so the estimated
percentage does not drift away from the app's.

### Weekly window — configured weekday, or rolling 7 days

`_weekly_window_start()` returns the start of the current weekly window, or `None`.

- **Configured mode.** If the user has set a weekly reset weekday
  (`RUNTIME["weekly_reset_day"]`, `0`=Mon … `6`=Sun, paired with `weekly_reset_hour`,
  default `20`), it returns that boundary converted to UTC, entries before it are
  excluded, and `compute_usage()` sets `weekly_reset = week_start + 7 days`.
- **Rolling mode.** If `weekly_reset_day` is `None` — the default — there is no boundary:
  every entry from the 7-day parse is counted, and `compute_usage()` sets
  `weekly_reset = None`.

**In rolling mode there is no single reset timestamp, and both the weekly gauge and the
per-model gauge render `-`.** The two share the same `weekly_reset` value, so this is
never one-sided. A rolling window slides continuously — every entry ages out on its own
schedule — so no instant exists at which it resets. The old behaviour showed
`first entry + 7 days`, which is merely when the *oldest currently-known* entry expires:
a number that moves whenever the oldest entry changes, and that never matched Claude's
own UI. On the pill's reset line the adapter formats each reset with `fmt_countdown()`, which maps
a falsy reset to the literal string `"-"` — so a rolling weekly window reads `주간 -` there.

If a user wants a real reset time, they set a weekly reset weekday in settings. Do not
reintroduce a synthesized one.

### Per-model (opus) window — the weekly window, filtered

The opus gauge uses **the same window and the same reset as the weekly gauge**; the only
difference is that its sum is restricted to entries whose lowercased model string
contains the model keyword. It is not a separate time window, so any change to weekly
windowing changes this gauge too.

The keyword is `RUNTIME["model_keyword"]`, default `"auto"`. Under `auto`,
`_detect_model_keyword()` picks the newest premium family present, searching
`PREMIUM_FAMILIES = ["fable", "mythos", "opus"]` in that order — first within the current
weekly window, then across the full 7 days, falling back to `"opus"`. The name "opus" is
therefore a historical label for the gauge's dict key, **not** a guarantee that Opus is
what it measures; the tier Anthropic applies a per-model weekly limit to has changed
before and is expected to change again.

### Spike detection windows

Spike detection uses two shorter windows over the same entries: the **last 5 minutes**
(`burn_5m`, `burn_5m_opus`) compared against a baseline built from the **preceding 25
minutes**, split into five 5-minute buckets. Only buckets with activity are averaged —
including idle zeros would drag the baseline below real activity and make the 2.5×
gate fire during ordinary use. Both use `noncache` (cache reads excluded).

---

## exact vs estimate

There are two sources of usage, and they coexist at runtime:

- **exact** — `fetch_exact_usage()`, backed by the OAuth token. The server returns
  percentages it computed itself. **This is the oracle.** When it is available it is
  what the gauges show, and no calibration is needed. `_read_oauth_token()` tries three
  sources in a deliberate order — credentials **file**, then the `security` **CLI**,
  then the **native** Keychain API — because only the last one can raise a Keychain
  prompt, and a background `LSUIElement` app that cannot show UI dies silently on it
  (`-25308`). Do not reorder these.
- **estimate** — `compute_usage()`, derived from the JSONL logs and the weights above.
  It is the fallback for when the token is unavailable, unreadable, or the user has not
  logged in.

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
the environment. **It does not run for ordinary users**, so do not describe exact mode as
"OAuth, falling back to the CLI" without that qualifier.

The reason is in its docstring: the `claude` CLI launches the whole Claude Code Node app
as a child process, which scans the home directory, project directories, and other
folders. macOS attributes that access to the **parent** — ClaudePet — which then triggers
protected-folder prompts (Downloads, Photos, network volumes). Since OAuth already
supplies session, weekly, per-model, and credit rows, the CLI buys nothing and costs a
wall of permission dialogs. Leave it off.

### Timing: what recomputes when

Two `NSTimer`s are registered on the same `Ticker` object, and conflating them is the
usual source of wrong statements about this app:

| Timer | Interval | What it does |
| --- | --- | --- |
| `tick:` | `TICK = 0.05` (20 Hz) | **Renders only.** `tick_()` reads `state["stats"]`, picks a mood, advances the animation frame. It never calls `compute_usage()`. |
| `refresh:` | `REFRESH_SEC = 30` | Spawns a daemon thread whose `work()` calls `compute_usage()`, then `fetch_exact_usage()`, then the cost calls, and finally sets `state["repaint"]`. |

So: **the estimate is recomputed once per 30 seconds on a background thread; the 20 Hz
tick only renders the last computed value.** `compute_usage()` also runs on three
one-off paths — a priming `refresh_(None)` at startup, a manual refresh on double-click,
and a call inside the settings-save handler that back-solves limits from a typed `%`.

When this document or a changelog says "the previous tick" — for instance in the
session-reset greeting below — it means **the previous 30-second refresh**, not the
previous animation frame. The distinction matters: across 16 ms nothing changes, while
across 30 s a session boundary can pass.

### The pill is one summary line, and where the estimate still reaches in exact mode

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

What the line contains is decided by `roam_summary()`, a pure function that returns one
`(kind, payload)` segment:

| kind | when | line |
| --- | --- | --- |
| `exact` | `state["oauth"]` has rows | the first three **gauge** rows (session, weekly, per-model — the adapter drops credits via `_label_order`), server labels verbatim |
| `estimate` | no server rows, logs present | session, weekly, and the model gauge from `compute_usage()`, each value prefixed with `SUMMARY_APPROX` (`≈`) |
| `cost` | API mode with an Admin key | today's cost, then this month's when known |
| `status` | otherwise | one translated status key (scanning, onboarding, missing key, loading) |

**Colour carries two things, on two different runs.** The *value* run says where the
number came from: `SUMMARY_COLORS["exact"]` is emerald, `["estimate"]` amber, and API cost
amounts are coral. The *label* run (session/weekly/model, today/this month) is white
(`"value"`) and turns `"warn"` at 50 % and `"bad"` at 85 % — `summary_value_kind()`, the
same thresholds the old bars used — or `"bad"` outright when that gauge is spiking, in which
case the label is also prefixed with `SUMMARY_SPIKE` (`▲`). (The user first asked for the
opposite assignment and then swapped it the same day: "텍스트랑 수치랑 색을 반대로 하자".) Note the asymmetry in exact mode: the adapter passes
`spike_first=bool(spike_info(stats))`, so a weekly or per-model *estimator* spike marks the exact
**session** label. The second line is `"sub"` (the dim text colour). In API mode the line is
`오늘 $x · 이번 달 $y / $budget` with the words "이번 달" coloured by this month's share of the budget.
The old status line's `⚠` survives as a trailing run appended by the adapter when the
estimate is showing because the OAuth token was rejected (`OAUTH_STATUS["auth_error"]`).
`roam_summary()` stays pure: the adapter pre-formats reset times with `fmt_countdown()` and
passes them in (`reset_texts`, and `row[2]` for exact rows), passes `spike_first` for the exact
session row, and keeps every server row except credits (`_label_order() >= 9`) so a model row
whose label is not a bare family word still shows. The adapter, `roam_summary_text()`, memoises
its result per input and 5-second window because it runs on every 20 Hz tick while the pill is
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

**Where the estimate still reaches in exact mode.** The numbers are server-derived, but three
visible paths are not. Re-derive this list from the source before relying on it — it has
been wrong before, including once in v0.24's own draft, which dropped path 1 while the
bars went away.

1. **The exact session label turns red with ▲ — inside the pill itself.** The adapter
   passes `spike_first=bool(spike_info(stats))`, `roam_summary()` marks the exact session
   row as spiking, and `_summary_segment_runs()` prefixes that label with `SUMMARY_SPIKE`
   and colours it `"bad"`. The value beside it is untouched and still emerald. This is the
   old red-session-bar path in its new clothes, and it keeps the old asymmetry: a weekly or
   per-model *estimator* spike marks the exact **session** label.
2. **Spike → the pet, and it outranks the server.** `current_mood()` consults
   `spike_info(state["stats"])` and returns `"failed"` *before* it reaches the exact-mode
   branch that derives a mood from the server percentage, so a false spike from the
   estimator overrides a perfectly good server reading. Four further effects hang off
   that same signal: `tick_()` forces a repaint for as long as a spike is live; the pet is
   tinted by a pulsing spike-coloured overlay that exists on no other path; the
   **mouse-proximity greeting is suppressed**, since its guard includes
   `not spike_info(state["stats"])`; and `roam_tick()` folds a live spike into `busy`, so
   the pet neither sets out on a walk nor keeps its arrival latch while a spike shows.
3. **The session-reset greeting.** The refresh worker compares the previous refresh's
   `session["pct"]` against the current one and plays the jump animation when it crosses
   from above 5 to below 1. Both values come from `compute_usage()`; the OAuth rows are
   never consulted here, and the comparison carries no mode guard.

**The exception — API mode.** Paths 1 and 2 are suppressed there by one mechanism:
`spike_info()` returns `None` outright when `RUNTIME["mode"] == "api"`, so `spike_first` is
False (and the API line has no session row anyway), mood falls through to the exact
branch, the overlay never draws, the greeting is no longer suppressed. Path 3 has no guard
and still fires in API mode.

The practical consequence: a parsing or weighting regression shows up as an alarmed,
tinted pet and a pet celebrating a session reset that did not happen — never as wrong
numbers on a logged-in user's pill, whose values are server-derived and drawn emerald.

---

## Danger zone

Two things make estimator changes higher-risk than they look.

**1. The limit constants are guesses.** In the `RUNTIME` dict near the top of
`claude_pet.py` (locate it by the `RUNTIME = {` line, not by line number):

```python
"session_limit": int(os.environ.get("CLAUDE_PET_SESSION_LIMIT",  8_000_000)),
"weekly_limit":  int(os.environ.get("CLAUDE_PET_WEEKLY_LIMIT",  60_000_000)),
"opus_limit":    int(os.environ.get("CLAUDE_PET_OPUS_LIMIT",    15_000_000)),
```

The inline comment says it outright: these are **estimates, not officially published
values** (한도 추정치 — 공식 공개값 아님). Do not treat them as ground truth, do not
"correct" them from an unsourced number, and do not build a claim on top of them.

**2. The `% 보정` (calibration) path back-solves an absolute limit from estimator
output.** The settings panel lets a user type the percentage shown in Claude's own
Settings → Usage. The app then computes `limit = current_estimated_usage ÷ (pct / 100)`
and stores that as the user's limit.

**Every limit input is optional, and blank means "keep".** `prepare_settings_config()`
resolves each of the three gauges independently: a filled `%` back-solves that gauge, an
empty `%` with a filled M-token field uses that number, and **both blank leaves
`base_cfg`'s existing key untouched — and creates no key if `base_cfg` has none.** The
last clause matters: inventing a persisted override for a gauge the user never touched
would pin a value they cannot see they set. Ordinary users cannot know their token
limits — Claude's own UI shows only percentages — so requiring the M-token fields (as
this code once did) made the panel unsaveable for exactly the people it was for.

**"Blank" and "wrong" are different, and only blank is a skip.** A value that is present
but unusable still rejects the *whole* save, unchanged from before; blankness is decided
on the untouched raw string, before any character is stripped.

**Two zero cases, two messages.** `0%` typed by the user (`s_err_calib_zero_pct`) is not
the same as an estimated usage of zero (`s_err_calib_zero`). A user seeing `0%` in Claude
is being told this window has no usage yet, so the actionable advice is "calibrate later
or leave it blank" — not "enter a number between 0 and 100". `_calibration_percent_error()`
runs **before** the usage scan for this reason: a scan reads Claude Code's own logs and
can fail, and a failure there would report "could not read usage" for what is really a
rejected input.

**Absolute limits stay reachable but live in a separate window.** The three M-token fields
are built by `open_advanced_limits()` in an `NSPanel` of their own, opened from a
button sharing note3's row in the main panel. They start blank and show the current value
in a read-only label beside them; they are never pre-filled, because pre-filling would make
"blank means keep" depend on whether the window had been opened, and a conditional
invariant is worth less than an unconditional one.

**That window is short, not narrow, and the distinction is load-bearing.** It is 500 × 190
— *wider* than the 420-wide main panel. Only the main panel is fighting for vertical space
on a 768-tall screen; the child window is bound by neither that budget nor 656, so it can
take the width its three columns need. Each row is laid out `16..186` label, `190..290`
input, `300..484` current-value label, leaving symmetric 16 pt margins. An earlier 380-wide
version truncated both the row labels and the `now: …M` values in every locale, so do not
"tidy" this back toward the main panel's width.

**The main panel's content height is 612 and must stay ≤ 656.** The minimum supported
screen is 1366×768, which leaves roughly 673 points once the menu bar and Dock are removed.
An earlier attempt kept the three fields in the main panel and merely hid them with
`setHidden_`, reserving their space; that reached 732 and pushed the Save button and title
bar off a 768-tall screen. Reserving space is not free, and this panel is a fixed-height
view with hand-placed coordinates, so genuinely collapsing it would mean recomputing every
widget below.

**A missing window and a blank field are the same input.** `adv_value(key)` returns `""`
when `ui` has no widget for that key, so never opening the advanced window is byte-identical
to leaving its fields blank — no extra branch exists anywhere in the save path, and the
frozen `plan_settings_save` / `prepare_settings_config` contract is untouched. It looks the
widget up on every read rather than capturing it, so a dead window cannot leave a live
reference behind feeding ghost values into a save.

**Lifetime is bound in both directions, and one direction is easy to miss.**
`parent.addChildWindow_ordered_` binds **parent → child** only: ordering the main panel out
takes the child with it. It does **nothing** for the child's own close button. The first
implementation had only that half, so clicking the advanced window's X left
`ui["adv_panel"]` and the three field refs pointing at a closed window — and `adv_value()`
would read `stringValue()` off it and apply it to the next Save. **Looking the widget up
on every read does not prevent ghost values by itself; something has to clear the ref.**

So both panels set `setDelegate_(handler)`, and `Handler.windowWillClose_` splits on
`notification.object()`: the child routes to `close_advanced()`, the main panel to
`close_main_panel()`. Every teardown path — Save, the main X, the child X — goes through
those two functions and nowhere else.

- `close_advanced()` runs `removeChildWindow_`, clears the delegate, orders out, and nils
  `ui["adv_panel"]` plus the three field refs. Reopening therefore always builds a fresh
  blank child, never revives a closed one — which is what keeps "blank means keep" from
  depending on a window's history.
- `close_main_panel()` tears the child down **first**, then the main panel. Reversed, the
  child can sit on screen without its parent, and this app is `LSUIElement` with no Dock
  icon, so the user has no way back to it. `open_advanced_limits()` refuses to build
  anything when there is no main panel for the same reason.
- Both panels set `setReleasedWhenClosed_(False)`. A window created with
  `initWithContentRect:` is released on close by default. This is **not** about the
  delegate receiving a freed object — `windowWillClose:` is delivered *before* the release,
  so the callback itself is safe. It is about everything after: `ui` and the cleanup
  functions hold explicit references, and letting Cocoa decide the window's lifetime on
  close would leave those pointing at a deallocated object. Turning it off keeps object
  lifetime under the explicit control of the Python teardown flow.
- `close_advanced()` carries a re-entrancy flag. `orderOut_` posts no close notification
  today, so nothing recurses — but a later change to `close()` would make delegate →
  cleanup → close → delegate loop silently, and the flag is what stops that from being
  discovered at runtime.

**The button and the window title use different strings.** `s_limit_advanced_button`
(≤ 20 chars) labels the 132 pt button in the main panel; the longer `s_limit_advanced` is
the child window's title, where the title bar has room. `s_limit_note3` is capped at
40 chars because it shares its row with that button — it states only that the `%` wins
over an absolute limit. All three keys exist in en/ko/ja/es.

**Calibration is not useless in exact mode.** The gauge percentages come from the server
there, but `spike_info()`/`is_spike()` weigh burn against `RUNTIME["session_limit"]`, so a
badly calibrated limit still produces phantom or missing spike alerts. `s_limit_note2`
says both halves; do not shorten it to "exact mode ignores these limits".

The consequence: **the stored limit is only meaningful relative to the estimator that
produced it.** Any change to parsing, deduplication, weighting, or windowing shifts
`current_estimated_usage`, which invalidates every limit a user has already calibrated —
their gauges silently move, with no error and no prompt, and their previously accurate
reading becomes wrong. Estimator changes are therefore user-visible even when the code
change looks internal. Say so in the release notes, and treat "calibrated users must
recalibrate" as part of the change's cost.

---

## Privacy

The app reads users' Claude Code transcripts. It must never expose their contents.

**[NEVER] print, log, or write out message bodies, project paths, or session IDs** — not
to stdout, not to the debug log (`~/claudepet_debug.log`, enabled by
`CLAUDE_PET_DEBUG=1`), not into an error message, not into a crash report, not into a
test fixture derived from real data. There is no authorization path for this and no
debugging need that justifies it; log counts and shapes instead.

The only things that may leave the parser are the aggregates it is built to produce:
timestamps, weighted totals, and the lowercased model string. Note that log **file
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
4. **The universal build needs a `universal2` Python** from python.org (pyenv's Python
   is single-architecture). `release.sh` checks with `lipo -archs` and refuses otherwise.
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
