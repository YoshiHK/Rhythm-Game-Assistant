## PHASE_7_SPEC.md

### Phase 7 — Games Recommendations (Expansion Pack)

**Status:** Design‑Locked  
**Upstream Dependencies:** Phase 1–6 (Read‑Only)

**Non‑Negotiable Rule:**  
**Do not modify anything in Completed Phases.**

---

### 0. Positioning

Phase 7 introduces **game‑level recommendations** to the Rhythm Game Assistant.

Unlike earlier phases that operate at the chart / song / tip level,
Phase 7 operates at the **meta‑game discovery level**.

Phase 7 is explicitly designed to be:
- additive
- downstream‑only
- reversible
- non‑blocking

---

### 1. Purpose

Phase 7 exists to:

- recommend suitable rhythm games based on:
  - demonstrated player capability,
  - preferences,
  - historical interaction;
- guide cross‑game discovery in a multi‑game ecosystem;
- reduce churn caused by poor game–player fit;
- establish a discovery loop above song recommendations.

Phase 7 may evolve over time via **offline learning**, but must remain
**deterministic at runtime**.

---

### 2. Phase Boundary

#### 2.1 Inputs (Consumed Only)

Phase 7 MAY consume:

- player profile and preferences (Phase 4 / 4.5),
- player history and completion‑rate summaries,
- song and game recommendation history,
- game registry and catalog metadata,
- batch difficulty profiles (Phase 3),
- invocation context and observability hooks (Phase 6).

Phase 7 MUST NOT introduce new upstream dependencies.

---

#### 2.2 Outputs (Side‑Effect Free)

Phase 7 produces:

- ranked game recommendations,
- human‑readable explanations,
- recommendation history records,
- **forward‑only feedback events**,
- semantic observability signals.

All outputs are additive and side‑effect free
with respect to Phases 1–6.

---

#### 2.3 Explicit Prohibitions

Phase 7 MUST NOT:

- alter song or chart recommendations;
- change tips meaning, severity, or narrative;
- redefine difficulty taxonomies;
- import or mutate Phase 1–6 logic;
- bypass Phase 6 enforcement;
- perform runtime learning or adaptation;
- perform runtime version switching.

---

### 3. Invariants

#### 3.1 Semantic Isolation

- Game recommendations are **advisory**, not prescriptive.
- They never suppress or override song‑level outputs.
- They exist as a parallel discovery channel.

---

#### 3.2 Contract Preservation

- Phase 7 uses **versionless contracts**.
- Evolution occurs via implementation updates only.
- Backward compatibility is enforced by CI, not runtime branching.

---

#### 3.3 Explainability Requirement

Every recommendation MUST be explainable using:

- player evidence,
- game capability signals,
- deterministic scoring logic.

Opaque or black‑box recommendations are not permitted.

---

### 4. Learning Loop (Normative)

Phase 7 supports a **game recommendation learning loop** under the following rules:

#### 4.1 Feedback Capture

- Phase 7 MAY emit structured feedback events describing:
  - user actions on recommendations,
  - exposure context,
  - recommendation rank.
- Feedback is **observational and forward‑only**.

#### 4.2 Offline Learning

- All learning and calibration occurs **offline in Phase 5**.
- Phase 7 MUST NOT consume feedback events at runtime.
- Learning outputs may include:
  - updated ranking parameters,
  - updated ranking implementation.

#### 4.3 Deployment and Governance

- Learned outcomes are introduced ONLY via deployment.
- Phase 6 governs rollout, rollback, and isolation.
- Runtime behavior remains deterministic and auditable.

This separation is non‑negotiable.

---

### 5. What Phase 7 Is NOT

Phase 7 is NOT:

- a tips generation phase;
- a chart analysis phase;
- a personalization override;
- a learning or experimentation engine at runtime;
- a platform hardening phase.

---

### 6. Relationship to Other Phases

- Phase 7 builds on Phase 6 guarantees.
- Phase 7 emits learning signals to Phase 5.
- Phase 7 does not unlock new upstream behavior.

---

### 7. Contract Closure

Phase 7 is:  
✅ additive  
✅ explainable  
✅ downstream‑only  
✅ reversible  
✅ learning‑enabled (offline)  

Phase 7 is NOT:  
❌ semantic‑breaking  
❌ opaque  
❌ runtime‑adaptive  
❌ upstream‑mutating  

**End of PHASE_7_SPEC.md**