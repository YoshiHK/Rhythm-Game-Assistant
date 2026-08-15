from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"


def ensure_artifacts_dir() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, payload: Dict[str, Any]) -> None:
    ensure_artifacts_dir()
    target = ARTIFACTS / path if not str(path).startswith("artifacts/") else ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: str | Path) -> Dict[str, Any]:
    target = ARTIFACTS / path if not str(path).startswith("artifacts/") else ROOT / path
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def write_text(path: str | Path, content: str) -> None:
    ensure_artifacts_dir()
    target = ARTIFACTS / path if not str(path).startswith("artifacts/") else ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def load_text(path: str | Path) -> str:
    target = ARTIFACTS / path if not str(path).startswith("artifacts/") else ROOT / path
    if not target.exists():
        return ""
    return target.read_text(encoding="utf-8", errors="ignore")


def emit_execution_gate(mode: str, approval_path: str) -> None:
    ensure_artifacts_dir()
    status = "allowed"
    reason = "Mode accepted"
    if mode == "execute" and not os.path.exists(approval_path):
        status = "blocked"
        reason = "Approval artifact missing"
    write_json(
        "artifacts/execution_gate.json",
        {
            "schema": "rga.execution_gate.v1.0",
            "requested_mode": mode,
            "status": status,
            "reason": reason,
        },
    )


def emit_approval_verification() -> None:
    write_json(
        "artifacts/approval_verification.json",
        {
            "schema": "rga.approval_verification.v1.0",
            "artifact_present": (ROOT / "artifacts/human_execution_approval.json").exists(),
        },
    )


def emit_runtime_executor_summary() -> None:
    stderr_path = ROOT / "artifacts/runtime_executor_stderr.txt"
    stdout_path = ROOT / "artifacts/runtime_executor_stdout.txt"
    exit_code_path = ROOT / "artifacts/runtime_executor_exit_code.txt"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
    try:
        exit_code = int(exit_code_path.read_text(encoding="utf-8", errors="ignore").strip() or "0")
    except Exception:
        exit_code = None

    payload = {
        "schema": "rga.runtime_executor.stderr_summary.v1.0",
        "stderr_present": stderr_path.exists(),
        "stderr_empty": len(stderr_text.strip()) == 0,
        "stdout_present": stdout_path.exists(),
        "stdout_empty": len(stdout_text.strip()) == 0,
        "executor_exit_code": exit_code,
        "execution_failed": exit_code is not None and exit_code != 0,
        "error_marker_count": sum(1 for marker in ["Traceback", "Error", "Exception", "ModuleNotFoundError", "RuntimeError", "ValueError"] if marker in stderr_text),
        "warning_marker_count": sum(1 for marker in ["warning", "Warning", "WARN"] if marker in stderr_text),
        "error_markers": [marker for marker in ["Traceback", "Error", "Exception", "ModuleNotFoundError", "RuntimeError", "ValueError"] if marker in stderr_text],
        "warning_markers": [marker for marker in ["warning", "Warning", "WARN"] if marker in stderr_text],
        "interpretation": "stderr_empty_no_error_output" if len(stderr_text.strip()) == 0 else "stderr_contains_output",
    }
    write_json("artifacts/runtime_executor_stderr_summary.json", payload)


def emit_runtime_executor_fallback_report() -> None:
    stderr_path = ROOT / "artifacts/runtime_executor_stderr.txt"
    stdout_path = ROOT / "artifacts/runtime_executor_stdout.txt"
    exit_code_path = ROOT / "artifacts/runtime_executor_exit_code.txt"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
    try:
        exit_code = int(exit_code_path.read_text(encoding="utf-8", errors="ignore").strip() or "0")
    except Exception:
        exit_code = None

    payload = {
        "schema": "rga.runtime_executor.report.fallback.v1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": None,
        "proposal_only": None,
        "dry_run": None,
        "execution_authority": False,
        "approval_authority": False,
        "plan": {},
        "dry_run_result": {},
        "apply_execution_result": {},
        "diagnostics": {
            "fallback_report_generated": True,
            "executor_exit_code": exit_code,
            "stdout_present": stdout_path.exists(),
            "stderr_present": stderr_path.exists(),
            "stdout_empty": len(stdout_text.strip()) == 0,
            "stderr_empty": len(stderr_text.strip()) == 0,
            "policy_result": {
                "policy_passed": False,
                "violations": ["runtime_executor.py did not emit runtime_executor_report.json."],
            },
        },
    }
    write_json("artifacts/runtime_executor_report.json", payload)
    write_text(
        "artifacts/runtime_executor_report.md",
        """# RGA Runtime Executor Report

## Fallback Report

`runtime_executor.py` did not emit a non-empty Markdown report.

See:

- `runtime_executor_report.json`
- `runtime_executor_stdout.txt`
- `runtime_executor_stderr.txt`
- `runtime_executor_stderr_summary.json`
- `runtime_executor_exit_code.txt`
""",
    )


