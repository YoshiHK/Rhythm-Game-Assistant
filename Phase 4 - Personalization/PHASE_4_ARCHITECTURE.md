# Phase 4 Architecture — Personalization

**Status:** Design‑Locked ✅  
**Phase Type:** Semantic Personalization (Presentation‑Safe)  
**Runtime Entry:** Phase 6 only

---

## 1. Purpose

Phase 4 applies **bounded, explainable personalization** on top of the
deterministic core (Phases 1–3).

It adapts ordering, emphasis, and presentation **without mutating semantic
meaning**.

Phase 4 is the **last phase allowed to influence gameplay tips directly**.
All downstream phases must treat Phase 4 outputs as authoritative.

---

## 2. Architectural Position

Phase 1–3 (Deterministic Core)
↓
Phase 4 (Personalization)
↓
Phase 6 (API / Platform)

- Phase 4 is invoked **only** via Phase 6.
- Phase 4 never invokes earlier phases.
- Phase 4 never invokes Phase 4.5 (localization) or Phase 7 (recommendations).

---

## 3. Responsibilities

Phase 4 is responsible for:

- bounded personalization of elements,
- explainable decision provenance,
- safe adjustment application,
- narrative module selection (non‑i18n),
- event logging and feedback capture,
- curator triage and offline learning hooks.

---

## 4. Non‑Responsibilities (Hard Boundaries)

Phase 4 MUST NOT:

- mutate semantic fields from Phases 1–3,
- introduce nondeterminism,
- perform localization (Phase 4.5),
- perform game recommendations (Phase 7),
- bypass Phase 6 governance,
- gate runtime execution based on CI outcomes.

---

## 5. Runtime vs CI Responsibilities

| Responsibility | Runtime | CI |
|---|---|---|
| Deterministic execution | ✅ | ✅ (regression enforcement) |
| Semantic immutability | ✅ | ✅ (authoritative) |
| Explainability provenance | ✅ | ✅ (authoritative) |
| Safety guardrails | ✅ | ✅ (authoritative) |
| Localization | ❌ | ❌ |
| Recommendation logic | ❌ | ❌ |

CI failures block merges, **not runtime execution**.

---

## 6. CI Governance Layer (Architectural)

Phase 4 includes a **first‑class CI governance layer**.

The CI layer:
- is CI‑only and non‑runtime,
- enforces architectural invariants,
- detects accidental behavioral drift,
- is authoritative for governance.

Phase 1–3 → Phase 4 Runtime → Phase 6
▲
│
Phase 4 CI Governance

The CI layer never participates in decision‑making.

---

## 7. Explainability Chain (Architectural Guarantee)

Phase 4 guarantees an explainability chain:

decision_source
→ model_outputs
→ applied_adjustments
→ provenance

This chain is:
- produced by runtime,
- **enforced by CI**,
- required for auditability and safety.

Any break in this chain is an **architectural violation**.

---

## 8. Determinism Guarantee

For identical inputs, Phase 4 MUST produce identical outputs.

- Runtime must avoid nondeterminism.
- CI enforces determinism via repeated execution and fixtures.

---

## 9. Safe Adjustment Architecture

All personalization adjustments MUST pass through the
**safe‑adjustment layer**.

Adjustments must be:
- bounded,
- non‑destructive,
- explicitly declared.

Bypassing this layer is forbidden.

---

## 10. Design‑Locked Statement

As of this revision:

> **Phase 4 runtime + CI governance is Design‑Locked ✅**

Future changes must:
- preserve all invariants,
- update CI before runtime,
- remain presentation‑safe and explainable.
