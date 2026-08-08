#!/usr/bin/env python3
"""
runtime_executor.py

RGA Executor Bot v1.0
Backend Maintenance Executor / Execution Plan Generator

Purpose:
- Consume Bot #1 runtime_verifier_report.json.
- Analyze root, derived, dependency, and governance failures.
- Generate an execution_plan.json for Bot #1 plan-audit.
- Generate a repair DAG and rollback plan.
- Operate in proposal-only mode by default.

Authority:
- Does not approve execution.
- Does not apply execution.
- Does not mutate databases.
- Does not delete source assets.
- Does not modify completed Phases 1-7.

Workflow:
Bot #1 pre-audit
    -> Bot #2 execution plan generation
    -> Bot #1 plan-audit
    -> Human approval
    -> Bot #2 execution, future gated mode only
    -> Bot #1 post-audit
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXECUTOR_SCHEMA = "rga.runtime_executor.report.v1.0"
EXECUTION_PLAN_SCHEMA = "rga.execution_plan.v1.0"
DEFAULT_MODE = "plan"

FORBIDDEN_OPERATIONS = [
    "modify_canonical_row",
    "modify_pattern_logic",
    "modify_tip_generation",
    "modify_personalization",
    "modify_localization",
    "modify_recommendation_logic",
    "delete_source_assets",
    "approve_execution",
    "override_governance",
    "database_mutation",
]

PROTECTED_COMPLETED_PHASES = {
    "phase_1_2_chart_understanding_and_tips": "immutable",
    "phase_3_canonical_ingestion": "immutable",
    "phase_4_personalization": "immutable",
    "phase_4_5_localization": "immutable",
    "phase_5_7_recommendation_stack": "immutable",
}

ARTIFACT_BACKBONE_CHAIN = [
    "file_scan_inventory.db",
    "chart_assets.db",
    "chart_patterns.db",
]

ARTIFACT_DATABASE_ROOT_CONTRACT = "artifact_database_policy"
DELETION_ROOT_CONTRACT = "deletion_readiness"

ARTIFACT_DERIVED_CONTRACTS = [
    "artifact_relationships",
    "artifact_backbone_contract",
    "asset_coverage",
    "hash_integrity",
    "type_A_usability",
    "runtime_artifact_readiness",
]


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------

@dataclass
class ProposedChange:
    change_id: str
    change_type: str
    target_files: List[str]
    purpose: str
    mutation_level: str
    requires_human_approval: bool = True


@dataclass
class RollbackPlan:
    available: bool
    strategy: str
    rollback_steps: List[str]


@dataclass
class VerificationStep:
    step_id: str
    description: str
    expected_evidence: str


@dataclass
class ExecutionPlan:
    schema: str
    mode: str
    target_root_failures: List[str]
    expected_derived_improvements: List[str]
    proposed_changes: List[ProposedChange]
    verification_steps: List[VerificationStep]
    rollback: RollbackPlan
    forbidden_changes_declared_absent: Dict[str, bool]
    human_approval_required: bool = True


@dataclass
class ExecutorResult:
    schema: str
    generated_at: str
    mode: str
    proposal_only: bool
    execution_authority: bool
    approval_authority: bool
    plan: Dict[str, Any]
    diagnostics: Dict[str, Any]


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def read_json_file(path: Path) -> Dict[str, Any]:
    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object at {path}, got {type(data).__name__}."
        )

    return data


def read_text_optional(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None

    if not path.exists():
        return None

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def safe_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def write_json(data: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        safe_json(data),
        encoding="utf-8",
    )


def write_markdown(data: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []

    plan = data.get("plan", {})
    diagnostics = data.get("diagnostics", {})
    policy_result = diagnostics.get("policy_result", {})

    lines.append("# RGA Executor Bot Report")
    lines.append("")
    lines.append(f"Schema: `{data.get('schema')}`")
    lines.append(f"Generated: `{data.get('generated_at')}`")
    lines.append(f"Mode: `{data.get('mode')}`")
    lines.append("")

    lines.append("## Authority")
    lines.append("")
    lines.append(f"- Proposal only: `{data.get('proposal_only')}`")
    lines.append(f"- Execution authority: `{data.get('execution_authority')}`")
    lines.append(f"- Approval authority: `{data.get('approval_authority')}`")
    lines.append("")

    lines.append("## Policy Result")
    lines.append("")
    lines.append(f"- Policy passed: `{policy_result.get('policy_passed')}`")
    lines.append(f"- Violation count: `{len(policy_result.get('violations', []))}`")
    lines.append("")

    if policy_result.get("violations"):
        lines.append("### Policy Violations")
        lines.append("")
        for item in policy_result.get("violations", []):
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Target Root Failures")
    lines.append("")
    for item in plan.get("target_root_failures", []):
        lines.append(f"- `{item}`")
    lines.append("")

    lines.append("## Proposed Changes")
    lines.append("")
    for item in plan.get("proposed_changes", []):
        lines.append(f"### `{item.get('change_id')}`")
        lines.append("")
        lines.append(f"- Type: `{item.get('change_type')}`")
        lines.append(f"- Mutation level: `{item.get('mutation_level')}`")
        lines.append(f"- Requires human approval: `{item.get('requires_human_approval')}`")
        lines.append(f"- Purpose: {item.get('purpose')}")
        lines.append("")

    lines.append("## Repair DAG")
    lines.append("")
    lines.append("```json")
    lines.append(safe_json(diagnostics.get("repair_dag", {})))
    lines.append("```")
    lines.append("")

    lines.append("## Full Execution Plan")
    lines.append("")
    lines.append("```json")
    lines.append(safe_json(plan))
    lines.append("```")
    lines.append("")

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# -----------------------------------------------------------------------------
# Executor core
# -----------------------------------------------------------------------------

class RuntimeExecutor:
    def __init__(
        self,
        *,
        verifier_report: Dict[str, Any],
        executor_config_text: Optional[str],
        mode: str,
    ) -> None:
        self.verifier_report = verifier_report
        self.executor_config_text = executor_config_text
        self.mode = mode

        self.governance = verifier_report.get(
            "governance",
            {},
        )

        self.root_failures = self.governance.get(
            "root_failures",
            [],
        )

        self.derived_failures = self.governance.get(
            "derived_failures",
            [],
        )

        self.dependency_failures = self.governance.get(
            "dependency_failures",
            [],
        )

        self.governance_failures = self.governance.get(
            "governance_failures",
            [],
        )

        self.diagnostics: Dict[str, Any] = {
            "executor_config_loaded": executor_config_text is not None,
            "executor_mode": mode,
        }

    def analyze_failures(self) -> Dict[str, Any]:
        root_contracts = [
            item.get("contract_type")
            for item in self.root_failures
            if isinstance(item, dict)
            and item.get("contract_type")
        ]

        derived_dependency_map = {
            item.get("contract_type"): item.get("dependency_of")
            for item in self.derived_failures
            if isinstance(item, dict)
            and item.get("contract_type")
        }

        dependency_contracts = [
            item.get("contract_type")
            for item in self.dependency_failures
            if isinstance(item, dict)
            and item.get("contract_type")
        ]

        analysis = {
            "root_contracts": sorted(set(root_contracts)),
            "derived_dependency_map": derived_dependency_map,
            "dependency_contracts": sorted(set(dependency_contracts)),
            "root_failure_count": len(self.root_failures),
            "derived_failure_count": len(self.derived_failures),
            "dependency_failure_count": len(self.dependency_failures),
            "governance_failure_count": len(self.governance_failures),
            "governance_verdict": self.governance.get("governance_verdict"),
            "runtime_verdict": self.governance.get("runtime_verdict"),
            "artifact_backbone_verdict": self.governance.get("artifact_backbone_verdict"),
            "deletion_verdict": self.governance.get("deletion_verdict"),
        }

        self.diagnostics["failure_analysis"] = analysis
        return analysis

    def build_repair_dag(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        root_contracts = analysis.get(
            "root_contracts",
            [],
        )

        derived_dependency_map = analysis.get(
            "derived_dependency_map",
            {},
        )

        dag: Dict[str, Any] = {}

        for root in root_contracts:
            dag[root] = {
                "failure_class": "root",
                "repair_priority": 1,
                "derived_contracts": sorted(
                    [
                        child
                        for child, parent
                        in derived_dependency_map.items()
                        if parent == root
                    ]
                ),
            }

        if ARTIFACT_DATABASE_ROOT_CONTRACT in root_contracts:
            dag[ARTIFACT_DATABASE_ROOT_CONTRACT]["artifact_backbone_chain"] = (
                ARTIFACT_BACKBONE_CHAIN
            )

        if DELETION_ROOT_CONTRACT in root_contracts:
            dag[DELETION_ROOT_CONTRACT]["deletion_policy"] = {
                "default_deletion": "blocked",
                "requires_global_verification": True,
            }

        self.diagnostics["repair_dag"] = dag
        return dag

    def proposed_changes_for_root(
        self,
        root_contract: str,
    ) -> List[ProposedChange]:
        if root_contract == ARTIFACT_DATABASE_ROOT_CONTRACT:
            return [
                ProposedChange(
                    change_id="plan_artifact_backbone_restoration",
                    change_type="planning",
                    target_files=[],
                    purpose=(
                        "Generate artifact backbone restoration plan for "
                        "file_scan_inventory.db, chart_assets.db, and "
                        "chart_patterns.db."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                ),
                ProposedChange(
                    change_id="generate_artifact_backbone_bootstrap_script_proposal",
                    change_type="bootstrap_script_proposal",
                    target_files=[
                        "tools/artifact_backbone_bootstrap.py",
                    ],
                    purpose=(
                        "Propose a non-destructive bootstrap script for artifact "
                        "database creation. Script generation only; script execution "
                        "requires human approval and Bot #1 plan audit."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                ),
            ]

        if root_contract == "runtime_wiring":
            return [
                ProposedChange(
                    change_id="plan_runtime_wiring_review",
                    change_type="planning",
                    target_files=[],
                    purpose=(
                        "Review runtime wiring for games_recommender injection. "
                        "No recommendation logic changes are proposed."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                )
            ]

        if root_contract == DELETION_ROOT_CONTRACT:
            return [
                ProposedChange(
                    change_id="preserve_deletion_block",
                    change_type="governance_guard",
                    target_files=[],
                    purpose=(
                        "Keep source asset deletion blocked until artifact backbone, "
                        "coverage, hash consistency, Type A usability, and runtime DB "
                        "readiness pass."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                )
            ]

        return [
            ProposedChange(
                change_id=f"plan_{root_contract}_review",
                change_type="planning",
                target_files=[],
                purpose=(
                    f"Generate a root-failure-first remediation plan for {root_contract}."
                ),
                mutation_level="proposal_only",
                requires_human_approval=True,
            )
        ]

    def generate_execution_plan(
        self,
        analysis: Dict[str, Any],
        repair_dag: Dict[str, Any],
    ) -> ExecutionPlan:
        target_root_failures = sorted(
            analysis.get(
                "root_contracts",
                [],
            )
        )

        proposed_changes: List[ProposedChange] = []

        for root_contract in target_root_failures:
            proposed_changes.extend(
                self.proposed_changes_for_root(
                    root_contract
                )
            )

        if not proposed_changes:
            proposed_changes.append(
                ProposedChange(
                    change_id="no_root_failure_execution_required",
                    change_type="no_op_plan",
                    target_files=[],
                    purpose=(
                        "No root failures were detected. No execution proposal is required."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                )
            )

        verification_steps = [
            VerificationStep(
                step_id="run_bot_1_plan_audit",
                description=(
                    "Run Bot #1 in plan_audit mode against this execution plan."
                ),
                expected_evidence=(
                    "runtime_verifier_report.json containing plan_audit section."
                ),
            ),
            VerificationStep(
                step_id="obtain_human_approval",
                description=(
                    "Human reviews Bot #1 plan-audit output and approves or rejects execution."
                ),
                expected_evidence="explicit human approval artifact",
            ),
            VerificationStep(
                step_id="run_bot_1_post_audit",
                description=(
                    "Run Bot #1 in post_audit mode after approved execution is applied."
                ),
                expected_evidence="post_audit report",
            ),
        ]

        rollback = RollbackPlan(
            available=True,
            strategy="No repository mutation is performed in proposal_only mode.",
            rollback_steps=[
                "Discard generated execution_plan.json.",
                "Discard generated execution_plan.md.",
                "Re-run Bot #1 pre_audit if a fresh baseline is needed.",
            ],
        )

        return ExecutionPlan(
            schema=EXECUTION_PLAN_SCHEMA,
            mode=self.mode,
            target_root_failures=target_root_failures,
            expected_derived_improvements=sorted(
                analysis.get(
                    "derived_dependency_map",
                    {},
                ).keys()
            ),
            proposed_changes=proposed_changes,
            verification_steps=verification_steps,
            rollback=rollback,
            forbidden_changes_declared_absent={
                "canonical_row": True,
                "pattern_logic": True,
                "tips_generation": True,
                "personalization": True,
                "localization": True,
                "recommendation_logic": True,
                "source_asset_deletion": True,
                "database_mutation": True,
            },
            human_approval_required=True,
        )

    def enforce_policy(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        violations: List[str] = []

        if self.mode != "plan":
            violations.append(
                "Only proposal-only plan mode is enabled in runtime_executor.py v1.0."
            )

        if not plan.human_approval_required:
            violations.append(
                "Execution plan must require human approval."
            )

        for change in plan.proposed_changes:
            if change.mutation_level != "proposal_only":
                violations.append(
                    f"Change {change.change_id} is not proposal_only."
                )

            if not change.requires_human_approval:
                violations.append(
                    f"Change {change.change_id} does not require human approval."
                )

        declared_absent = plan.forbidden_changes_declared_absent

        for operation in FORBIDDEN_OPERATIONS:
            key = operation
            if key in declared_absent and declared_absent[key] is not True:
                violations.append(
                    f"Forbidden operation not declared absent: {operation}"
                )

        policy_result = {
            "policy_passed": not violations,
            "violations": violations,
            "mode": self.mode,
            "proposal_only": True,
            "execution_authority": False,
            "approval_authority": False,
            "protected_completed_phases": PROTECTED_COMPLETED_PHASES,
        }

        self.diagnostics["policy_result"] = policy_result
        return policy_result

    def run_all(self) -> Dict[str, Any]:
        analysis = self.analyze_failures()

        repair_dag = self.build_repair_dag(
            analysis
        )

        plan = self.generate_execution_plan(
            analysis,
            repair_dag,
        )

        policy_result = self.enforce_policy(
            plan
        )

        result = ExecutorResult(
            schema=EXECUTOR_SCHEMA,
            generated_at=datetime.now(
                timezone.utc
            ).replace(
                microsecond=0,
            ).isoformat(),
            mode=self.mode,
            proposal_only=True,
            execution_authority=False,
            approval_authority=False,
            plan=asdict(plan),
            diagnostics={
                **self.diagnostics,
                "policy_result": policy_result,
            },
        )

        return asdict(result)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        "RGA Runtime Executor"
    )

    parser.add_argument(
        "--verifier-report",
        required=True,
        help="Path to Bot #1 runtime_verifier_report.json.",
    )

    parser.add_argument(
        "--executor-config",
        default=None,
        help="Optional path to rga_executor_bot.yml.",
    )

    parser.add_argument(
        "--mode",
        choices=[
            "plan",
        ],
        default=DEFAULT_MODE,
        help="Executor mode. v1.0 supports proposal-only planning only.",
    )

    parser.add_argument(
        "--json-out",
        default="artifacts/execution_plan.json",
        help="Execution plan JSON output path.",
    )

    parser.add_argument(
        "--md-out",
        default="artifacts/execution_plan.md",
        help="Execution plan Markdown output path.",
    )

    args = parser.parse_args()

    try:
        verifier_report = read_json_file(
            Path(
                args.verifier_report
            )
        )

        executor_config_text = read_text_optional(
            Path(
                args.executor_config
            )
            if args.executor_config
            else None
        )

        executor = RuntimeExecutor(
            verifier_report=verifier_report,
            executor_config_text=executor_config_text,
            mode=args.mode,
        )

        result = executor.run_all()

        write_json(
            result,
            Path(
                args.json_out
            ),
        )

        write_markdown(
            result,
            Path(
                args.md_out
            ),
        )

        print(
            safe_json(
                result
            )
        )

        policy_passed = (
            result.get(
                "diagnostics",
                {},
            )
            .get(
                "policy_result",
                {},
            )
            .get(
                "policy_passed",
                False,
            )
        )

        return 0 if policy_passed else 1

    except Exception as exc:
        fallback = {
            "schema": EXECUTOR_SCHEMA,
            "generated_at": datetime.now(
                timezone.utc
            ).replace(
                microsecond=0,
            ).isoformat(),
            "mode": args.mode,
            "proposal_only": True,
            "execution_authority": False,
            "approval_authority": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "policy_result": {
                "policy_passed": False,
                "violations": [
                    "runtime_executor.py failed before execution plan generation completed."
                ],
            },
        }

        print(
            safe_json(
                fallback
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
