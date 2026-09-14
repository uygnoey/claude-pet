"""The one owner of the core import on Windows — `import_core()` and nothing else.

`claude_pet.py` is written for macOS and two lines of it refuse to import on
Windows. Both detours below used to live inside `claude_pet_win._import_core`,
where only the GUI entry point could reach them; every other Windows entry
point (`win_update.py`, and through it `build_win.py` and
`verify_win_artifact.py`) reached the core with a bare `import claude_pet` and
therefore died at its first line on a real Windows machine:

    build_win.py → win_update.py → claude_pet.py:31  import fcntl
        ModuleNotFoundError: No module named 'fcntl'
    …with windows/compat on sys.path, one import later:
    claude_pet.py:161  ctypes.CDLL(None, use_errno=True)
        TypeError: LoadLibrary() argument 1 must be str, not None

(Observed on one Windows 11 machine, 2026-09-14, running the v0.25 pre-release
checks — AGENTS.md §5. macOS never sees either: `fcntl` is present and
`CDLL(None)` is the documented way to open the running process's symbols.)

So the two detours live here, in the one module every Windows entry point goes
through, and nowhere else:

1. **`import fcntl`** — POSIX only. `windows/compat/fcntl.py` (an `msvcrt`-based
   `flock`) goes to the front of `sys.path` so the core's own `import fcntl`
   binds to the shim. The shim raises `ImportError` if it is ever imported on a
   platform that has the real module, so this must stay `win32`-only.
2. **`ctypes.CDLL(None)`** — the core's `renameatx_np` probe. On Windows that
   raises `TypeError`, which the core's `except (OSError, AttributeError)` does
   not catch, so the module dies at import. `CDLL` is wrapped *for the duration
   of the import only* so a `None` argument raises `OSError` instead, and the
   core takes its own "this OS does not have it" fallback
   (`_RENAMEATX_NP = None`). The wrapper is removed in a `finally`: nothing
   outside this call ever sees a patched `ctypes`.

**On any other platform `import_core()` is `importlib.import_module`, exactly.**
`import_core()` adds no path and wraps no builtin — which is what lets the whole
Windows suite run on macOS and mean something. The scope belongs on the call, not
on the file: the *module body* below does insert the repository root into
`sys.path`, on every platform, because `claude_pet` cannot be found at all
otherwise. That one insertion is unconditional and happens at import time; the two
detours above are the only things the call itself can add, and only on `win32`.

Importable both ways, because it is imported from both sides of a package
boundary: as ``windows.win_core`` (the test suite, run with ``-t .`` from the
repository root) and bare as ``win_core`` (the port, and the PyInstaller bundle,
which flattens ``windows/`` onto ``sys.path``).
"""
import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
COMPAT_DIR = os.path.join(_HERE, "compat")

# The repository root has to be importable before `claude_pet` can be found at
# all. Done at import time, not inside import_core(), so that the call itself
# changes nothing on a host that needs no detour.
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def import_core():
    """Import `claude_pet` and return the module. Idempotent; safe to call from anywhere.

    Every Windows entry point calls this instead of importing the core itself —
    `claude_pet_win.py`, `win_update.py`, `build_win.py`,
    `verify_win_artifact.py`. A module that imports the core directly is a
    module that works here and dies on the target, which is the whole finding
    this file answers.
    """
    if sys.platform != "win32":
        return importlib.import_module("claude_pet")
    if COMPAT_DIR not in sys.path:
        sys.path.insert(0, COMPAT_DIR)
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
