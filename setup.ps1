param(
    [string]$RepoRoot = ".",
    [string]$PythonExe = "python",
    [string]$DataRoot = "",

    # Execution modes
    [switch]$BootstrapOnly,
    [switch]$SkipBootstrap,
    [switch]$SkipSmoke,

    # Forward to Bootstrap / RepoSmoke
    [switch]$OfflineValidationMode,
    [switch]$RunStageProbes,
    [switch]$RunOrchestrator,

    # Phase5 / validator control
    [switch]$SkipPhase5,
    [switch]$SkipDeterminism,
    [switch]$SkipSchema,
    [switch]$SkipContract,
    [switch]$SkipCoverage,
    [switch]$SkipIntegrity,
    [switch]$SkipDrift,
    [switch]$SkipRegression,

    [double]$RegressionTolerance = 0.0,
    [double]$DriftTolerance = 0.10,

    # Align with RepoSmoke / Phase5 Batch
    [switch]$EnableCaseExpectOverride,
    [string[]]$RequiredEventTypes = @(),
    [switch]$RequireInterpretationOutput,
    [switch]$SkipNonFeedbackCases,
    [switch]$StrictValidation,
    [string]$SummaryOutputPath = ""
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------
# logging
# --------------------------------------------------
function Write-Info($msg)  { Write-Host "[SETUP] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg) { Write-Host "[SETUP][WARN] $msg" -ForegroundColor Yellow }
function Write-Ok($msg)    { Write-Host "[SETUP][OK] $msg" -ForegroundColor Green }
function Write-Fail($msg)  { Write-Host "[SETUP][FAIL] $msg" -ForegroundColor Red }

# --------------------------------------------------
# helpers
# --------------------------------------------------
function Resolve-AbsolutePath($Path, $BaseDir) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $Path }
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return (Join-Path $BaseDir $Path)
}

function Test-FileExists($Path, $Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function Get-ProjectPython($RepoRoot, $PythonExe) {
    $venv = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venv) {
        Write-Ok "Using venv python: $venv"
        return $venv
    }

    Write-Warn2 "venv python not found -> using: $PythonExe"
    return $PythonExe
}

# --------------------------------------------------
# script targets (repo-level)
# --------------------------------------------------
$BootstrapScript = ".\bootstrap.ps1"
$RepoSmokeScript = ".\Run-RepoSmoke.ps1"

# --------------------------------------------------
# main
# --------------------------------------------------
Push-Location $RepoRoot
try {
    $resolvedRoot = (Resolve-Path ".").Path
    $pythonBin = Get-ProjectPython $resolvedRoot $PythonExe
    $resolvedDataRoot = Resolve-AbsolutePath $DataRoot $resolvedRoot

    Write-Host ""
    Write-Host "============================================="
    Write-Host "RGA Setup Entry"
    Write-Host "============================================="
    Write-Host "RepoRoot : $resolvedRoot"
    Write-Host "Python   : $pythonBin"
    if (-not [string]::IsNullOrWhiteSpace($resolvedDataRoot)) {
        Write-Host "DataRoot : $resolvedDataRoot"
    }
    Write-Host ""

    # --------------------------------------------------
    # STEP 1: Bootstrap
    # --------------------------------------------------
    if (-not $SkipBootstrap) {

        Test-FileExists $BootstrapScript "bootstrap.ps1"

        Write-Info "Running bootstrap..."

        $bootstrapParams = @{
            RepoRoot          = $resolvedRoot
            PythonExe         = $PythonExe
            SkipInstall       = $true
            SkipOneDriveCheck = $true
        }

        if (-not [string]::IsNullOrWhiteSpace($resolvedDataRoot)) {
            $bootstrapParams["DataRoot"] = $resolvedDataRoot
        }

        if ($OfflineValidationMode) { $bootstrapParams["OfflineValidationMode"] = $true }
        if ($RunStageProbes)        { $bootstrapParams["RunStageProbes"] = $true }
        if ($RunOrchestrator)       { $bootstrapParams["RunOrchestrator"] = $true }

        & $BootstrapScript @bootstrapParams

        if ($LASTEXITCODE -ne 0) {
            throw "bootstrap.ps1 failed"
        }

        Write-Ok "Bootstrap completed"
    }
    else {
        Write-Warn2 "Skipping bootstrap"
    }

    # --------------------------------------------------
    # EXIT EARLY (bootstrap only mode)
    # --------------------------------------------------
    if ($BootstrapOnly) {
        Write-Ok "Bootstrap-only mode complete"
        exit 0
    }

    # --------------------------------------------------
    # STEP 2: Repo Smoke
    # IMPORTANT:
    # Setup is the outer orchestrator. If bootstrap was already run
    # successfully above, RepoSmoke must NOT run bootstrap again.
    # This avoids duplicated environment reconstruction and CI DataRoot
    # mismatches.
    # --------------------------------------------------
    if (-not $SkipSmoke) {

        Test-FileExists $RepoSmokeScript "Run-RepoSmoke.ps1"

        Write-Info "Running repo smoke..."

        $smokeParams = @{
            ProjectRoot = $resolvedRoot
            PythonExe   = $PythonExe

            # Always skip bootstrap inside RepoSmoke when called from setup.ps1
            SkipBootstrap = $true
        }

        # Existing controls
        if ($SkipPhase5) { $smokeParams["SkipPhase5"] = $true }

        if ($OfflineValidationMode) { $smokeParams["OfflineValidationMode"] = $true }
        if ($RunStageProbes)        { $smokeParams["RunStageProbes"] = $true }
        if ($RunOrchestrator)       { $smokeParams["RunOrchestrator"] = $true }

        if ($SkipDeterminism) { $smokeParams["SkipDeterminism"] = $true }
        if ($SkipSchema)      { $smokeParams["SkipSchema"] = $true }
        if ($SkipContract)    { $smokeParams["SkipContract"] = $true }
        if ($SkipCoverage)    { $smokeParams["SkipCoverage"] = $true }
        if ($SkipIntegrity)   { $smokeParams["SkipIntegrity"] = $true }
        if ($SkipDrift)       { $smokeParams["SkipDrift"] = $true }
        if ($SkipRegression)  { $smokeParams["SkipRegression"] = $true }

        $smokeParams["RegressionTolerance"] = $RegressionTolerance
        $smokeParams["DriftTolerance"]      = $DriftTolerance

        # Forward newer RepoSmoke / Phase5 Batch controls
        if ($EnableCaseExpectOverride)    { $smokeParams["EnableCaseExpectOverride"] = $true }
