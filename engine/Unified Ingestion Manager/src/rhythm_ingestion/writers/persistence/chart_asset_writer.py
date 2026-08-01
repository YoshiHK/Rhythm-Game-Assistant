from __future__ import annotations

"""
chart_asset_writer.py

Persist chart assets into SQLite.

Scope
-----
- Stores canonical chart asset content / references
- Does NOT store personalization, localization, or rendered tips
- Supports type_A (embedded text) and type_B (reference) assets
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from rhythm_ingestion.writers.models.chart_asset_model import (
        ChartAsset,
        AssetType,
        utc_now_iso,
    )
except ImportError:
    try:
        from ..models.chart_asset_model import (
            ChartAsset,
            AssetType,
            utc_now_iso,
        )
    except ImportError as e:
        raise RuntimeError(
            "chart_asset_model import failed.\n"
            "Expected module path:\n"
            "  rhythm_ingestion.writers.models.chart_asset_model\n\n"
            "Please verify:\n"
            "- writers/models/chart_asset_model.py exists\n"
            "- PYTHONPATH includes src/\n"
            "- package structure is consistent with Phase 3.5 layout\n"
        ) from e


# --------------------------------------------------
# Constants
# --------------------------------------------------
DEFAULT_CHART_ASSET_DB_PATH = Path("chart_assets.db")


def _stable_asset_id(*parts: Any) -> str:
    payload = "||".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@contextmanager
def open_chart_asset_db(db_path: Path = DEFAULT_CHART_ASSET_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_chart_asset_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chart_assets (
            asset_id TEXT PRIMARY KEY,
            candidate_id TEXT,
            run_id TEXT,
            game_normalized TEXT,
            difficulty_normalized TEXT,
            level_normalized INTEGER,
            asset_type TEXT NOT NULL,
            asset_subtype TEXT,
            text_representation TEXT,
            reference_url TEXT,
            content_sha256 TEXT,
            conversion_version INTEGER,
            embedded_at TEXT NOT NULL,
            source_path TEXT,
            basename TEXT,
            extension TEXT,
            extra_metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_chart_assets_run
            ON chart_assets(run_id);

        CREATE INDEX IF NOT EXISTS idx_chart_assets_game_diff_level
            ON chart_assets(game_normalized, difficulty_normalized, level_normalized);

        CREATE INDEX IF NOT EXISTS idx_chart_assets_type_subtype
            ON chart_assets(asset_type, asset_subtype);
        """
    )


