"""
Phase 6 Song Recommendations — Catalog Loader (Design-Locked wiring)

Purpose
-------
Load a read-only SongCatalog from canonical artifacts produced by offline ingestion
(Phase 3 / UMI). This is a wiring-only loader:

- No gameplay semantics
- No external service calls
- Deterministic output for the same inputs

This module exists to replace Softr workflow dependency on raw DB record dumps
(Song DB / Difficulty DB / Producer DB) with a platform-owned, read-only catalog.

Inputs supported:
1) Pre-loaded dict artifacts (recommended for tests)
2) Local JSON files (canonical artifacts exported by offline pipeline)

Non-goals:
- Ranking or recommendation selection
- UI concerns
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from song_catalog import SongCatalog, CatalogError


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise CatalogError(f"invalid JSON: {path} ({e})") from e
    if not isinstance(obj, dict):
        raise CatalogError(f"JSON root must be an object: {path}")
    return obj


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

    Minimal requirement:
    - songs_path must exist and be parseable.

    Optional:
    - producers_path
    - difficulty_path
    """
    if not songs_path.exists():
        raise CatalogError(f"missing songs artifact: {songs_path}")

    songs_obj = _read_json(songs_path)
    producers_obj = _read_json(producers_path) if producers_path and producers_path.exists() else {}
    diff_obj = _read_json(difficulty_path) if difficulty_path and difficulty_path.exists() else {}

    return SongCatalog.from_artifacts(
        game_id=game_id,
        songs_artifact=songs_obj,
        producers_artifact=producers_obj,
        difficulty_artifact=diff_obj,
        source_meta={
            "songs_path": str(songs_path),
            "producers_path": str(producers_path) if producers_path else None,
            "difficulty_path": str(difficulty_path) if difficulty_path else None,
        },
    )


def load_catalog_from_dir(
    *,
    game_id: str,
    root_dir: Path,
    songs_filename: str = "songs.json",
    producers_filename: str = "producers.json",
