# Phase 2 Runtime – README

## Purpose

This directory contains the **deterministic execution spine**
for Phase 2 (Enhancement) of the Tip Generation System.

The runtime layer is responsible for:
- coordinating stage execution
- routing between Track A / B / C / D
- enforcing execution order and data flow

It does **not** implement domain logic.

---

## Runtime Responsibilities

The Phase 2 runtime:

- orchestrates Stage 2–7 execution
- invokes Track A (severity), Track B (selection),
  Track C (guidance), and Track D (narrative)
- enforces deterministic ordering and data passing
- validates data boundaries via schemas (indirectly)

---

## Files

### `phase2_core.py`
High-level Phase 2 execution coordinator.

Responsibilities:
- define the Phase 2 execution sequence
- invoke stage_router and track_router
- act as the single entrypoint for Phase 2 runtime

---

### `stage_router.py`
Routes execution between **stages**.

Responsibilities:
- Stage 2–4.1: Visual + SectionMetrics
- Stage 4.2: Tag → element candidates
- Stage 5.1: Severity + score + coverage
- Stage 5.2: Selection
- Stage 5.3: Guidance
- Stage 6: Narrative
- Stage 7: Summaries

---

### `track_router.py`
Routes execution between **tracks**.

Responsibilities:
- Track A: Severity + coverage
- Track B: Element selection
- Track C: Guidance filling
- Track D: Narrative rendering

Tracks are invoked only at their designated stages.

---

### `runtime_wrapper.py`
Integration wrapper for external callers.

Responsibilities:
- provide a stable invocation surface for Phase 3
- normalize inputs and outputs
- ensure Phase 2 runtime can be embedded safely

---

## Guarantees

- Execution order is deterministic
- No randomness or side effects are introduced
- No personalization or player context is used
- Phase 1 runtime behavior is not modified

---

## Relationship to Other Phases

- **Phase 1**
  - Phase 2 consumes Phase 1 outputs
  - Phase 1 runtime remains untouched

- **Phase 3**
  - Phase 3 Orchestrator calls Phase 2 runtime
  - No reverse dependency exists

- **Phase 4+**
  - Operates strictly on Phase 2 outputs

---

## Change Policy

✅ Allowed:
- Refactoring routing structure with identical behavior
- Documentation updates
- Additional wrappers for integration

❌ Not Allowed:
- Embedding domain logic
- Modifying Phase 1 behavior
- Introducing non-determinism

---

## Summary

The runtime layer is the **control plane** of Phase 2.

It coordinates enhancement logic without owning it,
ensuring Phase 2 remains modular, testable, and safe.