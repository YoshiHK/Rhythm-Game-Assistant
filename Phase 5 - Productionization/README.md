# Phase 5 — Productionization & Offline Learning

Phase 5 defines the **productionization and offline learning layer**
of the Rhythm Game Assistant.

It converts **correct, explainable personalization** (Phases 1–4.5)
into a **measurable, improvable, and scalable system**
without changing gameplay semantics, localization guarantees,
or runtime determinism.

Phase 5 is where learning happens — **but only offline**.

---

## Phase Boundary (Non‑Negotiable)

Phase 5 is:

- ✅ downstream‑only of Phases 1–4.5
- ✅ non‑semantic
- ✅ offline‑learning‑only
- ✅ explainability‑preserving
- ✅ deployment‑driven

Phase 5 MUST NOT:

- ❌ modify element selection, severity, or guidance
- ❌ reinterpret gameplay meaning
- ❌ perform live or online learning
- ❌ deploy or activate models directly
- ❌ affect any completed phase

Violating these rules invalidates Phase 5.

---

## What Phase 5 Does

Phase 5 exists to:

- close learning loops using **feedback and curator gold**,
- enable **safe, offline model and heuristic improvement**,
- productionize **song‑level recommendations** as stable contracts,
- support **guided practice** (opt‑in, non‑judgmental),
- enable **experimentation, marketplace flows, and safety signaling**,
- prepare learning outputs for **Phase 6 governance and hardening**.

Phase 5 provides **contracts and infrastructure**, not UI logic
and not runtime decision‑making.

---

## Song Recommendation Learning Loop (Phase 5)

Song Recommendation learning is a **first‑class Phase 5 subsystem**.

It is implemented as a **fully offline, deterministic learning pipeline**
that improves *selection heuristics* without touching gameplay semantics.

### High‑Level Flow

Phase 6 Runtime
→ deterministic song recommendations
→ exposure metadata + feedback events
Phase 5 Learning
→ aggregation
→ feature construction
→ heuristic calibration
→ evaluation & regression guards
→ static artifact generation
Deployment
→ Phase 6 configuration update

### Key Properties

- offline only
- deterministic by contract
- non‑semantic
- deployment‑only outputs
- CI hard‑gated (determinism, semantic isolation, regression safety)

If any invariant is violated, the learning loop must stop.

---

## Subsystems

Phase 5 is composed of the following subsystems:

- **Feedback Aggregation**  
  Normalize and group player/system outcomes into learning‑safe signals.

- **Curator Gold & Labeling**  
  Scale human review, disagreement tracking, and gold label generation.

- **Offline Retrain & Model Ops**  
  Train, validate, and register candidate models and artifacts offline.

- **Recommendation Layer (Song‑Level)**  
  Define stable, read‑only recommendation contracts with rationale.

- **Practice Integration (Optional)**  
  Map tips to drills and opt‑in in‑session practice hints.

- **Observability & Experimentation**  
  Define metrics, experiments, and feature‑flag safety bounds.

- **Marketplace Layer**  
  Manage creator participation, content catalogs, and monetization signals.

- **Safety / Legal / Anti‑Cheat Signals**  
  Record safety‑relevant events and escalate evidence to Phase 6.

Each subsystem owns schemas, invariants, and CI checks.

---

## Determinism as a Hard Contract

All Phase 5 learning outputs **MUST be deterministic**.

Determinism is not a best‑effort guideline.
It is a **hard contract enforced by CI**.

- Determinism tests are hard‑gated
- Any determinism failure fails the pipeline
- No learning artifact may be promoted if determinism is broken

This guarantees that Phase 5 learning remains:
- auditable,
- reproducible,
- and safe to deploy without runtime uncertainty.

---

## Relationship to Other Phases

- **Inputs:**  
  Phase 4 (Personalization), Phase 4.5 (Localization)

- **Governance:**  
  Phase 6 hardens, validates, and governs Phase 5 outputs

- **Expansion:**  
  Phase 7 builds on Phase 5 + Phase 6 to expand
  recommendations from songs → games

Phase 5 MUST be stable, deterministic, and explainable
before any downstream expansion.

---

## Design Intent

Phase 5 prioritizes **trust before scale**.

It exists to let the system improve without:
- semantic drift,
- opaque behavior,
- unsafe deployment,
- or premature judgment.

Learning is allowed.  
Runtime adaptation is not.

---

**End of Phase 5 README**