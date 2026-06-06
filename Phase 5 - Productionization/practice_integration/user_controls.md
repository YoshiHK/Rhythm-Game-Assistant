### User Controls

Defines how players interact with recommendations and hints.

---

### Purpose

- Allow players to customize experience
- Maintain user autonomy
- Provide opt-in / opt-out controls

---

### Supported Controls

- enable/disable hints
- adjust frequency of guidance
- dismiss recommendations
- reset personalization

---

### Constraints (CRITICAL)

User controls MUST:

- affect only presentation
- NOT affect:
  - model outputs
  - taxonomy reasoning
  - dataset generation

---

### Feedback Capture (NEW)

Actions MUST be recorded:

- dismiss → feedback event
- skip → behavior signal
- retry → practice telemetry

---

### Safety Rules

User controls MUST NOT:

- bypass system safeguards
- manipulate evaluation outcomes
- distort learning signals

---

### Observability (NEW)

All control interactions MUST:

- emit telemetry events
- be traceable to session_id
- support experiment analysis

---

User controls exist to:
> empower players without breaking system integrity