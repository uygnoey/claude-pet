# Review record — v0.25 Track A, stale OAuth token

Reviewer: reviewer-a (Claude), independent, Track A of
docs-design/followups-v025-plan-20260913.md. This file is untracked; the Reviewer commits
nothing and ran no git write command. The only files this role created are this record and
scratch files under the session scratchpad (`review-a/`). No production file, test file, or
untracked user-owned path was opened for writing. cwd `/Users/yeongyu/claude-pet`; times
UTC; fenced output verbatim; no token string appears anywhere below (the probes and captures
were grepped for the synthetic fixture prefixes: 0 hits).

## Review round 1

Record opened 2026-09-13T02:29Z, closed 02:40Z.

### 1. What was reviewed

```
$ git rev-parse HEAD
087ecf5b3d0a1dadf9f5df15d7646da399136c88          # brief said 13710db; one docs-only commit past it
$ git show 13710db:claude_pet.py | shasum -a 256 ; git show HEAD:claude_pet.py | shasum -a 256
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -
$ git status --porcelain | grep -v '^??'
 M CLAUDE.md
 M claude_pet.py
$ shasum -a 256 claude_pet.py tests/test_oauth_token_cache.py docs-design/followups-v025-plan-20260913.md
380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8  claude_pet.py
bfb348c9c2f9b7ddd2c0962af413b8b8b25b587ee3efd6092c28d92642e3e14d  tests/test_oauth_token_cache.py
4b3ad55606dfa0f33e0d7f9fd35c44bc51a976432c39310848f86a982e506495  docs-design/followups-v025-plan-20260913.md
```

The docs-only edits the brief said the tree carried (README*, docs/, preview.png) are now
committed as 087ecf5; the uncommitted change is exactly `claude_pet.py` + `CLAUDE.md` plus
the untracked gating file and the Verifier's record. Read in full: `git diff -- claude_pet.py
CLAUDE.md` (221 / 22 lines), `tests/test_oauth_token_cache.py` (704 lines),
`docs-design/track-a-verification-20260913.md` (936 lines, RED §1–7 and GREEN §8–14), the
Track A design, the survey key `oauth`, AGENTS.md §2/§3/§5, CLAUDE.md "exact vs estimate" /
"Privacy" / "Testing policy", and the Windows port's `claude_pet_win.py` (read-only).

### 2. AGENTS.md §2 — Developer–Verifier separation

**Condition A (Developer did not touch the gating assertions) — holds.** The gating file's
SHA256 now (`bfb348c9…`, 704 lines) is byte-identical to the one the Verifier recorded at RED
time (record §2, 01:58Z) and again at GREEN (record §8). No other test file is modified
(`git status`). So no assertion, expected value or fixture literal moved after the RED run.

**Condition B (Verifier has clean hands on the production files) — consistent, not
contradicted.** Nothing is committed yet, so authorship cannot be read from `git log`; what
can be checked is: (a) the Verifier's RED run was taken at `claude_pet.py` = `6f95bc8b…`,
which is HEAD's byte-for-byte; (b) the whole production diff is reproducible from the
Developer's `scratchpad/patch_track_a.py` — I re-applied it to a scratch copy of
`HEAD:claude_pet.py` (never to the tree) and the result differs from the working tree by
exactly one line: the script leaves a duplicated `return None` at the end of
`_fetch_oauth_usage`, which the tree does not have (file mtime 02:09:08Z, script mtime
02:07:38Z — a one-line hand cleanup 90 s after the script ran, before the Verifier's GREEN
section opened at 02:14Z). Note that record §8 calls it "five anchored replacements"; the
script applies six and the tree is script-output minus that one line (N4 below). The
release commit's `Developer:` / `Verifier:` trailers are where authorship is asserted; nothing
in the tree contradicts the record's statement.

### 3. AGENTS.md §3 — red before green

Recorded verbatim: record §7 is the full RED capture (`Ran 9 tests`, `FAILED (failures=21,
errors=2)`, 01:50:32Z at `6f95bc8b…`), with every failing subTest row and its assertion
message; §3 maps each distinct message to the rival it kills (12 × `'tokA' != 'tokB'`,
5 × `1 not greater than 1`, 2 × `'tokA' != 'None'`, two `AttributeError`s, one missing
`last_error` key). GREEN is §9 (9/9, 02:16:29Z at `380a651e…`). The pin test
(`test_401_forced_walk_reaches_native_once_and_respects_declined`) is labelled as green
before and after in its own docstring and in the record, so it is not presented as
red-before-green. Every method's docstring carries the §3 truth table; I checked the three
that matter most (rotation rows 1–4 against six rivals, the `none` row that separates survey
option A, the 429 row of the fail-retry table) and each rival yields a distinct value.

My own reruns:

```
$ python3 -m unittest tests.test_oauth_token_cache -v      # 2026-09-13T02:32:41Z, claude_pet.py 380a651e…
Ran 9 tests in 0.009s

