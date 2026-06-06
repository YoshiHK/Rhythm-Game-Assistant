## Phase 5 — Practice Integration & In-Session Experience

This layer defines how recommendations and guidance
are delivered to players during gameplay and practice.

---

## 🔷 Pipeline Role

```
recommendation_response → UI → in-session hints → practice → telemetry → feedback
```

---

## 🔷 Purpose

- Deliver recommendations in a usable form
- Provide contextual guidance during gameplay
- Capture player interaction signals
- Feed observability and learning pipelines

---

## 🔷 What This Layer Does

- Render recommendations and hints
- Map system outputs into gameplay context
- Capture user interaction signals
- Record telemetry for downstream analysis
- Support practice mode integration

---

## 🔷 What This Layer Does NOT Do

- ❌ Does NOT change semantic meaning
- ❌ Does NOT modify recommendation output logic
- ❌ Does NOT generate training labels
- ❌ Does NOT bypass Phase 6 control

---

## 🔷 Data Contract (NEW)

Primary schema:
- `practice_telemetry.schema.json`

Generated via:
- `build_practice_telemetry_event()`

Key objects:
- `practice_context` (mode, song, difficulty)
- `metrics` (duration, retry count)
- `experiment` (assignment tracking)

---

## 🔷 Practice Modes

| Mode | Purpose |
|------|----------|
| hint_shown | User requests guidance |
| hint_dismissed | User ignores hint |
| practice_retry | User attempts section again |
| section_replayed | User goes back to section |
| session_started | Practice begins |
| session_ended | Practice ends |

---

## 🔷 Relationship to Other Layers

| Layer | Role |
|-------|------|
| Recommendation | upstream (structured output) |
| UI/UX | parallel (presentation) |
| Telemetry | downstream (signal collection) |
| Feedback Aggregation | downstream (user reactions) |

---

## 🔷 Invariants

- All outputs must be traceable via provenance_id
- Presentation must not alter system meaning
- All interactions must be observable via telemetry
- Practice context must be fully populated

---

## 🔷 Design Intent

Practice Integration exists to:

✅ Deliver decisions safely
✅ Capture user engagement signals
✅ Support learning through guidance

NOT:

❌ Change recommendation meaning
❌ Make semantic modifications
❌ Bypass observability

---

**Practice Integration: Delivering decisions safely, without changing them.**
