# detected_tags.interface.md

## Purpose
Defines the contract for pattern-signal tags emitted during Phase 1.

These tags are the **primary signal** used to infer gameplay elements.

## Shape
- List of strings:
  - `["tap_stream", "wide_jump", "hold_density", ...]`

## Semantics
- Tags are **unordered**.
- Duplicates are allowed but SHOULD be deduplicated downstream.
- Tag meaning is defined by the taxonomy active at generation time.

## Guarantees
- Tags represent detectable structure only.
- Absence of tags indicates non-approachable charts.

## Notes
- Tag taxonomy is not enforced at this phase.
- Normalization occurs in Phase 2+.