"""
API Version Router (Phase 6)

Evaluates API version compatibility for external execution.
"""

from typing import Protocol


class APIVersionContext(Protocol):
    """
    Expected context attributes:
    - api_version: str
    - deprecated: bool
    - trigger_type: str  # scheduled | manual | external
    """


class APIVersionRouter:
    """
    Routing gate for API version compatibility.
    """

    def allow(self, context: APIVersionContext) -> bool:
        """
        Return True if the API version is allowed.

        Default behavior:
        - Deprecated versions are blocked.
        """
        if context.deprecated:
            return False

        return True