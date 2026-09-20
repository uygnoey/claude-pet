"""토큰 자동 갱신·복구 게이팅 테스트 — Verifier 작성, 구현 전.

이 파일은 아직 없는 동작을 고정한다. 작성 시점에 전부 빨강이어야 하고, 그 빨강을
먼저 관찰한 기록이 AGENTS.md §3 의 red-before-green 요구다.

고정하는 것은 **성질**이지 구현이 아니다. 특히 spawn 방식(disclaim 헬퍼 / launchd)은
고르지 않는다 — 대신 "ClaudePet 이 보호폴더 접근의 책임 프로세스가 되면 안 된다"와
"터미널 창을 띄우지 않는다"만 건다.

── 왜 이런 모양인지 (실측과 선행 사례) ──────────────────────────────────────

**직계 자식 spawn 금지.** 2026-07-13, `_fetch_cli_usage()` 가 `claude -p /usage` 로
Claude Code(Node 앱)를 직접 자식으로 띄웠고, 그 폴더 스캔이 부모(ClaudePet)에
귀속돼 macOS 가 보호폴더 프롬프트를 띄웠다. 이 맥 TCC DB 에
`com.yeongyu.claudepet` 거부 8건(13:08~14:08)이 남아 있고, 같은 날 밤 커밋 67849e4
가 그 대응으로 CLI 경로를 옵트인으로 내렸다. 복구는 같은 명령을 다시 쓰므로 같은
함정을 다시 밟지 않아야 한다.

**자가 갱신 금지 — 우리는 관찰자다.** Orca(ADE)는 `platform.claude.com/v1/oauth/token`
을 직접 호출해 갱신하고 회전된 refresh 토큰을 자기 저장소에 써넣는다. ADE 는 세션과
자격증명을 관리하는 게 본업이라 그게 성립한다. ClaudePet 은 옆에서 보기만 하는
관찰자고, 저장소도 이 맥에선 파일이 아니라 Keychain 이다(Orca 조차 Keychain 엔 쓰지
않는다). 써넣지 못하는 쪽이 갱신을 시도하면 회전된 refresh 토큰이 유실돼 사용자가
재로그인해야 한다 — 2026-07 에 실제로 그렇게 됐다. CodexBar 가 문서에 못박은 원칙과
같은 결론이다: **read-only tokens, CLI-owned refresh.**

**브라우저 튐 가드.** CodexBar PR #1848: Keychain 항목에 `claudeAiOauth` 없이 MCP
OAuth 상태만 들어 있을 때 백그라운드로 CLI 를 돌리면 `/usr/bin/open` 으로 브라우저가
떠버린다. 스폰 전에 `claudeAiOauth` 존재를 확인하는 fail-closed 가드가 필요하다.

**할당량은 쟁점이 아니다.** 2026-09-19 실측: `claude -p /usage` 3회가 만든 세션 로그
3개에 assistant 턴도 message.usage 도 0건이었다(모델 호출 없음).

**갱신은 만료 기반이다.** 액세스 토큰 수명은 8시간이고 `expiresAt` 은 로컬에서
읽힌다. 180초마다 Node 앱을 띄울 이유가 없다 — 만료 임박 때 한 번이면 하루 3회다.
마진은 Orca 의 5분(300s)을 참고값으로 둔다. 참고로 CodexBar 의 백그라운드 갱신
최소 간격은 15분(저전력 30분)이다.

테스트 정책(CLAUDE.md): 실제 ~/.claude 코퍼스를 읽지 않는다. 모든 픽스처는 합성이고
CLI 는 절대 실제로 실행하지 않는다.
"""

import ast
import inspect
import os
import pathlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import claude_pet  # noqa: E402
except ImportError:
    # Windows: 코어는 `fcntl` 과 `ctypes.CDLL(None)` 때문에 그대로는 임포트되지 않는다.
    # 그 우회로의 **유일한 소유자**는 포트의 `windows/win_core.py:import_core()` 이고,
    # 여기서 그 로직을 복제하지 않는다 — 한쪽만 고쳐지는 날이 오면 안 되기 때문이다.
    # (win_core 는 win32 가 아닌 곳에서는 그냥 importlib 이라 맥에서도 같은 뜻이다.)
    # `windows/` 가 없는 체크아웃에서는 이 파일이 돌 수 없고, 그건 조용히 통과시키는
    # 것보다 임포트 에러로 드러나는 편이 맞다.
    from windows.win_core import import_core  # noqa: E402
    claude_pet = import_core()


