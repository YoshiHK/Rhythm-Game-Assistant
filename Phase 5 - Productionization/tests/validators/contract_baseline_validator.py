from __future__ import annotations

from typing import Any, Dict, List, Optional


def _fail(errors: List[str], msg: str):
    errors.append(msg)


def _check_required_fields(obj: Dict[str, Any], fields: List[str], prefix: str, errors: List[str]):
    for f in fields:
        if f not in obj:
            _fail(errors, f"{prefix}: missing field '{f}'")


def _check_any_shape(obj: Dict[str, Any], allowed_shapes: List[List[str]]) -> bool:
    for shape in allowed_shapes:
        if all(k in obj for k in shape):
            return True
    return False


def _get_nested(obj: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def validate_contract_baseline_bundle(
    *,
    events: Optional[List[Dict[str, Any]]],
    interpreted_outputs: Optional[List[Dict[str, Any]]],
    pipeline_result: Optional[Dict[str, Any]],
    contract_baseline: Dict[str, Any],
) -> Dict[str, Any]:

    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    # ------------------------------------------------------
    # Event batch contract
    # ------------------------------------------------------
    event_cfg = contract_baseline.get("event_batch_contract", {})
    if events is not None and isinstance(events, list):

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                _fail(errors, f"event[{i}] is not dict")
                continue

            # top-level
            _check_required_fields(
                ev,
                event_cfg.get("required_top_level_keys", []),
                f"event[{i}]",
                errors,
            )

            # context
            ctx = ev.get("context", {})
            if isinstance(ctx, dict):
                _check_required_fields(
                    ctx,
                    event_cfg.get("required_context_fields", []),
                    f"event[{i}].context",
                    errors,
                )

            # payload
            payload = ev.get("payload", {})
            if isinstance(payload, dict):
                _check_required_fields(
                    payload,
                    event_cfg.get("required_payload_fields", []),
                    f"event[{i}].payload",
                    errors,
                )

            # event_type constraint
            allowed = event_cfg.get("allowed_event_types")
            if isinstance(allowed, list) and ev.get("event_type") not in allowed:
                _fail(errors, f"event[{i}] invalid event_type: {ev.get('event_type')}")

    # ------------------------------------------------------
    # Interpretation contract
    # ------------------------------------------------------
    interp_cfg = contract_baseline.get("interpretation_contract", {})

    if interp_cfg.get("require_output", False):
        if not interpreted_outputs:
            _fail(errors, "interpretation outputs required but missing")

    if interpreted_outputs:
        for i, out in enumerate(interpreted_outputs):
            if not isinstance(out, dict):
                _fail(errors, f"interpreted_outputs[{i}] not dict")
                continue

            allowed_shapes = interp_cfg.get("allowed_output_shapes_any_of", [])
            if allowed_shapes:
                if not _check_any_shape(out, allowed_shapes):
                    _fail(errors, f"interpreted_outputs[{i}] does not match allowed shapes")

    # ------------------------------------------------------
    # Phase 5 loop contract
    # ------------------------------------------------------
    p5_cfg = contract_baseline.get("phase5_loop_contract", {})

    if isinstance(pipeline_result, dict):

        result_obj = pipeline_result.get("result", pipeline_result)

        paths = result_obj.get("paths", {})
        if p5_cfg.get("require_paths", True):
            if not isinstance(paths, dict):
                _fail(errors, "pipeline_result missing paths")

        required_artifacts = p5_cfg.get("required_artifacts", [])
        for k in required_artifacts:
            if k not in (paths or {}):
                _fail(errors, f"missing artifact path: {k}")

        if p5_cfg.get("require_metrics", True):
            evaluation = result_obj.get("evaluation")
            if not isinstance(evaluation, dict):
                _fail(errors, "missing evaluation section")
            else:
                metrics = evaluation.get("metrics")
                if not isinstance(metrics, dict):
                    _fail(errors, "missing evaluation.metrics")

    # ------------------------------------------------------
    # Semantic rules
    # ------------------------------------------------------
    rules = contract_baseline.get("semantic_rules", [])

    for rule in rules:
        name = rule.get("name", "unknown_rule")

        if "if" in rule and "then" in rule:
            cond = rule["if"]
            then = rule["then"]

            for ev in events or []:
                payload = ev.get("payload", {})
                ok = True
                for k, v in cond.items():
                    if payload.get(k) != v:
                        ok = False
                        break

                if ok:
                    if then.get("dismiss_reason_not_null"):
                        if not payload.get("dismiss_reason"):
                            _fail(errors, f"{name}: dismiss_reason required")

        if "assert" in rule:
            for ev in events or []:
                payload = ev.get("payload", {})

                if "duration_ms_min" in rule["assert"]:
                    if payload.get("duration_ms", 0) < rule["assert"]["duration_ms_min"]:
                        _fail(errors, f"{name}: duration_ms < 0")

                if "retry_count_min" in rule["assert"]:
                    if payload.get("retry_count", 0) < rule["assert"]["retry_count_min"]:
                        _fail(errors, f"{name}: retry_count < 0")

    return {
        "validator": "contract_baseline_validator.bundle",
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }