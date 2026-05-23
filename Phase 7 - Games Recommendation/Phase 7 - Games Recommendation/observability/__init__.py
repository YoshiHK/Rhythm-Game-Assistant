"""
Phase 7 — Observability package (metrics only)

Design:
- Collect semantic-safe observations
- Must be non-blocking
- Must NOT affect runtime decisions
"""

from .metrics_collector import (
    Phase7Observation,
    collect_observation,
)

__all__ = [
    "Phase7Observation",
    "collect_observation",
]