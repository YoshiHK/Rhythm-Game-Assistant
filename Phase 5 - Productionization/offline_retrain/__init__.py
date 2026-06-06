"""
Phase 5 — Offline Retrain & Model Ops

This package defines versioned dataset construction and model-ops support
for offline learning.

## Primary Contracts

- training_dataset.schema.json
- model_validation.md
- model_registry.md

## Role

- Construct versioned training datasets
- Preserve curator-labeled ground truth
- Support validation and model lifecycle workflows
- Enable reproducible offline learning

## Primary API

- build_training_dataset() → construct training datasets
- DatasetBuilderConfig → configuration dataclass
- DatasetBuilderSummary → summary statistics dataclass

## What This Layer Does

- Construct versioned training datasets
- Execute offline training
- Run dual-axis evaluation:
  - outcome quality (selection)
  - reasoning quality (taxonomy alignment)
- Validate models
- Register artifacts

## What This Layer Does NOT Do

- ❌ Does NOT affect runtime behavior
- ❌ Does NOT select active models
- ❌ Does NOT deploy or rollback models directly
- ❌ Does NOT bypass Phase 6 governance

## Upstream Sources

- curator_gold → human truth labels
- feedback_aggregation → raw signals
- telemetry → performance metrics

## Downstream Outputs

- model_artifacts → trained models
- model_registry → artifact tracking
- evaluation_reports → quality assessment
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
