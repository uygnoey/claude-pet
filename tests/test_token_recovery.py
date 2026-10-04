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

── 2026-09-30 개정: macOS 에서는 메커니즘까지 고정한다 (cwdfix, Verifier) ────────

위에서 "spawn 방식은 고르지 않는다"고 적었다. 그 판단이 틀렸던 자리가 드러났다 —
"보호폴더 프롬프트가 뜨지 않는다"는 성질은 **CLI 가 누구의 자손인가만이 아니라 launchd 가
그 job 을 어떻게 돌리는가**에 달려 있었다. 세 칸(AGENTS.md §5)을 섞지 않고 적는다.

* 소스에서 읽히는 사실(관측이 아니다): v0.26 은 `launchctl submit` 을 썼다. `man
  launchctl` 의 submit 은 "keep the program alive in the event of failure" 라고만 적고 작업
  디렉터리 옵션이 없다 — 그래서 CLI 는 launchd 의 기본 cwd 인 `/` 에서 돈다.
* 관측(Coordinator 가 2026-09-30 09:05–09:31 KST 에 수집, 이 맥 한 대, CLI 2.1.284 —
  cwdfix 스펙의 Evidence 절; 횟수는 Verifier 가 같은 launchd 로그에서 다시 셌다): 06:15 의
  시도 한 번에서 launchd 가 CLI 를 세 번 띄웠다 — 06:15:29, 06:16:17, 06:17:05(마지막 것은
  06:17:36 에 job 이 내려질 때 아직 돌고 있었다). 실패할 때만이 아니다: exit 0 으로 끝난
  submit job 도 다시 떴다 — Developer 의 프로브에서 `/usr/bin/true` 를 올린 job 이 24초 동안
  1→2→3번 실행됐다(2026-09-30). Reviewer 의 프로브는 exit 0 뒤 job 이 "spawn scheduled" 로
  넘어가는 것까지만 봤고, 실제 두 번째 실행은 관측하지 않았다. tccd 로그 2026-09-30
  05:28–06:52 KST 의 AUTHREQ_PROMPTING 14건은 전부 그 job 이 띄운 PID 7개에서 나왔고
  책임 프로세스는 ClaudePet 이 아니라 CLI 자신이었다. 통제 실행(09:24–09:30 KST) 3회
  중 cwd 가 빈 사설 폴더일 때는 TCC 요청 0건, cwd `/` 일 때는 5초 안에 ~/Music·
  ~/Pictures·/Volumes 등을 읽으려 했다. 이것은 그 표본의 사실이고 그 이상을 말하지 않는다.
* 그래서 코드가 해야 하는 것: CLI 는 **사설 cwd**(`recovery_cli_cwd()`)에서, 시도마다
  **한 번만** 돈다 — launchd 에 `bootstrap` 으로 넘기는 원샷 job(`WorkingDirectory`,
  `RunAtLoad` true, keep-alive 없음), 앞뒤와 마감 경로에서 `bootout`.
* 모르는 것: 사설 cwd 에서 **실제 토큰 갱신이 일어나는** 실행은 직접 관측되지 않았다
  (강제할 수 없다). 앞으로의 CLI 가 cwd 와 무관하게 보호 위치를 읽을 가능성도 이 테스트가
  막지 못한다 — 여기서 고정하는 것은 우리 쪽이 줄 수 있는 조건까지다.

