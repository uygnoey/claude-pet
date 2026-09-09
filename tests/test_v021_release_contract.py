"""Static release-preparation gates for v0.21.

The release that was prepared as v0.22 was renumbered to v0.21 by the user's own
decision: v0.21 had never been tagged or published, so the work that was staged under
two headings now ships as one v0.21 entry, and the user additionally asked for a much
shorter entry.  This module therefore gates a **single** unpublished v0.21 changelog
section plus the version constants and source pins of the v0.21 release commit.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse tracked repository
text and bytes.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.21 application/verifier bytes change.

Two claims in the notes are cross-checked against the source rather than merely spelled
out here, because a note and a constant can drift apart in either direction: the "6초"
look duration is compared against ``ROAM_DEFAULTS["look_s"]``, and the quoted
context-menu label is compared against ``TR["ko"]["menu_roam"]``.  Pinning only one side
of either pair would let the other side move silently.
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

# Pinning from the published heading through EOF lets the unpublished v0.21 section be
# rewritten freely while making every byte users already received for v0.20 and older
# releases immutable.  This value is unchanged by the v0.22 -> v0.21 renumbering, which
# is the point: renumbering an unpublished entry must not disturb published bytes.
PUBLISHED_V020_AND_OLDER_SHA256 = (
    "6d73456411eac4d7b2aa9b7556bb185fc43f84417ce8e91969dd8b91caf52ee1"
)


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


def _module_def(path: Path, name: str, parent: str | None = None) -> ast.AST:
    """The module-level (or class-level, when parent is given) definition called name."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = tree.body
    if parent is not None:
        holders = [n for n in body if isinstance(n, ast.ClassDef) and n.name == parent]
        if len(holders) != 1:
            raise AssertionError(f"{path.name} must define exactly one class {parent}")
        body = holders[0].body
    found = [
        n for n in body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.name == name
    ]
    if len(found) != 1:
        raise AssertionError(
            f"{path.name} must define exactly one {name}"
            + (f" in {parent}" if parent else "")
        )
    return found[0]


def _strings(nodes) -> set[str]:
    out: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.add(child.value)
    return out


def _branch_on(func: ast.AST, marker: str) -> ast.If:
    """The `if` inside func whose *test* mentions the literal marker."""
    for child in ast.walk(func):
        if isinstance(child, ast.If) and marker in _strings([child.test]):
            return child
    raise AssertionError(f"no branch keyed on {marker!r} in {getattr(func, 'name', func)!r}")


class VersionAndPinContractTests(unittest.TestCase):
    def test_v021_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.21"]:
            problems.append(f"APP_VERSION must be one literal '0.21', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.21" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.21")
        for stale in ("0.22", "0.20"):
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
    def test_published_v020_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.20**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.20 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V020_AND_OLDER_SHA256,
            "published v0.20-and-older bytes were rewritten or dropped",
        )

    def test_v021_is_the_newest_heading_and_v022_is_gone(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["0.21", "0.20"],
            "the release was renumbered to v0.21, so v0.21 must sit directly above the "
            f"published v0.20 heading; got {headings[:2]!r}",
        )
        self.assertNotIn(
            "0.22", headings,
            "the v0.22 heading must be gone: v0.22 was never published and the release "
            "was renumbered to v0.21",
        )


