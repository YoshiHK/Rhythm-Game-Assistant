param(
    [string]$RepoRoot = ".",
    [string]$PythonExe = "python",
    [string]$DataRoot = "",

    # Execution modes
    [switch]$BootstrapOnly,
    [switch]$SkipBootstrap,
    [switch]$SkipSmoke,

    # Forward to Bootstrap / RepoSmoke (Path B foundation)
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
    [string]$SummaryOutputPath = "",

    # ------------------------------------------------------------
    # NEW: Path A / intersection wiring (additive only)
    # ------------------------------------------------------------
    [switch]$RunPathABaseline,
    [switch]$RunPathAIngestion,
    [switch]$RunDeploymentGate,
    [switch]$SkipPathAVerify,
    [switch]$RunOfflineAnalysis
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
$BootstrapScript      = ".\bootstrap.ps1"
$RepoSmokeScript      = ".\Run-RepoSmoke.ps1"
$RuntimeDbBuildScript = ".\Run_UpdateRuntimeDbs.ps1"
$IngestionRuntimeScript = ".\Run_Ingestion.ps1"
$DeploymentGateScript = ".\Run-DeploymentGate.ps1"

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
    # STEP 2: Repo Smoke / Path A + Path B harness
    # IMPORTANT:
    # setup.ps1 is the outer orchestrator. If bootstrap already ran
    # successfully above, RepoSmoke must NOT run bootstrap again.
    # --------------------------------------------------
    if (-not $SkipSmoke) {

        Test-FileExists $RepoSmokeScript "Run-RepoSmoke.ps1"
        Test-FileExists $RuntimeDbBuildScript "Run_UpdateRuntimeDbs.ps1"
        Test-FileExists $IngestionRuntimeScript "Run_Ingestion.ps1"
        Test-FileExists $DeploymentGateScript "Run-DeploymentGat.ps1"

        Write-Info "Running repo smoke..."

        $smokeParams = @{
            ProjectRoot = $resolvedRoot
            PythonExe   = $PythonExe

            # Always skip bootstrap inside RepoSmoke when called from setup.ps1
            SkipBootstrap = $true

            # Path A / intersection wiring
            RuntimeDbBuildScript   = $RuntimeDbBuildScript
            IngestionRuntimeScript = $IngestionRuntimeScript
            DeploymentGateScript   = $DeploymentGateScript
        }

        # Existing Path B controls
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
        if ($RequireInterpretationOutput) { $smokeParams["RequireInterpretationOutput"] = $true }
        if ($SkipNonFeedbackCases)        { $smokeParams["SkipNonFeedbackCases"] = $true }
        if ($StrictValidation)            { $smokeParams["StrictValidation"] = $true }

        if ($RequiredEventTypes -and $RequiredEventTypes.Count -gt 0) {
            $smokeParams["RequiredEventTypes"] = $RequiredEventTypes
        }

        if ($SummaryOutputPath -and $SummaryOutputPath.Trim() -ne "") {
            $smokeParams["SummaryOutputPath"] = $SummaryOutputPath
        }

        # NEW: Path A execution controls
        if ($RunPathABaseline)    { $smokeParams["RunPathABaseline"] = $true }
        if ($RunPathAIngestion)   { $smokeParams["RunPathAIngestion"] = $true }
        if ($RunDeploymentGate)   { $smokeParams["RunDeploymentGate"] = $true }
        if ($SkipPathAVerify)     { $smokeParams["SkipPathAVerify"] = $true }
        if ($RunOfflineAnalysis)  { $smokeParams["RunOfflineAnalysis"] = $true }

        & $RepoSmokeScript @smokeParams

        if ($LASTEXITCODE -ne 0) {
            throw "Run-RepoSmoke.ps1 failed"
        }

        Write-Ok "Repo smoke completed"
    }
    else {
        Write-Warn2 "Skipping repo smoke"
    }

    # --------------------------------------------------
    # FINAL
    # --------------------------------------------------
    Write-Host ""
    Write-Host "============================================="
    Write-Host "SETUP COMPLETE"
    Write-Host "============================================="
}
finally {
    Pop-Location
}
