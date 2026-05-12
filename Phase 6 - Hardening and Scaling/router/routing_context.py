"""
Immutable Routing Context for Phase 6.

This context is the single source of truth passed through:
- trigger router
- guards
- routing policy
- lifecycle routers
- observability
- integration
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RoutingContext:
    # Trigger (normalized)
    trigger_type: str                 # scheduled | manual | external
    source: Optional[str] = None      # cli | scheduler | partner | ci

    # Dispatch (non-semantic)
    mode: Optional[str] = None        # songs | games (opaque routing signal)

    # Request envelope (opaque)
    request_id: Optional[str] = None
    game_id: Optional[str] = None
    locale: Optional[str] = None
    action: Optional[str] = None      # refresh | save (policy signal)

    # Raw payload preserved as-is (router must not interpret)
    payload: Optional[Dict[str, Any]] = None
