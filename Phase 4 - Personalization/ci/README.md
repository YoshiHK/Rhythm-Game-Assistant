# Phase 4 CI — Personalization Governance

**Status:** Design‑Locked ✅  
**Scope:** Phase 4 (Personalization) only  
**Execution Context:** CI‑only (non‑runtime)

---

## 1. Purpose

This directory defines the **CI governance layer** for **Phase 4 — Personalization**.

It exists to:
- protect deterministic core invariants (Phases 1–3 remain intact),
- enforce Phase 4 safety boundaries (presentation‑only personalization),
- enforce explainability chain integrity (auditable provenance),
- prevent silent regressions in Phase 4 runtime wiring.

Phase 4 CI is **not** part of runtime execution.

---

## 2. What This CI Layer IS

Phase 4 CI:

- ✅ enforces deterministic behavior (same input → same output),
- ✅ enforces safety invariants (no semantic mutation),
- ✅ enforces explainability completeness (provenance chain),
- ✅ validates contract/document/schema presence,
- ✅ detects accidental behavioral drift via fixtures.

---

## 3. What This CI Layer is NOT

Phase 4 CI does **NOT**:

- ❌ judge model quality or ranking performance,
- ❌ evaluate narrative wording quality (Phase 4.5 owns localization constraints),
- ❌ introduce new personalization heuristics,
- ❌ mutate Phase 4 runtime behavior,
- ❌ gate runtime execution directly,
- ❌ bypass Phase 6 governance.

CI failures block merges; they do not change runtime behavior.

---

## 4. CI Structure

``