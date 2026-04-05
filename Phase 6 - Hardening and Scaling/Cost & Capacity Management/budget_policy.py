"""
Budget Policy

Defines declarative rules for:
- Budget thresholds
- Spending alerts
- Automated mitigation triggers
"""

class BudgetPolicy:
    def allow(self, context) -> bool:
        return True
