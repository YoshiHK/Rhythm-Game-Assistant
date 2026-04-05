from __future__ import annotations

import os
from fastapi import Header, HTTPException


def require_softr_bearer(authorization: str | None) -> None:
    """Validate Softr service-to-service bearer token.

    Softr sends: Authorization: Bearer {API_KEY}
    The expected key must be provided via env var RGA_SOFTR_API_KEY.

    This is a *platform boundary* (Phase 6 style): it authenticates Softr as a client.
    It must NOT be used to trigger analysis/ingestion; only consumption endpoints.
    """
    expected = os.getenv('RGA_SOFTR_API_KEY', '')
    if not expected:
        raise HTTPException(status_code=500, detail='Server misconfigured: RGA_SOFTR_API_KEY not set')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    token = authorization.removeprefix('Bearer ').strip()
    if token != expected:
        raise HTTPException(status_code=403, detail='Invalid API key')


def auth_header(authorization: str | None = Header(default=None)) -> str | None:
    return authorization
