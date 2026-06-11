from __future__ import annotations

import sys

from pathlib import Path
import json

from typing import Any, Callable, Tuple
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Phase5FeedbackLoopBatchRunnerConfig:
    """
    Config for Phase 5 feedback loop batch runner.
    """
    output_filename: str = "pipeline_result.json"
    strict: bool = True
    enable_artifacts: bool = True

def _ensure_import_paths() -> None:
    """
    Ensure repo root and Phase 5 song_recommendation utils directory are importable
    when this runner is executed directly as a script.
    """
    this_file = Path(__file__).resolve()
    phase5_dir = this_file.parent                      # .../Phase 5 - Productionization
    repo_root = this_file.parents[1]                  # .../Github Repository
    song_utils_dir = phase5_dir / "song_recommendation" / "utils"

    for p in (repo_root, phase5_dir, song_utils_dir):
        ps = str(p)
        if ps not in sys.path:
            sys.path.insert(0, ps)


# ---------------------------------------------------------------------
# Imports (support both package and script layouts)
# ---------------------------------------------------------------------

import sys
from pathlib import Path
from typing import Any, Callable, Tuple


def _ensure_import_paths() -> None:
    """
    Ensure repo root, Phase 5 root, and song_recommendation package root
    are importable when this runner is executed directly as a script.

    Canonical policy:
    - Primary import root: song_recommendation.*
    - Legacy fallback: phase5.*
    - Flat imports: last resort only
    """
    this_file = Path(__file__).resolve()

    phase5_root = this_file.parent                       # .../Phase 5 - Productionization
    repo_root = phase5_root.parent                       # .../Github Repository
    song_rec_root = phase5_root / "song_recommendation"  # .../song_recommendation
    utils_dir = song_rec_root / "utils"                  # .../song_recommendation/utils

    for p in (repo_root, phase5_root, song_rec_root, utils_dir):
        ps = str(p)
        if ps not in sys.path:
            sys.path.insert(0, ps)


def _imports() -> Tuple[Callable[..., Any], Callable[..., Any]]:
    """
    Resolve:
    - load_feedback_events
    - run_song_rec_learning_pipeline

    Canonical import policy:
    1) song_recommendation.utils.song_rec_learning_orchestrator
    2) local utils module fallback
    3) legacy phase5.* fallback (only if that package exists)

    MUST always return tuple OR raise.
    """
    _ensure_import_paths()

    errors = []

    # --------------------------------------------------
    # 1) Preferred: canonical package import
    # --------------------------------------------------
    try:
        from song_recommendation.utils.song_rec_learning_orchestrator import (  # type: ignore
            load_feedback_events,
            run_song_rec_learning_pipeline,
        )
        return load_feedback_events, run_song_rec_learning_pipeline
    except Exception as e:
        errors.append(f"[layout-1 song_recommendation.utils.*] {type(e).__name__}: {e}")

    # --------------------------------------------------
    # 2) Script-mode local utils fallback
    # --------------------------------------------------
    try:
        from song_rec_learning_orchestrator import (  # type: ignore
            load_feedback_events,
            run_song_rec_learning_pipeline,
        )
        return load_feedback_events, run_song_rec_learning_pipeline
    except Exception as e:
        errors.append(f"[layout-2 local utils module] {type(e).__name__}: {e}")

    # --------------------------------------------------
    # 3) Legacy package fallback
    # --------------------------------------------------
    try:
        from phase5.song_recommendation.utils.song_rec_learning_orchestrator import (  # type: ignore
            load_feedback_events,
            run_song_rec_learning_pipeline,
        )
        return load_feedback_events, run_song_rec_learning_pipeline
    except Exception as e:
        errors.append(f"[layout-3 legacy phase5.*] {type(e).__name__}: {e}")

    # --------------------------------------------------
    # Final hard failure
    # --------------------------------------------------
    raise ImportError(
        "Unable to import Phase 5 song recommendation learning orchestrator.\n"
        + "\n".join(errors)
    )

