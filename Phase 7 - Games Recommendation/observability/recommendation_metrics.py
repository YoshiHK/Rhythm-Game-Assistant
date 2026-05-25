"""
Phase 7 — Recommendation Metrics Catalog

Defines the canonical metric names used by Phase 7.
"""


# ✅ Volume & Coverage
VOLUME_METRICS = [
    "recommendation.requested",
    "recommendation.returned",
    "recommendation.empty",
    "recommendation.coverage_ratio",
]


# ✅ Explainability Quality
EXPLAINABILITY_METRICS = [
    "explanation.present_ratio",
    "explanation.why_count",
    "explanation.summary_present",
]


# ✅ Ranking Health
RANKING_METRICS = [
    "ranking.score_distribution",
    "ranking.diversity.game_id",
]


# ✅ Latency (semantic)
LATENCY_METRICS = [
    "phase7.execution_time_ms",
]


# ✅ Failure & Degradation
FAILURE_METRICS = [
    "phase7.disabled",
    "phase7.no_candidates",
    "phase7.degraded",
]


# ✅ Full catalog (flat)
ALL_METRICS = (
    VOLUME_METRICS
    + EXPLAINABILITY_METRICS
    + RANKING_METRICS
    + LATENCY_METRICS
    + FAILURE_METRICS
)