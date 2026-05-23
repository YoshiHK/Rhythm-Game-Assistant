# Phase 7 — Explanation Layer

This directory implements the **explainability adapter** for
Phase 7 – Games Recommendations.

## Role
- Translate structured ranking signals into **presentation-safe explanations**.
- Explanations are **bounded**, **deterministic**, and **audit-friendly**.
- No free-form generation is required.

## Non-goals
- Not a ranking engine.
- Not a learning system.
- Not a runtime version selector.
- Not a template store (templates belong to Phase 4.5 localization).

## Inputs
- Phase 7 contract items (RecommendationItem)
- Structured rationale signals:
  - `rationale["reasons"]` (list[str])
  - `rationale["diagnostics"]` (dict with deltas)

## Outputs
- Enriches `item.rationale` with:
  - `rationale["explanation"]["summary"]`
  - `rationale["explanation"]["why"]` (bounded list)
  - `rationale["explanation"]["locale"]`

## i18n integration
The engine supports an optional resolver:
- `ctx["resolve_message"](code: str, locale: str, detail: Any) -> str`
If absent, deterministic fallback messages are used.