"""Gating tests for the five hardware findings on v0.25 pre-release (Track F, 2026-09-14).

Run from the worktree root:

    python3 -m unittest discover -s windows/tests -t . -v

Verifier-owned (AGENTS.md §2 Condition A). The Developer owns
``windows/win_core.py`` (new), ``windows/win_update.py``,
``windows/win_autostart.py``, ``windows/claude_pet_win.py``,
``windows/build_win.py``, ``windows/verify_win_artifact.py``,
``windows/installer.iss`` and ``windows/README.md``, and must not touch an
assertion, an expected value or a fixture literal in this file.

This file deliberately shares no fixture with ``test_win_update.py`` or
``test_win_autostart.py``: those two were written from the *pre-hardware*
model of the system, and three of the five findings below are facts that
model got wrong. A gate that reused their fixtures would inherit the wrong
fact.

─────────────────────────── provenance of the facts (AGENTS.md §5) ───────────────────────────

**Observation, one machine.** A Windows 11 session ran the v0.25 pre-release
checks against this worktree's HEAD (``f876e40``) on 2026-09-14: it built the
artifacts, installed with the Inno installer, toggled "Start at sign-in" from
the right-click menu and from Task Manager › Startup apps, and uninstalled —
once with the pet closed and once with it running. Sample: one machine, one
Windows build, one install. It is an *observation*, not a measurement: no
count, window or denominator was taken, and none is claimed here.

**What that observation can and cannot support.** A single machine can
*refute* a universal claim and cannot *establish* one. So it is used here in
exactly one direction — to refute the three encodings this tree asserts:

* ``F1`` refutes "these two scripts run on Windows": both die at their first
  import (``ModuleNotFoundError: No module named 'fcntl'``, then, with the
  shim on ``sys.path``, ``TypeError: LoadLibrary() argument 1 must be str,
  not None``). The refutation does not depend on the sample: the same two
  failures are reproduced *deterministically* by this file's simulation,
  which is why F1's gates are host-independent.
* ``F2`` refutes "the Inno uninstall subkey ends in one closing brace": the
  uninstall log names ``…\\Uninstall\\{me.yeongyu.claudepet}}_is1`` and the peer
  called ``install_kind`` with both spellings (constant → ``portable``, real
  key → ``inno``). The corrected spelling is *derived* below from
  ``installer.iss``'s own ``AppId`` rather than transcribed, so the gate does
  not rest on the sample either.
* ``F3`` refutes "``0x02`` is the enabled byte and ``0x03`` the disabled one":
  disabling through the UI wrote ``01 00 00 00`` + FILETIME, re-enabling wrote
  twelve zero bytes, and third-party entries this UI never touched carry
  ``0x02``. **The even/odd rule this file gates is a *hypothesis* under §5**,
  proposed by the peer and not yet reproduced by a second party; what the
  observation establishes is only that ``0x00`` means enabled and ``0x01``
  means disabled, which is already enough to refute the shipped rule. The
  ``0x04``/``0x05`` rows below therefore gate the *chosen* rule, and the
  docstring of ``startup_approved_enabled`` must say which part is observed
  and which part is extrapolated.
* ``F4`` refutes "uninstalling removes the app tree": with the pet running,
  ``ClaudePet.exe`` and 44 files under ``_internal\\`` survived, the uninstall
  still returned rc=0, and the ARP entry and the Run value were gone before
  the failures — so nothing retries and nothing offers the user a way back.
  The uninstall log contained no Restart Manager / CloseApplications step at
  all, **even though this tree already sets ``CloseApplications=yes`` and
  ``RestartApplications=yes``**. That is why F4's gate requires an explicit
  ``[UninstallRun]`` kill step and treats those two directives as
  insufficient on their own: they were present when the failure happened.

``F5`` (no version resource on the exe) is a cosmetic gap, gated the same way.

─────────────────────────── the seams these gates pin ───────────────────────────

A Developer who wires them differently gets an ERROR rather than a silent
pass — that is the point of naming them:

* ``windows/win_core.py`` exposes ``import_core()`` → the core module. It is
  the *one* place the two Windows work-arounds live, importable both as
  ``windows.win_core`` (this suite, run with ``-t .``) and bare as
  ``win_core`` (the port and the PyInstaller bundle), and a no-op on macOS.
* ``win_update`` keeps the core on its module attribute ``cp`` — the name the
  port, the artifact gate and ``verify_release_artifact.py``'s Windows twin
  already read it by.
* ``build_win.write_version_resource(path, version)`` writes the PyInstaller
  version-resource file and returns the path it wrote.
* ``verify_win_artifact.check_version_resource(exe_path)`` returns a list of
  problems, and never returns an empty list *silently* on a host that cannot
  inspect a PE.

Every class docstring carries the AGENTS.md §3 truth table for its fixtures:
the rivals are the implementations someone would plausibly write, and each
fixture is chosen so that no rival collapses onto the expected value.
"""

import ast
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

WINDIR = os.path.join(ROOT, "windows")
ISS = os.path.join(WINDIR, "installer.iss")
PORT = os.path.join(WINDIR, "claude_pet_win.py")
README = os.path.join(WINDIR, "README.md")

CORE_HELPER = "windows.win_core"
WU = "windows.win_update"
WA = "windows.win_autostart"
BW = "windows.build_win"
VWA = "windows.verify_win_artifact"


def _mod(name):
    """Import lazily so a missing module fails each gate on its own line."""
    return importlib.import_module(name)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════════
# F1 — one owner for the core import
# ═══════════════════════════════════════════════════════════════════════════════

