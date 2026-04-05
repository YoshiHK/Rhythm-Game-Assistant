# proseka_guidance_engine.py
# Portable Practical Guidance Engine
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import json

def load_pattern_signals(path="pattern_signals_export_v2.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("pattern_and_difficulty_signals", {})

def load_tips_spec(path="proseka_tips_generation_spec_v1.0.1_advisory.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("tips_generation_spec", {})

def load_training_mapping(path="tips_training_mapping.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def categorize_tags(tags: List[str], taxonomy: Dict[str, List[str]]):
    tagset = set(tags)
    out = {}
    for cat, tl in taxonomy.items():
        hits = [t for t in tl if t in tagset]
        if hits:
            out[cat] = hits
    return out

CATEGORY_CAUSE = {
    "flow_patterns": "dense streams or bursts",
    "vertical_patterns": "vertical jumps or multi-lane hits",
    "directional_patterns": "direction-changing stairs",
    "alternation_patterns": "alternating or trilling patterns",
    "hand_interaction_tags": "cross-hand or forced hand-swaps",
    "precision_tags": "tight spacing or tiny-note precision requirements",
    "rhythm_tags": "rhythmic irregularity or syncopation",
    "pacing_tags": "tempo or density fluctuations",
    "bpm_density_relation_tags": "dense notes at low BPM",
    "temporal_disruption_tags": "stops, fake endings, or deceptive breaks",
    "readability_tags": "visibility or recognition difficulty",
    "slide_complexity_tags": "complex slide or trace structures",
    "duration_structure_tags": "long duration or endurance segments",
    "multi_lane_patterns": "multi-lane or chorded patterns",
}

TRAINING_PRIMARY = {
    "physical strength": "keeping your hands relaxed under sustained motion",
    "awareness": "tracking pattern transitions in advance",
    "timing": "aligning notes consistently with the beat",
    "precision": "reducing over-correction in lane movements",
    "chart readibility": "recognising shapes before they arrive",
    "hand movement": "assigning hands cleanly without last-second switches",
    "coordination": "keeping both hands moving consistently",
}

TRAINING_SECONDARY = {
    "physical strength": "not overspeeding during bursts",
    "awareness": "spotting sudden structural changes early",
    "timing": "avoiding hesitation during syncopation",
    "precision": "controlling lane travel between dense notes",
    "chart readibility": "grouping notes instead of reading individually",
    "hand movement": "pre-deciding hand roles before the section",
    "coordination": "maintaining mirrored motion when patterns drift",
}

TRAINING_STRATEGY = {
    "physical strength": "use micro-rests between bursts to avoid fatigue build-up",
    "awareness": "mark transitions mentally one beat early",
    "timing": "hum or internally count to stabilise timing",
    "precision": "anchor your gaze on pattern shapes rather than individual notes",
    "chart readibility": "read by shape clusters such as stairs or blocks",
    "hand movement": "lock in a consistent hand-routing pattern",
    "coordination": "slow-practice the motion and ramp speed while keeping form",
}

DEFAULT_PRIMARY = "maintaining stability across repeating patterns"
DEFAULT_SECONDARY = "keeping timing clean as density changes"
DEFAULT_STRATEGY = "treat the section as repeating shapes and commit to a simple route"


def derive_focus(training_items: List[str]):
    p = next((TRAINING_PRIMARY[i] for i in training_items if i in TRAINING_PRIMARY), DEFAULT_PRIMARY)
    s = next((TRAINING_SECONDARY[i] for i in training_items if i in TRAINING_SECONDARY), DEFAULT_SECONDARY)
    g = next((TRAINING_STRATEGY[i] for i in training_items if i in TRAINING_STRATEGY), DEFAULT_STRATEGY)
    return p, s, g


def fill_guidance_for_elements(selected_elements: List[Dict[str, Any]], difficulty: str,
                               pattern_signals_path="pattern_signals_export_v2.json",
                               tips_spec_path="proseka_tips_generation_spec_v1.0.1_advisory.json",
                               training_mapping_path="tips_training_mapping.json"):
    taxonomy = load_pattern_signals(pattern_signals_path)
    spec = load_tips_spec(tips_spec_path)
    mapping = load_training_mapping(training_mapping_path)

    for el in selected_elements:
        tags = el.get("matched_tags", [])
        cats = categorize_tags(tags, taxonomy)
        training = el.get("training_items", [])

        # difficulty causes
        if cats:
            cause_list = [CATEGORY_CAUSE[c] for c in cats if c in CATEGORY_CAUSE]
            dominant = ", ".join(cause_list)
            difficulty_causes = f"This element is challenging due to {dominant}."
        else:
            difficulty_causes = "This element recurs in key sections, increasing difficulty."

        # breakdown
        if cats:
            exemplar = next(iter(cats.values()))[0]
            chart_breakdown = f"It appears mainly through patterns like {exemplar}."
        else:
            chart_breakdown = "It appears across multiple sections without a single dominant form."

        # focus & strategy
        primary, secondary, strategy = derive_focus(training)

        # target section
        sc = el.get("section_coverage", 0)
        if sc >= 0.6:
            target = "most of the chart"
        elif sc >= 0.3:
            target = "the mid sections"
        else:
            target = "the specific difficult segments"

        el["guidance"] = {
            "difficulty_causes": difficulty_causes,
            "chart_breakdown": chart_breakdown,
            "primary_focus": primary,
            "secondary_focus": secondary,
            "strategy": strategy,
            "target_section": target,
        }

    return selected_elements