OK
```

### 4. Design points — each one located in the diff

| # | Track A design clause | implemented at (locate by symbol) | pinned by |
| --- | --- | --- | --- |
| 1 | `_oauth_token_cache` gains `src`, `file_sig`, `suspect` | the dict literal; `_remember_oauth_token` / `_forget_oauth_token` are the only writers | items 1, 5 |
| 2 | `_credentials_path()`, `_credentials_sig()` = `(st_mtime_ns, st_size, st_ino)` | `_credentials_path`, `_stat_sig`, `_credentials_sig`; `_read_credentials_file` stats before it opens (docstring explains the order) | item 0 |
| 3 | cached file-sourced token, signature changed or file vanished → drop and read afresh | first block of `_read_oauth_token` (non-force only) → `_forget_oauth_token`, then the ordinary walk | items 1, 1′ |
| 4 | `suspect` → re-validate through prompt-free sources only (file, then `security` CLI iff `src == "cli"`); native never entered | `_revalidate_oauth_token`: `_read_credentials_file()`, then `_token_from_cli()` only when `old_src == "cli" and sys.platform == "darwin"`; **no reference to `_keychain_token_native_bounded` or `_keychain_token_native` in its body** | item 2: `native.calls == 0` across all 20 subTests |
| 5 | replacement replaces; none keeps; `suspect` clears either way | same function: `c["suspect"] = False` before the branch; `_remember_oauth_token` on a hit, `return c["tok"]` otherwise | item 2 (`none`, `file-src-unchanged`) |
| 6 | success → `suspect = False`, `auth_error = False` (and `last_error = None`) | tail of `_fetch_oauth_usage` | item 5 |
| 7 | 401/403 with no replacement after the forced walk → clear `tok`, `auth_error = True` | `_read_oauth_token(force=True)` forgets under the lock in both its no-token exits; `_fetch_oauth_usage` forgets only if the cache still holds the rejected token (lock-busy case); the lock-busy early return now yields `None` under `force` instead of the just-rejected token | item 3; item 3′ pins the unchanged v0.16 walk |
| 8 | every other failure → `suspect = True`, `last_error ∈ {http:<code>, net, parse}` | the HTTPError / generic / parse branches of `_fetch_oauth_usage`; `raw = r.read()` moved inside the transport `try`, decode+parse in its own | item 5 (5 classes) |
| 9 | `fetch_exact_usage`: failed fetch cached `OAUTH_FAIL_RETRY_SEC = 60`, **except `http:429` → 180** | `OAUTH_FAIL_RETRY_SEC = 60` beside `OAUTH_CACHE_SEC`; `if err and err != "http:429": _oauth_cache["t"] = now - (OAUTH_CACHE_SEC - OAUTH_FAIL_RETRY_SEC)` | item 4 (500/URLError 1-2-3; 429/success 1-1-2) |
| 10 | nothing new rendered; `roam_summary_text` memo key unchanged | the diff touches only the OAuth region; the memo key still reads `bool(OAUTH_STATUS.get("auth_error"))`; `test_v024_release_contract`'s AST pin and `test_companion_motion`'s formatter test both `ok` in my full run | — |
| 11 | `_dbg` lines: codes and booleans only, never token bytes | the eight added `_dbg` calls (§5 below) | item 6 |
| 12 | Windows inherits (file is its only source there) | both the walk and `_revalidate_oauth_token` guard CLI/native on `sys.platform == "darwin"`; rotation test runs a `win32` subTest | items 1 (win32), 1′ (win32) |

### 5. Privacy — token bytes cannot reach `_dbg` or an exception message

Enumerated from the diff, every added diagnostic and its arguments:
`("read_oauth: file sig changed; vanished?", sig is None)`,
`("read_oauth: final tok?", bool(tok), "src", src-or-None, "declined?", bool)`,
`("read_oauth: revalidate src", src, "changed?", tok != c["tok"])`,
`("read_oauth: revalidate found nothing; keep src", old_src)`,
`("oauth fetch: http", code, "attempt", attempt)`,
`("oauth fetch: net", type(e).__name__, "attempt", attempt)`,
`("oauth fetch: parse", type(e).__name__)`,
`("oauth fetch: ok rows", len(rows) if rows else 0)`. Values are booleans, ints, the
source name (`file`/`cli`/`native`) and an exception *class name*; no path, no header, no
body. No exception is constructed with a token; `HTTPError` is consumed via `.code` only;
`_read_credentials_file` swallows everything, `_credentials_sig` swallows `OSError` (the only
class `os.stat` raises for a real path). Item 6 pins the log against the token and the word
"Bearer" under `CLAUDE_PET_DEBUG=1` with HOME redirected. Both full-suite captures and my
probe output contain 0 occurrences of the synthetic token prefixes.

### 6. Native Keychain reachability and 429 — checked, plus independent re-derivation

`_revalidate_oauth_token` is the only automatic re-validation and cannot reach the native
reader (§4 row 4). 429 keeps 180 s (§4 row 9). To satisfy AGENTS.md §5 ("presumed wrong
until reproduced by a non-author") I re-ran the Verifier's two probes from my own script
(`scratchpad/review-a/probe_review_a.py`, written without reading their probe's code; same
fixture as record §12: HOME → fresh temp dir before import, `_token_from_cli` /
`_keychain_token_native_bounded` / `urlopen` stubbed, raw `_keychain_token_native` fails the
run if reached, `time` shimmed), once against a copy of the tree (`380a651e…`, 02:33:52Z) and
once against a copy of HEAD (`6f95bc8b…`, 02:33:55Z). Counts only:

| probe | tree | HEAD |
| --- | --- | --- |
| A — darwin, file-sourced token, file removed, `declined` False, native → not-found: next read returns / CLI calls / native calls | None / 1 / 1 | dead token / 0 / 0 |
| B — darwin, CLI blocked, native always answers the dead token, server always 401; `fetch_exact_usage()` every 30 s × 21 (600 s): native / CLI / requests / `auth_error` / `declined` | 12 / 12 / 22 / True / False | 5 / 5 / 8 / True / False |
| C (new) — win32, file-sourced token; file rewritten mid-write (unparseable, new mtime); then restored at the same instant; then after `OAUTH_TOKEN_RETRY`+1: reads | live → None → None → live (CLI 0, native 0) | live → live → live → live |
| D (new) — darwin, native-sourced token, one 500: `suspect` after / CLI Δ / native Δ during the next read / `suspect` after | True / 0 / 0 / False | key absent / 0 / 0 / absent |

A and B reproduce the Verifier's numbers exactly. D confirms the design's literal choice: a
native-sourced token re-validates through the file only (CLI is consulted only for a
cli-sourced token), and never through native. C quantifies the torn-read cost the Verifier
named in note 2: on Windows one unparseable read costs `OAUTH_TOKEN_RETRY` = 120 s of
estimate mode; before the change the file was never re-read, so the cost was 0 s.

### 7. Windows port (`/Users/yeongyu/claude-pet-windows/windows/claude_pet_win.py`, read-only)

The port has no token code of its own. Its every touch of this area: `cp.OAUTH_STATUS.get("auth_error")`
in the memo key and the `⚠` tail (two sites), `cp._oauth_cache["t"] = 0.0` (double-click,
settings save), `cp.fetch_exact_usage()` in the refresh worker. None reads `last_error`,
`_oauth_token_cache`, or `_token_from_file`, so the widened `OAUTH_STATUS` dict and the new
cache keys change nothing it sees. `windows/tests/` has no oauth/token reference (`grep -rn`
→ nothing). The file parses (`ast.parse`). On win32 both `sys.platform == "darwin"` guards
hold, so the file-signature branch is the port's only rotation signal, as the design says,
and the gating rotation/vanished tests exercise it under `win32`. The `windows` branch's own
`claude_pet.py` is still `6f95bc8b…` — it receives this change when main is merged into
`windows`, which the plan assigns to the Coordinator after the tracks land.

### 8. CLAUDE.md paragraph — checked sentence by sentence

Every claim maps to a row of §4. Two precision notes, neither wrong enough to block: "re-checked
against that signature on **every read**" — every non-forced read (the force path skips the
check and re-reads the file at the end of the walk instead, same outcome); "status codes,
exception class names and booleans **only**" — the lines also carry the source name and a row
count, neither sensitive. The pre-existing sentence about `⚠` on `OAUTH_STATUS["auth_error"]`
(pill section) is still accurate. No other document mentions the old shapes.

### 9. Full suite (reviewer's own run)

```
$ python3 -m unittest discover -s tests -v      # started 2026-09-13T02:29:30Z, finished 02:33:55Z, repo root
Ran 556 tests in 264.737s

