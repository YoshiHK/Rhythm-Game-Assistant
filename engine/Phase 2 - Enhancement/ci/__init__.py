"""
Phase 2 CI Layer

Provides non-invasive validation and guard checks for
Phase 2 Enhancement pipeline.

Hard rules:
- CI must never modify runtime data
- CI must never affect control flow
- CI must be safe to disable
"""

from .determinism_checks import check_determinism
from .schema_alignment_checks import check_schema_alignment
from .non_destructive_checks import check_non_destructive

__all__ = [
    "check_determinism",
    "check_schema_alignment",
    "check_non_destructive",
]