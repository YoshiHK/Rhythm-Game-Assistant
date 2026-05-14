# Phase 5 — Song Recommendation Learning

This directory defines the **offline learning system** for
Song Recommendations in the Rhythm Game Assistant.

Phase 5 exists to close the learning loop:
from observed user behavior to calibrated selection heuristics,
**without changing gameplay semantics or runtime determinism**.

This layer is **offline only**, **auditable**, and **deployment‑driven**.

---

## Positioning

Song Recommendation learning is part of **Phase 5 (Productionization)**.

It operates strictly **downstream of runtime execution** and **upstream of deployment**:

Phase 6 (Runtime)
└─ Deterministic song selection
└─ Exposure metadata + feedback emission
↓
Phase 5 (Offline Learning)
└─ Aggregate feedback
└─ Build features
└─ Calibrate heuristics
└─ Evaluate & guard regressions
↓
Deployment
└─ Static parameter rollout

At no point does feedback influence runtime behavior directly.

---

## Scope

Phase 5 Song Recommendation learning is responsible for:

- aggregating forward‑only feedback emitted by Phase 6,
- constructing selection‑level features,
- calibrating deterministic selector heuristics,
- evaluating learning outcomes and guarding regressions,
- producing **static, deployment‑safe artifacts**.

Phase 5 is **not** responsible for:
- runtime recommendation decisions,
- gameplay analysis or tips generation,
- personalization inference at request time,
- UI or presentation logic.

---

## Non‑Negotiable Boundaries

This layer MUST:

- operate offline only,
- remain deterministic and auditable,
- avoid gameplay semantics entirely,
- produce static artifacts introduced via deployment,
- preserve all contracts of Completed Phases.

This layer MUST NOT:

- import or depend on Phase 6 runtime code,
- consume tips, taxonomy, severity, or narrative content,
- perform runtime learning or adaptation,
- dynamically load artifacts at runtime,
- modify behavior of any completed phase.

Violating any of these rules invalidates the learning loop.

---

## Directory Structure Overview

The Song Recommendation learning pipeline is structured as follows:

- **aggregation/**  
  Aggregates Phase 6 feedback into selection‑level records.

- **features/**  
  Transforms aggregated records into training‑ready features
  (selection‑level only, no semantics).

- **training/**  
  Calibrates deterministic selector parameters
  (heuristics, not models).

- **evaluation/**  
  Computes acceptance / play / completion metrics,
  compares against baselines, and enforces regression guards.

- **artifacts/**  
  Writes static, auditable artifacts for deployment
  (selector params, reports, baselines).

- **utils/**  
  Offline orchestration helpers to run the full learning pipeline end‑to‑end.

- **tests/**  
  Contract‑level CI tests enforcing determinism,
  semantic isolation, and deployment safety.

---

## Determinism as a Hard Contract

All Phase 5 Song Recommendation learning outputs **MUST be deterministic**.

Determinism is not a quality goal.
It is a **hard contract enforced by CI**.

Specifically:
- Determinism tests are marked as hard‑gate checks
- Any determinism violation fails the CI pipeline
- No learning artifact may be promoted if determinism is broken

This guarantees that Phase 5 learning remains:
- reproducible,
- reviewable,
- and safe to deploy without runtime uncertainty.

Violating determinism invalidates the learning loop by definition.

---

## Relationship to Other Phases

- **Upstream:** Phase 6 (Song Recommendation runtime & feedback emission)
- **Parallel:** Other Phase 5 learning systems (tips, practice, marketplace, etc.)
- **Downstream:** Deployment and Phase 6 configuration

Phase 5 learning may evolve independently,
as long as it preserves Phase 6 runtime determinism
and respects completed phase boundaries.

---

## Design Intent

This layer exists to let the system learn:

✅ which **selection heuristics** work better over time  

without learning:

❌ what gameplay means  
❌ what tips should say  
❌ how runtime decisions should adapt dynamically  

Phase 5 makes learning **safe** by making it:
offline, deterministic, auditable, and reversible.

---

**If Phase 5 Song Recommendation learning fails CI,  the learning loop must stop.**