## Phase 5 — Practice Integration

Practice Integration defines how generated tips and guidance
are applied during player practice and replay.

---

## Purpose

- Support deliberate practice
- Reinforce learning at the right moment
- Improve player comprehension of tips

---

## What This Layer Does

- Translate tips into practice‑time hints
- Surface contextual reminders
- Collect non‑judgmental practice telemetry

---

## What This Layer Does NOT Do

- It does NOT analyze charts
- It does NOT generate tips
- It does NOT alter recommendations
- It does NOT enforce behavior

---

## Relationship to Other Phases

- **Upstream**  
  Consumes tips and elements produced by Phases 1–4.5,
  executed under Phase 6 governance.

- **Downstream**  
  Emits practice telemetry for Phase 5 Observability,
  Feedback Aggregation, and Curator review.

Practice Integration is downstream of intelligence
and upstream of learning.

---

## Invariants

- All assistance is optional
- All behavior is reversible
- All semantics remain unchanged
- Phase 6 boundaries are never crossed

---

Practice Integration exists to **help players practice better**,
not to decide how they should play.
