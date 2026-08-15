from __future__ import annotations

"""
GitHub Lifecycle Bridge for RGA.

Purpose
-------
Bridge the local Path A maintenance result into the online lifecycle:

    Run_UpdateRuntimeDbs.ps1
        -> artifacts/runtime_baseline.json
        -> GitHub Contents API commit / PR / workflow_dispatch
        -> RGA Lifecycle Runner

This script is intentionally additive and non-destructive:
- It does not modify Completed Phases 1-7.
- It does not mutate runtime databases.
- It commits only governance evidence by default.
- It targets a branch, not main, by default.
- It can optionally create a PR.
- It can optionally dispatch the lifecycle workflow.

Supported actions
-----------------
--dry-run
    Validate baseline and write request/report only.

--dispatch
    Trigger RGA Lifecycle Runner only.

--commit-baseline
    Commit artifacts/runtime_baseline.json to a GitHub branch.

--commit-and-dispatch
    Commit baseline, then trigger lifecycle.

--create-pr
    Create PR after committing baseline branch.

Token requirement
-----------------
For any GitHub API mutation, set PAT_TOKEN locally:

    $env:PAT_TOKEN = "<fine-grained-token>"

Recommended token permissions:
- Contents: Read and write
- Actions: Read and write, if using --dispatch or --commit-and-dispatch
- Pull requests: Read and write, if using --create-pr

Recommended local usage
-----------------------
Dry-run first:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --workflow "RGA Lifecycle Runner.yml" `
        --ref main `
        --baseline .\\artifacts\\runtime_baseline.json `
        --audit-mode pre_audit `
        --dry-run

Commit baseline to a branch:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --baseline .\\artifacts\\runtime_baseline.json `
        --commit-baseline

Commit baseline, open PR, and dispatch lifecycle:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --workflow "RGA Lifecycle Runner.yml" `
        --baseline .\\artifacts\\runtime_baseline.json `
        --commit-and-dispatch `
        --create-pr
"""

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


# ------------------------------------------------------------
# Repository Paths
#
# If this file lives under tools/, repo root is parent.parent.
# If this file lives at repo root, repo root is parent.
# ------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
ROOT = (
    _THIS_FILE.parent.parent
    if _THIS_FILE.parent.name == "tools"
    else _THIS_FILE.parent
)
ARTIFACTS = ROOT / "artifacts"


# ------------------------------------------------------------
# Contracts / constants
# ------------------------------------------------------------

RUNTIME_BASELINE_SCHEMA = "rga.runtime_baseline.v1.0"
BRIDGE_SCHEMA = "rga.github_lifecycle_bridge.v1.1"

DEFAULT_WORKFLOW = "RGA Lifecycle Runner.yml"
DEFAULT_REF = "main"
DEFAULT_REMOTE_PATH = "artifacts/runtime_baseline.json"

ALLOWED_COMMIT_PATHS = {
    "artifacts/runtime_baseline.json",
    "artifacts/github_lifecycle_bridge_request.json",
    "artifacts/github_lifecycle_bridge_report.json",
}

PROHIBITED_REMOTE_PATH_FRAGMENTS = (
    "runtime/",
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Phase 4",
    "Phase 4.5",
    "Phase 5",
    "Phase 6",
    "Phase 7",
    "canonical_row",
    "pattern_logic",
    "tips_generation",
    "personalization",
    "localization",
    "recommendation_logic",
)


@dataclass(frozen=True)
class BridgeConfig:
    owner: str
    repo: str

    workflow: str
    ref: str

    baseline_path: Path
    audit_mode: str
    audit_session_id: str

    token_env: str

    dry_run: bool
    dispatch: bool
    commit_baseline: bool
    commit_and_dispatch: bool
    create_pr: bool

    base_branch: str
    target_branch: str

    remote_path: str
    commit_message: str

    pr_title: str
    pr_body: str


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def ensure_artifacts_dir() -> None:
    ARTIFACTS.mkdir(
        parents=True,
        exist_ok=True,
    )


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def write_json(
    path: Path,
    payload: Dict[str, Any],
) -> None:
    ensure_artifacts_dir()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def resolve_token(token_env: str) -> Optionalcandidates = [
        token_env,
        "PAT_TOKEN",
        "GH_TOKEN",
        "GITHUB_TOKEN",
    ]

    seen = set()

    for name in candidates:
        if not name or name in seen:
            continue

        seen.add(name)

        value = os.environ.get(name)

        if value and value.strip():
            return value.strip()

    return None


