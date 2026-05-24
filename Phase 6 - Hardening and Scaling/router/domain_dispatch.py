"""
domain_dispatch.py (Phase 6 / Router Layer)

Purpose
-------
Provide Phase 6 domain dispatch handlers for:
- Song Recommendation domain (mode="songs")
- Game Recommendation domain (mode="games", Phase 7)

This module is wiring-only and must remain non-semantic.

Design Constraints:
- MUST NOT interpret gameplay semantics
- MUST NOT contain recommendation "quality" logic
- MUST NOT mutate payload contents
- MUST provide deterministic, explicit STOP/DEGRADED responses on failure
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol

# Router context type (kept generic to avoid circular dependency)
# DomainDispatch expects context to expose:
# - mode (str)
# - payload (dict)
# - game_id (optional str)
# - request_id (optional str)


# ---------------------------------------------------------------------
# Types / Protocols
# ---------------------------------------------------------------------

class GameRouter(Protocol):
    """Phase 7 router boundary (or façade)."""
    def route(self, context: Any) -> Dict[str, Any]: ...


CatalogLoaderFn = Callable[[str, Any], Any]  # (game_id, context) -> SongCatalog


@dataclass(frozen=True)
class DomainDispatchConfig:
    # Rotation cap for action="save"
    max_history: int = 10
    # Default response locale if none provided
    default_locale: str = "en-US"


# ---------------------------------------------------------------------
# STOP / DEGRADED helpers (explicit, machine-readable)
# ---------------------------------------------------------------------

def _stop(*, context: Any, code: str, message: str) -> Dict[str, Any]:
    return {
        "status": "STOP",
        "code": code,
        "message": message,
        "mode": getattr(context, "mode", None),
        "game_id": getattr(context, "game_id", None),
        "request_id": getattr(context, "request_id", None),
    }


def _degraded(*, context: Any, code: str, message: str) -> Dict[str, Any]:
    return {
        "status": "DEGRADED",
        "code": code,
        "message": message,
        "mode": getattr(context, "mode", None),
        "game_id": getattr(context, "game_id", None),
        "request_id": getattr(context, "request_id", None),
    }


# ---------------------------------------------------------------------
# Domain dispatch
# ---------------------------------------------------------------------

class DomainDispatch:
    """
    Holds the two domain handlers:
    - route_songs
    - route_games

    Catalog loading strategy:
    - If catalog_loader_fn is provided: use it (preferred for tests/custom layouts)
    - Else: build deterministic in-memory catalog via load_catalog_from_artifacts()
      (CI-safe, no filesystem I/O)
    """

    def __init__(
        self,
        *,
        game_router: Optional[GameRouter] = None,
        capability_registry: Optional[Dict[str, Any]] = None,
        config: DomainDispatchConfig = DomainDispatchConfig(),
        catalog_loader_fn: Optional[CatalogLoaderFn] = None,
    ) -> None:
        self._game_router = game_router
        self._config = config
        self._catalog_loader_fn = catalog_loader_fn
        self._capability_registry = capability_registry if isinstance(capability_registry, dict) else None

        # Import Phase 6 song pipeline components (domain layer)
        from song_recommendations.request_normalizer import normalize_song_recommendation_request
        from song_recommendations.game_capability_resolver import resolve_game_capability
        from song_recommendations.song_rec_coordinator import generate_recommendation_items
        from song_recommendations.persistence_policy import compute_persistence_plan
        from song_recommendations.response_shaper import shape_song_recommendation_response
        from song_recommendations.catalog.catalog_selector import make_catalog_selector, SelectorConfig
        from song_recommendations.catalog.catalog_loader import load_catalog_from_artifacts

        self._normalize_req = normalize_song_recommendation_request
        self._resolve_cap = resolve_game_capability
        self._generate_items = generate_recommendation_items
        self._persistence_plan = compute_persistence_plan
        self._shape_resp = shape_song_recommendation_response
        self._make_selector = make_catalog_selector
        self._selector_cfg = SelectorConfig()
        self._load_catalog_from_artifacts = load_catalog_from_artifacts

        # Deterministic cache by game_id (memory only)
        self._catalog_cache: Dict[str, Any] = {}

    def _load_catalog(self, *, game_id: str, context: Any, cap: Any) -> Any:
        # deterministic cache first
        if game_id in self._catalog_cache:
            return self._catalog_cache[game_id]

        if self._catalog_loader_fn is not None:
            catalog = self._catalog_loader_fn(game_id, context)
            self._catalog_cache[game_id] = catalog
            return catalog

        # CI-safe deterministic fallback: synthesize from capability tiers
        catalog = self._load_catalog_from_artifacts(game_id=game_id, capability=cap)
        self._catalog_cache[game_id] = catalog
        return catalog

    # -----------------------------
    # songs domain
    # -----------------------------
    def route_songs(self, context: Any) -> Dict[str, Any]:
        payload = getattr(context, "payload", None)
        if not isinstance(payload, dict):
            return _stop(
                context=context,
                code="STOP_INVALID_PAYLOAD",
                message="Song recommendation requires an object payload.",
            )

        # Normalize request (contract enforced by domain layer)
        try:
            req = self._normalize_req(payload)
        except Exception as e:
            return _stop(
                context=context,
                code="STOP_REQUEST_CONTRACT",
                message=f"Request normalization failed: {e}",
            )

        # Resolve game capability (ordering only)
        try:
            cap = self._resolve_cap(req.game_id, capabilities=self._capability_registry)
        except Exception as e:
            return _stop(
                context=context,
                code="STOP_CAPABILITY_RESOLUTION",
                message=f"Game capability resolution failed: {e}",
            )

        # Load catalog (read-only)
        try:
            catalog = self._load_catalog(game_id=req.game_id, context=context, cap=cap)
        except Exception as e:
            return _stop(
                context=context,
                code="STOP_CATALOG_LOAD",
                message=f"Catalog load failed: {e}",
            )

        # Build deterministic selector
        try:
            selector = self._make_selector(catalog, config=self._selector_cfg)
        except Exception as e:
            return _degraded(
                context=context,
                code="DEGRADED_SELECTOR_INIT",
                message=f"Selector initialization failed: {e}",
            )

        # Generate items deterministically
        try:
            items, diagnostics = self._generate_items(req, cap, selector=selector)
        except Exception as e:
            return _degraded(
                context=context,
                code="DEGRADED_COORDINATOR_ERROR",
                message=f"Coordinator failed: {e}",
            )

        # Persistence planning (no I/O)
        try:
            plan = self._persistence_plan(req, items=items, max_history=self._config.max_history)
        except Exception as e:
            return _degraded(
                context=context,
                code="DEGRADED_PERSISTENCE_POLICY",
                message=f"Persistence policy failed: {e}",
            )

        # Shape final response
        try:
            return self._shape_resp(req, items=list(items), persistence=plan, diagnostics=diagnostics, status="OK")
        except Exception as e:
            return _degraded(
                context=context,
                code="DEGRADED_RESPONSE_SHAPER",
                message=f"Response shaping failed: {e}",
            )

    # -----------------------------
    # games domain
    # -----------------------------
    def route_games(self, context: Any) -> Dict[str, Any]:
        if self._game_router is None:
            return _stop(
                context=context,
                code="STOP_GAMES_NOT_WIRED",
                message="Game recommendation router (Phase 7) is not wired.",
            )
        try:
            return self._game_router.route(context)
        except Exception as e:
            return _degraded(
                context=context,
                code="DEGRADED_GAMES_ROUTER_ERROR",
                message=f"Game router failed: {e}",
            )


# ---------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------

def build_domain_dispatch(
    *,
    game_router: Optional[GameRouter] = None,
    capability_registry: Optional[Dict[str, Any]] = None,
    config: DomainDispatchConfig = DomainDispatchConfig(),
    catalog_loader_fn: Optional[CatalogLoaderFn] = None,
) -> DomainDispatch:
    """
    Factory to construct DomainDispatch with injected providers.

    NOTE: This is wiring-only. No semantics, no I/O required by default.
    """
    return DomainDispatch(
        game_router=game_router,
        capability_registry=capability_registry,
        config=config,
        catalog_loader_fn=catalog_loader_fn,
    )


__all__ = ["DomainDispatchConfig", "DomainDispatch", "build_domain_dispatch"]