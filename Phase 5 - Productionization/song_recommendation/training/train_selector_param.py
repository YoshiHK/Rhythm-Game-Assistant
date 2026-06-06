from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Config / Report
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TrainingConfig:
    """
    Training configuration for heuristic calibration.

    This is NOT a model trainer.
    It produces static selector parameters suitable for deployment.

    Defaults mirror the intended Phase 6 selector defaults:
    - widen_steps: (2, 4, 6, 10)
    - top_producers: 5

    Design constraints:
    - offline only
    - deterministic
    - non-semantic
    - deployment-safe
    """
    # Default fallback parameters (used when features are missing)
    default_widen_steps: Tuple[float, ...] = (2.0, 4.0, 6.0, 10.0)
    default_top_producers: int = 5
    default_rank_decay_alpha: float = 0.15  # mild decay

    # Outcome score mapping (must align with feature layer)
    outcome_score: Optional[Dict[str, int]] = None

    # If True, drop rows with forbidden semantic keys
    strict_semantic_guard: bool = True

    # Minimum rows required to learn non-default params
    min_rows: int = 200

    # Cap for rank used in rank-decay fitting (avoid long tails)
    max_rank_for_fit: int = 30

    # Versioning / metadata
    training_schema_version: str = "v1_song_selector_params"
    expected_feature_schema_version: Optional[str] = "v1_selection_features"

    # If True, include lightweight data/fit diagnostics in report
    include_fit_diagnostics: bool = True


@dataclass(frozen=True)
class TrainingReport:
    total_rows_in: int
    total_rows_used: int
    total_rows_dropped: int
    used_defaults: bool
    learned_fields: List[str]
    metrics: Dict[str, Any]
    feature_schema_version: Optional[str]
    training_schema_version: str


# -----------------------------------------------------------------------------
# Safety guards (no semantics allowed)
# -----------------------------------------------------------------------------

_FORBIDDEN_SEMANTIC_KEYS = {
    # Raw gameplay / semantic content should never drive selector param fitting
    "tips", "tip", "guidance", "narrative",
    "taxonomy", "severity", "pattern_tags", "elements",
    "analysis", "inference", "section_metrics", "sections",
}

