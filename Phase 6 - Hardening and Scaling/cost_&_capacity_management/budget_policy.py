"""
Budget Policy (Phase 6)

Defines declarative budget constraints for execution.

This policy:
- Governs WHETHER execution is allowed under budget limits.
- Does NOT compute costs.
- Does NOT schedule execution.
"""

from typing import Protocol


class BudgetContext(Protocol):
    """
    Expected context attributes:
    - estimated_cost: float | None
    - budget_remaining: float | None
    - trigger_type: str  # scheduled | manual | external
    """


class BudgetPolicy:
    """
    Budget gating policy.
    """

    def allow(self, context: BudgetContext) -> bool:
        """
        Return True if execution is permitted under budget constraints.

        Default behavior (skeleton):
        - Manual executions are allowed.
        - Scheduled / external executions require budget_remaining >= estimated_cost.
        """
        if context.trigger_type == "manual":
            return True

        if context.estimated_cost is None or context.budget_remaining is None:
            return True  # insufficient info → allow by default

        return context.budget_remaining >= context.estimated_cost