from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------
# Config / Report
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class TrainingConfig:
    """
    Training configuration for heuristic calibration.

    This is NOT a model trainer.
    It produces static selector parameters suitable for deployment.

    Defaults mirror the Phase 6 selector defaults:
    - widen_steps: (2,4,6,10)
    - top_producers: 5
    """
    # Default fallback parameters (used when features are missing)
    default_widen_steps: Tuple[float, ...] = (2.0, 4.0, 6.0, 10.0)
    default_top_producers: int = 5
    default_rank_decay_alpha: float = 0.15  # mild decay

    # Outcome score mapping (must align with feature layer)
    outcome_score: Dict[str, int] = None  # filled if None

    # If True, drop rows with forbidden semantic keys
    strict_semantic_guard: bool = True

    # Minimum rows required to learn non-default params
    min_rows: int = 200

    # Cap for rank used in rank-decay fitting (avoid long tails)
    max_rank_for_fit: int = 30


@dataclass(frozen=True)
class TrainingReport:
    total_rows_in: int
    total_rows_used: int
    total_rows_dropped: int
    used_defaults: bool
    learned_fields: List[str]
    metrics: Dict[str, Any]


# ---------------------------------------------------------------------
# Safety guards (no semantics allowed)
# ---------------------------------------------------------------------

_FORBIDDEN_SEMANTIC_KEYS = {
    "tips", "tip", "guidance", "narrative",
    "taxonomy", "severity", "pattern_tags", "elements",
    "analysis", "inference", "section_metrics", "sections",
}

_ALLOWED_KEYS_HINT = {
    # identity / join keys
    "player_id", "game_id", "recommendation_set_id", "song_id", "difficulty", "rank",
    # selection context
    "tier_id", "target_metric", "catalog_fingerprint", "locale",
    # outcomes
    "final_outcome", "outcome_score",
    "count_ignore", "count_accept", "count_played", "count_completed",
    "any_accept_or_better", "any_played_or_better", "any_completed",
    "exposure_span_seconds",
    # optional selection diagnostics (may be present if features layer includes them later)
    "window_used", "widen_step_index", "producer_rank",
}


def _default_outcome_score() -> Dict[str, int]:
    return {"ignore": 0, "accept": 1, "played": 2, "completed": 3}


def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _norm_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _semantic_guard(row: Dict[str, Any]) -> None:
    lowered = {str(k).strip().lower() for k in row.keys()}
    for bad in _FORBIDDEN_SEMANTIC_KEYS:
        if bad in lowered:
            raise ValueError(f"Semantic leakage detected: forbidden key '{bad}' present")


# ---------------------------------------------------------------------
# Core learning utilities (deterministic, explainable)
# ---------------------------------------------------------------------

def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / float(len(xs))


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _fit_rank_decay_alpha(pairs: List[Tuple[int, float]], *, default_alpha: float) -> float:
    """
    Fit a simple rank decay alpha using a deterministic heuristic.

    We model expected score as:
      expected ≈ base - alpha * log(1 + rank)

    This is NOT statistical regression—just a bounded calibration.

    Returns alpha in [0.0, 1.0].
    """
    if len(pairs) < 20:
        return default_alpha

    # bucket by rank to reduce noise
    buckets: Dict[int, List[float]] = {}
    for r, s in pairs:
        buckets.setdefault(r, []).append(s)

    # compute mean per rank
    pts: List[Tuple[int, float]] = []
    for r in sorted(buckets.keys()):
        m = _mean(buckets[r])
        if m is not None:
            pts.append((r, m))

    if len(pts) < 10:
        return default_alpha

    # approximate slope between low ranks and higher ranks
    low = pts[:3]
    high = pts[-3:]

    low_mean = _mean([s for _, s in low])
    high_mean = _mean([s for _, s in high])
    if low_mean is None or high_mean is None:
        return default_alpha

    # use log distance
    import math
    r_low = _mean([math.log(1.0 + float(r)) for r, _ in low]) or 0.0
    r_high = _mean([math.log(1.0 + float(r)) for r, _ in high]) or 1.0

    denom = (r_high - r_low) if (r_high - r_low) != 0 else 1.0
    alpha = (low_mean - high_mean) / denom

    # bound alpha to reasonable range
    return _clamp(float(alpha), 0.0, 1.0)


