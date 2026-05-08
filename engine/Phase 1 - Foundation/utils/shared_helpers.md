# Phase 1 Shared Helpers – Notes

## Purpose

This document explains the **intent and boundaries**
of shared helpers used in Phase 1 Foundation.

It exists to prevent accidental misuse of utility code
as the system evolves across phases.

---

## What Helpers Are (and Are Not)

### Helpers ARE:
- Small convenience functions
- Pure data manipulation utilities
- Reusable across multiple Phase 1 layers
- Deterministic and side-effect free

### Helpers are NOT:
- Decision logic
- Scoring logic
- Selection logic
- Severity logic
- Orchestration logic

If a helper influences *what* the system decides,
it does not belong here.

---

## Typical Use Cases

Helpers may be used for:
- safely reading optional fields
- normalizing container types
- clamping numeric values
- removing duplicates while preserving order
- basic string sanity checks

Helpers must NOT:
- interpret gameplay semantics
- encode domain knowledge
- modify element meaning

---

## Relationship to Other Phases

- **Phase 2+** may re‑implement similar helpers
- **Phase 3** may provide a different utils layer
- **Phase 4+** must not import Phase 1 utils directly

Phase 1 helpers exist only to support
the Foundation runtime.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Minor refactors with identical behavior
- Type annotations or comments

❌ Not Allowed:
- Adding new helper categories
- Introducing domain-specific logic
- Coupling helpers to specific layers
- Adding dependencies

Any meaningful extension must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

Shared helpers are **infrastructure glue**.

They exist to make Phase 1:
- readable
- maintainable
- safe to evolve around

They must never become a decision surface.