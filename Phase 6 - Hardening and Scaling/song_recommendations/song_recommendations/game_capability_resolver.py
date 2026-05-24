"""
Phase 6 Song Recommendations — Game Capability Resolver

Purpose
-------
Resolve game-specific configuration required for multi-game-safe song rec logic:
- difficulty tier ordering (tier_id list)
- completion ladder ordering (lowest -> highest)
- optional aliases (input label -> canonical id)

Design constraints:
- wiring-only, non-semantic
- deterministic
- no external I/O by default (caller may supply a loaded dict)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class CapabilityError(ValueError):
    """Raised when game capability config is missing or invalid."""


@dataclass(frozen=True)
class GameCapability:
    game_id: str
    difficulty_tiers: List[str]
    completion_ladder: List[str]
    tier_aliases: Dict[str, str]
    completion_aliases: Dict[str, str]


def _as_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return str(x).strip() or None


# Minimal built-in defaults (expand safely; no runtime versioning).
DEFAULT_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "proseka": {
        "difficulty_tiers": ["expert", "master", "append"],
        "completion_ladder": ["clear", "fc", "ap"],
        "tier_aliases": {
            "Expert": "expert",
            "Master": "master",
            "Append": "append",
        },
        "completion_aliases": {
            "Clear": "clear",
            "FC": "fc",
            "FullCombo": "fc",
            "AP": "ap",
            "AllPerfect": "ap",
        },
    }
}


def resolve_game_capability(
    game_id: str,
    *,
    capabilities: Optional[Dict[str, Dict[str, Any]]] = None,
) -> GameCapability:
    """Resolve a GameCapability from provided registry or built-in defaults."""
    gid = _as_str(game_id)
    if not gid:
        raise CapabilityError("game_id is required")

    registry = capabilities if isinstance(capabilities, dict) else DEFAULT_CAPABILITIES
    cfg = registry.get(gid)
    if not isinstance(cfg, dict):
        raise CapabilityError(f"missing game capability config for game_id={gid!r}")

    tiers = cfg.get("difficulty_tiers")
    ladder = cfg.get("completion_ladder")

    if not isinstance(tiers, list) or not tiers or not all(isinstance(x, str) and x.strip() for x in tiers):
        raise CapabilityError(f"invalid difficulty_tiers for game_id={gid!r}")
    if not isinstance(ladder, list) or not ladder or not all(isinstance(x, str) and x.strip() for x in ladder):
        raise CapabilityError(f"invalid completion_ladder for game_id={gid!r}")

    tier_aliases = cfg.get("tier_aliases") or {}
    completion_aliases = cfg.get("completion_aliases") or {}

    if not isinstance(tier_aliases, dict):
        tier_aliases = {}
    if not isinstance(completion_aliases, dict):
        completion_aliases = {}

    ta: Dict[str, str] = {}
    for k, v in tier_aliases.items():
        kk = _as_str(k)
        vv = _as_str(v)
        if kk and vv:
            ta[kk] = vv

    ca: Dict[str, str] = {}
    for k, v in completion_aliases.items():
        kk = _as_str(k)
        vv = _as_str(v)
        if kk and vv:
            ca[kk] = vv

    return GameCapability(
        game_id=gid,
        difficulty_tiers=[t.strip() for t in tiers],
        completion_ladder=[c.strip() for c in ladder],
        tier_aliases=ta,
        completion_aliases=ca,
    )


def canonicalize_tier_id(cap: GameCapability, tier_id: str) -> str:
    s = _as_str(tier_id) or ""
    return cap.tier_aliases.get(s, s.lower() or s)


def canonicalize_completion_id(cap: GameCapability, completion_id: str) -> str:
    s = _as_str(completion_id) or ""
    return cap.completion_aliases.get(s, s.lower() or s)