# The child process below emulates a Windows import environment on this macOS
# host. It applies NO work-around of its own: everything that makes the import
# succeed must come from the module under test. Three things make it Windows-like:
#
#   1. ``fcntl`` resolves only through ``windows/compat`` — and raises
#      ModuleNotFoundError when that directory is not on sys.path, which is
#      exactly what Windows does.
#   2. ``ctypes.CDLL(None)`` raises TypeError with the message the hardware saw.
#   3. ``sys.platform`` reads ``win32`` (after the stdlib the four modules need
#      has been imported, so that pre-Windows-ified stdlib modules such as
#      ``shutil``/``_winapi`` are not dragged in).
#
# A stub ``msvcrt`` is supplied because the compat shim imports it; it is never
# called during an import.
_CHILD = r'''
import ast, importlib, importlib.machinery, json, os, sys, types

ROOT, TARGET, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
COMPAT = os.path.join(ROOT, "windows", "compat")

# --- preload the stdlib these modules import, before sys.platform lies ---
_local = {"fcntl", "claude_pet", "win_update", "win_core", "win_autostart",
          "verify_win_artifact", "build_win", "PyInstaller", "PIL", "PySide6"}
_names = {"encodings.idna"}
for rel in ("claude_pet.py", "windows/win_update.py", "windows/win_autostart.py",
            "windows/build_win.py", "windows/verify_win_artifact.py", "windows/win_core.py"):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    for node in ast.parse(open(p, encoding="utf-8").read()).body:
        if isinstance(node, ast.Import):
            _names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            _names.add(node.module)
for name in sorted(_names):
    if name.split(".")[0] in _local:
        continue
    try:
        importlib.import_module(name)
    except Exception:
        pass


class WindowsLikeFcntl:
    """fcntl exists only when the compat shim's directory is on sys.path."""

    def find_spec(self, name, path=None, target=None):
        if name != "fcntl":
            return None
        if COMPAT in sys.path:
            return importlib.machinery.PathFinder.find_spec(name, [COMPAT], target)
        raise ModuleNotFoundError("No module named 'fcntl'", name="fcntl")


sys.meta_path.insert(0, WindowsLikeFcntl())
sys.modules.pop("fcntl", None)

_msvcrt = types.ModuleType("msvcrt")
_msvcrt.LK_LOCK, _msvcrt.LK_NBLCK, _msvcrt.LK_UNLCK = 0, 1, 2
_msvcrt.locking = lambda *a, **k: None
sys.modules["msvcrt"] = _msvcrt

import ctypes
_real_cdll = ctypes.CDLL


class _WindowsCDLL(_real_cdll):
    def __init__(self, name, *a, **k):
        if name is None:
            raise TypeError("LoadLibrary() argument 1 must be str, not None")
        super().__init__(name, *a, **k)


ctypes.CDLL = _WindowsCDLL
sys.platform = "win32"
sys.path.insert(0, os.path.join(ROOT, "windows"))
sys.path.insert(0, ROOT)

if MODE == "probe-bare":                 # instrument: hardware failure 1
    import claude_pet                    # noqa: F401
    print("RESULT " + json.dumps({"stage": "bare-import-did-not-fail"}))
    raise SystemExit(0)
if MODE == "probe-path-only":            # instrument: hardware failure 2
    sys.path.insert(0, COMPAT)
    import claude_pet                    # noqa: F401
    print("RESULT " + json.dumps({"stage": "path-only-did-not-fail"}))
    raise SystemExit(0)

mod = importlib.import_module(TARGET)
core = sys.modules.get("claude_pet")
wu = sys.modules.get("win_update")
out = {
    "target": TARGET,
    "core_imported": core is not None,
    "core_name": getattr(core, "__name__", None),
    "app_version": getattr(core, "APP_VERSION", None),
    "core_callables": sorted(n for n in ("_zip_members_are_safe", "_weigh_usage", "_ver_tuple")
                             if callable(getattr(core, n, None))),
    "renameatx_is_none": getattr(core, "_RENAMEATX_NP", "missing") is None,
    "fcntl_from_compat": os.path.dirname(getattr(sys.modules.get("fcntl"), "__file__", "")) == COMPAT,
    "win_update_cp_is_core": (wu is not None and getattr(wu, "cp", None) is core),
    "module_loaded": getattr(mod, "__name__", None),
}
print("RESULT " + json.dumps(out))
'''


