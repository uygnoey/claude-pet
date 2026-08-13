"""Temp-only gates for release-artifact application preflight.

The subject is ``verify_release_artifact`` delegation and its local code-leaf
check.  Signing/notarization is represented by a fake ``validate_update_app``;
no signing tool, release shell, installed application, or external path is
ever invoked.
"""

import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify_release_artifact


REAL_MKDTEMP = tempfile.mkdtemp
CHECKOUT_SOURCE = Path(verify_release_artifact.__file__).resolve().with_name(
    "claude_pet.py")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class FakeClaudePet:
    def __init__(self, verdict=True):
        self.verdict = verdict
        self.calls = []

    def validate_update_app(self, app_path, expect_version, **kwargs):
        self.calls.append((app_path, expect_version, kwargs))
        return self.verdict


class ReleaseArtifactAppPreflightTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(os.path.realpath(REAL_MKDTEMP()))
        self.addCleanup(shutil.rmtree, self.td, True)

    def make_app(self, name="ClaudePet.app", code="checkout"):
        app = self.td / name
        resources = app / "Contents" / "Resources"
        resources.mkdir(parents=True)
        leaf = resources / "claude_pet.py"
        if code == "checkout":
            shutil.copyfile(CHECKOUT_SOURCE, leaf)
        elif code == "stale":
            leaf.write_bytes(b"APP_VERSION = 'stale-artifact'\n")
        elif code == "missing":
            pass
        elif code == "directory":
            leaf.mkdir()
        elif code == "symlink":
            target = self.td / (name + "-real-code.py")
            shutil.copyfile(CHECKOUT_SOURCE, target)
            os.symlink(target, leaf)
        else:
            raise ValueError(code)
        return app, leaf

    def check_with_fake(self, app, version="0.20", arches=("arm64",)):
        fake = FakeClaudePet()
        with mock.patch.object(verify_release_artifact, "_load_app",
                               return_value=fake):
            result = verify_release_artifact.check_app(
                str(app), version, list(arches))
        return result, fake

    def test_cli_forwards_exact_version_and_ordered_arches_to_validator(self):
        app, leaf = self.make_app()
        self.assertEqual(sha256(leaf), sha256(CHECKOUT_SOURCE),
                         "valid fixture is not checkout-identical")
        fake = FakeClaudePet()
        version = "0.20-exact+build.7"
        arches = "x86_64,arm64"

        with mock.patch.object(verify_release_artifact, "_load_app",
                               return_value=fake):
            rc = verify_release_artifact.main([
                "app", str(app), "--expect-version", version,
                "--arches", arches,
            ])

        self.assertEqual(rc, 0)
        self.assertEqual(
            fake.calls,
            [(str(app), version,
              {"expect_arches": ("x86_64", "arm64")})],
            "CLI/check_app changed the version or architecture contract")

    def test_missing_arches_fails_before_validator_delegation(self):
        app, _leaf = self.make_app()
        fake = FakeClaudePet()
        with mock.patch.object(verify_release_artifact, "_load_app",
                               return_value=fake):
            rc = verify_release_artifact.main([
                "app", str(app), "--expect-version", "0.20",
            ])
        self.assertEqual((rc, fake.calls), (1, []))

    def test_missing_file_or_symlink_app_is_rejected_before_validator(self):
        real_app, _leaf = self.make_app("real-ClaudePet.app")
        regular_file = self.td / "file-ClaudePet.app"
        regular_file.write_bytes(b"not an app directory")
        symlink_app = self.td / "linked-ClaudePet.app"
        os.symlink(real_app, symlink_app)
        cases = {
            "missing": self.td / "missing-ClaudePet.app",
            "regular-file": regular_file,
            "symlink": symlink_app,
        }

        for label, app in cases.items():
            with self.subTest(label=label):
                result, fake = self.check_with_fake(app)
                self.assertEqual(
                    (result, fake.calls), (False, []),
                    "an invalid app root reached validate_update_app")

    def test_code_leaf_must_be_regular_present_and_not_a_symlink(self):
        for kind in ("missing", "directory", "symlink"):
            with self.subTest(kind=kind):
                app, leaf = self.make_app("%s-ClaudePet.app" % kind,
                                          code=kind)
                if kind == "symlink":
                    self.assertTrue(leaf.is_symlink())
                result, fake = self.check_with_fake(app)
                self.assertEqual(
                    (result, fake.calls), (False, []),
                    "a %s code leaf reached the updater validator" % kind)

    def test_stale_regular_code_leaf_is_rejected_before_validator(self):
        app, leaf = self.make_app(code="stale")
        self.assertTrue(leaf.is_file() and not leaf.is_symlink())
        self.assertNotEqual(sha256(leaf), sha256(CHECKOUT_SOURCE),
                            "stale fixture accidentally matches checkout")

        result, fake = self.check_with_fake(app)

        self.assertEqual(
            (result, fake.calls), (False, []),
            "a regular but stale bundled claude_pet.py passed the release gate")

    def test_exact_checkout_code_leaf_reaches_validator(self):
        app, leaf = self.make_app()
        self.assertTrue(leaf.is_file() and not leaf.is_symlink())
        self.assertEqual(sha256(leaf), sha256(CHECKOUT_SOURCE))

        result, fake = self.check_with_fake(
            app, version="0.20", arches=("arm64", "x86_64"))

        self.assertTrue(result)
        self.assertEqual(
            fake.calls,
            [(str(app), "0.20",
              {"expect_arches": ("arm64", "x86_64")})])


if __name__ == "__main__":
    unittest.main()
