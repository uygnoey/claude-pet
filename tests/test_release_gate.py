"""Executable tests for the packaging gate — fixtures, not source greps.

The gap this closes was invisible for a reason: the existing packaging tests are
substring searches over the build scripts. A grep passes when the string appears
in a *comment*, and it cannot tell whether the code it names ever runs. So the
release artifact went unverified while a test suite reported it covered.

Every test here therefore builds a real tree on disk and runs the real code
against it, and each one is written so that **deleting the check it targets makes
it fail**. Where a check is about "the old tree survives a failure", the fixture
injects the failure rather than asserting the happy path.

    python3 -m unittest tests.test_release_gate -v
"""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify_pet_payload


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / ".claude_pet"
REAL_HOME = Path(os.path.expanduser("~"))

# Paths in the user's real state that nothing here may touch. Checked after
# every test that starts a shell, because the classes below run `copy_pet_assets`
# — a function containing several `rm -rf` — inside a real zsh.
SENTINELS = (REAL_HOME / ".claude_pet",
             REAL_HOME / ".claude_pet.json",
             REAL_HOME / "claudepet_debug.log",
             REAL_HOME / "Library" / "Caches" / "me.yeongyu.claudepet",
             Path("/Applications/ClaudePet.app"))


def snapshot(paths):
    out = {}
    for p in paths:
        try:
            st = p.lstat()
            out[str(p)] = (True, st.st_size, st.st_mtime_ns)
        except OSError:
            out[str(p)] = (False, None, None)
    return out


class ShellSandbox:
    """Environment isolation for the classes that source `build_app.sh`.

    Two defects this replaces, both inherited and both the same shape as the
    `gh` isolation that was corrected elsewhere in this suite — hardening the
    thing expected to be dangerous while leaving the environment wide open:

    * the shells were started as `/bin/zsh -c` **without `-f`**, so the user's
      real `~/.zshenv` was sourced into every one of them. That file is
      arbitrary user code, running in a shell that is about to execute
      `copy_pet_assets` and its `rm -rf`s.
    * the environment was `dict(os.environ, ...)`, so real `HOME`, `TMPDIR`,
      `CDPATH` and `ZDOTDIR` came along. `WritePlistTests` passed no `env` at
      all and inherited the lot by default.

    The environment is therefore **built from an allow-list** rather than copied
    and amended: copy-and-amend only covers the variables someone thought of.
    """

    #: `-f` (NO_RCS) is the load-bearing flag: it stops `~/.zshenv` being read.
    ARGV = ["/bin/zsh", "-f", "-c"]

    @staticmethod
    def env(home, tmpdir, extra=None):
        base = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(home),
            "TMPDIR": str(tmpdir),
            "ZDOTDIR": str(home),
            "CDPATH": "",
            "LANG": "C",
            "LC_ALL": "C",
            # `copy_pet_assets` runs `${PYCHECK:-python3}`. With PATH narrowed
            # to system directories, a bare `python3` would resolve to whatever
            # /usr/bin offers rather than the interpreter running these tests -
            # so the payload check could fail for an interpreter reason and be
            # read as a payload verdict. Pin it to this interpreter instead.
            # `extra` still wins, which is what lets a fixture point PYCHECK at
            # /usr/bin/false to force the check to fail on purpose.
            "PYCHECK": sys.executable,
        }
        base.update(extra or {})
        return base


def payload_copy(dst):
    """A pristine copy of the shipped tree, as an artifact would contain it."""
    shutil.copytree(SOURCE, dst, symlinks=True)
    return Path(dst)


class ExpectedSetTests(unittest.TestCase):
    def test_expected_members_are_derived_not_hardcoded(self):
        """A literal 16 would silently check a subset once a fifth pet ships."""
        consts = verify_pet_payload._constants()
        rels = verify_pet_payload.expected_members(consts)
        self.assertEqual(
            len(rels),
            len(consts["BUNDLED_PET_README"])
            + len(consts["BUNDLED_PET_IDS"]) * len(consts["BUNDLED_PET_FILES"]),
        )
        # Derived from claude_pet.py, so a new pet grows the set with no edit here.
        fake = {
            "BUNDLED_PET_README": ("README.md",),
            "BUNDLED_PET_IDS": ("dog", "elephant", "fox", "scorpion", "newpet"),
            "BUNDLED_PET_FILES": ("pet.json", "spritesheet.webp", "preview.png"),
        }
        self.assertIn("pets/newpet/spritesheet.webp",
                      verify_pet_payload.expected_members(fake))

    def test_constants_are_read_without_importing_the_app(self):
        """BUNDLED_PET_FILES references BUNDLED_PET_SHEET, so plain literal_eval fails."""
        consts = verify_pet_payload._constants()
        self.assertIn("spritesheet.webp", consts["BUNDLED_PET_FILES"])
        self.assertEqual(len(consts["BUNDLED_PET_IDS"]), 4)


