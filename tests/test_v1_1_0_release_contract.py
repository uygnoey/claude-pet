"""Static release-preparation gates for v1.1.0.

Status as of 2026-10-05 (Verifier rel110-verify): v1.0.1 is published — annotated tag
``v1.0.1`` (dbbdd75d) on origin, pointing at e772ca4; GitHub release published
2026-09-30T09:45:29Z.  The tag's ``RELEASE_NOTES.md`` blob (c2f0b2d6) is the same blob
the v1.0.1 release commit a23d384 carried, so — as for v0.26.1 and unlike v1.0.0 — the
release commit and the tag agree.  Running ``release.sh``'s ``gen_release_notes`` awk
program (ver=``**v1.0.1**``) over the tag's file reproduces the live release body
(``gh release view v1.0.1 --json body``, checked 2026-10-05) byte for byte, 3210 bytes
(gh's output adds one trailing newline) — see the provenance note above
``PUBLISHED_V101_AND_OLDER_SHA256``.  So everything from the ``**v1.0.1**`` heading to the
end of ``RELEASE_NOTES.md`` is frozen text and is pinned here byte for byte, alongside the
older v1.0.0, v0.26.1, v0.26, v0.25, v0.24, v0.23 and v0.22 pins.  The single unpublished
section above it is ``**v1.1.0**``, and ``APP_VERSION`` is ``"1.1.0"`` — the bump the
release commit 4c088dc carries.  ``PublishedV023NotesContractTests`` through
``PublishedV100NotesContractTests`` and ``PublishedV101NotesContractTests`` keep holding
the frozen prose to the source it describes (a published promise outlives its release;
the v1.0.1 class is the former ``StagedV101NotesFormatTests`` with its method names
unchanged and one assertion re-scoped — see its docstring), and
``StagedV110NotesFormatTests`` holds the v1.1.0 section to CLAUDE.md's release-note
format rule and ties every checkable claim in it to the source.

Every v1.0.1 claim was judged individually against the v1.1.0 tree.  The v1.1.0 change
(server-only usage, per-provider settings, log spikes for Claude and Codex) touches the
pill, the settings panel and spike detection; the v1.0.1 claims are about the release
tooling (arm64 build interpreter, ``MIN_MACOS``, the minos gate, the updater's asset
preference) and the version comparator, none of which that change touched — every one of
them still holds and none was dropped.  The single re-scope is the version a published
bullet names ("같은 1.0.1로"), which is now tied to the section's own heading rather than
to ``APP_VERSION``, exactly as v1.0.0's was when it was published.  (The assertions the
server-only change *did* make obsolete — the published v0.24 notes' ``≈``/``⚠`` ties —
were already removed by bf25e95, with its reason, before this release.)

The v1.1.0 ties, one test per bullet.  "필에는 이제 서버가 알려 준 사용량만 표시합니다.
로그로 계산한 추정치(≈)와 한도 보정 설정은 없어졌고, 한도를 보정해 둔 분도 따로 할 일은
없습니다" against ``roam_summary`` never reading the log snapshot (``stats``) and having no
``estimate`` segment, against ``SUMMARY_APPROX`` and every ``≈`` being gone from the
source, against the three limit keys and the calibration/advanced-limits UI being gone
from ``RUNTIME``, ``TR`` and the module, and against ``apply_config`` reading only
``_RUNTIME_CONFIG_KEYS``, which names none of the old keys (so an old config file needs no
action).  "설정 창이 Claude Code와 Codex 구역으로 나뉘어, 제공자마다 필 표시 여부, 볼
게이지, 구독과 API 비용 중 무엇을 볼지 고릅니다(Codex 비용은 OpenAI Admin 키)" against
``open_settings`` building two ``section``s titled ``TR["ko"]["s_sec_claude"]`` /
``["s_sec_codex"]``, each with a show checkbox (``show_claude`` / ``show_codex``), a gauge
list (``s_gauges``) and a sub/API popup, against the ``RUNTIME`` defaults for those keys,
and against ``fetch_codex_cost`` reading ``openai_admin_key`` and querying OpenAI's
organization costs endpoint.  "Codex를 켰는데 설치나 로그인이 안 되어 있으면 우클릭 메뉴에
Codex 설치·로그인 항목이 나옵니다" against ``compute_codex_onboard_state`` and the menu
wiring — and **that sentence is held to who actually sees the item**: the state is
``None`` in Codex API mode and, without a token, ``None`` unless the Codex CLI or the Codex
home (``codex_home_exists``) is present, so a Codex user who has never installed it sees
nothing.  "급증 알림이 Codex 사용에도 울리고, 기준을 서버 값에서 익히기 때문에 실행 직후에는
기준을 익힐 때까지 알림이 없습니다" against ``codex_spikes`` feeding the refresh worker's
spikes and ``provider_spiking`` reading the Codex lanes, against ``is_spike`` refusing to
judge without a limit, ``LEARNED_LIMITS`` starting empty and living outside ``RUNTIME``
(never saved, so every launch starts unlearned), and ``learn_server_limits`` learning only
from server rows.  "Windows도 같은 1.1.0으로 같은 기능을 받습니다" against ``APP_VERSION``,
``windows/build_win.py`` reading it, and the port calling the same core functions for each
of the three bullets (the settings sections, ``cp.compute_codex_onboard_state`` and the
Codex menu items, ``cp.codex_spikes`` / ``cp.learn_server_limits`` / ``cp.provider_spiking``).
The behavioural gates are tests/test_server_only_usage.py, tests/test_codex_usage.py and
windows/tests/test_win_server_only_usage.py; this module only ties the prose to them.

The v1.0.1 section (published) was tied as follows when it was staged, and still is.
The v1.0.1 ties, one test per bullet: "Apple Silicon용 다운로드와 그 자동 업데이트가
macOS 26.3 이상에서만 열리던 문제를 고쳤습니다. 이제 안내대로 macOS 12 이상에서 열립니다"
against the updater's arm64 asset preference (``UPDATE_ASSET_NAMES["arm64"]`` names the
arm64 zip ``release.sh`` builds first), against the floor both halves of the release
tooling hold (``MIN_MACOS`` in ``release.sh`` and ``verify_release_artifact.py``, equal to
the macOS the READMEs promise), against ``release.sh``'s arm64 build interpreter
defaulting to the universal2 one and being checked by ``check_build_python`` before
py2app, and against ``check_app`` running ``check_minos`` before it delegates; "26.3"
against the deployment target ``release.sh`` records for the pyenv interpreter it no
longer uses.  "26.3보다 낮은 macOS에서 … 다시 내려받아 설치하세요. 앱이 잘 열리던 분은 앱의
업데이트 안내로 받으면 되고, 따로 할 일은 없습니다" against the same 26.3 and against the
comparator every published build carries ranking ``APP_VERSION`` above every published
version.  "Windows도 같은 1.0.1로 나오지만 기능은 달라진 것이 없습니다" against
``APP_VERSION`` and ``windows/build_win.py`` taking its version from it.  Two facts behind
these bullets are not static properties of this tree and were checked by hand on
2026-09-30 (minos-verify): the published v1.0.0 ``ClaudePet.zip`` (``gh release
download``) fails ``verify_release_artifact.py minos`` with 56 Mach-O slices at minos
26.3 (``Contents/MacOS/python`` among them) while ``ClaudePet-universal.zip`` passes (74
Mach-O files, all <= 12.0); and ``git diff v1.0.0 <release commit> -- windows/`` is empty
while ``claude_pet.py`` differs from the tag only in ``APP_VERSION`` — which is what
"기능은 달라진 것이 없습니다" rests on.  The behavioural gates are tests/test_minos_gate.py
(``CheckMinosTests``, ``CheckAppInvokesMinosTests``, ``CheckBuildPythonTests``).

Lineage: ``test_v022_release_contract.py`` → ``test_v023_release_contract.py`` →
``test_v024_release_contract.py`` → ``test_v025_release_contract.py`` →
``test_v026_release_contract.py`` → ``test_v026_1_release_contract.py`` →
``test_v1_0_0_release_contract.py`` → ``test_v1_0_1_release_contract.py`` →
this file; each
release renames the module with ``git mv`` and rewrites it for the version its release
commit carries.  The name spells all three parts of the version: squeezed the way
``v026`` squeezed 0.26, 1.0.0 would read ``v100``, which looks like version 100.  A
pattern written for the older names (``tests/test_v0*_release_contract.py``) does not
match this file; ``tests/test_v*_release_contract.py`` matches every name in the lineage.

These tests deliberately do not import the application, source a shell script, inspect
the installed app, or access the network/user home.  They only parse repository text and
bytes (the tracked sources — the Windows port's ``windows/`` sources included, since the
v1.0.0 notes speak for it — plus the two files under ``fonts/`` the v0.24 notes promise
are bundled).  One bounded exception: the v1.0.0 update tie calls the version comparator
every published build carries, which this file holds as text (``PUBLISHED_VER_TUPLE``, a
six-line pure function that uses nothing but builtins) — it is not taken from the
application.  The source-pin assertions keep the executable manual-update and upload
harnesses fail-closed when the final v1.0.0 application/verifier/script bytes change, and
the ``--expect-version`` usage example in ``verify_release_artifact.py`` is held to the
bumped version because every release commit since v0.21 moved it with ``APP_VERSION``
(``git log -S'--expect-version 0.22'``; a1f3d22 moved it to 0.24, aaf0ca6 to 0.25) and
``release.sh`` passes ``$(cur_version)``, so that example is the only place a stale
version literal can survive a release.

Claims in the notes are cross-checked against the source rather than merely spelled out
here, because a note and a constant can drift apart in either direction.  The v1.0.0
ties, one test per bullet: "v0.26부터 macOS에서 "토큰 자동 갱신"이 … 권한 창을 띄우던
문제를 고쳤습니다" against the recovery spawn's private working directory
(``recovery_cli_cwd()``, beneath the app's own cache, is the only value that can reach the
launchd job's ``WorkingDirectory``), against the one-shot ``bootstrap`` job that is never
kept alive and never ``submit``-ted, and against ``clear_stale_launchd_jobs`` booting out
the labels v0.26 submitted its jobs under, started from ``run_gui`` at launch behind no
setting; "v0.26부터" against the notes' own history (v0.26 is the oldest section that
names the label); "따로 할 일은 없고, 이미 허용했든 거부했든 그대로 두면 됩니다" against the
cleanup running behind no setting, the job's folder admitting no alternative value, and no
``tccutil`` anywhere in the source.  "이제 Codex가
실제로 쓰는 계정의 사용량이 보입니다" against ``fetch_codex_usage`` putting what
``read_codex_auth`` reads from ``tokens.account_id`` of Codex's own ``auth.json`` into a
``ChatGPT-Account-Id`` header.  "Windows에서는 "토큰 자동 갱신" 때 터미널 창이 떴다
사라지던 문제도 고쳤습니다" against the port's auto-recovery running the core's
``run_token_refresh``, whose Windows spawn is ``_win_wmi_create``, which always hands WMI
a ``Win32_ProcessStartup`` with ``ShowWindow`` 0 and never ``CreateFlags``; "macOS와
Windows 모두 1.0.0으로 나오며, 앱의 업데이트 안내에서 받을 수 있습니다" against
``APP_VERSION`` being the version named, the one both platforms' packagers stamp, the one
``release.sh`` tags, and the one both updaters (``check_github_update`` and the port's
``check_github_update_win``) compare the latest tag against — ranked newer than every
published version by the comparator every published build carries.  The behavioural gates
for these are tests/test_token_recovery.py (``RecoveryCliCwdTests``,
``DarwinOneShotJobTests``, ``StaleJobCleanupTests``, ``WindowsHiddenConsoleTests``) and
tests/test_codex_usage.py (``CodexAuthReadTests``, ``CodexAccountHeaderTests``).  The
v0.26.1 pair (kept, now published): the quoted status "Claude Code 미설치" against
``TR["ko"]["onb_install"]`` and against ``roam_summary_text``'s own
``claude_onboarding_suppressed`` local, which gates the suppression on exactly
``onb_install``/``onb_login`` and on a Codex segment that actually carries data (not
itself a ``"status"`` segment) — the behavioural proof, both the positive case and its two
non-overreach cases (a non-Codex user; every other Claude status untouched), lives in
tests/test_companion_motion.py's ``CodexOnboardingSuppressionTests``; this module only
ties the prose to it.  The v0.26 pairs (kept, published): the quoted menu label
"토큰 자동 갱신" against ``TR["ko"]["menu_auto_recover"]`` and "펫이 만료 직전에 알아서
되살립니다" against ``recovery_tick``'s pre-emptive branch (``REFRESH_MARGIN_SEC`` before
``expires_at``, gated on ``RUNTIME["auto_recover"]``) and against ``claude -p /usage``
being handed to launchd as a one-shot ``bootstrap`` job whose WorkingDirectory is the
private ``recovery_cli_cwd()`` and which is never kept alive, so the CLI is never our
descendant and runs once, away from ``/`` (re-tied 2026-09-30: this used to be
``launchctl submit``, which is what raised the folder prompts — see that test's
docstring); "로고와 함께" and "줄도 로고도 생기지 않습니다" (the v0.26 tag's wording, not
its release commit's — see the provenance note above ``PUBLISHED_V026_AND_OLDER_SHA256``)
against the single ``chatgpt.com/backend-api/wham/usage`` endpoint and against
``fetch_codex_usage`` / ``roam_summary_codex`` returning ``None`` — no row at all — when
there are no Codex credentials; the quoted "크레딧 금액으로" against
``TR["ko"]["menu_credit_money"]``, "쓴 금액이 $로" against ``CREDIT_DISPLAY_DEFAULT``
being ``"money"`` and ``credit_row_text`` formatting an amount, "켜 두었다면" against
``_parse_oauth_usage`` gating the credit row on ``user_disabled`` rather than
``is_enabled``, and "조회 중에 머물지 않고 이유를" against ``roam_summary``'s API branch
splitting a rejected key from a transient failure through ``api_error_kind``.  The v0.25
pairs keep theirs (the sign-in label, the OS-read checkmark, the token cache, the
uninstall label and the surviving pet folder), the v0.24 pairs theirs (thresholds, marker
glyphs, font, nested layout, toggle wording, colour roles), and the v0.23 pairs theirs
("1시간" against ``UPDATE_CHECK_SEC``, the quoted menu label, no check at launch, straight
to the latest release).  Pinning only one side of any of these pairs would let the other
side move silently.  The behavioural gates live elsewhere — tests/test_oauth_token_cache.py
for the token cache, tests/test_token_recovery.py for the recovery cycle,
tests/test_codex_usage.py for the Codex rows, tests/test_credit_row.py and
tests/test_api_cost_status.py for the credit row and the API status line,
tests/test_autostart.py for the sign-in item, and tests/test_companion_motion.py's
``CodexOnboardingSuppressionTests`` for the v0.26.1 onboarding suppression; this module
only ties the prose to them.

The Windows claims in the v0.25 notes (the same menu item there, in-app update for the
installer and the portable zip, "작업 관리자") are built on the Windows branch, not by
this tree, so no gate in this checkout can say whether they hold — only the macOS half of
each sentence is checked here.  The v0.26 notes make no Windows claim.  The v0.26.1
notes' third bullet claims both platforms ("macOS·Windows 모두 적용되며, 따로 설정할
것은 없습니다") — the Windows half is, again, built on the Windows branch and out of
scope for this checkout/session; this module pins the wording and checks only the macOS
half, that the fix needs no new config/``RUNTIME`` key, consistent with "따로 설정할
것은 없습니다".  The v1.0.0 notes are tied differently: the port is in this tree under
``windows/`` (it has been since before the v0.26 tag) and imports ``claude_pet.py`` as its
core (``windows/win_core.py``), so both halves of their third bullet are tied here — the
hidden console to the core spawn the port's auto-recovery runs, the 1.0.0 update to
``windows/win_update.py``, its call site in ``windows/claude_pet_win.py`` and
``windows/build_win.py``'s version.  What no static tie can say is whether a Windows
machine actually shows a window: that was observed on one Windows 11 machine (see
``_win_wmi_create``) and is gated behaviourally by ``WindowsHiddenConsoleTests``, which the
CI also runs on Windows.
"""

from __future__ import annotations

import ast
import hashlib
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO / "claude_pet.py"
RELEASE_VERIFIER = REPO / "verify_release_artifact.py"
BUILD_SCRIPT = REPO / "build_app.sh"
RELEASE_SCRIPT = REPO / "release.sh"
SETUP = REPO / "setup.py"
FONT_DIR = REPO / "fonts"
RELEASE_NOTES = REPO / "RELEASE_NOTES.md"
CLAUDE_POLICY = REPO / "CLAUDE.md"
MANUAL_TEST = REPO / "tests" / "test_manual_update_transaction.py"
UPLOAD_TEST = REPO / "tests" / "test_upload_artifact_gate.py"
WIN_APP = REPO / "windows" / "claude_pet_win.py"
WIN_UPDATE = REPO / "windows" / "win_update.py"
WIN_BUILD = REPO / "windows" / "build_win.py"

# Pinning from the newest *published* heading through EOF lets the unpublished section
# be rewritten freely while making every byte users already received immutable.
# v0.22-and-older: computed from the v0.22 release commit's blob (6d47df5e,
# `git show HEAD:RELEASE_NOTES.md` at the time) and unchanged since (2026-09-11).
PUBLISHED_V022_AND_OLDER_SHA256 = (
    "6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239"
)
# v0.23-and-older: from the ``**v0.23**`` heading through EOF, computed from the v0.23
# release commit's blob (`git show 81619b3:RELEASE_NOTES.md`, 22896 bytes, of which the
# suffix is 18516) and confirmed identical in the working tree after the v0.24 section
# was staged above it (2026-09-12T12:41Z; re-checked 2026-09-12T14:22Z).
PUBLISHED_V023_AND_OLDER_SHA256 = (
    "c7ddc40a8a25ce8eefac9867032a6a14f20425c6ae0368db41a86d859c96b562"
)
# v0.24-and-older: from the ``**v0.24**`` heading through EOF, computed from the v0.24
# release commit's blob (`git show a1f3d22:RELEASE_NOTES.md`, 23826 bytes, of which the
# suffix is 19446), identical in HEAD 36c2118 and confirmed identical in the working tree
# after the v0.25 section was staged above it (2026-09-13).
PUBLISHED_V024_AND_OLDER_SHA256 = (
    "c38940804b5b94ef72bf49727ac41a82d672dc779d45e53a3436a2460a1cddb4"
)
# v0.25-and-older: from the ``**v0.25**`` heading through EOF, computed from the v0.25
# release commit's blob (`git show aaf0ca6:RELEASE_NOTES.md`, 24476 bytes, of which the
# suffix is 20096), identical in the v0.25 tag's own tree (`git show v0.25:RELEASE_NOTES.md`,
# tag -> 8614a65) and confirmed identical in the working tree after the v0.26 section was
# staged above it (2026-09-20).  The v0.24 suffix is unchanged at 19446 bytes across the
# same three trees, so the v0.25 section was appended above it and nothing below moved.
PUBLISHED_V025_AND_OLDER_SHA256 = (
    "a862d2cf6fe512c7937eed3305781577cc243ef78ce857db6dee424012ae5920"
)
# v0.26-and-older: from the ``**v0.26**`` heading through EOF.  The v0.26 *release
# commit* (d3828ab) staged a different wording for the second bullet than what actually
# shipped: two follow-up commits landed on main before the tag was pushed, and one of
# them reworded that bullet.  What is pinned here is therefore the *tag*'s tree
# (`git show v0.26:RELEASE_NOTES.md`, tag -> commit 2541669, 25399 bytes, of which the
# suffix is 21019), independently confirmed byte-for-byte against the live GitHub
# release body (`gh release view v0.26 --json body`, checked 2026-09-21) — that is the
# only record of what users actually received.  Identical in the working tree after the
# v0.26.1 section was staged above it (2026-09-21).  The v0.25 suffix is unchanged at
# 20096 bytes across all of these trees, so the v0.26 section was appended above it and
# nothing below moved.
PUBLISHED_V026_AND_OLDER_SHA256 = (
    "1fe0efa1423c5a6e626cf1be27d2f50384e45ee94f49ab1f48ae0a112b58c403"
)
# v0.26.1-and-older: from the ``**v0.26.1**`` heading through EOF, computed from the
# *tag*'s tree (`git show v0.26.1:RELEASE_NOTES.md`; the tag is lightweight and points at
# b52926f, the v0.26.1 release commit itself — blob 57996617, 25783 bytes, of which the
# suffix is 21403).  Independently confirmed byte-for-byte against the live GitHub release
# body (`gh release view v0.26.1 --json body`, checked 2026-09-30; release published
# 2026-09-21T05:00:16Z): the body is release.sh's gen_release_notes output — the notes'
# preamble, the changelog heading and the v0.26.1 section alone — and running that awk
# program (ver=**v0.26.1**) over the tag's file reproduces all 3095 bytes of the body, so
# the 384-byte v0.26.1 section users received is the one pinned here.  Identical in the
# working tree after the v1.0.0 section was staged above it (2026-09-30).  The v0.26 suffix
# is unchanged at 21019 bytes across all of these trees, so the v0.26.1 section was
# appended above it and nothing below moved.
PUBLISHED_V0261_AND_OLDER_SHA256 = (
    "8e29e813f25b44d4d32002e17ec5562a322c28fd4e91e00227780e11143c2d16"
)
# v1.0.0-and-older: from the ``**v1.0.0**`` heading through EOF, computed from the *tag*'s
# tree (`git show v1.0.0:RELEASE_NOTES.md`; annotated tag e340b154 -> 837c867, blob
# 86d1e9ad, 26448 bytes, of which the suffix is 22068).  The release commit 59b807e carried
# a different blob (a165d9da): 8e5a722 reworded the v1.0.0 section before the tag was
# pushed, so — as for v0.26 — the tag, not the release commit, is what users received.
# Independently confirmed against the live GitHub release body
# (`gh release view v1.0.0 --json body`, checked 2026-09-30; published
# 2026-09-30T05:03:07Z): running release.sh's gen_release_notes awk program
# (ver=**v1.0.0**) over the tag's file reproduces the body's 3376 bytes exactly (gh's
# --jq output adds one trailing newline), so the 665-byte v1.0.0 section users received is
# the one pinned here.  Identical in the working tree after the v1.0.1 section was staged
# above it (2026-09-30).  The v0.26.1 suffix is unchanged at 21403 bytes across these
# trees, so the v1.0.0 section was appended above it and nothing below moved.
PUBLISHED_V100_AND_OLDER_SHA256 = (
    "aed895d1ff5b94ba95aabac313a9aa1e5abc1a6b0131978be7202a38a06ad451"
)
# v1.0.1-and-older: from the ``**v1.0.1**`` heading through EOF, computed from the *tag*'s
# tree (`git show v1.0.1:RELEASE_NOTES.md`; annotated tag dbbdd75d -> e772ca4, blob
# c2f0b2d6, 26947 bytes, of which the suffix is 22567).  That blob is also the v1.0.1
# release commit a23d384's — nothing reworded the section between the release commit and
# the tag.  Independently confirmed against the live GitHub release body
# (`gh release view v1.0.1 --json body`, checked 2026-10-05; published
# 2026-09-30T09:45:29Z): running release.sh's gen_release_notes awk program
# (ver=**v1.0.1**) over the tag's file reproduces the body's 3210 bytes exactly (gh's
# --jq output adds one trailing newline), so the 499-byte v1.0.1 section users received is
# the one pinned here.  Identical in the working tree after the v1.1.0 section was staged
# above it (4c088dc, 2026-10-05).  The v1.0.0 suffix is unchanged at 22068 bytes across
# these trees, so the v1.0.1 section was appended above it and nothing below moved.
PUBLISHED_V101_AND_OLDER_SHA256 = (
    "4d7f342b6532477c09005374f7378df7646f236c3f96015ad405a80913446d79"
)

