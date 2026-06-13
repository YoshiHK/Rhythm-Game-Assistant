"""
Writers layer (Phase 3)

This package provides output writers and readers for data persistence.

Design principles:
- Writers are stateless and deterministic
- Writers do NOT contain domain logic (no parsing / inference)
- Writers ONLY persist already-prepared data structures

Evolution:
- Phase 3: ExcelWriter
- Phase 7: chart_patterns DB (writer + reader)

This layer now acts as the data boundary for:
- chart capability persistence
- multi-game scalability
"""

# =========================================================
# Excel Writer (existing, keep stable)
# =========================================================
try:
    from .excel_writer import ExcelWriter  # type: ignore
except Exception:
    ExcelWriter = None


# =========================================================
# Chart Pattern Writer (Phase 7 extension)
# =========================================================
try:
    from .chart_pattern_writer import (
        ChartPatternRow,
        PatternFeatureRow,
        PatternBlobRow,
        ChartExtractionBundle,
        WriteSummary,
        ensure_chart_pattern_schema,
        write_chart_pattern_bundles,
        write_from_scan_inventory,
        iter_scan_inventory_candidates,
    )
except Exception:
    ChartPatternRow = None
    PatternFeatureRow = None
    PatternBlobRow = None
    ChartExtractionBundle = None
    WriteSummary = None
    ensure_chart_pattern_schema = None
    write_chart_pattern_bundles = None
    write_from_scan_inventory = None
    iter_scan_inventory_candidates = None


# =========================================================
# Chart Pattern Reader
# =========================================================
try:
    from .chart_pattern_reader import (
        get_chart_pattern,
        get_pattern_features,
        get_pattern_blobs,
        load_chart_capability_bundle,
        load_phase5_features,
    )
except Exception:
    get_chart_pattern = None
    get_pattern_features = None
    get_pattern_blobs = None
    load_chart_capability_bundle = None
    load_phase5_features = None


# =========================================================
# Public API
# =========================================================
__all__ = [
    # Excel
    "ExcelWriter",

    # Writer layer (DB persistence)
    "ChartPatternRow",
    "PatternFeatureRow",
    "PatternBlobRow",
    "ChartExtractionBundle",
    "WriteSummary",
    "ensure_chart_pattern_schema",
    "write_chart_pattern_bundles",
    "write_from_scan_inventory",
    "iter_scan_inventory_candidates",

    # Reader layer (DB access)
    "get_chart_pattern",
    "get_pattern_features",
    "get_pattern_blobs",
    "load_chart_capability_bundle",
    "load_phase5_features",
]