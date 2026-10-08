[Setup]
AppName=Floating Sinhala Translator
AppVersion=1.1.0
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

[Files]
Source: "dist\Floating Sinhala Translator\Floating Sinhala Translator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Floating Sinhala Translator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}\_internal"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FloatingSinhalaTranslator"; ValueData: """{app}\Floating Sinhala Translator.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Floating Sinhala Translator.exe"; Parameters: "--setup"; Description: "{cm:LaunchProgram,Floating Sinhala Translator}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
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

(* After install, remind the user that the app itself must also run as admin.
   The auto-start registry entry already launches it normally; users who pin
   the EXE to the taskbar should right-click → "Run as administrator", or use
   a scheduled-task launcher set to run with highest privileges. *)
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
    MsgBox(
      'Installation complete!' + #13#10 + #13#10 +
      'IMPORTANT: Floating Sinhala Translator must be run with ' +
      'Administrator privileges so that its global keyboard hooks can ' +
      'bypass Windows UIPI restrictions (required for the touchpad ' +
      'gesture fix to work correctly).' + #13#10 + #13#10 +
      'The app has been added to Windows startup. If you encounter any ' +
      'issues with hotkeys, right-click the EXE and choose ' +
      '"Run as administrator".',
      mbInformation, MB_OK);
end;