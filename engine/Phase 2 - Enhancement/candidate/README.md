# Phase 2 Candidate Layer – README

## Purpose

This directory implements the **Phase 2 Candidate Layer**
corresponding to **Stage 4.2: Tag → Element sole responsibility is to convert **detected pattern-signal tags**corresponding to **Stage 4.2: Tag → Element Candidates**.
into a **normalized list of element candidates** using
declarative training-mapping artifacts.

This layer is intentionally narrow and deterministic.

---

## Responsibilities

The Phase 2 Candidate Layer is responsible for:

1. Normalizing detected pattern tags
2. Resolving the applicable tips training mapping artifact
3. Inferring element candidates with:
   - matched_tags
   - training_items
   - tag_hit_count

This layer does **not** perform:
- severity inference
- scoring or coverage calculation
- element selection
- guidance filling
- narrative rendering

---

## Files

### `tag_normalization.py`
Provides deterministic normalization for detected tags.

Responsibilities:
- strip whitespace
- lowercase for matching stability
- drop empty or invalid values
- preserve input order

This module does **not**:
- define taxonomy
- introduce new tags
- reinterpret Phase 1 semantics

---

### `mapping_resolver.py`
Resolves and loads the **tips training mapping** artifact.

Responsibilities:
- select which mapping file to load
- load mapping data in a safe, best-effort way
- return an empty mapping on failure

This module does **not**:
- implement mapping semantics
- apply per-game or advanced search logic
- modify mapping contents

---

### `element_inference.py`
Infers element candidates from:
- normalized detected tags
- resolved training mapping

Responsibilities:
- compute matched_tags via set intersection
- compute tag_hit_count
- emit Phase 2–canonical candidate objects

Output objects must conform to:
- `element_candidate.interface.md`
- `element_candidate.schema.json`

---

## Determinism Guarantees

The Candidate Layer guarantees that:

- The same detected tags and mapping produce the same candidates
- Candidate ordering is stable for the same inputs
- No randomness or external state is used

---

## Relationship to Other Phases

### Phase 1
- Phase 1 may produce detected tags using visual heuristics
- Phase 1 mapping helpers remain untouched
- Phase 2 does not modify Phase 1 behavior

### Phase 2 (Downstream)
- **Stage 5.1 (Severity / Track A)** consumes element candidates
- **Stage 5.2 (Selection / Track B)** filters and ranks analysed elements

### Phase 3+
- Phase 3 Orchestrator may call this layer directly
- Phase 4 Personalization must not mutate candidate semantics

---

## Change Policy

✅ Allowed:
- Additive metadata fields (with schema updates)
- Improved normalization logic (non-breaking)
- Additional mapping resolution strategies (versioned)

❌ Not Allowed:
- Introducing scoring or severity logic
- Filtering candidates beyond min_tag_hits
- Embedding selection or ranking rules
- Adding personalization or player context

Any breaking change requires:
- explicit interface + schema versioning, or
- a parallel candidate implementation

---

## Summary

The Phase 2 Candidate Layer defines the **first explicit enhancement boundary**
after Phase 1 detection.

It converts raw signals into **interpretable, auditable candidates**
while remaining:
- deterministic
- schema-aligned
- safe for downstream evolution

