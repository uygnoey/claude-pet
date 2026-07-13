# 🐱 Claude Pet (Patch 에디션)

Codex Pets처럼 화면에 떠 있는 Patch가 Claude 토큰 사용량을 지켜보는 데스크톱 펫.
macOS 네이티브(AppKit) 렌더링 — 창 프레임/배경/잔상 없음.

## 요구사항 (파이썬)

GUI 펫이 화면에 뜨려면 **framework 빌드 파이썬**이 필요합니다. 다음 중 하나면 OK:

- **Homebrew**: `brew install python@3.13` (framework 빌드라 그대로 됨)
- **pyenv**: 반드시 `--enable-framework`로 설치
  ```bash
  brew install pyenv
  PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.13.14
  pyenv global 3.13.14
  ```

> ⚠️ macOS **시스템 파이썬(`/usr/bin/python3`, 3.9)** 은 pyobjc 설치가 깨지니 쓰지 마세요.
> `build_app.sh`는 실행 시 `pyenv shim → Homebrew → 시스템` 순으로 AppKit 되는 파이썬을 자동으로 찾습니다.
> pyenv 일반 빌드(framework 아님)는 터미널 `--report`만 되고 GUI는 안 뜹니다.

## 설치 & 실행

**앱으로 (추천)**:
```bash
./build_app.sh        # ClaudePet.app 생성 (맥에서 직접 빌드)
open ClaudePet.app    # 이후엔 더블클릭
```

**터미널로**:
```bash
python3 -m pip install pyobjc-framework-Cocoa   # 최초 1회 (framework 파이썬에)
python3 claude_pet.py                            # 펫 실행
python3 claude_pet.py --report                   # 터미널 리포트만
```

> 💡 **첫 실행 시 키체인 허용 창**이 뜹니다("Claude Code-credentials" 접근).
> 정확 모드가 Claude Code의 OAuth 토큰을 읽어 서버 계산 %를 가져오기 때문이며,
> **"항상 허용"** 을 누르면 다음부터 안 물어봅니다. (토큰은 실행당 1회만 조회)

## 행동

- **평소엔 가만히** — 첫 프레임 정지, 25초에 한 번 숨쉬기/깜빡임만
- **마우스가 가까이 가면** 손 흔들며 인사 (쿨다운 30초)
- **잡고 끌면** 끄는 방향으로 달리기, **더블클릭** 점프
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
