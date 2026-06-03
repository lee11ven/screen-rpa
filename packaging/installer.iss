; 使用 Inno Setup 6 编译生成安装向导（需本机安装 ISCC）。
; 命令示例: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss

#define MyAppName "Screen RPA"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Screen RPA"
#define MyAppExeName "ScreenRPA.exe"
#define MyAppShortcutHotkey "ctrl+alt+r"
#define DistDir "..\dist\ScreenRPA"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=ScreenRPA-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\logo.ico

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; HotKey: "{#MyAppShortcutHotkey}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; HotKey: "{#MyAppShortcutHotkey}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
