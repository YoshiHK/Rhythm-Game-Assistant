"""
Phase 7 — Ranking Layer

This package contains the single authoritative ranking implementation
for Game Recommendations.

Contract (Non-Negotiable):
- Ranking is deterministic and side-effect free.
- Runtime behavior MUST NOT adapt based on feedback.
- This layer MUST NOT import or consume learning outputs directly.

Learning Loop Policy:
- Ranking behavior MAY evolve only via offline learning (Phase 5).
- Learned outcomes are introduced exclusively through:
  - deployment of updated static parameters, or
  - updates to the ranking implementation.
- Runtime version switching and inline adaptation are forbidden.

This guarantees that Phase 7 ranking remains:
- deterministic
- explainable
- auditable
- reversible
"""

from ranking.ranker import (
    DeterministicRanker,
    RankDiagnostics,
    ScoreDelta,
    CONSTRAINTS_APPLIED,
    OFFLINE_TUNABLES,
)

__all__ = [
    "DeterministicRanker",
    "RankDiagnostics",
    "ScoreDelta",
    "CONSTRAINTS_APPLIED",
    "OFFLINE_TUNABLES",
]