아래 `DarwinOneShotJobTests` 이하가 그 계약이다. 실제 launchctl·CLI·WMI 는 절대 돌리지
않고, 캐시 폴더는 임시 폴더로 돌린다. 이 파일은 윈도우 CI 에서도 돌므로 darwin 경로를
윈도우에서 돌릴 때 필요한 POSIX 전용 속성(os.getuid 등)은 하네스가 채운다.
"""

import ast
import contextlib
import errno
import inspect
import os
import pathlib
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import time
import types
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


# ── darwin 원샷 job 하네스 (2026-09-30, cwdfix) ─────────────────────────────────────
#
# `_run_refresh_job` 의 darwin 경로를 **아무것도 실제로 띄우지 않고** 끝까지 돌린다.
# subprocess.run 은 launchd 의 상태 하나(그 라벨이 올라가 있는가)만 흉내 내는 대역이고,
# bootstrap 이 불리는 **그 순간** job 정의(plist)를 읽어 둔다 — 구현이 곧바로 지우기
# 때문이다. 캐시 폴더는 임시 폴더다. 대역은 임시 폴더 밖에는 아무것도 쓰지 않는다.

PROBE_LABEL = "me.yeongyu.claudepet.probe-verify"   # 앱의 라벨이 아니다
PROBE_UID = 4242      # 501 을 박아 넣은 구현을 가르려고 일부러 흔치 않은 값을 쓴다
CLI_WITH_SPACE = "/Users/who/Library/Application Support/claude/versions/9.9.9/claude"
# 가짜 job 은 출력을 두 번에 나눠 쓴다: launchd 가 띄울 때 앞부분, **끝났을 때** 뒷부분.
# 끝나기 전에 bootout 하면(= CLI 를 도중에 죽이면) 뒷부분이 없다 — 그래서 '끝나기를 기다리지
# 않는' 구현(폴링 조건을 뒤집은 것 등)이 결과 문자열에서 드러난다.
JOB_OUT_BEGIN, JOB_OUT_END = "job-stdout-begin|", "job-stdout-end|"
JOB_ERR_BEGIN, JOB_ERR_END = "job-stderr-begin|", "job-stderr-end|"
JOB_FULL = JOB_OUT_BEGIN + JOB_OUT_END + JOB_ERR_BEGIN + JOB_ERR_END   # 끝까지 돈 job
JOB_KILLED = JOB_OUT_BEGIN + JOB_ERR_BEGIN                             # 도중에 내려진 job
STALE = "STALE-FROM-LAST-RUN|"
# 실제 launchctl 의 반환값. 올라가 있지 않은 서비스를 bootout 하면 113("Could not find
# specified service"), 같은 라벨이 이미 있는데 bootstrap 하면 5("Input/output error").
BOOTOUT_NOT_FOUND_RC = 113
BOOTSTRAP_IO_ERROR_RC = 5
# 이 키가 있으면 launchd 가 job 을 다시 띄운다 — '시도마다 한 번' 과 양립하지 않는다.
RELAUNCH_KEYS = frozenset({"StartInterval", "StartCalendarInterval", "WatchPaths",
                           "QueueDirectories", "StartOnMount", "Sockets", "MachServices",
                           "LaunchEvents"})
# macOS 가 사용자 동의(TCC)를 요구하는 자리 — 2026-09-30 통제 실행에서 cwd `/` 의 CLI 가
# 건드린 곳(~/Music, ~/Pictures, ~/Documents 아래, /Volumes)과 표준 보호 폴더들.
TCC_PROTECTED_UNDER_HOME = (
    ("Desktop",), ("Documents",), ("Downloads",), ("Music",), ("Pictures",), ("Movies",),
    ("Library", "Mobile Documents"), ("Library", "CloudStorage"),
    ("Library", "Containers"), ("Library", "Group Containers"),
)


def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def _is_under(p, root):
    return _norm(p).startswith(_norm(root) + os.sep)


def _parts(p):
    return [x for x in _norm(p).replace("\\", "/").split("/") if x]


def _is_ancestor_or_equal(a, b):
    """a 가 b 이거나 b 의 조상인가. `/` 는 모든 경로의 조상이다."""
    pa = _parts(a)
    return _parts(b)[:len(pa)] == pa


class _Clock:
    """가짜 시계. sleep 이 시간을 흘려보내므로 마감 경로도 즉시 끝난다."""

    LIMIT = 500

    def __init__(self, events):
        self.t = 1_800_000_000.0
        self.sleeps = []
        self.events = events

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.events.append(("sleep", seconds, self.t))
        if len(self.sleeps) > self.LIMIT:
            raise AssertionError("폴링이 끝나지 않는다 — 마감이 시계를 따르지 않거나 간격이 0 이다")
        self.t += max(0.0, float(seconds))


class _TimeProxy:
    """claude_pet 안의 `time` 만 바꾼다. 전역 time 모듈은 건드리지 않는다."""

    def __init__(self, clock):
        self._clock = clock

    def time(self):
        return self._clock.now()

    def monotonic(self):
        return self._clock.now()

    def perf_counter(self):
        return self._clock.now()

    def sleep(self, seconds):
        self._clock.sleep(seconds)

    def __getattr__(self, name):
        return getattr(time, name)


class _FakeLaunchd:
    """subprocess.run 대역. 무엇을 불렀는지 기록하고, 아무것도 실행하지 않는다.

    이벤트는 (종류, 내용, 가짜 시계 시각[, 값]) 이다 — 마감 테스트가 '언제' 내렸는지 본다.
    """

    def __init__(self, cache, label, uid, io_paths, events, clock, *, stale_job=False,
                 bootstrap_rc=0, bootstrap_raises=False):
        self.cache = cache
        self.label = label
        self.uid = uid
        self.io_paths = io_paths
        self.events = events
        self.clock = clock
        self.loaded = bool(stale_job)
        self.bootstrap_rc = bootstrap_rc
        self.bootstrap_raises = bootstrap_raises
        self.runs = []
        self.snapshots = []
        self.job_paths = {}        # 우리가 올린 job 의 출력 파일(임시 폴더 안일 때만)
        self.finished = False

    def __call__(self, args, *a, **kw):
        argv = [str(x) for x in args] if isinstance(args, (list, tuple)) else [str(args)]
        self.runs.append((argv, dict(kw)))
        self.events.append(("run", argv, self.clock.now()))
        textual = bool(kw.get("text") or kw.get("universal_newlines") or kw.get("encoding"))

        def done(rc, err=""):
            out = "" if textual else b""
            result = subprocess.CompletedProcess(argv, rc, out, err if textual else err.encode())
            if kw.get("check") and rc:
                raise subprocess.CalledProcessError(rc, argv, out, result.stderr)
            return result

        if argv[:2] == [claude_pet.LAUNCHCTL, "bootstrap"]:
            snap = self._snapshot(argv)
            self.snapshots.append(snap)
            if self.bootstrap_raises:
                # 메시지에 plist 경로가 들어 있다 — 예외를 통째로 _dbg 에 넘기면 경로가 샌다.
                raise OSError(errno.EIO, "Input/output error", argv[-1])
            if self.loaded:
                return done(BOOTSTRAP_IO_ERROR_RC, "Bootstrap failed: 5: Input/output error\n")
            if self.bootstrap_rc:
                return done(self.bootstrap_rc, "Bootstrap failed\n")
            self.loaded = True
            self._run_the_job(snap)
            return done(0)
        if argv[:2] == [claude_pet.LAUNCHCTL, "bootout"]:
            if argv[2:] == ["gui/%d/%s" % (self.uid, self.label)] and self.loaded:
                self.loaded = False
                return done(0)
            return done(BOOTOUT_NOT_FOUND_RC,
                        "Boot-out failed: 113: Could not find specified service\n")
        return done(0)

    def _snapshot(self, argv):
        path = argv[-1]
        snap = {"argv": argv, "plist": None, "mode": None, "wd_isdir": False,
                "wd_mode": None, "stale": {}}
        try:
            with open(path, "rb") as f:
                snap["plist"] = plistlib.load(f)
            snap["mode"] = stat.S_IMODE(os.stat(path).st_mode)
        except Exception as e:          # launchd 도 못 읽는 정의다
            snap["error"] = type(e).__name__
        job = snap["plist"] if isinstance(snap["plist"], dict) else {}
        wd = job.get("WorkingDirectory")
        if isinstance(wd, str) and os.path.isdir(wd):
            snap["wd_isdir"] = True
            snap["wd_mode"] = stat.S_IMODE(os.stat(wd).st_mode)
        for p in self.io_paths:
            snap["stale"][p] = os.path.exists(p)
        return snap

    def _run_the_job(self, snap):
        """RunAtLoad 로 뜬 job 이 출력의 앞부분을 남긴다. launchd 처럼 이어 쓴다. 임시 폴더 안에만."""
        job = snap["plist"] if isinstance(snap["plist"], dict) else {}
        for key in ("StandardOutPath", "StandardErrorPath"):
            p = job.get(key)
            if (isinstance(p, str) and os.path.isabs(p)
                    and _norm(os.path.dirname(p)) == _norm(self.cache)):
                self.job_paths[key] = p
        self._write({"StandardOutPath": JOB_OUT_BEGIN, "StandardErrorPath": JOB_ERR_BEGIN})

    def finish(self):
        """job 이 스스로 끝났다 — 뒷부분을 쓴다. 이미 내려졌거나 끝났으면 아무 일도 없다."""
        if self.loaded and not self.finished:
            self.finished = True
            self._write({"StandardOutPath": JOB_OUT_END, "StandardErrorPath": JOB_ERR_END})

    def _write(self, texts):
        for key, text in texts.items():
            p = self.job_paths.get(key)
            if p:
                with open(p, "a", encoding="utf-8") as f:
                    f.write(text)


class _InlineThread:
    """threading.Thread 대역 — start() 가 그 자리에서 끝까지 돈다."""

    def __init__(self, target=None, args=(), kwargs=None, **_):
        self._call = (target, args, kwargs or {})

    def start(self):
        target, args, kwargs = self._call
        target(*args, **kwargs)


def _posix_shims(stack):
    """darwin 경로를 윈도우 CI 에서 돌릴 때 없는 POSIX 속성을 채운다(맥에서는 getuid 만 바꾼다)."""
    stack.enter_context(mock.patch.object(claude_pet.os, "getuid",
                                          return_value=PROBE_UID, create=True))
    if not hasattr(os, "geteuid"):
        stack.enter_context(mock.patch.object(os, "geteuid",
                                              return_value=PROBE_UID, create=True))
    for flag in ("O_NOFOLLOW", "O_CLOEXEC", "O_DIRECTORY"):
        if not hasattr(os, flag):
            stack.enter_context(mock.patch.object(os, flag, 0, create=True))


def _run_darwin_job(test, *, argv=None, label=PROBE_LABEL, stem="probe-stem", timeout=10,
                    alive=(True, False), stale_job=False, bootstrap_rc=0,
                    bootstrap_raises=False, stale_output=False, cache_is_a_file=False,
                    cwd_is_a_file=False, call=None):
    """darwin 경로를 한 번 돌리고 관찰한 것을 돌려준다.

    기본은 **처음 설치한 기계**다 — 캐시 폴더가 아직 없다. alive 는 _launchctl_job_alive
    가 차례로 돌려줄 값이고 마지막 값이 계속 반복된다((True,) 이면 마감까지 안 끝난다).
    False 를 처음 돌려주는 순간 job 이 '끝난' 것으로 치고 출력의 뒷부분이 써진다.
    cache_is_a_file: 캐시 폴더 자리에 파일(plist 도 못 쓴다).
    cwd_is_a_file:   캐시 폴더는 멀쩡하고 cli 자리에만 파일(plist 는 쓸 수 있다).
    call 을 주면 _run_refresh_job 대신 그것을 부른다(끝에서 끝까지 보는 테스트용).
    """
    td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    test.addCleanup(td.cleanup)
    root = os.path.realpath(td.name)
    cache = os.path.join(root, "cache")
    if cache_is_a_file:
        with open(cache, "w", encoding="utf-8") as f:
            f.write("not a directory")
    if cwd_is_a_file:
        os.makedirs(cache)
        with open(os.path.join(cache, "cli"), "w", encoding="utf-8") as f:
            f.write("not a directory")
    program = list(argv) if argv is not None else [CLI_WITH_SPACE, "-p", "/usage"]
    events, dbg = [], []
    clock = _Clock(events)
    seq = list(alive)
    polls = []

    def fake_alive(lbl):
        polls.append(lbl)
        if len(polls) > 2 * _Clock.LIMIT:
            raise AssertionError("살아 있는지 묻기를 멈추지 않는다 — sleep 없이 도는 폴링이다")
        value = seq.pop(0) if len(seq) > 1 else seq[0]
        events.append(("alive", lbl, clock.now(), value))
        if not value:
            fake.finish()             # 끝났다고 답하는 순간에는 job 이 정말 끝나 있다
        return value

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(claude_pet.sys, "platform", "darwin"))
        _posix_shims(stack)
        stack.enter_context(mock.patch.object(claude_pet, "RECOVERY_CACHE_DIR", cache,
                                              create=True))
        stack.enter_context(mock.patch.object(claude_pet, "_recovery_cache_dir",
                                              return_value=cache))
        io_paths = tuple(claude_pet._recovery_io_paths(stem))
        test.assertTrue(all(_is_under(p, root) for p in io_paths),
                        "하네스: 출력 경로가 임시 폴더 밖이다 — 돌리지 않는다")
        if stale_output:
            os.makedirs(cache, exist_ok=True)
            for p in io_paths:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(STALE)
        cwd_fn = getattr(claude_pet, "recovery_cli_cwd", None)
        cwd_by_contract = cwd_fn() if callable(cwd_fn) else None
        if cwd_by_contract is not None:
            test.assertTrue(_is_under(cwd_by_contract, root),
                            "하네스: recovery_cli_cwd() 가 _recovery_cache_dir() 를 따르지 않아 "
                            "임시 폴더 밖이다 — 실제 폴더를 만들 수 있으니 돌리지 않는다")
        fake = _FakeLaunchd(cache, label, PROBE_UID, io_paths, events, clock,
                            stale_job=stale_job, bootstrap_rc=bootstrap_rc,
                            bootstrap_raises=bootstrap_raises)
        stack.enter_context(mock.patch.object(claude_pet.subprocess, "run", new=fake))
        popen = stack.enter_context(mock.patch.object(claude_pet.subprocess, "Popen"))
        wmi = stack.enter_context(mock.patch.object(claude_pet, "_win_wmi_create",
                                                    return_value=None))
        stack.enter_context(mock.patch.object(claude_pet, "_launchctl_job_alive",
                                              new=fake_alive))
        stack.enter_context(mock.patch.object(claude_pet, "time", _TimeProxy(clock)))
        stack.enter_context(mock.patch.object(claude_pet, "_dbg",
                                              new=lambda *a: dbg.append(a)))
        if call is None:
            result = claude_pet._run_refresh_job(program, label, stem, timeout)
        else:
            result = call()
    plist_path = os.path.join(cache, stem + ".plist")
    leftovers = (sorted(n for n in os.listdir(cache) if n.endswith(".plist"))
                 if os.path.isdir(cache) else [])
    return types.SimpleNamespace(
        result=result, events=events, runs=fake.runs, snapshots=fake.snapshots,
        loaded=fake.loaded, popen=popen, wmi=wmi, dbg=dbg, root=root, cache=cache,
        io_paths=io_paths, expected_cwd=os.path.join(cache, "cli"),
        cwd_by_contract=cwd_by_contract, plist_path=plist_path,
        plist_left=os.path.exists(plist_path), leftover_plists=leftovers,
        program=[str(a) for a in program], label=label, sleeps=list(clock.sleeps))


def _only_job(test, r):
    """bootstrap 이 정확히 한 번 불렸고 그 순간의 job 정의를 읽을 수 있었다 → 그 스냅샷."""
    test.assertEqual(
        len(r.snapshots), 1,
        "launchctl bootstrap 이 정확히 한 번 불려야 한다. 실제 subprocess.run 호출: %r"
        % [argv for argv, _ in r.runs])
    snap = r.snapshots[0]
    test.assertIsInstance(snap["plist"], dict,
                          "bootstrap 시점에 job 정의를 읽지 못했다(%s)" % snap.get("error"))
    return snap


def _is_bootout(event, label):
    return (event[0] == "run" and event[1][:2] == [claude_pet.LAUNCHCTL, "bootout"]
            and event[1][2:] == ["gui/%d/%s" % (PROBE_UID, label)])


def _bootstrap_index(r):
    for i, event in enumerate(r.events):
        if event[0] == "run" and event[1][:2] == [claude_pet.LAUNCHCTL, "bootstrap"]:
            return i
    return None


def _final_bootout_index(r):
    found = [i for i, event in enumerate(r.events) if _is_bootout(event, r.label)]
    return found[-1] if found else None


def _cli_went_only_to_launchd(test, r, cli):
    """실행 경로로 본 '우리 자손이 아니다' — 메커니즘(submit/bootstrap)은 가리지 않는다.

    우리가 직접 돌린 것은 launchctl 뿐이고, CLI 는 launchctl 이 받은 인자(v0.26 의 submit)
    나 launchd 에 올린 job 정의(bootstrap) 안에만 나타난다.
    """
    test.assertFalse(r.popen.called, "subprocess.Popen 으로 직계 자식을 띄웠다")
    for argv, _ in r.runs:
        test.assertEqual(argv[0], claude_pet.LAUNCHCTL,
                         "launchctl 이 아닌 것을 우리가 직접 돌렸다: %r" % argv)
    handed = any(cli in argv[1:] for argv, _ in r.runs) or any(
        cli in ((s["plist"] if isinstance(s["plist"], dict) else {}).get("ProgramArguments")
                or []) for s in r.snapshots)
    test.assertTrue(handed, "CLI 가 launchd 에 넘어간 흔적이 없다")


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
        """2026-09-30 개정(cwdfix): darwin 의 argv[0] 은 이제 CLI 자신이다 — 계약상
        `recovery_spawn_argv` 는 launchd 가 돌릴 **프로그램**을 돌려주고 앞에 런처가 없다.
        그래서 darwin 쪽 '우리 자손이 아니다'는 argv 가 아니라 **실행 경로**로 증명한다
        (윈도우가 이미 그랬던 것처럼 — WindowsDetachmentTests). 윈도우 반쪽은 그대로다.
        darwin 반쪽은 메커니즘을 가리지 않는다(submit 이든 bootstrap 이든 '우리가 직접 돌린
        것은 launchctl 뿐'): 메커니즘 자체는 DarwinOneShotJobTests 가 건다.
        """
        with self.subTest(platform="win32"):
            argv = self.argv_on("win32")
            self.assertTrue(argv)
            base = os.path.basename(argv[0]).lower()
            self.assertNotIn(
                base, ("claude", "claude.exe", "claude.cmd", "claude.bat"),
                "win32: claude 를 직계 자식으로 띄우면 안 된다. macOS 에서는 보호폴더 "
                "접근이 ClaudePet 에 귀속되고(2026-07-13 TCC 거부 8건, 커밋 "
                "67849e4), 어느 쪽이든 타임아웃 때 정리해야 할 트리가 우리 밑에 "
                "매달린다 — 윈도우는 부모가 죽어도 자식이 살아남아 고아가 된다.")
        with self.subTest(platform="darwin"):
            r = _run_darwin_job(
                self, label=claude_pet.RECOVERY_JOB_LABEL, stem="token-refresh",
                call=lambda: claude_pet._run_refresh_job(
                    claude_pet.recovery_spawn_argv(CLI), claude_pet.RECOVERY_JOB_LABEL,
                    "token-refresh", 10))
            _cli_went_only_to_launchd(self, r, CLI)

    def test_login_is_not_a_direct_child_invocation_on_every_platform(self):
        """2026-09-30 개정(cwdfix): 위와 같은 이유로 darwin 반쪽은 실행 경로로 본다."""
        with self.subTest(platform="win32"):
            base = os.path.basename(self.argv_on("win32", "login_spawn_argv")[0]).lower()
            self.assertNotIn(base, ("claude", "claude.exe", "claude.cmd", "claude.bat"))
        with self.subTest(platform="darwin"):
            r = _run_darwin_job(
                self, label=claude_pet.LOGIN_JOB_LABEL, stem="login",
                call=lambda: claude_pet._run_refresh_job(
                    claude_pet.login_spawn_argv(CLI), claude_pet.LOGIN_JOB_LABEL, "login", 10))
            _cli_went_only_to_launchd(self, r, CLI)

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

    2026-09-30(cwdfix): 하네스가 `_recovery_cache_dir`·`RECOVERY_CACHE_DIR`·LOCALAPPDATA 도
    임시 폴더로 돌리고, `recovery_cli_cwd()` 가 그 밖을 가리키면 돌리지 않는다. 계약상 윈도우
    경로가 이제 `recovery_cli_cwd()`(= 캐시 폴더 아래 cli)를 만들기 때문이다 — 돌리지 않으면
    이 테스트가 맥에서는 실제 홈 아래 AppData 를, 윈도우에서는 실제 %LOCALAPPDATA% 를
    건드린다. 단언은 바뀌지 않았다.
    """

    def _run_win32(self, wmi_pid=None):
        with tempfile.TemporaryDirectory() as td:
            io_paths = (os.path.join(td, "o.txt"), os.path.join(td, "e.txt"))
            cache = os.path.join(td, "cache")
            with mock.patch.object(claude_pet.sys, "platform", "win32"), \
                 mock.patch.dict(os.environ, {"LOCALAPPDATA": os.path.join(td, "Local")}), \
                 mock.patch.object(claude_pet, "RECOVERY_CACHE_DIR", cache, create=True), \
                 mock.patch.object(claude_pet, "_recovery_cache_dir", return_value=cache), \
                 mock.patch.object(claude_pet, "_recovery_io_paths",
                                   return_value=io_paths), \
                 mock.patch.object(claude_pet, "_win_wmi_create",
                                   return_value=wmi_pid) as wmi, \
                 mock.patch.object(claude_pet.subprocess, "Popen") as popen, \
                 mock.patch.object(claude_pet.subprocess, "run") as run:
                cwd_fn = getattr(claude_pet, "recovery_cli_cwd", None)
                if callable(cwd_fn):         # 하네스 안전장치 — 임시 폴더 밖이면 돌리지 않는다
                    self.assertTrue(_is_under(cwd_fn(), os.path.realpath(td))
                                    or _is_under(cwd_fn(), td),
                                    "recovery_cli_cwd() 가 _recovery_cache_dir() 를 따르지 않는다")
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


def _same_path(a, b):
    return isinstance(a, str) and isinstance(b, str) and _norm(a) == _norm(b)


class RecoveryCliCwdTests(unittest.TestCase):
    """`recovery_cli_cwd()` — CLI 가 도는 사설 폴더. 두 플랫폼 공통 계약(스펙 §Fix 1).

    `/` 가 원인이었다고 `/` 만 막으면 되는 것이 아니다: 홈이나 그 위, 보호 폴더 아래나 그
    위도 같은 일을 한다. 캐시 폴더 자체도 안 된다 — .out/.err/.plist 가 거기 있다.
    """

    def _fn(self):
        fn = getattr(claude_pet, "recovery_cli_cwd", None)
        self.assertTrue(callable(fn), "claude_pet.recovery_cli_cwd() 가 없다 — 계약 이름이다")
        return fn

    def test_it_is_the_cli_folder_of_the_cache_dir_on_every_platform(self):
        """Rivals: `/`(v0.26 의 launchd 기본값), 홈, `/Users`, 캐시 폴더 자체, 보호 폴더
        아래(~/Documents/…)나 그 조상(~/Library), 상대경로."""
        fn = self._fn()
        home = os.path.expanduser("~")
        # 실제 홈 기준으로 계산하는 유일한 테스트다. 폴더를 만드는 구현이 여기서 실제 홈을
        # 건드리지 못하게, 만드는 호출은 전부 실패시킨다(순수성은 아래 테스트가 따로 본다).
        no_mkdir = AssertionError("recovery_cli_cwd() 가 폴더를 만들려 했다")
        for plat in ("darwin", "win32"):
            with self.subTest(platform=plat), \
                    mock.patch.object(claude_pet.sys, "platform", plat):
                cache = claude_pet._recovery_cache_dir()
                with mock.patch.object(claude_pet.os, "makedirs", side_effect=no_mkdir), \
                        mock.patch.object(claude_pet.os, "mkdir", side_effect=no_mkdir):
                    cwd = fn()
                self.assertIsInstance(cwd, str)
                self.assertTrue(os.path.isabs(cwd),
                                "절대경로여야 한다 — launchd·WMI 의 작업 디렉터리는 우리 것이 아니다")
                self.assertTrue(_same_path(cwd, os.path.join(cache, "cli")),
                                "캐시 폴더 아래 cli 여야 한다: %r" % cwd)
                self.assertFalse(_same_path(cwd, cache),
                                 "캐시 폴더 자체는 안 된다 — .out/.err/.plist 가 거기 있다")
                self.assertFalse(_is_ancestor_or_equal(cwd, home),
                                 "홈이거나 그 위(`/` 포함)다 — CLI 가 거기서부터 훑는다")
                for tail in TCC_PROTECTED_UNDER_HOME:
                    protected = os.path.join(home, *tail)
                    self.assertFalse(
                        _is_ancestor_or_equal(protected, cwd)
                        or _is_ancestor_or_equal(cwd, protected),
                        "보호 위치 ~/%s 와 겹친다" % "/".join(tail))
                self.assertFalse(_is_ancestor_or_equal("/Volumes", cwd)
                                 or _is_ancestor_or_equal(cwd, "/Volumes"))

    def test_it_follows_the_cache_dir_and_creates_nothing(self):
        """순수 함수다 — 경로를 계산할 뿐 폴더를 만들지 않는다(만드는 것은 _run_refresh_job).
        Rivals: 안에서 makedirs 하는 구현; _recovery_cache_dir() 를 따라가지 않는 고정 경로
        (~/Library/Caches/… 하드코딩, tempfile.gettempdir() 등)."""
        fn = self._fn()
        with tempfile.TemporaryDirectory() as td:
            cache = os.path.join(td, "not-created-yet")
            with mock.patch.object(claude_pet, "_recovery_cache_dir", return_value=cache):
                cwd = fn()
            self.assertTrue(_same_path(cwd, os.path.join(cache, "cli")),
                            "_recovery_cache_dir() 를 따라가지 않는다: %r" % cwd)
            self.assertFalse(os.path.exists(cache), "경로를 계산하다가 폴더를 만들었다")


class DarwinSpawnArgvTests(unittest.TestCase):
    """macOS 의 *_spawn_argv 는 launchd 가 돌릴 **프로그램 그 자체**다 — 앞에 런처가 없다
    (스펙 §Fix 2). '우리 자손이 아니다'는 이제 _run_refresh_job 이 어떻게 넘기느냐가 진다.

    Rivals: v0.26 의 `launchctl submit … --` 접두사; cwd 만 고친 `/usr/bin/env -C <dir>`
    접두사(여전히 submit 이라 keep-alive 다); 경로 객체를 str 로 바꾸지 않은 구현.
    """

    def test_the_refresh_argv_is_claude_p_usage(self):
        with mock.patch.object(claude_pet.sys, "platform", "darwin"):
            argv = claude_pet.recovery_spawn_argv(pathlib.PurePosixPath(CLI))
        self.assertEqual(argv, [CLI, "-p", "/usage"])
        self.assertTrue(all(type(a) is str for a in argv), "argv 는 전부 str 이어야 한다")

    def test_the_login_argv_is_claude_auth_login_claudeai(self):
        with mock.patch.object(claude_pet.sys, "platform", "darwin"):
            argv = claude_pet.login_spawn_argv(pathlib.PurePosixPath(CLI))
        self.assertEqual(argv, [CLI, "auth", "login", "--claudeai"])
        self.assertTrue(all(type(a) is str for a in argv), "argv 는 전부 str 이어야 한다")

    def test_windows_argv_is_unchanged(self):
        """**NOT A GATE** — 회귀 가드다. 작성 시점에 초록이고 그래야 맞다(스펙: win32 는
        그대로). `cmd.exe /c` 한 겹이 빠지면 npm 설치판의 claude.cmd 가 뜨지 않는다."""
        with mock.patch.object(claude_pet.sys, "platform", "win32"):
            rec = claude_pet.recovery_spawn_argv(CLI)
            login = claude_pet.login_spawn_argv(CLI)
            cmd = claude_pet._windows_cmd_exe()
        self.assertEqual(rec, [cmd, "/c", CLI, "-p", "/usage"])
        self.assertEqual(login, [cmd, "/c", CLI, "auth", "login", "--claudeai"])


class DarwinOneShotJobTests(unittest.TestCase):
    """macOS: CLI 는 launchd 에 `bootstrap` 으로 올리는 원샷 job 으로, 사설 cwd 에서, 시도마다
    한 번만 돈다(스펙 §Fix 3 darwin a–e; 이름과 순서는 바인딩 계약).

    전부 _run_darwin_job 하네스로 돈다 — 실제로는 아무것도 띄우지 않는다. 기본 픽스처는
    처음 설치한 기계(캐시 폴더 없음, 같은 라벨의 job 없음 → 첫 bootout 은 113)다.
    """

    def test_the_cli_is_handed_to_launchd_by_bootstrap_and_never_run_by_us(self):
        """Rivals: v0.26(이 하네스가 넘기는 새 argv 로는 CLI 를 subprocess.run 으로 직접
        돌린다); `launchctl submit`(cwd 옵션 없음, 끝난 job 을 다시 띄움 — exit 0 이어도); submit + `env -C`;
        Popen 으로 직계 자식; uid 501 하드코딩; plist 를 캐시 폴더가 아닌 곳에 둠."""
        r = _run_darwin_job(self)
        snap = _only_job(self, r)
        self.assertEqual(
            snap["argv"],
            [claude_pet.LAUNCHCTL, "bootstrap", "gui/%d" % PROBE_UID, r.plist_path],
            "bootstrap 은 gui/<os.getuid()> 도메인에, 캐시 폴더의 <stem>.plist 로 해야 한다")
        _cli_went_only_to_launchd(self, r, CLI_WITH_SPACE)
        for argv, _ in r.runs:
            self.assertNotIn("submit", argv,
                             "launchctl submit — cwd 를 정할 수 없고 끝난 job 을 다시 띄운다(exit 0 이어도)")
        self.assertFalse(r.wmi.called, "macOS 에서 WMI 경로를 탔다")

    def test_the_job_runs_exactly_the_given_argv_under_the_given_label(self):
        """Rivals: 라벨 하드코딩(RECOVERY_JOB_LABEL); argv 를 셸 문자열로 합쳐 /bin/sh -c 로
        넘김(공백 있는 경로에서 깨진다); 경로 객체를 그대로 plist 에 넣으려다 실패;
        Program 키를 다른 실행 파일로."""
        r = _run_darwin_job(self, argv=[pathlib.PurePosixPath(CLI_WITH_SPACE), "-p", "/usage"])
        job = _only_job(self, r)["plist"]
        self.assertEqual(job.get("Label"), PROBE_LABEL, "라벨은 인자로 받은 것이어야 한다")
        self.assertEqual(job.get("ProgramArguments"), [CLI_WITH_SPACE, "-p", "/usage"],
                         "argv 를 그대로(각각 str 로) 넘겨야 한다")
        self.assertEqual(job.get("Program", CLI_WITH_SPACE), CLI_WITH_SPACE,
                         "Program 키를 둔다면 ProgramArguments[0] 과 같아야 한다")

    def test_the_job_runs_in_the_private_cli_folder_which_exists_when_launchd_loads_it(self):
        """이 변경의 핵심. WorkingDirectory 가 없으면 launchd 는 `/` 에서 띄우고, 2026-09-30
        관측에서 cwd `/` 의 CLI 는 보호 위치를 읽으려 했다(모듈 주석의 세 칸 참조).
        Rivals: WorkingDirectory 없음; `/`; 홈; 캐시 폴더 자체; 이름은 맞지만 폴더를 만들지
        않음(launchd 가 chdir 하지 못한다 — 처음 설치한 기계가 정확히 그 경우다)."""
        r = _run_darwin_job(self)
        snap = _only_job(self, r)
        wd = snap["plist"].get("WorkingDirectory")
        self.assertIsInstance(wd, str,
                              "WorkingDirectory 가 없다 — launchd 는 `/` 에서 띄운다")
        self.assertTrue(_same_path(wd, r.expected_cwd),
                        "WorkingDirectory 는 캐시 폴더 아래 cli 여야 한다: %r" % wd)
        self.assertIsNotNone(r.cwd_by_contract, "recovery_cli_cwd() 가 없다")
        self.assertTrue(_same_path(wd, r.cwd_by_contract),
                        "WorkingDirectory 가 recovery_cli_cwd() 와 다르다")
        self.assertTrue(snap["wd_isdir"], "bootstrap 시점에 WorkingDirectory 폴더가 없다")

    def test_output_lands_where_the_drain_reads_it(self):
        """Rivals: 출력 키 없음(출력이 사라져 '로그인 만료' 를 알아채지 못한다); 두 경로를
        맞바꿈; _recovery_io_paths(stem) 와 다른 곳."""
        r = _run_darwin_job(self)
        job = _only_job(self, r)["plist"]
        self.assertTrue(_same_path(job.get("StandardOutPath"), r.io_paths[0]),
                        "StandardOutPath 가 _recovery_io_paths(stem)[0] 이 아니다")
        self.assertTrue(_same_path(job.get("StandardErrorPath"), r.io_paths[1]),
                        "StandardErrorPath 가 _recovery_io_paths(stem)[1] 이 아니다")
        self.assertEqual(r.result, JOB_FULL, "job 이 남긴 출력을 돌려주지 않았다")

    def test_the_job_runs_once_and_is_never_kept_alive(self):
        """v0.26 의 두 번째 원인: submit 은 끝난 job 을 다시 띄운다 — 실패했을 때만이 아니라
        exit 0 이어도(재현됨). 관측(모듈 주석)에서 시도 한 번이 CLI 실행 세 번이 됐다.
        로그인이라면 끝날 때마다 브라우저가 다시 뜬다.
        Rivals: KeepAlive true; KeepAlive {SuccessfulExit: false}(실패하면 재실행 — v0.26 보다
        좁지만 여전히 재실행이다); 옛 이름 OnDemand false; RunAtLoad 없음(올려도 안 뜬다);
        주기·감시 트리거."""
        r = _run_darwin_job(self)
        job = _only_job(self, r)["plist"]
        self.assertIs(job.get("RunAtLoad"), True, "RunAtLoad 가 true 가 아니면 올려도 뜨지 않는다")
        self.assertIs(job.get("KeepAlive", False), False,
                      "KeepAlive 는 없거나 false 여야 한다 — 조건 dict 도 재실행이다: %r"
                      % (job.get("KeepAlive"),))
        self.assertIs(job.get("OnDemand", True), True,
                      "OnDemand=false 는 옛 이름의 KeepAlive=true 다")
        self.assertEqual(sorted(RELAUNCH_KEYS & set(job)), [],
                         "job 을 다시 띄우는 트리거가 붙어 있다")

    def test_stale_output_is_cleared_before_the_job_starts(self):
        """launchd 는 출력 파일에 이어 쓴다. 지난 실행의 'Login expired' 가 남아 있으면 이번
        실행의 결과로 오해해 사이클을 닫는다. Rival: 지우지 않는 구현."""
        r = _run_darwin_job(self, stale_output=True)
        snap = _only_job(self, r)
        self.assertEqual(sorted(os.path.basename(p) for p, e in snap["stale"].items() if e), [],
                         "bootstrap 시점에 지난 출력이 남아 있다")
        self.assertEqual(r.result, JOB_FULL)

    def test_a_leftover_job_with_the_same_label_is_booted_out_first(self):
        """앱 업데이트 직후 — v0.26 의 submit 이 같은 라벨로 올려 둔 job 이 남아 있다. 그대로
        bootstrap 하면 launchd 가 5 로 거절하고 갱신은 영영 일어나지 않는다.
        Rivals: bootstrap 전 bootout 없음; bootout 의 '없음'(113)을 실패로 보고 멈추는 구현
        (첫 실행마다 그렇다 — 다른 테스트의 기본 픽스처가 그 경우다)."""
        r = _run_darwin_job(self, stale_job=True)
        _only_job(self, r)
        i = _bootstrap_index(r)
        self.assertTrue(any(_is_bootout(e, PROBE_LABEL) for e in r.events[:i]),
                        "bootstrap 전에 gui/<uid>/<label> 을 bootout 하지 않았다")
        self.assertEqual(r.result, JOB_FULL, "남아 있던 job 때문에 이번 시도가 실패했다")
        self.assertFalse(r.loaded)

    def test_after_the_job_finishes_it_is_booted_out_and_its_definition_removed(self):
        """keep-alive 없는 job 은 끝나도 launchd 에 '올라간 채' 남는다. 내리지 않으면 다음
        시도의 bootstrap 이 거절된다. 그리고 내리는 것은 **끝났다는 답을 본 뒤**여야 한다 —
        돌고 있는 job 을 내리면 CLI 가 도중에 죽어 갱신이 일어나지 않는다.
        Rivals: 끝난 뒤 bootout 없음; plist 를 남김; 다른 라벨로 묻거나 내림; 폴링 조건을
        뒤집어(`if _launchctl_job_alive(label): break`) 첫 폴에서 돌고 있는 job 을 내리는 구현
        — 결과에 job 의 뒷부분 출력이 없어서 드러난다(가짜 job 은 끝날 때 뒷부분을 쓴다)."""
        r = _run_darwin_job(self, alive=(True, True, False))
        _only_job(self, r)
        polls = [i for i, e in enumerate(r.events) if e[0] == "alive"]
        self.assertTrue(polls, "끝났는지 한 번도 묻지 않았다")
        self.assertEqual({r.events[i][1] for i in polls}, {PROBE_LABEL})
        last = _final_bootout_index(r)
        self.assertIsNotNone(last, "job 을 내리지 않았다")
        seen = [r.events[i][3] for i in polls if i < last]
        self.assertTrue(seen and seen[-1] is False,
                        "job 이 아직 도는데 내렸다 — 끝났다는 답(False)을 보기 전에 bootout 하면 "
                        "CLI 가 도중에 죽는다 (내리기 전 폴 결과: %r)" % seen)
        self.assertFalse(r.loaded, "끝난 job 이 launchd 에 남아 있다")
        self.assertFalse(r.plist_left, "job 정의(plist)를 지우지 않았다")
        self.assertEqual(r.leftover_plists, [])
        self.assertEqual(r.result, JOB_FULL, "끝까지 돈 job 의 출력을 다 돌려주지 않았다")

    def test_at_the_deadline_the_job_is_booted_out_too(self):
        """끝나지 않는 job — **마감까지 기다린 뒤** bootout 으로 죽이고 정의를 지우고, 그때까지
        받은 출력을 돌려준다(뒷부분은 없다 — 도중에 내렸으니까).
        Rivals: 끝났을 때만 bootout(마감 경로에서 job 이 계속 돈다 — 로그인이면 브라우저가
        떠 있는 채로); 마감에서 None(시작은 됐으니 '띄우지도 못했다' 가 아니다); 1초보다
        촘촘한 폴링(launchctl 프로세스를 쏟아낸다); 마감 전에 내림(폴링 조건을 뒤집은 구현은
        첫 폴인 2초 뒤에 내린다); 마감을 한참 넘겨 기다림."""
        timeout = 10
        r = _run_darwin_job(self, alive=(True,), timeout=timeout)
        _only_job(self, r)
        polls = [i for i, e in enumerate(r.events) if e[0] == "alive"]
        self.assertTrue(polls, "살아 있는지 한 번도 묻지 않았다")
        self.assertLessEqual(len(polls), timeout + 2, "폴링이 1초에 한 번보다 촘촘하다")
        last = _final_bootout_index(r)
        self.assertTrue(last is not None and last > polls[-1], "마감 경로에서 bootout 하지 않았다")
        waited = r.events[last][2] - r.events[_bootstrap_index(r)][2]
        self.assertGreaterEqual(waited, timeout - 2.0,
                                "마감(%ss) 전에 내렸다: %.1fs 만에" % (timeout, waited))
        self.assertLessEqual(waited, timeout + 4.0,
                             "마감(%ss)을 한참 넘겨 기다렸다: %.1fs" % (timeout, waited))
        self.assertFalse(r.loaded, "마감을 넘긴 job 이 launchd 에 남아 있다")
        self.assertFalse(r.plist_left, "job 정의(plist)를 지우지 않았다")
        self.assertEqual(r.leftover_plists, [])
        self.assertEqual(r.result, JOB_KILLED, "마감에서 받은 출력을 돌려주지 않았다")

    def test_a_job_that_cannot_be_started_gives_none_and_leaves_nothing_behind(self):
        """띄우지 못했으면 None(호출자가 폴백을 고른다), 뒤에는 아무것도 남기지 않는다, 로그에
        경로를 남기지 않는다(CLAUDE.md Privacy — 경로는 신원 정보다).
        Rivals: 실패해도 출력("")을 돌려줌; 실패 뒤 bootout 없음; plist 를 남김; submit 으로
        물러섬; 예외를 통째로 _dbg 에 넘김(이 픽스처의 예외 메시지에는 plist 경로가 있다);
        cwd 를 못 만들었는데도 job 을 올림 — 그 경쟁 구현은 "cwd unusable"(캐시 폴더는 멀쩡하고
        cli 자리에만 파일)이 가른다. 리뷰 R1: 캐시 폴더째 파일인 픽스처만으로는 plist 도 못 써서
        makedirs 실패를 무시하는 구현까지 None 을 돌려줬다. launchd 는 WorkingDirectory 가
        없거나 파일이면 job 을 띄우지 못하고(exit 78) 우리는 "" 를 돌려주게 되는데, 로그인
        경로에서 그것은 '띄웠다' 로 읽혀 터미널 폴백이 건너뛰어진다."""
        cases = (
            ("bootstrap rc != 0", dict(bootstrap_rc=BOOTSTRAP_IO_ERROR_RC)),
            ("bootstrap raises", dict(bootstrap_raises=True)),
            ("cache dir unusable", dict(cache_is_a_file=True)),
            ("cwd unusable", dict(cwd_is_a_file=True)),
        )
        for name, kw in cases:
            with self.subTest(case=name):
                r = _run_darwin_job(self, **kw)
                self.assertIsNone(r.result, "띄우지 못했으면 None 이어야 한다")
                self.assertFalse(r.loaded, "launchd 에 job 이 남아 있다")
                self.assertFalse(r.plist_left, "job 정의(plist)가 남아 있다")
                self.assertEqual(r.leftover_plists, [])
                self.assertFalse(r.popen.called)
                for argv, _ in r.runs:
                    self.assertNotIn("submit", argv, "bootstrap 실패 뒤 submit 으로 물러섰다")
                    self.assertNotEqual(argv[0], CLI_WITH_SPACE, "CLI 를 직접 돌렸다")
                i = _bootstrap_index(r)
                if kw.get("cache_is_a_file") or kw.get("cwd_is_a_file"):
                    self.assertIsNone(i, "cwd 를 만들 수 없는데 job 을 올렸다")
                else:
                    self.assertIsNotNone(i)
                    self.assertTrue(any(_is_bootout(e, PROBE_LABEL) for e in r.events[i + 1:]),
                                    "실패한 bootstrap 뒤에 bootout 하지 않았다")
                leaked = [a for a in r.dbg
                          if r.root in " ".join(str(x) for x in a)
                          or CLI_WITH_SPACE in " ".join(str(x) for x in a)]
                self.assertEqual(leaked, [], "_dbg 에 경로가 들어갔다")

    def test_every_launchctl_call_is_bounded(self):
        """**Verifier 가 끌어낸 조건이다 — 스펙 본문에는 없다.** 스펙은 bootstrap 호출의 인자를
        '…' 로 뒀고, 이 테스트는 기존 계약(test_the_attempt_is_bounded_by_a_timeout: 시도 하나는
        RECOVERY_TIMEOUT_SEC 로 묶인다)에서 나온다. launchctl 호출 하나가 timeout 없이 멈추면
        그 묶음이 깨지고 _recovery_busy 가 영원히 잡힌다. 특정 숫자가 아니라 **상한이 있다는
        것**만 건다(Coordinator 확인, 2026-09-30). Rival: timeout 없는 bootstrap."""
        r = _run_darwin_job(self)
        _only_job(self, r)
        for argv, kw in r.runs:
            t = kw.get("timeout")
            self.assertTrue(
                isinstance(t, (int, float)) and not isinstance(t, bool)
                and 0 < t <= claude_pet.RECOVERY_TIMEOUT_SEC,
                "%s 호출에 유한한 timeout 이 없다(%r)" % (" ".join(argv[:2]), t))

    def test_the_job_definition_and_the_cwd_are_private(self):
        """스펙: plist 0600, cwd 0700. umask 를 흔한 022 로 고정한다 — 077 이면 0644 로 쓰는
        구현도 우연히 통과한다. Rivals: open(path, "wb")(0644); makedirs 기본 모드(0755)."""
        if os.name != "posix":
            sys.stderr.write("\n[skip] %s: POSIX 권한 비트는 이 플랫폼에서 뜻이 없다\n" % self.id())
            self.skipTest("POSIX permission bits only")
        old = os.umask(0o022)
        try:
            r = _run_darwin_job(self)
        finally:
            os.umask(old)
        snap = _only_job(self, r)
        self.assertEqual(snap["mode"], 0o600, "job 정의(plist)가 0600 이 아니다: %o"
                         % (snap["mode"] or 0))
        self.assertTrue(snap["wd_isdir"], "WorkingDirectory 폴더가 없다")
        self.assertEqual(snap["wd_mode"] & 0o077, 0, "cwd 폴더가 0700 이 아니다: %o"
                         % snap["wd_mode"])


class DarwinEndToEndSpawnTests(unittest.TestCase):
    """실제 호출자가 launchd 에 무엇을 넘기는가 — 조립까지 본다.

    v0.26 의 버그는 조립에 있었다: recovery_spawn_argv 가 submit argv 를 만들고
    _run_refresh_job 이 그것을 그대로 돌렸다. 두 함수를 따로 보면 각자 멀쩡해 보일 수 있다.
    """

    def _assert_one_shot(self, r, label, program):
        job = _only_job(self, r)["plist"]
        self.assertEqual(job.get("Label"), label)
        self.assertEqual(job.get("ProgramArguments"), program)
        self.assertTrue(_same_path(job.get("WorkingDirectory"), r.expected_cwd),
                        "WorkingDirectory 가 사설 cli 폴더가 아니다: %r" % job.get("WorkingDirectory"))
        self.assertIs(job.get("KeepAlive", False), False)
        self.assertIs(job.get("RunAtLoad"), True)
        self.assertFalse(r.loaded, "끝난 job 이 launchd 에 남아 있다")
        _cli_went_only_to_launchd(self, r, CLI_WITH_SPACE)

    def test_the_token_refresh_hands_claude_p_usage_to_a_one_shot_job(self):
        holder = {"recovery": claude_pet.new_recovery_state()}
        with mock.patch.object(claude_pet, "_find_claude_cli", return_value=CLI_WITH_SPACE), \
             mock.patch.object(claude_pet, "threading",
                               types.SimpleNamespace(Thread=_InlineThread)):
            r = _run_darwin_job(self, label=claude_pet.RECOVERY_JOB_LABEL, stem="token-refresh",
                                call=lambda: claude_pet.run_token_refresh(holder))
        self.assertIs(r.result, True)
        self._assert_one_shot(r, claude_pet.RECOVERY_JOB_LABEL, [CLI_WITH_SPACE, "-p", "/usage"])

    def test_the_login_hands_auth_login_to_a_one_shot_job(self):
        """로그인은 keep-alive 의 대가가 가장 크다 — 끝난 `claude auth login` 이(취소든 실패든
        성공이든) LOGIN_TIMEOUT_SEC 까지 다시 떠서 브라우저를 또 연다(스펙 근본 원인 2)."""
        with mock.patch.object(claude_pet, "_find_claude_cli", return_value=CLI_WITH_SPACE):
            r = _run_darwin_job(self, label=claude_pet.LOGIN_JOB_LABEL, stem="login",
                                call=claude_pet.start_claude_login_background)
        self.assertIs(r.result, True)
        self._assert_one_shot(r, claude_pet.LOGIN_JOB_LABEL,
                              [CLI_WITH_SPACE, "auth", "login", "--claudeai"])


class LaunchctlBootoutTests(unittest.TestCase):
    """`_launchctl_bootout(label)` — `_launchctl_remove` 를 대신한다. 모양은 스펙이 정했다."""

    def _fn(self):
        fn = getattr(claude_pet, "_launchctl_bootout", None)
        self.assertTrue(callable(fn), "claude_pet._launchctl_bootout 가 없다 — 계약 이름이다")
        return fn

    def test_it_boots_out_the_service_in_the_gui_domain(self):
        """Rivals: uid 501 하드코딩; 서비스 대신 plist 경로를 넘기는 형태; 옛 `launchctl
        remove`; timeout 없는 호출."""
        fn = self._fn()
        calls = []

        def fake_run(argv, *a, **kw):
            calls.append(([str(x) for x in argv], kw))
            return subprocess.CompletedProcess(argv, 0, b"", b"")

        with mock.patch.object(claude_pet.os, "getuid", return_value=PROBE_UID, create=True), \
             mock.patch.object(claude_pet.subprocess, "run", new=fake_run):
            fn(PROBE_LABEL)
        self.assertEqual(
            [argv for argv, _ in calls],
            [[claude_pet.LAUNCHCTL, "bootout", "gui/%d/%s" % (PROBE_UID, PROBE_LABEL)]])
        t = calls[0][1].get("timeout")
        self.assertTrue(isinstance(t, (int, float)) and not isinstance(t, bool) and 0 < t <= 30,
                        "bootout 호출에 짧은 timeout 이 없다(%r)" % (t,))

    def test_it_never_raises(self):
        """정리 단계에서 터지면 plist 삭제와 출력 회수가 건너뛰어진다. Rival: 예외를 그대로
        올리는 구현."""
        fn = self._fn()
        for exc in (OSError(errno.ENOENT, "No such file or directory"),
                    subprocess.TimeoutExpired([claude_pet.LAUNCHCTL, "bootout"], 10),
                    subprocess.CalledProcessError(BOOTOUT_NOT_FOUND_RC, [claude_pet.LAUNCHCTL])):
            with self.subTest(exc=type(exc).__name__), \
                    mock.patch.object(claude_pet.os, "getuid", return_value=PROBE_UID,
                                      create=True), \
                    mock.patch.object(claude_pet.subprocess, "run", side_effect=exc):
                fn(PROBE_LABEL)


# ── 업데이트·종료가 남긴 옛 job 치우기 (2026-09-30, 리뷰 R2) ─────────────────────────────────
#
# 소스에서 읽히는 사실: v0.26 은 `launchctl submit` 으로 job 을 올렸다(`man launchctl` 은 "keep
# the program alive in the event of failure" 라고만 적는다). 관측(cwdfix-review 의 프로브,
# 2026-09-30, 이 맥 한 번; Developer 도 재현): 프로그램이 exit 0 으로 끝난 submit job 도
# "spawn scheduled" 로 넘어갔다 — 실패할 때만 다시 뜨는 것이 아니다. 그래서 앱이 업데이트
# 되거나 시도 도중에 꺼지면, 남은 job 이 다음 시도의 bootout(최대 8시간 뒤)까지 CLI 를 `/` 에서
# 다시 띄운다. 로그인 라벨이라면 브라우저가 다시 열린다.
# 그래서 코드가 해야 하는 것(계약, Coordinator — 이름은 바인딩): clear_stale_launchd_jobs() 는
# darwin 에서 _launchctl_bootout(LOGIN_JOB_LABEL) 을 늘 부르고, _launchctl_bootout(RECOVERY_JOB_LABEL)
# 은 _recovery_busy 를 **기다리지 않고** 잡을 수 있을 때만 부른다(그 동안 쥐고 있다가 놓는다).
# 잡혀 있으면 진행 중인 시도가 자기 bootout 으로 이미 옛 job 을 내렸고, 지금 내리면 그 시도의
# 살아 있는 CLI 를 죽인다. 다른 플랫폼에서는 subprocess 도 bootout 도 없다. 예외를 내지 않는다.
# run_gui() 는 기동할 때 이것을 데몬 threading.Thread 에서 한 번 띄운다(메인 스레드가 아니다).


class _FakeLock:
    """_recovery_busy 대역 — 절대 기다리지 않고, 무엇을 했는지 기록한다.

    held            진행 중인 시도가 쥐고 있다(잡으려 해도 실패한다).
    peek_says_free  locked() 가 '비었다' 고 답한다 — 들여다본 순간과 bootout 사이에 시도가
                    끼어든 경우다. 들여다보고 행동하는 구현만 여기서 틀린다.
    """

    def __init__(self, events, held=False, peek_says_free=False):
        self.events = events
        self.held = held
        self.peek_says_free = peek_says_free
        self.owned = 0

    def acquire(self, blocking=True, timeout=-1):
        waits = bool(blocking) and timeout != 0
        self.events.append(("acquire", "may-wait" if waits else "non-blocking"))
        if self.held:
            return False          # 진짜 Lock 이라면 기다리는 호출은 여기서 멈춘다
        self.owned += 1
        return True

    def release(self):
        if self.owned <= 0:
            self.events.append(("release-of-a-lock-it-does-not-hold",))
            return
        self.owned -= 1
        self.events.append(("release",))

    def locked(self):
        self.events.append(("peek",))
        return self.held and not self.peek_says_free

    def __enter__(self):
        self.acquire()
        return True

    def __exit__(self, *exc):
        self.release()
        return False


def _run_cleanup(test, platform="darwin", held=False, peek_says_free=False, fail_with=None,
                 patch_bootout=False):
    """clear_stale_launchd_jobs() 를 한 번 부른다. 실제 launchctl 은 절대 돌지 않는다."""
    fn = getattr(claude_pet, "clear_stale_launchd_jobs", None)
    test.assertTrue(callable(fn), "claude_pet.clear_stale_launchd_jobs() 가 없다 — 계약 이름이다")
    events = []
    lock = _FakeLock(events, held=held, peek_says_free=peek_says_free)

    def fake_run(argv, *a, **kw):
        events.append(("run", [str(x) for x in argv], lock.owned))
        if fail_with is not None:
            raise fail_with
        return subprocess.CompletedProcess(argv, BOOTOUT_NOT_FOUND_RC, b"", b"")

    raised = None
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(claude_pet.sys, "platform", platform))
        _posix_shims(stack)
        stack.enter_context(mock.patch.object(claude_pet.subprocess, "run", new=fake_run))
        popen = stack.enter_context(mock.patch.object(claude_pet.subprocess, "Popen"))
        stack.enter_context(mock.patch.object(claude_pet, "_recovery_busy", lock))
        bootout = (stack.enter_context(mock.patch.object(claude_pet, "_launchctl_bootout"))
                   if patch_bootout else None)
        try:
            fn()
        except Exception as e:          # 계약 위반이다 — 테스트가 판정한다
            raised = e
    runs = [e for e in events if e[0] == "run"]
    return types.SimpleNamespace(events=events, runs=runs, lock=lock, popen=popen,
                                 bootout=bootout, raised=raised)


