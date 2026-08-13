"""A copy that dies MIDWAY through a file, not one that never starts.

    python3 -m unittest tests.test_partial_copy_seeding -v    # from the repo root

WHY THIS IS A DIFFERENT STATE
-----------------------------
`_copy_into_fd` copies in two stages: `shutil.copy2` into a private scratch,
then `shutil.copyfileobj` from the scratch into a file opened relative to the
destination fd. Those two stages fail into different worlds:

* `copy2` raising - which is what the existing copy-failure coverage in
  `tests/test_settings_and_install.py` injects - happens *before* the
  destination fd is opened. No byte of that file ever reaches the stage, so no
  truncated file can exist. The stage is half-populated only in the sense that
  earlier whole files are in it.
* `copyfileobj` raising happens with the destination file already created and
  partly written. A **truncated file** exists inside the stage at the moment of
  failure. That is the state tested here, and nothing tested it before.

The distinction matters because the recovery mechanisms differ. A file that
never started is undone by removing the stage; a truncated file is undone by
removing the stage *and* by never having linked or published it first. The
danger is publish-then-fill: a pet directory published with two whole files and
one truncated one is skipped wholesale on every later run (the seeder skips by
directory), so the corruption is permanent and shows up as a pet that appears
in the menu and fails to load.

DISCRIMINATION
--------------
Every case asserts the injection actually fired and that it fired on the
fd-opened destination rather than on `copy2`'s internal copy - a wrapper that
silently never triggered would leave every "nothing was corrupted" assertion
true for the wrong reason. `assertInjectionFired` is that guard, and the tests
below would pass without it while testing nothing.

This suite writes only into `tempfile.TemporaryDirectory()`. It never reads the
real bundled payload and never touches `~/.claude_pet`.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import claude_pet


# Captured before anything is patched, so the injector below can still perform
# the copies it is not failing.
_real_copyfileobj = shutil.copyfileobj

# A sheet large enough that a partial write is unambiguously partial.
SHEET_BYTES = 8192


def make_pet_source(root):
    """A complete, valid bundled payload - built here, never copied from disk."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name in claude_pet.BUNDLED_PET_README:
        (root / name).write_bytes(("readme %s\n" % name).encode() * 64)
    for pet in claude_pet.BUNDLED_PET_IDS:
        d = root / "pets" / pet
        d.mkdir(parents=True)
        (d / "pet.json").write_text(json.dumps(
            {"id": pet,
             "spritesheetPath": claude_pet.BUNDLED_PET_SHEET,
             "spriteVersionNumber": 2}))
        (d / claude_pet.BUNDLED_PET_SHEET).write_bytes(
            (pet.encode() + b"-sheet-") * (SHEET_BYTES // 8))
        (d / "preview.png").write_bytes((pet.encode() + b"-preview") * 64)
    return root


class MidwayCopyFailure:
    """Replaces `shutil.copyfileobj`, failing after some bytes are written.

    Only the fd-opened destination is targeted. `copy2` may also route through
    `copyfileobj` depending on platform, and failing there would reproduce the
    already-covered "never started" case instead of this one. The two are told
    apart by the destination's `name`: `os.fdopen` leaves it an int, an ordinary
    `open()` leaves it a path string.
    """

    def __init__(self, target_basename, prefix_bytes=64):
        self.target = target_basename
        self.prefix = prefix_bytes
        self.fd_writes = []        # basenames we let through / failed on
        self.fired_on = None
        self.bytes_written = None

    def matches(self, src_name):
        """The two seeding paths name the scratch copy differently.

        `_seed_pets` copies under the final entry name (`pet.json`), while
        `_seed_readmes` copies under the staging name (`.seed-README.md-1a2b`)
        because it stages first and links afterwards. Matching only the plain
        name silently never fires on the README path - which is exactly what
        `assertInjectionFired` caught when this class did that.
        """
        return (src_name == self.target
                or src_name.startswith(".seed-%s-" % self.target))

    def __call__(self, fsrc, fdst, length=0):
        to_fd = isinstance(getattr(fdst, "name", None), int)
        src_name = os.path.basename(getattr(fsrc, "name", "") or "")
        if not to_fd:
            return _real_copyfileobj(fsrc, fdst, length)
        self.fd_writes.append(src_name)
        if self.matches(src_name) and self.fired_on is None:
            chunk = fsrc.read(self.prefix)
            fdst.write(chunk)
            fdst.flush()
            self.fired_on = src_name
            self.bytes_written = len(chunk)
            raise OSError(28, "simulated disk full midway through the file")
        return _real_copyfileobj(fsrc, fdst, length)


# Paths in the user's real home that this suite must never be the reason for
# touching. `seed_bundled_pet_assets` takes an explicit `dest_root`, so nothing
# here should reach them - which is exactly why it is checked rather than
# assumed. An updater test run created the cache directory below at 10:11 today
# by asking for a path, so "we only pass temp dirs" is not on its own evidence.
REAL_HOME = Path(os.path.expanduser("~"))
SENTINELS = (REAL_HOME / ".claude_pet",
             REAL_HOME / ".claude_pet.json",
             REAL_HOME / "claudepet_debug.log",
             REAL_HOME / "Library" / "Caches" / "me.yeongyu.claudepet")


def snapshot(paths):
    out = {}
    for p in paths:
        try:
            st = p.lstat()
            out[str(p)] = (True, st.st_size, st.st_mtime_ns)
        except OSError:
            out[str(p)] = (False, None, None)
    return out


class _SeedCase(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="partialcopy-"))
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        self.src = make_pet_source(self.td / "source" / ".claude_pet")
        self.dst = self.td / "home" / ".claude_pet"
        self.before = snapshot(SENTINELS)
        self.addCleanup(self.assertNothingEscaped)

    def assertNothingEscaped(self):
        after = snapshot(SENTINELS)
        for path, state in self.before.items():
            self.assertEqual(
                after[path], state,
                f"{path} changed while this test ran - the seeder reached "
                "outside the temp directory it was given")

    def seed(self, injector=None):
        if injector is None:
            return claude_pet.seed_bundled_pet_assets(
                source_root=self.src, dest_root=self.dst)
        with mock.patch.object(claude_pet.shutil, "copyfileobj", injector):
            return claude_pet.seed_bundled_pet_assets(
                source_root=self.src, dest_root=self.dst)

    # ---------- guards ----------

    def assertInjectionFired(self, inj):
        self.assertIsNotNone(
            inj.fired_on,
            "the failure was never injected - the destination never looked "
            f"like an fd-backed file (saw: {inj.fd_writes!r}). Every "
            "'nothing was corrupted' assertion below would hold for the wrong "
            "reason.")
        self.assertGreater(
            inj.bytes_written, 0,
            "the injection fired but wrote no bytes, so no truncated file was "
            "ever created - that is the already-covered 'never started' case, "
            "not this one.")

    def assertNoStageResidue(self):
        for d in (self.dst, self.dst / "pets"):
            if d.is_dir():
                leftovers = [p.name for p in d.iterdir()
                             if p.name.startswith(".seed-")]
                self.assertEqual(leftovers, [],
                                 f"staging residue left behind in {d.name}")

    def assertEverySurvivingFileIsWhole(self):
        """No file under the destination may be a truncation of its source.

        Stated over the whole tree rather than over the one file we broke: a
        publish-then-fill implementation would leave the truncation under a
        published pet, which a check aimed only at the stage would miss.
        """
        if not self.dst.exists():
            return
        for path in self.dst.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.dst)
            source = self.src / rel
            if not source.is_file():
                continue
            got, want = path.read_bytes(), source.read_bytes()
            self.assertEqual(
                len(got), len(want),
                f"{rel} is {len(got)} bytes but its source is {len(want)} - a "
                "partially copied file survived")
            self.assertEqual(got, want, f"{rel} does not match its source")


