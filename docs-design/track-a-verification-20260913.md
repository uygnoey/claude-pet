# Verification record — v0.25 Track A, stale OAuth token (RED phase)

Verifier: verifier-a (Claude), Track A of docs-design/followups-v025-plan-20260913.md.
Record opened 2026-09-13T01:41Z. This file is untracked; the Verifier commits nothing
(no `git add`/`commit`/`stash`/`checkout` was run by this role).

Scope of this record: the gating tests were authored and run **before any production
change** (AGENTS.md §3 step 1–2). The only files this role created are
`tests/test_oauth_token_cache.py` and this record. No production file was opened for
writing (§2 Condition B); `claude_pet.py` carries the same SHA256 before and after this
role's work (below). The user-owned untracked files (`diag.py`,
`release/ClaudePet.iconset/`, `release/icon_1024.png`) and every other untracked path were
not touched. The uncommitted docs-only edits the tree already carried (README*, docs/,
preview.png) were left alone.

All commands ran with cwd `/Users/yeongyu/claude-pet`. Times are UTC. Output is verbatim
where fenced.

## 1. What is under verification (read 01:41–01:48Z)

```
$ git rev-parse HEAD
13710dbb4ba9fc1e9b3f1b7d8cda27c3c4381bfa
$ git log -1 --format='%H %s'
13710dbb4ba9fc1e9b3f1b7d8cda27c3c4381bfa docs: site and README refresh after v0.24 — Windows beta, SmartScreen guidance, roadmap
$ shasum -a 256 claude_pet.py
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  claude_pet.py
$ grep -n -E 'OAUTH_FAIL_RETRY_SEC|last_error|file_sig|_credentials_path|_credentials_sig|"suspect"' claude_pet.py
grep rc=1            # none of the design's new names exist yet
$ python3 --version
Python 3.13.7
```

Tracked-tree status at 01:50Z (untracked `docs-design/*`, `diag.py`, `release/*` omitted):

```
 M README.es.md
 M README.ja.md
 M README.ko.md
 M README.md
 M docs-design/release-v024-review-20260912.md   # not mine — was clean in the session's opening snapshot; left alone
 M docs/assets/preview.png
 M docs/index.html
 M docs/llms-full.txt
 M docs/llms.txt
 M preview.png
?? tests/test_oauth_token_cache.py               # this role's deliverable
```

Design read: `docs-design/followups-v025-plan-20260913.md` "Track A" and the survey
report key `oauth` in the session scratchpad (`followups-survey.json`; findings quote the
current code). Symbols read in `claude_pet.py` by `grep -n` (line numbers approximate,
locate by symbol): `OAUTH_USAGE_URL`/`OAUTH_CACHE_SEC = 180`/`OAUTH_TOKEN_RETRY = 120`
(≈2110–2112), `_oauth_cache` (≈2113), `_oauth_token_cache = {"tok", "next_retry",
"declined"}` (≈2119), `_SEC_ITEM_NOT_FOUND = -25300` (≈2123), `_dbg` (≈2135),
`_token_from_file` (≈2147), `_token_from_cli` (≈2156), `_keychain_token_native` (≈2173),
`_native_state`/`_keychain_token_native_bounded` (≈2220–2223), `_read_oauth_token`
(≈2259), `_parse_oauth_usage`/`_rows_from_limits` (≈2454), `OAUTH_STATUS =
{"auth_error": False}` (≈2500), `_fetch_oauth_usage` (≈2503), `_fetch_cli_usage`
(≈2651, returns None unless `CLAUDE_PET_USE_CLI=1`), `fetch_exact_usage` (≈2688).

The bug as it reads from source (not an observation — deterministic): the first
statement of `_read_oauth_token(force=False)` is `if c["tok"] and not force: return
c["tok"]`; `_fetch_oauth_usage` sets `auth_error` in exactly two places (False on 200, True
on a 401/403 whose forced walk found nothing) and `except Exception: return None` for every
other failure with the token untouched; `fetch_exact_usage` writes `_oauth_cache["t"] =
now` before the fetch, so a failure is cached for the full 180 s exactly like a success.

Facts the rotation fixture rests on, checked in a temp directory under the default
`TMPDIR` (`/var/folders/…/T`, APFS) at 01:45Z, before the test was written:

```
ns exact: True 1700000000000000000
half-ms honoured: True int-sec equal: True float differs: True
in-place rewrite keeps inode: True size same: True
replace new inode: True mtime preserved: True
parse_reset_ts(None) -> None
socket.timeout is TimeoutError: True
```

i.e. `os.utime(ns=…)` is honoured to the nanosecond, `open(path, "w")` keeps the inode,
`os.replace` changes it while preserving a pinned mtime — so the fixture can hold the
three stat fields apart.

## 2. The gating file — `tests/test_oauth_token_cache.py`

One `TestCase`, nine methods. Isolation: `HOME` patched to a fresh `mkdtemp` per test
(`setUp` asserts `os.path.expanduser("~")` resolves there before anything else runs);
`_token_from_cli` and `_keychain_token_native_bounded` replaced by recording stubs;
`_keychain_token_native` replaced by a stub that fails the test if reached;
`urllib.request.urlopen` replaced by a scripted fake that records only the
`Authorization` header, compared by fixture name (`tokA`…`tokE`) and never printed;
`claude_pet.time` replaced by a shim whose `time()` is a settable clock (everything else
delegates to the real module); `sys.platform` patched per test to `darwin` or `win32`.
`_oauth_token_cache`, `_oauth_cache`, `OAUTH_STATUS`, `_native_state` are snapshotted in
`setUp` and restored **in place** by `addCleanup`; `reset_state()` between subTests resets
known keys without deleting keys the fixed code may add. `CLAUDE_PET_DEBUG` and
`CLAUDE_PET_USE_CLI` are removed from the environment except where a test sets the former.

Every method's docstring carries the §3 truth table: the rows of the fixture and what each
plausible rival returns. The rivals enumerated, by item of the assignment:

| # | method | gates | rivals shown distinct in the docstring |
| --- | --- | --- | --- |
| 0 | `test_credentials_helpers_resolve_under_home_and_sign_the_file` | `_credentials_path()` under HOME; `_credentials_sig()` None / stable / changes on +0.5 ms same-size rewrite and on new-inode rename | int(mtime)-only, mtime_ns-only, size-only, ino-only |
| 1 | `test_file_token_rotation_is_picked_up_without_restart` (subTest darwin, win32) | rotation served without restart; unchanged file served from cache; Keychain stubs 0 calls | never re-stat (today), always re-read, int(mtime)-only, mtime_ns-only, size-only, ino-only — rows 1–4 of the table; row 2 (content changed, signature preserved) is the one that separates "always re-read" from the design |
| 1' | `test_vanished_credentials_file_drops_the_cached_token` | the design's "or the file vanished" clause, on win32 | keep-serving (today) |
| 2 | `test_non_auth_failure_revalidates_through_prompt_free_sources_only` (subTest 5 failure classes × 4 scenarios) | next fetch after URLError / 500 / 429 / socket timeout / invalid JSON re-validates: CLI replacement → tokB sent; file appeared → tokB (file before CLI); no replacement → tokA kept **and** CLI consulted; native stub 0 calls throughout; the failure itself keeps the token | keep-serving (today), drop-and-re-walk-including-native (survey option A — separated by the `none` scenario), CLI-first re-validation (separated by `file`); the `file-src-unchanged` scenario is GREEN today by construction and only rules out "re-walk everything" |
| 3 | `test_401_with_no_replacement_stops_serving_the_dead_token` | 401, CLI → None, native → (-25300, None): `auth_error` True, `tok` None, read during cooldown None, file tokB after cooldown served | keep-dead-token (today), clear-without-auth_error |
| 3' | `test_401_forced_walk_reaches_native_once_and_respects_declined` | **pin, GREEN before and after by design**: the 401 forced walk reaches native exactly once unless `declined` | none — it gates nothing new; it is here so the fix cannot regress the v0.16 contract, and is labelled as such in its docstring |
| 4 | `test_failed_fetch_retries_within_fail_retry_sec_except_429` | `OAUTH_FAIL_RETRY_SEC == 60 < OAUTH_CACHE_SEC`; request counts at +30 s / +61 s / +181 s for 500, URLError, 429, success | uniform 180 (today), uniform 60 including 429, retry-every-call |
| 5 | `test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything` | each non-auth failure → `suspect` True, `last_error` ∈ {`http:500`, `http:429`, `net`, `parse`}, `auth_error` untouched, token kept; success → `auth_error` False, `last_error` None, `suspect` False | auth_error-only (today), success-clears-auth_error-only |
| 6 | `test_fetch_failure_debug_lines_carry_codes_not_token_bytes` | with `CLAUDE_PET_DEBUG=1` under the patched HOME: a fetch diagnostic names `500` and the network failure; the log contains neither the token nor "Bearer" (timestamp prefix stripped before matching) | no fetch `_dbg` (today), logging `str(e)`/the header |

