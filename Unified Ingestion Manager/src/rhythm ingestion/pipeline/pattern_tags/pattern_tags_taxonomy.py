# umi/pipeline/pattern_tags_taxonomy.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Optional

@dataclass(frozen=True)
class TagDef:
    """
    Universal tag definition for UMI.

    Notes:
    - `tag` is the canonical string emitted by detectors.
    - `category` is the taxonomy bucket used for guidance + aggregation.
    - `aliases` supports normalization from game- or detector-specific naming.
    """
    tag: str
    category: str
    description: str = ""
    aliases: tuple[str, ...] = ()

class PatternTagsTaxonomy:
    """
    Canonical pattern tag taxonomy for UMI.

    Grounded from pattern_signals_export_v2.json:
    Top-level: pattern_and_difficulty_signals
    Categories: flow_patterns, vertical_patterns, directional_patterns,
                alternation_patterns, hand_interaction_tags, precision_tags,
                rhythm_tags, pacing_tags, bpm_density_relation_tags,
                temporal_disruption_tags, readability_tags, slide_complexity_tags,
                duration_structure_tags, multi_lane_patterns
    [1](https://onedrive.live.com/?id=e3024480-35b7-45f7-9d3a-4702b19f7bef&cid=d5d62a1ef303ba22&web=1)
    """

    TAXONOMY_ID = "umi.pattern_tags_taxonomy"
    TAXONOMY_VERSION = "1.0.0"  # bump when you add/remove/rename canonical tags

    # ------------- Canonical category list (from pattern_signals_export_v2.json) -------------
    CATEGORIES: tuple[str, ...] = (
        "flow_patterns",
        "vertical_patterns",
        "directional_patterns",
        "alternation_patterns",
        "hand_interaction_tags",
        "precision_tags",
        "rhythm_tags",
        "pacing_tags",
        "bpm_density_relation_tags",
        "temporal_disruption_tags",
        "readability_tags",
        "slide_complexity_tags",
        "duration_structure_tags",
        "multi_lane_patterns",
    )

    # ------------- Canonical tags (from pattern_signals_export_v2.json) -------------
    # [1](https://onedrive.live.com/?id=e3024480-35b7-45f7-9d3a-4702b19f7bef&cid=d5d62a1ef303ba22&web=1)
    TAGS_BY_CATEGORY: Dict[str, List[str]] = {
        "flow_patterns": [
            "stream",
            "burst",
            "burst.start",
            "burst.end",
        ],
        "vertical_patterns": [
            "jump",
            "wide_jump",
            "stacked_chords",
        ],
        "directional_patterns": [
            "stair_single",
            "stairway_left",
            "stairway_right",
            "spiral_stairway",
            "zig-zag_stair",
        ],
        "alternation_patterns": [
            "trill_vertical",
            "trill_alternating",
            "trill_hybrid",
        ],
        "hand_interaction_tags": [
            "cross_hand",
            "forced_hand_swap",
        ],
        "precision_tags": [
            "tiny_notes",
            "tiny_hold",
            "tight_spacing",
        ],
        "rhythm_tags": [
            "difficult_rhythm",
            "syncopated",
            "swing_rhythm",
        ],
        "pacing_tags": [
            "bpm_shift",
            "sudden_speedup",
            "sudden_slowdown",
        ],
        "bpm_density_relation_tags": [
            "low_bpm_high_density",
        ],
        "temporal_disruption_tags": [
            "chart_stop",
            "fake_end",
            "post_climax_spike",
        ],
        "readability_tags": [
            "low_visibility",
            "long_short_taps_mix",
            "stacked_chords",  # appears here as well as vertical_patterns
        ],
        "slide_complexity_tags": [
            "notes_within_slide",
            "trace_flick",
        ],
        "duration_structure_tags": [
            "duration=>02:30",
            "endurance_focus",
        ],
        "multi_lane_patterns": [
            "multi_keys",
        ],
    }

    # ------------- Optional: richer tag definitions (descriptions + aliases) -------------
    # Use this if you want a single normalization/validation source of truth.
    # The tags themselves are grounded; descriptions/aliases are intentionally minimal and safe.
    TAG_DEFS: Dict[str, TagDef] = {
        # flow
        "stream": TagDef("stream", "flow_patterns", "Sustained dense tapping / continuous note flow."),
        "burst": TagDef("burst", "flow_patterns", "Short high-density segment."),
        "burst.start": TagDef("burst.start", "flow_patterns", "Onset of a burst (ramp-in)."),
        "burst.end": TagDef("burst.end", "flow_patterns", "Offset of a burst (release)."),

        # vertical
        "jump": TagDef("jump", "vertical_patterns", "Simultaneous multi-note hit."),
        "wide_jump": TagDef("wide_jump", "vertical_patterns", "Simultaneous hit with wide spacing."),
        "stacked_chords": TagDef("stacked_chords", "vertical_patterns", "Frequent or complex chords."),

        # directional
        "stair_single": TagDef("stair_single", "directional_patterns", "Single-lane stair / stepwise motion."),
        "stairway_left": TagDef("stairway_left", "directional_patterns", "Stair pattern biased left."),
        "stairway_right": TagDef("stairway_right", "directional_patterns", "Stair pattern biased right."),
        "spiral_stairway": TagDef("spiral_stairway", "directional_patterns", "Spiral-like stair motion."),
        "zig-zag_stair": TagDef("zig-zag_stair", "directional_patterns", "Alternating-direction stair motion."),

        # alternation
        "trill_vertical": TagDef("trill_vertical", "alternation_patterns", "Alternating hits in same/near lane."),
        "trill_alternating": TagDef("trill_alternating", "alternation_patterns", "Regular alternating trill."),
        "trill_hybrid": TagDef("trill_hybrid", "alternation_patterns", "Mixed trill cues / hybrid alternation."),

        # hand interaction
        "cross_hand": TagDef("cross_hand", "hand_interaction_tags", "Hand crossing / crossover."),
        "forced_hand_swap": TagDef("forced_hand_swap", "hand_interaction_tags", "Requires swapping hands/fingers."),

        # precision
        "tiny_notes": TagDef("tiny_notes", "precision_tags", "Small hit windows / micro notes."),
        "tiny_hold": TagDef("tiny_hold", "precision_tags", "Short holds requiring precision."),
        "tight_spacing": TagDef("tight_spacing", "precision_tags", "Very close note spacing."),

        # rhythm
        "difficult_rhythm": TagDef("difficult_rhythm", "rhythm_tags", "Non-trivial rhythm interpretation."),
        "syncopated": TagDef("syncopated", "rhythm_tags", "Syncopation / off-beat emphasis."),
        "swing_rhythm": TagDef("swing_rhythm", "rhythm_tags", "Swing-like rhythmic feel."),

        # pacing
        "bpm_shift": TagDef("bpm_shift", "pacing_tags", "Tempo change / speed shift."),
        "sudden_speedup": TagDef("sudden_speedup", "pacing_tags", "Abrupt increase in speed."),
        "sudden_slowdown": TagDef("sudden_slowdown", "pacing_tags", "Abrupt decrease in speed."),

        # bpm-density relation
        "low_bpm_high_density": TagDef("low_bpm_high_density", "bpm_density_relation_tags", "Low BPM but dense notes."),

        # temporal disruption
        "chart_stop": TagDef("chart_stop", "temporal_disruption_tags", "Stop / pause / interruption."),
        "fake_end": TagDef("fake_end", "temporal_disruption_tags", "Fake ending / deceptive structure."),
        "post_climax_spike": TagDef("post_climax_spike", "temporal_disruption_tags", "Difficulty spike after climax."),

        # readability
        "low_visibility": TagDef("low_visibility", "readability_tags", "Hard to read visually."),
        "long_short_taps_mix": TagDef("long_short_taps_mix", "readability_tags", "Mix of long/short taps affecting readability."),

        # slide complexity
        "notes_within_slide": TagDef("notes_within_slide", "slide_complexity_tags", "Notes embedded within slide paths."),
        "trace_flick": TagDef("trace_flick", "slide_complexity_tags", "Trace or path-followed flick/gesture."),

        # duration/structure
        "duration=>02:30": TagDef("duration=>02:30", "duration_structure_tags", "Long chart duration threshold signal."),
        "endurance_focus": TagDef("endurance_focus", "duration_structure_tags", "Endurance/physical stamina emphasis."),

        # multi-lane
        "multi_keys": TagDef("multi_keys", "multi_lane_patterns", "More lanes/keys than baseline."),
    }

    @classmethod
    def all_tags(cls) -> Set[str]:
        tags: Set[str] = set()
        for _, lst in cls.TAGS_BY_CATEGORY.items():
            tags.update(lst)
        return tags

    @classmethod
    def tag_category(cls, tag: str) -> Optional[str]:
        if tag in cls.TAG_DEFS:
            return cls.TAG_DEFS[tag].category
        # fallback: search map
        for cat, lst in cls.TAGS_BY_CATEGORY.items():
            if tag in lst:
                return cat
        return None

    @classmethod
    def validate_tags(cls, tags: List[str]) -> List[str]:
        """
        Return list of unknown tags (i.e., not in canonical taxonomy).
        """
        known = cls.all_tags()
        return [t for t in tags if t not in known]

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        """
        Normalize using aliases if you define them.
        Currently minimal; extend safely without breaking canonical tags.
        """
        # direct canonical
        if tag in cls.TAG_DEFS:
            return tag
        # alias lookup
        for tdef in cls.TAG_DEFS.values():
            if tag in tdef.aliases:
                return tdef.tag
        return tag
