from __future__ import annotations

"""
chart_pattern_reader.py

Reader layer for chart_patterns.db.

Responsibilities:
- Provide deterministic, read-only access to chart pattern data
- Serve Phase 5 (learning) and Phase 7 (ranking)
- Do NOT perform extraction or mutation
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Iterator


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------
DEFAULT_DB_PATH = Path("chart_patterns.db")


# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------
@contextmanager
def open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Core readers
# ---------------------------------------------------------------------
def get_chart_pattern(
    chart_id: str,
    *,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Fetch chart_patterns row
    """

    with open_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT *
            FROM chart_patterns
            WHERE chart_id = ? AND extraction_version = ?
            """,
            (chart_id, extraction_version),
        )
        row = cur.fetchone()

        return dict(row) if row else None


def get_pattern_features(
    chart_id: str,
    *,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Phase 5 / Phase 7 primary feature reader
    """

    with open_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT *
            FROM pattern_features
            WHERE chart_id = ? AND extraction_version = ?
            """,
            (chart_id, extraction_version),
        )
        row = cur.fetchone()

        if not row:
            return None

        result = dict(row)

        # deserialize JSON field safely
        try:
            import json
            if result.get("pattern_score_json"):
                result["pattern_score"] = json.loads(result["pattern_score_json"])
        except Exception:
            result["pattern_score"] = None

        return result


def get_pattern_blobs(
    chart_id: str,
    *,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[list[Dict[str, Any]]]:
    """
    Fetch all blob pointers for a chart
    """

    with open_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT *
            FROM pattern_blobs
            WHERE chart_id = ? AND extraction_version = ?
            """,
            (chart_id, extraction_version),
        )
        rows = cur.fetchall()

        if not rows:
            return None

        return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# High-level API (Phase 5 & Phase 7 use)
# ---------------------------------------------------------------------
def load_chart_capability_bundle(
    chart_id: str,
    *,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Unified read for Phase 5 & Phase 7.

    Returns:
    {
        chart_pattern: {...},
        pattern_features: {...},
        pattern_blobs: [...]
    }
    """

    return {
        "chart_pattern": get_chart_pattern(
            chart_id,
            extraction_version=extraction_version,
            db_path=db_path,
        ),
        "pattern_features": get_pattern_features(
            chart_id,
            extraction_version=extraction_version,
            db_path=db_path,
        ),
        "pattern_blobs": get_pattern_blobs(
            chart_id,
            extraction_version=extraction_version,
            db_path=db_path,
        ),
    }


# ---------------------------------------------------------------------
# Phase 5 helper (ready-to-use)
# ---------------------------------------------------------------------
def load_phase5_features(
    chart_id: str,
    *,
    extraction_version: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Lightweight helper tailored for Phase 5.

    Returns:
    minimal feature dict (safe fallback if missing)
    """

    features = get_pattern_features(
        chart_id,
        extraction_version=extraction_version,
        db_path=db_path,
    )

    if not features:
        return {}

    return {
        "density": features.get("density"),
        "burst_density": features.get("burst_density"),
        "stream_length_avg": features.get("stream_length_avg"),
        "jump_ratio": features.get("jump_ratio"),
        "hold_complexity": features.get("hold_complexity"),
        "section_variance": features.get("section_variance"),
        "spike_count": features.get("spike_count"),
        "pattern_score": features.get("pattern_score"),
    }


__all__ = [
    "get_chart_pattern",
    "get_pattern_features",
    "get_pattern_blobs",
    "load_chart_capability_bundle",
    "load_phase5_features",
]