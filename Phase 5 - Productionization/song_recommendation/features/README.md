# Phase 5 — Song Recommendation Features Layer

## Purpose

The Features Layer transforms **aggregated song recommendation feedback rows**
into **training-ready feature rows** for offline heuristic calibration.

This layer is strictly **offline only** and exists inside Phase 5.

---

## Phase Boundary

- **Upstream:** Aggregation Layer output (selection-level rows)
- **Downstream:** Training / calibration code (Phase 5 only)
- **Runtime impact:** None (deployment only)

This layer must never be imported by Phase 6 runtime.

---

## Non‑Negotiable Boundaries

This layer MUST:

- operate offline (Phase 5 only)
- be deterministic and auditable
- remain strictly selection-level
- emit explainable, bounded features

This layer MUST NOT:

- include tips, taxonomy, severity, narrative, or chart semantics
- infer gameplay meaning
- perform ranking or selection decisions
- consume feedback to alter runtime behavior directly

Any semantic leakage is invalid by definition.

---

## Inputs

Inputs are aggregated rows keyed per recommended item exposure, typically including:

- identity: `player_id`, `game_id`, `recommendation_set_id`, `song_id`, `difficulty`, `rank`
- context (non-semantic): `tier_id`, `target_metric`, `catalog_fingerprint`, `locale`
- outcomes: `final_outcome`, `action_counts`, `first_seen_utc`, `last_seen_utc`

---

## Outputs

Outputs are feature rows containing:

- stable identity fields (for joins / audits)
- selection context (tier/target metric if provided)
- outcome labels (e.g., numeric `outcome_score`)
- bounded engagement signals (counts + boolean flags)
- optional deterministic time span features

The output is suitable for:
- heuristic calibration
- regression testing
- offline evaluation

---

## Determinism Guarantees

- No randomness, sampling, or wall-clock dependence
- Stable sorting of output rows
- Explicit outcome mapping rules

---

## Design Intent

This layer exists to let Phase 5 learn:

✅ “Which selection heuristics work better?”  
without learning:  
❌ “What tips should say” or “What gameplay means”