from __future__ import annotations

"""
offline_pipeline_runner.py
"""

# --------------------------------------------------
# Encoding safety
# --------------------------------------------------
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --------------------------------------------------
# Standard imports
# --------------------------------------------------
import argparse
import inspect
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set, Tuple

from rhythm_ingestion.runtime_meta import RuntimeMetaManager
from rhythm_ingestion.orchestrator import ingest

from rhythm_ingestion.runtime_meta import (
    run_file_scan_wrapper,
    run_tips_wrapper,
    run_personalization_wrapper,
    run_localization_wrapper,
    run_song_recommendation_wrapper,
    run_recommendation_wrapper,
)

# --------------------------------------------------
# Path helpers
# --------------------------------------------------
def _normalize_source_path(value: str) -> str:
    return str(value).replace("\\", "/").casefold()


def _load_inventory_stat_cache(file_scan_db: Path) -> Dict[str, Tuple[int, int]]:
    cache: Dict[str, Tuple[int, int]] = {}

    if not file_scan_db or not Path(file_scan_db).exists():
        return cache

    with sqlite3.connect(str(file_scan_db)) as conn:
        rows = conn.execute(
            """
            SELECT source_path, size, mtime_ns
            FROM file_scan_inventory
            WHERE source_path IS NOT NULL
            """
        ).fetchall()

    for source_path, size, mtime_ns in rows:
        if source_path is None:
            continue
        norm = _normalize_source_path(str(source_path))
        cache[norm] = (int(size or 0), int(mtime_ns or 0))

    return cache


def _load_asset_source_path_cache(chart_assets_db: Path) -> Set[str]:
    covered: Set[str] = set()

    if not chart_assets_db or not Path(chart_assets_db).exists():
        return covered

    with sqlite3.connect(str(chart_assets_db)) as conn:
        rows = conn.execute(
            """
            SELECT source_path
            FROM chart_assets
            WHERE source_path IS NOT NULL
            """
        ).fetchall()

    for (source_path,) in rows:
        if source_path is None:
            continue
        covered.add(_normalize_source_path(str(source_path)))

    return covered


def _should_skip_asset_conversion(
    path: Path,
    inventory_stat_cache: Dict[str, Tuple[int, int]],
    asset_source_path_cache: Set[str],
) -> bool:
    norm_path = _normalize_source_path(str(path))

    if norm_path not in inventory_stat_cache:
        return False

    if norm_path not in asset_source_path_cache:
        return False

    try:
        st = path.stat()
    except Exception:
        return False

    current_size = int(st.st_size)
    current_mtime_ns = int(st.st_mtime_ns)

    baseline_size, baseline_mtime_ns = inventory_stat_cache[norm_path]

    return current_size == baseline_size and current_mtime_ns == baseline_mtime_ns


# --------------------------------------------------
# Safe kwargs forwarding
# --------------------------------------------------
def _call_with_supported_kwargs(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    sig = inspect.signature(fn)
    params = sig.parameters

    accepts_var_kw = any(
        p.kind is inspect.Parameter.VAR_KEYWORD
        for p in params.values()
    )

    if accepts_var_kw:
        return fn(*args, **kwargs)

    filtered = {k: v for k, v in kwargs.items() if k in params}
    return fn(*args, **filtered)


# --------------------------------------------------
# Ingest wrapper
# --------------------------------------------------
def _build_ingest_wrapper(
    *,
    enable_converter_cache: bool,
    file_scan_db: Optional[str],
    chart_assets_db: Optional[str],
) -> Callable[..., Any]:

    inventory_stat_cache: Dict[str, Tuple[int, int]] = {}
    asset_source_path_cache: Set[str] = set()

    if enable_converter_cache:
        if file_scan_db:
            inventory_stat_cache = _load_inventory_stat_cache(Path(file_scan_db))
        if chart_assets_db:
            asset_source_path_cache = _load_asset_source_path_cache(Path(chart_assets_db))

        print(
            f"[CACHE] enabled=1 inventory_entries={len(inventory_stat_cache)} "
            f"asset_entries={len(asset_source_path_cache)}"
        )
    else:
        print("[CACHE] enabled=0")

    def _wrapped_ingest(*args: Any, **kwargs: Any) -> Any:
        local_kwargs = dict(kwargs)

        if "chart_asset_db" not in local_kwargs:
            local_kwargs["chart_asset_db"] = chart_assets_db

        if enable_converter_cache:
            local_kwargs.update({
                "enable_converter_cache": True,
                "file_scan_db": file_scan_db,
                "chart_assets_db": chart_assets_db,
                "inventory_stat_cache": inventory_stat_cache,
                "asset_source_path_cache": asset_source_path_cache,
                "path_normalizer": _normalize_source_path,
                "asset_conversion_skip_predicate": _should_skip_asset_conversion,
            })

        return _call_with_supported_kwargs(ingest, *args, **local_kwargs)

    return _wrapped_ingest


# --------------------------------------------------
# Core runner
# --------------------------------------------------
def run_pipeline(
    source_dir: str,
    *,
    enable_converter_cache: bool = False,
    file_scan_db: Optional[str] = None,
    chart_assets_db: Optional[str] = None,
) -> Any:

    runtime_meta = RuntimeMetaManager()

    ingest_wrapper = _build_ingest_wrapper(
        enable_converter_cache=enable_converter_cache,
        file_scan_db=file_scan_db,
        chart_assets_db=chart_assets_db,
    )

    ingest_kwargs: Dict[str, Any] = {
        "tips_mode": "production",
        "skip_known_assets": True,
        "chart_asset_db": chart_assets_db,
    }

    if enable_converter_cache:
        ingest_kwargs.update({
            "enable_converter_cache": True,
            "file_scan_db": file_scan_db,
            "chart_assets_db": chart_assets_db,
        })

    result = runtime_meta.run_full_pipeline(
        source_dir=source_dir,
        ingest_fn=ingest_wrapper,
        scan_fn=run_file_scan_wrapper,
        tips_fn=run_tips_wrapper,
        personalization_fn=run_personalization_wrapper,
        localization_fn=run_localization_wrapper,
        song_recommendation_fn=run_song_recommendation_wrapper,
        recommendation_fn=run_recommendation_wrapper,
        ingest_kwargs=ingest_kwargs,
    )

    return result


# --------------------------------------------------
# CLI
# --------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", required=True)
    parser.add_argument("--enable-converter-cache", action="store_true")
    parser.add_argument("--file-scan-db", default=None)
    parser.add_argument("--chart-assets-db", default=None)

    args = parser.parse_args()

    result = run_pipeline(
        args.source_dir,
        enable_converter_cache=bool(args.enable_converter_cache),
        file_scan_db=args.file_scan_db,
        chart_assets_db=args.chart_assets_db,
    )

    print("Pipeline completed:")
    print(result)