"""
Phase 5 — Offline Retrain & Model Ops

This package defines versioned dataset construction and model-ops support
for offline learning.

Primary contracts:
- training_dataset.schema.json
- model_validation.md
- model_registry.md
- promotion_and_rollback.md

Role:
- Construct versioned training datasets
- Preserve curator-labeled ground truth
- Support validation and model lifecycle workflows

Boundary:
- Does NOT affect runtime behavior
- Does NOT select active models
- Does NOT deploy or rollback models directly
"""

from .dataset_builder import (
    DatasetBuilderConfig,
    DatasetBuilderSummary,
    build_training_dataset,
)

__all__ = [
    "DatasetBuilderConfig",
    "DatasetBuilderSummary",
    "build_training_dataset",
]