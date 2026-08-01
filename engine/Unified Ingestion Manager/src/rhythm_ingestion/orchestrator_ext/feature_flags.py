"""
rhythm_ingestion.orchestrator_ext.feature_flags

Feature flags for additive orchestrator extensions.
Default values MUST preserve existing orchestrator behavior.

Policy:
- Defaults are all False (thin pass-through)
- Flags are control-plane toggles; no gameplay semantics
- No versioning / runtime version switching
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


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

    def as_dict(self) -> Dict[str, bool]:
        return {
            "enable_run_plan": bool(self.enable_run_plan),
            "enable_preflight_checks": bool(self.enable_preflight_checks),
            "enable_capability_matrix": bool(self.enable_capability_matrix),
            "enable_reasoned_gates": bool(self.enable_reasoned_gates),
            "enable_idempotency": bool(self.enable_idempotency),
            "enable_retries": bool(self.enable_retries),
            "enable_circuit_breakers": bool(self.enable_circuit_breakers),
            "enable_safe_fallbacks": bool(self.enable_safe_fallbacks),
            "enable_schema_precheck": bool(self.enable_schema_precheck),
            "enable_run_report": bool(self.enable_run_report),
            "enable_metrics": bool(self.enable_metrics),
        }

    def any_enabled(self) -> bool:
        """True if ANY known flag is enabled."""
        return any(self.as_dict().values())

    def digest(self) -> str:
        """
        Return a stable digest string (suitable for hashing) for RunKey.
        This is deterministic and order-stable.
        """
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


__all__ = ["FeatureFlags"]