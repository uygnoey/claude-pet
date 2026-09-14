"""Windows "Start at sign-in" — the pure half (importable on macOS).

The right-click item ``t("menu_autostart")`` is backed on Windows by the same
HKCU ``Run`` value the installer's ``startup`` task writes (installer.iss
``[Registry]``): same subkey, same value name ``ClaudePet``, same REG_SZ text
``"<exe>"`` — the path in one pair of double quotes. The installer checkbox,
this toggle, the installer's ``uninsdeletevalue`` and the app's "Uninstall
completely" therefore all act on one value, and what this module writes is
what ``claude_pet_win.delete_run_value_if_ours`` recognises: both sides
compare through ``win_update.run_value_is_ours``.

Windows keeps a second location the Run value alone cannot show. Task Manager
› Startup apps does not delete the value when the user disables an app; it
writes a REG_BINARY of the same name under
``HKCU\\…\\Explorer\\StartupApproved\\Run``. ``startup_approved_enabled`` is the
one place that byte encoding lives — the **low bit of the first byte**: even is
enabled, odd is disabled. The hardware run that settled this (one Windows 11
machine, 2026-09-14) wrote ``0x00`` on re-enable and ``0x01`` on disable, and
found ``0x02`` on third-party entries the UI had never touched; the shipped
guess ("``0x02`` enabled, ``0x03`` disabled") read the enabled state as
disabled, so a machine Windows was launching us on showed the item unchecked.
If a later hardware run moves a byte, that one function and its test table
change together and nothing else does.

There is no persisted preference, mirroring the macOS half (CLAUDE.md
§ "Start at sign-in"): the registry is the only source of truth, re-read every
time the menu opens, so a change the user makes in Task Manager shows as-is
and is never re-applied behind their back. Nothing here reads or writes the
settings file.

The seam. The pure functions reach HKCU only through two injected callables,
both positional:

* ``reader(subkey, name)`` → the value (``str`` for the REG_SZ Run value,
  ``bytes`` for the StartupApproved blob), or ``None`` when the key or the
  value does not exist; anything else raises. The distinction is the design:
  "absent" is a state ("off"), "raised" is not ("unavailable").
* ``writer(subkey, name, data)`` → sets ``name`` to the ``str`` ``data`` as
  REG_SZ, deletes it when ``data is None``; returns nothing, raises on failure.

``registry_reader`` / ``registry_writer`` are the thin ``winreg`` adapter with
exactly those contracts (``winreg`` is imported at call time, so this module
imports anywhere), and ``real_registry()`` hands them out on win32 only,
deciding at call time.
"""
import sys

try:                                    # imported as windows.win_autostart — the test suite, from the repo root
    from . import win_update as _wu
except ImportError:                     # imported bare with windows/ first on sys.path — the port and the bundle
    import win_update as _wu

# The two names the installer, the updater's uninstall and this toggle share — one source, so they cannot drift.
RUN_SUBKEY = _wu.RUN_SUBKEY                              # Software\Microsoft\Windows\CurrentVersion\Run
RUN_VALUE_NAME = _wu.RUN_VALUE_NAME                      # ClaudePet
# Explorer's mirror of the Run value: Task Manager › Startup apps writes its enabled/disabled verdict here.
STARTUP_APPROVED_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

_STARTUP_APPROVED_DISABLED_BIT = 0x01   # low bit of the first byte: set = disabled, clear = enabled


def run_value_for(exe):
    """The REG_SZ text the installer writes for this exe: the path inside one pair of double quotes.

    Byte-identical to installer.iss ``ValueData: \"\"\"{app}\\{#MyAppExeName}\"\"\"``
    (Inno's ``\"\"`` is a literal quote). No normalisation — the value is the
    path as the process reports it, and ``win_update.run_value_is_ours`` does
    the case-insensitive comparison on the way back.
    """
    return '"' + exe + '"'


def startup_approved_enabled(blob):
    """True iff a StartupApproved blob says "enabled" — the only place the byte encoding lives.

    **The rule: the low bit of the first byte. Even means enabled, odd means
    disabled.** So ``0x00`` and ``0x02`` are enabled, ``0x01`` and ``0x03`` are
    disabled.

    Which half of that is measured and which is extrapolated, kept apart on
    purpose (AGENTS.md §5):

    * **Observed**, on one machine — Windows 11, through Settings › Startup
      apps and Task Manager › Startup apps, 2026-09-14. Disabling our entry
      wrote ``01 00 00 00`` followed by an 8-byte FILETIME (first byte
      ``0x01``); re-enabling it wrote twelve zero bytes (first byte ``0x00``);
      third-party entries that UI had never touched carried ``0x02``. One
      machine, one Windows build: enough to *refute* the encoding this code
      shipped with ("``0x02`` enabled, ``0x03`` disabled"), which read the
      enabled state as disabled and showed the menu item unchecked while
      Windows was launching us.
    * **Extrapolated** — that the same low bit decides it for every other
      first byte (``0x04`` enabled, ``0x05`` disabled, …). That is a hypothesis
      from the shape of the three observed values, not an observation, and no
      second party has reproduced it. A later hardware run may refute it
      without disturbing the observed half.

    Anything that is not a non-empty ``bytes``/``bytearray`` — ``None``, an
    empty blob, a ``str``, a ``memoryview`` — reads as *not* enabled, and
    nothing raises. The fail-safe direction is unchanged: a blob this code
    cannot read is not evidence that Windows will launch us. Read as "off" the
    item shows unchecked and the next click deletes the entry (absent =
    enabled), which is the self-healing path; read as "on" it would show a
    checkmark Windows does not honour and no click would fix it.
    """
    return bool(isinstance(blob, (bytes, bytearray)) and len(blob) > 0
                and not blob[0] & _STARTUP_APPROVED_DISABLED_BIT)


