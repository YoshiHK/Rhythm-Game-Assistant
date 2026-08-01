from __future__ import annotations

"""
chart_feature_bridge.py

Bridge layer that hydrates Phase 5 context with chart-pattern features
from chart_patterns.db via chart_pattern_reader.

Responsibilities
----------------
- Keep Phase 5 training / feature construction decoupled from DB access details
- Support normalized chart-id lookup for multi-game expansion
- Preserve deterministic, read-only behavior
- Expose stable hydration status fields for downstream consumers
- Wire song identity resolution through the resolver + reference reader stack

Notes
-----
- This is a wiring layer only
- This does NOT perform extraction
- This does NOT perform DB mutation
"""

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

# --------------------------------------------------
# Resolver bridge imports
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.bridges.song_identity_resolver import (
        build_default_song_catalog,
        resolve_song_identity,
    )
except ImportError:
    try:
        from .song_identity_resolver import (
            build_default_song_catalog,
            resolve_song_identity,
        )
    except ImportError:
        from song_identity_resolver import (
            build_default_song_catalog,
            resolve_song_identity,
        )

# --------------------------------------------------
# Pattern reader imports
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.readers.chart_pattern_reader import (
        DEFAULT_DB_PATH,
        DEFAULT_EXTRACTION_VERSION,
        DEFAULT_FALLBACK_VERSIONS,
        load_phase5_features,
        normalize_chart_id,
    )
except ImportError:
    try:
        from .chart_pattern_reader import (
            DEFAULT_DB_PATH,
            DEFAULT_EXTRACTION_VERSION,
            DEFAULT_FALLBACK_VERSIONS,
            load_phase5_features,
            normalize_chart_id,
        )
    except ImportError:
        from chart_pattern_reader import (
            DEFAULT_DB_PATH,
            DEFAULT_EXTRACTION_VERSION,
            DEFAULT_FALLBACK_VERSIONS,
            load_phase5_features,
            normalize_chart_id,
        )


DEFAULT_CHART_PATTERN_DB = DEFAULT_DB_PATH

# --------------------------------------------------
# Reference data paths
# --------------------------------------------------
DEFAULT_SONG_DB_EXPORT_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Song Database Export"
)

DEFAULT_SONG_INFO_SQLITE = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\data\reference\song_info.sqlite"
)

# --------------------------------------------------
# Lazy global song catalog cache
# --------------------------------------------------
_SONG_CATALOG = None


def _get_song_catalog():
    """
    Build a default song catalog lazily.

    Source priority:
    1. JSON export root
    2. song_info.sqlite (reference dataset) if present

    This remains read-only and deterministic.
    """
    global _SONG_CATALOG

    if _SONG_CATALOG is None:
        sqlite_path = DEFAULT_SONG_INFO_SQLITE if DEFAULT_SONG_INFO_SQLITE.exists() else None

        _SONG_CATALOG = build_default_song_catalog(
            export_root=DEFAULT_SONG_DB_EXPORT_ROOT,
            sqlite_path=sqlite_path,
            sqlite_default_game=None,
        )
  
    return build_default_song_catalog(
            export_root=DEFAULT_SONG_DB_EXPORT_ROOT,
            sqlite_path=sqlite_path
        )

def _stable_missing_features(
    *,
    normalized_chart_id: Optional[str],
    extraction_version: int,
) -> Dict[str, Any]:
    """
    Stable missing envelope for callers that expect chart-pattern keys
    to exist even when the chart is absent or unresolved.
    """
    return {
        "chart_id": normalized_chart_id,
        "requested_extraction_version": int(extraction_version),
        "resolved_extraction_version": None,
        "version_fallback_used": False,
        "has_chart_pattern_features": False,
        "chart_pattern_status": "MISSING",
        "chart_pattern_density": None,
        "chart_pattern_burst_density": None,
        "chart_pattern_stream_length_avg": None,
        "chart_pattern_jump_ratio": None,
        "chart_pattern_hold_complexity": None,
        "chart_pattern_section_variance": None,
        "chart_pattern_spike_count": None,
    }


