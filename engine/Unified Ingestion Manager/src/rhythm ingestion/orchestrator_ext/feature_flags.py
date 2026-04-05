"""rhythm_ingestion.orchestrator_ext.feature_flags

Feature flags for additive orchestrator extensions.

Default values MUST preserve existing orchestrator behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureFlags:
    # Booster
    enable_run_plan: bool = False
    enable_preflight_checks: bool = False
    enable_capability_matrix: bool = False
    enable_reasoned_gates: bool = False

    # Stabilizer
    enable_idempotency: bool = False
    enable_retries: bool = False
    enable_circuit_breakers: bool = False
    enable_safe_fallbacks: bool = False
    enable_schema_precheck: bool = False

    # Observability
    enable_run_report: bool = False
    enable_metrics: bool = False

    def digest(self) -> str:
        """Return a stable digest string (suitable for hashing) for RunKey."""
        items = [
            ("run_plan", self.enable_run_plan),
            ("preflight", self.enable_preflight_checks),
            ("cap_matrix", self.enable_capability_matrix),
            ("gates", self.enable_reasoned_gates),
            ("idempotency", self.enable_idempotency),
            ("retries", self.enable_retries),
            ("breakers", self.enable_circuit_breakers),
            ("fallbacks", self.enable_safe_fallbacks),
            ("schema", self.enable_schema_precheck),
            ("report", self.enable_run_report),
            ("metrics", self.enable_metrics),
        ]
        return ";".join(f"{k}={1 if v else 0}" for k, v in items)
