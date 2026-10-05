# ClaudePet v1.1.0 — Windows 2차 확인 + 최종 빌드

앞서 너가 한 1차 검증(4c088dc)에서 찾은 결함을 고쳤다. **최종 커밋 139669d** 로 다시 확인하고 최종 산출물을 만든다.
규칙은 1차와 같다: 사용자에게 묻지 마라, 저장소를 고치거나 커밋·푸시하지 마라, 사용자 파일은 읽기만.
1차의 스크래치 venv·실행기(run_src.py, run_syn.py)를 그대로 다시 써도 된다.

## 0. 준비
- 이 워크트리에서 `git fetch origin` → `git checkout --detach 139669d` → `git log -1 --oneline` 기록.
- 이전 산출물(release\claude-pet-win.zip, release\claude-pet-win-setup.exe)은 빌드가 다시 만든다.

## 1. 자동 테스트 (1차와 같은 4묶음) + 추가
- 1차의 4개 명령 그대로, 그리고 `python -m unittest discover -s tests -v -p "test_server_value_resilience.py"`. 요약 줄 기록.

## 2. 고친 항목 확인 (소스 실행, 1차와 같은 방식으로 사용자 설정 보호)
a. **ja 설정 창**: 데이터 소스 드롭다운 글자가 잘리지 않는지(`サブスク (ログイン中)`), 두 구역 모두. `shot2-settings-ja.png`. en/ko/es 도 한 장씩 다시: `shot2-settings-en.png` 등.
b. **구역 제목 크기**: "Claude Code"/"Codex" 제목이 일반 라벨과 같은 크기의 굵은 글씨인지(1차에선 더 컸다). 위 스크린샷으로 판단, 폰트 pointSize 도 기록.
c. **Codex 토큰 만료 표시**: 이 PC 의 Codex 토큰은 1차 때 서버가 401 을 줬다. 이제 Codex 줄이 사라지지 않고 "Codex 토큰 만료" 안내 문구가 떠야 한다(지금도 401 이면). `shot2-pill.png`. 401 이 아니면(정상 응답이면) 실제 Codex 줄이 보일 것 — 어느 쪽인지 적어라.
d. **설정 저장 뒤 숫자 유지**: 언어를 바꿔 저장 2~3번 해도 필의 Claude 숫자가 "사용량을 기다리는 중…"으로 바뀌지 않아야 한다(언어 변경은 재조회를 하지만, 429 등 일시 오류여도 직전 값을 유지). 저장 직후와 30초 뒤 `shot2-after-save.png`. 디버그로 `OAUTH_STATUS` 도 기록.
e. 30초 이상 무오류.

## 3. 최종 빌드
- `python windows\build_win.py`, `python windows\verify_win_artifact.py --version 1.1.0 --zip release\claude-pet-win.zip --installer release\claude-pet-win-setup.exe`. 출력·크기·SHA256 기록.
- **빌드본 GUI 확인**: 1차에선 설치본 ClaudePet(v0.26)이 단일 인스턴스 뮤텍스를 쥐어 못 봤다. 이번에는 **설치본을 잠깐 종료**(작업 관리자/Stop-Process 로 그 프로세스만)하고, ZIP 을 %TEMP% 에 풀어 그 exe 를 실행(USERPROFILE 등은 1차처럼 스크래치로 돌려 사용자 설정 보호). 필이 뜨고 우클릭 메뉴에 `ClaudePet v1.1.0` 이 보이는지 `shot2-built.png`. 확인 뒤 빌드본을 끄고, **설치본을 원래대로 다시 실행**해라(설치 경로의 ClaudePet.exe). 다시 떴는지 기록. 풀어 둔 폴더는 지운다.

## 4. 결과 보내기
- `WIN_REPORT2.md` 작성(각 항목 통과/실패, 관찰, 명령·출력 요약, 해시, 못 한 것).
- `curl.exe -T <파일> http://100.97.123.82:8817/<파일이름>` 로 업로드: WIN_REPORT2.md, shot2-*.png, release\claude-pet-win-setup.exe, release\claude-pet-win.zip.
- 마지막에 `WINTEST2-FINISHED` 출력.
