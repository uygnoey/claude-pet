# ClaudePet for Windows (개발 중)

macOS 판과 실행 조건을 같게 맞추는 Windows 이식입니다. 설계와 단계는
`docs-design/windows-port-plan-20260911.md` 를 따릅니다. 이 폴더의 코드는 `claude_pet.py` 를 **그대로 import** 해
추정기·자율 이동·업데이트 판단·설정·다국어를 재사용하고, 창·그리기·메뉴·트레이·시딩 게시·업데이트 교체만 Windows 용으로 구현합니다.
`claude_pet.py` 와 macOS 빌드·릴리즈 스크립트는 이 폴더의 코드로 바뀌지 않습니다.

## 소스로 실행 (개발)

```powershell
# python.org Python 3.13 (Microsoft Store 판은 사용하지 않음)
winget install --id Python.Python.3.13 -e --scope user
cd C:\Users\<you>\claude-pet
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r windows\requirements.txt
pythonw windows\claude_pet_win.py           # 펫 실행 (pythonw: 콘솔 창 없이)
python claude_pet.py --report               # GUI 없이 사용량 보고 (macOS 와 같은 명령)
```

처음 실행하면 Windows 11 은 새 트레이 아이콘을 `^`(숨겨진 아이콘) 안에 넣습니다. 작업표시줄 버튼이 없는 앱이라 트레이가
보이기/숨기기·종료의 진입로이니, `^` 를 열어 고양이 아이콘을 작업표시줄로 끌어내 고정해 두세요(설정 → 개인 설정 → 작업 표시줄 →
기타 시스템 트레이 아이콘에서도 켤 수 있습니다). 우클릭 메뉴는 펫 위에서 바로 열립니다.

## 알아 둘 것

- 배포판은 아직 **코드 서명이 없습니다.** 처음 실행할 때 SmartScreen 이 "Windows 의 PC 보호" 창을 띄우면 "추가 정보 → 실행" 을 누르세요.
  서명 절차는 `build_win.py` 에 준비돼 있지만(아래 "서명"), 인증서는 사용자가 직접 얻어야 하고 아직 없습니다.