FAILED (failures=49, errors=8, skipped=7)
exit=1
```

Capture: `scratchpad/review-a/full-suite.txt` (2045 lines). Classification, from
`grep -E '^(FAIL|ERROR): '` and the distinct `AssertionError` lines:

| module | count | cause |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | `setUp` hash pin: `'380a651e…' != '6f95bc8b…'` |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`, one per class) | `claude_pet.py changed after the shared-lock/version harness was reviewed` |
| `test_v024_release_contract` | 1 FAIL (`test_v024_version_and_final_source_pins_propagate`) | the two `REVIEWED_APP_SOURCE_SHA256` pins vs the final file |

48 + 8 + 1 = 57 = 49 + 8. **No `FAIL:`/`ERROR:` header names `test_oauth_token_cache`**; all 9
of its methods end `ok`. The 7 skips are the loud opt-in ones (3 × `test_v020_boundaries`,
2 + 2 × `test_updater` live checks). Counts and distribution are identical to the Verifier's
run (record §10) and the Developer's (`scratchpad/fullsuite.txt`). The hash-pin refusals are
the expected fallout of any `claude_pet.py` edit and are **not** re-pinned here — three pin
sites, not the one the brief named (record §10 already corrects this); the re-pin is a
release-gate step.

### 10. Non-blocking notes (N-numbered; none fails the design)