def _learn_top_producers(rows: List[Dict[str, Any]], default_top: int) -> int:
    """
    Learn a bounded top_producers value using producer_rank coverage if available.

    Heuristic:
    - If producer_rank exists and many successes come from deeper ranks,
      increase top_producers modestly.
    - Otherwise keep default.
    """
    ranks: List[int] = []
    for r in rows:
        pr = _norm_int(r.get("producer_rank"))
        if pr is not None:
            # consider only positive outcomes
            score = _norm_int(r.get("outcome_score"))
            if score is not None and score >= 1:
                ranks.append(pr)

    if len(ranks) < 50:
        return default_top

    # if median producer_rank is near the cap, widen candidate producer pool slightly
    ranks_sorted = sorted(ranks)
    mid = ranks_sorted[len(ranks_sorted)//2]

    # simple bounded adjustment
    if mid >= default_top:
        return int(_clamp(default_top + 2, 3, 15))
    if mid <= max(1, default_top // 2):
        return int(_clamp(default_top - 1, 3, 15))
    return default_top


def _learn_widen_steps(rows: List[Dict[str, Any]], default_steps: Tuple[float, ...]) -> Tuple[float, ...]:
    """
    Learn widen steps using widen_step_index success distribution if available.

    Heuristic:
    - If many positive outcomes occur only at late widen steps, make earlier steps slightly larger.
    - If most successes occur at early steps, keep defaults.
    """
    idx_scores: List[Tuple[int, int]] = []
    for r in rows:
        idx = _norm_int(r.get("widen_step_index"))
        sc = _norm_int(r.get("outcome_score"))
        if idx is None or sc is None:
            continue
        idx_scores.append((idx, sc))

    if len(idx_scores) < 80:
        return default_steps

    # success means accept or better (score >= 1)
    success_idxs = [idx for idx, sc in idx_scores if sc >= 1]
    if len(success_idxs) < 40:
        return default_steps

    # compute fraction of successes that required late widening
    max_idx = max(success_idxs)
    late = sum(1 for i in success_idxs if i >= max_idx)
    late_frac = late / float(len(success_idxs))

    # deterministic adjustment
    steps = list(default_steps)
    if late_frac >= 0.25 and len(steps) >= 2:
        # bump early windows slightly (bounded)
        steps[0] = float(_clamp(steps[0] + 0.5, 1.0, 6.0))
        steps[1] = float(_clamp(steps[1] + 0.5, steps[0], 10.0))
        return tuple(steps)

    return default_steps


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def train_song_selector_params(
    feature_rows: Iterable[Dict[str, Any]],
    *,
    config: TrainingConfig = TrainingConfig(),
) -> Dict[str, Any]:
    """
    Train (calibrate) static selector parameters from selection feature rows.

    Returns:
      {
        "params": {...},   # deployment-safe, static parameters
        "report": {...}    # TrainingReport as dict
      }

    This function is deterministic and performs no I/O.
    """
    cfg = config
    outcome_score = _default_outcome_score() if cfg.outcome_score is None else dict(cfg.outcome_score)

    total_in = 0
    used = 0
    dropped = 0

    rows: List[Dict[str, Any]] = []
    for row in feature_rows:
        total_in += 1
        if not isinstance(row, dict):
            dropped += 1
            continue

        try:
            if cfg.strict_semantic_guard:
                _semantic_guard(row)
        except Exception:
            dropped += 1
            continue

        # minimal requirements
        if not _norm_str(row.get("final_outcome")):
            dropped += 1
            continue

        # ensure outcome_score exists; if not, derive from final_outcome
        if row.get("outcome_score") is None:
            fo = _norm_str(row.get("final_outcome")).lower()
            row = dict(row)
            row["outcome_score"] = int(outcome_score.get(fo, 0))

        rows.append(row)
        used += 1

    used_defaults = True
    learned_fields: List[str] = []

    # Default params
    widen_steps = cfg.default_widen_steps
    top_producers = cfg.default_top_producers
    rank_decay_alpha = cfg.default_rank_decay_alpha

    metrics: Dict[str, Any] = {
        "mean_outcome_score": None,
        "rows_for_fit": used,
    }

    if used >= cfg.min_rows:
        used_defaults = False

        # Learn rank decay alpha from (rank, outcome_score)
        pairs: List[Tuple[int, float]] = []
        for r in rows:
            rank = _norm_int(r.get("rank"))
            sc = _norm_float(r.get("outcome_score"))
            if rank is None or sc is None:
                continue
            if rank <= cfg.max_rank_for_fit:
                pairs.append((rank, float(sc)))
        if pairs:
            rank_decay_alpha = _fit_rank_decay_alpha(pairs, default_alpha=cfg.default_rank_decay_alpha)
            learned_fields.append("rank_decay_alpha")

        # Learn top_producers (only if producer_rank present)
        top_producers2 = _learn_top_producers(rows, cfg.default_top_producers)
        if top_producers2 != top_producers:
            top_producers = top_producers2
            learned_fields.append("top_producers")

        # Learn widen_steps (only if widen_step_index present)
        widen2 = _learn_widen_steps(rows, cfg.default_widen_steps)
        if widen2 != widen_steps:
            widen_steps = widen2
            learned_fields.append("widen_steps")

    # Metrics
    scores = [float(_norm_int(r.get("outcome_score")) or 0) for r in rows]
    metrics["mean_outcome_score"] = (_mean(scores) if scores else None)

    params = {
        "schema_version": "v1",
        "domain": "song_recommendation",
        "learning_phase": "offline_only",
        "selector_params": {
            "widen_steps": [float(x) for x in widen_steps],
            "top_producers": int(top_producers),
            "rank_decay_alpha": float(rank_decay_alpha),
        },
        "notes": "Static parameters calibrated offline (Phase 5). Must be introduced via deployment only.",
    }

    report = TrainingReport(
        total_rows_in=total_in,
        total_rows_used=used,
        total_rows_dropped=dropped,
        used_defaults=used_defaults,
        learned_fields=learned_fields,
        metrics=metrics,
    )

    return {
        "params": params,
        "report": asdict(report),
    }


def export_song_selector_params_json(params: Dict[str, Any], path: str | Path) -> None:
    """
    Export learned selector params to JSON (offline artifact).

    NOTE:
    - Phase 6 runtime MUST NOT load artifacts dynamically.
    - This file is meant for deployment pipelines.
    """
    p = Path(path)
    p.write_text(json.dumps(params, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")