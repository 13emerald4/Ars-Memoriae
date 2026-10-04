' Adds Memorization App background services to Windows Startup
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strRepoRoot = FSO.GetParentFolderName(strScriptDir)
strStartup = WshShell.SpecialFolders("Startup")
strShortcutPath = strStartup & "\Memorize_App_AutoStart.lnk"

Set oShortcut = WshShell.CreateShortcut(strShortcutPath)
oShortcut.TargetPath = "wscript.exe"
oShortcut.Arguments = Chr(34) & strScriptDir & "\start_servers_silent.vbs" & Chr(34)
oShortcut.WorkingDirectory = strRepoRoot
oShortcut.Description = "Start Memorization App Background Services on Windows Login"
oShortcut.Save

WScript.Echo "Success: Auto-start enabled! The app services will start silently whenever you log into Windows, so your Chrome New Tab shortcut will always work instantly."