class PartialPetCopyTests(_SeedCase):
    def test_a_pet_whose_sheet_dies_midway_is_not_published(self):
        inj = MidwayCopyFailure(claude_pet.BUNDLED_PET_SHEET)
        report = self.seed(inj)
        self.assertInjectionFired(inj)
        self.assertFalse((self.dst / "pets" / "dog").exists(),
                         "a pet was published with a truncated sheet")
        self.assertNoStageResidue()
        self.assertEverySurvivingFileIsWhole()
        self.assertTrue(report["errors"], "the failure was not reported")

    def test_the_other_pets_are_still_seeded_whole(self):
        """One pet dying must not cost the rest - and must not half-cost them."""
        inj = MidwayCopyFailure(claude_pet.BUNDLED_PET_SHEET)
        self.seed(inj)
        self.assertInjectionFired(inj)
        for pet in claude_pet.BUNDLED_PET_IDS[1:]:
            with self.subTest(pet=pet):
                d = self.dst / "pets" / pet
                self.assertTrue(d.is_dir(), f"{pet} was not seeded")
                for name in claude_pet.BUNDLED_PET_FILES:
                    self.assertTrue((d / name).is_file(), f"{pet}/{name}")
        self.assertEverySurvivingFileIsWhole()

    def test_a_pet_that_died_midway_is_repaired_by_the_next_run(self):
        """The failure must not be sticky.

        The seeder skips by directory, so anything left at the destination -
        even an empty directory with the pet's name - would make the pet
        permanently unfixable. This is the assertion that a leftover stage
        renamed into place, or a pre-created target directory, would fail.
        """
        inj = MidwayCopyFailure(claude_pet.BUNDLED_PET_SHEET)
        self.seed(inj)
        self.assertInjectionFired(inj)
        report = self.seed()
        self.assertIn("pets/dog", report["copied"],
                      "the pet that failed midway was not repaired on a clean "
                      f"second run (report: {report!r})")
        for name in claude_pet.BUNDLED_PET_FILES:
            self.assertTrue((self.dst / "pets" / "dog" / name).is_file())
        self.assertEverySurvivingFileIsWhole()
        self.assertNoStageResidue()

    def test_the_first_file_dying_midway_is_handled_the_same_way(self):
        """pet.json is what `_is_pet_dir` keys on, so a truncated one is worst."""
        inj = MidwayCopyFailure("pet.json")
        report = self.seed(inj)
        self.assertInjectionFired(inj)
        self.assertFalse((self.dst / "pets" / "dog").exists())
        self.assertNoStageResidue()
        self.assertEverySurvivingFileIsWhole()
        self.assertTrue(report["errors"])


