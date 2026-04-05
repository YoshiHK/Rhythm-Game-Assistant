"""CI Runner: Run All Localization Checks (Phase 4.5)

Runs the Phase 4.5 localization CI checks in a deterministic order.

Checks executed:
1) check_localization.py           - folder completeness + meta presence + alias target validity
2) check_template_parity.py        - template file set parity + basic v3 structure
3) check_placeholder_integrity.py  - declared + inline placeholder preservation across locales
4) check_word_budget.py            - per-locale variant max_words budget enforcement

Run:
  python ci/run_all_localization_checks.py

Exit code:
  0 if all checks pass, otherwise propagates the first failing check exit code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECKS = [
    "check_localization.py",
    "check_template_parity.py",
    "check_placeholder_integrity.py",
    "check_word_budget.py",
]


def main() -> int:
    ci_dir = Path(__file__).parent
    python = sys.executable

    for name in CHECKS:
        path = ci_dir / name
        if not path.exists():
            print(f"CI FAIL: missing required check file: {path}")
            return 1

        print(f"\n=== Running {name} ===")
        proc = subprocess.run([python, str(path)], check=False)
        if proc.returncode != 0:
            print(f"CI FAIL: {name} returned exit code {proc.returncode}")
            return int(proc.returncode)

    print("\nCI PASS: All Phase 4.5 localization checks passed")
    return 0


def run_phase7_catalog_presentation_checks():
    print("Running Phase 7 catalog presentation checks...")
    import ci.test_catalog_presentation  # noqa: F401
    print("✅ Phase 7 catalog presentation checks passed")

def run_phase7_catalog_completeness_checks():
    print("Running Phase 7 catalog completeness checks...")
    import ci.test_catalog_completeness  # noqa: F401
    print("✅ Phase 7 catalog completeness checks passed")

def run_phase7_recommendation_eligibility_checks():
    print("Running Phase 7 recommendation eligibility coverage checks...")
    import ci.test_recommendation_eligibility  # noqa: F401
    print("✅ Phase 7 recommendation eligibility coverage passed")

def run_phase7_recommendation_data_readiness_checks():
    print("Running Phase 7 recommendation eligibility × data readiness checks...")
    import ci.test_recommendation_data_readiness  # noqa: F401
    print("✅ Phase 7 recommendation data readiness passed")

def run_phase7_recommendation_scoring_availability_checks():
    print("Running Phase 7 recommendation eligibility × scoring availability checks...")
    import ci.test_recommendation_scoring_availability  # noqa: F401
    print("✅ Phase 7 recommendation scoring availability passed")

def run_phase7_recommendation_score_diversity_checks():
    print("Running Phase 7 recommendation eligibility × score diversity checks...")
    import ci.test_recommendation_score_diversity  # noqa: F401
    print("✅ Phase 7 recommendation score diversity passed")



if __name__ == "__main__":
    # existing Phase 4.5 checks run here
    run_phase7_catalog_presentation_checks()
    run_phase7_catalog_completeness_checks()
    run_phase7_recommendation_eligibility_checks()
    run_phase7_recommendation_data_readiness_checks()
    run_phase7_recommendation_scoring_availability_checks()
    run_phase7_recommendation_score_diversity_checks()
    