# Safe / expected feature keys (others are ignored, not rejected)
_ALLOWED_KEYS_HINT = {
    # identity / join keys
    "event_id",
    "provenance_id",
    "player_id",
    "game_id",
    "recommendation_set_id",
    "song_id",
    "difficulty",
    "rank",

    # selection context
    "tier_id",
    "target_metric",
    "catalog_fingerprint",
    "locale",
    "session_id",

    # outcomes
    "final_outcome",
    "outcome_score",
    "count_ignore",
    "count_accept",
    "count_played",
    "count_completed",
    "any_accept_or_better",
    "any_played_or_better",
    "any_completed",
    "exposure_span_seconds",

    # optional selection diagnostics (if feature layer includes them later)
    "window_used",
    "widen_step_index",
    "producer_rank",

    # optional metadata from feature layer wrapper
    "feature_schema_version",
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


# -----------------------------------------------------------------------------
# Core learning utilities (deterministic, explainable)
# -----------------------------------------------------------------------------

def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / float(len(xs))


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _fit_rank_decay_alpha(
    pairs: List[Tuple[int, float]],
    *,
    default_alpha: float,
) -> float:
    """
    Fit a simple rank decay alpha using a deterministic heuristic.

    We model expected score as:
        expected ≈ base - alpha * log(1 + rank)

    This is NOT statistical regression; it is a bounded calibration heuristic.

    Returns alpha in [0.0, 1.0].
    """
    if len(pairs) < 20:
        return default_alpha

    import math

    # Bucket by rank to reduce noise
    buckets: Dict[int, List[float]] = {}
    for r, s in pairs:
        buckets.setdefault(r, []).append(s)

    pts: List[Tuple[int, float]] = []
    for r in sorted(buckets.keys()):
        m = _mean(buckets[r])
        if m is not None:
            pts.append((r, m))

    if len(pts) < 10:
        return default_alpha

    low = pts[:3]
    high = pts[-3:]

    low_mean = _mean([s for _, s in low])
    high_mean = _mean([s for _, s in high])
    if low_mean is None or high_mean is None:
        return default_alpha

    r_low = _mean([math.log(1.0 + float(r)) for r, _ in low]) or 0.0
    r_high = _mean([math.log(1.0 + float(r)) for r, _ in high]) or 1.0

    denom = (r_high - r_low) if (r_high - r_low) != 0 else 1.0
    alpha = (low_mean - high_mean) / denom

    return _clamp(float(alpha), 0.0, 1.0)


def _learn_top_producers(rows: List[Dict[str, Any]], default_top: int) -> int:
    """
    Learn a bounded top_producers value using producer_rank coverage if available.

    Heuristic:
    - If producer_rank exists and many positive outcomes come from deeper ranks,
      increase top_producers modestly.
    - Otherwise keep default.
    """
    ranks: List[int] = []
    for r in rows:
        pr = _norm_int(r.get("producer_rank"))
        if pr is not None:
            score = _norm_int(r.get("outcome_score"))
            if score is not None and score >= 1:
                ranks.append(pr)

    if len(ranks) < 50:
        return default_top

    ranks_sorted = sorted(ranks)
    mid = ranks_sorted[len(ranks_sorted) // 2]

    if mid >= default_top:
        return int(_clamp(default_top + 2, 3, 15))
    if mid <= max(1, default_top // 2):
        return int(_clamp(default_top - 1, 3, 15))
    return default_top


def _learn_widen_steps(
    rows: List[Dict[str, Any]],
    default_steps: Tuple[float, ...],
) -> Tuple[float, ...]:
    """
    Learn widen steps using widen_step_index success distribution if available.

    Heuristic:
    - If many positive outcomes occur only at late widen steps,
      make earlier steps slightly larger.
    - Otherwise keep defaults.
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

    success_idxs = [idx for idx, sc in idx_scores if sc >= 1]
    if len(success_idxs) < 40:
        return default_steps

    # Fraction of successes that required the latest available step index
    max_idx = max(success_idxs)
    late = sum(1 for i in success_idxs if i >= max_idx)
    late_frac = late / float(len(success_idxs))

    steps = list(default_steps)
    if late_frac >= 0.25 and len(steps) >= 2:
        steps[0] = float(_clamp(steps[0] + 0.5, 1.0, 6.0))
        steps[1] = float(_clamp(steps[1] + 0.5, steps[0], 10.0))
        return tuple(steps)

    return default_steps


# -----------------------------------------------------------------------------
# Inputs normalization
# -----------------------------------------------------------------------------

def _extract_rows_and_feature_version(
    feature_rows: Iterable[Dict[str, Any]] | Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Accept either:
    - an iterable of feature row dicts
    - or a wrapper object from build_selection_feature_rows():
      {
          "rows": [...],
          "summary": {...},
          "feature_schema_version": "..."
      }
    """
    if isinstance(feature_rows, dict):
        rows = feature_rows.get("rows")
        version = feature_rows.get("feature_schema_version")
        if isinstance(rows, list):
            clean_rows = [r for r in rows if isinstance(r, dict)]
            return clean_rows, _norm_str(version) or None
        return [], _norm_str(version) or None

    rows_list = [r for r in feature_rows if isinstance(r, dict)]
    return rows_list, None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def train_song_selector_params(
    feature_rows: Iterable[Dict[str, Any]] | Dict[str, Any],
    *,
    config: TrainingConfig = TrainingConfig(),
) -> Dict[str, Any]:
    """
    Train (calibrate) static selector parameters from selection feature rows.

    Accepts:
    - plain iterable of feature rows
    - OR feature builder wrapper object with rows + feature_schema_version

    Returns:
      {
        "params": {...},   # deployment-safe, static parameters
        "report": {...}    # TrainingReport as dict
      }

    This function is deterministic and performs no I/O.
    """
    cfg = config
    outcome_score = _default_outcome_score() if cfg.outcome_score is None else dict(cfg.outcome_score)

    incoming_rows, detected_feature_schema_version = _extract_rows_and_feature_version(feature_rows)

    total_in = 0
    used = 0
    dropped = 0

    rows: List[Dict[str, Any]] = []
    for row in incoming_rows:
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

        # Minimal requirements
        final_outcome = _norm_str(row.get("final_outcome")).lower()
        if not final_outcome:
            dropped += 1
            continue

        # Ensure outcome_score exists; if not, derive from final_outcome
        normalized = dict(row)
        if normalized.get("outcome_score") is None:
            normalized["outcome_score"] = int(outcome_score.get(final_outcome, 0))

        rows.append(normalized)
        used += 1

    used_defaults = True
    learned_fields: List[str] = []

    widen_steps = cfg.default_widen_steps
    top_producers = cfg.default_top_producers
    rank_decay_alpha = cfg.default_rank_decay_alpha

    metrics: Dict[str, Any] = {
        "mean_outcome_score": None,
        "rows_for_fit": used,
        "feature_schema_version_detected": detected_feature_schema_version,
        "feature_schema_version_expected": cfg.expected_feature_schema_version,
        "feature_schema_version_match": (
            detected_feature_schema_version == cfg.expected_feature_schema_version
            if (detected_feature_schema_version and cfg.expected_feature_schema_version)
            else None
        ),
    }

    fit_diagnostics: Dict[str, Any] = {}

    if used >= cfg.min_rows:
        used_defaults = False

        # Learn rank_decay_alpha from (rank, outcome_score)
        pairs: List[Tuple[int, float]] = []
        for r in rows:
            rank = _norm_int(r.get("rank"))
            sc = _norm_float(r.get("outcome_score"))
            if rank is None or sc is None:
                continue
            if rank <= cfg.max_rank_for_fit:
                pairs.append((rank, float(sc)))

        if pairs:
            rank_decay_alpha = _fit_rank_decay_alpha(
                pairs,
                default_alpha=cfg.default_rank_decay_alpha,
            )
            learned_fields.append("rank_decay_alpha")
            if cfg.include_fit_diagnostics:
                fit_diagnostics["rank_decay_pairs"] = len(pairs)

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
    metrics["mean_outcome_score"] = _mean(scores) if scores else None

    if cfg.include_fit_diagnostics and fit_diagnostics:
        metrics["fit_diagnostics"] = fit_diagnostics

    params = {
        "schema_version": cfg.training_schema_version,
        "domain": "song_recommendation",
        "learning_phase": "offline_only",
        "feature_schema_version": detected_feature_schema_version,
        "selector_params": {
            "widen_steps": [float(x) for x in widen_steps],
            "top_producers": int(top_producers),
            "rank_decay_alpha": float(rank_decay_alpha),
        },
        "notes": (
            "Static selector parameters calibrated offline (Phase 5). "
            "Must be introduced via deployment only."
        ),
    }

    report = TrainingReport(
        total_rows_in=total_in,
        total_rows_used=used,
        total_rows_dropped=dropped,
        used_defaults=used_defaults,
        learned_fields=learned_fields,
        metrics=metrics,
        feature_schema_version=detected_feature_schema_version,
        training_schema_version=cfg.training_schema_version,
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
    - This function is intended for deployment / artifact pipelines only.
    """
    p = Path(path)
    p.write_text(
        json.dumps(params, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


__all__ = [
    "TrainingConfig",
    "TrainingReport",
    "train_song_selector_params",
    "export_song_selector_params_json",
]