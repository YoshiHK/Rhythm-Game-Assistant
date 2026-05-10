# Phase 7 — SDK & Client Contract

This document defines the **client-visible expectations**
for Games Recommendations.

---

## Client Visibility

Phase 7 is exposed to clients only through:

- Phase 6 APIs
- Official SDKs built on top of Phase 6

Clients NEVER interact with Phase 7 directly.

---

## Client Expectations

Clients may assume:

- Game recommendations are:
  - advisory
  - explainable
  - non-blocking
- Absence of recommendations does NOT imply an error.
- Explanations are human-readable but bounded.

Clients MUST NOT assume:

- recommendations are exhaustive,
- rankings are permanent,
- availability implies enablement for all users.

---

## Stability Guarantees

- Contract shapes are stable (versionless).
- Semantic meaning does not change without Phase 6 coordination.
- Feature availability may vary per user or rollout.

---

## Prohibited Client Assumptions

Clients MUST NOT:

- infer platform availability from recommendations,
- treat recommendations as mandatory progression paths,
- cache recommendations indefinitely without refresh signals.

Phase 7 is a discovery aid, not a progression lock.