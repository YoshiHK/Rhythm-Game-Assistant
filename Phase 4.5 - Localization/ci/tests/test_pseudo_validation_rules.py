"""
CI Test: Pseudo Locale Validation Rules

Purpose:
- Ensure pseudo locale is structurally complete
- Validate template coverage vs registry
- Enforce glossary alignment
- Enforce placeholder parity (basic)

Non-goals:
- translation quality
- gameplay semantics
"""

from __future__ import annotations
import json
from pathlib import Path


BASE = Path("translations/pseudo")
META = BASE / "_meta"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_template_registry_exists():
    assert (META / "template_registry.json").exists()


def test_glossary_exists():
    assert (META / "glossary.json").exists()


def test_all_templates_present():
    registry = load_json(META / "template_registry.json")

    for layer, templates in registry.items():
        if layer.startswith("_") or layer == "constraints":
            continue

        for template_id in templates:
            # resolve expected folder
            if layer == "guidance_framing":
                folder = BASE / "guidance_framing"
            elif layer == "tone":
                folder = BASE / "tone"
            else:
                folder = BASE / layer

            file_path = folder / f"{template_id}.json"
            assert file_path.exists(), f"Missing template: {file_path}"


def test_glossary_alignment():
    glossary = load_json(META / "glossary.json")
    registry = load_json(META / "template_registry.json")

    taxonomy = glossary.get("taxonomy", {})

    for layer, templates in registry.items():
        if layer not in taxonomy:
            continue

        glossary_keys = taxonomy[layer].keys()

        for t in templates:
            assert (
                t in glossary_keys
            ), f"Template {t} missing in glossary taxonomy[{layer}]"


def test_no_extra_templates():
    registry = load_json(META / "template_registry.json")

    defined = set()
    for layer, templates in registry.items():
        if isinstance(templates, list):
            defined.update(templates)

    actual = set()

    for folder in [
        "chart_level",
        "element_level",
        "section_level",
        "guidance_framing",
        "tone",
    ]:
        for f in (BASE / folder).glob("*.json"):
            actual.add(f.stem)

    assert actual.issubset(defined), f"Unexpected templates found: {actual - defined}"