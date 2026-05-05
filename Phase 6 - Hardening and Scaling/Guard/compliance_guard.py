"""
Compliance Guard (Phase 6)

Ensures auditability and regulatory constraints.
"""

class ComplianceContext:
    """
    Expected context attributes:
    - audit_logging_enabled: bool
    - retention_policy_valid: bool
    """

    audit_logging_enabled: bool
    retention_policy_valid: bool


class ComplianceGuard:
    def allow(self, context: ComplianceContext) -> bool:
        """
        Block execution if compliance requirements are not met.
        """
        if not context.audit_logging_enabled:
            return False
        if not context.retention_policy_valid:
            return False
        return True
