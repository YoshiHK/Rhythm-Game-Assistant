"""
Phase 5 — Recommendation Layer

This package defines structured request / response builders for recommendations.

## Primary Contracts

- recommendation_request.schema.json
- recommendation_response.schema.json

## Role

- Normalize recommendation request inputs
- Normalize structured recommendation responses
- Preserve provenance and model traceability
- Support downstream UI, telemetry, and feedback capture

## Primary API

- build_recommendation_request() → construct requests
- build_recommendation_response() → construct responses

## What This Layer Does

- Generate recommendation responses
- Attach ranking and scoring metadata
- Provide structured reasoning (reason_codes)
- Support rationale mapping for UI
- Maintain provenance chain

## What This Layer Does NOT Do

- ❌ Does NOT change model decisions
- ❌ Does NOT introduce new semantic meaning
- ❌ Does NOT generate training labels
- ❌ Does NOT perform runtime learning

## Traceability Requirements (NEW)

Responses MUST include:

- request_id
- provenance_id
- model_version
- feature_version
- recommended_items (with ranking)

## Upstream Source

- model inference → predictions
- personalization → user context

## Downstream Consumers

- UI/UX → presentation
- telemetry → signal collection
- feedback → user reactions
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
