"""The instruments, not the code: do the updater tests' injections still bite?

    python3 -m unittest tests.test_mutation_instruments -v   # from the repo root

WHAT THIS IS FOR
----------------
The rollback and restore tests do not observe a failure - they *cause* one, by
substituting a literal out of the generated shell script:

    command = command.replace("sleep 1.5", ":")
    command = command.replace(line, "false", 1)

`str.replace` cannot fail. If the script's wording changes so a needle no longer
occurs, the call returns the string unchanged, the test then runs the
**unmutated** script, the transaction succeeds exactly as it should, and the
assertion "the app was restored" goes green - having never broken anything. The
test does not weaken gradually; it stops testing entirely, silently, while
reporting success.

That is the same shape as every vacuous assertion found on this release, and it
sits in the tests that guard the one operation that can destroy a user's
installed app. This module is the tripwire: it reads the injection sites out of
the test sources and checks each needle still occurs in the real generated
script.

HOW IT STAYS TRUE
-----------------
The needles are parsed from the test files with `ast` rather than copied here.
A hardcoded list would be a second instrument needing its own guard - it would
go stale the moment someone edits a test, and staleness in a checker looks
exactly like health.

SCOPE, STATED SO ITS SILENCE IS NOT MISREAD
-------------------------------------------
Only `.replace()` calls whose first argument is a **string literal** are
checkable this way. Sites that pass a variable (a needle computed from an
earlier match) are outside this module - it reports nothing about them, and its
passing must not be read as covering them.

A needle absent from the script here does not automatically mean the test is
inert: a test could chain replacements, so a needle might only exist after an
earlier one has been applied. No current site does that. If one is added, this
module fails and the failure message says so - which is the right outcome,
because that arrangement needs a human to confirm it is deliberate.

This module reads other agents' test files. It never modifies them, imports
them, or executes them.
"""

import ast
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import claude_pet

REPO = Path(__file__).resolve().parent.parent

# The real path production would use. Generating a replacement script asks for
# the lock path, and an earlier revision of `_update_lock_path` created this
# directory as a side effect of *computing* it - which is how an updater test
# run put a directory and a lock file in the user's real home at 10:11 today.
# The function is pure now and reads the constant at call time, but this module
# does not rely on that: it swaps the constant, and checks the real path is
# untouched either way. A guard that only works while the bug is absent is not
# a guard.
REAL_LOCK_DIR = Path(os.path.expanduser("~/Library/Caches/me.yeongyu.claudepet"))

# The suites whose tests inject failures by rewriting the generated script.
SOURCES = ("test_updater.py", "test_updater_adversarial.py")

# Receivers that hold generated shell text. Substitutions on anything else
# (paths, labels, report strings) are ordinary string handling and are not
# instruments, so including them would produce false alarms.
SCRIPT_RECEIVER_HINTS = ("command", "script", "uninstall", "sh")


LAUNCH_DEFINITION = "LAUNCH=open"
LAUNCH_PRIMARY = '$LAUNCH "$APP"'
LAUNCH_RESTORE = '( $LAUNCH "$RESTORED" )'


def assert_launch_grammar(script):
    """Pin the launch seam before any test is allowed to rewrite it."""
    expected = {
        LAUNCH_DEFINITION: 1,
        LAUNCH_PRIMARY: 1,
        LAUNCH_RESTORE: 1,
    }
    for literal, count in expected.items():
        actual = script.count(literal)
        if actual != count:
            raise AssertionError(
                f"replacement script has {actual} copies of {literal!r}; "
                f"expected exactly {count}")
    if script.count("$LAUNCH") != 2:
        raise AssertionError("replacement script must consume $LAUNCH twice")


