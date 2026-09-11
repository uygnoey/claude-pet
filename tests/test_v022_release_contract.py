"""Static release-preparation gates for v0.22.

v0.21 is published (tag on origin, GitHub release with that entry as its body), so
everything from the ``**v0.21**`` heading to the end of ``RELEASE_NOTES.md`` is frozen
text and is pinned here byte for byte.  The single unpublished section above it is
``**v0.22**``; this module holds that section to CLAUDE.md's release-note format rule
and holds the version constants and source pins of the v0.22 release commit together.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse tracked repository
text and bytes.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v0.22 application/verifier bytes change.

Claims in the notes are cross-checked against the source rather than merely spelled out
here, because a note and a constant can drift apart in either direction: the "10~20초"
follow range is compared against ``ROAM_DEFAULTS["follow_min_s"]`` / ``["follow_max_s"]``
and against the branch of ``Roamer._plan`` that draws the episode length from them; the
quoted context-menu label is compared against ``TR["ko"]["menu_roam"]``; "only a real
drag is remembered" is compared against the one place that persists ``x``/``y``.
Pinning only one side of any of these pairs would let the other side move silently.
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

# Pinning from the newest *published* heading through EOF lets the unpublished v0.22
# section be rewritten freely while making every byte users already received for v0.21
# and older releases immutable.  Computed from the v0.21 release commit's blob and
# confirmed identical in the working tree before the v0.22 section was added above it.
PUBLISHED_V021_AND_OLDER_SHA256 = (
    "323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75"
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


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_def(path: Path, name: str, parent: str | None = None) -> ast.AST:
    """The module-level (or class-level, when parent is given) definition called name."""
    body = _module_tree(path).body
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


def _any_def(path: Path, name: str) -> ast.AST:
    """The single definition called name anywhere in the module, however nested.

    The AppKit view class is built inside ``run_gui()``, so its methods are not
    reachable through ``_module_def``.
    """
    found = [
        n for n in ast.walk(_module_tree(path))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    ]
    if len(found) != 1:
        raise AssertionError(f"{path.name} must define exactly one {name}; found {len(found)}")
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


def _position_saves(node: ast.AST) -> list[ast.Call]:
    """Calls ``merge_config_updates({... "x": ..., "y": ...})`` beneath node."""
    saves: list[ast.Call] = []
    for child in ast.walk(node):
        if not (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                and child.func.id == "merge_config_updates"):
            continue
        for arg in child.args:
            if isinstance(arg, ast.Dict):
                keys = {k.value for k in arg.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                if {"x", "y"} <= keys:
                    saves.append(child)
    return saves


class VersionAndPinContractTests(unittest.TestCase):
    def test_v022_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["0.22"]:
            problems.append(f"APP_VERSION must be one literal '0.22', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 0.22" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 0.22")
        for stale in ("0.21", "0.20", "0.23"):
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
    def test_published_v021_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.21**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.21 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V021_AND_OLDER_SHA256,
            "published v0.21-and-older bytes were rewritten or dropped",
        )

    def test_v022_is_the_only_unpublished_heading_and_sits_directly_above_v021(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["0.22", "0.21"],
            "the unpublished v0.22 section must sit directly above the published v0.21 "
            f"heading, with nothing newer above it; got {headings[:2]!r}",
        )
        self.assertEqual(headings.count("0.22"), 1, "v0.22 heading must appear once")


class ReleaseNotesContractTests(unittest.TestCase):
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
                count = len(_sentences(bullet))
                self.assertGreaterEqual(count, 1, "each bullet must be at least one sentence")
                self.assertLessEqual(count, 2, "each bullet must have at most 2 sentences")

    def test_v022_notes_state_the_user_facing_behaviour_and_nothing_internal(self):
        problems: list[str] = []
        body = self.body

        # 1. Free wandering: anywhere on screen, rests on arrival, no return home, and
        #    only a real drag is remembered as the new home.
        if not _has_all(
            body,
            (r"산책", r"화면", r"(?:아무\s*데|어디든|아무\s*곳)", r"도착", r"(?:쉽니다|쉰다|쉬)"),
        ):
            problems.append(
                "say the pet wanders anywhere on the screen and rests where it arrives")
        if not _has_all(body, (r"(?:원래\s*자리|제자리|집)", r"돌아(?:오|가)지\s*않")):
            problems.append("say it does not return to where it started")
        if not _has_all(body, (r"드래그", r"(?:기억|저장)")):
            problems.append("say only a direct drag makes the new spot remembered")

        # 2. Following the pointer for a bounded random episode, then looking and resting
        #    where it stopped; grabbing it or opening the menu stops it in place.
        if not _has_all(
            body,
            (r"마우스", r"\d+\s*[~\-–]\s*\d+\s*초", r"(?:거리를\s*두|여백)", r"따라"),
        ):
            problems.append(
                "say the pet follows the moving mouse at a distance for a bounded range of seconds")
        if not _has_all(body, (r"바라보", r"(?:멈춘|그)\s*자리", r"(?:쉽니다|쉰다|쉬)")):
            problems.append("say it looks at you afterwards and rests where it stopped")
        if not _has_all(body, (r"(?:잡|끌)", r"메뉴", r"(?:멈|정지)")):
            problems.append("say grabbing it or opening the menu stops it in place")

        # 3. Multi-display jumps, the single switch that turns all of it off, and the
        #    estimator being untouched so no recalibration is needed.
        if not _has_all(body, (r"모니터", r"(?:두\s*대|둘|여러)", r"다른\s*화면", r"(?:점프|건너)")):
            problems.append("say it jumps to another display when there is more than one")
        if not _has_all(
            body,
            (r"우클릭", r"메뉴", r"(?:끄|끌)", r"따라다니", r"점프", r"(?:함께|같이|도)\s*(?:멈|중단)"),
        ):
            problems.append(
                "say switching the context-menu item off also stops following and jumping")
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

    def test_v022_follow_range_matches_the_source_defaults(self):
        """The notes' "10~20초" must be the follow bounds the source actually uses.

        Pinning only the source values would let the sentence drift; pinning only the
        sentence would let the constants drift.  This reads both and compares them.
        """
        defaults = _literal_assignments(APP_SOURCE, "ROAM_DEFAULTS")
        self.assertEqual(
            len(defaults), 1, "claude_pet.py must define exactly one literal ROAM_DEFAULTS")
        self.assertIsInstance(defaults[0], dict)
        bounds = []
        for key in ("follow_min_s", "follow_max_s"):
            value = defaults[0].get(key)
            self.assertIsInstance(value, (int, float), f'ROAM_DEFAULTS["{key}"] missing')
            self.assertNotIsInstance(value, bool)
            bounds.append(float(value))
        self.assertEqual(
            bounds, [10.0, 20.0],
            f'ROAM_DEFAULTS follow bounds are {bounds!r}; the v0.22 notes promise 10~20 seconds')
        self.assertLess(bounds[0], bounds[1])

        ranges = re.findall(r"(\d+(?:\.\d+)?)\s*[~\-–]\s*(\d+(?:\.\d+)?)\s*초", self.body)
        self.assertEqual(
            len(ranges), 1,
            f"expected exactly one duration range in seconds in the notes, got {ranges!r}")
        self.assertEqual(
            [float(ranges[0][0]), float(ranges[0][1])], bounds,
            f'notes say {ranges[0][0]}~{ranges[0][1]}초 but ROAM_DEFAULTS follow bounds are {bounds!r}')
        stray = [d for d in re.findall(r"(\d+(?:\.\d+)?)\s*초", self.body)
                 if float(d) != bounds[1]]
        self.assertEqual(stray, [], f"durations in the notes not backed by the follow range: {stray!r}")

    def test_v022_follow_episode_is_drawn_from_those_defaults_and_ends_in_a_look(self):
        """The follow branch of Roamer._plan must set the deadline from follow_min/max_s,
        and Roamer._watch must give follow the same review look as approach."""
        plan = _module_def(APP_SOURCE, "_plan", parent="Roamer")
        branch = _branch_on(plan, "follow_p")
        chosen = _strings(branch.body)
        for key in ("follow_min_s", "follow_max_s", "follow_cooldown_s"):
            self.assertIn(
                key, chosen,
                f'the follow branch of Roamer._plan must read ROAM_DEFAULTS["{key}"]')
        self.assertIn("follow", chosen, "the follow branch must enter the follow phase")
        self.assertNotIn(
            "follow_min_s", _strings(branch.orelse) | _strings(plan.body) - chosen,
            "only the follow branch draws the follow episode length")

        watch = _module_def(APP_SOURCE, "_watch", parent="Roamer")
        look = _branch_on(watch, "follow")
        self.assertIn("approach", _strings([look.test]),
                      "approach and follow share the review look in Roamer._watch")
        self.assertIn("look_s", _strings(look.body),
                      'the follow/approach branch of Roamer._watch must use ROAM_DEFAULTS["look_s"]')
        self.assertNotIn("look_s", _strings(look.orelse),
                         "the wander pause must not be the review look")

    def test_v022_menu_label_is_quoted_exactly_as_the_korean_source_string(self):
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
            "the v0.22 notes quote this exact context-menu label")
        self.assertIn(
            f'"{label}"', self.body,
            f"the v0.22 notes must quote the Korean menu label {label!r} verbatim")

    def test_the_roam_switch_gates_the_whole_roamer_and_reduce_motion_is_honoured(self):
        """"Off" must halt following and jumping too, which holds only if one switch
        gates the entire roamer rather than the wander alone."""
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "accessibilityDisplayShouldReduceMotion", source,
            "macOS Reduce Motion is honoured")
        runtime = re.search(r"(?ms)^RUNTIME = \{.*?^\}", source)
        self.assertIsNotNone(runtime, "RUNTIME dict not found")
        roam_default = re.search(
            r'"roam":\s*os\.environ\.get\("CLAUDE_PET_ROAM",\s*"1"\)\s*!=\s*"0"',
            runtime.group(0))
        self.assertIsNotNone(
            roam_default,
            'RUNTIME["roam"] must default on via CLAUDE_PET_ROAM, as the menu item implies')
        gate = re.search(
            r'enabled\s*=\s*bool\(RUNTIME\.get\("roam"\)\)\s*and\s*not\s*state\["reduce_motion"\]',
            source)
        self.assertIsNotNone(
            gate, 'the roamer must be enabled only by RUNTIME["roam"] and not Reduce Motion')
        defaults = _literal_assignments(APP_SOURCE, "ROAM_DEFAULTS")[0]
        self.assertIs(defaults.get("jump_enabled"), True,
                      "cross-display jumps must be on by default, as the notes describe")
        self.assertIs(defaults.get("wander_enabled"), True,
                      "wandering must be on by default, as the notes describe")

    def test_only_a_real_drag_persists_the_position(self):
        """"옮겨 둔 자리는 직접 드래그했을 때만 기억합니다": the one place that saves x/y is
        mouseUp_, under its `if moved:` branch — never the roamer's own arrivals."""
        saves = _position_saves(_module_tree(APP_SOURCE))
        self.assertEqual(len(saves), 1, f"expected exactly one x/y save, found {len(saves)}")
        mouse_up = _any_def(APP_SOURCE, "mouseUp_")
        moved_branches = [
            n for n in ast.walk(mouse_up)
            if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "moved"
        ]
        self.assertTrue(moved_branches, "mouseUp_ must branch on `moved`")
        inside = [c for b in moved_branches for c in _position_saves(ast.Module(body=b.body, type_ignores=[]))]
        self.assertEqual(len(inside), 1, "the x/y save must sit under mouseUp_'s `if moved:`")
        roamer = _module_def(APP_SOURCE, "Roamer")
        self.assertEqual(_position_saves(roamer), [], "Roamer must never persist x/y itself")


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
