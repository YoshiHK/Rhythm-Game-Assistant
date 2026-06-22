from __future__ import annotations

"""
Update_Runtime_Dbs.py

One-time runtime DB update helper for Phase 3.5 / UMI v2.0.

Purpose
-------
- scan chart files directly from source dir
- update runtime/ingestions/file_scan_inventory.db
- build canonical rows (for visibility / diagnostics)
- update runtime/assets/chart_assets.db via chart_asset_writer
- update runtime/features/chart_patterns.db via chart_pattern_writer bridge

Scope
-----
- additive wiring only
- no modification of Completed Phases
- intended for baseline build / direct runtime DB refresh
"""

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Defaults
# --------------------------------------------------
DEFAULT_SOURCE_DIR = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File"
)
DEFAULT_RUNTIME_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime"
)

DEFAULT_INVENTORY_DB = DEFAULT_RUNTIME_ROOT / "ingestions" / "file_scan_inventory.db"
DEFAULT_ASSET_DB = DEFAULT_RUNTIME_ROOT / "assets" / "chart_assets.db"
DEFAULT_PATTERN_DB = DEFAULT_RUNTIME_ROOT / "features" / "chart_patterns.db"

RUN_ID = "manual_db_update"


# --------------------------------------------------
# Imports (Phase 3.5-safe)
# --------------------------------------------------
from rhythm_ingestion.utils import scan_directory
from rhythm_ingestion.orchestrator import (
    SUPPORTED_CHART_EXTENSIONS,
    _filter_supported_extensions,
    _detect_game_for_file,
    _try_build_payload,
)
from rhythm_ingestion.config.games_loader import get_enabled_games
from rhythm_ingestion.adapters import get_adapter
from rhythm_ingestion.validators import get_validator

from rhythm_ingestion.writers.persistence.file_scan_inventory_writer import (
    persist_file_scan_inventory_from_paths,
)
from rhythm_ingestion.writers.persistence.chart_asset_writer import (
    persist_chart_assets_from_candidates,
)
from rhythm_ingestion.writers.persistence.chart_pattern_writer import (
    write_from_scan_inventory,
    phase5_bridge_extractor,
)


# --------------------------------------------------
# Helper adapters for file_scan_inventory_writer
# --------------------------------------------------
@dataclass(frozen=True)
class _Fingerprint:
    size: int
    mtime_ns: int


def _inventory_fingerprint(p: Path) -> _Fingerprint:
    st = p.stat()
    return _Fingerprint(
        size=int(st.st_size),
        mtime_ns=int(st.st_mtime_ns),
    )


def _inventory_normalize_key(p: Path) -> str:
    return str(p.resolve()).casefold()


def _inventory_extract_chart_hierarchy(p: Path) -> Dict[str, Optional[str]]:
    """
    Minimal hierarchy extractor for file_scan_inventory_writer.

    Expected shape:
        Chart File / <game> / <difficulty> / <level> / <file>

    This is a Phase 3.5 wiring adapter only. Normalization itself remains inside
    identity_normalizer.py via file_scan_inventory_writer.
    """
    parts = list(p.parts)

    game_folder = None
    difficulty_folder = None
    level_folder = None

    try:
        if len(parts) >= 4:
            game_folder = parts[-4]
            difficulty_folder = parts[-3]
            level_folder = parts[-2]
    except Exception:
        pass

    return {
        "game_folder": game_folder,
        "difficulty_folder": difficulty_folder,
        "level_folder": level_folder,
    }


