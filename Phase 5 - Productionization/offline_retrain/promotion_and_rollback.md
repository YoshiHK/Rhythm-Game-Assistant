## Promotion and Rollback (Phase 5 → Phase 6)

Phase 5 does NOT promote or rollback models directly.

### Phase 5 Responsibilities

- Produce trained model artifacts
- Validate models offline
- Submit promotion candidates to Phase 6

### Phase 6 Responsibilities

- Decide whether promotion is allowed
- Control rollout, canarying, and rollback
- Enforce safety, cost, and compliance constraints

### Invariants

- Phase 5 cannot activate models
- Phase 5 cannot override active models
- All promotion decisions are owned by Phase 6

This separation ensures **learning never bypasses safety**.