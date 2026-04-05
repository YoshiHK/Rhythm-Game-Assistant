# ORCHESTRATOR_EXTENSION_SPEC.md

**Title:** Orchestrator Extensions (Booster + Stabilizer) — Non‑Breaking Scale Spec  
**Scope:** Phase 3 (Unified Ingestion Manager) control plane only  
**Status:** Draft (Additive, Non‑Breaking)  
**Compatibility Contract:** MUST NOT modify completed phases (Phase 1/2/4). Default behavior MUST remain identical unless explicitly enabled.

---

## 0) Purpose (Why this exists)
As the system scales to many games, failures and regressions increasingly come from orchestration concerns rather than per‑game chart logic: routing, isolation, idempotency, observability, and failure containment.

This spec defines **additive orchestrator extensions** to:
- **Boost** multi‑game operability (routing quality, gating clarity, traceability)
- **Stabilize** execution under volume (idempotency, retries, circuit breakers, deterministic execution, safe fallbacks)

These extensions **do not add gameplay intelligence** and **do not alter tip content logic**.

---

## 1) Strict Non‑Goals
The orchestrator extensions MUST NOT:
1. Change Phase 1–2 detection, tagging, scoring, selection, or narrative rendering.
2. Change Phase 4 personalization decisioning, inference, or safe adjustment behavior.
3. Introduce new heuristics that alter element selection or tip text.
4. Mutate canonical payloads beyond attaching **additive** diagnostics/metadata.
5. Require adapters/validators to be rewritten; integration must be additive.

---

## 2) Definitions
- **Run:** One orchestrator execution for one chart (or a batch item).
- **Stage:** A named pipeline step (e.g., Ingest → Validate → Approachability → Phase1 → Phase2 → Phase4).
- **Mode:** Orchestrator run mode controlling which stages execute.
- **Gate:** A decision point that returns `ALLOW / STOP / DEGRADED` with reason codes.
- **Degraded mode:** Run continues but flags reduced fidelity (e.g., spatial mapping or missing sections).

---

## 3) High‑Level Architecture
Orchestrator remains the Phase‑3 entrypoint that:
- Selects adapter/validator from registry
- Produces canonical payload + canonical row
- Runs batch QA / approachability gate
- If allowed, executes tips pipeline (Phase 1 → Phase 2)
- If enabled, executes personalization (Phase 4)
- Writes outputs and logs events

**Extensions** add:
- **Booster layer:** routing, gating, compatibility introspection, stage‑plan assembly
- **Stabilizer layer:** determinism, isolation, retry policy, circuit breakers, idempotent writes, safe fallbacks

---

## 4) Extension Design Principles (Non‑Breaking Rules)
1. **Opt‑in by flags:** Every new behavior is behind feature flags; default off.
2. **Additive outputs only:** Extensions may attach diagnostics fields but must not alter existing core outputs.
3. **Deterministic:** Same inputs → same decisions and stable ordering.
4. **Stage isolation:** Failures in one stage must not corrupt later stages.
5. **Per‑game correctness:** Tips‑gated games must stop with explicit reasons, not crash.
6. **No silent bypass:** Any fallback/degradation must be explicit in logs and results.

---

# PART A — Orchestrator Booster

## A1) Stage Plan Assembly (Declarative)
**Requirement:** Orchestrator assembles a run plan from:
- game capabilities (adapter + validator)
- requested run mode
- feature flags
- environment constraints

**Output:** `RunPlan` (linear plan or DAG) containing:
- ordered `stages[]`
- per‑stage `inputs/outputs`
- `gates[]` (short‑circuit points)

**Non‑breaking:** If disabled, orchestrator uses the current fixed sequence.

---

## A2) Unified Gate Protocol (Reasoned STOP/DEGRADED)
Standardize internal gate outputs (without changing Phase outputs):

```json
{
  "decision": "ALLOW | STOP | DEGRADED",
  "stage": "INGEST | VALIDATE | APPROACHABILITY | PHASE1 | PHASE2 | PHASE4",
  "reason_code": "...",
  "details": {"key": "value"}
}
```

**Must include:** stable `reason_code` enum set (see §9).

---

## A3) Capability Introspection & Compatibility Matrix
Compute an informational per‑run matrix:
- `note_model`: lane_based / spatial / other (informational)
- supports_sections
- supports_variable_bpm
- supports_width
- supports_bpm_changes
- emits_canonical_payload
- time_unit (if applicable)

