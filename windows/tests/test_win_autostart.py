"""Gating tests for the Windows "Start at sign-in" toggle (Track B, Windows half, 2026-09-13).

Run from the worktree root:

    python3 -m unittest discover -s windows/tests -t . -v

Verifier-owned (AGENTS.md §2 Condition A). The Developer provides
``windows/win_autostart.py`` — importable on macOS as ``windows.win_autostart``
and by the port as ``win_autostart`` — plus the Qt wiring in
``windows/claude_pet_win.py`` and a README paragraph, and must not touch the
assertions or fixtures here. ``claude_pet.py`` is not edited by this track:
the six TR keys it already carries (``menu_autostart``, ``autostart_title``,
``autostart_approval``, ``autostart_open_settings``, ``autostart_fail``,
``autostart_unavailable``) are what the Windows half uses, so the two halves
read identically in the menu — same key, same position.

Surface pinned (the fixed design), and nothing else in the port:

    run_value_for(exe)                                -> '"<exe>"'
    startup_approved_enabled(blob)                    -> bool
    autostart_read_state(reader, exe, is_frozen)      -> "on" | "off" | "unavailable"
    autostart_toggle(reader, writer, exe, is_frozen)  -> (new_state, "autostart_fail" | None)
    RUN_SUBKEY / RUN_VALUE_NAME / STARTUP_APPROVED_SUBKEY      module constants
    registry_reader(subkey, name) / registry_writer(subkey, name, data)
                                                      the thin winreg adapter (imports winreg at call time)
    real_registry()                                   -> (registry_reader, registry_writer) on win32,
                                                         (None, None) anywhere else — read at call time

The seam — how the pure functions see the registry. Both callables are
positional, and they are the *only* way the module reaches HKCU:

* ``reader(subkey, name)`` returns the value (``str`` for the REG_SZ Run
  value, ``bytes`` for the REG_BINARY StartupApproved blob) or **``None`` when
  the key or the value does not exist**, and raises for anything else. The
  distinction is the design: "absent" is a state (``"off"``), "raised" is not
  (``"unavailable"``). ``winreg`` reports absence as ``FileNotFoundError``,
  so the real adapter translates that one exception into ``None`` — the
  adapter tests say so with a fake ``winreg`` module.
* ``writer(subkey, name, data)`` sets the value when ``data`` is a ``str``
  (REG_SZ) and deletes the value when ``data is None``. It returns nothing
  and raises on failure.

Both are called with the literal locations the installer uses —
``Software\\Microsoft\\Windows\\CurrentVersion\\Run`` / ``ClaudePet`` — and the
Explorer ``StartupApproved\\Run`` mirror of the same value name. The fixtures
key their dicts on those literals, so an implementation that reads any other
location sees an empty registry and fails every "on" row.

What the port must do (AST pins, because the port cannot be imported here —
PySide6, Pillow and winreg are absent on this host): a checkable
``QAction(cp.t("menu_autostart"), …)`` added to the right-click menu
immediately after the roam action and before ``menu_reset_size`` (the macOS
``rightMouseDown_`` order, checked side by side); ``<menu>.aboutToShow``
connected to a slot that calls ``autostart_read_state`` and sets
checked / enabled / text (``cp.t("autostart_unavailable")`` when
unavailable); ``triggered`` connected to a slot that calls
``autostart_toggle`` and shows the existing message-box helper with
``cp.t("autostart_title")`` / ``cp.t("autostart_fail")`` on failure; the
frozen flag, the executable and ``real_registry()`` handed over; no config
key anywhere; none of the six keys overridden in ``TR_WIN``.

``CLAUDE_PET_WIN_PORT_SOURCE`` points the port pins at another copy of the
port (the convention test_win_update.py established for observing RED
against retained bytes); the override is announced on stderr with the
file's SHA-256 so it is never silent.

Every class docstring carries the AGENTS.md §3 truth table for its fixtures:
the rivals are the implementations someone would plausibly write — the
brief names five of them (unquoted value, case-sensitive compare, ignore
StartupApproved, persisted config key wins, from-source registers pythonw) —
and each fixture is chosen so that no rival collapses onto the expected value.
"""

import ast
import hashlib
import importlib
import json
import ntpath
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import windows.win_core as win_core  # noqa: E402  — the ONE owner of the core import

# The core, through `import_core()` and never bare. `claude_pet.py` dies on Windows at
# `import fcntl` and then at `ctypes.CDLL(None)`; `windows/README.md` names this helper as
# the single place both detours live. A bare `import claude_pet` here collected fine on
# macOS and killed this whole module at collection time on the real target — which is the
# one host whose answers count for a Windows port.
cp = win_core.import_core()  # noqa: E402  — the core (TR keys, config surface)
import windows.win_update as wu  # noqa: E402  — the updater's registry names the toggle must share

MODULE = "windows.win_autostart"
PORT_SOURCE_ENV = "CLAUDE_PET_WIN_PORT_SOURCE"

RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "ClaudePet"
APPROVED_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

EXE = r"C:\Users\x\AppData\Local\Programs\ClaudePet\ClaudePet.exe"
EXE_UPPER = EXE.upper()
EXE_SPACES = r"C:\Program Files\Claude Pet\ClaudePet.exe"
OTHER_EXE = r"D:\Tools\ClaudePet\ClaudePet.exe"

ENABLED = bytes([0x02]) + bytes(11)                                  # 02 00 … 00
DISABLED = bytes([0x03, 0, 0, 0]) + bytes.fromhex("1032547698badcfe")  # 03 00 00 00 + FILETIME

AUTOSTART_KEYS = ("menu_autostart", "autostart_title", "autostart_approval",
                  "autostart_open_settings", "autostart_fail", "autostart_unavailable")
LOCALES = ("en", "ko", "ja", "es")
# The neighbourhood this test's name claims: autostart sits between "roam the screen"
# and "reset size", with nothing between them.
#
# This used to be a *quintet* — the two items that happened to precede roam were pinned
# alongside it, and the assertion took a fixed five-wide window around roam. v0.26
# inserted two new items ("credits in money", "auto-refresh token") before roam on both
# platforms, which slid that window two places left and turned the test red against a
# menu that was in fact correct. The five-wide window was never the claim; it was an
# accident of how many items happened to sit to the left at the time.
#
# What is durable is stated in two pieces below (see the test): the triple is contiguous
# on each platform, and the two platforms order every menu key they share identically.
# The second piece is what actually protects a port — it needs no literal here, so it
# cannot go stale, and it still fails the moment Windows puts an item somewhere macOS
# does not.
MENU_TRIPLE = ["menu_roam", "menu_autostart", "menu_reset_size"]


def _mod():
    """Import lazily so a missing module fails each gate on its own line."""
    return importlib.import_module(MODULE)


def _quoted(exe):
    return '"' + exe + '"'


# ───────────────────────────── fakes: a dict-backed HKCU ─────────────────────────────

