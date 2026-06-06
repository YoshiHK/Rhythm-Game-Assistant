## Phase 5 — Song Recommendation Training Layer

### Purpose

This layer performs **heuristic calibration** for Song Recommendations.

It consumes **selection-level feature rows** produced in Phase 5 and generates
**static selector parameters** for deployment.

This is NOT a model training system.
It is a deterministic, explainable calibration layer.

---

### Pipeline Role

```
aggregation → features → training → evaluation → artifact export → deployment
```

This layer transforms behavior signals into **deployment-safe selector parameters**.

---

### Phase Boundary

- **Upstream:** Features Layer output (selection-level feature rows)
- **Downstream:** Deployment artifacts + evaluation
- **Runtime impact:** None (deployment only)

Phase 6 runtime MUST NOT load or adapt these artifacts dynamically.

---

### Non‑Negotiable Boundaries

This layer MUST:

- operate offline (Phase 5 only)
- be deterministic and auditable
- calibrate only selection heuristics
- produce static, bounded parameters
- preserve traceability to feature inputs

This layer MUST NOT:

- consume tips content, taxonomy, severity, or narrative
- perform gameplay inference
- introduce runtime adaptation
- depend on Phase 6 runtime modules

---

### Inputs

Inputs are selection-level feature rows containing:

#### Identity / Traceability
- player_id
- game_id
- recommendation_set_id
- song_id
- provenance_id (recommended)

#### Selection Signals
- rank
- outcome_score
- final_outcome

#### Engagement Features
- count_* fields
- any_* flags

#### Optional Diagnostics
- widen_step_index
- producer_rank

---

### Feature Schema Alignment (NEW)

This layer supports inputs from:

```
build_selection_feature_rows(...)
```

including wrapper format:

```python
{
  "rows": [...],
  "summary": {...},
  "feature_schema_version": "..."
}
```

Training MUST:

- detect feature_schema_version
- report compatibility
- remain backward-safe

---

## Outputs

This layer produces:

1. Static Selector Parameters

Deployment-safe JSON:

- widen_steps
- top_producers
- rank_decay_alpha

2. Training Report

Includes:

- row counts (input / used / dropped)
- whether defaults were used
- learned fields
- outcome statistics
- feature schema alignment

---

## Determinism & Auditability

- No randomness
- No time-based tuning
- Stable outputs for identical inputs
- Explicit bounded parameter ranges

---

## Relationship to Evaluation

Outputs are used for:

- regression guard validation
- performance comparison vs baseline
- deployment eligibility checks

---

## Design Intent

This layer exists to let Phase 5 learn:

✅ “Which selection heuristics perform better?”

without learning:

❌ “What gameplay means”
❌ “What tips should say”

---

**Training calibrates decision knobs — it never defines meaning.**