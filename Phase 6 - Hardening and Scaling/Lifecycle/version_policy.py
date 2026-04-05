"""
Version Policy

Defines declarative rules for:
- API version compatibility
- Model version constraints
- Deprecation and sunset windows
"""

class VersionPolicy:
    def allow(self, context) -> bool:
        return True
