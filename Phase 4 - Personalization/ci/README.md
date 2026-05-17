# Phase 4 CI — Personalization Governance (Design-Locked)

## Overview

Phase 4 CI enforces **personalization invariants** to guarantee:

- Deterministic behavior
- Semantic immutability
- Safe adjustment boundaries
- Explainability chain integrity
- Ordering consistency

This is a **governance system**, not a quality evaluation system.

---

## CI Architecture

Phase 4 CI is composed of three layers:

### 1. Runner-Level Checks (Fast, Always-On)

Executed via:

phase_4_ci_runner.py

These checks enforce core invariants:

| Check | Purpose |
|------|--------|
| determinism_checks | Ensure identical inputs produce identical outputs |
| semantic_immutability_check | Ensure no semantic mutation (structure + fields) |
| ordering_contract_check ✅ | Enforce ordering behavior (Spec §7.3) |
| safety_checks | Guardrail enforcement |
| explainability_checks | Provenance + decision chain validation |

---

### 2. Pytest Policy Tests (Deep Validation)

Located in:

ci/tests/

These tests enforce deeper guarantees:

- fixture-based determinism
- explainability chain integrity (§7.2)
- safe adjustment bounds
- decision schema presence
- event logging contracts
- bounded semantic + ordering enforcement (personalized fixtures)

---

### 3. Infrastructure Tests

Validate CI system correctness:

- runner must fail on missing scripts
- runner must execute deterministically
- runner must exit 0 on success

---

## Ordering Contract (NEW)

Phase 4 enforces:

### Rule-based path
- MUST preserve exact element ordering
- No reordering allowed

### Model / Hybrid path
- MUST respect model-provided ordering
- Ordering must be preserved as subsequence

This is enforced by:
- ordering_contract_check.py (fast check)
- test_personalized_fixture_bounds.py (deep enforcement)

---

## Design Principles

Phase 4 CI follows strict separation:

| Layer | Responsibility |
|------|----------------|
| Runner | Enforce "what must be checked" |
| Tests | Define "what correct behavior is" |
| Runtime | Execute personalization (non-CI) |

---

## Non-Goals

Phase 4 CI does NOT:

- evaluate recommendation quality
- validate narrative phrasing
- assess localization correctness
- perform ranking evaluation

---

## Final Statement

Phase 4 CI guarantees:

- personalization is **deterministic**
- semantics are **immutable**
- ordering is **controlled**
- adjustments are **bounded**
- decisions are **explainable**

This forms the **non-bypassable safety barrier** for Phase 4.
