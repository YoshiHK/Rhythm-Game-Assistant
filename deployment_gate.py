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
    # --------------------------------------------------
    # Lite Gate checks
    # --------------------------------------------------
    require_repo_smoke: bool = True
    require_phase5_summary: bool = True
    require_offline_validation: bool = True
    require_governed_policy: bool = True

    # --------------------------------------------------
    # Optional runtime index / execution evidence
    # --------------------------------------------------
    require_runtime_index: bool = False
    require_runtime_integrity_pass: bool = True
    require_runtime_stage_completion: bool = True

    # --------------------------------------------------
    # Phase 5 behavior
    # --------------------------------------------------
    allow_zero_failed_cases_only: bool = True
    require_feedback_case_determinism: bool = True

    # --------------------------------------------------
    # Stage 1–8 Governance Chain
    #
    # Default False because deployment-gate.yml is Lite.
    # deployment-governance-gate.yml should enable these
    # via --governance-mode or policy.yml.
    # --------------------------------------------------
    require_runtime_baseline: bool = False
    require_database_mutation_policy: bool = False
    require_persistence_contract: bool = False

    require_runtime_verification_contract: bool = False
    require_runtime_verification_acceptance: bool = False
    require_runtime_certification: bool = False
    require_path_a_operational: bool = False


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
    
def _load_policy(policy_path: Optional[Path]) -> Dict[str, Any]:
    if not policy_path or not policy_path.exists():
        return {}

    content = policy_path.read_text(encoding="utf-8")

    if yaml:
        loaded = yaml.safe_load(content)
        return loaded or {}

    # Minimal fallback if PyYAML is unavailable.
    return {}


