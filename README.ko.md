# 🐱 Claude Pet (Patch 에디션)

[English](README.md) · **한국어** · [日本語](README.ja.md) · [Español](README.es.md)

Codex Pets처럼 화면에 떠 있는 Patch가 Claude 토큰 사용량을 지켜보는 데스크톱 펫.
macOS 네이티브(AppKit) 렌더링 — 창 프레임/배경/잔상 없음.

> 🧪 현재 **v0.1 (beta)** — 실험 단계라 동작/표기가 바뀔 수 있어요.

![Patch](preview.png)

## 다운로드 & 설치 (권장)

**Python 설치 불필요** — 앱에 내장돼 있고 **Apple 공증**되어 Gatekeeper 경고 없이 바로 열립니다.

1. [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest)에서 `ClaudePet.zip` 다운로드 — **Intel Mac**은 `ClaudePet-universal.zip`을 받으세요
2. 압축 해제 → `ClaudePet.app`을 **응용 프로그램** 폴더로 이동 → 더블클릭
3. macOS 12+ (Apple Silicon; Intel은 universal zip 사용)

### 권한 (첫 실행 시)

펫은 **`~/.claude`(사용량 로그)와 키체인의 OAuth 토큰만** 읽습니다. 그 외 폴더(사진·다운로드·문서 등)는 건드리지 않아요. 첫 실행 때 딱 이것만 뜹니다:

| 팝업 | 무엇 | 누를 것 |
|---|---|---|
| **키체인** — "Claude Code-credentials" | 정확 모드가 서버 계산 %를 가져올 OAuth 토큰 | **항상 허용** |
| **"다른 앱의 데이터"** — `~/.claude` | 사용량 로그 읽기 | **허용** |

- 토큰은 **실행당 1회만** 조회하고, 서명된 앱이라 결정이 영구 저장돼 다시 안 물어봅니다.
- **사진/다운로드/음악/데스크탑/문서/iCloud/네트워크볼륨 팝업은 뜨지 않습니다.** (과거엔 `claude` CLI를 자식으로 실행해 그 스캔이 앱에 귀속되며 떴지만, 지금은 CLI 호출을 기본 OFF로 막음)
  - 모델별(Fable) 줄을 CLI로 보충받고 싶으면 `CLAUDE_PET_USE_CLI=1`로 켤 수 있으나, 그러면 폴더 팝업이 다시 뜹니다.

### 업데이트

앱이 시작할 때 GitHub 최신 릴리즈를 확인해, 새 버전이 있으면 **우클릭 → "⬆︎ 새 버전 설치"** 로 다운로드·교체·재실행까지 자동 처리합니다.

---

## 직접 빌드 (개발자용)

소스에서 빌드하려면 **framework 빌드 파이썬**이 필요합니다:

- **Homebrew**: `brew install python@3.13` (framework 빌드라 그대로 됨)
- **pyenv**: 반드시 `--enable-framework`로 설치
  ```bash
  PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.13.14 && pyenv global 3.13.14
  ```
  > ⚠️ 시스템 파이썬(`/usr/bin/python3`, 3.9)은 pyobjc 빌드가 깨지니 쓰지 마세요.

```bash
./build_app.sh install     # 로컬 빌드+서명 → /Applications 설치+실행
python3 claude_pet.py --report   # GUI 없이 터미널 리포트만

./release.sh               # 배포용 자체포함 앱(py2app)+Developer ID 서명+공증+zip
```
`release.sh`는 최초 1회 공증 자격증명 등록이 필요합니다(스크립트 상단 주석 참고).

## 행동

- **평소엔 가만히** — 첫 프레임 정지, 25초에 한 번 숨쉬기/깜빡임만
- **마우스가 가까이 가면** 손 흔들며 인사 (쿨다운 30초)
- **잡고 끌면** 끄는 방향으로 달리기, **더블클릭** 점프 + **사용량 즉시 갱신**(캐시 무시 재조회)
- **토큰 소비 급증하면** 몸에 경고색 펄스 + 패닉 표정 + 게이지에 ▲급증:
  - 🔴 세션 급증 / 🟣 모델(Fable/Opus) 급증 / 🟠 주간 급증
- **세션 리셋 감지하면** 신나서 점프

## 조작

- **스크롤 (펫 위에서)**: 크기 조절 (0.3×~2.0×, 저장됨. 기본 0.5×)
- **클릭 (⌄ 버튼)**: 게이지 패널 접기/펴기
- **드래그**: 이동 (위치 저장)
- **우클릭**: 메뉴 — 설정 / 접기 / 크기 원래대로 / 종료

## 게이지 3종 (구독 모드)

세션(5h) / 주간 전체 / 주간 모델별 — 각각 %, 남은 토큰, 리셋 카운트다운.
모델별 게이지는 로그에서 상위 티어(fable → mythos → opus 순)를 **자동 감지**.

## 설정 (우클릭 → 설정)

- **데이터 소스**: 구독(Claude Code 로그) / API(Admin API 비용 — 오늘·이번 달·월 예산 게이지)
- **🔧 보정 (제일 중요!)**: 한도 토큰 수는 Anthropic 비공개라 아무도 모름.
  대신 Claude 앱 **설정 > 사용량**에 표시된 %를 그대로 입력하고 저장하면
  `한도 = 현재 사용량 ÷ %`로 자동 역산. 입력한 항목만 반영됨.
- **주간 리셋 요일/시각**: 앱에 "(토) 오후 8:00에 재설정"이라 나오면 토요일/20시로 설정. 미설정 시 롤링 7일.
- 모델 키워드(auto 권장), 급증 민감도, 마우스 인사 on/off, Admin API 키, 월 예산

모든 설정·크기·위치는 `~/.claude_pet.json`에 저장.

## 한계 (솔직하게)

- 데이터는 Claude Code 로컬 로그 기준 — 웹/데스크톱 채팅 사용량은 미포함. 그래서 앱 %보다 낮게 나올 수 있고, 보정을 주기적으로 다시 해주면 정확해짐.
- Admin API 비용은 Console 조직 것이며 구독 한도와 별개.
- Admin API 키는 `~/.claude_pet.json`에 평문 저장되니 개인 기기에서만 사용 권장.
