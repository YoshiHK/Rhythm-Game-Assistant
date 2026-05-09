# ULTIMATE_TIPS_PRODUCTION_GUIDE_v2.md
Project SEKAI Gameplay Tips Generation – Ultimate Guide (Phase 2)

This is the portable “single source of operational truth” for producing gameplay tips **with Phase 2 Track A–D enabled**.
It extends `ULTIMATE_TIPS_PRODUCTION_GUIDE.txt` (Phase 1) with calibration, selection, guidance, and narrative upgrades.

---

## 0) Required Artifacts (Phase 2)

### Authoritative Specs & Schemas (do not modify at runtime)
- `pattern_signals_export_v2.json`
- `tips_training_mapping.json`
- `proseka_batch_pipeline.json`
- `proseka_internal_analysis_schema_v1.4.0.json`
- `proseka_tips_generation_spec_v1.0.1_advisory.json`
- `proseka_summary_blocks_canonical.json`
- `proseka_batch_summary_schema_v1.1.0.json`

#### Phase 2 Tuning Configs (runtime inputs)
- score_calibration_config_v0.2.1.json (Track A)

(Track C/D tuning configs are applied in Phase 4 and are not part of Phase 2 runtime.)

### Core Engine Modules
- Phase 1 core modules remain required (detection, mapping, base inference).

### Phase 2 Modules (drop-in extensions)
- `proseka_score_calibration.py` (Track A wrapper)
- `selector_v2.py` (Track B)
- `guidance_engine_v2.py` (Track C)
- `narrative_module_v2.py` (Track D)

---

## 1) Pipeline Overview (Inputs → Outputs)

### Input (per chart)
Preferred payload shape:
```json
{
  "detected_tags": ["..."],
  "sections": ["SectionMetrics", "..."],
  "diagnostics": {"...": "..."}
}
```
Fallback payload:
```json
{ "detected_tags": ["..."] }
```

### Output (per chart)
- `tips_text` (2 paragraphs)
- `chart_summary` (per-chart summary schema)

### Output (batch)
- `batch_summary` (batch summary schema)

---

## 2) Stage Definitions (Phase 2)

### Stage 2–4.1: Visual detection and SectionMetrics
- Produce `sections` (SectionMetrics)
- Detect pattern tags aligned to taxonomy

### Stage 4.2: Tag → element candidates
- Use `tips_training_mapping.json`
- Emit per-element candidates with `matched_tags` and `training_items`

### Stage 5.1: Severity + score + coverage (Track A)
- Run base inference (Phase 1)
- Apply severity midpoint overrides
- If feature model enabled: compute chart-level scalar from SectionMetrics features and blend into element scores
- Preserve severity labels by default

### Stage 5.2: Select elements for tips (Track B)
- Use `selector_v2.select_elements_v2()`
- Enforce target counts: expert=3, master=3, append=4
- Use dominance-aware ranking + diversity + stable tie breaks

### Stage 5.3: Fill guidance fields (Track C)
- Use `guidance_engine_v2.fill_guidance_for_elements_v2()`
- Dominant (and tied) taxonomy categories drive cause
- Mixed-cue breakdown phrasing uses cue labels

### Stage 6: Render narrative (Track D)
- Use `narrative_module_v2.generate_tips_text_v2()`
- Spec-template rendering
- Small swap allowed for readability
- Word budget enforcement
- Auto-switch breakdown variant near hard max (scaled per difficulty)

### Stage 7: Summaries
- Dominant score remains `score * section_coverage`
- Emit canonical per-chart + batch summaries

---

## 3) Calibration Operation (Track A)

### Configuration
- Use `score_calibration_config_v0.2.1.json`
- Midpoint overrides define spacing between severity buckets
- Feature model toggles chart-level calibration

### Evaluation checklist (recommended)
- rank correlation (human/QA ordering)
- stability (selection shouldn’t oscillate under small noise)
- bucket sanity (rare demanding, common slight)
- tips compliance (word limits + tone)

---

## 4) Versioning Policy (Phase 2)
- Specs/schemas remain authoritative.
- Track A / Track C-D configs are runtime-tunable and should be versioned.
- Engine code remains deterministic.
- Patches are migration aids only.

END
