#!/usr/bin/env python3
"""
Claude Pet — Codex Pets 스타일 투명 오버레이 펫 + Claude 토큰 사용량
=====================================================================
- 창 프레임/타이틀 없음, 배경 완전 투명 (펫과 게이지만 화면에 떠 있음)
- 스프라이트: ~/.codex/pet-runs/patch-entp-cat/frames 의 Patch 고양이 프레임 사용
- 게이지 3종: 현재 세션(5h) / 주간 전체 / 주간 Opus — 남은량 + 리셋 카운트다운
- 한도 도달 정도에 따라 펫 모션이 변함 (모션별 고유 속도/반복 설정)
    <50%  idle(평온)  /  50~85% waiting(초조)  /  ≥85% failed(패닉)
    드래그하면 방향에 맞춰 running-left/right, 더블클릭 waving, 리셋 감지 시 jumping

실행:
  pip3 install pyobjc-framework-Cocoa   # 최초 1회
  python3 claude_pet.py                  # 펫 실행
  python3 claude_pet.py --report         # GUI 없이 사용량 출력

렌더링: macOS 네이티브 AppKit (잔상 없는 진짜 투명 오버레이)
"""

import json
import os
import re
import sys
import glob
import time
import shutil
import threading
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone

# ──────────────────────────── 설정 ────────────────────────────
def _default_pet_dir():
    # 1) 환경변수 → 2) 스크립트 옆 frames (앱 번들 내장) → 3) codex 펫 폴더
    env = os.environ.get("CLAUDE_PET_SPRITES")
    if env:
        return os.path.expanduser(env)
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
    if os.path.isdir(here):
        return here
    return os.path.expanduser("~/.codex/pet-runs/patch-entp-cat/frames")

PET_DIR = _default_pet_dir()
PET_SCALE_DOWN = int(os.environ.get("CLAUDE_PET_SCALE_DOWN", 1))  # 1=원본 크기

SESSION_HOURS = 5
REFRESH_SEC = 30

# 런타임 설정 — 환경변수가 기본값, ~/.claude_pet.json(설정 UI)이 덮어씀
RUNTIME = {
    "mode": "sub",   # "sub"=구독(Claude Code 로그) / "api"=Admin API 비용
    # 한도(토큰) 추정치 — 공식 공개값 아님. Settings > Usage와 비교해 보정.
    "session_limit": int(os.environ.get("CLAUDE_PET_SESSION_LIMIT", 8_000_000)),
    "weekly_limit":  int(os.environ.get("CLAUDE_PET_WEEKLY_LIMIT", 60_000_000)),
    "opus_limit":    int(os.environ.get("CLAUDE_PET_OPUS_LIMIT", 15_000_000)),
    "spike_mult": 1.0,          # 급증 민감도 배율 (0.5=민감, 1=보통, 2=둔감)
    "greet": os.environ.get("CLAUDE_PET_FOLLOW", "1") != "0",
    "admin_key": os.environ.get("ANTHROPIC_ADMIN_KEY", ""),
    "api_budget": 0.0,          # API 모드 월 예산($), 0이면 게이지 없음
    # 모델별 한도 게이지의 모델 키워드. "auto"면 로그에서 상위 티어 자동 감지
    # (앱의 모델별 한도 대상이 Opus → Fable 처럼 시기마다 바뀌므로 auto 권장)
    "model_keyword": os.environ.get("CLAUDE_PET_MODEL", "auto"),
    # 주간 리셋 요일/시각 (앱의 "(토) 오후 8:00에 재설정" 같은 것)
    # None이면 롤링 7일. 0=월 ... 5=토, 6=일
    "weekly_reset_day": None,
    "weekly_reset_hour": 20,
}

def apply_config(cfg):
    for k in ("mode", "session_limit", "weekly_limit", "opus_limit",
              "spike_mult", "greet", "admin_key", "api_budget",
              "model_keyword", "weekly_reset_day", "weekly_reset_hour"):
        if k in cfg:
            RUNTIME[k] = cfg[k]

# 모션별 (프레임 간격 ms, 반복, 루프 후 휴식 ms) — 평소엔 얌전히!
# 휴식 중엔 첫 프레임으로 정지. idle은 8초에 한 번만 숨쉬기/깜빡임.
STATE_CFG = {
    "idle":          (430, True,  25000),  # 25초에 한 번만 숨쉬기
    "waiting":       (340, True,  12000),  # 가끔만 꼼지락
    "failed":        (260, True,  6000),   # 패닉도 6초에 한 번만
    "waving":        (200, False, 0),      # 인사 — 한 번만
    "jumping":       (150, False, 0),      # 점프 — 한 번만
    "running-left":  (90,  True,  0),      # 달릴 때만 연속 재생
    "running-right": (90,  True,  0),
    "running":       (90,  True,  0),
    "review":        (360, True,  20000),
}
DEFAULT_CFG = (400, True, 15000)

# 소비 급증 기본 임계치(%): 최근 5분 소비가 한도의 몇 %를 넘으면 경보
# 실제 임계치 = 기본값 × RUNTIME["spike_mult"] (설정 UI의 민감도)
SPIKE_BASE = {"session": 1.0, "weekly": 0.5, "opus": 1.0}

CONFIG_PATH = os.path.expanduser("~/.claude_pet.json")

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass

LOG_DIRS = [
    os.path.expanduser("~/.claude/projects"),
    os.path.expanduser("~/.config/claude/projects"),
]

# ─────────────────────── 로그 파싱 ───────────────────────

def _iter_log_files():
    for d in LOG_DIRS:
        if os.path.isdir(d):
            yield from glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)


def parse_usage_entries(since: datetime):
    """since 이후의 (timestamp, total_tokens, model). 메시지 중복 제거."""
    entries, seen = [], set()
    for path in _iter_log_files():
        try:
            if datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc) < since:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = obj.get("message") or {}
                    usage = msg.get("usage") or obj.get("usage")
                    ts_raw = obj.get("timestamp")
                    if not usage or not ts_raw:
                        continue
                    key = (msg.get("id"), obj.get("requestId"))
                    if key != (None, None) and key in seen:
                        continue
                    seen.add(key)
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if ts < since:
                        continue
                    # 비용 가중 토큰: 실제 한도는 비용 기준으로 차감되는 것으로
                    # 보이므로 API 단가 비율로 가중 (입력1/출력5/캐시쓰기1.25/캐시읽기0.1)
                    # → 사용 패턴(캐시 비중)이 바뀌어도 % 보정이 유지됨
                    w_in = usage.get("input_tokens", 0)
                    w_out = usage.get("output_tokens", 0) * 5.0
                    w_cw = usage.get("cache_creation_input_tokens", 0) * 1.25
                    w_cr = usage.get("cache_read_input_tokens", 0) * 0.1
                    noncache = w_in + w_out + w_cw
                    total = noncache + w_cr
                    if total > 0:
                        entries.append((ts, total,
                                        (msg.get("model") or "").lower(),
                                        noncache))
        except OSError:
            continue
    entries.sort(key=lambda e: e[0])
    return entries


