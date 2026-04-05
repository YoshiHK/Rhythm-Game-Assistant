
# PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md
## Phase 4 — Personalization Decision Interface

**Status:** Draft (Ready for Lock Review)

**Depends on:**
- PHASE_4_SPEC.md
- PHASE_4_ARCHITECTURE.md
- UMI_INTERFACES.md

**Invariant:** Do not modify anything in Completed Phases.

---

## 1. Purpose

The Phase‑4 Personalization Decision Interface defines the **single, authoritative decision point** for all personalization behavior.

It answers:
> “Should personalization be applied, and if so, what non‑destructive adjustments are permitted?”

No other Phase‑4 component may bypass or duplicate this logic.

---

## 2. Position in System

```
Phase 3 Outputs
   ↓
[ Personalization Decision Interface ]
   ↓
Adjustment Directives
   ↓
Narrative Module v3
```

This interface consumes Phase‑3 outputs and emits **presentation‑only directives**.

---

## 3. Input Contract

### 3.1 Required Inputs (Read‑Only)

```json
{
  "canonical_payload": { ... },
  "canonical_rows": [ ... ],
  "elements_skeleton": [ ... ],
  "base_provenance": { ... }
}
```

These inputs MUST NOT be mutated.

---

### 3.2 Optional Inputs

```json
{
  "player_id": "opaque-id",
  "engine_mode": "deterministic | personalized | debug",
  "locale": "en-US | ja-JP | ...",
  "client_flags": { ... }
}
```

Absence of optional inputs MUST NOT prevent execution.

---

## 4. Engine Mode Handling

### 4.1 Deterministic Mode

- Personalization disabled
- Interface emits no adjustments
- Output equals Phase‑2 narrative

---

### 4.2 Personalized Mode

- Gate checks evaluated
- Adjustment directives MAY be produced
- Deterministic fallback guaranteed

---

### 4.3 Debug / Audit Mode

- Deterministic output forced
- Full decision trace emitted

---

## 5. Deterministic Decision Gates

Personalization is allowed only if all required gates pass.

### Required Gates

- Feature flag enabled
- Player opt‑in confirmed
- Required context available
- No safety constraint violated

---

### Gate Outcome Contract

```json
{
  "personalization_allowed": true | false,
  "gate_fail_reasons": ["OPT_OUT", "FLAG_DISABLED"]
}
```

If `false`, no personalization may be applied.

---

## 6. Adjustment Directive Contract

When personalization is allowed, the interface MAY emit adjustment directives.

### 6.1 Directive Shape

```json
{
  "element_ordering": ["element_id_1", "element_id_2"],
  "ranking_weights": {
    "element_id_1": 1.1,
    "element_id_2": 0.9
  },
  "narrative_template_id": "template_expert_v3_A",
  "variant_id": "variant_B"
}
```

---

### 6.2 Hard Constraints

Directives MAY:
- reorder existing elements
- apply scalar ranking weights
- select templates or variants

Directives MUST NOT:
- create or delete elements
- modify severity, scores, or guidance
- alter analytical meaning

---

## 7. Model Usage Boundary

Models MAY be consulted to suggest directives, but:

- outputs are advisory only
- final decisions are rule‑validated
- all model usage must be logged

Models MUST NOT:
- see raw chart data
- generate free‑form text
- modify semantic fields

---

## 8. Provenance Contract

Every invocation MUST emit provenance.

### Required Fields

```json
{
  "engine_mode": "personalized",
  "gate_results": { ... },
  "decision_source": "rule | model | hybrid",
  "model_id": "ranker_v2.1",
  "template_id": "template_expert_v3_A",
  "variant_reason": "exploration"
}
```

No provenance → invalid output.

---

## 9. Failure & Fallback Rules

If any error occurs:

- no exception propagates
- no partial personalization is applied
- deterministic output is returned
- failure reason is recorded

---

## 10. Contract Summary

This interface is:
✅ the sole personalization gate
✅ deterministic and auditable
✅ non‑destructive
✅ model‑optional
✅ safe by default

Any personalization outside this interface violates Phase‑4 contract.

---

**End of PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md**
