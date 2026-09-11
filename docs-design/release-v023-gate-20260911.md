# ClaudePet v0.23 — 실행 게이트 기록 (2026-09-11)

## v0.23 릴리즈 — 실행 게이트(AGENTS.md §6) 판정: GREEN

- 판정자: **coordinator-v023** (독립 Coordinator. 이 릴리즈에서 Developer·Verifier·Reviewer·Release operator 어느 역할도 보유하지 않았고, 저장소의 어떤 파일도 편집하지 않았으며, 커밋·태그·푸시를 하지 않았다. 아래 근거는 전부 저장소 루트 `/Users/yeongyu/claude-pet` 에서 읽기 전용 명령으로 직접 확인한 것이다.)
- 측정 창: **2026-09-11T02:12:37Z → 2026-09-11T02:17:12Z (UTC)**. 창의 시작과 끝 모두 `git rev-parse HEAD` = `81619b3e305d7c45e3aec02ba13d3becd1dee6f3`, 브랜치 `main`, `git status --porcelain` 의 tracked 항목은 ` M docs-design/release-v023-verification-20260911.md` 하나뿐(나머지 19줄은 전부 `??`: 사용자 소유 `diag.py`·`release/ClaudePet.iconset/`·`release/icon_1024.png` 와 이전 작업의 `docs-design/` 캡처·기록 16개).
- 판정 대상: 릴리즈 커밋 **81619b3e305d7c45e3aec02ba13d3becd1dee6f3** ("release: ClaudePet v0.23", 2026-09-11T11:01:58+09:00). 게시된 v0.22(태그 `v0.22` → 태그 객체 `927e7808` → 커밋 `6d47df5e`, `origin/main` 과 동일) 이후 이 릴리즈에 포함된 변경은 `git log v0.22..HEAD` 로 확인한 **커밋 1개**, 즉 이 릴리즈 커밋뿐이다. 변경 파일 11개(`CLAUDE.md`, `RELEASE_NOTES.md`, `claude_pet.py`, `verify_release_artifact.py`, `tests/test_manual_update_transaction.py`, `tests/test_upload_artifact_gate.py`, 신규 `tests/test_update_check_schedule.py`, `tests/test_v022_release_contract.py` → `tests/test_v023_release_contract.py`, 신규 `docs-design/release-v023-verification-20260911.md`, 신규 `docs-design/release-v023-review-20260911.md`)는 커밋 본문의 "Named deliverables staged" 목록과 정확히 일치하고, 사용자 소유 파일은 포함되지 않았다.

### 1. §8 병합 체크리스트 — 릴리즈 커밋에 대해 평가 가능하고, 충족됨

**1-1. trailer 존재·상이(§7, §8 항목 1).** `git log -1 --format=%B 81619b3` 의 trailer 다섯 줄이 서로 다른 당사자를 지명한다: `Developer: Claude (session 55c3dee4-727f-4a94-b960-66540b129014)` / `Verifier: verifier-v023` / `Reviewer: reviewer-v023` / `Coordinator: coordinator-v023` / `Release-Operator: operator-v023`. 동일값 없음. 이 커밋이 존재하므로 항목 1 은 지금 평가 가능하다.

**1-2. Developer–Verifier 분리(§2, §8 항목 2).** `git show 81619b3 --name-status` 와 커밋 본문의 편집 집합이 일치한다: Developer 는 `claude_pet.py`(79줄 변경)·`verify_release_artifact.py`(usage 예시 한 줄 `--expect-version 0.22` → `0.23`)·`RELEASE_NOTES.md`(+5줄)·`CLAUDE.md`(주기 문장 하나: "every 6 hours" → "every hour (never at launch …)"); Verifier 는 `tests/` 다섯 경로와 검증 기록; Reviewer 는 리뷰 기록만. 세 집합은 교집합이 없다. 추정기 심볼(`_weigh_usage`·`parse_usage_entries`·`compute_usage`·`_weekly_window_start`·`spike_info`)과 업데이터·시딩 심볼(`check_github_update`·`poll_github_update`·`install_github_update`·`_ver_tuple`·`select_update_asset`·`validate_update_app`·`_zip_members_are_safe`·`_acquire_update_lock`·`seed_bundled_pet_assets`)의 소스 세그먼트를 AST 로 HEAD~1 과 HEAD 에서 추출해 비교했더니 14개 전부 바이트 동일하다 — 커밋 본문의 "추정기·업데이터 트랜잭션·락 코드는 그대로" 주장이 참이고, 따라서 보정된 한도가 그대로 유효하다는 노트 문장도 참이다. `TR` 네 로케일(en/ko/ja/es)의 키 집합은 서로 같다(누락 0).

