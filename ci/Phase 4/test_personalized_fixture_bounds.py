"""Phase 4 CI: Bounded-Safety Assertions (Personalized Fixtures)

Patch intent
------------
This version tightens checks to align with PHASE_4_SPEC.md §7.2 (Explainability Chain):
  decision_source → model_outputs → applied_adjustments → provenance

Key enforcement added (Spec §7.2):
- If decision_source == "model":
  - model_outputs MUST be present (non-empty)
  - applied_adjustments MUST reflect model_outputs (after safety filtering)
  - provenance.adjustments MUST be consistent with applied_adjustments
- If decision_source == "rule":
  - model_outputs MUST be empty
  - applied_adjustments MUST be empty

This is a policy/safety check; it does not judge translation quality.

Run:
  python ci/phase4/test_personalized_fixture_bounds.py
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        fail(f"Failed to parse JSON: {path} ({e})")


def is_personalized_fixture(fx: dict) -> bool:
    return str(fx.get('engine_mode', '')).strip().lower() == 'personalized'


def index_by_element_id(elements: list) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for el in elements:
        if not isinstance(el, dict):
            continue
        eid = el.get('element_id')
        if isinstance(eid, str) and eid:
            out[eid] = el
    return out


def assert_permutation(input_ids: list[str], output_ids: list[str]) -> None:
    if sorted(input_ids) != sorted(output_ids):
        missing = sorted(set(input_ids) - set(output_ids))
        extra = sorted(set(output_ids) - set(input_ids))
        fail(f"elements_view is not a permutation of input elements. Missing={missing} Extra={extra}")


def extract_ids_any(x) -> list[str]:
    """Extract element_id strings from a variety of list-like structures."""
    if x is None:
        return []
    if isinstance(x, list):
        out: list[str] = []
        for item in x:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                eid = item.get('element_id') or item.get('id')
                if isinstance(eid, str):
                    out.append(eid)
            # ints (index-based) are ignored as ambiguous
        return out
    return []


def assert_order_subsequence(expected_ids: list[str], out_order: list[str]) -> None:
    """Require expected_ids to appear as an in-order subsequence within out_order."""
    it = iter(out_order)
    for eid in expected_ids:
        for got in it:
            if got == eid:
                break
        else:
            fail(f"Ordering integrity failed: expected id '{eid}' not found in-order in output order {out_order}")


def run_phase4(fixture: dict) -> dict:
    try:
        from phase4_personalization_runtime import run_phase4_personalization
    except Exception as e:
        fail(f"Unable to import Phase 4 runtime: {e}")

    return run_phase4_personalization(
        canonical_payload=fixture['canonical_payload'],
        canonical_row=fixture['canonical_row'],
        selected_elements=fixture['selected_elements'],
        difficulty=fixture['difficulty'],
        engine_mode='personalized',
        player_id_hash=fixture.get('player_id_hash'),
        locale=fixture.get('locale'),
        feature_flags=fixture.get('feature_flags'),
        opt_in=fixture.get('opt_in'),
    )


def _flt_weights(d: dict, allowed_ids: set[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in d.items():
        if isinstance(k, str) and k in allowed_ids and isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def assert_no_semantic_mutation(fixture: dict, out: dict) -> None:
    # --- inputs/outputs
    inp_elements = fixture.get('selected_elements')
    if not isinstance(inp_elements, list) or not inp_elements:
        fail('Fixture selected_elements missing or empty')

    out_elements = out.get('elements_view')
    if not isinstance(out_elements, list) or not out_elements:
        fail('Output elements_view missing or empty')

    inp_idx = index_by_element_id(inp_elements)
    out_idx = index_by_element_id(out_elements)

    if not inp_idx:
        fail('No element_id found in fixture selected_elements')
    if not out_idx:
        fail('No element_id found in output elements_view')

    assert_permutation(list(inp_idx.keys()), list(out_idx.keys()))

    # --- per-element immutability
    for eid, inp in inp_idx.items():
        out_el = out_idx.get(eid)
        if out_el is None:
            fail(f"Missing element in output: {eid}")
        for field in ('severity_label', 'score', 'training_items', 'matched_tags', 'guidance'):
            if inp.get(field) != out_el.get(field):
                fail(f"{field} changed for {eid}")

    # --- provenance and chain objects
    prov = out.get('phase4_provenance') or {}
    if not isinstance(prov, dict):
        fail('phase4_provenance must be an object')

    gates = prov.get('gates') or {}
    if not isinstance(gates, dict):
        fail('phase4_provenance.gates must be an object')

    if prov.get('engine_mode') != 'personalized':
        fail(f"phase4_provenance.engine_mode must be 'personalized', got {prov.get('engine_mode')}")

    if gates.get('personalization_allowed') is not True:
        fail('phase4_provenance.gates.personalization_allowed must be true for personalized fixture')

    decision_source = prov.get('decision_source')
    if not isinstance(decision_source, str) or not decision_source:
        fail('phase4_provenance.decision_source must be a non-empty string')
    decision_source = decision_source.strip().lower()

    model_out = out.get('model_outputs') or {}
    if not isinstance(model_out, dict):
        fail('model_outputs must be an object')

    applied = out.get('applied_adjustments') or {}
    if not isinstance(applied, dict):
        fail('applied_adjustments must be an object')

    prov_adj = prov.get('adjustments') or {}
    if prov_adj and not isinstance(prov_adj, dict):
        fail('phase4_provenance.adjustments must be an object when present')

    allowed_ids = set(out_idx.keys())

    # --- Spec §7.2: decision_source ↔ model_outputs ↔ applied_adjustments
    if decision_source == 'model':
        if not model_out:
            fail('Spec §7.2: decision_source="model" requires model_outputs to be present (non-empty)')

        # Enforce applied_adjustments reflect model_outputs for known keys.
        # (After safety filtering: we filter to known element_ids and compare.)
        # 1) element_ordering
        if 'element_ordering' in model_out:
            if 'element_ordering' not in applied:
                fail('Spec §7.2: model_outputs.element_ordering present but applied_adjustments.element_ordering missing')
            mo_ids = [eid for eid in extract_ids_any(model_out.get('element_ordering')) if eid in allowed_ids]
            ap_ids = [eid for eid in extract_ids_any(applied.get('element_ordering')) if eid in allowed_ids]
            if mo_ids and ap_ids != mo_ids:
                fail(f"Spec §7.2: applied_adjustments.element_ordering={ap_ids} != filtered model_outputs.element_ordering={mo_ids}")

        # 2) ranking_weights
        if 'ranking_weights' in model_out:
            if 'ranking_weights' not in applied:
                fail('Spec §7.2: model_outputs.ranking_weights present but applied_adjustments.ranking_weights missing')
            mw = model_out.get('ranking_weights')
            aw = applied.get('ranking_weights')
            if not isinstance(mw, dict) or not isinstance(aw, dict):
                fail('ranking_weights must be objects in both model_outputs and applied_adjustments')
            mwf = _flt_weights(mw, allowed_ids)
            awf = _flt_weights(aw, allowed_ids)
            if mwf.keys() != awf.keys():
                fail(f"Spec §7.2: ranking_weights keys differ. model={sorted(mwf.keys())} applied={sorted(awf.keys())}")
            for k in mwf:
                if abs(mwf[k] - awf[k]) > 1e-9:
                    fail(f"Spec §7.2: ranking_weights[{k}] differs. model={mwf[k]} applied={awf[k]}")

        # 3) narrative_template_id / variant_id
        # These are presentation choices, and if model emits them, they must be carried into applied_adjustments.
        for k in ('narrative_template_id', 'variant_id'):
            if k in model_out:
                if k not in applied:
                    fail(f"Spec §7.2: model_outputs.{k} present but applied_adjustments.{k} missing")
                if str(model_out.get(k)) != str(applied.get(k)):
                    fail(f"Spec §7.2: applied_adjustments.{k}={applied.get(k)!r} != model_outputs.{k}={model_out.get(k)!r}")

        # Also require provenance.adjustments to reflect applied_adjustments for those same keys (if provenance has adjustments).
        if isinstance(prov_adj, dict) and prov_adj:
            for k in ('element_ordering', 'ranking_weights', 'narrative_template_id', 'variant_id'):
                if k in applied:
                    if k not in prov_adj:
                        fail(f"Spec §7.2: applied_adjustments.{k} present but provenance.adjustments.{k} missing")

            # template/variant exact match
            for k in ('narrative_template_id', 'variant_id'):
                if k in applied and str(prov_adj.get(k)) != str(applied.get(k)):
                    fail(f"Spec §7.2: provenance.adjustments.{k} != applied_adjustments.{k}")

            # ordering match (after filtering)
            if 'element_ordering' in applied:
                pv_ids = [eid for eid in extract_ids_any(prov_adj.get('element_ordering')) if eid in allowed_ids]
                ap_ids = [eid for eid in extract_ids_any(applied.get('element_ordering')) if eid in allowed_ids]
                if pv_ids != ap_ids:
                    fail('Spec §7.2: provenance.adjustments.element_ordering != applied_adjustments.element_ordering')

            # weights match
            if 'ranking_weights' in applied:
                pw = prov_adj.get('ranking_weights')
                aw = applied.get('ranking_weights')
                if not isinstance(pw, dict) or not isinstance(aw, dict):
                    fail('Spec §7.2: ranking_weights must be objects in provenance.adjustments and applied_adjustments')
                pwf = _flt_weights(pw, allowed_ids)
                awf = _flt_weights(aw, allowed_ids)
                if pwf != awf:
                    fail('Spec §7.2: provenance.adjustments.ranking_weights != applied_adjustments.ranking_weights')

    elif decision_source == 'rule':
        # Spec §7.2: rule-based path must not have model outputs or applied adjustments.
        if model_out:
            fail('Spec §7.2: decision_source="rule" requires model_outputs to be empty')
        if applied:
            fail('Spec §7.2: decision_source="rule" requires applied_adjustments to be empty')
    else:
        fail(f"Unexpected decision_source: {decision_source!r}")

    # --- Spec §7.3: ordering and ranking consistency (ordering respected)
    if 'element_ordering' in model_out:
        expected_ids = [eid for eid in extract_ids_any(model_out.get('element_ordering')) if eid in allowed_ids]
        if expected_ids:
            out_order = [el.get('element_id') for el in out_elements if isinstance(el, dict) and isinstance(el.get('element_id'), str)]
            assert_order_subsequence(expected_ids, out_order)

    # --- Spec §7.4: model_metadata optional readiness
    model_md = prov.get('model_metadata')
    if model_md is not None:
        if not isinstance(model_md, dict):
            fail('phase4_provenance.model_metadata must be an object when present')
        for k in ('model_id', 'model_version', 'model_role'):
            if k in model_md and model_md[k] is not None and not isinstance(model_md[k], str):
                fail(f"phase4_provenance.model_metadata.{k} must be a string when present")
        if decision_source == 'model':
            role = model_md.get('model_role')
            if not isinstance(role, str) or not role.strip():
                fail('decision_source is "model" but model_metadata.model_role is missing or empty')

    # --- Allowed adjustment keys only
    allowed_adj_keys = {'element_ordering', 'ranking_weights', 'narrative_template_id', 'variant_id'}
    extra = sorted(set(applied.keys()) - allowed_adj_keys)
    if extra:
        fail(f"applied_adjustments contains disallowed keys: {extra}")


def main() -> int:
    inputs = sorted(FIXTURES_DIR.glob('fixture_*_input.json'))
    if not inputs:
        fail('No fixtures found')

    ran = 0
    for p in inputs:
        fx = load_json(p)
        if not isinstance(fx, dict):
            fail(f"Fixture must be an object: {p}")
        if not is_personalized_fixture(fx):
            continue

        out = run_phase4(fx)
        if not isinstance(out, dict):
            fail('Phase 4 runtime must return an object')

        assert_no_semantic_mutation(fx, out)
        print(f"PASS: {p.name}")
        ran += 1

    if ran == 0:
        fail('No personalized fixtures executed (expected at least one)')

    print('CI PASS: Bounded-safety assertions passed for personalized fixtures')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
