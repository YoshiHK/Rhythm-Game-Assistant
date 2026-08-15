from __future__ import annotations

"""
GitHub Lifecycle Bridge for RGA.

Purpose
-------
Bridge the local Path A maintenance result into the online lifecycle:

    Run_UpdateRuntimeDbs.ps1
        -> artifacts/runtime_baseline.json
        -> GitHub workflow_dispatch
        -> RGA Lifecycle Runner

This script is intentionally additive and non-destructive:
- It does not modify Completed Phases 1-7.
- It does not mutate runtime databases.
- It only validates the runtime baseline contract and optionally dispatches
  a GitHub Actions workflow.

Recommended local usage
-----------------------
Dry-run first:

    python github_lifecycle_bridge.py \
        --owner YoshiHK \
        --repo Rhythm-Game-Assistant \
        --workflow "RGA Lifecycle Runner.yml" \
        --ref main \
        --baseline artifacts/runtime_baseline.json \
        --audit-mode pre_audit \
        --dry-run

Dispatch:

    $env:PAT_TOKEN = "<token-with-actions-write>"

    python github_lifecycle_bridge.py \
        --owner YoshiHK \
        --repo Rhythm-Game-Assistant \
        --workflow "RGA Lifecycle Runner.yml" \
        --ref main \
        --baseline artifacts/runtime_baseline.json \
        --audit-mode pre_audit \
        --dispatch
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"

RUNTIME_BASELINE_SCHEMA = "rga.runtime_baseline.v1.0"
BRIDGE_SCHEMA = "rga.github_lifecycle_bridge.v1.0"
DEFAULT_WORKFLOW = "RGA Lifecycle Runner.yml"
DEFAULT_REF = "main"


@dataclass(frozen=True)
class BridgeConfig:
    owner: str
    repo: str
    workflow: str
    ref: str
    baseline_path: Path
    audit_mode: str
    audit_session_id: str
    dry_run: bool
    dispatch: bool
    token_env: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_artifacts_dir() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_artifacts_dir()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def resolve_token(token_env: str) -> Optional[str]:
    # Explicit env wins; then common GitHub token names.
    candidates = [
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


def validate_runtime_baseline(path: Path) -> Dict[str, Any]:
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
        name for name in required
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
        "baseline_ready": bool(payload.get("baseline_ready")),
        "summary": payload.get("summary") or {},
        "generated_at": payload.get("generated_at"),
        "contract": payload.get("contract") or {},
        "governance": payload.get("governance") or {},
    }


def build_workflow_dispatch_payload(config: BridgeConfig) -> Dict[str, Any]:
    inputs = {
        "audit_mode": config.audit_mode,
        "audit_session_id": config.audit_session_id,
        "runtime_baseline": str(config.baseline_path),
        "trigger_source": "github_lifecycle_bridge",
    }

    return {
        "ref": config.ref,
        "inputs": inputs,
    }


def workflow_dispatch_url(config: BridgeConfig) -> str:
    workflow = config.workflow
    return (
        "https://api.github.com/repos/"
        f"{config.owner}/{config.repo}/actions/workflows/"
        f"{workflow}/dispatches"
    )


def dispatch_workflow(config: BridgeConfig, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        workflow_dispatch_url(config),
        data=data,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "reason": response.reason,
                "body": body,
            }

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "body": body,
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "reason": type(exc).__name__,
            "body": str(exc),
        }


def parse_args(argv: Optional[list[str]] = None) -> BridgeConfig:
    parser = argparse.ArgumentParser(
        description="Bridge local RGA runtime baseline into GitHub lifecycle workflow_dispatch."
    )

    parser.add_argument("--owner", required=True, help="GitHub repository owner/org")
    parser.add_argument("--repo", required=True, help="GitHub repository name")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help="Workflow file name or workflow id")
    parser.add_argument("--ref", default=DEFAULT_REF, help="Git ref to dispatch")
    parser.add_argument("--baseline", default="artifacts/runtime_baseline.json", help="Path to runtime_baseline.json")
    parser.add_argument("--audit-mode", default="pre_audit", help="Lifecycle audit mode input")
    parser.add_argument("--audit-session-id", default="", help="Optional audit session id")
    parser.add_argument("--token-env", default="PAT_TOKEN", help="Environment variable containing GitHub token")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Write request/report but do not call GitHub API")
    mode.add_argument("--dispatch", action="store_true", help="Call GitHub workflow_dispatch API")

    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path

    audit_session_id = args.audit_session_id.strip()
    if not audit_session_id:
        audit_session_id = f"local-runtime-baseline-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    return BridgeConfig(
        owner=args.owner,
        repo=args.repo,
        workflow=args.workflow,
        ref=args.ref,
        baseline_path=baseline_path,
        audit_mode=args.audit_mode,
        audit_session_id=audit_session_id,
        dry_run=bool(args.dry_run),
        dispatch=bool(args.dispatch),
        token_env=args.token_env,
    )


def main(argv: Optional[list[str]] = None) -> int:
    ensure_artifacts_dir()
    config = parse_args(argv)

    baseline_validation = validate_runtime_baseline(config.baseline_path)
    request_payload = build_workflow_dispatch_payload(config)

    report: Dict[str, Any] = {
        "schema": BRIDGE_SCHEMA,
        "generated_at": utc_now_iso(),
        "mode": "dispatch" if config.dispatch else "dry_run",
        "repository": {
            "owner": config.owner,
            "repo": config.repo,
            "ref": config.ref,
            "workflow": config.workflow,
        },
        "runtime_baseline": baseline_validation,
        "workflow_dispatch": {
            "url": workflow_dispatch_url(config),
            "payload": request_payload,
        },
        "governance": {
            "completed_phases_remain_immutable": True,
            "bridge_is_non_destructive": True,
            "validation_is_not_verification": True,
            "deployment_gate_required": True,
        },
    }

    request_out = ARTIFACTS / "github_lifecycle_bridge_request.json"
    report_out = ARTIFACTS / "github_lifecycle_bridge_report.json"

    write_json(request_out, request_payload)

    if not baseline_validation.get("valid"):
        report["dispatch_result"] = {
            "attempted": False,
            "ok": False,
            "reason": baseline_validation.get("reason"),
        }
        write_json(report_out, report)
        print(f"[RGA-BRIDGE][FAIL] runtime baseline invalid: {baseline_validation.get('reason')}")
        print(f"[RGA-BRIDGE][REPORT] {report_out}")
        return 2

    if config.dispatch:
        token = resolve_token(config.token_env)
        if not token:
            report["dispatch_result"] = {
                "attempted": False,
                "ok": False,
                "reason": "github_token_missing",
                "checked_env": [config.token_env, "PAT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
            }
            write_json(report_out, report)
            print("[RGA-BRIDGE][FAIL] GitHub token missing.")
            print(f"[RGA-BRIDGE][REPORT] {report_out}")
            return 3

        result = dispatch_workflow(config, token, request_payload)
        report["dispatch_result"] = {
            "attempted": True,
            **result,
        }
        write_json(report_out, report)

        if result.get("ok"):
            print("[RGA-BRIDGE][OK] workflow_dispatch accepted.")
            print(f"[RGA-BRIDGE][REPORT] {report_out}")
            return 0

        print(f"[RGA-BRIDGE][FAIL] workflow_dispatch failed: {result.get('status')} {result.get('reason')}")
        print(f"[RGA-BRIDGE][REPORT] {report_out}")
        return 4

    report["dispatch_result"] = {
        "attempted": False,
        "ok": True,
        "reason": "dry_run",
    }
    write_json(report_out, report)

    print("[RGA-BRIDGE][DRY-RUN] request generated; no GitHub API call made.")
    print(f"[RGA-BRIDGE][REQUEST] {request_out}")
    print(f"[RGA-BRIDGE][REPORT] {report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
