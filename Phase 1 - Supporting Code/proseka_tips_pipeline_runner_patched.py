"""proseka_tips_pipeline_runner.py

Portable orchestration module for the Gameplay-Tips Generation workflow.

Default adapters
- This runner now defaults to the production-wired adapters in:
  proseka_pipeline_adapters_production_wired.py
  (wired to (5.1) severity_detector.infer_severities_for_chart).

If you want to override behavior, pass your own scanner/mapper/analyser/tips_generator
instances into run_batch().

No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Literal
import json
import time

Difficulty = Literal["expert", "master", "append"]
Severity = Literal["slight","light","mild","moderate","dense","complex","demanding"]


def log_event(stage: str, message: str, **fields: Any) -> Dict[str, Any]:
    """Structured log event (JSON-serializable)."""
    return {
        "ts": time.time(),
        "stage": stage,
        "message": message,
        "fields": fields or {},
    }


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
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ElementCandidate:
    name: str
    evidence_tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


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


@dataclass
class PerChartSummary:
    chart_id: Optional[str]
    song_id: Optional[str]
    element_count: int
    element_frequency: Dict[str, int]
    severity_distribution: Dict[str, int]
    avg_score: float
    avg_section_coverage: float
    max_score: float
    dominant_elements: List[str]
    dominant_selected_flags: Dict[str, bool]


@dataclass
class BatchSummary:
    batch_id: Optional[str]
    difficulty: Difficulty
    chart_count: int
    element_frequency: Dict[str, int]
    severity_distribution: Dict[str, int]
    avg_score: float
    avg_section_coverage: float
    dominant_total: int
    dominant_selected_count: int
    dominant_selection_ratio: float
    charts_with_full_dominant_coverage: int
    charts_with_zero_dominant_coverage: int


@dataclass
class ChartResult:
    chart_id: Optional[str]
    song_id: Optional[str]
    tips_text: str
    chart_summary: PerChartSummary


@dataclass
class BatchResult:
    batch_id: Optional[str]
    difficulty: Difficulty
    results: List[ChartResult]
    summary: BatchSummary
    logs: List[Dict[str, Any]] = field(default_factory=list)


# -----------------------------
# Default adapters (production-wired)
# -----------------------------

try:
    from proseka_pipeline_adapters_production_wired import (
        ProductionChartScanner as DefaultChartScanner,
        ProductionTagToElementMapper as DefaultTagToElementMapper,
        ProductionElementAnalyser as DefaultElementAnalyser,
        ProductionTipsGenerator as DefaultTipsGenerator,
    )
except Exception:  # pragma: no cover
    DefaultChartScanner = None
    DefaultTagToElementMapper = None
    DefaultElementAnalyser = None
    DefaultTipsGenerator = None


class ChartScanner:
    def scan(self, chart: ChartInput) -> List[TagSignal]:
        return []


class TagToElementMapper:
    def map_tags(self, tags: List[TagSignal], difficulty: Difficulty) -> List[ElementCandidate]:
        return []


class ElementAnalyser:
    def analyse(self, candidates: List[ElementCandidate], chart: ChartInput, difficulty: Difficulty) -> List[AnalysedElement]:
        return []


class TipsGenerator:
    def generate(self, analysed: List[AnalysedElement], difficulty: Difficulty) -> Tuple[List[AnalysedElement], TipsOutput]:
        return ([], TipsOutput("", ""))


@dataclass
class RunnerConfig:
    min_detected_tags: int = 1
    min_candidates: int = 1
    stop_on_unapproachable: bool = True


def is_approachable_for_tips(tags: List[TagSignal], candidates: List[ElementCandidate], cfg: RunnerConfig) -> bool:
    if len(tags) < cfg.min_detected_tags:
        return False
    if len(candidates) < cfg.min_candidates:
        return False
    return True


def build_per_chart_summary(chart: ChartInput, analysed_all: List[AnalysedElement], selected_for_tips: List[AnalysedElement]) -> PerChartSummary:
    freq: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {}
    scores: List[float] = []
    covs: List[float] = []

    for e in analysed_all:
        freq[e.name] = freq.get(e.name, 0) + 1
        sev_dist[e.severity] = sev_dist.get(e.severity, 0) + 1
        scores.append(e.score)
        covs.append(e.section_coverage)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_cov = sum(covs) / len(covs) if covs else 0.0
    max_score = max(scores) if scores else 0.0

    tol = 1e-6
    dominant = [e.name for e in analysed_all if abs(e.score - max_score) <= tol]
    selected_names = {e.name for e in selected_for_tips}
    dominant_flags = {name: (name in selected_names) for name in dominant}

    return PerChartSummary(
        chart_id=chart.chart_id,
        song_id=chart.song_id,
        element_count=len(analysed_all),
        element_frequency=freq,
        severity_distribution=sev_dist,
        avg_score=avg_score,
        avg_section_coverage=avg_cov,
        max_score=max_score,
        dominant_elements=dominant,
        dominant_selected_flags=dominant_flags,
    )


def build_batch_summary(batch_id: Optional[str], difficulty: Difficulty, chart_summaries: List[PerChartSummary]) -> BatchSummary:
    element_freq: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {}
    scores: List[float] = []
    covs: List[float] = []

    dominant_total = 0
    dominant_selected = 0
    full_dom_cov = 0
    zero_dom_cov = 0

    for cs in chart_summaries:
        scores.append(cs.avg_score)
        covs.append(cs.avg_section_coverage)

        for k, v in cs.element_frequency.items():
            element_freq[k] = element_freq.get(k, 0) + v
        for k, v in cs.severity_distribution.items():
            sev_dist[k] = sev_dist.get(k, 0) + v

        d = cs.dominant_elements
        dominant_total += len(d)
        selected_count = sum(1 for name in d if cs.dominant_selected_flags.get(name))
        dominant_selected += selected_count

        if len(d) > 0 and selected_count == len(d):
            full_dom_cov += 1
        if len(d) > 0 and selected_count == 0:
            zero_dom_cov += 1

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_cov = sum(covs) / len(covs) if covs else 0.0
    ratio = (dominant_selected / dominant_total) if dominant_total else 0.0

    return BatchSummary(
        batch_id=batch_id,
        difficulty=difficulty,
        chart_count=len(chart_summaries),
        element_frequency=element_freq,
        severity_distribution=sev_dist,
        avg_score=avg_score,
        avg_section_coverage=avg_cov,
        dominant_total=dominant_total,
        dominant_selected_count=dominant_selected,
        dominant_selection_ratio=ratio,
        charts_with_full_dominant_coverage=full_dom_cov,
        charts_with_zero_dominant_coverage=zero_dom_cov,
    )


def run_batch(
    *,
    batch_id: Optional[str],
    difficulty: Difficulty,
    charts: List[ChartInput],
    scanner: Optional[Any] = None,
    mapper: Optional[Any] = None,
    analyser: Optional[Any] = None,
    tips_generator: Optional[Any] = None,
    cfg: Optional[RunnerConfig] = None,
) -> BatchResult:
    """Full pipeline runner for a difficulty-ordered batch.

    If scanner/mapper/analyser/tips_generator are not provided, this function
    uses the production-wired defaults.
    """

    cfg = cfg or RunnerConfig()

    # Instantiate defaults lazily
    if scanner is None:
        scanner = DefaultChartScanner() if DefaultChartScanner else ChartScanner()
    if mapper is None:
        mapper = DefaultTagToElementMapper() if DefaultTagToElementMapper else TagToElementMapper()
    if analyser is None:
        analyser = DefaultElementAnalyser() if DefaultElementAnalyser else ElementAnalyser()
    if tips_generator is None:
        tips_generator = DefaultTipsGenerator() if DefaultTipsGenerator else TipsGenerator()

    logs: List[Dict[str, Any]] = []
    results: List[ChartResult] = []
    chart_summaries: List[PerChartSummary] = []

    logs.append(log_event("start", "Batch run started", batch_id=batch_id, difficulty=difficulty, chart_count=len(charts)))

    for chart in charts:
        logs.append(log_event("chart_start", "Processing chart", chart_id=chart.chart_id, song_id=chart.song_id))

        tags = scanner.scan(chart)
        logs.append(log_event("scan", "Tag scan complete", chart_id=chart.chart_id, tag_count=len(tags)))

        candidates = mapper.map_tags(tags, difficulty)
        logs.append(log_event("map", "Mapped tags to element candidates", chart_id=chart.chart_id, candidate_count=len(candidates)))

        approachable = is_approachable_for_tips(tags, candidates, cfg)
        logs.append(log_event("gate", "Approachability check", chart_id=chart.chart_id, approachable=approachable))

        if not approachable and cfg.stop_on_unapproachable:
            logs.append(log_event("stop", "Stopping pipeline for chart: insufficient structure for tips", chart_id=chart.chart_id))
            analysed: List[AnalysedElement] = []
            selected: List[AnalysedElement] = []
            tips = TipsOutput("", "")
            cs = build_per_chart_summary(chart, analysed, selected)
            chart_summaries.append(cs)
            results.append(ChartResult(chart.chart_id, chart.song_id, tips.full_text, cs))
            continue

        analysed = analyser.analyse(candidates, chart, difficulty)
        logs.append(log_event("analyse", "Internal analysis complete", chart_id=chart.chart_id, analysed_count=len(analysed)))

        selected, tips = tips_generator.generate(analysed, difficulty)
        logs.append(log_event("tips", "Tips generated", chart_id=chart.chart_id, selected_count=len(selected), tip_length=len(tips.full_text)))

        cs = build_per_chart_summary(chart, analysed, selected)
        chart_summaries.append(cs)

        results.append(ChartResult(chart.chart_id, chart.song_id, tips.full_text, cs))
        logs.append(log_event("chart_end", "Chart processing complete", chart_id=chart.chart_id))

    summary = build_batch_summary(batch_id, difficulty, chart_summaries)
    logs.append(log_event("end", "Batch run complete", batch_id=batch_id, difficulty=difficulty))

    return BatchResult(batch_id=batch_id, difficulty=difficulty, results=results, summary=summary, logs=logs)


def to_json(obj: Any, *, indent: int = 2) -> str:
    if hasattr(obj, "__dataclass_fields__"):
        return json.dumps(asdict(obj), ensure_ascii=False, indent=indent)
    return json.dumps(obj, ensure_ascii=False, indent=indent)


__all__ = [
    "ChartInput",
    "TagSignal",
    "ElementCandidate",
    "ElementGuidance",
    "AnalysedElement",
    "TipsOutput",
    "PerChartSummary",
    "BatchSummary",
    "ChartResult",
    "BatchResult",
    "RunnerConfig",
    "run_batch",
    "to_json",
]
