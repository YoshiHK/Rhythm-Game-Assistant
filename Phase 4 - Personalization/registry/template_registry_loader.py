
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
from typing import Any, Dict, List, Optional
import json


@dataclass(frozen=True)
class LoadedTemplateRegistries:
    registry_version: str
    default_locale: str
    template_registry: Dict[str, List[str]]
    variant_registry: Dict[str, List[str]]


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Template registry must be a JSON object.")
    return data


def _pick_templates_for_difficulty(
    block: Dict[str, Any],
    *,
    locale: Optional[str],
    default_locale: str,
) -> List[str]:
    default_list = block.get("default") or []
    if not isinstance(default_list, list) or not default_list:
        raise ValueError("Each difficulty must define a non-empty default template list.")

    locales = block.get("locales") or {}
    loc = (locale or "").strip() or None

    if loc and isinstance(locales, dict) and loc in locales:
        return [str(x) for x in locales[loc] if str(x)]

    if default_locale and isinstance(locales, dict) and default_locale in locales:
        return [str(x) for x in locales[default_locale] if str(x)]

    return [str(x) for x in default_list if str(x)]


def _filter_variant_ids(
    variants_block: Dict[str, Any],
    *,
    include_experimental: bool,
) -> List[str]:
    items = variants_block.get("variants") or []
    if not isinstance(items, list):
        return []

    allowed: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        vid = item.get("variant_id")
        if not isinstance(vid, str):
            continue
        if status == "active" or (include_experimental and status == "experimental"):
            allowed.append(vid)
    return allowed


def load_phase4_template_registry(
    registry_path: str,
    *,
    locale: Optional[str] = None,
    include_experimental_variants: bool = False,
) -> LoadedTemplateRegistries:
    data = _read_json(registry_path)

    registry_version = data.get("registry_version")
    if not isinstance(registry_version, str):
        raise ValueError("registry_version is required.")

    default_locale = data.get("default_locale") or ""
    templates_by_difficulty = data.get("templates_by_difficulty") or {}
    variants_by_template = data.get("variants_by_template") or {}

    template_registry: Dict[str, List[str]] = {}
    for difficulty, block in templates_by_difficulty.items():
        template_registry[difficulty] = _pick_templates_for_difficulty(
            block,
            locale=locale,
            default_locale=default_locale,
        )

    variant_registry: Dict[str, List[str]] = {}
    for template_id, vblock in variants_by_template.items():
        variant_registry[template_id] = _filter_variant_ids(
            vblock,
            include_experimental=include_experimental_variants,
        )

    return LoadedTemplateRegistries(
        registry_version=registry_version,
        default_locale=default_locale,
        template_registry=template_registry,
        variant_registry=variant_registry,
    )