T0 = datetime(2026, 9, 19, 3, 0, 0, tzinfo=timezone.utc)
CLI = "/Users/who/.local/bin/claude"


def _rec(**kw):
    base = claude_pet.new_recovery_state()
    base.update(kw)
    return base


def _tick(rec, now, **kw):
    """recovery_tick 인자 기본값 — 각 테스트는 바꿀 것만 준다.

    기본은 '토큰은 멀쩡하고 만료도 멀다' — 즉 아무 일도 없어야 하는 상태다.
    """
    args = dict(auth_error=False, token_sig="sig-A", cli_present=True, enabled=True,
                creds_have_oauth=True, expires_at=now + timedelta(hours=8))
    args.update(kw)
    return claude_pet.recovery_tick(rec, now, **args)


class QuietStateTests(unittest.TestCase):
    """아무 문제 없을 때는 아무것도 하지 않는다."""

    def test_healthy_token_far_from_expiry_does_nothing(self):
        rec, action = _tick(_rec(), T0)
        self.assertIsNone(action)
        self.assertEqual(rec["attempts"], 0)


class RefreshMarginTests(unittest.TestCase):
    """우리 마진은 CLI 보다 **늦어야** 한다 — 안 그러면 남의 일을 가로챈다.

    2026-09-20 윈도우 실측(n=1): Claude Code 세션이 **완전히 idle 인 상태에서도**
    만료 4.37분 전에 스스로 토큰을 갱신했다. 그 세션은 23:37 이후 입력도 API 호출도
    없었다. 새 expiresAt 은 파일을 쓴 시각 + 정확히 8시간이었고, refresh 토큰도
    회전했다(`bbfafecf3f37` → `beae7081dc9d`).

    4.37분은 5분 임계를 체크 주기만큼 늦게 지난 값으로 보인다 — 즉 CLI 의 마진도
    사실상 5분이고, 우리 마진이 같은 300초면 **둘이 같은 지점에서 경쟁한다.** 실제로
    우리가 38초 빨라서, Claude Code 가 떠 있는 사용자에게는 CLI 가 어차피 할 갱신을
    우리가 매번 가로채 Node 앱을 한 번씩 더 띄우게 된다(윈도우에선 최대 7프로세스).

    그래서 마진을 CLI 보다 작게 둔다. 그러면 CLI 가 있는 환경에서는 우리 차례가 올 때
    토큰이 이미 신선해 아무 일도 하지 않고, CLI 가 없는 환경에서만 우리가 뜬다.
    "살아 있는 claude 프로세스가 있으면 스폰하지 않는다"는 가드를 대신 두는 안도
    있었지만 기각했다 — 멈춘 CLI 가 복구를 영원히 막는 실패 모드를 만들고, 플랫폼마다
    프로세스 열거가 필요하다. 마진 하나로 같은 결과를 얻는다.

    n=1 이므로 CLI 마진을 300초로 **단정하지는 않는다.** 대신 우리 마진이 거기에
    닿지 않도록 여유를 둔다.
    """

    CLI_OBSERVED_MARGIN_SEC = 262    # 4.37분, 2026-09-20 윈도우 실측

    def test_our_margin_is_well_inside_the_clis(self):
        self.assertLess(
            claude_pet.REFRESH_MARGIN_SEC, self.CLI_OBSERVED_MARGIN_SEC,
            "CLI 가 만료 %d초 전에 스스로 갱신한다. 우리 마진이 그보다 이르면 "
            "Claude Code 를 쓰는 사용자에게 매번 불필요한 스폰이 생긴다."
            % self.CLI_OBSERVED_MARGIN_SEC)

    def test_the_margin_still_leaves_room_to_act_before_the_outage(self):
        """너무 줄이면 이미 만료된 뒤에야 움직여 사용자가 깨진 상태를 본다."""
        self.assertGreaterEqual(claude_pet.REFRESH_MARGIN_SEC, 30)


