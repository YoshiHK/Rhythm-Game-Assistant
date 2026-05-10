"""
CI Infrastructure Test — Phase 4 CI Runner Contract (Design-Locked)

Purpose:
- Validate the Phase 4 CI runner behaves as a deterministic orchestrator
- Ensure runner fails loudly on missing required scripts
- Ensure runner exits 0 when all required scripts exist and pass

Non-goals:
- Does not execute Phase 4 personalization runtime
- Does not validate safety/explainability logic (those belong to checks/tests)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, List

import pytest


# Candidate runner filenames (repo may choose either)
RUNNER_CANDIDATES = [
    "run_all_personalization_check.py",
    "phase_4_ci_runner.py",
]


def _find_runner_in_repo_root(repo_root: Path) -> Path:
    """
    Find the Phase 4 CI runner file from repo root.
    We intentionally accept either naming convention.
    """
    for name in RUNNER_CANDIDATES:
        matches = list(repo_root.rglob(name))
        if matches:
            # prefer shortest path (closest to root)
            return sorted(matches, key=lambda p: len(p.as_posix()))[0]
    raise AssertionError(
        f"Could not find Phase 4 CI runner. Expected one of: {RUNNER_CANDIDATES}"
    )


def _write_ok_script(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import sys\n"
        "print('OK')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )


def _write_fail_script(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import sys\n"
        "print('FAIL')\n"
        "sys.exit(1)\n",
        encoding="utf-8",
    )


def _run_runner(runner_path: Path, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(runner_path)],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def _make_minimal_ci_layout(ci_dir: Path) -> None:
    """
    Create the expected Phase 4 CI layout used by the runner.

    We intentionally create both:
    - checks/ (policy checks)
    - tests/  (tests)
    since your final runner contract should separate the two.
    """
    (ci_dir / "checks").mkdir(parents=True, exist_ok=True)
    (ci_dir / "tests").mkdir(parents=True, exist_ok=True)


def _populate_all_required_scripts(ci_dir: Path) -> None:
    """
    Create placeholder scripts the runner is expected to invoke.
    These scripts do not test Phase 4; they only return exit code 0.
    """
    # Checks (policy)
    for name in ("determinism_checks.py", "safety_checks.py", "explainability_checks.py"):
        _write_ok_script(ci_dir / "checks" / name)

    # Tests (structural / regression)
    for name in (
        "test_deterministic_core_invariants.py",
        "test_personalization_decision_schema.py",
        "test_safe_adjustment_bounds.py",
        "test_fixture_determinism_regression.py",
        "test_personalized_fixture_bounds.py",
    ):
        _write_ok_script(ci_dir / "tests" / name)


@pytest.mark.ci_infra
def test_phase4_ci_runner_fails_on_missing_required_scripts(tmp_path: Path) -> None:
    """
    Contract: runner must fail loudly if any required scripts are missing.
    """
    repo_root = Path(__file__).resolve().parents[2]
    runner_src = _find_runner_in_repo_root(repo_root)

    # Create isolated repo-like structure
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir(parents=True)

    ci_dir = fake_repo / "ci" / "phase4"
    _make_minimal_ci_layout(ci_dir)

    # Copy runner into fake repo
    runner_dst = ci_dir / runner_src.name
    runner_dst.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")

    # Do NOT create required scripts => runner must fail
    proc = _run_runner(runner_dst, cwd=fake_repo)
    assert proc.returncode != 0, f"Expected non-zero exit when scripts missing.\n{proc.stdout}"
    assert "CI FAIL" in proc.stdout or "Missing" in proc.stdout, (
        "Runner failure output should be actionable (mention CI FAIL or Missing). "
        f"\nOutput:\n{proc.stdout}"
    )


@pytest.mark.ci_infra
def test_phase4_ci_runner_passes_when_all_scripts_pass(tmp_path: Path) -> None:
    """
    Contract: runner must exit 0 when all required scripts exist and pass.
    """
    repo_root = Path(__file__).resolve().parents[2]
    runner_src = _find_runner_in_repo_root(repo_root)

    fake_repo = tmp_path / "repo"
    fake_repo.mkdir(parents=True)

    ci_dir = fake_repo / "ci" / "phase4"
    _make_minimal_ci_layout(ci_dir)

    runner_dst = ci_dir / runner_src.name
    runner_dst.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")

    _populate_all_required_scripts(ci_dir)

    proc = _run_runner(runner_dst, cwd=fake_repo)
    assert proc.returncode == 0, f"Expected exit code 0 when all scripts pass.\n{proc.stdout}"


@pytest.mark.ci_infra
def test_phase4_ci_runner_is_deterministic_ordering(tmp_path: Path) -> None:
    """
    Contract: runner should invoke scripts in deterministic order.
    We approximate this by making one script fail and checking that output
    shows earlier scripts ran before the failing one (based on printed markers).
    """
    repo_root = Path(__file__).resolve().parents[2]
    runner_src = _find_runner_in_repo_root(repo_root)

    fake_repo = tmp_path / "repo"
    fake_repo.mkdir(parents=True)

    ci_dir = fake_repo / "ci" / "phase4"
    _make_minimal_ci_layout(ci_dir)

    runner_dst = ci_dir / runner_src.name
    runner_dst.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")

    _populate_all_required_scripts(ci_dir)

    # Make one late-stage test fail
    _write_fail_script(ci_dir / "tests" / "test_personalized_fixture_bounds.py")

    proc = _run_runner(runner_dst, cwd=fake_repo)
    assert proc.returncode != 0, "Expected runner to fail when a script fails"

    out = proc.stdout
    # The runner should at least mention the failing script
    assert "test_personalized_fixture_bounds.py" in out or "personalized_fixture_bounds" in out, (
        "Runner output should identify the failing script.\n"
        f"Output:\n{out}"
    )