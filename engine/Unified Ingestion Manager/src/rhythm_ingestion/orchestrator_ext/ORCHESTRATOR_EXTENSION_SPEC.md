## ORCHESTRATOR_EXTENSION_SPEC.md

**Title:** Orchestrator Extensions (Booster + Stabilizer) — Non‑Breaking Control‑Plane Spec  
**Scope:** Phase 3 control plane only  
**Status:** Design‑Locked (Additive, Non‑Breaking)

---

### 0. Purpose

As the system scales, failures increasingly originate from orchestration concerns:
routing, isolation, retries, observability, and failure containment.

This spec defines **additive orchestrator extensions** that:
- improve multi‑game operability,
- stabilize execution under load,
- without altering gameplay semantics.

---

### 1. Strict Non‑Goals

Extensions MUST NOT:
- change Phase 1–2 detection or narrative,
- change Phase 4 personalization,
- introduce gameplay heuristics,
- mutate canonical payload semantics.

---

### 2. Boundary Definition

- **Stable entrypoint:** `OrchestratorBridge.run(...)`
- **Boundary contract:**
  - `mode` is accepted as **string**
  - semantic enums are internal only
- **Default behavior:** thin pass‑through

---

### 3. Booster Layer (Control‑Plane)

- Declarative RunPlan assembly
- Unified gate protocol
- Capability introspection (informational)
- Per‑game defaults via config

---

### 4. Stabilizer Layer (Control‑Plane)

- Deterministic RunKey
- Bounded retries
- Circuit breakers
- Exception → STOP conversion

STOP and DEGRADED are **valid outcomes**.

---

### 5. Run Modes

Supported modes (additive):
- `ingest`
- `tips`
- `personalized`
- `full`

Defaults remain unchanged unless flags enabled.

---

### 6. Observability & Schema

- Structured RunReport is first‑class
- CLI JSON output MUST surface STOP / DEGRADED
- JSON schemas define control‑plane contracts
- Schema validation is non‑blocking

---

### 7. Reason Codes

- Stable enum
- Additions allowed
- Removals forbidden
- Required on STOP / DEGRADED

---

### 8. Compatibility Policy

- No runtime version switching
- Additive upgrades only
- Defaults preserve legacy behavior

---

### 9. Summary

The Orchestrator Extension:
- protects semantic correctness,
- absorbs operational complexity,
- enables long‑term evolution without regressions.

This spec defines the **sealed control‑plane contract**.