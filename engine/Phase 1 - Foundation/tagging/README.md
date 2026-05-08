# Phase 1 Tagging Layer – README

## Purpose

This directory contains the **completed tagging subsystem**
used by Phase 1 of the Tip Generation System.

It is responsible for:
- interpreting pattern‑signal tags
- applying rule‑based logic to infer gameplay elements
- aligning internal identifiers with official PJsekai element labels

This layer implements **Stage 4.1–4.3** of the Phase 1 pipeline.

---

## Contents

### `element_rules.py`
Defines the rule registry that maps:
- pattern‑signal tags
- metric thresholds
to internal gameplay element identifiers.

Characteristics:
- Rule‑based
- Deterministic
- Taxonomy‑dependent

This file represents the **authoritative rule set** for Phase 1.

---

### `proseka_element_alignment.py`
Handles alignment between:
- internal element identifiers
- official PJsekai element names
- presentation‑level labels

This module ensures:
- stable naming
- consistent downstream references
- compatibility with guidance and narrative layers

---

## Guarantees

- Tag interpretation is deterministic
- Rule evaluation order is stable
- Element naming semantics are fixed

---

## Relationship to Later Phases

- **Phase 2** re‑uses tag semantics but may enhance scoring and selection
- **Phase 3** may wrap this logic via adapters
- **Phase 4+** must not modify or reinterpret Phase 1 tag rules directly

All extensions must occur **outside** this directory.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Non‑functional comments
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Rule changes
- Tag definition changes
- Threshold tuning
- New dependencies

Any required evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This layer defines the **semantic bridge** between
visual pattern detection and gameplay understanding.

It is locked to preserve:
- consistency
- reproducibility
- downstream stability