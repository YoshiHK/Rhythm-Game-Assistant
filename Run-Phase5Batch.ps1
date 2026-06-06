# ------------------------------------------------------------
# Phase 5 Batch Runner (Offline)
# ------------------------------------------------------------

param (
    [string]$RootDir = ".",
    [string]$CasesDir = "./phase5/tests/test_cases",
    [string]$OutputDir = "./phase5/tests/output"
)

Write-Host "============================================="
Write-Host "Phase 5 Batch Runner Start"
Write-Host "============================================="

# Create output dir
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$cases = Get-ChildItem $CasesDir -Directory

if ($cases.Count -eq 0) {
    Write-Host "❌ No test cases found"
    exit 1
}

$total = 0
$passed = 0
$failed = 0

foreach ($case in $cases) {

    $total++
    $caseName = $case.Name
    $casePath = $case.FullName

    Write-Host ""
    Write-Host "---------------------------------------------"
    Write-Host "Running case:" $caseName
    Write-Host "---------------------------------------------"

    try {

        # -------------------------
        # Step 1 — Event batch
        # -------------------------
        $eventOutput = Join-Path $OutputDir "$caseName-events"

        python phase5/events/event_batch_runner.py `
            --source_path "$casePath/input.json" `
            --output_dir "$eventOutput"

        if ($LASTEXITCODE -ne 0) {
            throw "Event batch failed"
        }

        # -------------------------
        # Step 2 — Interpretation
        # -------------------------
        $interpInput = Join-Path $eventOutput "structured_events.json"
        $interpOutput = Join-Path $OutputDir "$caseName-interp"

        python engine/feedback/feedback_interpretation_batch_runner.py `
            --source_path "$interpInput" `
            --output_dir "$interpOutput"

        if ($LASTEXITCODE -ne 0) {
            throw "Interpretation batch failed"
        }

        # -------------------------
        # Step 3 — Phase 5 loop
        # -------------------------
        python phase5/phase5_feedback_loop_batch_runner.py `
            --source_dir "$casePath"

        if ($LASTEXITCODE -ne 0) {
            throw "Phase 5 pipeline failed"
        }

        Write-Host "✅ PASS:" $caseName
        $passed++

    } catch {
        Write-Host "❌ FAIL:" $caseName
        Write-Host $_
        $failed++
    }
}

Write-Host ""
Write-Host "============================================="
Write-Host "Phase 5 Batch Summary"
Write-Host "============================================="
Write-Host "Total :" $total
Write-Host "Passed:" $passed
Write-Host "Failed:" $failed

if ($failed -gt 0) {
    exit 1
}
exit 0
