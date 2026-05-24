from __future__ import annotations

import os
from fastapi import Header, HTTPException, APIRouter

router = APIRouter(tags=["auth"])


def auth_header(authorization: str | None = Header(default=None)) -> str | None:
    """
    Extract Authorization header.

    This stays intentionally minimal and phase-safe.
    """
    return authorization


def require_softr_bearer(authorization: str | None) -> None:
    """
    Validate Softr service-to-service bearer token.

    Expected:
      Authorization: Bearer <API_KEY>

    Source of truth:
      Environment variable RGA_SOFTR_API_KEY

    Phase discipline:
      - Phase 6 boundary only
      - No downstream logic
    """

    expected = os.getenv("RGA_SOFTR_API_KEY", "").strip()

    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: RGA_SOFTR_API_KEY not set",
        )

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format",
        )

    token = authorization[len("Bearer "):].strip()

    if token != expected:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )