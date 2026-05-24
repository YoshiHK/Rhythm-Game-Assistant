from __future__ import annotations

"""
Trigger Router (Phase 6)

Normalizes external execution triggers into a canonical routing context.

This module:
- DOES normalize trigger metadata
- DOES NOT schedule execution
- DOES NOT evaluate routing decisions
"""

from dataclasses import dataclass
from typing import Literal, Optional

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
    CI-safe default behavior is pass-through.
    """

    def apply(self, ctx: RoutingContext, trig: Optional[TriggerContext] = None) -> RoutingContext:
        if trig is None:
            return ctx
        # return a new RoutingContext (immutable) with trigger fields populated
        return RoutingContext(
            mode=ctx.mode,
            payload=ctx.payload,
            game_id=ctx.game_id,
            request_id=ctx.request_id,
            trigger_type=trig.trigger_type,
            source=trig.source or ctx.source,
        )