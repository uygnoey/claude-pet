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
    """The app module as ``check_app`` sees it.

    The logo constants are part of that surface since v0.26: ``check_app`` reads
    ``SUMMARY_LOGO_DIR`` and refuses outright when it is absent, and it cross-checks the
    value against its own ``LOGO_DIR`` so a moved directory cannot make the gate silently
    follow along. A fake without them therefore fails every test in this module for a
    reason that has nothing to do with what the test is asking — which is what happened
    when the marks landed.

    The values mirror the real module deliberately; a mismatch here would exercise the
    gate's *disagreement* branch in every test rather than the one that targets it.
    """

    def __init__(self, verdict=True, logo_dir="logos",
                 logo_files=None):
        self.verdict = verdict
        self.calls = []
        self.SUMMARY_LOGO_DIR = logo_dir
        self.SUMMARY_LOGO_FILES = (
            {"claude": "claude.svg", "codex": "openai.svg"}
            if logo_files is None else logo_files)

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

    SVG_STUB = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>\n'

    def make_app(self, name="ClaudePet.app", code="checkout", fonts="ok", logos="ok"):
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
        self.make_logos(resources, logos)
        return app, leaf

    def make_logos(self, resources, logos):
        """``logos`` names one shape of Contents/Resources/logos; never the repo's files.

        Same rule as ``make_fonts``: the bytes are stubs, so this module never depends on
        what is actually sitting in the checkout's ``logos/``.
        """
        if logos == "absent-dir":
            return
        folder = resources / "logos"
        folder.mkdir()
        if logos == "empty":
            return
        names = FakeClaudePet().SUMMARY_LOGO_FILES
        if logos == "ok":
            for filename in names.values():
                (folder / filename).write_bytes(self.SVG_STUB)
        elif logos == "one-missing":
            (folder / names["claude"]).write_bytes(self.SVG_STUB)
        elif logos == "not-svg":
            for filename in names.values():
                (folder / filename).write_bytes(b"\x89PNG\r\n\x1a\n")
        elif logos == "symlink":
            target = resources.parent / "real-logo.svg"
            target.write_bytes(self.SVG_STUB)
            for filename in names.values():
                os.symlink(target, folder / filename)
        else:
            raise ValueError(logos)

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

    def test_the_logo_check_refuses_every_broken_shape_before_the_validator(self):
        """The provider marks get the same treatment as the font, and for the same
        reason: a bundle can lose them while a from-source run stays perfect, so the
        gate is the only place the loss is visible.

        Each shape is refused **before** ``validate_update_app`` is reached — a local
        check that runs after the delegated one would let a bad bundle be judged by a
        validator that knows nothing about logos.

        Rivals this separates: the directory missing entirely; it existing but empty;
        one of the two marks present and the other not (the asymmetric case a
        ``len(files) > 0`` check would pass); a file that is not an SVG at all, which is
        how a stray placeholder ships; and a symlink, which ``ditto`` may not carry into
        the artifact even when it resolves on the build machine.
        """
        for shape in ("absent-dir", "empty", "one-missing", "not-svg", "symlink"):
            with self.subTest(logos=shape):
                app, _leaf = self.make_app(f"logos-{shape}-ClaudePet.app", logos=shape)
                result, fake = self.check_with_fake(app)
                self.assertEqual(
                    result, False,
                    f"the gate accepted an artifact whose logos are {shape!r}")
                self.assertEqual(
                    fake.calls, [],
                    "the logo check must refuse before validate_update_app is called")

    def test_an_empty_logo_table_is_refused_rather_than_passing_vacuously(self):
        """``SUMMARY_LOGO_FILES`` 가 비면 로고 루프가 **한 번도 돌지 않고** 통과한다.

        `for provider, name in sorted(...items()):` 는 빈 매핑에서 아무것도 하지 않으므로,
        마크가 하나도 없는 아티팩트가 로고 검사를 '통과'한다. 빈 `logos/` 디렉터리까지
        같이 있으면 게이트 전체가 초록이다 — Reviewer 가 실제로 `check_app` 을 돌려
        `True` 를 받았다.

        오늘은 상수가 비어 있지 않아 도달 불가다. 그래도 거는 이유는 이 파일의 존재
        이유가 **fail-closed** 이기 때문이다: 검사할 것이 없다는 사실이 통과의 근거가
        되어서는 안 된다. 같은 모양의 공허한 통과가 이 릴리즈에서만 두 번 나왔다(죽은
        `str.replace` 바늘, 그리고 이것).

        Rival: 루프만 있고 비어 있음을 확인하지 않는 지금 구현.
        """
        app, _leaf = self.make_app("empty-logo-table-ClaudePet.app", logos="empty")
        fake = FakeClaudePet(logo_files={})
        with mock.patch.object(verify_release_artifact, "_load_app", return_value=fake):
            result = verify_release_artifact.check_app(str(app), "9.9", ["arm64"])
        self.assertEqual(
            result, False,
            "빈 로고 표 + 빈 logos/ 가 게이트를 통과했다 — 검사할 것이 없다는 것이 "
            "통과의 근거가 되면 그 검사는 존재하지 않는 것과 같다")
        self.assertEqual(fake.calls, [],
                         "빈 표는 validate_update_app 에 닿기 전에 막혀야 한다")

    def test_a_moved_logo_directory_is_refused_rather_than_followed(self):
        """``check_app`` cross-checks the app's ``SUMMARY_LOGO_DIR`` against its own
        ``LOGO_DIR``. Without that, moving the directory would make the gate follow the
        app silently and "the gate checks the logos" would quietly become an empty
        sentence — it would be looking wherever the app pointed it, including nowhere.

        Rivals: a gate that trusts the constant (follows the move, checks a directory
        that is always present and therefore always passes); a gate that ignores the
        constant and hardcodes the path (misses a deliberate rename and blocks forever).
        """
        app, _leaf = self.make_app("moved-logos-ClaudePet.app", logos="ok")
        fake = FakeClaudePet(logo_dir="marks")
        with mock.patch.object(verify_release_artifact, "_load_app", return_value=fake):
            moved = verify_release_artifact.check_app(str(app), "9.9", ["arm64"])
        self.assertEqual(moved, False, "a moved logo directory must be refused")
        self.assertEqual(fake.calls, [], "the disagreement must stop the gate early")


if __name__ == "__main__":
    unittest.main()