class _Registry:
    """Dict-backed HKCU that records every call.

    ``values``: ``{(subkey, name): data}``. ``reader(subkey, name)`` returns
    the data or ``None`` when absent; ``writer(subkey, name, data)`` sets on a
    ``str`` and deletes on ``None``. ``read_exc`` / ``write_exc`` is an
    exception instance raised by every call, or a ``{subkey: exception}``
    dict raised only for that subkey. The writer raises *before* it mutates,
    so a failed write leaves the registry exactly as it was.
    """

    def __init__(self, values=None, read_exc=None, write_exc=None):
        self.values = dict(values or {})
        self.read_exc, self.write_exc = read_exc, write_exc
        self.calls = []

    @staticmethod
    def _exc_for(spec, subkey):
        if spec is None:
            return None
        if isinstance(spec, dict):
            return spec.get(subkey)
        return spec

    def reader(self, subkey, name):
        self.calls.append(("read", subkey, name))
        exc = self._exc_for(self.read_exc, subkey)
        if exc is not None:
            raise exc
        return self.values.get((subkey, name))

    def writer(self, subkey, name, data):
        self.calls.append(("delete", subkey, name) if data is None else ("set", subkey, name, data))
        exc = self._exc_for(self.write_exc, subkey)
        if exc is not None:
            raise exc
        if data is None:
            self.values.pop((subkey, name), None)
        else:
            self.values[(subkey, name)] = data

    @property
    def reads(self):
        return [c for c in self.calls if c[0] == "read"]

    @property
    def writes(self):
        return [c for c in self.calls if c[0] != "read"]

    def run(self):
        return self.values.get((RUN_SUBKEY, RUN_VALUE))

    def approved(self):
        return self.values.get((APPROVED_SUBKEY, RUN_VALUE))


def _reg(run=None, approved=None, **kw):
    values = {}
    if run is not None:
        values[(RUN_SUBKEY, RUN_VALUE)] = run
    if approved is not None:
        values[(APPROVED_SUBKEY, RUN_VALUE)] = approved
    return _Registry(values, **kw)


