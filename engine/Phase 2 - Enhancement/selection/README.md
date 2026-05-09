# Phase 2 Selection Layer – README

## Purpose

This directory implements the **Phase 2 Selection Layer**
corresponding to **Stage 5.2: Select Elements for Tips (Track B)**.

The Selection Layer is responsible for deciding **which analysed elements**
(from Stage 5.1 / Track A) should be included in tips generation,
under deterministic, spec-aligned constraints.

It does **not** modify element semantics, severity, or guidance content.

---

## Responsibilities

The Phase 2 Selection Layer is responsible for:

1. Selecting a fixed number of elements per difficulty:
   - expert → 3
   - master → 3
   - append → 4
2. Applying dominance-aware ranking
3. Enforcing stable, deterministic tie-breaking
4. Applying conservative diversity constraints (when applicable)
5. Producing an ordered list of selected elements for downstream stages

This layer is the **only place** in Phase 2 where element inclusion/exclusion
decisions are made.

---

## What This Layer Does NOT Do

This layer does **not**:

- infer severity, score, or coverage (Stage 5.1 responsibility)
- modify severity labels or numerical scores
- fill guidance fields (Stage 5.3)
- render narrative text (Stage 6)
- apply personalization, player modeling, or difficulty adaptation
- reinterpret Phase 1 semantics

---

## Files

### `selector_v2_bridge.py`
Primary entrypoint for Stage 5.2 selection.

Responsibilities:
- prefer `selector_v2.select_elements_v2()` when available
- enforce target counts by difficulty
- provide deterministic fallback selection when selector_v2 is unavailable
- normalize input/output shapes for downstream stages

This module treats `selector_v2` as a **black box** and never depends
on its internal implementation.

---

### `dominance_ranker.py`
Provides deterministic ranking utilities.

Responsibilities:
- compute dominance score (default: `score * section_coverage`)
- rank elements using stable tie-breaking:
  1. dominance score (desc)
  2. score (desc)
  3. severity (desc)
  4. section coverage (desc)
  5. element name (asc)

This ranking logic is shared by:
- primary selection
- fallback selection
- summary dominance alignment

---

### `diversity_rules.py`
Applies conservative diversity constraints.

Responsibilities:
- limit over-representation of the same category (if category exists)
- preserve ranked order
- ensure target count is met via deterministic backfilling

If category information is not present, this module behaves as a **no-op**.

---

## Determinism Guarantees

The Selection Layer guarantees that:

- identical inputs produce identical selected outputs
- ordering is stable and reproducible
- no randomness or external state is used
- fallback behavior is fully deterministic

---

## Relationship to Other Phases

### Phase 1
- Phase 1 selection logic remains untouched
- Phase 2 selection is an enhancement layer, not a rewrite

### Phase 2 (Downstream)
- **Stage 5.3 (Guidance / Track C)** consumes selected elements
- **Stage 7 (Summaries)** relies on consistent dominance ordering

### Phase 3+
- Phase 3 Orchestrator may call this layer directly
- Phase 4 Personalization may re-rank presentation, but must not
  reinterpret selection semantics

---

## Change Policy

✅ Allowed:
- Improved dominance heuristics (schema-compatible)
- Additional diversity constraints (additive, optional)
- Versioned selector bridges

❌ Not Allowed:
- Changing target counts without spec updates
- Embedding severity or guidance logic
- Introducing non-deterministic behavior
- Adding player-specific logic

Any breaking change requires:
- explicit interface + schema versioning, or
- a parallel selection implementation

---

## Summary

The Phase 2 Selection Layer is the **decision boundary**
between numerical analysis and explanatory guidance.

It ensures that:
- tips remain focused
- difficulty signals are representative
- downstream narrative stays coherent and explainable