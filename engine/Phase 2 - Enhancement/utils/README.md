# Phase 2 Utils Layer – README

## Purpose

This directory contains **shared utility helpers** for Phase 2 (Enhancement).

 and debug helpersThe Utils Layer exists to:

It must never influence pipeline decisions or outcomes.

---

## Responsibilities

The Phase 2 Utils Layer is responsible for:

- light data normalization (non-semantic)
- routing and debug snapshots
- defensive guard checks (report-only)

All utilities are **optional**, **deterministic**, and **side-effect free**.

---

## What This Layer Does NOT Do

This layer does **not**:

- implement business logic
- influence severity, selection, or narrative
- mutate runtime payloads
- enforce schemas or block execution
- depend on Phase 1 internals

---

## Files

### `taxonomy_helpers.py`
Helpers for working with taxonomy and category labels.

Responsibilities:
- normalize taxonomy strings
- ensure stable comparisons
- avoid semantic reinterpretation

---

### `routing_debug.py`
Routing and execution debug helpers.

Responsibilities:
- snapshot current routing state
- expose stage/track markers for diagnostics
- assist QA and debugging

---

### `phase2_guards.py`
Defensive guard helpers.

Responsibilities:
- check for required fields
- report missing or malformed inputs
- never throw or stop execution

---

## Determinism & Safety Guarantees

The Utils Layer guarantees that:

- removing utils does not change outputs
- identical inputs produce identical helper outputs
- no randomness or external state is used

---

## Relationship to Other Phases

### Phase 2
- Utils may be used by any Phase 2 layer
- No Phase 2 layer may depend on utils for correctness

### Phase 3+
- Phase 3 may reuse concepts, not implementations
- Phase 4+ must not rely on Phase 2 utils

---

## Change Policy

✅ Allowed:
- New helper functions (additive)
- Improved diagnostics
- Additional guard checks (non-blocking)

❌ Not Allowed:
- Embedding logic
- Enforcing validation
- Introducing side effects

---

## Summary

The Phase 2 Utils Layer provides **supporting infrastructure**
that makes Phase 2 safer and easier to evolve —
without ever becoming part of the decision surface.
- reduce duplication
- improve readability
