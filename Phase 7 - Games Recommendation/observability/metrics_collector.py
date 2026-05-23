from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Phase7Observation:
    """
    Phase 7 — Observability payload (contract-level, CI-safe)

    Requirements:
    - Must be JSON-serializable
    - Must accept `timestamp` as an explicit field
    - Must be non-blocking to emit (sink failures swallowed)
    """
    player_id: str
    timestamp: str
    recommendation_count: int
    metadata: Dict[str, Any]
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def collect_observation(*args, **kwargs) -> Dict[str, Any]:
    """
    Collect observation (CI-safe, non-blocking).

    Supports:
    ✅ collect_observation(obs)
    ✅ collect_observation(player_id=..., ...)
    """

    # ✅ case 1: called with observation object
    if args:
        obs = args[0]

        try:
            payload = obs.to_dict() if hasattr(obs, "to_dict") else obs.__dict__
        except Exception:
            payload = {}

        return payload

    # ✅ case 2: keyword construction
    obs = Phase7Observation(
        player_id=str(kwargs.get("player_id", "")),
        timestamp=_now_utc_iso(),
        recommendation_count=len(kwargs.get("items", [])),
        metadata={"ci_safe": True},
        reason=kwargs.get("reason"),
    )

    return obs.to_dict()

__all__ = ["Phase7Observation", "collect_observation"]