"""
Phase 7 — Observability Layer

Defines metrics and lightweight collectors for recommendation behavior.
"""

from .metrics_collector import (
    Phase7Observation,
    collect_observation,
)

__all__ = [
    "Phase7Observation",
    "collect_observation",
]