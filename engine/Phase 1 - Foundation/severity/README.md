# Phase 1 Severity Layer – README

## Purpose

This directory contains the **baseline severity inference subsystem**
used by Phase for:used by Phase 1 of the Tip Generation System.
- mapping detected elements to severity labels
- computing baseline difficulty scores
- providing the foundational difficulty signal for tips generation

This layer implements **Stage 5.1 (baseline)** of the Phase 1 workflow.

---

## Contents

### `proseka_severity_rules.py`
Defines the canonical severity ruleset.

Responsibilities:
- define severity labels (e.g. light, moderate, dense)
- encode rule‑based thresholds
- provide severity comparison helpers

Characteristics:
- rule‑driven
- deterministic
- taxonomy‑aligned

This file defines the **authoritative Phase 1 severity semantics**.

---

### `severity_detector.py`
Implements the baseline severity inference engine.

Responsibilities:
- evaluate rules against detected elements
- compute baseline scores
- emit analysed element attributes

Characteristics:
- pure inference
- no calibration
- no personalization

---

## Guarantees

- Severity inference is deterministic
- The same input yields the same severity labels and scores
- No learning, blending, or adaptive behavior occurs here

---

## Relationship to Later Phases

- **Phase 2 (Track A)** augments this layer by:
  - applying midpoint overrides
  - blending SectionMetrics‑derived features
  - optionally calibrating scores

- **Phase 3** may wrap outputs for ingestion
- **Phase 4+** must not modify baseline severity semantics

Phase 1 severity exists to define the **baseline truth**,
not the final personalized difficulty.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Non‑functional comments
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Rule changes
- Threshold tuning
- Score scaling changes
- Calibration logic
- New dependencies

Any evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This layer defines the **baseline difficulty interpretation**
of gameplay elements.

It is intentionally conservative and locked to ensure:
- reproducibility
- historical consistency
- safe downstream enhancement

