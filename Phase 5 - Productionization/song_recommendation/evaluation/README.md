# Phase 5 – Song Recommendation Evaluation Layer

## Purpose

This layer defines **offline-only evaluation utilities** used to measure:

1. Recommendation quality (selection-level outcomes)
2. Model reasoning quality (alignment with human curator labels)

It is part of the Phase 5 learning loop:

```
feedback → aggregation → features → training → evaluation → artifacts → deployment
```

---

## Design Principles

- ✅ Offline only – must not affect runtime behavior  
- ✅ Deterministic – same input → same output  
- ✅ No mutation – inputs are treated as immutable  
- ✅ No semantic leakage – evaluation must not introduce new interpretations  
- ✅ Phase-isolated – operates strictly after aggregation / labeling  

---

## Key Modules

### 1. evaluate_selection_quality

**Purpose:**  
Measure recommendation effectiveness and enforce regression guards.

**Input:**
- Selection-level feature rows (output from `selection_features.py`)

**Metrics:**
- `accept_or_better_rate`
- `played_or_better_rate`
- `completed_rate`
- `mean_outcome_score`

**@k metrics:**
- `accept_at_k`
- `played_at_k`
- `completed_at_k`

**Regression Guards:**
- Compare current metrics vs baseline
- Enforce max drop / minimum delta constraints

**Use Cases:**
- Model evaluation after retraining
- Regression testing before promotion
- Experiment comparison

---

### 2. evaluate_reason_alignment

**Purpose:**  
Measure agreement between:

- `model_reason` (feedback_interpreter output)
- `curator_reason` (human ground truth)

**Input:**
- Curator review items (aligned to `curator_label.schema.json`)

**Metrics:**
- exact / partial / mismatch counts
- primary reason match rate
- reason code overlap
- confidence calibration slices

**Breakdowns:**
- by category
- by layer
- by plane
- by decision_type
- by cause_type
- by signal_type

**Use Cases:**
- Diagnosing model misclassification
- Improving taxonomy quality
- Evaluating training signal quality

---

## How These Modules Work Together

These evaluations operate on **different layers of the pipeline**:

| Layer | Evaluation |
|------|-----------|
| Selection output | `evaluate_selection_quality` |
| Reasoning / labeling | `evaluate_reason_alignment` |

They are **complementary, not interchangeable**:

- Selection metrics → "Did we recommend good songs?"
- Reason metrics → "Did we explain them correctly?"

---

## Example Usage

### Selection Quality

```python
from evaluation import evaluate_selection_quality

report = evaluate_selection_quality(feature_rows)
```

### Reason Alignment

```
from evaluation import evaluate_reason_alignment

report = evaluate_reason_alignment(curator_items)
```

---

## Output Contract

Both modules return:

```
{
    "report": {...}
}
```

This ensures:

- consistent orchestration
- easy export to artifacts / dashboards
- safe comparison across experiments

---

## What This Layer Does NOT Do

- ❌ No model training
- ❌ No inference
- ❌ No feature engineering
- ❌ No data mutation
- ❌ No runtime decision making

---

## Relationship to Other Components

| Component | Role |
|------|-----------|
| feedback_interpreter | Generates model_reason |
| reason_taxonomy | Defines meaning of reason_codes |
| curator_label.schema | Defines ground truth labels |
| dataset_builder | Produces training dataset |
| evaluation (this layer) | Measures quality + detects regressions |

---

## Future Extensions

- Confidence calibration curves
- Per-player / per-segment evaluation
- Temporal drift detection
- Experiment A/B comparison helpers

---

## Summary

This layer answers two critical questions:

1. Are we recommending the right songs?
2. Are we understanding why correctly?

Both are required for a stable Phase 5 learning loop.
