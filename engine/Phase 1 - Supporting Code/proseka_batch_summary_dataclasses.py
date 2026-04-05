"""proseka_batch_summary_dataclasses.py

Dataclass definitions for the batch-level summary output structure.

This module mirrors proseka_batch_summary_schema_v1.1.0.json and is intended for
pipeline use (build/validate/export). It does not depend on any chart parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal

Difficulty = Literal["expert","master","append"]


@dataclass
class ScoreDistribution:
    min: float
    p25: float
    p50: float
    p75: float
    p90: float
    max: float


@dataclass
class TopElement:
    element: str
    count: int
    share: float


@dataclass
class TipsCompliance:
    tips_generated_count: int
    tips_valid_count: int
    tips_valid_ratio: float
    avg_word_count: Optional[float] = None
    max_word_count: Optional[int] = None
    over_limit_count: Optional[int] = None


@dataclass
class BatchLevelSummary:
    """Aggregated summary statistics for a full difficulty batch.

    Required fields match the JSON schema required list.
    Optional fields provide diagnostics and ranking summaries.
    """

    # Optional but recommended
    batch_id: Optional[str] = None

    # Required
    difficulty: Difficulty = "expert"
    chart_count: int = 0
    element_frequency: Dict[str, int] = field(default_factory=dict)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    avg_score: float = 0.0
    avg_section_coverage: float = 0.0
    dominant_total: int = 0
    dominant_selected_count: int = 0
    dominant_selection_ratio: float = 0.0
    charts_with_full_dominant_coverage: int = 0
    charts_with_zero_dominant_coverage: int = 0

    # Optional extensions (v1.1.0)
    score_distribution: Optional[ScoreDistribution] = None
    top_elements: Optional[List[TopElement]] = None
    tips_compliance: Optional[TipsCompliance] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""

        def conv(obj):
            if obj is None:
                return None
            if hasattr(obj, "__dict__"):
                d = obj.__dict__.copy()
                for k, v in list(d.items()):
                    if isinstance(v, list):
                        d[k] = [conv(i) for i in v]
                    else:
                        d[k] = conv(v)
                return d
            return obj

        return conv(self)

    @staticmethod
    def from_dict(data: dict) -> "BatchLevelSummary":
        """Create BatchLevelSummary from a dict (e.g., loaded JSON)."""

        sd = data.get("score_distribution")
        te = data.get("top_elements")
        tc = data.get("tips_compliance")

        return BatchLevelSummary(
            batch_id=data.get("batch_id"),
            difficulty=data["difficulty"],
            chart_count=data["chart_count"],
            element_frequency=data["element_frequency"],
            severity_distribution=data["severity_distribution"],
            avg_score=data["avg_score"],
            avg_section_coverage=data["avg_section_coverage"],
            dominant_total=data["dominant_total"],
            dominant_selected_count=data["dominant_selected_count"],
            dominant_selection_ratio=data["dominant_selection_ratio"],
            charts_with_full_dominant_coverage=data["charts_with_full_dominant_coverage"],
            charts_with_zero_dominant_coverage=data["charts_with_zero_dominant_coverage"],
            score_distribution=ScoreDistribution(**sd) if isinstance(sd, dict) else None,
            top_elements=[TopElement(**x) for x in te] if isinstance(te, list) else None,
            tips_compliance=TipsCompliance(**tc) if isinstance(tc, dict) else None,
            notes=data.get("notes")
        )

    def validate_basic(self) -> None:
        """Lightweight checks that mirror schema constraints (non-exhaustive)."""

        if self.chart_count < 0:
            raise ValueError("chart_count must be >= 0")
        if not (0.0 <= self.avg_score <= 1.0):
            raise ValueError("avg_score must be in [0,1]")
        if not (0.0 <= self.avg_section_coverage <= 1.0):
            raise ValueError("avg_section_coverage must be in [0,1]")
        if self.dominant_total < 0 or self.dominant_selected_count < 0:
            raise ValueError("dominant counts must be >= 0")
        if self.dominant_total == 0 and self.dominant_selection_ratio != 0.0:
            raise ValueError("dominant_selection_ratio must be 0.0 when dominant_total == 0")
        if not (0.0 <= self.dominant_selection_ratio <= 1.0):
            raise ValueError("dominant_selection_ratio must be in [0,1]")


__all__ = [
    "Difficulty",
    "ScoreDistribution",
    "TopElement",
    "TipsCompliance",
    "BatchLevelSummary",
]
