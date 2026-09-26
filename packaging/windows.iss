#ifndef Product
  #error Product must be Live or Manager
#endif
#ifndef Version
  #define Version "1.0.0-beta.5"
#endif
#if Product != "Live" && Product != "Manager"
  #error Unsupported product
#endif
#define ProductName "SecretariatPro " + Product

[Setup]
AppId=SecretariatPro{#Product}
AppName={#ProductName}
AppVersion={#Version}
AppPublisher=SecretariatPro
AppPublisherURL=https://secretariatproapp.com
VersionInfoVersion=1.0.0.5
VersionInfoProductName={#ProductName}
DefaultDirName={localappdata}\Programs\SecretariatPro\{#Product}
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0.17763
OutputDir=..\release
OutputBaseFilename=SecretariatPro-{#Product}-{#Version}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#ProductName}.exe
#if Product == "Live"
SetupIconFile=..\assets\secretariatpro.ico
#else
SetupIconFile=..\assets\manager_icon.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "finnish"; MessagesFile: "compiler:Languages\Finnish.isl"
Name: "swedish"; MessagesFile: "compiler:Languages\Swedish.isl"
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#ProductName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\prerequisites\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Flags: dontcopy

[Icons]
Name: "{group}\{#ProductName}"; Filename: "{app}\{#ProductName}.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\{#ProductName}.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ProductName}.exe"; Description: "{cm:LaunchProgram,{#ProductName}}"; Flags: nowait postinstall skipifsilent

[Code]
function RuntimeInstalled: Boolean;
var
  Version: String;
  Key: String;
begin
  Key := 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := (RegQueryStringValue(HKLM32, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
  if not Result then
    Result := (RegQueryStringValue(HKCU, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
begin
  Result := '';
  if RuntimeInstalled then Exit;
  ExtractTemporaryFile('MicrosoftEdgeWebView2RuntimeInstallerX64.exe');
  if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'),
      '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
  begin
    Result := 'Microsoft WebView2 could not be installed. Please retry the installation.';
    Exit;
  end;
  NeedsRestart := (ExitCode = 3010);
  if not RuntimeInstalled then
    Result := 'Microsoft WebView2 is required. Installation failed (code ' + IntToStr(ExitCode) + '). Please restart Windows and retry.';
end;
