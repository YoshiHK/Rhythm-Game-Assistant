#!/usr/bin/env python3
"""
PHASE 3 CONTRACT — Unified Ingestion Orchestrator (UMI)

This file is the authoritative coordination layer for Phase 3 of the
Rhythm Game Assistant pipeline.

(Completed Phases 1–2 MUST remain unchanged.)
"""

from __future__ import annotations

import argparse
import json
import sqlite3 
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rhythm_ingestion.config.games_loader import (
    get_enabled_games,
    get_games_supporting_tips,
)
from rhythm_ingestion.utils import scan_directory, log
from rhythm_ingestion.adapters import get_adapter
from rhythm_ingestion.validators import get_validator
from rhythm_ingestion.writers import get_writer
from rhythm_ingestion.writers.normalizers.identity_normalizer import normalize_folder_identity
from rhythm_ingestion.pipeline.tips import build_batch_summary
from rhythm_ingestion.pipeline.section_metrics import build_section_feature_vector
from rhythm_ingestion.pipeline.pattern_tags import (
    dominant_tag_categories,
    count_tags_by_category,
)
from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import (
    PatternTagsTaxonomy,
)
from rhythm_ingestion.runtime_meta import RuntimeMetaManager

# ------------------------------------------------------------
# Control-plane constants
# ------------------------------------------------------------

DEFAULT_CHART_ROOT = (
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File"
)

SUPPORTED_CHART_EXTENSIONS = {
    # generic / fallback
    ".html",
    ".htm",
    ".mht",
    ".mhtml",
    ".json",
    ".txt",
    ".svg",

    # game-specific deterministic chart files
    ".aff",   # Arcaea
    ".sus",   # SUS / Yumesute
    ".c2s",   # CHUNITHM
    ".xml",   # Dynamix / others
    ".ogkr",  # Ongeki
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)



def _filter_supported_extensions(
    paths: List[Path],
) -> Tuple[List[Path], List[Path]]:
    """
    Control-plane validation only.

    Returns:
      (supported_files, excluded_files)

    No semantic decisions are made here.
    """
    supported: List[Path] = []
    excluded: List[Path] = []

    for p in paths:
        try:
            if p.suffix.lower() in SUPPORTED_CHART_EXTENSIONS:
                supported.append(p)
            else:
                excluded.append(p)
        except Exception:
            excluded.append(p)

    return supported, excluded

def _resolve_game_from_path(path: Path) -> Optional[str]:
    """
    Identity-first routing using folder structure:

    Chart File/{game}/{difficulty}/{level}/{file}
    """

    parts = list(path.parts)

    try:
        idx = parts.index("Chart File")
    except ValueError:
        return None

    game_folder = parts[idx + 1] if len(parts) > idx + 1 else None
    difficulty_folder = parts[idx + 2] if len(parts) > idx + 2 else None
    level_folder = parts[idx + 3] if len(parts) > idx + 3 else None

    identity = normalize_folder_identity(
        game_folder=game_folder,
        difficulty_folder=difficulty_folder,
        level_folder=level_folder,
    )

    return identity.get("game")

def _detect_game_for_file(
    file_path: Path,
    enabled_game_ids: List[str],
) -> Tuple[Optional[str], List[str]]:
    """
    Detect which enabled game adapter accepts this file.

    Returns:
      (chosen_game_id or None, matching_game_ids)
    """
    matches: List[str] = []

    for gid in enabled_game_ids:
        try:
            adapter = get_adapter(gid)
            if adapter.accepts_file(file_path):
                matches.append(gid)
        except Exception:
            continue

    if not matches:
        return None, []

    return matches[0], matches


def _try_build_payload(adapter: Any, path: Path) -> Dict[str, Any]:
    if hasattr(adapter, "to_canonical_payload"):
        try:
            return adapter.to_canonical_payload(str(path))
        except Exception:
            return {"diagnostics": {}}
    return {"diagnostics": {}}
    
