## Phase 6 — Router Layer

The Router Layer is the **coordination spine** of Phase 6.

It:
- sequences guard evaluation,
- applies routing policy,
- invokes lifecycle routing,
- and forwards execution context.

The Router Layer MUST NOT:
- contain guard logic,
- contain lifecycle logic,
- interpret execution payloads,
- or make semantic decisions.

All decisions are delegated to:
- guards,
- policies,
- routers,
- and observers.

The router only orchestrates.
``