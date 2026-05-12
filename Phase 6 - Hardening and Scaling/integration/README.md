# Phase 6 — Integration Layer

The Integration Layer defines the **external boundary** of the platform
in Phase 6 (Platform Hardening and Scale).

It governs:
- partner access,
- SDK boundaries,
- API version compatibility,
- and external execution intent.

This layer MUST NOT:
- interpret gameplay data,
- modify tips or recommendations,
- schedule execution,
- or bypass Phase 6 guards.

It exists to answer:
> “Is this external request allowed to enter the system, and under what constraints?”

---

## Design Principles

### 1. Boundary, Not Business Logic
The Integration Layer is a **gateway**, not a product feature.

It does not understand:
- charts,
- difficulty,
- tips,
- personalization,
- or recommendation meaning.

All semantic decisions remain in Phases 1–5.

---

### 2. Trigger‑Aware Execution

All external requests are normalized by **Trigger Router** into
a canonical execution intent:

- **scheduled**  
  Platform‑initiated automation (not typical for partners)

- **manual**  
  Operator‑initiated execution (debug, audit)

- **external**  
  Partner, SDK, CI, or API‑initiated execution

Integration logic is **trigger‑aware**, but never trigger‑driven.

---

## Components

### api_version_router.py
**Routing Gate**

- Enforces API version compatibility.
- Blocks deprecated or incompatible versions.
- Does not rewrite requests.

### partner_gateway.py
**Boundary Gate**

- Validates partner identity and access scope.
- Normalizes external requests into routing context.
- Does not execute ingestion or analysis.

### sdk_boundary.py
**SDK Contract Boundary**

- Defines what SDKs may and may not do.
- Prevents SDKs from bypassing Phase 6 routing and guards.
- Acts as a hard boundary for partner code.

---

## Execution Model

1. External request enters via Integration Layer.
2. API version compatibility is evaluated.
3. Partner access and SDK boundaries are enforced.
4. Request is normalized into Phase 6 routing context.
5. Downstream routing, guards, and observability apply.

At no point does the Integration Layer:
- generate tips,
- select recommendations,
- or bypass must‑scan, security, or cost constraints.

---

## Invariants

- All external execution is auditable.
- No partner can bypass Phase 6 guards.
- Manual execution is explicit and traceable.
- Phase 1–5 semantics remain immutable.

---

The Integration Layer protects the platform boundary,
not gameplay intelligence.
