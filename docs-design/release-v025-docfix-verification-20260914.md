# Verification — v0.25 documentation fixes (two changes)

- **Verifier:** an independent Claude Code subagent, spawned for this verification only.
  Held **no other role** on either change: not Developer, not Reviewer, not Coordinator,
  not the gate verifier (`docs-design/release-v025-gate-20260914.md`), not the reviewer
  who raised B1/B2 (`docs-design/release-v025-review-20260914.md`). It edited no tracked
  file, ran no git write command, ran nothing from `release.sh` or `build_app.sh`, started
  no GUI, read no `~/.claude` transcript, wrote nothing under `~/.claude_pet/`, and created
  no untracked file other than this record. Having verified these changes it is **not**
  eligible to operate the release (AGENTS.md §1).
- **Written (UTC):** 2026-09-14T06:05Z.
- **Subjects:**
  - Change 1 — `/Users/yeongyu/claude-pet`, branch `main`, HEAD `aaf0ca6`, uncommitted
    edits to `README.md`, `README.ko.md`, `README.ja.md`, `README.es.md`.
  - Change 2 — `/Users/yeongyu/claude-pet-windows` (worktree), branch `windows`, HEAD
    `6d94c4d`, uncommitted edits to `windows/README.md`, `windows/build_win.py`,
    `windows/claude_pet_win.py`, `windows/verify_win_artifact.py`,
    `windows/win_autostart.py`.

---

## Verdicts

| Change | Verdict | Blocking items |
| --- | --- | --- |
| **1 — the four READMEs (B1 + B2 remedy)** | **FAIL** | **D1** — the macOS 12 fallback path names a screen that does not exist on macOS 12, in all four languages |
| **2 — the Windows doc/comment corrections** | **PASS** | none |

B1 is fully remedied. B2 is remedied in *structure* — the toggle is correctly qualified to
macOS 13+ and the Login Items instruction is restored — but the restored instruction carries
the macOS 13+ UI naming, so the half of the sentence addressed to macOS 12 users is not
actionable for them. That is D1, and it is the one thing standing between Change 1 and a PASS.

---

# Change 1 — the four READMEs

## B1 — the Spanish menu label — **PASS**

`TR["es"]["menu_autostart"]` in `claude_pet.py` is:

```
"menu_autostart": "Abrir al iniciar sesión",
```

(extracted by parsing `claude_pet.py` with `ast` and evaluating the `TR` assignment, so the
value is read, not grepped.) The reviewer's B1 is confirmed: the pre-fix cells quoted
`"Iniciar al iniciar sesión"`, which is not a string the app contains.

Both cells of `README.es.md:21` now quote the source string exactly:

```
| Inicio al iniciar sesión | Menú contextual → “Abrir al iniciar sesión” (…) | Menú contextual → “Abrir al iniciar sesión” (también como opción del instalador) |
```

The row's own label — `Inicio al iniciar sesión` — is a table heading, not a quoted menu
item, and is correctly left alone.

**The other three locales quote their own source exactly:**

| README | quoted | `TR[…]["menu_autostart"]` | match |
| --- | --- | --- | --- |
| `README.md:21` | `Start at sign-in` | `Start at sign-in` | ✓ |
| `README.ko.md:21` | `로그인 시 자동 실행` | `로그인 시 자동 실행` | ✓ |
| `README.ja.md:21` | `サインイン時に自動起動` | `サインイン時に自動起動` | ✓ |

**Neighbouring Spanish strings — all four use the same verb, "Abrir":**

```
"menu_autostart":        "Abrir al iniciar sesión"
"autostart_title":       "Abrir al iniciar sesión"
"autostart_unavailable": "Abrir al iniciar sesión (no disponible aquí)"
"autostart_approval":    "macOS necesita tu aprobación: Ajustes del Sistema → General → Ítems de inicio"
"autostart_open_settings": "Abrir Ítems de inicio"
```

No residue of the "Iniciar" verb remains anywhere in the `es` autostart family. The Spanish
README's macOS 12 path (`Ajustes del Sistema → General → Ítems de inicio`) is also a
character-for-character match with `autostart_approval`'s path — see D1 for why that
consistency is not by itself sufficient.

