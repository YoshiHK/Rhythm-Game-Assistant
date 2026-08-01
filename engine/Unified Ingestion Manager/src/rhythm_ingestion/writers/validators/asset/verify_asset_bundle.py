from __future__ import annotations

"""
verify_asset_bundle.py

Bundle verifier (verify_all_chart_assets) for the chart asset system.

Purpose
-------
Run the full asset-focused verification stack in one place and return a single,
read-only report suitable for CLI use, notebook use, or deletion-safety gates.

This bundle currently orchestrates:
- verify_chart_assets
- verify_asset_consistency
- verify_conversion_determinism
- verify_identity_consistency
- verify_asset_pattern_reconciliation
- verify_chart_pipeline

Notes
-----
- read-only only
- no database mutation
- no completed-phase modification
- intended as a safety gate before any source-file deletion workflow
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.validators.verify_chart_assets import verify_chart_assets
    from rhythm_ingestion.writers.validators.verify_asset_consistency import verify_asset_consistency
    from rhythm_ingestion.writers.validators.verify_conversion_determinism import verify_conversion_determinism
    from rhythm_ingestion.writers.validators.verify_identity_consistency import verify_identity_consistency
    from rhythm_ingestion.writers.validators.verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation
    from rhythm_ingestion.writers.validators.verify_chart_pipeline import verify_chart_pipeline
except ImportError:
    try:
        from .verify_chart_assets import verify_chart_assets
        from .verify_asset_consistency import verify_asset_consistency
        from .verify_conversion_determinism import verify_conversion_determinism
        from .verify_identity_consistency import verify_identity_consistency
        from .verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation
        from .verify_chart_pipeline import verify_chart_pipeline
    except Exception:
        from verify_chart_assets import verify_chart_assets
        from verify_asset_consistency import verify_asset_consistency
        from verify_conversion_determinism import verify_conversion_determinism
        from verify_identity_consistency import verify_identity_consistency
        from verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation
        from verify_chart_pipeline import verify_chart_pipeline


DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")
DEFAULT_CHART_PATTERNS_DB = Path("chart_patterns.db")
DEFAULT_FILE_SCAN_INVENTORY_DB = Path("file_scan_inventory.db")


# --------------------------------------------------
# Report models
# --------------------------------------------------
@dataclass
class BundleStageResult:
    ok: bool
    stage: str
    summary: Dict[str, Any] = field(default_factory=dict)
    issue_count: int = 0
    hard_fail: bool = False


@dataclass
class BundleSummary:
    chart_assets_ok: bool = False
    asset_consistency_ok: bool = False
    conversion_determinism_ok: bool = False
    identity_consistency_ok: bool = False 
    asset_pattern_reconciliation_ok: bool = False
    chart_pipeline_ok: bool = False

    all_ok: bool = False
    deletion_safe: bool = False

    total_stage_failures: int = 0
    total_issue_count: int = 0


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _stage_result(*, stage: str, report: Dict[str, Any], ok: bool, hard_fail: bool) -> BundleStageResult:
    issues = report.get("issues") or []
    return BundleStageResult(
        ok=bool(ok),
        stage=stage,
        summary=report.get("summary") or {},
        issue_count=len(issues),
        hard_fail=bool(hard_fail),
    )


# --------------------------------------------------
# Public bundled verification
# --------------------------------------------------
def verify_asset_bundle(
    *,
    chart_asset_db: Path = DEFAULT_CHART_ASSET_DB,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERNS_DB,
    file_scan_inventory_db: Optional[Path] = None,
    sample_limit: int = 20,
) -> Dict[str, Any]:
    stage_reports: Dict[str, Dict[str, Any]] = {}
    stage_results: List[BundleStageResult] = []

    # 1) asset DB completeness / asset-level verification
    report_assets = verify_chart_assets(
        chart_asset_db=chart_asset_db,
        file_scan_inventory_db=file_scan_inventory_db,
        sample_limit=sample_limit,
    )
    ok_assets = int((report_assets.get("summary") or {}).get("invalid_assets") or 0) == 0
    stage_reports["verify_chart_assets"] = report_assets
    stage_results.append(
        _stage_result(
            stage="verify_chart_assets",
            report=report_assets,
            ok=ok_assets,
            hard_fail=not ok_assets,
        )
    )

    # 2) internal asset consistency
    report_consistency = verify_asset_consistency(
        chart_asset_db=chart_asset_db,
    )
    ok_consistency = bool((report_consistency.get("summary") or {}).get("consistent"))
    stage_reports["verify_asset_consistency"] = report_consistency
    stage_results.append(
        _stage_result(
            stage="verify_asset_consistency",
            report=report_consistency,
            ok=ok_consistency,
            hard_fail=not ok_consistency,
        )
    )

    # 3) conversion determinism (warning-only if source files are already absent)
    report_determinism = verify_conversion_determinism(
        chart_asset_db=chart_asset_db,
        sample_limit=sample_limit,
    )
    summary_det = report_determinism.get("summary") or {}
    # Treat determinism as strict only when at least one source file was checked.
    if int(summary_det.get("source_files_checked") or 0) > 0:
        ok_determinism = bool(summary_det.get("deterministic"))
        hard_fail_determinism = not ok_determinism
    else:
        ok_determinism = True
        hard_fail_determinism = False
    stage_reports["verify_conversion_determinism"] = report_determinism
    stage_results.append(
        _stage_result(
            stage="verify_conversion_determinism",
            report=report_determinism,
            ok=ok_determinism,
            hard_fail=hard_fail_determinism,
        )
    )
    
    # 3.5) identity consistency
    report_identity = verify_identity_consistency(
        chart_asset_db=chart_asset_db,
    )

    summary_id = report_identity.get("summary") or {}
    ok_identity = summary_id.get("conflicts", 0) == 0

    stage_reports["verify_identity_consistency"] = report_identity
    stage_results.append(
        _stage_result(
            stage="verify_identity_consistency",
            report=report_identity,
            ok=ok_identity,
            hard_fail=False,  # ⚠️ important: never hard fail
        )
    )

    # 4) asset ↔ pattern reconciliation
    report_reconcile = verify_asset_pattern_reconciliation(
        chart_asset_db=chart_asset_db,
        chart_patterns_db=chart_patterns_db,
        file_scan_inventory_db=file_scan_inventory_db,
        sample_limit=sample_limit,
    )
    sum_rec = report_reconcile.get("summary") or {}
    unreconciled = int(sum_rec.get("unreconciled_assets") or 0)
    insufficient = int(sum_rec.get("insufficient_identity_assets") or 0)
    ok_reconcile = unreconciled <= insufficient
    stage_reports["verify_asset_pattern_reconciliation"] = report_reconcile
    stage_results.append(
        _stage_result(
            stage="verify_asset_pattern_reconciliation",
            report=report_reconcile,
            ok=ok_reconcile,
            hard_fail=not ok_reconcile,
        )
    )

    # 5) full chart pipeline smoke / usability
    report_pipeline = verify_chart_pipeline(
        chart_asset_db=chart_asset_db,
        chart_patterns_db=chart_patterns_db,
        file_scan_inventory_db=file_scan_inventory_db,
        sample_limit=sample_limit,
    )
    ok_pipeline = bool((report_pipeline.get("summary") or {}).get("pipeline_usable"))
    stage_reports["verify_chart_pipeline"] = report_pipeline
    stage_results.append(
        _stage_result(
            stage="verify_chart_pipeline",
            report=report_pipeline,
            ok=ok_pipeline,
            hard_fail=not ok_pipeline,
        )
    )

    # Aggregate summary
    bundle_summary = BundleSummary(
        chart_assets_ok=ok_assets,
        asset_consistency_ok=ok_consistency,
        conversion_determinism_ok=ok_determinism,
        identity_consistency_ok=ok_identity, 
        asset_pattern_reconciliation_ok=ok_reconcile,
        chart_pipeline_ok=ok_pipeline,
        total_stage_failures=sum(1 for r in stage_results if not r.ok),
        total_issue_count=sum(r.issue_count for r in stage_results),
    )
    bundle_summary.all_ok = (
        bundle_summary.chart_assets_ok
        and bundle_summary.asset_consistency_ok
        and bundle_summary.conversion_determinism_ok
        and bundle_summary.identity_consistency_ok
        and bundle_summary.asset_pattern_reconciliation_ok
        and bundle_summary.chart_pipeline_ok
    )

    # deletion_safe is intentionally strict
    bundle_summary.deletion_safe = bundle_summary.all_ok

    return {
        "summary": asdict(bundle_summary),
        "stages": [asdict(r) for r in stage_results],
        "reports": stage_reports,
    }


# Alias for the user's naming preference
verify_all_chart_assets = verify_asset_bundle


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_asset_bundle")
    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
        help=f"Path to chart_assets.db (default: {DEFAULT_CHART_ASSET_DB})",
    )
    parser.add_argument(
        "--chart-patterns-db",
        default=str(DEFAULT_CHART_PATTERNS_DB),
        help=f"Path to chart_patterns.db (default: {DEFAULT_CHART_PATTERNS_DB})",
    )
    parser.add_argument(
        "--file-scan-db",
        default=None,
        help="Optional path to file_scan_inventory.db for coverage / reconciliation",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write the full bundle verification report",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Max number of sampled issues / smoke rows per stage",
    )

    args = parser.parse_args(argv)

    report = verify_asset_bundle(
        chart_asset_db=Path(args.chart_assets_db),
        chart_patterns_db=Path(args.chart_patterns_db),
        file_scan_inventory_db=Path(args.file_scan_db) if args.file_scan_db else None,
        sample_limit=int(args.sample_limit),
    )

    summary = report.get("summary", {})
    print("[BUNDLE] chart_assets_ok=", summary.get("chart_assets_ok"))
    print("[BUNDLE] asset_consistency_ok=", summary.get("asset_consistency_ok"))
    print("[BUNDLE] conversion_determinism_ok=", summary.get("conversion_determinism_ok"))
    print("[BUNDLE] identity_consistency_ok=", summary.get("identity_consistency_ok"))
    print("[BUNDLE] asset_pattern_reconciliation_ok=", summary.get("asset_pattern_reconciliation_ok"))
    print("[BUNDLE] chart_pipeline_ok=", summary.get("chart_pipeline_ok"))
    print("[BUNDLE] all_ok=", summary.get("all_ok"))
    print("[BUNDLE] deletion_safe=", summary.get("deletion_safe"))
    print("[BUNDLE] total_stage_failures=", summary.get("total_stage_failures"))
    print("[BUNDLE] total_issue_count=", summary.get("total_issue_count"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("[BUNDLE] report_written=", args.json_out)

    return 0 if bool(summary.get("deletion_safe")) else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_asset_bundle",
    "verify_all_chart_assets",
    "cli_main",
]
