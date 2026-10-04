"""Codex 사용량 행 게이팅 테스트 — Verifier 작성, 구현 전.

이 파일은 아직 없는 동작을 고정한다. 작성 시점에 전부 빨강이어야 하고, 그 빨강을
먼저 관찰한 기록이 AGENTS.md §3 의 요구다.

── 왜 이 모양인지 (선행 사례 두 곳을 교차검증했다) ────────────────────────────

Codex 사용량을 읽는 방법은 우리가 발명할 것이 아니다. 같은 일을 하는 구현이 둘 있고,
2026-09-19 에 **서로 독립적으로 같은 값을 쓰고 있음을 확인했다**:

- **Orca**(로컬 앱, app.asar 에서 직접 확인): `https://chatgpt.com/backend-api/wham/usage`
  를 호출하고 `rate_limit.primary_window` / `secondary_window` 를 각각 세션/주간 레인으로
  매핑한다. 창 길이는 `limit_window_seconds` 를 분으로 환산하고, 기본값은 세션 300분.
- **CodexBar**(문서 `docs/codex.md`): 같은 엔드포인트, 같은 매핑. 자격증명은
  `~/.codex/auth.json`(또는 `$CODEX_HOME/auth.json`).

두 구현이 일치하므로 그 계약을 그대로 쓴다.

**read-only 원칙은 Claude 쪽과 동일하다.** CodexBar 가 문서에 못박은 문장:
"CodexBar never publishes refreshed native tokens into `auth.json`; when native
credentials are stale, the explicit OAuth path delegates recovery to the Codex CLI,
which owns that file." ClaudePet 은 관찰자지 ADE 가 아니다 — 회전된 토큰을 되쓸 수
없는 쪽이 갱신을 시도하면 사용자가 재로그인하게 된다. 그래서 `auth.json` 에 쓰지 않고
`https://auth.openai.com/oauth/token` 도 우리가 부르지 않는다.

**0% 를 지어내지 않는다.** PR #9 이 Claude 쪽에서 세운 원칙과 같다: 읽을 게 없는 것과
0% 인 것은 다른 사실이다. Codex 자격증명이 없거나 응답이 이상하면 **행을 아예 그리지
않는다** — 0% 행은 "안 썼다"로 읽히기 때문이다.

**윈도우 포함.** 맥에서 되는 것은 윈도우에서도 똑같이 돼야 한다. 경로 해석(`CODEX_HOME`,
홈 디렉터리)은 양쪽에서 같은 뜻이어야 하고, 이 파일은 윈도우 CI 에서도 돈다.

테스트 정책(CLAUDE.md): 실제 `~/.codex` 를 읽지 않는다. 모든 픽스처는 합성이다.

── 2026-09-30 개정: 계정 헤더 (cwdfix, Verifier) ─────────────────────────────────────

`fetch_codex_usage()` 는 `Authorization` 하나만 보냈다. Coordinator 가 2026-09-30T00:19Z 에
같은 엔드포인트를 두 번 불러 본 결과(관측, 계정 하나·호출 두 번): 헤더 없이 부르면
`account_id: ""`, `allowed: false`, `used_percent: 100` 이 왔고, `ChatGPT-Account-Id:
<auth.json 의 tokens.account_id>` 를 붙이면 `allowed: true`, `used_percent: 76` — Codex CLI 자신의
세션 파일에 남은 최신 스냅숏(76.0)과 같은 값 — 이 왔다. 2026-09-13 조사도 엔드포인트가
`tokens.access_token` + `tokens.account_id` 를 받는다고 적어 두었는데 구현이 뒤쪽을 빠뜨렸다.
그래서 코드가 해야 하는 것: `read_codex_auth(path)` 가 `(토큰, 계정 id)` 를 읽고, 계정 id 가
쓸 만할 때만 그 헤더를 보낸다. 계정 id 는 식별자라 로그·행·캐시·예외 어디에도 남기지 않는다.
아래 픽스처는 계정 id 를 **세 자리에 서로 다른 값으로** 넣어 둔다 — id_token 이나 access
token(JWT)의 클레임에서 꺼내는 경쟁 구현을 가려내려는 것이다. 전부 합성 값이다.
"""

import base64
import inspect
import io
import json
import os
import sys
import tempfile
import types
import unittest
import urllib.error
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()


# 창 길이. 이 두 수가 이 파일에서 유일하게 '어느 레인인가'를 정하는 근거다.
SESSION_WINDOW_SEC = 5 * 3600          # 300분 — Orca 가 쓰는 Codex 세션 창 기본값
WEEKLY_WINDOW_SEC = 7 * 24 * 3600      # 604800 — 사용자 계정의 실측값(아래 참조)


def usage_payload(primary_pct=12.0, secondary_pct=34.0, **kw):
    """wham/usage 응답의 최소 형태 — **세션 창과 주간 창이 모두 있는** 계정 모양.

    주의: 이 픽스처의 키 배치(primary=세션, secondary=주간)는 우리가 **가정한** 것이지
    관측된 것이 아니다. 실제로 관측된 계정은 primary 가 주간이었다(REAL_WEEKLY_ONLY_RATE_LIMIT).
    그래서 이 픽스처로 레인 매핑을 단언하면 안 된다 — 가정으로 만든 픽스처는 그 가정을
    검증하지 못한다. 레인 게이트는 창 길이로 판별하는 아래 테스트들이 맡는다.
    """
    body = {
        "plan_type": "plus",
        "rate_limit": {
            "primary_window": {"used_percent": primary_pct,
                               "limit_window_seconds": SESSION_WINDOW_SEC,
                               "reset_at": 1789900000},
            "secondary_window": {"used_percent": secondary_pct,
                                 "limit_window_seconds": WEEKLY_WINDOW_SEC,
                                 "reset_at": 1790400000},
        },
    }
    body.update(kw)
    return body


# ── 실측 페이로드 (2026-09-20, 사용자 계정의 실제 wham/usage 응답) ───────────────────
#
# **`rate_limit` 블록만 옮겨 적었다.** 응답 최상위에는 `user_id`·`account_id`·`email` 이
#들어 있고, CLAUDE.md 의 Privacy 절이 그것들을 테스트 픽스처에 넣는 것을 금지한다.
# 파서가 읽는 것은 `rate_limit` 하나뿐이라 식별자는 애초에 필요가 없다.
#
# 이 블록이 이 파일에서 유일하게 **관측된** 응답이고, 그래서 이 버그를 잡은 것이기도 하다:
# 나머지 픽스처는 전부 손으로 만든 것이라 우리가 가정한 매핑을 그대로 재생산했다.
#
#   · primary_window.limit_window_seconds == 604800 == 7일 → **주간 창이다**
#   · secondary_window 는 아예 없다 (None) — 이 계정에는 세션 창이 없다
#
# 즉 관측된 유일한 계정에서 primary 는 세션이 **아니었다**.
REAL_WEEKLY_ONLY_RATE_LIMIT = {
    "allowed": True,
    "limit_reached": False,
    "primary_window": {"used_percent": 68,
                       "limit_window_seconds": 604800,
                       "reset_after_seconds": 510968,
                       "reset_at": 1790411020},
    "secondary_window": None,
}


def auth_payload(access="ACCESS-TOKEN-VALUE", **kw):
    body = {"OPENAI_API_KEY": None,
            "tokens": {"id_token": "ID", "access_token": access,
                       "refresh_token": "REFRESH", "account_id": "acct_1"},
            "last_refresh": "2026-09-19T00:00:00Z"}
    body.update(kw)
    return body


# ── 계정 헤더 픽스처 (2026-09-30, cwdfix) ──────────────────────────────────────────