def _weekly_window_start():
    """설정된 주간 리셋 요일/시각 기준 이번 주 시작(UTC). 미설정이면 None(롤링)."""
    wday = RUNTIME.get("weekly_reset_day")
    if wday is None:
        return None
    try:
        hh = int(RUNTIME.get("weekly_reset_hour", 20))
        nl = datetime.now().astimezone()
        back = (nl.weekday() - int(wday)) % 7
        ls = (nl - timedelta(days=back)).replace(hour=hh, minute=0,
                                                 second=0, microsecond=0)
        if ls > nl:
            ls -= timedelta(days=7)
        return ls.astimezone(timezone.utc)
    except Exception:
        return None


# 상위 티어 모델 패밀리, 최신 우선 (모델별 주간 한도가 걸리는 대상)
PREMIUM_FAMILIES = ["fable", "mythos", "opus"]

def _detect_model_keyword(wk_entries, all_entries):
    """모델 게이지 대상 자동 감지 — 앱과 같은 기준:
    이번 주간 창에서 사용된 가장 최신 상위 티어 (없으면 전체 로그에서)."""
    for pool in (wk_entries, all_entries):
        for fam in PREMIUM_FAMILIES:          # 최신 우선
            if any(fam in e[2] and e[1] > 0 for e in pool):
                return fam
    return "opus"


def compute_usage():
    now = datetime.now(timezone.utc)
    entries = parse_usage_entries(now - timedelta(days=7))

    week_start = _weekly_window_start()
    wk_entries = [e for e in entries
                  if week_start is None or e[0] >= week_start]
    kw = str(RUNTIME.get("model_keyword", "auto")).lower().strip()
    if kw in ("auto", ""):
        kw = _detect_model_keyword(wk_entries, entries)
    weekly = sum(e[1] for e in wk_entries)
    weekly_opus = sum(e[1] for e in wk_entries if kw in e[2])

    # 세션 블록: 앱과 같은 방식으로 5시간 단위 타일링.
    # 블록이 끝난 뒤 첫 활동 시각(정시 스냅)에 새 블록이 시작됨.
    # (연속 사용 시에도 5시간마다 정확히 리셋되어 앱 %와 어긋나지 않음)
    session_tokens, session_reset, last_activity = 0, None, None
    if entries:
        last_activity = entries[-1][0]
        block_start = block_end = None
        for e in entries:
            if block_end is None or e[0] >= block_end:
                block_start = e[0].replace(minute=0, second=0, microsecond=0)
                block_end = block_start + timedelta(hours=SESSION_HOURS)
        if now < block_end:  # 현재 블록이 아직 유효
            session_reset = block_end
            session_tokens = sum(e[1] for e in entries
                                 if block_start <= e[0] < block_end)

    # 주간 리셋: 설정된 요일/시각이 있으면 그 기준, 없으면 롤링 7일
    if week_start is not None:
        weekly_reset = week_start + timedelta(days=7)
    else:
        weekly_reset = entries[0][0] + timedelta(days=7) if entries else None

    # 소비 급증 감지 — "평소보다 갑자기 많이" 쓸 때만.
    # 캐시 읽기 토큰은 제외(항상 커서 오탐 유발)하고,
    # 최근 5분 소비가 (a) 한도 대비 임계치 이상 AND (b) 직전 25분 평균의 2.5배 이상
    five_ago = now - timedelta(minutes=5)
    thirty_ago = now - timedelta(minutes=30)
    burn_all = sum(e[3] for e in entries if e[0] >= five_ago)
    burn_opus = sum(e[3] for e in entries if e[0] >= five_ago and kw in e[2])
    prev_all = sum(e[3] for e in entries if thirty_ago <= e[0] < five_ago)
    prev_opus = sum(e[3] for e in entries
                    if thirty_ago <= e[0] < five_ago and kw in e[2])
    base_all = prev_all / 5.0    # 직전 25분의 5분당 평균
    base_opus = prev_opus / 5.0
    mult = float(RUNTIME.get("spike_mult", 1.0)) or 1.0

    def is_spike(burn, base, limit, base_pct):
        floor = limit * base_pct * mult / 100
        return burn >= floor and burn >= 2.5 * max(base, floor / 5)

    spikes = {
        "session": is_spike(burn_all, base_all,
                            RUNTIME["session_limit"], SPIKE_BASE["session"]),
        "weekly":  is_spike(burn_all, base_all,
                            RUNTIME["weekly_limit"], SPIKE_BASE["weekly"]),
        "opus":    is_spike(burn_opus, base_opus,
                            RUNTIME["opus_limit"], SPIKE_BASE["opus"]),
    }

    def gauge(used, limit, reset):
        pct = min(100.0, used / limit * 100) if limit else 0.0
        return {"used": used, "limit": limit, "left": max(0, limit - used),
                "pct": pct, "reset": reset}

    return {
        "session": gauge(session_tokens, RUNTIME["session_limit"], session_reset),
        "weekly":  gauge(weekly, RUNTIME["weekly_limit"], weekly_reset),
        "opus":    gauge(weekly_opus, RUNTIME["opus_limit"], weekly_reset),
        "burn_5m": burn_all,
        "burn_5m_opus": burn_opus,
        "spikes": spikes,
        "model_kw": kw,
        "last_activity": last_activity,
        "now": now,
    }

# ─────────────────────── Admin API (선택) ───────────────────────

def fetch_api_cost(start_dt):
    """start_dt(UTC)부터 지금까지 비용(USD). 키 없거나 실패하면 None."""
    key = RUNTIME.get("admin_key", "")
    if not key:
        return None
    url = ("https://api.anthropic.com/v1/organizations/cost_report"
           f"?starting_at={start_dt:%Y-%m-%dT%H:%M:%SZ}&bucket_width=1d")
    req = urllib.request.Request(url, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        total = 0.0
        for b in data.get("data", []):
            for item in b.get("results", []):
                amt = item.get("amount")
                total += float(amt.get("value", 0)) if isinstance(amt, dict) else float(amt or 0)
        return total
    except Exception:
        return None


def fetch_api_cost_today():
    now = datetime.now(timezone.utc)
    return fetch_api_cost(now.replace(hour=0, minute=0, second=0, microsecond=0))


def fetch_api_cost_month():
    now = datetime.now(timezone.utc)
    return fetch_api_cost(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))

# ─────────────── OAuth 사용량 API (정확 모드) ───────────────
# Claude Code의 /usage 명령이 쓰는 것과 같은 엔드포인트.
# 성공하면 서버가 계산한 정확한 %를 그대로 표시 → 보정 불필요.
# 실패(토큰 없음/429 등)하면 로컬 로그 추정으로 폴백.

OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_CACHE_SEC = 180   # 과호출 시 429 → 3분 캐시 필수
_oauth_cache = {"t": 0.0, "gauges": None}