- 로그 위치는 `%USERPROFILE%\.claude\projects`, 정확 모드는 `%USERPROFILE%\.claude\.credentials.json` 을 읽습니다(내용을 저장하거나 전송하지 않습니다).
- 설정 파일은 macOS 와 같은 `%USERPROFILE%\.claude_pet.json`, 펫 폴더는 `%USERPROFILE%\.claude_pet\` 입니다.


## 업데이트 (앱 안에서)

판단은 `windows/win_update.py`(순수 Python, macOS 의 `windows/tests/` 로 시험), 실행은 `claude_pet_win.py` 입니다.
`claude_pet.py` 의 업데이트 코드는 macOS 전용 부분(.app, ditto, flock 상속)이 있어 그대로 쓰지 않고, 버전 비교(`_ver_tuple`)·
아카이브 멤버 검사(`_zip_members_are_safe`)·내려받기(`_download_update_zip`)만 재사용합니다.

- **확인 시점**: macOS 판과 같습니다. 시작할 때는 확인하지 않고 한 시간(`UPDATE_CHECK_SEC`) 뒤부터 30초 새로고침에 얹혀 매시간
  확인하며, 새 버전이 있으면 우클릭 메뉴 맨 위에 "새 버전 vX 설치" 가 생깁니다(자동 설치는 하지 않습니다). 우클릭
  "업데이트 확인…" 은 지금 확인하고 새 버전이 있으면 바로 설치합니다. 확인 결과 가운데 네트워크 실패와 JSON 이 아닌 응답만 다음
  새로고침(30초)에 다시 묻고, 그 밖의 모든 결과 — 최신, 새 버전, 그리고 "이 기기용 자산 없음" 같은 릴리즈·기기의 성질인 거절 — 는
  성공한 확인과 똑같이 한 시간을 기다립니다(`win_update.stamps_cooldown`; `update.log` 의 `check … cooldown=1`).
- **설치 종류**는 `unins000.exe` 가 exe 옆에 있고 레지스트리
  `HKCU\…\Uninstall\{me.yeongyu.claudepet}}_is1\InstallLocation` 이 그 폴더를 가리킬 때만 `inno`, 아니면 `portable` 입니다.
  (키 이름의 **닫는 중괄호는 두 개**입니다: `installer.iss` 의 `AppId={{me.yeongyu.claudepet}}` 에서 Inno 는 맨 앞의 `{{` 만
  리터럴 `{` 로 풀고 나머지는 그대로 두며, 제거 프로그램이 접미사를 붙입니다. 하나로 적으면 진짜 설치본에서도 키를 찾지 못해
  `install_kind()` 가 `portable` 을 돌려주고, 완전 삭제 안내와 인앱 업데이트가 둘 다 엉뚱한 갈래로 갑니다 — 실기에서
  두 철자로 각각 불러 확인했습니다, Windows 11, 2026-09-14.)
  소스 실행(`pythonw`)은 업데이트하지 않습니다(git pull).
- **자산**: AMD64 만 배포됩니다 — `inno` → `claude-pet-win-setup.exe`, `portable` → `claude-pet-win.zip`. ARM64 는 "이 기기용
  빌드가 없다" 고 알리고, 30초마다 되묻지 않고 매시간 확인만 계속합니다(자산이 나중에 올라오면 그때 잡힙니다). 릴리즈 JSON 의 `size` 와 `sha256:` `digest` 를 받은 파일과 대조하며, 어느 하나라도
  없거나 다르면 설치하지 않습니다(전송 무결성만 보장합니다 — 게시자 확인은 서명이 있어야 합니다).
- **inno**: `%LOCALAPPDATA%\me.yeongyu.claudepet\claude-pet-win-setup.exe` 로 받아 검증한 뒤
  `/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS /RESTARTAPPLICATIONS /RELAUNCH=1 /LOG=…\setup.log`
  로 실행합니다. 앱은 스스로 끝내지 않습니다: 설치 파일의 Restart Manager 가 앱을 닫고(앱이 시작할 때
  `RegisterApplicationRestart` 로 등록해 둡니다) 설치를 마친 뒤 다시 띄웁니다. `installer.iss` 의 `[Run] … Check: RelaunchRequested`
  항목이 `/RELAUNCH=1` 일 때 한 번 더 띄우고, 단일 인스턴스 뮤텍스(`Local\me.yeongyu.claudepet`)가 둘 중 하나만 남깁니다.
  진행 창이 잠깐 보입니다. 설치 파일이 앱을 닫지 않은 채 끝나면(취소·거절·실패) 앱은 30초 안에 그것을 알아채
  `install … status=exited rc=<n>` 를 남기고 다시 시도할 수 있는 상태로 돌아옵니다. 받은 설치 파일은 다음 업데이트가 덮어쓰거나
  완전 삭제가 캐시 폴더를 지울 때까지 캐시에 남습니다.
- **portable**: zip 을 받아 검증 → 멤버 검사(절대경로·`..`·백슬래시 탈출·링크 거부) → 앱 폴더 **옆** 의 `.claudepet-stage-…` 에 풀기
  → 레이아웃 검사(루트 `ClaudePet\` 하나, `ClaudePet.exe`, `_internal\`, 필수 파일, `_internal\claudepet-release.json` 의
  `version` 이 태그와 같음) → `.claudepet-new-…` 로 이름 바꾸기 → PowerShell 교체 스크립트
  (`%LOCALAPPDATA%\me.yeongyu.claudepet\swap-….ps1`, `powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File`)
  를 띄우고 앱이 끝납니다. 스크립트는 앱 pid 가 끝나길 기다린 뒤 설치 폴더의 이름을 `.claudepet-old-v<옛 버전>` 으로, 새 폴더의
  이름을 제자리로 바꾸고(모두 `Rename-Item` — 대상이 이미 있으면 실패하고 절대 덮어쓰지 않습니다; `Move-Item` 은 있는 폴더 *안으로*
  옮겨 `ClaudePet\ClaudePet` 을 만들기 때문에 쓰지 않습니다) 새 exe 를 실행해 살아 있는지 확인합니다. 어느 단계든 실패하면
  되돌리고 **옛 exe 를 다시 띄웁니다**. 옛 폴더는 새 앱이 뜬 것을 확인한 뒤에 지웁니다. 앱 폴더의 부모에 쓸 수 없으면(예: Program
  Files) 시작하지 않습니다.
  - `.claudepet-old-v<옛 버전>` 이 **이미 있으면 내려받기 전에 거절합니다** — `update.log` 에
    `install … status=refused reason=old-dir-exists`. 지난 교체가 옛 폴더를 반쯤 지우다 만 경우(백신이 DLL 을 붙잡는 등)가
    그렇고, 그런 폴더는 exe 나 버전 마커가 없어 앱이 자동으로 지우지 않습니다. 그 폴더를 직접 지우면 다음 업데이트가 진행됩니다.
  - 두 번의 이름 바꾸기 사이에서 PC 가 꺼진 극히 드문 경우에는 `ClaudePet\` 가 없고 `.claudepet-old-v…\` 와 `.claudepet-new-…\` 만
    남습니다. `.claudepet-new-…` 를 `ClaudePet` 로 이름을 바꾸면(또는 옛 폴더를) 복구됩니다. 다음 시작은 우리 exe 와 버전 마커를
    품은 옆 폴더(`-new-*`/`-old-*`)와, 아카이브 루트 `ClaudePet` 말고는 아무것도 없는 `.claudepet-stage-*` 만 지웁니다 — 이름만
    보고 지우지 않습니다.
- **로그**: 모든 단계는 `%LOCALAPPDATA%\me.yeongyu.claudepet\update.log` 에 개수·상태·태그만 남깁니다(경로 없음). Inno 의 자체
  로그는 같은 폴더의 `setup.log` 입니다. 실기 확인 때 이 두 파일을 봅니다.
- **잠금**: 업데이트와 완전 삭제는 같은 파일(`…\update-ClaudePet.lock`, 공유 모드 없이 연 핸들)을 잡습니다. 다른 쪽이 들고 있으면
  시작하지 않습니다(`… status=refused reason=lock-busy`). 어느 종류를 무엇이 지키는지는 다릅니다: **portable** 은 교체 헬퍼가 그
  핸들을 물려받아 끝날 때까지 들고 있습니다. **inno** 설치 파일은 핸들을 물려받지 않고 앱 쪽 핸들도 설치 파일을 띄운 직후 닫히므로,
  설치 파일이 도는 동안(앱이 닫히길 기다리는 사이) 두 번째 업데이트와 완전 삭제를 막는 것은 앱 안의 "설치 중" 표시입니다
  (`… status=refused reason=installing`). 어느 쪽이든 사용자에게는 "업데이트가 진행 중" 안내로 보입니다.

## 완전 삭제 (우클릭 "완전 삭제…")

macOS 판의 `UNINSTALL_PATHS` 와 같은 범위입니다. 지우는 것: `%USERPROFILE%\.claude_pet.json`, `.claude_pet.json.lock`,
`%USERPROFILE%\claudepet_debug.log`, `%LOCALAPPDATA%\me.yeongyu.claudepet\`(캐시·로그·잠금), 그리고 `HKCU\…\Run\ClaudePet` 이
이 exe 를 가리킬 때 그 값. **남기는 것**: `%USERPROFILE%\.claude_pet\`(사용자 펫과 README — macOS 와 같은 보존 정책),
`%USERPROFILE%\.claude\`(Claude Code 의 것). 그다음 **두 종류 다 "펫이 끝난 뒤에" 제거가 돌도록 헬퍼에 맡기고 앱이
끝납니다**: `inno` 는 우리 pid 를 기다렸다가 `unins000.exe /SILENT` 를 부르는 PowerShell 헬퍼
(`win_update.build_inno_uninstall_script`), `portable` 은 종료 뒤 앱 폴더를 지우는 헬퍼(우리 exe 와 버전 마커가 있을 때만).
소스 실행은 사용자 파일만 지우고 안내 창을 띄웁니다. 업데이트가 진행 중이면 지우지 않고 물러납니다(portable 은 잠금 핸들,
inno 는 "설치 중" 표시 — 위 "잠금").

설치 파일의 제거 프로그램(앱 및 기능)은 `installer.iss` 의 `[UninstallDelete]` 대로 `{app}\_internal`, `{app}\ClaudePet.exe`,
`{localappdata}\me.yeongyu.claudepet` 만 지웁니다 — `{app}` 통째로가 아닙니다(사용자가 기존 폴더에 설치했을 수 있습니다).

### 펫이 떠 있는 채로 제거할 때

제거 프로그램은 **파일을 지우기 전에 실행 중인 펫을 먼저 닫습니다**: `installer.iss` 의 `[UninstallRun]` 에
`taskkill /IM ClaudePet.exe /F` 한 줄(`runhidden skipifdoesntexist`, `RunOnceId` 있음)이 있습니다.

**이 순서는 조건부가 아니라 무조건입니다.** Inno Setup 6 문서의 `[Run] & [UninstallRun]` 절이 이 절을 "programs to
execute as the first step of _uninstallation_" 이라고 정의합니다(<https://jrsoftware.org/ishelp/topic_runsection.htm>).
예전에 이 문서와 `installer.iss` 주석은 "`postuninstall` **없음** — 붙이면 파일 삭제 뒤로 밀린다" 고 적어 두었는데,
**`postuninstall` 은 Inno 의 플래그가 아닙니다** — 그 페이지의 Flags 목록에 없습니다. 제거가 끝난 뒤에 무언가를 돌리는
것은 `[Code]` 의 `CurUninstallStepChanged`/`usPostUninstall` 이지 `[UninstallRun]` 항목이 아닙니다. 순서를 지켜 주는 것은
플래그를 뺀 덕이 아니라 절 자체의 정의이고, 없는 플래그를 근거로 적어 둔 쪽이 틀린 설명이었습니다.

**대신 조심할 플래그는 `nowait`, `shellexec`, `waituntilidle` 셋입니다.** 같은 문서: 이 셋 중 하나가 붙지 않는 한 Inno 는
프로그램이 끝날 때까지 기다린 뒤 다음으로 넘어갑니다(`waituntilterminated` 가 기본값입니다). 하나라도 붙이면 taskkill 이
끝나기 전에 파일 삭제가 시작되어 `사용 중(5)` 가 그대로 돌아옵니다. 그때도 **단계 순서는 그대로 남고 대기만 사라지므로
제거 로그의 순서만 봐서는 구별되지 않습니다** — 그래서 아래 실기 항목에서 순서와 함께 "기다렸는지" 를 봅니다.

기대는 것은 taskkill 이지 Restart Manager 가 아닙니다:
`CloseApplications=yes` / `RestartApplications=yes` 는 예전부터 이 파일에 있었는데도 실기에서 제거 로그에 Restart
Manager/CloseApplications 단계가 **아예 없었습니다**(Windows 11, 2026-09-14 — 펫이 떠 있는 채로 제거하면
`Failed to delete the file; it may be in use (5)` 가 줄줄이 나고 `ClaudePet.exe` 와 `_internal\` 44개가 남는데, 종료 코드는 0 이고
ARP 항목과 Run 값은 그 전에 이미 지워져 사용자에게는 "다시 제거" 버튼조차 남지 않았습니다). 펫이 떠 있지 않으면 taskkill 이
0 이 아닌 값을 돌려주지만 Inno 는 종료 코드를 보지 않고, taskkill 이 없는 기기에서도 `skipifdoesntexist` 로 제거가 실패하지
않습니다(문서는 이 플래그에 `Filename` 이 절대 경로일 것을 요구하는데 `{sys}\taskkill.exe` 는 절대 경로로 펼쳐집니다). `/T` 는 쓰지 않습니다 — 앱 안 '완전 삭제…' 에서는 제거 프로그램이 펫의 자식이라 자기 자신을 끊게 됩니다.
종료 단계를 넣어도 남기는 것은 그대로입니다: 제거 프로그램의 삭제 목록(`[UninstallDelete]`)은 `%USERPROFILE%` 아래를
전혀 건드리지 않으므로 `%USERPROFILE%\.claude_pet\` 과 `.claude_pet.json` 은 그대로 남습니다(설정 파일까지 지우는 것은
macOS 판 `UNINSTALL_PATHS` 와 같은 범위로 도는 앱 안의 '완전 삭제…' 뿐입니다 — 펫 폴더는 그쪽도 남깁니다).

## 로그인 시 자동 실행 (우클릭 "로그인 시 자동 실행")

macOS 판과 같은 자리(화면 돌아다니기 다음)의 체크 항목이고 문자열도 같은 키(`menu_autostart`)입니다. 판단은
`windows/win_autostart.py`(순수 Python, macOS 의 `windows/tests/` 로 시험), 실행은 `claude_pet_win.py` 입니다. 설치 파일의
"Windows 로그인 시 자동 실행" 옵션이 쓰는 값 그대로 — `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 의 `ClaudePet`
값에 `"<exe 경로>"`(큰따옴표 한 쌍) — 를 읽고 씁니다. 그래서 설치 옵션·이 항목·제거 프로그램의 `uninsdeletevalue`·완전 삭제가
한 값을 다룹니다. 설정 파일(`.claude_pet.json`)에는 아무것도 적지 않습니다: 메뉴를 열 때마다 레지스트리를 다시 읽으므로
작업 관리자 › 시작 앱에서 끈 것이 그대로 꺼진 것으로 보이고, 앱이 몰래 다시 켜지 않습니다. 작업 관리자는 끌 때 Run 값을 지우지
않고 `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run` 의 같은 이름 REG_BINARY 값에 기록합니다.

**그 값의 규칙은 첫 바이트의 최하위 비트입니다 — 짝수면 사용, 홀수면 사용 안 함.** 즉 `0x00` 과 `0x02` 는 사용,
`0x01` 과 `0x03` 은 사용 안 함입니다. 근거를 관찰과 추정으로 나눠 적습니다(AGENTS.md §5):

- **관찰(기기 한 대, Windows 11, 설정 › 시작 앱과 작업 관리자 › 시작 앱, 2026-09-14)**: 이 UI 에서 "사용 안 함" 으로 바꾸면
  `01 00 00 00` + 8바이트 FILETIME(첫 바이트 `0x01`), 다시 "사용" 으로 바꾸면 12바이트 0(첫 바이트 `0x00`) 이 적혔고,
  이 UI 가 건드린 적 없는 타사 항목들은 `0x02` 였습니다. 기기 한 대는 규칙을 세우지는 못하지만 **반증은 합니다** —
  예전 코드의 "`0x02` = 사용, `0x03` = 사용 안 함" 은 이 관찰로 반증됐습니다(사용 상태인 `0x00` 을 사용 안 함으로 읽어,
  Windows 는 띄우는데 메뉴 항목만 체크가 없었습니다).
- **추정**: `0x04`(사용) / `0x05`(사용 안 함) 처럼 그 위의 값까지 같은 비트가 결정한다는 것. 관찰이 아니라 가설이고,
  다른 사람이 재현하지 않았습니다. 나중 실기 결과가 이 부분만 뒤집을 수 있습니다.

규칙은 `win_autostart.startup_approved_enabled` 한 함수에만 있습니다(값이 바뀌면 그 함수와 시험 표만 함께 고칩니다).
켜져 있음 = Run 값이 이 exe 를 가리키고 StartupApproved 항목이 없거나 첫 바이트가 짝수. 켜면 Run 값을 쓰고(다른 경로를
가리키던 값은 덮어씀 — 옮겨 둔 portable 폴더를 고칩니다) 사용 안 함 항목을 지우며, 끄면 둘 다 지웁니다. 소스 실행(`pythonw`)은 항목이 "(여기서는 사용 불가)" 로 비활성입니다 — `pythonw.exe` 를
등록하지 않습니다(macOS 판의 소스 실행과 같은 정책). 클릭마다 `update.log` 에 `startup status=<on|off> error=<none|autostart_fail>`
한 줄이 남습니다.

## 배포물 만들기 (3단계)

Windows 에서, 저장소 루트, venv 활성화 후:

```
pip install -r windows\requirements.txt
python windows\build_win.py
```

`dist-win\ClaudePet\ClaudePet.exe` 가 만들어지고, `_internal\claudepet-release.json`(버전 마커 — 업데이터가 태그와 대조하는
번들 안의 유일한 신원)을 쓴 뒤 `release\claude-pet-win.zip` 으로 묶이며, 이어서 Inno Setup 으로
`release\claude-pet-win-setup.exe`(설치 파일: 사용자별 설치, 시작 메뉴, 로그인 시 자동 실행 옵션, 프로그램 추가/제거)를
만든다. Inno Setup 6 이 필요하다: `winget install --id JRSoftware.InnoSetup -e`. 마지막에 `windows\verify_win_artifact.py` 게이트가
**올릴 파일 그 자체**를 검사한다 — zip: 멤버 안전·레이아웃·버전 마커 == `APP_VERSION`·exe 의 버전 리소스, 설치 파일: 존재·크기 > 0·PE 헤더.
게이트가 거절하면 빌드는 실패다(직접 돌리려면 `python windows\verify_win_artifact.py --version X --zip … --installer …`).
사용자는 zip 을 풀어 `ClaudePet\ClaudePet.exe` 를 실행한다. 번들 안에는 코어와 같은 자리에 `frames\`, `fonts\`(Pretendard),
`.claude_pet\`, `claudepet.ico`, 버전 마커, 그리고 `fcntl` shim 과 `win_update` 가 들어간다.

**exe 의 버전 리소스.** PyInstaller 는 `--version-file` 을 준 경우에만 버전 리소스를 넣는다. 없으면 Windows 가 항목 이름을
`ClaudePet.exe`, 게시자를 빈칸으로 보여 준다.

- **관찰(기기 한 대, Windows 11, 2026-09-14)**: 이름은 `ClaudePet.exe`, 게시자는 빈칸이었고 바로 위 Claude 항목은
  "Claude / Anthropic, PBC" 였다. **보고에 남은 자리는 "설정/작업 관리자" 까지이고 어느 화면인지는 기록되지 않았다** —
  그래서 여기서도 화면 이름을 단정하지 않는다(AGENTS.md §5: 관찰은 관찰한 만큼만).
- **관찰과 무관하게 참인 것**: 시작 앱 목록(설정 › 시작 앱, 작업 관리자 › 시작 앱·세부 정보)은 exe 의
  `FileDescription`/`CompanyName` 을 읽고, 설정 › 앱 → 설치된 앱은 Inno 의 ARP 값을 읽는다. 뒤쪽의 `AppPublisher` 는
  `installer.iss` 에 이미 있으므로 거기서 게시자가 비어 있을 수는 없다. 어느 화면이었든 고치는 것은 exe 의 버전 리소스로
  같고, 화면 이름 확정만 다음 실기 몫이다(아래 "실기에서 확인할 것").

그래서 `build_win.write_version_resource()` 가 빌드할 때마다 리소스 파일을 새로 쓰고
(`FileDescription`=Claude Pet, `CompanyName`=Yeongyu Yang, `ProductName`=Claude Pet, `OriginalFilename`=ClaudePet.exe,
`LegalCopyright`, `FileVersion`/`ProductVersion` 은 `claude_pet.APP_VERSION`) `--version-file` 로 넘긴다 — 손으로 만들어
커밋해 두지 않는 이유는 그러면 버전이 그 자리에 얼어붙기 때문이다. 게이트의 `check_version_resource()` 가 zip 안의 exe 에
그 문자열들이 UTF-16LE 로 들어 있는지 본다(리소스 디렉터리를 파싱하지는 않는다 — macOS 에서 돌리면 그 한계를 stderr 로
알린다). 게이트는 그 문자열을 베껴 두지 않고 `build_win.VERSION_STRINGS` 에서 읽는다 — 사본이 있으면 빌더에서
`CompanyName` 을 고쳤을 때 게이트만 옛 값을 찾는다. 읽기는 `check_version_resource()` 안에서 하므로(모듈 꼭대기가 아니다)
"이 파일이 Windows 에서 첫 줄에 죽지 않는가" 를 보는 시험의 import 사슬은 그대로다.

**코어 import 은 `windows/win_core.py` 한 곳이 맡는다.** `claude_pet.py` 는 Windows 에서 `import fcntl` 과
`ctypes.CDLL(None)` 두 줄에 죽으므로, `windows/compat/fcntl.py` 를 `sys.path` 앞에 두고 import 하는 동안만 `CDLL` 을 감싸는
우회가 필요하다. 그 두 우회는 `win_core.import_core()` 에만 있고, `claude_pet_win.py`·`win_update.py`·`build_win.py`·
`verify_win_artifact.py` 가 모두 이 함수를 통해 코어를 얻는다(다른 곳에서 `import claude_pet` 을 하면 안 된다 — 예전에는
`win_update.py` 가 그렇게 해서 `python windows\build_win.py` 와 `python windows\verify_win_artifact.py` 가 실기에서 첫 줄에
죽었다). macOS 에서 `import_core()` 는 그냥 `importlib.import_module` 이라 `sys.path` 도 `ctypes` 도 건드리지 않는다 —
**그 말은 함수에 붙는 것이지 파일에 붙는 것이 아니다.** `win_core.py` 의 모듈 본문은 어느 플랫폼에서든 저장소 루트를
`sys.path` 에 한 번 넣는다(그러지 않으면 `claude_pet` 을 찾을 수가 없다). 호출이 더하는 것이 플랫폼에 따라 달라질 뿐이다.

릴리즈 자산 이름은 업데이터가 고르는 이름과 같아야 한다: `claude-pet-win.zip`, `claude-pet-win-setup.exe`
(`win_update.ZIP_ASSET` / `SETUP_ASSET`, `installer.iss` 의 `OutputBaseFilename`). 이름이 어긋나면 설치된 모든 사본이 조용히
영원히 재시도한다.

## 서명 (`CLAUDE_PET_WIN_SIGN`)

`build_win.py` 는 `ClaudePet.exe` 를 **묶기 전에**, 설치 파일을 **만든 뒤에** 서명한다. 모드는 환경변수로 고르고 기본은 `off` 다
(서명하지 않는다고 로그 한 줄을 남기고 계속한다). 모든 모드가 `signtool sign /fd SHA256 /td SHA256 /tr $CLAUDE_PET_WIN_TS` 로
시작하고(타임스탬프 서버 기본 `http://timestamp.digicert.com`) 서명 뒤 `signtool verify /pa` 로 확인한다. `signtool.exe` 는
`CLAUDE_PET_WIN_SIGNTOOL` → PATH → Windows Kits 순으로 찾는다(Windows SDK "Signing Tools for Desktop Apps").

| 모드 | 추가 인자 | 환경변수 | 용도 |
|---|---|---|---|
| `off` | — | — | 기본. 서명 없음 → SmartScreen 경고 |
| `pfx` | `/f <pfx> /p <암호>` | `CLAUDE_PET_WIN_PFX`, `CLAUDE_PET_WIN_PFX_PASSWORD`(출력하지 않음) | 자체 서명·시험용. 2023-06 이후 발급된 OV/EV 키는 하드웨어에만 있어 PFX 로 내보낼 수 없다 |
| `store` | `/sha1 <지문>` | `CLAUDE_PET_WIN_CERT_SHA1` | 인증서 저장소·USB 토큰의 OV/EV 인증서. 토큰 PIN 프롬프트가 뜨므로 무인 실행이 아니다 |
| `trusted` | `/dlib <dll> /dmdf <json>` | `CLAUDE_PET_WIN_DLIB`, `CLAUDE_PET_WIN_DMDF` (+ Azure 자격 증명은 signtool 이 환경에서 읽음) | Azure Trusted Signing |

**사용자가 직접 얻어야 하는 것** — 에이전트는 어느 것도 얻거나 보관하거나 쓸 수 없다(macOS 의 서명·공증과 같은 `[ASK-OP]` 분리):
OV 코드 서명 인증서(USB 토큰, 개인 신원 확인, SmartScreen 평판은 서서히 쌓임) 또는 EV 인증서(조직, 평판이 빨리 쌓임) 또는
Azure Trusted Signing(구독 + 신원 확인, 한국 가용성은 확인 필요). 어느 경로든 사용자의 법적 신원과 결제, 그리고 개인 키·PIN·Azure
자격 증명이 필요하다. 그것이 준비되면 위 변수를 채우고 `python windows\build_win.py` 를 돌리면 된다 — 코드는 바뀌지 않는다.
설치 파일 안의 `unins000.exe` 까지 서명하려면 Inno 의 `SignTool=` 통합이 따로 필요하다(후속).

## 실기에서 확인할 것 (macOS 에서는 검증 불가)

기기 한 대(Windows 11)로 2026-09-14 에 v0.25 사전 점검을 돌려 아래 항목의 일부가 답을 얻었고, 그 결과 다섯 가지를 고쳤다
(`windows/win_core.py` 도입, 제거 레지스트리 키 철자, StartupApproved 바이트 규칙, 실행 중 제거, exe 버전 리소스). **답이
나온 항목에는 "실기 2026-09-14" 를 달아 두고, 다시 확인해야 할 것과 아직 답이 없는 것은 그대로 둔다** — 기기 한 대의 결과는
규칙을 세우지는 못하고 반증만 한다(AGENTS.md §5).

- **실기 2026-09-14 (고침)**: `python windows\build_win.py` 와 `python windows\verify_win_artifact.py` 가 Windows 에서 첫 줄에
  죽지 않는가 — 예전에는 `ModuleNotFoundError: No module named 'fcntl'`, 그 다음엔 `TypeError: LoadLibrary() argument 1 must
  be str, not None` 이었다. 이제 둘 다 `win_core.import_core()` 를 지난다(위 "배포물 만들기"). **다시 볼 때는 그때 쓰던
  우회를 반드시 걷어내고 본다** — 세션에서 만든 `sitecustomize.py` 없이, `PYTHONPATH` 에 `windows\compat` 없이. 그 우회가
  남아 있으면 고친 것이 아니라 우회를 다시 재는 것이 된다.
- **실기 2026-09-14 (고침)**: 진짜 설치본에서 `install_kind()` 가 `inno` 를 돌려주는가(제거 레지스트리 키의 닫는 중괄호 둘 —
  위 "업데이트"). 완전 삭제 확인 창이 inno 계획(제거 프로그램 실행)을 보여 주는지로도 눈에 보인다.
- **실기 2026-09-14 (고침)**: 펫이 떠 있는 채로 제거해도 앱 폴더가 남지 않는가(위 "펫이 떠 있는 채로 제거할 때"). 남은 파일
  개수(전에는 45개)와 제거 로그에서 `taskkill` 단계가 **첫 파일 삭제보다 앞에** 있는지를 함께 본다. 순서만이 아니라
  **제거 프로그램이 `taskkill` 이 끝나기를 기다렸는지**도 로그에서 같이 적어 둔다 — 순서는 절의 정의가 보장하지만 대기는
  `nowait`/`shellexec`/`waituntilidle` 중 하나가 끼어들면 조용히 사라지고, 그때도 단계 순서는 그대로라서 로그의 이 부분이
  아니면 관찰할 데가 없다(위 "펫이 떠 있는 채로 제거할 때"). `Failed to delete the
  file; it may be in use (5)` 줄이 하나도 없어야 하고 `%USERPROFILE%\.claude_pet\` 과 `.claude_pet.json` 은 남아야 한다.
  이어서 `taskkill /F` 의 대가도 본다 — 제거 직전에 바꾼 설정이 `.claude_pet.json` 에 살아남았는가,
  `%LOCALAPPDATA%\me.yeongyu.claudepet` 에 잠금·임시 파일이 남지 않았는가, 핸들이 곧바로 풀려 재시도 없이 지워졌는가.
- **실기 2026-09-14 (고침)**: "Claude Pet / Yeongyu Yang" 으로 뜨는가(exe 버전 리소스). **어느 화면이었는지를 이번에
  적어 둔다** — 설정 › 시작 앱인지, 작업 관리자 › 시작 앱인지, 설정 › 앱 → 설치된 앱인지. 지난 보고에는 "설정/작업 관리자"
  까지만 남아 화면이 확정되지 않았다(위 "exe 의 버전 리소스"). 파일 속성 › 자세히 탭의 `FileVersion` 이 `APP_VERSION` 과
  같은지도 함께 본다.
- 설치 파일을 손으로 돌려 업그레이드할 때 펫이 닫혔다가 다시 뜨는가(`RestartApplications=yes` + `RegisterApplicationRestart`).
- 앱 안 업데이트(inno): 진행 창 뒤 펫이 다시 뜨고 하나만 떠 있는가; `update.log` 의 `install … status=launched`, `setup.log`.
- 앱 안 업데이트(portable): `update.log` 의 `swap … swapped=ok`, `new-app=running`, `old-tree=removed`; 새 exe 실행을 일부러
  막았을 때 `rollback=ok` 와 옛 펫 재실행.
- 앱 안 업데이트(portable) 거절: `.claudepet-old-v<현재 버전>` 폴더를 앱 폴더 옆에 미리 만들어 두고 업데이트 → 내려받지 않고
  `install … status=refused reason=old-dir-exists`; 그 폴더를 지우면 진행. 같은 폴더를 헬퍼가 도는 사이에 만들면 헬퍼가
  `swap refused=old-dir-exists` 를 남기고 옛 exe 를 다시 띄우는가.
- 잠금: 헬퍼가 도는 동안 두 번째 업데이트가 `install status=refused reason=lock-busy`; 설치 파일이 도는 동안 "완전 삭제…" 가
  `uninstall status=refused reason=installing`; 설치 파일을 취소하면 30초 안에 `install … status=exited rc=…` 뒤 다시 시도 가능.
- 확인 주기: ARM64 기기가 있다면 `check status=error reason=no-asset cooldown=1` 이 한 시간에 한 번만 남는가; 네트워크를 끊으면
  `reason=fetch-failed:… cooldown=0` 이 새로고침마다 남는가.
- 완전 삭제(inno/portable) 뒤 남는 것: `%USERPROFILE%\.claude_pet\` 만(펫을 닫아 놓고 제거했을 때는 실기 2026-09-14 에서
  확인됐다 — `.claude_pet\` 과 `.claude_pet.json` 만 남았다. 펫이 떠 있는 채로도 같은지가 이번에 고친 부분이다).
- 완전 삭제가 시작조차 못 할 때: `powershell.exe` 를 막고(AppLocker, 또는 VM 에서 이름 바꾸기) portable 설치에서 "완전 삭제…" →
  실패 안내 상자가 뜨고 `update.log` 에 `uninstall kind=portable status=failed at=run-helper error=<예외 종류>` 가 남으며 아무것도
  지워지지 않는가(inno 도 이제 PowerShell 헬퍼로 제거 프로그램을 부르므로 같은 조건에서 `at=run-uninstaller` 가 남는다).
  이 두 줄은 macOS 에서는 호출 모양만 확인된다.
- 관리형 PC 의 PowerShell 제한(Constrained Language, AppLocker)에서 교체 스크립트가 도는가.
- 로그인 시 자동 실행: 설치 파일에서 옵션을 켠 뒤 우클릭 메뉴 항목에 체크가 있는가; 항목을 끄고 켜면 작업 관리자 › 시작 앱의
  ClaudePet 이 사라지고 다시 나타나는가(`update.log` 의 `startup status=off` / `status=on`); 작업 관리자에서 "사용 안 함" 으로
  바꾸면 다음 우클릭에 항목이 꺼진 것으로 보이는가(**실기 2026-09-14**: `HKCU\…\Explorer\StartupApproved\Run` 의 `ClaudePet`
  값 첫 바이트는 사용 안 함이 `0x01`, 다시 사용이 `0x00` 이었고 타사 항목은 `0x02` 였다 — 짝수 = 사용, 홀수 = 사용 안 함.
  `0x03` 과 그 위는 같은 비트로 읽는다는 **추정**이니, 다른 값이 실제로 보이면 `win_autostart.startup_approved_enabled` 와
  그 시험 표를 함께 고친다. 다시 볼 때는 작업 관리자와 설정 › 시작 앱 **양쪽에서** 껐다 켜 보고, 그 기기에 있는 타사 항목
  전부의 첫 바이트를 판정이 아니라 **raw 바이트 그대로** 적는다 — `0x01`/`0x03` 이 아닌 홀수나 `0x00`/`0x02` 가 아닌
  짝수가 보이는 것이 추정을 확인하거나 뒤집는 자리다. 보고된 상태(Run 값 있음 + StartupApproved `00 ×12`)에서 메뉴 항목에
  체크가 보이는지도 확인한다); 사용 안 함 상태에서 메뉴 항목을 켜면 그 값이 지워지고
  다음 로그인에 펫이 실제로 뜨는가; portable(zip) 에서도 작업 관리자가 ClaudePet 이름으로 보여 주는가; 완전 삭제 뒤 Run 값이
  없는가.
