"""
Security Guard (Phase 6)

Enforces authentication and access boundaries.
"""

class SecurityContext:
    """
    Expected context attributes:
    - authenticated: bool
    - authorized: bool
    """

    authenticated: bool
    authorized: bool


class SecurityGuard:
    def allow(self, context: SecurityContext) -> bool:
        """
        Block execution if authentication or authorization fails.
        """
        if not context.authenticated:
            return False
        if not context.authorized:
            return False
        return True