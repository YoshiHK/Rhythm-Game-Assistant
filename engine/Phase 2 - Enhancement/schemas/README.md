# Phase 2 Schemas – README

## Purpose

This directory contains the **CI‑enforced canonical schemas**
for Phase 2 (Enhancement) of the Tip Generation System.

Schemas in this directory define the **authoritative data shapes**
produced by Phase 2 stages and consumed by downstream systems
(Phase 3 Orchestrator, Phase 4 Personalization, QA, and CI).

---

## Role of Schemas in Phase 2

Phase 2 schemas are:

- **Normative**: code must conform to them
- **Stable**: changes require explicit versioning
- **Downstream‑facing**: they protect consumers from refactors

They differ from Phase 1 schemas, which are descriptive and historical.

---

## Schema Files

- `section_metrics.schema.json`  
  Canonical shape for SectionMetrics produced in Stage 2–4.1.

- `element_candidate.schema.json`  
  Canonical shape for element candidates inferred in Stage 4.2.

- `analysed_element.schema.json`  
  Canonical shape for analysed elements after severity, score, and coverage (Stage 5.1).

- `guidance.schema.json`  
  Canonical shape for guidance fields filled in Track C (Stage 5.3).

- `tips_output.schema.json`  
  Canonical shape for final narrative output (Stage 6).

- `summary.schema.json`  
  Canonical shape for per‑chart and batch summaries (Stage 7).

---

## Guarantees

Phase 2 schemas guarantee that:

- Field names and types are explicit
- Required fields are enforced
- Optional fields are additive only
- No personalization semantics are embedded

---

## Change Policy

✅ Allowed:
- Additive fields
- New schemas for new Phase 2 capabilities

❌ Not Allowed:
- Removing required fields
- Changing field meaning
- Tightening constraints without versioning

---

## Summary

Phase 2 schemas are the **contractual backbone**
that allows Phase 2 to evolve internally
without breaking downstream phases.