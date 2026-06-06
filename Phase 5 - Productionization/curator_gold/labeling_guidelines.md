### Labeling Guidelines (Phase 5)### Labeling Guidelines (Phase converts feedback signals into **taxonomy-aligned ground truth**.

---

### Label Structure

Each label MUST include:

- primary_reason (single dominant explanation)
- reason_codes (all applicable causes)
- taxonomy metadata:
  - category
  - layer
  - plane
  - decision_type
  - cause_type
  - signal_type

---

### Core Rules

#### 1. Use Taxonomy Only (NEW)
- All reason_codes MUST exist in reason_taxonomy_v1
- No free-form labels allowed

---

#### 2. Separate Observation vs Interpretation

Curators must distinguish:

| Type | Example |
|------|--------|
| Observation | player skipped recommendation |
| Interpretation | SELECTOR_FALLBACK_USED |

---

#### 3. Primary Reason Selection

- Choose ONE dominant cause
- Use reason priority logic (same as interpreter ordering where possible)
- Avoid ambiguity

---

#### 4. Multi-Reason Cases

- Multiple reason_codes allowed
- Must still define a single primary_reason

---

#### 5. Handling Ambiguity (NEW)

If unclear:

- Prefer broader taxonomy category
- Avoid overfitting to rare edge cases
- Add notes for future refinement

---

#### 6. Machine vs Human Comparison (NEW)

Curators SHOULD consider:

- model_reason (machine hypothesis)
- Compare against observed signals

But MUST NOT blindly copy machine output.

---

### Error Categories

Common cases:

- Execution failure → EXEC_FAILURE
- Missing output → PARTIAL_OUTPUT
- Personalization mismatch → CAPABILITY_MISCLASSIFIED
- Fallback overuse → FALLBACK_OVERUSE

---

### Consistency Requirements

- Similar cases MUST produce consistent labels
- All labels must be reproducible from input signals
- Labeling decisions must be explainable

---

Labeling exists to:
> create stable, learnable truth signals

