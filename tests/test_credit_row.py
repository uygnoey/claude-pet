"""구독 + 크레딧 활성화 시 크레딧 사용량을 보여준다 — 게이팅, 구현 전.

사용자 보고(2026-09-20): 구독 모드에서 **크레딧을 활성화해 쓰고 있는데 표시가 안 된다**.

재현했다. 서버 응답에 `extra_usage.is_enabled` 가 참이고 `utilization` 이 있으면
`_parse_oauth_usage()` 는 크레딧 행을 제대로 만든다:

    {'extra_usage': {'is_enabled': True, 'utilization': 63.5}}
      → [('크레딧', 63.5, None, None)]      _label_order = 9

그런데 어댑터(`roam_summary_text`)가 `_label_order(label) >= 9` 인 행을 `continue`
로 **통째로 버린다.** 그래서 크레딧을 켜고 쓰는 사용자는 자기가 얼마나 썼는지 필에서
전혀 볼 수 없다. 파싱까지 다 해 놓고 마지막에 버리는 구조다.

왜 버리게 됐는지는 독스트링에 남아 있다 — 필은 "게이지 3행"(세션·주간·모델)을 위한
자리이고 크레딧은 게이지가 아니라는 것이다. 그 판단 자체는 필이 좁다는 제약에서
나왔지만, **크레딧 행은 켠 사람에게만 존재한다.** 즉 이 행이 보이는 사용자는 정확히
그것을 보고 싶어 켠 사람이다.

여기서 고정하는 것은 "크레딧이 있으면 보여준다" 하나다. 자리 배치·색은 기존 필
계약(`test_summary_pill`)이 이미 지키고 있으므로 건드리지 않는다.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()


def credit_label():
    return claude_pet.t("credit")


def rows(*, session=42.0, weekly=17.0, model=8.0, credit=None):
    """서버가 준 순서 그대로의 (label, pct, reset_dt, reset_text) 목록."""
    out = [(claude_pet.t("session"), session, None, "3h"),
           (claude_pet.t("weekly"), weekly, None, "2d"),
           ("Fable", model, None, "2d")]
    if credit is not None:
        out.append((credit_label(), credit, None, "30d"))
    return out


# 2026-09-20, 사용자 계정의 실제 응답에서 그대로 옮긴 모양. 한도를 넘긴 상태다.
# 이 픽스처가 이 파일의 핵심이다 — 합성으로 지어낸 값이 아니라 버그가 실제로
# 일어난 상태의 사본이다.
LIMIT_REACHED = {
    "is_enabled": False,                      # ← 한도를 넘겨서 조직이 꺼 버린 결과
    "monthly_limit": 10000,                   # = $100.00 (마이너 단위)
    "used_credits": 10066.0,                  # = $100.66 (마이너 단위)
    "utilization": 100.0,
    "currency": "USD",
    "decimal_places": 2,
    "disabled_reason": "org_level_disabled_until",
    "user_disabled": False,                   # ← 사용자는 켜 뒀다
    "spend_limit_reached": True,
    "credits_ever_enabled": True,
}

NEVER_ENABLED = {
    "is_enabled": False, "monthly_limit": None, "used_credits": None,
    "utilization": None, "currency": None, "decimal_places": None,
    "disabled_reason": None, "user_disabled": True,
    "spend_limit_reached": False, "credits_ever_enabled": False,
}


# 실측 금액($100.66/$100.00)을 그대로 쓰되 켜져 있는 상태.
ENABLED_LIMIT = dict(LIMIT_REACHED, is_enabled=True, user_disabled=False,
                     spend_limit_reached=False, disabled_reason=None)

ENABLED = dict(LIMIT_REACHED, is_enabled=True, used_credits=6350.0,
               utilization=63.5, spend_limit_reached=False, disabled_reason=None)


class CreditRowIsParsedTests(unittest.TestCase):
    """켜져 있을 때만 그린다 — 꺼져 있으면 행이 없다(사용자 결정, 2026-09-20).

    사용자가 보고한 버그는 **켜고 쓰는 동안 안 보이는 것**이었다. 그 원인은 파서가
    아니라 어댑터였다 — 파서는 행을 만드는데 `roam_summary_text` 가
    `_label_order(label) >= 9` 로 버렸다.

    꺼진 상태는 그리지 않는다. 이유는 묻지 않는다 — 사용자가 직접 껐든 한도를 다
    써서 조직이 껐든(`spend_limit_reached`), `is_enabled` 가 거짓이면 행이 없다.
    한도 소진 순간의 안내를 잃는다는 대가는 사용자가 알고 선택한 것이다.
    """

    def test_enabled_credits_become_a_row(self):
        got = claude_pet._parse_oauth_usage({"extra_usage": ENABLED})
        self.assertTrue(got)
        self.assertIn(credit_label(), [r[0] for r in got])

    def test_a_limit_reached_account_has_no_row(self):
        """한도를 다 써서 꺼진 것도 '꺼짐' 이다."""
        self.assertIsNone(claude_pet._parse_oauth_usage(
            {"extra_usage": LIMIT_REACHED}))

    def test_a_user_who_never_enabled_credits_gets_no_row(self):
        self.assertIsNone(claude_pet._parse_oauth_usage(
            {"extra_usage": NEVER_ENABLED}))

    def test_a_user_who_turned_it_off_themselves_gets_no_row(self):
        off = dict(ENABLED, is_enabled=False, user_disabled=True)
        self.assertIsNone(claude_pet._parse_oauth_usage({"extra_usage": off}))

    def test_enabled_but_no_numbers_means_no_row(self):
        """켜져 있어도 쓸 숫자가 없으면 0% 를 지어내지 않는다."""
        blank = dict(ENABLED, used_credits=None, utilization=None)
        self.assertIsNone(claude_pet._parse_oauth_usage({"extra_usage": blank}))


class CreditAmountIsMoneyTests(unittest.TestCase):
    """단위는 **마이너 단위**다 — 감으로 정하면 100배 틀린다.

    실측으로 확정했다: 같은 응답의 `spend.used.amount_minor` 가 10066 이고
    `exponent` 가 2 인데, `extra_usage.used_credits` 도 10066.0 이다. 즉 같은 값을
    같은 단위로 말하고 있고, `decimal_places: 2` 가 그 지수다. $100.66 이지
    $10,066 이 아니다.
    """

    def facts(self):
        return claude_pet.credit_facts(ENABLED_LIMIT)

    def test_used_is_converted_from_minor_units(self):
        self.assertAlmostEqual(self.facts()["used"], 100.66, places=2)

    def test_limit_is_converted_too(self):
        self.assertAlmostEqual(self.facts()["limit"], 100.00, places=2)

    def test_the_currency_comes_from_the_server_not_a_hardcoded_dollar(self):
        self.assertEqual(self.facts()["currency"], "USD")
        eur = claude_pet.credit_facts(dict(ENABLED_LIMIT, currency="EUR"))
        self.assertEqual(eur["currency"], "EUR")

    def test_decimal_places_come_from_the_server(self):
        """`decimal_places` 가 2 가 아닌 통화가 있다(JPY 는 0)."""
        jpy = claude_pet.credit_facts(
            dict(ENABLED_LIMIT, currency="JPY", decimal_places=0,
                 used_credits=1500, monthly_limit=2000))
        self.assertAlmostEqual(jpy["used"], 1500.0, places=2)
        self.assertAlmostEqual(jpy["limit"], 2000.0, places=2)

    def test_a_missing_decimal_places_does_not_silently_become_dollars(self):
        """지수를 모르면 금액을 지어내지 않는다 — 100배 틀릴 자리다."""
        unknown = dict(ENABLED_LIMIT, decimal_places=None)
        self.assertIsNone(claude_pet.credit_facts(unknown)["used"])

    def test_the_percentage_is_still_available(self):
        self.assertAlmostEqual(self.facts()["pct"], 100.0, places=2)


class CreditDisplayModeTests(unittest.TestCase):
    """%/$ 토글. 기본은 $ (사용자 결정, 2026-09-20)."""

    def test_the_setting_exists_and_defaults_to_money(self):
        self.assertIn("credit_display", claude_pet.RUNTIME)
        self.assertEqual(claude_pet.RUNTIME["credit_display"], "money")

    def test_the_key_is_settings_owned(self):
        self.assertIn("credit_display", claude_pet.SETTINGS_OWNED_KEYS)

    def test_money_mode_shows_an_amount_not_a_percentage(self):
        text = claude_pet.credit_row_text(ENABLED_LIMIT, "money")
        self.assertIn("100.66", text)
        self.assertNotIn("%", text)

    def test_percent_mode_shows_a_percentage(self):
        text = claude_pet.credit_row_text(ENABLED_LIMIT, "pct")
        self.assertIn("%", text)

    def test_money_mode_falls_back_to_percent_when_the_amount_is_unknown(self):
        """지수를 모를 때 금액 대신 빈칸을 보여주느니 아는 사실을 보여준다."""
        unknown = dict(ENABLED_LIMIT, decimal_places=None)
        self.assertIn("%", claude_pet.credit_row_text(unknown, "money"))


class CreditRowSurvivesToTheSummaryTests(unittest.TestCase):
    """버그의 핵심 — 파싱된 행이 필까지 살아서 가야 한다."""

    def test_the_credit_row_is_not_dropped(self):
        kind, payload = claude_pet.roam_summary(
            "sub", rows(credit=63.5), None, None, None, False, None)
        self.assertEqual(kind, "exact")
        labels = [r[0] for r in payload]
        self.assertIn(credit_label(), labels,
                      "크레딧을 켜고 쓰는 사용자가 자기 사용량을 볼 수 없다")

    def test_the_three_gauges_are_still_there_with_it(self):
        """크레딧이 게이지 한 줄을 밀어내면 그것도 회귀다."""
        _, payload = claude_pet.roam_summary(
            "sub", rows(credit=63.5), None, None, None, False, None)
        labels = [r[0] for r in payload]
        for gauge in (claude_pet.t("session"), claude_pet.t("weekly"), "Fable"):
            self.assertIn(gauge, labels, "%s 게이지가 사라졌다" % gauge)

    def test_no_credit_row_when_it_is_not_enabled(self):
        _, payload = claude_pet.roam_summary(
            "sub", rows(), None, None, None, False, None)
        self.assertNotIn(credit_label(), [r[0] for r in payload])

    def test_the_credit_percentage_is_carried_through_unchanged(self):
        _, payload = claude_pet.roam_summary(
            "sub", rows(credit=63.5), None, None, None, False, None)
        credit = [r for r in payload if r[0] == credit_label()][0]
        self.assertEqual(credit[1], 63.5)

    def test_an_invalid_credit_percentage_drops_only_that_row(self):
        bad = rows(credit=float("nan"))
        _, payload = claude_pet.roam_summary(
            "sub", bad, None, None, None, False, None)
        labels = [r[0] for r in payload]
        self.assertNotIn(credit_label(), labels)
        self.assertIn(claude_pet.t("session"), labels, "멀쩡한 게이지까지 잃었다")

    def test_the_spike_mark_still_belongs_to_the_session_row_only(self):
        """행이 하나 늘었다고 스파이크 표시가 옮겨 다니면 안 된다."""
        _, payload = claude_pet.roam_summary(
            "sub", rows(credit=63.5), None, None, None, False, None,
            spike_first=True)
        self.assertTrue(payload[0][2], "첫 행(세션)에 스파이크 표시가 없다")
        self.assertEqual([r[2] for r in payload[1:]], [False] * (len(payload) - 1))


class LegacyResponseKeepsItsGaugesTests(unittest.TestCase):
    """크레딧이 레거시 폴백을 가로채면 게이지가 통째로 사라진다.

    Developer 가 구현 중에 발견해 보고했고(고치지는 않았다 — 계약에도 게이팅
    테스트에도 없었으므로 옳은 처신이다), 여기서 계약으로 만든다.

    `_parse_oauth_usage()` 는 이 순서다:

        found = _rows_from_limits(data)
        ...크레딧을 found 에 append...
        if not found:                 # ← 크레딧이 들어갔으면 이 폴백이 영영 안 돈다
            found = _rows_from_utilization(data)

    그래서 **`limits` 배열이 없는 구버전 응답 + 크레딧 활성** 이면 게이지 3행이
    사라지고 크레딧만 남는다. 지금 서버 응답에는 `limits` 와 레거시 필드가 둘 다
    있어 이 경로에 닿지 않지만, 레거시 폴백이 존재하는 한 그것은 "아직 안 터졌다"
    이지 "안 터진다" 가 아니다. CLAUDE.md 가 이 파일 전반에서 요구하는 태도다.
    """

    LEGACY = {"five_hour": {"utilization": 42},
              "seven_day": {"utilization": 17},
              "seven_day_opus": {"utilization": 8}}

    def test_legacy_gauges_survive_when_credits_are_present(self):
        payload = dict(self.LEGACY, extra_usage=ENABLED_LIMIT)
        labels = [r[0] for r in (claude_pet._parse_oauth_usage(payload) or [])]
        self.assertIn(claude_pet.t("session"), labels,
                      "크레딧이 레거시 게이지를 밀어냈다")
        self.assertIn(claude_pet.t("weekly"), labels)

    def test_the_credit_row_is_there_too(self):
        payload = dict(self.LEGACY, extra_usage=ENABLED_LIMIT)
        labels = [r[0] for r in (claude_pet._parse_oauth_usage(payload) or [])]
        self.assertIn(credit_label(), labels)

    def test_the_legacy_path_is_unchanged_without_credits(self):
        """대조군 — 크레딧이 없을 때의 동작은 건드리지 않는다."""
        labels = [r[0] for r in (claude_pet._parse_oauth_usage(self.LEGACY) or [])]
        self.assertIn(claude_pet.t("session"), labels)
        self.assertNotIn(credit_label(), labels)


class MoneyReachesThePillTests(unittest.TestCase):
    """기본값이 `money` 면 **필에 금액이 보여야** 한다.

    Developer 가 정직하게 플래그한 지점이다: `credit_row_text` 는 만들었지만
    렌더러에 연결하지 않아, `credit_display` 가 `"money"` 인데도 필은 여전히
    `크레딧 100%` 를 그렸다. 계약 없이 핀 박힌 렌더러를 건드리지 않은 것은 옳은
    처신이었고, 그 계약이 여기다.

    `_summary_segment_runs` 는 모든 행을 `f" {approx}{pct:.0f}%"` 로 찍는다. 그래서
    **행이 자기 표시 문자열을 들고 올 수 있어야 한다** — 다섯 번째 원소가 있으면
    렌더러는 `%` 를 만들지 않고 그 문자열을 그대로 쓴다. 게이지 행은 4-튜플 그대로이고
    (기존 계약이 정확한 튜플을 핀으로 박고 있다), 크레딧 행만 5번째를 채운다.
    """

    def credit_run(self, mode="money", extra=None):
        rows_ = rows()
        facts = extra if extra is not None else ENABLED_LIMIT
        rows_.append((credit_label(), facts["utilization"], False, None,
                      claude_pet.credit_row_text(facts, mode)))
        main, _ = claude_pet.roam_summary_runs([("exact", rows_)], claude_pet.t)
        return "".join(t for t, _ in main)

    def test_a_row_carrying_its_own_text_is_rendered_verbatim(self):
        line = self.credit_run("money")
        self.assertIn("100.66", line, "필에 금액이 없다")

    def test_that_row_does_not_also_get_a_percentage(self):
        line = self.credit_run("money")
        self.assertNotIn("100%", line, "금액과 퍼센트가 같이 찍혔다")

    def test_percent_mode_still_renders_a_percentage(self):
        self.assertIn("%", self.credit_run("pct"))

    def test_gauge_rows_are_untouched_by_this(self):
        """4-튜플 게이지 행의 표시는 조금도 달라지지 않는다."""
        line = self.credit_run("money")
        for gauge_pct in ("42%", "17%", "8%"):
            self.assertIn(gauge_pct, line, "게이지 표시가 바뀌었다: %s" % gauge_pct)

    def test_a_four_tuple_row_still_works(self):
        """5번째 원소가 없는 행은 예전과 똑같이 % 로 찍힌다."""
        main, _ = claude_pet.roam_summary_runs([("exact", rows())], claude_pet.t)
        self.assertIn("42%", "".join(t for t, _ in main))


class CreditRowRendersTests(unittest.TestCase):
    """렌더러가 이미 이해하는 모양이어야 한다 — 그리기 코드는 손대지 않는다."""

    def test_it_becomes_runs_the_renderer_can_colour(self):
        seg = claude_pet.roam_summary(
            "sub", rows(credit=63.5), None, None, None, False, None)
        main, _sub = claude_pet.roam_summary_runs([seg], claude_pet.t)
        joined = "".join(t for t, _ in main)
        self.assertIn(credit_label(), joined)
        for _text, kind in main:
            self.assertIn(kind, claude_pet.SUMMARY_COLORS)


if __name__ == "__main__":
    unittest.main()
