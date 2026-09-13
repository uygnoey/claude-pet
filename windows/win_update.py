"""Windows in-app updater / uninstaller — the pure half (importable on macOS).

This module holds every decision the Windows port makes about updating and
uninstalling that does not need a Windows API: which release asset fits this
machine and this install kind, whether a download is the file the release
JSON described, whether an extracted tree is a complete ClaudePet, the text of
the PowerShell helper that swaps a portable install, the argv for a silent
Inno upgrade, and the ordered plan an uninstall executes. The Qt / winreg /
ctypes wiring that *acts* on these answers lives in ``claude_pet_win.py``.

Everything here is testable on macOS: no ``winreg``, no ``msvcrt``, no
``ctypes.windll`` at import time, and nothing touches the network except
through an injected ``fetch_json``.

The core is reached as a module attribute (``cp._zip_members_are_safe``,
``cp._ver_tuple``) rather than bound with ``from claude_pet import …``, so the
delegation stays observable and the two ports cannot drift on what "newer"
or "safe archive" means. ``verify_release_artifact.py`` takes the same stance.

Privacy (CLAUDE.md § Privacy): ``log_update()`` writes counts and status
tokens only. Callers must never pass a path, a project name or a session id
as a field — the update log lives on the user's disk but it is also the
first thing a bug report will quote.
"""
import datetime
import hashlib
import json
import ntpath
import os
import re
import sys
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import claude_pet as cp  # noqa: E402  — the core; attribute access on purpose (see module docstring)

# ── names shared with build_win.py / installer.iss / verify_win_artifact.py ──
CACHE_DIR_NAME = "me.yeongyu.claudepet"            # %LOCALAPPDATA%\me.yeongyu.claudepet (mirrors UPDATE_LOCK_DIR)
UPDATE_LOG_NAME = "update.log"                     # counts/status only
INNO_LOG_NAME = "setup.log"                        # Inno's own /LOG — it names files, so it is a separate file
LOCK_NAME = "update-ClaudePet.lock"                # share-none handle held for the whole transaction
SETUP_ASSET = "claude-pet-win-setup.exe"
ZIP_ASSET = "claude-pet-win.zip"
APP_DIR_NAME = "ClaudePet"                         # the one root inside claude-pet-win.zip
EXE_NAME = "ClaudePet.exe"
UNINS_NAME = "unins000.exe"
RELEASE_MARKER = os.path.join("_internal", "claudepet-release.json")
INNO_UNINSTALL_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}_is1"
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "ClaudePet"
MUTEX_NAME = r"Local\me.yeongyu.claudepet"
STAGE_PREFIX = ".claudepet-stage-"
NEW_PREFIX = ".claudepet-new-"
OLD_PREFIX = ".claudepet-old-"

# Everything a shipped portable tree must contain, relative to ClaudePet\.
# build_win.py's REQUIRED is this tuple, so the build gate and the updater's
# layout check cannot disagree about what "complete" means.
PORTABLE_REQUIRED = (
    EXE_NAME,
    os.path.join("_internal", "frames"),
    os.path.join("_internal", "fonts", "Pretendard-SemiBold.ttf"),
    os.path.join("_internal", "fonts", "LICENSE-Pretendard.txt"),
    os.path.join("_internal", ".claude_pet", "pets"),
    os.path.join("_internal", "claudepet.ico"),
    RELEASE_MARKER,
)

# machine × install kind → the exact asset names allowed, in preference order.
# Only AMD64 is published today; ARM64 is a *known* machine with nothing to
# offer, which is a different answer from "never heard of it".
KNOWN_MACHINES = ("AMD64", "ARM64")
INSTALL_KINDS = ("inno", "portable")
UPDATE_ASSET_NAMES_WIN = {
    ("AMD64", "inno"): (SETUP_ASSET,),
    ("AMD64", "portable"): (ZIP_ASSET,),
    ("ARM64", "inno"): (),
    ("ARM64", "portable"): (),
}
ASSET_HOST = "github.com"

INNO_SILENT_FLAGS = ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                     "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS")
INNO_RELAUNCH_PARAM = "/RELAUNCH=1"                # installer.iss [Run] … Check: RelaunchRequested

