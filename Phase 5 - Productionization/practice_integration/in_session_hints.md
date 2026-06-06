### In-Session Hints

Defines how guidance is presented during gameplay.

---

### Purpose

- Surface actionable hints at the right time
- Improve player understanding of recommendations
- Support learning without modifying model outputs

---

### Input Contract

Hints MUST be derived from:

- recommendation_response.reason
- structured reason_codes
- taxonomy-aligned outputs

---

### Presentation Rules

Hints MAY:

- rephrase for readability
- adjust wording for UI clarity
- localize content

Hints MUST NOT:

- ❌ change meaning of recommendation
- ❌ introduce new semantic content
- ❌ override system reasoning

---

### Timing Rules

Hints should be:

- context-aware (gameplay state)
- non-blocking
- dismissible

---

### Telemetry (NEW)

Each hint interaction MUST generate:

- hint_shown
- hint_dismissed
- follow-up action (if any)

Linked via:
- provenance_id
- session_id

---

### Invariants

- Hints are presentation-only
- All hint behavior is observable
- No hint affects model decision logic

---

Hints exist to:
> translate system decisions, not to redefine them