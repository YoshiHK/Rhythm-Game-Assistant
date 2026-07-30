# backend_start.ps1
# RGA Backend Startup (Phase-safe wiring only)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ''
Write-Host '=== Rhythm Game Assistant Backend Startup ===' -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"

# Activate virtual environment
$VenvActivate = Join-Path $ProjectRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $VenvActivate)) {
    throw "Virtual environment not found: $VenvActivate"
}

. $VenvActivate

# PYTHONPATH wiring
$env:PYTHONPATH = "$ProjectRoot\src;$ProjectRoot\src\rhythm_ingestion"

# Token check
if (-not $env:SOFTR_API_TOKEN) {
    Write-Warning 'SOFTR_API_TOKEN is not set in the current environment.'
    Write-Warning 'Authorization-protected API calls will fail.'
}
else {
    Write-Host 'SOFTR_API_TOKEN detected.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Starting FastAPI backend...' -ForegroundColor Green
Write-Host 'URL:  http://127.0.0.1:8000/docs'
Write-Host 'OpenAPI: http://127.0.0.1:8000/openapi.json'
Write-Host ''

python -m uvicorn main:app --reload --port 8000
