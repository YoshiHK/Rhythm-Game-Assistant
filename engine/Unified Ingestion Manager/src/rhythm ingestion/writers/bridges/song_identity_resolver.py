from __future__ import annotations

"""
song_identity_resolver.py

Purpose
-------
Resolve a stable song identity for chart-feature wiring while treating
song_name as the CANONICAL lookup field.

Design principles
-----------------
- Deterministic and read-only
- Multi-game friendly
- Tolerant of heterogeneous song DB exports
- song_name-first resolution; song_id is secondary fallback only
- Pure wiring helper (does not mutate completed phases)

Phase 3.5 note
--------------
This resolver may consume data from:
- Song database export files
- song_info.sqlite (via SongInfoReader)

The resolver remains the decision layer.
Raw SQLite access belongs to reader layer.
"""

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------
# Reader import (preferred)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.readers.song_info_reader import (
        SongInfoReader,
        DEFAULT_SONG_INFO_PATH,
    )
except ImportError:
    try:
        from ..readers.song_info_reader import (
            SongInfoReader,
            DEFAULT_SONG_INFO_PATH,
        )
    except Exception:
        from song_info_reader import (
            SongInfoReader,
            DEFAULT_SONG_INFO_PATH,
        )


DEFAULT_SONG_DB_EXPORT_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Song Database Export"
)

DEFAULT_SONG_INFO_SQLITE = DEFAULT_SONG_INFO_PATH


GAME_ALIASES: Dict[str, str] = {
    "project sekai": "project_sekai",
    "proseka": "project_sekai",
    "pjsekai": "project_sekai",
    "bang dream": "bandori",
    "bandori": "bandori",
    "arcaea": "arcaea",
    "chunithm": "chunithm",
    "cytus ii": "cytus_ii",
    "cytus2": "cytus_ii",
    "dynamix": "dynamix",
    "groove coaster": "groove_coaster",
    "lanota": "lanota",
    "maimai": "maimai",
    "ongeki": "ongeki",
    "phigros": "phigros",
    "sound voltex": "sound_voltex",
    "sdvx": "sound_voltex",
    "yumesute": "yumesute",
    "ユメステ": "yumesute",
}

TITLE_KEYS: Tuple[str, ...] = (
    "楽曲名", "song_name", "title", "name", "music_title", "musicName", "songTitle"
)
ID_KEYS: Tuple[str, ...] = (
    "ID", "id", "song_id", "music_id", "musicId"
)
ARTIST_KEYS: Tuple[str, ...] = (
    "ボカロP", "artist", "composer", "producer"
)
BPM_KEYS: Tuple[str, ...] = (
    "BPM", "bpm"
)
DB_DIFFICULTY_KEYS: Dict[str, Tuple[str, ...]] = {
    "easy": ("Easy", "easy", "BASIC", "Basic"),
    "normal": ("Normal", "normal"),
    "hard": ("Hard", "hard"),
    "expert": ("Expert", "expert", "Advanced", "ADVANCED"),
    "master": ("Master", "master"),
    "append": ("Append", "append"),
    "special": ("Special", "special"),
}

NOISE_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\(\s*tv\s*size\s*\)", re.I),
    re.compile(r"\(\s*full\s*ver(?:sion)?\s*\)", re.I),
    re.compile(r"\(\s*long\s*ver(?:sion)?\s*\)", re.I),
    re.compile(r"\(\s*short\s*ver(?:sion)?\s*\)", re.I),
    re.compile(r"\(\s*remaster(?:ed)?\s*\)", re.I),
)


# --------------------------------------------------
# Text normalization
# --------------------------------------------------
def _to_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_text(value: Any) -> str:
    """Conservative, deterministic normalizer used for canonical name matching."""
    s = _to_text(value).strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()

    replacements = {
        "＆": "&",
        "～": "~",
        "・": " ",
        "_": " ",
        "|": " ",
        "／": "/",
        "（": "(",
        "）": ")",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)

    for pat in NOISE_PATTERNS:
        s = pat.sub("", s)

    s = re.sub(r"\s+", " ", s)
    return s.strip()


def canonical_song_name(value: Any) -> Optional[str]:
    s = normalize_text(value)
    return s if s else None


