#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
adapter_ongeki.py (FULL REPLACEMENT - v2 normalized)

Phase-3-safe ONGEKI adapter for UMI.

Design goals
------------
- additive only
- do not rewrite completed ONGEKI gameplay logic
- provide conservative routing in mixed multi-game chart folders
- remain fallback-safe for partial / legacy sources
- align with BaseAdapterV2 + canonical payload contract
- align with validator_ongeki expectations

Scope
-----
- adapter-only
- no validator imports
- no persistence
- no verification
- no gameplay semantics inference
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    build_standard_diagnostics,
    attach_if_missing,
    file_matches_extensions,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "ongeki"
SECTION_VERSION = canonical_sections_version(GAME_ID, "ongeki-standalone", "v1")

# Conservative extension support:
# - .ogkr / .json are preferred machine-readable candidates
# - .html / .htm / .mht remain fallback-safe through common adapter utils
_PRIMARY_EXTS = [".ogkr", ".json", ".html", ".htm"]

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _ensure_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _looks_like_ongeki_path(path: Path) -> bool:
    """
    Conservative path hints for mixed-folder routing.
    """
    s = str(path).replace("\\", "/").casefold()
    name = path.name.casefold()

    return (
        "/ongeki/" in s
        or "ongeki" in s
        or "ongeki" in name
        or name.endswith(".ogkr")
    )


def _infer_song_id_and_difficulty(path: Path) -> Tuple[Optional[str], str]:
    """
    Best-effort identity inference from path only.
    Non-destructive and fallback-safe.
    """
    stem = path.stem.strip()

    # Best-effort numeric song id prefix
    digits: List[str] = []
    for ch in stem:
        if ch.isdigit():
            digits.append(ch)
        elif digits:
            break

    song_id = "".join(digits) if digits else None

    difficulty = "UNKNOWN"
    diff_names = ["Basic", "Advanced", "Expert", "Master", "Lunatic"]

    lower_stem = stem.casefold()
    for name in diff_names:
        if name.casefold() in lower_stem:
            difficulty = name.upper()
            break

    if difficulty == "UNKNOWN":
        parts_lower = [str(part).casefold() for part in path.parts]
        for name in diff_names:
            if name.casefold() in parts_lower:
                difficulty = name.upper()
                break

    return song_id, difficulty


def _infer_title(path: Path) -> str:
    """
    Best-effort title inference from path.
    """
    stem = path.stem.strip()
    if not stem:
        return path.name

    # Remove obvious difficulty suffix patterns if present
    stem = re.sub(r"\s*\[(BASIC|ADVANCED|EXPERT|MASTER|LUNATIC)\]\s*$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s+\((BASIC|ADVANCED|EXPERT|MASTER|LUNATIC)\)\s*$", "", stem, flags=re.IGNORECASE)
    return stem.strip() or path.stem


def _stable_chart_id(path: Path) -> str:
    """
    Stable chart identifier for asset/payload use.
    """
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def _try_build_payload_from_source(path: Path) -> Dict[str, Any]:
    """
    Best-effort standalone canonical-payload builder.

    Notes:
    - .ogkr / .json: try JSON decode
    - .html / .htm / .mht: route-only fallback
    - keeps content minimal and non-destructive
    """
    suffix = path.suffix.casefold()

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "note_events": [],
        "sections": [],
        "chart_meta": {},
        "diagnostics": {},
        "extra": {},
    }

    # JSON-like / ogkr best effort
    if suffix in {".ogkr", ".json"}:
        try:
            raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(raw, dict):
                payload.update(raw)
        except Exception:
            pass

    # HTML/MHT fallback: no parsing, route-only
    elif suffix in {".html", ".htm", ".mht"}:
        pass

    return payload


