# Phase 7 — Catalog Layer

This directory defines the **presentation‑only catalog layer**
for **Phase 7 – Games Recommendations**.

The catalog layer provides **UI‑facing metadata** for games
(display names, icons, links, grouping),
without influencing recommendation logic.

---

## Purpose

The Catalog Layer answers one question only:

> **How should games be presented to users?**

It does NOT decide:
- which games are recommended,
- how games are ranked,
- or whether a game is eligible.

---

## Design Principles

- **Presentation‑only**
  - Catalog data is used for display, search, and grouping.
  - It must not influence ranking, routing, or eligibility.

- **Downstream‑only**
  - Consumes registry outputs (`games.json`).
  - Never mutates or reinterprets registry semantics.

- **Optional and additive**
  - `catalog.json` is optional.
  - Absence of catalog metadata must never break Phase 7.

- **Localization‑aware, not localization‑owning**
  - Locale resolution and fallback belong to Phase 4.5.
  - The catalog only consumes resolved or raw display metadata.

---

## What Lives Here

✅ Core:
- `catalog_loader.py`
  - Loads and normalizes `catalog.json`
  - Safe, optional, and deterministic
- `GameCatalog` (external class)
  - Query, search, grouping, presentation helpers

✅ Supporting:
- `catalog.py`
  - Demonstration / playground usage only

⚠️ Experimental / Not in runtime path:
- `catalog_merge.py`
  - Prototype for registry + catalog merging
  - NOT imported by routing or APIs
  - Reserved for future Phase 4.5 or CI tooling

---

## What Does NOT Belong Here

🚫 Not allowed:
- Eligibility logic
- Ranking or scoring
- Personalization decisions
- Locale normalization rules
- Phase 6 guards or lifecycle logic

These responsibilities belong to other phases by design.

---

## Relationship to Other Layers

- **Registry Layer**
  - Defines game identity and status (authoritative)
- **Catalog Layer**
  - Adds optional presentation metadata
- **Routing / Ranking**
  - Must treat catalog as read‑only decoration
- **Phase 4.5**
  - Owns locale normalization and fallback
- **Phase 6**
  - Owns API exposure and platform wiring

---

## Architectural Invariant

If the Catalog Layer is removed or empty:
- Phase 7 recommendations must still function correctly.
- Only presentation quality is affected.

This layer exists to improve UX — never to alter semantics.
