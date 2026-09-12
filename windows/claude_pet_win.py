#!/usr/bin/env python3
"""ClaudePet for Windows — 2단계 (PySide6).

macOS 판 `claude_pet.py` 를 **그대로 import** 해 사용량 추정기·정확 모드·설정 파일·다국어·필 형상 상수·
자율 이동 상태기계(Roamer/RoamDisplay)·요약 필 내용·crop 기하(roam_frame)를 재사용하고, 이 파일은
Windows 에서 필요한 것만 구현한다:

  · 창: 프레임 없음 · 투명 배경 · 항상 위 · 작업표시줄 버튼 없음(Tool) · 트레이 아이콘
  · 그리기: 스프라이트(내장 PNG 폴더 또는 pet.json + spritesheet.webp) · 게이지 필 · 상태줄 · 접기 버튼 · 요약 필
  · 마우스: 드래그(놓으면 x/y 저장 — macOS 와 같은 정책) · 더블클릭(점프 + 즉시 새로고침) · 호버 인사 · 우클릭 메뉴
  · 자율 이동 어댑터: QScreen → RoamScreen(id/frame/bounds), 창 중심 ↔ 실제 창(crop), 점프 효과(창 불투명도),
    시스템 애니메이션 설정(= macOS 의 동작 줄이기), '화면 돌아다니기' 메뉴 토글

좌표: Qt 는 y 가 아래로 커진다. Roamer 는 축 방향을 가정하지 않으므로 전역 좌표를 그대로 넘기고,
RoamScreen.frame/bounds 도 같은 축으로 만든다. roam_frame 이 주는 crop/sprite/button/pill 은 창 내부 좌표라
(macOS 의 flipped 뷰와 같은 y-down) 그대로 쓰고, 실제 창 원점만 여기서 y-down 으로 계산한다.

2단계 범위 밖(다음): 설정 창(% 보정 등), 업데이트 교체, 펫 시딩, PyInstaller 패키징.
`claude_pet.py` 와 macOS 빌드·릴리즈 스크립트는 이 파일로 바뀌지 않는다.

실행: `pythonw windows\\claude_pet_win.py` (저장소 루트에서, Python 3.13 + PySide6 + Pillow)
"""
import math
import os
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _import_core():
    """`claude_pet` 을 Windows 에서 import 한다 — 기존 파일을 고치지 않고 두 가지만 우회한다.

    1. `import fcntl`: POSIX 전용 모듈. windows/compat/fcntl.py(msvcrt 기반 flock) 를 sys.path 맨 앞에 둔다.
    2. `ctypes.CDLL(None)`: macOS 의 renameatx_np 탐색이 Windows 에서는 OSError 가 아니라 TypeError 를 내
       모듈 최상단에서 죽는다. import 하는 동안만 CDLL 을 감싸 None 인자에 OSError 를 내게 하면 기존
       `except (OSError, AttributeError)` 가 잡아 `_RENAMEATX_NP = None` 폴백(이 OS 에는 없음)을 탄다.
    macOS 에서는 둘 다 적용하지 않는다(표준 fcntl·CDLL 그대로).
    """
    import importlib
    if sys.platform != "win32":
        return importlib.import_module("claude_pet")
    compat = os.path.join(_HERE, "compat")
    if compat not in sys.path:
        sys.path.insert(0, compat)
    import ctypes
    real_cdll = ctypes.CDLL

    class _CDLL(real_cdll):
        def __init__(self, name, *args, **kwargs):
            if name is None:
                raise OSError("CDLL(None) is not available on Windows")
            super().__init__(name, *args, **kwargs)
    ctypes.CDLL = _CDLL
    try:
        return importlib.import_module("claude_pet")
    finally:
        ctypes.CDLL = real_cdll


cp = _import_core()  # AppKit 은 run_gui 안에서만 import 되므로 GUI 없이 코어를 쓸 수 있다 (설계 문서 §0)

