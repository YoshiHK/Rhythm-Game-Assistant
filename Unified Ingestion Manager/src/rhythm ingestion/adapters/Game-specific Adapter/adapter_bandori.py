
#!/usr/bin/env python3
"""adapter_bandori.py

Bandori adapter (canonical payload capable) for UMI.

Naming policy:
- No version suffix in filename.
- Versioning is handled via adapter_metadata fields (adapter_id/adapter_version).

Grounding:
- Uses Bandori primitives provided by <File>bandori_model.py</File> and <File>bandori_chart.py</File>.
- Bandori chart JSON is parsed via Pydantic models.

Produces:
- CanonicalSongRow (writer-facing)
- CanonicalChartPayload (pipeline-facing) via to_canonical_payload()

Constraints:
- Pure structural normalization only.
- No tips / no element inference / no gameplay semantics.

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter
from .adapter_payload_utils import (
    build_adapter_metadata,
    attach_adapter_metadata,
    attach_internal_metadata,
)

# Prefer the package's intended module names (.model / .chart).
# Your uploaded files are named bandori_model.py / bandori_chart.py, but bandori_chart imports .model.
# To keep this adapter resilient, we try both.
try:
    from .model import Chart, ChartMeta, BPM, Command, Single, Directional, Slide, Connection  # type: ignore
except Exception:
    from .bandori_model import Chart, ChartMeta, BPM, Command, Single, Directional, Slide, Connection  # type: ignore

try:
    from .chart import get_max_beat, get_notes_for_type  # type: ignore
except Exception:
    from .bandori_chart import get_max_beat, get_notes_for_type  # type: ignore


class BandoriAdapter(BaseAdapter):
    """Bandori adapter for UMI routing + canonicalization."""

    game_id: str = "bandori"
    adapter_id: str = "adapter_bandori"
    adapter_version: str = "1.0.0"

    # ----------------------------
    # BaseAdapter required methods
    # ----------------------------

    def accepts_file(self, path: Any) -> bool:
        p = Path(str(path))
        return p.suffix.lower() == ".json"

    def load(self, path: Any) -> Dict[str, Any]:
        """Load a Bandori chart JSON.

        Supported shapes (best-effort):
        - A raw chart list (list of note objects)
        - An object containing {"chart": <chart>} (e.g., user post)
        - An object containing {"post": { ... "chart": ... }}

        Returns dict with keys: chart, meta (optional), bpms.
        """
        p = Path(str(path))
        data = json.loads(p.read_text(encoding="utf-8"))

        chart_obj = None
        meta_obj = None

        # 1) chart-only list
        if isinstance(data, list):
            chart_obj = Chart.model_validate(data)

        # 2) dict containers
        elif isinstance(data, dict):
            if "chart" in data:
                chart_obj = Chart.model_validate(data.get("chart"))
            elif "post" in data and isinstance(data.get("post"), dict) and "chart" in data["post"]:
                chart_obj = Chart.model_validate(data["post"].get("chart"))
            elif "__root__" in data:
                chart_obj = Chart.model_validate(data)

            # meta extraction (best-effort)
            # User post-like keys: id/title/level/diff/time/result/song/artists
            if all(k in data for k in ("title", "level", "diff")):
                try:
                    meta_obj = ChartMeta(
                        id=int(data.get("id") or 0),
                        title=str(data.get("title")),
                        level=int(data.get("level")),
                        difficulty=int(data.get("diff")),
                        release=__import__("datetime").datetime.datetime.utcfromtimestamp(int(data.get("time") or 0)),
                        is_official=bool(data.get("result", False)),
                        artist=str(data.get("artists")) if data.get("artists") else None,
                        chart_designer=None,
                        lyricist=None,
                        composer=None,
                        arranger=None,
                    )
                except Exception:
                    meta_obj = None

        if chart_obj is None:
            raise ValueError(f"Unsupported Bandori chart JSON shape: {p}")

        # Extract BPM events from chart
        bpms = list(get_notes_for_type(chart_obj, BPM))
        bpms_sorted = sorted(bpms, key=lambda b: float(b.beat)) if bpms else []

        return {"chart": chart_obj, "meta": meta_obj, "bpms": bpms_sorted}

    def to_canonical_row(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        chart: Chart = raw["chart"]
        meta: Optional[ChartMeta] = raw.get("meta")
        bpms: List[BPM] = raw.get("bpms") or []

        song_id = int(meta.id) if meta is not None else None
        difficulty_label = None
        level = None

        if meta is not None:
            # DifficultyInt is an IntEnum; convert to string name if available
            try:
                difficulty_label = getattr(meta.difficulty, "name", None) or str(meta.difficulty)
            except Exception:
                difficulty_label = str(meta.difficulty)
            level = int(meta.level)

        max_time_beats = float(get_max_beat(chart))

        bpm_val = int(bpms[0].bpm) if bpms else None

        return {
            "game_id": self.game_id,
            "song_id": song_id,
            "difficulty_label": difficulty_label,
            "level": level,
            "bpm": bpm_val,
            "max_time_beats": max_time_beats,
        }

    # ----------------------------
    # Optional canonical payload
    # ----------------------------

    def to_canonical_payload(self, path: str) -> Dict[str, Any]:
        raw = self.load(path)
        chart: Chart = raw["chart"]
        meta: Optional[ChartMeta] = raw.get("meta")
        bpms: List[BPM] = raw.get("bpms") or []

        row = self.to_canonical_row(raw)

        chart_id = str(row.get("song_id") or Path(path).stem)
        difficulty = str(row.get("difficulty_label") or "unknown")

        # chart_meta required by schema
        bpm0 = float(bpms[0].bpm) if bpms else float(row.get("bpm") or 0)
        chart_meta: Dict[str, Any] = {
            "bpm": bpm0,
            "max_time_beats": float(row.get("max_time_beats") or 0.0),
        }

        # bpm_changes (optional)
        bpm_changes: List[Dict[str, Any]] = []
        for b in bpms:
            bpm_changes.append({"time_beats": float(b.beat), "bpm": float(b.bpm)})
        if bpm_changes:
            chart_meta["bpm_changes"] = bpm_changes

        note_events = self._to_note_events(chart)

        payload: Dict[str, Any] = {
            "game_id": self.game_id,
            "chart_id": chart_id,
            "difficulty": difficulty,
            "note_events": note_events,
            "chart_meta": chart_meta,
        }

        meta_block = build_adapter_metadata(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            source_format="json",
            source_path=str(path),
        )
        attach_adapter_metadata(payload, meta_block)

        attach_internal_metadata(
            payload,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            sections_source="bandori",
        )

        return payload

    # ----------------------------
    # Note normalization
    # ----------------------------

    def _to_note_events(self, chart: Chart) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        for note in getattr(chart, "__root__", []) or []:
            # Skip BPM and system commands from note_events
            if isinstance(note, BPM) or isinstance(note, Command):
                continue

            # Slide/Long: emit connections
            if isinstance(note, Slide):
                conns = list(note.connections or [])
                for i, c in enumerate(conns):
                    if c.hidden:
                        continue
                    out.append(self._event_from_connection(c, i, len(conns)))
                continue

            if isinstance(note, Directional):
                out.append(self._event_from_directional(note))
                continue

            if isinstance(note, Single):
                out.append(self._event_from_single(note))
                continue

        out.sort(key=lambda e: (float(e.get("time_beats", 0.0)), float(e.get("lane", 0.0)), str(e.get("kind", ""))))
        return out

    def _event_from_single(self, n: Single) -> Dict[str, Any]:
        kind = "flick" if n.flick else "tap"
        extra: Dict[str, Any] = {}
        if n.skill:
            extra["skill"] = True
        if n.charge:
            extra["charge"] = True
        return {
            "time_beats": float(n.beat),
            "lane": float(n.lane),
            "kind": kind,
            "extra": extra,
        }

    def _event_from_directional(self, n: Directional) -> Dict[str, Any]:
        # Directional is a flick-like object; we preserve direction/width.
        extra: Dict[str, Any] = {
            "direction": str(n.direction),
            "width_lanes": float(n.width),
        }
        return {
            "time_beats": float(n.beat),
            "lane": float(n.lane),
            "kind": "flick_arrow",
            "extra": extra,
        }

    def _event_from_connection(self, c: Connection, idx: int, total: int) -> Dict[str, Any]:
        # Endpoints use hold_body_or_start unless they are flick endpoints.
        if idx == 0 or idx == total - 1:
            kind = "flick" if c.flick else "hold_body_or_start"
        else:
            kind = "hold_path"
        extra: Dict[str, Any] = {}
        if c.skill:
            extra["skill"] = True
        if c.charge:
            extra["charge"] = True
        return {
            "time_beats": float(c.beat),
            "lane": float(c.lane),
            "kind": kind,
            "extra": extra,
        }


__all__ = ["BandoriAdapter"]
