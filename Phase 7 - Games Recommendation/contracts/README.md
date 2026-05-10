# Phase 7 Contracts Layer

This directory defines the **stable public contracts** for Phase 7 — Games Recommendations.

---

## Purpose

The Phase 7 contracts layer exists to:
- define **what Phase 7 produces and consumes**,
- provide a **stable integration surface** for downstream consumers,
- and allow Phase 7 implementations to evolve **without breaking upstream or downstream expectations**.

This layer represents **the authoritative contract surface** of Phase 7.

---

## Contract Invariants

The following rules are non‑negotiable:

- Contracts are **additive only**.
- Existing fields MUST NOT change semantics.
- Removal or reinterpretation of fields is prohibited.
- Any breaking change requires an explicit contract redesign.

Phase 7 does **not** support runtime contract version switching.

---

## Files

- `types.py`
  - Canonical data structures for Phase 7 inputs and outputs.
  - These types define the **public recommendation contract** for Phase 7.

- `config.py`
  - Non‑semantic configuration only.
  - Used for feature gating and safe rollout control.
  - Configuration MUST NOT alter recommendation semantics.

- `feature_flags.py`
  - Progressive rollout and experiment gating.
  - Flags MUST NOT change the meaning or structure of outputs.

---

## What This Layer Is NOT

- ❌ Business logic
- ❌ Ranking or eligibility logic
- ❌ Platform hardening or enforcement
- ❌ Personalization override logic
- ❌ Runtime version management

All such behavior belongs to implementation layers or to Phase 6.

---

## Status

- **Contract State:** Stable
- **Mutation Policy:** Append‑only
- **Versioning:** Not exposed at runtime