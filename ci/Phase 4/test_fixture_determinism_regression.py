"""Phase 4 CI: Fixture-based Determinism Regression

This test provides *golden fixture* determinism regression for Phase 4.

Fixtures live in:
  ci/phase4/fixtures/

Fixture naming:
  - fixture_<name>_input.json
  - fixture_<name>_expected.sha256

What it validates
-----------------
1) Deterministic stability within a single run (each fixture executed twice; hashes must match)
2) Regression against recorded golden hashes (after scrubbing volatile timestamp-like fields)

Update goldens
--------------
  python ci/phase4/test_fixture_determinism_regression.py --update

This writes/overwrites:
  - fixture_<name>_expected.sha256
  - fixture_<name>_sanitized_output.json

Notes
-----
- Structural/policy regression only; does not judge personalization quality.
- Designed to detect accidental behavioral drift in Phase 4 runtime wiring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / 'fixtures'

VOLATILE_KEY_TOKENS = (
    'timestamp',
    'time',
    'datetime',
    'decision_timestamp',
    'event_timestamp',
)


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        fail(f"Failed to parse JSON: {path} ({e})")


def is_volatile_key(k: str) -> bool:
    kl = k.lower()
    return any(tok in kl for tok in VOLATILE_KEY_TOKENS)


def scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and is_volatile_key(k):
                continue
            out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    return obj


def canonical_dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def run_fixture(fixture: dict):
    try:
        from phase4_personalization_runtime import run_phase4_personalization, Phase4RuntimeConfig
    except Exception as e:
        fail(f"Unable to import Phase 4 runtime: {e}")

    cfg_obj = None
    cfg = fixture.get('cfg')
    if isinstance(cfg, dict):
        cfg_obj = Phase4RuntimeConfig(**cfg)  # type: ignore[arg-type]

    out = run_phase4_personalization(
        canonical_payload=fixture['canonical_payload'],
        canonical_row=fixture['canonical_row'],
        selected_elements=fixture['selected_elements'],
        difficulty=fixture['difficulty'],
        engine_mode=fixture.get('engine_mode', 'deterministic'),
        player_id_hash=fixture.get('player_id_hash'),
        locale=fixture.get('locale'),
        feature_flags=fixture.get('feature_flags'),
        opt_in=fixture.get('opt_in'),
        cfg=cfg_obj or Phase4RuntimeConfig(),
    )

    stable = {
        'case_id': fixture.get('case_id', ''),
        'engine_mode': (fixture.get('engine_mode') or '').strip().lower(),
        'tips_text': out.get('tips_text', ''),
        'elements_view': out.get('elements_view', []),
        'narrative_metadata': out.get('narrative_metadata', {}),
        'phase4_provenance': out.get('phase4_provenance', {}),
        'model_outputs': out.get('model_outputs', {}),
        'applied_adjustments': out.get('applied_adjustments', {}),
        'gate_fail_reasons': out.get('gate_fail_reasons', []),
    }

    sanitized = scrub(stable)
    digest = sha256_text(canonical_dumps(sanitized))
    return digest, sanitized


def iter_fixture_inputs():
    if not FIXTURES_DIR.exists():
        fail(f"Missing fixtures dir: {FIXTURES_DIR}")
    inputs = sorted(FIXTURES_DIR.glob('fixture_*_input.json'))
    if not inputs:
        fail('No fixture_*_input.json files found')
    return inputs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', action='store_true', help='Regenerate expected hashes and snapshots')
    args = ap.parse_args()

    for input_path in iter_fixture_inputs():
        fixture = load_json(input_path)
        if not isinstance(fixture, dict):
            fail(f"Fixture must be an object: {input_path}")

        name = input_path.name.replace('_input.json', '')
        expected_path = FIXTURES_DIR / f"{name}_expected.sha256"
        snapshot_path = FIXTURES_DIR / f"{name}_sanitized_output.json"

        d1, s1 = run_fixture(fixture)
        d2, s2 = run_fixture(fixture)
        if d1 != d2:
            snapshot_path.write_text(json.dumps(s1, indent=2, ensure_ascii=False), encoding='utf-8')
            fail(f"Non-deterministic output for {name}: hash differs across repeated runs")

        if args.update:
            expected_path.write_text(d1 + '\n', encoding='utf-8')
            snapshot_path.write_text(json.dumps(s1, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"UPDATED: {expected_path.name}")
            continue

        if not expected_path.exists():
            fail(f"Missing expected hash: {expected_path} (run with --update)")

        expected = expected_path.read_text(encoding='utf-8').strip().splitlines()[0].strip()
        if not expected or expected.startswith('PLEASE_'):
            fail(f"Expected hash not generated for {name}. Run --update and commit outputs.")

        if d1 != expected:
            snapshot_path.write_text(json.dumps(s1, indent=2, ensure_ascii=False), encoding='utf-8')
            fail(f"Regression detected for {name}: output hash differs from expected")

        print(f"PASS: {name}")

    print('CI PASS: All Phase 4 fixture determinism regressions passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
