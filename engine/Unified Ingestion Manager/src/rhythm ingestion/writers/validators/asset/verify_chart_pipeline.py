from __future__ import annotations

"""
verify_chart_pipeline.py

System-level verification for the chart pipeline.

Purpose
-------
This verifier sits ABOVE asset validation. It checks whether the chart pipeline
is usable in practice, without mutating any database or completed phase logic.

What it verifies
----------------
1) chart_assets.db integrity (delegates to verify_chart_assets)
2) chart_patterns.db presence + readable schema / rows
3) bridge-layer smoke checks against existing chart_pattern rows
4) optional inventory coverage via file_scan_inventory.db

Important
---------
- read-only only
- no conversion / no persistence
- intended for verification, not validation
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.validators.verify_chart_assets import verify_chart_assets
except ImportError:
    try:
        from .verify_chart_assets import verify_chart_assets
    except Exception:
        try:
            from verify_chart_assets import verify_chart_assets
        except Exception:
            verify_chart_assets = None  # type: ignore

try:
    from rhythm_ingestion.writers.readers.chart_pattern_reader import (
        DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB,
    )
except ImportError:
    try:
        from ..readers.chart_pattern_reader import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB
    except Exception:
        try:
            from chart_pattern_reader import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB
        except Exception:
            DEFAULT_CHART_PATTERN_DB = Path("chart_patterns.db")  # type: ignore

try:
    from rhythm_ingestion.writers.bridges.chart_feature_bridge import (
        build_chart_pattern_feature_payload,
    )
except ImportError:
    try:
        from ..bridges.chart_feature_bridge import build_chart_pattern_feature_payload
    except Exception:
        try:
            from chart_feature_bridge import build_chart_pattern_feature_payload
        except Exception:
            build_chart_pattern_feature_payload = None  # type: ignore

try:
    from rhythm_ingestion.writers.orchestrators.chart_asset_ingestion_orchestrator import (
        ingest_chart_assets_from_file_scan_candidates,
    )
except ImportError:
    try:
        from ..orchestrators.chart_asset_ingestion_orchestrator import (
            ingest_chart_assets_from_file_scan_candidates,
        )
    except Exception:
        try:
            from chart_asset_ingestion_orchestrator import ingest_chart_assets_from_file_scan_candidates
        except Exception:
            ingest_chart_assets_from_file_scan_candidates = None  # type: ignore


DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")
DEFAULT_FILE_SCAN_INVENTORY_DB = Path("file_scan_inventory.db")


# --------------------------------------------------
# DB helpers
# --------------------------------------------------
def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_rows(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(r) for r in rows]


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    if not _table_exists(conn, table_name):
        return []
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(r[1]) for r in rows]


def _best_available_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    colset = {str(c) for c in columns}
    for c in candidates:
        if c in colset:
            return c
    return None


def _choose_pattern_table(conn: sqlite3.Connection) -> Optional[str]:
    for name in ("chart_patterns", "chart_pattern_features", "patterns"):
        if _table_exists(conn, name):
            return name
    return None


# --------------------------------------------------
# Report models
# --------------------------------------------------
@dataclass
class PipelineVerifyIssue:
    severity: str  # error / warning
    code: str
    table: Optional[str] = None
    chart_id: Optional[str] = None
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineVerifySummary:
    assets_verified: bool = False
    asset_invalid_count: int = 0
    asset_warning_count: int = 0
    asset_total: int = 0

    patterns_db_present: bool = False
    pattern_table: Optional[str] = None
    pattern_rows: int = 0
    pattern_unique_chart_ids: int = 0
    pattern_read_errors: int = 0

    bridge_import_ok: bool = False
    bridge_smoke_attempts: int = 0
    bridge_smoke_passed: int = 0
    bridge_smoke_failed: int = 0

    orchestrator_import_ok: bool = False

    coverage_expected: Optional[int] = None
    coverage_found: Optional[int] = None
    coverage_missing: Optional[int] = None

    pipeline_usable: bool = False


# --------------------------------------------------
# Pattern DB verification
# --------------------------------------------------
def _verify_chart_patterns_db(
    *,
    chart_patterns_db: Path,
    sample_limit: int,
) -> Tuple[Dict[str, Any], List[PipelineVerifyIssue], List[Dict[str, Any]]]:
    issues: List[PipelineVerifyIssue] = []
    summary: Dict[str, Any] = {
        "patterns_db_present": False,
        "pattern_table": None,
        "pattern_rows": 0,
        "pattern_unique_chart_ids": 0,
        "pattern_read_errors": 0,
    }
    sample_rows: List[Dict[str, Any]] = []

    if not chart_patterns_db.exists():
        issues.append(
            PipelineVerifyIssue(
                severity="warning",
                code="chart_patterns_db_missing",
                details={"path": str(chart_patterns_db)},
            )
        )
        return summary, issues, sample_rows

    summary["patterns_db_present"] = True

    with sqlite3.connect(str(chart_patterns_db)) as conn:
        table = _choose_pattern_table(conn)
        if not table:
            issues.append(
                PipelineVerifyIssue(
                    severity="error",
                    code="pattern_table_missing",
                    details={"path": str(chart_patterns_db)},
                )
            )
            return summary, issues, sample_rows

        summary["pattern_table"] = table
        columns = _get_table_columns(conn, table)
        id_col = _best_available_column(columns, ("normalized_chart_id", "chart_id"))
        if id_col is None:
            issues.append(
                PipelineVerifyIssue(
                    severity="error",
                    code="pattern_id_column_missing",
                    table=table,
                )
            )
            return summary, issues, sample_rows

        try:
            rows = _get_rows(conn, table)
        except Exception as e:
            summary["pattern_read_errors"] += 1
            issues.append(
                PipelineVerifyIssue(
                    severity="error",
                    code="pattern_table_read_failed",
                    table=table,
                    details={"message": f"{type(e).__name__}: {e}"},
                )
            )
            return summary, issues, sample_rows

        summary["pattern_rows"] = len(rows)
        summary["pattern_unique_chart_ids"] = len(
            {str(r.get(id_col)) for r in rows if r.get(id_col) is not None}
        )

        sample_rows = rows[:sample_limit]

        if len(rows) == 0:
            issues.append(
                PipelineVerifyIssue(
                    severity="warning",
                    code="pattern_table_empty",
                    table=table,
                )
            )

    return summary, issues, sample_rows


# --------------------------------------------------
# Bridge smoke verification
# --------------------------------------------------
def _verify_bridge_smoke(
    *,
    chart_patterns_db: Path,
    sample_rows: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[PipelineVerifyIssue]]:
    issues: List[PipelineVerifyIssue] = []
    summary = {
        "bridge_import_ok": build_chart_pattern_feature_payload is not None,
        "bridge_smoke_attempts": 0,
        "bridge_smoke_passed": 0,
        "bridge_smoke_failed": 0,
    }

    if build_chart_pattern_feature_payload is None:
        issues.append(
            PipelineVerifyIssue(
                severity="warning",
                code="bridge_import_unavailable",
            )
        )
        return summary, issues

    for row in sample_rows:
        chart_id = row.get("normalized_chart_id") or row.get("chart_id")
        if chart_id is None:
            continue

        summary["bridge_smoke_attempts"] += 1
        try:
            payload = build_chart_pattern_feature_payload(
                chart_id=str(chart_id),
                game=row.get("game"),
                song_id=row.get("song_id"),
                difficulty=row.get("difficulty"),
                chart_type=row.get("chart_type"),
                level=row.get("level"),
                db_path=chart_patterns_db,
                candidate_or_event=row,
            )

            features = payload.get("chart_pattern_features", {}) if isinstance(payload, dict) else {}
            status = features.get("chart_pattern_status")
            has_feat = bool(features.get("has_chart_pattern_features"))

            if has_feat or status == "VALID":
                summary["bridge_smoke_passed"] += 1
            else:
                summary["bridge_smoke_failed"] += 1
                issues.append(
                    PipelineVerifyIssue(
                        severity="warning",
                        code="bridge_smoke_missing_features",
                        chart_id=str(chart_id),
                        details={
                            "status": status,
                        },
                    )
                )
        except Exception as e:
            summary["bridge_smoke_failed"] += 1
            issues.append(
                PipelineVerifyIssue(
                    severity="error",
                    code="bridge_smoke_exception",
                    chart_id=str(chart_id),
                    details={"message": f"{type(e).__name__}: {e}"},
                )
            )

    return summary, issues


# --------------------------------------------------
# Public verification
# --------------------------------------------------
def verify_chart_pipeline(
    *,
    chart_asset_db: Path = DEFAULT_CHART_ASSET_DB,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERN_DB,
    file_scan_inventory_db: Optional[Path] = None,
    sample_limit: int = 20,
) -> Dict[str, Any]:
    issues: List[PipelineVerifyIssue] = []
    summary = PipelineVerifySummary()

    # 1) asset verification (delegated)
    if verify_chart_assets is None:
        issues.append(
            PipelineVerifyIssue(
                severity="error",
                code="verify_chart_assets_import_unavailable",
            )
        )
    else:
        asset_report = verify_chart_assets(
            chart_asset_db=chart_asset_db,
            file_scan_inventory_db=file_scan_inventory_db,
            sample_limit=sample_limit,
        )
        asset_summary = asset_report.get("summary", {})
        summary.assets_verified = True
        summary.asset_invalid_count = int(asset_summary.get("invalid_assets") or 0)
        summary.asset_warning_count = int(asset_summary.get("warning_assets") or 0)
        summary.asset_total = int(asset_summary.get("total_assets") or 0)
        summary.coverage_expected = asset_summary.get("coverage_expected")
        summary.coverage_found = asset_summary.get("coverage_found")
        summary.coverage_missing = asset_summary.get("coverage_missing")

        for issue in asset_report.get("issues", []):
            issues.append(
                PipelineVerifyIssue(
                    severity=str(issue.get("severity") or "warning"),
                    code=f"asset::{issue.get('code')}",
                    asset_id=issue.get("asset_id"),
                    candidate_id=issue.get("candidate_id"),
                    details=issue.get("details") or {},
                )
            )

    # 2) pattern DB verification
    pattern_summary, pattern_issues, sample_rows = _verify_chart_patterns_db(
        chart_patterns_db=chart_patterns_db,
        sample_limit=sample_limit,
    )
    issues.extend(pattern_issues)
    summary.patterns_db_present = bool(pattern_summary.get("patterns_db_present"))
    summary.pattern_table = pattern_summary.get("pattern_table")
    summary.pattern_rows = int(pattern_summary.get("pattern_rows") or 0)
    summary.pattern_unique_chart_ids = int(pattern_summary.get("pattern_unique_chart_ids") or 0)
    summary.pattern_read_errors = int(pattern_summary.get("pattern_read_errors") or 0)

    # 3) bridge smoke verification
    bridge_summary, bridge_issues = _verify_bridge_smoke(
        chart_patterns_db=chart_patterns_db,
        sample_rows=sample_rows,
    )
    issues.extend(bridge_issues)
    summary.bridge_import_ok = bool(bridge_summary.get("bridge_import_ok"))
    summary.bridge_smoke_attempts = int(bridge_summary.get("bridge_smoke_attempts") or 0)
    summary.bridge_smoke_passed = int(bridge_summary.get("bridge_smoke_passed") or 0)
    summary.bridge_smoke_failed = int(bridge_summary.get("bridge_smoke_failed") or 0)

    # 4) orchestrator import availability
    summary.orchestrator_import_ok = ingest_chart_assets_from_file_scan_candidates is not None
    if not summary.orchestrator_import_ok:
        issues.append(
            PipelineVerifyIssue(
                severity="warning",
                code="orchestrator_import_unavailable",
            )
        )

    # Final pipeline usability heuristic
    summary.pipeline_usable = (
        summary.assets_verified
        and summary.asset_invalid_count == 0
        and summary.pattern_read_errors == 0
        and (not summary.patterns_db_present or summary.pattern_rows >= 0)
        and (summary.bridge_smoke_attempts == 0 or summary.bridge_smoke_failed == 0)
    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_chart_pipeline")
    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
        help=f"Path to chart_assets.db (default: {DEFAULT_CHART_ASSET_DB})",
    )
    parser.add_argument(
        "--chart-patterns-db",
        default=str(DEFAULT_CHART_PATTERN_DB),
        help=f"Path to chart_patterns.db (default: {DEFAULT_CHART_PATTERN_DB})",
    )
    parser.add_argument(
        "--file-scan-db",
        default=None,
        help="Optional path to file_scan_inventory.db for coverage verification",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write JSON verification report",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Max number of rows to use for smoke verification",
    )

    args = parser.parse_args(argv)

    report = verify_chart_pipeline(
        chart_asset_db=Path(args.chart_assets_db),
        chart_patterns_db=Path(args.chart_patterns_db),
        file_scan_inventory_db=Path(args.file_scan_db) if args.file_scan_db else None,
        sample_limit=int(args.sample_limit),
    )

    summary = report.get("summary", {})
    print("[PIPELINE VERIFY] assets_verified=", summary.get("assets_verified"))
    print("[PIPELINE VERIFY] asset_total=", summary.get("asset_total"))
    print("[PIPELINE VERIFY] asset_invalid_count=", summary.get("asset_invalid_count"))
    print("[PIPELINE VERIFY] asset_warning_count=", summary.get("asset_warning_count"))
    print("[PIPELINE VERIFY] patterns_db_present=", summary.get("patterns_db_present"))
    print("[PIPELINE VERIFY] pattern_table=", summary.get("pattern_table"))
    print("[PIPELINE VERIFY] pattern_rows=", summary.get("pattern_rows"))
    print("[PIPELINE VERIFY] bridge_import_ok=", summary.get("bridge_import_ok"))
    print("[PIPELINE VERIFY] bridge_smoke_attempts=", summary.get("bridge_smoke_attempts"))
    print("[PIPELINE VERIFY] bridge_smoke_passed=", summary.get("bridge_smoke_passed"))
    print("[PIPELINE VERIFY] bridge_smoke_failed=", summary.get("bridge_smoke_failed"))
    print("[PIPELINE VERIFY] orchestrator_import_ok=", summary.get("orchestrator_import_ok"))
    print("[PIPELINE VERIFY] pipeline_usable=", summary.get("pipeline_usable"))
    if summary.get("coverage_expected") is not None:
        print("[PIPELINE VERIFY] coverage_expected=", summary.get("coverage_expected"))
        print("[PIPELINE VERIFY] coverage_found=", summary.get("coverage_found"))
        print("[PIPELINE VERIFY] coverage_missing=", summary.get("coverage_missing"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("[PIPELINE VERIFY] report_written=", args.json_out)

    # non-zero if assets invalid or pipeline unusable
    return 0 if bool(summary.get("pipeline_usable")) else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_chart_pipeline",
    "cli_main",
]