### Other README text that quotes a menu label

Every quoted label was compared against its `TR` source. All match exactly **except one
family, which is pre-existing and outside this diff**:

- **`menu_update`** — line 58 of each README quotes a label the app does not literally
  produce, because the real label embeds the version number:

  | README:58 quotes | `TR[…]["menu_update"]` |
  | --- | --- |
  | `⬆︎ Install new version` | `⬆︎ Install v{v}` |
  | `⬆︎ 새 버전 설치` | `⬆︎ 새 버전 v{v} 설치` |
  | `⬆︎ 新しいバージョンをインストール` | `⬆︎ 新バージョン v{v} をインストール` |
  | `⬆︎ Instalar nueva versión` | `⬆︎ Instalar v{v}` |

  **Advisory, non-blocking, not introduced here.** A README cannot reproduce `{v}`, so a
  paraphrase is defensible; but it is the same class of drift B1 is about, and if the goal
  is "every quoted label is its `TR` source verbatim", this family is the remaining gap.

Exact matches confirmed: `menu_install_cc`, `menu_login_cc`, `menu_check_update`,
`menu_uninstall` in all four locales.

- **Line 66 of each README** quotes the *installer* task label, not a `TR` menu string:
  `installer.iss` defines `english.StartupTask=Start {#MyAppName} when I sign in to Windows`
  and `korean.StartupTask=Windows 로그인 시 {#MyAppName} 자동 실행`. The READMEs drop
  "to Windows" / "Windows". Pre-existing, outside this diff, **advisory only** — and there
  are no `ja`/`es` messages in `installer.iss` at all, so those two READMEs are describing
  a label their readers will see in English.

## B2 — what a macOS 12 user actually sees — **established, then judged**

Read directly out of `claude_pet.py` (source facts, not observations — AGENTS.md §5):

1. `autostart_service()` does `from ServiceManagement import SMAppService` inside a
   `try`, and returns `None` on any exception. Its own docstring states the case:
   *"macOS 12 에는 SMAppService 클래스가 없고"*. `SMAppService` is macOS 13+.
2. `autostart_current()` returns `(None, is_bundle)`.
3. `autostart_read_state(service=None, is_bundle=True)` short-circuits on
   `if not is_bundle or service is None: return "unavailable"` — `status()` is never called.
4. The menu builder, on `a_state == "unavailable"`, calls
   `mi.setTitle_(t("autostart_unavailable"))` and `mi.setEnabled_(False)`, with
   `menu.setAutoenablesItems_(False)` already set above so the disable is not undone.

**So on macOS 12 the item reads "Start at sign-in (not available here)" and is greyed out.**
It is never clickable, and `autostart_state()` is not even consulted. The reviewer's B2 is
confirmed.

The pre-v0.25 cell is also confirmed, from `git log -p -S "Login Items" -- README.md`: it
read `System Settings → General → Login Items` and the v0.25 commit replaced it wholesale.

### Judgement on the corrected cell

**macOS 13+ — accurate and actionable.** The toggle exists, the label is quoted exactly, and
the qualification correctly scopes it.

**macOS 12 — NOT actionable. This is D1.**

### D1 (blocking) — the macOS 12 fallback names a macOS 13+ screen, in all four languages

All four cells direct a macOS 12 user to the **Ventura-and-later** System Settings UI:

| file:line | the macOS 12 clause as written | what macOS 12 actually has |
| --- | --- | --- |
| `README.md:21` | `System Settings → General → Login Items` | `System Preferences → Users & Groups → Login Items` |
| `README.ko.md:21` | `시스템 설정 → 일반 → 로그인 항목` | `시스템 환경설정 → 사용자 및 그룹 → 로그인 항목` |
| `README.ja.md:21` | `システム設定 → 一般 → ログイン項目` | `システム環境設定 → ユーザとグループ → ログイン項目` |
| `README.es.md:21` | `Ajustes del Sistema → General → Ítems de inicio` | `Preferencias del Sistema → Usuarios y grupos → Ítems de inicio` |