def _find_feedback_file(source_dir: Path) -> Optional[Path]:
    """
    Locate a supported feedback events file inside source_dir.

    Priority order:
    1. interpretation output (current pipeline)
    2. legacy feedback event files
    3. structured events fallback (optional, last resort)

    Returns:
        Path to the first valid file found, or None if not found.
    """

    # --------------------------------------------------
    # 1) Preferred: interpretation output (your current pipeline)
    # --------------------------------------------------
    for name in (
        "interpreted_feedback_events.json",
        "interpreted_feedback_events.jsonl",
        "interpreted_feedback_events.ndjson",
    ):
        p = source_dir / name
        if p.exists() and p.is_file():
            return p

    # --------------------------------------------------
    # 2) Legacy feedback event naming (older pipeline)
    # --------------------------------------------------
    for name in (
        "feedback_events.json",
        "feedback_events.jsonl",
        "feedback_events.ndjson",
    ):
        p = source_dir / name
        if p.exists() and p.is_file():
            return p

    # --------------------------------------------------
    # 3) Fallback: structured events (optional compatibility)
    #    Only used if nothing else is found.
    # --------------------------------------------------
    for name in (
        "structured_events.json",
    ):
        p = source_dir / name
        if p.exists() and p.is_file():
            return p

    # --------------------------------------------------
    # 4) No valid file found
    # --------------------------------------------------
    return None


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _resolve_artifact_dir(artifact_root_dir: str | Path) -> Path:
    """
    Build artifact dir in the format:

        /artifacts/<date>/<date>_<run>/
    """
    root = Path(artifact_root_dir)
    date_str = _today_str()
    date_dir = root / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    existing_runs = []
    prefix = f"{date_str}_"

    for child in date_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            if suffix.isdigit():
                existing_runs.append(int(suffix))

    next_run = max(existing_runs, default=0) + 1
    run_dir = date_dir / f"{date_str}_{next_run}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_phase5_feedback_loop_batch(
    source_dir: str | Path,
    *,
    artifact_root_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    config: Phase5FeedbackLoopBatchRunnerConfig = Phase5FeedbackLoopBatchRunnerConfig(),
) -> Dict[str, Any]:
    """
    Run the currently executable Phase 5 feedback loop in batch mode.
    """
    load_feedback_events, run_song_rec_learning_pipeline = _imports()

    source_path = Path(source_dir)
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"source_dir not found or not a directory: {source_path}")

    feedback_file = _find_feedback_file(source_path)
    if feedback_file is None:
        raise FileNotFoundError("No supported feedback events file found in source_dir")

    events = load_feedback_events(feedback_file)

    if artifact_root_dir is not None:
        artifacts_root = _resolve_artifact_dir(artifact_root_dir)
    elif output_dir is not None:
        artifacts_root = Path(output_dir)
        artifacts_root.mkdir(parents=True, exist_ok=True)
    else:
        artifacts_root = source_path / config.artifact_subdir

    pipeline_result = run_song_rec_learning_pipeline(
        events=events,
        artifact_root_dir=artifacts_root,
    )

    return {
        "runner": "phase5_feedback_loop_batch_runner",
        "phase": "phase5",
        "source_dir": str(source_path),
        "input": {
            "feedback_events_file": str(feedback_file),
            "feedback_events_count": len(events),
        },
        "artifact_dir": str(artifacts_root),
        "result": pipeline_result,
    }


if __name__ == "__main__":
    import argparse
    import json
    import sys
    import traceback

    parser = argparse.ArgumentParser(description="Run Phase 5 feedback loop batch")
    parser.add_argument("--source_dir", required=True)
    parser.add_argument("--artifact_root_dir", required=False, default=None)
    parser.add_argument("--output_dir", required=False, default=None)
    args = parser.parse_args()

    try:
        result = run_phase5_feedback_loop_batch(
            args.source_dir,
            artifact_root_dir=args.artifact_root_dir,
            output_dir=args.output_dir,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)
