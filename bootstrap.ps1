param(
    [string]$ProjectRoot = "$HOME\OneDrive\Desktop\Rhythm Game Assistant",
    [string]$PythonExe = "python",
    [switch]$SkipVenv,
    [switch]$SkipInstall,
    [switch]$SkipEnv,
    [switch]$SkipOneDriveCheck
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[BOOTSTRAP] $msg" -ForegroundColor Cyan
}

function Write-Warn2($msg) {
    Write-Host "[BOOTSTRAP][WARN] $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) {
    Write-Host "[BOOTSTRAP][OK] $msg" -ForegroundColor Green
}

function Load-DotEnv($Path) {
    if (-not (Test-Path $Path)) {
        Write-Warn2 ".env not found at $Path ; skipped loading."
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }

        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { return }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }

    Write-Ok "Loaded .env values into current PowerShell process."
}

function Ensure-Venv($ProjectRoot, $PythonExe) {
    $venvPath = Join-Path $ProjectRoot ".venv"

    if (Test-Path $venvPath) {
        Write-Ok "Virtual environment already exists: $venvPath"
        return $venvPath
    }

    Write-Info "Creating virtual environment at $venvPath"
    & $PythonExe -m venv $venvPath
    Write-Ok "Virtual environment created."
    return $venvPath
}

function Get-VenvPython($VenvPath) {
    return Join-Path $VenvPath "Scripts\python.exe"
}

function Install-Requirements($ProjectRoot, $PythonBin) {
    $req = Join-Path $ProjectRoot "requirements.txt"

    if (-not (Test-Path $req)) {
        Write-Warn2 "requirements.txt not found at $req ; skipped pip install."
        return
    }

    Write-Info "Installing Python dependencies from requirements.txt"
    & $PythonBin -m pip install --upgrade pip
    & $PythonBin -m pip install -r $req
    Write-Ok "requirements.txt installed."
}

function Set-ProcessPythonPath($ProjectRoot) {
    $phase4 = Join-Path $ProjectRoot "Phase 4 - Personalization"
    $phase6 = Join-Path $ProjectRoot "Phase 6 - Hardening and Scaling"
    $phase7 = Join-Path $ProjectRoot "Phase 7 - Games Recommendation"

    $parts = @($phase6, $phase7, $phase4) | Where-Object { Test-Path $_ }
    $joined = [string]::Join(';', $parts)

    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $joined, "Process")
    Write-Ok "Set PYTHONPATH for current shell to: $joined"
}

function Test-RgaPaths($ProjectRoot) {
    $chartRoot = Join-Path $ProjectRoot "Chart File"
    $metaRoot  = Join-Path $ProjectRoot "Tips Output Meta"

    if (-not (Test-Path $chartRoot)) {
        throw "Chart root missing: $chartRoot"
    }

    if (-not (Test-Path $metaRoot)) {
        Write-Warn2 "Meta root missing, creating: $metaRoot"
        New-Item -ItemType Directory -Force -Path $metaRoot | Out-Null
    }

    Write-Ok "RGA root paths look present."
}

function Test-OneDriveLocalAvailability($Path) {
    if (-not (Test-Path $Path)) {
        throw "Cannot check OneDrive state; path missing: $Path"
    }

    $sample = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 5

    if (-not $sample) {
        Write-Warn2 "No sample files found under $Path to inspect local availability."
        return
    }

    Write-Info "Sample files for manual OneDrive icon verification:"
    $sample | ForEach-Object { Write-Host "  - $($_.FullName)" }

    Write-Warn2 "Verify these files show a solid green checkmark in File Explorer if you need fully local execution."
}

function Run-SanityChecks($ProjectRoot, $PythonBin) {
    Write-Info "Running minimal sanity checks"
    & $PythonBin --version

    $req = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $req) {
        & $PythonBin -m pip show fastapi uvicorn pydantic | Out-Null
        Write-Ok "Core packages are queryable."
    }
}

# --------------------
# main
# --------------------
Write-Info "ProjectRoot = $ProjectRoot"

if (-not (Test-Path $ProjectRoot)) {
    throw "Project root does not exist: $ProjectRoot"
}

if (-not $SkipEnv) {
    Load-DotEnv (Join-Path $ProjectRoot ".env")
    Set-ProcessPythonPath $ProjectRoot
}

Test-RgaPaths $ProjectRoot

$pythonBin = $PythonExe
if (-not $SkipVenv) {
    $venv = Ensure-Venv $ProjectRoot $PythonExe
    $pythonBin = Get-VenvPython $venv
}

if (-not $SkipInstall) {
    Install-Requirements $ProjectRoot $pythonBin
}

if (-not $SkipOneDriveCheck) {
    Test-OneDriveLocalAvailability (Join-Path $ProjectRoot "Chart File")
}

Run-SanityChecks $ProjectRoot $pythonBin

Write-Ok "Bootstrap complete."
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Activate venv: .\.venv\Scripts\Activate.ps1"
Write-Host "  2. Run file scan workflow from your project root."
Write-Host "  3. Confirm chart files used for local scanning are locally available on this PC."