class ReleaseNotesContractTests(unittest.TestCase):
    """The unpublished v0.21 section, held to CLAUDE.md's release-note format rule."""

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.21**", "**v0.20**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v021_notes_follow_the_three_bullet_450_character_format(self):
        self.assertEqual(
            len(self.top_level), 3,
            f"v0.21 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        self.assertEqual(self.nested, [], "v0.21 must not contain nested bullets")
        self.assertEqual(len(self.bullets), 3)

        normalized_body = " ".join(self.visible.split())
        self.assertLessEqual(
            len(normalized_body), 450,
            f"v0.21 Korean body is {len(normalized_body)} Unicode characters; max is 450")

        for index, bullet in enumerate(self.bullets, 1):
            with self.subTest(bullet=index):
                self.assertRegex(bullet, r"[가-힣]", "each release bullet must be Korean")
                self.assertLessEqual(
                    len(_sentences(bullet)), 2, "each bullet must have at most 2 sentences")

    def test_v021_notes_state_the_user_facing_behaviour_and_nothing_internal(self):
        problems: list[str] = []
        body = self.body

        # 1. Percentage calibration of the three limits.
        if not _has_all(
            body,
            (r"세션", r"주간", r"(?:모델|opus)", r"한도", r"%", r"(?:맞추|맞춥|보정|역산)"),
        ):
            problems.append(
                "say the session/weekly/model limits are set from the % Claude shows")
        if not _has_all(body, (r"빈\s*칸|빈칸", r"기존", r"(?:유지|보존)")):
            problems.append("say blank inputs preserve existing limits")
        # ``\bM\b`` would not fire here: Korean particles are word characters, so
        # "M을" carries no word boundary after the M.  Bound on Latin letters instead.
        if not _has_all(body, (r"(?<![A-Za-z])M(?![A-Za-z])", r"%", r"(?:우선|먼저)")):
            problems.append("say % wins when both % and an absolute M limit are given")

        # 2. The roaming pet.
        if not _has_all(
            body,
            (r"마우스", r"다가", r"\d+\s*초", r"(?:돌아옵|제자리)"),
        ):
            problems.append(
                "say the pet approaches while the mouse moves, looks, and returns")
        if not _has_all(body, (r"(?:잡|끌)", r"메뉴", r"(?:멈|정지)")):
            problems.append("say grabbing it or opening the menu stops it in place")
        if not _has_all(body, (r"(?:걷|걸을)", r"게이지", r"접")):
            problems.append("say the gauges fold while it walks")
        if not _has_all(body, (r"도착", r"세션", r"주간", r"%", r"한\s*줄")):
            problems.append("say the arrival shows a one-line session/weekly % summary")

        # 3. Turning it off, and the estimator being unchanged.
        if not _has_all(body, (r"우클릭", r"메뉴", r"(?:끄|끌|켜)")):
            problems.append("say the context menu toggles it off")
        if not _has_all(body, (r"동작\s*줄이기", r"(?:움직이지\s*않|멈)")):
            problems.append("say macOS Reduce Motion suppresses the movement")
        if not _has_all(
            body,
            (r"추정", r"(?:그대로|바뀌지|변경\s*(?:없|되지 않))",
             r"다시\s*보정", r"(?:필요\s*(?:가\s*)?없|불필요)"),
        ):
            problems.append("say recalibration is unnecessary because the estimator is unchanged")

        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v021_look_duration_matches_the_source_default(self):
        """The notes' "6초" must be the look constant the source actually uses.

        Pinning only the source value would let the sentence drift; pinning only the
        sentence would let the constant drift.  This reads both and compares them.
        """
        defaults = _literal_assignments(APP_SOURCE, "ROAM_DEFAULTS")
        self.assertEqual(
            len(defaults), 1, "claude_pet.py must define exactly one literal ROAM_DEFAULTS")
        self.assertIsInstance(defaults[0], dict)
        look_s = defaults[0].get("look_s")
        self.assertIsInstance(look_s, (int, float))
        self.assertNotIsInstance(look_s, bool)
        self.assertEqual(
            float(look_s), 6.0,
            f'ROAM_DEFAULTS["look_s"] is {look_s!r}; the v0.21 notes promise 6 seconds')

        stated = re.findall(r"(\d+(?:\.\d+)?)\s*초", self.body)
        self.assertEqual(
            len(stated), 1,
            f"expected exactly one duration in seconds in the notes, got {stated!r}")
        self.assertEqual(
            float(stated[0]), float(look_s),
            f'notes say {stated[0]}초 but ROAM_DEFAULTS["look_s"] is {look_s!r}')

    def test_v021_look_duration_governs_the_approach_watch(self):
        """look_s must be the approach branch's dwell, not the wander pause."""
        watch = _module_def(APP_SOURCE, "_watch", parent="Roamer")
        branch = _branch_on(watch, "approach")
        self.assertIn(
            "look_s", _strings(branch.body),
            'the "approach" branch of Roamer._watch must use ROAM_DEFAULTS["look_s"]')
        self.assertNotIn(
            "look_s", _strings(branch.orelse),
            "the non-approach (wander) pause must not be the 6-second look")
        self.assertIn("wander_pause_s", _strings(branch.orelse))

    def test_v021_menu_label_is_quoted_exactly_as_the_korean_source_string(self):
        """The quoted menu item must be TR["ko"]["menu_roam"], read out of the source.

        The notes tell the user to look for this label in the context menu, so a
        rewording on either side leaves the instruction pointing at nothing.
        """
        tables = _literal_assignments(APP_SOURCE, "TR")
        self.assertEqual(len(tables), 1, "claude_pet.py must define exactly one literal TR")
        table = tables[0]
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_roam")]
        self.assertEqual(missing, [], f"menu_roam missing from locales: {missing}")
        label = table["ko"]["menu_roam"]
        self.assertEqual(
            label, "화면 돌아다니기",
            "the v0.21 notes quote this exact context-menu label")
        self.assertIn(
            label, self.body,
            f"the v0.21 notes must quote the Korean menu label {label!r} verbatim")

    def test_reduce_motion_and_the_roam_default_are_where_the_notes_say(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "accessibilityDisplayShouldReduceMotion", source,
            "the notes promise macOS Reduce Motion is honoured")
        runtime = re.search(r"(?ms)^RUNTIME = \{.*?^\}", source)
        self.assertIsNotNone(runtime, "RUNTIME dict not found")
        roam_default = re.search(
            r'"roam":\s*os\.environ\.get\("CLAUDE_PET_ROAM",\s*"1"\)\s*!=\s*"0"',
            runtime.group(0))
        self.assertIsNotNone(
            roam_default,
            'RUNTIME["roam"] must default on via CLAUDE_PET_ROAM, as the menu item implies')


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


if __name__ == "__main__":
    unittest.main()
