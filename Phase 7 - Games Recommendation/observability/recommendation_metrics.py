# Phase 7 — Recommendation Metrics Catalog

This document defines the **canonical set of metrics**
emitted by Phase 7 for observability and analysis.

---

## 1. Volume & Coverage

- `recommendation.requested`
  - Number of Phase 7 recommendation requests

- `recommendation.returned`
  - Number of recommendations returned

- `recommendation.empty`
  - Requests returning zero recommendations

- `recommendation.coverage_ratio`
  - returned / requested

---

## 2. Explainability Quality

- `explanation.present_ratio`
  - % of items with explanation attached

- `explanation.why_count`
  - Number of “why” signals per recommendation item

- `explanation.summary_present`
  - Whether a summary explanation is present

---

## 3. Ranking Health

- `ranking.score_distribution`
  - Distribution of recommendation scores (binned)

- `ranking.diversity.game_id`
  - Count of distinct game_ids per response

---

## 4. Latency (Semantic)

- `phase7.execution_time_ms`
  - End-to-end Phase 7 execution time
  - (Measured by Phase 6; Phase 7 only emits timestamps)

---

## 5. Failure & Degradation Signals

- `phase7.disabled`
  - Phase 7 disabled by config or lifecycle

- `phase7.no_candidates`
  - No recommendable games available

- `phase7.degraded`
  - Fallback behavior triggered (e.g. no ranker)

---

## Notes

- These metrics are **semantic**, not infrastructural.
- Alerting thresholds are defined by Phase 6.
- Experiment interpretation belongs to Phase 5.