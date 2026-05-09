"""
Phase 2 Guidance Layer (Stage 5.3 / Track C)

Responsibilities:
- Fill guidance fields for selected analysed elements
- Resolve dominant difficulty causes from taxonomy signals
- Format chart breakdown explanations deterministically

Hard rules:
- No severity or score modification
- No element selection logic
- No narrative rendering
- No personalization or locale handling
"""

from .guidance_engine_v2 import fill_guidance_for_elements_v2
from .cause_resolver import resolve_difficulty_causes
from .breakdown_formatter import format_chart_breakdown

__all__ = [
    "fill_guidance_for_elements_v2",
    "resolve_difficulty_causes",
    "format_chart_breakdown",
]