"""
Phase 7 CI — Catalog Completeness (Design-Locked)

Catalog is OPTIONAL.
Absence of catalog.json MUST NOT break Phase 7.

Non-goals:
- Does NOT require catalog.json to exist
- Does NOT validate catalog content quality
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict


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


def test_catalog_optional_loading():
    """
    Catalog is optional.
    Absence of catalog.json must not break Phase 7.
    """
    m = _load_phase7_catalog_loader()
    load_catalog_config_optional = getattr(m, "load_catalog_config_optional")

    cfg = load_catalog_config_optional()
    assert isinstance(cfg, dict)
    assert "catalog" in cfg
    assert isinstance(cfg["catalog"], dict)


def test_catalog_entries_keyed_by_game_id():
    """
    If catalog entries exist, they must be keyed by game_id (str),
    and each entry value must be a dict (presentation metadata).
    """
    m = _load_phase7_catalog_loader()
    load_catalog_config_optional = getattr(m, "load_catalog_config_optional")
    get_all_catalog_entries = getattr(m, "get_all_catalog_entries")

    cfg = load_catalog_config_optional()
    entries: Dict[str, Dict[str, Any]] = get_all_catalog_entries(cfg)

    assert isinstance(entries, dict)
    for k, v in entries.items():
        assert isinstance(k, str)
        assert isinstance(v, dict)
