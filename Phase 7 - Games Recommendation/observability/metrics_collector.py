from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Phase7Observation:
    """
    Canonical observation event emitted by Phase 7.

    This structure is:
    - versionless
    - additive
    - observational only
    """
    player_id: str
    locale: Optional[str]

    requested: int
    returned: int

    has_explanations: bool
    avg_why_count: Optional[float]

    distinct_game_count: int

    degraded: bool
    reason: Optional[str]

    occurred_at_iso: str

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


def collect_observation(
    *,
    player_id: str,
    locale: Optional[str],
    items: List[Any],
    reason: Optional[str] = None,
    sink: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Collect a Phase 7 observation snapshot.

    Parameters:
    - items: list of RecommendationItem (or compatible objects)
    - reason: optional degradation or empty reason
    - sink: optional callable(payload: dict) -> None
            (owned by Phase 6; e.g. metrics pipeline)

    Behavior:
    - Non-blocking
    - Failures are swallowed
    - Always returns payload for logging or debugging
    """
    returned = len(items or [])

    # Explainability inspection (safe, shallow)
    why_counts: List[int] = []
    has_explanations = True

    for it in items or []:
        rationale = getattr(it, "rationale", None)
        explanation = None
        if isinstance(rationale, dict):
            explanation = rationale.get("explanation")
        if not isinstance(explanation, dict):
            has_explanations = False
            continue
        why = explanation.get("why")
        if isinstance(why, list):
            why_counts.append(len(why))

    avg_why = (
        sum(why_counts) / len(why_counts)
        if why_counts
        else None
    )

    distinct_games = len({getattr(it, "game_id", None) for it in items or []})

    obs = Phase7Observation(
        player_id=str(player_id),
        locale=str(locale) if locale else None,
        requested=1,
        returned=returned,
        has_explanations=has_explanations,
        avg_why_count=avg_why,
        distinct_game_count=distinct_games,
        degraded=bool(reason),
        reason=str(reason) if reason else None,
        occurred_at_iso=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )

    payload = obs.to_payload()

    if sink is not None:
        try:
            sink(payload)
        except Exception:
            # Observability must never affect runtime
            pass

    return payload