macOS 13 (Ventura) renamed **System Preferences** to **System Settings** and introduced the
`General → Login Items` pane; macOS 12 (Monterey) has neither the app name nor that pane.
The clause therefore sends the one audience it was written for — macOS 12 users, who face a
permanently greyed-out menu item — to an app they do not have.

> **Provenance of this claim, stated plainly (AGENTS.md §5).** This is not a repo fact and
> not a measurement taken here; no macOS 12 machine was available to this verifier. It is
> external, deterministic, and checkable by anyone against Apple's own documentation or any
> macOS 12 install. It is **not** an observation in §5's sense and is not offered as one.
> The repo half — that macOS 12 gets no working toggle — *is* read out of source above and
> is not in doubt.

**Why this is blocking rather than advisory.** The macOS 12 clause is the entire substance of
the B2 remedy. Without it the cell is a bare macOS 13+ statement; with it pointing at a
nonexistent screen, a macOS 12 user is no better off than before the fix — and arguably worse,
because the text now speaks to them by name. This is also precisely the failure mode B1 is
about (quoting UI a user cannot find), one row over.

**Note on origin, in fairness to the Developer.** The wording is verbatim from the reviewer's
own suggested fix in `docs-design/release-v025-review-20260914.md` (B2, "**Fix:**"), and the
inaccuracy is *inherited* — the pre-v0.25 cell carried the same Ventura naming for all users.
The Developer implemented the prescription faithfully. The prescription was wrong on this point.

**Concrete remedy (documentation-only, four one-line edits):**

```
README.md      | Start at sign-in | Right-click menu → “Start at sign-in” (macOS 13+; on macOS 12, System Preferences → Users & Groups → Login Items) | … |
README.ko.md   | 로그인 시 시작 | 우클릭 메뉴 → “로그인 시 자동 실행”(macOS 13 이상. macOS 12에서는 시스템 환경설정 → 사용자 및 그룹 → 로그인 항목) | … |
README.ja.md   | サインイン時に起動 | 右クリックメニュー →「サインイン時に自動起動」（macOS 13 以降。macOS 12 はシステム環境設定 → ユーザとグループ → ログイン項目） | … |
README.es.md   | Inicio al iniciar sesión | Menú contextual → “Abrir al iniciar sesión” (macOS 13+; en macOS 12, Preferencias del Sistema → Usuarios y grupos → Ítems de inicio) | … |
```

The reviewer's alternative — narrowing the OS row to macOS 13+ — also closes D1, but it
changes a **product support claim**, not a wording, so it is the user's call, not a
documentation edit an agent should make on its own.

Whichever is chosen, **do not "fix" `TR[...]["autostart_approval"]` to match.** That string
is only ever rendered from the `approval` branch of `toggleAutostart_`, which is reachable
only where `SMAppService` exists — macOS 13+ — where its current path is correct.

## No contradiction with the OS row, and no other sign-in claim

- The OS row says `macOS 12 or later` / `macOS 12 이상` / `macOS 12 以降` /
  `macOS 12 o posterior`. The new qualification **explains** that row rather than contradicting
  it: the app runs on 12, the toggle does not. This was the reviewer's stated consistency
  complaint and it is now resolved.
- Line 32 of each README repeats `macOS 12+` in the install prerequisites. Consistent.
- Every other sign-in mention in the four files was enumerated (`grep` for sign-in /
  로그인 / サインイン / iniciar sesión / Login Item / Startup): the only other one is
  line 66, the Windows installer option, which makes no macOS claim. **No contradiction found.**

## Diff scope and table integrity — **PASS**

```
$ git diff --stat
 README.es.md | 2 +-
 README.ja.md | 2 +-
 README.ko.md | 2 +-
 README.md    | 2 +-
 4 files changed, 4 insertions(+), 4 deletions(-)
```

- Exactly one line changed per file, and in every case it is line 21 — the
  "Start at sign-in" row of the platform table. **Nothing rode along.**
- `git diff --check -- README.md README.ko.md README.ja.md README.es.md` → **exit 0**, no output
  (no whitespace errors, no conflict markers).
