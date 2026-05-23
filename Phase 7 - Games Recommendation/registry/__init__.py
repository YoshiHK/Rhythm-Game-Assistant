
"""
Phase 7 — Registry package (flat exports)

Design:
- Read-only access to games.json
- No runtime mutation
- CI-safe loader
"""


from registry.registry import GameInfo, GameRegistry
from registry.registry_loader import (
    load_games_registry,
    load_games_registry_from_dict,
)

__all__ = [
    "GameInfo",
    "GameRegistry",
    "load_games_registry",
    "load_games_registry_from_dict",
]