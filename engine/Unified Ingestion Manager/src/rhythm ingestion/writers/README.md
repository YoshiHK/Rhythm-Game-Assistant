# writers Layer (Unified Ingestion Writer Architecture)

## Overview

The `writers` layer forms the **core ingestion and asset processing system**
for the Rhythm Game Assistant pipeline.

It is responsible for:

- Chart asset ingestion (files, web exports, references)
- Identity normalization (game / difficulty / level)
- Chart conversion into deterministic representations
- Database persistence (scan inventory, chart assets, patterns)
- Pipeline orchestration and wiring across ingestion stages

---

## System Pipeline Overview

The ingestion and processing pipeline now consists of multiple layers:

file scan → inventory → asset → pattern → blob → verification → safety

- **file scan (inventory)**  
  captures all discovered files into file_scan_inventory.db

- **asset layer**  
  classifies and converts files into chart_assets.db

- **pattern layer**  
  extracts structural features and stores them in chart_patterns.db

- **blob layer**  
  stores derived feature blobs for visualization / downstream usage

- **verification layer**  
  ensures system-wide correctness before any destructive operation

- **safety layer (safe delete)**  
  allows pruning only when full verification passes
  
---

## Layer Structure

The writers layer is organized into **9 sub-layers**, each with strict responsibilities:

```
writers/
├── models/
├── normalizers/
├── converters/
├── classifiers/
├── validators/
├── persistence/
├── readers/
├── bridges/
├── orchestrators/
```

---

## Sub-layer Responsibilities

### models/
Data structures and schema definitions  
- ChartAsset  
- AssetType / AssetSubtype  

✅ Pure data only  
❌ No logic / no DB / no conversion  

---

### normalizers/
Canonical identity mapping  
- game normalization  
- difficulty normalization  
- level parsing  

✅ raw → canonical  
❌ no persistence  

---

### converters/
Asset conversion layer  
- file → deterministic text (type_A)
- web → cleaned text
- helper hashing

✅ deterministic transformation  
❌ no DB writes  

---

### classifiers/
Asset classification layer  
- type_A (structured assets)
- type_B (reference assets: video / URL)

✅ routing decision  
❌ no conversion / no DB  

---

### validators/
Validation layer  
- candidate validation
- asset validation

✅ ensures DB integrity  
✅ returns warnings vs fatal errors  

---

### persistence/
All database / file writing  
- chart_assets.db  
- file_scan_inventory.db  
- chart_patterns.db  

✅ ONLY layer allowed to write data  

---

### readers/
Read-only data access  
- chart pattern lookup  

✅ DB → dict  
❌ no mutation  

---

### bridges/
Pipeline wiring layer  
- chart_feature_bridge  
- feedback_event_adapter  
- song_identity_resolver  

✅ Glue logic  
❌ no DB / no conversion  

---

### orchestrators/
End-to-end ingestion control  
- scan → classify → normalize → validate → convert → persist  

✅ single entry point for ingestion  

---

## Asset Model

Charts are represented as:

### type_A (deterministic assets)
- `.aff`, `.sus`, `.json`
- `.html`, `.mht`
- stored as `text_representation`

### type_B (reference assets)
- video clips
- YouTube links
- external pages

Stored as:
- `reference_url`
- derived analysis happens later

---

## Pipeline Flow

```
File Scan / Input
↓
Classifier
↓
Normalizer
↓
Validator (candidate-level)
↓
Converter (type_A only)
↓
Asset Builder
↓
Validator (asset-level)
↓
Persistence
↓
chart_assets.db
```

---

## Design Principles

### 1. Separation of Concerns

Each layer does only ONE thing.

```
No cross-layer logic leakage
```

---

### 2. Determinism
type_A assets must be:
- reproducible
- hashable (SHA-256)

---

### 3. Non-destructive Ingestion
- normalization issues are warnings
- ingestion should proceed whenever safe

---

### 4. Asset Abstraction
Charts are not just files:

```
chart = asset representation (text OR reference)
```

---

### 5. Phase Isolation

Writers layer must NOT:
- modify Phase 1–2 logic
- store personalization outputs
- store localization outputs
- store rendered tips

---

## Verification (System-Level)

Verification is a global safety check, not per-item validation.

The system uses a **full bundle verification** before destructive operations:

- verify_file_scan_inventory
- verify_inventory_asset_coverage
- verify_asset_bundle
- verify_pattern_bundle

These are aggregated into:

verify_full_bundle

Deletion is only allowed if:

full_bundle.summary.all_ok == True

---

## Safe Delete (Quarantine-Based Pruning)

Chart files are never deleted directly.

The system provides a **safe delete mechanism**:

- requires full bundle verification to pass
- operates in dry-run by default
- moves files to quarantine (reversible)
- preserves at least one copy per duplicate group

Usage flow:

1. generate candidate list
2. run safe_delete_candidates
3. verify plan
4. optionally execute quarantine

This ensures no data loss even under incorrect configurations.

---

## External Data (Non-Authoritative)

song_info.sqlite is used for metadata enrichment only.

It is NOT part of:
- verification
- deletion safety
- system-of-record

This prevents external / manual data from affecting correctness guarantees.


---

## Current Scope

✅ Implemented:

### Ingestion / Asset Layer
- chart asset ingestion
- deterministic text conversion (multi-format: aff / sus / json / html / mht / txt)
- asset classification (type_A / type_B)
- SQLite persistence (chart_assets.db)

### Inventory Layer
- file scan tracking (file_scan_inventory.db)
- normalized identity + hierarchy extraction
- scan coverage management

### Pattern Layer
- chart pattern extraction bridge
- feature persistence (chart_patterns.db)
- optional blob layer (feature-based, deterministic)

### Verification Layer
- system-level verification (inventory → asset → pattern)
- cross-layer coverage checks
- deterministic integrity checks

### Safety Layer
- policy-driven safe delete (quarantine-based)
- full bundle verification gate before delete
- dry-run + reversible operations

---

❗ Not included (future analysis layers):

Note:
Reference assets (type_B) are supported for ingestion and persistence,
but do not currently participate in structured chart analysis.

Planned future capabilities include:

- video → pseudo-chart structure extraction
- OCR / screenshot parsing
- advanced gameplay-level deduplication

This ensures that non-deterministic assets do not affect verification,
pattern extraction, or deletion safety.

---

## Recommended Usage

### Full ingestion

```
from writers import ingest_chart_assets

result = ingest_chart_assets(candidates=my_candidates)
```

---

## Fine-grained usage

```
from writers.classifiers import classify_chart_asset_candidate
from writers.validators import validate_chart_asset_candidate
from writers.persistence import persist_chart_assets
```

---

## Notes

- chart_assets.db is the canonical asset storage layer
- file_scan_inventory.db tracks discovery
- chart_patterns.db stores derived features

All runtime DBs should live under:

```
runtime/
```

---

## Final Remarks

This layer is designed as a scalable ingestion framework, not just a set of utilities.

It supports:

- multi-game expansion
- multi-format ingestion
- video-based chart analysis
- safe removal of large raw chart datasets

Note:
All verification and deletion logic operate only on system-generated, deterministic data.
External metadata sources (e.g. song_info.sqlite) are treated as non-authoritative.