- Markdown tables: each file holds **15** table rows before and after the change (`git show
  HEAD:<file>` vs. working tree), and **every** row in all four files has exactly 4 pipes,
  i.e. 3 columns. No row was split, merged, or left ragged. The edited cells contain no
  unescaped `|`.
- The four untracked user-owned paths (`diag.py`, `release/ClaudePet.iconset/`,
  `release/icon_1024.png`) are untouched and still `??` in `git status --porcelain`.

---

# Change 2 — the Windows worktree

## (a) Uninstall leftovers — **PASS**

**The claim is now stated, and it is correct.** `windows/README.md` carries it twice:

- a new paragraph in `## 완전 삭제` (line ~100) — *"레지스트리에 하나가 더 남습니다:
  `HKCU\…\Explorer\StartupApproved\Run` 의 `ClaudePet` 값"*, naming the wrong sentence
  explicitly (*"완전 삭제 뒤 남는 것은 `.claude_pet\` 뿐" 은 엄밀히 틀린 문장입니다*);
- the hardware-checklist item (line ~279), rewritten from the flat
  *"남는 것: `%USERPROFILE%\.claude_pet\` 만"* to *"파일은 … 뿐이고, **레지스트리에는 …
  값이 남는다**"*.

**Both mechanisms check out against source:**

| path | what it deletes | reaches StartupApproved? |
| --- | --- | --- |
| installer uninstaller | `installer.iss:60` — `Root: HKCU; Subkey: …\Run; ValueName: "ClaudePet"; Flags: uninsdeletevalue` | **no** — the only `[Registry]` entry is the `Run` value; there is no StartupApproved entry anywhere in the file |
| in-app "완전 삭제…" | `claude_pet_win.delete_run_value_if_ours` (line 279) opens `wu.RUN_SUBKEY` and calls `winreg.DeleteValue(k, wu.RUN_VALUE_NAME)` | **no** — it never opens `STARTUP_APPROVED_SUBKEY` |

The only code that deletes a StartupApproved entry is `win_autostart.autostart_toggle`'s
off-path, which the uninstall flow does not call.

**Harmlessness reasoning checks out for the observed byte.** `startup_approved_enabled` is
`not blob[0] & 0x01`, so a surviving `0x00` reads *enabled*; `_state_of` then returns `"on"`
once a reinstall restores the `Run` value. The README states this scoped to `0x00`, which is
the byte the hardware pass reported.

**`installer.iss` was NOT changed** — `git status --porcelain windows/installer.iss` returns
nothing, and it is absent from `git diff HEAD --name-only`. The README says so in as many
words (*"이번 릴리즈에서는 `installer.iss` 를 바꾸지 않는다"*) and records the deletion as a
next-release candidate with the two paths that would have to move together. Correct and
deliberate.

**Advisory (non-blocking).** The harmlessness argument is written for an *even* leftover byte.
A user who disabled startup through the Startup apps UI before uninstalling would leave `0x01`
behind, and a reinstall would then land on *disabled*, not enabled. The README's sentence is
correctly scoped to `0x00` so it is not wrong; it simply does not cover the odd case. A half
sentence would close it. Also, the *"남기는 것"* list at line ~89 is still file-only; the
correcting paragraph is eleven lines below it in the same section, which is close enough to
find but a forward pointer on line 89 would be better.

## (b) StartupApproved byte provenance — **PASS**

**The observation is now recorded to §5's standard**, in `win_autostart.startup_approved_enabled`'s
docstring, the module docstring, and `windows/README.md`. It carries:

- **scope** — one machine, Windows 11, 2026-09-14, through the startup UI;
- **the sample** — two disable/enable pairs from two different starting states (no prior
  record → `0x01` / `0x00`; existing `0x02` record → `0x03` / `0x02`), plus **eight**
  third-party entries all carrying `0x02`, none of them ever touched through that UI;
- **the raw bytes**, not verdicts — including that disabling appends an 8-byte FILETIME while
  enabling writes the first byte followed by zeros;
