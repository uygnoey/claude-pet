# Review record — Track F, hardware fixes F1–F5 (v0.25 pre-release)

Reviewer: reviewer-f (Claude), REVIEWER role only on this track; independent of the Developer
and of verifier-f. Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD
`f876e40ee8de3e7e80aa5dac8c5cd331b276630d` (the fix is in the working tree, uncommitted). This
file is untracked and was created by the Reviewer; the Coordinator stages by named paths.

Inputs: AGENTS.md §0–§8 (read in full for §2/§3/§4/§5/§6); CLAUDE.md (repo layout, Privacy,
release procedure, user-owned files); `windows/README.md` (before and after);
`docs-design/track-cd-review-20260913.md` and `docs-design/track-bw-review-20260913.md`
(the two prior review records, including the H1–H21 hardware list this record extends);
`docs-design/track-f-verification-20260914.md` (the Verifier's RED record, GREEN round 1 and
GREEN round 2, read in full); `git status --porcelain`; `git diff -- windows/`; the full text
of `windows/win_core.py`, `windows/installer.iss`, `windows/tests/test_win_hardware_fixes.py`,
and the changed regions of `windows/win_update.py`, `windows/win_autostart.py`,
`windows/claude_pet_win.py` (`_uninstall`, `_inno_registry_reader`), `windows/build_win.py`,
`windows/verify_win_artifact.py`; and the hardware evidence quoted verbatim in the Track F
assignment.

Not done, by instruction: no git write command was run; no production file and nothing under
`windows/tests/` or the repo-root `tests/` was opened for writing; `claude_pet.py` was never
opened for writing; no untracked file was touched other than this one, which the Reviewer
created. The GUI was not run, no PyInstaller or Inno build was attempted, and no Windows
registry was reached (this host has no `winreg`). The one Reviewer probe
(`…/scratchpad/probe_rev.py`) is in the session scratchpad, never in the worktree, and only
imports and reads. All commands ran with cwd at the worktree root. Times are UTC.

---

## Review round 1 (2026-09-14)

### Verdict: **FAIL** — 2 blocking items (B1 is not Track F's doing)

**F1–F5 are, as code, correctly and carefully fixed.** Every one of the five was re-derived
here independently of the Verifier's record and independently of the hardware report where the
fact admits of derivation, and all five check out. The two blocking items are not defects in
the five fixes:

- **B1** — the macOS suite is red on this branch (57 failures, one cause), so AGENTS.md §8
  item 5 is unsatisfiable. Pre-existing at `f876e40`; established here from git objects, not
  taken on the Verifier's word. Blocks merge for anything off this branch.
- **B2** — the in-app half of F4 (`win_update.build_inno_uninstall_script` plus the PID-WAIT
  rewiring of `_uninstall`'s inno branch) is **new production code that no assertion anywhere
  gates**, and the two tests that would cover it *skip themselves* on a condition a no-wait
  implementation also satisfies. A silent self-disarming gate is worse than a missing one.

Four non-blocking notes are in §7 and an eight-entry hardware list (H22–H29) is in §8.

---

### 1. The tree reviewed

`git rev-parse HEAD` → `f876e40ee8de3e7e80aa5dac8c5cd331b276630d`.
`git status --porcelain` → seven modified tracked files, three untracked paths, nothing else:

```
 M windows/README.md
 M windows/build_win.py
 M windows/claude_pet_win.py
 M windows/installer.iss
 M windows/verify_win_artifact.py
 M windows/win_autostart.py
 M windows/win_update.py
?? docs-design/track-f-verification-20260914.md
?? windows/tests/test_win_hardware_fixes.py
?? windows/win_core.py
```

`shasum -a 256` at the start of this review — **every value is byte-identical to the
Verifier's R2.1 table**, so this review covers exactly the bytes verified in GREEN round 2 and
nothing moved under either of us:

```
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
a3e323c85093e2cd436730113708e7fadd915764e20934da1a610ddd07e46733  windows/win_core.py
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
3c26fbffc723ba43f430225cf508dacd1218efbd1ea64d9036f6a2bea3363222  windows/win_autostart.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
9ba6fb64739e390e0ebce047ca15a06bee474cb7f54b641593e4e9a86fbac756  windows/build_win.py
3464a7c943b3fadecab5eb891c7acaa09fdae00e5469ff51d4d3c09069dadd49  windows/verify_win_artifact.py
3d92f68236816e472d0e3866c4a789209d8f0e35a78ee0d603b7d0d01ac52616  windows/installer.iss
069e13cd322021c1ebdc52602d7c8309bc33185e97d96fde52b41e3faf5b55eb  windows/README.md
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
```

**Scope respected.** `claude_pet.py` is byte-identical to `git show HEAD:claude_pet.py`, and
`git diff HEAD -- claude_pet.py tests/` is empty: the macOS half of the repository is untouched,
as the track requires. Nothing outside `windows/` and `docs-design/` changed. None of the three
user-owned paths in CLAUDE.md § "User-owned files" exists in this worktree, and none was
created or touched.

---

### 2. AGENTS.md §2 — Developer / Verifier separation

**Condition A (the Developer did not touch the gating assertions): evidenced, and by the right
mechanism.** `windows/tests/test_win_hardware_fixes.py` hashes
`53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c` at the Verifier's RED run
(§1), at GREEN round 1 (§9), at GREEN round 2 (R2.1) **and now**. A hash pin taken before the
fix existed and re-checked after it landed is exactly what makes this condition checkable
without trusting anyone's account, which is what §2 asks for. The Developer's fix is therefore
judged by assertions written against the unfixed tree, byte for byte.

**Condition B (the Verifier has clean hands on the production files): declared, not yet
independently checkable, and that is a property of the change being uncommitted rather than a
defect.** There is no commit and therefore no authorship to read. What *is* checkable is that
the two files the Verifier declares as deliverables
(`windows/tests/test_win_hardware_fixes.py`, `docs-design/track-f-verification-20260914.md`)
are disjoint from the eight production paths the Developer declares, and that the untracked set
contains exactly those two plus the Developer's `windows/win_core.py` — no third file appeared
that would suggest an undeclared hand. The condition becomes auditable at commit time, via the
`Developer:` / `Verifier:` trailers naming two different parties (§7). **That is a merge
precondition, not something this review can discharge.**

**Condition C is not invoked and does not need to be.** No exception is declared and none is
required: the declared role split is intact on its face.

**Deliverables (§4).** The Verifier's two paths and the Developer's `windows/win_core.py` were
each named in advance in their own records, and all three did not previously exist — which is
the ceiling §4 puts on what an assignment may name. This review file is the Reviewer's own
named deliverable and likewise did not exist. No untracked file belonging to anyone else was
opened for writing.

---

### 3. AGENTS.md §3 — red before green, and the discrimination runs

**The red record is real and specific.** §2 of the Verifier's record quotes 33 failures with
their assertion text, including the two tracebacks that reproduce the hardware's own failures
(`ModuleNotFoundError: No module named 'fcntl'`, then `TypeError: LoadLibrary() argument 1 must
be str, not None`). These are quoted output, not a claim that something failed.

**The discrimination runs are the strongest part of this change, and they are computed rather
than argued** (§3 of the Verifier's record). Three of them deserve to be singled out:

- **F3's rival table is genuinely discriminating, including against the rival that matters
  most.** `TABLE` (`blob[0] in (0x00, 0x02)`) is what a careful person writes straight off the
  hardware report, and it **agrees with the chosen rule on every observed byte**. It is killed
  only by the `0x04` row. That is precisely the §3 hazard — a rival that collapses onto the
  correct answer on the sampled fixtures — and it was found and closed rather than missed.
- **F4's ordering gate refuses the rival that was already true when the failure happened.**
  `CloseApplications=yes` and `RestartApplications=yes` were in `installer.iss` at `f876e40`,
  the commit the hardware failure was observed on. A gate that accepted them would be satisfied
  by the exact tree that failed. The gate requires an explicit `[UninstallRun]` step instead.
  This is the right shape of argument and it is stated as such.
- **The instrument is itself pinned.** `SimulationInstrumentTests` asserts that the simulated
  Windows child still reproduces both hardware failures against the *unfixed* import path. This
  is the `tests/test_mutation_instruments.py` hazard from the macOS suite, correctly transposed:
  a simulation that quietly stopped simulating would turn every F1 gate into a green no-op.

**One §3 defect was caught by the Verifier and is worth recording because it is the general
case, not a one-off.** On the first run, *both* F4 ordering gates skipped rather than failed,
because walking the `if kind == "inno"` `If` node whole reached its `orelse` — the
`elif kind == "portable"` branch, whose helper does call `os.getpid()`. The gate now walks
`node.body` only. **That same skip mechanism is what B2 is about** (§5.4 below): it was
disarmed by accident once, and it is still disarmable on purpose.

**Where §3 is not satisfied: B2.** `build_inno_uninstall_script` is new production code and
`grep build_inno_uninstall_script windows/tests/` finds nothing. There is no red run for it
because there is no test for it. The Verifier declares this (finding (i)) and frames it as "a
gap to assign, not a defect found", on the ground that the portable twin
`build_uninstall_script` is equally ungated. **The parity argument is sound about the *level* of
coverage and does not dispose of the §3 question**, because this change *adds* behaviour that
the suite would keep green if it were deleted. See §5.4.

---

### 4. AGENTS.md §5 — evidence, and the observation/invariant split

This is the section the F3 and F4 documentation had to get right, and it does.

**F3.** Three claims are kept in three slots, in both `startup_approved_enabled.__doc__` and
`windows/README.md`:

1. **Observation**, scoped: one machine, Windows 11, through Settings › Startup apps and Task
   Manager › Startup apps, 2026-09-14 — disable wrote `01 00 00 00` + an 8-byte FILETIME,
   re-enable wrote twelve zero bytes, third-party entries the UI never touched carried `0x02`.
   It is labelled an observation, and it carries no count, window or denominator, which is
   stated rather than papered over.
2. **The rule the code implements** — low bit of the first byte, even enabled / odd disabled —
   with `0x04`/`0x05` and above explicitly marked **extrapolation**, "a hypothesis from the
   shape of the three observed values, not an observation, and no second party has reproduced
   it".
3. **The operational consequence** — if a later hardware run moves a byte, that one function
   and its test table change together and nothing else does.

The direction of inference is also correct and stated: one machine cannot *establish* the
encoding, and it does not have to — it **refutes** the shipped rule, because `0x00` is a value
the shipped rule read as disabled and Windows was launching the app anyway. That is a valid use
of a single counterexample and is the only use made of it.

**F4.** Same treatment. The observation ("the uninstall log carried no Restart Manager /
CloseApplications step at all, and 44 files under `_internal\` survived with rc=0") is kept
separate from the operational consequence ("therefore an explicit `[UninstallRun]` kill step,
and the two directives do not satisfy this gate"), and the reason the consequence does not rest
on the observation is given: the directives were present when the failure happened.

**F2 is deliberately *not* treated as an observation, and that is right.** The corrected subkey
is derived from `installer.iss`'s own `AppId` — a fact readable out of source, checkable by
anyone, which §5 says must be cited rather than dressed in the vocabulary of uncertain evidence.
The hardware log is cited alongside as corroboration, not as the source. §5's "Slot 1 is for
sample-derived claims only" is honoured.

**Privacy (CLAUDE.md § Privacy).** Nothing added here logs a path, a project name or a session
id. `log_update("uninstall", kind=…, status=…, at=…, error=<exception class name>)` carries a
type name and status tokens only. `check_version_resource`'s messages carry
`os.path.basename(exe_path)` — a fixed literal (`ClaudePet.exe`), not a user path. The
generated PowerShell text contains the app path, but it is written to a `%TEMP%` file for the
helper, never to `update.log`. Clean.

---

### 5. The five findings, re-derived

Every claim below was checked by the Reviewer against the source, not read off the Verifier's
record. The probe used is `…/scratchpad/probe_rev.py` (session scratchpad, read-only).

#### 5.1 F1 — one owner for the core import: **correct**

```
F1 core-import sites under windows/ (AST: import / from-import / importlib.import_module):
    win_core.py [(69, 'import_module("claude_pet")'), (83, 'import_module("claude_pet")')]
```

Exactly one module names the core, and it is the helper. `claude_pet_win.py`, `win_update.py`,
`win_autostart.py` (transitively, through `win_update`), `build_win.py` and
`verify_win_artifact.py` all reach it through `win_core.import_core()`.

The no-op-on-macOS claim, measured rather than asserted:

```
F1 core: claude_pet APP_VERSION 0.24
   sys.path delta: []          # import_core() added nothing
   CDLL restored : True        # the wrapper did not leak past the finally
   compat on path: False       # windows/compat was not inserted
   idempotent    : True        # a second call returns the same module object
```

The two detours are correctly scoped: the `fcntl` shim is inserted only under
`sys.platform == "win32"`, and the `CDLL` subclass is installed and removed inside a
`try/finally` around the single `import_module` call, so nothing outside that call sees a
patched `ctypes`. The compat shim raises `ImportError` if imported on a platform that has the
real `fcntl`, which keeps the `win32` guard load-bearing rather than decorative.

The dual-import idiom (`from . import win_core` / `import win_core`) matches the one
`win_autostart.py` already uses for `win_update`, so the port, the PyInstaller bundle (which
flattens `windows/` onto `sys.path`) and the test suite (`-t .`, package form) all resolve. The
two module objects that can result both call `importlib.import_module("claude_pet")`, which is
`sys.modules`-backed, so there is exactly one core object either way — and the F1 gate asserts
`win_update.cp is core` to pin that.

`build_win.py` also gains `--hidden-import win_core`, without which the bundle would import the
port and fail at `import win_core`. Correct.

One nit, non-blocking: N1 in §7.

#### 5.2 F2 — the Inno uninstall subkey: **correct, and re-derived here**

Derived by the Reviewer from `installer.iss` alone, applying Inno's brace rule (a *leading*
`{{` is the escape for one literal `{`; `}` is never escaped, so a trailing `}}` survives as
two braces; the uninstaller appends `_is1`):

```
AppId as written : {{me.yeongyu.claudepet}}
AppId expanded   : {me.yeongyu.claudepet}}
derived subkey   : Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
constant         : Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
F2 MATCH         : True
```

This matches the hardware uninstall log verbatim
(`Deleting registry key: …\{me.yeongyu.claudepet}}_is1`), and — more to the point — it matches
**without consulting it**. The Inno wizard's own template is `AppId={{GUID}` with a *single*
closing brace for exactly this reason; `{{…}}` here produces the doubled one. The code states
the derivation in a comment, as asked.

**The fix is on the right side.** Correcting the constant (rather than "fixing" the AppId) is
the only safe direction: changing `AppId` would orphan every already-installed copy's ARP entry
and its `unins000.exe`. Nothing in the change touches `AppId`.

**Every other spelling agrees**, checked by grep across the whole worktree, not just the files
the gate looks at:

```
windows/installer.iss:13           AppId={{me.yeongyu.claudepet}}
windows/win_update.py:59,63,65,69  {me.yeongyu.claudepet}}_is1  (comment ×3 + the constant)
windows/claude_pet_win.py:261      {me.yeongyu.claudepet}}_is1  (_inno_registry_reader docstring)
windows/README.md:45,46            {me.yeongyu.claudepet}}_is1  + the derivation, spelled out
```

No one-brace spelling survives anywhere. `uninstall_plan("inno", …)` still ends in
`('run', [<dir>/unins000.exe, '/SILENT'])`, so the install-kind fix does not disturb the plan
the corrected kind now reaches.

**The anti-drift measure asked for is present and is the right one**: the gate derives the
expected key from `installer.iss` at test time (`_inno_uninstall_key_name`) instead of
transcribing it, so a future AppId change moves the constant and the test together.

#### 5.3 F3 — the StartupApproved byte rule: **correct, and it is the rule, not a table**

The implementation is a bit test, not a lookup:

```python
_STARTUP_APPROVED_DISABLED_BIT = 0x01   # low bit of the first byte: set = disabled, clear = enabled
...
return bool(isinstance(blob, (bytes, bytearray)) and len(blob) > 0
            and not blob[0] & _STARTUP_APPROVED_DISABLED_BIT)
