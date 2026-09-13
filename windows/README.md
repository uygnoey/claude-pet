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
  `HKCU\…\Uninstall\{me.yeongyu.claudepet}_is1\InstallLocation` 이 그 폴더를 가리킬 때만 `inno`, 아니면 `portable` 입니다.
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
`%USERPROFILE%\.claude\`(Claude Code 의 것). 그다음 `inno` 는 `unins000.exe /SILENT`(프로그램·바로가기·등록 항목 제거),
`portable` 은 종료 뒤 앱 폴더를 지우는 헬퍼(우리 exe 와 버전 마커가 있을 때만)를 띄우고 앱이 끝납니다. 소스 실행은 사용자
파일만 지우고 안내 창을 띄웁니다. 업데이트가 진행 중이면 지우지 않고 물러납니다(portable 은 잠금 핸들, inno 는 "설치 중" 표시 — 위
"잠금").

설치 파일의 제거 프로그램(앱 및 기능)은 `installer.iss` 의 `[UninstallDelete]` 대로 `{app}\_internal`, `{app}\ClaudePet.exe`,
`{localappdata}\me.yeongyu.claudepet` 만 지웁니다 — `{app}` 통째로가 아닙니다(사용자가 기존 폴더에 설치했을 수 있습니다).

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
**올릴 파일 그 자체**를 검사한다 — zip: 멤버 안전·레이아웃·버전 마커 == `APP_VERSION`, 설치 파일: 존재·크기 > 0·PE 헤더.
게이트가 거절하면 빌드는 실패다(직접 돌리려면 `python windows\verify_win_artifact.py --version X --zip … --installer …`).
사용자는 zip 을 풀어 `ClaudePet\ClaudePet.exe` 를 실행한다. 번들 안에는 코어와 같은 자리에 `frames\`, `fonts\`(Pretendard),
`.claude_pet\`, `claudepet.ico`, 버전 마커, 그리고 `fcntl` shim 과 `win_update` 가 들어간다.

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
- 완전 삭제(inno/portable) 뒤 남는 것: `%USERPROFILE%\.claude_pet\` 만.
- 완전 삭제가 시작조차 못 할 때: `powershell.exe` 를 막고(AppLocker, 또는 VM 에서 이름 바꾸기) portable 설치에서 "완전 삭제…" →
  실패 안내 상자가 뜨고 `update.log` 에 `uninstall kind=portable status=failed at=run-helper error=<예외 종류>` 가 남으며 아무것도
  지워지지 않는가(inno 에서 `unins000.exe` 실행을 막으면 `at=run-uninstaller`). 이 두 줄은 macOS 에서는 호출 모양만 확인된다.
- 관리형 PC 의 PowerShell 제한(Constrained Language, AppLocker)에서 교체 스크립트가 도는가.
