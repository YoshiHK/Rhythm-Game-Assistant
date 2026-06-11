"""
Phase 5 — Song Recommendation Learning
Evaluation Layer (Offline Only)

This package evaluates selection-quality changes using safe, selection-level metrics.

Contract (Non-Negotiable) — per PHASE_5_SONG_RECOMMENDATION_LEARNING_SPEC:
- Offline only (Phase 5).
- Deterministic and auditable.
- No gameplay semantics (tips/taxonomy/severity/narrative/localization content).
- Produces evaluation reports and regression guard outcomes.
- No runtime dependencies; no direct runtime feedback loop.

See README.md for boundaries and invariants.
"""

from .evaluate_selection_quality import (
    EvalConfig,
    EvalReport,
    evaluate_selection_quality,
)

__all__ = [
    "EvalConfig",
    "EvalReport",
    "evaluate_selection_quality",
]