```

Exercised by the Reviewer over the whole first-byte range and over the guard cases:

```
F3 disagreements with (b % 2 == 0) over all 256 first bytes: none
    None                -> False        b''                 -> False
    '\x00' (str)        -> False        0   (int)           -> False
    [0] (list)          -> False        memoryview(b'\x00') -> False
    bytearray(b'\x00')  -> True         b'\x00'             -> True
    b'\x01'             -> False        b'\x02'             -> True
    b'\x03'             -> False
    — nothing raised
```

Every guard the task asked to keep is kept, with the fail-safe direction unchanged and its
reasoning intact in the docstring ("read as 'off', the item shows unchecked and the next click
deletes the entry, which is the self-healing path; read as 'on' it would show a checkmark
Windows does not honour and no click would fix it"). Both removed constants are gone from the
tree with no dangling reference.

The provenance requirement is met in both places the task named — the docstring and
`windows/README.md` — and met in the §5 shape, with the observed half and the extrapolated half
in separate bullets rather than merged into a universal statement about Windows. The README's
"실기에서 확인할 것" list, which is what sent the hardware session looking at these bytes in the
first place, no longer states the refuted rule and now flags the `0x03`-and-above part as a
hypothesis a later run may overturn.

The end-to-end symptom gate is the right one to have: from the reported state (Run value present
and pointing at us, StartupApproved `00 ×12`), `autostart_read_state` must read `"on"`, and one
click must *delete* the Run value rather than rewrite it. Under the shipped rule the same click
took the "off" branch and wrote a value that was already there, so the item could never uncheck
— the click made the disagreement worse. That second half is asserted, not just the read.

Nothing else in `win_autostart.py` moved: the diff is the module docstring, the constants and
this one function. The Run-value format, the menu position and label, and the `update.log`
`startup status=on|off error=none` line — all of which passed on hardware — are untouched, and
the 43 pre-existing tests that pin them stay green.

#### 5.4 F4 — uninstalling while the pet is running: **installer half correct; in-app half correct by inspection but ungated (B2)**

**(a) The installer half.** `installer.iss` gains one entry:

```
[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ClaudePet.exe /F"; RunOnceId: "CloseClaudePet"; Flags: runhidden skipifdoesntexist
```

Checked against Inno Setup 6's documented semantics (I could not run `ISCC` here — this is
macOS — so this rests on the documentation, and H22 in §8 is the hardware confirmation):

- **Ordering.** `[UninstallRun]` is the uninstall-time counterpart of `[Run]`, and its entries
  are processed **at the start of uninstallation, before any files are removed** — which is the
  whole point of the entry. The `postuninstall` flag is what moves an entry to *after* removal,
  and the gate asserts its **absence**; the comment in the file says so explicitly. This is the
  ordering pin and it is correctly identified.
- **Waiting.** The default for a non-`shellexec` entry is `waituntilterminated`, so Inno waits
  for `taskkill` to return before it starts deleting. No `nowait` is present. Correct.
- **Tolerance.** `skipifdoesntexist` skips the entry when `{sys}\taskkill.exe` is absent rather
  than failing the uninstall; Inno does not inspect a `[Run]`/`[UninstallRun]` exit code, so
  `taskkill`'s non-zero "process not found" result is harmless. Both are stated in the comment.
- **`RunOnceId`** is present, which `[UninstallRun]` requires to avoid re-running the entry when
  several versions' uninstall logs are processed.
- **`runhidden`** keeps a console app from flashing a window. Correct for `taskkill`.
- **`/T` is deliberately omitted**, with the reason in the comment: in the in-app "완전 삭제…"
  path the uninstaller is a descendant of the pet, and a tree kill would cut its own branch.
  This is a real trap and catching it is good.
- **`{sys}`** resolves to `System32` here because `ArchitecturesInstallIn64BitMode=x64compatible`
  puts the install in 64-bit mode, so there is no WOW64 redirection surprise.

**The `.claude_pet` guarantee is not weakened.** The new entry deletes nothing — asserted by the
gate against a verb list, and confirmed by reading the section. `[UninstallDelete]` is unchanged
and still names only `{app}\_internal`, `{app}\ClaudePet.exe`,
`{app}\_internal\claudepet-release.json` and `{localappdata}\me.yeongyu.claudepet`; nothing
under `%USERPROFILE%` appears in any delete section. The in-app plan still never names the pets
directory, for either kind. Both halves are separately pinned, and the gate correctly does *not*
extend the `.claude_pet.json` half to `uninstall_plan` — the in-app "완전 삭제…" deletes that
file on purpose, in parity with the macOS `UNINSTALL_PATHS`, and conflating the two would have
produced a gate that contradicts the product.

**(b) The in-app half — correct as written.** `_uninstall`'s inno branch no longer launches
`unins000.exe` directly. It writes `wu.build_inno_uninstall_script(argv, os.getpid())` to a
`%TEMP%` `.ps1` and launches that detached, so the uninstaller starts only after this process is
gone. Generated text, exercised by the Reviewer with an embedded single quote in the path:

```
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id 4321 -Timeout 120 -ErrorAction Stop } catch { }
if (Get-Process -Id 4321 -ErrorAction SilentlyContinue) { exit 2 }
if (Test-Path -LiteralPath 'C:\it''s\ClaudePet\unins000.exe') {
  try { Start-Process -FilePath 'C:\it''s\ClaudePet\unins000.exe' -ArgumentList '/SILENT' } catch { exit 3 }
}
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }
exit 0
```

Line for line the shape of the already-shipped portable twin: same `Wait-Process -Timeout 120`,
same `exit 2` fail-closed refusal when the pid is still alive, same guarded action, same
self-delete; quoting is `ps_quote`'s doubling, not raw interpolation. The refusable
`os.path.isfile(unins000.exe)` precheck still sits ahead of the first irreversible delete, so a
launch that can fail still costs the user nothing — that ordering property, which the earlier
code had and which is easy to lose in a rewrite like this, is preserved and is separately gated.

**(c) B2 — and this is the blocking part.** Nothing asserts any of (b).

- `grep build_inno_uninstall_script windows/tests/` → no hit. The wait, the `exit 2` refusal and
  the `Start-Process` are pinned by no assertion anywhere.
- The two tests that would have covered the ordering —
  `test_the_uninstaller_is_not_launched_while_the_app_is_still_running` and
  `test_a_moment_is_given_for_the_process_to_exit` — **skip**, and the skip condition is
  `_pid_wait()`: "does the string `getpid` appear as a call inside the inno branch?" A
  hypothetical implementation that passes `os.getpid()` to a helper which never waits satisfies
  that condition exactly as the real one does. So the gate is satisfied by the *shape* of the
  fix rather than by its behaviour.
- The suite then reports `OK (skipped=2)`. A reader who checks the suite sees green; a reader who
  checks the skip messages sees "PID-WAIT implementation", which reads as a verdict and is in
  fact an assumption.

The Verifier saw this and recorded it honestly (finding (i), carried forward as R2.7), including
the sharpened form: "A rewrite that dropped the wait would keep the whole suite green." Their
reasons for not closing it in-round are correct — doing so would have changed the gating file's
hash and destroyed the Condition A evidence. So this is not a criticism of the Verifier's
conduct; it is an unmet §3 obligation that has to be met before merge.

**The parity argument does not dispose of it.** That `build_uninstall_script` (portable) is
equally ungated is true and is worth knowing, but it describes a pre-existing coverage level,
not a licence for new code. F4 is the finding where a regression strands the user's app folder
with the ARP entry already deleted — the one state the user cannot recover from inside the
product. New code on that path should not ship gated by a string match.

**Closable in one Verifier round, without touching production code**, and without disturbing the
existing Condition A evidence: add a **new** gating file (e.g.
`windows/tests/test_win_uninstall_helpers.py`) that pins both builders' generated text — the
`Wait-Process -Id <pid>`, the `exit 2` when the pid is still alive, the guarded `Start-Process`
of `unins000.exe`, the quote doubling — and observe it red against a scratch copy with the wait
removed (§3's revert-and-observe, on a throwaway branch, which is explicitly encouraged). The
existing gating file's hash is then untouched and both pieces of evidence stand.

**Residual risks, inherited rather than introduced** (they exist in the portable twin too, and
are the right things to put on the hardware list rather than to block on): pid reuse inside the
120 s wait; a pet that takes longer than 120 s to exit, which ends at `exit 2` with the user
files already deleted and the ARP entry still present. The second is *recoverable* precisely
because (a) landed — the user can re-run the uninstall from ARP, and `[UninstallRun]` now closes
the app — which is a nice interlock and worth saying out loud.

#### 5.5 F5 — the exe's version resource: **correct**

`build_win.write_version_resource(path, version)` writes a PyInstaller version-resource file at
build time into a `mkdtemp` removed in a `finally`, and `build()` passes it as `--version-file`.
Exercised by the Reviewer with a stub version the repository has never held:

```
write_version_resource(<tmp>, "7.13")
  parses as Python            : True     (VSVersionInfo / FixedFileInfo / StringFileInfo present)
  filevers/prodvers           : (7, 13, 0, 0)
  APP_VERSION (0.24) leaked?  : False
  FileDescription             : Claude Pet
  CompanyName                 : Yeongyu Yang
  ProductName                 : Claude Pet
  OriginalFilename            : ClaudePet.exe
  LegalCopyright              : Copyright (c) Yeongyu Yang
  FileVersion / ProductVersion: 7.13
_version_quad: "7.13"→(7,13,0,0)  "0.25"→(0,25,0,0)  "1.2.3.4.5"→(1,2,3,4)  "x"→(0,0,0,0)
```

The stub-version row is the one that matters: it rules out the "write it once by hand and commit
it" implementation the task forbade, because a committed file cannot contain `7.13`. The numbers
come from `app_version()` (parsed out of `claude_pet.APP_VERSION`) and from nowhere else, so the
resource cannot go stale. The `StringTable('040904B0')` / `VarStruct('Translation', [1033, 1200])`
pair is internally consistent (US English, Unicode).

`verify_win_artifact.check_version_resource(exe_path)` returns a problem list, never raises (a
missing or unreadable file becomes a problem entry), and matches the fixed strings as UTF-16LE
in the PE bytes. It does **not** parse the resource directory, and it says so — in the docstring
and on stderr when run off `win32`. That honesty is the right call: the check is a presence
test, and describing it as more would be the failure mode CLAUDE.md's macOS gates guard against
("skip loudly"). The gate is wired in behind a successful layout check in `check_zip`, so a
malformed zip reports the layout problem rather than a confusing missing-exe one.

One drift note, non-blocking: N3 in §7.

---

### 6. Suites re-run by the Reviewer

**Windows suite — green.**

```
$ cd /Users/yeongyu/claude-pet-windows
$ python3 -m unittest discover -s windows/tests -t . -v
…
Ran 179 tests in 1.084s

OK (skipped=2)
```

179 = 98 `test_win_update` + 43 `test_win_autostart` + 38 `test_win_hardware_fixes`. The two
skips are the pair discussed in §5.4(c) — `InAppInnoUninstallOrderTests`'s two ordering tests,
under `'PID-WAIT implementation: …'`. No other skip, failure or error. The two pre-existing
modules are unchanged and green, which is what pins the hardware-passing behaviour the task said
must not regress (menu position/label/value format, the `startup status=on|off error=none` line,
portable toggling over a foreign path, the disabled item on a source run, the
`check status=error reason=fetch-failed:URLError cooldown=0` line, leftover cleanup at 60 s).
`inno_silent_args` still emits `/RESTARTAPPLICATIONS` — checked directly:

```
['…\\setup.exe', '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS',
 '/FORCECLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS', '/RELAUNCH=1', '/LOG=…\\setup.log']
```

**macOS suite — red, and red before Track F existed (B1).**

```
$ python3 -m unittest discover -s tests -v
…
Ran 588 tests in 269.947s

