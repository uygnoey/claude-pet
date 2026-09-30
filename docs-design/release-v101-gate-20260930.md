# v1.0.1 — execution gate, Coordinator sign-off, release operator

Written by the Coordinator for this release: the main Claude Code session on the user's Mac
(claude-pet-05, 2026-09-30). This one file supplies AGENTS.md §6 items 1–5 for v1.0.1.

## What is being released
- **Tip:** `cd85727` on `dev`. The release commit is `a23d384` "release: ClaudePet v1.0.1". It sits on
  top of the fix merged at `797fcda`:
  - `45669a8` builds arm64 with the python.org universal2 Python and thins it; `check_build_python()`
    refuses targets above macOS 12.0.
  - `797fcda` adds the gating tests.
- **Follow-ups after the release commit:** `4b0cbf1` contract tests, `eeaea9a` usage line (docstring
  only), `cd85727` pin.
- **Why:** the published arm64 `ClaudePet.zip` of v0.23, v0.24, v0.26 and v1.0.0 each carries minos 26.3
  on `Contents/MacOS/python`. The dmg and other versions were not checked. The full minos gate was run
  on v1.0.0 only: 56 slices at 26.3. The in-app updater on Apple Silicon picks `claudepet.zip` first.
- **User authorization, verbatim.** The user typed these in this Coordinator session, directly. The
  subagents received them relayed from here, which is why a23d384's body says "relayed by the
  Coordinator"; both are true from each writer's position:
  - "v1.0.1 릴리즈까지 바로 진행해" — authorizes the release sequence. It changes nothing about the gate
    and makes no ineligible agent eligible for `[ASK-OP]` steps.
  - Earlier in the thread: "수정해줘", about the arm64 minimum.

## Items 1–3 — gate evidence
1. **Full suite from a clean tree at the tip.**
   - Verifier minos-verify: `python3 -m unittest discover -s tests` → `Ran 934 tests — OK (skipped=8)`.
     This was on 38fe952, whose tree is identical to cd85727; the rebase changed trailers only.
   - Reviewer: the same result in a clean scratch worktree at cd85727.
   - CI run on cd85727: macOS full suite and Windows gating contract both success.
2. **Red before green.**
   - `tests/test_minos_gate.py` against origin/dev 629bbb5: `Ran 26 — FAILED (failures=14, errors=19)`.
     Reproduced independently by minos-review. At the fix: `Ran 26 — OK`.
   - The v1.0.1 contract module against 797fcda: 7 failures.
   - The old verifier pin against eeaea9a: 48 `test_upload_artifact_gate` failures, all refused by the pin.
3. **Release notes checked.** minos-review: 3 top-level bullets, 235 normalized characters, no forbidden
   content. The claims are tied to source by the contract tests.

## Item 4 — Coordinator sign-off
- **Separation:** Developer–Verifier separation (§2) held on every commit:
  - minos-dev edited `release.sh`, `verify_release_artifact.py`, `claude_pet.py`, `RELEASE_NOTES.md`
    and `CLAUDE.md`.
  - minos-verify edited only `tests/`.
  - minos-review is the `Verifier:` on the three test-only commits 797fcda, 4b0cbf1 and cd85727. It
    confirmed their red, following the precedent of d0ed768/daf1b7e, where cwdfix-review did the same.
    It is Reviewer on everything else and signed off both the fix and the release commits. So the §1
    one-role rule does not hold on those three test commits; it is stated here rather than hidden.
- **Certification:** I certify v1.0.1 ready for the execution phase.
- **Not verified:**
  - Developer ID signing and notarization of the thinned arm64 bundle. The reviewer checked it with an
    ad-hoc signature only, `codesign --verify --deep --strict`.
  - A launch on a real macOS 12–26.2 Apple Silicon machine. None is available.

## Item 5 — Release operator
- **Ineligible:**
  - Coordinator: this session.
  - Developer: minos-dev. Verifier: minos-verify. Reviewer: minos-review.
  - Every agent of the v1.0.0 cycle and of the site change.
- **Designated operator:** `release-operator-v101`, created after this file is committed, for this one
  job.
  - Runs `./release.sh build`, `sign`, `notarize`, `universal`, `dmg`, `publish` individually.
  - Never runs `all` / `ship` / bare.
  - Records each step and stops at the first failure.
- **Windows:** the Windows artifacts are built on the user's Windows machine from the gate commit
  (unsigned, as always) and uploaded to the same release.
