"""제공자별 줄 묶음 레이아웃 게이트 — Verifier 작성, **구현 전**.

이 파일은 아직 없는 동작을 고정한다. 작성 시점에 전부 빨강이어야 하고, 그 빨강을 먼저
관찰한 기록이 AGENTS.md §3 의 요구다.

── 왜 이 게이트가 생겼는지 ────────────────────────────────────────────────────

v0.26 의 Codex 행이 화면에 닿지 않았다. 조립은 정확했고 색도 정확했는데 필이 고정폭
스트립이라 `roam_fit_runs` 가 뒤에서부터 잘라 냈고, Codex 구간은 언제나 맨 뒤였다.
그걸 잡는 폭 게이트는 tests/test_summary_pill.py 의 CodexRowFitsThePillTests 다.

그 다음에 더 심각한 것이 나왔다 — 라벨이 **틀려** 있었다(창 길이가 7일인데 "세션"이라고
불렀다; tests/test_summary_usage.py… 아니라 tests/test_codex_usage.py 의
CodexUsageParseTests 가 그걸 지킨다). 두 사고의 교훈이 이 파일의 설계를 정한다:

  · 잘린 행은 **잘린 게 보인다**. 잘못 붙은 라벨은 **맞아 보인다**. 그래서 화면에
    도달하는 것과 라벨이 참인 것을 각각 따로 게이트한다.
  · 손으로 만든 픽스처는 **우리가 가정한 모양을 재생산한다**. 그래서 여기서는 행 수도
    제공자 수도 **매개변수**다 — "오늘은 Codex 가 1행"이라는 오늘의 사실을 고정하면,
    Codex 가 5시간 세션 창을 되살리는 날 이 파일이 거짓이 된다(사용자 지적:
    "코덱스도 원래 5시간 세션 한도 있었어! 그러니 언제 다시 생길지 모름").

── 계약 (Coordinator 확정, 2026-09-20) ────────────────────────────────────────

  summary_lines(groups, measure, budget) -> [(provider_id, [line_runs, ...]), ...]

순수 함수다. 창도 RUNTIME 도 datetime.now() 도 보지 않는다. **접힘은 이 함수 안에서
일어나고 호출자는 절대 trim 하지 않는다** — 호출자가 `roam_fit_runs` 를 부르던 구조가
잘림의 원인이었다.

로고는 run 이 아니다. `(text, kind)` run 목록에 이미지가 들어가면 렌더러와 모든 measure
가 그걸 알아야 한다. 대신 제공자 블록 전체를 `SUMMARY_LOGO_W` 만큼 들여쓰고, 그 제공자의
**모든 줄**의 텍스트 예산이 `budget - SUMMARY_LOGO_W` 가 된다. 접혀서 생긴 이어지는 줄도
같은 들여쓰기라 정렬이 맞는다.

높이는 줄 수의 함수다. `SUMMARY_H`/`SUMMARY_H2` 가 "두 경우가 진실"로 되살아나면 3줄이
2줄 높이로 그려지고, 그건 사용자에게 잘린 것으로 보인다.

── 폭 측정 ────────────────────────────────────────────────────────────────────

measure 는 주입받는다. 실제 폰트 측정은 macOS 에서만 되고 CI 는 macOS+Windows 라,
tests/test_summary_pill.py 가 실제 번들 폰트에서 뽑아 둔 문자 advance 표를 그대로 쓴다.
**복제하지 않고 import 한다** — 표가 두 벌이 되면 갈라지고, 갈라진 순간 어느 쪽이 맞는지
아무도 모른다. 그 파일의 macOS 전용 동행 테스트가 표가 실제 폰트와 어긋나면 실패시킨다.

테스트 정책(CLAUDE.md): 실제 `~/.claude`·`~/.codex` 를 읽지 않는다. 픽스처는 전부 합성
이거나, 기록된 `rate_limit` 블록뿐이다(식별자 없음 — tests/test_codex_usage.py 참조).
"""

import ast
import math
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import claude_pet  # noqa: E402

# 문자 advance 표는 한 벌만 존재한다. 두 벌이 되면 갈라진다.
from test_summary_pill import pretendard_width  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ELLIPSIS = "…"


# ── 계약 접근자 ────────────────────────────────────────────────────────────────
# 생산 쪽 이름이 바뀌면 여기 한 줄만 고친다. 단언은 전부 성질로 되어 있어서 이름 변경이
# 테스트 재작성이 되지 않는다.

def _require(name):
    value = getattr(claude_pet, name, None)
    if value is None:
        raise AssertionError(
            f"claude_pet.{name} 가 없다 — 제공자별 줄 묶음 계약이 아직 구현되지 않았다. "
            "이 파일은 구현 전에 쓰였고 지금 빨간 것이 정상이다.")
    return value


# 최소 지원 화면(CLAUDE.md: 1366×768). 예산은 **여기서** 유도한다.
#
# 2026-09-20 정정: 이 파일은 원래 예산을 `PILL_W - 2*PILL_PAD` 로 유도했다. 그때는 그게
# 필의 상한이었기 때문이지만, 사용자가 지적한 대로 `PILL_W = 300` 은 근거 없는 상수였고
# 그 상한 자체가 내용이 잘리던 유일한 원인이었다. 상한이 화면으로 바뀐 지금 `PILL_W` 는
# 설정 패널 폭 계산에만 남아 있다 — 즉 예전 유도는 이제 **무관한 상수**를 가리킨다.
# 상수에서 유도하는 것과 올바른 것에서 유도하는 것은 다르고, 전자는 조용히 틀린다.
MIN_SUPPORTED_SCREEN = 1366


def layout(groups, measure=pretendard_width, budget=None):
    fn = _require("summary_lines")
    if budget is None:
        budget = full_budget()
    return fn(groups, measure, budget)


def logo_width():
    w = _require("SUMMARY_LOGO_W")
    return float(w)


def full_budget():
    """필 안쪽의 전체 가로 예산 — 화면에서 유도한다.

    `roam_pill_rect` 가 쓰는 것과 같은 식이다: 논리 창 폭에서 양쪽 가장자리 여백
    (`SUMMARY_EDGE`)을 빼면 필이 커질 수 있는 최대 폭이고, 거기서 필 내부 패딩을 빼면
    글자가 쓸 수 있는 폭이다. 최소 지원 화면을 쓰는 이유는 그것이 최악의 경우이고,
    게이트는 최악의 경우에서 참이어야 하기 때문이다.
    """
    room = max(claude_pet.SUMMARY_MIN_W,
               MIN_SUPPORTED_SCREEN - 2 * claude_pet.SUMMARY_EDGE)
    return room - 2 * claude_pet.PILL_PAD


def text_budget():
    """한 제공자의 한 줄이 쓸 수 있는 **텍스트** 폭. 로고 자리는 이미 빠져 있다."""
    return full_budget() - logo_width()


# ── 픽스처: 제공자 묶음. 행 수도 제공자 수도 매개변수다 ────────────────────────

SESSION_WINDOW_SEC = 5 * 3600
WEEKLY_WINDOW_SEC = 7 * 24 * 3600

CLAUDE_GAUGES = {
    "ko": [("세션", 42.0, "3시간 43분"), ("주간", 17.0, "2일 4시간"),
           ("Fable", 12.0, "2일 4시간")],
    "en": [("Session", 42.0, "3h 43m"), ("Weekly", 17.0, "2d 4h"),
           ("Fable", 12.0, "2d 4h")],
}
CLAUDE_CREDIT = {"ko": ("크레딧", 66.0, "9월 30일"), "en": ("Credit", 66.0, "Sep 30")}

# Codex 행 수는 계정마다 다르고 시간에 따라 변한다. 1행은 2026-09-20 에 관측된 모양,
# 2행은 Codex 가 5시간 세션 창을 되살렸을 때의 모양이다. **둘 다 지킨다.**
CODEX_ROWS = {
    1: [("codex_weekly", 68.0, None, "5일 21시간 후")],
    2: [("codex_session", 12.0, None, "3시간"),
        ("codex_weekly", 68.0, None, "5일 21시간 후")],
}


def claude_group(lang, credit=False):
    rows = list(CLAUDE_GAUGES[lang])
    kw = {}
    if credit:
        rows = rows + [CLAUDE_CREDIT[lang]]
        kw["credit_text"] = "$100.66"
    segment = claude_pet.roam_summary("subscription", rows, None, None, None,
                                      False, None, **kw)
    return ("claude", [segment])


def codex_group(rows):
    segment = claude_pet.roam_summary_codex(CODEX_ROWS[rows])
    assert segment is not None, "픽스처가 Codex 구간을 만들지 못했다"
    return ("codex", [segment])


def groups_for(lang, claude=True, codex=0, credit=False):
    out = []
    if claude:
        out.append(claude_group(lang, credit=credit))
    if codex:
        out.append(codex_group(codex))
    return out


