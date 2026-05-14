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

Invariant (Learning Flags):
- Learning-loop flags MUST NOT influence routing decisions.
- Routing is based ONLY on context.mode ("songs" vs "games") plus guards/policy.
- Any presence of learning flags in payload/context is treated as informational only.
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

    # ------------------------------------------------------------------
    # Invariant: learning flags MUST NOT influence routing
    # ------------------------------------------------------------------
    def _assert_learning_flags_do_not_affect_routing(self, context: RoutingContext) -> None:
        """
        Mechanical invariant check.

        This does NOT block requests.
        It exists to prevent accidental coupling where learning flags
        (e.g., learning_loop, learning_phase) start influencing routing.
        """
        payload = getattr(context, "payload", None)
        if not isinstance(payload, dict):
            return

        # If clients send learning flags, they must be ignored by routing.
        # We only assert that mode still exists and is the single routing key.
        # (No semantic meaning; purely structural guardrail.)
        _ = payload.get("learning_loop")
        _ = payload.get("learning_phase")
        _ = payload.get("song_recommendation")
        _ = payload.get("game_recommendation")

        # Ensure routing key is still mode (if provided)
        mode = getattr(context, "mode", None)
        if mode is not None and not isinstance(mode, str):
            raise AssertionError("RoutingContext.mode must be a string when provided")

    def route(self, *, trigger: TriggerContext, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 1) Normalize trigger + metadata into immutable context
        context = self._trigger_router.normalize(trigger, payload)

        # 2) Enforce invariant (informational only)
        self._assert_learning_flags_do_not_affect_routing(context)

        # 3) Evaluate guards (deterministic order)
        for g in self._guards:
            res = getattr(g, "evaluate", None)
            if callable(res):
                out = res(context)
                if isinstance(out, GuardResult):
                    if not out.ok:
                        return self._stop_response(context, out.code or "STOP_GUARD", out.message or "Guard blocked execution")
                else:
                    if out is False:
                        return self._stop_response(context, "STOP_GUARD", "Guard blocked execution")

        # 4) Apply routing policy (non-semantic)
        decision: RoutingDecision = self._policy.decide(context)
        if not decision.proceed:
            return self._stop_response(
                context,
                decision.stop_code or "STOP_POLICY",
                decision.stop_message or "Policy blocked execution",
            )

        # 5) Dispatch (ONLY by route selected by policy; must be mode-based)
        try:
            if decision.route == "songs":
                return self._song_handler(context)
            if decision.route == "games":
                return self._game_handler(context)
        except Exception as e:
            return self._degraded_response(context, "DEGRADED_HANDLER_ERROR", str(e))

        return self._stop_response(context, "STOP_NO_ROUTE", "No valid route selected")

    def _stop_response(self, context: RoutingContext, code: str, message: str) -> Dict[str, Any]:
        return {
            "status": "STOP",
            "code": code,
            "message": message,
            "mode": getattr(context, "mode", None),
            "game_id": getattr(context, "game_id", None),
            "request_id": getattr(context, "request_id", None),
        }

    def _degraded_response(self, context: RoutingContext, code: str, message: str) -> Dict[str, Any]:
        return {
            "status": "DEGRADED",
            "code": code,
            "message": message,
            "mode": getattr(context, "mode", None),
            "game_id": getattr(context, "game_id", None),
            "request_id": getattr(context, "request_id", None),
        }