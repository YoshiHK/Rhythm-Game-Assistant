"""
CI Runner — Phase 4 Personalization (Design-Locked)

Purpose:
- Orchestrate Phase 4 CI checks and tests in deterministic order
- Enforce Phase 4 governance boundaries

This runner is CI-only.
It MUST NOT be used as a runtime gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def _run(python: str, path: Path, label: str) -> None:
    print(f"\n=== Phase 4 CI: {label} ===")
    proc = subprocess.run(
        [python, str(path)],
        check=False,
    )
    if proc.returncode != 0:
        fail(f"{label} failed (exit code {proc.returncode})")


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    python = sys.executable

    # ----------------------------
    # Phase 4 CI CHECKS (policy / invariants)
    # ----------------------------
    checks: List[Path] = [
        ci_dir / "checks" / "determinism_checks.py",
        ci_dir / "checks" / "safety_checks.py",
        ci_dir / "checks" / "explainability_checks.py",
    ]

    for chk in checks:
        if not chk.exists():
            fail(f"Missing Phase 4 CI check: {chk.name}")
        _run(python, chk, f"CHECK · {chk.name}")

    # ----------------------------
    # Phase 4 CI TESTS (structural / regression)
    # ----------------------------
    tests: List[Path] = [
        ci_dir / "tests" / "test_deterministic_core_invariants.py",
        ci_dir / "tests" / "test_personalization_decision_schema.py",
        ci_dir / "tests" / "test_safe_adjustment_bounds.py",
        ci_dir / "tests" / "test_fixture_determinism_regression.py",
        ci_dir / "tests" / "test_personalized_fixture_bounds.py",
    ]

    for tst in tests:
        if not tst.exists():
            fail(f"Missing Phase 4 CI test: {tst.name}")
        _run(python, tst, f"TEST  · {tst.name}")

    print("\n✅ CI PASS: All Phase 4 personalization checks and tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
