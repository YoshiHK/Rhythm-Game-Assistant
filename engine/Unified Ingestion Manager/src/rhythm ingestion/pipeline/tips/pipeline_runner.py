from __future__ import annotations
"""pipeline_runner.py

Phase 3 runner with tips_generator integration (Wave 2) + tone hint wiring + logging.

Latest update:
- Logs tone_hint decisions per chart for observability and QA.
- Ensures tone_hint is always surfaced in tips output.

No Completed Phase code is modified.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Literal
import json
import time

Difficulty = Literal['expert', 'master', 'append']


def log_event(stage: str, message: str, **fields: Any) -> Dict[str, Any]:
    return {
        'ts': time.time(),
        'stage': stage,
        'message': message,
        'fields': fields or {},
    }


@dataclass
class ChartInput:
    chart_id: Optional[str] = None
    song_id: Optional[str] = None
    master_level: Optional[int] = None
    payload: Any = None


@dataclass
class ChartResult:
    chart_id: Optional[str]
    song_id: Optional[str]
    tips: Dict[str, Any]


@dataclass
class BatchResult:
    batch_id: Optional[str]
    difficulty: Difficulty
    results: List[ChartResult]
    logs: List[Dict[str, Any]] = field(default_factory=list)


# Default adapters (Phase 1/2)
try:
    from proseka_pipeline_adapters_production_wired import (
        ProductionChartScanner as DefaultChartScanner,
        ProductionTagToElementMapper as DefaultTagToElementMapper,
        ProductionElementAnalyser as DefaultElementAnalyser,
    )
except Exception:  # pragma: no cover
    DefaultChartScanner = None
    DefaultTagToElementMapper = None
    DefaultElementAnalyser = None


from .severity_engine import build_elements_skeleton
from .tips_generator import run_for_chart as run_tips_for_chart


def _tone_from_payload(payload: Dict[str, Any]) -> str:
    diag = payload.get('diagnostics')
    if isinstance(diag, dict):
        t = diag.get('tone_hint')
        if isinstance(t, str):
            return t
    return 'normal'


def run_batch(
    *,
    batch_id: Optional[str],
    game_id: str,
    difficulty: Difficulty,
    charts: List[ChartInput],
    scanner: Optional[Any] = None,
    mapper: Optional[Any] = None,
    analyser: Optional[Any] = None,
) -> BatchResult:
    logs: List[Dict[str, Any]] = []
    results: List[ChartResult] = []

    scanner = scanner or (DefaultChartScanner() if DefaultChartScanner is not None else None)

    for chart in charts:
        payload: Dict[str, Any] = chart.payload or {}
        try:
            if scanner is None:
                raise RuntimeError('ChartScanner unavailable')

            tags = scanner.scan(chart)
            payload['detected_tags'] = [t.tag for t in tags]

            # Stage 5.1 wiring
            build_elements_skeleton(
                game_id,
                payload,
                detected_tags=payload.get('detected_tags'),
            )

            # Tips generation (Track B/C/D via tips_generator)
            tips = run_tips_for_chart(
                game_id,
                payload,
                {'difficulty': difficulty, 'song_id': chart.song_id},
            )

            # Ensure tone_hint is present in output
            tone_hint = None
            if isinstance(tips, dict):
                tone_hint = tips.get('tone_hint')
                if not isinstance(tone_hint, str):
                    tone_hint = _tone_from_payload(payload)
                    tips['tone_hint'] = tone_hint
            else:
                tips = {}
                tone_hint = _tone_from_payload(payload)
                tips['tone_hint'] = tone_hint

            # Log tone decision for observability
            logs.append(
                log_event(
                    'tone_hint',
                    'Tone hint resolved for chart',
                    chart_id=chart.chart_id,
                    song_id=chart.song_id,
                    difficulty=difficulty,
                    tone_hint=tone_hint,
                )
            )

            results.append(
                ChartResult(
                    chart_id=chart.chart_id,
                    song_id=chart.song_id,
                    tips=tips,
                )
            )

        except Exception as e:
            logs.append(
                log_event(
                    'chart_error',
                    f'{type(e).__name__}: {e}',
                    chart_id=chart.chart_id,
                )
            )

    return BatchResult(batch_id=batch_id, difficulty=difficulty, results=results, logs=logs)


def to_json(obj: Any, *, indent: int = 2) -> str:
    if hasattr(obj, '__dataclass_fields__'):
        return json.dumps(asdict(obj), ensure_ascii=False, indent=indent)
    return json.dumps(obj, ensure_ascii=False, indent=indent)


__all__ = ['ChartInput', 'ChartResult', 'BatchResult', 'run_batch', 'to_json']
