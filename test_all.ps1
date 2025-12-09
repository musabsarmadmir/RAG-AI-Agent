<#
Test_All PowerShell wrapper

Run this from the repository root. It will:
- load environment variables from `local.env` into the session
- start the FastAPI app in the background using the repository venv (if present)
- wait for the health endpoint to be ready
- run the Python test runner `scripts/test_all.py` which performs uploads, rebuild, index verification and queries
- stop the server process started by this script

Usage:
  # Ensure venv is activated or available at .\.venv\Scripts\python.exe
  .\test_all.ps1

#>
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $Root

Write-Host "[test_all] Running from: $Root"

function Load-LocalEnv {
    $envFile = Join-Path $Root 'local.env'
    if (-not (Test-Path $envFile)) { Write-Error "local.env not found at $envFile"; return $false }
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            if ($line -match '^[\s]*([^=]+?)[\s]*=[\s]*(?:"?)(.*?)(?:"?)[\s]*$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"')
                # Do not echo secrets
                if ($name -eq 'OPENAI_API_KEY') { Set-Item -Path "Env:$name" -Value $value } else { Set-Item -Path "Env:$name" -Value $value; Write-Host "Loaded env: $name = '$value'" }
            }
        }
    }
    return $true
}

if (-not (Load-LocalEnv)) { Write-Error "Failed to load local.env"; exit 1 }

# Locate python in .venv if available, otherwise fallback to system python
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $Python = $venvPy } else { $Python = 'python' }
Write-Host "Using python: $Python"

# Start uvicorn in background
Write-Host "[test_all] Starting uvicorn..."
$uvArgs = '-m uvicorn app.main:app --host 127.0.0.1 --port 8000'
$proc = Start-Process -FilePath $Python -ArgumentList $uvArgs -NoNewWindow -PassThru
Write-Host "[test_all] uvicorn PID: $($proc.Id)"

# Wait for health endpoint
Write-Host "[test_all] Waiting for /v1/health to become available..."
$url = 'http://127.0.0.1:8000/v1/health'
$ready = $false
for ($i=0; $i -lt 30; $i++) {
    try {
        $r = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5
        Write-Host "[test_all] Health OK: $($r.status)"
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    Write-Error "Server did not become ready in time. Check uvicorn logs."; if ($proc -and -not $proc.HasExited) { $proc | Stop-Process -Force } ; exit 2
}

# Run the Python test runner which executes the full checklist
Write-Host "[test_all] Running Python test runner: scripts/test_all.py"
& $Python '.\scripts\test_all.py'
$exitCode = $LASTEXITCODE

Write-Host "[test_all] Python runner exited with code: $exitCode"

# Stop uvicorn started by this script
try {
    if ($proc -and -not $proc.HasExited) {
        Write-Host "[test_all] Stopping uvicorn (PID $($proc.Id))"
        $proc | Stop-Process -Force
    }
} catch {
    Write-Warning "Failed to stop uvicorn: $_"
}

if ($exitCode -ne 0) { Write-Error "test_all failed (exit code $exitCode)"; exit $exitCode } else { Write-Host "test_all completed successfully"; exit 0 }