def _bootout_targets(r):
    return [e[1][2] for e in r.runs if e[1][:2] == [claude_pet.LAUNCHCTL, "bootout"]
            and len(e[1]) == 3]


def _own_nodes(fn):
    """(node, in_loop) — fn 자신의 본문만. 중첩 함수·람다·클래스 안은 다른 때에 돈다.
    (본문 맨 위에 놓인 중첩 def 도 빼야 한다 — 처음엔 자식으로 발견된 것만 걸러서, 중첩 함수
    안의 호출을 메인 스레드 호출로 잘못 셌다. 정당한 모양 CL2·CL6 을 돌려서 찾았다.)"""
    nested = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
    out, stack = [], [(n, False) for n in fn.body if not isinstance(n, nested)]
    while stack:
        node, in_loop = stack.pop()
        out.append((node, in_loop))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nested):
                continue
            stack.append((child, in_loop or isinstance(node, (ast.For, ast.While, ast.AsyncFor))))
    return out


class StaleJobCleanupTests(unittest.TestCase):
    """clear_stale_launchd_jobs() — 위 주석의 관측과 계약.

    Rivals(전부 돌려 봤다 — scratchpad cwdfix-cleanup-red.txt): 부르지 않음; 한 라벨만;
    시도가 잠금을 쥐고 있는데 복구 라벨을 내림(살아 있는 job 을 죽인다); 잠금을 기다리며 잡음;
    잠금을 놓지 않음; 메인 스레드에서 부름; win32 에서 launchctl 을 건드림; 실패하면 예외;
    locked() 로 들여다보고 행동함; 잡았다 놓은 뒤에 내림; 못 잡았는데도 놓음; 데몬이 아닌 스레드;
    만들고 시작하지 않은 스레드; 두 번 띄움. 리뷰 R3 이 더 찾은 셋: 새로고침 시도마다 부름(C19 —
    진행 중인 로그인 job 을 내린다); AppHelper.runEventLoop() 뒤에서 시작(C20 — 앱이 떠 있는 동안
    돌지 않는다); 로그인마다 부름(C22 — '한 번' 이 깨진다).
    """

    LOGIN = "gui/%d/%s" % (PROBE_UID, claude_pet.LOGIN_JOB_LABEL)
    RECOVERY = "gui/%d/%s" % (PROBE_UID, claude_pet.RECOVERY_JOB_LABEL)

    def _no_waiting(self, r):
        self.assertEqual([e for e in r.events if e == ("acquire", "may-wait")], [],
                         "_recovery_busy 를 기다리며 잡으려 했다 — 시도가 끝날 때까지 멈춘다")
        self.assertNotIn(("release-of-a-lock-it-does-not-hold",), r.events,
                         "쥐지 않은 잠금을 풀었다 — 진행 중인 시도의 잠금이 풀린다")

    def test_on_macos_both_leftover_jobs_are_booted_out_when_no_attempt_is_running(self):
        r = _run_cleanup(self)
        self.assertIsNone(r.raised, "예외가 밖으로 나왔다: %r" % (r.raised,))
        self.assertEqual(sorted(_bootout_targets(r)), sorted([self.LOGIN, self.RECOVERY]),
                         "두 라벨을 한 번씩 내려야 한다 — 실제 호출: %r" % [e[1] for e in r.runs])
        self.assertEqual([e[1] for e in r.runs if e[1][:2] != [claude_pet.LAUNCHCTL, "bootout"]], [],
                         "bootout 말고 다른 것을 돌렸다")
        self.assertFalse(r.popen.called)
        held_during = [e[2] for e in r.runs if e[1][2:] == [self.RECOVERY]]
        self.assertEqual(held_during, [1],
                         "복구 라벨은 _recovery_busy 를 쥔 채로 내려야 한다 — 놓은 뒤에 내리면 그 틈에 "
                         "시작한 시도의 job 을 죽인다")
        self.assertEqual(r.lock.owned, 0, "_recovery_busy 를 놓지 않았다 — 복구가 영영 멈춘다")
        self._no_waiting(r)

    def test_the_recovery_job_is_left_alone_while_an_attempt_holds_the_lock(self):
        for name, kw in (("held", dict(held=True)),
                         ("taken between a peek and the bootout", dict(held=True, peek_says_free=True))):
            with self.subTest(lock=name):
                r = _run_cleanup(self, **kw)
                self.assertIsNone(r.raised, "예외가 밖으로 나왔다: %r" % (r.raised,))
                self.assertIn(self.LOGIN, _bootout_targets(r), "로그인 라벨은 늘 내려야 한다")
                self.assertNotIn(self.RECOVERY, _bootout_targets(r),
                                 "시도가 잠금을 쥐고 있는데 복구 job 을 내렸다 — 살아 있는 CLI 를 죽인다")
                self._no_waiting(r)

    def test_on_other_platforms_it_touches_nothing(self):
        for plat in ("win32", "linux"):
            with self.subTest(platform=plat):
                r = _run_cleanup(self, platform=plat, patch_bootout=True)
                self.assertIsNone(r.raised, "예외가 밖으로 나왔다: %r" % (r.raised,))
                self.assertEqual(r.runs, [], "%s 에서 subprocess 를 돌렸다" % plat)
                self.assertFalse(r.popen.called)
                self.assertFalse(r.bootout.called, "%s 에서 _launchctl_bootout 을 불렀다" % plat)

    def test_a_failing_launchctl_never_escapes_and_both_labels_are_still_tried(self):
        for exc in (OSError(errno.ENOENT, "No such file or directory"),
                    subprocess.TimeoutExpired([claude_pet.LAUNCHCTL, "bootout"], 10)):
            with self.subTest(exc=type(exc).__name__):
                r = _run_cleanup(self, fail_with=exc)
                self.assertIsNone(r.raised, "예외가 밖으로 나왔다 — 시작 스레드가 죽는다: %r" % (r.raised,))
                self.assertEqual(sorted(_bootout_targets(r)), sorted([self.LOGIN, self.RECOVERY]),
                                 "첫 실패 뒤 나머지 라벨을 내리지 않았다")
                self.assertEqual(r.lock.owned, 0, "실패한 뒤 _recovery_busy 를 놓지 않았다")

    def test_run_gui_starts_it_once_on_a_daemon_thread(self):
        """정적 검사(run_gui 는 GUI 라 돌릴 수 없다).

        허용하는 모양: run_gui 본문에서, 또는 run_gui 본문이 **한 번** 부르는 도우미 하나(모듈 함수나
        중첩 함수) 안에서, threading.Thread(target=…) 를 루프 밖에서 한 번 만들고 시작한다. target 은
        그 함수 자체, 그것을 부르는 람다, 또는 그것을 부르는 중첩 함수. 데몬은 daemon=True 인자나
        .daemon = True.

        리뷰 R3 이 더한 두 조건:
        (a) 그 시작(또는 도우미 호출)은 run_gui 본문에서 AppHelper.runEventLoop() 보다 **앞**이다 —
            그 호출은 앱이 끝날 때까지 돌아오지 않으므로, 뒤에 두면 앱이 떠 있는 동안 치우기가 돌지
            않는다(C20). tests/test_update_check_schedule.py 가 업데이트 시각 도장에 하는 것과 같은
            방식이다: run_gui 의 최상위 문장 번호를 비교한다.
        (b) 모듈 어디서도 그 함수를 **스레드의 target 말고는** 참조하지 않는다 — run_gui 안의 중첩
            메서드도 포함해서. 새로고침 시도마다(C19) 부르면 진행 중인 로그인 job 을 내리고, 로그인마다
            (C22) 부르면 '기동할 때 한 번' 이 깨진다. 같은 이유로 스레드를 시작하는 도우미와 target 으로
            쓴 중첩 함수도 한 번만 참조돼야 한다.
        """
        name = "clear_stale_launchd_jobs"
        event_loop = "AppHelper.runEventLoop()"
        tree = _source_tree()
        defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertIn("run_gui", defs, "run_gui 를 찾지 못했다")
        run_gui = defs["run_gui"]
        own = _own_nodes(run_gui)
        nested_defs = {n.name: n for n in ast.walk(run_gui)
                       if isinstance(n, ast.FunctionDef) and n is not run_gui}
        called = {c.func.id for c, _ in own
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        # run_gui 본문(메인 스레드)에서 곧바로 불리는 모듈 함수와 중첩 함수가 도우미 후보다.
        scopes = ([run_gui] + [defs[h] for h in sorted(called) if h in defs and h != name]
                  + [nested_defs[h] for h in sorted(called) if h in nested_defs and h != name])

        def refs_in(node):
            return [n for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == name]

        def calls_it(node):
            return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == name
                       for c in ast.walk(node))

        def target_refs(target, scope):
            """target 이 그 함수를 돌린다면 (그 참조들, 중첩 함수 이름|None), 아니면 None."""
            if isinstance(target, ast.Name) and target.id == name:
                return [target], None
            if isinstance(target, ast.Lambda) and calls_it(target.body):
                return refs_in(target.body), None
            if isinstance(target, ast.Name):
                nested = [n for n in ast.walk(scope)
                          if isinstance(n, ast.FunctionDef) and n.name == target.id and n is not scope]
                if nested and calls_it(nested[0]):
                    return refs_in(nested[0]), target.id
            return None

        found = []
        for scope in scopes:
            scope_own = _own_nodes(scope)
            for node, in_loop in scope_own:
                if not (isinstance(node, ast.Call) and (
                        (isinstance(node.func, ast.Attribute) and node.func.attr == "Thread")
                        or (isinstance(node.func, ast.Name) and node.func.id == "Thread"))):
                    continue
                target = next((kw.value for kw in node.keywords if kw.arg == "target"), None)
                hit = target_refs(target, scope) if target is not None else None
                if hit is None:
                    continue
                daemon = any(kw.arg == "daemon" and isinstance(kw.value, ast.Constant)
                             and kw.value.value is True for kw in node.keywords)
                started, var = False, None
                for parent, _ in scope_own:
                    if (isinstance(parent, ast.Attribute) and parent.value is node
                            and parent.attr == "start"):
                        started = True
                    if isinstance(parent, ast.Assign) and parent.value is node:
                        var = next((t.id for t in parent.targets if isinstance(t, ast.Name)), None)
                if var:
                    for n2, _ in scope_own:
                        if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                                and n2.func.attr == "start" and isinstance(n2.func.value, ast.Name)
                                and n2.func.value.id == var):
                            started = True
                        if (isinstance(n2, ast.Assign) and any(
                                isinstance(t, ast.Attribute) and t.attr == "daemon"
                                and isinstance(t.value, ast.Name) and t.value.id == var
                                for t in n2.targets)
                                and isinstance(n2.value, ast.Constant) and n2.value.value is True):
                            daemon = True
                found.append({"scope": scope, "call": node, "refs": hit[0], "via": hit[1],
                              "daemon": daemon, "started": started, "in_loop": in_loop})
        self.assertEqual(len(found), 1,
                         "run_gui 가 %s 를 도는 스레드를 정확히 한 번 만들어야 한다: %r"
                         % (name, [(f["scope"].name, f["in_loop"]) for f in found]))
        start = found[0]
        self.assertTrue(start["daemon"], "데몬 스레드가 아니다 — 종료를 붙잡는다")
        self.assertTrue(start["started"], "스레드를 만들고 시작하지 않았다")
        self.assertFalse(start["in_loop"], "루프 안에서 만든다 — 기동할 때 한 번이 아니다")

        # (b) 스레드의 target 말고는 모듈 어디서도 참조하지 않는다.
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        def where(node):
            chain = []
            while node in parents:
                node = parents[node]
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    chain.append(node.name)
            return ".".join(reversed(chain)) or "<module>"

        sanctioned = {id(n) for n in start["refs"]}
        stray = [where(n) for n in refs_in(tree) if id(n) not in sanctioned]
        self.assertEqual(stray, [],
                         "%s 를 스레드의 target 말고 다른 곳에서 참조한다 — 시도마다·로그인마다 부르면 "
                         "진행 중인 job 을 내리거나 '기동할 때 한 번' 이 깨진다(C19·C22)" % name)
        if start["via"] is not None:        # target 으로 쓴 중첩 함수도 그 한 번뿐이어야 한다
            uses = [n for n in ast.walk(run_gui) if isinstance(n, ast.Name) and n.id == start["via"]]
            self.assertEqual(len(uses), 1,
                             "target 으로 쓴 중첩 함수 %s 를 다른 곳에서도 부른다" % start["via"])

        # 도우미라면 run_gui 본문에서 루프 밖에서 한 번만 불리고, 다른 곳에서는 참조되지 않는다.
        if start["scope"] is run_gui:
            site = start["call"]
        else:
            helper = start["scope"].name
            universe = tree if helper in defs else run_gui
            uses = [n for n in ast.walk(universe) if isinstance(n, ast.Name) and n.id == helper]
            calls = [(c, in_loop) for c, in_loop in own if isinstance(c, ast.Call)
                     and isinstance(c.func, ast.Name) and c.func.id == helper]
            self.assertEqual((len(uses), len(calls)), (1, 1),
                             "스레드를 시작하는 도우미 %s 는 run_gui 본문에서 한 번만 불려야 한다" % helper)
            self.assertFalse(calls[0][1], "도우미를 루프 안에서 부른다 — 기동할 때 한 번이 아니다")
            site = calls[0][0]

        # (a) AppHelper.runEventLoop() 보다 앞 — run_gui 최상위 문장 번호로 비교한다.
        loops = [i for i, stmt in enumerate(run_gui.body)
                 if isinstance(stmt, ast.Expr) and ast.unparse(stmt) == event_loop]
        self.assertEqual(len(loops), 1, "run_gui 본문에 %s 가 정확히 하나 있어야 한다" % event_loop)
        at = next(i for i, stmt in enumerate(run_gui.body) if any(n is site for n in ast.walk(stmt)))
        self.assertLess(at, loops[0],
                        "스레드 시작이 %s 뒤에 있다 — 그 호출은 앱이 끝날 때까지 돌아오지 않으므로 "
                        "앱이 떠 있는 동안 치우기가 돌지 않는다(C20)" % event_loop)