def _b64url(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def synthetic_jwt(account_claim):
    """JWT 모양의 합성 문자열(서명 없음). 실제 Codex 토큰처럼 계정 클레임을 품고 있다."""
    return ".".join((_b64url({"alg": "none", "typ": "JWT"}),
                     _b64url({"https://api.openai.com/auth":
                              {"chatgpt_account_id": account_claim}}),
                     "c2lnbmF0dXJl"))


# 세 자리 모두에 '계정 id' 가 있고 값이 전부 다르다. 계약이 읽으라는 곳은 첫째뿐이다.
ACCOUNT_IN_FILE = "acct-file-0b7e"            # tokens.account_id
ACCOUNT_IN_ID_TOKEN = "acct-idtoken-5c21"     # id_token 의 chatgpt_account_id 클레임
ACCOUNT_IN_ACCESS_JWT = "acct-access-9d43"    # access_token 의 chatgpt_account_id 클레임
ACCESS_JWT = synthetic_jwt(ACCOUNT_IN_ACCESS_JWT)
ID_JWT = synthetic_jwt(ACCOUNT_IN_ID_TOKEN)
_MISSING = object()


def auth_with_account(account=ACCOUNT_IN_FILE, access=ACCESS_JWT):
    tokens = {"id_token": ID_JWT, "access_token": access,
              "refresh_token": "REFRESH-SYNTHETIC"}
    if account is not _MISSING:
        tokens["account_id"] = account
    return {"OPENAI_API_KEY": None, "tokens": tokens, "last_refresh": "2026-09-30T00:00:00Z"}


def _write_auth(td, obj, name="auth.json"):
    p = os.path.join(td, name)
    with open(p, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f)
    return p


def _headers(req):
    """urllib 은 헤더 이름을 capitalize 한다 — 대소문자를 무시하고 본다."""
    return {k.lower(): v for k, v in req.header_items()}


def _fetch_with(test, auth_obj, respond="ok"):
    """fetch_codex_usage() 를 합성 auth.json 과 가짜 urlopen 으로 한 번 돌린다.

    네트워크는 두 겹으로 막는다: urlopen 을 바꾸고, 그래도 소켓을 열려 하면 실패시킨다.
    """
    td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    test.addCleanup(td.cleanup)
    path = _write_auth(td.name, auth_obj)
    requests, dbg = [], []

    def fake_urlopen(req, *a, **kw):
        requests.append(req)
        if respond == "http":
            raise urllib.error.HTTPError(req.full_url, 500, "server error", {}, None)
        body = b"{not json" if respond == "garbage" else json.dumps(usage_payload()).encode()
        return io.BytesIO(body)

    with mock.patch.object(claude_pet, "codex_auth_path", new=lambda *a, **k: path), \
         mock.patch.dict(claude_pet._codex_cache, {"t": 0.0, "rows": None}), \
         mock.patch.object(claude_pet.urllib.request, "urlopen", new=fake_urlopen), \
         mock.patch.object(claude_pet, "_dbg", new=lambda *a: dbg.append(a)), \
         mock.patch("socket.create_connection",
                    side_effect=AssertionError("테스트가 네트워크에 나가려 했다")):
        rows = claude_pet.fetch_codex_usage()
        cache_text = repr(dict(claude_pet._codex_cache))
    return types.SimpleNamespace(rows=rows, requests=requests, dbg=dbg, cache_text=cache_text)


class CodexAuthPathTests(unittest.TestCase):
    """자격증명 위치 — 양쪽 플랫폼에서 같은 뜻이어야 한다."""

    def test_default_is_the_dot_codex_directory_in_the_home(self):
        p = claude_pet.codex_auth_path(env={}, home="/Users/who")
        self.assertEqual(os.path.basename(p), "auth.json")
        self.assertIn(".codex", p.replace("\\", "/"))
        self.assertTrue(p.replace("\\", "/").startswith("/Users/who"))

    def test_codex_home_overrides_the_default(self):
        p = claude_pet.codex_auth_path(env={"CODEX_HOME": "/elsewhere/cfg"},
                                       home="/Users/who")
        self.assertEqual(p.replace("\\", "/"), "/elsewhere/cfg/auth.json")

    def test_an_empty_codex_home_is_not_an_override(self):
        """빈 문자열은 설정된 것이 아니다 — 그걸 루트로 삼으면 엉뚱한 곳을 본다."""
        p = claude_pet.codex_auth_path(env={"CODEX_HOME": "   "}, home="/Users/who")
        self.assertIn(".codex", p.replace("\\", "/"))


class CodexTokenReadTests(unittest.TestCase):
    """토큰은 읽기만 한다. 값은 어디에도 남기지 않는다."""

    def _write(self, td, obj):
        p = os.path.join(td, "auth.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return p

    def test_reads_the_access_token_from_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, auth_payload(access="TOK-123"))
            self.assertEqual(claude_pet.read_codex_token(p), "TOK-123")

    def test_missing_file_is_none_not_an_exception(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(claude_pet.read_codex_token(
                os.path.join(td, "nope.json")))

    def test_malformed_json_is_none_not_an_exception(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "auth.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{ not json")
            self.assertIsNone(claude_pet.read_codex_token(p))

    def test_an_api_key_only_file_has_no_oauth_token(self):
        """OPENAI_API_KEY 만 있는 파일은 OAuth 로그인이 아니다."""
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, {"OPENAI_API_KEY": "sk-xxx", "tokens": None})
            self.assertIsNone(claude_pet.read_codex_token(p))

    def test_a_blank_access_token_is_not_a_token(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, auth_payload(access="   "))
            self.assertIsNone(claude_pet.read_codex_token(p))


class CodexAuthReadTests(unittest.TestCase):
    """`read_codex_auth(path)` → `(access_token | None, account_id | None)` — 스펙 Bug 2 §1.

    토큰 규칙은 `read_codex_token` 과 똑같고, 계정 id 는 `tokens.account_id` 가 공백이 아닌
    str 일 때만(앞뒤 공백을 떼어) 준다. 토큰이 없으면 계정 id 가 있어도 `(None, None)`.
    예외는 내보내지 않는다.
    """

    def _reader(self):
        fn = getattr(claude_pet, "read_codex_auth", None)
        self.assertTrue(callable(fn), "claude_pet.read_codex_auth(path) 가 없다 — 계약 이름이다")
        return fn

    def test_it_returns_the_token_and_tokens_account_id(self):
        """Rivals: 계정 id 를 id_token 의 클레임에서 꺼냄(→ acct-idtoken-…); access token
        JWT 의 클레임에서 꺼냄(→ acct-access-…); 토큰만 돌려줌(v0.26 의 read_codex_token)."""
        fn = self._reader()
        with tempfile.TemporaryDirectory() as td:
            got = fn(_write_auth(td, auth_with_account()))
        self.assertEqual(got, (ACCESS_JWT, ACCOUNT_IN_FILE))

    def test_the_account_id_is_stripped(self):
        """헤더 값에 공백이 붙어 나가지 않게 한다. Rival: 떼지 않고 그대로 주는 구현."""
        fn = self._reader()
        with tempfile.TemporaryDirectory() as td:
            got = fn(_write_auth(td, auth_with_account(account="  %s\t" % ACCOUNT_IN_FILE)))
        self.assertEqual(got, (ACCESS_JWT, ACCOUNT_IN_FILE))

    def test_the_token_is_stripped(self):
        """토큰 규칙은 v0.26 의 read_codex_token 과 **똑같다** — 앞뒤 공백을 뗀 값을 준다.

        (리뷰 R1 이 찾은 구멍: 아래 '두 함수가 같은 값을 준다' 테스트는 둘이 **함께**
        떼지 않는 구현을 통과시킨다 — read_codex_auth 가 날것을 주고 read_codex_token 이
        그것을 그대로 넘기면 둘은 여전히 같다. 그래서 값 자체를 단언한다.)
        Rival: 공백 검사만 하고 날것을 돌려주는 read_codex_auth(+ 그대로 넘기는
        read_codex_token)."""
        fn = self._reader()
        with tempfile.TemporaryDirectory() as td:
            p = _write_auth(td, auth_with_account(access="  %s\t\n" % ACCESS_JWT))
            self.assertEqual(fn(p), (ACCESS_JWT, ACCOUNT_IN_FILE))
            self.assertEqual(claude_pet.read_codex_token(p), ACCESS_JWT)

    def test_an_unusable_account_id_is_none_but_the_token_survives(self):
        """Rivals: str() 로 억지로 바꿈(12345 → "12345", True → "True"); 빈 문자열을 그대로
        줌; 계정 id 가 없다고 토큰까지 버림."""
        fn = self._reader()
        for name, account in (("missing", _MISSING), ("null", None), ("empty", ""),
                              ("blank", " \t "), ("number", 12345), ("bool", True),
                              ("list", [ACCOUNT_IN_FILE]), ("dict", {"id": ACCOUNT_IN_FILE})):
            with self.subTest(account=name), tempfile.TemporaryDirectory() as td:
                got = fn(_write_auth(td, auth_with_account(account=account)))
                self.assertEqual(got, (ACCESS_JWT, None))

    def test_no_usable_token_is_none_none_even_with_an_account_id(self):
        """Rivals: 토큰이 없어도 계정 id 는 돌려줌((None, acct)); 깨진 파일에서 예외."""
        fn = self._reader()
        with tempfile.TemporaryDirectory() as td:
            cases = {
                "missing file": os.path.join(td, "nope.json"),
                "a directory": td,
                "malformed json": _write_auth(td, "{ not json", "bad.json"),
                "json null": _write_auth(td, "null", "null.json"),
                "json list": _write_auth(td, [ACCOUNT_IN_FILE], "list.json"),
                "api key only": _write_auth(td, {"OPENAI_API_KEY": "sk-synthetic",
                                                 "tokens": None}, "apikey.json"),
                "tokens is a list": _write_auth(td, {"tokens": [ACCESS_JWT]}, "tl.json"),
                "blank token": _write_auth(td, auth_with_account(access="   "), "blank.json"),
                "non-string token": _write_auth(td, auth_with_account(access=12345), "num.json"),
                "no access_token": _write_auth(
                    td, {"tokens": {"account_id": ACCOUNT_IN_FILE}}, "noacc.json"),
            }
            for name, path in cases.items():
                with self.subTest(case=name):
                    self.assertEqual(fn(path), (None, None))

    def test_read_codex_token_is_exactly_the_token_half(self):
        """스펙: read_codex_token(path) == read_codex_auth(path)[0]. 두 규칙이 갈라지면 행이
        보이는 조건과 요청이 나가는 조건이 달라진다."""
        fn = self._reader()
        with tempfile.TemporaryDirectory() as td:
            paths = [
                _write_auth(td, auth_with_account(), "a.json"),
                _write_auth(td, auth_with_account(account=_MISSING), "b.json"),
                _write_auth(td, auth_with_account(access="  TOK-PADDED  "), "c.json"),
                _write_auth(td, auth_with_account(access="   "), "d.json"),
                _write_auth(td, "{ not json", "e.json"),
                os.path.join(td, "nope.json"),
            ]
            for p in paths:
                with self.subTest(path=os.path.basename(p)):
                    self.assertEqual(claude_pet.read_codex_token(p), fn(p)[0])

    def test_reading_logs_neither_the_token_nor_the_account_id(self):
        """읽기는 됐는데(첫 단언) 흔적은 없어야 한다 — 읽지도 않은 구현으로 통과하지 않게.
        Rival: `_dbg("codex auth: account", acct)` 같은 진단 줄."""
        fn = self._reader()
        seen = []
        with mock.patch.object(claude_pet, "_dbg", new=lambda *a: seen.append(a)), \
                tempfile.TemporaryDirectory() as td:
            self.assertEqual(fn(_write_auth(td, auth_with_account()))[1], ACCOUNT_IN_FILE)
            fn(_write_auth(td, auth_with_account(access="   "), "blank.json"))
            fn(_write_auth(td, "{ not json", "bad.json"))
        text = " ".join(str(x) for a in seen for x in a)
        self.assertNotIn(ACCOUNT_IN_FILE, text)
        self.assertNotIn(ACCESS_JWT, text)


class CodexUsageParseTests(unittest.TestCase):
    """레인 라벨은 **창 길이**에서 나온다 — 창 키 이름에서가 아니다.

    2026-09-20 에 잡힌 실제 버그: `CODEX_LANES` 가 `primary_window → codex_session` 으로
    박혀 있었는데, 관측된 계정의 `primary_window.limit_window_seconds` 는 604800(7일)이었다.
    사용자 화면에는 "Codex 세션 68%" 가 떴고 실제로는 주간 68% 였다. 잘린 것도 아니고
    빠진 것도 아니라 **틀린 것**이라, 사용자가 화면을 보고 알아낼 방법이 없었다.

    이 파일이 그걸 못 잡은 이유를 남겨 둔다(AGENTS.md §3 의 교과서적 사례라서):
    픽스처가 전부 손으로 만든 것이었고 실제 응답은 한 번도 기록된 적이 없었다. 그래서
    픽스처는 우리가 **가정한** 매핑을 그대로 재생산했고, 단언은 값의 **위치**로만
    되어 있어서(`rows[0][1] == 12.0`) 두 레인을 통째로 맞바꿔도 초록이었다. 가정으로
    만든 픽스처는 그 가정을 검증하지 못한다.

    그래서 아래 단언은 전부 **라벨**을 본다. 위치로 단언하지 않는다.
    """

    def rows(self, payload):
        return claude_pet.parse_codex_usage(payload)

    def labels(self, payload):
        return [r[0] for r in (self.rows(payload) or ())]

    def test_the_observed_account_is_a_weekly_window_not_a_session_one(self):
        """실측 응답 하나. primary 에 들어 있지만 창이 7일이므로 주간이다.

        Rivals: 키 이름으로 매핑(= 이 버그, "Codex 세션 68%"); 창 길이를 읽되 7일을
        세션으로 분류; 행 자체를 버려서 68% 를 아예 안 보여 주는 구현.
        """
        rows = self.rows({"rate_limit": REAL_WEEKLY_ONLY_RATE_LIMIT})
        self.assertIsNotNone(rows, "실측 응답에서 행이 하나도 나오지 않는다")
        self.assertEqual([r[0] for r in rows], ["codex_weekly"],
                         "7일(604800초) 창은 주간이다 — 세션이라고 부르면 수치가 거짓말을 한다")
        self.assertEqual([r[1] for r in rows], [68.0])

    def test_a_missing_second_window_is_a_normal_account_not_an_error(self):
        """`secondary_window: None` 은 정상 경로다 — 관측된 계정이 바로 그 모양이다.

        지금 코드는 `isinstance(window, dict)` 덕분에 우연히 살아남는다. 그게 의도였는지
        우연이었는지는 테스트가 말해야 한다: 여기서 말한다. 의도다.
        Rivals: None 에서 예외; None 을 0% 행으로 만들기(= '거의 안 썼다'로 읽힌다);
        창 하나가 없다고 응답 전체를 버리기.
        """
        payload = {"rate_limit": dict(REAL_WEEKLY_ONLY_RATE_LIMIT)}
        rows = self.rows(payload)
        self.assertEqual(len(rows), 1, "창이 하나면 행도 하나다")
        for absent in (None, {}, [], "none"):
            with self.subTest(secondary=absent):
                p = {"rate_limit": dict(REAL_WEEKLY_ONLY_RATE_LIMIT, secondary_window=absent)}
                self.assertEqual([r[0] for r in (self.rows(p) or ())], ["codex_weekly"])

    def test_the_label_follows_the_window_length_not_the_key_it_arrived_under(self):
        """**이 테스트가 이 클래스의 핵심이다.**

        두 창을 '가정과 반대로' 배치한다 — 7일 창을 primary 에, 5시간 창을 secondary 에.
        라벨이 창 길이를 따른다면 primary 는 주간, secondary 는 세션이 된다. 키 이름을
        따른다면 정반대가 나온다.

        Rivals, 전부 이 픽스처가 갈라 낸다: 원래 매핑(primary→세션); 매핑을 그냥 뒤집은
        수정(primary→주간)은 아래 '가정대로' 배치에서 틀린다; 두 픽스처를 값으로만
        외운 구현.
        """
        reversed_layout = {"rate_limit": {
            "primary_window": {"used_percent": 68.0,
                               "limit_window_seconds": WEEKLY_WINDOW_SEC,
                               "reset_at": 1790400000},
            "secondary_window": {"used_percent": 12.0,
                                 "limit_window_seconds": SESSION_WINDOW_SEC,
                                 "reset_at": 1789900000}}}
        by_label = {r[0]: r[1] for r in (self.rows(reversed_layout) or ())}
        self.assertEqual(
            by_label, {"codex_weekly": 68.0, "codex_session": 12.0},
            "라벨이 창 길이가 아니라 키 이름을 따라갔다 — 이 배치에서 수치가 뒤바뀐다")

        conventional = usage_payload(primary_pct=12.0, secondary_pct=34.0)
        by_label = {r[0]: r[1] for r in (self.rows(conventional) or ())}
        self.assertEqual(
            by_label, {"codex_session": 12.0, "codex_weekly": 34.0},
            "창 길이가 가정과 같은 배치에서도 같은 규칙이어야 한다")

    def test_the_session_row_comes_before_the_weekly_row(self):
        """제공자가 달라도 읽는 순서는 같다 — Claude 필이 세션·주간 순서인 것과 같다
        (`_label_order`: 세션 0, 주간 1). Rival: 페이로드의 키 순서를 그대로 따라가서,
        같은 두 창이 계정마다 다른 순서로 보이는 구현.

        **이 테스트는 지금 초록이지만 그건 증거가 아니다.** 현재 구현은 키 이름으로
        라벨을 붙이므로 'reversed keys' 배치에서도 primary→세션 순으로 나와 우연히
        통과한다. 라벨이 창 길이를 따르게 고쳐진 **뒤에야** 이 테스트가 판별력을 갖는다
        (그때 페이로드 키 순서를 그대로 따르는 구현은 [주간, 세션]을 내놓고 실패한다).
        고치기 전의 초록을 '순서가 검증됐다'로 읽지 말 것.
        """
        for name, payload in (
            ("conventional", usage_payload()),
            ("reversed keys", {"rate_limit": {
                "primary_window": {"used_percent": 68.0,
                                   "limit_window_seconds": WEEKLY_WINDOW_SEC,
                                   "reset_at": 1790400000},
                "secondary_window": {"used_percent": 12.0,
                                     "limit_window_seconds": SESSION_WINDOW_SEC,
                                     "reset_at": 1789900000}}}),
        ):
            with self.subTest(layout=name):
                self.assertEqual(self.labels(payload), ["codex_session", "codex_weekly"])

    def test_a_window_whose_length_we_cannot_read_is_dropped_not_guessed(self):
        """창 길이가 없거나 못 쓸 값이면 그 창을 **버린다**. 키 위치로 라벨을 지어내지 않는다.

        이 파일이 이미 지키는 원칙과 같은 것이다: 수치를 못 읽는 창은 그 창만 버린다.
        라벨은 수치만큼 load-bearing 하다 — 이번 버그가 정확히 그 증거다. 모르는 창을
        '세션'이라고 부르는 것은 0% 를 지어내는 것과 같은 종류의 거짓말이다.

        Rival: 창 길이를 못 읽으면 예전처럼 키 이름으로 떨어지는 폴백 — 그 폴백 하나가
        이 버그를 통째로 되살린다.
        """
        for bad in (None, "604800", True, float("nan"), -1, 0):
            with self.subTest(limit_window_seconds=bad):
                window = dict(REAL_WEEKLY_ONLY_RATE_LIMIT["primary_window"])
                if bad is None:
                    window.pop("limit_window_seconds")
                else:
                    window["limit_window_seconds"] = bad
                rows = self.rows({"rate_limit": {"primary_window": window,
                                                 "secondary_window": None}})
                self.assertIsNone(
                    rows,
                    f"창 길이가 {bad!r} 인데 행을 만들었다: {rows!r} — 라벨을 지어냈다")

    def test_parse_reads_the_window_length_field_at_all(self):
        """구조 가드. 위 두 픽스처의 정답만 외운 구현을 막는다 — 창 길이를 실제로 읽어야
        Codex 가 나중에 세션 창을 되살리거나 키 이름을 바꿔도 따라간다."""
        source = inspect.getsource(claude_pet.parse_codex_usage)
        helpers = "".join(
            inspect.getsource(getattr(claude_pet, n))
            for n in dir(claude_pet)
            if n.startswith("_codex") and callable(getattr(claude_pet, n, None)))
        self.assertTrue(                       # assertIn 은 실패 시 소스 전체를 찍는다
            "limit_window_seconds" in source + helpers,
            "parse_codex_usage 도 _codex* 헬퍼도 limit_window_seconds 를 읽지 않는다 "
            "— 라벨에 근거가 없다")

    def test_percentages_are_clamped_to_the_zero_hundred_range(self):
        by_label = {r[0]: r[1] for r in
                    self.rows(usage_payload(primary_pct=140.0, secondary_pct=-5.0))}
        self.assertEqual(by_label["codex_session"], 100.0)
        self.assertEqual(by_label["codex_weekly"], 0.0)

    def test_a_missing_rate_limit_yields_no_rows_rather_than_zeros(self):
        """0% 는 '안 썼다'로 읽힌다. 읽을 게 없으면 행을 그리지 않는다."""
        self.assertIsNone(self.rows({"plan_type": "plus"}))

    def test_a_non_numeric_percentage_is_dropped_not_coerced(self):
        """버려지는 것은 **그 창**이다. 라벨로 단언한다 — 위치로 세면 어느 창이 살아남았는지
        말하지 못하고, 이 클래스가 잡는 버그가 정확히 그 틈으로 들어왔다."""
        bad = usage_payload()
        bad["rate_limit"]["primary_window"]["used_percent"] = "12"     # 세션 창
        rows = self.rows(bad)
        self.assertTrue(rows is None or all(isinstance(r[1], float) for r in rows))
        self.assertEqual(self.labels(bad), ["codex_weekly"],
                         "문자열을 숫자로 억지로 바꿨거나, 엉뚱한 창을 버렸다")

    def test_a_window_without_a_percentage_is_dropped(self):
        bad = usage_payload()
        del bad["rate_limit"]["secondary_window"]["used_percent"]       # 주간 창
        self.assertEqual(self.labels(bad), ["codex_session"])

    def test_garbage_input_does_not_raise(self):
        for junk in (None, [], "", 0, {"rate_limit": "nope"},
                     {"rate_limit": {"primary_window": []}}):
            with self.subTest(junk=junk):
                self.assertIsNone(self.rows(junk))


class CodexSegmentTests(unittest.TestCase):
    """필에 붙는 구간. 그리기 코드는 손대지 않는다 — 구간만 덧붙인다."""

    def test_rows_become_one_segment_the_renderer_already_understands(self):
        seg = claude_pet.roam_summary_codex(usage_payload())
        self.assertIsInstance(seg, tuple)
        self.assertEqual(len(seg), 2)
        main, sub = claude_pet.roam_summary_runs([seg], claude_pet.t)
        self.assertTrue(main, "구간이 run 으로 렌더되지 않는다")
        for text, kind in main:
            self.assertIn(kind, claude_pet.SUMMARY_COLORS,
                          "SUMMARY_COLORS 에 없는 kind 는 기본색으로 떨어진다")

    def test_no_credentials_means_no_segment_at_all(self):
        """Codex 를 안 쓰는 사용자에게 0% 행을 보여주지 않는다."""
        self.assertIsNone(claude_pet.roam_summary_codex(None))

    def test_a_claude_segment_and_a_codex_segment_render_side_by_side(self):
        """구간 **조립**만 본다 — 구분자가 들어가는가. 폭은 여기서 보지 않는다.

        원래 이 픽스처는 Claude 쪽을 `("status", "scanning")` 으로 뒀다. 가장 짧은
        구간이고, 한국어에서는 Codex 를 붙여도 필에 들어가는 **유일한** 조합이었다.
        그래서 이 테스트는 초록이면서 실제로 배포되는 모든 조합(정확 3게이지, 크레딧,
        추정치, 그리고 영어에서는 status 까지)이 잘려 나가는 것을 전혀 구별하지 못했다 —
        AGENTS.md §3 의 '아무것도 판별하지 않는 픽스처' 그 자체다.

        픽스처를 현실적인 정확 모드 게이지 3행으로 바꾼다. 단언은 그대로 둔다: 이
        테스트의 질문은 여전히 '구분자가 들어가는가'이고, 그건 폭과 무관하게 참이어야
        한다. **폭 게이트는 여기가 아니라 tests/test_summary_pill.py 의
        CodexRowFitsThePillTests 다** — 이 테스트가 초록인 것을 'Codex 행이 화면에
        보인다'는 증거로 읽으면 안 된다.
        """
        claude_seg = ("exact", [("세션", 42.0, False, "3시간 43분"),
                                ("주간", 17.0, False, "2일 4시간"),
                                ("Fable", 12.0, False, "2일 4시간")])
        codex_seg = claude_pet.roam_summary_codex(usage_payload())

        # 한 구간 목록 안에서는 여전히 구분자가 들어간다 — 그 질문은 그대로다.
        main, _ = claude_pet.roam_summary_runs([claude_seg, codex_seg], claude_pet.t)
        joined = "".join(t for t, _ in main)
        self.assertIn(claude_pet.SUMMARY_SEP.strip() or "·", joined,
                      "두 제공자 사이에 구분자가 없다")

        # **구분의 근거가 옮겨 갔다.** 예전에는 `"Codex" in joined` 로 확인했는데, 그
        # 접두사는 제거됐다(`codex_session` → "세션"). 이제 제공자를 가르는 것은 글자가
        # 아니라 **블록과 로고**다: `summary_lines` 가 제공자별로 줄 묶음을 내고 각
        # 묶음 앞에 그 제공자의 마크가 그려진다. 그러니 라벨 문자열이 아니라 그 구조를
        # 단언한다 — 라벨이 또 바뀌어도 이 테스트는 여전히 옳은 것을 묻는다.
        blocks = claude_pet.summary_lines(
            [("claude", [claude_seg]), ("codex", [codex_seg])],
            lambda s: len(s) * 7.0, 10_000.0)
        self.assertEqual([pid for pid, _lines in blocks], ["claude", "codex"],
                         "두 제공자가 각자의 블록으로 나뉘지 않는다")
        for pid, lines in blocks:
            with self.subTest(provider=pid):
                self.assertTrue(lines, f"{pid} 블록에 줄이 없다")
        # 마크가 제공자 구분을 진짜로 지고 있는지는 그리기 층의 일이다 —
        # tests/test_companion_motion.py 의
        # test_a_lone_provider_still_gets_its_mark_and_the_same_text_indent 가 본다.
        self.assertIn("codex", claude_pet.SUMMARY_LOGO_FILES,
                      "Codex 마크가 선언되지 않았다 — 접두사를 떼면 구분이 사라진다")


class CodexReadOnlyTests(unittest.TestCase):
    """관찰자는 남의 자격증명을 쓰지 않는다 — Claude 쪽과 같은 원칙."""

    def _sources(self):
        """심볼이 없으면 **에러로 죽는다.** `if hasattr(...)` 로 거르면 안 된다.

        처음엔 그 필터가 있었는데, 구현이 없는 상태에서 `_sources()` 가 빈 문자열을
        돌려주는 바람에 아래 `assertNotIn` 들이 전부 공허하게 통과했다 — 구현 전
        빨강을 관찰하지 못한 테스트가 둘 생긴 것이고, 그건 AGENTS.md §3 이 경고하는
        '아무것도 판별하지 않는 테스트'다. Developer 가 잡아 줘서 고쳤다.
        """
        names = ("codex_auth_path", "read_codex_token", "parse_codex_usage",
                 "fetch_codex_usage", "roam_summary_codex")
        return "\n".join(inspect.getsource(getattr(claude_pet, n)) for n in names)

    def test_we_never_refresh_the_codex_token_ourselves(self):
        """auth.json 의 주인은 Codex CLI 다(CodexBar 문서가 못박은 원칙)."""
        src = self._sources()
        self.assertNotIn("auth.openai.com", src)
        self.assertNotIn("oauth/token", src)
        self.assertNotIn("refresh_token", src)

    def test_we_never_write_the_auth_file(self):
        src = self._sources()
        for w in ('"w"', "'w'", '"a"', "'a'"):
            self.assertNotIn(w, src, "auth.json 에 쓰는 모드가 보인다")

    def test_the_endpoint_is_the_one_both_implementations_use(self):
        src = inspect.getsource(claude_pet.fetch_codex_usage)
        self.assertIn("chatgpt.com/backend-api/wham/usage", src)

    def test_the_account_reader_is_read_only_too(self):
        """2026-09-30: auth.json 을 읽는 함수가 하나 늘었다(read_codex_auth). 같은 원칙을
        그 함수에도 건다. `_sources()` 에 넣지 않고 따로 두는 이유: 위 두 테스트는 그 함수가
        생기기 전부터 초록이었고, 여기에 섞으면 그 둘의 뜻이 바뀐다.
        Rivals: 계정 id 를 정리해 되써 넣는 구현; 토큰을 스스로 갱신하는 구현."""
        fn = getattr(claude_pet, "read_codex_auth", None)
        self.assertTrue(callable(fn), "claude_pet.read_codex_auth(path) 가 없다 — 계약 이름이다")
        src = inspect.getsource(fn)
        for w in ('"w"', "'w'", '"a"', "'a'", '"r+"', "'r+'",
                  "auth.openai.com", "oauth/token", "refresh_token"):
            self.assertNotIn(w, src)


class CodexPrivacyTests(unittest.TestCase):
    """토큰은 로그에도 예외 메시지에도 남지 않는다."""

    def test_the_token_never_appears_in_the_parsed_output(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "auth.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(auth_payload(access="SECRET-XYZ"), f)
            tok = claude_pet.read_codex_token(p)
        rows = claude_pet.parse_codex_usage(usage_payload())
        self.assertNotIn("SECRET-XYZ", repr(rows))
        self.assertEqual(tok, "SECRET-XYZ", "읽기 자체는 돼야 한다")

    def test_debug_logging_does_not_carry_the_token(self):
        seen = []
        with mock.patch.object(claude_pet, "_dbg", lambda *a, **k: seen.append(a)):
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "auth.json")
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(auth_payload(access="SECRET-XYZ"), f)
                claude_pet.read_codex_token(p)
        self.assertNotIn("SECRET-XYZ", repr(seen))


class CodexAccountHeaderTests(unittest.TestCase):
    """`fetch_codex_usage()` 는 `ChatGPT-Account-Id: <tokens.account_id>` 를 보낸다 — Codex
    CLI 가 쓰는 계정을 서버에 알려 주는 헤더다(스펙 Bug 2 §3, 관측은 모듈 주석).

    헤더 이름은 대소문자를 가리지 않고 본다(urllib 이 capitalize 한다). 엔드포인트·캐시
    규율·파싱은 그대로여야 한다.
    """

    def test_the_request_names_the_account_from_tokens_account_id(self):
        """Rivals: 헤더 없음(v0.26 — 서버가 다른 계정 문맥으로 100%, allowed=false 를 준다);
        id_token 클레임의 값; access token JWT 클레임의 값; 다른 헤더 이름
        (`OpenAI-Account-Id`, `chatgpt_account_id` …)."""
        r = _fetch_with(self, auth_with_account())
        self.assertEqual(len(r.requests), 1, "요청이 정확히 한 번 나가야 한다")
        req = r.requests[0]
        h = _headers(req)
        self.assertEqual(req.full_url, "https://chatgpt.com/backend-api/wham/usage")
        self.assertEqual(h.get("authorization"), "Bearer " + ACCESS_JWT,
                         "Authorization 은 그대로여야 한다")
        self.assertEqual(h.get("chatgpt-account-id"), ACCOUNT_IN_FILE,
                         "ChatGPT-Account-Id 가 tokens.account_id 가 아니다 (보낸 헤더 이름: %r)"
                         % sorted(h))
        self.assertEqual([(row[0], row[1]) for row in r.rows or ()],
                         [("codex_session", 12.0), ("codex_weekly", 34.0)],
                         "헤더를 붙이면서 파싱이 달라졌다")

    def test_the_header_is_sent_exactly_when_there_is_a_usable_account_id(self):
        """표 하나로 본다 — 앞의 세 줄은 v0.26 에서 빨강이고, 나머지는 '늘 보낸다' 는 경쟁
        구현(빈 값·"None"·"12345" 를 보냄)과 '토큰 없이도 계정만으로 요청' 하는 구현을 가른다.
        토큰이 없으면 계정 id 가 있어도 **요청 자체가 없고** 행도 없다(v0.26.1 계약).
        "padded token" 줄(리뷰 R1): Authorization 에는 **공백을 뗀** 토큰이 실린다 —
        날것의 토큰으로 헤더를 만드는 구현을 가른다(모든 요청 줄이 같은 단언을 쓴다)."""
        cases = (
            ("present", auth_with_account(), True, ACCOUNT_IN_FILE),
            ("padded", auth_with_account(account=" %s " % ACCOUNT_IN_FILE), True,
             ACCOUNT_IN_FILE),
            ("padded token", auth_with_account(access="  %s\t" % ACCESS_JWT), True,
             ACCOUNT_IN_FILE),
            ("missing", auth_with_account(account=_MISSING), True, None),
            ("null", auth_with_account(account=None), True, None),
            ("empty", auth_with_account(account=""), True, None),
            ("blank", auth_with_account(account="   "), True, None),
            ("number", auth_with_account(account=12345), True, None),
            ("bool", auth_with_account(account=True), True, None),
            ("list", auth_with_account(account=[ACCOUNT_IN_FILE]), True, None),
            ("blank token", auth_with_account(access="   "), False, None),
            ("no token", {"tokens": {"account_id": ACCOUNT_IN_FILE}}, False, None),
            ("api key only", {"OPENAI_API_KEY": "sk-synthetic", "tokens": None}, False, None),
        )
        for name, auth_obj, requested, expected in cases:
            with self.subTest(case=name):
                r = _fetch_with(self, auth_obj)
                if not requested:
                    self.assertEqual(r.requests, [], "토큰이 없는데 요청이 나갔다")
                    self.assertIsNone(r.rows, "토큰이 없는데 행이 생겼다")
                    continue
                self.assertEqual(len(r.requests), 1, "토큰이 있으면 요청은 나가야 한다")
                h = _headers(r.requests[0])
                self.assertEqual(h.get("authorization"), "Bearer " + ACCESS_JWT)
                self.assertEqual(h.get("chatgpt-account-id"), expected)

    def test_the_account_id_is_used_but_never_logged_cached_or_returned(self):
        """계정 id 는 식별자다 — 로그·행·캐시 어디에도 남지 않는다. 성공·HTTP 실패·깨진 응답
        세 경로 모두. 첫 단언(헤더로 실제로 쓰였다)이 없으면 읽지도 않는 구현으로 통과한다.
        Rivals: `_dbg("codex fetch: http", e.code, acct)`; 행이나 캐시에 계정을 싣는 구현."""
        for respond in ("ok", "http", "garbage"):
            with self.subTest(response=respond):
                r = _fetch_with(self, auth_with_account(), respond=respond)
                self.assertEqual(len(r.requests), 1)
                self.assertEqual(_headers(r.requests[0]).get("chatgpt-account-id"),
                                 ACCOUNT_IN_FILE, "계정 헤더가 쓰이지 않았다")
                logged = " ".join(str(x) for a in r.dbg for x in a)
                self.assertNotIn(ACCOUNT_IN_FILE, logged, "계정 id 가 _dbg 에 남았다")
                self.assertNotIn(ACCESS_JWT, logged, "토큰이 _dbg 에 남았다")
                self.assertNotIn(ACCOUNT_IN_FILE, repr(r.rows), "계정 id 가 행에 실렸다")
                self.assertNotIn(ACCOUNT_IN_FILE, r.cache_text, "계정 id 가 캐시에 남았다")



# ═══════════════ 2026-10-05: Codex 로그 급증 감지 · Codex API 비용 (sou-verify) ═══════════════
#
# docs-design/server-only-usage-20261005.md §3.2 / §3.3 / §6. 구현 전에 쓴 게이트다 — 작성
# 시점에 전부 빨강이어야 한다(AGENTS.md §3). 이 파일에 둔 이유: 윈도우 CI 가 이 파일을 돌린다.
# 실제 ~/.codex 는 읽지 않는다. 세션 루트는 언제나 임시 디렉터리다.

from datetime import datetime as _dt, timedelta as _td, timezone as _tz  # noqa: E402

_UTC = _tz.utc


def _need(test, name):
    test.assertTrue(hasattr(claude_pet, name), "missing production interface: %s" % name)
    return getattr(claude_pet, name)


def _last(input_tokens=0, cached=0, cache_write=0, output=0, reasoning=0):
    """last_token_usage — Codex CLI 가 token_count 이벤트에 적는 모양(합성)."""
    usage = {"input_tokens": input_tokens, "cached_input_tokens": cached,
             "output_tokens": output, "reasoning_output_tokens": reasoning}
    if cache_write is not None:
        usage["cache_write_input_tokens"] = cache_write
    return usage


def _token_event(ts, last, total_tokens, info=True):
    payload = {"type": "token_count",
               "info": ({"last_token_usage": last,
                         "total_token_usage": {"total_tokens": total_tokens}}
                        if info else None)}
    return {"type": "event_msg", "timestamp": ts.isoformat().replace("+00:00", "Z"),
            "payload": payload}


class _CodexLogTree(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = os.path.join(self._td.name, "sessions")
        os.makedirs(self.root)
        self.now = _dt.now(_UTC)

    def write(self, rel, records, raw_lines=()):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            for line in raw_lines:
                f.write(line + "\n")
        return path

    def parse(self, since=None):
        fn = _need(self, "parse_codex_entries")
        return fn(self.now - _td(days=7) if since is None else since, root=self.root)


class CodexSessionsRootTests(unittest.TestCase):
    """`codex_sessions_root(env=None, home=None)` — `codex_auth_path` 와 같은 루트 규칙(§3.2)."""

    def test_same_root_rule_as_the_auth_file(self):
        fn = _need(self, "codex_sessions_root")
        home = os.path.join("H", "user")
        self.assertEqual(fn(env={}, home=home), os.path.join(home, ".codex", "sessions"))
        self.assertEqual(fn(env={"CODEX_HOME": os.path.join("X", "cx")}, home=home),
                         os.path.join("X", "cx", "sessions"))
        self.assertEqual(fn(env={"CODEX_HOME": "   "}, home=home),
                         os.path.join(home, ".codex", "sessions"))


class CodexLogWeightTests(_CodexLogTree):
    """가중: (input−cached)×1(음수면 0) + cached×0.1 + cache_write×1.25 + output×5.
    reasoning 은 더하지 않는다. noncache = total − cached×0.1. 행 모양은 Claude 와 같다:
    (ts, total, model, noncache)."""

    def test_the_weights(self):
        """input 1000, cached 400, cache_write 100, output 50, reasoning 30.

        | implementation                          | total | noncache |
        | --------------------------------------- | ----- | -------- |
        | reasoning added ×5                      | 1165  | 1125     |
        | input not reduced by cached             | 1415  | 1375     |
        | cached weighed ×1                       | 1375  | 975      |
        | cache_write ignored                     | 890   | 850      |
        | **specified**                           | **1015** | **975** |
        """
        self.write("2026/10/05/rollout-a.jsonl", [
            _token_event(self.now - _td(minutes=1),
                         _last(1000, 400, 100, 50, 30), total_tokens=1580)])
        rows = self.parse()
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][1], 1015.0)
        self.assertAlmostEqual(rows[0][3], 975.0)

    def test_cached_above_input_clamps_the_uncached_part_to_zero(self):
        """input 100, cached 400, output 2 → (0) + 40 + 10 = 50, noncache 10.
        Rival: a negative uncached input (−300 → total −250, the row vanishes or subtracts)."""
        self.write("a.jsonl", [_token_event(self.now - _td(minutes=1),
                                            _last(100, 400, None, 2), total_tokens=502)])
        rows = self.parse()
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][1], 50.0)
        self.assertAlmostEqual(rows[0][3], 10.0)

    def test_an_unusable_number_drops_only_that_row(self):
        """문자열·음수·nan·bool 이 한 칸이라도 있으면 그 행 전체를 버린다. 멀쩡한 행은 남는다."""
        bad = [_last(1000, "400", 0, 5), _last(1000, 0, 0, -1), _last(float("nan"), 0, 0, 5),
               _last(True, 0, 0, 5)]
        events = [_token_event(self.now - _td(minutes=2), b, total_tokens=100 + i)
                  for i, b in enumerate(bad)]
        events.append(_token_event(self.now - _td(minutes=1), _last(0, 0, 0, 7),
                                   total_tokens=999))
        self.write("a.jsonl", events)
        rows = self.parse()
        self.assertEqual([r[1] for r in rows], [35.0])