Items 0, 1', 3' and 6 go beyond the five items named in the assignment. Each is taken
from an explicit sentence of the Track A design (the two helper names; "or the file
vanished"; the v0.16 "no new prompt path" constraint the survey flags; "`_dbg` lines carry
status codes and booleans only — never token bytes"). They are separate methods so the
Coordinator can drop any of them without touching the five; none of the five depends on
them.

Two constraints the fixture deliberately does **not** impose, so the Developer is not
over-pinned: the exact tuple shape of `_credentials_sig()` (only (in)equality across the
three rewrites is asserted), and the wording of the `_dbg` lines (any line containing
"oauth" plus the code / "net" or "URLError" passes).

Hashes at RED time, for the §2 Condition A check (a later `shasum` that differs means the
gating file changed after this record; the diff then shows whether an assertion, expected
value or fixture literal moved):

```
$ shasum -a 256 tests/test_oauth_token_cache.py docs-design/followups-v025-plan-20260913.md   # 01:58Z
bfb348c9c2f9b7ddd2c0962af413b8b8b25b587ee3efd6092c28d92642e3e14d  tests/test_oauth_token_cache.py
4b3ad55606dfa0f33e0d7f9fd35c44bc51a976432c39310848f86a982e506495  docs-design/followups-v025-plan-20260913.md
$ wc -l tests/test_oauth_token_cache.py
     704 tests/test_oauth_token_cache.py
```

## 3. RED

```
$ python3 -m unittest tests.test_oauth_token_cache -v      # 2026-09-13T01:50:32Z, HEAD 13710db, claude_pet.py 6f95bc8b…
Ran 9 tests in 0.011s

FAILED (failures=21, errors=2)
exit=1
```

Per-test outcome (the `subTest` rows are what unittest counts as separate failures):

| method | outcome |
| --- | --- |
| `test_401_forced_walk_reaches_native_once_and_respects_declined` | **ok** — the pin, green as predicted |
| `test_401_with_no_replacement_stops_serving_the_dead_token` | FAIL |
| `test_credentials_helpers_resolve_under_home_and_sign_the_file` | ERROR |
| `test_failed_fetch_retries_within_fail_retry_sec_except_429` | ERROR |
| `test_fetch_failure_debug_lines_carry_codes_not_token_bytes` | FAIL |
| `test_file_token_rotation_is_picked_up_without_restart` | FAIL × 2 (darwin, win32) |
| `test_non_auth_failure_revalidates_through_prompt_free_sources_only` | FAIL × 15 (5 classes × {cli, file, none}); the 5 `file-src-unchanged` rows pass, as the docstring predicts |
| `test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything` | FAIL |
| `test_vanished_credentials_file_drops_the_cached_token` | FAIL |

Distinct error lines, with counts (`grep -E '^(AssertionError|AttributeError)' | sort | uniq -c`):

```
  12 AssertionError: 'tokA' != 'tokB'
   5 AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI
   2 AssertionError: 'tokA' != 'None'
   1 AttributeError: module 'claude_pet' has no attribute 'OAUTH_FAIL_RETRY_SEC'
   1 AttributeError: module 'claude_pet' has no attribute '_credentials_path'
   1 AssertionError: False is not true : no fetch diagnostic carrying the HTTP status code
   1 AssertionError: 'last_error' not found in {'auth_error': False}
```

Mapping to the rivals: the twelve `'tokA' != 'tokB'` are row 1 of the rotation table on
both platforms (never re-stat) plus the ten `cli`/`file` re-validation rows (keep-serving);
the five `1 not greater than 1` are the `none` rows (the CLI was not consulted after the
failure — keep-serving again, and the row that would also catch option A via the native
count); the two `'tokA' != 'None'` are the dead token retained after a 401 and the cached
token served after the file vanished. The two `AttributeError`s are the missing constant
and helper. In every case the message is the one the docstring predicted for "today".

Not in the capture: any fixture token string (`grep -c synthetic-access-token` → 0). The
20 occurrences of "Bearer" are traceback source lines quoting the `assertBearer` method
name.

The full output of the run is appended verbatim in §7.

## 4. Isolation evidence

- `setUp` refuses to proceed unless `os.path.expanduser("~") == <mkdtemp>`; every
  credentials path and debug-log path in the run is under that directory.
- The real `~/.claude`, `~/.claude_pet`, `~/.claude_pet.json` were not read or written by
  the tests. One slip by this role outside the tests, recorded for completeness: an
  `ls -la ~/.claude/.credentials.json` was issued once at 01:50Z while checking the tree
  (metadata listing only, output discarded, no content read, no write). Nothing depends
  on it.
- No socket is opened: `urlopen` is replaced for the whole `TestCase`; `_fetch_cli_usage`
  returns None because `CLAUDE_PET_USE_CLI` is removed from the environment.
- No `security` subprocess and no native Keychain call: both readers are stubbed, and the
  raw `_keychain_token_native` is a stub that fails the test if anything reaches it.
- No GUI was run.

## 5. Expected fallout after the production change

`tests/test_upload_artifact_gate.py` pins `REVIEWED_APP_SOURCE_SHA256 =
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4` for `claude_pet.py`.
Before any production change it still runs:

```
$ python3 -m unittest tests.test_upload_artifact_gate      # 01:51Z
Ran 64 tests in 50.507s

OK
```

Once the Developer edits `claude_pet.py` that module will refuse to run (by design — it
guards the reviewed artifact gate). That refusal is expected during Track A and is **not**
re-pinned by this role; the re-pin belongs to the release gate, after review, at release
time.

## 6. Full suite with the new module present (before any production change)

Run from the repo root, in the background, while the record was being written; a second,
unrelated `unittest discover` process from another session ran concurrently for part of
it (observed by `pgrep` at 01:55Z), which only affects the wall time.

```
$ python3 -m unittest discover -s tests -v      # started 2026-09-13T01:52:05Z
Ran 574 tests in 322.535s

FAILED (failures=21, errors=2, skipped=7)
exit=1
$ grep -E '^(FAIL|ERROR): ' <capture> | grep -v test_oauth_token_cache
(no output)
```

So the 21 failures and 2 errors are exactly the RED of §3 — every `FAIL:`/`ERROR:` header
in the capture names `tests.test_oauth_token_cache` — and no other module changed
outcome by the new file's presence (the 7 skips are the loud, pre-existing ones:
`test_v020_boundaries`' fail-closed environment guard and the tool-prerequisite skips).
Beside the two neighbours that also patch `urlopen` the count is the same
(`python3 -m unittest tests.test_oauth_token_cache tests.test_summary_pill
tests.test_update_check_schedule` → `Ran 62 tests`, `FAILED (failures=21, errors=2)`),
and a fresh `import claude_pet` afterwards shows `claude_pet.time is time` and the
original dict keys, i.e. the `time`/`sys.platform`/dict patches do not leak.

This is the pre-fix baseline. The GREEN run after the Developer's change goes in a
separate section of this record, written by the Verifier from a fresh full-suite run —
with the expected `test_upload_artifact_gate` refusal (§5) noted rather than re-pinned.

## 7. Appendix — verbatim output of the RED run

```
2026-09-13T01:50:32Z
$ python3 -m unittest tests.test_oauth_token_cache -v
test_401_forced_walk_reaches_native_once_and_respects_declined (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_401_forced_walk_reaches_native_once_and_respects_declined)
Pin of the UNCHANGED v0.16 contract (GREEN before and after; it gates ... ok
test_401_with_no_replacement_stops_serving_the_dead_token (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_401_with_no_replacement_stops_serving_the_dead_token)
401 on the request, forced walk finds nothing (CLI → None, native → ... FAIL
test_credentials_helpers_resolve_under_home_and_sign_the_file (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_credentials_helpers_resolve_under_home_and_sign_the_file)
`_credentials_path()` resolves `~/.claude/.credentials.json` under the ... ERROR
test_failed_fetch_retries_within_fail_retry_sec_except_429 (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_failed_fetch_retries_within_fail_retry_sec_except_429)
`fetch_exact_usage()` caches a failed fetch for `OAUTH_FAIL_RETRY_SEC` ... ERROR
test_fetch_failure_debug_lines_carry_codes_not_token_bytes (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_fetch_failure_debug_lines_carry_codes_not_token_bytes)
With `CLAUDE_PET_DEBUG=1`, a 500 and a URLError each leave a fetch ... FAIL
test_file_token_rotation_is_picked_up_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_file_token_rotation_is_picked_up_without_restart)
A rotated `~/.claude/.credentials.json` is served by the next ... 
  test_file_token_rotation_is_picked_up_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_file_token_rotation_is_picked_up_without_restart) (platform='darwin')
A rotated `~/.claude/.credentials.json` is served by the next ... FAIL
  test_file_token_rotation_is_picked_up_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_file_token_rotation_is_picked_up_without_restart) (platform='win32')
A rotated `~/.claude/.credentials.json` is served by the next ... FAIL
test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only)
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... 
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
  test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... FAIL
test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything)
Each non-auth failure sets `_oauth_token_cache["suspect"]` and records its ... FAIL
test_vanished_credentials_file_drops_the_cached_token (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_vanished_credentials_file_drops_the_cached_token)
Design: "if `src == "file"` and the signature changed **or the file ... FAIL

======================================================================
ERROR: test_credentials_helpers_resolve_under_home_and_sign_the_file (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_credentials_helpers_resolve_under_home_and_sign_the_file)
`_credentials_path()` resolves `~/.claude/.credentials.json` under the
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 323, in test_credentials_helpers_resolve_under_home_and_sign_the_file
    self.assertEqual(os.path.realpath(claude_pet._credentials_path()),
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'claude_pet' has no attribute '_credentials_path'

======================================================================
ERROR: test_failed_fetch_retries_within_fail_retry_sec_except_429 (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_failed_fetch_retries_within_fail_retry_sec_except_429)
`fetch_exact_usage()` caches a failed fetch for `OAUTH_FAIL_RETRY_SEC`
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 582, in test_failed_fetch_retries_within_fail_retry_sec_except_429
    self.assertEqual(claude_pet.OAUTH_FAIL_RETRY_SEC, 60)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'claude_pet' has no attribute 'OAUTH_FAIL_RETRY_SEC'

======================================================================
FAIL: test_401_with_no_replacement_stops_serving_the_dead_token (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_401_with_no_replacement_stops_serving_the_dead_token)
401 on the request, forced walk finds nothing (CLI → None, native →
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 530, in test_401_with_no_replacement_stops_serving_the_dead_token
    self.assertEqual(self.cached_name(), "None",
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "dead token retained in the cache after a 401 with no replacement")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'None'
- tokA
+ None
 : dead token retained in the cache after a 401 with no replacement

======================================================================
FAIL: test_fetch_failure_debug_lines_carry_codes_not_token_bytes (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_fetch_failure_debug_lines_carry_codes_not_token_bytes)
With `CLAUDE_PET_DEBUG=1`, a 500 and a URLError each leave a fetch
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 697, in test_fetch_failure_debug_lines_carry_codes_not_token_bytes
    self.assertTrue(any("oauth" in m.lower() and "500" in m for m in msgs),
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    "no fetch diagnostic carrying the HTTP status code")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : no fetch diagnostic carrying the HTTP status code

======================================================================
FAIL: test_file_token_rotation_is_picked_up_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_file_token_rotation_is_picked_up_without_restart) (platform='darwin')
A rotated `~/.claude/.credentials.json` is served by the next
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 384, in test_file_token_rotation_is_picked_up_without_restart
    self.assertEqual(self.read_name(), "tokB",
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "row 1: same-size in-place rewrite 0.5 ms later not picked up")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : row 1: same-size in-place rewrite 0.5 ms later not picked up

======================================================================
FAIL: test_file_token_rotation_is_picked_up_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_file_token_rotation_is_picked_up_without_restart) (platform='win32')
A rotated `~/.claude/.credentials.json` is served by the next
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 384, in test_file_token_rotation_is_picked_up_without_restart
    self.assertEqual(self.read_name(), "tokB",
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "row 1: same-size in-place rewrite 0.5 ms later not picked up")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : row 1: same-size in-place rewrite 0.5 ms later not picked up

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a URLError carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a URLError carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='URLError', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 499, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertGreater(self.cli.calls, cli_before,
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       "cli-sourced token was not re-validated through the security CLI")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a HTTPError 500 carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a HTTPError 500 carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 500', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 499, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertGreater(self.cli.calls, cli_before,
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       "cli-sourced token was not re-validated through the security CLI")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a HTTPError 429 carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a HTTPError 429 carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='HTTPError 429', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 499, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertGreater(self.cli.calls, cli_before,
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       "cli-sourced token was not re-validated through the security CLI")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a socket timeout carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a socket timeout carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='socket timeout', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 499, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertGreater(self.cli.calls, cli_before,
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       "cli-sourced token was not re-validated through the security CLI")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='cli')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a invalid JSON carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='file')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 495, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertBearer(expected, "request after a %s carried the wrong token" % label)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 298, in assertBearer
    self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "%s (request %d)" % (msg, self.http.requests))
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'tokB'
- tokA
?    ^
+ tokB
?    ^
 : request after a invalid JSON carried the wrong token (request 2)

======================================================================
FAIL: test_non_auth_failure_revalidates_through_prompt_free_sources_only (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_non_auth_failure_revalidates_through_prompt_free_sources_only) (failure='invalid JSON', replacement='none')
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 499, in test_non_auth_failure_revalidates_through_prompt_free_sources_only
    self.assertGreater(self.cli.calls, cli_before,
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       "cli-sourced token was not re-validated through the security CLI")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1 not greater than 1 : cli-sourced token was not re-validated through the security CLI

======================================================================
FAIL: test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything)
Each non-auth failure sets `_oauth_token_cache["suspect"]` and records its
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 639, in test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything
    self.assertIn("last_error", claude_pet.OAUTH_STATUS)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'last_error' not found in {'auth_error': False}

======================================================================
FAIL: test_vanished_credentials_file_drops_the_cached_token (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_vanished_credentials_file_drops_the_cached_token)
Design: "if `src == "file"` and the signature changed **or the file
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 421, in test_vanished_credentials_file_drops_the_cached_token
    self.assertEqual(self.read_name(), "None", "cached token served after the file vanished")
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'None'
- tokA
+ None
 : cached token served after the file vanished

----------------------------------------------------------------------
Ran 9 tests in 0.011s

FAILED (failures=21, errors=2)
exit=1
```

---

# GREEN (round 1)

Verifier: verifier-a, same role as above. Section written 2026-09-13T02:26–02:28Z (appended 02:27:48Z). This role
still commits nothing and edited no production file in this round; the only writes were this
section and two scratchpad files (`probe_track_a.py`, and `claude_pet_head.py` — a `git show
HEAD:claude_pet.py` copy used by the probe, hash `6f95bc8b…`). cwd `/Users/yeongyu/claude-pet`
throughout; times UTC; fenced output verbatim.

## 8. What is under verification now (read 02:14–02:20Z)

The brief named HEAD `13710db`; the checkout is one docs-only commit past it, and the
pre-fix production bytes are the same at both:

```
$ git rev-parse HEAD
087ecf5b3d0a1dadf9f5df15d7646da399136c88
$ git log --oneline -2
087ecf5 docs: no "beta" label for Windows, platform spec table, built-in-cat preview, roadmap wording
13710db docs: site and README refresh after v0.24 — Windows beta, SmartScreen guidance, roadmap
$ git show --stat --format= HEAD | tail -1
 10 files changed, 623 insertions(+), 79 deletions(-)      # README*, docs/, preview.png, one docs-design file — no claude_pet.py
$ git show 13710db:claude_pet.py | shasum -a 256 ; git show HEAD:claude_pet.py | shasum -a 256
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  -
```

So the RED of §3 (taken at `6f95bc8b…`) is a run against exactly the bytes HEAD carries; the
docs-only edits §1 listed as uncommitted were committed by someone else (087ecf5), not by this
role.

Tracked-tree status at 02:14Z (untracked paths omitted; none of them were touched):

```
 M CLAUDE.md
 M claude_pet.py
```

Hashes for the §2 conditions:

```
$ shasum -a 256 claude_pet.py tests/test_oauth_token_cache.py docs-design/followups-v025-plan-20260913.md
380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8  claude_pet.py
bfb348c9c2f9b7ddd2c0962af413b8b8b25b587ee3efd6092c28d92642e3e14d  tests/test_oauth_token_cache.py
4b3ad55606dfa0f33e0d7f9fd35c44bc51a976432c39310848f86a982e506495  docs-design/followups-v025-plan-20260913.md
```

- **Condition A** — the gating file's hash is byte-identical to the one recorded at RED
  (§2, 01:58Z), so no assertion, expected value or fixture literal moved. The design doc is
  unchanged too, so the tests still hold the code to the design as written.
- **Condition B** — the set of files this role edited (`tests/test_oauth_token_cache.py`, this
  record) and the production set of the change (`claude_pet.py`) are disjoint.
- The production change is the whole of `git diff claude_pet.py` (read in full) and is the
  same text the Developer's `scratchpad/patch_track_a.py` applies as five anchored
  replacements; `CLAUDE.md` gained one 22-line paragraph under "exact vs estimate".

## 9. Gating file — GREEN

```
$ python3 -m unittest tests.test_oauth_token_cache -v      # 2026-09-13T02:16:29Z, claude_pet.py 380a651e…
test_401_forced_walk_reaches_native_once_and_respects_declined (...)
Pin of the UNCHANGED v0.16 contract (GREEN before and after; it gates ... ok
test_401_with_no_replacement_stops_serving_the_dead_token (...)
401 on the request, forced walk finds nothing (CLI → None, native → ... ok
test_credentials_helpers_resolve_under_home_and_sign_the_file (...)
`_credentials_path()` resolves `~/.claude/.credentials.json` under the ... ok
test_failed_fetch_retries_within_fail_retry_sec_except_429 (...)
`fetch_exact_usage()` caches a failed fetch for `OAUTH_FAIL_RETRY_SEC` ... ok
test_fetch_failure_debug_lines_carry_codes_not_token_bytes (...)
With `CLAUDE_PET_DEBUG=1`, a 500 and a URLError each leave a fetch ... ok
test_file_token_rotation_is_picked_up_without_restart (...)
A rotated `~/.claude/.credentials.json` is served by the next ... ok
test_non_auth_failure_revalidates_through_prompt_free_sources_only (...)
After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates ... ok
test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything (...)
Each non-auth failure sets `_oauth_token_cache["suspect"]` and records its ... ok
test_vanished_credentials_file_drops_the_cached_token (...)
Design: "if `src == "file"` and the signature changed **or the file ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.013s

OK
```

(`(...)` abbreviates the repeated `tests.test_oauth_token_cache.OAuthTokenCacheCase.<name>`
qualifier; nothing else is elided. Capture:
`scratchpad/verifier_gating_green.txt`.) Every `subTest` row passes — unittest prints a
subTest only when it fails, so the absence of indented rows is the pass. Against §3 this is
21 failures + 2 errors → 0, with the gating file unchanged by hash.

## 10. Full suite

```
$ python3 -m unittest discover -s tests -v      # started 2026-09-13T02:16:31Z, finished 02:20:55Z
Ran 556 tests in 264.103s

FAILED (failures=49, errors=8, skipped=7)
exit=1
```

(Capture: `scratchpad/verifier_fullsuite_green.txt`, 1925 lines; the `[update] rejected:`
lines that follow the summary in the raw capture are the updater tests' stderr arriving
after unittest's own stream and are not test outcomes.)

**Every one of the 57 non-passing outcomes is the same event: `claude_pet.py`'s SHA256
moved from `6f95bc8b…` to `380a651e…`.** Classification, from
`grep -E '^(FAIL|ERROR): '` and the distinct assertion lines:

| module | count | where it refuses | assertion line (verbatim, hashes abbreviated) |
| --- | --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | `setUp` → `assert_reviewed_file(self, APP_SOURCE, REVIEWED_APP_SOURCE_SHA256)` | `AssertionError: '380a651e…' != '6f95bc8b…' … claude_pet.py changed after this executable harness was reviewed; refusing to run it until a verifier reviews and repins the new bytes` |
| `test_manual_update_transaction` | 8 ERROR | `setUpClass`, one per class | `AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b…, found 380a651e…` |
| `test_v024_release_contract` | 1 FAIL | `test_v024_version_and_final_source_pins_propagate` | lists the two `REVIEWED_APP_SOURCE_SHA256` pins above against `final claude_pet.py is 380a651e…` |

`grep -c` of the distinct lines: 48 + 8 + 1 = 57 = 49 failures + 8 errors. No `FAIL:`/`ERROR:`
header names any other module; **`tests.test_oauth_token_cache` appears in none.**

**Correction to §5.** §5 named `test_upload_artifact_gate` as the module that pins the hash.
Three places pin it — the two `REVIEWED_APP_SOURCE_SHA256` constants
(`test_upload_artifact_gate.py`, `test_manual_update_transaction.py`) and the v0.24 contract
test that checks both against the final file. All three are the same expected fallout, and
none is re-pinned by this role; the re-pin is a release-gate step after review.

**Test count 574 → 556.** The 8 `setUpClass` errors stop their classes' methods from
running, and those classes hold exactly 18 tests
(`unittest.defaultTestLoader.loadTestsFromName("tests.test_manual_update_transaction")`,
per class: 3 + 2 + 2 + 2 + 2 + 3 + 3 + 1 = 18). 574 − 18 = 556, so no test outside those
classes appeared or disappeared.

**Skips: the same 7 as §6** — `test_updater`'s two installed-app-preflight and two
real-stapler skips (`CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`) and `test_v020_boundaries`' three
(`CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`), each printed loudly with its reason.

**The Developer's own capture** (`scratchpad/fullsuite.txt`, run ending 02:13:55Z) reads
`Ran 556 tests in 266.232s` / `FAILED (failures=49, errors=8, skipped=7)` with the same
48 / 8 / 1 distribution across the same three modules. Two independent runs of the same
bytes agree.

**Privacy of the captures:** `grep -c synthetic-access-token` → 0 in both full-suite
captures and the gating capture; no path under the temp `HOME` is printed by the gating
tests.

## 11. Conformance to the design, read from the diff

Read directly from `git diff claude_pet.py` — deterministic, source-cited, not an
observation (AGENTS.md §5). Each clause of the Track A design, the code that implements it,
and the test that pins it:

| design clause | code (locate by symbol) | pinned by |
| --- | --- | --- |
| cache gains `src`, `file_sig`, `suspect` | `_oauth_token_cache = {…, "src": None, "file_sig": None, "suspect": False}`; `_remember_oauth_token` / `_forget_oauth_token` are the only writers | item 5 (`suspect`), item 1 (via behaviour) |
| `_credentials_path()`, `_credentials_sig()` = `(st_mtime_ns, st_size, st_ino)` | `_credentials_path`, `_stat_sig`, `_credentials_sig`; `_read_credentials_file` stats **before** opening (docstring states why) | item 0 |
| `src == "file"` and signature changed or file vanished → drop and read afresh | first block of `_read_oauth_token`: `if not force and c["tok"] and c["src"] == "file": … if sig != c["file_sig"]: _forget_oauth_token(c)` | items 1, 1′ |
| `suspect` → re-validate through **prompt-free** sources only; native never entered | `_revalidate_oauth_token`: calls `_read_credentials_file()` and, only when `old_src == "cli"` on darwin, `_token_from_cli()`; **no reference to `_keychain_token_native_bounded` in its body** | item 2 asserts `native.calls == 0` in all 20 subTests, and CLI consulted only for a cli-sourced token |
| replacement replaces, none keeps, `suspect` clears either way | same function: `c["suspect"] = False` before the branch; `_remember_oauth_token` on a hit, `return c["tok"]` otherwise | item 2 (`none` and `file-src-unchanged` rows) |
| success → `suspect`/`auth_error`/`last_error` cleared | end of `_fetch_oauth_usage` | item 5 |
| 401/403 with no replacement → clear `tok`, `auth_error = True` | `_read_oauth_token(force=True)` forgets under the lock (both the `st is None` and the final `else` branch); `_fetch_oauth_usage` forgets only if the cache still holds the rejected token (lock-busy case) | item 3 |
| the 401 forced walk still reaches native once unless `declined` (v0.16 contract) | unchanged walk order inside the lock | item 3′ (pin) |
| every other failure → `suspect = True`, `last_error ∈ {http:<code>, net, parse}` | the three `except`/parse branches of `_fetch_oauth_usage` | item 5 (all five classes) |
| `fetch_exact_usage`: failed fetch cached 60 s, **429 keeps 180 s** | `if err and err != "http:429": _oauth_cache["t"] = now - (OAUTH_CACHE_SEC - OAUTH_FAIL_RETRY_SEC)`; `OAUTH_FAIL_RETRY_SEC = 60` beside `OAUTH_CACHE_SEC` | item 4 (500, URLError → 1/2/3; 429, success → 1/1/2) |
| nothing new rendered; memo key unchanged | the diff touches only the OAuth region (constants, helpers, `_read_oauth_token`, `_fetch_oauth_usage`, `fetch_exact_usage`); `test_v024_release_contract`'s memo-key AST test passed in the full run | — |
| `_dbg` carries codes and booleans only | the eight added `_dbg` calls: `("read_oauth: file sig changed; vanished?", sig is None)`, `("read_oauth: final tok?", bool(tok), "src", …, "declined?", …)`, `("read_oauth: revalidate src", src, "changed?", tok != c["tok"])`, `("read_oauth: revalidate found nothing; keep src", old_src)`, `("oauth fetch: http", code, "attempt", attempt)`, `("oauth fetch: net", type(e).__name__, "attempt", attempt)`, `("oauth fetch: parse", type(e).__name__)`, `("oauth fetch: ok rows", len(rows) if rows else 0)` — no token, no header, no response body, no path | item 6 |

The two relaxations the brief asked me to look for are therefore **absent**: automatic
re-validation cannot reach the native reader (there is no call to it in
`_revalidate_oauth_token`, and the first-block signature path forgets the token but does not
itself read anything), and 429 keeps the full `OAUTH_CACHE_SEC` (the guard is explicit and
the 429 row of item 4 passes: 1 request at +61 s, 2 at +181 s).

`_token_from_file` is kept by name and now returns `_read_credentials_file()[0]`;
`_read_credentials_file` has exactly three callers, all inside `_read_oauth_token` /
`_revalidate_oauth_token` (`grep -n '_read_credentials_file('`).

The CLAUDE.md paragraph was checked sentence by sentence against the same diff; each claim
maps to a row above. One reading note: "re-checked against that signature on every read"
means every non-force read — the force path skips the check and re-reads the file at the
end of the walk instead, which is the same outcome.

## 12. Two behaviours the tests do not pin, measured (scratch probe, not a test)

`scratchpad/probe_track_a.py`, run 02:24:55Z against the working tree and against the HEAD
copy (`6f95bc8b…`) with one fixture: `HOME` → fresh temp dir, `_token_from_cli` /
`_keychain_token_native_bounded` / `_keychain_token_native` / `urlopen` stubbed, `time`
shimmed, `sys.platform` = `darwin`; counts only, no token bytes in the output.

**Probe A — darwin, file-sourced token, credentials file removed, `declined` False, native
stub answers item-not-found.** Next `_read_oauth_token()`:

| tree | returns | CLI calls | native calls |
| --- | --- | --- | --- |
| working tree (`380a651e…`) | None | 1 | 1 |
| HEAD copy (`6f95bc8b…`) | the dead token | 0 | 0 |

This is the design's "drop the cached token and read afresh": the fresh read is the ordinary
walk, which on darwin ends at the native reader (respecting `declined`; in this fixture the
item is absent so nothing would prompt). The gating fixture for this clause (item 1′) runs on
`win32`, where the file is the only source, so it does not see this. Not a relaxation — the
design says "read afresh" and the walk is unchanged — but it is a case where the file path
now leads to the Keychain sooner than before (before: only after the server's 401).

**Probe B — persistent 401: CLI blocked (None), native answers the same dead token every
time (an "always allow" machine), server answers 401 to every request. `fetch_exact_usage()`
called every 30 s for 600 s of shimmed clock (21 calls).**

| tree | native calls | CLI calls | requests | `auth_error` | `declined` |
| --- | --- | --- | --- | --- | --- |
| working tree | 12 | 12 | 22 | True | False |
| HEAD copy | 5 | 5 | 8 | True | False |

Reading: 1 initial walk + one forced walk per fetch cycle; cycles every 60 s on the working
tree (`http:401` is a non-429 failure, so it gets `OAUTH_FAIL_RETRY_SEC`) against every
180 s on HEAD. **This is the design's letter** ("a failed fetch is cached for 60 s … except
`http:429`") and the gating fixture (item 4) does not include a 401 row, so the
implementation is conformant. It is flagged because the 401 forced walk is the one automatic
path that can prompt (survey history note), and it now runs at the shorter cadence in the
state "token dead in the Keychain, CLI blocked, user has not re-run Claude Code". Whether
401/403 should join 429 in keeping the full cache is a **design decision for the
Coordinator**, not a Developer fix; if taken it needs its own red fixture.

## 13. Notes for the Reviewer (none is a failure against the design)

1. Probe B above — 401/403 in the short-retry set.
2. Probe A above, and its torn-read variant: if Claude Code rewrites the credentials file in
   place (survey open question 2, still open), a read that lands between truncate and write
   parses no token, the signature has changed, the cache is forgotten, the walk runs, and the
   file is not consulted again for `OAUTH_TOKEN_RETRY` (120 s). Bounded, no new prompt path
   relative to a cold start, and a matter of how the producer writes the file, which nothing
   here can settle.
3. `fetch_exact_usage()` chooses the 60 s / 180 s cache from `OAUTH_STATUS["last_error"]`,
   which `_fetch_oauth_usage()` leaves untouched on its no-token early return. A cycle with no
   token therefore inherits the class of the previous failure (60 s after a prior 5xx/401,
   180 s after a prior 429 or a success). Harmless — with no token no request is made and the
   token path has its own `OAUTH_TOKEN_RETRY` cooldown — but "a failed fetch" in the
   docstring does not describe that cycle.
4. `run_native_smoke()` in `tests/test_companion_motion.py` still patches `_token_from_file`
   by name; `_read_oauth_token` no longer calls it (`_read_credentials_file` is the
   primitive). The smoke also patches `_read_oauth_token` and `fetch_exact_usage` wholesale
   and `_read_credentials_file` has no caller outside those two functions, so the smoke's
   guarantee holds; the `_token_from_file` entry is now vestigial rather than load-bearing.
5. The lock-busy early return in `_read_oauth_token` now returns `None` under `force`
   (previously the just-rejected token — a survey finding); `_fetch_oauth_usage` then forgets
   the token only when the cache still holds the one the server rejected, so a concurrent
   reader's fresh result is not discarded.

## 14. Verdict

**GREEN (round 1).** The gating file went from 21 failures + 2 errors at `6f95bc8b…` (§3,
01:50:32Z) to 9/9 with every `subTest` passing at `380a651e…` (§9, 02:16:29Z) with the
gating file byte-identical (`bfb348c9…`) and the design byte-identical (`4b3ad556…`). The
full suite's only non-green outcomes are the 57 refusals of the three `claude_pet.py` hash
pins (§10), expected since §5 and left for the release-time re-pin. Neither relaxation the
brief named is present (§11). §12–13 are observations and design questions for the Reviewer
and Coordinator, recorded with their numbers so they can be decided rather than rediscovered.

# ADDENDUM — the 2026-09-13 keychain-rotation incident (two more gating tests)

Verifier: verifier-a, same role. Section opened 2026-09-13T02:45Z. This role still commits
nothing and ran no git write command; the only files written were
`tests/test_oauth_token_cache.py` (two methods and helpers appended, one paragraph appended to
the module docstring; no existing assertion, expected value or fixture literal was touched —
the diff of the file against its RED-time bytes is purely additive below the last existing
method plus that docstring paragraph), this record, and scratch files under the session
scratchpad (`claude_pet_head/claude_pet.py`, `probe_addendum.py`, `probe_addendum_q.py`, the
captures named below). No production file was opened for writing; `claude_pet.py` is
`380a651e…` before and after (§A.1). No untracked path other than the two deliverables was
touched. cwd `/Users/yeongyu/claude-pet`; times UTC; fenced output verbatim; every capture was
grepped for the synthetic token prefix (0 hits, §A.4).

**The incident this pins** (brief, user's Mac, local times): v0.24 installed app started 00:56;
no `~/.claude/.credentials.json` on that Mac, so the token comes from the `security` CLI;
Claude Code rotated the "Claude Code-credentials" keychain item at 10:09; the app stayed on the
amber estimate line with the `⚠` of `OAUTH_STATUS["auth_error"]` for 76+ minutes, while a
fresh process obtained exact mode immediately through the same CLI. Two mechanisms are
plausible for the first failed cycle, and the brief asks for both to be covered:

- **R — rotation lag.** At the first 401 the forced walk returned the *same* old token (the
  keychain item not yet rewritten); the retry 401'd again; later the keychain held the new
  token.
- **P — pending native.** The CLI transiently returned nothing during the rewrite; the forced
  walk entered `_keychain_token_native_bounded`, which reported pending (`st is None`) and set
  the `OAUTH_TOKEN_RETRY` cooldown; later cycles must still consult the CLI and recover.

## A.1 What is under verification (read 02:45Z)

```
$ git rev-parse HEAD
087ecf5b3d0a1dadf9f5df15d7646da399136c88
$ git show HEAD:claude_pet.py > <scratch>/claude_pet_head/claude_pet.py      # 02:45:14Z
$ shasum -a 256 <scratch>/claude_pet_head/claude_pet.py claude_pet.py tests/test_oauth_token_cache.py
6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4  <scratch>/claude_pet_head/claude_pet.py
380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8  claude_pet.py
bfb348c9c2f9b7ddd2c0962af413b8b8b25b587ee3efd6092c28d92642e3e14d  tests/test_oauth_token_cache.py   # before this addendum
$ git status --porcelain | grep -v '^??'
 M CLAUDE.md
 M claude_pet.py
```

So the committed module is the pre-fix bytes (`6f95bc8b…`, the RED of §3) and the working
tree carries the Track A change (`380a651e…`, the GREEN of §9); the fix is already in the tree,
so §3's remedy 1 applies — RED is observed against a scratch copy of `HEAD:claude_pet.py`,
never by touching the tree.

Read from source before writing the fixtures (deterministic, not observations): on the tree,
`fetch_exact_usage()` re-bases `_oauth_cache["t"]` after any failure whose `last_error` is not
`http:429`, so a 401 is retried after `OAUTH_FAIL_RETRY_SEC` = 60 s; `_read_oauth_token(force=True)`
forgets the cached token in both no-token exits (pending and not-found) and in `_fetch_oauth_usage`
when the lock was busy; the ordinary walk consults the CLI before the native reader, and
`_remember_oauth_token` zeroes `next_retry` whenever a token is cached. On HEAD, every failure is
cached 180 s, the pending exit keeps the cached token, and the lock-busy exit returns it.

## A.2 The two tests, and why both drive `fetch_exact_usage()`

Appended to `OAuthTokenCacheCase` under "7. the 2026-09-13 keychain-rotation incident", with
two helpers: `server_accepting(token)` — a zero-arg outcome for the existing `_FakeHTTP.default`
that answers 200 when the header the fake has *already recorded* carries `token` and
`HTTPError 401` otherwise (the fake appends the header before it consults the outcome, so no
header-aware mode was added to the fake) — and `sent_names(start)`, the fixture names of the
bearer tokens sent, never the bytes. Same isolation as the first nine methods (HOME redirected,
CLI/native/raw-native stubbed, `urlopen` faked, `time` shimmed, `sys.platform` = `darwin`).

| method | cycle 1 (T) | poll T+30 | cycle 2 | asserts |
| --- | --- | --- | --- | --- |
| `test_rotation_lag_recovers_on_the_next_cycle_without_restart` | cached cli-sourced tokA; server accepts only tokB; CLI still returns tokA | nothing sent | T+61 (literal; = `OAUTH_FAIL_RETRY_SEC`+1), CLI returns tokB | cycle 1: requests `[tokA, tokA]`, CLI consulted, native 0, `auth_error` True, rows None; T+30: request count unchanged; T+61: rows, last bearer tokB, `auth_error` False, cache tokB, CLI consulted, native 0 |
| `test_pending_native_does_not_block_cli_recovery` | cached tokA; CLI → None; native → `(None, None)`; server accepts only tokB | nothing sent | T+`OAUTH_TOKEN_RETRY`+1 = T+121, CLI returns tokB, native *still* pending | cycle 1: requests `[tokA]`, CLI consulted, native exactly 1, `auth_error` True, cache `None` (own `subTest` so the run continues); T+30: unchanged; T+121: rows, new requests exactly `[tokB]`, `auth_error` False, cache tokB, CLI consulted, native still 1, `declined` False |

Nothing is reset between cycles in either method — `reset_state()` is called by `setUp` only —
which is the "no restart" the brief asks for.

**Why `fetch_exact_usage()` and not `_fetch_oauth_usage()` for cycle 1.** The brief phrases
cycle 1 as "`_fetch_oauth_usage()` → None". Computed before writing (and confirmed by the probe
in §A.5): if cycle 1 bypasses `fetch_exact_usage()`, `_oauth_cache["t"]` stays 0 and cycle 2
fetches unconditionally on both modules — and on HEAD the forced walk of that cycle reaches the
CLI, finds tokB and recovers, so **both tests would be GREEN on the pre-fix module**, i.e.
non-discriminating (§3). The failure cache is where the two modules differ for these
mechanisms, and it lives in `fetch_exact_usage()`, the entry the refresh worker calls every
30 s; cycle 1's "`_fetch_oauth_usage()` → None" is the inner result of that call and is still
what the assertions check (rows None, `auth_error` True, the requests sent).

**Truth tables** are in the docstrings. The rivals the brief names and where each is separated:

| rival | separated by |
| --- | --- |
| keep the dead token and skip the forced walk | test 1: cycle 1 sends one request, CLI not consulted, T+61 sends tokA; test 2: native 0 at cycle 1, T+121 sends tokA |
| forced walk only re-reads the file | test 1: cycle 1 sends one request, CLI not consulted, T+61 nothing (cooldown, no token); test 2: CLI not consulted and native 0 at cycle 1 (the v0.16 contract, item 3′) — it *does* recover at T+121 through the ordinary walk, so the recovery rows alone would not catch it |
| pending native blocks every later walk ("native gate") | test 2: T+121 nothing sent, native 2 |
| cooldown applies to force mode | **not separated, and not separable through the public entry points**: `_remember_oauth_token` zeroes `next_retry` whenever a token is cached, so a forced walk under a live cooldown is unreachable — the two implementations agree on every reachable state. Stated in both docstrings so nobody adds a fixture for it. |
| today (pre-fix: 180 s failure cache, dead token kept at pending) | test 1: T+61 rows None; test 2: cache row `tokA`, T+121 rows None |
| added: native-first walk (pre-v0.16 order) | test 1: native 1 at cycle 1 |
| added: keep the token at pending (the fix minus `_forget_oauth_token` in that branch) | test 2: cache row, and T+121 sends `[tokA, tokB]` |
| added: pending recorded as `declined` | test 2: `declined` True at the end |

The T+61 in test 1 is a literal, not `OAUTH_FAIL_RETRY_SEC + 1`, so that a run against a module
without the constant (HEAD) fails on behaviour rather than with `AttributeError`; item 4
already pins the constant at 60. (The Reviewer's N2 — whether 401/403 should join 429 in
keeping 180 s — would, if adopted, turn this row RED; at T+181 the row no longer separates
the tree from HEAD, see §A.5. That is the Coordinator's call and it is flagged, not decided,
here.)

Hashes after the edit (02:49:59Z):

```
$ shasum -a 256 claude_pet.py tests/test_oauth_token_cache.py docs-design/followups-v025-plan-20260913.md
380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8  claude_pet.py
1adccf00f5d6aa3342851d88b44290cc0069b5a83c1eba7dd722b47c7aa7d3f5  tests/test_oauth_token_cache.py
4b3ad55606dfa0f33e0d7f9fd35c44bc51a976432c39310848f86a982e506495  docs-design/followups-v025-plan-20260913.md
$ wc -l tests/test_oauth_token_cache.py
     894 tests/test_oauth_token_cache.py          # was 704
```

## A.3 ADDENDUM RED — against the committed module

`python3 -m unittest` puts the cwd first on `sys.path`, ahead of `PYTHONPATH`, so the HEAD copy
cannot win by environment alone; the run inserts the scratch directory ahead of the repo root
explicitly and prints `claude_pet.__file__` and the SHA256 of the module it imported.
(In the capture the two `print` lines appear *after* unittest's output: stdout was block-buffered
under the pipe while unittest wrote to stderr — an ordering artifact, the import happened first.)

```
2026-09-13T02:49:51Z
$ python3 -c "
import sys, hashlib
sys.path.insert(0, '/Users/yeongyu/claude-pet')
sys.path.insert(0, '<scratch>/claude_pet_head')
import claude_pet
print('claude_pet.__file__ =', claude_pet.__file__)
print('sha256 =', hashlib.sha256(open(claude_pet.__file__, 'rb').read()).hexdigest())
import unittest
unittest.main(module=None, argv=['unittest', '-v', '-k', 'rotation_lag', '-k', 'pending_native', 'tests.test_oauth_token_cache'])
"
test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery)
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced ... 
  test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery) (step='cache after the pending forced walk')
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced ... FAIL
test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery)
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced ... FAIL
test_rotation_lag_recovers_on_the_next_cycle_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_rotation_lag_recovers_on_the_next_cycle_without_restart)
Mechanism R — rotation lag. Cycle 1 (T): the cached cli-sourced tokA is ... FAIL

======================================================================
FAIL: test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery) (step='cache after the pending forced walk')
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 870, in test_pending_native_does_not_block_cli_recovery
    self.assertEqual(self.cached_name(), "None",
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     "the rejected token survived a forced walk that found no replacement")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'tokA' != 'None'
- tokA
+ None
 : the rejected token survived a forced walk that found no replacement

======================================================================
FAIL: test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery)
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 882, in test_pending_native_does_not_block_cli_recovery
    self.assertTrue(rows, "pending native: the cycle after the cooldown did not recover exact mode")
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: None is not true : pending native: the cycle after the cooldown did not recover exact mode

======================================================================
FAIL: test_rotation_lag_recovers_on_the_next_cycle_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_rotation_lag_recovers_on_the_next_cycle_without_restart)
Mechanism R — rotation lag. Cycle 1 (T): the cached cli-sourced tokA is
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/yeongyu/claude-pet/tests/test_oauth_token_cache.py", line 805, in test_rotation_lag_recovers_on_the_next_cycle_without_restart
    self.assertTrue(rows, "rotation lag: the next cycle did not recover exact mode")
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: None is not true : rotation lag: the next cycle did not recover exact mode

----------------------------------------------------------------------
Ran 2 tests in 0.002s

FAILED (failures=3)
claude_pet.__file__ = <scratch>/claude_pet_head/claude_pet.py
sha256 = 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4
exit=1
```

(`<scratch>` abbreviates
`/private/tmp/claude-501/-Users-yeongyu-claude-pet/55c3dee4-727f-4a94-b960-66540b129014/scratchpad`;
nothing else is elided. Capture: `scratchpad/addendum_red.txt`.) Two methods, three failures —
the `subTest` row counts separately. Each message is the one its docstring's "today" column
predicts: the pending forced walk left `tokA` cached; the T+121 poll in test 2 and the T+61 poll
in test 1 were served from the 180 s failure cache and returned no rows. Every assertion before
those (two requests both carrying tokA in test 1; one request, CLI consulted, native exactly
once in test 2; nothing sent at T+30 in both) passed on HEAD, as the "today" columns say.

## A.4 ADDENDUM GREEN — against the working tree

```
2026-09-13T02:49:54Z
$ python3 -c "import claude_pet, hashlib; print('claude_pet.__file__ =', claude_pet.__file__); print('sha256 =', hashlib.sha256(open(claude_pet.__file__,'rb').read()).hexdigest())"
claude_pet.__file__ = /Users/yeongyu/claude-pet/claude_pet.py
sha256 = 380a651e88d0f2a75ef67cadab93b827719598835541d63f2fda260d3ea2fbc8
$ python3 -m unittest tests.test_oauth_token_cache -k rotation_lag -k pending_native -v
test_pending_native_does_not_block_cli_recovery (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_pending_native_does_not_block_cli_recovery)
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced ... ok
test_rotation_lag_recovers_on_the_next_cycle_without_restart (tests.test_oauth_token_cache.OAuthTokenCacheCase.test_rotation_lag_recovers_on_the_next_cycle_without_restart)
Mechanism R — rotation lag. Cycle 1 (T): the cached cli-sourced tokA is ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.002s

OK
exit=0
```

The whole module, same tree:

```
2026-09-13T02:49:56Z
$ python3 -m unittest tests.test_oauth_token_cache -v
Ran 11 tests in 0.011s

OK
exit=0
```

(Capture `scratchpad/addendum_module_green.txt`: all nine earlier methods `ok`, unchanged, plus
the two new ones.) Beside the two neighbours that also patch `urlopen`, and a leak check in one
process (02:51:25Z):

```
$ python3 -m unittest tests.test_oauth_token_cache tests.test_summary_pill tests.test_update_check_schedule
Ran 64 tests in 0.483s

OK
module run: 11 tests, failures 0 errors 0
claude_pet.time is time: True | sys.platform: darwin
cache keys: ['declined', 'file_sig', 'next_retry', 'src', 'suspect', 'tok'] | status keys: ['auth_error', 'last_error']
cache cold: True | urlopen restored: urllib.request
```

Privacy of the captures (`grep -c synthetic-access-token` / `grep -c Bearer`):
`addendum_red.txt` 0 / 0, `addendum_green.txt` 0 / 0, `addendum_module_green.txt` 0 / 0,
`probe_addendum.out` 0. No socket, no `security` subprocess, no native call, no GUI, no read of
the real `~/.claude`, `~/.claude_pet` or `~/.claude_pet.json`: HOME is a fresh temp directory
in every test and probe.

## A.5 What the two mechanisms do and do not explain (scratch probes, not tests)

`scratchpad/probe_addendum.py`: the two fixtures above, polled at further offsets, against the
HEAD copy and the tree; same stubs as the tests; counts and fixture names only. First run between
02:45 and 02:49Z (untimestamped — not acceptable under §5, so it was re-run); re-run at
02:51:56Z (`probe_addendum.out`); both runs printed identical lines.

```
mechanism R (CLI serves the rotated token from the poll after cycle 1 on):
  HEAD  cycle 1: rows=False auth_error=True cache=tokA requests=[tokA, tokA] cli=2 native=0
  HEAD  T+30: nothing sent   T+61: nothing sent, rows None, cache tokA   T+181: rows, requests [tokA, tokB], cache tokB
  tree  cycle 1: identical to HEAD
  tree  T+30: nothing sent   T+61: rows, requests [tokA, tokB], cache tokB, cli=3, native=0
mechanism P:
  HEAD  cycle 1: rows=False auth_error=True cache=tokA requests=[tokA] cli=2 native=1
  HEAD  T+30, T+61, T+121: nothing sent, rows None, cache tokA        T+181: rows, requests [tokA, tokB], native still 1
  tree  cycle 1: as HEAD except cache=None
  tree  T+30, T+61: nothing sent   T+121: rows, requests [tokB], cache tokB, cli=3, native still 1
```

Read from those numbers (deterministic on the stubs; not a claim about the user's Mac):

1. **On the pre-fix module both mechanisms recover by T+181 s** — the forced walk of the
   next cached cycle asks the CLI, which by then has the rotated token. What the tree changes
   is the wait: 60 s instead of 180 s for R, and for P one `OAUTH_TOKEN_RETRY` (120 s) with the
   dead token *not* re-sent instead of 180 s with it re-sent. So the two tests separate the tree
   from HEAD on the failure-cache window and, for P, on the cache row — and on nothing else,
   which is why cycle 2 sits at T+61 / T+121 and not later.
2. **Neither mechanism, as stubbed, reproduces a 76-minute outage on HEAD.** `probe_addendum_q.py`
   (02:50:32Z) holds the CLI *empty* in the app process from the rotation until a chosen offset
   and then serves the rotated token, polling every 30 s for 1200 s:

   ```
   HEAD  native pending  : CLI back at T+0 → recovered T+0; T+60 → T+180; T+300 → T+360; T+900 → T+900   (requests 8, native 0/1/2/5)
   HEAD  native not-found: same recovery instants and counts
   tree  native pending  : CLI back at T+0 → T+0; T+60 → T+120; T+300 → T+360; T+900 → T+960          (requests 8/8/6/3, native 0/1/3/8)
   tree  native not-found: same recovery instants and counts
   ```

   Both modules recover within one grid step of the moment the CLI serves the new token (HEAD
   on the 180 s failure-cache grid, the tree on the 120 s `OAUTH_TOKEN_RETRY` grid — which is
   why T+900 recovers at T+960 on the tree). A 76-minute outage on HEAD therefore requires the
   `security` CLI to have returned nothing, or the old token, *inside the app process* for most
   of those minutes while a fresh process got the new one. **That is a hypothesis** (AGENTS.md
   §5: presumed wrong until reproduced), it is not what either brief mechanism says, and neither
   test pins it — nor can a test, until a cause is named. Something a future occurrence could
   settle: run the installed app with `CLAUDE_PET_DEBUG=1` and read the `read_oauth: cli tok?`
   / `native st` / `oauth fetch: http` lines (booleans and codes only) across the rotation.
3. **Cadence in the no-token state.** With the CLI empty for 900 s the tree enters the native
   reader 8 times against HEAD's 5 (every 120 s vs every 180 s), and sends 3 requests against 8
   (it never re-sends the dead token). This is the Reviewer's N2 seen from the token side: the
   fetch cache no longer bounds the walk cadence once the token is forgotten;
   `OAUTH_TOKEN_RETRY` does. In the *pending* state the alive native thread is reused, so those
   entries raise no new prompt; in the not-found state each entry is a real native attempt. For
   the Coordinator alongside N2; not a failure against the design.

## A.6 Full suite with the two new tests present

Run from the repo root, in the background, while §A.2–A.5 were being written (a second
`unittest` process — the leak check of §A.4 — ran concurrently for a few seconds, which affects
wall time only).

```
$ python3 -m unittest discover -s tests -v      # started 2026-09-13T02:50:02Z, finished 02:54:24Z
Ran 558 tests in 262.326s

FAILED (failures=49, errors=8, skipped=7)
exit=1
```

(Capture: `scratchpad/addendum_fullsuite.txt`; `grep -c synthetic-access-token` → 0.)

**Test count 556 → 558**: exactly the two methods added. **Every non-passing outcome is the
same hash-pin event as §10** — classification from `grep -E '^(FAIL|ERROR): '` and the
distinct assertion lines:

| module | count | assertion (hashes abbreviated) |
| --- | --- | --- |
| `test_upload_artifact_gate` | 48 FAIL | `AssertionError: '380a651e…' != '6f95bc8b…'` (`setUp` pin of `claude_pet.py`) |
| `test_manual_update_transaction` | 8 ERROR (`setUpClass`) | `claude_pet.py changed after the shared-lock/version harness was reviewed: expected 6f95bc8b…, found 380a651e…` |
| `test_v024_release_contract` | 1 FAIL | the two `REVIEWED_APP_SOURCE_SHA256` pins vs `final claude_pet.py is 380a651e…` |

48 + 8 + 1 = 57 = 49 + 8. **No `FAIL:`/`ERROR:` header names `test_oauth_token_cache`**; its
11 header lines all end `ok`, the two new ones included:

```
Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced ... ok
Mechanism R — rotation lag. Cycle 1 (T): the cached cli-sourced tokA is ... ok
```

The 7 skips are the same loud opt-in ones as §6/§10: 3 × `test_v020_boundaries`
(`CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1`), 2 + 2 × `test_updater` (installed-app
preflight, real stapler; `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1`). The hash pins are still not
re-pinned by this role — that is the release-gate step, unchanged from §5/§10.

## A.7 Verdict (addendum)

**GREEN.** Both incident tests are RED against the committed module (`6f95bc8b…`, §A.3:
`Ran 2 tests`, `FAILED (failures=3)`, each message the one its docstring predicts) and GREEN
against the working tree (`380a651e…`, §A.4: 2/2, module 11/11, full suite 558 with the same
57 expected hash-pin refusals and nothing else, §A.6). The production file was not touched by
this role; the nine earlier methods were not touched (the file's diff against `bfb348c9…` is
additive); the final gating-file hash is `1adccf00…` (894 lines).

Two things for the Coordinator, neither a failure against the design: (1) §A.5 point 2 — the
two brief mechanisms, as stubbed, both recover on the pre-fix module within 180 s, so the
76-minute outage implies an in-process CLI outage that neither mechanism names and neither test
pins; the tests pin recovery *given* that the CLI serves the rotated token by the next cycle.
(2) §A.2 — test 1's T+61 row and the Reviewer's N2 pull in opposite directions; if 401/403 is
moved to the 180 s set, that row must move with it and the fixture then separates the tree
from HEAD on mechanism P only.

Tree note at 02:55:26Z: `git status` now also lists ` M docs/index.html`, which was clean at
02:49:59Z (§A.2) and modified in the session's opening snapshot. Not this role's edit — no
command in this addendum touched `docs/`; another track is working in the same tree
concurrently. The tracked-file set this addendum edited is empty; its deliverables are the
untracked `tests/test_oauth_token_cache.py` and this record.
