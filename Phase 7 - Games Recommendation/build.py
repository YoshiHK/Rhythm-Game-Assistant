
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import Phase7Config
from .feature_flags import FeatureFlags
from .registry import GameInfo, GameRegistry
from .router import Phase7Router
from .ranker_v1 import DeterministicBaselineRankerV1


def build_registry_from_dict(raw: Dict[str, Any]) -> GameRegistry:
    entries: Dict[str, GameInfo] = {}
    for gid, meta in (raw or {}).items():
        entries[str(gid)] = GameInfo(game_id=str(gid), status=str(meta.get('status', 'disabled')), display_name=meta.get('display_name'))
    return GameRegistry(entries)


def build_phase7_router(*, config: Optional[Phase7Config] = None, registry: Optional[GameRegistry] = None, ranker: Optional[Any] = None, explainer: Optional[Any] = None) -> Phase7Router:
    cfg = config or Phase7Config(feature_flags=FeatureFlags())
    reg = registry or GameRegistry({})
    if ranker is None and cfg.ranker_version == 'v1':
        ranker = DeterministicBaselineRankerV1()
    return Phase7Router(config=cfg, registry=reg, ranker=ranker, explainer=explainer)
