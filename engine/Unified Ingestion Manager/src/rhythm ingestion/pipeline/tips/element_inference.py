from __future__ import annotations
"""element_inference.py

Stage 4.2–4.3 wiring utility: Tag → element candidates.

Grounded in the Stage 4.2/4.3 semantics:
- Stage 4.2: Tag -> element candidates via tips_training_mapping.json (or per-game mapping)
- Stage 4.3: Emit inferred candidates with matched_tags + training_items

This module is an additive, testable wiring layer used in Phase 3+.
It MUST NOT change any completed Phase 1/2 logic; it only standardizes:
- loading the mapping artifact
- tag normalization + parity reporting (unknown / uncategorized)
- candidate construction

Per-game mapping support:
- If a game_id is available, we first try a per-game mapping file:
    tips_training_mapping_<game_id>.json
  where <game_id> is lowercased and stripped.
- If not found (or game_id missing), we fall back to DEFAULT_TRAINING_MAPPING_PATH.
- Callers can override by passing mapping_path explicitly.

Mapping search paths support (NEW):
- Callers may provide mapping_search_paths: a list of directories to search.
- Resolution is deterministic and checks in this order:
    1) explicit mapping_path (if it exists as given)
    2) explicit mapping_path searched under mapping_search_paths (if provided)
    3) per-game mapping under mapping_search_paths
    4) default mapping under mapping_search_paths
    5) fallback to DEFAULT_TRAINING_MAPPING_PATH
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union
import json
import re

# Prefer local taxonomy module; keep a fallback import for older layouts.
try:
    from .pattern_tags_taxonomy import PatternTagsTaxonomy  # type: ignore
except Exception:  # pragma: no cover
    from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import PatternTagsTaxonomy  # type: ignore


DEFAULT_TRAINING_MAPPING_PATH = "tips_training_mapping.json"
PER_GAME_MAPPING_TEMPLATE = "tips_training_mapping_{game_id}.json"


@dataclass(frozen=True)
class ElementCandidate:
    """Lightweight element candidate container."""

    element_name: str
    matched_tags: Tuple[str, ...] = ()
    training_items: Tuple[str, ...] = ()
    tag_hit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_name": self.element_name,
            "matched_tags": list(self.matched_tags),
            "training_items": list(self.training_items),
            "tag_hit_count": int(self.tag_hit_count),
        }


def _normalize_game_id(game_id: Any) -> str:
    if game_id is None:
        return ""
    try:
        s = str(game_id)
    except Exception:
        return ""
    return s.strip().lower()


def _normalize_search_paths(
    paths: Optional[Sequence[Union[str, Path]]],
) -> List[Path]:
    """Normalize search paths into unique Path objects (deterministic order)."""

    if not paths:
        return [Path(".")]

    out: List[Path] = []
    seen: Set[str] = set()

    def _add_path(cand: Path) -> None:
        key = str(cand)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(cand)

    _GLOB_CHARS = ("*", "?", "[")
    _MAX_GLOB_MATCHES = 50

    def _looks_absolute(s: str) -> bool:
        if s.startswith("/") or s.startswith("~"):
            return True
        return bool(re.match(r"^[A-Za-z]:", s))

    def _glob_allowed(s: str) -> bool:
        if "**" in s:
            return False
        if ".." in s.replace("\\", "/").split("/"):
            return False
        if _looks_absolute(s):
            return False
        if "[" in s or "]" in s:
            return False
        if len(s) > 160:
            return False
        return True

    for item in paths:
        if item is None:
            continue

        if isinstance(item, Path):
            _add_path(item)
            continue

        try:
            s = str(item).strip()
        except Exception:
            continue
        if not s:
            continue

        has_glob = any(ch in s for ch in _GLOB_CHARS)

        if has_glob and _glob_allowed(s):
            try:
                matches = sorted(Path(".").glob(s))
            except Exception:
                matches = []
            count = 0
            for m in matches:
                if count >= _MAX_GLOB_MATCHES:
                    break
                try:
                    if m.is_dir():
                        _add_path(m)
                        count += 1
                except Exception:
                    continue
            continue

        _add_path(Path(s))

    return out or [Path(".")]


def _iter_candidate_locations(
    *,
    filename: str,
    search_paths: Sequence[Path],
) -> Iterable[Path]:
    """Yield candidate paths by joining filename to each search path."""
    for base in search_paths:
        yield base / filename


def resolve_training_mapping_path(
    *,
    game_id: Optional[str] = None,
    mapping_path: Optional[str] = None,
    mapping_search_paths: Optional[Sequence[str]] = None,
    default_path: str = DEFAULT_TRAINING_MAPPING_PATH,
    template: str = PER_GAME_MAPPING_TEMPLATE,
) -> str:
    """Resolve which mapping path to use."""

    if mapping_path:
        p = Path(mapping_path)
        if p.exists():
            return str(p)

    search_paths = _normalize_search_paths(mapping_search_paths)

    if mapping_path:
        name = str(mapping_path).strip()
        if name:
            for cand in _iter_candidate_locations(filename=name, search_paths=search_paths):
                if cand.exists():
                    return str(cand)

    gid = _normalize_game_id(game_id)

    if gid:
        per_game_name = template.format(game_id=gid)
        for cand in _iter_candidate_locations(filename=per_game_name, search_paths=search_paths):
            if cand.exists():
                return str(cand)

    for cand in _iter_candidate_locations(filename=default_path, search_paths=search_paths):
        if cand.exists():
            return str(cand)

    return default_path

@lru_cache(maxsize=64)
def load_tips_training_mapping(
    path: str = DEFAULT_TRAINING_MAPPING_PATH,
) -> Dict[str, Dict[str, Any]]:
    """Load a tips training mapping JSON file.

    Expected shape (best-effort):
      {
        "<element_name>": {
          "tags": ["tag1", "tag2", ...],
          "training_items": ["item1", ...],
          ...
        },
        ...
      }

    Returns {} if the file is missing or invalid.
    """

    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    # Normalize mapping tags once so downstream intersections are deterministic.
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue

        tags = v.get("tags")
        if isinstance(tags, list):
            norm_tags = [PatternTagsTaxonomy.normalize_tag(t) for t in tags if t is not None]
            norm_tags = [t for t in norm_tags if t]
        else:
            norm_tags = []

        training_items = v.get("training_items")
        if isinstance(training_items, list):
            ti = [str(x).strip() for x in training_items if x is not None]
            ti = [x for x in ti if x]
        else:
            ti = []

        out[k] = {**v, "tags": norm_tags, "training_items": ti}

    return out


def infer_element_candidates(
    detected_tags: Sequence[str],
    *,
    mapping: Optional[Dict[str, Dict[str, Any]]] = None,
    min_tag_hits: int = 1,
    include_zero_hit: bool = False,
) -> List[Dict[str, Any]]:
    """Infer element candidates from detected tags (Stage 4.2–4.3)."""

    mapping = mapping or {}

    norm_detected = [
        PatternTagsTaxonomy.normalize_tag(t)
        for t in (detected_tags or [])
        if isinstance(t, str)
    ]
    norm_detected = [t for t in norm_detected if t]
    detected_set: Set[str] = set(norm_detected)

    out: List[Dict[str, Any]] = []

    for element_name, spec in mapping.items():
        if not isinstance(element_name, str) or not isinstance(spec, dict):
            continue

        element_tags = spec.get("tags")
        if isinstance(element_tags, list):
            et = [PatternTagsTaxonomy.normalize_tag(t) for t in element_tags]
            et = [t for t in et if t]
        else:
            et = []

        matched = sorted(list(detected_set.intersection(set(et))))
        hit_count = len(matched)

        if not include_zero_hit and hit_count < int(min_tag_hits):
            continue

        training_items = spec.get("training_items")
        if isinstance(training_items, list):
            ti = [str(x).strip() for x in training_items if x is not None]
            ti = [x for x in ti if x]
        else:
            ti = []

        cand = ElementCandidate(
            element_name=element_name,
            matched_tags=tuple(matched),
            training_items=tuple(ti),
            tag_hit_count=hit_count,
        )
        out.append(cand.to_dict())

    # Stable ordering: hit_count desc then element_name asc.
    out.sort(
        key=lambda d: (-int(d.get("tag_hit_count") or 0), str(d.get("element_name") or ""))
    )
    return out


def _normalize_and_report_tags(
    canonical_payload: Dict[str, Any],
    detected_tags: Sequence[str],
    *,
    diagnostics_key: str = "diagnostics",
    tag_parity_key: str = "tag_parity",
    export_path: Optional[str] = None,
    guides_xlsx_path: Optional[str] = None,
) -> List[str]:
    """Phase-3 additive helper.

    - Normalize detected tags using PatternTagsTaxonomy
    - Record unknown / uncategorized tags into canonical_payload diagnostics (non-blocking)
    - Return normalized tag list
    """

    export_path = export_path or PatternTagsTaxonomy.DEFAULT_EXPORT_PATH
    guides_xlsx_path = guides_xlsx_path or PatternTagsTaxonomy.DEFAULT_GUIDES_XLSX_PATH

    norm = PatternTagsTaxonomy.normalize_tags(detected_tags or [])

    unknown = PatternTagsTaxonomy.unknown_tags(
        norm,
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
    )

    try:
        uncat_set = PatternTagsTaxonomy.uncategorized_tags(
            export_path=export_path,
            guides_xlsx_path=guides_xlsx_path,
        )
    except Exception:
        uncat_set = set()
    uncat_hit = [t for t in norm if t in uncat_set]

    diag = canonical_payload.setdefault(diagnostics_key, {})
    if isinstance(diag, dict):
        diag[tag_parity_key] = {
            "detected_tag_count": len(list(detected_tags or [])),
            "normalized_tag_count": len(norm),
            "unknown_tags": list(unknown),
            "uncategorized_tags": list(dict.fromkeys(uncat_hit)),
        }

    return norm


def attach_candidates_to_payload(
    canonical_payload: Dict[str, Any],
    *,
    detected_tags_key: str = "detected_tags",
    output_key: str = "element_candidates",
    mapping_path: Optional[str] = None,
    mapping_search_paths: Optional[Sequence[str]] = None,
    game_id: Optional[str] = None,
    min_tag_hits: int = 1,
    export_path: Optional[str] = None,
    guides_xlsx_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Infer candidates and attach them into canonical_payload (additive)."""

    detected_tags = canonical_payload.get(detected_tags_key) or []
    if not isinstance(detected_tags, list):
        detected_tags = []

    norm_tags = _normalize_and_report_tags(
        canonical_payload,
        [t for t in detected_tags if isinstance(t, str)],
        export_path=export_path,
        guides_xlsx_path=guides_xlsx_path,
    )

    gid = game_id or canonical_payload.get("game_id")
    resolved_path = resolve_training_mapping_path(
        game_id=gid,
        mapping_path=mapping_path,
        mapping_search_paths=mapping_search_paths,
    )

    mapping = load_tips_training_mapping(resolved_path)
    candidates = infer_element_candidates(
        norm_tags,
        mapping=mapping,
        min_tag_hits=min_tag_hits,
        include_zero_hit=False,
    )

    canonical_payload[output_key] = candidates

    # Add provenance for QA/debug (additive)
    diag = canonical_payload.setdefault("diagnostics", {})
    if isinstance(diag, dict):
        ei = diag.setdefault("element_inference", {})
        if isinstance(ei, dict):
            ei.setdefault("mapping_path", resolved_path)
            if mapping_search_paths is not None:
                ei.setdefault("mapping_search_paths", list(mapping_search_paths))
            if gid is not None:
                ei.setdefault("game_id", str(gid))

    return canonical_payload


__all__ = [
    "ElementCandidate",
    "resolve_training_mapping_path",
    "load_tips_training_mapping",
    "infer_element_candidates",
    "attach_candidates_to_payload",
]