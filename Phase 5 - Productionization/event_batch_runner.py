from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EventBatchRunnerConfig:
    """
    Batch runner for the Phase 5 events entry layer.

    This runner routes raw payloads into structured events using event_router.
    """
    allow_jsonl: bool = True
    allow_json_array: bool = True
    event_type_field: str = "event_category"
    output_filename: str = "structured_events.json"
    strict: bool = True



def _imports():
    try:
        from events.event_router import route_event
    except Exception:
        try:
            from event_router import route_event
        except Exception as e:
            raise e
    return route_event

def _load_items(path: Path, config: EventBatchRunnerConfig) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if config.allow_jsonl and path.suffix.lower() in {".jsonl", ".ndjson"}:
        out: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        return out

    if config.allow_json_array:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict):
            node = obj.get("items") or obj.get("events")
            if isinstance(node, list):
                return [x for x in node if isinstance(x, dict)]
            return [obj]

    raise ValueError(f"Unsupported input format: {path}")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _resolve_artifact_dir(artifact_root_dir: str | Path) -> Path:
    """
    Build artifact dir in the format:

        /artifacts/<date>/<date>_<run>/

    Run number increments from 1 upward based on existing folders.
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


def run_event_batch(
    source_path: str | Path,
    *,
    artifact_root_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    config: EventBatchRunnerConfig = EventBatchRunnerConfig(),
) -> Dict[str, Any]:
    """
    Batch route raw payloads into structured Phase 5 events.

    Expected input item shape:
    {
      "event_category": "feedback" | "telemetry" | "marketplace" | "safety",
      ...builder kwargs...
    }

    Optional wrapper shape:
    {
      "event_category": "...",
      "payload": {...}
    }
    """
    route_event = _imports()

    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"source_path not found: {src}")

    items = _load_items(src, config)
    structured: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            failed.append({"index": idx, "reason": "item_not_dict"})
            if config.strict:
                raise ValueError(f"Item {idx} is not a dict")
            continue

        event_category = item.get(config.event_type_field)
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else item

        if isinstance(payload, dict) and config.event_type_field in payload:
            payload = dict(payload)
            payload.pop(config.event_type_field, None)

        try:
            event = route_event(
                event_category=event_category,
                payload=payload,
            )
            structured.append(event)
        except Exception as e:
            failed.append({"index": idx, "reason": str(e)})
            if config.strict:
                raise

    result = {
        "runner": "event_batch_runner",
        "source_path": str(src),
        "total_items": len(items),
        "structured_count": len(structured),
        "failed_count": len(failed),
        "failed": failed,
        "events": structured,
    }

    final_output_dir: Optional[Path] = None

    if artifact_root_dir is not None:
        final_output_dir = _resolve_artifact_dir(artifact_root_dir)
    elif output_dir is not None:
        final_output_dir = Path(output_dir)
        final_output_dir.mkdir(parents=True, exist_ok=True)

    if final_output_dir is not None:
        out_path = final_output_dir / config.output_filename
        out_path.write_text(
            json.dumps(structured, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        result["artifact_dir"] = str(final_output_dir)
        result["output_path"] = str(out_path)

    return result


if __name__ == "__main__":
    import argparse
    import json
    import sys
    import traceback

    parser = argparse.ArgumentParser(description="Run Phase 5 entry event batch routing")
    parser.add_argument("--source_path", required=True)
    parser.add_argument("--artifact_root_dir", required=False, default=None)
    parser.add_argument("--output_dir", required=False, default=None)
    args = parser.parse_args()

    try:
        result = run_event_batch(
            args.source_path,
            artifact_root_dir=args.artifact_root_dir,
            output_dir=args.output_dir,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)