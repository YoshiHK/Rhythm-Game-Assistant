"""
Phase 6 Router

Central non-semantic coordinator for Phase 6 execution.

Responsibilities:
- Orchestrate guard evaluation order.
- Invoke lifecycle and integration routing gates.
- Forward immutable routing context.
- Trigger observability hooks.

This module MUST NOT:
- contain business logic,
- interpret gameplay semantics,
- or modify payload contents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from .routing_context import RoutingContext
from .routing_policy import RoutingDecision, RoutingPolicy
from .trigger_router import TriggerContext, TriggerRouter


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    code: Optional[str] = None
    message: Optional[str] = None


Guard = Any  # expected: guard.evaluate(context)->GuardResult
DomainHandler = Callable[[RoutingContext], Dict[str, Any]]


class Phase6Router:
    """
    Phase 6 routing coordinator.

    The router coordinates *when* things run, not *what* they mean.
    """

    def __init__(
        self,
        *,
        trigger_router: TriggerRouter,
        guards: Iterable[Guard],
        policy: RoutingPolicy,
        song_handler: DomainHandler,
        game_handler: DomainHandler,
    ):
        self._trigger_router = trigger_router
        self._guards = list(guards)
        self._policy = policy
        self._song_handler = song_handler
        self._game_handler = game_handler

    def route(self, *, trigger: TriggerContext, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 1) Normalize trigger + routing metadata into immutable context
        context = self._trigger_router.normalize(trigger, payload)

        # 2) Evaluate guards (deterministic order)
        for g in self._guards:
            res = getattr(g, "evaluate", None)
            if callable(res):
                out = res(context)
                if isinstance(out, GuardResult):
                    if not out.ok:
                        return self._stop_response(context, out.code or "STOP_GUARD", out.message or "Guard blocked execution")
                else:
                    # If guard returns a bool, treat False as STOP (avoid runtime failures)
                    if out is False:
                        return self._stop_response(context, "STOP_GUARD", "Guard blocked execution")

        # 3) Apply routing policy (non-semantic)
        decision: RoutingDecision = self._policy.decide(context)
        if not decision.proceed:
            return self._stop_response(context, decision.stop_code or "STOP_POLICY", decision.stop_message or "Policy blocked execution")

        # 4) Dispatch to domain handler based on route
        try:
            if decision.route == "songs":
                return self._song_handler(context)
            if decision.route == "games":
                return self._game_handler(context)
        except Exception as e:
            # Failure isolation: return explicit DEGRADED
            return self._degraded_response(context, "DEGRADED_HANDLER_ERROR", str(e))

        return self._stop_response(context, "STOP_NO_ROUTE", "No valid route selected")

    def _stop_response(self, context: RoutingContext, code: str, message: str) -> Dict[str, Any]:
        return {
            "status": "STOP",
            "code": code,
            "message": message,
            "mode": context.mode,
            "game_id": context.game_id,
            "request_id": context.request_id,
        }

    def _degraded_response(self, context: RoutingContext, code: str, message: str) -> Dict[str, Any]:
        return {
            "status": "DEGRADED",
            "code": code,
            "message": message,
            "mode": context.mode,
            "game_id": context.game_id,
            "request_id": context.request_id,
        }
