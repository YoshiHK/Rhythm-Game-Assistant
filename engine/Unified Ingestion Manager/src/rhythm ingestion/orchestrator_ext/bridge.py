"""rhythm_ingestion.orchestrator_ext.bridge

Wrapper bridge module.

Purpose:
- Provide a single, stable entrypoint for integrating the orchestrator extension
  layer (booster/stabilizer) without modifying an existing orchestrator.

Non-breaking contract:
- If all FeatureFlags are False, the wrapper behaves as a thin pass-through.
- This module must not import or call Phase 1/2/4 logic directly.

Notes:
- The bridge can wrap either:
  (A) a core object implementing `.run(game_id, chart_path, mode, ...)`, OR
  (B) a module-like object exposing `ingest(source_dir, ...)`.

In case (B), `.run()` treats `chart_path` as a DIRECTORY and delegates to `ingest()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Callable

from .config import OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .stabilizer import OrchestratorStabilizer
from .types import RunMode


class _HasRun(Protocol):
    def run(self, *, game_id: str, chart_path: str, mode: str = 'full', **kwargs: Any) -> Dict[str, Any]: ...


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
    """Adapter that exposes `.run()` by delegating to a module's `ingest()`.

    This supports wiring without modifying the existing orchestrator module.

    Contract:
    - `chart_path` MUST be a directory path.
    - `game_id` is passed as `only_game`.
    """

    ingest_func: Callable[..., int]

    def run(self, *, game_id: str, chart_path: str, mode: str = 'full', **kwargs: Any) -> Dict[str, Any]:
        # Interpret chart_path as a directory for batch ingestion.
        # Preserve existing orchestrator behavior by passing through known kwargs.
        db_path = kwargs.get('db_path')
        dry_run = bool(kwargs.get('dry_run', False))
        json_out = kwargs.get('json_out')
        tips_mode = str(kwargs.get('tips_mode') or 'production')

        # Execute ingest; return a structured wrapper dict.
        exit_code = self.ingest_func(
            source_dir=str(chart_path),
            db_path=db_path,
            dry_run=dry_run,
            only_game=game_id,
            json_out=json_out,
            tips_mode=tips_mode,
        )
        return {
            'passed': exit_code == 0,
            'exit_code': int(exit_code),
            'game_id': game_id,
            'source_dir': str(chart_path),
            'mode': str(mode),
        }


@dataclass
class OrchestratorBridge:
    """Stable .run() surface for both core and wrapped orchestrators."""

    core: _HasRun
    config: OrchestratorExtensionConfig
    stabilizer: Optional[OrchestratorStabilizer] = None

    def __post_init__(self) -> None:
        flags: FeatureFlags = self.config.feature_flags
        if any([
            flags.enable_idempotency,
            flags.enable_retries,
            flags.enable_circuit_breakers,
            flags.enable_safe_fallbacks,
            flags.enable_schema_precheck,
        ]):
            self.stabilizer = OrchestratorStabilizer(self.core, self.config)  # type: ignore[arg-type]
        else:
            self.stabilizer = None

    def run(self, *, game_id: str, chart_path: str, mode: str = 'full', **kwargs: Any) -> Dict[str, Any]:
        """Execute orchestration.

        Mirrors the core orchestrator signature to remain non-breaking.
        """
        try:
            rm = RunMode(str(mode))
        except Exception:
            rm = RunMode.FULL

        if self.stabilizer is not None:
            return self.stabilizer.run(game_id=game_id, chart_path=chart_path, mode=rm, **kwargs)
        return self.core.run(game_id=game_id, chart_path=chart_path, mode=rm.value, **kwargs)


def wrap_orchestrator(core: Any, config: Optional[OrchestratorExtensionConfig] = None) -> OrchestratorBridge:
    """Create a bridge wrapper around an existing orchestrator core.

    Accepted inputs:
    - core implementing `.run(...)`
    - module-like object with `ingest(...)` function

    If config is None, behavior is pass-through (all flags default False).
    """
    cfg = config or OrchestratorExtensionConfig()

    # If core already has .run, use it directly.
    if hasattr(core, 'run') and callable(getattr(core, 'run')):
        return OrchestratorBridge(core=core, config=cfg)

    # If core exposes ingest, wrap it.
    if hasattr(core, 'ingest') and callable(getattr(core, 'ingest')):
        wrapped = _ModuleIngestCore(ingest_func=getattr(core, 'ingest'))
        return OrchestratorBridge(core=wrapped, config=cfg)

    raise TypeError('wrap_orchestrator expects an object with .run() or .ingest().')
