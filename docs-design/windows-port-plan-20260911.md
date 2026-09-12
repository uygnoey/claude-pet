# ClaudePet Windows 이식 계획 (2026-09-11)

> 사용자 결정(2026-09-11): *"윈도우버전도 개발 고려해봐 실행 조건은 mac과 100% 동일해야해!"* → *"1은 일단 서명 없이 시작하고,
> 2는 전체 계획 문서 먼저 보고 시작하자 그리고 workspace 만들어서 시작해 기존 코드 영향 없게"*.
>
> 상태: **2단계 착수 (2026-09-12). 사용자 결정: 트레이 아이콘 유지, 릴리즈 자산 이름 `claude-pet-win.zip`.** 워크스페이스 `/Users/yeongyu/claude-pet-windows` (git worktree, 브랜치 `windows`, `main` 과 분리).
> `main` 의 파일은 이 계획으로 한 줄도 바뀌지 않는다.

## 0. 한 줄 요약

`claude_pet.py` 는 AppKit 을 `run_gui()` 안에서만 늦게 import 하므로 **AppKit 없이도 import 된다**(이 Mac 에서 AppKit 을 막고
확인). Windows 실기에서는 최상단의 `import fcntl`(POSIX 전용)과 `ctypes.CDLL(None)`(Windows 는 TypeError) 두 곳이 import 를
막았는데, 둘 다 기존 파일을 고치지 않고 `windows/compat/fcntl.py`(msvcrt 기반 flock)와 진입점의 import 시 CDLL 래핑으로 우회했다
(`_RENAMEATX_NP = None` 폴백을 타게 함). 따라서 Windows 판은 기존 파일을 고치지 않고, 새 진입점 `windows/claude_pet_win.py` 가 `claude_pet` 을 import 해
추정기·자율 이동 상태기계·업데이트 판단·설정·다국어를 그대로 쓰고, **창·그리기·메뉴·설정 창·트레이·시딩 게시·업데이트 교체**만
Windows 용으로 새로 쓴다. UI 툴킷은 PySide6(Qt), 패키징은 PyInstaller. 서명은 사용자 결정대로 보류한다.

## 1. 목표와 원칙

- **실행 조건 동일**: Python 설치 불필요(자체 포함), 작업표시줄 버튼 없이 항상 위에 떠 있는 투명 창, Claude Code 로그로 추정,
  OAuth 토큰으로 정확 모드, 기본 펫 4종 자동 시딩(덮어쓰기 없음), GitHub 릴리즈에서 한 번에 최신으로 업데이트, 우클릭 메뉴·설정 창,
  모니터 전체 산책·따라다니기·모니터 간 점프, 시스템 애니메이션 줄이기 존중. **유일한 예외는 코드 서명**: 무서명이라 첫 실행에
  SmartScreen 경고("추가 정보 → 실행")가 뜬다. 서명(EV/OV/Azure Trusted Signing)은 사용자 결정 시 별도 단계로 붙인다.
- **기존 코드 무영향**: `main` 브랜치와 `claude_pet.py`, `release.sh`, `build_app.sh`, `tests/` 는 건드리지 않는다. Windows 코드는
  `windows/` 아래에만 둔다. 나중에 두 판이 공유해야 할 상수(업데이트 자산 표 등)를 `claude_pet.py` 에 넣는 것은 **별도 승인** 뒤 한다.
- **같은 프로세스**: AGENTS.md 의 역할 분리(Developer/Verifier/Reviewer/Coordinator), red-before-green, §5 근거 기준을 Windows
  게이트에도 그대로 적용한다. Windows 전용 테스트는 `windows/tests/` 에 두고 Verifier 가 소유한다.

## 2. 무엇을 재사용하고 무엇을 새로 쓰는가