def _load_files_from_scan_state(scan_state_path: str) -> List[Path]:
    """
    Phase 3.5 replay helper.

    Load previously scanned files from file_scan_state.json.

    Preferred field:
        all_files

    Fallback:
        sample_files
    """
    p = Path(scan_state_path)
    if not p.exists():
        raise FileNotFoundError(f"scan_state_path not found: {scan_state_path}")

    data = json.loads(p.read_text(encoding="utf-8"))

    raw_files = data.get("all_files")
    if not isinstance(raw_files, list):
        raw_files = data.get("sample_files")

    if not isinstance(raw_files, list):
        return []

    out: List[Path] = []
    for item in raw_files:
        try:
            out.append(Path(str(item)))
        except Exception:
            continue

    return out
    
def _source_key(p: Path | str) -> str:
    try:
        return str(Path(p).resolve()).casefold()
    except Exception:
        return str(p).casefold()

def _load_existing_asset_source_keys(chart_asset_db: Optional[str]) -> set[str]:
    if not chart_asset_db:
        return set()

    db_path = Path(chart_asset_db)
    if not db_path.exists():
        return set()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chart_assets' LIMIT 1"
        ).fetchone()
        if row is None:
            return set()

        rows = conn.execute("SELECT source_path FROM chart_assets").fetchall()

        out: set[str] = set()
        for r in rows:
            source_path = r["source_path"]
            if source_path:
                out.add(_source_key(source_path))
        return out
    finally:
        conn.close()

