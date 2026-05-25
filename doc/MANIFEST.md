## Manifest (Wave 1–9 Source Documents)

This repository is derived from the following **authoritative wave artifacts**.

Each wave represents a completed or design‑locked milestone.

Note: Phase 4, Phase 4.5, and Phase 7 CI governance layers are design-locked and enforced separately.

### Purpose of This Manifest

This manifest defines the **authoritative origin of the system**.

It ensures:

- every architectural decision can be traced to a specific wave artifact
- semantic phases are grounded in immutable source documents
- no undocumented logic is introduced outside defined waves
- the system remains auditable and historically consistent

This file establishes **provenance integrity** across all phases.

---

### Wave 1 — Phase 1 Baseline
- PHASE_1_ARCHITECTURE.md
- PHASE_1_SPEC.md
- PHASE_1_TIPS_PRODUCTION_GUIDE.txt

---

### Wave 2 — Phase 2 Enhancement (Tracks A–D)
- PHASE_2_ARCHITECTURE.md
- PHASE_2_SPEC.md
- PHASE_2_TIPS_PRODUCTION_GUIDE_v2.md

---

### Wave 3 — Phase 3 Unified Ingestion Manager
- UMI_SPEC.md
- UMI_ARCHITECTURE.md
- `rhythm_ingestion/orchestrator.py` (core entrypoint)

---

### Wave 4 — Phase 4 Personalization
- PHASE_4_SPEC.md
- PHASE_4_ARCHITECTURE.md
- PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md

---

### Wave 5 — Phase 4.5 Localization
- PHASE_4.5_SPEC.md
- PHASE_4.5_ARCHITECTURE.md
- `translations/README.md`

---

### Wave 6 — Phase 5 Productionization
- PHASE_5_SPEC.md
- PHASE_5_ARCHITECTURE.md

---

### Wave 7 — Phase 6 Platform Hardening
- PHASE_6_SPEC.md
- PHASE_6_ARCHITECTURE.md
- Phase 6 README

---

### Wave 8 — Phase 7 Games Recommendations
- PHASE_7_SPEC.md
- PHASE_7_ARCHITECTURE.md
- Phase 7 README

---

### Wave 9 — Integration & Control‑Plane Anchors
- `rhythm_ingestion/orchestrator_ext/bridge.py`
- `rhythm_ingestion/orchestrator_ext/config.py`
- `rhythm_ingestion/orchestrator_ext/feature_flags.py`
- `rhythm_ingestion/orchestrator_ext/types.py`
- `rhythm_ingestion/orchestrator_ext/reason_codes.py`
- `rhythm_ingestion/orchestrator_ext/README.md`
- `games.json`

### Interpretation Rules

- Later waves may extend earlier ones, but MUST NOT contradict sealed semantics
- Missing modules MUST NOT be invented outside these artifacts
- Runtime behavior must always align with a corresponding wave definition

If a behavior cannot be traced to a wave artifact, it is **invalid by design**.
``