## Limitations & Non‑Goals (Phases 1–7)

This system is intentionally constrained to preserve:
**trust, determinism, auditability, and long‑term maintainability**.

These limitations are **by design**, not gaps.

### Why These Limitations Exist

These constraints enforce the following system-level guarantees:

- deterministic outputs (same input → same result)
- strict phase boundary isolation (no cross-layer semantic leakage)
- auditability and reproducibility of all recommendations
- long-term evolvability without breaking existing behavior

These are not implementation constraints, but **platform invariants**.
Violating them breaks the architectural contract of the system.

---

### Hard Prohibitions (Authoritative)

#### Phase 3 — Unified Ingestion Manager / Orchestrator Extension
- MUST NOT contain gameplay analysis logic.
- MUST NOT re‑implement or alter Phase 1–2 algorithms.
- MUST NOT decide severity, selection, or narrative meaning.
- MUST NOT embed game‑specific heuristics.
- MUST NOT perform personalization.
- MUST NOT modify canonical payload semantics.
- MUST NOT bypass Phase 6 runtime enforcement.

---

#### Phase 4 — Personalization
- MUST NOT modify detected elements, severity labels, scores, training items, or section coverage.
- MUST NOT create, delete, or rewrite elements.
- MUST NOT generate free‑form text (narrative is template‑bound).
- MUST NOT override Phase 1–2 semantic decisions.

---

#### Phase 4.5 — Localization
- MUST NOT change gameplay advice meaning, intent, ordering, or safety emphasis.
- MUST NOT summarize or paraphrase gameplay semantics.
- MUST NOT perform runtime free‑form translation.
- MUST NOT apply context‑less translation.

---

#### Phase 5 — Learning / Productionization
- Offline learning only: no live or online learning.
- MUST NOT alter Phase 4 outputs at runtime.
- MUST NOT modify element selection, severity, scoring, or guidance.
- MUST NOT inject learning behavior into runtime paths.

---

#### Phase 6 — Platform Hardening
- MUST NOT reinterpret gameplay advice.
- MUST NOT alter personalization or localization outputs.
- MUST NOT introduce new learning logic.
- MUST NOT override Phase 5 contracts.
- MUST NOT bypass orchestrator or Phase 7 boundaries.

---

#### Phase 7 — Games Recommendations
- MUST NOT alter song or chart recommendations.
- MUST NOT change tips meaning, severity, or narrative logic.
- MUST NOT redefine difficulty labels or taxonomies.
- MUST NOT inject logic into Phases 1–6.
- MUST NOT bypass Phase 6 enforcement or observability.

---

### Non‑Goals

- Phase 7 does **not** redesign the UI; it adds a **parallel discovery channel**.
- Phase 6 does **not** add product intelligence.
- Phase 5 does **not** own UI or runtime rendering.