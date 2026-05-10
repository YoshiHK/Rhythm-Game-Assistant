# Phase 4 — Personalization

**Status:** Design‑Locked ✅  
**Role:** Semantic Personalization (Presentation‑Safe)  
**Runtime Entry:** Phase 6 only

---

## 1. What Phase 4 Is

Phase 4 applies **bounded, explainable personalization**
on top of the deterministic analysis produced by Phases 1–3.

It adjusts **ordering, emphasis, and presentation** of gameplay tips
**without changing their semantic meaning**.

Phase 4 is the **last phase allowed to influence gameplay tips directly**.
All downstream phases treat Phase 4 outputs as authoritative.

---

## 2. What Phase 4 Is NOT

Phase 4 does **NOT**:

- ❌ modify severity, score, coverage, or guidance semantics
- ❌ introduce nondeterminism
- ❌ perform localization (Phase 4.5)
- ❌ perform game recommendations (Phase 7)
- ❌ bypass Phase 6 governance
- ❌ gate runtime execution based on CI outcomes

If you are looking for localization or recommendation logic,
you are in the wrong phase.

---

## 3. Where Phase 4 Sits in the Pipeline

Phase 1–3 (Deterministic Core)
↓
Phase 4 (Personalization)
↓
Phase 6 (API / Platform)

- Phase 4 is invoked **only** via Phase 6.
- Phase 4 never invokes earlier phases.
- Phase 4 never invokes Phase 4.5 or Phase 7.

---

## 4. Core Responsibilities

Phase 4 is responsible for:

- personalization decisions (rule / model / hybrid),
- safe adjustment application (bounded, non‑destructive),
- explainability provenance generation,
- narrative module selection (non‑i18n),
- event logging and feedback capture,
- curator triage and offline learning hooks.

---

## 5. Determinism & Safety Guarantees

Phase 4 guarantees:

- **Determinism**  
  Identical inputs always produce identical outputs.

- **Semantic Immutability**  
  Fields produced by Phases 1–3 are treated as read‑only.

- **Explainability**  
  Every personalization decision is auditable.

These guarantees are enforced jointly by **runtime code and CI governance**.

---

## 6. Explainability Chain (Key Concept)

Phase 4 enforces a strict explainability chain:

decision_source
→ model_outputs
→ applied_adjustments
→ provenance

- Rule‑based decisions produce no model outputs.
- Model‑driven decisions must expose their effects explicitly.
- Provenance must reflect what was actually applied.

Breaking this chain is considered an **architectural error**.

---

## 7. Directory Overview

Phase_4_Personalization/
├─ interfaces/        # Hard contracts (authoritative)
├─ schemas/           # CI‑enforced schemas
├─ registry/          # Declarative allow‑lists
├─ runtime/           # Deterministic execution spine
├─ decision/          # Presentation‑only decisions
├─ inference/         # Advisory model boundary
├─ safe_adjustment/   # Guardrails (non‑destructive)
├─ narrative/         # Narrative v3 selection (non‑i18n)
├─ events/            # Observational only
├─ curator/           # Offline human loop
├─ ci/                # CI governance (NON‑RUNTIME)
└─ utils/             # Helpers

If you are changing behavior, you are likely touching `runtime/`.
If you are enforcing guarantees, you are likely touching `ci/`.

---

## 8. CI Governance (Very Important)

Phase 4 includes a **first‑class CI governance layer**.

CI exists to:
- enforce determinism,
- enforce semantic immutability,
- enforce explainability chain integrity,
- detect accidental behavioral drift.

CI is:
- ✅ authoritative for governance
- ❌ never part of runtime execution

CI failures block merges, **not runtime execution**.

See `Phase_4_Personalization/ci/README.md` for details.

---

## 9. Fixtures as Policy Surface

Fixtures under `ci/tests/fixtures/` are **design‑locked policy surfaces**.

They exist to:
- represent allowed behavior,
- detect regressions,
- enforce safety and explainability invariants.

Fixtures are **not quality benchmarks**.
They are authoritative examples of what Phase 4 is allowed to do.

---

## 10. Relationship to Other Phases

- **Phases 1–3**  
  Deterministic core. Phase 4 must not mutate their semantics.

- **Phase 4.5**  
  Localization and language handling. Separate CI and ownership.

- **Phase 5**  
  Learning and retraining. Phase 4 emits signals but does not learn.

- **Phase 6**  
  Platform and governance gate. Owns runtime invocation.

- **Phase 7**  
  Game recommendations. Entirely separate decision surface.

---

## 11. Design‑Locked Statement

As of this revision:

> **Phase 4 — Runtime, CI, Architecture, and Spec are Design‑Locked ✅**

Future changes must:
- preserve all guarantees above,
- update CI before runtime,
- remain presentation‑safe and explainable.

If you are unsure whether a change belongs in Phase 4,
it probably does not.