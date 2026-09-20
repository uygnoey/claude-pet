"""Gates for the v0.26 Windows port (Track W, 2026-09-20). Verifier-owned.

Run from the worktree root:

    python -m unittest discover -s windows/tests -t . -v

Verifier-owned under AGENTS.md §2 Condition A. The Developer owns
``windows/claude_pet_win.py``, ``windows/win_core.py``, ``windows/win_update.py``,
``windows/win_autostart.py``, ``windows/build_win.py``,
``windows/verify_win_artifact.py`` and ``claude_pet.py``, and must not touch an
assertion, an expected value or a fixture literal in this file.

═══════════════════════════ what this file is for ═══════════════════════════

v0.26 landed on macOS and none of it reached the Qt port. Six things have to be
wired: token auto-recovery, the Codex usage row, credit amounts, the API refusal
reason, the provider marks, and per-provider lines inside a pill whose width
follows its content.

Every gate here is written against a defect that **actually shipped green on
macOS in this same release**. That is the selection rule: these are not
hypothetical rivals, they are the implementations that were written, passed a
full suite, and had to be found by hand afterwards. The Qt port has the same
traps in the same places, so the gates are aimed at them rather than at the
happy path.

The six macOS defects, and which gate answers each:

    1. the pill's cap hid one layer up — ``roam_pill_rect``'s cap was fixed but
       ``geom()`` still handed it ``W = PILL_W + 8``, so nothing widened.
       Qt has the identical line. → ``PillFollowsItsContentTests``
    2. the regression test for (1) fed ``roam_pill_rect`` a screen width that
       production never passes, while a second test fed it the production value
       and asserted 300. Both green, mutually contradictory.
       → this file takes its numbers from production on **both** sides: the
       content width comes from the port's own adapter and the pill from the
       port's own ``pill_rect()``. See ``_settle``.
    3. the logo tint was a complete no-op — ``setTemplate_`` plus a context fill
       colour, neither of which the draw path consults. Tinted and untinted were
       byte-identical and both black, so the OpenAI mark was invisible on the
       dark pill. Qt has the same trap: ``setPen``/``setBrush`` do not touch
       bitmap compositing. → ``ProviderMarksReachThePixelsTests``
    4. the tint gate covered the compositor and not the layer that decides
       whether to composite, so deleting the two tint lines broke no behavioural
       test. → the pixel gates render through the port's own pill-drawing entry
       point, so both layers are inside the gate by construction.
    5. the adapter's return shape changed to a 3-tuple and one of its three
       consumers was not updated. → ``AdapterConsumersAgreeTests``
    6. a release-gate loop over the logos passed vacuously when the list was
       empty, because a defensive ``getattr(..., {})`` disarmed the check.
       → ``BundleCarriesTheLogosTests`` asserts the list it iterates is
       non-empty and equals the core's own table before it checks anything.

═══════════════════════════ the discrimination rule ═══════════════════════════

AGENTS.md §3: a fixture must give a distinct result under every plausible wrong
implementation. Each test class below names its rivals in its docstring and says
what each one returns for the fixture. Where a rival ties with the correct
answer the fixture is changed until it does not — that enumeration is the work,
not the assertion count.

The lesson from defect (2) governs every fixture in this file: **a fixture may
take production's values; it may never recite production's formula.** A value
that goes stale goes stale loudly — the test breaks and someone looks. A recited
formula goes stale silently and agrees with itself forever, which is how two
green tests came to contradict each other.

**An earlier version of this docstring claimed that rule was already kept here,
and it was not.** Four places did production's own arithmetic, and the claim in
the docstring is what would have stopped the next reader from checking. The
corrected rule, which is stricter than "do not hardcode":

> Deriving a number is not enough. **The derivation has to come out of
> production's own callable.** A test that reaches the same number by repeating
> production's steps is a second implementation of that formula, and the two
> agree until the day production's copy changes — at which point the test
> confirms the change instead of judging it.

Measured, not argued: with ``inner = pill_w - 2 * PILL_PAD - SUMMARY_LOGO_W``
written out here, deleting the ``+ cp.SUMMARY_LOGO_W`` that the adapter hands
back to the fold budget broke **no gate in this file**. The budget shrank by the
mark's width, every line folded early, and the test recomputed the same shrunken
limit and agreed. The gates now call ``_pill_text_budget()`` and
``roam_pill_rect()`` — production's own — and that mutation is red.

Two things no width assertion can ever catch, so they are asserted **by
position** against the rendered image instead:

* **an over-folded line** — it fits every budget, so "does it fit" is always yes;
* **a line missing its indent** — it fits *better*, so a width test is not merely
  silent, it is reassured. It is caught by looking at where the ink is.

═══════════════════════════ what is real here ═══════════════════════════

The pixel gates render through real Qt on the offscreen platform — a real
``QImage``, real font rasterisation, a real SVG renderer. That is deliberate and
is the only reason defect (3) is catchable: it was invisible to every
source-reading test and visible immediately in a pixel histogram. Reading the
code cannot answer "does the mark end up a colour the user can see".

Nothing here touches ``%USERPROFILE%\\.claude_pet``, ``.claude_pet.json``, the
real registry, the network, or the real ``~/.claude`` log corpus. Every fixture
is built by hand; ``RUNTIME`` and ``OAUTH_STATUS`` are patched and restored.

If PySide6 is missing the Qt gates skip **loudly** — stderr plus ``skipTest`` —
so that a missing prerequisite can never read as coverage.
"""

import ast
import io
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import windows.win_core as win_core  # noqa: E402  — the ONE owner of the core import

# The core, through `import_core()` and never bare. A bare `import claude_pet` here
# collects fine on macOS and kills the whole module at collection time on Windows
# (`ModuleNotFoundError: No module named 'fcntl'`, then `TypeError: LoadLibrary()
# argument 1 must be str, not None`). windows/README.md names this helper as the single
# place both detours live.
cp = win_core.import_core()  # noqa: E402

WINDIR = os.path.join(ROOT, "windows")
PORT = os.path.join(WINDIR, "claude_pet_win.py")
BUILDER = os.path.join(WINDIR, "build_win.py")


