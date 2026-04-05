"""
No Runtime Analysis Check

Ensures that runtime-facing layers (API, personalization, localization,
production, discovery) do NOT trigger Phase 1–3 analysis or ingestion.

Invariant enforced:
- Players never trigger analysis
- Phase 1–3 are offline-only
"""

import sys
from pathlib import Path

FORBIDDEN_CALLS = (
    'orchestrator.run',
    'orchestrator.ingest',
    'UMI',
    'run_batch',
)

ROOT = Path(__file__).resolve().parents[2]

violations = []
for py in ROOT.rglob('*.py'):
    # runtime layers only
    if 'engine' in py.parts:
        continue
    text = py.read_text(encoding='utf-8', errors='ignore')
    for bad in FORBIDDEN_CALLS:
        if bad in text:
            violations.append((py, bad))

if violations:
    for file, bad in violations:
        print(f"Runtime analysis trigger '{bad}' found in {file}")
    sys.exit(1)

print('No runtime analysis violations found.')