**1-3. 핀과 소스 일치.** `shasum -a 256 claude_pet.py` = `57b24a286e92404cb2514c84a35e156f6eaeba29070885bcb2cde04515544a0b` 이고 작업 트리는 HEAD 와 같다(porcelain 에 `claude_pet.py` 없음). 같은 값이 `tests/test_upload_artifact_gate.py` 의 `REVIEWED_APP_SOURCE_SHA256` 과 `tests/test_manual_update_transaction.py` 의 `REVIEWED_APP_SOURCE_SHA256` 에 리터럴로 들어 있다. 두 하니스의 나머지 핀도 현재 바이트와 일치한다: `release.sh` `a5b256867bf3e78314b4bfdec7e9372d6a9ed7304c534b921a62cd9dc2146e23`, `verify_release_artifact.py` `fc0d38f6fb9e05294e279f52da21cc18a2fc731a3b7cc4cb81f8a9012a355c69`, `build_app.sh` `83eca429c7742a3254715a9f8c063289e79553b01a36124c1402c579cea600d6` — 핀 5개 중 5개 일치.

**1-4. 버전.** `grep -n '^APP_VERSION' claude_pet.py` → `APP_VERSION = "0.23"` 리터럴 정확히 하나. `setup.py` 는 그 리터럴을 정규식으로 읽어 `CFBundleVersion` 과 `CFBundleShortVersionString` 양쪽에 넣는다(별도 하드코딩 없음). 태그 `v0.23` 과 `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)` 비교가 맞물리므로 게시 뒤 v0.23 설치본이 자기 자신을 업데이트로 제안하는 일은 없다. (배정문은 `APP_VERSION == "0.22"` 를 기대치로 적었는데, 그것은 직전 릴리즈의 값이다. v0.23 릴리즈 커밋의 올바른 기대치는 `"0.23"` 이고 트리가 그 값을 갖고 있다. 만약 트리가 정말 `"0.22"` 였다면 태그와 상수가 어긋나 NOT GREEN 이었을 것이다.)

**1-5. red-before-green 이 원문으로 기록됨(§3, §8 항목 3).** `docs-design/release-v023-verification-20260911.md` §1 에 리핀·개정 전 실패 출력이 그대로 있다: 업로드 게이트 `Ran 64 tests in 3.597s` / `FAILED (failures=48)`, 수동 트랜잭션 `Ran 0 tests in 0.003s` / `FAILED (errors=8)`, 구 계약 테스트 `Ran 11 tests in 0.257s` / `FAILED (failures=2)`, 일정 테스트 초안 `Ran 6 tests in 0.173s` / `FAILED (failures=1)`; §5 에 스크래치 사본 변이 25/25 RED. Reviewer 기록은 독립 드라이버로 11/11 RED 재현을 적고 있다(리뷰 기록 헤더 01:38:19Z–01:38:25Z).

**1-6. Reviewer 사인오프(§1, §8 항목 4).** `docs-design/release-v023-review-20260911.md` "## Verdict: **PASS** — sign-off for the release commit (§8 item 4)". 작성자 reviewer-v023 은 헤더에 "Held no other role on this release" 를 명시했고 Developer 도 Verifier 도 아니다. 이 파일은 HEAD 에 tracked 이며 작업 트리와 HEAD 가 같다. 비차단 권고 두 건은 커밋 본문에 이월로 기록되어 있다.

**1-7. 전체 스위트 green, Verifier 실행(§8 항목 5).** 준비 트리 실행(검증 기록 §7, 01:25:27Z–01:31:01Z) `Ran 508 tests in 333.600s` / `OK (skipped=7)`; clean 트리 재실행은 아래 항목 2.

**1-8. untracked 파일 무접촉·파괴적 git 명령 없음(§4, §8 항목 6).** 지금 시점 `stat -f '%m %N'`: `diag.py` 1784689621, `release/icon_1024.png` 1783953996, `release/ClaudePet.iconset` 1783953996 — 검증 기록 §8, 리뷰 기록, 릴리즈 커밋 본문, Verifier 의 append 에 적힌 값과 전부 동일. `git reflog --date=iso` 의 최근 항목은 2026-09-09 이후 전부 `commit:` 이고 `reset`·`checkout -f`·`restore`·`clean`·`stash` 항목이 없다.

