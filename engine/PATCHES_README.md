# patches/README.md

## Phase 2 Note

> **Phase 2 patch conventions and inventory are documented in `PATCHES_README_v2.md`.**

> This file describes Phase 1 baseline patches only.

## Patch Artifacts – Project SEKAI Tips Generation

This directory contains **version-control patches**, not runtime code.


### Included Patch
- `proseka_tips_pipeline_runner_default_adapters.patch`

### Purpose
This patch updates the pipeline runner so that it **defaults to production-wired adapters** instead of requiring manual injection.

### Usage
Apply using Git:
```
git apply proseka_tips_pipeline_runner_default_adapters.patch
```

### Notes
- Do NOT import patch files in Python code.
- Patches exist only to migrate older checkouts to the finalized Phase 1 architecture.

END
