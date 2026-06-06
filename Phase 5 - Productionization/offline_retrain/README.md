### Phase 5 — Offline Retrain & Model Ops

This layer defines how the system **learns from curated data**.

---

### Purpose

- Train models using curator gold labels
- Evaluate models using:
  - selection quality
  - reason alignment
- Validate models for promotion eligibility
- Register model artifacts

---

### Learning Loop (UPDATED)

feedback → aggregation → features → training → evaluation → validation → registry → Phase 6

---

### What This Layer Does

- Construct versioned training datasets
- Execute offline training
- Run dual-axis evaluation:
  - outcome quality (selection)
  - reasoning quality (taxonomy alignment)
- Validate models
- Register artifacts

---

### What This Layer Does NOT Do

- Does NOT affect runtime behavior
- Does NOT select active models
- Does NOT deploy or rollback models
- Does NOT bypass Phase 6 governance

---

### Data Contract (UPDATED)

Primary schema:
- training_dataset.schema.json

Generated via:
- dataset_builder.py

---

### Relationship to Other Components

Consumes:
- Curator Gold (human truth)
- Feedback aggregation outputs
- Evaluation metrics

Produces:
- training datasets
- model artifacts
- evaluation reports

---

### Invariants

- All artifacts are versioned and immutable
- All datasets are schema-valid
- All models are traceable to dataset_id
- All evaluations are reproducible
- Phase 6 remains the sole runtime authority

---

Phase 5 exists to:
> earn the right to improve the model — not to deploy it