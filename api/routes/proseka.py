from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

router = APIRouter(prefix='/api/v1/proseka', tags=['proseka'])


class UserInfo(BaseModel):
    user_id: str = Field(..., description='Opaque user id from Softr')
    email: Optional[str] = Field(None, description='User email from Softr (optional)')


class PlayerSignals(BaseModel):
    # Keep all numeric inputs as optional strings to avoid Softr JSON issues.
    expert_ap_count: Optional[str] = None
    expert_fc_count: Optional[str] = None
    master_ap_count: Optional[str] = None
    master_fc_count: Optional[str] = None
    expert_clear_rate: Optional[str] = None
    master_clear_rate: Optional[str] = None
    highest_confirmed_difficulty: Optional[str] = 'Expert'


class Preferences(BaseModel):
    variant: Optional[str] = 'expert'
    allow_personalization: bool = True


class Evidence(BaseModel):
    screenshot_url: Optional[str] = ''
    notes: Optional[str] = ''


class RecommendRequest(BaseModel):
    request_id: Optional[str] = None
    source: str = 'softr_workflow'
    game_id: str = 'proseka'
    locale: Optional[str] = 'en-US'
    user: UserInfo
    player_signals: PlayerSignals = Field(default_factory=PlayerSignals)
    preferences: Preferences = Field(default_factory=Preferences)
    evidence: Evidence = Field(default_factory=Evidence)
    client: Dict[str, Any] = Field(default_factory=dict)


@router.post('/recommend')
def recommend(req: RecommendRequest, authorization: str | None = Depends(auth_header)) -> Dict[str, Any]:
    """Proseka-only recommendation endpoint (thin layer).

    This endpoint is intentionally thin:
    - Validates Softr bearer token (service-to-service)
    - Accepts player performance signals
    - Returns a placeholder response structure expected by Softr

    Wire-in points (to be implemented in your main repo):
    - Phase 5 song recommendation contract
    - Tips DB lookup for precomputed tips_text + chart_summary
    - Phase 4/4.5 presentation/localization application

    NOTE: This file does NOT implement analysis (Phase 1–3) and must not trigger ingestion.
    """
    require_softr_bearer(authorization)

    # TODO: Replace with real Phase 5 recommendation + tips DB lookup.
    # Returning deterministic placeholder that preserves schema.
    return {
        'game_id': 'proseka',
        'user_id': req.user.user_id,
        'locale': req.locale or 'en-US',
        'recommended_songs': [
            {
                'song_id': 'PLACEHOLDER_SONG_1',
                'difficulty': req.player_signals.highest_confirmed_difficulty or 'Expert',
                'tips_text': 'PLACEHOLDER: tips will be fetched from Tips DB (precomputed by UMI).',
                'chart_summary': {},
                'provenance_id': 'prov_placeholder_1',
            },
            {
                'song_id': 'PLACEHOLDER_SONG_2',
                'difficulty': req.player_signals.highest_confirmed_difficulty or 'Expert',
                'tips_text': 'PLACEHOLDER: tips will be fetched from Tips DB (precomputed by UMI).',
                'chart_summary': {},
                'provenance_id': 'prov_placeholder_2',
            },
            {
                'song_id': 'PLACEHOLDER_SONG_3',
                'difficulty': req.player_signals.highest_confirmed_difficulty or 'Expert',
                'tips_text': 'PLACEHOLDER: tips will be fetched from Tips DB (precomputed by UMI).',
                'chart_summary': {},
                'provenance_id': 'prov_placeholder_3',
            },
        ],
    }
