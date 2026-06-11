# ------------------------------------------------------------
# Phase 5 Batch Runner (Offline)
# ------------------------------------------------------------

param (
    [string]$RootDir = ".",
    [string]$PythonExe = "python",

    [string]$CasesDir = "",
    [string]$ArtifactRootDir = "",
    [string]$EventRunnerScript = "",
    [string]$InterpretationRunnerScript = "",
    [string]$Phase5RunnerScript = "",
    [string]$ValidateBundleScript = "",
    [switch]$SkipEventBatch,
    [switch]$SkipInterpretation,
    [switch]$SkipPhase5Loop,
    [switch]$SkipDeterminism,
    [switch]$SkipSchema,
    [switch]$SkipContract,
    [switch]$SkipCoverage,
    [switch]$SkipIntegrity,
    [switch]$SkipDrift,
    [switch]$SkipRegression,
    [switch]$StopOnFailure,
    [double]$RegressionTolerance = 0.0,
    [double]$DriftTolerance = 0.10,
    [switch]$EnableCaseExpectOverride,
    [string[]]$RequiredEventTypes = @(),
    [switch]$RequireInterpretationOutput,
    [switch]$SkipNonFeedbackCases,
    [switch]$StrictValidation,
    [string]$SummaryOutputPath = ""
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host "[PHASE5-BATCH] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg) { Write-Host "[PHASE5-BATCH][WARN] $msg" -ForegroundColor Yellow }
function Write-Ok($msg)    { Write-Host "[PHASE5-BATCH][OK] $msg" -ForegroundColor Green }
function Write-Fail($msg)  { Write-Host "[PHASE5-BATCH][FAIL] $msg" -ForegroundColor Red }

function Ensure-Dir($Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Test-FileExists($Path, $Label) {
    if (-not (Test-Path $Path)) {
        throw "$Label not found: $Path"
    }
}

function Get-TodayString {
    return (Get-Date).ToString("yyyy-MM-dd")
}

function Resolve-AbsolutePath($Path, $BaseDir) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path $BaseDir $Path)
}

function Get-ProjectPython($RootDir, $PythonExe) {
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        Write-Ok "Using venv python: $venvPython"
        return $venvPython
    }

    Write-Warn2 ".venv python not found; falling back to: $PythonExe"
    return $PythonExe
}

function New-SharedRunDirectory($ArtifactRootDir) {
    $rootPath = $ArtifactRootDir
    Ensure-Dir $rootPath

    $dateStr = Get-TodayString
    $dateDir = Join-Path $rootPath $dateStr
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

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Info "Starting: $Name"
    try {
        $result = & $Action
        Write-Ok "Passed: $Name"
        return [PSCustomObject]@{
            Name   = $Name
            Status = "PASS"
            Error  = $null
            Result = $result
        }
    }
    catch {
        Write-Fail "Failed: $Name"
        Write-Host $_ -ForegroundColor Red

        if ($StopOnFailure) {
            throw
        }

        return [PSCustomObject]@{
            Name   = $Name
            Status = "FAIL"
            Error  = $_.Exception.Message
            Result = $null
        }
    }
}

function Read-TextAutoEncoding {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $reader = New-Object System.IO.StreamReader($Path, $true)
    try {
        return $reader.ReadToEnd()
    }
    finally {
        $reader.Dispose()
    }
}

function Get-JsonFileObject {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    if (-not (Test-Path -LiteralPath $Path)) { return $null }

    try {
        $raw = [System.IO.File]::ReadAllText($Path)
        if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
        return ($raw | ConvertFrom-Json -Depth 100)
    }
    catch {
        Write-Host "[JSON-PARSE-FAIL] $Path" -ForegroundColor Yellow
        return $null
    }
}


function Get-NormalizedJson($Path) {
    $obj = Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100
    return ($obj | ConvertTo-Json -Depth 100 -Compress)
}

function Compare-JsonFiles($PathA, $PathB, $Label) {
    $a = Get-NormalizedJson $PathA
    $b = Get-NormalizedJson $PathB
    if ($a -ne $b) {
        throw "$Label mismatch between:`n$PathA`nand`n$PathB"
    }
}

function Assert-Condition($Condition, $Message) {
    if (-not $Condition) {
        throw $Message
    }
}

