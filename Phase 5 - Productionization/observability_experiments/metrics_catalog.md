### Metrics Catalog (Phase 5)

Defines canonical metrics derived from telemetry events.

---

### Core Metrics

- tip_view_rate
- tip_use_rate
- completion_improvement
- recommendation_accept_rate
- retry_success_rate

---

### Metric Requirements (UPDATED)

All metrics MUST:

- be computed from telemetry_events.schema.json
- be linkable via provenance_id
- be reproducible from raw events
- be comparable across time windows

---

### Aggregation Rules (NEW)

Metrics MUST define:

- numerator
- denominator
- aggregation window
- grouping dimensions (e.g. experiment_id, variant)

Example:
tip_view_rate = viewed_tips / total_presented_tips

---

### Experiment Compatibility

Metrics MUST support:

- A/B comparison
- variant-level aggregation
- baseline comparison

---

### Relationship to Evaluation (NEW)

Metrics are consumed by:

- evaluate_selection_quality
- model validation checks

---

### Non‑Goals

Metrics MUST NOT:

- be used for runtime gating
- assign blame to users
- encode hidden thresholds

---

Metrics exist to:
> quantify behavior, not interpret meaning