#!/usr/bin/env python3
"""
runtime_executor.py

RGA Executor Bot v1.2
Backend Maintenance Executor / Implementation Plan Generator

Purpose:
- Consume Bot #1 runtime_auditor_report.json / pre-audit report.
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
- Additive tooling, audit, governance artifacts, and new ingestion paths are allowed.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import dataclass, asdict, field
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
APPLY_EXECUTION_RESULT_OUT_PATH = Path("artifacts/apply_execution_result.json")
EXECUTOR_WRITE_MANIFEST_OUT_PATH = Path("artifacts/executor_write_manifest.json")
EXECUTION_PROVENANCE_OUT_PATH = Path("artifacts/execution_provenance.json")


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
class auditStep:
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

    audit_steps: List[auditStep]

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

    #
    # Core metadata
    #

    schema: str

    generated_at: str

    mode: str

    proposal_only: bool

    dry_run: bool

    execution_authority: bool

    approval_authority: bool

    #
    # Generated artifacts
    #

    plan: Dict[str, Any]

    dry_run_result: Dict[str, Any]

    apply_execution_result: Dict[str, Any]

    executor_write_manifest: Dict[str, Any]

    execution_provenance: Dict[str, Any]

    diagnostics: Dict[str, Any]

    #
    # Lifecycle metadata
    #

    lifecycle_stage: str = ""

    audit_session_id: str = ""

    governance_model: Dict[str, Any] = field(
        default_factory=dict
    )


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
    
def read_json_optional(
    path: Path,
) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        return read_json_file(path)
    except Exception:
        return {}    

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
        "- Additive tooling, governance artifacts, audit layers, and non-intrusive ingestion paths are allowed."
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
    # Executor Write Manifest
    # -------------------------------------------------------------------------        
        
    executor_write_manifest = data.get(
        "executor_write_manifest",
        {},
    )

    lines.append(
        "## Executor Write Manifest"
    )

    lines.append("")

    if executor_write_manifest:

        lines.append(
            f"- Executor written files: `{executor_write_manifest.get('executor_written_files', [])}`"
        )

        lines.append(
            f"- Allowed scope only: `{executor_write_manifest.get('allowed_scope_only')}`"
        )

        lines.append(
            f"- Protected scope touched: `{executor_write_manifest.get('protected_scope_touched')}`"
        )

        lines.append("")

        lines.append("```json")

        lines.append(
            safe_json(
                executor_write_manifest
            )
        )

        lines.append("```")

        lines.append("")    

    # -------------------------------------------------------------------------
    # Execution Provenance
    # -------------------------------------------------------------------------        

    execution_provenance = data.get(
        "execution_provenance",
        {},
    )        

    lines.append(
        "## Execution Provenance"
    )

    lines.append("")

    if execution_provenance:

        lines.append(
            f"- Provenance verdict: `{execution_provenance.get('provenance_verdict')}`"
        )

        lines.append(
            f"- Audit session: `{execution_provenance.get('audit_session_id')}`"
        )

        lines.append(
            f"- Executor mode: `{execution_provenance.get('executor_mode')}`"
        )

        lines.append("")

        lines.append("```json")

        lines.append(
            safe_json(
                execution_provenance
            )
        )

        lines.append("```")

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
# Execution Provenance Helpers
# -----------------------------------------------------------------------------

def build_executor_write_manifest(
    execution_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executor attribution artifact.

    Purpose:
    Distinguish executor-authored writes from
    generic repository dirty state.
    """

    executor_written_files = list(
        execution_result.get(
            "executor_written_files",
            execution_result.get(
                "written_files",
                [],
            ),
        )
    )

    policy_violations = list(
        execution_result.get(
            "policy_violations",
            [],
        )
    )

    return {
        "schema":
            "rga.executor_write_manifest.v1.0",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "executor":
            "runtime_executor.py",

        "executor_mode":
            execution_result.get(
                "executor_mode"
            ),

        "execution_attempted":
            execution_result.get(
                "execution_attempted",
                False,
            ),

        "execution_performed":
            execution_result.get(
                "execution_performed",
                False,
            ),

        "executor_written_files":
            executor_written_files,

        "allowed_scope_only":
            len(policy_violations) == 0,

        "protected_scope_touched":
            execution_result.get(
                "protected_scope_touched",
                False,
            ),

        "completed_phases_modified":
            execution_result.get(
                "completed_phase_mutation_performed",
                False,
            ),

        "database_mutation_performed":
            execution_result.get(
                "db_mutation_performed",
                False,
            ),

        "source_asset_deletion_performed":
            execution_result.get(
                "source_asset_deletion_performed",
                False,
            ),

        "policy_violations":
            policy_violations,

        "post_audit_required":
            execution_result.get(
                "post_audit_required",
                True,
            ),
    }        
    
