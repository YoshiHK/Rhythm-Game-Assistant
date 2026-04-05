"""base_adapter_v2.py

Adapter v2 base helpers for UMI Phase 3.

Supported games (source of truth):
- The authoritative list of supported games is defined in **games.json**.
- This module MUST NOT hardcode the supported game list.
- Adapters should set `game_id` to a value present in games.json.
- Any enable/disable decisions belong to games.json + loader/wiring.

Why this file exists (additive, non-breaking):
- base_adapter.py defines the minimal adapter contract (accepts_file/load/to_canonical_row plus optional payload).
- ADAPTER_V2_SPEC formalizes optional canonical payload emission and recommends consistent additive metadata fields.
- common_adapter_utils provides Phase-3-safe helpers to standardize internal_metadata and additive attachment.

Usage model:
- New/migrated adapters may inherit from BaseAdapterV2 for canonical payload finalization.
- Existing adapters can remain on BaseAdapter; using this module is optional.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .base_adapter import BaseAdapter
from .common_adapter_utils import attach_if_missing, build_internal_metadata, build_standard_diagnostics


@dataclass(frozen=True)
class AdapterIdentity:
    """Small identity bundle used for auditability."""

    adapter_id: Optional[str] = None
    adapter_version: Optional[str] = None


class BaseAdapterV2(BaseAdapter):
    """Additive adapter base that standardizes canonical payload blocks."""

    adapter_id: Optional[str] = None
    adapter_version: Optional[str] = None

    def identity(self) -> AdapterIdentity:
        return AdapterIdentity(adapter_id=self.adapter_id, adapter_version=self.adapter_version)

    def finalize_canonical_payload(
        self,
        payload: Dict[str, Any],
        *,
        sections_source: Optional[str] = None,
        notes: Optional[str] = None,
        internal_extra: Optional[Mapping[str, Any]] = None,
        attach_sections_diagnostics: bool = True,
    ) -> Dict[str, Any]:
        """Finalize a canonical payload in an additive, standard way."""

        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        ident = self.identity()
        internal = build_internal_metadata(
            adapter_id=ident.adapter_id,
            adapter_version=ident.adapter_version,
            sections_source=sections_source,
            notes=notes,
            extra=internal_extra,
        )
        attach_if_missing(payload, "internal_metadata", internal)

        if attach_sections_diagnostics and "diagnostics" not in payload:
            sections = payload.get("sections")
            if isinstance(sections, list) and sections:
                diag = build_standard_diagnostics(sections)
                if diag:
                    attach_if_missing(payload, "diagnostics", diag)

        return payload


__all__ = ["AdapterIdentity", "BaseAdapterV2"]