class PayloadVerificationTests(unittest.TestCase):
    """One fixture per check. Each must fail for its own reason."""

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.root = payload_copy(Path(self.td) / "payload")

    def verify(self):
        return verify_pet_payload.verify(str(self.root), str(SOURCE))

    def test_a_pristine_payload_passes(self):
        self.assertEqual(self.verify(), [])

    def test_missing_member_is_reported(self):
        (self.root / "pets" / "dog" / "preview.png").unlink()
        self.assertTrue(any("pets/dog/preview.png" in p and "missing" in p
                            for p in self.verify()))

    def test_missing_readme_is_reported(self):
        (self.root / "README.ko.md").unlink()
        self.assertTrue(any("README.ko.md" in p for p in self.verify()))

    def test_member_replaced_by_a_symlink_is_reported(self):
        target = self.root / "pets" / "fox" / "spritesheet.webp"
        target.unlink()
        os.symlink("preview.png", target)
        self.assertTrue(any("pets/fox/spritesheet.webp" in p and "symlink" in p
                            for p in self.verify()))

    def test_symlink_anywhere_in_the_subtree_is_reported(self):
        os.symlink("/etc/passwd", self.root / "pets" / "smuggled")
        self.assertTrue(any("symlink" in p for p in self.verify()))

    def test_contents_differing_from_source_are_reported(self):
        sheet = self.root / "pets" / "scorpion" / "spritesheet.webp"
        sheet.write_bytes(sheet.read_bytes() + b"tampered")
        self.assertTrue(any("pets/scorpion/spritesheet.webp" in p and "differ" in p
                            for p in self.verify()))

    def test_unexpected_extra_file_is_reported(self):
        (self.root / "pets" / "dog" / "notes.txt").write_text("stray")
        self.assertTrue(any("notes.txt" in p and "extra" in p for p in self.verify()))

    def test_wrong_sheet_name_in_metadata_is_reported(self):
        meta = self.root / "pets" / "dog" / "pet.json"
        doc = json.loads(meta.read_text())
        doc["spritesheetPath"] = "alternate.webp"
        meta.write_text(json.dumps(doc))
        self.assertTrue(any("spritesheetPath" in p for p in self.verify()))

    def test_wrong_sprite_version_in_metadata_is_reported(self):
        meta = self.root / "pets" / "elephant" / "pet.json"
        doc = json.loads(meta.read_text())
        doc["spriteVersionNumber"] = 999
        meta.write_text(json.dumps(doc))
        self.assertTrue(any("spriteVersionNumber" in p for p in self.verify()))

    def test_entirely_absent_payload_is_reported(self):
        shutil.rmtree(self.root)
        self.assertTrue(any("missing entirely" in p for p in self.verify()))

    def test_cli_exits_non_zero_and_names_the_member(self):
        (self.root / "pets" / "dog" / "pet.json").unlink()
        result = subprocess.run(
            ["python3", str(REPO / "verify_pet_payload.py"), str(self.root)],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pets/dog/pet.json", result.stderr)


class ChecksThatOnlyFireWhenSourceAndArtifactAgreeTests(unittest.TestCase):
    """The fixtures above are realistic but they do not *isolate* every check.

    Verified by mutation: delete the member-symlink, sheet-name or sprite-version
    check and the fixtures above still go red — because a payload that diverges
    from source also fails the **hash comparison**, which subsumes them. That
    redundancy is good in production and useless as evidence, so these fixtures
    break the repo source and the artifact **identically**. The bytes then match,
    the hash check is blind, and only the semantic check can object.

    Mutation-checked: with its target check deleted, each of these passes, so
    each one genuinely fails for the reason it names. Two checks remain subsumed
    and are honestly not isolated — member presence (a missing file also breaks
    the hash read) and the subtree symlink scan (a stray link is also an extra);
    both are kept as cheap, clearer-diagnostic defence in depth.
    """

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.source = Path(self.td) / "source"
        shutil.copytree(SOURCE, self.source, symlinks=True)

    def mirror(self):
        """Copy the (already broken) source, so payload == source byte-for-byte."""
        payload = Path(self.td) / "payload"
        shutil.copytree(self.source, payload, symlinks=True)
        return verify_pet_payload.verify(str(payload), str(self.source))

    def test_wrong_sprite_version_in_both_is_still_reported(self):
        meta = self.source / "pets" / "elephant" / "pet.json"
        doc = json.loads(meta.read_text())
        doc["spriteVersionNumber"] = 999
        meta.write_text(json.dumps(doc))
        self.assertTrue(any("spriteVersionNumber" in p for p in self.mirror()))

    def test_wrong_sheet_name_in_both_is_still_reported(self):
        meta = self.source / "pets" / "dog" / "pet.json"
        doc = json.loads(meta.read_text())
        doc["spritesheetPath"] = "alternate.webp"
        meta.write_text(json.dumps(doc))
        self.assertTrue(any("spritesheetPath" in p for p in self.mirror()))

    def test_a_symlinked_member_in_both_is_still_reported(self):
        target = self.source / "pets" / "fox" / "spritesheet.webp"
        target.unlink()
        os.symlink("preview.png", target)
        self.assertTrue(any("pets/fox/spritesheet.webp" in p and "symlink" in p
                            for p in self.mirror()))


class TreeShapeTests(unittest.TestCase):
    """Holes in the *shape* of the check, not its contents.

    Each was confirmed RED first — the gate passed a payload it should have
    refused — because file-level assertions all pass honestly when the thing
    deciding *which* files get checked is wrong. Same ancestor-vs-leaf pattern
    as the updater's symlink chain and the seeder's root swap.
    """

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)

    def test_a_symlinked_payload_root_is_refused(self):
        """os.walk follows the link and cleanly verifies the wrong tree."""
        real = self.td / "real"
        shutil.copytree(SOURCE, real, symlinks=True)
        link = self.td / "payload"
        os.symlink(real, link)
        problems = verify_pet_payload.verify(str(link), str(SOURCE))
        self.assertTrue(any("root is not a real directory" in p for p in problems))

    def test_a_symlinked_expected_directory_is_refused(self):
        payload = self.td / "payload"
        shutil.copytree(SOURCE, payload, symlinks=True)
        elsewhere = self.td / "elsewhere"
        shutil.move(str(payload / "pets"), str(elsewhere))
        os.symlink(elsewhere, payload / "pets")
        problems = verify_pet_payload.verify(str(payload), str(SOURCE))
        self.assertTrue(any("pets" in p and "not a real directory" in p
                            for p in problems))

    def test_an_unexpected_empty_directory_is_reported(self):
        """A file-only comparison cannot see a directory with nothing in it."""
        payload = self.td / "payload"
        shutil.copytree(SOURCE, payload, symlinks=True)
        (payload / "pets" / "ghost").mkdir()
        problems = verify_pet_payload.verify(str(payload), str(SOURCE))
        self.assertTrue(any("pets/ghost" in p for p in problems))

    def test_a_missing_expected_directory_is_reported(self):
        payload = self.td / "payload"
        shutil.copytree(SOURCE, payload, symlinks=True)
        shutil.rmtree(payload / "pets" / "fox")
        problems = verify_pet_payload.verify(str(payload), str(SOURCE))
        self.assertTrue(any("pets/fox" in p for p in problems))


