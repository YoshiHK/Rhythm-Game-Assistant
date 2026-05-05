from __future__ import annotations

"""<File>recommend.py</File>

Phase-safe recommendation endpoint (Song-level) with Phase 5/6 wiring.

## Phase alignment
- Phase 6 (Hardening): This endpoint is an **EXTERNAL trigger surface**.
  - Enforces Softr service-to-service auth.
  - Tags requests with a trigger envelope (record-only).
  - Does NOT schedule work.

- Phase 5 (Productionization): This endpoint returns a **read-only recommendation response**.
  - Includes rationale metadata per item.
  - Includes provenance_id and locale to anchor feedback/telemetry and presentation.
  - Does NOT perform live/online learning.
  - Does NOT modify Phase 1–4.5 semantics.

## Song Catalog interface contract (Phase 3 → API)
This API MUST NOT read the raw Song Database (e.g., Excel) at runtime.
It consumes a versioned, immutable catalog artefact produced by Phase 3 (UMI)
via a read-only SongCatalog interface.

## Client Event Taxonomy (Phase 5 Feedback / Telemetry)
This module defines the *client-side* event taxonomy for recommendation flows.
These events are observational (append-only) and must be linkable to provenance_id.

Event types (client):
- recommendation_viewed
- recommendation_item_clicked
- recommendation_accepted
- recommendation_dismissed
- recommendation_practice_started

Notes:
- This file provides contract definitions and a lightweight event ingestion stub.
- The ingestion stub intentionally ACKs only (no persistence/enforcement here).
"""

from typing import Any, Dict, Optional, Literal, List
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

router = APIRouter(prefix="/api/v1", tags=["recommend"])


# -----------------------------
# Helpers
# -----------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phase6_trigger_envelope(*, source: str = "softr") -> Dict[str, Any]:
    """Phase 6 trigger normalization (EXTERNAL).

    This endpoint is a partner/UI surface (Softr), therefore trigger_type=external.
    The envelope is record-only and must not be used to schedule or enforce here.
    """
    return {
        "trigger_type": "external",
        "source": source,
        "received_at": _utc_now_iso(),
    }


# -----------------------------
# Song Catalog Interface (contract)
# -----------------------------

class SongCatalog:
    """Read-only interface for canonical song metadata.

    Contract:
    - Backed by Phase 3 (UMI) canonicalized artefacts
    - Immutable, versioned, deterministic
    - No runtime mutation
    - No semantic or ranking logic

    Implementations may read from:
    - JSON / Parquet artefact
    - SQLite snapshot
    - Cached in-memory map

    The API MUST NOT read raw Excel song DB directly.
    """

    def get(self, song_id: str) -> Dict[str, Any]:
        """Return canonical metadata for song_id (empty dict if unknown)."""
        raise NotImplementedError


class InMemorySongCatalog(SongCatalog):
    """Minimal implementation loading a prebuilt catalog dict."""

    def __init__(self, catalog: Dict[str, Dict[str, Any]]):
        self._catalog = catalog

    def get(self, song_id: str) -> Dict[str, Any]:
        return self._catalog.get(song_id, {})


# Placeholder wiring (Phase-safe). Replace with Phase-3-produced artefact loader.
SONG_CATALOG: SongCatalog = InMemorySongCatalog(catalog={})


# -----------------------------
# Client Event Taxonomy (contract)
# -----------------------------