def emit_execution_plan_fingerprint() -> None:
    plan_path = ROOT / "artifacts/execution_plan.json"
    fingerprint = hashlib.sha256(plan_path.read_bytes()).hexdigest() if plan_path.exists() else None
    write_json(
        "artifacts/execution_plan_fingerprint.json",
        {
            "schema": "rga.execution_plan_fingerprint.v1.0",
            "execution_plan_present": plan_path.exists() and plan_path.is_file(),
            "sha256": fingerprint,
        },
    )


def emit_approval_matching() -> None:
    plan_path = ROOT / "artifacts/execution_plan.json"
    approval_path = ROOT / "artifacts/human_execution_approval.json"
    match = False
    if plan_path.exists() and approval_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approved_plan = approval.get("approved_execution_plan", {})
        match = approved_plan.get("schema") == plan.get("plan", {}).get("schema")
    write_json("artifacts/approval_artifact_matching.json", {"schema": "rga.approval_artifact_matching.v1.0", "approval_matches_plan": match})


def emit_scope_verification() -> None:
    write_json(
        "artifacts/execution_scope_verification.json",
        {
            "schema": "rga.execution_scope_verification.v1.0",
            "protected_scopes": ["canonical_row", "pattern_logic", "tips_generation", "personalization", "localization", "recommendation_logic"],
            "completed_phases_immutable": True,
        },
    )


def emit_policy_verification() -> None:
    write_json(
        "artifacts/execution_policy_verification.json",
        {
            "schema": "rga.execution_policy_verification.v1.0",
            "execution_authority": True,
            "approval_authority": False,
            "self_approval": False,
            "human_approval_required": True,
            "plan_audit_required": True,
            "post_audit_required": True,
        },
    )


def emit_apply_result() -> None:
    executor_report_file = ROOT / "artifacts/execution_plan.json"
    result = {}
    if executor_report_file.exists():
        try:
            executor_report = json.loads(executor_report_file.read_text(encoding="utf-8"))
            result = executor_report.get("apply_execution_result", {})
        except Exception as exc:
            result = {
                "schema": "rga.apply_execution_result.v1.0",
                "execution_attempted": False,
                "execution_performed": False,
                "written_files": [],
                "policy_violations": [f"Could not parse executor report: {exc}"],
                "post_audit_required": True,
            }
    if not result:
        result = {
            "schema": "rga.apply_execution_result.v1.0",
            "execution_attempted": False,
            "execution_performed": False,
            "written_files": [],
            "policy_violations": [],
            "post_audit_required": True,
            "note": "No apply_execution_result was emitted by runtime_executor.py.",
        }
    write_json("artifacts/apply_execution_result.json", result)


def emit_repository_changes(mode: str) -> None:
    apply_result_file = ROOT / "artifacts/apply_execution_result.json"
    repository_changes_applied = False
    changed_files: List[str] = []
    written_files: List[str] = []
    notes: List[str] = []
    policy_violations: List[str] = []
    if apply_result_file.exists():
        try:
            result = json.loads(apply_result_file.read_text(encoding="utf-8"))
            written_files = result.get("written_files", [])
            policy_violations = result.get("policy_violations", [])
        except Exception as exc:
            notes.append(f"Could not parse apply_execution_result.json: {exc}")
    else:
        notes.append("apply_execution_result.json not found.")

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
        "Phase 4 - Personalization",
        "Phase 4.5 - Localization",
        "Phase 5 - Productionization",
        "Phase 6 - Hardening and Scaling",
        "Phase 7 - Games Recommendation",
    ]
    allowed_roots = ["tools/", "artifacts/", ".github/workflows/", "docs/"]
    for item in written_files:
        normalized = str(item).replace("\\", "/")
        if any(token.lower() in normalized.lower() for token in protected_tokens):
            policy_violations.append(f"Protected scope change rejected: {normalized}")
            continue
        if not any(normalized.startswith(prefix) for prefix in allowed_roots):
            policy_violations.append(f"Change outside allowed roots rejected: {normalized}")
            continue
        changed_files.append(normalized)

    try:
        proc = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
        git_status_short = proc.stdout.splitlines()
    except Exception as exc:
        git_status_short = []
        notes.append(f"Could not inspect git status: {exc}")
    repository_changes_applied = bool(changed_files or git_status_short)
    write_json(
        "artifacts/repository_changes.json",
        {
            "schema": "rga.repository_changes.v1.1",
            "executor_mode": mode,
            "repository_changes_applied": repository_changes_applied,
            "changed_files_from_executor": changed_files,
            "git_status_short": git_status_short,
            "policy_violations": policy_violations,
            "notes": notes,
            "allowed_scope": allowed_roots,
            "protected_scopes": protected_tokens,
            "completed_phases_immutable": True,
            "governance_note": "Repository change evidence is derived from runtime_executor outputs and git status. This step does not approve changes.",
        },
    )


