"""rhythm_ingestion.adapters.common_adapter_utils

Shared adapter utilities for UMI Phase 3.

Scope (foundation-layer helper):
- Pure, lightweight helpers used by multiple game adapters.
- MUST NOT modify any Phase 1/2 logic.
- No IO, no registry lookups, no dependency on concrete adapters.

These helpers standardize a few optional fields that appear across canonical
payloads/rows:
- diagnostics: small numeric aggregates that are safe to compute generically
- internal_metadata: ingestion/QA tracing information
- canonical_sections_version: consistent version strings for sections producers

All functions are additive: callers decide whether/where to attach returned dicts.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def build_internal_metadata(
    *,
    adapter_id: Optional[str] = None,
    adapter_version: Optional[str] = None,
    sections_source: Optional[str] = None,
    notes: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a small internal_metadata block for canonical_payload.

    This is intended for ingestion/QA tracing only.
    """
    out: Dict[str, Any] = {}
    if adapter_id:
        out["adapter_id"] = adapter_id
    if adapter_version:
        out["adapter_version"] = adapter_version
    if sections_source:
        out["sections_source"] = sections_source
    if notes:
        out["notes"] = notes
    if extra:
        for k, v in dict(extra).items():
            # keep only JSON-serializable-ish primitives and dict/list
            out[k] = v
    return out


def canonical_sections_version(game_id: str, producer: str, version: str = "v1") -> str:
    """Return a normalized canonical_sections_version string.

    Example: canonical_sections_version('proseka','sectionmetrics','v1')
      -> 'proseka_sectionmetrics_v1'
    """
    gid = (game_id or "").strip().lower()
    prod = (producer or "").strip().lower().replace(" ", "_")
    ver = (version or "v1").strip().lower().lstrip("v")
    return f"{gid}_{prod}_v{ver}" if gid and prod else f"{gid}_sections_v{ver}"


def build_standard_diagnostics(
    sections: Optional[Iterable[Mapping[str, Any]]],
    *,
    nps_key: str = "nps",
    npb_key: str = "npb",
    hold_cov_key: str = "hold_coverage",
) -> Dict[str, Any]:
    """Compute lightweight diagnostics from sections.

    This intentionally mirrors the common QA metrics you already use:
    - sections_count
    - avg_nps
    - avg_npb
    - total_hold_coverage (mean of hold_coverage)

    Keys are customizable to support different section dict schemas.
    """
    secs = list(sections or [])
    if not secs:
        return {}

    n = len(secs)
    avg_nps = sum(_safe_float(s.get(nps_key), 0.0) for s in secs) / max(1, n)
    avg_npb = sum(_safe_float(s.get(npb_key), 0.0) for s in secs) / max(1, n)
    avg_hold = sum(_safe_float(s.get(hold_cov_key), 0.0) for s in secs) / max(1, n)

    return {
        "sections_count": n,
        "avg_nps": avg_nps,
        "avg_npb": avg_npb,
        "total_hold_coverage": avg_hold,
    }


def attach_if_missing(target: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """Attach a key/value into target only if key is absent.

    This is a tiny helper used to keep adapter output additive.
    """
    if key not in target:
        target[key] = value
    return target


__all__ = [
    "build_internal_metadata",
    "canonical_sections_version",
    "build_standard_diagnostics",
    "attach_if_missing",
]
