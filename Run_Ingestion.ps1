param(
    # ------------------------------------------------------------
    # Harness root = where this script belongs
    # ------------------------------------------------------------
    [string]$HarnessRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository",

    # ------------------------------------------------------------
    # UMI root = actual Python project root
    # ------------------------------------------------------------
    [string]$UMIRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\engine\Unified Ingestion Manager\Unified Ingestion Manager",

    # ------------------------------------------------------------
    # Runtime / source
    # ------------------------------------------------------------
    [string]$SourceDir = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File",
    [string]$RuntimeRoot = "C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime",
    [switch]$RunOfflineAnalysis,
    [switch]$EnableConverterCache,

    # ------------------------------------------------------------
    # Verification / delete controls
    # ------------------------------------------------------------
    [switch]$SkipVerify,
    [switch]$RunSafeDeleteDryRun,
    [switch]$ExecuteSafeDelete,

    # ------------------------------------------------------------
    # Safe-delete policy knobs
    # ------------------------------------------------------------
    [int]$ExcludeRecentDays = 7,
    [string]$QuarantineDir = "",
    [switch]$IncludeTypeB,
    [switch]$AllowDeleteLastCopy,
    [string]$PathsJson = ""
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

# ------------------------------------------------------------
# Resolve canonical locations
# ------------------------------------------------------------
$OfflineRunner = Join-Path $UMIRoot "offline_pipeline_runner.py"
$SrcRoot       = Join-Path $UMIRoot "src"
$ArtifactsRoot = Join-Path $HarnessRoot "artifacts"

$VerifyFullBundlePy    = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_full_bundle.py"
$VerifyRuntimeStrictPy = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_runtime_bundle_strict.py"
$SafeDeletePy          = Join-Path $SrcRoot "rhythm_ingestion\writers\safety\safe_delete_candidates.py"
$DbRefreshPs           = Join-Path $HarnessRoot "Run_UpdateRuntimeDbs.ps1"

$InventoryDb = Join-Path $RuntimeRoot "ingestions\file_scan_inventory.db"
$AssetDb     = Join-Path $RuntimeRoot "assets\chart_assets.db"
$PatternDb   = Join-Path $RuntimeRoot "features\chart_patterns.db"

$Timestamp  = Get-Date -Format "yyyy-MM-dd_HHmmss"
$ReportRoot = Join-Path $ArtifactsRoot ("phase35_bundle_" + $Timestamp)
Ensure-Dir $ReportRoot

$PipelineLog      = Join-Path $ReportRoot "pipeline_stdout.log"
$VerifyJson       = Join-Path $ReportRoot "verify_full_bundle.json"
$StrictVerifyJson = Join-Path $ReportRoot "verify_runtime_bundle_strict.json"
$SafeDeleteJson   = Join-Path $ReportRoot "safe_delete_report.json"

# ------------------------------------------------------------
# Validate required files / dirs
# ------------------------------------------------------------
Assert-File $OfflineRunner "offline_pipeline_runner.py"
Assert-File $VerifyFullBundlePy "verify_full_bundle.py"
Assert-File $SafeDeletePy "safe_delete_candidates.py"
Assert-File $DbRefreshPs "Run_UpdateRuntimeDbs.ps1"

if (-not $SkipVerify) {
    Assert-File $VerifyRuntimeStrictPy "verify_runtime_bundle_strict.py"
}

Ensure-Dir $ArtifactsRoot
Ensure-Dir (Join-Path $RuntimeRoot "ingestions")
Ensure-Dir (Join-Path $RuntimeRoot "assets")
Ensure-Dir (Join-Path $RuntimeRoot "features")

# ------------------------------------------------------------
# IMPORTANT MODE NOTE
# ------------------------------------------------------------
# This script is an INCREMENTAL / RUNTIME test runner.
# Runtime DB baseline must already exist and is expected to be built by:
#   .\Run_UpdateRuntimeDbs.ps1
#
# This script does NOT refresh runtime DB baseline.
# It uses existing runtime DBs for:
# - pre/post idempotency checks
# - strict runtime bundle verification
# - optional legacy verification
# - optional safe-delete
# - optional converter-cache-assisted runtime exercise

Write-Step "Phase 3.5 / UMI v2.0 - Environment"
Push-Location $UMIRoot
try {
    $env:PYTHONPATH = $SrcRoot

    Write-Host "HarnessRoot   : $HarnessRoot"
    Write-Host "UMIRoot       : $UMIRoot"
    Write-Host "SourceDir     : $SourceDir"
    Write-Host "RuntimeRoot   : $RuntimeRoot"
    Write-Host "InventoryDb   : $InventoryDb"
    Write-Host "AssetDb       : $AssetDb"
    Write-Host "PatternDb     : $PatternDb"
    Write-Host "ArtifactsRoot : $ArtifactsRoot"
    Write-Host "ReportRoot    : $ReportRoot"
    Write-Host "PYTHONPATH    : $env:PYTHONPATH"
    Write-Host "ConverterCache: $EnableConverterCache"

    # ------------------------------------------------------------
    # 0) Baseline precondition check (DBs must already exist)
    # ------------------------------------------------------------
    Write-Step "0) Runtime baseline prerequisite"
    Assert-File $InventoryDb "file_scan_inventory.db"
    Assert-File $AssetDb "chart_assets.db"
    Assert-File $PatternDb "chart_patterns.db"

    Write-Host "[BASELINE] Existing runtime DB baseline detected."
    Write-Host "[BASELINE] If you need to rebuild baseline, run: .\Run_UpdateRuntimeDbs.ps1" -ForegroundColor DarkYellow

    # ------------------------------------------------------------
    # 0.5) Pre-run DB snapshot
    # ------------------------------------------------------------
    Write-Step "0.5) Pre-run DB snapshot"
    @"
import sqlite3

inventory_db = r"$InventoryDb"
asset_db     = r"$AssetDb"
pattern_db   = r"$PatternDb"

def count(db, table):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()

print("[PRE] inventory =", count(inventory_db, "file_scan_inventory"))
print("[PRE] assets    =", count(asset_db, "chart_assets"))
print("[PRE] patterns  =", count(pattern_db, "chart_patterns"))
"@ | python -

    # ------------------------------------------------------------
    # 1A) Runtime / incremental ingestion exercise
    # ------------------------------------------------------------
    Write-Step "1A) Run full offline pipeline (incremental/runtime test)"

    $OfflineArgs = @(
        $OfflineRunner,
        "--source_dir", $SourceDir
    )

    if ($EnableConverterCache) {
        $OfflineArgs += @(
            "--enable-converter-cache",
            "--file-scan-db", $InventoryDb,
            "--chart-assets-db", $AssetDb
        )
    }

    & python @OfflineArgs 2>&1 | Tee-Object -FilePath $PipelineLog

    if ($LASTEXITCODE -ne 0) {
        throw "offline_pipeline_runner failed. See $PipelineLog"
    }

    Write-Host "[NOTE] Runtime DB baseline was not rebuilt by this script." -ForegroundColor DarkYellow
    Write-Host "[NOTE] This run is intended to exercise ingestion/runtime behavior against existing DB baseline." -ForegroundColor DarkYellow

    # ------------------------------------------------------------
    # 1B) Optional offline analysis / artifact run
    # ------------------------------------------------------------
    if ($RunOfflineAnalysis) {
        Write-Step "1B) Optional offline analysis (artifact pipeline)"

        $OfflineAnalysisArgs = @(
            $OfflineRunner,
            "--source_dir", $SourceDir
        )

        if ($EnableConverterCache) {
            $OfflineAnalysisArgs += @(
                "--enable-converter-cache",
                "--file-scan-db", $InventoryDb,
                "--chart-assets-db", $AssetDb
            )
        }

        & python @OfflineAnalysisArgs

        if ($LASTEXITCODE -ne 0) {
            throw "offline_pipeline_runner failed during optional offline analysis"
        }
    }

    # ------------------------------------------------------------
    # 1.5) Post-run DB snapshot
    # ------------------------------------------------------------
    Write-Step "1.5) Post-run DB snapshot"
    @"
import sqlite3

inventory_db = r"$InventoryDb"
asset_db     = r"$AssetDb"
pattern_db   = r"$PatternDb"

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
    # 2A) Strict runtime DB verification (Path A)
    # ------------------------------------------------------------
    if (-not $SkipVerify) {
        Write-Step "2A) Strict runtime bundle verification (Path A)"

        & python $VerifyRuntimeStrictPy `
            --file-scan-db $InventoryDb `
            --chart-assets-db $AssetDb `
            --chart-patterns-db $PatternDb `
            --json-out $StrictVerifyJson

        if ($LASTEXITCODE -ne 0) {
            throw "verify_runtime_bundle_strict failed. See $StrictVerifyJson"
        }

        # ------------------------------------------------------------
        # 2B) Legacy / full bundle verification (optional existing gate)
        # ------------------------------------------------------------
        Write-Step "2B) Verify full runtime DB bundle"

        Ensure-Dir $ReportRoot

        Assert-File $VerifyFullBundlePy "verify_full_bundle.py"
        Assert-File $InventoryDb "file_scan_inventory.db"
        Assert-File $AssetDb "chart_assets.db"
        Assert-File $PatternDb "chart_patterns.db"

        Write-Host "[VERIFY] verify_full_bundle.py = $VerifyFullBundlePy"
        Write-Host "[VERIFY] file_scan_inventory.db = $InventoryDb"
        Write-Host "[VERIFY] chart_assets.db       = $AssetDb"
        Write-Host "[VERIFY] chart_patterns.db     = $PatternDb"
        Write-Host "[VERIFY] json_out              = $VerifyJson"

        & python $VerifyFullBundlePy `
            --file-scan-db $InventoryDb `
            --chart-assets-db $AssetDb `
            --chart-patterns-db $PatternDb `
            --json-out $VerifyJson

        if ($LASTEXITCODE -ne 0) {
            throw "verify_full_bundle failed. See $VerifyJson"
        }
    }
    else {
        Write-Host "[SKIP] Verification skipped by -SkipVerify" -ForegroundColor Yellow
    }

    # ------------------------------------------------------------
    # 3) Optional safe-delete workflow
    # ------------------------------------------------------------
    if ($RunSafeDeleteDryRun -and $ExecuteSafeDelete) {
        throw "Choose only one of -RunSafeDeleteDryRun or -ExecuteSafeDelete"
    }

    if ($RunSafeDeleteDryRun -or $ExecuteSafeDelete) {
        Write-Step "3) Safe delete workflow"

        $SafeDeleteArgs = @(
            $SafeDeletePy,
            "--chart-assets-db", $AssetDb,
            "--chart-patterns-db", $PatternDb,
            "--file-scan-db", $InventoryDb,
            "--exclude-recent-days", $ExcludeRecentDays,
            "--json-out", $SafeDeleteJson
        )

        if ([string]::IsNullOrWhiteSpace($PathsJson)) {
            $SafeDeleteArgs += "--auto-from-db"
        }
        else {
            $SafeDeleteArgs += @("--paths-json", $PathsJson)
        }

        if (-not [string]::IsNullOrWhiteSpace($QuarantineDir)) {
            $SafeDeleteArgs += @("--quarantine-dir", $QuarantineDir)
        }

        if ($IncludeTypeB) {
            $SafeDeleteArgs += "--include-type-b-in-delete"
        }

        if ($AllowDeleteLastCopy) {
            $SafeDeleteArgs += "--allow-delete-last-copy"
        }

        if ($ExecuteSafeDelete) {
            $SafeDeleteArgs += "--execute"
            Write-Host "[SAFE DELETE] Execute mode enabled" -ForegroundColor Yellow
        }
        else {
            Write-Host "[SAFE DELETE] Dry-run mode enabled" -ForegroundColor Green
        }

        & python @SafeDeleteArgs

        if ($LASTEXITCODE -ne 0) {
            throw "safe_delete_candidates failed. See $SafeDeleteJson"
        }
    }
    else {
        Write-Host "[INFO] Safe-delete skipped" -ForegroundColor DarkYellow
    }

    # ------------------------------------------------------------
    # 4) Final summary bundle
    # ------------------------------------------------------------
    Write-Step "4) Final report bundle"
    Write-Host "Pipeline log            : $PipelineLog"

    if (Test-Path $StrictVerifyJson) {
        Write-Host "Strict verify bundle    : $StrictVerifyJson"
    }

    if (Test-Path $VerifyJson) {
        Write-Host "Verify bundle           : $VerifyJson"
    }

    if (Test-Path $SafeDeleteJson) {
        Write-Host "Safe delete JSON        : $SafeDeleteJson"
    }

    Write-Host "Artifacts root          : $ReportRoot"
    Write-Host "Inventory DB            : $InventoryDb"
    Write-Host "Asset DB                : $AssetDb"
    Write-Host "Pattern DB              : $PatternDb"
    Write-Host ""
    Write-Host "Phase 3.5 / UMI v2.0 run completed." -ForegroundColor Green
}
finally {
    Pop-Location
}