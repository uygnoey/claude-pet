"""Static release-preparation gates for v0.23.

v0.22 is published (tag on origin, GitHub release with that entry as its body), so
everything from the ``**v0.22**`` heading to the end of ``RELEASE_NOTES.md`` is frozen
text and is pinned here byte for byte.  The single unpublished section above it is
``**v0.23**``; this module holds that section to CLAUDE.md's release-note format rule
and holds the version constants and source pins of the v0.23 release commit together.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse tracked repository
text and bytes.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.23 application/verifier bytes change.

Claims in the notes are cross-checked against the source rather than merely spelled out
here, because a note and a constant can drift apart in either direction: the "1시간"
cadence is compared against ``UPDATE_CHECK_SEC``; the quoted context-menu label is
compared against ``TR["ko"]["menu_check_update"]``; "no check at launch" is compared
against ``run_gui``'s top level; "straight to the latest release" is compared against
the one endpoint ``check_github_update`` reads.  Pinning only one side of any of these
pairs would let the other side move silently.  The behavioural gates for the same change
are in tests/test_update_check_schedule.py; this module only ties the prose to them.
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
RELEASE_NOTES = REPO / "RELEASE_NOTES.md"
CLAUDE_POLICY = REPO / "CLAUDE.md"
MANUAL_TEST = REPO / "tests" / "test_manual_update_transaction.py"
UPLOAD_TEST = REPO / "tests" / "test_upload_artifact_gate.py"

# Pinning from the newest *published* heading through EOF lets the unpublished v0.23
# section be rewritten freely while making every byte users already received for v0.22
# and older releases immutable.  Computed from the v0.22 release commit's blob
# (HEAD 6d47df5e, `git show HEAD:RELEASE_NOTES.md`) and confirmed identical in the
# working tree after the v0.23 section was added above it (2026-09-11).
PUBLISHED_V022_AND_OLDER_SHA256 = (
    "6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239"
)

# The cadence the v0.23 notes promise, and the Korean label they tell the user to find.
EXPECTED_UPDATE_CHECK_SEC = 3600
KO_CHECK_LABEL = "⬆︎ 업데이트 확인…"


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


def _strings(nodes) -> set[str]:
    out: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.add(child.value)
    return out


class VersionAndPinContractTests(unittest.TestCase):
    def test_v023_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.23"]:
            problems.append(f"APP_VERSION must be one literal '0.23', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.23" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.23")
        for stale in ("0.22", "0.21", "0.24"):
            if f"--expect-version {stale}" in verifier_text:
                problems.append(
                    f"verify_release_artifact.py still advertises --expect-version {stale}"
                )

        expected_pins = (
            (MANUAL_TEST, "REVIEWED_APP_SOURCE_SHA256", _sha256(APP_SOURCE)),
            (UPLOAD_TEST, "REVIEWED_APP_SOURCE_SHA256", _sha256(APP_SOURCE)),
            (
                UPLOAD_TEST,
                "REVIEWED_VERIFIER_SHA256",
                _sha256(RELEASE_VERIFIER),
            ),
        )
        for path, name, actual_sha in expected_pins:
            try:
                pinned_sha = _one_literal_string(path, name)
            except AssertionError as exc:
                problems.append(str(exc))
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", pinned_sha):
                problems.append(f"{path.name}:{name} is not a literal lowercase SHA-256")
            elif pinned_sha != actual_sha:
                problems.append(
                    f"{path.name}:{name} pins {pinned_sha}, final source is {actual_sha}"
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

    def test_v023_is_the_only_unpublished_heading_and_sits_directly_above_v022(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["0.23", "0.22"],
            "the unpublished v0.23 section must sit directly above the published v0.22 "
            f"heading, with nothing newer above it; got {headings[:2]!r}",
        )
        self.assertEqual(headings.count("0.23"), 1, "v0.23 heading must appear once")


class ReleaseNotesContractTests(unittest.TestCase):
    """The unpublished v0.23 section, held to CLAUDE.md's release-note format rule."""

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
            f"UPDATE_CHECK_SEC is {interval!r}; the v0.23 notes promise an hourly check")

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
        tables = _literal_assignments(APP_SOURCE, "TR")
        self.assertEqual(len(tables), 1, "claude_pet.py must define exactly one literal TR")
        table = tables[0]
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_check_update")]
        self.assertEqual(missing, [], f"menu_check_update missing from locales: {missing}")
        label = table["ko"]["menu_check_update"]
        self.assertEqual(label, KO_CHECK_LABEL, "the v0.23 notes quote this context-menu label")
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
        UPDATE_CHECK_SEC and the no-launch-check behaviour the v0.23 notes describe."""
        text = CLAUDE_POLICY.read_text(encoding="utf-8")
        self.assertIn("polls the repo's latest release tag every hour", text)
        self.assertIn("never at launch", text)
        self.assertNotIn("every 6 hours", text)


if __name__ == "__main__":
    unittest.main()
