#!/usr/bin/env python3
"""ClaudePet for Windows — 2단계 (PySide6).

macOS 판 `claude_pet.py` 를 **그대로 import** 해 서버 사용량 조회(Claude·Codex)·로그 급증 감지와 학습 한도·설정 파일·다국어·필 형상 상수·
자율 이동 상태기계(Roamer/RoamDisplay)·요약 필 내용·crop 기하(roam_frame)를 재사용하고, 이 파일은
Windows 에서 필요한 것만 구현한다:

  · 창: 프레임 없음 · 투명 배경 · 항상 위 · 작업표시줄 버튼 없음(Tool) · 트레이 아이콘
  · 그리기: 스프라이트(내장 PNG 폴더 또는 pet.json + spritesheet.webp) · 한 줄 요약 필(유일한 필, macOS 판과 같은 run/색) · 접기 버튼
  · 마우스: 드래그(놓으면 x/y 저장 — macOS 와 같은 정책) · 더블클릭(점프 + 즉시 새로고침) · 호버 인사 · 우클릭 메뉴
  · 자율 이동 어댑터: QScreen → RoamScreen(id/frame/bounds), 창 중심 ↔ 실제 창(crop), 점프 효과(창 불투명도),
    시스템 애니메이션 설정(= macOS 의 동작 줄이기), '화면 돌아다니기' 메뉴 토글

좌표: Qt 는 y 가 아래로 커진다. Roamer 는 축 방향을 가정하지 않으므로 전역 좌표를 그대로 넘기고,
RoamScreen.frame/bounds 도 같은 축으로 만든다. roam_frame 이 주는 crop/sprite/button/pill 은 창 내부 좌표라
(macOS 의 flipped 뷰와 같은 y-down) 그대로 쓰고, 실제 창 원점만 여기서 y-down 으로 계산한다.

UI 는 macOS 판과 100% 같아야 한다(사용자 요구 2026-09-12): 필·행·막대·상태줄·버튼·요약 필·설정 창·우클릭 메뉴는
macOS 판의 같은 상수·같은 문자열·같은 좌표로 그린다. 폰트만 플랫폼 제약(SF Mono 는 Windows 에 없다) — MONO_FAMILIES 참조.
업데이트·제거(Track C/D, 2026-09-13): 판단은 windows/win_update.py(순수, macOS 에서 시험), 실행은 이 파일.
  · 확인: 매시간(시작 때는 하지 않고 cp.UPDATE_CHECK_SEC 뒤부터 — macOS 판과 같은 의미) + 우클릭 '업데이트 확인…'. 자산 표는
    machine × 설치 종류(inno/portable)로 windows/ 안에 있고, 버전 비교는 cp._ver_tuple 이다. 일시적 실패(네트워크, JSON 아님)만
    다음 새로고침(30초)에 다시 묻고, 그 밖의 결과(최신·새 버전·이 기기용 자산 없음 같은 거절)는 한 시간을 기다린다
    (win_update.stamps_cooldown) — 예전에는 모든 거절이 30초마다 api.github.com 을 불렀다.
  · inno(설치 파일로 깐 경우): setup.exe 를 %LOCALAPPDATA%\\me.yeongyu.claudepet 에 받아 크기·sha256 을 릴리즈 JSON 과 대조한 뒤
    /SILENT … /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /RELAUNCH=1 로 돌린다. 앱은 스스로 끝내지 않는다 — 설치 파일의 Restart
    Manager 가 닫고(RegisterApplicationRestart 로 등록돼 있어) 다시 띄우며, [Run] 의 /RELAUNCH 항목이 이중 보험, 단일 인스턴스
    뮤텍스가 둘 중 하나만 남긴다.
  · portable(zip 을 풀어 쓰는 경우): zip 을 받아 검증 → cp._zip_members_are_safe → 옆 폴더에 풀어 레이아웃·버전 마커 확인 →
    PowerShell 교체 스크립트(pid 종료 대기 → 설치 폴더를 .claudepet-old-v<버전> 으로 → 새 폴더를 제자리로 → 실행 → 살아 있는지
    확인, 실패하면 되돌리고 옛 exe 실행)를 띄우고 앱을 끝낸다. 이름 바꾸기는 모두 Rename-Item 이다(대상이 있으면 실패 — Move-Item 은
    있는 폴더 *안으로* 옮겨 ClaudePet\\ClaudePet 을 만든다). .claudepet-old-v<버전> 이 이미 있으면 내려받기 전에 거절한다
    (old-dir-exists — win_update.swap_refusal). 지난 거래가 남긴 옆 폴더는 다음 시작에서 지운다.
  · 잠금: portable 은 공유 모드 없는 잠금 핸들을 헬퍼에 물려주어 헬퍼가 끝날 때까지 산다. inno 설치 파일은 핸들을 물려받지 않고
    앱 쪽 핸들도 띄운 직후 닫히므로, 설치 파일이 도는 동안 두 번째 업데이트와 완전 삭제를 막는 것은 state["installing"] 표시다
    (win_update.uninstall_refusal); 설치 파일이 앱을 닫지 않고 끝나면 _reap_installer 가 표시를 지운다.
  · 완전 삭제: macOS 판 UNINSTALL_PATHS 의 사용자 파일 + 캐시 폴더 + HKCU Run 값(우리 exe 일 때만) 을 지우고, 두 종류 다
    "펫이 끝난 뒤" 에 도는 헬퍼에 맡긴다 — inno 는 pid 를 기다렸다가 unins000.exe /SILENT 를 부르는 PowerShell 헬퍼,
    portable 은 종료 뒤 폴더를 지우는 헬퍼. 펫이 살아 있는 채로 제거 프로그램을 띄우면 ARP 항목과 Run 값만 지워지고
    앱 트리는 "사용 중" 으로 남는다(실기 2026-09-14). %USERPROFILE%\\.claude_pet(펫)은 남긴다.
  · 모든 단계는 %LOCALAPPDATA%\\me.yeongyu.claudepet\\update.log 에 개수·상태만 남긴다(경로 없음 — CLAUDE.md § Privacy).
로그인 시 자동 실행(Track B-W, 2026-09-13): 우클릭 체크 항목 — macOS 판과 같은 자리(화면 돌아다니기 다음)·같은 TR 키. 판단은
  windows/win_autostart.py(순수, macOS 에서 시험): 설치 파일의 startup 옵션이 쓰는 HKCU Run 값 `ClaudePet` = "<exe>" 그대로 읽고 쓰며,
  시작 앱 UI 의 사용 안 함(Explorer StartupApproved — 설정 › 앱 › 시작 앱과 작업 관리자 › 시작 앱이 같은 키에 쓴다)도 본다.
  설정 키는 없다 — 메뉴를 열 때마다 OS 에서 다시 읽는다(CLAUDE.md § "Start at sign-in" 과 같은 계약).
  소스 실행(pythonw)은 항목이 '(여기서는 사용 불가)' 로 비활성이다.
`claude_pet.py` 와 macOS 빌드·릴리즈 스크립트는 이 파일로 바뀌지 않는다.

실행: `pythonw windows\\claude_pet_win.py` (저장소 루트에서, Python 3.13 + PySide6 + Pillow)
"""
import math
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)             # win_update.py 는 이 파일 옆 (소스 실행·PyInstaller 번들 모두)


import win_core  # noqa: E402  — 코어 import 의 유일한 주인 (windows/win_core.py)

# 두 가지 Windows 우회(compat/fcntl, CDLL(None))는 이제 win_core 한 곳에만 있다. 예전에는 이 파일 안에만 있어서
# win_update.py·build_win.py·verify_win_artifact.py 는 그냥 `import claude_pet` 을 했고, 실기에서 첫 줄에 죽었다.
cp = win_core.import_core()  # AppKit 은 run_gui 안에서만 import 되므로 GUI 없이 코어를 쓸 수 있다 (설계 문서 §0)
import win_update as wu  # noqa: E402  — cp 를 먼저 import 한 뒤 (같은 sys.modules 항목을 본다)
import win_autostart as wa  # noqa: E402  — 로그인 시 자동 실행의 순수 부분 (HKCU Run 값 + StartupApproved 판단)

from PIL import Image  # noqa: E402
from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import (QAction, QColor, QCursor, QFont, QFontDatabase, QFontMetrics,  # noqa: E402
                           QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QLabel, QLineEdit,  # noqa: E402
                               QMenu, QMessageBox, QPushButton, QSystemTrayIcon, QWidget)
# 제공자 마크(SVG)를 **명시적으로** 렌더한다. QPixmap(path) 로 qsvg 이미지 플러그인에 맡기지
# 않는 이유는 둘이다: PyInstaller 의 import 분석은 명시적 import 는 보지만 플러그인 경유는
# 못 보고, openai.svg 는 fill="currentColor" 라 우리가 색을 정해 주지 않으면 검정으로
# 래스터화되어 어두운 필에서 그대로 사라진다(틴트는 summary_logo_image 참조).
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

TICK_MS = 50                 # macOS 판 TICK = 0.05 와 같은 20 Hz
NEAR_PX = 100                # 인사 판정 거리 — macOS 판과 동일
GREET_COOLDOWN = float(getattr(cp, "GREET_COOLDOWN", 20.0))
BTN_LINE = "#2E2E33"
# macOS 판은 NSFont.monospacedSystemFontOfSize_weight_ (= SF Mono, bold 는 weight 0.4 ≈ semibold).
# SF Mono 는 Windows 에 배포할 수 없으므로 있으면 쓰고, 없으면 자간이 가장 비슷한 순서로 고른다.
# 두 플랫폼에 같은 글꼴을 번들하면 여기 한 줄만 바꾼다 (QFontDatabase.addApplicationFont 뒤 그 이름을 앞에).
MONO_FAMILIES = ("SF Mono", "Cascadia Mono", "Consolas")
CLAUDE_INSTALL_URL_WIN = "https://claude.ai/install.ps1"   # macOS 판 install.sh 의 Windows 판
UNINSTALL_PATHS_WIN = (cp.CONFIG_PATH, cp.CONFIG_PATH + ".lock", os.path.expanduser("~/claudepet_debug.log"))
SPI_GETCLIENTAREAANIMATION = 0x1042