from PIL import Image  # noqa: E402
from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (QAction, QColor, QCursor, QFont, QFontDatabase, QFontMetrics,  # noqa: E402
                           QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget  # noqa: E402

TICK_MS = 50                 # macOS 판 TICK = 0.05 와 같은 20 Hz
NEAR_PX = 100                # 인사 판정 거리 — macOS 판과 동일
GREET_COOLDOWN = float(getattr(cp, "GREET_COOLDOWN", 20.0))
BTN_LINE = "#2E2E33"
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
    """macOS 판 run_gui.spike_info 와 같은 규칙."""
    if not stats or cp.RUNTIME["mode"] == "api":
        return None
    sp = stats.get("spikes") or {}
    if sp.get("session"):
        return (cp.COL_BAD, cp.t("session"))
    if sp.get("weekly"):
        return (cp.COL_BAD, cp.t("weekly"))
    if sp.get("opus"):
        return (cp.COL_BAD, str(stats.get("model_kw", "opus")).capitalize())
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


# ─────────────────────────── 펫 창 ───────────────────────────
class PetWindow(QWidget):
    SUB_SHRINK_FLOOR = 0.85      # 서브텍스트 폰트 축소 하한 — 한글 받침이 뭉개지지 않는 선

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
                      "roam_env": None, "roam_crop": None, "roam_rects": None, "roam_mode": None}
        self.sticky = {"on": False}
        self._down = None
        self._moved = False
        self._refresh_gen = 0
        self._refresh_lock = threading.Lock()
        self._pending = None
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
    def geom(self):
        pw = int(self.PW0 * self.scale)
        ph = int(self.PH0 * self.scale)
        w = max(pw + cp.BTN_R * 2 + 16, cp.PILL_W + 8)
        h = ph + cp.GAP + cp.pill_h() + 4
        return pw, ph, w, h

    def _fonts(self):
        fixed = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fam = fixed.family()
        for cand in ("Cascadia Mono", "Consolas", fam):
            if cand in QFontDatabase.families():
                fam = cand
                break

        def mono(size, bold=False):
            f = QFont(fam, 1)
            f.setPointSizeF(size)
            f.setBold(bold)
            return f
        self.F_BOLD = mono(12, True)
        self.F_BIG = mono(15, True)
        self.F_SUB = mono(9.5)
        self.F_ALERT = mono(9.5, True)
        self.F_TINY = mono(8.5)
        self.F_STATUS = mono(10)
        self.F_SUMMARY = mono(11, True)

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
        kind, payload = cp.roam_summary(cp.RUNTIME["mode"], self.state["oauth"], self.state["stats"],
                                        self.state.get("onboard"), self.state["cost"],
                                        bool(cp.RUNTIME.get("admin_key")))
        txt = cp.roam_summary_line(kind, payload, cp.t)
        return txt, float(self._text_w(txt, self.F_SUMMARY))

    def roam_apply_display(self, phase):
        """표시 모드 → crop/rect → 실제 창 크기·원점. 경로·집은 건드리지 않는다 → 다시 그릴지."""
        mode = self.roam_display.mode(phase, self.state["show_panel"])
        text_w = self.roam_summary_text()[1] if mode == cp.DISPLAY_SUMMARY else 0.0
        w_, h_ = self.roam_env()
        lay = cp.roam_frame(self.roamer.pos, mode, self.pet_on_right(), self.pet_on_bottom(),
                            w_, h_, self.PW, self.PH, cp.pill_h(), self.scale, text_w)
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
        rects = self.state.get("roam_rects")
        if rects and rects.get("pill"):
            return rects["pill"]
        return (self.W - cp.PILL_W - 4 if self.pet_on_right() else 4,
                4 if self.pet_on_bottom() else self.PH + cp.GAP, cp.PILL_W, cp.pill_h())

    def pet_origin(self):
        rects = self.state.get("roam_rects")
        if rects:
            return (rects["sprite"][0], rects["sprite"][1])
        py = cp.pill_h() + cp.GAP if self.pet_on_bottom() else 2
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
        if st["oauth"]:
            pct = max((row[1] for row in st["oauth"]), default=0)
            return "failed" if pct >= 85 else ("waiting" if pct >= 50 else "idle")
        return cp.mood_for(stats) if stats else "idle"

    def _apply_pending(self):
        """새로고침 워커가 남긴 결과를 메인 스레드(tick)에서 반영한다 — 워커는 위젯·상태를 직접 만지지 않는다."""
        with self._refresh_lock:
            pending, self._pending = self._pending, None
        if pending is None:
            return False
        prev = self.state["stats"]
        self.state.update(pending)
        s = pending.get("stats")
        if prev and s and prev["session"]["pct"] > 5 and s["session"]["pct"] < 1:
            self.set_override("jumping")
        n = self._rows_n()
        if n != cp.CUR_PILL["n"]:
            cp.CUR_PILL["n"] = n
            self.state["relayout"] = True
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
                values["stats"] = cp.compute_usage()
                values["oauth"] = cp.fetch_exact_usage()
                values["onboard"] = cp.compute_onboard_state(values["oauth"], cp._has_claude_logs())
                if cp.RUNTIME["mode"] == "api":
                    values["cost"] = cp.fetch_api_cost_today()
                    values["cost_month"] = cp.fetch_api_cost_month()
            except Exception as e:  # 추정 실패는 화면에 '스캔 중' 으로 남고 다음 새로고침에 다시 시도
                print(f"[refresh] failed: {type(e).__name__}", file=sys.stderr)
            finally:
                with self._refresh_lock:
                    if gen == self._refresh_gen:      # 더 새 요청이 있으면 버린다 (macOS 판 세대 규칙)
                        self._pending = values
        threading.Thread(target=work, daemon=True).start()

    def _rows_n(self):
        if cp.RUNTIME["mode"] == "api":
            return 3
        if self.state["oauth"]:
            return max(1, len(self.state["oauth"]))
        return 3

    # ── 그리기 ──
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

    def _sub_right(self, p, candidates, font, color, ry, gx0, label_w):
        """서브텍스트 우측 정렬. macOS 판 draw_sub_right 와 같은 자리에 그리되 맞추는 방법이 다르다.

        Windows 의 모노 글꼴과 한글 대체 글꼴은 macOS 보다 넓어서, 라벨이 길면(예: 'Fable') 폰트를
        0.68 배까지 줄여도 넘치고 받침이 잘린다. 그래서 (1) 호출자가 준 후보 문자열을 긴 것부터 시도하되
        버리기 전에 그 후보를 SUB_SHRINK_FLOOR 까지만 줄여 보고, (2) 다 넘치면 마지막 후보를 하한으로 줄인 뒤
        말줄임한다. 세로는 실제 글꼴(대체 글꼴 포함) 높이로 행 안에 가운데 맞춘다.
        """
        if isinstance(candidates, str):
            candidates = [candidates]
        x_left = gx0 + cp.PILL_PAD + 2 + label_w + 10
        x_right = gx0 + cp.PILL_W - cp.PILL_PAD
        avail = max(20.0, x_right - x_left)
        f = QFont(font)
        txt = candidates[-1]
        for cand in candidates:
            w = self._text_w(cand, font)
            if w <= avail:
                txt, f = cand, QFont(font)
                break
            scale = avail / w
            if scale >= self.SUB_SHRINK_FLOOR:
                f = QFont(font)
                f.setPointSizeF(font.pointSizeF() * scale)
                if self._text_w(cand, f) <= avail:
                    txt = cand
                    break
        else:
            f = QFont(font)
            f.setPointSizeF(max(font.pointSizeF() * self.SUB_SHRINK_FLOOR, 6.0))
            if self._text_w(txt, f) > avail:
                txt = QFontMetrics(f).elidedText(txt, Qt.ElideRight, int(avail))
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QRectF(x_left, ry, avail, 16), Qt.AlignRight | Qt.AlignVCenter | Qt.TextSingleLine, txt)

    def _bar(self, p, bx0, by, bw, pct, color):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(cp.TRACK))
        p.drawRoundedRect(QRectF(bx0, by, bw, 6), 3, 3)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(bx0, by, max(8, bw * pct / 100), 6), 3, 3)

    def _draw_sub_pill(self, p, gx0, gy0, stats):
        sp = stats.get("spikes") or {}
        keys = ["session", "weekly", "opus"]
        for i, (label, gg) in enumerate(cp.gauge_rows(stats)):
            ry = gy0 + cp.PILL_PAD + i * cp.ROW_H
            lw = self._text(p, gx0 + cp.PILL_PAD + 2, ry - 2, label, self.F_BOLD, cp.TXT_MAIN)
            spiking = sp.get(keys[i])
            pct = f"{gg['pct']:.0f}%"
            left = f"{cp.t('left')} {cp.fmt_tokens(gg['left'])}"
            reset_s = cp.fmt_reset(gg['reset'], stats['now'])
            short_reset = cp.fmt_countdown(gg['reset'], stats['now']) if gg['reset'] else reset_s
            prefix = cp.t("spike_prefix") if spiking else ""
            # 후보 순서(정보 우선, 뜻 보존): 전체 → 짧은 리셋 → 남음만(라벨 유지) → 리셋만 → % 만.
            # '남음' 이라는 말을 빼고 숫자만 남기면 macOS 판과 달리 남은 양인지 쓴 양인지 모호해지므로 넣지 않는다.
            cands = [f"{prefix}{pct} · {left} · {reset_s}", f"{prefix}{pct} · {left} · {short_reset}",
                     f"{prefix}{pct} · {left}", f"{prefix}{pct} · {short_reset}", f"{prefix}{pct}"]
            self._sub_right(p, cands, self.F_ALERT if spiking else self.F_SUB,
                            cp.COL_BAD if spiking else cp.TXT_SUB, ry, gx0, lw)
            self._bar(p, gx0 + cp.PILL_PAD + 2, ry + 17, cp.PILL_W - cp.PILL_PAD * 2 - 4,
                      gg["pct"], cp.COL_BAD if spiking else cp.bar_color(gg["pct"]))

    def _draw_exact_pill(self, p, gx0, gy0, rows):
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        stats = self.state["stats"]
        for i, (label, pct, rdt, rtxt) in enumerate(rows[:cp.PILL_ROWS]):
            ry = gy0 + cp.PILL_PAD + i * cp.ROW_H
            lw = self._text(p, gx0 + cp.PILL_PAD + 2, ry - 2, label, self.F_BOLD, cp.TXT_MAIN)
            if rdt is not None:
                reset_s = cp.fmt_reset(rdt, now_utc)
                short_reset = cp.fmt_countdown(rdt, now_utc)
            elif rtxt:
                reset_s = cp.t("reset_prefix") + rtxt
                short_reset = rtxt
            else:
                reset_s = short_reset = ""
            used = f"{pct:.0f}% {cp.t('used')}"
            cands = [used + (f" · {reset_s}" if reset_s else ""),
                     f"{pct:.0f}%" + (f" · {reset_s}" if reset_s else ""),
                     f"{pct:.0f}%" + (f" · {short_reset}" if short_reset else ""),
                     f"{pct:.0f}%"]
            self._sub_right(p, cands, self.F_SUB, cp.TXT_SUB, ry, gx0, lw)
            spiking = bool(spike_info(stats)) and i == 0
            self._bar(p, gx0 + cp.PILL_PAD + 2, ry + 17, cp.PILL_W - cp.PILL_PAD * 2 - 4,
                      pct, cp.COL_BAD if spiking else cp.bar_color(pct))

    def _draw_centered(self, p, gx0, gy0, s, font, color):
        w = self._text_w(s, font)
        h = QFontMetrics(font).height()
        self._text(p, gx0 + (cp.PILL_W - w) / 2, gy0 + (cp.pill_h() - h) / 2, s, font, color)

    def _draw_onboard(self, p, gx0, gy0, kind):
        reason = cp.t("onb_install") if kind == "install" else cp.t("onb_login")
        hint = cp.t("menu_install_cc") if kind == "install" else cp.t("menu_login_cc")
        cy = gy0 + cp.pill_h() / 2
        rw = self._text_w(reason, self.F_BOLD)
        rh = QFontMetrics(self.F_BOLD).height()
        self._text(p, gx0 + (cp.PILL_W - rw) / 2, cy - rh - 1, reason, self.F_BOLD, cp.TXT_MAIN)
        hw = self._text_w(hint, self.F_SUB)
        self._text(p, gx0 + (cp.PILL_W - hw) / 2, cy + 3, hint, self.F_SUB, cp.TXT_SUB)

    def _draw_status(self, p, gx0, gy0):
        st = self.state
        if cp.RUNTIME["mode"] == "api":
            mode = "API"
        elif st["oauth"]:
            mode = cp.t("exact_mode")
        else:
            mode = cp.t("log_estimate").strip("()（）") + (" ⚠" if cp.OAUTH_STATUS.get("auth_error") else "")
        y = gy0 + cp.pill_h() - 14
        self._text(p, gx0 + cp.PILL_PAD + 2, y, mode, self.F_STATUS, "#7A7A82")
        ver = f"v{cp.APP_VERSION}"
        self._text(p, gx0 + cp.PILL_W - cp.PILL_PAD - self._text_w(ver, self.F_STATUS), y, ver,
                   self.F_STATUS, "#7A7A82")

    def _draw_summary_pill(self, p):
        """구경 도착 요약: 펫에 붙은 작은 둥근 필 한 줄. 상태줄·버전 없음. 폰트 축소 없이 말줄임 (macOS 판 규칙)."""
        rects = self.state.get("roam_rects")
        pill = rects.get("pill") if rects else None
        if not pill:
            return
        x, y, w, h = pill
        p.setPen(Qt.NoPen)
        p.setBrush(self._color(cp.PILL_BG, 0.96))
        p.drawRoundedRect(QRectF(x, y, w, h), h / 2, h / 2)
        txt, _tw = self.roam_summary_text()
        txt = cp.roam_fit_text(txt, w - 2 * cp.PILL_PAD, lambda v: self._text_w(v, self.F_SUMMARY))
        p.setFont(self.F_SUMMARY)
        p.setPen(QColor(cp.TXT_MAIN))
        p.drawText(QRectF(x, y, w, h), Qt.AlignCenter | Qt.TextSingleLine, txt)

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
        if mode == cp.DISPLAY_SUMMARY:
            self._draw_summary_pill(p)
        elif mode == cp.DISPLAY_FULL:
            gx0, gy0, gw, gh = self.pill_rect()
            p.setPen(Qt.NoPen)
            p.setBrush(self._color(cp.PILL_BG, 0.96))
            p.drawRoundedRect(QRectF(gx0, gy0, cp.PILL_W, cp.pill_h()), cp.PILL_R, cp.PILL_R)
            if cp.RUNTIME["mode"] == "api":
                self._draw_centered(p, gx0, gy0, "API", self.F_SUB, cp.TXT_SUB)   # 비용 표시는 설정 창과 함께
            elif st["oauth"]:
                self._draw_exact_pill(p, gx0, gy0, st["oauth"])
            elif st.get("onboard"):
                self._draw_onboard(p, gx0, gy0, st["onboard"])
            elif stats:
                self._draw_sub_pill(p, gx0, gy0, stats)
            else:
                self._draw_centered(p, gx0, gy0, cp.t("scanning"), self.F_SUB, cp.TXT_SUB)
            if (stats or st["oauth"]) and not st.get("onboard"):
                self._draw_status(p, gx0, gy0)

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
            is_full = mode == cp.DISPLAY_FULL
            point_down = (pill_below and not is_full) or (not pill_below and is_full)
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
        m = QMenu(self)
        m.addAction(cp.t("menu_toggle"), self._toggle_panel)
        pets = QMenu(cp.t("menu_pets"), m)
        for pinfo in self.pets:
            a = QAction(pinfo["name"], pets, checkable=True)
            a.setChecked(pinfo["id"] == self.cfg.get("pet", "default"))
            a.triggered.connect(lambda checked=False, pid=pinfo["id"]: self._set_pet(pid))
            pets.addAction(a)
        m.addMenu(pets)
        roam = QAction(cp.t("menu_roam"), m, checkable=True)
        roam.setChecked(bool(cp.RUNTIME.get("roam")))
        roam.setEnabled(not self.state["reduce_motion"])     # 동작 줄이기(애니메이션 끔)면 비활성
        roam.triggered.connect(self._toggle_roam)
        m.addAction(roam)
        m.addSeparator()
        v = m.addAction(f"ClaudePet v{cp.APP_VERSION}")
        v.setEnabled(False)
        m.addAction(cp.t("menu_quit"), QApplication.instance().quit)
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


def make_tray(app, win):
    """작업표시줄 버튼이 없으므로 트레이 아이콘이 보이기/숨기기·종료의 진입로가 된다 (사용자 결정: 유지)."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    icon = QIcon(win.frames["idle"][0].scaled(QSize(64, 64), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip(f"ClaudePet v{cp.APP_VERSION}")
    m = QMenu()
    m.addAction(cp.t("menu_toggle"), win._toggle_panel)
    m.addAction(cp.t("menu_quit"), app.quit)
    tray.setContextMenu(m)
    tray.activated.connect(lambda reason: win.setVisible(not win.isVisible())
                           if reason == QSystemTrayIcon.Trigger else None)
    tray.show()
    return tray


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    cfg = cp.load_config()
    cp.apply_config(cfg)
    if not cp.RUNTIME.get("lang"):            # 저장된 언어가 없으면 Windows UI 언어를 따른다
        code = windows_ui_lang()
        if code:
            cp.set_lang(code)
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
    win = PetWindow(frames, cfg, pets)
    win.show()
    tray = make_tray(app, win)  # noqa: F841  (GC 방지)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
