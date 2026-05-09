"""
Phase 2 Selection Layer (Stage 5.2 / Track B)

Responsibilities:
- Select elements for tips from analysed elements (post Stage 5.1)
- Enforce target counts by difficulty
- Apply dominance-aware ranking, diversity, and stable tie-breaks

Hard rules:
- Deterministic
- No severity inference, no guidance filling, no narrative rendering
- Does not modify Phase 1 semantics (Phase 2 is additive/enhancement only)
"""

from .selector_v2_bridge import select_elements_for_tips
from .dominance_ranker import rank_by_dominance
from .diversity_rules import apply_diversity_constraints

__all__ = [
    "select_elements_for_tips",
    "rank_by_dominance",
    "apply_diversity_constraints",
]