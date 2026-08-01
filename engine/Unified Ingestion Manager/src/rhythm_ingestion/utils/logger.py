from __future__ import annotations
"""[logger.py]
Phase 3 (UMI) logging utility.

Control-plane only:
- Lightweight, dependency-free logging.
- Safe to import from runners, orchestrators, and QA utilities.
- Must not introduce gameplay semantics.

Notes:
- Minimal stdout logger by default.
- Callers may override `sink` for tests/CI capture.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Logger:
    prefix: str = "INGEST"
    sink: Callable[[str], None] = print
    enabled: bool = True

    def _emit(self, level: str, msg: str) -> None:
        if not self.enabled:
            return
        self.sink(f"[{self.prefix}][{level}][{utc_now_iso()}] {msg}")

    def info(self, msg: str) -> None:
        self._emit("INFO", msg)

    def warn(self, msg: str) -> None:
        self._emit("WARN", msg)

    def error(self, msg: str) -> None:
        self._emit("ERROR", msg)


# Backwards-compatible helper
_default_logger: Optional[Logger] = Logger()


def log(msg: str) -> None:
    """Backwards compatible: `log(\"...\")` emits INFO."""
    (_default_logger or Logger()).info(msg)


__all__ = ["Logger", "log", "utc_now_iso"]