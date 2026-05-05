## Metrics Catalog (Phase 5)

This document defines **canonical, non-semantic metrics**
used for evaluation and experimentation.

### Core Metrics

- **tip_view_rate**  
  Fraction of presented tips that are viewed.

- **tip_use_rate**  
  Fraction of tips followed by a relevant player action.

- **completion_improvement**  
  Change in completion success relative to baseline.

- **recommendation_accept_rate**  
  Fraction of recommendations accepted by players.

- **retry_success_rate**  
  Success rate after retry prompted by guidance.

### Metric Invariants

All metrics MUST:
- be linkable to provenance_id
- be comparable across time windows
- avoid per-user ranking or judgment
- remain interpretable without hidden thresholds

### Non‑Goals

Metrics MUST NOT:
- be used for runtime gating
- trigger automatic model changes
- assign blame or score to individual players