| 구분 | 항목 | 근거 |
|---|---|---|
| 그대로 재사용 | 추정기 `parse_usage_entries`·`compute_usage`·`_weigh_usage`·창(세션/주간/모델)·spike | 순수 Python, 로그 형식 동일 |
| 그대로 재사용 | `Roamer`·`RoamDisplay`·`roam_summary`·`roam_frame`·`ROAM_DEFAULTS` | AppKit 무관(테스트가 이미 증명) |
| 그대로 재사용 | `check_github_update`·`poll_github_update`·`_ver_tuple`·`_zip_members_are_safe`·`select_update_asset` 의 형태 | 최신 릴리즈 하나만 보고 바로 감 |
| 그대로 재사용 | `TR`/`t()` 다국어, `CONFIG_PATH`·설정 병합, `prepare_settings_config`·`plan_settings_save`, 온보딩 판정 | 파일·문자열 처리뿐 |
| Windows 용 새로 작성 | 창(프레임리스·투명·항상 위·작업표시줄 제외), 스프라이트 그리기(webp/png), 게이지 필, 드래그/클릭/호버, 우클릭 메뉴, 설정 창, 트레이 아이콘 | AppKit 대응부 |
| Windows 용 새로 작성 | 토큰 읽기(`.credentials.json` 파일만; Keychain 없음), 시딩 게시 프리미티브(`os.link` + `MoveFileEx` 덮어쓰기 금지), 업데이트 잠금(`msvcrt.locking`), 교체 스크립트(PowerShell, 롤백 포함), 애니메이션 줄이기 읽기(`SPI_GETCLIENTAREAANIMATION`), 멀티모니터 `RoamScreen` 생성(QScreen, y 축 뒤집기·DPI 배율) | OS 프리미티브가 다름 |
| 확인됨 (Phase 0, 2026-09-11 실기) | 로그 경로 `%USERPROFILE%\.claude\projects` 존재(JSONL 702개), 자격 증명 파일 `%USERPROFILE%\.claude\.credentials.json` 존재(471 B) → 추정·정확 모드 모두 가능 | Windows 실기(Remote Control 세션) 조사 |

## 2.1 Windows 실기 조사 결과 (2026-09-11, Remote Control 세션, 읽기 전용)

- OS: Windows 11 Pro (NT 10.0.26200), AMD64. 모니터 1대 2560×1440, 96 DPI(100%), 작업표시줄 하단 48 px(WorkingArea 2560×1392). 창 애니메이션 켜짐(MinAnimate=1).
- **Python 없음**(Store 별칭 stub 뿐) → 개발용으로 python.org 3.13 설치가 선행. 배포본은 PyInstaller 가 Python 을 포함하므로 사용자에겐 불필요.
- Claude Code 2.1.268, native 설치(`~/.local/bin/claude.exe`). `.claude/projects` JSONL 702개, `.credentials.json` 471 B(내용 미열람).
- `.claude_pet.json`·`.claude_pet` 없음(클린). git 2.53, PowerShell 7.6, 디스크 여유 352 GiB.
- 시사점: 로그 702개 전체 스캔의 초기 비용은 macOS 와 같은 mtime 프리필터가 그대로 적용된다. 다중 모니터 실측은 이 머신에서는 불가(모니터 1대) — 점프는 합성 화면 테스트로만 검증.
- 1차 시험(Python 3.13 설치 뒤, 저장소 무변경): `python claude_pet.py --report` 0.54초 정상, 정확 모드(토큰 파일) 정상, `LOG_DIRS` 는 `C:\Users\<u>/.claude/projects` 로 풀림(구분자 혼용은 Windows API 가 허용).
  발견: (a) `import fcntl`·`CDLL(None)` import 블로커 → 호환 계층으로 해결(§0). (b) `select_update_asset` 이 `platform.machine()=='AMD64'` 를 모르는 아키텍처로 거부 → 3단계에서 Windows 자산 표에 AMD64/ARM64 매핑. (c) 추정기 주간 0.6% vs 서버 87% 불일치와 모델 라벨(Opus/Fable) 차이는 Windows 문제가 아니라 추정기 범위(다른 기기 사용량은 서버에만 집계, 자동 모델 감지) 문제로 보이며 별도 과제.
  후속 검토(별도 승인): `claude_pet.py` 의 `_load_renameatx_np` except 절에 `TypeError` 를 더하면 Windows 에서 호환 래핑 하나가 필요 없어진다(macOS 동작 불변). fcntl 은 호환 모듈로 계속 대체.

## 2.2 1단계 시제품 실기 라운드에서 확정된 것 (2026-09-12)

