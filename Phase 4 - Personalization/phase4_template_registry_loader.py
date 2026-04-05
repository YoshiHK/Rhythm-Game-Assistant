
#!/usr/bin/env python3
"""phase4_template_registry_loader.py

Phase 4 Template Registry Loader

Loads and validates the Phase 4 narrative template registry and produces
in-memory registries in the exact shapes expected by:
- phase4_model_inference.TemplateSelector (difficulty -> [template_id])
- phase4_model_inference.run_phase4_model_inference variant_registry (template_id -> [variant_id])

Key rules:
- Registry is an allow-list. Only listed templates/variants may be used.
- Variants are filtered by status (active/experimental) based on caller flags.
- No IO beyond reading the registry file.
- Does not modify any Phase 1–3 behavior.

Files created earlier:
- PHASE_4_TEMPLATE_REGISTRY.schema.json (schema)
- PHASE_4_TEMPLATE_REGISTRY_STARTER.json (starter registry)

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json


@dataclass(frozen=True)
class LoadedTemplateRegistries:
    """Convenience bundle returned by loader."""
    registry_version: str
    default_locale: str
    template_registry: Dict[str, List[str]]
    variant_registry: Dict[str, List[str]]


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _pick_templates_for_difficulty(
    block: Dict[str, Any],
    *,
    locale: Optional[str],
    default_locale: str,
) -> List[str]:
    """Pick templates for a difficulty with optional locale override."""
    if not isinstance(block, dict):
        return []
    # default list
    default_list = block.get("default") or []
    if not isinstance(default_list, list):
        default_list = []
    # locale override
    loc = (locale or "").strip() or None
    locales = block.get("locales") or {}
    if loc and isinstance(locales, dict) and loc in locales and isinstance(locales.get(loc), list):
        return [str(x) for x in locales.get(loc) if str(x)]
    # fallback to default locale override if provided (e.g., use default_locale)
    if (not loc) and default_locale and isinstance(locales, dict) and default_locale in locales and isinstance(locales.get(default_locale), list):
        return [str(x) for x in locales.get(default_locale) if str(x)]
    return [str(x) for x in default_list if str(x)]


def _filter_variant_ids(
    variants_block: Dict[str, Any],
    *,
    include_experimental: bool,
) -> List[str]:
    """Return allowed variant_id list filtered by status."""
    if not isinstance(variants_block, dict):
        return []
    items = variants_block.get("variants") or []
    if not isinstance(items, list):
        return []

    allowed: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        vid = it.get("variant_id")
        status = str(it.get("status") or "").strip().lower()
        if not isinstance(vid, str) or not vid:
            continue
        if status == "active":
            allowed.append(vid)
        elif status == "experimental" and include_experimental:
            allowed.append(vid)
        # disabled is never included
    return allowed


def load_phase4_template_registry(
    registry_path: str = "PHASE_4_TEMPLATE_REGISTRY_STARTER.json",
    *,
    locale: Optional[str] = None,
    include_experimental_variants: bool = False,
) -> LoadedTemplateRegistries:
    """Load Phase 4 template registry and return normalized registries.

    Parameters
    ----------
    registry_path:
        Path to registry JSON file.
    locale:
        Locale hint for selecting locale-specific template lists.
    include_experimental_variants:
        If True, include variants with status == "experimental".

    Returns
    -------
    LoadedTemplateRegistries
        template_registry: {difficulty: [template_id, ...]}
        variant_registry: {template_id: [variant_id, ...]}

    Notes
    -----
    - This function does not perform JSON Schema validation (kept dependency-free).
      Callers may validate separately in CI or build pipelines.
    """
    data = _read_json(registry_path)

    reg_ver = str(data.get("registry_version") or "v0")
    default_locale = str(data.get("default_locale") or "") or "en-US"

    tbd = data.get("templates_by_difficulty") or {}
    if not isinstance(tbd, dict):
        tbd = {}

    # Build template_registry in the shape expected by TemplateSelector
    template_registry: Dict[str, List[str]] = {}
    for diff, block in tbd.items():
        if not isinstance(diff, str) or not diff:
            continue
        templates = _pick_templates_for_difficulty(block, locale=locale, default_locale=default_locale)
        # Ensure stable ordering + uniqueness
        seen = set()
        out = []
        for t in templates:
            if t and t not in seen:
                out.append(t)
                seen.add(t)
        if out:
            template_registry[diff.strip().lower()] = out

    # Build variant_registry in the shape expected by BanditPolicy usage
    vbt = data.get("variants_by_template") or {}
    if not isinstance(vbt, dict):
        vbt = {}

    variant_registry: Dict[str, List[str]] = {}
    for template_id, vblock in vbt.items():
        if not isinstance(template_id, str) or not template_id:
            continue
        vids = _filter_variant_ids(vblock, include_experimental=include_experimental_variants)
        # stable unique
        seen = set()
        out = []
        for vid in vids:
            if vid and vid not in seen:
                out.append(vid)
                seen.add(vid)
        if out:
            variant_registry[template_id] = out

    return LoadedTemplateRegistries(
        registry_version=reg_ver,
        default_locale=default_locale,
        template_registry=template_registry,
        variant_registry=variant_registry,
    )


__all__ = [
    "LoadedTemplateRegistries",
    "load_phase4_template_registry",
]
