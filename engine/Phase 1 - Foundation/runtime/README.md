# Phase 1 Runtime – README

## Purpose

This directory contains the **locked execution spine** for Phase 1 (Foundation)
of the Tip Generation System.

The runtime here represents the **historical, production‑validated pipeline**
that executes the full Phase 1 workflow end‑to‑end.

> **Phase 1 runtime is COMPLETED and LOCKED.**

---

## Runtime Components

### `proseka_tips_pipeline_runner.py`
The canonical Phase 1 pipeline runner.

Responsibilities:
- Orchestrates the full Phase 1 workflow
- Invokes visual detection, tagging, element inference, guidance, narrative, and summary
- Enforces the batch pipeline spec (approachability gating)

This file defines the **authoritative execution order** of Phase 1.

---

### `alignment_helper.py`
Provides alignment and consistency helpers used during runtime execution.

Characteristics:
- Pure helper logic
- No orchestration responsibility
- No side effects

---

## Guarantees

The following guarantees apply to the Phase 1 runtime:

- Execution order is deterministic
- Input and output shapes are stable
- No personalization, localization, or model inference occurs here
- No downstream phase may alter runtime behavior

---

## Relationship to Later Phases

- **Phase 2** augments Phase 1 outputs but does NOT replace this runtime
- **Phase 3** may wrap this runtime via adapters or orchestrators
- **Phase 4+** must never call or modify Phase 1 runtime directly

All enhancements must occur **outside** this directory.

---

## Change Policy (Strict)

✅ Allowed:
- Documentation updates
- Non‑functional annotations
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Logic changes
- Execution order changes
- New dependencies
- Feature additions

Any required evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This runtime is the **bedrock** of the system.

It exists to be:
- Trusted
- Reproducible
- Untouched