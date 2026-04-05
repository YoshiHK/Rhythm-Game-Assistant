# SPEC_INDEX.md

## Phase 2 Note

> **Phase 2 artifacts are indexed in `ADVANCED_SPEC_INDEX_v2.md`.**

> This Phase 1 index remains authoritative for baseline specs and schemas.

``

Project: **Project SEKAI Gameplay Tips Generation**  
Phase: **Phase 1 – Tips Generation Model (Finalized)**

This index is the authoritative map of **all specifications, schemas, and code artifacts** involved in the tips generation pipeline. It clarifies **ownership, responsibility, and dependency direction** so the system can be maintained, audited, or extended without ambiguity.

---

## 1. How to Read This Index

Artifacts are grouped by **role**, not by file type.

- **Specs** = declarative, authoritative rules or contracts
- **Schemas** = validation contracts (what outputs look like)
- **Engine Code** = deterministic implementation
- **Orchestration** = wiring and runtime flow
- **Tooling** = convenience / access layers

Only **Specs and Schemas** should be treated as *authoritative inputs*. Code must conform to them.

---

## 2. Authoritative Specifications (Do Not Modify at Runtime)

### 2.1 Workflow / Orchestration Spec
- **`proseka_batch_pipeline.json`**  
  *Role*: Defines batch-level workflow rules, selection logic, templates, and I/O shapes.  
  *Type*: Procedural spec (NOT a data schema).

---

### 2.2 Analysis & Selection Rules
- **`proseka_internal_analysis_schema_v1.4.0.json`**  
  *Role*: Official element set, severity scale, selection baselines.

---

### 2.3 Tips Narrative Rules
- **`proseka_tips_generation_spec_v1.0.1_advisory.json`**  
  *Role*: Tone, word limits, paragraph structure, phrasing constraints.

---

### 2.4 Taxonomy & Training Intent
- **`pattern_signals_export_v2.json`**  
  *Role*: Canonical taxonomy of detected pattern signals.

- **`tips_training_mapping.json`**  
  *Role*: Mapping from official elements → tags → training_items.

---

## 3. Canonical Schemas (Validation Contracts)

### 3.1 Per‑Chart Summary Schema
- **`proseka_summary_blocks_canonical.json`**  
  *Role*: Contract for per-chart analytical summaries.

---

### 3.2 Batch Summary Schema
- **`proseka_batch_summary_schema_v1.1.0.json`**  
  *Role*: Contract for aggregated batch-level summaries.

---

## 4. Core Engine Implementation

### 4.1 Detection & Metrics
- `(2-4.1) chart_visual_detector_merged.py`

### 4.2 Tag → Element Mapping
- `(4.2) helper_functions.py`
- `(4.3) proseka_element_alignment.py`

### 4.3 Severity, Score & Coverage
- `(5.1) element_rules.py`
- `(5.1) utils.py`
- `proseka_severity_rules.py`
- `(5.1) severity_detector.py`

### 4.4 Selection & Guidance
- `(5.2) proseka_element_selector.py`
- `(5.3) alignment_helper.py`
- `(5.3) proseka_guidance_engine.py`

### 4.5 Narrative Rendering
- `(6) narrative_module.py`

### 4.6 Summaries
- `summary_builder_spec.txt`
- `(7) summary_builder.py`
- `(7) proseka_batch_summary_dataclasses.py`
- `(7) proseka_batch_summary_presenter.py`

---

## 5. Orchestration & Runtime

- **`proseka_pipeline_adapters_production_wired.py`**  
  *Role*: Production adapters wired to the severity detector.

- **`proseka_tips_pipeline_runner.py`**  
  *Role*: Canonical batch runner (defaults to wired adapters).

- **`proseka_tips_pipeline_runner_patched.py`**  
  *Role*: Variant runner with defaults applied explicitly.

---

## 6. Tooling / Access Layer (Non‑Authoritative)

- **`api_wrapper.py`**  
  *Role*: Convenience entrypoint for batch analysis.

- **`proseka_notebook_support.py`**  
  *Role*: Notebook-oriented loader for specs and light validation helpers.

---

## 7. Patch Artifacts (How to Wrap Them)

### 7.1 Patch File
- **`proseka_tips_pipeline_runner_default_adapters.patch`**

### 7.2 Recommended Handling

Patch files are **not runtime artifacts**. They should be:

- Stored under a dedicated directory, e.g.
  ```
  patches/
    proseka_tips_pipeline_runner_default_adapters.patch
  ```
- Referenced from documentation, not imported by code.
- Applied via version control tooling (`git apply`).

### 7.3 Documentation Wrapper (Recommended)

Create a small README alongside the patch:
```
patches/
  README.md
  proseka_tips_pipeline_runner_default_adapters.patch
```

**README.md (example):**
> This patch updates `proseka_tips_pipeline_runner.py` to default to production-wired adapters.  
> It is required only if the base runner does not yet include this behavior.

---

## 8. Dependency Direction (Strict)

```
Specs & Schemas
      ↓
Core Engine Code
      ↓
Orchestration
      ↓
Tooling / Access
```

No code may redefine rules already specified in specs or schemas.

---

## 9. Phase 1 Status

✅ Phase 1 – **COMPLETE**  
All artifacts required to generate deterministic, spec-compliant gameplay tips are finalized and indexed.

Further work belongs to Phase 2 (model improvements, heuristics tuning, or learning-based scoring).

END
