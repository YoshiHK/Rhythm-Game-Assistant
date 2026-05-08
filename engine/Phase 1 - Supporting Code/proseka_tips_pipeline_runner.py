"""proseka_tips_pipeline_runner.py

Portable orchestration module for the Gameplay-Tips Generation workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Literal
import json
import time

Difficulty = Literal["expert", "master", "append"]
Severity = Literal["slight", "light", "mild", "moderate", "dense", "complex", "demanding"]


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
    def analyse(
        self,
        candidates: List[ElementCandidate],
        chart: ChartInput,
        difficulty: Difficulty,
    ) -> List[AnalysedElement]:
        return []


class TipsGenerator:
    def generate(
        self,
        analysed: List[AnalysedElement],
        difficulty: Difficulty,
    ) -> Tuple[List[AnalysedElement], TipsOutput]:
        return [], TipsOutput("", "")


@dataclass
class RunnerConfig:
    min_detected_tags: int = 1
    min_candidates: int = 1
    stop_on_unapproachable: bool = True


def is_approachable_for_tips(
    tags: List[TagSignal],
    candidates: List[ElementCandidate],
    cfg: RunnerConfig,
) -> bool:
    if len(tags) < cfg.min_detected_tags:
        return False
    if len(candidates) < cfg.min_candidates:
        return False
    return True


def build_per_chart_summary(
    chart: ChartInput,
    analysed_all: List[AnalysedElement],
    selected_for_tips: List[AnalysedElement],
) -> PerChartSummary:
    freq: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {}
    scores: List[float] = []
    covs: List[float] = []
    # Stub: logic implemented elsewhere
    return PerChartSummary(
        chart.chart_id,
        chart.song_id,
        0,
        freq,
        sev_dist,
        0.0,
        0.0,
        0.0,
        [],
        {},
    )


def build_batch_summary(
    batch_id: Optional[str],
    difficulty: Difficulty,
    chart_summaries: List[PerChartSummary],
) -> BatchSummary:
    element_freq: Dict[str, int] = {}
    sev_dist: Dict[str, int] = {}
    scores: List[float] = []
    covs: List[float] = []
    # Stub: logic implemented elsewhere
    return BatchSummary(
        batch_id,
        difficulty,
        len(chart_summaries),
        element_freq,
        sev_dist,
        0.0,
        0.0,
        0,
        0,
        0.0,
        0,
        0,
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
    """Full pipeline runner for a difficulty-ordered batch."""
    raise NotImplementedError("run_batch is a wiring-only stub.")


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