# ─────────────────────────── 스프라이트 로드 (Pillow → QPixmap) ───────────────────────────
def _pil_to_pixmap(im):
    im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    qimg = QImage(data, im.width, im.height, im.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


def _load_sheet_pet(pet_dir, meta):
    """pet.json + spritesheet.webp (고정 v2 격자 규약) → 상태별 프레임. macOS 판 _load_sheet_pet 과 같은 규칙."""
    sp = os.path.join(pet_dir, meta.get("spritesheetPath") or cp.BUNDLED_PET_SHEET)
    try:
        sheet = Image.open(sp)
        sheet.load()
    except Exception:
        return None
    cols, rows = cp.PET_SHEET_COLS, cp.PET_SHEET_ROWS
    fw, fh = sheet.width // cols, sheet.height // rows
    if fw <= 0 or fh <= 0:
        return None
    out = {}
    for st, (row, count) in cp._pet_layout(meta).items():
        imgs = []
        for c in range(count):
            box = (c * fw, row * fh, (c + 1) * fw, (row + 1) * fh)
            imgs.append(_pil_to_pixmap(sheet.crop(box)))
        if imgs:
            out[st] = imgs
    return out or None


def _load_folder_pet(pet_dir):
    """(구형) 상태별 하위 폴더의 PNG — 내장 고양이."""
    import glob
    out = {}
    for st in sorted(os.listdir(pet_dir)):
        sd = os.path.join(pet_dir, st)
        if not os.path.isdir(sd):
            continue
        imgs = []
        for p in sorted(glob.glob(os.path.join(sd, "*.png"))):
            try:
                imgs.append(_pil_to_pixmap(Image.open(p)))
            except Exception:
                continue
        if imgs:
            out[st] = imgs
    return out or None


def load_pet_frames(pet_dir):
    """펫 폴더 → 상태별 프레임 dict. idle 없으면 None. (macOS 판과 같은 폴백 규칙)"""
    meta = cp._read_pet_json(pet_dir)
    frames = _load_sheet_pet(pet_dir, meta) if meta is not None else _load_folder_pet(pet_dir)
    if not frames or not frames.get("idle"):
        return None
    for need in cp._PET_FALLBACK_STATES:
        frames.setdefault(need, frames["idle"])
    return frames


# ─────────────────────────── 스파이크 / 시스템 설정 ───────────────────────────
def spike_info(stats):
    """macOS 판 run_gui.spike_info 와 같은 규칙 — 지금 보이는 제공자 중 하나라도 로그 급증이면 (색, 이름).

    API 모드는 제공자별이다(cp.provider_spiking). 필에 안 보이는 제공자의 급증은 펫을 흔들지 않는다 —
    ▲ 가 붙을 줄이 화면에 없으니 이유를 알 수 없는 경보가 된다.
    """
    if not stats:
        return None
    sp = stats.get("spikes") or {}
    if cp.provider_shown(cp.RUNTIME, "claude") and cp.provider_spiking(stats, "claude"):
        if sp.get("session"):
            return ("#FF453A", cp.t("session"))
        if sp.get("opus"):
            return ("#BF5AF2", str(stats.get("model_kw") or "opus").capitalize())
        return ("#FF9F0A", cp.t("weekly"))
    if cp.provider_shown(cp.RUNTIME, "codex") and cp.provider_spiking(stats, "codex"):
        return ("#FF453A", "Codex")
    return None


def reduce_motion():
    """Windows 의 '창 애니메이션' 설정이 꺼져 있으면 True — macOS 의 동작 줄이기에 대응. 다른 OS 에선 False."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        flag = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(flag), 0)
        return bool(ok) and flag.value == 0
    except Exception:
        return False


def windows_ui_lang():
    """Windows 의 사용자 UI 언어 → 앱 언어 코드. macOS 판 _system_lang() 은 Foundation 에만 기대므로 Windows 에선 항상 'en'
    이 된다. 설정 파일에 lang 이 저장돼 있으면(set_lang) 그 값이 우선이고, 없을 때만 여기 값을 쓴다."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF   # primary language id
    except Exception:
        return None
    code = {0x12: "ko", 0x11: "ja", 0x0A: "es", 0x09: "en"}.get(langid)
    return code if code in cp.SUPPORTED_LANGS else None


# ─────────────────────────── Windows 전용 문자열 (코어 TR 에 없는 것만; 있는 키는 cp.t 로) ───────────────────────────
TR_WIN = {
    "en": {
        "upd_no_asset": "No Windows build is published for this machine ({m}) yet.",
        "upd_source": "Running from source — update with git pull instead.",
        "upd_installing": "Installing v{v} — Claude Pet will close and reopen by itself.",
        "unin_busy": "An update is in progress. Try again in a minute.",
    },
    "ko": {
        "upd_no_asset": "이 기기({m})용 Windows 빌드가 아직 없습니다.",
        "upd_source": "소스에서 실행 중입니다 — git pull 로 갱신하세요.",
        "upd_installing": "v{v} 를 설치합니다 — Claude Pet 이 스스로 닫혔다가 다시 뜹니다.",
        "unin_busy": "업데이트가 진행 중입니다. 잠시 후 다시 시도하세요.",
    },
    "ja": {
        "upd_no_asset": "このPC（{m}）向けの Windows ビルドはまだ公開されていません。",
        "upd_source": "ソースから実行中です — git pull で更新してください。",
        "upd_installing": "v{v} をインストールします — Claude Pet は自動的に閉じて再び開きます。",
        "unin_busy": "アップデートの実行中です。しばらくしてからもう一度お試しください。",
    },
    "es": {
        "upd_no_asset": "Aún no hay una versión de Windows publicada para este equipo ({m}).",
        "upd_source": "Se está ejecutando desde el código fuente: actualiza con git pull.",
        "upd_installing": "Instalando v{v}: Claude Pet se cerrará y volverá a abrirse solo.",
        "unin_busy": "Hay una actualización en curso. Inténtalo en un minuto.",
    },
}


def tw(key, **kw):
    """Windows 전용 키 → 현재 언어 문자열(없으면 en, 그래도 없으면 cp.t)."""
    d = TR_WIN.get(cp.L["lang"]) or TR_WIN["en"]
    s = d.get(key) or TR_WIN["en"].get(key)
    if s is None:
        return cp.t(key, **kw)
    return s.format(**kw) if kw else s


# ─────────────────────────── Windows API 배선 (win32 에서만; 판단은 win_update 에) ───────────────────────────
_WIN32 = sys.platform == "win32"
_KEEP_HANDLES = []            # 프로세스가 사는 동안 들고 있을 핸들(단일 인스턴스 뮤텍스) — GC 로 닫히지 않게
RESTART_NO_CRASH, RESTART_NO_HANG, RESTART_NO_REBOOT = 1, 2, 8
ERROR_ALREADY_EXISTS = 183
ERROR_SHARING_VIOLATION = 32
GENERIC_READ, GENERIC_WRITE = 0x80000000, 0x40000000
OPEN_ALWAYS = 4
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_DELETE_ON_CLOSE = 0x04000000
INVALID_HANDLE_VALUE = -1


def is_frozen():
    """PyInstaller 번들(ClaudePet.exe)로 도는가. 아니면 소스 실행 — 업데이트/폴더 삭제 대상이 없다."""
    return bool(getattr(sys, "frozen", False)) and _WIN32


def app_exe_path():
    return os.path.abspath(sys.executable) if is_frozen() else None


def _inno_registry_reader(value_name):
    """HKCU\\…\\Uninstall\\{me.yeongyu.claudepet}}_is1 의 값(닫는 중괄호 둘 — installer.iss 의 AppId 에서 Inno 가 앞의 `{{` 만 푼다).

    키가 없으면 winreg 가 OSError 를 낸다 — install_kind 는 그것을 portable 로 읽는다."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, wu.INNO_UNINSTALL_SUBKEY) as k:
        value, _type = winreg.QueryValueEx(k, value_name)
        return value


def install_kind_now():
    """'inno' | 'portable' | 'source'."""
    exe = app_exe_path()
    if not exe:
        return "source"
    return wu.install_kind(exe, _inno_registry_reader)


def delete_run_value_if_ours(exe):
    """HKCU Run 의 ClaudePet 값이 이 exe 를 가리킬 때만 지운다 → 지웠으면 True."""
    if not _WIN32 or not exe:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, wu.RUN_SUBKEY, 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
            try:
                value, _type = winreg.QueryValueEx(k, wu.RUN_VALUE_NAME)
            except OSError:
                return False
            if not wu.run_value_is_ours(value, exe):
                return False
            winreg.DeleteValue(k, wu.RUN_VALUE_NAME)
            return True
    except OSError:
        return False


def acquire_single_instance_mutex():
    """Local\\me.yeongyu.claudepet 뮤텍스 → True 면 이 프로세스가 유일하다. 이미 있으면 False(다른 인스턴스가 떠 있다).
    다른 OS 에서는 항상 True."""
    if not _WIN32:
        return True
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)     # get_last_error 는 use_last_error 로 연 DLL 에서만 믿을 수 있다
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        h = k32.CreateMutexW(None, False, wu.MUTEX_NAME)
        err = ctypes.get_last_error()
        if not h:
            return True                        # 못 만들면 막지 않는다 — 두 개 뜨는 것보다 안 뜨는 것이 더 나쁘다
        if err == ERROR_ALREADY_EXISTS:
            k32.CloseHandle(h)
            return False
        _KEEP_HANDLES.append(h)
        return True
    except Exception:
        return True


RESTART_CMDLINE = "--restart"      # 재시작 때 붙는 인수. 앱은 인수를 읽지 않는다 — NULL/빈 문자열은 '등록 해제' 라 비워 둘 수 없다


def register_application_restart():
    """Restart Manager 에 '나를 다시 띄워 달라'고 등록한다 — 설치 파일(/CLOSEAPPLICATIONS /RESTARTAPPLICATIONS, RestartApplications=yes)
    이 이 앱을 닫고 설치를 마친 뒤 다시 띄우는 근거. 첫 인수는 실행 파일 이름을 뺀 명령줄이고, NULL 이나 빈 문자열은 등록을
    '지우는' 뜻이라 반드시 무언가를 준다(RESTART_CMDLINE). 충돌·멈춤·재부팅 뒤 자동 재시작은 끈다(RESTART_NO_*): 그건 Restart
    Manager 가 아니라 WER 의 일이고 원하지 않는다."""
    if not _WIN32:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.RegisterApplicationRestart.restype = ctypes.c_long
        k32.RegisterApplicationRestart.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
        rc = k32.RegisterApplicationRestart(RESTART_CMDLINE, RESTART_NO_CRASH | RESTART_NO_HANG | RESTART_NO_REBOOT)
        return rc == 0
    except Exception:
        return False


def open_update_lock(path):
    """업데이트 거래 잠금: 공유 모드 0(share-none) 으로 연 파일 핸들 → 핸들, 다른 프로세스가 들고 있으면 None.

    macOS 판 _acquire_update_lock 의 flock 에 해당한다. Windows 의 바이트 범위 잠금은 프로세스가 끝나면 풀리므로 헬퍼에 물려줄 수
    없고, share-none 핸들은 상속한 자식이 닫을 때까지 살아 있어 그 자리를 대신한다(조사 § Locks). 상속 가능하게 만들고
    DELETE_ON_CLOSE 를 주어 마지막 핸들이 닫히면 파일이 사라진다 — 잔여 잠금 파일이 남지 않는다."""
    if not _WIN32:
        return None
    import ctypes
    from ctypes import wintypes

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError as e:                        # 잠금 자리를 만들 수 없다 — 믿을 수 없는 자리에서는 진행하지 않는다
        wu.log_update("lock", status="failed", error=type(e).__name__)
        return None
    sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p)
    h = k32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, ctypes.byref(sa), OPEN_ALWAYS,
                        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_DELETE_ON_CLOSE, None)
    invalid = ctypes.c_void_p(INVALID_HANDLE_VALUE).value       # HANDLE 로 돌아온 INVALID_HANDLE_VALUE 의 정수 표현
    if h is None or h == invalid:
        return None                             # ERROR_SHARING_VIOLATION(다른 업데이터) 또는 열 수 없는 자리 — 둘 다 진행하지 않는다
    return h


def close_handle(h):
    if not _WIN32 or h is None:
        return
    try:
        import ctypes
        ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        pass


def powershell_exe():
    """System32 의 Windows PowerShell — PATH 를 믿지 않는다."""
    root = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def find_codex_cli():
    """Codex CLI 경로 또는 None — macOS 판 cp._find_codex_cli 의 Windows 판.

    npm 전역 설치는 %APPDATA%\\npm 에 codex.cmd(와 codex.ps1, 확장자 없는 sh 스크립트)를 만든다.
    확장자 없는 파일은 Windows 에서 실행할 수 없으므로 .cmd/.exe 를 먼저 찾고, 앱이 그 폴더가
    PATH 에 들어가기 전에 시작됐을 수 있어 그 폴더를 직접도 본다. 그 밖은 코어의 탐색에 맡긴다.
    """
    cands = [shutil.which("codex.cmd"), shutil.which("codex.exe")]
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(os.path.join(appdata, "npm", "codex.cmd"))
    for p in cands:
        if p and os.path.isfile(p):
            return p
    return cp._find_codex_cli()


def popen_detached(argv, inherit=None, cwd=None):
    """부모와 분리해 띄운다(새 프로세스 그룹, 창 없음). inherit 에 핸들을 주면 그 핸들만 자식에 물려준다 (macOS 판 pass_fds)."""
    kw = {}
    if _WIN32:
        kw["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                               | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if inherit:
            si = subprocess.STARTUPINFO()
            si.lpAttributeList = {"handle_list": list(inherit)}
            kw["startupinfo"] = si
            kw["close_fds"] = True
    return subprocess.Popen(argv, cwd=cwd, **kw)


# ─────────────────────────── 펫 창 ───────────────────────────
class PetWindow(QWidget):
    update_msg = Signal(str)     # 업데이트 확인 결과 — 워커 스레드에서 emit, GUI 스레드에서 알림 창(모달)
    notify = Signal(str)         # 비모달 알림(트레이 풍선) — 설치 파일이 이 앱을 닫는 동안 모달 창이 종료를 막지 않게
    quit_app = Signal()          # 워커 스레드에서 종료 요청 → GUI 스레드에서 QApplication.quit

    def __init__(self, frames, cfg, pets):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.frames = frames
        self.cfg = cfg
        self.pets = pets
        self.scale = max(0.3, min(2.0, float(cfg.get("scale", 0.5))))
        first = frames["idle"][0]
        self.PW0 = max(1, int(first.width() // cp.PET_SCALE_DOWN))
        self.PH0 = max(1, int(first.height() // cp.PET_SCALE_DOWN))
        # macOS 판 state 와 같은 키만 쓴다
        self.state = {"stats": None, "oauth": None, "onboard": None, "cost": None, "cost_month": None,
                      "frame": 0, "mood": "idle", "override": None, "show_panel": bool(cfg.get("show_panel", True)),
                      "elapsed": 0.0, "resting": False, "rest_elapsed": 0.0, "last_mood": "idle",
                      "dragging": False, "greet_cool": 0.0, "hover": False, "repaint": False,
                      # 자율 이동 어댑터 (macOS 판 roam_tick 과 같은 키)
                      "roam_layout": None, "roam_anim": None, "roam_hold": False, "menu_open": False,
                      "reduce_motion": False,
                      "roam_env": None, "roam_crop": None, "roam_rects": None, "roam_mode": None,
                      # codex: Codex(OpenAI) 사용량 행 또는 None. None 이면 구간 자체를 안 붙인다 —
                      # Codex 를 안 쓰는 사용자에게 0% 행을 보여 주지 않기 위해서다.
                      "codex": None,
                      # Codex 를 필에 보이는데 토큰이 없을 때: None|'install'|'login'
                      # (cp.compute_codex_onboard_state). 우클릭 메뉴가 읽는다.
                      "codex_onboard": None,
                      # Codex API 모드의 오늘·이달 비용과 마지막 조회 실패 종류(키 거부/일시 실패).
                      "codex_cost": None, "codex_cost_month": None,
                      "codex_api_error": False, "codex_api_stale": False,
                      # 요약 필 레이아웃. summary_lines_n 은 어댑터가 남기고 pill_band() 가 읽는다
                      # (높이가 줄 수를 따라가게 하는 유일한 경로). pill_w 는 _apply_pill_width 가
                      # 기록하고 geom() 이 읽는다 — 폭이 내용을 따라가게 하는 유일한 경로.
                      "summary_lines_n": 2, "pill_w": None, "pill_w_dirty": False,
                      # 토큰 자동 복구 상태 — 판단은 cp.recovery_tick 이 하고 여기서는 들고만 있는다.
                      "recovery": cp.new_recovery_state()}
        # Codex 구간은 훅으로 받는다(macOS 판 state["codex_summary"] 와 같은 모양) — 어댑터가
        # 모듈 함수를 이름으로 부르지 않게 해서, 창 없는 시험이 손으로 만든 state 로 어댑터를
        # 돌릴 때 훅이 없으면 그 시험의 범위가 그대로 유지되게 한다. 표시 설정·게이지 선택·
        # API 모드·Codex 자신의 급증은 코어(cp.codex_summary_segment)가 반영한다. 보일 게 없으면
        # None 이고, 그러면 구간이 붙지 않는다.
        self.state["codex_summary"] = lambda: cp.codex_summary_segment(
            cp.RUNTIME, self.state.get("codex"),
            cp.provider_spiking(self.state.get("stats"), "codex"),
            self.state.get("codex_cost"), self.state.get("codex_cost_month"),
            bool(self.state.get("codex_api_error")), bool(self.state.get("codex_api_stale")),
            auth_error=bool(cp.CODEX_STATUS.get("auth_error")))
        self.sticky = {"on": False}
        self._down = None
        self._moved = False
        self._refresh_gen = 0
        self._refresh_lock = threading.Lock()
        self._pending = None
        self._installer = None       # inno: 띄운 setup.exe 의 Popen — 앱을 닫지 않고 끝나면 _reap_installer 가 installing 을 지운다
        self.ui = {}                 # 설정 창 위젯 — macOS 판 ui 딕셔너리와 같은 키
        self._logo_cache = {}        # 제공자 → 틴트까지 끝낸 QImage(또는 None). 필은 20 Hz 로 다시 그려진다
        self.tray = None             # make_tray 가 채운다 — 비모달 알림(notify) 의 출구
        self._closing = False        # closeEvent 재진입 방지 (Restart Manager 의 WM_CLOSE → 종료)
        self.update_msg.connect(self._show_update_message)
        self.notify.connect(self._show_notify)
        self.quit_app.connect(lambda: QApplication.instance().quit())
        self._fonts()
        self.PW, self.PH, self.W, self.H = self.geom()
        self.resize(self.W, self.H)
        self._place_initial()
        # 자율 이동: 집 = 지금(클램프된) 논리 창 중심. 자동 이동은 x/y 를 저장하지 않는다.
        self.state["roam_env"] = (float(self.W), float(self.H))
        self.roamer = cp.Roamer(self.window_center(), time.monotonic(), radius=math.hypot(self.W / 2, self.H / 2))
        self.roam_display = cp.RoamDisplay()
        self.roam_clock = {"rm_at": 0.0, "last": time.monotonic()}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(int(cp.REFRESH_SEC * 1000))
        self.refresh()
        self.set_override("waving")

    # ── 형상 (macOS 판 geom 과 동일) ──
    def pill_band(self):
        """논리 창이 요약 필에 내어 주는 띠 높이 — **지금 그려질 줄 수** 기준.

        예전에는 geom()·pill_rect()·pet_origin()·roam_apply_display() 가 전부 인자 없는
        cp.pill_h() 를 불렀고, 그건 언제나 두 줄 높이였다. 제공자가 둘이 되고 접힘이
        생기면서 3줄 이상이 일상이 됐고, 그 상태로는 세 줄이 두 줄 높이 안에 그려져
        **폭을 고쳐 놓고 높이로 똑같이 잘려 보이는** 상태가 된다. 줄 수는 어댑터가
        state["summary_lines_n"] 에 남긴다. (macOS 판 pill_band 와 같은 규칙)
        """
        return cp.pill_h(self.state.get("summary_lines_n") or 2)

    def geom(self):
        """(펫 폭, 펫 높이, 논리 창 W, 논리 창 H).

        **W 는 필이 지금 필요로 하는 폭을 따라간다.** 예전에는 `cp.PILL_W + 8` 로 고정이었고,
        그래서 코어에서 상한을 "화면"으로 바꿔도 Qt 는 아무것도 안 넓어진다 —
        cp.roam_pill_rect 가 받는 W 가 언제나 308 이기 때문이다. 상한이 사라진 게 아니라
        한 층 위로 올라가 있었다(macOS 판 geom 의 같은 주석).

        state["pill_w"] 는 어댑터가 재서 넣는다(roam_summary_text). 아직 아무 글자도 안 잰
        첫 프레임에는 없으므로 cp.PILL_W 가 그 자리를 메운다 — 이 상수가 남아 있는 유일한
        이유다. '최대 너비'가 아니라 '측정 전 출발점'이다.
        """
        pw = int(self.PW0 * self.scale)
        ph = int(self.PH0 * self.scale)
        want = int(self.state.get("pill_w") or cp.PILL_W)
        w = max(pw + cp.BTN_R * 2 + 16, want + 2 * cp.SUMMARY_EDGE)
        h = ph + cp.GAP + self.pill_band() + 4
        return pw, ph, w, h

    def _fonts(self):
        """요약 필 글꼴 — 내장 Pretendard SemiBold(macOS 판과 같은 파일). 못 찾으면 MONO_FAMILIES 순서로 내려간다."""
        fam = None
        path = cp.bundled_font_path()
        if path:
            fid = QFontDatabase.addApplicationFont(path)
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            fam = fams[0] if fams else None
        if not fam:
            have = set(QFontDatabase.families())
            fam = next((c for c in MONO_FAMILIES if c in have),
                       QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
        self.font_family = fam
        cp._dbg("win font family", fam)                 # CLAUDE_PET_DEBUG=1 → ~/claudepet_debug.log
        def summary_font(size):
            f = QFont(fam, 1)
            f.setPointSizeF(size)
            f.setWeight(QFont.DemiBold)                 # Pretendard SemiBold = 600 (macOS weight 0.4 와 같은 급)
            # macOS(CoreText)처럼: 힌팅 없음 + 회색조 안티앨리어싱. 실기기 1:1 비교(2026-09-12, 2560×1440 100%,
            # ClearType 켜짐)에서 "글자가 깨져 보인다" 의 실체는 CFF(OTF)+힌팅 조합의 들쭉날쭉한 한글 획 굵기였고,
            # TTF + PreferNoHinting 으로 획이 고르게 펴졌다. 서브픽셀 색테는 세 판 모두 0건이라 NoSubpixelAntialias 는
            # 효과가 측정되지 않았지만, 반투명 창에서 회색조 AA 를 명시해 두는 것이 CoreText 와 같은 모델이라 유지한다.
            f.setHintingPreference(QFont.PreferNoHinting)
            f.setStyleStrategy(QFont.StyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias))
            return f
        self.F_SUMMARY = summary_font(11)               # 첫 줄
        self.F_SUMMARY_SUB = summary_font(9.5)          # 둘째 줄(리셋 시각)

    def _screen(self):
        return self.screen() or QApplication.primaryScreen()

    def _place_initial(self):
        """저장된 x/y 가 있으면 거기, 없으면 작업 영역 오른쪽 아래. 창 전체가 화면 안에 남게 클램프."""
        avail = QApplication.primaryScreen().availableGeometry()
        x = self.cfg.get("x")
        y = self.cfg.get("y")
        if x is None or y is None:
            x = avail.right() - self.W - 24
            y = avail.bottom() - self.H - 24
        x = min(max(int(x), avail.left()), avail.right() - self.W + 1)
        y = min(max(int(y), avail.top()), avail.bottom() - self.H + 1)
        self.move(x, y)

    # ── 논리 창 ↔ 실제 창 (macOS 판 roam_env / roam_crop_now / window_center / place_window_center) ──
    def roam_env(self):
        env = self.state.get("roam_env")
        return env if env else (float(self.width()), float(self.height()))

    def roam_crop_now(self):
        crop = self.state.get("roam_crop")
        if crop:
            return crop
        w_, h_ = self.roam_env()
        return (0.0, 0.0, w_, h_)

    def window_center(self):
        """논리 full 창의 중심 (전역 좌표, y 아래). crop 이 없으면 실제 창 중심과 같다."""
        cx, cy, cw, ch = self.roam_crop_now()
        w_, h_ = self.roam_env()
        return (self.x() - cx + w_ / 2, self.y() - cy + h_ / 2)

    def roam_logical_origin(self):
        cx, cy, cw, ch = self.roam_crop_now()
        return (self.x() - cx, self.y() - cy)

    def place_window_center(self, pos):
        """논리 중심 pos 에 맞춰 실제 창(현재 crop)을 놓는다. 크기가 다르면 크기까지."""
        cx, cy, cw, ch = self.roam_crop_now()
        w_, h_ = self.roam_env()
        ox = pos[0] - w_ / 2 + cx
        oy = pos[1] - h_ / 2 + cy
        if abs(self.width() - cw) > 0.5 or abs(self.height() - ch) > 0.5:
            self.setGeometry(int(round(ox)), int(round(oy)), int(round(cw)), int(round(ch)))
        else:
            self.move(int(round(ox)), int(round(oy)))

    def roam_screen_bounds(self, scr):
        avail = scr.availableGeometry()
        w_, h_ = self.roam_env()
        return (avail.left() + w_ / 2, avail.top() + h_ / 2,
                avail.left() + avail.width() - w_ / 2, avail.top() + avail.height() - h_ / 2)

    def roam_bounds(self):
        """창이 있는 화면의 허용 중심 rect (호환용 — screens 가 있으면 상태기계가 자기 화면의 bounds 를 쓴다)."""
        return self.roam_screen_bounds(self._screen())

    def roam_screens(self):
        """모든 화면의 RoamScreen(id, 실제 frame, 중심 허용 bounds). 창보다 작은 화면은 뺀다."""
        out = []
        for scr in QApplication.screens():
            b = self.roam_screen_bounds(scr)
            if b[0] > b[2] or b[1] > b[3]:
                continue
            g = scr.geometry()
            out.append(cp.RoamScreen(scr.name(), (g.left(), g.top(), g.left() + g.width(), g.top() + g.height()), b))
        return tuple(out)

    def roam_current_bounds(self):
        for scr in self.roam_screens():
            if scr.id == self.roamer.screen:
                return scr.bounds
        return self.roam_bounds()

    def roam_env_update(self):
        """크기 조절·펫 교체 뒤: 실제 창을 새 full 크기로 되돌려 두었으므로 crop 은 없고 논리 크기는 새 W×H."""
        self.state["roam_env"] = (float(self.W), float(self.H))
        self.state["roam_crop"] = None
        self.state["roam_rects"] = None
        self.state["roam_mode"] = None

    def roam_resync(self):
        """창 크기가 바뀐 뒤: 외접원 갱신, 하던 이동은 그 자리에서 접고, 창 전체가 화면 안에 남게 재배치."""
        w_, h_ = self.roam_env()
        self.roamer.radius = math.hypot(w_ / 2, h_ / 2)
        now = time.monotonic()
        cx, cy = self.roamer.pos if self.roamer.away else self.window_center()
        x0, y0, x1, y1 = self.roam_current_bounds()
        if x0 <= x1 and y0 <= y1:
            cx, cy = min(max(cx, x0), x1), min(max(cy, y0), y1)
        if self.roamer.away:
            self.roamer.release(now, (cx, cy), False)
        else:
            self.roamer.set_home((cx, cy), now)
        self.place_window_center((cx, cy))

    # ── 표시 계층 (macOS 판 roam_mode_now / roam_summary_text / roam_apply_display) ──
    def roam_mode_now(self):
        mode = self.state.get("roam_mode")
        if mode is None:
            return cp.DISPLAY_FULL if self.state["show_panel"] else cp.DISPLAY_FOLDED
        return mode

    def roam_summary_text(self):
        """요약 필 내용 → (제공자별 블록, 폭, 높이) — macOS 판 roam_summary_text 와 같은 규칙.

            blocks = [(provider_id, [[(text, kind), ...], ...]), ...]

        **여기서 접히고, 그린 뒤에 다시 자르는 곳은 없다.** 접힘은 cp.summary_lines 가 전부
        끝낸다. 예전 Qt 경로는 이 함수가 (main, sub) 두 줄만 돌려주고 _draw_summary_pill 이
        cp.roam_fit_runs 로 잘랐는데, 그 자리가 정확히 Codex 행이 화면에 닿지 못하던 원인이다
        (코어 summary_lines docstring). 잘라 내는 쪽은 언제나 맨 뒤 구간이었고, 맨 뒤는 언제나
        새로 붙인 제공자였다.

        여기서 하는 거르기는 **사용자가 고른 것**뿐이다: 제공자 표시(show_claude/show_codex)와
        게이지 선택(claude_gauges, cp.filter_claude_rows). Codex 쪽의 같은 거르기는 codex_summary 훅
        (cp.codex_summary_segment)이 한다. 어느 행을 쓸지(게이지 앞 3행, 크레딧은 그 한도 밖)는
        cp.roam_summary 가 정한다. 숫자는 언제나 서버 값이다 — 서버 행이 없으면 로그가 무엇을
        말하든 상태 문구이고, 추정치와 그 ⚠ 표식은 2026-10-05 에 없어졌다(macOS 판과 같다).

        매 tick(20 Hz) 불리므로 같은 입력·같은 5초 창 안에서는 메모한 값을 돌려준다.
        """
        st = self.state
        stats = st["stats"]
        oauth = st["oauth"]
        R = cp.RUNTIME
        show_claude = cp.provider_shown(R, "claude")
        show_codex = cp.provider_shown(R, "codex")
        key = (R["mode"], cp.L["lang"], st.get("onboard"), id(stats), id(oauth),
               st["cost"], st["cost_month"], R.get("api_budget"),
               bool(cp.OAUTH_STATUS.get("auth_error")), bool(st.get("api_error")),
               bool(st.get("api_stale")), st.get("credit_text"), id(st.get("codex")),
               show_claude, tuple(R.get("claude_gauges") or ()), show_codex,
               R.get("codex_mode"), tuple(R.get("codex_gauges") or ()),
               bool(R.get("openai_admin_key")), R.get("codex_budget"),
               st.get("codex_cost"), st.get("codex_cost_month"),
               bool(st.get("codex_api_error")), bool(st.get("codex_api_stale")),
               bool(cp.CODEX_STATUS.get("auth_error")),
               int(time.time() / 5))
        memo = getattr(self, "_summary_memo", None)
        if memo and memo[0] == key:
            return memo[1]
        # 사용자가 고른 게이지만. 거른 뒤 하나도 안 남으면 Claude 줄은 없다 — 빈 목록을
        # roam_summary 에 넘기면 '서버 행 없음'으로 읽혀 엉뚱한 상태 문구가 뜬다.
        claude_rows_gone = False
        if oauth:
            picked = cp.filter_claude_rows(oauth, R.get("claude_gauges") or [])
            claude_rows_gone = not picked
            now_utc = datetime.now(timezone.utc)
            rows = []
            for label, pct, rdt, rtxt in picked:
                reset_s = cp.fmt_countdown(rdt, now_utc) if rdt is not None else (rtxt or None)
                rows.append((label, pct, reset_s))
            oauth = rows
        segment = cp.roam_summary(R["mode"], oauth, stats, st.get("onboard"), st["cost"],
                                  bool(R.get("admin_key")), st["cost_month"],
                                  spike_first=cp.provider_spiking(stats, "claude", R),
                                  cost_budget=float(R.get("api_budget") or 0),
                                  auth_error=bool(cp.OAUTH_STATUS.get("auth_error")),
                                  api_error=bool(st.get("api_error")),
                                  api_stale=bool(st.get("api_stale")),
                                  credit_text=st.get("credit_text"))
        if not show_claude or (claude_rows_gone and R["mode"] != "api"):
            segment = None
        # 다른 제공자는 구간을 뒤에 덧붙이기만 한다 — 그리기·폭 계산은 run 단위라 손댈 곳이 없다.
        # 모듈 함수를 이름으로 부르지 않고 state 훅으로 받는다(roam_release·autostart_read 와
        # 같은 이유): 창 없는 시험은 손으로 만든 state 로 이 함수를 돌리고, 훅이 그냥 없으면
        # 그 시험의 범위가 그대로 유지된다. 훅이 없거나 읽을 게 없으면 **구간 자체가 없다** —
        # 0% 도, 빈 '조회 중' 줄도 지어내지 않는다.
        codex_hook = st.get("codex_summary")
        codex_seg = codex_hook() if codex_hook else None
        # Codex 만 쓰는 사용자에게 "Claude Code 미설치/로그인 필요"를 계속 들이밀지 않는다 —
        # Codex 행이 실제로 뜬다면(= 그 제공자를 켜서 쓰고 있다는 뜻) 온보딩 안내는 그 사람에게
        # 할 일이 없는 문구다. 토큰 만료·조회 중 같은 다른 status 는 그대로 둔다 — 저건
        # "Claude Code 를 쓰다가 지금 문제"라는 뜻이라 Codex 유무와 무관하게 알려야 한다.
        # (코어 roam_summary_text 와 같은 조건 — 두 플랫폼이 같은 규칙을 쓴다.)
        claude_onboarding_suppressed = (
            segment is not None
            and segment[0] == "status" and segment[1] in ("onb_install", "onb_login")
            and bool(codex_seg) and codex_seg[0] != "status"
        )
        # 지금 떠 있는 상태 키 — 필 클릭의 뜻을 고를 때 쓴다. 상태 문구가 아니면 None 이라
        # 숫자가 떠 있는 필의 클릭은 아무 뜻도 갖지 않는다. 위에서 억눌러 화면에 보이지 않는
        # 상태를 클릭 의미로 남겨 두면, 안 보이는 문구를 누른 것으로 처리하는 유령 클릭이 생긴다.
        st["summary_status"] = (
            None if claude_onboarding_suppressed or segment is None
            else (segment[1] if segment[0] == "status" else None)
        )
        measure = lambda v: self._text_w(v, self.F_SUMMARY)
        # 리셋 전용 measure. cp.summary_lines 는 **줄 전체가 sub 인 줄**에만 이것을 쓴다 —
        # 그리기(_draw_summary_pill)가 `all(kind == "sub")` 로 글꼴을 고르는 것과 같은
        # 줄 단위 판정이다. run 단위로 고르면 인라인된 리셋 조각만 9.5pt 로 재어 그려지는
        # 것보다 작게 잡고, 너무 늦게 접어 줄이 필 밖으로 넘친다(반대 방향의 같은 버그).
        measure_sub = lambda v: self._text_w(v, self.F_SUMMARY_SUB)
        # ── 제공자별 상태와 로딩 행렬 ────────────────────────────────────────────
        # 제공자마다 상태가 셋이다: **없음**(읽을 것이 없다) / **받는중**(첫 응답 전) /
        # **옴**(수치가 있다). 규칙 하나: **모든 제공자가 '받는중'이면 전역 한 줄에 마크
        # 없음**, 그 외에는 제공자마다 자기 블록과 자기 마크 — 아직 받는 중인 쪽도 자기
        # 마크와 함께 '조회 중'을 보인다. 그래야 "느린 거지 없는 게 아니다"가 전달된다.
        # 두 제공자는 **대칭**이고 어느 쪽도 먼저 보지 않는다(한쪽을 먼저 보는 구조면
        # 세 번째 제공자가 오는 날 또 고쳐야 한다).
        # '받는중'과 '없음'을 가르는 신호. 새 state 키를 만들지 않고 이미 있는 것을 읽는다:
        # stats 는 새로고침 워커가 한 번이라도 끝나야 dict 가 되고, 그 한 번의 패스가
        # oauth 와 codex 를 **같이** 가져온다. 그래서 오늘은 두 제공자의 '첫 응답 도착'이
        # 같은 순간이다. (두 조회가 나중에 서로 독립이 되면 제공자별 신호가 필요해진다.)
        fetched = isinstance(st.get("stats"), dict)
        kinds = {}
        for pid, seg in (("claude", segment), ("codex", codex_seg)):
            if not seg:
                continue                    # 꺼졌거나 보일 게 없는 제공자 — 블록이 없다
            # Codex 의 API 모드 상태(codex_need_admin_key 등)는 그 제공자의 할 일이라 Codex
            # 블록으로 보인다. 그 밖의 Codex 상태(조회 중 등)는 블록을 만들지 않는다.
            codex_own = pid == "codex" and seg[0] == "status" and str(seg[1]).startswith("codex_")
            if seg[0] != "status" or codex_own:
                kinds[pid] = ("ready", seg)
            elif not fetched and seg[1] in ("loading", "scanning"):
                # '받는중'은 **일반 대기 상태(loading/scanning)일 때만**이다. api_key_rejected·온보딩·
                # 토큰 만료 같은 구체적인 상태는 이미 '진짜 답'이므로 '조회 중'으로 덮으면
                # 사용자가 자기가 할 수 있는 일이 있다는 것을 영원히 모른다 — 키가 거부된
                # 뒤에도 필이 "조회 중…"을 띄우던 것이 정확히 그 증상이다.
                kinds[pid] = ("loading", ("status", "loading"))
            else:
                kinds[pid] = ("absent", seg)
        if not kinds:
            # 보일 제공자가 없다. 둘 다 꺼 두었으면 그렇다고 말하고(설정으로 가는 클릭),
            # 켜 둔 쪽이 아직 아무것도 못 냈으면 기다리는 중이다.
            key_ = "no_providers" if not (show_claude or show_codex) else (
                "scanning" if fetched else "loading")
            groups = [(None, [("status", key_)])]
            if key_ == "no_providers":
                st["summary_status"] = key_
        elif all(k == "loading" for k, _s in kinds.values()):
            # 공통 로딩 — 어느 제공자의 줄도 아니므로 마크가 붙으면 안 된다.
            groups = [(None, [("status", "loading")])]
        else:
            groups = []
            for pid in ("claude", "codex"):
                kind, seg = kinds.get(pid, ("absent", None))
                if kind in ("ready", "loading"):
                    groups.append((pid, [seg]))
                elif seg is not None and pid == "claude" and not claude_onboarding_suppressed:
                    # Claude 의 status(온보딩·토큰 만료·대기 중)는 버리지 않는다. 다만
                    # 제공자 블록이 아니라 전역 줄이다 — 마크 없이 필 전체 폭을 쓴다.
                    # (Codex 가 실제로 뜬 상태의 온보딩 안내는 위에서 이미 걸러졌다.)
                    groups.insert(0, (None, [seg]))
        # 폭을 **접기 전** 내용에서 정한다. 접은 뒤의 폭으로 정하면 영원히 안 커진다:
        # 접힘은 지금 예산에 맞춰 줄을 나누므로 결과는 언제나 예산 안이고, 그러면 "더
        # 필요하다"는 신호가 나올 자리가 없다. 펼친 폭으로 창을 먼저 키우고(화면이 끝이다),
        # 그 다음에 새 예산으로 접는다.
        # 폭을 **접기 전 줄** 에서 정한다. 줄 모양은 cp.summary_lines 에게 **물어서** 얻는다 —
        # 예산을 무한으로 주면 아무것도 접히지 않으므로 돌아오는 것이 접히기 전의 진짜 줄이고,
        # 인라인(게이지 하나면 리셋을 같은 줄에)도 이미 반영돼 있다. 규칙을 여기서 다시
        # 구현하지 않는 이유는 그렇게 하면 두 플랫폼이 갈리기 때문이다.
        #
        # 그리고 각 줄을 **렌더러가 그 줄에 고를 글꼴**로 잰다. 이것이 줄 단위 결정이라는
        # 점이 요점이다: 인라인된 리셋 run 은 kind 가 "sub" 이지만 11pt 로 그려지는 줄 안에
        # 산다. run 종류별로 글꼴을 고르면 그 조각만 9.5pt 로 재어 반대 방향으로 같은 버그를
        # 만든다. 실측: '주간 73% · 5d 18h' 는 11pt 로 124.0pt 인데, 인라인 전 두 줄을
        # 따로 재면 max(63.0, 95.0) = 95.0 이라 29.0pt 가 모자랐다.
        probe = cp.summary_lines(groups, measure, float("inf"), measure_sub)
        need = 0.0
        for _pid, lines in probe:
            for line in lines:
                font = self.F_SUMMARY_SUB if all(k == "sub" for _t, k in line) else self.F_SUMMARY
                need = max(need, sum(self._stable_w(txt, font) for txt, _k in line))
        # 훅이 주는 것은 **글자 자리** 폭이고 cp.summary_lines 가 받는 것은 **필 안쪽 전체**
        # 폭이다 — 로고 뺄셈은 summary_lines 의 것이라(그 docstring 참조) 여기서 로고 폭을
        # 되돌려 준다. 이 한 줄이 없으면 예산이 두 번 깎여, 가장 긴 줄이 딱 로고 폭만큼
        # 넘쳐 접힌다. 화면에서는 마지막 게이지의 라벨과 값이 갈라지는 것으로 보인다 —
        # 그리고 그 변이는 폭 단언으로는 영원히 안 잡힌다(과하게 접힌 줄은 어떤 예산에도
        # 들어가므로). 실제 어댑터를 구동하는 시험만 잡는다.
        budget = self._pill_budget_for(need) + cp.SUMMARY_LOGO_W
        blocks = cp.summary_lines(groups, measure, budget, measure_sub)
        # 각 줄을 **그 줄을 그리는 글꼴**로 잰다. 모든 줄을 11pt 로 재면 9.5pt 로 그려질
        # 리셋 줄이 실제보다 넓게 잡혀 필이 부푼다 — 접힘과 같은 뿌리의 두 번째 사례다.
        text_w = 0.0
        for _pid, lines in blocks:
            for line in lines:
                me = measure_sub if all(k == "sub" for _t, k in line) else measure
                text_w = max(text_w, sum(me(txt) for txt, _k in line))
        n_lines = sum(len(lines) for _pid, lines in blocks)
        if n_lines != st.get("summary_lines_n"):
            # 높이도 폭과 같은 경로로 반영한다 — 기록만 하고 틱의 _relayout() 이 창을 맞춘다.
            # 이 갱신을 빼면 세 줄이 두 줄 높이 안에 그려져, 폭을 고쳐 놓고 높이로 똑같이
            # 잘려 보이는 상태가 된다(pill_band 주석).
            st["relayout"] = True
        st["summary_lines_n"] = n_lines           # 창 높이가 따라간다(pill_band)
        value = (blocks, float(text_w) + cp.SUMMARY_LOGO_W, cp.pill_h(n_lines))
        self._summary_memo = (key, value)
        return value

    def roam_apply_display(self, phase):
        """표시 모드 → crop/rect → 실제 창 크기·원점. 경로·집은 건드리지 않는다 → 다시 그릴지."""
        mode = self.roam_display.mode(phase, self.state["show_panel"])
        text_w, text_h = (self.roam_summary_text()[1:] if mode != cp.DISPLAY_FOLDED else (0.0, cp.SUMMARY_H))
        w_, h_ = self.roam_env()
        lay = cp.roam_frame(self.roamer.pos, mode, self.pet_on_right(), self.pet_on_bottom(),
                            w_, h_, self.PW, self.PH, self.pill_band(), self.scale, text_w, text_h)
        crop = tuple(lay["crop"])
        changed = crop != self.state.get("roam_crop") or mode != self.state.get("roam_mode")
        if changed:
            center = self.window_center()      # 변경 '직전' 실제 창의 논리 중심 기준 (드래그 뒤 위치 보존)
        self.state["roam_mode"] = mode
        self.state["roam_crop"] = crop
        self.state["roam_rects"] = lay
        if changed:
            self.place_window_center(center)
        return changed

    def roam_apply_effect(self, now, effect):
        """점프의 출발/착지 효과를 창 불투명도로 그린다. 효과가 없으면 1 로 복원 — 값이 바뀔 때만."""
        fx = self.roam_clock.setdefault("fx", {"effect": None, "since": now, "alpha": 1.0})
        if effect != fx["effect"]:
            fx["effect"], fx["since"] = effect, now
        if effect == "takeoff":
            f = min(1.0, (now - fx["since"]) / max(self.roamer.cfg["jump_prep_s"], 1e-6))
            alpha = 1.0 - 0.85 * f
        elif effect == "landing":
            f = min(1.0, (now - fx["since"]) / max(self.roamer.cfg["jump_land_s"], 1e-6))
            alpha = 0.15 + 0.85 * f
        else:
            alpha = 1.0
        if abs(alpha - fx["alpha"]) > 1e-3:
            fx["alpha"] = alpha
            self.setWindowOpacity(alpha)

    def roam_tick(self, now):
        """Roamer 한 step 을 돌리고 창/애니메이션/표시에 반영한다 → 다시 그릴지. (macOS 판 roam_tick)"""
        st = self.state
        if now - self.roam_clock["rm_at"] >= 1.0:
            self.roam_clock["rm_at"] = now
            st["reduce_motion"] = reduce_motion()
        enabled = bool(cp.RUNTIME.get("roam")) and not st["reduce_motion"]
        blocked = bool(st["hover"]) or (st["override"] is not None and st["override"] != st["roam_anim"])
        busy = bool(st["menu_open"]) or bool(st["roam_hold"]) or bool(spike_info(st["stats"]))
        st["roam_hold"] = False
        gap = now - self.roam_clock.get("last", now)
        self.roam_clock["last"] = now
        mp = QCursor.pos()
        out = self.roamer.step(now, (float(mp.x()), float(mp.y())), self.roam_bounds(), enabled=enabled,
                               dragging=bool(st["dragging"]), blocked=blocked, busy=busy,
                               screens=self.roam_screens())
        self.roam_apply_effect(now, out.effect)
        self.roam_display.note(out.phase, self.roamer.kind, out.away,
                               interrupted=(not enabled) or busy or gap > self.roamer.cfg["gap_s"],
                               enabled=enabled, settled=self.roamer.settled)
        dirty = False
        if out.moved:
            if st["roam_layout"] is None:
                st["roam_layout"] = (self.pet_on_right(), self.pet_on_bottom())   # 이동 중 배치 고정
            self.place_window_center(out.pos)
            dirty = True
        if self.roam_apply_display(out.phase):
            dirty = True
        if out.anim != st["roam_anim"]:
            if out.anim is not None:
                self.set_override(out.anim, sticky=True)
            elif st["override"] == st["roam_anim"]:
                self.clear_sticky()
            st["roam_anim"] = out.anim
            dirty = True
        return dirty

    # ── 배치 (macOS 판 petOnRight/petOnBottom/petOrigin/pillTop/pillLeft/btnOrigin) ──
    def pet_on_right(self):
        frozen = self.state.get("roam_layout")
        if frozen is not None:
            return frozen[0]
        vf = self._screen().geometry()
        return self.window_center()[0] >= vf.left() + vf.width() / 2

    def pet_on_bottom(self):
        """Qt 는 y 가 아래로 커진다: 논리 창 중심이 화면 세로 중앙선보다 아래면 True → 필이 위로 붙음."""
        frozen = self.state.get("roam_layout")
        if frozen is not None:
            return frozen[1]
        vf = self._screen().geometry()
        return self.window_center()[1] >= vf.top() + vf.height() / 2

    def pill_rect(self):
        """요약 필 사각형(실제 창 좌표). 표시 계층이 아직 안 돌았으면 논리 창 = 실제 창이라 같은 규칙으로 계산. folded 면 None."""
        rects = self.state.get("roam_rects")
        if rects:
            return rects.get("pill")
        _blocks, text_w, text_h = self.roam_summary_text()
        return cp.roam_pill_rect(self.roam_mode_now(), self.pet_on_right(), self.pet_on_bottom(),
                                 self.W, self.PW, self.PH, self.pill_band(), text_w, text_h)

    def pet_origin(self):
        rects = self.state.get("roam_rects")
        if rects:
            return (rects["sprite"][0], rects["sprite"][1])
        py = self.pill_band() + cp.GAP if self.pet_on_bottom() else 2
        return (self.W - self.PW - 6, py) if self.pet_on_right() else (6, py)

    def btn_origin(self):
        rects = self.state.get("roam_rects")
        if rects:
            return (rects["button"][0], rects["button"][1])
        px, py = self.pet_origin()
        by = py + int(26 * self.scale)
        return (px - cp.BTN_R * 2 - 2, by) if self.pet_on_right() else (px + self.PW + 2, by)

    # ── 애니메이션 (macOS 판 tick_ 과 같은 규칙) ──
    def set_override(self, name, sticky=False):
        if self.state["override"] != name:
            self.state["frame"] = 0
            self.state["elapsed"] = 0.0
            self.state["resting"] = False
        self.state["override"] = name
        self.sticky["on"] = sticky

    def clear_sticky(self):
        if self.sticky["on"]:
            self.sticky["on"] = False
            self.state["override"] = None
            self.state["frame"] = 0

    def current_mood(self):
        st = self.state
        if st["override"]:
            return st["override"]
        stats = st["stats"]
        if stats and spike_info(stats):
            return "failed"
        # 서버 %가 기준이다(Claude·Codex 중 보이는 쪽). 서버 행이 없으면 idle — 로그에서
        # 기분을 만들지 않는다(macOS 판 current_mood 와 같다).
        # 제공자별로 따로 넘긴다 — 각자 자기 게이지 선택으로 걸러진다(cp.mood_for).
        return cp.mood_for(None, st["oauth"], codex_rows=st.get("codex"))

    def _apply_pending(self):
        """새로고침 워커가 남긴 결과를 메인 스레드(tick)에서 반영한다 — 워커는 위젯·상태를 직접 만지지 않는다."""
        with self._refresh_lock:
            pending, self._pending = self._pending, None
        if pending is None:
            return False
        prev_oauth, prev_codex = self.state["oauth"], self.state.get("codex")
        self.state.update(pending)
        # 세션 리셋 점프 — 서버 세션 행이 >5% 에서 <1% 로(제공자별, macOS 판 refresh 워커와 같은
        # cp.session_reset_jump). 로그 %는 쓰지 않는다. 이번 패스가 행을 못 가져왔으면(실패한
        # 패스) 판정하지 않는다 — 비교할 '이번 값'이 없다.
        if ("oauth" in pending or "codex" in pending) and cp.session_reset_jump(
                prev_oauth, self.state["oauth"], prev_codex, self.state.get("codex")):
            self.set_override("jumping")
        return True

    def _relayout(self):
        """geom 이 바뀌었다(행 수·크기·펫). 실제 창을 새 full 크기로 되돌리고 자율 이동을 재동기화한다."""
        lx, ly = self.roam_logical_origin()
        self.PW, self.PH, self.W, self.H = self.geom()
        self.setGeometry(int(round(lx)), int(round(ly)), self.W, self.H)
        self.roam_env_update()
        self.roam_resync()

    def tick(self):
        st = self.state
        now = time.monotonic()
        dirty = self._apply_pending()
        if st.pop("relayout", False):              # paint 밖에서 크기를 바꾼다 (paint 중 resize 는 재진입 위험)
            self._relayout()
            dirty = True
        mood = self.current_mood()
        if mood != st["last_mood"]:
            st["last_mood"] = mood
            st["mood"] = mood
            st["frame"] = 0
            st["elapsed"] = 0.0
            st["resting"] = False
            st["rest_elapsed"] = 0.0
            dirty = True
        dur, loop, rest = cp.STATE_CFG.get(mood, cp.DEFAULT_CFG)
        if st["resting"]:
            st["rest_elapsed"] += TICK_MS
            if st["rest_elapsed"] >= rest:
                st["resting"] = False
                st["rest_elapsed"] = 0.0
                st["frame"] = 0
                st["elapsed"] = 0.0
        else:
            st["elapsed"] += TICK_MS
            if st["elapsed"] >= dur:
                st["elapsed"] = 0.0
                seq_len = len(self.frames.get(mood, self.frames["idle"]))
                nxt = st["frame"] + 1
                if nxt >= seq_len:
                    st["frame"] = 0
                    if not loop and not self.sticky["on"]:
                        st["override"] = None
                    elif rest > 0 and not self.sticky["on"]:
                        st["resting"] = True
                else:
                    st["frame"] = nxt
                dirty = True
        # 호버 (접기 버튼 표시) — 실제 창 기준
        hover = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if hover != st["hover"]:
            st["hover"] = hover
            dirty = True
        # 근접 인사
        if (cp.RUNTIME.get("greet") and not st["dragging"] and st["override"] is None
                and not spike_info(st["stats"])):
            if time.time() >= st["greet_cool"]:
                mp = QCursor.pos()
                px, py = self.pet_origin()
                cx = self.x() + px + self.PW / 2
                cy = self.y() + py + self.PH / 2
                if math.hypot(mp.x() - cx, mp.y() - cy) < NEAR_PX + self.PW / 2:
                    self.set_override("waving")
                    st["greet_cool"] = time.time() + GREET_COOLDOWN
                    dirty = True
        # 조용한 동행 — 스스로 돌아다니기 (인사 판정 뒤, 같은 틱 안에서)
        if self.roam_tick(now):
            dirty = True
        if spike_info(st["stats"]):
            dirty = True
        if st["repaint"]:
            st["repaint"] = False
            dirty = True
        if dirty:
            self.update()

    # ── 사용량 새로고침 (30초, 백그라운드 스레드) ──
    def refresh(self):
        with self._refresh_lock:
            self._refresh_gen += 1
            gen = self._refresh_gen

        def work():
            values = {}
            try:
                oauth = cp.fetch_exact_usage()                 # 정확 모드 (180s 캐시)
                # Codex 자격증명이 없으면 파일 한 번 못 열고 끝난다 — 망을 타지 않으므로
                # Codex 를 안 쓰는 사용자에게 드는 비용은 없다. 읽을 게 없으면 None 이고,
                # 그러면 어댑터가 구간 자체를 안 붙인다(0% 를 지어내지 않는다).
                codex = cp.fetch_codex_usage()
                # 로그는 급증 감지에만 쓴다. 모델별 레인의 대상은 서버의 모델별 행이 정한다.
                s = cp.compute_usage(model_keyword=cp.model_keyword_from_rows(oauth))
                now_utc = s["now"]
                codex_entries = []
                codex_logs = (cp.provider_shown(cp.RUNTIME, "codex")
                              and cp.RUNTIME.get("codex_mode") != "api")
                if codex_logs and (codex or cp.LEARNED_LIMITS.get("codex_session")
                                   or cp.LEARNED_LIMITS.get("codex_weekly")):
                    codex_entries = cp.parse_codex_entries(now_utc - timedelta(days=7))
                # 급증 한도는 서버 %로부터 배운다(보정 UI 대체). 배운 뒤 같은 패스의 로그로
                # 급증을 다시 판정한다 — 파일을 다시 읽지 않는 계산뿐이다. 엔트리는 state 에
                # 남기지 않는다(macOS 판 워커처럼 꺼내서 쓴다).
                rows = s.pop("rows", None) or []
                # 같은 응답에 EMA 를 거듭 걸지 않게 마지막 '성공' 응답의 시각을 키로 넘긴다(macOS 판과 같다) —
                # 캐시 적중도, 일시 실패로 유지한 직전 값도 같은 키라 다시 배우지 않는다.
                cp.learn_server_limits(oauth, codex, rows, codex_entries,
                                       model_kw=s.get("model_kw"),
                                       claude_fetch=cp._oauth_cache["ok_t"],
                                       codex_fetch=cp._codex_cache["ok_t"])
                try:
                    mult = float(cp.RUNTIME.get("spike_mult", 1.0)) or 1.0
                except (TypeError, ValueError):
                    mult = 1.0
                spikes = dict(cp.claude_spikes(rows, now_utc, s.get("model_kw"), mult=mult))
                spikes.update(cp.codex_spikes(codex_entries, now_utc, mult=mult))
                s["spikes"] = spikes
                values["stats"] = s
                values["oauth"] = oauth
                values["codex"] = codex
                values["cost"] = cp.fetch_api_cost_today()
                if cp.RUNTIME["mode"] == "api":
                    values["cost_month"] = cp.fetch_api_cost_month()
                # Codex API 모드: OpenAI 조직 비용. 실패 종류는 Claude 쪽과 같은 규칙으로
                # 키 거부(사용자가 할 일 있음)와 일시 실패를 가른다(cp.api_error_kind).
                if cp.RUNTIME.get("codex_mode") == "api" and cp.provider_shown(cp.RUNTIME, "codex"):
                    values["codex_cost"] = cp.fetch_codex_cost_today()
                    values["codex_cost_month"] = cp.fetch_codex_cost_month()
                    _ckind = cp.api_error_kind(cp.CODEX_API_STATUS.get("last_error"))
                    values["codex_api_error"] = _ckind == "key"
                    values["codex_api_stale"] = _ckind == "transient"
                # Codex 를 보이는데 토큰이 없으면 우클릭 메뉴에 설치/로그인(macOS 판과 같은 판단).
                # Codex 를 쓰는 사람(CLI 또는 Codex 홈이 있음)에게만 낸다.
                values["codex_onboard"] = cp.compute_codex_onboard_state(
                    cp.provider_shown(cp.RUNTIME, "codex"), cp.RUNTIME.get("codex_mode"),
                    bool(cp.read_codex_token(cp.codex_auth_path())), bool(find_codex_cli()),
                    cp.codex_home_exists())
                # 크레딧 금액 문자열. 모드는 **지금** 읽는다(파싱 시점이 아니라) — 파싱은
                # 180초 캐시 뒤에 있어서, 거기서 굳히면 토글을 바꿔도 최대 3분 동안 옛 모드가
                # 남는다. 크레딧 행이 없으면 None 이고, 그러면 roam_summary 가 그 원소를
                # 붙이지 않는다. 문자열을 만드는 것은 워커의 일이다 — roam_summary 는 순수해야 한다.
                values["credit_text"] = (
                    cp.credit_row_text(cp.OAUTH_EXTRA["credit"],
                                       cp.credit_display_mode(cp.RUNTIME.get("credit_display")))
                    if cp.OAUTH_EXTRA["credit"] else None)
                # 키가 거부된 뒤에도 필이 "조회 중…" 에 머물던 자리. 마지막 조회의 **실패
                # 종류**를 보고, 사용자가 실제로 할 수 있는 일이 있는 경우만 경고로 올린다 —
                # 401/403 은 키를 고치면 되고, 망 장애나 5xx 는 고칠 키가 없으니 "키를
                # 확인하세요" 라고 말하면 거짓 안내가 된다.
                _api_kind = cp.api_error_kind(cp.API_STATUS.get("last_error"))
                values["api_error"] = _api_kind == "key"
                values["api_stale"] = _api_kind == "transient"
                # 온보딩 안내는 **토큰**으로 판단한다(macOS 워커와 같다) — 로그가 있어도 토큰이
                # 없으면 숫자를 볼 길이 없다. 확인은 캐시·자격증명 파일만(cp.claude_token_present).
                values["onboard"] = cp.compute_onboard_state(oauth, cp.claude_token_present())
                # 토큰을 살려 두는 자리. 판단은 순수 함수(cp.recovery_tick)가 하고 여기서는
                # 실행만 한다. 여기서 action 을 보고 values["onboard"] 를 덮어쓰지 **않는다** —
                # 맥에서 그 두 줄은 도달 불가능한 코드였고, 조건을 느슨하게 풀면 이번엔 반대로
                # 보여 줄 수치가 있는 사용자의 필을 '미설치' 문구로 덮는다.
                self._recovery_step()
            except Exception as e:  # 실패한 패스는 화면에 대기 상태로 남고 다음 새로고침에 다시 시도
                print(f"[refresh] failed: {type(e).__name__}", file=sys.stderr)
            finally:
                with self._refresh_lock:
                    if gen == self._refresh_gen:      # 더 새 요청이 있으면 버린다 (macOS 판 세대 규칙)
                        self._pending = values
            # 주기적 새 버전 확인 — macOS 판 run_gui 와 같은 규칙: 마지막 확인(또는 앱 시작, main 이 찍는다)에서
            # UPDATE_CHECK_SEC 가 지났을 때만, 그리고 이미 새 버전을 알고 있으면 하지 않는다. 결과는 우클릭 메뉴에 노출될 뿐
            # 자동으로 설치하지 않는다.
            try:
                self._reap_installer()
                if not self.state.get("update") and time.time() - cp._upd_cache["t"] > cp.UPDATE_CHECK_SEC:
                    self._run_update_check()
            except Exception as e:
                print(f"[update] periodic check failed: {type(e).__name__}", file=sys.stderr)
        threading.Thread(target=work, daemon=True).start()

    def _color(self, h, a=1.0):
        c = QColor(h)
        c.setAlphaF(a)
        return c

    def _text(self, p, x, y, s, font, color):
        p.setFont(font)
        p.setPen(QColor(color))
        fm = QFontMetrics(font)
        p.drawText(QPoint(int(x), int(y + fm.ascent())), s)
        return fm.horizontalAdvance(s)

    def _text_w(self, s, font):
        return QFontMetrics(font).horizontalAdvance(s)

    # ── 요약 필 폭 (macOS 판 _pill_text_budget / _stable_w / _pill_width_step / _apply_pill_width) ──
    def _pill_text_budget(self):
        """접힘이 쓸 수 있는 **텍스트** 가로 예산.

        접힘에 쓰는 예산과 필이 실제로 주는 폭이 **같은 뿌리**에서 나와야 한다 — geom() 의 W 다.
        cp.roam_pill_rect 도 같은 W 를 받으므로 "접힘이 믿는 폭 == 필이 주는 폭"이 구성상
        성립한다. 맥에서 이 둘이 갈라졌을 때(화면 폭 대 300) 넘치는 줄이 필 왼쪽에서 시작해
        로고를 덮고 말줄임표 없이 잘렸다.

        반환값은 **글자 자리** 폭이다 — 로고 폭까지 뺀 값. cp.summary_lines 가 받는 것은
        '필 안쪽 전체' 폭이라 의미가 다르므로, 어댑터가 넘기기 직전에 SUMMARY_LOGO_W 를
        되돌려 준다. 뺄셈의 주인은 summary_lines 이고(그 docstring), 여기서 뺀 것을 거기서
        또 빼면 예산이 두 번 깎여 가장 긴 줄이 딱 로고 폭만큼 넘쳐 접힌다.
        """
        room = max(cp.SUMMARY_MIN_W, self.geom()[2] - 2 * cp.SUMMARY_EDGE)
        return max(cp.SUMMARY_MIN_W, room - 2 * cp.PILL_PAD - cp.SUMMARY_LOGO_W)

    def _widest_digit(self):
        """필 글꼴에서 가장 넓은 숫자 글리프. 한 번만 재고 들고 있는다."""
        d = getattr(self, "_widest_digit_cache", None)
        if d is None:
            d = max("0123456789", key=lambda c: self._text_w(c, self.F_SUMMARY))
            self._widest_digit_cache = d
        return d

    def _stable_w(self, text, font=None):
        """숫자의 **값**에 흔들리지 않는 폭. 자릿수는 그대로 반영한다.

        필 폭이 실룩거리는 원인은 글꼴이 proportional 이라 숫자마다 폭이 다른 것이다
        (`1` 이 `0` 보다 좁아 `10%` 가 `9%` 보다 넓고 `11%` 는 `10%` 보다 좁다). 그래서 폭을
        잴 때만 모든 숫자를 가장 넓은 숫자로 바꿔 잰다 — `42% → 43%` 가 폭을 한 톨도 못
        움직인다. (macOS 판 _stable_w 와 같은 규칙)
        """
        widest = self._widest_digit()
        wide = "".join(widest if c.isdigit() else c for c in text)
        return self._text_w(wide, font if font is not None else self.F_SUMMARY)

    def _pill_width_step(self):
        """폭이 움직이는 최소 단위 = 가장 넓은 숫자 글리프 하나의 폭.

        임의의 상수가 아니다. 폭이 변하는 원인이 숫자 한 자리이므로, 그 한 자리가 한 단계
        안에 흡수되는 가장 작은 단위가 이것이다.
        """
        return max(1.0, float(self._text_w(self._widest_digit(), self.F_SUMMARY)))

    def _apply_pill_width(self, needed):
        """필요한 폭을 기록한다. 바뀌었으면 True.

        판단은 cp.next_pill_width 가 한다(순수). **여기서는 창을 건드리지 않는다** — 기록만
        하고, 실제 창 크기 반영은 틱의 _regeom() 이 한다. 이 함수는 요약 텍스트 경로에서
        불리고 그 경로는 그리기 도중에도 돌기 때문이다.
        """
        cur = float(self.state.get("pill_w") or cp.PILL_W)
        avail = self._screen().availableGeometry().width()
        want = cp.next_pill_width(cur, needed, self._pill_width_step(),
                                  max(cp.SUMMARY_MIN_W, avail - 2 * cp.SUMMARY_EDGE))
        if want == cur:
            return False
        self.state["pill_w"] = want
        self.state["pill_w_dirty"] = True
        # 창은 여기서 건드리지 않는다 — 이 경로는 paint 도중에도 돈다. 크기 반영은 틱의
        # _relayout() 이 한다(맥 _regeom 과 같은 춤). 기록만 남긴다.
        self.state["relayout"] = True
        return True

    def _pill_budget_for(self, text_w):
        """요약 경로의 폭 훅: 필요한 폭을 기록하고, 그 폭이 내주는 텍스트 예산을 준다.

        기록과 예산이 **같은 W 에서** 나오는 것이 요점이다(_pill_text_budget 참조).
        """
        self._apply_pill_width(text_w + cp.SUMMARY_LOGO_W + 2 * cp.PILL_PAD)
        return self._pill_text_budget()

    # ── 제공자 마크 (macOS 판 summary_logo_image / _tinted_logo / draw_summary_logo) ──
    def summary_logo_image(self, provider):
        """제공자 마크(QImage) 또는 None. 틴트가 선언된 제공자는 **미리 칠한 사본**을 준다.

        openai.svg 는 fill="currentColor" 라 색을 우리가 정해야 한다 — 안 정하면 기본값인
        검정으로 래스터화되고, 어두운 필 배경에서 그대로 사라진다. claude.svg 는 자체 컬러
        (#D97757)를 갖고 있어 이 비대칭이 생긴다. **어떤 테스트도 이걸 못 잡는다** — 한쪽
        마크만 조용히 안 보이는 번들이 나갈 수 있고, 맥에서 실제로 그 상태였다.

        **그리는 자리에서 칠하려고 하면 안 된다.** 맥에서 setTemplate_(True) + 컨텍스트
        fill 색 조합이 **합쳐서 아무 일도 하지 않은** 기록이 있다(픽셀 분포가 틴트를 건
        경우와 안 건 경우가 바이트 단위로 같았고 둘 다 검정이었다). Qt 도 같은 함정이 있다 —
        setPen/setBrush 는 비트맵 합성을 건드리지 않는다. 그래서 여기서 **CompositionMode_SourceIn**
        으로 알파 안쪽만 색을 갈아 끼운 사본을 만든다. SourceIn 은 대상의 알파를 유지하고
        색만 바꾸므로 맥의 sourceAtop(연산자 5)과 대응한다.

        칠한 사본을 캐시하는 것도 요점이다 — 필은 20 Hz 로 다시 그려진다.
        """
        cache = self._logo_cache
        if provider in cache:
            return cache[provider]
        img = None
        name = cp.SUMMARY_LOGO_FILES.get(provider)
        if name:
            try:
                path = cp.bundled_logo_path(name)
                if path:
                    mark = int(cp.SUMMARY_LOGO_MARK)
                    dpr = float(self.devicePixelRatioF() or 1.0)
                    px = max(1, int(round(mark * dpr)))
                    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
                    img.fill(Qt.transparent)
                    painter = QPainter(img)
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    QSvgRenderer(path).render(painter)
                    tint = cp.SUMMARY_LOGO_TINT.get(provider)
                    if tint:
                        # 알파는 그대로, 색만. 여기서 setBrush/setPen 으로 '칠하려' 하면 무동작이다.
                        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                        painter.fillRect(img.rect(), QColor(tint))
                    painter.end()
                    img.setDevicePixelRatio(dpr)
            except Exception as exc:
                cp._dbg("logo: load failed", provider, type(exc).__name__)
                img = None
        cache[provider] = img
        return img

    def _draw_summary_logo(self, p, provider, left, cy):
        """필 왼쪽에 마크 한 개. 색은 이미 사본에 들어 있으므로 여기서는 칠하지 않는다.

        파일이 없으면 조용히 건너뛴다 — 마크가 없다고 수치를 못 보여 줄 이유는 없고,
        들여쓰기는 그대로라 정렬도 깨지지 않는다.
        """
        img = self.summary_logo_image(provider)
        if img is None:
            return
        mark = float(cp.SUMMARY_LOGO_MARK)
        p.drawImage(QRectF(left, cy - mark / 2.0, mark, mark), img)

    def _draw_runs(self, p, runs, font, x, w, cy):
        """run 들을 **왼쪽 맞춤**으로, 세로는 cy 중심으로 — run 마다 제 색(SUMMARY_COLORS).

        가로 가운데 정렬(`x + (w - total) / 2`)이었는데, 그러면 짧은 줄이 긴 줄과 **다른 x
        에서 시작한다.** 실기 캡처에서 리셋 줄이 첫 줄보다 84pt(4배 기준) 안쪽으로 떠서
        마크와 세로로 맞지 않았다. 줄들은 같은 축에서 시작해야 마크가 그 블록 전체를
        가리키는 것으로 읽힌다.

        마크 없는 전역 상태 줄도 같은 규칙이다. 정렬은 기준점이 필요한데 제공자 줄은
        마크가, 마크 없는 줄은 필 왼쪽 안쪽 가장자리가 기준이라 **둘 다 왼쪽**이고 규칙은
        하나다. 전역 줄이 혼자일 때는 필이 그 줄에 맞춰지므로 가운데와 왼쪽이 픽셀 단위로
        같고, 혼자가 아닐 때는 가운데가 해롭다 — 로딩 행렬에서 Claude 의 token_expired
        상태 줄이 Codex 수치 줄 위에 올 수 있고, 그때 그 줄만 공통 축에서 벗어난다.

        w 는 이제 줄을 놓는 데 쓰이지 않지만(넘침은 cp.summary_lines 가 이미 접어서 없다)
        호출 계약을 유지한다.
        """
        widths = [self._text_w(text, font) for text, _kind in runs]
        cx = x
        lh = QFontMetrics(font).height()
        p.setFont(font)
        for (text, kind), tw in zip(runs, widths):
            p.setPen(QColor(cp.SUMMARY_COLORS.get(kind, cp.TXT_MAIN)))
            p.drawText(QRectF(cx, cy - lh / 2, tw + 2, lh), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, text)
            cx += tw

    def _draw_summary_pill(self, p):
        """요약 필: 펫에 붙은 둥근 필. 제공자 블록마다 왼쪽에 마크, 그 제공자의 모든 줄은 마크 폭만큼 들여쓴다.

        **여기서는 아무것도 자르지 않는다.** 줄을 나누는 일은 cp.summary_lines 가
        (roam_summary_text 경유로) 이미 끝냈고, 그린 뒤에 다시 재는 곳이 있으면 그게 곧
        잘림선이 된다 — Codex 행이 화면에 닿지 못하던 원인이 정확히 이 자리에 있던
        cp.roam_fit_runs 두 줄이었다.

        접혀서 생긴 이어지는 줄도 같은 들여쓰기라 세로로 맞는다. 마크는 run 이 아니라
        **들여쓰기**이므로 폭 계산(cp.summary_lines)과 그리기가 같은 약속을 쓴다.
        """
        pill = self.pill_rect()
        if not pill:
            return
        x, y, w, h = pill
        p.setPen(Qt.NoPen)
        p.setBrush(self._color(cp.PILL_BG, 0.96))
        # 반지름은 **고정**이다. h/2 로 하면 한 줄일 때만 알약이고 네 줄이면 반지름이
        # 39pt 가 되어 타원이 된다. SUMMARY_RADIUS 는 한 줄의 모서리가 정확히 반원이 되는
        # 값이고, 더 크면 곡선이 다음 줄을 먹는다.
        p.drawRoundedRect(QRectF(x, y, w, h), cp.SUMMARY_RADIUS, cp.SUMMARY_RADIUS)
        blocks, _tw, _th = self.roam_summary_text()
        rows = [(pid, line) for pid, lines in blocks for line in lines]
        if not rows:
            return
        indented = x + cp.PILL_PAD + cp.SUMMARY_LOGO_W
        indented_w = w - 2 * cp.PILL_PAD - cp.SUMMARY_LOGO_W
        top = y + (h - len(rows) * cp.SUMMARY_LINE_H) / 2.0
        seen = set()
        for i, (pid, line) in enumerate(rows):
            cy = top + i * cp.SUMMARY_LINE_H + cp.SUMMARY_LINE_H / 2.0
            # pid 가 None 이면 전역 줄이다 — 마크도 들여쓰기도 없고 필 전체 폭을 쓴다.
            # 로고는 "이 줄은 이 제공자의 수치다"라는 표시인데 전역 상태는 아무 제공자의
            # 수치도 아니다.
            text_x = indented if pid is not None else x + cp.PILL_PAD
            text_w = indented_w if pid is not None else w - 2 * cp.PILL_PAD
            if pid is not None and pid not in seen:   # 마크는 제공자의 첫 줄에만
                seen.add(pid)
                self._draw_summary_logo(p, pid, x + cp.PILL_PAD, cy)
            # 리셋 줄은 **작은 글꼴 + dim 색** 둘 다다. 색만으로는 위계가 약해서 리셋 줄이
            # 게이지 줄만큼 눈을 끈다(맥 실기 화면에서 그랬다). 줄 높이는 그대로 두어
            # pill_h(줄 수) 계약을 지킨다 — 16pt 줄상자 안의 9.5pt 글자는 보통 행간이다.
            font = self.F_SUMMARY_SUB if all(k == "sub" for _t, k in line) else self.F_SUMMARY
            self._draw_runs(p, line, font, text_x, text_w, cy)

    def paintEvent(self, event):
        st = self.state
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        stats = st["stats"]
        mood = st["mood"]
        seq = self.frames.get(mood, self.frames["idle"])
        img = seq[0 if st["resting"] else st["frame"] % len(seq)]

        mode = self.roam_mode_now()
        if mode in (cp.DISPLAY_FULL, cp.DISPLAY_SUMMARY):
            self._draw_summary_pill(p)

        px, py = self.pet_origin()
        pet_rect = QRect(int(px), int(py), self.PW, self.PH)
        p.drawPixmap(pet_rect, img)
        spk = spike_info(stats)
        if spk:
            pulse = 0.22 + 0.18 * (0.5 + 0.5 * math.sin(time.time() * 5))
            p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.fillRect(pet_rect, self._color(spk[0], pulse))
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if st["hover"]:
            bx, by = self.btn_origin()
            r = cp.BTN_R
            p.setPen(QPen(QColor(BTN_LINE), 1))
            p.setBrush(self._color(cp.PILL_BG, 0.96))
            p.drawEllipse(QRectF(bx, by, r * 2, r * 2))
            pill_below = not self.pet_on_bottom()
            is_open = mode in (cp.DISPLAY_FULL, cp.DISPLAY_SUMMARY)
            point_down = (pill_below and not is_open) or (not pill_below and is_open)
            cx, cy = bx + r, by + r
            wdt, hgt = 5.5, 3.0
            path = QPainterPath()
            if point_down:
                path.moveTo(cx - wdt, cy - hgt / 2); path.lineTo(cx, cy + hgt); path.lineTo(cx + wdt, cy - hgt / 2)
            else:
                path.moveTo(cx - wdt, cy + hgt / 2); path.lineTo(cx, cy - hgt); path.lineTo(cx + wdt, cy + hgt / 2)
            pen = QPen(QColor(cp.TXT_SUB), 2.0)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.end()

    # ── 마우스 ──
    def _on_button(self, pos):
        bx, by = self.btn_origin()
        return QRect(int(bx), int(by), cp.BTN_R * 2, cp.BTN_R * 2).contains(pos)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            # 누를 때 연다(macOS 판 rightMouseDown_ 과 같음). '뗄 때 열기 + activateWindow()' 는 실기기에서 메뉴가
            # 그려져도 항목이 마우스·키보드 어느 쪽으로도 눌리지 않았다(A/B 2026-09-12) — 다시 넣지 말 것.
            self._context_menu(e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton:
            return
        self._down = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._moved = False
        self.state["dragging"] = True

    def mouseMoveEvent(self, e):
        if self._down is None or not (e.buttons() & Qt.LeftButton):
            return
        delta = e.globalPosition().toPoint() - self.frameGeometry().topLeft() - self._down
        if abs(delta.x()) > 1 or abs(delta.y()) > 1:
            self._moved = True
            self.set_override("running-right" if delta.x() > 0 else "running-left", sticky=True)
        self.move(e.globalPosition().toPoint() - self._down)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self.state["dragging"] = False
        self.clear_sticky()
        self._clamp_to_screen()
        moved = self._moved
        if moved:
            # 진짜 드래그만 '수동 배치' 다: 자동 이동이 고정해 둔 배치를 풀고, 논리 full 창의 원점을 저장한다
            # (실제 창이 접힌 부분 사각형이면 원점은 crop 을 뺀 값 — 다음 실행에서 full 창이 같은 자리에 뜬다).
            self.state["roam_layout"] = None
            lx, ly = self.roam_logical_origin()
            self.cfg["x"], self.cfg["y"] = int(round(lx)), int(round(ly))
            cp.merge_config_updates({"x": self.cfg["x"], "y": self.cfg["y"]})
        # Roamer 에 알린다: moved 면 새 집(자연 완료), 아니면 그 자리 정지 (macOS 판 roam_release 훅)
        self.roamer.release(time.monotonic(), self.window_center(), moved)
        if moved:
            self.roam_display.reset()
        self._down = None
        self.update()
        if moved:
            return
        if self.state["hover"] and self._on_button(e.position().toPoint()):
            self.state["show_panel"] = self.roam_display.toggle(self.state["show_panel"])
            self.update()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.set_override("jumping")
            cp._oauth_cache["t"] = 0.0
            self.refresh()

    def _clamp_to_screen(self):
        """논리 full 창 전체가 가장 가까운 화면의 작업 영역 안에 들어가게 한다 (macOS 판 clamp_to_screen)."""
        lx, ly = self.roam_logical_origin()
        w_, h_ = self.roam_env()
        cx, cy = lx + w_ / 2, ly + h_ / 2
        best, best_d = None, None
        for scr in QApplication.screens():
            a = scr.availableGeometry()
            dx = max(a.left() - cx, 0, cx - (a.left() + a.width()))
            dy = max(a.top() - cy, 0, cy - (a.top() + a.height()))
            d = dx * dx + dy * dy
            if best_d is None or d < best_d:
                best, best_d = a, d
        if best is None:
            return
        nx = min(max(lx, best.left()), best.left() + best.width() - w_)
        ny = min(max(ly, best.top()), best.top() + best.height() - h_)
        if abs(nx - lx) > 0.5 or abs(ny - ly) > 0.5:
            ccx, ccy, ccw, cch = self.roam_crop_now()
            self.move(int(round(nx + ccx)), int(round(ny + ccy)))

    # ── 우클릭 메뉴 / 트레이 ──
    def _context_menu(self, gpos):
        """우클릭 메뉴 — macOS 판 rightMouseDown_ 과 같은 항목·순서·상태.

        [Claude 설치/로그인] [Codex 설치/로그인] [업데이트] 설정… · 접기/펴기 · 화면 돌아다니기(✓) · 로그인 시 자동 실행(✓) · 크기 원래대로 · 펫 ▸ · ─ ·
        제거 · 종료 · ─ · ClaudePet vX(비활성) · 업데이트 확인…  (맨 위 세 항목은 해당 상태일 때만, 각각 구분선과 함께)
        """
        self.roam_display.reset()              # macOS 판 roam_interrupt: 요약 래치 해제
        m = QMenu(self)
        top = []
        upd = self.state.get("update")
        if upd:
            top.append((cp.t("menu_update", v=upd[0]), self._do_update))
        # Codex 도 Claude 와 같은 모양(macOS 판 rightMouseDown_ 과 같은 순서) — 맨 위가 Claude,
        # 그 아래 Codex, 그 아래 업데이트. 둘 다 0 번에 끼우므로 Codex 를 먼저 넣는다.
        cob = self.state.get("codex_onboard")
        if cob:
            top.insert(0, (cp.t("menu_install_codex"), self._install_codex) if cob == "install"
                       else (cp.t("menu_login_codex"), self._login_codex))
        ob = self.state.get("onboard")
        if ob:
            top.insert(0, (cp.t("menu_install_cc"), self._install_claude) if ob == "install"
                       else (cp.t("menu_login_cc"), self._login_claude))
        for title, fn in top:
            m.addAction(title, fn)
            m.addSeparator()
        m.addAction(cp.t("menu_settings"), self._open_settings)
        m.addAction(cp.t("menu_toggle"), self._toggle_panel)
        # 체크 항목 셋은 붙여 둔다. menu_autostart 가 menu_roam 과 menu_reset_size 사이라는
        # 것은 AST 로 고정돼 있으니(windows/tests/test_win_autostart.py) 새 항목은 그 쌍
        # 사이가 아니라 앞에 놓는다 — macOS 판 rightMouseDown_ 과 같은 순서.
        credit = QAction(cp.t("menu_credit_money"), m, checkable=True)
        # 체크 = 금액 모드. 진실의 출처는 우리 설정 키다(RUNTIME). 기본값이 money 라
        # "pct 가 아니면 금액" 은 credit_display_mode() 와 같은 뜻이다.
        credit.setChecked(cp.RUNTIME.get("credit_display") != "pct")
        credit.triggered.connect(self._toggle_credit_money)
        m.addAction(credit)
        # 체크 표시는 RUNTIME 에서 온다 — autostart 와 달리 OS 등록 상태가 아니라 우리
        # 설정 키가 진실의 출처다(SETTINGS_OWNED_KEYS 에 있다).
        recover = QAction(cp.t("menu_auto_recover"), m, checkable=True)
        recover.setChecked(bool(cp.RUNTIME.get("auto_recover")))
        recover.triggered.connect(self._toggle_auto_recover)
        m.addAction(recover)
        roam = QAction(cp.t("menu_roam"), m, checkable=True)
        roam.setChecked(bool(cp.RUNTIME.get("roam")))
        roam.setEnabled(not self.state["reduce_motion"])     # 동작 줄이기(애니메이션 끔)면 비활성
        roam.triggered.connect(self._toggle_roam)
        m.addAction(roam)
        # 로그인 시 자동 실행 — macOS 판 rightMouseDown_ 과 같은 자리(화면 돌아다니기 다음, 크기 원래대로 앞), 같은 TR 키.
        # 체크 표시는 설정 파일이 아니라 OS(HKCU Run 값 + Explorer StartupApproved)에서 오고, 메뉴가 열릴 때마다(aboutToShow)
        # 다시 읽는다 — 설정 › 앱 › 시작 앱이나 작업 관리자에서 끈 것도 그대로 보인다(두 화면이 같은 키에 쓴다).
        # 판단은 win_autostart, 여기서는 항목과 알림창만.
        autostart = QAction(cp.t("menu_autostart"), m, checkable=True)
        autostart.triggered.connect(self._toggle_autostart)
        m.addAction(autostart)
        m.aboutToShow.connect(lambda: self._sync_autostart_item(autostart))
        m.addAction(cp.t("menu_reset_size"), self._reset_scale)
        pet_list = cp.discover_pets()          # 우클릭 때마다 다시 스캔 → 새로 넣은 펫 즉시 반영
        if pet_list:
            self.pets = pet_list
            cur_pet = self.cfg.get("pet") or pet_list[0]["id"]
            pets = QMenu(cp.t("menu_pets"), m)
            for pinfo in pet_list:
                a = QAction(pinfo["name"], pets, checkable=True)
                a.setChecked(pinfo["id"] == cur_pet)
                a.triggered.connect(lambda checked=False, pid=pinfo["id"]: self._set_pet(pid))
                pets.addAction(a)
            pets.addSeparator()
            pets.addAction(cp.t("pet_add"), self._add_pet)
            m.addMenu(pets)
        m.addSeparator()
        m.addAction(cp.t("menu_uninstall"), self._uninstall)
        m.addAction(cp.t("menu_quit"), QApplication.instance().quit)
        m.addSeparator()
        v = m.addAction(f"ClaudePet v{cp.APP_VERSION}")
        v.setEnabled(False)
        m.addAction(cp.t("menu_check_update"), self._check_update)
        # 메뉴는 동기 루프라 그동안 틱이 멈춘다. 자동 이동은 막고, 닫힌 뒤 첫 틱이 '그 자리 정지' 로 처리하게 표시를 남긴다.
        self.state["menu_open"] = True
        try:
            m.exec(gpos)
        finally:
            self.state["menu_open"] = False
            self.state["roam_hold"] = True

    def _toggle_panel(self):
        """기존 펼치기 조작(메뉴 '접기/펴기'): 요약 중이면 요약↔전체, 아니면 평소 선택 반전 (RoamDisplay.toggle)."""
        self.state["show_panel"] = self.roam_display.toggle(self.state["show_panel"])
        self.update()

    def _toggle_roam(self):
        """우클릭 체크 항목. 끄면 다음 틱에 그 자리에서 선다(집으로 되돌리지 않는다). 설정 키 roam 만 저장."""
        value = not cp.RUNTIME.get("roam")
        cp.RUNTIME["roam"] = value
        ok, merged = cp.merge_config_updates({"roam": value})
        if ok:
            self.cfg.clear()
            self.cfg.update(merged)
        else:
            self.cfg["roam"] = value

    # ── 토큰 자동 복구 (판단: cp.recovery_tick / 실행: 여기 — macOS 판 _recovery_step 과 같은 계약) ──
    def _recovery_step(self, force=False):
        """새로고침 워커가 매 주기 부르는 자리. 판단은 cp.recovery_tick 이, 실행만 여기서.

        force 는 사용자가 만료 문구를 직접 눌렀을 때다 — 포기한 사이클을 다시 열고 한 번 더
        띄운다. 자동 경로가 포기하는 것과 사용자가 다시 시도하는 것은 다른 일이다.

        스폰의 윈도우 분기는 코어가 이미 갖고 있다: `cmd.exe /c claude -p /usage` 를
        WMI(Win32_Process.Create)가 띄워 부모가 WmiPrvSE.exe 가 되므로 CLI 가 우리 자손으로
        뜨지 않고, 터미널 창도 없다(cp.recovery_spawn_argv / cp._run_refresh_job).
        """
        try:
            have_oauth, expires_at, token_sig = cp.oauth_token_facts()
            if force:
                self.state["recovery"] = dict(self.state["recovery"],
                                              attempts=0, gave_up=False, first_at=None,
                                              last_spawn=None, login_expired=False)
            rec, action = cp.recovery_tick(
                self.state["recovery"], datetime.now(timezone.utc),
                auth_error=bool(cp.OAUTH_STATUS.get("auth_error")),
                token_sig=token_sig,
                cli_present=bool(cp._find_claude_cli()),
                enabled=bool(cp.RUNTIME.get("auto_recover")) or force,
                creds_have_oauth=have_oauth,
                expires_at=expires_at)
            self.state["recovery"] = rec
            cp._dbg("recovery: action", action, "attempts", rec["attempts"])
            if action == "spawn":
                cp.run_token_refresh(self.state)
            return action
        except Exception as e:
            cp._dbg("recovery: step failed", type(e).__name__)
            return None

    def _toggle_credit_money(self):
        """크레딧 행을 금액($100.66)으로 볼지 %로 볼지. macOS 판 toggleCreditMoney_ 과 같은 계약.

        선택은 ~/.claude_pet.json 에 남는다 — 바꿨는데 다음 실행에 돌아가 있으면 바꾼 게 아니다.

        필 문자열을 여기서 바로 다시 만든다. 평소에는 새로고침 워커가 만들지만 그 주기는
        30초라 누르고 나서 한참 그대로처럼 보인다. credit_text 는 요약 memo 키에 들어 있으므로
        다음 tick 에 바로 다시 그려진다.
        """
        value = cp.credit_display_next(cp.RUNTIME.get("credit_display"))
        cp.RUNTIME["credit_display"] = value
        if cp.OAUTH_EXTRA["credit"]:
            self.state["credit_text"] = cp.credit_row_text(cp.OAUTH_EXTRA["credit"], value)
        ok, merged = cp.merge_config_updates({"credit_display": value})
        if ok:
            self.cfg.clear()
            self.cfg.update(merged)
        else:
            self.cfg["credit_display"] = value

    def _toggle_auto_recover(self):
        """토큰 자동 갱신·복구 켜기/끄기. macOS 판 toggleAutoRecover_ 과 같은 계약.

        선택은 ~/.claude_pet.json 에 남는다 — 껐는데 다음 실행에 다시 켜져 있으면 끈 게 아니다.
        """
        value = not cp.RUNTIME.get("auto_recover")
        cp.RUNTIME["auto_recover"] = value
        ok, merged = cp.merge_config_updates({"auto_recover": value})
        if ok:
            self.cfg.clear()
            self.cfg.update(merged)
        else:
            self.cfg["auto_recover"] = value

    # ── 로그인 시 자동 실행 (판단: win_autostart / 실행: 여기 — macOS 판 toggleAutostart_ 와 같은 계약, 설정 키 없음) ──
    def _autostart_args(self):
        """(reader, writer, exe, is_frozen) — 메뉴와 클릭이 같은 규칙으로 레지스트리와 신원을 고른다 (macOS 판 autostart_current).
        소스 실행(pythonw)은 is_frozen 이 False 라 순수 함수가 레지스트리를 건드리지 않고 "unavailable" 을 돌려준다."""
        reader, writer = wa.real_registry()
        return reader, writer, app_exe_path(), is_frozen()

    def _sync_autostart_item(self, action):
        """메뉴가 열릴 때마다 OS 에서 다시 읽어 체크·활성·제목을 맞춘다. 설정 파일에는 아무것도 없다."""
        reader, _writer, exe, frozen = self._autostart_args()
        state = wa.autostart_read_state(reader, exe, frozen)
        if state == "unavailable":
            action.setText(cp.t("autostart_unavailable"))     # 소스 실행, 또는 레지스트리를 읽을 수 없음
            action.setChecked(False)
            action.setEnabled(False)
            return
        action.setText(cp.t("menu_autostart"))
        action.setChecked(state == "on")
        action.setEnabled(True)

    def _toggle_autostart(self):
        """우클릭 체크 항목 한 번. 결과는 알릴 뿐 어디에도 저장하지 않는다 — 다음에 메뉴를 열면 OS 에서 다시 읽는다."""
        reader, writer, exe, frozen = self._autostart_args()
        new_state, err = wa.autostart_toggle(reader, writer, exe, frozen)
        wu.log_update("startup", status=new_state, error=err or "none")
        if err:
            box = self._msgbox(QMessageBox.Critical, cp.t("autostart_title"), cp.t("autostart_fail"))
            box.addButton(QMessageBox.Ok)
            box.exec()

    def _set_pet(self, pet_id):
        pinfo = next((x for x in self.pets if x["id"] == pet_id), None)
        if not pinfo:
            return
        nf = load_pet_frames(pinfo["dir"])
        if nf is None:
            return
        self.frames = nf
        first = nf["idle"][0]
        self.PW0 = max(1, int(first.width() // cp.PET_SCALE_DOWN))
        self.PH0 = max(1, int(first.height() // cp.PET_SCALE_DOWN))
        self.state["relayout"] = True
        self.cfg["pet"] = pet_id
        cp.merge_config_updates({"pet": pet_id})
        self.update()

    # ── 크기 (macOS 판 scrollWheel_ / set_scale) ──
    def wheelEvent(self, e):
        d = e.pixelDelta().y() if not e.pixelDelta().isNull() else e.angleDelta().y() / 120.0 * 10.0
        self.set_scale(self.scale + d * 0.004)

    def set_scale(self, value):
        new = max(0.3, min(2.0, value))
        if abs(new - self.scale) < 1e-4:
            return
        self.scale = new
        self._relayout()                       # 논리 full 창 기준으로 geom 을 다시 잡는다 (macOS 판과 같음)
        self.cfg["scale"] = round(new, 3)
        cp.merge_config_updates({"scale": self.cfg["scale"]})   # 이 경로가 가진 키만
        self.update()

    def _reset_scale(self):
        self.set_scale(0.5)

    # ── 메뉴 동작 (macOS 판 Handler 와 같은 이름 순서) ──
    def _add_pet(self):
        try:
            os.makedirs(cp.USER_PETS_DIR, exist_ok=True)
            cp._write_pets_readme(cp.USER_PETS_DIR)   # 포맷 안내 + 예시 pet.json (없을 때만)
        except Exception:
            pass
        os.startfile(cp.USER_PETS_DIR)

    def _run_in_console(self, lines):
        """새 PowerShell 창에서 실행 — macOS 판 _run_in_terminal(Terminal.app) 의 Windows 판."""
        script = "; ".join(lines)
        subprocess.Popen(["powershell", "-NoExit", "-Command", script],
                         creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))

    @staticmethod
    def _ps_echo(s):
        return "Write-Host '" + str(s).replace("'", "''") + "'"

    def _install_claude(self):
        """Claude Code 설치 → 이어서 로그인까지 새 콘솔에서 (macOS 판 start_claude_install)."""
        self._run_in_console([self._ps_echo(cp.t("term_installing")),
                              f"irm {CLAUDE_INSTALL_URL_WIN} | iex",
                              "Write-Host ''", self._ps_echo(cp.t("term_login")),
                              '& "$env:USERPROFILE\\.local\\bin\\claude.exe" auth login',
                              "Write-Host ''", self._ps_echo(cp.t("term_done"))])

    def _login_claude(self):
        binp = (shutil.which("claude") or shutil.which("claude.exe")
                or os.path.expanduser("~/.local/bin/claude.exe"))
        self._run_in_console([self._ps_echo(cp.t("term_login")),
                              "& '" + binp.replace("'", "''") + "' auth login",
                              "Write-Host ''", self._ps_echo(cp.t("term_done"))])

    def _install_codex(self):
        """Codex 설치(npm) → 이어서 로그인까지 새 콘솔에서 (macOS 판 start_codex_install).

        npm 과 codex 는 cmd 로 부른다: PowerShell 에서 이름만 쓰면 npm.ps1/codex.ps1 이 먼저 잡히고,
        Windows 클라이언트의 기본 실행 정책(Restricted)이 그 스크립트를 막는다. 설치 직후에는 이
        콘솔의 PATH 에 npm 전역 폴더가 없을 수 있어 앞에 붙인다.
        """
        need = self._ps_echo(cp.t("term_need_npm"))
        self._run_in_console([self._ps_echo(cp.t("term_installing_codex")),
                              "if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { "
                              + need + " }",
                              'cmd /c "npm install -g @openai/codex"',
                              "Write-Host ''", self._ps_echo(cp.t("term_login")),
                              '$env:Path = "$env:APPDATA\\npm;" + $env:Path',
                              'cmd /c "codex login"',
                              "Write-Host ''", self._ps_echo(cp.t("term_done"))])

    def _login_codex(self):
        """설치돼 있으나 로그인만 필요한 경우 (macOS 판 start_codex_login). 찾은 CLI 의 폴더를 PATH 앞에."""
        binp = find_codex_cli()
        lines = [self._ps_echo(cp.t("term_login"))]
        if binp:
            lines.append("$env:Path = '" + os.path.dirname(binp).replace("'", "''") + ";' + $env:Path")
        lines += ['cmd /c "codex login"', "Write-Host ''", self._ps_echo(cp.t("term_done"))]
        self._run_in_console(lines)

    # ── 완전 삭제 (macOS 판 uninstallApp_ / do_uninstall 과 같은 순서: 거절할 수 있는 단계가 먼저) ──
    def _uninstall(self):
        """제거 — macOS 판과 같은 확인 창(취소가 기본 버튼). 설치 종류별로:
          source   설정·잠금·디버그 로그·캐시 폴더만 (macOS 판 개발 모드와 같은 unin_devmode 안내)
          inno     위 파일들 + HKCU Run 값(우리 exe 일 때만) 을 지우고, 종료 뒤 unins000.exe /SILENT 를 부르는 헬퍼 → 종료.
                   제거 프로그램이 프로그램·바로가기·등록 항목을 지운다. 살아 있는 펫 위에서 돌리면 파일이 "사용 중" 으로
                   남으므로 헬퍼가 pid 를 기다린다(실기 2026-09-14).
          portable 위 파일들을 지우고, 종료 뒤 앱 폴더를 지우는 PowerShell 헬퍼 → 종료.
        %USERPROFILE%\\.claude_pet(펫) 은 어느 경우에도 남긴다."""
        why = wu.uninstall_refusal(self.state)        # 설치 파일이 이 앱을 닫길 기다리는 중 — 확인 창을 띄울 것도 없다
        if why:
            wu.log_update("uninstall", status="refused", reason=why)
            self._info(cp.t("unin_title"), tw("unin_busy"))
            return
        kind = install_kind_now()
        exe = app_exe_path()
        exe_dir = os.path.dirname(exe) if exe else None
        home = os.path.expanduser("~")
        if kind == "source":
            plan = [("delete", p) for p in UNINSTALL_PATHS_WIN] + [("delete", wu.cache_dir())]
        else:
            plan = wu.uninstall_plan(kind, exe_dir, home)
        items = [a for op, a in plan if op == "delete" and os.path.lexists(a)]
        if kind != "source":
            items.insert(0, exe_dir)
        shown = "\n".join("  • " + (p.replace(home, "~", 1) if p.startswith(home) else p) for p in items) \
            or "  • (없음 / none)"
        box = self._msgbox(QMessageBox.Critical, cp.t("unin_title"), cp.t("unin_body", items=shown))
        cancel = box.addButton(cp.t("unin_cancel"), QMessageBox.RejectRole)
        ok = box.addButton(cp.t("unin_ok"), QMessageBox.DestructiveRole)
        box.setDefaultButton(cancel)
        box.exec()
        if box.clickedButton() is not ok:
            return
        # 진행 중인 업데이트가 있으면 지우지 않고 물러난다 (macOS 판 do_uninstall). 두 겹이다: inno 설치 파일이 도는 동안은
        # state["installing"] 표시(설치 파일은 잠금 핸들을 물려받지 않는다 — win_update.uninstall_refusal), portable 헬퍼가 도는
        # 동안은 헬퍼가 물려받은 공유 모드 없는 잠금 핸들.
        why = wu.uninstall_refusal(self.state)
        if why:
            wu.log_update("uninstall", status="refused", reason=why)
            self._info(cp.t("unin_title"), tw("unin_busy"))
            return
        lock = None
        if _WIN32:
            lock = open_update_lock(wu.lock_path())
            if lock is None:
                wu.log_update("uninstall", status="refused", reason="lock-busy")
                self._info(cp.t("unin_title"), tw("unin_busy"))
                return
        err = None
        try:
            # 1. 거절할 수 있는 단계: 제거 프로그램/헬퍼를 먼저 띄운다. Popen 이 실패하면 아직 아무것도 지우지 않았다.
            if kind == "inno":
                # unins000.exe 를 지금 바로 띄우면 펫이 살아 있는 채로 제거가 돌아, ARP 항목과 Run 값은 지워지고
                # ClaudePet.exe·_internal\ 은 "사용 중" 으로 남는다(실기 H20). portable 과 같은 모양으로 — 우리 pid 가
                # 끝난 뒤에 제거 프로그램을 부르는 PowerShell 헬퍼에 맡긴다. 설정에서 시작한 제거는 installer.iss 의
                # [UninstallRun] taskkill 이 막는다.
                argv = plan[-1][1]
                if not os.path.isfile(argv[0]):
                    self._info(cp.t("unin_title"), cp.t("unin_fail"))
                    return
                script = os.path.join(os.environ.get("TEMP") or home,
                                      f"claudepet-uninstall-inno-{os.getpid()}.ps1")
                try:
                    with open(script, "w", encoding="utf-8-sig") as f:
                        f.write(wu.build_inno_uninstall_script(argv, os.getpid()))
                    popen_detached([powershell_exe(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                    "-File", script])
                except Exception as e:
                    wu.log_update("uninstall", kind=kind, status="failed", at="run-uninstaller", error=type(e).__name__)
                    self._info(cp.t("unin_title"), cp.t("unin_fail"))
                    return
            elif kind == "portable":
                script = os.path.join(os.environ.get("TEMP") or home, f"claudepet-uninstall-{os.getpid()}.ps1")
                try:
                    with open(script, "w", encoding="utf-8-sig") as f:
                        f.write(wu.build_uninstall_script(exe_dir, os.getpid()))
                    popen_detached([powershell_exe(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                    "-File", script])
                except Exception as e:
                    wu.log_update("uninstall", kind=kind, status="failed", at="run-helper", error=type(e).__name__)
                    self._info(cp.t("unin_title"), cp.t("unin_fail"))
                    return
            # 2. 되돌릴 수 없는 구간: 사용자 파일 → Run 값 → 캐시 폴더(잠금은 닫은 뒤; DELETE_ON_CLOSE 라 파일은 사라진다)
            delete_run_value_if_ours(exe)
            cache = wu.cache_dir()
            deleted = 0
            for op, p in plan:
                if op != "delete" or p == cache:
                    continue
                if not os.path.lexists(p):
                    continue
                try:
                    if os.path.isdir(p) and not os.path.islink(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
                    deleted += 1
                except Exception as e:
                    err = e
            wu.log_update("uninstall", kind=kind, deleted=deleted, error=(type(err).__name__ if err else "none"))
            close_handle(lock)
            lock = None
            shutil.rmtree(cache, ignore_errors=True)
        finally:
            close_handle(lock)
        if kind == "source":
            self._info(cp.t("unin_title"), cp.t("unin_fail") if err else cp.t("unin_devmode"))
            return
        QApplication.instance().quit()

    # ── 업데이트 (판단: win_update / 실행: 여기) ──
    def _run_update_check(self):
        """새 버전 확인 1회, 한 번에 하나만 → 'update' | 'current' | 'failed' | None(이미 확인 중).

        macOS 판 poll_github_update 의 규칙을 이유별로 나눈다(win_update.stamps_cooldown): 새 버전·최신, 그리고 이 릴리즈·이
        기기의 성질인 거절(no-asset, unknown-machine, bad-url …)은 재확인 쿨다운(_upd_cache["t"])을 찍어 한 시간 뒤에 다시 묻고,
        일시적 실패(fetch-failed:*, bad-payload)만 찍지 않아 다음 새로고침(30초)에 다시 묻는다. 예전에는 모든 error 가 쿨다운을
        건너뛰어 ARM64 기기가 30초마다 api.github.com 을 불렀다(시간당 120회 — 비인증 한도 60회). 새 버전일 때만
        state["update"] = (버전, url) 과 _upd_cache["choice"] 를 채운다. 소스 실행은 확인하지 않는다(자산이 소용없다).
        """
        if cp._upd_cache.get("busy"):
            return None
        cp._upd_cache["busy"] = True
        try:
            kind = install_kind_now()
            if kind == "source":
                cp._upd_cache["t"] = time.time()
                cp._upd_cache["choice"] = None
                self.state["update_reason"] = "source"
                return "current"
            got = wu.check_github_update_win(wu.fetch_json_default, platform.machine(), kind, cp.APP_VERSION)
            status = got[0]
            stamped = wu.stamps_cooldown(got)
            if stamped:
                cp._upd_cache["t"] = time.time()
            if status == "error":
                cp._upd_cache["choice"] = None
                self.state["update_reason"] = got[1]
                wu.log_update("check", status="error", reason=got[1], cooldown=int(stamped))
                return "failed"
            if status == "update":
                choice = got[2]
                cp._upd_cache["choice"] = choice
                self.state["update"] = (choice["tag"], choice["url"])
                self.state["update_reason"] = None
                wu.log_update("check", status="update", tag=choice["tag"], kind=kind, machine=platform.machine())
            else:
                cp._upd_cache["choice"] = None
                self.state["update_reason"] = None
            return status
        finally:
            cp._upd_cache["busy"] = False

    def _check_update(self):
        """우클릭 '업데이트 확인…': 지금 확인 → 새 버전이 있으면 바로 설치한다 (macOS 판 checkUpdate_). 결과는 알림 한 번."""
        def work():
            status = self._run_update_check()
            if status == "update":
                if self._install_update():
                    return                       # 설치가 시작됐다 — 알림/종료는 _install_update 가 보낸다
                msg = cp.t("upd_install_failed")
            elif status == "current":
                msg = tw("upd_source") if self.state.get("update_reason") == "source" \
                    else cp.t("upd_current", v=cp.APP_VERSION)
            elif status is None:
                msg = cp.t("upd_busy")
            elif self.state.get("update_reason") == "no-asset":
                msg = tw("upd_no_asset", m=platform.machine())
            else:
                msg = cp.t("upd_failed")
            self.update_msg.emit(msg)
        threading.Thread(target=work, daemon=True).start()

    def _do_update(self):
        """우클릭 '새 버전 vX 설치' (매시간 확인이 찾아 둔 것)."""
        def work():
            if not self._install_update():
                self.update_msg.emit(cp.t("upd_install_failed"))
        threading.Thread(target=work, daemon=True).start()

    def _install_update(self):
        """_upd_cache["choice"] 의 자산을 받아 설치한다 → True 면 설치가 시작됐다(inno: 설치 파일이 이 앱을 닫고 다시 띄운다,
        portable: 교체 헬퍼가 떠 있고 이 앱은 곧 끝난다). False 면 아무것도 바뀌지 않았다.

        순서 — 거절할 수 있는 단계가 전부 되돌릴 수 없는 단계 앞에 온다: 잠금 → 내려받기 → 크기·sha256 → (portable) 멤버 검사 →
        옆 폴더에 풀기 → 레이아웃·버전 마커 → 헬퍼/설치 파일 띄우기 → (portable) 종료. 잠금 핸들은 헬퍼에 물려주고 우리 쪽 사본은
        닫는다(macOS 판 pass_fds 와 같은 규율). 로그에는 개수·상태만 남긴다.
        """
        choice = cp._upd_cache.get("choice") or {}
        kind, tag = choice.get("kind"), choice.get("tag")
        exe = app_exe_path()
        if not exe or kind not in wu.INSTALL_KINDS or not tag or not choice.get("url"):
            return False
        if self.state.get("installing"):
            wu.log_update("install", status="refused", reason="installing")
            return False                          # 설치 파일이 이미 돌고 있다(이 앱이 닫히길 기다리는 중) — 두 번 띄우지 않는다
        if kind != install_kind_now():
            wu.log_update("install", status="refused", reason="kind-changed")
            return False
        cache = wu.cache_dir()
        # portable: 이름 셋을 내려받기 전에 정하고 미리 거절한다. .claudepet-old-v<버전> 이 이미 있으면(지난 거래가 반쯤 지운 옛
        # 폴더 — exe·마커가 없어 clean_update_leftovers 가 건드리지 않는다) 헬퍼의 Rename-Item 이 첫 단계에서 실패할 것이고,
        # 그 답은 사용자가 그 폴더를 지우기 전에는 바뀌지 않으니 수십 MB 를 받을 이유가 없다 (win_update.swap_refusal).
        app_dir = parent = token = stage = new_dir = old_dir = None
        if kind == "portable":
            app_dir = os.path.dirname(exe)
            parent = os.path.dirname(app_dir)
            token = f"{os.getpid()}-{os.urandom(4).hex()}"
            stage = os.path.join(parent, wu.STAGE_PREFIX + token)
            new_dir, old_dir = wu.swap_names(parent, cp.APP_VERSION, token)
            why = wu.swap_refusal(app_dir, new_dir, old_dir)
            if why:
                wu.log_update("install", tag=tag, kind=kind, status="refused", reason=why)
                return False
        lock = open_update_lock(wu.lock_path())
        if lock is None:
            wu.log_update("install", status="refused", reason="lock-busy")
            return False
        dest = os.path.join(cache, choice["asset"])
        staged = False                            # stage 폴더가 만들어졌고 아직 치우지 않았다
        try:
            try:
                total = cp._download_update_zip(choice["url"], dest)
            except Exception as e:
                wu.log_update("download", tag=tag, status="failed", error=type(e).__name__)
                return False
            wu.log_update("download", tag=tag, kind=kind, bytes=total, status="ok")
            if not wu.verify_download(dest, choice.get("size"), choice.get("digest")):
                wu.log_update("verify", tag=tag, status="refused", reason="size-or-digest")
                return False
            wu.log_update("verify", tag=tag, status="ok")
            if kind == "inno":
                argv = wu.inno_silent_args(dest, os.path.join(cache, wu.INNO_LOG_NAME))
                try:
                    proc = popen_detached(argv)
                except Exception as e:
                    wu.log_update("install", tag=tag, kind=kind, status="failed", error=type(e).__name__)
                    return False
                wu.log_update("install", tag=tag, kind=kind, status="launched")
                # 여기서 끝내지 않는다: 설치 파일의 Restart Manager 가 이 앱을 닫고(등록돼 있으므로) 다시 띄운다. 그동안 잠금 핸들은
                # 아래 finally 에서 닫히고 설치 파일은 물려받지 않으므로, 두 번째 업데이트와 완전 삭제를 막는 것은 이 표시다
                # (win_update.uninstall_refusal). 설치 파일이 이 앱을 닫지 않고 끝나면 _reap_installer 가 표시를 지운다.
                self._installer = proc
                self.state["installing"] = True
                self.notify.emit(tw("upd_installing", v=tag))
                return True
            # portable
            if not wu.scan_update_zip(dest):
                wu.log_update("scan", tag=tag, status="refused")
                return False
            try:
                os.mkdir(stage)                       # 부모가 쓰기 불가(예: Program Files)면 여기서 거절된다
                staged = True
                with zipfile.ZipFile(dest) as z:
                    z.extractall(stage)
            except Exception as e:
                wu.log_update("extract", tag=tag, status="failed", error=type(e).__name__)
                return False
            ok, reason = wu.validate_portable_layout(stage, tag)
            if not ok:
                wu.log_update("layout", tag=tag, status="refused", reason=reason.replace(" ", "-"))
                return False
            why = wu.swap_refusal(app_dir, new_dir, old_dir)      # 내려받는 사이에 생겼을 수 있다 — 같은 물음, 같은 거절
            if why:
                wu.log_update("install", tag=tag, kind=kind, status="refused", reason=why)
                return False
            try:
                os.rename(os.path.join(stage, wu.APP_DIR_NAME), new_dir)   # 대상이 있으면 FileExistsError — 덮어쓰지 않는다
                os.rmdir(stage)
                staged = False
            except Exception as e:
                wu.log_update("stage", tag=tag, status="failed", error=type(e).__name__)
                return False
            script = os.path.join(cache, f"swap-{token}.ps1")
            try:
                with open(script, "w", encoding="utf-8-sig") as f:       # BOM: PowerShell 5.1 이 UTF-8 로 읽게
                    f.write(wu.build_swap_script(app_dir, new_dir, old_dir, exe, os.getpid(),
                                                 log_path=wu.update_log_path()))
                popen_detached([powershell_exe(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                "-File", script], inherit=[lock])
            except Exception as e:
                wu.log_update("swap", tag=tag, status="failed", error=type(e).__name__)
                shutil.rmtree(new_dir, ignore_errors=True)
                return False
            wu.log_update("swap", tag=tag, kind=kind, status="launched")
            self.quit_app.emit()
            return True
        finally:
            if staged:
                shutil.rmtree(stage, ignore_errors=True)
            close_handle(lock)

    def _reap_installer(self):
        """inno 설치 파일이 이 앱을 닫지 않은 채 끝났으면(거절·취소·실패) installing 표시를 지운다 — 표시가 남으면 업데이트도
        완전 삭제도 이 앱이 다시 뜰 때까지 물러난다. 새로고침 워커가 30초마다 부른다. 정상 경로에서는 설치 파일이 이 앱을 먼저
        닫으므로 여기 오지 않는다."""
        proc = self._installer
        if proc is None:
            return
        rc = proc.poll()
        if rc is None:
            return
        self._installer = None
        self.state["installing"] = False
        wu.log_update("install", kind="inno", status="exited", rc=rc)

    def _show_update_message(self, msg):
        box = self._msgbox(QMessageBox.Information, cp.t("upd_title"), msg)
        box.addButton(QMessageBox.Ok)
        box.exec()

    def _info(self, title, msg):
        box = self._msgbox(QMessageBox.Information, title, msg)
        box.addButton(QMessageBox.Ok)
        box.exec()

    def _show_notify(self, msg):
        """비모달 알림 — 트레이 풍선. 트레이가 없으면 조용히 넘어간다(모달 창은 설치 파일의 종료 요청을 막는다)."""
        tray = self.tray
        if tray is not None:
            try:
                tray.showMessage(cp.t("upd_title"), msg, app_icon(), 8000)
            except Exception:
                pass

    # ── 설정 창 (macOS 판 open_settings / save_settings 와 같은 좌표·계약) ──
    def _open_settings(self):
        self.roam_display.reset()              # 설정 창은 명시적 중단: 요약 래치 해제
        if self.ui.get("panel"):
            self.ui["panel"].raise_()
            self.ui["panel"].activateWindow()
            return
        dlg = SettingsDialog(self)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def close_main_panel(self):
        """설정 창을 닫는 유일한 경로(저장 성공, X 버튼) — macOS 판 close_main_panel. 창과 참조는 같이 죽는다."""
        p = self.ui.get("panel")
        if p:
            p.blockSignals(True)
            p.hide()
            p.deleteLater()
        self.ui["panel"] = None        # 다음에 열 때 새 언어로 재구성

    def closeEvent(self, e):
        """창 닫기 요청(WM_CLOSE) 은 곧 앱 종료다. 트레이의 보이기/숨기기는 setVisible 이라 여기를 거치지 않는다.

        설치 파일의 Restart Manager(/CLOSEAPPLICATIONS) 는 이 프로세스의 최상위 창에 WM_CLOSE 를 보내 앱을 닫는다. 그냥 숨기기만
        하면 RM 은 앱이 안 닫혔다고 보고 강제 종료(/FORCECLOSEAPPLICATIONS)로 넘어간다 — 그래도 설정 파일은 os.replace 로 쓰므로
        찢어지지 않지만, 곱게 끝나는 쪽이 낫다. 모달 알림 창이 떠 있으면 먼저 닫아야 quit 이 먹는다(중첩 루프)."""
        if not self._closing:
            self._closing = True
            app = QApplication.instance()
            for w in app.topLevelWidgets():
                if w is not self and w.isVisible():
                    w.close()
            app.quit()
        e.accept()

    def _msgbox(self, icon, title, text, parent=None):
        """항상 위에 뜨는 알림 창 — 펫 창(항상 위) 아래에 숨지 않게 (macOS 판 NSAlert 는 모달로 앞에 온다)."""
        box = QMessageBox(icon, title, str(text), QMessageBox.NoButton, parent)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.setWindowIcon(app_icon())
        return box

    def settings_error(self, msg):
        box = self._msgbox(QMessageBox.Warning, cp.t("s_err_title"), msg, self.ui.get("panel"))
        box.addButton(QMessageBox.Ok)
        box.exec()

    def save_settings(self):
        """설정 저장 — macOS 판 save_settings 와 같은 폼·같은 트랜잭션. 검증 → 파일 기록이 모두
        성공한 뒤에야 반영하고, 실패하면 창은 열린 채 아무것도 바뀌지 않는다. 로그는 읽지 않는다 —
        역산할 한도가 없다."""
        ui = self.ui
        pet_ids = ui.get("pet_ids") or []
        sel_pet = pet_ids[ui["pet"].currentIndex()] if pet_ids else None
        prev_pet = self.cfg.get("pet") or (pet_ids[0] if pet_ids else None)
        form = {
            "pet": sel_pet,
            "lang": cp.SUPPORTED_LANGS[ui["lang"].currentIndex()],
            "mode": "api" if ui["mode"].currentIndex() == 1 else "sub",
            "api_budget": ui["bud"].text(),
            "spike_mult": [0.5, 1.0, 2.0][ui["sens"].currentIndex()],
            "greet": bool(ui["greet"].isChecked()),
            "admin_key": ui["key"].text().strip(),
            "show_claude": bool(ui["show_claude"].isChecked()),
            "claude_gauges": [g for g, b in ui["claude_g"].items() if b.isChecked()],
            "show_codex": bool(ui["show_codex"].isChecked()),
            "codex_mode": "api" if ui["codex_mode"].currentIndex() == 1 else "sub",
            "codex_gauges": [g for g, b in ui["codex_g"].items() if b.isChecked()],
            "openai_admin_key": ui["okey"].text().strip(),
            "codex_budget": ui["cbud"].text(),
        }
        plan, err = cp.plan_settings_save(self.cfg, form)
        if err:
            self.settings_error(err)
            return
        prev_settings = cp.settings_snapshot()
        ok, _merged = cp.apply_settings_plan(plan, self.cfg, apply_fn=cp.apply_config,
                                             set_pet_fn=self._set_pet, prev_pet=prev_pet)
        if not ok:
            self.settings_error(cp.t("s_err_save"))
            return
        # 세대를 올려, 저장 전에(옛 설정으로) 시작된 새로고침이 뒤늦게 덮어쓰지 못하게 한다.
        # 예: Codex 를 API 모드로 바꿨는데 옛 패스가 비용 없이 끝나 '조회 중'이 눌러앉는 일.
        with self._refresh_lock:
            self._refresh_gen += 1
            self._pending = None
        self.state["repaint"] = True
        # 다시 조회해야 하는 바뀜일 때만 캐시를 비운다(macOS 판과 같은 cp.settings_cache_resets).
        reset_oauth, reset_codex = cp.settings_cache_resets(prev_settings, cp.settings_snapshot())
        if reset_oauth:
            cp._oauth_cache["t"] = 0.0
        if reset_codex:
            cp._codex_cache["t"] = 0.0
        self.close_main_panel()
        self.refresh()
        self.update()


class SettingsDialog(QDialog):
    """macOS 판 open_settings 의 NSPanel(420×568) 을 같은 좌표로 옮긴 것.

    AppKit 은 y 가 아래에서 위로, Qt 는 위에서 아래로 커지므로 위젯의 위쪽 = PHT − y − h 로 뒤집는다.
    라벨·입력·팝업·체크·버튼의 x/폭/높이와 y 간격은 macOS 판과 같다. 펫·언어, Claude Code 구역,
    Codex 구역(같은 모양), 공통(급증 민감도·인사), 저장·버전 순서이고 높이 예산 ≤ 656 도 그대로다
    (CLAUDE.md Danger zone). 보정·한도·고급 창은 2026-10-05 에 없어졌다.
    """
    PWID, PHT = 420, 568

    def __init__(self, win):
        super().__init__(None, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.win = win
        t, R, cfg = cp.t, cp.RUNTIME, win.cfg
        self.setWindowTitle(t("settings_title"))
        self.setWindowIcon(app_icon())
        self.setFixedSize(self.PWID, self.PHT)

        def label(text, x, y, w=150, h=20):
            l = QLabel(text, self)
            l.setGeometry(x, self.PHT - y - h, w, h)
            return l

        def field(x, y, w, value, secure=False):
            f = QLineEdit(str(value), self)
            f.setGeometry(x, self.PHT - y - 22, w, 22)
            if secure:
                f.setEchoMode(QLineEdit.Password)
            return f

        def check(title, x, y, w, on):
            b = QCheckBox(title, self)
            b.setGeometry(x, self.PHT - y - 22, w, 22)
            b.setChecked(bool(on))
            return b

        def popup(x, y, w, items, index):
            # macOS 판 popup 처럼 y 는 라벨 기준선이고 팝업은 3pt 아래에서 26pt 높이다.
            c = QComboBox(self)
            c.setGeometry(x, self.PHT - (y - 3) - 26, w, 26)
            c.addItems(list(items))
            if items:
                c.setCurrentIndex(max(0, min(index, len(items) - 1)))
            return c

        def section(title, show_key, y):
            """구역 제목(굵게)과 같은 줄 오른쪽의 '필에 표시' 체크 (macOS 판 section).

            macOS 는 boldSystemFontOfSize_(13) — 굵기만 다르고 크기는 보통 라벨(13pt)과 같다.
            그래서 여기서도 굵게만 하고 크기는 label() 의 기본 글꼴 그대로 둔다(크기를 정하면
            Qt 기본보다 커져 제목만 도드라졌다 — Windows 실기 2026-10-05)."""
            head = label(title, 20, y, 150)
            f = head.font()
            f.setBold(True)
            head.setFont(f)
            return check(t("s_show_in_pill"), 180, y, 220, R.get(show_key, True))

        y = self.PHT - 40
        label(t("s_pet"), 20, y)
        pet_list_s = cp.discover_pets()
        pet_ids = [p["id"] for p in pet_list_s]
        cur_pet = cfg.get("pet") or (pet_ids[0] if pet_ids else None)
        pet_pop = popup(180, y, 220, [p["name"] for p in pet_list_s],
                        pet_ids.index(cur_pet) if cur_pet in pet_ids else 0)

        y -= 34
        label(t("s_language"), 20, y)
        lang_pop = popup(180, y, 160, [cp.LANG_NAMES[c] for c in cp.SUPPORTED_LANGS],
                         cp.SUPPORTED_LANGS.index(cp.L["lang"]))

        gauge_title = {"session": t("s_gauge_session"), "weekly": t("s_gauge_weekly"),
                       "model": t("s_gauge_model"), "credit": t("s_gauge_credit")}

        # ── Claude Code 구역 ──
        y -= 42
        show_claude = section(t("s_sec_claude"), "show_claude", y)
        y -= 30
        label(t("s_data_source"), 20, y)
        mode = popup(180, y, 220, [t("s_mode_sub"), t("s_mode_api")], 1 if R["mode"] == "api" else 0)
        y -= 30
        label(t("s_gauges"), 20, y)
        chosen = set(R.get("claude_gauges") or [])
        claude_g = {}
        for n, g in enumerate(cp.CLAUDE_GAUGES):
            # 2열 × 2행 — 네 이름이 어느 로케일에서도 120pt 안에 들어간다 (macOS 판과 같은 칸)
            gx, gy = 180 + (n % 2) * 120, y - (n // 2) * 24
            claude_g[g] = check(gauge_title[g], gx, gy, 116, g in chosen)
        y -= 54
        label(t("s_admin_key"), 20, y)
        f_key = field(180, y - 2, 220, R.get("admin_key", ""), secure=True)
        y -= 30
        label(t("s_budget"), 20, y)
        f_bud = field(180, y - 2, 90, R.get("api_budget") or 0)

        # ── Codex 구역 (같은 모양) ──
        y -= 42
        show_codex = section(t("s_sec_codex"), "show_codex", y)
        y -= 30
        label(t("s_data_source"), 20, y)
        codex_mode = popup(180, y, 220, [t("s_codex_mode_sub"), t("s_codex_mode_api")],
                           1 if R.get("codex_mode") == "api" else 0)
        y -= 30
        label(t("s_gauges"), 20, y)
        chosen = set(R.get("codex_gauges") or [])
        codex_g = {}
        for n, g in enumerate(cp.CODEX_GAUGES):
            codex_g[g] = check(gauge_title[g], 180 + n * 120, y, 116, g in chosen)
        y -= 30
        label(t("s_openai_key"), 20, y)
        f_okey = field(180, y - 2, 220, R.get("openai_admin_key", ""), secure=True)
        y -= 30
        label(t("s_codex_budget"), 20, y)
        f_cbud = field(180, y - 2, 90, R.get("codex_budget") or 0)

        # ── 공통 ──
        y -= 42
        label(t("s_spike_sens"), 20, y)
        m = R.get("spike_mult", 1.0)
        sens = popup(180, y, 220, [t("s_sens_high"), t("s_sens_normal"), t("s_sens_low")],
                     0 if m < 0.9 else (2 if m > 1.5 else 1))
        y -= 32
        greet = check(t("s_greet"), 20, y, 380, R.get("greet"))

        vl = label(f"ClaudePet v{cp.APP_VERSION}", 20, 18, 200)
        vl.setStyleSheet("color: palette(placeholder-text);")     # NSColor.secondaryLabelColor
        save_btn = QPushButton(t("s_save"), self)
        save_btn.setGeometry(self.PWID - 110, self.PHT - 12 - 30, 90, 30)
        save_btn.clicked.connect(win.save_settings)

        win.ui.update({"panel": self, "mode": mode, "sens": sens, "greet": greet,
                       "key": f_key, "bud": f_bud, "lang": lang_pop,
                       "show_claude": show_claude, "claude_g": claude_g,
                       "show_codex": show_codex, "codex_mode": codex_mode, "codex_g": codex_g,
                       "okey": f_okey, "cbud": f_cbud,
                       "pet": pet_pop, "pet_ids": pet_ids})
        scr = win.screen() or QApplication.primaryScreen()        # macOS panel.center()
        a = scr.availableGeometry()
        self.move(a.center().x() - self.PWID // 2, a.center().y() - self.PHT // 2)

    def closeEvent(self, e):
        # X 로 닫힐 때 (macOS 판 windowWillClose_ → close_main_panel)
        if self.win.ui.get("panel") is self:
            self.win.close_main_panel()
        e.accept()


APP_USER_MODEL_ID = "me.yeongyu.claudepet"   # macOS 번들 식별자와 같은 값


def claim_windows_app_identity():
    """작업표시줄이 이 프로세스의 창들을 'Python'(pythonw.exe 의 아이콘·이름)이 아니라 이 앱으로 묶게 한다.

    Windows 는 창을 실행 파일 단위로 묶고 그 실행 파일의 아이콘을 쓴다. 소스 실행(pythonw)에서는 설정 창을 열면
    작업표시줄에 Python 아이콘이 떴다(사용자 지적 2026-09-12). 프로세스에 명시적 AppUserModelID 를 주면 창마다 지정한
    아이콘(app_icon)과 제목으로 묶인다. 패키징된 ClaudePet.exe 는 실행 파일에 아이콘이 들어 있지만 같은 ID 를 유지한다.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def seed_bundled_pets():
    """동봉 펫 4종과 README 를 ~/.claude_pet 에 **없는 것만** 채운다 — macOS 판 seed_bundled_pet_assets 와 같은 성질.

    · 완성본을 같은 드라이브의 임시 폴더(.seed-stage-<pid>)에 먼저 만들고, 덮어쓰지 않는 이름 바꾸기로 게시한다.
      Windows 의 os.rename 은 대상이 있으면 FileExistsError 를 내므로(MoveFileEx 에 REPLACE_EXISTING 없음) 이것이
      macOS 판의 RENAME_EXCL 에 해당한다. 부분 산출물은 게시되지 않고, 이미 있는 펫 폴더는 안을 보지 않고 건너뛴다.
    · 소스는 게시 전에 검사한다(파일 3개가 정규 파일이고 _bad_pet_metadata 가 None). 조금이라도 어긋나면 그 펫은 게시하지
      않는다. 실패는 조용히 넘기되 시작을 막지 않는다(디버그 로그에만 남긴다).
    """
    try:
        src = cp._default_bundled_pet_dir()
    except Exception:
        return
    dest = cp.USER_PET_HOME
    if not src or not os.path.isdir(src):
        cp._dbg("seed: bundled pets dir missing")
        return
    try:
        os.makedirs(os.path.join(dest, "pets"), exist_ok=True)
    except Exception as e:
        cp._dbg("seed: cannot create dest", type(e).__name__)
        return
    stage = os.path.join(dest, f".seed-stage-{os.getpid()}")
    shutil.rmtree(stage, ignore_errors=True)
    published = []
    try:
        os.makedirs(os.path.join(stage, "pets"))
        for name in cp.BUNDLED_PET_README:
            s_, d_ = os.path.join(src, name), os.path.join(dest, name)
            if os.path.lexists(d_) or not os.path.isfile(s_):
                continue
            st = os.path.join(stage, name)
            shutil.copyfile(s_, st)
            try:
                os.rename(st, d_)
                published.append(name)
            except FileExistsError:
                pass
        for pid in cp.BUNDLED_PET_IDS:
            s_, d_ = os.path.join(src, "pets", pid), os.path.join(dest, "pets", pid)
            if os.path.lexists(d_):
                continue
            if not os.path.isdir(s_) or os.path.islink(s_):
                continue
            if any(not os.path.isfile(os.path.join(s_, f)) or os.path.islink(os.path.join(s_, f))
                   for f in cp.BUNDLED_PET_FILES) or cp._bad_pet_metadata(s_, pid):
                cp._dbg("seed: bundled pet rejected", pid)
                continue
            st = os.path.join(stage, "pets", pid)
            os.makedirs(st)
            for f in cp.BUNDLED_PET_FILES:
                shutil.copyfile(os.path.join(s_, f), os.path.join(st, f))
            try:
                os.rename(st, d_)
                published.append("pets/" + pid)
            except FileExistsError:
                pass
    except Exception as e:
        cp._dbg("seed: failed", type(e).__name__)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    cp._dbg("seed: published", published)


def app_icon():
    """macOS 앱 아이콘과 같은 그림. claudepet.ico 는 release/icon.icns 의 1024px 그림을 16~256px 로 담은 것."""
    p = os.path.join(_HERE, "claudepet.ico")
    return QIcon(p) if os.path.isfile(p) else QIcon()


def make_tray(app, win):
    """작업표시줄 버튼이 없으므로 트레이 아이콘이 보이기/숨기기·종료의 진입로가 된다 (사용자 결정: 유지)."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    # 아이콘은 macOS 앱 아이콘(release/icon.icns)에서 만든 같은 그림(windows/claudepet.ico) — 사용자 요구: 아이콘도 동일.
    tray = QSystemTrayIcon(app_icon(), app)
    tray.setToolTip(f"ClaudePet v{cp.APP_VERSION}")
    m = QMenu()
    m.addAction(cp.t("menu_toggle"), win._toggle_panel)
    m.addAction(cp.t("menu_quit"), app.quit)
    tray.setContextMenu(m)
    tray.activated.connect(lambda reason: win.setVisible(not win.isVisible())
                           if reason == QSystemTrayIcon.Trigger else None)
    tray.show()
    return tray


def clean_update_leftovers():
    """지난 업데이트 거래가 앱 폴더 옆에 남긴 우리 폴더를 지운다 — 교체 헬퍼가 옛 폴더를 못 지웠거나 중간에 죽은 경우다.
    -new-*/-old-* 는 우리 exe 와 버전 마커를 품은 것만, -stage-* 는 아카이브 루트(ClaudePet) 말고는 아무것도 없는 것만
    (win_update.leftover_dirs — 이름만으로는 지우지 않는다). 반쯤 지워진 옛 폴더는 그래서 남고, 다음 업데이트가 old-dir-exists 로
    거절된다(README 의 안내대로 사용자가 지운다)."""
    exe = app_exe_path()
    if not exe:
        return
    parent = os.path.dirname(os.path.dirname(exe))
    removed = 0
    for p in wu.leftover_dirs(parent):
        try:
            shutil.rmtree(p)
            removed += 1
        except Exception:
            pass
    if removed:
        wu.log_update("cleanup", removed=removed)


def main():
    claim_windows_app_identity()              # QApplication 보다 먼저 — 창이 만들어지기 전에 묶음 ID 가 있어야 한다
    if not acquire_single_instance_mutex():   # 이미 떠 있으면 조용히 끝난다 — 설치 파일의 재시작과 [Run] 이 둘 다 띄워도 하나만 남는다
        cp._dbg("win: another instance holds the mutex; exiting")
        return 0
    register_application_restart()           # 설치 파일(Restart Manager)이 닫은 뒤 다시 띄울 수 있게 (installer.iss RestartApplications=yes)
    app = QApplication(sys.argv)
    # 지난 거래의 옆 폴더 정리는 1분 뒤 — 방금 portable 교체로 떴다면 헬퍼가 아직 옛 폴더를 지우는 중일 수 있다(확인 ≤ 23초).
    QTimer.singleShot(60_000, clean_update_leftovers)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Claude Pet")
    app.setWindowIcon(app_icon())             # 설정 창·알림 창의 제목줄·작업표시줄 아이콘도 같은 그림
    cfg = cp.load_config()
    cp.apply_config(cfg)
    if not cp.RUNTIME.get("lang"):            # 저장된 언어가 없으면 Windows UI 언어를 따른다
        code = windows_ui_lang()
        if code:
            cp.set_lang(code)
    seed_bundled_pets()                        # 동봉 펫·README 를 ~/.claude_pet 에 없는 것만 (macOS 판과 같은 시점: 첫 메뉴 전)
    try:                                       # 펫 폴더 안내 README — 없거나 비어 있으면 (macOS 판 run_gui 와 같음)
        os.makedirs(cp.USER_PETS_DIR, exist_ok=True)
        cp._write_pets_readme(cp.USER_PETS_DIR)
    except Exception:
        pass
    pets = cp.discover_pets()
    if not pets:
        print(f"스프라이트를 찾지 못했습니다: {cp.PET_DIR}", file=sys.stderr)
        return 1
    sel = next((p for p in pets if p["id"] == cfg.get("pet")), None)
    frames = load_pet_frames(sel["dir"]) if sel else None
    if frames is None:
        sel = pets[0]
        frames = load_pet_frames(sel["dir"])
    if frames is None:
        print(f"스프라이트를 찾지 못했습니다: {sel['dir']}", file=sys.stderr)
        return 1
    # 새 릴리즈 확인은 시작 시 하지 않는다 — macOS 판과 같은 사용자 요구(2026-09-11). 기준점을 '지금' 으로 찍어 두면 새로고침
    # 워커가 UPDATE_CHECK_SEC(1시간) 뒤부터 확인한다. PetWindow 가 첫 새로고침을 바로 시작하므로 그 전에 찍는다.
    cp._upd_cache["t"] = time.time()
    win = PetWindow(frames, cfg, pets)
    win.show()
    tray = make_tray(app, win)  # noqa: F841  (GC 방지)
    win.tray = tray                            # 비모달 알림(트레이 풍선)의 출구
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
