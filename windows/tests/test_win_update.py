"""Gating tests for the Windows in-app updater's pure surface (Track C/D, 2026-09-13).

Run from the worktree root:

    python3 -m unittest discover -s windows/tests -t . -v

Verifier-owned (AGENTS.md §2 Condition A). The Developer provides
``windows/win_update.py`` — importable on macOS, win32-only imports guarded —
and must not touch the assertions or fixtures here.

The surface pinned here, and nothing else in the port, is what these tests
judge:

    install_kind(exe_path, registry_reader)              -> "inno" | "portable"
    select_update_asset_win(assets, machine, kind)       -> {name,url,size,digest} | (None, status)
    check_github_update_win(fetch_json, machine, kind, app_version)
                                                         -> ("update", tag, choice) | ("current", tag) | ("error", reason)
    verify_download(path, size, digest)                  -> bool
    scan_update_zip(zip_path)                            -> bool   (delegates to cp._zip_members_are_safe)
    validate_portable_layout(extract_dir, expected_tag)  -> (ok, reason)
    build_swap_script(app_dir, new_dir, old_dir, exe, pid) -> str  (PowerShell text)
    inno_silent_args(setup_exe, log_path)                -> list[str]
    uninstall_plan(kind, exe_dir, home)                  -> [(op, arg), ...]

Round 2 (after review round 1 — B1, B2, B3, N1), same file, same owner:

    stamps_cooldown(result) / transient_check_reason(reason) -> bool   (B1)
    swap_refusal(app_dir, new_dir, old_dir)              -> token | None  (B2)
    build_swap_script(...)   rollback text, Rename-Item only, Test-Path guard (B2)
    uninstall_refusal(state)                             -> "installing" | None  (B3)
    leftover_dirs(parent)                                -> [path, ...]  (N1)
    windows/claude_pet_win.py  text pins: the three helpers are actually wired

Round 3 (after review round 2 — B4), same file, same owner:

    every ``wu.log_update(`` call site in windows/claude_pet_win.py, lifted
    with ``ast`` and replayed through the real ``log_update``; the two
    ``_uninstall`` launch-failure handlers log/tell/return          (B4)
    the same call sites bound by keyword *name* against the signature —
    ``inspect.signature().bind`` first, the real call second, exactly one
    log line per site; ``CLAUDE_PET_WIN_PORT_SOURCE`` points the gate at a
    retained pre-fix copy for observing RED                       (B4, round-3 ask)

``scan_update_zip`` is the one name the task's bullet list did not spell out:
"unsafe members rejected via cp._zip_members_are_safe on the zip" cannot be
observed through ``validate_portable_layout(extract_dir, …)`` because the zip
is gone by then, so the scan step gets its own callable.

Seams these tests rely on. A Developer who wires them differently gets an
ERROR, not a silent pass — that is the point of pinning them:

* ``win_update.hashlib`` — the module does ``import hashlib`` and calls
  ``hashlib.sha256`` through that name, so the "size before hash" test can
  swap it for an object whose every attribute raises.
* ``claude_pet._zip_members_are_safe`` is reached as an attribute of the
  imported core module (``cp._zip_members_are_safe(path)``), never bound with
  ``from claude_pet import …``, so delegation is observable by patching the
  core. verify_release_artifact.py takes the same stance for the same reason.
* ``install_kind`` compares paths with Windows semantics (``ntpath.normcase``
  + strip one trailing backslash). The compared values are Windows registry
  paths whichever host runs the code; using host semantics would make the
  rule read differently on this test host than on the target.
* ``check_github_update_win`` reaches the network only through the injected
  ``fetch_json``; every check here runs with ``urllib.request.urlopen``
  patched to raise.
* ``uninstall_plan`` is a plan, not a scan: it names paths that do not exist
  and touches nothing. The executor filters by existence.

Every class docstring carries the AGENTS.md §3 truth table for its fixtures:
the rivals are the implementations someone would plausibly write, and each
fixture is chosen so that no rival collapses onto the expected value.
"""

import ast
import hashlib
import importlib
import inspect
import json
import ntpath
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import windows.win_core as win_core  # noqa: E402  — the ONE owner of the core import

# Same reason as test_win_autostart.py: a bare `import claude_pet` dies at collection on
# Windows (`ModuleNotFoundError: No module named 'fcntl'`), so the module under test was
# never reached at all on the only host that can answer for it. `windows/README.md`.
cp = win_core.import_core()  # noqa: E402  — the core the module under test must reach too

MODULE = "windows.win_update"


def _mod():
    """Import lazily so a missing module fails each gate on its own line."""
    return importlib.import_module(MODULE)


# ───────────────────────── fixtures shared across classes ─────────────────────────

SETUP_NAME = "claude-pet-win-setup.exe"
ZIP_NAME = "claude-pet-win.zip"
DECOY_NAME = "claude-pet-win.zip.sha256"     # a checksum sidecar: contains every substring a lazy match wants
MAC_NAMES = ("claudepet.zip", "claudepet-universal.zip", "ClaudePet.dmg", "ClaudePet-universal.dmg")
REPO_DL = f"https://github.com/{cp.GITHUB_REPO}/releases/download"

ZIP_SIZE = 72459838
SETUP_SIZE = 56012818
ZIP_DIGEST = "sha256:386679f9" + "ab" * 28          # 8 + 56 = 64 hex
SETUP_DIGEST = "sha256:cf743a5f" + "cd" * 28


def _asset(name, tag="v0.25", url=None, size=ZIP_SIZE, digest=ZIP_DIGEST):
    a = {"name": name, "size": size, "digest": digest}
    a["browser_download_url"] = url if url is not None else f"{REPO_DL}/{tag}/{name}"
    return a


def _mac_assets(tag="v0.25"):
    return [_asset(n, tag=tag) for n in MAC_NAMES]


def _win_assets(tag="v0.25", first="setup"):
    """Both Windows assets plus the decoy, in an order chosen per test (see truth tables)."""
    setup = _asset(SETUP_NAME, tag=tag, size=SETUP_SIZE, digest=SETUP_DIGEST)
    zipa = _asset(ZIP_NAME, tag=tag)
    decoy = _asset(DECOY_NAME, tag=tag, size=95, digest=None)
    pair = [setup, zipa] if first == "setup" else [zipa, setup]
    return [decoy] + pair + _mac_assets(tag)


def _no_network():
    return mock.patch("urllib.request.urlopen",
                      side_effect=AssertionError("the check reached the network"))


class _Fetch:
    """Injected fetch_json stand-in: records calls, returns a payload or raises."""

    def __init__(self, payload=None, exc=None):
        self.payload, self.exc, self.calls = payload, exc, []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.payload


def _release(tag, assets=None):
    data = {"tag_name": tag}
    if assets is not None:
        data["assets"] = assets
    return data


def _norm(p):
    """Compare paths across ntpath/posixpath joins: separators only."""
    return str(p).replace("\\", "/")


# ═════════════════════════════════ install_kind ═════════════════════════════════

class _Reader:
    def __init__(self, value=None, exc=None):
        self.value, self.exc, self.calls = value, exc, []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.value