def repo_api_root(config: BridgeConfig) -> str:
    return (
        "https://api.github.com/repos/"
        f"{config.owner}/{config.repo}"
    )


def github_request(
    *,
    method: str,
    url: str,
    token: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    body: Optional[bytes] = None

    if payload is not None:
        body = json.dumps(
            payload,
        ).encode(
            "utf-8",
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            text = response.read().decode(
                "utf-8",
                errors="replace",
            )

            parsed: Any = None

            if text.strip():
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = text

            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "reason": response.reason,
                "body": parsed,
            }

    except urllib.error.HTTPError as exc:

        text = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        parsed: Any = None

        if text.strip():
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = text

        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "body": parsed,
        }

    except Exception as exc:

        return {
            "ok": False,
            "status": None,
            "reason": type(exc).__name__,
            "body": str(exc),
        }


def validate_remote_path(
    remote_path: str,
) -> Dict[str, Any]:

    normalized = (
        remote_path
        .replace("\\", "/")
        .strip("/")
    )

    if normalized not in ALLOWED_COMMIT_PATHS:
        return {
            "valid": False,
            "reason": "remote_path_not_allowed",
            "remote_path": normalized,
            "allowed_paths": sorted(
                ALLOWED_COMMIT_PATHS
            ),
        }

    for fragment in PROHIBITED_REMOTE_PATH_FRAGMENTS:
        if fragment.lower() in normalized.lower():
            return {
                "valid": False,
                "reason": "remote_path_hits_prohibited_scope",
                "remote_path": normalized,
                "fragment": fragment,
            }

    return {
        "valid": True,
        "remote_path": normalized,
    }


