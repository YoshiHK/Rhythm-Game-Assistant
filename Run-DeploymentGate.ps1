param(
    [string]$RepoRoot = ".",
    [string]$OfflineValidationRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Tips Output Meta\offline_validation",
    [string]$OutputReport = ".\deployment_gate_report.json"
)

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Push-Location $RepoRoot

try {
    $PythonBin = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $PythonBin)) {
        throw "Venv python not found: $PythonBin"
    }

    $OfflineReport = Get-ChildItem `
        $OfflineValidationRoot `
        -Recurse -Filter "offline_validation_report.json" |
        Sort-Object LastWriteTime |
        Select-Object -Last 1

    if (-not $OfflineReport) {
        throw "offline_validation_report.json not found under $OfflineValidationRoot"
    }

    $RuntimeIndex = Get-ChildItem `
        (Resolve-Path ".").Path `
        -Recurse -Filter "runtime_index.json" |
        Sort-Object LastWriteTime |
        Select-Object -Last 1

    if (-not $RuntimeIndex) {
        throw "runtime_index.json not found in repository tree"
    }

    Write-Host "[DEPLOYMENT-GATE] Python        : $PythonBin" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Offline report: $($OfflineReport.FullName)" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Runtime index : $($RuntimeIndex.FullName)" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Output report : $OutputReport" -ForegroundColor Cyan

    & $PythonBin .\deployment_gate.py `
        --offline-validation-report $OfflineReport.FullName `
        --runtime-index $RuntimeIndex.FullName `
        --require-runtime-index `
        --output $OutputReport

    if ($LASTEXITCODE -ne 0) {
        throw "Deployment gate failed"
    }

    Write-Host "[DEPLOYMENT-GATE] PASS" -ForegroundColor Green
}
finally {
    Pop-Location
}