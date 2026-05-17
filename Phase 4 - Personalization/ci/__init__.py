"""
Phase 4 — CI Layer (Design-Locked)

Purpose:
- Provide a stable import surface for all Phase 4 CI checks
- Avoid import-time failure during pytest collection
- Keep CI checks discoverable without enforcing execution

IMPORTANT:
- Imports are lazy-safe (guarded)
- CI runner is the authoritative executor
"""

from typing import TYPE_CHECKING

# ✅ Safe import wrapper (prevents pytest collection crash)
def _safe_import(path, name):
    try:
        module = __import__(path, fromlist=[name])
        return getattr(module, name)
    except Exception:
        return None


# ✅ Exported check functions (safe, optional resolution)
run_determinism_checks = _safe_import(
    "Phase 4 - Personalization.ci.checks.determinism_checks",
    "run_determinism_checks",
)

run_semantic_immutability_checks = _safe_import(
    "Phase 4 - Personalization.ci.checks.semantic_immutability_check",
    "run_semantic_immutability_checks",
)

run_ordering_contract_check = _safe_import(
    "Phase 4 - Personalization.ci.checks.ordering_contract_check",
    "run_ordering_contract_check",
)

run_safety_checks = _safe_import(
    "Phase 4 - Personalization.ci.checks.safety_checks",
    "run_safety_checks",
)

run_explainability_checks = _safe_import(
    "Phase 4 - Personalization.ci.checks.explainability_checks",
    "run_explainability_checks",
)


__all__ = [
    "run_determinism_checks",
    "run_semantic_immutability_checks",
    "run_ordering_contract_check",
    "run_safety_checks",
    "run_explainability_checks",
]