from __future__ import annotations

"""
verify_pattern_bundle.py

Bundle verifier for chart pattern subsystem.
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rhythm_ingestion.writers.validators.verify_chart_patterns import verify_chart_patterns
    from rhythm_ingestion.writers.validators.verify_pattern_feature_consistency import verify_pattern_feature_consistency
    from rhythm_ingestion.writers.validators.verify_pattern_blob_integrity import verify_pattern_blob_integrity
    from rhythm_ingestion.writers.validators.verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation
except Exception:
    try:
        from .verify_chart_patterns import verify_chart_patterns
        from .verify_pattern_feature_consistency import verify_pattern_feature_consistency
        from .verify_pattern_blob_integrity import verify_pattern_blob_integrity
        from .verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation
    except Exception:
        from verify_chart_patterns import verify_chart_patterns
        from verify_pattern_feature_consistency import verify_pattern_feature_consistency
        from verify_pattern_blob_integrity import verify_pattern_blob_integrity
        from verify_asset_pattern_reconciliation import verify_asset_pattern_reconciliation

DEFAULT_CHART_PATTERNS_DB = Path("chart_patterns.db")
DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")
DEFAULT_FILE_SCAN_DB = Path("file_scan_inventory.db")


@dataclass
class PatternBundleStage:
    stage: str
    ok: bool
    hard_fail: bool
    issue_count: int
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternBundleSummary:
    chart_patterns_ok: bool = False
    pattern_feature_consistency_ok: bool = False
    pattern_blob_integrity_ok: bool = False
    asset_pattern_reconciliation_ok: bool = False
    all_ok: bool = False
    total_stage_failures: int = 0
    total_issue_count: int = 0


def _stage(stage: str, report: Dict[str, Any], ok: bool, hard_fail: bool) -> PatternBundleStage:
    return PatternBundleStage(
        stage=stage,
        ok=ok,
        hard_fail=hard_fail,
        issue_count=len(report.get("issues") or []),
        summary=report.get("summary") or {},
    )


def verify_pattern_bundle(
    *,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERNS_DB,
    chart_asset_db: Optional[Path] = None,
    file_scan_inventory_db: Optional[Path] = None,
) -> Dict[str, Any]:
    reports: Dict[str, Dict[str, Any]] = {}
    stages: List[PatternBundleStage] = []

    rep_patterns = verify_chart_patterns(chart_patterns_db=chart_patterns_db)
    ok_patterns = bool((rep_patterns.get("summary") or {}).get("usable"))
    reports["verify_chart_patterns"] = rep_patterns
    stages.append(_stage("verify_chart_patterns", rep_patterns, ok_patterns, not ok_patterns))

    rep_features = verify_pattern_feature_consistency(chart_patterns_db=chart_patterns_db)
    ok_features = bool((rep_features.get("summary") or {}).get("consistent"))
    reports["verify_pattern_feature_consistency"] = rep_features
    stages.append(_stage("verify_pattern_feature_consistency", rep_features, ok_features, not ok_features))

    rep_blobs = verify_pattern_blob_integrity(chart_patterns_db=chart_patterns_db)
    sum_blobs = rep_blobs.get("summary") or {}
    # if there are no blob rows, treat as OK for backward compatibility
    ok_blobs = bool(sum_blobs.get("consistent")) or int(sum_blobs.get("blob_rows") or 0) == 0
    reports["verify_pattern_blob_integrity"] = rep_blobs
    stages.append(_stage("verify_pattern_blob_integrity", rep_blobs, ok_blobs, not ok_blobs and int(sum_blobs.get("blob_rows") or 0) > 0))

    ok_reconcile = True
    if chart_asset_db is not None:
        rep_reconcile = verify_asset_pattern_reconciliation(
            chart_asset_db=chart_asset_db,
            chart_patterns_db=chart_patterns_db,
            file_scan_inventory_db=file_scan_inventory_db,
            sample_limit=20,
        )
        s = rep_reconcile.get("summary") or {}
        unreconciled = int(s.get("unreconciled_assets") or 0)
        insufficient = int(s.get("insufficient_identity_assets") or 0)
        ok_reconcile = unreconciled <= insufficient
        reports["verify_asset_pattern_reconciliation"] = rep_reconcile
        stages.append(_stage("verify_asset_pattern_reconciliation", rep_reconcile, ok_reconcile, not ok_reconcile))

    summary = PatternBundleSummary(
        chart_patterns_ok=ok_patterns,
        pattern_feature_consistency_ok=ok_features,
        pattern_blob_integrity_ok=ok_blobs,
        asset_pattern_reconciliation_ok=ok_reconcile,
        total_stage_failures=sum(1 for s in stages if not s.ok),
        total_issue_count=sum(s.issue_count for s in stages),
    )
    summary.all_ok = (
        summary.chart_patterns_ok and
        summary.pattern_feature_consistency_ok and
        summary.pattern_blob_integrity_ok and
        summary.asset_pattern_reconciliation_ok
    )

    return {
        "summary": asdict(summary),
        "stages": [asdict(s) for s in stages],
        "reports": reports,
    }


verify_all_chart_patterns = verify_pattern_bundle


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_pattern_bundle")
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--chart-assets-db", default=None)
    parser.add_argument("--file-scan-db", default=None)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_pattern_bundle(
        chart_patterns_db=Path(args.chart_patterns_db),
        chart_asset_db=Path(args.chart_assets_db) if args.chart_assets_db else None,
        file_scan_inventory_db=Path(args.file_scan_db) if args.file_scan_db else None,
    )
    summary = report.get("summary", {})
    print("[PATTERN BUNDLE] chart_patterns_ok=", summary.get("chart_patterns_ok"))
    print("[PATTERN BUNDLE] pattern_feature_consistency_ok=", summary.get("pattern_feature_consistency_ok"))
    print("[PATTERN BUNDLE] pattern_blob_integrity_ok=", summary.get("pattern_blob_integrity_ok"))
    print("[PATTERN BUNDLE] asset_pattern_reconciliation_ok=", summary.get("asset_pattern_reconciliation_ok"))
    print("[PATTERN BUNDLE] all_ok=", summary.get("all_ok"))
    print("[PATTERN BUNDLE] total_stage_failures=", summary.get("total_stage_failures"))
    print("[PATTERN BUNDLE] total_issue_count=", summary.get("total_issue_count"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("all_ok")) else 1


__all__ = ["verify_pattern_bundle", "verify_all_chart_patterns", "cli_main"]
