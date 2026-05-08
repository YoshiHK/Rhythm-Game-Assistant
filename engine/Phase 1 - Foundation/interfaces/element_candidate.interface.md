# element_candidate.interface.md

## Purpose
Defines the inferred gameplay element candidates derived from detected tags.

This interface represents **pre-scoring**, **pre-selection** candidates.

## Shape
Each candidate includes:
- `element_name` (string)
- `matched_tags` (list[string])
- `training_items` (list[string])
- `tag_hit_count` (integer)

## Semantics
- Candidates are unordered.
- Candidates may include low-confidence or zero-hit entries.
- No severity or score is assigned at this stage.

## Guarantees
- Candidates are additive.
- No candidate implies final selection.

## Notes
- Selection and scoring occur in Phase 2 (Track A / B).