"""
engine.feedback

Runtime-adjacent feedback interpretation and diagnostics layer.

Purpose:
- Define and expose feedback reasoning system (taxonomy + interpreter)
- Provide bridge to Phase 5 offline learning pipeline
- Offer debugging and tracing utilities

Design Principles:
- Must NOT modify raw feedback events
- Must remain deterministic and side-effect free
- Must NOT implement learning or training logic (belongs to Phase 5)

Submodules:
- taxonomy: reason taxonomy definition
- interpreter: runtime signal → reason codes
- bridge: safe enrichment for Phase 5 aggregation
- diagnostics: debugging / tracing tools
"""

from .taxonomy import reason_taxonomy_v1
from .interpreter import interpret_feedback
from .bridge import enrich_feedback_event

__all__ = [
    "reason_taxonomy_v1",
    "interpret_feedback",
    "enrich_feedback_event",
]