def canonical_game_id(raw: Any) -> Optional[str]:
    s = normalize_text(raw)
    if not s:
        return None
    return GAME_ALIASES.get(s, s.replace(" ", "_"))


# --------------------------------------------------
# Difficulty and title helpers
# --------------------------------------------------
_DIFFICULTY_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\[(append)\]", re.I), "append"),
    (re.compile(r"\[(master)\]", re.I), "master"),
    (re.compile(r"\[(expert)\]", re.I), "expert"),
    (re.compile(r"\[(special)\]", re.I), "special"),
    (re.compile(r"\[(hard)\]", re.I), "hard"),
    (re.compile(r"\[(normal)\]", re.I), "normal"),
    (re.compile(r"\[(easy)\]", re.I), "easy"),
    (re.compile(r"\bappend\b", re.I), "append"),
    (re.compile(r"\bmaster\b", re.I), "master"),
    (re.compile(r"\bexpert\b", re.I), "expert"),
    (re.compile(r"\bhard\b", re.I), "hard"),
    (re.compile(r"\bnormal\b", re.I), "normal"),
    (re.compile(r"\beasy\b", re.I), "easy"),
]


def extract_difficulty(value: Any) -> Optional[str]:
    s = _to_text(value)
    if not s:
        return None
    for pat, canonical in _DIFFICULTY_PATTERNS:
        if pat.search(s):
            return canonical
    return None


_SITE_SUFFIX_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\s+_\s+Bestdori!.*$", re.I),
    re.compile(r"\s+_\s+.*Resource Site.*$", re.I),
)


def extract_song_title_from_basename(basename: Any) -> Optional[str]:
    """Heuristic title extraction from file-scan basenames."""
    s = _to_text(basename).strip()
    if not s:
        return None

    s = re.sub(r"\.[A-Za-z0-9]+$", "", s)
    for pat in _SITE_SUFFIX_PATTERNS:
        s = pat.sub("", s)
    s = re.sub(r"^chart\s*[-:：]\s*", "", s, flags=re.I)
    s = re.sub(r"\[(append|master|expert|special|hard|normal|easy)\]", "", s, flags=re.I)
    s = s.strip(" -_\t\"'")
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def infer_game_from_filename(filename: str) -> Optional[str]:
    s = normalize_text(Path(filename).stem)
    for alias, canonical in GAME_ALIASES.items():
        if normalize_text(alias) in s:
            return canonical
    return None


def infer_game_from_path(path: Path) -> Optional[str]:
    valid_games = set(GAME_ALIASES.values())
    for part in path.parts:
        game = canonical_game_id(part)
        if game in valid_games:
            return game
    return None


def _looks_synthetic_song_id(song_id: Any) -> bool:
    s = normalize_text(song_id)
    if not s:
        return True
    return s.startswith("test_") or s.startswith("mock_") or s.startswith("sample_")


