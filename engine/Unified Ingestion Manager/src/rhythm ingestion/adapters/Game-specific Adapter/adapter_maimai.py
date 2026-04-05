#!/usr/bin/env python3
"""adapter_maimai.py

UMI Phase 3 adapter for **maimai**.

Triangular-audit alignment:
- ADAPTER_V2_SPEC.md: implements required methods (accepts_file/load/to_canonical_row) and
  provides optional to_canonical_payload + capabilities. Adapters remain structural normalizers only.
- common_adapter_utils.py: uses build_internal_metadata() and attach_if_missing() to keep outputs additive.

This adapter:
- Parses MA2 (tab-delimited) and Simai (token) formats.
- For Simai slides, ports ExtractConnectingSlides-style segmentation and duration redistribution.
- Emits conservative maimai-specific kinds (maimai_tap/hold/slide/touch) plus bpm_change/measure_change.
- Computes time_beats for ordering and time_ms using BPM tick-unit math.

Non-goal:
- No gameplay semantics or tips generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter
from .common_adapter_utils import build_internal_metadata, attach_if_missing


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


_ADAPTER_ID = 'adapter_maimai'
_ADAPTER_VERSION = '0.4.1'

_RE_BRACKET_DIFF = re.compile(r"\[(?P<diff>[^\]]+)\]")


def _infer_song_id_and_difficulty(path: Path) -> Tuple[str, str]:
    stem = path.stem
    diff = 'UNKNOWN'
    song = stem
    m = _RE_BRACKET_DIFF.search(stem)
    if m:
        diff = (m.group('diff') or '').strip() or diff
        song = (stem[:m.start()].strip() or stem)
    return song, diff


def _safe_int(x: str, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _safe_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _detect_format(text: str) -> str:
    if 'COMPATIBLE_CODE\tMA2' in text:
        return 'ma2'
    if 'inote_' in text and '&' in text:
        return 'simai'
    if '\nE\n' in text or text.strip().endswith('E'):
        return 'simai'
    return 'unknown'


def _time_beats(bar: int, tick: int, definition: int) -> float:
    return float(bar) * 4.0 + (float(tick) / float(definition)) * 4.0


def _tickstamp(bar: int, tick: int, definition: int) -> int:
    return int(bar) * int(definition) + int(tick)


def _get_bpm_time_unit(bpm: float, definition: int) -> float:
    # Note.cs: 60/bpm * 4/definition
    if bpm <= 0:
        return 0.0
    return (60.0 / float(bpm)) * (4.0 / float(definition))


def _normalize_bpm_changes(changes: List[Dict[str, Any]], definition: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in changes:
        if not isinstance(c, dict):
            continue
        bar = int(c.get('bar', 0))
        tick = int(c.get('tick', 0))
        bpm = float(c.get('bpm', 0.0))
        ts = _tickstamp(bar, tick, definition)
        out.append({'bar': bar, 'tick': tick, 'bpm': bpm, 'tickstamp': ts, 'bpm_unit': _get_bpm_time_unit(bpm, definition)})
    out.sort(key=lambda d: d['tickstamp'])
    return out


def _time_stamp_from_bpm_changes(change_table: List[Dict[str, Any]], overall_tick: int) -> Optional[float]:
    # Port of Note.GetTimeStamp(changeTable, overallTick)
    if overall_tick <= 0:
        return 0.0
    if not change_table:
        return None

    idx = 0
    for i, c in enumerate(change_table):
        if int(c.get('tickstamp', 0)) <= overall_tick:
            idx = i

    if idx == 0:
        return float(change_table[0].get('bpm_unit', 0.0)) * float(overall_tick)

    total = 0.0
    for i in range(1, idx + 1):
        prev = change_table[i - 1]
        cur = change_table[i]
        prev_unit = float(prev.get('bpm_unit', 0.0))
        total += (int(cur['tickstamp']) - int(prev['tickstamp'])) * prev_unit

    unit = float(change_table[idx].get('bpm_unit', 0.0))
    total += (overall_tick - int(change_table[idx]['tickstamp'])) * unit
    return total


def _attach_time_ms(ev: Dict[str, Any], change_table: List[Dict[str, Any]], definition: int) -> None:
    extra = ev.setdefault('extra', {})
    bar = int(extra.get('bar', 0))
    tick = int(extra.get('tick', 0))
    ts = _tickstamp(bar, tick, definition)
    extra['tickstamp'] = ts
    t = _time_stamp_from_bpm_changes(change_table, ts)
    if t is not None:
        ev['time_ms'] = int(round(t * 1000.0))


# ----------------------------
# MA2 parsing
# ----------------------------

_STD_BAR = 1
_STD_TICK = 2
_STD_KEY = 3
_STD_WAIT = 4
_STD_LAST = 5
_STD_ENDKEY = 6


def _ma2_definition(lines: List[str]) -> int:
    for ln in lines:
        if ln.startswith('RESOLUTION\t'):
            tail = ln.split('\t', 1)[1].strip()
            if tail.isdigit():
                return int(tail)
    return 384


def _ma2_bpm_changes(lines: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ln in lines:
        parts = ln.split('\t')
        if len(parts) >= 4 and parts[0] == 'BPM':
            out.append({'bar': _safe_int(parts[1]), 'tick': _safe_int(parts[2]), 'bpm': _safe_float(parts[3])})
    return out


def _ma2_note_events(lines: List[str], definition: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ln in lines:
        if '\t' not in ln:
            continue
        parts = ln.split('\t')
        typ = parts[0]

        # skip headers/stats
        if typ in {'VERSION', 'FES_MODE', 'RESOLUTION', 'CLK_DEF', 'COMPATIBLE_CODE'}:
            continue
        if typ.startswith('T_REC_') or typ.startswith('T_NUM_') or typ.startswith('T_JUDGE_') or typ.startswith('TTM_'):
            continue

        if len(parts) <= _STD_TICK:
            continue

        bar = _safe_int(parts[_STD_BAR])
        tick = _safe_int(parts[_STD_TICK])
        key = parts[_STD_KEY] if len(parts) > _STD_KEY else ''

        if typ == 'BPM' and len(parts) >= 4:
            bpm = _safe_float(parts[3])
            out.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': 'bpm_change',
                        'extra': {'raw_type': 'BPM', 'bar': bar, 'tick': tick, 'bpm': bpm, 'definition': definition, 'raw_parts': parts}})
            continue

        if typ == 'MET' and len(parts) >= 5:
            quaver = _safe_int(parts[_STD_KEY])
            wait = _safe_int(parts[_STD_WAIT])
            out.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': 'measure_change',
                        'extra': {'raw_type': 'MET', 'bar': bar, 'tick': tick, 'quaver': quaver, 'wait': wait, 'definition': definition, 'raw_parts': parts}})
            continue

        if typ in {'TAP', 'STR', 'XTP', 'XST', 'BRK', 'BST'}:
            kind = 'maimai_tap'
        elif typ == 'TTP':
            kind = 'maimai_touch'
        elif typ in {'HLD', 'XHO', 'THO'}:
            kind = 'maimai_hold'
        elif typ.startswith('S') or typ in {'SI_', 'SV_', 'SF_', 'SCL', 'SCR', 'SUL', 'SUR', 'SLL', 'SLR', 'SXL', 'SXR', 'SSL', 'SSR'}:
            kind = 'maimai_slide'
        else:
            kind = 'maimai_event'

        extra: Dict[str, Any] = {'raw_type': typ, 'bar': bar, 'tick': tick, 'key': key, 'definition': definition, 'raw_parts': parts}
        if kind == 'maimai_slide' and len(parts) > _STD_LAST:
            extra['wait_len_ticks'] = _safe_int(parts[_STD_WAIT])
            extra['last_len_ticks'] = _safe_int(parts[_STD_LAST])
            if len(parts) > _STD_ENDKEY:
                extra['end_key'] = parts[_STD_ENDKEY]
        if kind == 'maimai_hold' and len(parts) > _STD_WAIT:
            extra['last_len_ticks'] = _safe_int(parts[_STD_WAIT])

        out.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': kind, 'extra': extra})

    out.sort(key=lambda e: (float(e.get('time_beats', 0.0)), str(e.get('kind', ''))))
    return out


# ----------------------------
# Simai parsing + slide segmentation
# ----------------------------

_TOUCH_GROUP = set(list('ABCDEF'))
_ALLOWED_SLIDE_TYPE = {"qq", "q", "pp", "p", "v", "w", "<", ">", "^", "s", "z", "V", "-"}
_SLIDE_NOTATION_CHARS = set(list('-vw<>pqszV^'))


def _simai_strip_ws(text: str) -> str:
    return ''.join(ch for ch in text if not ch.isspace())


def _simai_tokens_from_text(text: str) -> List[str]:
    return _simai_strip_ws(text).split(',')


def _simai_parse_meta_and_charts(text: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    info: Dict[str, str] = {}
    charts: Dict[str, List[str]] = {}
    for item in text.split('&'):
        if not item:
            continue
        if 'title=' in item:
            info['Name'] = item.replace('title=', '').replace('[SD]', '').replace('[DX]', '')
        elif 'wholebpm=' in item:
            info['BPM'] = item.replace('wholebpm=', '')
        elif 'artist=' in item:
            info['Composer'] = item.replace('artist=', '')
        elif 'shortid=' in item:
            info['Music ID'] = item.replace('shortid=', '')
        elif 'inote_' in item and '=' in item:
            k, v = item.split('=', 1)
            charts[k.replace('inote_', '')] = _simai_tokens_from_text(v)
    return info, charts


def _simai_each_group_of_token(token: str) -> List[str]:
    # Conservative splitter: '/', parentheses blocks, and numeric runs.
    buf = ''
    extracted: List[str] = []
    for c in token:
        if c == '/':
            extracted.append(buf)
            buf = ''
        elif c in '({':
            if buf:
                extracted.append(buf)
            buf = c
        elif c in ')}':
            buf += c
            extracted.append(buf)
            buf = ''
        elif c == '`':
            buf += '%'
            extracted.append(buf)
            buf = ''
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
    # remove existing bracketed duration
    out = []
    ignoring = False
    for ch in old_value:
        if ch == '[':
            ignoring = True
        if not ignoring:
            out.append(ch)
        if ignoring and ch == ']':
            ignoring = False
    base = ''.join(out)
    if 'CN' in base:
        left, right = base.split('CN', 1)
        return f"{left}{new_duration}CN{right}"
    return base + new_duration


def _simai_extract_connecting_slides(token: str) -> List[str]:
    # Port of ExtractConnectingSlides: segment split + CN injection + single-duration redistribution.
    origin = token
    result: List[str] = []
    slide_candidate = ''
    first_segment_extracted = False

    while token:
        if _simai_is_slide_notation(token[0]):
            notation = token[:2] if token[:2] in ('pp', 'qq') else token[0]
            if notation not in _ALLOWED_SLIDE_TYPE:
                raise ValueError(f"Unexpected slide type: {notation} in slide: {origin}")
            if slide_candidate == '' and first_segment_extracted:
                raise ValueError(f"Unexpected occurrence of slide notation: {notation} in slide: {origin}")
            if slide_candidate:
                result.append(slide_candidate)
            first_segment_extracted = True
            slide_candidate = ''
        elif token[0].isdigit():
            notation = token[0]
        elif token[0] == '[':
            end = token.find(']')
            if end == -1:
                raise ValueError(f"Unclosed time notation: {token}")
            notation = token[:end + 1]
        else:
            raise ValueError(f"Cannot parse notation {token} in slide: {origin}")

        slide_candidate += notation
        token = token[len(notation):]

    if slide_candidate:
        result.append(slide_candidate)

    # CN injection
    start = 1 if result and _simai_is_slide_notation(result[0][0]) else 2
    if result and result[0].startswith('1_'):
        start = 2
    for i in range(len(result) - 1, start - 1, -1):
        prev = result[i - 1]
        if prev.endswith(']'):
            prev = prev[:prev.find('[')]
        last_key = int(prev[-1])
        result[i] = result[i] + 'CN' + str(last_key - 1)

    # duration redistribution
    if sum(1 for p in result if '[' in p) == 0:
        raise ValueError('Extracted slides do not contain any duration setting: ' + ', '.join(result))

    slide_parts = sum(1 for p in result if any(s in p for s in _ALLOWED_SLIDE_TYPE))
    duration_parts = sum(1 for p in result if '[' in p)

    if slide_parts >= 2 and duration_parts == 1:
        slide_duration_candidate = next(p for p in result if '[' in p)
        new_duration_candidate = '[' + slide_duration_candidate.split('[', 1)[1].split('CN')[0]
        actual_slide_part = sum(1 for p in result if '_' not in p)

        is_measure_duration = (':' in new_duration_candidate) and ('#' not in new_duration_candidate)

        if is_measure_duration:
            body = new_duration_candidate.strip('[]')
            q_s, m_s = body.split(':', 1)
            quaver = int(q_s) * actual_slide_part
            multiple = int(m_s)
            new_duration_candidate = f"[{quaver}:{multiple}]"
            write_original_wait = False
            original_wait = 0.0
            avg_last = 0.0
        else:
            body = new_duration_candidate.strip('[]')
            if '##' in body:
                wait_s, last_s = body.split('##', 1)
                original_wait = float(wait_s)
                total_last = float(last_s)
            elif body.startswith('#'):
                original_wait = 0.0
                total_last = float(body[1:])
            else:
                original_wait = 0.0
                total_last = float(body) if body else 0.0
            avg_last = round(total_last / max(1, actual_slide_part), 4)
            new_duration_candidate = f"[0##{avg_last}]"
            write_original_wait = True

        wrote_original = not write_original_wait
        start_i = 1 if '_' in result[0] else 0
        for i in range(start_i, len(result)):
            if write_original_wait and not wrote_original:
                dur = f"[{round(original_wait, 4)}##{avg_last}]"
                result[i] = _simai_replace_duration(result[i], dur)
                wrote_original = True
            else:
                result[i] = _simai_replace_duration(result[i], new_duration_candidate)

    return result


def _simai_get_time_candidates(bpm: float, input_str: str, definition: int, is_slide: bool) -> Tuple[float, float]:
    # Ported duration logic.
    if not (input_str.startswith('[') and input_str.endswith(']')):
        raise ValueError('duration must be bracketed')
    dur = input_str[1:-1]

    is_measure_duration = (':' in dur) and ('#' not in dur)
    is_slide_timed = ('##' in dur) and (':' not in dur)
    is_hold_timed = (not is_slide_timed) and ('#' in dur) and (':' not in dur)
    is_slide_bpm_measure = ('##' in dur) and ('#' in dur) and (':' in dur)
    is_hold_bpm_measure = (not is_slide_bpm_measure) and ('#' in dur) and (':' in dur)

    wait = 0.0
    last = 0.0

    if is_measure_duration:
        q_s, beat_s = dur.split(':', 1)
        q = float(q_s)
        beat = float(beat_s)
        last = _get_bpm_time_unit(bpm, definition) * (definition / q) * beat
        wait = 0.0
    elif is_slide_timed:
        a, b = dur.split('##', 1)
        wait = float(a)
        last = float(b)
    elif is_hold_timed:
        left, right = dur.split('#', 1)
        is_slide_reassigned = len(left) != 0
        if is_slide_reassigned:
            bpm_candidate = float(left)
            wait = _get_bpm_time_unit(bpm_candidate, definition) * (definition / 4)
            last = float(right)
        else:
            wait = 0.0
            last = float(right)
    elif is_slide_bpm_measure:
        wait_s, rest = dur.split('##', 1)
        bpm_s, qb = rest.split('#', 1)
        q_s, beat_s = qb.split(':', 1)
        bpm_candidate = float(bpm_s)
        q = float(q_s)
        beat = float(beat_s)
        wait = float(wait_s)
        last = _get_bpm_time_unit(bpm_candidate, definition) * (definition / q) * beat
    elif is_hold_bpm_measure:
        bpm_s, qb = dur.split('#', 1)
        q_s, beat_s = qb.split(':', 1)
        bpm_candidate = float(bpm_s)
        q = float(q_s)
        beat = float(beat_s)
        wait = 0.0
        last = _get_bpm_time_unit(bpm_candidate, definition) * (definition / q) * beat
    else:
        raise ValueError(f'duration pattern not matched: {dur}')

    # Slide wait override
    if is_slide and (is_measure_duration or is_hold_timed):
        wait = _get_bpm_time_unit(bpm, definition) * (definition / 4)
    elif is_slide and is_hold_bpm_measure:
        bpm_candidate = float(dur.split('#', 1)[0])
        wait = _get_bpm_time_unit(bpm_candidate, definition) * (definition / 4)

    return wait, last


def _parse_simai_tokens(tokens: List[str], definition: int = 384) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    time_in_bar = Fraction(0, 1)
    time_step = Fraction(1, 4)
    current_bpm = 0.0

    bpm_changes: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

    diag: Dict[str, Any] = {'tokens_total': len(tokens), 'definition': definition}

    for tok in tokens:
        each_notes = _simai_each_group_of_token(tok)
        t = float(time_in_bar)
        bar = int(t // 1)
        tick = int(round((t - bar) * definition))

        for each_note in each_notes:
            if each_note == '' or each_note == 'E':
                continue

            # BPM
            if each_note.startswith('(') and each_note.endswith(')'):
                bpm_val = _safe_float(each_note[1:-1], 0.0)
                current_bpm = bpm_val
                bpm_changes.append({'bar': bar, 'tick': tick, 'bpm': bpm_val})
                events.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': 'bpm_change',
                               'extra': {'raw_token': each_note, 'bar': bar, 'tick': tick, 'bpm': bpm_val, 'definition': definition}})
                continue

            # Measure
            if each_note.startswith('{') and each_note.endswith('}'):
                q = each_note[1:-1]
                quaver = _safe_int(q.replace('#', ''), 0)
                events.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': 'measure_change',
                               'extra': {'raw_token': each_note, 'bar': bar, 'tick': tick, 'quaver': q, 'definition': definition}})
                if not q.startswith('#') and quaver > 0:
                    time_step = Fraction(1, quaver)
                continue

            contains_grace = '%' in each_note
            token = each_note.replace('%', '') if contains_grace else each_note

            is_slide = ('[' in token and ']' in token) and _simai_contains_slide_notation(token)
            is_hold = ('h' in token) and ('[' in token and ']' in token) and not is_slide
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
                        'raw_token': seg,
                        'bar': int(seg_bar),
                        'tick': int(seg_tick),
                        'definition': definition,
                        'grace': contains_grace,
                        'segment_index': seg_i,
                        'segments_total': len(segments),
                    }
                    if seg_error and seg_i == 0:
                        extra['segmentation_error'] = seg_error

                    if '[' in seg and ']' in seg:
                        dur = '[' + seg.split('[', 1)[1].split(']', 1)[0] + ']'
                        try:
                            wait_sec, last_sec = _simai_get_time_candidates(current_bpm, dur, definition, is_slide=True)
                        except Exception as e:
                            wait_sec, last_sec = 0.0, 0.0
                            extra['duration_parse_error'] = str(e)
                        extra['duration'] = dur
                        extra['wait_time_sec'] = float(wait_sec)
                        extra['last_time_sec'] = float(last_sec)
                        bpm_unit = _get_bpm_time_unit(current_bpm, definition)
                        if bpm_unit > 0:
                            extra['wait_len_ticks'] = int(round(wait_sec / bpm_unit))
                            extra['last_len_ticks'] = int(round(last_sec / bpm_unit))
                            offset_ticks += int(extra.get('wait_len_ticks', 0)) + int(extra.get('last_len_ticks', 0))

                    events.append({'time_beats': _time_beats(int(seg_bar), int(seg_tick), definition), 'lane': 0, 'kind': 'maimai_slide', 'extra': extra})

                continue

            if is_hold:
                kind = 'maimai_hold'
            elif is_touch:
                kind = 'maimai_touch'
            elif token and token[0].isdigit():
                kind = 'maimai_tap'
            else:
                kind = 'maimai_event'

            extra: Dict[str, Any] = {'raw_token': token, 'bar': bar, 'tick': tick, 'definition': definition, 'grace': contains_grace}

            if kind == 'maimai_hold' and '[' in token and ']' in token:
                dur = '[' + token.split('[', 1)[1].split(']', 1)[0] + ']'
                try:
                    wait_sec, last_sec = _simai_get_time_candidates(current_bpm, dur, definition, is_slide=False)
                except Exception as e:
                    wait_sec, last_sec = 0.0, 0.0
                    extra['duration_parse_error'] = str(e)
                extra['duration'] = dur
                extra['wait_time_sec'] = float(wait_sec)
                extra['last_time_sec'] = float(last_sec)
                bpm_unit = _get_bpm_time_unit(current_bpm, definition)
                if bpm_unit > 0:
                    extra['wait_len_ticks'] = int(round(wait_sec / bpm_unit))
                    extra['last_len_ticks'] = int(round(last_sec / bpm_unit))

            events.append({'time_beats': _time_beats(bar, tick, definition), 'lane': 0, 'kind': kind, 'extra': extra})

        time_in_bar += time_step

    events.sort(key=lambda e: (float(e.get('time_beats', 0.0)), str(e.get('kind', ''))))
    return events, bpm_changes, diag


# ----------------------------
# Canonical payload builder
# ----------------------------


def build_canonical_payload_maimai(source_ref: str, *, preferred_simai_diff: Optional[str] = None) -> Dict[str, Any]:
    path = Path(source_ref)
    text = path.read_text(encoding='utf-8', errors='ignore')
    fmt = _detect_format(text)

    song_id, diff = _infer_song_id_and_difficulty(path)

    definition = 384
    bpm_changes_raw: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    diag: Dict[str, Any] = {}

    if fmt == 'ma2':
        lines = text.splitlines()
        definition = _ma2_definition(lines)
        bpm_changes_raw = _ma2_bpm_changes(lines)
        events = _ma2_note_events(lines, definition)
        diag['ma2_lines'] = len(lines)

    elif fmt == 'simai':
        info, charts = _simai_parse_meta_and_charts(text)
        chosen_key: Optional[str] = None
        if preferred_simai_diff and preferred_simai_diff in charts:
            chosen_key = preferred_simai_diff
        elif charts:
            chosen_key = sorted(charts.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]

        simai_tokens = charts.get(chosen_key) if chosen_key else _simai_tokens_from_text(text)
        events, bpm_changes_raw, diag2 = _parse_simai_tokens(simai_tokens or [], definition=384)
        diag.update({'simai_meta': info, 'simai_chart_candidates': sorted(list(charts.keys())), 'simai_selected': chosen_key, **diag2})

        if info.get('Music ID'):
            song_id = info.get('Music ID')
        elif info.get('Name'):
            song_id = info.get('Name')

    bpm_table = _normalize_bpm_changes(bpm_changes_raw, definition)

    for ev in events:
        _attach_time_ms(ev, bpm_table, definition)
        extra = ev.get('extra') or {}
        if isinstance(extra, dict) and ev.get('kind') in {'maimai_hold', 'maimai_slide'}:
            if 'time_ms' in ev and isinstance(ev['time_ms'], int):
                wt = float(extra.get('wait_time_sec', 0.0))
                lt = float(extra.get('last_time_sec', 0.0))
                if wt or lt:
                    ev['end_time_ms'] = int(round(ev['time_ms'] + (wt + lt) * 1000.0))

    bpm_base = bpm_table[0]['bpm'] if bpm_table else 0.0

    max_time_beats = 0.0
    max_time_ms: Optional[int] = None
    for ev in events:
        tb = ev.get('time_beats')
        if isinstance(tb, (int, float)):
            max_time_beats = max(max_time_beats, float(tb))
        tms = ev.get('end_time_ms') if isinstance(ev.get('end_time_ms'), int) else ev.get('time_ms')
        if isinstance(tms, int):
            max_time_ms = tms if max_time_ms is None else max(max_time_ms, tms)

    chart_meta: Dict[str, Any] = {
        'definition': int(definition),
        'bpm': float(bpm_base) if bpm_base else 0.0,
        'max_time_beats': float(max_time_beats),
    }
    if max_time_ms is not None:
        chart_meta['max_time_ms'] = int(max_time_ms)
    if bpm_table:
        chart_meta['bpm_changes'] = [
            {
                'time_beats': _time_beats(int(b['bar']), int(b['tick']), definition),
                'bpm': float(b['bpm']),
                'time_ms': int(round((_time_stamp_from_bpm_changes(bpm_table, int(b['tickstamp'])) or 0.0) * 1000.0)),
            }
            for b in bpm_table
        ]

    adapter_metadata: Dict[str, Any] = {
        'adapter_id': _ADAPTER_ID,
        'adapter_version': _ADAPTER_VERSION,
        'source_format': fmt,
        'source_path': str(path),
        'notes': 'events_v3 with simai slide segmentation + bpm-aware time_ms',
    }

    parse_level = 'events_v3' if any(isinstance(ev, dict) and str(ev.get('kind', '')).startswith('maimai_') for ev in events) else 'tokens_only'

    diagnostics: Dict[str, Any] = {
        'parse_level': parse_level,
        'note_events_total': len(events),
        'bpm_change_count': len(bpm_table),
        **diag,
    }

    internal_metadata = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes='structural-only; tips disabled until taxonomy mapping exists',
        extra={'parse_level': parse_level},
    )

    payload: Dict[str, Any] = {
        'game_id': 'maimai',
        'chart_id': str(path),
        'difficulty': diff,
        'note_events': events,
        'chart_meta': chart_meta,
        'adapter_metadata': adapter_metadata,
        'diagnostics': diagnostics,
        'internal_metadata': internal_metadata,
    }

    # Ensure additive attachment (in case callers pre-populate keys)
    attach_if_missing(payload, 'diagnostics', diagnostics)
    attach_if_missing(payload, 'internal_metadata', internal_metadata)

    return payload


class MaimaiAdapter(BaseAdapter):
    game_id = 'maimai'

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {'.ma2', '.simai', '.txt'}

    def load(self, path: Path) -> MaimaiIngestRaw:
        payload = build_canonical_payload_maimai(str(path))
        chart_meta = payload.get('chart_meta') or {}
        diag = payload.get('diagnostics') or {}
        song_id, diff = _infer_song_id_and_difficulty(path)

        events = payload.get('note_events') or []
        bpm_changes = chart_meta.get('bpm_changes') or []
        definition = int(chart_meta.get('definition') or 384)

        return MaimaiIngestRaw(
            chart_path=path,
            song_id=song_id,
            difficulty=payload.get('difficulty') or diff,
            source_format=payload.get('adapter_metadata', {}).get('source_format') or 'unknown',
            definition=definition,
            bpm_changes=list(bpm_changes) if isinstance(bpm_changes, list) else [],
            note_events=list(events) if isinstance(events, list) else [],
            diagnostics=dict(diag) if isinstance(diag, dict) else {},
        )

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_maimai(source_ref)

    def to_canonical_row(self, raw: MaimaiIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        diag = payload.get('diagnostics') or {}
        events = payload.get('note_events') or []

        note_total = 0
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict) and str(ev.get('kind', '')).startswith('maimai_'):
                    note_total += 1

        song_id = raw.song_id
        if isinstance(diag, dict):
            meta = diag.get('simai_meta')
            if isinstance(meta, dict):
                if meta.get('Music ID'):
                    song_id = str(meta.get('Music ID'))
                elif meta.get('Name'):
                    song_id = str(meta.get('Name'))

        chart_meta = payload.get('chart_meta') or {}
        return {
            'game': self.game_id,
            'song_id': song_id,
            'difficulty_label': payload.get('difficulty') or raw.difficulty or 'UNKNOWN',
            'note_total_chart': int(note_total),
            'duration_ms': chart_meta.get('max_time_ms'),
            'bpm': chart_meta.get('bpm'),
            'chart_path': str(raw.chart_path),
            'source_format': payload.get('adapter_metadata', {}).get('source_format'),
            'max_time_beats': chart_meta.get('max_time_beats'),
        }

    def capabilities(self) -> dict:
        return {
            'note_model': 'touch_radial',
            'supports_sections': False,
            'supports_variable_bpm': True,
            'supports_bpm_changes': True,
            'supports_width': False,
            'emits_canonical_payload': True,
            'source_format': 'ma2/simai',
            'parse_level': 'events_v3',
            'time_unit': 'beats+ms',
        }


__all__ = ['MaimaiAdapter', 'MaimaiIngestRaw', 'build_canonical_payload_maimai']