def validate_runtime_baseline(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {
            "valid": False,
            "reason": "runtime_baseline_missing",
            "path": str(path),
        }

    try:
        payload = read_json(path)

    except Exception as exc:
        return {
            "valid": False,
            "reason": "runtime_baseline_parse_error",
            "path": str(path),
            "error": str(exc),
        }

    schema = payload.get("schema")

    if schema != RUNTIME_BASELINE_SCHEMA:
        return {
            "valid": False,
            "reason": "unsupported_runtime_baseline_schema",
            "path": str(path),
            "schema": schema,
        }

    databases = payload.get("databases") or {}

    required = [
        "file_scan_inventory.db",
        "chart_assets.db",
        "chart_patterns.db",
    ]

    missing_database_nodes = [
        name
        for name in required
        if name not in databases
    ]

    unreadable = []

    for name in required:
        node = databases.get(name) or {}

        if node and node.get("readable") is not True:
            unreadable.append(name)

    if missing_database_nodes:
        return {
            "valid": False,
            "reason": "runtime_baseline_database_node_missing",
            "path": str(path),
            "missing_database_nodes": missing_database_nodes,
        }

    if unreadable:
        return {
            "valid": False,
            "reason": "runtime_baseline_database_not_readable",
            "path": str(path),
            "unreadable": unreadable,
        }

    return {
        "valid": True,
        "path": str(path),
        "schema": schema,
        "baseline_ready": bool(
            payload.get("baseline_ready")
        ),
        "summary": payload.get("summary") or {},
        "generated_at": payload.get("generated_at"),
        "contract": payload.get("contract") or {},
        "governance": payload.get("governance") or {},
    }


def build_workflow_dispatch_payload(
    config: BridgeConfig,
) -> Dict[str, Any]:

    return {
        "ref": config.ref,
        "inputs": {
            "audit_mode": config.audit_mode,
            "audit_session_id": config.audit_session_id,
            "runtime_baseline": str(
                config.baseline_path
            ),
            "trigger_source": "github_lifecycle_bridge",
        },
    }


def workflow_dispatch_url(
    config: BridgeConfig,
) -> str:

    # workflow may be a file name or numeric workflow id.
    workflow = urllib.parse.quote(
        config.workflow,
        safe="",
    )

    return (
        f"{repo_api_root(config)}"
        f"/actions/workflows/{workflow}/dispatches"
    )


def dispatch_workflow(
    *,
    config: BridgeConfig,
    token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    return github_request(
        method="POST",
        url=workflow_dispatch_url(config),
        token=token,
        payload=payload,
    )


def get_branch_sha(
    *,
    config: BridgeConfig,
    token: str,
    branch: str,
) -> Dict[str, Any]:

    branch_encoded = urllib.parse.quote(
        f"heads/{branch}",
        safe="",
    )

    url = (
        f"{repo_api_root(config)}"
        f"/git/ref/{branch_encoded}"
    )

    return github_request(
        method="GET",
        url=url,
        token=token,
    )


def create_branch(
    *,
    config: BridgeConfig,
    token: str,
    target_branch: str,
    base_branch: str,
) -> Dict[str, Any]:

    base_ref = get_branch_sha(
        config=config,
        token=token,
        branch=base_branch,
    )

    if not base_ref.get("ok"):
        return {
            "ok": False,
            "stage": "get_base_branch",
            "base_branch": base_branch,
            "result": base_ref,
        }

    body = base_ref.get("body") or {}
    base_sha = (
        (body.get("object") or {})
        .get("sha")
    )

    if not base_sha:
        return {
            "ok": False,
            "stage": "extract_base_sha",
            "base_branch": base_branch,
            "result": base_ref,
        }

    payload = {
        "ref": f"refs/heads/{target_branch}",
        "sha": base_sha,
    }

    result = github_request(
        method="POST",
        url=f"{repo_api_root(config)}/git/refs",
        token=token,
        payload=payload,
    )

    if result.get("ok"):
        return {
            "ok": True,
            "created": True,
            "branch": target_branch,
            "base_branch": base_branch,
            "base_sha": base_sha,
            "result": result,
        }

    # 422 often means branch already exists.
    # Treat it as non-fatal after verifying the branch exists.
    if result.get("status") == 422:

        existing = get_branch_sha(
            config=config,
            token=token,
            branch=target_branch,
        )

        return {
            "ok": bool(existing.get("ok")),
            "created": False,
            "already_exists": bool(
                existing.get("ok")
            ),
            "branch": target_branch,
            "base_branch": base_branch,
            "base_sha": base_sha,
            "result": result,
            "existing": existing,
        }

    return {
        "ok": False,
        "created": False,
        "branch": target_branch,
        "base_branch": base_branch,
        "base_sha": base_sha,
        "result": result,
    }


def get_remote_file_sha(
    *,
    config: BridgeConfig,
    token: str,
    remote_path: str,
    branch: str,
) -> Dict[str, Any]:

    path_encoded = urllib.parse.quote(
        remote_path,
        safe="/",
    )

    branch_encoded = urllib.parse.quote(
        branch,
        safe="",
    )

    url = (
        f"{repo_api_root(config)}"
        f"/contents/{path_encoded}"
        f"?ref={branch_encoded}"
    )

    return github_request(
        method="GET",
        url=url,
        token=token,
    )


def commit_runtime_baseline_to_github(
    *,
    config: BridgeConfig,
    token: str,
) -> Dict[str, Any]:
    """
    Commit local artifacts/runtime_baseline.json to GitHub Contents API.

    Steps:
    1. Read local artifacts/runtime_baseline.json.
    2. Get existing remote file SHA if present.
    3. PUT updated content to GitHub Contents API.
    4. Target a branch, preferably not main.
    5. Return a structured response for github_lifecycle_bridge_report.json.
    """

    path_validation = validate_remote_path(
        config.remote_path
    )

    if not path_validation.get("valid"):
        return {
            "attempted": False,
            "ok": False,
            "reason": path_validation.get("reason"),
            "path_validation": path_validation,
        }

    if config.target_branch == config.base_branch:
        return {
            "attempted": False,
            "ok": False,
            "reason": "target_branch_must_not_equal_base_branch",
            "base_branch": config.base_branch,
            "target_branch": config.target_branch,
        }

    if not config.baseline_path.exists():
        return {
            "attempted": False,
            "ok": False,
            "reason": "runtime_baseline_missing",
            "baseline_path": str(config.baseline_path),
        }

    branch_result = create_branch(
        config=config,
        token=token,
        target_branch=config.target_branch,
        base_branch=config.base_branch,
    )

    if not branch_result.get("ok"):
        return {
            "attempted": True,
            "ok": False,
            "stage": "create_branch",
            "branch_result": branch_result,
        }

    file_result = get_remote_file_sha(
        config=config,
        token=token,
        remote_path=config.remote_path,
        branch=config.target_branch,
    )

    remote_sha = None

    if file_result.get("ok"):
        body = file_result.get("body") or {}
        remote_sha = body.get("sha")

    content_bytes = config.baseline_path.read_bytes()

    encoded_content = base64.b64encode(
        content_bytes,
    ).decode(
        "ascii",
    )

    payload: Dict[str, Any] = {
        "message": config.commit_message,
        "content": encoded_content,
        "branch": config.target_branch,
    }

    if remote_sha:
        payload["sha"] = remote_sha

    path_encoded = urllib.parse.quote(
        config.remote_path,
        safe="/",
    )

    put_result = github_request(
        method="PUT",
        url=(
            f"{repo_api_root(config)}"
            f"/contents/{path_encoded}"
        ),
        token=token,
        payload=payload,
    )

    return {
        "attempted": True,
        "ok": bool(put_result.get("ok")),
        "remote_path": config.remote_path,
        "baseline_path": str(config.baseline_path),
        "base_branch": config.base_branch,
        "target_branch": config.target_branch,
        "remote_sha_before": remote_sha,
        "branch_result": branch_result,
        "remote_file_lookup": file_result,
        "put_result": put_result,
    }


def create_pull_request(
    *,
    config: BridgeConfig,
    token: str,
) -> Dict[str, Any]:

    payload = {
        "title": config.pr_title,
        "head": config.target_branch,
        "base": config.base_branch,
        "body": config.pr_body,
        "maintainer_can_modify": True,
    }

    return github_request(
        method="POST",
        url=f"{repo_api_root(config)}/pulls",
        token=token,
        payload=payload,
    )


def parse_args(
    argv: Optional[list[str]] = None,
) -> BridgeConfig:

    parser = argparse.ArgumentParser(
        description=(
            "Bridge local RGA runtime baseline "
            "into GitHub lifecycle."
        )
    )

    parser.add_argument(
        "--owner",
        required=True,
        help="GitHub repository owner/org",
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository name",
    )

    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        help="Workflow file name or workflow id",
    )

    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help="Git ref to dispatch workflow on",
    )

    parser.add_argument(
        "--baseline",
        default="artifacts/runtime_baseline.json",
        help="Path to runtime_baseline.json",
    )

    parser.add_argument(
        "--audit-mode",
        default="pre_audit",
        help="Lifecycle audit mode input",
    )

    parser.add_argument(
        "--audit-session-id",
        default="",
        help="Optional lifecycle correlation id",
    )

    parser.add_argument(
        "--token-env",
        default="PAT_TOKEN",
        help="Environment variable containing GitHub token",
    )

    parser.add_argument(
        "--base-branch",
        default=DEFAULT_REF,
        help="Base branch for baseline commit / PR",
    )

    parser.add_argument(
        "--target-branch",
        default="",
        help="Target branch for baseline commit",
    )

    parser.add_argument(
        "--remote-path",
        default=DEFAULT_REMOTE_PATH,
        help="Remote repository path to update",
    )

    parser.add_argument(
        "--commit-message",
        default="[RGA Runtime] Update runtime baseline contract",
        help="Commit message",
    )

    parser.add_argument(
        "--pr-title",
        default="[RGA Runtime] Update runtime baseline contract",
        help="Pull request title",
    )

    parser.add_argument(
        "--pr-body",
        default=(
            "Automated runtime baseline contract update "
            "generated by RGA GitHub Lifecycle Bridge."
        ),
        help="Pull request body",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate baseline and write request/report only",
    )

    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="Trigger RGA Lifecycle Runner only",
    )

    parser.add_argument(
        "--commit-baseline",
        action="store_true",
        help=(
            "Commit artifacts/runtime_baseline.json "
            "to GitHub branch"
        ),
    )

    parser.add_argument(
        "--commit-and-dispatch",
        action="store_true",
        help="Commit baseline, then trigger lifecycle",
    )

    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create PR after committing baseline branch",
    )

    args = parser.parse_args(argv)

    selected_actions = sum(
        bool(value)
        for value in [
            args.dry_run,
            args.dispatch,
            args.commit_baseline,
            args.commit_and_dispatch,
        ]
    )

    if selected_actions == 0:
        args.dry_run = True

    elif selected_actions > 1:
        parser.error(
            "Choose only one of "
            "--dry-run, --dispatch, "
            "--commit-baseline, or "
            "--commit-and-dispatch."
        )

    if args.create_pr and not (
        args.commit_baseline
        or args.commit_and_dispatch
    ):
        parser.error(
            "--create-pr requires "
            "--commit-baseline or "
            "--commit-and-dispatch."
        )

    baseline_path = Path(args.baseline)

    if not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path

    audit_session_id = args.audit_session_id.strip()

    if not audit_session_id:
        audit_session_id = (
            f"local-runtime-baseline-{safe_timestamp()}"
        )

    target_branch = args.target_branch.strip()

    if not target_branch:
        target_branch = (
            f"runtime-baseline/update-{safe_timestamp()}"
        )

    return BridgeConfig(
        owner=args.owner,
        repo=args.repo,
        workflow=args.workflow,
        ref=args.ref,
        baseline_path=baseline_path,
        audit_mode=args.audit_mode,
        audit_session_id=audit_session_id,
        token_env=args.token_env,
        dry_run=bool(args.dry_run),
        dispatch=bool(args.dispatch),
        commit_baseline=bool(args.commit_baseline),
        commit_and_dispatch=bool(
            args.commit_and_dispatch
        ),
        create_pr=bool(args.create_pr),
        base_branch=args.base_branch,
        target_branch=target_branch,
        remote_path=(
            args.remote_path
            .replace("\\", "/")
            .strip("/")
        ),
        commit_message=args.commit_message,
        pr_title=args.pr_title,
        pr_body=args.pr_body,
    )


