"""
No Chart Data Check

Ensures that no raw chart data or ingestion inputs
are committed into the source repository.

Invariant enforced:
- Charts are internal, ephemeral analytical inputs
- GitHub stores code and specs only
"""

import sys
from pathlib import Path

FORBIDDEN_PATTERNS = (
    'Chart File',
    '.svg',
    '.html',
    'raw_charts',
    'charts/',
)

ROOT = Path(__file__).resolve().parents[2]

violations = []
for path in ROOT.rglob('*'):
    name = str(path)
    for bad in FORBIDDEN_PATTERNS:
        if bad in name:
            violations.append(name)

if violations:
    print('Forbidden chart data detected in repository:')
    for v in violations:
        print(f' - {v}')
    sys.exit(1)

print('No chart data detected in repository.')
