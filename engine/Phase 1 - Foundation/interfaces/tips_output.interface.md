# tips_output.interface.md

## Purpose
Defines the final tips text output produced by Phase 1.

This is a **presentation-layer artifact**.

## Shape
- `paragraph_1` (string)
- `paragraph_2` (string)

## Semantics
- Text is human-readable.
- Paragraph structure is stable but phrasing may vary.

## Guarantees
- Output is safe to render directly in UI.
- No markup or executable content.

## Notes
- Localization and personalization occur in later phases.
