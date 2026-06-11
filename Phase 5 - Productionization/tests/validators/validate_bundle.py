from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# --------------------------------------------------
# Import strategy:
# - package mode: python -m ...
# - script mode:  python validate_bundle.py
# --------------------------------------------------
if __package__ in (None, ""):
    _THIS_DIR = Path(__file__).resolve().parent
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))

    from schema_validator import validate_structured_event_batch
    from contract_validator import validate_contract_bundle
    from coverage_validator import validate_coverage_bundle
    from artifact_integrity_validator import validate_pipeline_result_artifacts
    from metrics_guard_validator import validate_metrics_guard_bundle
    from contract_baseline_validator import validate_contract_baseline_bundle
    from test_case_integrity_validator import validate_test_case_integrity
else:
    from .schema_validator import validate_structured_event_batch
    from .contract_validator import validate_contract_bundle
    from .coverage_validator import validate_coverage_bundle
    from .artifact_integrity_validator import validate_pipeline_result_artifacts
    from .metrics_guard_validator import validate_metrics_guard_bundle
    from .contract_baseline_validator import validate_contract_baseline_bundle
    from .test_case_integrity_validator import validate_test_case_integrity

DEFAULT_REQUIRED_ARTIFACTS = (
    "selector_params",
    "training_report",
    "evaluation_report",
)

DEFAULT_METRIC_NAMES = (
    "accept_or_better_rate",
    "played_or_better_rate",
    "completed_rate",
    "mean_outcome_score",
)


def _load_json(path: str | Path) -> Any:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def _maybe_load(path: str | Path | None) -> Any:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return _load_json(p)


