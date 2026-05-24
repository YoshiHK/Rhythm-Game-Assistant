"""
Phase 7 CI — Catalog Presentation Helpers (Design-Locked)

Purpose:
- Presentation helpers must not crash on minimal/empty catalog config.

Non-goals:
- Does NOT validate catalog.json presence
- Does NOT validate UI fields correctness
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_phase7_catalog_loader() -> ModuleType:
    """
    Load Phase 7 catalog_loader.py by file path to avoid namespace collisions
    with Phase 6 (which may also have a top-level `catalog` package).
    """
    phase7_root = Path(__file__).resolve().parents[2]  # .../Phase 7 - Games Recommendation
    loader_path = phase7_root / "catalog" / "catalog_loader.py"
    assert loader_path.exists(), f"Phase 7 catalog_loader.py not found: {loader_path}"

    spec = importlib.util.spec_from_file_location("phase7_catalog_loader", loader_path)
    assert spec and spec.loader, "Unable to create import spec for Phase 7 catalog_loader.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def test_catalog_presentation_helpers_do_not_crash():
    m = _load_phase7_catalog_loader()

    load_catalog_config_optional = getattr(m, "load_catalog_config_optional")
    get_all_catalog_entries = getattr(m, "get_all_catalog_entries")
    get_catalog_entry = getattr(m, "get_catalog_entry")
    get_display_overrides = getattr(m, "get_display_overrides")

    cfg = load_catalog_config_optional()
    entries = get_all_catalog_entries(cfg)
    assert isinstance(entries, dict)

    # Must be safe even if catalog is empty
    _ = get_catalog_entry("non_existent_game", cfg)
    _ = get_display_overrides("non_existent_game", cfg)