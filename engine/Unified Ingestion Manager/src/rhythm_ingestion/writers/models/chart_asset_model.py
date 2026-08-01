from __future__ import annotations

"""
chart_asset_model.py

Canonical data model for persisted chart assets.

Design intent
-------------
- type_A = deterministic, embeddable asset content (native chart files / web-exported chart)
- type_B = external/reference asset (video, URL, web reference)
- Keep localization / personalization / rendered tips OUT of this model
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, Optional


class AssetType(str, Enum):
    TYPE_A = "type_A"  # embeddable / deterministic text asset
    TYPE_B = "type_B"  # reference asset (video/url)


class AssetSubtype(str, Enum):
    AFF = "aff"
    SUS = "sus"
    JSON = "json"
    HTML = "html"
    MHT = "mht"
    TEXT = "text"
    YOUTUBE = "youtube"
    VIDEO_FILE = "video_file"
    EXTERNAL_URL = "external_url"
    UNKNOWN = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ChartAsset:
    asset_id: str

    candidate_id: Optional[str] = None
    run_id: Optional[str] = None

    game_normalized: Optional[str] = None
    difficulty_normalized: Optional[str] = None
    level_normalized: Optional[int] = None

    asset_type: str = AssetType.TYPE_A.value
    asset_subtype: Optional[str] = None

    text_representation: Optional[str] = None
    reference_url: Optional[str] = None

    content_sha256: Optional[str] = None
    conversion_version: int = 1
    embedded_at: str = field(default_factory=utc_now_iso)

    source_path: Optional[str] = None
    basename: Optional[str] = None
    extension: Optional[str] = None

    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.asset_id:
            raise ValueError("asset_id is required")

        if self.asset_type not in {AssetType.TYPE_A.value, AssetType.TYPE_B.value}:
            raise ValueError(f"unsupported asset_type: {self.asset_type}")

        if self.asset_type == AssetType.TYPE_A.value:
            if not self.text_representation:
                raise ValueError("type_A asset requires text_representation")
        elif self.asset_type == AssetType.TYPE_B.value:
            if not self.reference_url:
                raise ValueError("type_B asset requires reference_url")

    def to_record(self) -> Dict[str, Any]:
        self.validate()
        out = asdict(self)
        out["extra_metadata_json"] = json.dumps(self.extra_metadata or {}, ensure_ascii=False, sort_keys=True)
        out.pop("extra_metadata", None)
        return out

    @classmethod
    def from_record(cls, row: Dict[str, Any]) -> "ChartAsset":
        meta = row.get("extra_metadata_json")
        try:
            extra_metadata = json.loads(meta) if meta else {}
        except Exception:
            extra_metadata = {}

        return cls(
            asset_id=row.get("asset_id"),
            candidate_id=row.get("candidate_id"),
            run_id=row.get("run_id"),
            game_normalized=row.get("game_normalized"),
            difficulty_normalized=row.get("difficulty_normalized"),
            level_normalized=row.get("level_normalized"),
            asset_type=row.get("asset_type"),
            asset_subtype=row.get("asset_subtype"),
            text_representation=row.get("text_representation"),
            reference_url=row.get("reference_url"),
            content_sha256=row.get("content_sha256"),
            conversion_version=int(row.get("conversion_version") or 1),
            embedded_at=row.get("embedded_at") or utc_now_iso(),
            source_path=row.get("source_path"),
            basename=row.get("basename"),
            extension=row.get("extension"),
            extra_metadata=extra_metadata,
        )


__all__ = [
    "AssetType",
    "AssetSubtype",
    "ChartAsset",
    "utc_now_iso",
]