def emit_commit_manifest() -> None:
    repository_changes = ROOT / "artifacts/repository_changes.json"
    changed_files: List[str] = []
    git_status_short: List[str] = []
    policy_violations: List[str] = []
    if repository_changes.exists():
        data = json.loads(repository_changes.read_text(encoding="utf-8"))
        changed_files = data.get("changed_files_from_executor", [])
        git_status_short = data.get("git_status_short", [])
        policy_violations = data.get("policy_violations", [])
    commit_required = bool(git_status_short) and not policy_violations
    write_json(
        "artifacts/execution_commit_manifest.json",
        {
            "schema": "rga.execution_commit_manifest.v1.1",
            "commit_required": commit_required,
            "commit_candidate_files": changed_files,
            "git_status_short": git_status_short,
            "policy_violations": policy_violations,
            "commit_message": "[RGA Executor] Apply approved maintenance execution",
            "branch_name": "maintenance/executor-generated",
            "human_review_required": True,
            "post_audit_required": True,
            "governance_note": "Commit manifest is a candidate only. Bot #2 does not self-approve. Human review remains required.",
        },
    )


def emit_pr_candidate() -> None:
    commit_manifest = ROOT / "artifacts/execution_commit_manifest.json"
    pull_request_required = False
    branch_name = "maintenance/executor-generated"
    title = "[RGA Executor] Approved maintenance updates"
    body = "Generated by RGA Executor. Bot #1 post-audit remains required."
    commit_candidate_files: List[str] = []
    policy_violations: List[str] = []
    if commit_manifest.exists():
        data = json.loads(commit_manifest.read_text(encoding="utf-8"))
        pull_request_required = data.get("commit_required", False)
        branch_name = data.get("branch_name", branch_name)
        commit_candidate_files = data.get("commit_candidate_files", [])
        policy_violations = data.get("policy_violations", [])
    write_json(
        "artifacts/execution_pull_request_candidate.json",
        {
            "schema": "rga.execution_pull_request_candidate.v1.1",
            "pull_request_required": pull_request_required,
            "branch_name": branch_name,
            "title": title,
            "body": body,
            "commit_candidate_files": commit_candidate_files,
            "policy_violations": policy_violations,
            "required_reviewers": ["human_governor"],
            "required_gates": ["execution_gate", "approval_artifact_matching", "execution_scope_verification", "execution_policy_verification", "post_audit"],
            "governance_note": "This file records a PR candidate. Actual PR creation occurs only in the gated PR creation step.",
        },
    )


def emit_execution_bundle_manifest() -> None:
    artifact_candidates = [
        "execution_plan.json",
        "execution_plan.md",
        "execution_plan_fingerprint.json",
        "approval_verification.json",
        "approval_artifact_matching.json",
        "execution_scope_verification.json",
        "execution_policy_verification.json",
        "apply_execution_result.json",
        "repository_changes.json",
        "execution_commit_manifest.json",
        "execution_pull_request_candidate.json",
        "execution_git_commit_result.json",
        "execution_pull_request_result.json",
        "execution_pull_request_url.txt",
        "execution_pull_request_stderr.txt",
        "execution_manifest.txt",
        "execution_lineage.json",
        "post_audit_trigger.json",
        "rollback_evidence.json",
        "execution_gate.json",
        "runtime_executor_stdout.txt",
        "runtime_executor_stderr.txt",
    ]
    existing = [item for item in artifact_candidates if (ROOT / "artifacts" / item).exists()]
    write_json(
        "artifacts/execution_bundle_manifest.json",
        {
            "schema": "rga.execution_bundle_manifest.v1.1",
            "bundle": "rga_maintenance_executor_bundle.zip",
            "artifact_count": len(existing),
            "bundle_contents": existing,
            "execution_lifecycle": ["execution_gate", "execution_plan", "approval_verification", "approval_artifact_matching", "execution_scope_verification", "execution_policy_verification", "apply_execution_result", "repository_changes", "execution_commit_manifest", "execution_pull_request_candidate", "execution_git_commit_result", "execution_pull_request_result", "execution_lineage", "post_audit_trigger", "rollback_evidence"],
        },
    )


