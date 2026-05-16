# Chart Template Taxonomy

## Positioning

This taxonomy defines the **set of allowable chart-level narrative template families**.

Chart-level templates represent the **global narrative compression layer**:
they summarize the overall structure and characteristics of a chart
without exposing individual pattern details.

---

## Non-Negotiable Boundary

This taxonomy MUST NOT:

- duplicate element-level descriptions
- introduce new semantic interpretation
- re-evaluate difficulty, severity, or scores
- describe specific patterns or techniques

Chart-level templates ONLY:

> summarize high-level chart characteristics.

---

## Design Principles

1. Compression Layer  
   Chart-level templates reduce multiple elements into a coherent summary.

2. Low Dimensionality  
   The number of families MUST remain small and stable.

3. Cross-game Generalization  
   Templates MUST work across different rhythm game mechanics.

4. Non-overlap with Element-Level  
   Chart-level MUST NOT restate element-level details.

---

## Taxonomy (Chart Template Families)

### 1. Difficulty Overview

- difficulty_overview  

Describes:
- overall difficulty impression
- combined effect of multiple elements

---

### 2. Summary

- chart_summary  

Describes:
- final narrative conclusion
- holistic chart identity

---

### 3. Endurance Profile

- endurance_profile  

Describes:
- duration-related pressure
- sustained load across time

---

### 4. Density Profile

- density_profile  

Describes:
- density distribution across the chart
- continuous vs sparse flow

---

### 5. Structure Profile

- structure_profile  

Describes:
- structural progression
- burst placement, climax distribution

---

## Mapping to Lower Layers

Chart-level templates aggregate:

- element-level signals (Phase 2 output)
- section-level patterns (temporal structure)

Example:

- high element_density + stream  
  → density_profile (high_density)

- repeated burst_section  
  → structure_profile (burst_pattern)

---

## Template Contract

Each chart-level template MUST:

- correspond to a single taxonomy family
- be non-redundant with other chart templates
- maintain semantic neutrality
- support multiple variants

---

## Learning Boundary

Phase 5 learning MAY:

- select chart template types
- select variants

Phase 5 learning MUST NOT:

- derive new chart-level categories
- override element-level meaning

---

## Summary

Chart-level taxonomy defines a **stable compression layer**
that connects element-level signals to user-facing narrative summaries,
while preserving cross-game compatibility.