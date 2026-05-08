# Phase 1 Visual Layer – README

## Purpose

This directory contains the **completed visual detection subsystem**
used by Phase 1 of the Tip Generation System.

It is responsible for:
- parsing chart visual data
- extracting note‑level events
- computing SectionMetrics
- emitting pattern‑signal tags

This layer implements **Stage 2–4.1** of the overall pipeline.

---

## Contents

### `chart_visual_detector_merged.py`
The canonical visual detector.

Responsibilities:
- Parse Proseka Trainer HTML / SVG exports
- Normalize visual events into NoteEvent
- Compute SectionMetrics
- Detect pattern‑signal tags aligned to the Phase 1 taxonomy

This file is **feature‑complete and locked**.

---

### `utils.py`
Utility helpers used by the visual and rule subsystems.

Characteristics:
- Pure helper functions
- No orchestration responsibility
- No side effects

---

## Guarantees

- Visual detection is deterministic
- SectionMetrics computation is stable
- Tag emission semantics are fixed

---

## Relationship to Later Phases

- **Phase 2** consumes SectionMetrics and tags for enhancement
- **Phase 3** may wrap this layer via adapters
- **Phase 4+** must not directly invoke or alter this code

All improvements must occur **outside** this directory.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Non‑functional annotations
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Logic changes
- Tag definition changes
- Metric computation changes
- Dependency changes

---

## Summary

This layer is the **visual ground truth** of the system.

It exists to be:
- Trusted
- Stable
- Untouched
