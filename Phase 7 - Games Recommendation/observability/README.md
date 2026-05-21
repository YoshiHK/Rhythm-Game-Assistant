# Phase 7 — Observability Layer

This directory defines **what is observed and measured**
for **Phase 7 – Games Recommendations**.

---

## Purpose

The Observability Layer answers one question only:

> **How well is Phase 7 behaving, without influencing its behavior?**

It exists to support:
- monitoring,
- audits,
- experimentation,
- and learning feedback loops.

---

## Design Principles

- **Observational only**
  - No routing, ranking, or eligibility logic is allowed here.
  - Observability must never influence runtime decisions.

- **Non-blocking**
  - Metrics collection must not delay or fail user-facing flows.

- **Semantic-level metrics**
  - Focus on recommendation quality signals (coverage, explainability),
    not infrastructure health (owned by Phase 6).

- **Phase 6 owns transport**
  - This layer defines *what* to measure.
  - Phase 6 defines *how* metrics are collected, stored, and alerted on.

---

## Relationship to Other Phases

- **Phase 7**
  - Emits structured observation signals.
- **Phase 6**
  - Handles ingestion, aggregation, SLOs, and alerting.
- **Phase 5**
  - Consumes aggregated metrics for experimentation and learning.

This layer never closes the loop by itself.