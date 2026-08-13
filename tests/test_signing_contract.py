"""Live contract tests for the commands we hand to the macOS signing tools.

These exist because a mocked `subprocess.run` cannot validate an *argument*.
`CODESIGN_REQUIREMENT` was once written without its leading `=` and without
quotes around the OU; `codesign` then read the whole string as a file path and
answered `invalid requirement specification` — i.e. it rejected every bundle
including ours — while the mocked tests stayed green, because the mock returned
the return code we had assumed.

So every test here runs the real binary against a real bundle, and each one
asserts something that **discriminates**: a check that accepts everything would
pass a return-code-only test exactly like a correct one does. The specific
traps, all found live rather than reasoned about:

  · `codesign -R`  — rejects a foreign signature, so rc alone is meaningful.
  · `spctl`        — **accepts Chrome too** (also a Notarized Developer ID app),
                     so rc=0 and even `source=Notarized Developer ID` prove
                     nothing about *who* signed it. Only the origin Team does.
  · `stapler`      — likewise rc=0 for Chrome; it proves a ticket is stapled,
                     not whose ticket.

When a prerequisite is missing a test skips **loudly** — printing to stderr as
well as calling skipTest — because a silent skip on a contract test is
indistinguishable from coverage.

    python3 -m unittest tests.test_signing_contract -v
"""

import os
import plistlib
import subprocess
import sys
import unittest

import claude_pet


CODESIGN = "/usr/bin/codesign"
SPCTL = "/usr/sbin/spctl"
XCRUN = "/usr/bin/xcrun"
INSTALLED_APP = "/Applications/ClaudePet.app"
# Signed by someone else and *also* notarized — the case that makes a
# return-code-only assertion useless.
FOREIGN_NOTARIZED_APP = "/Applications/Google Chrome.app"
# Apple-signed: used to check the requirement string's syntax even when neither
# of the above is installed.
APPLE_APP = "/System/Applications/Calculator.app"


def _skip_loudly(test, why):
    print(f"\n[signing-contract] SKIPPED: {why}", file=sys.stderr, flush=True)
    test.skipTest(why)


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def _need(test, path, what):
    if not os.path.exists(path):
        _skip_loudly(test, f"{what} is not present at {path}")


def _need_our_signed_app(test):
    _need(test, INSTALLED_APP, "the installed app")
    if _run([CODESIGN, "--verify", INSTALLED_APP]).returncode != 0:
        _skip_loudly(test, f"{INSTALLED_APP} is not validly signed "
                           "(a local unsigned build?)")


class CodesignRequirementContractTests(unittest.TestCase):
    def setUp(self):
        _need(self, CODESIGN, "codesign")

    def test_requirement_is_parsed_as_a_requirement_not_a_filename(self):
        """The exact failure that shipped: codesign reading it as a path."""
        _need(self, APPLE_APP, "an Apple-signed bundle")
        result = _run([CODESIGN, "--verify", "--deep", "--strict",
                       "-R", claude_pet.CODESIGN_REQUIREMENT, APPLE_APP])
        combined = (result.stderr or "") + (result.stdout or "")
        self.assertNotIn("invalid requirement specification", combined)
        self.assertNotIn("No such file or directory", combined)

    def test_requirement_rejects_a_bundle_signed_by_someone_else(self):
        """A requirement that accepted everything would also return 0 here."""
        _need(self, APPLE_APP, "an Apple-signed bundle")
        result = _run([CODESIGN, "--verify", "--deep", "--strict",
                       "-R", claude_pet.CODESIGN_REQUIREMENT, APPLE_APP])
        self.assertNotEqual(result.returncode, 0,
                            "the pinned requirement accepted Apple's signature")

    def test_requirement_rejects_another_developer_id_signature(self):
        """Closer case: a real third-party Developer ID, not Apple's own."""
        _need(self, FOREIGN_NOTARIZED_APP, "a third-party notarized app")
        result = _run([CODESIGN, "--verify", "--deep", "--strict",
                       "-R", claude_pet.CODESIGN_REQUIREMENT,
                       FOREIGN_NOTARIZED_APP])
        self.assertNotEqual(
            result.returncode, 0,
            "the pinned requirement accepted another developer's signature")

    def test_requirement_accepts_our_own_signed_app(self):
        _need_our_signed_app(self)
        result = _run([CODESIGN, "--verify", "--deep", "--strict",
                       "-R", claude_pet.CODESIGN_REQUIREMENT, INSTALLED_APP])
        self.assertEqual(
            result.returncode, 0,
            "our own signed app failed the pinned requirement: "
            f"{(result.stderr or '').strip()!r}")


