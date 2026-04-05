"""rhythm_ingestion.adapters package

v2 compatibility exports (additive, non-breaking).

Supported games (source of truth):
- The authoritative list of supported games is defined in **games.json**.
- Code in this package MUST NOT hardcode the supported game list.
- Adapters should set `game_id` to a value that matches an entry in games.json.
- Routing / registry / CLI help text should consult games.json (via the games loader) rather than
  inspecting this package.

Goals:
- Provide a single, stable import surface for adapters.
- Preserve legacy BaseAdapter contract.
- Add v2 standardization helpers (BaseAdapterV2) without forcing migration.
- Re-export common_adapter_utils helpers to reduce per-adapter boilerplate.

Notes:
- Per ADAPTER_V2_SPEC, adapters must not be version-suffixed; versioning travels via adapter_id/adapter_version.
- This __init__ does not import concrete game adapters by default to avoid import-time side effects.
"""

from __future__ import annotations

from .base_adapter import BaseAdapter

try:
    from .base_adapter_v2 import BaseAdapterV2, AdapterIdentity
except Exception:  # pragma: no cover
    BaseAdapterV2 = None  # type: ignore
    AdapterIdentity = None  # type: ignore

from .common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    build_standard_diagnostics,
    attach_if_missing,
)

__all__ = [
    "BaseAdapter",
    "BaseAdapterV2",
    "AdapterIdentity",
    "build_internal_metadata",
    "canonical_sections_version",
    "build_standard_diagnostics",
    "attach_if_missing",
]