class ProactiveRefreshTests(unittest.TestCase):
    """만료 임박 갱신 — 애초에 만료되지 않게 한다."""

    def test_margin_boundary(self):
        """마진 밖은 조용, 안은 스폰. 이 쌍이 '주기적으로 띄우는' 구현을 걸러낸다."""
        rec, action = _tick(_rec(), T0,
                            expires_at=T0 + timedelta(seconds=claude_pet.REFRESH_MARGIN_SEC + 60))
        self.assertIsNone(action)
        rec, action = _tick(_rec(), T0,
                            expires_at=T0 + timedelta(seconds=claude_pet.REFRESH_MARGIN_SEC - 60))
        self.assertEqual(action, "spawn")

    def test_already_expired_also_spawns(self):
        _, action = _tick(_rec(), T0, expires_at=T0 - timedelta(minutes=1))
        self.assertEqual(action, "spawn")

    def test_it_does_not_respawn_on_every_tick_while_still_near_expiry(self):
        """30초 틱마다 Node 앱을 띄우면 그게 재앙이다."""
        rec, action = _tick(_rec(), T0, expires_at=T0 + timedelta(minutes=1))
        self.assertEqual(action, "spawn")
        rec2, action = _tick(rec, T0 + timedelta(seconds=30),
                             expires_at=T0 + timedelta(seconds=30))
        self.assertIsNone(action, "만료가 가깝다는 이유로 매 틱 스폰했다")

    def test_an_unknown_expiry_is_not_treated_as_expired(self):
        """expiresAt 을 못 읽었을 때 만료로 단정하면 기동 직후마다 띄운다."""
        _, action = _tick(_rec(), T0, expires_at=None)
        self.assertIsNone(action)


class ReactiveRecoveryTests(unittest.TestCase):
    """그래도 거부당했을 때 — 3회 / 즉시·+5분·+15분(첫 시도 기준)."""

    def test_auth_error_spawns_immediately(self):
        rec, action = _tick(_rec(), T0, auth_error=True)
        self.assertEqual(action, "spawn")
        self.assertEqual(rec["attempts"], 1)

    def test_second_attempt_waits_five_minutes(self):
        rec, _ = _tick(_rec(), T0, auth_error=True)
        rec2, action = _tick(rec, T0 + timedelta(minutes=4, seconds=59), auth_error=True)
        self.assertIsNone(action)
        rec3, action = _tick(rec2, T0 + timedelta(minutes=5), auth_error=True)
        self.assertEqual(action, "spawn")
        self.assertEqual(rec3["attempts"], 2)

    def test_third_attempt_is_fifteen_minutes_from_the_first(self):
        rec, _ = _tick(_rec(), T0, auth_error=True)
        rec, _ = _tick(rec, T0 + timedelta(minutes=5), auth_error=True)
        rec2, action = _tick(rec, T0 + timedelta(minutes=14, seconds=59), auth_error=True)
        self.assertIsNone(action)
        rec3, action = _tick(rec2, T0 + timedelta(minutes=15), auth_error=True)
        self.assertEqual(action, "spawn")
        self.assertEqual(rec3["attempts"], 3)

    def test_fourth_tick_gives_up(self):
        rec = _rec()
        for at in (0, 5, 15):
            rec, action = _tick(rec, T0 + timedelta(minutes=at), auth_error=True)
            self.assertEqual(action, "spawn")
        rec, action = _tick(rec, T0 + timedelta(minutes=30), auth_error=True)
        self.assertEqual(action, "giveup")
        self.assertTrue(rec["gave_up"])

    def test_giving_up_never_spawns_again_on_the_same_token(self):
        rec = _rec()
        for at in (0, 5, 15):
            rec, _ = _tick(rec, T0 + timedelta(minutes=at), auth_error=True)
        rec, _ = _tick(rec, T0 + timedelta(minutes=30), auth_error=True)
        for at in (31, 45, 60, 120, 600):
            rec, action = _tick(rec, T0 + timedelta(minutes=at), auth_error=True)
            self.assertIsNone(action, "%d분 뒤에 다시 스폰했다" % at)


