# Phase 7 — Integration Layer

This directory defines **how Phase 7 is invoked and exposed** to
external systems, APIs, and SDKs.

It is a **boundary and contract layer**, not a computation layer.

---

## Purpose

The Integration Layer answers one question only:

> **How is Phase 7 safely invoked without violating phase boundaries?**

---

## Design Principles

- **Phase 6 is the only runtime gateway**
  - All Phase 7 runtime invocations MUST pass through Phase 6.
  - Direct calls from UI, SDKs, or partners are forbidden.

- **No business logic**
  - No ranking, routing, eligibility, or learning logic lives here.

- **Non-blocking by design**
  - Failure or disablement of Phase 7 must never affect upstream flows.

- **Contract-first**
  - All inputs and outputs must conform to Phase 7 contracts.
  - Integration never reshapes semantics.

---

## What Lives Here

✅ Allowed:
- Invocation contracts
- API / SDK expectations
- Phase 6 ↔ Phase 7 wiring documentation

🚫 Not allowed:
- Feature flags
- Runtime guards
- Experiment logic
- Version negotiation

---

## Relationship to Other Phases

- **Phase 6** owns:
  - authentication
  - authorization
  - rate limiting
  - abuse protection
  - lifecycle control

- **Phase 7** owns:
  - discovery logic
  - ranking
  - explanation

Integration simply connects the two.