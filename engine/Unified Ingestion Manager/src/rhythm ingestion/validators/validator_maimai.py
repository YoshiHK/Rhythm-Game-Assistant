#!/usr/bin/env python3
"""validator_maimai.py

Triangular-audit alignment:
- VALIDATOR_V2_SPEC.md: validate(canonical_payload)->ValidationResult dict.
- common_validator_utils.py: uses build_validation_ok/build_validation_fail.

Policy:
- maimai is currently ingestion-only: adapter emits maimai_* events without taxonomy mapping.
- Therefore this validator returns supported=False (stop before tips pipeline), with a clear error.

This remains Phase-3 safe: no gameplay advice, no tips generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_validator import BaseValidator
from .common_validator_utils import build_validation_ok, build_validation_fail


class MaimaiValidator(BaseValidator):
    game_id = 'maimai'

    def validate(self, canonical_payload: Dict[str, Any], **_: Any) -> dict:
        errors: List[str] = []
        warnings: List[str] = []

        events = canonical_payload.get('note_events')
        if not isinstance(events, list):
            errors.append("canonical_payload['note_events'] must be a list.")
            events = []

        chart_meta = canonical_payload.get('chart_meta')
        if not isinstance(chart_meta, dict):
            errors.append("canonical_payload['chart_meta'] must be a dict.")
        else:
            if 'definition' not in chart_meta:
                errors.append("chart_meta['definition'] is required.")

        # maimai_* events exist but taxonomy mapping is not yet defined in Phase 1/2.
        maimai_notes = 0
        for ev in events:
            if isinstance(ev, dict) and str(ev.get('kind', '')).startswith('maimai_'):
                maimai_notes += 1

        if maimai_notes <= 0:
            errors.append('No maimai_* note events were produced; cannot proceed to tips pipeline.')

        # Hard stop for tips pipeline until mapping exists.
        errors.append('Tips pipeline unsupported for maimai until taxonomy mapping is defined (ingestion-only).')

        if errors:
            return build_validation_fail(errors=errors, warnings=warnings, degraded_mode=True)
        return build_validation_ok(warnings=warnings, degraded_mode=True)

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
