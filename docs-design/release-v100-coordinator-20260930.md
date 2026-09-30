# v1.0.0 — Coordinator sign-off and release operator designation

Written by the Coordinator for this release: the main Claude Code session on the user's Mac (session
`40157a9c-9e95-4cba-845b-06ada6807462`, 2026-09-30). This file supplies AGENTS.md §6 items 4 and 5. Items 1–3 are
the gate record `release-v100-gate-20260930.md`.

## What is being released
- **Release commits** `59b807e` "release: ClaudePet v1.0.0" and `8e5a722` "docs: v1.0.0 노트 — 첫 정식 버전이라고 적는다"
  (the user, 2026-09-30: "이거부터 정식 릴리즈야", "1.0.0 이자나") on `dev`, on top of the merge `6785313` of
  `claude/fix-cli-cwd-codex-account` (commits `daf1b7e` … `d4e06c3`) into `dev` (which carried `fd67b55`, the
  Windows side of v0.26.1, not on `main`). `main` fast-forwards to the gate commit that adds this file; the tag
  `v1.0.0` goes on that commit. macOS and Windows artifacts are both built from it (Windows: unsigned, as always).
- **User authorization, verbatim** (2026-09-30, in this session): "검증 및 리뷰 하고 windows에서도 orca로 claude
  띄워서 테스트하고! 문제 없으면 버전 v1.0.0으로 릴리즈해! mac, windows 모두다". This is a blanket authorization of
  the release sequence under AGENTS.md §6's four guards; it changes nothing about the gate, and it does not make
  any ineligible agent eligible for the `[ASK-OP]` steps.

## Item 4 — Coordinator sign-off
I certify this release ready for the execution phase, on this evidence:
- **The gate is GREEN at G2 `8e5a722`** — `release-v100-gate-20260930.md` (author `cwdfix-verify`): clean-tree
  re-run `python3 -m unittest discover -s tests -v`, 2026-09-30T04:37:02Z → 04:42:27Z, 902 ran, OK (8 skipped: 7
  opt-in live checks + the no-built-bundle check a fresh worktree always skips), exit 0; the same at G `59b807e`;
  CI `36669138534` on G green on macOS and Windows; notes format and claims green via the contract module; the
  published sections byte-identical. Its one condition — the Reviewer's approve verdict for G and G2 — is met by
  `release-v100-review-20260930.md`.
- **A reading I am making, stated so it can be contested.** On the test-only commits A `daf1b7e`, D `d0ed768` and
  the pin moves C `d82bb22`, F `d4e06c3`, the `Verifier:` trailer names `cwdfix-review`, because AGENTS.md §7's
  test-only row puts there the agent that confirmed the red — the tests' author, `cwdfix-verify`, could not.
  Read commit by commit, §8 item 4 ("the Reviewer is neither Developer nor Verifier") is then not met on those four.
  I read it change by change, as §1 defines roles ("Roles are per-change"): on this change the Developer is
  `cwdfix-dev`, the Verifier is `cwdfix-verify`, and `cwdfix-review` wrote neither code nor tests; its red
  confirmation is an independent check, and the same red was observed on CI (`36662979506`, `36665455747`).
  If the user or a later auditor prefers the commit-level reading, a sign-off on those four commits from an agent
  with no role on this release closes it; nothing in the shipped bytes depends on which reading is taken.
- Every change carries red-before-green evidence with actual output: CI `36662979506` (`daf1b7e`, tests only — red:
  macOS 888 ran / 43 failures / 1 error, Windows 80 / 26 / 1), CI `36665455747` (`d0ed768`, follow-up tests only —
  red: 11 failures on both jobs = exactly the new gates), CI `36665491426` (`d4e06c3` — green on both), CI
  `36666667778` (`6785313`, the dev merge — green on both); the local records under the Verifier's and Reviewer's
  scratch directories are summarised in each commit body.
- Developer–Verifier separation held on every commit (`cwdfix-dev` edited only `claude_pet.py` (+ the release
  commit's docs/version), `cwdfix-verify` only tests); the Verifier's scratch reference implementation outside the
  repository was ruled compatible with §2 Condition B by the Reviewer and is declared in `daf1b7e`'s body.
- A Reviewer who wrote neither the code nor the tests (`cwdfix-review`) raised R1 (FAIL, fixed before A) and signed off
  R1-bis, R2, R3/R3-bis, the merge, G and G2 (`release-v100-review-20260930.md`: APPROVE for A–F, the merge, G and G2).
- Windows real-machine verification by a Windows-side Verifier (`cwdfix-win-verify`, a Claude Code session launched
  on the user's Windows 11 machine through Orca): rounds 1, 1b, 2 — see `release-v100-windows-verification-20260930.md` (round 2 on `d4e06c3`: OK). Round 3
  ran the port suite on the Windows box at G2 before building — including fd67b55's four Qt tests, which no Mac
  run and no CI job can execute (no PySide6 there); that session reported them green in its terminal at 13:40 KST
  ("Tests are green"); the counts will be in its round-3 report, recorded after publication.
- Not verified, stated so nobody reads it into this sign-off: the Codex header on Windows (that machine's Codex
  token expired 2026-07-03), the login shape on Windows (opens a browser), a private-folder CLI run that actually
  refreshes the token (cannot be forced), and the end-to-end in-app update to 1.0.0 (needs the published release).

## Item 5 — Release operator
`[ASK-OP]` requires the user's authorization for this artifact, every §6 gate recorded first, and execution by an
agent that held no other role on this release. **Ineligible:** Coordinator — this session; Developer —
`cwdfix-dev`; Verifier — `cwdfix-verify`, `cwdfix-win-verify`; Reviewer — `cwdfix-review`; and every agent of the
v0.26 cycle. **Designated operator:** `release-operator-v100`, created after this file is committed, for this one
job; runs the steps individually, never `all` / `ship` / bare, records each step, stops at the first failure.
The Windows upload (`[ASK]`, no signing) is done by `cwdfix-win-verify` after the macOS release exists.

Signed: Coordinator, 2026-09-30.
