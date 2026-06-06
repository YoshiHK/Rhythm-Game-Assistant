## Phase 5 — Offline Retrain & Model Ops

This layer defines how the system **learns from curated data**.

---

## 🔷 Purpose

- Train models using curator gold labels
- Evaluate models using:
  - selection quality
  - reason alignment
- Validate models for promotion eligibility
- Register model artifacts

---

## 🔷 Learning Loop (UPDATED)

```
feedback → aggregation → curation → features → training → evaluation → validation → registry → Phase 6
```

---

## 🔷 What This Layer Does

- Construct versioned training datasets
- Execute offline training
- Run dual-axis evaluation:
  - outcome quality (selection)
  - reasoning quality (taxonomy alignment)
- Validate models
- Register artifacts

---

## 🔷 What This Layer Does NOT Do

- ❌ Does NOT affect runtime behavior
- ❌ Does NOT select active models
- ❌ Does NOT deploy or rollback models
- ❌ Does NOT bypass Phase 6 governance

---

## 🔷 Data Contract (UPDATED)

Primary schema:
- `training_dataset.schema.json`

Generated via:
- `dataset_builder.py`

Key objects:
- `samples` (features + labels)
- `gold_labels` (curator truth)
- `model_reason` (baseline hypothesis)
- `curator_metadata` (comparison data)

---

## 🔷 Dataset Structure

Each training sample includes:

| Component | Source | Role |
|-----------|--------|------|
| `provenance_id` | Phase 4 runtime | traceability |
| `features` | deterministic computation | model inputs |
| `gold_labels` | human curation | learning signal |
| `model_reason` | baseline predictor | evaluation baseline |
| `curator_metadata` | comparison analysis | quality metrics |

---

## 🔷 Relationship to Other Components

| Component | Role |
|-----------|------|
| Curator Gold | upstream (human truth) |
| Feedback Aggregation | upstream (signals) |
| Model Training | outputs (trained model) |
| Model Registry | outputs (artifacts) |
| Phase 6 | downstream (deployment) |

---

## 🔷 Invariants

- All artifacts are versioned and immutable
- All datasets are schema-valid
- All models are traceable to dataset_id
- All evaluations are reproducible
- Phase 6 remains the sole runtime authority

---

## 🔷 Design Intent

Offline Retrain exists to:

✅ Earn the right to improve the model
✅ Ensure safe, measurable learning
✅ Validate improvements before deployment

NOT:

❌ Deploy models directly
❌ Bypass Phase 6 governance
❌ Auto-select active models

---

**Offline Retrain: Earning the right to improve — not deploying it.**
