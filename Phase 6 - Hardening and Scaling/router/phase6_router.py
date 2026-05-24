from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .routing_context import RoutingContext
from .routing_policy import RoutingDecision, RoutingPolicy
from .trigger_router import TriggerContext, TriggerRouter
from .domain_dispatch import build_domain_dispatch, DomainDispatch


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    code: Optional[str] = None
    message: Optional[str] = None


Guard = Any  # expected: guard.evaluate(context) -> GuardResult
DomainHandler = Callable[[RoutingContext], Dict[str, Any]]


class Phase6Router:
    """
    Phase 6 routing coordinator (non-semantic, deterministic).
    Wires to DomainDispatch for songs/games.
    """

    def __init__(
        self,
        *,
        trigger_router: Optional[TriggerRouter] = None,
        guards: Optional[List[Guard]] = None,
        policy: Optional[RoutingPolicy] = None,
        dispatch: Optional[DomainDispatch] = None,
        song_handler: Optional[DomainHandler] = None,
        game_handler: Optional[DomainHandler] = None,
    ) -> None:
        self.trigger_router = trigger_router or TriggerRouter()
        self.guards = guards or []
        self.policy = policy or RoutingPolicy()

        # ✅ wire domain dispatch by default (functional pass)
        self.dispatch = dispatch or build_domain_dispatch()
        self.song_handler = song_handler or self.dispatch.route_songs
        self.game_handler = game_handler or self.dispatch.route_games

    def handle(self, payload: Dict[str, Any], *, trigger: Optional[TriggerContext] = None) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {"status": "STOP", "code": "invalid_payload", "message": "payload must be an object"}

        mode = str(payload.get("mode") or "").strip()
        game_id = payload.get("game_id")
        request_id = payload.get("request_id")

        ctx = RoutingContext(
            mode=mode,
            payload=dict(payload),
            game_id=str(game_id) if isinstance(game_id, str) and game_id else None,
            request_id=str(request_id) if isinstance(request_id, str) and request_id else None,
            trigger_type=getattr(trigger, "trigger_type", "manual") if trigger else "manual",
            source=getattr(trigger, "source", None) if trigger else payload.get("source"),
        )

        # Trigger router (non-blocking)
        try:
            ctx = self.trigger_router.apply(ctx, trigger)
        except Exception:
            pass

        # Guards (fail fast)
        for g in self.guards:
            try:
                r = g.evaluate(ctx)  # type: ignore
            except Exception as e:
                return {"mode": mode, "status": "GUARD_FAIL", "code": "guard_exception", "message": str(e)}

            if not getattr(r, "ok", False):
                return {
                    "mode": mode,
                    "status": "GUARD_FAIL",
                    "code": getattr(r, "code", "guard_fail"),
                    "message": getattr(r, "message", "guard failed"),
                }

        # Policy decision
        decision: RoutingDecision = self.policy.decide(ctx)
        if not getattr(decision, "allowed", False):
            return {
                "mode": mode,
                "status": "STOP",
                "code": getattr(decision, "stop_code", None) or "policy_stop",
                "message": getattr(decision, "stop_message", None) or "stopped by policy",
            }

        route = (getattr(decision, "route", None) or mode).strip().lower()

        if route == "songs":
            out = self.song_handler(ctx)
            if isinstance(out, dict) and "mode" not in out:
                out = dict(out)
                out["mode"] = "songs"
            return out

        if route == "games":
            out = self.game_handler(ctx)
            if isinstance(out, dict) and "mode" not in out:
                out = dict(out)
                out["mode"] = "games"
            return out

        return {"mode": mode, "status": "STOP", "code": "unsupported_mode", "message": f"unsupported mode: {route}"}


def phase6_router(payload: Dict[str, Any]) -> Dict[str, Any]:
    return Phase6Router().handle(payload)


__all__ = ["Phase6Router", "phase6_router", "GuardResult"]