LATEST_RELEASE_URL = f"https://api.github.com/repos/{cp.GITHUB_REPO}/releases/latest"


# ═══════════════════════════════ paths ═══════════════════════════════

def local_appdata(home=None, env=None):
    """%LOCALAPPDATA%, falling back to <home>\\AppData\\Local. Pure."""
    env = os.environ if env is None else env
    v = env.get("LOCALAPPDATA")
    if v:
        return v
    home = home if home is not None else os.path.expanduser("~")
    return os.path.join(home, "AppData", "Local")


def cache_dir(home=None, env=None):
    """Where downloads, the lock, the helper scripts and update.log live."""
    return os.path.join(local_appdata(home, env), CACHE_DIR_NAME)


def update_log_path(home=None, env=None):
    return os.path.join(cache_dir(home, env), UPDATE_LOG_NAME)


def lock_path(home=None, env=None):
    return os.path.join(cache_dir(home, env), LOCK_NAME)


def swap_names(parent, old_tag, token):
    """(new_dir, old_dir) beside the installed folder for one transaction.

    The staged tree carries a per-transaction token so two attempts never
    share a name; the retired tree carries the version it holds, which is
    what a user restoring by hand needs to see.
    """
    return (os.path.join(parent, NEW_PREFIX + str(token)),
            os.path.join(parent, OLD_PREFIX + "v" + str(old_tag).lstrip("vV")))


# ═══════════════════════════════ logging ═══════════════════════════════

_LOG_MAX = 512 * 1024


def log_update(step, path=None, **fields):
    """Append one line to update.log: ``<utc> <step> k=v …``.

    Counts, sizes, tags, status tokens and booleans only. Never a path, a
    project name, a session id or an exception message that could carry one
    — pass ``type(e).__name__`` for errors.
    """
    p = path or update_log_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        try:
            if os.path.getsize(p) > _LOG_MAX:
                open(p, "w", encoding="utf-8").close()
        except OSError:
            pass
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tail = " ".join(f"{k}={v}" for k, v in fields.items())
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{ts} {step}" + (" " + tail if tail else "") + "\n")
    except Exception:
        pass


# ═══════════════════════════════ install kind ═══════════════════════════════

def _norm_win(p):
    """Windows path equality: ntpath.normcase, then one trailing separator off.

    The compared values are Windows registry paths whichever host runs this,
    so host semantics (posixpath.normcase is the identity) would make the
    rule read differently here than on the target.
    """
    s = ntpath.normcase(str(p))
    if s.endswith("\\"):
        s = s[:-1]
    return s


def install_kind(exe_path, registry_reader):
    """'inno' iff unins000.exe sits beside the exe AND the Inno InstallLocation
    registry value names the exe's directory; anything else is 'portable'.

    ``registry_reader(value_name)`` returns the value or raises (winreg raises
    OSError when the key is absent — that is the normal portable case).
    """
    exe_dir = os.path.dirname(os.path.abspath(str(exe_path)))
    unins = os.path.join(exe_dir, UNINS_NAME)
    if not os.path.isfile(unins) or os.path.islink(unins):
        return "portable"
    try:
        loc = registry_reader("InstallLocation")
    except Exception:
        return "portable"
    if not isinstance(loc, str) or not loc.strip():
        return "portable"
    return "inno" if _norm_win(loc) == _norm_win(exe_dir) else "portable"


# ═══════════════════════════════ asset selection ═══════════════════════════════

def _asset_url_ok(url):
    if not isinstance(url, str) or not url:
        return False
    try:
        parts = urllib.parse.urlparse(url)
    except Exception:
        return False
    return parts.scheme == "https" and parts.netloc.lower() == ASSET_HOST


