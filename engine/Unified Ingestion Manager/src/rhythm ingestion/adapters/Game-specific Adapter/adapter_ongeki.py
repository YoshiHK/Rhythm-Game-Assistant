#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adapter_ongeki.py

UMI Phase 3 adapter for ONGEKI.

Purpose
-------
This adapter is responsible for **Phase 3 ingestion and canonicalization** of
ONGEKI charts. It prepares structured inputs for downstream analysis and tips
pipelines, but does not itself perform gameplay analysis or tips generation.

What this adapter DOES
----------------------
- Parse ONGEKI chart sources (.html/.htm chart archive exports, .ogkr editor files)
- Canonicalize metadata (title, difficulty, bpm, etc.)
- Extract timing-related information (BPM / MET / SFL)
- Capture timing positions (measure / tick) when available
- Perform best-effort conversion from (measure, tick) → time_beats
- Emit a minimal timing surface suitable for Phase 3 validation and QA

What this adapter intentionally DOES NOT do (by design)
-------------------------------------------------------
- It does NOT generate gameplay tips at the adapter stage
- It does NOT infer gameplay semantics during ingestion
- It does NOT compute density / coverage / window segmentation at this stage

These responsibilities belong to downstream pipelines
(Phase 1–2 tips generation and Phase 4+ personalization),
once sufficient semantic and visual information is available.

Design Notes
------------
- This adapter follows the same Phase 3 discipline as other game adapters:
  ingestion is kept deterministic, auditable, and side-effect free.
- The presence of this adapter indicates that ONGEKI is a **planned and supported
  game** in the app; it does not imply limitations on tips or analysis capabilities.
- Downstream systems may enrich the canonical payload with gameplay objects,
  SectionMetrics, pattern tags, and tips when supported.

Completed phases are immutable; this adapter only prepares canonical inputs.
"""

from __future__ import annotations

from typing import Any, Dict

# Import the original adapter.
# This file assumes it lives in the same package.
from .adapter_ongeki import OngekiAdapter  # type: ignore


def _ensure_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _deep_setdefault(root: Dict[str, Any], path: str, default: Any) -> None:
    """Set nested default value by dotted path if missing."""
    cur = root
    parts = path.split('.')
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur.setdefault(parts[-1], default)


def augment_ongeki_payload(canonical_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Inject Phase-3-safe placeholders and capability flags."""

    payload = _ensure_dict(canonical_payload)

    # Ensure top-level containers exist (these are already present in many adapters, but keep safe).
    payload.setdefault('lanes', [])
    payload.setdefault('objects', [])
    payload.setdefault('timeline_events', [])
    payload.setdefault('area_objects', [])

    extra = payload.setdefault('extra', {})
    if not isinstance(extra, dict):
        extra = {}
        payload['extra'] = extra

    # Capability flags: explicit present vs planned.
    # Do NOT claim tips/semantics/density exist.
    extra.setdefault('capabilities', {
        'timing_surface': {'present': True, 'planned': True, 'notes': 'Timing surface is best-effort from HTML/OGKR sources.'},
        'reconstructed_gameplay_objects': {'present': False, 'planned': True, 'notes': 'Not available in Phase 3 ingestion sources; requires stable geometry reconstruction.'},
        'gameplay_semantics_inference': {'present': False, 'planned': True, 'notes': 'Requires reconstructed objects/geometry and tag taxonomy alignment.'},
        'density_coverage_window_segmentation': {'present': False, 'planned': True, 'notes': 'SectionMetrics features not computed for ONGEKI in Phase 3.'},
        'tips_generation': {'present': False, 'planned': True, 'notes': 'Tips remain disabled until semantic surfaces are available.'},
    })

    # Placeholders for future semantics (keep empty now)
    extra.setdefault('placeholders', {})
    ph = extra['placeholders']
    if isinstance(ph, dict):
        ph.setdefault('lanes', {'planned': True, 'example_shape': 'lane_object[]', 'current': []})
        ph.setdefault('objects', {'planned': True, 'example_shape': 'timeline_object[]', 'current': []})
        ph.setdefault('timeline_events', {'planned': True, 'example_shape': 'timeline_event[]', 'current': []})
        ph.setdefault('area_objects', {'planned': True, 'example_shape': 'area_object[]', 'current': []})

        # SectionMetrics placeholders (do NOT put npb/nps/coverage inside sections when timing_surface_only)
        ph.setdefault('section_metrics', {
            'planned': True,
            'notes': 'npb/nps/coverage/window segmentation will be emitted once gameplay objects are reconstructed.',
            'fields': ['npb', 'nps', 'section_coverage', 'time_beats_start', 'time_beats_end', 'window_id'],
        })

        # Pattern tags -> elements mapping placeholders
        ph.setdefault('pattern_tags', {
            'planned': True,
            'notes': 'Pattern-signal tags extraction requires visual/semantic surfaces; not produced from OGKR timing-only parsing.',
            'current': [],
        })
        ph.setdefault('element_candidates', {
            'planned': True,
            'notes': 'Tag→element candidates require tips_training_mapping alignment; not produced for ONGEKI in Phase 3.',
            'current': [],
        })

    # For convenience, surface an explicit flag that tips are not enabled.
    extra.setdefault('tips_enabled', False)

    # Keep sections timing_surface_only as-is (do not inject density fields here).
    return payload


class OngekiAdapterAugmented(OngekiAdapter):
    """Wrapper adapter that augments canonical payload with safe placeholders."""

    def load(self, file_path: str) -> Dict[str, Any]:
        row = super().load(file_path)
        if isinstance(row, dict) and isinstance(row.get('canonical_payload'), dict):
            row['canonical_payload'] = augment_ongeki_payload(row['canonical_payload'])
        return row


__all__ = ['OngekiAdapterAugmented', 'augment_ongeki_payload']
