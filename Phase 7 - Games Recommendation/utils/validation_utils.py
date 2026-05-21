from typing import Any, Optional


def require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def require_optional_str(value: Any, *, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or None")
    return value


def require_int(value: Any, *, field: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field} must be an int")
    return value


def require_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a bool")
    return value