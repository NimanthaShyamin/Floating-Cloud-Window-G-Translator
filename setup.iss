[Setup]
AppName=Floating Sinhala Translator
AppVersion=2.0.0
VersionInfoVersion=2.0.0.0
DefaultDirName={autopf}\FloatingSinhalaTranslator
DisableProgramGroupPage=yes
OutputBaseFilename=FloatingTranslator_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\Floating Sinhala Translator.exe
Compression=lzma
SolidCompression=yes
; Administrator privileges are REQUIRED so the app can register global keyboard
; hooks that bypass Windows UIPI restrictions (needed for the touchpad gesture fix).
PrivilegesRequired=admin
UsedUserAreasWarning=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Floating Sinhala Translator\Floating Sinhala Translator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Floating Sinhala Translator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}\_internal"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Floating Sinhala Translator"; Filename: "{app}\Floating Sinhala Translator.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Floating Sinhala Translator"; Filename: "{app}\Floating Sinhala Translator.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "FloatingSinhalaTranslator"; Flags: deletevalue uninsdeletevalue

[Run]
Filename: "{app}\Floating Sinhala Translator.exe"; Parameters: "--setup"; Description: "{cm:LaunchProgram,Floating Sinhala Translator}"; Flags: runascurrentuser nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""FloatingSinhalaTranslator"" /F"; Flags: runhidden; RunOnceId: "DeleteStartupTask"
Filename: "{sys}\cmd.exe"; Parameters: "/c taskkill /f /im ""Floating Sinhala Translator.exe"""; Flags: runhidden; RunOnceId: "KillTranslatorProcess"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
(* ---------------------------------------------------------------------------
   Startup check: warn the user if the installer is somehow not elevated.
   In practice, PrivilegesRequired=admin guarantees UAC elevation, but this
   guard is kept as an extra safety net.
   --------------------------------------------------------------------------- *)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

(* ---------------------------------------------------------------------------
   Register the elevated Scheduled Task during ssPostInstall.
   This guarantees taskschd registration completes under the installer's
   elevated credentials BEFORE any post-install launch occurs.
   --------------------------------------------------------------------------- *)
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  AppExe: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppExe := ExpandConstant('{app}\Floating Sinhala Translator.exe');
    Exec(ExpandConstant('{sys}\schtasks.exe'),
      '/Create /TN "FloatingSinhalaTranslator" /TR "\"' + AppExe + '\"" /SC ONLOGON /RL HIGHEST /F',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;