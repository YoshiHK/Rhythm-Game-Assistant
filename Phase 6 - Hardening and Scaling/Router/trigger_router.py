"""
Trigger Router (Phase 6)

Normalizes external execution triggers into a canonical routing context.

This module:
- DOES normalize trigger metadata.
- DOES NOT schedule execution.
- DOES NOT perform scanning.
- DOES NOT evaluate routing decisions.
"""

from dataclasses import dataclass
from typing import Literal, Optional


TriggerType = Literal["scheduled", "manual", "external"]


@dataclass(frozen=True)
class TriggerContext:
    """
    Immutable trigger context passed into Phase 6 routing.

    This context is consumed by routing_policy and guards.
    """
    trigger_type: TriggerType
    source: Optional[str] = None     # e.g. "cron", "cli", "ci", "partner"
    operator: Optional[str] = None   # populated for manual triggers
    reason: Optional[str] = None     # free-form annotation


class TriggerRouter:
    """
    Entry point for normalizing triggers.
    """

    def from_scheduler(self, *, source: str = "scheduler") -> TriggerContext:
        return TriggerContext(
            trigger_type="scheduled",
            source=source,
        )

    def from_manual(self, *, operator: str, reason: Optional[str] = None) -> TriggerContext:
        return TriggerContext(
            trigger_type="manual",
            source="cli",
            operator=operator,
            reason=reason,
        )

    def from_external(self, *, source: str, reason: Optional[str] = None) -> TriggerContext:
        return TriggerContext(
            trigger_type="external",
            source=source,
            reason=reason,
        )
