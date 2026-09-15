"""Static release-preparation gates for v0.25.

Status as of 2026-09-13 (Verifier verifier-v025, final pin run): v0.24 is published (tag
``v0.24`` on origin, GitHub release of 2026-09-12T15:55Z, release commit a1f3d22), so
everything from the ``**v0.24**`` heading to the end of ``RELEASE_NOTES.md`` is frozen
text and is pinned here byte for byte, alongside the older v0.23 and v0.22 pins.  The
single unpublished section above it is ``**v0.25**``, and ``APP_VERSION`` is ``"0.25"`` —
the bump the release commit carries.  ``PublishedV023NotesContractTests`` and
``PublishedV024NotesContractTests`` keep holding the frozen v0.23 and v0.24 prose to the
source they describe (a published promise outlives its release; the v0.24 class is the
former ``StagedV024NotesFormatTests`` with its assertions unchanged, only its status
renamed), and ``StagedV025NotesFormatTests`` holds the v0.25 section to CLAUDE.md's
release-note format rule and cross-checks every checkable claim in it against the source.

Lineage: ``test_v022_release_contract.py`` → ``test_v023_release_contract.py`` →
``test_v024_release_contract.py`` → this file; each release renames the module with
``git mv`` and rewrites it for the version its release commit carries.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse repository text and
bytes (the tracked sources, plus the two files under ``fonts/`` the v0.24 notes promise
are bundled).  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.25 application/verifier/script bytes change, and
the ``--expect-version`` usage example in ``verify_release_artifact.py`` is held to the
bumped version because every release commit since v0.21 moved it with ``APP_VERSION``
(``git log -S'--expect-version 0.22'``; a1f3d22 moved it to 0.24) and ``release.sh``
passes ``$(cur_version)``, so that example is the only place a stale version literal can
survive a release.

Claims in the notes are cross-checked against the source rather than merely spelled out
here, because a note and a constant can drift apart in either direction.  The v0.25
pairs: the quoted menu label "로그인 시 자동 실행" against ``TR["ko"]["menu_autostart"]``;
"시스템 설정 … 에서 끄면 메뉴에도 꺼진 것으로 보입니다" against ``autostart_read_state``
asking the service for ``status()`` on every read and none of the autostart functions
writing to ``RUNTIME`` or the config; "토큰을 갱신하거나 서버 응답이 잠깐 실패해도 재시작
없이" against ``_read_oauth_token``'s file-signature and re-validation paths, the forced
re-read on 401/403 and the ``suspect`` flag in ``_fetch_oauth_usage``, and
``OAUTH_FAIL_RETRY_SEC`` being shorter than ``OAUTH_CACHE_SEC`` and consulted by
``fetch_exact_usage``; the quoted "완전 삭제…" against ``TR["ko"]["menu_uninstall"]`` and
"내 펫 폴더는 남깁니다" against ``UNINSTALL_PATHS`` naming the config and the cache
directory but never the user's pet home.  The v0.24 pairs keep theirs (thresholds,
marker glyphs, font, nested layout, toggle wording, colour roles), and the v0.23 pairs
theirs ("1시간" against ``UPDATE_CHECK_SEC``, the quoted menu label, no check at launch,
straight to the latest release).  Pinning only one side of any of these pairs would let
the other side move silently.  The behavioural gates for the token cache are in
tests/test_oauth_token_cache.py and for the sign-in item in tests/test_autostart.py;
this module only ties the prose to them.

The Windows claims in the v0.25 notes (the same menu item there, in-app update for the
installer and the portable zip, "작업 관리자") are built on the Windows branch, not by
this tree, so no gate in this checkout can say whether they hold — only the macOS half of
each sentence is checked here.
"""

from __future__ import annotations

import ast
import hashlib
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO / "claude_pet.py"
RELEASE_VERIFIER = REPO / "verify_release_artifact.py"
BUILD_SCRIPT = REPO / "build_app.sh"
RELEASE_SCRIPT = REPO / "release.sh"
SETUP = REPO / "setup.py"
FONT_DIR = REPO / "fonts"
RELEASE_NOTES = REPO / "RELEASE_NOTES.md"
CLAUDE_POLICY = REPO / "CLAUDE.md"
MANUAL_TEST = REPO / "tests" / "test_manual_update_transaction.py"
UPLOAD_TEST = REPO / "tests" / "test_upload_artifact_gate.py"

# Pinning from the newest *published* heading through EOF lets the unpublished section
# be rewritten freely while making every byte users already received immutable.
# v0.22-and-older: computed from the v0.22 release commit's blob (6d47df5e,
# `git show HEAD:RELEASE_NOTES.md` at the time) and unchanged since (2026-09-11).
PUBLISHED_V022_AND_OLDER_SHA256 = (
    "6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239"
)
# v0.23-and-older: from the ``**v0.23**`` heading through EOF, computed from the v0.23
# release commit's blob (`git show 81619b3:RELEASE_NOTES.md`, 22896 bytes, of which the
# suffix is 18516) and confirmed identical in the working tree after the v0.24 section
# was staged above it (2026-09-12T12:41Z; re-checked 2026-09-12T14:22Z).
PUBLISHED_V023_AND_OLDER_SHA256 = (
    "c7ddc40a8a25ce8eefac9867032a6a14f20425c6ae0368db41a86d859c96b562"
)
# v0.24-and-older: from the ``**v0.24**`` heading through EOF, computed from the v0.24
# release commit's blob (`git show a1f3d22:RELEASE_NOTES.md`, 23826 bytes, of which the
# suffix is 19446), identical in HEAD 36c2118 and confirmed identical in the working tree
# after the v0.25 section was staged above it (2026-09-13).
PUBLISHED_V024_AND_OLDER_SHA256 = (
    "c38940804b5b94ef72bf49727ac41a82d672dc779d45e53a3436a2460a1cddb4"
)