**1-9. 정량 주장의 §5 충족(§8 항목 7).** 검증 기록의 append 절은 명령·cwd·인터프리터(Python 3.13.7)·환경 변수·집계 단위(unittest 케이스)·파일 집합(19개 모듈과 모듈별 케이스 수, 합 508)·창 시작/끝·측정 시각·분자/분모(508 중 501 통과, 7 스킵, 실패 0, 에러 0)·exit status 를 모두 갖춘다. 커밋 본문의 수치(hunk 10개, 변이 25/25, 세 실행의 Ran/OK 줄, 노트 222자)도 각각 근거 기록을 가리킨다.

### 2. Verifier 의 clean 트리 전체 스위트 재실행 — 기록 존재, 원문 인용 확인 (§6 항목 2)

- 기록 위치: `docs-design/release-v023-verification-20260911.md` 316~481행, 절 제목 "## v0.23 release — execution gate: clean-tree suite re-run at commit 81619b3e305d7c45e3aec02ba13d3becd1dee6f3" (verifier-v023 가 2026-09-11T02:12:05Z 에 append; 파일 mtime 1789092725 = 그 시각).
- 기록의 트리: HEAD `81619b3e…` 을 실행 전(02:02:17Z)과 후(02:08:48Z) 모두 확인, porcelain 은 같은 `??` 19줄뿐 → AGENTS.md §6 정의의 clean 트리. `claude_pet.py`·`RELEASE_NOTES.md`·테스트 모듈 19개의 SHA-256 이 02:02:41Z 와 02:08:48Z 에 21/21 동일.
- 명령: `python3 -m unittest discover -s tests -v`, cwd `/Users/yeongyu/claude-pet`. 창 **2026-09-11T02:02:50Z → 02:08:30Z (UTC)**, exit 0. 결과 줄 원문: **`Ran 508 tests in 339.092s`** / **`OK (skipped=7)`**. 스킵 7개는 전부 `CLAUDEPET_RUN_LIVE_UPDATER_TESTS` / `CLAUDEPET_RUN_LIVE_V020_TO_V021_BOUNDARIES` 미설정 opt-in(test_updater 4, test_v020_boundaries.B3Updater 3)이고 기록에 일곱 케이스가 stderr 동반 줄까지 원문으로 실려 있다 — 준비 트리·Reviewer·Coordinator 실행과 같은 일곱이다.
- 내가 직접 대조한 것: `git diff --numstat HEAD` = `166 0 docs-design/release-v023-verification-20260911.md` 하나뿐; 이 파일의 앞 315행은 `cmp` 로 HEAD 블롭과 바이트 동일(기존 기록은 한 글자도 바뀌지 않고 절 하나가 뒤에 붙었다). tracked 변경이 그 문서 파일 하나뿐이므로 테스트 모듈 19개와 `claude_pet.py` 는 HEAD 의 바이트 그대로이며, Verifier 가 돌린 트리와 지금 트리가 같은 코드다. `unittest.defaultTestLoader.discover('tests')` 를 저장소 루트에서 로드하면 케이스 508개, 로드 에러 0 — 기록의 분모와 일치. 기록의 `claude_pet.py` 해시(`57b24a28…`)와 `RELEASE_NOTES.md` 해시(`6e0b1cdfd988f878252aa12c694dafeb3b522783ffa7575b2f3d9145b716c07b`)는 내가 다시 잰 값과 같다. → **항목 2 GREEN.**

### 3. 릴리즈 노트 확인 (§6 항목 3, CLAUDE.md 2단계 형식)

