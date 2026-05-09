"""
Phase 2 Narrative Layer (Stage 6 / Track D)

Responsibilities:
- Render final tips text from guidance objects
- Apply spec-driven templates and word budgets
- Perform small, deterministic readability adjustments

Hard rules:
- No severity, score, or selection logic
- No personalization or locale handling
- Deterministic output only
"""

from .narrative_module_v2 import generate_tips_text_v2
from .template_renderer import render_from_template
from .readability_adjuster import adjust_readability

__all__ = [
    "generate_tips_text_v2",
    "render_from_template",
    "adjust_readability",
]