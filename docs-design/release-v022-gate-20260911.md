# ClaudePet v0.22 — 실행 게이트 기록 (2026-09-11)

## v0.22 릴리즈 — 실행 게이트(AGENTS.md §6) 판정: GREEN

- 판정자: **coordinator-v022** (독립 Coordinator. 이 릴리즈에서 Developer·Verifier·Reviewer·Release operator 어느 역할도 보유하지 않았고, 파일을 편집하지 않았으며, 커밋·태그·푸시를 하지 않았다. 아래 근거는 전부 저장소 루트 `/Users/yeongyu/claude-pet` 에서 읽기 전용 명령으로 직접 확인한 것이다.)
- 측정 창: **2026-09-11T00:27:57Z → 2026-09-11T00:31:55Z (UTC)**. 창의 시작과 끝 모두 `git rev-parse HEAD` = `f3acb47d83dcb25fb8c6a852934a0c060777951d`, `git status --porcelain` 의 tracked 항목은 ` M docs-design/release-v022-verification-20260911.md` 하나뿐(나머지는 전부 `??`).
- 판정 대상: 릴리즈 커밋 **f3acb47d83dcb25fb8c6a852934a0c060777951d** ("release: ClaudePet v0.22") 와, 게시된 v0.21(태그 `v0.21` → `24731b0`, HEAD 의 조상, `origin/main` 과 동일) 이후 그 커밋까지의 변경 전체(커밋 7개).

### 1. §8 병합 체크리스트 — 릴리즈 커밋과 릴리즈에 포함된 모든 변경에 대해 평가 가능하고, 충족됨

**1-1. trailer 존재·상이(§7, §8 항목 1).** `git log -1 --format=%B f3acb47` 의 trailer 다섯 줄이 서로 다른 당사자를 지명한다: `Developer: Claude (session 55c3dee4-727f-4a94-b960-66540b129014)` / `Verifier: verifier-v022` / `Reviewer: reviewer-v022` / `Coordinator: coordinator-v022` / `Release-Operator: operator-v022`. 동일값 없음.

**1-2. Developer–Verifier 분리(§2, §8 항목 2).** `git show f3acb47` 의 hunk 로 확인한 편집 집합: Developer 는 `claude_pet.py` 한 줄(`APP_VERSION = "0.21"` → `"0.22"`), `verify_release_artifact.py` 한 줄(usage 예시 `--expect-version 0.21` → `0.22`), `RELEASE_NOTES.md` +5줄; Verifier 는 `tests/test_upload_artifact_gate.py`(핀 리터럴 2개), `tests/test_manual_update_transaction.py`(핀 리터럴 1개), `tests/test_v021_release_contract.py → tests/test_v022_release_contract.py`(이름 변경 후 재작성), `docs-design/release-v022-verification-20260911.md`; Reviewer 는 `docs-design/release-v022-review-20260911.md`. 세 집합은 교집합이 없다(8개 파일, 1000 추가 / 111 삭제).

**1-3. 핀과 소스 일치.** `shasum -a 256 claude_pet.py` = `04d016e8c0011bb341155fc12b8851f12d2022558b116bfb2da6f4f997f66266` 이고 `git show HEAD:claude_pet.py | shasum -a 256` 과 같다. 같은 값이 `tests/test_upload_artifact_gate.py` 의 `REVIEWED_APP_SOURCE_SHA256` 과 `tests/test_manual_update_transaction.py` 의 앱 소스 핀에 그대로 들어 있다. 나머지 핀도 현재 바이트와 일치: `verify_release_artifact.py` = `8de85e87…b82d`(`REVIEWED_VERIFIER_SHA256`), `release.sh` = `a5b25686…46e23`(`REVIEWED_RELEASE_SHA256`), `build_app.sh` = `83eca429…00d6`(`REVIEWED_BUILD_APP_SHA256`).

**1-4. 버전.** `claude_pet.py` 에 `APP_VERSION = "0.22"` 리터럴이 정확히 하나(`grep -n '^APP_VERSION'`). `setup.py` 는 그 리터럴을 정규식으로 읽어 `CFBundleVersion` 과 `CFBundleShortVersionString` 양쪽에 넣는다(별도 하드코딩 없음).

