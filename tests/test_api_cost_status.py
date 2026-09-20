"""API 모드에서 실패를 실패라고 말한다 — 게이팅 테스트, 구현 전.

사용자 보고(2026-09-19): "api 활성화 상태일 때 표시 안되는 버그".

재현했다. `fetch_api_cost()` 가 **모든 예외를 삼키고 None 을 돌려주고**, `roam_summary`
는 그 None 을 `("status", "loading")` 로 옮긴다. 그래서 이 둘이 화면에서 구분되지
않는다:

    키 있고 아직 첫 조회가 안 끝남   → ('status', 'loading')
    키가 거부됐거나 조회가 실패함     → ('status', 'loading')   ← 같다

키를 잘못 넣은 사용자는 "loading…" 을 영원히 본다. 무엇이 잘못됐는지도, 자기가 할
일이 있는지도 알 수 없다.

**이것은 PR #9 이 Claude 쪽에서 고친 것과 같은 부류의 결함이다.** 거기서는 토큰이
거부됐는데 필이 `세션 ≈0%` 를 그렸다 — 실패를 무해해 보이는 상태로 위장한 것이다.
여기서는 "잠시만 기다리세요" 로 위장한다. 고치는 방향도 같다: **모르는 것과 실패한
것을 구분하고, 사용자가 할 수 있는 일이 있으면 그것을 말한다.**

그래서 계약도 그때 만든 구조를 그대로 따른다 — `OAUTH_STATUS["last_error"]` 와
`auth_error` 플래그가 하는 일을 `API_STATUS` 와 `api_error` 가 한다. 새 패턴을
발명하지 않는다.

**키는 어디에도 남기지 않는다.** CLAUDE.md 의 Privacy 절이 지배한다 — 로그에도,
예외 메시지에도, 상태 딕셔너리에도.
"""

import inspect
import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()


KEY = "sk-ant-admin-SECRET-VALUE"


def api_summary(cost_today=None, cost_month=None, has_key=True, api_error=False):
    return claude_pet.roam_summary("api", None, None, None, cost_today, has_key,
                                   cost_month, api_error=api_error)


