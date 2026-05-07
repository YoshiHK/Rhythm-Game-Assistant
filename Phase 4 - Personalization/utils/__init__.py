"""
Phase 4 — Utils Layer (pure helpers).

This package contains small, reusable helper utilities used across Phase 4:
- provenance construction helpers
- debug / inspection helpers

Hard rules:
- No IO side-effects
- No business logic
- No mutation of Phase 1–3 artifacts
- Safe to import from any Phase 4 sub-layer
"""

from .provenance_builder import (
    build_base_provenance,
    merge_adjustment_provenance,
)
from .debug_helpers import (
    summarize_adjustments,
    safe_repr,
)

__all__ = [
    # provenance helpers
    "build_base_provenance",
    "merge_adjustment_provenance",
    # debug helpers
    "summarize_adjustments",
    "safe_repr",
]