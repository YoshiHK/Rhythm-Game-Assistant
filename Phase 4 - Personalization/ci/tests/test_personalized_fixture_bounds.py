"""
Phase 4 CI: Bounded-Safety Assertions (Personalized Fixtures) — Part 1/2
Design-Locked Upgrade (Part 1)

Patch intent
------------
Tighten policy checks to align with PHASE_4_SPEC.md §7.2 (Explainability Chain):
  decision_source → model_outputs → applied_adjustments → provenance

This test is a policy/safety guardrail:
- It does NOT evaluate personalization quality.
- It does NOT evaluate translation/narrative quality.
- It enforces structural invariants only.

Run:
  python ci/phase4/test_personalized_fixture_bounds.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# Fixtures live alongside this file.
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ----------------------------
# Basic helpers (CI-only)
# ----------------------------

def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Failed to parse JSON: {path} ({e})")
    if not isinstance(obj, dict):
        fail(f"Fixture root must be an object: {path}")
    return obj


def is_personalized_fixture(fx: Dict[str, Any]) -> bool:
    return str(fx.get("engine_mode", "")).strip().lower() == "personalized"


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def index_by_element_id(elements: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build {element_id: element_obj} for list-like element structures.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for el in elements:
        if not isinstance(el, dict):
            continue
        eid = el.get("element_id")
        if isinstance(eid, str) and eid.strip():
            out[eid] = el
    return out


def extract_ids_any(x: Any) -> List[str]:
    """
    Extract element_id strings from a variety of list-like structures.

    Supported patterns:
    - ["E1", "E2", ...]
    - [{"element_id": "E1"}, ...]
    - [{"id": "E1"}, ...]
    """
    if x is None:
        return []
    if isinstance(x, list):
        out: List[str] = []
        for item in x:
            if isinstance(item, str) and item.strip():
                out.append(item)
            elif isinstance(item, dict):
                eid = item.get("element_id") or item.get("id")
                if isinstance(eid, str) and eid.strip():
                    out.append(eid)
            # ints (index-based) are ignored as ambiguous
        return out
    return []


def assert_permutation(input_ids: List[str], output_ids: List[str]) -> None:
    """
    Require output_ids to be a permutation of input_ids (no drops, no additions).
    Ordering is validated separately.
    """
    if sorted(input_ids) != sorted(output_ids):
        missing = sorted(set(input_ids) - set(output_ids))
        extra = sorted(set(output_ids) - set(input_ids))
        fail(
            "elements_view is not a permutation of input elements. "
            f"Missing={missing} Extra={extra}"
        )


def assert_order_subsequence(expected_ids: List[str], out_order: List[str]) -> None:
    """
    Require expected_ids to appear as an in-order subsequence within out_order.

    This is stricter than "contains" but weaker than "exact match".
    It allows Phase 4 to insert presentation-only elements_view items
    (if allowed by spec) while preserving relative order.
    """
    it = iter(out_order)
    for eid in expected_ids:
        for got in it:
            if got == eid:
                break
        else:
            fail(
                "Ordering integrity failed: expected id "
                f"'{eid}' not found in-order in output order {out_order}"
            )


# ----------------------------
# Phase 4 runtime invocation (injected import)
# ----------------------------

def run_phase4(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute Phase 4 personalization runtime for a single fixture.

    - This function performs no semantic evaluation.
    - It is a wiring-only invocation helper.
    """
    try:
        from phase4_personalization_runtime import run_phase4_personalization
    except Exception as e:
        fail(f"Unable to import Phase 4 runtime: {e}")

    # Mandatory fixture keys (fail loud)
    for k in ("canonical_payload", "canonical_row", "selected_elements", "difficulty"):
        if k not in fixture:
            fail(f"Fixture missing required key '{k}'")

    out = run_phase4_personalization(
        canonical_payload=fixture["canonical_payload"],
        canonical_row=fixture["canonical_row"],
        selected_elements=fixture["selected_elements"],
        difficulty=fixture["difficulty"],
        engine_mode="personalized",
        player_id_hash=fixture.get("player_id_hash"),
        locale=fixture.get("locale"),
        feature_flags=fixture.get("feature_flags"),
        opt_in=fixture.get("opt_in"),
    )

    if not isinstance(out, dict):
        fail("Phase 4 runtime output must be a dict")

    return out


