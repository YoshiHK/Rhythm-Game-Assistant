
"""
Phase 6 Song Recommendations — SongCatalog (read-only)

Purpose
-------
Provide a stable, read-only catalog interface for song recommendation wiring.

Key constraints:
- No external I/O
- Deterministic iteration and tie-break (stable ordering)
- Multi-game safe (tier ids and completion labels are opaque to this layer)

The catalog is built from canonical artifacts produced offline (Phase 3 / UMI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


class CatalogError(ValueError):
    """Raised when catalog artifacts are missing required shape/fields."""


@dataclass(frozen=True)
class Song:
    song_id: str
    name: str
    producer_id: Optional[str] = None
    producer_name: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Producer:
    producer_id: str
    name: str
    avg_difficulty: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DifficultyRecord:
    """
    DifficultyRecord connects a song to a difficulty tier with a numeric metric.

    metric can be:
    - 'level' (preferred): chart level / numeric difficulty
    - 'count' (legacy): count-based bucket from older workflows

    tier_id is game-scoped (e.g., 'expert', 'master', 'append', or other games).
    """
    song_id: str
    tier_id: str
    metric: float
    producer_id: Optional[str] = None
    producer_name: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


def _as_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return str(x).strip() or None


def _as_float(x: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return default


class SongCatalog:
    """
    Read-only catalog. Provides stable lookups for:
    - songs
    - producers
    - per-tier difficulty records (sorted deterministically)
    """

    def __init__(
        self,
        *,
        game_id: str,
        fingerprint: str = "",
        songs: Optional[Dict[str, Song]] = None,
        producers: Optional[Dict[str, Producer]] = None,
        difficulty_records: Optional[List[DifficultyRecord]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        source_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Keep compatibility with CI loader stub that may pass rows-only
        self.game_id = game_id
        self.fingerprint = fingerprint
        self.source_meta = source_meta or {}

        self._songs: Dict[str, Song] = songs or {}
        self._producers: Dict[str, Producer] = producers or {}
        self._difficulty_records: List[DifficultyRecord] = difficulty_records or []

        # Optional "rows" passthrough for simpler selectors/tests
        self.rows: List[Dict[str, Any]] = rows or []

        # Index difficulty by tier for deterministic retrieval
        self._difficulty_by_tier: Dict[str, List[DifficultyRecord]] = {}
        for dr in self._difficulty_records:
            self._difficulty_by_tier.setdefault(dr.tier_id, []).append(dr)

        for tier_id, arr in self._difficulty_by_tier.items():
            arr.sort(key=lambda r: (r.metric, r.song_id))

    # --------------------
    # Constructors
    # --------------------

    @staticmethod
    def from_artifacts(
        *,
        game_id: str,
        songs_artifact: Dict[str, Any],
        producers_artifact: Optional[Dict[str, Any]] = None,
        difficulty_artifact: Optional[Dict[str, Any]] = None,
        fingerprint: str = "",
        source_meta: Optional[Dict[str, Any]] = None,
    ) -> "SongCatalog":
        """
        Build catalog from canonical artifacts.

        Supported shapes (flexible):
        - songs_artifact:
            {"songs":[{id/name/...}]}, or {"items":[...]}, or {"data":[...]}
        - producers_artifact:
            {"producers":[...]}, or {"items":[...]}, or {"data":[...]}
        - difficulty_artifact:
            {"difficulty":[...]}, or {"items":[...]}, or {"data":[...]}
        """
        if not isinstance(songs_artifact, dict):
            raise CatalogError("songs_artifact must be an object")

        songs_list = (
            songs_artifact.get("songs")
            or songs_artifact.get("items")
            or songs_artifact.get("data")
            or []
        )
        if not isinstance(songs_list, list) or not songs_list:
            raise CatalogError("songs artifact has no songs list (songs/items/data)")

        # Producers
        producers_map: Dict[str, Producer] = {}
        if isinstance(producers_artifact, dict):
            prod_list = (
                producers_artifact.get("producers")
                or producers_artifact.get("items")
                or producers_artifact.get("data")
                or []
            )
            if isinstance(prod_list, list):
                for p in prod_list:
                    if not isinstance(p, dict):
                        continue
                    pid = _as_str(p.get("producer_id") or p.get("id"))
                    name = _as_str(p.get("name") or p.get("producer_name"))
                    if not pid or not name:
                        continue

                    avg_val = p.get("avg_difficulty") or p.get("avg") or p.get("Lr3Rr")
                    producers_map[pid] = Producer(
                        producer_id=pid,
                        name=name,
                        avg_difficulty=_as_float(avg_val, default=None) if avg_val is not None else None,
                        meta={k: v for k, v in p.items() if k not in {
                            "id", "producer_id", "name", "producer_name", "avg", "avg_difficulty", "Lr3Rr"
                        }},
                    )

        # Songs
        songs_map: Dict[str, Song] = {}
        for s in songs_list:
            if not isinstance(s, dict):
                continue
            sid = _as_str(s.get("song_id") or s.get("id"))
            name = _as_str(s.get("name") or s.get("song_name"))
            if not sid or not name:
                continue

            pid = _as_str(s.get("producer_id"))
            pname = _as_str(s.get("producer_name"))
            if pid and not pname and pid in producers_map:
                pname = producers_map[pid].name

            songs_map[sid] = Song(
                song_id=sid,
                name=name,
                producer_id=pid,
                producer_name=pname,
                meta={k: v for k, v in s.items() if k not in {
                    "id", "song_id", "name", "song_name", "producer_id", "producer_name"
                }},
            )

        # Difficulty records
        difficulty_records: List[DifficultyRecord] = []
        dr_list: List[Any] = []
        if isinstance(difficulty_artifact, dict):
            dr_list = (
                difficulty_artifact.get("difficulty")
                or difficulty_artifact.get("items")
                or difficulty_artifact.get("data")
                or []
            )
        if isinstance(dr_list, list):
            for d in dr_list:
                if not isinstance(d, dict):
                    continue
                song_id = _as_str(d.get("song_id") or d.get("id"))
                tier_id = _as_str(d.get("tier_id") or d.get("difficulty"))
                if not song_id or not tier_id:
                    continue

                metric_val = d.get("level")
                if metric_val is None:
                    metric_val = d.get("count")
                metric = float(_as_float(metric_val, default=0.0) or 0.0)

                pid = _as_str(d.get("producer_id"))
                pname = _as_str(d.get("producer_name"))
                if pid and not pname and pid in producers_map:
                    pname = producers_map[pid].name
                if not pid:
                    srec = songs_map.get(song_id)
                    pid = srec.producer_id if srec else None
                    pname = pname or (srec.producer_name if srec else None)

                difficulty_records.append(
                    DifficultyRecord(
                        song_id=song_id,
                        tier_id=tier_id,
                        metric=metric,
                        producer_id=pid,
                        producer_name=pname,
                        meta={k: v for k, v in d.items() if k not in {
                            "song_id", "id", "tier_id", "difficulty", "level", "count", "producer_id", "producer_name"
                        }},
                    )
                )

        return SongCatalog(
            game_id=game_id,
            fingerprint=fingerprint,
            songs=songs_map,
            producers=producers_map,
            difficulty_records=difficulty_records,
            rows=[],  # optional; can be filled by loader if needed
            source_meta=source_meta or {},
        )

    # --------------------
    # Read-only accessors
    # --------------------

    def get_song(self, song_id: str) -> Optional[Song]:
        return self._songs.get(song_id)

    def get_producer(self, producer_id: str) -> Optional[Producer]:
        return self._producers.get(producer_id)

    def iter_songs(self) -> Iterable[Song]:
        for sid in sorted(self._songs.keys()):
            yield self._songs[sid]

    def iter_difficulty(self, tier_id: str) -> List[DifficultyRecord]:
        return list(self._difficulty_by_tier.get(tier_id, []))

    def has_tier(self, tier_id: str) -> bool:
        return tier_id in self._difficulty_by_tier

    # --------------------
    # Deterministic selection helper (optional)
    # --------------------

    def deterministic_pick_song(
        self,
        *,
        tier_id: str,
        target_metric: float,
        producer_whitelist: Optional[List[str]] = None,
        excluded_song_ids: Optional[set] = None,
        window: float = 2.0,
    ) -> Optional[Dict[str, Any]]:
        excluded = excluded_song_ids or set()
        wl = set(producer_whitelist) if producer_whitelist else None

        candidates: List[Tuple[float, str, DifficultyRecord]] = []
        for dr in self.iter_difficulty(tier_id):
            if dr.song_id in excluded:
                continue
            if wl is not None and dr.producer_id and dr.producer_id not in wl:
                continue
            if abs(dr.metric - target_metric) > window:
                continue
            candidates.append((abs(dr.metric - target_metric), dr.song_id, dr))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (x[0], x[1]))
        _, sid, dr = candidates[0]
        song = self.get_song(sid)

        return {
            "song_id": sid,
            "song_name": song.name if song else sid,
            "producer_name": dr.producer_name or (song.producer_name if song else None) or "Unknown Producer",
            "tier_id": tier_id,
            "metric": dr.metric,
            "rationale": {
                "summary": "Deterministic selection from catalog window",
                "why": [f"tier={tier_id}", f"target≈{target_metric}", f"metric={dr.metric}"],
            },
        }


__all__ = [
    "CatalogError",
    "Song",
    "Producer",
    "DifficultyRecord",
    "SongCatalog",
]