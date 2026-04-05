"""
Declarative routing policy definitions for Phase 6.
"""

class RoutingPolicy:
    def allow(self, context) -> bool:
        return True
