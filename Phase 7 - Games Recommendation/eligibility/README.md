# Phase 7 — Eligibility Layer

This directory defines **explicit eligibility exclusions**
for **Phase 7 – Games Recommendations**.

Eligibility rules here are **governance-facing only**.

---

## Purpose

The eligibility layer exists to answer one question:

> **Which games are intentionally excluded from Phase 7 recommendations, and why?**

These exclusions are:
- explicit,
- documented,
- auditable,
- and non-silent.

---

## Design Principles

- **CI-only**
  - Runtime code MUST NOT import this layer.
  - Violations are architectural errors.

- **Explicit over implicit**
  - If a game is excluded, the reason must be written down.
  - Silent suppression is forbidden.

- **Non-semantic**
  - Eligibility rules do not reinterpret difficulty, skill, or ranking logic.
  - They exist outside recommendation semantics.

---

## Relationship to Other Layers

- **Registry Layer**
  - Defines which games exist and their status.
- **Eligibility Layer**
  - Defines which of those games are temporarily or structurally excluded.
- **Routing / Ranking**
  - MUST assume eligibility has already been validated by CI.

---

## Examples of Legitimate Exclusions

- Game enabled in registry but missing difficulty profiles
- Game pending QA or partner approval
- Game with incomplete catalog / localization coverage
- Game temporarily disabled for product or legal reasons

Eligibility exclusions are expected to change over time,
but **always via explicit edits**, never implicit logic.
