#!/usr/bin/env python3
"""validator_maimai.py

UMI Phase 3 validator for maimai.

Structural validation only:
- note_events must be a list
- note_total_chart == count(kind startswith 'maimai_')
- chart_meta is dict and contains definition
- bpm_changes optional shape validation
- time_ms non-decreasing
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator


class MaimaiValidator(BaseValidator):
    game_id = 'maimai'

    def validate(self, *, raw_chart: Any, canonical_payload: Dict[str, Any], canonical_row: Dict[str, Any]) -> None:
        errors: List[str] = []

        for k in ('game', 'song_id', 'note_total_chart', 'chart_path'):
            if k not in canonical_row:
                errors.append(f"Missing required field '{k}' in canonical_row.")

        if canonical_row.get('game') not in (self.game_id, 'maimai'):
            errors.append(f"canonical_row['game'] must be 'maimai', got {canonical_row.get('game')!r}.")

        ntc = canonical_row.get('note_total_chart')
        if not isinstance(ntc, int) or ntc < 0:
            errors.append(f"canonical_row['note_total_chart'] must be int >= 0, got {ntc!r}.")

        events = canonical_payload.get('note_events')
        if not isinstance(events, list):
            errors.append("canonical_payload['note_events'] must be a list.")
            events = []

        calc = 0
        for ev in events:
            if isinstance(ev, dict) and str(ev.get('kind','')).startswith('maimai_'):
                calc += 1

        if isinstance(ntc, int) and ntc != calc:
            errors.append(f"note_total_chart ({ntc}) must equal count(maimai_* events) ({calc}).")

        chart_meta = canonical_payload.get('chart_meta')
        if not isinstance(chart_meta, dict):
            errors.append("canonical_payload['chart_meta'] must be a dict.")
        else:
            if 'definition' not in chart_meta:
                errors.append("chart_meta['definition'] is required.")
            bpm_changes = chart_meta.get('bpm_changes')
            if bpm_changes is not None:
                if not isinstance(bpm_changes, list):
                    errors.append("chart_meta['bpm_changes'] must be a list when present.")
                else:
                    for i, bc in enumerate(bpm_changes[:50]):
                        if not isinstance(bc, dict):
                            errors.append(f"bpm_changes[{i}] must be a dict.")
                            break
                        if 'bpm' not in bc or 'time_beats' not in bc:
                            errors.append(f"bpm_changes[{i}] must contain bpm and time_beats.")
                            break

        last_ms = None
        for ev in events:
            if not isinstance(ev, dict):
                continue
            tms = ev.get('time_ms')
            if isinstance(tms, int):
                if last_ms is not None and tms < last_ms:
                    errors.append('event time_ms is not non-decreasing (ordering invariant violated).')
                    break
                last_ms = tms

        if errors:
            raise ValueError(f"MaimaiValidator failed for song_id={canonical_row.get('song_id')!r}: " + '; '.join(errors))

    def capabilities(self) -> dict:
        return {
            'note_model': 'touch_radial',
            'supports_sections': False,
            'supports_variable_bpm': True,
            'supports_width': False,
            'time_unit': 'beats+ms',
            'parse_level': 'events_v3',
        }


__all__ = ['MaimaiValidator']
