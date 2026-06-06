## Phase 5 — Song Recommendation Aggregation Layer

### Purpose

The Song Recommendation Aggregation Layer aggregates **forward-only Song Recommendation feedback events**
emitted by Phase 6 into **training-ready, selection-level datasets**.

This layer exists to enable an **offline learning loop** that improves song selection heuristics over time
**without modifying gameplay semantics or runtime behavior**.

This layer is **offline only** and must remain:

- deterministic
- auditable
- safe to evolve

---

### Pipeline Role

```
feedback_event → interpretation_bridge → aggregate_song_feedback → features → training → evaluation
```


This layer remains the **selection-level aggregation boundary** for song recommendation learning.

It may consume **derived reasoning produced upstream by the interpretation bridge**,
but it MUST preserve the boundary between:

- raw feedback reality
- derived machine hypothesis

---

### Phase Boundary

This aggregation layer operates **exclusively in Phase 5**.

- **Upstream:** Phase 6 Song Recommendation feedback emission
- **Adjacent bridge:** interpretation_bridge (derived, non-authoritative reasoning)
- **Downstream:** Feature construction, heuristic calibration, evaluation
- **Runtime impact:** None (deployment only)

At no point does this layer:

- influence runtime selection
- feed results back into Phase 6 directly
- participate in request routing

---

### Non-Negotiable Boundaries

This aggregation layer MUST:

- operate offline (Phase 5 only)
- remain deterministic (same inputs ⇒ same outputs)
- avoid gameplay semantics in raw aggregation
- produce explainable, reviewable aggregates
- preserve traceability to raw input events

This aggregation layer MUST NOT:

- consume or interpret tips content directly
- consume taxonomy or severity as raw event inputs
- perform ranking or recommendation selection
- introduce learning behavior into runtime
- create runtime dependencies on Phase 6

Violating any of the above breaks the phase boundary.

---

### Inputs

#### 1. Raw Feedback Events (Forward-Only)

The primary input is a stream or batch of feedback event objects
emitted by Phase 6, representing user actions on recommended songs
(e.g. accept, ignore, played, completed).

Each event MUST include the minimal identity required for aggregation:

- player_id
- game_id
- recommendation_set_id
- song_id
- action
- timestamp_utc (or equivalent timestamp field)

Optional **non-semantic** context is allowed:

- rank
- tier_id
- target_metric
- catalog_fingerprint
- locale
- session_id

Any semantic or gameplay-derived fields are forbidden as raw aggregation inputs.

---

#### 2. Derived Reasoning (Optional, NEW)

The aggregation layer MAY receive **derived machine reasoning**
through the interpretation bridge.

If present, derived reasoning MUST:

- remain clearly separated from the raw event
- never overwrite raw feedback fields
- be treated as review-support metadata only

Examples:
- derived_reason_codes
- derived_primary_reason
- derived_reason_confidence

Derived reasoning is **not** authoritative truth.

---

### Aggregation Rules

Aggregation is performed at the **recommended item exposure level**.

The canonical aggregation key is:

```
(player_id, game_id, recommendation_set_id, song_id, difficulty, rank)
```

For each aggregated item:

- multiple feedback events may be combined
- action counts are tracked per action type
- a single **final outcome** is derived using a fixed priority order
  (e.g. completed > played > accept > ignore)
- first-seen and last-seen timestamps are recorded deterministically
- optional derived machine reasoning may be attached as separate fields

All rules must be explicit, stable, and version-controlled.

---

### Outputs

This layer produces two outputs:

#### 1. Aggregated Rows

Per-item, selection-level rows suitable for:

- feature construction
- heuristic calibration
- offline evaluation and regression checks

These rows MUST remain:

- presentation-safe
- selection-level
- explainable
- reproducible

They MAY include:

- non-semantic aggregate fields
- optional derived machine reasoning (separate from raw feedback)

---

#### 2. Aggregation Summary

A lightweight summary suitable for:

- QA sanity checks
- volume and coverage tracking
- non-semantic drift detection

---

### Determinism & Auditability

The aggregation process MUST satisfy:

- no dependence on wall-clock execution time
- no randomness or sampling
- stable sorting and grouping rules
- reproducible outputs given identical inputs

Every aggregation run must be auditable after the fact.

---

### Relationship to Curator Gold

Aggregation outputs are intended to become **curator-reviewable units** downstream.

This layer does **not** decide correctness.
It prepares stable evidence so that:

- machines can assist
- humans can judge
- training can remain traceable

---

### Design Intent

This layer exists to make Song Recommendation learning:

- ✅ safe to analyze
- ✅ safe to iterate
- ✅ safe to audit
- ✅ safe to connect to curator review

without making runtime recommendation behavior unsafe.

**Aggregation observes. Selection decides elsewhere.**