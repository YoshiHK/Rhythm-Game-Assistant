from __future__ import annotations

import argparse
import inspect
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FeedbackInterpretationBatchRunnerConfig:
    """
    Batch runner for engine/feedback interpretation.

    This runner consumes feedback_event objects and emits:
    - derived_reason only
    OR
    - enriched feedback events (if interpretation bridge is available)
    """
    allow_jsonl: bool = True
    allow_json_array: bool = True
    output_filename: str = "interpreted_feedback_events.json"
    strict: bool = True


# -----------------------------------------------------------------------------
# Imports / resolution
# -----------------------------------------------------------------------------

def _resolve_callable(module: Any, names: Tuple[str, ...]) -> Optional[Callable[..., Any]]:
    for name in names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    return None


def _ensure_import_paths() -> None:
    """
    Ensure repo root and key engine/feedback subdirs are importable when
    this script is executed directly.

    Repo layout expected:
      repo_root/
        engine/
          feedback/
            feedback_interpretation_batch_runner.py
            interpreter/
              feedback_interpreter.py
            bridge/
              interpretation_bridge.py
    """
    this_file = Path(__file__).resolve()
    feedback_dir = this_file.parent                    # .../engine/feedback
    interpreter_dir = feedback_dir / "interpreter"    # .../engine/feedback/interpreter
    bridge_dir = feedback_dir / "bridge"              # .../engine/feedback/bridge
    repo_root = this_file.parents[2]                  # .../Github Repository

    for p in (repo_root, feedback_dir, interpreter_dir, bridge_dir):
        ps = str(p)
        if ps not in sys.path:
            sys.path.insert(0, ps)


def _imports() -> Tuple[Optional[Callable[..., Any]], Optional[Callable[..., Any]]]:
    """
    Import interpreter + optional bridge with flexible fallback.

    Prefer bridge first, because bridge is more likely to accept the full event.
    """
    _ensure_import_paths()

    interpret_feedback = None
    enrich_feedback_event = None

    # --------------------------------------------------
    # 1) Prefer bridge imports first
    # --------------------------------------------------
    try:
        from engine.feedback.bridge.interpretation_bridge import enrich_feedback_event as _efn  # type: ignore
        enrich_feedback_event = _efn
    except Exception:
        try:
            from bridge.interpretation_bridge import enrich_feedback_event as _efn  # type: ignore
            enrich_feedback_event = _efn
        except Exception:
            enrich_feedback_event = None

    # --------------------------------------------------
    # 2) Try engine.feedback package exports
    # --------------------------------------------------
    try:
        import engine.feedback as fb  # type: ignore
        interpret_feedback = _resolve_callable(
            fb,
            ("interpret_feedback", "attach_feedback_reason"),
        )
        if enrich_feedback_event is None:
            enrich_feedback_event = _resolve_callable(
                fb,
                ("enrich_feedback_event",),
            )
    except Exception:
        pass

    # --------------------------------------------------
    # 3) Try interpreter package paths
    # --------------------------------------------------
    if interpret_feedback is None:
        try:
            from engine.feedback.interpreter.feedback_interpreter import interpret_feedback as _ifn  # type: ignore
            interpret_feedback = _ifn
        except Exception:
            try:
                from interpreter.feedback_interpreter import interpret_feedback as _ifn  # type: ignore
                interpret_feedback = _ifn
            except Exception:
                try:
                    from feedback_interpreter import interpret_feedback as _ifn  # type: ignore
                    interpret_feedback = _ifn
                except Exception:
                    interpret_feedback = None

    if not callable(enrich_feedback_event) and not callable(interpret_feedback):
        raise ImportError(
            "Unable to import interpretation callables. "
            "Tried bridge and interpreter package/local fallbacks."
        )

    return interpret_feedback, enrich_feedback_event

# -----------------------------------------------------------------------------
# Invocation helpers
# -----------------------------------------------------------------------------

