"""
Phase 2 Summary Layer (Stage 7)

Responsibilities:
- Produce canonical per-chart summaries
- Produce batch-level summaries
- Compute dominance scores deterministically

Hard rules:
- No severity or score inference
- No element selection
- No narrative rendering
- No personalization or locale handling
"""

from .per_chart_summary import build_per_chart_summary
from .batch_summary import build_batch_summary
from .dominance_score import compute_dominance_score

__all__ = [
    "build_per_chart_summary",
    "build_batch_summary",
    "compute_dominance_score",
]