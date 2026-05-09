"""guidance_engine_v2.py

Phase 2 Track C: Guidance adaptation layer.

Enhancements implemented:
- Combine tied dominant categories into a single cause phrase.
- When tie occurs, chart_breakdown can reference exemplar tags drawn from up to two tied categories.
- Mixed-cue breakdown phrasing (category cue labels) when enabled, with an optional parenthetical variant (e.g., "readability cues (low_visibility)").

This remains non-breaking: output fields unchanged.
"""

from __future__ import annotations

from typing import List, Dict, Any
import json

try:
    from proseka_guidance_engine import (
        load_pattern_signals,
        load_tips_spec,
        load_training_mapping,
        categorize_tags,
        derive_focus,
        CATEGORY_CAUSE,
    )
except Exception:  # pragma: no cover
    load_pattern_signals = None
    load_tips_spec = None
    load_training_mapping = None
    categorize_tags = None
    derive_focus = None
    CATEGORY_CAUSE = {}


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_track_cd_config(path: str = 'track_cd_config.json') -> Dict[str, Any]:
    return _load_json(path)


def _join_phrases(parts: List[str], style: str = 'and') -> str:
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    if style == 'comma_and':
        return ', '.join(parts[:-1]) + f", and {parts[-1]}"
    return ', '.join(parts[:-1]) + f" and {parts[-1]}"


