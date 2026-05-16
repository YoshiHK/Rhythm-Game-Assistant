#!/usr/bin/env python3
"""
Phase 4.5 Localization — Taxonomy ↔ Registry Validator (CI-only, NON-RUNTIME)

This validator prevents drift between:
- Global template registry (template_registry.json)
- Taxonomy documents (Element/Chart/Section/Guidance/Tone)

It DOES NOT overlap with pseudo locale tests:
- It does not read translations/pseudo templates
- It does not validate translation quality or token parity
- It validates contract-document alignment only

Exit codes:
- 0: pass
- 2: fail (any ERROR)

Usage:
python "Phase 4.5 - Localization/ci/checks/taxonomy_validator.py" \
  --translations-root "Phase 4.5 - Localization/translations"
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# -----------------------------
# Helpers
# -----------------------------

def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def _find_first(root: Path, candidates: List[str]) -> Optional[Path]:
    # direct candidates
    for rel in candidates:
        cand = root / rel
        if cand.exists():
            return cand
    # recursive fallback (deterministic)
    hits: List[Path] = []
    for rel in candidates:
        hits += list(root.rglob(Path(rel).name))
    if hits:
        hits = sorted(hits, key=lambda x: str(x))
        return hits[0]
    return None

def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# -----------------------------
# Taxonomy parsing
# -----------------------------

TAXONOMY_FILES = {
    "element_level": "ELEMENT_TEMPLATE_TAXONOMY.md",
    "chart_level": "CHART_TEMPLATE_TAXONOMY.md",
    "section_level": "SECTION_TEMPLATE_TAXONOMY.md",
    "guidance_framing": "GUIDANCE_TEMPLATE_TAXONOMY.md",
    "tone": "TONE_TEMPLATE_TAXONOMY.md",
}

# Match markdown list lines like:
# - element_density
# - burst_section
# - neutral
_LIST_ITEM_RE = re.compile(r"^\s*-\s+([A-Za-z0-9_\-]+)\s*$")

def parse_taxonomy_ids(md_text: str) -> List[str]:
    ids: List[str] = []
    for line in md_text.splitlines():
        m = _LIST_ITEM_RE.match(line)
        if m:
            ids.append(m.group(1))
    return ids


# -----------------------------
# Issues
# -----------------------------

@dataclass
class Issue:
    level: str   # ERROR / WARN
    where: str
    message: str


def emit_ci_summary(issues: List[Issue]) -> None:
    errs = sum(1 for i in issues if i.level == "ERROR")
    warns = sum(1 for i in issues if i.level == "WARN")
    # single-line, machine-consumable
    print(f"LOCALIZATION_TAXONOMY_VALIDATION errors={errs} warnings={warns}")


# -----------------------------
# Main validation
# -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    ap.add_argument("--registry", type=str, default=None)
    ap.add_argument("--taxonomy-root", type=str, default=None)
    ap.add_argument("--fail-on-warn", action="store_true")
    args = ap.parse_args(argv)

    cwd = Path.cwd()

    translations_root = Path(args.translations_root) if args.translations_root else _find_first(
        cwd, ["translations", "Phase 4.5 - Localization/translations", "Phase_4.5_Localization/translations"]
    )
    if translations_root is None or not translations_root.exists():
        print("ERROR: cannot locate translations root")
        return 2

    registry_path = Path(args.registry) if args.registry else _find_first(
        translations_root, ["_meta/template_registry.json", "template_registry.json"]
    )
    if registry_path is None or not registry_path.exists():
        print("ERROR: cannot locate template_registry.json")
        return 2

    # taxonomy root: optional; if absent, search from repo root
    taxonomy_root = Path(args.taxonomy_root) if args.taxonomy_root else cwd

    registry = _read_json(registry_path)

    # Extract registry ids per layer
    layers = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]
    reg_ids_by_layer: Dict[str, List[str]] = {}
    for layer in layers:
        v = registry.get(layer, [])
        reg_ids_by_layer[layer] = [str(x) for x in v] if isinstance(v, list) else []

    reg_all: Set[str] = set(sum(reg_ids_by_layer.values(), []))

    # Load taxonomy docs and parse ids
    tax_ids_by_layer: Dict[str, List[str]] = {}
    tax_paths: Dict[str, Path] = {}
    issues: List[Issue] = []

    for layer, fname in TAXONOMY_FILES.items():
        p = _find_first(taxonomy_root, [fname])
        if p is None or not p.exists():
            issues.append(Issue("ERROR", layer, f"Missing taxonomy doc: {fname}"))
            tax_ids_by_layer[layer] = []
            continue
        tax_paths[layer] = p
        ids = parse_taxonomy_ids(_read_text(p))
        tax_ids_by_layer[layer] = ids

    # 1) Taxonomy must not reference unknown ids (not in registry)
    for layer, ids in tax_ids_by_layer.items():
        unknown = sorted(set(ids) - reg_all)
        if unknown:
            issues.append(Issue(
                "ERROR",
                layer,
                f"Taxonomy references ids not in registry: {unknown} (file={tax_paths.get(layer)})"
            ))

    # 2) Registry ids must all appear in the corresponding taxonomy doc
    for layer in layers:
        missing = sorted(set(reg_ids_by_layer[layer]) - set(tax_ids_by_layer.get(layer, [])))
        if missing:
            issues.append(Issue(
                "ERROR",
                layer,
                f"Registry ids missing in taxonomy: {missing} (taxonomy={tax_paths.get(layer)})"
            ))

    # 3) No id may appear in more than one taxonomy layer
    owner: Dict[str, str] = {}
    for layer, ids in tax_ids_by_layer.items():
        for tid in ids:
            if tid not in reg_all:
                continue  # already handled as unknown
            if tid in owner and owner[tid] != layer:
                issues.append(Issue(
                    "ERROR",
                    "overlap",
                    f"Template id '{tid}' appears in multiple taxonomies: {owner[tid]} and {layer}"
                ))
            else:
                owner[tid] = layer

    # Emit details (deterministic)
    for i in sorted(issues, key=lambda x: (x.level, x.where, x.message)):
        prefix = "ERROR" if i.level == "ERROR" else "WARN"
        print(f"{prefix}[{i.where}]: {i.message}")

    emit_ci_summary(issues)

    err_count = sum(1 for i in issues if i.level == "ERROR")
    warn_count = sum(1 for i in issues if i.level == "WARN")
    if err_count > 0:
        return 2
    if args.fail_on_warn and warn_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())