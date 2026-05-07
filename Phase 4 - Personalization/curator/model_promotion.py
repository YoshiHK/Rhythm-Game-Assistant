#!/usr/bin/env python3
from __future__ import annotations

"""
model_promotion.py

Phase 4 — Model Promotion (manual, reversible).

Stages:
- staging
- canary
- production

Promotion is:
- human-approved
- offline
- reversible
"""

import json
from typing import Dict


ALLOWED_STAGES = {"staging", "canary", "production"}


def promote_model(
    *,
    model_artifact_path: str,
    stage: str,
) -> Dict[str, str]:
    """
    Promote a trained model artifact to a given stage.

    Returns a promotion record for audit.
    """

    if stage not in ALLOWED_STAGES:
        raise ValueError(f"Invalid stage: {stage}")

    with open(model_artifact_path, "r", encoding="utf-8") as f:
        artifact: Dict = json.load(f)

    record = {
        "model_id": artifact.get("model_id"),
        "model_version": artifact.get("model_version"),
        "promoted_to": stage,
        "status": "promoted",
    }

    return record


__all__ = ["promote_model"]