Use it to:
- pick correct sub‑pipelines (e.g., sections stage only when supported)
- set degraded mode explicitly
- generate UI/QA explanations

**Non‑breaking:** informational only; gating must not change unless the same gate already exists.

---

## A4) Registry & Preflight Health Checks
Before executing any chart:
- confirm adapter/validator resolvable
- confirm adapter accepts extension (warn if mismatch; strict stop only if flag enabled)
- confirm required methods exist

**Non‑breaking:** default is warn + continue unless strict mode enabled.

---

## A5) Per‑Game Defaults Without Code Branching
Introduce optional per‑game orchestration config (separate from completed phase specs), e.g.:
- lane_offset defaults
- ticks_per_beat expectation
- time_unit override
- ingestion_only flag

**Goal:** avoid `if game_id == ...` sprawl.

---

# PART B — Orchestrator Stabilizer

## B1) Deterministic Ordering & Tie‑Breaks
All orchestrator aggregation steps must be deterministic:
- stable stage execution order
- stable sort of events/logs
- stable tie‑break rules

---

## B2) Idempotency & Run Keys
Define a deterministic `RunKey`:

```
RunKey = hash(game_id + chart_id + difficulty + adapter_version + pipeline_version + feature_flags_digest)
```

Use RunKey to:
- dedupe writes
- dedupe event logs
- allow safe retries

---

## B3) Stage Sandboxing (Failure Containment)
Each stage executes with:
- isolated working namespace
- bounded resource budgets (time/memory)
- exception boundary converting crash → `STOP` with reason_code

---

## B4) Retry Policy (Safe Retries Only)
Retries allowed only for:
- transient IO errors
- timeouts
- known flaky storage operations

Retries NOT allowed for:
- structural validation failures
- approachability failures
- deterministic algorithm failures

Default:
- max_attempts = 2
- exponential backoff + jitter

---

## B5) Circuit Breakers / Bulkhead Isolation
Prevent one failing game or stage from collapsing a batch:
- per‑game circuit breaker
- per‑stage circuit breaker
- per‑game concurrency limits

Example policy:
- N unexpected exceptions in validator/adapters → open breaker for that game in current batch

---

## B6) Safe Fallback Modes
If tips cannot proceed, orchestrator may still return:
- canonical payload (if available)
- validation report
- approachability decision
- diagnostics

Define additive fallback outputs:
- `INGEST_ONLY`
- `SUMMARY_ONLY`
- `DIAGNOSTICS_ONLY`

Any fallback mode MUST be represented as a `DEGRADED` gate decision
with an explicit `reason_code`.

Silent fallback is forbidden.

**Non‑breaking:** Only used where current pipeline would stop anyway.

---

## B7) Schema Enforcement (Pre‑Phase‑1)
Before entering Phase‑1:
- enforce presence/types of required canonical fields
- ensure `note_events` non‑empty
- ensure `chart_meta` sanity

If fail:
- STOP with reason_code `SCHEMA_INVALID`
- attach minimal debug details (missing keys)

---

# 7) Run Modes (Additive)
Introduce run modes (without changing default behavior):
- `ingest`: adapter + row + validator + batch QA
- `tips`: Phase 1 + Phase 2 (requires approachability allow)
- `personalized`: includes Phase 4 (requires gating/opt‑in)
- `full`: ingest + tips + optional personalization

---

# 8) Observability, Diagnostics & CLI Surfacing


## 8.1 Structured Run Report (First‑Class Output)

When orchestrator extensions are enabled, the orchestrator MUST be capable of
emitting a structured per‑run report (`RunReport`).

This report is:
- Control‑plane only (no gameplay semantics)
- Deterministic
- Safe to emit to logs, JSON output, and observability systems

### Canonical Shape

{
  "run_key": "...",
  "game_id": "...",
  "chart_id": "...",
  "mode": "full | tips | ingest | personalized",
  "stage_results": [
    {
      "stage": "INGEST",
      "status": "OK",
      "ms": 123
    },
    {
      "stage": "APPROACHABILITY",
      "status": "STOP",
      "reason_code": "APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE",
      "details": { "min_sections": 3, "observed": 1 }
    }
  ],
  "gates": [
    {
      "decision": "STOP",
      "stage": "APPROACHABILITY",
      "reason_code": "APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE"
    }
  ],
  "warnings": [],
  "degraded_mode": false
}

