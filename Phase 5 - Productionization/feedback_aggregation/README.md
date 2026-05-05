## Phase 5 — Feedback Aggregation

Feedback Aggregation is the first learning-facing layer in Phase 5
(Productionization).

Its role is to transform **runtime feedback signals**
into **structured review inputs** for Curator Gold & Labeling.

---

## Responsibilities

- Collect raw feedback from runtime execution.
- Preserve provenance and execution context.
- Aggregate feedback into curator-reviewable units.
- Maintain append-only, auditable datasets.

---

## What This Layer Does NOT Do

- It does NOT judge correctness.
- It does NOT score quality.
- It does NOT modify runtime behavior.
- It does NOT produce training labels.

---

## Relationship to Other Phases

- **Upstream**  
  Consumes runtime outputs from Phases 1–4.5,
  executed under Phase 6 governance.

- **Downstream**  
  Produces curated inputs for Phase 5 Curator Gold & Labeling.

Feedback Aggregation is downstream of runtime execution,
but upstream of human judgment.

---

## Design Invariants

- All feedback is immutable and append-only.
- All aggregation is reversible.
- All semantics remain human-interpreted.
- Phase 6 enforcement is never bypassed.

---

Feedback Aggregation exists to **prepare reality for learning**,
not to decide what reality means.