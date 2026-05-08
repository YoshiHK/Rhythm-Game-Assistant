PHASE_1_TIPS_PRODUCTION_GUIDE.md

============================================================
PHASE 2 NOTE
============================================================
This Phase 1 guide is superseded by ULTIMATE_TIPS_PRODUCTION_GUIDE_v2.md
for Track A–D operation.

Use this document only for Phase 1 baseline reference.



Project SEKAI Gameplay Tips Generation – Ultimate Guide (Phase 1)

This document is the portable “single source of operational truth” for producing gameplay tips.
It consolidates: pipeline stages, required inputs/outputs, rules, and the authoritative artifacts.

============================================================
0) Required Artifacts
============================================================

AUTHORITATIVE SPECS (do not modify during runtime)
- pattern_signals_export_v2.json
  - taxonomy of pattern tags grouped by category.
- tips_training_mapping.json
  - mapping: official element (JP) -> tags -> training_items.
- proseka_batch_pipeline.json
  - workflow spec: batch I/O shapes, selection logic, templates, word limits.
- proseka_internal_analysis_schema_v1.4.0.json
  - official element version, severity scale, selection rule baselines.
- proseka_tips_generation_spec_v1.0.1_advisory.json
  - tone rules and paragraph script templates.
- proseka_summary_blocks_canonical.json
  - per-chart summary contract.
- proseka_batch_summary_schema_v1.1.0.json
  - batch-level summary contract.

CORE ENGINE MODULES
- (2-4.1) chart_visual_detector_merged.py
- (4.2) helper_functions.py
- (4.3) proseka_element_alignment.py
- (5.1) element_rules.py
- (5.1) utils.py
- proseka_severity_rules.py
- (5.1) severity_detector.py
- (5.2) proseka_element_selector.py
- (5.3) alignment_helper.py
- (5.3) proseka_guidance_engine.py
- (6) narrative_module.py
- (7) summary_builder.py
- (7) proseka_batch_summary_dataclasses.py
- (7) proseka_batch_summary_presenter.py

ORCHESTRATION
- proseka_pipeline_adapters_production_wired.py
- proseka_tips_pipeline_runner.py (default adapters)

============================================================
1) Pipeline Overview (Inputs -> Outputs)
============================================================

Input (per chart)
- HTML/SVG export or structured payload containing detected tags and/or section metrics.

Output (per chart)
- tips_text (2 paragraphs)
- chart_summary block (canonical per-chart summary schema)

Output (batch)
- summary block (batch summary schema)

============================================================
2) Stage Definitions (Phase 1)
============================================================

Stage 2–4.1: Visual detection and SectionMetrics
- Parse chart export
- Produce NoteEvents
- Build SectionMetrics per section
- Detect pattern tags (tags must align to pattern_signals_export_v2 taxonomy)

Stage 4.2: Tag -> element candidates
- Use tips_training_mapping.json
- For each element: matched_tags = tags ∩ element.tags
- If matched_tags >= min_tag_hits => element present

Stage 5.1: Severity + score + section_coverage + elements_skeleton
- Compute canonical severities per section and aggregated
- Map canonical severities to element severities via registry severity_hooks
- Compute section_coverage:
  coverage(E) = sections where hook severity >= threshold / total_sections
- Compute score from severity bin midpoint
- Emit elements_skeleton dicts with:
  element_id, element_name (JP), category, severity, score, section_coverage

Stage 5.2: Select elements for tips
- target_count: expert=3, master=3, append=4
- filter rules: min_severity, score_ratio_threshold, chart-defining overrides
- sort: score desc, severity desc, section_coverage desc

Stage 5.3: Fill guidance fields
- Use training_items + pattern taxonomy categories
- Create guidance fields:
  difficulty_causes, chart_breakdown, primary_focus, secondary_focus, strategy, target_section
- target_section derived from section_coverage thresholds

Stage 6: Render narrative
- Paragraph 1: element summary
- Paragraph 2: difficulty explanation + breakdown + actionable guidance
- Tone: advisory, practical, supportive (no player variance language)

Stage 7: Summaries
- Per-chart summary block
- Dominant score definition:
  dominant_score = score * section_coverage
- Batch summary aggregates per-chart blocks

============================================================
3) Runner Defaults
============================================================

Default orchestration
- proseka_tips_pipeline_runner.py uses production-wired adapters by default.
- production-wired adapters call severity_detector for severity/score/coverage.

Recommended chart payload
{
  "detected_tags": [...],
  "sections": [...],
  "diagnostics": {...}
}

Fallback chart payload
{ "detected_tags": [...] }

============================================================
4) Versioning Policy
============================================================

- Specs are versioned artifacts; upgrades should be additive where possible.
- Workflow spec (batch pipeline) coordinates other specs; it is not a schema.
- Schemas are validation contracts; avoid embedding procedural rules into schemas.

============================================================
5) Phase 1 Completion Definition
============================================================

Phase 1 is complete when:
- Tips can be generated deterministically from chart exports.
- Outputs conform to the canonical schemas.
- Selection, guidance, and narrative follow the specs without ad-hoc overrides.

END
