"""
Declarative Routing Policy for Phase 6.

Defines the final non-semantic decision of whether execution may proceed,
after all guards have been evaluated.
"""

class RoutingPolicy:
    """
    Final execution policy.
    """

    def allow(self, context) -> bool:
        """
        Return True if execution may proceed.

        Default Phase 6 behavior:
        - Manual execution always allowed.
        - Otherwise, rely on guard-derived signals.
        """
        if context.trigger_type == "manual":
            return True

        # Default allow (guards already enforced)
        return True
