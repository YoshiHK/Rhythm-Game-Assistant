from __future__ import annotations

"""
Immutable Routing Context for Phase 6.

Single source of truth passed through:
- trigger router
- guards
- routing policy
- lifecycle routers
- observability
- domain dispatch / integration
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RoutingContext:
    # ✅ Primary routing selector
    mode: str

    # ✅ Immutable copy of incoming payload
    payload: Dict[str, Any]

    # ✅ Optional identifiers (non-semantic)
    game_id: Optional[str] = None
    request_id: Optional[str] = None

    # ✅ Trigger (normalized)
    trigger_type: str = "manual"      # scheduled | manual | external
    source: Optional[str] = None      # cli | scheduler | partner | ci