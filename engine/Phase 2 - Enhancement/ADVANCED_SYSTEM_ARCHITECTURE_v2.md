# ADVANCED_SYSTEM_ARCHITECTURE_v2.md
Project: **Project SEKAI Gameplay Tips Generation**
Phase: **Phase 2 – Track A–D Extensions (Non‑Breaking)**

This document extends the Phase 1 architecture (see `SYSTEM_ARCHITECTURE.md`) with Phase 2 upgrades:
- **Track A**: scoring calibration (severity midpoint overrides + chart‑level feature calibration)
- **Track B**: selection upgrades (dominance‑aware ranking, canonical-family diversity, tie‑break stability)
- **Track C**: guidance upgrades (taxonomy-aware dominant causes, tied-category causes, mixed‑cue breakdown phrasing)
- **Track D**: narrative upgrades (length control, readability swap, auto-switch breakdown variant near hard max)

The system remains **non‑breaking**: schema shapes and contracts do not change; only internal scoring/selection/narrative behaviors are improved.

---

## 1) Architecture at a Glance (Phase 2)

### 1.1 Layered Model (updated)

**A. Authoritative Specs & Schemas (contracts; unchanged)**
- Workflow/orchestration spec: `proseka_batch_pipeline.json`
- Analysis schema: `proseka_internal_analysis_schema_v1.4.0.json`
- Tips generation spec: `proseka_tips_generation_spec_v1.0.1_advisory.json`
- Per-chart summary schema: `proseka_summary_blocks_canonical.json`
- Batch summary schema: `proseka_batch_summary_schema_v1.1.0.json`
- Taxonomy: `pattern_signals_export_v2.json`
- Training mapping: `tips_training_mapping.json`

**B. Phase 2 Calibration / Heuristics Configs (new, runtime inputs)**
- Track A calibration config: `score_calibration_config_v0.2.1.json`
- Track C/D tuning config: `track_cd_config.json`

**C. Core Engine (deterministic; extended)**
- Detection & metrics: `(2-4.1) chart_visual_detector_merged.py`
- Tag→element mapping: `(4.2) helper_functions.py`
- Alignment: `(4.3) proseka_element_alignment.py`, `(5.3) alignment_helper.py`
- Base inference: `(5.1) severity_detector.py` + `proseka_severity_rules.py`

**Phase 2 add-ons (drop‑in replacements / wrappers):**
- Track A: `proseka_score_calibration.py` (wrapper around base inference)
- Track B: `selector_v2.py` (selection algorithm)
- Track C: `guidance_engine_v2.py` (guidance filler)
- Track D: `narrative_module_v2.py` (narrative renderer)

**D. Orchestration / Wiring (recommendation)**
- Adapters should call the Track A wrapper to produce calibrated `elements_skeleton`.
- Selection should use Track B selector.
- Guidance should use Track C engine.
- Narrative should use Track D module.

---

## 2) Canonical Data Flow (Phase 2)

### Step 2–4.1: SectionMetrics + detected tags
No schema changes. Produces `sections` and `detected_tags`.

### Step 4.2: Tag → element candidates
No schema changes. Produces per-element candidates with `matched_tags` and `training_items`.

### Step 5.1: Severity + score + coverage (Track A)
**Baseline**: base inference produces `elements_skeleton` with severity + midpoint score.

**Track A wrapper** (`proseka_score_calibration.py`):
1) Runs base inference.
2) Applies midpoint overrides (safe).
3) If feature model enabled: computes chart-level score from SectionMetrics features and blends into element scores.
4) Preserves severity labels unless explicitly configured otherwise.

Output remains `elements_skeleton` (same schema).

### Step 5.2: Element selection (Track B)
**selector_v2** performs:
- Dominance-aware ranking score (`score * (base + gain*coverage)`)
- Diversity constraint by canonical family
- Tie bucketization + coverage preference

Returns the final selected set (same count rules).

### Step 5.3: Guidance filling (Track C)
**guidance_engine_v2** performs:
- Dominant taxonomy categories from matched tags
- Combined cause phrases when categories tie
- Mixed-cue breakdown phrasing (such_as / paren)
- Coverage-aware `target_section`

Populates `guidance` fields on elements (same keys).

### Step 6: Narrative generation (Track D)
**narrative_module_v2** renders spec-driven 2-paragraph tips:
- Paragraph 1: element summary
- Paragraph 2: cause → breakdown → guidance, with:
  - small swap allowed when breakdown is long
  - sentence and total word budget enforcement
  - auto-switch mixed-cue breakdown to parenthetical form near hard max (scaled per difficulty)

### Step 7: Summaries
Unchanged contract. Dominant score rule remains `score * section_coverage`.

---

## 3) Non‑Breaking Guarantees

Phase 2 must preserve:
- schema shapes and required keys
- deterministic behavior (no stochastic generation)
- stable selection counts (expert=3, master=3, append=4)

Phase 2 may change:
- numeric `score` values
- selection ranking within eligible elements
- wording (within the narrative spec constraints)

---

## 4) Operational Modes

Recommended modes:
1) **Phase 2 Minimal**: midpoint override only (feature model disabled)
2) **Phase 2 Full**: midpoint override + feature model enabled (blend tuned)

Each mode is controlled by the Track A config and preserves compatibility with Phase 1 outputs.

---

## 5) File Manifest (Phase 2 additions)

### Track A
- `score_calibration_config_v0.2.1.json`
- `proseka_score_calibration.py`
- `TRACK_A_CALIBRATION_PLAYBOOK.md`

### Track B
- `selector_v2.py`

### Track C/D
- `track_cd_config.json`
- `guidance_engine_v2.py`
- `narrative_module_v2.py`

END