def select_update_asset_win(assets, machine, kind):
    """Pick the one asset this machine × install kind may install.

    Success → ``{"name", "url", "size", "digest"}`` (name lower-cased).
    Refusal → ``(None, status)``; ``"no-asset"`` is reserved for a known
    machine with nothing published (ARM64 today) so the UI can say so
    instead of retrying forever.
    """
    if machine not in KNOWN_MACHINES:
        return (None, "unknown-machine")
    if kind not in INSTALL_KINDS:
        return (None, "unknown-kind")
    allowed = UPDATE_ASSET_NAMES_WIN.get((machine, kind), ())
    if not allowed:
        return (None, "no-asset")
    by_name = {}
    try:
        items = list(assets or ())
    except TypeError:
        items = []
    for a in items:
        if not isinstance(a, dict):
            continue
        name = a.get("name")
        if not isinstance(name, str):
            continue
        name = name.strip().lower()
        if name not in allowed:
            continue
        if name in by_name:
            # Two assets normalising to one allowed name: picking one is a guess.
            return (None, "ambiguous-asset")
        by_name[name] = a
    for name in allowed:
        a = by_name.get(name)
        if a is None:
            continue
        url = a.get("browser_download_url")
        if not _asset_url_ok(url):
            return (None, "bad-url")
        return {"name": name, "url": url, "size": a.get("size"), "digest": a.get("digest")}
    return (None, "missing-asset")


# ═══════════════════════════════ the check ═══════════════════════════════

def fetch_json_default(url, timeout=10):
    """The one network call the check makes (injected as ``fetch_json``)."""
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "claude-pet"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def check_github_update_win(fetch_json, machine, kind, app_version):
    """→ ("update", tag, choice) | ("current", tag) | ("error", reason).

    ``tag`` is the release tag without its leading "v". Newer means
    ``cp._ver_tuple(tag) > cp._ver_tuple(app_version)`` — the argument, never
    ``cp.APP_VERSION`` — and the version is compared *before* any asset is
    looked at, so an equal tag on a machine with no asset is "current".
    ``choice`` carries ``{asset, kind, url, tag, size, digest, machine}``
    copied from the release JSON for the installer to verify against.
    """
    try:
        data = fetch_json(LATEST_RELEASE_URL)
    except Exception as e:
        return ("error", "fetch-failed:" + type(e).__name__)
    if not isinstance(data, dict):
        return ("error", "bad-payload")
    tag = str(data.get("tag_name") or "").strip().lstrip("vV")
    if not tag:
        return ("error", "no-tag")
    if cp._ver_tuple(tag) <= cp._ver_tuple(app_version):
        return ("current", tag)
    sel = select_update_asset_win(data.get("assets") or [], machine, kind)
    if isinstance(sel, tuple):
        return ("error", sel[1])
    choice = {"asset": sel["name"], "kind": kind, "url": sel["url"], "tag": tag,
              "size": sel["size"], "digest": sel["digest"], "machine": machine}
    return ("update", tag, choice)


# Reasons that describe the *network or the reply*, not the release. The next
# 30-second refresh may well succeed, so — like the core's ``failed`` — they do
# not stamp the hourly cooldown. Every other reason is a property of the
# published release or of this machine (no asset for ARM64, an unknown kind, a
# bad URL, two assets under one name): nothing the next refresh would see
# differently, so it waits the hour exactly as a successful check does. Without
# that split an ARM64 pet asked api.github.com every 30 s for the rest of its
# life (120/h against the unauthenticated 60/h limit).
TRANSIENT_CHECK_REASONS = ("bad-payload",)
TRANSIENT_CHECK_PREFIXES = ("fetch-failed:",)


def transient_check_reason(reason):
    """True for a check failure the next refresh may not repeat (network, a
    reply that is not JSON) — the only reasons that skip the cooldown."""
    r = str(reason or "")
    return r in TRANSIENT_CHECK_REASONS or r.startswith(TRANSIENT_CHECK_PREFIXES)


def stamps_cooldown(result):
    """True when a ``check_github_update_win`` result should stamp
    ``cp._upd_cache["t"]`` so the next check waits ``cp.UPDATE_CHECK_SEC``.

    ``("update", …)`` and ``("current", …)`` always stamp. ``("error", reason)``
    stamps unless the reason is transient (``transient_check_reason``): a
    deterministic refusal such as ``no-asset`` is re-asked hourly, never every
    refresh. Anything else — a malformed result — does not stamp.
    """
    try:
        status = result[0]
    except (TypeError, IndexError, KeyError):
        return False
    if status in ("update", "current"):
        return True
    if status == "error":
        reason = result[1] if len(result) > 1 else None
        return not transient_check_reason(reason)
    return False


