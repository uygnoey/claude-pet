"""Static release-preparation gates for v0.21 and v0.22.

The filename is kept from the v0.21 release: this module now gates **both** the
unpublished v0.21 changelog section (v0.21 was never tagged, so it ships inside v0.22)
and the new v0.22 section, plus the version constants and source pins of the v0.22
release commit.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse tracked repository
text and bytes.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.22 application/verifier bytes change.

The v0.21 and v0.22 note gates implement the CLAUDE.md format rule separately rather
than sharing one structural helper.  That duplication is deliberate: the v0.21 section
is a finished gate whose assertions must keep running exactly as written, and a shared
helper edited for v0.22 would silently change what v0.21 discriminates.
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

# Derived from RELEASE_NOTES.md SHA-256
# 8e7161612d27d02463a9cf4d7b43292e3486031f7c2d7f6c6a364734e475b6e5.
# Pinning from the published heading through EOF lets v0.21 be prepended while making
# every byte users already received for v0.20 and older releases immutable.
PUBLISHED_V020_AND_OLDER_SHA256 = (
    "6d73456411eac4d7b2aa9b7556bb185fc43f84417ce8e91969dd8b91caf52ee1"
)


# CLAUDE.md release-note step 2 forbids these in a user-facing entry.  One home, used by
# both the v0.21 and the v0.22 scan: a second copy would let one version drift.
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


class VersionAndPinContractTests(unittest.TestCase):
    def test_v022_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.22"]:
            problems.append(f"APP_VERSION must be one literal '0.22', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.22" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.22")
        for stale in ("0.21", "0.20"):
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


class ReleaseNotesContractTests(unittest.TestCase):
    def test_v021_notes_are_concise_user_facing_and_preserve_published_bytes(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.20**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.20 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V020_AND_OLDER_SHA256,
            "published v0.20-and-older bytes were rewritten or dropped",
        )

        text = raw.decode("utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["0.22", "0.21"],
            "v0.21 was never tagged, so it must stay directly under the new v0.22 "
            f"heading; got {headings[:2]!r}",
        )

        v021_heading = "**v0.21**"
        self.assertEqual(text.count(v021_heading), 1, "expected exactly one v0.21 heading")
        self.assertLess(text.index(v021_heading), text.index("**v0.20**"))
        block = text.split(v021_heading, 1)[1].split("**v0.20**", 1)[0]
        visible = re.sub(r"<!--.*?-->", "", block, flags=re.S).strip()

        lines = visible.splitlines()
        top_level = [line for line in lines if re.match(r"^-\s+\S", line)]
        nested = [line for line in lines if re.match(r"^\s+-\s+\S", line)]
        self.assertEqual(top_level, [line for line in lines if line.startswith("- ")])
        self.assertEqual(len(top_level), 3, "v0.21 must have exactly 3 top-level bullets")
        self.assertEqual(nested, [], "v0.21 must not contain nested bullets")

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
        self.assertEqual(preamble, [], "v0.21 body must consist only of its 3 bullets")
        self.assertEqual(len(bullets), 3)

        normalized_body = " ".join(visible.split())
        self.assertLessEqual(
            len(normalized_body),
            450,
            f"v0.21 Korean body is {len(normalized_body)} Unicode characters; max is 450",
        )
        for index, bullet in enumerate(bullets, 1):
            with self.subTest(bullet=index):
                self.assertRegex(bullet, r"[가-힣]", "each release bullet must be Korean")
                self.assertLessEqual(
                    len(_sentences(bullet)), 2, "each bullet must have at most 2 sentences"
                )

        problems: list[str] = []
        body = "\n".join(bullets)

        if not _has_all(
            body,
            (
                r"(?:3\s*개|세\s*개)",
                r"게이지",
                r"세션",
                r"주간",
                r"(?:모델|opus)",
                r"%",
                r"(?:보정|역산|맞추)",
            ),
        ):
            problems.append("describe all 3 session/weekly/model gauges calibrated from displayed %")

        example_ok = any(
            _has_all(
                bullet,
                (
                    r"(?:2\s*M|200\s*만)",
                    r"25\s*%",
                    r"(?:8\s*M|800\s*만)",
                    r"한도",
                ),
            )
            for bullet in bullets
        )
        if not example_ok:
            problems.append("include the auditable example: 2M used at 25% backsolves to an 8M limit")

        if not _has_all(body, (r"빈\s*칸|빈칸", r"기존", r"(?:유지|보존)")):
            problems.append("say blank inputs preserve existing limits")
        if not _has_all(
            body,
            (r"(?:직접|절대)", r"M", r"고급", r"현재", r"%", r"(?:우선|먼저)"),
        ):
            problems.append("say direct M inputs are Advanced/current-shown and % wins")
        if not _has_all(
            body,
            (r"0\s*%", r"빈\s*칸|빈칸", r"사용", r"다시", r"(?:시도|저장)"),
        ):
            problems.append("give the actionable 0% choice: leave blank or use then retry")
        if not _has_all(
            body,
            (
                r"정확\s*모드",
                r"서버",
                r"게이지",
                r"급증",
                r"(?:보정한|보정된)",
                r"추정",
                r"한도",
            ),
        ):
            problems.append("distinguish server exact-mode gauges from calibrated-estimate spike detection")
        if not _has_all(
            body,
            (r"추정", r"(?:그대로|바뀌지|변경\s*(?:없|되지 않))", r"다시\s*보정", r"(?:필요\s*없|불필요)"),
        ):
            problems.append("say recalibration is unnecessary because the estimator is unchanged")
        if not _has_all(body, (r"(?:4\s*개|네\s*개)", r"(?:언어|로케일)")):
            problems.append("state the equivalent 4-locale coverage")

        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


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


def _loaded_names(nodes) -> set[str]:
    out: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                out.add(child.id)
    return out


def _branch_on(func: ast.AST, marker: str) -> ast.If:
    """The `if` inside func whose *test* mentions the literal marker."""
    for child in ast.walk(func):
        if isinstance(child, ast.If) and marker in _strings([child.test]):
            return child
    raise AssertionError(f"no branch keyed on {marker!r} in {getattr(func, 'name', func)!r}")


class V022ReleaseNotesContractTests(unittest.TestCase):
    """The unpublished v0.22 section, held to CLAUDE.md's release-note format rule."""

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.22**", "**v0.21**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v022_notes_follow_the_three_bullet_450_character_format(self):
        self.assertEqual(
            len(self.top_level), 3,
            f"v0.22 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        self.assertEqual(self.nested, [], "v0.22 must not contain nested bullets")
        self.assertEqual(len(self.bullets), 3)

        normalized_body = " ".join(self.visible.split())
        self.assertLessEqual(
            len(normalized_body), 450,
            f"v0.22 Korean body is {len(normalized_body)} Unicode characters; max is 450")

        for index, bullet in enumerate(self.bullets, 1):
            with self.subTest(bullet=index):
                self.assertRegex(bullet, r"[가-힣]", "each release bullet must be Korean")
                self.assertLessEqual(
                    len(_sentences(bullet)), 2, "each bullet must have at most 2 sentences")

    def test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal(self):
        problems: list[str] = []
        body = self.body

        if not _has_all(
            body,
            (r"마우스", r"다가", r"\d+\s*초", r"바라보", r"(?:돌아옵|제자리)"),
        ):
            problems.append("say the pet approaches while the mouse moves, looks, and returns")
        if not _has_all(body, (r"커서", r"(?:걸어가지 않|지나가지 않|넘어가지 않)")):
            problems.append("say it never walks over the cursor")
        if not _has_all(
            body,
            (r"(?:잡|끌)", r"메뉴", r"설정", r"(?:멈|섭|정지)"),
        ):
            problems.append("say grabbing or opening the menu/settings stops it in place")

        if not _has_all(body, (r"(?:걷|걸을)", r"게이지", r"접")):
            problems.append("say the gauges fold while it walks")
        if not _has_all(body, (r"세션", r"주간", r"%", r"요약", r"한\s*줄")):
            problems.append("say the arrival shows a one-line session/weekly % summary")
        if not _has_all(body, (r"≈", r"(?:로그\s*)?추정")):
            problems.append("say ≈ marks log-estimated values")
        if not _has_all(body, (r"⌄", r"전체", r"펼")):
            problems.append("say the ⌄ button expands the full gauges")
        if not _has_all(body, (r"돌아", r"접")):
            problems.append("say the previous folded/expanded choice comes back on return")

        if not _has_all(body, (r"우클릭", r"화면\s*돌아다니기", r"(?:끄|켜)")):
            problems.append('name the context-menu item "화면 돌아다니기" and that it toggles')
        if not _has_all(body, (r"동작\s*줄이기", r"(?:움직이지\s*않|멈)")):
            problems.append("say macOS Reduce Motion suppresses the movement")
        if not _has_all(body, (r"v0\.21", r"보정", r"(?:함께|같이|포함|들어)")):
            problems.append("say v0.21's % calibration ships inside this version")

        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v022_look_duration_matches_the_source_default(self):
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
            f'ROAM_DEFAULTS["look_s"] is {look_s!r}; the v0.22 notes promise 6 seconds')

        stated = re.findall(r"(\d+(?:\.\d+)?)\s*초", self.body)
        self.assertEqual(
            len(stated), 1, f"expected exactly one duration in seconds in the notes, got {stated!r}")
        self.assertEqual(
            float(stated[0]), float(look_s),
            f'notes say {stated[0]}초 but ROAM_DEFAULTS["look_s"] is {look_s!r}')

    def test_v022_look_duration_governs_the_approach_watch(self):
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