**1-5. red-before-green 이 원문으로 기록됨(§3, §8 항목 3).** `docs-design/release-v022-verification-20260911.md` §3 에 리핀 전 실패 출력이 그대로 있다: 업로드 게이트 `Ran 64 tests in 3.324s` / `FAILED (failures=48)`, 수동 트랜잭션 `Ran 0 tests in 0.003s` / `FAILED (errors=8)`, 구 계약 테스트 `Ran 10 tests in 0.107s` / `FAILED (failures=2)`; 새 계약 테스트는 스크래치 변이 14/14 가 `FAILED` 로 기록되어 있고(§6, `00_control` 만 `OK`), Reviewer 기록은 독립 드라이버로 15/15 RED 를 재현했다고 적는다.

**1-6. Reviewer 사인오프(§1, §8 항목 4).** `docs-design/release-v022-review-20260911.md` "## Verdict" 가 **PASS** 이고 작성자는 reviewer-v022 — Developer 도 Verifier 도 아니다. 이 파일은 HEAD 에 tracked(blob `5c26cea2…`)이며 작업 트리와 HEAD 가 같다.

**1-7. 전체 스위트 green, Verifier 실행(§8 항목 5).** 준비 트리 실행(기록 §7) `Ran 486 tests in 328.034s` / `OK (skipped=7)`; clean 트리 재실행은 아래 항목 2.

**1-8. untracked 파일 무접촉·파괴적 git 명령 없음(§4, §8 항목 6).** 지금 시점 `stat -f '%m %N'`: `diag.py` 1784689621, `release/icon_1024.png` 1783953996, `release/ClaudePet.iconset` 1783953996 — 릴리즈 커밋 본문에 적힌 값과 동일. `git reflog --date=iso` 에 2026-09-10 이후 `reset`·`checkout -f`·`restore`·`clean`·`stash` 항목이 없고, `stash@{0}` 은 여전히 2026-07-23 의 것이다.

**1-9. 정량 주장의 §5 충족(§8 항목 7).** 검증 기록 E2 는 명령·cwd·인터프리터·환경 변수·집계 단위(unittest 케이스)·파일 집합(18개 모듈과 모듈별 케이스 수, 합 486)·창 시작/끝·측정 시각·분자/분모(486 실행, 479 통과, 7 스킵, 실패 0, 에러 0)를 모두 갖춘다.

**1-10. 릴리즈에 포함된 모든 변경(v0.21..HEAD, 커밋 7개).** `git log v0.21..HEAD` 의 일곱 커밋(`9f8ba13`, `147004d`, `dba49ef`, `4220229`, `ad1755f`, `0cc8a2b`, `f3acb47`) 전부 `Developer:` ≠ `Verifier:`. 기능 커밋 `147004d`·`ad1755f` 는 `Reviewer: Curie` 를 달고 있고, 독립 리뷰 기록 `docs-design/free-roaming-review-20260909.md`("Status: APPROVED", 최종 승인 절 "Source-only approval: APPROVED")·`docs-design/companion-play-review-20260909.md`("Status: APPROVED …")가 HEAD 에 있다. 두 검증 기록에는 RED 원문(`FAILED (failures=5)`, `FAILED (failures=14)` 등)과 전체 스위트 green 원문(`Ran 454 tests in 323.611s` / `OK (skipped=7)`, `Ran 485 tests in 327.916s` / `OK (skipped=7)`)이 있다. `git diff v0.21..HEAD -- claude_pet.py` 의 hunk 는 모듈 docstring 한 줄, `APP_VERSION` 한 줄, ROAM_DEFAULTS 위 주석, `ROAM_DEFAULTS`·`_roam_seg_dist`·`Roamer`·`RoamDisplay`·`run_gui` 에만 있고, `_weigh_usage`·`parse_usage_entries`·`compute_usage`·`_weekly_window_start`·`spike_info`·`is_spike`·`RUNTIME` 한도 상수·`SESSION_HOURS`·`PREMIUM_FAMILIES` 를 건드린 줄은 없다 — 릴리즈 노트의 "한도 계산은 그대로" 는 참이고, 보정 안내가 없는 것이 맞다.