def assert_uninstall_cleanup_contract(script, app, app_id, lock_dir, lock_id):
    """The corpus must be production's identity-bound, app-first cleanup."""
    import shlex
    app_line = "discard %s %s" % (shlex.quote(str(app)),
                                  shlex.quote(str(app_id)))
    lock_line = "discard %s %s" % (shlex.quote(str(lock_dir)),
                                   shlex.quote(str(lock_id)))
    for line in (app_line, lock_line):
        if script.count(line) != 1:
            raise AssertionError(
                f"uninstall cleanup does not carry exact identity line {line!r}")
    if script.index(app_line) >= script.index(lock_line):
        raise AssertionError(
            "uninstall cleanup must discard APP before its lock root")
    for marker in ("sleep 2", "/usr/bin/stat -f %d,%i",
                   '/bin/rm -rf "$1"'):
        if marker not in script:
            raise AssertionError(
                f"uninstall cleanup is missing production marker {marker!r}")


def generated_scripts(root, lock_dir):
    """Every shell text the updater emits, in both of its shapes.

    The staged and unstaged forms differ in the middle - one re-copies with
    `ditto`, the other reuses a stage Python already checked - so a needle
    present in only one of them is still a live needle.

    `root` holds real temp-only APP/WORK/STAGE objects so the current constructor
    receives identities from its caller instead of inventing them. `lock_dir`
    replaces `UPDATE_LOCK_DIR` for the duration. Generating a script asks for
    the lock path, and this module must never be the reason something appears
    under the user's real cache directory.
    """
    root = Path(root).resolve()
    app = root / "installed" / "ClaudePet.app"
    new = root / "work" / "ClaudePet.app"
    wd = root / "work"
    staged = root / ".claudepet-new-staged.app"
    uninstall_lock = root / "uninstall-lock-root"
    app.mkdir(parents=True)
    new.mkdir(parents=True)
    staged.mkdir()
    uninstall_lock.mkdir(mode=0o700)
    app_id = claude_pet._path_ident_str(str(app))
    work_id = claude_pet._path_ident_str(str(wd))
    stage_id = claude_pet._path_ident_str(str(staged))
    lock_id = claude_pet._path_ident_str(str(uninstall_lock))
    if not app_id or not work_id or not stage_id or not lock_id:
        raise AssertionError("fixture identities could not be read")

    def replacement(**kwargs):
        script = claude_pet._update_replace_script(
            str(app), str(new), str(wd), app_id=app_id, work_id=work_id,
            **kwargs)
        assert_launch_grammar(script)
        return script

    uninstall = claude_pet._uninstall_cleanup_script(
        str(app), app_id, str(uninstall_lock), lock_id)
    assert_uninstall_cleanup_contract(
        uninstall, app, app_id, uninstall_lock, lock_id)

    with mock.patch.object(claude_pet, "UPDATE_LOCK_DIR", str(lock_dir)):
        return {
            "replace script (unstaged)":
                replacement(),
            "replace script (staged)":
                replacement(staged=str(staged), stage_id=stage_id),
            "replace script (with inherited lock fd)":
                replacement(lock_fd=7),
            "uninstall cleanup": uninstall,
        }


# What each generated text must contain to be worth searching at all. The
# The cleanup helper is shorter than a replacement transaction, so a single
# length threshold across the corpus would either miss an emptied replacement
# script or reject a healthy cleanup script. Keep the floors per text.
SANITY = {
    "replace script (unstaged)":
        (500, ("$APP", "$STAGE", "APPID=", "WORKID=")),
    "replace script (staged)":
        (500, ("$APP", "$STAGE", "APPID=", "WORKID=", "STAGEID=")),
    "replace script (with inherited lock fd)":
        (500, ("$APP", "$STAGE", "APPID=", "WORKID=")),
    "uninstall cleanup":
        (150, ('/bin/rm -rf "$1"', "sleep 2", "discard ")),
}


def replace_sites(path):
    """(lineno, needle) for every `<script>.replace("literal", ...)` call."""
    tree = ast.parse(path.read_text(), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "replace"):
            continue
        if not node.args:
            continue
        receiver = (ast.unparse(fn.value) or "").lower()
        if not any(h in receiver for h in SCRIPT_RECEIVER_HINTS):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append((node.lineno, arg.value))
    return out


