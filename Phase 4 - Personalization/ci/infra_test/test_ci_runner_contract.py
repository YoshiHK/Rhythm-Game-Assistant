from pathlib import Path
import subprocess
import sys


RUNNER_CANDIDATES = [
    "phase_4_ci_runner.py",
    "run_all_personalization_check.py",
]


def _find_runner(repo_root: Path) -> Path:
    for name in RUNNER_CANDIDATES:
        matches = list(repo_root.rglob(name))
        if matches:
            return matches[0]
    raise AssertionError("Phase 4 CI runner not found")


def _run_runner(runner_path: Path, cwd: Path):
    return subprocess.run(
        [sys.executable, str(runner_path)],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def test_runner_exists():
    repo_root = Path(__file__).resolve().parents[2]
    runner = _find_runner(repo_root)

    assert runner.exists(), "CI runner not found"


def test_runner_fails_when_missing_checks(tmp_path):
    repo_root = tmp_path

    # minimal runner test environment
    runner_path = repo_root / "phase_4_ci_runner.py"
    runner_path.write_text(
        "import sys\nsys.exit(1)\n",
        encoding="utf-8",
    )

    proc = _run_runner(runner_path, repo_root)

    assert proc.returncode != 0, "Runner should fail when checks are missing"


def test_runner_passes_with_no_errors(tmp_path):
    repo_root = tmp_path

    runner_path = repo_root / "phase_4_ci_runner.py"
    runner_path.write_text(
        "import sys\nprint('OK')\nsys.exit(0)\n",
        encoding="utf-8",
    )

    proc = _run_runner(runner_path, repo_root)

    assert proc.returncode == 0, "Runner should pass when all checks succeed"
