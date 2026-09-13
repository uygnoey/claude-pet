"""Gating tests for the OAuth token cache — v0.25 Track A (stale OAuth token).

Design: docs-design/followups-v025-plan-20260913.md, "Track A". Authored by the
Verifier before any production change and recorded RED against `main` at 13710db
(AGENTS.md §2 Condition A/B, §3). The Developer may fix imports or docstrings here
but must not touch an assertion, an expected value, or a fixture literal.

What the design promises, in the words these tests hold it to:

* `_oauth_token_cache` gains `src` (`file|cli|native|None`), `file_sig` (the
  `(st_mtime_ns, st_size, st_ino)` of the credentials file when `src == "file"`),
  and `suspect`. Helpers `_credentials_path()` / `_credentials_sig()` exist.
* `_read_oauth_token()` with a cached token: `src == "file"` and a changed or
  vanished signature → drop it and read afresh. `suspect` → re-validate through
  prompt-free sources only (file, then the `security` CLI when the token came
  from cli); the native Keychain path is never entered by automatic
  re-validation. A replacement replaces the cache; none keeps the cached token.
* `_fetch_oauth_usage()`: success → `suspect = False`, `auth_error = False`,
  `last_error = None`. 401/403 with no replacement after the forced walk → clear
  `tok`, `auth_error = True`. Every other failure → `suspect = True` and
  `OAUTH_STATUS["last_error"]` in `{"http:<code>", "net", "parse"}`.
* `fetch_exact_usage()`: a failed fetch is cached for `OAUTH_FAIL_RETRY_SEC = 60`
  instead of `OAUTH_CACHE_SEC = 180`, except `http:429`, which keeps 180.
* `_dbg` lines carry status codes and booleans only — never token bytes.

Isolation (CLAUDE.md "Testing policy", "Privacy"): `HOME` is patched to a fresh
temp directory for every test, so `~/.claude/.credentials.json` and
`~/claudepet_debug.log` resolve inside it; `_token_from_cli`,
`_keychain_token_native_bounded` and `_keychain_token_native` are replaced by
recording stubs (the last one by a stub that fails the test if reached);
`urllib.request.urlopen` is replaced by a scripted fake that records only the
`Authorization` header, which the assertions compare by fixture *name* and never
print; `claude_pet.time` is a shim whose `time()` is a settable clock. No test
opens a socket, runs `security`, or touches the real `~/.claude`, `~/.claude_pet`,
`~/.claude_pet.json`. Every module dict the code mutates
(`_oauth_token_cache`, `_oauth_cache`, `OAUTH_STATUS`, `_native_state`) is
snapshotted in `setUp` and restored in place by `addCleanup`.

The fixture tokens are synthetic strings of equal length; the rotation rows
depend on that equal length (a same-size rewrite is what a size-only signature
cannot see).

Addendum (2026-09-13, same role): the two methods under "7. the 2026-09-13
keychain-rotation incident" at the end of the class were written *after* the
Track A change reached the working tree, so their RED was observed against a
`git show HEAD:claude_pet.py` copy placed first on `sys.path` (record,
"ADDENDUM RED"). Everything above still describes the first nine methods.
"""

import json
import os
import shutil
import socket
import sys
import tempfile
import time as _real_time
import unittest
import urllib.error
from unittest import mock

import claude_pet


# ─────────────────────────────── fixtures ───────────────────────────────

# Equal length on purpose — see the module docstring.
TOK_A = "synthetic-access-token-A"
TOK_B = "synthetic-access-token-B"
TOK_C = "synthetic-access-token-C"
TOK_D = "synthetic-access-token-D"
TOK_E = "synthetic-access-token-E"
NAMES = {TOK_A: "tokA", TOK_B: "tokB", TOK_C: "tokC", TOK_D: "tokD", TOK_E: "tokE",
         None: "None"}

# An exact nanosecond timestamp on a whole-second boundary, so a +0.5 ms bump keeps
# the integer second (and `int(st_mtime)`) unchanged while `st_mtime_ns` differs.
T_NS = 1_700_000_000_000_000_000
T0 = 1_800_000_000.0          # fake wall clock; its "%.3f" form contains no "500"/"429"

SUCCESS_BODY = json.dumps({"limits": [
    {"kind": "five_hour", "percent": 42, "resets_at": None},
    {"kind": "seven_day", "percent": 17, "resets_at": None},
]}).encode()
BAD_JSON_BODY = b"<html><body>502 upstream gateway</body></html>"


def http_error(code):
    def make():
        return urllib.error.HTTPError(claude_pet.OAUTH_USAGE_URL, code,
                                      "synthetic", {}, None)
    make.label = "HTTPError %d" % code
    return make


def url_error():
    return urllib.error.URLError("synthetic name resolution failure")


def sock_timeout():
    return socket.timeout("synthetic timed out")


# (label, outcome, class the design records in OAUTH_STATUS["last_error"])
NON_AUTH_FAILURES = (
    ("URLError", url_error, "net"),
    ("HTTPError 500", http_error(500), "http:500"),
    ("HTTPError 429", http_error(429), "http:429"),
    ("socket timeout", sock_timeout, "net"),
    ("invalid JSON", BAD_JSON_BODY, "parse"),
)


class _Resp:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body


