### Model Validation (Phase 5)

Model validation determines whether a trained model
is **eligible for promotion consideration**.

---

### Validation Checks

#### 1. Dataset Integrity (UPDATED)
- Must conform to training_dataset.schema.json
- Must include:
  - provenance_id linkage
  - gold_labels (taxonomy-aligned)
- Dataset must be complete and reproducible

---

#### 2. Selection Metrics Sanity
- accept_or_better_rate
- played_or_better_rate
- completed_rate
- No regression vs baseline beyond allowed thresholds

---

#### 3. Reason Alignment Metrics (NEW)
- exact / partial / mismatch rates
- primary_reason_match_rate
- reason_code_overlap

Purpose:
- ensure model explanations align with curator truth

---

#### 4. Explainability Constraints
- Model output must map to defined taxonomy
- No undefined reason_codes allowed

---

#### 5. Overfitting Indicators
- unstable performance across datasets
- abnormal confidence distribution

---

### Validation Outcomes

- ✅ Pass — eligible for Phase 6 submission
- ❌ Fail — model is archived, not deployed

---

### Invariants

- Validation does NOT rank models
- Validation does NOT activate models
- All failures are logged and auditable
- All checks are deterministic

---

Validation exists to:
> protect the system, not select winners