# The cadence the published v0.23 notes promise, and the Korean label they name.
EXPECTED_UPDATE_CHECK_SEC = 3600
KO_CHECK_LABEL = "⬆︎ 업데이트 확인…"

# What each locale's context-menu toggle must call the thing it toggles (v0.24 renamed
# the gauges to the summary pill), and the Korean wording the v0.24 notes reuse.
PILL_WORDS = {"en": "pill", "ko": "필", "ja": "ピル", "es": "píldora"}
KO_TOGGLE_WORDING = "접기/펴기"

# The two Korean menu labels the v0.25 notes quote, exactly as the source spells them.
KO_AUTOSTART_LABEL = "로그인 시 자동 실행"
KO_UNINSTALL_LABEL = "완전 삭제…"

# The two Korean menu labels the v0.26 notes quote, exactly as the source spells them.
KO_AUTO_RECOVER_LABEL = "토큰 자동 갱신"
KO_CREDIT_MONEY_LABEL = "크레딧 금액으로"

# The one Codex endpoint the v0.26 notes' "Codex 사용량" row is allowed to come from.
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"

# The onboarding status the v0.26.1 notes quote, exactly as TR["ko"]["onb_install"]
# spells it — an independent anchor, so a rename that moves both the source string and
# the note's quote together in the same wrong direction still gets caught.
KO_ONB_INSTALL_LABEL = "Claude Code 미설치"

# The launchd labels v0.26 and v0.26.1 submitted their jobs under (RECOVERY_JOB_LABEL and
# LOGIN_JOB_LABEL in `git show v0.26:claude_pet.py` and `git show v0.26.1:claude_pet.py`,
# checked 2026-09-30).  The v1.0.0 notes' first bullet rests partly on the startup cleanup
# clearing a job v0.26 left behind, and launchd knows that job only by these names.
V026_JOB_LABELS = ("me.yeongyu.claudepet.token-refresh", "me.yeongyu.claudepet.login")

# The header the v1.0.0 notes' "Codex가 실제로 쓰는 계정" rests on: the one Codex CLI itself
# sends, carrying auth.json's tokens.account_id (the comment block above codex_auth_path
# records the 2026-09-30 comparison that found it missing).
CODEX_ACCOUNT_HEADER = "ChatGPT-Account-Id"

# The version comparator every published build carries.  `ast.unparse` of ``_ver_tuple``
# is exactly this text (sha256 e9e2eab254b805f736520d7cdb382659b9896d5e4fcf79bb594046b6a1a80f7d)
# in claude_pet.py at every tag from v0.1-beta through v0.26.1 — 27 tags, checked
# 2026-09-30 — and each of those tags' ``check_github_update`` compares
# ``_ver_tuple(tag) <= _ver_tuple(APP_VERSION)``; the Windows port's
# ``check_github_update_win`` (in the v0.26 and v0.26.1 tags) makes the same comparison
# through ``cp._ver_tuple``.  Whether an installed copy offers v1.0.0 is decided by the
# comparator *it* carries, not by this tree's, so the update tie evaluates this text.
PUBLISHED_VER_TUPLE = (
    "def _ver_tuple(v):\n"
    "    out = []\n"
    "    for part in str(v).split('.'):\n"
    "        num = ''.join((ch for ch in part if ch.isdigit()))\n"
    "        out.append(int(num) if num else 0)\n"
    "    return tuple(out)"
)


# CLAUDE.md release-note step 2 forbids these in a user-facing entry.
FORBIDDEN_NOTE_PATTERNS = {
    "hash": r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{7,64}(?![0-9A-Fa-f])",
    "source path": r"(?:^|\s)[^\s`]*(?:\.py|\.sh|tests?/)[^\s`]*",
    "line reference": r"(?:\bline\s*\d+|\d+\s*행)",
    "internal identifier": r"(?:\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b|\b(?:APP_VERSION|RUNTIME|NSPanel)\b|\b[A-Za-z_]\w*\()",
    "test matrix/count prose": r"(?:테스트|매트릭스|fixture|unittest|\b(?:GREEN|RED|PASS|FAIL)\b|\d+\s*(?:tests?|테스트))",
    "unsupported magnitude/frequency": r"(?:대폭|훨씬|엄청|매우|대부분|대다수|많이|자주|종종|드물게|가끔|항상|완전히|상당히)",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal_assignments(path: Path, name: str) -> list[object]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: list[object] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        try:
            values.append(ast.literal_eval(node.value))
        except (TypeError, ValueError) as exc:
            raise AssertionError(f"{path.name}:{name} must remain a literal") from exc
    return values


def _one_literal_string(path: Path, name: str) -> str:
    values = _literal_assignments(path, name)
    if len(values) != 1 or not isinstance(values[0], str):
        raise AssertionError(
            f"{path.name} must define exactly one literal string {name}; got {values!r}"
        )
    return values[0]


def _one_literal_int(path: Path, name: str) -> int:
    values = _literal_assignments(path, name)
    if len(values) != 1 or type(values[0]) is not int:
        raise AssertionError(
            f"{path.name} must define exactly one literal int {name}; got {values!r}"
        )
    return values[0]


def _tr_table() -> dict:
    tables = _literal_assignments(APP_SOURCE, "TR")
    if len(tables) != 1 or not isinstance(tables[0], dict):
        raise AssertionError("claude_pet.py must define exactly one literal TR")
    return tables[0]


def _sentences(text: str) -> list[str]:
    """Split ordinary Korean release-note prose without splitting decimal values."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])(?:[\"'”’)]*)\s+", text.strip())
        if part.strip()
    ]


def _has_all(text: str, patterns: tuple[str, ...]) -> bool:
    return all(re.search(pattern, text, re.I) for pattern in patterns)


def _notes_block(text: str, heading: str, next_heading: str) -> str:
    """The visible body of one changelog section, comments stripped."""
    if text.count(heading) != 1:
        raise AssertionError(f"expected exactly one {heading} heading")
    if text.index(heading) >= text.index(next_heading):
        raise AssertionError(f"{heading} must sit above {next_heading}")
    block = text.split(heading, 1)[1].split(next_heading, 1)[0]
    return re.sub(r"<!--.*?-->", "", block, flags=re.S).strip()


def _bullet_shape(visible: str) -> tuple[list[str], list[str], list[str]]:
    """(top-level bullet lines, nested bullet lines, joined bullet texts)."""
    lines = visible.splitlines()
    top_level = [line for line in lines if re.match(r"^-\s+\S", line)]
    nested = [line for line in lines if re.match(r"^\s+-\s+\S", line)]
    bullets: list[str] = []
    current: list[str] | None = None
    preamble: list[str] = []
    for line in lines:
        if line.startswith("- "):
            if current is not None:
                bullets.append(" ".join(current))
            current = [line[2:].strip()]
        elif line.strip():
            if current is None:
                preamble.append(line.strip())
            else:
                current.append(line.strip())
    if current is not None:
        bullets.append(" ".join(current))
    if preamble:
        raise AssertionError(f"release body must consist only of bullets; got {preamble!r}")
    return top_level, nested, bullets


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_def(path: Path, name: str) -> ast.AST:
    """The single module-level definition called name."""
    found = [
        n for n in _module_tree(path).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.name == name
    ]
    if len(found) != 1:
        raise AssertionError(f"{path.name} must define exactly one module-level {name}")
    return found[0]


def _module_assignment(path: Path, name: str) -> ast.Assign:
    """The single module-level ``name = …`` statement, unevaluated."""
    found = [
        n for n in _module_tree(path).body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
    ]
    if len(found) != 1:
        raise AssertionError(f"{path.name} must assign module-level {name} exactly once")
    return found[0]


def _nested_function(outer: ast.AST, name: str) -> ast.FunctionDef:
    """The single function called name defined anywhere inside outer."""
    found = [n for n in ast.walk(outer) if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise AssertionError(f"expected exactly one nested function {name}, found {len(found)}")
    return found[0]


def _strings(nodes) -> set[str]:
    out: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.add(child.value)
    return out


def _names(node: ast.AST) -> set[str]:
    """Every bare name read or written anywhere inside node."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _calls_to(node: ast.AST, name: str) -> list[ast.Call]:
    """Calls of the bare name ``name(...)`` anywhere inside node."""
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name]


def _method_calls(node: ast.AST, attr: str) -> list[ast.Call]:
    """Calls of ``<anything>.attr(...)`` anywhere inside node."""
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == attr]


# ── Helpers for the v1.0.0 ties ──────────────────────────────────────────────────────────
# PublishedV026NotesContractTests keeps its own nested copies of the first few of these (it
# was re-tied inside this release and is left as it was reviewed); the ones below serve
# StagedV100NotesFormatTests.


def _changelog_sections(text: str) -> list[tuple[str, str]]:
    """(version, visible body) for every release heading under the changelog, newest
    first, comments stripped."""
    changelog = "### 📝 변경 내역 / Changelog"
    if text.count(changelog) != 1:
        raise AssertionError("expected exactly one changelog heading")
    parts = re.split(r"(?m)^\*\*v(\d+\.\d+(?:\.\d+)?)\*\*$", text.split(changelog, 1)[1])
    return [(parts[i], re.sub(r"<!--.*?-->", "", parts[i + 1], flags=re.S).strip())
            for i in range(1, len(parts), 2)]


def _module_defs(path: Path) -> dict:
    """Every module-level function in path, by name."""
    return {n.name: n for n in _module_tree(path).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _module_literals(path: Path) -> dict[str, set[str]]:
    """NAME -> every string literal a module-level ``NAME = …`` can hold, following the
    module-level names its value mentions (``LABELS = (A_LABEL, B_LABEL)`` holds both)."""
    direct: dict[str, set[str]] = {}
    refs: dict[str, set[str]] = {}
    for node in _module_tree(path).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                direct.setdefault(target.id, set()).update(
                    c.value for c in ast.walk(node.value)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str))
                refs.setdefault(target.id, set()).update(
                    c.id for c in ast.walk(node.value) if isinstance(c, ast.Name))
    out: dict[str, set[str]] = {}
    for name in direct:
        seen, todo = set(), [name]
        while todo:
            current = todo.pop()
            if current in seen or current not in direct:
                continue
            seen.add(current)
            todo.extend(refs[current])
        out[name] = set().union(*(direct[n] for n in seen))
    return out


def _reachable(defs: dict, *roots: str) -> list:
    """Every module-level function reachable from roots through any bare name, at any
    depth.  Over-approximate on purpose: a local that shares a function's name is followed
    too, which can only add code to what an absence check has to clear."""
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen or name not in defs:
            continue
        seen.add(name)
        todo.extend(n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name))
    return [defs[name] for name in sorted(seen)]


def _docstring_ids(nodes) -> set[int]:
    ids: set[int] = set()
    for node in nodes:
        for n in ast.walk(node):
            if (isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and n.body and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant)
                    and isinstance(n.body[0].value.value, str)):
                ids.add(id(n.body[0].value))
    return ids


def _code_strings(nodes, literals: dict | None = None) -> set[str]:
    """String literals the code uses — docstrings excluded, since those may tell the
    history (``submit``, ``CreateFlags``) — plus, given ``literals``, the literals of the
    module constants the code names."""
    skip, out = _docstring_ids(nodes), set()
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip:
                out.add(n.value)
            elif literals is not None and isinstance(n, ast.Name) and n.id in literals:
                out |= literals[n.id]
    return out


def _values_given(fn, key: str, *, fold_case: bool = False) -> list:
    """Every value fn gives ``key``: in a dict display, a subscript assignment, a keyword
    argument, or ``.setdefault(key, v)`` / ``.add_header(key, v)``.  Any other mention of
    the key is a value this cannot read — recorded as None, which fails closed."""
    def same(value):
        if fold_case:
            return isinstance(value, str) and value.lower() == key.lower()
        return isinstance(value, str) and value == key

    found, placed, skip = [], set(), _docstring_ids([fn])
    for n in ast.walk(fn):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and same(k.value):
                    found.append(v)
                    placed.add(id(k))
        elif isinstance(n, ast.Assign):
            for target in n.targets:
                if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and same(target.slice.value)):
                    found.append(n.value)
                    placed.add(id(target.slice))
        elif isinstance(n, ast.Call):
            found.extend(kw.value for kw in n.keywords if kw.arg and same(kw.arg))
            if (isinstance(n.func, ast.Attribute) and n.func.attr in ("setdefault", "add_header")
                    and len(n.args) == 2 and isinstance(n.args[0], ast.Constant)
                    and same(n.args[0].value)):
                found.append(n.args[1])
                placed.add(id(n.args[0]))
    for n in ast.walk(fn):
        if (isinstance(n, ast.Constant) and same(n.value)
                and id(n) not in placed and id(n) not in skip):
            found.append(None)
    return found


def _only_carries(defs: dict, fn, expr, source: str, index: int | None = None,
                  _seen: set | None = None) -> bool:
    """Whether ``expr``, inside the module-level function ``fn``, can only hold what a call
    to the module-level function ``source`` returned (element ``index`` of it, when given).

    Accepted: the call itself (``source(...)[index]`` for an element); a local every
    binding of which only carries it — a plain or annotated assignment, a walrus, or, for
    an element, its position in a tuple unpacking; a parameter that every call site in the
    module fills, positionally or by keyword, with something that only carries it.
    Anything else — a literal, another call, a global, a parameter nobody passes, any
    other kind of binding — is False, so a tie built on this fails closed."""
    seen = set() if _seen is None else _seen
    if isinstance(expr, ast.Call):
        return index is None and isinstance(expr.func, ast.Name) and expr.func.id == source
    if isinstance(expr, ast.Subscript):
        return (index is not None and isinstance(expr.slice, ast.Constant)
                and expr.slice.value == index
                and _only_carries(defs, fn, expr.value, source, None, seen))
    if not isinstance(expr, ast.Name):
        return False
    if (fn.name, expr.id, index) in seen:
        return True              # a cycle adds no new value; the other bindings decide
    seen.add((fn.name, expr.id, index))
    parents = {id(child): parent for parent in ast.walk(fn)
               for child in ast.iter_child_nodes(parent)}
    positional = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    is_param = expr.id in positional or expr.id in [a.arg for a in fn.args.kwonlyargs]
    bindings = [n for n in ast.walk(fn)
                if isinstance(n, ast.Name) and n.id == expr.id and isinstance(n.ctx, ast.Store)]
    if not bindings and not is_param:
        return False
    for name in bindings:
        holder = parents.get(id(name))
        if isinstance(holder, ast.Assign) and any(t is name for t in holder.targets):
            value = holder.value
        elif (isinstance(holder, (ast.AnnAssign, ast.NamedExpr)) and holder.target is name
              and holder.value is not None):
            value = holder.value
        elif (isinstance(holder, ast.Tuple) and isinstance(parents.get(id(holder)), ast.Assign)
              and any(t is holder for t in parents[id(holder)].targets)
              and not any(isinstance(e, ast.Starred) for e in holder.elts)):
            position = next(i for i, e in enumerate(holder.elts) if e is name)
            if index is None or position != index:
                return False
            if not _only_carries(defs, fn, parents[id(holder)].value, source, None, seen):
                return False
            continue
        else:
            return False
        if not _only_carries(defs, fn, value, source, index, seen):
            return False
    if is_param:
        calls = [(caller, call) for caller in defs.values() for call in ast.walk(caller)
                 if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                 and call.func.id == fn.name]
        if not calls:
            return False
        for caller, call in calls:
            if any(isinstance(a, ast.Starred) for a in call.args):
                return False
            slot = positional.index(expr.id) if expr.id in positional else None
            if slot is not None and slot < len(call.args):
                arg = call.args[slot]
            else:
                arg = next((kw.value for kw in call.keywords if kw.arg == expr.id), None)
            if arg is None or not _only_carries(defs, caller, arg, source, index, seen):
                return False
    return True


def _own_walk(node):
    """ast.walk without entering nested function or class bodies: the nodes that run when
    node itself runs.  Lambdas are entered — a lambda handed to a thread runs there."""
    todo = [node]
    while todo:
        current = todo.pop()
        yield current
        todo.extend(child for child in ast.iter_child_nodes(current)
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                              ast.ClassDef)))


def _guards(root: ast.AST, node: ast.AST) -> list[ast.AST]:
    """The tests of every if/while/conditional expression between root and node."""
    parents = {id(child): parent for parent in ast.walk(root)
               for child in ast.iter_child_nodes(parent)}
    tests, current = [], node
    while id(current) in parents:
        current = parents[id(current)]
        if isinstance(current, (ast.If, ast.IfExp, ast.While)):
            tests.append(current.test)
    return tests


class VersionAndPinContractTests(unittest.TestCase):
    def test_v110_version_and_final_source_pins_propagate(self):
        problems: list[str] = []

        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if versions != ["1.1.0"]:
            problems.append(f"APP_VERSION must be one literal '1.1.0', got {versions!r}")

        verifier_text = RELEASE_VERIFIER.read_text(encoding="utf-8")
        if "--expect-version 1.1.0" not in verifier_text:
            problems.append("verify_release_artifact.py usage must show --expect-version 1.1.0")
        # A bare version-number substring check would false-positive here: "1.0" is a
        # literal prefix of "1.0.1" (as "0.26" was of "0.26.1", and "1.1" is of "1.1.0"), so a naive
        # `f"--expect-version {stale}" in text` would flag the very string this test just
        # required above. The negative lookahead excludes exactly that case — it only
        # fires on a *bare* stale version, never on it being a prefix of the current one.
        # "1.1", "1.1.1", "1.2", "1.2.0" and "1.0.2" are the plausible wrong bumps; the
        # rest are the versions before.
        for stale in ("1.0.1", "1.0.0", "0.26.1", "0.26", "0.25", "0.24", "1.0",
                      "1.1", "1.1.1", "1.2", "1.2.0", "1.0.2"):
            if re.search(rf"--expect-version {re.escape(stale)}(?!\.\d)", verifier_text):
                problems.append(
                    f"verify_release_artifact.py still advertises --expect-version {stale}"
                )

        expected_pins = (
            (MANUAL_TEST, "REVIEWED_APP_SOURCE_SHA256", APP_SOURCE),
            (MANUAL_TEST, "REVIEWED_BUILD_APP_SHA256", BUILD_SCRIPT),
            (UPLOAD_TEST, "REVIEWED_APP_SOURCE_SHA256", APP_SOURCE),
            (UPLOAD_TEST, "REVIEWED_VERIFIER_SHA256", RELEASE_VERIFIER),
            (UPLOAD_TEST, "REVIEWED_RELEASE_SHA256", RELEASE_SCRIPT),
        )
        for path, name, pinned_file in expected_pins:
            actual_sha = _sha256(pinned_file)
            try:
                pinned_sha = _one_literal_string(path, name)
            except AssertionError as exc:
                problems.append(str(exc))
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", pinned_sha):
                problems.append(f"{path.name}:{name} is not a literal lowercase SHA-256")
            elif pinned_sha != actual_sha:
                problems.append(
                    f"{path.name}:{name} pins {pinned_sha}, final {pinned_file.name} is {actual_sha}"
                )

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


class PublishedNotesImmutabilityTests(unittest.TestCase):
    def test_published_v022_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.22**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.22 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V022_AND_OLDER_SHA256,
            "published v0.22-and-older bytes were rewritten or dropped",
        )

    def test_published_v023_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.23**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.23 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V023_AND_OLDER_SHA256,
            "published v0.23-and-older bytes were rewritten or dropped",
        )

    def test_published_v024_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.24**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.24 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V024_AND_OLDER_SHA256,
            "published v0.24-and-older bytes were rewritten or dropped",
        )

    def test_published_v025_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.25**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.25 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V025_AND_OLDER_SHA256,
            "published v0.25-and-older bytes were rewritten or dropped",
        )

    def test_published_v026_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.26**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.26 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V026_AND_OLDER_SHA256,
            "published v0.26-and-older bytes were rewritten or dropped",
        )

    def test_published_v0261_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v0.26.1**"
        self.assertEqual(raw.count(published_marker), 1, "published v0.26.1 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V0261_AND_OLDER_SHA256,
            "published v0.26.1-and-older bytes were rewritten or dropped",
        )

    def test_published_v100_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v1.0.0**"
        self.assertEqual(raw.count(published_marker), 1, "published v1.0.0 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V100_AND_OLDER_SHA256,
            "published v1.0.0-and-older bytes were rewritten or dropped",
        )

    def test_published_v101_and_older_bytes_are_untouched(self):
        raw = RELEASE_NOTES.read_bytes()
        published_marker = b"**v1.0.1**"
        self.assertEqual(raw.count(published_marker), 1, "published v1.0.1 heading changed")
        published_suffix = raw[raw.index(published_marker) :]
        self.assertEqual(
            hashlib.sha256(published_suffix).hexdigest(),
            PUBLISHED_V101_AND_OLDER_SHA256,
            "published v1.0.1-and-older bytes were rewritten or dropped",
        )

    def test_v110_is_the_only_unpublished_heading_and_sits_directly_above_v101(self):
        """Rivals this heading-shape regex must not miss: a stale two-part-only pattern
        (``\\d+\\.\\d+``) silently fails to match a three-part heading like
        ``**v0.26.1**`` at all — a regex bug that would have made every assertion below
        vacuously pass against an empty ``headings`` list rather than catching a
        misplaced or duplicated heading. The pattern below allows an optional third
        component for exactly this reason — and ``**v1.1.0**`` has one too."""
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        changelog = "### 📝 변경 내역 / Changelog"
        self.assertEqual(text.count(changelog), 1)
        release_area = text.split(changelog, 1)[1]
        headings = re.findall(r"(?m)^\*\*v(\d+\.\d+(?:\.\d+)?)\*\*$", release_area)
        self.assertTrue(headings, "changelog has no release heading")
        self.assertEqual(
            headings[:2],
            ["1.1.0", "1.0.1"],
            "the unpublished v1.1.0 section must sit directly above the published "
            f"v1.0.1 heading, with nothing newer above it; got {headings[:2]!r}",
        )
        self.assertEqual(headings.count("1.1.0"), 1, "v1.1.0 heading must appear once")


