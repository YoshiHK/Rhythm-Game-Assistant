"""
Health Metrics

Defines canonical, non-semantic system health metrics for Phase 6.

This module defines metric SHAPES only.
It does not collect, aggregate, or alert.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HealthMetrics:
    """
    Immutable snapshot of system health signals.
    """

    # Scan-related
    last_scan_timestamp: Optional[str] = None
    scan_age_seconds: Optional[int] = None
    unscanned_candidate_count: Optional[int] = None

    # Execution-related
    last_ingestion_timestamp: Optional[str] = None
    ingestion_error_rate: Optional[float] = None

    # System-level
    availability: Optional[float] = None
    latency_ms_p95: Optional[int] = None
