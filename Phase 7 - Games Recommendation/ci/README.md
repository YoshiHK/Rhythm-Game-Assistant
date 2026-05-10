# Phase 7 — CI Test Suite (Games Recommendations)

**Status:** Design‑Locked ✅  
**Scope:** Phase 7 (Games Recommendations) only  
**Execution Context:** CI‑only (non‑runtime)

---

## 1. Purpose

This directory defines the **continuous integration (CI) guardrails**
for **Phase 7 — Games Recommendations**.

Phase 7 CI exists to **protect architectural and contractual invariants**,
not to evaluate recommendation quality or business outcomes.

If these tests pass, Phase 7 can be:
- safely integrated,
- safely evolved,
- or temporarily disabled  
without breaking upstream phases or platform guarantees.

---

## 2. Core Principle

**Phase 7 CI tests are guardrails, not quality evaluators.**

They ensure that:
- contracts do not silently break,
- architectural boundaries are respected,
- runtime behavior remains deterministic and non‑blocking.

They intentionally avoid judging:
- recommendation “goodness”,
- player satisfaction,
- engagement or monetization outcomes.

---

## 3. Relationship to Phase 7 Architecture

Phase 7 CI mirrors the **Phase 7 routing structure** and enforces
its declared boundaries.

CI categories correspond directly to Phase 7 components:

| CI Category | Phase 7 Component |
|------------|------------------|
| `catalog/` | Presentation metadata & catalog wiring |
| `eligibility/` | Explicit recommendation eligibility rules |
| `ranking/` | Deterministic ranker & scoring integrity |
| `policy/` | Diversity & explainability guardrails |
| `contracts/` | Observability & feedback payload contracts |

Phase 7 CI never introduces new routing paths.

---

## 4. CI Layering Model

Phase 7 CI tests are organized into **five governance layers**.

### 4.1 Contract‑Level Tests (Always‑On)

**Purpose**
- Ensure payload shapes are stable and serializable.
- Ensure non‑blocking behavior when downstream sinks fail.

**Examples**
- `test_observability_payload_shape.py`
- `test_feedback_payload_shape.py`

**Guarantees**
- Required keys exist.
- Values are JSON‑serializable.
- Sink or transport failures never crash Phase 7.

**Non‑goals**
- Do not validate metric values.
- Do not validate learning or feedback consumption.

---

### 4.2 Structural Safety

**Purpose**
- Ensure Phase 7 does not crash under minimal or empty inputs.
- Ensure deterministic behavior for identical inputs.

**Examples**
- `test_ranker.py`
- `test_catalog_completeness.py`
- `test_catalog_presentation.py`

**Guarantees**
- Same input → same output.
- Empty or minimal inputs are handled safely.

**Non‑goals**
- No evaluation of ranking quality.

---

### 4.3 Governance & Readiness

**Purpose**
- Enforce explicit eligibility and data readiness rules.

**Examples**
- `test_recommendation_eligibility.py`
- `test_recommendation_data_readiness.py`

**Guarantees**
- No silent exclusion of enabled games.
- Recommendable games meet minimal UI‑safe data requirements.

**Non‑goals**
- No runtime policy enforcement.
- No ranking logic.

---

### 4.4 Behavioral Guardrails

**Purpose**
- Prevent degenerate or unsafe recommendation behavior.

**Examples**
- `test_recommendation_explainability_coverage.py`
- `test_recommendation_score_diversity.py`
- `test_recommendation_scoring_availability.py`

**Guarantees**
- Recommendations remain explainable.
- Scores are not degenerate (e.g., all identical).
- Every eligible game is scorable.

**Non‑goals**
- Does not judge explanation quality.
- Does not enforce diversity thresholds.

---

## 5. What Phase 7 CI MUST NOT Do

Phase 7 CI tests MUST NOT:

- import Phase 6 infrastructure or APIs,
- depend on production databases or services,
- perform I/O beyond in‑memory operations,
- introduce runtime branching or feature flags,
- redefine eligibility, ranking, or explanation semantics.

Violations of these rules are **architectural errors**.

---

## 6. Evolution Rules (Design‑Locked)

Phase 7 CI is **design‑locked**.

Allowed changes:
- Add tests for newly introduced Phase 7 components.
- Add regression coverage for fixed bugs.
- Strengthen contract validation (shape, determinism).

Disallowed changes:
- Adding “pure checks” that gate runtime behavior.
- Introducing quality scoring or business KPIs.
- Using CI to enforce semantic or product policy.

---

## 7. Relationship to Other Phases

- **Phase 5**
  - Consumes feedback and metrics produced by Phase 7.
  - CI does not validate learning outcomes.

- **Phase 6**
  - Owns transport, observability pipelines, and alerting.
  - CI validates payload contracts, not delivery.

- **Phase 7 Runtime**
  - Must remain independent from CI logic.
  - CI failures block merges, not runtime execution.

---

## 8. Summary

Phase 7 CI ensures that **Games Recommendations remain safe, bounded, and reversible**.

It is intentionally strict and conservative.

If you are unsure whether a test belongs here,
it probably does not.
