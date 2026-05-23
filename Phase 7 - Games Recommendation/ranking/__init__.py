"""
Phase 7 — Ranking package (flat exports)

Design:
- Deterministic ranker only
- CI-safe imports (no side effects)
- Keep exports aligned with ranking/ranker.py
"""

from .ranker import DeterministicRanker

__all__ = [
    "DeterministicRanker",
]