class _ConfigGuard:
    """A rogue persisted preference that must neither be read nor written.

    ``cp.CONFIG_PATH`` → a temp file holding ``"autostart": true``; ``RUNTIME``
    carries the same rogue key; ``HOME`` / ``USERPROFILE`` → the temp dir. On
    exit the file's bytes and ``RUNTIME`` must be exactly what they were.
    """

    def __init__(self, test):
        self.test = test

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="cpw-autostart-")
        self.test.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, ".claude_pet.json")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"autostart": True, "roam": False}, f)
        self.before = self._fingerprint()
        self.patches = [
            mock.patch.object(cp, "CONFIG_PATH", self.path),
            mock.patch.dict(os.environ, {"HOME": self.tmp, "USERPROFILE": self.tmp}),
            mock.patch.dict(cp.RUNTIME, {"autostart": True}),
        ]
        for p in self.patches:
            p.start()
        self.runtime_before = dict(cp.RUNTIME)
        return self

    def __exit__(self, *exc):
        runtime_after = dict(cp.RUNTIME)
        for p in reversed(self.patches):
            p.stop()
        self.test.assertEqual(self._fingerprint(), self.before, "the config file was rewritten")
        self.test.assertEqual(runtime_after, self.runtime_before, "RUNTIME was changed")
        self.test.assertEqual(sorted(os.listdir(self.tmp)), [".claude_pet.json"],
                              "something was created in HOME")
        return False

    def _fingerprint(self):
        with open(self.path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


# ═══════════════════════════════════ run_value_for ═══════════════════════════════════

def _installer_run_entry():
    """The installer's [Registry] Run line as {subkey, value_name, value_data, flags, exe_name}.

    Inno quoting: a parameter is one double-quoted string in which ``""`` is a
    literal ``"``. ``ValueData: \"\"\"{app}\\{#MyAppExeName}\"\"\"`` therefore
    writes the path inside one pair of double quotes.
    """
    with open(os.path.join(ROOT, "windows", "installer.iss"), encoding="utf-8") as f:
        text = f.read()
    exe_name = re.search(r'#define MyAppExeName "([^"]+)"', text).group(1)
    line = next(l for l in text.splitlines()
                if l.startswith("Root: HKCU") and "CurrentVersion\\Run\"" in l)

    def field(name):
        m = re.search(name + r': "((?:[^"]|"")*)"', line)
        return m.group(1).replace('""', '"') if m else None

    flags = re.search(r"Flags: ([^;]+)", line)
    return {"subkey": field("Subkey"), "value_name": field("ValueName"), "value_data": field("ValueData"),
            "flags": flags.group(1).split() if flags else [], "exe_name": exe_name}


class RunValueTests(unittest.TestCase):
    """run_value_for(exe) -> the exact REG_SZ the installer writes: ``"<exe>"``.

    installer.iss ``[Registry]``: ``ValueData: \"\"\"{app}\\{#MyAppExeName}\"\"\"`` —
    in Inno's quoting that is one pair of double quotes around the path. The
    toggle, the installer's checkbox and ``uninsdeletevalue`` then act on one
    value in one format, and ``wu.run_value_is_ours`` (what the port's
    ``delete_run_value_if_ours`` consults) must accept what the toggle wrote.

    Rivals: BARE = the path alone, SQ = single quotes, DBL = Inno's literal
    ``""…""`` copied verbatim, ARGS = a trailing argument, LOWER = normcased.

    | exe                              | BARE | SQ   | DBL    | ARGS      | LOWER  | **expected** |
    | C:\\…\\ClaudePet.exe              | p    | 'p'  | ""p""  | "p" --x   | "c:…"  | **"p"**      |
    | C:\\Program Files\\…\\ClaudePet.exe| p    | 'p'  | ""p""  | "p" --x   | "c:…"  | **"p"**      |
    | round trip run_value_is_ours     | True | False| False  | True      | True   | **True**     |

    BARE, ARGS and LOWER survive the round trip (``run_value_is_ours`` is
    tolerant by design), which is why the first two rows compare the string
    byte for byte against the installer's own expansion.
    """

    def test_quoted_once_with_double_quotes(self):
        wa = _mod()
        for exe in (EXE, EXE_SPACES, OTHER_EXE):
            with self.subTest(exe=exe):
                self.assertEqual(wa.run_value_for(exe), _quoted(exe))

    def test_matches_the_installer_registry_line(self):
        wa = _mod()
        entry = _installer_run_entry()
        self.assertEqual(entry["subkey"], RUN_SUBKEY)
        self.assertEqual(entry["value_name"], RUN_VALUE)
        self.assertIn("uninsdeletevalue", entry["flags"])
        self.assertEqual(entry["exe_name"], "ClaudePet.exe")
        app = EXE.rsplit("\\", 1)[0]                     # {app} — ntpath dirname, host-independent
        expanded = entry["value_data"].replace("{#MyAppExeName}", entry["exe_name"]).replace("{app}", app)
        self.assertEqual(expanded, _quoted(EXE), "the installer line does not expand to one quoted path")
        self.assertEqual(wa.run_value_for(EXE), expanded)

    def test_what_the_toggle_writes_the_uninstaller_recognises(self):
        wa = _mod()
        for exe in (EXE, EXE_SPACES):
            with self.subTest(exe=exe):
                self.assertTrue(wu.run_value_is_ours(wa.run_value_for(exe), exe))
        self.assertFalse(wu.run_value_is_ours(wa.run_value_for(OTHER_EXE), EXE))

    def test_shares_the_updaters_registry_names(self):
        wa = _mod()
        self.assertEqual(wa.RUN_SUBKEY, RUN_SUBKEY)
        self.assertEqual(wa.RUN_SUBKEY, wu.RUN_SUBKEY)
        self.assertEqual(wa.RUN_VALUE_NAME, RUN_VALUE)
        self.assertEqual(wa.RUN_VALUE_NAME, wu.RUN_VALUE_NAME)
        self.assertEqual(wa.STARTUP_APPROVED_SUBKEY, APPROVED_SUBKEY)


# ═════════════════════════════ startup_approved_enabled ═════════════════════════════

class StartupApprovedTests(unittest.TestCase):
    """startup_approved_enabled(blob) -> bool — the one place the byte encoding lives.

    Task Manager › Startup apps does not delete the Run value when the user
    disables an app; it writes a REG_BINARY under
    ``HKCU\\…\\Explorer\\StartupApproved\\Run`` with the Run value's name:
    first byte ``0x02`` = enabled, ``0x03`` = disabled (the rest is padding
    and, when disabled, a FILETIME). That encoding is from memory and is to be
    confirmed on hardware — which is why it is isolated in one function; if
    the hardware check moves a byte, this table and that function change
    together and nothing else does.

    Fail-safe direction for anything else: *not* enabled. A blob this code
    cannot read is not evidence that Windows will launch us; the menu then
    reads "off" and the next click deletes the entry (absent = enabled), which
    is the self-healing path. The opposite mistake — an unreadable blob read
    as enabled — shows a checkmark Windows does not honour and gives the user
    no click that fixes it.

    Rivals: NE3 = ``blob[0] != 0x03``, TRUTHY = ``bool(blob)``,
    EQ = ``blob == b"\\x02"``, LEN = ``len(blob) == 12``.

    | blob                        | NE3        | TRUTHY | EQ    | LEN       | **expected** |
    | 02 00…00 (12 bytes)         | True       | True   | False | True      | **True**     |
    | 03 00 00 00 + FILETIME      | False      | True   | False | True      | **False**    |
    | 02 (1 byte)                 | True       | True   | True  | False     | **True**     |
    | b""                         | IndexError | False  | False | False     | **False**    |
    | None                        | TypeError  | False  | False | TypeError | **False**    |
    | "\\x02" (str, wrong type)    | True       | True   | False | False     | **False**    |
    """

    def test_table(self):
        wa = _mod()
        rows = [
            (ENABLED, True),
            (DISABLED, False),
            (bytes([0x02]), True),
            (b"", False),
            (None, False),
            ("\x02", False),
        ]
        for blob, expected in rows:
            with self.subTest(blob=blob):
                self.assertIs(wa.startup_approved_enabled(blob), expected)


# ═══════════════════════════════ autostart_read_state ═══════════════════════════════

class ReadStateTests(unittest.TestCase):
    """autostart_read_state(reader, exe, is_frozen) -> "on" | "off" | "unavailable".

    "on" iff all of: a frozen build; a Run value present whose unquoted path
    equals ``exe`` under Windows semantics (``ntpath.normcase``); and the
    StartupApproved blob absent or enabled. Value absent, a foreign path, or
    a disabled blob → "off". Not frozen → "unavailable" without a single
    registry read (from source ``sys.executable`` is ``pythonw.exe`` — never
    ours to register, the macOS guard's shape). A reader that raises →
    "unavailable" (a registry we cannot read is not a state). ``reader is
    None`` or no exe → "unavailable", no call.

    Rivals: UNQ = compare the raw value (quotes and all), CASE = compare
    case-sensitively (``os.path.normcase`` is the identity on this host),
    PRESENT = any value is "on", IGN-SA = ignore StartupApproved, SA-OFF =
    any StartupApproved entry means disabled, NOFRZ = ignore is_frozen,
    RAISE = let the reader's exception out, CFG = a persisted "autostart"
    config key wins.

    | #  | frozen | Run value           | Approved     | UNQ | CASE | PRESENT | IGN-SA | SA-OFF | NOFRZ | RAISE  | CFG | **expected**    |
    | 1  | yes    | absent              | absent       | off | off  | off     | off    | off    | off   | off    | on  | **off**         |
    | 2  | yes    | "<exe>"             | absent       | off | on   | on      | on     | on     | on    | on     | on  | **on**          |
    | 3  | yes    | "<EXE UPPER-CASED>" | absent       | off | off  | on      | on     | on     | on    | on     | on  | **on**          |
    | 4  | yes    | <exe> (no quotes)   | absent       | on  | on   | on      | on     | on     | on    | on     | on  | **on**          |
    | 5  | yes    | "<other exe>"       | absent       | off | off  | on      | off    | off    | off   | off    | on  | **off**         |
    | 6  | yes    | "<exe>"             | 03… disabled | off | on   | on      | on     | off    | off   | off    | on  | **off**         |
    | 7  | yes    | "<exe>"             | 02… enabled  | off | on   | on      | on     | off    | on    | on     | on  | **on**          |
    | 8  | yes    | absent              | 02… enabled  | off | off  | off     | off    | off    | off   | off    | on  | **off**         |
    | 9  | no     | "<exe>"             | absent       | —   | —    | —       | —      | —      | on    | —      | —   | **unavailable** (no read) |
    | 10 | yes    | reader raises       | —            | —   | —    | —       | —      | —      | —     | raises | —   | **unavailable** |
    | 11 | yes    | b"\\x01" (not str)   | absent       | off | off  | on      | off    | off    | off   | off    | on  | **off**         |

    Row 1 runs again with a rogue ``"autostart": true`` in the config file
    and in ``RUNTIME`` — that is the CFG column. UNQ is wrong on 2 (and only
    right on 4), CASE on 3, PRESENT on 5, IGN-SA on 6, SA-OFF on 7, NOFRZ on
    9, RAISE on 10, CFG on 1 — every rival falls on at least one row.
    """

    ROWS = [
        # (label, run, approved, expected)
        ("1 absent/absent", None, None, "off"),
        ("2 ours quoted", _quoted(EXE), None, "on"),
        ("3 ours upper-cased", _quoted(EXE_UPPER), None, "on"),
        ("4 ours unquoted", EXE, None, "on"),
        ("5 foreign path", _quoted(OTHER_EXE), None, "off"),
        ("6 ours but disabled in Task Manager", _quoted(EXE), DISABLED, "off"),
        ("7 ours and enabled", _quoted(EXE), ENABLED, "on"),
        ("8 enabled blob without a Run value", None, ENABLED, "off"),
        ("11 non-string value", b"\x01", None, "off"),
    ]

    def test_state_table(self):
        wa = _mod()
        self.assertNotEqual(EXE, EXE_UPPER, "fixture must actually differ in case")
        self.assertEqual(ntpath.normcase(EXE), ntpath.normcase(EXE_UPPER))
        for label, run, approved, expected in self.ROWS:
            with self.subTest(row=label):
                reg = _reg(run=run, approved=approved)
                self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), expected)
                self.assertEqual(reg.writes, [], "reading the state must not write")

    def test_reads_only_the_installers_two_locations(self):
        wa = _mod()
        reg = _reg(run=_quoted(EXE), approved=ENABLED)
        self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), "on")
        self.assertEqual({(s, n) for _, s, n in reg.reads},
                         {(RUN_SUBKEY, RUN_VALUE), (APPROVED_SUBKEY, RUN_VALUE)})

    def test_source_run_is_unavailable_and_reads_nothing(self):
        wa = _mod()
        for frozen in (False, None, 0):
            with self.subTest(is_frozen=frozen):
                reg = _reg(run=_quoted(EXE))
                self.assertEqual(wa.autostart_read_state(reg.reader, EXE, frozen), "unavailable")
                self.assertEqual(reg.calls, [], "from source the registry is never consulted")

    def test_reader_failure_is_unavailable_not_off_and_not_raised(self):
        wa = _mod()
        cases = {
            "every read raises": _reg(run=_quoted(EXE), read_exc=PermissionError(13, "Access is denied")),
            "only StartupApproved raises": _reg(run=_quoted(EXE),
                                                read_exc={APPROVED_SUBKEY: OSError(5, "Access is denied")}),
        }
        for label, reg in cases.items():
            with self.subTest(case=label):
                self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), "unavailable")

    def test_no_reader_or_no_exe_is_unavailable_without_a_call(self):
        wa = _mod()
        self.assertEqual(wa.autostart_read_state(None, EXE, True), "unavailable")
        for exe in (None, ""):
            with self.subTest(exe=exe):
                reg = _reg(run=_quoted(EXE))
                self.assertEqual(wa.autostart_read_state(reg.reader, exe, True), "unavailable")
                self.assertEqual(reg.calls, [])

    def test_persisted_preference_does_not_win(self):
        """CFG: the OS registration is the only source of truth (no config key)."""
        wa = _mod()
        with _ConfigGuard(self):
            reg = _reg()
            self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), "off")
            reg = _reg(run=_quoted(EXE), approved=DISABLED)
            self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), "off")