class CodexLogDedupTests(_CodexLogTree):
    """같은 파일 안에서 total_token_usage.total_tokens 가 같은 이벤트는 한 번만.
    시각 필터가 먼저, 그 다음 중복 집합(JSONL 불변식 3 과 같은 이유)."""

    def test_same_total_in_one_file_counts_once_but_not_across_files(self):
        """file A: tt 1000 (out 10 → 50), tt 1000 again, tt 1600 (out 20 → 100).
        file B: tt 1000 (out 30 → 150) — another session.

        | implementation              | rows | sum |
        | --------------------------- | ---- | --- |
        | no dedup                    | 4    | 350 |
        | dedup across files          | 2    | 150 |
        | **per-file dedup**          | **3** | **300** |
        """
        t = self.now - _td(minutes=20)
        self.write("a.jsonl", [_token_event(t, _last(0, 0, 0, 10), 1000),
                               _token_event(t + _td(seconds=1), _last(0, 0, 0, 10), 1000),
                               _token_event(t + _td(seconds=2), _last(0, 0, 0, 20), 1600)])
        self.write("b.jsonl", [_token_event(t + _td(seconds=3), _last(0, 0, 0, 30), 1000)])
        rows = self.parse()
        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(sum(r[1] for r in rows), 300.0)
        self.assertEqual([r[0] for r in rows], sorted(r[0] for r in rows), "rows must be sorted")

    def test_the_time_filter_runs_before_the_dedup_set(self):
        """since−60s tt 2000, since+60s tt 2000 (same file). Rival: dedup first — the
        out-of-window event claims the key and the in-window one vanishes (0 rows)."""
        since = self.now - _td(hours=1)
        self.write("a.jsonl", [_token_event(since - _td(seconds=60), _last(0, 0, 0, 10), 2000),
                               _token_event(since + _td(seconds=60), _last(0, 0, 0, 10), 2000)])
        rows = self.parse(since=since)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], since + _td(seconds=60))

    def test_null_info_is_skipped_and_claims_nothing(self):
        t = self.now - _td(minutes=3)
        self.write("a.jsonl", [_token_event(t, None, 0, info=False),
                               _token_event(t + _td(seconds=1), _last(0, 0, 0, 4), 10)])
        rows = self.parse()
        self.assertEqual([r[1] for r in rows], [20.0])