- `RELEASE_NOTES.md` 맨 위 미게시 섹션 `**v0.23**`: 최상위 불릿 **3개**, 중첩 불릿 **0개**, 불릿 외 문장 없음. 공백 정규화 글자 수 **222**(`- ` 포함; 마커 제외 216) ≤ 450. 불릿마다 정확히 **2문장**. 해시·내부 식별자·소스 경로·줄 번호·테스트 언급·크기/빈도 표현 없음(정규식 스캔 결과 모두 빈 집합). 사용자가 할 행동(우클릭 → "업데이트 확인…")과 결과(내려받아 설치한 뒤 다시 켬), 그리고 다시 보정할 필요가 없다는 점을 적고 있고 구현 서술은 없다.
- 유일한 수치 **"1시간"**: `claude_pet.py` 의 `UPDATE_CHECK_SEC = 3600` 이고, 새로고침 워커의 게이트가 `if not state.get("update") and time.time() - _upd_cache["t"] > UPDATE_CHECK_SEC: _run_update_check()` 로 그 상수와 strict `>` 비교한다 — 릴리즈 커밋 시점 트리에서 감사 가능. "앱을 켤 때 하지 않고" 는 `run_gui()` 가 시작 시 확인 스레드를 띄우지 않고 `_upd_cache["t"] = time.time()` 스탬프만 찍는 것으로 확인했다. 인용 라벨 **"업데이트 확인…"** 은 `TR["ko"]["menu_check_update"]` = `"⬆︎ 업데이트 확인…"` 에서 앞 글리프를 뺀 것과 글자 그대로 일치하고, 그 항목은 `t("menu_check_update"), "checkUpdate:"` 로 우클릭 메뉴에 연결된다. "새 버전이 있으면 우클릭 메뉴 맨 위에 설치 항목" 은 `state.get("update")` 가 참일 때 최상단에 설치 항목을 넣는 기존 분기 그대로다. "중간 버전을 거치지 않고 GitHub의 최신 릴리즈로 바로" 는 `check_github_update()` 가 `/releases/latest` 하나만 요청해 `_ver_tuple(tag) <= _ver_tuple(APP_VERSION)` 로 비교하고 `checkUpdate_` 가 `install_github_update(upd[1], expect_version=upd[0])` 로 설치하는 것에서 확인했다(버전 목록을 훑거나 단계별로 올리는 코드 없음). "한도 계산은 그대로" 는 1-2 의 추정기 심볼 동일성으로 참.
- 게시된 부분 불변: `**v0.22**` 제목부터 EOF 까지의 바이트가 작업 트리·HEAD·HEAD~1 세 곳 모두 동일(SHA-256 `6e284e4fcef476b47de3f0527566c50714bcf39aec9136dace6ab89a5d11d239`), `**v0.23**` 앞의 머리말도 HEAD~1 의 `**v0.22**` 앞과 동일. `git diff HEAD~1 HEAD -- RELEASE_NOTES.md` 는 v0.22 제목 위에 +5줄뿐. (배정문이 든 "10~20초"·`TR["ko"]["menu_roam"]` 는 v0.23 섹션이 아니라 게시된 v0.22 섹션의 수치와 라벨이다. 그 섹션은 frozen 이고 바이트가 그대로이며, 참고로 지금 트리에서도 `ROAM_DEFAULTS["follow_min_s"] = 10.0`·`["follow_max_s"] = 20.0`, `TR["ko"]["menu_roam"] = "화면 돌아다니기"` 로 여전히 감사된다.)
- 미게시 확인: `git tag -l 'v0.23*'` 없음; `git ls-remote --tags origin` 에 v0.23 없음(최신 `refs/tags/v0.22` → `927e7808` → `6d47df5e`); `gh release list --limit 5` 최신은 **ClaudePet v0.22 (Latest, 2026-09-11T00:43:39Z)**. `origin/main` 은 `6d47df5e` 로, 릴리즈 커밋 81619b3 은 아직 푸시되지 않았다. 따라서 v0.23 섹션은 staged 상태이고, 이 게이트는 그것을 그대로 승인한다. → **항목 3 GREEN.**

### 4. Coordinator 사인오프 (§6 항목 4)

위 1~3 을 직접 확인한 결과, **릴리즈 커밋 81619b3e305d7c45e3aec02ba13d3becd1dee6f3 에 대한 AGENTS.md §6 실행 게이트는 GREEN 이다.** coordinator-v023 이 2026-09-11T02:17:12Z (UTC) 에 사인오프한다. 이 사인오프는 "릴리즈할 준비가 됐다"는 인증이지 권한 부여가 아니며(권한 부여는 아래 6 참조), 이 사인오프를 한 나는 §1 에 따라 내가 조율한 이 릴리즈의 오퍼레이터가 될 수 없다.

### 5. 릴리즈 오퍼레이터 지명과 자격 (§6 항목 5)

