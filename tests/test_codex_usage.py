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
"""

import inspect
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()


def usage_payload(primary_pct=12.0, secondary_pct=34.0, **kw):
    """wham/usage 응답의 최소 형태. 필드 이름은 Orca/CodexBar 양쪽에서 확인한 것."""
    body = {
        "plan_type": "plus",
        "rate_limit": {
            "primary_window": {"used_percent": primary_pct,
                               "limit_window_seconds": 300 * 60,
                               "reset_at": 1789900000},
            "secondary_window": {"used_percent": secondary_pct,
                                 "limit_window_seconds": 7 * 24 * 3600,
                                 "reset_at": 1790400000},
        },
    }
    body.update(kw)
    return body


def auth_payload(access="ACCESS-TOKEN-VALUE", **kw):
    body = {"OPENAI_API_KEY": None,
            "tokens": {"id_token": "ID", "access_token": access,
                       "refresh_token": "REFRESH", "account_id": "acct_1"},
            "last_refresh": "2026-09-19T00:00:00Z"}
    body.update(kw)
    return body


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


class CodexUsageParseTests(unittest.TestCase):
    """primary→세션 / secondary→주간. 이 대응이 뒤집히면 숫자가 거짓말을 한다."""

    def rows(self, payload):
        return claude_pet.parse_codex_usage(payload)

    def test_primary_is_the_session_lane_and_secondary_is_weekly(self):
        rows = self.rows(usage_payload(primary_pct=12.0, secondary_pct=34.0))
        self.assertEqual(len(rows), 2)
        (l1, p1, _, _), (l2, p2, _, _) = rows[0], rows[1]
        self.assertEqual(p1, 12.0, "첫 행이 primary(세션)가 아니다")
        self.assertEqual(p2, 34.0, "둘째 행이 secondary(주간)가 아니다")

    def test_the_two_lanes_are_labelled_differently(self):
        rows = self.rows(usage_payload())
        self.assertNotEqual(rows[0][0], rows[1][0])

    def test_percentages_are_clamped_to_the_zero_hundred_range(self):
        rows = self.rows(usage_payload(primary_pct=140.0, secondary_pct=-5.0))
        self.assertEqual(rows[0][1], 100.0)
        self.assertEqual(rows[1][1], 0.0)

    def test_a_missing_rate_limit_yields_no_rows_rather_than_zeros(self):
        """0% 는 '안 썼다'로 읽힌다. 읽을 게 없으면 행을 그리지 않는다."""
        self.assertIsNone(self.rows({"plan_type": "plus"}))

    def test_a_non_numeric_percentage_is_dropped_not_coerced(self):
        bad = usage_payload()
        bad["rate_limit"]["primary_window"]["used_percent"] = "12"
        rows = self.rows(bad)
        self.assertTrue(rows is None or all(isinstance(r[1], float) for r in rows))
        if rows:
            self.assertEqual(len(rows), 1, "문자열을 숫자로 억지로 바꿨다")

    def test_a_window_without_a_percentage_is_dropped(self):
        bad = usage_payload()
        del bad["rate_limit"]["secondary_window"]["used_percent"]
        rows = self.rows(bad)
        self.assertEqual(len(rows or []), 1)

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
        claude_seg = ("status", "scanning")
        codex_seg = claude_pet.roam_summary_codex(usage_payload())
        main, _ = claude_pet.roam_summary_runs([claude_seg, codex_seg], claude_pet.t)
        joined = "".join(t for t, _ in main)
        self.assertIn(claude_pet.SUMMARY_SEP.strip() or "·", joined,
                      "두 제공자 사이에 구분자가 없다")


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


if __name__ == "__main__":
    unittest.main()
