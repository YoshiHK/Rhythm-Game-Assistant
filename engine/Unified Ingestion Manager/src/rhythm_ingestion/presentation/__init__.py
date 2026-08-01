# presentation/__init__.py
"""
Presentation helpers for Phase 3 (UI-facing metadata only).

This module aggregates presentation-layer utilities such as:
- Status / capability badge mappings
- Game capability panel helpers (UI-ready payloads)

Notes
-----
- Wiring / presentation only.
- Does NOT perform ingestion, validation, or tips generation.
- Safe to import from API, UI, CLI, and admin tools.
"""

# Badge mappings
from .badges import (
    STATUS_BADGES,
    CAPABILITY_BADGES,
    get_status_badge,
    get_capability_badge,
)

# Game panel helpers
from .game_panels import (
    use_game_badges,
)

__all__ = [
    # Badge constants
    "STATUS_BADGES",
    "CAPABILITY_BADGES",

    # Badge helpers
    "get_status_badge",
    "get_capability_badge",

    # UI panel helpers
    "use_game_badges",
]