- **N1 — docstring overclaim in `_read_oauth_token`.** The new paragraph says the two
  cache-bypass cases "둘 다 프롬프트 없는 경로만 탄다". True of the `suspect` case; for the
  signature case what follows the forget is the *ordinary walk*, which on darwin reaches the
  native reader when the file yields nothing and `declined` is False (Probe A). Design-
  conformant ("read afresh"), no new prompt path relative to a cold start, and `src == "native"`
  users — the v0.16 "Allow once" class — never enter this branch; but the sentence will
  mislead the next reader. Recommend rewording before the release commit (comment-only edit;
  the hash pins are already moved).
- **N2 — 401/403 in the 60 s set (Probe B, reproduced).** A dead Keychain token with the CLI
  blocked now cycles native/CLI/request every 60 s instead of 180 s. Letter of the design;
  Coordinator decision whether `http:401`/`403` should join `http:429` in keeping
  `OAUTH_CACHE_SEC`. My recommendation: yes — retrying a token the server has rejected cannot
  succeed sooner, and the forced walk is the one automatic path that can prompt. Needs its own
  red fixture (item 4 has no 401 row) if adopted; not part of this round.
- **N3 — torn read costs 120 s on Windows (Probe C).** Bounded; hinges on how Claude Code
  rewrites the file (survey open question 2, still open). A refinement that keeps the previous
  token when a *present* file yields no token (distinct from "vanished") would need a design
  amendment and its own red fixture; the current tests pin only "vanished → None".
- **N4 — record §8 wording.** "the same text the Developer's patch script applies as five
  anchored replacements": the script applies six edits and its output differs from the tree by
  one duplicated `return None` line (§2 above). Affects the record's accuracy, not either
  §2 condition.
- **N5 — `_token_from_file` has no caller** in `claude_pet.py` now (wrapper over
  `_read_credentials_file()[0]`); kept so `run_native_smoke()`'s patch list in
  `tests/test_companion_motion.py` still resolves. Do not delete one without the other.
- **N6 — no-token cycle inherits the previous `last_error` class** (record note 3), so
  `fetch_exact_usage` may pick 60 s or 180 s from a stale class when no request was made.
  Harmless (no request is sent; the token path has its own `OAUTH_TOKEN_RETRY`).
- **N7 — check-then-act in the 401 lock-busy path.** `if c["tok"] == tok: _forget_oauth_token(c)`
  runs outside the lock; worst case a concurrent reader's fresh token is forgotten and
  re-walked next cycle. Bounded; the pre-change file path had the same non-atomic writes.
- **N8 — HEAD.** The brief named 13710db; the checkout is 087ecf5 (docs-only), `claude_pet.py`
  identical at both, so every hash in the Verifier's record still refers to the right bytes.

### 11. Verdict

**PASS (round 1).** Conditions A and B of AGENTS.md §2 hold as far as the tree can show;
the RED run is recorded verbatim and reproduced by rival; all twelve design clauses are
located in the diff and pinned; no token bytes can reach a diagnostic or an exception;
automatic re-validation cannot reach the native reader; 429 keeps 180 s; the Windows port's
three touch points are unaffected; the CLAUDE.md paragraph is accurate to two precision
notes; the full suite's only non-green outcomes are the 57 expected hash-pin refusals. No
blocking items. N1 is the one note I would want addressed before the release commit; N2 is
a design question for the Coordinator.

## Review addendum — the 2026-09-13 keychain-rotation incident (two more gating tests)

