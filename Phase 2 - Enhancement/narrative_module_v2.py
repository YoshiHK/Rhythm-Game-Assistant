"""narrative_module_v2.py
Phase 2 Track D: Narrative polish layer.

Goals
- Enforce spec structure (2 paragraphs) and stay within word budgets.
- Use the tips generation spec templates.
- Allow a SMALL swap (chart_breakdown <-> player_guidance) when it improves readability.
- Auto-switch mixed-cue breakdown to a shorter parenthetical form when near word budgets.
  * Master + Append use hard-max-scaled behavior (switch only when close to hard max).
  * Append typically switches later because its hard max is larger.

This module expects Step 5.3 guidance fields to exist for selected elements.
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional
import json
import re


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_track_cd_config(path: str = 'track_cd_config.json') -> Dict[str, Any]:
    return _load_json(path)


def load_tips_spec(path: str = 'proseka_tips_generation_spec_v1.0.1_advisory.json') -> Dict[str, Any]:
    return _load_json(path).get('tips_generation_spec', {})


def _words(s: str) -> List[str]:
    return [w for w in (s or '').strip().split() if w]


def _truncate_to_words(s: str, max_words: int) -> str:
    ws = _words(s)
    if len(ws) <= max_words:
        return s
    return ' '.join(ws[:max_words]).rstrip('.') + '.'


def _clean_phrase(s: str) -> str:
    s = (s or '').strip().strip('.')
    s = s.replace('This element is challenging due to ', '')
    s = s.replace('This element recurs in key sections, increasing difficulty', 'recurring patterns')
    return s.strip().strip('.')


def _to_paren_cue_breakdown(break_sentence: str) -> str:
    """Convert mixed-cue 'such as' breakdown into parenthetical form.

    Keeps leading 'This manifests as ' prefix if present.
    """
    s = (break_sentence or '').strip()
    prefix = ''
    if s.startswith('This manifests as '):
        prefix = 'This manifests as '
        s = s[len(prefix):]

    parts = s.split(' and ')
    if len(parts) == 1:
        if ' cues such as ' in s:
            head, tail = s.split(' cues such as ', 1)
            return prefix + f"{head} cues ({tail})"
        return break_sentence

    p1 = parts[0]
    p2 = ' and '.join(parts[1:])

    # same-category case
    if ' cues such as ' in p1 and ' cues such as ' not in p2:
        head, t1 = p1.split(' cues such as ', 1)
        return prefix + f"{head} cues ({t1}, {p2})"

    def conv(p: str) -> str:
        if ' cues such as ' in p:
            h, t = p.split(' cues such as ', 1)
            return f"{h} cues ({t})"
        return p

    return prefix + conv(p1) + ' and ' + conv(p2)


def _pick_focus_description(selected_elements: List[Dict[str, Any]]) -> str:
    if not selected_elements:
        return 'define its primary mechanical focus'
    g = (selected_elements[0].get('guidance') or {})
    cause = _clean_phrase(g.get('difficulty_causes', ''))
    if not cause:
        return 'define its primary mechanical focus'
    return f"centres on {cause}"


def _auto_switch_breakdown(
    difficulty: str,
    sent1: str,
    sent2: str,
    sent3: str,
    dcfg: Dict[str, Any],
) -> str:
    """Optionally convert mixed-cue breakdown to parenthetical form.

    Reads:
      track_d.auto_switch_breakdown_variant

    Supports per-difficulty overrides:
      - mode: within_words_of_hard_max (preferred for Master/Append)
      - ratio-based fallback

    The switch triggers if either:
      - breakdown word count is high (breakdown_words_ge)
      - OR total paragraph word count is close to budget (scaled or ratio)
    """
    auto_sw = dcfg.get('auto_switch_breakdown_variant', {})
    if not isinstance(auto_sw, dict) or not auto_sw.get('enabled'):
        return sent2

    apply_ds = set(d.lower() for d in auto_sw.get('apply_difficulties', []))
    if difficulty.lower() not in apply_ds:
        return sent2

    prefer = auto_sw.get('prefer_variant', 'paren')
    if prefer != 'paren' or ' cues such as ' not in sent2:
        return sent2

    hard_max_total = int(dcfg.get('compression', {}).get('max_total_hard', {}).get(difficulty, 120))
    total_words = len(_words(sent1 + ' ' + sent2 + ' ' + sent3))
    bd_words = len(_words(sent2))

    # Defaults
    thr_bd = int(auto_sw.get('when_breakdown_words_ge', 18))
    thr_ratio = float(auto_sw.get('when_total_words_ge_ratio', 0.92))
    within_words: Optional[int] = None

    overrides = auto_sw.get('per_difficulty_overrides', {})
    if isinstance(overrides, dict):
        o = overrides.get(difficulty.lower(), {})
        if isinstance(o, dict):
            # accept either key name
            if 'breakdown_words_ge' in o:
                thr_bd = int(o.get('breakdown_words_ge', thr_bd))
            elif 'when_breakdown_words_ge' in o:
                thr_bd = int(o.get('when_breakdown_words_ge', thr_bd))

            if o.get('mode') == 'within_words_of_hard_max':
                within_words = int(o.get('total_within_words', 0))
            else:
                if 'when_total_words_ge_ratio' in o:
                    thr_ratio = float(o.get('when_total_words_ge_ratio', thr_ratio))

    trigger = bd_words >= thr_bd

    if within_words is not None and hard_max_total > 0:
        trigger = trigger or (total_words >= max(0, hard_max_total - within_words))
    else:
        trigger = trigger or (hard_max_total > 0 and (total_words / float(hard_max_total)) >= thr_ratio)

    return _to_paren_cue_breakdown(sent2) if trigger else sent2


def _build_paragraphs(
    difficulty: str,
    selected_elements: List[Dict[str, Any]],
    tips_spec: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Tuple[str, str]:

    # Paragraph 1
    element_names = [el.get('element_name', '') for el in selected_elements]
    element_list = ', '.join([n for n in element_names if n])
    focus_description = _pick_focus_description(selected_elements)

    p1_template = (
        tips_spec.get('text_script', {})
        .get('paragraph_1', {})
        .get('template', 'This chart features {{element_list}}, which {{focus_description}}.')
    )
    para1 = (
        p1_template
        .replace('{{element_list}}', element_list)
        .replace('{{focus_description}}', focus_description)
    )

    # Paragraph 2 (anchor on top element)
    anchor = selected_elements[0]
    g = anchor.get('guidance', {}) or {}

    dominant_cause = _clean_phrase(g.get('difficulty_causes', 'recurring mechanics'))
    chart_breakdown = _clean_phrase(g.get('chart_breakdown', 'repeating patterns across key sections'))
    mechanical_interaction = _clean_phrase(g.get('chart_breakdown', '')) or chart_breakdown

    primary_focus = _clean_phrase(g.get('primary_focus', 'execution stability'))
    secondary_focus = _clean_phrase(g.get('secondary_focus', 'timing consistency'))
    strategy = _clean_phrase(g.get('strategy', 'a simple route'))
    target_section = _clean_phrase(g.get('target_section', 'the difficult segments'))

    t2 = (
        tips_spec.get('text_script', {})
        .get('paragraph_2', {})
        .get('templates', {})
    )

    s_cause = t2.get(
        'difficulty_cause',
        'The difficulty comes from {{dominant_cause}}, where {{mechanical_interaction}} increases execution pressure.'
    )
    s_break = t2.get('chart_breakdown', 'This manifests as {{chart_breakdown}}.')
    s_guide = t2.get(
        'player_guidance',
        'It helps to focus on {{primary_focus}}, prioritise {{secondary_focus}} over precision, and plan {{strategy}} early to stay consistent through {{target_section}}.'
    )

    sent1 = (
        s_cause
        .replace('{{dominant_cause}}', dominant_cause)
        .replace('{{mechanical_interaction}}', mechanical_interaction)
    )
    sent2 = s_break.replace('{{chart_breakdown}}', chart_breakdown)
    sent3 = (
        s_guide
        .replace('{{primary_focus}}', primary_focus)
        .replace('{{secondary_focus}}', secondary_focus)
        .replace('{{strategy}}', strategy)
        .replace('{{target_section}}', target_section)
    )

    dcfg = cfg.get('track_d', {}) or {}

    # Auto-switch breakdown variant (Master/Append)
    sent2 = _auto_switch_breakdown(difficulty, sent1, sent2, sent3, dcfg)

    # Allow small swap between breakdown and guidance
    allow_swap = bool(dcfg.get('allow_small_swap', False))
    trig = dcfg.get('swap_triggers', {}) or {}
    max_words_sent = int(trig.get('max_words_per_sentence', 30))
    breakdown_word_threshold = int(trig.get('breakdown_word_threshold', 20))

    order = [sent1, sent2, sent3]
    if allow_swap:
        if len(_words(sent2)) > breakdown_word_threshold or len(_words(sent2)) > max_words_sent:
            order = [sent1, sent3, sent2]

    # Enforce per-sentence max words
    order = [
        _truncate_to_words(s, max_words_sent) if len(_words(s)) > max_words_sent else s
        for s in order
    ]

    # Enforce hard max total words
    hard_max = int(dcfg.get('compression', {}).get('max_total_hard', {}).get(difficulty, 120))
    joined = ' '.join(order)

    if len(_words(joined)) > hard_max:
        trim_order = dcfg.get('compression', {}).get('trim_order', []) or []

        def drop_secondary_focus(txt: str) -> str:
            return re.sub(r",\s*prioritise[^,\.]+(over precision)?", '', txt)

        def shorten_mech(txt: str) -> str:
            return txt.replace('where ', '').replace(' increases execution pressure', '')

        def shorten_break(txt: str) -> str:
            return _truncate_to_words(txt, 12)

        for step in trim_order:
            if len(_words(joined)) <= hard_max:
                break
            if step == 'drop_secondary_focus_phrase':
                for i, s in enumerate(order):
                    if s.startswith('It helps') or 'It helps to focus on' in s:
                        order[i] = drop_secondary_focus(s)
                        break
            elif step == 'shorten_mechanical_interaction':
                order[0] = shorten_mech(order[0])
            elif step == 'shorten_breakdown':
                for i, s in enumerate(order):
                    if s.startswith('This manifests'):
                        order[i] = shorten_break(s)
                        break
            joined = ' '.join(order)

        if len(_words(joined)) > hard_max:
            joined = ' '.join(_words(joined)[:hard_max]).rstrip('.') + '.'

    return para1.strip(), joined.strip()


def generate_tips_text_v2(
    difficulty: str,
    selected_elements: List[Dict[str, Any]],
    *,
    tips_spec_path: str = 'proseka_tips_generation_spec_v1.0.1_advisory.json',
    track_cd_config_path: str = 'track_cd_config.json',
) -> str:

    if not selected_elements:
        return 'No actionable elements detected for this chart.'

    tips_spec = load_tips_spec(tips_spec_path)
    cfg = load_track_cd_config(track_cd_config_path)

    para1, para2 = _build_paragraphs(difficulty, selected_elements, tips_spec, cfg)
    return para1 + "\n\n" + para2


__all__ = ['generate_tips_text_v2']
