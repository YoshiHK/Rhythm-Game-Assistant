"""
Immutable routing context for Phase 6.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class RoutingContext:
    source: str
    payload: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    security_context: Dict[str, Any]
    environment: str
