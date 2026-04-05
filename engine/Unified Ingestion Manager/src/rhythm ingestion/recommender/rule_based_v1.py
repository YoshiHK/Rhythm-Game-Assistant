from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional


# -----------------------------
# Small math helpers
# -----------------------------

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _l2_norm(vec: List[float]) -> float:
    return sum(v * v for v in vec) ** 0.5


def _l1_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a.keys()) | set(b.keys())
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def _euclid_distance(a: Dict[str, float], b: Dict[str, float], scale: Dict[str, float]) -> float:
    keys = set(a.keys()) | set(b.keys())
    diffs: List[float] = []
    for k in keys:
        s = float(scale.get(k, 1.0) or 1.0)
        diffs.append((a.get(k, 0.0) - b.get(k, 0.0)) / s)
    return _l2_norm(diffs)


# -----------------------------
# Feature scaling (simple, deterministic)
# -----------------------------
# These scales keep distances sane without knowing game-specific ranges.
# They can be tuned later without changing schemas or callers.
DEFAULT_FEATURE_SCALES: Dict[str, float] = {
    "avg_nps": 10.0,
    "peak_nps": 15.0,
    "avg_npb": 6.0,
    "peak_npb": 10.0,
    "hold_ratio": 1.0,
    "lane_cross_rate": 1.0,
    "spacing_variance": 1.0,
    "bpm_shift_count": 5.0,
    "chart_stop_count": 5.0,
}


# -----------------------------
# Candidate model
# -----------------------------
@dataclass
class Candidate:
    song_id: str
    difficulty_label: Optional[str]
    difficulty_profile: Dict[str, Any]
    has_tips: bool = False
    tips_preview: Optional[str] = None
    game_specific_level: Any = None


# -----------------------------
# Core: distance between difficulty profiles
# -----------------------------
def difficulty_profile_distance(
    anchor: Dict[str, Any],
    cand: Dict[str, Any],
    *,
    feature_scales: Optional[Dict[str, float]] = None,
    w_section: float = 0.70,
    w_pattern: float = 0.30,
) -> float:
    """
    Compute a bounded-ish distance between two DifficultyProfile objects.

    - Section distance: Euclidean over section_features_mean (scaled).
    - Pattern distance: L1 over category_shares.

    Returns a non-negative float (smaller is more similar).
    """
    scales = feature_scales or DEFAULT_FEATURE_SCALES

    a_sec = anchor.get("section_features_mean") or {}
    c_sec = cand.get("section_features_mean") or {}

    # numeric-only dicts
    a_vec = {k: _safe_float(v) for k, v in a_sec.items() if isinstance(v, (int, float))}
    c_vec = {k: _safe_float(v) for k, v in c_sec.items() if isinstance(v, (int, float))}

    sec_dist = _euclid_distance(a_vec, c_vec, scales)

    a_pat = (anchor.get("pattern_profile") or {}).get("category_shares") or {}
    c_pat = (cand.get("pattern_profile") or {}).get("category_shares") or {}

    a_sh = {k: _safe_float(v) for k, v in a_pat.items() if isinstance(v, (int, float))}
    c_sh = {k: _safe_float(v) for k, v in c_pat.items() if isinstance(v, (int, float))}

    pat_dist = _l1_distance(a_sh, c_sh)

    # Weighted sum
    return (w_section * sec_dist) + (w_pattern * pat_dist)


# -----------------------------
# Explainability helpers
# -----------------------------
def _top_feature_deltas(anchor: Dict[str, Any], cand: Dict[str, Any], k: int = 3) -> List[Tuple[str, float]]:
    a = anchor.get("section_features_mean") or {}
    c = cand.get("section_features_mean") or {}
    keys = set(a.keys()) | set(c.keys())
    deltas = []
    for key in keys:
        av = _safe_float(a.get(key))
        cv = _safe_float(c.get(key))
        deltas.append((key, cv - av))
    deltas.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return deltas[:k]


def _build_actions(dominant_categories: List[str]) -> List[str]:
    actions: List[str] = []
    if "coordination" in dominant_categories:
        actions.append("Focus on alternating hands and lane transitions.")
    if "density" in dominant_categories or "burst" in dominant_categories:
        actions.append("Keep tapping relaxed to preserve stamina through dense sections.")
    if "readability" in dominant_categories:
        actions.append("Slow down visual scanning and pre-read note clusters.")
    if "hold" in dominant_categories:
        actions.append("Prioritize clean hold timing while maintaining tap stability.")
    if "gimmick" in dominant_categories:
        actions.append("Expect timing/structure changes and plan a simple recovery route.")
    return actions


def _rationale_summary(score: float, dom_cats: List[str]) -> str:
    if score >= 0.75:
        tone = "well-suited"
    elif score >= 0.50:
        tone = "a reasonable challenge"
    else:
        tone = "likely demanding"

    if dom_cats:
        return f"This pick is {tone} and mainly trains {', '.join(dom_cats[:2])}."
    return f"This pick is {tone} based on profile similarity."


