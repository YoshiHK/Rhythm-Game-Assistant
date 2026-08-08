#!/usr/bin/env python3
"""
runtime_executor.py

RGA Executor Bot v1.2
Backend Maintenance Executor / Implementation Plan Generator

Purpose:
- Consume Bot #1 runtime_verifier_report.json / pre-audit report.
- Analyze root, derived, dependency, and governance failures.
- Generate an implementation / execution plan for Bot #1 plan-audit.
- Generate a repair DAG and rollback plan.
- Support dry_run_execute mode without mutating the repository.
- Support gated execute mode only after Bot #1 plan-audit and human approval.

Authority:
- Does not approve execution.
- Does not self-approve execution.
- Does not override governance.
- Does not mutate databases in this gated implementation.
- Does not delete source assets.
- Does not modify completed Phases 1-7.
- May create approved tooling, workflow, governance, and evidence artifacts.

Lifecycle:
Bot #1 pre-audit
    -> Bot #2 implementation plan generation
    -> Bot #1 plan-audit
    -> Human approval
    -> Bot #2 dry-run or gated execution
    -> Bot #1 post-audit

Phase Boundary Policy:
- Do not modify canonical_row format.
- Do not modify pattern/tag logic.
- Do not modify tips generation.
- Do not modify personalization.
- Do not modify localization.
- Do not modify recommendation logic.
- Additive tooling, verification, governance artifacts, and new ingestion paths are allowed.
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

EXECUTOR_SCHEMA = "rga.runtime_executor.report.v1.2"
EXECUTION_PLAN_SCHEMA = "rga.execution_plan.v1.2"
DRY_RUN_RESULT_SCHEMA = "rga.runtime_executor.dry_run_result.v1.1"
APPLY_EXECUTION_RESULT_SCHEMA = "rga.runtime_executor.apply_execution_result.v1.1"

DEFAULT_MODE = "plan"

SUPPORTED_MODES = [
    "plan",
    "dry_run_execute",
    "execute",
]

REQUIRED_APPROVAL_PHRASE = "APPROVE_RGA_EXECUTION"

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

PERMITTED_WRITE_ROOTS = [
    "tools/",
    "artifacts/",
    ".github/workflows/",
    "docs/",
]

PROTECTED_PATH_TOKENS = [
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Phase 4 - Personalization",
    "Phase 4.5 - Localization",
    "Phase 5 - Productionization",
    "Phase 6 - Hardening and Scaling",
    "Phase 7 - Games Recommendation",
    "canonical_row",
    "pattern_logic",
    "tips_generation",
    "personalization",
    "localization",
    "recommendation_logic",
]

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

    #
    # governance metadata
    #

    allowed_by_policy: bool = True

    governance_scope: str = "maintenance"

    phase_boundary_checked: bool = True


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
class DryRunAction:
    action_id: str
    source_change_id: str

    would_touch_files: List[str]
    would_create_files: List[str]
    would_modify_files: List[str]
    would_delete_files: List[str]

    allowed_by_policy: bool
    note: str


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

    #
    # governance
    #

    human_approval_required: bool = True

    approval_authority: str = "human"

    plan_audit_required: bool = True

    post_audit_required: bool = True

    #
    # lifecycle
    #

    lifecycle_sequence: List[str] = None

    #
    # completed phase protection
    #

    phase_boundary_validation: Dict[str, bool] = None


@dataclass
class ExecutorResult:
    schema: str

    generated_at: str

    mode: str

    proposal_only: bool

    dry_run: bool

    execution_authority: bool

    approval_authority: bool

    #
    # generated artifacts
    #

    plan: Dict[str, Any]

    dry_run_result: Dict[str, Any]

    apply_execution_result: Dict[str, Any]

    diagnostics: Dict[str, Any]

    #
    # lifecycle metadata
    #

    lifecycle_stage: str = ""

    audit_session_id: str = ""

    governance_model: Dict[str, Any] = None


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def read_json_file(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"JSON file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"JSON path is not a file: {path}"
        )

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    if not text.strip():
        raise ValueError(
            f"JSON file is empty: {path}"
        )

    data = json.loads(
        text
    )

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object at {path}, got {type(data).__name__}."
        )

    return data


def read_text_optional(
    path: Optional[Path],
) -> Optional[str]:

    if path is None:
        return None

    if not path.exists():
        return None

    if not path.is_file():
        return None

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def safe_json(
    value: Any,
) -> str:

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def write_json(
    data: Dict[str, Any],
    out_path: Path,
) -> None:

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        safe_json(
            data
        ),
        encoding="utf-8",
    )

    if (
        not out_path.exists()
        or out_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"JSON report was not written successfully: {out_path}"
        )


def write_markdown(
    data: Dict[str, Any],
    out_path: Path,
) -> None:

    lines: List[str] = []

    plan = data.get(
        "plan",
        {},
    )

    diagnostics = data.get(
        "diagnostics",
        {},
    )

    policy_result = diagnostics.get(
        "policy_result",
        {},
    )

    dry_run_result = data.get(
        "dry_run_result",
        {},
    )

    apply_execution_result = data.get(
        "apply_execution_result",
        {},
    )

    lines.append(
        "# RGA Executor Bot Report"
    )

    lines.append("")

    lines.append(
        f"Schema: `{data.get('schema')}`"
    )

    lines.append(
        f"Generated: `{data.get('generated_at')}`"
    )

    lines.append(
        f"Mode: `{data.get('mode')}`"
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    lines.append(
        "## Maintenance Lifecycle"
    )

    lines.append("")

    lifecycle = [
        "Bot #1 pre-audit",
        "Bot #2 implementation plan",
        "Bot #1 plan-audit",
        "Human approval",
        "Bot #2 dry-run / gated execution",
        "Bot #1 post-audit",
    ]

    for item in lifecycle:
        lines.append(
            f"- {item}"
        )

    lines.append("")

    # -------------------------------------------------------------------------
    # Authority
    # -------------------------------------------------------------------------

    lines.append(
        "## Authority"
    )

    lines.append("")

    lines.append(
        f"- Proposal only: `{data.get('proposal_only')}`"
    )

    lines.append(
        f"- Dry run: `{data.get('dry_run')}`"
    )

    lines.append(
        f"- Execution authority: `{data.get('execution_authority')}`"
    )

    lines.append(
        f"- Approval authority: `{data.get('approval_authority')}`"
    )

    lines.append(
        "- Self approval: `False`"
    )

    lines.append(
        "- Human approval required: `True`"
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Phase Boundary Policy
    # -------------------------------------------------------------------------

    lines.append(
        "## Phase Boundary Policy"
    )

    lines.append("")

    lines.append(
        "- Completed phases remain immutable."
    )

    lines.append(
        "- Canonical row format must not be modified."
    )

    lines.append(
        "- Pattern logic must not be modified."
    )

    lines.append(
        "- Tips generation must not be modified."
    )

    lines.append(
        "- Personalization and localization must not be modified."
    )

    lines.append(
        "- Recommendation logic must not be modified."
    )

    lines.append(
        "- Additive tooling, governance artifacts, verification layers, and non-intrusive ingestion paths are allowed."
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Policy Result
    # -------------------------------------------------------------------------

    lines.append(
        "## Policy Result"
    )

    lines.append("")

    lines.append(
        f"- Policy passed: `{policy_result.get('policy_passed')}`"
    )

    lines.append(
        f"- Violation count: `{len(policy_result.get('violations', []))}`"
    )

    lines.append("")

    if policy_result.get(
        "violations"
    ):

        lines.append(
            "### Policy Violations"
        )

        lines.append("")

        for item in policy_result.get(
            "violations",
            [],
        ):
            lines.append(
                f"- {item}"
            )

        lines.append("")

    # -------------------------------------------------------------------------
    # Target Root Failures
    # -------------------------------------------------------------------------

    lines.append(
        "## Target Root Failures"
    )

    lines.append("")

    target_root_failures = plan.get(
        "target_root_failures",
        [],
    )

    if target_root_failures:

        for item in target_root_failures:
            lines.append(
                f"- `{item}`"
            )

    else:

        lines.append(
            "- No target root failures declared."
        )

    lines.append("")

    # -------------------------------------------------------------------------
    # Proposed Changes
    # -------------------------------------------------------------------------

    lines.append(
        "## Proposed Changes"
    )

    lines.append("")

    proposed_changes = plan.get(
        "proposed_changes",
        [],
    )

    if proposed_changes:

        for item in proposed_changes:

            lines.append(
                f"### `{item.get('change_id')}`"
            )

            lines.append("")

            lines.append(
                f"- Type: `{item.get('change_type')}`"
            )

            lines.append(
                f"- Mutation level: `{item.get('mutation_level')}`"
            )

            lines.append(
                f"- Requires human approval: `{item.get('requires_human_approval')}`"
            )

            lines.append(
                f"- Target files: `{item.get('target_files')}`"
            )

            lines.append(
                f"- Purpose: {item.get('purpose')}"
            )

            lines.append("")

    else:

        lines.append(
            "- No proposed changes."
        )

        lines.append("")

    # -------------------------------------------------------------------------
    # Dry Run Execution
    # -------------------------------------------------------------------------

    lines.append(
        "## Dry Run Execution"
    )

    lines.append("")

    if dry_run_result:

        lines.append(
            f"- Dry run performed: `{dry_run_result.get('dry_run_performed')}`"
        )

        lines.append(
            f"- Would mutate repository: `{dry_run_result.get('would_mutate_repository')}`"
        )

        lines.append(
            f"- Would mutate databases: `{dry_run_result.get('would_mutate_databases')}`"
        )

        lines.append(
            f"- Would delete files: `{dry_run_result.get('would_delete_files')}`"
        )

        lines.append(
            f"- Action count: `{len(dry_run_result.get('actions', []))}`"
        )

        lines.append("")

        lines.append(
            "```json"
        )

        lines.append(
            safe_json(
                dry_run_result
            )
        )

        lines.append(
            "```"
        )

        lines.append("")

    else:

        lines.append(
            "Dry run was not requested."
        )

        lines.append("")

    # -------------------------------------------------------------------------
    # Apply Execution Result
    # -------------------------------------------------------------------------

    lines.append(
        "## Apply Execution Result"
    )

    lines.append("")

    if apply_execution_result:

        lines.append(
            f"- Execution attempted: `{apply_execution_result.get('execution_attempted')}`"
        )

        lines.append(
            f"- Execution performed: `{apply_execution_result.get('execution_performed')}`"
        )

        lines.append(
            f"- Approval loaded: `{apply_execution_result.get('approval_loaded')}`"
        )

        lines.append(
            f"- Written files: `{apply_execution_result.get('written_files')}`"
        )

        lines.append(
            f"- Policy violation count: `{len(apply_execution_result.get('policy_violations', []))}`"
        )

        lines.append("")

        lines.append(
            "```json"
        )

        lines.append(
            safe_json(
                apply_execution_result
            )
        )

        lines.append(
            "```"
        )

        lines.append("")

    else:

        lines.append(
            "Apply execution was not requested or did not run."
        )

        lines.append("")

    # -------------------------------------------------------------------------
    # Repair DAG
    # -------------------------------------------------------------------------

    lines.append(
        "## Repair DAG"
    )

    lines.append("")

    lines.append(
        "```json"
    )

    lines.append(
        safe_json(
            diagnostics.get(
                "repair_dag",
                {},
            )
        )
    )

    lines.append(
        "```"
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Full Execution Plan
    # -------------------------------------------------------------------------

    lines.append(
        "## Full Execution Plan"
    )

    lines.append("")

    lines.append(
        "```json"
    )

    lines.append(
        safe_json(
            plan
        )
    )

    lines.append(
        "```"
    )

    lines.append("")

    # -------------------------------------------------------------------------
    # Write Markdown
    # -------------------------------------------------------------------------

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    markdown_text = "\n".join(
        str(line)
        for line in lines
    )

    if not markdown_text.strip():

        markdown_text = "\n".join(
            [
                "# RGA Executor Bot Report",
                "",
                "## Empty Markdown Guard",
                "",
                "Markdown renderer produced no content. Fallback content was generated.",
                "",
            ]
        )

    out_path.write_text(
        markdown_text,
        encoding="utf-8",
    )

    if (
        not out_path.exists()
        or out_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"Markdown report was not written successfully: {out_path}"
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
        
        self.governance_verdict = (
            self.governance.get(
                "governance_verdict"
            )
        )

        self.runtime_verdict = (
            self.governance.get(
                "runtime_verdict"
            )
        )

        self.approval_authority = (
            self.governance.get(
                "approval_authority",
                "human",
            )
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

        self.diagnostics = {
            "executor_config_loaded": executor_config_text is not None,
            "executor_mode": mode,
            "governance_verdict": self.governance_verdict,
            "runtime_verdict": self.runtime_verdict,
            "approval_authority": self.approval_authority,

            "lifecycle_position": {
                "plan": "implementation_plan",
                "dry_run_execute": "dry_run_execute",
                "execute": "execute",
            }.get(
                mode,
                "unknown",
            ),

            "supported_modes": SUPPORTED_MODES,

            "governance_model": {
                "bot_1": [
                    "pre_audit",
                    "plan_audit",
                    "post_audit",
                ],
                "bot_2": [
                    "implementation_plan",
                    "dry_run_execute",
                    "execute",
                ],
                "human_approval_required": True,
            },
        }
        
        self.diagnostics["immutable_phase_policy"] = {
            "canonical_row": "protected",
            "pattern_logic": "protected",
            "tips_generation": "protected",
            "personalization": "protected",
            "localization": "protected",
            "recommendation_logic": "protected",
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
            "artifact_backbone_verdict": self.governance.get(
                "artifact_backbone_verdict"
            ),
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
                "requires_plan_audit": True,
                "requires_human_approval": True,
                "verification_sequence": [
                    "bot_1_plan_audit",
                    "human_approval",
                    "bot_2_execute",
                    "bot_1_post_audit",
                ],
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
                    change_id="dry_run_artifact_backbone_bootstrap_script",
                    change_type="dry_run_bootstrap_script",
                    target_files=[
                        "tools/artifact_backbone_bootstrap.py",
                    ],
                    purpose=(
                        "Dry-run creation of a non-destructive artifact backbone "
                        "bootstrap script. Dry run records the intended file only; "
                        "no file is written in dry_run_execute mode."
                    ),
                    mutation_level="dry_run_only",
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

        #
        # ----------------------------------------------------------
        # Root Failure First
        # ----------------------------------------------------------
        #

        for root_contract in target_root_failures:
            proposed_changes.extend(
                self.proposed_changes_for_root(
                    root_contract
                )
            )

        #
        # ----------------------------------------------------------
        # No Root Failure
        # ----------------------------------------------------------
        #

        if not proposed_changes:
            proposed_changes.append(
                ProposedChange(
                    change_id="no_root_failure_execution_required",
                    change_type="no_op_plan",
                    target_files=[],
                    purpose=(
                        "No root failures were detected. "
                        "No execution proposal is required."
                    ),
                    mutation_level="proposal_only",
                    requires_human_approval=True,
                )
            )

        #
        # ----------------------------------------------------------
        # Lifecycle / Mode Normalization
        #
        # Bot #2 implementation planning
        # Bot #2 dry-run execution
        # Bot #2 gated execution
        #
        # Execute mode never bypasses:
        #
        #   Bot #1 plan_audit
        #   Human approval
        #
        # ----------------------------------------------------------
        #

        execution_gate = {
            "mode": self.mode,
            "requires_plan_audit": True,
            "requires_human_approval": True,
            "approval_authority": "human",
            "self_approval_allowed": False,
        }

        self.diagnostics["execution_gate"] = execution_gate

        for change in proposed_changes:

            #
            # Planning Mode
            #

            if self.mode == "plan":

                if change.mutation_level not in {
                    "proposal_only",
                    "planning",
                }:
                    change.mutation_level = "proposal_only"

            #
            # Dry Run Mode
            #

            elif self.mode == "dry_run_execute":

                if change.change_id in {
                    "dry_run_artifact_backbone_bootstrap_script",
                    "generate_artifact_backbone_bootstrap_script_proposal",
                }:
                    change.mutation_level = "dry_run_only"

            #
            # Execute Mode
            #

            elif self.mode == "execute":

                if change.change_id in {
                    "dry_run_artifact_backbone_bootstrap_script",
                    "generate_artifact_backbone_bootstrap_script_proposal",
                }:
                    change.mutation_level = "execute_allowed"

                #
                # Guard completed phases
                #

                protected_tokens = [
                    "canonical_row",
                    "pattern_logic",
                    "tips_generation",
                    "personalization",
                    "localization",
                    "recommendation_logic",
                ]

                target_blob = " ".join(
                    change.target_files or []
                ).lower()

                if any(
                    token.lower() in target_blob
                    for token in protected_tokens
                ):
                    raise RuntimeError(
                        "Execute plan violates immutable phase policy: "
                        f"{change.change_id}"
                    )

            else:

                raise RuntimeError(
                    f"Unsupported executor mode: {self.mode}"
                )

        #
        # ----------------------------------------------------------
        # Verification Steps
        # ----------------------------------------------------------
        #

        verification_steps = [
            VerificationStep(
                step_id="generate_implementation_plan",
                description=(
                    "Generate implementation plan from "
                    "Bot #1 pre-audit findings."
                ),
                expected_evidence="execution_plan.json",
            ),           
            VerificationStep(
                step_id="run_bot_1_plan_audit",
                description=(
                    "Run Bot #1 in plan_audit mode "
                    "against this execution plan."
                ),
                expected_evidence=(
                    "runtime_verifier_report.json "
                    "containing plan_audit section."
                ),
            ),
            VerificationStep(
                step_id="obtain_human_approval",
                description=(
                    "Human reviews Bot #1 plan-audit "
                    "output and approves or rejects execution."
                ),
                expected_evidence="human_execution_approval.json",
            ),
            VerificationStep(
                step_id="run_bot_1_post_audit",
                description=(
                    "Run Bot #1 in post_audit mode "
                    "after approved execution is applied."
                ),
                expected_evidence="post_audit report",
            ),
        ]

        #
        # ----------------------------------------------------------
        # Rollback
        # ----------------------------------------------------------
        #

        rollback = RollbackPlan(
            available=True,
            strategy=(
                "Execution is governed by Bot #1 "
                "plan audit, human approval, "
                "and post-audit verification."
            ),
            rollback_steps=[
                "Restore generated tooling artifacts if required.",
                "Remove generated bootstrap scripts if rejected.",
                "Discard execution_plan.json if execution is canceled.",
                "Discard execution_plan.md if execution is canceled.",
                "Discard dry_run_result evidence if generated.",
                "Re-run Bot #1 pre_audit for a fresh baseline.",
                "Re-run Bot #1 post_audit after rollback.",
            ],
        )

        #
        # ----------------------------------------------------------
        # Execution Plan
        # ----------------------------------------------------------
        #

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

            approval_authority="human",

            plan_audit_required=True,

            post_audit_required=True,

            lifecycle_sequence=[
                "bot_1_pre_audit",
                "bot_2_implementation_plan",
                "bot_1_plan_audit",
                "human_approval",
                "bot_2_execute",
                "bot_1_post_audit",
            ],

            phase_boundary_validation={
                "phase_1_2_mutation_detected": False,
                "phase_3_mutation_detected": False,
                "phase_4_mutation_detected": False,
                "phase_4_5_mutation_detected": False,
                "phase_5_7_mutation_detected": False,
            },
        )

    def simulate_dry_run_execution(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        actions: List[DryRunAction] = []

        for change in plan.proposed_changes:
            would_create_files: List[str] = []
            would_modify_files: List[str] = []
            would_delete_files: List[str] = []

            if change.change_type in {
                "dry_run_bootstrap_script",
                "bootstrap_script_proposal",
            }:
                would_create_files = list(change.target_files)

            elif change.target_files:
                would_modify_files = list(change.target_files)

            allowed_by_policy = (
                not would_delete_files
                and change.mutation_level in {
                    "proposal_only",
                    "dry_run_only",
                }
            )

            actions.append(
                DryRunAction(
                    action_id=f"dry_run_{change.change_id}",
                    source_change_id=change.change_id,
                    would_touch_files=list(change.target_files),
                    would_create_files=would_create_files,
                    would_modify_files=would_modify_files,
                    would_delete_files=would_delete_files,
                    allowed_by_policy=allowed_by_policy,
                    note=(
                        "Dry run only. No repository, database, source asset, "
                        "or completed-phase mutation was performed."
                    ),
                )
            )

        result = {
            "schema": "rga.runtime_executor.dry_run_result.v1.0",
            "dry_run_performed": self.mode == "dry_run_execute",
            "would_mutate_repository": False,
            "would_mutate_databases": False,
            "would_delete_files": False,
            "completed_phase_mutation": False,
            "actions": [
                asdict(action)
                for action in actions
            ],
            "policy_note": (
                "dry_run_execute simulates intended execution effects only. "
                "It does not write files, mutate databases, delete assets, "
                "or modify completed phases."
            ),
        }

        self.diagnostics["dry_run_result"] = result
        return result
        
    def find_human_approval_artifact(
        self,
    ) -> Optional[Path]:
        """
        Search known locations for a human approval artifact and return the Path
        to the first match. Returns None when no artifact is found.
        """
        candidates = [
            Path("artifacts/human_execution_approval.json"),
            Path("human_execution_approval.json"),
        ]

        for path in candidates:
            if path.exists() and path.is_file():
                return path

        return None


    def load_human_approval(
        self,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        approval_path = self.find_human_approval_artifact()

        if approval_path is None:
            return (
                None,
                "Human execution approval artifact was not found.",
            )

        try:
            data = read_json_file(
                approval_path
            )

            return (
                data,
                None,
            )

        except Exception as exc:
            return (
                None,
                str(exc),
            )


    def approval_matches_plan(
        self,
        *,
        approval: Dict[str, Any],
        plan: ExecutionPlan,
    ) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        approved = approval.get(
            "approved",
            False,
        )

        approval_phrase = approval.get(
            "approval_phrase",
        )

        approved_execution_plan = approval.get(
            "approved_execution_plan",
            {},
        )

        if approved is not True:
            issues.append(
                "Approval artifact does not set approved=true."
            )

        if approval_phrase != "APPROVE_RGA_EXECUTION":
            issues.append(
                "Approval artifact does not contain the required approval phrase."
            )

        if not isinstance(
            approved_execution_plan,
            dict,
        ):
            issues.append(
                "approved_execution_plan must be an object."
            )

            return (
                False,
                issues,
            )

        approved_targets = sorted(
            approved_execution_plan.get(
                "target_root_failures",
                [],
            )
        )

        plan_targets = sorted(
            plan.target_root_failures
        )

        if approved_targets != plan_targets:
            issues.append(
                "Approval artifact target_root_failures do not match the generated execution plan."
            )

        approved_schema = approved_execution_plan.get(
            "schema",
        )

        if approved_schema != plan.schema:
            issues.append(
                "Approval artifact schema does not match execution plan schema."
            )

        return (
            not issues,
            issues,
        )


    def is_write_path_allowed(
        self,
        path_text: str,
    ) -> Tuple[bool, str]:
        normalized = (
            path_text
            .replace("\\", "/")
            .strip()
        )

        if not normalized:
            return (
                False,
                "Empty path is not allowed.",
            )

        prohibited_tokens = [
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4 - Personalization",
            "Phase 4.5 - Localization",
            "Phase 5 - Productionization",
            "Phase 6 - Hardening and Scaling",
            "Phase 7 - Games Recommendation",
            "canonical_row",
            "pattern_logic",
            "tips_generation",
            "personalization",
            "localization",
            "recommendation_logic",
        ]

        for token in prohibited_tokens:
            if token.lower() in normalized.lower():
                return (
                    False,
                    f"Path is inside or refers to protected scope: {token}",
                )

        allowed_prefixes = [
            "tools/",
            "artifacts/",
            ".github/workflows/",
            "docs/",
        ]

        normalized_lower = normalized.lower()

        if any(
            normalized_lower.startswith(
                prefix.lower()
            )
            for prefix in allowed_prefixes
        ):
            return (
                True,
                "Path is inside permitted execution scope.",
            )

        return (
            False,
            "Path is outside permitted execution scope.",
        )


    def render_artifact_backbone_bootstrap_script(
        self,
    ) -> str:
        return '''#!/usr/bin/env python3
"""
artifact_backbone_bootstrap.py