def hydrate_phase5_context_with_chart_features(
    phase5_context: Dict[str, Any],
    *,
    chart_id: Optional[str] = None,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    song_name: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_CHART_PATTERN_DB,
    candidate_or_event: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Hydrate a Phase 5 context dict with chart-pattern features.

    Supported identity inputs:
    - chart_id directly
    - or normalized composite parts:
      game + song_id + difficulty (+ optional chart_type / level)

    Added context keys:
    - chart_pattern_features
    - chart_pattern_status
    - has_chart_pattern_features
    - chart_pattern_lookup

    This function mutates and returns phase5_context to preserve the
    original lightweight bridge-style calling contract.
    """
    # --------------------------------------------------
    # Build resolver input
    # --------------------------------------------------
    resolver_meta: Dict[str, Any] = {}

    resolver_input: Dict[str, Any] = {}
    if isinstance(candidate_or_event, dict):
        resolver_input.update(candidate_or_event)

    if game is not None:
        resolver_input.setdefault("game_id", game)
        resolver_input.setdefault("game", game)

    if song_id is not None:
        resolver_input.setdefault("song_id", song_id)

    if song_name is not None:
        resolver_input.setdefault("song_name", song_name)

    if difficulty is not None:
        resolver_input.setdefault("difficulty", difficulty)

    if level is not None:
        resolver_input.setdefault("level", level)

    # ensure file_candidate carries song_name if present
    if song_name is not None:
        fc = resolver_input.get("file_candidate")
        if isinstance(fc, dict):
            fc = dict(fc)
            fc.setdefault("song_name", song_name)
            resolver_input["file_candidate"] = fc

    # --------------------------------------------------
    # Song identity resolution (wiring only)
    # --------------------------------------------------
    if (song_id is None or game is None or difficulty is None) and resolver_input:
        try:
            catalog = _get_song_catalog()
            resolved = resolve_song_identity(resolver_input, catalog)

            resolver_meta = {
                "resolver_used": True,

                # resolved identity
                "resolved_song_id": resolved.get("song_id"),
                "resolved_song_name": resolved.get("song_name"),
                "resolved_canonical_song_name": resolved.get("canonical_song_name"),
                "resolved_game": resolved.get("game"),
                "resolved_difficulty": resolved.get("difficulty"),
                "resolved_level": resolved.get("level"),

                # confidence / source
                "resolver_confidence": resolved.get("confidence"),
                "resolver_source": resolved.get("source"),

                # input tracing
                "input_song_name": resolved.get("input_song_name"),
                "input_song_id": resolved.get("input_song_id"),
                "input_game": resolved.get("input_game"),
                "input_difficulty": resolved.get("input_difficulty"),

                # success
                "resolved": resolved.get("resolved"),
            }

            # fill missing only
            game = game or resolved.get("game")
            song_id = song_id or resolved.get("song_id")
            song_name = song_name or resolved.get("song_name")
            difficulty = difficulty or resolved.get("difficulty")
            level = level or resolved.get("level")

        except Exception as e:
            resolver_meta = {
                "resolver_used": True,
                "resolver_error": f"{type(e).__name__}: {e}",
            }

    # --------------------------------------------------
    # Chart ID normalization
    # --------------------------------------------------
    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )

    # --------------------------------------------------
    # Expose lookup metadata
    # --------------------------------------------------
    phase5_context["chart_pattern_lookup"] = {
        "requested_chart_id": chart_id,
        "normalized_chart_id": normalized_chart_id,
        "game": game,
        "song_id": song_id,
        "song_name": song_name,
        "difficulty": difficulty,
        "chart_type": chart_type,
        "level": level,
        "requested_extraction_version": int(extraction_version),
        "fallback_versions": [int(v) for v in fallback_versions],
        "db_path": str(db_path),
        "resolver": resolver_meta,
    }

    # --------------------------------------------------
    # Stable missing path if unresolved
    # --------------------------------------------------
    if not normalized_chart_id:
        features = _stable_missing_features(
            normalized_chart_id=None,
            extraction_version=extraction_version,
        )
        phase5_context["chart_pattern_features"] = features
        phase5_context["chart_pattern_status"] = features["chart_pattern_status"]
        phase5_context["has_chart_pattern_features"] = features["has_chart_pattern_features"]
        return phase5_context

    # --------------------------------------------------
    # Load chart-pattern features
    # --------------------------------------------------
    features = load_phase5_features(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
        extraction_version=extraction_version,
        fallback_versions=fallback_versions,
        db_path=db_path,
    )

    if not isinstance(features, dict):
        features = _stable_missing_features(
            normalized_chart_id=normalized_chart_id,
            extraction_version=extraction_version,
        )
    else:
        features = {
            "chart_id": features.get("chart_id", normalized_chart_id),
            "requested_extraction_version": features.get(
                "requested_extraction_version",
                int(extraction_version),
            ),
            "resolved_extraction_version": features.get("resolved_extraction_version"),
            "version_fallback_used": bool(
                features.get("version_fallback_used", False)
            ),
            "has_chart_pattern_features": bool(
                features.get("has_chart_pattern_features", False)
            ),
            "chart_pattern_status": features.get(
                "chart_pattern_status",
                "VALID" if features.get("has_chart_pattern_features") else "MISSING",
            ),
            "chart_pattern_density": features.get("chart_pattern_density"),
            "chart_pattern_burst_density": features.get("chart_pattern_burst_density"),
            "chart_pattern_stream_length_avg": features.get("chart_pattern_stream_length_avg"),
            "chart_pattern_jump_ratio": features.get("chart_pattern_jump_ratio"),
            "chart_pattern_hold_complexity": features.get("chart_pattern_hold_complexity"),
            "chart_pattern_section_variance": features.get("chart_pattern_section_variance"),
            "chart_pattern_spike_count": features.get("chart_pattern_spike_count"),

            # optional identity metadata
            "game": features.get("game", game),
            "song_id": features.get("song_id", song_id),
            "difficulty": features.get("difficulty", difficulty),
            "chart_type": features.get("chart_type", chart_type),
            "level": features.get("level", level),
            "source_file_hash": features.get("source_file_hash"),
            "computed_at": features.get("computed_at"),
            "updated_at": features.get("updated_at"),
        }

    phase5_context["chart_pattern_features"] = features
    phase5_context["chart_pattern_status"] = features["chart_pattern_status"]
    phase5_context["has_chart_pattern_features"] = features["has_chart_pattern_features"]

    return phase5_context


def build_chart_pattern_feature_payload(
    *,
    chart_id: Optional[str] = None,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    song_name: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_CHART_PATTERN_DB,
    candidate_or_event: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience helper for callers that only want the hydrated payload
    without mutating an existing context dict.
    """
    ctx: Dict[str, Any] = {}
    hydrate_phase5_context_with_chart_features(
        ctx,
        chart_id=chart_id,
        game=game,
        song_id=song_id,
        song_name=song_name,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
        extraction_version=extraction_version,
        fallback_versions=fallback_versions,
        db_path=db_path,
        candidate_or_event=candidate_or_event,
    )
    return ctx


__all__ = [
    "DEFAULT_CHART_PATTERN_DB",
    "DEFAULT_SONG_DB_EXPORT_ROOT",
    "DEFAULT_SONG_INFO_SQLITE",
    "hydrate_phase5_context_with_chart_features",
    "build_chart_pattern_feature_payload",
]