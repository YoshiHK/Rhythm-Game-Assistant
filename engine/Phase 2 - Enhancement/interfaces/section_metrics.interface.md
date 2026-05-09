# section_metrics.interface.md

## Purpose

Defines the contract for **SectionMetrics** produced and consumed in Phase 2
(Stage 2–4.1 and Stage 5.1).

SectionMetrics represent aggregated difficulty and structural signals
over fixed chart segments.

---

## Shape (Per Section)

Each SectionMetrics object includes (non-exhaustive):

- `section_index` (int)
- `note_density` (float)
- `rest_ratio` (float)
- `hold_coverage` (float)
- `notes_during_hold_ratio` (float)
- `overlap_ratio` (float)
- `bpm_delta_ratio` (float, optional)
- `chart_stop_count` (int, optional)
- `fake_end_flag` (bool, optional)

---

## Semantics

- Sections are ordered by chart progression.
- Metrics are normalized and bounded.
- Missing optional metrics MUST NOT break downstream logic.

---

## Guarantees

- SectionMetrics are deterministic.
- Values are bounded to safe numeric ranges.
- No personalization or player context is applied.

---

## Notes

- Phase 1 produces baseline SectionMetrics.
- Phase 2 may extend metrics additively but must preserve existing fields.