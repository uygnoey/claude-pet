"""Independent identity-bound cleanup gates for bundled-pet seeding.

Every source and destination path in this module lives below a realpath
temporary directory.  The tests pass both roots explicitly and never consult
``USER_PET_HOME`` or the process HOME.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import claude_pet


REAL_MKDTEMP = tempfile.mkdtemp
REAL_OPEN = os.open


def make_source(root):
    """Create one complete bundled pet and one README from literal bytes."""
    root = Path(root)
    root.mkdir(parents=True)
    readme = b"bundled README bytes\n"
    (root / "README.md").write_bytes(readme)
    dog = root / "pets" / "dog"
    dog.mkdir(parents=True)
    (dog / "pet.json").write_text(json.dumps({
        "id": "dog",
        "spritesheetPath": "spritesheet.webp",
        "spriteVersionNumber": 2,
    }))
    (dog / "spritesheet.webp").write_bytes(b"bundled dog sheet")
    (dog / "preview.png").write_bytes(b"bundled dog preview")
    return readme


class SeedingTemporaryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(os.path.realpath(REAL_MKDTEMP()))
        self.addCleanup(shutil.rmtree, self.td, True)
        self.source = self.td / "explicit-source" / ".claude_pet"
        self.destination = self.td / "explicit-home" / ".claude_pet"
        self.bundled_readme = make_source(self.source)

    @staticmethod
    def file_bytes_and_inode(path):
        path = Path(path)
        if not path.is_file():
            return None
        return path.read_bytes(), path.stat().st_ino

    def test_replacement_at_temporary_pet_folder_survives_cleanup(self):
        """Cleanup must not follow a replaced staging-folder name."""
        stage_name = ".seed-dog-fixed"
        pets = self.destination / "pets"
        stage = pets / stage_name
        displaced = pets / ".owned-dog-stage-displaced"
        sentinel = stage / "replacement-sentinel"
        replacement_bytes = b"replacement pet folder belongs to a rival\n"
        replacement_dir_inode = []
        replacement_file_inode = []
        real_remove_stage = claude_pet._remove_stage_at

        def replace_immediately_before_cleanup(
                dir_fd, temporary_name, *args, **kwargs):
            if temporary_name == stage_name and not replacement_dir_inode:
                stage.rename(displaced)
                stage.mkdir()
                sentinel.write_bytes(replacement_bytes)
                replacement_dir_inode.append(stage.stat().st_ino)
                replacement_file_inode.append(sentinel.stat().st_ino)
            return real_remove_stage(dir_fd, temporary_name, *args, **kwargs)

        with mock.patch.object(claude_pet, "BUNDLED_PET_README", ()), \
             mock.patch.object(claude_pet, "BUNDLED_PET_IDS", ("dog",)), \
             mock.patch.object(claude_pet, "_stage_name",
                               return_value=stage_name), \
             mock.patch.object(claude_pet, "_publish_dir_noreplace",
                               return_value=False), \
             mock.patch.object(
                 claude_pet, "_remove_stage_at",
                 side_effect=replace_immediately_before_cleanup):
            report = claude_pet.seed_bundled_pet_assets(
                source_root=self.source, dest_root=self.destination)

        self.assertTrue(replacement_dir_inode,
                        "the temporary pet cleanup boundary was not reached")
        self.assertTrue(stage.is_dir(),
                        "cleanup removed the replacement pet folder")
        self.assertEqual(stage.stat().st_ino, replacement_dir_inode[0],
                         "the replacement folder inode changed")
        self.assertEqual(
            self.file_bytes_and_inode(sentinel),
            (replacement_bytes, replacement_file_inode[0]),
            "cleanup altered or removed replacement folder contents")
        self.assertTrue(displaced.is_dir(),
                        "the updater-owned staging folder was not retained")
        self.assertFalse((pets / "dog").exists(),
                         "a deliberately refused pet was unexpectedly published")
        self.assertIn("pets/dog", report["skipped"])

    def test_replacement_at_temporary_readme_name_is_not_published_or_cleaned(self):
        """Publish and cleanup must remain bound to the staged README inode."""
        stage_name = ".seed-README-fixed"
        stage = self.destination / stage_name
        displaced = self.destination / ".owned-README-stage-displaced"
        final = self.destination / "README.md"
        replacement_bytes = b"replacement README temporary file\n"
        replacement_inode = []
        real_copy_into_fd = claude_pet._copy_into_fd

        def copy_then_replace(source, dir_fd, name):
            real_copy_into_fd(source, dir_fd, name)
            if name == stage_name and not replacement_inode:
                os.rename(name, displaced.name,
                          src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o600, dir_fd=dir_fd)
                with os.fdopen(fd, "wb") as out:
                    out.write(replacement_bytes)
                replacement_inode.append(
                    os.stat(name, dir_fd=dir_fd).st_ino)

        with mock.patch.object(claude_pet, "BUNDLED_PET_README",
                               ("README.md",)), \
             mock.patch.object(claude_pet, "BUNDLED_PET_IDS", ()), \
             mock.patch.object(claude_pet, "_stage_name",
                               return_value=stage_name), \
             mock.patch.object(claude_pet, "_copy_into_fd",
                               side_effect=copy_then_replace):
            claude_pet.seed_bundled_pet_assets(
                source_root=self.source, dest_root=self.destination)

        self.assertTrue(replacement_inode,
                        "the temporary README replacement was not injected")
        final_ok = (not final.exists()
                    or (final.is_file()
                        and final.read_bytes() == self.bundled_readme))
        displaced_ok = (displaced.is_file()
                        and displaced.read_bytes() == self.bundled_readme)
        self.assertEqual(
            (self.file_bytes_and_inode(stage), final_ok, displaced_ok),
            ((replacement_bytes, replacement_inode[0]), True, True),
            "(replacement_temp_state, final_absent_or_exact_bundled, "
            "owned_stage_retained_exact)")

    def test_replacement_between_pet_stage_mkdir_and_open_is_not_used(self):
        """Opening and publishing must stay bound to the mkdir-created stage."""
        stage_name = ".seed-dog-mkdir-open-fixed"
        pets = self.destination / "pets"
        stage = pets / stage_name
        displaced = pets / ".mkdir-created-stage-displaced"
        final = pets / "dog"
        sentinel = stage / "mkdir-open-rival-sentinel"
        replacement_bytes = b"rival won the stage name before open\n"
        replacement_dir_inode = []
        replacement_file_inode = []

        expected_pet = {
            name: (self.source / "pets" / "dog" / name).read_bytes()
            for name in claude_pet.BUNDLED_PET_FILES
        }

        def replace_immediately_before_stage_open(
                path, flags, *args, **kwargs):
            dir_fd = kwargs.get("dir_fd")
            if (path == stage_name and dir_fd is not None
                    and not replacement_dir_inode):
                stage.rename(displaced)
                stage.mkdir()
                sentinel.write_bytes(replacement_bytes)
                replacement_dir_inode.append(stage.stat().st_ino)
                replacement_file_inode.append(sentinel.stat().st_ino)
            return REAL_OPEN(path, flags, *args, **kwargs)

        with mock.patch.object(claude_pet, "BUNDLED_PET_README", ()), \
             mock.patch.object(claude_pet, "BUNDLED_PET_IDS", ("dog",)), \
             mock.patch.object(claude_pet, "_stage_name",
                               return_value=stage_name), \
             mock.patch.object(claude_pet.os, "open",
                               side_effect=replace_immediately_before_stage_open):
            claude_pet.seed_bundled_pet_assets(
                source_root=self.source, dest_root=self.destination)

        self.assertTrue(replacement_dir_inode,
                        "the mkdir-to-open replacement was not injected")
        rival_received_bundled_files = any(
            (stage / name).exists()
            for name in claude_pet.BUNDLED_PET_FILES)
        final_tree = None
        if final.is_dir():
            final_tree = {
                child.name: child.read_bytes()
                for child in final.iterdir()
                if child.is_file() and not child.is_symlink()
            }
        final_ok = not final.exists() or final_tree == expected_pet
        self.assertEqual(
            (stage.is_dir(),
             stage.stat().st_ino if stage.is_dir() else None,
             self.file_bytes_and_inode(sentinel),
             rival_received_bundled_files,
             final_ok),
            (True, replacement_dir_inode[0],
             (replacement_bytes, replacement_file_inode[0]),
             False, True),
            "(rival_present, rival_dir_inode, rival_sentinel_state, "
            "rival_received_bundled_files, final_absent_or_exact_bundled)")


if __name__ == "__main__":
    unittest.main()
