"""
SDK Boundary (Phase 6)

Defines hard boundaries for partner SDK behavior.

This module:
- Specifies what SDKs are allowed to do.
- Prevents SDKs from bypassing Phase 6 routing and guards.
"""

from typing import Protocol


class SDKContext(Protocol):
    """
    Expected context attributes:
    - sdk_name: str
    - sdk_version: str
    - trigger_type: str  # external
    """


class SDKBoundary:
    """
    Enforces SDK execution constraints.
    """

    def allow(self, context: SDKContext) -> bool:
        """
        Return True if SDK execution is permitted.

        Default behavior:
        - All SDKs allowed (skeleton).
        """
        return True