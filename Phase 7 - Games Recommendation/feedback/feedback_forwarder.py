from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


#---------------------------------
#Feedback Action Enum
#---------------------------------
class FeedbackAction(str, Enum):
    """
    Canonical user actions on a Phase 7 game recommendation.

    IMPORTANT:
    - Observational only
    - MUST NOT trigger runtime adaptation
    """
    CLICK = "click"
    VIEW = "view"
    LIKE = "like"
    DISLIKE = "dislike"



#---------------------------------
#Feedback Event Contract
#---------------------------------
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

    player_id: str
    game_id: str
    action: FeedbackAction
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)




#---------------------------------
#Non-blocking emitter
#---------------------------------

def emit_feedback_event(event: Phase7FeedbackEvent) -> None:
    """
    Phase 7 feedback forwarder (non-blocking).

    Design:
    - MUST NEVER raise
    - MUST NOT block runtime
    - Forward-only (Phase 5 owns learning)
    """

    try:
        payload = event.to_dict()

        # ✅ simulate forward (CI-safe)
        # future: send to queue / pipeline
        _ = payload

    except Exception:
        # ✅ CRITICAL: swallow ALL errors
        pass


__all__ = [
    "FeedbackAction",
    "Phase7FeedbackEvent",
    "emit_feedback_event",
]
