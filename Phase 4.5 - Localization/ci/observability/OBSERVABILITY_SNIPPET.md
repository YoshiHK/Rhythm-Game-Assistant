### Observability hook: CI SUMMARY scraping (Phase 6 wiring)

This document describes an **optional observability hook** that allows
Phase‑6‑style tooling to scrape CI SUMMARY lines and emit structured artifacts
for dashboards and alerts.

Important constraints:

- CI SUMMARY scraping is **observational only**
- It does **NOT** gate CI pass/fail decisions
- It does **NOT** affect runtime execution
- It does **NOT** influence Phase 4.5 or Phase 6 behavior

Purpose:
- Improve visibility into CI trends
- Enable alerting on repeated policy violations
- Support long‑term governance and maintenance

Example:

python ci/check_token_parity_per_string.py \
  | tee CI/logs/token_parity.log

python scripts/observability/scrape_ci_summaries.py \
  --log CI/logs/token_parity.log \
  --out CI/artifacts
  
Outputs:

CI/artifacts/ci_summary_events.jsonl
CI/artifacts/ci_summary_aggregate.json