- v1: 투명 창·게이지·정확 모드·우클릭·접기 버튼·드래그 저장/복원 모두 macOS 판과 같은 동작. 트레이 아이콘은 Windows 11 이 `^` 안에
  숨기므로 README 에 고정 안내(작업표시줄 버튼이 없어 트레이가 진입로).
- v2: `_system_lang()` 이 Foundation 에만 기대 Windows 에선 항상 en → 진입점에서 `GetUserDefaultUILanguage()` 로 ko/ja/es/en 을 골라
  `set_lang()`(설정 파일의 lang 이 있으면 그것이 우선). relayout 은 paint 밖(tick), 새로고침 결과는 워커가 `_pending` 에만 두고 tick 이 반영.
- v3→v4: 한국어에서 서브텍스트가 필 폭을 넘쳐 받침이 잘림(Windows 모노 글꼴 + 한글 대체 글꼴이 macOS 보다 넓음). 규칙: 후보 문자열
  (전체 → '사용' 생략 → 카운트다운만 → % 만; 추정 모드는 남음·리셋 조합)을 긴 것부터 시도하되, 버리기 전에 그 후보를 0.85 배까지만
  줄여 보고, 마지막엔 말줄임. 세로는 drawText(rect, AlignVCenter) 로 실제 글꼴 높이 기준. 0.68 배 축소는 한글이 뭉개져 금지.
- v5: 추정 모드 후보 순서는 전체 → '남음 X · 짧은 리셋' → **'남음 X'(라벨 유지)** → '짧은 리셋' → '%'. 폭이 모자랄 때 카운트다운보다
  라벨 붙은 잔여량을 우선한다: macOS 판과 숫자의 뜻이 같아야 하고(라벨 없는 숫자는 남은 양/쓴 양이 모호), 추정 모드의 주간·모델 행 리셋은
  rolling 창이라 '-' 인 경우가 많다. '남음' 없는 숫자+카운트다운 후보는 넣지 않는다. 실측(실제 플랫폼): 라벨 유지 후보는 세 행 모두 x1.5
  이상 여유, 스파이크 접두 최악도 x1.107 로 제 크기.
- 알려진 사항(양쪽 공통): 추정 모드에서 주간·모델 행의 리셋이 없으면(rolling 창) `fmt_reset` 이 '-' 를 돌려 `… · -` 꼬리가 남는다.
  macOS 판도 같은 문자열을 그리므로 Windows 판은 1단계에서 그대로 두었다(동등성 우선). 두 판을 함께 고치는 것은 별도 과제(`claude_pet.py`
  의 문자열 조립을 바꾸는 일이라 승인 필요).
- 1단계 마감(2026-09-12, v5): Windows 실기에서 정확 모드 회귀 없음, 추정 모드 세 행 '남음' 유지(제 크기), stderr 비어 있음, 위치 복원.
- 측정 원칙: 글꼴 폭·후보 선택은 **실제 플랫폼**에서만 잰다(offscreen 은 시스템 글꼴을 못 잡아 한글 폭을 과대 측정 — 실제 화면과 어긋난
  사례 있음). Mac offscreen 렌더는 배치 확인용일 뿐 Windows 폭 판단 근거가 아니다.
- 프로세스: venv 의 `Scripts\pythonw.exe` 는 런처라 실제 인터프리터가 다른 PID 로 뜬다(PID 2개). 3단계 업데이트 재시작·종료 로직은
  PID 가 아니라 창 클래스(`Qt…Window…`)나 뮤텍스로 인스턴스를 찾는다. PyInstaller exe 에는 런처가 없다.
- 전송: Remote Control 메시지는 약 1.1만 자를 넘기면 잘린다 → zip base64 를 ~6천 자 조각으로 나눠 조각별 길이·SHA256 으로 검증.

## 3. 단계