### 2. Verifier 의 clean 트리 전체 스위트 재실행 — 기록 존재, 원문 인용 확인 (§6 항목 2)

- 기록 위치: `docs-design/release-v022-verification-20260911.md` 맨 끝 절 "## v0.22 release — execution gate: clean-tree suite re-run at commit f3acb47d83dcb25fb8c6a852934a0c060777951d" (verifier-v022 가 2026-09-11T00:27:03Z 에 append).
- 기록의 트리: HEAD `f3acb47…` 을 실행 전(2026-09-11T00:18:55Z)과 후(00:25:02Z) 모두 확인, porcelain 은 `??` 만, `git diff --stat HEAD` 출력 없음 → AGENTS.md §6 정의의 clean 트리.
- 명령: `python3 -m unittest discover -s tests -v`, cwd `/Users/yeongyu/claude-pet`, Python 3.13.7. 창 **2026-09-11T00:19:15Z → 00:24:43Z**, exit 0. 결과 줄 원문: **`Ran 486 tests in 328.259s`** / **`OK (skipped=7)`**. 스킵 7개는 전부 `CLAUDEPET_RUN_LIVE_UPDATER_TESTS=1` 또는 `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES=1` 이 필요한 opt-in 라이브 검사이며 이름별로 기록되어 있다.
- 내가 직접 대조한 것: 스크래치 원본 `suite-output.txt` 의 SHA-256 `1d35365ead05512f4aa21af7497721ccff4197ca998d3229b7f74f5253f6c154` 가 기록과 일치, 731줄, 623·625행이 위 두 줄 그대로, `FAIL:`/`ERROR:` 블록 0개, `ok` 판정 479개 + `skipped` 7개 = 486.
- 작업 트리: `git diff --numstat HEAD` = `261 0 docs-design/release-v022-verification-20260911.md` 하나뿐. 이 파일의 앞 32993바이트는 HEAD 블롭 `359071a5b51b14498a6ef795e1a404e68d540e2f` 와 `cmp` 로 바이트 동일(SHA-256 `6442c3c8…ae04`), 즉 기존 기록은 한 글자도 바뀌지 않고 절 하나가 뒤에 붙었다. → **항목 2 GREEN.**

### 3. 릴리즈 노트 확인 (§6 항목 3, CLAUDE.md 2단계 형식)

- `RELEASE_NOTES.md` 맨 위 미게시 섹션 `**v0.22**`: 최상위 불릿 **3개**, 중첩 불릿 **0개**, 불릿 외 문장 없음. 공백 정규화 글자 수 **299**(불릿 본문, `- ` 포함; 마커 제외 293, 제목 포함 309) ≤ 450. 불릿마다 정확히 **2문장**. 해시·내부 식별자·소스 경로·줄 번호·테스트 언급·크기/빈도 표현 없음(정규식 스캔 결과 모두 빈 집합).
- 유일한 수치 **"10~20초"**: `claude_pet.py` 의 `ROAM_DEFAULTS["follow_min_s"] = 10.0`, `["follow_max_s"] = 20.0` 이고, `Roamer` 의 follow 분기가 `self.rng.uniform(self.cfg["follow_min_s"], self.cfg["follow_max_s"])` 로 그 값을 쓴다 — 릴리즈 커밋 시점 트리에서 감사 가능. 인용 라벨 **"화면 돌아다니기"** 는 `TR["ko"]["menu_roam"]` 과 글자 그대로 일치.
- 게시된 부분 불변: `**v0.21**` 제목부터 EOF 까지의 바이트가 작업 트리·HEAD·HEAD~1 세 곳 모두 SHA-256 `323664aeddc2d45c1c938f4f42aa51adaba00891888efdd52712ef997dde0a75`, 17273바이트, `cmp` 동일. `git diff HEAD~1 HEAD -- RELEASE_NOTES.md` 는 v0.21 제목 위에 +5줄뿐.
- 미게시 확인: `git tag -l 'v0.22*'` 없음; `git ls-remote --tags origin` 에 v0.22 없음(최신 `refs/tags/v0.21` → `24731b0`); `gh release list --limit 5` 최신은 **v0.21 (Latest, 2026-09-09T01:27:59Z)**; `gh release view v0.22` → "release not found". 따라서 v0.22 섹션은 staged 상태이고, 이 게이트는 그것을 그대로 승인한다. → **항목 3 GREEN.**

