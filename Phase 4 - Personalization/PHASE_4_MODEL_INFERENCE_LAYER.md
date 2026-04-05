
# PHASE_4_MODEL_INFERENCE_LAYER.md
## Phase 4 — Model Inference Layer (Ranking + Template Selector + Bandit Policy)

**Status:** Draft (Implementation-ready)

**Depends on:**
- PHASE_4_SPEC.md
- PHASE_4_ARCHITECTURE.md
- PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md
- PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md

**Hard Constraints:**
- Offline-trained models only; no online learning.
- Model outputs are advisory; rules and safety validation always apply.
- Models MUST NOT modify elements, severity, scores, guidance, or create free-form text.

---

## 1. Purpose

The Model Inference Layer provides **optional, bounded recommendations** to Phase 4:

1) **Ranking Model** → emits scalar reweighting factors and/or ordering suggestions
2) **Template Selector** → selects a narrative template ID
3) **Bandit Policy** → chooses among safe variants for constrained exploration

All outputs are **presentation-only** and must be validated before use.

---

## 2. Inputs (Read-only)

- `elements_skeleton` (selected elements from Phase 2)
- `canonical_payload` / `canonical_row` (Phase 3 outputs)
- `player_context` (optional)
- `engine_mode` and gate outcomes

No raw chart data is required.

---

## 3. Outputs (Advisory)

The model layer may emit:

```json
{
  "ranking_weights": {"element_id": 1.1},
  "element_ordering": ["element_id_1", "element_id_2"],
  "narrative_template_id": "template_expert_v3_A",
  "variant_id": "variant_B",
  "bandit": {
    "policy": "epsilon_greedy",
    "epsilon": 0.1
  }
}
```

These outputs are consumed by the Safe Adjustment Interface and Narrative Module v3.

---

## 4. Safety Rules

- Ranking weights may only affect ordering/emphasis (presentation)
- Template IDs must map to approved template registry
- Bandit variants must be constrained to safe variants
- Any invalid output MUST be dropped (fallback to deterministic)

---

## 5. Determinism & Debug

- Deterministic mode bypasses model inference.
- Debug mode may run inference but must not apply it, only record provenance.

---

**End of PHASE_4_MODEL_INFERENCE_LAYER.md**
