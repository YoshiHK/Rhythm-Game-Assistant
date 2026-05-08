# chart_input.interface.md

## Purpose
Defines the canonical input shape for Phase 1 tip generation.

This interface represents a single chart ingestion unit.
It is considered **locked** and MUST NOT be changed by downstream phases.

## Required Fields
- `chart_id` (string | null)
- `song_id` (string | null)
- `difficulty` (string)
- `payload` (any)

## Semantics
- `payload` may contain:
  - visual data
  - detected tags
  - pre-analysed structures (optional)
- Phase 1 does not assume any structure beyond presence.

## Guarantees
- Input is treated as immutable.
- Missing fields must not crash the pipeline.

## Notes
- Validation is best-effort only.
- Strict schema enforcement begins in Phase 3.