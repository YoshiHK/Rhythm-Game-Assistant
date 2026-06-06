### Promotion and Rollback (Phase 5 → Phase 6)

Phase 5 does NOT promote or rollback models directly.

---

### Phase 5 Responsibilities

- Produce versioned model artifacts
- Ensure dataset → model traceability
- Run full offline evaluation (selection + reason alignment)
- Validate models against all contracts
- Submit promotion candidates to Phase 6

---

### Phase 6 Responsibilities

- Decide whether promotion is allowed
- Control rollout, canarying, and rollback
- Enforce safety, cost, and compliance constraints

---

### Promotion Preconditions (NEW)

A model MUST satisfy ALL:

1. ✅ Dataset validity
   - Matches training_dataset.schema.json
   - Schema version recorded

2. ✅ Evaluation completeness
   - Selection metrics (accept / play / complete)
   - Reason alignment metrics

3. ✅ Regression guards
   - No violation of baseline thresholds

4. ✅ Validation pass

---

### Invariants

- Phase 5 cannot activate models
- Phase 5 cannot override active models
- All promotion decisions are owned by Phase 6
- All candidates must be reproducible from dataset_id

---

This separation ensures:
> learning never bypasses safety.