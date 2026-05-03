#!/usr/bin/env python3
"""taxonomy_qa_summary_helper.py

QA summary helper for PatternTagsTaxonomy.

Purpose:
- Provide a lightweight, deterministic summary of taxonomy health for CI/QA dashboards.
- Report counts for categorized vs known-but-uncategorized vs unknown tags.
- Optional strict mode for CI gating.

Strict mode:
- When strict_mode=True, the helper computes `strict_ok` plus `strict_errors`/`strict_warnings`
  based on simple, deterministic thresholds.
- The helper never raises by itself; enforcement is handled by optional wrappers.

Scope & constraints:
- Pure utility (no network, no registry lookups).
- Reads local artifacts only when explicitly invoked (via PatternTagsTaxonomy).
- Does NOT mutate any canonical payloads.

Primary dependency:
- pattern_tags_taxonomy.PatternTagsTaxonomy (MVP+).

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .pattern_tags_taxonomy import PatternTagsTaxonomy


@dataclass(frozen=True)
class TaxonomyQASummary:
    """Structured QA summary output."""

    export_path: str
    guides_xlsx_path: str
    categorized_tag_count: int
    uncategorized_tag_count: int
    total_known_tag_count: int

    detected_tag_count: int
    detected_known_count: int
    detected_unknown_count: int

    unknown_tags: List[str]
    uncategorized_tags_sample: List[str]

    strict_mode: bool
    strict_ok: bool
    strict_errors: List[str]
    strict_warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'export_path': self.export_path,
            'guides_xlsx_path': self.guides_xlsx_path,
            'categorized_tag_count': self.categorized_tag_count,
            'uncategorized_tag_count': self.uncategorized_tag_count,
            'total_known_tag_count': self.total_known_tag_count,
            'detected_tag_count': self.detected_tag_count,
            'detected_known_count': self.detected_known_count,
            'detected_unknown_count': self.detected_unknown_count,
            'unknown_tags': list(self.unknown_tags),
            'uncategorized_tags_sample': list(self.uncategorized_tags_sample),
            'strict_mode': self.strict_mode,
            'strict_ok': self.strict_ok,
            'strict_errors': list(self.strict_errors),
            'strict_warnings': list(self.strict_warnings),
        }


def build_taxonomy_qa_summary(
    *,
    detected_tags: Optional[Iterable[Any]] = None,
    export_path: Optional[str] = None,
    guides_xlsx_path: Optional[str] = None,
    max_unknown_list: int = 50,
    max_uncategorized_sample: int = 50,
    # --- strict mode knobs ---
    strict_mode: bool = False,
    max_detected_unknown: int = 0,
    max_uncategorized_total: Optional[int] = None,
    require_export_present: bool = True,
    require_guides_present: bool = False,
) -> Dict[str, Any]:
    """Build a QA summary dict for taxonomy and an optional detected tag list.

    Definitions:
    - categorized tags: tags present in pattern_signals_export_v2.json categories
    - uncategorized tags: known tags harvested from guides XLSX but absent from export categories
    - unknown tags: tags in neither categorized nor uncategorized

    Strict mode policy (simple, deterministic):
    - If require_export_present and export JSON appears missing/empty -> fail
    - If require_guides_present and guides XLSX appears missing/unreadable -> fail
    - If detected_unknown_count > max_detected_unknown -> fail
    - If max_uncategorized_total is not None and uncategorized_tag_count > max_uncategorized_total -> fail

    Returns a plain dict for easy JSON serialization.
    """

    export_path = export_path or PatternTagsTaxonomy.DEFAULT_EXPORT_PATH
    guides_xlsx_path = guides_xlsx_path or PatternTagsTaxonomy.DEFAULT_GUIDES_XLSX_PATH

    all_known = PatternTagsTaxonomy.all_tags(export_path=export_path, guides_xlsx_path=guides_xlsx_path)
    uncategorized = PatternTagsTaxonomy.uncategorized_tags(export_path=export_path, guides_xlsx_path=guides_xlsx_path)
    categorized_count = max(0, len(all_known) - len(uncategorized))

    detected_list = list(detected_tags or [])
    normalized_detected = PatternTagsTaxonomy.normalize_tags(detected_list)

    unknown = PatternTagsTaxonomy.unknown_tags(
        normalized_detected,
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
    )

    detected_known_count = 0
    for t in normalized_detected:
        if PatternTagsTaxonomy.is_known(t, export_path=export_path, guides_xlsx_path=guides_xlsx_path):
            detected_known_count += 1

    strict_errors: List[str] = []
    strict_warnings: List[str] = []

    if strict_mode:
        if require_export_present and categorized_count == 0:
            strict_errors.append(f"taxonomy export appears missing or empty: {export_path}")

        if require_guides_present and len(uncategorized) == 0:
            strict_errors.append(f"taxonomy guides appear missing or unreadable: {guides_xlsx_path}")

        if len(unknown) > int(max_detected_unknown):
            strict_errors.append(
                f"detected_unknown_count {len(unknown)} exceeds max_detected_unknown {int(max_detected_unknown)}"
            )

        if max_uncategorized_total is not None and len(uncategorized) > int(max_uncategorized_total):
            strict_errors.append(
                f"uncategorized_tag_count {len(uncategorized)} exceeds max_uncategorized_total {int(max_uncategorized_total)}"
            )

        if len(uncategorized) > 0:
            strict_warnings.append(
                "there are known-but-uncategorized tags; consider categorizing them in pattern_signals_export_v2.json"
            )

    strict_ok = (len(strict_errors) == 0) if strict_mode else True

    summary = TaxonomyQASummary(
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
        categorized_tag_count=categorized_count,
        uncategorized_tag_count=len(uncategorized),
        total_known_tag_count=len(all_known),
        detected_tag_count=len(normalized_detected),
        detected_known_count=detected_known_count,
        detected_unknown_count=len(unknown),
        unknown_tags=unknown[: max(0, int(max_unknown_list))],
        uncategorized_tags_sample=sorted(list(uncategorized))[: max(0, int(max_uncategorized_sample))],
        strict_mode=bool(strict_mode),
        strict_ok=bool(strict_ok),
        strict_errors=strict_errors,
        strict_warnings=strict_warnings,
    )

    return summary.to_dict()


# ----------------------------
# Strict mode wrappers
# ----------------------------

def assert_taxonomy_strict_ok(summary: Dict[str, Any], *, context: Optional[str] = None) -> None:
    """Assertion-style wrapper for strict mode.

    Intended for tests/CI:
    - Expects `summary` produced by build_taxonomy_qa_summary(strict_mode=True).
    - Raises AssertionError if strict_ok is False.
    """

    if not isinstance(summary, dict):
        raise AssertionError('taxonomy QA summary must be a dict')

    if not bool(summary.get('strict_mode')):
        raise AssertionError('assert_taxonomy_strict_ok requires summary.strict_mode == True')

    if not bool(summary.get('strict_ok')):
        errors = summary.get('strict_errors') or []
        prefix = f"[{context}] " if context else ""
        msg = prefix + 'taxonomy strict mode failed: ' + '; '.join([str(e) for e in errors])
        raise AssertionError(msg)


def enforce_taxonomy_strict_mode(
    *,
    detected_tags: Optional[Iterable[Any]] = None,
    export_path: Optional[str] = None,
    guides_xlsx_path: Optional[str] = None,
    max_detected_unknown: int = 0,
    max_uncategorized_total: Optional[int] = None,
    require_export_present: bool = True,
    require_guides_present: bool = False,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience wrapper: build strict summary and raise AssertionError on failure."""

    summary = build_taxonomy_qa_summary(
        detected_tags=detected_tags,
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
        strict_mode=True,
        max_detected_unknown=max_detected_unknown,
        max_uncategorized_total=max_uncategorized_total,
        require_export_present=require_export_present,
        require_guides_present=require_guides_present,
    )
    assert_taxonomy_strict_ok(summary, context=context)
    return summary