def _dominant_categories(cats: Dict[str, List[str]], cfg: Dict[str, Any]) -> List[str]:
    if not cats:
        return []
    strat = cfg.get('track_c', {}).get('dominant_category_strategy', 'most_hits')
    priority = cfg.get('track_c', {}).get('category_priority', [])

    if strat == 'priority':
        for c in priority:
            if c in cats:
                return [c]
        return [next(iter(cats.keys()))]

    items = sorted(cats.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    top_len = len(items[0][1])
    tied = [c for c, hits in items if len(hits) == top_len]

    ordered: List[str] = []
    for c in priority:
        if c in tied and c not in ordered:
            ordered.append(c)
    for c in tied:
        if c not in ordered:
            ordered.append(c)
    return ordered


def _cause_phrase(categories: List[str], difficulty: str, cfg: Dict[str, Any]) -> str:
    if not categories:
        return 'recurring patterns that increase execution pressure'

    variants = cfg.get('track_c', {}).get('cause_variants', {})
    style = cfg.get('track_c', {}).get('combine_join_style', 'and')
    max_n = int(cfg.get('track_c', {}).get('max_combined_categories', 2))
    combine = bool(cfg.get('track_c', {}).get('combine_tied_categories', True))

    use = categories[:max(1, max_n)] if combine else categories[:1]

    phrases: List[str] = []
    for category in use:
        if category in variants:
            v = variants[category]
            phrases.append(v.get(difficulty, v.get('default')))
        elif category in CATEGORY_CAUSE:
            phrases.append(CATEGORY_CAUSE[category])
        else:
            phrases.append('recurring patterns that increase execution pressure')

    return _join_phrases(phrases, style=style)


def _cue_label(category: str, cfg: Dict[str, Any]) -> str:
    labels = cfg.get('track_c', {}).get('breakdown', {}).get('cue_labels', {})
    if category in labels:
        return str(labels[category])
    # safe fallback
    return 'pattern cues'


def _breakdown_phrase(exemplar_pairs: List[tuple], cfg: Dict[str, Any]) -> str:
    """Build chart_breakdown string.

    exemplar_pairs: list of (category, tag) tuples.
    style:
      - patterns_like: "patterns like A and B"
      - mixed_cues: "<cue> such as A and <cue> such as B" (when categories differ)
    """
    if not exemplar_pairs:
        return 'it appears across multiple sections without a single dominant form'

    style = cfg.get('track_c', {}).get('breakdown', {}).get('style', 'patterns_like')
    max_n = int(cfg.get('track_c', {}).get('breakdown', {}).get('max_example_tags', 2))

    pairs = exemplar_pairs[:max(1, max_n)]

    # patterns_like
    if style != 'mixed_cues':
        tags = [t for _, t in pairs]
        if len(tags) == 1:
            return f"patterns like {tags[0]}"
        return f"patterns like {tags[0]} and {tags[1]}"

    # mixed_cues
    variant = cfg.get('track_c', {}).get('breakdown', {}).get('mixed_cue_variant', 'such_as')
    if len(pairs) == 1:
        c, t = pairs[0]
        if variant == 'paren':
            return f"{_cue_label(c, cfg)} ({t})"
        return f"{_cue_label(c, cfg)} such as {t}"

    (c1, t1), (c2, t2) = pairs[0], pairs[1]
    if c1 == c2:
        if variant == 'paren':
            return f"{_cue_label(c1, cfg)} ({t1}, {t2})"
        return f"{_cue_label(c1, cfg)} such as {t1} and {t2}"

    if variant == 'paren':
        return f"{_cue_label(c1, cfg)} ({t1}) and {_cue_label(c2, cfg)} ({t2})"
    return f"{_cue_label(c1, cfg)} such as {t1} and {_cue_label(c2, cfg)} such as {t2}"


def _target_section(sc: float, cfg: Dict[str, Any]) -> str:
    buckets = cfg.get('track_c', {}).get('coverage_buckets', {})
    hi = float(buckets.get('high', 0.6))
    mid = float(buckets.get('mid', 0.3))
    if sc >= hi:
        return 'most of the chart'
    if sc >= mid:
        return 'the mid sections'
    return 'the specific difficult segments'


def fill_guidance_for_elements_v2(
    selected_elements: List[Dict[str, Any]],
    difficulty: str,
    *,
    track_cd_config_path: str = 'track_cd_config.json',
    pattern_signals_path: str = 'pattern_signals_export_v2.json',
    tips_spec_path: str = 'proseka_tips_generation_spec_v1.0.1_advisory.json',
    training_mapping_path: str = 'tips_training_mapping.json',
) -> List[Dict[str, Any]]:

    cfg = load_track_cd_config(track_cd_config_path)

    taxonomy = load_pattern_signals(pattern_signals_path) if load_pattern_signals else _load_json(pattern_signals_path).get('pattern_and_difficulty_signals', {})
    _ = load_tips_spec(tips_spec_path) if load_tips_spec else None
    _ = load_training_mapping(training_mapping_path) if load_training_mapping else None

    for el in selected_elements:
        tags = el.get('matched_tags', []) or []
        training = el.get('training_items', []) or []
        sc = float(el.get('section_coverage', 0.0) or 0.0)

        cats = categorize_tags(tags, taxonomy) if categorize_tags else {c: [t for t in tl if t in set(tags)] for c, tl in taxonomy.items() if any(t in set(tags) for t in tl)}

        dom_cats = _dominant_categories(cats, cfg)
        difficulty_causes = _cause_phrase(dom_cats, difficulty, cfg)

        # Build exemplar (category, tag) pairs.
        include_ties = bool(cfg.get('track_c', {}).get('breakdown', {}).get('include_tied_categories', True))
        max_ex = int(cfg.get('track_c', {}).get('breakdown', {}).get('max_example_tags', 2))

        exemplar_pairs: List[tuple] = []
        if dom_cats:
            cats_to_use = dom_cats[:2] if include_ties else dom_cats[:1]
            seen = set()
            for c in cats_to_use:
                for t in cats.get(c, []):
                    if t in seen:
                        continue
                    exemplar_pairs.append((c, t))
                    seen.add(t)
                    if len(exemplar_pairs) >= max(1, max_ex):
                        break
                if len(exemplar_pairs) >= max(1, max_ex):
                    break

        if not exemplar_pairs and cats:
            # fallback: pick first available category's first tags
            c0 = next(iter(cats.keys()))
            for t in cats[c0][:max(1, max_ex)]:
                exemplar_pairs.append((c0, t))

        chart_breakdown = _breakdown_phrase(exemplar_pairs, cfg)

        if derive_focus:
            primary, secondary, strategy = derive_focus(training)
        else:
            primary = training[0] if training else 'maintaining stability across repeating patterns'
            secondary = training[1] if len(training) > 1 else 'keeping timing clean as density changes'
            strategy = 'treat the section as repeating shapes and commit to a simple route'

        target = _target_section(sc, cfg)

        el['guidance'] = {
            'difficulty_causes': difficulty_causes,
            'chart_breakdown': chart_breakdown,
            'primary_focus': primary,
            'secondary_focus': secondary,
            'strategy': strategy,
            'target_section': target,
        }

    return selected_elements


__all__ = ['fill_guidance_for_elements_v2']
