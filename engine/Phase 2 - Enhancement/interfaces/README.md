# Phase 2 Interfaces – README

## contracts** for Phase 2## Purpose
(Enhancement) of the Tip Generation System.

These interfaces describe the **canonical data boundaries**
between Phase 2 internal stages and all downstream consumers
(Phase 3 Orchestrator, Phase 4 Personalization, tooling, and CI).

> **Important**
> - Interfaces in this directory are authoritative for Phase 2
> - They define *what* data looks like, not *how* it is produced
> - No runtime logic is implemented here

---

## Role of Interfaces in Phase 2

Unlike Phase 1 (where interfaces are implicit and descriptive),
Phase 2 interfaces are **explicit and normative**:

- They define **stable contracts** for enhanced data
- They are the basis for Phase 2 schemas and CI checks
- They protect downstream phases from internal refactors

Phase 2 interfaces MUST be treated as **hard boundaries**.

---

## Interface Files

The following interfaces are defined in this directory:

### 1. `section_metrics.interface.md`
Contract for SectionMetrics produced during visual analysis
(Stage 2–4.1) and consumed by severity and scoring logic.

This interface guarantees:
- ordered sections
- normalized metric ranges
- deterministic aggregation behavior

---

### 2. `element_candidate.interface.md`
Contract for element candidates produced from pattern tags
(Stage 4.2).

This interface guarantees:
- official element naming
- explicit matched_tags and training_items
- no scoring or ranking at this stage

---

### 3. `analysed_element.interface.md`
Contract for analysed elements produced after severity, score,
and coverage inference (Stage 5.1).

This is the **primary analytical unit** for:
- selection (Track B)
- guidance filling (Track C)
- summaries (Stage 7)

---

### 4. `guidance.interface.md`
Contract for guidance fields filled in Track C (Stage 5.3).

This interface guarantees:
- explanatory, non-personalized guidance
- deterministic phrasing inputs
- readiness for narrative rendering

---

### 5. `narrative_output.interface.md`
Contract for final narrative output produced in Track D (Stage 6).

This interface defines:
- the stable paragraph structure
- safe, presentation-ready text output

---

## Guarantees

Phase 2 interfaces guarantee that:

- Data shapes are stable and explicit
- Fields are additive unless explicitly deprecated
- Ordering and typing are deterministic
- No player-specific personalization is applied

---

## Relationship to Other Layers

- **Phase 1**
  - Phase 2 consumes Phase 1 outputs
  - Phase 1 interfaces remain implicit and unchanged

- **Phase 3**
  - Phase 3 Orchestrator relies on Phase 2 interfaces
  - Adapters must conform to these contracts

- **Phase 4+**
  - Personalization and localization operate *after*
    Phase 2 interfaces
  - They must not mutate Phase 2 interface semantics

---

## Change Policy

✅ Allowed:
- Additive fields with backward compatibility
- Clarifications and documentation updates
- New interfaces for new Phase 2 capabilities

❌ Not Allowed:
- Removing required fields
- Changing field meanings
- Tightening constraints without versioning
- Introducing personalization semantics

Any breaking change requires:
- explicit versioning, or
- introduction of a parallel interface

---

## Summary

Phase 2 interfaces are the **stability spine**
between deterministic enhancement logic and all downstream phases.

They exist to make Phase 2:
- evolvable internally
- safe externally
- reliable as a platform boundary

