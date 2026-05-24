from __future__ import annotations

"""
Declarative Routing Policy for Phase 6.

Defines the final non-semantic decision of whether execution may proceed,
after all guards have been evaluated.
"""

from dataclasses import dataclass
from typing import Optional

from .routing_context import RoutingContext


@dataclass(frozen=True)
class RoutingDecision:
    allowed: bool
    route: Optional[str] = None          # "songs" | "games"
    stop_code: Optional[str] = None      # machine-readable reason
    stop_message: Optional[str] = None   # human-readable reason


class RoutingPolicy:
    """
    Final execution policy (non-semantic).
    """

    def decide(self, ctx: RoutingContext) -> RoutingDecision:
        mode = (ctx.mode or "").strip().lower()

        if mode in ("songs", "games"):
            return RoutingDecision(
                allowed=True,
                route=mode,
                stop_code=None,
                stop_message=None,
            )

        return RoutingDecision(
            allowed=False,
            route=None,
            stop_code=f"unsupported_mode:{mode}",
            stop_message=f"Unsupported mode: {mode}",
        )
