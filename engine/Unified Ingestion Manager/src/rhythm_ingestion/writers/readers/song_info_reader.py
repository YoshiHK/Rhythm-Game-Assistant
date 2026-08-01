from __future__ import annotations

"""
song_info_reader.py

Reader layer for song_info.sqlite (reference dataset).

Responsibilities:
- open sqlite database
- perform basic lookups
- return raw records (no normalization, no inference)

Design:
- read-only
- connection-safe (context manager supported)
- lightweight API surface

Non-responsibilities:
- no DB writes
- no identity resolution
- no verification logic
- no gameplay logic
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Config
# --------------------------------------------------

DEFAULT_SONG_INFO_PATH = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\data\reference\song_info.sqlite"
)


# --------------------------------------------------
# Reader class
# --------------------------------------------------

class SongInfoReader:
    """
    Low-level SQLite reader.

    Safe usage:
        with SongInfoReader() as reader:
            rows = reader.lookup(song_id="123")
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_SONG_INFO_PATH

        if not self.db_path.exists():
            raise FileNotFoundError(f"song_info.sqlite not found: {self.db_path}")

        self._conn: Optional[sqlite3.Connection] = None

    # --------------------------------------------------
    # Context manager (SAFE lifecycle)
    # --------------------------------------------------

    def __enter__(self) -> "SongInfoReader":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --------------------------------------------------
    # Connection handling
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
    # Core query helper
    # --------------------------------------------------

    def _execute(
        self,
        query: str,
        params: tuple = (),
    ) -> List[Dict[str, Any]]:
        conn = self.connect()
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def lookup_by_song_id(self, song_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM song_info
            WHERE song_id = ?
            """,
            (song_id,),
        )

    def lookup_by_name(self, song_name: str) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM song_info
            WHERE LOWER(name) LIKE LOWER(?)
            """,
            (f"%{song_name}%",),
        )

    def lookup_by_game(self, game_id: str) -> List[Dict[str, Any]]:
        return self._execute(
            """
            SELECT *
            FROM song_info
            WHERE game_id = ?
            """,
            (game_id,),
        )

    def lookup(
        self,
        *,
        song_id: Optional[str] = None,
        song_name: Optional[str] = None,
        game_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        General lookup entrypoint.

        Priority:
        1. song_id
        2. name
        3. game
        """

        if song_id:
            return self.lookup_by_song_id(song_id)

        if song_name:
            return self.lookup_by_name(song_name)[:limit]

        if game_id:
            return self.lookup_by_game(game_id)[:limit]

        return []

    def read_all(self, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM song_info"
        params: tuple = ()

        if limit is not None:
            query += " LIMIT ?"
            params = (int(limit),)

        return self._execute(query, params)

    def exists_song_id(self, song_id: str) -> bool:
        """
        Lightweight existence check (fast path for adapters)
        """
        rows = self._execute(
            """
            SELECT 1
            FROM song_info
            WHERE song_id = ?
            LIMIT 1
            """,
            (song_id,),
        )
        return len(rows) > 0