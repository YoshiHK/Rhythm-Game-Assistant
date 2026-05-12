"""
Partner Gateway (Phase 6)

Defines the external partner boundary.

This gateway:
- Validates partner access.
- Normalizes requests into routing context.
- Does NOT execute ingestion or analysis.
"""

from typing import Protocol, Optional


class PartnerContext(Protocol):
    """
    Expected context attributes:
    - partner_id: str
    - authenticated: bool
    - authorized: bool
    - trigger_type: str  # external
    """


class PartnerGateway:
    """
    Entry point for partner-originated requests.
    """

    def allow(self, context: PartnerContext) -> bool:
        """
        Return True if partner access is permitted.
        """
        if not context.authenticated:
            return False

        if not context.authorized:
            return False

        return True

    def normalize(self, *, partner_id: str, reason: Optional[str] = None):
        """
        Normalize partner request into trigger context.

        NOTE:
        Actual trigger normalization is delegated to Trigger Router.
        """
        return {
            "trigger_type": "external",
            "source": "partner",
            "partner_id": partner_id,
            "reason": reason,
        }