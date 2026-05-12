### Phase 6 — Router Layer

## Role

The Router Layer is the **coordination spine** of Phase 6.

It is responsible for:
- Sequencing guard evaluation
- Applying routing policy decisions
- Forwarding an immutable routing context
- Invoking lifecycle, observability, and integration routers

This layer defines **execution flow**, not execution meaning.

## What the Router Layer DOES

- Coordinates the order of Phase 6 components
- Passes a normalized, immutable routing context
- Enforces platform-level execution boundaries
- Acts as the single runtime entry point for Phase 6

## What the Router Layer MUST NOT Do

The Router Layer MUST NOT:
- Contain guard logic
- Contain lifecycle logic
- Interpret execution payloads
- Interpret gameplay or recommendation semantics
- Perform chart analysis or personalization

All decisions are delegated to:
- Guards
- Routing policies
- Domain routers (song / game)
- Observability and lifecycle handlers

## Design Principle

Phase 6 routing is **mechanical and declarative**.

Semantic interpretation belongs to downstream phases.
The router only orchestrates.
