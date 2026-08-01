"""rhythm_ingestion shim package

This shim allows code to import using the new package name
`rhythm_ingestion` while the original directory name contains a space
("rhythm ingestion").

Behavior:
- If a sibling directory named "rhythm ingestion" exists, it is prepended
  to this package's __path__ so submodules remain importable.
- This file is intentionally small and non-intrusive; once you delete the
  original "rhythm ingestion" tree you can optionally replace this shim
  with a full copy of the package contents.

Created by automated migration tool.
"""

from __future__ import annotations

import os
from pathlib import Path

# Prepend sibling directory named 'rhythm ingestion' (if present) so
# `import rhythm_ingestion.xxx` resolves to files under the original
# directory until you remove it.
_here = Path(__file__).resolve()
_sibling = _here.parent / "rhythm ingestion"
if _sibling.exists() and _sibling.is_dir():
    # Insert at front so explicit new files (if added later) still take precedence
    __path__.insert(0, str(_sibling))

# Minimal public surface; actual modules live in the sibling folder.
__all__ = ["orchestrator"]