**operator-v023** 을 지명한다. 이 게이트가 GREEN 이 된 뒤에 새로 생성되는 에이전트로, 이 릴리즈의 어떤 변경에서도 Developer·Verifier·Reviewer·Coordinator 역할을 보유한 적이 없다(보유하지 않은 역할: 네 가지 전부). 자격 배제 목록: Developer 세션(Claude, 55c3dee4-727f-4a94-b960-66540b129014)·verifier-v023·reviewer-v023·coordinator-v023(나)은 모두 이 릴리즈의 오퍼레이터가 될 수 없다. 오퍼레이터는 서명·공증 단계를 실행하는 유일한 당사자이며, 실행한 각 단계의 결과를 이 릴리즈의 기록(`docs-design/release-v023-operator-20260911.md` 같은 새 파일, v0.22 의 `release-v022-operator-20260911.md` 와 같은 꼴)에 남긴다.

### 6. 권한 부여의 상태

사용자의 말 **"23으로 배포해! 그리고 최신버전이 있으면 한방에 최신버전으로 업데이트 가능하게 하고"** (2026-09-11, Developer 세션에서 사용자가 직접 입력; 같은 자리에서 "0.20 버전인데 최신버전이 0.24버전이면 0.24버전으로 한방에 업데이트 가능하게 하라고" 로 명확화)는 그 말을 직접 본 Developer 세션이 릴리즈 커밋 본문에 원문 그대로 옮겨 적었다 — 권한 부여가 사는 자리(변경 설명)에 사용자 본인의 말로 기록된 것이다. 나는 그 문구를 배정문으로 전달받았을 뿐 직접 보지 못했으므로 이 기록은 권한 부여를 새로 만들지도 보증하지도 않는다. 문면 그대로의 범위는 v0.23 릴리즈를 끝까지 마치는 것(build·sign·notarize·universal·dmg·태그·푸시·publish)을 한 단계씩, 각 결과를 기록하고 첫 실패에서 멈추어 수행하는 것이다. 이 권한 부여로도 `all`·`ship`·인자 없는 `./release.sh` 는 [NEVER] 이고, 오퍼레이터 자격 제한은 풀리지 않으며, 권한 부여는 게이트가 통과했다는 발견이 아니다(게이트 통과는 위 4 가 별도로 답한다).

### 7. 오퍼레이터(operator-v023)에게 허용된 단계 — 이 순서, 이 목록 그대로

**시작 전 확인(전부 읽기 전용):** (a) Verifier 의 append 와 이 게이트 기록이 **문서만 바꾸는 커밋 하나**(게이트 기록 커밋)로 81619b3 위에 올라가 있을 것 — `git diff --stat 81619b3..HEAD` 가 `docs-design/*.md` 경로만 나열해야 한다. 그 커밋도 §7 대로 `Developer:`/`Verifier:` 를 서로 다른 당사자로 달고(v0.22 의 `6d47df5` 가 선례), 스테이징은 경로를 이름으로 지정해 `git diff --cached --name-only` 로 읽어 본 뒤 커밋한다. (b) `git rev-parse HEAD` 의 `claude_pet.py` 가 여전히 `57b24a28…` 일 것 — 게이트 기록 커밋은 코드를 바꾸지 않으므로 이 게이트 결과가 그 커밋의 코드에 그대로 적용된다. (c) `git status --porcelain` 에 tracked `M`/`A`/`D` 가 없을 것(`??` 는 정상). (d) `release/` 의 `ClaudePet.zip`·`ClaudePet-universal.zip`·`ClaudePet.dmg`·`ClaudePet-universal.dmg`(2026-09-11 09:38~09:42 KST) 와 `dist/ClaudePet.app`·`dist-universal/ClaudePet.app` 은 **v0.22 아티팩트**다(zip 안의 `Info.plist` 가 `CFBundleShortVersionString` 0.22). **재사용하지 않는다** — ①·⑤·⑥ 이 새로 만들어 덮어쓰며, `verify_release_artifact.py` 의 소스 해시·버전 검사가 어차피 거부한다. 손으로 지우지도 않는다(`release/` 는 사용자 소유 파일이 섞인 디렉터리).

