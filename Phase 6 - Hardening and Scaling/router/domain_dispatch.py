"""
domain_dispatch.py (Phase 6 / Router Layer)

Purpose
-------
Provide Phase 6 domain dispatch handlers for:
- Song Recommendation domain (mode="songs")
- Game Recommendation domain (mode="games", Phase 7)

This module is wiring-only and must remain non-semantic.

Design Constraints (aligned with Phase 6 Router Layer):
- MUST NOT interpret gameplay semantics
- MUST NOT contain recommendation "quality" logic
- MUST NOT mutate payload contents
- MUST provide deterministic, explicit STOP/DEGRADED responses on failure

The router layer orchestrates, and domain dispatch defines where execution continues.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Tuple


# ---------------------------------------------------------------------
# Types / Protocols
# ---------------------------------------------------------------------

class GameRouter(Protocol):
    """
    Phase 7 router boundary (or façade).
    """
    def route(self, context: Any) -> Dict[str, Any]: ...


# A catalog loader callable boundary (NOT a provider abstraction).
# Signature: (game_id, context) -> SongCatalog
CatalogLoaderFn = Callable[[str, Any], Any]


@dataclass(frozen=True)
class DomainDispatchConfig:
    """
    Wiring knobs (platform-owned).

    Catalog loading:
    - If artifacts_root is provided, DomainDispatch can load SongCatalog from disk
      using catalog_loader.load_catalog_from_dir().
    - If artifacts_root is None, you MUST inject catalog_loader_fn.
    """
    # Rotation cap for action="save"
    max_history: int = 10

    # Default response locale if none provided
    default_locale: str = "en-US"

    # Optional filesystem artifact root for catalogs:
    # Expected layout:
    #   <artifacts_root>/<game_id>/songs.json
    #   <artifacts_root>/<game_id>/producers.json
    #   <artifacts_root>/<game_id>/song_difficulty.json
    artifacts_root: Optional[str] = None
    per_game_subdir: bool = True
    songs_filename: str = "songs.json"
    producers_filename: str = "producers.json"
    difficulty_filename: str = "song_difficulty.json"


# ---------------------------------------------------------------------
# Import helpers (support both package and flat layouts)
# ---------------------------------------------------------------------

def _import_song_recommendation_modules():
    """
    Import Song Recommendation pipeline components with a robust fallback strategy.
    """
    try:
        from phase6.song_recommendation.request_normalizer import normalize_song_recommendation_request
        from phase6.song_recommendation.game_capability_resolver import resolve_game_capability
        from phase6.song_recommendation.song_rec_coordinator import generate_recommendation_items
        from phase6.song_recommendation.persistence_policy import compute_persistence_plan
        from phase6.song_recommendation.response_shaper import shape_song_recommendation_response
        from phase6.song_recommendation.catalog.catalog_selector import make_catalog_selector
        return (
            normalize_song_recommendation_request,
            resolve_game_capability,
            generate_recommendation_items,
            compute_persistence_plan,
            shape_song_recommendation_response,
            make_catalog_selector,
        )
    except Exception:
        from request_normalizer import normalize_song_recommendation_request
        from game_capability_resolver import resolve_game_capability
        from song_rec_coordinator import generate_recommendation_items
        from persistence_policy import compute_persistence_plan
        from response_shaper import shape_song_recommendation_response
        from catalog_selector import make_catalog_selector
        return (
            normalize_song_recommendation_request,
            resolve_game_capability,
            generate_recommendation_items,
            compute_persistence_plan,
            shape_song_recommendation_response,
            make_catalog_selector,
        )


def _import_catalog_loader():
    """
    Import catalog loader (filesystem-based) with fallback strategy.
    """
    try:
        from phase6.song_recommendation.catalog.catalog_loader import load_catalog_from_dir
        return load_catalog_from_dir
    except Exception:
        from catalog_loader import load_catalog_from_dir
        return load_catalog_from_dir


# ---------------------------------------------------------------------
# Registry loading (platform-owned, non-semantic)
# ---------------------------------------------------------------------

def _default_capability_registry_path() -> Optional[Path]:
    """
    Locate capability_registry.json in common repo layouts.
    Best-effort wiring only.
    """
    here = Path(__file__).resolve()

    # Typical: phase6/song_recommendation/capability_registry.json
    candidate = here.parents[1] / "song_recommendation" / "capability_registry.json"
    if candidate.exists():
        return candidate

    return None


def _load_capability_registry(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


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
    - If catalog_loader_fn is provided: use it (preferred for tests or custom layouts)
    - Else: load from filesystem using DomainDispatchConfig.artifacts_root
    """

    def __init__(
        self,
        *,
        game_router: Optional[GameRouter] = None,
        capability_registry: Optional[Dict[str, Any]] = None,
        config: DomainDispatchConfig = DomainDispatchConfig(),
        catalog_loader_fn: Optional[CatalogLoaderFn] = None,
    ):
        self._game_router = game_router
        self._config = config
        self._catalog_loader_fn = catalog_loader_fn

        if isinstance(capability_registry, dict):
            self._capability_registry = capability_registry
        else:
            self._capability_registry = _load_capability_registry(_default_capability_registry_path())

        (
            self._normalize_req,
            self._resolve_cap,
            self._generate_items,
            self._persistence_plan,
            self._shape_resp,
            self._make_selector,
        ) = _import_song_recommendation_modules()

        self._load_catalog_from_dir = _import_catalog_loader()

        # simple in-memory cache (deterministic)
        self._catalog_cache: Dict[str, Any] = {}

    def _load_catalog(self, *, game_id: str, context: Any) -> Any:
        """
        Load SongCatalog either through injected loader function or filesystem artifacts.
        """
        # cache first
        if game_id in self._catalog_cache:
            return self._catalog_cache[game_id]

        if self._catalog_loader_fn is not None:
            catalog = self._catalog_loader_fn(game_id, context)
            self._catalog_cache[game_id] = catalog
            return catalog

        # filesystem fallback
        if not self._config.artifacts_root:
            raise RuntimeError("No catalog_loader_fn provided and artifacts_root is not configured.")

        root = Path(self._config.artifacts_root)
        game_dir = (root / game_id) if self._config.per_game_subdir else root

        catalog = self._load_catalog_from_dir(
            game_id=game_id,
            root_dir=game_dir,
            songs_filename=self._config.songs_filename,
            producers_filename=self._config.producers_filename,
            difficulty_filename=self._config.difficulty_filename,
        )
        self._catalog_cache[game_id] = catalog
        return catalog

    # -----------------------------
    # songs domain
    # -----------------------------
    def route_songs(self, context: Any) -> Dict[str, Any]:
        """
        Domain handler for mode="songs".

        Pipeline (wiring only):
        payload -> request_normalizer
               -> capability_resolver (registry-backed)
               -> catalog_loader (injected or filesystem)
               -> selector
               -> coordinator
               -> persistence_policy
               -> response_shaper
        """

        payload = getattr(context, "payload", None)
        if not isinstance(payload, dict):
            return _stop(
                context=context,
                code="STOP_INVALID_PAYLOAD",
                message="Song recommendation requires a JSON object payload.",
            )

        # Normalize request (non-semantic)
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
            catalog = self._load_catalog(game_id=req.game_id, context=context)
        except Exception as e:
            return _stop(
                context=context,
                code="STOP_CATALOG_LOAD",
                message=f"Catalog load failed: {e}",
            )

        # Build deterministic selector
        try:
            selector = self._make_selector(catalog)
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

        # Persistence planning (no I/O here)
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
            return self._shape_resp(req, items=items, persistence=plan, diagnostics=diagnostics, status="OK")
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
        """
        Domain handler for mode="games".

        Boundary to Phase 7.
        Phase 6 must not implement game ranking semantics here.
        """
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

    NOTE: CatalogProvider abstraction has been intentionally removed.
    Use catalog_loader_fn or filesystem artifacts_root instead.
    """
    return DomainDispatch(
        game_router=game_router,
        capability_registry=capability_registry,
        config=config,
        catalog_loader_fn=catalog_loader_fn,
    )