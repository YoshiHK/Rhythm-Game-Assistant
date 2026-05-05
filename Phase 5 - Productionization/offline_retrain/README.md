## Phase 5 — Offline Retrain & Model Ops

This layer defines how the system **learns from curated data**
during Phase 5 (Productionization).

---

## Purpose

- Train new models using curator gold labels
- Evaluate models using offline metrics
- Prepare promotion candidates for Phase 6

---

## What This Layer Does

- Construct versioned training datasets
- Run offline training jobs
- Validate trained models
- Register model artifacts

---

## What This Layer Does NOT Do

- It does NOT affect runtime behavior
- It does NOT select active models
- It does NOT deploy or rollback models
- It does NOT bypass Phase 6 governance

---

## Relationship to Other Phases

- **Upstream**  
  Consumes:
  - Curator Gold & Labeling
  - Observability & Experimentation metrics

- **Downstream**  
  Submits validated candidates to Phase 6 lifecycle management

Offline learning informs the future; it never controls the present.

---

## Invariants

- All artifacts are versioned and immutable
- All decisions are auditable
- All promotions are externally governed
- Phase 6 remains the sole runtime authority

---

Phase 5 Offline Retrain exists to **earn the right to change the model**,
not to exercise it.
``