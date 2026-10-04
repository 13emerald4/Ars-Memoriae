' Launches background services silently, then opens Chrome in dedicated app-window mode
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strBatPath = strScriptDir & "\check_and_start_services.bat"

' 1. Start services completely hidden
WshShell.Run Chr(34) & strBatPath & Chr(34), 0, True

' 2. Short wait to ensure port 5173 is responsive
WScript.Sleep 1000

' 3. Detect Chrome Path
Dim strChrome
strChrome = ""

If FSO.FileExists("C:\Program Files\Google\Chrome\Application\chrome.exe") Then
    strChrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
ElseIf FSO.FileExists("C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") Then
    strChrome = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
ElseIf FSO.FileExists(WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe") Then
    strChrome = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe"
End If

If strChrome <> "" Then
    WshShell.Run Chr(34) & strChrome & Chr(34) & " --app=http://localhost:5173", 1, False
Else
    WshShell.Run "http://localhost:5173", 1, False
End If
