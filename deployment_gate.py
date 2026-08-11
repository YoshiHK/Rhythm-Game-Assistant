from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # Used for parsing config/policy.yml
except ImportError:
    yaml = None  # Fallback handled safely in evaluation logic


@dataclass(frozen=True)
class GateOptions:
    require_repo_smoke: bool = True
    require_phase5_summary: bool = True
    require_offline_validation: bool = True
    require_runtime_index: bool = False
    require_runtime_integrity_pass: bool = True
    require_runtime_stage_completion: bool = True
    allow_zero_failed_cases_only: bool = True
    require_governed_policy: bool = True  # <--- Local storage policy check flag
    require_database_mutation_policy: bool = True

REQUIRED_RUNTIME_STAGES: Tuple[str, ...] = (
    "scan",
    "ingestion",
    "tips",
    "personalization",
    "localization",
    "song_recommendation",
    "recommendation",
)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ok(results: List[Dict[str, Any]], check: str, details: Optional[Dict[str, Any]] = None) -> None:
    results.append({"check": check, "passed": True, "details": details or {}})


def _fail(results: List[Dict[str, Any]], check: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
    results.append({"check": check, "passed": False, "reason": reason, "details": details or {}})


def _read_if_exists(path_value: Optional[str]) -> Optional[Path]:
    if not path_value:
        return None
    p = Path(path_value)
    return p if p.exists() else None
    
def _offline_validation_path_from_runtime_index(index: Dict[str, Any]) -> Optional[Path]:
    """
    Future-facing helper.

    Current runtime_index.json does not explicitly expose an offline validation
    report path, so this returns None unless a future schema adds one.

    Anticipated future locations:
    - last_run["offline_validation"]["output"]
    - last_run["validation"]["output"]
    """
    last_run = index.get("last_run") or {}

    for key in ("offline_validation", "validation"):
        node = last_run.get(key) or {}
        output = node.get("output")
        if output:
            p = Path(output)
            if p.exists():
                return p

    return None


def evaluate_repo_smoke(summary: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    failed = int(summary.get("failed", 0))
    passed = int(summary.get("passed", 0))
    if failed != 0:
        _fail(results, "repo_smoke", "repo_smoke_failed", {"passed": passed, "failed": failed})
    else:
        _ok(results, "repo_smoke", {"passed": passed, "failed": failed})


def evaluate_phase5_summary(summary: Dict[str, Any], results: List[Dict[str, Any]], opts: GateOptions) -> None:
    totals = summary.get("totals") or {}
    failed_cases = int(totals.get("failed_cases", 0))
    passed_cases = int(totals.get("passed_cases", 0))
    skipped_cases = int(totals.get("skipped_cases", 0))

    if opts.allow_zero_failed_cases_only and failed_cases != 0:
        _fail(
            results,
            "phase5_summary",
            "phase5_failed_cases_present",
            {"passed_cases": passed_cases, "failed_cases": failed_cases, "skipped_cases": skipped_cases},
        )
        return

    # Optional additional assertion: for every PASS feedback case, determinism should also PASS if present.
    bad_cases: List[Dict[str, Any]] = []
    for case in summary.get("cases") or []:
        if case.get("event_category") == "feedback" and case.get("overall_status") == "PASS":
            if case.get("determinism") not in {"PASS", "SKIP"}:
                bad_cases.append({
                    "case": case.get("case"),
                    "determinism": case.get("determinism"),
                })

    if bad_cases:
        _fail(results, "phase5_summary", "feedback_case_determinism_not_passed", {"cases": bad_cases})
    else:
        _ok(
            results,
            "phase5_summary",
            {"passed_cases": passed_cases, "failed_cases": failed_cases, "skipped_cases": skipped_cases},
        )


def evaluate_offline_validation(report: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    status = report.get("status")
    if status != "ok":
        _fail(results, "offline_validation", "offline_validation_not_ok", {"status": status, "errors": report.get("errors") or []})
        return

    _ok(
        results,
        "offline_validation",
        {
            "status": status,
            "imports_checked": len(report.get("imports") or []),
            "executions_logged": len(report.get("executions") or []),
        },
    )


# --------------------------------------------------
# Governed Local Storage Policy Evaluation Check
# --------------------------------------------------
def evaluate_governed_policy(policy_path: Optional[Path], results: List[Dict[str, Any]]) -> None:
    if not policy_path or not policy_path.exists():
        _fail(results, "governed_policy", "policy_config_missing", {"expected_path": "config/policy.yml"})
        return

    try:
        content = policy_path.read_text(encoding="utf-8")
        if yaml:
            policy = yaml.safe_load(content)
        else:
            # Simple fallback string parser if PyYAML isn't installed in the environment
            policy = {"allowed_artifact_phases": [line.strip().replace("- ", "").replace('"', "") for line in content.splitlines() if "-" in line]}

        allowed_phases = policy.get("allowed_artifact_phases") or []
        if "offline_local_storage" not in allowed_phases:
            _fail(
                results,
                "governed_policy",
                "offline_local_storage_not_whitelisted",
                {"allowed_phases": allowed_phases},
            )
            return

        _ok(
            results,
            "governed_policy",
            {
                "policy_file": str(policy_path),
                "whitelisted_offline_phase": True,
                "allowed_database_paths": policy.get("allowed_database_paths", []),
            },
        )
    except Exception as e:
        _fail(results, "governed_policy", "policy_parse_error", {"error": str(e)})

# --------------------------------------------------
# Database Mutation Policy Validation
# --------------------------------------------------
def evaluate_database_mutation_policy(
    mutation_plan_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:

    if not mutation_plan_path or not mutation_plan_path.exists():
        _fail(
            results,
            "database_mutation_policy",
            "database_mutation_plan_missing",
        )
        return

    try:
        plan = _load_json(mutation_plan_path)

        schema = plan.get("schema")

        if schema != "rga.database_mutation_plan.v1.0":
            _fail(
                results,
                "database_mutation_policy",
                "unsupported_mutation_plan_schema",
                {
                    "schema": schema,
                },
            )
            return

        runtime_baseline = plan.get(
            "runtime_baseline"
        )

        if not runtime_baseline:
            _fail(
                results,
                "database_mutation_policy",
                "runtime_baseline_missing",
            )
            return

        approval = plan.get(
            "approval"
        ) or {}

        policy = plan.get(
            "policy"
        ) or {}

        _ok(
            results,
            "database_mutation_policy",
            {
                "schema": schema,
                "runtime_baseline": runtime_baseline,
                "approval_required":
                    approval.get("required"),
                "policy_validation_required":
                    policy.get(
                        "validation_required"
                    ),
                "mutation_count":
                    len(
                        plan.get(
                            "proposed_mutations"
                        )
                        or []
                    ),
            },
        )

    except Exception as e:
        _fail(
            results,
            "database_mutation_policy",
            "database_mutation_plan_parse_error",
            {
                "error": str(e),
            },
        )

def evaluate_runtime_index(index: Dict[str, Any], results: List[Dict[str, Any]], opts: GateOptions) -> None:
    schema_version = index.get("schema_version")
    last_run = index.get("last_run") or {}
    last_status = last_run.get("status")

    if last_status != "completed":
        _fail(results, "runtime_index", "runtime_last_run_not_completed", {"status": last_status, "schema_version": schema_version})
        return

    if opts.require_runtime_stage_completion:
        incomplete: Dict[str, Any] = {}
        for stage in REQUIRED_RUNTIME_STAGES:
            stage_obj = last_run.get(stage) or {}
            if stage_obj.get("status") != "completed":
                incomplete[stage] = stage_obj.get("status")
        if incomplete:
            _fail(results, "runtime_index", "runtime_stage_not_completed", {"incomplete": incomplete, "schema_version": schema_version})
            return

    if opts.require_runtime_integrity_pass:
        integrity = ((last_run.get("integrity_check") or {}).get("details") or {})
        if integrity.get("passed") is not True:
            _fail(results, "runtime_index", "runtime_integrity_check_failed", {"integrity": integrity, "schema_version": schema_version})
            return

    _ok(
        results,
        "runtime_index",
        {
            "schema_version": schema_version,
            "run_id": last_run.get("run_id"),
            "report_date": last_run.get("report_date"),
            "mode": last_run.get("mode"),
        },
    )


def evaluate_gate(
    *,
    repo_smoke_path: Optional[Path],
    phase5_summary_path: Optional[Path],
    offline_validation_path: Optional[Path],
    runtime_index_path: Optional[Path],
    policy_config_path: Optional[Path] = None,
    mutation_plan_path: Optional[Path] = None,
    options: GateOptions,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    runtime_index_obj: Optional[Dict[str, Any]] = None

    # --------------------------------------------------
    # Load runtime index early if present
    # --------------------------------------------------
    if runtime_index_path and runtime_index_path.exists():
        runtime_index_obj = _load_json(runtime_index_path)

    # --------------------------------------------------
    # Repo smoke
    # --------------------------------------------------
    if options.require_repo_smoke:
        if not repo_smoke_path or not repo_smoke_path.exists():
            _fail(results, "repo_smoke", "repo_smoke_summary_missing")
        else:
            evaluate_repo_smoke(_load_json(repo_smoke_path), results)

    # --------------------------------------------------
    # Phase 5 summary
    # --------------------------------------------------
    if options.require_phase5_summary:
        if not phase5_summary_path or not phase5_summary_path.exists():
            _fail(results, "phase5_summary", "phase5_summary_missing")
        else:
            evaluate_phase5_summary(_load_json(phase5_summary_path), results, options)

    # --------------------------------------------------
    # Offline validation
    # --------------------------------------------------
    resolved_offline_validation = offline_validation_path

    # Future-facing fallback via runtime_index schema (if/when added)
    if resolved_offline_validation is None and runtime_index_obj is not None:
        resolved_offline_validation = _offline_validation_path_from_runtime_index(runtime_index_obj)

    if options.require_offline_validation:
        if not resolved_offline_validation or not resolved_offline_validation.exists():
            details = {}
            if runtime_index_obj is not None:
                details["runtime_index_present"] = True
                details["note"] = (
                    "runtime_index.json is present, but current schema did not provide "
                    "an offline validation output path"
                )
            _fail(results, "offline_validation", "offline_validation_report_missing", details)
        else:
            evaluate_offline_validation(_load_json(resolved_offline_validation), results)

    # --------------------------------------------------
    # Governed local storage policy check
    # --------------------------------------------------
    if options.require_governed_policy:
        evaluate_governed_policy(policy_config_path, results)
        
    # --------------------------------------------------
    # Database mutation policy
    # --------------------------------------------------
    if options.require_database_mutation_policy:

        evaluate_database_mutation_policy(
            mutation_plan_path,
            results,
        )        

    # --------------------------------------------------
    # Runtime index
    # --------------------------------------------------
    if options.require_runtime_index:
        if runtime_index_obj is None:
            _fail(results, "runtime_index", "runtime_index_missing")
        else:
            evaluate_runtime_index(runtime_index_obj, results, options)

    allowed = all(item.get("passed") is True for item in results)

    return {
        "allowed": allowed,
        "checks": results,
        "summary": {
            "passed": sum(1 for item in results if item.get("passed") is True),
            "failed": sum(1 for item in results if item.get("passed") is False),
            "required_runtime_index": options.require_runtime_index,
        },
    }


def _latest_json(patterns: Iterable[str]) -> Optional[Path]:
    candidates: List[Path] = []
    root = Path(".")
    for pattern in patterns:
        candidates.extend(root.rglob(pattern))
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime)
    return candidates[-1]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Repo-level deployment gate for RGA")
    p.add_argument("--repo-smoke-summary", default="", help="Path to repo_smoke_summary.json")
    p.add_argument("--phase5-summary", default="", help="Path to test_case_summary.json")
    p.add_argument("--offline-validation-report", default="", help="Path to offline_validation_report.json")
    p.add_argument("--runtime-index", default="", help="Path to runtime_index.json")
    p.add_argument("--policy-config", default="", help="Path to policy.yml or policy.yaml")
    p.add_argument("--database-mutation-plan", default="", help="Path to database_mutation_plan.json")
    p.add_argument("--require-runtime-index", action="store_true", help="Require runtime_index.json to be present and valid")
    p.add_argument("--output", default="deployment_gate_report.json", help="Output JSON report path")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    repo_smoke_path = _read_if_exists(args.repo_smoke_summary) or _latest_json(["repo_smoke_summary.json"])
    phase5_summary_path = _read_if_exists(args.phase5_summary) or _latest_json(["test_case_summary.json"])
    offline_validation_path = _read_if_exists(args.offline_validation_report) or _latest_json(["offline_validation_report.json"])
    runtime_index_path = _read_if_exists(args.runtime_index) or _latest_json(["runtime_index.json"])
    mutation_plan_path = _read_if_exists(args.database_mutation_plan) or _latest_json(["database_mutation_plan.json"])
    
    # Resolve policy path (checks config/policy.yml and config/policy.yaml automatically)
    policy_config_path = (
        _read_if_exists(args.policy_config)
        or _read_if_exists("config/policy.yml")
        or _read_if_exists("config/policy.yaml")
    )

    result = evaluate_gate(
        repo_smoke_path=repo_smoke_path,
        phase5_summary_path=phase5_summary_path,
        offline_validation_path=offline_validation_path,
        runtime_index_path=runtime_index_path,
        policy_config_path=policy_config_path,
        mutation_plan_path=mutation_plan_path,
        options=GateOptions(require_runtime_index=bool(args.require_runtime_index)),
    )

    out_path = Path(args.output)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if result["allowed"]:
        print("[DEPLOYMENT-GATE][OK] Deployment gate passed")
        print(f"[DEPLOYMENT-GATE][OK] Report: {out_path}")
        return 0

    print("[DEPLOYMENT-GATE][FAIL] Deployment gate failed")
    print(f"[DEPLOYMENT-GATE][FAIL] Report: {out_path}")
    for item in result["checks"]:
        if item.get("passed") is False:
            print(f"  - {item['check']}: {item.get('reason', 'unknown_reason')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

