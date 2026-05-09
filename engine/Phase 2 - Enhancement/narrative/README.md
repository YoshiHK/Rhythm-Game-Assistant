# Phase 2 Narrative Layer – README

## Purpose

This directory implements the **Phase 2 Narrative Layer**
correspond**corresponding to **Stage 6: Render Narrative (Track D)**.
(Stage 5.3) into **final, presentation-ready tips text**
using deterministic, spec-driven templates.

---

## Responsibilities

The Phase 2 Narrative Layer is responsible for:

1. Rendering two-paragraph tips text:
   - Paragraph 1: element summary
   - Paragraph 2: difficulty explanation and breakdown
2. Applying narrative templates defined by the tips-generation spec
3. Enforcing word budgets deterministically
4. Applying small readability adjustments without changing meaning

This layer produces the **final text output** for Phase 2.

---

## What This Layer Does NOT Do

This layer does **not**:

- infer severity, score, or coverage (Stage 5.1)
- select elements (Stage 5.2)
- fill guidance fields (Stage 5.3)
- apply personalization or player modeling
- perform localization or language switching

---

## Files

### `narrative_module_v2.py`
Primary entrypoint for Stage 6 narrative rendering.

Responsibilities:
- orchestrate template rendering
- assemble paragraph 1 and paragraph 2
- enforce word budgets per difficulty
- provide a stable Phase 2 narrative surface

---

### `template_renderer.py`
Template rendering helper.

Responsibilities:
- render text from spec-aligned templates
- substitute guidance fields deterministically
- avoid stylistic or semantic drift

---

### `readability_adjuster.py`
Readability adjustment helper.

Responsibilities:
- perform small wording adjustments when near word limits
- switch to compact breakdown variants when required
- preserve original meaning and tone

---

## Determinism Guarantees

The Narrative Layer guarantees that:

- identical guidance inputs produce identical text outputs
- template selection and substitution are deterministic
- word budget enforcement is stable
- no randomness or external state is used

---

## Relationship to Other Phases

### Phase 2 (Upstream)
- Consumes guidance objects from Stage 5.3
- Consumes difficulty context from runtime orchestration

### Phase 2 (Downstream)
- **Stage 7 (Summaries)** may reuse narrative fragments
- Output is considered final for Phase 2

### Phase 3+
- Phase 3 Orchestrator may call this layer directly
- Phase 4 Narrative v3 may rephrase text,
  but must not reinterpret guidance semantics

---

## Change Policy

✅ Allowed:
- New deterministic templates (versioned)
- Improved readability heuristics (non-breaking)
- Additional breakdown variants (spec-aligned)

❌ Not Allowed:
- Changing narrative tone rules
- Adding personalization or locale logic
- Embedding gameplay logic or selection logic

Any breaking change requires:
- explicit interface + schema versioning, or
- a parallel narrative implementation

---

## Summary

The Phase 2 Narrative Layer is the **final presentation boundary**
of the enhancement pipeline.

It ensures that tips are:
- readable
- consistent
- explainable

