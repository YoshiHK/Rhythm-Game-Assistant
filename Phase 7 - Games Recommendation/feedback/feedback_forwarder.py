from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class FeedbackAction(str, Enum):
    """
    Canonical user actions on a Phase 7 game recommendation.

    IMPORTANT:
    - Observational only
    - MUST NOT trigger runtime adaptation
    """
    ACCEPT = "accept"
    DISMISS = "dismiss"
    ALREADY_PLAYING = "already_playing"
    IGNORE = "ignore"


@dataclass(frozen=True)
class Phase7FeedbackEvent:
    """
    Canonical feedback event emitted by Phase 7.

    Design constraints:
    - Forward-only (to Phase 5 / analytics sinks)
    - Immutable
    - No semantic interpretation at runtime
    - No aggregation or scoring here
    """

    # Event identity
    event_type: str                  # fixed: "phase7.game_feedback"
    timestamp_utc: str               # ISO-8601 UTC

    # Core identifiers
    player_id: str
    game_id: str
    action: FeedbackAction

    # Optional context for offline learning (non-semantic)
    locale: Optional[str] = None
    recommendation_rank: Optional[int] = None
    surface: Optional[str] = None          # e.g. "home", "onboarding", "explore"
    exposure_reason: Optional[str] = None  # e.g. ranker constraint / explanation code
    session_id: Optional[str] = None       # UI / client session identifier


def emit_feedback_event(
    *,
    player_id: str,
    game_id: str,
    action: FeedbackAction,
    locale: Optional[str] = None,
    recommendation_rank: Optional[int] = None,
    surface: Optional[str] = None,
    exposure_reason: Optional[str] = None,
    session_id: Optional[str] = None,
    sink: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Emit a Phase 7 feedback event.

    This function:
    - DOES emit structured feedback
    - DOES NOT aggregate, learn, or adapt behavior
    - DOES NOT mutate Phase 7 runtime logic
    - MAY forward to an external sink (best-effort)

    Any learning based on this event MUST occur offline (Phase 5).
    """

    evt = Phase7FeedbackEvent(
        event_type="phase7.game_feedback",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        player_id=player_id,
        game_id=game_id,
        action=action,
        locale=locale,
        recommendation_rank=recommendation_rank,
        surface=surface,
        exposure_reason=exposure_reason,
        session_id=session_id,
    )

    payload = asdict(evt)

    if sink is not None:
        # Best-effort emission; failures must not affect runtime
        sink.emit(payload)
        
    if not registry.games:
        pytest.skip("No games available")

    return payload