class WindowsCliCwdTests(unittest.TestCase):
    """윈도우도 사설 cwd 에서 돈다 — WMI 로 만든 프로세스는 따로 주지 않으면 WmiPrvSE 의 작업
    디렉터리를 물려받는다(스펙 §Fix 3 win32). 윈도우 라운드 1(2026-09-30, 한 기계)의 실측으로
    그것은 C:\\Windows\\System32\\DriverStore\\FileRepository\\ntprint.inf_amd64_…\\Amd64 였고,
    그 폴더의 프로젝트 슬러그 아래 2026-09-23 부터 쌓인 트랜스크립트가 27개 있었다.

    Rivals: v0.26(cwd 를 넘기지 않음); 캐시 폴더 자체를 넘김; 이름만 넘기고 폴더를 만들지
    않음(Win32_Process.Create 가 없는 CurrentDirectory 로는 실패한다).
    """

    def test_the_windows_spawn_runs_in_the_private_cli_folder(self):
        seen = []

        def fake_wmi(cmdline, *args, **kw):
            cwd = kw.get("cwd", args[0] if args else None)
            seen.append({"cmdline": cmdline, "cwd": cwd,
                         "isdir": isinstance(cwd, str) and os.path.isdir(cwd)})
            return None

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(td.cleanup)
        root = os.path.realpath(td.name)
        cache = os.path.join(root, "Local", "me.yeongyu.claudepet")
        with mock.patch.object(claude_pet.sys, "platform", "win32"), \
             mock.patch.dict(os.environ, {"LOCALAPPDATA": os.path.join(root, "Local")}), \
             mock.patch.object(claude_pet, "RECOVERY_CACHE_DIR", cache, create=True), \
             mock.patch.object(claude_pet, "_recovery_cache_dir", return_value=cache), \
             mock.patch.object(claude_pet, "_win_wmi_create", new=fake_wmi), \
             mock.patch.object(claude_pet.subprocess, "Popen") as popen, \
             mock.patch.object(claude_pet.subprocess, "run"):
            fn = getattr(claude_pet, "recovery_cli_cwd", None)
            by_contract = fn() if callable(fn) else None
            if by_contract is not None:      # 하네스 안전장치 — 임시 폴더 밖이면 돌리지 않는다
                self.assertTrue(_is_under(by_contract, root),
                                "recovery_cli_cwd() 가 _recovery_cache_dir() 를 따르지 않는다")
            result = claude_pet._run_refresh_job([CLI, "-p", "/usage"], "lbl", "stem", 1)
        self.assertIsNone(result, "WMI 가 PID 를 주지 않았으면 None 이다")
        self.assertFalse(popen.called)
        self.assertEqual(len(seen), 1, "WMI 를 정확히 한 번 거쳐야 한다")
        self.assertIsNotNone(seen[0]["cwd"],
                             "_win_wmi_create 에 cwd 를 넘기지 않았다 — CLI 가 WmiPrvSE 의 작업 "
                             "디렉터리(라운드 1 실측: System32\\DriverStore\\…\\Amd64)에서 돈다")
        self.assertTrue(_same_path(seen[0]["cwd"], os.path.join(cache, "cli")),
                        "cwd 가 캐시 폴더 아래 cli 가 아니다: %r" % seen[0]["cwd"])
        self.assertIsNotNone(by_contract, "recovery_cli_cwd() 가 없다")
        self.assertTrue(_same_path(seen[0]["cwd"], by_contract))
        self.assertTrue(seen[0]["isdir"], "WMI 를 부를 때 cwd 폴더가 없었다")
        self.assertIn(CLI, seen[0]["cmdline"])


