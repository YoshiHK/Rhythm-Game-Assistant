# rhythm_ingestion.orchestrator_ext

The **orchestrator extension** is an **additive, non‑breaking control‑plane layer**
for the Unified Ingestion Manager (UMI).

It exists to **stabilize, boost, and optimize orchestration work** as the system
scales across:

- many rhythm games
- multiple run modes
- personalization
- localization
- future production hardening phases

> **This package MUST NOT modify completed semantic phases.**  
> It coordinates execution and observability — not gameplay logic.

---

## What this package is

A **control‑plane extension layer** that can wrap an existing Phase‑3 orchestrator
**without modifying it**, providing:

- deterministic orchestration
- unified STOP / DEGRADED gating
- structured run reporting
- retry and circuit‑breaker hooks
- idempotency and provenance
- schema‑validated CLI JSON output

All behavior is **opt‑in via feature flags**.

If extensions are disabled, the orchestrator behaves **exactly as before**.

---

## What this package is NOT

The orchestrator extension **does not**:

- change Phase 1–2 detection, tagging, scoring, or narrative generation
- change Phase 4 personalization logic or model behavior
- introduce gameplay heuristics
- mutate canonical payloads beyond additive diagnostics

This preserves correctness, determinism, and long‑term auditability.

---

## Module overview

### Core data & contracts

- **`types.py`**  
  Canonical control‑plane dataclasses and enums:
  - `RunMode`
  - `Stage`
  - `GateDecision`
  - `GateResult`
  - `StageResult`
  - `RunPlan`
  - `RunReport`
  - `RunContext`
  - `compute_run_key()`

- **`reason_codes.py`**  
  Stable, machine‑readable reason‑code enum.
  - Used for all STOP / DEGRADED decisions
  - Additive only (no removals)

- **`interfaces.py`**  
  Protocol definitions for:
  - adapters
  - validators
  - orchestrator core

  Allows wrapping without rewriting existing code.

---

### Configuration & feature control

- **`feature_flags.py`**  
  Feature‑flag switches controlling all extension behavior.
  - Defaults preserve existing behavior
  - Enables gradual rollout and per‑environment control

- **`config.py`**  
  Orchestrator extension configuration:
  - retry policy
  - circuit breaker policy
  - per‑game defaults
  - strict vs permissive preflight

---

### Booster layer (planning & gating)

- **`run_plan.py`**  
  Declarative stage‑plan assembly.
  - Builds a `RunPlan` from run mode, flags, and capabilities
  - Non‑breaking: disabled → current fixed pipeline order

---

### Stabilizer layer (reliability & safety)

- **`stabilizer.py`**  
  Execution hardening wrapper:
  - idempotency via `RunKey`
  - retry (transient failures only)
  - circuit breakers / bulkheads
  - exception → STOP conversion
  - safe fallback paths

  Control‑plane only; no semantic logic.

---

### Reporting & observability

- **`reporting.py`**  
  Helpers for constructing and projecting `RunReport` objects.

- **`schemas/`**  
  Canonical JSON Schemas:
  - `orchestrator_run_report.schema.json`
  - `orchestrator_cli_result.schema.json`

  These define the **contract** for structured output and CLI JSON.

- **`schema_validator.py`**  
  Optional schema validation hook:
  - Validates RunReport and CLI JSON against schemas
  - Uses `jsonschema` if available
  - Falls back to minimal structural checks if not
  - Intended for CI, QA, and optional runtime assertions

---

### Integration & wiring

- **`bridge.py`**  
  The **single integration entrypoint**.

  Wraps:
  - a core object exposing `.run(...)`, **or**
  - an existing orchestrator module exposing `ingest(...)`

  Guarantees:
  - stable `.run()` surface
  - pass‑through behavior when flags are off
  - no dependency on Phase 1 / 2 / 4 logic

---

## Typical usage

```python
from rhythm_ingestion.orchestrator_ext import (
    wrap_orchestrator,
    OrchestratorExtensionConfig,
    FeatureFlags,
)

cfg = OrchestratorExtensionConfig(
    feature_flags=FeatureFlags(
        enable_retries=True,
        enable_circuit_breakers=True,
        enable_run_report=True,
    )
)

orch = wrap_orchestrator(existing_orchestrator, cfg)

result = orch.run(
    game_id="pjsekai",
    chart_path="./charts",
    db_path="SongDB.xlsx",
    tips_mode="production",
)