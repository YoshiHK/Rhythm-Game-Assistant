from __future__ import annotations

"""
verify_runtime_bundle_strict.py

Strict runtime DB verification for Phase 3.5 / Path A.

Recommended directory
---------------------
src/rhythm_ingestion/writers/verification/verify_runtime_bundle_strict.py

Purpose
-------
Verify the runtime DB bundle directly via SQLite (without depending on the
writer import graph):
- runtime/ingestions/file_scan_inventory.db
- runtime/assets/chart_assets.db
- runtime/features/chart_patterns.db

Design
------
- read-only
- deterministic
- DB-first
- safe for deployment / safe-delete gating
"""

import argparse
import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


# --------------------------------------------------
# Defaults
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
class StrictIssue:
    check: str
    severity: str
    message: str
    count: Optional[int] = None
    sample: List[str] = field(default_factory=list)


@dataclass
class StrictSummary:
    ok: bool = False
    inventory_ok: bool = False
    assets_ok: bool = False
    patterns_ok: bool = False
    coverage_ok: bool = False
    hashes_ok: bool = False
    type_a_usability_ok: bool = False
    counts_ok: bool = False

    inventory_count: int = 0
    asset_count: int = 0
    pattern_count: int = 0
    pattern_feature_count: int = 0
    pattern_blob_count: int = 0

    unique_inventory_source_paths: int = 0
    unique_asset_source_paths: int = 0
    unique_expected_pattern_chart_ids: int = 0

    missing_asset_coverage_count: int = 0
    unexpected_asset_coverage_count: int = 0
    missing_pattern_coverage_count: int = 0
    unexpected_pattern_coverage_count: int = 0

    missing_type_a_text_count: int = 0
    missing_type_a_hash_count: int = 0
    duplicate_inventory_source_path_count: int = 0
    duplicate_asset_source_path_count: int = 0

    issue_count: int = 0


# --------------------------------------------------
# SQLite helpers
# --------------------------------------------------
def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _view_exists(conn: sqlite3.Connection, view_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='view' AND name=? LIMIT 1",
        (view_name,),
    ).fetchone()
    return row is not None


