"""
rhythm_ingestion.orchestrator_ext.bridge
Wrapper bridge module.

Purpose:
- Provide a single, stable entrypoint for integrating the orchestrator extension
  layer (booster/stabilizer) without modifying an existing orchestrator.

Non-breaking contract:
- If all FeatureFlags are False, the wrapper behaves as a thin pass-through.
- This module must not import or call Phase 1/2/4 logic directly.

Notes:
- The bridge can wrap either:
  (A) a core object implementing .run(game_id, chart_path, mode, ...), OR
  (B) a module-like object exposing ingest(source_dir, ...).
- In case (B), .run() treats chart_path as a DIRECTORY and delegates to ingest().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from .config import OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .stabilizer import OrchestratorStabilizer
from .types import RunMode


@runtime_checkable
class _HasRun(Protocol):
    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class _HasIngest(Protocol):
    def ingest(
        self,
        source_dir: str,
        *,
        db_path: Optional[str],
        dry_run: bool,
        only_game: Optional[str],
        json_out: Optional[str],
        tips_mode: str,
    ) -> int: ...


@dataclass
class _ModuleIngestCore:
    """
    Adapter that exposes .run() by delegating to a module's ingest().

    Contract:
    - chart_path is interpreted as source_dir (directory)
    - returns a dict suitable for control-plane reporting
    """
    module: _HasIngest

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        source_dir = str(chart_path)
        db_path = kwargs.get("db_path")
        dry_run = bool(kwargs.get("dry_run", False))
        only_game = kwargs.get("only_game", game_id)
        json_out = kwargs.get("json_out")
        tips_mode = str(kwargs.get("tips_mode", "production"))

        rc = self.module.ingest(
            source_dir,
            db_path=db_path,
            dry_run=dry_run,
            only_game=only_game,
            json_out=json_out,
            tips_mode=tips_mode,
        )

        return {
            "game_id": game_id,
            "chart_id": source_dir,
            "mode": mode,
            "status": "OK" if int(rc) == 0 else "FAIL",
            "details": {"return_code": int(rc)},
        }


@dataclass
class _ModeCoercingCore:
    """
    Adapter around OrchestratorStabilizer that accepts mode as str and coerces to RunMode.

    This keeps the external surface stable:
        .run(..., mode: str, ...) -> Dict[str, Any]
    """
    stabilizer: OrchestratorStabilizer

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Best-effort mapping: unknown strings fall back to FULL
        m = (mode or "full").strip().lower()
        if m == RunMode.INGEST.value:
            rm = RunMode.INGEST
        elif m == RunMode.TIPS.value:
            rm = RunMode.TIPS
        elif m == RunMode.PERSONALIZED.value:
            rm = RunMode.PERSONALIZED
        else:
            rm = RunMode.FULL

        return self.stabilizer.run(game_id=game_id, chart_path=chart_path, mode=rm, **kwargs)


@dataclass
class OrchestratorBridge:
    """
    Stable .run() surface for both core and wrapped orchestrators.

    External callers (e.g., recommend.py) should depend ONLY on this surface.
    """
    core: _HasRun
    config: OrchestratorExtensionConfig

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.core.run(game_id=game_id, chart_path=chart_path, mode=mode, **kwargs)


def _flags_any_enabled(flags: FeatureFlags) -> bool:
    """
    Return True if any known feature flag is enabled.

    We use getattr() so this stays additive if flags gain new fields.
    """
    names = [
        # Booster
        "enable_run_plan",
        "enable_preflight_checks",
        "enable_capability_matrix",
        "enable_reasoned_gates",
        # Stabilizer
        "enable_idempotency",
        "enable_retries",
        "enable_circuit_breakers",
        "enable_safe_fallbacks",
        "enable_schema_precheck",
        # Observability
        "enable_run_report",
        "enable_metrics",
    ]
    return any(bool(getattr(flags, n, False)) for n in names)


def wrap_orchestrator(
    core: Any,
    config: Optional[OrchestratorExtensionConfig] = None,
) -> OrchestratorBridge:
    """
    Create a bridge wrapper around an existing orchestrator core.

    Non-breaking behavior:
    - If all FeatureFlags are False: pass-through (no stabilizer).
    - If any extension flags are enabled: wrap with OrchestratorStabilizer (control-plane only).

    Accepts:
    - a core object implementing .run(...), OR
    - a module-like object implementing ingest(...)

    Returns:
    - OrchestratorBridge with a stable .run() surface.
    """
    cfg = config or OrchestratorExtensionConfig()
    flags: FeatureFlags = cfg.feature_flags

    # Normalize core into a .run() surface
    if isinstance(core, _HasRun):
        base_core: _HasRun = core
    elif isinstance(core, _HasIngest):
        base_core = _ModuleIngestCore(module=core)
    else:
        raise TypeError("core must implement .run(...) or ingest(...)")

    # Pass-through if no extension behavior enabled
    if not _flags_any_enabled(flags):
        return OrchestratorBridge(core=base_core, config=cfg)

    # Wrap with stabilizer, but preserve stable mode:str surface externally
    stabilized = OrchestratorStabilizer(core=base_core, config=cfg)
    stable_core = _ModeCoercingCore(stabilizer=stabilized)

    return OrchestratorBridge(core=stable_core, config=cfg)


__all__ = ["OrchestratorBridge", "wrap_orchestrator"]