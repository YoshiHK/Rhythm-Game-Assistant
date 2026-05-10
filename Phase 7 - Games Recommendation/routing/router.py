from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..contracts.types import RecommendationItem, RecommendationResponse
from ..registry.registry import GameRegistry
from .routing_context import Phase7RoutingContext
from .routing_policy import Phase7RoutingPolicy


class Phase7Router:
    """
    Phase 7 routing coordinator (single runtime entrypoint).

    Responsibilities (coordinator-only):
    - Non-blocking orchestration
    - Candidate selection via registry + routing policy (read-only)
    - Ranker invocation (single implementation; no runtime version switching)
    - Explanation invocation (optional; bounded; no free-form required)
    - Optional side-channel emission:
        - Feedback events (forward-only; failures swallowed)
        - Observability snapshot (failures swallowed)

    Prohibitions (architectural):
    - MUST NOT import eligibility policy (CI-only governance)
    - MUST NOT implement learning or experimentation logic
    - MUST NOT implement runtime version negotiation or schema switching
    """

    def __init__(
        self,
        *,
        registry: GameRegistry,
        policy: Optional[Phase7RoutingPolicy] = None,
        ranker: Optional[Any] = None,
        explainer: Optional[Any] = None,
        enabled: bool = True,
        # Optional sinks (Phase 6 owns transport; Phase 7 only emits payloads)
        feedback_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        metrics_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        # Optional collectors (kept injectable to avoid hard coupling)
        feedback_emitter: Optional[Any] = None,
        observation_collector: Optional[Any] = None,
    ):
        self.registry = registry
        self.policy = policy or Phase7RoutingPolicy()
        self.ranker = ranker
        self.explainer = explainer
        self.enabled = bool(enabled)

        self.feedback_sink = feedback_sink
        self.metrics_sink = metrics_sink

        # Optional injection points (do NOT import CI-only or platform code here)
        self.feedback_emitter = feedback_emitter
        self.observation_collector = observation_collector

    # ------------------------------------------------------------
    # Public API (single entrypoint)
    # ------------------------------------------------------------

    def recommend_games(
        self,
        *,
        ctx: Phase7RoutingContext,
        player_profile: Optional[Dict[str, Any]] = None,
        player_history: Optional[Dict[str, Any]] = None,
        game_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> RecommendationResponse:
        """
        Compute game recommendations for a player context.

        Failure-isolated / non-blocking:
        - Never raises to upstream callers
        - Returns empty response on disablement or unrecoverable errors
        """
        if not self.enabled:
            resp = self._empty(ctx, reason="phase7_disabled")
            self._emit_observation(ctx=ctx, items=resp.items, reason="phase7_disabled")
            return resp

        # 1) Candidate selection (registry + policy)
        try:
            candidates = self.policy.select_candidates(
                registry=self.registry,
                platform=ctx.platform,
                locale=ctx.locale,
            )
        except Exception:
            resp = self._empty(ctx, reason="candidate_selection_failed")
            self._emit_observation(ctx=ctx, items=resp.items, reason="candidate_selection_failed")
            return resp

        if not candidates:
            resp = self._empty(ctx, reason="no_candidates")
            self._emit_observation(ctx=ctx, items=resp.items, reason="no_candidates")
            return resp

        # 2) Ranking (optional ranker; deterministic fallback if absent/fails)
        try:
            items = self._rank_candidates(
                candidates=candidates,
                ctx=ctx,
                player_profile=player_profile or {},
                player_history=player_history or {},
                game_profiles=game_profiles,
            )
        except Exception:
            items = self._fallback_unranked(candidates, reason="ranker_failed")

        # 3) Apply top_k cap
        top_k = self._safe_top_k(ctx.top_k)
        items = items[:top_k]

        # 4) Explanation (optional; must not block)
        if self.explainer is not None:
            try:
                self._explain(items=items, locale=ctx.locale)
            except Exception:
                # Explanation failures must not break routing
                pass

        # 5) Emit observation snapshot (must not block)
        self._emit_observation(ctx=ctx, items=items, reason=None)

        return RecommendationResponse(
            items=items,
            metadata={
                "player_id": ctx.player_id,
                "locale": ctx.locale,
                "generated_at_iso": self._utc_now_iso(),
                "invocation_source": ctx.invocation_source,
            },
        )

    # ------------------------------------------------------------
    # Internal helpers (pure/coordinator-safe)
    # ------------------------------------------------------------

    def _rank_candidates(
        self,
        *,
        candidates: Sequence[str],
        ctx: Phase7RoutingContext,
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        game_profiles: Optional[Dict[str, Dict[str, Any]]],
    ) -> List[RecommendationItem]:
        """
        Ranker adapter.

        Supports ranker implementations exposing either:
        - rank(candidate_game_ids=..., ctx=..., player_profile=..., player_history=..., game_profiles=...)
        - rank_games(...) with similar parameters

        No version argument is passed (no runtime version switching).
        """
        if self.ranker is None:
            return self._fallback_unranked(candidates, reason="no_ranker")

        payload_ctx = {"player_id": ctx.player_id, "locale": ctx.locale}

        if hasattr(self.ranker, "rank_games"):
            ranked = self.ranker.rank_games(  # type: ignore[attr-defined]
                candidate_game_ids=list(candidates),
                ctx=payload_ctx,
                player_profile=player_profile,
                player_history=player_history,
                game_profiles=game_profiles,
            )
        else:
            ranked = self.ranker.rank(
                candidate_game_ids=list(candidates),
                ctx=payload_ctx,
                player_profile=player_profile,
                player_history=player_history,
                game_profiles=game_profiles,
            )

        out: List[RecommendationItem] = []
        for r in ranked or []:
            if isinstance(r, RecommendationItem):
                out.append(r)
            elif isinstance(r, dict):
                out.append(
                    RecommendationItem(
                        game_id=str(r.get("game_id", "")),
                        song_id=str(r.get("song_id", "")),
                        score=float(r.get("score", 0.0)),
                        rationale=dict(r.get("rationale", {})),
                    )
                )
            else:
                # Unknown shape => skip (non-blocking)
                continue

        return out if out else self._fallback_unranked(candidates, reason="ranker_empty")

    def _explain(self, *, items: List[RecommendationItem], locale: str) -> None:
        """
        Explainer adapter. Expected to enrich item.rationale in-place.
        """
        if hasattr(self.explainer, "explain_items"):
            self.explainer.explain_items(items=items, ctx={"locale": locale})  # type: ignore[attr-defined]
        elif hasattr(self.explainer, "explain"):
            self.explainer.explain(items=items, locale=locale)  # type: ignore[attr-defined]

    def _emit_observation(
        self,
        *,
        ctx: Phase7RoutingContext,
        items: List[RecommendationItem],
        reason: Optional[str],
    ) -> None:
        """
        Emit semantic observation payload (non-blocking).
        Uses injected observation_collector if provided.
        """
        if self.observation_collector is None:
            return

        try:
            # Expected signature: collect_observation(player_id, locale, items, reason, sink)
            payload = self.observation_collector(
                player_id=ctx.player_id,
                locale=ctx.locale,
                items=items,
                reason=reason,
                sink=self.metrics_sink,
            )
            _ = payload  # payload returned for debugging; not required here
        except Exception:
            pass

    def emit_feedback(
        self,
        *,
        player_id: str,
        game_id: str,
        action: Any,
        locale: Optional[str] = None,
        recommendation_rank: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Optional feedback emission helper.

        This is NOT called by recommend_games().
        It exists for Phase 6 / UI wiring to forward feedback signals safely.

        - Forward-only (to Phase 5 via Phase 6 transport)
        - Non-blocking (sink failures swallowed)
        """
        if self.feedback_emitter is None:
            return None

        try:
            payload = self.feedback_emitter(
                player_id=player_id,
                game_id=game_id,
                action=action,
                locale=locale,
                recommendation_rank=recommendation_rank,
                sink=self.feedback_sink,
            )
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _fallback_unranked(self, candidates: Sequence[str], *, reason: str) -> List[RecommendationItem]:
        """
        Deterministic fallback: stable ordering by game_id.
        """
        return [
            RecommendationItem(
                game_id=str(gid),
                song_id="",
                score=0.0,
                rationale={"reason": reason},
            )
            for gid in sorted(str(x) for x in candidates)
        ]

    def _empty(self, ctx: Phase7RoutingContext, *, reason: str) -> RecommendationResponse:
        return RecommendationResponse(
            items=[],
            metadata={
                "player_id": ctx.player_id,
                "locale": ctx.locale,
                "generated_at_iso": self._utc_now_iso(),
                "invocation_source": ctx.invocation_source,
                "empty_reason": reason,
            },
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _safe_top_k(top_k: int) -> int:
        try:
            k = int(top_k)
        except Exception:
            return 5
        return 1 if k < 1 else (20 if k > 20 else k)