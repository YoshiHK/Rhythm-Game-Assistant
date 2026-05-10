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

from dataclasses import dataclass, is_dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from .config import OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .stabilizer import OrchestratorStabilizer
from .types import RunMode


# ------------------------------------------------------------
# Core surface protocols
# ------------------------------------------------------------

@runtime_checkable
class _HasRun(Protocol):
    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...


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
    ) -> int:
        ...


@runtime_checkable
class _HasRecommend(Protocol):
    def recommend(self, **kwargs: Any) -> Dict[str, Any]:
        ...


# ------------------------------------------------------------
# Adapters
# ------------------------------------------------------------

@dataclass(frozen=True)
class _ModuleIngestCore:
    """
    Adapter that exposes .run() by delegating to a module's ingest().

    This supports legacy/module-style orchestrators that only have:
        ingest(source_dir, db_path=..., dry_run=..., only_game=..., json_out=..., tips_mode=...) -> int

    Bridge contract:
    - .run(chart_path=...) treats chart_path as a DIRECTORY (source_dir).
    - Returns a dict payload with at least diagnostics.
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
        # Coerce legacy ingest params from kwargs with safe defaults
        db_path = kwargs.get("db_path")
        dry_run = bool(kwargs.get("dry_run", False))
        only_game = kwargs.get("only_game", game_id)
        json_out = kwargs.get("json_out")
        tips_mode = str(kwargs.get("tips_mode", "full"))

        # Delegate ingest
        rc = self.module.ingest(
            chart_path,
            db_path=db_path if isinstance(db_path, str) or db_path is None else str(db_path),
            dry_run=dry_run,
            only_game=only_game if isinstance(only_game, str) or only_game is None else str(only_game),
            json_out=json_out if isinstance(json_out, str) or json_out is None else str(json_out),
            tips_mode=tips_mode,
        )

        return {
            "diagnostics": {
                "adapter": "module_ingest",
                "mode": mode,
                "return_code": int(rc),
                "game_id": str(game_id),
                "source_dir": str(chart_path),
            }
        }


@dataclass(frozen=True)
class _ModeCoercingCore:
    """
    Adapter around an inner core that accepts mode as str and coerces to RunMode
    when possible.

    This keeps API callers simple (mode="full"/"rank_only"/etc.), while allowing
    internal extensions to use RunMode consistently.
    """
    core: Any

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        coerced = _coerce_mode(mode)
        # Pass coerced mode through as a string or enum depending on downstream tolerance.
        # We keep it conservative: pass the original string + add normalized_mode.
        kwargs = dict(kwargs)
        kwargs.setdefault("normalized_mode", coerced.value if hasattr(coerced, "value") else str(coerced))
        return self.core.run(game_id=game_id, chart_path=chart_path, mode=str(mode), **kwargs)


# ------------------------------------------------------------
# Bridge (stable entrypoint)
# ------------------------------------------------------------

@dataclass(frozen=True)
class OrchestratorBridge:
    """
    Stable .run() surface for both core and wrapped orchestrators.

    - .run(...) is always available
    - .recommend(...) is optional (delegates if core supports it)
    """
    _core: Any

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not hasattr(self._core, "run"):
            raise TypeError("Wrapped core does not expose .run()")
        return self._core.run(game_id=game_id, chart_path=chart_path, mode=mode, **kwargs)

    def recommend(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Optional convenience method for unified recommend API.

        This only works if the wrapped core exposes `.recommend(**kwargs) -> dict`.
        We intentionally DO NOT emulate recommend via .run(), because .run() is
        chart-level execution and the mapping is ambiguous.
        """
        if hasattr(self._core, "recommend") and callable(getattr(self._core, "recommend")):
            return self._core.recommend(**kwargs)
        raise RuntimeError(
            "Orchestrator core does not support .recommend(). "
            "Wire a recommender that implements recommend(), or call .run() for chart execution."
        )


# ------------------------------------------------------------
# Feature flag logic
# ------------------------------------------------------------

def _flags_any_enabled(flags: FeatureFlags) -> bool:
    """
    Return True if any known feature flag is enabled.

    Robust to FeatureFlags being a dataclass, object with attributes, or dict-like.
    """
    if flags is None:
        return False

    # Dataclass
    if is_dataclass(flags):
        for v in vars(flags).values():
            if bool(v):
                return True
        return False

    # Dict-like
    if isinstance(flags, dict):
        return any(bool(v) for v in flags.values())

    # Attribute-based
    for name in dir(flags):
        if name.startswith("_"):
            continue
        try:
            v = getattr(flags, name)
        except Exception:
            continue
        if isinstance(v, (bool, int)) and bool(v):
            return True
    return False


def _coerce_mode(mode: str) -> RunMode:
    """
    Coerce a string into RunMode when possible.

    - If RunMode is an enum, accept both member.name and member.value.
    - Otherwise, return a best-effort default.
    """
    m = (mode or "").strip()

    # If RunMode behaves like an Enum, try matching names/values
    try:
        for member in RunMode:  # type: ignore
            # member.name
            if getattr(member, "name", "").lower() == m.lower():
                return member
            # member.value
            val = getattr(member, "value", None)
            if isinstance(val, str) and val.lower() == m.lower():
                return member
    except Exception:
        pass

    # Fallback: try common defaults by string
    try:
        return RunMode.FULL  # type: ignore[attr-defined]
    except Exception:
        # Last resort: pick first enum member if iterable
        try:
            return next(iter(RunMode))  # type: ignore
        except Exception as e:
            raise RuntimeError(f"Cannot coerce mode; RunMode unavailable: {e}") from e


# ------------------------------------------------------------
# Factory
# ------------------------------------------------------------

def wrap_orchestrator(
    core: Any,
    config: Optional[OrchestratorExtensionConfig] = None,
) -> OrchestratorBridge:
    """
    Create a bridge wrapper around an existing orchestrator core.

    Behavior:
    - Accepts:
        (A) objects with .run(...)
        (B) module-like objects with .ingest(...)
    - If all FeatureFlags are disabled, returns thin pass-through wrapper.
    - If any FeatureFlag enabled, tries to wrap core with OrchestratorStabilizer.
    - Always returns an OrchestratorBridge with stable .run() surface.
    """
    if core is None:
        raise ValueError("core must not be None")

    # Default config
    if config is None:
        try:
            config = OrchestratorExtensionConfig()  # type: ignore[call-arg]
        except Exception:
            # If config requires parameters, fall back to a minimal stub-like object
            config = OrchestratorExtensionConfig  # type: ignore[assignment]

    # Normalize to a core with .run(...)
    normalized_core: Any = core
    if isinstance(core, _HasIngest) and not hasattr(core, "run"):
        normalized_core = _ModuleIngestCore(module=core)

    # Optional mode coercion wrapper
    if hasattr(normalized_core, "run"):
        normalized_core = _ModeCoercingCore(core=normalized_core)

    # Decide whether to apply stabilizer
    flags = None
    try:
        flags = getattr(config, "feature_flags", None)
    except Exception:
        flags = None

    if flags is not None and _flags_any_enabled(flags):
        try:
            stabilized = OrchestratorStabilizer(core=normalized_core, config=config)  # type: ignore
            return OrchestratorBridge(_core=stabilized)
        except Exception:
            # If stabilizer wiring fails, fall back to pass-through (non-breaking)
            return OrchestratorBridge(_core=normalized_core)

    # Thin pass-through
    return OrchestratorBridge(_core=normalized_core)


__all__ = ["OrchestratorBridge", "wrap_orchestrator"]