# Phase 7 — Registry Layer

This directory defines the **authoritative, read-only game registry**
used by **Phase 7 – Games Recommendations**.

The registry answers one question only:

> **Which games are eligible to appear in Phase 7 recommendations?**

---

## Design Principles

- **Downstream-only**
  - Phase 7 consumes registry metadata.
  - Phase 7 never mutates or redefines it.

- **Read-only adapter**
  - The registry reflects an upstream source of truth
    (e.g. `games.json` used by ingestion).
  - Phase 7 does not introduce new registry semantics.

- **Deterministic**
  - Given the same registry input, outputs are stable.
  - No runtime inference or experimentation occurs here.

---

## What This Layer Is NOT

The registry layer is NOT:

- a feature flag system
- a rollout controller
- a learning or experimentation mechanism
- a catalog or localization layer

Eligibility decisions beyond registry status belong to:
- CI checks (Phase 7 eligibility policy)
- Phase 5 learning
- Phase 6 lifecycle management

---

## Relationship to Other Layers

- **Phase 3** remains the source of ingestion truth.
- **Phase 6** remains the operational gatekeeper.
- **Phase 7** uses the registry for discovery eligibility only.

If this registry is removed or empty, Phase 7 produces no recommendations,
but all upstream phases continue to function unchanged.