def _client_event_taxonomy() -> Dict[str, Any]:
    """Canonical client-side event taxonomy for recommendation flows."""

    common_required = [
        "event_id",
        "event_type",
        "timestamp",
        "provenance_id",
        "request_id",
        "response_id",
    ]

    return {
        "version": "v1",
        "principles": [
            "Observational only (no judgment)",
            "Append-only",
            "Linkable to provenance_id",
            "Deduplicate per response_id where specified",
        ],
        "events": {
            "recommendation_viewed": {
                "source_type": "client",
                "description": "Recommendation list rendered on screen (first exposure).",
                "emit_when": "After /recommend response is received AND list is first rendered.",
                "dedupe_key": "response_id",
                "required_fields": common_required + ["visible_song_ids"],
                "optional_fields": ["ui_surface", "client_version"],
            },
            "recommendation_item_clicked": {
                "source_type": "client",
                "description": "User clicked/tapped a recommended item (navigation intent).",
                "emit_when": "On click/tap of a song card in the recommendation list.",
                "dedupe_key": None,
                "required_fields": common_required + ["song_id"],
                "optional_fields": ["ui_surface", "client_version"],
            },
            "recommendation_accepted": {
                "source_type": "client",
                "description": "User explicitly accepted a recommendation (e.g., add to play queue).",
                "emit_when": "When user confirms they will play/queue the recommended song.",
                "dedupe_key": None,
                "required_fields": common_required + ["song_id"],
                "optional_fields": ["accept_mode", "client_version"],
            },
            "recommendation_dismissed": {
                "source_type": "client",
                "description": "User dismissed the recommendation list or a specific item.",
                "emit_when": "When user closes list without acceptance OR hides an item.",
                "dedupe_key": None,
                "required_fields": common_required,
                "optional_fields": ["song_id", "dismiss_reason", "client_version"],
            },
            "recommendation_practice_started": {
                "source_type": "client",
                "description": "User started practice flow from a recommended item.",
                "emit_when": "When user enters practice mode driven by a recommended song.",
                "dedupe_key": None,
                "required_fields": common_required + ["song_id"],
                "optional_fields": ["practice_mode", "client_version"],
            },
        },
    }


def _build_viewed_event_template(
    *,
    provenance_id: Optional[str],
    request_id: str,
    response_id: str,
    game_id: str,
    visible_song_ids: List[str],
) -> Dict[str, Any]:
    """Ready-to-emit recommendation_viewed template."""
    return {
        "event_id": "<uuid>",
        "event_type": "recommendation_viewed",
        "source_type": "client",
        "timestamp": "<iso-utc>",
        "provenance_id": provenance_id,
        "request_id": request_id,
        "response_id": response_id,
        "payload": {
            "game_id": game_id,
            "visible_song_ids": visible_song_ids,
            "ui_surface": "recommendation_list",
            "client_version": "<client-version>",
        },
    }


# -----------------------------
# API Models
# -----------------------------

class RecommendV1Request(BaseModel):
    game_id: str = Field(..., description="Game id, e.g. proseka")
    locale: Optional[str] = Field("zh-HK", description="BCP-47 locale")

    # Phase 4 provenance linkage (optional but strongly recommended)
    provenance_id: Optional[str] = Field(None, description="Phase 4 provenance identifier (optional)")

    # Softr-provided identity
    player: dict = Field(default_factory=dict, description="Player identity info from Softr")

    # Player self-reported performance submission
    performance: dict = Field(default_factory=dict, description="Player performance submission")

    # Optional evidence (screenshots, notes)
    evidence: dict = Field(default_factory=dict, description="Optional evidence (screenshots, notes)")

    # Submission metadata (client timestamp, timezone, etc.)
    submission: dict = Field(default_factory=dict, description="Submission metadata")

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "example": {
                "game_id": "proseka",
                "locale": "zh-Hant-HK",
                "provenance_id": "PROV_PLACEHOLDER",
                "player": {"email": "player@example.com", "player_name": "Test Player"},
                "performance": {
                    "expert": {"ap": "12", "fc": "20", "clear": "30", "reported_catalog_size": 625},
                    "master": {"ap": "3", "fc": "10", "clear": "15", "reported_catalog_size": 625},
                    "append": {"ap": "1", "fc": "2", "clear": "5"},
                },
                "evidence": {"screenshot": {"url": "https://example.com/screenshot.png", "filename": "screenshot.png"}},
                "submission": {"submitted_at": "2026-04-05T17:20:00+08:00", "client_timezone": "Asia/Hong_Kong"},
            }
        },
    }