def unfolded_runs(segments):
    """접기 전 이 제공자의 모든 run — 첫 줄과 리셋 줄을 이어 붙인 것."""
    main, sub = claude_pet.roam_summary_runs(segments, claude_pet.t)
    return list(main) + list(sub)


def content_runs(runs):
    """구분자를 뺀 run — 접힘은 줄 경계의 구분자를 지워도 되지만 내용은 못 지운다."""
    return [(t, k) for t, k in runs if t != claude_pet.SUMMARY_SEP]


def all_lines(result):
    return [line for _pid, lines in result for line in lines]


class LangMixin:
    def setUp(self):
        self.addCleanup(claude_pet.set_lang, claude_pet.L.get("lang"))

    def use(self, lang):
        claude_pet.set_lang(lang)


COMBINATIONS = [
    # (이름, claude?, codex 행수)
    ("claude only", True, 0),
    ("codex only", False, 1),
    ("codex only, two rows", False, 2),
    ("both", True, 1),
    ("both, codex two rows", True, 2),
    ("neither", False, 0),
]


class NothingIsEverTruncatedTests(LangMixin, unittest.TestCase):
    """어떤 조합에서도 어떤 행도 잘리지 않는다 — 넘치면 접혀서 전부 보인다.

    단언은 **내용 run 이 전부, 순서대로, 글자 그대로 살아남는가**다. "구간이 결과
    어딘가에 있다"로는 안 된다 — 그게 Codex 행이 화면에서 반토막 나 있는 동안 초록이던
    단언이다. 구분자는 줄 경계에서 사라져도 되지만(접힘은 줄을 나누는 일이다) 라벨과
    수치는 한 글자도 못 잃는다.

    Rivals: 접는 대신 자르는 구현(오늘의 동작); 마지막 줄만 접고 나머지는 자르는 구현;
    말줄임표를 붙여 '보이긴 한다'고 주장하는 구현; 제공자 하나만 접고 다른 하나는 자르는
    구현.
    """

    def assert_nothing_lost(self, lang, claude, codex, credit=False):
        self.use(lang)
        groups = groups_for(lang, claude=claude, codex=codex, credit=credit)
        result = layout(groups)
        by_provider = {pid: lines for pid, lines in result}
        for pid, segments in groups:
            with self.subTest(provider=pid):
                self.assertIn(pid, by_provider, f"{pid} 제공자의 줄이 통째로 사라졌다")
                produced = [r for line in by_provider[pid] for r in line]
                self.assertEqual(
                    content_runs(produced), content_runs(unfolded_runs(segments)),
                    f"{pid} 의 내용 run 이 접힘에서 사라지거나 바뀌었다 "
                    f"(lang={lang}, codex_rows={codex}, credit={credit})")

    def assert_no_ellipsis(self, lang, claude, codex, credit=False):
        self.use(lang)
        groups = groups_for(lang, claude=claude, codex=codex, credit=credit)
        source = "".join(t for _pid, segs in groups for t, _k in unfolded_runs(segs))
        for line in all_lines(layout(groups)):
            for text, _kind in line:
                if ELLIPSIS in text and ELLIPSIS not in source:
                    self.fail(f"말줄임표가 생겼다 — 접힌 것이 아니라 잘렸다: {text!r}")

    def test_no_content_is_lost_in_any_provider_combination(self):
        for name, claude, codex in COMBINATIONS:
            for lang in ("ko", "en"):
                with self.subTest(combination=name, lang=lang):
                    self.assert_nothing_lost(lang, claude, codex)

    def test_no_content_is_lost_with_the_credit_row_present(self):
        for name, claude, codex in COMBINATIONS:
            if not claude:
                continue
            for lang in ("ko", "en"):
                with self.subTest(combination=name, lang=lang):
                    self.assert_nothing_lost(lang, claude, codex, credit=True)

    def test_folding_never_ellipsises(self):
        for name, claude, codex in COMBINATIONS:
            for lang in ("ko", "en"):
                for credit in (False, True):
                    if credit and not claude:
                        continue
                    with self.subTest(combination=name, lang=lang, credit=credit):
                        self.assert_no_ellipsis(lang, claude, codex, credit=credit)

    def test_the_english_claude_line_with_credit_now_fits_on_one_line(self):
        """이 테스트는 **뒤집혔다**, 그리고 그게 기록할 가치가 있다.

        원래는 "영어 4게이지+크레딧 줄이 예산을 넘으니 접혀야 한다"였다. 그 전제가
        예산 274pt(= `PILL_W 300 - 2*PILL_PAD`)였고, 사용자가 그 274 의 근거를 물은
        순간 전제가 사라졌다 — 상한이 화면이 되자 같은 줄이 최소 지원 화면에서도 여유
        있게 들어간다. 잘리던 것은 줄이 길어서가 아니라 상한이 임의였기 때문이다.

        그래서 이제 요구사항의 **긍정형**을 단언한다: 이 줄은 접히지도 잘리지도 않고 한
        줄로 그려진다. 접힘 자체는 사라지지 않았고 아래 테스트가 계속 지킨다.

        Rival: 상한을 조금만 키운 수정 — 이 줄은 통과하지만 더 긴 조합에서 같은 자리로
        돌아온다. 그래서 여유를 함께 단언한다.
        """
        self.use("en")
        groups = groups_for("en", claude=True, codex=0, credit=True)
        one_line = sum(pretendard_width(t) for t, _k in
                       claude_pet.roam_summary_runs(groups[0][1], claude_pet.t)[0])
        self.assertLess(
            one_line, text_budget(),
            f"영어 크레딧 줄이 {one_line:.0f}pt 인데 예산이 {text_budget():.0f}pt 다 — "
            "최소 지원 화면에서 이미 배포되는 조합이 들어가지 않는다")
        lines = dict(layout(groups))["claude"]
        gauges = [ln for ln in lines if any(k != "sub" for _t, k in ln)]
        self.assertEqual(len(gauges), 1,
                         f"들어가는 줄이 접혔다 — 접힘은 넘칠 때만 일어나야 한다: {gauges!r}")
        self.assert_nothing_lost("en", True, 0, credit=True)

    def test_folding_still_fires_when_a_line_genuinely_exceeds_the_budget(self):
        """접힘은 이제 **현실에서 거의 발화하지 않는 안전장치**다. 그래서 더 중요하다.

        상한이 화면이 된 뒤 실제 내용은 예산의 4분의 1도 못 채운다. 그러면 접힘 코드는
        한 번도 돌지 않게 되고, 한 번도 돌지 않는 코드는 조용히 썩는다 — 제공자가 더
        늘거나 서버가 비정상적으로 긴 라벨을 주는 날 처음 돌면서 틀린다. 실제 입력으로는
        더 이상 발화시킬 수 없으므로 **합성 입력으로 발화시킨다.**

        Rivals: 접힘을 지워 버리는 수정('이제 안 넘치니까'); 예산을 무시하고 한 줄에
        밀어 넣는 구현; 접는 대신 자르는 구현.
        """
        self.use("ko")
        # 여러 run 으로 만든다. 접힘은 **run 경계**에서 일어나므로, run 하나가 예산보다
        # 긴 경우는 접어서 해결할 수 있는 문제가 아니다(그 한계는 별도로 보고했다).
        # 실제 내용도 항상 여러 run 이라 이쪽이 현실적인 모양이기도 하다.
        rows = [("게이지%02d" % i, 50.0, False, None) for i in range(40)]
        groups = [("claude", [("exact", rows)])]
        runs = claude_pet.roam_summary_runs(groups[0][1], claude_pet.t)[0]
        self.assertGreater(sum(pretendard_width(t) for t, _k in runs), text_budget(),
                           "합성 픽스처가 예산을 넘지 않는다 — 접힘을 발화시키지 못한다")
        lines = dict(layout(groups))["claude"]
        self.assertGreater(len(lines), 1, "예산을 넘는 줄이 접히지 않았다")
        for line in lines:
            self.assertLessEqual(sum(pretendard_width(t) for t, _k in line),
                                 text_budget() + 0.5)
        produced = [r for line in lines for r in line]
        self.assertEqual(content_runs(produced), content_runs(runs),
                         "접히면서 내용이 사라졌다")


class EveryLineFitsTests(LangMixin, unittest.TestCase):
    """생산된 모든 줄이 예산 안에 있다. 이것이 '접혔다'의 조작적 정의다."""

    def test_every_produced_line_fits_the_text_budget(self):
        for name, claude, codex in COMBINATIONS:
            for lang in ("ko", "en"):
                for credit in (False, True):
                    if credit and not claude:
                        continue
                    with self.subTest(combination=name, lang=lang, credit=credit):
                        self.use(lang)
                        groups = groups_for(lang, claude=claude, codex=codex, credit=credit)
                        for line in all_lines(layout(groups)):
                            width = sum(pretendard_width(t) for t, _k in line)
                            self.assertLessEqual(
                                width, text_budget() + 0.5,
                                f"줄이 예산을 넘는다: {width:.1f}pt > {text_budget():.1f}pt "
                                f"({''.join(t for t, _k in line)!r})")