# The cadence the published v0.23 notes promise, and the Korean label they name.
EXPECTED_UPDATE_CHECK_SEC = 3600
KO_CHECK_LABEL = "⬆︎ 업데이트 확인…"

# What each locale's context-menu toggle must call the thing it toggles (v0.24 renamed
# the gauges to the summary pill), and the Korean wording the v0.24 notes reuse.
PILL_WORDS = {"en": "pill", "ko": "필", "ja": "ピル", "es": "píldora"}
KO_TOGGLE_WORDING = "접기/펴기"

# The two Korean menu labels the v0.25 notes quote, exactly as the source spells them.
KO_AUTOSTART_LABEL = "로그인 시 자동 실행"
KO_UNINSTALL_LABEL = "완전 삭제…"


# CLAUDE.md release-note step 2 forbids these in a user-facing entry.
FORBIDDEN_NOTE_PATTERNS = {
    "hash": r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{7,64}(?![0-9A-Fa-f])",
    "source path": r"(?:^|\s)[^\s`]*(?:\.py|\.sh|tests?/)[^\s`]*",
    "line reference": r"(?:\bline\s*\d+|\d+\s*행)",
    "internal identifier": r"(?:\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b|\b(?:APP_VERSION|RUNTIME|NSPanel)\b|\b[A-Za-z_]\w*\()",
    "test matrix/count prose": r"(?:테스트|매트릭스|fixture|unittest|\b(?:GREEN|RED|PASS|FAIL)\b|\d+\s*(?:tests?|테스트))",
    "unsupported magnitude/frequency": r"(?:대폭|훨씬|엄청|매우|대부분|대다수|많이|자주|종종|드물게|가끔|항상|완전히|상당히)",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal_assignments(path: Path, name: str) -> list[object]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: list[object] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        try:
            values.append(ast.literal_eval(node.value))
        except (TypeError, ValueError) as exc:
            raise AssertionError(f"{path.name}:{name} must remain a literal") from exc
    return values


def _one_literal_string(path: Path, name: str) -> str:
    values = _literal_assignments(path, name)
    if len(values) != 1 or not isinstance(values[0], str):
        raise AssertionError(
            f"{path.name} must define exactly one literal string {name}; got {values!r}"
        )
    return values[0]


def _one_literal_int(path: Path, name: str) -> int:
    values = _literal_assignments(path, name)
    if len(values) != 1 or type(values[0]) is not int:
        raise AssertionError(
            f"{path.name} must define exactly one literal int {name}; got {values!r}"
        )
    return values[0]


def _tr_table() -> dict:
    tables = _literal_assignments(APP_SOURCE, "TR")
    if len(tables) != 1 or not isinstance(tables[0], dict):
        raise AssertionError("claude_pet.py must define exactly one literal TR")
    return tables[0]


def _sentences(text: str) -> list[str]:
    """Split ordinary Korean release-note prose without splitting decimal values."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])(?:[\"'”’)]*)\s+", text.strip())
        if part.strip()
    ]


def _has_all(text: str, patterns: tuple[str, ...]) -> bool:
    return all(re.search(pattern, text, re.I) for pattern in patterns)


def _notes_block(text: str, heading: str, next_heading: str) -> str:
    """The visible body of one changelog section, comments stripped."""
    if text.count(heading) != 1:
        raise AssertionError(f"expected exactly one {heading} heading")
    if text.index(heading) >= text.index(next_heading):
        raise AssertionError(f"{heading} must sit above {next_heading}")
    block = text.split(heading, 1)[1].split(next_heading, 1)[0]
    return re.sub(r"<!--.*?-->", "", block, flags=re.S).strip()


def _bullet_shape(visible: str) -> tuple[list[str], list[str], list[str]]:
    """(top-level bullet lines, nested bullet lines, joined bullet texts)."""
    lines = visible.splitlines()
    top_level = [line for line in lines if re.match(r"^-\s+\S", line)]
    nested = [line for line in lines if re.match(r"^\s+-\s+\S", line)]
    bullets: list[str] = []
    current: list[str] | None = None
    preamble: list[str] = []
    for line in lines:
        if line.startswith("- "):
            if current is not None:
                bullets.append(" ".join(current))
            current = [line[2:].strip()]
        elif line.strip():
            if current is None:
                preamble.append(line.strip())
            else:
                current.append(line.strip())
    if current is not None:
        bullets.append(" ".join(current))
    if preamble:
        raise AssertionError(f"release body must consist only of bullets; got {preamble!r}")
    return top_level, nested, bullets


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_def(path: Path, name: str) -> ast.AST:
    """The single module-level definition called name."""
    found = [
        n for n in _module_tree(path).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.name == name
    ]
    if len(found) != 1:
        raise AssertionError(f"{path.name} must define exactly one module-level {name}")
    return found[0]


def _module_assignment(path: Path, name: str) -> ast.Assign:
    """The single module-level ``name = …`` statement, unevaluated."""
    found = [
        n for n in _module_tree(path).body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
    ]
    if len(found) != 1:
        raise AssertionError(f"{path.name} must assign module-level {name} exactly once")
    return found[0]


def _nested_function(outer: ast.AST, name: str) -> ast.FunctionDef:
    """The single function called name defined anywhere inside outer."""
    found = [n for n in ast.walk(outer) if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(f"expected exactly one nested function {name}, found {len(found)}")
    return found[0]


def _strings(nodes) -> set[str]:
    out: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.add(child.value)
    return out


def _names(node: ast.AST) -> set[str]:
    """Every bare name read or written anywhere inside node."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _calls_to(node: ast.AST, name: str) -> list[ast.Call]:
    """Calls of the bare name ``name(...)`` anywhere inside node."""
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name]


