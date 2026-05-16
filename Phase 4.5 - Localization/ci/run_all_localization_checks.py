#!/usr/bin/env python3
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
from typing import List, Tuple


def _run(py: str, script: Path, args: List[str]) -> Tuple[int, str]:
    proc = subprocess.run(
        [py, str(script), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, proc.stdout


def _fail(script: Path, code: int, output: str) -> None:
    print(f"CI FAIL: {script.name} (exit_code={code})")
    print(output.rstrip())
    sys.exit(code if code != 0 else 1)


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    checks_dir = ci_dir / "checks"
    py = sys.executable

    # The runner assumes translations root is adjacent to Phase 4.5 folder.
    # Let each check auto-discover if not provided; pass when useful.
    translations_root_candidates = [
        (ci_dir.parent / "translations"),
        Path("Phase 4.5 - Localization") / "translations",
        Path("translations"),
    ]
    translations_root = next((p for p in translations_root_candidates if p.exists()), None)
    common_args: List[str] = []
    if translations_root is not None:
        common_args = ["--translations-root", str(translations_root)]

    # Deterministic order: contract → structure → parity → integrity → budgets
    check_list = [
        "taxonomy_validator.py",
        "check_pack_integrity.py",
        "check_localization.py",
        "check_template_parity.py",
        "check_placeholder_integrity.py",
        "check_debug_consistency.py",
        "check_token_counts.py",
        "check_token_parity_per_string.py",
        "check_word_budget.py",
    ]

    for name in check_list:
        script = checks_dir / name
        if not script.exists():
            _fail(script, 2, f"ERROR: Missing check script: {script}")

        code, out = _run(py, script, common_args)
        if code != 0:
            _fail(script, code, out)
        else:
            # keep logs concise but informative
            print(f"PASS: {name}")

    print("CI PASS: Phase 4.5 localization checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())