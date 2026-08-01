from __future__ import annotations

"""
chart_asset_reader.py

Reader layer for chart_assets.db.

Responsibilities:
- read asset rows
- expose filtered retrieval API

Non-responsibilities:
- no normalization
- no conversion
- no validation
- no persistence
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Reader
# --------------------------------------------------

class ChartAssetReader:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"chart_assets.db not found: {self.db_path}")

        self._conn: Optional[sqlite3.Connection] = None

    # --------------------------------------------------
    # Context manager
    # --------------------------------------------------

    def __enter__(self) -> "ChartAssetReader":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --------------------------------------------------
    # Connection
    # --------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # --------------------------------------------------
    # Core query
    # --------------------------------------------------

    def _execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = self.connect()
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def read_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM chart_assets"
        params: tuple = ()

        if limit:
            query += " LIMIT ?"
            params = (limit,)

        return self._execute(query, params)

    def read_by_game(self, game_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM chart_assets
            WHERE game = ?
            """,
            (game_id,),
        )

    def read_type_a(self) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM chart_assets
            WHERE text_representation IS NOT NULL
            """
        )

    def read_type_b(self) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM chart_assets
            WHERE reference_url IS NOT NULL
            """
        )

    def read_by_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM chart_assets
            WHERE hash = ?
            """,
            (content_hash,),
        )