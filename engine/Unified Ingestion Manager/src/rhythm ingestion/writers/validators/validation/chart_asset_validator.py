from __future__ import annotations

"""
chart_asset_validator.py

Validation layer for chart assets and chart-asset candidates.

Scope
-----
- validate candidate shape before ingestion
- validate ChartAsset before persistence
- keep identity issues visible but non-destructive when possible
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


# --------------------------------------------------
# Imports (Phase 3.5-safe: canonical + relative)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.classifiers.chart_asset_classifier import (
        ChartAssetClassification,
        classify_chart_asset_candidate,
    )
    from rhythm_ingestion.writers.models.chart_asset_model import (
        ChartAsset,
    )

except ImportError:
    try:
        from ...classifiers.chart_asset_classifier import (
            ChartAssetClassification,
            classify_chart_asset_candidate,
        )
        from ...models.chart_asset_model import (
            ChartAsset,
        )

    except ImportError as e:
        raise RuntimeError(
            "chart_asset_validator import dependencies failed.\n"
            "Expected modules:\n"
            "  - rhythm_ingestion.writers.classifiers.chart_asset_classifier\n"
            "  - rhythm_ingestion.writers.models.chart_asset_model\n\n"
            "Please verify:\n"
            "- package structure follows Phase 3.5 layout\n"
            "- PYTHONPATH includes src/\n"
            "- no legacy flat imports remain\n"
        ) from e


@dataclass
class ValidationResult:
    is_valid: bool
    fatal_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    classification: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def validate_chart_asset_candidate(candidate: Dict[str, Any]) -> ValidationResult:
    """
    Validate candidate input before conversion/persistence.

    Philosophy:
    - block only truly invalid / unsupported assets
    - keep normalization issues as warnings, not fatal, because
      asset storage may still be useful even with incomplete identity
    """
    classification = classify_chart_asset_candidate(candidate)
    fatal_errors: list[str] = []
    warnings: list[str] = []

    if not classification.is_supported:
        fatal_errors.extend(classification.reasons)

    # local file existence check
    source_path = _to_text(candidate.get("source_path"))
    if classification.source_kind == "local_file":
        if not source_path:
            fatal_errors.append("missing_source_path")
        elif not Path(source_path).exists():
            fatal_errors.append("source_path_not_found")

    # external ref validation
    reference_url = _to_text(candidate.get("reference_url"))
    if classification.source_kind == "external_reference" and not reference_url:
        fatal_errors.append("missing_reference_url")

    # normalization issues should be visible but not automatically fatal
    norm_issues = candidate.get("normalization_issues") or candidate.get("issues") or []
    if isinstance(norm_issues, list):
        warnings.extend(str(x) for x in norm_issues if x)

    # optional identity completeness warnings
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


def validate_chart_asset(asset: ChartAsset) -> ValidationResult:
    """
    Validate a built ChartAsset before writing to DB.
    """
    fatal_errors: list[str] = []
    warnings: list[str] = []

    try:
        asset.validate()
    except Exception as e:
        fatal_errors.append(f"{type(e).__name__}: {e}")

    if asset.asset_type == "type_A" and not asset.content_sha256:
        fatal_errors.append("missing_content_sha256_for_type_A")

    if asset.asset_type == "type_B" and not asset.reference_url:
        fatal_errors.append("missing_reference_url_for_type_B")

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
    "ValidationResult",
    "validate_chart_asset_candidate",
    "validate_chart_asset",
]