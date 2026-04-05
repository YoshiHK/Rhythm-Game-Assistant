"""proseka_element_alignment.py

Companion alignment file for Project SEKAI chart analysis.

Purpose:
- Align canonical (English, system-facing) element identifiers
  with the official Japanese element labels used in the
  proseka_internal_analysis_schema_v1.3.0 (official element list).
- Provide a single source of truth for name translation and grouping.

This file contains NO logic, scoring, or inference rules.
"""

from typing import Dict, List

# Canonical element IDs used internally by the analysis / inference system
CANONICAL_ELEMENTS: List[str] = [
    "stream",
    "burst",
    "stacked_chord",
    "trill",
    "cross_hand",
    "stair",
    "vertical_chain",
    "rhythm_complex",
    "tiny_notes",
    "readability",
    "hold_interference",
    "slide_complexity",
    "trace_flick",
    "flick_density",
    "low_bpm_high_density",
    "bpm_shift",
    "chart_stop",
    "fake_end",
    "endurance"
]

# Mapping to official Japanese element labels (schema v1.3.0)
ELEMENT_ALIGNMENT: Dict[str, List[str]] = {
    "stream": ["物量", "乱打"],
    "burst": ["局所難"],
    "stacked_chord": ["縦連", "微縦連", "多点押し", "5k", "6k"],
    "trill": ["トリル"],
    "cross_hand": ["持ち替え・交差", "混フレ"],
    "stair": ["階段", "くの字"],
    "vertical_chain": ["縦連", "微縦連"],
    "rhythm_complex": ["リズム難", "ハネリズム", "変拍子"],
    "tiny_notes": ["極小ノーツ"],
    "readability": ["視認難", "認識難"],
    "hold_interference": ["終点判定"],
    "slide_complexity": ["スライド難", "トレース難"],
    "trace_flick": ["トレース難", "フリック難"],
    "flick_density": ["フリック難"],
    "low_bpm_high_density": ["物量"],
    "bpm_shift": ["速度変化"],
    "chart_stop": ["譜面停止"],
    "fake_end": ["譜面停止"],
    "endurance": ["長時間"]
}

# Reverse lookup: JP label -> canonical ID
JP_TO_CANONICAL: Dict[str, str] = {}
for canonical, jp_list in ELEMENT_ALIGNMENT.items():
    for jp in jp_list:
        JP_TO_CANONICAL[jp] = canonical

__all__ = [
    "CANONICAL_ELEMENTS",
    "ELEMENT_ALIGNMENT",
    "JP_TO_CANONICAL"
]
