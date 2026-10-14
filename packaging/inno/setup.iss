; Inno Setup — instalador de Control Maletas
; Compilar:  ISCC /DAppVersion=0.1.0 packaging\inno\setup.iss   (desde la raíz del repo)
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6F2C1B1E-4B1A-4C87-9A5E-0C0A7E5D2A11}
AppName=Control Maletas
AppVersion={#AppVersion}
AppPublisher=Control Maletas
DefaultDirName={autopf}\Control Maletas
DefaultGroupName=Control Maletas
DisableProgramGroupPage=yes
OutputDir=..\..\installer
OutputBaseFilename=ControlMaletas-Setup-{#AppVersion}
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\ControlMaletas.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
; Colores del logo
WizardImageFile=..\..\assets\wizard.bmp
WizardSmallImageFile=..\..\assets\wizard_small.bmp

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\..\dist\ControlMaletas\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Control Maletas"; Filename: "{app}\ControlMaletas.exe"
Name: "{group}\Desinstalar Control Maletas"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Control Maletas"; Filename: "{app}\ControlMaletas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ControlMaletas.exe"; Description: "Abrir Control Maletas"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Los datos del usuario (%APPDATA%\ControlMaletas) NO se borran: contienen la base de datos.
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    MsgBox('Sus datos (base de datos y tickets) se conservaron en %APPDATA%\ControlMaletas.' + #13#10 +
           'Elimine esa carpeta manualmente si ya no los necesita.', mbInformation, MB_OK);
end;