class InstallerRefusalsAreMirroredTests(unittest.TestCase):
    """Anything the runtime seeder refuses, the release gate must refuse too.

    Hash-comparing artifact against source proves the artifact *mirrors* the
    source. It proves nothing about the source being valid, so a defect present
    identically in both is invisible by construction. These fixtures therefore
    break source and artifact together, and each corresponds to a rejection in
    `claude_pet._bad_pet_metadata` — the consumer that would decline the pet
    after we shipped it.
    """

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.source = self.td / "source"
        shutil.copytree(SOURCE, self.source, symlinks=True)

    def mirror(self):
        payload = self.td / "payload"
        shutil.copytree(self.source, payload, symlinks=True)
        return verify_pet_payload.verify(str(payload), str(self.source))

    def edit_meta(self, pet, **changes):
        meta = self.source / "pets" / pet / "pet.json"
        doc = json.loads(meta.read_text())
        doc.update(changes)
        meta.write_text(json.dumps(doc))

    def test_an_id_disagreeing_with_its_folder_is_refused(self):
        """The installer refuses this pet; shipping it would certify a dud."""
        self.edit_meta("dog", id="fox")
        self.assertTrue(any("id is 'fox'" in p for p in self.mirror()))
        # ...and confirm that is genuinely what the installer does.
        import claude_pet
        self.assertIsNotNone(
            claude_pet._bad_pet_metadata(str(self.source / "pets" / "dog"), "dog"))

    def test_every_installer_refusal_has_a_gate_counterpart(self):
        """The surface is closed: each rejection below is caught by both."""
        import claude_pet
        cases = (
            ("dog", {"id": "fox"}),
            ("dog", {"spritesheetPath": "alternate.webp"}),
            ("elephant", {"spriteVersionNumber": 999}),
            ("fox", {"spriteVersionNumber": "not-an-int"}),
        )
        for pet, changes in cases:
            with self.subTest(pet=pet, changes=changes):
                shutil.rmtree(self.source)
                shutil.copytree(SOURCE, self.source, symlinks=True)
                shutil.rmtree(self.td / "payload", ignore_errors=True)
                self.edit_meta(pet, **changes)
                self.assertIsNotNone(
                    claude_pet._bad_pet_metadata(
                        str(self.source / "pets" / pet), pet),
                    "the installer would accept this — gate/installer disagree")
                self.assertTrue(self.mirror(),
                                "the installer refuses this but the gate ships it")