class PublishedV023NotesContractTests(unittest.TestCase):
    """The published v0.23 section: its bytes are frozen above, and the source must still
    keep every promise it made — a published note is a contract with the users who read
    it, not a description of one release."""

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.23**", "**v0.22**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v023_notes_follow_the_three_bullet_450_character_format(self):
        self.assertEqual(
            len(self.top_level), 3,
            f"v0.23 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        self.assertEqual(self.nested, [], "v0.23 must not contain nested bullets")
        self.assertEqual(len(self.bullets), 3)

        normalized_body = " ".join(self.visible.split())
        self.assertLessEqual(
            len(normalized_body), 450,
            f"v0.23 Korean body is {len(normalized_body)} Unicode characters; max is 450")

        for index, bullet in enumerate(self.bullets, 1):
            with self.subTest(bullet=index):
                self.assertRegex(bullet, r"[가-힣]", "each release bullet must be Korean")
                count = len(_sentences(bullet))
                self.assertGreaterEqual(count, 1, "each bullet must be at least one sentence")
                self.assertLessEqual(count, 2, "each bullet must have at most 2 sentences")

    def test_v023_notes_state_the_user_facing_behaviour_and_nothing_internal(self):
        problems: list[str] = []
        body = self.body

        # 1. No check at launch; a periodic check every hour instead; a new version still
        #    surfaces as an install item at the top of the context menu.
        if not _has_all(body, (r"새\s*버전", r"켤\s*때", r"하지\s*않", r"1\s*시간", r"마다")):
            problems.append(
                "say the new-version check no longer runs at launch and runs every hour instead")
        if not _has_all(body, (r"새\s*버전이\s*있으면", r"우클릭", r"메뉴", r"(?:맨\s*위|최상단)", r"설치")):
            problems.append(
                "say a new version still appears as an install item at the top of the context menu")

        # 2. The new context-menu item: checks now, and installs then relaunches when there
        #    is a new version.
        if not _has_all(body, (r"우클릭\s*메뉴에", r'"업데이트 확인…"', r"생겼")):
            problems.append('say the context menu gained "업데이트 확인…"')
        if not _has_all(body, (r"누르면", r"바로\s*확인", r"내려받아", r"설치", r"다시\s*켭")):
            problems.append(
                "say pressing it checks now and, if there is a new version, downloads, installs "
                "and relaunches")

        # 3. Straight to the latest release, and the estimator untouched so no recalibration.
        if not _has_all(body, (r"중간\s*버전", r"거치지\s*않", r"최신\s*릴리즈", r"바로")):
            problems.append("say the update goes straight to the latest release, skipping nothing")
        if not _has_all(
            body,
            (r"한도", r"(?:그대로|바뀌지|변경\s*(?:없|되지 않))",
             r"다시\s*보정", r"(?:필요\s*(?:가\s*)?없|불필요)"),
        ):
            problems.append("say recalibration is unnecessary because the limits are unchanged")

        prose_for_forbidden_scan = body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v023_cadence_matches_update_check_sec(self):
        """The notes' "1시간" must be the interval the source actually uses.

        Pinning only the constant would let the sentence drift; pinning only the sentence
        would let the constant drift.  This reads both and compares them in seconds.
        """
        intervals = _literal_assignments(APP_SOURCE, "UPDATE_CHECK_SEC")
        self.assertEqual(
            len(intervals), 1, "claude_pet.py must define exactly one literal UPDATE_CHECK_SEC")
        interval = intervals[0]
        self.assertIs(type(interval), int)
        self.assertEqual(
            interval, EXPECTED_UPDATE_CHECK_SEC,
            f"UPDATE_CHECK_SEC is {interval!r}; the published v0.23 notes promise an hourly check")

        hours = re.findall(r"(\d+(?:\.\d+)?)\s*시간", self.body)
        self.assertEqual(
            len(hours), 1, f"expected exactly one duration in hours in the notes, got {hours!r}")
        self.assertEqual(
            float(hours[0]) * 3600, float(interval),
            f"notes say {hours[0]}시간 but UPDATE_CHECK_SEC is {interval} seconds")
        stray = re.findall(r"\d+(?:\.\d+)?\s*(?:분|초)", self.body)
        self.assertEqual(stray, [], f"durations in the notes not backed by UPDATE_CHECK_SEC: {stray!r}")

    def test_v023_menu_label_is_quoted_exactly_as_the_korean_source_string(self):
        """The quoted menu item must be TR["ko"]["menu_check_update"] minus its arrow glyph.

        The notes tell the user to look for this label in the context menu, so a
        rewording on either side leaves the instruction pointing at nothing.
        """
        table = _tr_table()
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_check_update")]
        self.assertEqual(missing, [], f"menu_check_update missing from locales: {missing}")
        label = table["ko"]["menu_check_update"]
        self.assertEqual(label, KO_CHECK_LABEL, "the published v0.23 notes quote this context-menu label")
        glyph, _, quoted = label.partition(" ")
        self.assertEqual(glyph, "⬆︎", "the label leads with the update arrow, as menu_update does")
        self.assertIn(
            f'"{quoted}"', self.body,
            f"the v0.23 notes must quote the Korean menu label {quoted!r} verbatim")

    def test_v023_no_launch_check_is_backed_by_run_gui(self):
        """"앱을 켤 때 하지 않고": run_gui's top level must stamp the cooldown origin and
        must not start, schedule or call the update check itself."""
        run_gui = _module_def(APP_SOURCE, "run_gui")
        top_level = [s for s in run_gui.body
                     if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        mentions = [ast.unparse(s) for s in top_level
                    if any(isinstance(n, ast.Name) and n.id in
                           ("_run_update_check", "poll_github_update", "check_github_update")
                           for n in ast.walk(s))]
        self.assertEqual(mentions, [], "run_gui's top level still reaches the update check at launch")
        stamps = [s for s in top_level
                  if isinstance(s, ast.Assign) and ast.unparse(s) == "_upd_cache['t'] = time.time()"]
        self.assertEqual(len(stamps), 1, "run_gui must stamp _upd_cache['t'] once at launch")

    def test_v023_direct_to_latest_is_backed_by_the_single_endpoint(self):
        """"중간 버전을 거치지 않고 … 최신 릴리즈로 바로": check_github_update must read
        GitHub's /releases/latest and nothing else, and compare that one tag against
        APP_VERSION."""
        check = _module_def(APP_SOURCE, "check_github_update")
        source = ast.unparse(check)
        endpoints = re.findall(r"https://api\.github\.com/[^\s'\"]*", source)
        self.assertEqual(
            endpoints, [f"https://api.github.com/repos/{{GITHUB_REPO}}/releases/latest"],
            f"check_github_update must read exactly the latest-release endpoint; got {endpoints!r}")
        self.assertIn("_ver_tuple(tag) <= _ver_tuple(APP_VERSION)", source,
                      "the one tag is compared against APP_VERSION — no version walk")
        self.assertNotIn("/releases'", source)
        self.assertNotIn("/releases\"", source)


class ReleaseNotesPolicyTests(unittest.TestCase):
    def test_claude_has_durable_user_facing_release_note_policy(self):
        text = CLAUDE_POLICY.read_text(encoding="utf-8")
        step2 = "2. **Add a section to the top of the changelog"
        step3 = "3. **Build, sign, notarize.**"
        self.assertEqual(text.count(step2), 1)
        self.assertEqual(text.count(step3), 1)
        policy = text.split(step2, 1)[1].split(step3, 1)[0]

        required = {
            "exactly 3 top-level bullets": (r"(?:정확히\s*)?3\s*개", r"(?:최상위|상위)", r"불릿"),
            "450-character budget": (r"450", r"(?:글자|문자)"),
            "no nested bullets": (r"(?:중첩|하위)", r"불릿", r"(?:없|금지|쓰지)"),
            "one or two sentences per bullet": (r"1\s*[~-]\s*2", r"문장"),
            "user action": (r"사용자", r"(?:행동|조치|해야\s*할\s*일)"),
            "auditable quantities": (r"수치|정량", r"AGENTS\.md", r"§\s*5", r"(?:재현|감사|검증|근거)"),
            "no implementation internals": (r"구현", r"식별자", r"해시", r"테스트", r"(?:매트릭스|개수|수)"),
            "published entries stay frozen": (r"published", r"Do not rewrite or drop"),
        }
        missing = [
            label for label, patterns in required.items() if not _has_all(policy, patterns)
        ]
        self.assertEqual(
            missing,
            [],
            "CLAUDE.md release-note policy is missing: " + ", ".join(missing),
        )

    def test_claude_states_the_hourly_never_at_launch_cadence(self):
        """CLAUDE.md's release-procedure sentence about the poll cadence must match
        UPDATE_CHECK_SEC and the no-launch-check behaviour the published v0.23 notes
        describe."""
        text = CLAUDE_POLICY.read_text(encoding="utf-8")
        self.assertIn("polls the repo's latest release tag every hour", text)
        self.assertIn("never at launch", text)
        self.assertNotIn("every 6 hours", text)


class PublishedV024NotesContractTests(unittest.TestCase):
    """The published v0.24 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v0.24 release's ``StagedV024NotesFormatTests`` with its assertions and
    method names unchanged — only its status moved from staged to published when the
    ``v0.24`` tag and GitHub release went out on 2026-09-12.  The format gate still says
    what CLAUDE.md step 2 says: exactly three top-level bullets, no nesting, at most 450
    normalized characters, 1-2 Korean sentences per bullet, and none of the forbidden
    token classes.  Every checkable claim in it stays tied to the source: the threshold
    percentages to ``summary_value_kind``, the spike glyph to ``SUMMARY_SPIKE`` (``≈`` and
    the ⚠ suffix were withdrawn on 2026-10-05 — see the test), the font to ``SUMMARY_FONT_FILE`` and the bundled
    files, the nested layout to ``discover_pets``, the toggle wording to
    ``TR["ko"]["menu_toggle"]``, and the colour roles to ``draw_summary_pill``'s docstring
    — so neither side can drift alone.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.24**", "**v0.23**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v024_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.24 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.24 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.24 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v024_thresholds_and_markers_match_the_source(self):
        quoted = {int(value) for value in re.findall(r"(\d+)%", self.body)}
        function = _module_def(APP_SOURCE, "summary_value_kind")
        compared = {
            node.value for node in ast.walk(function)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        }
        self.assertEqual(quoted, compared,
                         f"notes quote {sorted(quoted)}% but summary_value_kind compares against {sorted(compared)}")
        spike = _one_literal_string(APP_SOURCE, "SUMMARY_SPIKE")
        self.assertIn(spike, self.body, f"the note no longer mentions the {spike!r} marker the pill draws")
        # 2026-10-05 (sou-verify): the ``≈`` estimate marker and the ⚠ suffix were removed
        # by the user's decision "추정 로그치 적는건 이제 없애자!! 기능도 없애고"
        # (docs-design/server-only-usage-20261005.md §1). The v0.24 section is published
        # and frozen, so it still names them; the source no longer backs those two
        # promises, deliberately, and the next release's notes have to say so. The
        # source-side checks for them were removed here; the spike check stays.
        for glyph in ("≈", "⚠"):
            self.assertIn(glyph, self.body, "the frozen v0.24 section changed")

    def test_v024_font_claim_is_backed_by_the_bundled_files_and_both_packagers(self):
        """"Pretendard (OFL)를 앱에 내장": the constant, the two files under fonts/, the
        OFL text, and both packagers (setup.py resources, build_app.sh staging) must all
        name the same font.  Rivals: the note names a font the app does not load; the
        file is missing or a symlink; the licence file is not the OFL; one packager
        ships the font and the other does not."""
        self.assertIn("Pretendard", self.body)
        self.assertIn("OFL", self.body)
        font_file = _one_literal_string(APP_SOURCE, "SUMMARY_FONT_FILE")
        self.assertTrue(font_file.startswith("Pretendard"),
                        f"SUMMARY_FONT_FILE is {font_file!r}; the note promises Pretendard")
        font_path = FONT_DIR / font_file
        self.assertTrue(font_path.is_file(), f"fonts/{font_file} missing — the note promises it is bundled")
        self.assertFalse(font_path.is_symlink(), f"fonts/{font_file} must be a regular file")
        licence = FONT_DIR / "LICENSE-Pretendard.txt"
        self.assertTrue(licence.is_file(), "fonts/LICENSE-Pretendard.txt missing")
        self.assertIn("SIL Open Font License", licence.read_text(encoding="utf-8"),
                      "the bundled licence text is not the OFL the note names")
        setup_text = SETUP.read_text(encoding="utf-8")
        self.assertRegex(setup_text, r'"resources"\s*:\s*\[[^\]]*"fonts"',
                         "setup.py must ship fonts/ as a bundle resource")
        self.assertIn(font_file, BUILD_SCRIPT.read_text(encoding="utf-8"),
                      "build_app.sh must stage the same font file the app loads")

    def test_v024_nested_layout_claim_is_backed_by_discover_pets(self):
        """"pets/이름/이름/ 도 인식": discover_pets must resolve every candidate through
        the module-level _nested_pet_dir exactly once.  Rivals: the note promises a
        layout no code resolves; the helper exists but discover_pets never calls it."""
        self.assertIn("pets/이름/이름/", self.body)
        _module_def(APP_SOURCE, "_nested_pet_dir")
        discover = _module_def(APP_SOURCE, "discover_pets")
        calls = [n for n in ast.walk(discover)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_nested_pet_dir"]
        self.assertEqual(len(calls), 1,
                         "discover_pets must resolve each candidate through _nested_pet_dir exactly once")

    def test_v024_windows_beta_wording_is_present_and_marked_unsigned(self):
        """The Windows beta is built on the Windows branch, not by this tree, so only the
        wording is pinned: the asset name users will look for, and that it is unsigned.
        The macOS updater's asset table must not gain it — a Windows zip is never an
        install candidate for a Mac."""
        self.assertIn("claude-pet-win.zip", self.body)
        self.assertRegex(self.body, r"claude-pet-win\.zip[^)]*서명 없음",
                         "the Windows beta must be described as unsigned beside its file name")
        tables = _literal_assignments(APP_SOURCE, "UPDATE_ASSET_NAMES")
        self.assertEqual(len(tables), 1, "claude_pet.py must define exactly one literal UPDATE_ASSET_NAMES")
        allowed = {str(name).lower() for names in tables[0].values() for name in names}
        self.assertNotIn("claude-pet-win.zip", allowed,
                         "the macOS updater must not treat the Windows zip as an install candidate")

    def test_v024_toggle_wording_matches_every_locale_and_locales_share_one_key_set(self):
        """"접기/펴기 … 그대로": the notes reuse the Korean toggle wording, so
        TR["ko"]["menu_toggle"] must still contain it; every locale's toggle must name
        the pill it now toggles (v0.24 replaced the gauges); and the four locales must
        carry identical key sets so no locale can lose a menu item silently.  Rivals: the
        pre-v0.24 gauge wording in any locale; a locale missing menu_toggle; a Korean
        label reworded away from the notes."""
        table = _tr_table()
        self.assertEqual(sorted(table), ["en", "es", "ja", "ko"])
        key_sets = {lang: set(keys) for lang, keys in table.items()}
        for lang, keys in key_sets.items():
            with self.subTest(lang=lang):
                self.assertEqual(
                    keys, key_sets["en"],
                    f"TR[{lang!r}] keys differ from en: missing {sorted(key_sets['en'] - keys)}, "
                    f"extra {sorted(keys - key_sets['en'])}")
        for lang, word in PILL_WORDS.items():
            with self.subTest(lang=lang):
                label = table[lang].get("menu_toggle", "")
                self.assertIn(word.casefold(), label.casefold(),
                              f"TR[{lang!r}]['menu_toggle'] = {label!r} no longer names the pill")
        self.assertIn(KO_TOGGLE_WORDING, self.body, "the notes must say the toggle is unchanged")
        self.assertIn(KO_TOGGLE_WORDING, table["ko"]["menu_toggle"],
                      "the Korean toggle label must keep the wording the notes reuse")

    def test_v024_pill_docstring_and_notes_agree_on_label_and_value_colours(self):
        """"수치는 출처 … 라벨은 흰색이다가": the values carry the source colour and the
        labels the remaining-budget colour.  draw_summary_pill's docstring must say the
        same (its pre-final wording had the two roles swapped); the behaviour itself is
        gated in tests/test_summary_pill.py."""
        self.assertRegex(self.body, r"수치는\s*출처")
        self.assertRegex(self.body, r"라벨은\s*흰색")
        draw = _nested_function(_module_def(APP_SOURCE, "run_gui"), "draw_summary_pill")
        doc = ast.get_docstring(draw) or ""
        self.assertIn("라벨(잔여량 색)", doc, "draw_summary_pill's docstring must give labels the remaining colour")
        self.assertIn("수치(출처 색)", doc, "draw_summary_pill's docstring must give values the source colour")
        self.assertNotIn("라벨(출처 색)", doc, "swapped roles in draw_summary_pill's docstring")
        self.assertNotIn("수치(잔여량 색)", doc, "swapped roles in draw_summary_pill's docstring")


class PublishedV025NotesContractTests(unittest.TestCase):
    """The published v0.25 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v0.25 release's ``StagedV025NotesFormatTests`` with its assertions and
    method names unchanged — only its status moved from staged to published when the
    ``v0.25`` tag and GitHub release went out on 2026-09-14T05:05:58Z.  The format gate
    still says what CLAUDE.md step 2 says: exactly three top-level
    bullets, no nesting, at most 450 normalized characters, 1-2 Korean sentences per
    bullet, and none of the forbidden token classes.  Every checkable claim in it is then
    tied to the source: the quoted "로그인 시 자동 실행" to ``TR["ko"]["menu_autostart"]``;
    "시스템 설정 … 에서 끄면 메뉴에도 꺼진 것으로 보입니다" to the menu reading the OS
    registration through ``autostart_read_state`` (which asks the service for ``status()``)
    and to no autostart function writing the config or ``RUNTIME``; "토큰을 갱신하거나 서버
    응답이 잠깐 실패해도 재시작 없이" to the token cache's rotation and re-validation
    paths, the forced re-read on 401/403, the ``suspect`` flag, and a failure-retry
    interval shorter than the success cache; and the quoted "완전 삭제…" with "내 펫 폴더는
    남깁니다" to ``TR["ko"]["menu_uninstall"]`` and to ``UNINSTALL_PATHS`` naming the config
    and the cache directory but never the user's pet home.  The Windows halves of those
    sentences are built on the Windows branch and are not checkable here.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.25**", "**v0.24**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v025_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.25 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.25 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.25 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v025_autostart_label_is_quoted_exactly_as_the_korean_source_string(self):
        """"우클릭 메뉴에 "로그인 시 자동 실행"이 생겼습니다": the quoted label must be
        TR["ko"]["menu_autostart"] verbatim, every locale must carry the item and its
        companion strings, and the context menu built in run_gui must actually add the
        item.  Rivals: a Korean label reworded on either side; a locale missing the key
        (the v0.24 key-set test catches a missing key, not a wrong Korean label); a menu
        that never adds the item although the strings exist."""
        table = _tr_table()
        for key in ("menu_autostart", "autostart_title", "autostart_approval",
                    "autostart_open_settings", "autostart_fail", "autostart_unavailable"):
            missing = [lang for lang in ("en", "ko", "ja", "es") if not table.get(lang, {}).get(key)]
            self.assertEqual(missing, [], f"{key} missing from locales: {missing}")
        label = table["ko"]["menu_autostart"]
        self.assertEqual(label, KO_AUTOSTART_LABEL, "the v0.25 notes quote this context-menu label")
        self.assertRegex(self.body, r"우클릭\s*메뉴에\s*\"" + re.escape(label) + r"\"",
                         f"the v0.25 notes must quote the Korean menu label {label!r} verbatim")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        menu_keys = {n.args[0].value for n in _calls_to(run_gui, "t")
                     if n.args and isinstance(n.args[0], ast.Constant)}
        self.assertIn("menu_autostart", menu_keys, "run_gui never puts menu_autostart in the menu")
        self.assertIn("autostart_unavailable", menu_keys,
                      "run_gui must retitle the item with autostart_unavailable when there is no service")

    def test_v025_autostart_state_is_read_from_the_os_and_never_stored(self):
        """"시스템 설정 … 에서 끄면 메뉴에도 꺼진 것으로 보입니다": the checkmark must come
        from the OS registration, read afresh, never from a stored flag.  So
        autostart_read_state asks the service for status(); autostart_toggle re-reads
        the state through autostart_read_state after registering (a register can land in
        "approval"); none of the four autostart functions touches RUNTIME, the config or
        a config writer; and run_gui reaches autostart_read_state through the
        "autostart_read" hook the menu consults.  Rivals: a stored flag that goes stale
        the moment System Settings turns the item off; a toggle that assumes "registered
        means on"; a menu that reads a config key instead of the hook."""
        read_state = _module_def(APP_SOURCE, "autostart_read_state")
        self.assertEqual(len(_method_calls(read_state, "status")), 1,
                         "autostart_read_state must ask the service for status() exactly once")
        toggle = _module_def(APP_SOURCE, "autostart_toggle")
        self.assertEqual(len(_calls_to(toggle, "autostart_read_state")), 2,
                         "autostart_toggle must read the state before and re-read it after the call")
        self.assertTrue(_method_calls(toggle, "registerAndReturnError_"),
                        "autostart_toggle never registers")
        self.assertTrue(_method_calls(toggle, "unregisterAndReturnError_"),
                        "autostart_toggle never unregisters")
        forbidden = {"RUNTIME", "cfg", "CONFIG_PATH", "save_config", "merge_config_updates",
                     "load_config", "USER_PET_HOME"}
        for name in ("autostart_state", "autostart_read_state", "autostart_toggle",
                     "uninstall_autostart"):
            with self.subTest(function=name):
                touched = sorted(_names(_module_def(APP_SOURCE, name)) & forbidden)
                self.assertEqual(touched, [], f"{name} must not touch the config or RUNTIME: {touched}")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        self.assertIn("autostart_read", _strings([run_gui]),
                      "run_gui must expose the autostart_read hook the menu consults")
        self.assertTrue(_calls_to(run_gui, "autostart_read_state"),
                        "run_gui's hook must read the state through autostart_read_state")

    def test_v025_exact_mode_recovery_is_backed_by_the_token_cache(self):
        """"토큰을 갱신하거나 서버 응답이 잠깐 실패해도 재시작 없이 정확 모드로": three
        mechanisms, each pinned to a name the behavioural gates in
        tests/test_oauth_token_cache.py exercise.  Rotation: _read_oauth_token compares
        the credentials file's signature (_credentials_sig) and re-validates a suspect
        token (_revalidate_oauth_token).  Rejection: _fetch_oauth_usage re-reads the token
        with force=True on 401/403 and raises the suspect flag on every other failure.
        Transient failure: OAUTH_FAIL_RETRY_SEC is a literal shorter than OAUTH_CACHE_SEC
        and fetch_exact_usage consults it, so a failed fetch is not cached for the full
        success interval.  Rivals: a cache with no rotation signal; a fetch that gives up
        on a 5xx without marking the token suspect; a failure cached for the full 180 s
        (the v0.24 behaviour the note says is gone); a retry constant no shorter than the
        cache, which changes nothing."""
        self.assertRegex(self.body, r"재시작\s*없이")
        self.assertRegex(self.body, r"정확\s*모드")
        self.assertRegex(self.body, r"추정\s*모드")
        read = _module_def(APP_SOURCE, "_read_oauth_token")
        self.assertTrue(_calls_to(read, "_credentials_sig"),
                        "_read_oauth_token must compare the credentials file signature (rotation signal)")
        self.assertTrue(_calls_to(read, "_revalidate_oauth_token"),
                        "_read_oauth_token must re-validate a suspect token")
        fetch = _module_def(APP_SOURCE, "_fetch_oauth_usage")
        forced = [c for c in _calls_to(fetch, "_read_oauth_token")
                  if any(k.arg == "force" and isinstance(k.value, ast.Constant) and k.value.value is True
                         for k in c.keywords)]
        self.assertEqual(len(forced), 1, "_fetch_oauth_usage must re-read the token once with force=True")
        fetch_src = ast.unparse(fetch)
        self.assertIn("c['suspect'] = True", fetch_src, "a non-auth failure must mark the token suspect")
        self.assertIn("c['suspect'] = False", fetch_src, "a success must clear the suspect flag")
        retry = _one_literal_int(APP_SOURCE, "OAUTH_FAIL_RETRY_SEC")
        cache = _one_literal_int(APP_SOURCE, "OAUTH_CACHE_SEC")
        self.assertGreater(retry, 0)
        self.assertLess(retry, cache,
                        f"OAUTH_FAIL_RETRY_SEC={retry} must be shorter than OAUTH_CACHE_SEC={cache}")
        exact = _module_def(APP_SOURCE, "fetch_exact_usage")
        self.assertIn("OAUTH_FAIL_RETRY_SEC", _names(exact),
                      "fetch_exact_usage must cache a failure for OAUTH_FAIL_RETRY_SEC, not the full interval")

    def test_v025_uninstall_label_is_quoted_and_the_pet_folder_survives_it(self):
        """""완전 삭제…"는 설정과 캐시까지 지우고 내 펫 폴더는 남깁니다": the quoted label
        must be TR["ko"]["menu_uninstall"] verbatim; UNINSTALL_PATHS must name the config
        (CONFIG_PATH) and the cache directory (UPDATE_LOCK_DIR) and must not name the
        user's pet home, by constant or by path text; and do_uninstall must delete
        through uninstall_targets rather than reaching for USER_PET_HOME itself.  Rivals:
        a reworded label on either side; the pet home added to the list "to clean up
        completely"; the cache directory dropped so the sentence over-promises; a direct
        rmtree of the pet home outside the list."""
        table = _tr_table()
        label = table["ko"]["menu_uninstall"]
        self.assertEqual(label, KO_UNINSTALL_LABEL, "the v0.25 notes quote this context-menu label")
        self.assertIn(f'"{label}"', self.body,
                      f"the v0.25 notes must quote the Korean menu label {label!r} verbatim")
        self.assertRegex(self.body, r"펫\s*폴더는\s*남깁니다")
        paths = _module_assignment(APP_SOURCE, "UNINSTALL_PATHS")
        self.assertIsInstance(paths.value, ast.Tuple, "UNINSTALL_PATHS must stay a tuple literal")
        names = _names(paths.value)
        self.assertIn("CONFIG_PATH", names, "UNINSTALL_PATHS must delete the settings file")
        self.assertIn("UPDATE_LOCK_DIR", names, "UNINSTALL_PATHS must delete the cache directory")
        self.assertNotIn("USER_PET_HOME", names, "UNINSTALL_PATHS must never name the user's pet home")
        for text in _strings([paths.value]):
            self.assertNotIn(".claude_pet/", text, f"UNINSTALL_PATHS reaches into the pet home: {text!r}")
            self.assertNotEqual(text.rstrip("/"), "~/.claude_pet",
                                "UNINSTALL_PATHS must never name the user's pet home")
        do_uninstall = _module_def(APP_SOURCE, "do_uninstall")
        self.assertTrue(_calls_to(do_uninstall, "uninstall_targets"),
                        "do_uninstall must delete through uninstall_targets")
        self.assertNotIn("USER_PET_HOME", _names(do_uninstall),
                         "do_uninstall must not reach for the pet home directly")
        targets = _module_def(APP_SOURCE, "uninstall_targets")
        self.assertIn("UNINSTALL_PATHS", _names(targets), "uninstall_targets must read UNINSTALL_PATHS")


class PublishedV026NotesContractTests(unittest.TestCase):
    """The published v0.26 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v0.26 release's former ``StagedV026NotesFormatTests`` with its assertions
    and method names unchanged — only its status moved from staged to published when the
    ``v0.26`` tag and GitHub release went out on 2026-09-20T15:50:23Z (the same promotion
    the v0.25 class went through a release earlier).  Every assertion below was
    re-verified against current source before this rename (2026-09-21) and still holds.
    One exception since: on 2026-09-30 (cwdfix) the "할 일은 없고" spawn tie in
    ``test_v026_pre_emptive_refresh_is_backed_by_recovery_tick_and_the_spawn`` was re-tied
    from ``launchctl submit`` to the one-shot ``bootstrap`` job, because the old tie encoded
    the claim that turned out false; the frozen notes bytes are untouched.
    The format gate still says what CLAUDE.md step 2 says: exactly three top-level
    bullets, no nesting, at most 450 normalized characters, 1-2 Korean sentences per
    bullet, and none of the forbidden token classes.  Every checkable claim in it is then
    tied to the source, one test per bullet:

    * "토큰이 끊기던 상황에서도 정확 모드가 유지됩니다 — 펫이 만료 직전에 알아서
      되살립니다 … 우클릭 메뉴 "토큰 자동 갱신"에서 끌 수
      있습니다" — the quoted label to ``TR["ko"]["menu_auto_recover"]`` and the menu
      wiring in ``run_gui``; "만료 직전" to ``recovery_tick``'s **pre-emptive** branch
      (``REFRESH_MARGIN_SEC`` before ``expires_at``, not merely a retry after rejection);
      "할 일은 없고" to the ``RUNTIME["auto_recover"]`` default being on and to
      ``claude -p /usage`` being handed to launchd as a one-shot ``bootstrap`` job with the
      private ``recovery_cli_cwd()`` as its WorkingDirectory and no keep-alive, rather than
      run as our own child (re-tied 2026-09-30 from ``launchctl submit``, whose cwd ``/``
      and keep-alive raised the folder prompts the note promised away).
    * "각 제공자의 수치가 그 로고와 함께 자기 줄에 보입니다 … 쓰지 않으면 줄도 로고도
      생기지 않습니다" — the wording the *tag*'s tree actually carries (a later commit
      reworded this bullet after the release commit that first staged it; see the module
      docstring's provenance note) — to the single
      ``chatgpt.com/backend-api/wham/usage`` endpoint, to the row carrying the same
      ``"exact"`` segment kind the Claude rows use, and to both ``fetch_codex_usage`` and
      ``roam_summary_codex`` returning ``None`` — no row at all, not a 0% row — when
      there are no Codex credentials.
    * "크레딧을 켜 두었다면 쓴 금액이 $로 … "크레딧 금액으로"에서 %로 … "조회 중"에
      머물지 않고 이유를" — "켜 두었다면" to ``_parse_oauth_usage`` gating the credit row
      on ``user_disabled`` and **not** on ``is_enabled``; "$" to ``CREDIT_DISPLAY_DEFAULT``
      being money and ``credit_row_text`` reaching ``CURRENCY_SIGNS``; the quoted toggle to
      ``TR["ko"]["menu_credit_money"]`` and its menu wiring; and the quoted "조회 중" to
      ``TR["ko"]["loading"]`` together with ``roam_summary``'s API branch leaving that
      status for a distinct, translated reason once a fetch has actually failed.

    The v0.26 notes make no Windows claim, so unlike v0.25 nothing here is split across
    branches.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.26**", "**v0.25**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v026_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.26 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.26 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.26 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_every_quoted_string_in_the_notes_is_a_real_korean_ui_string(self):
        """따옴표 안의 모든 문구가 실제 ``TR["ko"]`` 값이어야 한다 — **하나도 빠짐없이.**

        이 테스트가 왜 따로 필요한가: 아래 세 테스트는 내가 **이름을 하나씩 적어 둔** 세
        라벨만 본다(`menu_auto_recover`, `menu_credit_money`, `loading`). 다음 릴리즈에서
        네 번째 문구를 인용하면 그건 **아무도 검사하지 않는다**. 인용된 라벨이 화면의
        문자열과 어긋나면 사용자는 있지도 않은 메뉴 항목을 찾게 되고, 그건 노트가 할 수
        있는 거짓말 중 사용자가 가장 빨리 부딪히는 종류다.

        허용하는 변형은 둘뿐이고 **의도적**이다:

        · 끝의 말줄임표를 뗀 형태 — "조회 중…"을 문장 안에서 "조회 중"으로 인용하는 것.
          사용자가 *읽는* 상태 문구이지 *누르는* 항목이 아니라, 말줄임표까지 옮기면
          문장이 어색해진다. v0.23 노트가 "⬆︎ 업데이트 확인…"을 "업데이트 확인…"으로
          인용한 선례와 같은 처리다.
        · 앞의 글리프를 뗀 형태 — 같은 선례의 화살표(⬆︎) 쪽.

        그 밖의 불일치는 전부 실패다. 변형을 허용한다는 것과 검사하지 않는다는 것은
        다르고, 이 테스트는 어느 변형으로 맞았는지까지 실패 메시지에 적는다.
        """
        table = _tr_table()["ko"]

        def forms(value):
            out = {value}
            out.add(value.rstrip("…").strip())
            head, _, rest = value.partition(" ")
            if rest and not re.match(r"[0-9A-Za-z가-힣]", head):
                out.add(rest)
                out.add(rest.rstrip("…").strip())
            return {form for form in out if form}

        index = {}
        for key, value in table.items():
            if isinstance(value, str):
                for form in forms(value):
                    index.setdefault(form, []).append(key)

        quoted = re.findall(r'"([^"]+)"', self.body)
        self.assertTrue(
            quoted,
            "노트가 UI 문구를 하나도 인용하지 않는다 — 이 테스트가 공허해졌거나 "
            "인용이 사라졌다. 어느 쪽인지 사람이 확인해야 한다.")
        problems = [q for q in quoted if q not in index]
        self.assertEqual(
            problems, [],
            "노트가 인용한 문구가 TR['ko'] 의 어떤 값과도 맞지 않는다 "
            f"{problems!r} — 사용자가 화면에서 찾을 수 없는 이름이다. "
            f"(검사한 인용: {quoted!r})")

    def test_v026_auto_recover_label_is_quoted_and_the_toggle_is_in_the_menu(self):
        """"우클릭 메뉴 "토큰 자동 갱신"에서 끌 수 있습니다": the quoted label must be
        TR["ko"]["menu_auto_recover"] verbatim, every locale must carry the key, and
        run_gui must actually put that item in the context menu behind its own action.
        Rivals: a Korean label reworded on either side; a locale missing the key; the
        strings existing while no menu item is ever built, so the sentence sends the user
        looking for something that is not there."""
        table = _tr_table()
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_auto_recover")]
        self.assertEqual(missing, [], f"menu_auto_recover missing from locales: {missing}")
        label = table["ko"]["menu_auto_recover"]
        self.assertEqual(label, KO_AUTO_RECOVER_LABEL, "the v0.26 notes quote this context-menu label")
        self.assertRegex(self.body, r"우클릭\s*메뉴\s*\"" + re.escape(label) + r"\"",
                         f"the v0.26 notes must quote the Korean menu label {label!r} verbatim")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        menu_keys = {n.args[0].value for n in _calls_to(run_gui, "t")
                     if n.args and isinstance(n.args[0], ast.Constant)}
        self.assertIn("menu_auto_recover", menu_keys, "run_gui never puts menu_auto_recover in the menu")
        self.assertIn("toggleAutoRecover:", _strings([run_gui]),
                      "run_gui must wire the item to its own toggle action")

    def test_v026_pre_emptive_refresh_is_backed_by_recovery_tick_and_the_spawn(self):
        """"Claude Code를 한동안 안 써서 토큰이 끊기던 상황에서도 정확 모드가 유지됩니다 —
        펫이 만료 직전에 알아서 되살립니다. 할 일은 없고": three separable claims.

        "만료 직전" is the **pre-emptive** path, which is not the same as retrying after a
        rejection: recovery_tick must weigh expires_at against REFRESH_MARGIN_SEC and must
        treat an unknown expiry (expires_at is None) as *not* expiring, and it must rate
        limit that path with RECOVERY_COOLDOWN_SEC.  "할 일은 없고" is the default being
        on — RUNTIME["auto_recover"] reads an opt-out env var, so an untouched install is
        True — and the spawn not costing the user a folder prompt: on macOS the CLI is
        handed to launchd as a one-shot ``bootstrap`` job whose WorkingDirectory is the
        private ``recovery_cli_cwd()`` and which is never kept alive, so it is launchd's
        child and not ours, and it runs once, away from ``/``.  "토큰이
        끊기던 상황에서도 … 유지됩니다" is the reactive path surviving more than one
        rejection — the pre-emptive branch alone would not keep the promise for a token
        that is already rejected — so RECOVERY_DELAYS_SEC must be a literal tuple with
        more than one entry.

        Re-tied 2026-09-30 (cwdfix, Verifier): this used to pin
        ``return [LAUNCHCTL, 'submit'`` in recovery_spawn_argv, i.e. the claim that handing
        the CLI to ``launchctl submit`` spares the user a folder prompt.  That claim is what
        turned out false — ``submit`` has no working-directory option, so the CLI ran with
        cwd ``/`` and asked for protected folders in its own name, and ``submit`` re-runs a
        job after it exits — even after exit 0 — so one attempt became three CLI runs in the
        06:15 launchd log.  The note's promise now
        rests on the mechanism tied below, stated as a property of everything reachable
        from _run_refresh_job (review R1: an earlier version pinned one implementation's
        shape instead).  It is a prose tie and deliberately loose — it cannot see *which*
        directory the job gets; the behaviour itself is gated in
        tests/test_token_recovery.py (``DarwinOneShotJobTests`` and friends).

        Rivals, each of which would leave the sentence false: a reactive-only cycle that
        waits for the server to reject before doing anything (no REFRESH_MARGIN_SEC); a
        tick that reads a missing expiry as expired and so spawns the CLI on every launch;
        an opt-in default, which makes "할 일은 없고" wrong for everyone; running the CLI
        as our own child, which attributes its folder scans to the pet; a launchd job with
        no private WorkingDirectory or with keep-alive (v0.26's ``submit``), which lets the
        CLI ask for protected folders in its own name and relaunch after it exits; a
        single retry."""
        tick = _module_def(APP_SOURCE, "recovery_tick")
        tick_names = _names(tick)
        for constant in ("REFRESH_MARGIN_SEC", "RECOVERY_COOLDOWN_SEC", "RECOVERY_DELAYS_SEC"):
            self.assertIn(constant, tick_names,
                          f"recovery_tick must consult {constant}")
        self.assertIn("expires_at", tick_names, "recovery_tick must take the token expiry into account")
        tick_src = ast.unparse(tick)
        self.assertIn("if expires_at is None:\n        return (r, None)", tick_src,
                      "an unknown expiry must not be read as an expired one")
        self.assertIn("(expires_at - now).total_seconds() > REFRESH_MARGIN_SEC", tick_src,
                      "the pre-emptive branch must compare the remaining lifetime to the margin")
        margin = _one_literal_int(APP_SOURCE, "REFRESH_MARGIN_SEC")
        self.assertGreater(margin, 0, "a non-positive margin would never fire before expiry")

        delays = _literal_assignments(APP_SOURCE, "RECOVERY_DELAYS_SEC")
        self.assertEqual(len(delays), 1, "claude_pet.py must define exactly one literal RECOVERY_DELAYS_SEC")
        self.assertIsInstance(delays[0], tuple)
        self.assertGreater(len(delays[0]), 1,
                           "the notes promise the pet keeps trying; one attempt is not 'keeps'")

        runtime = _module_assignment(APP_SOURCE, "RUNTIME")
        self.assertIsInstance(runtime.value, ast.Dict, "RUNTIME must stay a dict literal")
        defaults = {k.value: ast.unparse(v)
                    for k, v in zip(runtime.value.keys, runtime.value.values)
                    if isinstance(k, ast.Constant)}
        self.assertEqual(
            defaults.get("auto_recover"),
            "os.environ.get('CLAUDE_PET_AUTO_RECOVER', '1') != '0'",
            "auto_recover must default ON (an opt-out env var); the notes say there is "
            f"nothing to do, got {defaults.get('auto_recover')!r}")

        spawn = _module_def(APP_SOURCE, "recovery_spawn_argv")
        self.assertIn("'-p', '/usage'", ast.unparse(spawn),
                      "the refresh is triggered by one `claude -p /usage` run")
        self.assertNotIn("LAUNCHCTL", _names(spawn),
                         "recovery_spawn_argv returns the program the detached job runs, with "
                         "no launcher in front (the spec's words)")

        # "할 일은 없고" — the spawn costs the user no folder prompt.  Written as a PROPERTY of
        # the spawn path, read from the spec, not as the shape of one implementation: review
        # R1 showed the two earlier versions of this block rejecting legitimate code (a job
        # dict built key by key, bootstrap two calls down, a helper fed by a parameter) and,
        # once amended, accepting little beyond the fix's own shape.  The spawn path is every
        # module-level function reachable from _run_refresh_job through any name, at any
        # depth.  What it must show: `bootstrap`, never `submit`; recovery_cli_cwd feeding it;
        # the job keys; RunAtLoad and KeepAlive at the only values that mean "one run".
        tree = _module_tree(APP_SOURCE)
        defs = {n.name: n for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        module_strings = {}               # NAME = "literal" (or any container of literals)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                literals = {c.value for c in ast.walk(node.value)
                            if isinstance(c, ast.Constant) and isinstance(c.value, str)}
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_strings[target.id] = literals

        def reachable(*roots):
            seen, todo = set(), list(roots)
            while todo:
                name = todo.pop()
                if name in seen or name not in defs:
                    continue
                seen.add(name)
                todo.extend(n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name))
            return [defs[name] for name in sorted(seen)]

        def docstring_nodes(fns):
            ids = set()
            for fn in fns:
                for n in ast.walk(fn):
                    if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                            and n.body and isinstance(n.body[0], ast.Expr)
                            and isinstance(n.body[0].value, ast.Constant)
                            and isinstance(n.body[0].value.value, str)):
                        ids.add(id(n.body[0].value))
            return ids

        def code_strings(fns):
            """String literals the code uses (docstrings excluded — they may tell the
            `submit` history), plus the literals of module constants it names."""
            skip, out = docstring_nodes(fns), set()
            for fn in fns:
                for n in ast.walk(fn):
                    if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                            and id(n) not in skip):
                        out.add(n.value)
                    elif isinstance(n, ast.Name) and n.id in module_strings:
                        out |= module_strings[n.id]
            return out

        def spelled_keys(fns):
            """Every key the code can spell: string literals and keyword names (dict(...))."""
            return code_strings(fns) | {kw.arg for fn in fns for kw in ast.walk(fn)
                                        if isinstance(kw, ast.keyword) and kw.arg}

        def values_given(fns, key):
            """Every value the code gives `key`: in a dict display, a subscript assignment,
            a keyword argument or `.setdefault(key, value)`.  Any other mention of the key is
            a value this test cannot read — recorded as None, which fails closed."""
            found, placed, skip = [], set(), docstring_nodes(fns)
            for fn in fns:
                for n in ast.walk(fn):
                    if isinstance(n, ast.Dict):
                        for k, v in zip(n.keys, n.values):
                            if isinstance(k, ast.Constant) and k.value == key:
                                found.append(v)
                                placed.add(id(k))
                    elif isinstance(n, ast.Assign):
                        for target in n.targets:
                            if (isinstance(target, ast.Subscript)
                                    and isinstance(target.slice, ast.Constant)
                                    and target.slice.value == key):
                                found.append(n.value)
                                placed.add(id(target.slice))
                    elif isinstance(n, ast.Call):
                        found.extend(kw.value for kw in n.keywords if kw.arg == key)
                        if (isinstance(n.func, ast.Attribute) and n.func.attr == "setdefault"
                                and len(n.args) == 2 and isinstance(n.args[0], ast.Constant)
                                and n.args[0].value == key):
                            found.append(n.args[1])
                            placed.add(id(n.args[0]))
            for fn in fns:
                for n in ast.walk(fn):
                    if (isinstance(n, ast.Constant) and n.value == key
                            and id(n) not in placed and id(n) not in skip):
                        found.append(None)
            return found

        spawn_path = reachable("_run_refresh_job")
        self.assertIn("bootstrap", code_strings(spawn_path),
                      "on macOS the CLI must be handed to launchd with `launchctl bootstrap`")
        whole_path = reachable("_run_refresh_job", "recovery_spawn_argv", "login_spawn_argv")
        self.assertNotIn("submit", code_strings(whole_path),
                         "`launchctl submit` must appear nowhere in the spawn path: it runs the "
                         "CLI from / and re-runs the job after it exits, even after exit 0")
        self.assertIn("recovery_cli_cwd",
                      {n.id for fn in spawn_path for n in ast.walk(fn) if isinstance(n, ast.Name)},
                      "the job's working directory must come from recovery_cli_cwd()")
        missing = sorted({"ProgramArguments", "WorkingDirectory", "RunAtLoad"}
                         - spelled_keys(spawn_path))
        self.assertEqual(missing, [], f"the launchd job definition lacks {missing}")
        for key, required in (("RunAtLoad", True), ("KeepAlive", False), ("OnDemand", True)):
            wrong = [v for v in values_given(spawn_path, key)
                     if not (isinstance(v, ast.Constant) and v.value is required)]
            self.assertEqual(
                ["<unreadable>" if v is None else ast.unparse(v) for v in wrong], [],
                f"{key} must be literally {required} wherever the spawn path sets it — the job "
                "runs once and is never relaunched")
        triggers = sorted({"StartInterval", "StartCalendarInterval", "WatchPaths",
                           "QueueDirectories", "StartOnMount", "Sockets", "MachServices",
                           "LaunchEvents"} & spelled_keys(spawn_path))
        self.assertEqual(triggers, [], f"the launchd job carries relaunch triggers {triggers}")

    def test_v026_codex_row_comes_from_one_endpoint_and_vanishes_without_credentials(self):
        """"Codex 사용량이 같은 줄에 함께 보입니다. Codex에 로그인돼 있으면 자동으로
        나타나고, 쓰지 않으면 아무것도 달라지지 않습니다."

        "같은 줄" means the Codex rows are one more segment of the same summary pill, in
        the same ``exact`` kind the server-derived Claude rows use — not a second line and
        not an estimate colour.  "쓰지 않으면 아무것도 달라지지 않습니다" means *no row*,
        which is stronger than a zero row: fetch_codex_usage must return None the moment
        the credential read comes back empty, and roam_summary_codex must return None for
        empty rows.  And the row may come from exactly one endpoint.

        Rivals: a 0% Codex row for users who have never signed in, which reads as "you
        have barely used it"; a second provider endpoint added quietly beside the first;
        the row rendered as an estimate, which would tell the user we guessed a number the
        server actually computed."""
        self.assertIn("Codex", self.body, "the v0.26 notes must name the provider they add")
        # The note's claim got **stronger** when the layout changed. It used to read
        # "같은 줄에 함께 보입니다 … 쓰지 않으면 아무것도 달라지지 않습니다"; Codex now has
        # its own line and its own mark, so the sentence is "제공자 로고와 함께 아래 줄에
        # 보입니다 … 쓰지 않으면 줄도 로고도 생기지 않습니다". That second half promises two
        # absences, not one, and an empty line or an orphan mark would each falsify it —
        # which is exactly what tests/test_summary_layout.py's
        # AbsentProviderLeavesNoTraceTests asserts, separately from any width check.
        self.assertRegex(self.body, r"로고와\s*함께",
                         "the note must say the Codex row is marked with its provider logo")
        self.assertRegex(self.body, r"쓰지\s*않으면\s*줄도\s*로고도\s*생기지\s*않습니다",
                         "the note must promise no line AND no logo for an unused provider")

        fetch = _module_def(APP_SOURCE, "fetch_codex_usage")
        urls = set(re.findall(r"https://[^\s'\"]+", ast.unparse(fetch)))
        self.assertEqual(
            urls, {CODEX_USAGE_URL},
            f"fetch_codex_usage must read exactly the one Codex usage endpoint; got {sorted(urls)!r}")
        fetch_src = ast.unparse(fetch)
        self.assertIn("if not tok:", fetch_src, "no credentials must short-circuit before any request")
        self.assertRegex(fetch_src, r"if not tok:\n(?:.*\n)?\s*return None",
                         "fetch_codex_usage must return None — not an empty row set — without a token")

        summary = _module_def(APP_SOURCE, "roam_summary_codex")
        returns = {ast.unparse(n) for n in ast.walk(summary) if isinstance(n, ast.Return)}
        self.assertIn("return None", returns,
                      "roam_summary_codex must drop the segment entirely when there is nothing to show")
        self.assertIn("return ('exact', out)", returns,
                      "the Codex segment must carry the same 'exact' kind the server-derived rows use")
        self.assertIn("if not rows:", ast.unparse(summary),
                      "empty rows must produce no segment rather than a 0% row")

    def test_v026_credit_row_is_money_by_default_and_gated_on_user_disabled(self):
        """"크레딧을 켜 두었다면 쓴 금액이 $로 보입니다. 우클릭 메뉴 "크레딧 금액으로"에서
        %로 바꿀 수 있고":

        "켜 두었다면" is the **user's** switch, and the source says so in one place: the
        credit row is gated on ``user_disabled`` and must not consult ``is_enabled``, which
        the organisation lowers when a spend limit is reached.  Gating on is_enabled would
        hide the credit row from exactly the user who most needs it — the repository has
        made and reverted that change once.  "$로 보입니다" is the default display mode
        being money and the formatter reaching a currency sign.  The quoted toggle must be
        the Korean label verbatim, wired into the menu, and it must flip between exactly
        the two modes the renderer knows.

        Rivals: the is_enabled gate, which passes every test built from a healthy account;
        a percent default, making the first sentence wrong; a third display mode, which
        leaves the renderer with a value it cannot draw; a reworded label on either side."""
        table = _tr_table()
        missing = [lang for lang in ("en", "ko", "ja", "es")
                   if not table.get(lang, {}).get("menu_credit_money")]
        self.assertEqual(missing, [], f"menu_credit_money missing from locales: {missing}")
        label = table["ko"]["menu_credit_money"]
        self.assertEqual(label, KO_CREDIT_MONEY_LABEL, "the v0.26 notes quote this context-menu label")
        self.assertIn(f'"{label}"', self.body,
                      f"the v0.26 notes must quote the Korean menu label {label!r} verbatim")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        menu_keys = {n.args[0].value for n in _calls_to(run_gui, "t")
                     if n.args and isinstance(n.args[0], ast.Constant)}
        self.assertIn("menu_credit_money", menu_keys, "run_gui never puts menu_credit_money in the menu")
        self.assertIn("toggleCreditMoney:", _strings([run_gui]),
                      "run_gui must wire the item to its own toggle action")

        modes = _literal_assignments(APP_SOURCE, "CREDIT_DISPLAY_MODES")
        self.assertEqual(len(modes), 1, "claude_pet.py must define exactly one literal CREDIT_DISPLAY_MODES")
        self.assertEqual(tuple(modes[0]), ("money", "pct"),
                         "the toggle flips between exactly the two modes the pill can draw")
        self.assertEqual(_one_literal_string(APP_SOURCE, "CREDIT_DISPLAY_DEFAULT"), "money",
                         "the v0.26 notes say the amount is what the user sees first")
        self.assertRegex(self.body, r"금액이\s*\$로", "the notes must say the amount is shown in currency")
        row_text = _module_def(APP_SOURCE, "credit_row_text")
        self.assertIn("CURRENCY_SIGNS", _names(row_text),
                      "credit_row_text must reach the currency signs the notes' '$' comes from")
        signs = _literal_assignments(APP_SOURCE, "CURRENCY_SIGNS")
        self.assertEqual(len(signs), 1, "claude_pet.py must define exactly one literal CURRENCY_SIGNS")
        self.assertEqual(signs[0].get("USD"), "$", "the '$' in the notes must be a sign the source knows")

        parse = _module_def(APP_SOURCE, "_parse_oauth_usage")
        gates = [n for n in ast.walk(parse)
                 if isinstance(n, ast.If) and "user_disabled" in ast.unparse(n.test)]
        self.assertEqual(len(gates), 1,
                         "_parse_oauth_usage must gate the credit row on user_disabled exactly once")
        self.assertEqual(
            ast.unparse(gates[0].test),
            "isinstance(extra, dict) and (not extra.get('user_disabled'))",
            "the credit gate must ask only whether the user turned credits off")
        self.assertNotIn(
            "is_enabled", ast.unparse(gates[0]),
            "is_enabled is lowered when a spend limit is reached; gating on it hides the "
            "credit row from the user who most needs to see it")

    def test_v026_api_failure_says_why_instead_of_sitting_on_loading(self):
        """""조회 중"에 머물지 않고 이유를 알려 줍니다": the quoted status is
        TR["ko"]["loading"] minus its ellipsis, and roam_summary's API branch must leave it
        for a *distinct* reason once a fetch has actually failed — a rejected key and a
        transient failure are different sentences, both translated in all four locales,
        because api_error_kind splits 401/403 from everything else.

        Rivals: one shared error string, which is a false instruction to half the people
        who see it (telling a user whose network dropped to go check a working key); the
        status left at "loading" after a definitive rejection, which is the v0.25
        behaviour the note says is gone; a reason string present in English only."""
        table = _tr_table()
        loading = table["ko"]["loading"]
        quoted = loading.rstrip("…")
        self.assertIn(f'"{quoted}"', self.body,
                      f"the v0.26 notes must quote the Korean loading status {quoted!r} verbatim")
        self.assertNotEqual(quoted, loading, "the loading label carries a trailing ellipsis the notes drop")
        for key in ("api_key_rejected", "api_unreachable"):
            missing = [lang for lang in ("en", "ko", "ja", "es") if not table.get(lang, {}).get(key)]
            self.assertEqual(missing, [], f"{key} missing from locales: {missing}")
        self.assertNotEqual(table["ko"]["api_key_rejected"], table["ko"]["api_unreachable"],
                            "a rejected key and a transient failure must not share one sentence")

        kind = _module_def(APP_SOURCE, "api_error_kind")
        kind_src = ast.unparse(kind)
        self.assertIn("if not last_error:\n        return None", kind_src,
                      "'not fetched yet' is not a failure and must not produce a reason")
        self.assertIn("'http:401'", kind_src)
        self.assertIn("'http:403'", kind_src)

        summary = _module_def(APP_SOURCE, "roam_summary")
        summary_src = ast.unparse(summary)
        self.assertIn("return ('status', 'api_key_rejected')", summary_src,
                      "a rejected key must reach its own status line")
        self.assertIn("return ('status', 'api_unreachable' if api_stale else 'loading')", summary_src,
                      "'loading' must survive only while nothing has failed yet")


class PublishedV0261NotesContractTests(unittest.TestCase):
    """The published v0.26.1 section: its bytes are frozen above, and the source must
    still keep every promise it made.

    This is the v0.26.1 release's former ``StagedV0261NotesFormatTests`` with its
    assertions and method names unchanged — only its status moved from staged to
    published when the ``v0.26.1`` tag and GitHub release went out on
    2026-09-21T05:00:16Z (the same promotion the v0.26 class went through a release
    earlier).  Every assertion below was re-run against the v1.0.0 release tree before
    this rename (2026-09-30) and still holds.  The format gate still says what CLAUDE.md
    step 2 says: exactly three top-level bullets, no nesting, at most 450 normalized
    characters, 1-2 Korean sentences per bullet, and none of the forbidden token classes.
    Every checkable claim in it is then tied to the source, one test per bullet.
    Consistent with this module's own stated
    principle ("behavioural gates live elsewhere … this module only ties the prose to
    them"), the per-bullet tests below cite the actual behavioural proof in
    tests/test_companion_motion.py's ``CodexOnboardingSuppressionTests`` rather than
    re-implementing its ``roam_summary_text`` harness here — this module only checks that
    the prose is anchored to a real, named piece of source:

    * "Codex만 설정되어 있고 Claude Code는 설치·로그인 전이면, 이제 필에 "Claude Code
      미설치" 안내 대신 Codex 사용량만 표시됩니다" — the quoted status to
      ``TR["ko"]["onb_install"]`` and to ``roam_summary_text``'s own
      ``claude_onboarding_suppressed`` local, which must gate the suppression on exactly
      the two onboarding status keys and on the Codex segment actually carrying data.
    * "Claude Code를 실제로 쓰다가 토큰이 만료되었거나 조회 중일 때는 예전처럼 그대로
      안내가 뜹니다" — the same local must **not** name any other status key, so
      token_expired/scanning/etc reach the pill exactly as before this release, Codex or
      not.
    * "macOS·Windows 모두 적용되며, 따로 설정할 것은 없습니다" — the Windows half is
      built on the Windows branch and out of scope for this checkout/session (the same
      treatment the v0.25 notes' Windows claims get, in this module's own docstring);
      the macOS half is checked here: the suppression needs no new config/``RUNTIME``
      key.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.visible = _notes_block(text, "**v0.26.1**", "**v0.26**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def test_v0261_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v0.26.1 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v0.26.1 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v0.26.1 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_every_quoted_string_in_the_notes_is_a_real_korean_ui_string(self):
        """Same discriminator as ``PublishedV026NotesContractTests``'s namesake test: every
        quoted string in the v0.26.1 body must be a real ``TR["ko"]`` value (allowing the
        same two intentional variants — a trailing ellipsis dropped, a leading glyph
        dropped), so a quote that drifted from the actual menu/status text is caught even
        if no other test happens to name that particular key."""
        table = _tr_table()["ko"]

        def forms(value):
            out = {value}
            out.add(value.rstrip("…").strip())
            head, _, rest = value.partition(" ")
            if rest and not re.match(r"[0-9A-Za-z가-힣]", head):
                out.add(rest)
                out.add(rest.rstrip("…").strip())
            return {form for form in out if form}

        index = {}
        for key, value in table.items():
            if isinstance(value, str):
                for form in forms(value):
                    index.setdefault(form, []).append(key)

        quoted = re.findall(r'"([^"]+)"', self.body)
        self.assertTrue(
            quoted,
            "the v0.26.1 notes quote no UI string at all — either this test is now "
            "vacuous or the quote disappeared; a human must check which")
        problems = [q for q in quoted if q not in index]
        self.assertEqual(
            problems, [],
            f"the v0.26.1 notes quote a string that matches no TR['ko'] value: {problems!r} "
            f"— the user cannot find this on screen (checked quotes: {quoted!r})")

    def test_v0261_codex_only_users_no_longer_see_the_onboarding_status(self):
        """"이제 필에 "Claude Code 미설치" 안내 대신 Codex 사용량만 표시됩니다": the quoted
        status is ``TR["ko"]["onb_install"]`` verbatim, and ``roam_summary_text``'s own
        ``claude_onboarding_suppressed`` local must gate the suppression on exactly
        ``onb_install``/``onb_login`` and on the Codex segment actually carrying data —
        ``bool(codex_seg) and codex_seg[0] != "status"``, not merely a truthy Codex
        segment (a Codex-side loading/absent status is not "real" data). The flag must
        also be consulted at both use sites: it clears the clickable
        ``state["summary_status"]`` and it is what drops the global status line from the
        provider blocks.

        The actual suppress/don't-suppress behaviour — including the positive case and
        both of its non-overreach cases (a user who does not use Codex; every other
        Claude status shown regardless of Codex) — is proven behaviourally, not here, by
        tests/test_companion_motion.py::CodexOnboardingSuppressionTests
        (``test_codex_ready_suppresses_onb_install``,
        ``test_codex_ready_suppresses_onb_login``,
        ``test_onb_install_still_shows_without_codex``). This test only ties the quoted
        prose to the named local that implements it. Rivals this rules out: the quoted
        status text drifting from the real TR value while the note still reads
        plausibly; the suppression computed but consulted at only one of its two use
        sites (leaving a ghost-clickable or a still-visible line); the condition gated on
        Codex truthiness alone rather than on it carrying real data."""
        table = _tr_table()
        label = table["ko"]["onb_install"]
        self.assertEqual(label, KO_ONB_INSTALL_LABEL,
                         "the v0.26.1 notes quote this onboarding status")
        self.assertIn(f'"{label}"', self.body,
                      f"the v0.26.1 notes must quote the Korean onboarding status {label!r} verbatim")

        run_gui = _module_def(APP_SOURCE, "run_gui")
        text_fn = _nested_function(run_gui, "roam_summary_text")
        src = ast.unparse(text_fn)
        self.assertIn(
            "claude_onboarding_suppressed", src,
            "roam_summary_text must gate the suppression through its own named local")
        self.assertIn(
            "segment[1] in ('onb_install', 'onb_login')", src,
            "the suppression must be scoped to exactly the two onboarding status keys")
        self.assertIn(
            "bool(codex_seg) and (codex_seg[0] != 'status')", src,
            "the suppression must require a real (non-status) Codex segment, not merely "
            "a truthy one")
        self.assertEqual(
            src.count("claude_onboarding_suppressed"), 3,
            "the flag must be computed once and consulted at both of its use sites "
            "(state['summary_status'] and the global-line insert) — a stray or missing "
            "use site is exactly how this fix would half-apply")

    def test_v0261_other_claude_statuses_are_unaffected_by_codex(self):
        """"Claude Code를 실제로 쓰다가 토큰이 만료되었거나 조회 중일 때는 예전처럼 그대로
        안내가 뜹니다": the suppression above must not be widened to any status other
        than the two onboarding keys, so token_expired/scanning/need_admin_key/loading/…
        reach the pill exactly as before this release, whether or not Codex has data.

        Behavioural proof: tests/test_companion_motion.py::CodexOnboardingSuppressionTests
        .test_scanning_shows_regardless_of_ready_codex and
        .test_token_expired_shows_regardless_of_ready_codex, each with a Codex segment
        that is actually ready (the case a narrower suppression condition could still get
        wrong). This test only checks that the condition text itself names no status
        other than the two onboarding keys — the rivals it rules out: a suppression that
        silently grew to swallow "every Claude status once Codex is ready" (the note's
        first sentence would still read true while the second sentence became false)."""
        self.assertRegex(self.body, r"토큰이\s*만료되었거나\s*조회\s*중")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        text_fn = _nested_function(run_gui, "roam_summary_text")
        src = ast.unparse(text_fn)
        match = re.search(r"claude_onboarding_suppressed = (.+?)\n", src)
        self.assertIsNotNone(match, "roam_summary_text must define claude_onboarding_suppressed")
        condition = match.group(1)
        self.assertIn("'onb_install', 'onb_login'", condition)
        for other_status in ("token_expired", "scanning", "need_admin_key", "loading",
                             "api_key_rejected", "api_unreachable"):
            self.assertNotIn(
                repr(other_status), condition,
                f"the suppression condition must not name {other_status!r} — only "
                "onb_install/onb_login may ever be suppressed")

    def test_v0261_applies_to_both_platforms_with_nothing_new_to_configure(self):
        """"macOS·Windows 모두 적용되며, 따로 설정할 것은 없습니다": the Windows half is
        built on the Windows branch, not by this tree — following this module's own
        precedent for the v0.25 notes' Windows claims (see the module docstring's
        "Windows claims" paragraph), no gate in this checkout/session can say whether the
        Windows half holds, so it is out of scope here and is not attempted. This test
        pins the wording and checks only the macOS half: the fix is a local computed
        inside an existing closure, not a new user-facing switch, so it reads no
        ``RUNTIME``/``cfg`` key and needs no new one."""
        self.assertRegex(self.body, r"macOS\s*[·・]\s*Windows\s*모두\s*적용")
        self.assertRegex(self.body, r"따로\s*설정할\s*것은\s*없습니다")
        run_gui = _module_def(APP_SOURCE, "run_gui")
        text_fn = _nested_function(run_gui, "roam_summary_text")
        src = ast.unparse(text_fn)
        match = re.search(r"claude_onboarding_suppressed = (.+?)\n", src)
        self.assertIsNotNone(match, "roam_summary_text must define claude_onboarding_suppressed")
        condition = match.group(1)
        self.assertNotIn("RUNTIME[", condition,
                         "the suppression must not be gated by a new RUNTIME toggle — "
                         "there is nothing for the user to configure")
        self.assertNotIn("cfg[", condition,
                         "the suppression must not be gated by a new config key — there "
                         "is nothing for the user to configure")


class PublishedV100NotesContractTests(unittest.TestCase):
    """The published v1.0.0 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v1.0.0 release's former ``StagedV100NotesFormatTests`` with its method
    names unchanged — its status moved from staged to published when the ``v1.0.0`` tag
    and GitHub release went out on 2026-09-30T05:03:07Z.  One assertion is re-scoped, in
    ``test_v100_windows_console_is_hidden_and_both_platforms_ship_the_version_named``:
    "1.0.0으로 나오며" used to be tied to ``APP_VERSION`` being ``"1.0.0"``, which was the
    claim while the section was staged; now that ``APP_VERSION`` has moved on, the version
    the bullet names is tied to the section's own heading (the release it describes), while
    every packager/updater tie beside it — each still a property of ``APP_VERSION`` — is
    unchanged.  Every other assertion was re-run against the v1.0.1 release tree before this
    rename (2026-09-30) and still holds.  The format gate says what CLAUDE.md step 2 says: exactly three top-level bullets,
    no nesting, at most 450 normalized characters, 1-2 Korean sentences per bullet, and
    none of the forbidden token classes.  Every checkable claim in it is then tied to the
    source, one test per bullet.  The ties are prose ties and deliberately loose about
    *shape* — each is written as a property of the named mechanism, so a helper, a dict
    built key by key or a keyword argument all pass — while the behaviour itself is gated
    in tests/test_token_recovery.py and tests/test_codex_usage.py:

    * "v0.26부터 macOS에서 "토큰 자동 갱신"이 Apple Music·네트워크 볼륨·다운로드 등의 권한
      창을 띄우던 문제를 고쳤습니다. 따로 할 일은 없고, 이미 허용했든 거부했든 그대로 두면
      됩니다" — the quoted label to ``TR["ko"]["menu_auto_recover"]``; "v0.26부터" to the
      oldest published section that names it; the fix to the three things that removed the
      prompts: the CLI's private working directory (``recovery_cli_cwd()``, beneath the
      app's own cache, as the only value that can reach the launchd job's
      ``WorkingDirectory``), the one-shot ``bootstrap`` job (never ``submit``, never kept
      alive), and ``clear_stale_launchd_jobs`` booting out the labels v0.26 used, started
      by ``run_gui`` at launch; "따로 할 일은 없고" to no setting in front of either;
      "허용했든 거부했든 그대로" to the source never running ``tccutil``.
    * "Codex 사용량이 Codex에서 보는 값과 다르게 나올 수 있던 문제를 고쳤습니다. 이제
      Codex가 실제로 쓰는 계정의 사용량이 보입니다" — to ``fetch_codex_usage`` sending a
      ``ChatGPT-Account-Id`` header that can only hold what ``read_codex_auth`` read from
      ``tokens.account_id`` of Codex's own ``auth.json`` (``codex_auth_path``).
    * "Windows에서는 "토큰 자동 갱신" 때 터미널 창이 떴다 사라지던 문제도 고쳤습니다. macOS와
      Windows 모두 1.0.0으로 나오며, 앱의 업데이트 안내에서 받을 수 있습니다" — the window
      to the port's auto-recovery calling the core's ``run_token_refresh``, whose Windows
      spawn ``_win_wmi_create`` always passes a ``Win32_ProcessStartup`` with
      ``ShowWindow`` 0 and never ``CreateFlags``; "1.0.0으로" to ``APP_VERSION`` and to
      both platforms' packagers taking their version from it; "업데이트 안내에서" to
      ``release.sh`` tagging the release from ``APP_VERSION``, to both updaters comparing
      the latest tag against ``APP_VERSION`` (the port's through ``cp.APP_VERSION``), and
      to the comparator every published build carries ranking it above every published
      version.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.text = text
        self.visible = _notes_block(text, "**v1.0.0**", "**v0.26.1**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def _bullet(self, pattern: str) -> str:
        """The one bullet matching pattern — found by what it says, not by its position."""
        matching = [b for b in self.bullets if re.search(pattern, b)]
        self.assertEqual(len(matching), 1,
                         f"expected exactly one v1.0.0 bullet matching {pattern!r}, "
                         f"got {len(matching)}")
        return matching[0]

    def test_v100_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v1.0.0 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v1.0.0 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v1.0.0 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_every_quoted_string_in_the_notes_is_a_real_korean_ui_string(self):
        """Same discriminator as ``PublishedV026NotesContractTests``'s namesake test: every
        quoted string in the v1.0.0 body must be a real ``TR["ko"]`` value (allowing the
        same two intentional variants — a trailing ellipsis dropped, a leading glyph
        dropped), so a quote that drifted from the actual menu text is caught even if no
        other test happens to name that key."""
        table = _tr_table()["ko"]

        def forms(value):
            out = {value}
            out.add(value.rstrip("…").strip())
            head, _, rest = value.partition(" ")
            if rest and not re.match(r"[0-9A-Za-z가-힣]", head):
                out.add(rest)
                out.add(rest.rstrip("…").strip())
            return {form for form in out if form}

        index = {}
        for key, value in table.items():
            if isinstance(value, str):
                for form in forms(value):
                    index.setdefault(form, []).append(key)

        quoted = re.findall(r'"([^"]+)"', self.body)
        self.assertTrue(
            quoted,
            "the v1.0.0 notes quote no UI string at all — either this test is now vacuous "
            "or the quote disappeared; a human must check which")
        problems = [q for q in quoted if q not in index]
        self.assertEqual(
            problems, [],
            f"the v1.0.0 notes quote a string that matches no TR['ko'] value: {problems!r} "
            f"— the user cannot find this on screen (checked quotes: {quoted!r})")

    def test_v100_macos_prompts_are_fixed_with_nothing_left_for_the_user(self):
        """"v0.26부터 macOS에서 "토큰 자동 갱신"이 … 권한 창을 띄우던 문제를 고쳤습니다. 따로
        할 일은 없고, 이미 허용했든 거부했든 그대로 두면 됩니다."

        What removed the prompts, per the 2026-09-30 record in claude_pet.py (the comment
        block above REFRESH_MARGIN_SEC): the CLI no longer starts in ``/`` — it starts in
        ``recovery_cli_cwd()``, a folder beneath the app's own cache — and it runs once per
        attempt, as a ``bootstrap``-ed job that is never kept alive, where v0.26's
        ``submit`` job started it in ``/`` and ran it again after it exited.  A v0.26 job
        orphaned by the update would go on doing that until the next attempt booted it
        out, so ``clear_stale_launchd_jobs`` boots out v0.26's labels when the app starts.
        "따로 할 일은 없고": neither of those waits for a setting.  "허용했든 거부했든 그대로
        두면 됩니다": the fix works by not triggering the reads, not by changing the
        user's answers — nothing in the source runs ``tccutil``.

        Rivals, each of which would leave a sentence false: the label quoted differently
        from the menu; a "since" version that is not where the feature arrived; the CLI's
        folder moved back to ``/`` or the home folder, in ``recovery_cli_cwd`` or anywhere
        between it and ``WorkingDirectory`` (a literal, another call, a caller passing
        something else); ``submit`` back anywhere on the spawn path; ``KeepAlive`` true or a
        relaunch trigger; a cleanup that misses a label v0.26 used or a label a job is
        created under, or that renamed the labels so v0.26's jobs are no longer the ones it
        clears; the cleanup reached only from a menu action, or behind a setting; a
        ``tccutil reset`` "to clear the old answers"."""
        problems: list[str] = []
        bullet = self._bullet(r"권한\s*창")
        table = _tr_table()
        label = table["ko"]["menu_auto_recover"]
        if f'"{label}"' not in bullet:
            problems.append(f"the bullet must quote the menu label {label!r} verbatim")

        # "v0.26부터" — the oldest published section that names the label.
        since = re.search(r"v(\d+\.\d+(?:\.\d+)?)부터", bullet)
        naming = [version for version, body in _changelog_sections(self.text)[1:]
                  if f'"{label}"' in body]
        if not since:
            problems.append("the bullet must say since which version the prompts appeared")
        elif not naming:
            problems.append(f"no published section names {label!r}")
        elif since.group(1) != naming[-1]:
            problems.append(f"the bullet dates the problem from v{since.group(1)}, but the "
                            f"oldest published section naming {label!r} is v{naming[-1]}")

        defs = _module_defs(APP_SOURCE)
        literals = _module_literals(APP_SOURCE)
        undefined = [name for name in ("recovery_cli_cwd", "_recovery_cache_dir",
                                       "_run_refresh_job", "clear_stale_launchd_jobs", "run_gui")
                     if name not in defs]
        if undefined:
            problems.append(f"claude_pet.py must define {undefined} at module level")
            self.fail("\n" + "\n".join(f"- {p}" for p in problems))

        # The private working directory: a folder beneath the app's own cache …
        cache_dirs = _literal_assignments(APP_SOURCE, "RECOVERY_CACHE_DIR")
        if not (len(cache_dirs) == 1 and isinstance(cache_dirs[0], str)
                and re.fullmatch(r"~/Library/Caches/[^/]+(?:/[^/]+)*", cache_dirs[0])):
            problems.append("RECOVERY_CACHE_DIR must be one literal folder under "
                            f"~/Library/Caches, got {cache_dirs!r}")
        if "RECOVERY_CACHE_DIR" not in _names(defs["_recovery_cache_dir"]):
            problems.append("_recovery_cache_dir must be built from RECOVERY_CACHE_DIR")
        returns = [n.value for n in ast.walk(defs["recovery_cli_cwd"]) if isinstance(n, ast.Return)]
        if not returns or not all(r is not None and _calls_to(r, "_recovery_cache_dir")
                                  for r in returns):
            problems.append("every return of recovery_cli_cwd must be built from "
                            "_recovery_cache_dir() — the CLI's folder is the app's own")
        # … and the only value that can reach the launchd job's WorkingDirectory.
        spawn = _reachable(defs, "_run_refresh_job")
        given = [(fn, value) for fn in spawn for value in _values_given(fn, "WorkingDirectory")]
        if not given:
            problems.append("the launchd job never sets WorkingDirectory (launchd would use /)")
        stray = ["<unreadable>" if value is None else f"{fn.name}: {ast.unparse(value)}"
                 for fn, value in given
                 if value is None or not _only_carries(defs, fn, value, "recovery_cli_cwd")]
        if stray:
            problems.append(f"WorkingDirectory can hold something other than recovery_cli_cwd(): {stray}")

        # The one-shot job: bootstrap, never submit, never kept alive, nothing that relaunches.
        whole = _reachable(defs, "_run_refresh_job", "recovery_spawn_argv", "login_spawn_argv",
                           "clear_stale_launchd_jobs")
        if "bootstrap" not in _code_strings(spawn, literals):
            problems.append("the CLI must be handed to launchd with `launchctl bootstrap`")
        if "submit" in _code_strings(whole, literals):
            problems.append("`launchctl submit` must appear nowhere on the spawn path")
        spelled = _code_strings(spawn, literals) | {
            kw.arg for fn in spawn for kw in ast.walk(fn) if isinstance(kw, ast.keyword) and kw.arg}
        if "RunAtLoad" not in spelled:
            problems.append("the launchd job must set RunAtLoad")
        for key, required in (("RunAtLoad", True), ("KeepAlive", False), ("OnDemand", True)):
            wrong = ["<unreadable>" if value is None else ast.unparse(value)
                     for fn in spawn for value in _values_given(fn, key)
                     if not (isinstance(value, ast.Constant) and value.value is required)]
            if wrong:
                problems.append(f"{key} must be literally {required} wherever it is set; got {wrong}")
        triggers = sorted({"StartInterval", "StartCalendarInterval", "WatchPaths",
                           "QueueDirectories", "StartOnMount", "Sockets", "MachServices",
                           "LaunchEvents"} & spelled)
        if triggers:
            problems.append(f"the launchd job carries relaunch triggers {triggers}")

        # The startup cleanup clears what v0.26 left, and every label a job is created under.
        cleared = _code_strings([defs["clear_stale_launchd_jobs"]], literals)
        missing = [lbl for lbl in V026_JOB_LABELS if lbl not in cleared]
        if missing:
            problems.append(f"clear_stale_launchd_jobs does not clear the v0.26 labels {missing}")
        if "bootout" not in _code_strings(_reachable(defs, "clear_stale_launchd_jobs"), literals):
            problems.append("clear_stale_launchd_jobs must boot the jobs out (`launchctl bootout`)")
        job_labels: set[str] = set()
        for fn in defs.values():
            for call in _calls_to(fn, "_run_refresh_job"):
                arg = (call.args[1] if len(call.args) > 1
                       else next((kw.value for kw in call.keywords if kw.arg == "label"), None))
                if isinstance(arg, ast.Name) and literals.get(arg.id):
                    job_labels |= literals[arg.id]
                elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    job_labels.add(arg.value)
                else:
                    job_labels.add("<unreadable label>")
        if not job_labels:
            problems.append("no call of _run_refresh_job names a label")
        uncleared = sorted(job_labels - cleared)
        if uncleared:
            problems.append(f"jobs are created under labels the cleanup never clears: {uncleared}")

        # Started by run_gui itself at launch — its own top-level code or a helper that code
        # calls, not a menu action — and behind no setting.
        run_gui = defs["run_gui"]
        top = [s for s in run_gui.body
               if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        nested = {n.name: n for n in ast.walk(run_gui)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not run_gui}

        def mentions(stmts):
            return [n for s in stmts for n in _own_walk(s)
                    if isinstance(n, ast.Name) and n.id == "clear_stale_launchd_jobs"]

        sites = [(run_gui, n) for n in mentions(top)]      # (where it sits, what to check)
        for call in (n for s in top for n in _own_walk(s)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id in nested):
            inner = mentions(nested[call.func.id].body)
            if inner:
                sites += [(run_gui, call)] + [(nested[call.func.id], n) for n in inner]
        if not sites:
            problems.append("run_gui must start clear_stale_launchd_jobs at launch, from its own "
                            "top-level code or a helper that code calls")
        for root, site in sites:
            gated = [ast.unparse(test) for test in _guards(root, site)
                     if _names(test) & {"RUNTIME", "cfg", "config", "load_config"}]
            if gated:
                problems.append(f"the startup cleanup is behind a setting: {gated}")

        # "허용했든 거부했든 그대로": the user's earlier answers are left alone.
        resets = sorted(s for s in _code_strings([_module_tree(APP_SOURCE)]) if "tccutil" in s)
        if resets:
            problems.append(f"the source runs tccutil ({resets}); the notes say the user's "
                            "earlier answers stay as they are")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v100_codex_asks_for_the_account_codex_itself_uses(self):
        """"Codex 사용량이 Codex에서 보는 값과 다르게 나올 수 있던 문제를 고쳤습니다. 이제
        Codex가 실제로 쓰는 계정의 사용량이 보입니다."

        "Codex가 실제로 쓰는 계정" is the account in Codex's own credentials file: the one
        ``codex_auth_path`` names (``CODEX_HOME`` or the home folder's ``.codex``,
        ``auth.json``), read by ``read_codex_auth`` from ``tokens.account_id``.  The fix is
        that ``fetch_codex_usage`` now sends it as ``ChatGPT-Account-Id``, as Codex CLI does;
        without it the server answered for another account context (the comment block above
        ``codex_auth_path``).  Which requests carry the header, and exactly when, is gated
        in tests/test_codex_usage.py (``CodexAccountHeaderTests``, ``CodexAuthReadTests``);
        this ties the sentence to that mechanism.

        Rivals: no header (v0.26.1); another header name; a header fed from a literal, from
        the token's position, or from somewhere other than read_codex_auth; an account id
        read from outside the ``tokens`` object; credentials read from a file Codex does
        not use."""
        problems: list[str] = []
        bullet = self._bullet(r"Codex")
        for pattern in (r"Codex에서\s*보는\s*값", r"Codex가\s*실제로\s*쓰는\s*계정"):
            if not re.search(pattern, bullet):
                problems.append(f"the bullet no longer says {pattern!r}")
        defs = _module_defs(APP_SOURCE)
        undefined = [name for name in ("codex_auth_path", "read_codex_auth", "fetch_codex_usage")
                     if name not in defs]
        if undefined:
            problems.append(f"claude_pet.py must define {undefined} at module level")
            self.fail("\n" + "\n".join(f"- {p}" for p in problems))

        path_strings = _code_strings([defs["codex_auth_path"]])
        for needed in ("CODEX_HOME", ".codex", "auth.json"):
            if needed not in path_strings:
                problems.append(f"codex_auth_path no longer names {needed!r} — is it still "
                                "the file Codex itself uses?")

        # read_codex_auth takes the account from tokens.account_id; find where it returns it.
        read = defs["read_codex_auth"]
        read_parents = {id(c): p for p in ast.walk(read) for c in ast.iter_child_nodes(p)}

        def bound_values(name):
            out = []
            for n in ast.walk(read):
                if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store):
                    holder = read_parents.get(id(n))
                    out.append(getattr(holder, "value", None))
            return out

        def mentions_tokens(expr, seen=frozenset()):
            """expr is, or is a name only ever bound to, a lookup of "tokens"."""
            if expr is None:
                return False
            if any(isinstance(c, ast.Constant) and c.value == "tokens" for c in ast.walk(expr)):
                return True
            if not isinstance(expr, ast.Name) or expr.id in seen:
                return False
            values = bound_values(expr.id)
            return bool(values) and all(mentions_tokens(v, seen | {expr.id}) for v in values)

        lookups = [n for n in ast.walk(read)
                   if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "get" and n.args
                       and isinstance(n.args[0], ast.Constant) and n.args[0].value == "account_id"
                       and mentions_tokens(n.func.value))
                   or (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                       and n.slice.value == "account_id" and mentions_tokens(n.value))]
        if not lookups:
            problems.append("read_codex_auth must read account_id from the tokens object")
        carriers = {n.id for n in ast.walk(read)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                    and any(lk in list(ast.walk(read_parents.get(id(n))))
                            for lk in lookups)}
        positions = {i for n in ast.walk(read)
                     if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple)
                     for i, e in enumerate(n.value.elts)
                     if (isinstance(e, ast.Name) and e.id in carriers) or e in lookups}
        if len(positions) != 1:
            problems.append("read_codex_auth must return the account id at one fixed "
                            f"position of its result; found {sorted(positions)}")
        else:
            account = positions.pop()
            fetch_path = _reachable(defs, "fetch_codex_usage")
            if not {"read_codex_auth", "codex_auth_path"} <= _names(defs["fetch_codex_usage"]):
                problems.append("fetch_codex_usage must read Codex's auth.json through "
                                "read_codex_auth(codex_auth_path())")
            given = [(fn, value) for fn in fetch_path
                     for value in _values_given(fn, CODEX_ACCOUNT_HEADER, fold_case=True)]
            if not given:
                problems.append(f"no {CODEX_ACCOUNT_HEADER} header on the Codex request")
            stray = ["<unreadable>" if value is None else f"{fn.name}: {ast.unparse(value)}"
                     for fn, value in given
                     if value is None
                     or not _only_carries(defs, fn, value, "read_codex_auth", account)]
            if stray:
                problems.append(f"the {CODEX_ACCOUNT_HEADER} header can hold something other "
                                f"than the account read_codex_auth read: {stray}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v100_windows_console_is_hidden_and_both_platforms_ship_the_version_named(self):
        """"Windows에서는 "토큰 자동 갱신" 때 터미널 창이 떴다 사라지던 문제도 고쳤습니다.
        macOS와 Windows 모두 1.0.0으로 나오며, 앱의 업데이트 안내에서 받을 수 있습니다."

        The window: the port's auto-recovery runs the core's ``run_token_refresh``, whose
        Windows spawn is ``_win_wmi_create``; it must hand WMI a ``Win32_ProcessStartup``
        with ``ShowWindow`` 0 on every call (with or without a working directory) and must
        never pass ``CreateFlags`` — WMI refuses that with ReturnValue 21 and nothing runs
        (the record is in ``_win_wmi_create``'s docstring; the behaviour is gated by
        tests/test_token_recovery.py's ``WindowsHiddenConsoleTests``).  "1.0.0으로
        나오며": the version named is ``APP_VERSION``, which ``setup.py``, ``build_app.sh``
        and ``windows/build_win.py`` all read from claude_pet.py.  "앱의 업데이트
        안내에서": ``release.sh`` tags the release ``v`` + ``APP_VERSION``, both updaters
        compare the latest tag against ``APP_VERSION`` with the core's ``_ver_tuple`` (the
        port passes ``cp.APP_VERSION``), and — what decides it for users already installed
        — the comparator every published build carries (``PUBLISHED_VER_TUPLE``) ranks
        this version above every published one.

        Rivals: the startup information dropped, sent only when a working directory is
        given, or set to a visible ``ShowWindow``; ``CreateFlags`` added "to be safe"; the
        port's recovery spawning some other way; a version in the notes that is not
        ``APP_VERSION``; a packager with its own version literal; a tag not taken from
        ``APP_VERSION``; an updater comparing against something other than the running
        version; a version the installed comparator does not rank above every published
        one (``0.9.0`` is a real example: it reads as older than 0.26.1)."""
        problems: list[str] = []
        bullet = self._bullet(r"터미널\s*창")
        table = _tr_table()
        label = table["ko"]["menu_auto_recover"]
        if not _has_all(bullet, (r"Windows에서는", re.escape(f'"{label}"'), r"터미널\s*창")):
            problems.append("the bullet must say the Windows terminal window during "
                            f'"{label}" is fixed')

        defs = _module_defs(APP_SOURCE)
        literals = _module_literals(APP_SOURCE)
        port = _module_tree(WIN_APP)
        port_spawns = [n for n in ast.walk(port) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Attribute) and n.func.attr == "run_token_refresh"
                       and isinstance(n.func.value, ast.Name) and n.func.value.id == "cp"]
        if not port_spawns:
            problems.append("the port's auto-recovery must run the core's cp.run_token_refresh")
        wmi = defs.get("_win_wmi_create")
        if wmi is None or wmi not in _reachable(defs, "run_token_refresh"):
            problems.append("run_token_refresh must reach _win_wmi_create on Windows")
        else:
            strings = _code_strings([wmi], literals)
            if not any("Win32_ProcessStartup" in s for s in strings):
                problems.append("_win_wmi_create must build a Win32_ProcessStartup")
            if not any(re.search(r"ShowWindow\s*=\s*(?:\[u?int(?:16|32)\]\s*)?0(?![\dxX.])", s)
                       for s in strings):
                problems.append("the startup information must set ShowWindow to 0 (SW_HIDE)")
            if any("CreateFlags" in s for s in strings):
                problems.append("CreateFlags must not be passed: WMI refuses it and nothing spawns")
            skip = _docstring_ids([wmi])
            carriers = [n for n in ast.walk(wmi) if isinstance(n, ast.Constant)
                        and isinstance(n.value, str) and id(n) not in skip
                        and ("ProcessStartupInformation" in n.value
                             or "Win32_ProcessStartup" in n.value)]
            if not any("ProcessStartupInformation" in n.value for n in carriers):
                problems.append("_win_wmi_create must pass the startup information to Create "
                                "(ProcessStartupInformation)")
            conditional = sorted({ast.unparse(test) for n in carriers for test in _guards(wmi, n)})
            if conditional:
                problems.append("the hidden-window startup information must go with every "
                                f"Create, not only when {conditional}")

        # "1.0.0으로 나오며": the version named is the release this (published) section
        # describes — it was APP_VERSION while the section was staged — and every packager
        # takes its version from APP_VERSION.
        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        named = re.search(r"(\d+(?:\.\d+)+)\s*으로\s*나오", bullet)
        own = [v for v, body in _changelog_sections(self.text) if body == self.visible]
        if not named:
            problems.append("the bullet must name the version both platforms ship")
        elif own != [named.group(1)]:
            problems.append(f"the bullet says both platforms ship {named.group(1)}; "
                            f"the section it sits in is {own!r}")
        setup_tree = _module_tree(SETUP)
        setup_version = [n for n in setup_tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in n.targets)]
        setup_reads = _code_strings(setup_version)
        if not (len(setup_version) == 1 and "claude_pet.py" in setup_reads
                and any("APP_VERSION" in s for s in setup_reads)):
            problems.append("setup.py must read APP_VERSION out of claude_pet.py")
        stamped = [v for n in ast.walk(setup_tree) if isinstance(n, ast.Dict)
                   for k, v in zip(n.keys, n.values)
                   if isinstance(k, ast.Constant) and k.value == "CFBundleShortVersionString"]
        if not stamped or not all(isinstance(v, ast.Name) and v.id == "APP_VERSION" for v in stamped):
            problems.append("setup.py must stamp CFBundleShortVersionString with APP_VERSION")
        build_text = BUILD_SCRIPT.read_text(encoding="utf-8")
        if not re.search(r"(?m)^APP_VERSION=\$\(sed [^\n]*APP_VERSION[^\n]*claude_pet\.py", build_text):
            problems.append("build_app.sh must read APP_VERSION out of claude_pet.py")
        if "<key>CFBundleShortVersionString</key><string>${APP_VERSION}</string>" not in build_text:
            problems.append("build_app.sh must stamp CFBundleShortVersionString with APP_VERSION")
        win_version = _module_defs(WIN_BUILD).get("app_version")
        if win_version is None or not ("claude_pet.py" in _code_strings([win_version])
                                       and any("APP_VERSION" in s for s in _code_strings([win_version]))):
            problems.append("windows/build_win.py's app_version must read APP_VERSION out of "
                            "claude_pet.py")

        # "앱의 업데이트 안내에서 받을 수 있습니다": the tag is taken from APP_VERSION …
        release_text = RELEASE_SCRIPT.read_text(encoding="utf-8")
        cur = re.search(r"(?ms)^cur_version\(\)\s*\{(.*?)^\}", release_text)
        if not cur or "APP_VERSION" not in cur.group(1) or "claude_pet.py" not in cur.group(1):
            problems.append("release.sh's cur_version must read APP_VERSION out of claude_pet.py")
        if not re.search(r'TAG="v\$\(cur_version\)"', release_text):
            problems.append('release.sh must publish under TAG="v$(cur_version)"')

        # … both updaters compare the latest tag against the running version …
        def compares(fn, qualifier, running):
            """A comparison of <q>_ver_tuple(<tag>) with <q>_ver_tuple(<running>)."""
            def ver_arg(node):
                if not (isinstance(node, ast.Call) and len(node.args) == 1):
                    return None
                func = node.func
                if qualifier is None and isinstance(func, ast.Name) and func.id == "_ver_tuple":
                    return node.args[0]
                if (qualifier is not None and isinstance(func, ast.Attribute)
                        and func.attr == "_ver_tuple" and isinstance(func.value, ast.Name)
                        and func.value.id == qualifier):
                    return node.args[0]
                return None
            for n in ast.walk(fn):
                if isinstance(n, ast.Compare) and len(n.comparators) == 1:
                    args = [ver_arg(n.left), ver_arg(n.comparators[0])]
                    if None in args:
                        continue
                    if any(ast.unparse(a) == running for a in args) and any(
                            isinstance(a, ast.Name) and a.id != running for a in args):
                        return True
            return False

        if "check_github_update" not in defs or not compares(
                defs["check_github_update"], None, "APP_VERSION"):
            problems.append("check_github_update must compare the latest tag against "
                            "_ver_tuple(APP_VERSION)")
        win_update = _module_defs(WIN_UPDATE).get("check_github_update_win")
        if win_update is None:
            problems.append("windows/win_update.py must define check_github_update_win")
        else:
            params = [a.arg for a in win_update.args.posonlyargs + win_update.args.args]
            running = next((p for p in params if compares(win_update, "cp", p)), None)
            if compares(win_update, "cp", "cp.APP_VERSION"):
                pass                    # compares against the running core's version directly
            elif running is None:
                problems.append("check_github_update_win must compare the latest tag against "
                                "the running version (cp.APP_VERSION, or an argument the port "
                                "fills with it)")
            else:
                slot = params.index(running)
                calls = [n for n in ast.walk(port) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "check_github_update_win"]
                if not calls:
                    problems.append("the port never runs check_github_update_win")
                for call in calls:
                    arg = (call.args[slot] if slot < len(call.args)
                           else next((kw.value for kw in call.keywords if kw.arg == running), None))
                    if arg is None or ast.unparse(arg) != "cp.APP_VERSION":
                        problems.append("the port must hand check_github_update_win cp.APP_VERSION, "
                                        f"got {ast.unparse(arg) if arg is not None else None!r}")
            latest = [n for n in _module_tree(WIN_UPDATE).body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "LATEST_RELEASE_URL"
                              for t in n.targets)]
            if not (len(latest) == 1 and "cp.GITHUB_REPO" in ast.unparse(latest[0])
                    and "/releases/latest" in ast.unparse(latest[0])
                    and "LATEST_RELEASE_URL" in _names(win_update)):
                problems.append("check_github_update_win must read the latest release of the "
                                "core's GITHUB_REPO")

        # … and what installed copies decide with: the comparator every published build
        # carries must rank APP_VERSION above every published version.
        if len(versions) == 1 and isinstance(versions[0], str):
            namespace = {"__builtins__": {"str": str, "int": int, "tuple": tuple}}
            exec(compile(PUBLISHED_VER_TUPLE, "<PUBLISHED_VER_TUPLE>", "exec"), namespace)
            published_ver = namespace["_ver_tuple"]
            published = [version for version, _ in _changelog_sections(self.text)[1:]]
            not_newer = [v for v in published if not published_ver(versions[0]) > published_ver(v)]
            if not published or not_newer:
                problems.append(f"installed copies would not offer {versions[0]}: their "
                                f"comparator does not rank it above {not_newer or 'anything'}")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


class PublishedV101NotesContractTests(unittest.TestCase):
    """The published v1.0.1 section: its bytes are frozen above, and the source must still
    keep every promise it made.

    This is the v1.1.0 release's former ``StagedV101NotesFormatTests`` with its method
    names unchanged — its status moved from staged to published when the ``v1.0.1`` tag
    and GitHub release went out on 2026-09-30T09:45:29Z.  One assertion is re-scoped, in
    ``test_v101_windows_ships_the_same_version``: "같은 1.0.1로" used to be tied to
    ``APP_VERSION`` being ``"1.0.1"`` (and the staged heading being ``APP_VERSION``), which
    was the claim while the section was staged; now that ``APP_VERSION`` has moved on, the
    version the bullet names is tied to the section's own heading (the release it
    describes), while the Windows packager tie beside it — still a property of
    ``APP_VERSION`` — is unchanged.  The heading-equals-``APP_VERSION`` check lives on in
    ``StagedV110NotesFormatTests``.  Every other assertion was re-run against the v1.1.0
    release tree (4c088dc, 2026-10-05) and still holds: none of them is about what the
    server-only change touched.  The format gate says what CLAUDE.md step 2 says: exactly three top-level bullets,
    no nesting, at most 450 normalized characters, 1-2 Korean sentences per bullet, and
    none of the forbidden token classes.  Every checkable claim in it is then tied to the
    source, one test per bullet (see the module docstring for the two hand-checked facts
    behind them).  The v1.0.1 notes quote no UI string, so the quoted-string test the
    earlier classes carry has nothing to check here; ``test_v101_notes_quote_no_ui_string``
    pins that, so a quote added later has to bring its own tie.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.text = text
        self.visible = _notes_block(text, "**v1.0.1**", "**v1.0.0**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def _bullet(self, pattern: str) -> str:
        """The one bullet matching pattern — found by what it says, not by its position."""
        matching = [b for b in self.bullets if re.search(pattern, b)]
        self.assertEqual(len(matching), 1,
                         f"expected exactly one v1.0.1 bullet matching {pattern!r}, "
                         f"got {len(matching)}")
        return matching[0]

    def test_v101_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v1.0.1 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v1.0.1 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v1.0.1 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v101_notes_quote_no_ui_string(self):
        self.assertEqual(re.findall(r'"([^"]+)"', self.body), [],
                         "the v1.0.1 notes now quote a UI string — tie it to TR['ko'] "
                         "the way the earlier classes do")

    def test_v101_apple_silicon_download_and_update_open_on_macos_12(self):
        """"Apple Silicon용 다운로드와 그 자동 업데이트가 macOS 26.3 이상에서만 열리던 문제를
        고쳤습니다. 이제 안내대로 macOS 12 이상에서 열립니다."

        "Apple Silicon용 다운로드와 그 자동 업데이트": the arm64 zip ``release.sh`` builds is
        the updater's first choice on arm64, so the in-app update on Apple Silicon is the
        same artifact as the download.  "macOS 12 이상 / 안내대로": the floor is 12.0 in both
        ``release.sh`` and ``verify_release_artifact.py``, and the READMEs promise macOS 12.
        "고쳤습니다": the arm64 build interpreter defaults to the universal2 one (not pyenv),
        ``build()`` refuses an interpreter above the floor before py2app, and runs the minos
        gate on what it built; ``check_app`` — the upload gate — runs ``check_minos`` before
        delegating.  "26.3": the deployment target ``release.sh`` records for the pyenv
        interpreter it used to default to (and the value the published v1.0.0 arm64 zip's
        Mach-O files carry — checked by hand, see the module docstring).

        Rivals, each of which would leave a sentence false: the updater preferring the
        universal zip on arm64 (then "그 자동 업데이트" was never affected); a floor above
        12 in either tool, or the two disagreeing; ``PY`` still defaulting to pyenv; the
        interpreter check after py2app or absent; ``check_app`` not calling the minos
        check, or calling it after the validator; a number in the notes other than the one
        the tree records."""
        problems: list[str] = []
        bullet = self._bullet(r"Apple\s*Silicon")
        if not _has_all(bullet, (r"자동\s*업데이트", r"macOS\s*26\.3\s*이상에서만",
                                 r"macOS\s*12\s*이상")):
            problems.append("the bullet must say the Apple Silicon download and its update "
                            "opened only on macOS 26.3+ and now open on macOS 12+")

        release_text = RELEASE_SCRIPT.read_text(encoding="utf-8")
        names = _literal_assignments(APP_SOURCE, "UPDATE_ASSET_NAMES")
        zip_line = re.search(r'(?m)^ZIP="([^"]+)"', release_text)
        if not (len(names) == 1 and isinstance(names[0], dict) and names[0].get("arm64")
                and zip_line
                and names[0]["arm64"][0] == Path(zip_line.group(1)).name.lower()):
            problems.append("the updater's first arm64 asset must be the arm64 zip release.sh "
                            "builds (ZIP)")

        floor_sh = re.search(r'(?m)^MIN_MACOS="(\d+)\.(\d+)"', release_text)
        floor_py = _literal_assignments(RELEASE_VERIFIER, "MIN_MACOS")
        promised = re.search(r"macOS\s*(\d+)\s*이상", bullet)
        if not floor_sh or floor_py != [(int(floor_sh.group(1)), int(floor_sh.group(2)))]:
            problems.append(f"release.sh MIN_MACOS and verify_release_artifact.MIN_MACOS must "
                            f"agree; got {floor_sh and floor_sh.groups()!r} vs {floor_py!r}")
        elif not promised or floor_py[0] != (int(promised.group(1)), 0):
            problems.append(f"the notes promise macOS {promised and promised.group(1)}; the "
                            f"gate's floor is {floor_py[0]!r}")
        readme = (REPO / "README.ko.md").read_text(encoding="utf-8")
        if not promised or f"macOS {promised.group(1)} 이상" not in readme:
            problems.append("'안내대로': README.ko.md must promise the same macOS floor")

        upy = re.search(r'(?m)^UPY="\$\{UPY:-([^}]+)\}"', release_text)
        py = re.search(r'(?m)^PY="([^"]*)"', release_text)
        if not upy or ".pyenv" in upy.group(1) or not py or py.group(1) != "${PY:-$UPY}":
            problems.append(f"release.sh's PY must default to the universal2 UPY; got "
                            f"{py and py.group(0)!r}")
        build = re.search(r"(?ms)^build\(\)\s*\{(.*?)^\}", release_text)
        body = build.group(1) if build else ""
        check_at = body.find('check_build_python "$PY"')
        py2app_at = body.find("setup.py py2app")
        if check_at == -1 or py2app_at == -1 or check_at > py2app_at:
            problems.append("build() must run check_build_python \"$PY\" before py2app")
        if "verify_release_artifact.py minos" not in body:
            problems.append("build() must run the minos gate on the bundle it built")
        check_fn = re.search(r"(?ms)^check_build_python\(\)\s*\{(.*?)^\}", release_text)
        if not check_fn or "MACOSX_DEPLOYMENT_TARGET" not in check_fn.group(1) \
                or "MIN_MACOS" not in check_fn.group(1):
            problems.append("check_build_python must compare MACOSX_DEPLOYMENT_TARGET with "
                            "MIN_MACOS")

        check_app = _module_def(RELEASE_VERIFIER, "check_app")
        minos_calls = _calls_to(check_app, "check_minos")
        validate_calls = _method_calls(check_app, "validate_update_app")
        if not minos_calls or not validate_calls or \
                min(c.lineno for c in minos_calls) > min(c.lineno for c in validate_calls):
            problems.append("check_app must call check_minos before validate_update_app")

        # "26.3": the number the tree records for the interpreter it stopped using.
        number = re.search(r"macOS\s*(\d+\.\d+)\s*이상에서만", bullet)
        if not number or not re.search(
                rf"pyenv[^\n]*\n?[^\n]*\({re.escape(number.group(1))}\)", release_text):
            problems.append(f"the notes say macOS {number and number.group(1)}; release.sh "
                            "must record that as the pyenv interpreter's deployment target")

        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v101_users_who_could_not_open_reinstall_others_just_update(self):
        """"26.3보다 낮은 macOS에서 앱이 열리지 않았다면 이 버전을 다시 내려받아 설치하세요.
        앱이 잘 열리던 분은 앱의 업데이트 안내로 받으면 되고, 따로 할 일은 없습니다."

        The 26.3 here must be the first bullet's.  "업데이트 안내로 받으면": ``release.sh``
        tags ``v`` + ``APP_VERSION`` and the comparator every published build carries ranks
        ``APP_VERSION`` above every published version, so installed copies offer it.  (A
        copy that cannot open cannot run its updater — hence "다시 내려받아".)

        Rivals: two different thresholds in the notes; a version the installed comparator
        does not rank above every published one; a tag not taken from ``APP_VERSION``."""
        problems: list[str] = []
        bullet = self._bullet(r"다시\s*내려받")
        first = self._bullet(r"Apple\s*Silicon")
        here = re.search(r"(\d+\.\d+)\s*보다\s*낮은\s*macOS", bullet)
        there = re.search(r"macOS\s*(\d+\.\d+)\s*이상에서만", first)
        if not here or not there or here.group(1) != there.group(1):
            problems.append("the reinstall threshold must be the same version the first "
                            "bullet names")
        if not _has_all(bullet, (r"업데이트\s*안내", r"따로\s*할\s*일은\s*없")):
            problems.append("the bullet must say working copies just take the in-app update")

        release_text = RELEASE_SCRIPT.read_text(encoding="utf-8")
        if not re.search(r'TAG="v\$\(cur_version\)"', release_text):
            problems.append('release.sh must publish under TAG="v$(cur_version)"')
        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if len(versions) == 1 and isinstance(versions[0], str):
            namespace = {"__builtins__": {"str": str, "int": int, "tuple": tuple}}
            exec(compile(PUBLISHED_VER_TUPLE, "<PUBLISHED_VER_TUPLE>", "exec"), namespace)
            published_ver = namespace["_ver_tuple"]
            published = [version for version, _ in _changelog_sections(self.text)[1:]]
            not_newer = [v for v in published if not published_ver(versions[0]) > published_ver(v)]
            if not published or not_newer:
                problems.append(f"installed copies would not offer {versions[0]}: their "
                                f"comparator does not rank it above {not_newer or 'anything'}")
        else:
            problems.append(f"APP_VERSION must be one literal string, got {versions!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v101_windows_ships_the_same_version(self):
        """"Windows도 같은 1.0.1로 나오지만 기능은 달라진 것이 없습니다."

        "같은 1.0.1로": the version named is the section's own heading (it was
        ``APP_VERSION`` while staged — see the class docstring), and ``windows/build_win.py``'s
        ``app_version`` reads ``APP_VERSION`` out of claude_pet.py, as the macOS packagers do.  "기능은
        달라진 것이 없습니다" is a statement about a diff, which no static tie can make; it
        was checked by hand (module docstring).

        Rivals: a version in the notes that is not the section's own; the Windows packager
        carrying its own version literal."""
        problems: list[str] = []
        bullet = self._bullet(r"Windows")
        named = re.search(r"(\d+(?:\.\d+)+)\s*로\s*나오", bullet)
        # "같은 1.0.1로": the version named is the release this (published) section
        # describes — it was APP_VERSION while the section was staged.
        own = [v for v, body in _changelog_sections(self.text) if body == self.visible]
        if not named or own != [named.group(1)]:
            problems.append(f"the bullet names {named and named.group(1)!r}; the section it "
                            f"sits in is {own!r}")
        win_version = _module_defs(WIN_BUILD).get("app_version")
        if win_version is None or not ("claude_pet.py" in _code_strings([win_version])
                                       and any("APP_VERSION" in s
                                               for s in _code_strings([win_version]))):
            problems.append("windows/build_win.py's app_version must read APP_VERSION out of "
                            "claude_pet.py")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


# ── Helpers for the v1.1.0 ties ──────────────────────────────────────────────────────────


def _tr_keys_called(node: ast.AST) -> list[str]:
    """Every literal key handed to ``t("key")`` / ``cp.t("key")`` anywhere inside node."""
    out = []
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)
                and ((isinstance(n.func, ast.Name) and n.func.id == "t")
                     or (isinstance(n.func, ast.Attribute) and n.func.attr == "t"))):
            out.append(n.args[0].value)
    return out


def _dict_display_keys(path: Path, name: str) -> set[str]:
    """The literal keys of the module-level ``name = {…}`` display, whose values need not be
    literals (``RUNTIME`` calls ``os.environ``; ``SUMMARY_COLORS`` names colour constants)."""
    node = _module_assignment(path, name)
    if not isinstance(node.value, ast.Dict):
        raise AssertionError(f"{name} must stay a dict display")
    return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}


def _runtime_default_keys(path: Path) -> set[str]:
    return _dict_display_keys(path, "RUNTIME")


def _settings_builders(tree: ast.AST) -> list[ast.AST]:
    """Every function that builds a ``section(t("s_sec_…"), "show_…", …)`` row — the
    settings panel (macOS ``open_settings``, the port's settings dialog)."""
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in _own_walk(fn):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "section" and len(n.args) >= 2):
                found.append(fn)
                break
    return found


def _section_pairs(fn: ast.AST) -> set[tuple[str, str]]:
    """(TR key of the title, show key) for every ``section(...)`` call in fn."""
    pairs = set()
    for n in _own_walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "section"
                and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)):
            keys = _tr_keys_called(n.args[0])
            if len(keys) == 1:
                pairs.add((keys[0], n.args[1].value))
    return pairs


class StagedV110NotesFormatTests(unittest.TestCase):
    """The unpublished v1.1.0 section, held to CLAUDE.md's release-note format rule and to
    the source it describes.

    The section is staged text until the tag is pushed, so correcting it is ordinary work;
    the format gate only says what CLAUDE.md step 2 says: exactly three top-level bullets,
    no nesting, at most 450 normalized characters, 1-2 Korean sentences per bullet, and
    none of the forbidden token classes.  Every checkable claim in it is then tied to the
    source, one test per claim (see the module docstring for the list).  The v1.1.0 notes
    quote no UI string, so ``test_v110_notes_quote_no_ui_string`` pins that, and a quote
    added later has to bring its own tie.

    The ties are deliberately loose about *shape* — each is a property of the named
    mechanism — while the behaviour is gated in tests/test_server_only_usage.py,
    tests/test_codex_usage.py and windows/tests/test_win_server_only_usage.py.
    """

    def setUp(self):
        text = RELEASE_NOTES.read_text(encoding="utf-8")
        self.text = text
        self.visible = _notes_block(text, "**v1.1.0**", "**v1.0.1**")
        self.top_level, self.nested, self.bullets = _bullet_shape(self.visible)
        self.body = "\n".join(self.bullets)

    def _bullet(self, pattern: str) -> str:
        """The one bullet matching pattern — found by what it says, not by its position."""
        matching = [b for b in self.bullets if re.search(pattern, b)]
        self.assertEqual(len(matching), 1,
                         f"expected exactly one v1.1.0 bullet matching {pattern!r}, "
                         f"got {len(matching)}")
        return matching[0]

    def _sentence(self, pattern: str) -> str:
        """The one sentence (in any bullet) matching pattern."""
        matching = [s for b in self.bullets for s in _sentences(b) if re.search(pattern, s)]
        self.assertEqual(len(matching), 1,
                         f"expected exactly one v1.1.0 sentence matching {pattern!r}, "
                         f"got {len(matching)}")
        return matching[0]

    def test_v110_notes_follow_the_three_bullet_450_character_format(self):
        problems: list[str] = []
        if len(self.top_level) != 3:
            problems.append(f"v1.1.0 must have exactly 3 top-level bullets, got {len(self.top_level)}")
        if self.nested:
            problems.append("v1.1.0 must not contain nested bullets")
        normalized_body = " ".join(self.visible.split())
        if len(normalized_body) > 450:
            problems.append(f"v1.1.0 Korean body is {len(normalized_body)} Unicode characters; max is 450")
        for index, bullet in enumerate(self.bullets, 1):
            if not re.search(r"[가-힣]", bullet):
                problems.append(f"bullet {index} must be Korean")
            count = len(_sentences(bullet))
            if not 1 <= count <= 2:
                problems.append(f"bullet {index} has {count} sentences; CLAUDE.md allows 1-2")
        prose_for_forbidden_scan = self.body.replace("`", "")
        for label, pattern in FORBIDDEN_NOTE_PATTERNS.items():
            match = re.search(pattern, prose_for_forbidden_scan, re.I)
            if match:
                problems.append(f"remove {label}: {match.group(0)!r}")
        # The only number a v1.1.0 bullet may carry is the version (commit 4c088dc: "숫자는
        # 버전뿐") — anything else would need a §5 record behind it.
        numbers = set(re.findall(r"\d+(?:\.\d+)*", self.body))
        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if numbers - set(versions):
            problems.append(f"the notes carry numbers other than the version: "
                            f"{sorted(numbers - set(versions))!r}")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v110_notes_quote_no_ui_string(self):
        self.assertEqual(re.findall(r'"([^"]+)"', self.body), [],
                         "the v1.1.0 notes now quote a UI string — tie it to TR['ko'] "
                         "the way the earlier classes do")

    def test_v110_heading_and_version_are_the_bump(self):
        """The staged heading is the version the release commit bumps to.

        Rivals: a heading left at 1.0.1 or written as 1.1; ``APP_VERSION`` not bumped, or
        bumped to something the heading does not say."""
        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        heading = _changelog_sections(self.text)[0][0]
        self.assertEqual(versions, [heading],
                         f"the staged heading is v{heading}; APP_VERSION is {versions!r}")

    def test_v110_pill_shows_only_server_values_and_calibration_is_gone(self):
        """"필에는 이제 서버가 알려 준 사용량만 표시합니다. 로그로 계산한 추정치(≈)와 한도
        보정 설정은 없어졌고, 한도를 보정해 둔 분도 따로 할 일은 없습니다."

        "서버가 알려 준 사용량만": the pill's Claude segment (``roam_summary``) never reads
        the log snapshot it is handed (``stats``) and has no ``estimate`` segment; the
        Codex segment (``codex_summary_segment``) is built from the server rows or the API
        cost only.  "추정치(≈)": ``SUMMARY_APPROX`` is gone, no code string carries ``≈``,
        and ``SUMMARY_COLORS`` has no ``estimate`` colour.  "한도 보정 설정은 없어졌고": the
        three limit keys (and the model keyword / weekly reset settings that fed the
        estimate) are gone from the ``RUNTIME`` defaults; no ``CLAUDE_PET_*_LIMIT``
        environment override survives; no ``TR`` key for the limit/calibration UI survives
        in any locale; the advanced-limits window is gone.  "따로 할 일은 없습니다":
        ``apply_config`` reads only ``_RUNTIME_CONFIG_KEYS``, which names none of the old
        keys, so an old ``~/.claude_pet.json`` that still carries them is simply not read.

        Rivals: ``roam_summary`` falling back to ``stats`` when there are no server rows
        (the pre-1.1.0 estimate path); the ``≈`` prefix left in; a limit key left in
        ``RUNTIME`` or re-read from the config file (then a calibrated user's old value
        would still act); the calibration fields left in the panel."""
        problems: list[str] = []
        bullet = self._bullet(r"서버가\s*알려\s*준\s*사용량만")
        if not _has_all(bullet, (r"추정치", r"≈", r"한도\s*보정\s*설정은\s*없어", r"따로\s*할\s*일은\s*없")):
            problems.append("the bullet must say the estimate (≈) and the limit calibration are "
                            "gone and calibrated users have nothing to do")

        defs = _module_defs(APP_SOURCE)
        literals = _module_literals(APP_SOURCE)
        summary = defs.get("roam_summary")
        if summary is None:
            problems.append("claude_pet.py must define roam_summary")
        else:
            params = {a.arg for a in summary.args.args + summary.args.kwonlyargs}
            reads = {n.id for n in ast.walk(summary) if isinstance(n, ast.Name)
                     and isinstance(n.ctx, ast.Load)}
            if "stats" in params and "stats" in reads:
                problems.append("roam_summary must not read the log snapshot (stats)")
            if "estimate" in _code_strings([summary], literals):
                problems.append("roam_summary must not produce an estimate segment")
        codex_seg = defs.get("codex_summary_segment")
        if codex_seg is None or not (_calls_to(codex_seg, "roam_summary_codex")
                                     and _calls_to(codex_seg, "roam_summary_codex_cost")):
            problems.append("the Codex segment must be built only from server rows "
                            "(roam_summary_codex) or the API cost (roam_summary_codex_cost)")
        tree = _module_tree(APP_SOURCE)
        names = {t.id for n in tree.body if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Name)}
        if "SUMMARY_APPROX" in names:
            problems.append("SUMMARY_APPROX must be gone")
        code = _code_strings([tree])
        if any("≈" in s for s in code):
            problems.append("no code string may carry ≈ any more")
        colours = _dict_display_keys(APP_SOURCE, "SUMMARY_COLORS")
        if "exact" not in colours or "estimate" in colours:
            problems.append(f"SUMMARY_COLORS must keep exact and have no estimate colour; "
                            f"got {sorted(colours)!r}")

        old_keys = {"session_limit", "weekly_limit", "opus_limit", "model_keyword",
                    "weekly_reset_day", "weekly_reset_hour"}
        left = old_keys & _runtime_default_keys(APP_SOURCE)
        if left:
            problems.append(f"RUNTIME still defaults the removed settings {sorted(left)!r}")
        envs = sorted(s for s in code if re.fullmatch(r"CLAUDE_PET_\w*LIMIT\w*", s))
        if envs:
            problems.append(f"limit environment overrides survive: {envs!r}")
        table = _tr_table()
        ui = sorted({k for lang in table.values() for k in lang
                     if re.match(r"s_(?:limit|calib|err_calib|err_limit|model_kw|weekly_reset|rolling7)", k)})
        if ui:
            problems.append(f"the limit/calibration UI strings survive: {ui!r}")
        nested = {n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        gone = sorted(nested & {"open_advanced_limits", "close_advanced",
                                "prepare_settings_config", "_calibration_percent_error"})
        if gone:
            problems.append(f"the calibration path survives: {gone!r}")

        keys = _literal_assignments(APP_SOURCE, "_RUNTIME_CONFIG_KEYS")
        if len(keys) != 1 or not isinstance(keys[0], tuple):
            problems.append("_RUNTIME_CONFIG_KEYS must be one literal tuple")
        elif old_keys & set(keys[0]):
            problems.append(f"apply_config would still read {sorted(old_keys & set(keys[0]))!r}")
        apply = defs.get("apply_config")
        loops = [n for n in ast.walk(apply) if isinstance(n, ast.For)] if apply else []
        if not apply or not any(isinstance(l.iter, ast.Name) and l.iter.id == "_RUNTIME_CONFIG_KEYS"
                                for l in loops):
            problems.append("apply_config must copy only _RUNTIME_CONFIG_KEYS into RUNTIME")
        elif any(isinstance(n, ast.Constant) and n.value in old_keys for n in ast.walk(apply)):
            problems.append("apply_config must not name a removed key")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v110_settings_have_a_claude_and_a_codex_section_on_both_platforms(self):
        """"설정 창이 Claude Code와 Codex 구역으로 나뉘어, 제공자마다 필 표시 여부, 볼 게이지,
        구독과 API 비용 중 무엇을 볼지 고릅니다(Codex 비용은 OpenAI Admin 키)."

        On macOS (``open_settings``) and in the port's settings dialog alike: two
        ``section`` rows titled ``s_sec_claude`` ("Claude Code") and ``s_sec_codex``
        ("Codex"), each carrying its show checkbox (``show_claude`` / ``show_codex``); a
        gauge list (``s_gauges``) per section; a sub/API popup per section
        (``s_mode_sub``/``s_mode_api``, ``s_codex_mode_sub``/``s_codex_mode_api``); an
        OpenAI Admin key field (``s_openai_key``).  The ``RUNTIME`` defaults carry the keys
        those widgets edit.  "Codex 비용은 OpenAI Admin 키": ``fetch_codex_cost`` reads
        ``RUNTIME["openai_admin_key"]`` and queries OpenAI's organization costs endpoint.

        Rivals: one shared section; a section without its own show checkbox or gauge list;
        Codex with no sub/API choice; Codex cost read with the Anthropic Admin key; the
        port's dialog left at the old layout."""
        problems: list[str] = []
        bullet = self._bullet(r"구역")
        if not _has_all(bullet, (r"Claude\s*Code와\s*Codex\s*구역", r"필\s*표시", r"게이지",
                                 r"구독과\s*API\s*비용", r"OpenAI\s*Admin\s*키")):
            problems.append("the bullet must name the two sections, the three choices and the "
                            "OpenAI Admin key")
        table = _tr_table()
        if (table["ko"].get("s_sec_claude"), table["ko"].get("s_sec_codex")) != ("Claude Code", "Codex"):
            problems.append("TR['ko'] must title the sections 'Claude Code' and 'Codex'")
        if "OpenAI Admin" not in table["ko"].get("s_codex_mode_api", ""):
            problems.append("the Codex API choice must say OpenAI Admin")

        needed_pairs = {("s_sec_claude", "show_claude"), ("s_sec_codex", "show_codex")}
        needed_keys = ("s_mode_sub", "s_mode_api", "s_codex_mode_sub", "s_codex_mode_api",
                       "s_openai_key", "s_show_in_pill")
        for path in (APP_SOURCE, WIN_APP):
            builders = _settings_builders(_module_tree(path))
            fits = [fn for fn in builders if needed_pairs <= _section_pairs(fn)]
            if len(fits) != 1:
                problems.append(f"{path.name}: expected one settings builder with both "
                                f"sections, got {len(fits)}")
                continue
            keys = _tr_keys_called(fits[0])
            missing = [k for k in needed_keys if k not in keys]
            if missing:
                problems.append(f"{path.name}: the settings panel lacks {missing!r}")
            if keys.count("s_gauges") < 2:
                problems.append(f"{path.name}: each section must carry its own gauge list")

        defaults = _runtime_default_keys(APP_SOURCE)
        missing = sorted({"mode", "show_claude", "claude_gauges", "show_codex", "codex_mode",
                          "codex_gauges", "openai_admin_key"} - defaults)
        if missing:
            problems.append(f"RUNTIME lacks defaults for {missing!r}")

        cost = _module_defs(APP_SOURCE).get("fetch_codex_cost")
        url = _literal_assignments(APP_SOURCE, "CODEX_COST_URL")
        if cost is None or "openai_admin_key" not in _code_strings([cost]):
            problems.append("fetch_codex_cost must read RUNTIME['openai_admin_key']")
        elif "admin_key" in _code_strings([cost]):
            problems.append("fetch_codex_cost must not read the Anthropic admin_key")
        if url != ["https://api.openai.com/v1/organization/costs"] or (
                cost is not None and "CODEX_COST_URL" not in _names(cost)):
            problems.append("fetch_codex_cost must query OpenAI's organization costs endpoint")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v110_codex_menu_sentence_names_who_actually_sees_the_items(self):
        """"Codex를 켰는데 설치나 로그인이 안 되어 있으면 우클릭 메뉴에 Codex 설치·로그인
        항목이 나옵니다." (the wording at 4c088dc)

        The wiring: the refresh worker (macOS and the port) sets ``codex_onboard`` from
        ``compute_codex_onboard_state(provider_shown(…, "codex"), codex_mode, has_token,
        cli_present, codex_home_exists())``, and the right-click menu turns ``"install"``
        into ``menu_install_codex`` → ``installCodex:`` and ``"login"`` into
        ``menu_login_codex`` → ``loginCodex:``.

        Who sees it is decided by ``compute_codex_onboard_state``, a pure function this
        test evaluates from its source text (as the v1.0.0 tie evaluates
        ``PUBLISHED_VER_TUPLE``): the sentence may promise the items only where that
        function returns a state.  Two cases are read off it: (a) Codex shown in
        subscription mode, no token, **no CLI and no Codex home** — a Codex user who has
        never installed it; (b) Codex shown in **API mode** without a token.  If the
        function returns ``None`` in (a), the sentence must restrict the items to a machine
        where Codex is installed or its folder exists; if ``None`` in (b), it must restrict
        them to subscription.  Either restriction becomes unnecessary — and this test stops
        asking for it — the moment the source starts showing the item in that case.

        Rivals: the sentence promising an install item to every user who has Codex turned on
        (false at 4c088dc for (a)); promising it in API mode (false for (b)); the menu
        mapping the states to the wrong actions; the port computing the state some other
        way."""
        problems: list[str] = []
        sentence = self._sentence(r"설치\s*·\s*로그인\s*항목")
        if not _has_all(sentence, (r"우클릭\s*메뉴", r"Codex\s*설치\s*·\s*로그인\s*항목")):
            problems.append("the sentence must name the right-click Codex install/login items")

        fn = _module_def(APP_SOURCE, "compute_codex_onboard_state")
        source = ast.get_source_segment(APP_SOURCE.read_text(encoding="utf-8"), fn)
        free = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} - {
            a.arg for a in fn.args.args}
        if free:
            problems.append(f"compute_codex_onboard_state must stay pure; it reads {sorted(free)!r}")
        else:
            namespace = {"__builtins__": {}}
            exec(compile(source, "<compute_codex_onboard_state>", "exec"), namespace)
            state = namespace["compute_codex_onboard_state"]
            if (state(True, "sub", False, True, True), state(True, "sub", False, False, True),
                    state(True, "sub", True, True, True), state(False, "sub", False, True, True)) \
                    != ("login", "install", None, None):
                problems.append("compute_codex_onboard_state must give login with the CLI, "
                                "install with only the Codex home, nothing with a token or "
                                "with Codex hidden")
            never_installed = state(True, "sub", False, False, False)
            api_mode = state(True, "api", False, True, True)
            presence = (r"(?:설치(?:돼|되어)\s*있|폴더가?\s*있|흔적|써\s*(?:온|본|왔|봤)|"
                        r"쓰던|쓰고\s*있|사용해\s*(?:온|본))")
            if never_installed is None and not re.search(presence, sentence):
                problems.append(
                    "the sentence promises the items to anyone with Codex on who has not "
                    "installed it, but compute_codex_onboard_state gives None without the "
                    "Codex CLI or the Codex home — say the item appears only where Codex is "
                    f"installed or its folder exists; sentence: {sentence!r}")
            if api_mode is None and not re.search(r"구독", sentence):
                problems.append(
                    "compute_codex_onboard_state gives None in Codex API mode — the sentence "
                    f"must restrict the items to subscription; sentence: {sentence!r}")

        for path, qual in ((APP_SOURCE, None), (WIN_APP, "cp")):
            calls = [n for n in ast.walk(_module_tree(path)) if isinstance(n, ast.Call)
                     and ((qual is None and isinstance(n.func, ast.Name)
                           and n.func.id == "compute_codex_onboard_state")
                          or (qual and isinstance(n.func, ast.Attribute)
                              and n.func.attr == "compute_codex_onboard_state"
                              and isinstance(n.func.value, ast.Name) and n.func.value.id == qual))]
            if len(calls) != 1:
                problems.append(f"{path.name}: expected one compute_codex_onboard_state call, "
                                f"got {len(calls)}")
                continue
            text = ast.unparse(calls[0])
            if not ("provider_shown" in text and "'codex'" in text and "codex_mode" in text
                    and "codex_home_exists()" in text and "read_codex_token" in text):
                problems.append(f"{path.name}: the state must come from provider_shown('codex'), "
                                f"codex_mode, the token and codex_home_exists(); got {text}")
        mac_menu = [ast.unparse(n) for n in ast.walk(_module_tree(APP_SOURCE))
                    if isinstance(n, ast.IfExp)
                    and {"menu_install_codex", "menu_login_codex"} <= set(_tr_keys_called(n))]
        if not any("'installCodex:'" in m and "'loginCodex:'" in m
                   and m.index("menu_install_codex") < m.index("'installCodex:'")
                   < m.index("menu_login_codex") < m.index("'loginCodex:'")
                   and "== 'install'" in m for m in mac_menu):
            problems.append("the macOS menu must map 'install' to menu_install_codex/installCodex: "
                            "and otherwise menu_login_codex/loginCodex:")
        win_menu = [ast.unparse(n) for n in ast.walk(_module_tree(WIN_APP))
                    if isinstance(n, ast.IfExp)
                    and {"menu_install_codex", "menu_login_codex"} <= set(_tr_keys_called(n))]
        if not any("_install_codex" in m and "_login_codex" in m and "== 'install'" in m
                   for m in win_menu):
            problems.append("the port's menu must map 'install' to its Codex install item and "
                            "otherwise to its login item")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))

    def test_v110_spikes_cover_codex_and_wait_for_a_learned_limit(self):
        """"급증 알림이 Codex 사용에도 울리고, 기준을 서버 값에서 익히기 때문에 실행 직후에는
        기준을 익힐 때까지 알림이 없습니다. Windows도 같은 1.1.0으로 같은 기능을 받습니다."

        "Codex 사용에도": the refresh worker on both platforms merges ``codex_spikes`` into
        the spikes it stores, and ``provider_spiking`` reads the two Codex lanes.  "기준을
        서버 값에서 익히기": the worker calls ``learn_server_limits`` with the server rows
        (``fetch_exact_usage`` / ``fetch_codex_usage``), and ``learn_lane`` — the only
        writer of a learned limit — is called from nowhere else.  "익힐 때까지 알림이
        없습니다": ``is_spike`` returns False when the limit is missing or zero, and both
        spike functions take the limit from the learned table.  "실행 직후에는":
        ``LEARNED_LIMITS`` starts as an empty literal, is not a ``RUNTIME`` default nor a
        config key, and no function that touches the config file names it — so every
        launch starts unlearned.  "Windows도 같은 1.1.0으로": the staged heading is
        ``APP_VERSION`` and ``windows/build_win.py`` reads it.

        Rivals: Codex lanes missing from ``provider_spiking`` or never computed; a default
        limit restored (the old 8M/60M/15M guesses), which would alert before anything is
        learned; learned limits persisted to the config (then "실행 직후" would be false and
        removed limit keys could come back); the port not running the same learning."""
        problems: list[str] = []
        sentence = self._sentence(r"급증\s*알림")
        if not _has_all(sentence, (r"Codex\s*사용에도", r"서버\s*값에서\s*익히",
                                   r"실행\s*직후", r"알림이\s*없")):
            problems.append("the sentence must say spikes cover Codex and wait for a limit "
                            "learned from server values")
        defs = _module_defs(APP_SOURCE)
        lanes = _literal_assignments(APP_SOURCE, "_PROVIDER_LANES")
        if not lanes or set(lanes[0].get("codex", ())) != {"codex_session", "codex_weekly"}:
            problems.append("provider_spiking must read the codex_session and codex_weekly lanes")
        spike_fn = defs.get("is_spike")
        guard = spike_fn is not None and any(
            isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
            and isinstance(n.test.op, ast.Not)
            and len(n.body) == 1 and isinstance(n.body[0], ast.Return)
            and isinstance(n.body[0].value, ast.Constant) and n.body[0].value.value is False
            for n in spike_fn.body)
        if not guard:
            problems.append("is_spike must return False before it judges when there is no limit")
        for name in ("claude_spikes", "codex_spikes"):
            fn = defs.get(name)
            text = ast.unparse(fn) if fn else ""
            if "LEARNED_LIMITS if learned is None else learned" not in text \
                    or "learned.get(" not in text:
                problems.append(f"{name} must take its limits from the learned table")
        learned = _literal_assignments(APP_SOURCE, "LEARNED_LIMITS")
        if learned != [{}]:
            problems.append(f"LEARNED_LIMITS must start as an empty dict, got {learned!r}")
        if "LEARNED_LIMITS" in _runtime_default_keys(APP_SOURCE):
            problems.append("LEARNED_LIMITS must not be a RUNTIME default")
        config_fns = [fn for fn in defs.values() if "CONFIG_PATH" in _names(fn)]
        if not config_fns:
            problems.append("no function touches CONFIG_PATH — the persistence check is vacuous")
        persisted = sorted(fn.name for fn in config_fns if "LEARNED_LIMITS" in _names(fn))
        if persisted:
            problems.append(f"learned limits must not touch the config file: {persisted!r}")
        writers = sorted(fn.name for fn in defs.values()
                         if _calls_to(fn, "learn_lane") and fn.name != "learn_server_limits")
        if writers:
            problems.append(f"learn_lane must be called only from learn_server_limits: {writers!r}")

        for path, qual in ((APP_SOURCE, None), (WIN_APP, "cp")):
            def called(node, name):
                return [n for n in ast.walk(node) if isinstance(n, ast.Call)
                        and ((qual is None and isinstance(n.func, ast.Name) and n.func.id == name)
                             or (qual and isinstance(n.func, ast.Attribute) and n.func.attr == name
                                 and isinstance(n.func.value, ast.Name) and n.func.value.id == qual))]
            workers = [fn for fn in ast.walk(_module_tree(path))
                       if isinstance(fn, ast.FunctionDef)
                       and called(fn, "learn_server_limits") and called(fn, "codex_spikes")
                       and called(fn, "fetch_exact_usage") and called(fn, "fetch_codex_usage")]
            worker = min(workers, key=lambda f: f.end_lineno - f.lineno) if workers else None
            if worker is None:
                problems.append(f"{path.name}: no refresh worker both learns from the server "
                                "and computes Codex spikes")
                continue
            learn = called(worker, "learn_server_limits")[0]
            first_two = [ast.unparse(a) for a in learn.args[:2]]
            bound = {}
            for n in ast.walk(worker):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            bound.setdefault(t.id, []).append(ast.unparse(n.value))
            if len(first_two) != 2 or [bound.get(v) for v in first_two] != [
                    [f"{qual + '.' if qual else ''}fetch_exact_usage()"],
                    [f"{qual + '.' if qual else ''}fetch_codex_usage()"]]:
                problems.append(f"{path.name}: learn_server_limits must learn from the server "
                                f"rows only; got {first_two!r} bound to "
                                f"{[bound.get(v) for v in first_two]!r}")
            if not any("spikes.update" in ast.unparse(n) for n in called(worker, "codex_spikes")) \
                    and not any(isinstance(p, ast.Call) and ast.unparse(p.func) == "spikes.update"
                                and any(a is c for a in p.args for c in called(worker, "codex_spikes"))
                                for p in ast.walk(worker)):
                problems.append(f"{path.name}: Codex spikes must be merged into the stored spikes")

        named = re.search(r"Windows도\s*같은\s*(\d+(?:\.\d+)+)\s*으로", self.body)
        versions = _literal_assignments(APP_SOURCE, "APP_VERSION")
        if not named or versions != [named.group(1)]:
            problems.append(f"the notes say Windows ships {named and named.group(1)!r}; "
                            f"APP_VERSION is {versions!r}")
        win_version = _module_defs(WIN_BUILD).get("app_version")
        if win_version is None or not ("claude_pet.py" in _code_strings([win_version])
                                       and any("APP_VERSION" in s
                                               for s in _code_strings([win_version]))):
            problems.append("windows/build_win.py's app_version must read APP_VERSION out of "
                            "claude_pet.py")
        self.assertFalse(problems, "\n" + "\n".join(f"- {p}" for p in problems))


