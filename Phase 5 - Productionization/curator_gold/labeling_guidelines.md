## Curator Labeling Guidelines (Phase 5)

This document defines how curators apply **gold labels** used for
offline evaluation and retraining.

### Core Principles

- Judge **correctness**, not writing style.
- Anchor all judgments to **Phase 4 provenance**.
- Do not infer intent beyond observable output.
- When uncertain, record uncertainty rather than forcing agreement.

### Label Semantics

- **tip_effectiveness**  
  Did the tip meaningfully help address the identified issue?

- **severity_accuracy**  
  Was the assigned severity appropriate given the chart context?

- **element_relevance**  
  Was the chosen gameplay element correct and well‑scoped?

- **recommendation_quality**  
  Was the recommended song appropriate for the player’s capability?

### Confidence & Notes

- Confidence reflects how strongly the curator believes the label
  represents ground truth.
- Notes are encouraged for edge cases and ambiguous charts.

### Non‑Goals

- Labels MUST NOT trigger runtime changes.
- Labels MUST NOT override algorithmic output directly.
- Disagreements are data, not errors.
