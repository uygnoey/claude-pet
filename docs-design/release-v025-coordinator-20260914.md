# v0.25 — Coordinator sign-off and release operator designation

Written by the Coordinator for this release: the main session
`55c3dee4-727f-4a94-b960-66540b129014`. This file supplies AGENTS.md §6 items 4 and 5,
which the gate record `release-v025-gate-20260914.md` flagged as missing (C4, C5). It
supplies nothing else; items 1–3 are that record's, and the review it required (R1) is
`release-v025-review-20260914.md`.

## What is being released

- **Release commit** `aaf0ca6` "release: ClaudePet v0.25" on `main`, plus the
  documentation correction `f9043ef` that the release commit's own review demanded.
  `main` is at `f9043ef`.
- **Windows branch** `38b2eb4`, which merges both, is what the Windows artefacts are
  built from. Nothing on that branch reaches macOS users; the two trees share
  `claude_pet.py` byte for byte.
- **Tag to create:** `v0.25`. It does not exist locally or on the remote.

## Item 4 — Coordinator sign-off

I have read the gate record, the release review, the docfix verification, and the four
track records (`track-a-*`, `track-b-*`, `track-bw-*`, `track-f-*`). I certify this
release ready for the execution phase, on this evidence:

- **The suite is green from a clean tracked tree.** The gate verifier ran
  `python3 -m unittest discover -s tests -v` at `aaf0ca6` and recorded 612 tests, OK with
  7 loud opt-in skips, exit 0. The docfix verifier repeated it at the docfix state and
  recorded 612 OK with 8 such skips, plus the Windows suite at 215 OK.
- **Every behavioural change carries red-before-green evidence with actual output**, in
  the four track verification records. Two of them pin the RED baseline by the module's
  SHA-256 so the red state cannot be claimed from memory.
- **Developer–Verifier separation held on every track**, and each track was passed by a
  Reviewer who developed and verified none of it. The release commit itself was reviewed
  by `reviewer-v025`, who held no role on the release; it found two documentation defects
  and both are fixed in `f9043ef`.
- **The release notes pass the frozen format** — three top-level bullets, no nesting,
  290 characters normalised against the 450 cap, no hashes, identifiers, paths or test
  names, and no number at all. The v0.24 and older sections are byte-identical to what
  is published, verified against `git show v0.24:RELEASE_NOTES.md`.
- **The version set is coherent**: `APP_VERSION` 0.25, the newest notes heading v0.25,
  `setup.py` deriving both plist keys from that one literal, the usage example in
  `verify_release_artifact.py` at 0.25, newest existing tag v0.24, and no v0.25 tag on
  any ref.
- **The user's own words authorize this release**, recorded verbatim in `aaf0ca6`:
  "그거 다되면, 릴리즈까지 마무리 해놔라! 그리고 세션 모두 종료해!" and
  "다 되면 릴리즈하고 세션 모두 종료해~!".

**Two things this sign-off does not cover, stated so nobody reads them into it:**

1. **The Windows artefacts in `release/` are the v0.24 build** (gate finding W1) and must
   not be uploaded. The v0.25 zip and installer exist only on the user's Windows machine,
   built from `windows` at `6d94c4d`; they arrive here on a temporary branch and must be
   hash-checked against what that session reported before any upload:
   `claude-pet-win.zip` `6f2be9f25ab58bc48311847e9cc9f84b5abe3b623a8f5778d58f15288b3b433d`
   (72,507,309 bytes) and `claude-pet-win-setup.exe`
   `e0c461942fdbd6f055c7d15c5377736c90ed2e0b03b7665a2b1c389a2c907b3e` (56,058,641 bytes),
   with the in-zip marker reading version 0.25. **They are unsigned**, as v0.24's were.
   A rebuild from `38b2eb4` is equally acceptable and would carry the documentation
   corrections; either way the digests must be re-measured here, never taken on report.
2. **The end-to-end Windows in-app update (v0.24 → v0.25) has not been exercised**, because
   it needs a published higher version to climb to. It is the first thing to verify after
   publication, and the third release-notes bullet rests until then on the Windows
   session's component checks plus this repository's gating tests, not on a live upgrade.

## Item 5 — Release operator

**The rule, from CLAUDE.md:** `[ASK-OP]` requires the user's authorization for this
artifact, every §6 gate recorded first, and execution by an agent that held **no other
role on this release — not Developer, not Verifier, not Reviewer, and not Coordinator**.
No authorization lifts that last condition; it is separation of duties.

**Ineligible, by role held on this release:**

| Role | Who |
| --- | --- |
| Coordinator | this session (`55c3dee4-…`) |
| Developer | `developer-a`, `developer-b`, `developer-cd`, `developer-bw`, `developer-f`, `developer-g`, and this session for the documentation commits |
| Verifier | `verifier-a`, `verifier-b`, `verifier-cd`, `verifier-bw`, `verifier-f`, `verifier-f2`, the release-preparation verifier, `gate-verifier-v025`, the docfix verifier, the `f3c4780` sweep agent |
| Reviewer | `reviewer-a`, `reviewer-b`, `reviewer-cd`, `reviewer-bw`, `reviewer-f`, `reviewer-f2`, `reviewer-f3`, `reviewer-v024`, `reviewer-v025` |
| Codex (site work in `8c900f6`, `931681f`) | `pages_developer`, `pages_verifier`, `pages_reviewer` |

Also ineligible: the Windows session that built and verified the Windows artefacts.

**Designated operator:** a dedicated agent created after this file exists, holding none of
those roles, addressed as `release-operator-v025`. Its instructions: run the steps
individually in order, never `all`, never `ship`, never bare `./release.sh`; record each
command, its UTC window and its exit status as it completes; and stop at the first
failure rather than continuing.

## Corrections after the gate's second pass

The gate verifier re-read this file and found three imprecisions in the evidence above
and five names missing from the ineligibility table. The table is corrected in place;
the evidence corrections are recorded here rather than silently rewritten:

1. **"The docfix verifier repeated it at the docfix state"** overstates where that run
   happened. That verifier ran the suite from the `windows` worktree, which carried
   uncommitted Windows edits — `claude_pet.py` is the same blob in both trees, so the run
   is evidence about the same code, but the first full-suite run from a clean `main` tree
   at `f9043ef` is the gate's own second pass (612, OK, 7 skips, exit 0). The differing
   skip count, 8 there and 7 here, is that environment.
2. **"the four track records"** undercounts: there are five tracks — a, b, bw, cd, f —
   and bw, cd and f are recorded on the `windows` branch, not on `main`.
3. **This file was untracked when it was written.** v0.24's precedent (`3190ce6`) is to
   commit the gate record, and this release follows it: this file and the gate record are
   committed before the operator runs.

The five names the table was missing: `reviewer-f` and `reviewer-f2`, both Track F
Reviewers, and Codex's `pages_developer` / `pages_verifier` / `pages_reviewer`, who carry
role trailers on the two site commits inside `v0.24..HEAD`. None of them could have become
the operator — the designation is defined by creation time, which excludes every agent that
already exists — so the defect was in the enumeration, not in the rule. It is fixed above
so the audit trail is complete.

One item the gate raised and did not hold the gate on, recorded so it is not lost: the
documentation-correction commit `f9043ef` carries no post-hoc Reviewer trailer. It touches
no production file, its wording was prescribed in advance and in writing by the two parties
that did not write it, and no test reads these READMEs.

Signed: Coordinator, main session `55c3dee4-727f-4a94-b960-66540b129014`, 2026-09-14.