class SummaryMemoContractTests(unittest.TestCase):
    def test_summary_memo_key_covers_mode_language_and_onboarding(self):
        """roam_summary_text memoises per input; its key must include everything the
        text depends on that a refresh does not replace: the mode, the language ``t()``
        reads from the module-level ``L``, the onboarding state ``roam_summary`` turns
        into a status line, the two data objects and the auth-error flag.  The
        behavioural gate is in tests/test_companion_motion.py; this pins the shape so a
        dropped element is named rather than found as stale text.

        v0.26 adds four inputs the pill now depends on and a refresh does not replace: the
        two API-failure flags that decide whether an empty number reads as "loading" or as
        a reason, the pre-formatted credit text (which changes with the money/percent
        toggle without any data changing), and the Codex rows.  A memo key missing any of
        them shows the user stale text for up to the memo window — the failure this test
        exists to name."""
        text_fn = _nested_function(_module_def(APP_SOURCE, "run_gui"), "roam_summary_text")
        keys = [n for n in ast.walk(text_fn)
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "key"]
        self.assertEqual(len(keys), 1, "roam_summary_text must build exactly one memo key")
        self.assertIsInstance(keys[0].value, ast.Tuple, "the memo key must be a tuple literal")
        elements = [ast.unparse(e) for e in keys[0].value.elts]
        for needed in ("RUNTIME['mode']", "L['lang']", "state.get('onboard')",
                       "id(stats)", "id(oauth)", "bool(OAUTH_STATUS.get('auth_error'))",
                       "bool(state.get('api_error'))", "bool(state.get('api_stale'))",
                       "state.get('credit_text')", "id(state.get('codex'))"):
            self.assertIn(needed, elements, f"memo key {elements!r} lacks {needed}")
        self.assertIn("_summary_memo['key'] == key", ast.unparse(text_fn),
                      "the memo must be consulted by comparing the whole key")


if __name__ == "__main__":
    unittest.main()