# ═════════════════════════════════ autostart_toggle ═════════════════════════════════

class ToggleTests(unittest.TestCase):
    """autostart_toggle(reader, writer, exe, is_frozen) -> (new_state, error_key | None).

    One click. From "on": delete the Run value and, if present, the
    StartupApproved entry (a stale entry would silently block a later
    enable). From "off": write ``run_value_for(exe)`` to the Run value —
    overwriting a foreign path — and delete a *disabled* StartupApproved
    entry. Not frozen, no reader / writer, or a reader that raises →
    ``("unavailable", None)`` and nothing is written. A writer that raises →
    (the state before the click, ``"autostart_fail"``). Never a config key.

    Rivals: DEL-IF-PRESENT = a present value is deleted whatever it names,
    KEEP-SA = the Run value is rewritten but the disabled StartupApproved
    entry stays (Windows keeps ignoring us), SA-WRITE = an enabled ``02``
    blob is written instead of deleting the entry, SWALLOW = a writer
    failure still reports the new state, NOFRZ = from source the toggle
    registers ``pythonw.exe``, PERSIST = an "autostart" key is written to
    the config.

    | from (Run / Approved)      | DEL-IF-PRESENT | KEEP-SA  | SA-WRITE   | SWALLOW      | NOFRZ | **expected**, registry after            |
    | absent / absent            | on             | on       | on, SA=02  | on           | on    | **("on", None)**  Run="<exe>", no SA     |
    | "<exe>" / absent           | off            | off      | off        | off          | off   | **("off", None)** Run gone               |
    | "<exe>" / 02 enabled       | off            | off, SA  | off        | off          | off   | **("off", None)** Run gone, SA gone      |
    | "<exe>" / 03 disabled      | off (deleted!) | on, SA=03| on, SA=02  | on           | on    | **("on", None)**  Run="<exe>", SA gone   |
    | "<other>" / absent         | off (deleted!) | on       | on         | on           | on    | **("on", None)**  Run="<exe>"            |
    | "<other>" / 03 disabled    | off            | on, SA=03| on, SA=02  | on           | on    | **("on", None)**  Run="<exe>", SA gone   |
    | absent, not frozen         | —              | —        | —          | —            | on    | **("unavailable", None)** no call        |
    | absent, writer raises      | —              | —        | —          | ("on", None) | —     | **("off", "autostart_fail")** Run absent |
    | "<exe>", writer raises     | —              | —        | —          | ("off",None) | —     | **("on", "autostart_fail")** Run kept    |
    | reader raises              | —              | —        | —          | —            | —     | **("unavailable", None)** writer untouched |

    "Report the flipped state without re-reading" is deliberately *not* a
    rival here: under this writer contract a write either lands or raises,
    so it is indistinguishable from re-reading — the scratch harness
    confirmed it passes every row. What
    ``test_the_returned_state_is_what_the_registry_now_reads`` does pin is
    that the two functions agree on every transition (it is what catches
    UNQ and KEEP-SA a second way). PERSIST is caught by the ``_ConfigGuard``.
    """

    def test_off_to_on_writes_exactly_the_installers_value(self):
        wa = _mod()
        reg = _reg()
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("on", None))
        self.assertEqual(reg.writes, [("set", RUN_SUBKEY, RUN_VALUE, _quoted(EXE))])
        self.assertEqual(reg.run(), _quoted(EXE))
        self.assertIsNone(reg.approved(), "SA-WRITE: nothing is written under StartupApproved")

    def test_on_to_off_deletes_the_run_value_only(self):
        wa = _mod()
        reg = _reg(run=_quoted(EXE))
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("off", None))
        self.assertEqual(reg.writes, [("delete", RUN_SUBKEY, RUN_VALUE)])
        self.assertIsNone(reg.run())

    def test_on_to_off_also_removes_a_present_startup_approved_entry(self):
        wa = _mod()
        reg = _reg(run=_quoted(EXE), approved=ENABLED)
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("off", None))
        self.assertEqual(sorted(reg.writes),
                         sorted([("delete", RUN_SUBKEY, RUN_VALUE), ("delete", APPROVED_SUBKEY, RUN_VALUE)]))
        self.assertEqual(reg.values, {})

    def test_disabled_in_task_manager_is_off_and_the_click_unblocks_it(self):
        wa = _mod()
        reg = _reg(run=_quoted(EXE), approved=DISABLED)
        self.assertEqual(wa.autostart_read_state(reg.reader, EXE, True), "off")
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("on", None))
        self.assertIn(("delete", APPROVED_SUBKEY, RUN_VALUE), reg.writes, "KEEP-SA: the disabled entry must go")
        self.assertIsNone(reg.approved())
        self.assertEqual(reg.run(), _quoted(EXE))
        self.assertNotIn("set", [w[0] for w in reg.writes if w[1] == APPROVED_SUBKEY],
                         "SA-WRITE: the entry is deleted, not rewritten as enabled")

    def test_a_foreign_path_is_overwritten_not_deleted(self):
        wa = _mod()
        reg = _reg(run=_quoted(OTHER_EXE))
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("on", None))
        self.assertEqual(reg.run(), _quoted(EXE))
        self.assertIn(("set", RUN_SUBKEY, RUN_VALUE, _quoted(EXE)), reg.writes)

    def test_a_foreign_path_with_a_disabled_entry(self):
        wa = _mod()
        reg = _reg(run=_quoted(OTHER_EXE), approved=DISABLED)
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("on", None))
        self.assertEqual(reg.run(), _quoted(EXE))
        self.assertIsNone(reg.approved())

    def test_source_run_touches_nothing(self):
        wa = _mod()
        reg = _reg()
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, False), ("unavailable", None))
        self.assertEqual(reg.calls, [], "NOFRZ: from source nothing is read or written")
        pythonw = r"C:\Users\x\AppData\Local\Programs\Python\Python313\pythonw.exe"
        reg = _reg()
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, pythonw, False), ("unavailable", None))
        self.assertEqual(reg.values, {}, "NOFRZ: pythonw.exe is never registered")

    def test_no_registry_is_unavailable(self):
        wa = _mod()
        self.assertEqual(wa.autostart_toggle(None, None, EXE, True), ("unavailable", None))
        reg = _reg()
        self.assertEqual(wa.autostart_toggle(reg.reader, None, EXE, True), ("unavailable", None))
        self.assertEqual(reg.writes, [])

    def test_writer_failure_turning_on_reports_and_leaves_off(self):
        wa = _mod()
        reg = _reg(write_exc=PermissionError(13, "Access is denied"))
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("off", "autostart_fail"))
        self.assertIsNone(reg.run())

    def test_writer_failure_turning_off_reports_and_leaves_on(self):
        wa = _mod()
        reg = _reg(run=_quoted(EXE), write_exc=OSError(5, "Access is denied"))
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("on", "autostart_fail"))
        self.assertEqual(reg.run(), _quoted(EXE))

    def test_reader_failure_is_unavailable_and_writes_nothing(self):
        wa = _mod()
        reg = _reg(read_exc=PermissionError(13, "Access is denied"))
        self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), ("unavailable", None))
        self.assertEqual(reg.writes, [])

    def test_the_returned_state_is_what_the_registry_now_reads(self):
        """The state reported is the state a fresh read sees, and a second click flips it back."""
        wa = _mod()
        starts = [_reg(), _reg(run=_quoted(EXE)), _reg(run=_quoted(EXE), approved=ENABLED),
                  _reg(run=_quoted(EXE), approved=DISABLED), _reg(run=_quoted(OTHER_EXE))]
        for reg in starts:
            with self.subTest(start=dict(reg.values)):
                new_state, err = wa.autostart_toggle(reg.reader, reg.writer, EXE, True)
                self.assertIsNone(err)
                fresh = _Registry(reg.values)
                self.assertEqual(wa.autostart_read_state(fresh.reader, EXE, True), new_state)
                again, err = wa.autostart_toggle(reg.reader, reg.writer, EXE, True)
                self.assertIsNone(err)
                self.assertNotEqual(again, new_state, "a second click must flip the state back")

    def test_never_a_config_key(self):
        """PERSIST: no preference is read or written — design X, the macOS contract."""
        wa = _mod()
        with _ConfigGuard(self):
            reg = _reg()
            for expected in ("on", "off", "on"):
                self.assertEqual(wa.autostart_toggle(reg.reader, reg.writer, EXE, True), (expected, None))
        src = _module_text()
        for forbidden in ("RUNTIME", "merge_config_updates", "save_config", "load_config", "CONFIG_PATH",
                          "SETTINGS_OWNED_KEYS", "apply_config"):
            self.assertNotIn(forbidden, src, f"win_autostart.py must not mention {forbidden}")


