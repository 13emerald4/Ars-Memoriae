' Launches background services silently, then opens Chrome to http://localhost:5173
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strRepoRoot = FSO.GetParentFolderName(strScriptDir)

' 1. Check Ollama (:11434)
If Not IsPortListening(11434) Then
    WshShell.Run "cmd.exe /c start /b ollama serve", 0, False
End If

' 2. Check FastAPI Backend (:8000)
If Not IsPortListening(8000) Then
    strBackendCmd = "cmd.exe /c ""cd /d """ & strRepoRoot & "\backend"" && """ & strRepoRoot & "\backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --port 8000"""
    WshShell.Run strBackendCmd, 0, False
End If

' 3. Check Vite Frontend (:5173)
If Not IsPortListening(5173) Then
    strFrontendCmd = "cmd.exe /c ""cd /d """ & strRepoRoot & "\frontend"" && npm run dev"""
    WshShell.Run strFrontendCmd, 0, False
End If

' 4. Wait for Vite listener to open (up to 15 seconds)
Dim iAttempts
iAttempts = 0
Do While Not IsPortListening(5173) And iAttempts < 30
    WScript.Sleep 500
    iAttempts = iAttempts + 1
Loop

' 5. Detect Chrome and launch
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
    WshShell.Run Chr(34) & strChrome & Chr(34) & " http://localhost:5173", 1, False
Else
    WshShell.Run "http://localhost:5173", 1, False
End If

Function IsPortListening(port)
    Dim oExec, strOut
    Set oExec = WshShell.Exec("cmd.exe /c netstat -ano | findstr :" & port & ".*LISTENING")
    strOut = oExec.StdOut.ReadAll
    IsPortListening = (Len(Trim(strOut)) > 0)
End Function
