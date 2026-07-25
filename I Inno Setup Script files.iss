[Setup]
AppName=Floating Sinhala Translator
AppVersion=1.0.2
DefaultDirName={autopf}\FloatingSinhalaTranslator
DisableProgramGroupPage=yes
OutputBaseFilename=FloatingTranslator_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\Floating Sinhala Translator.exe
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "Z:\GitHub\Translate App\Floating-Cloud-Window-G-Translator\dist\Floating Sinhala Translator\Floating Sinhala Translator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Z:\GitHub\Translate App\Floating-Cloud-Window-G-Translator\dist\Floating Sinhala Translator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "Z:\GitHub\Translate App\Floating-Cloud-Window-G-Translator\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FloatingSinhalaTranslator"; ValueData: """{app}\Floating Sinhala Translator.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Floating Sinhala Translator.exe"; Parameters: "--setup"; Description: "{cm:LaunchProgram,Floating Sinhala Translator}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ""Floating Sinhala Translator.exe"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"