| 단계 | 내용 | 산출물 | 기간 |
|---|---|---|---|
| 0. 준비 | 워크스페이스(완료), Windows 실기 확보(완료: Remote Control), 로그·자격 증명 경로 확인(완료), Python 설치, PySide6·Pillow·PyInstaller 버전 고정 | `windows/README.md`, `windows/requirements.txt` | 1~2일 |
| 1. 시제품 | 투명 창에 펫 애니메이션 + 게이지 필, 로그 추정치 표시, 드래그·더블클릭·호버 인사, 우클릭 메뉴 최소(종료·접기), 소스로 실행 | `windows/claude_pet_win.py` 1차 | 1주 |
| 2. 기능 동등 | 정확 모드(토큰 파일), 설정 창(% 보정·고급 한도·언어·펫), 요약 필·접기, 자율 이동 어댑터(멀티모니터·점프·애니메이션 줄이기), 스파이크 표시, 온보딩 안내, 트레이 | 기능 완성본 | 1~2주 |
| 3. 배포·업데이트·시딩 | PyInstaller onedir → `claude-pet-win.zip`, 시딩(무덮어쓰기), 업데이트 확인(1시간 주기·메뉴 즉시 확인)과 교체·재실행·롤백, 제거 메뉴, GitHub Actions(windows-latest)로 빌드·테스트 | 자동 빌드 zip, CI | 1주 |
| 4. 검증 게이트 | 순수 테스트 공유 실행, Windows 전용 게이트(창·설치 트랜잭션·업데이트 교체·시딩), 역할 분리 기록 | `windows/tests/`, 검증·리뷰 기록 | 병행 |
| 5. 서명 (보류) | 인증서 결정 시 signtool/Trusted Signing 단계 추가, SmartScreen 경고 제거 | — | 사용자 결정 뒤 |

첫 화면(1단계)까지는 1주, 기능 동등(3단계 끝)까지는 3~5주를 본다. Windows 실기가 없으면 CI(offscreen Qt)로 단위·스모크만
가능하고 실제 창·DPI·다중 모니터는 검증되지 않는다 — 실기 확보가 일정의 전제다.

## 4. 실행 조건 동등성 표

| 조건 | macOS (현재) | Windows (계획) | 동등 |
|---|---|---|---|
| Python 없이 실행 | py2app 번들 | PyInstaller onedir zip | ○ |
| 첫 실행 경고 없음 | Developer ID + 공증 | 무서명 → SmartScreen 경고 | **× (보류)** |
| Dock/작업표시줄 없음, 항상 위, 투명 | LSUIElement + NSWindow | Qt Tool 창 + 트레이 아이콘 | ○ |
| 로그 추정 | `~/.claude/projects` | `%USERPROFILE%\.claude\projects` | ○ |
| 정확 모드 | 파일 → security → Keychain | 파일 | ○ (확인 필요) |
| 최신 버전으로 한 번에 업데이트 | zip 검증 → 교체 → 재실행 | 같은 흐름, PowerShell 교체 | ○ |
| 기본 펫 시딩 | link + RENAME_EXCL | link + MoveFileEx(무덮어쓰기) | ○ |
| 모니터 전체·간 이동, 애니메이션 줄이기 | NSScreen, Reduce Motion | QScreen, 시스템 애니메이션 설정 | ○ |
| 설정 파일 | `~/.claude_pet.json` | `%USERPROFILE%\.claude_pet.json` | ○ |

## 5. 기술 선택

- **PySide6**: 프레임리스·반투명·항상 위 창, QPainter 로 스프라이트·게이지 그리기, QMenu·QDialog·QSystemTrayIcon, QScreen 으로
  모니터 목록(`RoamScreen` 의 id/frame/bounds 로 변환). 순수 Win32 보다 작업량이 절반 이하.
- **Pillow**: 펫 스프라이트시트(webp) 디코딩(macOS 는 NSImage 가 내장 처리).
- **PyInstaller onedir**: 실행 파일 + 의존성 폴더를 zip 으로. 파일 하나(onefile)는 백신 오탐과 시작 지연이 커서 피한다.
- **좌표계**: Roamer 는 창 중심 좌표만 알고 축 방향을 가정하지 않는다. 어댑터가 Qt 의 y-down 전역 좌표를 그대로 쓰되 `RoamScreen.frame/bounds`
  를 같은 축으로 만들면 된다(축 뒤집기 불필요, 부호만 일관).
