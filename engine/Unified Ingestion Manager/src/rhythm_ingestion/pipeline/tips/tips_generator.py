from __future__ import annotations
"""tips_generator.py (Phase 3 patched – Track B wrapper + tone hint wiring)

Phase 3 wiring patch for tips generation.

Key points:
- Track B selection is routed through element_selector_wrapper.select_elements_phase3.
  That wrapper attaches tone_hint to selected elements and to canonical_payload['diagnostics']['tone_hint'].
- "Promising tips" gating is driven ONLY by Track C/D degraded flags
  (runner_degraded_mode.should_use_promising_tips).
- This module attaches tone_hint to the returned output dict for downstream (runner/UI).

No Completed Phase code is modified.
"""

from typing import Any, Dict, Optional

from .element_inference import attach_candidates_to_payload as _ei_attach_candidates_to_payload
from .runner_degraded_mode import should_use_promising_tips
from .element_selector_wrapper import select_elements_phase3, Tone

DEFAULT_TRAINING_MAPPING_PATH = 'tips_training_mapping.json'


def _get_tone_hint(canonical_payload: Dict[str, Any]) -> Tone:
    diag = canonical_payload.get('diagnostics')
    if isinstance(diag, dict):
        t = diag.get('tone_hint')
        if isinstance(t, str) and t in ('normal', 'neutral', 'minimal'):
            return t  # type: ignore
    return 'normal'


def _build_degraded_tips_output(
    canonical_payload: Dict[str, Any],
    *,
    reason: Optional[str] = None,
    selected_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Return a degraded-safe tips output.

    This avoids narrative/guidance claims and stays structural.
    """

    elements = canonical_payload.get('elements_skeleton') or []

    canonical_payload.setdefault('diagnostics', {}).setdefault('tips_generator', {}).update({
        'degraded': True,
        'fallback': 'structural_summary',
    })

    tone_hint = _get_tone_hint(canonical_payload)

    summary: Dict[str, Any] = {
        'mode': 'degraded',
        'element_count': len(elements),
        'note': reason or 'Degraded mode active (Track C/D gated)',
        'tone_hint': tone_hint,
    }
    if selected_count is not None:
        summary['selected_count'] = int(selected_count)

    return {
        'tips_text': '',
        'tone_hint': tone_hint,
        'summary': summary,
    }


def run_for_chart(
    game_id: str,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    *,
    mode: str = 'production',
    attach_to_payload: bool = True,
) -> Dict[str, Any]:
    """Run tips generation for a single chart (Phase 3 wiring)."""

    gid = (game_id or '').strip().lower()

    # Ensure element candidates exist (Stage 4.2/4.3)
    _ei_attach_candidates_to_payload(
        canonical_payload,
        game_id=gid,
        mapping_path=DEFAULT_TRAINING_MAPPING_PATH,
    )

    difficulty = canonical_row.get('difficulty') or canonical_payload.get('difficulty')

    # Track B (selection) through Phase 3 wrapper (records diagnostics.track_b + tone_hint)
    selected = select_elements_phase3(
        game_id=gid,
        canonical_payload=canonical_payload,
        difficulty=str(difficulty or ''),
    )

    # Gate Track C/D only (latest semantics)
    if not should_use_promising_tips(canonical_payload):
        out = _build_degraded_tips_output(
            canonical_payload,
            selected_count=len(selected),
        )
        if attach_to_payload:
            canonical_payload['tips'] = out
        return out

    # Completed Phase Track C/D modules
    from . import guidance_engine_v2  # type: ignore
    from . import narrative_module_v2  # type: ignore

    guided = guidance_engine_v2.fill_guidance_for_elements_v2(
        selected,
        difficulty=str(difficulty or ''),
    )

    tips_text = narrative_module_v2.generate_tips_text_v2(
        str(difficulty or ''),
        guided,
    )

    tone_hint = _get_tone_hint(canonical_payload)

    out = {
        'tips_text': tips_text,
        'elements': guided,
        'tone_hint': tone_hint,
    }

    if attach_to_payload:
        canonical_payload['tips'] = out

    return out


__all__ = ['run_for_chart']
