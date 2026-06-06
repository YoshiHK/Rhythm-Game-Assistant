"""
Phase 5 — Recommendation Layer

This package defines structured request / response builders for recommendations.

Primary contracts:
- recommendation_request.schema.json
- recommendation_response.schema.json

Role:
- Normalize recommendation request inputs
- Normalize structured recommendation responses
- Preserve provenance and model traceability
- Support downstream UI, telemetry, and feedback capture

Boundary:
- Does NOT train models
- Does NOT evaluate performance
- Does NOT alter runtime learning boundaries
"""

from .recommendation_request_builder import (
    build_recommendation_request,
)
from .recommendation_response_builder import (
    build_recommendation_response,
)

__all__ = [
    "build_recommendation_request",
    "build_recommendation_response",
]