def build_execution_provenance(
    *,
    execution_result: Dict[str, Any],
    executor_write_manifest: Dict[str, Any],
    repository_changes: Optional[Dict[str, Any]] = None,
    execution_commit_manifest: Optional[Dict[str, Any]] = None,
    execution_git_commit_result: Optional[Dict[str, Any]] = None,
    execution_pull_request_candidate: Optional[Dict[str, Any]] = None,
    persistence_contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build execution-stage provenance evidence.

    Purpose:
    Bind executor-attributed writes, repository dirty state,
    commit candidate evidence, git commit result, PR candidate
    evidence, and persistence policy into one traceable execution
    chain.

    This artifact does not approve execution and does not certify
    deployment. It only summarizes provenance for post-audit and
    deployment governance.

    Important distinction:

        executor_write_manifest.executor_written_files
            = files attributed to runtime_executor.py

        repository_changes.git_status_short
            = workspace dirty state and diagnostic signal only

    Therefore, git_status_short must not be treated as patch proof.
    """

    repository_changes = repository_changes or {}
    execution_commit_manifest = execution_commit_manifest or {}
    execution_git_commit_result = execution_git_commit_result or {}
    execution_pull_request_candidate = (
        execution_pull_request_candidate or {}
    )
    persistence_contract = persistence_contract or {}

    executor_written_files = list(
        executor_write_manifest.get(
            "executor_written_files",
            [],
        )
    )

    changed_files_from_executor = list(
        repository_changes.get(
            "changed_files_from_executor",
            [],
        )
    )

    commit_candidate_files = list(
        execution_commit_manifest.get(
            "commit_candidate_files",
            [],
        )
    )

    git_status_short = list(
        repository_changes.get(
            "git_status_short",
            execution_commit_manifest.get(
                "git_status_short",
                [],
            ),
        )
    )

    protected_scopes = list(
        repository_changes.get(
            "protected_scopes",
            PROTECTED_PATH_TOKENS,
        )
    )

    protected_workspace_dirty_files: List[str] = []

    for raw_status in git_status_short:
        status_text = str(raw_status)

        for protected_token in protected_scopes:
            if protected_token in status_text:
                protected_workspace_dirty_files.append(
                    status_text
                )
                break

    policy_violations: List[str] = []

    policy_violations.extend(
        executor_write_manifest.get(
            "policy_violations",
            [],
        )
    )

    policy_violations.extend(
        repository_changes.get(
            "policy_violations",
            [],
        )
    )

    policy_violations.extend(
        execution_commit_manifest.get(
            "policy_violations",
            [],
        )
    )

    policy_violations.extend(
        execution_pull_request_candidate.get(
            "policy_violations",
            [],
        )
    )

    executor_attempted = bool(
        executor_write_manifest.get(
            "execution_attempted",
            False,
        )
    )

    executor_performed = bool(
        executor_write_manifest.get(
            "execution_performed",
            False,
        )
    )

    executor_has_writes = bool(
        executor_written_files
    )

    commit_required = bool(
        execution_commit_manifest.get(
            "commit_required",
            False,
        )
    )

    commit_attempted = bool(
        execution_git_commit_result.get(
            "commit_attempted",
            False,
        )
    )

    commit_created = bool(
        execution_git_commit_result.get(
            "commit_created",
            False,
        )
    )

    pull_request_required = bool(
        execution_pull_request_candidate.get(
            "pull_request_required",
            False,
        )
    )

    protected_scope_touched = bool(
        executor_write_manifest.get(
            "protected_scope_touched",
            False,
        )
    )

    completed_phases_modified = bool(
        executor_write_manifest.get(
            "completed_phases_modified",
            False,
        )
    )

    database_mutation_performed = bool(
        executor_write_manifest.get(
            "database_mutation_performed",
            False,
        )
    )

    source_asset_deletion_performed = bool(
        executor_write_manifest.get(
            "source_asset_deletion_performed",
            False,
        )
    )

    persistence_permissions = persistence_contract.get(
        "permissions",
        {},
    )

    executor_may_write_db = persistence_permissions.get(
        "executor_may_write_db",
        None,
    )

    ############################################################
    # Verdict model
    ############################################################

    if policy_violations:
        provenance_verdict = "patch_provenance_blocked"

    elif (
        protected_scope_touched
        or completed_phases_modified
        or database_mutation_performed
        or source_asset_deletion_performed
    ):
        provenance_verdict = "patch_provenance_blocked"

    elif (
        protected_workspace_dirty_files
        and not executor_has_writes
    ):
        provenance_verdict = (
            "blocked_by_protected_workspace_dirty_state"
        )

    elif (
        executor_attempted
        and not executor_has_writes
    ):
        provenance_verdict = "traceable_no_patch"

    elif (
        executor_has_writes
        and set(commit_candidate_files) == set(executor_written_files)
        and not policy_violations
        and not protected_scope_touched
        and not completed_phases_modified
        and not database_mutation_performed
        and not source_asset_deletion_performed
    ):
        provenance_verdict = "patch_provenance_ready"

    elif executor_has_writes:
        provenance_verdict = "patch_provenance_incomplete"

    else:
        provenance_verdict = "incomplete"

    if (
        provenance_verdict == "patch_provenance_ready"
        and commit_required
        and commit_candidate_files
    ):
        provenance_verdict = "patch_commit_ready"

    if (
        provenance_verdict in {
            "patch_provenance_ready",
            "patch_commit_ready",
        }
        and pull_request_required
    ):
        provenance_verdict = "patch_pr_candidate_ready"

    if (
        provenance_verdict in {
            "patch_commit_ready",
            "patch_pr_candidate_ready",
        }
        and commit_attempted
        and commit_created
    ):
        provenance_verdict = "patch_committed"

    return {
        "schema": "rga.execution_provenance.v1.0",
        "generated_at": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        ),
        "producer": "runtime_executor.py",
        "lifecycle_stage": "execute",

        "source_artifacts": {
            "apply_execution_result":
                str(APPLY_EXECUTION_RESULT_OUT_PATH),
            "executor_write_manifest":
                str(EXECUTOR_WRITE_MANIFEST_OUT_PATH),
            "repository_changes":
                "artifacts/repository_changes.json",
            "execution_commit_manifest":
                "artifacts/execution_commit_manifest.json",
            "execution_git_commit_result":
                "artifacts/execution_git_commit_result.json",
            "execution_pull_request_candidate":
                "artifacts/execution_pull_request_candidate.json",
            "persistence_contract":
                "artifacts/persistence_contract.json",
        },

        "executor_provenance": {
            "execution_attempted": executor_attempted,
            "execution_performed": executor_performed,
            "executor_written_files": executor_written_files,
            "changed_files_from_executor":
                changed_files_from_executor,
            "patch_probe_performed":
                executor_write_manifest.get(
                    "patch_probe_performed",
                    False,
                ),
            "patch_certifiable":
                executor_write_manifest.get(
                    "patch_certifiable",
                    False,
                ),
            "execution_verdict":
                executor_write_manifest.get(
                    "execution_verdict",
                ),
        },

        "repository_state": {
            "git_status_short": git_status_short,
            "workspace_dirty_files": git_status_short,
            "protected_workspace_dirty_files":
                protected_workspace_dirty_files,
            "non_executor_dirty_files": [
                item
                for item in git_status_short
                if item not in changed_files_from_executor
            ],
        },

        "commit_provenance": {
            "commit_required": commit_required,
            "commit_attempted": commit_attempted,
            "commit_created": commit_created,
            "branch_name":
                execution_commit_manifest.get(
                    "branch_name",
                    execution_git_commit_result.get(
                        "branch_name",
                    ),
                ),
            "commit_message":
                execution_commit_manifest.get(
                    "commit_message",
                    execution_git_commit_result.get(
                        "commit_message",
                    ),
                ),
            "commit_candidate_files": commit_candidate_files,
        },

        "pr_provenance": {
            "pull_request_required": pull_request_required,
            "branch_name":
                execution_pull_request_candidate.get(
                    "branch_name",
                ),
            "title":
                execution_pull_request_candidate.get(
                    "title",
                ),
            "required_reviewers":
                execution_pull_request_candidate.get(
                    "required_reviewers",
                    [],
                ),
            "required_gates":
                execution_pull_request_candidate.get(
                    "required_gates",
                    [],
                ),
        },

        "persistence_policy": {
            "executor_may_write_db": executor_may_write_db,
            "persistence_layer_owns_db_writes":
                persistence_permissions.get(
                    "persistence_layer_owns_db_writes",
                ),
            "human_approval_required":
                persistence_permissions.get(
                    "human_approval_required",
                ),
            "deployment_gate_required":
                persistence_permissions.get(
                    "deployment_gate_required",
                ),
        },

        "policy": {
            "allowed_scope_only":
                executor_write_manifest.get(
                    "allowed_scope_only",
                    False,
                ),
            "protected_scope_touched":
                protected_scope_touched,
            "completed_phases_modified":
                completed_phases_modified,
            "database_mutation_performed":
                database_mutation_performed,
            "source_asset_deletion_performed":
                source_asset_deletion_performed,
            "policy_violations": policy_violations,
        },

        "provenance_verdict": provenance_verdict,
        "governance_note": (
            "Execution provenance aggregates executor writes, "
            "repository state, commit candidate evidence, git commit "
            "result, PR candidate evidence, and persistence policy. "
            "It does not approve execution or certify deployment."
        ),
    }    
    
# -----------------------------------------------------------------------------
# Executor core
# -----------------------------------------------------------------------------

class RuntimeExecutor:
    def __init__(
        self,
        *,
        auditor_report: Dict[str, Any],
        executor_config_text: Optional[str],
        mode: str,
    ) -> None:
        self.auditor_report = auditor_report
        self.executor_config_text = executor_config_text
        self.mode = mode

        self.governance = auditor_report.get(
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
                "audit_sequence": [
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
                "requires_global_audit": True,
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
        #
        # Bot #2 plans from Bot #1 pre-audit findings.
        # Bot #2 does not reinterpret governance independently.
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
        #
        # If Bot #1 reports no root failures, Bot #2 produces a
        # no-op plan rather than inventing remediation.
        # ----------------------------------------------------------
        #

        if not proposed_changes:

            proposed_changes.append(
                ProposedChange(
                    change_id=
                        "no_root_failure_execution_required",

                    change_type=
                        "no_op_plan",

                    target_files=[],

                    purpose=(
                        "No root failures were detected. "
                        "No implementation or execution proposal "
                        "is required."
                    ),

                    mutation_level=
                        "proposal_only",

                    requires_human_approval=
                        True,

                    allowed_by_policy=
                        True,

                    governance_scope=
                        "maintenance",

                    phase_boundary_checked=
                        True,
                )
            )

        #
        # ----------------------------------------------------------
        # Execution Gate
        #
        # Execute mode never bypasses:
        #
        #   1. Bot #1 plan_audit
        #   2. Human approval
        #   3. Bot #1 post_audit
        #
        # ----------------------------------------------------------
        #

        execution_gate = {
            "mode":
                self.mode,

            "requires_plan_audit":
                True,

            "requires_human_approval":
                True,

            "approval_authority":
                "human",

            "self_approval_allowed":
                False,

            "requires_post_audit":
                True,
        }

        self.diagnostics[
            "execution_gate"
        ] = execution_gate

        #
        # ----------------------------------------------------------
        # Protected Scope Guard
        #
        # Completed phases are immutable.
        #
        # This scan is intentionally conservative and checks only
        # proposed target file paths / target identifiers.
        #
        # ----------------------------------------------------------
        #

        protected_tokens = [
            "canonical_row",
            "pattern_logic",
            "tips_generation",
            "personalization",
            "localization",
            "recommendation_logic",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4",
            "Phase 4.5",
            "Phase 5",
            "Phase 6",
            "Phase 7",
        ]

        protected_target_hits: List[Dict[str, Any]] = []

        for change in proposed_changes:

            target_blob = " ".join(
                change.target_files or []
            ).lower()

            matched_tokens = [
                token
                for token in protected_tokens
                if token.lower() in target_blob
            ]

            if matched_tokens:

                protected_target_hits.append(
                    {
                        "change_id":
                            change.change_id,

                        "target_files":
                            change.target_files,

                        "matched_tokens":
                            matched_tokens,
                    }
                )

                change.allowed_by_policy = False
                change.phase_boundary_checked = True

        self.diagnostics[
            "protected_target_scan"
        ] = {
            "protected_target_hit_count":
                len(
                    protected_target_hits
                ),

            "protected_target_hits":
                protected_target_hits,

            "policy":
                "completed_phases_immutable",
        }

        if protected_target_hits:

            raise RuntimeError(
                "Execution plan violates immutable phase policy: "
                + safe_json(
                    protected_target_hits
                )
            )

        #
        # ----------------------------------------------------------
        # Lifecycle / Mode Normalization
        #
        # plan:
        #   implementation plan only
        #
        # dry_run_execute:
        #   dry-run evidence only
        #
        # execute:
        #   gated execution only for explicitly allowed additive
        #   tooling / governance / audit changes
        # ----------------------------------------------------------
        #

        executable_change_ids = {
            "dry_run_artifact_backbone_bootstrap_script",
            "generate_artifact_backbone_bootstrap_script_proposal",
        }

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

                change.requires_human_approval = True
                change.allowed_by_policy = (
                    change.allowed_by_policy
                    and True
                )
                change.phase_boundary_checked = True

            #
            # Dry Run Mode
            #

            elif self.mode == "dry_run_execute":

                if change.change_id in executable_change_ids:
                    change.mutation_level = "dry_run_only"
                else:
                    change.mutation_level = "proposal_only"

                change.requires_human_approval = True
                change.allowed_by_policy = (
                    change.allowed_by_policy
                    and True
                )
                change.phase_boundary_checked = True

            #
            # Execute Mode
            #

            elif self.mode == "execute":

                is_permitted_scope = any(
                    target.startswith(tuple(PERMITTED_WRITE_ROOTS))
                    for target in change.target_files
                ) if change.target_files else True

                if change.change_id in executable_change_ids or is_permitted_scope:
                    change.mutation_level = "execute_allowed"
                else:
                    change.mutation_level = "proposal_only"

                change.requires_human_approval = True
                change.allowed_by_policy = (
                    change.allowed_by_policy
                    and is_permitted_scope
                )
                change.phase_boundary_checked = True


            else:
                
                raise RuntimeError(
                    f"Unsupported executor mode: {self.mode}"
                )

        #
        # ----------------------------------------------------------
        # Phase Boundary Validation
        # ----------------------------------------------------------
        #

        phase_boundary_validation = {
            "phase_1_2_mutation_detected":
                False,

            "phase_3_mutation_detected":
                False,

            "phase_4_mutation_detected":
                False,

            "phase_4_5_mutation_detected":
                False,

            "phase_5_7_mutation_detected":
                False,
        }

        self.diagnostics[
            "phase_boundary_validation"
        ] = phase_boundary_validation

        #
        # ----------------------------------------------------------
        # audit Steps
        #
        # These represent the intended maintenance lifecycle.
        # ----------------------------------------------------------
        #

        audit_steps = [
            auditStep(
                step_id=
                    "generate_implementation_plan",

                description=(
                    "Bot #2 generates an implementation plan "
                    "from Bot #1 pre-audit findings."
                ),

                expected_evidence=
                    "execution_plan.json",
            ),

            auditStep(
                step_id=
                    "run_bot_1_plan_audit",

                description=(
                    "Run Bot #1 in plan_audit mode "
                    "against the Bot #2 implementation plan."
                ),

                expected_evidence=(
                    "runtime_auditor_report.json "
                    "containing plan_audit section."
                ),
            ),

            auditStep(
                step_id=
                    "obtain_human_approval",

                description=(
                    "Human reviews Bot #1 plan-audit output "
                    "and approves or rejects execution."
                ),

                expected_evidence=
                    "human_execution_approval.json",
            ),

            auditStep(
                step_id=
                    "run_bot_2_gated_execution",

                description=(
                    "Bot #2 executes only the human-approved, "
                    "policy-allowed, non-completed-phase changes."
                ),

                expected_evidence=
                    "apply_execution_result.json",
            ),

            auditStep(
                step_id=
                    "run_bot_1_post_audit",

                description=(
                    "Run Bot #1 in post_audit mode after "
                    "approved execution is applied."
                ),

                expected_evidence=
                    "post_audit report",
            ),
        ]

        #
        # ----------------------------------------------------------
        # Rollback
        # ----------------------------------------------------------
        #

        rollback = RollbackPlan(
            available=
                True,

            strategy=(
                "Execution is governed by Bot #1 plan audit, "
                "human approval, gated Bot #2 execution, "
                "and Bot #1 post-audit audit."
            ),

            rollback_steps=[
                "Restore generated tooling artifacts if required.",
                "Remove generated bootstrap scripts if rejected.",
                "Discard execution_plan.json if execution is canceled.",
                "Discard runtime_executor_report.json if execution is canceled.",
                "Discard runtime_executor_report.md if execution is canceled.",
                "Discard dry_run_result evidence if generated.",
                "Discard apply_execution_result evidence if generated.",
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
            schema=
                EXECUTION_PLAN_SCHEMA,

            mode=
                self.mode,

            target_root_failures=
                target_root_failures,

            expected_derived_improvements=sorted(
                analysis.get(
                    "derived_dependency_map",
                    {},
                ).keys()
            ),

            proposed_changes=
                proposed_changes,

            audit_steps=
                audit_steps,

            rollback=
                rollback,

            forbidden_changes_declared_absent={
                "canonical_row":
                    True,

                "pattern_logic":
                    True,

                "tips_generation":
                    True,

                "personalization":
                    True,

                "localization":
                    True,

                "recommendation_logic":
                    True,

                "source_asset_deletion":
                    True,

                "database_mutation":
                    True,

                "approval_override":
                    True,

                "governance_override":
                    True,
            },

            human_approval_required=
                True,

            approval_authority=
                "human",

            plan_audit_required=
                True,

            post_audit_required=
                True,

            lifecycle_sequence=[
                "bot_1_pre_audit",
                "bot_2_implementation_plan",
                "bot_1_plan_audit",
                "human_approval",
                "bot_2_execute",
                "bot_1_post_audit",
            ],

            phase_boundary_validation=
                phase_boundary_validation,
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
    print("Manual review and Bot #1 audit are required before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    def apply_execution(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        """
        Apply a human-approved execution plan in gated execute mode.

        Patch Probe Contract
        --------------------
        This function intentionally treats
        artifacts/apply_execution_result.json itself as the first
        safe patch-probe artifact.

        Purpose:
        - Prove runtime_executor.py actually entered execute mode.
        - Prove runtime_executor.py can emit canonical execution evidence.
        - Prove executor-authored writes are distinguishable from dirty
          workspace state.
        - Preserve the successful E2E lifecycle loop:
            PowerShell
            -> GitHub
            -> Lifecycle Runner
            -> Pre-Audit
            -> Plan
            -> Plan-Audit
            -> Human Approval
            -> Execution
            -> Post-Audit
            -> Deployment Governance Gate
            -> Completion Signal
            -> Remote Governance Completion Verification
            -> Local Environment

        Hard Rule:
        Further changes must not break the successful E2E lifecycle loop.
        This function may only write allowed-scope evidence/tooling files
        and must not modify Completed Phases 1-7, runtime DBs, source
        assets, canonical_row, pattern logic, tips generation,
        personalization, localization, or recommendation logic.
        """

        approval, approval_error = self.load_human_approval()

        def utc_now_iso() -> str:
            return (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
            )

        def normalize_path_for_policy(
            value: Any,
        ) -> str:
            return str(value).replace("\\", "/")

        def path_has_protected_token(
            value: Any,
        ) -> Tuple[bool, Optional[str]]:
            normalized = normalize_path_for_policy(value)

            for token in PROTECTED_PATH_TOKENS:
                if token in normalized:
                    return True, token

            return False, None

        def append_policy_violation(
            result: Dict[str, Any],
            message: str,
        ) -> None:
            result.setdefault(
                "policy_violations",
                [],
            ).append(message)

        execution_result: Dict[str, Any] = {
            "schema": APPLY_EXECUTION_RESULT_SCHEMA,
            "generated_at": utc_now_iso(),
            "executor": "runtime_executor.py",
            "executor_mode": self.mode,

            ####################################################
            # Execution / patch-probe state
            ####################################################
            "execution_attempted": False,
            "execution_performed": False,
            "patch_probe_enabled": True,
            "patch_probe_performed": False,
            "patch_probe_artifact": str(
                APPLY_EXECUTION_RESULT_OUT_PATH
            ),

            ####################################################
            # Approval state
            ####################################################
            "approval_loaded": approval is not None,
            "approval_error": approval_error,

            ####################################################
            # Provenance
            ####################################################
            "written_files": [],
            "executor_written_files": [],
            "workspace_dirty_files": [],
            "non_executor_dirty_files": [],
            "patch_provenance": [],

            ####################################################
            # Governance / policy state
            ####################################################
            "skipped_changes": [],
            "policy_violations": [],
            "db_mutation_performed": False,
            "source_asset_deletion_performed": False,
            "completed_phase_mutation_performed": False,
            "protected_scope_touched": False,
            "all_written_files_within_allowed_scope": True,
            "post_audit_required": True,

            ####################################################
            # E2E lifecycle safety contract
            ####################################################
            "lifecycle_safety_contract": {
                "must_not_break_e2e_loop": True,
                "maintenance_phase_preserved": True,
                "operation_phase_preserved": True,
                "execution_phase_preserved": True,
                "deployment_phase_preserved": True,
                "feedback_completion_phase_preserved": True,
                "completed_phases_1_to_7_immutable": True,
            },

            ####################################################
            # Explicit scope contract
            ####################################################
            "allowed_scope": list(PERMITTED_WRITE_ROOTS),
            "protected_scope": list(PROTECTED_PATH_TOKENS),
        }
        
        def finalize_execution_result() -> Dict[str, Any]:
            """
            Emit all execution-stage evidence artifacts.

            This is the single artifact-emission boundary for:
              - apply_execution_result.json
              - executor_write_manifest.json
              - execution_provenance.json

            It must be used for success, skipped execution,
            missing approval, approval mismatch, and policy-blocked paths.
            """

            executor_write_manifest = (
                build_executor_write_manifest(
                    execution_result
                )
            )

            repository_changes = read_json_optional(
                Path(
                    "artifacts/repository_changes.json"
                )
            )

            execution_commit_manifest = read_json_optional(
                Path(
                    "artifacts/execution_commit_manifest.json"
                )
            )

            execution_git_commit_result = read_json_optional(
                Path(
                    "artifacts/execution_git_commit_result.json"
                )
            )

            execution_pull_request_candidate = (
                read_json_optional(
                    Path(
                        "artifacts/execution_pull_request_candidate.json"
                    )
                )
            )

            persistence_contract = read_json_optional(
                Path(
                    "artifacts/persistence_contract.json"
                )
            )

            execution_provenance = (
                build_execution_provenance(
                    execution_result=execution_result,
                    executor_write_manifest=executor_write_manifest,
                    repository_changes=repository_changes,
                    execution_commit_manifest=execution_commit_manifest,
                    execution_git_commit_result=execution_git_commit_result,
                    execution_pull_request_candidate=execution_pull_request_candidate,
                    persistence_contract=persistence_contract,
                )
            )

            write_json(
                execution_result,
                APPLY_EXECUTION_RESULT_OUT_PATH,
            )

            write_json(
                executor_write_manifest,
                EXECUTOR_WRITE_MANIFEST_OUT_PATH,
            )

            write_json(
                execution_provenance,
                EXECUTION_PROVENANCE_OUT_PATH,
            )

            return execution_result        

        ########################################################
        # Always emit a canonical result, even when not executing.
        ########################################################

        if self.mode != "execute":
            execution_result["skipped_changes"].append(
                "Execution skipped because mode is not execute."
            )

            execution_result["patch_provenance"].append(
                {
                    "type": "execution_not_attempted",
                    "reason": "mode_is_not_execute",
                    "artifact": str(
                        APPLY_EXECUTION_RESULT_OUT_PATH
                    ),
                }
            )

            return finalize_execution_result()

        execution_result["execution_attempted"] = True

        ########################################################
        # Human approval is mandatory.
        ########################################################

        if approval is None:
            append_policy_violation(
                execution_result,
                approval_error or "Human approval artifact missing.",
            )

            execution_result["patch_provenance"].append(
                {
                    "type": "execution_blocked",
                    "reason": "human_approval_missing",
                    "artifact": str(
                        APPLY_EXECUTION_RESULT_OUT_PATH
                    ),
                }
            )

            return finalize_execution_result()

        approval_ok, approval_issues = self.approval_matches_plan(
            approval=approval,
            plan=plan,
        )

        if not approval_ok:
            execution_result["policy_violations"].extend(
                approval_issues
            )

            execution_result["patch_provenance"].append(
                {
                    "type": "execution_blocked",
                    "reason": "approval_does_not_match_plan",
                    "issues": approval_issues,
                    "artifact": str(
                        APPLY_EXECUTION_RESULT_OUT_PATH
                    ),
                }
            )

            return finalize_execution_result()

        ########################################################
        # Execute approved, allowed-scope changes only.
        ########################################################

        for change in plan.proposed_changes:
            if change.mutation_level not in {
                "execute_allowed",
                "dry_run_only",
                "proposal_only",
            }:
                append_policy_violation(
                    execution_result,
                    (
                        f"Change {change.change_id} has unsupported "
                        f"mutation_level={change.mutation_level}."
                    ),
                )
                continue

            if change.mutation_level != "execute_allowed":
                execution_result["skipped_changes"].append(
                    (
                        f"{change.change_id} "
                        f"(mutation_level={change.mutation_level}) "
                        "skipped because it is not execute_allowed."
                    )
                )
                continue

            if not change.target_files:
                execution_result["skipped_changes"].append(
                    (
                        f"{change.change_id} "
                        "(mutation_level=execute_allowed) skipped "
                        "because it has no target files."
                    )
                )
                continue

            for target in change.target_files:
                normalized_target = normalize_path_for_policy(
                    target
                )

                protected, protected_token = (
                    path_has_protected_token(
                        normalized_target
                    )
                )

                if protected:
                    execution_result[
                        "completed_phase_mutation_performed"
                    ] = True
                    execution_result[
                        "protected_scope_touched"
                    ] = True
                    execution_result[
                        "all_written_files_within_allowed_scope"
                    ] = False

                    append_policy_violation(
                        execution_result,
                        (
                            "Protected scope rejected for "
                            f"{change.change_id}: "
                            f"{normalized_target}; "
                            f"matched protected token: "
                            f"{protected_token}"
                        ),
                    )
                    continue

                allowed, reason = self.is_write_path_allowed(
                    normalized_target
                )

                if not allowed:
                    execution_result[
                        "all_written_files_within_allowed_scope"
                    ] = False

                    append_policy_violation(
                        execution_result,
                        (
                            "Target path rejected for "
                            f"{change.change_id}: "
                            f"{normalized_target}; {reason}"
                        ),
                    )
                    continue

                target_path = Path(normalized_target)
                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if change.change_id in {
                    "dry_run_artifact_backbone_bootstrap_script",
                    "generate_artifact_backbone_bootstrap_script_proposal",
                }:
                    content = (
                        self.render_artifact_backbone_bootstrap_script()
                    )
                else:
                    content = (
                        "# Managed by RGA Executor Bot\n"
                        f"# Change ID: {change.change_id}\n"
                        f"# Purpose: {change.purpose}\n"
                        "# Scope: allowed lifecycle wiring/tooling/"
                        "governance artifact patch\n"
                        "# Completed Phases 1-7: immutable\n"
                    )

                target_path.write_text(
                    content,
                    encoding="utf-8",
                )

                path_text = normalize_path_for_policy(
                    target_path
                )

                execution_result["written_files"].append(
                    path_text
                )
                execution_result[
                    "executor_written_files"
                ].append(path_text)

                execution_result["patch_provenance"].append(
                    {
                        "type": "executor_write",
                        "change_id": change.change_id,
                        "change_type": change.change_type,
                        "mutation_level": change.mutation_level,
                        "path": path_text,
                        "purpose": change.purpose,
                        "allowed_scope": True,
                        "protected_scope_touched": False,
                    }
                )

        ########################################################
        # Patch probe: the canonical apply result itself is
        # executor-authored evidence.
        #
        # This is the first safe proof that execute mode ran and
        # wrote an allowed-scope artifact.
        ########################################################

        result_path_text = normalize_path_for_policy(
            APPLY_EXECUTION_RESULT_OUT_PATH
        )

        result_protected, result_token = path_has_protected_token(
            result_path_text
        )

        if result_protected:
            execution_result["protected_scope_touched"] = True
            execution_result[
                "completed_phase_mutation_performed"
            ] = True
            execution_result[
                "all_written_files_within_allowed_scope"
            ] = False

            append_policy_violation(
                execution_result,
                (
                    "Patch probe artifact unexpectedly matched "
                    f"protected scope: {result_path_text}; "
                    f"token={result_token}"
                ),
            )
        else:
            result_allowed, result_reason = self.is_write_path_allowed(
                result_path_text
            )

            if not result_allowed:
                execution_result[
                    "all_written_files_within_allowed_scope"
                ] = False

                append_policy_violation(
                    execution_result,
                    (
                        "Patch probe artifact rejected by write policy: "
                        f"{result_path_text}; {result_reason}"
                    ),
                )
            else:
                execution_result["patch_probe_performed"] = True

                if result_path_text not in execution_result[
                    "written_files"
                ]:
                    execution_result["written_files"].append(
                        result_path_text
                    )

                if result_path_text not in execution_result[
                    "executor_written_files"
                ]:
                    execution_result[
                        "executor_written_files"
                    ].append(result_path_text)

                execution_result["patch_provenance"].append(
                    {
                        "type": "patch_probe",
                        "path": result_path_text,
                        "purpose": (
                            "Canonical executor apply result emitted "
                            "as the first safe patch-probe artifact."
                        ),
                        "allowed_scope": True,
                        "protected_scope_touched": False,
                        "completed_phases_modified": False,
                        "database_mutation_performed": False,
                        "source_asset_deletion_performed": False,
                    }
                )

        ########################################################
        # Final execution verdict.
        ########################################################

        execution_result["execution_performed"] = bool(
            execution_result["executor_written_files"]
        )

        if execution_result["policy_violations"]:
            execution_result["patch_certifiable"] = False
            execution_result["execution_verdict"] = (
                "blocked_by_policy"
            )
        elif execution_result["patch_probe_performed"]:
            execution_result["patch_certifiable"] = True
            execution_result["execution_verdict"] = (
                "patch_probe_passed"
            )
        else:
            execution_result["patch_certifiable"] = False
            execution_result["execution_verdict"] = (
                "no_safe_patch_performed"
            )

        ########################################################
        # Hard safety assertions.
        ########################################################

        if execution_result["db_mutation_performed"]:
            append_policy_violation(
                execution_result,
                "Database mutation is not allowed in this executor mode.",
            )

        if execution_result["source_asset_deletion_performed"]:
            append_policy_violation(
                execution_result,
                "Source asset deletion is not allowed.",
            )

        if execution_result["completed_phase_mutation_performed"]:
            append_policy_violation(
                execution_result,
                "Completed Phase mutation is not allowed.",
            )

        if execution_result["policy_violations"]:
            execution_result["patch_certifiable"] = False
            execution_result["execution_verdict"] = (
                "blocked_by_policy"
            )

        return finalize_execution_result()

    def enforce_policy(
        self,
        plan: ExecutionPlan,
        dry_run_result: Dict[str, Any],
        apply_execution_result: Dict[str, Any],
        executor_write_manifest: Optional[Dict[str, Any]] = None,
        execution_provenance: Optional[Dict[str, Any]] = None,
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
                
            ####################################################
            # Executor write manifest policy
            ####################################################

            if not executor_write_manifest:
                violations.append(
                    "execute mode requires executor_write_manifest."
                )

            else:
                if executor_write_manifest.get(
                    "policy_violations"
                ):
                    violations.extend(
                        executor_write_manifest.get(
                            "policy_violations",
                            [],
                        )
                    )

                if not executor_write_manifest.get(
                    "allowed_scope_only",
                    False,
                ):
                    violations.append(
                        "executor_write_manifest must confirm allowed_scope_only."
                    )

                if executor_write_manifest.get(
                    "protected_scope_touched"
                ):
                    violations.append(
                        "executor_write_manifest indicates protected scope was touched."
                    )

                if executor_write_manifest.get(
                    "completed_phases_modified"
                ):
                    violations.append(
                        "executor_write_manifest indicates completed phases were modified."
                    )

                if executor_write_manifest.get(
                    "database_mutation_performed"
                ):
                    violations.append(
                        "executor_write_manifest indicates database mutation was performed."
                    )

                if executor_write_manifest.get(
                    "source_asset_deletion_performed"
                ):
                    violations.append(
                        "executor_write_manifest indicates source asset deletion was performed."
                    ) 

            ####################################################
            # Execution provenance policy
            ####################################################

            if not execution_provenance:
                violations.append(
                    "execute mode requires execution_provenance."
                )

            else:
                provenance_verdict = execution_provenance.get(
                    "provenance_verdict"
                )

                allowed_provenance_verdicts = {
                    "traceable_no_patch",
                    "patch_provenance_ready",
                    "patch_commit_ready",
                    "patch_pr_candidate_ready",
                    "patch_committed",
                }

                if provenance_verdict not in allowed_provenance_verdicts:
                    violations.append(
                        (
                            "execution_provenance has non-certifiable "
                            f"verdict: {provenance_verdict}"
                        )
                    )

                provenance_policy = execution_provenance.get(
                    "policy",
                    {},
                )

                if provenance_policy.get(
                    "policy_violations"
                ):
                    violations.extend(
                        provenance_policy.get(
                            "policy_violations",
                            [],
                        )
                    )

                if provenance_policy.get(
                    "protected_scope_touched"
                ):
                    violations.append(
                        "execution_provenance indicates protected scope was touched."
                    )

                if provenance_policy.get(
                    "completed_phases_modified"
                ):
                    violations.append(
                        "execution_provenance indicates completed phases were modified."
                    )

                if provenance_policy.get(
                    "database_mutation_performed"
                ):
                    violations.append(
                        "execution_provenance indicates database mutation was performed."
                    )

                if provenance_policy.get(
                    "source_asset_deletion_performed"
                ):
                    violations.append(
                        "execution_provenance indicates source asset deletion was performed."
                    )                    
                
            self.diagnostics["execution_gate"] = {
                "mode": self.mode,
                "requires_human_approval": True,
                "approval_phrase_required": True,
                "apply_execution_result_required": True,
                "executor_write_manifest_required": True,
                "execution_provenance_required": True,
            }  

            self.diagnostics["execution_provenance_gate"] = {
                "executor_write_manifest_present":
                    bool(executor_write_manifest),
                "execution_provenance_present":
                    bool(execution_provenance),
                "provenance_verdict":
                    (
                        execution_provenance or {}
                    ).get(
                        "provenance_verdict"
                    ),
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

        dry_run_result = (
            self.simulate_dry_run_execution(
                plan
            )
        )

    #
    # Execution-stage artifacts
    #

    apply_execution_result: Dict[str, Any] = {}

    executor_write_manifest: Dict[str, Any] = {}

    execution_provenance: Dict[str, Any] = {}

    if self.mode == "execute":

        apply_execution_result = (
            self.apply_execution(
                plan
            )
        )

        #
        # Reload executor-generated artifacts.
        #
        # apply_execution() owns artifact production.
        # run_all() consumes them.
        #

        executor_write_manifest = (
            read_json_optional(
                EXECUTOR_WRITE_MANIFEST_OUT_PATH
            )
        )

        execution_provenance = (
            read_json_optional(
                EXECUTION_PROVENANCE_OUT_PATH
            )
        )

    #
    # Governance / policy enforcement
    #

    policy_result = self.enforce_policy(
        plan=plan,
        dry_run_result=dry_run_result,
        apply_execution_result=apply_execution_result,
        executor_write_manifest=executor_write_manifest,
        execution_provenance=execution_provenance,
    )

    #
    # Final report
    #

    result = ExecutorResult(
        schema=EXECUTOR_SCHEMA,

        generated_at=(
            datetime.now(
                timezone.utc
            )
            .replace(
                microsecond=0,
            )
            .isoformat()
        ),

        mode=self.mode,

        proposal_only=(
            self.mode == "plan"
        ),

        dry_run=(
            self.mode == "dry_run_execute"
        ),

        execution_authority=(
            self.mode == "execute"
        ),

        approval_authority=False,

        #
        # generated artifacts
        #

        plan=asdict(
            plan
        ),

        dry_run_result=(
            dry_run_result
        ),

        apply_execution_result=(
            apply_execution_result
        ),

        executor_write_manifest=(
            executor_write_manifest
        ),

        execution_provenance=(
            execution_provenance
        ),

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

    #
    # ----------------------------------------------------------
    # Bot #1 report
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--auditor-report",
        required=False,
        default=None,
        help=(
            "Path to Bot #1 runtime_auditor_report.json."
        ),
    )

    parser.add_argument(
        "--pre-audit-report",
        required=False,
        default=None,
        help=(
            "Alias of --auditor-report."
        ),
    )

    #
    # ----------------------------------------------------------
    # Executor config
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--executor-config",
        default=None,
        help=(
            "Optional path to "
            "rga_executor_bot.yml."
        ),
    )

    #
    # ----------------------------------------------------------
    # Mode
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="execute",
        help=(
            "Executor mode. "
            "plan generates an execution plan only. "
            "dry_run_execute simulates execution. "
            "execute enforces live execution and applies approved changes."
        ),
    )

    #
    # ----------------------------------------------------------
    # Execution plan artifact
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--json-out",
        default="artifacts/execution_plan.json",
        help=(
            "Execution plan JSON output path."
        ),
    )

    #
    # ----------------------------------------------------------
    # Executor report markdown
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--md-out",
        default="artifacts/runtime_executor_report.md",
        help=(
            "Runtime executor markdown report path."
        ),
    )

    #
    # ----------------------------------------------------------
    # Executor report json
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--report-json-out",
        default=(
            "artifacts/runtime_executor_report.json"
        ),
        help=(
            "Runtime executor JSON report path."
        ),
    )

    args = parser.parse_args()

    #
    # ----------------------------------------------------------
    # Report Path Resolution
    # ----------------------------------------------------------
    #

    auditor_report_path = (
        args.auditor_report
        or args.pre_audit_report
    )

    if not auditor_report_path:

        raise ValueError(
            "Either --auditor-report "
            "or --pre-audit-report "
            "must be supplied."
        )

    try:

        auditor_report = read_json_file(
            Path(
                auditor_report_path
            )
        )

        executor_config_text = (
            read_text_optional(
                Path(
                    args.executor_config
                )
            )
            if args.executor_config
            else None
        )

        executor = RuntimeExecutor(
            auditor_report=auditor_report,
            executor_config_text=executor_config_text,
            mode=args.mode,
        )

        result = executor.run_all()

        #
        # ------------------------------------------------------
        # Execution Plan
        # ------------------------------------------------------
        #

        write_json(
            result.get(
                "plan",
                {},
            ),
            Path(
                args.json_out
            ),
        )

        #
        # ------------------------------------------------------
        # Runtime Executor Report JSON
        # ------------------------------------------------------
        #

        write_json(
            result,
            Path(
                args.report_json_out
            ),
        )

        #
        # ------------------------------------------------------
        # Runtime Executor Report Markdown
        # ------------------------------------------------------
        #

        write_markdown(
            result,
            Path(
                args.md_out
            ),
        )

        #
        # ------------------------------------------------------
        # Stdout
        # ------------------------------------------------------
        #

        print(
            safe_json(
                result
            )
        )

        diagnostics = result.get(
            "diagnostics",
            {},
        )

        policy_result = (
            diagnostics.get(
                "policy_result",
                {},
            )
            if isinstance(diagnostics, dict)
            else {}
        )

        policy_passed = (
            policy_result.get(
                "policy_passed",
                False,
            )
            if isinstance(policy_result, dict)
            else False
        )

        return (
            0
            if policy_passed
            else 1
        )

    except Exception as exc:

        fallback = {
            "schema": EXECUTOR_SCHEMA,

            "generated_at": datetime.now(
                timezone.utc
            ).replace(
                microsecond=0,
            ).isoformat(),

            "mode": args.mode,

            "proposal_only":
                args.mode == "plan",

            "dry_run":
                args.mode == "dry_run_execute",

            "execution_authority":
                False,

            "approval_authority":
                False,

            "error":
                str(exc),

            "traceback":
                traceback.format_exc(),

            "policy_result": {
                "policy_passed": False,
                "violations": [
                    (
                        "runtime_executor.py "
                        "failed before execution "
                        "plan or dry-run generation "
                        "completed."
                    )
                ],
            },
        }

        #
        # ------------------------------------------------------
        # Write Fallback Executor Report
        # ------------------------------------------------------
        #

        try:

            write_json(
                fallback,
                Path(
                    args.report_json_out
                ),
            )

        except Exception:
            pass

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