def _run_child(target, mode="import"):
    """Run the simulated-Windows import in a child. → (rc, stdout, stderr, result-dict|None)."""
    with tempfile.TemporaryDirectory(prefix="cpw-f1-") as tmp:
        script = os.path.join(tmp, "simwin.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(_CHILD)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p = subprocess.run([sys.executable, script, ROOT, target, mode],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    payload = None
    for line in p.stdout.splitlines():
        if line.startswith("RESULT "):
            payload = json.loads(line[len("RESULT "):])
    return p.returncode, p.stdout, p.stderr, payload


def _tail(text, n=12):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


class SimulationInstrumentTests(unittest.TestCase):
    """Instrument pin (expected green before and after the fix): the harness above
    really reproduces the two hardware failures, in the order the hardware hit them.

    ``str.replace``-style instruments cannot fail, and neither can a simulation
    that quietly stopped simulating: if a future Python or a stdlib change made
    the child import ``claude_pet`` successfully with no work-around at all, every
    F1 gate below would go green while testing nothing. These two probes are what
    make that impossible — they assert the *unfixed* path still fails, and with
    which exception.

    | probe            | what the child does                    | **expected**                        |
    | probe-bare       | ``import claude_pet``, nothing else    | **ModuleNotFoundError, 'fcntl'**    |
    | probe-path-only  | compat on sys.path, then import        | **TypeError, LoadLibrary()… None**  |

    The second row is the rival "a sys.path hack is the whole fix": it puts the
    shim exactly where a partial fix would and still dies, one import later.
    """

    def test_stage_one_is_the_missing_fcntl(self):
        rc, out, err, _ = _run_child("claude_pet", mode="probe-bare")
        self.assertNotEqual(rc, 0, f"the bare import was expected to fail:\n{out}")
        self.assertIn("ModuleNotFoundError", err, _tail(err))
        self.assertIn("No module named 'fcntl'", err, _tail(err))

    def test_stage_two_is_the_cdll_none_typeerror(self):
        rc, out, err, _ = _run_child("claude_pet", mode="probe-path-only")
        self.assertNotEqual(rc, 0, f"the path-only import was expected to fail:\n{out}")
        self.assertIn("TypeError", err, _tail(err))
        self.assertIn("LoadLibrary() argument 1 must be str, not None", err, _tail(err))


class SimulatedWindowsImportTests(unittest.TestCase):
    """F1 — ``windows/win_update.py``, ``windows/verify_win_artifact.py`` and
    ``windows/build_win.py`` must import under a Windows-like environment.

    On hardware all three die at their first import. Each gate below runs one
    module in the child described above, which supplies no work-around of its
    own, so the import can only succeed if the module reaches the core through
    a helper that performs both detours.

    Rivals, and the row that kills each:

    | fixture                    | ONLY-BW | PATH-ONLY | HELPER-UNUSED | **expected** |
    | import win_update          | fail✗   | fail✗     | fail✗         | **ok**       |
    | import verify_win_artifact | fail✗   | fail✗     | fail✗         | **ok**       |
    | import build_win           | ok      | fail✗     | fail✗         | **ok**       |
    | AST: who imports the core  | 3 sites✗| 3 sites✗  | ≥1 site✗      | **1 site**   |

    * ONLY-BW = "put the work-around in build_win.py, where the report started".
      Killed by the first two rows.
    * PATH-ONLY = "insert windows/compat on sys.path and be done". Killed by
      every row, with the TypeError the instrument test above pins.
    * HELPER-UNUSED = "add win_core.py but leave the old ``import claude_pet``
      in place". Killed by the AST row, and by all three import rows whenever
      the old import still runs first.

    The result payload also pins that what came back is a *working* core, not a
    stub that merely imported: ``APP_VERSION``, three callables the port and the
    artifact gate reach through, ``_RENAMEATX_NP is None`` (the Windows fallback
    was taken, i.e. the CDLL detour ran rather than being skipped) and
    ``fcntl`` resolved to ``windows/compat``.
    """

    def _assert_imports(self, target):
        rc, out, err, payload = _run_child(target)
        self.assertEqual(rc, 0, f"{target} does not import under a Windows-like environment:\n{_tail(err)}")
        self.assertIsNotNone(payload, f"no RESULT line from the child:\n{out}\n{_tail(err)}")
        self.assertTrue(payload["core_imported"], payload)
        self.assertEqual(payload["core_name"], "claude_pet", payload)
        self.assertIsInstance(payload["app_version"], str, payload)
        self.assertTrue(payload["app_version"].strip(), payload)
        self.assertEqual(payload["core_callables"],
                         ["_ver_tuple", "_weigh_usage", "_zip_members_are_safe"], payload)
        self.assertTrue(payload["renameatx_is_none"], f"the CDLL detour did not run: {payload}")
        self.assertTrue(payload["fcntl_from_compat"], f"fcntl did not come from windows/compat: {payload}")
        self.assertTrue(payload["win_update_cp_is_core"], f"win_update.cp is not the core: {payload}")
        return payload

    def test_win_update_imports(self):
        self._assert_imports("win_update")

    def test_verify_win_artifact_imports(self):
        self._assert_imports("verify_win_artifact")

    def test_build_win_imports(self):
        self._assert_imports("build_win")


def _core_import_sites(path):
    """Every place a module reaches ``claude_pet`` by name → [(lineno, form)]."""
    tree = ast.parse(_read(path))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "claude_pet" or a.name.startswith("claude_pet."):
                    hits.append((node.lineno, "import " + a.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "claude_pet" or mod.startswith("claude_pet.") or mod.endswith(".claude_pet"):
                hits.append((node.lineno, "from " + mod + " import …"))
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name not in ("import_module", "__import__"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, ast.Constant) and arg.value == "claude_pet":
                    hits.append((node.lineno, name + '("claude_pet")'))
    return hits


class OneOwnerForTheCoreImportTests(unittest.TestCase):
    """F1 — exactly one module under ``windows/`` may name ``claude_pet``.

    The hardware work-around the peer had to invent (a session-local
    ``sitecustomize.py`` plus ``windows/compat`` on ``PYTHONPATH``) exists
    because the two detours live in ``claude_pet_win._import_core`` and nothing
    else can reach them. Consolidating them is only worth anything if every
    other entry point then goes through the one owner, so that is what is
    pinned: ``windows/win_core.py`` is the sole importer, by AST rather than by
    grep, counting ``import``, ``from … import`` and
    ``importlib.import_module("claude_pet")`` alike.

    Scope: the modules directly under ``windows/`` — not ``windows/tests/``
    (this suite imports the core on purpose, from a macOS host) and not
    ``windows/compat/`` (the shim is imported *by* the core, never the reverse).

    Rivals: GREP = a text search for "import claude_pet" (misses
    ``importlib.import_module``, which is precisely how ``claude_pet_win``
    reaches it today), COUNT = "at most one per file" (a helper plus a
    left-behind direct import in the same file passes).
    """

    def _modules(self):
        return sorted(p for p in os.listdir(WINDIR)
                      if p.endswith(".py") and os.path.isfile(os.path.join(WINDIR, p)))

    def test_the_helper_module_exists_and_exposes_import_core(self):
        self.assertTrue(os.path.isfile(os.path.join(WINDIR, "win_core.py")),
                        "windows/win_core.py is missing — nothing owns the core import")
        wc = _mod(CORE_HELPER)
        self.assertTrue(callable(getattr(wc, "import_core", None)),
                        "win_core.import_core() is missing")

    def test_only_win_core_names_the_core(self):
        offenders = {}
        for name in self._modules():
            if name == "win_core.py":
                continue
            sites = _core_import_sites(os.path.join(WINDIR, name))
            if sites:
                offenders[name] = sites
        self.assertEqual(offenders, {},
                         "these modules reach claude_pet without the helper: " + repr(offenders))

    def test_win_core_actually_imports_the_core(self):
        sites = _core_import_sites(os.path.join(WINDIR, "win_core.py"))
        self.assertTrue(sites, "win_core.py never imports claude_pet — it cannot be the owner")

    def test_the_helper_leaves_this_host_as_it_found_it(self):
        """What import_core() may add is host-dependent; what it must restore is not.

        The previous version of this test asserted the no-op half unconditionally and
        was named ``..._is_a_no_op_on_this_host``. That is wrong on the one host the
        Windows port ships to: ``win_core``'s own docstring says the two detours are
        added **on win32 and nowhere else**, so putting ``windows/compat`` on
        ``sys.path`` there is the documented contract, not a leak. Run on Windows the
        old assertion failed against correct code, which is the worst kind of red —
        it accuses the thing that is right.

        Split by host, because the two hosts make genuinely different promises:

        * everywhere — the core comes back, the call is idempotent, and the ``CDLL``
          wrapper is gone by the time it returns (``finally``). This is the half that
          actually protects anything: a leaked wrapper would follow every later
          ``ctypes`` user in the process.
        * non-win32 — nothing at all is added to ``sys.path``.
        * win32 — ``windows/compat`` is added (so the core's own ``import fcntl``
          binds to the shim) and nothing *else* is.
        """
        import ctypes
        wc = _mod(CORE_HELPER)
        before_cdll = ctypes.CDLL
        before_path = list(sys.path)
        compat = os.path.join(WINDIR, "compat")
        core = wc.import_core()
        self.assertIs(core, sys.modules["claude_pet"])
        self.assertIs(wc.import_core(), core, "import_core() is not idempotent")
        self.assertIs(ctypes.CDLL, before_cdll, "the CDLL wrapper leaked out of import_core()")
        added = [q for q in sys.path if q not in before_path]
        if sys.platform == "win32":
            self.assertIn(compat, sys.path,
                          "windows/compat is not on sys.path — the core's `import fcntl` "
                          "cannot reach the shim")
            self.assertEqual([q for q in added if q != compat], [],
                             "import_core() added something other than windows/compat")
        else:
            self.assertNotIn(compat, sys.path,
                             "windows/compat was put on sys.path on a non-Windows host")
            self.assertEqual(added, [],
                             "import_core() changed sys.path on a non-Windows host")

    def test_every_windows_entry_point_still_imports_here(self):
        for name in (CORE_HELPER, WU, WA, BW, VWA):
            with self.subTest(module=name):
                self.assertTrue(_mod(name))


# ═══════════════════════════════════════════════════════════════════════════════
# F2 — the Inno uninstall subkey
# ═══════════════════════════════════════════════════════════════════════════════

UNINSTALL_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


def _iss_directive(text, name):
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*(.+?)\s*$", text)
    return m.group(1) if m else None


def _inno_uninstall_key_name(app_id_raw):
    """installer.iss's ``AppId=`` text → the registry subkey name Inno creates.

    Inno expands a *leading* ``{{`` to one literal ``{`` (that is the only
    brace escape it applies to an AppId); every other character, the trailing
    ``}}`` included, is carried through unchanged, and the uninstaller appends
    ``_is1``. So ``{{me.yeongyu.claudepet}}`` becomes the key
    ``{me.yeongyu.claudepet}}_is1`` — two closing braces, which is what the
    hardware's uninstall log printed.
    """
    name = app_id_raw.strip()
    if name.startswith("{{"):
        name = name[1:]
    return name + "_is1"


class InnoUninstallKeyTests(unittest.TestCase):
    """F2 — ``win_update.INNO_UNINSTALL_SUBKEY`` must be the key Inno actually writes.

    The expected value is *derived here from installer.iss* rather than
    transcribed from the hardware log: the AppId and the constant then cannot
    drift apart again, and the gate keeps working if the AppId is ever changed.

    | fixture                                   | ONE-BRACE (today) | LITERAL     | **expected**                    |
    | AppId ``{{me.yeongyu.claudepet}}``        | …claudepet}_is1 ✗ | …}}}_is1 ✗  | **{me.yeongyu.claudepet}}_is1** |
    | hive keyed by the derived name            | portable ✗        | portable ✗  | **inno**                        |
    | empty hive (a portable copy)              | portable          | portable    | **portable**                    |

    * ONE-BRACE = the shipped constant: the AppId with both braces collapsed.
      It is what makes a real installed copy report ``portable``, which in turn
      showed the user a portable uninstall plan (leaving ``unins000.exe``, the
      ARP entry and the Start-Menu shortcut behind) and routed an installed
      copy's in-app update through the folder swap instead of the silent Inno
      upgrade.
    * LITERAL = "the AppId text as written, braces and all" — the other way to
      get it wrong, and it ties with ONE-BRACE on the reader rows, which is why
      row 1 is derived and asserted on its own.

    The reader fixture is the hardware's own experiment: a hive keyed by the
    **real** subkey name, read through whatever constant the code holds. A
    wrong constant misses the key exactly as ``winreg`` does, and
    ``install_kind`` reads that as ``portable``.
    """

    def setUp(self):
        self.iss = _read(ISS)
        self.app_id = _iss_directive(self.iss, "AppId")
        self.assertIsNotNone(self.app_id, "installer.iss has no AppId")
        self.key_name = _inno_uninstall_key_name(self.app_id)
        self.expected = UNINSTALL_ROOT + "\\" + self.key_name

    def test_the_derivation_itself(self):
        self.assertEqual(_inno_uninstall_key_name("{{me.yeongyu.claudepet}}"),
                         "{me.yeongyu.claudepet}}_is1")
        self.assertEqual(self.app_id, "{{me.yeongyu.claudepet}}")
        self.assertEqual(self.key_name, "{me.yeongyu.claudepet}}_is1")

    def test_the_constant_is_the_key_inno_writes(self):
        wu = _mod(WU)
        self.assertEqual(wu.INNO_UNINSTALL_SUBKEY, self.expected)
        self.assertTrue(wu.INNO_UNINSTALL_SUBKEY.endswith("}}_is1"),
                        "the trailing '}' of the AppId survives; only the leading '{{' collapses")

    def _exe_dir_with_uninstaller(self):
        tmp = tempfile.mkdtemp(prefix="cpw-f2-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        wu = _mod(WU)
        with open(os.path.join(tmp, wu.UNINS_NAME), "wb") as f:
            f.write(b"MZ")
        return tmp

    def _reader_over(self, hive):
        """A reader keyed by *subkey name*, as winreg is: a wrong constant raises."""
        wu = _mod(WU)

        def reader(value_name):
            return hive[wu.INNO_UNINSTALL_SUBKEY][value_name]
        return reader

    def test_a_real_installed_copy_reads_as_inno(self):
        wu = _mod(WU)
        exe_dir = self._exe_dir_with_uninstaller()
        exe = os.path.join(exe_dir, wu.EXE_NAME)
        hive = {self.expected: {"InstallLocation": exe_dir}}
        self.assertEqual(wu.install_kind(exe, self._reader_over(hive)), "inno")

    def test_a_portable_copy_still_reads_as_portable(self):
        wu = _mod(WU)
        exe_dir = self._exe_dir_with_uninstaller()
        exe = os.path.join(exe_dir, wu.EXE_NAME)
        self.assertEqual(wu.install_kind(exe, self._reader_over({})), "portable")

    def test_the_inno_uninstall_plan_still_runs_the_uninstaller(self):
        wu = _mod(WU)
        plan = wu.uninstall_plan("inno", r"C:\nonexistent\ClaudePet", r"C:\nonexistent\home")
        self.assertEqual(plan[-1][0], "run")
        argv = plan[-1][1]
        self.assertTrue(str(argv[0]).endswith(wu.UNINS_NAME), argv)
        self.assertIn("/SILENT", argv)

    def test_every_other_spelling_of_the_key_agrees(self):
        """installer.iss, win_update.py, claude_pet_win.py and README.md are one fact."""
        bad = {}
        for path in (os.path.join(WINDIR, "win_update.py"), PORT, README):
            for n, line in enumerate(_read(path).splitlines(), 1):
                if "_is1" not in line:
                    continue
                if self.key_name not in line:
                    bad.setdefault(os.path.basename(path), []).append((n, line.strip()))
        self.assertEqual(bad, {}, "these spell the uninstall key the old way: " + repr(bad))


# ═══════════════════════════════════════════════════════════════════════════════
# F3 — the StartupApproved first byte
# ═══════════════════════════════════════════════════════════════════════════════

FILETIME = bytes.fromhex("1032547698badcfe")          # any 8 bytes; the value is never read
HW_DISABLED = b"\x01\x00\x00\x00" + FILETIME          # observed: disabled through Settings › Startup apps
HW_ENABLED = bytes(12)                                # observed: re-enabled through Settings › Startup apps
THIRD_PARTY = b"\x02" + bytes(11)                     # observed on entries this UI never touched
OLD_DISABLED = b"\x03" + bytes(11)
EVEN_4 = b"\x04" + bytes(11)
ODD_5 = b"\x05" + bytes(11)


class StartupApprovedByteRuleTests(unittest.TestCase):
    """F3 — ``win_autostart.startup_approved_enabled(blob)``: the even/odd rule.

    The shipped rule ("``0x02`` enabled, anything else not") was written from
    memory and the hardware refutes it: disabling wrote ``01 00 00 00`` +
    FILETIME and re-enabling wrote twelve zero bytes, so ``0x00`` — the value
    the shipped rule reads as *disabled* — is the byte Windows writes for
    *enabled*. Entries this UI never touched carry ``0x02``, so that value is
    real too. The rule gated here is the low bit of the first byte: even means
    enabled, odd means disabled.

    Rivals:

    * EQ2 = ``blob[0] == 0x02`` (shipped),
    * TABLE = ``blob[0] in (0x00, 0x02)`` — the four-value lookup someone
      writes straight off the hardware report,
    * NE3 = ``blob[0] != 0x03`` (the rival the previous suite already listed),
    * NE13 = ``blob[0] not in (0x01, 0x03)``,
    * EVEN = ``blob[0] % 2 == 0`` (expected).

    | blob                        | EQ2   | TABLE | NE3    | NE13   | **EVEN / expected** |
    | 00 ×12 (re-enabled)         | False✗| True  | True   | True   | **True**            |
    | 01 00 00 00 + FILETIME      | False | False | True ✗ | False  | **False**           |
    | 02 00…00 (third party)      | True  | True  | True   | True   | **True**            |
    | 03 00…00                    | False | False | False  | False  | **False**           |
    | 04 00…00                    | False✗| False✗| True   | True   | **True**            |
    | 05 00…00                    | False | False | True ✗ | True ✗ | **False**           |
    | b"" / None / "\\x00" (str)   | False | False | raises | raises | **False**           |

    Row 1 kills EQ2 on its own. Rows 4 and 5 are the discriminating pair no
    fixture drawn only from ``0x00``–``0x03`` can supply: TABLE agrees with
    EVEN on every observed byte and disagrees at ``0x04``, and NE3/NE13 agree
    everywhere except at an odd byte above ``0x03``.

    ``0x04``/``0x05`` are **extrapolation, not observation** — the hardware
    reported ``0x00``, ``0x01`` and ``0x02`` only. They gate the rule the port
    chose to implement, and the function's docstring must say which half is
    which, so a later hardware run can refute the extrapolation without having
    to re-derive the observed part.

    The guards are unchanged and are re-pinned here rather than inherited:
    a non-``bytes`` value, an empty blob and ``None`` all read as *not*
    enabled, and nothing raises. The fail-safe direction is the same as before
    — an unreadable blob read as "on" shows a checkmark Windows does not
    honour, and no click fixes it.
    """

    ROWS = (
        ("re-enabled through the UI (12 zero bytes)", HW_ENABLED, True),
        ("disabled through the UI (01 + FILETIME)", HW_DISABLED, False),
        ("a third-party entry (02 …)", THIRD_PARTY, True),
        ("03 …", OLD_DISABLED, False),
        ("04 … (even, extrapolated)", EVEN_4, True),
        ("05 … (odd, extrapolated)", ODD_5, False),
        ("one byte 00", b"\x00", True),
        ("one byte 01", b"\x01", False),
        ("bytearray 00", bytearray(12), True),
        ("bytearray 01", bytearray(b"\x01" + bytes(11)), False),
        ("empty", b"", False),
        ("None", None, False),
        ("str", "\x00", False),
        ("int", 0, False),
        ("list of ints", [0, 0, 0], False),
        ("memoryview is not bytes", memoryview(b"\x00"), False),
    )

    def test_table(self):
        wa = _mod(WA)
        for label, blob, expected in self.ROWS:
            with self.subTest(case=label):
                self.assertIs(wa.startup_approved_enabled(blob), expected)

    def test_the_whole_range_of_the_first_byte(self):
        """No lookup table survives all 256 first bytes. One assertion, so the
        failure names the disagreeing bytes instead of printing 128 tracebacks."""
        wa = _mod(WA)
        wrong = [hex(b) for b in range(256)
                 if wa.startup_approved_enabled(bytes([b]) + bytes(11)) is not (b % 2 == 0)]
        self.assertEqual(wrong, [], f"{len(wrong)} first bytes disagree with the even/odd rule, "
                                    f"starting at {wrong[:8]}")

    def test_the_docstring_records_which_half_is_observed(self):
        wa = _mod(WA)
        doc = (wa.startup_approved_enabled.__doc__ or "")
        low = doc.lower()
        self.assertTrue(("even" in low and "odd" in low) or ("짝수" in doc and "홀수" in doc),
                        "the docstring must state the even/odd rule:\n" + doc)
        for token in ("0x00", "0x01", "0x02", "0x03"):
            self.assertIn(token, doc, f"the docstring never names {token}:\n{doc}")
        self.assertTrue("Windows 11" in doc or "windows 11" in low,
                        "the docstring must carry the observation's provenance (one machine, Windows 11)")


class AutostartSymptomTests(unittest.TestCase):
    """F3 — the user-visible symptom, end to end through ``autostart_read_state``.

    Reported: "Run 값이 있고 StartupApproved 가 00…(= Windows 기준 사용, 설정
    화면도 켬)인 상태에서 우클릭 메뉴의 '로그인 시 자동 실행' 이 체크 없이
    나옵니다." The menu asks ``autostart_read_state``; with the shipped byte
    rule that reads "off" while Windows launches the app anyway, and the next
    click deletes the Run value — the click makes the disagreement worse.

    | Run value       | StartupApproved  | EQ2 (shipped) | **expected** |
    | ours, quoted    | 00 ×12           | "off" ✗       | **"on"**     |
    | ours, quoted    | 01 + FILETIME    | "off"         | **"off"**    |
    | ours, quoted    | absent           | "on"          | **"on"**     |
    | ours, quoted    | 02 …             | "on"          | **"on"**     |
    | someone else's  | 00 ×12           | "off"         | **"off"**    |
    | absent          | 00 ×12           | "off"         | **"off"**    |
    | not frozen      | —                | "unavailable" | **"unavailable"** |

    The toggle row that follows it is the other half of the symptom: from the
    first state one click must turn autostart *off* (delete the Run value), not
    re-write it. Under the shipped rule the same click takes the "off" branch
    and writes the value that is already there, so the item never unchecks.
    """

    EXE = r"C:\Users\x\AppData\Local\Programs\ClaudePet\ClaudePet.exe"
    OTHER = r"D:\Tools\ClaudePet\ClaudePet.exe"

    def _reader(self, run, approved):
        wa = _mod(WA)

        def reader(subkey, name):
            self.assertEqual(name, wa.RUN_VALUE_NAME)
            if subkey == wa.RUN_SUBKEY:
                return run
            if subkey == wa.STARTUP_APPROVED_SUBKEY:
                return approved
            raise AssertionError("unexpected subkey: " + subkey)
        return reader

    def test_read_state_table(self):
        wa = _mod(WA)
        rows = (
            ('"' + self.EXE + '"', HW_ENABLED, True, "on"),
            ('"' + self.EXE + '"', HW_DISABLED, True, "off"),
            ('"' + self.EXE + '"', None, True, "on"),
            ('"' + self.EXE + '"', THIRD_PARTY, True, "on"),
            ('"' + self.OTHER + '"', HW_ENABLED, True, "off"),
            (None, HW_ENABLED, True, "off"),
            ('"' + self.EXE + '"', HW_ENABLED, False, "unavailable"),
        )
        for run, approved, frozen, expected in rows:
            with self.subTest(run=run, approved=approved, frozen=frozen):
                self.assertEqual(wa.autostart_read_state(self._reader(run, approved), self.EXE, frozen),
                                 expected)

    def test_one_click_from_the_reported_state_turns_it_off(self):
        wa = _mod(WA)
        store = {wa.RUN_SUBKEY: {wa.RUN_VALUE_NAME: '"' + self.EXE + '"'},
                 wa.STARTUP_APPROVED_SUBKEY: {wa.RUN_VALUE_NAME: HW_ENABLED}}

        def reader(subkey, name):
            return store.get(subkey, {}).get(name)

        def writer(subkey, name, data):
            if data is None:
                store.get(subkey, {}).pop(name, None)
            else:
                store.setdefault(subkey, {})[name] = data

        state, err = wa.autostart_toggle(reader, writer, self.EXE, True)
        self.assertIsNone(err)
        self.assertEqual(state, "off")
        self.assertNotIn(wa.RUN_VALUE_NAME, store.get(wa.RUN_SUBKEY, {}),
                         "the Run value survived a click that was meant to turn autostart off")
        self.assertNotIn(wa.RUN_VALUE_NAME, store.get(wa.STARTUP_APPROVED_SUBKEY, {}),
                         "the StartupApproved entry was left behind and would block a later enable")


class StartupApprovedDocTests(unittest.TestCase):
    """F3 — ``windows/README.md`` records the corrected encoding and its provenance.

    The README's "실기에서 확인할 것" list is what sent the hardware session
    looking at these bytes, and it currently states the refuted rule. Under
    AGENTS.md §5 the replacement has to keep three things apart: what the one
    Windows 11 machine wrote (``0x00``/``0x01``, and ``0x02`` on entries the UI
    never touched), the rule the code implements (even enabled / odd disabled),
    and the fact that everything above ``0x03`` is extrapolation.
    """

    def test_readme_states_the_even_odd_rule_with_its_provenance(self):
        text = _read(README)
        low = text.lower()
        self.assertIn("StartupApproved", text)
        self.assertTrue(("짝수" in text and "홀수" in text) or ("even" in low and "odd" in low),
                        "README does not state the even/odd rule")
        for token in ("0x00", "0x01", "0x02", "0x03"):
            self.assertIn(token, text, f"README never names {token}")
        self.assertIn("Windows 11", text, "README does not say which machine the bytes came from")
        self.assertTrue("작업 관리자" in text or "Task Manager" in text,
                        "README does not name where the observation was made")


# ═══════════════════════════════════════════════════════════════════════════════
# F4 — uninstalling while the pet is running
# ═══════════════════════════════════════════════════════════════════════════════

def _iss_entries(text, section):
    """Non-comment entry lines of one .iss section, in file order."""
    out, inside = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = (s.lower() == "[" + section.lower() + "]")
            continue
        if inside and s and not s.startswith(";"):
            out.append(s)
    return out


def _iss_comments(text, section):
    out, inside = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = (s.lower() == "[" + section.lower() + "]")
            continue
        if inside and s.startswith(";"):
            out.append(s.lstrip("; ").strip())
    return out


def _iss_params(entry):
    """One entry line → {lowercased key: value}. Quote-aware on the ';' separator."""
    parts, cur, quoted = [], "", False
    for ch in entry:
        if ch == '"':
            quoted = not quoted
            cur += ch
        elif ch == ";" and not quoted:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    out = {}
    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        out[k.strip().lower()] = v.strip().strip('"')
    return out


DELETE_VERBS = ("del ", "erase ", "rd ", "rmdir", "remove-item", "format ", "/s /q")


class InstallerClosesTheAppTests(unittest.TestCase):
    """F4 — ``installer.iss``'s uninstall path must close the running app before
    it deletes files.

    Hardware, pet running: "Failed to delete the file; it may be in use (5)"
    for ``ClaudePet.exe`` and 44 files under ``_internal\\``, uninstaller
    rc=0, ARP entry and Run value already gone. There is no retry and no way
    back — the user has to delete the folder by hand.

    **Why the two directives already in the file do not satisfy this gate.**
    ``CloseApplications=yes`` and ``RestartApplications=yes`` were present at
    ``f876e40``, which is the commit the failure was observed on, and the
    uninstall log carried no Restart Manager / CloseApplications step at all.
    A gate that accepted them would be satisfied by the exact tree that
    failed. So an explicit ``[UninstallRun]`` kill step is required; the
    Restart Manager directives may stay or be extended alongside it, and this
    gate neither requires nor forbids that.

    | fixture                                     | TODAY | RM-ONLY | **expected** |
    | an [UninstallRun] entry naming ClaudePet.exe| none✗ | none✗   | **present**  |
    | …with a RunOnceId                           | —     | —       | **present**  |
    | …with runhidden                             | —     | —       | **present**  |
    | …with skipifdoesntexist                     | —     | —       | **present**  |
    | …deleting nothing                           | —     | —       | **no verb**  |

    * TODAY = the shipped file. * RM-ONLY = "add/keep the Restart Manager
      directives and call it fixed" — the state the failure was observed in.
    * ``skipifdoesntexist`` is the tolerance pin: the step must not turn a
      machine without the tool it calls into a failed uninstall, and it must
      not care whether the process is actually running.
    * The "deleting nothing" row is adversarial: a kill step is not a licence
      to sweep the install directory from a shell.

    **Correction (closing round, B3).** An earlier version of this docstring
    carried a third rival column, POSTUNINST — "an ``[UninstallRun]`` entry
    that runs *after* the files are removed" — and the sentence "That flag is
    the ordering pin: without it, an ``[UninstallRun]`` entry runs at the start
    of the uninstall, before file removal." Both are wrong, and the round-2
    review refuted them: **``postuninstall`` is not an Inno Setup flag.** It
    is absent from the complete Flags list for ``[Run]``/``[UninstallRun]``
    (<https://jrsoftware.org/ishelp/topic_runsection.htm>); the "post-uninstall"
    concept exists only as the ``usPostUninstall`` ``TUninstallStep`` constant
    reached from ``CurUninstallStepChanged`` in ``[Code]``. So the POSTUNINST
    rival cannot be written, the row it occupied proved nothing, and the
    ordering it described as conditional is in fact **unconditional**: the same
    page says an ``[UninstallRun]`` program is executed "as the first step of
    uninstallation", full stop.

    The ``assertNotIn("postuninstall", flags)`` line below is kept — it costs
    nothing and documents the misconception — but **it is not the ordering pin
    and must not be read as one.** The flags that can actually defeat this fix
    are ``nowait``, ``shellexec`` and ``waituntilidle``, each of which removes
    Inno's documented ``waituntilterminated`` default so file removal starts
    before ``taskkill`` returns. Those are pinned, together with an allow-list
    over the whole flag set, in
    ``windows/tests/test_win_uninstall_contract.InstallerUninstallRunTests``.
    """

    def setUp(self):
        self.iss = _read(ISS)
        self.entries = _iss_entries(self.iss, "UninstallRun")

    def _kill_entries(self):
        out = []
        for e in self.entries:
            p = _iss_params(e)
            blob = " ".join([p.get("filename", ""), p.get("parameters", "")]).lower()
            if "claudepet.exe" in blob:
                out.append((e, p))
        return out

    def test_there_is_an_uninstall_run_step_that_closes_the_app(self):
        self.assertTrue(self.entries, "installer.iss has no [UninstallRun] section")
        self.assertTrue(self._kill_entries(),
                        "no [UninstallRun] entry names ClaudePet.exe: " + repr(self.entries))

    def test_the_step_runs_before_file_removal_and_tolerates_absence(self):
        kills = self._kill_entries()
        self.assertTrue(kills, "no [UninstallRun] entry names ClaudePet.exe — nothing to order")
        for entry, p in kills:
            with self.subTest(entry=entry):
                flags = p.get("flags", "").lower().split()
                self.assertTrue(p.get("runonceid", "").strip(),
                                "the kill step has no RunOnceId — an upgrade would run it twice")
                self.assertIn("runhidden", flags, "the kill step must not flash a console window")
                self.assertNotIn("postuninstall", flags,
                                 "postuninstall runs the step AFTER the files are removed — "
                                 "that is the failure, not the fix")
                self.assertIn("skipifdoesntexist", flags,
                              "the kill step must not fail the uninstall when its tool is absent")

    def test_the_kill_step_deletes_nothing(self):
        kills = self._kill_entries()
        self.assertTrue(kills, "no [UninstallRun] entry names ClaudePet.exe — nothing to inspect")
        for entry, p in kills:
            blob = (p.get("filename", "") + " " + p.get("parameters", "")).lower()
            for verb in DELETE_VERBS:
                with self.subTest(entry=entry, verb=verb):
                    self.assertNotIn(verb, blob,
                                     "the close-the-app step must not delete anything itself")

    def test_a_comment_names_the_mechanism_relied_on(self):
        comments = " ".join(_iss_comments(self.iss, "UninstallRun")).lower()
        self.assertTrue(comments.strip(), "[UninstallRun] carries no comment")
        self.assertTrue("taskkill" in comments or "restart manager" in comments
                        or "restartmanager" in comments,
                        "the comment must name the mechanism the uninstall relies on: " + comments)


class PreservedUserFilesTests(unittest.TestCase):
    """F4 — the two things an uninstall must never take, re-pinned independently.

    Hardware, pet closed: the uninstall removed everything except
    ``%USERPROFILE%\\.claude_pet`` and ``.claude_pet.json``. Both survive
    because *the installer* never lists them, so this pin is over the
    installer's delete sections — ``[UninstallDelete]``, ``[InstallDelete]``
    and the new kill step. It is deliberately **not** extended to
    ``win_update.uninstall_plan``: the in-app "완전 삭제…" does delete
    ``.claude_pet.json``, on purpose, in parity with the macOS
    ``UNINSTALL_PATHS``. Only the pets directory is off-limits to both, and
    that half is asserted for the plan as well.

    | fixture                              | SWEEP-HOME | SWEEP-APP | **expected**       |
    | .claude_pet in a delete section      | present ✗  | absent    | **absent**         |
    | .claude_pet.json in a delete section | present ✗  | absent    | **absent**         |
    | {userprofile} in a delete section    | present ✗  | absent    | **absent**         |
    | ~/.claude_pet in uninstall_plan      | present ✗  | present ✗ | **absent**         |

    SWEEP-HOME = "delete the app's dot-files from the profile while we are
    here"; SWEEP-APP = "``filesandordirs {app}``", which the existing suite
    already gates and which this one does not duplicate.
    """

    def test_the_installer_never_names_the_users_pets_or_config(self):
        iss = _read(ISS)
        sections = ("UninstallDelete", "InstallDelete", "UninstallRun")
        for section in sections:
            for entry in _iss_entries(iss, section):
                low = entry.lower()
                for needle in (".claude_pet", "{userprofile}", "%userprofile%", "{userappdata}"):
                    with self.subTest(section=section, entry=entry, needle=needle):
                        self.assertNotIn(needle, low,
                                         f"[{section}] reaches the user's own files: {entry}")

    def test_the_in_app_plan_never_names_the_pets_directory(self):
        wu = _mod(WU)
        home = r"C:\nonexistent\home"
        for kind in ("inno", "portable"):
            plan = wu.uninstall_plan(kind, r"C:\nonexistent\ClaudePet", home)
            for op, arg in plan:
                for p in ([arg] if isinstance(arg, str) else list(arg)):
                    s = str(p).replace("/", "\\").lower()
                    base = (home + r"\.claude_pet").lower()
                    with self.subTest(kind=kind, step=(op, arg)):
                        self.assertFalse(s == base or s.startswith(base + "\\"),
                                         f"{p} is the user's pets directory")


def _func_def(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _calls(node):
    """[(lineno, dotted-ish name)] for every Call under ``node``."""
    out = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        if isinstance(fn, ast.Attribute):
            out.append((n.lineno, fn.attr, n))
        elif isinstance(fn, ast.Name):
            out.append((n.lineno, fn.id, n))
    return out


class InAppInnoUninstallOrderTests(unittest.TestCase):
    """F4 — the refusable precheck in ``_uninstall``'s inno branch.

    **Scope correction (closing round).** This class used to carry two more
    tests — "the uninstaller is not launched while the app is still running"
    and "a moment is given for the process to exit" — written to accept either
    of two implementations, QUIT-FIRST or PID-WAIT, and each opening with

        if self._pid_wait():
            self.skipTest(...)

    where ``_pid_wait()`` was ``any(name == "getpid" …)`` over the branch's
    calls. The tree took the PID-WAIT route, so **both tests skipped
    themselves on every run** and the suite reported ``OK (skipped=2)`` while
    gating nothing: the predicate is satisfied by any implementation that
    passes ``os.getpid()`` to any callee, including one that hands it to a
    helper that never waits. Those two tests have been **deleted**, not
    repaired, because the obligation they were meant to carry is now stated
    unconditionally and split into separately-failing assertions in
    ``windows/tests/test_win_uninstall_contract.py``
    (``InAppInnoUninstallOrderTests`` there pins the hand-over of the pid and
    the launch of the helper; ``InnoUninstallHelperTextTests`` pins that the
    generated helper actually waits on that pid and refuses when it is still
    alive, reading each line as code rather than as text so a commented-out
    wait fails). Keeping a skipping copy here would have left a second,
    weaker statement of the same rule in the tree, which is the state that
    made the hole hard to see in the first place.

    What remains is the one row that never skipped, and it is a regression pin
    in the other direction: the reason the launch sits where it does is that a
    ``Popen`` failure must cost the user nothing, so moving it must not take
    the refusable check with it — the ``os.path.isfile`` guard on the
    uninstaller has to stay ahead of the first irreversible delete.

    | fixture                        | NO-PRECHECK | **expected** |
    | isfile precheck before deletes | absent ✗    | **before every delete** |
    """

    def setUp(self):
        self.tree = ast.parse(_read(PORT))
        self.fn = _func_def(self.tree, "_uninstall")
        self.assertIsNotNone(self.fn, "claude_pet_win.py has no _uninstall")
        self.branch = self._inno_branch(self.fn)
        self.assertIsNotNone(self.branch, "_uninstall has no `kind == \"inno\"` branch")

    @staticmethod
    def _inno_branch(fn):
        """The statements guarded by ``kind == "inno"`` — its ``body`` only.

        Deliberately not the whole ``If`` node: its ``orelse`` holds the
        ``elif kind == "portable"`` branch, whose helper already waits on
        ``os.getpid()``, so walking the node entire would read the portable
        branch's PID wait as if the inno branch had one.
        """
        for n in ast.walk(fn):
            if not isinstance(n, ast.If):
                continue
            for cmp_node in ast.walk(n.test):
                if isinstance(cmp_node, ast.Constant) and cmp_node.value == "inno":
                    return n.body
        return None

    def _branch_calls(self):
        out = []
        for stmt in self.branch:
            out.extend(_calls(stmt))
        return out

    def test_the_refusable_precheck_still_precedes_every_irreversible_delete(self):
        prechecks = [ln for ln, name, _ in self._branch_calls() if name in ("isfile", "exists", "lexists")]
        self.assertTrue(prechecks, "the inno branch no longer checks that unins000.exe is there")
        deletes = [ln for ln, name, _ in _calls(self.fn) if name in ("rmtree", "remove", "unlink")]
        self.assertTrue(deletes, "_uninstall deletes nothing — the plan's executor moved away")
        self.assertLess(min(prechecks), min(deletes),
                        "a launch that can fail must be refused before anything is deleted")


# ═══════════════════════════════════════════════════════════════════════════════
# F5 — the exe's version resource
# ═══════════════════════════════════════════════════════════════════════════════

FIXED_STRINGS = {
    "FileDescription": "Claude Pet",
    "CompanyName": "Yeongyu Yang",
    "ProductName": "Claude Pet",
    "OriginalFilename": "ClaudePet.exe",
}
STUB_VERSION = "9.87"          # deliberately unlike any real APP_VERSION


class VersionResourceTests(unittest.TestCase):
    """F5 — ``build_win.write_version_resource(path, version)`` and the gate that checks it.

    Hardware: Settings › Apps and Task Manager show the entry as
    ``ClaudePet.exe`` with an empty publisher, while the Claude entry directly
    above reads "Claude / Anthropic, PBC". A PyInstaller exe carries no version
    resource unless one is passed with ``--version-file``.

    The generator is called **with a stub version**, never by building: the
    point is that the strings are fixed and the numbers come from the argument.

    | fixture                                  | HARDCODED | TEMPLATE-ONLY | **expected**        |
    | write_version_resource(p, "9.87")        | 0.24 ✗    | "{version}" ✗ | **9.87 everywhere** |
    | the four fixed strings                   | present   | present       | **present**         |
    | ast.parse of the file                    | ok        | ok            | **VSVersionInfo(…)**|
    | build() passes --version-file            | absent ✗  | absent ✗      | **present**         |
    | build_win derives the version from APP_VERSION | ✗   | ✗             | **app_version()**   |

    * HARDCODED = a version resource written once by hand and committed, which
      is what the task's "so it cannot go stale" forbids: it passes every
      string check and freezes the version at whatever it was when written.
      The stub row kills it — a hand-written file cannot contain 9.87.
    * TEMPLATE-ONLY = a template shipped with ``{version}`` never substituted.

    ``FileVersion``/``ProductVersion`` must carry the given version as a
    string, and the ``filevers``/``prodvers`` tuples the format requires must
    be its numeric parts padded to four (``9.87`` → ``9, 87, 0, 0``).
    """

    def _generate(self, version=STUB_VERSION):
        bw = _mod(BW)
        writer = getattr(bw, "write_version_resource", None)
        self.assertTrue(callable(writer),
                        "build_win.write_version_resource(path, version) is missing")
        tmp = tempfile.mkdtemp(prefix="cpw-f5-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        path = os.path.join(tmp, "version_info.txt")
        returned = writer(path, version)
        self.assertTrue(os.path.isfile(path), "write_version_resource wrote no file")
        self.assertEqual(os.path.abspath(str(returned)), os.path.abspath(path),
                         "write_version_resource must return the path it wrote")
        return _read(path)

    def test_the_fixed_strings_are_present(self):
        text = self._generate()
        for key, value in FIXED_STRINGS.items():
            with self.subTest(key=key):
                self.assertRegex(text, re.escape(key) + r"\W+" + re.escape(value))
        self.assertIn("LegalCopyright", text)
        self.assertIn("Yeongyu Yang", text)

    def test_the_version_comes_from_the_argument(self):
        cp = _mod("claude_pet")
        text = self._generate()
        for key in ("FileVersion", "ProductVersion"):
            with self.subTest(key=key):
                self.assertRegex(text, re.escape(key) + r"\W+" + re.escape(STUB_VERSION))
        flat = re.sub(r"\s+", "", text)
        self.assertIn("9,87,0,0", flat, "filevers/prodvers must be the numeric parts padded to four")
        self.assertNotIn(cp.APP_VERSION, text.replace(STUB_VERSION, ""),
                         "the generated file carries a version the caller did not ask for")

    def test_the_file_is_a_parseable_pyinstaller_version_resource(self):
        text = self._generate()
        tree = ast.parse(text)
        names = [n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("VSVersionInfo", names, "not a PyInstaller version resource:\n" + text[:400])
        self.assertIn("StringFileInfo", names)
        self.assertIn("FixedFileInfo", names)

    def test_the_build_passes_it_to_pyinstaller_and_derives_the_version(self):
        src = _read(os.path.join(WINDIR, "build_win.py"))
        self.assertTrue("--version-file" in src,
                        "build_win never hands the version resource to PyInstaller")
        tree = ast.parse(src)
        used = {name for _ln, name, _n in _calls(tree)}
        self.assertIn("write_version_resource", used,
                      "write_version_resource is defined but never called by the build")
        self.assertIn("app_version", used,
                      "the build must take the version from claude_pet.APP_VERSION")


class ArtifactGateKnowsTheVersionResourceTests(unittest.TestCase):
    """F5 — ``verify_win_artifact`` must check for the version resource, and must
    not pass vacuously on a host that cannot read a PE.

    macOS cannot inspect a PE version resource without a dependency this
    repository does not carry, so the check is allowed to skip — but **loudly**
    (stderr), the way the macOS suite's tool-dependent tests do, because a
    silent empty problem list on the build machine is indistinguishable from a
    passing check.

    | fixture                        | SILENT-SKIP | STRICT (pure-python PE) | **expected**            |
    | a file that is not a PE        | [] + no msg✗| ["…no version resource"]| **problems or stderr**  |
    | a path that does not exist     | raises ✗    | []                      | **never raises**        |
    | check_all's body               | absent ✗    | present                 | **calls the check**     |

    Both implementations named in the task are accepted; what is refused is the
    third one — a check that returns "fine" without looking.
    """

    def _fn(self):
        vwa = _mod(VWA)
        fn = getattr(vwa, "check_version_resource", None)
        self.assertTrue(callable(fn), "verify_win_artifact.check_version_resource(exe_path) is missing")
        return fn

    def test_a_file_without_a_version_resource_is_never_a_silent_pass(self):
        fn = self._fn()
        tmp = tempfile.mkdtemp(prefix="cpw-f5g-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        exe = os.path.join(tmp, "ClaudePet.exe")
        with open(exe, "wb") as f:
            f.write(b"MZ" + bytes(512))
        buf = io.StringIO()
        with redirect_stderr(buf):
            problems = fn(exe)
        self.assertIsInstance(problems, list)
        self.assertTrue(problems or buf.getvalue().strip(),
                        "the version-resource check returned no problems and said nothing — "
                        "on a host that cannot read a PE it must skip loudly")

    def test_a_missing_file_never_raises(self):
        fn = self._fn()
        buf = io.StringIO()
        with redirect_stderr(buf):
            problems = fn(os.path.join(tempfile.gettempdir(), "cpw-does-not-exist", "ClaudePet.exe"))
        self.assertIsInstance(problems, list)

    def test_the_gate_actually_calls_it(self):
        src = _read(os.path.join(WINDIR, "verify_win_artifact.py"))
        tree = ast.parse(src)
        for fname in ("check_all", "check_zip"):
            fn = _func_def(tree, fname)
            if fn is None:
                continue
            if "check_version_resource" in {name for _ln, name, _n in _calls(fn)}:
                return
        self.fail("neither check_all nor check_zip calls check_version_resource")


if __name__ == "__main__":
    unittest.main()
