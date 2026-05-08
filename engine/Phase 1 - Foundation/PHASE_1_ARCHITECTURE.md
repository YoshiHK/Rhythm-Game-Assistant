# SYSTEM_ARCHITECTURE.md

## Phase 2 Note

> **Phase 2 extensions are documented in `ADVANCED_SYSTEM_ARCHITECTURE_v2.md`.**

> This Phase 1 document remains authoritative for the baseline architecture; see the v2 document for Track A–D additions.

Project: **Project SEKAI Gameplay Tips Generation** (Phase 1 – Tips Generation Model)

This document describes the **finalized** architecture for the gameplay-tips generation workflow: inputs → detection → analysis → selection → guidance → narrative → summaries → batch reporting.


---

## 1. Architecture at a Glance

### 1.1 Layered Model

**A. Authoritative Specs (contracts and rules)**
- **Workflow / orchestration spec**: `<File>proseka_batch_pipeline.json</File>` (batch I/O shapes, selection logic, templates). 
- **Analysis schema**: `<File>proseka_internal_analysis_schema_v1.4.0.json</File>` (official element set, selection rules, severity scale).
- **Tips generation spec**: `<File>proseka_tips_generation_spec_v1.0.1_advisory.json</File>` (tone, word budgets, paragraph scripts).
- **Per-chart summary schema**: `<File>proseka_summary_blocks_canonical.json</File>`.
- **Batch summary schema**: `<File>proseka_batch_summary_schema_v1.1.0.json</File>`.
- **Pattern signals taxonomy**: `<File>pattern_signals_export_v2.json</File>`.
- **Training mapping**: `<File>tips_training_mapping.json</File>`.

**B. Core Engine (deterministic pipeline implementation)**
- Detection & metrics: `(2-4.1) chart_visual_detector_merged.py`.
- Mapping: `(4.2) helper_functions.py`.
- Registry: `(5.1) element_rules.py` + `(5.1) utils.py`.
- Severity inference: `proseka_severity_rules.py` + `(5.1) severity_detector.py`.
- Selection: `(5.2) proseka_element_selector.py`.
- Guidance: `(5.3) proseka_guidance_engine.py`.
- Narrative: `(6) narrative_module.py`.
- Per-chart summary: `(7) summary_builder.py` + `summary_builder_spec.txt`.
- Batch summary & presenter: `(7) proseka_batch_summary_dataclasses.py` + `(7) proseka_batch_summary_presenter.py`.

**C. Orchestration & Tooling**
- Default adapters (wired): `proseka_pipeline_adapters_production_wired.py`.
- Runner (patched to default adapters): `proseka_tips_pipeline_runner.py` (and `proseka_tips_pipeline_runner_patched.py` where applicable).
- Convenience entrypoints: `api_wrapper.py`, `proseka_notebook_support.py`.

---

## 2. Canonical Data Flow (Step-by-Step)

### Step 2–4.1: Chart parsing, NoteEvents, SectionMetrics, tags
**Module:** `(2-4.1) chart_visual_detector_merged.py`

**Input:** Proseka Trainer HTML/SVG export

**Output (typical payload fields):**
- `sections`: list of `SectionMetrics`
- `detected_tags`: list of pattern-signal tags
- diagnostics / meta

This stage also runs canonical severity inference on sections (via the severity rules engine), and uses both direct geometry heuristics and severity-based heuristics to tag signals.

---

### Step 4.2: Tag → official element candidates
**Module:** `(4.2) helper_functions.py`

**Input:** `detected_tags` (list[str]) + `tips_training_mapping.json`

**Output:** list of inferred element records:
- `element_name` (JP label)
- `matched_tags`
- `training_items`

---

### Step 4.3 / 5.3: Canonical alignment (JP ↔ canonical)
**Modules:** `(4.3) proseka_element_alignment.py`, `(5.3) alignment_helper.py`

Provides reversible mapping and optional grouping by canonical families.

---

