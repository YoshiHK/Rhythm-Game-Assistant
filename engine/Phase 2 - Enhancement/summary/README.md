# Phase 2 Summary Layer – README

## Purpose

This directory implements the **Phase 2 Summary Layer**
corresponding to **Stage 7: Summaries**.

The Summary Layer consolidates outputs from earlier in the analysis, without influencing decisions.The Summary Layer consolidates outputs from earlier stages

---

## Responsibilities

The Phase 2 Summary Layer is responsible for:

1. Building per-chart summaries from selected analysed elements
2. Computing dominance scores using:
   dominant_score = score × section_coverage
3. Aggregating per-chart summaries into batch-level summaries
4. Producing schema-aligned, downstream-safe outputs

This layer is the **final analytical output boundary** of Phase 2.

---

## What This Layer Does NOT Do

This layer does **not**:

- infer severity, score, or coverage
- select or rank elements
- fill guidance fields
- render narrative text
- apply personalization or player modeling

---

## Files

### `dominance_score.py`
Defines the canonical dominance score computation.

Responsibilities:
- compute dominance as score × section_coverage
- enforce numeric bounds
- provide a shared utility for summaries and selection alignment

---

### `per_chart_summary.py`
Builds per-chart summary objects.

Responsibilities:
- aggregate selected analysed elements
- attach dominance scores
- emit canonical per-chart summary structures

---

### `batch_summary.py`
Builds batch-level summaries.

Responsibilities:
- aggregate per-chart summaries
- compute batch-level statistics deterministically
- emit schema-aligned batch summary objects

---

## Determinism Guarantees

The Summary Layer guarantees that:

- identical inputs produce identical summaries
- dominance computation is stable and bounded
- ordering of elements in summaries is deterministic
- no randomness or external state is used

---

## Relationship to Other Phases

### Phase 2 (Upstream)
- Consumes analysed elements from Stage 5.1
- Consumes selected elements from Stage 5.2

### Phase 2 (Downstream)
- Summary outputs are considered final for Phase 2

### Phase 3+
- Phase 3 Orchestrator consumes summaries for logging, QA, and export
- Phase 4 may reference summaries for explanation, but must not
  reinterpret their semantics

---

## Change Policy

✅ Allowed:
- Additive summary fields (schema-aligned)
- Additional batch-level metrics (deterministic)

❌ Not Allowed:
- Changing dominance definition
- Embedding decision logic
- Adding personalization signals

Any breaking change requires:
- explicit schema + interface versioning, or
- a parallel summary implementation

---

## Summary

The Phase 2 Summary Layer provides the **authoritative explanation artifacts**
for the enhancement pipeline.

It ensures that outputs are:
- auditable
- stable
- safe for downstream use
into **canonical, stable summary objects** that explain
