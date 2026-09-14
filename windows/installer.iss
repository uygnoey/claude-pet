; Claude Pet — Windows 설치 파일 (Inno Setup 6). build_win.py 가 /DMyAppVersion=… /O<출력 폴더> 로 컴파일한다.
; 설치는 사용자별(%LOCALAPPDATA%\Programs\ClaudePet, 관리자 권한 불필요). 서명은 build_win.py 의 CLAUDE_PET_WIN_SIGN 이 맡는다
; (기본 off → 첫 실행 때 SmartScreen "추가 정보 → 실행"). 앱 안의 업데이트는 이 설치 파일을 /SILENT 로 다시 돌린다 (windows/README.md).
#ifndef MyAppVersion
  #define MyAppVersion "0.0"
#endif
#define MyAppName "Claude Pet"
#define MyAppPublisher "Yeongyu Yang"
#define MyAppURL "https://claude-pet.yeongyu.me/"
#define MyAppExeName "ClaudePet.exe"

[Setup]
AppId={{me.yeongyu.claudepet}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/uygnoey/claude-pet
AppUpdatesURL=https://github.com/uygnoey/claude-pet/releases/latest
DefaultDirName={localappdata}\Programs\ClaudePet
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputBaseFilename=claude-pet-win-setup
SetupIconFile=claudepet.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=yes
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[CustomMessages]
english.StartupTask=Start {#MyAppName} when I sign in to Windows
korean.StartupTask=Windows 로그인 시 {#MyAppName} 자동 실행

[Tasks]
Name: "startup"; Description: "{cm:StartupTask}"; Flags: checkedonce
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
; build_win.py 가 만든 onedir 폴더 통째로 (ClaudePet.exe + _internal\)
Source: "..\dist-win\ClaudePet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; 로그인 시 자동 실행 — 설치 옵션. 제거하면 값도 지운다.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ClaudePet"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
; 앱 안에서 시작한 조용한 업데이트(/SILENT … /RELAUNCH=1 — win_update.inno_silent_args)는 postinstall 항목을 건너뛰므로 여기서
; 다시 띄운다. Restart Manager 도 앱을 다시 띄울 수 있지만(RestartApplications=yes + RegisterApplicationRestart) 둘 다 뜨면
; 앱의 단일 인스턴스 뮤텍스(Local\me.yeongyu.claudepet)가 두 번째를 바로 끝낸다.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: RelaunchRequested

[UninstallRun]
; 제거는 파일을 지우기 전에 실행 중인 펫을 먼저 닫는다 — 여기서 기대는 것은 taskkill 이지 Restart Manager 가 아니다.
; CloseApplications=yes / RestartApplications=yes 는 이 파일에 이미 있었지만, 펫이 떠 있는 채로 제거했을 때 제거 로그에
; Restart Manager/CloseApplications 단계가 아예 없었고 ClaudePet.exe 와 _internal\ 44개가 "사용 중(5)" 으로 남았다
; (실기 관찰, Windows 11, 2026-09-14). 그래서 명시적인 종료 단계를 둔다.
; 순서는 조건부가 아니라 무조건이다. Inno Setup 6 문서의 [Run] & [UninstallRun] 절
; (https://jrsoftware.org/ishelp/topic_runsection.htm): "The [UninstallRun] section ... specifies any number of
; programs to execute as the first step of uninstallation." 플래그로 켜고 끄는 것이 아니라 절의 정의가 그렇다.
; 그리고 postuninstall 은 애초에 Inno 의 플래그가 아니다 — 그 페이지의 Flags 목록(32bit, 64bit, dontlogparameters,
; hidewizard, logoutput, nowait, postinstall, runascurrentuser, runasoriginaluser, runhidden, runmaximized,
; runminimized, shellexec, skipifdoesntexist, skipifnotsilent, skipifsilent, unchecked, waituntilidle,
; waituntilterminated)에 없다. 제거가 끝난 뒤에 무언가를 돌리는 것은 [Code] 의 CurUninstallStepChanged 와
; usPostUninstall 이지 [UninstallRun] 항목이 아니다. 예전 주석은 이 순서가 "postuninstall 을 안 붙인 덕" 이라고
; 적어 두었는데, 없는 플래그를 근거로 든 틀린 설명이었다.
; 이 항목을 실제로 망가뜨릴 수 있는 것은 nowait, shellexec, waituntilidle 셋이다. 같은 문서: "By default, when
; processing a [Run]/[UninstallRun] entry, Setup/Uninstall will wait until the program has terminated before
; proceeding to the next one, unless the nowait, shellexec, or waituntilidle flags are used." 셋 중 하나라도 붙으면
; Inno 는 taskkill 이 끝나기를 기다리지 않고 파일 삭제로 넘어가고, "사용 중(5)" 가 그대로 돌아온다. 그때도 단계 순서는
; 그대로 남고 대기만 사라지므로 제거 로그의 순서만 봐서는 티가 나지 않는다. 셋 다 붙이지 않는다.
; 펫이 떠 있지 않으면 taskkill 이 0 이 아닌 값을 돌려주지만 Inno 는 종료 코드를 보지 않고, taskkill.exe 가 없는 기기에서도
; skipifdoesntexist 로 제거가 실패하지 않는다 — 문서는 이 플래그에 Filename 이 절대 경로일 것을 요구하는데
; {sys}\taskkill.exe 는 절대 경로로 펼쳐지므로 그 조건을 만족한다. /T 는 쓰지 않는다 — 앱 안의 '완전 삭제…'
; 에서는 제거 프로그램이 펫의 자식이므로 자기 자신을 끊는다.
; 두 가지는 적어 둘 값이 있다. (1) /IM 은 이름으로 고르므로 지금 제거하는 설치본이 아닌 같은 이름의 프로세스까지 닫는다.
; 설치 프로그램이 PID 를 겨눌 방법은 없고, 앱의 단일 인스턴스 뮤텍스(Local\me.yeongyu.claudepet) 때문에 다른 폴더의
; 두 번째 사본이 같이 떠 있을 수는 없으므로 실제로는 한 개다. (2) /F 라 펫은 정상 종료 절차 없이 끝난다 — 설정은 바뀔 때
; 바로 쓰므로 잃을 것이 없어야 하지만, 그것과 "핸들이 곧바로 풀려 다음 삭제 단계가 한 번에 성공하는가" 는 실기에서
; 확인할 항목이다(windows/README.md).
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ClaudePet.exe /F"; RunOnceId: "CloseClaudePet"; Flags: runhidden skipifdoesntexist

[UninstallDelete]
; 설치 파일이 놓은 것만 지운다 — {app} 통째로가 아니다. DisableDirPage=auto 라 사용자가 기존 폴더(예: C:\Tools)에 설치했을 수
; 있고, 그때 filesandordirs {app} 은 우리 것이 아닌 파일까지 지운다. 빈 {app} 은 Inno 가 알아서 없앤다.
Type: files; Name: "{app}\_internal\claudepet-release.json"
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\{#MyAppExeName}"
; 앱이 만드는 캐시(업데이트 잠금·내려받은 파일·update.log·setup.log). Inno 는 이 폴더를 기록한 적이 없으므로 명시한다.
Type: filesandordirs; Name: "{localappdata}\me.yeongyu.claudepet"
; 남기는 것(macOS 판 UNINSTALL_PATHS 와 같은 보존 정책): %USERPROFILE%\.claude_pet(사용자 펫), .claude_pet.json, claudepet_debug.log.
; 그 셋은 앱 메뉴의 '완전 삭제…' 가 지운 뒤 이 제거 프로그램을 /SILENT 로 부른다.

[Code]
function RelaunchRequested: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;
