## PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md
### Phase 4 — Personalization Decision Interface

**Status:** Draft (Lock‑ready)  
**Invariant:** Completed Phases (1–3) MUST NOT be modified.

### 1. Authority
This interface is the **sole authority** that determines:
- whether personalization is allowed
- which presentation‑only adjustments MAY be applied

No other Phase‑4 component may introduce personalization behavior.

### 2. Inputs (Read‑Only)
- canonical_payload (Phase 3)
- canonical_rows (Phase 3)
- elements_skeleton (Phase 2 output)
- base_provenance

Optional:
- player_context
- engine_mode (deterministic | personalized | debug)
- client_flags

### 3. Decision Gates (Deterministic)
Personalization is allowed **only if all gates pass**:
- feature flag enabled
- player opt‑in
- required context present
- no safety constraint violated

If any gate fails → personalization_disabled.

### 4. Output: Adjustment Directives (Advisory)
The interface MAY emit:
- element ordering
- scalar weights
- narrative template ID
- variant ID

It MUST NOT:
- modify elements
- change severity / scores
- generate text

### 5. Model Boundary
Models MAY be consulted to suggest directives, but:
- all outputs are advisory
- final decision is rule‑validated
- all model usage must be recorded

### 6. Failure Rules
Any error → deterministic fallback, no partial personalization.

### 7. Provenance
Every invocation MUST emit:
- decision_source (rule | model | hybrid)
- gate_results
- model_id (if used)

No provenance → invalid output.

**This interface is mandatory and non‑bypassable.**
``