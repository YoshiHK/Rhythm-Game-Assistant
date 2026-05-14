from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class SongFeedbackAction(str, Enum):
    """
    Canonical user actions on a Song Recommendation.

    Observational only.
    MUST NOT trigger runtime adaptation.
    """
    ACCEPT = "accept"          # user explicitly accepts the recommendation
    IGNORE = "ignore"          # user skips / dismisses
    PLAYED = "played"          # user played the song
    COMPLETED = "completed"    # user completed the song/session


@dataclass(frozen=True)
class SongRecommendationFeedbackEvent:
    """
    Canonical feedback event for Song Recommendations.

    Design constraints:
    - Forward-only (Phase 6 -> Phase 5)
    - Immutable
    - No semantic interpretation at runtime
    """

    event_type: str                    # fixed: "phase6.song_feedback"
    timestamp_utc: str                 # ISO-8601 UTC

    # Identity
    player_id: str
    game_id: str
    song_id: str
    difficulty: Optional[str]

    # Recommendation context
    recommendation_set_id: str
    rank: Optional[int]

    # User action
    action: SongFeedbackAction

    # Optional, non-semantic context
    tier_id: Optional[str] = None
    target_metric: Optional[float] = None
    catalog_fingerprint: Optional[str] = None
    locale: Optional[str] = None
    session_id: Optional[str] = None


def emit_song_feedback_event(
    *,
    player_id: str,
    game_id: str,
    song_id: str,
    difficulty: Optional[str],
    recommendation_set_id: str,
    action: SongFeedbackAction,
    rank: Optional[int] = None,
    tier_id: Optional[str] = None,
    target_metric: Optional[float] = None,
    catalog_fingerprint: Optional[str] = None,
    locale: Optional[str] = None,
    session_id: Optional[str] = None,
    sink: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Emit a Song Recommendation feedback event.

    This function:
    - DOES emit structured feedback
    - DOES NOT aggregate, learn, or adapt behavior
    - DOES NOT modify runtime recommendation logic
    """

    evt = SongRecommendationFeedbackEvent(
        event_type="phase6.song_feedback",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        player_id=player_id,
        game_id=game_id,
        song_id=song_id,
        difficulty=difficulty,
        recommendation_set_id=recommendation_set_id,
        rank=rank,
        action=action,
        tier_id=tier_id,
        target_metric=target_metric,
        catalog_fingerprint=catalog_fingerprint,
        locale=locale,
        session_id=session_id,
    )

    payload = asdict(evt)

    if sink is not None:
        # Best-effort emission; must never block runtime
        sink.emit(payload)

    return payload