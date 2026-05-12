# Game Capability Fixtures (Phase 6)

## Purpose

This directory contains **game capability fixtures** used by the
Phase 6 Song Recommendation routing domain.

Each fixture defines the **mechanical capability surface** of a rhythm game,
including:
- Difficulty tier ordering
- Completion ladder ordering
- Canonical aliases for normalization

These fixtures are the **only source of truth** for game-specific ordering
used by Phase 6.

## What a Game Capability Fixture Is

A game capability fixture describes:
- Which difficulty tiers exist for a game
- Their relative ordering (lowest → highest)
- Which completion states exist and how they are ordered

It does NOT describe:
- Gameplay semantics
- Chart mechanics
- Player skill expectations
- Difficulty meaning beyond ordering

Phase 6 treats all tier and completion labels as **opaque strings**
with a defined order.

## Design Constraints

All fixtures in this directory MUST follow these rules:

- `game_id` must be a stable, unique string
- `difficulty_tiers` must be:
  - A non-empty list
  - Deterministically ordered
  - Free of duplicates
- `completion_ladder` must be:
  - A list of length ≥ 2
  - Deterministically ordered
- Aliases may be provided for ingestion normalization,
  but canonical keys must remain stable

These constraints are enforced by CI.

## Scope and Responsibility Boundaries

Game capability fixtures are used by:
- `game_capability_resolver.py`
- Deterministic selection and window-widening logic
- Coordinator-level recommendation assembly

They MUST NOT be used to:
- Infer gameplay difficulty
- Rank charts semantically
- Model player capability
- Encode heuristics or assumptions

All semantic interpretation belongs to downstream phases.

## Notes on Evolution

- Adding a new game requires adding a new fixture file
- Changing tier ordering is a **breaking change** and must be intentional
- Game-specific hard invariants should be enforced via CI tests,
  not via runtime logic

Phase 6 remains a coordination and policy layer only.