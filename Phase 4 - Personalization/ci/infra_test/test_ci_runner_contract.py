"""
CI Infrastructure Test — Phase 4 CI Runner Contract (Design-Locked)

Purpose:
- Ensure the Phase 4 CI runner exists at the design-locked location.
- Ensure the runner is executable as an orchestrator (CI-only).
- This does NOT validate correctness of checks/tests (handled elsewhere).
"""

from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    # .../Phase 4 - Personalization/ci/infra_tests -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _phase4_ci_runner_path() -> Path:
    # design-locked per routing skeleton
    return _repo_root() / "Phase 4 - Personalization" / "ci" / "phase_4_ci_runner.py"


def test_phase4_ci_runner_exists():
    p = _phase4_ci_runner_path()
    assert p.exists(), f"Missing Phase 4 CI runner at: {p}"


def test_phase4_ci_runner_is_invokable():
    """
    Runner must be invokable. We do not assert pass/fail here because
    that depends on whether checks/scripts are present in this repo state.
    """
    runner = _phase4_ci_runner_path()
    proc = subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(runner.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    # Must produce some output and exit deterministically.
    assert proc.stdout is not None
    assert len(proc.stdout.strip()) > 0, "Runner produced no output"
    assert proc.returncode in (0, 1, 2), f"Unexpected runner exit code: {proc.returncode}"
    