# --------------------------------------------------
# Reader-backed raw lookup helpers
# --------------------------------------------------
def _reader_lookup_song_rows(
    *,
    sqlite_path: Optional[str | Path],
    song_id: Optional[str] = None,
    song_name: Optional[str] = None,
    game_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Lightweight bridge to SongInfoReader.

    This keeps sqlite access out of resolver logic while still allowing
    the resolver to consume raw reference rows deterministically.
    """
    try:
        reader = SongInfoReader(db_path=sqlite_path or DEFAULT_SONG_INFO_SQLITE)
    except Exception:
        return []

    try:
        return reader.lookup(
            song_id=song_id,
            song_name=song_name,
            game_id=game_id,
            limit=limit,
        )
    finally:
        try:
            reader.close()
        except Exception:
            pass


def _extract_first_present(row: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None

@dataclass(frozen=True)
class SongMatch:
    game: Optional[str]
    song_id: Optional[str]
    song_name: Optional[str]
    canonical_song_name: Optional[str]
    difficulty: Optional[str]
    level: Optional[str] = None
    bpm: Optional[str] = None
    artist: Optional[str] = None
    source: str = "unknown"
    confidence: str = "none"
    raw_row: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "game": self.game,
            "song_id": self.song_id,
            "song_name": self.song_name,
            "canonical_song_name": self.canonical_song_name,
            "difficulty": self.difficulty,
            "level": self.level,
            "bpm": self.bpm,
            "artist": self.artist,
            "source": self.source,
            "confidence": self.confidence,
            "raw_row": self.raw_row,
        }


class SongDatabaseCatalog:
    def __init__(self) -> None:
        self.rows_by_game: Dict[str, List[Dict[str, Any]]] = {}
        self.by_name: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self.by_id: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    @staticmethod
    def _row_title(row: Dict[str, Any]) -> Optional[str]:
        for key in TITLE_KEYS:
            if key in row and _to_text(row.get(key)).strip():
                return _to_text(row.get(key)).strip()
        return None

    @staticmethod
    def _row_id(row: Dict[str, Any]) -> Optional[str]:
        for key in ID_KEYS:
            if key in row and _to_text(row.get(key)).strip():
                return _to_text(row.get(key)).strip()
        return None

    @staticmethod
    def _row_artist(row: Dict[str, Any]) -> Optional[str]:
        for key in ARTIST_KEYS:
            if key in row and _to_text(row.get(key)).strip():
                return _to_text(row.get(key)).strip()
        return None

    @staticmethod
    def _row_bpm(row: Dict[str, Any]) -> Optional[str]:
        for key in BPM_KEYS:
            if key in row and _to_text(row.get(key)).strip():
                return _to_text(row.get(key)).strip()
        return None

    @staticmethod
    def _row_level(row: Dict[str, Any], difficulty: Optional[str]) -> Optional[str]:
        if difficulty is None:
            return None
        for key in DB_DIFFICULTY_KEYS.get(difficulty, (difficulty, difficulty.title())):
            if key in row:
                val = _to_text(row.get(key)).strip()
                if val and val != "-":
                    return val
        return None

    def add_json_rows(self, game: str, rows: Iterable[Dict[str, Any]]) -> None:
        game = canonical_game_id(game) or str(game)
        self.rows_by_game.setdefault(game, [])
        self.by_name.setdefault(game, {})
        self.by_id.setdefault(game, {})

        for row in rows:
            if not isinstance(row, dict):
                continue
            self.rows_by_game[game].append(row)

            title = self._row_title(row)
            cid = self._row_id(row)
            cname = canonical_song_name(title)
            if cname:
                self.by_name[game].setdefault(cname, []).append(row)
            if cid:
                self.by_id[game].setdefault(normalize_text(cid), []).append(row)

    @classmethod
    def load_from_export_root(
        cls,
        export_root: Path | str = DEFAULT_SONG_DB_EXPORT_ROOT,
    ) -> "SongDatabaseCatalog":
        root = Path(export_root)
        catalog = cls()
        if not root.exists():
            return catalog

        for path in sorted(root.rglob("*.json")):
            try:
                rows = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(rows, list):
                continue

            game = (
                infer_game_from_filename(path.name)
                or infer_game_from_path(path)
                or "unknown"
            )

            catalog.add_json_rows(game, [r for r in rows if isinstance(r, dict)])

        return catalog

    @classmethod
    def load_from_sqlite(
        cls,
        sqlite_path: Path | str,
        *,
        default_game: Optional[str] = None,
    ) -> "SongDatabaseCatalog":
        """
        Reader-backed sqlite loading.

        Phase 3.5 wiring:
        - raw row access belongs to SongInfoReader
        - catalog construction remains here
        """
        path = Path(sqlite_path)
        catalog = cls()
        if not path.exists():
            return catalog

        try:
            reader = SongInfoReader(db_path=path)
        except Exception:
            return catalog

        try:
            rows = reader.read_all()
        except Exception:
            try:
                reader.close()
            except Exception:
                pass
            return catalog

        try:
            game = canonical_game_id(default_game) if default_game else infer_game_from_filename(path.name)
            game = game or infer_game_from_path(path) or "unknown"
            catalog.add_json_rows(game, [r for r in rows if isinstance(r, dict)])
            return catalog
        finally:
            try:
                reader.close()
            except Exception:
                pass

    def _choose_best_row(
        self,
        rows: Sequence[Dict[str, Any]],
        difficulty: Optional[str],
    ) -> Dict[str, Any]:
        if not rows:
            return {}

        if difficulty is None:
            return rows[0]

        scored: List[Tuple[int, Dict[str, Any]]] = []
        for row in rows:
            score = 1 if self._row_level(row, difficulty) is not None else 0
            scored.append((score, row))

        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1]

    def _match_from_row(
        self,
        game: str,
        row: Dict[str, Any],
        difficulty: Optional[str],
        *,
        source: str,
        confidence: str,
    ) -> SongMatch:
        title = self._row_title(row)
        return SongMatch(
            game=game,
            song_id=self._row_id(row),
            song_name=title,
            canonical_song_name=canonical_song_name(title),
            difficulty=difficulty,
            level=self._row_level(row, difficulty),
            bpm=self._row_bpm(row),
            artist=self._row_artist(row),
            source=source,
            confidence=confidence,
            raw_row=dict(row),
        )

    def resolve(
        self,
        *,
        game: Optional[str],
        song_name: Optional[str],
        difficulty: Optional[str],
        song_id: Optional[str] = None,
    ) -> SongMatch:
        """
        Canonical strategy:
          1) exact song_name match WITHIN game
          2) exact song_name match ACROSS games if unique
          3) conservative contains match WITHIN game
          4) song_id fallback only if it looks non-synthetic
        """
        game = canonical_game_id(game)
        cname = canonical_song_name(song_name)
        difficulty = difficulty.lower().strip() if isinstance(difficulty, str) else None

        if game and cname and game in self.by_name and cname in self.by_name[game]:
            row = self._choose_best_row(self.by_name[game][cname], difficulty)
            return self._match_from_row(
                game,
                row,
                difficulty,
                source="song_name",
                confidence="exact",
            )

        if cname:
            candidates: List[Tuple[str, Dict[str, Any]]] = []
            for g, name_map in self.by_name.items():
                if cname in name_map:
                    row = self._choose_best_row(name_map[cname], difficulty)
                    candidates.append((g, row))

            if len(candidates) == 1:
                g, row = candidates[0]
                return self._match_from_row(
                    g,
                    row,
                    difficulty,
                    source="song_name",
                    confidence="cross_game_exact",
                )

        if game and cname and game in self.rows_by_game:
            subset = self.rows_by_game[game]
            fallback_rows = [
                r
                for r in subset
                if cname
                and canonical_song_name(self._row_title(r))
                and cname in canonical_song_name(self._row_title(r))
            ]
            if len(fallback_rows) == 1:
                row = self._choose_best_row(fallback_rows, difficulty)
                return self._match_from_row(
                    game,
                    row,
                    difficulty,
                    source="song_name",
                    confidence="contains",
                )

        sid = normalize_text(song_id)
        if (
            game
            and sid
            and not _looks_synthetic_song_id(sid)
            and game in self.by_id
            and sid in self.by_id[game]
        ):
            row = self._choose_best_row(self.by_id[game][sid], difficulty)
            return self._match_from_row(
                game,
                row,
                difficulty,
                source="song_id",
                confidence="secondary_fallback",
            )

        return SongMatch(
            game=game,
            song_id=None,
            song_name=song_name,
            canonical_song_name=cname,
            difficulty=difficulty,
            source="unresolved",
            confidence="none",
            raw_row={},
        )


# --------------------------------------------------
# Module-level cache
# --------------------------------------------------

_CATALOG_CACHE: Dict[tuple, SongDatabaseCatalog] = {}


def _catalog_cache_key(
    *,
    export_root: Path | str,
    sqlite_path: Optional[Path | str],
    sqlite_default_game: Optional[str],
) -> tuple:
    """
    Build a stable cache key based on input sources.

    IMPORTANT:
    - must normalize paths to string
    - must distinguish None vs actual path
    """
    return (
        str(Path(export_root).resolve()),
        str(Path(sqlite_path).resolve()) if sqlite_path else None,
        sqlite_default_game,
    )


def invalidate_song_catalog_cache(
    *,
    export_root: Optional[Path | str] = None,
    sqlite_path: Optional[Path | str] = None,
):
    """
    Optional manual invalidation hook.

    Useful when:
    - export JSON updated
    - sqlite updated
    """
    global _CATALOG_CACHE

    if export_root is None and sqlite_path is None:
        _CATALOG_CACHE.clear()
        return

    keys_to_remove = []

    for k in _CATALOG_CACHE.keys():
        k_export_root, k_sqlite_path, _ = k

        if export_root and str(Path(export_root).resolve()) == k_export_root:
            keys_to_remove.append(k)

        if sqlite_path and k_sqlite_path and str(Path(sqlite_path).resolve()) == k_sqlite_path:
            keys_to_remove.append(k)

    for k in keys_to_remove:
        _CATALOG_CACHE.pop(k, None)


# --------------------------------------------------
# Cache-aware builder
# --------------------------------------------------

def build_default_song_catalog(
    *,
    export_root: Path | str = DEFAULT_SONG_DB_EXPORT_ROOT,
    sqlite_path: Optional[Path | str] = None,
    sqlite_default_game: Optional[str] = None,
    force_rebuild: bool = False,
) -> SongDatabaseCatalog:
    """
    Build (or reuse) song catalog.

    Cache strategy:
    - keyed by (export_root, sqlite_path, sqlite_default_game)
    - reused across calls within the same process
    """

    key = _catalog_cache_key(
        export_root=export_root,
        sqlite_path=sqlite_path,
        sqlite_default_game=sqlite_default_game,
    )

    # ✅ cache hit
    if not force_rebuild and key in _CATALOG_CACHE:
        return _CATALOG_CACHE[key]

    # --------------------------------------------------
    # build fresh catalog
    # --------------------------------------------------
    catalog = SongDatabaseCatalog.load_from_export_root(export_root)

    if sqlite_path is not None:
        sqlite_catalog = SongDatabaseCatalog.load_from_sqlite(
            sqlite_path,
            default_game=sqlite_default_game,
        )

        for game, rows in sqlite_catalog.rows_by_game.items():
            catalog.add_json_rows(game, rows)

    # ✅ store in cache
    _CATALOG_CACHE[key] = catalog

    return catalog


def _extract_best_song_name(obj: Dict[str, Any]) -> Optional[str]:
    file_candidate = obj.get("file_candidate") if isinstance(obj.get("file_candidate"), dict) else {}
    provenance = obj.get("_provenance") if isinstance(obj.get("_provenance"), dict) else {}

    candidates = [
        obj.get("song_name"),
        obj.get("title"),
        obj.get("name"),
        provenance.get("song_name"),
        file_candidate.get("song_name"),
        extract_song_title_from_basename(file_candidate.get("basename")),
        extract_song_title_from_basename(obj.get("basename")),
    ]

    for c in candidates:
        if canonical_song_name(c):
            return _to_text(c).strip() if c is not None else None

    return None


def resolve_song_identity(
    candidate_or_event: Dict[str, Any],
    catalog: SongDatabaseCatalog,
) -> Dict[str, Any]:
    """
    Resolve canonical song identity from an event-like dict.

    Canonical lookup field = song_name.
    song_id is used only as a secondary fallback when it appears non-synthetic.
    """
    obj = dict(candidate_or_event or {})
    file_candidate = obj.get("file_candidate") if isinstance(obj.get("file_candidate"), dict) else {}

    game = canonical_game_id(
        obj.get("game_id")
        or obj.get("game")
        or file_candidate.get("game_id")
        or file_candidate.get("game")
    )
    difficulty = (
        obj.get("difficulty")
        or file_candidate.get("difficulty")
        or extract_difficulty(file_candidate.get("basename"))
    )
    song_name = _extract_best_song_name(obj)
    song_id = obj.get("song_id") or file_candidate.get("song_id")

    match = catalog.resolve(
        game=game,
        song_name=song_name,
        difficulty=difficulty,
        song_id=song_id,
    )

    out = match.as_dict()
    out["resolved"] = bool(out.get("song_id") or out.get("canonical_song_name"))
    out["input_game"] = game
    out["input_song_name"] = song_name
    out["input_song_id"] = song_id
    out["input_difficulty"] = difficulty
    return out


__all__ = [
    "DEFAULT_SONG_DB_EXPORT_ROOT",
    "DEFAULT_SONG_INFO_SQLITE",
    "SongMatch",
    "SongDatabaseCatalog",
    "build_default_song_catalog",
    "resolve_song_identity",
    "extract_song_title_from_basename",
    "extract_difficulty",
    "canonical_game_id",
    "canonical_song_name",
    "infer_game_from_filename",
    "infer_game_from_path",
    "normalize_text",
]
