## Phase 5 — Song Recommendation Features Layer

### Purpose

The Features Layer transforms **aggregated song recommendation feedback rows**
into **training-ready feature rows** for offline heuristic calibration.

This layer is strictly **offline only** and exists inside Phase 5.

---

### Pipeline Role

```
feedback_event → aggregation → (optional) interpretation_bridge → features → training → evaluation
```

This layer performs a **pure, mechanical transformation** from
selection-level aggregates into model-ready inputs.

---

### Phase Boundary

- **Upstream:** Aggregation Layer output (selection-level rows)
- **Downstream:** Training / calibration / evaluation (Phase 5 only)
- **Runtime impact:** None (deployment only)

This layer must never be imported by Phase 6 runtime.

---

### Non‑Negotiable Boundaries

This layer MUST:

- operate offline (Phase 5 only)
- be deterministic and auditable
- remain strictly selection-level
- emit bounded, explainable features
- preserve traceability to aggregation inputs

This layer MUST NOT:

- include tips, taxonomy, severity, or narrative
- infer gameplay meaning
- perform ranking or recommendation selection
- introduce semantic interpretation
- alter runtime behavior

Any semantic leakage is invalid by definition.

---

### Inputs

Inputs are aggregated rows keyed per recommended item exposure.

Required fields (minimum):

- player_id
- game_id
- recommendation_set_id
- song_id
- final_outcome
- action_counts

Optional non-semantic context:

- difficulty, rank
- tier_id, target_metric
- catalog_fingerprint, locale
- session_id
- first_seen_utc, last_seen_utc
- provenance_id (strongly recommended)

---

### Derived Reason (NEW)

Inputs MAY include derived machine reasoning from the interpretation bridge:

- derived_primary_reason
- derived_reason_codes
- derived_reason_confidence

Rules:

- MUST NOT be used as model features by default
- MUST remain separate from behavioral signals
- MAY be preserved as metadata for debugging / evaluation

---

### Outputs

Feature rows MUST contain:

#### Identity / Traceability
- player_id
- game_id
- recommendation_set_id
- song_id
- provenance_id (if available)

#### Selection Context
- difficulty, rank
- tier_id, target_metric
- locale

#### Outcome Labels
- final_outcome
- outcome_score (deterministic mapping)

#### Engagement Signals
- count_ignore / accept / played / completed
- any_accept_or_better
- any_played_or_better
- any_completed

#### Timing Features
- exposure_span_seconds (deterministic)

---

### Feature Schema Version (NEW)

Each output batch MUST include:

- feature_schema_version

This ensures compatibility with:
- training_dataset.schema.json
- evaluation layer
- model registry

---

### Determinism Guarantees

- No randomness or sampling
- No wall-clock dependence
- Stable sorting of output rows
- Explicit outcome mapping
- Identical input ⇒ identical output

---

### Relationship to Evaluation

Feature outputs are consumed by:

- evaluate_selection_quality
- training dataset construction

They MUST remain compatible with:

- regression guard metrics
- selection-level evaluation logic

---

### Design Intent

This layer exists to let Phase 5 learn:

✅ “Which selection heuristics work better?”

without learning:

❌ “What gameplay means”  
❌ “What tips should say”

---

**Features transform behavior into signals — not meaning into labels.**