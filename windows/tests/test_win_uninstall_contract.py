"""Closing-round gates for the Windows uninstall contract (Track F, B2/B3/N5/N6, 2026-09-14).

Run from the worktree root:

    python3 -m unittest discover -s windows/tests -t . -v

Verifier-owned (AGENTS.md §2 Condition A). The Developer owns
``windows/win_update.py``, ``windows/claude_pet_win.py``,
``windows/build_win.py``, ``windows/installer.iss`` and ``windows/README.md``,
and must not touch an assertion, an expected value or a fixture literal here.

This is a **new** file rather than an addition to
``windows/tests/test_win_hardware_fixes.py`` because that file's SHA256 is
pinned in ``docs-design/track-f-verification-20260914.md``; a gate added inside
it would invalidate the pin it is recorded under.

─────────────────────────── why this file exists ───────────────────────────

**B2 — the two uninstall-helper builders were gated by nothing.**
``grep -rln 'build_inno_uninstall_script\\|build_uninstall_script' windows/tests/``
returned no file before this one. The in-app ordering *looked* covered by
``test_win_hardware_fixes.InAppInnoUninstallOrderTests``, but both of its
ordering tests open with

    if self._pid_wait():
        self.skipTest(...)

and ``_pid_wait()`` is ``any(name == "getpid" for _ln, name, _n in
self._branch_calls())`` — satisfied by *any* implementation that passes
``os.getpid()`` to *any* callee, including one that hands it to a helper which
never waits. The suite then reports ``OK (skipped=2)``. **This file supersedes
those two tests**: it re-states the same obligation with no self-skip
predicate, and it closes the hole the predicate left by gating the generated
helper text itself, so "the pid was handed over" and "the helper waits on it"
are two separate, separately-failing assertions rather than one assumption.

**B3 (second half) — the real ordering rivals in ``installer.iss``.**
The retired assertion was ``assertNotIn("postuninstall", flags)``, which is
vacuous: ``postuninstall`` is not an Inno Setup flag at all (it is absent from
the Flags list of https://jrsoftware.org/ishelp/topic_runsection.htm), so no
``.iss`` that ``ISCC`` compiles can carry it and no implementation this suite
could be handed would ever fail that check. The flags that *can* break the
entry are the three that remove Inno's documented ``waituntilterminated``
default — ``nowait``, ``shellexec``, ``waituntilidle`` — after which file
deletion begins before ``taskkill`` returns while the step order in the
uninstall log looks unchanged. Those are pinned here instead.

**N5** — the single-source property between ``build_win.VERSION_STRINGS`` and
the resource file ``write_version_resource`` emits was documented and ungated;
a generator that hand-copied the table back into its own f-string would pass
every existing test, because the existing gate hard-codes its own copy of the
expected strings (``FIXED_STRINGS``) and so shares the fault it is meant to
catch. Gated here by mutating the source table and requiring the output to
follow.

**N6** — ``skipifdoesntexist`` requires an absolute ``Filename``. Documented,
satisfied by ``{sys}\\taskkill.exe``, previously unchecked. One assertion here.

─────────────────────────── the rival seam ───────────────────────────

Red-before-green (AGENTS.md §3) needs these assertions run against
implementations that are *wrong*, and neither ``windows/win_update.py`` nor
``windows/claude_pet_win.py`` nor ``windows/installer.iss`` may be edited to
produce them. So every source this file reads — module or text — is resolved
through ``_src()`` / ``_wu()`` / ``_bw()``, which consult
``CLAUDE_PET_WIN_RIVAL_ROOT``: a scratch mirror holding a deliberately broken
copy of one file. The variable is **unset in the suite**, so a plain
``python3 -m unittest discover -s windows/tests -t .`` gates the working tree
unconditionally — there is no branch here that a normal run can take.

Two instruments protect the rival runs from being silently vacuous:

* setting the variable prints a banner to stderr, so a rival run can never be
  mistaken for a real one in a transcript;
* ``_wu()`` / ``_bw()`` / ``_src()`` **raise** if the mirror is set and the
  file they returned is not the mirror's copy. A rival run that silently read
  the worktree would otherwise pass and be recorded as a discrimination.

─────────────────────────── truth tables ───────────────────────────

Every class below carries the AGENTS.md §3 table for its own fixtures. The
rivals are named R1–R5 / P1–P3 / I1–I5 and each one is a real scratch file the
verification record shows failing.
"""

import ast
import importlib
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# The scratch mirror, or "". Unset in the suite; see the module docstring.
RIVAL_ROOT = os.environ.get("CLAUDE_PET_WIN_RIVAL_ROOT", "").strip()

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if RIVAL_ROOT:
    # Ahead of ROOT, and ahead of the cwd `python -m` puts at sys.path[0]:
    # `windows` is a namespace package, so its __path__ follows sys.path order
    # and recomputes when sys.path changes.
    while RIVAL_ROOT in sys.path:
        sys.path.remove(RIVAL_ROOT)
    sys.path.insert(0, RIVAL_ROOT)
    importlib.invalidate_caches()
    sys.stderr.write(
        "\n*** RIVAL RUN — CLAUDE_PET_WIN_RIVAL_ROOT=%s ***\n"
        "*** these results gate a scratch copy, NOT the working tree ***\n\n" % RIVAL_ROOT)
    sys.stderr.flush()


