from __future__ import annotations

"""
rhythm_ingestion.adapters.common_adapter_utils
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
- fallback file extension helpers for adapter acceptance logic

All functions are additive: callers decide whether/where to attach returned dicts.
"""

from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Set


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
    """Build a small internal_metadata block for canonical_payload."""
    out: Dict[str, Any] = {}
    if adapter_id is not None:
        out["adapter_id"] = adapter_id
    if adapter_version is not None:
        out["adapter_version"] = adapter_version
    if sections_source is not None:
        out["sections_source"] = sections_source
    if notes is not None:
        out["notes"] = notes
    if extra:
        out.update(dict(extra))
    return out


def canonical_sections_version(game_id: str, producer: str, version: str = "v1") -> str:
    """Return a normalized canonical_sections_version string."""
    gid = str(game_id or "unknown").strip()
    prod = str(producer or "unknown").strip()
    ver = str(version or "v1").strip()
    return f"{gid}:{prod}:{ver}"


def build_standard_diagnostics(
    sections: Optional[Iterable[Mapping[str, Any]]],
    *,
    nps_key: str = "nps",
    npb_key: str = "npb",
    hold_cov_key: str = "hold_coverage",
) -> Dict[str, Any]:
    """Compute lightweight diagnostics from sections."""
    rows = list(sections or [])
    if not rows:
        return {
            "section_count": 0,
            "avg_nps": 0.0,
            "avg_npb": 0.0,
            "avg_hold_coverage": 0.0,
        }

    nps_vals = [_safe_float(r.get(nps_key, 0.0)) for r in rows]
    npb_vals = [_safe_float(r.get(npb_key, 0.0)) for r in rows]
    hold_vals = [_safe_float(r.get(hold_cov_key, 0.0)) for r in rows]

    return {
        "section_count": len(rows),
        "avg_nps": (sum(nps_vals) / len(nps_vals)) if nps_vals else 0.0,
        "avg_npb": (sum(npb_vals) / len(npb_vals)) if npb_vals else 0.0,
        "avg_hold_coverage": (sum(hold_vals) / len(hold_vals)) if hold_vals else 0.0,
    }


def attach_if_missing(target: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """Attach a key/value into target only if key is absent."""
    if key not in target:
        target[key] = value
    return target


# ---------------------------------------------------------------------
# Baseline fallback file-extension helpers
# ---------------------------------------------------------------------

BASELINE_FALLBACK_EXTENSIONS: Set[str] = {".html", ".mht"}


def normalize_extensions(extensions: Optional[Sequence[str]]) -> Set[str]:
    """Normalize an iterable of extensions to lower-case dotted strings."""
    out: Set[str] = set()
    for ext in extensions or []:
        if ext is None:
            continue
        e = str(ext).strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return out


def with_baseline_fallback_extensions(
    extensions: Optional[Sequence[str]] = None,
    *,
    include_baseline: bool = True,
) -> Set[str]:
    """
    Return normalized extensions with baseline fallback extensions added.

    Recommended use in adapters:
        allowed = with_baseline_fallback_extensions([".json", ".txt"])
    """
    out = normalize_extensions(extensions)
    if include_baseline:
        out.update(BASELINE_FALLBACK_EXTENSIONS)
    return out


def file_matches_extensions(path: Any, extensions: Optional[Sequence[str]] = None) -> bool:
    """
    Return True if the file suffix matches the normalized extension set.
    """
    suffix = str(getattr(path, "suffix", "") or "").lower()
    allowed = with_baseline_fallback_extensions(extensions)
    return suffix in allowed


__all__ = [
    "build_internal_metadata",
    "canonical_sections_version",
    "build_standard_diagnostics",
    "attach_if_missing",
    "BASELINE_FALLBACK_EXTENSIONS",
    "normalize_extensions",
    "with_baseline_fallback_extensions",
    "file_matches_extensions",
]