# -----------------------------
# Public API: multi-candidate ranking
# -----------------------------
def recommend_ranked_v1(
    recommendation_input: Dict[str, Any],
    *,
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    Rule-based multi-candidate recommender (v1).

    Backward compatible:
    - If recommendation_input contains only a single song_context + difficulty_profile,
      returns a 1-item recommendation list.
    - If recommendation_input contains candidate_pool (optional extension),
      ranks all candidates by distance to the anchor difficulty_profile.

    Expected input keys (schema v1):
    - schema_version
    - player_context
    - difficulty_profile           (anchor profile; e.g., "current comfort zone")
    - song_context                 (single candidate)

    Optional extension (recommended for ranking use):
    - candidate_pool: [ { song_context, difficulty_profile }, ... ]
    """
    schema_version = "v1"
    player = recommendation_input["player_context"]
    anchor_profile = recommendation_input["difficulty_profile"]
    game_id = player["game_id"]

    # Player signals
    recent_clear_rate = _safe_float(player.get("recent_clear_rate", 0.5), 0.5)
    self_conf = _safe_float(player.get("self_reported_confidence", recent_clear_rate), recent_clear_rate)

    constraints = recommendation_input.get("recommendation_constraints") or {}
    max_jump = constraints.get("max_difficulty_jump")  # optional, may be None

    # Build candidate list
    candidates: List[Candidate] = []

    pool = recommendation_input.get("candidate_pool")
    if isinstance(pool, list) and pool:
        for item in pool:
            if not isinstance(item, dict):
                continue
            sc = item.get("song_context") or {}
            dp = item.get("difficulty_profile") or {}
            if not isinstance(sc, dict) or not isinstance(dp, dict):
                continue
            candidates.append(
                Candidate(
                    song_id=str(sc.get("song_id")),
                    difficulty_label=sc.get("difficulty_label"),
                    difficulty_profile=dp,
                    has_tips=bool(sc.get("has_tips", False)),
                    tips_preview=sc.get("tips_preview"),
                    game_specific_level=sc.get("game_specific_level"),
                )
            )
    else:
        # fallback to single candidate mode
        sc = recommendation_input["song_context"]
        candidates.append(
            Candidate(
                song_id=str(sc.get("song_id")),
                difficulty_label=sc.get("difficulty_label"),
                difficulty_profile=anchor_profile,  # if no candidate profile provided, treat as identical
                has_tips=bool(sc.get("has_tips", False)),
                tips_preview=sc.get("tips_preview"),
                game_specific_level=sc.get("game_specific_level"),
            )
        )

    # Rank candidates by distance to anchor
    ranked: List[Tuple[Candidate, float]] = []
    for c in candidates:
        dist = difficulty_profile_distance(anchor_profile, c.difficulty_profile)

        # Optional: if player confidence is low, penalize far distances more.
        # (still deterministic; no heuristics based on unknown scales)
        if self_conf < 0.6:
            dist *= 1.15

        ranked.append((c, dist))

    ranked.sort(key=lambda x: (x[1], x[0].song_id))

    # Build output recommendations
    recs: List[Dict[str, Any]] = []
    for idx, (cand, dist) in enumerate(ranked[:max_results], start=1):
        # Convert distance to confidence score: smaller dist => higher score
        # We bound it softly using (1 / (1 + dist)).
        base = 1.0 / (1.0 + float(dist))

        # Blend with recent performance (if player is clearing well, allow slightly higher confidence)
        conf = _clamp01((0.80 * base) + (0.20 * recent_clear_rate))

        dom_cats = (cand.difficulty_profile.get("pattern_profile") or {}).get("dominant_categories") or []
        if not isinstance(dom_cats, list):
            dom_cats = []

        deltas = _top_feature_deltas(anchor_profile, cand.difficulty_profile, k=3)
        key_factors = []
        for feat, delta in deltas:
            # Direction is descriptive, not evaluative
            direction = "neutral"
            if delta > 0.0001:
                direction = "positive"
            elif delta < -0.0001:
                direction = "negative"
            key_factors.append({"factor": str(feat), "direction": direction})

        recs.append(
            {
                "song_id": cand.song_id,
                "difficulty_label": cand.difficulty_label,
                "rank": idx,
                "confidence": round(conf, 3),
                "difficulty_profile": cand.difficulty_profile,
                "rationale": {
                    "summary": _rationale_summary(conf, dom_cats),
                    "key_factors": key_factors,
                },
                "tips_preview": cand.tips_preview if cand.has_tips else None,
                "recommended_actions": _build_actions([str(x) for x in dom_cats if isinstance(x, str)]),
            }
        )

    return {
        "schema_version": schema_version,
        "game_id": game_id,
        "recommendations": recs,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