def augment_ongeki_payload(canonical_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inject Phase-3-safe placeholders and capability flags.

    Responsibilities:
    - preserve existing payload content
    - ensure diagnostics/internal_metadata/chart_meta blocks exist
    - attach game_id if missing
    - avoid gameplay / tips semantics
    """
    payload = _ensure_dict(canonical_payload)

    diagnostics = _ensure_dict(payload.get("diagnostics"))
    internal_metadata = _ensure_dict(payload.get("internal_metadata"))
    chart_meta = _ensure_dict(payload.get("chart_meta"))
    extra = _ensure_dict(payload.get("extra"))

    payload["diagnostics"] = diagnostics
    payload["internal_metadata"] = internal_metadata
    payload["chart_meta"] = chart_meta
    payload["extra"] = extra

    attach_if_missing(payload, "game_id", GAME_ID)
    attach_if_missing(payload, "note_events", [])
    attach_if_missing(payload, "sections", [])

    return payload


def build_canonical_payload_ongeki(source_ref: str) -> Dict[str, Any]:
    """
    Main module-level builder.

    Guarantees a structurally valid payload even for route-only HTML/MHT sources.
    """
    path = Path(source_ref)

    song_id, difficulty_name = _infer_song_id_and_difficulty(path)
    title = _infer_title(path)

    payload = _try_build_payload_from_source(path)
    payload = augment_ongeki_payload(payload)

    chart_meta = _ensure_dict(payload.get("chart_meta"))
    note_events = payload.get("note_events")
    if not isinstance(note_events, list):
        note_events = []
        payload["note_events"] = note_events

    # Best-effort max_time_beats from note_events
    if "max_time_beats" not in chart_meta:
        max_tb = 0.0
        for ev in note_events:
            if not isinstance(ev, dict):
                continue
            tb = _safe_float(ev.get("time_beats"), default=None)
            if tb is not None:
                max_tb = max(max_tb, tb)
        chart_meta["max_time_beats"] = max_tb

    payload["chart_meta"] = chart_meta

    # --------------------------------------------------
    # Diagnostics enrichment
    # --------------------------------------------------
    diagnostics = _ensure_dict(payload.get("diagnostics"))
    diagnostics.setdefault("game_id", GAME_ID)
    diagnostics.setdefault("adapter_id", "adapter_ongeki")
    diagnostics.setdefault("adapter_version", "2.0.0")
    diagnostics.setdefault("source_path", str(path))
    diagnostics.setdefault("routing_only_html", path.suffix.casefold() in {".html", ".htm", ".mht"})
    diagnostics.setdefault("note_event_count", len(note_events))

    try:
        diag = build_standard_diagnostics(payload.get("sections"))
        if isinstance(diag, dict):
            for k, v in diag.items():
                diagnostics.setdefault(k, v)
    except Exception:
        pass

    payload["diagnostics"] = diagnostics

    # --------------------------------------------------
    # Adapter metadata
    # --------------------------------------------------
    payload.setdefault(
        "adapter_metadata",
        {
            "adapter_id": "adapter_ongeki",
            "adapter_version": "2.0.0",
            "source_format": path.suffix.lower().lstrip("."),
            "source_path": str(path),
            "notes": "ONKEGI standalone adapter with conservative routing and fallback-safe payload generation.",
        },
    )

    # --------------------------------------------------
    # Internal metadata
    # --------------------------------------------------
    internal_meta = _ensure_dict(payload.get("internal_metadata"))
    meta = build_internal_metadata(
        adapter_id="adapter_ongeki",
        adapter_version="2.0.0",
        sections_source="ongeki-standalone" if payload.get("sections") else None,
    )
    for k, v in meta.items():
        internal_meta.setdefault(k, v)

    internal_meta.setdefault("canonical_sections_version", SECTION_VERSION)
    payload["internal_metadata"] = internal_meta

    # --------------------------------------------------
    # Identity fields (canonical payload contract)
    # --------------------------------------------------
    payload.setdefault("game_id", GAME_ID)
    payload.setdefault("chart_id", _stable_chart_id(path))
    payload.setdefault("title", title)
    payload.setdefault("difficulty", difficulty_name)

    # Optional compatibility aliases (safe)
    if song_id is not None:
        payload.setdefault("song_id", song_id)
    payload.setdefault("difficulty_name", difficulty_name)

    return payload


# ---------------------------------------------------------------------
# Adapter implementation
# ---------------------------------------------------------------------

class OngekiAdapter(BaseAdapterV2):
    """
    Standalone rebuilt ONGEKI adapter.

    This adapter preserves the routing-safe wrapper spirit while becoming
    self-contained and v2-normalized.
    """

    game_id = GAME_ID
    adapter_id = "adapter_ongeki"
    adapter_version = "2.0.0"

    def accepts_file(self, path: Any) -> bool:
        p = Path(path)

        # Use shared extension policy, then require explicit ONGEKI hint.
        if file_matches_extensions(p, _PRIMARY_EXTS):
            return _looks_like_ongeki_path(p)

        return False

    def load(self, path: Any) -> Dict[str, Any]:
        """
        Standalone, fallback-safe load.

        Behavior:
        - best-effort payload generation from source
        - non-destructive payload augmentation
        - diagnostics/internal_metadata alignment with common_adapter_utils
        """
        p = Path(path)
        payload = build_canonical_payload_ongeki(str(p))

        return {
            "game_id": self.game_id,
            "source_ref": str(p),
            "song_id": payload.get("song_id"),
            "difficulty_name": payload.get("difficulty"),
            "canonical_payload": payload,
        }

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        """
        Return canonical_payload only.
        """
        payload = build_canonical_payload_ongeki(source_ref)

        # Enforce minimum adapter-validator contract.
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(source_ref),
            default_chart_id=payload.get("chart_id") or _stable_chart_id(Path(source_ref)),
            default_difficulty=payload.get("difficulty") or "UNKNOWN",
        )

        return payload

    def to_canonical_row(self, raw: Any) -> Dict[str, Any]:
        """
        Emit a fallback-safe canonical_row aligned with validator_ongeki expectations.
        """
        if isinstance(raw, dict):
            source_ref = raw.get("source_ref")
            payload = raw.get("canonical_payload") or raw
            song_id = raw.get("song_id")
            difficulty = raw.get("difficulty_name") or payload.get("difficulty") or "UNKNOWN"
        else:
            source_ref = str(raw)
            payload = self.to_canonical_payload(source_ref)
            song_id = payload.get("song_id")
            difficulty = payload.get("difficulty") or "UNKNOWN"

        if not isinstance(payload, dict):
            payload = {}

        note_events = payload.get("note_events")
        if not isinstance(note_events, list):
            note_events = []

        chart_meta = _ensure_dict(payload.get("chart_meta"))

        difficulty = (
            payload.get("difficulty")
            or payload.get("difficulty_name")
            or difficulty
            or "UNKNOWN"
        )

        song_id = (
            payload.get("song_id")
            or payload.get("chart_id")
            or song_id
        )

        title = payload.get("title") or payload.get("name") or _infer_title(Path(source_ref)) if source_ref else None
        bpm = chart_meta.get("bpm")

        duration_ms = chart_meta.get("max_time_ms")
        if duration_ms is None:
            max_time_beats = chart_meta.get("max_time_beats")
            if (
                isinstance(max_time_beats, (int, float))
                and isinstance(bpm, (int, float))
                and float(bpm) > 0
            ):
                try:
                    duration_ms = int(float(max_time_beats) * 60000.0 / float(bpm))
                except Exception:
                    duration_ms = None

        return {
            "game": self.game_id,
            "game_id": self.game_id,
            "song_id": song_id,
            "name": title,
            "title": title,
            "tier": difficulty,
            "level": None,
            "difficulty_code": None,
            "difficulty_label": difficulty,
            "note_total_chart": int(len(note_events)),
            "note_total_db": None,
            "note_delta": None,
            "duration_ms": duration_ms,
            "bpm": bpm,
            "rating_raw": None,
            "chart_path": source_ref,
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_timing_surface_schema": True,
            "emits_canonical_payload": True,
            "source_format": "ogkr/json/html",
            "supports_best_effort_fallback": True,
        }


__all__ = ["OngekiAdapter", "augment_ongeki_payload", "build_canonical_payload_ongeki"]