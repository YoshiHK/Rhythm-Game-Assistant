"""
Phase 5 — Validator Package Exports

This package provides reusable offline validators for Phase 5.

Primary validators:
- schema_validator
- contract_validator
- determinism_validator
- coverage_validator
- artifact_integrity_validator
- metrics_guard_validator

Extended validators (NEW):
- contract_baseline_validator
- test_case_integrity_validator

Recommended usage:
- Python entry: validate_bundle.py
- PowerShell entry: call validate_bundle.py from batch scripts

Scope:
- offline only
- deterministic checks only
- no runtime mutation
- no deployment side effects
"""

# --------------------------------------------------
# Schema Validators
# --------------------------------------------------
from .schema_validator import (
    validate_feedback_event_shape,
    validate_curator_label_shape,
    validate_structured_event_batch,
)

# --------------------------------------------------
# Contract Validators
# --------------------------------------------------
from .contract_validator import (
    validate_entry_event_contract,
    validate_interpreted_output_contract,
    validate_curator_truth_contract,
    validate_contract_bundle,
)

# NEW: Contract Baseline Validator
from .contract_baseline_validator import (
    validate_contract_baseline_bundle,
)

# --------------------------------------------------
# Determinism Validators
# --------------------------------------------------
from .determinism_validator import (
    validate_object_pair,
    validate_json_file_pair,
    validate_named_artifact_pairs,
)

# --------------------------------------------------
# Coverage Validators
# --------------------------------------------------
from .coverage_validator import (
    validate_event_coverage,
    validate_interpretation_coverage,
    validate_artifact_coverage,
    validate_coverage_bundle,
)

# --------------------------------------------------
# Artifact Integrity Validators
# --------------------------------------------------
from .artifact_integrity_validator import (
    validate_artifact_file,
    validate_phase5_artifact_set,
    validate_pipeline_result_artifacts,
)

# --------------------------------------------------
# Metrics Validators
# --------------------------------------------------
from .metrics_guard_validator import (
    validate_drift,
    validate_regression,
    validate_deployment_gate,
    validate_metrics_guard_bundle,
)

# --------------------------------------------------
# NEW: Test Case Integrity Validator
# --------------------------------------------------
from .test_case_integrity_validator import (
    validate_test_case_integrity,
)

# --------------------------------------------------
# Bundle Entry
# --------------------------------------------------
from .validate_bundle import (
    run_validation_bundle,
)

# --------------------------------------------------
# Public API
# --------------------------------------------------
__all__ = [
    # Schema
    "validate_feedback_event_shape",
    "validate_curator_label_shape",
    "validate_structured_event_batch",

    # Contract (original)
    "validate_entry_event_contract",
    "validate_interpreted_output_contract",
    "validate_curator_truth_contract",
    "validate_contract_bundle",

    # Contract baseline (NEW)
    "validate_contract_baseline_bundle",

    # Determinism
    "validate_object_pair",
    "validate_json_file_pair",
    "validate_named_artifact_pairs",

    # Coverage
    "validate_event_coverage",
    "validate_interpretation_coverage",
    "validate_artifact_coverage",
    "validate_coverage_bundle",

    # Artifact
    "validate_artifact_file",
    "validate_phase5_artifact_set",
    "validate_pipeline_result_artifacts",

    # Metrics
    "validate_drift",
    "validate_regression",
    "validate_deployment_gate",
    "validate_metrics_guard_bundle",

    # Test case integrity (NEW)
    "validate_test_case_integrity",

    # Entry point
    "run_validation_bundle",
]