class PartialReadmeCopyTests(_SeedCase):
    """The README path publishes with `os.link`, not a directory rename.

    Different primitive, same requirement: the link must never be made from a
    truncated staging file, and the staging file must not survive.
    """

    def test_a_readme_that_dies_midway_is_not_linked_into_place(self):
        target = claude_pet.BUNDLED_PET_README[2]
        inj = MidwayCopyFailure(target)
        report = self.seed(inj)
        self.assertInjectionFired(inj)
        self.assertFalse((self.dst / target).exists(),
                         f"{target} was published from a truncated staging file")
        self.assertNoStageResidue()
        self.assertEverySurvivingFileIsWhole()
        self.assertTrue(report["errors"])

    def test_the_other_readmes_still_land_whole(self):
        target = claude_pet.BUNDLED_PET_README[2]
        inj = MidwayCopyFailure(target)
        self.seed(inj)
        self.assertInjectionFired(inj)
        for name in claude_pet.BUNDLED_PET_README:
            if name == target:
                continue
            with self.subTest(readme=name):
                self.assertTrue((self.dst / name).is_file(),
                                f"{name} was not seeded")
        self.assertEverySurvivingFileIsWhole()

    def test_a_readme_that_died_midway_is_repaired_by_the_next_run(self):
        target = claude_pet.BUNDLED_PET_README[2]
        inj = MidwayCopyFailure(target)
        self.seed(inj)
        self.assertInjectionFired(inj)
        report = self.seed()
        self.assertIn(target, report["copied"],
                      f"{target} was not repaired on a clean second run")
        self.assertEverySurvivingFileIsWhole()
        self.assertNoStageResidue()


