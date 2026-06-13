from pathlib import Path
from writers import load_phase5_features

DEFAULT_CHART_PATTERN_DB = Path("chart_patterns.db")

def hydrate_phase5_context_with_chart_features(
    phase5_context: dict,
    *,
    chart_id: str | None,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_CHART_PATTERN_DB,
) -> dict:
    if not chart_id:
        phase5_context["chart_pattern_features"] = {}
        return phase5_context

    features = load_phase5_features(
        chart_id,
        extraction_version=extraction_version,
        db_path=db_path,
    )

    phase5_context["chart_pattern_features"] = features or {}
    return phase5_context
