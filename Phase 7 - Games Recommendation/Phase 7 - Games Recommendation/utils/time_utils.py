from datetime import datetime, timezone


def now_utc_iso() -> str:
    """
    Return current UTC time in ISO-8601 format without microseconds.

    Example:
        2026-05-10T02:14:30+00:00
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
