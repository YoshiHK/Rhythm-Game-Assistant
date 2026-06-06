## Phase 5 — Feedback Aggregation

Feedback Aggregation is the **first learning-facing layer** in Phase 5.

It transforms **raw runtime feedback events**
into **structured, curator-reviewable units**.

---

## 🔷 Pipeline Role

```
feedback_event → interpretation_bridge → aggregation → curator_queue → curator_label
```

This layer prepares data for human interpretation,
but never performs interpretation itself.

---

## 🔷 Purpose

- Collect raw feedback from runtime execution
- Preserve full provenance and context
- Maintain append-only, auditable records
- Aggregate feedback into coherent review units
- Ensure compatibility with schemas

---

## 🔷 What This Layer Does

- Receive feedback_events from event layer
- Aggregate signals by provenance_id
- Preserve original payload without modification
- Structure data for curator review
- Maintain append-only transaction log

---

## 🔷 What This Layer Does NOT Do

- ❌ Does NOT judge correctness
- ❌ Does NOT assign reason codes
- ❌ Does NOT score quality
- ❌ Does NOT modify runtime behavior
- ❌ Does NOT produce training labels
- ❌ Does NOT perform semantic interpretation

---

## 🔷 Data Contract (NEW)

Inputs MUST conform to:
- `feedback_events.schema.json`

Generated via:
- `build_feedback_event()`

Output guarantees:
- `event_id`
- `provenance_id`
- Raw `payload` (uninterpreted)
- `context` (runtime linkage)
- `system_context` (non-semantic signals)

---

## 🔷 Relationship to Other Layers

| Layer | Role |
|-------|------|
| Events Layer | upstream (raw input) |
| Curator Queue | downstream (review units) |
| Curator Gold | downstream (human truth) |
| Dataset Builder | downstream (training data) |

---

## 🔷 Design Invariants

- All feedback is immutable and append-only
- Aggregation is reversible to raw events
- No semantic interpretation is introduced
- All meaning is deferred to humans or interpreter layer
- Full provenance chain is maintained

---

## 🔷 Design Intent

Feedback Aggregation exists to:

✅ Collect raw behavior signals
✅ Structure data for review
✅ Preserve complete provenance

NOT:

❌ Judge or score behavior
❌ Interpret meaning
❌ Filter or preprocess data

---

**Feedback Aggregation: Preparing reality for learning, never interpreting it.**
