from __future__ import annotations
"""severity_engine.py

Phase 3 wiring layer for Stage 5.1 (Track A): Severity + score + coverage.

Responsibilities:
- Consume SectionMetrics ("sections") produced upstream (Stage 2–4.1).
- Run a Track A driver to produce elements_skeleton:
    element_id, element_name (JP), category, severity, score, section_coverage.
- Optionally enrich elements_skeleton with Stage 4.2/4.3 candidate metadata:
    matched_tags, training_items, tag_hit_count (additive, non-breaking).
- Optionally add dominant_score = score * section_coverage (Stage 7 convention).

Multi-game support (wiring-only):
- Driver registry keyed by normalized game_id.
- Default driver is Proseka-compatible wrapper (best-effort).
- Additional drivers can be registered via register_track_a_driver().

Degraded mode:
- Adds a boolean `degraded_mode` flag + `degraded_reasons` list when:
  - The requested game_id has no registered Track A driver and we fall back to proseka.
  - The Track A driver reports it is unavailable.

Track C/D degraded flags (NEW):
- When degraded_mode is True, this module ALSO writes additive flags under diagnostics:
    diagnostics['track_c']['degraded_mode'] / ['degraded_reasons']
    diagnostics['track_d']['degraded_mode'] / ['degraded_reasons']
  so Track C (guidance_engine_v2) and Track D (narrative_module_v2) wiring can gate
  "promising tips" behaviors without changing completed Phase 2 logic.

Constraints:
- MUST NOT modify completed Phase 1/2 logic.
- MUST NOT require adapters/validators.
- No import-time heavy IO.

"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Union


DEFAULT_CALIBRATION_CONFIG_PATH = "score_calibration_config_v0.2.1.json"
PER_GAME_CALIBRATION_TEMPLATE = "score_calibration_config_{game_id}.json"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _normalize_game_id(game_id: Any) -> str:
    if game_id is None:
        return ""
    try:
        return str(game_id).strip().lower()
    except Exception:
        return ""


def _compute_dominant_score(el: Dict[str, Any]) -> float:
    score = _safe_float(el.get("score"), 0.0)
    cov = _safe_float(el.get("section_coverage"), 0.0)
    return score * cov


def _index_candidates_by_name(element_candidates: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for c in element_candidates or []:
        if not isinstance(c, dict):
            continue
        name = c.get("element_name")
        if not isinstance(name, str) or not name:
            continue
        if name not in out:
            out[name] = c
    return out


def merge_candidate_metadata(
    elements_skeleton: List[Dict[str, Any]],
    element_candidates: Sequence[Dict[str, Any]],
    *,
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    """Additively merge Stage 4.2/4.3 metadata into elements_skeleton."""

    idx = _index_candidates_by_name(element_candidates)
    for el in elements_skeleton or []:
        if not isinstance(el, dict):
            continue
        name = el.get("element_name")
        if not isinstance(name, str) or not name:
            continue
        cand = idx.get(name)
        if not isinstance(cand, dict):
            continue
        for key in ("matched_tags", "training_items", "tag_hit_count"):
            if key in cand and (overwrite or key not in el):
                el[key] = cand.get(key)
    return elements_skeleton


def resolve_calibration_config_path(
    *,
    game_id: Optional[str] = None,
    calibration_config_path: Optional[str] = None,
    calibration_search_paths: Optional[Sequence[Union[str, Path]]] = None,
    default_path: str = DEFAULT_CALIBRATION_CONFIG_PATH,
    template: str = PER_GAME_CALIBRATION_TEMPLATE,
) -> str:
    """Best-effort resolver for per-game calibration config paths."""

    def _norm_paths(paths: Optional[Sequence[Union[str, Path]]]) -> List[Path]:
        if not paths:
            return [Path(".")]
        out: List[Path] = []
        seen: Set[str] = set()
        for p in paths:
            if p is None:
                continue
            cand = p if isinstance(p, Path) else Path(str(p).strip())
            key = str(cand)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(cand)
        return out or [Path(".")]

    if calibration_config_path:
        p = Path(calibration_config_path)
        if p.exists():
            return str(p)

    search_paths = _norm_paths(calibration_search_paths)

    if calibration_config_path:
        name = str(calibration_config_path).strip()
        if name:
            for base in search_paths:
                cand = base / name
                if cand.exists():
                    return str(cand)

    gid = _normalize_game_id(game_id)
    if gid:
        fname = template.format(game_id=gid)
        for base in search_paths:
            cand = base / fname
            if cand.exists():
                return str(cand)

    for base in search_paths:
        cand = base / default_path
        if cand.exists():
            return str(cand)

    return default_path


TrackADriver = Callable[..., Dict[str, Any]]


def run_track_a_proseka(
    sections: Sequence[Any],
    *,
    calibration_config_path: str = DEFAULT_CALIBRATION_CONFIG_PATH,
    preserve_severity: bool = True,
    coverage_threshold: Optional[str] = None,
) -> Dict[str, Any]:
    """Best-effort Proseka Track A wrapper.

    Uses severity_detector.infer_severities_for_chart() if available.
    Optionally applies proseka_score_calibration.apply_calibration() if present.
    """

    # Import severity_detector (local-first)
    try:
        from . import severity_detector as _sd  # type: ignore
    except Exception:
        try:
            import severity_detector as _sd  # type: ignore
        except Exception:
            _sd = None  # type: ignore

    # Import calibration (optional)
    try:
        from . import proseka_score_calibration as _cal  # type: ignore
    except Exception:
        try:
            import proseka_score_calibration as _cal  # type: ignore
        except Exception:
            _cal = None  # type: ignore

    if _sd is not None and hasattr(_sd, "infer_severities_for_chart"):
        try:
            cov = coverage_threshold or "moderate"
            report = _sd.infer_severities_for_chart(list(sections or []), coverage_threshold=cov)  # type: ignore
            if isinstance(report, dict):
                if _cal is not None and hasattr(_cal, "apply_calibration") and isinstance(report.get("elements_skeleton"), list):
                    try:
                        report["elements_skeleton"] = _cal.apply_calibration(  # type: ignore
                            report["elements_skeleton"],
                            config_path=calibration_config_path,
                            preserve_severity=preserve_severity,
                        )
                    except Exception:
                        pass
                return report
        except Exception:
            pass

    return {
        "elements_skeleton": [],
        "diagnostics": {
            "track_a": "unavailable",
            "calibration_config_path": calibration_config_path,
        },
    }


_TRACK_A_DRIVERS: Dict[str, TrackADriver] = {
    "proseka": run_track_a_proseka,
}


def register_track_a_driver(game_id: str, driver: TrackADriver) -> None:
    gid = _normalize_game_id(game_id)
    if gid:
        _TRACK_A_DRIVERS[gid] = driver


def _attach_degraded_flags_for_track_cd(
    canonical_payload: Dict[str, Any],
    *,
    degraded_mode: bool,
    degraded_reasons: Sequence[str],
) -> None:
    """Additively attach degraded flags for Track C/D wiring."""

    diag = canonical_payload.setdefault("diagnostics", {})
    if not isinstance(diag, dict):
        return

    for k in ("track_c", "track_d"):
        block = diag.setdefault(k, {})
        if isinstance(block, dict):
            block.setdefault("degraded_mode", bool(degraded_mode))
            if degraded_reasons:
                block.setdefault("degraded_reasons", list(degraded_reasons))


def build_elements_skeleton(
    game_id: str,
    canonical_payload: Dict[str, Any],
    *,
    element_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    detected_tags: Optional[Sequence[str]] = None,
    calibration_config_path: Optional[str] = None,
    calibration_search_paths: Optional[Sequence[Union[str, Path]]] = None,
    preserve_severity: bool = True,
    coverage_threshold: Optional[str] = None,
    attach_to_payload: bool = True,
    add_dominant_score: bool = True,
    overwrite_candidate_metadata: bool = False,
    output_key: str = "elements_skeleton",
) -> Dict[str, Any]:
    """Unified Stage 5.1 entrypoint."""

    gid = _normalize_game_id(game_id)

    # Inputs
    sections = canonical_payload.get("sections")
    if not isinstance(sections, list):
        sections = []

    if element_candidates is None:
        ec = canonical_payload.get("element_candidates")
        element_candidates = ec if isinstance(ec, list) else []

    if detected_tags is None:
        dt = canonical_payload.get("detected_tags")
        detected_tags = dt if isinstance(dt, list) else None

    resolved_cal = resolve_calibration_config_path(
        game_id=gid,
        calibration_config_path=calibration_config_path,
        calibration_search_paths=calibration_search_paths,
    )

    # Driver selection
    driver = _TRACK_A_DRIVERS.get(gid) or _TRACK_A_DRIVERS.get("proseka")
    driver_name = getattr(driver, "__name__", "<driver>")

    # Degraded-mode detection
    degraded_mode = False
    degraded_reasons: List[str] = []
    if gid and gid not in _TRACK_A_DRIVERS and driver is _TRACK_A_DRIVERS.get("proseka"):
        degraded_mode = True
        degraded_reasons.append("fallback_driver:proseka")

    report = driver(
        sections,
        calibration_config_path=resolved_cal,
        preserve_severity=preserve_severity,
        coverage_threshold=coverage_threshold,
    )

    if not isinstance(report, dict):
        report = {"elements_skeleton": []}

    elements_skeleton = report.get("elements_skeleton")
    if not isinstance(elements_skeleton, list):
        elements_skeleton = []

    # If Track A unavailable, mark degraded
    diag_r = report.get("diagnostics") if isinstance(report, dict) else None
    if isinstance(diag_r, dict) and diag_r.get("track_a") == "unavailable":
        degraded_mode = True
        degraded_reasons.append("track_a_unavailable")

    # Enrich with candidate metadata
    try:
        elements_skeleton = merge_candidate_metadata(
            elements_skeleton,
            element_candidates or [],
            overwrite=overwrite_candidate_metadata,
        )
    except Exception:
        pass

    # Add dominant_score
    if add_dominant_score:
        for el in elements_skeleton:
            if isinstance(el, dict) and "dominant_score" not in el:
                el["dominant_score"] = _compute_dominant_score(el)

    # Attach to payload
    if attach_to_payload:
        canonical_payload[output_key] = elements_skeleton

    # Add diagnostics provenance (additive)
    diag = canonical_payload.setdefault("diagnostics", {})
    if isinstance(diag, dict):
        se = diag.setdefault("severity_engine", {})
        if isinstance(se, dict):
            se.setdefault("game_id", gid)
            se.setdefault("driver", driver_name)
            se.setdefault("calibration_config_path", resolved_cal)
            se.setdefault("degraded_mode", bool(degraded_mode))
            if degraded_reasons:
                se.setdefault("degraded_reasons", list(degraded_reasons))

    # NEW: propagate degraded flags to Track C/D wiring
    _attach_degraded_flags_for_track_cd(
        canonical_payload,
        degraded_mode=bool(degraded_mode),
        degraded_reasons=degraded_reasons,
    )

    out: Dict[str, Any] = dict(report)
    out["elements_skeleton"] = elements_skeleton
    out["degraded_mode"] = bool(degraded_mode)
    if degraded_reasons:
        out["degraded_reasons"] = list(degraded_reasons)
    return out


__all__ = [
    "run_track_a_proseka",
    "register_track_a_driver",
    "merge_candidate_metadata",
    "resolve_calibration_config_path",
    "build_elements_skeleton",
]
