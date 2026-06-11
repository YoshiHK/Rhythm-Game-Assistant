from __future__ import annotations
import os
from typing import Optional
from fastapi import Header, HTTPException, APIRouter

router = APIRouter(tags=["auth"])


def auth_header(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """
    Extract Authorization header.
    """
    return authorization


def require_softr_bearer(authorization: Optional[str]) -> None:
    """
    Validate Softr service-to-service bearer token.

    Expected format:
    Authorization: Bearer <TOKEN>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "").strip()

    expected = os.getenv("SOFTR_API_TOKEN")

    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")
``