def _method_calls(node: ast.AST, attr: str) -> list[ast.Call]:
    """Calls of ``<anything>.attr(...)`` anywhere inside node."""
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == attr]


class VersionAndPinContractTests(unittest.TestCase):
    def test_v025_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.25"]:
            problems.append(f"APP_VERSION must be one literal '0.25', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.25" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.25")
        for stale in ("0.24", "0.23", "0.26"):
            if f"--expect-version {stale}" in verifier_text:
                problems.append(
                    f"verify_release_artifact.py still advertises --expect-version {stale}"
                )

        expected_pins = (
            (MANUAL_TEST, "REVIEWED_APP_SOURCE_SHA256", APP_SOURCE),
            (MANUAL_TEST, "REVIEWED_BUILD_APP_SHA256", BUILD_SCRIPT),
            (UPLOAD_TEST, "REVIEWED_APP_SOURCE_SHA256", APP_SOURCE),
            (UPLOAD_TEST, "REVIEWED_VERIFIER_SHA256", RELEASE_VERIFIER),
            (UPLOAD_TEST, "REVIEWED_RELEASE_SHA256", RELEASE_SCRIPT),
        )
        for path, name, pinned_file in expected_pins:
            actual_sha = _sha256(pinned_file)
            try:
                pinned_sha = _one_literal_string(path, name)
            except AssertionError as exc:
                problems.append(str(exc))
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", pinned_sha):
                problems.append(f"{path.name}:{name} is not a literal lowercase SHA-256")
            elif pinned_sha != actual_sha:
                problems.append(
                    f"{path.name}:{name} pins {pinned_sha}, final {pinned_file.name} is {actual_sha}"
                )

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


class PublishedNotesImmutabilityTests(unittest.TestCase):
    def test_published_v022_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.22**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.22 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V022_AND_OLDER_SHA256,
            "published v0.22-and-older bytes were rewritten or dropped",
        )

    def test_published_v023_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.23**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.23 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V023_AND_OLDER_SHA256,
            "published v0.23-and-older bytes were rewritten or dropped",
        )

    def test_published_v024_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.24**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.24 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V024_AND_OLDER_SHA256,
            "published v0.24-and-older bytes were rewritten or dropped",
        )

    def test_v025_is_the_only_unpublished_heading_and_sits_directly_above_v024(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["0.25", "0.24"],
            "the unpublished v0.25 section must sit directly above the published v0.24 "
            f"heading, with nothing newer above it; got {headings[:2]!r}",
        )
        self.assertEqual(headings.count("0.25"), 1, "v0.25 heading must appear once")


