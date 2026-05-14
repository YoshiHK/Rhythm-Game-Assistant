from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------
# Config / Report
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class EvalConfig:
    """
    Evaluation configuration.

    This layer must remain:
    - offline-only
    - deterministic
    - selection-level only

    Regression guards compare current metrics vs baseline metrics (if provided).
    """
    # Evaluate acceptance / play / completion at these rank cutoffs
    k_values: Tuple[int, ...] = (1, 3, 5)

    # Minimum sample size required to enforce regression guards
    min_rows_for_guards: int = 200

    # Allowed maximum drop (negative delta) in key rates before failing guards
    max_drop_accept_rate: float = 0.02
    max_drop_play_rate: float = 0.02
    max_drop_complete_rate: float = 0.01

    # Optional: require non-negative improvement (set to 0.0) instead of allowing drops
    # (keep defaults lenient for early iterations)
    min_delta_accept_rate: float = -0.02
    min_delta_play_rate: float = -0.02
    min_delta_complete_rate: float = -0.01

    # If True, reject rows that contain forbidden semantic keys
    strict_semantic_guard: bool = True

    # If True, drop invalid rows instead of raising
    drop_invalid: bool = True


@dataclass(frozen=True)
class EvalReport:
    total_rows_in: int
    total_rows_used: int
    total_rows_dropped: int

    metrics: Dict[str, Any]
    baseline_metrics: Optional[Dict[str, Any]]
    deltas: Optional[Dict[str, Any]]

    guard_pass: bool
    guard_fail_reasons: List[str]


# ---------------------------------------------------------------------
# Safety guards (no semantics allowed)
# ---------------------------------------------------------------------

_FORBIDDEN_SEMANTIC_KEYS = {
    "tips", "tip", "guidance", "narrative",
    "taxonomy", "severity", "pattern_tags", "elements",
    "analysis", "inference", "section_metrics", "sections",
}

_ALLOWED_SELECTION_KEYS_HINT = {
    "player_id", "game_id", "recommendation_set_id", "song_id", "difficulty", "rank",
    "tier_id", "target_metric", "catalog_fingerprint", "locale",
    "final_outcome", "outcome_score",
    "count_ignore", "count_accept", "count_played", "count_completed",
    "any_accept_or_better", "any_played_or_better", "any_completed",
    "exposure_span_seconds",
    # Optional diagnostics if you later include them in features:
    "window_used", "widen_step_index", "producer_rank",
}


def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _as_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y", "t"}


def _as_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _as_float(x: Any) -> Optional[float]:
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


def _validate_row(row: Dict[str, Any], cfg: EvalConfig) -> bool:
    if not isinstance(row, dict):
        return False
    if cfg.strict_semantic_guard:
        _semantic_guard(row)

    # Minimal required fields for evaluation
    if not _norm_str(row.get("final_outcome")):
        return False

    # rank is optional, but if present must be parseable
    r = row.get("rank")
    if r is not None and _as_int(r) is None:
        return False

    return True


# ---------------------------------------------------------------------
# Metric computation (deterministic)
# ---------------------------------------------------------------------

def _rate(numer: int, denom: int) -> float:
    return float(numer) / float(denom) if denom > 0 else 0.0


def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / float(len(xs))


def _compute_core_metrics(rows: List[Dict[str, Any]], k_values: Tuple[int, ...]) -> Dict[str, Any]:
    total = len(rows)

    # Core booleans
    any_accept = sum(1 for r in rows if _as_bool(r.get("any_accept_or_better")))
    any_played = sum(1 for r in rows if _as_bool(r.get("any_played_or_better")))
    any_completed = sum(1 for r in rows if _as_bool(r.get("any_completed")))

    # Outcome score mean (if available)
    scores: List[float] = []
    for r in rows:
        sc = _as_float(r.get("outcome_score"))
        if sc is not None:
            scores.append(float(sc))
    mean_score = _mean(scores)

    metrics: Dict[str, Any] = {
        "total_items": total,
        "accept_or_better_rate": _rate(any_accept, total),
        "played_or_better_rate": _rate(any_played, total),
        "completed_rate": _rate(any_completed, total),
        "mean_outcome_score": mean_score,
    }

    # Rank-based metrics (accept@k, played@k, completed@k)
    # If rank missing, those rows are excluded from @k denominator
    for k in k_values:
        in_k = [r for r in rows if (_as_int(r.get("rank")) is not None and _as_int(r.get("rank")) <= k)]
        denom = len(in_k)
        acc_k = sum(1 for r in in_k if _as_bool(r.get("any_accept_or_better")))
        play_k = sum(1 for r in in_k if _as_bool(r.get("any_played_or_better")))
        comp_k = sum(1 for r in in_k if _as_bool(r.get("any_completed")))

        metrics[f"accept_at_{k}"] = _rate(acc_k, denom)
        metrics[f"played_at_{k}"] = _rate(play_k, denom)
        metrics[f"completed_at_{k}"] = _rate(comp_k, denom)
        metrics[f"items_with_rank_le_{k}"] = denom

    return metrics


