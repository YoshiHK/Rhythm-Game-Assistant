
#!/usr/bin/env python3
"""adapter_payload_utils.py

Additive helpers for building canonical chart payload blocks.

Why this exists:
- <File>common_adapter_utils.py</File> is Phase-3 foundation and is kept stable.
- We avoid filename version suffixes (no *_v2.py naming).
- These helpers extend functionality without changing completed-phase files.

Scope:
- Pure helpers only (no IO, no registry lookups).
- Standardize adapter_metadata attachment for canonical_chart_payload.

"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .common_adapter_utils import (
    build_internal_metadata,
    build_standard_diagnostics,
    canonical_sections_version,
    attach_if_missing,
)


def build_adapter_metadata(
    *,
    adapter_id: Optional[str] = None,
    adapter_version: Optional[str] = None,
    source_format: Optional[str] = None,
    source_path: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Build adapter_metadata for canonical_chart_payload.schema.json."""
    out: Dict[str, Any] = {}
    if adapter_id:
        out["adapter_id"] = adapter_id
    if adapter_version:
        out["adapter_version"] = adapter_version
    if source_format:
        out["source_format"] = source_format
    if source_path:
        out["source_path"] = source_path
    if notes:
        out["notes"] = notes
    return out


def attach_adapter_metadata(payload: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Attach adapter_metadata if missing (additive)."""
    return attach_if_missing(payload, "adapter_metadata", meta)


def attach_internal_metadata(payload: Dict[str, Any], *, extra: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    """Attach internal_metadata if missing (additive)."""
    meta = build_internal_metadata(extra=extra, **kwargs)
    return attach_if_missing(payload, "internal_metadata", meta)


def attach_diagnostics_from_sections(
    payload: Dict[str, Any],
    *,
    sections_key: str = "sections",
    diagnostics_key: str = "diagnostics",
) -> Dict[str, Any]:
    """Compute and attach lightweight diagnostics from sections if present."""
    sections = payload.get(sections_key)
    diag = build_standard_diagnostics(sections) if sections is not None else {}
    if diag:
        base = payload.get(diagnostics_key)
        if not isinstance(base, dict):
            base = {}
        base = dict(base)
        base.update(diag)
        payload[diagnostics_key] = base
    return payload


__all__ = [
    "build_adapter_metadata",
    "attach_adapter_metadata",
    "attach_internal_metadata",
    "attach_diagnostics_from_sections",
    "build_internal_metadata",
    "build_standard_diagnostics",
    "canonical_sections_version",
]
