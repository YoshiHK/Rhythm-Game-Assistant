"""
Evaluation Layer – Song Recommendation (Phase 5)

This module exposes deterministic, offline-only evaluation utilities
for measuring learning quality and regression safety.

Structure:
- evaluate_selection_quality:
    Selection-level performance metrics (accept / play / completion, @k, regression guards)

- evaluate_reason_alignment:
    Model vs curator reasoning alignment (agreement rates, mismatch analysis)

Design Principles:
- Offline only (no runtime impact)
- Deterministic outputs
- No semantic inference / mutation of upstream data
- Compatible with Phase 5 routing + dataset pipeline
"""

from .evaluate_selection_quality import (
    evaluate_selection_quality,
    EvalConfig as SelectionEvalConfig,
)

from .evaluate_reason_alignment import (
    evaluate_reason_alignment,
    ReasonAlignmentSummary,
)

__all__ = [
    # Selection performance
    "evaluate_selection_quality",
    "SelectionEvalConfig",

    # Reason alignment
    "evaluate_reason_alignment",
    "ReasonAlignmentSummary",
]