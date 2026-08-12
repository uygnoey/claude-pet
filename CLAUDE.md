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
window with an animated sprite and usage gauges), written in Python against PyObjC
(AppKit/Foundation), and shipped as a self-contained, Developer ID-signed and
Apple-notarized `.app` bundle built with py2app.

**`claude_pet.py` is essentially the whole app** — about 2,700 lines containing config,
i18n (en/ko/ja/es), log parsing, the usage estimator, OAuth/keychain token reading, the
Admin API client, the AppKit UI, the settings panel, the updater, and the uninstaller.
There is no package structure to navigate. Use `grep -n` on symbol names; line numbers
in any document (including this one) drift as the file changes, so treat every line
number as approximate and locate code by symbol.

---

## Repo layout

| Path | What it is |
| --- | --- |
| `claude_pet.py` | The application. Everything below the UI layer lives here too. |
| `tests/test_log_estimate.py` | Unit tests for the log estimator (`parse_usage_entries`, `compute_usage`). |
| `build_app.sh` | Fast local build: assembles `ClaudePet.app` from `claude_pet.py` + `frames/`, no signing. `install` / `update` subcommands. |
| `release.sh` | Real release: py2app build → Developer ID sign → notarize → staple → zip/dmg. |
| `setup.py` | py2app configuration. |
| `launcher.c` | Tiny Mach-O launcher — the bundle executable must be Mach-O to be code-signable. |
| `entitlements.plist` | Hardened-runtime entitlements for signing. |
| `frames/` | Sprite frames for the built-in pet, plus `frames-manifest.json`. |
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
./build_app.sh install    # local build → /Applications → restart. For day-to-day testing.
./build_app.sh update     # swap claude_pet.py in the installed bundle and restart. Fastest loop.
./release.sh build        # py2app build only, unsigned. Safe to run.
```

`build_app.sh` is unsigned and local — use it freely for development.

**[NEVER] run bare `./release.sh`.** With no argument it defaults to `all`
(`case "${1:-all}"`) and runs build, sign, notarize, universal, and dmg in one
invocation. **The ban is not about signing** — an authorized release operator may run
those same actions individually. It is that a combined command destroys the per-step
recording and stop-on-failure the authorization is conditioned on, so it stays forbidden
for everyone, operator included. Same ground as `all` and `ship` below.

The subcommands are **not** uniformly forbidden. Four tiers, with full effects and the
exact conditions under [Release procedure](#release-procedure) step 3:

- **`build`** — unsigned local build. Ordinary work for development, run it freely. As
  *the release's* artifact build (step 3) it is still ordinary work by tag, but it sits in
  the execution phase and waits for the gate like everything else there.
- **`publish`** — **[ASK]**. Writes to the user's GitHub releases via their `gh` auth and
  performs no signing, so the user can authorize it, per-instance.
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

**4. `cache_creation` nested fields sum to the flat field.** Within one usage object,
`cache_creation["ephemeral_5m_input_tokens"] + cache_creation["ephemeral_1h_input_tokens"]`
equals the flat `cache_creation_input_tokens`. `_weigh_usage()` relies on this, and
defensively weights any unclassified remainder (`flat - 5m - 1h`) at the 5m rate. Older
logs have no `cache_creation` dict at all; those fall back to the flat field.

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

It returns `(total, noncache)` where `noncache` excludes the cache-read term.
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
own UI. `fmt_reset()` maps a falsy reset to the literal string `"-"`.

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

### Estimate bugs are never fully invisible in exact mode — but be precise about where

The claim is true, and what stays clean is narrower than "the pill": the gauge
**numbers** are server-derived, but three other visible paths are not. State it that
way; both over-claims are easy to make.

**Where the estimate does NOT reach in exact mode.** The gauge percentages are drawn by
`draw_exact_pill()` from the server rows in `state["oauth"]`. Get the dispatch right,
because it is a chain and not a pair: the pill draws `draw_api_pill()` when
`RUNTIME["mode"] == "api"`, **`elif state["oauth"]`** `draw_exact_pill()`, and only below
that reaches `draw_sub_pill()`, the renderer for estimate output. So the server rows win
when they exist *and* the mode is not `api`. A weighting or parsing bug therefore
**cannot** move the displayed percentages of a logged-in user. That is a statement about
the **numbers**, not about the pill as a whole — the bar drawn under them is path 1
below.

**Where it does reach.** `compute_usage()` runs on every 30-second refresh regardless of
whether exact data is available, and **three** paths carry its output into visible
behaviour. Re-derive this list from the source before relying on it as complete: it has
been wrong twice already — once listing two paths and missing the bar, once missing the
greeting suppression now folded into path 2.

1. **The session bar turns red — inside the exact pill itself.** `draw_exact_pill()`
   computes `spiking = bool(spike_info(stats)) and i == 0` from `state["stats"]`, the
   estimator's output, and fills that bar `COL_BAD` instead of `bar_color(pct)`. So an
   estimator spike repaints a bar whose *number* came from the server. Two asymmetries
   worth knowing: it is the **first row only** — the session row, since exact rows are
   sorted by `_label_order()`, which ranks session `0` — and `spike_info()` is truthy for
   a session, weekly, **or** opus spike, so a weekly spike reddens the session bar. The
   `%` text beside it is untouched. (`draw_sub_pill()`, the estimate-mode renderer, is
   the one that colours per gauge, via `sp.get(keys[i])`.)
2. **Spike → the pet, and it outranks the server.** `current_mood()` consults
   `spike_info(state["stats"])` and returns `"failed"` *before* it reaches the exact-mode
   branch that derives a mood from the server percentage, so a false spike from the
   estimator overrides a perfectly good server reading. Three further effects hang off
   that same signal, which is why this is one path and not four: `tick_()` forces a
   repaint for as long as a spike is live; the pet is tinted by a pulsing spike-coloured
   overlay that exists on no other path; and the **mouse-proximity greeting is
   suppressed**, since its guard includes `not spike_info(state["stats"])` — so a phantom
   spike also stops the pet waving when you approach it.
3. **The session-reset greeting.** The refresh worker compares the previous refresh's
   `session["pct"]` against the current one and plays the jump animation when it crosses
   from above 5 to below 1. Both values come from `compute_usage()`; the OAuth rows are
   never consulted here, and the comparison carries no mode guard.

**The exception — API mode.** Paths 1 and 2 are both suppressed there, but by **two
independent mechanisms**, and collapsing them produces a plausible-sounding false
statement. First, `spike_info()` returns `None` outright when `RUNTIME["mode"] == "api"`,
which kills the signal itself: mood falls through to the exact branch, the overlay never
draws, the greeting is no longer suppressed. Second — and this is the one to state
carefully — **the session bar is not "restored to `bar_color(pct)`" in API mode; it is
not drawn at all.** The dispatch above tests `RUNTIME["mode"] == "api"` *first*, so
`draw_api_pill()` runs and `draw_exact_pill()` is never reached. **Path 3 has neither
guard** and still fires in API mode. So the correct summary is: spikes affect the session
bar and the pet in subscription mode only, while the session-reset jump is driven by the
estimator in every mode.

The practical consequence: a parsing or weighting regression shows up as phantom spike
alerts — a red session bar and an alarmed, tinted pet — and a pet celebrating a session
reset that did not happen, not as wrong numbers on a logged-in user's gauges.

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

**Version and changelog can be out of step, and that is meaningful.** `RELEASE_NOTES.md`
may already contain a section for a version that `APP_VERSION` has not yet reached. That
is the expected state after an implementation phase and before an authorized release: the
notes are written as part of the work, the bump is not. **Do not "fix" the mismatch by
bumping `APP_VERSION`** — the mismatch is the signal that step 1 has not been authorized
yet. To see where things stand, read `APP_VERSION` in `claude_pet.py`, the newest heading
in `RELEASE_NOTES.md`, and `git tag | tail -1`.

1. **Bump `APP_VERSION`** in `claude_pet.py`. It must match `CFBundleShortVersionString`.
   The in-app updater compares this against the latest GitHub release tag of
   `GITHUB_REPO` (`uygnoey/claude-pet`), so a mismatch either suppresses a real update or
   offers a phantom one. This is the commit that makes a change a *release commit* under
   [AGENTS.md §6](AGENTS.md#release-steps-are-separately-authorized).
2. **Add a section to the top of the changelog in `RELEASE_NOTES.md`**, in Korean,
   matching the existing style. `release.sh` uses this file as the release body — which
   is why it is a maintained file rather than generated from git history.

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
   git tag | tail -1                  # newest tag
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
   ./release.sh              # [NEVER]  no argument defaults to `all` (case "${1:-all}")
   ```

   **`[ASK-OP]` means the release-operator gate**: user authorization for this artifact,
   all §6 gates recorded first, and executed only by an agent that held **no other role on
   this release — not Developer, not Verifier, not Reviewer, and not Coordinator**. The
   four `[ASK-OP]` subcommands each reach a `codesign` or notarization step, which is what
   puts them in that class.

   **`build` and `publish` are the only two that avoid signing**, and they are not
   equivalent: `build` is ordinary local work, `publish` is [ASK] because it writes to the
   user's GitHub releases.

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
   - **Bare `./release.sh` is not a no-op or a usage message.** The dispatch is
     `case "${1:-all}"`, so omitting the argument runs `all` — build, sign, notarize,
     universal, dmg. Only an *unrecognized* argument prints usage and exits 1.

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
   polls the repo's latest release tag every 6 hours, so pushing it causes **every
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