class StatusRecordsTheFailureKindTests(unittest.TestCase):
    """왜 실패했는지 기록한다 — 사용자가 할 일이 다르기 때문이다."""

    def setUp(self):
        claude_pet.API_STATUS["last_error"] = None
        self._key = claude_pet.RUNTIME.get("admin_key", "")
        claude_pet.RUNTIME["admin_key"] = KEY
        self.addCleanup(lambda: claude_pet.RUNTIME.__setitem__("admin_key", self._key))

    def _fetch_raising(self, exc):
        with mock.patch.object(claude_pet.urllib.request, "urlopen", side_effect=exc):
            return claude_pet.fetch_api_cost_today()

    def test_a_rejected_key_is_recorded_as_such(self):
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
        self.assertIsNone(self._fetch_raising(err))
        self.assertEqual(claude_pet.API_STATUS["last_error"], "http:401")

    def test_a_forbidden_key_is_recorded_as_such(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        self._fetch_raising(err)
        self.assertEqual(claude_pet.API_STATUS["last_error"], "http:403")

    def test_a_transport_failure_is_not_confused_with_a_bad_key(self):
        """네트워크 문제는 사용자가 할 일이 없다 — 키 문제는 있다."""
        self._fetch_raising(urllib.error.URLError("boom"))
        self.assertEqual(claude_pet.API_STATUS["last_error"], "net")

    def test_an_unparseable_body_is_its_own_kind(self):
        class FakeResp:
            def read(self):
                return b"{ not json"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(claude_pet.urllib.request, "urlopen",
                               return_value=FakeResp()):
            claude_pet.fetch_api_cost_today()
        self.assertEqual(claude_pet.API_STATUS["last_error"], "parse")

    def test_success_clears_a_previous_failure(self):
        """일시적 장애 뒤에 경고가 눌러앉으면 그것도 거짓말이다."""
        claude_pet.API_STATUS["last_error"] = "net"

        class FakeResp:
            def read(self):
                return json.dumps({"data": [{"results": [{"amount": "1.50"}]}]}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(claude_pet.urllib.request, "urlopen",
                               return_value=FakeResp()):
            got = claude_pet.fetch_api_cost_today()
        self.assertEqual(got, 1.5)
        self.assertIsNone(claude_pet.API_STATUS["last_error"])

    def test_no_key_at_all_is_not_an_error_state(self):
        """키를 아직 안 넣은 것은 실패가 아니라 안내 대상이다."""
        claude_pet.RUNTIME["admin_key"] = ""
        claude_pet.API_STATUS["last_error"] = None
        self.assertIsNone(claude_pet.fetch_api_cost_today())
        self.assertIsNone(claude_pet.API_STATUS["last_error"])


class SummaryDistinguishesLoadingFromFailureTests(unittest.TestCase):
    """이 쌍이 버그의 핵심이다 — 정수 하나가 아니라 플래그 하나로 갈린다."""

    def test_loading_and_failure_are_different_states(self):
        loading = api_summary(cost_today=None, api_error=False)
        failed = api_summary(cost_today=None, api_error=True)
        self.assertEqual(loading, ("status", "loading"))
        self.assertNotEqual(failed, loading,
                            "키가 거부됐는데 '잠시만 기다리세요' 로 보인다 — 원래 버그다")
        self.assertEqual(failed[0], "status")

    def test_a_missing_key_still_wins_over_the_error_state(self):
        """키가 없으면 실패가 아니라 '키를 넣으세요' 가 맞는 안내다."""
        self.assertEqual(api_summary(has_key=False, api_error=True),
                         ("status", "need_admin_key"))

    def test_numbers_win_over_a_stale_error(self):
        """오늘 비용을 이미 받아 왔으면 그걸 보여 준다 — 지난 실패로 가리지 않는다."""
        kind, payload = api_summary(cost_today=1.23, cost_month=4.56, api_error=True)
        self.assertEqual(kind, "cost")
        self.assertEqual(payload[0], 1.23)

    def test_the_flag_defaults_to_false_so_existing_callers_are_unchanged(self):
        self.assertEqual(
            claude_pet.roam_summary("api", None, None, None, 1.0, True, 2.0),
            ("cost", (1.0, 2.0, None)))

    def test_the_failure_status_key_renders_in_every_locale(self):
        kind, key = api_summary(cost_today=None, api_error=True)
        for lang in ("en", "ko", "ja", "es"):
            with self.subTest(lang=lang):
                self.assertIsInstance(claude_pet.TR[lang].get(key), str,
                                      "%s 에 %s 없음" % (lang, key))
        en = claude_pet.TR["en"][key]
        same = [l for l in ("ko", "ja", "es") if claude_pet.TR[l].get(key) == en]
        self.assertEqual(same, [], "번역되지 않은 로케일: %s" % same)

    def test_the_message_tells_the_user_what_to_do(self):
        """'오류가 발생했습니다' 는 안내가 아니다 — 키를 고치라고 말해야 한다."""
        _, key = api_summary(cost_today=None, api_error=True)
        self.assertNotEqual(key, "loading")
        self.assertIn("key", claude_pet.TR["en"][key].lower())


class TransientFailureIsAlsoSaidOutLoudTests(unittest.TestCase):
    """5xx·망·본문 오류도 "조회 중…" 으로 위장하지 않는다.

    첫 라운드에서 경고는 401/403 에만 올렸다. 좁게 잡은 판단 자체는 옳았다 — 망
    장애에 "설정에서 키를 확인하세요" 를 띄우면 그것도 거짓 안내다. 하지만 그 결과
    5xx·망·파싱 실패가 여전히 "조회 중…" 으로 보이고, 사용자는 같은 자리에서 같은
    질문("왜 안 뜨지")을 하게 된다. 남은 절반이다.

    그래서 **두 번째 문구**를 둔다. 키를 고치라는 말과 섞이면 안 되므로 별도 키다.
    """

    def _summary(self, err):
        claude_pet.API_STATUS["last_error"] = err
        return claude_pet.roam_summary(
            "api", None, None, None, None, True, None,
            api_error=claude_pet.api_error_kind(err) == "key",
            api_stale=claude_pet.api_error_kind(err) == "transient")

    def test_the_three_transient_kinds_share_one_verdict(self):
        for err in ("http:500", "http:503", "net", "parse"):
            with self.subTest(err=err):
                self.assertEqual(claude_pet.api_error_kind(err), "transient")

    def test_a_rejected_key_is_not_transient(self):
        for err in ("http:401", "http:403"):
            with self.subTest(err=err):
                self.assertEqual(claude_pet.api_error_kind(err), "key")

    def test_no_error_is_neither(self):
        self.assertIsNone(claude_pet.api_error_kind(None))

    def test_a_transient_failure_is_not_shown_as_loading(self):
        kind, key = self._summary("net")
        self.assertEqual(kind, "status")
        self.assertNotEqual(key, "loading",
                            "망 장애가 '잠시만 기다리세요' 로 보인다")

    def test_it_is_also_not_shown_as_a_key_problem(self):
        """사용자가 멀쩡한 키를 의심하게 만들면 안 된다."""
        _, transient = self._summary("net")
        _, rejected = self._summary("http:401")
        self.assertNotEqual(transient, rejected)

    def test_the_transient_message_exists_in_every_locale_and_is_translated(self):
        _, key = self._summary("net")
        for lang in ("en", "ko", "ja", "es"):
            with self.subTest(lang=lang):
                self.assertIsInstance(claude_pet.TR[lang].get(key), str)
        en = claude_pet.TR["en"][key]
        self.assertEqual([l for l in ("ko", "ja", "es")
                          if claude_pet.TR[l].get(key) == en], [])

    def test_the_transient_message_does_not_blame_the_key(self):
        _, key = self._summary("net")
        self.assertNotIn("key", claude_pet.TR["en"][key].lower())

    def test_numbers_still_win_over_a_transient_failure(self):
        claude_pet.API_STATUS["last_error"] = "net"
        kind, payload = claude_pet.roam_summary(
            "api", None, None, None, 1.23, True, None, api_stale=True)
        self.assertEqual(kind, "cost")
        self.assertEqual(payload[0], 1.23)


class SettingsAreReachableFromTheMessageTests(unittest.TestCase):
    """"설정에서 확인하세요" 라고 써 놓고 클릭이 안 되면 안내가 아니다."""

    def act(self, status_key):
        return claude_pet.summary_click_action(
            status_key=status_key, in_pill=True, click_count=1, moved=False)

    def test_a_rejected_key_opens_settings(self):
        self.assertEqual(self.act("api_key_rejected"), "settings")

    def test_a_missing_key_opens_settings_too(self):
        """같은 말을 하는 문구인데 하나만 열리면 그게 더 헷갈린다."""
        self.assertEqual(self.act("need_admin_key"), "settings")

    def test_a_transient_failure_does_not_open_settings(self):
        """사용자가 할 일이 없는 상태다 — 설정을 열어 봐야 고칠 것이 없다."""
        _, key = claude_pet.roam_summary(
            "api", None, None, None, None, True, None, api_stale=True)
        self.assertIsNone(self.act(key))

    def test_the_existing_click_meanings_are_unchanged(self):
        self.assertEqual(self.act("onb_login"), "login")
        self.assertEqual(self.act("onb_install"), "install")
        self.assertEqual(self.act("token_expired"), "recover")
        self.assertIsNone(self.act("loading"))


class ApiKeyPrivacyTests(unittest.TestCase):
    """키는 어디에도 남지 않는다."""

    def test_the_key_is_not_written_into_the_status(self):
        claude_pet.RUNTIME["admin_key"] = KEY
        claude_pet.API_STATUS["last_error"] = None
        try:
            with mock.patch.object(claude_pet.urllib.request, "urlopen",
                                   side_effect=urllib.error.HTTPError(
                                       "u", 401, "no", {}, None)):
                claude_pet.fetch_api_cost_today()
            self.assertNotIn(KEY, repr(claude_pet.API_STATUS))
        finally:
            claude_pet.RUNTIME["admin_key"] = ""

    def test_the_debug_log_never_carries_the_key(self):
        seen = []
        claude_pet.RUNTIME["admin_key"] = KEY
        try:
            with mock.patch.object(claude_pet, "_dbg", lambda *a, **k: seen.append(a)), \
                 mock.patch.object(claude_pet.urllib.request, "urlopen",
                                   side_effect=urllib.error.URLError("boom")):
                claude_pet.fetch_api_cost_today()
            self.assertNotIn(KEY, repr(seen))
        finally:
            claude_pet.RUNTIME["admin_key"] = ""

    def test_the_fetcher_does_not_interpolate_the_key_into_any_message(self):
        src = inspect.getsource(claude_pet.fetch_api_cost)
        self.assertNotIn("admin_key}", src)
        self.assertNotIn("{key}", src)


if __name__ == "__main__":
    unittest.main()
