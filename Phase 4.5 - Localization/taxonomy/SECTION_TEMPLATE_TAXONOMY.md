# Section Template Taxonomy

## Positioning

This taxonomy defines the **set of allowable section-level narrative template families**.

Section-level templates describe **temporal segments within a chart**,
capturing how difficulty and structure evolve over time.

---

## Non-Negotiable Boundary

This taxonomy MUST NOT:

- define pattern detection logic
- introduce element-level semantics
- overlap with chart-level summaries
- describe specific input techniques

Section-level templates ONLY:

> describe time-based structural behavior.

---

## Design Principles

1. Temporal Focus  
   Templates reflect how the chart evolves across time.

2. Game-Agnostic  
   No reliance on specific UI (lanes, arcs, touch zones).

3. Structural Role  
   Section templates describe *where* and *how* pressure occurs.

4. Minimal Basis  
   Only essential temporal structures should exist.

---

## Taxonomy (Section Template Families)

### 1. Burst Sections

- burst_section  

Describes:
- short-lived spikes in intensity
- concentrated difficulty

---

### 2. Climax Sections

- climax_section  

Describes:
- peak difficulty segments
- dominant or defining sections

---

### 3. Opening Profile

- opening_profile  

Describes:
- how the chart begins
- initial pacing and difficulty introduction

---

### 4. Ending Profile

- ending_profile  

Describes:
- how the chart concludes
- final spikes, fake endings, or tapering

---

## Mapping to Lower Layers

Section-level templates aggregate:

- local element intensity
- density changes
- structural transitions

Example:

- sudden increase in density  
  → burst_section

- highest sustained pressure  
  → climax_section

---

## Relationship to Chart-Level

Section-level templates feed into chart-level summaries:

- burst_section patterns  
  → structure_profile

- opening_profile  
  → influences difficulty pacing

- ending_profile  
  → influences final chart impression

---

## Template Contract

Each section-level template MUST:

- represent a temporal characteristic
- avoid duplication with element-level
- support multiple variants
- remain semantically neutral

---

## Learning Boundary

Phase 5 learning MAY:

- select which section templates apply
- select variant phrasing

Phase 5 learning MUST NOT:

- create new temporal categories
- reinterpret structure

---

## Summary

Section-level taxonomy defines the **temporal structure layer**
bridging element-level details and chart-level summaries,
enabling consistent multi-game narrative generation.