# analysed_element.interface.md

## Purpose

Defines the **analysed element** contract produced in Phase 2
(Stage guidance filling, and summaries.(Stage 5.1).

---

## Shape

Each analysed element includes:

- `name` (string)
- `severity` (string)
- `score` (float, 0.0–1.0)
- `section_coverage` (float, 0.0–1.0)
- `is_chart_defining` (bool)
- `guidance` (object, may be partially filled)

---

## Semantics

- Severity labels are preserved by default.
- Score may be blended with SectionMetrics-derived features.
- Coverage represents chart-wide influence.

---

## Guarantees

- Analysed elements are deterministic.
- No personalization or locale-specific logic is applied.

---

## Notes

- Phase 2 Track A augments Phase 1 baseline inference.


This is the primary analytical unit used for selection,