def emit_bundle_integrity_manifest() -> None:
    hashes = {}
    artifacts_dir = ROOT / "artifacts"
    if artifacts_dir.exists():
        for path in sorted(artifacts_dir.rglob("*")):
            if path.is_file() and path.name != "bundle_integrity_manifest.json":
                hashes[str(path.relative_to(artifacts_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json("artifacts/bundle_integrity_manifest.json", {"schema": "rga.bundle_integrity_manifest.v1.0", "artifact_hash_count": len(hashes), "sha256": hashes})


def emit_lineage() -> None:
    write_json("artifacts/execution_lineage.json", {"schema": "rga.execution_lineage.v1.0", "flow": ["runtime_verifier_report", "execution_plan", "apply_execution_result", "post_audit"]})


def emit_post_audit_trigger() -> None:
    apply_result_file = ROOT / "artifacts/apply_execution_result.json"
    execution_performed = False
    post_audit_required = True
    if apply_result_file.exists():
        try:
            apply_result = json.loads(apply_result_file.read_text(encoding="utf-8"))
            execution_performed = bool(apply_result.get("execution_performed", False))
            post_audit_required = bool(apply_result.get("post_audit_required", True))
        except Exception:
            execution_performed = False
            post_audit_required = True
    write_json(
        "artifacts/post_audit_trigger.json",
        {
            "schema": "rga.post_audit_trigger.v1.1",
            "audit_mode": "post_audit",
            "required": post_audit_required,
            "execution_performed": execution_performed,
            "trigger_source": "Bot #2 execution",
            "recommended_workflow": "RGA Runtime Verifier",
            "governance_note": "Post-audit should be run by Bot #1 after any successful Bot #2 execution.",
        },
    )


def emit_rollback_evidence() -> None:
    write_json("artifacts/rollback_evidence.json", {"schema": "rga.rollback_evidence.v1.0", "rollback_available": True, "strategy": "restore generated executor artifacts"})


def emit_manifest() -> None:
    write_text("artifacts/execution_manifest.txt", "\n".join(sorted(str(path.name) for path in (ROOT / "artifacts").glob("*"))) + "\n")


def emit_pull_request_result(url: str | None, stderr: str | None) -> None:
    write_json(
        "artifacts/execution_pull_request_result.json",
        {
            "schema": "rga.execution_pull_request_result.v1.0",
            "pull_request_attempted": True,
            "pull_request_created": bool(url and url.strip()),
            "pull_request_url": url.strip() if url else None,
            "stderr": stderr,
            "post_audit_required": True,
        },
    )


def emit_commit_result() -> None:
    write_json(
        "artifacts/execution_git_commit_result.json",
        {
            "schema": "rga.execution_git_commit_result.v1.0",
            "commit_attempted": False,
            "commit_created": False,
            "branch_name": "maintenance/executor-generated",
            "commit_message": "[RGA Executor] Apply approved maintenance execution",
            "reason": None,
        },
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python tools/rga_workflow_helpers.py <function_name>")
    name = sys.argv[1]
    if name == "emit_execution_gate":
        emit_execution_gate(sys.argv[2], sys.argv[3])
    elif name == "emit_approval_verification":
        emit_approval_verification()
    elif name == "emit_runtime_executor_summary":
        emit_runtime_executor_summary()
    elif name == "emit_runtime_executor_fallback_report":
        emit_runtime_executor_fallback_report()
    elif name == "emit_execution_plan_fingerprint":
        emit_execution_plan_fingerprint()
    elif name == "emit_approval_matching":
        emit_approval_matching()
    elif name == "emit_scope_verification":
        emit_scope_verification()
    elif name == "emit_policy_verification":
        emit_policy_verification()
    elif name == "emit_apply_result":
        emit_apply_result()
    elif name == "emit_repository_changes":
        emit_repository_changes(sys.argv[2])
    elif name == "emit_commit_manifest":
        emit_commit_manifest()
    elif name == "emit_pr_candidate":
        emit_pr_candidate()
    elif name == "emit_execution_bundle_manifest":
        emit_execution_bundle_manifest()
    elif name == "emit_bundle_integrity_manifest":
        emit_bundle_integrity_manifest()
    elif name == "emit_lineage":
        emit_lineage()
    elif name == "emit_post_audit_trigger":
        emit_post_audit_trigger()
    elif name == "emit_rollback_evidence":
        emit_rollback_evidence()
    elif name == "emit_manifest":
        emit_manifest()
    elif name == "emit_pull_request_result":
        emit_pull_request_result(sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
    elif name == "emit_commit_result":
        emit_commit_result()
    else:
        raise SystemExit(f"Unknown function: {name}")
