from __future__ import annotations

"""
safe_delete_candidates.py

Policy-driven safe pruning utility for chart source files.

Purpose
-------
Prune VERIFIED chart files only after verification passes, while preserving at
least one on-disk survivor per duplicate group by default.

Safety model
------------
- verification gate required by default
- dry-run first
- quarantine move (reversible) instead of permanent delete
- explicit file list only
- keep at least one surviving copy per duplicate group by default
- type_A-only pruning by default

Recommended layer
-----------------
writers/safety/safe_delete_candidates.py
"""

import argparse
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# --------------------------------------------------
# Imports (support package / relative / flat fallback)
# --------------------------------------------------

# FULL bundle (primary)
try:
    from writers.verification.verify_full_bundle import verify_full_bundle
except ImportError:
    try:
        from ..validators.verify_full_bundle import verify_full_bundle
    except Exception:
        from verify_full_bundle import verify_full_bundle
        
# ⚠️ legacy (asset-only verification, fallback only)      
try:
    from rhythm_ingestion.writers.validators import verify_asset_bundle
except ImportError:
    try:
        from ..validators import verify_asset_bundle
    except Exception:
        try:
            from writers.validators import verify_asset_bundle
        except Exception:
            from verify_asset_bundle import verify_asset_bundle  # type: ignore        


# --------------------------------------------------
# Default DB paths (runtime-aligned)
# --------------------------------------------------

DEFAULT_RUNTIME_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime"
)

DEFAULT_CHART_ASSET_DB = DEFAULT_RUNTIME_ROOT / "assets" / "chart_assets.db"
DEFAULT_CHART_PATTERNS_DB = DEFAULT_RUNTIME_ROOT / "features" / "chart_patterns.db"
DEFAULT_FILE_SCAN_INVENTORY_DB = DEFAULT_RUNTIME_ROOT / "ingestions" / "file_scan_inventory.db"

# --------------------------------------------------
# Models
# --------------------------------------------------
@dataclass
class DeletePolicy:
    require_verification: bool = True
    keep_at_least_one_copy: bool = True
    only_type_a: bool = True
    dry_run: bool = True
    action_mode: str = "quarantine"  # current supported mode


@dataclass
class DeleteAction:
    action: str  # keep / quarantine / skip / error
    source_path: str
    reason: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    group_key: Optional[str] = None
    target_path: Optional[str] = None


@dataclass
class DeleteSummary:
    dry_run: bool = True
    verification_passed: bool = False
    total_requested: int = 0
    total_known_assets: int = 0
    total_groups: int = 0

    keep_count: int = 0
    quarantine_count: int = 0
    skip_count: int = 0
    error_count: int = 0

    quarantine_dir: Optional[str] = None