class RecoveryResetTests(unittest.TestCase):
    """성공·토큰 교체·재시작이 사이클을 푸는 세 경로."""

    def test_success_resets_the_counter(self):
        rec, _ = _tick(_rec(), T0, auth_error=True)
        rec, action = _tick(rec, T0 + timedelta(minutes=5), auth_error=False)
        self.assertIsNone(action)
        self.assertEqual(rec["attempts"], 0)
        self.assertFalse(rec["gave_up"])

    def test_a_changed_token_reopens_the_cycle_after_giving_up(self):
        rec = _rec()
        for at in (0, 5, 15):
            rec, _ = _tick(rec, T0 + timedelta(minutes=at), auth_error=True)
        rec, _ = _tick(rec, T0 + timedelta(minutes=30), auth_error=True)
        self.assertTrue(rec["gave_up"])
        _, action = _tick(rec, T0 + timedelta(minutes=40), auth_error=True)
        self.assertIsNone(action)
        rec_new, action = _tick(rec, T0 + timedelta(minutes=40), auth_error=True,
                                token_sig="sig-B")
        self.assertEqual(action, "spawn")
        self.assertFalse(rec_new["gave_up"])

    def test_a_fresh_state_after_restart_may_try_again(self):
        fresh = claude_pet.new_recovery_state()
        self.assertEqual(fresh["attempts"], 0)
        self.assertFalse(fresh["gave_up"])


class SpawnGuardTests(unittest.TestCase):
    """스폰하면 안 되는 조건들."""

    def test_disabled_setting_never_spawns(self):
        rec, action = _tick(_rec(), T0, auth_error=True, enabled=False)
        self.assertIsNone(action)
        self.assertEqual(rec["attempts"], 0)

    def test_missing_cli_defers_to_onboarding(self):
        rec, action = _tick(_rec(), T0, auth_error=True, cli_present=False)
        self.assertEqual(action, "onboard_install")
        self.assertEqual(rec["attempts"], 0)

    def test_credentials_without_claude_oauth_never_spawn(self):
        """CodexBar PR #1848 의 함정 — MCP OAuth 상태만 있으면 브라우저가 떠버린다.

        갱신할 대상이 없는 상태이기도 하다. fail-closed 로 막는다.
        """
        rec, action = _tick(_rec(), T0, auth_error=True, creds_have_oauth=False)
        self.assertIsNone(action, "claudeAiOauth 가 없는데 CLI 를 띄웠다")
        rec, action = _tick(_rec(), T0, creds_have_oauth=False,
                            expires_at=T0 - timedelta(minutes=1))
        self.assertIsNone(action, "선제 갱신 경로에도 같은 가드가 필요하다")


class ReadOnlyPrincipleTests(unittest.TestCase):
    """관찰자는 남의 자격증명을 쓰지 않는다 — 실패가 재로그인으로 튀지 않게."""

    def _recovery_sources(self):
        names = ("recovery_tick", "recovery_spawn_argv", "new_recovery_state",
                 "recovery_note_output")
        return "\n".join(inspect.getsource(getattr(claude_pet, n)) for n in names)

    def test_recovery_never_calls_the_oauth_token_endpoint(self):
        """자가 갱신 금지. 회전된 refresh 토큰을 되쓸 수 없는 쪽이 갱신하면 안 된다."""
        src = self._recovery_sources()
        self.assertNotIn("oauth/token", src)
        self.assertNotIn("refresh_token", src)

    def test_recovery_never_writes_to_the_keychain(self):
        src = self._recovery_sources()
        self.assertNotIn("add-generic-password", src)

    def test_recovery_never_writes_the_credentials_file(self):
        src = self._recovery_sources()
        for w in ("credentials.json", "_credentials_path"):
            self.assertNotIn(w, src)


