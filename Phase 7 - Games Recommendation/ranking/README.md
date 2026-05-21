## Phase 7 — Ranking Layer

This directory implements the **single authoritative ranking logic**
for Phase 7 — Games Recommendations.

The ranking layer determines **which games are recommended and in what order**,
based on player context and game metadata.

---

## Design Constraints (Non-Negotiable)

The ranking layer MUST be:

- **Downstream-only**  
  MUST NOT trigger analysis, ingestion, or training.

- **Non-semantic**  
  MUST NOT change tips meaning or upstream semantics.

- **Deterministic**  
  Same inputs MUST always produce the same outputs.

- **Explainable**  
  Emits structured, bounded reasons suitable for explanation and audit.

- **No I/O**  
  Performs no file, network, or database access at runtime.

---

## Learning Loop Contract

The ranking layer **supports evolution**, but **never runtime adaptation**.

### Allowed

- Offline learning and calibration in **Phase 5**
- Updating static ranking parameters
- Updating the ranking implementation via deployment
- Reversible rollout and rollback

### Explicitly Forbidden

- Runtime learning or parameter tuning
- Consuming feedback events directly
- Dynamic version switching
- Non-deterministic behavior

All learning outcomes must be **compiled into the deployed code or parameters**.

---

## Runtime Rule

There is exactly **one authoritative ranking implementation** at runtime.

Ranking behavior must not vary by:
- request
- session
- time
- feedback state

---

## Outputs

The ranker returns **contract-shaped recommendation items** suitable for:
- routing
- explanation generation
- feedback exposure context
- observability

Ranking outputs are safe to analyze offline but must not influence
runtime behavior beyond deterministic execution.

---

## Design Intent

This layer exists to make Game Recommendations **safe to evolve**
without making them **unsafe to run**.

Learning is allowed.
Runtime adaptation is not.

---

**End of Phase 7 Ranking Layer README**