from __future__ import annotations

"""
chart_asset_ingestion_orchestrator.py

End-to-end orchestration for chart asset ingestion:

scan/file/reference candidate
    -> classify
    -> normalize identity
    -> validate candidate
    -> convert/build asset
    -> validate asset
    -> persist asset(s)

Scope
-----
- orchestration only
- no completed-phase mutation
- supports both local files and external references
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# --------------------------------------------------
# Imports (Phase 3.5-safe: canonical absolute + package relative)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.classifiers.chart_asset_classifier import (
        classify_chart_asset_candidate,
    )
    from rhythm_ingestion.writers.validators.validation.chart_asset_validator import (
        validate_chart_asset_candidate,
        validate_chart_asset,
    )
    from rhythm_ingestion.writers.normalizers.identity_normalizer import (
        normalize_folder_identity,
    )
    from rhythm_ingestion.writers.persistence.chart_asset_writer import (
        DEFAULT_CHART_ASSET_DB_PATH,
        build_chart_asset_from_file,
        build_chart_asset_from_reference,
        persist_chart_assets,
    )

except ImportError:
    try:
        from ..classifiers.chart_asset_classifier import (
            classify_chart_asset_candidate,
        )
        from ..validators.validation.chart_asset_validator import (
            validate_chart_asset_candidate,
            validate_chart_asset,
        )
        from ..normalizers.identity_normalizer import (
            normalize_folder_identity,
        )
        from ..persistence.chart_asset_writer import (
            DEFAULT_CHART_ASSET_DB_PATH,
            build_chart_asset_from_file,
            build_chart_asset_from_reference,
            persist_chart_assets,
        )
    except ImportError as e:
        raise RuntimeError(
            "Failed to import chart asset orchestrator dependencies "
            "(classifiers / validators / normalizers / persistence). "
            "Please verify writer-layer package structure and __init__.py wiring."
        ) from e


# --------------------------------------------------
# Results
# --------------------------------------------------
@dataclass
class IngestionItemResult:
    source_path: Optional[str] = None
    reference_url: Optional[str] = None
    asset_id: Optional[str] = None
    asset_type: Optional[str] = None
    asset_subtype: Optional[str] = None
    status: str = "unknown"   # pending / skipped / built / persisted / failed
    fatal_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_identity: Dict[str, Any] = field(default_factory=dict)
    classification: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionSummary:
    total_candidates: int = 0
    built_assets: int = 0
    persisted_assets: int = 0
    skipped_assets: int = 0
    failed_assets: int = 0
    db_path: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------
# Internal helpers
# --------------------------------------------------
def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _augment_with_normalized_identity(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure candidate carries normalized identity if raw folder fields exist.
    Non-destructive: preserves explicit normalized fields if already present.
    """
    out = dict(candidate)

    norm = normalize_folder_identity(
        game_folder=out.get("game_folder"),
        difficulty_folder=out.get("difficulty_folder"),
        level_folder=out.get("level_folder"),
    )

    if out.get("game_normalized") is None:
        out["game_normalized"] = norm.get("game")

    if out.get("difficulty_normalized") is None:
        out["difficulty_normalized"] = norm.get("difficulty")

    if out.get("level_normalized") is None:
        out["level_normalized"] = norm.get("level")

    existing_issues = _safe_list(out.get("normalization_issues"))
    new_issues = _safe_list(norm.get("issues"))
    merged_issues = existing_issues + [x for x in new_issues if x not in existing_issues]
    out["normalization_issues"] = merged_issues

    return out