class SpawnShapeTests(unittest.TestCase):
    """2026-07-13 재발 방지 + 조용함. 메커니즘은 고르지 않는다.

    **플랫폼을 가르지 않는다.** macOS 에서 되는 것은 Windows 에서도 똑같이 돼야
    한다는 것이 이 프로젝트의 원칙이고, 그건 테스트 커버리지에도 적용된다. 한때
    이 클래스를 "근거가 TCC 이니 macOS 전용"으로 좁히자는 안이 있었는데 그건
    **윈도우가 이 보호를 영영 못 받게 만드는** 선택이라 기각했다. 간접화의 이유는
    플랫폼마다 다를 수 있어도(맥은 TCC 귀속, 윈도우는 창·고아 트리 통제),
    "우리 자손으로 CLI 를 띄우지 않는다"는 성질 자체는 양쪽 공통이다.

    구현은 `sys.platform` 을 함수 안에서 읽으므로 여기서 패치해 양쪽을 다 본다.
    """

    def argv_on(self, platform, fn="recovery_spawn_argv"):
        with mock.patch.object(claude_pet.sys, "platform", platform):
            return [str(a) for a in getattr(claude_pet, fn)(CLI)]

    def test_spawn_is_not_a_direct_child_invocation_on_every_platform(self):
        for plat in ("darwin", "win32"):
            with self.subTest(platform=plat):
                argv = self.argv_on(plat)
                self.assertTrue(argv)
                base = os.path.basename(argv[0]).lower()
                self.assertNotIn(
                    base, ("claude", "claude.exe", "claude.cmd", "claude.bat"),
                    "%s: claude 를 직계 자식으로 띄우면 안 된다. macOS 에서는 보호폴더 "
                    "접근이 ClaudePet 에 귀속되고(2026-07-13 TCC 거부 8건, 커밋 "
                    "67849e4), 어느 쪽이든 타임아웃 때 정리해야 할 트리가 우리 밑에 "
                    "매달린다 — 윈도우는 부모가 죽어도 자식이 살아남아 고아가 된다."
                    % plat)

    def test_login_is_not_a_direct_child_invocation_on_every_platform(self):
        for plat in ("darwin", "win32"):
            with self.subTest(platform=plat):
                base = os.path.basename(self.argv_on(plat, "login_spawn_argv")[0]).lower()
                self.assertNotIn(base, ("claude", "claude.exe", "claude.cmd", "claude.bat"))

    def test_spawn_never_opens_a_terminal_window(self):
        for plat in ("darwin", "win32"):
            with self.subTest(platform=plat):
                argv = self.argv_on(plat)
                self.assertNotIn("Terminal", " ".join(argv))
                self.assertFalse(any(a.endswith(".command") for a in argv))

    def test_windows_suppresses_the_console_window(self):
        """플래그 없이 띄우면 창이 실제로 뜬다 — 윈도우 실측 양성 대조군 2/2.

        `CREATE_NO_WINDOW`(0x08000000) 3/3 과 `DETACHED_PROCESS` 3/3 이 창 0개였고,
        콘솔이 아예 없어지는 후자보다 전자를 택했다. 자식 트리가 한 번에 최대 7개
        (claude.exe + bash.exe×3 + conhost×2 + cmd.exe)라 그 conhost 창까지 같이
        막아야 한다.
        """
        with mock.patch.object(claude_pet.sys, "platform", "win32"):
            self.assertEqual(claude_pet._spawn_no_window_flags(), 0x08000000)
        with mock.patch.object(claude_pet.sys, "platform", "darwin"):
            self.assertEqual(claude_pet._spawn_no_window_flags(), 0)

    def test_the_usage_subcommand_is_still_what_runs(self):
        for plat in ("darwin", "win32"):
            with self.subTest(platform=plat):
                argv = self.argv_on(plat)
                self.assertIn(CLI, argv, "절대경로가 그대로 전달돼야 한다")
                self.assertIn("-p", argv)
                self.assertIn("/usage", argv)

    def test_recovery_does_not_reuse_the_opt_in_cli_usage_path(self):
        """_fetch_cli_usage() 는 출력을 쓰려는 경로고 CLAUDE_PET_USE_CLI 뒤에 있다.

        복구의 목적은 갱신이라는 부수효과다. 그 게이트에 묶이면 기본 OFF 설정이
        복구까지 꺼버린다.

        (파서 자체는 멀쩡하다 — 2026-09-19 재측정에서 `_fetch_cli_usage()` 가
        세션 3.0 / 주간 1.0 / Fable 0.0 을 정상 반환했다. 한때 수치 줄이 안 보였던
        것은 그 시간대에 usage API 가 429 였기 때문이고, 그때 CLI 는 할당량 줄 없이
        로컬 통계만 출력한다. 그래서 CLI 수치는 OAuth API 보다 신뢰도가 낮다 —
        조용히 사라진다. 수치 경로를 CLI 로 바꾸지 않는 이유는 이것이다.)
        """
        self.assertNotIn("_fetch_cli_usage",
                         inspect.getsource(claude_pet.recovery_spawn_argv))

    def test_the_attempt_is_bounded_by_a_timeout(self):
        """붙어서 안 끝나는 자식이 남으면 다음 시도를 영원히 막는다."""
        self.assertIsInstance(claude_pet.RECOVERY_TIMEOUT_SEC, (int, float))
        self.assertGreater(claude_pet.RECOVERY_TIMEOUT_SEC, 0)
        self.assertLessEqual(claude_pet.RECOVERY_TIMEOUT_SEC, 300)


