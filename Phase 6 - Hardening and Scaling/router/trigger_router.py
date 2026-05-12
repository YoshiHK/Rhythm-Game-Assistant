"""
Trigger Router (Phase 6)

Normalizes external execution triggers into a canonical routing context.

This module:
- DOES normalize trigger metadata
- DOES NOT schedule execution
- DOES NOT perform scanning
- DOES NOT evaluate routing decisions
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from .routing_context import RoutingContext

TriggerType = Literal["scheduled", "manual", "external"]


@dataclass(frozen=True)
class TriggerContext:
    """
    Immutable trigger context passed into Phase 6 routing.
    """
    trigger_type: TriggerType
    source: Optional[str] = None


class TriggerRouter:
    """
    Entry point for normalizing external triggers.
    """

    def normalize(self, trigger: TriggerContext, payload: Optional[Dict[str, Any]] = None) -> RoutingContext:
        payload = payload if isinstance(payload, dict) else None

        # Extract only routing metadata (no semantic interpretation)
        mode = None if payload is None else payload.get("mode")
        game_id = None if payload is None else payload.get("game_id")
        locale = None if payload is None else payload.get("locale")
        action = None if payload is None else payload.get("action")
        request_id = None if payload is None else payload.get("request_id")

        return RoutingContext(
            trigger_type=trigger.trigger_type,
            source=trigger.source,
            mode=mode if isinstance(mode, str) else None,
            game_id=game_id if isinstance(game_id, str) else None,
            locale=locale if isinstance(locale, str) else None,
            action=action if isinstance(action, str) else None,
            request_id=request_id if isinstance(request_id, str) else None,
            payload=payload,
        )