def _read_oauth_token():
    """Claude Code OAuth 토큰: macOS 키체인 → ~/.claude/.credentials.json 순."""
    if sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["security", "find-generic-password",
                 "-s", "Claude Code-credentials", "-w"],
                capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout.strip())
                tok = (data.get("claudeAiOauth") or {}).get("accessToken")
                if tok:
                    return tok
        except Exception:
            pass
    try:
        with open(os.path.expanduser("~/.claude/.credentials.json")) as f:
            data = json.load(f)
        return (data.get("claudeAiOauth") or {}).get("accessToken")
    except Exception:
        return None


def _oauth_label(key):
    k = key.lower()
    if "five_hour" in k or "session" in k:
        return ("세션", 0)
    if "seven_day" in k or "weekly" in k:
        for fam in PREMIUM_FAMILIES + ["sonnet", "haiku"]:
            if fam in k:
                return (fam.capitalize(), 2)
        return ("주간", 1)
    if "extra" in k or "credit" in k:
        return ("크레딧", 9)   # 추가 사용량(크레딧) — 주요 3개 있으면 잘림
    return (key, 5)


def _parse_oauth_usage(data):
    """응답에서 utilization 항목을 관용적으로 수집 → [(label, pct, reset_dt)]"""
    found = []

    def walk(obj, hint):
        if isinstance(obj, list):
            for item in obj:
                walk(item, hint)
            return
        if not isinstance(obj, dict):
            return
        if "utilization" in obj:
            try:
                pct = float(obj.get("utilization") or 0)
            except (TypeError, ValueError):
                return
            if pct <= 1.5:
                pct *= 100
            raw = obj.get("resets_at") or obj.get("reset_at") or obj.get("resets")
            rdt = None
            if raw is not None:
                try:
                    rdt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except ValueError:
                    try:
                        rdt = datetime.fromtimestamp(float(raw), tz=timezone.utc)
                    except (TypeError, ValueError):
                        pass
            # 항목 안에 model/name이 있으면 라벨 힌트에 포함 (모델별 주간 한도)
            model_hint = str(obj.get("model") or obj.get("name") or
                             obj.get("label") or "")
            label, order = _oauth_label(f"{hint}_{model_hint}".lower())
            found.append((order, label, min(100.0, max(0.0, pct)), rdt))
        else:
            for k, v in obj.items():
                walk(v, f"{hint}_{k}" if hint else k)

    walk(data, "")
    found.sort(key=lambda x: x[0])
    # 같은 라벨 중복 제거. (label, pct, reset_dt, reset_text)
    seen, rows = set(), []
    for _, label, pct, rdt in found:
        if label in seen:
            continue
        seen.add(label)
        rows.append((label, pct, rdt, None))
    return rows[:PILL_ROWS] or None


def _label_order(label):
    if label == "세션":
        return 0
    if label == "주간":
        return 1
    if label == "크레딧":
        return 9
    if label.lower() in PREMIUM_FAMILIES + ["sonnet", "haiku"]:
        return 2
    return 5


