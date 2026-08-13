"""Safe behavioural tests for the zsh source guards.

The production scripts contain destructive and credential-bearing dispatch arms.
These tests never run those arms.  Each script is copied to a temporary directory
and its bottom dispatch is replaced, exactly once, with a case that only appends a
marker.  The function definitions and the real guard remain unchanged.

The resulting fixture distinguishes all three relevant behaviours:

* sourcing the guarded script returns normally without reaching the marker;
* executing the guarded script reaches the marker exactly once; and
* sourcing the same fixture after deleting exactly the guard line reaches the
  marker exactly once.

No git history, repository artifact, application bundle, build tool, signing tool,
or network command is involved.
"""

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "build_app.sh": {
        "dispatch": 'case "$1" in',
        "functions": ("write_plist", "copy_pet_assets", "build", "sign_app"),
    },
    "release.sh": {
        "dispatch": 'case "${1:-}" in',
        "functions": ("verify_bundled_pet_payload", "verify_upload_artifact",
                      "build", "publish"),
    },
}
GUARD = 'case "${ZSH_EVAL_CONTEXT}" in *:file*) return 0 ;; esac'
SENTINEL = "__SOURCE_RETURNED__"
FUNCTIONS_SENTINEL = "__FUNCTIONS_DEFINED__"


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(tempfile.mkdtemp(prefix="source-guard-")).resolve()
        self.addCleanup(shutil.rmtree, self.temp_root, ignore_errors=True)

    def _instrumented_copy(self, name, *, remove_guard=False):
        """Copy *name* with only its bottom dispatch changed to a marker."""
        source = (REPO / name).read_text()
        dispatch = SCRIPTS[name]["dispatch"]
        dispatch_line = f"\n{dispatch}\n"
        self.assertEqual(
            source.count(dispatch_line), 1,
            f"{name}: bottom dispatch anchor must occur exactly once",
        )

        prefix, original_dispatch = source.split(dispatch_line, 1)
        self.assertTrue(
            original_dispatch.rstrip().endswith("esac"),
            f"{name}: dispatch is no longer the final shell construct",
        )
        marker_dispatch = (
            '\ncase "${1:-}" in\n'
            '  *) printf "%s\\n" dispatch '
            '>> "$CLAUDE_PET_GUARD_MARKER" ;;\n'
            'esac\n'
        )
        instrumented = prefix + marker_dispatch

        self.assertEqual(instrumented.count(GUARD), 1,
                         f"{name}: source guard must occur exactly once")
        if remove_guard:
            instrumented = instrumented.replace(GUARD, "", 1)
            self.assertNotIn(GUARD, instrumented)

        box = self.temp_root / f"{name}-{'unguarded' if remove_guard else 'guarded'}"
        box.mkdir()
        script = box / name
        script.write_text(instrumented)
        script.chmod(0o755)

        # Top-level initialization reads these files before it reaches the guard.
        (box / "claude_pet.py").write_text('APP_VERSION = "0.0"\n')
        (box / "home").mkdir()
        (box / "tmp").mkdir()
        (box / "zdot").mkdir()
        return box, script

    def _environment(self, box, marker):
        """A minimal, sandbox-local environment; inherit no user tool settings."""
        return {
            "PATH": "/usr/bin:/bin",
            "HOME": str(box / "home"),
            "TMPDIR": f"{box / 'tmp'}/",
            "ZDOTDIR": str(box / "zdot"),
            "CDPATH": "",
            "LC_ALL": "C",
            "CLAUDE_PET_GUARD_MARKER": str(marker),
        }

    def _run(self, box, marker, command):
        return subprocess.run(
            ["/bin/zsh", "-f", "-c",
             f"setopt FUNCTION_ARGZERO; {command}"],
            cwd=box,
            env=self._environment(box, marker),
            capture_output=True,
            text=True,
            timeout=10,
        )

    def _marker_count(self, marker):
        if not marker.exists():
            return 0
        return marker.read_text().splitlines().count("dispatch")

    def _source_command(self, script, functions):
        checks = "; ".join(
            f"typeset -f {shlex.quote(function)} >/dev/null || exit 91"
            for function in functions
        )
        return (
            f"source {shlex.quote(str(script))}; source_rc=$?; "
            f"{checks}; "
            f"printf '%s\\n' {shlex.quote(FUNCTIONS_SENTINEL)}; "
            f"printf '%s\\n' {shlex.quote(SENTINEL)}; "
            'printf "SOURCE_RC=%s\\n" "$source_rc"; '
            'printf "CWD=%s\\n" "${PWD:A}"'
        )

    def _assert_successful_source(self, result, box):
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn(FUNCTIONS_SENTINEL, lines)
        self.assertIn(SENTINEL, lines)
        self.assertIn("SOURCE_RC=0", lines)
        self.assertIn(f"CWD={box}", lines)

    def test_guarded_source_is_inert_and_defines_functions(self):
        for name, contract in SCRIPTS.items():
            with self.subTest(script=name):
                box, script = self._instrumented_copy(name)
                marker = box / "marker.log"
                command = self._source_command(script, contract["functions"])
                result = self._run(box, marker, command)

                self._assert_successful_source(result, box)
                self.assertEqual(self._marker_count(marker), 0)

    def test_direct_execution_reaches_dispatch_exactly_once(self):
        for name in SCRIPTS:
            with self.subTest(script=name):
                box, script = self._instrumented_copy(name)
                marker = box / "marker.log"
                result = self._run(
                    box, marker,
                    f"{shlex.quote(str(script))} __guardcheck__",
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self._marker_count(marker), 1)

    def test_removing_the_guard_makes_source_reach_dispatch_once(self):
        for name, contract in SCRIPTS.items():
            with self.subTest(script=name):
                box, script = self._instrumented_copy(name, remove_guard=True)
                marker = box / "marker.log"
                command = self._source_command(script, contract["functions"])
                result = self._run(box, marker, command)

                self._assert_successful_source(result, box)
                self.assertEqual(self._marker_count(marker), 1)


if __name__ == "__main__":
    unittest.main()
