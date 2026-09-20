[Setup]
AppName=Files Organizer
AppVersion=1.0
AppPublisher=Migi Gustian
DefaultDirName={autopf}\Files Organizer
DefaultGroupName=Files Organizer
OutputDir=dist
OutputBaseFilename=FilesOrganizer_Setup
SetupIconFile=assets\organize_files.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Files Organizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Files Organizer"; Filename: "{app}\Files Organizer.exe"
Name: "{group}\{cm:UninstallProgram,Files Organizer}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Files Organizer"; Filename: "{app}\Files Organizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Files Organizer.exe"; Description: "{cm:LaunchProgram,Files Organizer}"; Flags: nowait postinstall skipifsilent
