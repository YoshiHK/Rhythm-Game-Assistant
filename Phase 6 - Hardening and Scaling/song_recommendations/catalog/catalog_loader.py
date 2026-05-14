"""
Phase 6 Song Recommendations — Catalog Loader (Design-Locked wiring)

### Purpose

Load a read-only SongCatalog from canonical artifacts produced by offline ingestion
(Phase 3 / UMI). This is a wiring-only loader:
- No gameplay semantics
- No external service calls
- Deterministic output for the same inputs

This module exists to replace Softr workflow dependency on raw DB record dumps
(Song DB / Difficulty DB / Producer DB) with a platform-owned, read-only catalog.

Inputs supported:
- Pre-loaded dict artifacts (recommended for tests)
- Local JSON files (canonical artifacts exported by offline pipeline)

Non-goals:
- Ranking or recommendation selection
- UI concerns
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Support both package and flat imports
try:
    from phase6.song_recommendation.catalog.song_catalog import SongCatalog, CatalogError  # type: ignore
except Exception:
    from song_catalog import SongCatalog, CatalogError  # type: ignore


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise CatalogError(f"invalid JSON: {path}") from e
    if not isinstance(obj, dict):
        raise CatalogError(f"JSON root must be an object: {path}")
    return obj


def _fingerprint_dict(obj: Dict[str, Any]) -> str:
    """
    Deterministic short fingerprint for catalog components.
    Used for diagnostics/learning-loop provenance only.
    """
    text = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _fingerprint_catalog(songs: Dict[str, Any],
                         producers: Optional[Dict[str, Any]],
                         difficulty: Optional[Dict[str, Any]]) -> str:
    parts = {
        "songs": songs,
        "producers": producers or {},
        "difficulty": difficulty or {},
    }
    return _fingerprint_dict(parts)


@dataclass(frozen=True)
class CatalogPaths:
    """
    A conventional set of artifact files.
    If your repo uses different names, pass explicit paths to load_catalog_from_files().
    """
    songs: Path
    producers: Optional[Path] = None
    difficulty: Optional[Path] = None


def load_catalog_from_files(
    *,
    game_id: str,
    songs_path: Path,
    producers_path: Optional[Path] = None,
    difficulty_path: Optional[Path] = None,
) -> SongCatalog:
    """
    Load catalog from explicit JSON files.
    """
    if not isinstance(game_id, str) or not game_id.strip():
        raise CatalogError("game_id must be a non-empty string")

    songs = _read_json(songs_path)
    producers = _read_json(producers_path) if producers_path is not None and producers_path.exists() else None
    difficulty = _read_json(difficulty_path) if difficulty_path is not None and difficulty_path.exists() else None

    fingerprint = _fingerprint_catalog(songs, producers, difficulty)

    # Delegate to SongCatalog constructor/factory (no semantics here)
    try:
        # If SongCatalog provides a from_artifacts API, prefer it.
        from_artifacts = getattr(SongCatalog, "from_artifacts", None)
        if callable(from_artifacts):
            return from_artifacts(
                game_id=game_id,
                songs=songs,
                producers=producers,
                difficulty=difficulty,
                catalog_fingerprint=fingerprint,
            )
    except Exception:
        # Fall through to generic constructor below
        pass

    # Generic fallback: store artifacts + fingerprint inside catalog.
    # SongCatalog implementation decides how to interpret.
    return SongCatalog(
        game_id=game_id,
        songs=songs,
        producers=producers,
        difficulty=difficulty,
        catalog_fingerprint=fingerprint,
    )


def load_catalog_from_dir(
    *,
    game_id: str,
    root_dir: Path,
    songs_filename: str = "songs.json",
    producers_filename: str = "producers.json",
    difficulty_filename: str = "song_difficulty.json",
) -> SongCatalog:
    """
    Load catalog from a conventional directory layout:
      root_dir/
        songs.json
        producers.json (optional)
        song_difficulty.json (optional)
    """
    if not root_dir.exists():
        raise CatalogError(f"catalog root_dir not found: {root_dir}")

    songs_path = root_dir / songs_filename
    if not songs_path.exists():
        raise CatalogError(f"missing songs artifact: {songs_path}")

    producers_path = root_dir / producers_filename
    difficulty_path = root_dir / difficulty_filename

    return load_catalog_from_files(
        game_id=game_id,
        songs_path=songs_path,
        producers_path=producers_path if producers_path.exists() else None,
        difficulty_path=difficulty_path if difficulty_path.exists() else None,
    )