class CodexLogFileTests(_CodexLogTree):
    def test_recursion_other_events_and_garbage(self):
        """Nested date folders are found; non-token_count events and broken lines are
        skipped without killing the file."""
        t = self.now - _td(minutes=3)
        decoy = {"type": "event_msg", "timestamp": t.isoformat().replace("+00:00", "Z"),
                 "payload": {"type": "agent_message",
                             "info": {"last_token_usage": _last(0, 0, 0, 999),
                                      "total_token_usage": {"total_tokens": 5}}}}
        self.write(os.path.join("2026", "10", "05", "rollout-x.jsonl"),
                   [decoy, _token_event(t, _last(0, 0, 0, 3), 7)],
                   raw_lines=("{not json", "[]", '"str"'))
        rows = self.parse()
        self.assertEqual([r[1] for r in rows], [15.0])

    def test_mtime_is_only_a_prefilter(self):
        """A file touched now holding 10-day-old records yields nothing (불변식 6)."""
        old = self.now - _td(days=10)
        path = self.write("a.jsonl", [_token_event(old, _last(0, 0, 0, 3), 7)])
        os.utime(path, None)
        self.assertEqual(self.parse(), [])

    def test_nothing_identifying_reaches_the_debug_log(self):
        """CLAUDE.md Privacy: no path (the temp root carries a session-like name here) and
        no content in `_dbg`."""
        t = self.now - _td(minutes=3)
        self.write(os.path.join("2026", "rollout-SESSIONID-777.jsonl"),
                   [_token_event(t, _last(0, 0, 0, 3), 7)], raw_lines=("{broken",))
        seen = []
        with mock.patch.object(claude_pet, "_dbg", side_effect=lambda *a: seen.append(a)):
            self.parse()
        logged = " ".join(str(x) for a in seen for x in a)
        self.assertNotIn("SESSIONID-777", logged)
        self.assertNotIn(self._td.name, logged)


