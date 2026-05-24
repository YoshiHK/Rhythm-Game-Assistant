"""
Phase 6 — Router layer package (public surface)

Goals:
- Provide a stable import surface for integration tests.
- Avoid forcing callers to wire dependencies manually.
- Keep routing non-semantic (mode-based dispatch only).
"""

from .phase6_router import Phase6Router

def build_default_router() -> Phase6Router:
    """
    Construct a Phase6Router with CI-safe defaults.

    This keeps integration tests from skipping due to missing constructor deps.
    """
    # Lazy imports avoid circular deps at import-time
    from .trigger_router import TriggerRouter
    from .routing_policy import RoutingPolicy

    # Domain handlers: wire to real implementations if available,
    # otherwise provide explicit STOP response (non-semantic).
    def _default_song_handler(context):
        return {"mode": "songs", "status": "STOP", "reason": "song_handler_not_wired"}

    def _default_game_handler(context):
        return {"mode": "games", "status": "STOP", "reason": "game_handler_not_wired"}

    return Phase6Router(
        trigger_router=TriggerRouter(),
        guards=[],
        policy=RoutingPolicy(),
        song_handler=_default_song_handler,
        game_handler=_default_game_handler,
    )

def route(payload: dict) -> dict:
    """
    Convenience entrypoint: route a payload through the default router.
    """
    router = build_default_router()
    # Support both common method names
    if hasattr(router, "handle"):
        return router.handle(payload)
    if hasattr(router, "route"):
        return router.route(payload)
    raise AttributeError("Phase6Router has no handle()/route() method")

__all__ = ["Phase6Router", "build_default_router", "route"]