# ═══════════════════════════════ download verification ═══════════════════════════════

_DIGEST_RE = re.compile(r"sha256:([0-9a-fA-F]{64})")


def parse_digest(digest):
    """'sha256:<64 hex>' → lower-case hex, else None. Nothing else is a digest."""
    if not isinstance(digest, str):
        return None
    m = _DIGEST_RE.fullmatch(digest.strip())
    return m.group(1).lower() if m else None


def verify_download(path, size, digest):
    """Size first (a stat, no read), then the sha256 digest. Both must match.

    A missing or malformed digest refuses even when the size matches: the
    release JSON carries one for every asset, so its absence is a signal.
    """
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        return False
    try:
        st = os.stat(path)
    except OSError:
        return False
    if st.st_size != size:
        return False
    want = parse_digest(digest)
    if want is None:
        return False
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        return False
    return h.hexdigest().lower() == want


# ═══════════════════════════════ archive + layout ═══════════════════════════════

def scan_update_zip(zip_path):
    """The core's archive scan, and nothing else: it already normalises
    backslashes before looking for '..' and reads symlink targets."""
    try:
        return bool(cp._zip_members_are_safe(zip_path))
    except Exception:
        return False


def read_release_marker(app_dir):
    """_internal\\claudepet-release.json as a dict, else None."""
    p = os.path.join(app_dir, RELEASE_MARKER)
    try:
        if os.path.islink(p) or not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def validate_portable_layout(extract_dir, expected_tag):
    """(ok, reason). Accepts only: exactly one top-level entry, ``ClaudePet/``;
    every PORTABLE_REQUIRED path present; ``_internal/claudepet-release.json``
    whose "version" equals the tag (leading "v" removed) as a string, exactly.

    Reasons carry names relative to the archive and counts — never the
    extraction path, which is under the user's profile.
    """
    tag = str(expected_tag or "").strip().lstrip("vV")
    if not tag:
        return (False, "no expected version to verify against")
    try:
        entries = sorted(os.listdir(extract_dir))
    except OSError as e:
        return (False, f"extraction directory unreadable ({type(e).__name__})")
    if entries != [APP_DIR_NAME]:
        return (False, f"expected exactly one top-level entry '{APP_DIR_NAME}', found {len(entries)}")
    app = os.path.join(extract_dir, APP_DIR_NAME)
    if os.path.islink(app) or not os.path.isdir(app):
        return (False, f"'{APP_DIR_NAME}' is not a directory")
    exe = os.path.join(app, EXE_NAME)
    if os.path.islink(exe) or not os.path.isfile(exe):
        return (False, f"'{EXE_NAME}' missing")
    internal = os.path.join(app, "_internal")
    if os.path.islink(internal) or not os.path.isdir(internal):
        return (False, "'_internal' is not a directory")
    for rel in PORTABLE_REQUIRED:
        p = os.path.join(app, rel)
        if os.path.islink(p) or not os.path.exists(p):
            return (False, f"required entry missing: {rel}")
    marker = read_release_marker(app)
    if marker is None:
        return (False, "release marker missing or unparseable")
    version = marker.get("version")
    if not isinstance(version, str) or not version:
        return (False, "release marker has no version")
    if version != tag:
        return (False, "release marker version does not match the release tag")
    return (True, "ok")


