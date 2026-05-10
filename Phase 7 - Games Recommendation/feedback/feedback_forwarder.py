from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class FeedbackAction(str, Enum):
    """
    Canonical user actions on a Phase 7 recommendation.
    """
    ACCEPT = "accept"
    DISMISS = "dismiss"
    ALREADY_PLAYING = "already_playing"
    IGNORE = "ignore"


@dataclass(frozen=True)
class Phase7FeedbackEvent:
    """
    Canonical feedback event emitted by Phase 7.

    This structure is:
    - versionless
    - additive
    - safe for downstream learning
    """
    player_id: str
    game_id: str
    action: FeedbackAction

    # Context
    locale: Optional[str] = None
    recommendation_rank: Optional[int] = None

    # Metadata
    source: str = "phase7"
    occurred_at_iso: str = ""

    def to_payload(self) -> Dict[str, Any]:
        """
        Convert to a serializable payload.
        """
        d = asdict(self)
        d["action"] = self.action.value
        return d


def emit_feedback_event(
    *,
    player_id: str,
    game_id: str,
    action: FeedbackAction,
    locale: Optional[str] = None,
    recommendation_rank: Optional[int] = None,
    sink: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Emit a Phase 7 feedback event.

    Parameters:
    - sink: optional callable(payload: dict) -> None
      (e.g. Phase 6 event bus, logger, async queue)

    Behavior:
    - Non-blocking
    - Failures are swallowed
    - Always returns the event payload for observability
    """
    event = Phase7FeedbackEvent(
        player_id=str(player_id),
        game_id=str(game_id),
        action=action,
        locale=str(locale) if locale else None,
        recommendation_rank=int(recommendation_rank) if recommendation_rank is not None else None,
        occurred_at_iso=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )

    payload = event.to_payload()

    if sink is not None:
        try:
            sink(payload)
        except Exception:
            # Non-blocking by design: feedback must never break runtime flows
            pass

    return payload