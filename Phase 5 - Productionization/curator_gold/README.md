### Phase 5 — Curator Gold & Labeling

This layer defines how the system produces **human-validated ground truth**.

It is the **only layer allowed to assign meaning** to feedback.

---

### Pipeline Role

```
feedback → aggregation → curator_queue → curator_label → dataset → training
```

Curator outputs directly define the learning signal.

---

### Purpose

- Transform aggregated signals into structured, human-labeled truth
- Align all labels with reason_taxonomy_v1
- Provide reliable supervision for model training

---

### Key Principles

- ✅ Human judgment defines truth
- ✅ Labels must be deterministic and reproducible
- ✅ Labels must align with taxonomy
- ✅ Labels must remain independent of runtime control

---

### Data Contract (NEW)

### Data Contract (NEW)

Primary schema:
- curator_label.schema.json 

Generated via:
- build_curator_label()

Key objects:
- model_reason (machine hypothesis)
- curator_reason (human truth)
- judgement (comparison)


---

### Relationship to Other Layers

Upstream:
- Feedback Aggregation (raw, uninterpreted signals)

Parallel:
- model_reason (machine hypothesis)

Downstream:
- dataset_builder
- training
- evaluation
- validation

---

### Invariants

- Curator labels are authoritative
- All labels are auditable and traceable
- No feedback is auto-labeled
- Absence of label ≠ correctness

---

Curator Gold exists to:
> define truth for learning, not to automate judgment