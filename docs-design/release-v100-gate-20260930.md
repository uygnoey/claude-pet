# ClaudePet v1.0.0 — execution-gate record (AGENTS.md §6 items 1–3)

## Verdict: **GREEN**, conditional on the Reviewer's record for G and G2

§6 items 1–3 are GREEN at **G2** `8e5a722233149245b3148cb3fe7c7baa3a7b0c5f`, with one exception.
§8 item 4 — the Reviewer's sign-off — for the two release commits **G** `59b807e` and **G2**
`8e5a722` lives in `docs-design/release-v100-review-20260930.md`.

**The verdict is GREEN only if that file exists and records an approve verdict for both
commits.** Without it, item 1 fails for G and G2 and the verdict is NOT GREEN. v0.25's gate
handled its R1 the same way. Items 4 and 5 — the Coordinator's sign-off and the named release
operator — are in `docs-design/release-v100-coordinator-20260930.md`, not here.

The subject changed while this gate was being evaluated. It was first G. The user then said
v1.0.0 is the first official release ("이거부터 정식 릴리즈야"), so G2 changed one sentence of
the notes, and the gate was re-evaluated at G2. G's own suite run is recorded in §2 too.

- **Author:** `cwdfix-verify`. It was the Verifier on this release: it wrote the tests in
  `daf1b7e`, `d82bb22`, `d0ed768`, `d4e06c3` and the test half of `59b807e`, and it verified
  `d79b858`, `5cca59d`, `59b807e` and `8e5a722`. It also checked CLAUDE.md's new section (§7).
  It edited no production file and ran nothing from `release.sh` or `build_app.sh`. In the
  main repository its only git writes were `git fetch origin dev` and `git worktree add/remove`
  for the two throwaway worktrees — no branch, index or working-file change. In the main tree
  it created this file only, as assigned.
  **It is not eligible to operate the release.**
- **Written (UTC):** 2026-09-30T04:45Z.
- **Subject:** `8e5a722` "docs: v1.0.0 노트 — 첫 정식 버전이라고 적는다" on `dev`, on top of
  `59b807e` "release: ClaudePet v1.0.0". The range is `v0.26.1..8e5a722`.
- **Outside world** (queried 2026-09-30T04:38Z):
  - `git tag -l v1.0.0` → empty; `git ls-remote --tags origin` has no `refs/tags/v1.0.0`;
  - `gh release list` → latest is `ClaudePet v0.26.1` (2026-09-21T05:00:16Z).
  - So v1.0.0 is unpublished and its notes section is staged.

---

## 1. §6 item 1 — §8 for every change in the release

Every commit in `v0.26.1..8e5a722`, oldest first. The red→green and Reviewer columns give
pointers; the underlying records are in the commit bodies and CI.

| commit | change | Developer | Verifier | red → green | Reviewer |
| --- | --- | --- | --- | --- | --- |
| `fd67b55` | Windows side of v0.26.1 (dev only) | v026-win-dev | v026-win-verify | CI `35565052629` success | v0.26.1 cycle |
| `13c6821` | AGENTS.md §0 [ASK] fast path (already on main) | claude-pet-b0 | verifier-v0261 | its body | v0.26.1 cycle |
| `9cd98a3` | merge main → dev | — (no trailers) | — | CI `35566778587` success | — |
| **A** `daf1b7e` | tests: private folder, one-shot job, Codex account header | cwdfix-verify | cwdfix-review | **red**: CI `36662979506` (both jobs fail); body: 80/27/1, 38/15, 40/1 on the unfixed `claude_pet.py` df3f13bd | R1 (the body records the Reviewer independently reproducing the red) |
| **B** `d79b858` | fix: recovery CLI + Codex header | cwdfix-dev | cwdfix-verify | **green**: body "게이팅 테스트 전부 초록, 전체 888 OK" | R1/R1-bis/R2 (`6785313` body) |
| **C** `d82bb22` | pin move → 26ebcf21 | cwdfix-verify | cwdfix-review | pure pin move (body) | its body |
| **D** `d0ed768` | tests: WMI window hidden, stale-job cleanup | cwdfix-verify | cwdfix-review | **red**: CI `36665455747` (11 failures = the new gates); body 88 ran / 11 on 26ebcf21 | R3 (three survivors added, body) |
| **E** `5cca59d` | fix: ShowWindow=0, `clear_stale_launchd_jobs` | cwdfix-dev | cwdfix-verify | **green**: body 88/38/40, 896 OK | R3/R3-bis (`6785313` body) |
| **F** `d4e06c3` | pin move → 843623b5 | cwdfix-verify | cwdfix-review | **green**: CI `36665491426` macOS + Windows success | R3-bis |
| `6785313` | merge of the fix branch into dev | coordinator (authored no content) | cwdfix-review | **green**: CI `36666667778` macOS + Windows success | the Verifier trailer (checked against both parents) |
| **G** `59b807e` | release commit | cwdfix-dev | cwdfix-verify | **red→green**: body 46 ran / 7 failures → 46 OK, 902 OK; CI `36669138534` success; §2 below | **see `release-v100-review-20260930.md`** |
| **G2** `8e5a722` | notes: "첫 정식 버전" | cwdfix-dev | cwdfix-verify | **green**: §2 below | **see `release-v100-review-20260930.md`** |