- **an explicit refutation note** — one machine is enough to refute, and it did refute the
  shipped `0x02`-enabled guess.

**It does not assert a universal Windows fact.** The three §5 slots are kept in three separate
bullets, and the middle one — *"Windows keeps the existing record's upper bits and flips only
the lowest one"* — is labelled in its own text as *"기기 한 대의 동작에서 끌어낸 추론이지
문서화된 계약이 아니고, 다른 사람이 재현하지도 않았습니다"* / *"still an inference from one
machine's behaviour and not a documented contract, and no second party has reproduced it
(AGENTS.md §5)"*. The remaining extrapolation is narrowed and separately labelled: first bytes
**above** `0x03` only, *"관찰이 아니라 위 방식에서 따라 나오는 것뿐"*. That is the correct
shape — the observation is not promoted to an invariant, and the instruction ("if another byte
shows up, change that one function and its test table together") is stated separately from both.

**The implementation is unchanged.** Comparing against `git show HEAD:windows/win_autostart.py`
by AST (docstrings stripped), the bodies of `startup_approved_enabled` and `_state_of` are
**identical**. The function is still, byte for byte:

```python
    return bool(isinstance(blob, (bytes, bytearray)) and len(blob) > 0
                and not blob[0] & _STARTUP_APPROVED_DISABLED_BIT)
```

with `_STARTUP_APPROVED_DISABLED_BIT = 0x01` unchanged. The even/odd rule stands.

**Advisories (non-blocking, both about provenance wording rather than substance):**

1. The record's account of *which* startup UI produced the byte pairs **changed** between the
   two versions. `HEAD` said the toggling was done *"설정 › 시작 앱과 작업 관리자 › 시작 앱"*
   (both UIs); the new text says *"같은 UI"* / *"both pairs below came from the same UI"*
   without naming it. That is the more conservative claim, so it is not an overreach — but
   the change is unexplained, and having just gone to the trouble of pinning the
   blank-publisher screen by name, leaving this one anonymous is a gap the next hardware pass
   should close. (The checklist at README:301 already asks for it.)
2. *"Settings › Apps › Startup apps and Task Manager › Startup apps **both write** the same
   key"* is asserted flatly in the module docstring, the `STARTUP_APPROVED_SUBKEY` comment and
   `README.md:143`, with no cited source and no statement of whether the hardware pass
   exercised Task Manager. It replaces an equally unsourced single-UI attribution, so it is a
   net improvement and the code does not depend on it — it reads the key regardless of who
   wrote it — but strictly it is a Windows behavioural claim in slot 2 with no source.

## (c) The blank-publisher screen — **PASS**

Both files now **name** the screen instead of declining to:

- `windows/build_win.py:83` — *"화면은 `설정 › 앱 › 시작 앱` 이었다(작업 관리자도, 설정 › 앱 →
  설치된 앱도 아니다 — 이번 실기에서 확정됐다)"*, replacing *"어느 화면인지는 기록되지 않았다 …
  여기서 화면 이름을 단정하지 않는다"*.
- `windows/README.md:190` — *"**화면은 `설정 › 앱 › 시작 앱`** 이다"*, plus the after-state
  (*"고친 뒤 같은 줄은 'Claude Pet / Yeongyu Yang' 으로 보인다"*).
- `windows/verify_win_artifact.py:56` — the same, in `check_version_resource`'s docstring.
- The hardware checklist item at README:263 is retitled *"(고침, 화면 확정)"* and now records
  the answer instead of asking the question; what remains open is narrowed to the *other two*
  lists and the `FileVersion` check.

**Every remaining Task Manager reference was enumerated and classified:**