def leftover_dirs(parent):
    """Our own staging/backup trees beside the installed folder that a
    killed or failed transaction left behind — never by name alone.

    ``.claudepet-new-*`` / ``.claudepet-old-*`` must carry our exe and release
    marker. ``.claudepet-stage-*`` is an extraction scratch whose contents were
    never complete by design (the kill may have come mid-extract), so it is
    identified by its prefix AND its shape: it holds nothing but the archive's
    single root ``ClaudePet`` (or nothing at all). A folder with the prefix and
    anything else inside is not ours and is left alone.

    A *partial* old tree — one whose removal was interrupted and that lacks the
    exe or the marker — is therefore never removed here; ``swap_refusal``
    refuses the next update on it (``old-dir-exists``) until a person deletes it.
    """
    out = []
    try:
        names = os.listdir(parent)
    except OSError:
        return out
    for name in names:
        if not name.startswith((STAGE_PREFIX, NEW_PREFIX, OLD_PREFIX)):
            continue
        p = os.path.join(parent, name)
        if os.path.islink(p) or not os.path.isdir(p):
            continue
        if name.startswith(STAGE_PREFIX):
            try:
                inside = set(os.listdir(p))
            except OSError:
                continue
            if inside <= {APP_DIR_NAME}:        # ours by prefix and shape: only the archive's root, possibly partial
                out.append(p)
            continue
        if os.path.isfile(os.path.join(p, EXE_NAME)) and read_release_marker(p) is not None:
            out.append(p)
    return out


def swap_refusal(app_dir, new_dir, old_dir):
    """Why a portable swap must not start, as a status token, or ``None``.

    Asked before anything is downloaded: each answer stays true until a person
    acts, so a download would be wasted on it.

    ``old-dir-exists``  something already sits at the retired-tree name. The
                        helper renames with ``Rename-Item``, which refuses an
                        existing destination, so the swap would fail at its
                        first step — and a leftover *partial* old tree (a
                        removal interrupted by AV holding a DLL) is exactly
                        what ``leftover_dirs`` will not remove, so it would
                        refuse every update until deleted by hand.
    ``new-dir-exists``  the staged name is taken.
    ``app-dir-missing`` the installed folder is not a directory (or is a link).
    ``not-siblings``    the three names do not share one parent —
                        ``Rename-Item`` cannot move across directories.
    """
    if os.path.lexists(old_dir):
        return "old-dir-exists"
    if os.path.lexists(new_dir):
        return "new-dir-exists"
    if os.path.islink(app_dir) or not os.path.isdir(app_dir):
        return "app-dir-missing"
    parents = {os.path.normcase(os.path.dirname(os.path.abspath(p))) for p in (app_dir, new_dir, old_dir)}
    if len(parents) != 1:
        return "not-siblings"
    return None


def uninstall_refusal(state):
    """Why "완전 삭제…" must not start, as a status token, or ``None``.

    ``installing``  an Inno ``setup.exe`` launched by the in-app update is
                    running and waiting to close this app. The share-none lock
                    handle does not cover that run — the installer does not
                    inherit it and our copy is closed once it is launched — so
                    this flag is what keeps ``unins000.exe`` from running beside
                    a live setup. The portable kind needs no flag: its helper
                    inherits the handle and holds it until it exits.
    """
    try:
        return "installing" if state.get("installing") else None
    except AttributeError:
        return None


# ═══════════════════════════════ helper scripts ═══════════════════════════════

def ps_quote(s):
    """Single-quote for PowerShell — the only quoting that expands nothing;
    an embedded quote is doubled."""
    return "'" + str(s).replace("'", "''") + "'"