class WritePlistTests(unittest.TestCase):
    """`write_plist` must be executed and its output parsed, not grepped.

    A substring search over the script passes on a comment and proves nothing
    about the value written — which is how the hardcoded `1.0` drifted here
    before.
    """

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.sandbox = self.td / "repo"
        self.sandbox.mkdir()
        self.home = self.td / "home"
        self.tmp = self.td / "tmp"
        for d in (self.home, self.tmp):
            d.mkdir()
        shutil.copy2(REPO / "build_app.sh", self.sandbox / "build_app.sh")
        shutil.copy2(REPO / "claude_pet.py", self.sandbox / "claude_pet.py")
        self.bundle = self.td / "ClaudePet.app"
        (self.bundle / "Contents").mkdir(parents=True)
        self.before = snapshot(SENTINELS)
        self.addCleanup(self.assertNothingEscaped)

    def assertNothingEscaped(self):
        after = snapshot(SENTINELS)
        for path, state in self.before.items():
            self.assertEqual(after[path], state,
                             f"{path} changed while this test ran")

    def app_version(self):
        import re
        text = (REPO / "claude_pet.py").read_text()
        return re.search(r'APP_VERSION = "([^"]+)"', text).group(1)

    def test_both_version_keys_equal_app_version(self):
        subprocess.run(
            ShellSandbox.ARGV + [
             f'source "{self.sandbox}/build_app.sh" >/dev/null 2>&1 || true; '
             f'write_plist "{self.bundle}"'],
            cwd=str(self.sandbox), capture_output=True, text=True,
            env=ShellSandbox.env(self.home, self.tmp))
        plist_path = self.bundle / "Contents" / "Info.plist"
        self.assertTrue(plist_path.is_file(), "write_plist produced no Info.plist")
        with plist_path.open("rb") as f:
            plist = plistlib.load(f)
        want = self.app_version()
        self.assertEqual(plist["CFBundleShortVersionString"], want)
        self.assertEqual(plist["CFBundleVersion"], want)
        self.assertNotEqual(want, "1.0",
                            "the fixture cannot distinguish a hardcoded 1.0")
        self.assertEqual(plist["CFBundleIdentifier"], "me.yeongyu.claudepet")


