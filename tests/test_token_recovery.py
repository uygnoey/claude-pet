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
  launchctl` 의 submit 은 "keep the program alive in the event of failure" 이고 작업
  디렉터리 옵션이 없다 — 그래서 CLI 는 launchd 의 기본 cwd 인 `/` 에서 돈다.
* 관측(Coordinator 가 2026-09-30 09:05–09:31 KST 에 수집, 이 맥 한 대, CLI 2.1.284 —
  cwdfix 스펙의 Evidence 절): launchd 로그에서 06:15:29 에 뜬 그 job 의 CLI 가 06:16:17 에
  끝나자 곧바로 다시 떠서 스폰 한 번이 CLI 실행 두 번이 됐다. tccd 로그 2026-09-30
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
        돌린다); `launchctl submit`(cwd 옵션 없음, 실패 시 재실행); submit + `env -C`;
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
                             "launchctl submit — cwd 를 정할 수 없고 실패한 job 을 살려 둔다")
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
        """v0.26 의 두 번째 원인: submit 은 실패한 job 을 살려 둔다 — 관측(모듈 주석)에서
        스폰 한 번이 CLI 실행 두 번이 됐다. 로그인이라면 취소할 때마다 브라우저가 다시 뜬다.
        Rivals: KeepAlive true; KeepAlive {SuccessfulExit: false}(= 실패하면 재실행, 정확히
        그 버그); 옛 이름 OnDemand false; RunAtLoad 없음(올려도 안 뜬다); 주기·감시 트리거."""
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
        """로그인은 keep-alive 의 대가가 가장 크다 — 취소하거나 실패한 `claude auth login` 이
        LOGIN_TIMEOUT_SEC 까지 다시 떠서 브라우저를 또 연다(스펙 근본 원인 2)."""
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