def _augment_with_classification(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure candidate carries classification metadata.
    Non-destructive: candidate keys remain authoritative if already present.
    """
    out = dict(candidate)

    classification = _safe_dict(classify_chart_asset_candidate(out))
    for k, v in classification.items():
        out.setdefault(k, v)

    # keep a stable nested copy for reporting
    out["_classification"] = classification
    return out


def _build_asset_from_candidate(
    cand: Dict[str, Any],
    classification: Dict[str, Any],
):
    """
    Build asset according to source classification.
    """
    source_kind = classification.get("source_kind") or cand.get("source_kind")

    if source_kind == "external_reference":
        return build_chart_asset_from_reference(
            reference_url=cand.get("reference_url"),
            candidate_id=cand.get("candidate_id"),
            run_id=cand.get("run_id"),
            game_normalized=cand.get("game_normalized"),
            difficulty_normalized=cand.get("difficulty_normalized"),
            level_normalized=cand.get("level_normalized"),
            source_path=cand.get("source_path"),
            basename=cand.get("basename"),
            extension=cand.get("extension"),
            extra_metadata=cand.get("extra_metadata") or {},
        )

    source_path = cand.get("source_path")
    if not source_path:
        raise ValueError("source_path is required for file-based asset build")

    return build_chart_asset_from_file(
        Path(source_path),
        candidate_id=cand.get("candidate_id"),
        run_id=cand.get("run_id"),
        game_normalized=cand.get("game_normalized"),
        difficulty_normalized=cand.get("difficulty_normalized"),
        level_normalized=cand.get("level_normalized"),
        extra_metadata=cand.get("extra_metadata") or {},
    )


# --------------------------------------------------
# Public item-level ingestion
# --------------------------------------------------
def ingest_single_chart_asset_candidate(candidate: Dict[str, Any]) -> IngestionItemResult:
    """
    Build (but do not persist) a single chart asset candidate.
    Returns detailed item result including validation/classification state.
    """
    # Step 1: normalize candidate identity
    cand = _augment_with_normalized_identity(candidate)

    # Step 2: classify candidate
    cand = _augment_with_classification(cand)
    classification = _safe_dict(cand.get("_classification"))

    # Step 3: validate candidate
    candidate_validation = validate_chart_asset_candidate(cand)

    result = IngestionItemResult(
        source_path=_to_text(cand.get("source_path")) or None,
        reference_url=_to_text(cand.get("reference_url")) or None,
        status="skipped" if not candidate_validation.is_valid else "pending",
        fatal_errors=list(_safe_list(getattr(candidate_validation, "fatal_errors", []))),
        warnings=list(_safe_list(getattr(candidate_validation, "warnings", []))),
        normalized_identity={
            "game_normalized": cand.get("game_normalized"),
            "difficulty_normalized": cand.get("difficulty_normalized"),
            "level_normalized": cand.get("level_normalized"),
            "normalization_issues": cand.get("normalization_issues") or [],
        },
        classification=classification,
    )

    # Merge any validator-side classification additions (if present)
    validator_classification = _safe_dict(getattr(candidate_validation, "classification", {}))
    if validator_classification:
        merged_classification = dict(classification)
        merged_classification.update(validator_classification)
        result.classification = merged_classification
        classification = merged_classification

    if not candidate_validation.is_valid:
        return result

    # Step 4: build asset according to classification
    try:
        asset = _build_asset_from_candidate(cand, classification)
    except Exception as e:
        result.status = "failed"
        result.fatal_errors.append(f"{type(e).__name__}: {e}")
        return result

    # Step 5: validate built asset
    try:
        asset_validation = validate_chart_asset(asset)
    except Exception as e:
        result.status = "failed"
        result.fatal_errors.append(f"{type(e).__name__}: {e}")
        return result

    result.asset_id = getattr(asset, "asset_id", None)
    result.asset_type = getattr(asset, "asset_type", None)
    result.asset_subtype = getattr(asset, "asset_subtype", None)
    result.warnings.extend(_safe_list(getattr(asset_validation, "warnings", [])))

    if not asset_validation.is_valid:
        result.status = "failed"
        result.fatal_errors.extend(_safe_list(getattr(asset_validation, "fatal_errors", [])))
        return result

    # Step 6: stash asset for batch persistence
    result.classification["_built_asset"] = asset
    result.status = "built"
    return result


# --------------------------------------------------
# Batch ingestion
# --------------------------------------------------
def ingest_chart_assets(
    *,
    candidates: Sequence[Dict[str, Any]],
    db_path: Path = DEFAULT_CHART_ASSET_DB_PATH,
) -> Dict[str, Any]:
    """
    Full ingestion:
    - build/validate all assets
    - persist all valid built assets
    """
    item_results: List[IngestionItemResult] = []
    built_assets = []

    for cand in candidates:
        r = ingest_single_chart_asset_candidate(cand)
        item_results.append(r)

        built = r.classification.get("_built_asset")
        if built is not None and r.status == "built":
            built_assets.append(built)

    summary = IngestionSummary(
        total_candidates=len(candidates),
        built_assets=len(built_assets),
        persisted_assets=0,
        skipped_assets=sum(1 for r in item_results if r.status == "skipped"),
        failed_assets=sum(1 for r in item_results if r.status == "failed"),
        db_path=str(db_path),
    )

    if built_assets:
        db_result = persist_chart_assets(
            db_path=db_path,
            assets=built_assets,
        )
        summary.persisted_assets = int(db_result.get("rows_written") or 0)

        for r in item_results:
            if r.status == "built":
                r.status = "persisted"

    # remove internal built-asset object from outward-facing results
    cleaned_results: List[Dict[str, Any]] = []
    for r in item_results:
        c = dict(r.classification)
        c.pop("_built_asset", None)
        r.classification = c
        cleaned_results.append(r.as_dict())

    return {
        "summary": summary.as_dict(),
        "items": cleaned_results,
    }


# --------------------------------------------------
# File-scan convenience wrapper
# --------------------------------------------------
def ingest_chart_assets_from_file_scan_candidates(
    *,
    db_path: Path,
    candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convenience wrapper for file_scan-style candidates.

    Expected candidate shape (minimal):
    {
        "candidate_id": ...,
        "run_id": ...,
        "source_path": ...,
        "basename": ...,
        "extension": ...,
        "game_folder": ...,
        "difficulty_folder": ...,
        "level_folder": ...,
        "game_normalized": ... (optional),
        "difficulty_normalized": ... (optional),
        "level_normalized": ... (optional),
        "normalization_issues": [...],   # optional
        "reference_url": ...              # optional for external refs
        "extra_metadata": {...}           # optional
    }
    """
    return ingest_chart_assets(
        candidates=candidates,
        db_path=db_path,
    )


__all__ = [
    "IngestionItemResult",
    "IngestionSummary",
    "ingest_single_chart_asset_candidate",
    "ingest_chart_assets",
    "ingest_chart_assets_from_file_scan_candidates",
]