# Phase 2 Severity Layer – README

## Purpose

This directory implements the **Phase 2 Severity Layer**
corresponding to **Stage 5.1: Severity + Score + Coverage (Track A)**.

Its role is to **enhance**, not replace, the Phase 1 baseline
severity inference by applying deterministic calibration and
feature-based score refinement.

---

## Responsibilities

The Phase 2 Severity Layer is responsible for:

1. Running baseline severity inference (Phase 1 semantics)
2. Applying severity midpoint overrides (when enabled)
3. Computing section coverage from SectionMetrics
4. Blending chart-level scalar features into element scores
5. Emitting analysed elements with:
   - severity (label preserved by default)
   - score (refined)
   - section_coverage

This layer is the **only place** where severity-related
numerical refinement is allowed in Phase 2.

---

## What This Layer Does NOT Do

This layer does **not**:

- select elements for tips (Stage 5.2)
- fill guidance fields (Stage 5.3)
- render narrative text (Stage 6)
- apply personalization or player modeling
- redefine Phase 1 severity labels or taxonomy

---

## Files (Conceptual Roles)

### `severity_engine.py`
Coordinates severity enhancement.

Responsibilities:
- invoke Phase 1 baseline inference
- apply Phase 2 calibration hooks
- emit analysed element objects

---

### `coverage_calculator.py`
Computes section coverage.

Responsibilities:
- calculate coverage as:
  coverage(E) = (# sections meeting threshold) / (total sections)
- ensure coverage values are normalized and bounded

---

### `calibration_bridge.py`
Optional calibration layer.

Responsibilities:
- apply midpoint overrides
- integrate external calibration configs (if enabled)
- preserve original severity labels by default

---

### `feature_blender.py`
Optional feature-based score refinement.

Responsibilities:
- compute chart-level scalars from SectionMetrics
- blend scalars into element scores deterministically
- avoid overfitting or dominance inversion

---

## Determinism Guarantees

The Severity Layer guarantees that:

- identical inputs produce identical outputs
- severity labels are stable unless explicitly overridden
- score and coverage values are bounded
- no randomness or external state is used

---

## Relationship to Other Phases

### Phase 1
- Phase 1 provides baseline severity semantics
- Phase 2 MUST NOT mutate Phase 1 logic

### Phase 2 (Downstream)
- **Stage 5.2 (Selection / Track B)** consumes analysed elements
- **Stage 7 (Summaries)** uses score × section_coverage

### Phase 3+
- Phase 3 Orchestrator may call this layer directly
- Phase 4 Personalization must treat severity outputs as pre-decision inputs

---

## Change Policy

✅ Allowed:
- Additive feature blending (with schema support)
- Optional calibration layers (versioned)
- Numerical refinement within documented bounds

❌ Not Allowed:
- Changing severity taxonomy
- Making severity player-dependent
- Embedding selection or guidance logic
- Introducing non-determinism

Any breaking change requires:
- explicit schema + interface versioning, or
- a parallel severity implementation

---

## Summary

The Phase 2 Severity Layer is the **numerical refinement core**
of the enhancement pipeline.

It preserves Phase 1 semantics while enabling:
- better score fidelity
- clearer dominance signals
- safer downstream selection
``