# guidance.interface.md

## Purpose

Defines the **guidance fields** filled in Phase 2
(Stage 5.3 – Track C).

Guidance explains *why* an element contributes to difficulty
and *how* players should approach it.

---

## Shape

Guidance object includes:

- `difficulty_causes` (string)
- `chart_breakdown` (string)
- `primary_focus` (string)
- `secondary_focus` (string)
- `strategy` (string)
- `target_section` (string)

---

## Semantics

- Guidance is explanatory, not prescriptive.
- Phrasing is deterministic and spec-driven.
- No player variance language is included.

---

## Guarantees

- Guidance is safe for direct narrative rendering.
- No personalization or localization occurs here.

---

## Notes

- Narrative v3 (Phase 4) may reinterpret guidance, but must not mutate it.