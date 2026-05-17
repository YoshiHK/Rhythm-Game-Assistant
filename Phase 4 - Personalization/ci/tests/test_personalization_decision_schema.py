"""
Phase 4 CI — Personalization Decision Contract Presence (Design-Locked)

Purpose:
- Ensure Phase 4 decision-making is governed by explicit contract documents.
- Prevent silent removal of decision/safe-adjustment/model-inference interfaces.

This is STRUCTURAL ONLY (no runtime execution).
"""

from pathlib import Path


def _phase4_root() -> Path:
    # .../Phase 4 - Personalization/ci/tests/ -> parents[2] = Phase 4 - Personalization
    return Path(__file__).resolve().parents[2]


def _assert_nonempty_file(path: Path) -> None:
    assert path.exists(), f"Missing contract file: {path}"
    text = path.read_text(encoding="utf-8").strip()
    assert len(text) > 0, f"Contract file is empty: {path}"


def test_personalization_contract_docs_exist_and_nonempty():
    root = _phase4_root()
    interfaces = root / "interfaces"

    _assert_nonempty_file(interfaces / "personalization_decision.interface.md")
    _assert_nonempty_file(interfaces / "safe_adjustment.interface.md")
    _assert_nonempty_file(interfaces / "model_inference.interface.md")