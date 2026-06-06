## Phase 5 — Song Recommendation Learning
Song Recommendations in the Rhythm Game Assistant.

Phase 5 closes the loop:

```
runtime behavior → feedback → learning → validated improvement → deployment
```

---

## 🔷 Pipeline Overview

```
Phase 6 (Runtime)
↓
feedback events (forward-only)
↓
Phase 5 (Offline Learning)
aggregation
→ features
→ training
→ evaluation
→ artifacts
→ deployment_gate ✅
↓
Deployment
↓
Phase 6 (Next Version)
```

---

## 🔷 Purpose

Phase 5 exists to:

- improve **selection quality**
- calibrate deterministic heuristics
- validate improvements safely
- produce deployable outputs

WITHOUT:

- changing gameplay meaning
- breaking runtime determinism
- introducing semantic drift

---

## 🔷 Scope

### ✅ Responsibilities

- Aggregate feedback signals
- Construct selection-level features
- Calibrate heuristic parameters
- Evaluate learning outcomes
- Guard regressions
- Produce deployment-safe artifacts
- Enforce deployment eligibility

---

### ❌ Non-Responsibilities

- Runtime recommendation logic
- Gameplay interpretation
- Tips / narrative / taxonomy
- Real-time adaptation
- UI / presentation

---

## 🔷 Non‑Negotiable Boundaries

This layer MUST:

- be offline only
- be deterministic
- be auditable
- be reversible
- preserve all completed phase contracts

This layer MUST NOT:

- import Phase 6 runtime logic
- modify completed phases
- introduce semantics
- dynamically load artifacts in runtime

---

## 🔷 Determinism (Hard Contract)

- identical inputs → identical outputs
- no randomness
- no time-based effects
- enforced by CI

Violation = pipeline invalid.

---

## 🔷 Key Subsystems

| Layer | Purpose |
|------|--------|
| aggregation | behavior → structured signals |
| features | signals → model-ready data |
| training | calibration (heuristics only) |
| evaluation | metrics + regression guards |
| artifacts | deployment outputs |
| deployment | promotion decision |

---

## 🔷 Deployment Safety (NEW)

Artifacts are NOT automatically deployable.

Deployment requires:

```
evaluation.guard_pass == True
AND
deployment_gate.allowed == True
```

---

## 🔷 Relationship to Other Phases

- Upstream: Phase 6 runtime feedback
- Downstream: Deployment → Phase 6 config
- Parallel: Other Phase 5 learning systems

---

## 🔷 Design Intent

Phase 5 enables the system to learn:

✅ which recommendations perform better  

WITHOUT learning:

❌ gameplay meaning  
❌ tips content  
❌ runtime logic  

---

**Phase 5 makes learning safe by making it:**
- offline  
- deterministic  
- governed  
- auditable  