def _src(rel):
    """Path to a source file: the mirror's copy when it has one, else the worktree's."""
    if RIVAL_ROOT:
        cand = os.path.join(RIVAL_ROOT, rel)
        if os.path.exists(cand):
            return cand
    return os.path.join(ROOT, rel)


def _mirrored(mod_or_path, rel):
    """Fail loudly when a rival run silently read the worktree instead of the mirror."""
    if not RIVAL_ROOT:
        return mod_or_path
    got = getattr(mod_or_path, "__file__", mod_or_path)
    if os.path.exists(os.path.join(RIVAL_ROOT, rel)) and not os.path.abspath(got).startswith(
            os.path.abspath(RIVAL_ROOT) + os.sep):
        raise RuntimeError(
            "rival run is vacuous: %s resolved to %s, not to the mirror copy at %s"
            % (rel, got, os.path.join(RIVAL_ROOT, rel)))
    return mod_or_path


def _wu():
    return _mirrored(importlib.import_module("windows.win_update"), "windows/win_update.py")


def _bw():
    return _mirrored(importlib.import_module("windows.build_win"), "windows/build_win.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


ISS = _src("windows/installer.iss")
PORT = _src("windows/claude_pet_win.py")


# ═══════════════════════════════════════════════════════════════════════════════
# helpers — PowerShell text
# ═══════════════════════════════════════════════════════════════════════════════

# A PowerShell single-quoted string: anything but a quote, or a doubled quote.
_PS_STRING = re.compile(r"'(?:[^']|'')*'")

# Anything that touches the machine. Ordering is stated over this set, so a
# rival that moves any one of them ahead of the wait fails, not just the launch.
_ACTIONS = ("Start-Process", "Remove-Item", "Rename-Item", "Stop-Process", "Move-Item",
            "New-Item", "Copy-Item", "Expand-Archive")


def _outside_quotes(text):
    """``text`` with every single-quoted span blanked — what PowerShell would
    treat as code rather than as a literal."""
    return _PS_STRING.sub("''", text)


def _ps_code(line):
    """One line of the generated helper, reduced to what PowerShell would
    actually **execute**: any trailing ``#`` comment removed.

    B4. Every text assertion below used to read the raw line, and
    ``_outside_quotes`` only separates *quoted* from *unquoted* — not *code*
    from *comment*. So a helper whose wait, or whose still-alive refusal, is
    present but **commented out** satisfied every one of them: the substring
    ``Wait-Process`` is still on the line, the pid and the ``-Timeout`` are
    still in the comment, and nothing waits. That is rival MR6 / MR8, and it
    is the shape the regression actually arrives in ("commented out while
    debugging"). Routing the scans through this function is what makes those
    two fail.

    The ``#`` is located on a length-preserving mask of the line — each quoted
    span replaced by as many spaces — so a ``#`` *inside* a quoted path is not
    mistaken for a comment, and the slice index still refers to the real line.
    (Blanking the spans to a shorter ``''`` instead would shift the index left
    and could cut live code off a line that quotes a path before its comment.)
    """
    masked = _PS_STRING.sub(lambda m: " " * len(m.group(0)), line)
    i = masked.find("#")
    return line[:i] if i >= 0 else line


def _first(lines, needle, start=0):
    """Index of the first line at or after ``start`` whose *code* contains
    ``needle``, or -1. Commented-out occurrences do not count (``_ps_code``)."""
    for i in range(start, len(lines)):
        if needle in _ps_code(lines[i]):
            return i
    return -1


# ═══════════════════════════════════════════════════════════════════════════════
# helpers — Python AST
# ═══════════════════════════════════════════════════════════════════════════════

def _func_def(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return n
    return None


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _calls(node):
    """Every Call under ``node`` as ``(lineno, name, call_node)``."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            out.append((n.lineno, _call_name(n), n))
    return out


def _calls_in(stmts):
    out = []
    for s in stmts:
        out.extend(_calls(s))
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# helpers — installer.iss
# ═══════════════════════════════════════════════════════════════════════════════

def _iss_sections(text):
    """``{section name: [entry line, ...]}`` — comments and blanks dropped."""
    out, cur = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            out.setdefault(cur, [])
            continue
        if cur is not None:
            out[cur].append(line)
    return out


def _iss_params(entry):
    """``Filename: "x"; Flags: a b`` → ``{"Filename": "x", "Flags": "a b"}``.

    Splits on ``;`` outside double quotes, so a parameter value may contain one.
    """
    parts, buf, inq = [], [], False
    for ch in entry:
        if ch == '"':
            inq = not inq
            buf.append(ch)
        elif ch == ";" and not inq:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    out = {}
    for p in parts:
        p = p.strip()
        if not p or ":" not in p:
            continue
        k, v = p.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        out[k.strip()] = v
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# (a) B2 — the two generated uninstall helpers
# ═══════════════════════════════════════════════════════════════════════════════

PID = 424242                       # unlike any pid this host will hold
EXE_SPACE = r"C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe"
EXE_QUOTE = r"C:\Apps\Claude's Pet\unins000.exe"
DIR_SPACE = r"C:\ZZFIXTUREZZ Files\ClaudePet"
DIR_QUOTE = r"C:\Apps\Claude's Pet"


class _HelperTextMixin:
    """Shared assertions over a generated PowerShell helper.

    The contract, stated as an order over ``_ACTIONS`` rather than over the one
    call each builder happens to make, so a rival that reorders *any* machine-
    touching statement ahead of the wait fails:

        nothing in ``_ACTIONS`` ─→ Wait-Process on our pid (bounded timeout)
          ─→ refuse with a non-zero exit if the pid is still alive
            ─→ the builder's own action (launch / remove)

    Every scan below reads ``_ps_code(line)``, not the raw line: a
    commented-out ``Wait-Process`` or a commented-out still-alive check is not
    a wait and not a refusal, and before B4 both satisfied every assertion
    here while the emitted helper raced exactly as it did before the fix.
    """

    def _lines(self, text):
        return text.splitlines()

    def _wait_index(self, lines):
        i = _first(lines, "Wait-Process")
        self.assertGreaterEqual(
            i, 0, "the generated helper never waits for the app to exit:\n" + "\n".join(lines))
        return i

    def assert_waits_on_our_pid(self, text):
        lines = self._lines(text)
        i = self._wait_index(lines)
        line = _ps_code(lines[i])
        self.assertRegex(line, r"Wait-Process\s+(?:[^\n]*\s)?-Id\s+%d\b" % PID,
                         "Wait-Process does not name the app's pid: " + line)
        m = re.search(r"-Timeout\s+(\d+)", line)
        self.assertIsNotNone(m, "the wait is unbounded — no -Timeout: " + line)
        self.assertGreater(int(m.group(1)), 0, "a -Timeout of 0 is not a wait: " + line)

    def assert_nothing_happens_before_the_wait(self, text):
        lines = self._lines(text)
        i = self._wait_index(lines)
        early = [(n, ln) for n, ln in enumerate(lines[:i])
                 if any(a in _outside_quotes(_ps_code(ln)) for a in _ACTIONS)]
        self.assertEqual([], early,
                         "these statements run before the wait, while the pet still holds its "
                         "files open: " + repr(early))

    def _refusal(self, text):
        """``(index, exit code)`` of the still-alive refusal after the wait."""
        lines = self._lines(text)
        i = self._wait_index(lines)
        j = -1
        for n in range(i, len(lines)):
            code = _ps_code(lines[n])
            if "Get-Process" in code and re.search(r"-Id\s+%d\b" % PID, code):
                j = n
                break
        self.assertGreaterEqual(
            j, 0,
            "nothing checks whether the pid is still alive after the wait, so a wait that "
            "times out is indistinguishable from one that succeeded:\n" + "\n".join(lines))
        blob = "\n".join(_ps_code(ln) for ln in lines[j:j + 8])
        m = re.search(r"\bexit\s+(\d+)", blob)
        self.assertIsNotNone(m, "the still-alive branch does not exit:\n" + blob)
        return j, int(m.group(1))

    def assert_refuses_when_still_alive(self, text):
        _j, code = self._refusal(text)
        self.assertNotEqual(0, code,
                            "the helper carries on with exit code 0 while the pet is still "
                            "running — the deletions then hit open files")

    def assert_refusal_code_is_the_documented_two(self, text):
        _j, code = self._refusal(text)
        self.assertEqual(2, code,
                         "2 is the token the update/uninstall log and win_update's own exit-code "
                         "table use for 'the pet never exited'; got %r" % code)

    def assert_action_comes_after_the_refusal(self, text, needle):
        lines = self._lines(text)
        wait_i = self._wait_index(lines)
        refuse_i, _code = self._refusal(text)
        act_i = -1
        for n, ln in enumerate(lines):
            if needle in _outside_quotes(_ps_code(ln)):
                act_i = n
                break
        self.assertGreaterEqual(act_i, 0, "the helper never runs %r at all" % needle)
        self.assertLess(wait_i, act_i,
                        "%r is at line %d, before the wait at line %d" % (needle, act_i, wait_i))
        self.assertLess(refuse_i, act_i,
                        "%r is at line %d, before the still-alive refusal at line %d"
                        % (needle, act_i, refuse_i))


class InnoUninstallHelperTextTests(_HelperTextMixin, unittest.TestCase):
    r"""B2(a) — ``win_update.build_inno_uninstall_script(argv, pid)``.

    The helper exists because launching ``unins000.exe`` from a live pet is the
    race the hardware hit: the uninstaller removes the ARP entry and the Run
    value first, fails on every file the running process holds open, and still
    exits 0 — leaving the folder behind with nothing left to retry from.

    §3 truth table. Fixture: ``argv = [EXE_SPACE, "/SILENT", "/SUPPRESSMSGBOXES"]``,
    ``pid = 424242``. R1–R4 and R6/R8 are scratch copies of
    ``windows/win_update.py`` under the rival root; ✗ marks the cell where the
    rival differs from the working tree, which is the cell the assertion reads.
    R6 and R8 are the two commented-out rivals B4 was raised about: the line is
    still in the text, so every cell below reads it through ``_ps_code``.

    | assertion                          | R1 no wait | R2 no refusal | R3 launch first | R4 raw path | R6 wait commented | R8 refusal commented | **tree** |
    | ---------------------------------- | ---------- | ------------- | --------------- | ----------- | ----------------- | -------------------- | -------- |
    | Wait-Process names the pid, bounded | absent ✗   | present       | present         | present     | comment only ✗    | present              | **present** |
    | nothing acts before the wait        | n/a ✗      | holds         | Start first ✗   | holds       | n/a ✗             | holds                | **holds** |
    | refuses non-zero while alive        | n/a ✗      | absent ✗      | present         | present     | n/a ✗             | comment only ✗       | **exit 2** |
    | refusal code is 2                   | n/a ✗      | absent ✗      | 2               | 2           | n/a ✗             | comment only ✗       | **2**    |
    | launch after wait and refusal       | n/a ✗      | after wait    | before ✗        | after       | n/a ✗             | n/a ✗                | **after** |
    | every path single-quoted            | quoted     | quoted        | quoted          | raw ✗       | quoted            | quoted               | **quoted** |

    No row has the expected value appearing under a rival and under the tree at
    once for *every* column: R1 and R2 are separated by the refusal rows, R2 and
    R3 by the ordering rows, R3 and R4 by the quoting row, and R6/R8 are
    separated from each other by which of the two lines is still executable.
    A single fixture is enough because the six rivals differ in six different
    cells.
    """

    ARGV = [EXE_SPACE, "/SILENT", "/SUPPRESSMSGBOXES"]

    def setUp(self):
        self.wu = _wu()
        self.text = self.wu.build_inno_uninstall_script(list(self.ARGV), PID)

    def test_it_waits_on_the_apps_pid_with_a_bounded_timeout(self):
        self.assert_waits_on_our_pid(self.text)

    def test_nothing_touches_the_machine_before_the_wait(self):
        self.assert_nothing_happens_before_the_wait(self.text)

    def test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive(self):
        self.assert_refuses_when_still_alive(self.text)

    def test_the_refusal_uses_the_documented_exit_code_two(self):
        self.assert_refusal_code_is_the_documented_two(self.text)

    def test_the_uninstaller_is_launched_only_after_the_wait_and_the_refusal(self):
        self.assert_action_comes_after_the_refusal(self.text, "Start-Process")

    def test_every_interpolated_argument_is_single_quoted(self):
        q = self.wu.ps_quote
        for item in self.ARGV:
            self.assertIn(q(item), self.text,
                          "%r does not appear single-quoted in the helper" % item)

    def test_no_interpolated_path_reaches_the_script_as_bare_code(self):
        self.assertNotIn("ZZFIXTUREZZ", _outside_quotes(self.text),
                         "the uninstaller path appears outside any quoted string — a path with a "
                         "space or a metacharacter would be re-parsed by PowerShell:\n" + self.text)

    def test_an_apostrophe_in_the_path_is_doubled_not_escaped(self):
        text = self.wu.build_inno_uninstall_script([EXE_QUOTE, "/SILENT"], PID)
        self.assertIn("Claude''s Pet", text,
                      "a single quote inside the path is not doubled, so it closes the literal")
        self.assertNotIn("Claude\\'s Pet", text,
                         "backslash-escaping is a shell idiom PowerShell does not have")

    def test_the_uninstaller_path_is_checked_before_it_is_launched(self):
        lines = self.text.splitlines()
        test_i = _first(lines, "Test-Path")
        start_i = _first(lines, "Start-Process")
        self.assertGreaterEqual(test_i, 0, "the helper launches without checking the exe is there")
        self.assertLess(test_i, start_i, "the Test-Path guard is after the launch")


class PortableUninstallHelperTextTests(_HelperTextMixin, unittest.TestCase):
    r"""B2(b) — ``win_update.build_uninstall_script(app_dir, pid)``.

    Same wait, different irreversible act: this one removes the install folder,
    so the ordering assertion is read over ``Remove-Item`` of ``app_dir``
    rather than over ``Start-Process``.

    §3 truth table. Fixture: ``app_dir = DIR_SPACE``, ``pid = 424242``.

    | assertion                           | R1 no wait | R2 no refusal | R4 raw path | R6 wait commented | R8 refusal commented | **tree** |
    | ----------------------------------- | ---------- | ------------- | ----------- | ----------------- | -------------------- | -------- |
    | Wait-Process names the pid, bounded  | absent ✗   | present       | present     | comment only ✗    | present              | **present** |
    | nothing acts before the wait         | n/a ✗      | holds         | holds       | n/a ✗             | holds                | **holds** |
    | refuses non-zero while alive         | n/a ✗      | absent ✗      | present     | n/a ✗             | comment only ✗       | **exit 2** |
    | the folder is removed after the wait | n/a ✗      | after wait    | after       | n/a ✗             | n/a ✗                | **after** |
    | every path single-quoted             | quoted     | quoted        | raw ✗       | quoted            | quoted               | **quoted** |

    R3 (launch before the wait) is an inno-only rival — this builder launches
    nothing — so it is absent from this table rather than silently tied. R6 and
    R8 comment the wait / the refusal out in *both* builders, so both classes
    read them.
    """

    def setUp(self):
        self.wu = _wu()
        self.text = self.wu.build_uninstall_script(DIR_SPACE, PID)

    def test_it_waits_on_the_apps_pid_with_a_bounded_timeout(self):
        self.assert_waits_on_our_pid(self.text)

    def test_nothing_touches_the_machine_before_the_wait(self):
        self.assert_nothing_happens_before_the_wait(self.text)

    def test_it_refuses_with_a_non_zero_exit_when_the_pid_is_still_alive(self):
        self.assert_refuses_when_still_alive(self.text)

    def test_the_refusal_uses_the_documented_exit_code_two(self):
        self.assert_refusal_code_is_the_documented_two(self.text)

    def test_the_app_folder_is_removed_only_after_the_wait_and_the_refusal(self):
        self.assert_action_comes_after_the_refusal(self.text, "Remove-Item")

    def test_the_folder_it_removes_is_the_one_it_was_given(self):
        self.assertIn("Remove-Item -LiteralPath " + self.wu.ps_quote(DIR_SPACE), self.text)

    def test_no_interpolated_path_reaches_the_script_as_bare_code(self):
        self.assertNotIn("ZZFIXTUREZZ", _outside_quotes(self.text),
                         "the install folder appears outside any quoted string:\n" + self.text)

    def test_an_apostrophe_in_the_path_is_doubled_not_escaped(self):
        text = self.wu.build_uninstall_script(DIR_QUOTE, PID)
        self.assertIn("Claude''s Pet", text)
        self.assertNotIn("Claude\\'s Pet", text)

    def test_it_removes_nothing_unless_the_folder_still_carries_our_exe_and_marker(self):
        lines = self.text.splitlines()
        guard_i = _first(lines, "Test-Path")
        rm_i = -1
        for n, ln in enumerate(lines):
            if "Remove-Item" in ln and self.wu.ps_quote(DIR_SPACE) in ln:
                rm_i = n
                break
        self.assertGreaterEqual(guard_i, 0, "the helper removes the folder unconditionally")
        self.assertGreaterEqual(rm_i, 0)
        self.assertLess(guard_i, rm_i)
        self.assertIn(self.wu.ps_quote(os.path.join(DIR_SPACE, self.wu.EXE_NAME)), self.text)
        self.assertIn(self.wu.ps_quote(os.path.join(DIR_SPACE, self.wu.RELEASE_MARKER)), self.text)


# ═══════════════════════════════════════════════════════════════════════════════
# (b) B2 — the in-app ordering, with no self-skip
# ═══════════════════════════════════════════════════════════════════════════════

class InAppInnoUninstallOrderTests(unittest.TestCase):
    r"""B2(c) — ``claude_pet_win._uninstall``'s inno branch, read structurally.

    **This class supersedes**
    ``test_win_hardware_fixes.InAppInnoUninstallOrderTests``'s two ordering
    tests. Those skip themselves whenever ``os.getpid()`` appears anywhere in
    the branch, which is true of an implementation that hands the pid to a
    helper that never waits — so the gate evaporates exactly when it is needed.
    Here the pid is followed to its destination instead: it must be an argument
    of ``build_inno_uninstall_script`` specifically, and that function's output
    is gated above. Nothing in this class skips.

    The order the branch must hold:

        unins000.exe precheck (refusable, nothing deleted yet)
          ─→ the helper text is written, built with our own pid
            ─→ the helper is launched detached
              ─→ the irreversible deletes
                ─→ quit

    §3 truth table. Rivals P1–P3 are scratch copies of
    ``windows/claude_pet_win.py`` under the rival root.

    | assertion                                    | P1 pid→literal | P2 direct launch | P3 no precheck | **tree** |
    | -------------------------------------------- | -------------- | ---------------- | -------------- | -------- |
    | the helper is built at all                    | built          | absent ✗         | built          | **built** |
    | its pid argument is ``os.getpid()``           | literal ✗      | n/a ✗            | getpid         | **getpid** |
    | the branch launches the helper, not ``argv``  | helper         | ``argv`` ✗       | helper         | **helper** |
    | the precheck precedes the build               | precedes       | n/a              | absent ✗       | **precedes** |
    | every delete follows the launch                | follows        | follows          | follows        | **follows** |
    | quit follows every delete                      | follows        | follows          | follows        | **follows** |

    The last two rows tie across all three rivals and are marked as such: they
    are regression pins, not discriminators, and the record says so rather than
    counting them as evidence.
    """

    def setUp(self):
        self.tree = ast.parse(_read(PORT))
        self.fn = _func_def(self.tree, "_uninstall")
        self.assertIsNotNone(self.fn, "claude_pet_win.py has no _uninstall")
        self.branch = self._inno_branch(self.fn)
        self.assertIsNotNone(self.branch, '_uninstall has no `kind == "inno"` branch')

    @staticmethod
    def _inno_branch(fn):
        """The statements guarded by ``kind == "inno"`` — its ``body`` only.

        Not the whole ``If``: its ``orelse`` carries the portable branch, whose
        helper already waits on ``os.getpid()``, so walking the node entire
        would read the portable branch's wait as if it were the inno branch's.
        """
        for n in ast.walk(fn):
            if not isinstance(n, ast.If):
                continue
            for cmp_node in ast.walk(n.test):
                if isinstance(cmp_node, ast.Constant) and cmp_node.value == "inno":
                    return n.body
        return None

    def _branch_calls(self):
        return _calls_in(self.branch)

    def _build_call(self):
        hits = [(ln, c) for ln, name, c in self._branch_calls()
                if name == "build_inno_uninstall_script"]
        self.assertEqual(1, len(hits),
                         "the inno branch must build its helper text exactly once; found "
                         + repr([ln for ln, _ in hits]))
        return hits[0]

    def _launch_calls(self):
        return [(ln, c) for ln, name, c in self._branch_calls()
                if name in ("popen_detached", "Popen", "startfile", "run", "call", "system")]

    def test_the_branch_builds_its_helper_from_win_update(self):
        ln, _call = self._build_call()
        self.assertGreater(ln, 0)

    def test_the_pid_handed_to_the_helper_is_this_process(self):
        _ln, call = self._build_call()
        pid_args = [a for a in call.args if isinstance(a, ast.Call) and _call_name(a) == "getpid"]
        self.assertTrue(
            pid_args,
            "build_inno_uninstall_script is not called with os.getpid(); the helper would wait "
            "on something other than the process holding the files open. args="
            + repr([ast.dump(a) for a in call.args]))

    def test_the_branch_launches_the_helper_and_not_the_uninstaller(self):
        launches = self._launch_calls()
        self.assertTrue(launches, "the inno branch launches nothing at all")
        src = _read(PORT)
        for ln, call in launches:
            seg = ast.get_source_segment(src, call) or ""
            self.assertNotIn(
                "argv", seg,
                "line %d launches the uninstaller argv directly, while this process is still "
                "running and holding ClaudePet.exe and _internal\\ open: %s" % (ln, seg))

    def test_the_launched_file_is_the_one_the_helper_text_was_written_to(self):
        opens = [c for _ln, name, c in self._branch_calls() if name == "open"]
        self.assertTrue(opens, "the inno branch never writes a helper file")
        names = {a.id for c in opens for a in c.args[:1] if isinstance(a, ast.Name)}
        self.assertTrue(names, "the helper file's path is not a plain local name")
        src = _read(PORT)
        launched = "\n".join(ast.get_source_segment(src, c) or "" for _ln, c in self._launch_calls())
        self.assertTrue(any(n in launched for n in names),
                        "the launch does not reference the file the helper text was written to; "
                        "written=%r launched=%r" % (sorted(names), launched))

    def test_the_refusable_precheck_precedes_the_helper_and_every_delete(self):
        prechecks = [ln for ln, name, _ in self._branch_calls()
                     if name in ("isfile", "exists", "lexists")]
        self.assertTrue(prechecks, "the inno branch no longer checks that unins000.exe is there")
        build_ln, _ = self._build_call()
        self.assertLess(min(prechecks), build_ln,
                        "a step that can refuse must come before the helper is written")
        deletes = [ln for ln, name, _ in _calls(self.fn) if name in ("rmtree", "remove", "unlink")]
        self.assertTrue(deletes, "_uninstall deletes nothing — the plan's executor moved away")
        self.assertLess(min(prechecks), min(deletes),
                        "a launch that can fail must be refused before anything is deleted")

    def test_every_irreversible_delete_happens_after_the_helper_is_launched(self):
        launches = [ln for ln, _ in self._launch_calls()]
        self.assertTrue(launches)
        deletes = [ln for ln, name, _ in _calls(self.fn) if name in ("rmtree", "remove", "unlink")]
        self.assertTrue(deletes)
        self.assertLess(max(launches), min(deletes),
                        "the deletes start before the helper is even launched; a Popen failure "
                        "would then cost the user their files for nothing")

    def test_the_app_quits_after_the_deletes(self):
        deletes = [ln for ln, name, _ in _calls(self.fn) if name in ("rmtree", "remove", "unlink")]
        quits = [ln for ln, name, _ in _calls(self.fn) if name == "quit"]
        self.assertTrue(quits, "_uninstall never tells the app to quit, so the helper's wait "
                               "never returns and the uninstaller never runs")
        self.assertGreater(max(quits), max(deletes))

    def test_this_file_never_skips_itself(self):
        """The instrument check the superseded predicate failed.

        ``InAppInnoUninstallOrderTests`` in ``test_win_hardware_fixes.py``
        reports ``OK (skipped=2)`` for an implementation that never waits. A
        gate that can excuse itself is not a gate, so this file may contain no
        self-skip at all.
        """
        me = ast.parse(_read(os.path.abspath(__file__)))
        skips = [ln for ln, name, _ in _calls(me) if name in ("skipTest", "skip", "skipIf",
                                                             "skipUnless", "SkipTest")]
        self.assertEqual([], skips,
                         "this file has grown a self-skip at line(s) %r; the B2 hole was "
                         "exactly that" % skips)


# ═══════════════════════════════════════════════════════════════════════════════
# (c) B3 — installer.iss [UninstallRun] ordering, and N6
# ═══════════════════════════════════════════════════════════════════════════════

# Inno Setup 6 flags that remove the documented waituntilterminated default of a
# [Run]/[UninstallRun] entry (https://jrsoftware.org/ishelp/topic_runsection.htm:
# "By default, when processing a [Run]/[UninstallRun] entry, Setup/Uninstall will
# wait until the program has terminated before proceeding to the next one, unless
# the nowait, shellexec, or waituntilidle flags are used.").
NO_WAIT_FLAGS = ("nowait", "shellexec", "waituntilidle")

# Inno directory constants that expand to an absolute path. skipifdoesntexist
# requires the Filename to be one — a bare program name is not.
ABSOLUTE_CONSTANTS = ("sys", "sysnative", "win", "app", "pf", "pf32", "pf64", "cf", "cf32",
                      "cf64", "localappdata", "userappdata", "commonappdata", "tmp", "src",
                      "sd", "userpf", "usercf", "dotnet40", "dotnet64")

# Anything in [Code] that could delete a file. None of these may appear: Inno
# documents the order of its own sections, and says nothing about where a
# [Code] deletion would land relative to [UninstallRun].
CODE_DELETIONS = ("DeleteFile", "DelTree", "RemoveDir", "DelayDeleteFile", "CurUninstallStepChanged")


class InstallerUninstallRunTests(unittest.TestCase):
    r"""B3 — the ``[UninstallRun]`` kill step, pinned by what can actually break it.

    **Retired:** ``assertNotIn("postuninstall", flags)``. ``postuninstall`` is
    not in Inno Setup 6's flag list for this section, so no ``.iss`` that
    ``ISCC`` compiles can carry it; the assertion could not fail against any
    implementation and was therefore a test of nothing (AGENTS.md §3).

    **Pinned instead:** the three flags that *are* in that list and that each
    remove the documented ``waituntilterminated`` default. With any one of
    them, Inno proceeds to file deletion without waiting for ``taskkill`` to
    return, the files come back as "in use (5)", and the uninstall log's step
    order looks exactly the same — which is why the log alone cannot catch it
    and an assertion must.

    §3 truth table. Rivals I1–I5 are scratch copies of ``windows/installer.iss``.

    | assertion                        | I1 nowait | I2 shellexec | I3 waituntilidle | I4 relative name | I5 [Code] delete | **tree** |
    | -------------------------------- | --------- | ------------ | ---------------- | ---------------- | ---------------- | -------- |
    | none of the three no-wait flags  | nowait ✗  | shellexec ✗  | waituntilidle ✗  | holds            | holds            | **holds** |
    | Filename is absolute (N6)         | absolute  | absolute     | absolute         | bare name ✗      | absolute         | **{sys}\\taskkill.exe** |
    | skipifdoesntexist present         | present   | present      | present          | present          | present          | **present** |
    | [Code] deletes nothing            | holds     | holds        | holds            | holds            | DeleteFile ✗     | **holds** |

    Each rival occupies a distinct column, so no two tie on the cell that
    separates them from the tree.
    """

    def setUp(self):
        self.text = _read(ISS)
        self.sections = _iss_sections(self.text)
        self.assertIn("UninstallRun", self.sections,
                      "installer.iss has no [UninstallRun] section, so nothing closes the pet "
                      "before the files are deleted")
        entries = self.sections["UninstallRun"]
        self.assertEqual(1, len(entries),
                         "expected exactly one [UninstallRun] entry; extra entries change what "
                         "runs first: " + repr(entries))
        self.entry = _iss_params(entries[0])
        self.flags = self.entry.get("Flags", "").split()

    def test_the_entry_kills_the_pet_with_taskkill(self):
        self.assertEqual(r"{sys}\taskkill.exe", self.entry.get("Filename"))
        params = self.entry.get("Parameters", "")
        self.assertIn("/IM ClaudePet.exe", params)
        self.assertIn("/F", params)
        self.assertNotIn("/T", params.split(),
                         "/T kills the process tree; the in-app '완전 삭제…' makes the "
                         "uninstaller a child of the pet, so /T would cut its own branch")

    def test_no_flag_removes_inno_s_documented_wait(self):
        present = [f for f in self.flags if f.lower() in NO_WAIT_FLAGS]
        self.assertEqual(
            [], present,
            "%r removes the waituntilterminated default, so Inno starts deleting files before "
            "taskkill returns — and the uninstall log's step order is unchanged, so nothing "
            "downstream would show it. Flags=%r" % (present, self.flags))

    def test_the_filename_is_absolute_as_skipifdoesntexist_requires(self):
        """N6 — the flag's documented condition, pinned."""
        self.assertIn("skipifdoesntexist", [f.lower() for f in self.flags],
                      "without skipifdoesntexist a machine with no taskkill.exe fails the "
                      "whole uninstall instead of skipping this step")
        name = self.entry.get("Filename", "")
        m = re.match(r"^\{([a-z0-9]+)\}[\\/]", name)
        absolute = bool(re.match(r"^[A-Za-z]:[\\/]", name)) or (
            m is not None and m.group(1) in ABSOLUTE_CONSTANTS)
        self.assertTrue(absolute,
                        "skipifdoesntexist requires an absolute Filename; %r is not one, so the "
                        "flag's behaviour is undefined for this entry" % name)

    def test_the_entry_is_flagged_only_in_ways_that_keep_the_wait(self):
        known_safe = {"runhidden", "skipifdoesntexist", "runascurrentuser", "runasoriginaluser",
                      "dontlogparameters", "hidewizard", "logoutput", "waituntilterminated",
                      "32bit", "64bit", "runmaximized", "runminimized", "skipifnotsilent",
                      "skipifsilent", "unchecked"}
        unknown = [f for f in self.flags if f.lower() not in known_safe]
        self.assertEqual([], unknown,
                         "unrecognised flag(s) %r on the kill step — check them against "
                         "https://jrsoftware.org/ishelp/topic_runsection.htm before shipping"
                         % unknown)

    def test_nothing_in_code_can_delete_a_file_ahead_of_the_kill_step(self):
        code = "\n".join(self.sections.get("Code", []))
        found = [d for d in CODE_DELETIONS if d in code]
        self.assertEqual(
            [], found,
            "[Code] contains %r. Inno documents the order of its own sections; it documents "
            "nothing about where a [Code] deletion lands relative to [UninstallRun], so a "
            "deletion here is an ordering this file can no longer state." % found)

    def test_the_kill_step_is_declared_before_the_deletions_it_protects(self):
        """A readability pin, not the mechanism.

        Inno's execution order comes from the sections' definitions, not from
        their position in the file — ``[UninstallRun]`` runs "as the first step
        of uninstallation" wherever it sits. This asserts only that the file
        reads in the order it executes, so the next reader is not invited to
        infer the opposite.
        """
        run_at = self.text.index("[UninstallRun]")
        del_at = self.text.index("[UninstallDelete]")
        self.assertLess(run_at, del_at)

    def test_close_applications_is_present_but_is_not_what_this_rests_on(self):
        """F4's finding: both directives were already set when the pet's files
        survived the uninstall, so they are pinned as present and explicitly
        not credited with the ordering."""
        self.assertIn("CloseApplications=yes", self.text)
        self.assertIn("RestartApplications=yes", self.text)


# ═══════════════════════════════════════════════════════════════════════════════
# (d) N5 — the version resource is derived from VERSION_STRINGS, not re-typed
# ═══════════════════════════════════════════════════════════════════════════════

SENTINEL_STRINGS = {
    "CompanyName": "ZZ-Rival-Company",
    "FileDescription": "ZZ-Rival-Description",
    "InternalName": "ZZRivalInternal",
    "LegalCopyright": "ZZ-Rival-Copyright",
    "OriginalFilename": "ZZRival.exe",
    "ProductName": "ZZ-Rival-Product",
}
STUB_VERSION = "9.87"


class VersionResourceSingleSourceTests(unittest.TestCase):
    r"""N5 — ``build_win.write_version_resource`` must read ``VERSION_STRINGS``.

    The existing gate (``test_win_hardware_fixes.VersionResourceTests``) keeps
    its own hard-coded copy of the expected strings, so it agrees with a
    generator that hard-codes them too: both would have to be edited together,
    and a generator that stopped consulting ``VERSION_STRINGS`` would stay
    green. The property that was documented and ungated is *derivation*, and
    the only way to test derivation is to change the source and require the
    output to follow.

    §3 truth table. R5 is a scratch copy of ``windows/build_win.py`` whose
    generator emits a literal table.

    | fixture                              | R5 hard-coded rows | **tree** |
    | ------------------------------------ | ------------------ | -------- |
    | VERSION_STRINGS patched to sentinels | real strings ✗     | **sentinels** |
    | VERSION_STRINGS untouched            | real strings       | **real strings** (tie) |
    | version "9.87"                       | 9.87               | **9.87** (tie) |

    Only the first row discriminates; the other two are marked as ties and are
    regression pins. Patching a module attribute is the fixture here, which is
    why the second row cannot do the job on its own — it is exactly the shape
    the superseded gate had.
    """

    def setUp(self):
        self.bw = _bw()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "version_info.txt")

    def _emit(self, version=STUB_VERSION):
        self.bw.write_version_resource(self.path, version)
        return _read(self.path)

    def test_the_emitted_table_follows_a_mutated_VERSION_STRINGS(self):
        real = dict(self.bw.VERSION_STRINGS)
        with mock.patch.object(self.bw, "VERSION_STRINGS", dict(SENTINEL_STRINGS)):
            text = self._emit()
        for key, value in SENTINEL_STRINGS.items():
            self.assertIn("StringStruct(%r, %r)" % (key, value), text,
                          "%s did not follow the source table — the generator keeps its own "
                          "copy, so VERSION_STRINGS is no longer the single source" % key)
        for key, value in real.items():
            self.assertNotIn(
                "StringStruct(%r, %r)" % (key, value), text,
                "the real %s (%r) was emitted even though VERSION_STRINGS said otherwise" % (key, value))

    def test_every_key_of_VERSION_STRINGS_reaches_the_file(self):
        text = self._emit()
        for key, value in self.bw.VERSION_STRINGS.items():
            self.assertIn("StringStruct(%r, %r)" % (key, value), text)

    def test_the_two_version_strings_come_from_the_argument(self):
        text = self._emit()
        self.assertIn("StringStruct('FileVersion', %r)" % STUB_VERSION, text)
        self.assertIn("StringStruct('ProductVersion', %r)" % STUB_VERSION, text)
        self.assertNotIn("FileVersion", self.bw.VERSION_STRINGS,
                         "FileVersion must not be a fixed string — it would freeze at the "
                         "committed value")
        self.assertNotIn("ProductVersion", self.bw.VERSION_STRINGS)

    def test_the_numeric_quad_comes_from_the_same_argument(self):
        text = self._emit()
        self.assertIn("filevers=(9, 87, 0, 0)", text)
        self.assertIn("prodvers=(9, 87, 0, 0)", text)

    def test_the_generator_writes_a_fresh_file_every_call(self):
        first = self._emit("1.2")
        second = self._emit("3.4")
        self.assertNotEqual(first, second,
                            "the resource file is not rewritten per build, so the version in it "
                            "freezes at whatever was there first")
        self.assertIn("filevers=(3, 4, 0, 0)", second)


if __name__ == "__main__":
    unittest.main()
