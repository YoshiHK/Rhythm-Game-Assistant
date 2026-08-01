"""
writers.normalizers

Canonical identity normalization layer.
"""

from .identity_normalizer import (
    normalize_game,
    normalize_difficulty,
    normalize_level,
    normalize_folder_identity,
)

__all__ = [
    "normalize_game",
    "normalize_difficulty",
    "normalize_level",
    "normalize_folder_identity",
]