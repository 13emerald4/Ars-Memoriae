' Creates a Windows Desktop shortcut for the Memorization App
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strRepoRoot = FSO.GetParentFolderName(strScriptDir)
strDesktop = WshShell.SpecialFolders("Desktop")
strShortcutPath = strDesktop & "\Memorize App.lnk"

Set oShortcut = WshShell.CreateShortcut(strShortcutPath)
oShortcut.TargetPath = "wscript.exe"
oShortcut.Arguments = Chr(34) & strScriptDir & "\start_app_silent.vbs" & Chr(34)
oShortcut.WorkingDirectory = strRepoRoot
oShortcut.Description = "Launch Memorization App and Open in Chrome"

' Detect Chrome icon if available
If FSO.FileExists("C:\Program Files\Google\Chrome\Application\chrome.exe") Then
    oShortcut.IconLocation = "C:\Program Files\Google\Chrome\Application\chrome.exe,0"
ElseIf FSO.FileExists("C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") Then
    oShortcut.IconLocation = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe,0"
ElseIf FSO.FileExists(WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe") Then
    oShortcut.IconLocation = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe,0"
End If

oShortcut.Save

WScript.Echo "Success: 'Memorize App' shortcut created on your Desktop!"
