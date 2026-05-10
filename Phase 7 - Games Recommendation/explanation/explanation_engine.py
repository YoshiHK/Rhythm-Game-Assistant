from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# Uses contract-layer item shape (Phase 7 is game-level).
from ..contracts.types import RecommendationItem


ResolveMessage = Callable[[str, str, Any], str]


class ExplanationEngine:
    """
    Phase 7 Explanation Engine (versionless).

    Purpose:
    - Convert structured ranking signals into presentation-safe explanations.
    - Deterministic, bounded, and auditable.
    - No free-form generation required.

    Design notes:
    - This engine does NOT perform I/O.
    - This engine MUST NOT implement ranking.
    - This engine MUST NOT implement runtime version switching.

    Expected item shape:
      RecommendationItem(
        game_id=...,
        song_id="",
        score=...,
        rationale={
          "reasons": [ "history:novelty_bonus", ... ],
          "diagnostics": { "baseline": ..., "deltas": [ {"code":..., "delta":..., "detail":...}, ... ] },
          ...
        }
      )

    The engine enriches item.rationale IN-PLACE by mutating the rationale dict
    (safe even if RecommendationItem is frozen, because dict is mutable).
    """

    def __init__(self, *, max_why: int = 4):
        self.max_why = int(max_why) if int(max_why) > 0 else 4

    def explain_items(
        self,
        *,
        items: Sequence[RecommendationItem],
        ctx: Dict[str, Any],
    ) -> List[RecommendationItem]:
        """
        Enrich items with explanation fields.

        ctx supports:
          - locale: str (optional, default "")
          - resolve_message: callable(code, locale, detail) -> str (optional)
        """
        locale = str(ctx.get("locale") or "")
        resolver: Optional[ResolveMessage] = ctx.get("resolve_message")

        for it in items or []:
            rationale = getattr(it, "rationale", None)
            if not isinstance(rationale, dict):
                continue

            reasons = rationale.get("reasons")
            if not isinstance(reasons, list):
                reasons = []
            else:
                # normalize to str list
                reasons = [str(x) for x in reasons if x is not None]

            diagnostics = rationale.get("diagnostics")
            if not isinstance(diagnostics, dict):
                diagnostics = {}

            why = self._build_why(
                reasons=reasons,
                diagnostics=diagnostics,
                locale=locale,
                resolver=resolver,
            )
            summary = self._build_summary(why=why, locale=locale, resolver=resolver)

            # Write back into rationale (bounded + presentation-safe)
            explanation = {
                "locale": locale,
                "summary": summary,
                "why": why,
            }
            rationale["explanation"] = explanation

        return list(items)

    # -------------------------
    # Internal helpers (pure)
    # -------------------------

    def _build_why(
        self,
        *,
        reasons: List[str],
        diagnostics: Dict[str, Any],
        locale: str,
        resolver: Optional[ResolveMessage],
    ) -> List[Dict[str, Any]]:
        """
        Build bounded 'why' list from diagnostics deltas (preferred),
        then fall back to reasons list if deltas unavailable.
        """
        why: List[Dict[str, Any]] = []

        deltas = diagnostics.get("deltas")
        if isinstance(deltas, list):
            for d in deltas:
                if not isinstance(d, dict):
                    continue
                code = str(d.get("code") or "").strip()
                if not code:
                    continue
                delta = self._to_float(d.get("delta"))
                detail = d.get("detail")

                msg = self._message_for_code(
                    code=code,
                    locale=locale,
                    detail=detail,
                    resolver=resolver,
                )
                why.append(
                    {
                        "code": code,
                        "delta": delta,
                        "message": msg,
                    }
                )

        # If no deltas, fall back to reasons codes (bounded)
        if not why and reasons:
            for code in reasons:
                code_s = str(code).strip()
                if not code_s:
                    continue
                msg = self._message_for_code(
                    code=code_s,
                    locale=locale,
                    detail=None,
                    resolver=resolver,
                )
                why.append({"code": code_s, "delta": 0.0, "message": msg})

        # Sort by absolute impact desc, then code asc (deterministic)
        why.sort(key=lambda x: (-abs(self._to_float(x.get("delta"))), str(x.get("code") or "")))

        return why[: self.max_why]

    def _build_summary(
        self,
        *,
        why: List[Dict[str, Any]],
        locale: str,
        resolver: Optional[ResolveMessage],
    ) -> str:
        """
        Pick a concise, deterministic summary.
        """
        if not why:
            return self._fallback_summary(locale=locale, resolver=resolver)

        msg = str(why[0].get("message") or "").strip()
        return msg or self._fallback_summary(locale=locale, resolver=resolver)

    def _fallback_summary(self, *, locale: str, resolver: Optional[ResolveMessage]) -> str:
        # Allow resolver to provide a localized default if desired
        if resolver is not None:
            try:
                return str(resolver("summary:default", locale, None))
            except Exception:
                pass
        return "Recommended based on your recent activity and preferences."

    def _message_for_code(
        self,
        *,
        code: str,
        locale: str,
        detail: Any,
        resolver: Optional[ResolveMessage],
    ) -> str:
        """
        Resolve a human-readable explanation message for a standardized code.

        If ctx provides resolve_message(), it is used first.
        Otherwise falls back to deterministic built-in messages.
        """
        if resolver is not None:
            try:
                out = resolver(code, locale, detail)
                if out is not None:
                    s = str(out).strip()
                    if s:
                        return s
            except Exception:
                # Non-blocking: resolver failures must not break explanation
                pass

        # Built-in deterministic fallback mapping (English baseline)
        mapping = {
            "history:recent_penalty": "You recently played this game, so it was deprioritized to encourage variety.",
            "history:novelty_bonus": "You have not played this recently, so it is suggested for variety.",
            "exp:new": "Signals suggest this game may be a smoother fit for newer players.",
            "exp:intermediate": "Signals suggest this game aligns with steady progression.",
            "exp:advanced": "Signals suggest this game offers more challenge.",
            "fit:low_clear": "Based on your recent performance signals, a practice-friendly option was favored.",
            "fit:high_clear": "Based on your recent performance signals, a challenge option was favored.",
            "fit:stamina_high": "Signals suggest stamina-heavy content may be a good fit.",
            "fit:stamina_low": "Signals suggest avoiding stamina-heavy content for now.",
            "affinity:tags": "Signals suggest this matches your stated preferences.",
            "summary:default": "Recommended based on your recent activity and preferences.",
        }
        if code in mapping:
            return mapping[code]

        d = str(detail).strip() if detail is not None else ""
        return f"Recommendation signal: {code}" + (f" ({d})" if d else "")

    @staticmethod
    def _to_float(x: Any) -> float:
        try:
            if x is None:
                return 0.0
            return float(x)
        except Exception:
            return 0.0