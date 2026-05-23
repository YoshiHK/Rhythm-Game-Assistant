"""
Phase 7 — Routing Layer

Flat exports for Phase 7 routing.

This package exposes the **only runtime entrypoint**
for Phase 7 recommendations and the minimal structures
required to coordinate routing.

Design invariants:
- Routing is a coordinator only.
- No ranking, learning, or eligibility logic lives here.
- No runtime version switching is permitted.
"""

from routing.routing_context import Phase7RoutingContext
from routing.routing_policy import Phase7RoutingPolicy
from routing.router import Phase7Router

__all__ = [
    "Phase7RoutingContext",
    "Phase7RoutingPolicy",
    "Phase7Router",
]