class CopyPrimitiveRefusesAnExistingNameTests(_SeedCase):
    """`_copy_into_fd` opens with `O_EXCL`, and that is load-bearing.

    Same production function as the rest of this module, one property along:
    not "what happens when the copy dies" but "what happens when the name it
    is about to create already exists".

    Found by mutation - dropping `O_EXCL` for `O_TRUNC` killed no test in any
    module. It is not a redundant belt: `O_CREAT|O_TRUNC` **follows a symlink**,
    so a link planted at the staging name redirects the write out of the tree
    entirely and truncates whatever it points at. The staging name carries five
    random bytes, so this is not trivially reachable - which is the argument for
    keeping `O_EXCL`, not for leaving it untested. The randomness is the lock;
    `O_EXCL` is what happens when the lock is picked.

    The fixture pins the staging name so the plant is deterministic. That is
    the only way to exercise the branch at all, and it does not overstate
    reachability: the assertion is about what the primitive does when the name
    exists, not about how often it does.
    """

    FIXED = ".seed-README.md-deadbeef00"

    def plant_and_seed(self, link_target):
        """Pin only the README.md staging name; everything else stays random.

        Pinning every tag would make the pet staging *directories* collide with
        the planted symlink too, so a refusal could come from the wrong place.
        """
        real_stage_name = claude_pet._stage_name
        self.dst.mkdir(parents=True)
        os.symlink(str(link_target), self.dst / self.FIXED)

        def stage_name(tag):
            return self.FIXED if tag == "README.md" else real_stage_name(tag)

        with mock.patch.object(claude_pet, "_stage_name", stage_name):
            return claude_pet.seed_bundled_pet_assets(
                source_root=self.src, dest_root=self.dst), self.FIXED

    def test_a_symlink_planted_at_the_staging_name_is_not_written_through(self):
        victim = self.td / "someone-elses-file.txt"
        original = "SOMEBODY ELSE'S FILE"
        victim.write_text(original)
        report, _fixed = self.plant_and_seed(victim)
        self.assertEqual(
            victim.read_text(), original,
            "the seeder wrote through a symlink planted at its staging name - "
            "a file outside the destination tree was overwritten")
        self.assertTrue(report["errors"],
                        "the refusal was not reported at all")

    def test_the_plant_is_actually_in_the_way(self):
        """Discrimination: if the fixture missed, the test above proves nothing.

        A staging name that does not collide leaves the victim untouched for
        the most boring reason available, and the assertion still passes. This
        checks the collision really happened.
        """
        victim = self.td / "someone-elses-file.txt"
        victim.write_text("x")
        seen = []
        real_open = os.open

        def watch(path, flags, *a, **kw):
            if isinstance(path, str) and path.startswith(".seed-"):
                seen.append((path, flags))
            return real_open(path, flags, *a, **kw)

        with mock.patch.object(os, "open", watch):
            _report, fixed = self.plant_and_seed(victim)
        creates = [(p, f) for p, f in seen if p == fixed and f & os.O_CREAT]
        self.assertTrue(
            creates,
            f"the seeder never tried to CREATE {fixed!r}, so the planted "
            f"symlink was never in the way (saw: {seen!r})")
        self.assertTrue(
            all(f & os.O_EXCL for _p, f in creates),
            "the staging file was created without O_EXCL, so the open would "
            "have followed the planted symlink")


if __name__ == "__main__":
    unittest.main()
