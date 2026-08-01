from __future__ import annotations

"""
file_scan_inventory_writer.py

Persist file scan inventory into SQLite.

Scope:
- Store scanned file candidates
- Store raw + normalized identity
- DO NOT handle chart conversion (handled by chart_asset_writer)
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from rhythm_ingestion.writers.normalizers.identity_normalizer import normalize_folder_identity
except ImportError:
    try:
        from ..normalizers.identity_normalizer import normalize_folder_identity
    except ImportError:
        from identity_normalizer import normalize_folder_identity


DEFAULT_FILE_SCAN_DB_PATH = Path("file_scan_inventory.db")


# --------------------------------------------------
# DB connection
# --------------------------------------------------

@contextmanager
def open_file_scan_inventory_db(db_path: Path = DEFAULT_FILE_SCAN_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------
# schema
# --------------------------------------------------

def ensure_file_scan_inventory_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS file_scan_inventory (

            candidate_id TEXT PRIMARY KEY,
            run_id TEXT,

            source_path TEXT NOT NULL,
            normalized_key TEXT NOT NULL,

            basename TEXT,
            extension TEXT,

            size INTEGER,
            mtime_ns INTEGER,

            game_folder TEXT,
            difficulty_folder TEXT,
            level_folder TEXT,

            game_normalized TEXT,
            difficulty_normalized TEXT,
            level_normalized INTEGER,

            normalization_issues_json TEXT,

            discovered_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_scan_inventory_run
            ON file_scan_inventory(run_id);

        CREATE INDEX IF NOT EXISTS idx_scan_inventory_game
            ON file_scan_inventory(game_normalized);
        """
    )


# --------------------------------------------------
# helpers
# --------------------------------------------------

def _safe_json(v: Any) -> str:
    try:
        return json.dumps(v or {}, ensure_ascii=False)
    except Exception:
        return "{}"


# --------------------------------------------------
# core writer
# --------------------------------------------------

def persist_file_scan_inventory_rows(
    *,
    db_path: Path,
    rows: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    rows should contain:
    {
        source_path,
        normalized_key,
        basename,
        extension,
        size,
        mtime_ns,
        game_folder,
        difficulty_folder,
        level_folder,
        run_id,
        discovered_at
    }
    """

    rows_written = 0

    with open_file_scan_inventory_db(db_path) as conn:
        ensure_file_scan_inventory_schema(conn)

        for row in rows:
            hier_game = row.get("game_folder")
            hier_diff = row.get("difficulty_folder")
            hier_level = row.get("level_folder")

            # ✅ normalize identity
            norm = normalize_folder_identity(
                game_folder=hier_game,
                difficulty_folder=hier_diff,
                level_folder=hier_level,
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO file_scan_inventory(
                    candidate_id,
                    run_id,
                    source_path,
                    normalized_key,
                    basename,
                    extension,
                    size,
                    mtime_ns,
                    game_folder,
                    difficulty_folder,
                    level_folder,
                    game_normalized,
                    difficulty_normalized,
                    level_normalized,
                    normalization_issues_json,
                    discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("candidate_id"),
                    row.get("run_id"),
                    row.get("source_path"),
                    row.get("normalized_key"),
                    row.get("basename"),
                    row.get("extension"),
                    row.get("size"),
                    row.get("mtime_ns"),
                    hier_game,
                    hier_diff,
                    hier_level,
                    norm.get("game"),
                    norm.get("difficulty"),
                    norm.get("level"),
                    _safe_json(norm.get("issues")),
                    row.get("discovered_at"),
                ),
            )

            rows_written += 1

    return {
        "db_path": str(db_path),
        "rows_written": rows_written,
    }


# --------------------------------------------------
# convenience wrapper
# --------------------------------------------------

def persist_file_scan_inventory_from_paths(
    *,
    db_path: Path,
    candidates: Iterable[Path],
    run_id: str,
    extract_chart_hierarchy,
    _normalize_key,
    fingerprint,
    utc_now_iso,
) -> Dict[str, Any]:

    rows: List[Dict[str, Any]] = []

    for p in candidates:
        try:
            fp = fingerprint(p)
        except Exception:
            continue

        hier = extract_chart_hierarchy(p)

        rows.append(
            {
                "candidate_id": f"{run_id}:{_normalize_key(p)}",
                "run_id": run_id,
                "source_path": str(p),
                "normalized_key": _normalize_key(p),
                "basename": p.name,
                "extension": p.suffix.lower(),
                "size": fp.size,
                "mtime_ns": fp.mtime_ns,
                "game_folder": hier.get("game_folder"),
                "difficulty_folder": hier.get("difficulty_folder"),
                "level_folder": hier.get("level_folder"),
                "discovered_at": utc_now_iso(),
            }
        )

    return persist_file_scan_inventory_rows(
        db_path=db_path,
        rows=rows,
    )


__all__ = [
    "open_file_scan_inventory_db",
    "ensure_file_scan_inventory_schema",
    "persist_file_scan_inventory_rows",
    "persist_file_scan_inventory_from_paths",
]