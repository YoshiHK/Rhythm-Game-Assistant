"""
Phase 4 — CI Layer.

This package enforces Phase 4 invariants:
- Determinism (no semantic drift)
- Safety (non-destructive personalization)
- Explainability (provenance completeness)

CI checks are read-only and must not mutate runtime state.
"""

from .determinism_checks import run_determinism_checks
from .safety_checks import run_safety_checks
from .explainability_checks import run_explainability_checks

__all__ = [
    "run_determinism_checks",
    "run_safety_checks",
    "run_explainability_checks",
]