- **업데이트 자산**: 릴리즈에 `claude-pet-win.zip` 을 추가한다. 선택 표는 우선 `windows/` 안에 두고, macOS 게시 게이트(정확히 4개 자산
  검사)는 건드리지 않는다 — Windows zip 은 CI 가 게시 뒤 `gh release upload` 로 덧붙인다. 표를 `claude_pet.py` 로 합치는 것은 별도 승인.

## 6. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| SmartScreen 경고(무서명) | README 에 "추가 정보 → 실행" 안내. 서명은 5단계에서 |
| 백신 오탐(PyInstaller) | onedir 사용, 릴리즈마다 VirusTotal 확인, 오탐 신고 절차 문서화 |
| 투명 창/DPI 배율 | Qt 고DPI 정책 고정, 모니터별 배율에서 창 크기·좌표 검증(실기) |
| Claude Code 자격 증명 위치 | 0단계에서 실기 확인, 없으면 추정 모드로 동작(현재 macOS 와 같은 폴백) |
| Windows 실기 부재 | CI offscreen 스모크 + 사용자 실기 확인 세션 |
| 두 판의 규칙 드리프트 | 순수 코드는 import 공유라 드리프트 없음; OS 프리미티브만 Windows 판에 존재 |

## 7. 검증 방식

- 순수 테스트(추정기·Roamer·업데이트 판단·설정)는 `tests/` 의 것을 Windows CI 에서 그대로 실행한다(zsh·codesign 에 묶인 8개 모듈은 제외).
- Windows 전용 게이트: 창 어댑터(offscreen), 시딩 게시(무덮어쓰기·부분 게시 없음), 업데이트 교체 트랜잭션(롤백), 잠금, 자산 선택.
- 실기 스모크: 첫 실행·트레이·우클릭·드래그·다중 모니터 점프·업데이트 한 번에.

## 8. GO 시 첫 작업(1단계 착수 항목)

1. `windows/requirements.txt`, `windows/README.md`(실행·빌드 방법, SmartScreen 안내).
2. `windows/claude_pet_win.py`: `import claude_pet`, 창·타이머·스프라이트·게이지·드래그·호버·우클릭(접기/종료).
3. `windows/tests/test_win_adapter.py`(Verifier): offscreen 창 생성, 게이지 배치, RoamScreen 변환.
4. CI 워크플로 초안(`.github/workflows/windows.yml`, 브랜치 `windows` 에만).

## 9. 사용자에게 필요한 결정

- ~~Windows 실기 또는 VM 을 쓸 수 있는지~~ → Remote Control 로 연결된 Windows 11 실기 사용(모니터 1대).
- ~~트레이 아이콘을 둘지~~ → 유지(사용자 결정 2026-09-12).
- ~~릴리즈 자산 이름~~ → `claude-pet-win.zip`(사용자 결정 2026-09-12: "그냥 win으로" → 이어서 "claude-pet-win").


## UI 동일성 감사 (2026-09-12)

사용자 요구: **"UI는 맥과 windows 100% 동일해야한다!"** (실행 조건 100% 동일 요구에 이어). 두 렌더러를 요소별로
소스 대조한 결과와 조치. 검증 기준은 실기기 나란히 스크린샷이며, Mac offscreen 측정은 한글 폭을 과대평가하므로
폭 판단에는 쓰지 않는다(§2.2 원칙).

