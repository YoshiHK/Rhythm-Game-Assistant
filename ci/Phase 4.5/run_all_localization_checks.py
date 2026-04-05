"""CI Runner: Localization (Phase 4.5) + Downstream Contract Checks

This file owns CI orchestration only.
It does NOT define Phase 7 semantics.

Phase 4.5 checks are run via subprocess in deterministic order.
Phase 7 checks are invoked as import-based tests after Phase 4.5 passes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CHECKS = [
    "check_localization.py",
    "check_template_parity.py",
    "check_placeholder_integrity.py",
    "check_token_parity_per_string.py",
    "check_token_counts.py",
    "check_word_budget.py",
]


def main() -> int:
    """Run Phase 4.5 localization checks."""
    ci_dir = Path(__file__).parent
    python = sys.executable
    for name in CHECKS:
        path = ci_dir / name
        if not path.exists():
            print(f"CI FAIL: missing required check file: {path}")
            return 1
        print(f"
=== Running {name} ===")
        proc = subprocess.run([python, str(path)], check=False)
        if proc.returncode != 0:
            print(f"CI FAIL: {name} returned exit code {proc.returncode}")
            return int(proc.returncode)
    print("
CI PASS: All Phase 4.5 localization checks passed")
    return 0


# -----------------------------
# Phase 7 convenience runners
# -----------------------------

def run_phase7_catalog_presentation_checks() -> None:
    print("Running Phase 7 catalog presentation checks...")
    import ci.test_catalog_presentation  # noqa: F401
    print("✅ Phase 7 catalog presentation checks passed")


def run_phase7_catalog_completeness_checks() -> None:
    print("Running Phase 7 catalog completeness checks...")
    import ci.test_catalog_completeness  # noqa: F401
    print("✅ Phase 7 catalog completeness checks passed")


def run_phase7_recommendation_eligibility_checks() -> None:
    print("Running Phase 7 recommendation eligibility coverage checks...")
    import ci.test_recommendation_eligibility  # noqa: F401
    print("✅ Phase 7 recommendation eligibility coverage passed")


def run_phase7_recommendation_data_readiness_checks() -> None:
    print("Running Phase 7 recommendation eligibility × data readiness checks...")
    import ci.test_recommendation_data_readiness  # noqa: F401
    print("✅ Phase 7 recommendation data readiness passed")


def run_phase7_recommendation_scoring_availability_checks() -> None:
    print("Running Phase 7 recommendation eligibility × scoring availability checks...")
    import ci.test_recommendation_scoring_availability  # noqa: F401
    print("✅ Phase 7 recommendation scoring availability passed")


def run_phase7_recommendation_score_diversity_checks() -> None:
    print("Running Phase 7 recommendation eligibility × score diversity checks...")
    import ci.test_recommendation_score_diversity  # noqa: F401
    print("✅ Phase 7 recommendation score diversity passed")


def run_phase7_recommendation_explainability_coverage_checks() -> None:
    print("Running Phase 7 recommendation explainability coverage checks...")
    import ci.test_recommendation_explainability_coverage  # noqa: F401
    print("✅ Phase 7 recommendation explainability coverage passed")


if __name__ == "__main__":
    code = main()
    if code != 0:
        raise SystemExit(code)

    run_phase7_catalog_presentation_checks()
    run_phase7_catalog_completeness_checks()
    run_phase7_recommendation_eligibility_checks()
    run_phase7_recommendation_data_readiness_checks()
    run_phase7_recommendation_scoring_availability_checks()
    run_phase7_recommendation_score_diversity_checks()
    run_phase7_recommendation_explainability_coverage_checks()