Record opened 2026-09-13T02:57Z, closed at the timestamp on the last line. Same role, same
rules: no git write command, no production or test file opened for writing, no untracked path
touched except this record; scratch files under `<scratch>/review-a-addendum/` (`<scratch>` =
the session scratchpad; files `head/claude_pet.py`, `tree/claude_pet.py`, `my_red.txt`,
`my_green.txt`, `full-suite.txt`, `probe_review_a_addendum.py`, `probe.out`). Every capture
was grepped for the fixture token prefixes (`synthetic-access-token`, `probe-token`): 0 hits.
No token string appears below.

### A1. What was reviewed

```
$ git rev-parse HEAD                                        # 02:57Z
8c900f65ea44ce30cb2d3d8d741468fd0d7f9afb                    # brief said 087ecf5; one docs-only commit past it
$ git diff 087ecf5 HEAD --stat -- claude_pet.py tests/
(empty)
$ git show HEAD:claude_pet.py | shasum -a 256
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -
$ shasum -a 256 claude_pet.py tests/test_oauth_token_cache.py docs-design/track-a-verification-20260913.md   # 02:57:44Z
380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8  claude_pet.py
1adccf00f5d6aa3342851d88b44290cc0069b5a83c1eba7dd722b47c7aa7d3f5  tests/test_oauth_token_cache.py
b78fef172709dae2cad0edc4fb9b9408f683af88d0bc694889d932ee36499ad9  docs-design/track-a-verification-20260913.md
$ wc -l tests/test_oauth_token_cache.py docs-design/track-a-verification-20260913.md
     894 tests/test_oauth_token_cache.py
    1302 docs-design/track-a-verification-20260913.md
```

`claude_pet.py` is `380a651e…` — the bytes round 1 reviewed — so **there is no production
change in this addendum**; the brief's "(none)" holds. The brief's `git diff --
tests/test_oauth_token_cache.py` is empty because the file is untracked; the delta under review
is `bfb348c9…` (704 lines, round 1) → `1adccf00…` (894 lines), reconstructed in A2. Read in
full: record §A.1–A.7 (lines 937–1302), the two methods and their two helpers (file lines
708–890) plus the module-docstring paragraph (42–47), the fixtures (113–308) again, and the
HEAD and tree bodies of `_read_oauth_token`, `_keychain_token_native_bounded`,
`_token_from_cli`, `_fetch_oauth_usage`, `fetch_exact_usage`.

Tree at 02:57Z: ` M CLAUDE.md`, ` M claude_pet.py`, ` M docs/index.html` — the last is not
Track A's (record §A.7 notes it too); at 03:05:21Z only the first two remained. HEAD moved
087ecf5 → 8c900f6 between the Verifier's addendum and this one; that commit touches `docs/`
only, so every hash in the record still names the right bytes.

### A2. AGENTS.md §2 — Condition A verified byte-for-byte by reconstruction

No copy of the gating file at its RED-time hash exists anywhere (`find <scratch> -name
'test_oauth_token_cache*'` → nothing), so the record's "purely additive" claim cannot be
checked by diffing. It can be checked by reconstruction: delete from the current 894-line file
the module-docstring paragraph (lines 42–47) and section 7 (lines 707–890: the comment block,
`server_accepting`, `sent_names`, the two methods) and hash what is left:

```
MATCH: remove lines [42..47] and [707..890] -> sha256 bfb348c9c2f9b7ddd2c0962af413b8b8b25b587ee3efd6092c28d92642e3e14d, 704 lines
```

That is the exact hash and line count of the file the Verifier recorded at RED (record §2,
01:58Z) and GREEN (§8), and that round 1 reviewed. So every assertion, expected value and
fixture literal of the nine earlier methods is byte-identical to what was observed RED at
01:50Z, and nothing was reordered. **Condition A holds.** **Condition B:** `claude_pet.py` is
`380a651e…` before the addendum (record §A.1, 02:45Z), after it (§A.2, 02:49:59Z) and now —
the Verifier's addendum touched no production file. As in round 1, authorship itself is
asserted only by the release commit's trailers; nothing in the tree contradicts the record.

### A3. AGENTS.md §3 — RED reproduced by a non-author, and the baseline confirmed

Record §A.3 does show what the brief requires: the run inserts the scratch HEAD copy ahead of
the repo root on `sys.path` and prints `claude_pet.__file__` (the scratch path) and the SHA256
of the module actually imported (`6f95bc8b…`); the paragraph above the capture explains why
`PYTHONPATH` alone could not have done it (`-m unittest` puts the cwd first). I read the
capture itself (`scratchpad/addendum_red.txt`): same two lines, `FAILED (failures=3)`, 0 token
hits.