| location | what it says | correct? |
| --- | --- | --- |
| `build_win.py:86`, `verify_win_artifact.py:58`, `README.md:193` | *"시작 앱 목록(설정 › 앱 › 시작 앱, 작업 관리자 › 시작 앱·세부 정보)은 exe 의 `FileDescription`/`CompanyName` 을 읽고"* | ✓ — **which lists read the PE version resource**, exactly the intended framing |
| `build_win.py:83`, `verify_win_artifact.py:56`, `README.md:190`, `README.md:264` | *"작업 관리자도 … 아니었다"* | ✓ — explicitly excludes Task Manager as the observation site |
| `README.md:266` | *"남은 것은 다른 두 목록(작업 관리자 › 시작 앱·세부 정보, 설정 › 앱 → 설치된 앱)에서도 같은 이름·게시자로 보이는지"* | ✓ — a future check, correctly marked as not yet done |
| `win_autostart.py:13,59,87`, `claude_pet_win.py:44,1100`, `README.md:143` | both UIs write the same StartupApproved key | ✓ — a different subject (who writes the key), not observation provenance |
| `README.md:294–306` | toggle through Task Manager during the next hardware pass | ✓ — a test instruction |

**No remaining Task Manager reference attributes the blank-publisher observation to it.**

## (d) Comments/docstrings/strings only — **PASS**

Method: for each of the four files, parse the working-tree version and
`git show HEAD:<file>` with `ast`, strip every module/class/function docstring, and compare
`ast.dump`. Comments are invisible to the AST, docstrings are removed, so equality proves the
executable content is identical — every statement, every constant value, every branch.

```
windows/win_autostart.py        code AST identical: True
windows/claude_pet_win.py       code AST identical: True
windows/build_win.py            code AST identical: True   (full AST identical too — comments only)
windows/verify_win_artifact.py  code AST identical: True
```

**No executable line, no constant, no control flow changed.** `VERSION_STRINGS`,
`STARTUP_APPROVED_SUBKEY`, `_STARTUP_APPROVED_DISABLED_BIT`, `RUN_SUBKEY`, `RUN_VALUE_NAME` all
carry their previous values. Reading the diff confirms the non-docstring hunks are `#` comments
throughout.

### Bonus check — the new "정정(2026-09-14)" item is itself correct

The change adds a correction that was not in my brief, so I verified its claims too. It says
the uninstall confirmation dialog cannot distinguish `inno` from `portable`. Both claims hold:

- `claude_pet_win._uninstall`: `items = [a for op, a in plan if op == "delete" and os.path.lexists(a)]`
  — only `("delete", …)` steps become lines, so `win_update.uninstall_plan`'s kind step
  (`("run", [unins000.exe, "/SILENT"])` for inno, `("helper", exe_dir)` for portable) never
  appears on screen;
- `if kind != "source": items.insert(0, exe_dir)` — `exe_dir` is prepended for **every**
  non-source kind, so the two dialogs show the same lines.

The correction is accurate, and keeping it in place rather than deleting the wrong expectation
is the right call for a record of what a hardware session was told to look at.

## (e) Test runs — **both green**

Run from `/Users/yeongyu/claude-pet-windows` (the worktree), 2026-09-14, no environment
overrides:

```
$ python3 -m unittest discover -s windows/tests -t .
Ran 215 tests in 1.121s
OK
```

```
$ python3 -m unittest discover -s tests
Ran 612 tests in 333.528s
OK (skipped=8)
```

All 8 skips are the **loud** opt-in live checks, each printing its reason to stderr before
skipping — `[updater] SKIPPED: the installed-app preflight is an opt-in live check; set
CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1 to run it` and the matching stapler-contract line. That is
the documented behaviour of `tests/test_updater.py` (CLAUDE.md: *"Tests that need the real
macOS tools skip **loudly**"*), not silent coverage loss. No failures, no errors, exit 0 from
both.

---

## Summary

- **Change 2 — PASS.** The three hardware findings are recorded accurately and to §5's
  standard, the even/odd implementation and `installer.iss` are provably untouched, the diff
  is comments and docstrings only by AST equivalence, and both suites are green. Two
  provenance advisories, neither blocking.
- **Change 1 — FAIL on D1.** B1 is fully fixed, the diff scope is exactly four table cells,
  `git diff --check` is clean, the tables are intact, and B2's structure is right — but the
  macOS 12 fallback path names the macOS 13+ System Settings UI in all four languages, so the
  clause written for macOS 12 users points at a screen they do not have. Four one-line edits
  close it; the exact replacement text for each locale is given under D1 above.
