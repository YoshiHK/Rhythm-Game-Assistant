"""
rhythm_ingestion.utils
Shared, game-agnostic utilities for the Unified Ingestion Manager (Phase 3).

Utilities in this package MUST NOT:
- contain game-specific logic
- depend on adapters or validators
- implement gameplay or tips-generation logic
"""

from __future__ import annotations

# ------------------------------
# File system / scan utilities
# ------------------------------
from .file_scan import (  # noqa: F401
    scan_directory,
    scan_many,
    DEFAULT_ALLOWED_EXTENSIONS,
)

# ------------------------------
# Logging utilities
# ------------------------------
from .logger import Logger, log, utc_now_iso  # noqa: F401

# ------------------------------
# QA & reporting utilities
# ------------------------------
from .qa_reporter import QASummary  # noqa: F401

# ------------------------------
# Paired artefact integrity (control-plane)
# ------------------------------
from .paired_integrity import (  # noqa: F401
    canonical_dumps,
    compute_content_hash_sha256,
    stamp_integrity,
    verify_integrity,
    verify_pairing,
)

# ------------------------------
# Optional: filename scenario engine (if present)
# ------------------------------
try:  # noqa: SIM105
    from .file_scan_scenarios import (  # type: ignore # noqa: F401
        FileScanScenarioEngine,
        ParsedFilename,
        ScanResult,
        ScanStatus,
        ScenarioType,
        scan_directory_and_match,
        scan_many_and_match,
    )
except Exception:  # pragma: no cover
    FileScanScenarioEngine = None  # type: ignore
    ParsedFilename = None  # type: ignore
    ScanResult = None  # type: ignore
    ScanStatus = None  # type: ignore
    ScenarioType = None  # type: ignore
    scan_directory_and_match = None  # type: ignore
    scan_many_and_match = None  # type: ignore


__all__ = [
    # file_scan
    "scan_directory",
    "scan_many",
    "DEFAULT_ALLOWED_EXTENSIONS",
    # logger
    "Logger",
    "log",
    "utc_now_iso",
    # qa_reporter
    "QASummary",
    # paired_integrity
    "canonical_dumps",
    "compute_content_hash_sha256",
    "stamp_integrity",
    "verify_integrity",
    "verify_pairing",
    # file_scan_scenarios (optional)
    "FileScanScenarioEngine",
    "ParsedFilename",
    "ScanResult",
    "ScanStatus",
    "ScenarioType",
    "scan_directory_and_match",
    "scan_many_and_match",
]