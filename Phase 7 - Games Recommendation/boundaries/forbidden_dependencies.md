
# Phase 7 — Forbidden Dependencies

This document defines **imports, behaviors, and interactions**
that Phase 7 is explicitly forbidden from performing.

Violations constitute architectural errors.

---

## 1. Forbidden Imports

Phase 7 MUST NOT import or depend on any of the following.

### 1.1 Phase 1–2 (Foundation & Enhancement)

- Chart analysis pipelines
- Visual detection or pattern extraction logic
- Tips generation internals
- Element inference, severity, or selection logic

---

### 1.2 Phase 3 (Unified Ingestion Manager)

- Orchestrator runtime logic
- Adapters or validators
- Raw ingestion payloads
- Pipeline execution modules

Phase 3 outputs remain authoritative and opaque to Phase 7.

---

### 1.3 Phase 4 / 4.5 (Personalization & Localization)

- Personalization decision engines
- Safe‑adjustment application logic
- Narrative mutation logic
- Localization internals beyond template consumption

Phase 7 may consume localized outputs, but must not participate in localization logic.

---

### 1.4 Phase 5 (Learning & Productionization)

- Learning pipelines
- Retraining or promotion logic
- Curator tooling or gold labels

Phase 7 may emit feedback signals, but never consume learning internals.

---

### 1.5 Phase 6 (Platform Hardening)

- Enforcement logic
- Guard decision internals
- Lifecycle or rollout controllers

Phase 6 remains the sole operational gatekeeper.

---

## 2. Forbidden Behaviors

Phase 7 MUST NOT:

- mutate upstream outputs;
- override or suppress song‑level recommendations;
- reorder or reinterpret tips;
- redefine difficulty labels or taxonomies;
- inject logic into Phases 1–6;
- bypass Phase 6 routing, guards, or observability;
- introduce runtime contract versioning or schema switching.

---

## 3. Architectural Invariant

Phase 7 is **advisory and additive only**.

If Phase 7 is disabled, removed, or fails:
- all upstream phases MUST continue to function unchanged.  
