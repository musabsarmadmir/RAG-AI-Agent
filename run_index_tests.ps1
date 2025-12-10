<#
run_index_tests.ps1

Run full end-to-end index tests:
 - load `local.env` into the session
 - start the FastAPI server in background
 - wait for health
 - run parsing, create providers, upload, rebuild, verify and query tests
 - run embedding sanity test
 - stop the server and report status

Run from repository root with venv activated: `.
un_index_tests.ps1`
#>
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $Root

Write-Host "[run_index_tests] Running from: $Root"

function Load-LocalEnv {
    $envFile = Join-Path $Root 'local.env'
    if (-not (Test-Path $envFile)) { Write-Error "local.env not found at $envFile"; return $false }
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            if ($line -match '^[\s]*([^=]+?)[\s]*=[\s]*(?:"?)(.*?)(?:"?)[\s]*$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"')
                # Hide long keys from output
                if ($name -eq 'OPENAI_API_KEY') { Set-Item -Path "Env:$name" -Value $value } else { Set-Item -Path "Env:$name" -Value $value; Write-Host "Loaded env: $name = '$value'" }
            }
        }
    }
    return $true
}

if (-not (Load-LocalEnv)) { Write-Error "Failed to load local.env"; exit 1 }

# Find python in venv or fallback
$venvPy = Join-Path $Root '.venv\Scripts\python.exe'
if (Test-Path $venvPy) { $Python = $venvPy } else { $Python = 'python' }
Write-Host "Using python: $Python"

# Start uvicorn in background
Write-Host "[run_index_tests] Starting uvicorn in background..."
$uvArgs = '-m uvicorn app.main:app --host 127.0.0.1 --port 8000'
$proc = Start-Process -FilePath $Python -ArgumentList $uvArgs -NoNewWindow -PassThru
Write-Host "uvicorn PID: $($proc.Id)"

# Wait for health
Write-Host "Waiting for /v1/health..."
$url = 'http://127.0.0.1:8000/v1/health'
$ready = $false
for ($i=0; $i -lt 40; $i++) {
    try {
        $r = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5
        Write-Host "Health: $($r.status)"
        $ready = $true; break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) { Write-Error "Server not ready"; if ($proc -and -not $proc.HasExited) { $proc | Stop-Process -Force }; exit 2 }

# Run parsing script to populate sample-files/Aimdtalk.xlsx and rag-data
Write-Host "Running PDF parser -> metadata..."
& $Python '.\scripts\parse_pdf_to_metadata.py' --provider Fatima --pdf 'sample-files\Fatima_AI_Services-1.pdf'

# Run test_all (full pipeline) which creates providers, uploads, rebuilds, verifies and queries
Write-Host "Running full test runner scripts/test_all.py (this may take a few minutes)"
& $Python '.\scripts\test_all.py'
$rc = $LASTEXITCODE
if ($rc -ne 0) { Write-Error "scripts/test_all.py failed with exit code $rc" }

# Embedding sanity check
Write-Host "Running embedding sanity test"
& $Python '.\scripts\test_embeddings_openai.py'
$embRc = $LASTEXITCODE
if ($embRc -ne 0) { Write-Warning "Embedding test failed (exit $embRc)" }

# Verify Aimdtalk.xlsx sheet
Write-Host "Verifying sample-files/Aimdtalk.xlsx"
& $Python '.\scripts\verify_aimdtalk.py'
$verifyRc = $LASTEXITCODE
if ($verifyRc -ne 0) { Write-Warning "Aimdtalk verification returned $verifyRc" }

Write-Host "Stopping uvicorn (PID $($proc.Id))"
try { if ($proc -and -not $proc.HasExited) { $proc | Stop-Process -Force } } catch { Write-Warning "Failed to stop uvicorn: $_" }

if ($rc -ne 0 -or $embRc -ne 0 -or $verifyRc -ne 0) { Write-Error "One or more steps failed"; exit 5 } else { Write-Host "All tests completed successfully"; exit 0 }