def _fetch_count(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _fetch_strings(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> List[str]:
    rows = conn.execute(sql, params).fetchall()
    out: List[str] = []
    for r in rows:
        if not r:
            continue
        value = r[0]
        if value is None:
            continue
        out.append(str(value))
    return out


def _sample(values: Iterable[str], n: int = 5) -> List[str]:
    out: List[str] = []
    for x in values:
        out.append(str(x))
        if len(out) >= n:
            break
    return out


# --------------------------------------------------
# Identity helpers
# --------------------------------------------------
def _safe_chart_id_from_source_path(source_path: str) -> str:
    return hashlib.sha256(str(source_path).encode("utf-8")).hexdigest()


# --------------------------------------------------
# Core verification
# --------------------------------------------------
def verify_runtime_bundle_strict(
    *,
    file_scan_inventory_db: Path = DEFAULT_FILE_SCAN_DB,
    chart_asset_db: Path = DEFAULT_CHART_ASSET_DB,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERNS_DB,
) -> Dict[str, Any]:
    issues: List[StrictIssue] = []
    summary = StrictSummary()

    # --------------------------------------------------
    # Existence checks
    # --------------------------------------------------
    if not file_scan_inventory_db.exists():
        issues.append(StrictIssue(
            check="inventory_db_exists",
            severity="error",
            message=f"file_scan_inventory.db not found: {file_scan_inventory_db}",
        ))
    if not chart_asset_db.exists():
        issues.append(StrictIssue(
            check="asset_db_exists",
            severity="error",
            message=f"chart_assets.db not found: {chart_asset_db}",
        ))
    if not chart_patterns_db.exists():
        issues.append(StrictIssue(
            check="pattern_db_exists",
            severity="error",
            message=f"chart_patterns.db not found: {chart_patterns_db}",
        ))

    if issues:
        summary.issue_count = len(issues)
        return {
            "summary": asdict(summary),
            "issues": [asdict(x) for x in issues],
            "bundle": {
                "file_scan_inventory_db": str(file_scan_inventory_db),
                "chart_asset_db": str(chart_asset_db),
                "chart_patterns_db": str(chart_patterns_db),
            },
        }

    # --------------------------------------------------
    # Inventory DB checks
    # --------------------------------------------------
    inventory_source_paths: List[str] = []
    expected_pattern_chart_ids: List[str] = []
    with sqlite3.connect(str(file_scan_inventory_db)) as conn:
        if not _table_exists(conn, "file_scan_inventory"):
            issues.append(StrictIssue(
                check="inventory_table",
                severity="error",
                message="file_scan_inventory table not found",
            ))
        else:
            summary.inventory_count = _fetch_count(conn, "file_scan_inventory")
            inventory_source_paths = _fetch_strings(
                conn,
                "SELECT source_path FROM file_scan_inventory WHERE source_path IS NOT NULL"
            )
            summary.unique_inventory_source_paths = len(set(inventory_source_paths))
            dup_count = summary.inventory_count - summary.unique_inventory_source_paths
            summary.duplicate_inventory_source_path_count = max(0, dup_count)
            if dup_count > 0:
                issues.append(StrictIssue(
                    check="inventory_duplicate_source_paths",
                    severity="error",
                    message="Duplicate source_path values found in file_scan_inventory",
                    count=dup_count,
                    sample=_sample(inventory_source_paths),
                ))
            expected_pattern_chart_ids = [_safe_chart_id_from_source_path(p) for p in inventory_source_paths]
            summary.unique_expected_pattern_chart_ids = len(set(expected_pattern_chart_ids))

        # compat view is optional but useful signal
        if not _view_exists(conn, "scan_candidates"):
            issues.append(StrictIssue(
                check="scan_candidates_view",
                severity="warning",
                message="scan_candidates view not found in inventory DB",
            ))

    # --------------------------------------------------
    # Asset DB checks
    # --------------------------------------------------
    asset_source_paths: List[str] = []
    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            issues.append(StrictIssue(
                check="asset_table",
                severity="error",
                message="chart_assets table not found",
            ))
        else:
            summary.asset_count = _fetch_count(conn, "chart_assets")
            asset_source_paths = _fetch_strings(
                conn,
                "SELECT source_path FROM chart_assets WHERE source_path IS NOT NULL"
            )
            summary.unique_asset_source_paths = len(set(asset_source_paths))
            dup_count = summary.asset_count - summary.unique_asset_source_paths
            summary.duplicate_asset_source_path_count = max(0, dup_count)
            if dup_count > 0:
                issues.append(StrictIssue(
                    check="asset_duplicate_source_paths",
                    severity="error",
                    message="Duplicate source_path values found in chart_assets",
                    count=dup_count,
                    sample=_sample(asset_source_paths),
                ))

            missing_type_a_text = _fetch_count(conn, "chart_assets")
            missing_type_a_text = int(conn.execute(
                """
                SELECT COUNT(*) FROM chart_assets
                WHERE asset_type='type_A'
                  AND (text_representation IS NULL OR TRIM(text_representation)='')
                """
            ).fetchone()[0])
            summary.missing_type_a_text_count = missing_type_a_text
            if missing_type_a_text > 0:
                issues.append(StrictIssue(
                    check="type_a_text_usability",
                    severity="error",
                    message="type_A assets with missing/empty text_representation detected",
                    count=missing_type_a_text,
                ))

            missing_type_a_hash = int(conn.execute(
                """
                SELECT COUNT(*) FROM chart_assets
                WHERE asset_type='type_A'
                  AND (content_sha256 IS NULL OR TRIM(content_sha256)='')
                """
            ).fetchone()[0])
            summary.missing_type_a_hash_count = missing_type_a_hash
            if missing_type_a_hash > 0:
                issues.append(StrictIssue(
                    check="type_a_hash_presence",
                    severity="error",
                    message="type_A assets with missing content_sha256 detected",
                    count=missing_type_a_hash,
                ))

    # --------------------------------------------------
    # Pattern DB checks
    # --------------------------------------------------
    pattern_chart_ids: List[str] = []
    with sqlite3.connect(str(chart_patterns_db)) as conn:
        tables_ok = True
        for name in ("chart_patterns", "pattern_features", "pattern_blobs"):
            if not _table_exists(conn, name):
                tables_ok = False
                issues.append(StrictIssue(
                    check=f"pattern_table_{name}",
                    severity="error",
                    message=f"{name} table not found",
                ))

        if tables_ok:
            summary.pattern_count = _fetch_count(conn, "chart_patterns")
            summary.pattern_feature_count = _fetch_count(conn, "pattern_features")
            summary.pattern_blob_count = _fetch_count(conn, "pattern_blobs")
            pattern_chart_ids = _fetch_strings(
                conn,
                "SELECT chart_id FROM chart_patterns WHERE chart_id IS NOT NULL"
            )

            if summary.pattern_feature_count != summary.pattern_count:
                issues.append(StrictIssue(
                    check="pattern_feature_count_match",
                    severity="error",
                    message="pattern_features row count does not match chart_patterns row count",
                    count=summary.pattern_feature_count - summary.pattern_count,
                ))

            if summary.pattern_blob_count != summary.pattern_count:
                issues.append(StrictIssue(
                    check="pattern_blob_count_match",
                    severity="error",
                    message="pattern_blobs row count does not match chart_patterns row count",
                    count=summary.pattern_blob_count - summary.pattern_count,
                ))

    # --------------------------------------------------
    # Cross-DB coverage checks
    # --------------------------------------------------
    inventory_set = set(inventory_source_paths)
    asset_set = set(asset_source_paths)
    expected_pattern_set = set(expected_pattern_chart_ids)
    pattern_set = set(pattern_chart_ids)

    missing_assets = sorted(inventory_set - asset_set)
    unexpected_assets = sorted(asset_set - inventory_set)
    summary.missing_asset_coverage_count = len(missing_assets)
    summary.unexpected_asset_coverage_count = len(unexpected_assets)
    if missing_assets:
        issues.append(StrictIssue(
            check="inventory_to_assets_coverage",
            severity="error",
            message="Inventory files missing from chart_assets coverage",
            count=len(missing_assets),
            sample=_sample(missing_assets),
        ))
    if unexpected_assets:
        issues.append(StrictIssue(
            check="asset_to_inventory_coverage",
            severity="warning",
            message="chart_assets contains source_path values not present in inventory",
            count=len(unexpected_assets),
            sample=_sample(unexpected_assets),
        ))

    missing_patterns = sorted(expected_pattern_set - pattern_set)
    unexpected_patterns = sorted(pattern_set - expected_pattern_set)
    summary.missing_pattern_coverage_count = len(missing_patterns)
    summary.unexpected_pattern_coverage_count = len(unexpected_patterns)
    if missing_patterns:
        issues.append(StrictIssue(
            check="assets_to_patterns_coverage",
            severity="error",
            message="Expected pattern chart_id values missing from chart_patterns",
            count=len(missing_patterns),
            sample=_sample(missing_patterns),
        ))
    if unexpected_patterns:
        issues.append(StrictIssue(
            check="pattern_to_inventory_coverage",
            severity="warning",
            message="chart_patterns contains chart_id values not expected from inventory source_path hashing",
            count=len(unexpected_patterns),
            sample=_sample(unexpected_patterns),
        ))

    # --------------------------------------------------
    # Summary flags
    # --------------------------------------------------
    summary.inventory_ok = summary.inventory_count > 0 and not any(
        i.severity == "error" and i.check.startswith("inventory") for i in issues
    )
    summary.assets_ok = summary.asset_count > 0 and summary.missing_type_a_text_count == 0 and summary.missing_type_a_hash_count == 0 and summary.duplicate_asset_source_path_count == 0
    summary.patterns_ok = summary.pattern_count > 0 and summary.pattern_feature_count == summary.pattern_count and summary.pattern_blob_count == summary.pattern_count
    summary.coverage_ok = summary.missing_asset_coverage_count == 0 and summary.missing_pattern_coverage_count == 0
    summary.hashes_ok = summary.missing_type_a_hash_count == 0
    summary.type_a_usability_ok = summary.missing_type_a_text_count == 0
    summary.counts_ok = (
        summary.inventory_count == summary.asset_count == summary.pattern_count == summary.pattern_feature_count == summary.pattern_blob_count
    )
    summary.issue_count = len(issues)
    summary.ok = (
        summary.inventory_ok
        and summary.assets_ok
        and summary.patterns_ok
        and summary.coverage_ok
        and summary.hashes_ok
        and summary.type_a_usability_ok
        and summary.counts_ok
        and not any(i.severity == "error" for i in issues)
    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(x) for x in issues],
        "bundle": {
            "file_scan_inventory_db": str(file_scan_inventory_db),
            "chart_asset_db": str(chart_asset_db),
            "chart_patterns_db": str(chart_patterns_db),
            "recommended_directory": r"src\rhythm_ingestion\writers\verification\verify_runtime_bundle_strict.py",
        },
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_runtime_bundle_strict")
    parser.add_argument("--file-scan-db", default=str(DEFAULT_FILE_SCAN_DB))
    parser.add_argument("--chart-assets-db", default=str(DEFAULT_CHART_ASSET_DB))
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_runtime_bundle_strict(
        file_scan_inventory_db=Path(args.file_scan_db),
        chart_asset_db=Path(args.chart_assets_db),
        chart_patterns_db=Path(args.chart_patterns_db),
    )

    summary = report.get("summary", {})
    print("[STRICT VERIFY]")
    print("ok                     =", summary.get("ok"))
    print("inventory_ok           =", summary.get("inventory_ok"))
    print("assets_ok              =", summary.get("assets_ok"))
    print("patterns_ok            =", summary.get("patterns_ok"))
    print("coverage_ok            =", summary.get("coverage_ok"))
    print("counts_ok              =", summary.get("counts_ok"))
    print("type_a_usability_ok    =", summary.get("type_a_usability_ok"))
    print("hashes_ok              =", summary.get("hashes_ok"))
    print("inventory_count        =", summary.get("inventory_count"))
    print("asset_count            =", summary.get("asset_count"))
    print("pattern_count          =", summary.get("pattern_count"))
    print("pattern_feature_count  =", summary.get("pattern_feature_count"))
    print("pattern_blob_count     =", summary.get("pattern_blob_count"))
    print("issue_count            =", summary.get("issue_count"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("json_out               =", args.json_out)

    return 0 if bool(summary.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())
