"""
CI Runner: Phase 4.5 Localization Checks

Purpose:
- Orchestrate Phase 4.5 localization CI checks in deterministic order
- Enforce structural and policy contracts for localization

Non-goals:
- Runtime execution
- Translation quality evaluation
- Phase 7 checks
- Observability scraping (handled elsewhere)

This runner is CI-only and MUST NOT be used as a runtime gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    python = sys.executable

    checks: List[str] = [
        # Structural / contract checks (order matters)
        "check_localization.py",
        "check_template_parity.py",
        "check_placeholder_integrity.py",

        # Token & budget policy checks
        "check_token_parity_per_string.py",
        "check_token_counts.py",
        "check_word_budget.py",
    ]

    for name in checks:
        path = ci_dir / name
        if not path.exists():
            fail(f"Missing required Phase 4.5 check file: {name}")

        print(f"\n=== Running Phase 4.5 check: {name} ===")
        proc = subprocess.run(
            [python, str(path)],
            check=False,
        )

        if proc.returncode != 0:
            fail(f"Check failed: {name} (exit code {proc.returncode})")

    print("\n✅ CI PASS: All Phase 4.5 localization checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())