class ManualBuildAssetSwapTests(unittest.TestCase):
    """`build_app.sh copy_pet_assets` must never destroy the old tree first.

    The discriminating case is the third one: a `rm -rf`-then-`cp -R`
    implementation passes "the tree is refreshed" and "the plist is versioned",
    and fails only when the copy is made to fail partway.
    """

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self.bundle = Path(self.td) / "ClaudePet.app"
        (self.bundle / "Contents" / "Resources").mkdir(parents=True)
        self.sandbox = Path(self.td) / "repo"
        self.sandbox.mkdir()
        self.home = Path(self.td) / "home"
        self.tmp = Path(self.td) / "tmp"
        for d in (self.home, self.tmp):
            d.mkdir()
        self.sandbox_script()
        self.before = snapshot(SENTINELS)
        self.addCleanup(self.assertNothingEscaped)

    def assertNothingEscaped(self):
        after = snapshot(SENTINELS)
        for path, state in self.before.items():
            self.assertEqual(
                after[path], state,
                f"{path} changed while this test ran - copy_pet_assets runs "
                "`rm -rf` in a real shell, so this is checked, not assumed")

    @property
    def resources(self):
        return self.bundle / "Contents" / "Resources"

    def snapshot(self):
        """Hashes and mtimes of the installed payload — the survival evidence."""
        root = self.resources / ".claude_pet"
        return {
            str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()
        }

    def run_copy(self, extra_env=None, script=None):
        """Source a **copy** of the script, never the repo's own.

        Sourcing `build_app.sh` in place used to run its bottom `case`, which
        built and code-signed with the Developer ID. The copy is what lets a
        fixture corrupt the script to inject a fault.

        **What actually keeps this from signing, stated accurately.** An earlier
        version of this docstring said the copy meant the file "must not depend
        on" the source guard. It does depend on it: the copy carries the same
        bottom `case`, so copying provides no independence at all. Two other
        things provide the safety, and it is worth naming them so nobody removes
        the wrong one —

        * the guard (`ZSH_EVAL_CONTEXT`) returns before the dispatch, which is
          why `copy_pet_assets` is reachable here at all; and
        * with the guard gone, `$1` is unset in this shell, and `build_app.sh`
          sends the no-argument case to *usage + `exit 1`* rather than to
          `build`. The shell would die and every test here would fail loudly.
          **That default is the thing standing between this file and a signing
          run**, so it must not be "restored" to `build`.

        **And be precise about what that run would be.** The fallback is not
        "an unsigned local build". `build()` ends in `sign_app`, which takes the
        first `Developer ID Application|Apple Development` identity from
        `security find-identity` - on this machine the only identity present is
        `Developer ID Application: Yeongyu Yang (RXGNVSLYF5)` - and runs
        `codesign --force --options runtime --timestamp`. `sign_app` is reached
        by `build`, `install` and `update` alike (`build_app.sh:140`, `:338`).
        So a fault here signs the user's real certificate over a fixture
        bundle. Verified by reading `sign_app` and running
        `security find-identity -v -p codesigning`, not taken on report.

        This matters because documentation said otherwise: `CLAUDE.md` has
        described `build_app.sh` as unsigned and safe to run freely. Anyone
        reasoning from that text would have judged this file's blast radius
        wrongly - which is the same failure as the old comment above, one level
        up.

        The environment is built rather than inherited - see `ShellSandbox`.
        """
        env = ShellSandbox.env(self.home, self.tmp, extra_env)
        src = script or (self.sandbox / "build_app.sh")
        return subprocess.run(
            ShellSandbox.ARGV + [
             f'source "{src}" >/dev/null 2>&1 || true; '
             f'copy_pet_assets "{self.bundle}"'],
            cwd=str(self.sandbox), capture_output=True, text=True, env=env)

    def replacing(self, old, new, count=1):
        """A mutation that asserts it actually applied.

        A `str.replace` whose pattern no longer matches silently does nothing,
        and the fixture then exercises the unmutated script and passes — a
        vacuous green that looks like coverage. Assert the replacement count.
        """
        def apply(text):
            found = text.count(old)
            self.assertEqual(
                found, count,
                f"fault injection did not apply: expected {count} occurrence(s) "
                f"of {old!r}, found {found} — the script changed under the test")
            return text.replace(old, new)
        return apply

    def sandbox_script(self, mutate=None):
        """A working copy of the repo laid out as the script expects."""
        shutil.copy2(REPO / "build_app.sh", self.sandbox / "build_app.sh")
        shutil.copy2(REPO / "verify_pet_payload.py",
                     self.sandbox / "verify_pet_payload.py")
        shutil.copy2(REPO / "claude_pet.py", self.sandbox / "claude_pet.py")
        shutil.copytree(SOURCE, self.sandbox / ".claude_pet", symlinks=True,
                        dirs_exist_ok=True)
        if mutate:
            path = self.sandbox / "build_app.sh"
            path.write_text(mutate(path.read_text()))
        return self.sandbox / "build_app.sh"

    def test_assets_are_installed_into_a_fresh_bundle(self):
        self.run_copy()
        landed = self.bundle / "Contents" / "Resources" / ".claude_pet"
        self.assertTrue((landed / "pets" / "dog" / "spritesheet.webp").is_file())
        self.assertEqual(verify_pet_payload.verify(str(landed), str(SOURCE)), [])

    def test_a_failing_copy_leaves_the_existing_tree_untouched(self):
        """The assertion a destroy-then-copy implementation cannot pass."""
        self.run_copy()
        landed = self.bundle / "Contents" / "Resources" / ".claude_pet"
        before = {
            str(p.relative_to(landed)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in landed.rglob("*") if p.is_file()
        }
        self.assertTrue(before, "precondition: the first copy must have landed")

        # Make the verification of the *new* copy fail, standing in for any
        # mid-copy failure: the swap must not happen and the old tree must stay.
        result = self.run_copy(extra_env={"PYCHECK": "/usr/bin/false"})
        self.assertNotEqual(result.returncode, 0)

        after = {
            str(p.relative_to(landed)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in landed.rglob("*") if p.is_file()
        }
        self.assertEqual(after, before,
                         "a failed refresh modified or removed the installed assets")

    def test_a_failing_final_move_preserves_the_old_payload(self):
        """Fault at the second rename — stage→final. Old payload must survive."""
        self.run_copy()
        before = self.snapshot()
        script = self.sandbox_script(
            mutate=self.replacing('if ! mv "$stage" "$final"; then',
                                  'if ! false; then'))
        result = self.run_copy(script=script)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before,
                         "a failed final move lost the installed payload")

    def test_a_failing_restore_keeps_the_backup_and_says_so(self):
        """The case the old code lied about: restore fails, it claimed success.

        The payload must remain findable — at the final location or under the
        named backup — and the script must not report a rollback it never did.
        """
        self.run_copy()
        before = self.snapshot()
        script = self.sandbox_script(
            mutate=lambda t: self.replacing(
                'if ! mv "$stage" "$final"; then', 'if ! false; then')(
                    self.replacing(
                        'if [ ! -e "$final" ] && mv "$backup" "$final" \\\n',
                        'if [ ! -e "$final" ] && false \\\n')(t)))
        result = self.run_copy(script=script)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("되돌렸습니다", result.stdout,
                         "claimed a rollback that did not happen")
        backup = self.resources / ".claude_pet.previous"
        self.assertTrue(backup.is_dir(), "the only copy of the payload was deleted")
        surviving = {
            str(p.relative_to(backup)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in backup.rglob("*") if p.is_file()
        }
        self.assertEqual(surviving, before)

    #: Bytes that exist nowhere in the source tree, so a file of this name
    #: created fresh cannot satisfy an assertion on its contents.
    SENTINEL = "only the crashed-out backup carries these bytes\n"

    def crash_between_the_renames(self):
        """Drive a run that dies after final→backup, before stage→final.

        That is the crash window the named backup exists for: the old payload
        is no longer at `final` and is findable only under `.claude_pet.previous`.
        """
        script = self.sandbox_script(
            mutate=self.replacing('if ! mv "$stage" "$final"; then',
                                  'exit 9\n  if ! mv "$stage" "$final"; then'))
        self.run_copy(script=script)
        backup = self.resources / ".claude_pet.previous"
        self.assertTrue(backup.is_dir(),
                        "a crash between the renames left nothing findable")
        self.assertFalse((self.resources / ".claude_pet").exists())
        return backup

    def test_recovery_moves_the_crashed_out_backup_itself(self):
        """Recovery must restore *that* directory, not produce a look-alike.

        This assertion is hard to make because **"restored, then reinstalled"
        and "deleted the backup, then copied fresh" converge on the same final
        state** — the old payload and the source are byte-identical, so no
        assertion about the end state of a completed run can tell them apart.
        The earlier attempts failed for that reason: a sentinel cannot survive a
        completed run, and the "↩️" log line is a process observable the code can
        emit without doing the work, so an implementation that prints and does
        not restore passes.

        What separates them is stopping the run **at the boundary**: recovery
        happens first, then the verifier is forced to fail, which aborts before
        the success path deletes the backup and reinstalls from source. The
        sentinel is therefore still in place at the moment it is asserted on —
        and asserting its **bytes** means a same-named file created fresh does
        not satisfy it.
        """
        self.run_copy()
        before = self.snapshot()
        backup = self.crash_between_the_renames()
        (backup / "RECOVERED-ME.txt").write_text(self.SENTINEL)

        result = self.run_copy(extra_env={"PYCHECK": "/usr/bin/false"})
        self.assertNotEqual(result.returncode, 0,
                            "the forced verifier failure did not abort the run — "
                            "the success path may have cleaned up the evidence")

        recovered = self.resources / ".claude_pet" / "RECOVERED-ME.txt"
        self.assertTrue(
            recovered.is_file(),
            "the crashed-out payload was not restored to its place: recovery "
            "either never ran or rebuilt the tree from source")
        self.assertEqual(
            recovered.read_text(), self.SENTINEL,
            "a file of the right name is there but not the recovered one")
        self.assertFalse(
            backup.exists(),
            "the backup is still present — it was copied, not moved, so a "
            "later cleanup can still delete the only recovered copy")
        # `mv` preserves mtimes, so the rest of the tree must match the original
        # snapshot exactly. A fresh copy from source would carry new mtimes.
        rest = {k: v for k, v in self.snapshot().items()
                if k != "RECOVERED-ME.txt"}
        self.assertEqual(rest, before,
                         "the restored tree is not the one that was backed up")

    def test_the_next_ordinary_run_self_heals_and_completes(self):
        """After the crash, an unmutated run recovers and finishes the job.

        This is the completion half only. The evidence that recovery *moved the
        backup* lives in the boundary test above — here the run legitimately
        reinstalls from source afterwards, which erases that evidence, so
        compare **contents only**: `cp -R` does not preserve mtimes, and
        requiring identical mtimes would assert that recovery left the job
        undone.
        """
        self.run_copy()
        before = self.snapshot()
        self.crash_between_the_renames()

        result = self.run_copy(script=self.sandbox_script())
        self.assertEqual(result.returncode, 0,
                         "the next run did not complete after recovery")
        self.assertEqual({k: v[0] for k, v in self.snapshot().items()},
                         {k: v[0] for k, v in before.items()},
                         "the recovered payload has the wrong contents")
        residue = [p.name for p in self.resources.iterdir()
                   if p.name.startswith(".claude_pet.")]
        self.assertEqual(residue, [], "recovery left staging or backup residue")
        self.assertIn("↩️", result.stdout,
                      "the run did not report recovering the interrupted state")

    def test_a_copy_that_fails_midway_leaves_the_old_payload_intact(self):
        """Different state from a copy that fails at the start.

        A `cp` that dies partway leaves a stage with *some* files in it, which
        is the state most likely to be mistaken for a usable tree by anything
        downstream. The old payload must still be untouched and the partial
        stage must not survive.
        """
        self.run_copy()
        before = self.snapshot()
        script = self.sandbox_script(
            mutate=self.replacing(
                'if ! cp -R .claude_pet "$stage"; then',
                'mkdir -p "$stage"\n'
                '  cp .claude_pet/README.md "$stage/" 2>/dev/null || true\n'
                '  cp -R .claude_pet/pets "$stage/" 2>/dev/null || true\n'
                '  rm -f "$stage/pets/fox/spritesheet.webp"\n'
                '  if ! false; then'))
        result = self.run_copy(script=script)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before,
                         "a mid-copy failure damaged the installed payload")
        residue = [p.name for p in self.resources.iterdir()
                   if p.name.startswith(".claude_pet.")]
        self.assertEqual(residue, [], "a half-populated stage survived")

    def test_no_staging_or_backup_residue_is_left_behind(self):
        self.run_copy()
        self.run_copy(extra_env={"PYCHECK": "/usr/bin/false"})
        res = self.bundle / "Contents" / "Resources"
        residue = [p.name for p in res.iterdir()
                   if p.name.startswith(".claude_pet.")]
        self.assertEqual(residue, [])


if __name__ == "__main__":
    unittest.main()
