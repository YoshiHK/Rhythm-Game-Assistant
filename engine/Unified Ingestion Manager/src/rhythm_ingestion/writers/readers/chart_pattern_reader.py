from __future__ import annotations
"""
chart_pattern_reader.py
Reader layer for chart_patterns.db.

Responsibilities:
- Provide deterministic, read-only access to chart pattern data.
- Normalize chart identity so Phase 5 and Phase 7 can use a stable lookup key.
- Add extraction-version fallback so callers do not need to recompute patterns
  immediately when newer versions are missing.
- Do NOT perform extraction or mutation.
"""

import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------

DEFAULT_DB_PATH = Path("chart_patterns.db")
DEFAULT_EXTRACTION_VERSION = 1
DEFAULT_FALLBACK_VERSIONS: Tuple[int, ...] = ()

# Canonical Phase 5 / Phase 7 feature keys.
FEATURE_KEYS: Tuple[str, ...] = (
    "chart_pattern_density",
    "chart_pattern_burst_density",
    "chart_pattern_stream_length_avg",
    "chart_pattern_jump_ratio",
    "chart_pattern_hold_complexity",
    "chart_pattern_section_variance",
    "chart_pattern_spike_count",
)

# Registry / metadata columns that are useful when present.
META_KEYS: Tuple[str, ...] = (
    "chart_id",
    "game",
    "song_id",
    "difficulty",
    "chart_type",
    "level",
    "source_file_hash",
    "computed_at",
    "updated_at",
)


# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------

@contextmanager
def open_db(db_path: Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    if not _table_exists(conn, table_name):
        return []
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(r[1]) for r in rows]


def _choose_pattern_table(conn: sqlite3.Connection) -> Optional[str]:
    for name in ("chart_patterns", "chart_pattern_features", "patterns"):
        if _table_exists(conn, name):
            return name
    return None


def _choose_blob_table(conn: sqlite3.Connection) -> Optional[str]:
    for name in ("chart_pattern_blobs", "pattern_blobs", "chart_visual_blobs"):
        if _table_exists(conn, name):
            return name
    return None


def _best_available_column(columns: Iterable[str], candidates: Sequence[str]) -> Optional[str]:
    colset = {str(c) for c in columns}
    for c in candidates:
        if c in colset:
            return c
    return None


# ---------------------------------------------------------------------
# Chart-id normalization
# ---------------------------------------------------------------------


def normalize_chart_id(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
) -> Optional[str]:
    """
    Normalize chart identity to a stable, lowercase key.

    Priority:
    1) Existing chart_id if supplied
    2) Composite key from game/song_id/difficulty/(chart_type)/(level)

    We keep the function deterministic and purely lexical so that it is safe
    for both Phase 5 and Phase 7 lookups.
    """
    if chart_id is not None and str(chart_id).strip():
        return _normalize_token(str(chart_id))

    parts = [
        _normalize_token(game),
        _normalize_token(song_id),
        _normalize_token(difficulty),
    ]
    extra = [_normalize_token(chart_type), _normalize_token(level)]
    parts.extend([p for p in extra if p])
    parts = [p for p in parts if p]
    return "::".join(parts) if parts else None


def _normalize_token(value: Optional[Any]) -> str:
    if value is None:
        return ""
    s = str(value).strip().lower()
    if not s:
        return ""
    # Normalize a small set of separators while staying conservative.
    for old, new in (("/", "-"), ("\\", "-"), (" ", "_"), ("|", ":")):
        s = s.replace(old, new)
    while "__" in s:
        s = s.replace("__", "_")
    while ":::" in s:
        s = s.replace(":::", "::")
    return s.strip("_:")


# ---------------------------------------------------------------------
# Version fallback helpers
# ---------------------------------------------------------------------


def _build_version_chain(
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
) -> Tuple[int, ...]:
    versions: List[int] = []
    seen = set()

    def add(v: int) -> None:
        if isinstance(v, int) and v > 0 and v not in seen:
            versions.append(v)
            seen.add(v)

    add(int(extraction_version))
    for v in fallback_versions:
        add(int(v))

    # Deterministic fallback to lower versions if not already included.
    for v in range(int(extraction_version) - 1, 0, -1):
        add(v)

    return tuple(versions)


# ---------------------------------------------------------------------
# Internal readers
# ---------------------------------------------------------------------


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row is not None else None



