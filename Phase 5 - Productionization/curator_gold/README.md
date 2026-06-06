## Phase 5 — Curator Gold & Labeling

This layer defines how the system produces **human-validated ground truth**.

It is the **only layer allowed to assign meaning** to feedback.

---

## 🔷 Pipeline Role

```
feedback → aggregation → curator_queue → curator_label → dataset → training
```

Curator outputs directly define the learning signal.

---

## 🔷 Purpose

- Transform aggregated signals into structured, human-labeled truth
- Align all labels with reason_taxonomy_v1
- Provide reliable supervision for model training

---

## 🔷 Key Principles

- ✅ Human judgment defines truth
- ✅ Labels must be deterministic and reproducible
- ✅ Labels must align with taxonomy
- ✅ Labels must remain independent of runtime control

---

## 🔷 Data Contract (NEW)

Primary schema:
- `curator_label.schema.json`

Generated via:
- `build_curator_label()`

Key objects:
- `model_reason` (machine hypothesis)
- `curator_reason` (human truth with taxonomy)
- `judgement` (comparison and severity)

---

## 🔷 What This Layer Does

- Accept aggregated feedback units
- Apply human judgment and expertise
- Assign taxonomy-aligned reason codes
- Compare model predictions with human labels
- Produce deterministic, auditable curation records

---

## 🔷 What This Layer Does NOT Do

- ❌ Does NOT auto-label feedback
- ❌ Does NOT modify runtime behavior
- ❌ Does NOT filter or delete data
- ❌ Does NOT perform semantic reasoning beyond taxonomy

---

## 🔷 Relationship to Other Layers

| Layer | Role |
|-------|------|
| Feedback Aggregation | upstream (raw signals) |
| Model Interpreter | parallel (machine hypothesis) |
| Dataset Builder | downstream (features + labels) |
| Training | downstream (learning signal) |

---

## 🔷 Invariants

- Curator labels are authoritative
- All labels are auditable and traceable
- No feedback is auto-labeled without human review
- Absence of label ≠ correctness
- Labels must align with taxonomy enums

---

## 🔷 Design Intent

Curator Gold exists to:

✅ Define truth for learning
✅ Validate model hypotheses
✅ Provide quality supervision

NOT:

❌ Automate judgment
❌ Bypass human oversight
❌ Enforce runtime decisions

---

**Curator Gold: Where meaning enters the learning loop.**
