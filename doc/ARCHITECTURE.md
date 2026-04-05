# System Architecture (Phases 1–7)

## 1) High-level placement

```
[ Phase 1–2 ]  Analysis & Tips Generation
      ↓
[ Phase 3 ]    Unified Ingestion Manager (UMI) — orchestration spine
      ↓
[ Phase 4 ]    Personalization & Presentation (non-destructive)
      ↓
[ Phase 4.5 ]  Localization (presentation-only)
      ↓
[ Phase 5 ]    Productionization & Offline Learning (contracts, APIs)
      ↓
[ Phase 6 ]    Platform Hardening (guards, reliability, compliance)
      ↓
[ UI / Softr ] Consumption surfaces
      ↘
       [ Phase 7 ] Games Recommendations (discovery layer)
```

## 2) Canonical data flow (Phase 1–2)
- Chart parsing → metrics/tags
- Tag → element candidates
- Severity/score/coverage
- Element selection
- Guidance filling
- Narrative rendering
- Per-chart and batch summary emission

Phase 2 Track A–D improves scoring/selection/guidance/narrative while preserving schema shapes.

## 3) UMI (Phase 3) orchestration flow
1. discover candidate files
2. detect game adapter
3. load & canonicalize
4. validate
5. governance checks
6. invoke Phase 1–2
7. persist canonical rows
8. accumulate batch enrichment
9. build batch summaries
10. emit structured run report

## 4) Phase 4 personalization chain
Decision gates → (optional model advisory outputs) → safe adjustments → narrative render → provenance

## 5) Phase 4.5 localization pipeline
Locale resolution → translation lookup → translation application → fallback handling → localization provenance

## 6) Phase 6 hardening integration
Phase 6 wraps Phase 5 systems and orchestrator execution with:
- retries/circuit breakers/idempotency and safe fallbacks
- security & compliance boundaries
- observability and alerting
- partner/API boundary enforcement

It integrates with the orchestrator extension layer (bridge/stabilizer), not by modifying the core orchestrator.

## 7) Phase 7 discovery integration
Phase 7 consumes stabilized outputs and produces ranked game recommendations with explanations and feedback signals.
Execution must be non-blocking and failure-isolated from core flows.