Each §8 item, for the release as a whole:

1. **Trailers present and different — PASS.**
   - Every non-merge commit carries a `Developer:` and a `Verifier:` naming different parties.
   - `6785313` carries both.
   - `9cd98a3` carries none, but introduces no content of its own: its diff against its first
     parent is identical to `13c6821`'s file list and counts
     (`diff <(git diff --stat 9cd98a3^1 9cd98a3) <(git show --stat --format= 13c6821)` → no
     output). This is the same non-blocking class v0.25's gate recorded for merges.
2. **Developer–Verifier separation — PASS.**
   - `cwdfix-dev` edited `claude_pet.py`, plus the release commit's version, notes and docs.
   - `cwdfix-verify` edited `tests/` only.
   - The test commits are verified by `cwdfix-review`.
   - The Verifier's out-of-repo reference implementation, used to run rivals, is declared in
     `daf1b7e`'s body. The Reviewer ruled it compatible with §2 Condition B.
3. **Red before green — PASS.**
   - A and D were red on CI and in their bodies, failing only on the new gates.
   - B, E and F were green (the CI numbers above).
   - The release-contract module was red at the follow-up state and green at G (46 ran /
     7 failures → 46 OK; the Verifier's record of that step is summarised in `59b807e`'s body).
4. **Reviewer sign-off — PASS for A–F and `6785313`**, with one recorded observation. For
   **G and G2 the pointer is `docs-design/release-v100-review-20260930.md`** — see the
   verdict.

   **Observation: the Verifier trailer and the Reviewer are the same agent on four commits.**
   On the test-only commits A and D and the pin moves C and F, `cwdfix-review` holds both,
   because AGENTS.md §7's "Test-only" row puts the agent who confirmed the red in the Verifier
   trailer. Read commit by commit, §8 item 4's "neither Developer nor Verifier" is not met on
   those four. Read change by change — tests, fix and pins land together through `6785313` —
   the roles are distinct:
   - Developer `cwdfix-dev` wrote the production code;
   - Verifier `cwdfix-verify` wrote the tests;
   - Reviewer `cwdfix-review` wrote neither.

   The Reviewer therefore signed off on nobody's work but others', which is what §1 forbids it
   to break. The red it confirmed was also confirmed without it, on CI (`36662979506`,
   `36665455747`) and in the tests' author's own record. I count item 4 as PASS on the
   change-level reading. If the Coordinator reads it commit by commit instead, item 4 fails for
   A, C, D and F; a sign-off on them from an agent with no role on this release would close it.
5. **Full suite green, run by the Verifier — PASS** (§2).
6. **No untracked file outside the deliverables touched — PASS.**
   - `git diff --stat v0.26.1 8e5a722` lists 13 tracked paths.
   - None is a user-owned untracked file (`diag.py`, `release/ClaudePet.iconset/`,
     `release/icon_1024.png`, the untracked `docs-design/*` records).
   - This record's author ran no destructive git command.
7. **Quantitative claims meet §5 — PASS.**
   - The commit bodies scope every observation by date, machine, CLI version and count.
   - The two CLAUDE.md claims this Verifier found not to hold at the release preparation are
     fixed in G's CLAUDE.md (§3).

## 2. §6 item 2 — the suite re-run from a clean tree — **GREEN**

**At G2** — a throwaway worktree, removed afterwards:

```
git worktree add --detach <scratchpad>/g2-wt 8e5a722233149245b3148cb3fe7c7baa3a7b0c5f
git status --porcelain --untracked-files=no      → (empty) before and after the run
python3 -m unittest discover -s tests -v -p "test_v1_0_0_release_contract.py"
    2026-09-30T04:34:00Z → 04:34:02Z   Ran 46 tests   OK   exit 0
python3 -m unittest discover -s tests -v          (from the worktree root)
    2026-09-30T04:37:02Z → 04:42:27Z   Ran 902 tests in 324.651s   OK (skipped=8)   exit 0
```

The eight skips are all opt-in or live checks; none is a gating test that failed to run:
- 3× `test_v020_boundaries.B3Updater.*` — "live installed-v0.20 to checkout-v0.21 boundary
  requires CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1";
- 1× `test_v020_boundaries.B2Bundle.test_py2app_bundle_carries_every_asset` — "no built bundle
  at <worktree>/dist/ClaudePet.app/Contents/Resources/.claude_pet";
- 2× `test_updater.RealBundleAcceptanceTests` — "the installed-app preflight is an opt-in live
  check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1";
- 2× `test_updater.StaplerLiveContractTests` — "the real stapler contract is an opt-in live
  check; set CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1".

**At G**, the first subject — the same procedure in `<scratchpad>/gate-wt` at `59b807e`:
- `git status --porcelain --untracked-files=no` was empty before and after;
- 2026-09-30T04:30:53Z → 04:36:55Z, `Ran 902 tests in 361.506s`, `OK (skipped=8)`, exit 0, the
  same eight skips.