My own reproduction, from a fresh `git show HEAD:claude_pet.py` into my own scratch directory
(03:00:26Z):

```
$ shasum -a 256 <scratch>/review-a-addendum/head/claude_pet.py
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4
$ python3 -u -c "import sys; sys.path.insert(0, '/Users/yeongyu/claude-pet'); sys.path.insert(0, '<scratch>/review-a-addendum/head'); import claude_pet; print(claude_pet.__file__); ...; import unittest; unittest.main(module=None, argv=['unittest', '-v', '-k', 'rotation_lag', '-k', 'pending_native', 'tests.test_oauth_token_cache'])"
claude_pet.__file__ = <scratch>/review-a-addendum/head/claude_pet.py
sha256 = 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4
FAIL: test_pending_native_does_not_block_cli_recovery (...) (step='cache after the pending forced walk')
AssertionError: 'tokA' != 'None' : the rejected token survived a forced walk that found no replacement
FAIL: test_pending_native_does_not_block_cli_recovery (...)
AssertionError: None is not true : pending native: the cycle after the cooldown did not recover exact mode
FAIL: test_rotation_lag_recovers_on_the_next_cycle_without_restart (...)
AssertionError: None is not true : rotation lag: the next cycle did not recover exact mode
Ran 2 tests in 0.002s
FAILED (failures=3)
exit=1
```

Three failures for two methods (the `subTest` row counts separately), each the message its
docstring's "today" column predicts; identical to §A.3. GREEN on the tree (03:00:30Z):
`claude_pet.__file__ = /Users/yeongyu/claude-pet/claude_pet.py`, `380a651e…`,
`python3 -m unittest tests.test_oauth_token_cache -v` → `Ran 11 tests`, `OK`, all nine earlier
methods still `ok`.

**Truth tables.** I recomputed each rival column against the assertions rather than reading
the cells: forced-walk-re-reads-file-only fails cycle 1's `sent_names == [tokA, tokA]` and
`cli.calls == 2` (test 1) and `cli.calls == 2` / `native.calls == 1` (test 2); native-first
fails `native.calls == 0` at cycle 1 (test 1); keep-at-pending fails the cache row and
`sent_names(1) == [tokB]` (it sends `[tokA, tokB]`); pending-as-declined fails the final
`declined` assertion; native-gate fails `rows` at T+121 and `native.calls == 1`; today fails
`rows` at T+61 / T+121 and the cache row. Every listed rival is separated on at least one
assertion. One rival the tables do not list is also separated: the forget half of the fix
without the `OAUTH_FAIL_RETRY_SEC` half (T+61 and T+121 are still inside a 180 s failure
cache → `rows` None). "Cooldown applies to force mode" is unreachable, as both docstrings say:
`_read_oauth_token(force=True)` is only called after a request carried a token, a token is
only in the cache via `_remember_oauth_token`, and that zeroes `next_retry`.

**Why cycle 1 goes through `fetch_exact_usage()`** — the Verifier's argument in §A.2, checked
by my probe (variant V in A4): on HEAD, cycle 1 through `_fetch_oauth_usage()` and cycle 2
through `fetch_exact_usage()` at T+61 (R) / T+121 (P) both return rows — so both tests would
be GREEN on the pre-fix module and prove nothing. The failure cache is the discriminator, and
it lives in `fetch_exact_usage()`.

### A4. AGENTS.md §5 — record §A.5 reproduced from my own probe

`<scratch>/review-a-addendum/probe_review_a_addendum.py`, written from the record's stated
procedure without reading `probe_addendum.py` / `probe_addendum_q.py`; same isolation as the
tests (HOME → fresh temp dir before import, `_token_from_cli` /
`_keychain_token_native_bounded` / `urlopen` replaced, raw `_keychain_token_native` fails the
run if reached, `time` shimmed); run 03:03:00Z once against `head/claude_pet.py` (`6f95bc8b…`)
and once against `tree/claude_pet.py` (`380a651e…`), polling `fetch_exact_usage()` every 30 s.
Deterministic on the stubs — these are read-outs of the code, not sample observations. Names
and counts only:

