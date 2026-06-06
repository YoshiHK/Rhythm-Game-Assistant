## Phase 5 — Song Recommendation Artifacts Layer

### Purpose

The Artifacts Layer defines how Phase 5 produces **deployment-safe outputs**.

It is the final stage of the offline learning pipeline:

```
aggregation → features → training → evaluation → artifacts → deployment
```

---

### Role in Pipeline (UPDATED)

This layer:

- materializes static selector parameters
- records training and evaluation reports
- produces baseline snapshots for regression comparison

It is the **only layer that generates deployable outputs**.

---

### What This Layer Does

- Write selector parameter artifacts
- Write training reports (audit + QA)
- Write evaluation reports (metrics + regression guards)
- Write / load baseline metrics snapshots

---

### What This Layer Does NOT Do

- ❌ Does NOT run in runtime (Phase 6)
- ❌ Does NOT perform learning or calibration
- ❌ Does NOT interpret model outputs
- ❌ Does NOT trigger deployment

---

### Artifact Format (NEW)

All artifacts MUST follow a standard envelope:

```json
{
  "artifact_type": "...",
  "artifact_schema_version": "...",
  "payload": {...}
}
```

This ensures:

- consistency across artifact types
- forward compatibility
- auditability

---

## Artifact Types

### 1. selector_params

Deployment payload:

- widen_steps
- top_producers
- rank_decay_alpha

Constraints:

- must pass validation
- must be bounded and deterministic

---

### 2. training_report

Includes:

- aggregation summary
- feature summary
- training output
- schema versions

Used for:

- QA
- debugging
- audit

---

### 3. evaluation_report

Includes:

- metrics
- deltas vs baseline
- guard_pass
- guard_fail_reasons

Used for:

- regression protection
- promotion gating

---

### 4. baseline_metrics

Snapshot of metrics for:

- future comparison
- regression detection

---

## Deployment Boundary (CRITICAL)

Artifacts are:

✅ build-time outputs
✅ consumed by deployment pipelines

Artifacts are NOT:

❌ runtime inputs
❌ dynamically loaded
❌ self-updating

---

## Guard Constraints

Artifacts MUST:

- only be updated when evaluation guard passes

Artifacts MUST NOT:

- be generated from regressed models
- overwrite valid baseline with failing runs

---

## Determinism & Auditability

- Same inputs → same artifacts
- All outputs are stable JSON
- All artifacts are versioned
- All data is traceable back to inputs

---

## Relationship to Other Layers

| Layer | Relationship |
|------|------|
| training | produces |
| evaluation | validates results |
| utils | orchestrates writing |
| deployment | consumes artiting |

---

## Design Intent

This layer exists to:

✅ safely move learning outputs into deployment
✅ enforce reproducibility
✅ prevent unsafe model promotion

---

**Artifacts define what can be deployed — not what should be learned.**