def _fetch_oauth_usage():
    tok = _read_oauth_token()
    if not tok:
        return None
    req = urllib.request.Request(OAUTH_USAGE_URL, headers={
        "Authorization": f"Bearer {tok}",
        "User-Agent": "claude-code/2.1.0",   # 없으면 429 버킷에 걸림
        "anthropic-beta": "oauth-2025-04-20",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        return _parse_oauth_usage(data)
    except Exception:
        return None


def _find_claude_cli():
    for p in (shutil.which("claude"),
              os.path.expanduser("~/.claude/local/claude"),
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        if p and os.path.exists(p):
            return p
    return None


_CLI_LINE = re.compile(
    r"Current (session|week \(([^)]*)\)):\s*(\d+(?:\.\d+)?)% used"
    r"(?:\s*·\s*resets (.*))?")


def _fetch_cli_usage():
    """`claude -p /usage` 출력 파싱 — OAuth 실패 시 폴백."""
    cli = _find_claude_cli()
    if not cli:
        return None
    try:
        r = subprocess.run([cli, "-p", "/usage"], capture_output=True,
                           text=True, timeout=90)
    except Exception:
        return None
    rows = []
    for line in (r.stdout or "").splitlines():
        m = _CLI_LINE.search(line)
        if not m:
            continue
        if m.group(1) == "session":
            label = "세션"
        else:
            scope = (m.group(2) or "").strip().lower()
            label = "주간" if scope.startswith("all") else (m.group(2) or "모델").strip()
        txt = (m.group(4) or "").strip() or None
        if txt:
            txt = re.sub(r"\s*\([^)]*\)\s*$", "", txt)  # (Asia/Seoul) 제거
        rows.append((label, float(m.group(3)), None, txt))
    return rows[:PILL_ROWS] or None


def fetch_exact_usage():
    """정확 사용량 [(label, pct, reset_dt, reset_text)] 최대 4줄.
    OAuth 우선, 모델별(Fable 등) 줄이 없으면 CLI(claude -p /usage)에서 보충.
    180초 캐시 (과호출 시 429)."""
    now = time.time()
    if now - _oauth_cache["t"] < OAUTH_CACHE_SEC:
        return _oauth_cache["gauges"]
    _oauth_cache["t"] = now
    rows = _fetch_oauth_usage()
    if rows is None:
        rows = _fetch_cli_usage()
    elif not any(_label_order(r[0]) == 2 for r in rows):
        # OAuth 응답에 모델별 항목이 없으면 CLI에서 Fable 줄 보충
        cli = _fetch_cli_usage() or []
        have = {r[0] for r in rows}
        for r in cli:
            if r[0] not in have:
                rows.append(r)
    if rows:
        rows = sorted(rows, key=lambda r: _label_order(r[0]))[:PILL_ROWS]
    _oauth_cache["gauges"] = rows
    return rows

# ─────────────────────── 유틸 ───────────────────────

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(int(n))


def fmt_countdown(reset, now):
    if not reset:
        return "-"
    d = reset - now
    if d.total_seconds() <= 0:
        return "리셋됨"
    h, rem = divmod(int(d.total_seconds()), 3600)
    m = rem // 60
    if h >= 24:
        return f"{h//24}일 {h%24}시간 후"
    return f"{h}시간 {m}분 후" if h else f"{m}분 후"


def worst_pct(stats):
    return max(stats["session"]["pct"], stats["weekly"]["pct"], stats["opus"]["pct"])


def mood_for(stats):
    pct = worst_pct(stats)
    if pct >= 85:
        return "failed"
    if pct >= 50:
        return "waiting"
    return "idle"


# ─────────────────── 픽셀 지오메트리 (GUI/미리보기 공용) ───────────────────

PILL_W = 330          # 상태 필 너비
PILL_R = 18           # 라운드 반경
PILL_PAD = 13         # 필 내부 패딩
ROW_H = 30            # 필 안 행 높이
PILL_ROWS = 4         # 세션 / 주간 / 모델(Fable 등) / 크레딧
PILL_H = PILL_PAD * 2 + ROW_H * PILL_ROWS - 6
GAP = 6               # 펫-필 간격
BTN_R = 13            # 접기 버튼 반지름

PILL_BG = "#1C1C1F"
TRACK = "#3A3A3F"
TXT_MAIN = "#F2F2F7"
TXT_SUB = "#98989F"
COL_OK, COL_WARN, COL_BAD = "#32D74B", "#FFD60A", "#FF453A"


def bar_color(pct):
    return COL_OK if pct < 50 else (COL_WARN if pct < 85 else COL_BAD)


def gauge_rows(stats):
    model_label = str(stats.get("model_kw", "opus")).capitalize()
    return [("세션", stats["session"]), ("주간", stats["weekly"]),
            (model_label, stats["opus"])]

# ─────────────────────── GUI (macOS 네이티브 AppKit) ───────────────────────
# 행동 원칙:
#   · 평소엔 첫 프레임으로 "정지". 25초에 한 번만 숨쉬기
#   · 마우스가 가까이 오면 인사 (쿨다운 30초)
#   · 잡고 끌면 끄는 방향으로 달리기, 더블클릭 점프
#   · 토큰 소비 급증: 경고색 펄스 + 패닉 표정 + 게이지 ▲급증
#   · 스크롤 = 크기 조절 / 우클릭 = 메뉴(설정·접기·종료)

def run_gui():
    import math
    import time as _time
    try:
        from AppKit import (
            NSApplication, NSWindow, NSPanel, NSView, NSColor, NSImage, NSFont,
            NSBezierPath, NSMakeRect, NSMakePoint, NSScreen, NSTimer, NSEvent,
            NSMenu, NSMenuItem, NSTextField, NSSecureTextField, NSPopUpButton,
            NSButton, NSWindowStyleMaskBorderless, NSWindowStyleMaskTitled,
            NSWindowStyleMaskClosable, NSBackingStoreBuffered,
            NSFontAttributeName, NSForegroundColorAttributeName,
            NSCompositingOperationSourceOver, NSCompositingOperationSourceAtop,
            NSZeroRect, NSRectFillUsingOperation,
        )
        from Foundation import NSObject, NSAttributedString
        from PyObjCTools import AppHelper
    except ImportError:
        print("macOS 네이티브 렌더링에 pyobjc가 필요합니다. 설치:", file=sys.stderr)
        print("  pip3 install pyobjc-framework-Cocoa", file=sys.stderr)
        sys.exit(1)

    def hexcolor(h, a=1.0):
        h = h.lstrip("#")
        r, g_, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
        return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g_, b, a)

    C_PILL = hexcolor(PILL_BG, 0.96)
    C_TRACK = hexcolor(TRACK)
    C_MAIN = hexcolor(TXT_MAIN)
    C_SUB = hexcolor(TXT_SUB)
    C_BTNL = hexcolor("#2E2E33")

    F_BOLD = {NSFontAttributeName: NSFont.boldSystemFontOfSize_(12),
              NSForegroundColorAttributeName: C_MAIN}
    F_BIG = {NSFontAttributeName: NSFont.boldSystemFontOfSize_(15),
             NSForegroundColorAttributeName: C_MAIN}
    F_SUB = {NSFontAttributeName: NSFont.systemFontOfSize_(9.5),
             NSForegroundColorAttributeName: C_SUB}
    F_ALERT = {NSFontAttributeName: NSFont.boldSystemFontOfSize_(9.5),
               NSForegroundColorAttributeName: hexcolor(COL_BAD)}
    F_TINY = {NSFontAttributeName: NSFont.systemFontOfSize_(8.5),
              NSForegroundColorAttributeName: hexcolor("#5A5A60")}
    F_CHEV = {NSFontAttributeName: NSFont.boldSystemFontOfSize_(12),
              NSForegroundColorAttributeName: C_SUB}

    def astr(s, attrs):
        return NSAttributedString.alloc().initWithString_attributes_(s, attrs)

    # ── 스프라이트 로드 ──
    frames = {}
    if os.path.isdir(PET_DIR):
        for st in os.listdir(PET_DIR):
            sd = os.path.join(PET_DIR, st)
            if not os.path.isdir(sd):
                continue
            imgs = [NSImage.alloc().initWithContentsOfFile_(p)
                    for p in sorted(glob.glob(os.path.join(sd, "*.png")))]
            imgs = [i for i in imgs if i]
            if imgs:
                frames[st] = imgs
    if not frames.get("idle"):
        print(f"스프라이트를 찾지 못했습니다: {PET_DIR}", file=sys.stderr)
        sys.exit(1)
    for need in ("waiting", "failed", "waving", "running-left",
                 "running-right", "jumping"):
        frames.setdefault(need, frames["idle"])

    sz = frames["idle"][0].size()
    PW0 = int(sz.width // PET_SCALE_DOWN)
    PH0 = int(sz.height // PET_SCALE_DOWN)

    cfg = load_config()
    apply_config(cfg)
    g = {"scale": max(0.3, min(2.0, float(cfg.get("scale", 0.5))))}  # 기본 0.5×

    def geom():
        pw = int(PW0 * g["scale"])
        ph = int(PH0 * g["scale"])
        w = max(pw + BTN_R * 2 + 16, PILL_W + 8)
        h = ph + GAP + PILL_H + 4
        return pw, ph, w, h

    PW, PH, W, H = geom()

    state = {"stats": None, "cost": None, "cost_month": None, "oauth": None,
             "frame": 0, "mood": "idle", "override": None, "show_panel": True,
             "elapsed": 0.0, "resting": False, "rest_elapsed": 0.0,
             "last_mood": "idle", "dragging": False, "greet_cool": 0.0,
             "hover": False}
    sticky = {"on": False}
    ui = {}   # 설정 창 위젯 참조 (GC 방지)

    TICK = 0.05
    NEAR_PX = 100
    GREET_COOLDOWN = 30.0

    def set_override(name, sticky_flag=False):
        if state["override"] != name:
            state["frame"] = 0
            state["elapsed"] = 0.0
            state["resting"] = False
        state["override"] = name
        sticky["on"] = sticky_flag

    def clear_sticky():
        if sticky["on"]:
            sticky["on"] = False
            state["override"] = None
            state["frame"] = 0

    def spike_info(stats):
        if not stats or RUNTIME["mode"] == "api":
            return None
        sp = stats.get("spikes") or {}
        if sp.get("session"):
            return ("#FF453A", "세션")
        if sp.get("opus"):
            return ("#BF5AF2", "Opus")
        if sp.get("weekly"):
            return ("#FF9F0A", "주간")
        return None

    def current_mood():
        if state["override"]:
            return state["override"]
        stats = state["stats"]
        if stats and spike_info(stats):
            return "failed"
        if state["oauth"]:   # 정확 모드: 서버 %가 기준
            pct = max((row[1] for row in state["oauth"]), default=0)
            return "failed" if pct >= 85 else ("waiting" if pct >= 50 else "idle")
        return mood_for(stats) if stats else "idle"

    # ── 필 그리기 헬퍼 (클래스 밖: PyObjC 셀렉터 변환 회피) ──
    def draw_sub_pill(gx0, gy0, stats):
        sp = stats.get("spikes") or {}
        keys = ["session", "weekly", "opus"]
        for i, (label, gg) in enumerate(gauge_rows(stats)):
            ry = gy0 + PILL_PAD + i * ROW_H
            astr(label, F_BOLD).drawAtPoint_(
                NSMakePoint(gx0 + PILL_PAD + 2, ry - 2))
            spiking = sp.get(keys[i])
            txt = (f"{gg['pct']:.0f}% · 남음 {fmt_tokens(gg['left'])}"
                   f" · {fmt_countdown(gg['reset'], stats['now'])}")
            if spiking:
                txt = "▲급증 " + txt
            sub = astr(txt, F_ALERT if spiking else F_SUB)
            ss = sub.size()
            sub.drawAtPoint_(
                NSMakePoint(gx0 + PILL_W - PILL_PAD - ss.width, ry))
            bx0 = gx0 + PILL_PAD + 2
            bw = PILL_W - PILL_PAD * 2 - 4
            C_TRACK.set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17, bw, 6), 3, 3).fill()
            hexcolor(COL_BAD if spiking else bar_color(gg["pct"])).set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17,
                           max(8, bw * gg["pct"] / 100), 6), 3, 3).fill()
        if state["cost"] is not None:
            c = astr(f"오늘 API ${state['cost']:.2f}", F_TINY)
            cw = c.size()
            c.drawAtPoint_(NSMakePoint(
                gx0 + PILL_W - PILL_PAD - cw.width, gy0 + PILL_H - 15))

    def draw_exact_pill(gx0, gy0, rows):
        """정확 모드: OAuth/CLI에서 받은 서버 계산 % 표시 (보정 불필요)."""
        stats = state["stats"]
        now_utc = datetime.now(timezone.utc)
        for i, (label, pct, rdt, rtxt) in enumerate(rows[:PILL_ROWS]):
            ry = gy0 + PILL_PAD + i * ROW_H
            astr(label, F_BOLD).drawAtPoint_(
                NSMakePoint(gx0 + PILL_PAD + 2, ry - 2))
            if rdt is not None:
                reset_s = "리셋 " + fmt_countdown(rdt, now_utc)
            elif rtxt:
                reset_s = "리셋 " + rtxt
            else:
                reset_s = ""
            sub = astr(f"{pct:.0f}% 사용" + (f" · {reset_s}" if reset_s else ""),
                       F_SUB)
            ss = sub.size()
            sub.drawAtPoint_(
                NSMakePoint(gx0 + PILL_W - PILL_PAD - ss.width, ry))
            bx0 = gx0 + PILL_PAD + 2
            bw = PILL_W - PILL_PAD * 2 - 4
            C_TRACK.set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17, bw, 6), 3, 3).fill()
            spiking = bool(spike_info(stats)) and i == 0
            hexcolor(COL_BAD if spiking else bar_color(pct)).set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17, max(8, bw * pct / 100), 6), 3, 3).fill()
        if len(rows) < PILL_ROWS:
            tag = astr("정확 모드", F_TINY)
            ts_ = tag.size()
            tag.drawAtPoint_(NSMakePoint(gx0 + PILL_W - PILL_PAD - ts_.width,
                                         gy0 + PILL_H - 15))

    def draw_api_pill(gx0, gy0):
        if not RUNTIME.get("admin_key"):
            m = astr("우클릭 → 설정에서 Admin API 키를 입력하세요", F_SUB)
            ms = m.size()
            m.drawAtPoint_(NSMakePoint(gx0 + (PILL_W - ms.width) / 2,
                                       gy0 + (PILL_H - ms.height) / 2))
            return
        today = state["cost"]
        month = state["cost_month"]
        ry = gy0 + PILL_PAD
        astr("오늘", F_BOLD).drawAtPoint_(NSMakePoint(gx0 + PILL_PAD + 2, ry))
        t = astr("조회 중..." if today is None else f"${today:.2f}", F_BIG)
        ts = t.size()
        t.drawAtPoint_(NSMakePoint(gx0 + PILL_W - PILL_PAD - ts.width, ry - 3))
        ry += ROW_H
        astr("이번 달", F_BOLD).drawAtPoint_(NSMakePoint(gx0 + PILL_PAD + 2, ry))
        m2 = astr("조회 중..." if month is None else f"${month:.2f}", F_BIG)
        m2s = m2.size()
        m2.drawAtPoint_(NSMakePoint(gx0 + PILL_W - PILL_PAD - m2s.width, ry - 3))
        ry += ROW_H
        budget = float(RUNTIME.get("api_budget") or 0)
        if budget > 0 and month is not None:
            pct = min(100.0, month / budget * 100)
            astr("예산", F_BOLD).drawAtPoint_(NSMakePoint(gx0 + PILL_PAD + 2, ry - 2))
            sub = astr(f"{pct:.0f}% · 남음 ${max(0, budget - month):.0f} / ${budget:.0f}", F_SUB)
            ss = sub.size()
            sub.drawAtPoint_(NSMakePoint(gx0 + PILL_W - PILL_PAD - ss.width, ry))
            bx0 = gx0 + PILL_PAD + 2
            bw = PILL_W - PILL_PAD * 2 - 4
            C_TRACK.set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17, bw, 6), 3, 3).fill()
            hexcolor(bar_color(pct)).set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(bx0, ry + 17, max(8, bw * pct / 100), 6), 3, 3).fill()
        else:
            hint = astr("설정에서 월 예산($)을 넣으면 게이지가 생겨요", F_TINY)
            hint.drawAtPoint_(NSMakePoint(gx0 + PILL_PAD + 2, ry + 2))

    class PetView(NSView):
        def isFlipped(self):
            return True

        def acceptsFirstMouse_(self, event):
            return True

        def petOnRight(self):
            """펫이 화면 오른쪽 절반에 있으면 True → 필이 왼쪽으로 붙음."""
            w = self.window()
            scr = (w.screen() if w else None) or NSScreen.mainScreen()
            vf = scr.frame()
            wx = w.frame().origin.x if w else vf.origin.x
            return (wx + W / 2) >= (vf.origin.x + vf.size.width / 2)

        def petOnBottom(self):
            """펫이 화면 아래쪽 절반에 있으면 True → 필이 위로 붙음."""
            w = self.window()
            scr = (w.screen() if w else None) or NSScreen.mainScreen()
            vf = scr.frame()
            wy = w.frame().origin.y if w else vf.origin.y
            return (wy + H / 2) < (vf.origin.y + vf.size.height / 2)

        def pillTop(self):
            """필의 y (flipped 좌표). 펫이 아래쪽이면 필이 위."""
            return 4 if self.petOnBottom() else PH + GAP

        def pillLeft(self):
            """필의 x — 펫이 있는 쪽으로 정렬."""
            if self.petOnRight():
                return W - PILL_W - 4    # 펫 오른쪽 → 필도 오른쪽 정렬
            return 4                     # 펫 왼쪽 → 필도 왼쪽 정렬

        def petOrigin(self):
            py = PILL_H + GAP if self.petOnBottom() else 2
            # 버튼이 안쪽에 붙으므로 펫은 창 가장자리에 밀착
            if self.petOnRight():
                return (W - PW - 6, py)   # 펫 오른쪽 끝, 버튼은 왼쪽 안쪽
            return (6, py)                # 펫 왼쪽 끝, 버튼은 오른쪽 안쪽

        def btnOrigin(self):
            px, py = self.petOrigin()
            by = py + int(26 * g["scale"])
            if self.petOnRight():
                return (px - BTN_R * 2 - 2, by)      # 펫 오른쪽 → 버튼 왼쪽
            return (px + PW + 2, by)                 # 펫 왼쪽 → 버튼 오른쪽

        def drawRect_(self, rect):
            stats = state["stats"]
            mood = state["mood"]
            seq = frames.get(mood, frames["idle"])
            fr = 0 if state["resting"] else state["frame"] % len(seq)
            img = seq[fr]

            # ── 상태 필 (펫 위치 기준 상하 플립 + 좌우 정렬) ──
            if state["show_panel"]:
                gx0 = self.pillLeft()
                gy0 = self.pillTop()
                C_PILL.set()
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(gx0, gy0, PILL_W, PILL_H), PILL_R, PILL_R).fill()

                if RUNTIME["mode"] == "api":
                    draw_api_pill(gx0, gy0)
                elif state["oauth"]:
                    draw_exact_pill(gx0, gy0, state["oauth"])  # 정확 모드
                elif stats:
                    draw_sub_pill(gx0, gy0, stats)
                else:
                    m = astr("사용량 스캔 중...", F_SUB)
                    ms = m.size()
                    m.drawAtPoint_(NSMakePoint(gx0 + (PILL_W - ms.width) / 2,
                                               gy0 + (PILL_H - ms.height) / 2))

            # ── 펫 ──
            px, py = self.petOrigin()
            pet_rect = NSMakeRect(px, py, PW, PH)
            img.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(
                pet_rect, NSZeroRect,
                NSCompositingOperationSourceOver, 1.0, True, None)

            spk = spike_info(stats)
            if spk:
                pulse = 0.22 + 0.18 * (0.5 + 0.5 * math.sin(_time.time() * 5))
                hexcolor(spk[0], pulse).set()
                NSRectFillUsingOperation(pet_rect,
                                         NSCompositingOperationSourceAtop)

            # ── 접기 버튼 (마우스 오버 시에만 표시) ──
            if state["hover"]:
                bx, by = self.btnOrigin()
                C_PILL.set()
                NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(bx, by, BTN_R * 2, BTN_R * 2)).fill()
                C_BTNL.set()
                ring = NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(bx, by, BTN_R * 2, BTN_R * 2))
                ring.setLineWidth_(1)
                ring.stroke()
                # 꺾쇠: 필이 열리는/닫히는 방향을 가리키도록 직접 그림
                pill_below = not self.petOnBottom()   # 필이 펫 아래에 붙는 배치
                # 열려 있으면 '접는' 방향(필 반대쪽), 닫혀 있으면 '펼치는' 방향(필 쪽)
                point_down = (pill_below and not state["show_panel"]) or \
                             (not pill_below and state["show_panel"])
                cx, cy = bx + BTN_R, by + BTN_R
                wdt, hgt = 5.5, 3.0
                chev = NSBezierPath.bezierPath()
                chev.setLineWidth_(2.0)
                chev.setLineCapStyle_(1)   # round
                chev.setLineJoinStyle_(1)  # round
                if point_down:  # flipped 좌표: 아래 = y 증가
                    chev.moveToPoint_(NSMakePoint(cx - wdt, cy - hgt / 2))
                    chev.lineToPoint_(NSMakePoint(cx, cy + hgt))
                    chev.lineToPoint_(NSMakePoint(cx + wdt, cy - hgt / 2))
                else:
                    chev.moveToPoint_(NSMakePoint(cx - wdt, cy + hgt / 2))
                    chev.lineToPoint_(NSMakePoint(cx, cy - hgt))
                    chev.lineToPoint_(NSMakePoint(cx + wdt, cy + hgt / 2))
                C_SUB.set()
                chev.stroke()

        # ── 마우스 ──
        def mouseDown_(self, event):
            self._down = event.locationInWindow()
            state["dragging"] = True
            self._moved = False

        def mouseDragged_(self, event):
            loc = event.locationInWindow()
            dx = loc.x - self._down.x
            dy = loc.y - self._down.y
            if abs(dx) > 1 or abs(dy) > 1:
                self._moved = True
                if abs(dx) >= abs(dy):
                    set_override("running-right" if dx > 0 else "running-left",
                                 sticky_flag=True)
            w = self.window()
            o = w.frame().origin
            w.setFrameOrigin_(NSMakePoint(o.x + dx, o.y + dy))

        def mouseUp_(self, event):
            state["dragging"] = False
            clear_sticky()
            clamp_to_screen()   # 화면 밖으로 나갔으면 다시 안으로
            fo = self.window().frame().origin
            cfg["x"], cfg["y"] = fo.x, fo.y
            save_config(cfg)
            self.setNeedsDisplay_(True)  # 좌우 플립 반영
            if getattr(self, "_moved", False):
                return
            if event.clickCount() == 2:
                set_override("jumping")
                return
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            bx, by = self.btnOrigin()
            if (loc.x - bx - BTN_R) ** 2 + (loc.y - by - BTN_R) ** 2 <= (BTN_R + 6) ** 2:
                state["show_panel"] = not state["show_panel"]
                self.setNeedsDisplay_(True)

        def rightMouseDown_(self, event):
            menu = NSMenu.alloc().initWithTitle_("ClaudePet")
            for title, action in (("설정...", "openSettings:"),
                                  ("게이지 접기/펴기", "togglePanel:"),
                                  ("크기 원래대로", "resetScale:"),
                                  (None, None),
                                  ("Claude Pet 종료", "quitApp:")):
                if title is None:
                    menu.addItem_(NSMenuItem.separatorItem())
                    continue
                mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title, action, "")
                mi.setTarget_(handler)
                menu.addItem_(mi)
            NSMenu.popUpContextMenu_withEvent_forView_(menu, event, self)

        def scrollWheel_(self, event):
            set_scale(g["scale"] + event.scrollingDeltaY() * 0.004)

    # ── 화면 경계 클램프: 창이 모든 모니터 밖으로 나가 증발하는 것 방지 ──
    def clamp_to_screen():
        f = win.frame()
        cx = f.origin.x + f.size.width / 2
        cy = f.origin.y + f.size.height / 2
        best, best_d = None, None
        for scr in NSScreen.screens():
            vf = scr.visibleFrame()
            dx = max(vf.origin.x - cx, 0, cx - (vf.origin.x + vf.size.width))
            dy = max(vf.origin.y - cy, 0, cy - (vf.origin.y + vf.size.height))
            d = dx * dx + dy * dy
            if best_d is None or d < best_d:
                best, best_d = vf, d
        if best is None:
            return
        # 창 전체가 화면 안에 있도록 (필은 안쪽으로 플립되므로 이게 자연스러움)
        fw, fh = f.size.width, f.size.height
        nx = min(max(f.origin.x, best.origin.x),
                 best.origin.x + best.size.width - fw)
        ny = min(max(f.origin.y, best.origin.y),
                 best.origin.y + best.size.height - fh)
        if abs(nx - f.origin.x) > 0.5 or abs(ny - f.origin.y) > 0.5:
            win.setFrameOrigin_(NSMakePoint(nx, ny))

    # ── 크기 조절 ──
    def set_scale(value):
        nonlocal PW, PH, W, H
        new = max(0.3, min(2.0, value))
        if abs(new - g["scale"]) < 1e-4:
            return
        g["scale"] = new
        PW, PH, W, H = geom()
        f = win.frame()
        win.setFrame_display_(NSMakeRect(f.origin.x, f.origin.y, W, H), True)
        view.setFrame_(NSMakeRect(0, 0, W, H))
        view.setNeedsDisplay_(True)
        cfg["scale"] = round(g["scale"], 3)
        save_config(cfg)

    # ── 설정 창 ──
    def open_settings():
        if ui.get("panel"):
            ui["panel"].makeKeyAndOrderFront_(None)
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            return
        PWID, PHT = 420, 520
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PWID, PHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False)
        panel.setTitle_("Claude Pet 설정")
        panel.center()
        cv = panel.contentView()

        def label(text, x, y, w=150):
            l = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, 20))
            l.setStringValue_(text)
            l.setBezeled_(False)
            l.setDrawsBackground_(False)
            l.setEditable_(False)
            l.setSelectable_(False)
            cv.addSubview_(l)
            return l

        def field(x, y, w, value, secure=False):
            cls = NSSecureTextField if secure else NSTextField
            f = cls.alloc().initWithFrame_(NSMakeRect(x, y, w, 22))
            f.setStringValue_(str(value))
            cv.addSubview_(f)
            return f

        y = PHT - 40
        label("데이터 소스", 20, y)
        mode = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 220, 26), False)
        mode.addItemsWithTitles_(["구독 (Claude Code 로그)", "API (Admin API 비용)"])
        mode.selectItemAtIndex_(1 if RUNTIME["mode"] == "api" else 0)
        cv.addSubview_(mode)

        y -= 34
        label("모델 게이지 키워드", 20, y)
        f_kw = field(180, y - 2, 100, RUNTIME.get("model_keyword", "auto"))
        label("(auto=자동감지)", 288, y, 120)

        y -= 34
        label("주간 리셋", 20, y)
        wreset = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 130, 26), False)
        wreset.addItemsWithTitles_(["롤링 7일", "월요일", "화요일", "수요일",
                                    "목요일", "금요일", "토요일", "일요일"])
        wd = RUNTIME.get("weekly_reset_day")
        wreset.selectItemAtIndex_(0 if wd is None else int(wd) + 1)
        cv.addSubview_(wreset)
        f_wh = field(318, y - 2, 40, int(RUNTIME.get("weekly_reset_hour", 20)))
        label("시", 362, y, 30)

        # ── 보정: Claude 앱의 % 입력 → 한도 자동 역산 ──
        y -= 40
        label("🔧 보정: Claude 앱 설정 > 사용량의 %를 입력하면", 20, y, 380)
        y -= 20
        label("      한도를 자동으로 계산해요 (입력한 것만 반영)", 20, y, 380)
        y -= 28
        label("현재 세션 사용됨 (%)", 20, y)
        f_cs = field(180, y - 2, 60, "")
        y -= 30
        label("주간 모든 모델 (%)", 20, y)
        f_cw = field(180, y - 2, 60, "")
        y -= 30
        label("주간 모델별 (%)", 20, y)
        f_cm = field(180, y - 2, 60, "")

        y -= 40
        label("세션 한도 (백만 토큰)", 20, y)
        f_ses = field(180, y - 2, 90, round(RUNTIME["session_limit"] / 1e6, 2))
        y -= 30
        label("주간 한도 (백만 토큰)", 20, y)
        f_wk = field(180, y - 2, 90, round(RUNTIME["weekly_limit"] / 1e6, 2))
        y -= 30
        label("모델 한도 (백만 토큰)", 20, y)
        f_op = field(180, y - 2, 90, round(RUNTIME["opus_limit"] / 1e6, 2))

        y -= 36
        label("급증 알림 민감도", 20, y)
        sens = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 220, 26), False)
        sens.addItemsWithTitles_(["민감 (조금만 써도 경보)", "보통", "둔감 (많이 써야 경보)"])
        m = RUNTIME.get("spike_mult", 1.0)
        sens.selectItemAtIndex_(0 if m < 0.9 else (2 if m > 1.5 else 1))
        cv.addSubview_(sens)

        y -= 32
        greet = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 300, 22))
        greet.setButtonType_(3)  # 체크박스
        greet.setTitle_("마우스가 가까이 오면 인사하기")
        greet.setState_(1 if RUNTIME.get("greet") else 0)
        cv.addSubview_(greet)

        y -= 34
        label("Admin API 키", 20, y)
        f_key = field(180, y - 2, 220, RUNTIME.get("admin_key", ""), secure=True)
        y -= 30
        label("API 월 예산 ($)", 20, y)
        f_bud = field(180, y - 2, 90, RUNTIME.get("api_budget") or 0)

        save_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(PWID - 110, 12, 90, 30))
        save_btn.setTitle_("저장")
        save_btn.setBezelStyle_(1)
        save_btn.setTarget_(handler)
        save_btn.setAction_("saveSettings:")
        cv.addSubview_(save_btn)

        ui.update({"panel": panel, "mode": mode, "ses": f_ses, "wk": f_wk,
                   "op": f_op, "sens": sens, "greet": greet,
                   "key": f_key, "bud": f_bud, "kw": f_kw,
                   "wreset": wreset, "whour": f_wh,
                   "cs": f_cs, "cw": f_cw, "cm": f_cm})
        panel.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def save_settings():
        def num(fld, default):
            try:
                return float(str(fld.stringValue()).replace(",", "").replace("%", "").strip())
            except ValueError:
                return default
        cfg["mode"] = "api" if ui["mode"].indexOfSelectedItem() == 1 else "sub"
        cfg["model_keyword"] = (str(ui["kw"].stringValue()).strip().lower()
                                or "auto")
        widx = ui["wreset"].indexOfSelectedItem()
        cfg["weekly_reset_day"] = None if widx == 0 else widx - 1
        cfg["weekly_reset_hour"] = max(0, min(23, int(num(ui["whour"], 20))))
        cfg["session_limit"] = int(num(ui["ses"], 8) * 1e6)
        cfg["weekly_limit"] = int(num(ui["wk"], 60) * 1e6)
        cfg["opus_limit"] = int(num(ui["op"], 15) * 1e6)
        cfg["spike_mult"] = [0.5, 1.0, 2.0][ui["sens"].indexOfSelectedItem()]
        cfg["greet"] = bool(ui["greet"].state())
        cfg["admin_key"] = str(ui["key"].stringValue()).strip()
        cfg["api_budget"] = num(ui["bud"], 0)
        apply_config(cfg)   # 키워드/리셋 요일 먼저 적용 후 사용량 재계산
        # 보정: 앱에 표시된 %가 입력됐으면 한도 = 사용량 ÷ (% / 100)
        s = compute_usage()
        for fld, gkey, ckey in (("cs", "session", "session_limit"),
                                ("cw", "weekly", "weekly_limit"),
                                ("cm", "opus", "opus_limit")):
            pct = num(ui[fld], 0)
            used = s[gkey]["used"]
            if pct > 0 and used > 0:
                cfg[ckey] = max(int(used * 100 / pct), used)
        apply_config(cfg)
        save_config(cfg)
        ui["panel"].orderOut_(None)
        ticker.refresh_(None)
        view.setNeedsDisplay_(True)

    # ── 메뉴/설정 핸들러 ──
    class Handler(NSObject):
        def openSettings_(self, sender):
            open_settings()

        def togglePanel_(self, sender):
            state["show_panel"] = not state["show_panel"]
            view.setNeedsDisplay_(True)

        def resetScale_(self, sender):
            set_scale(0.5)

        def quitApp_(self, sender):
            NSApplication.sharedApplication().terminate_(None)

        def saveSettings_(self, sender):
            save_settings()

    # ── 타이머 ──
    class Ticker(NSObject):
        def tick_(self, timer):
            mood = current_mood()
            if mood != state["last_mood"]:
                state["last_mood"] = mood
                state["frame"] = 0
                state["elapsed"] = 0.0
                state["resting"] = False
            state["mood"] = mood
            dur, loop, rest = STATE_CFG.get(mood, DEFAULT_CFG)
            dirty = False

            if state["resting"]:
                state["rest_elapsed"] += TICK * 1000
                if state["rest_elapsed"] >= rest:
                    state["resting"] = False
                    state["rest_elapsed"] = 0.0
                    state["frame"] = 0
                    state["elapsed"] = 0.0
            else:
                state["elapsed"] += TICK * 1000
                if state["elapsed"] >= dur:
                    state["elapsed"] = 0.0
                    seq_len = len(frames.get(mood, frames["idle"]))
                    nxt = state["frame"] + 1
                    if nxt >= seq_len:
                        state["frame"] = 0
                        if not loop and not sticky["on"]:
                            state["override"] = None
                        elif rest > 0 and not sticky["on"]:
                            state["resting"] = True
                    else:
                        state["frame"] = nxt
                    dirty = True

            # 마우스 호버 감지 (접기 버튼 표시용)
            mpos_h = NSEvent.mouseLocation()
            fh_ = win.frame()
            hover = (fh_.origin.x <= mpos_h.x <= fh_.origin.x + fh_.size.width
                     and fh_.origin.y <= mpos_h.y <= fh_.origin.y + fh_.size.height)
            if hover != state["hover"]:
                state["hover"] = hover
                dirty = True

            # 마우스 근접 인사 (평소엔 가만히)
            if (RUNTIME.get("greet") and not state["dragging"]
                    and state["override"] is None
                    and not spike_info(state["stats"])):
                now = _time.time()
                if now >= state["greet_cool"]:
                    mpos = NSEvent.mouseLocation()
                    f = win.frame()
                    px, py = view.petOrigin()
                    cx = f.origin.x + px + PW / 2
                    cy = f.origin.y + (H - py - PH / 2)
                    if math.hypot(mpos.x - cx, mpos.y - cy) < NEAR_PX + PW / 2:
                        set_override("waving")
                        state["greet_cool"] = now + GREET_COOLDOWN
                        dirty = True

            if spike_info(state["stats"]):
                dirty = True
            if dirty:
                view.setNeedsDisplay_(True)

        def refresh_(self, timer):
            def work():
                s = compute_usage()
                prev = state["stats"]
                state["stats"] = s
                state["oauth"] = fetch_exact_usage()   # 정확 모드 (180s 캐시)
                state["cost"] = fetch_api_cost_today()
                if RUNTIME["mode"] == "api":
                    state["cost_month"] = fetch_api_cost_month()
                if prev and prev["session"]["pct"] > 5 and s["session"]["pct"] < 1:
                    set_override("jumping")
            threading.Thread(target=work, daemon=True).start()

    # ── 앱/윈도우 ──
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)

    vf = NSScreen.mainScreen().visibleFrame()
    x = cfg.get("x", vf.origin.x + vf.size.width - W - 36)
    y = cfg.get("y", vf.origin.y + 70)
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, W, H), NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setHasShadow_(False)
    win.setLevel_(25)
    # 모든 스페이스에 표시 + 전체화면 앱 위에도 보조로 표시
    win.setCollectionBehavior_(1 << 0 | 1 << 8)

    view = PetView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
    win.setContentView_(view)
    win.orderFrontRegardless()
    clamp_to_screen()   # 저장된 좌표가 화면 밖이면 안으로 복구

    handler = Handler.alloc().init()
    ticker = Ticker.alloc().init()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        TICK, ticker, "tick:", None, True)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        REFRESH_SEC, ticker, "refresh:", None, True)
    ticker.refresh_(None)
    set_override("waving")

    AppHelper.runEventLoop()




