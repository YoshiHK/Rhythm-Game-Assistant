"""
Capacity Router (Phase 6)

Evaluates execution requests against capacity constraints.

This router:
- Determines whether capacity is available.
- Does NOT provision resources.
- Does NOT reschedule execution.
"""

from typing import Protocol


class CapacityContext(Protocol):
    """
    Expected context attributes:
    - capacity_available: bool | None
    - trigger_type: str  # scheduled | manual | external
    """


class CapacityRouter:
    """
    Capacity gating router.
    """

    def allow(self, context: CapacityContext) -> bool:
        """
        Return True if sufficient capacity exists.

        Default behavior:
        - Manual execution is allowed.
        - Scheduled / external execution requires capacity_available == True.
        """
        if context.trigger_type == "manual":
            return True

        if context.capacity_available is None:
            return True  # unknown capacity → allow (Phase 6 skeleton)

        return bool(context.capacity_available)
``