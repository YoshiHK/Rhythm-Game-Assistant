# Phase 4.5 — Localization

Phase 4.5 provides **safe, deterministic localization**
for personalized gameplay tips.

It adapts presentation to language and locale
**without changing gameplay meaning**.

---

## What Phase 4.5 Does

- Applies locale‑specific narrative templates
- Enforces placeholder safety
- Enforces word budgets
- Handles locale normalization and fallback
- Emits localization metadata

---

## What Phase 4.5 Does NOT Do

- ❌ No gameplay analysis
- ❌ No semantic decisions
- ❌ No personalization logic
- ❌ No free‑form translation
- ❌ No runtime gating

---

## Where It Runs

Phase 4.5:
- is invoked only via **Phase 6**
- never runs standalone
- never bypasses platform controls

---

## Folder Layout

Phase_4.5_Localization/
├─ translations/
├─ locale_normalizer/
├─ ci/                # governance only
├─ PHASE_4.5_SPEC.md
├─ PHASE_4.5_ARCHITECTURE.md
└─ README.md

---

## CI Governance

Localization is protected by **Phase 4.5 CI**:

- Structural checks
- Template parity
- Placeholder & token safety
- Word budgets
- Auditable waivers

CI failures indicate **contract violations**, not translation quality issues.

---

## Relationship to Other Phases

- Phase 4 → produces personalized content
- Phase 4.5 → localizes presentation
- Phase 6 → routes and handles failures
- Phase 7 → unrelated (separate CI)

---

## Design Principles

- Deterministic
- Non‑semantic
- CI‑governed
- No silent fallback
- No versioned contracts

---

## Summary

Phase 4.5 ensures that localization is:
**safe, explainable, and scalable**.

If something fails here,
the fix is always in localization assets or CI governance —
never in runtime logic.

