from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

router = APIRouter(prefix="/api/v1", tags=["recommend"])


class RecommendV1Request(BaseModel):
    game_id: str = Field(..., description="Game id, e.g. proseka")
    locale: str | None = Field("zh-HK", description="BCP-47 locale")

    player: dict = Field(
        default_factory=dict,
        description="Player identity info from Softr"
    )
    performance: dict = Field(
        default_factory=dict,
        description="Player performance submission"
    )
    evidence: dict = Field(
        default_factory=dict,
        description="Optional evidence (screenshots, notes)"
    )
    submission: dict = Field(
        default_factory=dict,
        description="Submission metadata"
    )

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "example": {
                "game_id": "proseka",
                "locale": "zh-Hant-HK",
                "player": {
                    "email": "player@example.com",
                    "player_name": "Test Player"
                },
                "performance": {
                    "expert": {
                        "ap": "12",
                        "fc": "20",
                        "clear": "30",
                        "reported_catalog_size": 625
                    },
                    "master": {
                        "ap": "3",
                        "fc": "10",
                        "clear": "15",
                        "reported_catalog_size": 625
                    },
                    "append": {
                        "ap": "1",
                        "fc": "2",
                        "clear": "5"
                    }
                },
                "evidence": {
                    "screenshot": {
                        "url": "https://example.com/screenshot.png",
                        "filename": "screenshot.png"
                    }
                },
                "submission": {
                    "submitted_at": "2026-04-05T17:20:00+08:00",
                    "client_timezone": "Asia/Hong_Kong"
                }
            }
        }
    }


@router.post("/recommend")
def recommend(req: RecommendV1Request, authorization: str | None = Depends(auth_header)) -> Dict[str, Any]:
    # Phase 6 boundary: Softr service-to-service auth
    require_softr_bearer(authorization)

    # Deterministic placeholder response (Phase-safe; does not trigger Phase 1–3)
    # Add fields that map cleanly into your Recommendation DB.
    return {
        "game_id": req.game_id,
        "locale": req.locale or "en-US",
        "player": req.player,
        "recommended_songs": [
            {
                "song_id": "PLACEHOLDER_SONG_1",
                "song_name": "PLACEHOLDER SONG 1",
                "producer": "PLACEHOLDER PRODUCER",
                "difficulty_level": "Expert",
                "difficulty_scale": 26,
                "recommendation_type": "AP",
                "reason": "PLACEHOLDER: reason/explanation will be computed by Phase 5/7 contracts.",
                "tips": "PLACEHOLDER: tips_text will be fetched from Tips DB (precomputed by UMI).",
                "rotation_order": 1,
            },
            {
                "song_id": "PLACEHOLDER_SONG_2",
                "song_name": "PLACEHOLDER SONG 2",
                "producer": "PLACEHOLDER PRODUCER",
                "difficulty_level": "Expert",
                "difficulty_scale": 27,
                "recommendation_type": "FC",
                "reason": "PLACEHOLDER: reason/explanation will be computed by Phase 5/7 contracts.",
                "tips": "PLACEHOLDER: tips_text will be fetched from Tips DB (precomputed by UMI).",
                "rotation_order": 2,
            },
            {
                "song_id": "PLACEHOLDER_SONG_3",
                "song_name": "PLACEHOLDER SONG 3",
                "producer": "PLACEHOLDER PRODUCER",
                "difficulty_level": "Expert",
                "difficulty_scale": 28,
                "recommendation_type": "Clear",
                "reason": "PLACEHOLDER: reason/explanation will be computed by Phase 5/7 contracts.",
                "tips": "PLACEHOLDER: tips_text will be fetched from Tips DB (precomputed by UMI).",
                "rotation_order": 3,
            },
        ],
    }