def _state_of(run, approved, exe):
    """"on" | "off" for two values already read: ours in Run, and not disabled by Explorer."""
    if not _wu.run_value_is_ours(run, exe):
        return "off"                    # absent, someone else's path, or not a string at all
    if approved is None:
        return "on"                     # Task Manager has never ruled on us: the Run value stands
    return "on" if startup_approved_enabled(approved) else "off"


def autostart_read_state(reader, exe, is_frozen):
    """The menu state now: "on" | "off" | "unavailable". Never writes.

    "on" iff all of: a frozen build; a Run value present whose unquoted path
    is this exe under Windows path semantics (``ntpath.normcase``, via
    ``win_update.run_value_is_ours``); and the StartupApproved entry absent or
    enabled. Value absent, a foreign path, or a disabled entry → "off".

    Not frozen → "unavailable" without a single registry read: from source
    ``sys.executable`` is ``pythonw.exe``, never ours to register (the shape
    of the macOS bundle guard). No reader or no exe → "unavailable", no
    call. A reader that raises → "unavailable": a registry we cannot read
    is not a state, and neither "off" (the next click would write) nor an
    exception (the menu would not open) is the right answer for it.
    """
    if not is_frozen or reader is None or not exe:
        return "unavailable"
    try:
        run = reader(RUN_SUBKEY, RUN_VALUE_NAME)
        if not _wu.run_value_is_ours(run, exe):
            return "off"                # nothing of ours to look up under StartupApproved
        approved = reader(STARTUP_APPROVED_SUBKEY, RUN_VALUE_NAME)
    except Exception:
        return "unavailable"
    return _state_of(run, approved, exe)


def autostart_toggle(reader, writer, exe, is_frozen):
    """One click. Returns ``(new_state, "autostart_fail" | None)``.

    From "on": delete the StartupApproved entry if present, then the Run
    value — a stale entry left behind would silently block a later enable,
    and Explorer first keeps the pre-click state truthful under a partial
    failure (Run present + entry absent still reads "on"). From "off": write
    ``run_value_for(exe)`` to the Run value — overwriting a foreign path,
    which is how a moved portable folder is repaired — then delete a
    *disabled* StartupApproved entry so Windows honours the value again; the
    entry is deleted, never rewritten as enabled (absent means enabled, and
    the byte layout is not ours to author).

    The new state is **read back** from the registry afterwards, as the macOS
    half reads it back from the service. A writer that raises leaves the
    state as it was before the click and reports ``"autostart_fail"``. Not
    frozen, no reader or writer, no exe, or a reader that raises →
    ``("unavailable", None)`` with nothing written. Nothing is persisted
    anywhere else.
    """
    if not is_frozen or reader is None or writer is None or not exe:
        return "unavailable", None
    try:
        run = reader(RUN_SUBKEY, RUN_VALUE_NAME)
        approved = reader(STARTUP_APPROVED_SUBKEY, RUN_VALUE_NAME)
    except Exception:
        return "unavailable", None
    state = _state_of(run, approved, exe)
    try:
        if state == "on":
            if approved is not None:
                writer(STARTUP_APPROVED_SUBKEY, RUN_VALUE_NAME, None)
            writer(RUN_SUBKEY, RUN_VALUE_NAME, None)
        else:
            writer(RUN_SUBKEY, RUN_VALUE_NAME, run_value_for(exe))
            if approved is not None and not startup_approved_enabled(approved):
                writer(STARTUP_APPROVED_SUBKEY, RUN_VALUE_NAME, None)
    except Exception:
        return state, "autostart_fail"
    return autostart_read_state(reader, exe, is_frozen), None


# ─────────────────────────── the thin winreg adapter (executes on Windows only) ───────────────────────────

def registry_reader(subkey, name):
    """``reader`` over HKCU: the value itself, or ``None`` when the key or the value does not exist.

    ``winreg`` reports both absences as ``FileNotFoundError``, and this is the
    one place that maps them to ``None`` — "never registered" is a state
    ("off"), not a failure. (The macOS half once shipped the opposite mapping
    and every fresh install showed a disabled item.) Any other ``OSError`` — a
    denied open, a corrupt hive — propagates, and the callers read it as
    "unavailable". The ``(value, type)`` pair ``QueryValueEx`` returns is
    unpacked here so callers see the value alone.
    """
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    return value


def registry_writer(subkey, name, data):
    """``writer`` over HKCU: a ``str`` sets ``name`` as REG_SZ, ``None`` deletes it. Raises on failure.

    Always the *named* value (``SetValueEx`` / ``DeleteValue``), never the
    key's default value. A set creates the subkey when it is missing
    (``CreateKeyEx`` opens an existing one). Deleting a value that is already
    gone is the requested end state rather than a failure, so that one
    ``FileNotFoundError`` is absorbed; everything else propagates.
    """
    import winreg
    if data is None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
        return
    if not isinstance(data, str):
        raise TypeError("registry_writer: data must be a str (REG_SZ) or None (delete)")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, data)


def real_registry():
    """``(registry_reader, registry_writer)`` on Windows, ``(None, None)`` anywhere else — decided at call time.

    The pure functions treat ``None`` as "unavailable" without a call, so on
    any other platform the item is simply disabled.
    """
    if sys.platform == "win32":
        return registry_reader, registry_writer
    return None, None