# ----------------------------
# Safety filtering helpers
# ----------------------------

def _flt_weights(d: Dict[str, Any], allowed_ids: Set[str]) -> Dict[str, float]:
    """
    Filter weight dict to {element_id: float} limited to allowed element_ids.
    This avoids comparing weights for unknown/extra keys.
    """
    out: Dict[str, float] = {}
    for k, v in d.items():
        if isinstance(k, str) and k in allowed_ids and isinstance(v, (int, float)):
            out[k] = float(v)
    return out

# ----------------------------
# Part 2/2 — Policy assertions + runner
# ----------------------------

# Fields that MUST NOT change (semantic immutability) for personalized fixtures.
# Note: This is stricter than Phase4 safety_checks, because this fixture test is
# explicitly scoped to PHASE_4_SPEC §7.2 chain + element immutability.
IMMUTABLE_ELEMENT_FIELDS = (
    "severity_label",
    "score",
    "training_items",
    "matched_tags",
    "guidance",
)

# Only these adjustment keys are allowed to escape the safety filter into applied_adjustments.
ALLOWED_ADJUSTMENT_KEYS = {
    "element_ordering",
    "ranking_weights",
    "narrative_template_id",
    "variant_id",
}

# Treat these decision sources as "model-driven" for chain enforcement.
MODEL_LIKE_SOURCES = {"model", "hybrid"}
RULE_LIKE_SOURCES = {"rule"}


def _require_dict(x, *, name: str) -> dict:
    if not isinstance(x, dict):
        fail(f"{name} must be an object")
    return x


def _require_list(x, *, name: str) -> list:
    if not isinstance(x, list):
        fail(f"{name} must be a list")
    return x


def _lower_str(x, *, name: str) -> str:
    if not isinstance(x, str) or not x.strip():
        fail(f"{name} must be a non-empty string")
    return x.strip().lower()


