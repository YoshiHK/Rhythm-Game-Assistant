from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Phase7Observation:
    """
    Phase 7 — Observability payload (contract-level)

    This is presentation/metrics only.
    Must be JSON-serializable and non-blocking to emit.
    """
    player_id: str
    timestamp: str
    recommendation_count: int
    metadata: Dict[str, Any]
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
    Collect a Phase 7 observation snapshot (non-blocking).

    Contract:
    - Always returns a dict payload
    - Never raises if sink fails
    """
    obs = Phase7Observation(
        player_id=str(player_id),
        timestamp=_now_utc_iso(),
        recommendation_count=len(items) if isinstance(items, list) else 0,
        metadata={"locale": locale or "", "ci_safe": True},
        reason=reason,
    )

    payload = obs.to_dict()

    # Non-blocking sink behavior
    if sink is not None:
        try:
            sink(payload)
        except Exception:
            pass

    return payload


__all__ = ["Phase7Observation", "collect_observation"]