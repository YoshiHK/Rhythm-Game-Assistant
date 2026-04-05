"""
Reliability Guard

Responsibilities:
- Idempotency
- Retries
- Circuit breakers
- Safe fallbacks
"""

class ReliabilityGuard:
    def prepare(self, context):
        return True
