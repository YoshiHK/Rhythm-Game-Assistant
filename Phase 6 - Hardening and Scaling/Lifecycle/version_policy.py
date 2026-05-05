"""
Version Policy

Defines declarative, non-semantic rules for:
- API version compatibility
- Model version constraints
- Deprecation and sunset windows

This policy governs WHETHER execution is allowed,
not HOW execution behaves.
"""

from typing import Protocol


class VersionContext(Protocol):
    api_version: str
    model_version: str
    deprecated: bool


class VersionPolicy:
    """
    Phase 6 version gating policy.
    """

    def allow(self, context: VersionContext) -> bool:
        """
        Return True if versions are permitted for execution.

        Default behavior:
        - Block explicitly deprecated versions.
        - Allow all others.
        """
        if context.deprecated:
            return False
        return True
