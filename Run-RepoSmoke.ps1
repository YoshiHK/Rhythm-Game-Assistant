param(
    [string]$ProjectRoot = ".",
    [string]$PythonExe = "python",

    [switch]$SkipBootstrap,
    [switch]$SkipPhase5,
    [switch]$SkipEngineFeedback,
    [switch]$StopOnFailure,

    [string]$BootstrapScript = ".\bootstrap.ps1",
    [string]$Phase5BatchScript = ".\Run-Phase5Batch.ps1",
    [string]$OutputDir = ".\repo_smoke_output",

    [switch]$SkipDeterminism,
    [switch]$SkipSchema,
    [switch]$SkipContract,
    [switch]$SkipCoverage,
    [switch]$SkipIntegrity,
    [switch]$SkipDrift,
    [switch]$SkipRegression,

    [double]$RegressionTolerance = 0.0,
    [double]$DriftTolerance = 0.10,

    [switch]$OfflineValidationMode,
    [switch]$RunStageProbes,
    [switch]$RunOrchestrator,

    # Existing Path B alignment
    [switch]$EnableCaseExpectOverride,
    [string[]]$RequiredEventTypes = @(),
    [switch]$RequireInterpretationOutput,
    [switch]$SkipNonFeedbackCases,
    [switch]$StrictValidation,
    [string]$SummaryOutputPath = "",

    # ------------------------------------------------------------
    # Path A / intersection wiring (additive only)
    # ------------------------------------------------------------
    [switch]$RunPathABaseline,
    [switch]$RunPathAIngestion,
    [switch]$RunDeploymentGate,
    [switch]$SkipPathAVerify,
    [switch]$RunOfflineAnalysis,
    [switch]$EnableConverterCache,

    [string]$RuntimeDbBuildScript = ".\Run_UpdateRuntimeDbs.ps1",
    [string]$IngestionRuntimeScript = ".\Run_Ingestion.ps1",
    [string]$DeploymentGateScript = ".\Run-DeploymentGate.ps1"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host "[REPO-SMOKE] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg) { Write-Host "[REPO-SMOKE][WARN] $msg" -ForegroundColor Yellow }
function Write-Ok($msg)    { Write-Host "[REPO-SMOKE][OK] $msg" -ForegroundColor Green }
function Write-Fail($msg)  { Write-Host "[REPO-SMOKE][FAIL] $msg" -ForegroundColor Red }

function Ensure-Dir($Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Resolve-AbsolutePath($Path, $BaseDir) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return (Join-Path $BaseDir $Path)
}

function Get-TodayString {
    return (Get-Date).ToString("yyyy-MM-dd")
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Info "Starting: $Name"
    try {
        & $Action
        Write-Ok "Passed: $Name"
        return [PSCustomObject]@{
            Name   = $Name
            Status = "PASS"
            Error  = $null
        }
    }
    catch {
        Write-Fail "Failed: $Name"
        Write-Host $_ -ForegroundColor Red

        if ($StopOnFailure) { throw }

        return [PSCustomObject]@{
            Name   = $Name
            Status = "FAIL"
            Error  = $_.Exception.Message
        }
    }
}

function Test-FileExists($Path, $Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function New-SharedRunDirectory($ArtifactRootDir) {
    Ensure-Dir $ArtifactRootDir
    $dateStr = Get-TodayString
    $dateDir = Join-Path $ArtifactRootDir $dateStr
    Ensure-Dir $dateDir

    $existingRuns = @()
    Get-ChildItem $dateDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -like "$dateStr_*") {
            $suffix = $_.Name.Substring($dateStr.Length + 1)
            if ($suffix -match '^\d+$') {
                $existingRuns += [int]$suffix
            }
        }
    }

    if ($existingRuns.Count -eq 0) {
        $nextRun = 1
    }
    else {
        $nextRun = ($existingRuns | Measure-Object -Maximum).Maximum + 1
    }

    $runDir = Join-Path $dateDir ("{0}_{1}" -f $dateStr, $nextRun)
    Ensure-Dir $runDir
    return $runDir
}

function Get-ProjectPython($ProjectRoot, $PythonExe) {
    $venv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venv) {
        Write-Ok "Using venv python: $venv"
        return $venv
    }
    Write-Warn2 "Using fallback python: $PythonExe"
    return $PythonExe
}

function Run-BootstrapStep {
    param($Root)

    Test-FileExists $BootstrapScript "Bootstrap script"

    $params = @{
        RepoRoot          = $Root
        SkipInstall       = $true
        SkipOneDriveCheck = $true
    }

    if ($OfflineValidationMode) { $params["OfflineValidationMode"] = $true }
    if ($RunStageProbes)        { $params["RunStageProbes"] = $true }
    if ($RunOrchestrator)       { $params["RunOrchestrator"] = $true }

    & $BootstrapScript @params

    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap failed"
    }
}

