"""
Deployment Router (Phase 6)

Evaluates whether execution may proceed based on deployment context.

This router:
- Enforces environment and stage constraints.
- Does NOT provision infrastructure.
- Does NOT reschedule execution.
"""

from typing import Protocol


class DeploymentContext(Protocol):
    """
    Expected context attributes:
    - environment: str    # dev | staging | prod
    - stage: str          # canary | stable | rollback
    - trigger_type: str   # scheduled | manual | external
    """


class DeploymentRouter:
    """
    Routing gate for deployment constraints.
    """

    def allow(self, context: DeploymentContext) -> bool:
        """
        Return True if execution is allowed in the given deployment context.

        Default behavior (skeleton):
        - All environments allowed.
        - Rollback stage always allowed.
        """
        if context.stage == "rollback":
            return True

        return True