def _module_path():
    return os.path.join(ROOT, "windows", "win_autostart.py")


def _module_text():
    with open(_module_path(), encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════ the thin winreg adapter (fake winreg) ═══════════════════════════

class _FakeKey:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def Close(self):
        pass


class _FakeWinreg(types.ModuleType):
    """Just enough ``winreg`` to run the adapter on macOS.

    ``keys``: ``{subkey.lower(): {name: (value, type)}}``. A missing subkey
    raises ``FileNotFoundError`` from ``OpenKey``; a missing value raises it
    from ``QueryValueEx`` / ``DeleteValue`` — as the real module does.
    ``deny``: subkeys whose open raises ``PermissionError`` instead.
    """

    HKEY_CURRENT_USER = 0x80000001
    HKEY_LOCAL_MACHINE = 0x80000002
    KEY_READ, KEY_WRITE, KEY_ALL_ACCESS = 0x20019, 0x20006, 0xF003F
    KEY_QUERY_VALUE, KEY_SET_VALUE, KEY_WOW64_64KEY, KEY_WOW64_32KEY = 0x1, 0x2, 0x100, 0x200
    REG_SZ, REG_EXPAND_SZ, REG_BINARY, REG_DWORD = 1, 2, 3, 4
    error = OSError

    def __init__(self, keys=None, deny=()):
        super().__init__("winreg")
        self.keys = {k.lower(): dict(v) for k, v in (keys or {}).items()}
        self.deny = {d.lower() for d in deny}
        self.calls = []

    def _open(self, root, subkey, create):
        if root != self.HKEY_CURRENT_USER:
            raise PermissionError(5, "Access is denied")
        path = subkey.lower()
        if path in self.deny:
            raise PermissionError(5, "Access is denied")
        if path not in self.keys:
            if not create:
                raise FileNotFoundError(2, "The system cannot find the file specified")
            self.keys[path] = {}
        return _FakeKey(path)

    def OpenKey(self, root, subkey, reserved=0, access=KEY_READ):
        self.calls.append(("OpenKey", subkey, access))
        return self._open(root, subkey, False)

    OpenKeyEx = OpenKey

    def CreateKey(self, root, subkey):
        self.calls.append(("CreateKey", subkey))
        return self._open(root, subkey, True)

    def CreateKeyEx(self, root, subkey, reserved=0, access=KEY_WRITE):
        self.calls.append(("CreateKeyEx", subkey, access))
        return self._open(root, subkey, True)

    def QueryValueEx(self, key, name):
        self.calls.append(("QueryValueEx", key.path, name))
        try:
            return self.keys[key.path][name]
        except KeyError:
            raise FileNotFoundError(2, "The system cannot find the file specified") from None

    def SetValueEx(self, key, name, reserved, type_, value):
        self.calls.append(("SetValueEx", key.path, name, type_, value))
        self.keys[key.path][name] = (value, type_)

    def SetValue(self, key, sub_key, type_, value):
        # the *default* value of a sub key — the wrong call for a named value; kept so the rival is visible
        self.calls.append(("SetValue", key.path, sub_key, type_, value))
        self.keys.setdefault((key.path + "\\" + (sub_key or "")).rstrip("\\").lower(), {})[""] = (value, type_)

    def DeleteValue(self, key, name):
        self.calls.append(("DeleteValue", key.path, name))
        try:
            del self.keys[key.path][name]
        except KeyError:
            raise FileNotFoundError(2, "The system cannot find the file specified") from None

    def CloseKey(self, key):
        pass


class RegistryAdapterTests(unittest.TestCase):
    """registry_reader / registry_writer — the only winreg code, run here against a fake ``winreg``.

    The adapter is the one part that executes only on Windows, and the
    translation it owns is the one that decides between "off" and
    "unavailable" for every fresh install: ``winreg`` raises
    ``FileNotFoundError`` for an absent key *and* for an absent value, and the
    reader must return ``None`` for both while letting any other ``OSError``
    out. (The macOS half shipped a mapping that sent "never registered" to
    "unavailable" — every fresh install showed a disabled item; this pin is
    that lesson, translated.) ``winreg`` is imported inside the adapter, so a
    fake module in ``sys.modules`` is all the test needs; the module itself
    must import with no ``winreg`` on the host at all.

    Rivals: TUPLE = return ``QueryValueEx``'s ``(value, type)`` pair, NF-RAISE
    = let ``FileNotFoundError`` out (absent reads as unavailable), ALL-NONE =
    swallow every ``OSError`` (a denied read reads as "off"), EXPAND = write
    ``REG_EXPAND_SZ``, DEFAULT = ``SetValue`` (the key's default value),
    TOP-IMPORT = ``import winreg`` at module level, GUARD-AT-IMPORT =
    ``real_registry`` decided by a module constant.

    | call                                         | TUPLE     | NF-RAISE | ALL-NONE | EXPAND | DEFAULT | **expected**            |
    | reader(Run, "ClaudePet"), value present      | (v, 1)    | v        | v        | v      | v       | **v**                   |
    | reader(Run, "ClaudePet"), value absent       | raises    | raises   | None     | None   | None    | **None**                |
    | reader(StartupApproved\\Run, …), key absent   | raises    | raises   | None     | None   | None    | **None**                |
    | reader(Run, …), open denied                  | raises    | raises   | None     | raises | raises  | **raises OSError**      |
    | writer(Run, "ClaudePet", '"p"')              | —         | —        | —        | type 2 | default | **("\"p\"", REG_SZ)**   |
    | writer(Run, "ClaudePet", None), present      | —         | —        | —        | —      | —       | **value gone**          |
    """

    def _fake(self, keys=None, deny=()):
        fake = _FakeWinreg(keys, deny)
        patcher = mock.patch.dict(sys.modules, {"winreg": fake})
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def test_reader_returns_the_value_not_the_pair(self):
        wa = _mod()
        self._fake({RUN_SUBKEY: {RUN_VALUE: (_quoted(EXE), 1)}})
        self.assertEqual(wa.registry_reader(RUN_SUBKEY, RUN_VALUE), _quoted(EXE))

    def test_reader_returns_none_for_an_absent_value_and_an_absent_key(self):
        wa = _mod()
        self._fake({RUN_SUBKEY: {"Other": ("x", 1)}})          # Run exists, ClaudePet does not; SA key absent
        self.assertIsNone(wa.registry_reader(RUN_SUBKEY, RUN_VALUE))
        self.assertIsNone(wa.registry_reader(APPROVED_SUBKEY, RUN_VALUE))

    def test_reader_lets_a_denied_open_out(self):
        wa = _mod()
        self._fake({RUN_SUBKEY: {RUN_VALUE: (_quoted(EXE), 1)}}, deny=(RUN_SUBKEY,))
        with self.assertRaises(OSError) as ctx:
            wa.registry_reader(RUN_SUBKEY, RUN_VALUE)
        self.assertNotIsInstance(ctx.exception, FileNotFoundError)

    def test_writer_sets_a_reg_sz_named_value(self):
        wa = _mod()
        fake = self._fake({RUN_SUBKEY: {}})
        wa.registry_writer(RUN_SUBKEY, RUN_VALUE, _quoted(EXE))
        self.assertEqual(fake.keys[RUN_SUBKEY.lower()].get(RUN_VALUE), (_quoted(EXE), fake.REG_SZ))
        self.assertNotIn("SetValue", [c[0] for c in fake.calls], "DEFAULT: SetValue writes the key's default value")

    def test_writer_deletes_on_none(self):
        wa = _mod()
        fake = self._fake({RUN_SUBKEY: {RUN_VALUE: (_quoted(EXE), 1)},
                           APPROVED_SUBKEY: {RUN_VALUE: (DISABLED, 3)}})
        wa.registry_writer(RUN_SUBKEY, RUN_VALUE, None)
        wa.registry_writer(APPROVED_SUBKEY, RUN_VALUE, None)
        self.assertEqual(fake.keys[RUN_SUBKEY.lower()], {})
        self.assertEqual(fake.keys[APPROVED_SUBKEY.lower()], {})

    def test_real_registry_is_decided_by_the_platform_at_call_time(self):
        wa = _mod()
        with mock.patch.object(sys, "platform", "win32"):
            reader, writer = wa.real_registry()
        self.assertIs(reader, wa.registry_reader)
        self.assertIs(writer, wa.registry_writer)
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(wa.real_registry(), (None, None))

    def test_winreg_is_imported_inside_the_adapter_only(self):
        """No module-level `import winreg`; some function imports it at call time.

        The ``sys.modules`` probe below is **host-dependent and is only evidence on a
        host that has no winreg**. On Windows ``winreg`` is a built-in that the
        interpreter already has in ``sys.modules`` before any test runs, so asserting
        its absence there fails against perfectly correct code — it measures the host,
        not the module. It used to be asserted unconditionally and did exactly that.

        The two AST assertions are the real gate and they discriminate on **both**
        hosts: a top-level ``import winreg`` fails the first, and deleting the
        call-time import fails the second.
        """
        _mod()
        if sys.platform != "win32":
            self.assertNotIn("winreg", sys.modules,
                             "the module must import with no winreg on the host")
        tree = ast.parse(_module_text())
        top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = {a.name for n in top for a in n.names} | {n.module for n in top if isinstance(n, ast.ImportFrom)}
        self.assertNotIn("winreg", names, "TOP-IMPORT: winreg must be imported at call time")
        inside = [n for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
                  for n in ast.walk(f) if isinstance(n, ast.Import) and any(a.name == "winreg" for a in n.names)]
        self.assertTrue(inside, "no function imports winreg — where is the adapter?")

    def test_importable_the_way_the_port_imports_it(self):
        """The port runs with ``windows/`` first on sys.path and imports ``win_autostart`` bare."""
        code = ("import sys; sys.path.insert(0, 'windows'); import win_autostart as m; "
                "print(m.run_value_for('C:/a/ClaudePet.exe'))")
        proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr.strip().splitlines()[-1:] or proc.stderr)
        self.assertEqual(proc.stdout.strip(), '"C:/a/ClaudePet.exe"')