def _text(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


# ═══════════════════════════════════════════════════════════════════════════════
# Qt harness — offscreen, hand-built window, no timers and no threads
# ═══════════════════════════════════════════════════════════════════════════════

_QT_ERROR = None
_APP = None

try:                                              # pragma: no cover - import shape
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtGui import QImage, QPainter, QPixmap, QColor
except Exception as exc:                          # pragma: no cover - absent Qt
    _QT_ERROR = "%s: %s" % (type(exc).__name__, exc)
    QApplication = QWidget = QImage = QPainter = QPixmap = QColor = None


def _qt_app():
    """One offscreen QApplication for the module. Returns None if Qt is unusable."""
    global _APP, _QT_ERROR
    if _QT_ERROR:
        return None
    if _APP is None:
        try:
            _APP = QApplication.instance() or QApplication([])
        except Exception as exc:                  # pragma: no cover - no display
            _QT_ERROR = "%s: %s" % (type(exc).__name__, exc)
            return None
    return _APP


def _port_module():
    """Import `claude_pet_win` the way the port itself is imported (bare, windows/ on path)."""
    windir = WINDIR
    if windir not in sys.path:
        sys.path.insert(0, windir)
    import importlib
    return importlib.import_module("claude_pet_win")


def _require_qt(case):
    """Skip loudly. A missing prerequisite must never be mistaken for coverage."""
    if _qt_app() is None:
        msg = ("[win-v026] SKIPPING Qt pixel gates: PySide6 unusable here (%s). "
               "These gates are the only ones that can see a logo tint that does "
               "nothing; skipping them is NOT a pass." % _QT_ERROR)
        print(msg, file=sys.stderr)
        case.skipTest(msg)
    try:
        return _port_module()
    except Exception as exc:
        msg = ("[win-v026] SKIPPING: windows/claude_pet_win.py did not import (%s: %s)"
               % (type(exc).__name__, exc))
        print(msg, file=sys.stderr)
        case.skipTest(msg)


# ── fixture content ────────────────────────────────────────────────────────────
#
# Rows are the shape `roam_summary` consumes: (label, pct, reset_dt, reset_text).
# Values are chosen so that no two candidate implementations produce the same
# rendering — see each test class for the rival table.

CLAUDE_OAUTH = [
    ("Session", 42.0, None, "3h 43m"),
    ("Weekly", 17.0, None, "2d 4h"),
    ("Fable", 12.0, None, "6d 1h"),
]

# Codex rows as `parse_codex_usage` emits them: TR keys, not display text.
CODEX_ROWS = [
    ("codex_session", 68.0, None, "1h 5m"),
    ("codex_weekly", 23.0, None, "4d 2h"),
]


def _base_state(**over):
    """The state keys the pill path reads, all explicit. Mirrors PetWindow.__init__."""
    st = {
        "stats": None, "oauth": None, "onboard": None, "cost": None, "cost_month": None,
        "frame": 0, "mood": "idle", "override": None, "show_panel": True,
        "elapsed": 0.0, "resting": False, "rest_elapsed": 0.0, "last_mood": "idle",
        "dragging": False, "greet_cool": 0.0, "hover": False, "repaint": False,
        "roam_layout": (True, False),   # pet on the right, not on the bottom — fixed,
                                        # so the pill's placement does not depend on
                                        # where an unshown widget happens to sit.
        "roam_anim": None, "roam_hold": False, "menu_open": False,
        "reduce_motion": False,
        "roam_env": None, "roam_crop": None, "roam_rects": None,
        "roam_mode": cp.DISPLAY_FULL,
    }
    st.update(over)
    return st


def _make_window(port, **state_over):
    """A real QWidget with the port's real fonts, and nothing else running.

    Built with ``__new__`` rather than ``PetWindow(...)`` because the real
    constructor starts two QTimers, spawns the refresh thread and reads the
    user's config — none of which this file is allowed to do, and all of which
    would make a pixel comparison depend on the clock.

    Everything the pill path actually touches is filled in explicitly, so a new
    collaborator appearing in that path shows up as a clear AttributeError
    naming it rather than as a silently different picture.
    """
    w = port.PetWindow.__new__(port.PetWindow)
    QWidget.__init__(w)
    w.frames = {"idle": [QPixmap(8, 8)]}
    w.cfg = {}
    w.pets = []
    w.scale = 0.5
    w.PW0 = w.PH0 = 64
    w.sticky = {"on": False}
    w.ui = {}
    w.tray = None
    # Per-instance caches that PetWindow.__init__ creates and the pill path reads.
    # The harness does not run __init__, so it owes them. If a new one appears the
    # failure names it exactly ("no attribute '<name>'"), which is why they are set
    # here rather than papered over with a __getattr__ that would invent a value.
    w._logo_cache = {}
    w.state = _base_state(**state_over)
    w._fonts()
    w.PW, w.PH, w.W, w.H = w.geom()
    return w


def _adapter(w):
    """The port's summary adapter, with its 5-second memo defeated.

    The memo keys on ``int(time.time() / 5)`` and on ``id()`` of the stats and
    oauth objects. Both are hazards for a test: two calls can land in different
    5-second windows, and CPython reuses ids of collected objects. Clearing the
    memo before each call removes both without reaching into the memo's shape.
    """
    if hasattr(w, "_summary_memo"):
        try:
            del w._summary_memo
        except AttributeError:                    # pragma: no cover - class attr
            w._summary_memo = None
    return w.roam_summary_text()


def _blocks_of(value):
    """The adapter's blocks, whichever shape it returns, or a contract failure.

    This is where defect (5) surfaces: the macOS adapter went from
    ``(main, sub, w, h)`` to ``(blocks, w, h)`` and one of three consumers kept
    unpacking four. "The function is called" and "what came back can be used"
    are different questions, and only the second one is about the screen.
    """
    if not isinstance(value, tuple):
        raise AssertionError("roam_summary_text() returned %r, not a tuple" % (type(value),))
    if len(value) == 3:
        return value[0]
    raise AssertionError(
        "roam_summary_text() returned a %d-tuple; the v0.26 contract is "
        "(blocks, width, height) where blocks is [(provider_id, [line, ...]), ...]. "
        "A 4-tuple is the pre-v0.26 (main, sub, w, h) shape, which carries no "
        "provider identity and so cannot place a per-provider mark." % len(value))


def _lines(blocks):
    """Every rendered line in order, flattened: [(provider_id, [(text, kind), ...]), ...]."""
    return [(pid, line) for pid, lines in blocks for line in lines]


def _line_text(line):
    return "".join(text for text, _kind in line)


def _is_reset_line(line):
    """The one rule, in the one place. A line whose every run is "sub" is a reset line.

    Line-level, never run-level. The core folds by this rule (``summary_lines``) and
    the draw code picks its font by this rule (``_draw_summary_pill``); a third
    spelling in the tests would be a fourth opinion. An inlined reset is a "sub" run
    on a gauge line and must **not** drag that line to the small font.
    """
    return bool(line) and all(kind == "sub" for _t, kind in line)


def _line_font(w, line):
    """The font the port will actually draw this line in."""
    return w.F_SUMMARY_SUB if _is_reset_line(line) else w.F_SUMMARY


def _streams(lines):
    """A provider's lines split into the two streams the adapter folds separately.

    ``[("value", [...]), ("reset", [...])]``. The discriminator is the one the draw
    code uses to choose a font: a line whose every run is ``"sub"`` is a reset line.
    Reading it off the runs rather than off position means a provider that gains a
    third stream does not silently get classified as one of these two.
    """
    reset = [l for l in lines if _is_reset_line(l)]
    value = [l for l in lines if l and not _is_reset_line(l)]
    return [("value", value), ("reset", reset)]


def _settle(w):
    """Drive one frame of the real sequence: measure, then re-shape the window.

    This is the order the app runs per tick — the adapter measures the content
    and records the width it needs, then the geometry is recomputed from that
    record. Doing it in the other order is what defect (1) was: the cap was
    lifted inside ``roam_pill_rect`` while the ``W`` handed to it stayed pinned
    at ``PILL_W + 8`` one layer up, so the lifted cap never applied to anything.

    Returns (blocks, adapter_width, adapter_height). The second pass exists
    because ``next_pill_width`` only *grows* immediately; a shrink needs a
    settled frame, and a test that measured once would read a stale width.
    """
    for _ in range(2):
        value = _adapter(w)
        w.PW, w.PH, w.W, w.H = w.geom()
    return (_blocks_of(value),) + tuple(value[1:])


def _render_pill(w):
    """Render the pill through the port's own drawing entry point → (QImage, rect).

    Painting the pill rather than the whole widget keeps the pet sprite, the
    spike overlay and the fold button out of the picture, so a pixel difference
    in this image is a difference in the pill. The entry point is the port's, so
    both the layer that composites a mark and the layer that decides whether to
    composite one are inside the gate — defect (4) was a gate that covered only
    the first.
    """
    rect = w.pill_rect()
    if not rect:
        raise AssertionError("pill_rect() returned None in a pill-showing mode")
    x, y, pw_, ph_ = (int(v) for v in rect)
    img = QImage(max(1, x + pw_ + 8), max(1, y + ph_ + 8), QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w._draw_summary_pill(p)
    finally:
        p.end()
    return img, (x, y, pw_, ph_)


def _rgb(img, x, y):
    c = img.pixelColor(x, y)
    return (c.red(), c.green(), c.blue(), c.alpha())


def _ink(img, box, bg):
    """Pixels in `box` that are not the pill background — [(x, y, (r,g,b,a)), ...].

    "Not the background" is decided against the pill's own rendered background
    colour, sampled from the same image, rather than against a threshold this
    file invented. That matters: the failure being gated is differential (a mark
    that is the wrong colour vs. one that is the right colour), and a made-up
    cutoff would decide the outcome instead of the pixels.
    """
    x0, y0, bw, bh = box
    out = []
    for yy in range(y0, y0 + bh):
        for xx in range(x0, x0 + bw):
            px = _rgb(img, xx, yy)
            if px[3] < 8:
                continue
            if abs(px[0] - bg[0]) + abs(px[1] - bg[1]) + abs(px[2] - bg[2]) > 24:
                out.append((xx, yy, px))
    return out


def _dominant(ink):
    """The most common fully-opaque colour among these ink pixels, or None.

    Comparing the *whole* pixel list of two marks does not discriminate "the same
    file was drawn twice": the two marks sit at different sub-pixel offsets, so
    their antialiased edge pixels differ even when the shape is identical, and the
    lists compare unequal for a reason that has nothing to do with the marks. The
    solid interior colour is what actually identifies a mark, and it does not move
    with the offset.
    """
    counts = {}
    for _x, _y, px in ink:
        if px[3] >= 200:
            counts[px[:3]] = counts.get(px[:3], 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _nearest(px, palette):
    """Which of `palette`'s named colours this pixel is closest to. No threshold."""
    return min(palette.items(),
               key=lambda kv: sum(abs(px[i] - kv[1][i]) for i in range(3)))[0]


def _asset_colour(logo_name, size=None):
    """The dominant opaque colour of a logo asset, rendered straight from the file.

    Derived from the asset production ships (``SUMMARY_LOGO_FILES`` →
    ``bundled_logo_path``), never written down here. That matters for the indent
    gate below, whose whole job is to tell mark pixels from text pixels: a
    hardcoded terracotta would keep agreeing with itself after someone replaced
    the mark, and the gate would quietly stop finding the thing it looks for.
    """
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtCore import Qt as _Qt
    path = cp.bundled_logo_path(logo_name)
    if not path:
        return None
    n = int(size or cp.SUMMARY_LOGO_MARK)
    img = QImage(n, n, QImage.Format_ARGB32_Premultiplied)
    img.fill(_Qt.transparent)
    pa = QPainter(img)
    try:
        pa.setRenderHint(QPainter.Antialiasing, True)
        QSvgRenderer(path).render(pa)
    finally:
        pa.end()
    counts = {}
    for y in range(n):
        for x in range(n):
            c = img.pixelColor(x, y)
            if c.alpha() >= 200:
                k = (c.red(), c.green(), c.blue())
                counts[k] = counts.get(k, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else None


def _hex_rgb(h):
    c = QColor(h)
    return (c.red(), c.green(), c.blue())


class _QtCase(unittest.TestCase):
    """Base: Qt required, RUNTIME and OAUTH_STATUS restored, no user files touched."""

    def setUp(self):
        self.port = _require_qt(self)
        self._runtime = dict(cp.RUNTIME)
        self._oauth = dict(cp.OAUTH_STATUS)
        self.addCleanup(self._restore)
        cp.RUNTIME["mode"] = "subscription"
        cp.RUNTIME["credit_display"] = "money"
        cp.OAUTH_STATUS["auth_error"] = False

    def _restore(self):
        cp.RUNTIME.clear()
        cp.RUNTIME.update(self._runtime)
        cp.OAUTH_STATUS.clear()
        cp.OAUTH_STATUS.update(self._oauth)

    def _wide_first_line_window(self):
        """A window whose **widest drawn line is a value line**, not a reset line.

        The indent gate needs a provider whose first line very nearly fills its box,
        because ``_draw_runs`` centres each line: a line much narrower than its box
        keeps clear of the mark gutter even with the indent removed, and the gate
        then ties with the correct implementation.

        ``_two_provider_window`` stopped satisfying that once the core began folding
        reset lines at the 9.5pt font they are drawn in. The pill narrowed to fit its
        content, and the line that now sets the width is a **reset** line (302pt at
        9.5pt) while the widest value line is 268pt — 34pt short of what the gutter
        test needs. Nothing regressed; the fixture simply stopped being the shape the
        test is about.

        So this fixture makes a value line the widest line: longer gauge labels
        (a model name that is not one bare word, which is the account shape this
        already has to survive) and short countdowns, so the reset line cannot
        outgrow it. The pill's width is then set by a line that carries a mark, and
        ``widest_first + SUMMARY_LOGO_W > box`` holds by exactly the mark's width —
        structurally, not by a number tuned to this font.

        Measured here: value line 330pt, box 330pt, margin +18pt. The old fixture was
        268 against 302, margin -16.
        """
        rows = [("Session", 42.0, None, "1h"),
                ("Weekly", 17.0, None, "2h"),
                ("Fable 5.1 Opus", 12.0, None, "3h")]
        codex = [("codex_session", 68.0, None, "4h"),
                 ("codex_weekly", 23.0, None, "5h")]
        w = _make_window(self.port, oauth=list(rows))
        w.state["codex"] = list(codex)
        w.state["codex_summary"] = lambda: cp.roam_summary_codex(list(codex))
        return w

    def _two_provider_window(self):
        """Claude (3 gauges + resets) beside Codex (2 rows + resets).

        This fixture's whole job is to be **wider than the old cap**: measured
        with the port's own font its longest line needs more than ``PILL_W``
        and far less than the screen, so a pill that stops at 300 and a pill
        that follows its content give visibly different answers. A one-provider
        fixture cannot do that — it fits inside 300, where the bug and the fix
        agree.
        """
        w = _make_window(self.port, oauth=list(CLAUDE_OAUTH))
        w.state["codex"] = list(CODEX_ROWS)
        w.state["codex_summary"] = lambda: cp.roam_summary_codex(list(CODEX_ROWS))
        return w


# ═══════════════════════════════════════════════════════════════════════════════
# A — the pill follows its content, in both directions
# ═══════════════════════════════════════════════════════════════════════════════

class PillFollowsItsContentTests(_QtCase):
    """The cap is the screen, the height is the line count, and nothing is cut.

    Rivals, and what each returns for the two-provider fixture (longest line
    ≈338pt of text, 4 lines unfolded, offscreen screen 800pt wide):

    ===========================  ==============  ===========  =================
    implementation               pill width      pill height  lines
    ===========================  ==============  ===========  =================
    R1 ``W = PILL_W + 8``        300 (clamped)   46           5 (codex sub folds)
        — the shipped Qt line, and the macOS defect (1)
    R2 ``cp.pill_h()`` no arg    follows text    46           4, two of them
        — the four call sites at geom/roam_apply_display/                 clipped
          pill_rect/pet_origin
    R3 both R1 and R2            300             46           5, clipped
    R4 width follows, height     ≈382            78           4
       follows  (**correct**)
    ===========================  ==============  ===========  =================

    Note R1 and R2 are *independently* wrong and produce the same visible
    symptom — content that looks cut off. That is exactly why the height gate
    is separate from the width gate: with only a width gate, fixing the width
    leaves a green suite and a pill that still looks cut, and the next reader
    has no way to tell which of the two is left.

    The width assertion is a *relation*, not a recomputation: every line the
    port decided to draw has to fit in the pill the port decided to draw it in,
    both measured with the port's own font. Nothing here re-derives
    ``W - 2 * SUMMARY_EDGE``.
    """

    def test_every_line_fits_inside_the_pill_it_is_drawn_in(self):
        w = self._two_provider_window()
        blocks, _tw, _th = _settle(w)
        rect = w.pill_rect()
        self.assertIsNotNone(rect, "pill_rect() is None while the pill is showing")
        pill_w = rect[2]
        rows = _lines(blocks)
        self.assertTrue(rows, "the adapter produced no lines at all")
        # The limit is **production's own**, not this file's arithmetic. It used to
        # read `pill_w - 2 * PILL_PAD - SUMMARY_LOGO_W`, which is exactly the body of
        # _pill_text_budget() written out a second time — and the two copies agreed
        # through a mutation that changed the real one (see the module docstring).
        inner = w._pill_text_budget()
        self.assertLessEqual(
            inner, pill_w,
            "the fold budget (%.1fpt) exceeds the whole pill (%.1fpt) — the two come "
            "from different widths, which is how a line comes to start left of the "
            "pill and run off its right edge." % (inner, pill_w))
        for pid, line in rows:
            # **The font this line is drawn in, decided per line.** This test is named
            # for the pill the line is drawn in, and measuring every line at 11pt is
            # not that: a reset line is drawn at 9.5pt, so 11pt overstates it (measured
            # on the three-gauge English reset line: 346.0 against 302.0) and the gate
            # rejects a pill the content fits in.
            #
            # Per line, never per run. An inlined reset is a "sub" run sitting on a
            # gauge line, so it is drawn at 11pt with the rest of that line; choosing
            # the measure by run kind would size that fragment at 9.5pt and be wrong in
            # the other direction. The core folds by the same line-level rule and says
            # so in summary_lines; the draw code picks its font the same way. Three
            # places, one rule.
            font = _line_font(w, line)
            width = sum(w._text_w(text, font) for text, _k in line)
            self.assertLessEqual(
                width, inner + 0.5,
                "line %r (provider %s) is %.1fpt wide at the %.1fpt font it is drawn "
                "in, but the budget it was folded against gives it %.1fpt. The pill "
                "did not follow its content: either the cap is still a constant, or "
                "it is applied one layer above roam_pill_rect."
                % (_line_text(line), pid, width, font.pointSizeF(), inner))

    def test_the_pill_is_not_capped_at_the_old_constant(self):
        """The fixture needs more than PILL_W and the screen has room, so it must get it.

        Containment alone does **not** discriminate R1, and that is the trap
        worth naming: with the cap at 300 the content simply folds into more
        lines and every line then fits. A suite with only the containment test
        above is green on the shipped bug. This assertion is the one that goes
        red, because it asks the question the user asks — did the pill get
        wider — rather than the question folding can always answer yes to.
        """
        w = self._two_provider_window()
        blocks, tw, th = _settle(w)
        rect = w.pill_rect()
        screen = w._screen().geometry().width()
        # What width would this content get if the screen were unlimited? Asked of
        # **roam_pill_rect itself** by handing it a logical window nothing can clamp,
        # rather than by re-deriving `text_w + 2 * PILL_PAD` here. The clamp is the
        # subject of the test, so the unclamped answer must not be this file's opinion.
        need = cp.roam_pill_rect(w.roam_mode_now(), w.pet_on_right(), w.pet_on_bottom(),
                                 10 ** 6, w.PW, w.PH, w.pill_band(), tw, th)[2]
        self.assertGreater(
            need, cp.PILL_W,
            "fixture is too narrow to discriminate: it needs %.1fpt, which fits in "
            "PILL_W (%d), so a capped pill and an uncapped pill agree here. Widen "
            "the fixture." % (need, cp.PILL_W))
        self.assertLess(
            need, screen,
            "fixture is too wide to discriminate: it needs %.1fpt on a %dpt screen, "
            "so even a correct pill must fold." % (need, screen))
        self.assertGreaterEqual(
            rect[2], need - 0.5,
            "the pill is %.1fpt wide but its content needs %.1fpt, and the screen "
            "offers %dpt. PILL_W is %d — if the pill stopped there, the cap is still "
            "in force somewhere above roam_pill_rect (on macOS it was geom()'s "
            "`w = max(pet, PILL_W + 8)`; the Qt port has the same line)."
            % (rect[2], need, screen, cp.PILL_W))

    def test_no_line_is_folded_that_would_have_fit(self):
        """Over-folding is invisible to every width assertion, so it is asked directly.

        A line that was split too early **fits every budget** — that is what makes it
        undetectable by "does this line fit". The question has to be the other one:
        would two lines the port drew have fitted on one?

        **Measured in the font each line is actually drawn in.** The draw code picks
        ``F_SUMMARY_SUB`` for a line whose every run is ``"sub"`` and ``F_SUMMARY``
        otherwise; this test reads the same property off the same runs. Measuring a
        reset line with the body font is not a conservative approximation — it is a
        different number, and folding against it splits lines that fit.

        Adjacent pairs, not the whole stream: folding is greedy left to right, so
        "could these two have been one line" is the local question, and joining every
        line of a stream would pass trivially as soon as a stream legitimately needs
        three.

        ==========================================  ==========================
        implementation                              adjacent pair vs. budget
        ==========================================  ==========================
        R1 adapter folds sub lines with the body     pair **fits** — red
           font while drawing them in the sub font
        R2 adapter folds against a budget short by   pair **fits** — red
           the mark's width (the ``+ SUMMARY_LOGO_W``
           handed back is dropped)
        R3 folded in the font it is drawn in,        pair does not fit
           against the real budget (**correct**)
        ==========================================  ==========================

        Every number comes from production: the budget from ``_pill_text_budget()``,
        the fonts from the port, the measure from ``_text_w``, the separator from the
        core. This file computes none of them.
        """
        w = self._two_provider_window()
        blocks, _tw, _th = _settle(w)
        budget = w._pill_text_budget()
        self.assertGreater(budget, 0, "the fold budget is not a usable width")
        for pid, lines in blocks:
            for name, stream in _streams(lines):
                if len(stream) < 2:
                    continue          # one line cannot have been folded too early
                font = w.F_SUMMARY_SUB if name == "reset" else w.F_SUMMARY
                for a, b in zip(stream, stream[1:]):
                    joined = _line_text(a) + cp.SUMMARY_SEP + _line_text(b)
                    width = w._text_w(joined, font)
                    self.assertGreater(
                        width, budget + 0.5,
                        "provider %s split its %s content across two lines, but drawn "
                        "in the font it uses (%.1fpt) the two together are %.1fpt and "
                        "the budget is %.1fpt — they fitted. No width assertion can "
                        "see this: an over-folded line fits every budget. Check that "
                        "the measure handed to summary_lines is the font the line is "
                        "drawn in, and that the mark's width handed back to the "
                        "budget has not gone missing. a=%r b=%r"
                        % (pid, name, font.pointSizeF(), width, budget,
                           _line_text(a), _line_text(b)))

    def test_the_pill_height_follows_the_line_count(self):
        """Three or more lines must not be drawn into a two-line pill.

        ``cp.pill_h()`` with no argument is always the two-line height. The Qt
        port calls it that way in four places. With two providers the content is
        four lines, so the no-argument default is off by two line heights and
        the bottom half of the pill is simply not there.
        """
        w = self._two_provider_window()
        blocks, _tw, th = _settle(w)
        n = len(_lines(blocks))
        self.assertGreaterEqual(
            n, 3,
            "fixture produced %d lines; at 2 or fewer the no-argument pill_h() ties "
            "with the correct answer and this test proves nothing." % n)
        self.assertEqual(
            th, cp.pill_h(n),
            "the adapter reported height %s for %d lines, but pill_h(%d) is %s. "
            "pill_h() called with no argument returns the two-line height (%s)."
            % (th, n, n, cp.pill_h(n), cp.pill_h()))
        rect = w.pill_rect()
        self.assertGreaterEqual(
            rect[3], cp.pill_h(n) - 0.5,
            "the pill rect is %.1fpt tall for %d lines, which needs %s. A pill that "
            "is too short looks exactly like a pill that is too narrow, so this is "
            "gated apart from the width." % (rect[3], n, cp.pill_h(n)))

    def test_a_provider_with_nothing_to_say_leaves_no_line_and_no_gap(self):
        """Codex absent → a Claude-only pill, with no blank line and no stray mark.

        Rivals: a port that always emits two blocks leaves an empty Codex block
        (one bare mark, or a floating separator); a port that emits the segment
        only when the hook returns rows gives exactly one block. The user
        instruction this encodes is explicit: Claude only when Codex is absent,
        Codex only when Claude is absent.
        """
        w = _make_window(self.port, oauth=list(CLAUDE_OAUTH))
        w.state["codex"] = None
        w.state["codex_summary"] = lambda: None
        blocks, _tw, _th = _settle(w)
        ids = [pid for pid, _lines in blocks]
        self.assertEqual(
            ids, ["claude"],
            "with no Codex rows the pill must carry the Claude block and nothing "
            "else; got %r. An empty provider block draws a mark with no numbers "
            "beside it." % (ids,))
        for _pid, line in _lines(blocks):
            self.assertTrue(_line_text(line).strip(),
                            "a blank line reached the pill")


# ═══════════════════════════════════════════════════════════════════════════════
# B — the marks reach the pixels, in a colour the user can see
# ═══════════════════════════════════════════════════════════════════════════════

class ProviderMarksReachThePixelsTests(_QtCase):
    """Read the rendered image, not the source.

    This is the one class in the file that could not be written any other way.
    On macOS the tint was applied with ``setTemplate_(True)`` plus a context
    fill colour; the draw path consults neither, so the two lines together did
    nothing at all. Every source-reading test passed — the lines were *there*.
    The pixel histogram of a tinted render and an untinted render were
    byte-identical, and both were black, which on the near-black pill means the
    OpenAI mark was invisible. Qt has the same trap in a different spelling:
    ``setPen`` and ``setBrush`` do not affect bitmap compositing either.

    Rivals for the OpenAI mark, and what each puts in the mark box:

    =====================================  ============================
    implementation                         mark box contents
    =====================================  ============================
    R1 no mark drawn at all                pill background only
    R2 drawn, tint requested via pen/brush  near-black ink (invisible)
    R3 drawn, tinted into the pixels        ink nearest SUMMARY_LOGO_TINT
       (**correct**)
    R4 drawn, but claude.svg on both lines  ink, but identical to the
                                            Claude mark
    =====================================  ============================

    R1 and R2 are distinguished from R3 by *nearest production colour*, never by
    a cutoff this file invented: each ink pixel is classified against the pill
    background, black, and the tint, and the winner is asked. R4 is caught by
    comparing the two providers' mark boxes to each other — a comparison that
    needs no colour knowledge at all.
    """

    def _marks(self, w):
        """(image, pill rect, background colour, {provider: mark box}).

        The mark box is located from the layout contract the core documents —
        a provider's mark sits in the left gutter of that provider's **first**
        line, and every line of that provider is indented past it by
        ``SUMMARY_LOGO_W``. The gutter is read as a band rather than as an
        exact square, so a mark placed a pixel or two off still reads as a mark
        and this gate stays about colour and presence, which is what broke.
        """
        img, (x, y, pw_, ph_) = _render_pill(w)
        bg = _rgb(img, x + pw_ // 2, y + 2)[:3]
        rows = _lines(_blocks_of(_adapter(w)))
        n = len(rows)
        top = y + (ph_ - n * cp.SUMMARY_LINE_H) / 2.0
        boxes, seen = {}, set()
        for i, (pid, _line) in enumerate(rows):
            if pid in seen:
                continue
            seen.add(pid)
            cy = top + i * cp.SUMMARY_LINE_H + cp.SUMMARY_LINE_H / 2.0
            boxes[pid] = (int(x + cp.PILL_PAD) - 1,
                          int(cy - cp.SUMMARY_LOGO_MARK / 2.0) - 1,
                          cp.SUMMARY_LOGO_MARK + 2, cp.SUMMARY_LOGO_MARK + 2)
        return img, (x, y, pw_, ph_), bg, boxes

    def test_each_provider_line_carries_its_own_mark(self):
        w = self._two_provider_window()
        _settle(w)
        img, _rect, bg, boxes = self._marks(w)
        self.assertEqual(
            sorted(boxes), ["claude", "codex"],
            "expected a Claude block and a Codex block, got %r" % (sorted(boxes),))
        inks = {}
        for pid, box in boxes.items():
            ink = _ink(img, box, bg)
            self.assertTrue(
                ink,
                "the %s mark box is empty — every pixel in the gutter of that "
                "provider's first line is the pill background. Either no mark was "
                "drawn (%s is missing from the bundle, or the draw call is not "
                "wired) or it was drawn in the background colour."
                % (pid, cp.SUMMARY_LOGO_FILES.get(pid)))
            inks[pid] = _dominant(ink)
            self.assertIsNotNone(
                inks[pid], "the %s mark box has no opaque pixel at all" % pid)
        self.assertNotEqual(
            inks["claude"], inks["codex"],
            "both marks have the same solid colour %r — the same file was drawn on "
            "both lines. claude.svg is terracotta and carries its own colour; "
            "openai.svg is fill=\"currentColor\" and is tinted to %s. A provider "
            "lookup that ignores its argument gives both lines the first mark."
            % (inks["claude"], cp.SUMMARY_LOGO_TINT.get("codex")))

    def test_the_openai_mark_is_not_drawn_in_black(self):
        """openai.svg is fill="currentColor" — unset, it rasterises black and vanishes.

        The classification below has no invented threshold in it. Each ink pixel
        is handed three colours that all come from production — the pill
        background, black, and the declared tint — and asked which it is nearest
        to. "Black wins" is the shipped macOS bug; "background wins" is no mark
        at all; "tint wins" is the mark the user can see.
        """
        w = self._two_provider_window()
        _settle(w)
        img, _rect, bg, boxes = self._marks(w)
        tint = cp.SUMMARY_LOGO_TINT.get("codex")
        self.assertTrue(
            tint,
            "SUMMARY_LOGO_TINT declares no tint for codex, so this gate has nothing "
            "to check and would pass vacuously. openai.svg needs one.")
        palette = {"background": bg, "black": (0, 0, 0), "tint": _hex_rgb(tint)}
        ink = _ink(img, boxes["codex"], bg)
        self.assertTrue(ink, "the Codex mark box is empty")
        verdicts = [_nearest(px, palette) for _x, _y, px in ink]
        self.assertIn(
            "tint", verdicts,
            "not one pixel of the OpenAI mark is nearest to the declared tint %s. "
            "Verdicts: %r. If they are 'black', the tint was requested somewhere the "
            "draw path does not consult — on macOS that was setTemplate_ plus a "
            "context fill colour; in Qt setPen/setBrush do not touch bitmap "
            "compositing either. Pre-tint the mark into its own image instead."
            % (tint, sorted(set(verdicts))))
        self.assertGreater(
            verdicts.count("tint"), verdicts.count("black"),
            "more of the OpenAI mark is nearest to black than to the tint %s "
            "(%d black vs %d tint of %d ink pixels) — on the near-black pill that "
            "is an invisible mark."
            % (tint, verdicts.count("black"), verdicts.count("tint"), len(verdicts)))

    def test_the_text_is_indented_clear_of_its_own_mark(self):
        """A line that lost its indent fits *better*, so only position can catch it.

        This is the second of the two failures a width assertion can never see. An
        over-folded line at least fits; a line drawn without its indent fits with
        **room to spare**, so a width test is not merely silent about it, it is
        reassured. What the user sees is the mark and the first label on top of each
        other.

        Asked as a question about columns of ink, with no colour classification and
        no layout arithmetic beyond naming the gutter:

        * the mark's rows are the rows that carry ink in the pill's left gutter;
        * within those rows, find the rightmost inked column in the gutter;
        * immediately to its right there must be a column with **no ink at all** —
          the gap between the mark and the text it is indented away from.

        Colour was tried first and is not usable here: the mark's antialiased edge
        fades terracotta toward the pill background and passes within one unit of
        ``SUMMARY_COLORS["bad"]`` (measured: distance 134 to "bad" against 135 to the
        mark). A classifier that close to a coin-flip decides the test's outcome
        instead of the pixels.

        =============================================  =========================
        implementation                                 column right of the mark
        =============================================  =========================
        R1 block not indented past its mark            inked — text runs straight
           (``indented = x + PILL_PAD``)               through the gutter
        R2 indented by the mark's width (**correct**)  empty
        =============================================  =========================

        The precondition below is what keeps this honest: ``_draw_runs`` centres each
        line in its box, so a line much narrower than its box stays clear of the
        gutter even with the indent removed and would tie. The test asserts the
        provider it examines has a first line that nearly fills its box, and says so
        loudly if no provider does.
        """
        w = self._wide_first_line_window()
        blocks, _tw, _th = _settle(w)
        img, (x, y, pw_, ph_) = _render_pill(w)
        bg = _rgb(img, x + pw_ // 2, y + 2)[:3]
        gutter_end = x + cp.PILL_PAD + cp.SUMMARY_LOGO_W

        def inked(xx, yy):
            px = _rgb(img, xx, yy)
            return px[3] >= 8 and sum(abs(px[i] - bg[i]) for i in range(3)) > 24

        widest = max(sum(w._text_w(t_, _line_font(w, lines[0])) for t_, _k in lines[0])
                     for _pid, lines in blocks if lines)
        box = pw_ - 2 * cp.PILL_PAD - cp.SUMMARY_LOGO_W
        self.assertGreater(
            widest + cp.SUMMARY_LOGO_W, box,
            "no provider's first line comes within a mark's width of filling its box "
            "(widest %.1fpt, box %.1fpt). Every line is centred, so with the indent "
            "removed they would all still clear the gutter and this test would tie "
            "with the correct implementation.\n"
            "This trips when the widest drawn line is a *reset* line, which sets the "
            "pill's width while carrying no mark. Widen the fixture's gauge labels "
            "or shorten its countdowns until a value line is the widest one; do not "
            "relax this check, which is the only thing standing between a real gate "
            "and a green one that discriminates nothing."
            % (widest, box))

        rows = [yy for yy in range(y, y + ph_)
                if any(inked(xx, yy) for xx in range(x, gutter_end))]
        self.assertTrue(
            rows, "the pill's left gutter is empty on every row — no mark was drawn "
                  "at all, so there is nothing for the text to be indented away from")
        right = max(xx for yy in rows for xx in range(x, gutter_end) if inked(xx, yy))
        gap = [xx for xx in range(right + 1, x + pw_)
               if not any(inked(xx, yy) for yy in rows)]
        self.assertTrue(
            gap and gap[0] == right + 1,
            "the column immediately right of the mark (x=%d) carries ink on the "
            "mark's own rows, so the text was not indented past the mark — it is "
            "drawn over it. A width assertion cannot see this: an un-indented line "
            "was given *more* room, not less." % (right + 1))

    def test_a_single_provider_still_gets_its_mark(self):
        """One provider is not a reason to drop the mark.

        The rival here is a port that only draws marks when it has more than one
        provider to tell apart — a reasonable-sounding optimisation that makes
        the Claude-only pill (the common case) the one case with no mark, and
        silently changes the indentation that ``summary_lines`` already budgeted
        for.
        """
        w = _make_window(self.port, oauth=list(CLAUDE_OAUTH))
        w.state["codex"] = None
        w.state["codex_summary"] = lambda: None
        _settle(w)
        img, _rect, bg, boxes = self._marks(w)
        self.assertEqual(sorted(boxes), ["claude"])
        self.assertTrue(
            _ink(img, boxes["claude"], bg),
            "with Claude as the only provider its mark box is empty. The mark is "
            "not a disambiguator between providers; summary_lines reserves "
            "SUMMARY_LOGO_W for it whether there is one provider or two, so "
            "dropping it leaves the text indented past an empty gutter.")


# ═══════════════════════════════════════════════════════════════════════════════
# C — the six features reach the screen
# ═══════════════════════════════════════════════════════════════════════════════

class FeaturesReachTheScreenTests(_QtCase):
    """A pure function returning the right value is not the same as it being drawn.

    Every test here asserts on text that came back from the port's own adapter,
    so cutting the one line that passes the fact in turns it red. Testing the
    core function instead would stay green with the wiring removed, which is the
    exact shape of "the port has none of v0.26 while the core has all of it".
    """

    def _pill_text(self, w):
        blocks, _tw, _th = _settle(w)
        return "\n".join(_line_text(line) for _pid, line in _lines(blocks))

    def test_the_codex_row_reaches_the_pill(self):
        """Keyed on the provider id and on Codex-only values, never on the label.

        Asserting ``t("codex_session") in pill_text`` is about to become vacuous:
        once the provider prefix is dropped that label reads as the plain session
        label, which the Claude block prints too, so the assertion would be
        satisfied with the Codex block entirely absent. The two things that stay
        distinct are the block's provider id and the percentages only Codex has.
        """
        w = self._two_provider_window()
        blocks, _tw, _th = _settle(w)
        ids = [pid for pid, _lines in blocks]
        self.assertIn(
            "codex", ids,
            "no Codex block reached the pill (blocks: %r). The rows parse correctly "
            "in the core; what is missing is the segment being appended for the "
            "second provider." % (ids,))
        codex_text = "".join(_line_text(line)
                             for pid, lines in blocks if pid == "codex"
                             for line in lines)
        self.assertIn("68%", codex_text,
                      "the Codex session value is not in the Codex block: %r" % codex_text)
        self.assertIn("23%", codex_text,
                      "the Codex weekly value is not in the Codex block: %r" % codex_text)

    def test_the_codex_row_is_never_trimmed_away(self):
        """Whatever folding does, it does not delete the last provider.

        The macOS bug was ``roam_fit_runs`` at the draw site: it trims from the
        end, and the end is always the most recently added provider. The Qt port
        still calls ``roam_fit_runs`` in ``_draw_summary_pill``. Folding splits
        lines; trimming removes content — the difference is invisible on a wide
        screen and total on a narrow one, so this is checked by content rather
        than by line count.
        """
        w = self._two_provider_window()
        blocks, _tw, _th = _settle(w)
        joined = "".join(_line_text(line) for _pid, line in _lines(blocks))
        self.assertNotIn(
            "…", joined,
            "an ellipsis reached the pill: something trimmed instead of folding. "
            "summary_lines folds at run boundaries and loses no character; "
            "roam_fit_runs truncates, and what it truncates is always the last "
            "provider. Pill: %r" % joined)
        # A Codex-only value, not a label: the label stops being Codex-only when the
        # provider prefix is dropped, and this assertion would then be satisfied by
        # the Claude block.
        self.assertIn("23%", joined,
                      "the last Codex row did not survive to the pill: %r" % joined)

    def test_folding_never_deletes_the_last_provider(self):
        """Content wider than the screen folds; it does not get cut off the end.

        The previous test asks the same question with content the screen can hold,
        where **no implementation trims anything** — folding and trimming tie, and
        that test alone is green against the trimming bug. This one is the fixture
        that separates them: six Codex rows measure wider than this screen, so the
        pill genuinely cannot show them on one line and something has to give.

        =========================================  ===========================
        implementation                             result for this fixture
        =========================================  ===========================
        R1 roam_fit_runs at the draw site          last rows replaced by "…";
           (the shipped macOS bug)                 66% never drawn
        R2 summary_lines folds at run boundaries   every row present, on more
           (**correct**)                           lines
        =========================================  ===========================

        The distinguishing value is the **last** row's percentage. Trimming always
        eats the tail, and the tail is always the newest provider's last row —
        which is precisely why the Codex row was the one that never reached the
        screen on macOS.
        """
        # The fixture is **sized to this screen**, not to a row count that happened to
        # be wide enough on the machine it was written on. A literal count ties with
        # the correct implementation on any display wide enough to hold it, and the
        # tie is silent: the test still passes, having tested nothing. Rows are added
        # until the widest line genuinely exceeds the screen.
        w = _make_window(self.port, oauth=list(CLAUDE_OAUTH))
        screen_w = w._screen().geometry().width()

        def _rows(n):
            return [("codex_session" if i % 2 == 0 else "codex_weekly",
                     61.0 + i, None, "%dh %dm" % (i + 1, i * 7 + 3))
                    for i in range(n)]

        def _widest(rows_):
            seg = cp.roam_summary_codex(list(rows_))
            return max(sum(w._text_w(t_, w.F_SUMMARY) for t_, _k in runs)
                       for runs in cp.roam_summary_runs([seg], cp.t))

        n = 2
        while n < 64 and _widest(_rows(n)) <= screen_w:
            n += 2
        wide = _rows(n)
        # The last row's percentage is what trimming would eat, so it has to be unique.
        last_pct = "%d%%" % int(61.0 + (n - 1))
        self.assertEqual([r for _l, r, _d, _t in wide].count(61.0 + (n - 1)), 1,
                         "the distinguishing value is not unique in the fixture")
        w.state["codex"] = list(wide)
        w.state["codex_summary"] = lambda: cp.roam_summary_codex(list(wide))
        blocks, tw, _th = _settle(w)
        screen = w._screen().geometry().width()
        joined = "".join(_line_text(line) for _pid, line in _lines(blocks))
        unfolded = _widest(wide)
        self.assertGreater(
            unfolded, screen,
            "fixture is too narrow to discriminate: its widest line is %.1fpt on a "
            "%dpt screen, so nothing has to fold and trimming ties with folding. "
            "(%d rows were generated; the search caps at 64.)" % (unfolded, screen, n))
        self.assertNotIn(
            "…", joined,
            "an ellipsis reached the pill. summary_lines folds at run boundaries and "
            "loses no character; roam_fit_runs truncates, and what it truncates is "
            "always the tail. Pill: %r" % joined)
        self.assertIn(
            last_pct, joined,
            "the last Codex row is missing from the pill. Folding moves a row to "
            "another line; trimming deletes it, and the row it deletes is always the "
            "last one added. Pill: %r" % joined)
        self.assertGreater(
            len(_lines(blocks)), 4,
            "content wider than the screen produced no extra lines, so it was not "
            "folded at all — it is either overflowing the pill or being cut.")

    def test_credit_shows_money_and_follows_the_toggle(self):
        """The credit row carries an amount, and the menu toggle changes it.

        Rivals: a port that never passes ``credit_text`` renders the credit row
        as a percentage in both modes (the two modes tie, and a test that only
        checked one mode would pass); a port that hardcodes money ignores the
        toggle. Asserting that the two modes **differ**, and that money mode
        carries the amount, separates all three.
        """
        extra = {"used_credits": 10066.0, "monthly_limit": 20000.0,
                 "decimal_places": 2, "utilization": 50.33, "currency": "USD"}
        rows = list(CLAUDE_OAUTH) + [(cp.t("credit"), 50.33, None, None)]
        seen = {}
        for mode in ("money", "pct"):
            cp.RUNTIME["credit_display"] = mode
            w = _make_window(self.port, oauth=list(rows))
            w.state["credit_extra"] = dict(extra)
            w.state["credit_text"] = cp.credit_row_text(extra, mode)
            w.state["codex"] = None
            w.state["codex_summary"] = lambda: None
            seen[mode] = self._pill_text(w)
        self.assertIn(
            "100.66", seen["money"],
            "credit money mode does not show the amount. credit_row_text() returns "
            "%r for this payload; the adapter has to hand it to roam_summary as "
            "credit_text, which is the only way a row renders as anything but a "
            "percentage. Pill:\n%s"
            % (cp.credit_row_text(extra, "money"), seen["money"]))
        self.assertNotEqual(
            seen["money"], seen["pct"],
            "the credit row renders identically in money and pct mode, so the "
            "menu toggle reaches nothing. Both:\n%s" % seen["money"])

    def test_api_mode_says_the_key_was_rejected_instead_of_loading(self):
        """A rejected key must not keep reading "loading" forever.

        Rivals and what each shows with no cost number and a rejected key:
        a port that passes neither flag → ``loading`` (the shipped bug: the user
        never learns there is something for them to do); one that passes only
        ``api_stale`` → ``api_unreachable`` (wrong: it blames the network for a
        key problem); one that passes both → ``api_key_rejected``. All three
        strings differ, so this fixture separates them.
        """
        cp.RUNTIME["mode"] = "api"
        cp.RUNTIME["admin_key"] = "sk-ant-test"
        w = _make_window(self.port)
        w.state["cost"] = None
        w.state["api_error"] = True
        w.state["api_stale"] = False
        w.state["codex"] = None
        w.state["codex_summary"] = lambda: None
        text = self._pill_text(w)
        self.assertIn(
            cp.t("api_key_rejected"), text,
            "API mode with a rejected key shows %r, not the rejection. The fact "
            "lives in state; roam_summary only learns it if the adapter passes "
            "api_error=. 'loading' is only true while a lookup is still running."
            % text)
        self.assertNotIn(cp.t("loading"), text)

    def test_api_mode_separates_a_stale_lookup_from_a_rejected_key(self):
        """The two failures get different words, because the user's next move differs."""
        cp.RUNTIME["mode"] = "api"
        cp.RUNTIME["admin_key"] = "sk-ant-test"
        w = _make_window(self.port)
        w.state["cost"] = None
        w.state["api_error"] = False
        w.state["api_stale"] = True
        w.state["codex"] = None
        w.state["codex_summary"] = lambda: None
        text = self._pill_text(w)
        self.assertIn(
            cp.t("api_unreachable"), text,
            "a lookup that failed for a non-key reason shows %r. api_stale has to "
            "reach roam_summary separately from api_error — collapsing them tells "
            "a user with a network problem to go fix their key." % text)

    def test_token_expiry_marks_the_estimate_it_degraded_to(self):
        """The ⚠ tail, and it belongs on a gauge line, not on the reset line.

        Two ways to get this wrong, both of which happened on macOS: making the
        marker its own gauge row invents a ``≈0%`` that reads as "barely used",
        and appending it to ``lines[-1]`` puts it in the dim reset colour where
        it reads as a note about the reset time rather than about the numbers.
        """
        cp.OAUTH_STATUS["auth_error"] = True
        stats = {
            "entries": 12,
            "session": {"pct": 42.0, "reset": None},
            "weekly": {"pct": 17.0, "reset": None},
            "opus": {"pct": 12.0, "reset": None},
            "spikes": {}, "model_kw": "fable", "now": None,
        }
        w = _make_window(self.port, stats=stats)
        w.state["codex"] = None
        w.state["codex_summary"] = lambda: None
        blocks, _tw, _th = _settle(w)
        rows = _lines(blocks)
        marked = [(pid, line) for pid, line in rows if "⚠" in _line_text(line)]
        self.assertTrue(
            marked, "the token-expiry marker never reached the pill; lines were %r"
            % [_line_text(l) for _p, l in rows])
        pid, line = marked[0]
        self.assertEqual(pid, "claude", "the marker landed on the wrong provider")
        kinds = {kind for _text, kind in line}
        self.assertNotEqual(
            kinds, {"sub"},
            "the marker is on a line whose every run is 'sub' — that is the reset "
            "line, where it is drawn dim beside a countdown and reads as a comment "
            "on the reset time. It marks the numbers, so it belongs on the last "
            "gauge line.")
        self.assertNotIn(
            "⚠ ≈", _line_text(line),
            "the marker was rendered as its own gauge row, which invents a "
            "percentage that no measurement produced.")

    def test_auto_recovery_is_reachable_and_off_switch_is_honoured(self):
        """The recovery tick is driven from the port, and RUNTIME['auto_recover'] gates it.

        The pure decision function lives in the core and is already tested there.
        What this asserts is the part the port owns: that a recovery state
        object exists on the port's side and that the port passes the user's
        setting through. Rivals: a port that never calls ``recovery_tick``
        (nothing ever recovers); one that calls it with ``enabled=True``
        hardcoded (the menu item does nothing).
        """
        self.assertTrue(
            hasattr(cp, "recovery_tick") and hasattr(cp, "new_recovery_state"),
            "the core lost its recovery entry points")
        src = _text(PORT)
        self.assertIn(
            "recovery_tick", src,
            "windows/claude_pet_win.py never calls recovery_tick(). The core can "
            "decide to refresh a token all it likes; on Windows nothing asks it.")
        self.assertIn(
            "new_recovery_state", src,
            "the port never builds a recovery state, so recovery_tick() has "
            "nothing to carry between refreshes.")
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "recovery_tick"]
        self.assertTrue(calls, "recovery_tick appears in the source but is never called")
        gated = False
        for call in calls:
            for kw in call.keywords:
                if kw.arg == "enabled" and not (
                        isinstance(kw.value, ast.Constant) and kw.value.value is True):
                    gated = True
        self.assertTrue(
            gated,
            "every recovery_tick() call passes a literal enabled=True (or no "
            "enabled= at all), so the 'Auto-refresh token' menu item cannot turn it "
            "off. The setting is RUNTIME['auto_recover'].")


# ═══════════════════════════════════════════════════════════════════════════════
# D — the adapter's consumers agree with the adapter
# ═══════════════════════════════════════════════════════════════════════════════

class AdapterConsumersAgreeTests(_QtCase):
    """Calling the adapter and being able to use what it returns are two questions.

    macOS shipped a 3-tuple adapter with one of three consumers still unpacking
    four, which would have raised ``ValueError`` on the first paint. The Qt port
    has the same three consumers — ``roam_apply_display`` slices it,
    ``pill_rect`` unpacks it, ``_draw_summary_pill`` unpacks it — and they were
    written against the old 4-tuple. A test that only called the adapter would
    not have seen it.
    """

    def test_every_consumer_of_the_adapter_survives_one_frame(self):
        w = self._two_provider_window()
        _settle(w)
        for name in ("pill_rect", "pet_origin", "btn_origin"):
            with self.subTest(consumer=name):
                getattr(w, name)()
        img, _rect = _render_pill(w)
        self.assertGreater(img.width(), 0)

    def test_the_folded_mode_asks_the_adapter_for_nothing_it_cannot_give(self):
        """Folded draws no pill, but the geometry path still runs every frame."""
        w = self._two_provider_window()
        _settle(w)
        w.state["roam_mode"] = cp.DISPLAY_FOLDED
        w.state["roam_rects"] = None
        self.assertIsNone(
            w.pill_rect(),
            "pill_rect() returned a rect in folded mode — the pet would be drawn "
            "with a pill behind it")


# ═══════════════════════════════════════════════════════════════════════════════
# E — the logos actually ship
# ═══════════════════════════════════════════════════════════════════════════════

class BundleCarriesTheLogosTests(unittest.TestCase):
    """Both the builder's data list and the updater's layout check, or neither counts.

    ``fonts/`` has already made exactly this mistake once in this repository:
    present for a source run, absent from the bundle, and nothing noticed until
    a user saw the wrong glyphs. A mark that is missing from the bundle is
    worse, because the pill still draws and simply has a blank gutter.

    The vacuity guard is deliberate and is defect (6): the macOS release gate's
    logo loop was wrapped in ``getattr(..., {})``, so when the table came back
    empty the loop ran zero times and reported success. Every assertion below
    therefore proves its own input is non-empty first, against the core's table
    rather than against a list transcribed into this file.
    """

    def setUp(self):
        self.expected = set(cp.SUMMARY_LOGO_FILES.values())
        self.assertTrue(
            self.expected,
            "SUMMARY_LOGO_FILES is empty, so every check below would iterate zero "
            "times and pass without looking at anything. That is the shape of the "
            "release-gate bug this class exists to avoid.")

    def test_the_source_tree_has_the_files_the_core_names(self):
        for name in sorted(self.expected):
            with self.subTest(logo=name):
                path = os.path.join(ROOT, cp.SUMMARY_LOGO_DIR, name)
                self.assertTrue(os.path.isfile(path),
                                "%s is named by SUMMARY_LOGO_FILES but not in %s/"
                                % (name, cp.SUMMARY_LOGO_DIR))

    def test_the_builder_copies_the_logo_directory_into_the_bundle(self):
        """build_win.py's data list must carry logos/, read by AST, not by grep.

        A substring search for "logos" would match this module's own comment or
        a docstring. The data list is a literal, so it is read as one.
        """
        tree = ast.parse(_text(BUILDER))
        pairs = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == "data" for t in node.targets):
                continue
            if not isinstance(node.value, ast.List):
                continue
            for elt in node.value.elts:
                if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                    src = elt.elts[0]
                    if isinstance(src, ast.Constant) and isinstance(src.value, str):
                        pairs.append(src.value)
        self.assertTrue(
            pairs,
            "no literal `data = [...]` list of (src, dest) pairs found in "
            "build_win.py — this gate cannot see what the bundle carries, so it "
            "must fail rather than pass silently.")
        self.assertIn(
            cp.SUMMARY_LOGO_DIR, pairs,
            "build_win.py's PyInstaller data list is %r and does not include %r. "
            "bundled_logo_path() looks for logos/ beside the core, so without this "
            "entry a source run shows both marks and the bundle shows neither — "
            "the exact failure fonts/ had."
            % (pairs, cp.SUMMARY_LOGO_DIR))

    def test_the_updater_refuses_a_portable_tree_with_no_logos(self):
        """PORTABLE_REQUIRED must name each mark, so a broken zip is rejected, not installed.

        The builder's data list and this tuple are two independent doors. Only
        one of them being right is the silent case: the bundle is built correctly
        today and the first build that drops the entry is installed by every
        client without complaint.
        """
        import windows.win_update as wu
        required = getattr(wu, "PORTABLE_REQUIRED", ())
        self.assertTrue(
            required, "PORTABLE_REQUIRED is empty — every layout check passes vacuously")
        flat = {str(r).replace("/", os.sep).lower() for r in required}
        for name in sorted(self.expected):
            with self.subTest(logo=name):
                want = os.path.join("_internal", cp.SUMMARY_LOGO_DIR, name).lower()
                self.assertIn(
                    want, flat,
                    "PORTABLE_REQUIRED does not name %r. The updater would accept a "
                    "zip with no marks and swap it in; the pill then draws an empty "
                    "gutter and nothing reports why. Current entries: %r"
                    % (want, sorted(flat)))


# ═══════════════════════════════════════════════════════════════════════════════
# G — the label carries no provider prefix, and a lone gauge inlines its reset
# ═══════════════════════════════════════════════════════════════════════════════

class LabelsAndInlineResetTests(unittest.TestCase):
    """The two new display rules. Both are the core’s to implement.

    They are gated from the Windows suite because the Windows pill is where they are
    seen, and because the port has its own adapter: a core that gets this right and
    an adapter that flattens it back is exactly the split this file exists for.

    **Rule 1 — no provider prefix on the label.** ``codex_session`` and
    ``codex_weekly`` read as the plain session and weekly labels. What then tells a
    user whose 73% they are looking at is the **mark** — which is why the mark gates
    above stop being cosmetic the moment this lands. With the prefix gone, a Codex
    line drawn without its mark is indistinguishable from a Claude line.

    **Rule 2 — a provider with a single gauge row inlines its reset** on the value
    line, without the reset word: ``Weekly 73% · 5d 18h``. Two or more gauge rows
    keep the separate reset line and keep the word. The rule is not Codex-only; it
    applies to Claude on the same terms.

    Rivals for rule 2, with a one-row payload carrying a reset:

    ==========================================  ======  ===========  ==========
    implementation                              lines   reset word   countdown
    ==========================================  ======  ===========  ==========
    R1 always a separate reset line (current)   2       yes          yes
    R2 inlined, but the word comes with it      1       yes          yes
    R3 inlined, word dropped, and the           1       no           **no**
       countdown dropped with it
    R4 inlined, word dropped, countdown kept    1       no           yes
       (**correct**)
    ==========================================  ======  ===========  ==========

    No two rows agree on all three columns, so three assertions separate all four.
    Dropping any one lets a rival through: without the line count R1 survives,
    without the word check R2 survives, without the countdown check R3 survives —
    and R3 is the one that looks right in a screenshot of a pill whose reset happens
    to be far away.

    **Not gated here, deliberately:** a provider with one gauge row *and* a credit
    row. Credits are not a gauge (``SUMMARY_GAUGE_ROWS`` excludes them, and
    CLAUDE.md says so), which reads as "one gauge, so inline" — but the resulting
    line then carries two values and one countdown, and which of them the countdown
    belongs to is a question the layout cannot answer. That is a design decision,
    not a fact to derive, so it is flagged rather than guessed.
    """

    LOCALES = ("en", "ko", "ja", "es")

    def setUp(self):
        self._lang = cp.L["lang"]
        self.addCleanup(lambda: cp.L.__setitem__("lang", self._lang))

    @staticmethod
    def _runs(segment, provider="claude"):
        """One segment -> (value-line text, reset-line text, lines, gauge count).

        **Through ``summary_lines``, because that is the layer that inlines.**
        ``roam_summary_runs`` assembles one segment's runs and does not know whose
        they are or how many gauges the provider has; the inline rule is a
        provider-block rule and the core keeps it in ``summary_lines``. Asking
        ``roam_summary_runs`` whether a reset was inlined is asking a layer that was
        never given the question -- it answers "no" for every implementation, correct
        or not, which is a test that cannot pass.

        The budget is infinite so nothing folds: these tests are about the inline
        seam, and a fold would split lines for an unrelated reason and be read as one.
        ``len`` is the measure for the same reason -- no font, no Qt, no width has any
        bearing on the question being asked.

        Value lines and reset lines are separated by the rule the core folds by and
        the draw code picks fonts by: a line whose every run is "sub".
        """
        groups = [(provider, [segment])]
        blocks = cp.summary_lines(groups, len, float("inf"), len)
        lines = [line for _pid, block in blocks for line in block]
        value = "".join(t_ for line in lines if not _is_reset_line(line)
                        for t_, _k in line)
        reset = "".join(t_ for line in lines if _is_reset_line(line)
                        for t_, _k in line)
        return value, reset, lines, cp._summary_gauge_count([segment])

    # -- rule 1 --------------------------------------------------------------
    #
    # What these two tests are FOR changed when the core landed the rule, and saying
    # so matters more than the fact that they pass.
    #
    # They were written to catch drift between four hand-written locale tables. The
    # core did better than that: it derives the Codex label from the plain one, for
    # every locale, in a loop --
    #
    #     for _lang in TR:
    #         for _window in ("session", "weekly"):
    #             TR[_lang]["codex_" + _window] = TR[_lang][_window]
    #
    # -- so the four values cannot diverge, and the drift these tests were written to
    # catch is no longer expressible. The core's own comment says as much, and it is
    # right: a gate reports a divergence after the fact; a derivation prevents one.
    #
    # They are kept, with a narrower job: they pin the *contract* that the two read
    # alike, so that replacing the derivation with literals fails here. Mutation-
    # checked in that shape -- a literal override after the loop, for one locale and
    # for all four, turns both of them red. That is a smaller claim than the one they
    # were written for, and it is the honest one.
    def test_the_codex_labels_carry_no_provider_prefix(self):
        for lang in self.LOCALES:
            cp.L["lang"] = lang
            for codex_key, plain_key in (("codex_session", "session"),
                                         ("codex_weekly", "weekly")):
                with self.subTest(lang=lang, key=codex_key):
                    self.assertEqual(
                        cp.t(codex_key), cp.t(plain_key),
                        "%s in %r is %r but must read as the plain %r label (%r). "
                        "The provider is told by its mark now, not by a word glued "
                        "onto every row."
                        % (codex_key, lang, cp.t(codex_key), plain_key,
                           cp.t(plain_key)))

    def test_no_locale_is_left_with_the_old_prefix(self):
        """All four locales, because a change made in one is the likely miss."""
        stale = []
        for lang in self.LOCALES:
            cp.L["lang"] = lang
            for key in ("codex_session", "codex_weekly"):
                if "codex" in cp.t(key).lower():
                    stale.append((lang, key, cp.t(key)))
        self.assertEqual(
            stale, [], "these labels still name the provider: %r" % (stale,))

    # -- rule 2 --------------------------------------------------------------
    def test_a_lone_gauge_inlines_its_reset_without_the_reset_word(self):
        for lang in self.LOCALES:
            cp.L["lang"] = lang
            with self.subTest(lang=lang):
                main, sub, _lines, gauges = self._runs(
                    ("exact", [("Weekly", 73.0, False, "5d 18h")]))
                self.assertEqual(
                    gauges, 1,
                    "production counts %d gauge rows in this fixture, so it is not "
                    "the single-gauge case this test is about" % gauges)
                self.assertEqual(
                    sub, "",
                    "a provider with one gauge row still produced a separate reset "
                    "line (%r). With a single row there is nothing for a reset line "
                    "to disambiguate, so it belongs on the value line." % sub)
                self.assertIn("73%", main, "the value left the line")
                self.assertIn(
                    "5d 18h", main,
                    "the countdown is on no line at all. Inlining it is the rule; "
                    "dropping it is not, and a pill whose reset is far away looks "
                    "correct until the user needs it. main=%r" % main)
                self.assertNotIn(
                    cp.t("reset_prefix").strip(), main,
                    "the inlined reset kept the reset word (%r). The shape is "
                    "label, value, countdown. main=%r"
                    % (cp.t("reset_prefix"), main))
                # The reset run is "<label> <countdown>" because a reset *line* has
                # to pair each countdown with its gauge. Inlined next to that very
                # gauge there is nothing to pair, and keeping it reads as
                # "Weekly 73% - Weekly 5d 18h".
                self.assertEqual(
                    main.count("Weekly"), 1,
                    "the gauge label appears twice on the inlined line: %r" % main)

    def test_two_gauges_keep_the_separate_reset_line_and_the_word(self):
        for lang in self.LOCALES:
            cp.L["lang"] = lang
            with self.subTest(lang=lang):
                seg = ("exact", [("Session", 42.0, False, "3h 43m"),
                                 ("Weekly", 73.0, False, "5d 18h")])
                main, sub, _lines, gauges = self._runs(seg)
                self.assertEqual(
                    gauges, 2,
                    "production counts %d gauge rows, not the two this test needs"
                    % gauges)
                self.assertTrue(
                    sub,
                    "two gauge rows produced no reset line. Inlining two countdowns "
                    "on the value line gives four numbers in a row with nothing "
                    "saying which belongs to which.")
                self.assertTrue(
                    sub.startswith(cp.t("reset_prefix")),
                    "the reset line lost its opening word: %r does not start with "
                    "%r. The word is dropped only when the reset is inlined."
                    % (sub, cp.t("reset_prefix")))
                self.assertNotIn(
                    "5d 18h", main, "a countdown leaked onto the value line")
                self.assertIn("3h 43m", sub)
                self.assertIn("5d 18h", sub)

    def test_the_rule_is_symmetric_and_not_codex_only(self):
        """Claude with one gauge inlines exactly as Codex does.

        The rival is an implementation that special-cases the provider — easy to
        write, since Codex is where the one-row payload was first seen. Both
        segments below are built the same way and must render the same shape.
        """
        cp.L["lang"] = "ko"
        claude = ("exact", [("Weekly", 73.0, False, "5d 18h")])
        codex = cp.roam_summary_codex([("codex_weekly", 73.0, None, "5d 18h")])
        self.assertIsNotNone(codex, "roam_summary_codex dropped a usable row")
        c_main, c_sub, _a, c_n = self._runs(claude, provider="claude")
        x_main, x_sub, _c, x_n = self._runs(codex, provider="codex")
        self.assertEqual((c_n, x_n), (1, 1),
                         "both fixtures must be the single-gauge case; got %r"
                         % ((c_n, x_n),))
        self.assertEqual(
            (c_sub == "", x_sub == ""), (True, True),
            "one of the two providers still emits a reset line for a single gauge "
            "row: claude sub=%r codex sub=%r" % (c_sub, x_sub))
        self.assertTrue(c_main.endswith("5d 18h"), "claude: %r" % c_main)
        self.assertTrue(x_main.endswith("5d 18h"), "codex: %r" % x_main)

    def test_a_lone_gauge_with_no_reset_adds_nothing(self):
        """No reset to inline means no separator left dangling on the end."""
        cp.L["lang"] = "ko"
        main, sub, _lines, _n = self._runs(
            ("exact", [("Weekly", 73.0, False, None)]))
        self.assertEqual(sub, "")
        self.assertFalse(
            main.rstrip().endswith(cp.SUMMARY_SEP.strip()),
            "the value line ends in a separator with nothing after it: %r" % main)
        self.assertTrue(main.endswith("73%"), "main=%r" % main)


# ═══════════════════════════════════════════════════════════════════════════════
# F — the Codex lane comes from the window length, not from the key name
# ═══════════════════════════════════════════════════════════════════════════════

class CodexLaneComesFromWindowLengthTests(unittest.TestCase):
    """The observed account put its 7-day window in ``primary_window``.

    This is not a hypothetical. On 2026-09-20 the lane was chosen by key name —
    ``primary_window`` → session, ``secondary_window`` → weekly — and the
    observed account's ``primary_window.limit_window_seconds`` was 604800. The
    screen read "Codex session 68%" for what was in fact 68% of the week. A
    missing row is visibly missing; a mislabelled row looks correct, so nothing
    but a test at this exact shape finds it.

    The fixture inverts the keys — the 7-day window in ``primary``, the 5-hour
    window in ``secondary`` — which is what makes it discriminating:

    ==========================================  ==========================
    implementation                              rows for this payload
    ==========================================  ==========================
    R1 key name → lane (the shipped bug)        primary=session(23%),
                                                secondary=weekly(68%)
    R2 key name → lane, with the mapping        primary=weekly(23%),
       simply swapped                           secondary=session(68%)
    R3 window length → lane (**correct**)       session=68%, weekly=23%
    ==========================================  ==========================

    R2 is the reason the percentages differ between the two windows and the
    fixture is inverted: a patch that just swaps the two key names produces R2,
    which matches neither R1 nor R3. Had both windows carried the same
    percentage, R2 and R3 would tie and the fixture would prove nothing.
    """

    PAYLOAD = {
        "rate_limit": {
            # 7 days — a weekly window, sitting in the key named "primary".
            "primary_window": {"limit_window_seconds": 604800,
                               "used_percent": 23.0, "reset_at": None},
            # 5 hours — a session window, sitting in the key named "secondary".
            "secondary_window": {"limit_window_seconds": 18000,
                                 "used_percent": 68.0, "reset_at": None},
        }
    }

    def test_the_label_follows_the_window_length(self):
        rows = cp.parse_codex_usage(self.PAYLOAD)
        self.assertIsNotNone(rows, "both windows were discarded")
        got = {label: pct for label, pct, _dt, _txt in rows}
        self.assertEqual(
            got, {"codex_session": 68.0, "codex_weekly": 23.0},
            "lane assignment came from the key name, not from "
            "limit_window_seconds. The 18000s window is the session and the "
            "604800s window is the week, whichever key holds them. Got %r" % (got,))

    def test_the_order_is_session_then_weekly_whatever_the_payload_order(self):
        rows = cp.parse_codex_usage(self.PAYLOAD)
        self.assertEqual(
            [r[0] for r in rows], ["codex_session", "codex_weekly"],
            "row order follows the payload's key order, so the same two windows "
            "appear in a different order on different accounts")

    def test_a_window_of_unknown_length_is_dropped_not_guessed(self):
        """A 2-day window belongs to no lane; naming it 'session' would be a lie."""
        payload = {"rate_limit": {
            "primary_window": {"limit_window_seconds": 2 * 86400,
                               "used_percent": 55.0, "reset_at": None},
        }}
        self.assertIsNone(
            cp.parse_codex_usage(payload),
            "a window whose length matches no lane was kept and labelled. There is "
            "no basis for either name, and a percentage the user cannot attribute "
            "to a window is worse than no row.")

    def test_one_window_accounts_still_produce_a_row(self):
        """`secondary_window: None` is the observed normal shape, not an error."""
        payload = {"rate_limit": {
            "primary_window": {"limit_window_seconds": 604800,
                               "used_percent": 23.0, "reset_at": None},
            "secondary_window": None,
        }}
        rows = cp.parse_codex_usage(payload)
        self.assertEqual([r[0] for r in rows], ["codex_weekly"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
