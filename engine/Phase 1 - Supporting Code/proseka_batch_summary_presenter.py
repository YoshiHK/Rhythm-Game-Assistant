"""proseka_batch_summary_presenter.py

Batch summary presenter for Project SEKAI chart analysis.

Goal
- Turn a BatchLevelSummary (or dict) into concise, well-phrased outlines.
- Provide both plain-text and Markdown rendering.

Inputs
- BatchLevelSummary as defined in proseka_batch_summary_dataclasses.py
  (or a dict with identical keys).

Outputs
- A string suitable for logs, dashboards, or Softr blocks.

This module intentionally avoids business logic (no recomputation of stats).
It only formats and narrates the provided batch summary.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Tuple


SEVERITY_ORDER = ["slight", "light", "mild", "moderate", "dense", "complex", "demanding"]


def _safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default)


def _fmt_pct(x: Optional[float], digits: int = 1) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.{digits}f}%"


def _fmt_score(x: Optional[float], digits: int = 2) -> str:
    if x is None:
        return "—"
    return f"{x:.{digits}f}"


def _sorted_top_elements(freq: Dict[str, int], k: int = 5) -> List[Tuple[str, int]]:
    return sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def _severity_line(dist: Dict[str, int]) -> str:
    total = sum(dist.values()) if dist else 0
    if total == 0:
        return "No severity data." 
    parts: List[str] = []
    for s in SEVERITY_ORDER:
        c = dist.get(s, 0)
        if c:
            parts.append(f"{s}: {c} ({(c/total)*100:.0f}%)")
    return "; ".join(parts) if parts else "No severity data."


def _pick_narrative_focus(freq: Dict[str, int], difficulty: str) -> str:
    """Choose a short focus phrase based on top elements (heuristic)."""
    top = _sorted_top_elements(freq, k=3)
    names = [n for n, _ in top]
    if not names:
        return "no dominant mechanical pattern"

    # Light-touch heuristics; avoids speculative claims.
    if "stream" in names:
        return "sustained density and timing stability"
    if "stacked_chord" in names:
        return "simultaneous input control"
    if "trill" in names:
        return "alternation speed and timing precision"
    if "cross_hand" in names:
        return "hand assignment and movement control"
    if difficulty == "append":
        return "layered mechanics and planning"
    return "a mix of recurring chart mechanics"


def present_batch_summary(
    batch_summary: Any,
    *,
    style: str = "markdown",
    top_k: int = 5,
    include_diagnostics: bool = True
) -> str:
    """Render a batch summary as a compact outline.

    style: 'markdown' | 'text'
    """

    data: Dict[str, Any]
    if is_dataclass(batch_summary):
        data = asdict(batch_summary)
    elif isinstance(batch_summary, dict):
        data = batch_summary
    else:
        raise TypeError("batch_summary must be a dataclass instance or dict")

    batch_id = _safe_get(data, "batch_id")
    difficulty = _safe_get(data, "difficulty", "—")
    chart_count = _safe_get(data, "chart_count", 0)

    freq = _safe_get(data, "element_frequency", {}) or {}
    sev_dist = _safe_get(data, "severity_distribution", {}) or {}

    avg_score = _safe_get(data, "avg_score")
    avg_cov = _safe_get(data, "avg_section_coverage")

    dom_total = _safe_get(data, "dominant_total", 0)
    dom_sel = _safe_get(data, "dominant_selected_count", 0)
    dom_ratio = _safe_get(data, "dominant_selection_ratio", 0.0)

    full_cov = _safe_get(data, "charts_with_full_dominant_coverage", 0)
    zero_cov = _safe_get(data, "charts_with_zero_dominant_coverage", 0)

    score_dist = _safe_get(data, "score_distribution")
    tips_comp = _safe_get(data, "tips_compliance")
    notes = _safe_get(data, "notes")

    focus = _pick_narrative_focus(freq, difficulty)

    top_list = _sorted_top_elements(freq, k=top_k)
    total_elements = sum(freq.values()) if freq else 0

    def fmt_top_items() -> str:
        if not top_list or total_elements == 0:
            return "—"
        parts = []
        for name, count in top_list:
            share = count / total_elements
            parts.append(f"{name} {count} ({share*100:.0f}%)")
        return ", ".join(parts)

    # Compose sections
    header = f"Batch Summary" + (f" — {batch_id}" if batch_id else "")
    lead = (
        f"{chart_count} charts in {difficulty.upper()} with {total_elements} detected element instances. "
        f"Overall focus: {focus}."
    )

    stats = (
        f"Avg score { _fmt_score(avg_score) }, avg coverage { _fmt_pct(avg_cov) }. "
        f"Dominant selection {dom_sel}/{dom_total} ({_fmt_pct(dom_ratio,1)}). "
        f"Full dominant coverage {full_cov} charts; zero coverage {zero_cov} charts."
    )

    severity_line = _severity_line(sev_dist)

    top_line = f"Top elements: {fmt_top_items()}."

    extra_lines: List[str] = []

    if include_diagnostics and isinstance(tips_comp, dict):
        gen = tips_comp.get("tips_generated_count")
        valid = tips_comp.get("tips_valid_count")
        ratio = tips_comp.get("tips_valid_ratio")
        avg_wc = tips_comp.get("avg_word_count")
        max_wc = tips_comp.get("max_word_count")
        over = tips_comp.get("over_limit_count")
        diag = f"Tips compliance: valid {valid}/{gen} ({_fmt_pct(ratio,1)})."
        if avg_wc is not None:
            diag += f" Avg words {avg_wc:.1f}."
        if max_wc is not None:
            diag += f" Max words {max_wc}."
        if over is not None:
            diag += f" Over-limit {over}."
        extra_lines.append(diag)

    if include_diagnostics and isinstance(score_dist, dict):
        sd = score_dist
        extra_lines.append(
            "Score distribution: "
            f"min {_fmt_score(sd.get('min'))}, p25 {_fmt_score(sd.get('p25'))}, p50 {_fmt_score(sd.get('p50'))}, "
            f"p75 {_fmt_score(sd.get('p75'))}, p90 {_fmt_score(sd.get('p90'))}, max {_fmt_score(sd.get('max'))}."
        )

    if notes:
        extra_lines.append(f"Notes: {notes}")

    if style == "markdown":
        out = [f"## {header}", lead, "", f"**Key stats:** {stats}", "", f"**Severity mix:** {severity_line}", "", top_line]
        if extra_lines:
            out.append("")
            out.append("**Diagnostics:**")
            for line in extra_lines:
                out.append(f"- {line}")
        return "
".join(out)

    # Plain text
    out = [header, lead, stats, f"Severity mix: {severity_line}", top_line]
    out.extend(extra_lines)
    return "
".join(out)


__all__ = ["present_batch_summary"]
