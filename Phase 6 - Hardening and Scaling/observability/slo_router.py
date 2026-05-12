"""
SLO Router (Phase 6)

Evaluates system health against declared Service Level Objectives (SLOs).

This router:
- Consumes HealthMetrics
- Produces SLO evaluation results
- Does NOT trigger alerts directly
"""

from dataclasses import dataclass
from typing import Optional

from .health_metrics import HealthMetrics


@dataclass(frozen=True)
class SLOResult:
    """
    Result of SLO evaluation.
    """
    healthy: bool
    reason: Optional[str] = None


class SLORouter:
    """
    Evaluates SLOs based on health metrics.
    """

    def evaluate(self, metrics: HealthMetrics) -> SLOResult:
        """
        Evaluate system health.

        Default behavior (skeleton):
        - If scan age is known and excessively stale, mark unhealthy.
        - Otherwise, healthy.

        NOTE:
        Thresholds are intentionally not defined here.
        """
        if metrics.scan_age_seconds is not None:
            # Threshold intentionally unspecified (Phase 6 skeleton)
            pass

        return SLOResult(healthy=True)