| scenario | HEAD `6f95bc8b…` | tree `380a651e…` |
| --- | --- | --- |
| R cycle 1 (CLI still serves the old item at the first 401) | rows None, sent `[old, old]`, cache old, `auth_error` True, cli 2, native 0 | identical |
| R, CLI serves the new item from the next poll on | first recovery **T+180**, that cycle sends `[old, new]`; cli 3, native 0 | first recovery **T+60**, sends `[old, new]`; cli 3, native 0 |
| P cycle 1 (CLI empty, native pending) | rows None, sent `[old]`, `next_retry` T+120, **cache old**, cli 2, native 1 | as HEAD but **cache none** |
| P, CLI serves the new item from the next poll on, native still pending | first recovery **T+180**, sends `[old, new]`; native still 1 | first recovery **T+120**, sends `[new]` only; native still 1 |
| Q, in-process CLI serves nothing until T+X, native pending / not-found (both states gave the same rows) | X=0 → T+0; 60 → T+180; 300 → T+360; 900 → T+900; native entries 0/1/2/5 | X=0 → T+0; 60 → T+120; 300 → T+360; 900 → T+960; native entries 0/1/3/8 |
| V, cycle 1 via `_fetch_oauth_usage()` instead | cycle 2 via `fetch_exact_usage()` at T+61 (R) / T+121 (P) → **rows** on HEAD | rows |

These match record §A.5 line for line (their T+181 is my T+180 — a grid choice; their request
totals are higher because their probe keeps polling past recovery and mine stops at the first;
the native-entry counts are identical). §5's "reproduced by a non-author" is satisfied for
§A.5 points 1–3.

### A5. Mechanisms R and P, from the code

**Which of R and P the v0.24 module (`6f95bc8b…`) could not recover from: neither.** On that
module `_read_oauth_token()` returns a cached token before it looks at the cooldown
(`if c["tok"] and not force: return c["tok"]` precedes `time.time() < c["next_retry"]`), so a
pending-native cooldown never withholds the next cycle's request; every cycle after the 180 s
failure cache re-sends the cached token, receives 401, and `_read_oauth_token(force=True)`
consults `_token_from_cli()` *before* `_keychain_token_native_bounded()`. The moment the
in-process CLI serves the rotated item the retry carries it, the 200 clears `auth_error`, and
the cache is replaced — R and P alike, at the first fetch cycle ≥ 180 s after the failure (A4
rows 2 and 4). What v0.24 could **not** do is (i) recover inside the 180 s failure cache —
there was no `OAUTH_FAIL_RETRY_SEC` — and (ii) stop re-sending the rejected token meanwhile:
under P the pending exit kept it (`'tokA' != 'None'`), under R it heads every cycle. Neither
R nor P, as the brief states them, holds v0.24 in `auth_error` for 76 minutes: row Q shows
recovery within one grid step of the CLI serving the new item, for both native states. A
76-minute outage on v0.24 therefore requires the `security` CLI *inside the app process* to
have returned nothing or the old bytes for most of that time while a fresh process got the
new item — record §A.5 point 2's hypothesis, which I endorse as a hypothesis only (§5):
unpinned by any test, and the thing a `CLAUDE_PET_DEBUG=1` log across a rotation would settle
(`read_oauth: cli tok?` / `native st` / `oauth fetch: http` — booleans and codes only). One
candidate shape, offered only as a place to look: `_token_from_cli()`'s docstring says the CLI
blocks when the keychain raises a prompt and its 60 s timeout then yields None; if the
rewritten item's ACL made `security` prompt from the app's process context while a terminal
process is allowed, the app would see None on every walk. That is not evidence.

**The working tree (`380a651e…`) recovers from both**, and the two tests pin it: R at T+60
(the 60 s failure cache), P at T+120 (one `OAUTH_TOKEN_RETRY`, the dead token forgotten at the
pending exit and never re-sent, the native reader entered once and not re-entered while the
CLI answers).

### A6. Isolation and privacy of the two new methods

Same `setUp` as the nine (HOME → temp dir, `_token_from_cli` / `_keychain_token_native_bounded`
stubs, `_keychain_token_native` → failing stub, `urlopen` → fake, `time` → shim,
`sys.platform` → `darwin`), nothing reset between cycles. The two helpers: `server_accepting`
compares the header the fake already recorded to `"Bearer " + token` and returns a body or an
`HTTPError` — it never formats the token; `sent_names` maps to fixture names. Every assertion
message carries names (`'tokA' != 'None'`), as the RED output shows. Captures `my_red.txt`,
`my_green.txt`, `full-suite.txt`, `probe.out`: 0 hits of `synthetic-access-token` /
`probe-token`. No socket, no `security` subprocess, no native call, no GUI, no read of the real
`~/.claude`, `~/.claude_pet`, `~/.claude_pet.json`.

### A7. Full suite (reviewer's own run)

```
$ python3 -m unittest discover -s tests -v      # repo root; started 02:57:41Z, finished 03:02:05Z
Ran 558 tests in 263.089s

FAILED (failures=49, errors=8, skipped=7)
exit=1
```

