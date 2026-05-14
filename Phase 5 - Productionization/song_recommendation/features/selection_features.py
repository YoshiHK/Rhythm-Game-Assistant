from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------
# Contracts / Config
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureConfig:
    """
    Feature construction config.

    Keep this layer purely mechanical and selection-level:
    - no semantics
    - no tips/taxonomy/severity fields
    """
    # Allowed outcomes (must match aggregation layer final_outcome values)
    allowed_outcomes: Tuple[str, ...] = ("ignore", "accept", "played", "completed")

    # Outcome -> numeric label (for offline calibration convenience)
    # completed > played > accept > ignore
    outcome_score: Dict[str, int] = None  # filled in __post_init__ style below

    # If True, reject any row containing forbidden semantic keys
    strict_semantic_guard: bool = True

    # If True, output only safe feature columns (whitelist)
    strict_safe_output: bool = True

    # If True, drop invalid rows instead of raising
    drop_invalid: bool = True


@dataclass(frozen=True)
class FeatureSummary:
    total_rows_in: int
    total_rows_used: int
    total_rows_dropped: int
    outcome_counts: Dict[str, int]


def _default_outcome_score() -> Dict[str, int]:
    return {"ignore": 0, "accept": 1, "played": 2, "completed": 3}


# ---------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------

_FORBIDDEN_SEMANTIC_KEYS = {
    # Any hint of Phase 1–4 semantics should never appear here
    "tips", "tip", "guidance", "narrative",
    "taxonomy", "severity", "element", "elements",
    "pattern_tags", "matched_tags", "training_items",
    "section_metrics", "sections",
    "analysis", "inference", "dominance",
}

# Whitelist of safe columns expected from aggregation output
_ALLOWED_INPUT_KEYS = {
    "player_id",
    "game_id",
    "recommendation_set_id",
    "song_id",
    "difficulty",
    "rank",
    "tier_id",
    "target_metric",
    "catalog_fingerprint",
    "locale",
    "session_id",
    "first_seen_utc",
    "last_seen_utc",
    "action_counts",
    "final_outcome",
}

# Whitelist of safe output feature columns
_ALLOWED_OUTPUT_KEYS = {
    # identity (kept for join/debug; may be dropped later by training code)
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

    # outcome labels
    "final_outcome",
    "outcome_score",

    # derived engagement features (selection-level)
    "count_ignore",
    "count_accept",
    "count_played",
    "count_completed",
    "any_accept_or_better",
    "any_played_or_better",
    "any_completed",

    # timing features (mechanical; optional)
    "exposure_span_seconds",
}


def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _norm_optional_str(x: Any) -> Optional[str]:
    s = _norm_str(x)
    return s if s else None


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


def _parse_iso8601(s: Any) -> Optional[datetime]:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _semantic_guard(row: Dict[str, Any]) -> None:
    # Reject forbidden keys (direct or nested shallow match)
    lowered = {str(k).strip().lower() for k in row.keys()}
    for bad in _FORBIDDEN_SEMANTIC_KEYS:
        if bad in lowered:
            raise ValueError(f"Semantic leakage detected: forbidden key '{bad}' present in row")


def _validate_row(row: Dict[str, Any], cfg: FeatureConfig) -> bool:
    if not isinstance(row, dict):
        return False

    if cfg.strict_semantic_guard:
        _semantic_guard(row)

    # Must have minimal identity
    required = ["player_id", "game_id", "recommendation_set_id", "song_id", "final_outcome"]
    for k in required:
        if not _norm_str(row.get(k)):
            return False

    out = _norm_str(row.get("final_outcome")).lower()
    if out not in cfg.allowed_outcomes:
        return False

    # action_counts must be dict-like
    ac = row.get("action_counts")
    if not isinstance(ac, dict):
        return False

    return True


def _safe_extract_action_counts(ac: Dict[str, Any]) -> Dict[str, int]:
    # Ensure stable presence of known action keys; ignore unknowns
    def as_int(v: Any) -> int:
        try:
            return int(v)
        except Exception:
            return 0

    return {
        "ignore": as_int(ac.get("ignore")),
        "accept": as_int(ac.get("accept")),
        "played": as_int(ac.get("played")),
        "completed": as_int(ac.get("completed")),
    }