class V022SourceBackedClaimTests(unittest.TestCase):
    """Every remaining named thing in the v0.22 notes, read back out of the source."""

    def test_approx_mark_is_applied_to_estimates_and_withheld_from_server_rows(self):
        self.assertEqual(
            _one_literal_string(APP_SOURCE, "SUMMARY_APPROX"), "≈",
            "the notes promise ≈ in front of log-estimated values")
        line = _module_def(APP_SOURCE, "roam_summary_line")
        estimate = _branch_on(line, "estimate")
        exact = _branch_on(line, "exact")
        self.assertIn(
            "SUMMARY_APPROX", _loaded_names(estimate.body),
            "the estimate branch must prefix SUMMARY_APPROX")
        self.assertNotIn(
            "SUMMARY_APPROX", _loaded_names(exact.body),
            "server (exact) rows must not be marked as estimates")

    def test_roam_menu_item_exists_in_every_locale_with_the_documented_korean_label(self):
        tables = _literal_assignments(APP_SOURCE, "TR")
        self.assertEqual(len(tables), 1, "claude_pet.py must define exactly one literal TR")
        table = tables[0]
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_roam")]
        self.assertEqual(missing, [], f"menu_roam missing from locales: {missing}")
        self.assertEqual(
            table["ko"]["menu_roam"], "화면 돌아다니기",
            "the v0.22 notes name this exact context-menu label")

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


if __name__ == "__main__":
    unittest.main()
