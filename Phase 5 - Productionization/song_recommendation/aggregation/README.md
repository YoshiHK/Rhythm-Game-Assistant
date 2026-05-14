# Phase 5 — Song Recommendation Aggregation Layer

## Purpose

The Song Recommendation Aggregation Layer aggregates
**forward‑only Song Recommendation feedback events**
emitted by Phase 6 into **training‑ready, selection‑level datasets**.

This layer exists to enable an **offline learning loop**
that improves song selection heuristics over time
**without modifying gameplay semantics or runtime behavior**.

This layer is **offline only** and must be:
- deterministic,
- auditable,
- and safe to evolve.

---

## Phase Boundary

This aggregation layer operates **exclusively in Phase 5**.

- **Upstream:** Phase 6 Song Recommendation feedback emission
- **Downstream:** Feature construction, heuristic calibration, evaluation
- **Runtime impact:** None (deployment only)

At no point does this layer:
- influence runtime selection,
- feed results back into Phase 6 directly,
- or participate in request routing.

---

## Non‑Negotiable Boundaries

This aggregation layer MUST:

- operate offline (Phase 5 only),
- remain deterministic (same inputs ⇒ same outputs),
- avoid gameplay semantics entirely,
- produce explainable, reviewable aggregates.

This aggregation layer MUST NOT:

- consume or interpret tips content,
- consume taxonomy or severity fields,
- perform ranking or recommendation selection,
- introduce learning behavior into runtime,
- create runtime dependencies on Phase 6.

Violating any of the above breaks the phase boundary.

---

## Inputs

### Feedback Events (Forward‑Only)

The primary input is a stream or batch of feedback event objects
emitted by Phase 6, representing user actions on recommended songs
(e.g. `accept`, `ignore`, `played`, `completed`).

Each event MUST include the minimal identity required for aggregation:

- `player_id`
- `game_id`
- `recommendation_set_id`
- `song_id`
- `action`
- `timestamp_utc`

Optional **non‑semantic** context is allowed (and useful):

- `rank`
- `tier_id`
- `target_metric`
- `catalog_fingerprint`
- `locale`
- `session_id`

Any semantic or gameplay‑derived fields are forbidden inputs.

---

## Aggregation Rules

Aggregation is performed at the **recommended item exposure level**.

The canonical aggregation key is:

(player_id, game_id, recommendation_set_id, song_id, difficulty, rank)

For each aggregated item:

- multiple feedback events may be combined,
- action counts are tracked per action type,
- a single **final outcome** is derived using a fixed priority order
  (e.g. `completed` > `played` > `accept` > `ignore`),
- first‑seen and last‑seen timestamps are recorded deterministically.

All rules must be explicit, stable, and version‑controlled.

---

## Outputs

This layer produces two outputs:

### 1. Aggregated Rows

Per‑item, selection‑level rows suitable for:

- feature construction,
- heuristic calibration,
- offline evaluation and regression checks.

These rows MUST remain:
- presentation‑safe,
- non‑semantic,
- and explainable.

### 2. Aggregation Summary

A lightweight summary suitable for:

- QA sanity checks,
- volume and coverage tracking,
- non‑semantic drift detection.

---

## Determinism & Auditability

The aggregation process MUST satisfy:

- no dependence on wall‑clock execution time,
- no randomness or sampling,
- stable sorting and grouping rules,
- reproducible outputs given identical inputs.

Every aggregation run must be auditable after the fact.

---

## Design Intent

This layer exists to make Song Recommendation learning:

✅ safe to analyze  
✅ safe to iterate  
✅ safe to audit  

without making runtime recommendation behavior unsafe.

**Aggregation observes.  Selection decides elsewhere.**