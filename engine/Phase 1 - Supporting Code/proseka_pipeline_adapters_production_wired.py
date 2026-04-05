"""proseka_pipeline_adapters_production_wired.py

Production-aligned adapter implementations for the Project SEKAI tips pipeline,
now wired to the Step 5.1 severity + coverage builder.

Wiring changes
- ProductionElementAnalyser now consumes SectionMetrics sections (if provided in
  chart.payload['sections']) and calls severity_detector.infer_severities_for_chart()
  to obtain per-element severity, score, and section_coverage.

This mirrors your production helper flow:
- helper_functions.load_tips_training_mapping + infer_elements_from_tags
- (5.1) severity_detector.infer_severities_for_chart
- downstream selection + narrative via batch pipeline spec

Expected payload shapes
- Tag-only payload: { 'detected_tags': [...] }
- Visual detector payload (recommended):
  { 'detected_tags': [...], 'sections': [SectionMetrics, ...], 'diagnostics': {...} }

Note
- This module does not implement chart parsing; use chart_visual_detector_merged.py
  upstream to generate detected_tags + sections.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Literal
import json

# Track B selector (v2)
from selector_v2 import select_elements_v2

# Production helper functions
from helper_functions import load_tips_training_mapping, infer_elements_from_tags

# Step 5.1 severity+coverage builder (the missing piece)
from severity_detector import infer_severities_for_chart

Difficulty = Literal["expert", "master", "append"]
Severity = Literal["slight","light","mild","moderate","dense","complex","demanding"]

SEVERITY_ORDER: List[Severity] = ["slight","light","mild","moderate","dense","complex","demanding"]
SEV_INDEX: Dict[Severity, int] = {s: i for i, s in enumerate(SEVERITY_ORDER)}

USE_CALIBRATION = True
# Prefer v0.2.0 when available; fall back to v0.1.0.
CALIBRATION_CONFIG = "score_calibration_config_v0.2.0.json"

try:
    from proseka_score_calibration import infer_severities_for_chart_calibrated as _infer_calibrated
except Exception:  # pragma: no cover
    _infer_calibrated = None


def _infer_severity_result(sections):
    # Track A integration point: returns severity_detector-compatible dict.
    if USE_CALIBRATION and _infer_calibrated is not None:
        return _infer_calibrated(
            sections,
            calibration_config_path=CALIBRATION_CONFIG,
            preserve_severity=True,
        )
    return infer_severities_for_chart(sections)


# ---- Data classes (structural compatibility with proseka_tips_pipeline_runner) ---- (structural compatibility with proseka_tips_pipeline_runner) ----

@dataclass
class ChartInput:
    chart_id: Optional[str] = None
    song_id: Optional[str] = None
    master_level: Optional[int] = None
    payload: Any = None


@dataclass
class TagSignal:
    tag: str
    confidence: float = 1.0
    meta: Dict[str, Any] = None


@dataclass
class ElementCandidate:
    # Official element label (JP) from tips_training_mapping
    name: str
    evidence_tags: List[str]
    meta: Dict[str, Any]


@dataclass
class ElementGuidance:
    difficulty_causes: str
    chart_breakdown: str
    primary_focus: str
    secondary_focus: str
    strategy: str
    target_section: str


@dataclass
class AnalysedElement:
    name: str
    severity: Severity
    score: float
    section_coverage: float
    is_chart_defining: bool
    guidance: ElementGuidance


@dataclass
class TipsOutput:
    paragraph_1: str
    paragraph_2: str

    @property
    def full_text(self) -> str:
        return f"{self.paragraph_1}

{self.paragraph_2}".strip()


# -----------------------------
# Adapter 1: ChartScanner
# -----------------------------

class ProductionChartScanner:
    """Production-aligned chart scanner.

    Mirrors the production batch wrapper expectation used by api_wrapper:
    each chart dict contains 'detected_tags': list[str].

    Supported payload shapes:
    - payload is dict with key 'detected_tags' -> list[str]
    - payload is list[str]
    - payload is list[dict] with key 'tag'

    Returns TagSignal objects.
    """

    def scan(self, chart: ChartInput) -> List[TagSignal]:
        raw = chart.payload
        detected: List[str] = []

        if raw is None:
            return []

        if isinstance(raw, dict):
            dt = raw.get("detected_tags")
            if isinstance(dt, list):
                detected = [str(x).strip() for x in dt if str(x).strip()]
        elif isinstance(raw, list):
            if all(isinstance(x, str) for x in raw):
                detected = [x.strip() for x in raw if x.strip()]
            else:
                for item in raw:
                    if isinstance(item, dict) and "tag" in item:
                        t = str(item["tag"]).strip()
                        if t:
                            detected.append(t)

        return [TagSignal(tag=t, confidence=1.0, meta={}) for t in detected]


# -----------------------------
# Adapter 2: TagToElementMapper
# -----------------------------

class ProductionTagToElementMapper:
    """Production-aligned tag -> element mapper.

    EXACTLY uses:
    - load_tips_training_mapping(path)
    - infer_elements_from_tags(detected_tags, mapping, min_tag_hits)

    Output ElementCandidate:
    - name = element_name (official element label, JP)
    - evidence_tags = matched_tags
    - meta.training_items = training_items
    """

    def __init__(self, mapping_path: str = "tips_training_mapping.json", min_tag_hits: int = 1):
        self.mapping_path = mapping_path
        self.min_tag_hits = min_tag_hits
        self._mapping_cache: Optional[Dict[str, Any]] = None

    def _mapping(self) -> Dict[str, Any]:
        if self._mapping_cache is None:
            self._mapping_cache = load_tips_training_mapping(self.mapping_path)
        return self._mapping_cache

    def map_tags(self, tags: List[TagSignal], difficulty: Difficulty) -> List[ElementCandidate]:
        detected_tags = [t.tag for t in tags]
        elements = infer_elements_from_tags(detected_tags, self._mapping(), min_tag_hits=self.min_tag_hits)

        candidates: List[ElementCandidate] = []
        for el in elements:
            candidates.append(
                ElementCandidate(
                    name=el["element_name"],
                    evidence_tags=list(el.get("matched_tags", [])),
                    meta={
                        "training_items": list(el.get("training_items", [])),
                        "detected_tags": detected_tags
                    }
                )
            )
        return candidates


# -----------------------------
# Adapter 3: ElementAnalyser (wired)
# -----------------------------

class ProductionElementAnalyser:
    """Production-aligned element analyser, wired to severity_detector.

    Behavior order:
    1) If payload already contains analysed elements in payload['elements'], pass through.
    2) Else if payload contains SectionMetrics in payload['sections'], call
       infer_severities_for_chart(sections) to obtain an elements_skeleton with
       severity, score, and section_coverage.
       Then, restrict to elements present per tag-mapping (candidates), and enrich
       them with skeleton fields.
    3) Else fall back to deterministic tag-count scoring (legacy behavior).

    Policy: element '個人差' is excluded.
    """

    def __init__(
        self,
        chart_defining_elements: Optional[List[str]] = None,
    ):
        self.chart_defining_elements = set(chart_defining_elements or ["多点押し", "fake_end", "chart_stop"])

    def analyse(self, candidates: List[ElementCandidate], chart: ChartInput, difficulty: Difficulty) -> List[AnalysedElement]:
        raw = chart.payload

        # 1) Pass-through structured analysis if present.
        if isinstance(raw, dict) and isinstance(raw.get("elements"), list):
            analysed: List[AnalysedElement] = []
            for e in raw["elements"]:
                if not isinstance(e, dict):
                    continue
                name = e.get("name") or e.get("element_name")
                if name == "個人差":
                    continue
                sev = e.get("severity")
                score = float(e.get("score", 0.0))
                cov = float(e.get("section_coverage", 0.0))
                is_cd = bool(e.get("is_chart_defining", name in self.chart_defining_elements))

                g = e.get("guidance") or {}
                guidance = ElementGuidance(
                    difficulty_causes=str(g.get("difficulty_causes", "")),
                    chart_breakdown=str(g.get("chart_breakdown", "")),
                    primary_focus=str(g.get("primary_focus", "")),
                    secondary_focus=str(g.get("secondary_focus", "")),
                    strategy=str(g.get("strategy", "")),
                    target_section=str(g.get("target_section", "")),
                )

                analysed.append(
                    AnalysedElement(
                        name=str(name),
                        severity=sev if sev in SEVERITY_ORDER else "moderate",
                        score=max(0.0, min(1.0, score)),
                        section_coverage=max(0.0, min(1.0, cov)),
                        is_chart_defining=is_cd,
                        guidance=guidance,
                    )
                )
            return analysed

        # Build lookup from candidates (tag mapping)
        cand_by_name: Dict[str, ElementCandidate] = {c.name: c for c in candidates if c.name != "個人差"}

        # 2) If we have sections, wire severity_detector.
        if isinstance(raw, dict) and isinstance(raw.get("sections"), list) and raw.get("sections"):
            sections = raw["sections"]
            sev_result = _infer_severity_result(sections)
            skeleton = sev_result.get("elements_skeleton", []) or []

            # Index skeleton by JP element_name
            sk_by_name: Dict[str, Dict[str, Any]] = {}
            for el in skeleton:
                if not isinstance(el, dict):
                    continue
                nm = el.get("element_name") or el.get("name") or el.get("element_id")
                if isinstance(nm, str):
                    sk_by_name[nm] = el

            analysed: List[AnalysedElement] = []

            # Restrict to mapped elements (production presence definition)
            for name, c in cand_by_name.items():
                sk = sk_by_name.get(name)

                # Pull severity/score/coverage from skeleton if available
                sev = sk.get("severity") if isinstance(sk, dict) else None
                score = sk.get("score") if isinstance(sk, dict) else None
                cov = sk.get("section_coverage") if isinstance(sk, dict) else None

                # Fallback if skeleton is missing fields
                matched = c.evidence_tags or []
                training_items = list((c.meta or {}).get("training_items", []))

                if sev not in SEVERITY_ORDER:
                    # deterministic fallback from matched-tag count
                    tmp_score = min(1.0, 0.35 + 0.12 * len(set(matched)))
                    score = tmp_score
                    sev = _score_to_severity(tmp_score)

                if score is None:
                    score = 0.0
                score = float(score)

                if cov is None:
                    cov = 0.0
                cov = float(cov)

                is_cd = (name in self.chart_defining_elements)

                guidance = _derive_guidance_from_training_items(name, training_items, matched)

                analysed.append(
                    AnalysedElement(
                        name=name,
                        severity=sev,  # type: ignore[arg-type]
                        score=max(0.0, min(1.0, score)),
                        section_coverage=max(0.0, min(1.0, cov)),
                        is_chart_defining=is_cd,
                        guidance=guidance,
                    )
                )

            return analysed

        # 3) Legacy fallback (tag-only): deterministic tag-count scoring
        analysed: List[AnalysedElement] = []
        for name, c in cand_by_name.items():
            matched = c.evidence_tags or []
            training_items = list((c.meta or {}).get("training_items", []))

            score = min(1.0, 0.35 + 0.12 * len(set(matched)))
            sev = _score_to_severity(score)
            section_coverage = 0.25
            is_cd = (name in self.chart_defining_elements)
            guidance = _derive_guidance_from_training_items(name, training_items, matched)

            analysed.append(
                AnalysedElement(
                    name=name,
                    severity=sev,
                    score=score,
                    section_coverage=section_coverage,
                    is_chart_defining=is_cd,
                    guidance=guidance,
                )
            )

        return analysed


# -----------------------------
# Adapter 4: TipsGenerator
# -----------------------------

class ProductionTipsGenerator:
    """Production-aligned tips generator.

    Selection + templates are driven by the tips spec JSON.
    This adapter keeps the previously-exported behavior:
    - 3 elements for expert/master, 4 for append
    - eligibility: severity >= min_severity OR score >= chart_score * ratio OR chart_defining
    - sorted by score, severity, section_coverage
    """

    def __init__(self, tips_spec_path: Optional[str] = None):
        self.tips_spec_path = tips_spec_path
        self._spec: Optional[Dict[str, Any]] = None

    def _load_spec(self) -> Optional[Dict[str, Any]]:
        if not self.tips_spec_path:
            return None
        if self._spec is None:
            with open(self.tips_spec_path, "r", encoding="utf-8") as f:
                self._spec = json.load(f)
        return self._spec

    def generate(self, analysed: List[AnalysedElement], difficulty: Difficulty) -> Tuple[List[AnalysedElement], TipsOutput]:
        spec = self._load_spec()

        target = 4 if difficulty == "append" else 3
        min_sev: Severity = "moderate"
        score_ratio_threshold = 0.8
        chart_defining = {"多点押し", "fake_end", "chart_stop"}

        if spec and "tips_generation_spec" in spec:
            es = spec["tips_generation_spec"].get("element_selection", {})
            target = es.get("target_count", {}).get(difficulty, target)
            er = es.get("eligibility_rules", {})
            min_sev = er.get("min_severity", min_sev)
            score_ratio_threshold = er.get("score_ratio_threshold", score_ratio_threshold)
            chart_defining = set(es.get("chart_defining_elements", list(chart_defining)))

        scores = sorted([e.score for e in analysed], reverse=True)
        max_el = scores[0] if scores else 0.0
        top3 = scores[:3]
        avg_top3 = sum(top3) / len(top3) if top3 else 0.0
        chart_score = max_el * 0.4 + avg_top3 * 0.4

        eligible: List[AnalysedElement] = []
        for e in analysed:
            if SEV_INDEX[e.severity] >= SEV_INDEX[min_sev] or e.score >= chart_score * score_ratio_threshold or e.is_chart_defining or e.name in chart_defining:
                eligible.append(e)

        # Track B selection (B1, B2, B5) via selector_v2
        elements_for_select = [
            {
                "element_name": e.name,
                "severity": e.severity,
                "score": e.score,
                "section_coverage": e.section_coverage,
                "is_chart_defining": e.is_chart_defining,
            }
            for e in eligible
        ]

        selected_dicts = select_elements_v2(
            elements_for_select,
            difficulty,
            schema_path="proseka_internal_analysis_schema_v1.4.0.json",
        )

        by_name = {e.name: e for e in eligible}
        selected = [by_name[d.get("element_name")] for d in selected_dicts if d.get("element_name") in by_name]

        # Ensure exact count (fallback to best-ranked eligible if needed)
        if len(selected) < target:
            remaining = [e for e in eligible if e.name not in {s.name for s in selected}]
            remaining.sort(key=lambda e: (e.score, SEV_INDEX[e.severity], e.section_coverage), reverse=True)
            selected.extend(remaining[: max(0, target - len(selected))])
        selected = selected[:target]

        if not selected:
            return [], TipsOutput("", "")

        element_list = ", ".join([e.name for e in selected])
        focus_description = "define its primary mechanical focus" if difficulty != "append" else "form a layered mechanical focus"
        p1 = f"This chart features {element_list}, which {focus_description}."

        anchor = selected[0].guidance
        p2 = (
            f"The difficulty comes from {anchor.difficulty_causes}, where {anchor.chart_breakdown} increases execution pressure. "
            f"This manifests as {anchor.chart_breakdown}. "
            f"It helps to focus on {anchor.primary_focus}, prioritise {anchor.secondary_focus} over precision, and plan {anchor.strategy} early to stay consistent through {anchor.target_section}."
        )

        return selected, TipsOutput(p1, p2)


# -----------------------------
# Shared helpers
# -----------------------------

_SKILL_TO_CAUSE = {
    "timing": "timing pressure",
    "precision": "precision requirements",
    "coordination": "coordination load",
    "physical strength": "endurance pressure",
    "awareness": "recognition pressure",
    "chart readibility": "reading load",
    "hand movement": "hand movement control",
    "chart analysis": "pattern recognition",
    "mirror mode": "hand symmetry control",
    "chart analysis (optional)": "pattern recognition",
}


def _score_to_severity(score: float) -> Severity:
    if score <= 0.15:
        return "slight"
    if score <= 0.30:
        return "light"
    if score <= 0.45:
        return "mild"
    if score <= 0.60:
        return "moderate"
    if score <= 0.75:
        return "dense"
    if score <= 0.90:
        return "complex"
    return "demanding"


def _derive_guidance_from_training_items(element_name: str, training_items: List[str], matched_tags: List[str]) -> ElementGuidance:
    causes = [_SKILL_TO_CAUSE.get(x, x) for x in training_items]
    if not causes:
        causes = ["mechanical consistency"]

    difficulty_causes = ", ".join(dict.fromkeys(causes))

    if matched_tags:
        chart_breakdown = f"the chart repeatedly introduces tags such as {', '.join(matched_tags[:3])}"
    else:
        chart_breakdown = f"the chart repeatedly presents the {element_name} pattern"

    primary_focus = training_items[0] if training_items else "execution stability"
    secondary_focus = training_items[1] if len(training_items) > 1 else "timing consistency"

    if element_name in {"譜面停止", "局所難"}:
        strategy = "entry preparation"
        target_section = "transition points"
    elif element_name in {"物量", "長時間", "乱打"}:
        strategy = "stamina management"
        target_section = "late sections"
    elif element_name in {"多点押し", "5k", "6k"}:
        strategy = "finger assignment"
        target_section = "multi-key moments"
    else:
        strategy = "hand assignment"
        target_section = "dense sections"

    return ElementGuidance(
        difficulty_causes=difficulty_causes,
        chart_breakdown=chart_breakdown,
        primary_focus=primary_focus,
        secondary_focus=secondary_focus,
        strategy=strategy,
        target_section=target_section,
    )


__all__ = [
    "ProductionChartScanner",
    "ProductionTagToElementMapper",
    "ProductionElementAnalyser",
    "ProductionTipsGenerator",
]