### Step 5.1: Severity + score + section coverage + elements_skeleton
**Modules:** `proseka_severity_rules.py`, `(5.1) severity_detector.py`, `(5.1) element_rules.py`, `(5.1) utils.py`

**Key computed outputs:**
- `canonical_severities` (aggregated)
- `per_section` canonical severities
- `element_severities` (derived via registry `severity_hooks`)
- `section_coverages`
- `elements_skeleton`

**Coverage definition (canonical):**
> coverage(E) = (# sections where any hook severity ≥ threshold) / total_sections

**Score definition (Phase 1 baseline):**
> score = representative numeric score derived from the severity bin midpoint.

---

### Step 5.2: Element selection
**Module:** `(5.2) proseka_element_selector.py`

Selects top-N elements per difficulty (Expert/Master: 3, Append: 4) using:
- min severity threshold
- score ratio threshold
- chart-defining override
- sorting: score desc → severity desc → section_coverage desc

---

### Step 5.3: Guidance filling
**Module:** `(5.3) proseka_guidance_engine.py`

Consumes:
- selected elements
- their `training_items` (from training mapping)
- matched tag categories (from pattern taxonomy)
- section_coverage

Produces guidance fields:
- `difficulty_causes`
- `chart_breakdown`
- `primary_focus`
- `secondary_focus`
- `strategy`
- `target_section`

---

### Step 6: Narrative generation
**Module:** `(6) narrative_module.py`

Renders the final 2-paragraph tips text, assuming guidance fields exist.

---

### Step 7: Summary blocks
**Modules:** `(7) summary_builder.py`, `summary_builder_spec.txt`

Produces canonical per-chart summary block.

**Dominance scoring rule (summary):**
> dominant_score = score × section_coverage

Also emits batch-level summaries using the batch summary schema.

---

## 3. Runtime Integration

### 3.1 Default runner path
**Runner:** `proseka_tips_pipeline_runner.py`

By default, the runner uses **wired production adapters**:
- `proseka_pipeline_adapters_production_wired.py`

That adapter set is wired to `(5.1) severity_detector.py` for severity/score/coverage production.

### 3.2 Input payload conventions
Recommended payload shape per chart for full fidelity:
```json
{
  "detected_tags": ["..."],
  "sections": ["SectionMetrics", "..."],
  "diagnostics": {"...": "..."}
}
```

Fallback payload shape for tag-only workflows:
```json
{ "detected_tags": ["..."] }
```

---

## 4. Artifact Boundaries (No Duplication Policy)

- **Schemas** describe **what** the pipeline outputs (validation contracts).
- **Workflow specs** describe **how** outputs are produced (procedural rules + templates).
- **Code** implements the procedure and must treat specs as authoritative inputs.

`proseka_batch_pipeline.json` is a **workflow/orchestration spec**, not a summary schema.

---

## 5. Phase 1 Closure Checklist

Phase 1 (tips generation model) is considered complete when:
- The batch runner produces tips for charts with sufficient structure.
- Selection and guidance are spec-driven and deterministic.
- Summaries conform to the canonical summary schemas.
- All key pipeline artifacts are versioned and portable.

---

## 6. File Manifest (Phase 1)

### Authoritative Specs
- pattern_signals_export_v2.json
- tips_training_mapping.json
- proseka_batch_pipeline.json
- proseka_internal_analysis_schema_v1.4.0.json
- proseka_tips_generation_spec_v1.0.1_advisory.json
- proseka_summary_blocks_canonical.json
- proseka_batch_summary_schema_v1.1.0.json

### Core Engine
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
- summary_builder_spec.txt
- (7) summary_builder.py
- (7) proseka_batch_summary_dataclasses.py
- (7) proseka_batch_summary_presenter.py

### Orchestration & Tooling
- proseka_pipeline_adapters_production_wired.py
- proseka_tips_pipeline_runner.py
- proseka_tips_pipeline_runner_patched.py
- api_wrapper.py
- proseka_notebook_support.py
