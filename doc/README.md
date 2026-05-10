# Repository Documentation

This directory contains the **authoritative documentation** for the
Rhythm Game Assistant system.

These documents describe:
- system architecture and phase boundaries,
- routing and runtime topology,
- control‑plane vs semantic responsibilities,
- operational guarantees and limitations.

They are **descriptive of the current system**, not aspirational.

---

## 🔑 Single Source of Truth (Routing)

> ✅ **Routing Truth:**  
> **`Repo_Routing_Skeleton.txt`**

This file defines:
- the only legal runtime entrypoints,
- which phases may call which,
- forbidden routing paths,
- and the current Phase 1–7 wiring topology.

If documentation, diagrams, or code comments conflict with the routing skeleton,
**the routing skeleton wins**.

---

## 📘 Core Architecture Documents

### ARCHITECTURE.md
- End‑to‑end system architecture (Phase 1–7)
- Semantic vs control‑plane separation
- Phase 6 as the sole runtime gate
- References `Repo_Routing_Skeleton.txt` as routing authority

### ARCHITECTURE_CLOSEOUT.md
- Design‑locked declarations
- Phase completion and freeze rationale
- Architectural invariants

---

## 🧭 Specifications

### SPEC.md
- High‑level system specification
- Phase responsibilities and invariants
- Non‑goals and constraints

### Phase‑Specific Specs
- `PHASE_1_SPEC.md`
- `PHASE_2_SPEC.md`
- `PHASE_3_SPEC.md`
- `PHASE_4_SPEC.md`
- `PHASE_4.5_SPEC.md`
- `PHASE_5_SPEC.md`
- `PHASE_6_SPEC.md`
- `PHASE_7_SPEC.md`

Each phase spec defines **what the phase owns and what it must not do**.

---

## 🚦 Usage & Integration

### USAGE.md
- Supported entrypoints (CLI, API)
- Phase 6 runtime usage
- OrchestratorBridge integration
- Tips flow vs Games Recommendation flow

### LIMITATIONS.md
- Hard prohibitions per phase
- Explicit non‑goals
- Guardrails that preserve trust and determinism

---

## 📦 Control‑Plane & Integration

### MANIFEST.md
- Canonical source document lineage
- Wave‑based evolution history
- Control‑plane anchors (bridge, schemas, games.json)

### PLATFORM_OVERVIEW.md
- Platform‑level view (Phase 6 perspective)
- Runtime guarantees
- Security and operational posture

---

## 🧠 How to Read These Docs (Recommended Order)

1. **Repo_Routing_Skeleton.txt** ← routing truth
2. ARCHITECTURE.md
3. SPEC.md
4. USAGE.md
5. LIMITATIONS.md
6. Phase‑specific specs (as needed)

---

## ✅ Design‑Locked Guarantees

Across all documents, the following invariants hold:

- ✅ Completed semantic phases are frozen
- ✅ Wiring between phases may evolve
- ✅ Phase 6 is the only runtime gate
- ✅ STOP / DEGRADED are valid outcomes
- ✅ No runtime versioning
- ✅ No silent fallback

If a change violates any of these, it is **architecturally invalid**.

---

## 📌 Final Note

These documents are intended to be:
- readable by new contributors,
- enforceable in code review,
- stable over time.

They reflect the system **as it exists today**.

For questions about routing, **always consult `Repo_Routing_Skeleton.txt` first**.