---

## 8.2 Minimum Metrics
Track at minimum:
- runs_total by game_id
- stop_total by reason_code
- crash_total by stage
- avg_latency_ms by stage
- retry_count
- circuit_breaker_open_count
- dedupe_hits

---

## 8.3 CLI JSON Output Contract (STOP / DEGRADED Surfacing)

When the orchestrator is invoked via CLI with `--json` output enabled,
and orchestrator extensions are active:

### Requirements

1. If a run STOPs or DEGRADED:
   - The CLI JSON output MUST surface:
     - `decision` (STOP | DEGRADED)
     - `reason_code`
     - `stage` at which the decision occurred

2. This information MUST be included even if:
   - The pipeline stopped early
   - Tips generation did not run
   - Personalization was not reached

3. The CLI JSON output MAY embed the full `RunReport`,
   or MAY embed a summarized projection:

{
  "file": "...",
  "game_id": "...",
  "passed": false,
  "decision": "STOP",
  "stage": "APPROACHABILITY",
  "reason_code": "APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE",
  "run_key": "...",
  "diagnostics": { ... }
}

---

# 9) Standard Reason Codes (Stable Enum)
Reason codes must be stable (additions allowed; removals not).
All `reason_code` values are:
- Stable
- Machine‑readable
- Required to surface in structured RunReport
- Required to surface in CLI JSON output when STOP or DEGRADED occurs

**Adapter/Registry**
- `ADAPTER_NOT_FOUND`
- `VALIDATOR_NOT_FOUND`
- `UNSUPPORTED_EXTENSION`
- `CAPABILITIES_MISMATCH`

**Schema/Structure**
- `SCHEMA_INVALID`
- `NOTE_EVENTS_EMPTY`
- `CHART_META_INVALID`

**Approachability Gate**
- `APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE`
- `APPROACHABILITY_FAIL_UNSUPPORTED_MODEL`

**Tips Pipeline**
- `TIPS_DISABLED_FOR_GAME`
- `PATTERN_TAXONOMY_INCOMPLETE`
- `SECTIONS_UNAVAILABLE`

**Personalization**
- `PHASE4_FLAG_DISABLED`
- `PHASE4_OPT_OUT`
- `PHASE4_GATING_FAIL`

**Operational**
- `IO_TRANSIENT_FAILURE`
- `TIMEOUT`
- `UNHANDLED_EXCEPTION`

---

# 10) Compatibility & Versioning

## 10.1 Version Digests
Compute digests for:
- adapter version
- validator version (if available)
- pipeline version(s)
- feature flags

Include in RunKey and event provenance.

## 10.2 Non‑Breaking Upgrade Policy
- Additive stages allowed
- Additive reason codes allowed
- Existing run modes keep semantics
- Defaults unchanged unless flags enabled

---

# 11) Testing & QA (Scale Guardrails)

## 11.1 Golden Runs (Per Game)
Maintain per‑game tiny chart(s) with expected outcomes:
- ALLOW/STOP/DEGRADED
- expected reason_code if not ALLOW

## 11.2 Batch Stress Tests
Run mixed‑game batches and assert:
- no cross‑run state leaks
- idempotency works
- breakers isolate failures

## 11.3 Determinism Tests
Same input twice → identical RunKey, stage decisions, reason codes, and ordering.

---

# 12) Implementation Notes (Non‑Binding)
This spec does not prescribe files/classes, but typical additive modules may include:
- `orchestrator_run_plan.py`
- `orchestrator_gates.py`
- `orchestrator_stabilizer.py`
- `orchestrator_metrics.py`

Existing orchestrator entrypoints remain intact.

---

## Appendix — “Necessary Items” Checklist

### Booster essentials
- Stage plan assembly
- Unified gate protocol + reason codes
- Capability/compatibility matrix
- Registry preflight checks
- Per‑game defaults config (avoid if/else branching)

### Stabilizer essentials
- Deterministic ordering
- RunKey idempotency + dedupe
- Stage sandboxing + exception boundaries
- Retry policy (transient only)
- Circuit breakers + bulkheads
- Safe fallback modes
- Schema enforcement pre‑Phase‑1
- Structured run report + core metrics