# ═══════════════════════════ uninstall: the value written is the value removed ═══════════════════════════

def _port_source():
    """The port text the wiring pins read, and where it came from (override announced on stderr)."""
    override = os.environ.get(PORT_SOURCE_ENV)
    path = override or os.path.join(ROOT, "windows", "claude_pet_win.py")
    with open(path, "rb") as f:
        raw = f.read()
    if override:
        sys.stderr.write(f"[{PORT_SOURCE_ENV}] gating {path} sha256={hashlib.sha256(raw).hexdigest()}\n")
    return path, raw.decode("utf-8")


def _method_text(text, name):
    """The source text of ``def <name>(`` up to the next def / class / decorator at the same indentation."""
    m = re.search(r"(?m)^(\s*)def " + re.escape(name) + r"\(", text)
    if m is None:
        return ""
    indent = m.group(1)
    rest = text[m.end():]
    n = re.search(r"(?m)^" + indent + r"(def |class |@)", rest)
    return text[m.start():m.end() + (n.start() if n else len(rest))]


class UninstallPinTests(unittest.TestCase):
    """"Uninstall completely" removes the value the toggle writes.

    The brief says ``uninstall_plan`` carries the Run-value step. It does not:
    ``uninstall_plan`` is a file plan ("delete" / "run" / "helper" over
    paths), and the registry step is the port's own
    ``delete_run_value_if_ours(exe)`` in ``_uninstall``'s irreversible
    section, guarded by ``wu.run_value_is_ours``. These pins name the real
    mechanism so it stays where it is: a refactor that moves the step goes
    back through the Verifier. The first two are regression pins (green
    before this change, expected to stay green); the third is the gate that
    ties the two halves together (red until ``run_value_for`` exists).
    """

    def test_uninstall_plan_is_a_file_plan_with_no_registry_step(self):
        for kind in ("inno", "portable"):
            plan = wu.uninstall_plan(kind, r"C:\Programs\ClaudePet", r"C:\Users\x")
            for op, arg in plan:
                with self.subTest(kind=kind, step=op):
                    self.assertIn(op, ("delete", "run", "helper"))
                    for p in ([arg] if isinstance(arg, str) else list(arg)):
                        self.assertNotIn("CurrentVersion", p, "the plan is paths, never registry locations")

    def test_the_port_deletes_the_run_value_after_the_point_of_no_return(self):
        _, port = _port_source()
        body = _method_text(port, "_uninstall")
        self.assertTrue(body, "no _uninstall in the port")
        launch = max(body.find("popen_detached("), body.find("run-uninstaller"))
        step = body.find("delete_run_value_if_ours(")
        self.assertGreater(step, -1, "_uninstall no longer deletes the Run value")
        self.assertGreater(launch, -1)
        self.assertLess(launch, step, "the Run value goes in the irreversible section, after the launch")
        helper = _method_text(port, "delete_run_value_if_ours")
        self.assertIn("run_value_is_ours(", helper, "the delete must stay identity-guarded")
        self.assertIn("DeleteValue(", helper)

    def test_what_the_toggle_writes_is_what_the_uninstaller_recognises(self):
        wa = _mod()
        self.assertTrue(wu.run_value_is_ours(wa.run_value_for(EXE), EXE))
        self.assertTrue(wu.run_value_is_ours(wa.run_value_for(EXE), EXE_UPPER))
        self.assertFalse(wu.run_value_is_ours(wa.run_value_for(EXE), OTHER_EXE))


# ═══════════════════════════════ the port's wiring (AST, no GUI) ═══════════════════════════════

def _in_order(nodes):
    return sorted(nodes, key=lambda n: (n.lineno, n.col_offset))


def _find_def(tree, name, within=None):
    for node in ast.walk(tree):
        if within is None:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        elif isinstance(node, ast.ClassDef) and node.name == within:
            for sub in ast.walk(node):
                if isinstance(sub, ast.FunctionDef) and sub.name == name:
                    return sub
    return None


def _find_class(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _t_key(node):
    """``"key"`` from ``cp.t("key")`` / ``t("key")`` / ``tw("key")``; else None."""
    if (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)):
        f = node.func
        if (isinstance(f, ast.Name) and f.id in ("t", "tw")) or (isinstance(f, ast.Attribute) and f.attr == "t"):
            return node.args[0].value
    return None


