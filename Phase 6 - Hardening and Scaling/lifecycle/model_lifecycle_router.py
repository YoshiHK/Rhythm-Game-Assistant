"""
Model Lifecycle Router (Phase 6)

Evaluates whether execution may proceed based on model lifecycle state.

This router:
- Governs model state (active, pinned, deprecated, rollback-only).
- Does NOT train models.
- Does NOT select models.
- Does NOT alter inference behavior.
"""

from typing import Protocol


class ModelLifecycleContext(Protocol):
    """
    Expected context attributes:
    - model_version: str
    - model_state: str   # e.g. "active", "pinned", "deprecated"
    - trigger_type: str  # scheduled | manual | external
    """


class ModelLifecycleRouter:
    """
    Routing gate for model lifecycle state.
    """

    def allow(self, context: ModelLifecycleContext) -> bool:
        """
        Return True if execution is allowed with the given model state.

        Default behavior (skeleton):
        - Deprecated models are blocked.
        - All other states are allowed.
        """
        if context.model_state == "deprecated":
            return False

        return True