def check_taxonomy_strict_mode(
    *,
    detected_tags: Optional[Iterable[Any]] = None,
    export_path: Optional[str] = None,
    guides_xlsx_path: Optional[str] = None,
    max_detected_unknown: int = 0,
    max_uncategorized_total: Optional[int] = None,
    require_export_present: bool = True,
    require_guides_present: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """Non-assert strict-mode wrapper.

    Returns (ok, summary).
    """

    summary = build_taxonomy_qa_summary(
        detected_tags=detected_tags,
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
        strict_mode=True,
        max_detected_unknown=max_detected_unknown,
        max_uncategorized_total=max_uncategorized_total,
        require_export_present=require_export_present,
        require_guides_present=require_guides_present,
    )
    return bool(summary.get('strict_ok')), summary


# ----------------------------
# Strict report formatter (requested)
# ----------------------------

def format_taxonomy_strict_report(
    summary: Dict[str, Any],
    *,
    context: Optional[str] = None,
    include_warnings: bool = True,
    max_unknown: int = 10,
    max_uncategorized: int = 10,
) -> str:
    """Format a human-friendly report string for strict mode.

    PURE: does not raise.
    """

    if not isinstance(summary, dict):
        return (f"[{context}] " if context else "") + "taxonomy QA summary: <invalid summary>"

    prefix = f"[{context}] " if context else ""

    strict_mode = bool(summary.get('strict_mode'))
    strict_ok = bool(summary.get('strict_ok'))
    errors = summary.get('strict_errors') or []
    warnings = summary.get('strict_warnings') or []

    categorized = summary.get('categorized_tag_count')
    uncategorized = summary.get('uncategorized_tag_count')
    total_known = summary.get('total_known_tag_count')

    detected_total = summary.get('detected_tag_count')
    detected_known = summary.get('detected_known_count')
    detected_unknown = summary.get('detected_unknown_count')

    unknown_tags = summary.get('unknown_tags') or []
    uncategorized_sample = summary.get('uncategorized_tags_sample') or []

    def take(xs, n):
        try:
            n = int(n)
        except Exception:
            n = 10
        return list(xs)[: max(0, n)]

    status = "PASS" if (strict_mode and strict_ok) else ("FAIL" if strict_mode else "INFO")

    lines: List[str] = []
    lines.append(prefix + f"Taxonomy strict report: {status}")
    lines.append(prefix + f"Known tags: {total_known} (categorized={categorized}, uncategorized={uncategorized})")
    lines.append(prefix + f"Detected tags: {detected_total} (known={detected_known}, unknown={detected_unknown})")

    if strict_mode:
        if errors:
            lines.append(prefix + "Strict errors:")
            for e in errors:
                lines.append(prefix + f"- {e}")
        if include_warnings and warnings:
            lines.append(prefix + "Strict warnings:")
            for w in warnings:
                lines.append(prefix + f"- {w}")
    else:
        lines.append(prefix + "(strict_mode is OFF)")

    if detected_unknown and unknown_tags:
        lines.append(prefix + f"Unknown tag samples (up to {int(max_unknown)}): {', '.join(take(unknown_tags, max_unknown))}")

    if uncategorized and uncategorized_sample:
        lines.append(prefix + f"Uncategorized tag samples (up to {int(max_uncategorized)}): {', '.join(take(uncategorized_sample, max_uncategorized))}")

    return "
".join(lines)




def format_taxonomy_strict_report_one_line(
    summary: Dict[str, Any],
    *,
    context: Optional[str] = None,
    include_warnings: bool = False,
    max_unknown: int = 3,
    max_uncategorized: int = 3,
) -> str:
    """Format a condensed single-line strict mode report.

    Intended for CI annotations / brief logs.
    PURE: does not raise.

    Example:
      [taxonomy-ci] FAIL known=123(cat=80,uncat=43) detected=3(known=2,unk=1) unknown=[not_a_tag]
    """

    if not isinstance(summary, dict):
        return (f"[{context}] " if context else "") + "taxonomy strict: <invalid summary>"

    prefix = f"[{context}] " if context else ""

    strict_mode = bool(summary.get('strict_mode'))
    strict_ok = bool(summary.get('strict_ok'))
    categorized = summary.get('categorized_tag_count')
    uncategorized = summary.get('uncategorized_tag_count')
    total_known = summary.get('total_known_tag_count')

    detected_total = summary.get('detected_tag_count')
    detected_known = summary.get('detected_known_count')
    detected_unknown = summary.get('detected_unknown_count')

    unknown_tags = summary.get('unknown_tags') or []
    uncategorized_sample = summary.get('uncategorized_tags_sample') or []

    def take(xs, n):
        try:
            n = int(n)
        except Exception:
            n = 3
        return list(xs)[: max(0, n)]

    status = "PASS" if (strict_mode and strict_ok) else ("FAIL" if strict_mode else "INFO")

    parts = [
        prefix + status,
        f"known={total_known}(cat={categorized},uncat={uncategorized})",
        f"detected={detected_total}(known={detected_known},unk={detected_unknown})",
    ]

    if detected_unknown and unknown_tags:
        parts.append(f"unknown=[{', '.join(take(unknown_tags, max_unknown))}]")

    if uncategorized and uncategorized_sample:
        parts.append(f"uncat_sample=[{', '.join(take(uncategorized_sample, max_uncategorized))}]")

    if include_warnings and summary.get('strict_warnings'):
        ws = summary.get('strict_warnings') or []
        parts.append(f"warnings={len(ws)}")

    if strict_mode and not strict_ok and summary.get('strict_errors'):
        es = summary.get('strict_errors') or []
        # keep it short: include the first error only
        parts.append(f"error={str(es[0])}")

    return ' '.join([p for p in parts if p])

__all__ = [
    'TaxonomyQASummary',
    'build_taxonomy_qa_summary',
    'assert_taxonomy_strict_ok',
    'enforce_taxonomy_strict_mode',
    'check_taxonomy_strict_mode',
    'format_taxonomy_strict_report',
    'format_taxonomy_strict_report_one_line',
]
