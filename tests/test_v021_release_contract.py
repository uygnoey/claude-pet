"""Static release-preparation gates owned by the v0.21 Verifier.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse tracked repository
text and bytes.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.21 application/verifier bytes change.
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
    def test_v021_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.21"]:
            problems.append(f"APP_VERSION must be one literal '0.21', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.21" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.21")
        if "--expect-version 0.20" in verifier_text:
            problems.append("verify_release_artifact.py still advertises --expect-version 0.20")

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
            headings[0],
            "0.21",
            f"newest release heading must be v0.21, got v{headings[0]}",
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

        forbidden = {
            "hash": r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{7,64}(?![0-9A-Fa-f])",
            "source path": r"(?:^|\s)[^\s`]*(?:\.py|\.sh|tests?/)[^\s`]*",
            "line reference": r"(?:\bline\s*\d+|\d+\s*행)",
            "internal identifier": r"(?:\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b|\b(?:APP_VERSION|RUNTIME|NSPanel)\b|\b[A-Za-z_]\w*\()",
            "test matrix/count prose": r"(?:테스트|매트릭스|fixture|unittest|\b(?:GREEN|RED|PASS|FAIL)\b|\d+\s*(?:tests?|테스트))",
            "unsupported magnitude/frequency": r"(?:대폭|훨씬|엄청|매우|대부분|대다수|많이|자주|종종|드물게|가끔|항상|완전히|상당히)",
        }
        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in forbidden.items():
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


if __name__ == "__main__":
    unittest.main()
