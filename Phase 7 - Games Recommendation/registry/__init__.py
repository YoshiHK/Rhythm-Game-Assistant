"""
Phase 7 — Registry Layer

Flat exports for the Phase 7 game registry.
This package is read-only and deterministic.
"""

from .registry import GameInfo, GameRegistry
from .registry_loader import (
    load_games_registry,
    load_games_registry_from_dict,
)

__all__ = [
    "GameInfo",
    "GameRegistry",
    "load_games_registry",
    "load_games_registry_from_dict",
]