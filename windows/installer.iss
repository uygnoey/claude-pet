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