class WindowsWmiCwdTests(unittest.TestCase):
    """`_win_wmi_create(cmdline, cwd=None)` — cwd 는 명령줄과 같은 규칙을 따른다: PowerShell
    인용을 거치지 않도록 **자기 환경변수**로 건너가 `-Arguments @{…}` 의 CurrentDirectory 가
    된다. 경로에 작은따옴표·공백이 있어도 그대로 도착해야 한다.

    Rivals: cwd 를 스크립트 문자열에 끼워 넣음(작은따옴표에서 깨진다); 다른 환경변수 이름;
    해시테이블 밖에 둠; cwd 가 없는데도 CurrentDirectory 를 보냄; cwd 인자를 받지 않음(v0.26).
    """

    NAME = "CLAUDEPET_SPAWN_CWD"
    CWD = "C:\\Users\\O'Brien Smith\\AppData\\Local\\me.yeongyu.claudepet\\cli"
    CMDLINE = ('C:\\Windows\\System32\\cmd.exe /c '
               '"C:\\Users\\O\'Brien Smith\\.local\\bin\\claude.exe" -p /usage > '
               '"C:\\Users\\O\'Brien Smith\\AppData\\Local\\me.yeongyu.claudepet\\stem.out" 2>&1')

    def _create(self, **kw):
        calls = []

        def fake_run(argv, *a, **k):
            calls.append((list(argv), dict(k)))
            return subprocess.CompletedProcess(argv, 0, "4242", "")

        with mock.patch.object(claude_pet.sys, "platform", "win32"), \
             mock.patch.dict(os.environ), \
             mock.patch.object(claude_pet.subprocess, "run", new=fake_run):
            os.environ.pop(self.NAME, None)
            pid = claude_pet._win_wmi_create(self.CMDLINE, **kw)
        return pid, calls

    def _script(self, argv):
        self.assertIn("-Command", argv)
        return argv[argv.index("-Command") + 1]

    def test_the_cwd_rides_in_its_own_environment_variable(self):
        self.assertEqual(getattr(claude_pet, "WIN_SPAWN_CWD_ENV", None), self.NAME,
                         "WIN_SPAWN_CWD_ENV 가 스펙의 이름이 아니다")
        pid, calls = self._create(cwd=self.CWD)
        self.assertEqual(pid, 4242)
        self.assertEqual(len(calls), 1)
        argv, kw = calls[0]
        env = kw.get("env") or {}
        self.assertEqual(env.get(self.NAME), self.CWD, "cwd 가 환경변수로 건너가지 않았다")
        self.assertEqual(env.get(claude_pet.WIN_SPAWN_ENV), self.CMDLINE)
        script = self._script(argv)
        self.assertRegex(
            script, r"-Arguments\s*@\{[^}]*\bCurrentDirectory\s*=\s*\$env:%s\b[^}]*\}" % self.NAME,
            "CurrentDirectory=$env:%s 가 -Arguments 해시테이블 안에 없다" % self.NAME)
        self.assertRegex(script, r"\bCommandLine\s*=\s*\$env:%s\b" % claude_pet.WIN_SPAWN_ENV)
        for a in argv:
            self.assertNotIn("O'Brien", a, "경로가 PowerShell 인자에 그대로 들어갔다")

    def test_without_a_cwd_no_current_directory_is_sent(self):
        pid, calls = self._create(cwd=None)
        self.assertEqual(pid, 4242)
        argv, kw = calls[0]
        self.assertNotIn("CurrentDirectory", self._script(argv))
        self.assertNotIn(self.NAME, kw.get("env") or {})


