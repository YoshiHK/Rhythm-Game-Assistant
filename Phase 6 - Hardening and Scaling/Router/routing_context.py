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

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RoutingContext:
    # Trigger
    trigger_type: str               # scheduled | manual | external
    source: Optional[str] = None    # cli | scheduler | partner | ci

    # Execution payload (opaque to Phase 6)
    payload: Dict[str, Any] = None

    # Scan & ingestion signals
    scan_state_fresh: Optional[bool] = None
    unscanned_candidate_count: Optional[int] = None

    # Security / abuse
    authenticated: Optional[bool] = None
    authorized: Optional[bool] = None
    rate_limited: Optional[bool] = None
    anomalous: Optional[bool] = None

    # Cost & capacity
    estimated_cost: Optional[float] = None
    budget_remaining: Optional[float] = None
    capacity_available: Optional[bool] = None

    # Lifecycle / versioning
    api_version: Optional[str] = None
    model_version: Optional[str] = None
    model_state: Optional[str] = None
    environment: Optional[str] = None
    stage: Optional[str] = None

    # Observability hooks
    metadata: Optional[Dict[str, Any]] = None