def ingest(
    source_dir: str,
    *,
    db_path: Optional[str],
    dry_run: bool,
    only_game: Optional[str],
    json_out: Optional[str],
    tips_mode: str,
    scan_state_path: Optional[str] = None,
    chart_asset_db: Optional[str] = None,
    skip_known_assets: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    
    log("🔥 DEBUG: NEW ingest() WITH CACHE ACTIVE")

    src = Path(source_dir)

    if not src.exists():
        log(f"Error: directory not found: {src}")
        return {
            "status_code": 1,
            "rows": [],
            "batch_summary": None,
            "error": f"directory not found: {src}",
        }

    # --------------------------------------------------------
    # Optional converter-cache wiring (additive only)
    # --------------------------------------------------------
    enable_converter_cache = bool(kwargs.get("enable_converter_cache", False))
    inventory_stat_cache = kwargs.get("inventory_stat_cache") or {}
    asset_source_path_cache = kwargs.get("asset_source_path_cache") or set()
    asset_conversion_skip_predicate = kwargs.get("asset_conversion_skip_predicate")

    skipped_existing_count = 0
    skipped_converter_cache_count = 0

    # --------------------------------------------------------
    # 1) File scan / replay
    # --------------------------------------------------------
    if scan_state_path:
        try:
            all_files = _load_files_from_scan_state(scan_state_path)
            if not all_files:
                log(f"[INGEST] scan_state_path provided but no files found: {scan_state_path}")
                all_files = scan_directory(
                    src,
                    allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
                )
            else:
                log(f"[INGEST] Reusing scan snapshot: {scan_state_path}")
        except Exception as e:
            log(f"[INGEST] Failed to load scan snapshot, fallback live scan: {e}")
            all_files = scan_directory(
                src,
                allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
            )
    else:
        all_files = scan_directory(
            src,
            allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
        )

    files, excluded = _filter_supported_extensions(all_files)

    if excluded:
        log(
            f"Excluded {len(excluded)} files with unsupported extensions "
            f"(out of {len(all_files)} total files scanned)"
        )

    log(f"Candidate chart files after filtering: {len(files)}")

    # --------------------------------------------------------
    # 1.5) Incremental skip logic (legacy behavior)
    # --------------------------------------------------------
    # IMPORTANT:
    # - If converter cache is enabled, do NOT drop files here.
    #   We still want full canonical row flow.
    # - Keep legacy skip behavior only when converter cache is disabled.
    if (not enable_converter_cache) and skip_known_assets and chart_asset_db:
        existing_asset_keys = _load_existing_asset_source_keys(chart_asset_db)

        if existing_asset_keys:
            new_files: List[Path] = []
            for p in files:
                if _source_key(p) in existing_asset_keys:
                    skipped_existing_count += 1
                else:
                    new_files.append(p)

            files = new_files
            log(
                f"[INGEST] Incremental skip active: skipped_existing={skipped_existing_count} "
                f"remaining_candidates={len(files)}"
            )

            log(
                f"[INGEST MODE] total_before={len(all_files)} "
                f"total_after={len(files)}"
            )
    elif enable_converter_cache:
        log(
            f"[INGEST CACHE MODE] total_before={len(all_files)} total_after={len(files)} "
            f"(full canonical flow preserved; cache applies at asset-ingest layer)"
        )

    total = len(files)
    for idx, file_path in enumerate(files):
        if idx % 100 == 0:
            log(f"[INGEST PROGRESS] {idx}/{total} current={file_path}")

    # --------------------------------------------------------
    # Resolve artifact paths
    # --------------------------------------------------------
    if not db_path:
        raise ValueError("db_path must be provided for Phase 3 ingestion")

    if not json_out:
        raise ValueError("json_out must be provided for song_db_meta")

    resolved_db_path = db_path
    resolved_json_out = json_out

    # --------------------------------------------------------
    # 2) Game / adapter routing
    # --------------------------------------------------------   
    enabled_games = get_enabled_games()
    tips_enabled_games = set(get_games_supporting_tips())

    rows: List[Dict[str, Any]] = []
    asset_candidates: List[Dict[str, Any]] = []

    route_none_count = 0
    canonical_error_count = 0
    canonical_error_samples: List[str] = []

    for path in files:
        # ------------------------------------------
        # NEW: Identity-first routing
        # ------------------------------------------
        game_id = _resolve_game_from_path(path)

        if game_id:
            try:
                adapter = get_adapter(game_id)
            except Exception:
                adapter = None
        else:
            adapter = None
                    
        log(f"[DEBUG ROUTE] path={path} -> identity_game_id={game_id}")
        log(f"[DEBUG ROUTE] adapter_after_identity={adapter}")
        
        # ------------------------------------------
        # Fallback: legacy adapter detection
        # ------------------------------------------
        if adapter is None:
            game_id_fallback, matches = _detect_game_for_file(path, enabled_games)
            
            log(f"[DEBUG ROUTE] fallback_game_id={game_id_fallback} matches={matches}")

            if not game_id_fallback:
                route_none_count += 1
                log(f"[ROUTING MISS] {path}")
                continue

            game_id = game_id_fallback

            try:
                adapter = get_adapter(game_id)
            except Exception:
                route_none_count += 1
                log(f"[ROUTING MISS] {path} (adapter load failed for {game_id})")
                continue
                
            log(f"[DEBUG ROUTE] adapter_after_fallback={adapter}")

        # ------------------------------------------
        # Optional game filter
        # ------------------------------------------
        if only_game and game_id != only_game:
            continue

        log(f"[ROUTING HIT] {path} → {game_id}")

        validator = get_validator(game_id)

        payload = _try_build_payload(adapter, path)

        try:
            validator.validate(payload)
        except Exception as e:
            payload.setdefault("diagnostics", {})["validation_error"] = str(e)

        try:
            canonical_row = adapter.to_canonical_row(payload)
        except Exception as e:
            canonical_error_count += 1
            if len(canonical_error_samples) < 10:
                canonical_error_samples.append(f"{path.name}: {repr(e)}")
            log(f"canonical_row error for {path}: {e}")
            continue

        rows.append(
            {
                "game_id": game_id,
                "canonical_row": canonical_row,
            }
        )

        try:
            asset_candidate = {
                "candidate_id": f"{game_id}:{path.name}",
                "run_id": "phase3_ingest",
                "source_path": str(path),
                "basename": path.name,
                "extension": path.suffix.lower(),
                "game_normalized": game_id,
                "difficulty_normalized": (
                    canonical_row.get("difficulty")
                    if isinstance(canonical_row, dict)
                    else None
                ),
                "level_normalized": (
                    canonical_row.get("level")
                    if isinstance(canonical_row, dict)
                    else None
                ),
                "extra_metadata": {
                    "source": "umi_phase3",
                },
            }

            asset_candidates.append(asset_candidate)

        except Exception:
            pass

    log(f"[INGEST] rows={len(rows)} route_miss={route_none_count} errors={canonical_error_count}")

    if canonical_error_samples:
        print("CANONICAL_ERROR_SAMPLES:")
        for item in canonical_error_samples:
            print("  ", item)


    # --------------------------------------------------------
    # 3) Writers / QA summary
    # --------------------------------------------------------
    if not dry_run:
        writer = get_writer()
        writer.write_rows(rows, db_path=resolved_db_path)

    try:
        from rhythm_ingestion.writers.orchestrators import (
            ingest_chart_assets_from_file_scan_candidates,
        )

        asset_db_path = Path(
            chart_asset_db
            or kwargs.get("chart_assets_db")
            or r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime\assets\chart_assets.db"
        )

        asset_candidates_to_ingest = asset_candidates

        # ----------------------------------------------------
        # Converter-cache filter (asset-ingest layer only)
        # ----------------------------------------------------
        if (
            enable_converter_cache
            and callable(asset_conversion_skip_predicate)
            and inventory_stat_cache
            and asset_source_path_cache
        ):
            filtered_candidates: List[Dict[str, Any]] = []

            for cand in asset_candidates:
                source_path = cand.get("source_path")
                if not source_path:
                    filtered_candidates.append(cand)
                    continue

                try:
                    should_skip = asset_conversion_skip_predicate(
                        Path(source_path),
                        inventory_stat_cache,
                        asset_source_path_cache,
                    )
                except Exception as e:
                    log(f"[CACHE][WARN] predicate failed for {source_path}: {e}")
                    should_skip = False

                if should_skip:
                    skipped_converter_cache_count += 1
                    continue

                filtered_candidates.append(cand)

            asset_candidates_to_ingest = filtered_candidates
            log(
                f"[CACHE] asset_candidates_total={len(asset_candidates)} "
                f"asset_candidates_skipped={skipped_converter_cache_count} "
                f"asset_candidates_to_ingest={len(asset_candidates_to_ingest)}"
            )

        asset_result = ingest_chart_assets_from_file_scan_candidates(
            db_path=Path(asset_db_path),
            candidates=asset_candidates_to_ingest,
        )

        persisted = (
            asset_result.get("summary", {})
            .get("persisted_assets")
        )

        log(f"[ASSET INGEST] persisted={persisted}")

    except Exception as e:
        log(f"[ASSET INGEST FAILED] {e}")

    summary = build_batch_summary(rows, tips_mode=tips_mode)

    # --------------------------------------------------------
    # Safe pattern writer wiring
    # --------------------------------------------------------
    try:
        from rhythm_ingestion.writers.persistence import chart_pattern_writer

        pattern_db_path = kwargs.get("chart_pattern_db") or \
            r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime\features\chart_patterns.db"

        if hasattr(chart_pattern_writer, "write_from_rows"):
            chart_pattern_writer.write_from_rows(
                rows=rows,
                db_path=pattern_db_path,
            )
            log("[PATTERN INGEST] completed")
        else:
            log("[PATTERN INGEST] write_from_rows not available -> skipping (safe)")
    except Exception as e:
        log(f"[PATTERN INGEST][WARN] skipped due to: {e}")

    batch_summary = summary
    log("Batch summary generated")

    # --------------------------------------------------------
    # Build song_db_meta
    # --------------------------------------------------------
    by_game = {}
    for item in rows:
        gid = item.get("game_id")
        if not gid:
            continue
        slot = by_game.setdefault(gid, {"files": 0, "rows": 0, "failures": 0})
        slot["files"] += 1
        slot["rows"] += 1

    from datetime import datetime, timezone

    song_db_meta = {
        "report_type": "song_db_meta",
        "report_date": Path(resolved_json_out).parent.parent.name,
        "run_id": Path(resolved_json_out).parent.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_file": Path(resolved_db_path).name,
        "summary": {
            "total_files_scanned": len(all_files),
            "total_supported_files": len(files),
            "rows_built": len(rows),
            "rows_written": len(rows) if not dry_run else 0,
            "skipped_existing_assets": skipped_existing_count,
            "skipped_converter_cache": skipped_converter_cache_count,
            "remaining_candidates": len(files),
        },
        "validation": {
            "routing_failures": route_none_count,
            "adapter_failures": 0,
            "canonical_row_errors": canonical_error_count,
            "validation_errors": 0,
        },
        "by_game": by_game,
        "data_quality": {},
        "lookup_stats": {},
        "integrity": {
            "schema_version": 2,
            "scan_state_path": scan_state_path,
            "scan_reused": bool(scan_state_path),
            "incremental_skip_enabled": bool(skip_known_assets and chart_asset_db and not enable_converter_cache),
            "converter_cache_enabled": bool(enable_converter_cache),
        },
    }

    if json_out:
        _json_dump(resolved_json_out, song_db_meta)
    else:
        raise ValueError("json_out must be provided for song_db_meta")

    log("Ingestion completed")

    return {
        "status_code": 0,
        "rows": rows,
        "batch_summary": batch_summary,
    }

# ------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser("Unified Ingestion Orchestrator (UMI)")

    # --------------------------------------------------------
    # Core arguments
    # --------------------------------------------------------
    parser.add_argument(
        "--source",
        required=False,
        default=DEFAULT_CHART_ROOT,
        help=(
            "Directory containing raw chart files "
            f"(default: {DEFAULT_CHART_ROOT})"
        ),
    )

    parser.add_argument(
        "--db",
        required=False,
        help="Path to Song Database (full).xlsx (required unless --dry-run)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing to Excel DB",
    )

    parser.add_argument(
        "--game",
        required=False,
        help="Restrict run to a single enabled game_id from games.json",
    )

    parser.add_argument(
        "--json",
        required=False,
        help="Write run report to JSON path",
    )

    parser.add_argument(
        "--tips-mode",
        default="production",
        choices=["production", "debug"],
        help="Tips generation mode (only for games that support tips)",
    )

    # --------------------------------------------------------
    # Scan / runtime wiring (existing optional)
    # --------------------------------------------------------
    parser.add_argument(
        "--scan-state",
        required=False,
        help="Path to file_scan_state.json (reuse scan snapshot)",
    )

    parser.add_argument(
        "--chart-asset-db",
        required=False,
        help="Path to chart_assets.db (for incremental behavior)",
    )

    # --------------------------------------------------------
    # Converter cache wiring (additive only)
    # --------------------------------------------------------
    parser.add_argument(
        "--enable-converter-cache",
        action="store_true",
        help="Enable converter cache (skip unchanged asset conversion)",
    )

    parser.add_argument(
        "--file-scan-db",
        required=False,
        help="Path to file_scan_inventory.db (required for converter cache)",
    )

    parser.add_argument(
        "--chart-assets-db",
        required=False,
        help="(Alias) Path to chart_assets.db for converter cache",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Resolve cache-related inputs
    # --------------------------------------------------------
    chart_asset_db = args.chart_asset_db or args.chart_assets_db

    # --------------------------------------------------------
    # Execution
    # --------------------------------------------------------
    ingest(
        args.source,

        db_path=args.db,
        dry_run=args.dry_run,
        only_game=args.game,
        json_out=args.json,
        tips_mode=args.tips_mode,

        scan_state_path=args.scan_state,
        chart_asset_db=chart_asset_db,

        # ----------------------------------------------------
        # Pass-through cache flags (non-breaking)
        # ----------------------------------------------------
        enable_converter_cache=args.enable_converter_cache,
        file_scan_db=args.file_scan_db,
        chart_assets_db=args.chart_assets_db,
    )


if __name__ == "__main__":
    main()