def _compute_deltas(curr: Dict[str, Any], base: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute numeric deltas for shared numeric keys.
    """
    deltas: Dict[str, Any] = {}
    for k, v in curr.items():
        if isinstance(v, (int, float)) and isinstance(base.get(k), (int, float)):
            deltas[k] = float(v) - float(base[k])
    return deltas


def _apply_regression_guards(
    *,
    curr: Dict[str, Any],
    base: Dict[str, Any],
    cfg: EvalConfig,
    total_rows_used: int,
) -> Tuple[bool, List[str]]:
    """
    Enforce regression guards on key rates only.
    """
    if total_rows_used < cfg.min_rows_for_guards:
        # Not enough data to enforce; pass but record reason
        return True, [f"guard_skipped_insufficient_rows:{total_rows_used}<{cfg.min_rows_for_guards}"]

    reasons: List[str] = []

    def check(key: str, min_delta: float, max_drop: float) -> None:
        if key not in curr or key not in base:
            return
        c = curr[key]
        b = base[key]
        if not isinstance(c, (int, float)) or not isinstance(b, (int, float)):
            return
        d = float(c) - float(b)
        # Both min_delta and max_drop are supported; max_drop is an absolute negative bound.
        if d < min_delta:
            reasons.append(f"delta_below_min:{key}:{d:.4f}<{min_delta:.4f}")
        if d < -abs(max_drop):
            reasons.append(f"drop_exceeds_max:{key}:{d:.4f}<-{abs(max_drop):.4f}")

    check("accept_or_better_rate", cfg.min_delta_accept_rate, cfg.max_drop_accept_rate)
    check("played_or_better_rate", cfg.min_delta_play_rate, cfg.max_drop_play_rate)
    check("completed_rate", cfg.min_delta_complete_rate, cfg.max_drop_complete_rate)

    return (len(reasons) == 0), reasons


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def evaluate_selection_quality(
    feature_rows: Iterable[Dict[str, Any]],
    *,
    baseline_metrics: Optional[Dict[str, Any]] = None,
    config: EvalConfig = EvalConfig(),
) -> Dict[str, Any]:
    """
    Evaluate song recommendation selection quality from feature rows.

    Inputs:
    - feature_rows: output rows from Features Layer (selection_features.py)
    - baseline_metrics: optional dict from prior evaluation (for deltas + regression guards)

    Outputs:
      {
        "report": {...}  # EvalReport as dict
      }
    """
    cfg = config

    total_in = 0
    used = 0
    dropped = 0
    rows: List[Dict[str, Any]] = []

    for r in feature_rows:
        total_in += 1
        try:
            ok = _validate_row(r, cfg)
            if not ok:
                raise ValueError("invalid feature row")
        except Exception:
            dropped += 1
            if cfg.drop_invalid:
                continue
            raise
        rows.append(r)
        used += 1

    # Deterministic ordering (for auditability only; metrics are order-invariant)
    rows.sort(
        key=lambda x: (
            _norm_str(x.get("player_id")),
            _norm_str(x.get("game_id")),
            _norm_str(x.get("recommendation_set_id")),
            (_as_int(x.get("rank")) if _as_int(x.get("rank")) is not None else 10**9),
            _norm_str(x.get("song_id")),
        )
    )

    metrics = _compute_core_metrics(rows, cfg.k_values)

    deltas: Optional[Dict[str, Any]] = None
    guard_pass = True
    guard_fail_reasons: List[str] = []

    if isinstance(baseline_metrics, dict) and baseline_metrics:
        deltas = _compute_deltas(metrics, baseline_metrics)
        guard_pass, guard_fail_reasons = _apply_regression_guards(
            curr=metrics,
            base=baseline_metrics,
            cfg=cfg,
            total_rows_used=used,
        )

    report = EvalReport(
        total_rows_in=total_in,
        total_rows_used=used,
        total_rows_dropped=dropped,
        metrics=metrics,
        baseline_metrics=baseline_metrics if isinstance(baseline_metrics, dict) else None,
        deltas=deltas,
        guard_pass=guard_pass,
        guard_fail_reasons=guard_fail_reasons,
    )

    return {"report": asdict(report)}