1. **① `./release.sh build`** — py2app 빌드, 서명 없음. 이 릴리즈의 실행 단계이므로 이 게이트가 GREEN 인 지금부터 허용.
2. **② 주석 달린 로컬 태그 `v0.23`** 을 **게이트 기록 커밋**에 만든다(`git tag -a v0.23 -m "ClaudePet v0.23" <게이트 기록 커밋>`). 릴리즈 커밋 81619b3 자체에는 달지 않는다(v0.22 선례: `v0.22^{}` = 게이트 기록 커밋 `6d47df5`, 릴리즈 커밋 `f3acb47` 이 아님). 만든 뒤 `git tag --sort=-v:refname | head -1` 이 `v0.23` 이고 `git rev-parse v0.23^{}` 가 게이트 기록 커밋임을 기록한다.
3. **③ `./release.sh sign`** — [ASK-OP].
4. **④ `./release.sh notarize`** — [ASK-OP].
5. **⑤ `./release.sh universal`** — [ASK-OP]. `universal2` Python 이 없으면 스크립트가 거부한다; 그 거부는 실패로 기록하고 멈춘다.
6. **⑥ `./release.sh dmg`** — [ASK-OP].
7. **⑦ `git push origin main`** — [ASK]. `origin/main` 은 `6d47df5e`(v0.22)이므로 릴리즈 커밋 81619b3 + 게이트 기록 커밋이 올라간다.
8. **⑧ `git push origin v0.23`** — [ASK]. 이 순간부터 설치된 모든 앱이 다음 주기 확인에서 업데이트를 제안받는다; 되돌릴 수 없다.
9. **⑨ `./release.sh publish`** — [ASK]. 업로드 전에 아티팩트 게이트(4개 파일 전부, 아카이브 안전성, 소스 해시, 버전 0.23, 파일명이 정하는 아키텍처, 서명·공증·스테이플)가 돌고, 하나라도 거부하면 업로드하지 않는다. 거부는 실패로 기록하고 멈춘다.

**③~⑥ [ASK-OP] 세 조건:** 사용자 권한 부여가 릴리즈 커밋에 원문으로 기록되어 있고(위 6), 모든 게이트가 이 기록으로 먼저 기록되었고(위 1~5), 실행자는 다른 역할이 없는 operator-v023 이다. **각 단계마다** 명령·UTC 시작/끝·exit status·핵심 출력 줄을 기록하고, **첫 실패에서 멈추어** 유지보수자에게 남은 것을 그대로 넘긴다. 실패 후 다음 단계로 넘어가거나 순서를 바꾸지 않는다.

**[NEVER] 유지:** `./release.sh all`, `./release.sh ship`, 인자 없는 `./release.sh`(오퍼레이터에게도 금지 — 단계별 기록과 stop-on-failure 를 없앤다; `ship` 은 빌드 전에 푸시한다); `git add -A`/`git add .`; `git clean`; `rm -rf release`(`release/ClaudePet.iconset/`·`release/icon_1024.png` 는 사용자 소유, 복구 불가); `diag.py` 등 사용자 소유·타인 소유 untracked 파일 접촉; 실제 `~/.claude` 읽기; `~/.claude_pet/` 쓰기.

### 8. 이 판정에서 내가 실행하지 않은 것

`git add`(모든 형태)·`git commit`·`git tag`·`git push`·`git clean`·`git stash`·`git reset`/`checkout`/`restore`, `rm -rf`, `./release.sh`(모든 서브커맨드), `./build_app.sh`. 저장소 안의 어떤 파일도 만들거나 고치지 않았다(이 기록 텍스트는 배정자에게 돌려주었고, 파일로 두고 커밋하는 것은 배정자의 몫이다). untracked 파일은 `stat` 으로 mtime 만 읽었고 열지도 바꾸지도 않았으며(`docs-design/` 의 타인 QA 캡처 포함), `~/.claude` 를 읽지 않았고 `~/.claude_pet` 에 쓰지 않았다. `release/*.zip` 은 `unzip -p` 로 `Info.plist` 한 항목만 읽었다(추출 없음).

보조로, 판정과 무관하게 같은 명령(`python3 -m unittest discover -s tests -v`, 저장소 루트, HEAD 81619b3)을 세션 스크래치패드 `coordinator-v023-gate-suite.log` 로 02:14:00Z 에 시작해 두었다. 사인오프 시각(02:17:12Z)에는 진행 중(` ... ok` 317개, `FAIL:`/`ERROR:` 0개)이었고 이 판정은 그 실행에 기대지 않는다 — 항목 2 의 근거는 Verifier 의 기록과 위의 대조다.
