"""rhythm_ingestion.orchestrator_ext.stabilizer

Stabilizer wrapper skeleton (retries + circuit breaker hooks).

Control-plane only; must not implement Phase 1/2/4 logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .config import CircuitBreakerPolicy, OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .interfaces import OrchestratorCoreProtocol
from .reason_codes import ReasonCode
from .types import RunContext, RunMode, Stage, compute_run_key


@dataclass
class InMemoryBreakerState:
    failures: Dict[str, int] = field(default_factory=dict)

    def _key(self, game_id: str, stage: Stage) -> str:
        return f"{game_id}:{stage.value}"

    def record_failure(self, game_id: str, stage: Stage) -> int:
        k = self._key(game_id, stage)
        self.failures[k] = int(self.failures.get(k, 0)) + 1
        return self.failures[k]

    def is_open(self, game_id: str, stage: Stage, policy: CircuitBreakerPolicy) -> bool:
        if not policy.enabled:
            return False
        return int(self.failures.get(self._key(game_id, stage), 0)) >= int(policy.open_after)


class OrchestratorStabilizer:
    def __init__(self, core: OrchestratorCoreProtocol, config: OrchestratorExtensionConfig):
        self.core = core
        self.config = config
        self.breaker_state = InMemoryBreakerState()

    def run(self, *, game_id: str, chart_path: str, mode: RunMode = RunMode.FULL, **kwargs: Any) -> Dict[str, Any]:
        flags: FeatureFlags = self.config.feature_flags
        ctx = RunContext(game_id=game_id, chart_id=str(chart_path), difficulty=kwargs.get("difficulty"), adapter_version=kwargs.get("adapter_version"), pipeline_version=kwargs.get("pipeline_version"), feature_flags_digest=flags.digest())
        run_key = compute_run_key(ctx)

        if flags.enable_circuit_breakers and self.breaker_state.is_open(game_id, Stage.INGEST, self.config.breaker_policy):
            return {"run_key": run_key, "game_id": game_id, "chart_id": str(chart_path), "mode": mode.value, "status": "STOP", "reason_code": ReasonCode.UNHANDLED_EXCEPTION.value, "details": {"breaker": "open", "stage": Stage.INGEST.value}}

        max_attempts = self.config.retry_policy.max_attempts if (flags.enable_retries and self.config.retry_policy.enabled) else 1
        attempt = 1
        last_exc: Optional[Exception] = None
        while attempt <= max_attempts:
            try:
                return self.core.run(game_id=game_id, chart_path=chart_path, mode=mode.value, **kwargs)
            except Exception as e:
                last_exc = e
                self.breaker_state.record_failure(game_id, Stage.INGEST)
                if attempt >= max_attempts:
                    break
                attempt += 1

        return {"run_key": run_key, "game_id": game_id, "chart_id": str(chart_path), "mode": mode.value, "status": "STOP", "reason_code": ReasonCode.UNHANDLED_EXCEPTION.value, "details": {"exception": str(last_exc) if last_exc else "unknown"}}
