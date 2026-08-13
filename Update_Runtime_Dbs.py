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

from collections import Counter, defaultdict
from datetime import datetime, timezone

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

# ---------------------------------------------------------------------
# Config layer import (legacy UMI path preferred; Phase 7 fallback)
# ---------------------------------------------------------------------
try:
    # Legacy / in-package location
    from rhythm_ingestion.config.games_loader import get_enabled_games

except Exception:
    try:
        # Phase 7 config layer exposed on PYTHONPATH by Run_UpdateRuntimeDbs.ps1
        from games_loader import get_enabled_games  # type: ignore

    except Exception:
        # Last-resort fallback: locate Phase 7 games_loader.py by walking upward
        import importlib.util
        from pathlib import Path

        _HERE = Path(__file__).resolve()

        def _find_phase7_games_loader(start: Path) -> Path:
            for parent in [start.parent, *start.parents]:
                candidate = (
                    parent
                    / "Phase 7 - Games Recommendation"
                    / "config"
                    / "games_loader.py"
                )
                if candidate.exists():
                    return candidate

            raise ModuleNotFoundError(
                "Could not locate Phase 7 games_loader.py by walking parent directories "
                f"from: {start}"
            )

        _PHASE7_GAMES_LOADER = _find_phase7_games_loader(_HERE)

        _spec = importlib.util.spec_from_file_location(
            "phase7_games_loader",
            str(_PHASE7_GAMES_LOADER),
        )
        if _spec is None or _spec.loader is None:
            raise ModuleNotFoundError(
                f"Could not build import spec for: {_PHASE7_GAMES_LOADER}"
            )

        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)

        get_enabled_games = _mod.get_enabled_games
        
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
    Robust hierarchy extractor for file_scan_inventory_writer.

    Expected canonical shape:
        Chart File / <game> / <difficulty> / <level> / <file>

    This helper is additive wiring only:
    - it does NOT replace identity_normalizer
    - it only improves the upstream folder slicing fed into normalization

    If the expected anchor folder ("Chart File") is found, extract relative
    folders after that anchor.
    Otherwise, fall back conservatively to the old tail-based heuristic.
    """
    parts = list(p.parts)

    game_folder: Optional[str] = None
    difficulty_folder: Optional[str] = None
    level_folder: Optional[str] = None

    # --------------------------------------------------
    # Preferred: anchor-based extraction
    # --------------------------------------------------
    try:
        lowered = [str(x).casefold() for x in parts]
        if "chart file".casefold() in lowered:
            anchor_idx = lowered.index("chart file".casefold())

            rel = parts[anchor_idx + 1 :]  # folders after "Chart File"

            # Need at least: <game>/<difficulty>/<level>/<file>
            if len(rel) >= 4:
                game_folder = rel[0]
                difficulty_folder = rel[1]
                level_folder = rel[2]
                return {
                    "game_folder": game_folder,
                    "difficulty_folder": difficulty_folder,
                    "level_folder": level_folder,
                }

            # Partial / shallow fallback after anchor
            if len(rel) >= 3:
                game_folder = rel[0]
                difficulty_folder = rel[1]
                level_folder = None
                return {
                    "game_folder": game_folder,
                    "difficulty_folder": difficulty_folder,
                    "level_folder": level_folder,
                }

            if len(rel) >= 2:
                game_folder = rel[0]
                difficulty_folder = None
                level_folder = None
                return {
                    "game_folder": game_folder,
                    "difficulty_folder": difficulty_folder,
                    "level_folder": level_folder,
                }
    except Exception:
        pass

    # --------------------------------------------------
    # Conservative fallback: tail-based heuristic
    # --------------------------------------------------
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
def _safe_log_text(value: Any) -> str:
    try:
        return ascii(str(value))
    except Exception:
        return ascii(value)
        
def ensure_runtime_dirs(runtime_root: Path) -> None:
    (runtime_root / "ingestions").mkdir(parents=True, exist_ok=True)
    (runtime_root / "assets").mkdir(parents=True, exist_ok=True)
    (runtime_root / "features").mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# Semantic Mapping Layer (Tips Guide reference)
# --------------------------------------------------

SEMANTIC_KINDS = {
    "tap",
    "hold_body_or_start",
    "hold_path",
    "flick_arrow",
    "critical_tap",
    "lane_based_pattern",
    "spatial_path_pattern",
    "timing_surface_pattern",
    "radial_position",
    "multi_side_transition",
    "judge_line_relative",
    "scratch_semantic",
    "slide_graph_semantic",
    "cross_hand_pattern",
    "forced_hand_swap_pattern",
}

# --------------------------------------------------
# Game Coverage (Tips Guide reference)
# --------------------------------------------------

GAME_COVERAGE = {
    "proseka": ("high", True),
    "bandori": ("high", True),
    "yumesute": ("high", True),
    "d4dj": ("high", True),
    "arcaea": ("high", True),
    "chunithm": ("high", True),

    "maimai": ("medium", False),
    "ongeki": ("medium", False),
    "phigros": ("medium", False),
    "lanota": ("medium", False),
    "dynamix": ("medium", False),
}

# -------------------------
# Canonical Error Buckets v2
# -------------------------

_BUCKET_ROUTE_MISS = "ROUTE_MISS"
_BUCKET_NO_ADAPTER = "NO_ADAPTER"
_BUCKET_NO_VALIDATOR = "NO_VALIDATOR"

_BUCKET_VALIDATION_FAIL = "VALIDATION_FAIL"

# ✅ NEW
_BUCKET_ADAPTER_FAIL = "ADAPTER_FAIL"
_BUCKET_VALIDATOR_FAIL = "VALIDATOR_FAIL"
_BUCKET_SCHEMA_FAIL = "SCHEMA_FAIL"

# ✅ SEMANTIC + COVERAGE
_BUCKET_SEMANTIC_GAP = "SEMANTIC_GAP"
_BUCKET_COVERAGE_GAP = "COVERAGE_GAP"

_BUCKET_CANONICAL_PAYLOAD_FAIL = "CANONICAL_PAYLOAD_FAIL"
_BUCKET_CANONICAL_ROW_FAIL = "CANONICAL_ROW_FAIL"

_BUCKET_UNKNOWN = "UNKNOWN"

# --------------------------------------------------
# Canonical Error Breakdown Contract
# --------------------------------------------------

CANONICAL_ERROR_SCHEMA_ID = "rga.canonical_error_breakdown.v1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------
# Canonical Error Logging Helper
# --------------------------------------------------
def _append_canonical_error(
    error_rows: List[Dict[str, Any]],
    *,
    source_path: Path,
    normalized_game_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    classifier_result: Optional[str] = None,
    adapter_id: Optional[str] = None,
    validator_id: Optional[str] = None,
    bucket: str = _BUCKET_UNKNOWN,
    reason_code: str = "UNSPECIFIED",
    reason_message: str = "",
    exception: Optional[Exception] = None,
    validation_ok: Optional[bool] = None,
    canonical_payload_ok: Optional[bool] = None,
    canonical_row_ok: Optional[bool] = None,
) -> None:
    error_rows.append({
        "source_path": str(source_path),
        "normalized_game_id": normalized_game_id,
        "asset_type": asset_type,
        "classifier_result": classifier_result,
        "adapter_id": adapter_id,
        "validator_id": validator_id,
        "bucket": bucket,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "exception_type": type(exception).__name__ if exception is not None else None,
        "exception_message": str(exception) if exception is not None else None,
        "validation_ok": validation_ok,
        "canonical_payload_ok": canonical_payload_ok,
        "canonical_row_ok": canonical_row_ok,
    })



# --------------------------------------------------
# Canonical Error Breakdown Generator
# --------------------------------------------------
def _build_canonical_error_breakdown(
    *,
    build_id: str,
    audit_session_id: Optional[str] = None,
    source_dir: Path,
    runtime_root: Path,
    inventory_count: int,
    rows_built: int,
    route_miss: int,
    canonical_errors: int,
    error_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    bucket_counter: Counter[str] = Counter()
    game_bucket_counter: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in error_rows:
        bucket = str(row.get("bucket") or _BUCKET_UNKNOWN)
        game_id = row.get("normalized_game_id") or "unknown"

        bucket_counter[bucket] += 1
        game_bucket_counter[str(game_id)][bucket] += 1

    by_bucket = [
        {"bucket": bucket, "count": count}
        for bucket, count in sorted(bucket_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    by_game = []
    for game_id, counter in sorted(game_bucket_counter.items(), key=lambda kv: kv[0]):
        total = sum(counter.values())
        by_game.append({
            "game_id": game_id,
            "count": total,
            "buckets": [
                {"bucket": bucket, "count": count}
                for bucket, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
        })

    return {
        "schema_id": CANONICAL_ERROR_SCHEMA_ID,
        "kind": "verification_artifact",
        "build_id": build_id,
        "audit_session_id": audit_session_id,
        "generated_at": _utc_now_iso(),
        "source_dir": str(source_dir),
        "runtime_root": str(runtime_root),
        "summary": {
            "inventory_count": int(inventory_count),
            "rows_built": int(rows_built),
            "route_miss": int(route_miss),
            "canonical_errors": int(canonical_errors),
        },
        "diagnosis": {
            "phase3_fail": any(b in bucket_counter for b in [
                _BUCKET_ADAPTER_FAIL,
                _BUCKET_VALIDATOR_FAIL,
                _BUCKET_SCHEMA_FAIL
            ]),
            "semantic_gap": _BUCKET_SEMANTIC_GAP in bucket_counter,
            "coverage_gap": _BUCKET_COVERAGE_GAP in bucket_counter,
        },
        "by_bucket": by_bucket,
        "by_game": by_game,
        "rows": error_rows,
    }

# --------------------------------------------------
# Core Pipeline Implementation
# --------------------------------------------------
def update_runtime_dbs(
    *,
    run_id: str = RUN_ID,
    audit_session_id: Optional[str] = None,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    inventory_db: Path = DEFAULT_INVENTORY_DB,
    asset_db: Path = DEFAULT_ASSET_DB,
    pattern_db: Path = DEFAULT_PATTERN_DB,
    canonical_error_out: Optional[Path] = None,
) -> Dict[str, Any]:
    ensure_runtime_dirs(runtime_root)

    # 1) Scan
    all_files = scan_directory(
        source_dir,
        allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
    )
    files, excluded = _filter_supported_extensions(all_files)

    print(f"[DB UPDATE] total_scanned={len(all_files)} supported={len(files)} excluded={len(excluded)}")

    # 2) Inventory DB
    inventory_result = persist_file_scan_inventory_from_paths(
        db_path=inventory_db,
        candidates=files,
        run_id=run_id,
        extract_chart_hierarchy=_inventory_extract_chart_hierarchy,
        _normalize_key=_inventory_normalize_key,
        fingerprint=_inventory_fingerprint,
        utc_now_iso=_inventory_utc_now_iso,
    )

    print(f"[DB UPDATE] inventory_db={inventory_db}")
    print(f"[DB UPDATE] inventory_result={json.dumps(inventory_result, ensure_ascii=False)}")

    _ensure_scan_candidates_compat_view(inventory_db)

    # 3) Canonical rows + asset candidates
    enabled_games = get_enabled_games()

    rows: List[Dict[str, Any]] = []
    asset_candidates: List[Dict[str, Any]] = []
    route_miss = 0
    canonical_errors = 0
    canonical_error_rows: List[Dict[str, Any]] = []

    DEBUG_LIMIT_ROUTE_MISS = 20
    DEBUG_LIMIT_CANONICAL_ERROR = 20
    debug_route_miss_count = 0
    debug_canonical_error_count = 0

    for i, path in enumerate(files):
        if i % 200 == 0:
            print(f"[DB UPDATE PROGRESS] {i}/{len(files)} current={path}")

        hier = _inventory_extract_chart_hierarchy(path)

        try:
            from rhythm_ingestion.writers.normalizers import normalize_folder_identity
        except Exception:
            normalize_folder_identity = None

        if normalize_folder_identity is None:
            route_miss += 1
            if debug_route_miss_count < DEBUG_LIMIT_ROUTE_MISS:
                print(f"[DEBUG ROUTE_MISS:NORMALIZER_UNAVAILABLE] path={_safe_log_text(path)} hier={_safe_log_text(hier)}")
                debug_route_miss_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                bucket=_BUCKET_ROUTE_MISS,
                reason_code="NORMALIZER_UNAVAILABLE",
                reason_message="normalize_folder_identity could not be imported",
            )
            continue

        norm = normalize_folder_identity(
            game_folder=hier.get("game_folder"),
            difficulty_folder=hier.get("difficulty_folder"),
            level_folder=hier.get("level_folder"),
        )

        game_id = norm.get("game")
        difficulty = norm.get("difficulty")
        level = norm.get("level")

        if not game_id:
            route_miss += 1
            if debug_route_miss_count < DEBUG_LIMIT_ROUTE_MISS:
                print(f"[DEBUG ROUTE_MISS:GAME_ID_MISSING] path={_safe_log_text(path)} hier={_safe_log_text(hier)}")
                debug_route_miss_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                asset_type="type_A",
                classifier_result="type_A",
                bucket=_BUCKET_ROUTE_MISS,
                reason_code="GAME_ID_MISSING",
                reason_message="normalize_folder_identity did not produce a game_id",
            )
            continue

        try:
            adapter = get_adapter(game_id)
        except Exception as e:
            route_miss += 1
            if debug_route_miss_count < DEBUG_LIMIT_ROUTE_MISS:
                print(f"[DEBUG ROUTE_MISS:GET_ADAPTER_FAILED] game_id={_safe_log_text(game_id)} path={_safe_log_text(path)}")
                debug_route_miss_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                bucket=_BUCKET_NO_ADAPTER,
                reason_code="GET_ADAPTER_FAILED",
                reason_message=f"get_adapter({game_id}) failed",
                exception=e,
            )
            continue

        try:
            validator = get_validator(game_id)
        except Exception as e:
            route_miss += 1
            if debug_route_miss_count < DEBUG_LIMIT_ROUTE_MISS:
                print(f"[DEBUG ROUTE_MISS:GET_VALIDATOR_FAILED] game_id={_safe_log_text(game_id)} path={_safe_log_text(path)}")
                debug_route_miss_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                adapter_id=getattr(adapter, "adapter_id", None),
                bucket=_BUCKET_NO_VALIDATOR,
                reason_code="GET_VALIDATOR_FAILED",
                reason_message=f"get_validator({game_id}) failed",
                exception=e,
            )
            continue

        try:
            payload = _try_build_payload(adapter, path)
        except Exception as e:
            canonical_errors += 1
            if debug_canonical_error_count < DEBUG_LIMIT_CANONICAL_ERROR:
                print(f"[DEBUG CANONICAL_ERROR:TRY_BUILD_PAYLOAD_FAILED] game_id={_safe_log_text(game_id)} path={_safe_log_text(path)}")
                debug_canonical_error_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                adapter_id=getattr(adapter, "adapter_id", None),
                validator_id=getattr(validator, "validator_id", None),
                bucket=_BUCKET_CANONICAL_PAYLOAD_FAIL,
                reason_code="TRY_BUILD_PAYLOAD_FAILED",
                reason_message="_try_build_payload raised",
                exception=e,
                canonical_payload_ok=False,
            )
            continue

        validation_ok: Optional[bool] = None
        try:
            validation_result = validator.validate(payload)
            validation_ok = validation_result.get("ok") if isinstance(validation_result, dict) else bool(validation_result)
        except Exception as e:
            payload.setdefault("diagnostics", {})["validation_error"] = str(e)
            canonical_errors += 1
            if debug_canonical_error_count < DEBUG_LIMIT_CANONICAL_ERROR:
                print(f"[DEBUG CANONICAL_ERROR:VALIDATOR_RAISED] game_id={_safe_log_text(game_id)} path={_safe_log_text(path)}")
                debug_canonical_error_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                adapter_id=getattr(adapter, "adapter_id", None),
                validator_id=getattr(validator, "validator_id", None),
                bucket=_BUCKET_VALIDATOR_FAIL,
                reason_code="VALIDATOR_RAISED",
                reason_message="validator.validate(payload) raised",
                exception=e,
                validation_ok=False,
                canonical_payload_ok=True,
            )
            continue

        observed_kinds = set()
        try:
            for ev in (payload.get("note_events") or []):
                if isinstance(ev, dict) and isinstance(ev.get("kind"), str):
                    observed_kinds.add(ev["kind"])
        except Exception:
            pass

        semantic_missing = [k for k in observed_kinds if k not in SEMANTIC_KINDS]
        coverage = GAME_COVERAGE.get(game_id)
        semantic_level = coverage[0] if coverage else None

        if validation_ok is False:
            canonical_errors += 1
            final_bucket = _BUCKET_SEMANTIC_GAP if semantic_missing else (_BUCKET_COVERAGE_GAP if (coverage and semantic_level != "high") else _BUCKET_VALIDATOR_FAIL)

            if debug_canonical_error_count < DEBUG_LIMIT_CANONICAL_ERROR:
                print(f"[DEBUG CANONICAL_ERROR:VALIDATION_NOT_OK] game_id={_safe_log_text(game_id)} bucket={final_bucket}")
                debug_canonical_error_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                adapter_id=getattr(adapter, "adapter_id", None),
                validator_id=getattr(validator, "validator_id", None),
                bucket=final_bucket,
                reason_code="VALIDATION_NOT_OK",
                reason_message="validator returned ok=False",
                validation_ok=False,
                canonical_payload_ok=True,
            )
            continue

        try:
            canonical_row = adapter.to_canonical_row(payload)
        except Exception as e:
            canonical_errors += 1
            if debug_canonical_error_count < DEBUG_LIMIT_CANONICAL_ERROR:
                print(f"[DEBUG CANONICAL_ERROR:TO_CANONICAL_ROW_FAILED] game_id={_safe_log_text(game_id)} path={_safe_log_text(path)}")
                debug_canonical_error_count += 1

            _append_canonical_error(
                canonical_error_rows,
                source_path=path,
                normalized_game_id=game_id,
                asset_type="type_A",
                classifier_result="type_A",
                adapter_id=getattr(adapter, "adapter_id", None),
                validator_id=getattr(validator, "validator_id", None),
                bucket=_BUCKET_CANONICAL_ROW_FAIL,
                reason_code="TO_CANONICAL_ROW_FAILED",
                reason_message="adapter.to_canonical_row(payload) raised",
                exception=e,
                validation_ok=True,
                canonical_payload_ok=True,
                canonical_row_ok=False,
            )
            continue

        rows.append({"game_id": game_id, "canonical_row": canonical_row})
        asset_candidates.append({
            "candidate_id": f"{game_id}:{path.name}",
            "run_id": run_id,
            "source_path": str(path),
            "basename": path.name,
            "extension": path.suffix.lower(),
            "game_normalized": game_id,
            "difficulty_normalized": difficulty,
            "level_normalized": level,
            "extra_metadata": {"source": run_id, "identity": norm},
        })

    print(f"[DB UPDATE] rows_built={len(rows)} route_miss={route_miss} canonical_errors={canonical_errors}")

    canonical_error_breakdown = _build_canonical_error_breakdown(
        build_id=run_id,
        audit_session_id=audit_session_id,
        source_dir=source_dir,
        runtime_root=runtime_root,
        inventory_count=len(files),
        rows_built=len(rows),
        route_miss=route_miss,
        canonical_errors=canonical_errors,
        error_rows=canonical_error_rows,
    )

    if canonical_error_out is not None:
        canonical_error_out.parent.mkdir(parents=True, exist_ok=True)
        canonical_error_out.write_text(
            json.dumps(canonical_error_breakdown, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[DB UPDATE] canonical_error_out={canonical_error_out}")

    # 4) Asset DB
    print("[DEBUG] entering asset DB stage")
    asset_result = persist_chart_assets_from_candidates(db_path=asset_db, candidates=asset_candidates)

    # 5) Pattern DB
    print("[DEBUG] entering pattern DB stage")
    try:
        pattern_summary = write_from_scan_inventory(
            scan_db_path=inventory_db,
            extractor=phase5_bridge_extractor,
            output_db_path=pattern_db,
            run_id=run_id,
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
        pattern_result = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}

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
        "run_id": run_id,
        "audit_session_id": audit_session_id,
        "generated_at": _utc_now_iso(),
        "inventory_db": str(inventory_db),
        "asset_db": str(asset_db),
        "pattern_db": str(pattern_db),
        "inventory_result": inventory_result,
        "asset_result": asset_result,
        "pattern_result": pattern_result,
        "canonical_error_breakdown": canonical_error_breakdown,
        "canonical_error_out": str(canonical_error_out) if canonical_error_out else None,
    }

# --------------------------------------------------
# CLI Entrypoint & Runtime Baseline Construction
# --------------------------------------------------
def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("Update_Runtime_Dbs")

    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--audit-session-id", default=None)
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--inventory-db", default=str(DEFAULT_INVENTORY_DB))
    parser.add_argument("--asset-db", default=str(DEFAULT_ASSET_DB))
    parser.add_argument("--pattern-db", default=str(DEFAULT_PATTERN_DB))

    parser.add_argument("--json-out", default=None)
    parser.add_argument("--canonical-error-out", default=None)
    parser.add_argument(
        "--runtime-baseline-out",
        default=None,
        help="Optional runtime baseline contract output path.",
    )

    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir)
    runtime_root = Path(args.runtime_root)
    inventory_db = Path(args.inventory_db)
    asset_db = Path(args.asset_db)
    pattern_db = Path(args.pattern_db)

    json_out: Optional[Path] = Path(args.json_out) if args.json_out else None
    canonical_error_out: Optional[Path] = Path(args.canonical_error_out) if args.canonical_error_out else None
    runtime_baseline_out: Optional[Path] = Path(args.runtime_baseline_out) if args.runtime_baseline_out else None

    report = update_runtime_dbs(
        run_id=args.run_id,
        audit_session_id=args.audit_session_id,
        source_dir=source_dir,
        runtime_root=runtime_root,
        inventory_db=inventory_db,
        asset_db=asset_db,
        pattern_db=pattern_db,
        canonical_error_out=canonical_error_out,
    )

    if json_out is not None:
        try:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"[DB UPDATE] json_out={json_out}")
        except Exception as e:
            print(f"[DB UPDATE ERROR] Failed to write json_out path={json_out} error={type(e).__name__}: {e}")
            raise

    # Deployment Governance Gate Baseline Contract
    if runtime_baseline_out is not None:
        def _db_snapshot(path: Path) -> dict:
            return {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }

        baseline = {
            "schema": "rga.runtime_baseline.v1.0",
            "generated_at": _utc_now_iso(),
            "run_id": args.run_id,
            "audit_session_id": args.audit_session_id,
            "runtime_root": str(runtime_root),
            "baseline_ready": (
                inventory_db.exists()
                and asset_db.exists()
                and pattern_db.exists()
            ),
            "databases": {
                "file_scan_inventory.db": _db_snapshot(inventory_db),
                "chart_assets.db": _db_snapshot(asset_db),
                "chart_patterns.db": _db_snapshot(pattern_db),
            },
            "verification_required": True,
            "deployment_gate_required": True,
        }

        runtime_baseline_out.parent.mkdir(parents=True, exist_ok=True)
        runtime_baseline_out.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[RUNTIME BASELINE] path={runtime_baseline_out}")

    return 0

if __name__ == "__main__":
    raise SystemExit(cli_main())