function Run-EngineFeedbackImportSmoke {
    param(
        [string]$PythonBin,
        [string]$RunDir
    )

    $code = @'
import importlib

mods = ["engine", "engine.feedback"]
failed = []

for m in mods:
    try:
        importlib.import_module(m)
        print("[IMPORT][OK]", m)
    except Exception as e:
        print("[IMPORT][FAIL]", m, "->", str(e))
        failed.append({"module": m, "error": str(e)})

if failed:
    raise SystemExit(1)
'@

    $outFile = Join-Path $RunDir "engine_feedback_import_smoke.txt"

    & $PythonBin -c $code | Tee-Object -FilePath $outFile

    if ($LASTEXITCODE -ne 0) {
        throw "engine/feedback import smoke failed"
    }
}

function Run-Phase5BatchStep {
    param(
        [string]$ScriptPath,
        [string]$RunDir
    )

    Test-FileExists $ScriptPath "Phase5 batch script"

    $phase5ArtifactRoot = Join-Path $RunDir "phase5"
    Ensure-Dir $phase5ArtifactRoot

    $stdoutFile = Join-Path $phase5ArtifactRoot "phase5_batch_stdout.txt"
    $stderrFile = Join-Path $phase5ArtifactRoot "phase5_batch_stderr.txt"

    $childArgs = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ScriptPath,

        "-CasesDir", ".\Phase 5 - Productionization\tests\test_cases",
        "-EventRunnerScript", ".\Phase 5 - Productionization\event_batch_runner.py",
        "-InterpretationRunnerScript", ".\engine\feedback\feedback_interpretation_batch_runner.py",
        "-Phase5RunnerScript", ".\Phase 5 - Productionization\feedback_loop_batch_runner.py",
        "-ValidateBundleScript", ".\Phase 5 - Productionization\tests\validators\validate_bundle.py",

        "-ArtifactRootDir", $phase5ArtifactRoot,
        "-RegressionTolerance", [string]$RegressionTolerance,
        "-DriftTolerance", [string]$DriftTolerance
    )

    if ($SkipDeterminism) { $childArgs += "-SkipDeterminism" }
    if ($SkipSchema)      { $childArgs += "-SkipSchema" }
    if ($SkipContract)    { $childArgs += "-SkipContract" }
    if ($SkipCoverage)    { $childArgs += "-SkipCoverage" }
    if ($SkipIntegrity)   { $childArgs += "-SkipIntegrity" }
    if ($SkipDrift)       { $childArgs += "-SkipDrift" }
    if ($SkipRegression)  { $childArgs += "-SkipRegression" }
    if ($EnableCaseExpectOverride)    { $childArgs += "-EnableCaseExpectOverride" }
    if ($RequireInterpretationOutput) { $childArgs += "-RequireInterpretationOutput" }
    if ($SkipNonFeedbackCases)        { $childArgs += "-SkipNonFeedbackCases" }
    if ($StrictValidation)            { $childArgs += "-StrictValidation" }

    if ($RequiredEventTypes -and $RequiredEventTypes.Count -gt 0) {
        $childArgs += "-RequiredEventTypes"
        $childArgs += $RequiredEventTypes
    }

    if ($SummaryOutputPath -and $SummaryOutputPath.Trim() -ne "") {
        $childArgs += "-SummaryOutputPath"
        $childArgs += $SummaryOutputPath
    }

    Write-Info "Running Phase 5 batch..."
    Write-Host "[REPO-SMOKE][PHASE5-CALL] pwsh $($childArgs -join ' ')" -ForegroundColor DarkYellow

    & pwsh @childArgs 1> $stdoutFile 2> $stderrFile

    if ($LASTEXITCODE -ne 0) {
        $out = ""
        $err = ""

        if (Test-Path -LiteralPath $stdoutFile) {
            $out = [System.IO.File]::ReadAllText($stdoutFile)
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $err = [System.IO.File]::ReadAllText($stderrFile)
        }

        throw "Phase5 batch failed.`n--- STDOUT ---`n$out`n--- STDERR ---`n$err"
    }

    Write-Ok "Phase 5 batch completed"
}

