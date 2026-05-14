# PHASE_5_SONG_RECOMMENDATION_LEARNING_SPEC.md

## Phase 5 — Song Recommendation Learning (Offline Only)

**Status:** Design‑Locked  
**Scope:** Phase 5 (Productionization)  
**Upstream Dependencies:** Phase 6 (Song Recommendation Feedback) ✅  
**Downstream Impact:** Deployment only

**Non‑Negotiable Rule:**  
**Do not modify anything in Completed Phases.**

---

## 0. Positioning

Song Recommendation learning in Phase 5 exists to **improve selection quality**
without altering gameplay meaning, tips semantics, or runtime determinism.

This phase closes the loop between:
- what songs were recommended,
- how users reacted,
- and how future selection heuristics should be calibrated.

Phase 5 learning is **offline, auditable, and reversible**.

---

## 1. Purpose

Phase 5 Song Recommendation learning exists to:

- analyze user feedback on song recommendations,
- evaluate the effectiveness of selection heuristics,
- calibrate deterministic selector parameters,
- and improve discovery and practice outcomes over time.

It does **not** exist to:
- invent new recommendation logic,
- reinterpret gameplay difficulty,
- or override completed semantic phases.

---

## 2. Learning Loop Overview

The Song Recommendation learning loop spans multiple phases:

Phase 6 (Runtime)
└─ Deterministic selection
└─ Exposure metadata (set_id, rank, diagnostics)
└─ Forward-only feedback emission
↓
Phase 5 (Offline Learning)
└─ Feedback aggregation
└─ Feature construction
└─ Heuristic calibration
↓
Deployment
└─ Static parameter rollout
↓
Phase 6 (Next Version Runtime)

At no point does feedback directly influence runtime behavior.

---

## 3. Inputs

Phase 5 consumes the following inputs:

### 3.1 Feedback Events
- Song recommendation feedback emitted by Phase 6
- Actions such as:
  - accept
  - ignore
  - played
  - completed

### 3.2 Exposure Metadata
- recommendation_set_id
- rank
- tier_id (if present)
- target_metric (if present)
- catalog_fingerprint
- selection diagnostics:
  - window_used
  - widen_step_index
  - producer_rank

---

## 4. Allowed Learning Targets

Phase 5 MAY learn and adjust:

- window widening behavior
- tier targeting accuracy
- rank-based discounting
- producer diversity trade-offs
- short-term vs long-term engagement weighting

All learned outputs MUST be expressible as:
- static parameters
- deterministic lookup tables
- bounded configuration values

---

## 5. Forbidden Learning Targets (Strict)

Phase 5 MUST NOT learn from or modify:

- tips text or guidance wording
- taxonomy or pattern labels
- severity definitions
- gameplay correctness judgments
- narrative structure
- localization or language content

Any learning signal that leaks gameplay semantics is invalid by definition.

---

## 6. Training and Evaluation

### 6.1 Training

Training focuses on **heuristic calibration**, not model invention.

Examples:
- adjusting window thresholds
- reweighting producer proximity
- tuning rank decay curves

No runtime model inference is permitted.

---

### 6.2 Evaluation

Evaluation MUST include:

- acceptance rate deltas
- play-through rate changes
- completion rate deltas
- regression guards against quality drops

Learning results MUST be explainable and reviewable.

---

## 7. Outputs

Phase 5 produces:

### 7.1 Deployment Artifacts
- Static selector parameter files (e.g. JSON)
- Versioned and auditable

### 7.2 Reports
- Offline evaluation summaries
- Change justification and metrics

Phase 6 runtime MUST NOT load artifacts dynamically.

---

## 8. Deployment Contract

- Learned outputs are introduced via deployment only
- Rollouts must be reversible
- No partial or silent updates are allowed
- Phase 6 remains deterministic across a single deployment

---

## 9. Invariants

The following invariants MUST always hold:

- Learning is offline only
- Runtime behavior is deterministic
- Completed phases remain immutable
- Phase 6 does not consume learning outputs directly
- Phase 5 does not emit runtime logic

Violating any invariant invalidates the learning loop.

---

## 10. Contract Closure

Phase 5 Song Recommendation learning enables the system to:

- improve discovery quality,
- remain explainable and safe,
- and evolve without semantic drift.

This spec is **authoritative and design‑locked**.

**End of PHASE_5_SONG_RECOMMENDATION_LEARNING_SPEC.md**