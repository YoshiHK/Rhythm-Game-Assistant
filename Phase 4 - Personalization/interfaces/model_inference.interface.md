## PHASE_4_MODEL_INFERENCE_INTERFACE.md
### Phase 4 — Model Inference Interface

**Status:** Draft (Implementation‑ready)

### 1. Purpose
Provide **bounded, presentation‑only suggestions** to the
Personalization Decision Interface.

This layer has **no authority**.

### 2. Inputs (Read‑Only)
- elements_skeleton
- canonical_payload
- player_context (optional)

### 3. Allowed Outputs (Advisory Only)
- ranking weights
- element ordering suggestions
- narrative template ID
- variant ID

### 4. Prohibited Outputs
Models MUST NOT:
- create or delete elements
- modify severity, scores, guidance
- generate free‑form text
- see raw chart data

### 5. Safety Rules
- All outputs must pass rule validation
- Invalid output → dropped silently
- Deterministic fallback always available

### 6. Determinism
- deterministic mode bypasses models
- debug mode may run models but MUST NOT apply output

This interface is optional and safe to disable.