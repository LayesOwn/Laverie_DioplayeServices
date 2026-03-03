Dim WshShell, oShortcut, sBatPath, sIconPath

WshShell  = CreateObject("WScript.Shell")
sBatPath  = WScript.ScriptFullName
sBatPath  = Left(sBatPath, InStrRev(sBatPath, "\")) & "Lancer_DioplayeServices.bat"

' Raccourci sur le bureau
oShortcut = WshShell.CreateShortcut( _
    WshShell.SpecialFolders("Desktop") & "\Dioplaye Services.lnk")

oShortcut.TargetPath       = sBatPath
oShortcut.WorkingDirectory = Left(sBatPath, InStrRev(sBatPath, "\") - 1)
oShortcut.WindowStyle      = 1
oShortcut.Description      = "Lancer l'application Dioplaye Services - Laverie"

oShortcut.Save

MsgBox "Raccourci cree sur le bureau !" & vbCrLf & vbCrLf & _
       "Double-cliquez sur 'Dioplaye Services' pour lancer l'application.", _
       vbInformation, "Dioplaye Services"
