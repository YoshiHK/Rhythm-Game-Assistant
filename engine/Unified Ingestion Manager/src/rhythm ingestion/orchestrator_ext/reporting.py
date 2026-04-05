"""rhythm_ingestion.orchestrator_ext.reporting

Observability helpers for structured RunReport.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .types import GateResult, RunMode, RunReport, StageResult


def run_report_to_dict(report: RunReport) -> Dict[str, Any]:
    return asdict(report)


def minimal_report(*, run_key: str, game_id: str, chart_id: str, mode: RunMode, stage_results: List[StageResult], gates: Optional[List[GateResult]] = None, degraded_mode: bool = False, warnings: Optional[List[str]] = None, diagnostics: Optional[Dict[str, Any]] = None) -> RunReport:
    return RunReport(run_key=run_key, game_id=game_id, chart_id=chart_id, mode=mode, stage_results=list(stage_results), gates=list(gates or []), degraded_mode=bool(degraded_mode), warnings=list(warnings or []), diagnostics=dict(diagnostics or {}))