@lru_cache(maxsize=8192)
def _get_chart_pattern_cached(
    normalized_chart_id_value: str,
    extraction_version: int,
    fallback_versions: Tuple[int, ...],
    db_path_str: str,
) -> Optional[Dict[str, Any]]:
    """
    Internal cached chart-pattern lookup.

    Key responsibilities:
    - Use normalized_chart_id_value (string ONLY)
    - Perform tolerant matching against DB key variations
    - Support version fallback
    """

    db_path = Path(db_path_str)

    with open_db(db_path) as conn:
        table = _choose_pattern_table(conn)
        if not table:
            return None

        columns = _get_table_columns(conn, table)

        # ✅ Prefer explicit normalized key column, fallback to chart_id
        id_col = _best_available_column(columns, ("normalized_chart_id", "chart_id"))

        version_col = _best_available_column(
            columns,
            ("extraction_version", "pattern_version", "version"),
        )

        if id_col is None:
            return None

        select_cols = ", ".join(columns) if columns else "*"

        # --------------------------------------------------
        # ✅ Candidate key generation (CRITICAL FIX)
        # --------------------------------------------------
        candidates: List[str] = []

        if normalized_chart_id_value:
            candidates.append(normalized_chart_id_value)

            # ✅ tolerant matching (format fallback)
            candidates.append(normalized_chart_id_value.replace("::", "|"))
            candidates.append(normalized_chart_id_value.replace("::", "-"))
            candidates.append(normalized_chart_id_value.replace("::", "_"))
            candidates.append(normalized_chart_id_value.replace(":", ""))

        # Remove duplicates while preserving order
        seen = set()
        candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

        # --------------------------------------------------
        # ✅ Case 1 — no version column
        # --------------------------------------------------
        if version_col is None:
            for cid in candidates:
                row = conn.execute(
                    f"SELECT {select_cols} FROM {table} WHERE {id_col} = ? LIMIT 1",
                    (cid,),
                ).fetchone()

                if row is not None:
                    out = _row_to_dict(row)
                    # Optional debug hook
                    # print("✅ matched chart_id:", cid)
                    return out

            return None

        # --------------------------------------------------
        # ✅ Case 2 — versioned lookup
        # --------------------------------------------------
        for v in _build_version_chain(extraction_version, fallback_versions):

            for cid in candidates:
                row = conn.execute(
                    f"""
                    SELECT {select_cols}
                    FROM {table}
                    WHERE {id_col} = ? AND {version_col} = ?
                    ORDER BY rowid DESC
                    LIMIT 1
                    """,
                    (cid, v),
                ).fetchone()

                if row is not None:
                    out = dict(row)

                    # ✅ stable metadata guarantees
                    out.setdefault("requested_extraction_version", extraction_version)
                    out.setdefault(
                        "resolved_extraction_version",
                        out.get(version_col, v),
                    )
                    out.setdefault(
                        "version_fallback_used",
                        int(out.get(version_col, v)) != int(extraction_version),
                    )

                    # Optional debug hook
                    # print("✅ matched chart_id:", cid, "version:", v)

                    return out

        # Optional debug hook
        # print("❌ no match for:", candidates)

        return None

def _get_pattern_blobs_cached(
    normalized_chart_id: str,
    extraction_version: int,
    fallback_versions: Tuple[int, ...],
    db_path_str: str,
) -> Optional[List[Dict[str, Any]]]:
    db_path = Path(db_path_str)
    with open_db(db_path) as conn:
        table = _choose_blob_table(conn)
        if not table:
            return None

        columns = _get_table_columns(conn, table)
        id_col = _best_available_column(columns, ("normalized_chart_id", "chart_id"))
        version_col = _best_available_column(columns, ("extraction_version", "pattern_version", "version"))
        if id_col is None:
            return None

        select_cols = ", ".join(columns) if columns else "*"

        versions = (None,) if version_col is None else _build_version_chain(extraction_version, fallback_versions)
        for v in versions:
            if v is None:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM {table} WHERE {id_col} = ? ORDER BY rowid ASC",
                    (normalized_chart_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM {table} "
                    f"WHERE {id_col} = ? AND {version_col} = ? ORDER BY rowid ASC",
                    (normalized_chart_id, v),
                ).fetchall()
            if rows:
                return [dict(r) for r in rows]

        return None


