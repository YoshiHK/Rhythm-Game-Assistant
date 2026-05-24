# Schema Layer (Song Recommendation)

## Purpose

This directory defines **contract schemas** for the Song Recommendation API
and internal coordination payloads.

Schemas serve as:
- Validation boundaries
- Cross‑phase contracts
- CI‑enforced safety rails

They describe **structure only**, not behavior.

## Non‑Responsibilities

Schemas MUST NOT:
- Encode gameplay semantics
- Enumerate game‑specific difficulty names
- Contain ranking or recommendation logic
- Perform validation beyond structural constraints

## Enforcement

All schemas in this directory are:
- JSON Schema based
- Validated in CI
- Required to remain backward compatible unless explicitly versioned

## Notes

Game‑specific semantics (e.g. difficulty ordering) are resolved via
`game_capability` fixtures, not schemas.