# ── 윈도우: WMI 가 만드는 콘솔은 숨긴다 (2026-09-30, cwdfix 윈도우 라운드 1·1b) ──────────────
#
# 관측(윈도우 11 10.0.26200 한 대, Windows Terminal 이 콘솔 위임을 받는 기본 터미널인 기계,
# cwdfix-win-verify 가 2026-09-30 11:20–11:39 KST 에 측정 — scratchpad WIN-ROUND1/1B 보고):
# ProcessStartupInformation 없이 Win32_Process.Create 로 띄운 복구 스폰은 5회 중 5회 **보이는
# Windows Terminal 창**을 3–4초 띄웠다(수정 전·후 모두). Win32_ProcessStartup{ShowWindow=
# [uint16]0} 을 넘긴 변형 B 는 2회 중 2회 보이는 창이 0개였다(클래식 conhost 창은 있으나
# IsWindowVisible=False 이고 위임이 일어나지 않았다). ReturnValue·PID·출력·cwd·트랜스크립트
# 폴더·잔여 프로세스 0 은 같았다. CreateFlags 에 CREATE_NO_WINDOW 를 넣은 변형 C·D 는 2회씩
# 모두 ReturnValue 21 로 **아무것도 띄우지 못했다**. 그 기계·그 표본의 사실이다.
# 그래서 코드가 해야 하는 것(Coordinator 계약): 스크립트가 클라이언트 쪽에서 ShowWindow 가
# 0 인 Win32_ProcessStartup 을 만들어 Create 의 ProcessStartupInformation 으로 넘긴다 — cwd 가
# 있든 없든. CreateFlags 는 절대 두지 않는다. 명령줄과 cwd 는 여전히 두 환경변수로만 가고,
# PID 는 여전히 $r.ProcessId, 0 이 아닌 ReturnValue 는 여전히 None 이다.
# 모르는 것: 로그인 경로(브라우저를 여는 것)는 윈도우에서 돌려 보지 않았다. 타입 없는 0
# (PowerShell 에서 Int32)이 클라이언트 전용 인스턴스에서 받아들여지는지도 측정되지 않았다 —
# 그래서 아래 검사는 **측정된 형태**인 [uint16]0 을 요구한다.
#
# 실제 WMI 는 절대 부르지 않는다. PowerShell 로 넘어가는 -Command 스크립트를 읽어서 판단한다.
# 한 가지 철자에 묶이지 않도록 문장·해시테이블을 나눠 읽고, PowerShell 처럼 대소문자를
# 가리지 않는다(매개변수 순서, 변수 이름, 공백, 줄바꿈, 인라인 인스턴스 모두 허용).


