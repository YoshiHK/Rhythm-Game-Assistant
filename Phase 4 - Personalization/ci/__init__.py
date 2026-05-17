"""
Phase 4 — CI Layer.

This package enforces Phase 4 invariants (CI-only, NON-RUNTIME):
- Determinism (identical inputs -> identical outputs)
- Semantic immutability (no semantic drift from Phase 1–3 outputs)
- Ordering contract (Spec §7.3 ordering consistency)
- Safety (bounded, non-destructive personalization)
- Explainability (provenance completeness + decision chain)

CI checks are read-only and MUST NOT mutate runtime state.
"""

from .checks.determinism_checks import run_determinism_checks
from .checks.semantic_immutability_check import run_semantic_immutability_checks
from .checks.ordering_contract_check import run_ordering_contract_check
from .checks.safety_checks import run_safety_checks
from .checks.explainability_checks import run_explainability_checks

__all__ = [
    "run_determinism_checks",
    "run_semantic_immutability_checks",
    "run_ordering_contract_check",
    "run_safety_checks",
    "run_explainability_checks",
]