### 4. Coordinator 사인오프 (§6 항목 4)

위 1~3 을 직접 확인한 결과, **릴리즈 커밋 f3acb47d83dcb25fb8c6a852934a0c060777951d 에 대한 AGENTS.md §6 실행 게이트는 GREEN 이다.** coordinator-v022 가 2026-09-11T00:31:55Z (UTC) 에 사인오프한다. 이 사인오프는 "릴리즈할 준비가 됐다"는 인증이지 권한 부여가 아니며(권한 부여는 §6 항목 6 참조), 이 사인오프를 한 나는 §1 에 따라 이 릴리즈의 오퍼레이터가 될 수 없다.

### 5. 릴리즈 오퍼레이터 지명과 자격 (§6 항목 5)

**operator-v022** 를 지명한다. 이 게이트가 GREEN 이 된 뒤에 새로 생성되는 에이전트로, 이 릴리즈의 어떤 변경에서도 Developer·Verifier·Reviewer·Coordinator 역할을 보유한 적이 없다(보유하지 않은 역할: 네 가지 전부). 자격 배제 목록: Developer 세션(Claude, 55c3dee4-727f-4a94-b960-66540b129014)·verifier-v022·reviewer-v022·coordinator-v022(나)·이전 변경의 Mendel/Curie 는 모두 이 릴리즈의 어떤 변경에 역할을 가졌으므로 오퍼레이터가 될 수 없다.

### 6. 권한 부여의 상태

사용자의 말 **"22 버전으로 릴리즈해"** (2026-09-11, Developer 세션에서 사용자가 직접 입력)는 그 말을 직접 본 Developer 세션이 릴리즈 커밋 본문에 원문 그대로 옮겨 적었다 — 권한 부여가 사는 자리(변경 설명)에 사용자 본인의 말로 기록된 것이다. 나는 그 문구를 배정문으로 전달받았을 뿐 직접 보지 못했으므로 이 기록은 권한 부여를 새로 만들지도 보증하지도 않는다. 문면 그대로의 범위는 v0.22 릴리즈를 끝까지 마치는 것(build·sign·notarize·universal·dmg·태그·푸시·publish)이며, 그 범위에서도 `all`·`ship`·인자 없는 `./release.sh` 는 [NEVER] 이고 오퍼레이터 자격 제한은 풀리지 않는다. 권한 부여는 게이트가 통과했다는 발견이 아니다 — 통과 여부는 위 1~4 가 답한다.

### 7. 오퍼레이터(operator-v022)에게 허용된 단계 — 이 순서, 이 목록 그대로

**시작 전 확인(전부 읽기 전용):** (a) 이 게이트 기록과 Verifier 의 append 가 **문서만 바꾸는 커밋 하나**(게이트 기록 커밋)로 f3acb47 위에 올라가 있을 것 — `git diff --stat f3acb47..HEAD` 가 `docs-design/*.md` 경로만 나열해야 한다. 그 커밋도 §7 대로 `Developer:`/`Verifier:` 를 서로 다른 당사자로 달고, 스테이징은 경로를 이름으로 지정해(`git add docs-design/release-v022-verification-20260911.md docs-design/<게이트 기록 파일>`) `git diff --cached --name-only` 로 읽어 확인한다 — `git add -A`/`git add .` 는 [NEVER]. (b) `shasum -a 256 claude_pet.py` 가 여전히 `04d016e8…6266` 이고 `git status --porcelain` 에 `??` 외 항목이 없을 것. (c) 문서만 바뀌었으므로 소스 핀·계약 테스트·릴리즈 노트 접미 해시는 그대로 유효하고 게이트 재평가는 필요 없다; 조건 (a)(b) 중 하나라도 깨지면 시작하지 말고 보고한다.

