"""
Phase 2 Utils Layer

Shared helper utilities for Phase 2 Enhancement.

Hard rules:
- No business logic
- No decision making
- No mutation of payloads
- Safe to remove without changing pipeline behavior
"""

from .taxonomy_helpers import normalize_taxonomy_labels
from .routing_debug import snapshot_routing_state
from .phase2_guards import guard_required_fields

__all__ = [
    "normalize_taxonomy_labels",
    "snapshot_routing_state",
    "guard_required_fields",
]