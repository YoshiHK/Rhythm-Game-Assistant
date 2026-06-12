
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class GateOptions:
    require_repo_smoke: bool = True
    require_phase5_summary: bool = True
    require_offline_validation: bool = True
    require_runtime_index: bool = False
    require_runtime_integrity_pass: bool = True
    require_runtime_stage_completion: bool = True
    allow_zero_failed_cases_only: bool = True


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
    p.add_argument("--require-runtime-index", action="store_true", help="Require runtime_index.json to be present and valid")
    p.add_argument("--output", default="deployment_gate_report.json", help="Output JSON report path")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    repo_smoke_path = _read_if_exists(args.repo_smoke_summary) or _latest_json(["repo_smoke_summary.json"])
    phase5_summary_path = _read_if_exists(args.phase5_summary) or _latest_json(["test_case_summary.json"])
    offline_validation_path = _read_if_exists(args.offline_validation_report) or _latest_json(["offline_validation_report.json"])
    runtime_index_path = _read_if_exists(args.runtime_index) or _latest_json(["runtime_index.json"])

    result = evaluate_gate(
        repo_smoke_path=repo_smoke_path,
        phase5_summary_path=phase5_summary_path,
        offline_validation_path=offline_validation_path,
        runtime_index_path=runtime_index_path,
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