| module | count | assertion (hashes abbreviated) |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | `'380a651e…' != '6f95bc8b…'` (`setUp` pin of `claude_pet.py`) |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`, one per class) | `claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b…, found 380a651e…` |
| `test_v024_release_contract` | 1 FAIL (`test_v024_version_and_final_source_pins_propagate`) | the two `REVIEWED_APP_SOURCE_SHA256` pins vs `final claude_pet.py is 380a651e…` |

48 + 8 + 1 = 57 = 49 + 8; the two SHA256 strings occur 107 times each in the capture and no
other hash appears in a failure. **No `FAIL:`/`ERROR:` header names `test_oauth_token_cache`**;
its 11 header lines end `ok`, the two new ones included. Skips 3 + 2 + 2 = 7, the loud opt-in
ones (`CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`; `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1` for
the installed-app preflight and the real stapler). 556 → 558 = the two methods. Identical in
count and distribution to record §A.6, and to round 1 §9 plus two. The pins are the expected
release-gate re-pin (three sites) and are not touched here.

### A8. Notes (N-numbered, continuing round 1; none blocks)

- **N9 — N2's blast radius is both rows, not one.** If 401/403 join `http:429` in keeping
  180 s, test 1's T+61 *and* test 2's T+121 go RED (121 < 180). Record §A.7 says "that row
  must move with it"; read it as both rows. After moving both to T+181, test 1 no longer
  separates the tree from HEAD (both recover there — A4 row 2), test 2 still does on the cache
  row and on cycle 2's requests (`[tokB]` vs `[tokA, tokB]`). Coordinator's call, unchanged.
- **N10 — R keeps a "replacement" that is the same bytes.** On the tree, when the forced
  walk's CLI answer equals the rejected token, `_remember_oauth_token` re-caches it and the
  next cycle re-sends it once before walking again. Treating a same-bytes answer as "no
  replacement" would clear the cache and walk fresh at the next cycle; both tests as written
  would still pass (test 1 checks the last bearer and the CLI count, not the whole cycle-2
  sequence). Design freedom, not a defect; noted so the accepted superset is known.
- **N11 — tests authored after the fix.** The two methods were written by the Verifier after
  reading the Track A diff. §3's remedy 1 (pre-fix bytes in a scratch copy) was applied,
  recorded with the imported module's path and hash, and reproduced here by a non-author, so
  the RED is genuine; the discrimination argument rests on the rival enumeration, which A3
  checks. Acceptable; noted because the order is weaker than tests-before-fix.
- **N12 — HEAD.** 8c900f6 (docs-only) since the record's §A.1 (087ecf5); `claude_pet.py`
  byte-identical at 13710db, 087ecf5 and 8c900f6.
- **N13 — Track A's staging set is still `claude_pet.py`, `CLAUDE.md`,
  `tests/test_oauth_token_cache.py`** (plus the two records if the Coordinator wants them
  tracked). `docs/index.html` was modified by another track during this review and is not
  Track A's; stage by name, never by sweep.

### A9. Verdict (addendum)

**PASS.** Condition A verified byte-for-byte by reconstruction (the nine earlier methods and
every fixture literal unchanged; the addendum is additive); Condition B consistent
(`claude_pet.py` unchanged across the addendum, no production change); the RED was observed
against the committed module and the record proves it with `claude_pet.__file__` and the
imported module's SHA256, and I reproduced it from my own scratch copy; GREEN 11/11 on the
tree; record §A.5 reproduced by a non-author; from the code, v0.24 could recover from both R
and P (within 180 s of the CLI serving the rotated item) and the tree now recovers from both,
faster and without re-sending the dead token — the 76-minute outage is explained by neither
and stays an open hypothesis for the Coordinator; no token bytes in any capture; full suite
green apart from the 57 expected hash pins. No blocking items.
Tree at close (2026-09-13T03:08:11Z): HEAD 931681f; tracked modifications  M CLAUDE.md; M claude_pet.py;; claude_pet.py 380a651e…; tests/test_oauth_token_cache.py 1adccf00…
HEAD at close is 931681f (`web: use requested fonts, show the app pill and highlight support`, docs-only: `git diff 8c900f6 931681f --stat -- claude_pet.py tests/` is empty; `git show HEAD:claude_pet.py` is still `6f95bc8b…`), so N12 extends to it and every hash above still names the right bytes. Strict grep of this record for the full fixture tokens (`synthetic-access-token-[A-E]`, `probe-token-(OLD|NEW)`): 0 — the two prefix mentions above are names, not values. 2026-09-13T03:08:36Z
