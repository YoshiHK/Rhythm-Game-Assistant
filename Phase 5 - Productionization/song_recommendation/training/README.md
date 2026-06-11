# Phase 5 — Song Recommendation Training Layer

## Purpose

This layer performs **heuristic calibration** for Song Recommendations.

It consumes **selection-level feature rows** (built offline in Phase 5) and produces
**static selector parameters** intended for **deployment only**.

This is not a model training system. It is a deterministic calibration layer.

---

## Phase Boundary

- **Upstream:** Features Layer output (selection-level feature rows)
- **Downstream:** Deployment artifacts (static parameters) + evaluation reports
- **Runtime impact:** None (deployment only)

Phase 6 runtime MUST NOT load these artifacts dynamically.

---

## Non‑Negotiable Boundaries

This layer MUST:

- operate offline (Phase 5 only)
- remain deterministic and auditable
- calibrate only selection heuristics (windows, rank decay, diversity knobs)
- produce static, bounded parameters

This layer MUST NOT:

- consume tips content, taxonomy, severity, or narrative fields
- perform gameplay inference
- introduce runtime adaptation
- depend on Phase 6 routing modules

---

## Inputs

Inputs are feature rows containing safe, selection-level signals such as:

- identity: `game_id`, `song_id`, `recommendation_set_id`, `rank`
- outcomes: `final_outcome`, `outcome_score`, action counts
- context: `tier_id`, `target_metric`, `catalog_fingerprint`, `locale`
- optional selection diagnostics: `widen_step_index`, `producer_rank`

Any gameplay semantic fields are forbidden.

---

## Outputs

This layer produces:

1) **Static selector parameters** (JSON-friendly), such as:
- widen steps
- top producers
- rank decay alpha

2) **Training report**:
- row counts, defaults used, learned fields
- basic outcome statistics for QA and regression checks

---

## Determinism & Auditability

- No randomness
- No time-based tuning
- Stable output for the same input rows
- Explicit, bounded parameter ranges

---

## Design Intent

The training layer exists to let Phase 5 learn:

✅ “Which selection heuristics perform better?”  
without learning:  
❌ “What gameplay means” or “What tips should say”.