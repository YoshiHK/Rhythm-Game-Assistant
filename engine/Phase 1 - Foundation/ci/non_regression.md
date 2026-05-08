# Phase 1 CI – Non‑Regression Policy

## Purpose

This document defines the **non‑regression guarantees**
for Phase 1 (Foundation).

Phase 1 is finalized; therefore, its behavior must never regress.

---

## What Constitutes a Regression

A regression includes (but is not limited to):

- Changed element selection results for the same input
- Changed severity labels or scores for the same chart
- Different guidance or narrative text without spec changes
- Modified summary block structure or dominance logic
- Changed behavior without explicit Phase versioning

---

## Scope of Protection

Non‑regression applies to:

- Core engine logic
- Orchestration order
- Default adapter wiring
- Output shapes and semantics

---

## Allowed Changes (Strictly Limited)

✅ Allowed:
- Documentation clarification
- File renaming for clarity (non‑breaking)
- Packaging metadata (e.g. `__init__.py`)
- Phase labeling and routing skeleton updates

❌ Not Allowed:
- Logic refactors
- Rule tuning
- Threshold changes
- Silent behavior changes

---

## Relationship to Later Phases

- Phase 2+ may **override or extend behavior**
- Phase 1 behavior itself must remain unchanged
- Regression fixes must be implemented in:
  - Phase 1.1 (parallel foundation), or
  - Phase 2+ enhancement layers

---

## CI Expectations (Conceptual)

Any CI validating Phase 1 should:

- Compare outputs against golden references
- Flag differences in selection, guidance, or summaries
- Require explicit phase/version justification for any divergence

---

## Summary

Phase 1 is a **historical baseline**.

Regression is not evolution — it is a violation.