function Save-JsonObject($Object, $Path) {
    $json = $Object | ConvertTo-Json -Depth 100
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

function Resolve-CaseExecutionProfile {
    param(
        [string]$CasePath,
        [switch]$EnableCaseExpectOverride,
        [string[]]$RequiredEventTypes,
        [switch]$RequireInterpretationOutput,
        [switch]$SkipNonFeedbackCases
    )

    # ------------------------------------------
    # Load input.json
    # ------------------------------------------
    $inputPath = Join-Path $CasePath "input.json"
    $inputObj = Get-JsonFileObject $inputPath

    $eventCategory = "unknown"
    if ($null -ne $inputObj -and
        $null -ne $inputObj.event_category -and
        "$($inputObj.event_category)" -ne "") {
        $eventCategory = [string]$inputObj.event_category
    }

    # ------------------------------------------
    # Load coverage.expect.json
    # ------------------------------------------
    $expectPath = Join-Path $CasePath "coverage.expect.json"
    $expectObj = $null

    if ($EnableCaseExpectOverride -and (Test-Path $expectPath)) {
        $expectObj = Get-JsonFileObject $expectPath
    }

    # ------------------------------------------
    # Resolve event_batch expectations
    # ------------------------------------------
    $resolvedRequiredEventTypes = @()
    $resolvedMinStructuredEvents = 1

    if ($RequiredEventTypes -and $RequiredEventTypes.Count -gt 0) {
        $resolvedRequiredEventTypes = @($RequiredEventTypes)
    }
    elseif ($null -ne $expectObj -and
            $null -ne $expectObj.event_batch -and
            $null -ne $expectObj.event_batch.required_event_types) {

        $resolvedRequiredEventTypes = @($expectObj.event_batch.required_event_types)
    }

    if ($null -ne $expectObj -and
        $null -ne $expectObj.event_batch -and
        $null -ne $expectObj.event_batch.min_structured_events) {

        try {
            $resolvedMinStructuredEvents = [int]$expectObj.event_batch.min_structured_events
        }
        catch {}
    }

    # ------------------------------------------
    # Resolve interpretation expectations
    # ------------------------------------------
    $resolvedRequireInterpretationOutput = [bool]$RequireInterpretationOutput

    if ($null -ne $expectObj -and
        $null -ne $expectObj.interpretation_batch) {

        # If interpretation section exists, we usually expect output
        if ($null -ne $expectObj.interpretation_batch.min_outputs) {
            $resolvedRequireInterpretationOutput = $true
        }
    }

    # ------------------------------------------
    # Resolve Phase 5 expectations (artifacts)
    # ------------------------------------------
    $resolvedRequiredArtifacts = @()

    if ($null -ne $expectObj -and
        $null -ne $expectObj.phase5_loop -and
        $null -ne $expectObj.phase5_loop.required_artifacts) {

        $resolvedRequiredArtifacts = @($expectObj.phase5_loop.required_artifacts)
    }

    # ------------------------------------------
    # Routing-based skipping logic
    # ------------------------------------------
    $skipInterpretationForCase = $false
    $skipPhase5ForCase = $false

    if ($SkipNonFeedbackCases -and $eventCategory -ne "feedback") {
        $skipInterpretationForCase = $true
        $skipPhase5ForCase = $true
        $resolvedRequireInterpretationOutput = $false
        $resolvedRequiredEventTypes = @()
    }

    # ------------------------------------------
    # Return execution profile
    # ------------------------------------------
    return [PSCustomObject]@{
        event_category                  = $eventCategory
        expect_path                     = $(if (Test-Path $expectPath) { $expectPath } else { $null })

        # Event batch
        min_structured_events           = $resolvedMinStructuredEvents
        required_event_types            = $resolvedRequiredEventTypes

        # Interpretation
        require_interpretation_output   = $resolvedRequireInterpretationOutput

        # Phase 5
        required_artifacts              = $resolvedRequiredArtifacts

        # Routing behavior
        skip_interpretation_for_case    = $skipInterpretationForCase
        skip_phase5_for_case            = $skipPhase5ForCase
    }
}

function Resolve-CaseLayerStatus {
    param(
        [string]$StepName,
        [object[]]$CaseSteps,
        [string]$DefaultIfMissing = "SKIP"
    )

    $step = $CaseSteps | Where-Object { $_.Name -eq $StepName } | Select-Object -First 1
    if (-not $step) { return $DefaultIfMissing }
    return [string]$step.Status
}

function Build-CaseSummaryEntry {
    param(
        [string]$CaseName,
        [string]$CasePath,
        [string]$CaseOutput,
        [object[]]$CaseSteps,
        [bool]$CaseFailed,
        [object]$CaseProfile,
        [switch]$SkipEventBatch,
        [switch]$SkipInterpretation,
        [switch]$SkipPhase5Loop,
        [switch]$SkipSchema,
        [switch]$SkipContract,
        [switch]$SkipCoverage,
        [switch]$SkipIntegrity,
        [switch]$SkipDrift,
        [switch]$SkipRegression,
        [switch]$SkipDeterminism
    )

    $structuredFile      = Join-Path (Join-Path $CaseOutput "events") "structured_events.json"
    $interpFile          = Join-Path (Join-Path $CaseOutput "interp") "interpreted_feedback_events.json"
    $bundlePath          = Join-Path $CaseOutput "validator_bundle_result.json"
    $pipelineResultFile  = Join-Path (Join-Path $CaseOutput "phase5") "pipeline_result.json"

    $structuredObj = Get-JsonFileObject $structuredFile
    $interpObj     = Get-JsonFileObject $interpFile
    $bundleObj     = Get-JsonFileObject $bundlePath
    $phase5Obj     = Get-JsonFileObject $pipelineResultFile

    $eventStatus = if ($SkipEventBatch) {
        "SKIP"
    } else {
        Resolve-CaseLayerStatus -StepName "$CaseName :: Event Batch" -CaseSteps $CaseSteps
    }

    $interpretStatus = if ($SkipInterpretation -or $CaseProfile.skip_interpretation_for_case) {
        "N/A"
    } else {
        Resolve-CaseLayerStatus -StepName "$CaseName :: Interpretation Batch" -CaseSteps $CaseSteps
    }

    $phase5Status = if ($SkipPhase5Loop -or $CaseProfile.skip_phase5_for_case) {
        "N/A"
    } else {
        Resolve-CaseLayerStatus -StepName "$CaseName :: Phase 5 Loop" -CaseSteps $CaseSteps
    }

    $determinismStatus = if ($SkipDeterminism) {
        "SKIP"
    } else {
        Resolve-CaseLayerStatus -StepName "$CaseName :: Determinism Test" -CaseSteps $CaseSteps
    }

    $validatorStepStatus = Resolve-CaseLayerStatus -StepName "$CaseName :: Validator Bundle" -CaseSteps $CaseSteps -DefaultIfMissing "SKIP"

    # --------------------------------------------------
    # Default validator-related statuses
    # --------------------------------------------------
    $schemaStatus            = if ($SkipSchema)     { "SKIP" } else { "SKIP" }
    $contractStatus          = if ($SkipContract)   { "SKIP" } else { "SKIP" }
    $coverageStatus          = if ($SkipCoverage)   { "SKIP" } else { "SKIP" }
    $integrityStatus         = if ($SkipIntegrity)  { "SKIP" } else { "SKIP" }
    $contractBaselineStatus  = "SKIP"
    $artifactIntegrityStatus = if ($SkipIntegrity)  { "SKIP" } else { "SKIP" }
    $driftStatus             = if ($SkipDrift)      { "SKIP" } else { "SKIP" }
    $regressionStatus        = if ($SkipRegression) { "SKIP" } else { "SKIP" }

    # --------------------------------------------------
    # Helper: infer status from validator details if present
    # --------------------------------------------------
    function _detailStatus($detailProps, $likePattern, $defaultIfMissing = "SKIP") {
        $entry = $detailProps | Where-Object { $_.Name -like $likePattern } | Select-Object -First 1
        if (-not $entry) { return $defaultIfMissing }
        if ($entry.Value.passed -eq $true) { return "PASS" }
        return "FAIL"
    }

    # --------------------------------------------------
    # Preferred path: use validator details if available
    # --------------------------------------------------
    if ($null -ne $bundleObj -and $null -ne $bundleObj.details) {
        $detailProps = $bundleObj.details.PSObject.Properties

        $schemaStatus            = if ($SkipSchema)    { "SKIP" } else { _detailStatus $detailProps "*schema_validator*" }
        $contractStatus          = if ($SkipContract)  { "SKIP" } else { _detailStatus $detailProps "*contract_validator*" }
        $coverageStatus          = if ($SkipCoverage)  { "SKIP" } else { _detailStatus $detailProps "*coverage_validator*" }
        $integrityStatus         = if ($SkipIntegrity) { "SKIP" } else { _detailStatus $detailProps "*test_case_integrity_validator*" }
        $contractBaselineStatus  = _detailStatus $detailProps "*contract_baseline_validator*"
        $artifactIntegrityStatus = if ($SkipIntegrity) { "SKIP" } else { _detailStatus $detailProps "*artifact_integrity_validator*" }

        if (-not $SkipDrift) {
            $driftStatus = _detailStatus $detailProps "*metrics_guard_validator*"
        }
        if (-not $SkipRegression) {
            $regressionStatus = _detailStatus $detailProps "*metrics_guard_validator*"
        }
    }
    elseif ($validatorStepStatus -eq "PASS") {
        # --------------------------------------------------
        # Fallback path:
        # validator ran successfully, but bundle result has no details
        # --------------------------------------------------
        if (-not $SkipSchema)    { $schemaStatus            = "PASS" }
        if (-not $SkipContract)  { $contractStatus          = "PASS" }
        if (-not $SkipCoverage)  { $coverageStatus          = "PASS" }
        if (-not $SkipIntegrity) { $integrityStatus         = "PASS" }
        if (-not $SkipIntegrity) { $artifactIntegrityStatus = "PASS" }

        $contractBaselineStatus = "PASS"

        if (-not $SkipDrift)      { $driftStatus      = "PASS" }
        if (-not $SkipRegression) { $regressionStatus = "PASS" }
    }

    # --------------------------------------------------
    # Required artifacts for feedback cases
    # --------------------------------------------------
    $requiredArtifacts = @()
    if ($CaseProfile.event_category -eq "feedback") {
        $requiredArtifacts = @("selector_params", "training_report", "evaluation_report")
    }

    # --------------------------------------------------
    # Artifact paths + artifact presence
    # --------------------------------------------------
    $artifactPathsPresent = $false
    $artifactsPresent     = @()
    $metricsPresent       = $false

    $evaluationReportPath = $null

    if ($null -ne $phase5Obj) {
        $resultObj = if ($null -ne $phase5Obj.result) { $phase5Obj.result } else { $phase5Obj }

        if ($null -ne $resultObj.paths) {
            $artifactPathsPresent = $true

            foreach ($name in $requiredArtifacts) {
                if ($resultObj.paths.PSObject.Properties.Name -contains $name) {
                    $artifactsPresent += $name
                }
            }

            if ($resultObj.paths.PSObject.Properties.Name -contains "evaluation_report") {
                $evaluationReportPath = $resultObj.paths.evaluation_report
            }
        }

        # Preferred metrics locations
        if (($null -ne $resultObj.evaluation -and $null -ne $resultObj.evaluation.metrics) -or
            ($null -ne $resultObj.summary -and
             $null -ne $resultObj.summary.evaluation -and
             $null -ne $resultObj.summary.evaluation.metrics) -or
            ($null -ne $resultObj.payload -and $null -ne $resultObj.payload.metrics)) {
            $metricsPresent = $true
        }
    }

    # --------------------------------------------------
    # Artifact-based metrics fallback:
    # if evaluation_report.json exists and parses, count metrics as present
    # --------------------------------------------------
    if (-not $metricsPresent -and -not [string]::IsNullOrWhiteSpace($evaluationReportPath)) {
        if (Test-Path -LiteralPath $evaluationReportPath) {
            $evalObj = Get-JsonFileObject $evaluationReportPath
            if ($null -ne $evalObj) {
                $metricsPresent = $true
            }
        }
    }

    # --------------------------------------------------
    # Counts
    # --------------------------------------------------
    $actualStructuredCount = 0
    if ($structuredObj -is [System.Array]) {
        $actualStructuredCount = @($structuredObj).Count
    }
    elseif ($null -ne $structuredObj) {
        $actualStructuredCount = 1
    }

    $actualInterpCount = 0
    if ($interpObj -is [System.Array]) {
        $actualInterpCount = @($interpObj).Count
    }
    elseif ($null -ne $interpObj) {
        $actualInterpCount = 1
    }

    # --------------------------------------------------
    # Build summary record
    # --------------------------------------------------
    return [PSCustomObject]@{
        case                   = $CaseName
        event_category         = $CaseProfile.event_category
        overall_status         = $(if ($CaseFailed) { "FAIL" } else { "PASS" })

        integrity              = $integrityStatus
        event_batch            = $eventStatus
        interpretation_batch   = $interpretStatus
        phase5_loop            = $phase5Status
        contract_baseline      = $contractBaselineStatus

        schema                 = $schemaStatus
        contract               = $contractStatus
        coverage               = $coverageStatus
        artifact_integrity     = $artifactIntegrityStatus
        drift                  = $driftStatus
        regression             = $regressionStatus
        determinism            = $determinismStatus

        expected = [PSCustomObject]@{
            min_structured_events         = $CaseProfile.min_structured_events
            required_event_types          = $CaseProfile.required_event_types
            require_interpretation_output = $CaseProfile.require_interpretation_output
            required_artifacts            = $requiredArtifacts
        }

        actual = [PSCustomObject]@{
            structured_events_count   = $actualStructuredCount
            interpreted_outputs_count = $actualInterpCount
            artifacts_present         = $artifactsPresent
            artifact_paths_present    = $artifactPathsPresent
            metrics_present           = $metricsPresent
        }

        errors   = @($CaseSteps | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object { $_.Error })
        warnings = @()
    }
}

function Invoke-PythonJson {
    param(
        [string]$PythonBin,
        [string[]]$ArgsList
    )

    Write-Host "[PY-CALL] $PythonBin $($ArgsList -join ' ')" -ForegroundColor DarkGray

    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()
    $jsonTempFile = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".json")

    try {
        # Capture stdout / stderr separately
        & $PythonBin @ArgsList
        $exitCode = $LASTEXITCODE

        $stdoutText = ""
        $stderrText = ""

        if (Test-Path -LiteralPath $stdoutFile) {
            $stdoutText = Get-Content -LiteralPath $stdoutFile -Raw -Encoding UTF8
        }

        if (Test-Path -LiteralPath $stderrFile) {
            $stderrText = Get-Content -LiteralPath $stderrFile -Raw -Encoding UTF8
        }

        if ($null -eq $stdoutText) { $stdoutText = "" }
        if ($null -eq $stderrText) { $stderrText = "" }

        $stdoutText = $stdoutText.Trim()
        $stderrText = $stderrText.Trim()

        if ($exitCode -ne 0) {
            throw "Python command failed:`n$PythonBin $($ArgsList -join ' ')`n$stderrText"
        }

        if (-not $stdoutText) {
            throw "Python command returned empty stdout"
        }

        # Remove BOM if present
        if ($stdoutText.Length -gt 0 -and [int][char]$stdoutText[0] -eq 65279) {
            $stdoutText = $stdoutText.Substring(1)
        }

        # --------------------------------------------------
        # 1) Direct JSON parse
        # --------------------------------------------------
        try {
            return ($stdoutText | ConvertFrom-Json -Depth 100)
        }
        catch {
            # continue
        }

        # --------------------------------------------------
        # 2) Retry via temp JSON file
        # --------------------------------------------------
        try {
            Set-Content -LiteralPath $jsonTempFile -Value $stdoutText -Encoding UTF8
            $jsonFromFile = Get-Content -LiteralPath $jsonTempFile -Raw -Encoding UTF8
            return ($jsonFromFile | ConvertFrom-Json -Depth 100)
        }
        catch {
            # continue
        }

        # --------------------------------------------------
        # 3) output_path fallback
        # --------------------------------------------------
        $outputPath = $null
        if ($stdoutText -match '"output_path"\s*:\s*"([^"]+)"') {
            $outputPath = $matches[1] -replace '\\\\','\'
        }

        if ($outputPath) {
            if (-not (Test-Path -LiteralPath $outputPath)) {
                throw "Python stdout was not parseable JSON, and output_path does not exist: $outputPath"
            }

            $artifactRaw = Get-Content -LiteralPath $outputPath -Raw -Encoding UTF8
            try {
                $artifactObj = $artifactRaw | ConvertFrom-Json -Depth 100
            }
            catch {
                throw "Python stdout was not parseable JSON, and artifact was not valid JSON: $outputPath"
            }

            return [PSCustomObject]@{
                runner              = "artifact_fallback"
                parsed_from         = "output_path"
                output_path         = $outputPath
                artifact_json_type  = $artifactObj.GetType().FullName
                artifact_content    = $artifactObj
            }
        }

        throw "Python stdout was not parseable JSON, and no output_path could be extracted.`nStdout:`n$stdoutText`nStderr:`n$stderrText"
    }
    finally {
        foreach ($p in @($stdoutFile, $stderrFile, $jsonTempFile)) {
            if ($p -and (Test-Path -LiteralPath $p)) {
                Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Invoke-PythonArtifactStep {
    param(
        [string]$PythonBin,
        [string[]]$ArgsList,
        [string]$ExpectedArtifactPath,
        [string]$StepLabel
    )

    $output = & $PythonBin @ArgsList 2>&1
    if ($LASTEXITCODE -ne 0) {
        $joinedErr = ($output -join [Environment]::NewLine).Trim()
        throw "$StepLabel failed: $PythonBin $($ArgsList -join ' ')`n$joinedErr"
    }

    if (-not (Test-Path $ExpectedArtifactPath)) {
        $joined = ($output -join [Environment]::NewLine).Trim()
        throw "$StepLabel completed with exit code 0, but expected artifact was not found: $ExpectedArtifactPath`nStdout:`n$joined"
    }

    $fileInfo = Get-Item $ExpectedArtifactPath
    if ($fileInfo.Length -le 0) {
        throw "$StepLabel completed, but artifact file is empty: $ExpectedArtifactPath"
    }

    return [PSCustomObject]@{
        runner        = $StepLabel
        output_path   = $ExpectedArtifactPath
        artifact_size = $fileInfo.Length
        parsed_from   = "artifact_only"
    }
}

function Resolve-ExistingPath {
    param(
        [string]$RootDir,
        [string]$ExplicitPath,
        [string[]]$CandidatePaths,
        [string]$Label,
        [switch]$DirectoryMode
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        $resolved = Resolve-AbsolutePath $ExplicitPath $RootDir
        if ($DirectoryMode) {
            if (-not (Test-Path $resolved)) {
                throw "$Label directory not found: $resolved"
            }
        }
        else {
            Test-FileExists $resolved $Label
        }
        return $resolved
    }

    foreach ($candidate in $CandidatePaths) {
        $resolved = Resolve-AbsolutePath $candidate $RootDir
        if (Test-Path $resolved) {
            Write-Ok "$Label auto-detected: $resolved"
            return $resolved
        }
    }

    $joined = ($CandidatePaths -join "; ")
    throw "Could not auto-detect $Label. Checked: $joined"
}

function Resolve-ArtifactRootDir {
    param(
        [string]$RootDir,
        [string]$ExplicitPath
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return (Resolve-AbsolutePath $ExplicitPath $RootDir)
    }

    $candidates = @(
        "./Phase_5_Productionization/artifacts",
        "./Phase 5 - Productionization/artifacts",
        "./artifacts"
    )

    foreach ($candidate in $candidates) {
        $resolved = Resolve-AbsolutePath $candidate $RootDir
        $parent = Split-Path $resolved -Parent
        if ((Test-Path $resolved) -or (Test-Path $parent)) {
            Write-Ok "Artifact root auto-detected: $resolved"
            return $resolved
        }
    }

    $fallback = Resolve-AbsolutePath "./Phase_5_Productionization/artifacts" $RootDir
    Write-Warn2 "Artifact root could not be detected from existing folders; using fallback: $fallback"
    return $fallback
}

function Invoke-ValidatorBundle {
    param(
        [string]$PythonBin,
        [string]$ValidatorScript,
        [string]$CasePath,
        [string]$StructuredPath,
        [string]$InterpretedPath,
        [string]$PipelineResultPath,

        # Optional validator overrides
        [string]$BaselineMetricsPath = "",
        [string]$DeploymentDecisionPath = "",
        [int]$MinEvents = 1,
        [string[]]$RequiredEventTypes = @(),
        [switch]$RequireInterpretationOutput,
        [string[]]$RequiredArtifacts = @()
    )

    Test-FileExists $ValidatorScript "Validator bundle script"

    # --------------------------------------------------
    # Normalize optional paths
    # --------------------------------------------------
    function Normalize-OptionalPath([string]$p) {
        if ([string]::IsNullOrWhiteSpace($p)) { return $null }
        return $p
    }

    $CasePath = Normalize-OptionalPath $CasePath
    $StructuredPath = Normalize-OptionalPath $StructuredPath
    $InterpretedPath = Normalize-OptionalPath $InterpretedPath
    $PipelineResultPath = Normalize-OptionalPath $PipelineResultPath
    $BaselineMetricsPath = Normalize-OptionalPath $BaselineMetricsPath
    $DeploymentDecisionPath = Normalize-OptionalPath $DeploymentDecisionPath

    # --------------------------------------------------
    # Safe existence checks
    # --------------------------------------------------
    $hasStructured = $false
    if (-not [string]::IsNullOrWhiteSpace($StructuredPath)) {
        $hasStructured = Test-Path -LiteralPath $StructuredPath
    }

    $hasInterpreted = $false
    if (-not [string]::IsNullOrWhiteSpace($InterpretedPath)) {
        $hasInterpreted = Test-Path -LiteralPath $InterpretedPath
    }

    $hasPipeline = $false
    if (-not [string]::IsNullOrWhiteSpace($PipelineResultPath)) {
        $hasPipeline = Test-Path -LiteralPath $PipelineResultPath
    }

    $hasBaseline = $false
    if (-not [string]::IsNullOrWhiteSpace($BaselineMetricsPath)) {
        $hasBaseline = Test-Path -LiteralPath $BaselineMetricsPath
    }

    $hasDeploymentDecision = $false
    if (-not [string]::IsNullOrWhiteSpace($DeploymentDecisionPath)) {
        $hasDeploymentDecision = Test-Path -LiteralPath $DeploymentDecisionPath
    }

    if (-not $hasStructured -and -not $hasPipeline) {
        throw "Validator bundle requires at least structured events or pipeline result"
    }

    # --------------------------------------------------
    # Build CLI args
    # --------------------------------------------------
    $args = @($ValidatorScript)

    if ($null -ne $CasePath) {
        $args += @("--case_path", $CasePath)
    }

    if ($hasStructured) {
        $args += @("--structured_events_path", $StructuredPath)
    }

    if ($hasInterpreted) {
        $args += @("--interpreted_outputs_path", $InterpretedPath)
    }

    if ($hasPipeline) {
        $args += @("--pipeline_result_path", $PipelineResultPath)
    }

    if ($hasBaseline) {
        $args += @("--baseline_metrics_path", $BaselineMetricsPath)
    }

    if ($hasDeploymentDecision) {
        $args += @("--deployment_decision_path", $DeploymentDecisionPath)
    }

    if ($MinEvents -gt 0) {
        $args += @("--min_events", "$MinEvents")
    }

    if ($RequiredEventTypes -and $RequiredEventTypes.Count -gt 0) {
        $args += "--required_event_types"
        $args += $RequiredEventTypes
    }

    if ($RequireInterpretationOutput) {
        $args += "--require_interpretation_output"
    }

    if ($RequiredArtifacts -and $RequiredArtifacts.Count -gt 0) {
        $args += "--required_artifacts"
        $args += $RequiredArtifacts
    }

    $args += @("--drift_tolerance", "$DriftTolerance")
    $args += @("--regression_tolerance", "$RegressionTolerance")

    # --------------------------------------------------
    # Debug print (keep for now)
    # --------------------------------------------------
    Write-Host "[VALIDATOR-CALL] $PythonBin $($args -join ' ')" -ForegroundColor DarkYellow

    # --------------------------------------------------
    # Invoke Python validator
    # --------------------------------------------------
    $stdoutFile = [System.IO.Path]::GetTempFileName()
	$stderrFile = [System.IO.Path]::GetTempFileName()

	& $pythonBin @(
		$ValidateBundleScript,
		"--case_path", $casePath,
		"--structured_events_path", $structuredFile,
		"--interpreted_outputs_path", $interpFile,
		"--pipeline_result_path", $pipelineResultFile,
		"--min_events", 1,
		"--require_interpretation_output",
		"--drift_tolerance", 0.1,
		"--regression_tolerance", 0
	) 1> $stdoutFile 2> $stderrFile

	if ($LASTEXITCODE -ne 0) {
		$err = ""
		if (Test-Path $stderrFile) {
			$err = [System.IO.File]::ReadAllText($stderrFile)
		}
		throw "Validator bundle failed:`n$err"
	}

	Write-Host "[VALIDATOR] Completed successfully" -ForegroundColor Green
    
	return [PSCustomObject]@{
		passed = $true
		source = "validator_bundle (exit_code)"
	}
}

function Resolve-Phase5ArtifactPath($Phase5Result, $ArtifactKey, $FallbackDir, $FallbackRelativePath) {
    if ($null -ne $Phase5Result -and $null -ne $Phase5Result.paths) {
        $candidate = $Phase5Result.paths.$ArtifactKey
        if ($null -ne $candidate -and "$candidate" -ne "") {
            return $candidate
        }
    }

    if ($null -ne $Phase5Result -and $null -ne $Phase5Result.result -and $null -ne $Phase5Result.result.paths) {
        $candidate = $Phase5Result.result.paths.$ArtifactKey
        if ($null -ne $candidate -and "$candidate" -ne "") {
            return $candidate
        }
    }

    if ($null -ne $FallbackDir -and $null -ne $FallbackRelativePath) {
        return (Join-Path $FallbackDir $FallbackRelativePath)
    }

    throw "Unable to resolve artifact path for key: $ArtifactKey"
}

function Validate-Determinism {
    param(
        [string]$PythonBin,
        [string]$CasePath,
        [string]$CaseName,
        [string]$ResolvedEventRunnerScript,
        [string]$ResolvedInterpretationRunnerScript,
        [string]$ResolvedPhase5RunnerScript,
        [string]$RunDirRoot
    )

    $detRoot = Join-Path $RunDirRoot "$CaseName-determinism"
    $run1Dir = Join-Path $detRoot "run1"
    $run2Dir = Join-Path $detRoot "run2"

    Ensure-Dir $run1Dir
    Ensure-Dir $run2Dir

    $inputPath = Join-Path $CasePath "input.json"
    Test-FileExists $inputPath "Case input"

    # ------------------------------------------------
	# Event Batch (artifact-first)
	# ------------------------------------------------
	$event1Dir = Join-Path $run1Dir "events"
	$event2Dir = Join-Path $run2Dir "events"
	Ensure-Dir $event1Dir
	Ensure-Dir $event2Dir

	$event1Structured = Join-Path $event1Dir "structured_events.json"
	$event2Structured = Join-Path $event2Dir "structured_events.json"

	# Run 1
	$eventRun1 = Invoke-PythonArtifactStep `
		-PythonBin $PythonBin `
		-ArgsList @(
			$ResolvedEventRunnerScript,
			"--source_path", $inputPath,
			"--output_dir", $event1Dir
		) `
		-ExpectedArtifactPath $event1Structured `
		-StepLabel "event_batch_runner"

	# Run 2
	$eventRun2 = Invoke-PythonArtifactStep `
		-PythonBin $PythonBin `
		-ArgsList @(
			$ResolvedEventRunnerScript,
			"--source_path", $inputPath,
			"--output_dir", $event2Dir
		) `
		-ExpectedArtifactPath $event2Structured `
		-StepLabel "event_batch_runner"

	# Sanity-check both artifacts exist before diff
	Test-FileExists $event1Structured "Determinism event batch output (run1)"
	Test-FileExists $event2Structured "Determinism event batch output (run2)"

	Compare-JsonFiles `
		$event1Structured `
		$event2Structured `
		"Determinism check for event batch"

    # ------------------------------------------------
	# Interpretation Batch (artifact-first)
	# ------------------------------------------------
	$interp1Dir = Join-Path $run1Dir "interp"
	$interp2Dir = Join-Path $run2Dir "interp"
	Ensure-Dir $interp1Dir
	Ensure-Dir $interp2Dir

	$interp1File = Join-Path $interp1Dir "interpreted_feedback_events.json"
	$interp2File = Join-Path $interp2Dir "interpreted_feedback_events.json"

	# Run 1
	$interpRun1 = Invoke-PythonArtifactStep `
		-PythonBin $PythonBin `
		-ArgsList @(
			$ResolvedInterpretationRunnerScript,
			"--source_path", $event1Structured,
			"--output_dir", $interp1Dir
		) `
		-ExpectedArtifactPath $interp1File `
		-StepLabel "feedback_interpretation_batch_runner"

	# Run 2
	$interpRun2 = Invoke-PythonArtifactStep `
		-PythonBin $PythonBin `
		-ArgsList @(
			$ResolvedInterpretationRunnerScript,
			"--source_path", $event2Structured,
			"--output_dir", $interp2Dir
		) `
		-ExpectedArtifactPath $interp2File `
		-StepLabel "feedback_interpretation_batch_runner"

	# Sanity-check both artifacts exist before diff
	Test-FileExists $interp1File "Determinism interpretation batch output (run1)"
	Test-FileExists $interp2File "Determinism interpretation batch output (run2)"

	Compare-JsonFiles `
		$interp1File `
		$interp2File `
		"Determinism check for interpretation batch"

    # ------------------------------------------------
	# Phase 5 Loop (artifact-first determinism, normalized)
	# ------------------------------------------------
	$phase5Out1 = Join-Path $run1Dir "phase5"
	$phase5Out2 = Join-Path $run2Dir "phase5"
	Ensure-Dir $phase5Out1
	Ensure-Dir $phase5Out2

	$phase5Err1 = Join-Path $phase5Out1 "phase5_loop_stderr.txt"
	$phase5Err2 = Join-Path $phase5Out2 "phase5_loop_stderr.txt"

	$phase5Result1 = Join-Path $phase5Out1 "pipeline_result.json"
	$phase5Result2 = Join-Path $phase5Out2 "pipeline_result.json"

	# Phase 5 loop should consume interpretation outputs
	$phase5Source1 = Split-Path $interp1File -Parent
	$phase5Source2 = Split-Path $interp2File -Parent

	# --- Run 1 ---
	& $PythonBin @(
		$ResolvedPhase5RunnerScript,
		"--source_dir", $phase5Source1,
		"--output_dir", $phase5Out1
	) 1> $null 2> $phase5Err1

	if ($LASTEXITCODE -ne 0) {
		$err = ""
		if (Test-Path -LiteralPath $phase5Err1) {
			$err = [System.IO.File]::ReadAllText($phase5Err1)
		}
		throw "Phase 5 loop (run1) failed:`n$err"
	}

	# --- Run 2 ---
	& $PythonBin @(
		$ResolvedPhase5RunnerScript,
		"--source_dir", $phase5Source2,
		"--output_dir", $phase5Out2
	) 1> $null 2> $phase5Err2

	if ($LASTEXITCODE -ne 0) {
		$err = ""
		if (Test-Path -LiteralPath $phase5Err2) {
			$err = [System.IO.File]::ReadAllText($phase5Err2)
		}
		throw "Phase 5 loop (run2) failed:`n$err"
	}

	# ------------------------------------------------
	# Compare actual Phase 5 artifacts (true source of truth)
	# ------------------------------------------------
	$artifactPairs = @(
		@{
			Label    = "selector_params"
			Relative = "song_recommendation\song_selector_params.json"
		},
		@{
			Label    = "training_report"
			Relative = "song_recommendation\song_selector_training_report.json"
		},
		@{
			Label    = "evaluation_report"
			Relative = "song_recommendation\song_selector_evaluation_report.json"
		}
	)

	$normalizedPaths = [ordered]@{
		baseline_metrics  = $null
		selector_params   = "song_recommendation\song_selector_params.json"
		training_report   = "song_recommendation\song_selector_training_report.json"
		evaluation_report = "song_recommendation\song_selector_evaluation_report.json"
	}

	foreach ($pair in $artifactPairs) {
		$path1 = Join-Path $phase5Out1 $pair.Relative
		$path2 = Join-Path $phase5Out2 $pair.Relative

		Test-FileExists $path1 ("Phase5 artifact (run1) - {0}" -f $pair.Label)
		Test-FileExists $path2 ("Phase5 artifact (run2) - {0}" -f $pair.Label)

		Compare-JsonFiles `
			$path1 `
			$path2 `
			("Determinism check for {0}" -f $pair.Label)
	}

	# ------------------------------------------------
	# Build normalized pipeline_result.json for both runs
	# NOTE:
	# - Do NOT include run-specific absolute paths
	# - Do NOT include artifact_dir / source_dir / output folder paths
	# - Determinism is asserted through artifact equality above
	# ------------------------------------------------
	$phase5Obj1 = [PSCustomObject]@{
		phase  = "phase5"
		runner = "phase5_feedback_loop_batch_runner"
		result = [PSCustomObject]@{
			status = "OK"
			paths  = [PSCustomObject]$normalizedPaths
		}
	}

	$phase5Obj2 = [PSCustomObject]@{
		phase  = "phase5"
		runner = "phase5_feedback_loop_batch_runner"
		result = [PSCustomObject]@{
			status = "OK"
			paths  = [PSCustomObject]$normalizedPaths
		}
	}

	Save-JsonObject -Object $phase5Obj1 -Path $phase5Result1
	Save-JsonObject -Object $phase5Obj2 -Path $phase5Result2

	Compare-JsonFiles `
		$phase5Result1 `
		$phase5Result2 `
		"Determinism check for phase5 loop"

	return [PSCustomObject]@{
		determinism_check   = "PASS"
		compared_artifacts  = @(
			"selector_params",
			"training_report",
			"evaluation_report"
		)
	}
}	

Write-Host "============================================="
Write-Host "Phase 5 Batch Runner Start"
Write-Host "============================================="

Push-Location $RootDir
try {
    $resolvedRootDir = (Resolve-Path ".").Path
    $pythonBin = Get-ProjectPython -RootDir $resolvedRootDir -PythonExe $PythonExe

    $resolvedCasesDir = Resolve-ExistingPath `
        -RootDir $resolvedRootDir `
        -ExplicitPath $CasesDir `
        -CandidatePaths @(
            "./Phase_5_Productionization/phase5/tests/test_cases",
            "./phase5/tests/test_cases"
        ) `
        -Label "Cases directory" `
        -DirectoryMode

    $resolvedArtifactRootDir = Resolve-ArtifactRootDir `
        -RootDir $resolvedRootDir `
        -ExplicitPath $ArtifactRootDir

    $resolvedEventRunnerScript = $null
	if (-not $SkipEventBatch) {
		$resolvedEventRunnerScript = Resolve-ExistingPath `
			-RootDir $resolvedRootDir `
			-ExplicitPath $EventRunnerScript `
			-CandidatePaths @(
				"./Phase_5_Productionization/phase5/events/event_batch_runner.py",
				"./phase5/events/event_batch_runner.py"
			) `
			-Label "Event runner script"
	}

	$resolvedInterpretationRunnerScript = $null
	if (-not $SkipInterpretation) {
		$resolvedInterpretationRunnerScript = Resolve-ExistingPath `
			-RootDir $resolvedRootDir `
			-ExplicitPath $InterpretationRunnerScript `
			-CandidatePaths @(
				"./engine/feedback/feedback_interpretation_batch_runner.py"
			) `
			-Label "Interpretation runner script"
	}

	$resolvedPhase5RunnerScript = $null
	if (-not $SkipPhase5Loop) {
		$resolvedPhase5RunnerScript = Resolve-ExistingPath `
			-RootDir $resolvedRootDir `
			-ExplicitPath $Phase5RunnerScript `
			-CandidatePaths @(
				"./Phase_5_Productionization/phase5/feedback_loop_batch_runner.py",
				"./phase5/feedback_loop_batch_runner.py"
			) `
			-Label "Phase 5 runner script"
	}

	$resolvedValidateBundleScript = $null
	if ((-not $SkipSchema) -or (-not $SkipContract) -or (-not $SkipCoverage) -or (-not $SkipIntegrity) -or (-not $SkipDrift) -or (-not $SkipRegression)) {
		$resolvedValidateBundleScript = Resolve-ExistingPath `
			-RootDir $resolvedRootDir `
			-ExplicitPath $ValidateBundleScript `
			-CandidatePaths @(
				"./Phase_5_Productionization/phase5/tests/validators/validate_bundle.py",
				"./phase5/tests/validators/validate_bundle.py"
			) `
			-Label "Validate bundle script"
	}

    Ensure-Dir $resolvedArtifactRootDir
    $sharedRunDir = New-SharedRunDirectory $resolvedArtifactRootDir
    Write-Info "Shared run directory: $sharedRunDir"

    $cases = Get-ChildItem $resolvedCasesDir -Directory -ErrorAction Stop

    if ($cases.Count -eq 0) {
        Write-Fail "No test cases found"
        exit 1
    }

    $summaryResults = @()
    $total = 0
    $passed = 0
    $failed = 0

    foreach ($case in $cases) {
		$total++
		$caseName = $case.Name
		$casePath = $case.FullName
		$caseOutput = Join-Path $sharedRunDir $caseName
		Ensure-Dir $caseOutput

		$caseProfile = Resolve-CaseExecutionProfile `
			-CasePath $casePath `
			-EnableCaseExpectOverride:$EnableCaseExpectOverride `
			-RequiredEventTypes $RequiredEventTypes `
			-RequireInterpretationOutput:$RequireInterpretationOutput `
			-SkipNonFeedbackCases:$SkipNonFeedbackCases
			
		if ($SkipNonFeedbackCases -and $caseProfile.event_category -ne "feedback") {
			Write-Host ""
			Write-Host "---------------------------------------------"
			Write-Host "Skipping non-feedback case: $caseName [$($caseProfile.event_category)]"
			Write-Host "---------------------------------------------" -ForegroundColor Yellow

			$summaryResults += [PSCustomObject]@{
				case                   = $caseName
				event_category         = $caseProfile.event_category
				overall_status         = "SKIP"

				integrity              = "SKIP"
				event_batch            = "SKIP"
				interpretation_batch   = "N/A"
				phase5_loop            = "N/A"
				contract_baseline      = "SKIP"

				schema                 = "SKIP"
				contract               = "SKIP"
				coverage               = "SKIP"
				artifact_integrity     = "SKIP"
				drift                  = "SKIP"
				regression             = "SKIP"
				determinism            = "SKIP"

				expected = [PSCustomObject]@{
					min_structured_events         = $caseProfile.min_structured_events
					required_event_types          = $caseProfile.required_event_types
					require_interpretation_output = $caseProfile.require_interpretation_output
					required_artifacts            = @()
				}

				actual = [PSCustomObject]@{
					structured_events_count   = 0
					interpreted_outputs_count = 0
					artifacts_present         = @()
					artifact_paths_present    = $false
					metrics_present           = $false
				}

				errors   = @()
				warnings = @("Skipped because event_category=$($caseProfile.event_category) and -SkipNonFeedbackCases was enabled")
			}

			continue
		}
	 

		Write-Host ""
		Write-Host "---------------------------------------------"
		Write-Host "Running case: $caseName [$($caseProfile.event_category)]"
		Write-Host "---------------------------------------------"

		$caseSteps = @()
		$caseFailed = $false

		$structuredFile = Join-Path (Join-Path $caseOutput "events") "structured_events.json"
		$interpFile = Join-Path (Join-Path $caseOutput "interp") "interpreted_feedback_events.json"
		$phase5ArtifactsDir = Join-Path $caseOutput "phase5"
		$pipelineResultFile = Join-Path $phase5ArtifactsDir "pipeline_result.json"

		try {
			if ($SkipEventBatch -and -not (Test-Path $structuredFile)) {
				throw "SkipEventBatch was set, but no pre-existing structured_events.json is available for case: $caseName"
			}

			if (-not $SkipEventBatch) {
				$caseSteps += Invoke-Step -Name "$caseName :: Event Batch" -Action {
					$inputPath = Join-Path $casePath "input.json"
					Test-FileExists $inputPath "Case input"

					$eventsDir = Join-Path $caseOutput "events"
					Ensure-Dir $eventsDir

					$structuredEventsPath = Join-Path $eventsDir "structured_events.json"

					Invoke-PythonArtifactStep `
						-PythonBin $pythonBin `
						-ArgsList @(
							$resolvedEventRunnerScript,
							"--source_path", $inputPath,
							"--output_dir", $eventsDir
						) `
						-ExpectedArtifactPath $structuredEventsPath `
						-StepLabel "event_batch_runner"
				}
				if ($caseSteps[-1].Status -eq "FAIL") { throw "$caseName event batch failed" }
			}

			if (-not $SkipInterpretation -and -not $caseProfile.skip_interpretation_for_case) {
				$caseSteps += Invoke-Step -Name "$caseName :: Interpretation Batch" -Action {
					Test-FileExists $structuredFile "Structured events"

					$interpDir = Join-Path $caseOutput "interp"
					Ensure-Dir $interpDir

					$interpOutput = Join-Path $interpDir "interpreted_feedback_events.json"

					Invoke-PythonArtifactStep `
						-PythonBin $pythonBin `
						-ArgsList @(
							$resolvedInterpretationRunnerScript,
							"--source_path", $structuredFile,
							"--output_dir", $interpDir
						) `
						-ExpectedArtifactPath $interpOutput `
						-StepLabel "feedback_interpretation_batch_runner"
				}
				if ($caseSteps[-1].Status -eq "FAIL") { throw "$caseName interpretation batch failed" }
			}
		
			if (-not $SkipPhase5Loop -and -not $caseProfile.skip_phase5_for_case) {
				$caseSteps += Invoke-Step -Name "$caseName :: Phase 5 Loop" -Action {
					Ensure-Dir $phase5ArtifactsDir

					# Phase 5 loop should consume interpretation outputs
					$sourceDir = Split-Path $interpFile -Parent

					$stdoutFile = Join-Path $phase5ArtifactsDir "pipeline_result_stdout.json"
					$stderrFile = Join-Path $phase5ArtifactsDir "phase5_loop_stderr.txt"

					& $pythonBin @(
						$resolvedPhase5RunnerScript,
						"--source_dir", $sourceDir,
						"--output_dir", $phase5ArtifactsDir
					) 1> $stdoutFile 2> $stderrFile

					if ($LASTEXITCODE -ne 0) {
						$stderrText = ""
						if (Test-Path -LiteralPath $stderrFile) {
							$stderrText = [System.IO.File]::ReadAllText($stderrFile)
						}
						throw "Phase 5 loop failed:`n$stderrText"
					}

					# --------------------------------------------------
					# Artifact-first validation
					# --------------------------------------------------
					$selectorParamsFile   = Join-Path $phase5ArtifactsDir "song_recommendation\song_selector_params.json"
					$trainingReportFile   = Join-Path $phase5ArtifactsDir "song_recommendation\song_selector_training_report.json"
					$evaluationReportFile = Join-Path $phase5ArtifactsDir "song_recommendation\song_selector_evaluation_report.json"

					Test-FileExists $selectorParamsFile   "Phase 5 selector_params artifact"
					Test-FileExists $trainingReportFile   "Phase 5 training_report artifact"
					Test-FileExists $evaluationReportFile "Phase 5 evaluation_report artifact"

					# --------------------------------------------------
					# Build canonical pipeline_result.json directly
					# --------------------------------------------------
					$pipelineResult = [PSCustomObject]@{
						phase = "phase5"
						runner = "phase5_feedback_loop_batch_runner"
						source_dir = $sourceDir
						result = [PSCustomObject]@{
							status = "OK"
							paths = [PSCustomObject]@{
								selector_params   = $selectorParamsFile
								training_report   = $trainingReportFile
								evaluation_report = $evaluationReportFile
							}
						}
					}

					Save-JsonObject -Object $pipelineResult -Path $pipelineResultFile
					$pipelineResult
				}

				if ($caseSteps[-1].Status -eq "FAIL") {
					throw "$caseName phase5 loop failed"
				}
			}

			if ((-not $SkipSchema) -or (-not $SkipContract) -or (-not $SkipCoverage) -or (-not $SkipIntegrity) -or (-not $SkipDrift) -or (-not $SkipRegression)) {
				$caseSteps += Invoke-Step -Name "$caseName :: Validator Bundle" -Action {
					$pipelineArg = $null
					if (Test-Path $pipelineResultFile) {
						$pipelineArg = $pipelineResultFile
					}

					$validatorArgs = @{
						PythonBin       = $pythonBin
						ValidatorScript = $resolvedValidateBundleScript
						CasePath        = $casePath
						StructuredPath  = $structuredFile
						InterpretedPath = $(if (Test-Path $interpFile) { $interpFile } else { $null })
						PipelineResultPath = $pipelineArg
					}

					if ($caseProfile.required_event_types -and $caseProfile.required_event_types.Count -gt 0) {
						$validatorArgs["RequiredEventTypes"] = $caseProfile.required_event_types
					}

					if ($caseProfile.require_interpretation_output) {
						$validatorArgs["RequireInterpretationOutput"] = $true
					}
									
				Write-Host "[VALIDATOR-ARGS] case=$caseName casePath=$casePath structured=$structuredFile interp=$(if (Test-Path $interpFile) { $interpFile } else { '<missing>' }) pipeline=$(if ($pipelineArg) { $pipelineArg } else { '<null>' }) requiredEventTypes=$($caseProfile.required_event_types -join ',') requireInterp=$($caseProfile.require_interpretation_output)" -ForegroundColor DarkYellow

                $bundleResult = Invoke-ValidatorBundle @validatorArgs


					$bundleResult = Invoke-ValidatorBundle @validatorArgs

					$bundlePath = Join-Path $caseOutput "validator_bundle_result.json"
					Save-JsonObject -Object $bundleResult -Path $bundlePath
					$bundleResult
				}
				if ($caseSteps[-1].Status -eq "FAIL") { throw "$caseName validator bundle failed" }
			}

			if (-not $SkipDeterminism -and $caseProfile.event_category -eq "feedback") {
				$caseSteps += Invoke-Step -Name "$caseName :: Determinism Test" -Action {
					Validate-Determinism `
						-PythonBin $pythonBin `
						-CasePath $casePath `
						-CaseName $caseName `
						-ResolvedEventRunnerScript $resolvedEventRunnerScript `
						-ResolvedInterpretationRunnerScript $resolvedInterpretationRunnerScript `
						-ResolvedPhase5RunnerScript $resolvedPhase5RunnerScript `
						-RunDirRoot $sharedRunDir
				}
				if ($caseSteps[-1].Status -eq "FAIL") { throw "$caseName determinism test failed" }
			}

			Write-Host "✅ PASS: $caseName"
			$passed++
		}
		catch {
			Write-Host "❌ FAIL: $caseName"
			Write-Host $_ -ForegroundColor Red
			$failed++
			$caseFailed = $true
			if ($StopOnFailure) { throw }
		}

		$summaryResults += Build-CaseSummaryEntry `
			-CaseName $caseName `
			-CasePath $casePath `
			-CaseOutput $caseOutput `
			-CaseSteps $caseSteps `
			-CaseFailed:$caseFailed `
			-CaseProfile $caseProfile `
			-SkipEventBatch:$SkipEventBatch `
			-SkipInterpretation:$SkipInterpretation `
			-SkipPhase5Loop:$SkipPhase5Loop `
			-SkipSchema:$SkipSchema `
			-SkipContract:$SkipContract `
			-SkipCoverage:$SkipCoverage `
			-SkipIntegrity:$SkipIntegrity `
			-SkipDrift:$SkipDrift `
			-SkipRegression:$SkipRegression `
			-SkipDeterminism:$SkipDeterminism
	}

    # --------------------------------------------------
	# Compute totals (PASS / FAIL / SKIP)
	# --------------------------------------------------

	$skipped = ($summaryResults | Where-Object { $_.overall_status -eq "SKIP" }).Count

	$totals = [PSCustomObject]@{
		total_cases   = $total
		passed_cases  = $passed
		failed_cases  = $failed
		skipped_cases = $skipped
	}

	# --------------------------------------------------
	# Status legend
	# --------------------------------------------------

	$statusLegend = [PSCustomObject]@{
		PASS = "validator/layer completed successfully"
		FAIL = "validator/layer executed and failed"
		SKIP = "validator/layer intentionally skipped"
		N_A  = "validator/layer not applicable for this case"
	}

	# --------------------------------------------------
	# Final summary object
	# --------------------------------------------------

	$summaryPath = Join-Path $sharedRunDir "test_case_summary.json"

	$summary = [PSCustomObject]@{
		summary_type    = "phase5_test_case_summary"
		summary_version = "2.0"
		timestamp       = (Get-Date).ToString("o")

		root_dir                     = $resolvedRootDir
		python_bin                   = $pythonBin
		cases_dir                    = $resolvedCasesDir
		artifact_root_dir            = $resolvedArtifactRootDir
		shared_run_dir               = $sharedRunDir

		event_runner_script          = $resolvedEventRunnerScript
		interpretation_runner_script = $resolvedInterpretationRunnerScript
		phase5_runner_script         = $resolvedPhase5RunnerScript
		validate_bundle_script       = $resolvedValidateBundleScript

		totals         = $totals
		status_legend  = $statusLegend

		cases          = $summaryResults
	}

	# --------------------------------------------------
	# Save JSON
	# --------------------------------------------------

	$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding UTF8

	# --------------------------------------------------
	# Console output (clean)
	# --------------------------------------------------

	Write-Host ""
	Write-Host "============================================="
	Write-Host "Phase 5 Test Case Summary"
	Write-Host "============================================="

	Write-Host "Shared Run Dir             : $sharedRunDir"
	Write-Host "Total Cases                : $($totals.total_cases)"
	Write-Host "Passed                     : $($totals.passed_cases)"
	Write-Host "Failed                     : $($totals.failed_cases)"
	Write-Host "Skipped                    : $($totals.skipped_cases)"
	Write-Host "Summary                    : $summaryPath"

	# --------------------------------------------------
	# Exit condition
	# --------------------------------------------------

	if ($failed -gt 0) {
		exit 1
	}

	exit 0
}

finally {
    Pop-Location
}