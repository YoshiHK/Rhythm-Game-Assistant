"""CI Runner: Phase 4 Personalization Checks

Runs Phase 4 CI checks in deterministic order.

Run:
  python ci/phase4/run_all_personalization_check.py

Exit code:
  0 if all checks pass, otherwise first failing check's exit code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECKS = [
    'test_deterministic_core_invariants.py',
    'test_personalization_decision_schema.py',
    'test_safe_adjustment_bounds.py',
    'test_event_logging_contract.py',
]


def main() -> int:
    here = Path(__file__).parent
    py = sys.executable

    for name in CHECKS:
        p = here / name
        if not p.exists():
            print(f"CI FAIL: missing check file: {p}")
            return 1

        print(f"\n=== Running {name} ===")
        proc = subprocess.run([py, str(p)], check=False)
        if proc.returncode != 0:
            print(f"CI FAIL: {name} returned exit code {proc.returncode}")
            return int(proc.returncode)

    print("\nCI PASS: All Phase 4 personalization checks passed")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
