# Phase 1 Selection Layer – README

## Purpose

This directory contains the **completed element selection subsystem**
used by Phase 1 of the Tip Generation System.

It is responsible for:
- filtering inferred gameplay elements
- enforcing approachability rules
- selecting elements eligible for tips generation

This layer implements **Stage 5.2** of the Phase 1 workflow.

---

## Contents

### `proseka_element_selector.py`
The canonical Phase 1 element selector.

Responsibilities:
- apply approachability gating
- enforce minimum detectable structure
- select a fixed number of elements for tips generation

Characteristics:
- rule‑based
- deterministic
- difficulty‑aware

This file defines the **authoritative Phase 1 selection behavior**.

---

### `helper_functions.py`
Helper utilities used by the selection and tagging logic.

Responsibilities:
- tag → element mapping helpers
- rule lookup and alignment utilities
- shared glue logic across Phase 1 layers

Characteristics:
- pure helper functions
- no orchestration responsibility
- no side effects

---

## Guarantees

- Selection behavior is deterministic
- The same input produces the same selected elements
- No personalization or model inference occurs here

---

## Relationship to Later Phases

- **Phase 2** replaces selection logic via Track B (selector_v2)
- **Phase 3** may wrap Phase 1 selection for compatibility
- **Phase 4+** must not depend on Phase 1 selection semantics

Phase 1 selection exists to support the original foundation workflow,
not to serve as a long‑term optimization layer.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Non‑functional comments
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Selection rule changes
- Threshold tuning
- Difficulty logic changes
- New dependencies

Any evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This layer defines **which gameplay elements are eligible**
for tips generation in Phase 1.

It is locked to preserve:
- reproducibility
- historical behavior
- downstream stability