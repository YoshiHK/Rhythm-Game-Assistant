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

from typing import Iterable, Any


class Phase6Router:
    """
    Phase 6 routing coordinator.
    """

    def __init__(
        self,
        *,
        guards: Iterable[Any],
        routing_policy: Any,
        lifecycle_routers: Iterable[Any],
        observability: Any,
        integration: Any,
    ):
        self.guards = list(guards)
        self.routing_policy = routing_policy
        self.lifecycle_routers = list(lifecycle_routers)
        self.observability = observability
        self.integration = integration

    def route(self, context: Any) -> Any:
        """
        Route execution through Phase 6.

        Returns:
        - forwarded execution payload or handle
        """

        # 1. Evaluate guards (block or allow)
        for guard in self.guards:
            if not guard.allow(context):
                raise RuntimeError(f"Execution blocked by {guard.__class__.__name__}")

        # 2. Routing policy (final allow/deny)
        if not self.routing_policy.allow(context):
            raise RuntimeError("Execution blocked by routing policy")

        # 3. Lifecycle routing gates
        for router in self.lifecycle_routers:
            if not router.allow(context):
                raise RuntimeError(f"Execution blocked by {router.__class__.__name__}")

        # 4. Observability (side-effect free)
        if self.observability:
            self.observability.observe(context)

        # 5. Integration boundary routing
        return self.integration.forward(context)