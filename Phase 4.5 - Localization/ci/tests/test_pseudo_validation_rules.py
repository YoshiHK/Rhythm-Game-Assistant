"""
CI Infrastructure Test: Pseudo Validation Rules

Purpose:
- Validate minimal structural rules for pseudo locale
- Ensure pseudo locale behaves like a FULL locale (no shortcuts)

Non-goals:
- Translation correctness
- Business logic validation
"""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_LAYERS = [
    "chart_level",
    "element_level",
    "section_level",
    "guidance_framing",
    "tone",
]


def _make_fixture(translations_root: Path) -> None:
    """
    Create minimal but valid translations tree for testing
    """

    # --- global meta ---
    meta = translations_root / "_meta"
    meta.mkdir(parents=True, exist_ok=True)

    (meta / "locales.json").write_text(
        """{
  "base_locale": "en-US",
  "supported_locales": ["en-US", "pseudo"]
}""",
        encoding="utf-8",
    )

    (meta / "template_registry.json").write_text(
        """{
  "chart_level": ["chart_summary"],
  "element_level": [],
  "section_level": [],
  "guidance_framing": [],
  "tone": ["neutral"]
}""",
        encoding="utf-8",
    )

    # --- locale builder ---
    def make_locale(loc: str):
        loc_dir = translations_root / loc

        # meta files
        m = loc_dir / "_meta"
        m.mkdir(parents=True, exist_ok=True)

        for fname in ["locale_meta.json", "glossary.json", "pack_version.json", "debug.json"]:
            (m / fname).write_text("{}", encoding="utf-8")

        # layers
        for layer in REQUIRED_LAYERS:
            (loc_dir / layer).mkdir(parents=True, exist_ok=True)

        # minimal chart template
        (loc_dir / "chart_level" / "chart_summary.json").write_text(
            """{
  "template_id": "chart_summary",
  "version": "v3",
  "strings": {
    "default": {
      "text": "Summary: {base_text}",
      "placeholders": ["base_text"]
    }
  }
}""",
            encoding="utf-8",
        )

        # minimal tone template
        (loc_dir / "tone" / "neutral.json").write_text(
            """{
  "template_id": "neutral",
  "version": "v3",
  "strings": {
    "default": {
      "text": "{base_text}",
      "placeholders": ["base_text"]
    }
  }
}""",
            encoding="utf-8",
        )

    make_locale("en-US")
    make_locale("pseudo")


# ✅ ✅ ✅ TESTS


def test_pseudo_has_full_structure(tmp_path: Path) -> None:
    translations_root = tmp_path / "translations"
    _make_fixture(translations_root)

    pseudo_dir = translations_root / "pseudo"

    # must exist
    assert pseudo_dir.exists()

    # must have _meta
    meta = pseudo_dir / "_meta"
    assert meta.exists()

    for fname in ["locale_meta.json", "glossary.json", "pack_version.json", "debug.json"]:
        assert (meta / fname).exists(), f"Missing {fname} in pseudo/_meta"

    # must have all layers
    for layer in REQUIRED_LAYERS:
        assert (pseudo_dir / layer).exists(), f"Missing layer {layer} in pseudo"


def test_pseudo_matches_base_templates(tmp_path: Path) -> None:
    translations_root = tmp_path / "translations"
    _make_fixture(translations_root)

    base_dir = translations_root / "en-US"
    pseudo_dir = translations_root / "pseudo"

    def get_template_ids(locale_dir: Path):
        out = set()
        for layer in REQUIRED_LAYERS:
            for f in (locale_dir / layer).glob("*.json"):
                obj = json.loads(f.read_text(encoding="utf-8"))
                out.add(obj["template_id"])
        return out

    base_ids = get_template_ids(base_dir)
    pseudo_ids = get_template_ids(pseudo_dir)

    assert base_ids == pseudo_ids, "Pseudo locale must match base templates exactly"