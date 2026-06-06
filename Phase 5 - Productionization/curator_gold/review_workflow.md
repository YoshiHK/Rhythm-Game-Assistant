### Review Workflow (Phase 5)

Defines how curator labeling is executed and validated.

---

### Workflow Steps (UPDATED)

1. Receive curator queue item
2. Inspect aggregated feedback
3. Review model_reason (optional reference)
4. Apply taxonomy-aligned labeling
5. Validate consistency
6. Submit labeled item

---

### Required Inputs

Each review MUST have access to:

- aggregated feedback signals
- runtime context
- provenance_id
- (optional) model_reason

---

### Output Requirements

Each review MUST produce:

- curator_reason (taxonomy-aligned)
- judgement comparison:
  - is_correct
  - agreement_type
  - severity

---

### Review Modes (NEW)

#### Standard Review
- Label from scratch

#### Assisted Review
- Compare against model_reason
- Correct or confirm model output

---

### Consistency Enforcement (NEW)

- Reviewers must follow labeling_guidelines
- Conflicting labels should be escalated
- High-disagreement cases should be flagged

---

### Escalation (NEW)

Escalate when:

- taxonomy is insufficient
- case is ambiguous
- repeated mismatch detected

---

### Traceability

Each review must be traceable to:

- original feedback events
- aggregation output
- eventual training dataset

---

### Downstream Impact (NEW)

Curator output directly affects:

- dataset_builder
- model training
- evaluation metrics

---

Review workflow exists to:
> ensure truth is applied consistently and safely