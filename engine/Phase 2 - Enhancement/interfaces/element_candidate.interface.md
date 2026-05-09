# element_candidate.interface.md

## Purpose

Defines the **element candidate** contract used in Phase 2
(Stage 4.2).

Element candidates represent potential gameplay elements inferred
from detected pattern tags.

---

## Shape

Each element candidate includes:

- `element_name` (string, official JP label)
- `matched_tags` (list[string])
- `training_items` (list[string])
- `tag_hit_count` (int)

---

## Semantics

- Candidates are unordered.
- Candidates are **pre-scoring** and **pre-selection**.
- Presence does not imply final inclusion in tips.

---

## Guarantees

- Candidates are additive.
- No severity, score, or coverage is attached at this stage.

---

## Notes

- This interface mirrors Phase 1 output but is treated as a **hard contract** in Phase 2.