"""
rhythm_ingestion.orchestrator_ext.stabilizer
Stabilizer wrapper (retries + circuit breaker hooks).

Control-plane only; must not implement Phase 1/2/4 logic.
No I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List

from .config import CircuitBreakerPolicy, OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .interfaces import OrchestratorCoreProtocol
from .reason_codes import ReasonCode
from .types import (
    RunContext,
    RunMode,
    Stage,
    StageStatus,
    GateDecision,
    GateResult,
    StageResult,
    RunReport,
    coerce_run_mode,
    compute_run_key,
)


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
    """
    Wraps a core orchestrator and provides optional:
    - circuit breaker
    - retries
    - safe fallback STOP reports (control-plane only)

    Bridge compatibility:
    - run(..., mode: str) boundary
    """

    def __init__(self, *, core: OrchestratorCoreProtocol, config: OrchestratorExtensionConfig):
        self.core = core
        self.config = config
        self.breaker_state = InMemoryBreakerState()

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        flags: FeatureFlags = self.config.feature_flags

        run_mode: RunMode = coerce_run_mode(mode)

        ctx = RunContext(
            game_id=str(game_id),
            chart_id=str(chart_path),
            difficulty=kwargs.get("difficulty"),
            adapter_version=kwargs.get("adapter_version"),
            pipeline_version=kwargs.get("pipeline_version"),
            feature_flags_digest=flags.digest(),
        )
        run_key = compute_run_key(ctx)

        # Circuit breaker (Stage.INGEST is the first control-plane gate)
        if flags.enable_circuit_breakers and self.breaker_state.is_open(
            str(game_id),
            Stage.INGEST,
            self.config.breaker_policy,
        ):
            return self._stop_report(
                run_key=run_key,
                game_id=str(game_id),
                chart_id=str(chart_path),
                mode=run_mode,
                stage=Stage.INGEST,
                reason=ReasonCode.CIRCUIT_OPEN,
                details={"breaker": "open", "stage": Stage.INGEST.value},
            )

        # Retry policy
        max_attempts = (
            int(self.config.retry_policy.max_attempts)
            if (flags.enable_retries and self.config.retry_policy.enabled)
            else 1
        )

        attempt = 1
        last_exc: Optional[Exception] = None

        while attempt <= max_attempts:
            try:
                # Pass-through to core; keep boundary mode as string
                return self.core.run(
                    game_id=str(game_id),
                    chart_path=str(chart_path),
                    mode=str(mode),
                    **kwargs,
                )
            except Exception as e:
                last_exc = e
                self.breaker_state.record_failure(str(game_id), Stage.INGEST)

                if attempt >= max_attempts:
                    break
                attempt += 1

        # Exhausted retries (or single failure)
        return self._stop_report(
            run_key=run_key,
            game_id=str(game_id),
            chart_id=str(chart_path),
            mode=run_mode,
            stage=Stage.INGEST,
            reason=ReasonCode.RETRY_EXHAUSTED if max_attempts > 1 else ReasonCode.UNHANDLED_EXCEPTION,
            details={"exception": str(last_exc) if last_exc else "unknown", "attempts": max_attempts},
        )

    def _stop_report(
        self,
        *,
        run_key: str,
        game_id: str,
        chart_id: str,
        mode: RunMode,
        stage: Stage,
        reason: ReasonCode,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        gate = GateResult(
            decision=GateDecision.STOP,
            stage=stage,
            reason_code=reason,
            details=dict(details),
        )
        sr = StageResult(
            stage=stage,
            status=StageStatus.STOP,
            ms=None,
            gate=gate,
            warnings=[],
        )
        report = RunReport(
            run_key=run_key,
            game_id=game_id,
            chart_id=chart_id,
            mode=mode,
            stage_results=[sr],
            gates=[gate],
            degraded_mode=False,
            warnings=[],
            diagnostics={"status": "STOP"},
        )
        return asdict(report)


__all__ = ["OrchestratorStabilizer", "InMemoryBreakerState"]