# Phase 1 Guidance Layer – README

## Purpose

This directory contains the **completed guidance and narrative subsystem**
used by Phase 1 of the Tip Generation System.

It is responsible for:
- transforming analysed elements into human‑readable guidance
- assembling narrative tips text
- enforcing basic phrasing and structure constraints

This layer implements **Stage 5.3 and Stage 6** of the Phase 1 workflow.

---

## Contents

### `proseka_guidance_engine.py`
The canonical Phase 1 guidance engine.

Responsibilities:
- convert analysed elements into guidance components
- populate difficulty causes and focus areas
- provide structured input for narrative rendering

Characteristics:
- rule‑based
- deterministic
- non‑personalized

---

### `narrative_module.py`
The Phase 1 narrative renderer.

Responsibilities:
- assemble tips text from guidance components
- enforce paragraph structure
- generate stable, readable output

Characteristics:
- template‑driven
- deterministic
- language‑fixed (no i18n)

---

## Guarantees

- Guidance generation is deterministic
- Narrative output structure is stable
- No personalization, localization, or model inference occurs here

---

## Relationship to Later Phases

- **Phase 2 (Track C / Track D)**:
  - replaces guidance filling with `guidance_engine_v2`
  - replaces narrative rendering with `narrative_module_v2`

- **Phase 3**:
  - may wrap or route around Phase 1 guidance for compatibility

- **Phase 4+**:
  - introduces Narrative v3, personalization, and localization
  - must not modify Phase 1 guidance logic

Phase 1 guidance exists as a **historical baseline**, not a future optimization target.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Non‑functional comments
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Guidance logic changes
- Narrative phrasing changes
- Template updates
- Localization hooks
- New dependencies

Any evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This layer defines the **baseline narrative voice**
of the Tip Generation System.

It is locked to preserve:
- reproducibility
- historical consistency
- downstream safety