Generated by RGA Executor Bot.

Purpose:
- Prepare non-destructive artifact backbone bootstrap scaffolding.
- Does not run automatically.
- Does not delete source assets.
- Does not modify completed phases.

Backbone:
file_scan_inventory.db
    -> chart_assets.db
    -> chart_patterns.db
"""

from __future__ import annotations


def main() -> int:
    print("Artifact backbone bootstrap scaffold.")
    print("This script is intentionally non-destructive.")
    print("Manual review and Bot #1 verification are required before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


    def apply_execution(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        #
        # ----------------------------------------------------------
        # Gated Apply Execution
        #
        # This is intentionally narrow.
        #
        # It may create approved tooling/governance/evidence files.
        #
        # It must not:
        #   - mutate databases
        #   - delete source assets
        #   - modify completed phases
        #   - approve itself
        #   - override governance
        # ----------------------------------------------------------
        #

        approval, approval_error = self.load_human_approval()

        execution_result: Dict[str, Any] = {
            "schema":
                "rga.runtime_executor.apply_execution_result.v1.0",

            "execution_attempted":
                False,

            "execution_performed":
                False,

            "approval_loaded":
                approval is not None,

            "approval_error":
                approval_error,

            "written_files":
                [],

            "skipped_changes":
                [],

            "policy_violations":
                [],

            "db_mutation_performed":
                False,

            "source_asset_deletion_performed":
                False,

            "completed_phase_mutation_performed":
                False,

            "post_audit_required":
                True,
        }

        if self.mode != "execute":
            execution_result[
                "skipped_changes"
            ].append(
                "Execution skipped because mode is not execute."
            )

            return execution_result

        execution_result[
            "execution_attempted"
        ] = True

        if approval is None:
            execution_result[
                "policy_violations"
            ].append(
                approval_error
                or "Human approval artifact missing."
            )

            return execution_result

        approval_ok, approval_issues = (
            self.approval_matches_plan(
                approval=approval,
                plan=plan,
            )
        )

        if not approval_ok:
            execution_result[
                "policy_violations"
            ].extend(
                approval_issues
            )

            return execution_result

        for change in plan.proposed_changes:
            if change.mutation_level not in {
                "execute_allowed",
                "dry_run_only",
                "proposal_only",
            }:
                execution_result[
                    "policy_violations"
                ].append(
                    (
                        f"Change {change.change_id} has unsupported "
                        f"mutation_level={change.mutation_level}."
                    )
                )
                continue

            #
            # v1.0 gated execution only materializes the artifact
            # backbone bootstrap script. Other changes remain advisory.
            #

            if change.change_id in {
                "dry_run_artifact_backbone_bootstrap_script",
                "generate_artifact_backbone_bootstrap_script_proposal",
            }:
                for target in change.target_files:
                    allowed, reason = self.is_write_path_allowed(
                        target
                    )

                    if not allowed:
                        execution_result[
                            "policy_violations"
                        ].append(
                            (
                                f"Target path rejected for "
                                f"{change.change_id}: {target}; {reason}"
                            )
                        )
                        continue

                    target_path = Path(
                        target
                    )

                    target_path.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    target_path.write_text(
                        self.render_artifact_backbone_bootstrap_script(),
                        encoding="utf-8",
                    )

                    execution_result[
                        "written_files"
                    ].append(
                        str(
                            target_path
                        )
                    )

            else:
                execution_result[
                    "skipped_changes"
                ].append(
                    (
                        f"{change.change_id} is not executable in "
                        "the current gated execution implementation."
                    )
                )

        execution_result[
            "execution_performed"
        ] = bool(
            execution_result[
                "written_files"
            ]
        )

        return execution_result


    def enforce_policy(
        self,
        plan: ExecutionPlan,
        dry_run_result: Dict[str, Any],
        apply_execution_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        violations: List[str] = []

        if self.mode not in SUPPORTED_MODES:
            violations.append(
                f"Unsupported mode: {self.mode}"
            )

        if not plan.human_approval_required:
            violations.append(
                "Execution plan must require human approval."
            )

        allowed_mutation_levels = {
            "proposal_only",
        }

        if self.mode == "dry_run_execute":
            allowed_mutation_levels.add(
                "dry_run_only"
            )

        if self.mode == "execute":
            allowed_mutation_levels.update(
                {
                    "dry_run_only",
                    "execute_allowed",
                }
            )

        for change in plan.proposed_changes:
            if change.mutation_level not in allowed_mutation_levels:
                violations.append(
                    (
                        f"Change {change.change_id} uses disallowed "
                        f"mutation level: {change.mutation_level}."
                    )
                )

            if not change.requires_human_approval:
                violations.append(
                    f"Change {change.change_id} does not require human approval."
                )

        declared_absent = plan.forbidden_changes_declared_absent

        for operation in FORBIDDEN_OPERATIONS:
            if (
                operation in declared_absent
                and declared_absent[operation] is not True
            ):
                violations.append(
                    f"Forbidden operation not declared absent: {operation}"
                )

        if dry_run_result.get(
            "would_mutate_databases"
        ):
            violations.append(
                "dry_run_execute must not mutate databases."
            )

        if dry_run_result.get(
            "would_delete_files"
        ):
            violations.append(
                "dry_run_execute must not delete files."
            )

        if dry_run_result.get(
            "completed_phase_mutation"
        ):
            violations.append(
                "dry_run_execute must not modify completed phases."
            )        

        if self.mode == "execute":
            if not apply_execution_result:
                violations.append(
                    "execute mode requires apply_execution_result."
                )

            elif apply_execution_result.get(
                "policy_violations"
            ):
                violations.extend(
                    apply_execution_result.get(
                        "policy_violations",
                        [],
                    )
                )

            if apply_execution_result.get(
                "db_mutation_performed"
            ):
                violations.append(
                    "execute mode must not mutate databases in this gated implementation."
                )

            if apply_execution_result.get(
                "source_asset_deletion_performed"
            ):
                violations.append(
                    "execute mode must not delete source assets."
                )

            if apply_execution_result.get(
                "completed_phase_mutation_performed"
            ):
                violations.append(
                    "execute mode must not modify completed phases."
                )
                
            self.diagnostics["execution_gate"] = {
                "mode": self.mode,
                "requires_human_approval": True,
                "approval_phrase_required": True,
            }                

        policy_result = {
            "policy_passed":
                not violations,

            "violations":
                violations,

            "mode":
                self.mode,

            "proposal_only":
                self.mode == "plan",

            "dry_run":
                self.mode == "dry_run_execute",

            "execution_authority":
                self.mode == "execute",

            "approval_authority":
                False,

            "protected_completed_phases":
                PROTECTED_COMPLETED_PHASES,
        }

        self.diagnostics[
            "policy_result"
        ] = policy_result

        return policy_result


    def run_all(
        self,
    ) -> Dict[str, Any]:
        analysis = self.analyze_failures()

        repair_dag = self.build_repair_dag(
            analysis
        )

        plan = self.generate_execution_plan(
            analysis,
            repair_dag,
        )

        dry_run_result: Dict[str, Any] = {}

        if self.mode == "dry_run_execute":
            dry_run_result = self.simulate_dry_run_execution(
                plan
            )

        apply_execution_result: Dict[str, Any] = {}

        if self.mode == "execute":
            apply_execution_result = self.apply_execution(
                plan
            )

        policy_result = self.enforce_policy(
            plan,
            dry_run_result,
            apply_execution_result,
        )

        result = ExecutorResult(
            schema=EXECUTOR_SCHEMA,
            generated_at=datetime.now(
                timezone.utc
            ).replace(
                microsecond=0,
            ).isoformat(),
            mode=self.mode,
            proposal_only=self.mode == "plan",
            dry_run=self.mode == "dry_run_execute",
            execution_authority=self.mode == "execute",
            approval_authority=False,
            plan=asdict(plan),
            dry_run_result=dry_run_result,
            apply_execution_result=apply_execution_result,
            diagnostics={
                **self.diagnostics,
                "policy_result":
                    policy_result,
            },
        )

        return asdict(
            result
        )


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
        choices=SUPPORTED_MODES,
        default=DEFAULT_MODE,
        help=(
            "Executor mode. plan generates an execution plan only. "
            "dry_run_execute simulates execution without writing files."
        ),
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
            "proposal_only": args.mode == "plan",
            "dry_run": args.mode == "dry_run_execute",
            "execution_authority": False,
            "approval_authority": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "policy_result": {
                "policy_passed": False,
                "violations": [
                    "runtime_executor.py failed before execution plan or dry-run generation completed."
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