# ---------------------------------------------------------------------
# Public readers
# ---------------------------------------------------------------------


def get_chart_pattern(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Fetch a raw chart_patterns row with normalized chart-id support."""
    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )
    if not normalized_chart_id:
        return None
    return _get_chart_pattern_cached(
        normalized_chart_id,
        int(extraction_version),
        tuple(int(v) for v in fallback_versions),
        str(db_path),
    )


def get_pattern_features(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Phase 5 / Phase 7 primary feature reader."""
    row = get_chart_pattern(
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
    if row is None:
        return None

    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )

    out: Dict[str, Any] = {
        "chart_id": normalized_chart_id_value,
        "requested_extraction_version": int(extraction_version),
        "resolved_extraction_version": int(
            row.get("resolved_extraction_version")
            or row.get("extraction_version")
            or row.get("pattern_version")
            or extraction_version
        ),
        "version_fallback_used": bool(row.get("version_fallback_used", False)),
        "has_chart_pattern_features": True,
        "chart_pattern_status": "VALID",
    }

    for key in FEATURE_KEYS:
        out[key] = row.get(key)

    # Preserve useful metadata when available.
    for key in META_KEYS:
        if key in row and key not in out:
            out[key] = row.get(key)

    return out


def get_pattern_blobs(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch all blob-pointer rows for a chart."""
    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )
    if not normalized_chart_id:
        return None
    return _get_pattern_blobs_cached(
        normalized_chart_id,
        int(extraction_version),
        tuple(int(v) for v in fallback_versions),
        str(db_path),
    )


def load_chart_capability_bundle(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Unified read for Phase 5 & Phase 7.
    Returns a stable envelope even when the chart is missing.
    """
    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )
    features = get_pattern_features(
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
    blobs = get_pattern_blobs(
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

    if features is None:
        return {
            "chart_id": normalized_chart_id_value,
            "requested_extraction_version": int(extraction_version),
            "resolved_extraction_version": None,
            "version_fallback_used": False,
            "chart_pattern_status": "MISSING",
            "has_chart_pattern_features": False,
            "pattern_features": {},
            "pattern_blobs": blobs or [],
        }

    pattern_features = {k: features.get(k) for k in FEATURE_KEYS}
    return {
        "chart_id": features.get("chart_id", normalized_chart_id),
        "requested_extraction_version": features.get("requested_extraction_version", int(extraction_version)),
        "resolved_extraction_version": features.get("resolved_extraction_version"),
        "version_fallback_used": bool(features.get("version_fallback_used", False)),
        "chart_pattern_status": features.get("chart_pattern_status", "VALID"),
        "has_chart_pattern_features": bool(features.get("has_chart_pattern_features", True)),
        "pattern_features": pattern_features,
        "pattern_blobs": blobs or [],
        "metadata": {k: features.get(k) for k in META_KEYS if k in features},
    }


def load_phase5_features(
    chart_id: Optional[str] = None,
    *,
    game: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    chart_type: Optional[str] = None,
    level: Optional[str] = None,
    extraction_version: int = DEFAULT_EXTRACTION_VERSION,
    fallback_versions: Sequence[int] = DEFAULT_FALLBACK_VERSIONS,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Lightweight helper tailored for Phase 5.
    Returns a stable feature dict, never None.
    """
    features = get_pattern_features(
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
    if features is not None:
        return features

    normalized_chart_id = normalize_chart_id(
        chart_id,
        game=game,
        song_id=song_id,
        difficulty=difficulty,
        chart_type=chart_type,
        level=level,
    )
    out: Dict[str, Any] = {
        "chart_id": normalized_chart_id_value,
        "requested_extraction_version": int(extraction_version),
        "resolved_extraction_version": None,
        "version_fallback_used": False,
        "has_chart_pattern_features": False,
        "chart_pattern_status": "MISSING",
    }
    for key in FEATURE_KEYS:
        out[key] = None
    return out


__all__ = [
    "FEATURE_KEYS",
    "DEFAULT_DB_PATH",
    "DEFAULT_EXTRACTION_VERSION",
    "DEFAULT_FALLBACK_VERSIONS",
    "normalize_chart_id",
    "open_db",
    "get_chart_pattern",
    "get_pattern_features",
    "get_pattern_blobs",
    "load_chart_capability_bundle",
    "load_phase5_features",
]