class InstallKindTests(unittest.TestCase):
    """install_kind(exe_path, registry_reader) -> "inno" | "portable".

    Inno iff BOTH hold: ``unins000.exe`` is a regular file beside the exe, and
    ``registry_reader("InstallLocation")`` returns a path that equals the
    exe's directory after ``ntpath.normcase`` and stripping a trailing
    backslash. Anything else — including a reader that raises, which is what
    ``winreg`` does when the key is absent — is portable.

    Rivals: U = "unins000.exe beside the exe is enough", R = "registry value
    is enough", RAW = "both, compared as raw strings", HOST = "both, compared
    with os.path.normcase" (identity on this host), X = "reader exceptions
    propagate".

    | unins | registry value            | U    | R    | RAW  | HOST | X      | **expected** |
    | yes   | == dir                    | inno | inno | inno | inno | inno   | **inno**     |
    | yes   | None                      | inno | port | port | port | port   | **portable** |
    | no    | == dir                    | port | inno | inno | inno | inno   | **portable** |
    | yes   | == other dir              | inno | port | port | port | port   | **portable** |
    | yes   | == dir + "\\"             | inno | inno | port | inno | inno   | **inno**     |
    | yes   | == dir.upper()            | inno | inno | port | port | inno   | **inno**     |
    | yes   | reader raises OSError     | inno | rais | rais | rais | raises | **portable** |

    Every rival is wrong on at least one row; RAW and HOST are told apart by
    the upper-case row, which only Windows semantics accept on this host.
    """

    def _exe(self, unins=True):
        d = tempfile.mkdtemp(prefix="cpw-kind-")
        self.addCleanup(shutil.rmtree, d, True)
        exe = os.path.join(d, "ClaudePet.exe")
        with open(exe, "wb") as f:
            f.write(b"MZ")
        if unins:
            with open(os.path.join(d, "unins000.exe"), "wb") as f:
                f.write(b"MZ")
        return d, exe

    def test_inno_needs_both_the_uninstaller_and_a_matching_install_location(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        reader = _Reader(d)
        self.assertEqual(wu.install_kind(exe, reader), "inno")
        flat = [a for args, kw in reader.calls for a in list(args) + list(kw.values())]
        self.assertIn("InstallLocation", flat,
                      "the reader must be asked for the Inno InstallLocation value")

    def test_uninstaller_alone_is_portable(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        self.assertEqual(wu.install_kind(exe, _Reader(None)), "portable")

    def test_registry_alone_is_portable(self):
        wu = _mod()
        d, exe = self._exe(unins=False)
        self.assertEqual(wu.install_kind(exe, _Reader(d)), "portable")

    def test_registry_pointing_elsewhere_is_portable(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        other = tempfile.mkdtemp(prefix="cpw-other-")
        self.addCleanup(shutil.rmtree, other, True)
        self.assertEqual(wu.install_kind(exe, _Reader(other)), "portable")

    def test_trailing_backslash_in_install_location_is_tolerated(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        self.assertEqual(wu.install_kind(exe, _Reader(d + "\\")), "inno")

    def test_case_difference_is_tolerated_with_windows_semantics(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        self.assertNotEqual(d, d.upper(), "fixture must actually differ in case")
        self.assertEqual(ntpath.normcase(d), ntpath.normcase(d.upper()))
        self.assertEqual(wu.install_kind(exe, _Reader(d.upper())), "inno")

    def test_a_reader_that_raises_means_portable_not_a_crash(self):
        wu = _mod()
        d, exe = self._exe(unins=True)
        self.assertEqual(wu.install_kind(exe, _Reader(exc=OSError(2, "key not found"))),
                         "portable")


# ═══════════════════════════ select_update_asset_win ═══════════════════════════

class SelectAssetTests(unittest.TestCase):
    """select_update_asset_win(assets, machine, kind).

    Success returns the chosen asset as a dict with at least ``name`` (the
    allowed name, lower-cased), ``url``, ``size``, ``digest``. Refusal returns
    ``(None, status)`` with a non-empty status string; ``"no-asset"`` is
    reserved for "this machine is known and nothing is published for it"
    (ARM64 today), so the UI can say so instead of retrying forever.

    Table: AMD64 × inno → claude-pet-win-setup.exe; AMD64 × portable →
    claude-pet-win.zip; ARM64 → (None, "no-asset"); unknown machine or kind →
    (None, other status). URL must be https and on github.com.

    Rivals: F = "first asset in the list", S = "first name containing 'win'"
    (substring match), K = "ignore kind" (one Windows asset for both kinds),
    M = "ignore machine", H = "accept any scheme/host".

    The decoy ``claude-pet-win.zip.sha256`` is listed FIRST in every fixture,
    and the two Windows assets are ordered per test so that F and S never
    land on the expected name:

    | fixture order                        | kind     | F     | S     | K(zip) | K(setup) | **expected** |
    | decoy, zip, setup, mac…              | inno     | decoy | decoy | zip    | setup    | **setup**    |
    | decoy, setup, zip, mac…              | portable | decoy | decoy | zip    | setup    | **zip**      |

    K(setup) ties with the inno row and K(zip) with the portable row — each
    is refuted by the other row, which is why both rows exist.
    """

    def _refused(self, got, want_status=None):
        self.assertIsInstance(got, tuple, f"refusal must be (None, status), got {got!r}")
        self.assertEqual(len(got), 2)
        self.assertIsNone(got[0])
        self.assertIsInstance(got[1], str)
        self.assertTrue(got[1], "status must not be empty")
        if want_status is None:
            self.assertNotEqual(got[1], "no-asset", "'no-asset' is reserved for a known machine with nothing published")
        else:
            self.assertEqual(got[1], want_status)
        return got[1]

    def test_amd64_inno_takes_the_setup_exe(self):
        wu = _mod()
        got = wu.select_update_asset_win(_win_assets(first="zip"), "AMD64", "inno")
        self.assertIsInstance(got, dict, f"success must be the asset dict, got {got!r}")
        self.assertEqual(got["name"], SETUP_NAME)
        self.assertEqual(got["url"], f"{REPO_DL}/v0.25/{SETUP_NAME}")
        self.assertEqual(got["size"], SETUP_SIZE)
        self.assertEqual(got["digest"], SETUP_DIGEST)

    def test_amd64_portable_takes_the_zip(self):
        wu = _mod()
        got = wu.select_update_asset_win(_win_assets(first="setup"), "AMD64", "portable")
        self.assertIsInstance(got, dict)
        self.assertEqual(got["name"], ZIP_NAME)
        self.assertEqual(got["url"], f"{REPO_DL}/v0.25/{ZIP_NAME}")
        self.assertEqual(got["size"], ZIP_SIZE)
        self.assertEqual(got["digest"], ZIP_DIGEST)

    def test_arm64_is_refused_with_the_explicit_no_asset_status(self):
        wu = _mod()
        for kind in ("inno", "portable"):
            with self.subTest(kind=kind):
                self._refused(wu.select_update_asset_win(_win_assets(), "ARM64", kind), "no-asset")

    def test_unknown_machine_is_refused_rather_than_guessed(self):
        wu = _mod()
        for machine in ("x86", "arm64", "x86_64", "", None):
            with self.subTest(machine=machine):
                self._refused(wu.select_update_asset_win(_win_assets(), machine, "inno"))

    def test_unknown_kind_is_refused(self):
        wu = _mod()
        for kind in ("source", "", None):
            with self.subTest(kind=kind):
                self._refused(wu.select_update_asset_win(_win_assets(), "AMD64", kind))

    def test_missing_windows_asset_is_refused_but_not_as_no_asset(self):
        wu = _mod()
        got = wu.select_update_asset_win([_asset(DECOY_NAME)] + _mac_assets(), "AMD64", "portable")
        self._refused(got)

    def test_non_https_or_wrong_host_is_never_selected(self):
        wu = _mod()
        bad = (
            f"http://github.com/{cp.GITHUB_REPO}/releases/download/v0.25/{ZIP_NAME}",
            f"https://example.com/{cp.GITHUB_REPO}/releases/download/v0.25/{ZIP_NAME}",
            f"https://github.com.evil.example/{ZIP_NAME}",
            f"https:///{ZIP_NAME}",
            "",
        )
        for url in bad:
            with self.subTest(url=url):
                assets = [_asset(DECOY_NAME), _asset(ZIP_NAME, url=url)] + _mac_assets()
                self._refused(wu.select_update_asset_win(assets, "AMD64", "portable"))

    def test_case_and_surrounding_whitespace_are_normalized(self):
        wu = _mod()
        assets = [_asset(DECOY_NAME), _asset(" Claude-Pet-Win.zip ")] + _mac_assets()
        got = wu.select_update_asset_win(assets, "AMD64", "portable")
        self.assertIsInstance(got, dict)
        self.assertEqual(got["name"], ZIP_NAME)

    def test_two_assets_normalizing_to_one_name_are_ambiguous(self):
        wu = _mod()
        assets = [_asset(DECOY_NAME), _asset(ZIP_NAME), _asset("Claude-Pet-Win.zip")] + _mac_assets()
        self._refused(wu.select_update_asset_win(assets, "AMD64", "portable"))

    def test_malformed_asset_entries_do_not_raise(self):
        wu = _mod()
        assets = [None, {}, {"name": None}, "claude-pet-win.zip", 7,
                  {"name": ZIP_NAME}]                      # last one: no url at all
        got = wu.select_update_asset_win(assets, "AMD64", "portable")
        self._refused(got)


# ═══════════════════════════ check_github_update_win ═══════════════════════════

class CheckGithubUpdateWinTests(unittest.TestCase):
    """check_github_update_win(fetch_json, machine, kind, app_version).

    Returns ("update", tag, choice) only when ``cp._ver_tuple(tag) >
    cp._ver_tuple(app_version)`` and an asset was selected; ("current", tag)
    when the tag is not newer; ("error", reason) otherwise. ``tag`` is the
    release tag without its leading "v". ``choice`` carries
    ``{asset, kind, url, tag, size, digest}`` copied from the release JSON.

    Rivals: STR = "compare version strings", CONST = "compare against
    cp.APP_VERSION (0.24) and ignore the argument", GE = "treat an equal tag
    as an update", SEL1 = "select the asset before comparing versions",
    NET = "call urllib directly instead of fetch_json".

    | tag     | app_version | STR     | CONST   | GE      | **expected** |
    | v0.25   | 0.24        | update  | update  | update  | **update**   |
    | v0.25   | 0.25        | current | update  | update  | **current**  |
    | v0.25   | 0.30        | current | update  | current | **current**  |
    | v0.9    | 0.24        | update  | update  | update  | **current**  |
    | v0.100  | 0.24        | current | update  | update  | **update**   |

    STR is refuted by the last two rows, CONST by rows 2–3, GE by row 2.
    SEL1 is refuted by an ARM64 machine with an equal tag (expected current,
    SEL1 says error) and by a payload with no ``assets`` key and an equal
    tag (expected current, SEL1 raises or errors). NET is refuted by every
    test: ``urllib.request.urlopen`` raises for the duration.
    """

    CHOICE_KEYS = {"asset", "kind", "url", "tag", "size", "digest"}

    def _check(self, fetch, machine="AMD64", kind="portable", app_version="0.24"):
        wu = _mod()
        with _no_network():
            return wu.check_github_update_win(fetch, machine, kind, app_version)

    def test_newer_release_returns_update_with_the_full_choice(self):
        fetch = _Fetch(_release("v0.25", _win_assets(first="setup")))
        got = self._check(fetch, kind="portable", app_version="0.24")
        self.assertEqual(got[:2], ("update", "0.25"))
        self.assertEqual(len(got), 3)
        choice = got[2]
        self.assertIsInstance(choice, dict)
        self.assertLessEqual(self.CHOICE_KEYS, set(choice), "choice is missing keys")
        self.assertEqual(choice["asset"], ZIP_NAME)
        self.assertEqual(choice["kind"], "portable")
        self.assertEqual(choice["url"], f"{REPO_DL}/v0.25/{ZIP_NAME}")
        self.assertEqual(choice["tag"], "0.25")
        self.assertEqual(choice["size"], ZIP_SIZE)
        self.assertEqual(choice["digest"], ZIP_DIGEST)

    def test_inno_kind_chooses_the_setup_exe_in_the_choice(self):
        fetch = _Fetch(_release("v0.25", _win_assets(first="zip")))
        got = self._check(fetch, kind="inno", app_version="0.24")
        self.assertEqual(got[0], "update")
        self.assertEqual(got[2]["asset"], SETUP_NAME)
        self.assertEqual(got[2]["kind"], "inno")
        self.assertEqual(got[2]["size"], SETUP_SIZE)
        self.assertEqual(got[2]["digest"], SETUP_DIGEST)

    def test_fetch_json_is_called_once_with_the_latest_release_url(self):
        fetch = _Fetch(_release("v0.25", _win_assets()))
        self._check(fetch)
        self.assertEqual(len(fetch.calls), 1)
        args, kwargs = fetch.calls[0]
        url = args[0] if args else kwargs.get("url")
        self.assertIsInstance(url, str)
        self.assertIn(f"api.github.com/repos/{cp.GITHUB_REPO}/releases/latest", url)

    def test_equal_or_older_tag_is_current_and_uses_the_argument_not_the_constant(self):
        for tag, app_version in (("v0.25", "0.25"), ("v0.25", "0.30"), ("v0.24", "0.24")):
            with self.subTest(tag=tag, app_version=app_version):
                got = self._check(_Fetch(_release(tag, _win_assets(tag))), app_version=app_version)
                self.assertEqual(got, ("current", tag.lstrip("v")))

    def test_versions_are_compared_numerically_not_as_strings(self):
        got = self._check(_Fetch(_release("v0.9", _win_assets("v0.9"))), app_version="0.24")
        self.assertEqual(got, ("current", "0.9"), "'0.9' > '0.24' lexically; numerically it is older")
        got = self._check(_Fetch(_release("v0.100", _win_assets("v0.100"))), app_version="0.24")
        self.assertEqual(got[:2], ("update", "0.100"), "'0.100' < '0.24' lexically; numerically it is newer")

    def test_the_comparison_is_the_core_ver_tuple(self):
        """The two ports must not drift on what 'newer' means."""
        self.assertGreater(cp._ver_tuple("0.100"), cp._ver_tuple("0.24"))
        self.assertLess(cp._ver_tuple("0.9"), cp._ver_tuple("0.24"))
        got = self._check(_Fetch(_release("v0.24.1", _win_assets("v0.24.1"))), app_version="0.24")
        self.assertEqual(got[:2], ("update", "0.24.1"))

    def test_current_does_not_need_the_asset_list_at_all(self):
        got = self._check(_Fetch({"tag_name": "v0.24"}), machine="ARM64", app_version="0.24")
        self.assertEqual(got, ("current", "0.24"))

    def test_arm64_with_a_newer_release_is_an_error_carrying_no_asset(self):
        got = self._check(_Fetch(_release("v0.25", _win_assets())), machine="ARM64", app_version="0.24")
        self.assertEqual(got, ("error", "no-asset"))

    def test_newer_release_without_the_windows_asset_is_an_error_but_not_no_asset(self):
        got = self._check(_Fetch(_release("v0.25", _mac_assets())), app_version="0.24")
        self.assertEqual(got[0], "error")
        self.assertEqual(len(got), 2)
        self.assertIsInstance(got[1], str)
        self.assertTrue(got[1])
        self.assertNotEqual(got[1], "no-asset")

    def test_fetch_failure_or_bad_payload_is_an_error_not_an_exception(self):
        cases = {
            "raises": _Fetch(exc=OSError("boom")),
            "not a dict": _Fetch(["v0.25"]),
            "empty": _Fetch({}),
            "blank tag": _Fetch(_release("", _win_assets())),
            "none": _Fetch(None),
        }
        for label, fetch in cases.items():
            with self.subTest(case=label):
                got = self._check(fetch)
                self.assertEqual(got[0], "error")
                self.assertEqual(len(got), 2)
                self.assertIsInstance(got[1], str)
                self.assertTrue(got[1])


# ═══════════════════════════════ verify_download ═══════════════════════════════

class _NoHash:
    """Stands in for win_update.hashlib: any use means hashing happened."""

    def __getattr__(self, name):
        raise AssertionError(f"hashlib.{name} was used before the size check refused the file")


class VerifyDownloadTests(unittest.TestCase):
    """verify_download(path, size, digest) -> bool.

    Order: size first (a stat, no read), then the digest. The digest must be
    ``"sha256:" + 64 hex``; a missing or malformed digest refuses even when
    the size matches — the release JSON carries one for every asset, so its
    absence is a signal, not a default.

    Rivals: HF = "hash first, then size", SO = "size only" (digest ignored),
    DO = "digest only" (size ignored), MD = "missing digest ⇒ size-only pass",
    ANY = "accept any 'algo:hex' digest", LEN = "no length check".

    | file  | size arg | digest arg              | HF      | SO    | DO    | MD    | ANY   | LEN   | **expected** |
    | hello | 999      | sha256(hello)           | hashes✗ | False | True✗ | False | False | False | **False**    |
    | hello | 5        | sha256(other)           | False   | True✗ | False | False | False | False | **False**    |
    | hello | 5        | None                    | False   | True✗ | False | True✗ | False | False | **False**    |
    | hello | 5        | md5:<32 hex of hello>   | False   | True✗ | False | False | True✗ | False | **False**    |
    | hello | 5        | <64 hex, no prefix>     | False   | True✗ | False | False | False | False | **False**    |
    | hello | 5        | sha256:<63 hex>         | False   | True✗ | False | False | False | True✗ | **False**    |
    | hello | None     | sha256(hello)           | ?       | ?     | True✗ | ?     | ?     | ?     | **False**    |
    | hello | 5        | sha256(hello)           | True    | True  | True  | True  | True  | True  | **True**     |

    HF is caught by the instrument in the first row (win_update.hashlib is
    replaced by an object that raises on any attribute).
    """

    CONTENT = b"hello"

    def _file(self, content=CONTENT):
        d = tempfile.mkdtemp(prefix="cpw-dl-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, ZIP_NAME)
        with open(p, "wb") as f:
            f.write(content)
        return p

    def _digest(self, content=CONTENT):
        return "sha256:" + hashlib.sha256(content).hexdigest()

    def test_a_matching_file_passes(self):
        wu = _mod()
        p = self._file()
        self.assertIs(wu.verify_download(p, len(self.CONTENT), self._digest()), True)

    def test_size_mismatch_is_refused_before_anything_is_hashed(self):
        wu = _mod()
        p = self._file()
        with mock.patch.object(wu, "hashlib", new=_NoHash()):
            self.assertIs(wu.verify_download(p, 999, self._digest()), False)

    def test_digest_mismatch_is_refused_even_when_the_size_matches(self):
        wu = _mod()
        p = self._file()
        self.assertIs(wu.verify_download(p, len(self.CONTENT), self._digest(b"other")), False)

    def test_a_correct_digest_does_not_rescue_a_wrong_size(self):
        wu = _mod()
        p = self._file()
        self.assertIs(wu.verify_download(p, 999, self._digest()), False)
        self.assertIs(wu.verify_download(p, None, self._digest()), False)

    def test_missing_digest_is_refused(self):
        wu = _mod()
        p = self._file()
        for digest in (None, ""):
            with self.subTest(digest=digest):
                self.assertIs(wu.verify_download(p, len(self.CONTENT), digest), False)

    def test_malformed_digest_is_refused(self):
        wu = _mod()
        p = self._file()
        hexd = hashlib.sha256(self.CONTENT).hexdigest()
        bad = {
            "md5 prefix": "md5:" + hashlib.md5(self.CONTENT).hexdigest(),
            "no colon": hexd,
            "wrong length": "sha256:" + hexd[:-1],
            "too long": "sha256:" + hexd + "0",
            "not hex": "sha256:" + "zz" * 32,
            "sha1": "sha1:" + hashlib.sha1(self.CONTENT).hexdigest(),
        }
        for label, digest in bad.items():
            with self.subTest(case=label):
                self.assertIs(wu.verify_download(p, len(self.CONTENT), digest), False)

    def test_missing_file_is_refused_not_raised(self):
        wu = _mod()
        d = tempfile.mkdtemp(prefix="cpw-dl-")
        self.addCleanup(shutil.rmtree, d, True)
        self.assertIs(wu.verify_download(os.path.join(d, "absent.zip"), 5, self._digest()), False)


# ═══════════════════════════════ scan_update_zip ═══════════════════════════════

def _zip_with(members, path):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members:
            z.writestr(name, data)
    return path


class ScanUpdateZipTests(unittest.TestCase):
    """scan_update_zip(zip_path) -> bool, delegating to cp._zip_members_are_safe.

    The core scan already normalizes ``\\`` to ``/`` before looking for
    ``..`` and reads symlink targets from external_attr; the port must reuse
    it rather than write a second scanner that drifts.

    Rivals: NAME = "own scan: reject names starting with '/' or containing
    '../'" (misses backslash traversal), IMP = "bound the core function at
    import time" (delegation invisible to a patch on the core).

    | zip members                          | NAME   | IMP (real core) | **expected** |
    | ClaudePet/ClaudePet.exe, _internal/… | True   | True            | **True**     |
    | ClaudePet\\..\\evil.txt              | True✗  | False           | **False**    |
    | ../evil.txt                          | False  | False           | **False**    |
    | /evil.txt                            | False  | False           | **False**    |
    | clean zip, core patched → False      | True✗  | True✗           | **False**    |
    """

    def _tmp(self):
        d = tempfile.mkdtemp(prefix="cpw-zip-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_a_clean_portable_zip_is_accepted(self):
        wu = _mod()
        p = _zip_with([("ClaudePet/ClaudePet.exe", b"MZ"), ("ClaudePet/_internal/a.txt", b"x")],
                      os.path.join(self._tmp(), ZIP_NAME))
        self.assertIs(wu.scan_update_zip(p), True)

    def test_backslash_traversal_is_refused(self):
        wu = _mod()
        p = _zip_with([("ClaudePet/ClaudePet.exe", b"MZ"), ("ClaudePet\\..\\evil.txt", b"x")],
                      os.path.join(self._tmp(), ZIP_NAME))
        self.assertIs(wu.scan_update_zip(p), False)

    def test_dotdot_and_absolute_members_are_refused(self):
        wu = _mod()
        for name in ("../evil.txt", "/evil.txt", "ClaudePet/../../evil.txt"):
            with self.subTest(member=name):
                p = _zip_with([("ClaudePet/ClaudePet.exe", b"MZ"), (name, b"x")],
                              os.path.join(self._tmp(), ZIP_NAME))
                self.assertIs(wu.scan_update_zip(p), False)

    def test_an_unreadable_archive_is_refused_not_raised(self):
        wu = _mod()
        p = os.path.join(self._tmp(), ZIP_NAME)
        with open(p, "wb") as f:
            f.write(b"not a zip")
        self.assertIs(wu.scan_update_zip(p), False)

    def test_the_scan_is_the_core_scan(self):
        wu = _mod()
        p = _zip_with([("ClaudePet/ClaudePet.exe", b"MZ")], os.path.join(self._tmp(), ZIP_NAME))
        calls = []

        def fake(path):
            calls.append(path)
            return False
        with mock.patch.object(cp, "_zip_members_are_safe", side_effect=fake):
            self.assertIs(wu.scan_update_zip(p), False)
        self.assertEqual(calls, [p], "scan_update_zip must call cp._zip_members_are_safe with the zip path")


# ═══════════════════════════ validate_portable_layout ═══════════════════════════

MARKER = os.path.join("_internal", "claudepet-release.json")


def _required_entries():
    """PORTABLE_REQUIRED minus the two entries this fixture places itself.

    The exe and the release marker are built by name because their *shape* matters
    to the validator and to individual tests: the exe has to be a file
    (``exe=False`` removes it), and the marker's contents are the subject of
    several tests (``marker_text=``). Everything else the validator wants is taken
    from the tuple, not transcribed.
    """
    wu = _mod()
    skip = {os.path.normpath(wu.EXE_NAME), os.path.normpath(MARKER)}
    return [r for r in wu.PORTABLE_REQUIRED if os.path.normpath(r) not in skip]


def _make_tree(root, name="ClaudePet", version="0.25", exe=True, internal=True,
               marker=True, marker_text=None, omit=None):
    """A PyInstaller onedir tree the way build_win.py lays it out, under root/<name>/.

    **"Complete" is read from ``win_update.PORTABLE_REQUIRED``, never transcribed.**
    It used to be a hand-written list of four files and three directories, and it
    went stale the moment v0.26 added the two provider marks to that tuple: three
    tests asserting a complete tree is *accepted* went red against a validator that
    was doing exactly its job. A fixture that enumerates what production requires
    must be edited every time production requires more, and the only prompt to edit
    it is a red test whose message points at the validator rather than at the
    fixture. Deriving it removes the class of failure entirely.

    Entries with a file extension are created as files and the rest as directories,
    which is how build_win.py lays them out. The validator only asks
    ``os.path.exists`` for these, so the distinction is about the fixture resembling
    a real build, not about passing the check.

    ``omit`` drops one required entry, for the test that each of them is
    load-bearing.
    """
    app = os.path.join(root, name)
    os.makedirs(app, exist_ok=True)
    if exe:
        with open(os.path.join(app, "ClaudePet.exe"), "wb") as f:
            f.write(b"MZ")
    if internal:
        os.makedirs(os.path.join(app, "_internal"), exist_ok=True)
        dropped = None if omit is None else os.path.normpath(omit)
        for rel in _required_entries():
            if dropped is not None and os.path.normpath(rel) == dropped:
                continue
            target = os.path.join(app, rel)
            if os.path.splitext(rel)[1]:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as f:
                    f.write(b"\0")
            else:
                os.makedirs(target, exist_ok=True)
        frames = os.path.join(app, "_internal", "frames")
        if os.path.isdir(frames):
            with open(os.path.join(frames, "idle_0.png"), "wb") as f:
                f.write(b"\0")
        if marker or marker_text is not None:
            with open(os.path.join(app, MARKER), "w", encoding="utf-8") as f:
                if marker_text is not None:
                    f.write(marker_text)
                else:
                    json.dump({"version": version, "asset": ZIP_NAME}, f)
    return app


class PortableLayoutTests(unittest.TestCase):
    """validate_portable_layout(extract_dir, expected_tag) -> (ok, reason).

    Accepts only: exactly one top-level entry, the directory ``ClaudePet/``;
    ``ClaudePet/ClaudePet.exe`` a file; ``ClaudePet/_internal/`` a directory;
    ``ClaudePet/_internal/claudepet-release.json`` parseable JSON whose
    ``"version"`` equals the expected tag with its leading "v" removed —
    compared as strings, exactly. ``ok`` is a real bool; a refusal carries a
    non-empty reason.

    Rivals: ONE = "isdir(extract/ClaudePet) is enough" (extra entries
    ignored), FIRST/LAST = "validate the first/last directory listed",
    NOVER = "marker present is enough", TUP = "compare versions with
    _ver_tuple", NOEXE = "no exe check", ROOT = "an empty extraction has
    nothing to object to", V = "compare the tag with its 'v' left on".

    | extract_dir contents                                  | ONE   | FIRST/LAST | NOVER | TUP   | NOEXE | ROOT  | V      | **expected** |
    | ClaudePet/ (complete, 0.25) + ClaudePet2/ (complete)  | True✗ | True✗      | True✗ | True✗ | True✗ | False | False  | **False**    |
    | ClaudePet/ (complete) + README.txt at the root        | True✗ | True✗      | True✗ | True✗ | True✗ | False | False  | **False**    |
    | (empty)                                               | False | False      | False | False | False | True✗ | False  | **False**    |
    | ClaudePet/ without ClaudePet.exe                      | False | False      | False | False | True✗ | False | False  | **False**    |
    | ClaudePet/ without the marker                         | False | False      | True✗ | False | False | False | False  | **False**    |
    | marker unparseable / no "version" key                 | False | False      | True✗ | False | False | False | False  | **False**    |
    | marker 0.24, tag v0.25                                | False | False      | True✗ | False | False | False | False  | **False**    |
    | marker 0.025, tag v0.25                               | False | False      | True✗ | True✗ | False | False | False  | **False**    |
    | ClaudePet/ complete, marker 0.25, tag v0.25           | True  | True       | True  | True  | True  | True  | False✗ | **True**     |
    | ClaudePet/ complete, marker 0.25, tag 0.25            | True  | True       | True  | True  | True  | True  | True   | **True**     |

    The two-roots row uses two COMPLETE trees so that "pick one and
    validate it" passes whichever it picks — only "exactly one" refuses.

    ``_internal`` present as a file (test_internal_must_be_a_directory) is
    refused by every implementation that reads the marker, because the
    marker lives inside ``_internal`` — that row isolates no rival and is
    kept only so the reason text is exercised on that shape.
    """

    def _root(self):
        d = tempfile.mkdtemp(prefix="cpw-lay-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def _ok(self, got):
        self.assertIsInstance(got, tuple, f"must return (ok, reason), got {got!r}")
        self.assertEqual(len(got), 2)
        self.assertIs(got[0], True, f"expected acceptance, got {got!r}")

    def _refused(self, got):
        self.assertIsInstance(got, tuple, f"must return (ok, reason), got {got!r}")
        self.assertEqual(len(got), 2)
        self.assertIs(got[0], False, f"expected refusal, got {got!r}")
        self.assertIsInstance(got[1], str)
        self.assertTrue(got[1], "a refusal must say why")

    def test_a_complete_tree_matching_the_tag_is_accepted(self):
        wu = _mod()
        for tag in ("v0.25", "0.25"):
            with self.subTest(tag=tag):
                root = self._root()
                _make_tree(root, version="0.25")
                self._ok(wu.validate_portable_layout(root, tag))

    def test_every_required_entry_is_load_bearing(self):
        """Drop one entry from the tree and the validator must refuse — for each of them.

        This is the test that makes a *future* addition to PORTABLE_REQUIRED gated
        automatically, and it is the piece that was missing when v0.26 added the two
        provider marks. What existed was "a complete tree is accepted" and a handful
        of hand-picked removals (the exe, the marker); a newly required entry joined
        the tuple with nothing asserting the validator actually consults it.

        The rival it rules out is a validator that names entries it never checks —
        a list that looks like a contract and enforces nothing. Under that rival every
        subtest here passes; under a validator that checks them all, every subtest
        refuses. There is no fixture-dependent tie: the entry removed is the only
        difference between this tree and the one the test above proves is accepted.

        It iterates production's own tuple, and asserts the tuple is non-empty first —
        an empty PORTABLE_REQUIRED would make this loop run zero times and report
        success, which is the vacuous-gate shape this repository has been bitten by.
        """
        wu = _mod()
        required = list(wu.PORTABLE_REQUIRED)
        self.assertTrue(required,
                        "PORTABLE_REQUIRED is empty - this test would pass without "
                        "checking anything")
        for rel in required:
            with self.subTest(entry=rel):
                root = self._root()
                if os.path.normpath(rel) == os.path.normpath(wu.EXE_NAME):
                    _make_tree(root, version="0.25", exe=False)
                elif os.path.normpath(rel) == os.path.normpath(MARKER):
                    _make_tree(root, version="0.25", marker=False)
                else:
                    _make_tree(root, version="0.25", omit=rel)
                got = wu.validate_portable_layout(root, "v0.25")
                self.assertIs(
                    got[0], False,
                    "a tree missing %r was accepted. PORTABLE_REQUIRED names it, so "
                    "either the validator does not consult that entry or the fixture "
                    "did not actually omit it. got=%r" % (rel, got))

    def test_two_complete_roots_are_refused(self):
        wu = _mod()
        root = self._root()
        _make_tree(root, name="ClaudePet")
        _make_tree(root, name="ClaudePet2")
        self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_an_extra_top_level_file_is_refused(self):
        wu = _mod()
        root = self._root()
        _make_tree(root)
        with open(os.path.join(root, "README.txt"), "w", encoding="utf-8") as f:
            f.write("hi")
        self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_an_empty_extraction_is_refused(self):
        wu = _mod()
        self._refused(wu.validate_portable_layout(self._root(), "v0.25"))

    def test_missing_exe_is_refused(self):
        wu = _mod()
        root = self._root()
        _make_tree(root, exe=False)
        self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_internal_must_be_a_directory(self):
        wu = _mod()
        root = self._root()
        app = _make_tree(root, internal=False)
        with open(os.path.join(app, "_internal"), "wb") as f:
            f.write(b"x")
        self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_missing_marker_is_refused(self):
        wu = _mod()
        root = self._root()
        _make_tree(root, marker=False)
        self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_unparseable_or_keyless_marker_is_refused(self):
        wu = _mod()
        for text in ("{not json", "[]", '{"ver": "0.25"}', ""):
            with self.subTest(marker=text):
                root = self._root()
                _make_tree(root, marker=False, marker_text=text)
                self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_version_mismatch_is_refused_exactly_not_numerically(self):
        wu = _mod()
        for version in ("0.24", "0.26", "0.025", "0.25.0"):
            with self.subTest(marker_version=version):
                root = self._root()
                _make_tree(root, version=version)
                self._refused(wu.validate_portable_layout(root, "v0.25"))

    def test_blank_expected_tag_is_refused(self):
        wu = _mod()
        root = self._root()
        _make_tree(root)
        for tag in ("", None, "v"):
            with self.subTest(tag=tag):
                self._refused(wu.validate_portable_layout(root, tag))


# ═══════════════════════════════ build_swap_script ═══════════════════════════════

PARENT = r"C:\Users\Yeon Gyu\AppData\Local\Programs"
APP_DIR = PARENT + r"\ClaudePet"
NEW_DIR = PARENT + r"\.claudepet-new-7f3a"
OLD_DIR = PARENT + r"\.claudepet-old-v0.25"
EXE = APP_DIR + r"\ClaudePet.exe"
PID = 4242


def _occurrences(text, needle):
    """Occurrences of needle not continued by another path character."""
    return len(re.findall(re.escape(needle) + r"(?![\\/\w.\-])", text))


def _quoted(text, needle):
    return text.count("'" + needle + "'")


class SwapScriptTests(unittest.TestCase):
    """build_swap_script(app_dir, new_dir, old_dir, exe, pid) -> PowerShell text.

    The text must (1) wait for the given pid to exit, (2) rename the
    installed folder to the old name BEFORE renaming the staged folder into
    place, (3) Start-Process the exe, (4) quote every path with single
    quotes — the only PowerShell quoting that does not expand ``$`` or
    backticks — with an embedded ``'`` doubled, and never leave a user path
    unquoted anywhere in the text.

    Rivals: DQ = "double-quoted paths", RAW = "unquoted paths where no space
    is expected", ORD = "rename new→app before app→old", NOESC = "single
    quotes, no doubling", NOWAIT = "no pid wait".

    | fixture                                    | DQ    | RAW   | ORD   | NOESC | NOWAIT | **expected**            |
    | paths with a space, pid 4242               | fail  | fail  | fail  | pass  | fail   | quoted, ordered, waited |
    | app dir C:\\Users\\O'Brien\\…\\ClaudePet   | fail  | fail  | —     | fail  | —      | O''Brien, never O'Brien |
    """

    def _script(self, app=APP_DIR, new=NEW_DIR, old=OLD_DIR, exe=EXE, pid=PID):
        wu = _mod()
        s = wu.build_swap_script(app, new, old, exe, pid)
        self.assertIsInstance(s, str)
        self.assertTrue(s.strip())
        return s

    def test_waits_for_the_pid_before_touching_anything(self):
        s = self._script()
        self.assertRegex(s, r"(Wait-Process|Get-Process)[^\n]*\b%d\b" % PID)
        wait_at = min(m.start() for m in re.finditer(r"Wait-Process|Get-Process", s))
        first_rename = min(m.start() for m in re.finditer(r"Rename-Item|Move-Item", s))
        self.assertLess(wait_at, first_rename, "the wait must precede the first rename")

    def test_renames_old_out_of_the_way_before_new_into_place(self):
        s = self._script()
        lines = s.splitlines()
        app_to_old = new_to_app = None
        old_base = ntpath.basename(OLD_DIR)
        app_base = ntpath.basename(APP_DIR)
        for i, line in enumerate(lines):
            if not re.search(r"Rename-Item|Move-Item", line):
                continue
            if app_to_old is None and f"'{APP_DIR}'" in line and old_base in line:
                app_to_old = i
            elif new_to_app is None and f"'{NEW_DIR}'" in line and (f"'{app_base}'" in line or f"'{APP_DIR}'" in line):
                new_to_app = i
        self.assertIsNotNone(app_to_old, "no rename of the installed folder to the old name")
        self.assertIsNotNone(new_to_app, "no rename of the staged folder into place")
        self.assertLess(app_to_old, new_to_app)

    def test_starts_the_exe(self):
        s = self._script()
        self.assertRegex(s, r"Start-Process[^\n]*'" + re.escape(EXE) + "'")

    def test_every_path_is_single_quoted_everywhere_it_appears(self):
        s = self._script()
        for p in (APP_DIR, NEW_DIR, EXE):
            with self.subTest(path=p):
                n = _occurrences(s, p)
                self.assertGreater(n, 0, f"{p} does not appear")
                self.assertEqual(_quoted(s, p), n, f"{p} appears unquoted or double-quoted")
        if _occurrences(s, OLD_DIR):
            self.assertEqual(_quoted(s, OLD_DIR), _occurrences(s, OLD_DIR))
        else:
            base = ntpath.basename(OLD_DIR)
            self.assertGreater(_occurrences(s, base), 0, "the old name never appears")
            self.assertEqual(_quoted(s, base), _occurrences(s, base))
        self.assertNotIn('"' + PARENT, s, "a path is double-quoted")

    def test_an_embedded_single_quote_is_doubled_and_never_raw(self):
        parent = r"C:\Users\O'Brien\AppData\Local\Programs"
        s = self._script(app=parent + r"\ClaudePet", new=parent + r"\.claudepet-new-1",
                         old=parent + r"\.claudepet-old-v0.25", exe=parent + r"\ClaudePet\ClaudePet.exe")
        self.assertIn("O''Brien", s)
        self.assertIsNone(re.search(r"O'Brien", s), "an unescaped quote reached the script")

    def test_pid_is_the_integer_given(self):
        s = self._script(pid=31337)
        self.assertIn("31337", s)
        self.assertNotIn(str(PID), s)


# ═══════════════════════════════ inno_silent_args ═══════════════════════════════

SETUP_PATH = r"C:\Users\Yeon Gyu\AppData\Local\me.yeongyu.claudepet\claude-pet-win-setup.exe"
LOG_PATH = r"C:\Users\Yeon Gyu\AppData\Local\me.yeongyu.claudepet\update.log"
INNO_FLAGS = ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS")


class InnoSilentArgsTests(unittest.TestCase):
    """inno_silent_args(setup_exe, log_path) -> argv list.

    A list for subprocess, not a command line: argv[0] is the setup exe, the
    five flags are present verbatim, and exactly one element is
    ``"/LOG=" + log_path`` with no quotes added by us — CreateProcess quoting
    is subprocess's job, and a literal ``"`` inside the value would become
    part of the filename Inno opens.

    Rivals: STR = "return a shell string", Q = '/LOG="…"' with manual quotes,
    VS = "/VERYSILENT instead of /SILENT", NOLOG = "no /LOG".
    """

    def test_argv_shape_and_flags(self):
        wu = _mod()
        argv = wu.inno_silent_args(SETUP_PATH, LOG_PATH)
        self.assertIsInstance(argv, list)
        self.assertTrue(all(isinstance(a, str) for a in argv))
        self.assertEqual(argv[0], SETUP_PATH)
        for flag in INNO_FLAGS:
            with self.subTest(flag=flag):
                self.assertIn(flag, argv)

    def test_log_flag_is_the_bare_path_exactly_once(self):
        wu = _mod()
        argv = wu.inno_silent_args(SETUP_PATH, LOG_PATH)
        logs = [a for a in argv if a.upper().startswith("/LOG")]
        self.assertEqual(logs, ["/LOG=" + LOG_PATH])

    def test_no_element_carries_manual_quotes(self):
        wu = _mod()
        for a in wu.inno_silent_args(SETUP_PATH, LOG_PATH):
            self.assertNotIn('"', a)


# ═══════════════════════════════ uninstall_plan ═══════════════════════════════

CACHE_NAME = "me.yeongyu.claudepet"
HOME_FILES = (".claude_pet.json", ".claude_pet.json.lock", "claudepet_debug.log")


class UninstallPlanTests(unittest.TestCase):
    """uninstall_plan(kind, exe_dir, home) -> ordered list of (op, arg).

    ops: ``("delete", path)`` for the three per-user files that mirror the
    home entries of cp.UNINSTALL_PATHS (``.claude_pet.json``,
    ``.claude_pet.json.lock``, ``claudepet_debug.log``) and for the cache
    directory ``%LOCALAPPDATA%\\me.yeongyu.claudepet`` (``LOCALAPPDATA`` from
    the environment, else ``home\\AppData\\Local``); then, LAST, the
    kind-specific step: ``("run", [exe_dir\\unins000.exe, "/SILENT"])`` for
    inno, ``("helper", exe_dir)`` for portable. Never ``home\\.claude_pet``
    (the user's pets — parity with macOS, whose UNINSTALL_PATHS never lists
    it) and never ``home\\.claude`` (Claude Code's own directory). Unknown
    kind raises ValueError. The plan is pure: nothing here exists on disk.

    Rivals: PETS = "delete ~/.claude_pet too", SCAN = "filter by lexists"
    (drops everything, since nothing exists), ORD = "kind step first",
    ENV = "ignore LOCALAPPDATA", NOCACHE = "forget the cache dir",
    GUESS = "unknown kind → portable".
    """

    HOME = "/nonexistent/home"
    EXE_DIR = "/nonexistent/Programs/ClaudePet"

    def _plan(self, kind, localappdata=None):
        wu = _mod()
        env = dict(os.environ)
        env.pop("LOCALAPPDATA", None)
        if localappdata is not None:
            env["LOCALAPPDATA"] = localappdata
        with mock.patch.dict(os.environ, env, clear=True):
            plan = wu.uninstall_plan(kind, self.EXE_DIR, self.HOME)
        self.assertIsInstance(plan, list)
        for step in plan:
            self.assertIsInstance(step, tuple)
            self.assertEqual(len(step), 2)
            self.assertIn(step[0], ("delete", "run", "helper"))
        return plan

    def _deletes(self, plan):
        return [_norm(a) for op, a in plan if op == "delete"]

    def test_the_per_user_files_mirror_the_core_names(self):
        for name in HOME_FILES:
            self.assertIn(name, {os.path.basename(cp.CONFIG_PATH), os.path.basename(cp.CONFIG_PATH) + ".lock",
                                 "claudepet_debug.log"})
        deletes = self._deletes(self._plan("inno"))
        for name in HOME_FILES:
            with self.subTest(name=name):
                self.assertIn(_norm(os.path.join(self.HOME, name)), deletes)

    def test_cache_dir_comes_from_localappdata_when_set(self):
        deletes = self._deletes(self._plan("portable", localappdata="/nonexistent/Local"))
        self.assertIn("/nonexistent/Local/" + CACHE_NAME, deletes)
        self.assertNotIn(_norm(os.path.join(self.HOME, "AppData", "Local", CACHE_NAME)), deletes)

    def test_cache_dir_falls_back_to_home_appdata_local(self):
        deletes = self._deletes(self._plan("portable"))
        self.assertIn(_norm(os.path.join(self.HOME, "AppData", "Local", CACHE_NAME)), deletes)

    def test_never_the_pets_directory_nor_claude_code_itself(self):
        for kind in ("inno", "portable"):
            plan = self._plan(kind)
            forbidden = (_norm(os.path.join(self.HOME, ".claude_pet")), _norm(os.path.join(self.HOME, ".claude")))
            for op, arg in plan:
                for p in ([arg] if isinstance(arg, str) else list(arg)):
                    p = _norm(p)
                    for base in forbidden:
                        with self.subTest(kind=kind, step=(op, arg), base=base):
                            self.assertFalse(p == base or p.startswith(base + "/"), f"{p} is under {base}")

    def test_inno_ends_with_the_silent_uninstaller_and_has_no_helper(self):
        plan = self._plan("inno")
        self.assertEqual(plan[-1][0], "run")
        argv = plan[-1][1]
        self.assertIsInstance(argv, list)
        self.assertEqual([_norm(argv[0])] + argv[1:], [_norm(os.path.join(self.EXE_DIR, "unins000.exe")), "/SILENT"])
        self.assertNotIn("helper", [op for op, _ in plan])
        self.assertTrue(all(op == "delete" for op, _ in plan[:-1]), "deletes come first, the uninstaller last")

    def test_portable_ends_with_the_folder_helper_and_has_no_run(self):
        plan = self._plan("portable")
        self.assertEqual(plan[-1][0], "helper")
        self.assertEqual(_norm(plan[-1][1]), _norm(self.EXE_DIR))
        self.assertNotIn("run", [op for op, _ in plan])
        self.assertTrue(all(op == "delete" for op, _ in plan[:-1]))

    def test_the_plan_does_not_depend_on_anything_existing(self):
        self.assertFalse(os.path.exists(self.HOME))
        plan = self._plan("inno")
        self.assertGreaterEqual(len(self._deletes(plan)), 4)

    def test_unknown_kind_raises(self):
        wu = _mod()
        for kind in ("source", "", None):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                wu.uninstall_plan(kind, self.EXE_DIR, self.HOME)


# ═══════════════════════ cross-file pins: build_win.py / installer.iss ═══════════════════════

class BuildWinMarkerTests(unittest.TestCase):
    """build_win.py must write the marker the validator reads, under the same name.

    Pins ``build_win.write_release_marker(app_dir, version) -> path``: it
    creates ``<app_dir>\\_internal\\claudepet-release.json`` with
    ``{"version": version, …}``, ``REQUIRED`` lists that relative path so the
    bundle gate refuses a build without it, and the asset names build_win.py
    produces are the ones select_update_asset_win hands out.
    """

    def test_marker_writer_and_validator_agree(self):
        bw = importlib.import_module("windows.build_win")
        wu = _mod()
        root = tempfile.mkdtemp(prefix="cpw-mark-")
        self.addCleanup(shutil.rmtree, root, True)
        app = _make_tree(root, marker=False)
        path = bw.write_release_marker(app, "0.25")
        self.assertEqual(os.path.normpath(path), os.path.normpath(os.path.join(app, MARKER)))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["version"], "0.25")
        self.assertIs(wu.validate_portable_layout(root, "v0.25")[0], True)
        self.assertIn(MARKER, [os.path.normpath(p) for p in bw.REQUIRED])

    def test_asset_names_are_the_ones_the_updater_selects(self):
        bw = importlib.import_module("windows.build_win")
        self.assertEqual(os.path.basename(bw.ZIP), ZIP_NAME)
        self.assertEqual(os.path.basename(bw.SETUP), SETUP_NAME)
        with open(os.path.join(ROOT, "windows", "installer.iss"), encoding="utf-8") as f:
            iss = f.read()
        self.assertRegex(iss, r"(?m)^OutputBaseFilename=" + re.escape(SETUP_NAME[:-len(".exe")]) + r"\s*$")


def _iss_section(text, name):
    lines = text.splitlines()
    out, inside = [], False
    for line in lines:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = (s == f"[{name}]")
            continue
        if inside and s and not s.startswith(";"):
            out.append(s)
    return out


class InstallerScriptTests(unittest.TestCase):
    """installer.iss pins (text): the uninstaller's reach and the relaunch promise.

    * ``[UninstallDelete]`` names the cache directory
      ``{localappdata}\\me.yeongyu.claudepet`` — the update lock, downloads
      and update.log live there and Inno never logged them.
    * ``[UninstallDelete]`` never names bare ``{app}`` unless
      ``DisableDirPage=yes`` pins the directory: with a user-chosen install
      directory, ``filesandordirs {app}`` deletes files that were never ours.
    * ``RestartApplications=yes`` is only a promise if the port registers
      with the Restart Manager: the port source must contain
      ``RegisterApplicationRestart`` whenever that line is present.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "windows", "installer.iss"), encoding="utf-8") as f:
            self.iss = f.read()
        with open(os.path.join(ROOT, "windows", "claude_pet_win.py"), encoding="utf-8") as f:
            self.port = f.read()

    def test_uninstall_delete_reaches_the_cache_directory(self):
        entries = _iss_section(self.iss, "UninstallDelete")
        self.assertTrue(any(re.search(r"\{localappdata\}\\" + re.escape(CACHE_NAME) + r'"?\s*$', e)
                            for e in entries), entries)

    def test_uninstall_delete_never_names_bare_app_unless_the_dir_is_fixed(self):
        entries = _iss_section(self.iss, "UninstallDelete")
        bare = [e for e in entries if re.search(r'Name:\s*"\{app\}"\s*$', e)]
        fixed = re.search(r"(?m)^DisableDirPage=yes\s*$", self.iss) is not None
        self.assertTrue(not bare or fixed,
                        f"bare {{app}} in [UninstallDelete] with DisableDirPage != yes: {bare}")

    def test_restart_applications_is_backed_by_a_registration_in_the_port(self):
        if re.search(r"(?m)^RestartApplications=yes\s*$", self.iss):
            self.assertTrue("RegisterApplicationRestart" in self.port,
                            "installer.iss promises RestartApplications=yes but the port never calls "
                            "RegisterApplicationRestart, so a silent upgrade has no relaunch path")


# ═══════════════════════ round 2 — review B1: which check results stamp the cooldown ═══════════════════════

class CooldownTests(unittest.TestCase):
    """stamps_cooldown(result) -> bool; transient_check_reason(reason) -> bool.

    A ``check_github_update_win`` result stamps the hourly cooldown
    (``cp._upd_cache["t"]``) unless its failure is one the next 30-second
    refresh might not repeat. Only the network and a non-JSON reply are
    transient — ``fetch-failed:<ExceptionName>`` and ``bad-payload``. Every
    other outcome — update, current, and the deterministic refusals
    (``no-asset``, ``unknown-machine``, ``unknown-kind``, ``bad-url``,
    ``ambiguous-asset``, ``missing-asset``, ``no-tag``) — waits the hour
    exactly as a successful check does. A malformed result stamps nothing
    and raises nothing.

    Rivals: ALL = "stamp on every result", NONE = "stamp only on update /
    current" (the round-1 wiring — an ARM64 pet re-polled GitHub every 30 s
    for the rest of its life), EXACT = "transient iff reason in
    ('fetch-failed', 'bad-payload')" (no prefix handling), INV = "stamp only
    the transient reasons", RAISE = "index a malformed result".

    | result                              | ALL   | NONE   | EXACT  | INV    | RAISE  | **expected** |
    | ("update", "0.25", {...})           | True  | True   | True   | False✗ | True   | **True**     |
    | ("current", "0.24")                 | True  | True   | True   | False✗ | True   | **True**     |
    | ("error", "no-asset")               | True  | False✗ | True   | False✗ | True   | **True**     |
    | ("error", "unknown-machine")        | True  | False✗ | True   | False✗ | True   | **True**     |
    | ("error", "fetch-failed:OSError")   | True✗ | False  | True✗  | True✗  | False  | **False**    |
    | ("error", "bad-payload")            | True✗ | False  | False  | True✗  | False  | **False**    |
    | None / () / ("bogus",) / "update"   | —     | —      | —      | —      | raises | **False**    |
    """

    STAMPING = ("no-asset", "unknown-machine", "unknown-kind", "bad-url", "ambiguous-asset",
                "missing-asset", "no-tag")
    TRANSIENT = ("fetch-failed:OSError", "fetch-failed:URLError", "fetch-failed:TimeoutError",
                 "fetch-failed:JSONDecodeError", "bad-payload")

    def test_update_and_current_always_stamp(self):
        wu = _mod()
        for result in (("update", "0.25", {"asset": ZIP_NAME}), ("current", "0.24"), ("current", "0.25")):
            with self.subTest(result=result):
                self.assertIs(wu.stamps_cooldown(result), True)

    def test_deterministic_refusals_stamp(self):
        wu = _mod()
        for reason in self.STAMPING:
            with self.subTest(reason=reason):
                self.assertIs(wu.stamps_cooldown(("error", reason)), True)
                self.assertIs(wu.transient_check_reason(reason), False)

    def test_transient_failures_do_not_stamp(self):
        wu = _mod()
        for reason in self.TRANSIENT:
            with self.subTest(reason=reason):
                self.assertIs(wu.stamps_cooldown(("error", reason)), False)
                self.assertIs(wu.transient_check_reason(reason), True)

    def test_the_real_check_results_are_classified_the_same_way(self):
        """The helper must recognise the reason strings the check actually produces —
        a drift such as the check saying 'fetch-error:' while the helper looks for
        'fetch-failed:' would re-arm the 30-second re-poll silently."""
        wu = _mod()
        with _no_network():
            raised = wu.check_github_update_win(_Fetch(exc=OSError("boom")), "AMD64", "portable", "0.24")
            not_json = wu.check_github_update_win(_Fetch(["v0.25"]), "AMD64", "portable", "0.24")
            arm = wu.check_github_update_win(_Fetch(_release("v0.25", _win_assets())), "ARM64", "portable", "0.24")
            no_win = wu.check_github_update_win(_Fetch(_release("v0.25", _mac_assets())), "AMD64", "portable", "0.24")
            current = wu.check_github_update_win(_Fetch(_release("v0.24", _win_assets("v0.24"))), "AMD64", "portable", "0.24")
            update = wu.check_github_update_win(_Fetch(_release("v0.25", _win_assets())), "AMD64", "portable", "0.24")
        self.assertEqual(raised[0], "error")
        self.assertIs(wu.stamps_cooldown(raised), False, raised)
        self.assertEqual(not_json[0], "error")
        self.assertIs(wu.stamps_cooldown(not_json), False, not_json)
        self.assertEqual(arm, ("error", "no-asset"))
        self.assertIs(wu.stamps_cooldown(arm), True)
        self.assertEqual(no_win[0], "error")
        self.assertIs(wu.stamps_cooldown(no_win), True, no_win)
        self.assertEqual(current[0], "current")
        self.assertIs(wu.stamps_cooldown(current), True)
        self.assertEqual(update[0], "update")
        self.assertIs(wu.stamps_cooldown(update), True)

    def test_malformed_results_stamp_nothing_and_raise_nothing(self):
        wu = _mod()
        for result in (None, (), ("bogus",), "update", 7, {"status": "update"}):
            with self.subTest(result=result):
                self.assertIs(wu.stamps_cooldown(result), False)


# ═══════════════════════ round 2 — review B2: refuse before the download, no Move-Item ═══════════════════════

class SwapRefusalTests(unittest.TestCase):
    """swap_refusal(app_dir, new_dir, old_dir) -> status token | None.

    Asked before anything is downloaded. ``old-dir-exists`` when *anything*
    sits at the retired-tree name — a directory, a plain file, a dangling
    link (``lexists``); ``new-dir-exists`` likewise for the staged name;
    ``app-dir-missing`` when the installed folder is not a real directory (a
    symlink to one does not count); ``not-siblings`` when the three do not
    share one parent (``Rename-Item`` cannot cross directories). Checked in
    that order, so when several hold the token the user reads is the one
    README documents. ``None`` means the swap may start.

    Rivals: NONE = "no preflight" (round 1: the helper found out at its first
    rename, after the download), EXISTS = "os.path.exists" (a dangling link
    at old_dir passes), OLDONLY = "check old_dir and nothing else",
    ISDIR = "app_dir: isdir without islink", NOPARENT = "no sibling check",
    REV = "new_dir before old_dir".

    | fixture                           | NONE  | EXISTS | OLDONLY | ISDIR | NOPARENT | REV  | **expected**       |
    | all clear                         | None  | None   | None    | None  | None     | None | **None**           |
    | old_dir a directory               | None✗ | old    | old     | old   | old      | old  | **old-dir-exists** |
    | old_dir a dangling symlink        | None✗ | None✗  | old     | old   | old      | old  | **old-dir-exists** |
    | old_dir a plain file              | None✗ | old    | old     | old   | old      | old  | **old-dir-exists** |
    | new_dir a directory               | None✗ | new    | None✗   | new   | new      | new  | **new-dir-exists** |
    | old_dir AND new_dir directories   | None✗ | old    | old     | old   | old      | new✗ | **old-dir-exists** |
    | app_dir absent                    | None✗ | app    | None✗   | app   | app      | app  | **app-dir-missing**|
    | app_dir a symlink to a directory  | None✗ | app    | None✗   | None✗ | app      | app  | **app-dir-missing**|
    | old_dir under another parent      | None✗ | sib    | None✗   | sib   | None✗    | sib  | **not-siblings**   |
    """

    def _names(self, app=True):
        parent = tempfile.mkdtemp(prefix="cpw-swap-")
        self.addCleanup(shutil.rmtree, parent, True)
        app_dir = os.path.join(parent, "ClaudePet")
        if app:
            _make_tree(parent, name="ClaudePet")
        return parent, app_dir, os.path.join(parent, ".claudepet-new-7f3a"), os.path.join(parent, ".claudepet-old-v0.24")

    def test_all_clear_is_none(self):
        wu = _mod()
        _, app, new, old = self._names()
        self.assertIsNone(wu.swap_refusal(app, new, old))

    def test_anything_at_the_old_name_refuses(self):
        wu = _mod()
        for shape in ("directory", "file", "dangling-symlink", "partial-old-tree"):
            with self.subTest(shape=shape):
                parent, app, new, old = self._names()
                if shape == "directory":
                    os.mkdir(old)
                elif shape == "file":
                    with open(old, "wb") as f:
                        f.write(b"x")
                elif shape == "dangling-symlink":
                    os.symlink(os.path.join(parent, "gone"), old)
                    self.assertFalse(os.path.exists(old), "fixture: the link must dangle")
                else:                                      # exe and marker gone, DLLs left — what leftover_dirs skips
                    _make_tree(parent, name=os.path.basename(old), exe=False, marker=False)
                self.assertEqual(wu.swap_refusal(app, new, old), "old-dir-exists")

    def test_anything_at_the_new_name_refuses(self):
        wu = _mod()
        parent, app, new, old = self._names()
        os.mkdir(new)
        self.assertEqual(wu.swap_refusal(app, new, old), "new-dir-exists")

    def test_old_is_reported_before_new_when_both_exist(self):
        wu = _mod()
        parent, app, new, old = self._names()
        os.mkdir(new)
        os.mkdir(old)
        self.assertEqual(wu.swap_refusal(app, new, old), "old-dir-exists")

    def test_a_missing_or_linked_app_dir_refuses(self):
        wu = _mod()
        with self.subTest(shape="absent"):
            parent, app, new, old = self._names(app=False)
            self.assertFalse(os.path.lexists(app))
            self.assertEqual(wu.swap_refusal(app, new, old), "app-dir-missing")
        with self.subTest(shape="symlink-to-a-directory"):
            parent, app, new, old = self._names(app=False)
            real = _make_tree(parent, name="Real")
            os.symlink(real, app)
            self.assertTrue(os.path.isdir(app), "fixture: the link must resolve to a directory")
            self.assertEqual(wu.swap_refusal(app, new, old), "app-dir-missing")

    def test_names_under_different_parents_refuse(self):
        wu = _mod()
        parent, app, new, old = self._names()
        other = tempfile.mkdtemp(prefix="cpw-swap-other-")
        self.addCleanup(shutil.rmtree, other, True)
        self.assertEqual(wu.swap_refusal(app, new, os.path.join(other, ".claudepet-old-v0.24")), "not-siblings")
        self.assertEqual(wu.swap_refusal(app, os.path.join(other, ".claudepet-new-1"), old), "not-siblings")


_RENAME_RE = re.compile(r"(Rename-Item|Move-Item)\s+-LiteralPath\s+'((?:[^']|'')*)'\s+-(?:NewName|Destination)\s+'((?:[^']|'')*)'")
_EXIT_RE = re.compile(r"(?m)^\s*exit\s+\d+\s*$")


def _renames(text):
    """[(pos, src, dst)] for every rename in either syntax; dst may be a full path or a base name."""
    return [(m.start(), m.group(2), m.group(3)) for m in _RENAME_RE.finditer(text)]


def _is(dst, full):
    return dst == full or dst == ntpath.basename(full)


class SwapScriptRollbackTests(unittest.TestCase):
    """build_swap_script(...) — the no-overwrite renames and the rollback text.

    Round-2 pins (review B2). Every rename is ``Rename-Item`` — which fails on
    an existing destination — and never ``Move-Item``, which moves the source
    *inside* an existing destination directory and so nested the install as
    ``ClaudePet\\ClaudePet`` on rollback. The helper tests ``old_dir`` with
    ``Test-Path`` before its first rename. Each of the two rollback branches
    renames the old tree back to the app name and only THEN starts the exe —
    that order is what makes the relaunched exe the OLD one — and the
    not-running branch first moves the swapped-in tree out of the way, since
    under ``Rename-Item`` the app name must be free before old→app can succeed.

    Rivals: MOVE = "Move-Item everywhere, no Test-Path" (round 1), NOROLL =
    "no rollback at all", STARTFIRST = "start the exe, then rename back",
    NOUNWIND = "old→app without app→new first", ONEROLL = "rollback only after
    a failed new→app, none after a new app that did not stay up".

    | pin                                                        | MOVE | NOROLL | STARTFIRST | NOUNWIND | ONEROLL | **expected** |
    | 'Move-Item' absent                                         | ✗    | ✓      | ✓          | ✓        | ✓       | absent       |
    | Test-Path old_dir before the first rename                  | ✗    | ✓      | ✓          | ✓        | ✓       | present      |
    | ≥ 2 renames old→app, every one after new→app               | ✓    | ✗      | ✓          | ✓        | ✗       | present      |
    | a rename app→new after new→app and before the last old→app | ✓    | ✗      | ✓          | ✗        | ✗       | present      |
    | Start-Process exe after each old→app, before the next exit | ✓    | ✗      | ✗          | ✓        | ✗       | present      |
    """

    def _script(self):
        wu = _mod()
        return wu.build_swap_script(APP_DIR, NEW_DIR, OLD_DIR, EXE, PID)

    def _forward(self, s):
        rn = _renames(s)
        a2o = [r for r in rn if r[1] == APP_DIR and _is(r[2], OLD_DIR)]
        n2a = [r for r in rn if r[1] == NEW_DIR and _is(r[2], APP_DIR)]
        self.assertEqual(len(a2o), 1, f"expected exactly one app→old rename, got {a2o}")
        self.assertEqual(len(n2a), 1, f"expected exactly one new→app rename, got {n2a}")
        return rn, a2o[0], n2a[0]

    def test_never_move_item(self):
        s = self._script()
        self.assertNotIn("Move-Item", s, "Move-Item nests the source inside an existing destination directory")
        self.assertGreaterEqual(s.count("Rename-Item"), 2)

    def test_old_dir_is_tested_before_the_first_rename(self):
        s = self._script()
        rn, a2o, n2a = self._forward(s)
        m = re.search(r"Test-Path\s+-LiteralPath\s+'" + re.escape(OLD_DIR) + "'", s)
        self.assertIsNotNone(m, "no Test-Path on old_dir")
        self.assertLess(m.start(), min(p for p, _, _ in rn), "the Test-Path must precede every rename")

    def test_both_rollback_branches_rename_the_old_tree_back(self):
        s = self._script()
        rn, a2o, n2a = self._forward(s)
        back = [r for r in rn if r[1] == OLD_DIR and _is(r[2], APP_DIR)]
        self.assertGreaterEqual(len(back), 2, f"expected a rollback after a failed new→app AND after a dead new app, got {back}")
        for p, _, _ in back:
            self.assertGreater(p, n2a[0], "a rollback can only follow the new→app rename")
        unwind = [r for r in rn if r[1] == APP_DIR and _is(r[2], NEW_DIR)]
        self.assertGreaterEqual(len(unwind), 1, "the dead-new-app branch must move the swapped-in tree away before old→app")
        last_back = max(p for p, _, _ in back)
        self.assertTrue(any(n2a[0] < p < last_back for p, _, _ in unwind),
                        "app→new must sit between the new→app rename and the final old→app rollback")

    def test_every_rollback_relaunches_the_old_exe_before_exiting(self):
        s = self._script()
        rn, a2o, n2a = self._forward(s)
        back = [r for r in rn if r[1] == OLD_DIR and _is(r[2], APP_DIR)]
        self.assertTrue(back)
        starts = [m.start() for m in re.finditer(r"Start-Process\s+-FilePath\s+'" + re.escape(EXE) + "'", s)]
        exits = [m.start() for m in _EXIT_RE.finditer(s)]
        for p, _, _ in back:
            nxt = min([e for e in exits if e > p] or [len(s)])
            self.assertTrue(any(p < st < nxt for st in starts),
                            "after renaming old→app the helper must Start-Process the exe before it exits")


# ═══════════════════════ round 2 — review B3: no uninstall while setup.exe runs ═══════════════════════

class UninstallRefusalTests(unittest.TestCase):
    """uninstall_refusal(state) -> "installing" | None.

    The Inno installer launched by the in-app update does not inherit the
    share-none lock handle, and the app's own copy is closed as soon as setup
    is launched, so during setup's run only ``state["installing"]`` stands
    between "완전 삭제…" and ``unins000.exe /SILENT`` beside a live installer
    (review B3). A known-but-not-installing update is not a reason; a state
    that is not a dict is not a crash.

    Rivals: NONE = "never refuse" (round 1), ANYUPDATE = "refuse whenever
    state['update'] is set", STRICT = "installing is True" (identity),
    RAISE = "state.get on None propagates".

    | state                             | NONE  | ANYUPDATE   | STRICT     | RAISE  | **expected**   |
    | {"installing": True}              | None✗ | installing  | installing | inst.  | **installing** |
    | {"installing": 1}                 | None✗ | installing  | None✗      | inst.  | **installing** |
    | {}                                | None  | None        | None       | None   | **None**       |
    | {"installing": False}             | None  | None        | None       | None   | **None**       |
    | {"update": ("0.25", "https://…")} | None  | installing✗ | None       | None   | **None**       |
    | None                              | None  | None        | None       | raises | **None**       |
    """

    def test_installing_refuses(self):
        wu = _mod()
        for state in ({"installing": True}, {"installing": 1}, {"installing": True, "update": ("0.25", "u")}):
            with self.subTest(state=state):
                self.assertEqual(wu.uninstall_refusal(state), "installing")

    def test_not_installing_allows(self):
        wu = _mod()
        for state in ({}, {"installing": False}, {"installing": None},
                      {"update": ("0.25", f"{REPO_DL}/v0.25/{ZIP_NAME}")}):
            with self.subTest(state=state):
                self.assertIsNone(wu.uninstall_refusal(state))

    def test_a_state_that_is_not_a_dict_is_not_a_crash(self):
        wu = _mod()
        self.assertIsNone(wu.uninstall_refusal(None))


# ═══════════════════════ round 2 — review N1: leftovers by prefix AND shape ═══════════════════════

class LeftoverDirsTests(unittest.TestCase):
    """leftover_dirs(parent) -> our transaction leftovers beside the install
    that the next start may delete — never by name alone.

    ``.claudepet-new-*`` / ``.claudepet-old-*``: only with our exe AND a
    readable release marker (a half-removed old tree lacks them and is left
    for the user; ``swap_refusal`` then refuses on it). ``.claudepet-stage-*``:
    an extraction scratch that was never complete by design, so its prefix
    plus its *shape* — nothing inside but the archive's root ``ClaudePet`` (or
    nothing at all) — identifies it; anything else inside means it is not
    ours. Symlinked entries are never followed.

    Rivals: PREFIX = "stage dirs by prefix alone" (round 1 — README said
    otherwise), NAME = "all three prefixes by name alone", NOSTAGE = "stage
    dirs never", FOLLOW = "follow a symlinked entry".

    | entry                                             | PREFIX | NAME | NOSTAGE | FOLLOW | **expected** |
    | .claudepet-old-v0.23 with exe + marker            | yes    | yes  | yes     | yes    | **listed**   |
    | .claudepet-old-v0.24 with marker, no exe          | no     | yes✗ | no      | no     | **skipped**  |
    | .claudepet-new-7f3a with exe + marker             | yes    | yes  | yes     | yes    | **listed**   |
    | .claudepet-stage-1 empty                          | yes    | yes  | no✗     | yes    | **listed**   |
    | .claudepet-stage-2 holding only ClaudePet/        | yes    | yes  | no✗     | yes    | **listed**   |
    | .claudepet-stage-3 holding ClaudePet/ + notes.txt | yes✗   | yes✗ | no      | no     | **skipped**  |
    | .claudepet-stage-4 holding only other/            | yes✗   | yes✗ | no      | no     | **skipped**  |
    | .claudepet-old-v0.22 → symlink to a complete tree | no     | yes✗ | no      | yes✗   | **skipped**  |
    | Other/ with exe + marker (no prefix)              | no     | no   | no      | no     | **skipped**  |
    """

    def _parent(self):
        parent = tempfile.mkdtemp(prefix="cpw-left-")
        self.addCleanup(shutil.rmtree, parent, True)
        _make_tree(parent, name="ClaudePet")                                   # the live install, never listed
        _make_tree(parent, name=".claudepet-old-v0.23", version="0.23")
        _make_tree(parent, name=".claudepet-old-v0.24", version="0.24", exe=False)
        _make_tree(parent, name=".claudepet-new-7f3a")
        os.mkdir(os.path.join(parent, ".claudepet-stage-1"))
        _make_tree(os.path.join(parent, ".claudepet-stage-2"), name="ClaudePet", exe=False, internal=False)
        _make_tree(os.path.join(parent, ".claudepet-stage-3"), name="ClaudePet")
        with open(os.path.join(parent, ".claudepet-stage-3", "notes.txt"), "w", encoding="utf-8") as f:
            f.write("mine")
        os.makedirs(os.path.join(parent, ".claudepet-stage-4", "other"))
        real = _make_tree(parent, name="Other", version="0.22")
        os.symlink(real, os.path.join(parent, ".claudepet-old-v0.22"))
        return parent

    def test_listed_and_skipped(self):
        wu = _mod()
        parent = self._parent()
        got = {os.path.basename(p) for p in wu.leftover_dirs(parent)}
        self.assertEqual(got, {".claudepet-old-v0.23", ".claudepet-new-7f3a", ".claudepet-stage-1", ".claudepet-stage-2"})

    def test_an_unreadable_parent_is_an_empty_list(self):
        wu = _mod()
        self.assertEqual(wu.leftover_dirs("/nonexistent/parent/for/claudepet"), [])


# ═══════════════════════ round 2 — the helpers are wired into the port (text pins) ═══════════════════════

def _method(text, name):
    """The source text of ``def <name>(`` up to the next def at the same indentation."""
    m = re.search(r"(?m)^(\s*)def " + re.escape(name) + r"\(", text)
    if m is None:
        return ""
    indent = m.group(1)
    rest = text[m.end():]
    n = re.search(r"(?m)^" + indent + r"(def |class |@)", rest)
    return text[m.start():m.end() + (n.start() if n else len(rest))]


class PortWiringTests(unittest.TestCase):
    """windows/claude_pet_win.py text pins: the three round-2 helpers are wired.

    A pure helper that nothing calls fixes nothing. The port cannot be
    imported here (PySide6/winreg), so — as with the installer.iss pins — the
    source text is the observable: ``_run_update_check`` consults
    ``stamps_cooldown`` (B1); ``_install_update`` consults ``swap_refusal``
    before it downloads (B2); ``_uninstall`` consults ``uninstall_refusal``
    (B3). Each name must appear inside that method, not merely somewhere in
    the file (a comment or docstring would satisfy a whole-file search).
    """

    def setUp(self):
        with open(os.path.join(ROOT, "windows", "claude_pet_win.py"), encoding="utf-8") as f:
            self.port = f.read()

    def test_b1_the_check_stamps_the_cooldown_through_the_helper(self):
        body = _method(self.port, "_run_update_check")
        self.assertTrue(body, "no _run_update_check in the port")
        self.assertIn("stamps_cooldown(", body)

    def test_b2_the_install_asks_swap_refusal_before_it_downloads(self):
        body = _method(self.port, "_install_update")
        self.assertTrue(body, "no _install_update in the port")
        ask = body.find("swap_refusal(")
        download = body.find("_download_update_zip(")
        self.assertGreater(ask, -1, "the install never asks swap_refusal")
        self.assertGreater(download, -1, "the install never downloads")
        self.assertLess(ask, download, "the refusal must come before the download")

    def test_b3_the_uninstall_asks_uninstall_refusal(self):
        body = _method(self.port, "_uninstall")
        self.assertTrue(body, "no _uninstall in the port")
        self.assertIn("uninstall_refusal(", body)


# ═══════════════════ round 3 — every log_update call site in the port executes (B4) ═══════════════════

_TOKEN = "tok"          # stands in for every computed argument; lowercase so it passes the step shape too
_LINE_SHAPE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ [a-z]+( [A-Za-z_]+=[^ ]+)*$")


def _log_update_calls(text):
    """Every ``wu.log_update(...)`` in the port, as (lineno, args, kwargs, splat).

    A token stands in for each computed value. ``splat`` is True when the
    call carries ``*x`` or ``**x`` — a shape this gate cannot replay and
    therefore refuses.
    """
    def value_of(node):
        return node.value if isinstance(node, ast.Constant) else _TOKEN
    out = []
    for node in ast.walk(ast.parse(text)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "log_update"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "wu"):
            continue
        splat = any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords)
        args = [value_of(a) for a in node.args if not isinstance(a, ast.Starred)]
        kwargs = {k.arg: value_of(k.value) for k in node.keywords if k.arg is not None}
        out.append((node.lineno, args, kwargs, splat))
    return sorted(out)


def _function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _is_type_name(node):
    """``type(e).__name__`` — the only exception spelling CLAUDE.md § Privacy lets into a log line."""
    return (isinstance(node, ast.Attribute) and node.attr == "__name__"
            and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "type")


class LogUpdateCallShapeTests(unittest.TestCase):
    """Every ``wu.log_update(`` call site in windows/claude_pet_win.py executes (B4).

    ``log_update(step, path=None, **fields)`` takes ``step`` and ``path`` by
    name, so a call site that spells a *field* ``step=`` or ``path=`` raises
    ``TypeError`` the moment it is reached — which for a failure handler is
    the moment the user most needs the line, and on a windowed exe the
    traceback goes nowhere visible. The port cannot be imported here, so each
    call is lifted out with ``ast`` and replayed through the real
    ``log_update`` into a temp file; the two ``_uninstall`` launch-failure
    handlers are then read for the whole of what B4 asked: log with the
    failure vocabulary, tell the user, return before anything is deleted.
    The fixture is the port text itself; the rivals are edits of it:

    | port | executes | b4 handlers |
    | --- | --- | --- |
    | round-2 port, ``step="run-uninstaller"`` (5a5af83a…) | TypeError ×2 | no ``status`` |
    | ``path="run-uninstaller"`` instead | TypeError ×2 (path) | ok |
    | the two handler log lines deleted | ok | < 2 handlers log |
    | log, but no ``_info`` | ok | user not told |
    | ``error=str(e)`` | ok | privacy |
    | log + tell, but no ``return`` | ok | deletion proceeds |
    | a handler with no positional step | TypeError (missing) | step is None |
    | a constant value carrying a space | malformed line | status ≠ failed |
    | ``**fields`` splat | refused | no ``status`` (nothing to read) |
    | **worktree** | **ok, one well-formed line each** | **2, all four properties** |
    """

    def setUp(self):
        with open(os.path.join(ROOT, "windows", "claude_pet_win.py"), encoding="utf-8") as f:
            self.port = f.read()

    def test_every_call_site_executes_and_writes_one_well_formed_line(self):
        wu = _mod()
        calls = _log_update_calls(self.port)
        steps = {a[0] for _, a, _, _ in calls if a}
        self.assertTrue({"check", "install", "swap", "uninstall"} <= steps,
                        f"the README's hardware tokens are not all logged: {sorted(map(str, steps))}")
        self.assertEqual([ln for ln, _, _, splat in calls if splat], [], "a splatted call cannot be replayed here")
        failures = []
        with tempfile.TemporaryDirectory() as td:
            log = os.path.join(td, "cache", "update.log")
            for lineno, args, kwargs, _ in calls:
                try:
                    wu.log_update(*args, path=log, **kwargs)
                except Exception as e:  # the shape of the failure is the finding
                    failures.append(f"line {lineno}: {type(e).__name__}: {e}")
            self.assertEqual(failures, [])
            with open(log, encoding="utf-8") as f:
                lines = f.read().splitlines()
        self.assertEqual(len(lines), len(calls), "every call site writes exactly one line")
        self.assertEqual([l for l in lines if not _LINE_SHAPE.match(l)], [], "every line is <utc> <step> k=v …")
        self.assertEqual([l for l in lines if td in l], [], "no line carries the log's own path")

    def test_b4_both_uninstall_launch_failures_log_status_failed_tell_the_user_and_return(self):
        fn = _function(ast.parse(self.port), "_uninstall")
        self.assertIsNotNone(fn, "no _uninstall in the port")
        handlers = []
        for h in ast.walk(fn):
            if not isinstance(h, ast.ExceptHandler):
                continue
            logs = [n for n in ast.walk(h) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "log_update"]
            if not logs:
                continue                      # the delete loop's handler keeps the error for the summary line
            kw = {k.arg: k.value for k in logs[0].keywords}
            first = logs[0].args[0] if logs[0].args else None
            handlers.append({
                "line": h.lineno,
                "step": first.value if isinstance(first, ast.Constant) else None,
                "status": kw["status"].value if isinstance(kw.get("status"), ast.Constant) else None,
                "error_is_type_name": _is_type_name(kw.get("error")),
                "told": any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_info"
                            for n in ast.walk(h)),
                "returns": bool(h.body) and isinstance(h.body[-1], ast.Return),
            })
        self.assertGreaterEqual(len(handlers), 2,
                                f"fewer than two failure handlers in _uninstall log anything: {handlers}")
        for h in handlers:
            with self.subTest(line=h["line"]):
                self.assertEqual(h["step"], "uninstall")
                self.assertEqual(h["status"], "failed", "a failure line says status=failed like every other one")
                self.assertTrue(h["error_is_type_name"], "error= must be type(e).__name__ (CLAUDE.md § Privacy)")
                self.assertTrue(h["told"], "the user must be told (unin_fail) once the line is logged")
                self.assertTrue(h["returns"], "a launch failure returns before anything is deleted")


# ═══════════ round 3 (second gate) — every log_update call site binds by keyword *name* (B4) ═══════════

PORT_SOURCE_ENV = "CLAUDE_PET_WIN_PORT_SOURCE"
_PLACEHOLDER = "x"


def _port_source():
    """The port text this gate reads, and the path it came from.

    Normally ``windows/claude_pet_win.py`` in this tree. The environment
    variable exists for one purpose: observing the RED state against a
    retained pre-fix copy without copying the whole tree (AGENTS.md §3, "revert
    and observe"). When it is set, the path and the file's SHA-256 go to
    stderr so a record of that run says which bytes were gated — an override
    is never silent.
    """
    override = os.environ.get(PORT_SOURCE_ENV)
    path = override or os.path.join(ROOT, "windows", "claude_pet_win.py")
    with open(path, "rb") as f:
        raw = f.read()
    if override:
        sys.stderr.write(f"[{PORT_SOURCE_ENV}] gating {path} sha256={hashlib.sha256(raw).hexdigest()}\n")
    return path, raw.decode("utf-8")


def _log_update_sites(text):
    """Every ``wu.log_update(...)`` in the port as (lineno, positional, names, splat).

    ``positional``: a string literal is kept verbatim (it is the step token the
    port passes), anything computed becomes the placeholder. ``names``: the
    keyword names in call order. ``splat``: True when the call carries ``*x``
    or ``**x`` — names this gate cannot see and therefore cannot vouch for.
    """
    out = []
    for node in ast.walk(ast.parse(text)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "log_update"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "wu"):
            continue
        splat = (any(isinstance(a, ast.Starred) for a in node.args)
                 or any(k.arg is None for k in node.keywords))
        positional = [a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else _PLACEHOLDER
                      for a in node.args if not isinstance(a, ast.Starred)]
        names = [k.arg for k in node.keywords if k.arg is not None]
        out.append((node.lineno, positional, names, splat))
    return sorted(out)


def _count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        return len(f.read().splitlines())


class LogUpdateKeywordBindingTests(unittest.TestCase):
    """Every ``wu.log_update(`` call site in the port binds to
    ``log_update(step, path=None, **fields)`` by keyword *name* (B4, second gate).

    ``LogUpdateCallShapeTests`` above replays each call with its constants and
    reads the written line back. This gate asks the narrower question the
    Reviewer's round-3 ask names — does the *keyword set* of each call bind
    against the signature at all — and asks it twice per site: first through
    ``inspect.signature(log_update).bind`` with placeholder values, so the
    finding is the binding error itself with nothing executed; then through
    the real call into a temp file, counting that the file gained exactly one
    line. Every value is a placeholder, so a site that fails here fails for
    its *names* — ``step=`` or ``path=`` spelled as a field, a missing
    positional step — and not for what it logs. A ``path=`` field and a
    ``**`` splat are refused up front rather than replayed: the first would
    send the line to a file named after its value (no error, no line in
    update.log), the second hides its names from any static gate.

    Fixture: the port text. Rivals are edits of it (the scratch copies under
    the session scratchpad, ``vcd3/rivals``), T1 = names test, T2 = bind test:

    | port | T1 (path=/splat) | T2 (bind, call, +1 line) |
    | --- | --- | --- |
    | round-2 port, ``step="run-…"`` at 1286/1297 (5a5af83a…) | ok | FAIL — ``multiple values for argument 'step'`` ×2, bind and call |
    | ``path="run-…"`` instead (RA) | FAIL — a field named path | ok (path is dropped from the replay) |
    | no positional step at 1286 (RF) | ok | FAIL — ``missing a required argument: 'step'`` |
    | ``**dict(...)`` at 1286 (RH) | FAIL — hidden names | ok (the splat is skipped) |
    | handler lines deleted / no ``_info`` / ``str(e)`` / no ``return`` (RB–RE) | ok | ok — not this gate's question; ``LogUpdateCallShapeTests`` holds those |
    | ``status="failed to launch"`` (RG) | ok | ok — a value, not a name; the first gate's line-shape check holds it |
    | **worktree** | **ok** | **ok — 28 bind, 28 call, 28 lines** |

    Each of R0, RA, RF, RH is red on at least one of the two tests; T1 is the
    sole discriminator for RA and RH, T2 for R0 and RF, so neither is redundant.
    """

    @classmethod
    def setUpClass(cls):
        cls.path, cls.port = _port_source()
        cls.sites = _log_update_sites(cls.port)

    def test_no_call_site_hides_or_misroutes_its_field_names(self):
        self.assertTrue(self.sites, f"no wu.log_update( call in {self.path} — the gate has nothing to gate")
        self.assertEqual([ln for ln, _, names, _ in self.sites if "path" in names], [],
                         "a field spelled path= is log_update's log-file parameter: the line would go to a "
                         "file named after the value and never reach update.log")
        self.assertEqual([ln for ln, _, _, splat in self.sites if splat], [],
                         "a * or ** splat hides its keyword names from this gate; spell the fields out")

    def test_every_call_site_binds_and_writes_exactly_one_line(self):
        wu = _mod()
        sig = inspect.signature(wu.log_update)
        self.assertTrue(self.sites, f"no wu.log_update( call in {self.path} — the gate has nothing to gate")
        findings = []
        with tempfile.TemporaryDirectory() as td:
            log = os.path.join(td, "cache", "update.log")
            for lineno, positional, names, _ in self.sites:
                fields = {k: _PLACEHOLDER for k in names if k != "path"}
                try:
                    sig.bind(*positional, path=log, **fields)
                except TypeError as e:
                    findings.append(f"line {lineno}: bind: TypeError: {e}")
                before = _count_lines(log)
                try:
                    wu.log_update(*positional, path=log, **fields)
                except TypeError as e:
                    findings.append(f"line {lineno}: call: TypeError: {e}")
                gained = _count_lines(log) - before
                if gained != 1:
                    findings.append(f"line {lineno}: the log gained {gained} lines, expected 1")
        self.assertEqual(findings, [], f"gated {self.path}")



if __name__ == "__main__":
    unittest.main()
