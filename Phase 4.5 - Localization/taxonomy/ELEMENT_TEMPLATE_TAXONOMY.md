## Element Template Taxonomy

---

# 1. Positioning

This taxonomy defines the **complete set of allowable element-level narrative template families**  
used by Phase 4.5 Localization.

✅ It is a **presentation-layer contract**  
❌ It is NOT a detection or inference specification

---

# 2. Non-Negotiable Boundary

This taxonomy MUST NOT:

- define or modify pattern detection logic (Phase 1)
- define or modify element inference logic (Phase 2)
- introduce new semantic meaning
- alter severity, scores, or selection outcomes

✅ This taxonomy ONLY defines how elements are expressed in language

---

# 3. Design Principles

### ✅ Non-semantic
Templates describe *observations*, not decisions.

### ✅ Cross-game generalization
Must work across rhythm games (engine-agnostic).

### ✅ Family-based grouping
Templates are grouped into stable narrative families.

### ✅ Learning-safe
Phase 5 may select templates, but MUST NOT modify taxonomy.

---

# 4. Canonical Element Template Families

---

## 4.1 Density & Load
- element_density

Describes:
- sustained density
- recovery window compression
- local vs continuous load

---

## 4.2 Timing & Rhythm
- element_rhythm
- element_timing_variation

Describes:
- irregular timing
- off-beat emphasis
- timing shifts / BPM variation

---

## 4.3 Precision
- element_precision

Describes:
- tight spacing
- small input tolerance
- micro-timing requirements

---

## 4.4 Movement & Spatial Reach
- element_movement

Describes:
- lateral movement
- jump distance
- cross-screen transitions

---

## 4.5 Pattern Complexity (Cognitive Load)
- element_pattern_complexity

Describes:
- mixed pattern types
- hybrid interaction
- pattern switching complexity

---

## 4.6 Directional Inputs
- element_flick

Describes:
- directional control changes
- repeated directional inputs
- direction switching

---

## 4.7 Sustained Inputs
- element_hold
- element_slide

Describes:
- input occupation over time
- path tracking
- overlapping responsibilities

---

## 4.8 Alternating Patterns
- element_trill

Describes:
- alternating sequences
- coordination stability
- repetitive timing consistency

---

## 4.9 Visibility & Readability
- element_visibility

Describes:
- visual clutter
- overlapping notes
- low readability situations

---

## 4.10 Multi-Input Coordination
- element_chord
- element_coordination

Describes:
- simultaneous inputs
- multi-lane coordination
- synchronization demands

---

## 4.11 Spatial Conflict & Hand Distribution
- element_cross_hand

Describes:
- hand crossing
- spatial conflict
- hand-switching burden

---

## 4.12 Flow & Directionality
- element_flow_direction

Describes:
- directional flow changes
- zig-zag / rotational motion
- path readability

---

# 5. Mapping to Detection Layer

Each family aggregates one or more detection-level tags.

Example:

- element_flick  
  ← directional_flick, trace_flick, alternating_flick

- element_trill  
  ← trill_vertical, trill_alternating, trill_hybrid

❌ Mapping MUST NOT be defined or modified here.

---

# 6. Template Contract

Each template file MUST:

- map to exactly one taxonomy family
- use stable template_id
- preserve semantic neutrality
- support multiple variants

---

# 7. Learning Boundary

Phase 5 MAY:
- select template_id
- select variant

Phase 5 MUST NOT:
- modify template text
- redefine taxonomy
- merge or split families

---

# 8. Alignment with Localization System

This taxonomy guarantees:

✅ Full compatibility with:
- template_registry.json
- locale-based template packs
- CI validation (pack integrity, parity)

✅ Deterministic mapping:
- every template exists in all locales
- no implicit or hidden categories

---

# ✅ Final Rule

> 🔒 If a category is not in this taxonomy, it MUST NOT exist in localization.

---

# ✅ Summary

The Element Template Taxonomy ensures:

✅ stable narrative structure  
✅ cross-game compatibility  
✅ CI-enforced consistency  
✅ strict separation from gameplay logic  

It is a core contract of Phase 4.5 Localization.