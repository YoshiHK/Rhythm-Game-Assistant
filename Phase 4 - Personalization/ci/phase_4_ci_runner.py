from pathlib import Path
import sys
import subprocess
import json


def fail(msg: str) -> None:
    """
    CI hard failure helper.
    """
    print(f"[Phase4 CI] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _run(python: str, path: Path, label: str) -> None:
    """
    Execute a CI check script deterministically.
    """
    if not path.exists():
        fail(f"{label} check missing: {path.name}")

    result = subprocess.run(
        [python, str(path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        fail(f"{label} check failed")

    print(f"[Phase4 CI] PASS: {label}")


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    python = sys.executable

    checks_dir = ci_dir / "checks"

    required = [
        "determinism_checks.py",
        "semantic_immutability_check.py",
        "ordering_contract_check.py",
        "safety_checks.py",
        "explainability_checks.py",
    ]

    # --------------------------------------------------------
    # Validate required files exist
    # --------------------------------------------------------
    for name in required:
        path = checks_dir / name
        if not path.exists():
            fail(f"Missing required CI check: {name}")

    # --------------------------------------------------------
    # Deterministic execution order (IMPORTANT for CI invariants)
    # --------------------------------------------------------
    _run(python, checks_dir / "determinism_checks.py", "determinism")
    _run(python, checks_dir / "semantic_immutability_check.py", "immutability")
    _run(python, checks_dir / "ordering_contract_check.py", "ordering")
    _run(python, checks_dir / "safety_checks.py", "safety")
    _run(python, checks_dir / "explainability_checks.py", "explainability")

    print(json.dumps({
        "status": "ok",
        "phase": "phase4",
        "runner": "ci"
    }))

    return 0


if __name__ == "__main__":
    main()
