"""
dataset_builder.py

Phase 5 – Offline Retrain dataset builder

Purpose:
- Convert curator-labeled review units into deterministic training dataset objects
- Keep runtime and completed phases untouched
- Align with:
  * curator_label.schema.json
  * training_dataset.schema.json
  * feedback aggregation / selection-level review units

Non-goals:
- No model training here
- No I/O or database access here
- No mutation of inputs
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Config / summary
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class DatasetBuilderConfig:
    """
    Controls dataset generation.

    include_model_reason:
        Include machine hypothesis alongside gold labels for later analysis.

    include_curator_metadata:
        Include comparison metadata (agreement / notes / curator id) in sample extras.

    require_curator_primary_reason:
        Drop items that do not provide a curator primary reason.

    allowed_primary_reasons:
        Optional allow-list for curator primary reasons.
        If empty, accept all reasons.

    label_schema_version:
        Written into the dataset top-level object.
    """
    include_model_reason: bool = True
    include_curator_metadata: bool = True
    require_curator_primary_reason: bool = True
    allowed_primary_reasons: Tuple[str, ...] = ()
    label_schema_version: str = "v1_full"


@dataclass(frozen=True)
class DatasetBuilderSummary:
    total_items_in: int
    total_samples_out: int
    total_items_dropped: int
    label_counts: Dict[str, int]
    agreement_counts: Dict[str, int]


# -----------------------------------------------------------------------------
# Helpers (pure)
# -----------------------------------------------------------------------------

def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _norm_opt_str(x: Any) -> Optional[str]:
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


def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _agreement_type(item: Dict[str, Any]) -> Optional[str]:
    judgement = _as_dict(item.get("judgement"))
    return _norm_opt_str(judgement.get("agreement_type"))


def _curator_reason(item: Dict[str, Any]) -> Dict[str, Any]:
    return _as_dict(item.get("curator_reason"))


def _model_reason(item: Dict[str, Any]) -> Dict[str, Any]:
    return _as_dict(item.get("model_reason"))


def _curator_primary_reason(item: Dict[str, Any]) -> Optional[str]:
    curator = _curator_reason(item)

    primary = _norm_opt_str(curator.get("primary_reason"))
    if primary:
        return primary

    codes = curator.get("reason_codes")
    if isinstance(codes, list) and codes:
        return _norm_opt_str(codes[0])

    return None


def _selection_features(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build deterministic offline features from a curator review unit.

    This expects the incoming item to already contain selection-level / aggregation
    fields such as:
    - player_id, game_id, recommendation_set_id, song_id
    - difficulty, rank, action
    - locale, tier_id, target_metric, catalog_fingerprint
    - derived_primary_reason / derived_reason_confidence (optional)
    """
    return {
        "game_id": _norm_str(item.get("game_id")),
        "song_id": _norm_str(item.get("song_id")),
        "difficulty": _norm_opt_str(item.get("difficulty")),
        "rank": _norm_int(item.get("rank")),
        "action": _norm_opt_str(item.get("action")),
        "locale": _norm_opt_str(item.get("locale")),
        "tier_id": _norm_opt_str(item.get("tier_id")),
        "target_metric": _norm_float(item.get("target_metric")),
        "catalog_fingerprint": _norm_opt_str(item.get("catalog_fingerprint")),
        "derived_primary_reason": _norm_opt_str(item.get("derived_primary_reason")),
        "derived_reason_confidence": _norm_float(item.get("derived_reason_confidence")),
        "recommendation_set_id": _norm_opt_str(item.get("recommendation_set_id")),
        "session_id": _norm_opt_str(item.get("session_id")),
    }