def _merge_results(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    results = list(results)
    passed = all(bool(r.get("passed")) for r in results)
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    for r in results:
        validator = str(r.get("validator", "unknown"))
        details[validator] = r
        errors.extend(r.get("errors") or [])
        warnings.extend(r.get("warnings") or [])

    return {
        "validator": "validate_bundle",
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }


def _extract_pipeline_result(pipeline_result: Any) -> Dict[str, Any]:
    if not isinstance(pipeline_result, dict):
        return {}
    if isinstance(pipeline_result.get("result"), dict):
        return pipeline_result["result"]
    return pipeline_result


def _extract_artifact_paths(pipeline_result: Any) -> Optional[Dict[str, str]]:
    result_obj = _extract_pipeline_result(pipeline_result)
    paths = result_obj.get("paths") if isinstance(result_obj, dict) else None
    return paths if isinstance(paths, dict) else None


def _extract_evaluation_report(pipeline_result: Any) -> Optional[Dict[str, Any]]:
    result_obj = _extract_pipeline_result(pipeline_result)

    if not isinstance(result_obj, dict):
        return None

    evaluation_obj = result_obj.get("evaluation")
    if isinstance(evaluation_obj, dict):
        return evaluation_obj

    payload_obj = result_obj.get("payload")
    if isinstance(payload_obj, dict) and isinstance(payload_obj.get("metrics"), dict):
        return payload_obj

    return None


def _extract_current_metrics(evaluation_report: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(evaluation_report, dict):
        return None
    metrics = evaluation_report.get("metrics")
    return metrics if isinstance(metrics, dict) else None


def _case_expectations_from_path(case_path: str | Path | None) -> Dict[str, Any]:
    if case_path is None:
        return {}
    expect_path = Path(case_path) / "coverage.expect.json"
    if not expect_path.exists():
        return {}
    try:
        obj = json.loads(expect_path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


# NEW
def _load_contract_baseline(case_path: str | Path | None) -> Optional[Dict[str, Any]]:
    if case_path is None:
        return None
    p = Path(case_path) / "contract_baseline_metrics.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# NEW
def _load_integrity_spec(case_path: str | Path | None) -> Optional[Dict[str, Any]]:
    if case_path is None:
        return None
    p = Path(case_path) / "test_case_integrity.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _resolve_required_artifacts(user_value: Optional[Iterable[str]]) -> List[str]:
    items = list(user_value) if user_value is not None else list(DEFAULT_REQUIRED_ARTIFACTS)
    return [str(x).strip() for x in items if str(x).strip()]


def _resolve_required_event_types(
    user_value: Optional[Iterable[str]],
    coverage_expect: Dict[str, Any],
) -> Optional[List[str]]:
    if user_value is not None:
        vals = [str(x).strip() for x in user_value if str(x).strip()]
        return vals or None

    vals = coverage_expect.get("required_event_types")
    if isinstance(vals, list):
        out = [str(x).strip() for x in vals if str(x).strip()]
        return out or None

    return None


def run_validation_bundle(
    *,
    case_path: str | Path | None = None,
    structured_events_path: str | Path | None = None,
    interpreted_outputs_path: str | Path | None = None,
    pipeline_result_path: str | Path | None = None,
    baseline_metrics_path: str | Path | None = None,
    deployment_decision_path: str | Path | None = None,
    min_events: int = 1,
    required_event_types: Optional[Iterable[str]] = None,
    require_interpretation_output: bool = False,
    required_artifacts: Optional[Iterable[str]] = None,
    drift_tolerance: float = 0.10,
    regression_tolerance: float = 0.0,
) -> Dict[str, Any]:
    """
    Aggregate Phase 5 validators into a single bundle result.

    Alignment rules:
    - TEST_CASE_CONTRACT.md:
      * supports coverage.expect.json under case_path
      * supports drift_baseline_metrics.json under case_path when baseline
        not explicitly provided
      * supports regression_baseline_metrics.json under case_path when baseline
        not explicitly provided
      * treats interpretation output as optional unless required by contract
        or explicit flag
    - OFFLINE_ARTIFACT_CONTRACT.md:
      * expects phase5 pipeline result to expose result.paths as source of truth
      * validates required artifacts selector_params / training_report /
        evaluation_report by default
      * uses validator bundle JSON return contract
    """
    results: List[Dict[str, Any]] = []

    coverage_expect = _case_expectations_from_path(case_path)
    contract_baseline = _load_contract_baseline(case_path)   # NEW
    integrity_spec = _load_integrity_spec(case_path)         # NEW

    if baseline_metrics_path is None and case_path is not None:
        drift_candidate = Path(case_path) / "drift_baseline_metrics.json"
        regression_candidate = Path(case_path) / "regression_baseline_metrics.json"

        if drift_candidate.exists():
            baseline_metrics_path = drift_candidate
        elif regression_candidate.exists():
            baseline_metrics_path = regression_candidate

    structured_events = _maybe_load(structured_events_path)
    interpreted_outputs = _maybe_load(interpreted_outputs_path)
    pipeline_result = _maybe_load(pipeline_result_path)
    baseline_metrics = _maybe_load(baseline_metrics_path)
    deployment_decision = _maybe_load(deployment_decision_path)

    resolved_min_events = int(coverage_expect.get("min_structured_events", min_events))
    resolved_required_event_types = _resolve_required_event_types(
        required_event_types,
        coverage_expect,
    )
    resolved_require_interpretation = bool(
        coverage_expect.get("require_interpretation_output", require_interpretation_output)
    )
    resolved_required_artifacts = _resolve_required_artifacts(required_artifacts)

    # ------------------------------------------------------------------
    # Test-case integrity validation (NEW)
    # ------------------------------------------------------------------
    if integrity_spec is not None:
        results.append(
            validate_test_case_integrity(
                case_path=case_path,
                integrity_spec=integrity_spec,
            )
        )

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------
    if structured_events is not None:
        if isinstance(structured_events, list):
            results.append(validate_structured_event_batch(structured_events))
        else:
            results.append(
                {
                    "validator": "schema_validator.structured_event_batch",
                    "passed": False,
                    "errors": ["structured_events_path must contain a JSON array"],
                    "warnings": [],
                    "details": {},
                }
            )

    if structured_events is None and case_path is not None:
        results.append(
            {
                "validator": "schema_validator.structured_event_batch",
                "passed": False,
                "errors": ["structured_events_path is required for case-compatible validation"],
                "warnings": [],
                "details": {"case_path": str(case_path)},
            }
        )

    # ------------------------------------------------------------------
    # Contract validation (existing)
    # ------------------------------------------------------------------
    results.append(
        validate_contract_bundle(
            entry_events=structured_events if isinstance(structured_events, list) else None,
            interpreted_outputs=interpreted_outputs if isinstance(interpreted_outputs, list) else None,
            curator_labels=None,
        )
    )

    # ------------------------------------------------------------------
    # Contract baseline validation (NEW)
    # ------------------------------------------------------------------
    if contract_baseline is not None:
        results.append(
            validate_contract_baseline_bundle(
                events=structured_events if isinstance(structured_events, list) else None,
                interpreted_outputs=interpreted_outputs if isinstance(interpreted_outputs, list) else None,
                pipeline_result=pipeline_result if isinstance(pipeline_result, dict) else None,
                contract_baseline=contract_baseline,
            )
        )

    # ------------------------------------------------------------------
    # Coverage + artifact-path extraction
    # ------------------------------------------------------------------
    artifact_paths = _extract_artifact_paths(pipeline_result)
    evaluation_report = _extract_evaluation_report(pipeline_result)
    current_metrics = _extract_current_metrics(evaluation_report)

    results.append(
        validate_coverage_bundle(
            events=structured_events if isinstance(structured_events, list) else None,
            interpreted_outputs=interpreted_outputs if isinstance(interpreted_outputs, list) else None,
            artifact_paths=artifact_paths,
            min_events=resolved_min_events,
            required_event_types=resolved_required_event_types,
            require_interpretation_output=resolved_require_interpretation,
            required_artifacts=resolved_required_artifacts,
        )
    )

    # ------------------------------------------------------------------
    # Artifact integrity
    # ------------------------------------------------------------------
    if artifact_paths is not None:
        results.append(validate_pipeline_result_artifacts(pipeline_result))
    elif case_path is not None:
        results.append(
            {
                "validator": "artifact_integrity_validator.pipeline_result",
                "passed": False,
                "errors": ["pipeline_result must expose result.paths as artifact source of truth"],
                "warnings": [],
                "details": {"required_artifacts": resolved_required_artifacts},
            }
        )

    # ------------------------------------------------------------------
    # Metrics / drift / regression / deployment-gate validation
    # ------------------------------------------------------------------
    if current_metrics is not None:
        results.append(
            validate_metrics_guard_bundle(
                current_metrics=current_metrics,
                baseline_metrics=baseline_metrics if isinstance(baseline_metrics, dict) else None,
                metric_names=DEFAULT_METRIC_NAMES,
                drift_tolerance=drift_tolerance,
                regression_tolerance=regression_tolerance,
                evaluation_report=evaluation_report if isinstance(evaluation_report, dict) else None,
                deployment_decision=deployment_decision if isinstance(deployment_decision, dict) else None,
            )
        )
    elif case_path is not None and pipeline_result is not None:
        results.append(
            {
                "validator": "metrics_guard_validator.bundle",
                "passed": False,
                "errors": ["unable to extract evaluation metrics from pipeline_result"],
                "warnings": [],
                "details": {},
            }
        )

    merged = _merge_results(results)
    merged["details"]["contract_alignment"] = {
        "case_path": str(case_path) if case_path is not None else None,
        "resolved_min_events": resolved_min_events,
        "resolved_required_event_types": resolved_required_event_types,
        "resolved_require_interpretation_output": resolved_require_interpretation,
        "resolved_required_artifacts": resolved_required_artifacts,
        "baseline_metrics_path": str(baseline_metrics_path) if baseline_metrics_path is not None else None,
        "has_contract_baseline": contract_baseline is not None,
        "has_integrity_spec": integrity_spec is not None,
    }
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 5 validator bundle")
    parser.add_argument("--case_path", default=None)
    parser.add_argument("--structured_events_path", default=None)
    parser.add_argument("--interpreted_outputs_path", default=None)
    parser.add_argument("--pipeline_result_path", default=None)
    parser.add_argument("--baseline_metrics_path", default=None)
    parser.add_argument("--deployment_decision_path", default=None)
    parser.add_argument("--min_events", type=int, default=1)
    parser.add_argument("--required_event_types", nargs="*", default=None)
    parser.add_argument("--require_interpretation_output", action="store_true")
    parser.add_argument("--required_artifacts", nargs="*", default=None)
    parser.add_argument("--drift_tolerance", type=float, default=0.10)
    parser.add_argument("--regression_tolerance", type=float, default=0.0)

    args = parser.parse_args()

    result = run_validation_bundle(
        case_path=args.case_path,
        structured_events_path=args.structured_events_path,
        interpreted_outputs_path=args.interpreted_outputs_path,
        pipeline_result_path=args.pipeline_result_path,
        baseline_metrics_path=args.baseline_metrics_path,
        deployment_decision_path=args.deployment_decision_path,
        min_events=args.min_events,
        required_event_types=args.required_event_types,
        require_interpretation_output=args.require_interpretation_output,
        required_artifacts=args.required_artifacts,
        drift_tolerance=args.drift_tolerance,
        regression_tolerance=args.regression_tolerance,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))