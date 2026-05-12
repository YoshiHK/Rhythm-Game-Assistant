# Song Recommendation CI Tests (Phase 6)

## Purpose

This test suite enforces **platform‑level invariants** for the
Song Recommendation routing domain.

The goal is to ensure:
- Multi‑game safety
- Deterministic behavior
- Contract stability

## What These Tests Do

- Validate game capability fixtures
- Enforce ladder ordering invariants
- Check selector determinism
- Validate schema parseability
- Ensure coordinator integration stability

## What These Tests Do NOT Do

- Judge gameplay correctness
- Validate recommendation quality
- Test model performance
- Encode game‑specific semantics

## Design Philosophy

CI tests in Phase 6 exist to prevent:
- Silent regressions
- Game‑specific assumptions leaking into shared logic
- Unsafe expansions across games

Semantic correctness belongs to downstream phases.