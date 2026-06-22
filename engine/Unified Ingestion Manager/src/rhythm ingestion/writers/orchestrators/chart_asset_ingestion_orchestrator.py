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

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


# --------------------------------------------------
# Imports (Phase 3.5-safe: canonical absolute + package relative)
# --------------------------------------------------
try:
    # --------------------------------------------------
    # Canonical absolute imports
    # --------------------------------------------------
    from rhythm_ingestion.writers.classifiers.chart_asset_classifier import (
        classify_chart_asset_candidate,
    )
    from rhythm_ingestion.writers.validators.validation.chart_asset_validator import (
        validate_chart_asset_candidate,
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
    # --------------------------------------------------
    # Package-relative imports
    # chart_asset_ingestion_orchestrator.py is under:
    # writers/orchestrators/
    # so siblings are reachable with ..
    # --------------------------------------------------
    try:
        from ..classifiers.chart_asset_classifier import (
            classify_chart_asset_candidate,
        )
        from ..validators.validation.chart_asset_validator import (
            validate_chart_asset_candidate,
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

@dataclass
class IngestionItemResult:
    source_path: Optional[str] = None
    reference_url: Optional[str] = None
    asset_id: Optional[str] = None
    asset_type: Optional[str] = None
    asset_subtype: Optional[str] = None
    status: str = "unknown"     # persisted / skipped / failed
    fatal_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_identity: Dict[str, Any] = field(default_factory=dict)
    classification: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionSummary:
    total_candidates: int = 0
    persisted_assets: int = 0
    skipped_assets: int = 0
    failed_assets: int = 0
    db_path: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


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

    out.setdefault("game_normalized", norm.get("game"))
    out.setdefault("difficulty_normalized", norm.get("difficulty"))
    out.setdefault("level_normalized", norm.get("level"))
    out.setdefault("normalization_issues", norm.get("issues") or [])

    return out


def ingest_single_chart_asset_candidate(candidate: Dict[str, Any]) -> IngestionItemResult:
    """
    Build (but do not persist) a single chart asset candidate.
    Returns detailed item result including validation state.
    """
    cand = _augment_with_normalized_identity(candidate)

    candidate_validation = validate_chart_asset_candidate(cand)
    classification = candidate_validation.classification or {}

    result = IngestionItemResult(
        source_path=_to_text(cand.get("source_path")) or None,
        reference_url=_to_text(cand.get("reference_url")) or None,
        status="skipped" if not candidate_validation.is_valid else "pending",
        fatal_errors=list(candidate_validation.fatal_errors),
        warnings=list(candidate_validation.warnings),
        normalized_identity={
            "game_normalized": cand.get("game_normalized"),
            "difficulty_normalized": cand.get("difficulty_normalized"),
            "level_normalized": cand.get("level_normalized"),
            "normalization_issues": cand.get("normalization_issues") or [],
        },
        classification=classification,
    )

    if not candidate_validation.is_valid:
        return result

    # Build asset according to classification
    try:
        if classification.get("source_kind") == "external_reference":
            asset = build_chart_asset_from_reference(
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
        else:
            asset = build_chart_asset_from_file(
                Path(cand.get("source_path")),
                candidate_id=cand.get("candidate_id"),
                run_id=cand.get("run_id"),
                game_normalized=cand.get("game_normalized"),
                difficulty_normalized=cand.get("difficulty_normalized"),
                level_normalized=cand.get("level_normalized"),
                extra_metadata=cand.get("extra_metadata") or {},
            )

        asset_validation = validate_chart_asset(asset)

        result.asset_id = asset.asset_id
        result.asset_type = asset.asset_type
        result.asset_subtype = asset.asset_subtype
        result.warnings.extend(asset_validation.warnings)

        if not asset_validation.is_valid:
            result.status = "failed"
            result.fatal_errors.extend(asset_validation.fatal_errors)
            return result

        # stash built asset inside classification bucket for later persistence
        result.classification["_built_asset"] = asset
        result.status = "built"
        return result

    except Exception as e:
        result.status = "failed"
        result.fatal_errors.append(f"{type(e).__name__}: {e}")
        return result


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

        # mark built items as persisted
        for r in item_results:
            if r.status == "built":
                r.status = "persisted"

    # remove internal built-asset object from output
    cleaned_results = []
    for r in item_results:
        c = dict(r.classification)
        c.pop("_built_asset", None)
        r.classification = c
        cleaned_results.append(r.as_dict())

    return {
        "summary": summary.as_dict(),
        "items": cleaned_results,
    }


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