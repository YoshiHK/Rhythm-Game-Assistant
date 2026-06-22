param(
    # ------------------------------------------------------------
    # Harness / repo root
    # ------------------------------------------------------------
    [string]$HarnessRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository",

    # ------------------------------------------------------------
    # UMI project root
    # ------------------------------------------------------------
    [string]$UMIRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\engine\Unified Ingestion Manager\Unified Ingestion Manager",

    # ------------------------------------------------------------
    # Input locations
    # ------------------------------------------------------------
    [string]$OfflineValidationRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Tips Output Meta\offline_validation",
    [string]$RuntimeRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime",

    # ------------------------------------------------------------
    # Optional
    # ------------------------------------------------------------
    [string]$OutputReport = "",
    [switch]$SkipStrictRuntimeVerify
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor DarkCyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "===========================================================" -ForegroundColor DarkCyan
}

function Assert-File($PathToCheck, $Label) {
    if (-not (Test-Path -LiteralPath $PathToCheck)) {
        throw "$Label not found: $PathToCheck"
    }
}

function Ensure-Dir($DirPath) {
    if (-not (Test-Path -LiteralPath $DirPath)) {
        New-Item -ItemType Directory -Path $DirPath -Force | Out-Null
    }
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Push-Location $HarnessRoot

try {
    $PythonBin         = Join-Path $HarnessRoot ".venv\Scripts\python.exe"
    $DeploymentGatePy  = Join-Path $HarnessRoot "deployment_gate.py"
    $SrcRoot           = Join-Path $UMIRoot "src"
    $StrictVerifyPy    = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_runtime_bundle_strict.py"
    $ArtifactsRoot     = Join-Path $HarnessRoot "artifacts"

    $InventoryDb = Join-Path $RuntimeRoot "ingestions\file_scan_inventory.db"
    $AssetDb     = Join-Path $RuntimeRoot "assets\chart_assets.db"
    $PatternDb   = Join-Path $RuntimeRoot "features\chart_patterns.db"

    $Timestamp  = Get-Date -Format "yyyy-MM-dd_HHmmss"
    $ReportRoot = Join-Path $ArtifactsRoot ("deployment_gate_" + $Timestamp)
    Ensure-Dir $ReportRoot

    if ([string]::IsNullOrWhiteSpace($OutputReport)) {
        $OutputReport = Join-Path $ReportRoot "deployment_gate_report.json"
    }

    $StrictVerifyJson = Join-Path $ReportRoot "verify_runtime_bundle_strict.json"

    # ------------------------------------------------------------
    # Validate required files
    # ------------------------------------------------------------
    Assert-File $PythonBin "Venv python"
    Assert-File $DeploymentGatePy "deployment_gate.py"

    if (-not $SkipStrictRuntimeVerify) {
        Assert-File $StrictVerifyPy "verify_runtime_bundle_strict.py"
    }

    Assert-File $InventoryDb "file_scan_inventory.db"
    Assert-File $AssetDb "chart_assets.db"
    Assert-File $PatternDb "chart_patterns.db"

    # ------------------------------------------------------------
    # Resolve latest offline validation report
    # ------------------------------------------------------------
    $OfflineReport = Get-ChildItem `
        -LiteralPath $OfflineValidationRoot `
        -Recurse -Filter "offline_validation_report.json" |
        Sort-Object LastWriteTime |
        Select-Object -Last 1

    if (-not $OfflineReport) {
        throw "offline_validation_report.json not found under $OfflineValidationRoot"
    }

    # ------------------------------------------------------------
    # Resolve latest runtime_index.json
    # ------------------------------------------------------------
    $RuntimeIndex = Get-ChildItem `
        -LiteralPath (Resolve-Path $HarnessRoot).Path `
        -Recurse -Filter "runtime_index.json" |
        Sort-Object LastWriteTime |
        Select-Object -Last 1

    if (-not $RuntimeIndex) {
        throw "runtime_index.json not found in repository tree"
    }

    Write-Step "Deployment Gate - Environment"
    Write-Host "HarnessRoot    : $HarnessRoot"
    Write-Host "UMIRoot        : $UMIRoot"
    Write-Host "Python         : $PythonBin"
    Write-Host "RuntimeRoot    : $RuntimeRoot"
    Write-Host "InventoryDb    : $InventoryDb"
    Write-Host "AssetDb        : $AssetDb"
    Write-Host "PatternDb      : $PatternDb"
    Write-Host "Offline report : $($OfflineReport.FullName)"
    Write-Host "Runtime index  : $($RuntimeIndex.FullName)"
    Write-Host "Output report  : $OutputReport"
    Write-Host "ReportRoot     : $ReportRoot"

    # ------------------------------------------------------------
    # 1) Strict runtime verification (Path A)
    # ------------------------------------------------------------
    if (-not $SkipStrictRuntimeVerify) {
        Write-Step "1) Strict runtime bundle verification (Path A)"

        & $PythonBin $StrictVerifyPy `
            --file-scan-db $InventoryDb `
            --chart-assets-db $AssetDb `
            --chart-patterns-db $PatternDb `
            --json-out $StrictVerifyJson

        if ($LASTEXITCODE -ne 0) {
            throw "verify_runtime_bundle_strict failed. See $StrictVerifyJson"
        }
    }
    else {
        Write-Host "[SKIP] Strict runtime verification skipped" -ForegroundColor Yellow
    }

    # ------------------------------------------------------------
    # 2) Deployment gate (Path B + intersection)
    # ------------------------------------------------------------
    Write-Step "2) Deployment gate"

    Write-Host "[DEPLOYMENT-GATE] Python        : $PythonBin" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Offline report: $($OfflineReport.FullName)" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Runtime index : $($RuntimeIndex.FullName)" -ForegroundColor Cyan
    Write-Host "[DEPLOYMENT-GATE] Output report : $OutputReport" -ForegroundColor Cyan

    & $PythonBin $DeploymentGatePy `
        --offline-validation-report $OfflineReport.FullName `
        --runtime-index $RuntimeIndex.FullName `
        --require-runtime-index `
        --output $OutputReport

    if ($LASTEXITCODE -ne 0) {
        throw "Deployment gate failed"
    }

    # ------------------------------------------------------------
    # 3) Summary
    # ------------------------------------------------------------
    Write-Step "3) Deployment Gate Completed"

    if (Test-Path -LiteralPath $StrictVerifyJson) {
        Write-Host "Strict verify JSON : $StrictVerifyJson"
    }

    Write-Host "Deployment report  : $OutputReport"
    Write-Host "[DEPLOYMENT-GATE] PASS" -ForegroundColor Green
}
finally {
    Pop-Location
}
