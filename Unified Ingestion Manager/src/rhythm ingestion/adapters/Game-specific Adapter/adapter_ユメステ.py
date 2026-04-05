#!/usr/bin/env python3
"""adapter_ユメステ.py

UMI Phase 3 adapter for ユメステ (夢のステラリウム / World Dai Star).

This version explicitly wires the shared SUS -> canonical extractor:
  extract_yumesute_note_events_from_sus()

Grounding (from repo file "canonical note_events.py"):
- ticks_per_beat is assumed to be 480 and tick->beats is tick/480.
- score.taps yields tap notes where t.type: 1 normal, 2 critical, 3 flick.
- score.slides yields holds/slides; extractor emits hold start/body/end events.
- chart_meta includes bpm, max_time_beats, optional bpm_changes.

Scope (Phase 3 / ADAPTER_V2_SPEC):
- Structural normalization only.
- No gameplay semantics inference.
- Preserve raw tokens/fields in extra.

Canonical payload ordering follows the project ordering convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from .base_adapter import BaseAdapter


# ----------------------------
# Shared extractor (wired)
# ----------------------------

try:
    # Prefer the canonical extractor module name if present.
    # If your repo keeps it under a different filename, adjust import path accordingly.
    from .yumesute_sus_extract import extract_yumesute_note_events_from_sus  # type: ignore
except Exception:
    # Fallback: local implementation copied from "canonical note_events.py" is embedded below.
    extract_yumesute_note_events_from_sus = None  # type: ignore


def _tick_to_beats(tick: int) -> float:
    return float(tick) / 480.0


def _bpm_changes(score) -> list[dict]:
    out = []
    for tick, bpm in (getattr(score, 'bpms', None) or []):
        out.append({'time_beats': _tick_to_beats(int(tick)), 'bpm': float(bpm)})
    return out


def _base_bpm(score) -> float:
    bpms = getattr(score, 'bpms', None) or []
    if not bpms:
        return 0.0
    return float(bpms[0][1])


def _extract_local(sus_text: str, *, lane_offset: int = 2) -> dict:
    """Local fallback extractor (from canonical note_events.py)"""
    import sus  # type: ignore

    score = sus.loads(sus_text)
    note_events: list[dict] = []

    # TAP / CRITICAL / FLICK
    for t in getattr(score, 'taps', []) or []:
        tick = int(t.tick)
        lane = int(t.lane) - lane_offset + 1
        width = int(getattr(t, 'width', 1) or 1)
        kind = 'tap'
        raw_type = 'tap'
        if int(getattr(t, 'type', 1) or 1) == 2:
            kind = 'critical_tap'
            raw_type = 'tap_critical'
        elif int(getattr(t, 'type', 1) or 1) == 3:
            kind = 'flick_arrow'
            raw_type = 'flick'
        note_events.append({
            'time_beats': _tick_to_beats(tick),
            'lane': lane,
            'kind': kind,
            'extra': {
                'raw_type': raw_type,
                'width_lanes': width,
                'tick': tick,
            }
        })

    # HOLDS / SLIDES
    slides = getattr(score, 'slides', None) or []
    for hold in sorted(slides, key=lambda s: s[0].tick):
        start = hold[0]
        end = hold[-1]
        start_tick = int(start.tick)
        end_tick = int(end.tick)
        lane = int(start.lane) - lane_offset + 1
        width = int(getattr(start, 'width', 1) or 1)
        start_beats = _tick_to_beats(start_tick)
        end_beats = _tick_to_beats(end_tick)

        note_events.append({
            'time_beats': start_beats,
            'lane': lane,
            'kind': 'hold_body_or_start',
            'extra': {'raw_type': 'hold_start', 'width_lanes': width, 'tick': start_tick},
        })
        note_events.append({
            'time_beats': start_beats,
            'lane': lane,
            'kind': 'hold_path',
            'extra': {
                'raw_type': 'hold_body',
                'width_lanes': width,
                'tick': start_tick,
                'rect_height': max(0.0, end_beats - start_beats),
                'shape': 'hold',
            },
        })
        note_events.append({
            'time_beats': end_beats,
            'lane': lane,
            'kind': 'hold_body_or_start',
            'extra': {'raw_type': 'hold_end', 'width_lanes': width, 'tick': end_tick},
        })

    note_events.sort(key=lambda e: (float(e['time_beats']), int(e['lane']), str(e['kind'])))

    max_tick = 0
    for ev in note_events:
        max_tick = max(max_tick, int(ev.get('extra', {}).get('tick', 0)))

    chart_meta = {
        'bpm': _base_bpm(score),
        'max_time_beats': _tick_to_beats(max_tick),
    }
    bpm_changes = _bpm_changes(score)
    if bpm_changes:
        chart_meta['bpm_changes'] = bpm_changes

    return {'chart_meta': chart_meta, 'note_events': note_events}


def extract_yumesute_note_events_from_sus_wired(sus_text: str, *, lane_offset: int = 2) -> dict:
    """Unified entrypoint. Uses shared extractor if importable, otherwise local fallback."""
    if extract_yumesute_note_events_from_sus is not None:
        return extract_yumesute_note_events_from_sus(sus_text, lane_offset=lane_offset)
    return _extract_local(sus_text, lane_offset=lane_offset)


# ----------------------------
# Raw ingestion model
# ----------------------------

@dataclass
class ユメステIngestRaw:
    chart_path: Path
    song_id: str
    difficulty_name: str


def _infer_song_id_and_difficulty(path: Path) -> Tuple[str, str]:
    stem = path.stem
    diff = 'UNKNOWN'
    song = stem
    if '[' in stem and ']' in stem:
        try:
            l = stem.rfind('[')
            r = stem.rfind(']')
            if 0 <= l < r:
                diff = stem[l+1:r].strip() or diff
                song = stem[:l].strip() or stem
        except Exception:
            pass
    return song, diff


# ----------------------------
# Payload builder
# ----------------------------


def build_canonical_payload_yumesute(source_ref: str, *, lane_offset: int = 2) -> Dict[str, Any]:
    path = Path(source_ref)
    sus_text = path.read_text(encoding='utf-8', errors='ignore')

    extracted = extract_yumesute_note_events_from_sus_wired(sus_text, lane_offset=lane_offset)
    note_events = list(extracted.get('note_events') or [])
    chart_meta = dict(extracted.get('chart_meta') or {})

    # Ensure max_time_beats exists.
    if 'max_time_beats' not in chart_meta:
        mt = 0.0
        for ev in note_events:
            try:
                mt = max(mt, float(ev.get('time_beats', 0.0)))
            except Exception:
                pass
        chart_meta['max_time_beats'] = mt

    song_id, diff = _infer_song_id_and_difficulty(path)

    adapter_metadata: Dict[str, Any] = {
        'adapter_id': 'adapter_yumesute',
        'adapter_version': '1.0.0',
        'source_format': 'sus',
        'source_path': str(path),
        'notes': 'YMST adapter wiring extract_yumesute_note_events_from_sus() into Phase 3 canonical payload.',
    }

    diagnostics: Dict[str, Any] = {
        'note_events_count': len(note_events),
        'bpm_changes_count': len(chart_meta.get('bpm_changes') or []),
        'lane_offset': lane_offset,
    }

    internal_metadata: Dict[str, Any] = {
        'adapter_id': adapter_metadata.get('adapter_id'),
        'adapter_version': adapter_metadata.get('adapter_version'),
        'sections_source': None,
    }

    return {
        'game_id': 'yumesute',
        'chart_id': str(path),
        'difficulty': diff,
        'note_events': note_events,
        'chart_meta': chart_meta,
        'adapter_metadata': adapter_metadata,
        'diagnostics': diagnostics,
        'internal_metadata': internal_metadata,
    }


# ----------------------------
# Adapter implementation
# ----------------------------


class ユメステAdapter(BaseAdapter):
    game_id = 'yumesute'

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {'.sus', '.txt'}

    def load(self, path: Path) -> ユメステIngestRaw:
        song_id, diff = _infer_song_id_and_difficulty(path)
        return ユメステIngestRaw(chart_path=path, song_id=song_id, difficulty_name=diff)

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_yumesute(source_ref)

    def to_canonical_row(self, raw: ユメステIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        note_events = payload.get('note_events') or []
        note_total_chart = len(note_events) if isinstance(note_events, list) else 0
        chart_meta = payload.get('chart_meta') or {}

        return {
            'game': self.game_id,
            'song_id': raw.song_id,
            'difficulty_label': payload.get('difficulty') or raw.difficulty_name or 'UNKNOWN',
            'note_total_chart': int(note_total_chart),
            'duration_ms': None,
            'bpm': chart_meta.get('bpm'),
            'chart_path': str(raw.chart_path),
            'max_time_beats': chart_meta.get('max_time_beats'),
        }

    def capabilities(self) -> dict:
        return {
            'note_model': 'lane_based',
            'supports_sections': False,
            'supports_variable_bpm': True,
            'emits_canonical_payload': True,
            'source_format': 'sus',
        }


__all__ = [
    'ユメステAdapter',
    'ユメステIngestRaw',
    'build_canonical_payload_yumesute',
    'extract_yumesute_note_events_from_sus_wired',
]
