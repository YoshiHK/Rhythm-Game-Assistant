# Catalog Layer (Song Recommendation)

## Purpose

The catalog layer provides a **read‑only, deterministic view** of song and
difficulty artifacts used by the Song Recommendation system.

It is responsible for:
- Loading canonical song metadata
- Exposing difficulty availability per song
- Supporting deterministic selection and window‑widening

This layer MUST NOT:
- Perform gameplay analysis
- Interpret difficulty semantics
- Apply personalization or ranking logic
- Mutate state or persist data

All semantic interpretation (difficulty meaning, skill modeling, etc.)
belongs to downstream phases.

## Design Principles

- Read‑only and side‑effect free
- Deterministic given the same inputs
- Game‑agnostic (no Proseka‑style assumptions)
- Driven entirely by resolved game capability ordering

## Key Modules

- `catalog_loader.py`  
  Loads canonical song and difficulty artifacts.

- `song_catalog.py`  
  In‑memory representation of the catalog.

- `catalog_selector.py`  
  Deterministic selection logic using ordered difficulty tiers.