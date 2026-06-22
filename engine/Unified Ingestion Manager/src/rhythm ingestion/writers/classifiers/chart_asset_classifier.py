from __future__ import annotations

"""
chart_asset_classifier.py

Classify candidate chart assets into:
- type_A: deterministic / embeddable assets
- type_B: reference / external assets

Scope
-----
- classification only
- no persistence
- no conversion
- no DB writes
"""

# NOTE:
# Extensions like ".json" are shared across multiple games.
# Game identity must NOT be inferred from extension.
# Use folder normalization / identity resolution instead.

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

# --------------------------------------------------
# Chart extension registry (Phase-safe, classifier-only)
# --------------------------------------------------

# deterministic / chart-like formats (type_A candidates)
CHART_FILE_EXTENSIONS = {
    # core formats
    ".aff",        # Arcaea
    ".sus",        # SUS / Yumesute
    ".json",       # generic / schema
    ".txt",        # various chart dumps

    # HTML-like (fallback / scraped)
    ".html",
    ".htm",
    ".mht",
    ".mhtml",

    # rhythm game specific
    ".c2s",        # CHUNITHM
    ".maidata",    # maimai legacy
    ".maidata.txt",
    ".xml",        # Dynamix / others
    ".ogkr",       # Ongeki
}

# reference / non-deterministic inputs (type_B candidates)
REFERENCE_FILE_EXTENSIONS = {
    # video
    ".mp4",
    ".webm",
    ".mkv",
    ".avi",
    ".mov",

    # link-like files (future support)
    ".url",
    ".webloc",
}

# --------------------------------------------------
# Imports (Phase 3.5-safe: canonical + relative)
# --------------------------------------------------
try:
    # ✅ Canonical absolute import (preferred)
    from rhythm_ingestion.writers.converters.chart_text_converter import (
        classify_asset_type,
        classify_asset_subtype,
        SUPPORTED_TEXT_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )

except ImportError:
    try:
        from ..converters.chart_text_converter import (
            classify_asset_type,
            classify_asset_subtype,
            SUPPORTED_TEXT_EXTENSIONS,
            VIDEO_EXTENSIONS,
        )

    except ImportError as e:
        # ❗ Hard fail (no flat fallback)
        raise RuntimeError(
            "chart_text_converter import failed.\n"
            "Expected module path:\n"
            "  rhythm_ingestion.writers.converters.chart_text_converter\n\n"
            "Please verify:\n"
            "- writers/converters/chart_text_converter.py exists\n"
            "- PYTHONPATH includes src/\n"
            "- package structure follows Phase 3.5 layout\n"
        ) from e


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
IGNORED_EXTENSIONS = {
    ".osr",   # replay-ish examples
    ".rpl",
    ".rep",
    ".log",
    ".csv",
}


@dataclass
class ChartAssetClassification:
    source_kind: str                      # local_file / external_reference / unknown
    asset_type: Optional[str]             # type_A / type_B / None
    asset_subtype: Optional[str]          # aff / sus / json / youtube / video_file / ...
    is_supported: bool
    source_path: Optional[str] = None
    reference_url: Optional[str] = None
    extension: Optional[str] = None
    basename: Optional[str] = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_url(value: Any) -> bool:
    s = _to_text(value)
    return s.startswith("http://") or s.startswith("https://")


def classify_chart_asset_candidate(candidate: Dict[str, Any]) -> ChartAssetClassification:
    """
    Classify an asset candidate from either:
    - local file path (source_path)
    - external reference (reference_url)
    """
    source_path = _to_text(candidate.get("source_path"))
    reference_url = _to_text(candidate.get("reference_url"))

    if reference_url and _is_url(reference_url):
        subtype = classify_asset_subtype(reference_url)
        asset_type = classify_asset_type(reference_url)

        return ChartAssetClassification(
            source_kind="external_reference",
            asset_type=asset_type,
            asset_subtype=subtype,
            is_supported=(asset_type == "type_B"),
            source_path=source_path or None,
            reference_url=reference_url,
            extension=Path(reference_url).suffix.lower() or None,
            basename=Path(reference_url).name or None,
            reasons=[] if asset_type == "type_B" else ["unsupported_external_reference"],
        )

    if source_path:
        p = Path(source_path)
        ext = p.suffix.lower()
        subtype = classify_asset_subtype(p)
        asset_type = classify_asset_type(p)

        # explicitly unsupported / ignored
        if ext in IMAGE_EXTENSIONS:
            return ChartAssetClassification(
                source_kind="local_file",
                asset_type=None,
                asset_subtype=None,
                is_supported=False,
                source_path=source_path,
                reference_url=None,
                extension=ext,
                basename=p.name,
                reasons=["image_assets_not_in_core_chart_asset_flow"],
            )

        if ext in IGNORED_EXTENSIONS:
            return ChartAssetClassification(
                source_kind="local_file",
                asset_type=None,
                asset_subtype=None,
                is_supported=False,
                source_path=source_path,
                reference_url=None,
                extension=ext,
                basename=p.name,
                reasons=["ignored_asset_type"],
            )

        # deterministic chart assets (type_A)
        if ext in CHART_FILE_EXTENSIONS:
            return ChartAssetClassification(
                source_kind="local_file",
                asset_type="type_A",
                asset_subtype=subtype,
                is_supported=True,
                source_path=source_path,
                reference_url=None,
                extension=ext,
                basename=p.name,
                reasons=[],
            )


        # reference / non-deterministic assets (type_B)
        if ext in REFERENCE_FILE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
            return ChartAssetClassification(
                source_kind="local_file",
                asset_type="type_B",
                asset_subtype=subtype,
                is_supported=True,
                source_path=source_path,
                reference_url=None,
                extension=ext,
                basename=p.name,
                reasons=[],
            )

        return ChartAssetClassification(
            source_kind="local_file",
            asset_type=None,
            asset_subtype=subtype,
            is_supported=False,
            source_path=source_path,
            reference_url=None,
            extension=ext,
            basename=p.name,
            reasons=["unsupported_extension"],
        )

    return ChartAssetClassification(
        source_kind="unknown",
        asset_type=None,
        asset_subtype=None,
        is_supported=False,
        source_path=None,
        reference_url=None,
        extension=None,
        basename=None,
        reasons=["missing_source_path_and_reference_url"],
    )


__all__ = [
    "ChartAssetClassification",
    "classify_chart_asset_candidate",
]