def main(
    argv: Optional[list[str]] = None,
) -> int:

    ensure_artifacts_dir()

    config = parse_args(argv)

    baseline_validation = validate_runtime_baseline(
        config.baseline_path
    )

    path_validation = validate_remote_path(
        config.remote_path
    )

    request_payload = build_workflow_dispatch_payload(
        config
    )

    report: Dict[str, Any] = {
        "schema": BRIDGE_SCHEMA,
        "generated_at": utc_now_iso(),
        "mode": (
            "commit_and_dispatch"
            if config.commit_and_dispatch
            else "commit_baseline"
            if config.commit_baseline
            else "dispatch"
            if config.dispatch
            else "dry_run"
        ),
        "repository": {
            "owner": config.owner,
            "repo": config.repo,
            "workflow": config.workflow,
            "dispatch_ref": config.ref,
            "base_branch": config.base_branch,
            "target_branch": config.target_branch,
            "remote_path": config.remote_path,
        },
        "runtime_baseline": baseline_validation,
        "remote_path_validation": path_validation,
        "workflow_dispatch": {
            "url": workflow_dispatch_url(config),
            "payload": request_payload,
        },
        "governance": {
            "completed_phases_remain_immutable": True,
            "bridge_is_non_destructive": True,
            "bridge_commits_only_governance_evidence": True,
            "bridge_does_not_commit_runtime_dbs": True,
            "validation_is_not_verification": True,
            "deployment_gate_required": True,
        },
    }

    request_out = (
        ARTIFACTS
        / "github_lifecycle_bridge_request.json"
    )

    report_out = (
        ARTIFACTS
        / "github_lifecycle_bridge_report.json"
    )

    write_json(
        request_out,
        request_payload,
    )

    if not baseline_validation.get("valid"):
        report["dispatch_result"] = {
            "attempted": False,
            "ok": False,
            "reason": baseline_validation.get("reason"),
        }

        write_json(
            report_out,
            report,
        )

        print(
            "[RGA-BRIDGE][FAIL] "
            f"runtime baseline invalid: "
            f"{baseline_validation.get('reason')}"
        )

        print(
            f"[RGA-BRIDGE][REPORT] {report_out}"
        )

        return 2

    if not path_validation.get("valid"):
        report["commit_result"] = {
            "attempted": False,
            "ok": False,
            "reason": path_validation.get("reason"),
        }

        write_json(
            report_out,
            report,
        )

        print(
            "[RGA-BRIDGE][FAIL] "
            f"remote path rejected: "
            f"{path_validation.get('reason')}"
        )

        print(
            f"[RGA-BRIDGE][REPORT] {report_out}"
        )

        return 5

    token: Optional[str] = None

    needs_token = (
        config.dispatch
        or config.commit_baseline
        or config.commit_and_dispatch
        or config.create_pr
    )

    if needs_token:
        token = resolve_token(
            config.token_env
        )

        if not token:
            report["token_result"] = {
                "ok": False,
                "reason": "github_token_missing",
                "checked_env": [
                    config.token_env,
                    "PAT_TOKEN",
                    "GH_TOKEN",
                    "GITHUB_TOKEN",
                ],
            }

            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "GitHub token missing. Set PAT_TOKEN."
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 3

        report["token_result"] = {
            "ok": True,
            "source_env": config.token_env,
        }

    if config.commit_baseline or config.commit_and_dispatch:
        assert token is not None

        commit_result = commit_runtime_baseline_to_github(
            config=config,
            token=token,
        )

        report["commit_result"] = commit_result

        if not commit_result.get("ok"):
            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "baseline commit failed: "
                f"{commit_result.get('reason') or commit_result.get('stage')}"
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 6

        if config.create_pr:
            pr_result = create_pull_request(
                config=config,
                token=token,
            )

            report["pull_request_result"] = {
                "attempted": True,
                **pr_result,
            }

            if not pr_result.get("ok"):
                write_json(
                    report_out,
                    report,
                )

                print(
                    "[RGA-BRIDGE][FAIL] "
                    "PR creation failed: "
                    f"{pr_result.get('status')} "
                    f"{pr_result.get('reason')}"
                )

                print(
                    f"[RGA-BRIDGE][REPORT] {report_out}"
                )

                return 7

    if config.dispatch or config.commit_and_dispatch:
        assert token is not None

        dispatch_result = dispatch_workflow(
            config=config,
            token=token,
            payload=request_payload,
        )

        report["dispatch_result"] = {
            "attempted": True,
            **dispatch_result,
        }

        if not dispatch_result.get("ok"):
            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "workflow_dispatch failed: "
                f"{dispatch_result.get('status')} "
                f"{dispatch_result.get('reason')}"
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 4

    if config.dry_run:
        report["dispatch_result"] = {
            "attempted": False,
            "ok": True,
            "reason": "dry_run",
        }

        report["commit_result"] = {
            "attempted": False,
            "ok": True,
            "reason": "dry_run",
            "target_branch": config.target_branch,
            "remote_path": config.remote_path,
        }

    write_json(
        report_out,
        report,
    )

    if config.dry_run:
        print(
            "[RGA-BRIDGE][DRY-RUN] "
            "request/report generated; "
            "no GitHub mutation performed."
        )
    else:
        print(
            "[RGA-BRIDGE][OK] "
            "requested bridge operation completed."
        )

    print(
        f"[RGA-BRIDGE][REQUEST] {request_out}"
    )

    print(
        f"[RGA-BRIDGE][REPORT] {report_out}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())