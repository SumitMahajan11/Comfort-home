# scripts/run_product.ps1
# One-command local runner for ClimateAdapt-Comfort v2 decision-support product.
# Validates manifest checksums, audits CPWD cost rates, and starts API & Web Frontend.

param (
    [switch]$AllowUnfilledCosts = $false,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " ClimateAdapt-Comfort v2: One-Command Product Runner" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Locate Python Virtual Environment
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# 1. Validate data/export Checksums
Write-Host "`n[1/3] Verifying data/export/manifest.json integrity checksums..." -ForegroundColor Yellow
$VerifyScript = @"
import sys, os
from api.loader import ArtifactStore
store = ArtifactStore()
try:
    store.verify_and_load()
    print(f'Verification PASSED: {len(store.manifest_data.get(\"files\", {}))} artifacts match manifest SHA256.')
except Exception as e:
    print(f'FATAL Checksum Error: {e}', file=sys.stderr)
    sys.exit(1)
"@
& $PythonExe -c $VerifyScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Artifact checksum verification failed! Refusing to start." -ForegroundColor Red
    exit 1
}

# 2. Run CPWD Cost Rate Validator
Write-Host "`n[2/3] Auditing CPWD DSR rate schedules..." -ForegroundColor Yellow
$CostValidator = Join-Path $ProjectRoot "tools\validate_costs.py"
& $PythonExe $CostValidator
$CostExitCode = $LASTEXITCODE

if ($CostExitCode -ne 0) {
    if ($AllowUnfilledCosts) {
        Write-Host "`n[WARNING] CPWD DSR cost rates contain 'TO BE FILLED' placeholders." -ForegroundColor Yellow
        Write-Host "Continuing because -AllowUnfilledCosts was specified." -ForegroundColor Yellow
        Write-Host "Under Decision D-025, monetary costs will display as 'Rates unpopulated in official DSR schedule'." -ForegroundColor Yellow
    } else {
        Write-Host "`n================================================================================" -ForegroundColor Red
        Write-Host " PRODUCT STARTUP BLOCKED: UNFILLED COST RATES (Decision D-025)" -ForegroundColor Red
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "CPWD DSR cost rates are still marked 'TO BE FILLED'." -ForegroundColor Red
        Write-Host "Under non-negotiable project honesty rules, release is blocked while placeholders remain." -ForegroundColor Red
        Write-Host ""
        Write-Host "To resolve:" -ForegroundColor White
        Write-Host "  1. Populate official rates in data/costs/dsr_rates_template.csv and run tools/csv_to_dsr_json.py" -ForegroundColor White
        Write-Host "  2. Or run with -AllowUnfilledCosts to start with strict null-gated cost warnings:" -ForegroundColor White
        Write-Host "     .\scripts\run_product.ps1 -AllowUnfilledCosts" -ForegroundColor Cyan
        exit 1
    }
}

# 3. Start Backend & Frontend Services
Write-Host "`n[3/3] Launching FastAPI Backend and Next.js Web Frontend..." -ForegroundColor Yellow
Write-Host "  FastAPI Service:   http://127.0.0.1:$ApiPort (Docs: http://127.0.0.1:$ApiPort/docs)" -ForegroundColor Green
Write-Host "  Next.js Frontend:  http://localhost:$WebPort" -ForegroundColor Green
Write-Host "`nStarting services in background processes. Press Ctrl+C in their windows to stop.`n"

# Start FastAPI uvicorn
$ApiCmd = "$PythonExe -m uvicorn api.main:app --host 127.0.0.1 --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'ClimateAdapt-Comfort API' -ForegroundColor Cyan; $ApiCmd"

# Start Next.js frontend
$WebDir = Join-Path $ProjectRoot "web"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$WebDir'; Write-Host 'ClimateAdapt-Comfort Frontend' -ForegroundColor Cyan; npm run dev -- -p $WebPort"

Write-Host "Services dispatched successfully!" -ForegroundColor Green