class CodexSpikeTests(unittest.TestCase):
    """`codex_spikes(entries, now, learned=None, mult=None)` → {"codex_session": bool,
    "codex_weekly": bool}. SPIKE_BASE 의 대응값 session 2.0, weekly 0.5. Claude 와 같은 창
    (직전 5분 burn, 그 앞 25분 활성 버킷 평균), burn 은 noncache."""

    def setUp(self):
        self.now = _dt(2026, 10, 5, 12, 0, tzinfo=_UTC)

    def e(self, minutes_ago, noncache, total=None):
        return (self.now - _td(minutes=minutes_ago), float(total or noncache), "codex",
                float(noncache))

    def test_the_base_percentages(self):
        self.assertEqual(claude_pet.SPIKE_BASE.get("codex_session"), 2.0)
        self.assertEqual(claude_pet.SPIKE_BASE.get("codex_weekly"), 0.5)

    def test_nothing_learned_means_no_spike(self):
        fn = _need(self, "codex_spikes")
        out = fn([self.e(1, 10 ** 9)], self.now, learned={}, mult=1.0)
        self.assertEqual(out, {"codex_session": False, "codex_weekly": False})

    def test_lanes_use_their_own_floor_and_the_noncache_burn(self):
        """Both lanes learned at 1_000_000: floors session 20_000, weekly 5_000. Burn:
        noncache 10_000, total 100_000.

        | implementation                 | session | weekly |
        | ------------------------------ | ------- | ------ |
        | base_pct swapped               | True    | False  |
        | burn weighed by total          | True    | True   |
        | **specified**                  | **False** | **True** |
        """
        fn = _need(self, "codex_spikes")
        learned = {"codex_session": 1_000_000.0, "codex_weekly": 1_000_000.0}
        out = fn([self.e(1, 10_000, total=100_000)], self.now, learned=learned, mult=1.0)
        self.assertEqual(out, {"codex_session": False, "codex_weekly": True})

    def test_the_active_base_gate_applies(self):
        """Steady 8_000 per 5-minute bucket for the preceding 25 minutes → base 8_000,
        gate 20_000 > burn 10_000 → no spike. Rival: no base gate (weekly True)."""
        fn = _need(self, "codex_spikes")
        learned = {"codex_weekly": 1_000_000.0}
        entries = [self.e(m, 8_000) for m in (7, 12, 17, 22, 27)] + [self.e(1, 10_000)]
        out = fn(entries, self.now, learned=learned, mult=1.0)
        self.assertFalse(out["codex_weekly"])


