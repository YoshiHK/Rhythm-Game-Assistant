#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_maimai.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for maimai.

Design goals
------------
- additive only
- do not rewrite completed MA2 / Simai parsing logic
- provide stable canonical payload contract for validator/schema
- preserve raw timing / token information in extra
- keep gameplay semantics conservative

This adapter:
- Parses MA2 (tab-delimited) and Simai (token) formats.
- Preserves Simai slide segmentation and duration redistribution logic.
- Normalizes gameplay notes into canonical note_events.
- Moves BPM / measure events into chart_meta instead of note_events.
- Computes time_beats ordering and stores time_ms / end_time_ms in extra.

Non-goal
--------
- No gameplay semantics inference
- No tips generation
- No Phase 4 logic
"""

import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    build_standard_diagnostics,
    attach_if_missing,
    with_baseline_fallback_extensions,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "maimai"
_ADAPTER_ID = "adapter_maimai"
_ADAPTER_VERSION = "2.0.0"
_SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_maimai", "v2")

_RE_BRACKET_DIFF = re.compile(r"\[(?P<diff>[^\]]+)\]")

_TOUCH_GROUP = set(list("ABCDEF"))
_ALLOWED_SLIDE_TYPE = {"qq", "q", "pp", "p", "v", "w", "<", ">", "^", "s", "z", "V", "-"}
_SLIDE_NOTATION_CHARS = set(list("-vw<>pqszV^"))

# Canonical kinds used by payload contract
_CANONICAL_KINDS = {
    "tap",
    "hold_body_or_start",
    "hold_path",
}

@dataclass
class MaimaiIngestRaw:
    chart_path: Path
    song_id: str
    difficulty: str
    source_format: str
    definition: int
    bpm_changes: List[Dict[str, Any]]
    note_events: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def _infer_song_id_and_difficulty(path: Path) -> Tuple[str, str]:
    stem = path.stem
    diff = "UNKNOWN"
    song = stem
    m = _RE_BRACKET_DIFF.search(stem)
    if m:
        diff = (m.group("diff") or "").strip() or diff
        song = (stem[:m.start()].strip() or stem)
    return song, diff.upper()


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _detect_format(text: str) -> str:
    if "COMPATIBLE_CODE\tMA2" in text:
        return "ma2"
    if "inote_" in text and "&" in text:
        return "simai"
    if "\nE\n" in text or text.strip().endswith("E"):
        return "simai"
    return "unknown"


def _time_beats(bar: int, tick: int, definition: int) -> float:
    return float(bar) * 4.0 + (float(tick) / float(definition)) * 4.0


def _tickstamp(bar: int, tick: int, definition: int) -> int:
    return int(bar) * int(definition) + int(tick)


def _get_bpm_time_unit(bpm: float, definition: int) -> float:
    if bpm <= 0:
        return 0.0
    return (60.0 / float(bpm)) * (4.0 / float(definition))


def _normalize_bpm_changes(changes: List[Dict[str, Any]], definition: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in changes:
        if not isinstance(c, dict):
            continue
        bar = int(c.get("bar", 0))
        tick = int(c.get("tick", 0))
        bpm = float(c.get("bpm", 0.0))
        ts = _tickstamp(bar, tick, definition)
        out.append({
            "bar": bar,
            "tick": tick,
            "bpm": bpm,
            "tickstamp": ts,
            "bpm_unit": _get_bpm_time_unit(bpm, definition),
        })
    out.sort(key=lambda d: d["tickstamp"])
    return out


def _time_stamp_from_bpm_changes(change_table: List[Dict[str, Any]], overall_tick: int) -> Optional[float]:
    if overall_tick <= 0:
        return 0.0
    if not change_table:
        return None

    idx = 0
    for i, c in enumerate(change_table):
        if int(c.get("tickstamp", 0)) <= overall_tick:
            idx = i

    if idx == 0:
        return float(change_table[0].get("bpm_unit", 0.0)) * float(overall_tick)

    total = 0.0
    for i in range(1, idx + 1):
        prev = change_table[i - 1]
        cur = change_table[i]
        prev_unit = float(prev.get("bpm_unit", 0.0))
        total += (int(cur["tickstamp"]) - int(prev["tickstamp"])) * prev_unit

    unit = float(change_table[idx].get("bpm_unit", 0.0))
    total += (overall_tick - int(change_table[idx]["tickstamp"])) * unit
    return total


def _attach_time_ms(ev: Dict[str, Any], change_table: List[Dict[str, Any]], definition: int) -> None:
    extra = ev.setdefault("extra", {})
    bar = int(extra.get("bar", 0))
    tick = int(extra.get("tick", 0))
    ts = _tickstamp(bar, tick, definition)
    extra["tickstamp"] = ts
    t = _time_stamp_from_bpm_changes(change_table, ts)
    if t is not None:
        extra["time_ms"] = int(round(t * 1000.0))


# ---------------------------------------------------------------------
# MA2 parsing
# ---------------------------------------------------------------------

_STD_BAR = 1
_STD_TICK = 2
_STD_KEY = 3
_STD_WAIT = 4
_STD_LAST = 5
_STD_ENDKEY = 6


def _ma2_definition(lines: List[str]) -> int:
    for ln in lines:
        if ln.startswith("RESOLUTION\t"):
            tail = ln.split("\t", 1)[1].strip()
            if tail.isdigit():
                return int(tail)
    return 384


def _ma2_bpm_changes(lines: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ln in lines:
        parts = ln.split("\t")
        if len(parts) >= 4 and parts[0] == "BPM":
            out.append({"bar": _safe_int(parts[1]), "tick": _safe_int(parts[2]), "bpm": _safe_float(parts[3])})
    return out


def _ma2_note_events(lines: List[str], definition: int) -> List[Dict[str, Any]]:
    """
    Raw maimai event stream.
    IMPORTANT:
    - includes note-like and timing/meta-like events
    - canonical filtering happens later
    """
    out: List[Dict[str, Any]] = []
    for ln in lines:
        if "\t" not in ln:
            continue
        parts = ln.split("\t")
        typ = parts[0]

        if typ in {"VERSION", "FES_MODE", "RESOLUTION", "CLK_DEF", "COMPATIBLE_CODE"}:
            continue
        if typ.startswith("T_REC_") or typ.startswith("T_NUM_") or typ.startswith("T_JUDGE_") or typ.startswith("TTM_"):
            continue

        if len(parts) <= _STD_TICK:
            continue

        bar = _safe_int(parts[_STD_BAR])
        tick = _safe_int(parts[_STD_TICK])
        key = parts[_STD_KEY] if len(parts) > _STD_KEY else ""

        if typ == "BPM" and len(parts) >= 4:
            bpm = _safe_float(parts[3])
            out.append({
                "time_beats": _time_beats(bar, tick, definition),
                "kind": "bpm_change",
                "extra": {
                    "raw_type": "BPM",
                    "bar": bar,
                    "tick": tick,
                    "bpm": bpm,
                    "definition": definition,
                    "raw_parts": parts,
                },
            })
            continue

        if typ == "MET" and len(parts) >= 5:
            quaver = _safe_int(parts[_STD_KEY])
            wait = _safe_int(parts[_STD_WAIT])
            out.append({
                "time_beats": _time_beats(bar, tick, definition),
                "kind": "measure_change",
                "extra": {
                    "raw_type": "MET",
                    "bar": bar,
                    "tick": tick,
                    "quaver": quaver,
                    "wait": wait,
                    "definition": definition,
                    "raw_parts": parts,
                },
            })
            continue

        if typ in {"TAP", "STR", "XTP", "XST", "BRK", "BST"}:
            kind = "maimai_tap"
        elif typ == "TTP":
            kind = "maimai_touch"
        elif typ in {"HLD", "XHO", "THO"}:
            kind = "maimai_hold"
        elif typ.startswith("S") or typ in {"SI_", "SV_", "SF_", "SCL", "SCR", "SUL", "SUR", "SLL", "SLR", "SXL", "SXR", "SSL", "SSR"}:
            kind = "maimai_slide"
        else:
            kind = "maimai_event"

        extra: Dict[str, Any] = {
            "raw_type": typ,
            "bar": bar,
            "tick": tick,
            "key": key,
            "definition": definition,
            "raw_parts": parts,
        }

        if kind == "maimai_slide" and len(parts) > _STD_LAST:
            extra["wait_len_ticks"] = _safe_int(parts[_STD_WAIT])
            extra["last_len_ticks"] = _safe_int(parts[_STD_LAST])
            if len(parts) > _STD_ENDKEY:
                extra["end_key"] = parts[_STD_ENDKEY]

        if kind == "maimai_hold" and len(parts) > _STD_WAIT:
            extra["last_len_ticks"] = _safe_int(parts[_STD_WAIT])

        out.append({
            "time_beats": _time_beats(bar, tick, definition),
            "kind": kind,
            "extra": extra,
        })

    out.sort(key=lambda e: (float(e.get("time_beats", 0.0)), str(e.get("kind", ""))))
    return out


# ---------------------------------------------------------------------
# Simai parsing + slide segmentation
# ---------------------------------------------------------------------

def _simai_strip_ws(text: str) -> str:
    return "".join(ch for ch in text if not ch.isspace())


def _simai_tokens_from_text(text: str) -> List[str]:
    return _simai_strip_ws(text).split(",")


def _simai_parse_meta_and_charts(text: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    info: Dict[str, str] = {}
    charts: Dict[str, List[str]] = {}
    for item in text.split("&"):
        if not item:
            continue
        if "title=" in item:
            info["Name"] = item.replace("title=", "").replace("[SD]", "").replace("[DX]", "")
        elif "wholebpm=" in item:
            info["BPM"] = item.replace("wholebpm=", "")
        elif "artist=" in item:
            info["Composer"] = item.replace("artist=", "")
        elif "shortid=" in item:
            info["Music ID"] = item.replace("shortid=", "")
        elif "inote_" in item and "=" in item:
            k, v = item.split("=", 1)
            charts[k.replace("inote_", "")] = _simai_tokens_from_text(v)
    return info, charts


def _simai_each_group_of_token(token: str) -> List[str]:
    buf = ""
    extracted: List[str] = []
    for c in token:
        if c == "/":
            extracted.append(buf)
            buf = ""
        elif c in "({":
            if buf:
                extracted.append(buf)
            buf = c
        elif c in ")}":
            buf += c
            extracted.append(buf)
            buf = ""
        elif c == "`":
            buf += "%"
            extracted.append(buf)
            buf = ""
        else:
            buf += c
    if buf:
        extracted.append(buf)

    out: List[str] = []
    for part in extracted:
        if part.isdigit():
            out.extend(list(part))
        else:
            out.append(part)
    return out


def _simai_is_slide_notation(ch: str) -> bool:
    return ch in _SLIDE_NOTATION_CHARS


def _simai_contains_slide_notation(token: str) -> bool:
    return any(c in token for c in _SLIDE_NOTATION_CHARS)


def _simai_replace_duration(old_value: str, new_duration: str) -> str:
    out = []
    ignoring = False
    for ch in old_value:
        if ch == "[":
            ignoring = True
        if not ignoring:
            out.append(ch)
        if ignoring and ch == "]":
            ignoring = False
    base = "".join(out)
    if "CN" in base:
        left, right = base.split("CN", 1)
        return f"{left}{new_duration}CN{right}"
    return base + new_duration


def _simai_extract_connecting_slides(token: str) -> List[str]:
    origin = token
    result: List[str] = []
    slide_candidate = ""
    first_segment_extracted = False

    while token:
        if _simai_is_slide_notation(token[0]):
            notation = token[:2] if token[:2] in ("pp", "qq") else token[0]
            if notation not in _ALLOWED_SLIDE_TYPE:
                raise ValueError(f"Unexpected slide type: {notation} in slide: {origin}")
            if slide_candidate == "" and first_segment_extracted:
                raise ValueError(f"Unexpected occurrence of slide notation: {notation} in slide: {origin}")
            if slide_candidate:
                result.append(slide_candidate)
            first_segment_extracted = True
            slide_candidate = ""
        elif token[0].isdigit():
            notation = token[0]
        elif token[0] == "[":
            end = token.find("]")
            if end == -1:
                raise ValueError(f"Unclosed time notation: {token}")
            notation = token[: end + 1]
        else:
            raise ValueError(f"Cannot parse notation {token} in slide: {origin}")

        slide_candidate += notation
        token = token[len(notation):]

    if slide_candidate:
        result.append(slide_candidate)

    # CN injection
    start = 1 if result and _simai_is_slide_notation(result[0][0]) else 2
    if result and result[0].startswith("1_"):
        start = 2
    for i in range(len(result) - 1, start - 1, -1):
        prev = result[i - 1]
        if prev.endswith("]"):
            prev = prev[: prev.find("[")]
        last_key = int(prev[-1])
        result[i] = result[i] + "CN" + str(last_key - 1)

    # duration redistribution
    if sum(1 for p in result if "[" in p) == 0:
        raise ValueError("Extracted slides do not contain any duration setting: " + ", ".join(result))

    slide_parts = sum(1 for p in result if any(s in p for s in _ALLOWED_SLIDE_TYPE))
    duration_parts = sum(1 for p in result if "[" in p)

    if slide_parts >= 2 and duration_parts == 1:
        slide_duration_candidate = next(p for p in result if "[" in p)
        new_duration_candidate = "[" + slide_duration_candidate.split("[", 1)[1].split("CN")[0]
        actual_slide_part = sum(1 for p in result if "_" not in p)

        is_measure_duration = (":" in new_duration_candidate) and ("#" not in new_duration_candidate)

        if is_measure_duration:
            body = new_duration_candidate.strip("[]")
            q_s, m_s = body.split(":", 1)
            quaver = int(q_s) * actual_slide_part
            multiple = int(m_s)
            new_duration_candidate = f"[{quaver}:{multiple}]"
            write_original_wait = False
            original_wait = 0.0
            avg_last = 0.0
        else:
            body = new_duration_candidate.strip("[]")
            if "##" in body:
                wait_s, last_s = body.split("##", 1)
                original_wait = float(wait_s)
                total_last = float(last_s)
            elif body.startswith("#"):
                original_wait = 0.0
                total_last = float(body[1:])
            else:
                original_wait = 0.0
                total_last = float(body) if body else 0.0
            avg_last = round(total_last / max(1, actual_slide_part), 4)
            new_duration_candidate = f"[0##{avg_last}]"
            write_original_wait = True

        wrote_original = not write_original_wait
        start_i = 1 if "_" in result[0] else 0
        for i in range(start_i, len(result)):
            if write_original_wait and not wrote_original:
                dur = f"[{round(original_wait, 4)}##{avg_last}]"
                result[i] = _simai_replace_duration(result[i], dur)
                wrote_original = True
            else:
                result[i] = _simai_replace_duration(result[i], new_duration_candidate)

    return result


def _simai_get_time_candidates(bpm: float, input_str: str, definition: int, is_slide: bool) -> Tuple[float, float]:
    if not (input_str.startswith("[") and input_str.endswith("]")):
        raise ValueError("duration must be bracketed")
    dur = input_str[1:-1]

    is_measure_duration = (":" in dur) and ("#" not in dur)
    is_slide_timed = ("##" in dur) and (":" not in dur)
    is_hold_timed = (not is_slide_timed) and ("#" in dur) and (":" not in dur)
    is_slide_bpm_measure = ("##" in dur) and ("#" in dur) and (":" in dur)
    is_hold_bpm_measure = (not is_slide_bpm_measure) and ("#" in dur) and (":" in dur)

    wait = 0.0
    last = 0.0

    if is_measure_duration:
        q_s, beat_s = dur.split(":", 1)
        q = float(q_s)
        beat = float(beat_s)
        last = _get_bpm_time_unit(bpm, definition) * (definition / q) * beat
        wait = 0.0
    elif is_slide_timed:
        a, b = dur.split("##", 1)
        wait = float(a)
        last = float(b)
    elif is_hold_timed:
        left, right = dur.split("#", 1)
        is_slide_reassigned = len(left) != 0
        if is_slide_reassigned:
            bpm_candidate = float(left)
            wait = _get_bpm_time_unit(bpm_candidate, definition) * (definition / 4)
            last = float(right)
        else:
            wait = 0.0
            last = float(right)
    elif is_slide_bpm_measure:
        wait_s, rest = dur.split("##", 1)
        bpm_s, qb = rest.split("#", 1)
        q_s, beat_s = qb.split(":", 1)
        bpm_candidate = float(bpm_s)
        q = float(q_s)
        beat = float(beat_s)
        wait = float(wait_s)
        last = _get_bpm_time_unit(bpm_candidate, definition) * (definition / q) * beat
    elif is_hold_bpm_measure:
        bpm_s, qb = dur.split("#", 1)
        q_s, beat_s = qb.split(":", 1)
        bpm_candidate = float(bpm_s)
        q = float(q_s)
        beat = float(beat_s)
        wait = 0.0
        last = _get_bpm_time_unit(bpm_candidate, definition) * (definition / q) * beat
    else:
        raise ValueError(f"duration pattern not matched: {dur}")

    if is_slide and (is_measure_duration or is_hold_timed):
        wait = _get_bpm_time_unit(bpm, definition) * (definition / 4)
    elif is_slide and is_hold_bpm_measure:
        bpm_candidate = float(dur.split("#", 1)[0])
        wait = _get_bpm_time_unit(bpm_candidate, definition) * (definition / 4)

    return wait, last


def _parse_simai_tokens(tokens: List[str], definition: int = 384) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    time_in_bar = Fraction(0, 1)
    time_step = Fraction(1, 4)
    current_bpm = 0.0

    bpm_changes: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

    diag: Dict[str, Any] = {"tokens_total": len(tokens), "definition": definition}

    for tok in tokens:
        each_notes = _simai_each_group_of_token(tok)
        t = float(time_in_bar)
        bar = int(t // 1)
        tick = int(round((t - bar) * definition))

        for each_note in each_notes:
            if each_note == "" or each_note == "E":
                continue

            # BPM
            if each_note.startswith("(") and each_note.endswith(")"):
                bpm_val = _safe_float(each_note[1:-1], 0.0)
                current_bpm = bpm_val
                bpm_changes.append({"bar": bar, "tick": tick, "bpm": bpm_val})
                continue

            # Measure
            if each_note.startswith("{") and each_note.endswith("}"):
                q = each_note[1:-1]
                quaver = _safe_int(q.replace("#", ""), 0)
                events.append({
                    "time_beats": _time_beats(bar, tick, definition),
                    "kind": "measure_change",
                    "extra": {
                        "raw_token": each_note,
                        "bar": bar,
                        "tick": tick,
                        "quaver": q,
                        "definition": definition,
                    },
                })
                if not q.startswith("#") and quaver > 0:
                    time_step = Fraction(1, quaver)
                continue

            contains_grace = "%" in each_note
            token = each_note.replace("%", "") if contains_grace else each_note

            is_slide = ("[" in token and "]" in token) and _simai_contains_slide_notation(token)
            is_hold = ("h" in token) and ("[" in token and "]" in token) and not is_slide
            is_touch = len(token) >= 1 and token[0] in _TOUCH_GROUP

            if is_slide:
                seg_error = None
                try:
                    segments = _simai_extract_connecting_slides(token)
                except Exception as e:
                    segments = [token]
                    seg_error = str(e)

                base_ts = _tickstamp(bar, tick, definition)
                offset_ticks = 0

                for seg_i, seg in enumerate(segments):
                    seg_ts = base_ts + offset_ticks
                    seg_bar = seg_ts // definition
                    seg_tick = seg_ts % definition

                    extra: Dict[str, Any] = {
                        "raw_token": seg,
                        "bar": int(seg_bar),
                        "tick": int(seg_tick),
                        "definition": definition,
                        "grace": contains_grace,
                        "segment_index": seg_i,
                        "segments_total": len(segments),
                    }
                    if seg_error and seg_i == 0:
                        extra["segmentation_error"] = seg_error

                    if "[" in seg and "]" in seg:
                        dur = "[" + seg.split("[", 1)[1].split("]", 1)[0] + "]"
                        try:
                            wait_sec, last_sec = _simai_get_time_candidates(current_bpm, dur, definition, is_slide=True)
                        except Exception as e:
                            wait_sec, last_sec = 0.0, 0.0
                            extra["duration_parse_error"] = str(e)
                        extra["duration"] = dur
                        extra["wait_time_sec"] = float(wait_sec)
                        extra["last_time_sec"] = float(last_sec)
                        bpm_unit = _get_bpm_time_unit(current_bpm, definition)
                        if bpm_unit > 0:
                            extra["wait_len_ticks"] = int(round(wait_sec / bpm_unit))
                            extra["last_len_ticks"] = int(round(last_sec / bpm_unit))
                            offset_ticks += int(extra.get("wait_len_ticks", 0)) + int(extra.get("last_len_ticks", 0))

                    events.append({
                        "time_beats": _time_beats(int(seg_bar), int(seg_tick), definition),
                        "kind": "maimai_slide",
                        "extra": extra,
                    })

                continue

            if is_hold:
                kind = "maimai_hold"
            elif is_touch:
                kind = "maimai_touch"
            elif token and token[0].isdigit():
                kind = "maimai_tap"
            else:
                kind = "maimai_event"

            extra: Dict[str, Any] = {
                "raw_token": token,
                "bar": bar,
                "tick": tick,
                "definition": definition,
                "grace": contains_grace,
            }

            if kind == "maimai_hold" and "[" in token and "]" in token:
                dur = "[" + token.split("[", 1)[1].split("]", 1)[0] + "]"
                try:
                    wait_sec, last_sec = _simai_get_time_candidates(current_bpm, dur, definition, is_slide=False)
                except Exception as e:
                    wait_sec, last_sec = 0.0, 0.0
                    extra["duration_parse_error"] = str(e)
                extra["duration"] = dur
                extra["wait_time_sec"] = float(wait_sec)
                extra["last_time_sec"] = float(last_sec)
                bpm_unit = _get_bpm_time_unit(current_bpm, definition)
                if bpm_unit > 0:
                    extra["wait_len_ticks"] = int(round(wait_sec / bpm_unit))
                    extra["last_len_ticks"] = int(round(last_sec / bpm_unit))

            events.append({
                "time_beats": _time_beats(bar, tick, definition),
                "kind": kind,
                "extra": extra,
            })

        time_in_bar += time_step

    events.sort(key=lambda e: (float(e.get("time_beats", 0.0)), str(e.get("kind", ""))))
    return events, bpm_changes, diag


# ---------------------------------------------------------------------
# Canonical normalization
# ---------------------------------------------------------------------

def _map_raw_kind_to_canonical(raw_kind: str) -> Optional[str]:
    """
    Conservative canonical mapping.

    We intentionally normalize:
    - maimai_tap / maimai_touch -> tap
    - maimai_hold              -> hold_body_or_start
    - maimai_slide             -> hold_path

    Non-note / meta events return None and are moved to chart_meta / diagnostics.
    """
    if raw_kind in {"maimai_tap", "maimai_touch"}:
        return "tap"
    if raw_kind == "maimai_hold":
        return "hold_body_or_start"
    if raw_kind == "maimai_slide":
        return "hold_path"
    return None


def _normalize_raw_events_to_payload(
    *,
    events: List[Dict[str, Any]],
    bpm_table: List[Dict[str, Any]],
    definition: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """
    Split raw parser output into:
    - canonical note_events
    - chart_meta additions
    - diagnostics additions
    """
    note_events: List[Dict[str, Any]] = []
    bpm_changes: List[Dict[str, Any]] = []
    measure_markers: List[float] = []

    diagnostics_extra: Dict[str, Any] = {
        "raw_event_count": len(events),
        "ignored_event_count": 0,
        "measure_event_count": 0,
        "touch_event_count": 0,
        "slide_event_count": 0,
        "hold_event_count": 0,
    }

    for ev in events:
        if not isinstance(ev, dict):
            diagnostics_extra["ignored_event_count"] += 1
            continue

        raw_kind = str(ev.get("kind", ""))
        extra = ev.get("extra")
        if not isinstance(extra, dict):
            extra = {}

        # meta/timing events -> chart_meta
        if raw_kind == "bpm_change":
            bpm = _safe_float(extra.get("bpm"), 0.0)
            bpm_changes.append({
                "time_beats": float(ev.get("time_beats", 0.0)),
                "bpm": bpm,
                "time_ms": int(extra.get("time_ms")) if isinstance(extra.get("time_ms"), int) else None,
            })
            continue

        if raw_kind == "measure_change":
            measure_markers.append(float(ev.get("time_beats", 0.0)))
            diagnostics_extra["measure_event_count"] += 1
            continue

        canonical_kind = _map_raw_kind_to_canonical(raw_kind)
        if canonical_kind is None:
            diagnostics_extra["ignored_event_count"] += 1
            continue

        if raw_kind == "maimai_touch":
            diagnostics_extra["touch_event_count"] += 1
        elif raw_kind == "maimai_slide":
            diagnostics_extra["slide_event_count"] += 1
        elif raw_kind == "maimai_hold":
            diagnostics_extra["hold_event_count"] += 1

        canonical_extra: Dict[str, Any] = {
            "raw_type": raw_kind,
        }

        # preserve parser metadata
        for k in (
            "raw_token",
            "bar",
            "tick",
            "definition",
            "grace",
            "segment_index",
            "segments_total",
            "duration",
            "wait_time_sec",
            "last_time_sec",
            "wait_len_ticks",
            "last_len_ticks",
            "key",
            "end_key",
            "quaver",
            "tickstamp",
            "time_ms",
        ):
            if k in extra:
                canonical_extra[k] = extra[k]

        # hold / slide => expose duration-like fields to canonical schema-compatible extra
        if raw_kind in {"maimai_hold", "maimai_slide"}:
            canonical_extra["shape"] = "slide" if raw_kind == "maimai_slide" else "hold"

            if isinstance(extra.get("last_len_ticks"), int):
                canonical_extra["duration_ticks"] = int(extra["last_len_ticks"])

            if isinstance(extra.get("last_time_sec"), (int, float)):
                canonical_extra["duration_sec"] = float(extra["last_time_sec"])
                canonical_extra["rect_height"] = float(extra["last_time_sec"])

        # touch can be marked in extra only
        if raw_kind == "maimai_touch":
            canonical_extra["surface"] = "touch"

        note_events.append({
            "time_beats": float(ev.get("time_beats", 0.0)),
            "lane": 0,  # conservative baseline; maimai uses radial/touch geometry
            "kind": canonical_kind,
            "extra": canonical_extra,
        })

    chart_meta_extra: Dict[str, Any] = {}
    if bpm_changes:
        chart_meta_extra["bpm_changes"] = bpm_changes
    if measure_markers:
        chart_meta_extra["measure_markers"] = measure_markers

    return note_events, chart_meta_extra, diagnostics_extra


# ---------------------------------------------------------------------
# Canonical payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_maimai(
    source_ref: str,
    *,
    preferred_simai_diff: Optional[str] = None,
) -> Dict[str, Any]:
    path = Path(source_ref)
    text = path.read_text(encoding="utf-8", errors="ignore")
    fmt = _detect_format(text)

    song_id, diff = _infer_song_id_and_difficulty(path)

    definition = 384
    bpm_changes_raw: List[Dict[str, Any]] = []
    raw_events: List[Dict[str, Any]] = []
    diag: Dict[str, Any] = {}

    if fmt == "ma2":
        lines = text.splitlines()
        definition = _ma2_definition(lines)
        bpm_changes_raw = _ma2_bpm_changes(lines)
        raw_events = _ma2_note_events(lines, definition)
        diag["ma2_lines"] = len(lines)

    elif fmt == "simai":
        info, charts = _simai_parse_meta_and_charts(text)
        chosen_key: Optional[str] = None
        if preferred_simai_diff and preferred_simai_diff in charts:
            chosen_key = preferred_simai_diff
        elif charts:
            chosen_key = sorted(charts.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]

        simai_tokens = charts.get(chosen_key) if chosen_key else _simai_tokens_from_text(text)
        raw_events, bpm_changes_raw, diag2 = _parse_simai_tokens(simai_tokens or [], definition=384)
        diag.update({
            "simai_meta": info,
            "simai_chart_candidates": sorted(list(charts.keys())),
            "simai_selected": chosen_key,
            **diag2,
        })

        if info.get("Music ID"):
            song_id = info.get("Music ID")
        elif info.get("Name"):
            song_id = info.get("Name")

    bpm_table = _normalize_bpm_changes(bpm_changes_raw, definition)

    for ev in raw_events:
        _attach_time_ms(ev, bpm_table, definition)
        extra = ev.get("extra") or {}
        if isinstance(extra, dict) and ev.get("kind") in {"maimai_hold", "maimai_slide"}:
            if "time_ms" in extra and isinstance(extra["time_ms"], int):
                wt = float(extra.get("wait_time_sec", 0.0))
                lt = float(extra.get("last_time_sec", 0.0))
                if wt or lt:
                    extra["end_time_ms"] = int(round(extra["time_ms"] + (wt + lt) * 1000.0))

    note_events, chart_meta_extra, diagnostics_extra = _normalize_raw_events_to_payload(
        events=raw_events,
        bpm_table=bpm_table,
        definition=definition,
    )

    bpm_base = bpm_table[0]["bpm"] if bpm_table else 0.0

    max_time_beats = 0.0
    max_time_ms: Optional[int] = None
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time_beats = max(max_time_beats, float(tb))
        extra = ev.get("extra")
        if isinstance(extra, dict):
            tms = extra.get("end_time_ms") if isinstance(extra.get("end_time_ms"), int) else extra.get("time_ms")
            if isinstance(tms, int):
                max_time_ms = tms if max_time_ms is None else max(max_time_ms, tms)

    chart_meta: Dict[str, Any] = {
        "definition": int(definition),
        "bpm": float(bpm_base) if bpm_base else 0.0,
        "max_time_beats": float(max_time_beats),
    }
    if max_time_ms is not None:
        chart_meta["max_time_ms"] = int(max_time_ms)

    for k, v in chart_meta_extra.items():
        chart_meta[k] = v

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": _ADAPTER_ID,
        "adapter_version": _ADAPTER_VERSION,
        "source_format": fmt,
        "source_path": str(path),
        "notes": "maimai adapter with MA2 / Simai parsing, slide segmentation, and canonical normalized output.",
    }

    parse_level = "events_v4_normalized" if note_events else "tokens_only"

    diagnostics: Dict[str, Any] = {
        "parse_level": parse_level,
        "note_events_total": len(note_events),
        "raw_event_total": len(raw_events),
        "bpm_change_count": len(bpm_table),
        **diagnostics_extra,
        **diag,
    }

    internal_metadata = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes="structural-only; no gameplay inference",
        extra={"parse_level": parse_level},
    )

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": str(path.resolve()),
        "title": str(song_id),
        "difficulty": str(diff).upper(),

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "sections": [],
        "song_id": str(song_id),            # compatibility alias
        "difficulty_name": str(diff).upper() # compatibility alias
    }

    attach_if_missing(payload, "diagnostics", diagnostics)
    attach_if_missing(payload, "internal_metadata", internal_metadata)

    return payload


# ---------------------------------------------------------------------
# Adapter implementation
# ---------------------------------------------------------------------

class MaimaiAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = _ADAPTER_ID
    adapter_version = _ADAPTER_VERSION

    def accepts_file(self, path: Any) -> bool:
        p = Path(path)
        allowed = with_baseline_fallback_extensions(
            [".ma2", ".simai", ".txt"],
            include_baseline=False,
        )
        return p.suffix.casefold() in allowed

    def load(self, path: Any) -> MaimaiIngestRaw:
        p = Path(path)

        try:
            payload = build_canonical_payload_maimai(str(p))
        except Exception:
            payload = {}

        if not isinstance(payload, dict):
            payload = {}

        chart_meta = payload.get("chart_meta") or {}
        diag = payload.get("diagnostics") or {}
        song_id, diff = _infer_song_id_and_difficulty(p)

        events = payload.get("note_events") or []
        bpm_changes = chart_meta.get("bpm_changes") or []
        definition = int(chart_meta.get("definition") or 384)

        return MaimaiIngestRaw(
            chart_path=p,
            song_id=str(payload.get("song_id") or song_id),
            difficulty=str(payload.get("difficulty") or diff),
            source_format=str(payload.get("adapter_metadata", {}).get("source_format") or "unknown"),
            definition=definition,
            bpm_changes=list(bpm_changes) if isinstance(bpm_changes, list) else [],
            note_events=list(events) if isinstance(events, list) else [],
            diagnostics=dict(diag) if isinstance(diag, dict) else {},
        )

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_maimai(source_ref)
        if not isinstance(payload, dict):
            payload = {}

        p = Path(source_ref)

        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}

        diagnostics.setdefault("game_id", self.game_id)
        diagnostics.setdefault("adapter_id", self.adapter_id)
        diagnostics.setdefault("adapter_version", self.adapter_version)
        diagnostics.setdefault("source_path", str(p))

        try:
            diag = build_standard_diagnostics(payload.get("sections"))
            for k, v in diag.items():
                diagnostics.setdefault(k, v)
        except Exception:
            pass

        payload["diagnostics"] = diagnostics

        internal_meta = payload.get("internal_metadata")
        if not isinstance(internal_meta, dict):
            internal_meta = {}

        try:
            meta = build_internal_metadata(
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                sections_source="maimai",
            )
            for k, v in meta.items():
                internal_meta.setdefault(k, v)
        except Exception:
            pass

        try:
            internal_meta.setdefault(
                "canonical_sections_version",
                canonical_sections_version(self.game_id, "maimai"),
            )
        except Exception:
            pass

        payload["internal_metadata"] = internal_meta

        # CRITICAL: enforce v2 contract here
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(p),
            default_chart_id=payload.get("chart_id") or str(p.resolve()),
            default_difficulty=payload.get("difficulty") or "UNKNOWN",
        )

        return payload

    def to_canonical_row(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, MaimaiIngestRaw):
            payload = self.to_canonical_payload(str(raw.chart_path))
            source_path = str(raw.chart_path)
        elif isinstance(raw, dict):
            payload = raw
            source_path = str(raw.get("chart_id") or raw.get("source_path") or "")
        else:
            source_path = str(raw)
            payload = self.to_canonical_payload(source_path)

        if not isinstance(payload, dict):
            payload = {}

        diag = payload.get("diagnostics")
        if not isinstance(diag, dict):
            diag = {}

        events = payload.get("note_events")
        if not isinstance(events, list):
            events = []

        chart_meta = payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        song_id = payload.get("song_id")
        if not isinstance(song_id, str) or not song_id.strip():
            p = Path(source_path) if source_path else None
            song_id = _infer_song_id_and_difficulty(p)[0] if p else None

        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            title = song_id

        difficulty = payload.get("difficulty") or payload.get("difficulty_name") or "UNKNOWN"

        note_total = len(events)

        return {
            "game": self.game_id,
            "game_id": self.game_id,
            "song_id": song_id,
            "name": title,
            "title": title,
            "tier": difficulty,
            "level": None,
            "difficulty_code": None,
            "difficulty_label": difficulty,
            "note_total_chart": int(note_total),
            "note_total_db": None,
            "note_delta": None,
            "duration_ms": chart_meta.get("max_time_ms"),
            "bpm": chart_meta.get("bpm"),
            "rating_raw": None,
            "chart_path": source_path or payload.get("chart_id"),
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "touch_radial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_bpm_changes": True,
            "supports_width": False,
            "emits_canonical_payload": True,
            "source_format": "ma2/simai",
            "parse_level": "events_v4_normalized",
            "time_unit": "beats+ms",
        }


__all__ = [
    "MaimaiAdapter",
    "MaimaiIngestRaw",
    "build_canonical_payload_maimai",
]