def dynamic_sites(path):
    """The same calls, but with a non-literal needle - out of scope, counted."""
    tree = ast.parse(path.read_text(), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "replace"):
            continue
        if not node.args:
            continue
        receiver = (ast.unparse(fn.value) or "").lower()
        if not any(h in receiver for h in SCRIPT_RECEIVER_HINTS):
            continue
        arg = node.args[0]
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            out.append((node.lineno, ast.unparse(arg)))
    return out


class _Generated(unittest.TestCase):
    """Generates the scripts with the lock path redirected, and proves it."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="instruments-"))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.lock_dir = self.td / "locks"
        self.before = self._real_lock_state()
        self.scripts = generated_scripts(self.td, self.lock_dir)
        self.addCleanup(self.assertRealLockDirUntouched)

    @staticmethod
    def _real_lock_state():
        try:
            st = REAL_LOCK_DIR.lstat()
            names = sorted(p.name for p in REAL_LOCK_DIR.iterdir())
            return (True, st.st_mtime_ns, names)
        except OSError:
            return (False, None, None)

    def assertRealLockDirUntouched(self):
        self.assertEqual(
            self._real_lock_state(), self.before,
            f"{REAL_LOCK_DIR} changed while this test ran - generating a "
            "script reached the user's real cache directory")


class LockPathIsolationTests(_Generated):
    def test_the_redirect_actually_took_effect(self):
        """Otherwise the isolation is theatre and the check above is vacuous.

        If the patch missed - wrong attribute name, a value frozen at import
        time - every script would still carry the real path while
        `assertRealLockDirUntouched` quietly passed, because merely reading a
        path changes nothing. So assert the substitution is visible in the
        output, not just that nothing broke.
        """
        scripts = [t for label, t in self.scripts.items()
                   if label.startswith("replace script")]
        self.assertTrue(scripts)
        for text in scripts:
            self.assertIn(str(self.lock_dir), text,
                          "the generated script does not carry the redirected "
                          "lock directory, so UPDATE_LOCK_DIR was not honoured")
            self.assertNotIn(str(REAL_LOCK_DIR), text,
                             "the generated script still names the user's real "
                             "cache directory")
            self.assertIn(str(self.td), text,
                          "the constructor was not bound to the temp fixture")
            self.assertNotIn("/Applications/ClaudePet.app", text,
                             "the generated corpus names the live app path")

    def test_generating_a_script_creates_nothing(self):
        """`_update_lock_path` must be pure: asking is not making."""
        self.assertFalse(
            self.lock_dir.exists(),
            "generating a replacement script created the lock directory - "
            "computing a path must not make it. With the real constant in "
            "place this would have landed in the user's home.")


class InjectionNeedlesStillMatchTests(_Generated):

    def test_the_generator_produces_something_to_search(self):
        """Discrimination: an empty script would make every check below vacuous.

        If `_update_replace_script` ever returned "" - a refactor behind a flag,
        a signature change swallowed by a default - every needle would be
        reported missing, or worse, a `substring in ""` check written the other
        way round would pass everything. Pin the corpus first.
        """
        self.assertEqual(set(self.scripts), set(SANITY),
                         "a generated text has no sanity rule, so it would be "
                         "searched without ever being shown to be searchable")
        for label, text in self.scripts.items():
            floor, markers = SANITY[label]
            with self.subTest(script=label):
                self.assertGreater(len(text), floor,
                                   f"{label} is implausibly short")
                for marker in markers:
                    self.assertIn(marker, text,
                                  f"{label} does not look like itself")

    def test_every_literal_needle_still_occurs_in_the_generated_script(self):
        checked = 0
        for name in SOURCES:
            path = REPO / "tests" / name
            if not path.exists():
                self.skipTest(f"{name} is not present")
            for lineno, needle in replace_sites(path):
                checked += 1
                with self.subTest(source=name, line=lineno, needle=needle):
                    found = [label for label, text in self.scripts.items()
                             if needle in text]
                    self.assertTrue(
                        found,
                        f"{name}:{lineno} injects its failure by replacing "
                        f"{needle!r}, which occurs in none of the generated "
                        "scripts. `str.replace` does not raise, so that test "
                        "now runs the UNMUTATED script and passes without "
                        "having broken anything. (If the site deliberately "
                        "chains onto an earlier replacement, this module "
                        "cannot see it and the site needs its own check.)")
        self.assertGreater(
            checked, 0,
            "no injection sites were found at all - the parser stopped "
            "matching, so this module is the broken instrument now")

    def test_the_needles_are_not_so_generic_that_they_hit_everywhere(self):
        """A needle matching many places replaces more than the test intends.

        `command.replace(x, y)` with no count replaces *every* occurrence, so a
        needle that appears three times silently rewrites three lines. That is
        not a failure of the script, it is a failure of the injection to be the
        surgical edit its test assumes.
        """
        for name in SOURCES:
            path = REPO / "tests" / name
            if not path.exists():
                self.skipTest(f"{name} is not present")
            for lineno, needle in replace_sites(path):
                for label, text in self.scripts.items():
                    n = text.count(needle)
                    if n <= 1:
                        continue
                    with self.subTest(source=name, line=lineno, script=label):
                        self.assertLessEqual(
                            n, 1,
                            f"{name}:{lineno} replaces {needle!r}, which "
                            f"occurs {n} times in {label} - the injection is "
                            "editing more of the transaction than the test "
                            "describes")


class ScopeIsVisibleTests(unittest.TestCase):
    """What this module cannot see must not be invisible."""

    def test_dynamic_needle_sites_are_reported_rather_than_silently_skipped(self):
        unverifiable = []
        for name in SOURCES:
            path = REPO / "tests" / name
            if path.exists():
                unverifiable += [(name, ln, src)
                                 for ln, src in dynamic_sites(path)]
        # Not a failure - a computed needle can be perfectly sound. The point
        # is that the number is stated somewhere a reader will meet it, rather
        # than this module's green result implying full coverage.
        self.assertIsInstance(unverifiable, list)
        if unverifiable:
            print("\n[instruments] %d injection site(s) use a computed needle "
                  "and are NOT checked here:" % len(unverifiable))
            for name, ln, src in unverifiable:
                print(f"  {name}:{ln}  replace({src}, ...)")


# ── 2026-09-20: 같은 계열의 사고가 업데이터 **밖에서** 났다 ─────────────────────
#
# 이 모듈은 업데이터가 **생성하는 셸 스크립트**에 대한 바늘만 지켜 왔다(SOURCES 참조).
# 그 범위 밖에서 정확히 같은 일이 일어났다: tests/test_settings_and_install.py 가
# setup.py 의 `"resources": ["frames", ".claude_pet", "fonts"],` 를 리터럴 바늘로 적어
# 두었는데, 이번 릴리즈에서 목록에 "logos" 가 붙자 바늘이 어긋났다. `str.replace` 는
# 실패하지 않으므로 변이체가 원본과 같아졌고, 그 테스트는 소리 없이 아무것도 검사하지
# 않게 됐다. 그 자리에 우연히 있던 `assertNotEqual` 가드 하나가 아니었으면 초록인 채로
# 지나갔을 것이다.
#
# 그래서 같은 tripwire 를 **저장소의 추적 파일에 주입하는 바늘**에도 건다. 위와 같은
# 방식이다: 바늘을 여기 베껴 적지 않고 테스트 소스에서 AST 로 읽는다.
PACKAGING_SOURCES = ("test_settings_and_install.py", "test_release_gate.py",
                     "test_summary_pill.py", "test_summary_layout.py")
PACKAGING_RECEIVER_HINTS = ("setup_source", "build_source", "app_source",
                            "release_source", "verifier_source", "setup_text",
                            "build_text", "source")
TRACKED_INJECTION_TARGETS = ("setup.py", "build_app.sh", "verify_release_artifact.py",
                             "claude_pet.py", "release.sh")


def packaging_replace_sites(path):
    """(lineno, needle) — 추적 소스 텍스트를 받는 변수에 대한 `.replace("literal", …)`."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "replace" and node.args):
            continue
        receiver = (ast.unparse(node.func.value) or "").lower()
        if not any(h in receiver for h in PACKAGING_RECEIVER_HINTS):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append((node.lineno, arg.value))
    return out


