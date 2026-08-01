# rhythm_ingestion migration shim

This directory contains a small shim package that makes the new
package name `rhythm_ingestion` resolve to the existing directory
named `rhythm ingestion` (space in the name).

Purpose
- Allow repository-wide imports and tooling to start using
  `rhythm_ingestion` immediately.
- Preserve runtime behavior while you manually remove the original
  `rhythm ingestion` folder when ready.

Next steps
- Once you have deleted the original `rhythm ingestion` folder,
  replace this shim with a real copy of the package contents (if
  desired) or keep a lightweight shim that points to the final layout.