# --------------------------------------------------
# SQLite helpers
# --------------------------------------------------
def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_rows(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------
# Asset lookup / grouping helpers
# --------------------------------------------------
def _source_key(p: Path | str) -> str:
    """
    Normalize source path for cross-layer matching.

    Ensures consistency across:
    - inventory
    - asset DB
    - pattern DB
    """
    try:
        return str(Path(p).resolve())
    except Exception:
        return str(p)


def _build_asset_index(chart_asset_db: Path) -> Dict[str, Dict[str, Any]]:
    if not chart_asset_db.exists():
        raise FileNotFoundError(f"chart asset db not found: {chart_asset_db}")

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table not found")
        rows = _get_rows(conn, "chart_assets")

    by_source: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        source_path = row.get("source_path")
        if not source_path:
            continue
        by_source[_source_key(source_path)] = row
    return by_source
    
# --------------------------------------------------
# Candidate generation (DB-driven)
# --------------------------------------------------

def generate_delete_candidates_from_DB(
    *,
    file_scan_inventory_db: Path,
    chart_asset_db: Path,
    only_type_a: bool = True,
) -> List[Path]:
    """
    Generate delete candidate paths from DB comparison.

    Strategy
    --------
    inventory (all scanned files)
    MINUS
    asset_index (all known/ingested assets)
    =
    deletion candidates

    Notes
    -----
    - does NOT perform verification
    - does NOT perform deletion
    - only returns candidate file paths
    """

    if not file_scan_inventory_db.exists():
        raise FileNotFoundError(f"file_scan_inventory_db not found: {file_scan_inventory_db}")

    if not chart_asset_db.exists():
        raise FileNotFoundError(f"chart_asset_db not found: {chart_asset_db}")

    # ------------------------------------------
    # load inventory
    # ------------------------------------------
    with sqlite3.connect(str(file_scan_inventory_db)) as conn:
        if not _table_exists(conn, "file_scan_inventory"):
            raise ValueError("file_scan_inventory table not found")

        rows = _get_rows(conn, "file_scan_inventory")

    inventory_paths: List[str] = []
    for row in rows:
        p = row.get("source_path") or row.get("path") or row.get("file_path")
        if not p:
            continue
        try:
            inventory_paths.append(_source_key(p))
        except Exception:
            continue

    # ------------------------------------------
    # load assets
    # ------------------------------------------
    asset_index = _build_asset_index(chart_asset_db)

    asset_keys = set(asset_index.keys())

    # ------------------------------------------
    # filter candidates
    # ------------------------------------------
    candidates: List[Path] = []

    for sk in inventory_paths:
        if sk in asset_keys:
            continue

        # optional type filtering
        if only_type_a:
            # we cannot directly know type from inventory
            # → rely on absence in asset DB (already type_A ingestion result)
            pass

        try:
            candidates.append(Path(sk))
        except Exception:
            continue

    return candidates
    
# --------------------------------------------------
# Smart filtering (non-destructive)
# --------------------------------------------------
def filter_delete_candidates(
    *,
    candidates: List[Path],
    chart_asset_db: Path,
    exclude_recent_days: Optional[int] = None,
    include_games: Optional[List[str]] = None,
) -> List[Path]:
    """
    Apply smart filtering to candidate delete list.

    IMPORTANT:
    - does NOT mutate DB
    - does NOT perform deletion
    - only filters candidate list

    Parameters
    ----------
    candidates:
        Output from generate_delete_candidates_from_DB()

    exclude_recent_days:
        Skip files modified within the last N days

    include_games:
        Restrict to specific game_ids
    """

    if not candidates:
        return []

    filtered: List[Path] = []

    # ------------------------------------------
    # optional: recent file filter
    # ------------------------------------------
    recent_cutoff_ts = None
    if exclude_recent_days is not None:
        import time
        seconds = int(exclude_recent_days) * 86400
        recent_cutoff_ts = time.time() - seconds

    # ------------------------------------------
    # load asset metadata for enrichment
    # ------------------------------------------
    asset_index = _build_asset_index(chart_asset_db)

    def _key(p: Path):
        return _source_key(p)

    for path in candidates:

        sk = _key(path)

        # ------------------------------------------
        # filter 1: recent files
        # ------------------------------------------
        if recent_cutoff_ts is not None:
            try:
                if path.exists():
                    mtime = path.stat().st_mtime
                    if mtime >= recent_cutoff_ts:
                        continue
            except Exception:
                pass

        # ------------------------------------------
        # filter 2: game-based filtering
        # ------------------------------------------
        if include_games:
            row = asset_index.get(sk)

            if row:
                game = row.get("game_normalized") or row.get("game_id")
                if game and game not in include_games:
                    continue

        filtered.append(path)

    return filtered


def _group_key_for_asset(row: Dict[str, Any]) -> Optional[str]:
    """
    Prefer content hash for duplicate grouping.
    Fall back to normalized source path when no hash is available.
    """
    asset_type = str(row.get("asset_type") or "")
    content_sha256 = row.get("content_sha256")
    source_path = row.get("source_path")

    if asset_type == "type_A" and content_sha256:
        return f"sha256:{content_sha256}"

    if source_path:
        asset_id = row.get("asset_id")
        return f"path:{_source_key(source_path)}:{asset_id}"

    return None

def _choose_survivor(rows: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Deterministic survivor selection:
    - lexicographically smallest resolved source_path wins
    """
    if not rows:
        return None
    ordered = sorted(
        rows,
        key=lambda r: _source_key(str(r.get("source_path") or "")).casefold(),
    )
    return ordered[0]


# --------------------------------------------------
# Core
# --------------------------------------------------
def safe_delete_candidates(
    *,
    paths: List[Path],
    chart_asset_db: Path,
    chart_patterns_db: Optional[Path] = None,
    file_scan_inventory_db: Optional[Path] = None,
    policy_path: Optional[Path] = None,
    dry_run: bool = True,
    require_verification: bool = True,
    verify_report: Optional[Dict[str, Any]] = None,
    quarantine_dir: Optional[Path] = None,
    keep_at_least_one_copy: bool = True,
    only_type_a: bool = True,
) -> Dict[str, Any]:

    # ------------------------------------------
    # policy loading
    # ------------------------------------------
    policy_config = _load_policy_config(policy_path)

    try:
        from rhythm_ingestion.writers.validators import validate_delete_policy
    except Exception:
        from writers.validators import validate_delete_policy

    policy_validation = validate_delete_policy(policy_config)

    if not policy_validation["valid"]:
        raise ValueError(
            "Invalid delete policy",
            policy_validation["issues"],
        )

    if policy_validation["issues"]:
        print("[DELETE POLICY WARNINGS]")
        for issue in policy_validation["issues"]:
            if issue.get("severity") != "error":
                print(" ", issue)

    # ------------------------------------------
    # merge policy
    # ------------------------------------------
    dedup_cfg = policy_config.get("deduplication", {})
    keep_at_least_one_copy = dedup_cfg.get(
        "keep_at_least_one_copy",
        keep_at_least_one_copy,
    )

    max_copies_to_keep = dedup_cfg.get("max_copies_to_keep", 1)

    scope_cfg = policy_config.get("scope", {})
    only_type_a = scope_cfg.get("only_type_A", only_type_a)

    action_cfg = policy_config.get("action", {})

    if not quarantine_dir:
        qd = action_cfg.get("quarantine_dir")
        if isinstance(qd, str) and qd:
            quarantine_dir = chart_asset_db.parent / qd

    allow_delete_last_copy = action_cfg.get("allow_delete_last_copy", False)

    if allow_delete_last_copy:
        keep_at_least_one_copy = False

    policy = DeletePolicy(
        require_verification=require_verification,
        keep_at_least_one_copy=keep_at_least_one_copy,
        only_type_a=only_type_a,
        dry_run=dry_run,
        action_mode="quarantine",
    )

    # --------------------------------------------------
    # 1) STRICT Verification gate (NO FALLBACK)
    # --------------------------------------------------
    verification_passed = False

    if policy.require_verification:
        print("[SAFE DELETE] Running full system verification...")

        if verify_report is not None:
            v_summary = verify_report.get("summary", {})
            verification_passed = bool(
                v_summary.get("all_ok") or v_summary.get("deletion_safe")
            )
        else:
            # ✅ STRICT: no fallback allowed
            full_report = verify_full_bundle(
                file_scan_inventory_db=file_scan_inventory_db or DEFAULT_FILE_SCAN_INVENTORY_DB,
                chart_asset_db=chart_asset_db,
                chart_patterns_db=chart_patterns_db or DEFAULT_CHART_PATTERNS_DB,
            )

            full_summary = full_report.get("summary", {})

            verification_passed = bool(full_summary.get("all_ok"))

            if not verification_passed:
                print("[SAFE DELETE] ❌ FULL VERIFICATION FAILED")
                print("  inventory_ok =", full_summary.get("inventory_ok"))
                print("  coverage_ok  =", full_summary.get("inventory_asset_coverage_ok"))
                print("  asset_ok     =", full_summary.get("asset_bundle_ok"))
                print("  pattern_ok   =", full_summary.get("pattern_bundle_ok"))
                print("  failures     =", full_summary.get("total_stage_failures"))

        if not verification_passed:
            raise RuntimeError(
                "Deletion blocked: full bundle verification failed"
            )

        print("[SAFE DELETE] ✅ Verification passed")
    else:
        verification_passed = True

    # --------------------------------------------------
    # 2) Resolve requested assets
    # --------------------------------------------------
    asset_index = _build_asset_index(chart_asset_db)

    def _normalize_key(p: Path | str) -> str:
        try:
            return str(Path(p).resolve()).casefold()
        except Exception:
            return str(p).casefold()

    requested_keys = [_normalize_key(p) for p in paths]

    known_rows: List[Dict[str, Any]] = []
    actions: List[DeleteAction] = []

    for sk in requested_keys:
        row = asset_index.get(sk)

        if row is None:
            actions.append(
                DeleteAction(
                    action="skip",
                    source_path=sk,
                    reason="not_found_in_chart_assets",
                )
            )
            continue

        asset_type = str(row.get("asset_type") or "")

        if policy.only_type_a and asset_type != "type_A":
            actions.append(
                DeleteAction(
                    action="skip",
                    source_path=sk,
                    reason="non_type_A_asset_skipped",
                    asset_id=row.get("asset_id"),
                    candidate_id=row.get("candidate_id"),
                )
            )
            continue

        known_rows.append(row)

    # --------------------------------------------------
    # 3) Group by duplicate key
    # --------------------------------------------------
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for row in known_rows:
        gk = _group_key_for_asset(row)

        if gk is None:
            actions.append(
                DeleteAction(
                    action="skip",
                    source_path=str(row.get("source_path") or ""),
                    reason="missing_group_key",
                    asset_id=row.get("asset_id"),
                    candidate_id=row.get("candidate_id"),
                )
            )
            continue

        groups.setdefault(gk, []).append(row)

    quarantine_dir = quarantine_dir or (chart_asset_db.parent / "_quarantine_deleted")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 4) Decide actions per group
    # --------------------------------------------------
    for gk, rows in sorted(groups.items(), key=lambda kv: kv[0].casefold()):
        survivor = _choose_survivor(rows)

        if len(rows) == 1 and policy.keep_at_least_one_copy:
            row = rows[0]
            actions.append(
                DeleteAction(
                    action="keep",
                    source_path=str(row.get("source_path") or ""),
                    reason="last_copy_preserved",
                    asset_id=row.get("asset_id"),
                    candidate_id=row.get("candidate_id"),
                    group_key=gk,
                )
            )
            continue

        for row in rows:
            source_path = Path(str(row.get("source_path") or ""))

            source_key = _normalize_key(source_path)
            survivor_key = (
                _normalize_key(survivor.get("source_path"))
                if survivor else None
            )

            if policy.keep_at_least_one_copy and survivor_key == source_key:
                actions.append(
                    DeleteAction(
                        action="keep",
                        source_path=str(source_path),
                        reason="survivor_copy_preserved",
                        asset_id=row.get("asset_id"),
                        candidate_id=row.get("candidate_id"),
                        group_key=gk,
                    )
                )
                continue

            target_path = quarantine_dir / source_path.name

            # name conflict resolution
            if target_path.exists():
                stem = target_path.stem
                suffix = target_path.suffix
                i = 1
                while True:
                    alt = quarantine_dir / f"{stem}__dup{i}{suffix}"
                    if not alt.exists():
                        target_path = alt
                        break
                    i += 1

            if policy.dry_run:
                actions.append(
                    DeleteAction(
                        action="quarantine",
                        source_path=str(source_path),
                        reason="would_be_quarantined",
                        asset_id=row.get("asset_id"),
                        candidate_id=row.get("candidate_id"),
                        group_key=gk,
                        target_path=str(target_path),
                    )
                )
            else:
                try:
                    if not source_path.exists():
                        actions.append(
                            DeleteAction(
                                action="skip",
                                source_path=str(source_path),
                                reason="source_missing_at_execution_time",
                                asset_id=row.get("asset_id"),
                                candidate_id=row.get("candidate_id"),
                                group_key=gk,
                            )
                        )
                    else:
                        shutil.move(str(source_path), str(target_path))
                        actions.append(
                            DeleteAction(
                                action="quarantine",
                                source_path=str(source_path),
                                reason="quarantined",
                                asset_id=row.get("asset_id"),
                                candidate_id=row.get("candidate_id"),
                                group_key=gk,
                                target_path=str(target_path),
                            )
                        )
                except Exception as e:
                    actions.append(
                        DeleteAction(
                            action="error",
                            source_path=str(source_path),
                            reason=f"move_failed: {type(e).__name__}: {e}",
                            asset_id=row.get("asset_id"),
                            candidate_id=row.get("candidate_id"),
                            group_key=gk,
                            target_path=str(target_path),
                        )
                    )

    # --------------------------------------------------
    # 5) Summary
    # --------------------------------------------------
    summary = DeleteSummary(
        dry_run=policy.dry_run,
        verification_passed=verification_passed,
        total_requested=len(paths),
        total_known_assets=len(known_rows),
        total_groups=len(groups),
        keep_count=sum(1 for a in actions if a.action == "keep"),
        quarantine_count=sum(1 for a in actions if a.action == "quarantine"),
        skip_count=sum(1 for a in actions if a.action == "skip"),
        error_count=sum(1 for a in actions if a.action == "error"),
        quarantine_dir=str(quarantine_dir),
    )

    highlighted = []
    for a in actions:
        if a.action == "keep":
            highlighted.append(f"[KEEP] {a.source_path} :: {a.reason}")
        elif a.action == "quarantine":
            highlighted.append(f"[QUARANTINE] {a.source_path} -> {a.target_path}")
        elif a.action == "skip":
            highlighted.append(f"[SKIP] {a.source_path} :: {a.reason}")
        else:
            highlighted.append(f"[ERROR] {a.source_path} :: {a.reason}")

    return {
        "summary": asdict(summary),
        "actions": [asdict(a) for a in actions],
        "policy": asdict(policy),
        "highlighted": highlighted,
    }


# Alias
prune_verified_chart_files = safe_delete_candidates

# --------------------------------------------------
# CLI
# --------------------------------------------------

def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("safe_delete_candidates")

    parser.add_argument(
        "--paths-json",
        required=False,
        help="JSON file containing list of chart file paths",
    )

    parser.add_argument(
        "--auto-from-db",
        action="store_true",
        help="Generate candidate paths automatically from DB (inventory - assets)",
    )
        
    parser.add_argument(
        "--exclude-recent-days",
        type=int,
        default=7,
        help="Exclude files modified in last N days (auto-from-db only)",
    )

    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
    )

    parser.add_argument(
        "--chart-patterns-db",
        default=str(DEFAULT_CHART_PATTERNS_DB),
    )

    parser.add_argument(
        "--file-scan-db",
        default=str(DEFAULT_FILE_SCAN_INVENTORY_DB),
    )

    parser.add_argument(
        "--quarantine-dir",
        default=None,
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute (default: dry-run)",
    )

    parser.add_argument(
        "--allow-delete-last-copy",
        action="store_true",
    )

    parser.add_argument(
        "--include-type-b-in-delete",
        action="store_true",
    )

    parser.add_argument(
        "--json-out",
        default=None,
    )

    args = parser.parse_args(argv)

    # --------------------------------------------------
    # Resolve DB paths
    # --------------------------------------------------
    chart_asset_db = Path(args.chart_assets_db)
    chart_patterns_db = Path(args.chart_patterns_db)
    file_scan_db = Path(args.file_scan_db) if args.file_scan_db else None

    quarantine_dir = (
        Path(args.quarantine_dir)
        if args.quarantine_dir
        else None
    )

    # --------------------------------------------------
    # Decide candidate source
    # --------------------------------------------------
    if args.auto_from_db:

        print("[SAFE DELETE] Generating candidates from DB...")

        if file_scan_db is None:
            raise ValueError("--file-scan-db is required for --auto-from-db")

        paths = generate_delete_candidates_from_DB(
            file_scan_inventory_db=file_scan_db,
            chart_asset_db=chart_asset_db,
        )
        
        print(f"[SAFE DELETE] Generated {len(paths)} candidates from DB")
        
        if args.exclude_recent_days is not None:
            print(f"[SAFE DELETE] Applying recent filter: exclude {args.exclude_recent_days} days")

            paths = filter_delete_candidates(
                candidates=paths,
                chart_asset_db=chart_asset_db,
                exclude_recent_days=args.exclude_recent_days,
                include_games=None,
            )

            print(f"[SAFE DELETE] After filtering: {len(paths)} candidates")

        print(f"[SAFE DELETE] Generated {len(paths)} candidates from DB")

    else:
        # ✅ require JSON only in this branch
        if not args.paths_json:
            raise ValueError(
                "Either --paths-json or --auto-from-db must be provided"
            )

        input_path = Path(args.paths_json)

        if not input_path.exists():
            raise FileNotFoundError(f"paths-json not found: {input_path}")

        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}") from e

        if not isinstance(data, list):
            raise ValueError("paths-json must contain a list of file paths")

        paths: List[Path] = []
        for p in data:
            try:
                paths.append(Path(p).expanduser())
            except Exception:
                continue

        if not paths:
            raise ValueError("No valid paths found in JSON")

    # --------------------------------------------------
    # Run safe delete
    # --------------------------------------------------
    report = safe_delete_candidates(
        paths=paths,
        chart_asset_db=chart_asset_db,
        chart_patterns_db=chart_patterns_db,
        file_scan_inventory_db=file_scan_db,
        dry_run=not bool(args.execute),
        quarantine_dir=quarantine_dir,
        keep_at_least_one_copy=not bool(args.allow_delete_last_copy),
        only_type_a=not bool(args.include_type_b_in_delete),
    )

    summary = report.get("summary", {})
    policy = report.get("policy", {})

    # --------------------------------------------------
    # Print context
    # --------------------------------------------------
    print("\n[SAFE DELETE - ENV]")
    print("chart_assets_db     =", chart_asset_db)
    print("chart_patterns_db   =", chart_patterns_db)
    print("file_scan_db        =", file_scan_db)
    print("input_path_count    =", len(paths))

    print("\n[SAFE DELETE POLICY]")
    print("verification_passed =", summary.get("verification_passed"))
    print("dry_run             =", summary.get("dry_run"))
    print("keep_one_copy       =", policy.get("keep_at_least_one_copy"))
    print("only_type_a         =", policy.get("only_type_a"))

    print("\n[SAFE DELETE SUMMARY]")
    print("total_requested     =", summary.get("total_requested"))
    print("total_known_assets  =", summary.get("total_known_assets"))
    print("total_groups        =", summary.get("total_groups"))
    print("keep_count          =", summary.get("keep_count"))
    print("quarantine_count    =", summary.get("quarantine_count"))
    print("skip_count          =", summary.get("skip_count"))
    print("error_count         =", summary.get("error_count"))
    print("quarantine_dir      =", summary.get("quarantine_dir"))

    print("\n[HIGHLIGHTED ACTIONS]")
    for line in report.get("highlighted", []):
        print(" ", line)

    # --------------------------------------------------
    # Output JSON
    # --------------------------------------------------
    if args.json_out:
        out_path = Path(args.json_out)
        _json_dump(out_path, report)
        print("\nreport_written =", out_path)

    # --------------------------------------------------
    # Exit code
    # --------------------------------------------------
    verification_passed = bool(summary.get("verification_passed"))
    error_count = int(summary.get("error_count") or 0)

    if not verification_passed:
        return 2

    if error_count > 0:
        return 1

    return 0


__all__ = [
    "safe_delete_candidates",
    "prune_verified_chart_files",
    "cli_main",
]