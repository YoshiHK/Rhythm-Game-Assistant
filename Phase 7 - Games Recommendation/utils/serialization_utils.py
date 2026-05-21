import json
from typing import Any


def ensure_json_safe(payload: Any) -> None:
    """
    Assert that payload is JSON-serializable.

    Raises:
        TypeError if not serializable.
    """
    json.dumps(payload)