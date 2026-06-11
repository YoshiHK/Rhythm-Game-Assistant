from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_JSON_PATH = Path(__file__).with_suffix(".json")

reason_taxonomy_v1: Dict[str, Any] = json.loads(
    _JSON_PATH.read_text(encoding="utf-8")
)

version: str = reason_taxonomy_v1.get("version", "")
fields: List[str] = list(reason_taxonomy_v1.get("fields", []))
enums: Dict[str, Any] = dict(reason_taxonomy_v1.get("enums", {}))
reason_codes: List[Dict[str, Any]] = list(reason_taxonomy_v1.get("reason_codes", []))

__all__ = [
    "reason_taxonomy_v1",
    "version",
    "fields",
    "enums",
    "reason_codes",
]