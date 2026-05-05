"""
Reliability Guard (Phase 6)

Protects against unstable or unsafe execution patterns.

This guard is non-semantic and execution-scoped only.
"""

class ReliabilityContext:
    """
    Expected context attributes:
    - retry_count: int
    - max_retries: int
    - idempotent: bool
    """

    retry_count: int
    max_retries: int
    idempotent: bool


class ReliabilityGuard:
    def allow(self, context: ReliabilityContext) -> bool:
        """
        Block execution if retry budget is exceeded and execution is non-idempotent.
        """
        if not context.idempotent and context.retry_count > context.max_retries:
            return False
        return True