1. **① `./release.sh build`** — py2app 빌드, 서명 없음. 이 릴리즈의 실행 단계이므로 이 게이트가 GREEN 인 지금부터 허용.
2. **② 주석 달린 로컬 태그 `v0.22`** 를 **게이트 기록 커밋**에 만든다(`git tag -a v0.22 -m "ClaudePet v0.22" <게이트 기록 커밋>`). 릴리즈 커밋 f3acb47 자체나, 히스토리의 `7865af5 "release: ClaudePet v0.22"`(v0.21 로 재번호되어 게시된 적 없는 이전 준비 커밋, v0.21 의 조상)에는 달지 않는다. `git tag --sort=-v:refname | head -1` 이 `v0.22` 이고 `git rev-parse v0.22^{}` 가 그 커밋인지 읽어 확인.
3. **③ `./release.sh sign`** — [ASK-OP].
4. **④ `./release.sh notarize`** — [ASK-OP].
5. **⑤ `./release.sh universal`** — [ASK-OP]. `universal2` Python 이 없으면 스크립트가 거부한다; 그 거부는 실패로 기록하고 멈춘다.
6. **⑥ `./release.sh dmg`** — [ASK-OP].
7. **⑦ `git push origin main`** — [ASK]. `origin/main` 은 `24731b0`(v0.21)이므로 이 릴리즈의 커밋 7개 + 게이트 기록 커밋이 올라간다.
8. **⑧ `git push origin v0.22`** — [ASK]. 이 순간부터 설치된 모든 앱이 업데이트를 제안받는다; 되돌릴 수 없다.
9. **⑨ `./release.sh publish`** — [ASK]. 업로드 전에 아티팩트 게이트(4개 파일 전부, 아카이브 안전성, 소스 해시, 버전, 파일명이 정하는 아키텍처, 서명·공증·스테이플)가 돌고, 하나라도 거부하면 업로드하지 않는다. 거부는 실패로 기록하고 멈춘다.

**③~⑥ [ASK-OP] 세 조건:** 사용자 권한 부여가 릴리즈 커밋에 원문으로 기록되어 있고(§6 항목 6), 모든 게이트가 이 기록으로 먼저 기록되었고, 실행자는 다른 역할이 없는 operator-v022 다. **각 단계마다** 명령·UTC 시작/끝·exit status·핵심 출력 줄을 기록하고, **첫 실패에서 멈추어** 유지보수자에게 남은 것을 그대로 넘긴다. 실패 후 다음 단계로 넘어가거나 순서를 바꾸지 않는다.

**[NEVER] 유지:** `./release.sh all`, `./release.sh ship`, 인자 없는 `./release.sh`(오퍼레이터에게도 금지 — 단계별 기록과 stop-on-failure 를 없앤다); `git add -A`/`git add .`; `git clean`; `rm -rf release`(`release/ClaudePet.iconset/`·`release/icon_1024.png` 는 사용자 소유, 복구 불가); `diag.py` 등 사용자 소유·타인 소유 untracked 파일 접촉; 실제 `~/.claude` 읽기. **`release/` 에 남은 v0.21 아티팩트(`*.zip`, `*.dmg`)는 재사용하지 않는다** — ③~⑥ 가 새로 덮어쓰며, 남아 있는 것을 올리려 해도 `verify_release_artifact.py` 의 소스 해시 검사가 거부한다. 이전 `dist/`·`build/` 출력도 손으로 지우지 않는다(빌드 도구가 관리).

### 8. 이 판정에서 내가 실행하지 않은 것

`git add`(모든 형태)·`git commit`·`git tag`·`git push`·`git clean`·`git stash`·`git reset`/`checkout`/`restore`, `rm -rf`, `./release.sh`(모든 서브커맨드), `./build_app.sh`, 테스트 스위트 재실행(Verifier 의 재실행 기록을 원본 출력과 대조하는 것으로 대신함). untracked 파일은 열지도 바꾸지도 않았고(`docs-design/` 의 타인 QA 캡처 포함), `~/.claude` 를 읽지 않았으며 `~/.claude_pet`·`~/.claude_pet.json` 에 쓰지 않았다. 스크래치는 세션 scratchpad 에만 남겼다.