function Run-PathABaselineStep {
    param(
        [string]$ScriptPath,
        [string]$RunDir
    )

    Test-FileExists $ScriptPath "Path A baseline script"

    $artifactRoot = Join-Path $RunDir "path_a_baseline"
    Ensure-Dir $artifactRoot

    $stdoutFile = Join-Path $artifactRoot "run_update_runtime_dbs_stdout.txt"
    $stderrFile = Join-Path $artifactRoot "run_update_runtime_dbs_stderr.txt"
    $jsonOut    = Join-Path $artifactRoot "runtime_db_build.json"

    $childArgs = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ScriptPath,
        "-JsonOut", $jsonOut
    )

    if ($SkipPathAVerify) {
        $childArgs += "-SkipVerify"
    }

    Write-Info "Running Path A baseline build..."
    Write-Host "[REPO-SMOKE][PATH-A-BASELINE] pwsh $($childArgs -join ' ')" -ForegroundColor DarkYellow

    & pwsh @childArgs 1> $stdoutFile 2> $stderrFile

    if ($LASTEXITCODE -ne 0) {
        $out = ""
        $err = ""
        if (Test-Path -LiteralPath $stdoutFile) {
            $out = [System.IO.File]::ReadAllText($stdoutFile)
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $err = [System.IO.File]::ReadAllText($stderrFile)
        }
        throw "Path A baseline build failed.`n--- STDOUT ---`n$out`n--- STDERR ---`n$err"
    }

    Write-Ok "Path A baseline build completed"
}

function Run-PathAIngestionStep {
    param(
        [string]$ScriptPath,
        [string]$RunDir
    )

    Test-FileExists $ScriptPath "Path A ingestion script"

    $artifactRoot = Join-Path $RunDir "path_a_ingestion"
    Ensure-Dir $artifactRoot

    $stdoutFile = Join-Path $artifactRoot "run_ingestion_stdout.txt"
    $stderrFile = Join-Path $artifactRoot "run_ingestion_stderr.txt"

    $childArgs = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ScriptPath
    )

    if ($SkipPathAVerify) {
        $childArgs += "-SkipVerify"
    }
    if ($RunOfflineAnalysis) {
        $childArgs += "-RunOfflineAnalysis"
    }
    if ($EnableConverterCache) {
        $childArgs += "-EnableConverterCache"
    }

    Write-Info "Running Path A ingestion/runtime test..."
    Write-Host "[REPO-SMOKE][PATH-A-INGESTION] pwsh $($childArgs -join ' ')" -ForegroundColor DarkYellow

    & pwsh @childArgs 1> $stdoutFile 2> $stderrFile

    if ($LASTEXITCODE -ne 0) {
        $out = ""
        $err = ""
        if (Test-Path -LiteralPath $stdoutFile) {
            $out = [System.IO.File]::ReadAllText($stdoutFile)
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $err = [System.IO.File]::ReadAllText($stderrFile)
        }
        throw "Path A ingestion/runtime test failed.`n--- STDOUT ---`n$out`n--- STDERR ---`n$err"
    }

    Write-Ok "Path A ingestion/runtime test completed"
}

function Run-DeploymentGateStep {
    param(
        [string]$ScriptPath,
        [string]$RunDir
    )

    Test-FileExists $ScriptPath "Deployment gate script"

    $artifactRoot = Join-Path $RunDir "deployment_gate"
    Ensure-Dir $artifactRoot

    $stdoutFile = Join-Path $artifactRoot "deployment_gate_stdout.txt"
    $stderrFile = Join-Path $artifactRoot "deployment_gate_stderr.txt"
    $jsonOut    = Join-Path $artifactRoot "deployment_gate_report.json"

    $childArgs = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ScriptPath,
        "-OutputReport", $jsonOut
    )

    if ($SkipPathAVerify) {
        $childArgs += "-SkipStrictRuntimeVerify"
    }

    Write-Info "Running deployment gate..."
    Write-Host "[REPO-SMOKE][DEPLOYMENT-GATE] pwsh $($childArgs -join ' ')" -ForegroundColor DarkYellow

    & pwsh @childArgs 1> $stdoutFile 2> $stderrFile

    if ($LASTEXITCODE -ne 0) {
        $out = ""
        $err = ""
        if (Test-Path -LiteralPath $stdoutFile) {
            $out = [System.IO.File]::ReadAllText($stdoutFile)
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $err = [System.IO.File]::ReadAllText($stderrFile)
        }
        throw "Deployment gate failed.`n--- STDOUT ---`n$out`n--- STDERR ---`n$err"
    }

    Write-Ok "Deployment gate completed"
}

# -------------------- MAIN --------------------

