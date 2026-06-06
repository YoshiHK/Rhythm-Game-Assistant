param(
    [string]$ProjectRoot = ".",
    [switch]$SkipBootstrap,
    [switch]$SkipPhase5,
    [switch]$SkipEngineFeedback,
    [switch]$StopOnFailure,
    [string]$BootstrapScript = ".\bootstrap.ps1",
    [string]$Phase5BatchScript = ".\phase5\tests\Run-Phase5Batch.ps1",
    [string]$OutputDir = ".\repo_smoke_output"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[REPO-SMOKE] $msg" -ForegroundColor Cyan
}

function Write-Warn2($msg) {
    Write-Host "[REPO-SMOKE][WARN] $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) {
    Write-Host "[REPO-SMOKE][OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "[REPO-SMOKE][FAIL] $msg" -ForegroundColor Red
}

function Ensure-Dir($Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
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

        if ($StopOnFailure) {
            throw
        }

        return [PSCustomObject]@{
            Name   = $Name
            Status = "FAIL"
            Error  = $_.Exception.Message
        }
    }
}

function Test-FileExists($Path, $Label) {
    if (-not (Test-Path $Path)) {
        throw "$Label not found: $Path"
    }
}

function Run-BootstrapStep($ProjectRoot, $BootstrapScript) {
    Test-FileExists $BootstrapScript "Bootstrap script"

    & $BootstrapScript `
        -ProjectRoot $ProjectRoot `
        -SkipInstall `
        -SkipOneDriveCheck

    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap.ps1 returned non-zero exit code: $LASTEXITCODE"
    }
}

function Run-EngineFeedbackImportSmoke($OutputDir) {
    $code = @"
import importlib

mods = [
    "engine",
    "engine.feedback",
]

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
"@

    $outFile = Join-Path $OutputDir "engine_feedback_import_smoke.txt"

    python -c $code | Tee-Object -FilePath $outFile

    if ($LASTEXITCODE -ne 0) {
        throw "engine/feedback import smoke failed"
    }
}

function Run-Phase5BatchStep($Phase5BatchScript) {
    Test-FileExists $Phase5BatchScript "Phase 5 batch script"

    & $Phase5BatchScript

    if ($LASTEXITCODE -ne 0) {
        throw "Run-Phase5Batch.ps1 returned non-zero exit code: $LASTEXITCODE"
    }
}

# --------------------
# Main
# --------------------
Push-Location $ProjectRoot
try {
    Ensure-Dir $OutputDir

    $results = @()

    if (-not $SkipBootstrap) {
        $results += Invoke-Step -Name "Bootstrap" -Action {
            Run-BootstrapStep -ProjectRoot $ProjectRoot -BootstrapScript $BootstrapScript
        }
    }
    else {
        Write-Warn2 "Skipping bootstrap step"
    }

    if (-not $SkipEngineFeedback) {
        $results += Invoke-Step -Name "Engine/Feedback Import Smoke" -Action {
            Run-EngineFeedbackImportSmoke -OutputDir $OutputDir
        }
    }
    else {
        Write-Warn2 "Skipping engine/feedback import smoke"
    }

    if (-not $SkipPhase5) {
        $results += Invoke-Step -Name "Phase 5 Batch" -Action {
            Run-Phase5BatchStep -Phase5BatchScript $Phase5BatchScript
        }
    }
    else {
        Write-Warn2 "Skipping Phase 5 batch step"
    }

    $summaryPath = Join-Path $OutputDir "repo_smoke_summary.json"

    $summary = [PSCustomObject]@{
        project_root = (Resolve-Path ".").Path
        timestamp    = (Get-Date).ToString("o")
        results      = $results
        passed       = @($results | Where-Object { $_.Status -eq "PASS" }).Count
        failed       = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
    }

    $summary | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryPath -Encoding UTF8

    Write-Host ""
    Write-Host "============================================="
    Write-Host "Repo Smoke Summary"
    Write-Host "============================================="
    Write-Host "Passed: $($summary.passed)"
    Write-Host "Failed: $($summary.failed)"
    Write-Host "Summary: $summaryPath"

    if ($summary.failed -gt 0) {
        exit 1
    }

    exit 0
}
finally {
    Pop-Location
}