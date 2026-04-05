# Feedback Collector

Responsibilities:
- Ingest feedback events from UI / Softr / API
- Validate against schema
- Persist events in append-only storage

Notes:
- This module MUST NOT make decisions
- This module MUST NOT aggregate or score feedback
- All interpretation happens offline
