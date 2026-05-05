"""
Must-Scan Guard (Phase 6)

Enforces the invariant:
"If new or changed candidate files exist relative to the latest scan-state,
 ingestion MUST NOT proceed against a stale scan-state."

This guard:
- DOES NOT schedule scans
- DOES NOT perform scans
- DOES NOT interpret file contents
"""

class MustScanContext:
    """
    Minimal interface required by MustScanGuard.

    Expected attributes (provided by routing_context):
    - scan_state_fresh: bool
    - trigger_type: str  # 'scheduled' | 'manual' | 'external'
    """

    scan_state_fresh: bool
    trigger_type: str


class MustScanGuard:
    """
    Guard enforcing must-scan rule.
    """

    def allow(self, context: MustScanContext) -> bool:
        """
        Return True if ingestion may proceed.

        Rules:
        - Manual execution is always allowed.
        - Scheduled / external execution requires fresh scan-state.
        """
        if context.trigger_type == "manual":
            return True

        return bool(context.scan_state_fresh)