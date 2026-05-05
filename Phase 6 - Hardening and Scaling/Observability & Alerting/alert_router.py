"""
Alert Router (Phase 6)

Routes alerts based on SLO evaluation results.

This module:
- Consumes SLOResult
- Decides whether an alert should be emitted
- Does NOT perform notification delivery itself
"""

from typing import Optional

from .slo_router import SLOResult


class AlertRouter:
    """
    Determines alert escalation based on SLO results.
    """

    def route(self, slo_result: SLOResult) -> Optional[str]:
        """
        Determine alert action.

        Returns:
        - alert message identifier, or
        - None if no alert is required.
        """
        if not slo_result.healthy:
            return f"ALERT: {slo_result.reason or 'SLO violation'}"

        return None