def build_swap_script(app_dir, new_dir, old_dir, exe, pid, log_path=None):
    r"""PowerShell text that swaps a portable install after the pet exits.

    Order is the contract: wait for ``pid`` → refuse if anything sits at
    ``old_dir`` → rename the installed folder to ``old_dir`` → rename the staged
    ``new_dir`` into place → start ``exe`` → confirm a process with that path is
    alive → remove the old tree. Any failure after the first rename rolls back
    and relaunches the OLD exe; a failure before it removes the staging tree and
    relaunches the old exe. Every path is single-quoted wherever it appears.

    Every rename is ``Rename-Item``, never ``Move-Item``. ``Move-Item`` with an
    existing *directory* as ``-Destination`` moves the source **inside** it, so
    a leftover ``old_dir`` would land the install at ``old_dir\ClaudePet`` and
    the rollback at ``ClaudePet\ClaudePet`` — no pet, and no error at the
    step that caused it. ``Rename-Item`` fails on an existing destination (the
    no-overwrite primitive this repository prizes) and only renames within one
    directory, which is why ``swap_refusal`` requires the three names to be
    siblings before anything is downloaded.

    Exit codes, all logged as tokens: 0 swapped; 2 the pet never exited;
    3 the installed folder could not be renamed; 4 the staged folder could not
    be renamed into place (rolled back); 5 the new exe did not stay running
    (rolled back); 6 ``old_dir`` already existed when the helper ran.
    """
    pid = int(pid)
    q = ps_quote
    app_q, new_q, old_q, exe_q = q(app_dir), q(new_dir), q(old_dir), q(exe)
    app_name_q = q(ntpath.basename(ntpath.normpath(str(app_dir))))
    new_name_q = q(ntpath.basename(ntpath.normpath(str(new_dir))))
    old_name_q = q(ntpath.basename(ntpath.normpath(str(old_dir))))
    if log_path:
        note = ("function Note($m) {\n"
                f"  try {{ Add-Content -LiteralPath {q(log_path)} -Value "
                "((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') + ' swap ' + $m) } catch { }\n"
                "}")
    else:
        note = "function Note($m) { }"
    drop_staging = (f"try {{ Remove-Item -LiteralPath {new_q} -Recurse -Force -ErrorAction Stop }} "
                    "catch { Note 'warn=staging-left' }")
    start_old = f"try {{ Start-Process -FilePath {exe_q} -ErrorAction Stop }} catch {{ Note 'warn=old-exe-not-started' }}"
    lines = [
        "# ClaudePet portable update helper — generated by windows/win_update.py.",
        "# Runs after the pet has exited; logs status tokens only. Every rename refuses an existing destination — nothing here overwrites.",
        "$ErrorActionPreference = 'Stop'",
        "$ProgressPreference = 'SilentlyContinue'",
        note,
        f"Note ('begin pid={pid}')",
        f"try {{ Wait-Process -Id {pid} -Timeout 120 -ErrorAction Stop }} catch {{ }}",
        f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{",
        "  Note 'refused=app-still-running'",
        "  " + drop_staging,
        "  exit 2",
        "}",
        f"if (Test-Path -LiteralPath {old_q}) {{",
        "  Note 'refused=old-dir-exists'",
        "  " + drop_staging,
        "  " + start_old,
        "  exit 6",
        "}",
        "$moved = $false",
        "for ($i = 0; $i -lt 40; $i++) {",
        f"  try {{ Rename-Item -LiteralPath {app_q} -NewName {old_name_q} -ErrorAction Stop; $moved = $true; break }}",
        "  catch { Start-Sleep -Milliseconds 500 }",
        "}",
        "if (-not $moved) {",
        "  Note 'failed=app-to-old'",
        "  " + drop_staging,
        "  " + start_old,
        "  exit 3",
        "}",
        f"try {{ Rename-Item -LiteralPath {new_q} -NewName {app_name_q} -ErrorAction Stop }}",
        "catch {",
        "  Note 'failed=new-to-app rollback=start'",
        f"  try {{ Rename-Item -LiteralPath {old_q} -NewName {app_name_q} -ErrorAction Stop; Note 'rollback=ok' }}",
        "  catch { Note 'rollback=failed old-tree=left' }",
        "  " + start_old,
        "  exit 4",
        "}",
        "Note 'swapped=ok'",
        f"Start-Process -FilePath {exe_q} -WorkingDirectory {app_q}",
        "$alive = $false",
        "for ($i = 0; $i -lt 40; $i++) {",
        "  Start-Sleep -Milliseconds 500",
        f"  try {{ if (Get-Process -Name 'ClaudePet' -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq {exe_q} }}) {{ $alive = $true; break }} }} catch {{ }}",
        "}",
        "if ($alive) {",
        "  Start-Sleep -Seconds 3",
        f"  try {{ if (-not (Get-Process -Name 'ClaudePet' -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq {exe_q} }})) {{ $alive = $false }} }} catch {{ }}",
        "}",
        "if (-not $alive) {",
        "  Note 'failed=new-app-not-running rollback=start'",
        f"  try {{ Rename-Item -LiteralPath {app_q} -NewName {new_name_q} -ErrorAction Stop; "
        f"Rename-Item -LiteralPath {old_q} -NewName {app_name_q} -ErrorAction Stop; Note 'rollback=ok' }}",
        "  catch { Note 'rollback=failed' }",
        "  " + start_old,
        "  exit 5",
        "}",
        "Note 'new-app=running'",
        f"try {{ Remove-Item -LiteralPath {old_q} -Recurse -Force -ErrorAction Stop; Note 'old-tree=removed' }}",
        "catch { Note 'warn=old-tree-left' }",
        "try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }",
        "exit 0",
    ]
    return "\n".join(lines) + "\n"


def build_uninstall_script(app_dir, pid):
    """PowerShell text that removes a portable install's folder after the pet
    exits — only while the folder still carries our exe and release marker."""
    q = ps_quote
    pid = int(pid)
    exe_q = q(os.path.join(app_dir, EXE_NAME))
    marker_q = q(os.path.join(app_dir, RELEASE_MARKER))
    lines = [
        "# ClaudePet portable uninstall helper — generated by windows/win_update.py.",
        "$ErrorActionPreference = 'Stop'",
        f"try {{ Wait-Process -Id {pid} -Timeout 120 -ErrorAction Stop }} catch {{ }}",
        f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 2 }}",
        f"if ((Test-Path -LiteralPath {exe_q}) -and (Test-Path -LiteralPath {marker_q})) {{",
        "  for ($i = 0; $i -lt 40; $i++) {",
        f"    try {{ Remove-Item -LiteralPath {q(app_dir)} -Recurse -Force -ErrorAction Stop; break }}",
        "    catch { Start-Sleep -Milliseconds 500 }",
        "  }",
        "}",
        "try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }",
        "exit 0",
    ]
    return "\n".join(lines) + "\n"