def _ps_split(text, seps=";\n"):
    """PowerShell 텍스트를 최상위 구분자로 자른다 — 따옴표·괄호·중괄호 안은 자르지 않는다."""
    parts, buf, depth, quote, i = [], [], 0, None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                if i + 1 < len(text) and text[i + 1] == quote:   # '' · "" 는 따옴표 이스케이프
                    buf.append(text[i + 1])
                    i += 1
                else:
                    quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch in seps and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
        else:
            buf.append(ch)
        i += 1
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def _ps_braced(text, start):
    """text[start:] 가 '@{' 로 시작하면 짝이 맞는 '}' 까지의 조각, 아니면 None."""
    if not text.startswith("@{", start):
        return None
    depth, quote = 0, None
    for i in range(start + 1, len(text)):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _ps_hashtable(text):
    """'@{k=v; k2=v2}' → {k 소문자: v 원문}. 해시테이블이 아니면 None (PowerShell 키는 대소문자 무시)."""
    if not (isinstance(text, str) and text.startswith("@{") and text.endswith("}")):
        return None
    out = {}
    for entry in _ps_split(text[2:-1]):
        key, sep, value = entry.partition("=")
        if not sep:
            return None
        out[key.strip().strip("'\"").lower()] = value.strip()
    return out


def _ps_param(command, name):
    """명령 문장에서 `-name 값` 의 값 텍스트(해시테이블이면 @{…} 전체). 없으면 None."""
    m = re.search(r"(?i)(?<![\w-])-%s(?::|\s+)" % re.escape(name), command)
    if not m:
        return None
    if command.startswith("@{", m.end()):
        return _ps_braced(command, m.end())
    tokens = _ps_split(command[m.end():], seps=" \t")
    return tokens[0].strip("'\"") if tokens else None


_UINT16_ZERO = re.compile(r"(?i)^\[(?:system\.)?uint16\]\s*(?:0x)?0+$")


def _startup_instance_problem(expr):
    """expr 가 '클라이언트 쪽 Win32_ProcessStartup, ShowWindow=[uint16]0' 이면 None, 아니면 그 이유."""
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        expr = expr[1:-1].strip()
    m = re.match(r"(?is)^New-CimInstance\b(.*)$", expr)
    if not m:
        return "시작 정보가 New-CimInstance 로 만든 인스턴스가 아니다: %r" % expr[:80]
    args = m.group(1)
    cls = _ps_param(args, "ClassName")
    if cls is None:
        tokens = _ps_split(args, seps=" \t")
        cls = tokens[0].strip("'\"") if tokens and not tokens[0].startswith("-") else None
    if (cls or "").lower() != "win32_processstartup":
        return "Win32_ProcessStartup 인스턴스가 아니다: %r" % cls
    if not re.search(r"(?i)(?<![\w-])-ClientOnly\b", args):
        return "-ClientOnly 가 없다 — 서버에 만들려다 실패하고 기본 창 동작으로 돌아간다"
    props = _ps_hashtable(_ps_param(args, "Property"))
    if props is None:
        return "-Property @{…} 를 읽을 수 없다"
    if not _UINT16_ZERO.match(props.get("showwindow", "")):
        return "ShowWindow 가 [uint16]0(SW_HIDE)이 아니다: %r" % props.get("showwindow")
    return None


