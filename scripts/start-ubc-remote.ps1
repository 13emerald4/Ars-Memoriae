# ==============================================================================
# UBC Library Remote Access Launcher (Memorization & Code Lab)
# Creates a secure, encrypted HTTPS tunnel so you can access the app from any
# UBC Library computer (Mac M1, Windows lab PC, tablet, or phone).
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   🏛️  UBC LIBRARY REMOTE ACCESS TUNNEL LAUNCHER               " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsDir = Join-Path $repoRoot "tools"
if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir | Out-Null
}

# 1. Verify Local Services (FastAPI 8000, Vite 5173, Ollama 11434)
Write-Host "[1/3] Checking local servers..." -ForegroundColor Gray

$backendConn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
$frontendConn = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
$ollamaConn = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }

if (-not $backendConn -or -not $frontendConn -or -not $ollamaConn) {
    Write-Host "  -> Some local services are not running. Launching them now..." -ForegroundColor Yellow
    $startBatch = Join-Path $PSScriptRoot "check_and_start_services.bat"
    if (Test-Path $startBatch) {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$startBatch`"" -WindowStyle Hidden
        Start-Sleep -Seconds 4
    }
} else {
    Write-Host "  ✓ FastAPI (8000), Vite (5173), and Ollama (11434) are active." -ForegroundColor Green
}

# 2. Prepare Cloudflared Tunnel Utility
Write-Host "[2/3] Preparing secure HTTPS tunnel..." -ForegroundColor Gray

$cloudflaredCmd = Get-Command "cloudflared" -ErrorAction SilentlyContinue
$cloudflaredExe = if ($cloudflaredCmd) { $cloudflaredCmd.Source } else { Join-Path $toolsDir "cloudflared.exe" }

if (-not (Test-Path $cloudflaredExe) -and -not $cloudflaredCmd) {
    Write-Host "  -> Downloading portable cloudflared single-file binary to tools/..." -ForegroundColor Yellow
    $cfUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $cfUrl -OutFile $cloudflaredExe -UseBasicParsing
        Write-Host "  ✓ Download complete." -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️ Could not download cloudflared directly: $_" -ForegroundColor Red
    }
}

$tunnelUrl = ""

if (Test-Path $cloudflaredExe) {
    Write-Host "[3/3] Starting Cloudflare Quick Tunnel on port 5173..." -ForegroundColor Gray
    $logFile = Join-Path $env:TEMP "cloudflared_memorization.log"
    if (Test-Path $logFile) { Remove-Item $logFile -Force }

    $cfProc = Start-Process -FilePath $cloudflaredExe -ArgumentList "tunnel --url http://127.0.0.1:5173" -RedirectStandardError $logFile -PassThru -WindowStyle Hidden

    Write-Host "  -> Waiting for tunnel connection..." -ForegroundColor Gray
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 800
        if (Test-Path $logFile) {
            $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
            if ($content -match "https://[a-zA-Z0-9\-]+\.trycloudflare\.com") {
                $tunnelUrl = $matches[0]
                break
            }
        }
    }
}

if (-not $tunnelUrl) {
    # Fallback to SSH localhost.run (zero software download needed)
    Write-Host "  -> Using SSH zero-download tunnel fallback..." -ForegroundColor Yellow
    $sshCmd = Get-Command "ssh" -ErrorAction SilentlyContinue
    if ($sshCmd) {
        $sshLog = Join-Path $env:TEMP "ssh_tunnel.log"
        if (Test-Path $sshLog) { Remove-Item $sshLog -Force }
        $sshProc = Start-Process -FilePath "ssh" -ArgumentList "-R 80:127.0.0.1:5173 -o StrictHostKeyChecking=no nokey@localhost.run" -RedirectStandardOutput $sshLog -PassThru -WindowStyle Hidden
        for ($i = 0; $i -lt 25; $i++) {
            Start-Sleep -Milliseconds 800
            if (Test-Path $sshLog) {
                $content = Get-Content $sshLog -Raw -ErrorAction SilentlyContinue
                if ($content -match "https://[a-zA-Z0-9\-]+\.lhr\.life") {
                    $tunnelUrl = $matches[0]
                    break
                }
            }
        }
    }
}

if ($tunnelUrl) {
    try {
        Set-Clipboard -Value $tunnelUrl
        $copiedText = " (COPIED TO YOUR CLIPBOARD!)"
    } catch {
        $copiedText = ""
    }

    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "  🎉 YOUR SECURE UBC LIBRARY ACCESS URL IS LIVE:                 " -ForegroundColor Green
    Write-Host ""
    Write-Host "       $tunnelUrl" -ForegroundColor White -BackgroundColor DarkBlue
    Write-Host "       $copiedText" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "HOW TO ACCESS FROM THE UBC LIBRARY MAC / LAB PC:" -ForegroundColor Cyan
    Write-Host "  1. Sit down at any Mac M1 or computer in Koerner / IKB / Woodward." -ForegroundColor Gray
    Write-Host "  2. Open Chrome or Safari and paste this link." -ForegroundColor Gray
    Write-Host "  3. Log in with your email/password. All cards, code lab, and LLM" -ForegroundColor Gray
    Write-Host "     grading will execute through this tunnel!" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press Ctrl+C or close this window when your study session is done." -ForegroundColor DarkGray
    Write-Host ""

    # Keep process open so tunnel stays alive
    try {
        while ($true) {
            Start-Sleep -Seconds 2
        }
    } finally {
        if ($cfProc -and -not $cfProc.HasExited) { Stop-Process -Id $cfProc.Id -Force -ErrorAction SilentlyContinue }
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to establish remote tunnel automatically." -ForegroundColor Red
    Write-Host "Check your internet connection or see log at $logFile" -ForegroundColor Yellow
}