class _FakeHTTP:
    """Sequential fake `urlopen`: records each Request, answers from `answers`."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        ans = self.answers.pop(0)
        if isinstance(ans, BaseException):
            raise ans
        body = ans if isinstance(ans, bytes) else json.dumps(ans).encode("utf-8")
        return io.BytesIO(body)


class CodexApiCostTests(unittest.TestCase):
    """`fetch_codex_cost(start_dt)` and `CODEX_API_STATUS` — §6, symmetric with
    `fetch_api_cost` / `API_STATUS`. Key from RUNTIME["openai_admin_key"]."""

    KEY = "sk-admin-SYNTHETIC-123"
    START = _dt(2026, 10, 1, 0, 0, tzinfo=_UTC)

    def setUp(self):
        saved = dict(claude_pet.RUNTIME)
        self.addCleanup(lambda: (claude_pet.RUNTIME.clear(), claude_pet.RUNTIME.update(saved)))
        claude_pet.RUNTIME["openai_admin_key"] = self.KEY
        status = getattr(claude_pet, "CODEX_API_STATUS", None)
        if isinstance(status, dict):
            prev = dict(status)
            self.addCleanup(lambda: (status.clear(), status.update(prev)))
            status["last_error"] = None

    def run_fetch(self, answers):
        fetch = _need(self, "fetch_codex_cost")
        fake = _FakeHTTP(answers)
        dbg = []
        with mock.patch.object(claude_pet.urllib.request, "urlopen", side_effect=fake), \
                mock.patch.object(claude_pet, "_dbg", side_effect=lambda *a: dbg.append(a)):
            value = fetch(self.START)
        return value, fake, dbg

    def test_no_key_no_request(self):
        claude_pet.RUNTIME["openai_admin_key"] = ""
        value, fake, _ = self.run_fetch([])
        self.assertIsNone(value)
        self.assertEqual(fake.requests, [])

    def test_pages_are_followed_and_every_result_summed(self):
        """page 1: two results 1.25 + 0.75, has_more → page 2: 3.00.

        | implementation                 | result |
        | ------------------------------ | ------ |
        | first page only                | 2.00   |
        | first result per bucket        | 4.25   |
        | **all pages, all results**     | **5.00** |
        """
        page1 = {"object": "page", "data": [{"results": [{"amount": {"value": 1.25,
                                                                     "currency": "usd"}},
                                                         {"amount": {"value": 0.75,
                                                                     "currency": "usd"}}]}],
                 "has_more": True, "next_page": "pg_2"}
        page2 = {"object": "page", "data": [{"results": [{"amount": {"value": 3.0,
                                                                     "currency": "usd"}}]}],
                 "has_more": False, "next_page": None}
        value, fake, _ = self.run_fetch([page1, page2])
        self.assertAlmostEqual(value, 5.0)
        self.assertEqual(len(fake.requests), 2)
        first = urllib.parse.urlsplit(fake.requests[0].full_url)
        q1 = urllib.parse.parse_qs(first.query)
        self.assertEqual((first.scheme, first.netloc, first.path),
                         ("https", "api.openai.com", "/v1/organization/costs"))
        self.assertEqual(q1.get("start_time"), [str(int(self.START.timestamp()))])
        self.assertEqual(q1.get("bucket_width"), ["1d"])
        self.assertEqual(q1.get("limit"), ["31"])
        self.assertEqual(_headers(fake.requests[0]).get("authorization"), "Bearer " + self.KEY)
        q2 = urllib.parse.parse_qs(urllib.parse.urlsplit(fake.requests[1].full_url).query)
        self.assertEqual(q2.get("page"), ["pg_2"])
        self.assertIsNone(claude_pet.CODEX_API_STATUS["last_error"])

    def test_failures_are_classified_like_the_anthropic_cost(self):
        """401/403 → "http:<code>" (api_error_kind "key"); network → "net" ("transient");
        a broken body → "parse". Rival: everything as "net" (a rejected key would read as
        an outage)."""
        cases = (
            (urllib.error.HTTPError("u", 401, "no", {}, None), "http:401", "key"),
            (urllib.error.HTTPError("u", 403, "no", {}, None), "http:403", "key"),
            (urllib.error.URLError("down"), "net", "transient"),
            (b"{not json", "parse", "transient"),
        )
        for answer, err, kind in cases:
            with self.subTest(err=err):
                value, _fake, dbg = self.run_fetch([answer])
                self.assertIsNone(value)
                self.assertEqual(claude_pet.CODEX_API_STATUS["last_error"], err)
                self.assertEqual(claude_pet.api_error_kind(err), kind)
                logged = " ".join(str(x) for a in dbg for x in a)
                self.assertNotIn(self.KEY, logged, "the admin key reached _dbg")

    def test_today_and_month_are_ordered_windows(self):
        today = _need(self, "fetch_codex_cost_today")
        month = _need(self, "fetch_codex_cost_month")
        starts = []
        with mock.patch.object(claude_pet, "fetch_codex_cost",
                               side_effect=lambda s: starts.append(s) or 0.0):
            today()
            month()
        self.assertEqual(len(starts), 2)
        now = _dt.now(_UTC)
        self.assertLessEqual(starts[1], starts[0])
        self.assertLessEqual(starts[0], now)
        self.assertLess(now - starts[0], _td(days=1, hours=1))
        self.assertLess(now - starts[1], _td(days=32))


if __name__ == "__main__":
    unittest.main()