def _compute_exposure_span_seconds(first_seen_utc: Any, last_seen_utc: Any) -> Optional[int]:
    a = _parse_iso8601(first_seen_utc)
    b = _parse_iso8601(last_seen_utc)
    if a is None or b is None:
        return None
    # Deterministic integer seconds (floor)
    delta = b - a
    return int(delta.total_seconds())


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def build_selection_feature_rows(
    aggregated_rows: Iterable[Dict[str, Any]],
    *,
    config: FeatureConfig = FeatureConfig(),
) -> Dict[str, Any]:
    """
    Convert aggregated selection-level rows -> feature rows.

    Input rows should come from the aggregation layer and be selection-level.
    Output rows are deterministic and safe for offline training/calibration.

    Returns:
      {
        "rows": [feature_row, ...],
        "summary": {...}
      }
    """
    cfg = config
    if cfg.outcome_score is None:
        # create default mapping without mutating dataclass
        outcome_score = _default_outcome_score()
    else:
        outcome_score = dict(cfg.outcome_score)

    total_in = 0
    used = 0
    dropped = 0
    outcome_counts: Dict[str, int] = {k: 0 for k in cfg.allowed_outcomes}

    out_rows: List[Dict[str, Any]] = []

    for row in aggregated_rows:
        total_in += 1
        try:
            ok = _validate_row(row, cfg)
            if not ok:
                raise ValueError("invalid aggregated row")
        except Exception:
            dropped += 1
            if cfg.drop_invalid:
                continue
            raise

        used += 1

        final_outcome = _norm_str(row.get("final_outcome")).lower()
        outcome_counts[final_outcome] = int(outcome_counts.get(final_outcome, 0)) + 1

        ac = _safe_extract_action_counts(row.get("action_counts", {}))

        feature: Dict[str, Any] = {
            # identity / join keys
            "player_id": _norm_str(row.get("player_id")),
            "game_id": _norm_str(row.get("game_id")),
            "recommendation_set_id": _norm_str(row.get("recommendation_set_id")),
            "song_id": _norm_str(row.get("song_id")),
            "difficulty": _norm_optional_str(row.get("difficulty")),
            "rank": _norm_int(row.get("rank")),

            # selection context
            "tier_id": _norm_optional_str(row.get("tier_id")),
            "target_metric": _norm_float(row.get("target_metric")),
            "catalog_fingerprint": _norm_optional_str(row.get("catalog_fingerprint")),
            "locale": _norm_optional_str(row.get("locale")),

            # labels
            "final_outcome": final_outcome,
            "outcome_score": int(outcome_score.get(final_outcome, 0)),

            # action counts
            "count_ignore": int(ac["ignore"]),
            "count_accept": int(ac["accept"]),
            "count_played": int(ac["played"]),
            "count_completed": int(ac["completed"]),

            # derived engagement flags
            "any_accept_or_better": bool(ac["accept"] > 0 or ac["played"] > 0 or ac["completed"] > 0),
            "any_played_or_better": bool(ac["played"] > 0 or ac["completed"] > 0),
            "any_completed": bool(ac["completed"] > 0),

            # deterministic timing feature (optional)
            "exposure_span_seconds": _compute_exposure_span_seconds(
                row.get("first_seen_utc"), row.get("last_seen_utc")
            ),
        }

        if cfg.strict_safe_output:
            feature = {k: feature.get(k) for k in _ALLOWED_OUTPUT_KEYS}

        out_rows.append(feature)

    # Deterministic output ordering for auditability
    out_rows.sort(
        key=lambda r: (
            r.get("player_id") or "",
            r.get("game_id") or "",
            r.get("recommendation_set_id") or "",
            (r.get("rank") if r.get("rank") is not None else 10**9),
            r.get("song_id") or "",
        )
    )

    summary = FeatureSummary(
        total_rows_in=total_in,
        total_rows_used=used,
        total_rows_dropped=dropped,
        outcome_counts=outcome_counts,
    )

    return {
        "rows": out_rows,
        "summary": asdict(summary),
    }