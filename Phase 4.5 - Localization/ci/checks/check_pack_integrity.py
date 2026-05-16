#!/usr/bin/env python3
"""
Phase 4.5 Localization — Locale Pack Integrity Validator (CI-only, NON-RUNTIME)

Why this exists:
- Template work is cognitively expensive and drift-prone.
- This validator blocks drift early by enforcing structural contracts.

What it enforces:
1) Locale folder presence for all supported locales (from locales.json)
2) Required meta files per locale:
   - locale_meta.json
   - glossary.json
   - pack_version.json
3) Required template coverage per locale (from template_registry.json)
4) Template schema sanity:
   - template_id
   - version == "v3"
   - strings.default.text exists
5) Placeholder parity across locales (compared to base_locale)
6) Optional warnings on extra/unregistered templates

It supports two layouts (auto-detected per locale):
A) New layout:
   <locale>/_meta/*.json
   <locale>/chart_level/*.json
   <locale>/element_level/*.json
   <locale>/section_level/*.json
   <locale>/guidance_framing/*.json
   <locale>/tone/*.json
B) Legacy routing skeleton layout:
   <locale>/locale_meta.json
   <locale>/glossary/glossary.json or <locale>/glossary.json
   <locale>/templates/narrative_v3/**.json
   <locale>/variants/*.json

Exit codes:
- 0: pass
- 2: fail (any ERROR)

Usage (recommended):
python "Phase 4.5 - Localization/ci/checks/check_pack_integrity.py" \
  --translations-root "Phase 4.5 - Localization/translations" \
  --locales "Phase 4.5 - Localization/translations/_meta/locales.json" \
  --registry "Phase 4.5 - Localization/translations/_meta/template_registry.json"

If --locales/--registry are omitted, it will try to auto-discover.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Helpers
# -----------------------------

def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _is_json_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() == ".json"

def _stable_sort(paths: Iterable[Path]) -> List[Path]:
    return sorted(list(paths), key=lambda x: str(x))

def _find_first(root: Path, rel_candidates: List[str]) -> Optional[Path]:
    # direct children first
    for rel in rel_candidates:
        cand = root / rel
        if cand.exists():
            return cand
    # recursive fallback
    for rel in rel_candidates:
        hits = list(root.rglob(Path(rel).name))
        if hits:
            hits = _stable_sort(hits)
            return hits[0]
    return None

def _normalize_placeholders(ph: Any) -> List[str]:
    if ph is None:
        return []
    if isinstance(ph, list):
        return [str(x) for x in ph]
    return [str(ph)]


# -----------------------------
# Registry
# -----------------------------

@dataclass(frozen=True)
class Registry:
    chart_level: List[str]
    element_level: List[str]
    section_level: List[str]
    guidance_framing: List[str]
    tone: List[str]

    @property
    def all_ids(self) -> List[str]:
        return (
            list(self.chart_level)
            + list(self.element_level)
            + list(self.section_level)
            + list(self.guidance_framing)
            + list(self.tone)
        )

    def expected_counts(self) -> Dict[str, int]:
        return {
            "chart_level": len(self.chart_level),
            "element_level": len(self.element_level),
            "section_level": len(self.section_level),
            "guidance_framing": len(self.guidance_framing),
            "tone": len(self.tone),
            "total_templates": len(self.all_ids),
        }

def load_registry(p: Path) -> Registry:
    obj = _read_json(p)
    def _get(k: str) -> List[str]:
        v = obj.get(k, [])
        return [str(x) for x in v] if isinstance(v, list) else []
    return Registry(
        chart_level=_get("chart_level"),
        element_level=_get("element_level"),
        section_level=_get("section_level"),
        guidance_framing=_get("guidance_framing"),
        tone=_get("tone"),
    )


# -----------------------------
# Layout detection
# -----------------------------

@dataclass(frozen=True)
class Layout:
    kind: str              # "new" or "legacy"
    meta_dir: Path         # where meta files live

def detect_layout(locale_dir: Path) -> Layout:
    if (locale_dir / "_meta").exists() or (locale_dir / "chart_level").exists():
        return Layout("new", locale_dir / "_meta")
    if (locale_dir / "templates" / "narrative_v3").exists() or (locale_dir / "variants").exists():
        return Layout("legacy", locale_dir)
    return Layout("new", locale_dir / "_meta")


# -----------------------------
# Template discovery
# -----------------------------

def discover_template_files(locale_dir: Path) -> List[Path]:
    layout = detect_layout(locale_dir)
    files: List[Path] = []

    if layout.kind == "new":
        for sub in ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]:
            d = locale_dir / sub
            if d.exists():
                files += [p for p in d.rglob("*.json") if _is_json_file(p)]
        # tolerate transitional state where some templates are at locale root
        files += [p for p in locale_dir.glob("*.json") if _is_json_file(p)]
        # exclude meta
        files = [p for p in files if "_meta" not in p.parts]
        return _stable_sort(set(files))

    # legacy
    base = locale_dir / "templates" / "narrative_v3"
    if base.exists():
        files += [p for p in base.rglob("*.json") if _is_json_file(p)]
    var = locale_dir / "variants"
    if var.exists():
        files += [p for p in var.rglob("*.json") if _is_json_file(p)]
    return _stable_sort(set(files))

def load_templates_by_id(locale_dir: Path) -> Dict[str, Tuple[Path, Dict[str, Any]]]:
    out: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    for p in discover_template_files(locale_dir):
        try:
            obj = _read_json(p)
        except Exception:
            continue
        tid = obj.get("template_id")
        if isinstance(tid, str) and tid:
            if tid not in out or str(p) < str(out[tid][0]):
                out[tid] = (p, obj)
    return out


# -----------------------------
# Issues
# -----------------------------

@dataclass
class Issue:
    level: str   # ERROR / WARN
    locale: str
    msg: str


# -----------------------------
# Meta validations
# -----------------------------

def _meta_file_candidates(layout: Layout, locale_dir: Path, name: str) -> List[Path]:
    # new layout: <locale>/_meta/name, fallback to <locale>/name
    if layout.kind == "new":
        return [layout.meta_dir / name, locale_dir / name]
    # legacy: <locale>/name or <locale>/glossary/glossary.json
    return [locale_dir / name, locale_dir / "glossary" / name]

def validate_meta(locale: str, locale_dir: Path, reg: Registry) -> List[Issue]:
    issues: List[Issue] = []
    layout = detect_layout(locale_dir)

    # locale_meta.json
    lm = next((p for p in _meta_file_candidates(layout, locale_dir, "locale_meta.json") if p.exists()), None)
    if lm is None:
        issues.append(Issue("ERROR", locale, "Missing locale_meta.json"))
    else:
        try:
            obj = _read_json(lm)
            if obj.get("locale") != locale:
                issues.append(Issue("ERROR", locale, f"locale_meta.json locale mismatch: {obj.get('locale')} != {locale}"))
        except Exception as e:
            issues.append(Issue("ERROR", locale, f"Invalid locale_meta.json: {e}"))

    # glossary.json
    gl = next((p for p in _meta_file_candidates(layout, locale_dir, "glossary.json") if p.exists()), None)
    if gl is None:
        issues.append(Issue("ERROR", locale, "Missing glossary.json"))
    else:
        try:
            _read_json(gl)
        except Exception as e:
            issues.append(Issue("ERROR", locale, f"Invalid glossary.json: {e}"))

    # pack_version.json
    pv = next((p for p in _meta_file_candidates(layout, locale_dir, "pack_version.json") if p.exists()), None)
    if pv is None:
        issues.append(Issue("ERROR", locale, "Missing pack_version.json"))
    else:
        try:
            obj = _read_json(pv)
            if obj.get("locale") != locale:
                issues.append(Issue("ERROR", locale, f"pack_version locale mismatch: {obj.get('locale')} != {locale}"))
            cov = obj.get("coverage")
            if isinstance(cov, dict):
                exp = reg.expected_counts()
                for k in ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]:
                    if k in cov and isinstance(cov[k], int) and cov[k] != exp[k]:
                        issues.append(Issue("ERROR", locale, f"pack_version coverage mismatch {k}: {cov[k]} != {exp[k]}"))
        except Exception as e:
            issues.append(Issue("ERROR", locale, f"Invalid pack_version.json: {e}"))

    return issues


# -----------------------------
# Template validations
# -----------------------------

def validate_templates(locale: str, locale_dir: Path, reg: Registry) -> Tuple[List[Issue], Dict[str, Tuple[Path, Dict[str, Any]]]]:
    issues: List[Issue] = []
    templates = load_templates_by_id(locale_dir)
    required = set(reg.all_ids)

    missing = sorted(required - set(templates.keys()))
    if missing:
        issues.append(Issue("ERROR", locale, f"Missing templates: {missing}"))

    # schema sanity for required templates
    for tid in sorted(required & set(templates.keys())):
        p, obj = templates[tid]
        if obj.get("version") != "v3":
            issues.append(Issue("ERROR", locale, f"{tid} version != v3 in {p}"))
        strings = obj.get("strings")
        if not isinstance(strings, dict) or "default" not in strings:
            issues.append(Issue("ERROR", locale, f"{tid} missing strings.default in {p}"))
            continue
        for vk, vv in strings.items():
            if not isinstance(vv, dict):
                issues.append(Issue("ERROR", locale, f"{tid}:{vk} must be object in {p}"))
                continue
            if "text" not in vv or not isinstance(vv.get("text"), str):
                issues.append(Issue("ERROR", locale, f"{tid}:{vk} missing text in {p}"))
            ph = vv.get("placeholders", [])
            if not isinstance(ph, list):
                issues.append(Issue("ERROR", locale, f"{tid}:{vk} placeholders must be list in {p}"))

    extra = sorted(set(templates.keys()) - required)
    if extra:
        issues.append(Issue("WARN", locale, f"Extra templates not in registry: {extra}"))

    return issues, templates


def validate_placeholder_parity(base_locale: str, locale_dirs: Dict[str, Path], reg: Registry) -> List[Issue]:
    issues: List[Issue] = []
    if base_locale not in locale_dirs:
        issues.append(Issue("ERROR", base_locale, "Base locale directory missing; cannot validate placeholder parity"))
        return issues

    base = load_templates_by_id(locale_dirs[base_locale])

    for loc, d in locale_dirs.items():
        if loc == base_locale:
            continue
        cur = load_templates_by_id(d)
        for tid in reg.all_ids:
            if tid not in base or tid not in cur:
                continue
            _, bobj = base[tid]
            _, cobj = cur[tid]
            bs = bobj.get("strings", {})
            cs = cobj.get("strings", {})
            if not isinstance(bs, dict) or not isinstance(cs, dict):
                continue

            for vk, bvv in bs.items():
                if vk not in cs:
                    issues.append(Issue("ERROR", loc, f"{tid} missing variant '{vk}' (base has it)"))
                    continue
                cvv = cs[vk]
                bph = _normalize_placeholders(bvv.get("placeholders", []))
                cph = _normalize_placeholders(cvv.get("placeholders", []))
                if bph != cph:
                    issues.append(Issue("ERROR", loc, f"Placeholder mismatch {tid}:{vk} {cph} != base {bph}"))
    return issues


# -----------------------------
# CI summary
# -----------------------------

def emit_ci_summary(issues: List[Issue]) -> None:
    errs = sum(1 for i in issues if i.level == "ERROR")
    warns = sum(1 for i in issues if i.level == "WARN")
    print(f"LOCALIZATION_PACK_VALIDATION errors={errs} warnings={warns}")


# -----------------------------
# Main
# -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    ap.add_argument("--locales", type=str, default=None)
    ap.add_argument("--registry", type=str, default=None)
    ap.add_argument("--fail-on-warn", action="store_true")
    args = ap.parse_args(argv)

    cwd = Path.cwd()
    translations_root = Path(args.translations_root) if args.translations_root else _find_first(
        cwd, ["translations", "Phase 4.5 - Localization/translations", "Phase_4.5_Localization/translations"]
    )
    if translations_root is None or not translations_root.exists():
        print("ERROR: cannot locate translations root")
        return 2

    locales_path = Path(args.locales) if args.locales else _find_first(
        translations_root, ["_meta/locales.json", "locales.json"]
    )
    if locales_path is None or not locales_path.exists():
        print("ERROR: cannot locate locales.json")
        return 2

    registry_path = Path(args.registry) if args.registry else _find_first(
        translations_root, ["_meta/template_registry.json", "template_registry.json"]
    )
    if registry_path is None or not registry_path.exists():
        print("ERROR: cannot locate template_registry.json")
        return 2

    locales_obj = _read_json(locales_path)
    supported = locales_obj.get("supported_locales", [])
    base_locale = str(locales_obj.get("base_locale", "en-US"))
    if not isinstance(supported, list) or not supported:
        print("ERROR: locales.json supported_locales missing")
        return 2
    supported_locales = [str(x) for x in supported]

    reg = load_registry(registry_path)

    issues: List[Issue] = []
    locale_dirs: Dict[str, Path] = {}

    # per-locale checks
    for loc in supported_locales:
        d = translations_root / loc
        if not d.exists():
            issues.append(Issue("ERROR", loc, f"Missing locale directory: {d}"))
            continue
        locale_dirs[loc] = d
        issues += validate_meta(loc, d, reg)
        t_issues, _ = validate_templates(loc, d, reg)
        issues += t_issues

    # cross-locale parity
    issues += validate_placeholder_parity(base_locale, locale_dirs, reg)

    # print details (deterministic order)
    for i in sorted(issues, key=lambda x: (x.level, x.locale, x.msg)):
        prefix = "ERROR" if i.level == "ERROR" else "WARN"
        print(f"{prefix}[{i.locale}]: {i.msg}")

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
