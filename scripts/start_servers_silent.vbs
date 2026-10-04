' Checks ports and starts any missing Memorization App services invisibly
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

Function IsPortListening(port)
    Dim oExec, strOut
    Set oExec = WshShell.Exec("cmd.exe /c netstat -ano | findstr :" & port & ".*LISTENING")
    strOut = oExec.StdOut.ReadAll
    IsPortListening = (Len(Trim(strOut)) > 0)
End Function
