"""
ordering_contract_check.py
Phase 4 CI — Ordering Contract Check (Design-Locked)

Purpose:
- Enforce ordering invariants for Phase 4 personalization
- Validate ordering behavior for rule vs model decision paths

Scope:
- Fast structural + contract-level validation
- Does NOT evaluate personalization quality

Spec alignment:
- PHASE_4_SPEC §7.3 Ordering Consistency
"""

from typing import Any, Dict, List


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def _extract_ids(elements: List[Dict[str, Any]]) -> List[str]:
    out = []
    for el in elements:
        if isinstance(el, dict):
            eid = el.get("element_id")
            if isinstance(eid, str) and eid:
                out.append(eid)
    return out


def run_ordering_contract_check(
    *,
    base_elements: List[Dict[str, Any]],
    personalized_elements: List[Dict[str, Any]],
    decision_source: str,
    model_outputs: Dict[str, Any],
) -> None:

    base_ids = _extract_ids(base_elements)
    out_ids = _extract_ids(personalized_elements)

    if not base_ids or not out_ids:
        fail("Ordering check: missing element ids")

    # ✅ RULE PATH (strict)
    if decision_source == "rule":
        if base_ids != out_ids:
            fail(
                "Ordering Contract FAIL: rule-based path must preserve exact ordering"
            )

    # ✅ MODEL / HYBRID PATH
    elif decision_source in ("model", "hybrid"):

        mo_order = model_outputs.get("element_ordering")

        if isinstance(mo_order, list) and mo_order:
            expected = [eid for eid in mo_order if isinstance(eid, str)]

            # enforce subsequence
            it = iter(out_ids)
            for eid in expected:
                for got in it:
                    if got == eid:
                        break
                else:
                    fail(
                        f"Ordering Contract FAIL: model ordering not preserved for element '{eid}'"
                    )

    else:
        fail(f"Unknown decision_source: {decision_source}")