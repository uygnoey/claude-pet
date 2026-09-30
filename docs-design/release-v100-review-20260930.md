# ClaudePet v1.0.0 — Reviewer record for `claude/fix-cli-cwd-codex-account` and the release commit (AGENTS.md §1, §8 item 4)

## Verdict: **APPROVE** — A–F, the dev merge 6785313, G 59b807e and G2 8e5a722. No open blocking item.

Every blocking finding raised during the review was fixed before the commit it concerned. The
non-blocking caveats are listed at the end.

- **Reviewer:** `cwdfix-review`, a Claude Code subagent. On this change and this release it
  held **no other role**: it was not the Developer (`cwdfix-dev`), the Verifier
  (`cwdfix-verify`), the Coordinator, or the Windows-side Verifier (`cwdfix-win-verify`).
- **What it did not do:** it authored no production or test line and edited no tracked file.
  It ran no git write command except `git worktree add/remove` for scratch worktrees at the
  Coordinator's request (`merge-wt`, `g-wt`; both removed). It ran nothing from `release.sh` or
  `build_app.sh` and never ran the `claude` CLI. It read no `~/.claude` transcript or
  `~/.codex` file and wrote nothing under `~/.claude_pet/`. It created no file in this tree
  except this one.
- **Real-machine actions (this Mac):**
  - two launchd probes under `me.yeongyu.claudepet.probe-review-*` labels, running only
    `/bin/pwd` and `/bin/sh`, all booted out;
  - one read-only `log show` of launchd lines for 2026-09-30 06:15:20–06:17:40 KST.
- **Eligibility:** having reviewed this release, it is **not** eligible to operate it (§1).
- **Written (UTC):** 2026-09-30T04:37Z.
- **Where the evidence is:** the session scratchpad `review/` folder (red, green and full-suite
  logs; rival harnesses and reports). Rivals were run in scratch copies; the repo's
  `claude_pet.py` was never edited.

## Verdicts, with one-line evidence

| Phase | Commit(s) | Verdict | Evidence |
|---|---|---|---|
| R1 | tests before A | FAIL → fixed | Red 80/26/1, 37/13/0, 40/1/0 against 13c6821. Of 40 rivals, 3 survived: unstripped token (×2), cwd-unusable. The v026 re-tie was shape-bound: it rejected 4 legitimate implementations and caught no rival on its own. |
| R1-bis | **A daf1b7e** | APPROVE | Red 80/27/1, 38/15/0, 40/1/0; 44/44 rivals caught; the v026 re-tie is now a property. The committed bytes equal the reviewed ones plus the two requested system32 text fixes (byte diff checked). |
| R2 | **B d79b858** | APPROVE | `cwdfix-dev.patch` reproduces `26ebcf21…`; only recovery and Codex definitions changed (AST diff). Green 80/38/40; full suite 888 OK in a scratch tree. The launchd probe confirmed rc 5 for a same-label bootstrap and that `bootout gui/<uid>/<label>` removes a `submit` job. The v0.26-leftover gap was raised here and closed in E. |
| R2 | **C d82bb22** | APPROVE | Only the two `REVIEWED_APP_SOURCE_SHA256` literals moved, to `26ebcf21…`. Nothing those tests exercise changed. Old pins fail on the fix; new pins pass. |
| R3 / R3-bis | **D d0ed768** | APPROVE | Red 88 ran / 11 failures against 26ebcf21, only the new gates. 28/28 rivals caught once C19/C20/C22 (callers outside `run_gui`; start after `runEventLoop()`) were closed. The committed file (`f3b0fa74…`) is the approved `2f5086a6…` plus one docstring sentence I had flagged as an optional nit (text only). |
| R3 / R3-bis | **E 5cca59d** | APPROVE | `claude_pet.py` = `843623b5…`; its docstring-stripped AST is identical to the reviewed `1fe11e81…`. The launchd log confirms 3 CLI runs in the 06:15 attempt (41913, 42066 and 42228; the two respawns "because inefficient"). Startup cleanup: within this process it cannot boot out a live recovery job (same `_recovery_busy` lock, one creator), and it clears the login label at every launch. |
| R3-bis | **F d4e06c3** | APPROVE | Pure re-pin to `843623b5…`. Green 88/38/40/18/64 on D+E+F. |
| dev merge | **6785313** | APPROVE (caveat 1) | `git diff d4e06c3 6785313` is byte-identical to fd67b55's own diff; `git diff 9cd98a3 6785313` is byte-identical to `13c6821..d4e06c3`; no conflict residue. Full suite 896 OK (8 skipped); port suite 252 OK (23 Qt skips). |
| release | **G 59b807e** | APPROVE | Notes are a pure insertion above `**v0.26.1**` (3 bullets, 304 chars). The CLAUDE.md section was checked against source and records (port paths `_login_claude`/`_install_claude`; py2app's `chdir_resource` → `Contents/Resources`; observation counts). The contract rename weakened nothing: no pin constant removed or changed; 33 tests unchanged; the v0.26.1 tests moved with identical bodies; the new published pin equals the v0.26.1 tag's bytes. 5 mutations were each caught by their claim tie; full suite 902 OK (8 skipped). |
| release | **G2 8e5a722** | APPROVE | `RELEASE_NOTES.md` only, one sentence ("첫 정식 버전인 1.0.0"). Published bytes unchanged; 313 chars; contract module 46 OK. |

## Caveats (non-blocking)

1. **fd67b55's Qt-dependent port gates were not exercised by me.** These are
   `CodexOnboardingSuppressionTests` and the other 19 Qt pixel gates. They skip loudly without
   PySide6, which is absent on this Mac and not installed by the Windows CI job (whose
   port-suite step is `continue-on-error`). Before the v1.0.0 Windows build, run the port suite
   on the Windows box at the release commit.
2. **Unmeasured Windows paths:** the Windows login path (a visible PowerShell console by
   design), and the `taskkill /T` timeout branch of `_run_refresh_job`.
3. **Not re-verified by me:** the CI run IDs and the Windows round reports cited in commit
   messages. I relied on them only where this record says so.
