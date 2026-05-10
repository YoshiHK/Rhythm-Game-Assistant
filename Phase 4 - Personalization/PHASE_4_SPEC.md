# Phase 4 Specification — Personalization

**Status:** Design‑Locked ✅  
**Scope:** Phase 4 (Personalization)  
**Normative Authority:** Runtime + CI

---

## §0. Normative Status

This specification is **normative**.

Compliance is enforced by:
- Phase 4 runtime implementation, and
- Phase 4 CI governance layer.

Where runtime behavior is ambiguous, **CI interpretation is authoritative**.

---

## §1. Inputs (Normative)

Phase 4 accepts:
- deterministic outputs from Phases 1–3,
- player context and feature flags,
- locale metadata (passed through only).

Inputs are treated as read‑only.

---

## §2. Determinism (Normative)

### Requirement

For identical inputs, Phase 4 MUST produce identical outputs.

### Enforcement

- Runtime MUST avoid nondeterminism.
- CI MUST verify determinism using:
  - repeated execution checks,
  - fixture‑based regression tests.

Any nondeterministic output is a **spec violation**.

---

## §3. Output Structure (Normative)

Phase 4 outputs MUST:
- preserve element identity,
- preserve semantic meaning,
- include explainability provenance,
- be JSON‑serializable.

---

## §4. Semantic Immutability (Normative)

### Requirement

Phase 4 MUST NOT modify semantic fields produced by Phases 1–3, including:
- severity labels,
- scores,
- coverage,
- guidance,
- matched tags.

### Enforcement

- Runtime treats these fields as read‑only.
- CI fails on any detected mutation.

Semantic immutability is **non‑negotiable**.

---

## §5. Safe Adjustment (Normative)

### Requirement

Adjustments MAY be applied only through the safe‑adjustment layer.

Adjustments MUST be:
- bounded,
- non‑destructive,
- explicitly declared.

### Enforcement

- Runtime MUST expose guardrails.
- CI MUST fail if the guardrail surface is missing or bypassed.

---

## §6. Decision Source (Normative)

Phase 4 MUST declare a `decision_source`:

- `rule`
- `model`
- `hybrid`

The value MUST be explicit and auditable.

---

## §7. Explainability Chain (Normative, CI‑Enforced)

### §7.1 Chain Definition

Phase 4 MUST maintain:

decision_source → model_outputs → applied_adjustments → provenance

---

### §7.2 Rules

- If `decision_source == "model"` or `"hybrid"`:
  - `model_outputs` MUST be present and non‑empty
  - `applied_adjustments` MUST reflect `model_outputs`
  - `provenance.adjustments` MUST match `applied_adjustments`

- If `decision_source == "rule"`:
  - `model_outputs` MUST be empty
  - `applied_adjustments` MUST be empty

---

### §7.3 Ordering Consistency

If ordering is produced by the model:
- output ordering MUST respect the model ordering
- relative order MUST be preserved

---

### §7.4 Model Metadata (Optional)

If present, `model_metadata` MUST:
- be an object,
- contain string fields only,
- include `model_role` when decision_source is model‑driven.

---

### Enforcement

All rules in §7 are **enforced by CI**.
Violations are **architectural errors**.

---

## §8. Fixtures as Policy Surface (Normative)

Phase 4 fixtures are **normative policy surfaces**.

They exist to:
- represent allowed behavior,
- detect regressions,
- enforce safety and explainability invariants.

Fixtures are **not quality benchmarks**.

CI treats fixtures as authoritative.

---

## §9. Event Logging (Normative)

Phase 4 MUST emit events conforming to declared schemas.

CI enforces:
- schema presence,
- parseability.

---

## §10. CI Authority Statement

The Phase 4 CI layer is authoritative for:
- invariant enforcement,
- contract validation,
- regression detection.

Runtime behavior that passes CI is considered **spec‑compliant**.

---

## §11. Non‑Goals

Phase 4 does NOT specify:
- localization behavior (Phase 4.5),
- recommendation logic (Phase 7),
- learning outcomes (Phase 5),
- platform concerns (Phase 6).

---

## §12. Design‑Locked Statement

As of this revision:

> **Phase 4 specification is Design‑Locked ✅**

Future changes must preserve all guarantees above.