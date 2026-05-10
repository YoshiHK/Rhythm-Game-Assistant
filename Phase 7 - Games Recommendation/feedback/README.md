# Phase 7 — Feedback Layer

This directory defines **how Phase 7 captures and forwards feedback**
to downstream learning systems (Phase 5).

---

## Purpose

The Feedback Layer answers one question only:

> **How do user interactions with game recommendations become learning signals,
> without affecting runtime behavior?**

---

## Design Principles

- **Observational only**
  - Feedback capture must never affect recommendation results.
  - No ranking, routing, or eligibility logic is allowed here.

- **Forward-only**
  - Feedback flows from Phase 7 → Phase 5.
  - No feedback is consumed by Phase 7 at runtime.

- **Non-blocking**
  - Feedback failures must not break or delay user-facing flows.

- **Schema-first**
  - Feedback events must be structured, auditable, and versionless.

---

## What Is Considered Feedback

Typical Phase 7 feedback signals include:
- Recommendation accepted
- Recommendation dismissed
- User indicates “already playing”
- Recommendation ignored (implicit / optional)

---

## Relationship to Other Phases

- **Phase 7**
  - Emits feedback events only.
- **Phase 5**
  - Aggregates, labels, and learns from feedback.
- **Phase 6**
  - Owns transport reliability, persistence, and observability.

This layer defines *what* is emitted, not *how* it is transported.
