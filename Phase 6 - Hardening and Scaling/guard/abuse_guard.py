"""
Abuse Guard (Phase 6)

Mitigates abusive or anomalous execution patterns.
"""

class AbuseContext:
    """
    Expected context attributes:
    - rate_limited: bool
    - anomalous: bool
    """

    rate_limited: bool
    anomalous: bool


class AbuseGuard:
    def allow(self, context: AbuseContext) -> bool:
        """
        Block execution if rate limits are exceeded or anomalies are detected.
        """
        if context.rate_limited:
            return False
        if context.anomalous:
            return False
        return True