class GatekeeperAssessmentContractTests(unittest.TestCase):
    """`spctl --assess --type execute -vv` — note the flags are load-bearing.

    Without an explicit `--type execute` spctl assesses under a different
    policy, and without `-vv` it prints no origin, which is the only part of
    the output that identifies *who* signed the thing.
    """

    def setUp(self):
        _need(self, SPCTL, "spctl")

    def test_assessment_reports_notarization_and_our_team_for_our_app(self):
        _need_our_signed_app(self)
        result = _run([SPCTL, "--assess", "--type", "execute", "-vv",
                       INSTALLED_APP])
        combined = (result.stderr or "") + (result.stdout or "")
        self.assertNotIn("Usage:", combined, "spctl rejected our arguments")
        if result.returncode != 0:
            _skip_loudly(self, "the installed app is not notarized "
                               f"({combined.strip()!r}); the argument contract "
                               "still held")
        self.assertIn("source=Notarized Developer ID", combined)
        self.assertIn(claude_pet.TEAM_ID, combined,
                      "spctl did not attribute the app to our team")

    def test_assessment_alone_does_not_identify_the_signer(self):
        """Why the team check above matters: spctl accepts other vendors too."""
        _need(self, FOREIGN_NOTARIZED_APP, "a third-party notarized app")
        result = _run([SPCTL, "--assess", "--type", "execute", "-vv",
                       FOREIGN_NOTARIZED_APP])
        combined = (result.stderr or "") + (result.stdout or "")
        if result.returncode != 0:
            _skip_loudly(self, "the third-party app is not accepted here; "
                               "cannot demonstrate the distinction")
        self.assertNotIn(
            claude_pet.TEAM_ID, combined,
            "a third-party app was attributed to our team — the origin line "
            "cannot be used to identify the signer")


class StaplerContractTests(unittest.TestCase):
    """`xcrun stapler validate` — `stapler` is not on PATH without `xcrun`."""

    def setUp(self):
        _need(self, XCRUN, "xcrun")
        _need_our_signed_app(self)

    def test_stapler_validates_the_installed_app(self):
        result = _run([XCRUN, "stapler", "validate", INSTALLED_APP])
        combined = (result.stderr or "") + (result.stdout or "")
        if result.returncode != 0:
            _skip_loudly(self, "the installed app has no stapled ticket "
                               f"({combined.strip()!r})")
        self.assertIn("The validate action worked", combined)

    def test_stapler_rejects_a_bundle_with_no_stapled_ticket(self):
        """Discrimination: stapler must fail on something unstapled."""
        _need(self, APPLE_APP, "an Apple-signed bundle")
        result = _run([XCRUN, "stapler", "validate", APPLE_APP])
        self.assertNotEqual(
            result.returncode, 0,
            "stapler reported success for a bundle with no notarization "
            "ticket — the check cannot distinguish stapled from unstapled")


class ValidateUpdateAppLiveTests(unittest.TestCase):
    def test_the_real_installed_app_passes_the_whole_preflight(self):
        """End-to-end, unmocked: the path a real update actually takes."""
        _need(self, CODESIGN, "codesign")
        _need(self, SPCTL, "spctl")
        _need_our_signed_app(self)
        if _run([SPCTL, "--assess", "--type", "execute",
                 INSTALLED_APP]).returncode != 0:
            _skip_loudly(self, f"{INSTALLED_APP} is not notarized")
        with open(os.path.join(INSTALLED_APP, "Contents", "Info.plist"),
                  "rb") as plist_file:
            info = plistlib.load(plist_file)
        short_version = info.get("CFBundleShortVersionString")
        bundle_version = info.get("CFBundleVersion")
        self.assertIsInstance(short_version, str)
        self.assertTrue(short_version.strip(),
                        "installed app has a blank short version")
        self.assertEqual(
            short_version, bundle_version,
            "installed app's two bundle version keys disagree")
        self.assertTrue(
            claude_pet.validate_update_app(INSTALLED_APP, short_version),
            "validate_update_app rejected our own signed, notarized app; "
            "every future update would be refused")


if __name__ == "__main__":
    unittest.main()
