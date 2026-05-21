from __future__ import annotations

"""
ranker.py
Phase 7 — Games Recommendations

Deterministic, auditable ranking logic.

Design constraints (sealed by the Phase 7 docs):
- Downstream-only: MUST NOT trigger analysis, ingestion, or training.
- Non-semantic: MUST NOT change tips meaning or upstream semantics.
- Deterministic: same inputs => same outputs.
- Explainable: emit structured, bounded reasons. No free-form generation required.
- This module performs NO I/O.

Runtime rule:
- Single authoritative ranking implementation at runtime.
- Evolution is handled by updating this implementation (no runtime version switching).

Learning Loop Contract (Non-Negotiable):
- This ranker MUST NOT learn or adapt at runtime.
- Feedback MUST NOT be consumed here.
- Any learning/calibration MUST occur offline (Phase 5) and be introduced ONLY via deployment:
  - by updating OFFLINE_TUNABLES below, or
  - by updating this implementation.
"""

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Contract-layer outputs (versionless)
from contracts.types import RecommendationItem

# ----------------------------
# Standardized constraint / adjustment codes
# ----------------------------
# NOTE: values are stable, machine-friendly strings. Do not change existing values.
CONSTRAINTS_APPLIED: Dict[str, str] = {
    "HISTORY_RECENT_PENALTY": "history:recent_penalty",
    "HISTORY_NOVELTY_BONUS": "history:novelty_bonus",
    "EXP_NEW": "exp:new",
    "EXP_INTERMEDIATE": "exp:intermediate",
    "EXP_ADVANCED": "exp:advanced",
    "FIT_LOW_CLEAR": "fit:low_clear",
    "FIT_HIGH_CLEAR": "fit:high_clear",
    "FIT_STAMINA_HIGH": "fit:stamina_high",
    "FIT_STAMINA_LOW": "fit:stamina_low",
    "AFFINITY_TAGS": "affinity:tags",
}

# ----------------------------
# Offline-tunable parameters (learning loop entrypoint)
# ----------------------------
# These parameters MAY be calibrated offline in Phase 5 based on feedback,
# but MUST be deployed as static values. No runtime adaptation allowed.
OFFLINE_TUNABLES: Dict[str, float] = {
    # History
    "history_recent_penalty": -0.10,
    "history_novelty_bonus": +0.05,

    # Experience / complexity fit
    "exp_weight": 0.10,  # used in exp delta formulas

    # Stamina fit
    "stamina_match_bonus": +0.04,
    "stamina_mismatch_penalty": -0.04,
    "stamina_match_threshold": 0.2,
    "stamina_mismatch_threshold": 0.5,

    # Tag affinity
    "tag_overlap_unit_bonus": 0.02,
    "tag_overlap_cap_bonus": 0.06,
    "tag_overlap_detail_cap": 3,
}

# ----------------------------
# Rank diagnostics (pure, per-item)
# ----------------------------

@dataclass(frozen=True)
class ScoreDelta:
    code: str
    delta: float
    detail: str = ""


@dataclass(frozen=True)
class RankDiagnostics:
    """
    Per-item diagnostics for auditability.
    Keep content bounded and machine-readable.
    """
    baseline: float
    deltas: List[ScoreDelta]
    unclamped: float
    clamped: float
    final: float


def _diag_to_dict(d: RankDiagnostics) -> Dict[str, Any]:
    return asdict(d)


# ----------------------------
# Helpers (pure)
# ----------------------------

def _stable_score(token: Any) -> float:
    """
    Stable baseline score in [0, 1).
    Deterministic across runs for the same token.
    """
    h = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    n = int(h[:12], 16)
    return (n % 1_000_000) / 1_000_000.0


