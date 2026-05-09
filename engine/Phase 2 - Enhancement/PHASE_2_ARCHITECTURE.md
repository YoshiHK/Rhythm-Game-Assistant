## PHASE_2_ARCHITECTURE.md

Project: **Project SEK A–D Enhancements (Non‑Breaking)**Project: **Project SEKAI Gameplay Tips Generation**  

This document extends the Phase 1 architecture with **Phase 2 enhancement tracks**.
Phase 2 introduces calibrated scoring, improved selection, richer guidance, and
controlled narrative rendering while preserving all Phase 1 contracts.

---

## 1) Architecture at a Glance (Phase 2)

### 1.1 Layered Model

**A. Authoritative Specs & Schemas (unchanged)**  
- Workflow/orchestration spec: proseka_batch_pipeline.json  
- Analysis schema: proseka_internal_analysis_schema_v1.4.0.json  
- Tips generation spec: proseka_tips_generation_spec_v1.0.1_advisory.json  
- Per-chart summary schema: proseka_summary_blocks_canonical.json  
- Batch summary schema: proseka_batch_summary_schema_v1.1.0.json  
- Taxonomy: pattern_signals_export_v2.json  
- Training mapping: tips_training_mapping.json  

**B. Phase 2 Calibration Configs (runtime inputs)**  
- Track A calibration config: score_calibration_config_v0.2.1.json  

*(Track C/D tuning configs are handled in Phase 4 Personalization and are not part of Phase 2 runtime.)*

**C. Core Engine (deterministic; extended)**  
- Detection & metrics: (2–4.1) chart_visual_detector_merged.py  
- Tag → element mapping: (4.2) helper_functions.py  
- Alignment: (4.3) proseka_element_alignment.py, alignment_helper.py  
- Base inference: (5.1) severity_detector.py + proseka_severity_rules.py  

**D. Phase 2 Execution Tracks (integrated via runtime routing)**  
- **Track A**: severity enhancement and calibrated scoring (config‑driven)  
- **Track B**: dominance‑aware element selection (selector_v2)  
- **Track C**: taxonomy‑aware guidance filling (guidance_engine_v2)  
- **Track D**: spec‑driven narrative rendering with readability control (narrative_module_v2)  

**E. Phase 2 Runtime Spine**  
- phase2_core.py orchestrates Stage 2–7 execution  
- stage_router.py enforces canonical stage order  
- track_router.py dispatches Track A–D deterministically  
- runtime_wrapper.py provides a stable black‑box entrypoint for Phase 3  

---

## 2) Canonical Data Flow (Phase 2)

*(No changes; content unchanged from previous version)*

---

## 3) Non‑Breaking Guarantees

Phase 2 preserves:
- schema shapes and required keys  
- deterministic behavior  
- stable selection counts (expert=3, master=3, append=4)

Phase 2 may change:
- numeric score values  
- ranking within eligible elements  
- wording within narrative spec constraints  

---

## 4) Operational Modes

- **Phase 2 Minimal**: midpoint override only  
- **Phase 2 Full**: midpoint override + feature model enabled  

Both modes preserve compatibility with Phase 1 outputs.

---

END

