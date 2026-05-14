"""
Phase 5 — Song Recommendation Learning

This package implements the **offline learning loop** for
Song Recommendations.

Contract (Non-Negotiable):
- This layer is OFFLINE ONLY.
- No runtime dependencies on Phase 6 routing or selection.
- No gameplay semantics, tips, taxonomy, or severity logic.
- Learning outputs are introduced via deployment only.

Responsibilities:
- Aggregate song recommendation feedback
- Construct selection-level features
- Train and evaluate selector heuristics
- Produce static deployment artifacts

Non-Responsibilities:
- Runtime recommendation selection
- Feedback emission
- Request routing or coordination
- UI or presentation logic

Phase Boundary:
- Consumes forward-only feedback from Phase 6
- Produces static artifacts for deployment
"""

__all__ = [
    # Intentionally left minimal.
    # Submodules define aggregation, features, training, and evaluation.
]