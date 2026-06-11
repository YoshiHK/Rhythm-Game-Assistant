param(
    [string]$RepoRoot = ".",
    [string]$DataRoot = "$HOME\OneDrive\Desktop\Rhythm Game Assistant",
    [string]$PythonExe = "python",
    [switch]$SkipVenv,
    [switch]$SkipInstall,
    [switch]$SkipEnv,
    [switch]$SkipOneDriveCheck,
    [switch]$SkipImportSmoke,

    # Offline Learning Validation Mode
    [switch]$OfflineValidationMode,
    [switch]$RunStageProbes,
    [switch]$RunOrchestrator,
    [string]$ValidationOutputRoot = ""
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------
# logging
# --------------------------------------------------
function Write-Info($msg)  { Write-Host "[BOOTSTRAP] $msg" -ForegroundColor Cyan }
function Write-Warn2($msg) { Write-Host "[BOOTSTRAP][WARN] $msg" -ForegroundColor Yellow }
function Write-Ok($msg)    { Write-Host "[BOOTSTRAP][OK] $msg" -ForegroundColor Green }
function Write-Fail($msg)  { Write-Host "[BOOTSTRAP][FAIL] $msg" -ForegroundColor Red }

# --------------------------------------------------
# STRICT native command runner
# --------------------------------------------------
function Invoke-NativeOrThrow {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $false)][string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Native command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

# --------------------------------------------------
# repo / path helpers
# --------------------------------------------------
function Get-ResolvedRepoRoot($RepoRoot) {
    return (Resolve-Path $RepoRoot).Path
}

function Resolve-DataRoot($InputPath, $RepoRoot) {
    if ($InputPath -and (Test-Path $InputPath)) {
        Write-Ok "Using DataRoot: $InputPath"
        return (Resolve-Path $InputPath).Path
    }

    $root = Get-ResolvedRepoRoot $RepoRoot

    $candidates = @(
        "$HOME\OneDrive\Desktop\Rhythm Game Assistant",
        "$HOME\Desktop\Rhythm Game Assistant",
        "$HOME\Documents\Rhythm Game Assistant",
        (Join-Path $root "data"),
        (Join-Path $root "Rhythm Game Assistant")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            Write-Ok "Auto-detected DataRoot: $candidate"
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Data root not found. Checked explicit path and fallbacks. Please pass -DataRoot explicitly."
}

function Resolve-ProjectPython($RepoRoot, $PythonExe) {
    $root = Get-ResolvedRepoRoot $RepoRoot
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"

    if (Test-Path $venvPython) {
        Write-Ok "Using venv python: $venvPython"
        return $venvPython
    }

    Write-Warn2 ".venv python not found; falling back to: $PythonExe"
    return $PythonExe
}

# --------------------------------------------------
# .env helpers
# --------------------------------------------------
function Ensure-EnvTemplate($RepoRoot) {
    $root = Get-ResolvedRepoRoot $RepoRoot
    $envPath = Join-Path $root ".env"
    $templateCandidates = @(
        (Join-Path $root ".env.template"),
        (Join-Path $root ".env.example")
    )

    if (Test-Path $envPath) {
        return
    }

    foreach ($template in $templateCandidates) {
        if (Test-Path $template) {
            Copy-Item $template $envPath
            Write-Warn2 ".env was missing. Created from template: $template"
            return
        }
    }

    Write-Warn2 ".env not found and no template file was found. Continuing without .env."
}

function Load-DotEnv($Path) {
    if (-not (Test-Path $Path)) {
        Write-Warn2 ".env not found at $Path"
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }

        if ($line -match '^\s*([^=]+?)\s*=\s*(.*)\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()

            # strip surrounding double quotes
            if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }

    Write-Ok ".env loaded into current PowerShell process."
}

# --------------------------------------------------
# venv
# --------------------------------------------------
function Ensure-Venv($RepoRoot, $PythonExe) {
    $root = Get-ResolvedRepoRoot $RepoRoot
    $venvPath = Join-Path $root ".venv"

    if (Test-Path $venvPath) {
        Write-Ok "venv exists: $venvPath"
        return $venvPath
    }

    Write-Info "Creating venv..."
    Invoke-NativeOrThrow $PythonExe @("-m", "venv", $venvPath)
    Write-Ok "venv created."
    return $venvPath
}

function Get-VenvPython($VenvPath) {
    $pythonPath = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        throw "venv python not found: $pythonPath"
    }
    return $pythonPath
}

# --------------------------------------------------
# pip install
# --------------------------------------------------
function Install-Requirements($RepoRoot, $PythonBin) {
    $root = Get-ResolvedRepoRoot $RepoRoot
    $req = Join-Path $root "requirements.txt"

    if (-not (Test-Path $req)) {
        Write-Warn2 "No requirements.txt at $req"
        return
    }

    Write-Info "Installing dependencies..."
    Invoke-NativeOrThrow $PythonBin @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-NativeOrThrow $PythonBin @("-m", "pip", "install", "-r", $req)
    Write-Ok "Dependencies installed."
}

# --------------------------------------------------
# Phase 5 path discovery
# --------------------------------------------------
function Get-Phase5Context($RepoRoot) {
    $root = Get-ResolvedRepoRoot $RepoRoot

    $candidates = @(
        @{
            Label       = "Phase_5_Productionization\phase5"
            Phase5Outer = Join-Path $root "Phase_5_Productionization"
            PackageRoot = Join-Path (Join-Path $root "Phase_5_Productionization") "phase5"
        },
        @{
            Label       = "phase5"
            Phase5Outer = $root
            PackageRoot = Join-Path $root "phase5"
        },
        @{
            Label       = "Phase 5 - Productionization"
            Phase5Outer = Join-Path $root "Phase 5 - Productionization"
            PackageRoot = $null
        }
    )

    Write-Host "[BOOTSTRAP][DEBUG] Phase5 candidates:" -ForegroundColor Yellow
    foreach ($c in $candidates) {
        Write-Host ("  Label={0} | Phase5Outer={1} | PackageRoot={2}" -f `
            $c.Label, `
            $c.Phase5Outer, `
            $(if ($c.PackageRoot) { $c.PackageRoot } else { "<null>" }))
    }

    foreach ($c in $candidates) {
        Write-Host ("[BOOTSTRAP][DEBUG] checking: {0}" -f $c.Label) -ForegroundColor Yellow

        $valid = $false
        $resolvedPkg = $null

        # --------------------------------------------------
        # Condition A: legacy phase5-style package root exists
        # --------------------------------------------------
        if ($c.PackageRoot -and (Test-Path -LiteralPath $c.PackageRoot)) {
            $valid = $true
            $resolvedPkg = $c.PackageRoot
        }

        # --------------------------------------------------
        # Condition B: current productionization script layout
        # Must have the Phase 5 runner + tests directory
        # --------------------------------------------------
        $runner     = Join-Path $c.Phase5Outer "feedback_loop_batch_runner.py"
        $testsDir   = Join-Path $c.Phase5Outer "tests"
        $casesDir   = Join-Path $testsDir "test_cases"
        $validators = Join-Path $testsDir "validators"

        if ((Test-Path -LiteralPath $runner) -and
            (Test-Path -LiteralPath $testsDir) -and
            (Test-Path -LiteralPath $casesDir) -and
            (Test-Path -LiteralPath $validators)) {

            $valid = $true

            # For script-based Phase 5, use Phase5Outer as the effective root.
            if (-not $resolvedPkg) {
                $resolvedPkg = $c.Phase5Outer
            }
        }

        if ($valid) {
            return [PSCustomObject]@{
                RepoRoot    = $root
                Phase5Outer = $c.Phase5Outer
                PackageRoot = $resolvedPkg
                Label       = $c.Label
            }
        }
    }

    $checked = $candidates | ForEach-Object {
        $runner   = Join-Path $_.Phase5Outer "feedback_loop_batch_runner.py"
        $testsDir = Join-Path $_.Phase5Outer "tests"
        $pkgText  = if ($_.PackageRoot) { $_.PackageRoot } else { "<null>" }

        "[{0}] Phase5Outer={1}; PackageRoot={2}; Runner={3}; Tests={4}" -f `
            $_.Label, $_.Phase5Outer, $pkgText, $runner, $testsDir
    }

    throw "Could not find valid Phase 5 structure. Checked: $($checked -join '; ')"
}

# --------------------------------------------------
# PYTHONPATH (process-only; portable across PCs)
# --------------------------------------------------
function Set-ProcessPythonPath($RepoRoot) {
    $root = Get-ResolvedRepoRoot $RepoRoot
    $phase5 = Get-Phase5Context $RepoRoot

    $paths = @(
        $root,
        (Join-Path $root "engine"),
        (Join-Path $root "Phase 4 - Personalization"),
        (Join-Path $root "Phase 4.5 - Localization"),
		(Join-Path $root "Phase 5 - Productionization"),
        $phase5.PackageRoot,
        (Join-Path $root "Phase 6 - Hardening and Scaling"),
        (Join-Path $root "Phase 7 - Games Recommendation")
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

    $existing = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
    if ($existing) {
        $paths = @($paths + ($existing -split ';')) |
            Where-Object { $_ -and $_.Trim() -ne "" } |
            Select-Object -Unique
    }

    $joined = [string]::Join(';', $paths)
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $joined, "Process")

    Write-Ok "PYTHONPATH set for current process:"
    Write-Host "  $joined"
}

# --------------------------------------------------
# RGA data validation
# --------------------------------------------------
function Test-RgaPaths($DataRoot) {
    $chartRoot = Join-Path $DataRoot "Chart File"
    $metaRoot  = Join-Path $DataRoot "Tips Output Meta"

    if (-not (Test-Path $chartRoot)) {
        throw "Missing Chart File folder: $chartRoot"
    }

    if (-not (Test-Path $metaRoot)) {
        Write-Warn2 "Creating meta folder: $metaRoot"
        New-Item -ItemType Directory -Force -Path $metaRoot | Out-Null
    }

    Write-Ok "RGA paths OK"
}

# --------------------------------------------------
# sanity checks
# --------------------------------------------------
function Run-SanityChecks($PythonBin) {
    Write-Info "Python sanity check"
    Invoke-NativeOrThrow $PythonBin @("--version")

    try {
        Invoke-NativeOrThrow $PythonBin @("-m", "pip", "show", "fastapi")
        Write-Ok "Core package check passed"
    }
    catch {
        Write-Warn2 "Core package check did not fully pass (fastapi not confirmed). Continuing."
    }
}

# --------------------------------------------------
# import smoke check
# --------------------------------------------------
function Run-ImportSmokeChecks($PythonBin) {
    Write-Info "Running import smoke test"

$code = @"
import importlib

mods = [
    "engine",
    "engine.feedback",
    "song_recommendation",
    "song_recommendation.utils",
]

failed = []
for m in mods:
    try:
        importlib.import_module(m)
        print("[IMPORT][OK]", m)
    except Exception as e:
        print("[IMPORT][FAIL]", m, "->", str(e))
        failed.append(m)

if failed:
    raise SystemExit(1)
"@

    Invoke-NativeOrThrow $PythonBin @("-c", $code)
    Write-Ok "Import smoke passed"
}

# --------------------------------------------------
# Phase 5 offline structure validation
# --------------------------------------------------
function Test-Phase5OfflineStructure($RepoRoot) {

    $phase5 = Get-Phase5Context $RepoRoot

    # ------------------------------------------
    # Resolve effective root (CRITICAL)
    # ------------------------------------------
    $pkg = $phase5.PackageRoot

    if (-not $pkg -or -not (Test-Path -LiteralPath $pkg)) {
        $pkg = $phase5.Phase5Outer
    }

    if (-not $pkg -or -not (Test-Path -LiteralPath $pkg)) {
        throw "Resolved Phase 5 path is invalid."
    }

    # ------------------------------------------
    # Diagnostics
    # ------------------------------------------
    Write-Info "Detected Phase 5 context:"
    Write-Host "  Label       : $($phase5.Label)"
    Write-Host "  Phase5Outer : $($phase5.Phase5Outer)"
    Write-Host "  PackageRoot : $pkg"

    # ------------------------------------------
    # Required structure (productionized layout)
    # ------------------------------------------
    $requiredPaths = @(
        # execution layer
        (Join-Path $pkg "feedback_loop_batch_runner.py"),
        (Join-Path $pkg "event_batch_runner.py"),

        # tests
        (Join-Path $pkg "tests"),
        (Join-Path $pkg "tests\test_cases"),
        (Join-Path $pkg "tests\validators"),

        # core learning modules
        (Join-Path $pkg "song_recommendation"),
        (Join-Path $pkg "song_recommendation\aggregation"),
        (Join-Path $pkg "song_recommendation\aggregation\aggregate_song_feedback.py"),

        (Join-Path $pkg "song_recommendation\features"),
        (Join-Path $pkg "song_recommendation\features\selection_features.py"),

        (Join-Path $pkg "song_recommendation\training"),
        (Join-Path $pkg "song_recommendation\training\train_selector_params.py"),

        (Join-Path $pkg "song_recommendation\evaluation"),
        (Join-Path $pkg "song_recommendation\evaluation\evaluate_selection_quality.py"),

        (Join-Path $pkg "song_recommendation\utils"),
        (Join-Path $pkg "song_recommendation\utils\song_rec_learning_orchestrator.py")
    )

    # ------------------------------------------
    # Optional structure (warn only)
    # ------------------------------------------
    $optionalPaths = @(
        (Join-Path $pkg "song_recommendation\artifacts"),
        (Join-Path $pkg "feedback_aggregation"),
        (Join-Path $pkg "curator_gold"),
        (Join-Path $pkg "offline_retrain"),
        (Join-Path $pkg "observability_experiments"),
        (Join-Path $pkg "practice_integration"),
        (Join-Path $pkg "recommendation"),
        (Join-Path $pkg "marketplace"),
        (Join-Path $pkg "safety")
    )

    # ------------------------------------------
    # Validation
    # ------------------------------------------
    $missingRequired = @()

    foreach ($p in $requiredPaths) {
        if (-not (Test-Path -LiteralPath $p)) {
            $missingRequired += $p
        }
    }

    if ($missingRequired.Count -gt 0) {
        Write-Fail "Phase 5 offline structure validation failed."

        foreach ($m in $missingRequired) {
            Write-Host "  MISSING: $m"
        }

        throw "Required Phase 5 offline structure is incomplete."
    }

    # ------------------------------------------
    # Optional checks
    # ------------------------------------------
    foreach ($opt in $optionalPaths) {
        if (-not (Test-Path -LiteralPath $opt)) {
            Write-Warn2 "Optional Phase 5 path not found: $opt"
        }
    }

    Write-Ok "Phase 5 offline structure validated"

    return [PSCustomObject]@{
        RepoRoot    = $phase5.RepoRoot
        Phase5Outer = $phase5.Phase5Outer
        PackageRoot = $pkg
        Label       = $phase5.Label
    }
}


# --------------------------------------------------
# Validation output path
# --------------------------------------------------
function Get-ValidationOutputDir($DataRoot, $ValidationOutputRoot) {
    if ($ValidationOutputRoot -and $ValidationOutputRoot.Trim() -ne "") {
        $base = $ValidationOutputRoot
    }
    else {
        $base = Join-Path (Join-Path $DataRoot "Tips Output Meta") "offline_validation"
    }

    if (-not (Test-Path $base)) {
        New-Item -ItemType Directory -Force -Path $base | Out-Null
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $dir = Join-Path $base $stamp
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    return $dir
}

# --------------------------------------------------
# Offline Learning Validation Mode
# --------------------------------------------------
function Run-OfflineLearningValidationMode {
    param(
        [string]$RepoRoot,
        [string]$PythonBin,
        [string]$DataRoot,
        [string]$ValidationOutputRoot,
        [switch]$RunStageProbes,
        [switch]$RunOrchestrator
    )

    Write-Info "Starting Offline Learning Validation Mode"

    # --------------------------------------------------
    # Resolve Phase 5 context and effective root
    # --------------------------------------------------
    $phase5 = Test-Phase5OfflineStructure $RepoRoot

    $pkg = $phase5.PackageRoot
    if (-not $pkg -or -not (Test-Path -LiteralPath $pkg)) {
        $pkg = $phase5.Phase5Outer
    }

    if (-not $pkg -or -not (Test-Path -LiteralPath $pkg)) {
        throw "Resolved Phase 5 path is invalid."
    }

    # --------------------------------------------------
    # Output locations
    # --------------------------------------------------
    $outDir = Get-ValidationOutputDir $DataRoot $ValidationOutputRoot
    $reportPath = Join-Path $outDir "offline_validation_report.json"
    $pyPath = Join-Path $outDir "offline_validation_probe.py"

    # --------------------------------------------------
    # Normalize for Python string embedding
    # --------------------------------------------------
    $packageRootPy = ($pkg -replace '\\', '\\\\')
    $reportPathPy  = ($reportPath -replace '\\', '\\\\')

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------
    Write-Info "Detected Phase 5 context:"
    Write-Host "  Label       : $($phase5.Label)"
    Write-Host "  Phase5Outer : $($phase5.Phase5Outer)"
    Write-Host "  PackageRoot : $pkg"

    # --------------------------------------------------
    # Python validation probe
    # --------------------------------------------------
    $py = @"
import importlib
import inspect
import json
import pathlib
import sys
import traceback

PACKAGE_ROOT = pathlib.Path(r"$packageRootPy")
REPORT_PATH = pathlib.Path(r"$reportPathPy")
RUN_STAGE_PROBES = ${RunStageProbes}
RUN_ORCHESTRATOR = ${RunOrchestrator}

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

report = {
    "package_root": str(PACKAGE_ROOT),
    "run_stage_probes": bool(RUN_STAGE_PROBES),
    "run_orchestrator": bool(RUN_ORCHESTRATOR),
    "imports": [],
    "entrypoints": [],
    "executions": [],
    "status": "ok",
    "errors": [],
}

modules = [
    ("aggregation", "song_recommendation.aggregation.aggregate_song_feedback"),
    ("features", "song_recommendation.features.selection_features"),
    ("training", "song_recommendation.training.train_selector_params"),
    ("evaluation", "song_recommendation.evaluation.evaluate_selection_quality"),
    ("orchestrator", "song_recommendation.utils.song_rec_learning_orchestrator"),
]

common_entrypoints = ["main", "run", "orchestrate", "run_pipeline", "cli"]

def can_call_without_required_args(fn):
    try:
        sig = inspect.signature(fn)
    except Exception:
        return False
    for p in sig.parameters.values():
        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD
        ):
            if p.default is inspect._empty:
                return False
    return True

loaded = {}

for kind, mod_name in modules:
    rec = {"kind": kind, "module": mod_name, "ok": False, "error": None}
    try:
        mod = importlib.import_module(mod_name)
        loaded[kind] = mod
        rec["ok"] = True
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        report["status"] = "failed"
        report["errors"].append(f"import failed: {mod_name}: {type(e).__name__}: {e}")
    report["imports"].append(rec)

for kind, mod_name in modules:
    ep = {"kind": kind, "module": mod_name, "entrypoint": None, "callable_without_required_args": False}
    mod = loaded.get(kind)
    if mod is None:
        report["entrypoints"].append(ep)
        continue

    found = None
    callable_ok = False
    for name in common_entrypoints:
        fn = getattr(mod, name, None)
        if callable(fn):
            found = name
            callable_ok = can_call_without_required_args(fn)
            break

    ep["entrypoint"] = found
    ep["callable_without_required_args"] = callable_ok
    report["entrypoints"].append(ep)

def attempt_execute(kind_to_run):
    mod = loaded.get(kind_to_run)
    if mod is None:
        report["executions"].append({
            "kind": kind_to_run,
            "executed": False,
            "reason": "module_not_loaded"
        })
        return

    selected = None
    for x in report["entrypoints"]:
        if x["kind"] == kind_to_run:
            selected = x
            break

    if not selected or not selected["entrypoint"]:
        report["executions"].append({
            "kind": kind_to_run,
            "executed": False,
            "reason": "no_supported_entrypoint_found"
        })
        return

    if not selected["callable_without_required_args"]:
        report["executions"].append({
            "kind": kind_to_run,
            "executed": False,
            "reason": "entrypoint_requires_arguments"
        })
        return

    fn = getattr(mod, selected["entrypoint"])
    try:
        value = fn()
        report["executions"].append({
            "kind": kind_to_run,
            "executed": True,
            "entrypoint": selected["entrypoint"],
            "return_type": None if value is None else type(value).__name__
        })
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
        if code != 0:
            report["status"] = "failed"
            report["errors"].append(f"execution failed: {kind_to_run}: SystemExit({code})")
        report["executions"].append({
            "kind": kind_to_run,
            "executed": True,
            "entrypoint": selected["entrypoint"],
            "system_exit": code
        })
    except Exception as e:
        report["status"] = "failed"
        report["errors"].append(f"execution failed: {kind_to_run}: {type(e).__name__}: {e}")
        report["executions"].append({
            "kind": kind_to_run,
            "executed": True,
            "entrypoint": selected["entrypoint"],
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()
        })

if RUN_STAGE_PROBES:
    for kind in ["aggregation", "features", "training", "evaluation"]:
        attempt_execute(kind)

if RUN_ORCHESTRATOR:
    attempt_execute("orchestrator")

REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print("[VALIDATION] report =", REPORT_PATH)
print("[VALIDATION] status =", report["status"])

if report["status"] != "ok":
    raise SystemExit(1)
"@

    Set-Content -LiteralPath $pyPath -Value $py -Encoding UTF8

    try {
        Invoke-NativeOrThrow $PythonBin @($pyPath)
    }
    catch {
        Write-Fail "Offline Learning Validation Mode failed. A report should still exist if the Python probe got far enough."
        if (Test-Path -LiteralPath $reportPath) {
            Write-Host "Report: $reportPath" -ForegroundColor Yellow
        }
        throw
    }

    Write-Ok "Offline Learning Validation Mode passed."
    Write-Host "Report: $reportPath" -ForegroundColor Green

    try {
        $json = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json

        Write-Host ""
        Write-Host "Validation Summary" -ForegroundColor Cyan
        Write-Host "  Package root       : $($json.package_root)"
        Write-Host "  Stage probes       : $($json.run_stage_probes)"
        Write-Host "  Orchestrator probe : $($json.run_orchestrator)"
        Write-Host "  Imports checked    : $($json.imports.Count)"
        Write-Host "  Executions logged  : $($json.executions.Count)"
        Write-Host "  Final status       : $($json.status)"
    }
    catch {
        Write-Warn2 "Could not parse validation report summary."
    }
}

# --------------------------------------------------
# main
# --------------------------------------------------
$resolvedRepoRoot = Get-ResolvedRepoRoot $RepoRoot
$resolvedDataRoot = Resolve-DataRoot $DataRoot $resolvedRepoRoot

Write-Info "RepoRoot = $resolvedRepoRoot"
Write-Info "DataRoot = $resolvedDataRoot"

if (-not (Test-Path $resolvedRepoRoot)) {
    throw "Repo root missing: $resolvedRepoRoot"
}

if (-not $SkipEnv) {
    Ensure-EnvTemplate $resolvedRepoRoot
    Load-DotEnv (Join-Path $resolvedRepoRoot ".env")
    Set-ProcessPythonPath $resolvedRepoRoot
}

Test-RgaPaths $resolvedDataRoot

$pythonBin = Resolve-ProjectPython $resolvedRepoRoot $PythonExe

if (-not $SkipVenv) {
    $venv = Ensure-Venv $resolvedRepoRoot $PythonExe
    $pythonBin = Get-VenvPython $venv
}

if (-not $SkipInstall) {
    Install-Requirements $resolvedRepoRoot $pythonBin
}

if (-not $SkipOneDriveCheck) {
    Write-Warn2 "OneDrive offline availability must be manually verified."
}

Run-SanityChecks $pythonBin

if (-not $SkipImportSmoke) {
    Run-ImportSmokeChecks $pythonBin
}

if ($OfflineValidationMode) {
    Run-OfflineLearningValidationMode `
        -RepoRoot $resolvedRepoRoot `
        -PythonBin $pythonBin `
        -DataRoot $resolvedDataRoot `
        -ValidationOutputRoot $ValidationOutputRoot `
        -RunStageProbes:$RunStageProbes `
        -RunOrchestrator:$RunOrchestrator
}

Write-Ok "Bootstrap COMPLETE"

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Activate venv (optional): .\.venv\Scripts\Activate.ps1"
Write-Host "  2. Use -OfflineValidationMode to validate Phase 5 offline learning wiring"
Write-Host "  3. Add -RunStageProbes and/or -RunOrchestrator for opt-in execution probes"
Write-Host "  4. Keep Phase 6 as the runtime entry point"
Write-Host "  5. Re-run this bootstrap on another PC without requiring permanent env setup"