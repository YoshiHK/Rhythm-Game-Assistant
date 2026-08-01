"""base_adapter.py

Base adapter interface for the Unified Ingestion Manager (UMI).

Supported games (source of truth):
- The authoritative list of supported games is defined in **games.json**.
- This module MUST NOT hardcode the supported game list.
- Each concrete adapter MUST set `game_id` to a value that matches a games.json entry.
- Any enable/disable decisions belong to games.json + loader/wiring, not to adapters.

Each game-specific adapter MUST:
- detect valid files via accepts_file(path)
- parse raw chart data via load(path)
- convert to canonical song-row dict via to_canonical_row(raw)

Optional (additive) capabilities:
- emit canonical chart payload via to_canonical_payload(path)
- expose adapter capabilities via capabilities()

Notes:
- This file intentionally avoids filename/class version suffixes.
- Versioning is carried via adapter_id / adapter_version metadata fields.
"""

from __future__ import annotations

from typing import Optional, Any, Dict


class BaseAdapter:
    # Logical game identifier (e.g., "proseka", "arcaea", "bandori")
    game_id: Optional[str] = None

    # Optional adapter identity for auditability (recommended for canonical payloads)
    adapter_id: Optional[str] = None
    adapter_version: Optional[str] = None

    # ----------------------------
    # REQUIRED: routing + persistence
    # ----------------------------
    def accepts_file(self, path) -> bool:
        """Return True if this adapter should handle the given file path."""
        raise NotImplementedError

    def load(self, path):
        """Load raw game-specific data from a file path into an intermediate representation."""
        raise NotImplementedError

    def to_canonical_row(self, raw) -> Dict[str, Any]:
        """Convert a raw object into a CanonicalSongRow dict for persistence."""
        raise NotImplementedError

    # ----------------------------
    # OPTIONAL: canonical payload + capabilities (additive)
    # ----------------------------
    def to_canonical_payload(self, path: str) -> Dict[str, Any]:
        """OPTIONAL: emit canonical chart payload aligned to canonical schema."""
        raise NotImplementedError

    def capabilities(self) -> Dict[str, Any]:
        """OPTIONAL: informational capability descriptor."""
        return {}