class _FakeHTTP:
    """Stands in for `urllib.request.urlopen`.

    `script` is a queue of outcomes consumed one per request; `default` serves
    once the queue is empty. An outcome is a bytes body or a zero-arg factory
    returning an exception to raise (fresh instance per request). Only the
    `Authorization` header of each request is kept, for comparison by name.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.auth = []
        self.script = []
        self.default = None

    @property
    def requests(self):
        return len(self.auth)

    def __call__(self, req, timeout=None):
        self.auth.append(req.get_header("Authorization"))
        outcome = self.script.pop(0) if self.script else self.default
        if outcome is None:
            raise AssertionError("fake urlopen reached with nothing scripted")
        if callable(outcome):
            outcome = outcome()
        if isinstance(outcome, BaseException):
            raise outcome
        return _Resp(outcome)


class _Source:
    """A recording stand-in for a token source; `value` is what it returns."""

    def __init__(self, value=None):
        self.value = value
        self.calls = 0

    def reset(self, value=None):
        self.value = value
        self.calls = 0

    def __call__(self, *a, **k):
        self.calls += 1
        return self.value


class _Clock:
    """Replaces the `time` module *inside claude_pet only*: `time()` is settable,
    everything else delegates to the real module."""

    def __init__(self, now):
        self.now = float(now)

    def time(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds

    def set(self, now):
        self.now = float(now)

    def __getattr__(self, name):
        return getattr(_real_time, name)


def _forbidden_native(*a, **k):
    raise AssertionError("_keychain_token_native() was reached — the raw native "
                         "reader must only run behind _keychain_token_native_bounded")


class OAuthTokenCacheCase(unittest.TestCase):

    # ───────────── isolation ─────────────

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="claudepet-oauth-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        env = mock.patch.dict(os.environ, {"HOME": self.home})
        env.start()
        self.addCleanup(env.stop)
        for key in ("CLAUDE_PET_DEBUG", "CLAUDE_PET_USE_CLI"):
            os.environ.pop(key, None)          # inside patch.dict → restored on stop
        self.assertEqual(os.path.expanduser("~"), self.home,
                         "HOME redirection failed; refusing to touch the real home")
        self.cred_path = os.path.join(self.home, ".claude", ".credentials.json")

        for name in ("_oauth_token_cache", "_oauth_cache", "OAUTH_STATUS", "_native_state"):
            d = getattr(claude_pet, name)
            self.addCleanup(self._restore, d, dict(d))

        self.cli = _Source(None)
        self.native = _Source((claude_pet._SEC_ITEM_NOT_FOUND, None))
        self.http = _FakeHTTP()
        self.clock = _Clock(T0)
        for target, repl in (
            ("_token_from_cli", self.cli),
            ("_keychain_token_native_bounded", self.native),
            ("_keychain_token_native", _forbidden_native),
            ("time", self.clock),
        ):
            p = mock.patch.object(claude_pet, target, repl)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(claude_pet.urllib.request, "urlopen", self.http)
        p.start()
        self.addCleanup(p.stop)
        self.reset_state()

    @staticmethod
    def _restore(d, snapshot):
        d.clear()
        d.update(snapshot)

    def reset_state(self):
        """Cold process state, without deleting keys the fixed code may rely on."""
        c = claude_pet._oauth_token_cache
        c.update({"tok": None, "next_retry": 0.0, "declined": False})
        for key, cold in (("src", None), ("file_sig", None), ("suspect", False)):
            if key in c:
                c[key] = cold
        claude_pet._oauth_cache.update({"t": 0.0, "gauges": None})
        claude_pet.OAUTH_STATUS["auth_error"] = False
        if "last_error" in claude_pet.OAUTH_STATUS:
            claude_pet.OAUTH_STATUS["last_error"] = None
        claude_pet._native_state.update({"thread": None, "result": None})
        self.cli.reset(None)
        self.native.reset((claude_pet._SEC_ITEM_NOT_FOUND, None))
        self.http.reset()
        self.clock.set(T0)
        self.remove_credentials()

    def platform(self, name):
        return mock.patch.object(sys, "platform", name)

    # ───────────── credentials file helpers ─────────────

    def write_credentials(self, token, mtime_ns):
        """In-place rewrite (`open(.., "w")` truncates and keeps the inode), then
        pin the mtime exactly."""
        os.makedirs(os.path.dirname(self.cred_path), exist_ok=True)
        with open(self.cred_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"claudeAiOauth": {"accessToken": token}}))
        os.utime(self.cred_path, ns=(mtime_ns, mtime_ns))
        return self.cred_path

    def replace_credentials(self, token, mtime_ns):
        """Atomic-rename rewrite: a new inode with the mtime pinned *before* the
        rename, so only `st_ino` differs from the previous signature."""
        os.makedirs(os.path.dirname(self.cred_path), exist_ok=True)
        tmp = self.cred_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"claudeAiOauth": {"accessToken": token}}))
        os.utime(tmp, ns=(mtime_ns, mtime_ns))
        os.replace(tmp, self.cred_path)
        return self.cred_path

    def remove_credentials(self):
        try:
            os.remove(self.cred_path)
        except FileNotFoundError:
            pass

    # ───────────── assertions that never print a token ─────────────

    def read_name(self):
        return NAMES.get(claude_pet._read_oauth_token(), "<unexpected token>")

    def cached_name(self):
        return NAMES.get(claude_pet._oauth_token_cache.get("tok"), "<unexpected token>")

    def assertBearer(self, token, msg):
        sent = self.http.auth[-1] if self.http.auth else None
        sent_tok = sent[len("Bearer "):] if isinstance(sent, str) and sent.startswith("Bearer ") else None
        self.assertEqual(NAMES.get(sent_tok, "<unexpected token>"), NAMES[token],
                         "%s (request %d)" % (msg, self.http.requests))

    # ───────────── 0. the helpers the design names ─────────────

    def test_credentials_helpers_resolve_under_home_and_sign_the_file(self):
        """`_credentials_path()` resolves `~/.claude/.credentials.json` under the
        (patched) HOME; `_credentials_sig()` is None for a missing file, stable
        while the file is untouched, and changes on each of the three rewrites the
        rotation test uses.

        Rival implementations and what each yields on the three rewrites
        (rewrite 1: same size, same inode, +0.5 ms; rewrite 2: new inode, mtime and
        size preserved; the "unchanged" row is a repeat stat):

        | signature source         | unchanged | +0.5 ms | new inode |
        | ------------------------ | --------- | ------- | --------- |
        | int(st_mtime) only       | same      | same ✗  | same ✗    |
        | st_mtime_ns only         | same      | changed | same ✗    |
        | st_size only             | same      | same ✗  | same ✗    |
        | st_ino only              | same      | same ✗  | changed   |
        | (mtime_ns, size, ino)    | same      | changed | changed   |

        Today: AttributeError — neither helper exists.
        """
        self.assertEqual(os.path.realpath(claude_pet._credentials_path()),
                         os.path.realpath(self.cred_path))
        self.assertIsNone(claude_pet._credentials_sig(), "missing file must sign as None")

        self.write_credentials(TOK_A, mtime_ns=T_NS)
        sig1 = claude_pet._credentials_sig()
        self.assertIsNotNone(sig1)
        self.assertEqual(claude_pet._credentials_sig(), sig1, "signature drifted on an untouched file")

        self.write_credentials(TOK_B, mtime_ns=T_NS + 500_000)      # same size, inode, second
        sig2 = claude_pet._credentials_sig()
        self.assertNotEqual(sig2, sig1, "same-size rewrite 0.5 ms later not detected")

        self.replace_credentials(TOK_C, mtime_ns=T_NS + 500_000)    # new inode only
        sig3 = claude_pet._credentials_sig()
        self.assertNotEqual(sig3, sig2, "atomic-rename rewrite with preserved mtime not detected")

    # ───────────── 1. rotation without restart ─────────────

    def test_file_token_rotation_is_picked_up_without_restart(self):
        """A rotated `~/.claude/.credentials.json` is served by the next
        `_read_oauth_token()` — no restart — and an *unchanged* file is served from
        the cache without consulting the Keychain. Run on `darwin` (file wins before
        the CLI/native block) and `win32` (the file is the only source; this is the
        Windows port's only rotation signal).

        Rows, in the order applied to ONE file (tokens are all the same length):

        | row | change to the file                                   | expected |
        | --- | ---------------------------------------------------- | -------- |
        | 0   | written with tokA, mtime T                           | tokA     |
        | 1   | in-place tokB, same size+inode, mtime T + 0.5 ms     | tokB     |
        | 2   | in-place tokC, signature restored to row 1's exactly | tokB     |
        | 3   | os.replace → tokD, new inode, mtime/size preserved   | tokD     |
        | 4   | in-place tokE, mtime + 2 s                           | tokE     |
        | 5   | untouched, repeat call; CLI/native call counts       | tokE / 0 |

        Truth table (what each rival returns per row):

        | row | never re-stat (today) | always re-read | int(mtime) only | mtime_ns only | size only | ino only | **design** |
        | --- | --------------------- | -------------- | --------------- | ------------- | --------- | -------- | ---------- |
        | 1   | tokA ✗                | tokB           | tokA ✗          | tokB          | tokA ✗    | tokA ✗   | **tokB**   |
        | 2   | tokA ✗                | tokC ✗         | tokA ✗          | tokB          | tokA ✗    | tokA ✗   | **tokB**   |
        | 3   | tokA ✗                | tokD           | tokB ✗          | tokB ✗        | tokB ✗    | tokD     | **tokD**   |
        | 4   | tokA ✗                | tokE           | tokE            | tokE          | tokD ✗    | tokD ✗   | **tokE**   |

        Row 2 is the tie-break-style row: a rewrite that preserves all three stat
        fields is not something a real writer produces, but it is the only fixture
        under which "always re-read the file" and "cache keyed by signature" give
        different answers — the design chose the signature-keyed cache. Row 3 is
        the atomic-rename shape (new inode), row 4 the in-place shape (new mtime).
        Today: row 1 fails with 'tokA' != 'tokB'.
        """
        for platform in ("darwin", "win32"):
            with self.subTest(platform=platform):
                self.reset_state()
                with self.platform(platform):
                    self.write_credentials(TOK_A, mtime_ns=T_NS)
                    self.assertEqual(self.read_name(), "tokA", "row 0")

                    self.write_credentials(TOK_B, mtime_ns=T_NS + 500_000)
                    self.assertEqual(self.read_name(), "tokB",
                                     "row 1: same-size in-place rewrite 0.5 ms later not picked up")

                    self.write_credentials(TOK_C, mtime_ns=T_NS + 500_000)
                    self.assertEqual(self.read_name(), "tokB",
                                     "row 2: signature unchanged, so the cached token must be served")

                    self.replace_credentials(TOK_D, mtime_ns=T_NS + 500_000)
                    self.assertEqual(self.read_name(), "tokD",
                                     "row 3: new inode with preserved mtime not picked up")

                    self.write_credentials(TOK_E, mtime_ns=T_NS + 2_000_500_000)
                    self.assertEqual(self.read_name(), "tokE",
                                     "row 4: in-place rewrite 2 s later not picked up")

                    self.assertEqual(self.read_name(), "tokE", "row 5: untouched file")
                    self.assertEqual((self.cli.calls, self.native.calls), (0, 0),
                                     "a file-sourced token must never send the reader to the Keychain")

    def test_vanished_credentials_file_drops_the_cached_token(self):
        """Design: "if `src == "file"` and the signature changed **or the file
        vanished** → drop the cached token and read afresh." On `win32` the file is
        the only source, so after it vanishes the fresh read finds nothing and the
        reader returns None; once the retry cooldown lapses and the file is back
        with tokB, tokB is served.

        | step                                   | keep-serving (today) | design |
        | -------------------------------------- | -------------------- | ------ |
        | file removed → read                    | tokA ✗               | None   |
        | file back with tokB, cooldown lapsed   | tokA ✗               | tokB   |

        Today: 'cached token served after the file vanished'.
        """
        with self.platform("win32"):
            self.write_credentials(TOK_A, mtime_ns=T_NS)
            self.assertEqual(self.read_name(), "tokA")
            self.remove_credentials()
            self.assertEqual(self.read_name(), "None", "cached token served after the file vanished")
            self.write_credentials(TOK_B, mtime_ns=T_NS + 5_000_000_000)
            self.clock.advance(claude_pet.OAUTH_TOKEN_RETRY + 1)
            self.assertEqual(self.read_name(), "tokB", "restored file not read after the cooldown")
            self.assertEqual((self.cli.calls, self.native.calls), (0, 0))

    # ───────────── 2. non-auth failure → prompt-free re-validation ─────────────

    def test_non_auth_failure_revalidates_through_prompt_free_sources_only(self):
        """After a non-auth failure the *next* `_fetch_oauth_usage()` re-validates
        the cli-sourced token through prompt-free sources only. Per failure class
        (URLError, HTTPError 500, HTTPError 429, socket timeout, invalid JSON) and
        per replacement scenario:

        * `cli`  — the `security` CLI now yields tokB → the next request carries tokB.
        * `file` — a credentials file with tokB has appeared while the CLI still
          yields tokA → tokB (file is consulted before the CLI).
        * `none` — the CLI yields nothing → the cached tokA is kept and sent, and
          the CLI *was* consulted (its call count rose).
        * `file-src-unchanged` — the token came from the file and the file is
          untouched → tokA is sent and the CLI is never consulted (only a
          cli-sourced token re-validates through the CLI).

        In every scenario the native Keychain stub is called 0 times and the
        failing fetch itself leaves the cached token in place.

        Truth table (header on the request after the failure / native calls /
        CLI consulted on the retry):

        | scenario | keep-serving (today) | drop + re-walk incl. native (opt A) | re-validate cli-first | **design**   |
        | -------- | -------------------- | ----------------------------------- | --------------------- | ------------ |
        | cli      | tokA ✗ / 0 / no ✗    | tokB / 0 / yes                      | tokB / 0 / yes        | tokB/0/yes   |
        | file     | tokA ✗               | tokB                                | tokA ✗                | tokB         |
        | none     | tokA / 0 / no ✗      | no request ✗ / 1 ✗ / yes            | tokA / 0 / yes        | tokA/0/yes   |
        | file-src | tokA / 0 / no        | tokA / 0 / yes ✗                    | tokA / 0 / no         | tokA/0/no    |

        `none` is the row that separates option A from the design (A walks on
        to the native path when the CLI has nothing); `file-src` is GREEN today by
        construction and only rules out "re-walk everything". Today: the `cli`
        rows fail with "request carried tokA, expected tokB".
        """
        for label, outcome, _cls in NON_AUTH_FAILURES:
            for scenario in ("cli", "file", "none", "file-src-unchanged"):
                with self.subTest(failure=label, replacement=scenario):
                    self.reset_state()
                    with self.platform("darwin"):
                        if scenario == "file-src-unchanged":
                            self.write_credentials(TOK_A, mtime_ns=T_NS)
                        else:
                            self.cli.value = TOK_A
                        self.assertEqual(self.read_name(), "tokA", "fixture: token not cached")
                        cli_before = self.cli.calls

                        self.http.script = [outcome]
                        self.assertIsNone(claude_pet._fetch_oauth_usage())
                        self.assertBearer(TOK_A, "fixture: failing request did not carry the cached token")
                        self.assertEqual(self.cached_name(), "tokA",
                                         "a non-auth failure must not discard the cached token")

                        if scenario == "cli":
                            self.cli.value = TOK_B
                            expected = TOK_B
                        elif scenario == "file":
                            self.write_credentials(TOK_B, mtime_ns=T_NS + 7_000_000_000)
                            expected = TOK_B
                        elif scenario == "none":
                            self.cli.value = None
                            expected = TOK_A
                        else:
                            expected = TOK_A

                        self.http.script = [SUCCESS_BODY]
                        rows = claude_pet._fetch_oauth_usage()
                        self.assertTrue(rows, "the retry with a valid response must return rows")
                        self.assertBearer(expected, "request after a %s carried the wrong token" % label)
                        self.assertEqual(self.native.calls, 0,
                                         "automatic re-validation entered the native Keychain path")
                        if scenario in ("cli", "none"):
                            self.assertGreater(self.cli.calls, cli_before,
                                               "cli-sourced token was not re-validated through the security CLI")
                        elif scenario == "file-src-unchanged":
                            self.assertEqual(self.cli.calls, 0,
                                             "a file-sourced token must not be re-validated through the CLI")

    # ───────────── 3. persistent 401 with no replacement ─────────────

    def test_401_with_no_replacement_stops_serving_the_dead_token(self):
        """401 on the request, forced walk finds nothing (CLI → None, native →
        (-25300, None), no file): `OAUTH_STATUS["auth_error"]` is True, the cache no
        longer holds the dead token, `_read_oauth_token()` during the retry cooldown
        returns None, and after the cooldown a credentials file with tokB is served.

        | step                       | keep-dead-token (today) | clear tok, no auth_error | **design** |
        | -------------------------- | ----------------------- | ------------------------ | ---------- |
        | auth_error after the fetch | True                    | False ✗                  | True       |
        | cache["tok"]               | tokA ✗                  | None                     | None       |
        | read during cooldown       | tokA ✗                  | None                     | None       |
        | file tokB, cooldown lapsed | tokA ✗                  | tokB                     | tokB       |

        Today: 'dead token retained in the cache after a 401 with no replacement'.
        """
        with self.platform("darwin"):
            self.cli.value = TOK_A
            self.assertEqual(self.read_name(), "tokA")
            self.cli.value = None
            self.http.default = http_error(401)

            self.assertIsNone(claude_pet._fetch_oauth_usage())
            self.assertTrue(claude_pet.OAUTH_STATUS["auth_error"])
            self.assertEqual(self.cached_name(), "None",
                             "dead token retained in the cache after a 401 with no replacement")
            self.assertEqual(self.read_name(), "None", "dead token re-served during the retry cooldown")

            self.write_credentials(TOK_B, mtime_ns=T_NS)
            self.clock.advance(claude_pet.OAUTH_TOKEN_RETRY + 1)
            self.assertEqual(self.read_name(), "tokB", "replacement token not read after the cooldown")

    def test_401_forced_walk_reaches_native_once_and_respects_declined(self):
        """Pin of the UNCHANGED v0.16 contract (GREEN before and after; it gates
        nothing new and is here so the fix cannot regress it): the 401 forced walk
        may reach the native reader — exactly once — unless the user declined.

        | declined | native calls today | native calls after |
        | -------- | ------------------ | ------------------ |
        | True     | 0                  | 0                  |
        | False    | 1                  | 1                  |
        """
        for declined, expected_calls in ((True, 0), (False, 1)):
            with self.subTest(declined=declined):
                self.reset_state()
                with self.platform("darwin"):
                    self.cli.value = TOK_A
                    self.assertEqual(self.read_name(), "tokA")
                    self.cli.value = None
                    claude_pet._oauth_token_cache["declined"] = declined
                    self.http.default = http_error(401)
                    self.assertIsNone(claude_pet._fetch_oauth_usage())
                    self.assertTrue(claude_pet.OAUTH_STATUS["auth_error"])
                    self.assertEqual(self.native.calls, expected_calls)

    # ───────────── 4. fail-retry window ─────────────

    def test_failed_fetch_retries_within_fail_retry_sec_except_429(self):
        """`fetch_exact_usage()` caches a failed fetch for `OAUTH_FAIL_RETRY_SEC`
        (60) instead of `OAUTH_CACHE_SEC` (180), except `http:429`, which keeps the
        full 180 (the "과호출 시 429 → 3분 캐시 필수" rationale). Success keeps 180.
        Measured by counting requests through the fake `urlopen` at three clock
        offsets from the first fetch: +30 s, +OAUTH_FAIL_RETRY_SEC+1, +OAUTH_CACHE_SEC+1.

        Truth table (requests seen after each offset, starting from 1):

        | outcome      | uniform 180 (today) | uniform 60 incl. 429 | retry every call | **design** |
        | ------------ | ------------------- | -------------------- | ---------------- | ---------- |
        | HTTPError 500| 1 / 1 ✗ / 2         | 1 / 2 / 3            | 2 ✗ / …          | 1 / 2 / 3  |
        | URLError     | 1 / 1 ✗ / 2         | 1 / 2 / 3            | 2 ✗ / …          | 1 / 2 / 3  |
        | HTTPError 429| 1 / 1 / 2           | 1 / 2 ✗ / 3          | 2 ✗ / …          | 1 / 1 / 2  |
        | success      | 1 / 1 / 2           | 1 / 2 ✗ / 3          | 1 / 1 / 2        | 1 / 1 / 2  |

        Today: AttributeError on `OAUTH_FAIL_RETRY_SEC`; with the constant alone
        added, the 500/URLError rows fail at +61 s with 1 != 2.
        """
        self.assertEqual(claude_pet.OAUTH_FAIL_RETRY_SEC, 60)
        self.assertLess(claude_pet.OAUTH_FAIL_RETRY_SEC, claude_pet.OAUTH_CACHE_SEC)
        FAIL, CACHE = "fail-retry", "full-cache"
        cases = (
            ("HTTPError 500", http_error(500), FAIL),
            ("URLError", url_error, FAIL),
            ("HTTPError 429", http_error(429), CACHE),
            ("success", SUCCESS_BODY, CACHE),
        )
        for label, outcome, hold in cases:
            with self.subTest(outcome=label):
                self.reset_state()
                with self.platform("darwin"):
                    self.cli.value = TOK_A
                    self.http.default = outcome

                    first = claude_pet.fetch_exact_usage()
                    if hold == FAIL or label.startswith("HTTPError"):
                        self.assertIsNone(first)
                    else:
                        self.assertTrue(first)
                    self.assertEqual(self.http.requests, 1)

                    self.clock.set(T0 + 30)
                    claude_pet.fetch_exact_usage()
                    self.assertEqual(self.http.requests, 1,
                                     "%s: refetched one refresh tick later — nothing is cached" % label)

                    self.clock.set(T0 + claude_pet.OAUTH_FAIL_RETRY_SEC + 1)
                    claude_pet.fetch_exact_usage()
                    if hold == FAIL:
                        self.assertEqual(self.http.requests, 2,
                                         "%s: no retry within OAUTH_FAIL_RETRY_SEC" % label)
                    else:
                        self.assertEqual(self.http.requests, 1,
                                         "%s: retried before OAUTH_CACHE_SEC elapsed" % label)

                    self.clock.set(T0 + claude_pet.OAUTH_CACHE_SEC + 1)
                    claude_pet.fetch_exact_usage()
                    self.assertEqual(self.http.requests, 3 if hold == FAIL else 2,
                                     "%s: request count after OAUTH_CACHE_SEC" % label)

    # ───────────── 5. status bookkeeping ─────────────

    def test_status_bookkeeping_failure_marks_suspect_and_success_clears_everything(self):
        """Each non-auth failure sets `_oauth_token_cache["suspect"]` and records its
        class in `OAUTH_STATUS["last_error"]` (`http:<code>`, `net`, `parse`) while
        leaving `auth_error` alone; a successful fetch clears `suspect`, sets
        `auth_error` False and `last_error` None.

        | after                | today (auth_error only)     | success clears auth_error only | **design**                     |
        | -------------------- | --------------------------- | ------------------------------ | ------------------------------ |
        | HTTPError 500        | suspect absent ✗, no class ✗| suspect True, "http:500"       | suspect True, "http:500"       |
        | success (pre-set all)| auth_error False, rest stale ✗ | suspect True ✗, last_error stale ✗ | False / None / False       |

        Today: "last_error" is not a key of OAUTH_STATUS.
        """
        self.assertIn("last_error", claude_pet.OAUTH_STATUS)
        with self.platform("darwin"):
            self.cli.value = TOK_A
            self.assertEqual(self.read_name(), "tokA")
            for label, outcome, cls in NON_AUTH_FAILURES:
                with self.subTest(failure=label):
                    claude_pet.OAUTH_STATUS["auth_error"] = False
                    claude_pet.OAUTH_STATUS["last_error"] = None
                    claude_pet._oauth_token_cache["suspect"] = False
                    self.http.script = [outcome]
                    self.assertIsNone(claude_pet._fetch_oauth_usage())
                    self.assertIs(claude_pet._oauth_token_cache.get("suspect"), True,
                                  "%s did not mark the token suspect" % label)
                    self.assertEqual(claude_pet.OAUTH_STATUS.get("last_error"), cls)
                    self.assertFalse(claude_pet.OAUTH_STATUS["auth_error"],
                                     "%s is not an auth error" % label)
                    self.assertEqual(self.cached_name(), "tokA")

            claude_pet._oauth_token_cache["suspect"] = True
            claude_pet.OAUTH_STATUS["auth_error"] = True
            claude_pet.OAUTH_STATUS["last_error"] = "http:500"
            self.http.script = [SUCCESS_BODY]
            self.assertTrue(claude_pet._fetch_oauth_usage())
            self.assertFalse(claude_pet.OAUTH_STATUS["auth_error"])
            self.assertIsNone(claude_pet.OAUTH_STATUS.get("last_error"))
            self.assertIs(claude_pet._oauth_token_cache.get("suspect"), False,
                          "a successful fetch must clear suspect")

    # ───────────── 6. privacy of the diagnostics ─────────────

    def test_fetch_failure_debug_lines_carry_codes_not_token_bytes(self):
        """With `CLAUDE_PET_DEBUG=1`, a 500 and a URLError each leave a fetch
        diagnostic in `~/claudepet_debug.log` (patched HOME) that names the status
        code / failure class, and the file contains neither the token nor the word
        "Bearer". The timestamp prefix `_dbg` writes is stripped before matching
        so a wall-clock digit run cannot satisfy the "500" check.

        | log content              | no fetch _dbg (today) | logs str(e)/header ✗ | **design** |
        | ------------------------ | --------------------- | -------------------- | ---------- |
        | line with oauth + 500    | absent ✗              | present              | present    |
        | token / "Bearer" present | absent                | possible ✗           | absent     |

        Today: 'no fetch diagnostic carrying the HTTP status code'.
        """
        with mock.patch.dict(os.environ, {"CLAUDE_PET_DEBUG": "1"}), self.platform("darwin"):
            self.cli.value = TOK_A
            self.assertEqual(self.read_name(), "tokA")
            for outcome in (http_error(500), url_error):
                self.http.script = [outcome]
                self.assertIsNone(claude_pet._fetch_oauth_usage())

        log_path = os.path.join(self.home, "claudepet_debug.log")
        self.assertTrue(os.path.exists(log_path), "debug log was not written under the patched HOME")
        with open(log_path, encoding="utf-8") as f:
            log = f.read()
        self.assertFalse(TOK_A in log, "token bytes reached the debug log")
        self.assertFalse("Bearer" in log, "an Authorization header reached the debug log")
        msgs = [line.split(" ", 1)[1] if " " in line else line for line in log.splitlines()]
        self.assertTrue(any("oauth" in m.lower() and "500" in m for m in msgs),
                        "no fetch diagnostic carrying the HTTP status code")
        self.assertTrue(any("oauth" in m.lower() and ("net" in m or "URLError" in m) for m in msgs),
                        "no fetch diagnostic naming the network failure")

    # ───────────── 7. the 2026-09-13 keychain-rotation incident ─────────────
    #
    # Addendum (Verifier, Track A). Real incident on the user's Mac: v0.24 running
    # since 00:56 local, no ~/.claude/.credentials.json, token served by the
    # `security` CLI; Claude Code rotated the "Claude Code-credentials" keychain
    # item at 10:09 local; the app stayed on the amber estimate line with the ⚠ of
    # OAUTH_STATUS["auth_error"] for 76+ minutes while a fresh process obtained
    # exact mode at once through the same CLI. Two mechanisms are plausible for the
    # first failed cycle, and both must recover on a later cycle without a restart.
    # Both fixtures drive `fetch_exact_usage()` — the entry the refresh worker calls
    # every 30 s — because the failure cache lives there: `_fetch_oauth_usage()` on
    # its own cannot tell the pre-fix module from the fixed one on either mechanism
    # (its forced walk reaches the CLI on both). Nothing is reset between cycles.

    def server_accepting(self, token):
        """A zero-arg outcome for `_FakeHTTP.default`: 200 with SUCCESS_BODY when
        the request just recorded carries `token`, else HTTPError 401. The fake
        appends the header before it consults the outcome, so this decides per
        request without the fake growing a header-aware mode."""
        def outcome():
            if self.http.auth[-1] == "Bearer " + token:
                return SUCCESS_BODY
            return urllib.error.HTTPError(claude_pet.OAUTH_USAGE_URL, 401, "synthetic", {}, None)
        return outcome

    def sent_names(self, start=0):
        """Fixture names of the bearer tokens sent from request index `start` on."""
        names = []
        for sent in self.http.auth[start:]:
            tok = sent[len("Bearer "):] if isinstance(sent, str) and sent.startswith("Bearer ") else None
            names.append(NAMES.get(tok, "<unexpected token>"))
        return names

    def test_rotation_lag_recovers_on_the_next_cycle_without_restart(self):
        """Mechanism R — rotation lag. Cycle 1 (T): the cached cli-sourced tokA is
        rejected (401); the forced walk asks the `security` CLI, which still returns
        tokA (the keychain item has not been rewritten yet); the retry is rejected
        too; the cycle ends in estimate mode with `auth_error`. A poll one refresh
        tick later (T+30 s) sends nothing — the failure is cached. Cycle 2 (T+61 s,
        past OAUTH_FAIL_RETRY_SEC): the CLI now returns tokB and the server accepts
        only tokB → rows, `auth_error` False, cache tokB. The native Keychain stub is
        never called, because the CLI answered every walk.

        (T+61 is written as a literal rather than `OAUTH_FAIL_RETRY_SEC + 1` so a
        run against a module without the constant fails on behaviour, not on the
        name; item 4 pins the constant at 60.)

        Truth table — columns are the plausible implementations, cells what each
        yields (A/B = the token a request carried; "today" = the module before
        Track A: dead token kept, every failure cached 180 s):

        | step                      | today    | keep dead tok, skip forced walk | forced walk re-reads file only | native-first walk | **design**      |
        | ------------------------- | -------- | ------------------------------- | ------------------------------ | ----------------- | --------------- |
        | cycle 1 requests          | A, A     | A ✗                             | A ✗                            | A, A              | **A, A**        |
        | cycle 1 CLI consulted     | yes      | no ✗                            | no ✗                           | yes               | **yes**         |
        | cycle 1 native calls      | 0        | 0                               | 0                              | 1 ✗               | **0**           |
        | cycle 1 rows / auth_error | None / T | None / T                        | None / T                       | None / T          | **None / True** |
        | T+30 new requests         | none     | none                            | none                           | none              | **none**        |
        | T+61 rows                 | None ✗   | None ✗                          | None ✗ (cooldown, no token)    | rows              | **rows**        |
        | T+61 last request         | (none)   | A ✗                             | (none)                         | B                 | **B**           |
        | T+61 cache / auth_error   | A / T ✗  | A / T ✗                         | None / T ✗                     | B / F             | **B / False**   |

        "Cooldown applies to force mode" (the brief's fourth rival) is not separated
        by this fixture, nor by any sequence of public calls: `_remember_oauth_token`
        zeroes `next_retry` whenever a token is cached, so a forced walk under a live
        cooldown is unreachable and the two implementations agree on every reachable
        state. Recorded so nobody adds a fixture for it.

        Today: `rows` is None at T+61 — the 180 s failure cache. Polled at T+181
        instead, the same fixture recovers on the pre-fix module as well (record,
        "ADDENDUM"), so this row pins the shorter window; the recovery itself is
        older than the fix.
        """
        with self.platform("darwin"):
            self.cli.value = TOK_A
            self.assertEqual(self.read_name(), "tokA", "fixture: token not cached")
            self.assertEqual(self.cli.calls, 1)
            self.http.default = self.server_accepting(TOK_B)

            # cycle 1 — the keychain item is not rewritten yet: the CLI still says tokA
            self.assertIsNone(claude_pet.fetch_exact_usage(), "cycle 1 must end in estimate mode")
            self.assertEqual(self.sent_names(), ["tokA", "tokA"],
                             "cycle 1: the rejected token, then the forced walk's same token, then nothing")
            self.assertEqual(self.cli.calls, 2, "the forced walk did not consult the security CLI")
            self.assertEqual(self.native.calls, 0,
                             "the forced walk reached the native Keychain although the CLI answered")
            self.assertTrue(claude_pet.OAUTH_STATUS["auth_error"])

            # one refresh tick later: the failure is cached, nothing is sent
            self.clock.set(T0 + 30)
            self.assertIsNone(claude_pet.fetch_exact_usage())
            self.assertEqual(self.http.requests, 2, "a poll 30 s after the failure sent a request")

            # cycle 2 — the keychain now holds tokB
            self.cli.value = TOK_B
            self.clock.set(T0 + 61)      # OAUTH_FAIL_RETRY_SEC + 1, see the docstring
            rows = claude_pet.fetch_exact_usage()
            self.assertTrue(rows, "rotation lag: the next cycle did not recover exact mode")
            self.assertBearer(TOK_B, "the recovering request carried the wrong token")
            self.assertFalse(claude_pet.OAUTH_STATUS["auth_error"])
            self.assertEqual(self.cached_name(), "tokB")
            self.assertEqual(self.cli.calls, 3, "cycle 2 did not consult the security CLI")
            self.assertEqual(self.native.calls, 0, "recovery went through the native Keychain")

    def test_pending_native_does_not_block_cli_recovery(self):
        """Mechanism P — pending native. Cycle 1 (T): tokA is rejected; the forced
        walk finds the CLI empty (the item is mid-rewrite) and falls through to the
        native reader, which reports *pending* (`(None, None)`: the prompt is up and
        unanswered). That sets the OAUTH_TOKEN_RETRY cooldown, and the rejected
        token must not survive it (the cache row, in its own subTest so the run
        continues past it). A poll at T+30 s sends nothing. Cycle 2 (T+121 s: past
        OAUTH_FAIL_RETRY_SEC and past OAUTH_TOKEN_RETRY): the CLI now has tokB, the
        native stub is *still* pending, and the walk must take the CLI's answer
        without consulting the native reader again → rows, `auth_error` False,
        cache tokB, and the native stub called exactly once in the whole test
        (cycle 1's forced walk — the v0.16 contract item 3′ pins). `declined` stays
        False: pending is neither a failure nor a refusal.

        Truth table ("today" = pre-fix module; "native gate" = a walk that returns
        pending while the native thread is alive, before it asks the CLI; "keep at
        pending" = the fix without `_forget_oauth_token` in the pending branch;
        "pending = declined" = the pending branch setting `declined`):

        | step                     | today  | keep dead tok, skip forced walk | forced walk re-reads file only | native gate | keep at pending | pending = declined | **design** |
        | ------------------------ | ------ | ------------------------------- | ------------------------------ | ----------- | --------------- | ------------------ | ---------- |
        | cycle 1 requests         | A      | A                               | A                              | A           | A               | A                  | **A**      |
        | cycle 1 CLI consulted    | yes    | no ✗                            | no ✗                           | yes         | yes             | yes                | **yes**    |
        | cycle 1 native calls     | 1      | 0 ✗                             | 0 ✗                            | 1           | 1               | 1                  | **1**      |
        | cycle 1 cache            | A ✗    | A ✗                             | None                           | None        | A ✗             | None               | **None**   |
        | T+30 new requests        | none   | none                            | none                           | none        | none            | none               | **none**   |
        | T+121 rows               | None ✗ | None ✗                          | rows                           | None ✗      | rows            | rows               | **rows**   |
        | T+121 new requests       | none   | A ✗                             | B                              | none        | A, B ✗          | B                  | **B**      |
        | native calls, whole test | 1      | 0 ✗                             | 0 ✗                            | 2 ✗         | 1               | 1                  | **1**      |
        | declined at the end      | False  | False                           | False                          | False       | False           | True ✗             | **False**  |

        "Forced walk re-reads file only" recovers at T+121 through the ordinary
        walk; the rows that separate it are cycle 1's CLI and native counts (the
        forced walk must ask the CLI, and reach the native reader once when the CLI
        has nothing). "Cooldown applies to force mode": unreachable, see the
        previous test.

        Today: the cache row fails first (`'tokA' != 'None'`), then T+121 fails with
        `rows` None — the 180 s failure cache, the dead token still cached and no
        request sent. Polled at T+181 instead, the same fixture recovers on the
        pre-fix module too (record, "ADDENDUM").
        """
        with self.platform("darwin"):
            self.cli.value = TOK_A
            self.assertEqual(self.read_name(), "tokA", "fixture: token not cached")
            self.assertEqual(self.cli.calls, 1)
            self.http.default = self.server_accepting(TOK_B)

            # cycle 1 — CLI transiently empty, native prompt pending
            self.cli.value = None
            self.native.value = (None, None)
            self.assertIsNone(claude_pet.fetch_exact_usage(), "cycle 1 must end in estimate mode")
            self.assertEqual(self.sent_names(), ["tokA"], "no replacement token, so no retry request")
            self.assertEqual(self.cli.calls, 2, "the forced walk did not consult the security CLI")
            self.assertEqual(self.native.calls, 1,
                             "with the CLI empty the forced walk must reach the native reader once")
            self.assertTrue(claude_pet.OAUTH_STATUS["auth_error"])
            with self.subTest(step="cache after the pending forced walk"):
                self.assertEqual(self.cached_name(), "None",
                                 "the rejected token survived a forced walk that found no replacement")

            # one refresh tick later: the failure is cached, nothing is sent
            self.clock.set(T0 + 30)
            self.assertIsNone(claude_pet.fetch_exact_usage())
            self.assertEqual(self.http.requests, 1, "a poll 30 s after the failure sent a request")

            # cycle 2 — the CLI has the rotated token; the native prompt is still pending
            self.cli.value = TOK_B
            self.clock.set(T0 + claude_pet.OAUTH_TOKEN_RETRY + 1)
            rows = claude_pet.fetch_exact_usage()
            self.assertTrue(rows, "pending native: the cycle after the cooldown did not recover exact mode")
            self.assertEqual(self.sent_names(1), ["tokB"],
                             "cycle 2 must send the CLI's fresh token and nothing else")
            self.assertFalse(claude_pet.OAUTH_STATUS["auth_error"])
            self.assertEqual(self.cached_name(), "tokB")
            self.assertEqual(self.cli.calls, 3, "cycle 2 did not consult the security CLI")
            self.assertEqual(self.native.calls, 1,
                             "a pending native prompt blocked, or was re-entered by, the later walk")
            self.assertFalse(claude_pet._oauth_token_cache["declined"], "pending was recorded as a refusal")


if __name__ == "__main__":
    unittest.main()
