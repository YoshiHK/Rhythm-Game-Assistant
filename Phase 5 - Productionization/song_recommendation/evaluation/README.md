# Phase 5 — Song Recommendation Evaluation Layer

## Purpose

The Evaluation Layer measures whether Song Recommendation learning outcomes
improve selection quality **offline**, and enforces **regression guards**
before any deployment rollout.

Per the Phase 5 Song Recommendation learning spec, evaluation MUST include:
- acceptance rate deltas
- play-through rate changes
- completion rate deltas
- regression guards against quality drops

This layer is offline-only, deterministic, and non-semantic. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

---

## Phase Boundary

- **Upstream:** Features Layer output (selection-level feature rows)
- **Downstream:** Training reports, promotion/rollback decisions, deployment gating
- **Runtime impact:** None (deployment only)

This layer must never be imported by Phase 6 runtime.

---

## Non‑Negotiable Boundaries

This layer MUST:
- operate offline (Phase 5 only)
- remain deterministic and auditable
- evaluate selection-level outcomes only
- enforce regression guards before rollout

This layer MUST NOT:
- consume tips content, taxonomy, severity, or narrative fields
- infer gameplay meaning
- perform runtime adaptation or tuning
- create feedback loops into Phase 6 directly

Any semantic leakage invalidates the evaluation by definition. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

---

## Inputs

Inputs are selection-level feature rows containing safe signals such as:
- `rank`
- `final_outcome` / `outcome_score`
- `any_accept_or_better`, `any_played_or_better`, `any_completed`
- action counts and bounded context fields

No gameplay semantic fields are allowed.

---

## Outputs

This layer produces:
- a deterministic evaluation report (`metrics`)
- optional baseline comparison (`deltas`)
- regression guard results (`pass/fail` + reasons)

These outputs are used to decide:
- whether to promote learned parameters
- whether to rollback or hold deployment

---

## Metrics (Examples)

- Overall rates:
  - accept_or_better_rate
  - played_or_better_rate
  - completed_rate
  - mean_outcome_score

- Rank cut metrics:
  - accept_at_1 / accept_at_3 / accept_at_5
  - played_at_k, completed_at_k

---

## Regression Guards

Regression guards compare current metrics against baseline metrics.
If data volume is insufficient, guards may be skipped explicitly.

Guards must be:
- explicit
- bounded
- deterministic
- explainable

No silent promotion is allowed. 