def inno_silent_args(setup_exe, log_path):
    """argv for the silent in-app upgrade — a list for subprocess, never a
    shell string: CreateProcess quoting is subprocess's job, and a literal
    quote inside ``/LOG=`` would become part of the file name Inno opens."""
    return [str(setup_exe), *INNO_SILENT_FLAGS, INNO_RELAUNCH_PARAM, "/LOG=" + str(log_path)]


# ═══════════════════════════════ uninstall ═══════════════════════════════

def _home_user_files(home):
    """The per-user files macOS deletes, mapped onto <home>: every
    cp.UNINSTALL_PATHS entry that lives directly in ~ (the config, its lock,
    the debug log). Library/… entries and the macOS cache dir are skipped —
    the Windows cache dir is added separately."""
    out = []
    for p in cp.UNINSTALL_PATHS:
        if p == cp.UPDATE_LOCK_DIR:
            continue
        if p.startswith("~/"):
            rel = p[2:]
        elif p == cp.CONFIG_PATH or p == cp.CONFIG_PATH + ".lock":
            rel = os.path.basename(p)
        else:
            continue
        if "/" in rel or "\\" in rel:
            continue
        out.append(os.path.join(home, rel))
    return out


def uninstall_plan(kind, exe_dir, home):
    """Ordered [(op, arg)] — a plan, not a scan: nothing here need exist.

    ``("delete", path)`` for the per-user files and the cache directory, then
    LAST the kind step: ``("run", [exe_dir\\unins000.exe, "/SILENT"])`` for
    inno, ``("helper", exe_dir)`` for portable. Never ``home\\.claude_pet``
    (the user's pets — parity with macOS) and never ``home\\.claude``
    (Claude Code's own directory).
    """
    if kind not in INSTALL_KINDS:
        raise ValueError(f"unknown install kind: {kind!r}")
    plan = [("delete", p) for p in _home_user_files(home)]
    plan.append(("delete", cache_dir(home)))
    if kind == "inno":
        plan.append(("run", [os.path.join(exe_dir, UNINS_NAME), "/SILENT"]))
    else:
        plan.append(("helper", exe_dir))
    return plan


def run_value_is_ours(value, exe):
    """True when an HKCU Run value (possibly quoted) names this exe."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    if v.startswith('"'):
        end = v.find('"', 1)
        v = v[1:end] if end > 0 else v[1:]
    return bool(v) and _norm_win(v) == _norm_win(exe)
