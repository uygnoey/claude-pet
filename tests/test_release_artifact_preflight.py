"""Temp-only gates for release-artifact application preflight.

The subject is ``verify_release_artifact`` delegation and its local code-leaf
check.  Signing/notarization is represented by a fake ``validate_update_app``;
no signing tool, release shell, installed application, or external path is
ever invoked.

Staged v0.24 (Verifier verifier-v024, 2026-09-12): the gate also refuses a bundle
without ``Contents/Resources/fonts/Pretendard-SemiBold.ttf`` (a regular file whose
first four bytes are the TrueType magic ``00 01 00 00``; round 3 replaced the CFF
``.otf``, whose ``OTTO`` magic is now refused) and ``LICENSE-Pretendard.txt``.  The app falls back
to the system font *silently* when the file is missing, and a signature says who
built the bundle, not what is inside, so this is the only place a py2app resource
regression would be caught.  The fixture font is a four-byte magic plus padding —
nothing is copied from ``fonts/``.
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

    FONT_FILE = "Pretendard-SemiBold.ttf"
    LICENCE_FILE = "LICENSE-Pretendard.txt"
    TRUETYPE = b"\x00\x01\x00\x00" + b"\0" * 60     # sfnt 1.0 magic, then padding
    CFF = b"OTTO" + b"\0" * 60                       # the round-2 build, refused since round 3

    def make_app(self, name="ClaudePet.app", code="checkout", fonts="ok"):
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
        self.make_fonts(resources, fonts)
        return app, leaf

    def make_fonts(self, resources, fonts):
        """``fonts`` names one shape of Contents/Resources/fonts; never the repo's file."""
        folder = resources / "fonts"
        font = folder / self.FONT_FILE
        licence = folder / self.LICENCE_FILE
        if fonts == "absent-dir":
            return
        folder.mkdir()
        if fonts == "ok":
            font.write_bytes(self.TRUETYPE)
            licence.write_text("SIL Open Font License 1.1 (stub)\n", encoding="utf-8")
        elif fonts == "no-font":
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "no-licence":
            font.write_bytes(self.TRUETYPE)
        elif fonts == "cff":
            font.write_bytes(self.CFF)
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "otf-only":
            # the round-2 bundle: the CFF file under its old name, no .ttf at all
            (folder / "Pretendard-SemiBold.otf").write_bytes(self.CFF)
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "ttf-bytes-under-otf-name":
            (folder / "Pretendard-SemiBold.otf").write_bytes(self.TRUETYPE)
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "empty":
            font.write_bytes(b"")
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "font-is-dir":
            font.mkdir()
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "font-symlink":
            target = self.td / (resources.parent.parent.name + "-real-font.ttf")
            target.write_bytes(self.TRUETYPE)
            os.symlink(target, font)
            licence.write_text("stub\n", encoding="utf-8")
        elif fonts == "licence-symlink":
            font.write_bytes(self.TRUETYPE)
            target = self.td / (resources.parent.parent.name + "-real-licence.txt")
            target.write_text("stub\n", encoding="utf-8")
            os.symlink(target, licence)
        else:
            raise ValueError(fonts)

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

    def test_bundle_without_the_font_or_with_a_non_truetype_file_is_rejected_before_validator(self):
        """Rivals: no font check at all (the pre-change gate — every shape below
        reached the validator and passed); an ``exists`` check that accepts a
        directory, a symlink or a 0-byte placeholder; the round-2 gate (``OTTO``
        magic under the ``.otf`` name — it accepts ``cff`` here and, together with
        the positive control in the next test, is separated from a gate that refuses
        everything); a magic check that accepts any bytes under the ``.ttf`` name;
        the licence not required."""
        shapes = ("absent-dir", "no-font", "no-licence", "cff", "otf-only",
                  "ttf-bytes-under-otf-name", "empty", "font-is-dir", "font-symlink",
                  "licence-symlink")
        for shape in shapes:
            with self.subTest(fonts=shape):
                app, leaf = self.make_app("%s-ClaudePet.app" % shape, fonts=shape)
                self.assertEqual(sha256(leaf), sha256(CHECKOUT_SOURCE),
                                 "the code leaf is valid, so only the font can refuse")
                result, fake = self.check_with_fake(app)
                self.assertEqual(
                    (result, fake.calls), (False, []),
                    "a bundle with fonts/%s reached the updater validator" % shape)

    def test_font_check_runs_after_the_code_leaf_check_and_needs_only_the_magic(self):
        """The two local checks are independent gates: stale code is refused even with
        a perfect fonts/ folder, and a valid font is judged by its first four bytes
        alone (the fixture is not the real 2.6 MB file), so the gate cannot depend on
        the repository's ``fonts/`` being present on the build machine."""
        app, _leaf = self.make_app("stale-fonts-ok-ClaudePet.app", code="stale", fonts="ok")
        self.assertEqual(self.check_with_fake(app)[0], False)
        app, _leaf = self.make_app("ok-ClaudePet.app", fonts="ok")
        font = app / "Contents" / "Resources" / self.FONT_FILE
        self.assertFalse(font.exists(), "the font must live under Resources/fonts, not Resources")
        result, fake = self.check_with_fake(app)
        self.assertEqual((result, len(fake.calls)), (True, 1))


if __name__ == "__main__":
    unittest.main()
