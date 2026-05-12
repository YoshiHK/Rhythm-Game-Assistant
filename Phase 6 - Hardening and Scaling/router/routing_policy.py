"""
Declarative Routing Policy for Phase 6.

Defines the final non-semantic decision of whether execution may proceed,
after all guards have been evaluated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .routing_context import RoutingContext


@dataclass(frozen=True)
class RoutingDecision:
    proceed: bool
    route: Optional[str] = None          # "songs" | "games"
    stop_code: Optional[str] = None      # machine-readable reason
    stop_message: Optional[str] = None   # human-readable reason


class RoutingPolicy:
    """
    Final execution policy.

    This policy MUST remain non-semantic:
    - It only selects the domain route based on context.mode.
    - It does not interpret gameplay, recommendation meaning, or payload internals.
    """

    def decide(self, context: RoutingContext) -> RoutingDecision:
        mode = (context.mode or "").strip().lower()

        if mode == "songs":
            return RoutingDecision(proceed=True, route="songs")
        if mode == "games":
            return RoutingDecision(proceed=True, route="games")

        return RoutingDecision(
            proceed=False,
            route=None,
            stop_code="STOP_UNSUPPORTED_MODE",
            stop_message="Unsupported mode. Expected 'songs' or 'games'.",
        )