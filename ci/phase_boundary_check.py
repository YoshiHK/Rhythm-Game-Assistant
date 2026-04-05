"""
Phase Boundary Check

Ensures downstream phases (4–7) do not import or reference upstream analysis phases (1–3).
This enforces semantic immutability.
"""

import sys
from pathlib import Path

FORBIDDEN_IMPORTS = (
    'engine.phase1',
    'engine.phase2',
    'engine.umi',
)

ROOT = Path(__file__).resolve().parents[2]

violations = []
for py in ROOT.rglob('*.py'):
    if 'engine' in py.parts:
        continue
    text = py.read_text(encoding='utf-8', errors='ignore')
    for bad in FORBIDDEN_IMPORTS:
        if bad in text:
            violations.append((py, bad))

if violations:
    for file, bad in violations:
        print(f"Forbidden import {bad} found in {file}")
    sys.exit(1)

print('Phase boundary check passed.')
