## umi/pipeline/pattern_tags_taxonomy.py

"""pattern_tags_taxonomy.py
Canonical pattern tag taxonomy for UMI (multi-game).

This version adds **known-but-uncategorized** tags sourced from an operator guide
("Tips Generation Guides.xlsx") in addition to the categorized allowlist from
"pattern_signals_export_v2.json".

Provided APIs (Phase-3-safe, pure):
- normalize_tag(tag) -> str
- category_of(tag) -> Optional[str]
- is_known(tag) -> bool  (categorized OR known-but-uncategorized)
- unknown_tags(tags) -> List[str]
- uncategorized_tags() -> Set[str]

Design constraints:
- Avoid import-time heavy IO: artifacts are loaded lazily + cached.
- Deterministic and safe for Stage 4.2 wiring utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import json
import re


@dataclass(frozen=True)
class TagDef:
    """Universal tag definition for UMI."""

    tag: str
    category: Optional[str] = None
    aliases: Tuple[str, ...] = ()


class PatternTagsTaxonomy:
    """Canonical pattern tag taxonomy for UMI."""

    DEFAULT_EXPORT_PATH = "pattern_signals_export_v2.json"
    DEFAULT_GUIDES_XLSX_PATH = "Tips Generation Guides.xlsx"

    _RE_MULTI_WS = re.compile(r"\s+")

    # ----------------------------
    # Normalization
    # ----------------------------

    @staticmethod
    def normalize_tag(tag: Any) -> str:
        if tag is None:
            return ""
        try:
            s = str(tag)
        except Exception:
            return ""
        s = s.strip()
        while s.startswith(","):
            s = s[1:].lstrip()
        s = PatternTagsTaxonomy._RE_MULTI_WS.sub(" ", s).strip()
        return s.lower()

    @staticmethod
    def _split_tag_cell(cell: Any) -> List[str]:
        if cell is None:
            return []
        try:
            s = str(cell)
        except Exception:
            return []
        parts = s.split(",")
        out: List[str] = []
        for p in parts:
            nt = PatternTagsTaxonomy.normalize_tag(p)
            if nt:
                out.append(nt)
        return out

    # ----------------------------
    # Loading / indexing
    # ----------------------------

    @staticmethod
    def _extract_groups(data: Dict[str, Any]) -> Dict[str, List[str]]:
        root = data.get("pattern_and_difficulty_signals")
        if not isinstance(root, dict):
            return {}
        out: Dict[str, List[str]] = {}
        for cat, tags in root.items():
            if not isinstance(cat, str) or not isinstance(tags, list):
                continue
            norm: List[str] = []
            for t in tags:
                nt = PatternTagsTaxonomy.normalize_tag(t)
                if nt:
                    norm.append(nt)
            out[cat] = norm
        return out

    @staticmethod
    @lru_cache(maxsize=8)
    def _load_export(path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return {}

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_known_uncategorized_from_guides(xlsx_path: str) -> Set[str]:
        p = Path(xlsx_path)
        if not p.exists():
            return set()
        try:
            import pandas as pd  # type: ignore
        except Exception:
            return set()
        try:
            sheets = pd.read_excel(p, sheet_name=None, engine="openpyxl")
        except Exception:
            return set()

        tags: Set[str] = set()

        def harvest_df(df) -> None:
            if df is None:
                return
            cols = {str(c).strip().lower(): c for c in df.columns}
            for key in ("tags", "lit of tags", "list of tags", "lit_of_tags"):
                if key in cols:
                    col = cols[key]
                    for v in df[col].tolist():
                        for t in PatternTagsTaxonomy._split_tag_cell(v):
                            tags.add(t)

        for df in sheets.values():
            harvest_df(df)

        # Fallback: scan all cells for tag-like strings
        try:
            for df in sheets.values():
                for v in df.values.flatten().tolist():
                    if v is None:
                        continue
                    s = str(v)
                    if len(s) > 64:
                        continue
                    if any(ch in s for ch in ("_", ".", "=>")):
                        for t in PatternTagsTaxonomy._split_tag_cell(s):
                            tags.add(t)
        except Exception:
            pass

        return tags

    @classmethod
    @lru_cache(maxsize=8)
    def _build_indexes(cls, export_path: str, guides_xlsx_path: str) -> Tuple[Dict[str, str], Dict[str, Set[str]], Set[str]]:
        data = cls._load_export(export_path)
        groups = cls._extract_groups(data)

        tag_to_cat: Dict[str, str] = {}
        cat_to_tags: Dict[str, Set[str]] = {}
        for cat, tags in groups.items():
            cat_to_tags.setdefault(cat, set())
            for t in tags:
                cat_to_tags[cat].add(t)
                if t not in tag_to_cat:
                    tag_to_cat[t] = cat

        known_uncat = cls._load_known_uncategorized_from_guides(guides_xlsx_path)
        known_uncat = {t for t in known_uncat if t and t not in tag_to_cat}
        return tag_to_cat, cat_to_tags, known_uncat

    # ----------------------------
    # Query API
    # ----------------------------

    @classmethod
    def all_tags(cls, export_path: str = None, guides_xlsx_path: str = None) -> Set[str]:
        export_path = export_path or cls.DEFAULT_EXPORT_PATH
        guides_xlsx_path = guides_xlsx_path or cls.DEFAULT_GUIDES_XLSX_PATH
        tag_to_cat, _, known_uncat = cls._build_indexes(export_path, guides_xlsx_path)
        return set(tag_to_cat.keys()) | set(known_uncat)

    @classmethod
    def uncategorized_tags(cls, export_path: str = None, guides_xlsx_path: str = None) -> Set[str]:
        export_path = export_path or cls.DEFAULT_EXPORT_PATH
        guides_xlsx_path = guides_xlsx_path or cls.DEFAULT_GUIDES_XLSX_PATH
        _, _, known_uncat = cls._build_indexes(export_path, guides_xlsx_path)
        return set(known_uncat)

    @classmethod
    def is_known(cls, tag: Any, export_path: str = None, guides_xlsx_path: str = None) -> bool:
        export_path = export_path or cls.DEFAULT_EXPORT_PATH
        guides_xlsx_path = guides_xlsx_path or cls.DEFAULT_GUIDES_XLSX_PATH
        nt = cls.normalize_tag(tag)
        if not nt:
            return False
        tag_to_cat, _, known_uncat = cls._build_indexes(export_path, guides_xlsx_path)
        return nt in tag_to_cat or nt in known_uncat

    @classmethod
    def category_of(cls, tag: Any, export_path: str = None) -> Optional[str]:
        export_path = export_path or cls.DEFAULT_EXPORT_PATH
        nt = cls.normalize_tag(tag)
        if not nt:
            return None
        tag_to_cat, _, _ = cls._build_indexes(export_path, cls.DEFAULT_GUIDES_XLSX_PATH)
        return tag_to_cat.get(nt)

    @classmethod
    def unknown_tags(cls, tags: Iterable[Any], export_path: str = None, guides_xlsx_path: str = None) -> List[str]:
        export_path = export_path or cls.DEFAULT_EXPORT_PATH
        guides_xlsx_path = guides_xlsx_path or cls.DEFAULT_GUIDES_XLSX_PATH
        tag_to_cat, _, known_uncat = cls._build_indexes(export_path, guides_xlsx_path)
        out: List[str] = []
        for t in tags or []:
            nt = cls.normalize_tag(t)
            if not nt:
                continue
            if nt not in tag_to_cat and nt not in known_uncat:
                out.append(nt)
        # stable unique
        seen: Set[str] = set()
        uniq: List[str] = []
        for t in out:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
        return uniq


__all__ = ["TagDef", "PatternTagsTaxonomy"]