| 요소 | macOS 판 | Windows 판(감사 전) | 조치 |
| --- | --- | --- | --- |
| 필 배경·반경·패딩·행 높이·상태줄 | `PILL_*`, `STATUS_H`, `pill_h()` | 같은 상수 import | 동일 |
| 게이지 막대 | ry+17, 높이 6, 반경 3, 최소 8, `bar_color`/`COL_BAD` | 동일 | 동일 |
| 서브텍스트 맞춤 | 문자열 유지, 넘치면 폰트만 `max(0.68, avail/w)` 배, 말줄임 없음, 줄 위 = ry | 후보 문자열 5종 + 0.85 하한 + 말줄임, 세로 가운데 | **macOS 규칙으로 교체** |
| 추정 필 문자열 | `{pct}% · 남음 X · {리셋}` | 후보 문자열(짧은 리셋 등) | 동일 문자열 |
| 정확 필 문자열 | `{pct}% 사용 · {리셋}` | 후보 문자열 | 동일 문자열 |
| API 모드 필 | 오늘/이달 금액, 예산 막대 또는 안내 | "API" 한 줄 | **이식** |
| 폰트 크기·역할 | mono 12b/15b/9.5/9.5b/8.5/10/11b | 동일 | 동일 |
| 폰트 굵기 | weight 0.4(≈ semibold 600) | bold 700 | DemiBold(600) 로 |
| 폰트 패밀리 | SF Mono(+Apple SD Gothic Neo) | Cascadia Mono/Consolas(+맑은 고딕) | **결정 필요** — 아래 |
| 접기 버튼 ⌄ | 원 r13, 테두리 #2E2E33, 꺾쇠 2.0 round | 동일 | 동일 |
| 급증 오버레이 | SourceAtop, pulse 0.22+0.18·sin | 동일 | 동일 |
| 펫 그리기 | drawInRect(보간) | SmoothPixmapTransform | 동일 |
| 요약 필 | 반경 h/2, F_SUMMARY, `roam_fit_text` 말줄임 | 동일 | 동일(폭은 글꼴 폭에 따름: 실기기 184, Mac offscreen 229) |
| 우클릭 메뉴 | [설치/로그인] [업데이트] 설정… · 접기/펴기 · 돌아다니기✓ · 크기 원래대로 · 펫▸(+펫 추가…) · ─ · 제거 · 종료 · ─ · 버전 · 업데이트 확인… | 접기/펴기 · 펫▸ · 돌아다니기 · ─ · 버전 · 종료 | **같은 항목·순서로 재구성** |
| 스크롤 휠 크기 조절 | `scrollingDeltaY × 0.004`, 0.3~2.0, scale 저장 | 없음 | **이식** (`wheelEvent`) |
| 설정 창 | NSPanel 420×612, 고급 한도 500×190, `adv_value` 계약, 저장 = `plan_settings_save`/`apply_settings_plan` | 없음 | **QDialog 로 같은 좌표에 이식** (y 축만 뒤집음) |
| 제거 | 확인 창(취소가 기본) → 설정·잠금·로그 삭제 → 앱 번들 삭제 예약 | 없음 | 확인 창·파일 삭제 이식; **앱 폴더 삭제는 3단계** |
| 업데이트 확인… | 확인 → 새 버전이면 즉시 설치·재실행 | 없음 | 확인·메시지 이식; **설치는 3단계** (지금은 릴리즈 페이지를 연다) |
| Claude Code 설치/로그인 | Terminal.app 에서 install.sh → `claude auth login` | 없음 | PowerShell 새 콘솔에서 install.ps1 → `claude auth login` |
| 트레이 아이콘 | 없음 | 있음 | 유지 (사용자 결정 2026-09-11) |

**폰트 — 유일하게 남은 결정.** macOS 판은 시스템 모노 글꼴(SF Mono, 한글은 Apple SD Gothic Neo 대체)을 쓰고,
이 글꼴은 Apple 기기 밖으로 배포할 수 없다. 글리프까지 같으려면 두 플랫폼이 **같은 글꼴을 번들**해야 한다(예:
D2Coding, OFL). 그러면 macOS 앱의 글꼴이 바뀌므로 macOS 릴리즈가 필요하다. 번들하지 않으면 Windows 는
`MONO_FAMILIES` 순서(SF Mono 가 있으면 그것, 없으면 Cascadia Mono → Consolas)로 가장 비슷한 것을 쓰고, 글리프 모양과
한글 폭만 다르다 — 그 밖의 모든 요소는 위 표대로 같다. 어느 쪽이든 `MONO_FAMILIES` 한 줄로 바꾼다.

**오프스크린 확인(2026-09-12, Mac, `win_parity_smoke.py`)**: 정확·추정·API(키 없음/있음) 필 렌더링, 메뉴 항목 순서
(업데이트 항목 포함), 설정 창 420×612·고급 창 500×190 생성과 `adv_value` 계약(창 없음 → "", 열림 → 입력값, 닫힘 → ""),
scale 0.5→0.6 시 창 크기 변화와 `{"scale": 0.6}` 저장 호출. 실기기 확인은 다음 라운드.