class PublishedV023NotesContractTests(unittest.TestCase):
    """The published v0.23 section: its bytes are frozen above, and the source must still
    keep every promise it made — a published note is a contract with the users who read
    it, not a description of one release."""

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.23**", "**v0.22**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v023_notes_follow_the_three_bullet_450_character_format(self):
        self.assertEqual(
            len(self.top_level), 3,
            f"v0.23 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        self.assertEqual(self.nested, [], "v0.23 must not contain nested bullets")
        self.assertEqual(len(self.bullets), 3)

        normalized_body = " ".join(self.visible.split())
        self.assertLessEqual(
            len(normalized_body), 450,
            f"v0.23 Korean body is {len(normalized_body)} Unicode characters; max is 450")

        for index, bullet in enumerate(self.bullets, 1):
            with self.subTest(bullet=index):
                self.assertRegex(bullet, r"[가-힣]", "each release bullet must be Korean")
                count = len(_sentences(bullet))
                self.assertGreaterEqual(count, 1, "each bullet must be at least one sentence")
                self.assertLessEqual(count, 2, "each bullet must have at most 2 sentences")

    def test_v023_notes_state_the_user_facing_behaviour_and_nothing_internal(self):
        problems: list[str] = []
        body = self.body

        # 1. No check at launch; a periodic check every hour instead; a new version still
        #    surfaces as an install item at the top of the context menu.
        if not _has_all(body, (r"새\s*버전", r"켤\s*때", r"하지\s*않", r"1\s*시간", r"마다")):
            problems.append(
                "say the new-version check no longer runs at launch and runs every hour instead")
        if not _has_all(body, (r"새\s*버전이\s*있으면", r"우클릭", r"메뉴", r"(?:맨\s*위|최상단)", r"설치")):
            problems.append(
                "say a new version still appears as an install item at the top of the context menu")

        # 2. The new context-menu item: checks now, and installs then relaunches when there
        #    is a new version.
        if not _has_all(body, (r"우클릭\s*메뉴에", r'"업데이트 확인…"', r"생겼")):
            problems.append('say the context menu gained "업데이트 확인…"')
        if not _has_all(body, (r"누르면", r"바로\s*확인", r"내려받아", r"설치", r"다시\s*켭")):
            problems.append(
                "say pressing it checks now and, if there is a new version, downloads, installs "
                "and relaunches")

        # 3. Straight to the latest release, and the estimator untouched so no recalibration.
        if not _has_all(body, (r"중간\s*버전", r"거치지\s*않", r"최신\s*릴리즈", r"바로")):
            problems.append("say the update goes straight to the latest release, skipping nothing")
        if not _has_all(
            body,
            (r"한도", r"(?:그대로|바뀌지|변경\s*(?:없|되지 않))",
             r"다시\s*보정", r"(?:필요\s*(?:가\s*)?없|불필요)"),
        ):
            problems.append("say recalibration is unnecessary because the limits are unchanged")

        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v023_cadence_matches_update_check_sec(self):
        """The notes' "1시간" must be the interval the source actually uses.

        Pinning only the constant would let the sentence drift; pinning only the sentence
        would let the constant drift.  This reads both and compares them in seconds.
        """
        intervals = _literal_assignments(APP_SOURCE, "UPDATE_CHECK_SEC")
        self.assertEqual(
            len(intervals), 1, "claude_pet.py must define exactly one literal UPDATE_CHECK_SEC")
        interval = intervals[0]
        self.assertIs(type(interval), int)
        self.assertEqual(
            interval, EXPECTED_UPDATE_CHECK_SEC,
            f"UPDATE_CHECK_SEC is {interval!r}; the published v0.23 notes promise an hourly check")

        hours = re.findall(r"(\d+(?:\.\d+)?)\s*시간", self.body)
        self.assertEqual(
            len(hours), 1, f"expected exactly one duration in hours in the notes, got {hours!r}")
        self.assertEqual(
            float(hours[0]) * 3600, float(interval),
            f"notes say {hours[0]}시간 but UPDATE_CHECK_SEC is {interval} seconds")
        stray = re.findall(r"\d+(?:\.\d+)?\s*(?:분|초)", self.body)
        self.assertEqual(stray, [], f"durations in the notes not backed by UPDATE_CHECK_SEC: {stray!r}")

    def test_v023_menu_label_is_quoted_exactly_as_the_korean_source_string(self):
        """The quoted menu item must be TR["ko"]["menu_check_update"] minus its arrow glyph.

        The notes tell the user to look for this label in the context menu, so a
        rewording on either side leaves the instruction pointing at nothing.
        """
        table = _tr_table()
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_check_update")]
        self.assertEqual(missing, [], f"menu_check_update missing from locales: {missing}")
        label = table["ko"]["menu_check_update"]
        self.assertEqual(label, KO_CHECK_LABEL, "the published v0.23 notes quote this context-menu label")
        glyph, _, quoted = label.partition(" ")
        self.assertEqual(glyph, "⬆︎", "the label leads with the update arrow, as menu_update does")
        self.assertIn(
            f'"{quoted}"', self.body,
            f"the v0.23 notes must quote the Korean menu label {quoted!r} verbatim")

    def test_v023_no_launch_check_is_backed_by_run_gui(self):
        """"앱을 켤 때 하지 않고": run_gui's top level must stamp the cooldown origin and
        must not start, schedule or call the update check itself."""
        run_gui = _module_def(APP_SOURCE, "run_gui")
        top_level = [s for s in run_gui.body
                     if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        mentions = [ast.unparse(s) for s in top_level
                    if any(isinstance(n, ast.Name) and n.id in
                           ("_run_update_check", "poll_github_update", "check_github_update")
                           for n in ast.walk(s))]
        self.assertEqual(mentions, [], "run_gui's top level still reaches the update check at launch")
        stamps = [s for s in top_level
                  if isinstance(s, ast.Assign) and ast.unparse(s) == "_upd_cache['t'] = time.time()"]
        self.assertEqual(len(stamps), 1, "run_gui must stamp _upd_cache['t'] once at launch")

    def test_v023_direct_to_latest_is_backed_by_the_single_endpoint(self):
        """"중간 버전을 거치지 않고 … 최신 릴리즈로 바로": check_github_update must read
        GitHub's /releases/latest and nothing else, and compare that one tag against
        APP_VERSION."""
        check = _module_def(APP_SOURCE, "check_github_update")
        source = ast.unparse(check)
        endpoints = re.findall(r"https://api\.github\.com/[^\s'\"]*", source)
        self.assertEqual(
            endpoints, [f"https://api.github.com/repos/{{GITHUB_REPO}}/releases/latest"],
            f"check_github_update must read exactly the latest-release endpoint; got {endpoints!r}")
        self.assertIn("_ver_tuple(tag) <= _ver_tuple(APP_VERSION)", source,
                      "the one tag is compared against APP_VERSION — no version walk")
        self.assertNotIn("/releases'", source)
        self.assertNotIn("/releases\"", source)


class ReleaseNotesPolicyTests(unittest.TestCase):
    def test_claude_has_durable_user_facing_release_note_policy(self):
        text = CLAUDE_POLICY.read_text(encoding="utf-8")
        step2 = "2. **Add a section to the top of the changelog"
        step3 = "3. **Build, sign, notarize.**"
        self.assertEqual(text.count(step2), 1)
        self.assertEqual(text.count(step3), 1)
        policy = text.split(step2, 1)[1].split(step3, 1)[0]

        required = {
            "exactly 3 top-level bullets": (r"(?:정확히\s*)?3\s*개", r"(?:최상위|상위)", r"불릿"),
            "450-character budget": (r"450", r"(?:글자|문자)"),
            "no nested bullets": (r"(?:중첩|하위)", r"불릿", r"(?:없|금지|쓰지)"),
            "one or two sentences per bullet": (r"1\s*[~-]\s*2", r"문장"),
            "user action": (r"사용자", r"(?:행동|조치|해야\s*할\s*일)"),
            "auditable quantities": (r"수치|정량", r"AGENTS\.md", r"§\s*5", r"(?:재현|감사|검증|근거)"),
            "no implementation internals": (r"구현", r"식별자", r"해시", r"테스트", r"(?:매트릭스|개수|수)"),
            "published entries stay frozen": (r"published", r"Do not rewrite or drop"),
        }
        missing = [
            label for label, patterns in required.items() if not _has_all(policy, patterns)
        ]
        self.assertEqual(
            missing,
            [],
            "CLAUDE.md release-note policy is missing: " + ", ".join(missing),
        )

    def test_claude_states_the_hourly_never_at_launch_cadence(self):
        """CLAUDE.md's release-procedure sentence about the poll cadence must match
        UPDATE_CHECK_SEC and the no-launch-check behaviour the published v0.23 notes
        describe."""
        text = CLAUDE_POLICY.read_text(encoding="utf-8")
        self.assertIn("polls the repo's latest release tag every hour", text)
        self.assertIn("never at launch", text)
        self.assertNotIn("every 6 hours", text)


class PublishedV024NotesContractTests(unittest.TestCase):
    """The published v0.24 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v0.24 release's ``StagedV024NotesFormatTests`` with its assertions and
    method names unchanged — only its status moved from staged to published when the
    ``v0.24`` tag and GitHub release went out on 2026-09-12.  The format gate still says
    what CLAUDE.md step 2 says: exactly three top-level bullets, no nesting, at most 450
    normalized characters, 1-2 Korean sentences per bullet, and none of the forbidden
    token classes.  Every checkable claim in it stays tied to the source: the threshold
    percentages to ``summary_value_kind``, the marker glyphs to ``SUMMARY_SPIKE`` /
    ``SUMMARY_APPROX`` / the ⚠ suffix, the font to ``SUMMARY_FONT_FILE`` and the bundled
    files, the nested layout to ``discover_pets``, the toggle wording to
    ``TR["ko"]["menu_toggle"]``, and the colour roles to ``draw_summary_pill``'s docstring
    — so neither side can drift alone.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.24**", "**v0.23**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v024_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.24 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.24 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.24 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v024_thresholds_and_markers_match_the_source(self):
        quoted = {int(value) for value in re.findall(r"(\d+)%", self.body)}
        function = _module_def(APP_SOURCE, "summary_value_kind")
        compared = {
            node.value for node in ast.walk(function)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        }
        self.assertEqual(quoted, compared,
                         f"notes quote {sorted(quoted)}% but summary_value_kind compares against {sorted(compared)}")
        spike = _one_literal_string(APP_SOURCE, "SUMMARY_SPIKE")
        approx = _one_literal_string(APP_SOURCE, "SUMMARY_APPROX")
        for glyph in (spike, approx, "⚠"):
            self.assertIn(glyph, self.body, f"the note no longer mentions the {glyph!r} marker the pill draws")
        gui_strings = _strings([_module_def(APP_SOURCE, "run_gui")])
        self.assertTrue(any("⚠" in s for s in gui_strings), "run_gui no longer draws the ⚠ suffix the note promises")

    def test_v024_font_claim_is_backed_by_the_bundled_files_and_both_packagers(self):
        """"Pretendard (OFL)를 앱에 내장": the constant, the two files under fonts/, the
        OFL text, and both packagers (setup.py resources, build_app.sh staging) must all
        name the same font.  Rivals: the note names a font the app does not load; the
        file is missing or a symlink; the licence file is not the OFL; one packager
        ships the font and the other does not."""
        self.assertIn("Pretendard", self.body)
        self.assertIn("OFL", self.body)
        font_file = _one_literal_string(APP_SOURCE, "SUMMARY_FONT_FILE")
        self.assertTrue(font_file.startswith("Pretendard"),
                        f"SUMMARY_FONT_FILE is {font_file!r}; the note promises Pretendard")
        font_path = FONT_DIR / font_file
        self.assertTrue(font_path.is_file(), f"fonts/{font_file} missing — the note promises it is bundled")
        self.assertFalse(font_path.is_symlink(), f"fonts/{font_file} must be a regular file")
        licence = FONT_DIR / "LICENSE-Pretendard.txt"
        self.assertTrue(licence.is_file(), "fonts/LICENSE-Pretendard.txt missing")
        self.assertIn("SIL Open Font License", licence.read_text(encoding="utf-8"),
                      "the bundled licence text is not the OFL the note names")
        setup_text = SETUP.read_text(encoding="utf-8")
        self.assertRegex(setup_text, r'"resources"\s*:\s*\[[^\]]*"fonts"',
                         "setup.py must ship fonts/ as a bundle resource")
        self.assertIn(font_file, BUILD_SCRIPT.read_text(encoding="utf-8"),
                      "build_app.sh must stage the same font file the app loads")

    def test_v024_nested_layout_claim_is_backed_by_discover_pets(self):
        """"pets/이름/이름/ 도 인식": discover_pets must resolve every candidate through
        the module-level _nested_pet_dir exactly once.  Rivals: the note promises a
        layout no code resolves; the helper exists but discover_pets never calls it."""
        self.assertIn("pets/이름/이름/", self.body)
        _module_def(APP_SOURCE, "_nested_pet_dir")
        discover = _module_def(APP_SOURCE, "discover_pets")
        calls = [n for n in ast.walk(discover)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_nested_pet_dir"]
        self.assertEqual(len(calls), 1,
                         "discover_pets must resolve each candidate through _nested_pet_dir exactly once")

    def test_v024_windows_beta_wording_is_present_and_marked_unsigned(self):
        """The Windows beta is built on the Windows branch, not by this tree, so only the
        wording is pinned: the asset name users will look for, and that it is unsigned.
        The macOS updater's asset table must not gain it — a Windows zip is never an
        install candidate for a Mac."""
        self.assertIn("claude-pet-win.zip", self.body)
        self.assertRegex(self.body, r"claude-pet-win\.zip[^)]*서명 없음",
                         "the Windows beta must be described as unsigned beside its file name")
        tables = _literal_assignments(APP_SOURCE, "UPDATE_ASSET_NAMES")
        self.assertEqual(len(tables), 1, "claude_pet.py must define exactly one literal UPDATE_ASSET_NAMES")
        allowed = {str(name).lower() for names in tables[0].values() for name in names}
        self.assertNotIn("claude-pet-win.zip", allowed,
                         "the macOS updater must not treat the Windows zip as an install candidate")

    def test_v024_toggle_wording_matches_every_locale_and_locales_share_one_key_set(self):
        """"접기/펴기 … 그대로": the notes reuse the Korean toggle wording, so
        TR["ko"]["menu_toggle"] must still contain it; every locale's toggle must name
        the pill it now toggles (v0.24 replaced the gauges); and the four locales must
        carry identical key sets so no locale can lose a menu item silently.  Rivals: the
        pre-v0.24 gauge wording in any locale; a locale missing menu_toggle; a Korean
        label reworded away from the notes."""
        table = _tr_table()
        self.assertEqual(sorted(table), ["en", "es", "ja", "ko"])
        key_sets = {lang: set(keys) for lang, keys in table.items()}
        for lang, keys in key_sets.items():
            with self.subTest(lang=lang):
                self.assertEqual(
                    keys, key_sets["en"],
                    f"TR[{lang!r}] keys differ from en: missing {sorted(key_sets['en'] - keys)}, "
                    f"extra {sorted(keys - key_sets['en'])}")
        for lang, word in PILL_WORDS.items():
            with self.subTest(lang=lang):
                label = table[lang].get("menu_toggle", "")
                self.assertIn(word.casefold(), label.casefold(),
                              f"TR[{lang!r}]['menu_toggle'] = {label!r} no longer names the pill")
        self.assertIn(KO_TOGGLE_WORDING, self.body, "the notes must say the toggle is unchanged")
        self.assertIn(KO_TOGGLE_WORDING, table["ko"]["menu_toggle"],
                      "the Korean toggle label must keep the wording the notes reuse")

    def test_v024_pill_docstring_and_notes_agree_on_label_and_value_colours(self):
        """"수치는 출처 … 라벨은 흰색이다가": the values carry the source colour and the
        labels the remaining-budget colour.  draw_summary_pill's docstring must say the
        same (its pre-final wording had the two roles swapped); the behaviour itself is
        gated in tests/test_summary_pill.py."""
        self.assertRegex(self.body, r"수치는\s*출처")
        self.assertRegex(self.body, r"라벨은\s*흰색")
        draw = _nested_function(_module_def(APP_SOURCE, "run_gui"), "draw_summary_pill")
        doc = ast.get_docstring(draw) or ""
        self.assertIn("라벨(잔여량 색)", doc, "draw_summary_pill's docstring must give labels the remaining colour")
        self.assertIn("수치(출처 색)", doc, "draw_summary_pill's docstring must give values the source colour")
        self.assertNotIn("라벨(출처 색)", doc, "swapped roles in draw_summary_pill's docstring")
        self.assertNotIn("수치(잔여량 색)", doc, "swapped roles in draw_summary_pill's docstring")


class StagedV025NotesFormatTests(unittest.TestCase):
    """The unpublished v0.25 section, held to CLAUDE.md's release-note format rule and to
    the source it describes.

    The section is staged text until the tag is pushed, so correcting it is ordinary
    work; the format gate only says what CLAUDE.md step 2 says: exactly three top-level
    bullets, no nesting, at most 450 normalized characters, 1-2 Korean sentences per
    bullet, and none of the forbidden token classes.  Every checkable claim in it is then
    tied to the source: the quoted "로그인 시 자동 실행" to ``TR["ko"]["menu_autostart"]``;
    "시스템 설정 … 에서 끄면 메뉴에도 꺼진 것으로 보입니다" to the menu reading the OS
    registration through ``autostart_read_state`` (which asks the service for ``status()``)
    and to no autostart function writing the config or ``RUNTIME``; "토큰을 갱신하거나 서버
    응답이 잠깐 실패해도 재시작 없이" to the token cache's rotation and re-validation
    paths, the forced re-read on 401/403, the ``suspect`` flag, and a failure-retry
    interval shorter than the success cache; and the quoted "완전 삭제…" with "내 펫 폴더는
    남깁니다" to ``TR["ko"]["menu_uninstall"]`` and to ``UNINSTALL_PATHS`` naming the config
    and the cache directory but never the user's pet home.  The Windows halves of those
    sentences are built on the Windows branch and are not checkable here.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.25**", "**v0.24**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v025_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.25 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.25 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.25 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string(self):
        """"우클릭 메뉴에 "로그인 시 자동 실행"이 생겼습니다": the quoted label must be
        TR["ko"]["menu_autostart"] verbatim, every locale must carry the item and its
        companion strings, and the context menu built in run_gui must actually add the
        item.  Rivals: a Korean label reworded on either side; a locale missing the key
        (the v0.24 key-set test catches a missing key, not a wrong Korean label); a menu
        that never adds the item although the strings exist."""
        table = _tr_table()
        for key in ("menu_autostart", "autostart_title", "autostart_approval",
                    "autostart_open_settings", "autostart_fail", "autostart_unavailable"):
            missing = [lang for lang in ("en", "ko", "ja", "es") if not table.get(lang, {}).get(key)]
            self.assertEqual(missing, [], f"{key} missing from locales: {missing}")
        label = table["ko"]["menu_autostart"]
        self.assertEqual(label, KO_AUTOSTART_LABEL, "the v0.25 notes quote this context-menu label")
        self.assertRegex(self.body, r"우클릭\s*메뉴에\s*\"" + re.escape(label) + r"\"",
                         f"the v0.25 notes must quote the Korean menu label {label!r} verbatim")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        menu_keys = {n.args[0].value for n in _calls_to(run_gui, "t")
                     if n.args and isinstance(n.args[0], ast.Constant)}
        self.assertIn("menu_autostart", menu_keys, "run_gui never puts menu_autostart in the menu")
        self.assertIn("autostart_unavailable", menu_keys,
                      "run_gui must retitle the item with autostart_unavailable when there is no service")

    def test_v025_autostart_state_is_read_from_the_os_and_never_stored(self):
        """"시스템 설정 … 에서 끄면 메뉴에도 꺼진 것으로 보입니다": the checkmark must come
        from the OS registration, read afresh, never from a stored flag.  So
        autostart_read_state asks the service for status(); autostart_toggle re-reads
        the state through autostart_read_state after registering (a register can land in
        "approval"); none of the four autostart functions touches RUNTIME, the config or
        a config writer; and run_gui reaches autostart_read_state through the
        "autostart_read" hook the menu consults.  Rivals: a stored flag that goes stale
        the moment System Settings turns the item off; a toggle that assumes "registered
        means on"; a menu that reads a config key instead of the hook."""
        read_state = _module_def(APP_SOURCE, "autostart_read_state")
        self.assertEqual(len(_method_calls(read_state, "status")), 1,
                         "autostart_read_state must ask the service for status() exactly once")
        toggle = _module_def(APP_SOURCE, "autostart_toggle")
        self.assertEqual(len(_calls_to(toggle, "autostart_read_state")), 2,
                         "autostart_toggle must read the state before and re-read it after the call")
        self.assertTrue(_method_calls(toggle, "registerAndReturnError_"),
                        "autostart_toggle never registers")
        self.assertTrue(_method_calls(toggle, "unregisterAndReturnError_"),
                        "autostart_toggle never unregisters")
        forbidden = {"RUNTIME", "cfg", "CONFIG_PATH", "save_config", "merge_config_updates",
                     "load_config", "USER_PET_HOME"}
        for name in ("autostart_state", "autostart_read_state", "autostart_toggle",
                     "uninstall_autostart"):
            with self.subTest(function=name):
                touched = sorted(_names(_module_def(APP_SOURCE, name)) & forbidden)
                self.assertEqual(touched, [], f"{name} must not touch the config or RUNTIME: {touched}")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        self.assertIn("autostart_read", _strings([run_gui]),
                      "run_gui must expose the autostart_read hook the menu consults")
        self.assertTrue(_calls_to(run_gui, "autostart_read_state"),
                        "run_gui's hook must read the state through autostart_read_state")

    def test_v025_exact_mode_recovery_is_backed_by_the_token_cache(self):
        """"토큰을 갱신하거나 서버 응답이 잠깐 실패해도 재시작 없이 정확 모드로": three
        mechanisms, each pinned to a name the behavioural gates in
        tests/test_oauth_token_cache.py exercise.  Rotation: _read_oauth_token compares
        the credentials file's signature (_credentials_sig) and re-validates a suspect
        token (_revalidate_oauth_token).  Rejection: _fetch_oauth_usage re-reads the token
        with force=True on 401/403 and raises the suspect flag on every other failure.
        Transient failure: OAUTH_FAIL_RETRY_SEC is a literal shorter than OAUTH_CACHE_SEC
        and fetch_exact_usage consults it, so a failed fetch is not cached for the full
        success interval.  Rivals: a cache with no rotation signal; a fetch that gives up
        on a 5xx without marking the token suspect; a failure cached for the full 180 s
        (the v0.24 behaviour the note says is gone); a retry constant no shorter than the
        cache, which changes nothing."""
        self.assertRegex(self.body, r"재시작\s*없이")
        self.assertRegex(self.body, r"정확\s*모드")
        self.assertRegex(self.body, r"추정\s*모드")
        read = _module_def(APP_SOURCE, "_read_oauth_token")
        self.assertTrue(_calls_to(read, "_credentials_sig"),
                        "_read_oauth_token must compare the credentials file signature (rotation signal)")
        self.assertTrue(_calls_to(read, "_revalidate_oauth_token"),
                        "_read_oauth_token must re-validate a suspect token")
        fetch = _module_def(APP_SOURCE, "_fetch_oauth_usage")
        forced = [c for c in _calls_to(fetch, "_read_oauth_token")
                  if any(k.arg == "force" and isinstance(k.value, ast.Constant) and k.value.value is True
                         for k in c.keywords)]
        self.assertEqual(len(forced), 1, "_fetch_oauth_usage must re-read the token once with force=True")
        fetch_src = ast.unparse(fetch)
        self.assertIn("c['suspect'] = True", fetch_src, "a non-auth failure must mark the token suspect")
        self.assertIn("c['suspect'] = False", fetch_src, "a success must clear the suspect flag")
        retry = _one_literal_int(APP_SOURCE, "OAUTH_FAIL_RETRY_SEC")
        cache = _one_literal_int(APP_SOURCE, "OAUTH_CACHE_SEC")
        self.assertGreater(retry, 0)
        self.assertLess(retry, cache,
                        f"OAUTH_FAIL_RETRY_SEC={retry} must be shorter than OAUTH_CACHE_SEC={cache}")
        exact = _module_def(APP_SOURCE, "fetch_exact_usage")
        self.assertIn("OAUTH_FAIL_RETRY_SEC", _names(exact),
                      "fetch_exact_usage must cache a failure for OAUTH_FAIL_RETRY_SEC, not the full interval")

    def test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it(self):
        """""완전 삭제…"는 설정과 캐시까지 지우고 내 펫 폴더는 남깁니다": the quoted label
        must be TR["ko"]["menu_uninstall"] verbatim; UNINSTALL_PATHS must name the config
        (CONFIG_PATH) and the cache directory (UPDATE_LOCK_DIR) and must not name the
        user's pet home, by constant or by path text; and do_uninstall must delete
        through uninstall_targets rather than reaching for USER_PET_HOME itself.  Rivals:
        a reworded label on either side; the pet home added to the list "to clean up
        completely"; the cache directory dropped so the sentence over-promises; a direct
        rmtree of the pet home outside the list."""
        table = _tr_table()
        label = table["ko"]["menu_uninstall"]
        self.assertEqual(label, KO_UNINSTALL_LABEL, "the v0.25 notes quote this context-menu label")
        self.assertIn(f'"{label}"', self.body,
                      f"the v0.25 notes must quote the Korean menu label {label!r} verbatim")
        self.assertRegex(self.body, r"펫\s*폴더는\s*남깁니다")
        paths = _module_assignment(APP_SOURCE, "UNINSTALL_PATHS")
        self.assertIsInstance(paths.value, ast.Tuple, "UNINSTALL_PATHS must stay a tuple literal")
        names = _names(paths.value)
        self.assertIn("CONFIG_PATH", names, "UNINSTALL_PATHS must delete the settings file")
        self.assertIn("UPDATE_LOCK_DIR", names, "UNINSTALL_PATHS must delete the cache directory")
        self.assertNotIn("USER_PET_HOME", names, "UNINSTALL_PATHS must never name the user's pet home")
        for text in _strings([paths.value]):
            self.assertNotIn(".claude_pet/", text, f"UNINSTALL_PATHS reaches into the pet home: {text!r}")
            self.assertNotEqual(text.rstrip("/"), "~/.claude_pet",
                                "UNINSTALL_PATHS must never name the user's pet home")
        do_uninstall = _module_def(APP_SOURCE, "do_uninstall")
        self.assertTrue(_calls_to(do_uninstall, "uninstall_targets"),
                        "do_uninstall must delete through uninstall_targets")
        self.assertNotIn("USER_PET_HOME", _names(do_uninstall),
                         "do_uninstall must not reach for the pet home directly")
        targets = _module_def(APP_SOURCE, "uninstall_targets")
        self.assertIn("UNINSTALL_PATHS", _names(targets), "uninstall_targets must read UNINSTALL_PATHS")


class SummaryMemoContractTests(unittest.TestCase):
    def test_summary_memo_key_covers_mode_language_and_onboarding(self):
        """roam_summary_text memoises per input; its key must include everything the
        text depends on that a refresh does not replace: the mode, the language ``t()``
        reads from the module-level ``L``, the onboarding state ``roam_summary`` turns
        into a status line, the two data objects and the auth-error flag.  The
        behavioural gate is in tests/test_companion_motion.py; this pins the shape so a
        dropped element is named rather than found as stale text."""
        text_fn = _nested_function(_module_def(APP_SOURCE, "run_gui"), "roam_summary_text")
        keys = [n for n in ast.walk(text_fn)
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "key"]
        self.assertEqual(len(keys), 1, "roam_summary_text must build exactly one memo key")
        self.assertIsInstance(keys[0].value, ast.Tuple, "the memo key must be a tuple literal")
        elements = [ast.unparse(e) for e in keys[0].value.elts]
        for needed in ("RUNTIME['mode']", "L['lang']", "state.get('onboard')",
                       "id(stats)", "id(oauth)", "bool(OAUTH_STATUS.get('auth_error'))"):
            self.assertIn(needed, elements, f"memo key {elements!r} lacks {needed}")
        self.assertIn("_summary_memo['key'] == key", ast.unparse(text_fn),
                      "the memo must be consulted by comparing the whole key")


if __name__ == "__main__":
    unittest.main()
