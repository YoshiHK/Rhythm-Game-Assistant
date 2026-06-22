param(
    # ------------------------------------------------------------
    # Harness root (script location)
    # ------------------------------------------------------------
    [string]$HarnessRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository",

    # ------------------------------------------------------------
    # UMI project root
    # ------------------------------------------------------------
    [string]$UMIRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\engine\Unified Ingestion Manager\Unified Ingestion Manager",

    # ------------------------------------------------------------
    # Runtime / source
    # ------------------------------------------------------------
    [string]$SourceDir = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File",
    [string]$RuntimeRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime",

    # ------------------------------------------------------------
    # Optional
    # ------------------------------------------------------------
    [string]$JsonOut = "",
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor DarkCyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "===========================================================" -ForegroundColor DarkCyan
}

function Assert-File($PathToCheck, $Label) {
    if (-not (Test-Path $PathToCheck)) {
        throw "$Label not found: $PathToCheck"
    }
}

function Ensure-Dir($DirPath) {
    if (-not (Test-Path $DirPath)) {
        New-Item -ItemType Directory -Path $DirPath -Force | Out-Null
    }
}

# ------------------------------------------------------------
# Resolve paths
# ------------------------------------------------------------

# FIRST: resolve core roots (MUST come before usage)
$SrcRoot       = Join-Path $UMIRoot "src"
$ArtifactsRoot = Join-Path $HarnessRoot "artifacts"

# runtime directories
$InventoryDir = Join-Path $RuntimeRoot "ingestions"
$AssetDir     = Join-Path $RuntimeRoot "assets"
$PatternDir   = Join-Path $RuntimeRoot "features"

# primary script path
$ScriptPath = Join-Path $HarnessRoot "Update_Runtime_Dbs.py"

# verification scripts
$VerifyFullBundlePy    = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_full_bundle.py"
$VerifyRuntimeStrictPy = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_runtime_bundle_strict.py"

# ------------------------------------------------------------
# Ensure directories exist
# ------------------------------------------------------------
Ensure-Dir $InventoryDir
Ensure-Dir $AssetDir
Ensure-Dir $PatternDir
Ensure-Dir $ArtifactsRoot

# ------------------------------------------------------------
# Assert required files
# ------------------------------------------------------------
Assert-File $ScriptPath
Assert-File $VerifyFullBundlePy
Assert-File $VerifyRuntimeStrictPy

# ------------------------------------------------------------
# Report bundle
# ------------------------------------------------------------
$Timestamp  = Get-Date -Format "yyyy-MM-dd_HHmmss"
$ReportRoot = Join-Path $ArtifactsRoot ("runtime_db_build_" + $Timestamp)
Ensure-Dir $ReportRoot

$PipelineLog      = Join-Path $ReportRoot "update_runtime_dbs.log"
$StrictVerifyJson = Join-Path $ReportRoot "verify_runtime_bundle_strict.json"

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------
Write-Step "Update Runtime DBs - Environment"

Push-Location $HarnessRoot
try {
    $env:PYTHONPATH = $SrcRoot

    Write-Host "HarnessRoot : $HarnessRoot"
    Write-Host "UMIRoot     : $UMIRoot"
    Write-Host "SourceDir   : $SourceDir"
    Write-Host "RuntimeRoot : $RuntimeRoot"
    Write-Host "PYTHONPATH  : $env:PYTHONPATH"

    # ------------------------------------------------------------
    # Execute updater
    # ------------------------------------------------------------
    Write-Step "1) Run Update_Runtime_Dbs.py"

    $Args = @(
        $ScriptPath,
        "--source-dir", $SourceDir,
        "--runtime-root", $RuntimeRoot
    )

    if (-not [string]::IsNullOrWhiteSpace($JsonOut)) {
        $Args += @("--json-out", $JsonOut)
    }

    & python @Args 2>&1 | Tee-Object -FilePath $PipelineLog

    if ($LASTEXITCODE -ne 0) {
        throw "Update_Runtime_Dbs.py failed"
    }

    # ------------------------------------------------------------
    # Post-build snapshot
    # ------------------------------------------------------------
    Write-Step "2) Post-build DB snapshot"
    @"
import sqlite3

inventory_db = r"$InventoryDir\file_scan_inventory.db"
asset_db     = r"$AssetDir\chart_assets.db"
pattern_db   = r"$PatternDir\chart_patterns.db"

def count(db, table):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()

print("[POST] inventory =", count(inventory_db, "file_scan_inventory"))
print("[POST] assets    =", count(asset_db, "chart_assets"))
print("[POST] patterns  =", count(pattern_db, "chart_patterns"))
"@ | python -

    # ------------------------------------------------------------
    # Strict verification (Path A)
    # ------------------------------------------------------------
    if (-not $SkipVerify) {
        Write-Step "3) Strict runtime bundle verification"

        & python $VerifyRuntimeStrictPy `
            --file-scan-db (Join-Path $InventoryDir "file_scan_inventory.db") `
            --chart-assets-db (Join-Path $AssetDir "chart_assets.db") `
            --chart-patterns-db (Join-Path $PatternDir "chart_patterns.db") `
            --json-out $StrictVerifyJson

        if ($LASTEXITCODE -ne 0) {
            throw "verify_runtime_bundle_strict failed"
        }
    }
    else {
        Write-Host "[SKIP] Strict verification skipped" -ForegroundColor Yellow
    }

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------
    Write-Step "4) Update Completed"

    Write-Host "Inventory DB : $(Join-Path $InventoryDir 'file_scan_inventory.db')"
    Write-Host "Asset DB     : $(Join-Path $AssetDir 'chart_assets.db')"
    Write-Host "Pattern DB   : $(Join-Path $PatternDir 'chart_patterns.db')"
    Write-Host "Log file     : $PipelineLog"

    if (Test-Path $StrictVerifyJson) {
        Write-Host "Strict verify: $StrictVerifyJson"
    }

    if (-not [string]::IsNullOrWhiteSpace($JsonOut)) {
        Write-Host "Report JSON  : $JsonOut"
    }

    Write-Host ""
    Write-Host "✅ Runtime DB baseline build completed." -ForegroundColor Green
}
finally {
    Pop-Location
}