FAILED (failures=49, errors=8, skipped=8)
```

Grouped by module, from this run's own output:

```
   8 ERROR test_manual_update_transaction   (all setUpClass)
  48 FAIL  test_upload_artifact_gate        (all setUp → assert_reviewed_file)
   1 FAIL  test_v024_release_contract
```

All 57 have one cause, a stale review pin rather than a behaviour:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

**Established independently of the Verifier's account, and from git objects rather than from the
checkout:** `git show f876e40:claude_pet.py | shasum -a 256` is `9dd9fb12…` while
`git show f876e40:tests/test_upload_artifact_gate.py`'s `REVIEWED_APP_SOURCE_SHA256` is
`6f95bc8b…` — the pin and the file it pins already disagree **at the commit**, before any Track F
edit exists. The worktree's `claude_pet.py` is byte-identical to `git show HEAD:claude_pet.py`,
and `git diff HEAD -- claude_pet.py tests/` is empty. Track F cannot reach these modules by any
route: `grep -rn 'win_update\|win_core\|win_autostart\|build_win\|verify_win' tests/*.py` finds
nothing, and the only occurrence of "windows" anywhere under `tests/` is a test *name* in
`test_v024_release_contract.py` about release-notes wording.

The brief's expectation ("currently passes with 7 loud skips") describes the sibling checkout on
`main`, not this commit. On this branch the count is 8 skips — the eighth is
`test_v020_boundaries.B2Bundle.test_py2app_bundle_carries_every_asset`, skipped because
`dist/ClaudePet.app` is not built in this worktree, which is a property of the worktree and not
of any change.

**Why this still blocks.** §8 item 5 requires the *full* suite green, and it is not. The remedy
is not a bump: both constants guard a *review*, and re-pinning without re-reviewing
`release.sh`, `verify_release_artifact.py` and `claude_pet.py` against the harness converts a
loud refusal into a silent pass — the exact failure those pins exist to prevent. It needs its own
assignment, and it is not Track F's to do (and not this Reviewer's — `tests/` is out of scope by
instruction).

---

### 7. Non-blocking notes

- **N1 — `win_core`'s "no path is added" sentence is true of the function, not of the module.**
  `import_core()` adds nothing on macOS (measured, §5.1), but the module body inserts `_ROOT`
  into `sys.path` at import time on every platform. The docstring explains this two paragraphs
  above the sentence, and the behaviour is unchanged from the `win_update.py` code it replaced,
  so nothing is wrong — but the emphasised sentence is the one a hurried reader will quote.
  Consider "`import_core()` adds no path and wraps no builtin" to keep the scope attached.
- **N2 — `taskkill /IM ClaudePet.exe /F` is name-matched, so it reaches any process of that name,
  not only the one being uninstalled.** In practice the single-instance mutex
  (`Local\me.yeongyu.claudepet`) means a second copy from another folder cannot be running, so
  this is theoretical. `/F` also means the pet is terminated without a graceful shutdown; worth
  confirming on hardware that nothing is lost by that (H26). Not a reason to change the entry —
  a PID-targeted kill is not available to an installer.
- **N3 — `verify_win_artifact.VERSION_RESOURCE_STRINGS` is a hand-copy of
  `build_win.VERSION_STRINGS`'s values,** kept in step only by a comment. The drift is fail-loud
  (a changed `CompanyName` in the builder would make the gate refuse the artifact rather than
  pass it silently), so this is a maintenance nit, not a hole. Importing the builder's dict
  would remove it: `build_win` imports PyInstaller lazily inside `build()`, so importing the
  module from the gate is cheap and safe.
- **N4 — the F5 observation may name the wrong Settings page, and that is worth settling on the
  re-verification round.** The comments and README say "설정 › 앱과 작업 관리자"; the hardware
  quote says "설정/작업 관리자 … 바로 위 Claude 항목은 'Claude / Anthropic, PBC'". An adjacent
  Claude entry with a publisher is the shape of **Settings › Startup apps** (and Task Manager ›
  Startup apps), both of which read the exe's `FileDescription`/`CompanyName` — which is exactly
  what F5 fixes. Settings › Apps → Installed apps would instead read Inno's ARP values, and
  `AppPublisher="Yeongyu Yang"` is already set in `installer.iss:17`, so that page should never
  have shown an empty publisher. The fix is right either way; only the provenance sentence is
  loose, and under §5 provenance is the part that has to be exact. H29.

---

### 8. Hardware-only verification (continues the H1–H21 list in
`docs-design/track-cd-review-20260913.md`)

**Which of the four defects can only be confirmed on Windows hardware.** All four fixes are
*derivable* on macOS to different depths, and it is worth being precise about which:

| finding | confirmable here | needs hardware |
| --- | --- | --- |
| **F1** | **Yes, fully.** The simulated-Windows child reproduces both failures deterministically and the fixed modules import under it. This is not a proxy for the machine — it is the same two exceptions. | Only the end-to-end `python windows\build_win.py` run (H23), for the parts the simulation does not model (PyInstaller, Inno, Qt). |
| **F2** | **The spelling, yes** — derived from `installer.iss` here, matching the hardware log. | **The registry, no.** That `install_kind()` returns `inno` against a real hive needs `winreg` on a real install (H24). |
| **F3** | **The rule as implemented, yes** (all 256 first bytes). | **The encoding itself, no** — and the `0x04`/`0x05` half is an unreproduced hypothesis by construction (H25). |
| **F4** | **The installer text and the helper text, yes.** | **The behaviour, no.** Whether `[UninstallRun]` actually runs before removal on this Inno version, and whether the app tree is gone afterwards, is hardware-only (H22, H26, H27). |
| **F5** | **The generator, yes.** | **The PE and the two UI surfaces, no** (H28, H29). |

The eight items for the re-verification round:

- **H22** *(F4, the core one)* Uninstall from Settings › Apps **with the pet running**. Expect:
  the uninstall log shows the `taskkill` `[UninstallRun]` step **before** the first file removal;
  no `Failed to delete the file; it may be in use (5)` lines; `ClaudePet.exe` and `_internal\`
  are gone; `%USERPROFILE%\.claude_pet\` and `.claude_pet.json` remain. Record the surviving-file
  count (0 expected, against 45 before) and paste the log's step order.
- **H23** *(F1)* `python windows\build_win.py` and
  `python windows\verify_win_artifact.py --version <v> --zip … --installer …` run to completion
  on a clean Windows box with **no** `sitecustomize.py` and **no** `windows\compat` on
  `PYTHONPATH` — i.e. with the session-local work-around deliberately removed, since that is what
  the fix replaces.
- **H24** *(F2)* On a real Inno install: `install_kind()` returns `inno`; the "완전 삭제…"
  confirmation box lists the **inno** plan (not the portable one); and an in-app update from that
  copy takes the silent Inno upgrade, not the folder swap. Re-run the peer's two-spelling
  experiment once more against the corrected constant so the result is recorded against the fix
  rather than against the bug.
- **H25** *(F3)* Re-read the `StartupApproved\Run\ClaudePet` first byte after disabling and
  re-enabling from **both** Task Manager and Settings › Startup apps, and sample the first byte
  of every third-party entry present. Any odd value other than `0x01`/`0x03`, or any even value
  other than `0x00`/`0x02`, is what would confirm or refute the extrapolated half; report the
  raw bytes, not a verdict. Confirm the menu item now shows checked in the reported state.
- **H26** *(F4/N2)* Confirm `taskkill /F` costs nothing: after H22, re-install and check that
  `.claude_pet.json` settings written shortly before the uninstall survived, and that no
  orphaned lock or temp file is left in `%LOCALAPPDATA%\me.yeongyu.claudepet`. Also confirm
  `taskkill` releases file handles fast enough that Inno's very next step succeeds — i.e. that
  no retry is needed.
- **H27** *(F4, in-app)* In-app "완전 삭제…" on an **inno** install: the pet closes, the helper
  runs, `unins000.exe /SILENT` completes, and the whole app tree plus ARP entry plus Start-Menu
  shortcut are gone, with only `%USERPROFILE%\.claude_pet\` left. Then the failure arm: block
  `powershell.exe` (AppLocker, or rename it in a VM) and confirm
  `uninstall kind=inno status=failed at=run-uninstaller error=<type>` with **nothing deleted** —
  the inno branch now goes through PowerShell like the portable one, so H21's condition applies
  to it too.
- **H28** *(F5)* `ClaudePet.exe` from the built zip shows "Claude Pet" / "Yeongyu Yang" in Task
  Manager › Details (Description, Company) and in the file's Properties › Details tab, with
  `FileVersion` equal to `APP_VERSION`.
- **H29** *(F5/N4)* Name the surface: which page showed `ClaudePet.exe` with an empty publisher —
  Settings › Startup apps, Task Manager › Startup apps, or Settings › Apps → Installed apps?
  Confirm it now reads "Claude Pet / Yeongyu Yang", and correct the provenance sentence in
  `windows/README.md` and `windows/build_win.py` to whichever it was.

---

### 9. What must happen before merge

1. **B2** — a gate for `build_inno_uninstall_script` (and, while there, `build_uninstall_script`),
   in a **new** file so the existing gating file's hash pin survives, with a recorded red run
   against a scratch copy that drops the wait. Verifier-owned.
2. **B1** — a separate assignment to re-review the pinned harnesses against the merged
   `claude_pet.py` and re-pin the two `REVIEWED_APP_SOURCE_SHA256` constants. Not Track F's, and
   it blocks anything merging off this branch.
3. The commit trailers must name **two different parties** for `Developer:` and `Verifier:`
   (§7), which is also what makes §2 Condition B auditable after the fact.
4. Staging by named path only — `git add windows/win_core.py windows/win_update.py
   windows/win_autostart.py windows/claude_pet_win.py windows/build_win.py
   windows/verify_win_artifact.py windows/installer.iss windows/README.md
   windows/tests/test_win_hardware_fixes.py docs-design/track-f-verification-20260914.md
   docs-design/track-f-review-20260914.md`, then `git diff --cached --name-only` read back.
   **Never `git add -A` / `git add .`** (CLAUDE.md § Release procedure step 2).
5. Note for whoever prepares the release, not for this change: `APP_VERSION` still reads `0.24`.
   The bump is release step 1 and is separately authorized; it is not this track's to make.

### 10. What this review did not check

- Anything requiring Qt, PyInstaller, Inno Setup, `winreg` or a PE parser — none is available on
  this host. §8 lists what that leaves open.
- The runtime behaviour of `_uninstall` as a whole. It was read, and its AST-visible ordering was
  checked, but no GUI was run.
- `claude_pet.py` and the repo-root `tests/`, beyond hashing them and establishing that Track F
  does not touch them. Out of scope by instruction.
- Whether the Verifier in fact opened no production file for writing (§2 Condition B): not
  determinable from an uncommitted tree. See §2.

---

## Review round 2 (2026-09-14, 01:38Z–01:44Z)

Same reviewer, same role, same worktree and HEAD (`f876e40…`). This round re-reviews the tree
**after the Developer addressed round 1's four non-blocking notes** (N1–N4) and re-checks the two
blocking items. Inputs added since round 1: the Verifier's fourth round
(`GREEN (post-review 1)`, §PR1.1–PR1.10) read in full; the changed bytes of the five files that
moved; and — new this round, because round 1's F4 argument rested on it and the assignment asks
for the citation — the **Inno Setup 6 documentation** for the `[Run]` & `[UninstallRun]` sections
(<https://jrsoftware.org/ishelp/topic_runsection.htm>) and the script-events topic
(<https://jrsoftware.org/ishelp/topic_scriptevents.htm>).

Nothing was written in the repository this round except this section. No git write command, no
production file and nothing under `windows/tests/` or `tests/` opened for writing, no untracked
file but this one touched. The two Reviewer probes are in the session scratchpad and only read.

### Verdict: **FAIL** — 3 blocking items (B1 and B2 carried, **B3 new**)

- **B1** (carried, not Track F's) — the macOS suite is red at `f876e40` itself. Re-measured this
  round, not taken on anyone's word.
- **B2** (carried, **not closed**) — `win_update.build_inno_uninstall_script` is still gated by no
  assertion anywhere, and the two tests that would cover it still skip themselves on a condition a
  no-wait implementation satisfies.
- **B3** (**new**) — **`postuninstall` is not an Inno Setup flag.** F4's ordering guarantee is real
  and is in fact *stronger* than the file claims, but `installer.iss` and `windows/README.md` both
  tell the reader it is conditional on a flag that does not exist, the gate spends its ordering
  assertion on that non-existent flag, and the three documented flags that **would** defeat the fix
  are pinned by nothing.

N1–N4 are all genuinely addressed — re-derived here rather than read off the Verifier's report —
and F1, F2, F3 and F5 remain correct on the new bytes. Details below; one new non-blocking note
(N5) in §R2.7 and the unchanged hardware list in §R2.8.

---

### R2.1 What moved since round 1

`git rev-parse HEAD` is unchanged. `git status --porcelain` now lists **four** untracked paths —
the fourth is this review record, which did not exist when round 1 hashed the tree.

`shasum -a 256`, this round, against round 1's table: **five files moved, five are byte-identical.**

| path | round 1 | round 2 | |
| --- | --- | --- | --- |
| `windows/tests/test_win_hardware_fixes.py` | `53b3582b…` | `53b3582b…` | **unchanged — §2 Condition A** |
| `claude_pet.py` | `9dd9fb12…` | `9dd9fb12…` | unchanged |
| `windows/win_update.py` | `e2de9ad5…` | `e2de9ad5…` | unchanged |
| `windows/win_autostart.py` | `3c26fbff…` | `3c26fbff…` | unchanged |
| `windows/claude_pet_win.py` | `7315a6c6…` | `7315a6c6…` | unchanged |
| `windows/win_core.py` | `a3e323c8…` | **`61e08df2…`** | N1 |
| `windows/build_win.py` | `9ba6fb64…` | **`45d1a677…`** | N4 |
| `windows/verify_win_artifact.py` | `3464a7c9…` | **`912bd9fe…`** | N3 |
| `windows/installer.iss` | `3d92f682…` | **`7b4753a7…`** | N2 |
| `windows/README.md` | `069e13cd…` | **`45ab79fc…`** | N1/N3/N4 |

```
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  windows/win_core.py
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
3c26fbffc723ba43f430225cf508dacd1218efbd1ea64d9036f6a2bea3363222  windows/win_autostart.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py
912bd9feb6b9b4e9559358a467889cc8765a1a4495ea3882fe6048808550eb08  windows/verify_win_artifact.py
7b4753a7ef75ffa6aaeca19498824b89688880207521666b78ae8a342b63e1a5  windows/installer.iss
45ab79fc562a9ea57324dc080815168fa9a218ff6883a12f63ea0e272118d273  windows/README.md
9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61  claude_pet.py
```

**AGENTS.md §2 Condition A survives a fourth round.** The gating file has now held one hash across
the RED run, two GREEN rounds, a review-fix round and this review. The Developer changed production
code twice without touching an assertion, an expected value or a fixture literal in the file that
judges it — which is the evidence §2 asks for and cannot be manufactured after the fact.

**Condition B is unchanged and still not independently checkable**, for the same reason as round 1:
the work is uncommitted, so there is no authorship to read. It becomes auditable at commit time via
the trailers, and remains a merge precondition rather than something this review can discharge.
`claude_pet.py` is still byte-identical to `git show HEAD:claude_pet.py` and
`git diff HEAD -- claude_pet.py tests/` is still empty, so the macOS half is untouched.

---

### R2.2 The four notes, re-derived

Each was checked against the source, not against the Verifier's account of it.

**N1 — addressed, and the scope now sits on the call.** `win_core.__doc__` reads
"`import_core()` adds no path and wraps no builtin … The scope belongs on the call, not on the
file: the *module body* below does insert the repository root into `sys.path`, on every platform".
Measured here rather than read:

```
F1 core APP_VERSION: 0.24
   sys.path delta  : []          # import_core() added nothing
   CDLL restored   : True        # the wrapper did not leak past the finally
   compat on path  : False
   idempotent      : True
   win_update.cp is core: True
```

**N2 — recorded rather than changed, which is what the note asked.** The `[UninstallRun]` line is
byte-identical to the one round 1 quoted; only the comment grew, and it now states both halves —
that `/IM` matches by name and an installer cannot target a pid, and that `/F` ends the pet without
a graceful shutdown, handed to hardware (H26). *But the same comment is where B3 lives — see §R2.5.*

**N3 — the gate now reads the builder, and an unreadable builder is a refusal, not a pass.** The
hand-copied table is gone. Exercised directly this round, including the discriminating arm the note
existed for (move the *builder's* value and see whether the gate follows, which a hand-copy could
not):

```
exe carrying the current strings   -> []
builder CompanyName → 'Someone Else Ltd'
                                   -> ["exe has no version resource string 'Someone Else Ltd': ClaudePet.exe …"]
builder made unreadable            -> ['cannot read build_win.VERSION_STRINGS (TypeError): the gate has no strings to look for in ClaudePet.exe']
plain MZ file, no resource         -> 4 problems
path that does not exist           -> ['exe missing, cannot check its version resource: ClaudePet.exe']  (no raise)
```

Both import shapes resolve the builder and return the same triple — `('Claude Pet', 'Yeongyu Yang',
'ClaudePet.exe')` as `windows.verify_win_artifact` and bare as `verify_win_artifact`.

**The one thing worth checking about N3 was whether it broke the F1 instrument, and it did not.**
`SimulatedWindowsImportTests`'s ONLY-BW rival row turns on `verify_win_artifact` *not* reaching the
core through `build_win`; putting the import at module top would have quietly retired that row.
Measured:

```
import verify_win_artifact (alone): build_win in sys.modules -> False
```

So the import really is deferred into `_version_resource_strings()`, and the ONLY-BW row still
kills its rival. This is the kind of change that disarms a gate as a side effect, and it did not.

**N4 — the provenance sentence no longer names a screen.** `build_win.VERSION_STRINGS`' comment,
`check_version_resource.__doc__` and `windows/README.md` now say the report reaches only as far as
"설정/작업 관리자", state that **which page it was is not recorded**, give the part that is true
regardless (startup lists read the exe's `FileDescription`/`CompanyName`; Settings › Apps reads
Inno's ARP values, whose `AppPublisher` is already set), and hand the naming to H29. That is the §5
split the note asked for.

---

### R2.3 F1, F2, F3, F5 on the new bytes — all still correct

Re-derived independently this round; only the results are quoted.

**F1.** Exactly one module under `windows/` names the core, and it is the helper:

```
F1 core-import sites under windows/ (AST):
    windows/win_core.py [(73, 'import_module("claude_pet")'), (87, 'import_module("claude_pet")')]
```

Everything else — `claude_pet_win.py`, `win_update.py`, `win_autostart.py` (transitively),
`build_win.py`, `verify_win_artifact.py` — reaches it through `win_core.import_core()`. The no-op
measurement on macOS is in §R2.2.

**F2.** Re-derived from `installer.iss` alone, without consulting the hardware log, applying Inno's
brace rule (a *leading* `{{` escapes to one literal `{`; `}` is never escaped, so a trailing `}}`
survives as two; the uninstaller appends `_is1`):

```
AppId as written : {{me.yeongyu.claudepet}}
AppId expanded   : {me.yeongyu.claudepet}}
derived subkey   : Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
constant         : Software\Microsoft\Windows\CurrentVersion\Uninstall\{me.yeongyu.claudepet}}_is1
MATCH            : True     (closing braces in the constant: 2)
```

A fresh `grep -rn '_is1'` over the whole worktree finds the two-brace spelling in
`win_update.py` (constant + comment), `claude_pet_win.py` (`_inno_registry_reader`),
`windows/README.md` and the gating file, and **no one-brace spelling outside the historical
records**. The fix is still on the right side — `AppId` is untouched, so already-installed copies
keep their ARP entry and `unins000.exe`.

**F3.** The implementation is a rule, not a table — checked structurally as well as behaviourally:

```
implementation is a single return : True
uses BitAnd (a rule, not a lookup): True
compares against int literals      : none
disagreements with (b % 2 == 0) over all 256 first bytes : none
None→False  b''→False  b'\x00'→True  b'\x01'→False  b'\x02'→True  b'\x03'→False
b'\x04'→True  b'\x05'→False  bytearray(b'\x00')→True  '\x00'(str)→False
0→False  [0]→False  memoryview(b'\x00')→False   — nothing raised
```

Every guard the assignment asked to keep is kept, the fail-safe direction is unchanged, and the
docstring keeps observation and extrapolation in separate bullets — one machine, Windows 11,
Settings › Startup apps and Task Manager › Startup apps, 2026-09-14 for the three observed bytes;
`0x04`/`0x05` and above explicitly marked a hypothesis no second party has reproduced. The README
carries the same split. It does **not** assert the rule as a universal fact about Windows, which is
what §5 requires and what the assignment asked me to confirm.

**F5.** Re-exercised with a version this repository has never held, which is the row that rules out
"write the resource by hand and commit it":

```
write_version_resource(<tmp>, "7.13")
  parses as Python        : True
  filevers/prodvers       : (7, 13, 0, 0)
  APP_VERSION (0.24) leaked? : False
  all six fixed strings + FileVersion/ProductVersion present
_version_quad: "0.25"→(0,25,0,0)  "7.13"→(7,13,0,0)  "1.2.3.4.5"→(1,2,3,4)
               "x"→(0,0,0,0)  ""→(0,0,0,0)  "0.25-rc1"→(0,25,0,0)
```

The numbers come only from the argument, which comes only from `app_version()`. The resource file
is written into a `mkdtemp` removed in a `finally`, deliberately *not* under `WORK`, because
`--clean` empties `workpath`. The gate's arms are in §R2.2.

---

### R2.4 B2 — unchanged, still open, re-checked on the current bytes

Round 1 filed this; the Verifier confirmed it as finding (i) and again as PR1.9(i) and declined to
close it in-round. Re-measured here rather than carried forward on trust:

```
grep -rln build_inno_uninstall_script windows/tests/  -> NO HITS
grep -rln build_uninstall_script      windows/tests/  -> NO HITS
```

and the skip predicate is unchanged:

```python
def _pid_wait(self):
    return any(name == "getpid" for _ln, name, _n in self._branch_calls())
```

Both `InAppInnoUninstallOrderTests.test_the_uninstaller_is_not_launched_while_the_app_is_still_running`
and `…test_a_moment_is_given_for_the_process_to_exit` return early on that predicate, so the whole
suite reports `OK (skipped=2)` while the helper's wait, its `exit 2` refusal and its
`Start-Process` are pinned by nothing. **An implementation that hands `os.getpid()` to a helper
that never waits satisfies the predicate exactly as the real one does** — the gate is satisfied by
the *shape* of the fix, not its behaviour.

The in-app half remains correct **by inspection**: `_uninstall`'s inno branch prechecks
`os.path.isfile(unins000.exe)` (refusable, before any delete), writes
`wu.build_inno_uninstall_script(argv, os.getpid())` to a `%TEMP%` `.ps1`, launches it detached,
*then* performs the irreversible deletes, *then* quits — and the generated text is line-for-line
the shape of the already-shipped portable twin. None of that is asserted anywhere.

The remedy is unchanged and is one Verifier round: a **new** gating file, so the existing file's
hash pin survives, pinning both builders' generated text, with a recorded red run against a scratch
copy that drops the wait. B3 below should be folded into the same file.

---

### R2.5 B3 (new) — `postuninstall` is not an Inno Setup flag

This is the item the assignment asked me to settle by citing the documentation I rely on. Doing so
confirmed F4's *conclusion* and refuted the *reason* written beside it in two shipped files and in
the gate's own docstring.

**What the documentation says** (Inno Setup 6 help, `[Run] & [UninstallRun] sections`,
<https://jrsoftware.org/ishelp/topic_runsection.htm>):

> "The [UninstallRun] section is optional as well, and specifies any number of programs to execute
> as the first step of *uninstallation*."

and the complete Flags list on that page:

> 32bit, 64bit, dontlogparameters, hidewizard, logoutput, nowait, postinstall, runascurrentuser,
> runasoriginaluser, runhidden, runmaximized, runminimized, shellexec, skipifdoesntexist,
> skipifnotsilent, skipifsilent, unchecked, waituntilidle, waituntilterminated

**There is no `postuninstall`.** The "post-uninstall" concept exists in Inno, but as a
`TUninstallStep` constant `usPostUninstall` reached from `CurUninstallStepChanged` in `[Code]`
(<https://jrsoftware.org/ishelp/topic_scriptevents.htm>) — not as a flag on an `[UninstallRun]`
entry.

**Three consequences, in increasing order of how much they matter.**

1. **Two shipped texts state a false fact about Inno.** `installer.iss`'s `[UninstallRun]` comment
   says "`[UninstallRun]` 항목은 postuninstall 플래그가 없으면 파일을 지우기 *전에* 돈다 — … postuninstall
   을 붙이면 안 된다", and `windows/README.md` says "`postuninstall` **없음** — 그 플래그를 붙이면 파일
   삭제 *뒤* 로 밀려 아무 소용이 없습니다". Both describe the ordering as conditional on a flag that
   does not exist. The documented guarantee is **unconditional**: an `[UninstallRun]` entry is the
   first step of uninstallation, full stop. Under AGENTS.md §5 this is the failure mode the file is
   otherwise careful about everywhere else — a written-down fact with no source, which happens to
   be wrong, sitting in the one comment a future maintainer will read before touching this entry.
   It is also exactly CLAUDE.md's own argument for why stale or wrong written facts are worse than
   absent ones.
2. **The gate's ordering assertion is vacuous.**
   `self.assertNotIn("postuninstall", flags, "postuninstall runs the step AFTER the files are
   removed — that is the failure, not the fix")` can never fail: no `installer.iss` that ISCC will
   compile can carry a flag Inno does not define. The gate's discrimination table presents
   **POSTUNINST** as a rival it rules out, and describes it as "an `[UninstallRun]` entry that runs
   *after* the files are removed … which would reproduce the failure exactly while looking like a
   fix". That rival cannot be written. This is the AGENTS.md §3 non-discriminating-test hazard in
   its purest form — an assertion that looks like the ordering pin and pins nothing — and it is the
   more serious half of B3 because the table is the evidence a reader would rely on.
3. **The flags that would actually defeat the fix are pinned by nothing.** The same page:

   > "nowait: If this flag is specified, it will not wait for the process to finish executing before
   > proceeding to the next [Run] entry, or completing Setup."
   >
   > "By default, when no wait flag is specified, Setup waits for the program to terminate before
   > proceeding to the next entry, unless the nowait, shellexec, or waituntilidle flags are used."

   So `nowait`, `shellexec` and `waituntilidle` each make Inno proceed to file removal without
   waiting for `taskkill` to terminate — which re-creates H20's race while leaving every assertion
   in `InstallerClosesTheAppTests` green. **These are real rivals, writable in one word, and the
   gate checks none of them.** The shipped entry carries `Flags: runhidden skipifdoesntexist` and
   is correct; nothing stops the next edit from adding `nowait` to "make the uninstall feel faster".

**What is right, and should be said plainly so the fix is not over-corrected.** The mechanism
itself is sound and better-founded than the file claims:

- **Ordering** — guaranteed unconditionally by the "first step of uninstallation" sentence above.
- **Waiting** — the entry carries no `nowait`/`shellexec`/`waituntilidle`, so the documented default
  (`waituntilterminated`) applies and Inno waits for `taskkill` before removing anything.
- **Tolerance** — `skipifdoesntexist` is documented for `[UninstallRun]` specifically: "the
  uninstaller won't display the 'some elements could not be removed' warning if Filename doesn't
  exist." The doc adds "When this flag is used, Filename must be an absolute path"; `{sys}\taskkill.exe`
  expands to one, so the entry satisfies it. (The gate does not check that, which is a smaller
  version of point 3 — noted, not blocking.)
- **`RunOnceId`** — documented as `[UninstallRun]`-only and warned about by the compiler when
  absent; present here.
- **`/T` omitted**, with the reason in the comment (in the in-app path the uninstaller is a
  descendant of the pet). Still a good catch.
- **`.claude_pet` is not weakened.** Re-read this round: the new entry deletes nothing,
  `[UninstallDelete]` still names only `{app}\_internal`, `{app}\ClaudePet.exe`,
  `{app}\_internal\claudepet-release.json` and `{localappdata}\me.yeongyu.claudepet`, and nothing
  under `%USERPROFILE%` appears in any delete section.

**The fix for B3 is text plus one assertion, not a mechanism change.** Correct the two shipped
sentences to state the unconditional guarantee and cite it; and, in the new gate file B2 already
requires, replace the vacuous `postuninstall` assertion's role with a pin on the flags that can
actually defeat it (`assertNotIn` each of `nowait`, `shellexec`, `waituntilidle`). Keeping the
`postuninstall` line as well is harmless; presenting it as *the* ordering pin is not.

---

### R2.6 Suites, re-run by the Reviewer this round

**Windows suite — green.** `python3 -m unittest discover -s windows/tests -t . -v`, from the
worktree root, Python 3.13.7, Darwin 25.5.0, 2026-09-14T01:41Z:

```
Ran 179 tests in 1.018s

OK (skipped=2)
```

179 = 98 `test_win_update` + 43 `test_win_autostart` + 38 `test_win_hardware_fixes`. The two skips
are B2's pair, with their declared reasons:

```
test_a_moment_is_given_for_the_process_to_exit … skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_uninstaller_is_not_launched_while_the_app_is_still_running … skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'
```

No other skip, failure or error. Both pre-existing modules are byte-identical to round 1 and green,
which is what pins the hardware-passing behaviour the assignment said must not regress — the menu
item's position/label/value format, the `startup status=on|off error=none` line, portable toggling
over a foreign path, the disabled item on a source run, the
`check status=error reason=fetch-failed:URLError cooldown=0` line, and leftover cleanup at 60 s.
`inno_silent_args` still emits `/RESTARTAPPLICATIONS`.

**macOS suite — red, and red at `f876e40` before Track F existed (B1).**
`python3 -m unittest discover -s tests -v`, 2026-09-14T01:34Z–01:38Z:

```
Ran 588 tests in 270.641s

FAILED (failures=49, errors=8, skipped=8)
```

Identical to round 1 and to all four Verifier rounds. Grouped from this run's own output:

```
  48 FAIL  test_upload_artifact_gate       (all via setUp → assert_reviewed_file)
   8 ERROR test_manual_update_transaction  (all setUpClass)
   1 FAIL  test_v024_release_contract
```

All 57 carry one cause:

```
AssertionError: claude_pet.py changed after the shared-lock/version harness was reviewed:
  expected 6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4,
  found    9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61
```

**Established again from git objects, not from the assertion**: `git show f876e40:claude_pet.py |
shasum -a 256` is `9dd9fb12…`, while `git show f876e40:tests/test_upload_artifact_gate.py` and
`git show f876e40:tests/test_manual_update_transaction.py` both pin
`REVIEWED_APP_SOURCE_SHA256 = "6f95bc8b…"`. The pin and the file it pins already disagree **at the
commit**. `git diff HEAD -- claude_pet.py tests/` is empty and
`grep -rn 'win_update\|win_core\|win_autostart\|build_win\|verify_win' tests/*.py` finds nothing,
so Track F cannot reach these modules by any route.

The brief's expectation — "the macOS suite currently passes with 7 loud skips" — describes the
sibling checkout on `main`, not this commit. Here it is 8 skips and 57 failures, and was before
Track F. Recorded plainly rather than reported as a green nobody saw.

**Why this still blocks.** AGENTS.md §8 item 5 requires the full suite green, and it is not. The
remedy is not a bump: both constants guard a *review*, and re-pinning without re-reviewing
`release.sh`, `verify_release_artifact.py` and `claude_pet.py` against the harness converts a loud
refusal into a silent pass. It needs its own assignment and is not Track F's.

---

### R2.7 Non-blocking notes

- **N1–N4 are closed.** Re-derived in §R2.2; none needs further work. N4's remaining question
  (which Windows surface showed the empty publisher) is correctly parked as H29 rather than guessed.
- **N5 — N3's single-source property is itself ungated.** `grep -rn 'VERSION_STRINGS\|_version_resource_strings'
  windows/tests/` → 0 hits, so a future edit re-introducing a hand-copied string table in
  `verify_win_artifact.py` would pass all 179 tests. The Verifier filed this as PR1.9(iii) and
  framed it correctly: the pre-N3 hand-copy was ungated in exactly the same way, so this is a gap
  to assign, not a regression. It belongs in the same new file as B2 and B3 — the discrimination
  run already exists (§R2.2), it is simply recorded in a document rather than pinned by an assertion.
- **N6 — the `skipifdoesntexist` absolute-path requirement is unpinned.** The documentation makes it
  a condition of the flag, the shipped `{sys}\taskkill.exe` satisfies it, and nothing checks it. One
  line in the same new file if it is cheap; not worth a round on its own.

---

### R2.8 Hardware-only verification — unchanged from round 1

**Which of the defects can only be confirmed on Windows hardware.** Unchanged by this round:

| finding | confirmable here | needs hardware |
| --- | --- | --- |
| **F1** | **Yes, fully.** The simulated-Windows child reproduces both failures and the fixed modules import under it — the same two exceptions, not a proxy. | Only the end-to-end run (H23), for what the simulation does not model: PyInstaller, Inno, Qt. |
| **F2** | **The spelling, yes** — re-derived from `installer.iss` this round. | **The registry, no** (H24). |
| **F3** | **The rule as implemented, yes** (all 256 first bytes). | **The encoding itself, no**; the `0x04`/`0x05` half is an unreproduced hypothesis by construction (H25). |
| **F4** | **The installer text, the helper text and now the documented Inno semantics, yes.** | **The behaviour, no** (H22, H26, H27). |
| **F5** | **The generator and the gate, yes.** | **The PE and the UI surface, no** (H28, H29). |

**H22–H29 stand exactly as written in §8 of round 1** and are not restated. One extension:

- **H22 (extended, from B3)** — when pasting the uninstall log's step order, also record whether the
  uninstaller **waited** for `taskkill` to return before the first file removal, not only that the
  step appears first. The ordering is documented; the waiting is the part a stray `nowait` would
  silently remove, and the log is the only place it is observable.

---

### R2.9 What must happen before merge — updated

1. **B2** — a gate for `build_inno_uninstall_script` (and `build_uninstall_script`), in a **new**
   file so the existing gating file's hash pin survives, with a recorded red run against a scratch
   copy that drops the wait. Verifier-owned. Unchanged from round 1.
2. **B3** — correct the `postuninstall` sentence in `windows/installer.iss` and
   `windows/README.md` to the unconditional guarantee, with the documentation cited; and pin
   `nowait` / `shellexec` / `waituntilidle` as the real ordering rivals in the new file from item 1.
   The first half is the Developer's (text only, no mechanism change); the second is the Verifier's.
   N5 and N6 fold into the same file.
3. **B1** — a separate assignment to re-review the pinned harnesses against the merged
   `claude_pet.py` and re-pin the two `REVIEWED_APP_SOURCE_SHA256` constants. Not Track F's, and it
   blocks anything merging off this branch.
4. The commit trailers must name **two different parties** for `Developer:` and `Verifier:` (§7),
   which is also what makes §2 Condition B auditable after the fact.
5. Staging by named path only, then `git diff --cached --name-only` read back. **Never `git add -A`
   / `git add .`** (CLAUDE.md § Release procedure step 2). The path list is round 1's, plus this
   record — which is already in it.
6. `APP_VERSION` still reads `0.24`. The bump is release step 1, separately authorized, and not this
   track's to make.

### R2.10 What this round did not check

- Anything requiring Qt, PyInstaller, Inno Setup (`ISCC`), `winreg` or a PE parser — none is
  available on this host. §R2.8 lists what that leaves open. In particular, **that `ISCC` rejects an
  unknown `Flags` value was not executed here**; B3 rests on the documented flag list, which is
  enough to establish that `postuninstall` is not a flag, and does not depend on how the compiler
  reacts to one.
- The runtime behaviour of `_uninstall` as a whole; it was read and its AST-visible ordering
  checked, but no GUI was run.
- `claude_pet.py` and the repo-root `tests/`, beyond hashing them and establishing that Track F does
  not touch them. Out of scope by instruction.
- Whether the Verifier in fact opened no production file for writing (§2 Condition B): not
  determinable from an uncommitted tree.

---

## Closing review (2026-09-14, 02:40Z–03:00Z)

*reviewer-f2 (REVIEWER). Neither the Track F Developer nor either Verifier; held no other role on
this change. Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`, HEAD `f876e40` with the
uncommitted Track F change. No git write command was run. The only file this round wrote inside the
worktree is this section of this record; everything else it produced lives outside any git path,
under `…/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/rev-f2/`.*

### Verdict: **FAIL** — 2 blocking items

| item | status |
| --- | --- |
| **B2** — the two uninstall-helper builders gated by nothing; the in-app ordering skipping itself | **closed in substance, with one rival class still tying → B4** |
| **B3** (second half) — retire the vacuous `postuninstall` assertion, pin the real ordering rivals | **closed** |
| **N5**, **N6** | **closed** |
| **B4** *(new, blocking, narrow)* — the helper-text gate cannot tell PowerShell **code** from a PowerShell **comment**, so a commented-out wait and a commented-out refusal both pass all 38 tests | **open**; Verifier-owned, one helper function, fix validated below |
| **B1** — the two stale `REVIEWED_APP_SOURCE_SHA256` pins under the repo-root `tests/` | **open, and not Track F's.** Blocks merge under §8 item 5 regardless of this track. |
| N7, N8, N9 | non-blocking, unchanged; N7 re-confirmed against the shipped texts this round |

Everything the closing Verifier claims about the file's construction, its rival seam and its
instruments reproduced here. The single new finding is a gap in the **gate**, not in the production
code: `win_update.py`'s two builders are correct as they stand.

### CR-R.1 Environment and hashes

```
$ python3 -VV
Python 3.13.7 (v3.13.7:bcee1c32211, Aug 14 2025, 19:10:51) [Clang 16.0.0 (clang-1600.0.26.6)]
$ uname -srm
Darwin 25.5.0 arm64
$ git rev-parse --short HEAD
f876e40
```

Re-hashed by the Reviewer, 2026-09-14T02:41Z — **every value matches CR.1 of the verification
record**, so this round and the Verifier's read the same bytes:

```
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py
8d51b49fb0e1bbd62ddf2c9da823e21c7ed0cc7157500a6da8407f1314ef65ac  windows/installer.iss
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  windows/win_core.py
53b3582b8b69a5e6a16abdcf0aa418ca6eb2088d176e42a3ed5463e624023a7c  windows/tests/test_win_hardware_fixes.py   ← the pinned value, unchanged
3791adc9a364069e1beb84ca6d3ec1bdcb0829118e91ea05162643c04b7f1c3f  windows/tests/test_win_uninstall_contract.py
```

`git diff HEAD -- claude_pet.py tests/` is **empty** (0 bytes) and neither path appears in
`git diff HEAD --name-only`, whose whole output is the seven `windows/` files. The three
user-owned untracked paths under CLAUDE.md § *User-owned files* were not touched by this round.

### CR-R.2 Suites re-run by the Reviewer

**Windows suite — green, and the two skips do not hide the ordering coverage.**

```
$ python3 -m unittest discover -s windows/tests -t .        # 2026-09-14T02:41Z, worktree root
Ran 217 tests in 1.124s
OK (skipped=2)
```

Run again with `-v` and filtered on `skip`, the entire skip list is:

```
test_a_moment_is_given_for_the_process_to_exit (…test_win_hardware_fixes.InAppInnoUninstallOrderTests) ... skipped 'PID-WAIT implementation: the helper waits on the pid instead'
test_the_uninstaller_is_not_launched_while_the_app_is_still_running (…test_win_hardware_fixes.InAppInnoUninstallOrderTests) ... skipped 'PID-WAIT implementation: os.getpid() is handed to the launched helper'
```

Both are the superseded pair inside the hash-pinned file; **no test in
`test_win_uninstall_contract.py` skips**, and the ordering obligation those two abandoned is
re-stated there unconditionally. 217 = 179 + 38 reproduces.

**The vacuity measurement reproduces independently.** Re-implemented the superseded predicate in a
scratch AST script and applied it to two sources (2026-09-14T02:48Z):

```
working tree  _pid_wait() = True   getpid at [1309, 1312]  -> old gate SKIPS
MP1 pid->0    _pid_wait() = True   getpid at [1309]        -> old gate SKIPS
```

MP1 is my own scratch copy of `claude_pet_win.py` with `build_inno_uninstall_script(argv, os.getpid())`
changed to `(argv, 0)` — the race back in full — and the old gate still skips on it while the new
gate fails on it (CR-R.3). CR.3's finding stands as written.

**macOS suite — red, from exactly one cause, and that cause is not Track F's.**

```
$ python3 -m unittest discover -s tests                      # 2026-09-14T02:52Z, worktree root
Ran 588 tests in 267.833s
FAILED (failures=49, errors=8, skipped=8)
```

Every one of the 57 failures/errors carries the same assertion:

```
48 ×  AssertionError: '9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61' != '6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4'
 8 ×  AssertionError: reviewed: expected 6f95bc8b…, found 9dd9fb12…
 1 ×  AssertionError: ['test_manual_update_transaction.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b…, final claude_pet.py is 9dd9fb12…',
                       'test_upload_artifact_gate.py:REVIEWED_APP_SOURCE_SHA256 pins 6f95bc8b…, final claude_pet.py is 9dd9fb12…'] is not false
```

Grouping key: one unittest outcome. File set: the repo-root `tests/` discovered by that command.
Window: the single run above. That is B1 and nothing else.

### CR-R.3 The rivals, rebuilt from the Reviewer's own scratch copies

Nine scratch mirrors, built by this Reviewer from the worktree bytes with occurrence-counted
`str.replace` needles, under `…/scratchpad/rev-f2/`. None is on a git path. Each run is
`CLAUDE_PET_WIN_RIVAL_ROOT=<mirror> python3 -m unittest windows.tests.test_win_uninstall_contract`
from the worktree root, 2026-09-14T02:43Z–02:58Z.

| mirror | mutation | result | first assertion |
| --- | --- | --- | --- |
| **MR0** | *unmutated copy of `win_update.py`* — negative control | **OK (38)** | — the seam itself causes no failure, so every failure below is attributable to its mutation |
| **MR1** | `Wait-Process` line deleted from **both uninstall builders only** (`build_swap_script`'s wait left intact, so the discrimination is attributable to the two builders alone) | FAILED (10) | `AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit` |
| **MR3** | inno helper launches first, then waits | FAILED (2) | `AssertionError: 5 not less than 3 : 'Start-Process' is at line 3, before the wait at line 5` |
| **MR4** | interpolated paths stop going through `ps_quote` | FAILED (7) | both quoting pins fire, in both builders |
| **MP1** | `build_inno_uninstall_script(argv, os.getpid())` → `(argv, 0)` | FAILED (1) | `AssertionError: [] is not true : build_inno_uninstall_script is not called with os.getpid(); … args=["Name(id='argv', ctx=Load())", 'Constant(value=0)']` |
| **MI1** | `nowait` added to the `[UninstallRun]` flags | FAILED (2) | `AssertionError: Lists differ: [] != ['nowait']`, twice — the no-wait pin **and** the allow-list |
| **MR5** | `write_version_resource` hard-codes the string table instead of reading `VERSION_STRINGS` | FAILED (1) | `CompanyName did not follow the source table — the generator keeps its own copy` |
| **MR6** | the wait is **commented out** in the emitted script, keeping the real pid and timeout in the comment | **OK (38)** ✗ | — see B4 |
| **MR8** | the still-alive refusal is **commented out**, likewise | **OK (38)** ✗ | — see B4 |

`MP1` and `MR3` came out byte-identical to the Verifier's `P1` (`73ef49ad…`) and `R3`
(`0197713f…`) although they were built independently, which is as much cross-check of those two
rivals as this round can give.

**The fail-closed mirror instrument works.** Forcing the case it exists for — pre-importing
`windows.win_update` from the worktree before the test module loads, so the mirror is set but does
not take effect — raises instead of reporting green:

```
RuntimeError: rival run is vacuous: windows/win_update.py resolved to
/Users/yeongyu/claude-pet-windows/windows/win_update.py, not to the mirror copy at …/MR1/windows/win_update.py
```

And `CLAUDE_PET_WIN_RIVAL_ROOT` is genuinely absent from the suite path: the 217-test run above
takes no branch on it, and the banner it prints on stderr appeared in every rival run and in none
of the suite runs.

### CR-R.4 B2 — closed in substance; **B4** is what is left

**Closed.** `grep -rln 'build_inno_uninstall_script\|build_uninstall_script' windows/tests/` now
returns the new file where it returned nothing; the helper's wait and the hand-over of the pid are
two assertions that fail separately (MR1 and MP1 above); the in-app ordering is re-stated with no
predicate that can excuse it, and `test_this_file_never_skips_itself` keeps it that way. Stating the
ordering over the whole `_ACTIONS` set rather than over `Start-Process` alone is the right call and
MR3 shows it biting.

**B4 (new, blocking, narrow).** The helper text is gated as text, and the text-level helpers
distinguish *quoted* from *unquoted* (`_outside_quotes`) but not *code* from *comment*.
`_wait_index()` takes the first line containing the substring `Wait-Process` anywhere, and
`_refusal()` scans for `Get-Process … -Id <pid>` and then for `exit <n>` the same way. So a
generated helper in which those lines are present but **commented out** satisfies every assertion.
MR6 is that rival — the "comment it out while debugging and forget" edit, which is the shape this
kind of regression actually arrives in — and this is the script a green 38-test run accepts:

```
# ClaudePet inno uninstall helper — generated by windows/win_update.py.
$ErrorActionPreference = 'Stop'
# Wait-Process -Id 424242 -Timeout 120 -- disabled while debugging
if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }
if (Test-Path -LiteralPath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe') {
  try { Start-Process -FilePath 'C:\ZZFIXTUREZZ Files\ClaudePet\unins000.exe' -ArgumentList '/SILENT' } catch { exit 3 }
}
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch { }
exit 0
```

That helper does not wait. It is H20's race, and the suite reports `OK`. MR8 shows the same for the
refusal. Under AGENTS.md §3 — "if any rival collapses onto the correct answer, the fixture is
unfinished" — the fixture is unfinished, and it is unfinished on exactly the sentence B2 was raised
about: *a rewrite dropping the wait keeps the whole suite green.*

It is blocking, and it is small. **The fix is one helper and four call sites, all inside the
Verifier-owned file; no production file is involved.** Validated in a scratch copy of the gating file
this round (mirror `FIX/`, 2026-09-14T02:58Z): add

```python
def _ps_code(line):
    """One line with quoted spans blanked AND any trailing comment removed —
    what PowerShell would actually execute."""
    stripped = _PS_STRING.sub("''", line)
    i = stripped.find("#")
    return line[:i] if i >= 0 else line
```

and route `_first()`, `assert_waits_on_our_pid`'s line, `_refusal()`'s `Get-Process` scan and its
`exit` blob, `assert_nothing_happens_before_the_wait` and `assert_action_comes_after_the_refusal`
through it. With that change the working tree stays **`Ran 38 … OK`**, MR6 fails 10 assertions,
MR8 fails 6, and MR1/MR3/MR4 keep the discrimination they already had (10 / 2 / 7). *(Watch the name:
`assert_action_comes_after_the_refusal` already binds a local `_code` from `self._refusal(text)`;
naming the helper `_code` shadows it and the file dies with `TypeError: 'int' object is not callable`.
That was this Reviewer's first attempt and is why the name above is `_ps_code`.)*

If the Coordinator judges the commented-out rival implausible rather than fixing it, then it must be
written into CR.7's "what this file does not gate" list, verbatim, rather than left unsaid — a tie
that nobody records is the thing §3 is about.

### CR-R.5 B3 — closed, and the vacuous assertion is retired in the only sense available

The new file carries **no** `postuninstall` assertion; it pins `nowait` / `shellexec` /
`waituntilidle` instead, plus an allow-list over the whole flag set so a fourth flag fails loudly.
MI1 fires both. The literal `assertNotIn("postuninstall", flags)` still stands in
`test_win_hardware_fixes.py`, which is hash-pinned and which the Verifier may not edit — and round 2
of this review said keeping that line is harmless, only presenting it as *the* ordering pin is not.
That condition is met: the ordering pin is now elsewhere and the reason is recorded in CR.4.

Two residues in that pinned file, for whoever is next assigned it — **non-blocking, and they extend
N8 rather than being new work**: the class docstring still reads "That flag is the ordering pin:
without it, an `[UninstallRun]` entry runs at the start of the uninstall", which is the sentence
round 2 refuted, and the two dead skips are still there.

The Developer's half of B3 re-read against the shipped bytes this round: `windows/installer.iss` and
`windows/README.md` both now state the unconditional guarantee, quote
`topic_runsection.htm` for both the "first step of uninstallation" definition and the
`waituntilterminated` default, name the three flags, and say plainly that the old explanation rested
on a flag that does not exist. N7 is confirmed still open and still asymmetric: `installer.iss` says
taskkill returns **`128`**, `README.md` says **"0 이 아닌 값"**, and only the second is supported.

### CR-R.6 N5 and N6 — closed

N5: `write_version_resource` is exercised with `VERSION_STRINGS` monkey-patched to sentinels, which
is the only shape that tests *derivation*; MR5 fails it, and the existing `FIXED_STRINGS` gate does
not. N6: `skipifdoesntexist` is asserted present and `Filename` asserted absolute, by drive letter
or by a constant from a named list of Inno constants that expand to absolute paths. Both are real
assertions with a rival behind them.

### CR-R.7 §3 discrimination reading of the new file

Read line by line. The file marks its ties honestly and does not count them as evidence — the
`CloseApplications` / `RestartApplications` pin says in its own docstring that it is *not* credited
with the ordering (which matters, because both were already set on the tree that failed); the
`[UninstallRun]`-before-`[UninstallDelete]` pin says in its own docstring that it is readability and
not mechanism; `VersionResourceSingleSourceTests`' second and third rows are labelled ties; and
`PortableUninstallHelperTextTests` drops R3 from its table rather than letting an inno-only rival sit
there tied. That is the standard §3 asks for, and it is rare to see it applied to the file's own
weakest rows.

The one collapse found is B4. Nothing else in the file has a rival that ties with the expected value.

### CR-R.8 B1, and whether merging main would make §8 item 5 satisfiable

**Today: no.** §8 item 5 ("the full suite is green, run by the Verifier") is unsatisfiable on this
branch by anyone, for the reason CR-R.2 measured. Nobody on Track F may fix it: `tests/` is out of
this track's scope by instruction, and the fix is a re-pin that belongs to the release.

**The re-pin is not yet a commit.** `git log --all -S<new pin> -- tests/` returns nothing, and both
branches' committed trees carry the *stale* pin: `git show main:tests/test_manual_update_transaction.py`
and `git show windows:…` both read `6f95bc8b…`, and `git show main:claude_pet.py` and
`git show windows:claude_pet.py` are both `9dd9fb12…`. **B1 is therefore a mismatch main carries
too, not something the windows branch introduced.** The re-pin exists as uncommitted preparation in
the main worktree `/Users/yeongyu/claude-pet` (HEAD `36c2118`), where `claude_pet.py` is `8d0ed11c…`
— HEAD's bytes plus the one-line `APP_VERSION` bump to `"0.25"` — and both harnesses pin that same
value, recorded with its lineage in that worktree's
`docs-design/release-v025-verification-20260913.md` by `verifier-v025`, who states there that they
held no other role on the release.

**After that work lands as the v0.25 release commit on main: yes, merging it would make §8 item 5
satisfiable** — with two conditions that are not automatic.

- The merge is clean for these paths. `git merge-base --is-ancestor main windows` is true, and
  `git log main..windows -- claude_pet.py` and `-- tests/` are both empty: the windows branch has no
  commit of its own touching either path. So the merge takes main's `claude_pet.py` and main's
  `tests/` verbatim, and the pins then agree with the merged `claude_pet.py` **by construction** —
  the same commit carries both sides of the equality, which is the only shape that is safe. A
  cherry-pick of the pins without the bump, or of the bump without the pins, re-creates B1 with the
  numbers swapped.
- **Agreement of the pin removes the single cause of all 57 failures; it does not establish that the
  rest is green.** That is a claim to be measured after the merge, by the Verifier, from the merged
  tree — not inferred from this round's cause analysis.

Note also what the merge brings with it: `APP_VERSION` becomes `"0.25"` on the windows branch. That
is main's release step 1 and is separately authorized there; it is not Track F's to make or to
anticipate.

### CR-R.9 Hardware-only verification — H22–H29 stand, one item added

**H22–H29 are unchanged from §8 of round 1, including the H22 extension added in R2.8** (when
pasting the uninstall log's step order, record whether the uninstaller *waited* for `taskkill` to
return, not only that the step ran first). Nothing in the closing round moves any of them: no
PowerShell, no `ISCC`, no Inno, no PyInstaller, no PE parser and no Qt ran on this host, so the
helper scripts remain gated as **text** and the claim that `powershell.exe` interprets that text the
way these assertions assume is still hardware-only.

Restated, so this section stands alone:

- **H22** *(F4, the core one)* — uninstall from Settings › Apps **with the pet running**: the
  `taskkill` `[UninstallRun]` step appears **before** the first file removal; no
  `Failed to delete the file; it may be in use (5)`; `ClaudePet.exe` and `_internal\` gone;
  `%USERPROFILE%\.claude_pet\` and `.claude_pet.json` still there. Record the surviving-file count
  (0 expected, against 45 before), paste the log's step order, **and record whether the uninstaller
  waited for `taskkill` to return** (R2.8's extension — the ordering is documented, the waiting is
  what a stray `nowait` silently removes).
- **H23** *(F1)* — `python windows\build_win.py` and `python windows\verify_win_artifact.py …` run to
  completion on a clean box with **no** `sitecustomize.py` and **no** `windows\compat` on
  `PYTHONPATH`.
- **H24** *(F2)* — on a real Inno install: `install_kind()` returns `inno`; the "완전 삭제…" box lists
  the inno plan; an in-app update takes the silent Inno upgrade, not the folder swap. Re-run the
  peer's two-spelling experiment against the corrected constant.
- **H25** *(F3)* — re-read the `StartupApproved\Run\ClaudePet` first byte after disabling and
  re-enabling from **both** Task Manager and Settings › Startup apps, and sample the first byte of
  every third-party entry present. Report raw bytes, not a verdict; the `0x04`/`0x05` half is an
  unreproduced hypothesis by construction.
- **H26** *(F4/N2)* — after H22, re-install and confirm settings written shortly before the uninstall
  survived `taskkill /F`, that no orphaned lock or temp file is left in
  `%LOCALAPPDATA%\me.yeongyu.claudepet`, and that handles are released fast enough that Inno's very
  next step succeeds with no retry.
- **H27** *(F4, in-app)* — in-app "완전 삭제…" on an **inno** install: pet closes, helper runs,
  `unins000.exe /SILENT` completes, app tree + ARP entry + Start-Menu shortcut gone,
  `%USERPROFILE%\.claude_pet\` left. Then the failure arm: block `powershell.exe` and confirm
  `uninstall kind=inno status=failed at=run-uninstaller error=<type>` with **nothing deleted**.
- **H28** *(F5)* — `ClaudePet.exe` from the built zip shows "Claude Pet" / "Yeongyu Yang" in Task
  Manager › Details and in Properties › Details, with `FileVersion` equal to `APP_VERSION`.
- **H29** *(F5/N4)* — name the surface that showed an empty publisher (Settings › Startup apps, Task
  Manager › Startup apps, or Settings › Apps → Installed apps), confirm it now reads
  "Claude Pet / Yeongyu Yang", and correct the provenance sentence in `windows/README.md` and
  `windows/build_win.py` to whichever it was.
- **H30** *(new this round, from CR.7 and R2.10)* — compile `installer.iss` with `ISCC` and record
  the compiler's own reaction to the flag set: no warning on the `[UninstallRun]` entry, and, in one
  throwaway copy, that an **undefined** `Flags` value is a compile error rather than an ignored word.
  The new allow-list assertion rests on the documented flag list, and the premise it leans on — that
  no `.iss` which `ISCC` compiles can carry a flag Inno does not define — has been read, never
  executed.

### CR-R.10 What this round did not check

- Anything needing PowerShell, `ISCC`, Inno, PyInstaller, `winreg`, Qt or a PE parser. None exists on
  this host; see CR-R.9.
- `_uninstall` at runtime. It was read structurally, the same limitation CR.7 states: an ordering
  correct in the AST and wrong at runtime would pass.
- `build_swap_script`. MR1 deliberately left its wait intact so the helper-text discrimination could
  not be credited to it; whatever covers it is in `test_win_update.py` and was not audited here.
- Whether the Developer and the Verifier in fact held clean hands on each other's files (§2
  Conditions A and B): still not determinable from an uncommitted tree. What *is* determinable was
  checked — the new gating file touches no production file, and no production file's hash moved this
  round.
- `claude_pet.py` and the repo-root `tests/` beyond running them and hashing them; out of scope by
  instruction, and untouched (`git diff HEAD --` on both is empty).

### CR-R.11 What must happen before merge — updated

1. **B4** — route the helper-text scans through a code-vs-comment helper, in the Verifier-owned
   `windows/tests/test_win_uninstall_contract.py`, with MR6 and MR8 (or equivalents) recorded red.
   The fix is stated and validated in CR-R.4; no production file changes.
2. **B1** — unchanged from R2.9 item 3. Not Track F's. Merging main's v0.25 release commit once it
   exists is the route; CR-R.8 states the two conditions.
3. Commit trailers must name **two different parties** for `Developer:` and `Verifier:` (§7).
4. Staging by named path only, then `git diff --cached --name-only` read back. **Never `git add -A`
   / `git add .`** — the three user-owned untracked paths are not gitignored. The path list is round
   1's, plus this record and `windows/tests/test_win_uninstall_contract.py`.
5. `APP_VERSION` still reads `0.24` on this branch. The bump is release step 1 on main, separately
   authorized, and not this track's to make.
6. Non-blocking, for whoever is next assigned `windows/tests/test_win_hardware_fixes.py`: delete the
   `_pid_wait()` predicate and its two skips (N8), and correct the docstring sentence that still
   calls `postuninstall` the ordering pin (CR-R.5). Both are recorded with their evidence and neither
   is load-bearing any more.

---

## Final review (2026-09-14, 03:16Z–03:29Z)

*reviewer-f3 (REVIEWER, Track F final sign-off). Neither the Track F Developer nor either Verifier;
held no other role on this change. Worktree `/Users/yeongyu/claude-pet-windows`, branch `windows`,
HEAD `f876e40` with the uncommitted Track F change. **No git write command was run.** The only file
this round wrote inside the worktree is this section; everything else it produced lives outside any
git path, under `…/55c3dee4-727f-4a94-b960-66540b129014/scratchpad/rev-f3/`. `diag.py`,
`release/ClaudePet.iconset/` and `release/icon_1024.png` were neither read nor written.*

### Verdict: **PASS** for Track F — F1–F5, B2, B3 and B4 are all closed

| item | status |
| --- | --- |
| **F1–F5** | closed (re-derived in rounds 1 and 2; nothing since moved their bytes) |
| **B2** | closed (closing round), and the rival class that still tied is now gone with B4 |
| **B3** | closed — both halves; the vacuous assertion stays retired (FR.5) |
| **B4** | **closed.** Rebuilt from this Reviewer's own scratch mirrors and observed failing (FR.2) |
| **N5, N6, N7, N8** | closed. N7's asymmetry is gone (FR.6); N8's two dead skips are gone (FR.4) |
| **B1** | **open, and not Track F's.** Blocks merge under §8 item 5. Resolved by the release commit on `main` — see FR.8 |
| **N10, N11** *(new, non-blocking)* | a narrow truncation blind spot `_ps_code` introduces (FR.3), and two exit-code sentences neither cited page documents (FR.6) |

Track F's own scope is finished. What remains before merge is B1, the trailers, and the staging
discipline — none of them this track's work.

### FR.1 Environment, hashes, and the two paths that must not move

```
$ python3 -VV
Python 3.13.7 (v3.13.7:bcee1c32211, Aug 14 2025, 19:10:51) [Clang 16.0.0 (clang-1600.0.26.6)]
$ uname -srm
Darwin 25.5.0 arm64
$ git rev-parse --short HEAD
f876e40
```

`shasum -a 256`, 2026-09-14T03:16:15Z, worktree root:

```
e2de9ad5c6b17929f3c54a43f87a1f3373b6df2d299b99e68b68c63d1a315635  windows/win_update.py          = CR-R.1 / B4.7
7315a6c6b93fe23db41cb89ebdeafbfceb7dedf9b3267d42114f7c9c313e30eb  windows/claude_pet_win.py      = CR-R.1 / B4.7
45d1a67741f358999dd2101ec6d312d7a0c0bad9ebcbca7bb0fc25bbec0b5b8b  windows/build_win.py           = CR-R.1 / B4.7
61e08df22d607fa44f42f17224249b50b27dad256e642c622f74d5d9111c0411  windows/win_core.py            = CR-R.1
3d8308152c3293de36451ebac2224494b82f9b3435e19614d666b9d86527483e  windows/installer.iss          = B4.7 (was 8d51b49f… at CR-R.1 — the Developer's N7 line, FR.6)
efd33cff182b72ad01aca417240c099c06cb144740d7502fe688f80f5e66f9c3  windows/tests/test_win_uninstall_contract.py   = B4.7
392f9bc3eb6f2ae020ddfeb686ba7d1c9372845952c090b038076f4027f5d84d  windows/tests/test_win_hardware_fixes.py       = B4.7
```

**`claude_pet.py` and the repo-root `tests/` are untouched.** `git diff HEAD -- claude_pet.py tests/`
is **0 bytes**; `git diff HEAD --name-only` is exactly the seven `windows/` files and names neither
path; and `shasum -a 256 claude_pet.py` is `9dd9fb12…`, byte-identical to `git show HEAD:claude_pet.py`.
`git status --porcelain` is unchanged in shape from B4.7.

### FR.2 B4 — rebuilt independently, and shown to fail

**The mirrors are this Reviewer's own.** `…/scratchpad/rev-f3/mk.py` builds them from the worktree
bytes, locating each builder by its `def` line and asserting its needle counts (`Wait-Process` line: 3
occurrences, of which the third is `build_swap_script`'s and is left alone; refusal line: 2). None is
on a git path.

| mirror | mutation | sha256 |
| --- | --- | --- |
| `MR0` | none — negative control | `e2de9ad5…` (identical to the worktree file) |
| `MR6` | the wait **commented out** in both uninstall builders, real pid and timeout kept in the comment | `bacbe720bbee7196328111fdd18a490c312404ce8522ce06701f0a9636ae4dca` |
| `MR8` | the still-alive refusal **commented out**, likewise | `7b668009b436a5016472b41508b0f6cc9f343d69d49e3f1dc0b031f1c0aa3c09` |

Both hashes came out **byte-identical to B4.2's**, though built here from the source text without
consulting that section — an incidental cross-check of the two rivals that matter, which the earlier
rounds could only give for `MR3`/`P1`.

```
$ for m in MR0 MR6 MR8; do CLAUDE_PET_WIN_RIVAL_ROOT=$SP/$m \
      python3 -m unittest windows.tests.test_win_uninstall_contract; done   # 2026-09-14T03:18Z
===== MR0 =====   Ran 38 tests in 0.185s   OK
===== MR6 =====   Ran 38 tests in 0.151s   FAILED (failures=10)
===== MR8 =====   Ran 38 tests in 0.153s   FAILED (failures=6)
```

10 and 6 — the counts the closing review predicted and B4.4 recorded. MR6's first assertion, verbatim:

```
AssertionError: -1 not greater than or equal to 0 : the generated helper never waits for the app to exit:
# ClaudePet inno uninstall helper — generated by windows/win_update.py.
$ErrorActionPreference = 'Stop'
# Wait-Process -Id 424242 -Timeout 120 -- disabled while debugging
if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }
```

MR8's:

```
AssertionError: -1 not greater than or equal to 0 : nothing checks whether the pid is still alive
after the wait, so a wait that times out is indistinguishable from one that succeeded:
…
try { Wait-Process -Id 424242 -Timeout 120 -ErrorAction Stop } catch { }
# if (Get-Process -Id 424242 -ErrorAction SilentlyContinue) { exit 2 }
```

**And the discrimination is attributable to `_ps_code` and to nothing else.** Rather than trust the
pre-fix bytes second-hand, this round neutered the helper at runtime — `m._ps_code = lambda line: line`,
the pre-B4 behaviour — in a scratch driver that touches no repo file
(`…/scratchpad/rev-f3/ident_drv.py`):

```
IDENT(_ps_code=identity) vs MR0          : ran=38 failures=0 errors=0
IDENT(_ps_code=identity) vs MR6          : ran=38 failures=0 errors=0      ← B4 reproduced
IDENT(_ps_code=identity) vs MR8          : ran=38 failures=0 errors=0      ← B4 reproduced
IDENT(_ps_code=identity) vs working tree : ran=38 failures=0 errors=0
```

One function separates "all 38 green on a helper that does not wait" from "10 red". That is the red
state and the green state of the same fixture, observed in this round, not carried over.

**The Verifier's deviation from the literal snippet is correct and is the safer form.** Measured here
on the case that separates them:

```
line     : Start-Process -FilePath 'C:\Program Files\ClaudePet\unins000.exe'   # note
literal  : "Start-Process -FilePath 'C:\\P"          ← live code severed
shipped  : "Start-Process -FilePath 'C:\\Program Files\\ClaudePet\\unins000.exe'   "
```

The length-preserving mask is what keeps the `#` index referring to the real line. B4.1's reasoning
reproduces exactly; the deviation is an improvement on the snippet, not a departure from its intent.

### FR.3 The comment-stripping helper — does it open a new blind spot?

Constructed the cases rather than reasoning about them (`…/scratchpad/rev-f3/blindspot.py`,
2026-09-14T03:19Z). Part A applies `_ps_code` to nine lines; part B runs the four `_HelperTextMixin`
assertions end-to-end over synthesized helper texts.

**The case the assignment names is handled.** A `#` inside a single-quoted path is *not* taken for a
comment:

```
if (Test-Path -LiteralPath 'C:\Tools\C#\ClaudePet\unins000.exe') { Start-Process -FilePath '…C#…' }
  -> KEPT-WHOLE
```

and a whole helper whose every path is `C:\C#\unins000.exe` passes all four assertions, exactly as the
control does. A quoted path followed by a real comment is cut at the comment and nowhere else.
`# don't: Wait-Process … is 'disabled'` — an apostrophe *inside* the comment — is still dropped whole.

**One new blind spot exists, and it runs the other way.** `_ps_code` truncates, and truncation can
only *remove* needles. Every assertion that requires a needle therefore fails loudly on a mis-cut —
but `assert_nothing_happens_before_the_wait` is a **negative** scan, and there a mis-cut hides the
thing it is looking for. `_PS_STRING` masks single-quoted spans only, so a `#` inside a *double-quoted*
span truncates live code:

```
  pre-wait Remove-Item behind a "#"     nothing_before_the_wait = PASS   ← should be FAIL
     same line, without the "#"         nothing_before_the_wait = FAIL   ← control: the assertion does bite
```

The fixture is one line placed before the wait:
`Write-Host "step #1"; Remove-Item -LiteralPath 'C:\x\_internal' -Recurse -Force`. A here-string body
line behaves the same way, and a wait sitting in the body of a multi-line `<# … #>` block comment
still counts as a wait (that one is **not** new — the raw line counted before B4 too).

**Non-blocking, for a reason that is measured and not assumed.** Neither builder can produce the
shape today:

```
build_inno_uninstall_script  lines=9   double-quote: False  here-string: False  '#' outside col 0: False
build_uninstall_script       lines=12  double-quote: False  here-string: False  '#' outside col 0: False
```

`ps_quote` emits single-quoted strings only, so reaching this rival needs two independent deviations
(introduce a double-quoted `#`, *and* move a machine-touching statement ahead of the wait) where B4's
rival needed one keystroke. B4.8 records the class honestly; what it does not say is the **direction** —
that the residue can silently weaken the pre-wait assertion rather than merely miss a comment. Recorded
here as **N10**, with the cheapest fix being the three-assertion instrument test B4.8 itself deferred,
extended by one case: a `#` inside a double-quoted span must not truncate. Whoever is next assigned
`windows/tests/test_win_uninstall_contract.py` owns it; this Reviewer may not edit that file and did not.

### FR.4 The Windows suite — 215, `OK`, and **no skips at all**

```
$ python3 -m unittest discover -s windows/tests -t .     # 2026-09-14T03:20:24Z, worktree root
Ran 215 tests in 1.110s
OK
```

The assignment's brief says "currently Ran 217, OK with 2 skips". **That is stale** — B4.6 deleted the
two tests that were skipping. A `-v` run grepped for `skip` returns three lines and not one of them is
a skip: two are test *names* containing the word (`test_this_file_never_skips_itself`,
`test_the_filename_is_absolute_as_skipifdoesntexist_requires`) and the third is
`test_win_update.LeftoverDirsTests.test_listed_and_skipped … ok`. `grep -c ' ... ok$'` over the verbose
run is **215**: every test executed.

**No skip hides ordering coverage, because there is no skip.** The two that did — the `_pid_wait()`
pair in `test_win_hardware_fixes.InAppInnoUninstallOrderTests` — are deleted along with the predicate
and the members that existed only for them; `grep -rn 'skipTest\|_pid_wait' windows/tests/` now returns
only docstring prose in the two files explaining what was removed and why. The obligation they
abandoned is stated unconditionally in `test_win_uninstall_contract.InAppInnoUninstallOrderTests`, and
`test_this_file_never_skips_itself` AST-scans that file for `skipTest`/`skip`/`skipIf`/`skipUnless`/
`SkipTest` and fails on any of them, so the hole cannot be re-opened quietly. Per-module:
`test_win_uninstall_contract` 38 `OK`, `test_win_hardware_fixes` 36 `OK`.

### FR.5 The vacuous `postuninstall` assertion stays retired

`grep -rn postuninstall windows/tests/` returns seven lines. Six are prose. The seventh is the literal
`assertNotIn("postuninstall", flags)` still executing in `test_win_hardware_fixes.py` — kept
deliberately, and **no longer presented as the ordering pin**: the class docstring now carries a
**Correction** paragraph that states the flag does not exist, cites the Flags list, says in its own
words that the line "is not the ordering pin and must not be read as one", and points at
`test_win_uninstall_contract.InstallerUninstallRunTests` for the three flags that can actually defeat
the fix. The new file carries no `postuninstall` assertion at all and pins `nowait` / `shellexec` /
`waituntilidle` plus a whole-flag-set allow-list instead. That is CR-R.5's condition, met.

### FR.6 The Developer's `installer.iss` change

**Exactly one line changed, it is a comment, and the `[UninstallRun]` entry line is byte-identical.**
The pre-edit bytes were recoverable: `…/scratchpad/rev-f2/FIX/windows/installer.iss` hashes to
`8d51b49fb0e1bbd62ddf2c9da823e21c7ed0cc7157500a6da8407f1314ef65ac`, which is exactly what CR-R.1
recorded for the file before this edit. `diff -u` against the worktree copy is one hunk, one line:

```
-; 펫이 떠 있지 않으면 taskkill 이 128 을 돌려주지만 Inno 는 종료 코드를 보지 않고, …
+; 펫이 떠 있지 않으면 taskkill 이 0 이 아닌 값을 돌려주지만 Inno 는 종료 코드를 보지 않고, …
```

The entry line is not in the hunk, and it compares byte-for-byte equal to the three places the two
records quote it (review line 353, verification lines 1133 and 1385):

```
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ClaudePet.exe /F"; RunOnceId: "CloseClaudePet"; Flags: runhidden skipifdoesntexist
```

No test file was touched and the suite still reads this file (`InstallerUninstallRunTests` parses
`ISS` at `setUp`) and is green. **N7 is closed**: `installer.iss` and `windows/README.md` now say the
same thing, "0 이 아닌 값".

**Checked against the primary sources, not against the previous rounds.** Fetched
<https://jrsoftware.org/ishelp/topic_runsection.htm>, 2026-09-14T03:26Z:

- the Flags list it returns is **the same 19 values in the same order** the comment enumerates —
  `32bit, 64bit, dontlogparameters, hidewizard, logoutput, nowait, postinstall, runascurrentuser,
  runasoriginaluser, runhidden, runmaximized, runminimized, shellexec, skipifdoesntexist,
  skipifnotsilent, skipifsilent, unchecked, waituntilidle, waituntilterminated` — and `postuninstall`
  is absent from it;
- "Specifies any number of programs to execute as the first step of uninstallation." — the comment's
  unconditional-ordering quote, verbatim;
- "By default, when processing a [Run]/[UninstallRun] entry, Setup/Uninstall will wait until the
  program has terminated before proceeding to the next one, unless the nowait, shellexec, or
  waituntilidle flags are used." — verbatim;
- "When this flag is used, Filename must be an absolute path." — the `skipifdoesntexist` condition the
  comment and N6's assertion both rest on.

So four of the comment's five claims are quotations of the page it cites, and the test file's
`NO_WAIT_FLAGS` and allow-list are drawn from the same documented list.

**N11 (new, non-blocking): two clauses in that sentence are still not documented by either source
cited.** The Inno page "contains no information about whether the program's exit or return code is
checked or ignored", so "Inno 는 종료 코드를 보지 않고" has no citation; and Microsoft's taskkill
reference (<https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill>,
fetched 2026-09-14T03:27Z) documents **no exit codes at all** — it has no return-code section — so
"0 이 아닌 값" is the conventional claim rather than a documented one. This is not a regression: the
Developer's edit strictly weakened an unsourced specific number (`128`) to the safer general one and
made the two documents agree, which is what N7 asked for. What is left is smaller than N7 and is
hardware-checkable — see **H31**. The same two clauses appear in `windows/README.md` lines 121–123 and
should move together if either is corrected.

### FR.7 The macOS suite — still one cause, and that cause is B1

```
$ python3 -m unittest discover -s tests        # 2026-09-14T03:22:23Z–03:26:54Z, worktree root
Ran 588 tests in 270.973s
FAILED (failures=49, errors=8, skipped=8)
```

Grouping key: one unittest outcome. File set: the repo-root `tests/` discovered by that command.
Window: the single run above. All **57** failing outcomes carry an `AssertionError`, and across those
57 lines exactly **two** 64-hex values occur, 58 times each: the stale pin
`6f95bc8b923a58ddbec053d2a83f9aeb1645a05362ad5b3427d773a87956d2e4` and this checkout's
`claude_pet.py`, `9dd9fb12b7965a9feac934684201201279280af0486f9516543988e017d66a61`. No third hash and
no other assertion text appears. CR-R.2's measurement reproduces on byte-identical inputs.

### FR.8 B1 — stated explicitly, because it is the one thing this track cannot close

**B1 (the two stale `REVIEWED_APP_SOURCE_SHA256` pins under the repo-root `tests/`) is not resolved
here. It is resolved by the v0.25 release commit on `main`, which carries an independent verifier's
re-pin recorded in the main worktree's `docs-design/release-v025-verification-20260913.md`; merging
that commit into this branch is what makes AGENTS.md §8 item 5 satisfiable.**

Each half re-checked in this round rather than carried over:

- **The re-pin is real and independent.** `/Users/yeongyu/claude-pet` (HEAD `36c2118`) has
  `claude_pet.py` at `8d0ed11cafbc27ef00d31341e5499e447412963c0ceac02bd0a4fa9e8660eb0c` — HEAD's bytes
  plus the one-line `APP_VERSION = "0.25"` — and both `tests/test_manual_update_transaction.py` and
  `tests/test_upload_artifact_gate.py` pin that same value. The record's header names
  `verifier-v025`, states they "Held no other role on this release", and that they edited only files
  under `tests/` and ran no git write command.
- **It is not yet a commit.** `git log --all -S8d0ed11c… -- tests/` returns **0 lines**. Both branches'
  committed trees carry the stale pin (`git show main:…` and `git show windows:…` both read
  `6f95bc8b…`) over an identical committed `claude_pet.py` (`9dd9fb12…` on both). **B1 is a mismatch
  `main` carries too, not something the windows branch introduced.**
- **The merge is clean for these paths.** `git merge-base --is-ancestor main windows` is true and
  `git log main..windows -- claude_pet.py tests/` is **empty** — the windows branch has no commit of
  its own touching either path — so the merge takes main's `claude_pet.py` and main's `tests/`
  verbatim and the pins agree with the merged source **by construction**. A cherry-pick of the pins
  without the bump, or of the bump without the pins, re-creates B1 with the numbers swapped.
- **Agreement of the pin removes the single cause of all 57 failures; it does not establish that the
  rest is green.** That is a measurement to be taken after the merge, by the Verifier, from the merged
  tree.

Note what the merge brings with it: `APP_VERSION` becomes `"0.25"` on this branch. That is main's
release step 1, separately authorized there, and not Track F's to make or to anticipate.

### FR.9 Hardware-only verification — H23–H31, in the order one session should run them

Nothing in this round moved any hardware item: no PowerShell, no `ISCC`, no Inno, no PyInstaller, no
`winreg`, no PE parser and no Qt ran on this host, so the helper scripts remain gated as **text**.
The content of H22–H30 is CR-R.9's, unchanged; what follows re-orders them so a single session leaves
the machine in the state the next item needs, and adds **H31**.

1. **H23** *(F1)* — on a clean box with **no** `sitecustomize.py` and **no** `windows\compat` on
   `PYTHONPATH`: `python windows\build_win.py`, then `python windows\verify_win_artifact.py …`, both to
   completion. Everything below needs this artifact.
2. **H30** *(B3 premise)* — compile `installer.iss` with `ISCC` and record the compiler's own reaction
   to the flag set: no warning on the `[UninstallRun]` entry, and, in one throwaway copy, that an
   **undefined** `Flags` value is a compile error rather than an ignored word. Do it while the `.iss`
   is in hand and before anything is installed; the new allow-list assertion rests on this premise and
   it has been read, never executed.
3. **H28** *(F5)* — `ClaudePet.exe` from the built zip shows "Claude Pet" / "Yeongyu Yang" in Task
   Manager › Details and in Properties › Details, `FileVersion` equal to `APP_VERSION`. Read-only on
   the artifact; no install needed yet.
4. *Install via the Inno installer.* **H24** *(F2)* — `install_kind()` returns `inno`; the "완전 삭제…"
   box lists the inno plan; an in-app update takes the silent Inno upgrade, not the folder swap. Re-run
   the peer's two-spelling experiment against the corrected constant. Reversible, so it precedes every
   destructive item.
5. **H25** *(F3)* — re-read the `StartupApproved\Run\ClaudePet` first byte after disabling and
   re-enabling from **both** Task Manager and Settings › Startup apps, and sample the first byte of
   every third-party entry present. **Report raw bytes, not a verdict**; the `0x04`/`0x05` half is an
   unreproduced hypothesis by construction. Leaves autostart enabled, which the next item needs.
6. **H29** *(F5/N4)* — on those same screens: name the surface that showed an empty publisher
   (Settings › Startup apps, Task Manager › Startup apps, or Settings › Apps → Installed apps), confirm
   it now reads "Claude Pet / Yeongyu Yang", and correct the provenance sentence in
   `windows/README.md` and `windows/build_win.py` to whichever it was.
7. **H27** *(F4, in-app)* — **failure arm first**, because it is the non-destructive one: block
   `powershell.exe` and confirm `uninstall kind=inno status=failed at=run-uninstaller error=<type>`
   with **nothing deleted**. Then the success arm: in-app "완전 삭제…" on the inno install — pet closes,
   helper runs, `unins000.exe /SILENT` completes, app tree + ARP entry + Start-Menu shortcut gone,
   `%USERPROFILE%\.claude_pet\` left.
8. *Re-install.* **H22** *(F4, the core one)* — uninstall from Settings › Apps **with the pet running**:
   the `taskkill` `[UninstallRun]` step appears **before** the first file removal; no
   `Failed to delete the file; it may be in use (5)`; `ClaudePet.exe` and `_internal\` gone;
   `%USERPROFILE%\.claude_pet\` and `.claude_pet.json` still there. Record the surviving-file count
   (0 expected, against 45 before), paste the log's step order, **and record whether the uninstaller
   waited for `taskkill` to return** — the ordering is guaranteed by the section's definition, the
   waiting is what a stray `nowait` silently removes and the log's order would not show.
9. **H26** *(F4/N2)* — immediately after H22, before re-installing anything: settings written shortly
   before the uninstall survived `taskkill /F`, no orphaned lock or temp file is left in
   `%LOCALAPPDATA%\me.yeongyu.claudepet`, and handles are released fast enough that Inno's very next
   step succeeds with no retry.
10. **H31** *(new this round, from N11)* — *re-install, then uninstall from Settings › Apps with the
    pet **not** running.* Record `taskkill`'s actual `ERRORLEVEL` when no matching process exists, and
    confirm the uninstall completes normally despite it. This is the one claim in `installer.iss` and
    `windows/README.md` that neither cited page supports — the Inno page says nothing about whether a
    `[Run]`/`[UninstallRun]` program's exit code is checked, and Microsoft's `taskkill` reference
    documents no exit codes at all. Destructive, so it goes last.

### FR.10 What this round did not check

- Anything needing PowerShell, `ISCC`, Inno, PyInstaller, `winreg`, Qt or a PE parser. None exists on
  this host; that is why FR.9 exists at all. In particular, "PowerShell treats an unquoted `#` as
  starting a comment" is the premise `_ps_code` rests on and it was reasoned about here, never executed.
- `_uninstall` at runtime, and `build_swap_script` — unchanged limitations from CR.7 / CR-R.10. `MR1`
  was again built so that `build_swap_script`'s own wait stays intact, so nothing above is credited to it.
- Whether the Developer and the Verifier in fact held clean hands on each other's files (§2 Conditions
  A and B): still not determinable from an uncommitted tree. What *is* determinable was checked — no
  production file's hash moved in the B4 round (FR.1 against B4.7), and the two gating files are the
  Verifier's own.
- The macOS suite beyond running it and attributing its failures; `claude_pet.py` and the repo-root
  `tests/` are out of this track's scope by instruction and are untouched (FR.1).

### FR.11 What must happen before merge

1. **B1.** Not Track F's. The route and its two conditions are in FR.8.
2. **Commit trailers must name two different parties** for `Developer:` and `Verifier:` (§7, §8 item 1).
3. **Stage by named path only**, then read back `git diff --cached --name-only`. **Never `git add -A`
   / `git add .`** — `diag.py`, `release/ClaudePet.iconset/` and `release/icon_1024.png` are untracked
   and not gitignored. The path list is round 1's, plus this record and
   `windows/tests/test_win_uninstall_contract.py`.
4. `APP_VERSION` still reads `0.24` on this branch. The bump arrives with main's release commit; it is
   not this track's to make.
5. Non-blocking, for whoever is next assigned `windows/tests/test_win_uninstall_contract.py`: **N10** —
   the three-assertion instrument test for `_ps_code` that B4.8 deferred, extended by the
   double-quoted-`#` case FR.3 measured.
6. Non-blocking: **N11** — the two exit-code clauses in `windows/installer.iss` and
   `windows/README.md`, to be settled by H31 and corrected together if H31 refutes either.