def _bool_policy(
    policy: Dict[str, Any],
    key: str,
    default: bool,
) -> bool:
    value = policy.get(key, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

    return bool(value)

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

    # Guard feedback determinism checking with allow_zero_failed_cases_only / policy setting
    if opts.allow_zero_failed_cases_only:
        bad_cases: List[Dict[str, Any]] = []
        for case in summary.get("cases") or []:
            if case.get("event_category") == "feedback" and case.get("overall_status") == "PASS":
                if case.get("determinism") not in {"PASS", "SKIP"}:
                    bad_cases.append({
                        "case": case.get("case"),
                        "determinism": case.get("determinism"),
                    })
                    
    # Optional additional assertion:
    # for every PASS feedback case, determinism should also PASS if present.
    if not opts.require_feedback_case_determinism:
        _ok(
            results,
            "phase5_summary",
            {
                "passed_cases": passed_cases,
                "failed_cases": failed_cases,
                "skipped_cases": skipped_cases,
                "feedback_case_determinism_required": False,
            },
        )
        return                    

        if bad_cases:
            _fail(results, "phase5_summary", "feedback_case_determinism_not_passed", {"cases": bad_cases})
            return            

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
# Stage 1: Runtime Baseline Contract
# --------------------------------------------------
def evaluate_runtime_baseline_contract(
    runtime_baseline_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not runtime_baseline_path or not runtime_baseline_path.exists():
        _fail(
            results,
            "runtime_baseline",
            "runtime_baseline_missing",
        )
        return

    try:
        baseline = _load_json(runtime_baseline_path)

        schema = baseline.get("schema")
        if schema != "rga.runtime_baseline.v1.0":
            _fail(
                results,
                "runtime_baseline",
                "unsupported_runtime_baseline_schema",
                {"schema": schema},
            )
            return

        contract = baseline.get("contract") or {}
        governance = baseline.get("governance") or {}
        summary = baseline.get("summary") or {}

        _ok(
            results,
            "runtime_baseline",
            {
                "schema": schema,
                "baseline_ready": baseline.get("baseline_ready"),
                "bootstrap_only": baseline.get("bootstrap_only", False),
                "required_database_count": summary.get("required_database_count"),
                "existing_database_count": summary.get("existing_database_count"),
                "readable_database_count": summary.get("readable_database_count"),
                "total_records": summary.get("total_records"),
                "verification_required": contract.get("verification_required"),
                "deployment_gate_required": contract.get("deployment_gate_required"),
                "completed_phases_remain_immutable": governance.get(
                    "completed_phases_remain_immutable"
                ),
            },
        )

    except Exception as e:
        _fail(
            results,
            "runtime_baseline",
            "runtime_baseline_parse_error",
            {"error": str(e)},
        ) 
        
# --------------------------------------------------
# Stage 2-3: Database Mutation Policy Validation
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
                {"schema": schema},
            )
            return

        runtime_baseline = plan.get("runtime_baseline")
        if not runtime_baseline:
            _fail(
                results,
                "database_mutation_policy",
                "runtime_baseline_missing",
            )
            return

        approval = plan.get("approval") or {}
        policy = plan.get("policy") or {}
        proposed_mutations = plan.get("proposed_mutations") or []

        _ok(
            results,
            "database_mutation_policy",
            {
                "schema": schema,
                "runtime_baseline": runtime_baseline,
                "approval_required": approval.get("required"),
                "approval_state": approval.get("approved"),
                "policy_validation_required": policy.get("validation_required"),
                "policy_validated": policy.get("validated"),
                "mutation_count": len(proposed_mutations),
            },
        )

    except Exception as e:
        _fail(
            results,
            "database_mutation_policy",
            "database_mutation_plan_parse_error",
            {"error": str(e)},
        )
        
# --------------------------------------------------
# Stage 4: Persistence Contract
# --------------------------------------------------
def evaluate_persistence_contract(
    persistence_contract_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not persistence_contract_path or not persistence_contract_path.exists():
        _fail(
            results,
            "persistence_contract",
            "persistence_contract_missing",
        )
        return

    try:
        contract = _load_json(persistence_contract_path)

        schema = contract.get("schema")
        if schema != "rga.persistence_contract.v1.0":
            _fail(
                results,
                "persistence_contract",
                "unsupported_persistence_contract_schema",
                {"schema": schema},
            )
            return

        ownership = contract.get("ownership") or {}
        permissions = contract.get("permissions") or {}
        requirements = contract.get("runtime_requirements") or {}

        if permissions.get("executor_may_write_db") is not False:
            _fail(
                results,
                "persistence_contract",
                "executor_db_write_not_explicitly_forbidden",
                {"executor_may_write_db": permissions.get("executor_may_write_db")},
            )
            return

        if permissions.get("persistence_layer_owns_db_writes") is not True:
            _fail(
                results,
                "persistence_contract",
                "persistence_layer_not_declared_owner",
                {
                    "persistence_layer_owns_db_writes":
                        permissions.get("persistence_layer_owns_db_writes")
                },
            )
            return

        _ok(
            results,
            "persistence_contract",
            {
                "schema": schema,
                "planner": ownership.get("planner"),
                "executor": ownership.get("executor"),
                "approver": ownership.get("approver"),
                "policy_validator": ownership.get("policy_validator"),
                "executor_may_write_db": permissions.get("executor_may_write_db"),
                "persistence_layer_owns_db_writes": permissions.get(
                    "persistence_layer_owns_db_writes"
                ),
                "runtime_baseline_required": requirements.get(
                    "runtime_baseline_required"
                ),
                "mutation_validation_required": requirements.get(
                    "mutation_validation_required"
                ),
            },
        )

    except Exception as e:
        _fail(
            results,
            "persistence_contract",
            "persistence_contract_parse_error",
            {"error": str(e)},
        )
        
# --------------------------------------------------
# Stage 5: Runtime Verification Contract
# --------------------------------------------------
def evaluate_runtime_verification_contract(
    verification_contract_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not verification_contract_path or not verification_contract_path.exists():
        _fail(
            results,
            "runtime_verification_contract",
            "runtime_verification_contract_missing",
        )
        return

    try:
        contract = _load_json(verification_contract_path)

        schema = contract.get("schema")
        if schema != "rga.runtime_verification_contract.v1.0":
            _fail(
                results,
                "runtime_verification_contract",
                "unsupported_runtime_verification_contract_schema",
                {"schema": schema},
            )
            return

        scope = contract.get("verification_scope") or {}
        governance = contract.get("governance") or {}
        status = contract.get("status") or {}

        required_scope = [
            "inventory_coverage",
            "asset_coverage",
            "pattern_coverage",
            "hash_consistency",
            "runtime_surface",
            "artifact_integrity",
        ]

        missing_scope = [
            key for key in required_scope
            if scope.get(key) is not True
        ]

        if missing_scope:
            _fail(
                results,
                "runtime_verification_contract",
                "required_verification_scope_missing",
                {"missing_scope": missing_scope},
            )
            return

        _ok(
            results,
            "runtime_verification_contract",
            {
                "schema": schema,
                "verification_type": contract.get("verification_type"),
                "verification_scope": scope,
                "verification_performed": status.get("verification_performed"),
                "verification_passed": status.get("verification_passed"),
                "accepted": status.get("accepted"),
                "verification_is_global": governance.get("verification_is_global"),
                "completed_phases_immutable": governance.get(
                    "completed_phases_immutable"
                ),
            },
        )

    except Exception as e:
        _fail(
            results,
            "runtime_verification_contract",
            "runtime_verification_contract_parse_error",
            {"error": str(e)},
        )   

# --------------------------------------------------
# Stage 6: Runtime Verification Acceptance
# --------------------------------------------------
def evaluate_runtime_verification_acceptance(
    acceptance_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not acceptance_path or not acceptance_path.exists():
        _fail(
            results,
            "runtime_verification_acceptance",
            "runtime_verification_acceptance_missing",
        )
        return

    try:
        acceptance = _load_json(acceptance_path)

        schema = acceptance.get("schema")
        if schema != "rga.runtime_verification_acceptance.v1.0":
            _fail(
                results,
                "runtime_verification_acceptance",
                "unsupported_runtime_verification_acceptance_schema",
                {"schema": schema},
            )
            return

        accepted = bool(acceptance.get("accepted", False))

        if not accepted:
            _fail(
                results,
                "runtime_verification_acceptance",
                "runtime_verification_not_accepted",
                {
                    "accepted": accepted,
                    "reasons": acceptance.get("reasons") or [],
                },
            )
            return

        _ok(
            results,
            "runtime_verification_acceptance",
            {
                "schema": schema,
                "accepted": accepted,
                "source_contract": acceptance.get("source_contract"),
                "reasons": acceptance.get("reasons") or [],
            },
        )

    except Exception as e:
        _fail(
            results,
            "runtime_verification_acceptance",
            "runtime_verification_acceptance_parse_error",
            {"error": str(e)},
        )     

# --------------------------------------------------
# Stage 7: Runtime Certification
# --------------------------------------------------
def evaluate_runtime_certification(
    certification_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not certification_path or not certification_path.exists():
        _fail(
            results,
            "runtime_certification",
            "runtime_certification_missing",
        )
        return

    try:
        certification = _load_json(certification_path)

        schema = certification.get("schema")
        if schema != "rga.runtime_certification.v1.0":
            _fail(
                results,
                "runtime_certification",
                "unsupported_runtime_certification_schema",
                {"schema": schema},
            )
            return

        certification_node = certification.get("certification") or {}
        runtime_certified = bool(
            certification_node.get("runtime_certified", False)
        )

        if not runtime_certified:
            _fail(
                results,
                "runtime_certification",
                "runtime_not_certified",
                {"runtime_certified": runtime_certified},
            )
            return

        _ok(
            results,
            "runtime_certification",
            {
                "schema": schema,
                "runtime_certified": runtime_certified,
                "certification_scope": certification_node.get(
                    "certification_scope"
                ) or {},
            },
        )

    except Exception as e:
        _fail(
            results,
            "runtime_certification",
            "runtime_certification_parse_error",
            {"error": str(e)},
        ) 

# --------------------------------------------------
# Stage 8: Path A Operational Contract
# --------------------------------------------------
def evaluate_path_a_operational(
    path_a_operational_path: Optional[Path],
    results: List[Dict[str, Any]],
) -> None:
    if not path_a_operational_path or not path_a_operational_path.exists():
        _fail(
            results,
            "path_a_operational",
            "path_a_operational_contract_missing",
        )
        return

    try:
        contract = _load_json(path_a_operational_path)

        schema = contract.get("schema")
        if schema != "rga.path_a_operational.v1.0":
            _fail(
                results,
                "path_a_operational",
                "unsupported_path_a_operational_schema",
                {"schema": schema},
            )
            return

        state = contract.get("operational_state") or {}

        path_a_operational = bool(
            state.get("path_a_operational", False)
        )

        if not path_a_operational:
            _fail(
                results,
                "path_a_operational",
                "path_a_not_operational",
                {
                    "runtime_certified": state.get("runtime_certified"),
                    "path_a_operational": state.get("path_a_operational"),
                    "serving_ready": state.get("serving_ready"),
                },
            )
            return

        _ok(
            results,
            "path_a_operational",
            {
                "schema": schema,
                "runtime_certified": state.get("runtime_certified"),
                "path_a_operational": state.get("path_a_operational"),
                "serving_ready": state.get("serving_ready"),
            },
        )

    except Exception as e:
        _fail(
            results,
            "path_a_operational",
            "path_a_operational_parse_error",
            {"error": str(e)},
        )        
        
def build_gate_options(
    *,
    policy: Dict[str, Any],
    governance_mode: bool,
    require_runtime_index: bool,
    no_require_repo_smoke: bool,
    no_require_phase5_summary: bool,
    no_require_offline_validation: bool,
) -> GateOptions:
    validation_rules = policy.get("validation_rules") or {}

    # --------------------------------------------------
    # Lite defaults
    # --------------------------------------------------
    require_repo_smoke = validation_rules.get(
        "require_repo_smoke_summary",
        True,
    )

    require_offline_validation = validation_rules.get(
        "require_offline_validation_report",
        True,
    )

    require_feedback_case_determinism = validation_rules.get(
        "require_feedback_case_determinism",
        True,
    )

    require_phase5_summary = True

    # Explicit CLI overrides.
    if no_require_repo_smoke:
        require_repo_smoke = False

    if no_require_phase5_summary:
        require_phase5_summary = False

    if no_require_offline_validation:
        require_offline_validation = False

    # --------------------------------------------------
    # Governance mode enables Stage 1–8.
    #
    # policy.yml already declares these required flags.
    # --------------------------------------------------
    return GateOptions(
        require_repo_smoke=bool(require_repo_smoke),
        require_phase5_summary=bool(require_phase5_summary),
        require_offline_validation=bool(require_offline_validation),
        require_governed_policy=True,

        require_runtime_index=bool(require_runtime_index),
        require_runtime_integrity_pass=True,
        require_runtime_stage_completion=True,

        allow_zero_failed_cases_only=True,
        require_feedback_case_determinism=bool(
            require_feedback_case_determinism
        ),

        require_runtime_baseline=(
            governance_mode
            and _bool_policy(
                policy,
                "require_runtime_baseline",
                True,
            )
        ),

        require_database_mutation_policy=(
            governance_mode
            and _bool_policy(
                policy,
                "require_database_mutation_policy",
                True,
            )
        ),

        require_persistence_contract=(
            governance_mode
            and _bool_policy(
                policy,
                "require_persistence_contract",
                True,
            )
        ),

        require_runtime_verification_contract=(
            governance_mode
            and _bool_policy(
                policy,
                "require_runtime_verification_contract",
                True,
            )
        ),

        require_runtime_verification_acceptance=(
            governance_mode
            and _bool_policy(
                policy,
                "require_runtime_verification_acceptance",
                True,
            )
        ),

        require_runtime_certification=(
            governance_mode
            and _bool_policy(
                policy,
                "require_runtime_certification",
                True,
            )
        ),

        require_path_a_operational=(
            governance_mode
            and _bool_policy(
                policy,
                "require_path_a_operational",
                True,
            )
        ),
    )

def evaluate_runtime_index(
    index: Dict[str, Any],
    results: List[Dict[str, Any]],
    opts: GateOptions,
) -> None:
    schema_version = index.get("schema_version")

    last_run = index.get("last_run") or {}
    last_status = last_run.get("status")

    # --------------------------------------------------
    # Overall runtime completion
    # --------------------------------------------------

    if last_status != "completed":
        _fail(
            results,
            "runtime_index",
            "runtime_last_run_not_completed",
            {
                "status": last_status,
                "schema_version": schema_version,
            },
        )
        return

    # --------------------------------------------------
    # Runtime stage completion verification
    # --------------------------------------------------

    if opts.require_runtime_stage_completion:

        incomplete: Dict[str, Any] = {}

        for stage in opts.REQUIRED_RUNTIME_STAGES:

            stage_obj = last_run.get(stage) or {}

            if stage_obj.get("status") != "completed":
                incomplete[stage] = stage_obj.get("status")

        if incomplete:

            _fail(
                results,
                "runtime_index",
                "runtime_stage_not_completed",
                {
                    "incomplete": incomplete,
                    "schema_version": schema_version,
                },
            )

            return

    # --------------------------------------------------
    # Runtime integrity verification
    # --------------------------------------------------

    if opts.require_runtime_integrity_pass:

        integrity = (
            (
                last_run.get("integrity_check")
                or {}
            ).get("details")
            or {}
        )

        if integrity.get("passed") is not True:

            _fail(
                results,
                "runtime_index",
                "runtime_integrity_check_failed",
                {
                    "integrity": integrity,
                    "schema_version": schema_version,
                },
            )

            return

    # --------------------------------------------------
    # Runtime index accepted
    # --------------------------------------------------

    _ok(
        results,
        "runtime_index",
        {
            "schema_version": schema_version,
            "run_id": last_run.get("run_id"),
            "report_date": last_run.get("report_date"),
            "mode": last_run.get("mode"),
            "status": last_status,
        },
    )

def evaluate_gate(
    *,
    repo_smoke_path: Optional[Path],
    phase5_summary_path: Optional[Path],
    offline_validation_path: Optional[Path],
    runtime_index_path: Optional[Path],
    policy_config_path: Optional[Path] = None,

    # Stage 1
    runtime_baseline_path: Optional[Path] = None,

    # Stage 2-3
    mutation_plan_path: Optional[Path] = None,

    # Stage 4
    persistence_contract_path: Optional[Path] = None,

    # Stage 5
    runtime_verification_contract_path: Optional[Path] = None,

    # Stage 6
    runtime_verification_acceptance_path: Optional[Path] = None,

    # Stage 7
    runtime_certification_path: Optional[Path] = None,

    # Stage 8
    path_a_operational_path: Optional[Path] = None,

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
            _fail(
                results,
                "repo_smoke",
                "repo_smoke_summary_missing",
            )
        else:
            evaluate_repo_smoke(
                _load_json(repo_smoke_path),
                results,
            )

    # --------------------------------------------------
    # Phase 5 summary
    # --------------------------------------------------
    if options.require_phase5_summary:
        if not phase5_summary_path or not phase5_summary_path.exists():
            _fail(
                results,
                "phase5_summary",
                "phase5_summary_missing",
            )
        else:
            evaluate_phase5_summary(
                _load_json(phase5_summary_path),
                results,
                options,
            )

    # --------------------------------------------------
    # Offline validation
    # --------------------------------------------------
    resolved_offline_validation = offline_validation_path

    if (
        resolved_offline_validation is None
        and runtime_index_obj is not None
    ):
        resolved_offline_validation = (
            _offline_validation_path_from_runtime_index(
                runtime_index_obj
            )
        )

    if options.require_offline_validation:
        if (
            not resolved_offline_validation
            or not resolved_offline_validation.exists()
        ):
            details: Dict[str, Any] = {}

            if runtime_index_obj is not None:
                details["runtime_index_present"] = True
                details["note"] = (
                    "runtime_index.json is present, but current schema "
                    "did not provide an offline validation output path"
                )

            _fail(
                results,
                "offline_validation",
                "offline_validation_report_missing",
                details,
            )
        else:
            evaluate_offline_validation(
                _load_json(resolved_offline_validation),
                results,
            )

    # --------------------------------------------------
    # Governed policy
    # --------------------------------------------------
    if options.require_governed_policy:
        evaluate_governed_policy(
            policy_config_path,
            results,
        )

    # --------------------------------------------------
    # Stage 1: Runtime baseline
    # --------------------------------------------------
    if options.require_runtime_baseline:
        evaluate_runtime_baseline_contract(
            runtime_baseline_path,
            results,
        )

    # --------------------------------------------------
    # Stage 2-3: Database mutation policy
    # --------------------------------------------------
    if options.require_database_mutation_policy:
        evaluate_database_mutation_policy(
            mutation_plan_path,
            results,
        )

    # --------------------------------------------------
    # Stage 4: Persistence contract
    # --------------------------------------------------
    if options.require_persistence_contract:
        evaluate_persistence_contract(
            persistence_contract_path,
            results,
        )

    # --------------------------------------------------
    # Stage 5: Runtime verification contract
    # --------------------------------------------------
    if options.require_runtime_verification_contract:
        evaluate_runtime_verification_contract(
            runtime_verification_contract_path,
            results,
        )

    # --------------------------------------------------
    # Stage 6: Runtime verification acceptance
    # --------------------------------------------------
    if options.require_runtime_verification_acceptance:
        evaluate_runtime_verification_acceptance(
            runtime_verification_acceptance_path,
            results,
        )

    # --------------------------------------------------
    # Stage 7: Runtime certification
    # --------------------------------------------------
    if options.require_runtime_certification:
        evaluate_runtime_certification(
            runtime_certification_path,
            results,
        )

    # --------------------------------------------------
    # Stage 8: Path A operational
    # --------------------------------------------------
    if options.require_path_a_operational:
        evaluate_path_a_operational(
            path_a_operational_path,
            results,
        )

    # --------------------------------------------------
    # Runtime index
    #
    # Runtime index is execution evidence and should be
    # evaluated after governance contracts.
    # --------------------------------------------------
    if options.require_runtime_index:
        if runtime_index_obj is None:
            _fail(
                results,
                "runtime_index",
                "runtime_index_missing",
            )
        else:
            evaluate_runtime_index(
                runtime_index_obj,
                results,
                options,
            )

    allowed = all(
        item.get("passed") is True
        for item in results
    )



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
    p.add_argument("--policy-config", default="", help="Path to policy.yml or policy.yaml")
    p.add_argument("--governance-mode", action="store_true", help="Enable Stage 1-8 governance contract checks")
    p.add_argument("--runtime-index", default="", help="Path to runtime_index.json")    
    p.add_argument("--runtime-baseline", default="", help="Path to runtime_baseline.json")
    p.add_argument("--database-mutation-plan", default="", help="Path to database_mutation_plan.json")
    p.add_argument("--persistence-contract", default="", help="Path to persistence_contract.json")
    p.add_argument("--runtime-verification-contract", default="", help="Path to runtime_verification_contract.json")
    p.add_argument("--runtime-verification-acceptance", default="", help="Path to runtime_verification_acceptance.json")
    p.add_argument("--runtime-certification", default="", help="Path to runtime_certification.json")
    p.add_argument("--path-a-operational", default="", help="Path to path_a_operational.json")
    p.add_argument("--require-runtime-index", action="store_true", help="Require runtime_index.json to be present and valid")
    p.add_argument("--no-require-repo-smoke", action="store_true", help="Override policy to skip repo smoke summary requirement")
    p.add_argument("--no-require-phase5-summary", action="store_true", help="Override policy to skip Phase 5 summary requirement")
    p.add_argument("--no-require-offline-validation", action="store_true", help="Override policy to skip offline validation requirement")
    p.add_argument("--output", default="deployment_gate_report.json", help="Output JSON report path")
    return p

def main() -> int:
    args = build_arg_parser().parse_args()

    repo_smoke_path = (
        _read_if_exists(args.repo_smoke_summary)
        or _latest_json(["repo_smoke_summary.json"])
    )

    phase5_summary_path = (
        _read_if_exists(args.phase5_summary)
        or _latest_json(
            [
                "test_case_summary.json",
                "phase5_summary.json",
            ]
        )
    )

    offline_validation_path = (
        _read_if_exists(args.offline_validation_report)
        or _latest_json(["offline_validation_report.json"])
    )

    runtime_index_path = (
        _read_if_exists(
            getattr(
                args,
                "runtime_index",
                "",
            )
        )
        or _latest_json(
            ["runtime_index.json"]
        )
    )

    policy_config_path = (
        _read_if_exists(args.policy_config)
        or _read_if_exists("config/policy.yml")
        or _read_if_exists("config/policy.yaml")
    )

    policy = _load_policy(policy_config_path)

    runtime_baseline_path = (
        _read_if_exists(args.runtime_baseline)
        or _latest_json(["runtime_baseline.json"])
    )

    mutation_plan_path = (
        _read_if_exists(args.database_mutation_plan)
        or _latest_json(["database_mutation_plan.json"])
    )

    persistence_contract_path = (
        _read_if_exists(args.persistence_contract)
        or _latest_json(["persistence_contract.json"])
    )

    runtime_verification_contract_path = (
        _read_if_exists(args.runtime_verification_contract)
        or _latest_json(["runtime_verification_contract.json"])
    )

    runtime_verification_acceptance_path = (
        _read_if_exists(args.runtime_verification_acceptance)
        or _latest_json(["runtime_verification_acceptance.json"])
    )

    runtime_certification_path = (
        _read_if_exists(args.runtime_certification)
        or _latest_json(["runtime_certification.json"])
    )

    path_a_operational_path = (
        _read_if_exists(args.path_a_operational)
        or _latest_json(["path_a_operational.json"])
    )

    options = build_gate_options(
        policy=policy,
        governance_mode=bool(args.governance_mode),
        require_runtime_index=bool(args.require_runtime_index),
        no_require_repo_smoke=bool(args.no_require_repo_smoke),
        no_require_phase5_summary=bool(args.no_require_phase5_summary),
        no_require_offline_validation=bool(
            args.no_require_offline_validation
        ),
    )

    result = evaluate_gate(
        repo_smoke_path=repo_smoke_path,
        phase5_summary_path=phase5_summary_path,
        offline_validation_path=offline_validation_path,
        runtime_index_path=runtime_index_path,
        policy_config_path=policy_config_path,

        runtime_baseline_path=runtime_baseline_path,
        mutation_plan_path=mutation_plan_path,
        persistence_contract_path=persistence_contract_path,
        runtime_verification_contract_path=(
            runtime_verification_contract_path
        ),
        runtime_verification_acceptance_path=(
            runtime_verification_acceptance_path
        ),
        runtime_certification_path=runtime_certification_path,
        path_a_operational_path=path_a_operational_path,

        options=options,
    )

    out_path = Path(args.output)

    out_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if result["allowed"]:
        print("[DEPLOYMENT-GATE][OK] Deployment gate passed")
        print(f"[DEPLOYMENT-GATE][OK] Report: {out_path}")
        return 0

    print("[DEPLOYMENT-GATE][FAIL] Deployment gate failed")
    print(f"[DEPLOYMENT-GATE][FAIL] Report: {out_path}")

    for item in result["checks"]:
        if item.get("passed") is False:
            print(
                f"  - {item['check']}: "
                f"{item.get('reason', 'unknown_reason')}"
            )

    return 1

if __name__ == "__main__":
    raise SystemExit(main())

