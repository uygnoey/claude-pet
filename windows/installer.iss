; Claude Pet — Windows 설치 파일 (Inno Setup 6). build_win.py 가 /DMyAppVersion=… /O<출력 폴더> 로 컴파일한다.
; 설치는 사용자별(%LOCALAPPDATA%\Programs\ClaudePet, 관리자 권한 불필요). 서명 없음 → 첫 실행 때 SmartScreen "추가 정보 → 실행".
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
RestartApplications=no
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

[UninstallDelete]
; 앱이 만드는 캐시/로그는 지우고, 사용자 펫(~/.claude_pet/pets)과 설정은 남긴다 (macOS 판 완전 삭제와 같은 보존 정책은 앱 메뉴가 담당)
Type: filesandordirs; Name: "{app}"
