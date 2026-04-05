"""
SDK Boundary

Responsibilities:
- Define stable SDK-facing abstractions
- Prevent direct access to internal representations
- Enable safe evolution of internal systems
"""

class SDKBoundary:
    def expose(self, payload):
        return payload