def assert_no_semantic_mutation(fixture: dict, out: dict) -> None:
    """
    Policy/safety assertions for personalized fixtures.

    Enforces:
    - No element creation/deletion
    - No semantic field mutation on elements_view
    - Explainability chain consistency (Spec §7.2)
    - Ordering consistency (Spec §7.3)
    - Optional model_metadata readiness (Spec §7.4)
    - Disallow unexpected applied_adjustments keys
    """
    fixture = _require_dict(fixture, name="fixture")
    out = _require_dict(out, name="Phase 4 runtime output")

    # --- inputs/outputs
    inp_elements = fixture.get("selected_elements")
    inp_elements = _require_list(inp_elements, name="fixture.selected_elements")
    if not inp_elements:
        fail("Fixture selected_elements missing or empty")

    out_elements = out.get("elements_view")
    out_elements = _require_list(out_elements, name="output.elements_view")
    if not out_elements:
        fail("Output elements_view missing or empty")

    inp_idx = index_by_element_id(inp_elements)
    out_idx = index_by_element_id(out_elements)

    if not inp_idx:
        fail("No element_id found in fixture selected_elements")
    if not out_idx:
        fail("No element_id found in output elements_view")

    inp_ids = list(inp_idx.keys())
    out_ids = list(out_idx.keys())

    # Must be a permutation (no add/drop)
    assert_permutation(inp_ids, out_ids)

    # --- per-element immutability
    for eid, inp in inp_idx.items():
        out_el = out_idx.get(eid)
        if out_el is None:
            fail(f"Missing element in output: {eid}")
        for field in IMMUTABLE_ELEMENT_FIELDS:
            if inp.get(field) != out_el.get(field):
                fail(f"Semantic field '{field}' changed for element_id={eid}")

    # --- provenance and chain objects
    prov = out.get("phase4_provenance")
    prov = _require_dict(prov, name="output.phase4_provenance")

    gates = prov.get("gates")
    gates = _require_dict(gates, name="phase4_provenance.gates")

    engine_mode = prov.get("engine_mode")
    if str(engine_mode) != "personalized":
        fail(f"phase4_provenance.engine_mode must be 'personalized', got {engine_mode!r}")

    # Personalized fixtures must have personalization_allowed=True gate.
    if gates.get("personalization_allowed") is not True:
        fail("phase4_provenance.gates.personalization_allowed must be true for personalized fixture")

    decision_source = _lower_str(prov.get("decision_source"), name="phase4_provenance.decision_source")

    model_out = _require_dict(out.get("model_outputs") or {}, name="output.model_outputs")
    applied = _require_dict(out.get("applied_adjustments") or {}, name="output.applied_adjustments")

    prov_adj = prov.get("adjustments")
    if prov_adj is None:
        prov_adj = {}
    if prov_adj and not isinstance(prov_adj, dict):
        fail("phase4_provenance.adjustments must be an object when present")
    prov_adj = prov_adj if isinstance(prov_adj, dict) else {}

    allowed_ids = set(out_idx.keys())

    # --- Spec §7.2: decision_source ↔ model_outputs ↔ applied_adjustments
    if decision_source in MODEL_LIKE_SOURCES:
        if not model_out:
            fail('Spec §7.2: decision_source="model/hybrid" requires model_outputs to be present (non-empty)')

        # 1) element_ordering
        if "element_ordering" in model_out:
            if "element_ordering" not in applied:
                fail("Spec §7.2: model_outputs.element_ordering present but applied_adjustments.element_ordering missing")

            mo_ids = [eid for eid in extract_ids_any(model_out.get("element_ordering")) if eid in allowed_ids]
            ap_ids = [eid for eid in extract_ids_any(applied.get("element_ordering")) if eid in allowed_ids]

            # Only enforce if model emits usable IDs
            if mo_ids and ap_ids != mo_ids:
                fail(
                    "Spec §7.2: applied_adjustments.element_ordering "
                    f"{ap_ids} != filtered model_outputs.element_ordering {mo_ids}"
                )

        # 2) ranking_weights
        if "ranking_weights" in model_out:
            if "ranking_weights" not in applied:
                fail("Spec §7.2: model_outputs.ranking_weights present but applied_adjustments.ranking_weights missing")

            mw = model_out.get("ranking_weights")
            aw = applied.get("ranking_weights")
            if not isinstance(mw, dict) or not isinstance(aw, dict):
                fail("ranking_weights must be objects in both model_outputs and applied_adjustments")

            mwf = _flt_weights(mw, allowed_ids)
            awf = _flt_weights(aw, allowed_ids)

            if mwf.keys() != awf.keys():
                fail(
                    "Spec §7.2: ranking_weights keys differ. "
                    f"model={sorted(mwf.keys())} applied={sorted(awf.keys())}"
                )
            for k in mwf:
                if abs(mwf[k] - awf[k]) > 1e-9:
                    fail(f"Spec §7.2: ranking_weights[{k}] differs. model={mwf[k]} applied={awf[k]}")

        # 3) narrative_template_id / variant_id (presentation choices)
        for k in ("narrative_template_id", "variant_id"):
            if k in model_out:
                if k not in applied:
                    fail(f"Spec §7.2: model_outputs.{k} present but applied_adjustments.{k} missing")
                if str(model_out.get(k)) != str(applied.get(k)):
                    fail(
                        f"Spec §7.2: applied_adjustments.{k}={applied.get(k)!r} "
                        f"!= model_outputs.{k}={model_out.get(k)!r}"
                    )

        # Provenance consistency (only if provenance.adjustments exists/non-empty)
        if prov_adj:
            for k in ("element_ordering", "ranking_weights", "narrative_template_id", "variant_id"):
                if k in applied and k not in prov_adj:
                    fail(f"Spec §7.2: applied_adjustments.{k} present but provenance.adjustments.{k} missing")

            for k in ("narrative_template_id", "variant_id"):
                if k in applied and str(prov_adj.get(k)) != str(applied.get(k)):
                    fail(f"Spec §7.2: provenance.adjustments.{k} != applied_adjustments.{k}")

            if "element_ordering" in applied:
                pv_ids = [eid for eid in extract_ids_any(prov_adj.get("element_ordering")) if eid in allowed_ids]
                ap_ids = [eid for eid in extract_ids_any(applied.get("element_ordering")) if eid in allowed_ids]
                if pv_ids != ap_ids:
                    fail("Spec §7.2: provenance.adjustments.element_ordering != applied_adjustments.element_ordering")

            if "ranking_weights" in applied:
                pw = prov_adj.get("ranking_weights")
                aw = applied.get("ranking_weights")
                if not isinstance(pw, dict) or not isinstance(aw, dict):
                    fail("Spec §7.2: ranking_weights must be objects in provenance.adjustments and applied_adjustments")
                pwf = _flt_weights(pw, allowed_ids)
                awf = _flt_weights(aw, allowed_ids)
                if pwf != awf:
                    fail("Spec §7.2: provenance.adjustments.ranking_weights != applied_adjustments.ranking_weights")

    elif decision_source in RULE_LIKE_SOURCES:
        # Spec §7.2: rule-based path must not have model outputs or applied adjustments.
        if model_out:
            fail('Spec §7.2: decision_source="rule" requires model_outputs to be empty')
        if applied:
            fail('Spec §7.2: decision_source="rule" requires applied_adjustments to be empty')
    else:
        fail(f"Unexpected decision_source: {decision_source!r} (allowed: {sorted(MODEL_LIKE_SOURCES | RULE_LIKE_SOURCES)})")

    # --- Spec §7.3: ordering and ranking consistency (ordering respected)
    if "element_ordering" in model_out:
        expected_ids = [eid for eid in extract_ids_any(model_out.get("element_ordering")) if eid in allowed_ids]
        if expected_ids:
            out_order = [
                el.get("element_id")
                for el in out_elements
                if isinstance(el, dict) and isinstance(el.get("element_id"), str)
            ]
            assert_order_subsequence(expected_ids, out_order)

    # --- Spec §7.4: model_metadata optional readiness
    model_md = prov.get("model_metadata")
    if model_md is not None:
        model_md = _require_dict(model_md, name="phase4_provenance.model_metadata")
        for k in ("model_id", "model_version", "model_role"):
            if k in model_md and model_md[k] is not None and not isinstance(model_md[k], str):
                fail(f"phase4_provenance.model_metadata.{k} must be a string when present")

        if decision_source in MODEL_LIKE_SOURCES:
            role = model_md.get("model_role")
            if not isinstance(role, str) or not role.strip():
                fail('decision_source is "model/hybrid" but model_metadata.model_role is missing or empty')

    # --- Allowed adjustment keys only
    extra = sorted(set(applied.keys()) - ALLOWED_ADJUSTMENT_KEYS)
    if extra:
        fail(f"applied_adjustments contains disallowed keys: {extra}")


def main() -> int:
    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))
    if not inputs:
        fail("No fixtures found")

    ran = 0
    for p in inputs:
        fx = load_json(p)
        if not is_personalized_fixture(fx):
            continue

        out = run_phase4(fx)
        assert_no_semantic_mutation(fx, out)
        print(f"PASS: {p.name}")
        ran += 1

    if ran == 0:
        fail("No personalized fixtures executed (expected at least one)")

    print("CI PASS: Bounded-safety assertions passed for personalized fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