def _gold_labels(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert curator_reason into training_dataset.schema-compatible gold_labels.
    """
    curator = _curator_reason(item)
    if not curator:
        return []

    reason_codes = curator.get("reason_codes")
    if not isinstance(reason_codes, list):
        reason_codes = []

    gold = {
        "primary_reason": _norm_opt_str(curator.get("primary_reason")),
        "reason_codes": [str(x) for x in reason_codes],
        "category": _norm_opt_str(curator.get("category")),
        "layer": _norm_opt_str(curator.get("layer")),
        "plane": _norm_opt_str(curator.get("plane")),
        "decision_type": _norm_opt_str(curator.get("decision_type")),
        "cause_type": _norm_opt_str(curator.get("cause_type")),
        "signal_type": _norm_opt_str(curator.get("signal_type")),
    }

    return [gold]


def _source_timestamp(item: Dict[str, Any]) -> Optional[str]:
    return _norm_opt_str(item.get("timestamp"))


def _should_keep(item: Dict[str, Any], cfg: DatasetBuilderConfig) -> bool:
    primary = _curator_primary_reason(item)

    if cfg.require_curator_primary_reason and not primary:
        return False

    if cfg.allowed_primary_reasons:
        if primary not in set(cfg.allowed_primary_reasons):
            return False

    return True


def _sample_extras(item: Dict[str, Any], cfg: DatasetBuilderConfig) -> Dict[str, Any]:
    """
    Optional extra fields beyond the minimum required by training_dataset.schema.json.

    The current schema does not forbid additional properties, so these can be
    retained for analysis / evaluation.
    """
    extras: Dict[str, Any] = {}

    if cfg.include_model_reason:
        model = _model_reason(item)
        extras["model_reason"] = {
            "reason_codes": model.get("reason_codes") if isinstance(model.get("reason_codes"), list) else [],
            "primary_reason": _norm_opt_str(model.get("primary_reason")),
            "confidence": _norm_float(model.get("confidence")),
        }

    if cfg.include_curator_metadata:
        judgement = _as_dict(item.get("judgement"))
        extras["curator_metadata"] = {
            "agreement_type": _norm_opt_str(judgement.get("agreement_type")),
            "is_correct": judgement.get("is_correct") if isinstance(judgement.get("is_correct"), bool) else None,
            "severity": _norm_opt_str(judgement.get("severity")),
            "notes": _norm_opt_str(item.get("notes")),
            "curator_id": _norm_opt_str(item.get("curator_id")),
            "timestamp": _norm_opt_str(item.get("timestamp")),
            "event_id": _norm_opt_str(item.get("event_id")),
            "curation_id": _norm_opt_str(item.get("curation_id")),
        }

    return extras


def _make_sample(item: Dict[str, Any], cfg: DatasetBuilderConfig) -> Dict[str, Any]:
    sample: Dict[str, Any] = {
        "provenance_id": _norm_str(item.get("provenance_id")),
        "features": _selection_features(item),
        "gold_labels": _gold_labels(item),
    }

    extras = _sample_extras(item, cfg)
    if extras:
        sample.update(extras)

    return sample


def _compute_source_range(items: List[Dict[str, Any]]) -> Dict[str, str]:
    timestamps = [
        ts for ts in (_source_timestamp(item) for item in items)
        if ts
    ]

    if not timestamps:
        now = _utc_now_iso()
        return {
            "from": now,
            "to": now,
        }

    return {
        "from": min(timestamps),
        "to": max(timestamps),
    }


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def build_training_dataset(
    items: Iterable[Dict[str, Any]],
    *,
    dataset_id: Optional[str] = None,
    created_at: Optional[str] = None,
    config: DatasetBuilderConfig = DatasetBuilderConfig(),
) -> Dict[str, Any]:
    """
    Convert curator-reviewed items into a training_dataset.schema-compatible object.

    Input expectation
    -----------------
    Each item should be a curator review unit aligned to curator_label.schema.json,
    and may additionally include selection-level aggregation fields.

    Output shape
    ------------
    {
      "dataset_id": "...",
      "created_at": "...",
      "source_range": {"from": "...", "to": "..."},
      "label_schema_version": "...",
      "samples": [...],
      "summary": {...}   # extra helper block, optional for downstream usage
    }
    """
    accepted_items: List[Dict[str, Any]] = []
    total_in = 0
    total_dropped = 0
    label_counts: Dict[str, int] = {}
    agreement_counts: Dict[str, int] = {}

    for item in items:
        total_in += 1

        if not isinstance(item, dict):
            total_dropped += 1
            continue

        if not _should_keep(item, config):
            total_dropped += 1
            continue

        accepted_items.append(item)

        label = _curator_primary_reason(item)
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1

        agreement = _agreement_type(item)
        if agreement:
            agreement_counts[agreement] = agreement_counts.get(agreement, 0) + 1

    samples = [_make_sample(item, config) for item in accepted_items]

    summary = DatasetBuilderSummary(
        total_items_in=total_in,
        total_samples_out=len(samples),
        total_items_dropped=total_dropped,
        label_counts=label_counts,
        agreement_counts=agreement_counts,
    )

    dataset = {
        "dataset_id": dataset_id or "phase5_training_dataset",
        "created_at": created_at or _utc_now_iso(),
        "source_range": _compute_source_range(accepted_items),
        "label_schema_version": config.label_schema_version,
        "samples": samples,

        # optional helper block for analysis / orchestration
        "summary": asdict(summary),
    }

    return dataset


__all__ = [
    "DatasetBuilderConfig",
    "DatasetBuilderSummary",
    "build_training_dataset",
]