- CI `36669138534` on `59b807e`: macOS full suite success, Windows gating contract success.

**Reviewed source pins match the bytes under test:**
- `REVIEWED_APP_SOURCE_SHA256` = `5fff289f…` = `claude_pet.py` at G2;
- `REVIEWED_VERIFIER_SHA256` = `98680efc…` = `verify_release_artifact.py`;
- `REVIEWED_RELEASE_SHA256` = `a5b25686…` (`release.sh`, unchanged);
- `REVIEWED_BUILD_APP_SHA256` = `aa8fce8d…` (`build_app.sh`, unchanged).
- The pin tests and the version/pin contract test are part of the green run.

## 3. §6 item 3 — release notes checked — **GREEN**

The staged section at G2 (`RELEASE_NOTES.md` sha256 `205da060…`):

```
**v1.0.0**

- v0.26부터 macOS에서 "토큰 자동 갱신"이 Apple Music·네트워크 볼륨·다운로드 등의 권한 창을 띄우던 문제를 고쳤습니다. 따로 할 일은 없고, 이미 허용했든 거부했든 그대로 두면 됩니다.
- Codex 사용량이 Codex에서 보는 값과 다르게 나올 수 있던 문제를 고쳤습니다. 이제 Codex가 실제로 쓰는 계정의 사용량이 보입니다.
- Windows에서는 "토큰 자동 갱신" 때 터미널 창이 떴다 사라지던 문제도 고쳤습니다. macOS와 Windows 모두 첫 정식 버전인 1.0.0으로 나오며, 앱의 업데이트 안내에서 받을 수 있습니다.
```

- **Format (CLAUDE.md step 2).** The check is the green run of
  `tests/test_v1_0_0_release_contract.py`'s `StagedV100NotesFormatTests` at G2, not a separate
  reading.
  - 3 top-level bullets, none nested; 313 normalised characters (limit 450);
  - 2 Korean sentences per bullet; no hash, path, identifier, test-count or magnitude word;
  - the only number is the version;
  - the one quoted UI string, "토큰 자동 갱신", is `TR["ko"]["menu_auto_recover"]`.
- **Claims.** The same class ties one test per bullet to the source, and all pass at G2:
  - Bullet 1: the private working directory, the one-shot `bootstrap` job and the startup
    cleanup of v0.26's labels; "v0.26부터" is the oldest published section naming the label;
    there is no `tccutil`.
  - Bullet 2: `ChatGPT-Account-Id` carrying `tokens.account_id` from Codex's own `auth.json`.
  - Bullet 3: `_win_wmi_create`'s `ShowWindow` 0 startup info on every Create, and no
    `CreateFlags`; `APP_VERSION` 1.0.0 as the version named, stamped by both platforms'
    packagers, tagged by `release.sh`, and compared by both updaters; the comparator every
    published build carries ranks it above every published version.
  - That ranking is also what makes "첫" true. "정식" is the user's own designation
    (2026-09-30), not a source fact.
- **Published sections are byte-identical.**
  - From `**v0.26.1**` to EOF: 21403 bytes, sha256 `8e29e813…`. This equals the `v0.26.1` tag's
    tree and the live GitHub release body; that check was made when the pin was written.
  - The older pins (`v0.26` `1fe0efa1…`, v0.25, v0.24, v0.23, v0.22) hold.
  - The heading order is `1.0.0`, `0.26.1`, `0.26`, …
- **CLAUDE.md's new section** ("Token auto-recovery runs the CLI detached, in a private folder,
  once per attempt"; CLAUDE.md `dad2c39a…`). The two claims found not to hold at the
  preparation are fixed:
  1. The prompts are now attributed to v0.26's own recovery jobs (tccd 05:28–06:52, 14
     `AUTHREQ_PROMPTING` from 7 PIDs), and the controlled `/` run is described as sandboxed
     and unable to prompt.
  2. The section is scoped by platform. The pill's login click is macOS only; recovery is the
     Windows port's only use of `_run_refresh_job`; the port's own console paths
     (`_login_claude` / `_install_claude`) are listed; "the login shape through
     `_run_refresh_job`" is marked macOS only.

  Both now hold against the source and the records. The new "both platforms, same environment
  variable" for `_fetch_cli_usage()` also holds: the port calls `cp.fetch_exact_usage()`.
- **Non-blocking:** the bullet-3 test's docstring still quotes the pre-G2 sentence ("macOS와
  Windows 모두 1.0.0으로 나오며"). The checks read the bullet and pass; only the quotation is
  stale.

## 4–5. Coordinator sign-off and release operator

Not in this record — see `docs-design/release-v100-coordinator-20260930.md`.

## What this record did and did not do

- **Did:** ran `unittest` in two throwaway detached worktrees (`59b807e` and `8e5a722`, both
  removed afterwards), and made read-only `git`, `gh run view`, `gh release list` and
  `git ls-remote` queries.
- **Did not:** run the Windows port suite at G2 (CI `36669138534`'s Windows job covers G's
  gating contract), build, sign, tag, push or publish anything.
- **Did not:** evaluate items 4 and 5.
- **Did not see:** the Reviewer's sign-off on G and G2. The verdict depends on it.
