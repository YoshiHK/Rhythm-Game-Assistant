# Phase 7 — CI Test Suite

This directory defines the **continuous integration (CI) guardrails**
for **Phase 7 – Games Recommendations**.

These tests exist to **protect architectural invariants**,
not to evaluate recommendation quality.

---

## Core Principle

> **Phase 7 CI tests are guardrails, not quality evaluators.**

They ensure that:
- contracts do not silently break,
- boundaries are not violated,
- and runtime behavior does not regress in unsafe ways.

They intentionally avoid judging:
- recommendation “goodness”,
- player satisfaction,
- or business outcomes.

---

## CI Layering Model

Phase 7 CI tests are organized into **four conceptual layers**.

### 1. Contract‑Level Tests (Always‑On)

Purpose:
- Ensure payload shapes are stable and serializable.
- Ensure non‑blocking behavior when downstream systems fail.

Examples:
- `test_observability_payload_shape.py`
- `test_feedback_payload_shape.py`

Guarantees:
- Required keys exist.
- Values are JSON‑serializable.
- Sink / transport failures never crash Phase 7.

Non‑goals:
- Do not validate metric values.
- Do not validate learning behavior.

---

### 2. Wave 1 — Structural Safety

Purpose:
- Ensure Phase 7 does not crash under minimal or empty inputs.
- Ensure deterministic behavior for identical inputs.

Examples:
- `test_ranker.py`
- `test_catalog_completeness.py`
- `test_catalog_presentation.py`

Guarantees:
- Same input → same output.
- Empty / minimal inputs are handled safely.

Non‑goals:
- No evaluation of ranking quality.

---

### 3. Wave 2 — Governance & Readiness

Purpose:
- Enforce governance rules around eligibility and data readiness.

Examples:
- `test_recommendation_eligibility.py`
- `test_recommendation_data_readiness.py`

Guarantees:
- No “silent exclusion” of enabled games.
- Recommendable games meet minimal UI‑safe data requirements.

Non‑goals:
- No ranking logic.
- No runtime policy enforcement.

---

### 4. Wave 3 — Behavioral Guardrails

Purpose:
- Prevent degenerate or unsafe recommendation behavior.

Examples:
- `test_recommendation_explainability_coverage.py`
- `test_recommendation_score_diversity.py`
- `test_recommendation_scoring_availability.py`

Guarantees:
- Recommendations remain explainable.
- Scores are not degenerate (e.g., all identical).
- Every eligible game is scorable.

Non‑goals:
- Does not judge explanation quality.
- Does not enforce diversity thresholds.

---

## What CI Tests MUST NOT Do

Phase 7 CI tests MUST NOT:

- import Phase 6 infrastructure or APIs
- depend on production databases or services
- perform I/O beyond in‑memory operations
- introduce runtime branching or feature flags
- redefine eligibility or ranking semantics

Violations of these rules are considered architectural errors.

---

## Relationship to Other Phases

- **Phase 5**
  - Consumes feedback and metrics produced by Phase 7.
  - CI does not validate learning outcomes.

- **Phase 6**
  - Owns transport, observability pipelines, and alerting.
  - CI only validates payload contracts, not delivery.

- **Phase 7 Runtime**
  - Must remain independent from CI logic.
  - CI failures block merges, not runtime execution.

---

## Design Intent

If all Phase 7 CI tests pass, the following statement must be true:

> *Phase 7 can be safely integrated, evolved, or temporarily disabled
> without breaking upstream phases or platform guarantees.*

This README is intentionally strict.
If you are unsure whether a test belongs here, it probably does not.