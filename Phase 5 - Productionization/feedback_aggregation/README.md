
### Phase 5 — Feedback Aggregation

Feedback Aggregation is the **first learning-facing layer** in Phase 5.

It transforms **raw runtime feedback events**
into **structured, curator-reviewable units**.

---

### Pipeline Role 

```
feedback_event → interpretation_bridge → aggregation → curator_queue → curator_label
```

This layer prepares data for human interpretation,
but never performs interpretation itself.

---

### Responsibilities

- Collect raw feedback from runtime execution
- Preserve full provenance and context
- Maintain append-only, auditable records
- Aggregate feedback into coherent review units
- Ensure compatibility with:
  - feedback_events.schema.json
  - curator_label.schema.json

---

### What This Layer Does NOT Do

- ❌ Does NOT judge correctness
- ❌ Does NOT assign reason codes
- ❌ Does NOT score quality
- ❌ Does NOT modify runtime behavior
- ❌ Does NOT produce training labels

---

### Data Contract (NEW)

Inputs MUST conform to:
- feedback_events.schema.json 

Generated via:
- build_feedback_event()

Output guarantees:
- event_id
- provenance_id
- raw payload (uninterpreted)

---

### Relationship to Other Phases

Upstream:
- Runtime outputs (Phase 1–4.5, governed by Phase 6)

Downstream:
- curator_queue
- curator_label

---

### Design Invariants

- All feedback is immutable and append-only
- Aggregation is reversible to raw events
- No semantic interpretation is introduced
- All meaning is deferred to humans or interpreter layer

---

Feedback Aggregation exists to:
> prepare reality for learning, never to interpret it