# ─────────────────────── CLI 리포트 ───────────────────────

def print_report():
    exact = fetch_exact_usage()
    if exact:
        print("─" * 60)
        print(" 정확 모드 (서버 계산 값)")
        for label, pct, rdt, rtxt in exact:
            reset = fmt_countdown(rdt, datetime.now(timezone.utc)) if rdt else (rtxt or "-")
            print(f" {label:<6} {pct:5.1f}%  · 리셋 {reset}")
    s = compute_usage()
    def line(name, g):
        print(f" {name:<6} {g['pct']:5.1f}%  사용 {fmt_tokens(g['used'])} / {fmt_tokens(g['limit'])}"
              f"  · 남음 {fmt_tokens(g['left'])}  · 리셋 {fmt_countdown(g['reset'], s['now'])}")
    print("─" * 60)
    print(" Claude Pet 사용량 리포트")
    print("─" * 60)
    line("세션", s["session"])
    line("주간", s["weekly"])
    line("Opus", s["opus"])
    if s["last_activity"]:
        print(f" 마지막 활동: {s['last_activity'].astimezone():%Y-%m-%d %H:%M}")
    cost = fetch_api_cost_today()
    if cost is not None:
        print(f" 오늘 API 비용: ${cost:.2f}")
    print("─" * 60)


if __name__ == "__main__":
    apply_config(load_config())
    if "--report" in sys.argv:
        print_report()
    else:
        run_gui()