class LogoWidthIsSubtractedTests(LangMixin, unittest.TestCase):
    """로고는 run 이 아니라 **들여쓰기**다 — 그래서 예산에서 미리 빠져야 한다.

    이 구조에서 '로고가 0폭 run 으로 들어가 모든 줄을 넓어 보이게 하는' 실패는 생기지
    않는다. 대응하는 실패 모드는 **로고 폭이 0 이거나, 선언만 되고 예산에서 빠지지 않는
    것**이고, 그러면 모든 줄이 로고 폭만큼 넘치게 그려진다. 그 둘을 여기서 잡는다.

    숫자는 적지 않는다. `SUMMARY_LOGO_W` 를 생산 쪽에서 읽어 온다 — 그래야 Developer 가
    고른 실제 값을 재고, 어림값이 테스트에 화석이 되지 않는다.
    """

    def test_the_logo_reserves_a_real_width(self):
        self.assertGreater(logo_width(), 0.0,
                           "로고 폭이 0 이면 로고 자리가 예산에서 빠지지 않는다")
        self.assertLess(logo_width(), full_budget(),
                        "로고가 필 전체를 먹었다")

    def test_a_line_that_only_fits_without_the_logo_is_folded(self):
        """판별 테스트: 예산과 '예산 − 로고' **사이**의 폭을 가진 줄을 만든다.

        로고 폭이 실제로 빠졌다면 접혀서 두 줄이 된다. 선언만 되고 안 빠졌다면 한 줄로
        남고, 그 줄은 화면에서 로고와 겹치거나 잘린다.

        Rival: `SUMMARY_LOGO_W` 가 존재하고 `test_the_logo_reserves_a_real_width` 도
        통과하지만 접기 계산이 full budget 을 쓰는 구현 — 그 구현은 이 테스트만 틀린다.
        """
        # 재야 하는 것은 라벨 폭이 아니라 **줄 전체 폭**이다. 이 구간은
        # exact 행 하나를 (라벨 run, 값 run) 두 개로 렌더하므로, 라벨만 두 예산 사이에
        # 맞추면 값 run 이 더해져 줄이 두 예산을 모두 넘어가 버리고 — 그러면 로고를 빼든
        # 안 빼든 접히므로 이 테스트가 아무것도 판별하지 못한다. 실제로 그렇게 쓰여 있었고,
        # 상한이 화면으로 바뀌면서 M3(로고 폭을 안 빼는 변이)가 통과해 버리는 것으로
        # 드러났다. 값 run 을 먼저 빼고 라벨을 맞춘다.
        forced_row = (("exact", [("", 50.0, False, None)]),)
        value_w = sum(pretendard_width(t) for t, _k
                      in claude_pet.roam_summary_runs(list(forced_row), claude_pet.t)[0])
        target = (full_budget() + text_budget()) / 2.0 - value_w
        filler = "0"
        unit = pretendard_width(filler)
        self.assertGreater(unit, 0)
        text = filler * int(target // unit)

        forced = [("claude", [("exact", [(text, 50.0, False, None)])])]
        width = sum(pretendard_width(t) for t, _k
                    in claude_pet.roam_summary_runs(forced[0][1], claude_pet.t)[0])
        self.assertLess(text_budget(), width,
                        f"픽스처 줄({width:.1f}pt)이 텍스트 예산({text_budget():.1f}pt)을 넘지 않는다")
        self.assertLessEqual(width, full_budget(),
                             f"픽스처 줄({width:.1f}pt)이 전체 예산({full_budget():.1f}pt)도 넘는다 "
                             "— 로고를 빼든 안 빼든 접히므로 판별력이 없다")

        lines = dict(layout(forced))["claude"]
        self.assertGreater(
            len(lines), 1,
            f"폭 {width:.1f}pt 짜리 줄이 접히지 않았다 — 텍스트 예산 {text_budget():.1f}pt "
            f"(전체 {full_budget():.1f}pt − 로고 {logo_width():.1f}pt)를 쓰지 않았다는 뜻이다")


class AbsentProviderLeavesNoTraceTests(LangMixin, unittest.TestCase):
    """없는 제공자는 줄도, 로고도, 구분자도 남기지 않는다.

    사용자 지시: "코덱스가 없으면 클로드만, 클로드가 없고 코덱스만 있으면 코덱스만".
    **폭 단언으로는 안 잡힌다** — 빈 줄도, 떠 있는 구분자만 있는 줄도, 로고만 있는 줄도
    폭 예산 안에 들어가므로 전부 통과한다. 그래서 따로 단언한다.

    Rivals: 제공자 자리를 항상 만들어 두고 내용만 비우는 구현(빈 줄이 남는다); 구분자를
    먼저 넣고 내용을 나중에 붙이는 구현(앞에 떠 있는 ' · ' 가 남는다); 로고를 줄 수와
    무관하게 그리는 구현(로고만 있는 줄).
    """

    def assert_no_empty_lines(self, result):
        for pid, lines in result:
            self.assertTrue(lines, f"{pid} 가 줄이 없는 채로 결과에 남아 있다")
            for line in lines:
                self.assertTrue(line, f"{pid} 에 빈 줄이 있다")
                joined = "".join(t for t, _k in line)
                self.assertTrue(joined.strip(),
                                f"{pid} 에 공백뿐인 줄이 있다: {joined!r}")
                self.assertTrue(
                    content_runs(line),
                    f"{pid} 에 구분자뿐인 줄이 있다: {joined!r}")
                self.assertNotEqual(line[0][0], claude_pet.SUMMARY_SEP,
                                    f"{pid} 의 줄이 구분자로 시작한다: {joined!r}")
                self.assertNotEqual(line[-1][0], claude_pet.SUMMARY_SEP,
                                    f"{pid} 의 줄이 구분자로 끝난다: {joined!r}")

    def test_a_provider_that_is_absent_from_the_groups_produces_nothing(self):
        for lang in ("ko", "en"):
            with self.subTest(lang=lang, present="claude only"):
                self.use(lang)
                result = layout(groups_for(lang, claude=True, codex=0))
                self.assertEqual([pid for pid, _l in result], ["claude"])
                self.assert_no_empty_lines(result)
            with self.subTest(lang=lang, present="codex only"):
                self.use(lang)
                result = layout(groups_for(lang, claude=False, codex=1))
                self.assertEqual([pid for pid, _l in result], ["codex"])
                self.assert_no_empty_lines(result)

    def test_a_provider_present_but_empty_is_dropped_entirely(self):
        """구간이 None 이거나 비어 있는 제공자는 결과에 **나타나지 않는다**.

        어댑터가 '훅이 없으면 구간을 안 붙인다'로 막고 있지만, 그 보호는 어댑터의 것이고
        이 함수의 것이 아니다. 두 군데가 같은 약속을 해야 한 군데가 바뀌어도 안전하다.
        """
        for empty in (None, [], [None]):
            with self.subTest(codex_segments=empty):
                self.use("ko")
                groups = [claude_group("ko"), ("codex", empty)]
                result = layout(groups)
                self.assertEqual([pid for pid, _l in result], ["claude"],
                                 f"빈 제공자가 결과에 남았다: {result!r}")
                self.assert_no_empty_lines(result)

    def test_no_providers_at_all_produces_no_lines(self):
        self.use("ko")
        self.assertEqual(layout([]), [])
        self.assertEqual(layout([("codex", [])]), [])

    def test_no_line_is_empty_or_separator_only_in_any_combination(self):
        for name, claude, codex in COMBINATIONS:
            for lang in ("ko", "en"):
                with self.subTest(combination=name, lang=lang):
                    self.use(lang)
                    self.assert_no_empty_lines(layout(groups_for(lang, claude=claude, codex=codex)))


class PillHeightFollowsTheLineCountTests(unittest.TestCase):
    """3줄인데 2줄 높이면 잘려 보인다. 높이는 줄 수의 함수여야 한다.

    Rivals: `SUMMARY_H`/`SUMMARY_H2` 두 경우를 상수로 박은 지금 구조가 그대로 남는 것
    (`pill_h()` 는 현재 인자도 받지 않고 무조건 `SUMMARY_H2` 를 돌려준다); 세 줄 이상을
    전부 같은 높이로 처리하는 구현.
    """

    def heights(self, counts):
        fn = claude_pet.pill_h
        out = []
        for n in counts:
            try:
                out.append(float(fn(n)))
            except TypeError as exc:
                raise AssertionError(
                    "pill_h() 가 줄 수를 받지 않는다 — 높이가 줄 수의 함수가 아니다 "
                    f"({exc})") from exc
        return out

    def test_pill_height_increases_with_each_additional_line(self):
        h = self.heights([1, 2, 3, 4])
        for i in range(1, len(h)):
            self.assertGreater(
                h[i], h[i - 1],
                f"{i + 1}줄이 {i}줄보다 높지 않다: {h} — 줄이 잘려 보인다")

    def test_the_height_is_not_pinned_to_the_two_case_constants(self):
        """`SUMMARY_H2` 를 무조건 돌려주는 구현을 직접 막는다."""
        h = self.heights([1, 2, 3])
        self.assertNotEqual(len(set(h)), 1,
                            f"줄 수가 달라도 높이가 같다: {h}")
        two_case = {getattr(claude_pet, "SUMMARY_H", None),
                    getattr(claude_pet, "SUMMARY_H2", None)}
        self.assertFalse(
            set(h) <= two_case,
            f"높이가 여전히 두 상수만으로 나온다: {h} ⊆ {two_case} — 세 줄 이상이 그려질 수 없다")


def _run_gui_def():
    tree = ast.parse((ROOT / "claude_pet.py").read_text(encoding="utf-8"),
                     filename="claude_pet.py")
    found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_gui"]
    if len(found) != 1:
        raise AssertionError("claude_pet.py 에 run_gui 가 정확히 하나 있어야 한다")
    return found[0]


def _nested(outer, name):
    found = [n for n in ast.walk(outer)
             if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(
            f"run_gui 안에 {name}() 가 정확히 하나 있어야 한다 (찾은 개수 {len(found)}) — "
            "이름이 바뀌었다면 이 게이트의 접근자를 맞춰라")
    return found[0]


def _calls_named(node, name):
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name]


def _names_in(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


class SummaryLinesIsActuallyWiredToTheScreenTests(unittest.TestCase):
    """`summary_lines` 의 결과가 **실제로 그려지는 것에 도달하는가.**

    이 클래스가 따로 있는 이유를 적어 둔다. 위의 모든 테스트는 `summary_lines` 가 맞는
    값을 낸다는 것만 말한다 — 그리고 그 17개가 전부 초록인 동안 화면에는 아무것도 닿지
    않았다. 순수 함수를 만들어 놓고 렌더러에 붙이지 않는 것은 이 저장소에서 **세 번째**
    반복되는 모양이다:

      1. Reviewer 의 F3 — 배선 5줄을 지워도 행동 테스트가 전부 초록이었다.
      2. 이번 릴리즈의 `credit_row_text` — 만들어 놓고 렌더러에 안 붙였다.
      3. 지금 — `summary_lines` 17/17 초록, 필은 여전히 단일 줄 경로.

    1번에서 고른 처방이 '렌더러를 테스트한다'였고 그래서 2번과 3번이 일어났다. 렌더러를
    테스트하는 것은 배선을 테스트하는 것이 **아니다**. 그래서 여기서는 호출 간선을 직접
    단언한다: 배선 한 줄을 끊으면 빨개져야 하고, 그 성질은 아래 mutation 으로 증명한다
    (증명 기록은 Verifier 보고에 있다).

    AppKit 없이 도는 이유: `draw_summary_pill` 과 `roam_summary_text` 는 `run_gui` 안의
    중첩 함수라 창 없이 부를 수 없다. 그래서 소스를 AST 로 읽는다 — 이 저장소가
    tests/test_autostart.py 의 메뉴 배선에 쓰는 것과 같은 방법이다.
    """

    def setUp(self):
        self.run_gui = _run_gui_def()
        self.draw = _nested(self.run_gui, "draw_summary_pill")

    def test_the_pill_text_path_calls_summary_lines(self):
        """배선 간선 1: 무언가가 실제로 `summary_lines` 를 부른다.

        Rival: `summary_lines` 가 모듈에 존재하고 17/17 초록인데 `run_gui` 안의 아무도
        부르지 않는 것 — 정확히 지금 상태다.
        """
        calls = _calls_named(self.run_gui, "summary_lines")
        self.assertTrue(
            calls,
            "run_gui 안의 아무도 summary_lines 를 부르지 않는다 — 접힘이 화면에 도달하지 "
            "않는다. 이것이 F3 의 세 번째 재발이다.")

    def test_the_drawing_path_never_trims(self):
        """배선 간선 2: 그리는 쪽이 더 이상 자르지 않는다.

        접힘이 배선돼도 `draw_summary_pill` 이 `roam_fit_runs` 를 계속 부르면 접힌 줄을
        다시 자른다 — 그러면 행 손실이 그대로 남고, 위의 17개는 여전히 초록이다.

        Rival: `summary_lines` 를 부르면서 결과를 다시 `roam_fit_runs` 에 통과시키는 구현.
        """
        for trimmer in ("roam_fit_runs", "roam_fit_text"):
            with self.subTest(trimmer=trimmer):
                self.assertEqual(
                    [ast.unparse(c) for c in _calls_named(self.draw, trimmer)], [],
                    f"draw_summary_pill 이 아직 {trimmer} 를 부른다 — 접힌 줄을 다시 자른다. "
                    "필 경로에서 자르는 쪽은 아무도 없어야 한다.")

    def test_the_pill_height_asks_for_the_line_count(self):
        """배선 간선 3: 높이가 줄 수를 따라간다.

        `pill_h()` 는 이제 줄 수를 받는다. 인자 없이 부르면 기본값 2가 쓰이고, 3줄짜리
        필이 2줄 높이로 그려져 사용자에게는 잘린 것으로 보인다 — 폭을 고쳐 놓고 높이로
        같은 증상을 만드는 길이다.

        Rival: 접힘은 배선했는데 `pill_h()` 를 인자 없이 계속 부르는 구현.
        """
        bare = [c for c in _calls_named(self.run_gui, "pill_h") if not c.args and not c.keywords]
        self.assertEqual(
            [ast.unparse(c) for c in bare], [],
            "pill_h() 를 인자 없이 부르는 자리가 남아 있다 — 줄 수와 무관한 높이가 그려진다")
        self.assertTrue(
            [c for c in _calls_named(self.run_gui, "pill_h") if c.args or c.keywords],
            "run_gui 안에서 pill_h 에 줄 수를 넘기는 자리가 없다")

    def test_every_consumer_unpacks_the_shape_roam_summary_text_actually_returns(self):
        """배선 간선 5: 반환 모양과 **모든** 소비자가 일치하는가.

        이것이 배선이 실제로 깨진 방식이다. `roam_summary_text` 가
        `(main, sub, text_w, text_h)` 에서 `(blocks, text_w, pill_h)` 로 바뀌었는데,
        소비자 셋 중 하나만 따라갔다:

            blocks, _tw, _th = roam_summary_text()                    ← 3, 맞다
            text_w, text_h = roam_summary_text()[2:]                  ← 1개에서 2개, 터진다
            _main, _sub, text_w, text_h = roam_summary_text()         ← 3개에서 4개, 터진다

        둘 다 `ValueError` 로 필 경로에서 죽는다. 순수 함수 쪽 테스트는 17/17 초록이고,
        호출 간선 테스트도 (이 테스트가 없으면) 전부 초록이다 — 부르기는 부르니까.
        '부른다'와 '받은 것을 쓸 수 있다'는 다른 질문이고, 이 클래스가 존재하는 이유인
        F3 는 정확히 그 틈에서 반복된다.

        Rival: 반환 모양만 바꾸고 소비자를 한 곳만 고치는 변경 — 지금 상태다. 창을 띄우지
        않는 테스트는 전부 초록인 채로 앱은 첫 렌더에서 죽는다.
        """
        text_fn = _nested(self.run_gui, "roam_summary_text")
        tuples = [n.value for n in ast.walk(text_fn)
                  if isinstance(n, ast.Assign) and isinstance(n.value, ast.Tuple)
                  and any(isinstance(t, ast.Name) and t.id == "value" for t in n.targets)]
        self.assertEqual(len(tuples), 1,
                         "roam_summary_text 가 메모에 넣는 튜플을 한 군데서 만들어야 한다")
        arity = len(tuples[0].elts)

        problems = []
        for node in ast.walk(self.run_gui):
            if not isinstance(node, ast.Assign):
                continue
            source = ast.unparse(node)
            if "roam_summary_text()" not in source:
                continue
            target = node.targets[0]
            if not isinstance(target, (ast.Tuple, ast.List)):
                continue
            wanted = len(target.elts)
            value = node.value
            if isinstance(value, ast.IfExp):        # `… if mode != FOLDED else (…)`
                value = value.body
            available = arity
            if isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Slice):
                lower = value.slice.lower
                start = lower.value if isinstance(lower, ast.Constant) else 0
                available = max(0, arity - start)
            if wanted != available:
                problems.append(
                    f"line {node.lineno}: {source.splitlines()[0]} — "
                    f"{wanted}개를 받으려 하는데 {available}개가 온다")
        self.assertEqual(
            problems, [],
            "roam_summary_text 의 반환 모양과 소비자가 어긋난다 — 필 경로가 ValueError 로 "
            f"죽는다 (반환 원소 {arity}개):\n  " + "\n  ".join(problems))

    def test_the_logo_is_drawn_on_the_pill_path(self):
        """배선 간선 4: 로고가 실제로 그려진다.

        로고 폭은 이미 모든 줄의 예산에서 빠져 있다(`SUMMARY_LOGO_W`). 그려지지 않으면
        사용자는 그만큼의 빈 들여쓰기만 보게 되고, 어느 제공자의 줄인지 구분할 방법이
        사라진다 — 텍스트 접두사는 로고가 대신하기로 하면서 빠졌다.

        Rival: 폭만 예약하고 마크는 안 그리는 구현. 폭 단언으로는 절대 안 잡힌다.
        """
        reached = _names_in(self.draw)
        logo_names = {"SUMMARY_LOGO_FILES", "SUMMARY_LOGO_DIR", "SUMMARY_LOGO_MARK",
                      "SUMMARY_LOGO_TINT", "summary_logo_image", "_summary_logo",
                      "draw_summary_logo", "_draw_logo"}
        self.assertTrue(
            reached & logo_names,
            "draw_summary_pill 이 로고를 전혀 건드리지 않는다 — 자리만 비워 두고 마크를 "
            f"그리지 않는다. (본 이름: {sorted(reached & logo_names)})")


class LogoAssetsArePackagedTests(unittest.TestCase):
    """로고가 번들에서만 사라지는 실패를 막는다.

    `fonts/` 가 정확히 이 실패를 한 적이 있다: 소스 실행에서는 멀쩡하고 번들에서만
    글꼴이 없었다. 그래서 `fonts/` 가 따르는 세 자리를 그대로 요구한다 — `setup.py`
    리소스, `build_app.sh` 의 `build()` **와** `update()` 양쪽 복사, 그리고
    `verify_release_artifact.py` 가 없는 아티팩트를 거부하는 것. 셋 중 하나라도 빠지면
    코드만 새로 고친 번들에서 로고가 조용히 사라진다.
    """

    def files(self):
        mapping = _require("SUMMARY_LOGO_FILES")
        self.assertIsInstance(mapping, dict,
                              "SUMMARY_LOGO_FILES 는 제공자 → 파일명 매핑이어야 한다")
        for provider in ("claude", "codex"):
            self.assertIn(provider, mapping,
                          f"{provider} 로고가 선언되지 않았다")
        return mapping

    def test_every_declared_logo_is_a_real_regular_file_in_this_tree(self):
        directory = ROOT / _require("SUMMARY_LOGO_DIR")
        for provider, name in self.files().items():
            with self.subTest(provider=provider):
                path = directory / name
                self.assertTrue(path.is_file(), f"{path} 가 없다")
                self.assertFalse(path.is_symlink(), f"{path} 는 일반 파일이어야 한다")
                head = path.read_bytes()[:512].lstrip()
                self.assertTrue(head.startswith(b"<?xml") or head.startswith(b"<svg"),
                                f"{path} 가 SVG 가 아니다")

    def test_setup_py_ships_the_logo_directory_as_a_resource(self):
        directory = _require("SUMMARY_LOGO_DIR")
        text = (ROOT / "setup.py").read_text(encoding="utf-8")
        self.assertRegex(text, r'"resources"\s*:\s*\[[^\]]*' + re.escape(directory),
                         f"setup.py 가 {directory} 를 번들 리소스로 넣지 않는다")

    def test_build_app_copies_the_logos_in_both_build_and_update(self):
        """양쪽 다여야 한다 — `update()` 가 빠지면 코드만 새로 고친 번들에서 로고가
        사라지고, 그건 `.claude_pet` 트리와 폰트가 이미 겪은 실패다."""
        source = (ROOT / "build_app.sh").read_text(encoding="utf-8")
        directory = _require("SUMMARY_LOGO_DIR")
        for arm in ("build_body", "update_installed"):
            with self.subTest(arm=arm):
                body = _zsh_function(source, arm)
                self.assertIn(directory, body,
                              f"build_app.sh 의 {arm}() 가 {directory} 를 복사하지 않는다")

    def test_the_release_gate_refuses_an_artifact_without_the_logos(self):
        text = (ROOT / "verify_release_artifact.py").read_text(encoding="utf-8")
        self.assertIn(_require("SUMMARY_LOGO_DIR"), text,
                      "verify_release_artifact.py 가 로고 없는 아티팩트를 통과시킨다")


class FoldBudgetMatchesTheActualPillTests(LangMixin, unittest.TestCase):
    """접힘이 믿는 예산과 필이 실제로 주는 폭이 **같은 값인가.**

    ── 이 클래스가 왜 생겼는지, 내 실수를 그대로 적어 둔다 ────────────────────────

    나는 이 파일과 `PillWidthFollowsContentTests` 에서 "상한이 화면을 따라간다"를
    단언했다. 관계는 참이었다. **입력이 허구였다.** 내 헬퍼는 이렇게 불렀다:

        roam_pill_rect(mode, False, False, screen_w, …)      # 매개변수 이름이 screen_w

    생산은 거기에 화면을 **절대** 넘기지 않는다. `geom()` 의
    `W = max(pw + BTN_R*2 + 16, PILL_W + 8)` 를 넘기고, 그 값은 펫 크기와 무관하게
    **308** 이다. 그래서 필의 상한은 여전히 `300 - 2*SUMMARY_EDGE` = 300 이고, 글자가
    쓸 수 있는 자리는 `300 - 2*PILL_PAD - SUMMARY_LOGO_W` = **256** 이다. 그런데
    `_pill_text_budget()` 은 **화면**(≈1920)을 접힘에 넘긴다. 접힘은 1920 이 있다고 믿어
    접지 않고, `draw_summary_pill` 은 (의도대로) 자르지 않고, `_draw_runs` 는 가운데
    정렬이라 넘치는 줄의 시작점이 필 왼쪽 **밖으로** 나간다 — 말줄임표도 없이.

    내가 매개변수에 `screen_w` 라고 이름을 붙인 순간 가정이 픽스처에 박혔고, 그 뒤로는
    테스트가 그 가정을 검사할 방법이 없었다. **은퇴시킨 `test_the_pill_cannot_be_widened_
    to_make_room` 과 같은 종류다** — 그때 나는 "매직 넘버를 고정하는 테스트는 틀려 보이지
    않고 엄밀해 보인다"고 적었다. 이번엔 한 층 위에서, *관계만 검사하는* 테스트가 허구의
    입력으로 같은 일을 했다. 관계를 검사하는 것으로는 부족하고, **입력이 생산에서 와야**
    한다.

    그래서 이 클래스는 양쪽 끝을 **생산 경로에서 유도**한다: `W` 는 `geom()` 을 꺼내서
    부르고, 접힘 예산은 `_pill_text_budget()` 을 꺼내서 부른다. 식을 여기 다시 적지
    않는다 — 다시 적는 순간 또 갈라진다.
    """

    SCREEN = 1920.0          # a realistic display; only _pill_text_budget sees it

    def setUp(self):
        super().setUp()
        from test_companion_motion import gui_functions
        api = _require("PILL_W")  # fail early with the contract message if absent
        scope = {
            "PW0": 120, "PH0": 90, "g": {"scale": 1.0},
            "BTN_R": claude_pet.BTN_R, "GAP": claude_pet.GAP,
            "PILL_W": claude_pet.PILL_W, "PILL_PAD": claude_pet.PILL_PAD,
            "SUMMARY_MIN_W": claude_pet.SUMMARY_MIN_W,
            "SUMMARY_EDGE": claude_pet.SUMMARY_EDGE,
            "SUMMARY_LOGO_W": claude_pet.SUMMARY_LOGO_W,
            "SUMMARY_LINE_H": claude_pet.SUMMARY_LINE_H,
            "SUMMARY_PAD_V": claude_pet.SUMMARY_PAD_V,
            "SUMMARY_H": claude_pet.SUMMARY_H,
            "pill_h": claude_pet.pill_h,
            "state": {"summary_lines_n": 2},
            "win": None,
            "NSScreen": SimpleNamespaceScreen(self.SCREEN),
        }
        gui_functions(self, ("geom", "_pill_text_budget"), scope)
        self.PW, self.PH, self.W, self.H = scope["geom"]()
        self.fold_budget = float(scope["_pill_text_budget"]())

    def pill_text_area(self, text_w, lines):
        """생산이 실제로 그리는 필의 **글자 자리** 폭. roam_pill_rect 를 그대로 쓴다."""
        band = claude_pet.pill_h(lines)
        rect = claude_pet.roam_pill_rect(
            claude_pet.DISPLAY_FULL, False, False, self.W, self.PW, self.PH,
            band, text_w=text_w, text_h=band)
        self.assertIsNotNone(rect)
        x, _y, w, _h = rect
        return x, w - 2 * claude_pet.PILL_PAD - claude_pet.SUMMARY_LOGO_W

    def measure_line(self, line):
        return sum(pretendard_width(t) for t, _k in line)

    def test_the_fold_budget_is_the_width_the_pill_actually_gives(self):
        """불변식의 뿌리. 접힘에 넘기는 예산과 필이 내주는 글자 자리가 같아야 한다.

        다르면 접힘은 자기가 가진 줄 알고 안 접고, 필은 그만큼을 안 준다. 오늘 그 비는
        7.5배다.

        Rival: 예산을 화면에서 재고 필을 `geom()` 의 W 로 재는 구현 — 지금 상태다. 양쪽
        각각은 '맞는 값'이고 둘이 같은 것을 가리키지 않는다.
        """
        _x, available = self.pill_text_area(text_w=10_000, lines=2)
        self.assertAlmostEqual(
            self.fold_budget, available, delta=1.0,
            msg=(f"접힘 예산 {self.fold_budget:.0f}pt 인데 필이 주는 글자 자리는 "
                 f"{available:.0f}pt 다 ({self.fold_budget / max(available, 1):.1f}배). "
                 f"논리 창 W={self.W} (geom(): max(pw+BTN_R*2+16, PILL_W+8)) 는 화면이 "
                 "아니다 — 접힘이 믿는 폭과 필이 주는 폭이 같은 값이어야 한다."))

    def test_no_produced_line_exceeds_the_pill_it_will_be_drawn_in(self):
        """**같은 내용**에 대해 `summary_lines` 가 낸 줄과 `roam_pill_rect` 가 낸 필을
        맞댄다. 양쪽 다 생산 값으로.

        Reviewer 실측으로 오늘 이미 넘치는 조합이 있다 — 영어 Claude 게이지+크레딧 줄이
        대표다. 넘치는데 접히지도 잘리지도 않으므로 사용자는 **말줄임표 없이 사라진 글자**를
        본다.
        """
        problems = []
        for lang in ("ko", "en"):
            for credit in (False, True):
                for codex in (0, 1, 2):
                    self.use(lang)
                    groups = groups_for(lang, claude=True, codex=codex, credit=credit)
                    blocks = layout(groups, budget=self.fold_budget)
                    lines = all_lines(blocks)
                    if not lines:
                        continue
                    text_w = max(self.measure_line(l) for l in lines) + claude_pet.SUMMARY_LOGO_W
                    _x, available = self.pill_text_area(text_w, len(lines))
                    for line in lines:
                        width = self.measure_line(line)
                        if width > available + 0.5:
                            problems.append(
                                f"[{lang} credit={credit} codex={codex}] "
                                f"{width:.1f}pt > {available:.1f}pt : "
                                f"{''.join(t for t, _k in line)!r}")
        self.assertEqual(
            problems, [],
            "필 밖으로 나가는 줄이 있다 — 접히지도 잘리지도 않으므로 사용자에게는 "
            "말줄임표 없이 글자가 사라진 것으로 보인다:\n  " + "\n  ".join(problems))

    def test_an_overflowing_line_starts_outside_the_pill_not_merely_wide(self):
        """`_draw_runs` 는 가운데 정렬이다 — `cx = x + (w - total) / 2`. total 이 w 를
        넘으면 **시작점이 필 왼쪽 밖**으로 나가고, 로고 자리를 침범한 뒤 창에서 잘린다.

        "안 잘린다"만 단언하면 이걸 못 잡는다. 그래서 그리기 시작점을 직접 계산해서
        글자 자리 왼쪽 경계 안에 있는지 본다.

        Rival: 폭만 보고 통과시키는 단언 — 넘치는 줄도 '그려지기는 한다'.
        """
        problems = []
        for lang in ("ko", "en"):
            for credit in (False, True):
                self.use(lang)
                groups = groups_for(lang, claude=True, codex=1, credit=credit)
                lines = all_lines(layout(groups, budget=self.fold_budget))
                if not lines:
                    continue
                text_w = max(self.measure_line(l) for l in lines) + claude_pet.SUMMARY_LOGO_W
                pill_x, available = self.pill_text_area(text_w, len(lines))
                text_left = pill_x + claude_pet.PILL_PAD + claude_pet.SUMMARY_LOGO_W
                for line in lines:
                    start = text_left + (available - self.measure_line(line)) / 2.0
                    if start < text_left - 0.5:
                        problems.append(
                            f"[{lang} credit={credit}] 시작 x={start:.1f} < 글자 자리 "
                            f"왼쪽 {text_left:.1f} : {''.join(t for t, _k in line)!r}")
        self.assertEqual(
            problems, [],
            "가운데 정렬 때문에 줄의 시작점이 글자 자리 밖으로 나간다 — 로고 자리를 "
            "침범하고 창에서 잘린다:\n  " + "\n  ".join(problems))


class PillWidthDoesNotJitterTests(LangMixin, unittest.TestCase):
    """필 폭이 **숫자 값**에 흔들리지 않는가. 자릿수에는 흔들려도 된다.

    두 경우를 섞으면 안 되고, 그 구분이 이 클래스의 전부다:

    · `42% → 43%`, `99% → 98%` — **자릿수가 같다.** 폭이 한 톨이라도 움직이면 실패다.
      사용자에게는 새로고침마다 펫이 실룩거리는 것으로 보인다.
    · `9% → 10%`, `99% → 100%` — **자릿수가 늘었다.** 폭이 움직이는 것이 **정상**이고,
      안 움직이면 글자가 필 밖으로 나간다. 이걸 실패로 걸면 넘침을 강제하게 된다.

    첫째는 우연이 아니라 **구성상** 참이다 — `_stable_w()` 가 폭을 잴 때 모든 숫자를
    가장 넓은 숫자 글리프로 바꿔서 재기 때문이다. 그래서 여기서는 고른 전이 몇 개를
    확인하지 않고 **그 성질 자체**를 단언한다: "자릿수가 같으면 잰 폭이 같다". 성질로
    걸면 다른 로케일·다른 게이지 조합·앞으로 생길 제공자에도 자동으로 적용된다. 표에서
    고른 전이 네 개만 보는 게이트는 그 표에만 맞는다.
    """

    def setUp(self):
        super().setUp()
        from test_companion_motion import gui_functions
        widths = {}

        def astr(text, _font):
            import types
            return types.SimpleNamespace(
                size=lambda: types.SimpleNamespace(
                    width=sum(widths.get(c, pretendard_width(c)) for c in text)))

        scope = {"astr": astr, "F_SUMMARY": None,
                 "SUMMARY_MIN_W": claude_pet.SUMMARY_MIN_W,
                 "PILL_W": claude_pet.PILL_W}
        gui_functions(self, ("_stable_w", "_pill_width_step", "_widest_digit"), scope)
        self.stable_w = scope["_stable_w"]
        self.step = scope["_pill_width_step"]()
        self.widest_digit = scope["_widest_digit"]()

    def test_the_step_is_derived_from_the_widest_digit_not_chosen_from_a_sample(self):
        """`_pill_width_step()` 은 실측에서 고른 상수가 아니라 **유도된 값**이어야 한다 —
        '가장 넓은 숫자 글리프 하나의 폭'. 그 유도가 유지되는지 본다.

        Rival: 샘플에서 고른 양자화 단위(예: 4pt). 경계가 두 인접값 사이에 떨어지느냐가
        우연이라 그 샘플에만 맞고, 다른 글꼴·다른 크기에서 조용히 틀린다.
        """
        self.assertEqual(len(self.widest_digit), 1)
        self.assertTrue(self.widest_digit.isdigit())
        widest = max("0123456789", key=pretendard_width)
        self.assertAlmostEqual(
            pretendard_width(self.widest_digit), pretendard_width(widest), places=4,
            msg=f"_widest_digit() = {self.widest_digit!r} 인데 실제 가장 넓은 숫자는 "
                f"{widest!r} 이다")
        self.assertAlmostEqual(
            self.step, pretendard_width(widest), places=4,
            msg=f"step {self.step} 이 가장 넓은 숫자 글리프 폭 "
                f"{pretendard_width(widest)} 에서 유도되지 않았다")

    def test_same_digit_count_measures_the_same_width(self):
        """성질 그 자체. 자릿수만 같으면 **어떤 숫자든** 잰 폭이 같아야 한다.

        고른 전이가 아니라 실제 필 문구에 대해 확인한다 — 로케일 둘 × 크레딧 유무 ×
        Codex 0/1/2 행, 각 조합의 모든 줄에 대해 퍼센트 값만 바꿔 가며.
        """
        problems = []
        for lang in ("ko", "en"):
            for credit in (False, True):
                for codex in (0, 1, 2):
                    self.use(lang)
                    for pcts in ((42.0, 17.0, 12.0), (43.0, 18.0, 13.0), (99.0, 98.0, 97.0)):
                        groups = groups_for(lang, claude=True, codex=codex, credit=credit)
                        base = [l for l in all_lines(layout(groups))]
                        texts = ["".join(t for t, _k in line) for line in base]
                        for text in texts:
                            swapped = text.translate(str.maketrans("0123456789", "5555555555"))
                            if sum(c.isdigit() for c in text) != sum(c.isdigit() for c in swapped):
                                continue
                            a, b = self.stable_w(text), self.stable_w(swapped)
                            if abs(a - b) > 1e-6:
                                problems.append(
                                    f"[{lang} credit={credit} codex={codex}] "
                                    f"{a:.3f} != {b:.3f} : {text!r} vs {swapped!r}")
        self.assertEqual(
            problems, [],
            "자릿수가 같은데 잰 폭이 달라진다 — 숫자 값이 바뀔 때마다 필이 실룩거린다:\n  "
            + "\n  ".join(problems[:8]))

    def test_a_value_change_at_equal_digit_count_never_moves_the_width(self):
        """위 성질을 `next_pill_width` 까지 통과시켜 확인한다. `W` 가 움직이면 실패."""
        cap = 2000.0
        for before, after in (("세션 42%", "세션 43%"), ("세션 99%", "세션 98%"),
                              ("Session 42%", "Session 43%"), ("Weekly 10%", "Weekly 99%")):
            with self.subTest(transition=f"{before} -> {after}"):
                self.assertEqual(sum(c.isdigit() for c in before),
                                 sum(c.isdigit() for c in after), "픽스처의 자릿수가 다르다")
                w0 = claude_pet.next_pill_width(claude_pet.PILL_W, self.stable_w(before),
                                                self.step, cap)
                w1 = claude_pet.next_pill_width(w0, self.stable_w(after), self.step, cap)
                self.assertEqual(w1, w0,
                                 f"{before!r} → {after!r} 에서 폭이 {w0} → {w1} 로 움직였다")

    def test_a_digit_count_change_is_allowed_to_move_the_width(self):
        """**이건 실패가 아니다.** 자릿수가 늘면 폭이 따라가야 한다 — 안 따라가면 넘친다.

        그래서 '움직였다'를 단언하지 않고, 움직이더라도 **필요한 폭을 덮는다**는 것만
        단언한다. 방향을 고정하면 구현을 과하게 묶는다.
        """
        cap = 2000.0
        for before, after in (("세션 9%", "세션 10%"), ("세션 99%", "세션 100%"),
                              ("Session 9%", "Session 10%")):
            with self.subTest(transition=f"{before} -> {after}"):
                w0 = claude_pet.next_pill_width(claude_pet.PILL_W, self.stable_w(before),
                                                self.step, cap)
                w1 = claude_pet.next_pill_width(w0, self.stable_w(after), self.step, cap)
                self.assertGreaterEqual(
                    w1, self.stable_w(after),
                    f"{after!r} 에 필요한 폭 {self.stable_w(after):.1f} 을 새 폭 {w1} 이 "
                    "덮지 못한다 — 글자가 필 밖으로 나간다")

    def test_growth_is_immediate_and_shrinking_needs_a_full_step(self):
        """커질 때는 그 프레임에 바로, 줄어들 때는 한 단계 아래로 확실히 내려간 뒤에만.

        Rivals: 커지는 쪽을 미루는 구현(그 프레임에 글자가 밖으로 나간다 — 이번 사고);
        줄어드는 쪽을 즉시 따라가는 구현(경계에서 폭이 오간다); 단조 증가만 하는 구현
        (내용이 짧아져도 넓은 필이 남아 "유려하게"를 어긴다).
        """
        step, cap = self.step, 2000.0
        self.assertEqual(claude_pet.next_pill_width(200.0, 260.0, step, cap),
                         math.ceil(260.0 / step) * step, "커질 때 즉시 따라가지 않는다")
        self.assertEqual(claude_pet.next_pill_width(300.0, 300.0 - step / 2, step, cap),
                         300.0, "한 단계 미만으로 줄었는데 폭이 내려갔다")
        shrunk = claude_pet.next_pill_width(300.0, 300.0 - step * 2, step, cap)
        self.assertLess(shrunk, 300.0, "충분히 줄었는데 폭이 안 내려간다 — 단조 증가다")
        self.assertLessEqual(claude_pet.next_pill_width(100.0, 999_999.0, step, cap), cap,
                             "상한을 넘겼다")


class SimpleNamespaceScreen:
    """`_pill_text_budget` 이 보는 화면. 실제 기계 한 대를 흉내 낸다."""

    def __init__(self, width):
        self._w = width

    def mainScreen(self):
        return self

    def visibleFrame(self):
        import types
        return types.SimpleNamespace(size=types.SimpleNamespace(width=self._w, height=1080.0))


class LogoTintIsActuallyAppliedTests(unittest.TestCase):
    """틴트가 **픽셀에 실제로 닿는가**. macOS 전용, 크게 건너뛴다.

    이 클래스는 이번 릴리즈에서 **유일하게 게이트가 못 잡고 눈으로 잡힌 결함** 때문에
    생겼다. `openai.svg` 는 `fill="currentColor"` 라 색을 우리가 정해야 하는데, 한때
    `setTemplate_(True)` 를 켜고 그리기 직전에 `hexcolor(tint).set()` 을 했고 **둘이
    합쳐서 아무 일도 하지 않았다**. 번들에는 파일이 바이트 동일하게 들어갔고 AppKit 이
    로드하는 것까지 확인됐는데, 마크는 검게 그려져 어두운 필 배경에서 보이지 않았다.
    상수와 배선을 다 확인해도 픽셀을 보기 전에는 아무도 몰랐다.

    그래서 여기서는 성질을 **차등**으로 잰다 — "보이는가"를 판정할 대비 임계값을 지어낼
    필요가 없다. 지어낸 임계값을 재는 테스트는 아무것도 재지 않는다(그래서 처음에 이
    게이트를 안 만들었고, 그 판단이 틀렸다). 실제 실패 모드는 **틴트를 건 렌더와 안 건
    렌더의 픽셀이 바이트 단위로 같았다**는 것이고, 그건 임계값 없이 그대로 단언된다.

    `_tinted_logo` 는 `run_gui` 안의 중첩 함수라 창 없이 못 부른다. 그래서
    tests/test_companion_motion.py 의 `gui_functions` 로 **생산 코드 그 자체**를 뽑아
    쓴다 — 여기서 같은 합성을 다시 구현하면 내 구현을 시험하는 꼴이 되고, 그건 이 결함이
    통과한 경로와 정확히 같은 모양이다.
    """

    SIZE = 28

    def setUp(self):
        if sys.platform != "darwin":
            self._skip("마크 합성 검사는 macOS AppKit 이 필요하다")
        try:
            from AppKit import (NSImage, NSMakeSize, NSMakeRect, NSZeroRect,
                                NSRectFillUsingOperation, NSBitmapImageRep, NSColor)
        except ImportError as exc:
            self._skip(f"pyobjc 를 못 불러온다 ({exc.__class__.__name__})")
        from test_companion_motion import gui_functions
        self.ns = dict(NSImage=NSImage, NSMakeSize=NSMakeSize, NSMakeRect=NSMakeRect,
                       NSZeroRect=NSZeroRect,
                       NSRectFillUsingOperation=NSRectFillUsingOperation,
                       NSBitmapImageRep=NSBitmapImageRep, NSColor=NSColor)

        def hexcolor(h, a=1.0):
            h = h.lstrip("#")
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
            return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)

        self.hexcolor = hexcolor
        scope = dict(self.ns, hexcolor=hexcolor)
        gui_functions(self, ("_tinted_logo",), scope)
        self.tinted_logo = scope["_tinted_logo"]

    def _skip(self, why):
        print(f"\n[summary-logo] SKIPPED: {why}", file=sys.stderr, flush=True)
        self.skipTest(why)

    def load(self, provider):
        directory = ROOT / _require("SUMMARY_LOGO_DIR")
        name = _require("SUMMARY_LOGO_FILES")[provider]
        image = self.ns["NSImage"].alloc().initWithContentsOfFile_(str(directory / name))
        self.assertIsNotNone(image, f"{name} 를 NSImage 가 읽지 못했다")
        return image

    def pixels(self, image):
        """{(r,g,b): 개수} — 거의 투명한 픽셀은 뺀다. 알파 개수도 같이 돌려준다."""
        rep = self.ns["NSBitmapImageRep"].imageRepWithData_(image.TIFFRepresentation())
        counts, opaque = {}, 0
        for x in range(0, int(rep.pixelsWide()), 2):
            for y in range(0, int(rep.pixelsHigh()), 2):
                colour = rep.colorAtX_y_(x, y)
                if colour.alphaComponent() < 0.05:
                    continue
                opaque += 1
                key = tuple(round(getattr(colour, c)(), 2) for c in
                            ("redComponent", "greenComponent", "blueComponent"))
                counts[key] = counts.get(key, 0) + 1
        return counts, opaque

    def plain(self, image):
        """틴트를 **전혀** 걸지 않은 같은 크기 렌더 — 비교 기준."""
        out = self.ns["NSImage"].alloc().initWithSize_(
            self.ns["NSMakeSize"](self.SIZE, self.SIZE))
        out.lockFocus()
        try:
            image.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(
                self.ns["NSMakeRect"](0, 0, self.SIZE, self.SIZE),
                self.ns["NSZeroRect"], 2, 1.0, True, None)
        finally:
            out.unlockFocus()
        return out

    def test_tinting_actually_changes_the_pixels(self):
        """**배포된 결함 그 자체.** 틴트를 건 렌더가 안 건 렌더와 같으면 틴트는 없는 것이다.

        Rivals: `setTemplate_(True)` + 그리기 직전 `set()`(실제로 나간 것 — 직접 그리기
        경로에서 template 플래그는 무시되고 컨텍스트 fill color 는 비트맵 합성에 적용되지
        않는다); 틴트를 선언만 하고 합성하지 않는 구현.
        """
        for provider, tint in _require("SUMMARY_LOGO_TINT").items():
            with self.subTest(provider=provider):
                image = self.load(provider)
                before, _ = self.pixels(self.plain(image))
                after, _ = self.pixels(self.tinted_logo(image, tint, self.SIZE))
                self.assertNotEqual(
                    before, after,
                    f"{provider} 마크의 틴트 전후 픽셀 분포가 같다 — 틴트가 아무 일도 하지 "
                    f"않는다 (분포: {sorted(before.items())[:3]})")

    def test_the_tinted_pixels_carry_the_declared_colour(self):
        """색이 *바뀌었다*로는 부족하다 — **선언한 그 색**이어야 한다."""
        for provider, tint in _require("SUMMARY_LOGO_TINT").items():
            with self.subTest(provider=provider):
                wanted = self.hexcolor(tint)
                target = tuple(round(getattr(wanted, c)(), 2) for c in
                               ("redComponent", "greenComponent", "blueComponent"))
                counts, opaque = self.pixels(self.tinted_logo(
                    self.load(provider), tint, self.SIZE))
                self.assertTrue(opaque, f"{provider} 마크가 불투명 픽셀을 하나도 안 남겼다")
                dominant = max(counts, key=counts.get)
                for got, want in zip(dominant, target):
                    self.assertAlmostEqual(
                        got, want, delta=0.08,
                        msg=f"{provider} 마크의 주된 색이 {dominant} 인데 선언은 {target} 이다")

    def test_tinting_preserves_the_silhouette(self):
        """실루엣이 유지돼야 한다 — 틴트는 색을 바꾸는 것이지 사각형을 칠하는 게 아니다.

        Rival: `sourceAtop`(5) 대신 `sourceOver`(2)로 칠하는 구현. 색은 바뀌므로 위
        두 테스트를 통과하지만 마크가 사각형 덩어리가 된다. 불투명 픽셀 수로 갈린다.
        """
        for provider, tint in _require("SUMMARY_LOGO_TINT").items():
            with self.subTest(provider=provider):
                image = self.load(provider)
                _, before = self.pixels(self.plain(image))
                _, after = self.pixels(self.tinted_logo(image, tint, self.SIZE))
                self.assertEqual(
                    after, before,
                    f"{provider} 마크의 불투명 픽셀 수가 {before} → {after} 로 바뀌었다 — "
                    "알파 밖까지 칠했다(sourceOver)거나 실루엣을 잃었다")

    def test_the_image_the_app_hands_the_renderer_is_already_tinted(self):
        """**버그가 있던 층을 검사한다.** 위 세 테스트는 합성기(`_tinted_logo`)를 보고,
        버그는 합성할지 **정하는 곳**(`summary_logo_image`)에 있었다.

        Reviewer 의 T6: 틴트를 적용하는 두 줄을 지워도

            tint = SUMMARY_LOGO_TINT.get(provider)
            -if tint:
            -    img = _tinted_logo(img, tint, SUMMARY_LOGO_MARK)

        전체 스위트에서 **행동 테스트가 하나도 안 떨어진다.** 떨어지는 것은 전부 SHA256
        바이트 핀인데, 그건 주석 오타에도 똑같이 떨어지므로 행동에 대한 증거가 아니다.
        합성기가 다섯 가지 변이로 전부 잡히는 것과, 앱이 실제로 합성기를 **부르는지**는
        다른 질문이고, 배포된 화면을 결정한 것은 후자다.

        그래서 `summary_logo_image(provider)` 를 그대로 구동해 **돌려받은 이미지**의
        지배색을 본다. 검정이면 실패다 — 그게 사용자가 본 것이다.

        Rivals: 틴트 적용 줄 삭제(T6, 배포된 상태); 캐시가 안 칠한 사본을 먼저 채우는
        구현; 틴트 표에서 제공자가 빠지는 것.
        """
        from test_companion_motion import gui_functions
        for provider, tint in _require("SUMMARY_LOGO_TINT").items():
            with self.subTest(provider=provider):
                directory = ROOT / _require("SUMMARY_LOGO_DIR")
                scope = dict(self.ns, hexcolor=self.hexcolor,
                             SUMMARY_LOGO_FILES=_require("SUMMARY_LOGO_FILES"),
                             SUMMARY_LOGO_TINT=_require("SUMMARY_LOGO_TINT"),
                             SUMMARY_LOGO_MARK=_require("SUMMARY_LOGO_MARK"),
                             bundled_logo_path=lambda name: str(directory / name),
                             # `_logo_cache` is an assignment inside run_gui, and
                             # `gui_functions` extracts function definitions only — so it
                             # has to be supplied. A fresh dict per subtest is also what
                             # makes this test honest: a shared cache would let an earlier
                             # provider's result answer for a later one.
                             _logo_cache={},
                             _dbg=lambda *a, **k: None)
                gui_functions(self, ("summary_logo_image",), scope)
                image = scope["summary_logo_image"](provider)
                self.assertIsNotNone(image, f"{provider} 마크를 앱이 불러오지 못했다")

                counts, opaque = self.pixels(image)
                self.assertTrue(opaque, f"{provider} 마크가 불투명 픽셀을 안 남겼다")
                dominant = max(counts, key=counts.get)
                wanted = self.hexcolor(tint)
                target = tuple(round(getattr(wanted, c)(), 2) for c in
                               ("redComponent", "greenComponent", "blueComponent"))
                black = all(channel < 0.12 for channel in dominant)
                self.assertFalse(
                    black,
                    f"{provider} 마크를 앱이 **검게** 돌려준다 (지배색 {dominant}) — "
                    f"틴트 {tint} 가 선언돼 있는데 적용되지 않았다. 어두운 필 배경에서 "
                    "사용자에게는 마크가 아예 없는 것으로 보인다.")
                for got, want in zip(dominant, target):
                    self.assertAlmostEqual(
                        got, want, delta=0.08,
                        msg=f"{provider} 마크의 지배색이 {dominant}, 선언은 {target}")

    def test_a_mark_that_renders_monochrome_black_must_declare_a_tint(self):
        """비대칭을 성질로 고정한다. Claude 마크는 자체 컬러라 틴트가 필요 없고,
        `currentColor` 마크는 검정으로 래스터화되므로 반드시 틴트를 선언해야 한다.

        `SUMMARY_LOGO_TINT` 에 `codex` 가 있는지 직접 묻지 않는 이유: 그건 오늘의 답을
        외우는 것이다. 여기서는 **파일을 렌더해 보고** 단색 검정으로 나오는 마크가 틴트
        없이 선언돼 있으면 실패한다 — 세 번째 제공자가 같은 모양으로 들어오는 날 잡힌다.
        """
        tints = _require("SUMMARY_LOGO_TINT")
        for provider in sorted(_require("SUMMARY_LOGO_FILES")):
            with self.subTest(provider=provider):
                counts, opaque = self.pixels(self.plain(self.load(provider)))
                self.assertTrue(opaque, f"{provider} 마크가 아무것도 그리지 않는다")
                dark = sum(n for (r, g, b), n in counts.items()
                           if r < 0.12 and g < 0.12 and b < 0.12)
                if dark / float(opaque) > 0.95:
                    self.assertIn(
                        provider, tints,
                        f"{provider} 마크는 틴트 없이 단색 검정으로 그려진다 "
                        f"(불투명 픽셀의 {dark / opaque:.0%}) — 어두운 필 배경에서 보이지 "
                        "않는다. SUMMARY_LOGO_TINT 에 색을 선언해야 한다.")


def _zsh_function(source, name):
    header = f"{name}() {{"
    if source.count(header) != 1:
        raise AssertionError(f"build_app.sh 에 {header!r} 가 정확히 하나 있어야 한다")
    start = source.index(header)
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"{name} 가 닫히지 않았다")


if __name__ == "__main__":
    unittest.main()
