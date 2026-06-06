### Curator Queue (Phase 5)

The Curator Queue prepares aggregated feedback
for human review.

---

### Purpose

- Group related feedback events by provenance_id
- Present coherent review units to curators
- Preserve full traceability to raw feedback and runtime outputs

---

### Queue Units (UPDATED)

Each queue item MUST contain:

- One provenance_id
- All associated feedback events
- Aggregated selection-level context
- Linked runtime outputs (tips / recommendations)
- Time window definition (for grouping)

---

### Traceability (NEW)

Each queue item MUST allow:

- Reconstruction of original feedback events
- Navigation to:
  - runtime output
  - feedback signals
  - downstream curator labels

---

### Relationship to Interpretation Layer (NEW)

Queue items MAY include:

- derived_reason (from interpretation_bridge)

BUT MUST ensure:
- raw feedback remains unmodified
- derived_reason is clearly separated

---

### Non‑Goals

- ❌ The queue does NOT prioritize correctness
- ❌ The queue does NOT approve or reject outputs
- ❌ The queue does NOT enforce policy
- ❌ The queue does NOT assign labels

---

### Invariants

- Queue ordering does NOT imply severity
- Absence of feedback does NOT imply correctness
- Queue must remain audit-friendly and reproducible
- Curators may skip, defer, or escalate freely

---

The Curator Queue exists to:
> support human judgment, not replace it