def persist_chart_asset(*, conn: sqlite3.Connection, asset: ChartAsset) -> Dict[str, Any]:
    record = asset.to_record()
    conn.execute(
        """
        INSERT OR REPLACE INTO chart_assets(
            asset_id,
            candidate_id,
            run_id,
            game_normalized,
            difficulty_normalized,
            level_normalized,
            asset_type,
            asset_subtype,
            text_representation,
            reference_url,
            content_sha256,
            conversion_version,
            embedded_at,
            source_path,
            basename,
            extension,
            extra_metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("asset_id"),
            record.get("candidate_id"),
            record.get("run_id"),
            record.get("game_normalized"),
            record.get("difficulty_normalized"),
            record.get("level_normalized"),
            record.get("asset_type"),
            record.get("asset_subtype"),
            record.get("text_representation"),
            record.get("reference_url"),
            record.get("content_sha256"),
            record.get("conversion_version"),
            record.get("embedded_at"),
            record.get("source_path"),
            record.get("basename"),
            record.get("extension"),
            record.get("extra_metadata_json"),
        ),
    )
    return {
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "asset_subtype": asset.asset_subtype,
    }


def build_chart_asset_from_file(
    path: Path,
    *,
    candidate_id: Optional[str] = None,
    run_id: Optional[str] = None,
    game_normalized: Optional[str] = None,
    difficulty_normalized: Optional[str] = None,
    level_normalized: Optional[int] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> ChartAsset:

    # --------------------------------------------------
    # ✅ Lazy imports (CRITICAL to avoid circular import)
    # --------------------------------------------------
    try:
        from rhythm_ingestion.writers.classifiers.chart_asset_classifier import (
            classify_asset_type,
            classify_asset_subtype,
        )
        from rhythm_ingestion.writers.converters.chart_text_converter import (
            convert_chart_file_to_text,
            build_reference_asset,
        )
    except ImportError:
        from ..classifiers.chart_asset_classifier import (
            classify_asset_type,
            classify_asset_subtype,
        )
        from ..converters.chart_text_converter import (
            convert_chart_file_to_text,
            build_reference_asset,
        )

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------
    asset_type = classify_asset_type(path)
    subtype = classify_asset_subtype(path)

    # --------------------------------------------------
    # TYPE_A (text-based chart)
    # --------------------------------------------------
    if asset_type == AssetType.TYPE_A.value:
        converted = convert_chart_file_to_text(
            path,
            metadata={
                "game": game_normalized,
                "difficulty": difficulty_normalized,
                "level": level_normalized,
                **(extra_metadata or {}),
            },
        )

        asset_id = _stable_asset_id(
            run_id,
            candidate_id,
            str(path),
            converted["content_sha256"],
        )

        return ChartAsset(
            asset_id=asset_id,
            candidate_id=candidate_id,
            run_id=run_id,
            game_normalized=game_normalized,
            difficulty_normalized=difficulty_normalized,
            level_normalized=level_normalized,
            asset_type=converted["asset_type"],
            asset_subtype=converted["asset_subtype"],
            text_representation=converted["text_representation"],
            content_sha256=converted["content_sha256"],
            conversion_version=int(converted["conversion_version"]),
            embedded_at=utc_now_iso(),
            source_path=str(path),
            basename=path.name,
            extension=path.suffix.lower(),
            extra_metadata=extra_metadata or {},
        )

    # --------------------------------------------------
    # TYPE_B (reference asset)
    # --------------------------------------------------
    converted = build_reference_asset(
        reference_url=str(path),
        subtype=subtype,
    )

    asset_id = _stable_asset_id(
        run_id,
        candidate_id,
        str(path),
        converted["content_sha256"],
    )

    return ChartAsset(
        asset_id=asset_id,
        candidate_id=candidate_id,
        run_id=run_id,
        game_normalized=game_normalized,
        difficulty_normalized=difficulty_normalized,
        level_normalized=level_normalized,
        asset_type=converted["asset_type"],
        asset_subtype=converted["asset_subtype"],
        reference_url=converted["reference_url"],
        content_sha256=converted["content_sha256"],
        conversion_version=int(converted["conversion_version"]),
        embedded_at=utc_now_iso(),
        source_path=str(path),
        basename=path.name,
        extension=path.suffix.lower(),
        extra_metadata=extra_metadata or {},
    )

def build_chart_asset_from_reference(
    *,
    reference_url: str,
    candidate_id: Optional[str] = None,
    run_id: Optional[str] = None,
    game_normalized: Optional[str] = None,
    difficulty_normalized: Optional[str] = None,
    level_normalized: Optional[int] = None,
    source_path: Optional[str] = None,
    basename: Optional[str] = None,
    extension: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> ChartAsset:

    # --------------------------------------------------
    # ✅ Lazy import (avoid circular import)
    # --------------------------------------------------
    try:
        from rhythm_ingestion.writers.converters.chart_text_converter import (
            build_reference_asset,
        )
    except ImportError:
        from ..converters.chart_text_converter import (
            build_reference_asset,
        )

    # --------------------------------------------------
    # Build reference asset
    # --------------------------------------------------
    converted = build_reference_asset(reference_url=reference_url)

    asset_id = _stable_asset_id(
        run_id,
        candidate_id,
        reference_url,
        converted["content_sha256"],
    )

    return ChartAsset(
        asset_id=asset_id,
        candidate_id=candidate_id,
        run_id=run_id,
        game_normalized=game_normalized,
        difficulty_normalized=difficulty_normalized,
        level_normalized=level_normalized,
        asset_type=converted["asset_type"],
        asset_subtype=converted["asset_subtype"],
        reference_url=converted["reference_url"],
        content_sha256=converted["content_sha256"],
        conversion_version=int(converted["conversion_version"]),
        embedded_at=utc_now_iso(),
        source_path=source_path,
        basename=basename,
        extension=extension,
        extra_metadata=extra_metadata or {},
    )

def persist_chart_assets(
    *,
    db_path: Path,
    assets: Sequence[ChartAsset],
) -> Dict[str, Any]:
    rows_written = 0
    with open_chart_asset_db(db_path) as conn:
        ensure_chart_asset_schema(conn)
        for asset in assets:
            persist_chart_asset(conn=conn, asset=asset)
            rows_written += 1
    return {
        "db_path": str(db_path),
        "rows_written": rows_written,
    }


def persist_chart_assets_from_candidates(
    *,
    db_path: Path,
    candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build + persist chart assets from candidate dicts.

    Expected candidate shape (minimal):
        {
            "source_path": ...,
            "candidate_id": ...,
            "run_id": ...,
            "game_normalized": ...,
            "difficulty_normalized": ...,
            "level_normalized": ...,
            "reference_url": ...   # for external refs
            "extra_metadata": {...}
        }
    """
    built: List[ChartAsset] = []
    for cand in candidates:
        source_path = cand.get("source_path")
        reference_url = cand.get("reference_url")

        if reference_url and not source_path:
            asset = build_chart_asset_from_reference(
                reference_url=reference_url,
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
            built.append(asset)
            continue

        if not source_path:
            continue

        path = Path(source_path)
        asset = build_chart_asset_from_file(
            path,
            candidate_id=cand.get("candidate_id"),
            run_id=cand.get("run_id"),
            game_normalized=cand.get("game_normalized"),
            difficulty_normalized=cand.get("difficulty_normalized"),
            level_normalized=cand.get("level_normalized"),
            extra_metadata=cand.get("extra_metadata") or {},
        )
        built.append(asset)

    result = persist_chart_assets(db_path=db_path, assets=built)
    result["assets_built"] = len(built)
    return result


__all__ = [
    "DEFAULT_CHART_ASSET_DB_PATH",
    "open_chart_asset_db",
    "ensure_chart_asset_schema",
    "persist_chart_asset",
    "persist_chart_assets",
    "persist_chart_assets_from_candidates",
    "build_chart_asset_from_file",
    "build_chart_asset_from_reference",
]
