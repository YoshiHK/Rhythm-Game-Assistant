# analysed_element.interface.md

## Purpose
Defines the analysed gameplay element after Phase 1 inference.

This represents the **core unit** used for tips generation.

## Shape
Each analysed element includes:
- `name` (string)
- `severity` (string)
- `score` (float 0.0–1.0)
- `section_coverage` (float 0.0–1.0)
- `is_chart_defining` (boolean)
- `guidance` (object)

## Semantics
- Severity labels are advisory.
- Score represents relative difficulty contribution.
- Coverage represents chart-wide influence.

## Guarantees
- Elements are self-contained.
- No personalization applied at this stage.

## Notes
- Severity calibration may override scores in Phase 2.