def _as_str_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v) for v in x if v is not None]
    if isinstance(x, str):
        return [x]
    return []


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _norm_token(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip().lower().replace(" ", "_")


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


# ----------------------------
# Ranker (single authoritative implementation)
# ----------------------------

class DeterministicRanker:
    """
    Deterministic games recommendation ranker.

    Expected usage:
    - routing passes candidate_game_ids and player signals (dicts)
    - optional game_profiles can be provided for better fit scoring
      (still deterministic; still no I/O)

    This ranker never performs I/O and never imports upstream phases.
    """

    def rank_games(
        self,
        *,
        candidate_game_ids: Sequence[str],
        ctx: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        game_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[RecommendationItem]:
        # Alias for consumers that call rank_games()
        return self.rank(
            candidate_game_ids=candidate_game_ids,
            ctx=ctx,
            player_profile=player_profile,
            player_history=player_history,
            game_profiles=game_profiles,
        )

    def rank(
        self,
        *,
        candidate_game_ids: Sequence[str],
        ctx: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        game_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[RecommendationItem]:
        """
        Return contract-shaped RecommendationItem list ordered by descending score,
        with deterministic tie-breaks.

        The returned items include bounded, structured rationale payloads:
        - applied reason codes
        - diagnostics with baseline and deltas
        """
        locale = str(ctx.get("locale") or "")
        exp_level = _norm_token(player_profile.get("experience_level") or player_profile.get("exp") or "")
        stamina = _as_float(player_profile.get("stamina"))

        # History signals
        recent_games = set(_as_str_list(player_history.get("recent_game_ids") or player_history.get("recent_games")))
        played_games = set(_as_str_list(player_history.get("played_game_ids") or player_history.get("played_games")))
        played_or_recent = played_games.union(recent_games)

        # Affinity tags
        player_tags = set(_norm_token(t) for t in _as_str_list(player_profile.get("tags")) if t)

        scored: List[Tuple[str, float, Dict[str, Any]]] = []

        # Pull tunables once (still deterministic)
        H_RECENT = OFFLINE_TUNABLES["history_recent_penalty"]
        H_NOVELTY = OFFLINE_TUNABLES["history_novelty_bonus"]
        EXP_W = OFFLINE_TUNABLES["exp_weight"]
        ST_MATCH = OFFLINE_TUNABLES["stamina_match_bonus"]
        ST_MISMATCH = OFFLINE_TUNABLES["stamina_mismatch_penalty"]
        ST_MATCH_TH = OFFLINE_TUNABLES["stamina_match_threshold"]
        ST_MISMATCH_TH = OFFLINE_TUNABLES["stamina_mismatch_threshold"]
        TAG_UNIT = OFFLINE_TUNABLES["tag_overlap_unit_bonus"]
        TAG_CAP = OFFLINE_TUNABLES["tag_overlap_cap_bonus"]
        TAG_DETAIL_CAP = int(OFFLINE_TUNABLES["tag_overlap_detail_cap"])

        for gid_raw in candidate_game_ids:
            gid = str(gid_raw)
            baseline = _stable_score(gid)

            deltas: List[ScoreDelta] = []
            score = baseline

            # ---- History adjustment (bounded) ----
            if gid in recent_games:
                d = float(H_RECENT)
                deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["HISTORY_RECENT_PENALTY"], d, "recently played"))
                score += d
            elif gid not in played_or_recent:
                d = float(H_NOVELTY)
                deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["HISTORY_NOVELTY_BONUS"], d, "novel option"))
                score += d

            # ---- Experience adjustment (bounded) ----
            # Uses optional game_profiles[gid]["complexity"] in [0,1] if available.
            gp = (game_profiles or {}).get(gid) or {}
            complexity = _as_float(gp.get("complexity"))
            if complexity is None:
                # Deterministic pseudo-complexity derived from gid (still pure)
                complexity = _stable_score(f"{gid}:complexity")

            # experience tiers: new / intermediate / advanced
            if exp_level in {"new", "beginner", "exp:new"}:
                # Prefer lower complexity
                d = (EXP_W * (0.5 - float(complexity)))
                deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["EXP_NEW"], d, "prefer lower complexity"))
                score += d
            elif exp_level in {"intermediate", "mid", "exp:intermediate"}:
                # Prefer mid complexity near 0.5
                d = (EXP_W * (0.5 - abs(float(complexity) - 0.5)))
                deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["EXP_INTERMEDIATE"], d, "prefer mid complexity"))
                score += d
            elif exp_level in {"advanced", "expert", "exp:advanced"}:
                # Prefer higher complexity
                d = (EXP_W * (float(complexity) - 0.5))
                deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["EXP_ADVANCED"], d, "prefer higher complexity"))
                score += d

            # ---- Stamina fit (bounded) ----
            # Uses optional game_profiles[gid]["stamina_demand"] in [0,1].
            stamina_demand = _as_float(gp.get("stamina_demand"))
            if stamina is not None:
                if stamina_demand is None:
                    stamina_demand = _stable_score(f"{gid}:stamina_demand")
                # Fit improves when stamina is close to demand
                gap = abs(float(stamina) - float(stamina_demand))
                if gap <= float(ST_MATCH_TH):
                    d = float(ST_MATCH)
                    deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["FIT_STAMINA_HIGH"], d, "stamina match"))
                    score += d
                elif gap >= float(ST_MISMATCH_TH):
                    d = float(ST_MISMATCH)
                    deltas.append(ScoreDelta(CONSTRAINTS_APPLIED["FIT_STAMINA_LOW"], d, "stamina mismatch"))
                    score += d

            # ---- Affinity tags (bounded) ----
            game_tags = set(_norm_token(t) for t in _as_str_list(gp.get("tags")) if t)
            if player_tags and game_tags:
                overlap = sorted(player_tags.intersection(game_tags))
                if overlap:
                    # Small bounded boost with cap
                    d = min(float(TAG_CAP), float(TAG_UNIT) * len(overlap))
                    deltas.append(
                        ScoreDelta(
                            CONSTRAINTS_APPLIED["AFFINITY_TAGS"],
                            d,
                            f"tags:{','.join(overlap[:TAG_DETAIL_CAP])}",
                        )
                    )
                    score += d

            unclamped = score
            clamped = _clamp01(score)
            final = clamped

            diag = RankDiagnostics(
                baseline=baseline,
                deltas=deltas,
                unclamped=unclamped,
                clamped=clamped,
                final=final,
            )

            rationale = {
                "reasons": [sd.code for sd in deltas],
                "diagnostics": _diag_to_dict(diag),
                "locale": locale,
            }

            scored.append((gid, final, rationale))

        # Deterministic ordering:
        # - primary: score desc
        # - secondary: stable tie-break by game_id asc
        scored.sort(key=lambda x: (-x[1], x[0]))

        items: List[RecommendationItem] = []
        for gid, s, rationale in scored:
            items.append(
                RecommendationItem(
                    game_id=gid,
                    song_id="",  # Phase 7 is game-level (keep empty)
                    score=float(s),
                    rationale=rationale,
                )
            )

        return items


__all__ = [
    "DeterministicRanker",
    "RankDiagnostics",
    "ScoreDelta",
    "CONSTRAINTS_APPLIED",
    "OFFLINE_TUNABLES",
]