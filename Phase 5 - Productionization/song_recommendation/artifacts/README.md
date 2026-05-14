# Phase 5 — Song Recommendation Artifacts Layer

## Purpose

This layer writes **offline artifacts** produced by the Phase 5 Song Recommendation
learning loop, including:

- static selector parameters (deployment artifact)
- training reports (audit + QA)
- evaluation reports (metrics + regression guards)
- baseline metric snapshots (for future deltas)

This layer is **offline only**.

---

## Phase Boundary

- **Upstream:** Training + Evaluation layers (Phase 5)
- **Downstream:** Deployment pipeline (build-time integration)
- **Runtime impact:** None (Phase 6 must not load artifacts dynamically)

Artifacts are introduced via **deployment only**, consistent with the learning spec. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

---

## Non‑Negotiable Boundaries

This layer MUST:
- be deterministic and auditable
- serialize artifacts in stable JSON form
- avoid gameplay semantics and any tips content
- remain offline only (Phase 5)

This layer MUST NOT:
- introduce runtime loading requirements
- create a closed loop into Phase 6 runtime
- write or consume tips/taxonomy/severity/narrative content

---

## Artifact Files (Conventional)

- `song_selector_params.json`  
  Static selector parameters intended for deployment only.

- `song_selector_training_report.json`  
  Counts, defaults used, learned fields, basic summary metrics.

- `song_selector_evaluation_report.json`  
  Acceptance/play/completion metrics, baseline deltas, regression guard results.

- `song_selector_baseline_metrics.json`  
  Baseline metrics snapshot used offline to compute future deltas.

---

## Design Intent

Artifacts exist to make learning:
✅ reviewable  
✅ reproducible  
✅ reversible  

without changing runtime determinism.

Learning is offline. Deployment integrates results.