class WindowsDetachmentTests(unittest.TestCase):
    """argv 검사만으로는 분리가 증명되지 않는다 — 그 구멍을 막는다.

    **이 클래스는 구현 이후에 추가됐고 처음부터 초록이었다.** 게이트가 아니라
    회귀 가드다. 그렇게 된 경위를 적어 둔다: 원래 계약은 `argv[0]` 이 claude 가
    아니면 됐는데, 윈도우 구현이 `cmd.exe /c claude …` 를 돌려주므로 그 조건은
    **직계 자식으로 띄워도 만족된다**(그러면 claude 는 손자일 뿐 여전히 우리
    트리다). 실제 분리는 argv 가 아니라 실행 경로가 WMI 를 타는 데서 온다.
    검증하다 그 틈을 발견해 여기서 닫는다.
    """

    def _run_win32(self, wmi_pid=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            io_paths = (os.path.join(td, "o.txt"), os.path.join(td, "e.txt"))
            with mock.patch.object(claude_pet.sys, "platform", "win32"), \
                 mock.patch.object(claude_pet, "_recovery_io_paths",
                                   return_value=io_paths), \
                 mock.patch.object(claude_pet, "_win_wmi_create",
                                   return_value=wmi_pid) as wmi, \
                 mock.patch.object(claude_pet.subprocess, "Popen") as popen, \
                 mock.patch.object(claude_pet.subprocess, "run") as run:
                claude_pet._run_refresh_job([CLI, "-p", "/usage"], "lbl", "stem", 1)
            return wmi, popen, run

    def test_the_windows_spawn_goes_through_wmi(self):
        wmi, _, _ = self._run_win32()
        self.assertTrue(wmi.called, "WMI 를 거치지 않았다 — 분리가 일어나지 않는다")

    def test_the_windows_spawn_is_never_a_direct_child(self):
        """여기서 Popen 이 불리면 claude 가 우리 트리 안에서 돌고 있다는 뜻이다."""
        _, popen, run = self._run_win32()
        self.assertFalse(popen.called, "subprocess.Popen 으로 직계 자식을 띄웠다")
        for call in run.call_args_list:
            argv = call.args[0] if call.args else []
            joined = " ".join(str(a) for a in argv)
            self.assertNotIn("-p /usage", joined,
                             "subprocess.run 으로 CLI 를 직접 돌렸다")

    def test_the_command_line_carries_the_cli_and_its_redirection(self):
        wmi, _, _ = self._run_win32()
        cmdline = wmi.call_args.args[0]
        self.assertIn(CLI, cmdline)
        self.assertIn("/usage", cmdline)
        self.assertIn("2>&1", cmdline, "출력을 받지 못하면 결과를 읽을 수 없다")


class LoginExpiredShortCircuitTests(unittest.TestCase):
    """refresh 토큰까지 죽었으면 남은 시도는 의미가 없다."""

    def test_login_expired_output_is_recognized(self):
        self.assertTrue(claude_pet.cli_says_login_expired(
            "Login expired · Please run /login"))

    def test_ordinary_usage_output_is_not_mistaken_for_it(self):
        self.assertFalse(claude_pet.cli_says_login_expired(
            "Last 7d · 2838 requests · 3 sessions"))

    def test_the_word_login_alone_is_not_enough(self):
        """부분일치 구현을 걸러내는 쌍."""
        self.assertFalse(claude_pet.cli_says_login_expired(
            "Run /login to switch accounts."))

    def test_detection_skips_the_remaining_attempts(self):
        rec, _ = _tick(_rec(), T0, auth_error=True)
        rec = claude_pet.recovery_note_output(rec, "Login expired · Please run /login")
        rec2, action = _tick(rec, T0 + timedelta(minutes=5), auth_error=True)
        self.assertIsNone(action, "만료가 확인됐는데도 또 띄웠다")
        self.assertTrue(rec2["gave_up"])


class LoginSpawnTests(unittest.TestCase):
    """로그인도 터미널 없이 — 창 대신 브라우저가 뜨고, CLI 가 알아서 끝낸다.

    2026-09-19 실측(claude 2.1.271): `claude auth login --claudeai` 를 stdin 에
    아무것도 쓰지 않고 제어 터미널 없이 띄웠더니 **21초 만에 스스로 exit 0** 했고,
    새 토큰을 CLI 가 직접 저장소에 써넣었다(expiresAt·refresh 지문 모두 교체). 출력의
    `Paste code here if prompted >` 는 말 그대로 폴백 줄이고, 원격 콜백이 먼저 끝나
    같은 줄에 `Login successful.` 이 이어졌다. 즉 붙여넣기 UI 는 필요 없다.

    여기서도 우리가 자격증명을 쓰지 않는다는 원칙은 같다 — 쓰는 쪽은 CLI 다.
    """

    def test_login_is_fired_in_the_background_not_in_a_terminal(self):
        argv = [str(a) for a in claude_pet.login_spawn_argv(CLI)]
        self.assertNotIn("Terminal", " ".join(argv))
        self.assertFalse(any(a.endswith(".command") for a in argv))

    def test_login_runs_the_auth_login_subcommand(self):
        argv = [str(a) for a in claude_pet.login_spawn_argv(CLI)]
        self.assertIn("auth", argv)
        self.assertIn("login", argv)

    def test_login_picks_the_subscription_flow_explicitly(self):
        """--claudeai 를 명시해 대화형 선택 화면을 만들지 않는다.

        TTY 가 없으므로 고르라는 화면이 뜨면 거기서 멈춘다 — 사용자는 눌렀는데
        아무 일도 안 일어난 것으로 보인다.
        """
        self.assertIn("--claudeai", [str(a) for a in claude_pet.login_spawn_argv(CLI)])

    def test_login_does_not_go_through_the_terminal_helper(self):
        self.assertNotIn("_run_in_terminal",
                         inspect.getsource(claude_pet.login_spawn_argv))

    def test_the_login_attempt_is_bounded(self):
        """실측 21초. 사용자가 브라우저에서 꾸물대도 영원히 매달려 있으면 안 된다."""
        self.assertIsInstance(claude_pet.LOGIN_TIMEOUT_SEC, (int, float))
        self.assertGreaterEqual(claude_pet.LOGIN_TIMEOUT_SEC, 60)
        self.assertLessEqual(claude_pet.LOGIN_TIMEOUT_SEC, 300)


class PillClickTests(unittest.TestCase):
    """포기했을 때 사용자가 할 수 있는 것 — 필 클릭.

    기존 상호작용(더블클릭=즉시갱신 / 접기 버튼 / 드래그)을 깨지 않는다.
    """

    def act(self, **kw):
        args = dict(status_key="onb_login", in_pill=True, click_count=1, moved=False)
        args.update(kw)
        return claude_pet.summary_click_action(**args)

    def test_single_click_on_login_status_opens_login(self):
        self.assertEqual(self.act(), "login")

    def test_single_click_on_install_status_opens_install(self):
        self.assertEqual(self.act(status_key="onb_install"), "install")

    def test_single_click_on_token_expired_retries_recovery(self):
        self.assertEqual(self.act(status_key="token_expired"), "recover")

    def test_double_click_still_belongs_to_refresh(self):
        self.assertIsNone(self.act(click_count=2))

    def test_a_drag_is_not_a_click(self):
        self.assertIsNone(self.act(moved=True))

    def test_click_outside_the_pill_does_nothing(self):
        self.assertIsNone(self.act(in_pill=False))

    def test_non_status_segments_are_not_clickable(self):
        """`need_admin_key` 는 이 목록에서 빠졌다 — 낡은 항목이었다.

        이 목록을 처음 쓸 때 `need_admin_key` 는 아무 동작도 없는 문구였다. 그 뒤
        API 모드 작업에서 그 문구가 "설정에서 키를 확인하세요" 라고 행동을 지시하게
        됐고, 지시해 놓고 클릭이 죽어 있으면 그건 안내가 아니다. 그래서 지금은
        `test_api_cost_status.SettingsAreReachableFromTheMessageTests` 가 그 키를
        `"settings"` 로 고정한다. 두 파일이 같은 함수의 같은 입력을 정반대로 요구하고
        있었고, 새 쪽이 사용자 결정을 담고 있으므로 이쪽을 뺀다.

        나머지는 그대로 — 수치가 보이는 동안의 클릭이 로그인이나 설정을 띄우면 안 된다.
        """
        for key in (None, "", "loading", "scanning"):
            self.assertIsNone(self.act(status_key=key), "status_key=%r" % key)


class RecoverySettingTests(unittest.TestCase):
    """설정 토글 하나. 기존 설정 트랜잭션 계약은 건드리지 않는다."""

    def test_runtime_carries_the_toggle(self):
        self.assertIn("auto_recover", claude_pet.RUNTIME)
        self.assertIsInstance(claude_pet.RUNTIME["auto_recover"], bool)

    def test_the_key_is_settings_owned_so_a_save_round_trips_it(self):
        self.assertIn("auto_recover", claude_pet.SETTINGS_OWNED_KEYS)


def _source_tree():
    return ast.parse(
        (pathlib.Path(claude_pet.__file__)).read_text(encoding="utf-8"),
        filename="claude_pet.py")


def _find_func(name):
    for node in ast.walk(_source_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


class AutoRecoverMenuTests(unittest.TestCase):
    """사용자가 끌 수 있어야 한다 — config 파일만으로는 끌 수 있는 게 아니다.

    설정 패널은 고정 높이(본문 612, 상한 656)라 항목을 더 넣을 자리가 없다. 그래서
    'Start at sign-in' 과 'Roam the screen' 이 그랬듯 **우클릭 메뉴의 체크 항목**으로
    간다. 이 클래스는 그 패턴(4개 로케일 TR 키 + 메뉴 배선 + 핸들러)을 autostart 와
    같은 모양으로 고정한다.
    """

    KEY = "menu_auto_recover"

    def test_the_menu_title_exists_in_every_locale(self):
        for lang in ("en", "ko", "ja", "es"):
            with self.subTest(lang=lang):
                title = claude_pet.TR[lang].get(self.KEY)
                self.assertIsInstance(title, str, "%s 에 %s 없음" % (lang, self.KEY))
                self.assertTrue(0 < len(title) <= claude_pet.MENU_TITLE_MAX,
                                "메뉴 제목 길이 초과: %r" % title)

    def test_the_title_is_translated_not_pasted(self):
        """영어를 ko/ja/es 에 그대로 붙여 넣으면 t() 의 폴백을 통과해 버린다."""
        en = claude_pet.TR["en"][self.KEY]
        same = [l for l in ("ko", "ja", "es") if claude_pet.TR[l].get(self.KEY) == en]
        self.assertEqual(same, [], "번역되지 않은 로케일: %s" % same)

    def test_the_menu_wires_the_item_to_a_handler(self):
        """제목만 있고 핸들러가 없으면 눌러도 아무 일도 안 일어난다."""
        fn = _find_func("rightMouseDown_")
        self.assertIsNotNone(fn, "rightMouseDown_ 을 찾지 못했다")
        src = ast.dump(fn)
        self.assertIn(self.KEY, src, "메뉴가 %s 를 쓰지 않는다" % self.KEY)
        self.assertIn("toggleAutoRecover:", src, "액션이 배선되지 않았다")

    def test_the_handler_exists(self):
        self.assertIsNotNone(_find_func("toggleAutoRecover_"),
                             "Handler.toggleAutoRecover_ 가 없다")

    def test_the_handler_persists_the_choice(self):
        """껐는데 재시작하면 다시 켜져 있으면 끈 게 아니다."""
        fn = _find_func("toggleAutoRecover_")
        self.assertIsNotNone(fn)
        src = ast.dump(fn)
        self.assertIn("auto_recover", src)
        self.assertIn("merge_config_updates", src,
                      "선택이 ~/.claude_pet.json 에 저장되지 않는다")


class RoamSummaryRegressionTests(unittest.TestCase):
    """복구가 붙어도 PR #9 의 필 계약은 그대로다."""

    def test_token_expired_still_requires_both_no_data_and_auth_error(self):
        """**NOT A GATE** — 회귀 가드다. 이 파일에서 유일하게 작성 시점에 초록이었고,
        그래야 맞다. PR #9 이 이미 건 계약(entries==0 AND auth_error)을 복구 기능이
        무너뜨리지 않는지만 본다.
        """
        stats = {"entries": 0, "session": {"pct": 0.0}, "weekly": {"pct": 0.0},
                 "opus": {"pct": 0.0}, "spikes": {}, "model_kw": "fable"}
        seg = claude_pet.roam_summary("sub", None, stats, None, 0, False, None,
                                      auth_error=True)
        self.assertEqual(seg, ("status", "token_expired"))
        seg = claude_pet.roam_summary("sub", None, dict(stats, entries=5), None, 0,
                                      False, None, auth_error=True)
        self.assertNotEqual(seg[0], "status")


if __name__ == "__main__":
    unittest.main()
