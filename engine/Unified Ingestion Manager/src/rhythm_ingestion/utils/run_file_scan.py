from __future__ import annotations

from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
import json
import importlib

from rhythm_ingestion.utils.file_scan import (
    scan_directory,
    allocate_run_id,
    commit_scan_state_for_run,
    DEFAULT_CHART_ROOT,
    DEFAULT_STATE_BASE_DIR
)

from rhythm_ingestion.utils.qa_reporter import QASummary
from rhythm_ingestion.utils.tips_meta_builder import build_tips_meta, save_tips_meta
from rhythm_ingestion.utils.logger import log


# -------------------------------------------------
# ✅ Load games.json (single source of truth)
# -------------------------------------------------
def load_games_config() -> Dict[str, Any]:
    path = Path("src/rhythm_ingestion/config/games.json")
    return json.loads(path.read_text(encoding="utf-8"))


def build_extension_map(config: Dict[str, Any]) -> Dict[str, str]:
    ext_map: Dict[str, str] = {}

    for game in config["games"]:
        if game.get("capabilities", {}).get("adapter") != "enabled":
            continue

        exts = game.get("supported_extensions", {}).get("adapter", [])

        for ext in exts:
            ext_map[ext.lower()] = game["game_id"]

    return ext_map


# -------------------------------------------------
# ✅ Smart extension detection (handles multi-ext)
# -------------------------------------------------
def detect_game(path: Path, ext_map: Dict[str, str]) -> Optional[str]:
    name = path.name.lower()

    # ✅ multi-extension special cases
    for ext in sorted(ext_map.keys(), key=len, reverse=True):
        if name.endswith(ext):
            return ext_map[ext]

    return None


# -------------------------------------------------
# ✅ Dynamic adapter + validator loader
# -------------------------------------------------
def load_game_components(game_id: str):
    try:
        adapter_module = importlib.import_module(
            f"adapters.game_specific_adapters.adapter_{game_id}"
        )

        validator_module = importlib.import_module(
            f"validators.game_specific_validators.validator_{game_id}"
        )

        builder = getattr(adapter_module, "build_canonical_payload")

        # class name: ProsekaValidator / ArcaeaValidator / etc
        class_name = "".join([part.capitalize() for part in game_id.split("_")]) + "Validator"
        validator_cls = getattr(validator_module, class_name)

        return builder, validator_cls()

    except Exception as e:
        return None, e


# -------------------------------------------------
# ✅ Multi-game ingestion (proper routing)
# -------------------------------------------------
def run_ingestion(files: List[Path], ext_map: Dict[str, str]) -> QASummary:

    total_charts = 0
    total_success = 0
    total_failed = 0

    by_game: Dict[str, Dict[str, int]] = {}
    failures: List[Dict[str, Any]] = []

    metadata_stats = {
        "combo_mismatch_charts": 0,
        "bpm_mismatch_charts": 0,
        "duration_mismatch_charts": 0,
    }

    for path in files:
        total_charts += 1

        game_id = detect_game(path, ext_map)

        if not game_id:
            total_failed += 1
            failures.append({
                "game_id": "unknown",
                "song_id": None,
                "song_name": None,
                "difficulty": None,
                "error": "Unsupported file extension",
            })
            continue

        builder, validator_or_err = load_game_components(game_id)

        if builder is None:
            total_failed += 1
            failures.append({
                "game_id": game_id,
                "error": f"Adapter loading failed: {validator_or_err}",
            })
            continue

        validator = validator_or_err

        try:
            payload = builder(str(path))
            validator.validate(payload)

            total_success += 1

            if game_id not in by_game:
                by_game[game_id] = {"success": 0, "failed": 0}

            by_game[game_id]["success"] += 1

        except Exception as e:
            total_failed += 1

            if game_id not in by_game:
                by_game[game_id] = {"success": 0, "failed": 0}

            by_game[game_id]["failed"] += 1

            failures.append({
                "game_id": game_id,
                "song_id": None,
                "song_name": None,
                "difficulty": None,
                "error": str(e),
            })

    return QASummary(
        total_charts=total_charts,
        total_success=total_success,
        total_failed=total_failed,
        by_game=by_game,
        failures=failures,
        metadata_stats=metadata_stats,
    )


# -------------------------------------------------
# ✅ Main runner (UMI-compliant)
# -------------------------------------------------
def main():

    chart_root = DEFAULT_CHART_ROOT
    base_dir = DEFAULT_STATE_BASE_DIR

    log(f"Scanning directory: {chart_root}")

    candidates = scan_directory(
    chart_root,
    allowed_extensions=allowed_extensions)

    log(f"Detected {len(candidates)} files")

    if not candidates:
        log("No chart files found. Exiting.")
        return

    # ✅ config-driven routing
    allowed_extensions = sorted(set(ext_map.keys()))

    log(f"Routing map loaded: {len(ext_map)} extensions")

    # ✅ ingestion
    qa = run_ingestion(candidates, ext_map)

    # ✅ run_id
    report_date = date.today().isoformat()
    run_id, _ = allocate_run_id(base_dir, report_date)

    log(f"Run ID: {run_id}")

    # ✅ tips_meta
    payload = build_tips_meta(qa, base_dir=base_dir)
    tips_path = save_tips_meta(payload, base_dir)

    log(f"tips_meta written: {tips_path}")

    # ✅ scan_state pairing
    scan_path, _ = commit_scan_state_for_run(
        candidates,
        base_dir=base_dir,
        run_id=run_id,
        pair_tips_meta_path=tips_path,
    )

    log(f"scan_state written: {scan_path}")

    log("✅ UMI run complete")


# -------------------------------------------------

if __name__ == "__main__":
    main()