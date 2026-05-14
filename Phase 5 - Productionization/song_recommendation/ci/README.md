## Phase 5 — Song Recommendation CI Tests

This directory contains **contract‑level CI tests** for the
Phase 5 Song Recommendation learning pipeline.

These tests do not validate model quality.
They enforce **non‑negotiable learning invariants** that must hold
before any learning artifact may be promoted or deployed.

---

## Scope and Responsibility

These CI tests apply **only to Phase 5 (offline learning)**.

They ensure that Phase 5 learning:
- is strictly offline,
- is deterministic and auditable,
- does not consume or emit gameplay semantics,
- does not influence runtime behavior directly,
- and produces deployment‑safe static artifacts.

These tests MUST NOT:
- import Phase 6 runtime code,
- modify completed phases (Phase 1–4.5),
- or introduce runtime learning behavior.

---

## Invariants Enforced

This CI suite enforces the following invariants:

- **Offline‑only learning**  
  Phase 5 learning must not depend on runtime state or services.

- **No semantic leakage**  
  Tips, taxonomy, severity, narrative, or gameplay semantics must never
  appear in aggregation, features, training, or evaluation layers.

- **Deterministic outputs**  
  Identical inputs must always produce identical outputs,
  regardless of execution order or environment.

- **Static deployment artifacts only**  
  Outputs must be static, versioned artifacts introduced via deployment,
  never dynamically loaded at runtime.

- **Regression protection**  
  Learning results must be evaluated against baselines and guarded
  against quality regressions before promotion.

Any violation of these invariants invalidates the learning loop.

---

## Determinism as a Hard Contract (CI‑Enforced)

Determinism is **not a best‑effort property** of Phase 5 learning.
It is a **hard contract enforced by CI**.

Specifically:

- Determinism tests are explicitly marked as **hard‑gate CI checks**
- Any determinism failure causes the CI pipeline to fail immediately
- No learning artifact may be promoted if determinism is violated
- No override or partial acceptance is permitted

This guarantees that Phase 5 learning remains:
- auditable,
- reproducible,
- and safe to deploy without introducing runtime uncertainty.

Violating determinism invalidates the learning loop by definition.

---

## Test Structure Overview

The CI tests are organized by learning layer:

- **aggregation/**  
  Determinism, outcome priority, and semantic‑leak prevention

- **features/**  
  Deterministic feature construction and safe column enforcement

- **training/**  
  Static parameter calibration and order‑independent learning

- **evaluation/**  
  Deterministic metrics, baseline deltas, and regression guards

- **orchestrator/**  
  End‑to‑end pipeline determinism and artifact consistency

Meta tests validate the **entire Phase 5 pipeline as a single system**.

---

## CI Failure Policy

Any CI failure in this directory results in:

- ❌ learning artifact rejection
- ❌ blocked promotion or deployment
- ❌ required investigation before retry

These failures represent **contract violations**, not tuning issues.

---

## Design Intent

This CI layer exists to make Phase 5 Song Recommendation learning:

✅ safe to iterate  
✅ safe to audit  
✅ safe to deploy  

without making Phase 6 runtime behavior unsafe.

**If these tests fail, the learning loop must stop.**