ClientEventType = Literal[
    "recommendation_viewed",
    "recommendation_item_clicked",
    "recommendation_accepted",
    "recommendation_dismissed",
    "recommendation_practice_started",
]


class RecommendClientEventV1(BaseModel):
    """Client-side telemetry/feedback event for Phase 5 aggregation."""

    event_id: str = Field(..., description="Client-generated UUID")
    event_type: ClientEventType = Field(..., description="Recommendation client event type")
    timestamp: str = Field(..., description="ISO datetime string")

    provenance_id: Optional[str] = Field(None, description="Phase 4 provenance identifier")
    request_id: str = Field(..., description="/recommend request_id")
    response_id: str = Field(..., description="/recommend response_id")

    song_id: Optional[str] = Field(None, description="Song id for item-specific events")
    payload: dict = Field(default_factory=dict, description="Non-judgmental event payload")

    model_config = {"extra": "allow"}


# -----------------------------
# Endpoints
# -----------------------------

@router.post("/recommend")
def recommend(req: RecommendV1Request, authorization: Optional[str] = Depends(auth_header)) -> Dict[str, Any]:
    """Return a deterministic, read-only recommendation response."""

    require_softr_bearer(authorization)

    trigger = _phase6_trigger_envelope(source="softr")

    request_id = str(uuid4())
    response_id = str(uuid4())

    # Deterministic placeholder recommendations (no Phase 1–3 triggers)
    base = [
        ("PLACEHOLDER_SONG_1", 26, "AP", 1),
        ("PLACEHOLDER_SONG_2", 27, "FC", 2),
        ("PLACEHOLDER_SONG_3", 28, "Clear", 3),
    ]

    recommended_songs: List[Dict[str, Any]] = []
    for song_id, scale, rec_type, order in base:
        meta = SONG_CATALOG.get(song_id)
        recommended_songs.append(
            {
                "song_id": song_id,
                "song_name": meta.get("song_name") or meta.get("title") or f"{song_id}",
                "producer": meta.get("producer") or meta.get("artist") or "UNKNOWN",
                "difficulty_level": "Expert",
                "difficulty_scale": scale,
                "recommendation_type": rec_type,
                "rationale": "PLACEHOLDER: rationale will be produced by Phase 5 recommendation contracts.",
                # Backward-compatible alias
                "reason": "PLACEHOLDER: rationale will be produced by Phase 5 recommendation contracts.",
                "tips": "PLACEHOLDER: tips_text will be fetched from Tips DB (precomputed by UMI).",
                "rotation_order": order,
            }
        )

    visible_song_ids = [s["song_id"] for s in recommended_songs]

    return {
        "request_id": request_id,
        "response_id": response_id,
        "generated_at": _utc_now_iso(),
        "game_id": req.game_id,
        "locale": req.locale or "en-US",
        "provenance_id": req.provenance_id,
        "player": req.player,
        "trigger": trigger,
        "recommended_songs": recommended_songs,
        "request_context": {
            "provenance_id": req.provenance_id,
            "performance": req.performance,
            "evidence": req.evidence,
            "submission": req.submission,
        },
        "client_event_taxonomy": _client_event_taxonomy(),
        "client_event_templates": {
            "recommendation_viewed": _build_viewed_event_template(
                provenance_id=req.provenance_id,
                request_id=request_id,
                response_id=response_id,
                game_id=req.game_id,
                visible_song_ids=visible_song_ids,
            )
        },
    }


@router.post("/recommend/events")
def ingest_recommend_client_event(
    evt: RecommendClientEventV1,
    authorization: Optional[str] = Depends(auth_header),
) -> Dict[str, Any]:
    """ACK-only ingestion of client-side recommendation events (Phase 5).

    Intentionally no persistence/enforcement in this module.
    """

    require_softr_bearer(authorization)

    return {
        "status": "accepted",
        "event_id": evt.event_id,
        "event_type": evt.event_type,
        "provenance_id": evt.provenance_id,
        "received_at": _utc_now_iso(),
    }
