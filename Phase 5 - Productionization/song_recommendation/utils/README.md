## Phase 5 — Song Recommendation Utils Layer

### Purpose

The Utils Layer defines **offline orchestration helpers**
for the Song Recommendation learning pipeline.

It coordinates the full Phase 5 learning loop:

```
feedback → aggregation → features → training → evaluation → artifacts
```

---

### Role in Pipeline (UPDATED)

This layer provides:

- pipeline entrypoints
- dataflow coordination
- artifact orchestration

It does NOT implement:

- aggregation logic
- feature logic
- training logic
- evaluation logic

---

### What This Layer Does

- Execute the full offline learning pipeline
- Connect pipeline stages in correct order
- Handle I/O for offline runs (loading/writing)
- Manage baseline comparison flow
- Produce deployment-ready outputs

---

### What This Layer Does NOT Do

- ❌ Does NOT run in runtime (Phase 6)
- ❌ Does NOT affect recommendation decisions
- ❌ Does NOT introduce semantics
- ❌ Does NOT perform model learning itself

---

### Data Contracts (NEW)

Pipeline stages must propagate:

- feature_schema_version
- training_schema_version
- evaluation outputs

This layer MUST preserve:

- version traceability
- deterministic execution
- strict input/output contracts

---

### Failure Semantics (NEW)

Pipeline result statuses:

| Status | Meaning |
|------|--------|
| OK | Safe to deploy |
| GUARD_FAIL | Regression guard failed (do NOT deploy) |
| NO_DATA | No usable data |

Strict mode:

- `strict=True` → raise on failure
- `strict=False` → return status only

---

### Determinism Guarantees

- Same inputs → same outputs
- No randomness or sampling
- No runtime dependencies

---

### Relationship to Other Layers

| Layer | Role |
|------|------|
| aggregation | behavior aggregation |
| features | signal construction |
| training | parameter calibration |
| evaluation | quality checks |
| artifacts | deployment output |

Utils connects them — it does not replace them.

---

### Design Intent

This layer exists to:

✅ execute the learning pipeline safely  
✅ ensure reproducibility  
✅ enforce evaluation before deployment  

---

**Utils orchestrates the pipeline. It never defines logic.**