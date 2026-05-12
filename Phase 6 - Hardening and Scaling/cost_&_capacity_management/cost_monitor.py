"""
Cost Monitor (Phase 6)

Observes cost-related signals and emits non-semantic metrics.

This module:
- Observes cost usage.
- Emits cost-related measurements.
- Does NOT enforce limits.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CostMetrics:
    """
    Immutable snapshot of cost signals.
    """
    estimated_cost: Optional[float] = None
    budget_remaining: Optional[float] = None
    cost_rate_per_hour: Optional[float] = None


class CostMonitor:
    """
    Produces cost-related metrics for routing and observability.
    """

    def observe(self) -> CostMetrics:
        """
        Observe current cost signals.

        Skeleton implementation:
        - No actual cost computation.
        """
        return CostMetrics()