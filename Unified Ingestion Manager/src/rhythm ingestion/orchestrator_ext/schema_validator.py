"""rhythm_ingestion.orchestrator_ext.schema_validator

JSON schema validation hook for orchestrator extension outputs.

Scope:
- Control-plane only.
- Additive / non-breaking.
- Intended for CI checks, QA tooling, and optional runtime assertions.

This module validates:
1) RunReport objects against `schemas/orchestrator_run_report.schema.json`
2) CLI JSON projection objects against `schemas/orchestrator_cli_result.schema.json`

Dependency policy:
- Prefers `jsonschema` if available.
- Falls back to minimal structural checks if `jsonschema` is unavailable.

Note: This module MUST NOT modify Phase 1/2/4 behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class SchemaValidationResult:
    ok: bool
    error: Optional[str] = None


def _schema_dir() -> Path:
    return Path(__file__).resolve().parent / 'schemas'


def _load_schema(name: str) -> Dict[str, Any]:
    p = _schema_dir() / name
    import json
    return json.loads(p.read_text(encoding='utf-8'))


def _try_jsonschema_validate(instance: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    try:
        import jsonschema  # type: ignore
        # Draft 2020-12 compatible validator
        jsonschema.validate(instance=instance, schema=schema)
        return True, None
    except ImportError:
        return False, 'jsonschema_not_installed'
    except Exception as e:
        return False, str(e)


def _minimal_run_report_checks(obj: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(obj, dict):
        return False, 'run_report_not_object'
    for k in ('run_key', 'game_id', 'chart_id', 'mode', 'stage_results', 'degraded_mode'):
        if k not in obj:
            return False, f'missing_{k}'
    if not isinstance(obj.get('stage_results'), list) or len(obj['stage_results']) == 0:
        return False, 'stage_results_empty'
    # If any stage has status STOP, require a gate with reason_code (best-effort)
    for sr in obj['stage_results']:
        if isinstance(sr, dict) and sr.get('status') == 'STOP':
            gate = sr.get('gate')
            if not isinstance(gate, dict) or not gate.get('reason_code'):
                return False, 'stop_without_reason_code'
    return True, None


def _minimal_cli_checks(obj: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(obj, dict):
        return False, 'cli_result_not_object'
    for k in ('file', 'game_id', 'passed'):
        if k not in obj:
            return False, f'missing_{k}'
    if obj.get('passed') is False:
        for k in ('decision', 'stage', 'reason_code'):
            if k not in obj:
                return False, f'missing_{k}_for_failed'
    return True, None


def validate_run_report(report: Dict[str, Any]) -> SchemaValidationResult:
    schema = _load_schema('orchestrator_run_report.schema.json')
    ok, err = _try_jsonschema_validate(report, schema)
    if ok:
        return SchemaValidationResult(ok=True)
    if err == 'jsonschema_not_installed':
        ok2, err2 = _minimal_run_report_checks(report)
        return SchemaValidationResult(ok=ok2, error=err2)
    return SchemaValidationResult(ok=False, error=err)


def validate_cli_result(cli_obj: Dict[str, Any]) -> SchemaValidationResult:
    schema = _load_schema('orchestrator_cli_result.schema.json')
    ok, err = _try_jsonschema_validate(cli_obj, schema)
    if ok:
        return SchemaValidationResult(ok=True)
    if err == 'jsonschema_not_installed':
        ok2, err2 = _minimal_cli_checks(cli_obj)
        return SchemaValidationResult(ok=ok2, error=err2)
    return SchemaValidationResult(ok=False, error=err)
