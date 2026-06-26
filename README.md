# 🎮 Rhythm Game Assistant (RGA)

A deterministic, multi‑phase recommendation platform for rhythm game players.

---

## 🚀 What is RGA?

Rhythm Game Assistant (RGA) helps players improve by generating:

- 🎯 Song‑level recommendations  
- 🎤 Actionable gameplay tips  
- 🧠 Personalized advice  
- 🌍 Localized outputs across languages  
- 🎮 Game discovery across multiple rhythm games  

All through a single unified API.

---

## ⚡ How it works (User view)

Choose a game → Pick a song → Tap “Get Mascot Tip” → Receive clear, personalized advice

RGA handles everything behind the scenes — from analysis to personalization to localization — and returns a concise, explainable result.

---

## 🧠 Core Capabilities

### 🎯 Recommendation Layer
- Song recommendations (runtime)
- Game discovery (multi-game support)
- Structured tips with explanations

### 🧠 Intelligence Layer
- Multi-vector personalization (Phase 4)
- Multi-vector localization (Phase 4.5)
- Offline learning loop (Phase 5)

### 🎮 Platform Layer
- Multi-game support via centralized registry (`games.json`)
- Capability-based feature enablement per game
- Deterministic execution pipeline

### 🔐 API Layer
- Single entrypoint: `POST /api/v1/recommend`
- Secure request boundary (auth + traceability)
- Stable contract (no runtime version switching)

### 📊 Operations & Governance
- CI-driven validation across phases
- Structured observability (CI SUMMARY signals)
- Phase-isolated execution model

---

## 🏗 System Architecture

RGA is a **multi-phase system**, not a monolithic API:

```
Client / UI
  ↓
Phase 6 API (runtime gate)
  ↓
OrchestratorBridge
  ↓
Phase 3 → Phase 1–2 → Phase 4 → Phase 4.5
  ↓
Response (tips / recommendations)
```

### Key rule:
> ✅ Phase 6 is the ONLY runtime entrypoint  
> ✅ All logic flows through controlled phase boundaries  

---

## 🔍 API vs System (Important)

### ✅ API (Phase 6)
- Handles authentication, routing, and response shaping
- Does NOT implement recommendation logic

### ✅ System (Phases 1–7)
- Executes analysis, personalization, localization, and ranking
- Enforces deterministic, explainable behavior

👉 The API orchestrates the system — it does not replace it.

---

## ⚖️ Core Guarantees

- ✅ Deterministic outputs  
  *(same input → same result)*  

- ✅ Strict phase isolation  
  *(no cross-layer logic leakage)*  

- ✅ Explainable recommendations  
  *(no black-box responses)*  

- ✅ Multi-game scalability  
  *(add new games without rewriting pipeline)*  

- ✅ Observability-driven governance  
  *(CI + structured telemetry)*  

---

## 🎮 Multi‑Game Support

RGA supports multiple rhythm games via a centralized registry:

games.json

Each game defines:

- capability enablement
- recommendation availability
- learning readiness

👉 Adding a new game is configuration-driven, not architecture-breaking.

---

## 🔁 Learning & Automation

RGA includes an **offline learning loop** (Phase 5):

- feedback collection  
- evaluation & retraining  
- artifact generation  

### Important:

> ❗ Learning does NOT occur at runtime  
> ✅ Runtime behavior remains deterministic  

---

## 📡 Integration

RGA is designed to connect to external apps:

- Softr / no-code platforms  
- mobile or web apps  
- partner integrations  

All integrations use:

POST /api/v1/recommend

as the single stable interface.

---

## 🚫 Design Philosophy

RGA intentionally avoids:

- ❌ runtime randomness  
- ❌ hidden model behavior  
- ❌ cross-phase logic mixing  
- ❌ versioned API branching  

Instead, it enforces:

> ✅ clarity, stability, and long-term maintainability

---

## 📂 Documentation

- `ARCHITECTURE.md` → phase model & design rules  
- `SPEC.md` → API contract  
- `USAGE.md` → integration patterns  
- `PLATFORM_OVERVIEW.md` → runtime responsibilities  
- `LIMITATIONS.md` → system invariants  
- `MANIFEST.md` → source-of-truth artifacts  
- `ARCHITECTURE_CLOSEOUT.md` → sealed guarantees  

---

## 🧠 What makes RGA different?

RGA is not:

just another recommendation API

It is:

> 🔥 A deterministic, phase‑governed, observable recommendation platform

---

## 🏁 Status

✅ Architecture sealed  
✅ API production-ready  
✅ CI governance complete  
✅ Multi-phase system operational  

---

## 🚀 Future Direction

- Add more rhythm games (primary scaling path)  
- Improve ranking / personalization models  
- Expand observability & analytics  

---

## 📣 Final Note

RGA is designed as a system that can:

- evolve without breaking  
- scale without rewriting  
- and remain explainable at every step  

---

## Status Badges

[![CodeQL Advanced](https://github.com/YoshiHK/Rhythm-Game-Assistant/actions/workflows/codeql.yml/badge.svg)](https://github.com/YoshiHK/Rhythm-Game-Assistant/actions/workflows/codeql.yml)

[![Deployment Gate](https://github.com/YoshiHK/Rhythm-Game-Assistant/actions/workflows/deployment-gate.yml/badge.svg)](https://github.com/YoshiHK/Rhythm-Game-Assistant/actions/workflows/deployment-gate.yml)

---

**End of README**
