# ClaudePet v1.1.0 — Windows 실기기 검증 + 빌드 (Windows 측 지시서)

너는 사용자의 Windows PC 에서 도는 검증 세션이다. Mac 쪽 조정자 세션이 이 일을 맡겼다.
**사용자에게 질문하지 마라**(AskUserQuestion 금지). 막히면 보고서에 적고 끝내라.
저장소 파일을 고치거나 커밋·푸시하지 마라(검증만). 사용자 개인 파일(~/.claude_pet, ~/.claude_pet.json,
~/.claude, ~/.codex)을 바꾸거나 지우지 마라 — 읽기만. 설정 저장 테스트는 **임시 설정 파일**로 한다(아래).

## 0. 준비
- 이 워크트리에서: `git fetch origin` 후 `git checkout --detach 4c088dc`(릴리즈 커밋, APP_VERSION 1.1.0). `git log -1 --oneline` 기록.
- Python/PySide6 등은 windows/requirements.txt 대로(이미 깔려 있으면 그대로).

## 1. 자동 테스트 (기록: 명령과 마지막 요약 줄)
- `python -m unittest discover -s tests -v -p "test_server_only_usage.py"`
- `python -m unittest discover -s tests -v -p "test_codex_usage.py"`
- `python -m unittest discover -s tests -v -p "test_token_recovery.py"`
- `python -m unittest discover -s windows/tests -t . -v` (PySide6 있으면 Qt 테스트도 돈다)

## 2. 실제 앱 실행 — 소스로 (사용자 설정을 건드리지 않게)
- 이미 돌고 있는 설치본 ClaudePet 이 있으면 **끄지 말고** 그대로 둔다(둘 다 떠도 된다). 화면에서 구분이 안 되면 보고서에 적어라.
- 설정 파일을 임시로 돌린다: 코어의 `CONFIG_PATH`/`USER_PET_HOME` 을 임시 경로로 바꾼 **스크래치 복사본**(워크트리 밖 %TEMP%) 에서 `windows/claude_pet_win.py` 를 실행하거나, 포트가 지원하는 환경변수가 있으면 그걸 쓴다. 어떤 방법을 썼는지 적어라.
- 확인하고 **스크린샷**(PNG) 으로 남길 것:
  a. 필: Claude 줄(서버 값, ≈ 없음)과 Codex 줄(이 PC 에 Codex 로그인이 있으면). `shot-pill.png`
  b. 설정 창(우클릭 → 설정…): Claude Code / Codex 두 구역, 표시 체크, 게이지 체크, 데이터 소스, 키·예산. 언어를 ko, en, ja, es 로 바꿔 각각 한 장: `shot-settings-ko.png` 등 4장. 글자 잘림·겹침 여부를 적어라.
  c. 우클릭 메뉴 한 장: `shot-menu.png`. Codex 설치/로그인 항목이 보이는지와 그 이유(이 PC 에 codex CLI 나 %USERPROFILE%\.codex 가 있는지) 기록.
  d. 설정에서 Codex "필에 표시" 끄고 저장 → 필에서 Codex 줄이 사라지는지, 다시 켜면 돌아오는지. Claude 게이지에서 "주간" 끄면 주간이 빠지는지. `shot-codex-off.png`, `shot-weekly-off.png`
  e. 앱이 오류 없이 30초 이상 도는지(콘솔 오류 로그가 있으면 첨부).
- 끝나면 소스 실행본을 종료.

## 3. 빌드 (릴리즈 산출물, 서명 없음 — Windows 는 원래 무서명)
- `python windows/build_win.py` 로 `claude-pet-win-setup.exe` 와 `claude-pet-win.zip` 을 만든다(스크립트가 안내하는 방식 그대로).
- `python windows/verify_win_artifact.py --version 1.1.0 <산출물>` (스크립트 사용법대로) 실행, 출력 기록.
- 두 파일의 크기와 SHA256 기록(`Get-FileHash -Algorithm SHA256`).
- 빌드된 앱을 **설치하지 말고** ZIP 을 %TEMP% 에 풀어 그 exe 를 실행해 필이 뜨고 버전이 1.1.0 인지 확인(트레이/우클릭 메뉴의 버전 표시). `shot-built.png`. 확인 뒤 종료.

## 4. 결과 보내기 (Mac 이 받는다, Tailscale)
- 보고서를 `WIN_REPORT.md` 로 쓴다: 위 각 항목의 결과(통과/실패, 관찰), 명령과 출력 요약, 해시, 못 한 것과 이유.
- 업로드: 각 파일을 `curl.exe -T <파일> http://100.97.123.82:8817/<파일이름>` 로 PUT. 보낼 것:
  WIN_REPORT.md, shot-*.png 전부, claude-pet-win-setup.exe, claude-pet-win.zip.
  응답이 `ok` 가 아니면 보고서에 적어라.
- 마지막 줄로 터미널에 `WINTEST-FINISHED` 를 출력해라.