def _inventory_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------
# Compatibility bridge for chart_pattern_writer
# --------------------------------------------------
def _ensure_scan_candidates_compat_view(inventory_db: Path) -> None:
    """
    Bridge inventory DB → chart_pattern_writer expected schema.

    FIX:
    - normalized_key (file path) cannot be used as chart_id
    - generate safe deterministic chart_id via SHA256(source_path)
    """

    import hashlib

    def _hash_path(p: str) -> str:
        return hashlib.sha256(p.encode("utf-8")).hexdigest()

    with sqlite3.connect(str(inventory_db)) as conn:
        conn.execute("DROP VIEW IF EXISTS scan_candidates")

        rows = conn.execute(
            """
            SELECT
                candidate_id,
                run_id,
                source_path,
                normalized_key,
                basename,
                extension,
                size,
                mtime_ns,
                game_normalized,
                discovered_at
            FROM file_scan_inventory
            """
        ).fetchall()

        conn.execute("DROP TABLE IF EXISTS _scan_candidates_tmp")
        conn.execute(
            """
            CREATE TABLE _scan_candidates_tmp (
                candidate_id TEXT,
                run_id TEXT,
                source_path TEXT,
                normalized_key TEXT,
                basename TEXT,
                extension TEXT,
                size INTEGER,
                mtime_ns INTEGER,
                file_hash TEXT,
                game_id TEXT,
                discovered_at TEXT
            )
            """
        )

        insert_rows = []
        for r in rows:
            source_path = r[2]
            safe_chart_id = _hash_path(source_path)

            insert_rows.append((
                r[0],  # candidate_id
                r[1],  # run_id
                source_path,
                safe_chart_id, 
                r[4],  # basename
                r[5],  # extension
                r[6],  # size
                r[7],  # mtime_ns
                None,  # file_hash
                r[8],  # game_id
                r[9],  # discovered_at
            ))

        conn.executemany(
            """
            INSERT INTO _scan_candidates_tmp VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows
        )

        conn.execute("DROP VIEW IF EXISTS scan_candidates")
        conn.execute(
            """
            CREATE VIEW scan_candidates AS
            SELECT * FROM _scan_candidates_tmp
            """
        )

        conn.commit()

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def ensure_runtime_dirs(runtime_root: Path) -> None:
    (runtime_root / "ingestions").mkdir(parents=True, exist_ok=True)
    (runtime_root / "assets").mkdir(parents=True, exist_ok=True)
    (runtime_root / "features").mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Core
# --------------------------------------------------
def update_runtime_dbs(
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    inventory_db: Path = DEFAULT_INVENTORY_DB,
    asset_db: Path = DEFAULT_ASSET_DB,
    pattern_db: Path = DEFAULT_PATTERN_DB,
) -> Dict[str, Any]:
    ensure_runtime_dirs(runtime_root)

    # --------------------------------------------------
    # 1) Scan
    # --------------------------------------------------
    all_files = scan_directory(
        source_dir,
        allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
    )
    files, excluded = _filter_supported_extensions(all_files)

    print(f"[DB UPDATE] total_scanned={len(all_files)} supported={len(files)} excluded={len(excluded)}")

    # --------------------------------------------------
    # 2) Inventory DB
    # --------------------------------------------------
    inventory_result = persist_file_scan_inventory_from_paths(
        db_path=inventory_db,
        candidates=files,
        run_id=RUN_ID,
        extract_chart_hierarchy=_inventory_extract_chart_hierarchy,
        _normalize_key=_inventory_normalize_key,
        fingerprint=_inventory_fingerprint,
        utc_now_iso=_inventory_utc_now_iso,
    )

    print(f"[DB UPDATE] inventory_db={inventory_db}")
    print(f"[DB UPDATE] inventory_result={json.dumps(inventory_result, ensure_ascii=False)}")

    # compatibility bridge for chart_pattern_writer
    _ensure_scan_candidates_compat_view(inventory_db)

    # --------------------------------------------------
    # 3) Canonical rows + asset candidates
    # --------------------------------------------------
    enabled_games = get_enabled_games()

    rows: List[Dict[str, Any]] = []
    asset_candidates: List[Dict[str, Any]] = []
    route_miss = 0
    canonical_errors = 0

    for i, path in enumerate(files):
        if i % 200 == 0:
            print(f"[DB UPDATE PROGRESS] {i}/{len(files)} current={path}")

        game_id, matches = _detect_game_for_file(path, enabled_games)

        if not game_id:
            route_miss += 1
            continue

        adapter = get_adapter(game_id)
        validator = get_validator(game_id)

        payload = _try_build_payload(adapter, path)

        try:
            validator.validate(payload)
        except Exception as e:
            payload.setdefault("diagnostics", {})["validation_error"] = str(e)

        try:
            canonical_row = adapter.to_canonical_row(payload)
        except Exception:
            canonical_errors += 1
            continue

        rows.append({
            "game_id": game_id,
            "canonical_row": canonical_row,
        })

        asset_candidates.append({
            "candidate_id": f"{game_id}:{path.name}",
            "run_id": RUN_ID,
            "source_path": str(path),
            "basename": path.name,
            "extension": path.suffix.lower(),
            "game_normalized": game_id,
            "difficulty_normalized": (
                canonical_row.get("difficulty")
                if isinstance(canonical_row, dict) else None
            ),
            "level_normalized": (
                canonical_row.get("level")
                if isinstance(canonical_row, dict) else None
            ),
            "extra_metadata": {
                "source": "manual_db_update",
            },
        })

    print(f"[DB UPDATE] rows_built={len(rows)} route_miss={route_miss} canonical_errors={canonical_errors}")

    # --------------------------------------------------
    # 4) Asset DB
    # --------------------------------------------------
    print("[DEBUG] entering asset DB stage")

    asset_result = persist_chart_assets_from_candidates(
        db_path=asset_db,
        candidates=asset_candidates,
    )

    print(f"[DB UPDATE] asset_db={asset_db}")
    print(f"[DB UPDATE] asset_result={json.dumps(asset_result, ensure_ascii=False)}")

    # --------------------------------------------------
    # 5) Pattern DB
    # --------------------------------------------------
    print("[DEBUG] entering pattern DB stage")
    
    try:
        pattern_summary = write_from_scan_inventory(
            scan_db_path=inventory_db,
            extractor=phase5_bridge_extractor,
            output_db_path=pattern_db,
            run_id=RUN_ID,
        )

        pattern_result = {
            "status": "completed",
            "db_path": pattern_summary.db_path,
            "extraction_version": pattern_summary.extraction_version,
            "chart_patterns_written": pattern_summary.chart_patterns_written,
            "pattern_features_written": pattern_summary.pattern_features_written,
            "pattern_blobs_written": pattern_summary.pattern_blobs_written,
            "writer": "write_from_scan_inventory",
            "extractor": "phase5_bridge_extractor",
        }

    except Exception as e:
        pattern_result = {
            "status": "failed",
            "reason": f"{type(e).__name__}: {e}",
        }

    print(f"[DB UPDATE] pattern_db={pattern_db}")
    print(f"[DB UPDATE] pattern_result={json.dumps(pattern_result, ensure_ascii=False)}")

    print("[DB UPDATE] completed")

    return {
        "summary": {
            "total_scanned": len(all_files),
            "supported_files": len(files),
            "excluded_files": len(excluded),
            "rows_built": len(rows),
            "route_miss": route_miss,
            "canonical_errors": canonical_errors,
            "pattern_writer_status": pattern_result.get("status"),
        },
        "inventory_db": str(inventory_db),
        "asset_db": str(asset_db),
        "pattern_db": str(pattern_db),
        "inventory_result": inventory_result,
        "asset_result": asset_result,
        "pattern_result": pattern_result,
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------
def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("Update_Runtime_Dbs")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--inventory-db", default=str(DEFAULT_INVENTORY_DB))
    parser.add_argument("--asset-db", default=str(DEFAULT_ASSET_DB))
    parser.add_argument("--pattern-db", default=str(DEFAULT_PATTERN_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = update_runtime_dbs(
        source_dir=Path(args.source_dir),
        runtime_root=Path(args.runtime_root),
        inventory_db=Path(args.inventory_db),
        asset_db=Path(args.asset_db),
        pattern_db=Path(args.pattern_db),
    )

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[DB UPDATE] json_out={out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