def _ref(node):
    """A stable name for an action reference: ``x`` for Name, ``self.x`` for self.attr."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return "self." + node.attr
    return None


def _menu_var(fn):
    """The name bound to the top-level ``QMenu(...)`` in the method (the context menu itself)."""
    for st in fn.body:
        if (isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Name)
                and st.value.func.id == "QMenu" and len(st.targets) == 1):
            return _ref(st.targets[0])
    return None


def _action_assignments(fn):
    """{ref: (key, call)} for ``ref = QAction(cp.t("key"), …)`` and ``ref = <menu>.addAction(cp.t("key"), …)``."""
    out = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.value, ast.Call):
            f = node.value.func
            is_qaction = isinstance(f, ast.Name) and f.id == "QAction"
            is_add = isinstance(f, ast.Attribute) and f.attr == "addAction"
            ref = _ref(node.targets[0])
            if (is_qaction or is_add) and node.value.args and ref:
                key = _t_key(node.value.args[0])
                if key:
                    out[ref] = (key, node.value)
    return out


def _menu_sequence(fn, menu):
    """Source-ordered labels of ``<menu>.addAction / addMenu / addSeparator`` calls in the method."""
    refs = _action_assignments(fn)
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and _ref(n.func.value) == menu and n.func.attr in ("addAction", "addMenu", "addSeparator")]
    seq = []
    for c in _in_order(calls):
        if c.func.attr == "addSeparator":
            seq.append("---")
            continue
        if c.func.attr == "addMenu":
            seq.append("<submenu>")
            continue
        a0 = c.args[0] if c.args else None
        key = _t_key(a0)
        if key:
            seq.append(key)
        elif _ref(a0) in refs:
            seq.append(refs[_ref(a0)][0])
        elif isinstance(a0, ast.JoinedStr):
            seq.append("<version>")
        else:
            seq.append("<?>")
    return seq


def _mac_menu_keys():
    """The macOS ``rightMouseDown_`` tuple list, as TR keys (None → separator)."""
    with open(os.path.join(ROOT, "claude_pet.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    fn = _find_def(tree, "rightMouseDown_")
    if fn is None:
        return None
    for node in ast.walk(fn):
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple) and node.iter.elts
                and all(isinstance(e, ast.Tuple) and len(e.elts) == 2 for e in node.iter.elts)):
            return [_t_key(pair.elts[0]) or "---" for pair in node.iter.elts]
    return None


def _connect_calls(fn, signal):
    """[(receiver_ref, slot_expr)] for every ``<receiver>.<signal>.connect(<slot>)`` in the method."""
    out = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "connect"
                and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == signal and n.args):
            out.append((_ref(n.func.value.value), n.args[0]))
    return out


def _reach(tree, cls, fn, start, limit=60):
    """The AST nodes reachable from a slot expression: nested defs of ``fn``, methods of ``cls``, module defs."""
    module_defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    class_defs = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)} if cls else {}
    nested = {n.name: n for n in ast.walk(fn) if isinstance(n, ast.FunctionDef) and n is not fn}
    seen, out, queue = set(), [], [start]
    while queue and len(out) < limit:
        node = queue.pop(0)
        if id(node) in seen:
            continue
        seen.add(id(node))
        out.append(node)
        for sub in ast.walk(node):
            target = _ref(sub)
            if target is None:
                continue
            name = target[5:] if target.startswith("self.") else target
            tables = (class_defs,) if target.startswith("self.") else (nested, module_defs)
            for table in tables:
                d = table.get(name)
                if d is not None and id(d) not in seen:
                    queue.append(d)
                    break
    return out


def _called(nodes):
    out = set()
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    out.add(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    out.add(n.func.attr)
    return out


def _keys_used(nodes):
    return {k for node in nodes for n in ast.walk(node) for k in [_t_key(n)] if k}


def _names(nodes):
    return {n.id for node in nodes for n in ast.walk(node) if isinstance(n, ast.Name)}


def _attrs(nodes):
    return {n.attr for node in nodes for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def _consts(nodes):
    return {n.value for node in nodes for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _tr_win_keys(tree):
    """Every key defined in the port's own ``TR_WIN`` table, whatever the locale."""
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "TR_WIN" and isinstance(node.value, ast.Dict)):
            keys = set()
            for locale_dict in node.value.values:
                if isinstance(locale_dict, ast.Dict):
                    keys |= {k.value for k in locale_dict.keys if isinstance(k, ast.Constant)}
            return keys
    return None


