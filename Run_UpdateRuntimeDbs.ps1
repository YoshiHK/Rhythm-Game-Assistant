param(
    # ------------------------------------------------------------
    # Harness root
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
    # Optional outputs
    # ------------------------------------------------------------
    [string]$JsonOut = "",

    [string]$RuntimeBaselineOut = "",

    [switch]$SkipVerify,

    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

function Write-Step {
    param(
        [string]$Message
    )

    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor DarkCyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "===========================================================" -ForegroundColor DarkCyan
}

function Assert-File {
    param(
        [string]$PathToCheck,
        [string]$Label
    )

    if ([System.String]::IsNullOrWhiteSpace($PathToCheck)) {
        throw "$Label path is empty."
    }

    if (-not (Test-Path -LiteralPath $PathToCheck)) {
        throw "$Label not found: $PathToCheck"
    }
}

function Ensure-Dir {
    param(
        [string]$DirPath
    )

    if ([System.String]::IsNullOrWhiteSpace($DirPath)) {
        return
    }

    if (-not (Test-Path -LiteralPath $DirPath)) {
        New-Item `
            -ItemType Directory `
            -Path $DirPath `
            -Force `
            | Out-Null
    }
}

function Ensure-ParentDir {
    param(
        [string]$FilePath
    )

    if ([System.String]::IsNullOrWhiteSpace($FilePath)) {
        return
    }

    $Parent = Split-Path `
        -Parent `
        $FilePath

    if (-not [System.String]::IsNullOrWhiteSpace($Parent)) {
        Ensure-Dir `
            -DirPath $Parent
    }
}

function Remove-IfExists {
    param(
        [string]$PathToRemove,
        [string]$Label
    )

    if ([System.String]::IsNullOrWhiteSpace($PathToRemove)) {
        Write-Host "Empty path supplied for $Label. Skipping." -ForegroundColor DarkYellow
        return
    }

    if (Test-Path -LiteralPath $PathToRemove) {
        Write-Host "Removing $Label : $PathToRemove" -ForegroundColor Yellow

        Remove-Item `
            -LiteralPath $PathToRemove `
            -Force
    }
    else {
        Write-Host "Not found (skip) $Label : $PathToRemove" -ForegroundColor DarkYellow
    }
}

function Resolve-OutputPath {
    param(
        [string]$BaseRoot,
        [string]$PathValue
    )

    if ([System.String]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }

    return (Join-Path $BaseRoot $PathValue)
}

# ------------------------------------------------------------
# Resolve paths
# ------------------------------------------------------------

$SrcRoot = Join-Path $UMIRoot "src"

$ArtifactsRoot = Join-Path $HarnessRoot "artifacts"

# Runtime directories
$InventoryDir = Join-Path $RuntimeRoot "ingestions"
$AssetDir     = Join-Path $RuntimeRoot "assets"
$PatternDir   = Join-Path $RuntimeRoot "features"

# Runtime DB files
$InventoryDb = Join-Path $InventoryDir "file_scan_inventory.db"
$AssetDb     = Join-Path $AssetDir "chart_assets.db"
$PatternDb   = Join-Path $PatternDir "chart_patterns.db"

# Primary script path
$ScriptPath = Join-Path $HarnessRoot "Update_Runtime_Dbs.py"

# Verification scripts
$VerifyRuntimeStrictPy = Join-Path $SrcRoot "rhythm_ingestion\writers\verification\verify_runtime_bundle_strict.py"

# Alignment Matrix
$AlignmentMatrixPy = Join-Path $HarnessRoot "auto_verify_alignment_matrix.py"

# ------------------------------------------------------------
# Ensure base directories exist
# ------------------------------------------------------------

Ensure-Dir $InventoryDir
Ensure-Dir $AssetDir
Ensure-Dir $PatternDir
Ensure-Dir $ArtifactsRoot

# ------------------------------------------------------------
# Report bundle
# ------------------------------------------------------------

$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"

$ReportRoot = Join-Path $ArtifactsRoot ("runtime_db_build_" + $Timestamp)

Ensure-Dir $ReportRoot

$PipelineLog = Join-Path $ReportRoot "update_runtime_dbs.log"

$StrictVerifyJson = Join-Path $ReportRoot "verify_runtime_bundle_strict.json"

$CanonicalErrorJson = Join-Path $ReportRoot "canonical_error_breakdown.json"

$AlignmentMatrixJson = Join-Path $ReportRoot "alignment_matrix_v2.json"

$AlignmentMatrixCi = Join-Path $ReportRoot "alignment_matrix_ci.txt"

# Runtime baseline output
if ([System.String]::IsNullOrWhiteSpace($RuntimeBaselineOut)) {
    $RuntimeBaselinePath = Join-Path `
        $ReportRoot `
        "runtime_baseline.json"
}
else {
    $RuntimeBaselinePath = Resolve-OutputPath `
        -BaseRoot $HarnessRoot `
        -PathValue $RuntimeBaselineOut
}

# Optional JSON report output
if (-not [System.String]::IsNullOrWhiteSpace($JsonOut)) {
    $JsonOutPath = Resolve-OutputPath `
        -BaseRoot $HarnessRoot `
        -PathValue $JsonOut
}
else {
    $JsonOutPath = ""
}

Ensure-ParentDir $RuntimeBaselinePath

if (-not [System.String]::IsNullOrWhiteSpace($JsonOutPath)) {
    Ensure-ParentDir `
        -FilePath $JsonOutPath
}

# ------------------------------------------------------------
# Assert required files
# ------------------------------------------------------------

Assert-File $ScriptPath "Update_Runtime_Dbs.py"
Assert-File $VerifyRuntimeStrictPy "verify_runtime_bundle_strict.py"
Assert-File $AlignmentMatrixPy "auto_verify_alignment_matrix.py"

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

Write-Step "Update Runtime DBs - Environment"

Push-Location $HarnessRoot

try {

    # ------------------------------------------------------------
    # Phase 7 config path
    # ------------------------------------------------------------

    $Phase7ConfigRoot = Join-Path `
        $HarnessRoot `
        "Phase 7 - Games Recommendation\config"

    Assert-File `
        (Join-Path $Phase7ConfigRoot "games_loader.py") `
        "Phase 7 games_loader.py"

    Assert-File `
        (Join-Path $Phase7ConfigRoot "games.json") `
        "Phase 7 games.json"

    # ------------------------------------------------------------
    # PYTHONPATH
    # ------------------------------------------------------------
    #
    # Include:
    #   1. UMI src root
    #   2. Phase 7 config root
    #
    # This keeps Completed Phases unchanged while exposing
    # operational wiring.
    # ------------------------------------------------------------

    $env:PYTHONPATH = "$SrcRoot;$Phase7ConfigRoot"

    Write-Host "HarnessRoot        : $HarnessRoot"
    Write-Host "UMIRoot            : $UMIRoot"
    Write-Host "SourceDir          : $SourceDir"
    Write-Host "RuntimeRoot        : $RuntimeRoot"
    Write-Host "Phase7ConfigRoot   : $Phase7ConfigRoot"
    Write-Host "PYTHONPATH         : $env:PYTHONPATH"
    Write-Host "ReportRoot         : $ReportRoot"
    Write-Host "Rebuild            : $Rebuild"
    Write-Host "SkipVerify         : $SkipVerify"
    Write-Host "RuntimeBaselineOut : $RuntimeBaselinePath"

	if (-not [System.String]::IsNullOrWhiteSpace($JsonOutPath)) {
		Write-Host "JsonOut            : $JsonOutPath"
	}

    # ------------------------------------------------------------
    # UTF-8 safety
    #
    # Prevent:
    #   UnicodeEncodeError: cp950 ...
    #
    # when chart filenames contain
    # Japanese / Unicode characters.
    # ------------------------------------------------------------

    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    Write-Host "PYTHONUTF8       : $env:PYTHONUTF8"
    Write-Host "PYTHONIOENCODING : $env:PYTHONIOENCODING"
	
    # ------------------------------------------------------------
    # Optional rebuild mode
    # ------------------------------------------------------------

    if ($Rebuild) {
        Write-Step "0) Rebuild Mode - Clearing Runtime DBs"

        Remove-IfExists $InventoryDb "Inventory DB"
        Remove-IfExists $AssetDb     "Asset DB"
        Remove-IfExists $PatternDb   "Pattern DB"

        Write-Host "Runtime DB rebuild reset completed." -ForegroundColor Green
    }
    else {
        Write-Host "[CACHE] Rebuild not requested - existing runtime DBs will be reused if present." -ForegroundColor Yellow
    }

    # ------------------------------------------------------------
    # Execute updater
    #
    # Important:
    #
    #   Do not use:
    #
    #     & python @Args 2>&1
    #
    #   In Windows PowerShell, native stderr can surface as an
    #   error record when $ErrorActionPreference = "Stop".
    #
    #   Instead:
    #
    #     - redirect stdout to a file
    #     - redirect stderr to a file
    #     - capture $LASTEXITCODE
    #     - print both streams after process completion
    #     - fail in a controlled way
    # ------------------------------------------------------------

    Write-Step "1) Run Update_Runtime_Dbs.py"

    $UpdaterStdout = Join-Path `
        $ReportRoot `
        "update_runtime_dbs_stdout.txt"

    $UpdaterStderr = Join-Path `
        $ReportRoot `
        "update_runtime_dbs_stderr.txt"

    $Args = @(
        $ScriptPath,
        "--source-dir", $SourceDir,
        "--runtime-root", $RuntimeRoot,
        "--inventory-db", $InventoryDb,
        "--asset-db", $AssetDb,
        "--pattern-db", $PatternDb,
        "--canonical-error-out", $CanonicalErrorJson
    )

    if (-not [System.String]::IsNullOrWhiteSpace($JsonOutPath)) {
        $Args += @(
            "--json-out", $JsonOutPath
        )
    }

    Write-Host "Python executable : python"
    Write-Host "Script path       : $ScriptPath"
    Write-Host "Stdout            : $UpdaterStdout"
    Write-Host "Stderr            : $UpdaterStderr"
    Write-Host "Pipeline log      : $PipelineLog"

    & python @Args `
        1> $UpdaterStdout `
        2> $UpdaterStderr

    $UpdaterExitCode = $LASTEXITCODE

    # ------------------------------------------------------------
    # Merge stdout/stderr into canonical pipeline log
    # ------------------------------------------------------------

    $LogLines = @()

    $LogLines += "==========================================================="
    $LogLines += "Update_Runtime_Dbs.py"
    $LogLines += "==========================================================="
    $LogLines += ""
    $LogLines += "Exit code: $UpdaterExitCode"
    $LogLines += ""
    $LogLines += "-----------------------------------------------------------"
    $LogLines += "STDOUT"
    $LogLines += "-----------------------------------------------------------"

    if (Test-Path -LiteralPath $UpdaterStdout) {
        $LogLines += Get-Content `
            -LiteralPath $UpdaterStdout `
            -ErrorAction SilentlyContinue
    }
    else {
        $LogLines += "(stdout file missing)"
    }

    $LogLines += ""
    $LogLines += "-----------------------------------------------------------"
    $LogLines += "STDERR"
    $LogLines += "-----------------------------------------------------------"

    if (Test-Path -LiteralPath $UpdaterStderr) {
        $LogLines += Get-Content `
            -LiteralPath $UpdaterStderr `
            -ErrorAction SilentlyContinue
    }
    else {
        $LogLines += "(stderr file missing)"
    }

    $LogLines | Set-Content `
        -LiteralPath $PipelineLog `
        -Encoding UTF8

    # ------------------------------------------------------------
    # Echo logs to console
    # ------------------------------------------------------------

    if (Test-Path -LiteralPath $UpdaterStdout) {
        $StdoutText = Get-Content `
            -LiteralPath $UpdaterStdout `
            -ErrorAction SilentlyContinue

        if ($StdoutText.Count -gt 0) {
            Write-Host ""
            Write-Host "[Update_Runtime_Dbs.py stdout]" -ForegroundColor DarkCyan
            $StdoutText | ForEach-Object {
                Write-Host $_
            }
        }
    }

    if (Test-Path -LiteralPath $UpdaterStderr) {
        $StderrText = Get-Content `
            -LiteralPath $UpdaterStderr `
            -ErrorAction SilentlyContinue

        if ($StderrText.Count -gt 0) {
            Write-Host ""
            Write-Host "[Update_Runtime_Dbs.py stderr]" -ForegroundColor Yellow
            $StderrText | ForEach-Object {
                Write-Host $_ -ForegroundColor Yellow
            }
        }
    }

    # ------------------------------------------------------------
    # Controlled failure
    # ------------------------------------------------------------

    if ($UpdaterExitCode -ne 0) {
        throw "Update_Runtime_Dbs.py failed with exit code $UpdaterExitCode. See: $UpdaterStderr"
    }

    # ------------------------------------------------------------
    # Post-build snapshot
    # ------------------------------------------------------------

    Write-Step "2) Post-build DB snapshot"

    @"
import sqlite3
import os

inventory_db = r"$InventoryDb"
asset_db     = r"$AssetDb"
pattern_db   = r"$PatternDb"

def count(db, table):
    if not os.path.exists(db):
        return "MISSING"

    conn = sqlite3.connect(db)

    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    finally:
        conn.close()

print("[POST] inventory =", count(inventory_db, "file_scan_inventory"))
print("[POST] assets    =", count(asset_db, "chart_assets"))
print("[POST] patterns  =", count(pattern_db, "chart_patterns"))
"@ | python -

    if ($LASTEXITCODE -ne 0) {
        throw "Post-build DB snapshot failed"
    }

    # ------------------------------------------------------------
    # Runtime Baseline Contract
    #
    # Stage 1:
    #
    #   DB build
    #     ↓
    #   runtime_baseline.json
    #
    # This is a baseline contract, not a full verification verdict.
    # Full coverage/hash/usability verification remains separate.
    # ------------------------------------------------------------

    Write-Step "3) Write Runtime Baseline Contract"

    Ensure-ParentDir $RuntimeBaselinePath

    @"
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

runtime_root = Path(r"$RuntimeRoot")
source_dir = Path(r"$SourceDir")

inventory_db = Path(r"$InventoryDb")
asset_db = Path(r"$AssetDb")
pattern_db = Path(r"$PatternDb")

runtime_baseline_out = Path(r"$RuntimeBaselinePath")

def table_count(db_path: Path, table_name: str):
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))

        try:
            return conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

        finally:
            conn.close()

    except Exception:
        return None

def db_snapshot(name: str, path: Path, table_name: str):
    exists = path.exists()

    record_count = table_count(
        path,
        table_name,
    )

    readable = (
        exists
        and record_count is not None
    )

    return {
        "name": name,
        "path": str(path),
        "exists": exists,
        "table": table_name,
        "record_count": record_count,
        "readable": readable,
    }

databases = {
    "file_scan_inventory.db": db_snapshot(
        "file_scan_inventory.db",
        inventory_db,
        "file_scan_inventory",
    ),

    "chart_assets.db": db_snapshot(
        "chart_assets.db",
        asset_db,
        "chart_assets",
    ),

    "chart_patterns.db": db_snapshot(
        "chart_patterns.db",
        pattern_db,
        "chart_patterns",
    ),
}

baseline_ready = all(
    item["exists"] and item["readable"]
    for item in databases.values()
)

total_records = sum(
    item["record_count"] or 0
    for item in databases.values()
)

payload = {
    "schema": "rga.runtime_baseline.v1.0",

    "generated_at": datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat(),

    "source_dir": str(source_dir),

    "runtime_root": str(runtime_root),

    "baseline_ready": baseline_ready,

    "databases": databases,

    "summary": {
        "required_database_count": 3,
        "existing_database_count": sum(
            1
            for item in databases.values()
            if item["exists"]
        ),
        "readable_database_count": sum(
            1
            for item in databases.values()
            if item["readable"]
        ),
        "total_records": total_records,
    },

    "contract": {
        "stage": "runtime_baseline",
        "verification_required": True,
        "deployment_gate_required": True,
        "deletion_allowed": False,
        "baseline_is_not_full_verification": True,
    },

    "governance": {
        "completed_phases_remain_immutable": True,
        "phase_1_to_7_modified": False,
        "persistence_layer_owns_db_writes": True,
        "validation_is_not_verification": True,
    },
}

runtime_baseline_out.parent.mkdir(
    parents=True,
    exist_ok=True,
)

runtime_baseline_out.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(f"[RUNTIME BASELINE] path={runtime_baseline_out}")
print(f"[RUNTIME BASELINE] baseline_ready={baseline_ready}")
print(f"[RUNTIME BASELINE] total_records={total_records}")
"@ | python -

    if ($LASTEXITCODE -ne 0) {
        throw "Runtime baseline contract generation failed"
    }

    Assert-File $RuntimeBaselinePath "runtime_baseline.json"

    # ------------------------------------------------------------
    # Publish Canonical Runtime Baseline
    #
    # Governance Bridge:
    #
    #   runtime_db_build_<timestamp>
    #           ↓
    #   artifacts/runtime_baseline.json
    #
    # GitHub Runtime Auditor consumes the
    # canonical path instead of timestamped bundles.
    # ------------------------------------------------------------

    Copy-Item `
        $RuntimeBaselinePath `
        (Join-Path $ArtifactsRoot "runtime_baseline.json") `
        -Force

    Write-Host ""
    Write-Host "[RUNTIME BASELINE] Published canonical baseline:"
    Write-Host "  $(Join-Path $ArtifactsRoot 'runtime_baseline.json')"

    Assert-File `
        (Join-Path $ArtifactsRoot "runtime_baseline.json") `
        "canonical runtime_baseline.json"


    # ------------------------------------------------------------
    # Strict verification
    # ------------------------------------------------------------

    if (-not $SkipVerify) {
        Write-Step "4) Strict runtime bundle verification"

        & python $VerifyRuntimeStrictPy `
            --file-scan-db $InventoryDb `
            --chart-assets-db $AssetDb `
            --chart-patterns-db $PatternDb `
            --json-out $StrictVerifyJson

        if ($LASTEXITCODE -ne 0) {
            throw "verify_runtime_bundle_strict failed"
        }
    }
    else {
        Write-Host "[SKIP] Strict verification skipped" -ForegroundColor Yellow
    }

    # ------------------------------------------------------------
    # Alignment Matrix v2 Diagnostic
    # ------------------------------------------------------------

    Write-Step "5) Alignment Matrix v2 Diagnosis"

    & python $AlignmentMatrixPy `
        --repo-root $HarnessRoot `
        --json-out $AlignmentMatrixJson `
        --ci-summary `
        --ci-summary-out $AlignmentMatrixCi `
        --strict-phase3-only

    if ($LASTEXITCODE -ne 0) {
        throw "Alignment Matrix Phase 3 correctness failed"
    }

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    Write-Step "6) Update Completed + Diagnosis Summary"

    Write-Host "Inventory DB      : $InventoryDb"
    Write-Host "Asset DB          : $AssetDb"
    Write-Host "Pattern DB        : $PatternDb"
    Write-Host "Runtime baseline  : $RuntimeBaselinePath"
    Write-Host "Log file          : $PipelineLog"

    if (Test-Path $CanonicalErrorJson) {
        Write-Host "Canonical errors  : $CanonicalErrorJson"
    }

    if (Test-Path $StrictVerifyJson) {
        Write-Host "Strict verify     : $StrictVerifyJson"
    }

    if (Test-Path $AlignmentMatrixJson) {
        Write-Host "Alignment v2      : $AlignmentMatrixJson"
    }

    if (Test-Path $AlignmentMatrixCi) {
        Write-Host "CI Summary        : $AlignmentMatrixCi"
    }

	if (-not [System.String]::IsNullOrWhiteSpace($JsonOutPath)) {
		Write-Host "Report JSON       : $JsonOutPath"
	}

    Write-Host ""

    if ($Rebuild) {
        Write-Host "Runtime DB rebuild + build completed." -ForegroundColor Green
    }
    else {
        Write-Host "Runtime DB baseline build completed." -ForegroundColor Green
    }

    # ------------------------------------------------------------
    # 7) GitHub API Commit & Push Trigger
    # ------------------------------------------------------------
    Write-Step "7) Push Runtime Baseline via GitHub API"

    $RepoOwner = "YoshiHK" # Your GitHub username/org
    $RepoName  = "Rhythm-Game-Assistant"
    $Branch    = "main"
    $FilePath  = "artifacts/runtime_baseline.json"
    $LocalFile = Join-Path $ArtifactsRoot "runtime_baseline.json"

    # Read file content and encode in Base64 for GitHub API
    $FileBytes   = [System.IO.File]::ReadAllBytes($LocalFile)
    $Base64Content = [System.Convert]::ToBase64String($FileBytes)

    # Retrieve GitHub PAT Token from environment variable
    $GitHubToken = $env:PAT_TOKEN
    if ([System.String]::IsNullOrWhiteSpace($GitHubToken)) {
        throw "PAT_TOKEN environment variable is not set."
    }

    $Headers = @{
        "Authorization" = "Bearer $GitHubToken"
        "Accept"        = "application/vnd.github.v3+json"
    }

    # Check if file exists on remote branch to obtain its SHA (for updating)
    $Uri = "https://api.github.com/repos/$RepoOwner/$RepoName/contents/$FilePath?ref=$Branch"
    $Sha = $null

    try {
        $ExistingFile = Invoke-RestMethod -Uri $Uri -Method Get -Headers $Headers
        $Sha = $ExistingFile.sha
        Write-Host "Found existing remote file SHA: $Sha" -ForegroundColor Yellow
    } catch {
        Write-Host "Remote file does not exist yet. Will perform initial creation." -ForegroundColor Cyan
    }

    # Construct commit body
    # NOTE: Removed [skip ci] so PAT_TOKEN push triggers downstream auditing steps
    $CommitBody = @{
        message = "auto(runtime): publish updated runtime_baseline.json"
        content = $Base64Content
        branch  = $Branch
    }

    if ($Sha) {
        $CommitBody["sha"] = $Sha
    }

    $JsonBody = $CommitBody | ConvertTo-Json -Depth 5

    # Push commit to GitHub via API
    $PutUri = "https://api.github.com/repos/$RepoOwner/$RepoName/contents/$FilePath"
    $Response = Invoke-RestMethod -Uri $PutUri -Method Put -Headers $Headers -Body $JsonBody -ContentType "application/json"

    Write-Host "Successfully committed runtime_baseline.json via GitHub API!" -ForegroundColor Green
    Write-Host "Commit SHA: $($Response.commit.sha)" -ForegroundColor DarkCyan
}	

finally {
    Pop-Location
}