Push-Location $ProjectRoot
try {
    $root = (Resolve-Path ".").Path
    $outRoot = Resolve-AbsolutePath $OutputDir $root
    Ensure-Dir $outRoot

    $runDir = New-SharedRunDirectory $outRoot
    $python = Get-ProjectPython $root $PythonExe

    $bootstrapAbs      = Resolve-AbsolutePath $BootstrapScript $root
    $phase5Abs         = Resolve-AbsolutePath $Phase5BatchScript $root
    $runtimeDbBuildAbs = Resolve-AbsolutePath $RuntimeDbBuildScript $root
    $ingestionAbs      = Resolve-AbsolutePath $IngestionRuntimeScript $root
    $deploymentGateAbs = Resolve-AbsolutePath $DeploymentGateScript $root

    $results = @()

    if (-not $SkipBootstrap) {
        $results += Invoke-Step "Bootstrap" { Run-BootstrapStep $root }
    }
    else {
        Write-Warn2 "Skipping bootstrap"
    }

    if (-not $SkipEngineFeedback) {
        $results += Invoke-Step "Engine Smoke" { Run-EngineFeedbackImportSmoke $python $runDir }
    }
    else {
        Write-Warn2 "Skipping engine/feedback import smoke"
    }

    if ($RunPathABaseline) {
        $results += Invoke-Step "Path A Baseline" { Run-PathABaselineStep $runtimeDbBuildAbs $runDir }
    }
    else {
        Write-Warn2 "Skipping Path A baseline"
    }

    if ($RunPathAIngestion) {
        $results += Invoke-Step "Path A Ingestion" { Run-PathAIngestionStep $ingestionAbs $runDir }
    }
    else {
        Write-Warn2 "Skipping Path A ingestion/runtime test"
    }

    if (-not $SkipPhase5) {
        $results += Invoke-Step "Phase5 Batch" { Run-Phase5BatchStep $phase5Abs $runDir }
    }
    else {
        Write-Warn2 "Skipping Phase 5 batch"
    }

    if ($RunDeploymentGate) {
        $results += Invoke-Step "Deployment Gate" { Run-DeploymentGateStep $deploymentGateAbs $runDir }
    }
    else {
        Write-Warn2 "Skipping deployment gate"
    }

    $summaryPath = Join-Path $runDir "repo_smoke_summary.json"

    $summary = [PSCustomObject]@{
        root                          = $root
        python                        = $python
        bootstrap_script              = $BootstrapScript
        phase5_script                 = $Phase5BatchScript
        runtime_db_build_script       = $RuntimeDbBuildScript
        ingestion_runtime_script      = $IngestionRuntimeScript
        deployment_gate_script        = $DeploymentGateScript
        output_root                   = $outRoot
        run_dir                       = $runDir

        validation_mode               = [bool]$OfflineValidationMode
        stage_probes                  = [bool]$RunStageProbes
        orchestrator                  = [bool]$RunOrchestrator

        skip_bootstrap                = [bool]$SkipBootstrap
        skip_engine_feedback          = [bool]$SkipEngineFeedback
        skip_phase5                   = [bool]$SkipPhase5
        run_path_a_baseline           = [bool]$RunPathABaseline
        run_path_a_ingestion          = [bool]$RunPathAIngestion
        run_deployment_gate           = [bool]$RunDeploymentGate
        skip_path_a_verify            = [bool]$SkipPathAVerify
        run_offline_analysis          = [bool]$RunOfflineAnalysis
        enable_converter_cache        = [bool]$EnableConverterCache

        skip_determinism              = [bool]$SkipDeterminism
        skip_schema                   = [bool]$SkipSchema
        skip_contract                 = [bool]$SkipContract
        skip_coverage                 = [bool]$SkipCoverage
        skip_integrity                = [bool]$SkipIntegrity
        skip_drift                    = [bool]$SkipDrift
        skip_regression               = [bool]$SkipRegression

        regression_tolerance          = $RegressionTolerance
        drift_tolerance               = $DriftTolerance

        enable_case_expect_override   = [bool]$EnableCaseExpectOverride
        required_event_types          = $RequiredEventTypes
        require_interpretation_output = [bool]$RequireInterpretationOutput
        skip_non_feedback_cases       = [bool]$SkipNonFeedbackCases
        strict_validation             = [bool]$StrictValidation
        summary_output_path           = $SummaryOutputPath

        passed                        = @($results | Where-Object { $_.Status -eq "PASS" }).Count
        failed                        = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
        results                       = $results
    }

    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

    Write-Host ""
    Write-Host "============================================="
    Write-Host "Repo Smoke Summary"
    Write-Host "============================================="
    Write-Host "RunDir                     : $runDir"
    Write-Host "Python                     : $python"
    Write-Host "Passed                     : $($summary.passed)"
    Write-Host "Failed                     : $($summary.failed)"
    Write-Host "Summary                    : $summaryPath"

    if ($summary.failed -gt 0) { exit 1 }
    exit 0
}
finally {
    Pop-Location
}
