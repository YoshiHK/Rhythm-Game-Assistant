"""
rhythm_ingestion.utils

Shared, game-agnostic utilities for the Unified Ingestion Manager (Phase 3).

This package contains helper modules that are safe to import across:
- ingestion runners
- batch QA tools
- orchestrators
- dry-run / testing pipelines

Utilities in this package MUST NOT:
- contain game-specific logic
- depend on adapters or validators
- implement gameplay or tips-generation logic
"""

from __future__ import annotations

# ----------------------------------------------------------------------
# File system utilities
# ----------------------------------------------------------------------
from .file_scan import (  # noqa: F401
    scan_directory,
    scan_many,
    DEFAULT_ALLOWED_EXTENSIONS,
)

# ----------------------------------------------------------------------
# Logging utilities
# ----------------------------------------------------------------------
from .logger import log  # noqa: F401

# ----------------------------------------------------------------------
# QA & reporting utilities
# ----------------------------------------------------------------------
from .qa_reporter import (  # noqa: F401
    QASummary,
)

__all__ = [
    # file_scan
    "scan_directory",
    "scan_many",
    "DEFAULT_ALLOWED_EXTENSIONS",
    # logger
    "log",
    # qa_reporter
    "QASummary",
]