def _wmi_script_problems(script):
    """-Command 스크립트가 숨김 계약을 어기는 곳들의 목록. 비어 있으면 통과."""
    problems = []
    if re.search(r"(?i)createflags", script):
        problems.append("CreateFlags 를 둔다 — WMI 가 ReturnValue 21 로 거부해 아무것도 뜨지 않는다(1b 실측)")
    statements = _ps_split(script)
    bound = {}                         # 변수(소문자) → [(문장 번호, 오른쪽 식)]
    create = None
    for i, statement in enumerate(statements):
        m = re.match(r"(?s)^\$(\w+)\s*=\s*(.+)$", statement)
        if not m:
            continue
        var, expr = m.group(1).lower(), m.group(2).strip()
        bound.setdefault(var, []).append((i, expr))
        if re.match(r"(?i)^Invoke-CimMethod\b", expr):
            create = (i, var, expr)
    if create is None:
        return problems + ["Create 결과를 변수에 받는 Invoke-CimMethod 가 없다"]
    at, result, expr = create
    if not (re.search(r"(?i)(?<![\w-])-ClassName(?::|\s+)['\"]?Win32_Process['\"]?(?!\w)", expr)
            and re.search(r"(?i)(?<![\w-])-MethodName(?::|\s+)['\"]?Create\b", expr)):
        problems.append("Win32_Process 의 Create 호출이 아니다")
    args = _ps_hashtable(_ps_param(expr, "Arguments"))
    if args is None:
        return problems + ["Create 의 -Arguments @{…} 를 읽을 수 없다"]
    extra = sorted(set(args) - {"commandline", "currentdirectory", "processstartupinformation"})
    if extra:
        problems.append("Create 의 매개변수가 아닌 키가 있다: %s" % extra)
    info = args.get("processstartupinformation")
    if info is None:
        problems.append("ProcessStartupInformation 을 넘기지 않는다 — 기본값이면 콘솔이 "
                        "Windows Terminal 로 위임돼 보이는 창이 뜬다(1·1b 실측 5/5)")
    else:
        m = re.match(r"^\$(\w+)$", info)
        if m:
            earlier = [e for j, e in bound.get(m.group(1).lower(), []) if j < at]
            problem = (_startup_instance_problem(earlier[-1]) if earlier else
                       "ProcessStartupInformation 의 $%s 가 Create 앞에서 만들어지지 않았다"
                       % m.group(1))
        else:
            problem = _startup_instance_problem(info)
        if problem:
            problems.append(problem)
    if not re.search(r"(?i)\bif\s*\(\s*\$%s\.ReturnValue\s+-ne\s+0\s*\)\s*\{\s*exit\s+1\s*\}"
                     % re.escape(result), script):
        problems.append("Create 결과($%s)의 ReturnValue 가 0 이 아닐 때 exit 1 하지 않는다" % result)
    if not re.search(r"(?i)\[Console\]::Out\.Write\(\s*\$%s\.ProcessId\s*\)" % re.escape(result),
                     script):
        problems.append("PID 를 Create 결과($%s.ProcessId)에서 내보내지 않는다" % result)
    return problems


class WindowsHiddenConsoleTests(unittest.TestCase):
    """WMI 가 띄우는 콘솔은 **보이지 않게** 만든다 — 위 주석의 관측과 계약.

    Rivals(전부 돌려 봤다 — scratchpad cwdfix-win-hide-red.txt): 시작 정보 없음(현재 코드,
    그리고 '-WindowStyle Hidden 이면 된다' 는 판단 — 그 옵션은 PowerShell 자신만 숨긴다);
    CreateFlags 만(변형 C, ReturnValue 21); ShowWindow+CreateFlags(변형 D, 21); ShowWindow 가
    1·2 등 0 이 아닌 값; 인스턴스를 만들고 넘기지 않음; ShowWindow 를 Create 해시테이블에
    직접(Create 의 매개변수가 아니다); cwd 가 있을 때만 시작 정보를 붙임; -ClientOnly 없음;
    다른 변수를 넘김; Create 뒤에 만듦; 결과 배선(ReturnValue·ProcessId)을 다른 변수로.
    """

    NAME = WindowsWmiCwdTests.NAME
    CWD = WindowsWmiCwdTests.CWD
    CMDLINE = WindowsWmiCwdTests.CMDLINE
    _create = WindowsWmiCwdTests._create
    _script = WindowsWmiCwdTests._script

    def test_the_console_it_creates_is_hidden_with_and_without_a_cwd(self):
        for case, kw in (("cwd given", {"cwd": self.CWD}), ("cwd None", {"cwd": None}),
                         ("cwd omitted", {})):
            with self.subTest(case=case):
                pid, calls = self._create(**kw)
                self.assertEqual(len(calls), 1, "PowerShell 을 정확히 한 번 불러야 한다")
                argv, k = calls[0]
                script = self._script(argv)
                self.assertEqual(_wmi_script_problems(script), [],
                                 "숨김 계약 위반 — 받은 스크립트: %s" % script)
                self.assertEqual((k.get("env") or {}).get(claude_pet.WIN_SPAWN_ENV), self.CMDLINE,
                                 "명령줄은 여전히 환경변수로 건너가야 한다")
                for a in argv:
                    self.assertNotIn("O'Brien", a, "명령줄이나 cwd 가 PowerShell 인자에 그대로 들어갔다")
                self.assertEqual(pid, 4242)

    def test_a_failed_create_is_still_none_and_the_pid_still_comes_back(self):
        """**NOT A GATE** — 회귀 가드다(작성 시점에 초록이고 그래야 맞다). 숨김을 붙이면서
        파이썬 쪽 배선이 바뀌지 않았는지 본다: 0 이 아닌 종료 → None, 숫자가 아닌 출력 → None,
        0 이하 PID → None, 정상 → PID."""
        for rc, out, expected in ((0, "4242", 4242), (1, "", None), (0, "", None), (0, "0", None)):
            with self.subTest(rc=rc, stdout=out):
                def fake_run(argv, *a, _rc=rc, _out=out, **k):
                    return subprocess.CompletedProcess(argv, _rc, _out, "")
                with mock.patch.object(claude_pet.sys, "platform", "win32"), \
                        mock.patch.dict(os.environ), \
                        mock.patch.object(claude_pet.subprocess, "run", new=fake_run):
                    self.assertEqual(claude_pet._win_wmi_create(self.CMDLINE, cwd=self.CWD),
                                     expected)

    def test_the_checker_itself_accepts_b_and_rejects_its_rivals(self):
        """**NOT A GATE** — 계측기 검사다(claude_pet 을 보지 않는다). 위 게이트가 기대는
        _wmi_script_problems 가 측정된 변형 B 와 그 정당한 변형들은 받고, 경쟁 구현은 전부
        거절하는지 본다. 이것이 초록이 아니면 게이트의 초록은 아무것도 말하지 않는다."""
        head = "$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property "
        create = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
                  "@{CommandLine=$env:CLAUDEPET_SPAWN_CMDLINE; CurrentDirectory=$env:CLAUDEPET_SPAWN_CWD; %s}")
        tail = "; if ($r.ReturnValue -ne 0) { exit 1 }; [Console]::Out.Write($r.ProcessId)"
        b = head + "@{ShowWindow=[uint16]0}; " + create % "ProcessStartupInformation=$si" + tail
        accepted = {
            "B (1b, production string)": b,
            "B without cwd": b.replace("; CurrentDirectory=$env:CLAUDEPET_SPAWN_CWD", ""),
            "parameters reordered, other case and spacing":
                "$Startup = new-ciminstance -ClientOnly -classname win32_processstartup "
                "-property @{ ShowWindow = [UInt16]0 }; $R = invoke-cimmethod -MethodName Create "
                "-ClassName Win32_Process -Arguments @{ ProcessStartupInformation = $startup ; "
                "CommandLine = $env:CLAUDEPET_SPAWN_CMDLINE }" + tail.replace("$r", "$R"),
            "instance inline":
                create % ("ProcessStartupInformation=(New-CimInstance -ClassName Win32_ProcessStartup "
                          "-ClientOnly -Property @{ShowWindow=[uint16]0})") + tail,
            "newlines between statements, [System.UInt16]":
                (head + "@{ShowWindow=[System.UInt16]0}\n" + create % "ProcessStartupInformation=$si"
                 + tail).replace("; if", "\nif").replace("; [Console]", "\n[Console]"),
        }
        a = create % "X=1"
        a = a.replace("; X=1", "") + tail
        rejected = {
            "A: no startup information (current code)": a,
            "C: CreateFlags only": head + "@{CreateFlags=[uint32]0x08000000}; "
                                   + create % "ProcessStartupInformation=$si" + tail,
            "D: ShowWindow and CreateFlags": head + "@{ShowWindow=[uint16]0; CreateFlags=[uint32]0x08000000}; "
                                             + create % "ProcessStartupInformation=$si" + tail,
            "ShowWindow 1": b.replace("[uint16]0", "[uint16]1"),
            "ShowWindow 2": b.replace("[uint16]0", "[uint16]2"),
            "ShowWindow untyped 0 (unmeasured Int32)": b.replace("[uint16]0", "0"),
            "built but not passed": head + "@{ShowWindow=[uint16]0}; " + a,
            "ShowWindow in the Create hashtable": create % "ShowWindow=[uint16]0" + tail,
            "no -ClientOnly": b.replace(" -ClientOnly", ""),
            "another variable passed": b.replace("ProcessStartupInformation=$si",
                                                 "ProcessStartupInformation=$startup"),
            "made after Create": create % "ProcessStartupInformation=$si" + "; "
                                 + head + "@{ShowWindow=[uint16]0}" + tail,
            "ReturnValue check dropped": b.replace("if ($r.ReturnValue -ne 0) { exit 1 }; ", ""),
            "PID from the wrong object": b.replace("$r.ProcessId", "$si.ProcessId"),
            "CreateFlags 0 alongside ShowWindow": b.replace("@{ShowWindow=[uint16]0}",
                                                            "@{ShowWindow=[uint16]0; CreateFlags=[uint32]0}"),
            "wrong class": b.replace("Win32_ProcessStartup", "Win32_StartupCommand"),
        }
        for name, script in accepted.items():
            with self.subTest(accept=name):
                self.assertEqual(_wmi_script_problems(script), [], script)
        for name, script in rejected.items():
            with self.subTest(reject=name):
                self.assertNotEqual(_wmi_script_problems(script), [], script)


def _code_strings(fn):
    """함수 본문의 문자열 상수 — 독스트링은 뺀다(이력 설명에 'submit' 이 나오는 것은 괜찮다)."""
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return {n.value for stmt in body for n in ast.walk(stmt)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


class SubmitIsGoneTests(unittest.TestCase):
    """정적 보강 — 실행 테스트가 밟지 않는 분기(예: 특정 예외에서만 submit 으로 물러서기)까지
    본다. 스펙: "`launchctl submit` must no longer appear anywhere in the spawn path"."""

    def test_launchctl_submit_appears_nowhere_in_the_spawn_path(self):
        for name in ("recovery_spawn_argv", "login_spawn_argv", "_run_refresh_job",
                     "_launchctl_bootout"):
            with self.subTest(function=name):
                fn = _find_func(name)
                self.assertIsNotNone(fn, "%s 가 없다" % name)
                self.assertNotIn("submit", _code_strings(fn))


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

    def test_token_expired_follows_auth_error_whatever_the_logs_hold(self):
        """Rewritten 2026-10-05 (sou-verify, server-only-usage §1). The old guard pinned
        "entries==0 AND auth_error" and, for entries=5, an estimate segment. The spec now
        says 401/403 → ``token_expired`` "로그 유무와 무관하게", and there is no estimate to
        fall back to. Both fixtures must therefore read ``token_expired``; a rival that
        keeps the entries condition returns a non-status segment for entries=5.
        """
        stats = {"entries": 0, "spikes": {}, "model_kw": "fable"}
        seg = claude_pet.roam_summary("sub", None, stats, None, 0, False, None,
                                      auth_error=True)
        self.assertEqual(seg, ("status", "token_expired"))
        seg = claude_pet.roam_summary("sub", None, dict(stats, entries=5), None, 0,
                                      False, None, auth_error=True)
        self.assertEqual(seg, ("status", "token_expired"))

if __name__ == "__main__":
    unittest.main()
