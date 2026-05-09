# ADVANCED_SPEC_INDEX_v2.md
Project: **Project SEKAI Gameplay Tips Generation**
Phase: **Phase 2 – Track A–D (Non‑Breaking Extensions)**

This index extends `SPEC_INDEX.md` with Phase 2 artifacts. It clarifies which files are:
- **Authoritative** (specs/schemas): treated as inputs; do not modify at runtime
- **Tuning configs**: runtime inputs; safe to swap versions
- **Deterministic engine code**: must conform to specs
- **Patches**: version-control migration aids only

---

## 1) Authoritative Specs (unchanged)
- `proseka_batch_pipeline.json` (workflow spec)
- `proseka_internal_analysis_schema_v1.4.0.json` (official elements, selection baselines)
- `proseka_tips_generation_spec_v1.0.1_advisory.json` (tone, scripts, word limits)
- `pattern_signals_export_v2.json` (taxonomy)
- `tips_training_mapping.json` (element→tags→training)

## 2) Canonical Schemas (unchanged)
- `proseka_summary_blocks_canonical.json` (per-chart summary)
- `proseka_batch_summary_schema_v1.1.0.json` (batch summary)

---

## 3) Phase 2 Tuning Configs (new)

### 3.1 Track A – score calibration config
- `score_calibration_config_v0.2.1.json`
  - severity midpoint override
  - feature_model toggle + weights + blend

### 3.2 Track C/D – guidance & narrative tuning
- `track_cd_config.json`
  - Track C category priorities, cause variants, cue labels
  - Track D swap triggers, word budgets, auto-switch thresholds
  Note: Track C/D tuning configs are not consumed by Phase 2 runtime;
  they are applied in later personalization phases.

---

## 4) Phase 2 Engine Extensions (new)

### 4.1 Track A – calibrated wrapper
- `proseka_score_calibration.py`
  - drop-in wrapper around `(5.1) severity_detector.infer_severities_for_chart`
  - applies midpoint override and optional feature model blending

### 4.2 Track B – selector v2
- `selector_v2.py`
  - dominance-aware ranking
  - canonical-family diversity constraint
  - tie bucketization + coverage preference

### 4.3 Track C – guidance engine v2
- `guidance_engine_v2.py`
  - dominant category selection
  - tied-category combined cause phrasing
  - mixed-cue breakdown phrasing (such_as / paren)

### 4.4 Track D – narrative module v2
- `narrative_module_v2.py`
  - spec-template rendering
  - swap logic for readability
  - strict word budget enforcement
  - auto-switch mixed-cue breakdown near hard max (scaled per difficulty)

---

## 5) Orchestration / Runtime Wiring

Phase 2 recommended call graph (logical):
1) base detection + mapping
2) Track A wrapper produces calibrated `elements_skeleton`
3) Track B selects elements
4) Track C fills guidance
5) Track D renders narrative
6) summaries as usual

(Adapters/runner wiring may vary by checkout; treat this index as the target integration topology.)

---

## 6) Patch Artifacts (migration aids)
Patch files are not runtime artifacts. See `PATCHES_README_v2.md` for the Phase 2 patch set.

END
