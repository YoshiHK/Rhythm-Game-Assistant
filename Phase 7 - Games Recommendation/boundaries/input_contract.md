# Phase 7 — Input Contract

This document defines the **complete and exclusive set of inputs**
that Phase 7 – Games Recommendations is allowed to consume.

Any dependency or signal not listed here is **explicitly forbidden**.

---

## 1. Allowed Inputs (Read‑Only)

Phase 7 MAY consume the following inputs, strictly in a **read‑only** manner.

### 1.1 Player Signals

Derived, stabilized player data only:

- Player profile and preferences  
  (produced by Phase 4 / Phase 4.5)
- Player completion‑rate submissions
- Aggregated player performance history
- Player song‑level recommendation history
- Player game‑level recommendation history

Phase 7 MUST NOT infer player capability from raw chart data or tips internals.

---

### 1.2 Game & Catalog Signals

Authoritative, declarative game metadata only:

- Game registry and enablement status
- Presentation catalog metadata
  (display names, icons, descriptions)
- Locale resolution outputs
  (aliases, fallback chains, normalized locale)

Catalog data is **presentation‑only** and must not affect upstream semantics.

---

### 1.3 Difficulty & Capability Signals

Stabilized, batch‑level signals only:

- Batch difficulty profiles emitted by Phase 3 ingestion
- Aggregated game capability representations

Phase 7 MUST NOT re‑analyze raw charts, sections, or pattern tags.

---

### 1.4 Platform Context

Invocation and operational context supplied by Phase 6:

- Invocation source and routing context
- Feature flag state
- Observability and telemetry hooks (read‑only)

Phase 7 MUST NOT inspect or depend on Phase 6 enforcement internals.

---

## 2. Explicit Constraints

Phase 7:

- MUST NOT introduce new upstream dependencies
- MUST treat all upstream artifacts as authoritative
- MUST treat all consumed data as immutable
- MUST remain non‑blocking to upstream execution

---

## 3. Architectural Rationale

Phase 7 operates at the **meta‑game discovery layer**.

It reasons over existing, stabilized truth and produces
**advisory discovery outputs**, without redefining or re‑deriving truth.  