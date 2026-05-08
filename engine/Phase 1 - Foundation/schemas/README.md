# Phase 1 Schemas – README

## Purpose

This directory contains the **canonical JSON schemas** used by Phase 1
(Foundation) of the Tip Generation System.

These schemas describe the *effective output shapes* produced by the
Phase 1 pipeline and MUST be treated as **stable and locked**.

---

## Schema Files

### 1. `proseka_internal_analysis.schema.json`
Describes the internal analysis object used to drive:
- element construction
- guidance filling
- narrative rendering

This schema reflects the historical Phase 1 analysis contract.

---

### 2. `proseka_batch_summary.schema.json`
Describes the per-chart and batch-level summary outputs.

Used for:
- reporting
- QA inspection
- downstream presentation

---

### 3. `proseka_summary_blocks.schema.json`
Defines the structured summary blocks emitted after tips generation.

These blocks are presentation-oriented and additive.

---

### 4. `tips_generation_spec.schema.json`
Defines the advisory rules that guide:
- element eligibility
- narrative constraints
- output shaping

This schema is **advisory**, not strictly enforced.

---

## Guarantees

- Schemas in this directory are **read-only**
- No Phase 2+ component may assume stricter validation than described here
- Phase 1 code will NOT be retrofitted to satisfy new constraints

---

## Relationship to Later Phases

- **Phase 2** re-interprets these schemas via explicit adapters
- **Phase 3** may validate or transform these schemas at ingestion time
- **Phase 4+** must not directly depend on Phase 1 schema internals

---

## Change Policy

✅ Allowed:
- Clarifying documentation
- Comments and README updates

❌ Not Allowed:
- Changing required fields
- Tightening constraints
- Adding enforcement semantics

Any evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

These schemas represent the **historical truth** of Phase 1.
They exist to be understood, not to be reshaped.
``