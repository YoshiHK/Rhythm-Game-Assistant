"""
song_info_reader.py

Reader layer for song_info.sqlite (reference dataset).

Responsibilities:
- open sqlite database
- perform basic lookups
- return raw records (no normalization, no inference)

Non-responsibilities:
- no DB writes
- no identity resolution
- no verification logic
- no gameplay logic
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Config
# --------------------------------------------------

DEFAULT_SONG_INFO_PATH = (
    Path(
        r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\data\reference\song_info.sqlite"
    )
)


# --------------------------------------------------
# Reader class
# --------------------------------------------------

class SongInfoReader:
    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_SONG_INFO_PATH

        if not self.db_path.exists():
            raise FileNotFoundError(f"song_info.sqlite not found: {self.db_path}")

        self._conn = None

    # --------------------------------------------------
    # Connection handling
    # --------------------------------------------------

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # --------------------------------------------------
    # Core query helpers
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

    def lookup_by_song_id(
        self,
        song_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Lookup entries by song_id.

        Returns raw rows from sqlite.
        """
        return self._execute(
            """
            SELECT *
            FROM song_info
            WHERE song_id = ?
            """,
            (song_id,),
        )

    def lookup_by_name(
        self,
        song_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Case-insensitive lookup by song name (LIKE match).

        Note:
        - exact matching is preferred upstream
        - this is fallback / fuzzy support
        """
        return self._execute(
            """
            SELECT *
            FROM song_info
            WHERE LOWER(name) LIKE LOWER(?)
            """,
            (f"%{song_name}%",),
        )

    def lookup_by_game(
        self,
        game_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Lookup all songs for a given game.
        (useful for preloading / reference browsing)
        """
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
        
    
    def read_all(
        self,
        *,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read all rows from song_info table (raw).

        Responsibilities:
        - no normalization
        - no filtering
        - no matching

        Used by:
        - SongDatabaseCatalog.load_from_sqlite()
        """

        query = "SELECT * FROM song_info"
        params: tuple = ()

        if limit is not None:
            query += " LIMIT ?"
            params = (int(limit),)

        return self._execute(query, params)