def _call_interpret_fn(fn: Callable[..., Any], event: Dict[str, Any]) -> Any:
    """
    Call interpret_feedback in a signature-tolerant way.

    Supports:
    - zero-arg call
    - positional event call
    - common keyword call styles
    - keyword-only Phase 5 feedback interpreter signature
    """
    try:
        sig = inspect.signature(fn)
    except Exception:
        return fn(event)

    params = sig.parameters

    # --------------------------------------------------
    # 1) Zero-arg compatibility
    # --------------------------------------------------
    if len(params) == 0:
        return fn()

    # --------------------------------------------------
    # 2) Detect your current keyword-only interpreter signature
    # --------------------------------------------------
    kw_only_names = {
        "trigger",
        "request",
        "run_result",
        "diagnostics",
        "tips_payload",
        "personalization_context",
        "localization_context",
        "provenance_id",
        "rationale",
    }

    if kw_only_names.intersection(params.keys()):
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        context = event.get("context", {}) if isinstance(event.get("context"), dict) else {}

        kwargs: Dict[str, Any] = {}

        if "trigger" in params:
            kwargs["trigger"] = {
                "event_type": event.get("event_type"),
                "payload": payload,
                "context": context,
                "timestamp": event.get("timestamp"),
            }

        if "request" in params:
            kwargs["request"] = {
                "payload": payload,
                "context": context,
            }

        if "run_result" in params:
            kwargs["run_result"] = None

        if "diagnostics" in params:
            kwargs["diagnostics"] = {
                "source_type": event.get("source_type"),
                "system_context": event.get("system_context"),
                "experiment": event.get("experiment"),
            }

        if "tips_payload" in params:
            kwargs["tips_payload"] = payload

        if "personalization_context" in params:
            kwargs["personalization_context"] = context

        if "localization_context" in params:
            kwargs["localization_context"] = {
                "locale": context.get("locale"),
            }

        if "provenance_id" in params:
            kwargs["provenance_id"] = event.get("provenance_id")

        if "rationale" in params:
            kwargs["rationale"] = None

        return fn(**kwargs)

    # --------------------------------------------------
    # 3) Positional attempt
    # --------------------------------------------------
    values = list(params.values())
    first = values[0]

    if first.kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        try:
            return fn(event)
        except TypeError:
            pass

    # --------------------------------------------------
    # 4) Common keyword fallbacks
    # --------------------------------------------------
    for kw in ("raw_event", "event", "payload", "feedback_event"):
        if kw in params:
            return fn(**{kw: event})

    # --------------------------------------------------
    # 5) kwargs fallback
    # --------------------------------------------------
    for p in values:
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return fn(event=event)

    raise TypeError(f"Unsupported interpret_feedback signature: {sig}")

def _call_enrich_fn(fn: Callable[..., Any], event: Dict[str, Any]) -> Any:
    """
    Call enrich_feedback_event in a signature-tolerant way.
    """
    try:
        sig = inspect.signature(fn)
    except Exception:
        return fn(event)

    params = list(sig.parameters.values())

    if len(params) == 0:
        return fn()

    for p in params:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL,):
            return fn(event)

    first = params[0]

    if first.kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        try:
            return fn(event)
        except TypeError:
            pass

    for kw in ("raw_event", "event", "payload", "feedback_event"):
        if kw in sig.parameters:
            return fn(**{kw: event})

    for p in params:
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return fn(event=event)

    return fn(event)


# -----------------------------------------------------------------------------
# Input loading
# -----------------------------------------------------------------------------

def _load_items(path: Path, config: FeedbackInterpretationBatchRunnerConfig) -> List[Dict[str, Any]]:
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
            node = obj.get("events") or obj.get("items")
            if isinstance(node, list):
                return [x for x in node if isinstance(x, dict)]
            return [obj]

    raise ValueError(f"Unsupported input format: {path}")


# -----------------------------------------------------------------------------
# Artifact directory helpers
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def run_feedback_interpretation_batch(
    source_path: str | Path,
    *,
    artifact_root_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    config: FeedbackInterpretationBatchRunnerConfig = FeedbackInterpretationBatchRunnerConfig(),
) -> Dict[str, Any]:
    """
    Batch run engine/feedback interpretation over feedback_event objects.

    Output shape:
    - If bridge is available:
        enriched event dicts
    - Else:
        {
          "raw_event": {...},
          "derived_reason": {...}
        }
    """
    interpret_feedback, enrich_feedback_event = _imports()

    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"source_path not found: {src}")

    events = _load_items(src, config)

    outputs: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            failed.append({"index": idx, "reason": "event_not_dict"})
            if config.strict:
                raise ValueError(f"Event {idx} is not a dict")
            continue

        try:
            if callable(enrich_feedback_event):
                out = _call_enrich_fn(enrich_feedback_event, event)
            elif callable(interpret_feedback):
                interpreted = _call_interpret_fn(interpret_feedback, event)
                out = {
                    "raw_event": event,
                    "derived_reason": interpreted,
                }
            else:
                raise ImportError("No interpretation callable resolved")

            outputs.append(out if isinstance(out, dict) else {"output": out})

        except Exception as e:
            failed.append({"index": idx, "reason": str(e)})
            if config.strict:
                raise

    result = {
        "runner": "feedback_interpretation_batch_runner",
        "source_path": str(src),
        "total_events": len(events),
        "interpreted_count": len(outputs),
        "failed_count": len(failed),
        "failed": failed,
        "outputs": outputs,
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
            json.dumps(outputs, ensure_ascii=False, indent=2, sort_keys=True),
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

    parser = argparse.ArgumentParser(description="Run engine/feedback interpretation batch")
    parser.add_argument("--source_path", required=True)
    parser.add_argument("--artifact_root_dir", required=False, default=None)
    parser.add_argument("--output_dir", required=False, default=None)
    args = parser.parse_args()

    try:
        result = run_feedback_interpretation_batch(
            args.source_path,
            artifact_root_dir=args.artifact_root_dir,
            output_dir=args.output_dir,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
        sys.stdout.flush()
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)
