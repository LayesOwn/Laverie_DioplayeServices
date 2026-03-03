; ============================================================
;  Dioplaye Services - Laverie
;  Script Inno Setup 6
;  Genere un installateur Windows standalone
; ============================================================

#define AppName    "Dioplaye Services - Laverie"
#define AppVersion "1.0.0"
#define AppPublisher "Dioplaye Services"
#define AppExeName "Lancer_DioplayeServices.bat"
#define AppRoot    ".."

[Setup]
AppId={{F3A2C8E1-9D4B-4F72-B3C5-8E2A1D6F0C3B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppVerName={#AppName} {#AppVersion}

; Installe sans droits administrateur (dans %LOCALAPPDATA%\Programs)
PrivilegesRequired=lowest
DefaultDirName={autopf}\DioplayeServices
DefaultGroupName=Dioplaye Services

; Sortie
OutputDir=dist
OutputBaseFilename=Setup_DioplayeServices_v{#AppVersion}
SetupIconFile=

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Apparence
WizardStyle=modern
WizardSmallImageFile=

; Infos
LicenseFile=
MinVersion=10.0

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
; --- Fichiers application ---
Source: "{#AppRoot}\app.py";             DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\config.py";          DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\extensions.py";      DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\models.py";          DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\wsgi.py";            DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\requirements.txt";   DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppRoot}\Lancer_DioplayeServices.bat"; DestDir: "{app}"; Flags: ignoreversion

; --- Routes ---
Source: "{#AppRoot}\routes\*"; DestDir: "{app}\routes"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Templates ---
Source: "{#AppRoot}\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Static ---
Source: "{#AppRoot}\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Dossier instance (base de donnees) - modifiable par l'utilisateur
Name: "{app}\instance"; Flags: uninsalwaysuninstall

[Icons]
; Menu Demarrer
Name: "{group}\Dioplaye Services";              Filename: "{app}\Lancer_DioplayeServices.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13
Name: "{group}\Desinstaller Dioplaye Services"; Filename: "{uninstallexe}"

; Bureau
Name: "{commondesktop}\Dioplaye Services"; Filename: "{app}\Lancer_DioplayeServices.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13

[Run]
; 1. Creer le venv Python
Filename: "{sys}\cmd.exe"; Parameters: "/c python -m venv ""{app}\venv"""; \
  Flags: runhidden waituntilterminated; \
  StatusMsg: "Creation de l'environnement Python..."; \
  Description: "Environnement Python"

; 2. Installer les dependances
Filename: "{sys}\cmd.exe"; Parameters: "/c ""{app}\venv\Scripts\python.exe"" -m pip install --quiet --no-warn-script-location -r ""{app}\requirements.txt"""; \
  Flags: runhidden waituntilterminated; \
  StatusMsg: "Installation des dependances (peut prendre 1-2 minutes)..."; \
  Description: "Dependances Flask"

; 3. Lancer apres installation (optionnel)
Filename: "{app}\Lancer_DioplayeServices.bat"; \
  Description: "Lancer Dioplaye Services maintenant"; \
  Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
; Supprimer venv et pycache a la desinstallation
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
{ ============================================================
   Verification : Python doit etre installe et dans le PATH
  ============================================================ }

function PythonInstalle: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\cmd.exe'),
                 '/c python --version',
                 '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  if not PythonInstalle then
  begin
    MsgBox(
      'Python n''est pas installe ou n''est pas dans le PATH.' + #13#10 + #13#10 +
      'Veuillez installer Python 3.10 ou superieur depuis :' + #13#10 +
      'https://www.python.org/downloads/' + #13#10 + #13#10 +
      'Cochez "Add Python to PATH" lors de l''installation.',
      mbError, MB_OK
    );
    Result := False;
  end
  else
    Result := True;
end;
