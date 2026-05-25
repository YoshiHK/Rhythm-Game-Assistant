"""
CI Observability Layer — Public Interface

This module provides a stable import surface for CI observability tools.

Design principles:
- Phase-agnostic
- CI-only (never used at runtime)
- Safe imports (no side effects)
- Structured signal processing

Key responsibilities:
- Scrape CI SUMMARY signals
- Aggregate CI health
- Support external alerting
"""

__all__ = [
    "scrape_ci_summaries",
    "alert_ci_summary",
]