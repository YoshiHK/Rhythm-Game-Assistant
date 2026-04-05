## Observability hook: CI SUMMARY scraping (Phase 6 wiring)

A Phase‑6‑style observability hook is provided to scrape `CI SUMMARY:` lines across runs
and emit structured artifacts for dashboards/alerts:

- `scripts/observability/scrape_ci_summaries.py`

Outputs:
- `CI/artifacts/ci_summary_events.jsonl`
- `CI/artifacts/ci_summary_aggregate.json`

Example:
```bash
python ci/check_token_parity_per_string.py | tee CI/logs/token_parity.log
python scripts/observability/scrape_ci_summaries.py --log CI/logs/token_parity.log --out CI/artifacts
```
