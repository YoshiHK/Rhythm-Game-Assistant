## PHASE_2_TIPS_PRODUCTION_GUIDE.md

Project SEKAI Gameplay Tips Generation – Ultimate Guide (Phase 2)

This document is the portable **single source of operational truth**
for producing gameplay tips with **Phase 2 Track A–D enabled**.

---

## 0) Required Artifacts (Phase 2)

### Authoritative Specs & Schemas (do not modify at runtime)
- pattern_signals_export_v2.json  
- tips_training_mapping.json  
- proseka_batch_pipeline.json  
- proseka_internal_analysis_schema_v1.4.0.json  
- proseka_tips_generation_spec_v1.0.1_advisory.json  
- proseka_summary_blocks_canonical.json  
- proseka_batch_summary_schema_v1.1.0.json  

### Phase 2 Tuning Configs (runtime inputs)
- score_calibration_config_v0.2.1.json (Track A)

*(Track C/D tuning configs are applied in Phase 4 Personalization and are not part of Phase 2 runtime.)*

### Phase 2 Modules (drop‑in enhancements)
- selector_v2.py (Track B)  
- guidance_engine_v2.py (Track C)  
- narrative_module_v2.py (Track D)  

---

## 1) Pipeline Overview (Inputs → Outputs)

*(Unchanged)*

---

## 2) Stage Definitions (Phase 2)

*(All stages unchanged; content remains accurate)*

---

## 3) Calibration Operation (Track A)

*(Unchanged)*

---

## 4) Versioning Policy (Phase 2)

- Specs and schemas remain authoritative  
- Track A configs are runtime‑tunable and versioned  
- Engine code remains deterministic  
- Patches are migration aids only  

---

END