class PortWiringTests(unittest.TestCase):
    """windows/claude_pet_win.py, read as an AST: the item, its place, its two slots, and what it hands over.

    The port cannot be imported on this host, so the observable is its
    source. Each pin is written so that the extractor's own failure is a
    different message from the design's: a test that cannot find the roam
    item says so, rather than reporting a wrong order.

    Rivals: BEFORE-ROAM / AFTER-RESET = the item somewhere else in the menu,
    NOT-CHECKABLE = a plain action, CONSTRUCT-ONLY = the state read once when
    the menu is built and never on ``aboutToShow``, NO-UNAVAILABLE = the
    disabled item keeps the plain title, SILENT-FAIL = the toggle's error key
    dropped on the floor, CONFIG = ``merge_config_updates({"autostart": …})``
    the way roam does it, LOCAL-TR = the keys redefined in ``TR_WIN``,
    FROM-SOURCE = the frozen flag not handed over.

    | port                                          | order test | checkable | aboutToShow | click | handover | no-config |
    | HEAD (no item)                                | FAIL       | FAIL      | FAIL        | FAIL  | FAIL     | ok        |
    | item before roam                              | FAIL       | ok        | ok          | ok    | ok       | ok        |
    | item after reset size                         | FAIL       | ok        | ok          | ok    | ok       | ok        |
    | plain QAction                                 | ok         | FAIL      | ok          | ok    | ok       | ok        |
    | state read at construction only               | ok         | ok        | FAIL        | ok    | ok       | ok        |
    | error key ignored                             | ok         | ok        | ok          | FAIL  | ok       | ok        |
    | roam-style merge_config_updates               | ok         | ok        | ok          | ok    | ok       | FAIL      |
    | **as designed**                               | **ok**     | **ok**    | **ok**      | **ok**| **ok**   | **ok**    |
    """

    @classmethod
    def setUpClass(cls):
        cls.path, cls.port = _port_source()
        cls.tree = ast.parse(cls.port, filename=cls.path)
        cls.cls = _find_class(cls.tree, "PetWindow")
        cls.fn = _find_def(cls.tree, "_context_menu", within="PetWindow")

    def setUp(self):
        self.assertIsNotNone(self.cls, "no PetWindow class in the port")
        self.assertIsNotNone(self.fn, "no PetWindow._context_menu in the port")
        self.menu = _menu_var(self.fn)
        self.assertIsNotNone(self.menu, "no QMenu(...) assignment in _context_menu")

    def _autostart_ref(self):
        refs = _action_assignments(self.fn)
        hits = [ref for ref, (key, _) in refs.items() if key == "menu_autostart"]
        self.assertEqual(len(hits), 1,
                         f"expected exactly one action built from t('menu_autostart') in _context_menu, found {hits}")
        return hits[0], refs[hits[0]][1]

    def test_menu_autostart_sits_between_roam_and_reset_size_as_on_macos(self):
        seq = _menu_sequence(self.fn, self.menu)
        self.assertIn("menu_roam", seq, f"extractor found no roam item in {seq}")
        self.assertIn("menu_reset_size", seq, f"extractor found no reset-size item in {seq}")
        mac = _mac_menu_keys()
        self.assertIsNotNone(mac, "could not read the macOS rightMouseDown_ tuple list")
        i = seq.index("menu_roam")
        j = mac.index("menu_roam")
        self.assertEqual(seq[i:i + 3], MENU_TRIPLE, f"Windows menu order: {seq}")
        self.assertEqual(mac[j:j + 3], MENU_TRIPLE, f"macOS menu order: {mac}")
        # The piece with no literal in it, so it cannot go stale: **macOS is the
        # reference**. Every menu key macOS has must be on Windows, in the same
        # relative order. Windows may add entries of its own (the update check, the
        # version line) — the port has more to say — but it may not drop one or move
        # one, and dropping is the failure this port actually has: v0.26 landed on
        # macOS and reached none of the Windows menu.
        #
        # An *intersection* of the two lists does not say this. Under an intersection a
        # key Windows simply does not have falls out of both sides and the comparison
        # passes, which is the one case that matters most. Mutation-checked: deleting
        # the auto-refresh item from the Windows menu left an intersection-based
        # version green.
        want = [k for k in mac if k.startswith("menu_")]
        self.assertGreaterEqual(
            len(want), len(MENU_TRIPLE),
            "the macOS extractor produced only %r — with fewer keys than the triple "
            "this comparison would pass without comparing anything" % (want,))
        missing = [k for k in want if k not in seq]
        self.assertEqual(
            missing, [],
            "the Windows menu is missing %r, which macOS has. windows=%r macos=%r"
            % (missing, seq, mac))
        self.assertEqual(
            [k for k in seq if k in set(want)], want,
            "the Windows menu orders macOS's items differently. windows=%r macos=%r"
            % (seq, mac))

    def test_the_autostart_action_is_checkable(self):
        ref, call = self._autostart_ref()
        by_keyword = any(k.arg == "checkable" and isinstance(k.value, ast.Constant) and k.value.value is True
                         for k in call.keywords)
        by_call = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setCheckable"
                      and _ref(n.func.value) == ref and n.args
                      and isinstance(n.args[0], ast.Constant) and n.args[0].value is True
                      for n in ast.walk(self.fn))
        self.assertTrue(by_keyword or by_call, f"{ref} is not checkable (no checkable=True, no setCheckable(True))")

    def test_the_menu_rereads_the_state_when_it_opens(self):
        slots = [slot for recv, slot in _connect_calls(self.fn, "aboutToShow") if recv == self.menu]
        self.assertTrue(slots, f"no {self.menu}.aboutToShow.connect(...) in _context_menu (CONSTRUCT-ONLY)")
        reach = [n for slot in slots for n in _reach(self.tree, self.cls, self.fn, slot)]
        called = _called(reach)
        self.assertIn("autostart_read_state", called, f"the aboutToShow slot never reads the state; it calls {sorted(called)}")
        for setter in ("setChecked", "setEnabled", "setText"):
            self.assertIn(setter, called, f"the slot never calls {setter}")
        self.assertIn("autostart_unavailable", _keys_used(reach),
                      "NO-UNAVAILABLE: the disabled item must carry t('autostart_unavailable')")

    def test_the_click_toggles_and_a_failure_reaches_the_message_box(self):
        ref, _ = self._autostart_ref()
        slots = [slot for recv, slot in _connect_calls(self.fn, "triggered") if recv == ref]
        self.assertTrue(slots, f"no {ref}.triggered.connect(...) in _context_menu")
        reach = [n for slot in slots for n in _reach(self.tree, self.cls, self.fn, slot)]
        called = _called(reach)
        self.assertIn("autostart_toggle", called, f"the click never calls autostart_toggle; it calls {sorted(called)}")
        keys = _keys_used(reach)
        self.assertLessEqual({"autostart_title", "autostart_fail"}, keys,
                             f"SILENT-FAIL: the failure box needs t('autostart_title') / t('autostart_fail'); saw {sorted(keys)}")
        self.assertTrue({"_msgbox", "_info"} & called, "the existing message-box helper must show the failure")

    def test_the_wiring_hands_over_the_frozen_flag_the_exe_and_the_real_registry(self):
        ref, _ = self._autostart_ref()
        starts = [slot for recv, slot in _connect_calls(self.fn, "aboutToShow") if recv == self.menu]
        starts += [slot for recv, slot in _connect_calls(self.fn, "triggered") if recv == ref]
        self.assertTrue(starts)
        reach = [n for s in starts for n in _reach(self.tree, self.cls, self.fn, s)]
        called, names, attrs, consts = _called(reach), _names(reach), _attrs(reach), _consts(reach)
        self.assertTrue("is_frozen" in called or "frozen" in consts,
                        "FROM-SOURCE: neither is_frozen() nor getattr(sys, 'frozen', …) is handed over")
        self.assertTrue("executable" in attrs or "app_exe_path" in called,
                        "the executable (sys.executable / app_exe_path()) is not handed over")
        self.assertTrue("real_registry" in called or {"registry_reader", "registry_writer"} <= (names | attrs),
                        "the real winreg adapter (real_registry()) is not handed over")

    def test_no_config_key_and_no_local_override(self):
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Constant) and n.value == "autostart":
                self.fail(f"CONFIG: the port carries an 'autostart' string at line {n.lineno} — no config key exists")
        ref, _ = self._autostart_ref()
        starts = [slot for recv, slot in _connect_calls(self.fn, "aboutToShow") if recv == self.menu]
        starts += [slot for recv, slot in _connect_calls(self.fn, "triggered") if recv == ref]
        reach = [n for s in starts for n in _reach(self.tree, self.cls, self.fn, s)]
        self.assertFalse({"merge_config_updates", "save_config", "apply_config"} & _called(reach),
                         "CONFIG: the slots must not persist anything")
        self.assertNotIn("RUNTIME", _names(reach) | _attrs(reach), "CONFIG: RUNTIME is not the source of truth")
        local = _tr_win_keys(self.tree)
        self.assertIsNotNone(local, "no TR_WIN table in the port")
        self.assertEqual(set(AUTOSTART_KEYS) & local, set(), "LOCAL-TR: the six keys come from claude_pet.py only")
        used = _keys_used([self.tree])
        for key in ("menu_autostart", "autostart_unavailable", "autostart_title", "autostart_fail"):
            self.assertIn(key, used, f"the port never uses t('{key}')")


# ═══════════════════════════ preconditions and documentation ═══════════════════════════

class SharedKeysTests(unittest.TestCase):
    """Precondition, expected green: the six keys the Windows half uses exist in claude_pet.py for every locale.

    Not a gate on this change (claude_pet.py is not edited here); it pins
    that the merge the port relies on is present in this tree, so a wiring
    failure is never mistaken for a missing string.
    """

    def test_every_locale_defines_every_key(self):
        for loc in LOCALES:
            for key in AUTOSTART_KEYS:
                with self.subTest(locale=loc, key=key):
                    value = cp.TR[loc].get(key)
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip())


class ReadmeTests(unittest.TestCase):
    """windows/README.md names the toggle and the hardware checks macOS cannot run.

    Documentation pin: the README's "실기에서 확인할 것" list is the checklist
    the hardware run follows, and the StartupApproved byte encoding is the
    one fact in this feature that only that run can settle.
    """

    def test_readme_names_the_toggle_and_the_hardware_checks(self):
        with open(os.path.join(ROOT, "windows", "README.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue("StartupApproved" in text, "the README never names StartupApproved")
        self.assertTrue("0x02" in text and "0x03" in text, "the byte values to confirm on hardware")
        self.assertTrue("작업 관리자" in text or "Task Manager" in text, "Task Manager › Startup apps is the hardware check")
        self.assertTrue(cp.TR["ko"]["menu_autostart"] in text or "menu_autostart" in text,
                        "the README must name the menu item")


if __name__ == "__main__":
    unittest.main()
