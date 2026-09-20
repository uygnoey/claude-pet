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
        main, _ = claude_pet.roam_summary_runs([claude_seg, codex_seg], claude_pet.t)
        joined = "".join(t for t, _ in main)
        self.assertIn(claude_pet.SUMMARY_SEP.strip() or "·", joined,
                      "두 제공자 사이에 구분자가 없다")
        self.assertIn("Codex", joined, "Codex 구간이 조립 결과에 없다")


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
