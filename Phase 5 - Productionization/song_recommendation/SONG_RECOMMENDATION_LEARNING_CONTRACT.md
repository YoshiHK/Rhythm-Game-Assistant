## SONG_RECOMMENDATION_LEARNING_CONTRACT

### Phase 5 — Song Recommendation Learning (Offline Only)

**Status:** Authoritative Contract  
**Scope:** Phase 5  
**Upstream:** Phase 6 feedback  
**Downstream:** Deployment only  

---

## 1. Core Principle

Phase 5 improves **selection quality** while preserving:

- runtime determinism
- gameplay meaning
- semantic integrity

---

## 2. Learning Loop

```
Phase 6 runtime
→ feedback
→ Phase 5 learning
→ evaluated artifacts
→ deployment
→ Phase 6 next version
```

Feedback MUST NOT directly affect runtime.

---

## 3. Inputs

### ✅ Allowed

- feedback events
- selection metadata
- exposure diagnostics

### ❌ Forbidden

- tips
- taxonomy
- severity
- narrative
- gameplay semantics

---

## 4. Learning Scope

### ✅ Allowed

- rank decay
- window widening
- producer diversity
- selector heuristics

### ❌ Forbidden

- semantic learning
- content interpretation
- gameplay reasoning

---

## 5. Training

- heuristic calibration ONLY
- no model inference
- deterministic transforms

---

## 6. Evaluation

MUST include:

- acceptance rate
- play rate
- completion rate
- regression guards

---

## 7. Outputs

### ✅ Artifacts

- static selector parameters
- versioned JSON

### ✅ Reports

- training summary
- evaluation report

---

## 8. Deployment Contract

Deployment is allowed ONLY if:

```
evaluation.guard_pass == True
AND
deployment_gate.allowed == True
```

---

## 9. Invariants

- offline-only
- deterministic
- no semantic leakage
- no runtime mutation
- completed phases immutable

Violation = contract broken

---

## 10. Final Guarantee

Phase 5 ensures:

✅ safe learning  
✅ reproducible outputs  
✅ controlled deployment  

WITHOUT introducing runtime instability.

---

**This contract is binding across all Phase 5 components.**