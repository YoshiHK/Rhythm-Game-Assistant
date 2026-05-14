# Phase 6 — Song Recommendation Feedback Layer

## Purpose

The Song Recommendation Feedback Layer captures **user reactions**
to song recommendations and emits **structured, forward-only events**
for offline learning.

This layer is intentionally minimal and non-semantic.

---

## What This Layer DOES

- Capture explicit user actions on song recommendations:
  - accept
  - ignore
  - played
  - completed
- Attach exposure context:
  - recommendation_set_id
  - rank
  - tier and target metric (if available)
  - catalog fingerprint
- Emit immutable feedback events to downstream sinks (Phase 5)

---

## What This Layer MUST NOT Do

This layer MUST NOT:

- Interpret feedback meaning
- Aggregate or score feedback
- Influence song selection or ranking
- Modify runtime behavior
- Import Phase 5 learning logic
- Bypass Phase 6 routing or guards

Runtime song recommendations must remain:
- deterministic
- explainable
- reproducible

---

## Learning Loop Contract

The Song Recommendation learning loop is **explicitly split**:

### Phase 6 (This Layer)
- Emits feedback events only
- Performs no learning
- Does not read feedback outcomes

### Phase 5 (Offline Learning)
- Aggregates feedback events
- Learns selection heuristics (e.g. window widening effectiveness)
- Produces updated static parameters

### Deployment
- Introduces learned changes via deployment only
- No runtime adaptation is permitted

---

## Design Intent

This layer exists to make Song Recommendations:

✅ safe to learn from  
✅ safe to audit  
✅ safe to evolve  

without making them unsafe to run.

---

**Learning is allowed.  Runtime adaptation is not.**