# Phase 2 Guidance Layer – README

## Purpose

This directory implements the **Phase 2 Guidance Layer**
corresponding to **Stage 5.3: Fill Guidance Fields (Track C)**.

The Guidance Layer explains **why** selected elements contribute
to chart difficulty and **how** players should approach them,
without performing any selection or narrative rendering.

---

## Responsibilities

The Phase 2 Guidance Layer is responsible for:

1. Resolving dominant difficulty causes from taxonomy signals
2. Producing structured chart breakdown explanations
3. Filling guidance fields for each selected element:
   - difficulty_causes
   - chart_breakdown
   - primary_focus
   - secondary_focus
   - strategy
   - target_section

This layer produces **explanatory metadata**, not final text.

---

## What This Layer Does NOT Do

This layer does **not**:

- modify severity, score, or coverage (Stage 5.1)
- select or rank elements (Stage 5.2)
- render final narrative text (Stage 6)
- apply personalization or player modeling
- perform localization or tone adaptation

---

## Files

### `guidance_engine_v2.py`
Primary entrypoint for Stage 5.3.

Responsibilities:
- coordinate cause resolution and breakdown formatting
- attach guidance objects to analysed elements
- ensure outputs conform to `guidance.interface.md`
  and `guidance.schema.json`

---

### `cause_resolver.py`
Resolves dominant difficulty causes.

Responsibilities:
- analyze taxonomy categories and cues
- determine primary and secondary causes
- ensure stable, deterministic cause ordering

---

### `breakdown_formatter.py`
Formats chart breakdown explanations.

Responsibilities:
- convert mixed cue signals into readable breakdown text
- apply deterministic phrasing rules
- avoid narrative embellishment

---

## Determinism Guarantees

The Guidance Layer guarantees that:

- identical inputs produce identical guidance outputs
- ordering of causes and breakdowns is stable
- no randomness or external state is used

---

## Relationship to Other Phases

### Phase 2 (Upstream)
- Consumes **selected analysed elements** from Stage 5.2
- Consumes severity and coverage from Stage 5.1

### Phase 2 (Downstream)
- **Stage 6 (Narrative / Track D)** renders guidance into text
- **Stage 7 (Summaries)** may reuse cause signals

### Phase 3+
- Phase 3 Orchestrator may call this layer directly
- Phase 4 Personalization may rephrase narrative,
  but must not alter guidance semantics

---

## Change Policy

✅ Allowed:
- Improved cause heuristics (schema-compatible)
- Additional breakdown variants (deterministic)
- Versioned guidance engines

❌ Not Allowed:
- Severity or score manipulation
- Selection logic
- Narrative tone changes
- Player-specific logic

Any breaking change requires:
- explicit interface + schema versioning, or
- a parallel guidance implementation

---

## Summary

The Phase 2 Guidance Layer is the **explanatory bridge**
between numerical analysis and narrative presentation.

It ensures that tips remain:
- interpretable
- consistent
- explainable