from __future__ import annotations

"""
verify_full_bundle.py

Unified system-level verification entrypoint.

Purpose
-------
Verify full runtime bundle:

    file_scan_inventory → chart_assets → chart_patterns
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Imports (reuse existing verifiers)
# --------------------------------------------------

try:
    from rhythm_ingestion.writers.validators.inventory import (
        verify_file_scan_inventory,
        verify_inventory_asset_coverage,
    )
    from rhythm_ingestion.writers.validators.asset import (
        verify_asset_bundle,
    )
    from rhythm_ingestion.writers.validators.pattern import (
        verify_pattern_bundle,
    )
except Exception:
    # fallback
    from verify_file_scan_inventory import verify_file_scan_inventory
    from verify_inventory_asset_coverage import verify_inventory_asset_coverage
    from verify_asset_bundle import verify_asset_bundle
    from verify_pattern_bundle import verify_pattern_bundle


# --------------------------------------------------
# Defaults (runtime DB locations)
# --------------------------------------------------

DEFAULT_RUNTIME_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime"
)

DEFAULT_FILE_SCAN_DB = DEFAULT_RUNTIME_ROOT / "ingestions" / "file_scan_inventory.db"
DEFAULT_CHART_ASSET_DB = DEFAULT_RUNTIME_ROOT / "assets" / "chart_assets.db"
DEFAULT_CHART_PATTERNS_DB = DEFAULT_RUNTIME_ROOT / "features" / "chart_patterns.db"


# --------------------------------------------------
# Models
# --------------------------------------------------

@dataclass
class FullBundleStage:
    stage: str
    ok: bool
    issue_count: int
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FullBundleSummary:
    inventory_ok: bool = False
    inventory_asset_coverage_ok: bool = False
    asset_bundle_ok: bool = False
    pattern_bundle_ok: bool = False

    all_ok: bool = False
    total_stage_failures: int = 0
    total_issue_count: int = 0


# --------------------------------------------------
# Core bundle
# --------------------------------------------------

def verify_full_bundle(
    *,
    file_scan_inventory_db: Path = DEFAULT_FILE_SCAN_DB,
    chart_asset_db: Path = DEFAULT_CHART_ASSET_DB,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERNS_DB,
) -> Dict[str, Any]:

    # ✅ FIX: build bundle_meta INSIDE function
    bundle_meta = {
        "file_scan_inventory_db": str(file_scan_inventory_db),
        "chart_asset_db": str(chart_asset_db),
        "chart_patterns_db": str(chart_patterns_db),
    }

    stages: List[FullBundleStage] = []
    reports: Dict[str, Dict[str, Any]] = {}

    # --------------------------------------------------
    # inventory
    # --------------------------------------------------
    rep_inventory = verify_file_scan_inventory(
        file_scan_inventory_db=file_scan_inventory_db
    )
    ok_inventory = bool((rep_inventory.get("summary") or {}).get("usable"))

    reports["verify_file_scan_inventory"] = rep_inventory
    stages.append(
        FullBundleStage(
            stage="verify_file_scan_inventory",
            ok=ok_inventory,
            issue_count=len(rep_inventory.get("issues") or []),
            summary=rep_inventory.get("summary") or {},
        )
    )

    # --------------------------------------------------
    # coverage
    # --------------------------------------------------
    rep_cov = verify_inventory_asset_coverage(
        file_scan_inventory_db=file_scan_inventory_db,
        chart_asset_db=chart_asset_db,
    )
    ok_cov = bool((rep_cov.get("summary") or {}).get("consistent"))

    reports["verify_inventory_asset_coverage"] = rep_cov
    stages.append(
        FullBundleStage(
            stage="verify_inventory_asset_coverage",
            ok=ok_cov,
            issue_count=len(rep_cov.get("issues") or []),
            summary=rep_cov.get("summary") or {},
        )
    )

    # --------------------------------------------------
    # asset
    # --------------------------------------------------
    rep_asset = verify_asset_bundle(
        chart_asset_db=chart_asset_db,
    )
    ok_asset = bool((rep_asset.get("summary") or {}).get("all_ok"))

    reports["verify_asset_bundle"] = rep_asset
    stages.append(
        FullBundleStage(
            stage="verify_asset_bundle",
            ok=ok_asset,
            issue_count=len(rep_asset.get("issues") or []),
            summary=rep_asset.get("summary") or {},
        )
    )

    # --------------------------------------------------
    # pattern
    # --------------------------------------------------
    rep_pattern = verify_pattern_bundle(
        chart_patterns_db=chart_patterns_db,
        chart_asset_db=chart_asset_db,
        file_scan_inventory_db=file_scan_inventory_db,
    )
    ok_pattern = bool((rep_pattern.get("summary") or {}).get("all_ok"))

    reports["verify_pattern_bundle"] = rep_pattern
    stages.append(
        FullBundleStage(
            stage="verify_pattern_bundle",
            ok=ok_pattern,
            issue_count=len(rep_pattern.get("issues") or []),
            summary=rep_pattern.get("summary") or {},
        )
    )

    # --------------------------------------------------
    # summary
    # --------------------------------------------------
    summary = FullBundleSummary(
        inventory_ok=ok_inventory,
        inventory_asset_coverage_ok=ok_cov,
        asset_bundle_ok=ok_asset,
        pattern_bundle_ok=ok_pattern,
        total_stage_failures=sum(1 for s in stages if not s.ok),
        total_issue_count=sum(s.issue_count for s in stages),
    )

    summary.all_ok = (
        summary.inventory_ok
        and summary.inventory_asset_coverage_ok
        and summary.asset_bundle_ok
        and summary.pattern_bundle_ok
    )

    return {
        "summary": asdict(summary),
        "stages": [asdict(s) for s in stages],
        "reports": reports,
        "bundle": bundle_meta,
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------

def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_full_bundle")

    parser.add_argument("--file-scan-db", default=str(DEFAULT_FILE_SCAN_DB))
    parser.add_argument("--chart-assets-db", default=str(DEFAULT_CHART_ASSET_DB))
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--json-out", default=None)

    args = parser.parse_args(argv)

    report = verify_full_bundle(
        file_scan_inventory_db=Path(args.file_scan_db),
        chart_asset_db=Path(args.chart_assets_db),
        chart_patterns_db=Path(args.chart_patterns_db),
    )

    summary = report.get("summary", {})

    print("\n[BUNDLE]")
    print("file_scan_inventory_db =", args.file_scan_db)
    print("chart_assets_db        =", args.chart_assets_db)
    print("chart_patterns_db      =", args.chart_patterns_db)

    print("\n[FULL BUNDLE]")
    print("inventory_ok =", summary.get("inventory_ok"))
    print("coverage_ok  =", summary.get("inventory_asset_coverage_ok"))
    print("asset_ok     =", summary.get("asset_bundle_ok"))
    print("pattern_ok   =", summary.get("pattern_bundle_ok"))
    print("all_ok       =", summary.get("all_ok"))
    print("failures     =", summary.get("total_stage_failures"))
    print("issues       =", summary.get("total_issue_count"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)

    return 0 if bool(summary.get("all_ok")) else 1


__all__ = [
    "verify_full_bundle",
    "cli_main",
]


if __name__ == "__main__":
    raise SystemExit(cli_main())