class PackagingInjectionNeedlesTests(unittest.TestCase):
    """추적 파일에 주입하는 바늘도 여전히 표적을 찾는가.

    업데이터 쪽 tripwire 와 같은 이유로 존재한다 — 다만 표적이 생성된 스크립트가 아니라
    저장소의 추적 파일이다. 이번 릴리즈에서 setup.py·build_app.sh·
    verify_release_artifact.py 가 전부 바뀌었고, 그중 하나가 실제로 바늘을 죽였다.

    Rival: 바늘 목록을 여기 하드코딩하는 것 — 그건 자기 자신을 지킬 또 하나의 계기가
    되고, 검사기의 노후는 건강과 똑같이 생겼다.
    """

    def sources(self):
        available = [(name, REPO / "tests" / name) for name in PACKAGING_SOURCES]
        return [(n, p) for n, p in available if p.is_file()]

    def test_every_packaging_needle_still_occurs_in_a_tracked_source(self):
        texts = {}
        for name in TRACKED_INJECTION_TARGETS:
            path = REPO / name
            if path.is_file():
                texts[name] = path.read_text(encoding="utf-8")
        self.assertTrue(texts, "주입 표적이 될 추적 파일을 하나도 찾지 못했다")

        scanned = self.sources()
        self.assertTrue(scanned,
                        "패키징 테스트 파일을 하나도 찾지 못했다 — 이 tripwire 가 표적을 "
                        f"잃었다 (찾던 이름: {PACKAGING_SOURCES})")

        checked = 0
        for name, path in scanned:
            for lineno, needle in packaging_replace_sites(path):
                if len(needle) < 8:
                    continue          # 경로 정규화 같은 평범한 문자열 처리
                checked += 1
                with self.subTest(source=name, line=lineno):
                    where = [f for f, text in texts.items() if needle in text]
                    self.assertTrue(
                        where,
                        f"{name}:{lineno} 이 주입하려는 바늘이 어떤 추적 파일에도 없다: "
                        f"{needle!r} — `str.replace` 는 실패하지 않으므로 이 주입은 "
                        "아무것도 바꾸지 않고, 그 테스트는 소리 없이 공허해진다")

        # **리터럴 바늘이 0개인 것은 정상이고, 오히려 낫다.** 소스에서 계산한 바늘은
        # 애초에 어긋날 수가 없어서 이 tripwire 가 필요 없다 — setup.py 의 바늘이 죽은
        # 뒤 그렇게 고쳤다. 그래서 '리터럴이 최소 하나는 있어야 한다'고 단언하지 않는다:
        # 그건 더 안전한 형태를 금지하는 단언이 된다. 대신 표적 파일을 실제로 읽었는지를
        # 단언하고(위), 몇 개를 봤는지는 아래에 남긴다 — 0 이 '검사기가 고장났다'로
        # 읽히지 않도록.
        if not checked:
            print("\n[mutation-instruments] 패키징 리터럴 바늘 0개 — "
                  f"{len(scanned)}개 파일을 파싱했고 전부 소스에서 계산한 바늘이다.",
                  file=sys.stderr, flush=True)


if __name__ == "__main__":
    unittest.main()
