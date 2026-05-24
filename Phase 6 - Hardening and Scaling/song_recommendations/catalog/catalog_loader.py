from __future__ import annotations

"""
Phase 6 Song Recommendations — Catalog Loader (Design-Locked wiring)

Purpose:
- Load/build a read-only SongCatalog for deterministic selection.
- Wiring-only: no gameplay semantics, no external services.

Inputs supported:
- Pre-loaded dict artifacts (recommended for tests/CI)
- Local JSON files (offline exported artifacts)

Non-goals:
- Ranking or recommendation selection
- UI concerns
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List

from .song_catalog import SongCatalog, CatalogError


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


def _fingerprint_catalog(
    songs: Dict[str, Any],
    producers: Optional[Dict[str, Any]],
    difficulty: Optional[Dict[str, Any]],
) -> str:
    parts = {
        "songs": songs,
        "producers": producers or {},
        "difficulty": difficulty or {},
    }
    return _fingerprint_dict(parts)


@dataclass(frozen=True)
class CatalogPaths:
    """
    Conventional artifact set. If your repo uses different names,
    pass explicit paths to load_catalog_from_files().
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
    producers = _read_json(producers_path) if producers_path else None
    difficulty = _read_json(difficulty_path) if difficulty_path else None

    fp = _fingerprint_catalog(songs, producers, difficulty)
    rows = _build_rows_from_artifacts(game_id, songs, producers, difficulty)

    return SongCatalog(game_id=game_id, fingerprint=fp, rows=rows)


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
    producers_path = root_dir / producers_filename
    difficulty_path = root_dir / difficulty_filename

    return load_catalog_from_files(
        game_id=game_id,
        songs_path=songs_path,
        producers_path=producers_path if producers_path.exists() else None,
        difficulty_path=difficulty_path if difficulty_path.exists() else None,
    )


def load_catalog_from_artifacts(
    *,
    game_id: str,
    capability: Any,
    artifacts: Optional[Dict[str, Any]] = None,
) -> SongCatalog:
    """
    CI-friendly builder:
    - If artifacts is provided, interpret it as {"songs":..., "producers":..., "difficulty":...}
    - If artifacts is None, synthesize a deterministic minimal catalog from capability.difficulty_tiers

    This exists so selector/coordinator tests can run without offline exported files.
    """
    if not isinstance(game_id, str) or not game_id.strip():
        raise CatalogError("game_id must be a non-empty string")

    if artifacts is not None:
        songs = artifacts.get("songs") or {}
        producers = artifacts.get("producers") or {}
        difficulty = artifacts.get("difficulty") or {}

        if not isinstance(songs, dict) or not isinstance(producers, dict) or not isinstance(difficulty, dict):
            raise CatalogError("artifacts must contain dicts: songs/producers/difficulty")

        fp = _fingerprint_catalog(songs, producers, difficulty)
        rows = _build_rows_from_artifacts(game_id, songs, producers, difficulty)
        return SongCatalog(game_id=game_id, fingerprint=fp, rows=rows)

    # Deterministic minimal catalog from capability
    tiers: List[str] = list(getattr(capability, "difficulty_tiers", []) or [])
    rows: List[Dict[str, Any]] = []
    for tier in tiers:
        for idx in range(3):
            song_id = f"{game_id}:{tier}:{idx}"
            rows.append(
                {
                    "song_id": song_id,
                    "tier_id": tier,
                    "metric": float(10 + idx),  # deterministic
                    "producer_id": f"producer:{idx}",
                }
            )

    fp = _fingerprint_dict({"game_id": game_id, "rows": rows})
    return SongCatalog(game_id=game_id, fingerprint=fp, rows=rows)


def _build_rows_from_artifacts(
    game_id: str,
    songs: Dict[str, Any],
    producers: Optional[Dict[str, Any]],
    difficulty: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert artifacts into a normalized row list for the selector.

    Minimal row contract (for selector tests):
    - song_id: str
    - tier_id: str
    - metric: float (optional; default 0.0)
    - producer_id: str (optional)
    """
    rows: List[Dict[str, Any]] = []

    # Accept either {"songs":[...]} or {"<song_id>": {...}} styles.
    song_list = songs.get("songs") if isinstance(songs.get("songs"), list) else None
    if song_list is None:
        # interpret as mapping
        song_list = []
        for sid, meta in songs.items():
            if isinstance(meta, dict):
                m = dict(meta)
                m.setdefault("song_id", sid)
                song_list.append(m)

    # difficulty may be {"difficulty":[...]} or mapping
    diff_map: Dict[str, Any] = {}
    if isinstance(difficulty, dict):
        if isinstance(difficulty.get("difficulty"), list):
            for d in difficulty["difficulty"]:
                if isinstance(d, dict) and d.get("song_id"):
                    diff_map[str(d["song_id"])] = d
        else:
            diff_map = difficulty

    for s in song_list:
        if not isinstance(s, dict):
            continue
        sid = s.get("song_id") or s.get("id")
        if not sid:
            continue
        sid = str(sid)

        d = diff_map.get(sid, {}) if isinstance(diff_map.get(sid, {}), dict) else {}
        tier_id = d.get("tier_id") or s.get("tier_id") or s.get("difficulty") or ""
        tier_id = str(tier_id) if tier_id is not None else ""

        metric = d.get("metric") or d.get("level") or s.get("metric") or 0.0
        try:
            metric_f = float(metric)
        except Exception:
            metric_f = 0.0

        producer_id = s.get("producer_id") or s.get("producer") or ""
        producer_id = str(producer_id) if producer_id is not None else ""

        rows.append(
            {
                "song_id": sid,
                "tier_id": tier_id,
                "metric": metric_f,
                "producer_id": producer_id,
            }
        )

    return rows


__all__ = [
    "CatalogError",
    "SongCatalog",
    "CatalogPaths",
    "load_catalog_from_files",
    "load_catalog_from_dir",
    "load_catalog_from_artifacts",
]