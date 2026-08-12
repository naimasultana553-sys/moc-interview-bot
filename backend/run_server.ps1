# AI Mock Interview Bot - server launcher (Windows)
# Starts the FastAPI app with the bundled virtualenv and logs to
# server_out.log / server_err.log in this directory.

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
$OutLog = Join-Path $BackendDir "server_out.log"
$ErrLog = Join-Path $BackendDir "server_err.log"

if (-not (Test-Path $Python)) {
    Write-Error "Virtualenv not found at $Python. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}

# Stop any process already bound to the configured port (default 8000).
$port = 8000
if (Test-Path (Join-Path $BackendDir ".env")) {
    $match = Select-String -Path (Join-Path $BackendDir ".env") -Pattern "^PORT=(\d+)$"
    if ($match) { $port = [int]$match.Matches[0].Groups[1].Value }
}
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Stopping existing server on port $port (PID $($existing.OwningProcess))..."
    Stop-Process -Id $existing.OwningProcess -Force
    Start-Sleep -Seconds 1
}

Write-Host "Starting Mock Interview Bot on http://127.0.0.1:$port"
Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$port", "--log-level", "info" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -WindowStyle Hidden

Start-Sleep -Seconds 3
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Server is up: $($health.Content)"
} catch {
    Write-Host "Server did not respond yet. Check $ErrLog"
}
