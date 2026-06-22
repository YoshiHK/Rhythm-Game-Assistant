from __future__ import annotations

"""
reference_asset_validator.py

Reference-asset-specific validation for type_B chart assets.

Scope
-----
- validate reference-only candidates before ingestion
- validate reference-only ChartAsset objects before persistence / verification
- stays local (validation only), not system-level verification

What this covers
----------------
- external URLs (e.g. YouTube / external pages)
- local reference file paths (e.g. video clips stored as reference assets)
- type_B structural correctness

What this does NOT do
---------------------
- network reachability checks
- media decoding
- video analysis
- persistence
"""

from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.classifiers.chart_asset_classifier import (
        classify_chart_asset_candidate,
    )
    from rhythm_ingestion.writers.models.chart_asset_model import ChartAsset
    from rhythm_ingestion.writers.validators.chart_asset_validator import ValidationResult
    from rhythm_ingestion.writers.converters.chart_text_converter import (
        VIDEO_EXTENSIONS,
        classify_asset_subtype,
    )
except ImportError:
    try:
        from ..classifiers.chart_asset_classifier import classify_chart_asset_candidate
        from ..models.chart_asset_model import ChartAsset
        from .chart_asset_validator import ValidationResult
        from ..converters.chart_text_converter import VIDEO_EXTENSIONS, classify_asset_subtype
    except Exception:
        from chart_asset_classifier import classify_chart_asset_candidate
        from chart_asset_model import ChartAsset
        from chart_asset_validator import ValidationResult
        from chart_text_converter import VIDEO_EXTENSIONS, classify_asset_subtype


SUPPORTED_REFERENCE_SUBTYPES = {
    "youtube",
    "video_file",
    "external_url",
}


def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_url(value: Any) -> bool:
    s = _to_text(value)
    return s.startswith("http://") or s.startswith("https://")


def _looks_local_path(value: Any) -> bool:
    s = _to_text(value)
    if not s:
        return False
    if _is_url(s):
        return False
    # tolerate Windows and POSIX-like paths
    return any(token in s for token in (":\\", "/", "\\")) or Path(s).suffix != ""


def _is_youtube_url(value: Any) -> bool:
    s = _to_text(value)
    if not _is_url(s):
        return False
    parsed = urlparse(s)
    host = (parsed.netloc or "").lower()
    return "youtube.com" in host or "youtu.be" in host


def _validate_reference_string(reference: str, *, subtype: Optional[str]) -> tuple[list[str], list[str]]:
    fatal_errors: list[str] = []
    warnings: list[str] = []

    ref = _to_text(reference)
    if not ref:
        fatal_errors.append("missing_reference_url")
        return fatal_errors, warnings

    inferred_subtype = subtype or classify_asset_subtype(ref)

    # URL-backed references
    if _is_url(ref):
        parsed = urlparse(ref)
        if not parsed.scheme or not parsed.netloc:
            fatal_errors.append("invalid_reference_url")
            return fatal_errors, warnings

        if inferred_subtype == "youtube":
            if not _is_youtube_url(ref):
                warnings.append("youtube_subtype_but_non_youtube_host")
        elif inferred_subtype == "external_url":
            # generic external URL; valid as long as URL shape is OK
            pass
        else:
            warnings.append("url_reference_with_unexpected_subtype")
        return fatal_errors, warnings

    # Local-file-backed references (e.g. video clip path stored as reference asset)
    if _looks_local_path(ref):
        p = Path(ref)
        ext = p.suffix.lower()

        if inferred_subtype == "video_file":
            if ext not in VIDEO_EXTENSIONS:
                fatal_errors.append("video_file_reference_with_non_video_extension")
            if not p.exists():
                warnings.append("local_reference_path_not_found")
        else:
            # Still allow it, but make it visible
            warnings.append("local_reference_path_with_unexpected_subtype")
            if not p.exists():
                warnings.append("local_reference_path_not_found")
        return fatal_errors, warnings

    # Unknown string shape
    fatal_errors.append("unsupported_reference_format")
    return fatal_errors, warnings


def validate_reference_asset_candidate(candidate: Dict[str, Any]) -> ValidationResult:
    """
    Validate a candidate intended for type_B ingestion.

    This is stricter than generic candidate validation:
    - candidate must resolve to asset_type == type_B
    - must carry usable reference_url OR local video path source
    """
    classification = classify_chart_asset_candidate(candidate)
    fatal_errors: list[str] = []
    warnings: list[str] = []

    if not classification.is_supported:
        fatal_errors.extend(classification.reasons)

    if classification.asset_type != "type_B":
        fatal_errors.append("candidate_is_not_type_B")

    reference_url = _to_text(candidate.get("reference_url"))
    source_path = _to_text(candidate.get("source_path"))
    subtype = classification.asset_subtype

    # external ref path
    if classification.source_kind == "external_reference":
        errs, warns = _validate_reference_string(reference_url, subtype=subtype)
        fatal_errors.extend(errs)
        warnings.extend(warns)

    # local reference asset (e.g. video file)
    elif classification.source_kind == "local_file":
        if subtype == "video_file":
            errs, warns = _validate_reference_string(source_path, subtype=subtype)
            fatal_errors.extend(errs)
            warnings.extend(warns)
        else:
            # local file but classified as type_B in some other way
            errs, warns = _validate_reference_string(source_path or reference_url, subtype=subtype)
            fatal_errors.extend(errs)
            warnings.extend(warns)

    else:
        fatal_errors.append("unknown_reference_candidate_source_kind")

    # optional identity warnings
    if candidate.get("game_normalized") is None:
        warnings.append("missing_game_normalized")
    if candidate.get("difficulty_normalized") is None:
        warnings.append("missing_difficulty_normalized")
    if candidate.get("level_normalized") is None:
        warnings.append("missing_level_normalized")

    return ValidationResult(
        is_valid=(len(fatal_errors) == 0),
        fatal_errors=fatal_errors,
        warnings=warnings,
        classification=classification.as_dict(),
    )


def validate_reference_asset(asset: ChartAsset) -> ValidationResult:
    """
    Validate a built type_B ChartAsset.

    Rules:
    - asset_type must be type_B
    - reference_url must be present and structurally plausible
    - text_representation should normally be empty
    - subtype should be one of the known reference subtypes
    """
    fatal_errors: list[str] = []
    warnings: list[str] = []

    if asset.asset_type != "type_B":
        fatal_errors.append("asset_is_not_type_B")

    reference_url = _to_text(asset.reference_url)
    subtype = _to_text(asset.asset_subtype) or None

    errs, warns = _validate_reference_string(reference_url, subtype=subtype)
    fatal_errors.extend(errs)
    warnings.extend(warns)

    if asset.text_representation:
        warnings.append("type_B_asset_should_not_store_text_representation")

    if subtype and subtype not in SUPPORTED_REFERENCE_SUBTYPES:
        warnings.append("reference_asset_subtype_not_in_supported_reference_set")

    if not asset.game_normalized:
        warnings.append("missing_game_normalized")
    if not asset.difficulty_normalized:
        warnings.append("missing_difficulty_normalized")
    if asset.level_normalized is None:
        warnings.append("missing_level_normalized")

    return ValidationResult(
        is_valid=(len(fatal_errors) == 0),
        fatal_errors=fatal_errors,
        warnings=warnings,
        classification=None,
    )


__all__ = [
    "SUPPORTED_REFERENCE_SUBTYPES",
    "validate_reference_asset_candidate",
    "validate_reference_asset",
]
