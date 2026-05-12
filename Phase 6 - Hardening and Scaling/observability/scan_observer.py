"""
Scan Observer (Phase 6)

Observes scan-state artifacts and derives non-semantic health metrics.

This module:
- READS scan_state
- EMITS HealthMetrics
- DOES NOT block execution
- DOES NOT trigger alerts
"""

from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from .health_metrics import HealthMetrics


class ScanObserver:
    """
    Produces scan-related health metrics from scan_state artifacts.
    """

    def observe(
        self,
        *,
        latest_scan_state_path: Optional[Path],
        unscanned_candidate_count: Optional[int] = None,
    ) -> HealthMetrics:
        """
        Observe scan-state freshness and candidate coverage.

        Parameters:
        - latest_scan_state_path: path to most recent scan_state file
        - unscanned_candidate_count: derived elsewhere (optional)

        Returns:
        - HealthMetrics snapshot
        """
        last_scan_ts = None
        scan_age_seconds = None

        if latest_scan_state_path and latest_scan_state_path.exists():
            mtime = latest_scan_state_path.stat().st_mtime
            last_scan_ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            scan_age_seconds = int(
                (datetime.now(timezone.utc).timestamp() - mtime)
            )

        return HealthMetrics(
            last_scan_timestamp=last_scan_ts,
            scan_age_seconds=scan_age_seconds,
            unscanned_candidate_count=unscanned_candidate_count,
        )
