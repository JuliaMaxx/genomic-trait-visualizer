# whoami – Genomic Exploration Platform for Explainable Trait Analysis

## 🎯 Goal

Build an **interactive, explainable genomic exploration system** that allows users to:

- Upload DNA data
- Understand trait predictions
- Explore variant → genotype → trait relationships
- Learn through interaction and experimentation

# 🧱 Phase 1 – Solidify Core Pipeline (You are here)

## Goal

Make your current system **clean, reliable, and extensible**.

## Tasks

- [ ] Clean DNA upload flow (single entry point)
- [ ] Standardize parsed data structure
  - Variant: `{ rsid, genotype, chromosome, position }`

- [ ] Ensure traits are derived from a clear mapping
  - Trait → list of rsIDs → interpretation logic

- [ ] Refactor code into layers:
  - parser
  - trait service
  - API layer

## Output

- Stable upload → parse → traits flow
- Clean data model (VERY important for later phases)
- Unlocks: reliable data flow from DNA file → structured variants → basic trait results

---

# 🔍 Phase 2 – Trait Drill-Down (Core Exploration Feature)

## Goal

Turn traits into **interactive exploration entry points**.

## Tasks

- [ ] Make each trait clickable
- [ ] Create Trait Detail Page:
  - Trait name
  - User result (e.g. "Likely lactose tolerant")
  - List of contributing rsIDs

- [ ] For each rsID show:
  - User genotype
  - Meaning of genotype

- [ ] Add explanation sections:
  - Simple explanation
  - Technical explanation (optional toggle)

## Output

- Trait → rsID → genotype → meaning flow
- Unlocks: ability to trace trait → rsID → genotype → meaning (core explainability)

---

# 🔎 Phase 3 – Global Search

## Goal

Enable **free exploration** across the system.

## Tasks

- [ ] Add search input (top-level UI)
- [ ] Implement search over:
  - traits
  - rsIDs
  - keyword (“eye color”, “caffeine”)

- [ ] Display results grouped by type
- [ ] Link results to:
  - Trait page
  - rsID page (next phase)

## Output

- Users can explore without predefined navigation
- Unlocks: free navigation across traits and variants without fixed UI paths

---

# 🧬 Phase 4 – rsID Knowledge Base

## Goal

Create a **foundational learning layer**.

## Tasks

- [ ] Create rsID Detail Page
- [ ] Display:
  - rsID
  - Associated gene (if available)
  - Related traits
  - Genotype interpretations (AA / AG / GG)

- [ ] Add "fun fact" or explanation section
- [ ] Use static dataset initially (20–50 rsIDs)
- stop hardcoding logic per trait (go from 5 → ~10–15 traits)
- only add traits you can fully map to rsIDs

## Output

- System supports bottom-up exploration (variant-first)
- Unlocks: bottom-up exploration starting from genetic variants instead of traits

---

# 📊 Phase 5 – Genotype Impact Visualization

## Goal

Add **meaningful visual explanation (not decorative charts)**.

## Tasks

- [ ] Build reusable component:
  - Shows genotype options (AA / AG / GG)
  - Displays relative effect (low / medium / high)

- [ ] Highlight user's genotype
- [ ] Integrate into Trait Detail Page

## Rules

- Keep visuals simple
- No heavy libraries (start with basic UI blocks)

## Output

- Visual understanding of variant influence
- Unlocks: intuitive understanding of how genotype differences influence trait outcomes

---

# 🧪 Phase 6 – DNA Explorer (Mock Genome Mode)

## Goal

Enable **exploration without user data** (VERY important for thesis).

## Tasks

- [ ] Create "Explorer Mode" tab
- [ ] Load sample/mock genome dataset
- [ ] Allow browsing:
  - traits
  - rsIDs

- [ ] Add genotype toggle:
  - Switch between AA / AG / GG
- go form 10-15 to 20 → 30+ traits
- [ ] Recalculate trait interpretation dynamically

## Output

- Interactive learning environment
- Demonstrates causality
- Unlocks: experimentation with genotype changes to understand causality

---

# 🧩 Phase 7 – Trait Organization & Metadata

## Goal

Improve structure and interpretability.

## Tasks

- [ ] Group traits into categories:
  - Nutrition
  - Appearance
  - Health
  - Behavior

- [ ] Add confidence levels:
  - Strong
  - Moderate
  - Weak
- go from 30+ traits to 40 → 100+ traits
- [ ] Display confidence in UI

## Output

- More structured and trustworthy system
- Unlocks: structured, interpretable system with categories and confidence levels

---

# 🧠 Phase 8 – Explanation System

## Goal

Make the platform **educational**.

## Tasks

- [ ] Add explanation toggle:
  - "Simple" vs "Technical"

- [ ] Write explanations for:
  - traits
  - rsIDs

- [ ] Ensure consistent tone and clarity

## Output

- Supports both beginners and advanced users
- Unlocks: accessibility for different knowledge levels (beginner ↔ advanced)

---

# 🏗️ Phase 9 – Architecture & Code Quality (Thesis Critical)

## Goal

Prepare system for **academic evaluation**.

## Tasks

- [ ] Document architecture:
  - frontend (React)
  - backend (FastAPI)
  - data flow

- [ ] Ensure modular services:
  - parser service
  - trait engine
  - knowledge base

- [ ] Add basic tests:
  - parser tests
  - trait mapping tests

## Output

- Clean, defensible engineering design
- Unlocks: defensible, well-structured system suitable for academic evaluation

---

# 🎨 Phase 10 – UX/UI Refinement (FINAL)

## Goal

Polish the experience **after functionality is complete**.

## Tasks

- [ ] Improve layout consistency
- [ ] Add spacing, typography
- [ ] Improve navigation between:
  - traits
  - rsIDs
  - explorer

- [ ] Make interactions intuitive

## Output

- Cohesive, user-friendly interface
- Unlocks: cohesive, intuitive user experience built on top of solid functionality

---

# 🧪 Optional Phase – Counterfactual Simulation Layer (Advanced Exploration)

## Goal

Add a **simulation-based exploration layer** that allows users to explore how genetic trait interpretations might change under different hypothetical biological contexts, without modifying or collecting real user identity data. This phase introduces a “what-if” system where users can adjust contextual parameters (e.g. age range, biological context, population baseline) and observe how trait interpretations shift, while keeping the underlying genetic analysis unchanged and immutable.

## Tasks

- [ ] Add “Simulation Mode” toggle in Trait Detail page and/or Explorer Mode
- [ ] Introduce conditional simulation controls:
  - Age slider (e.g. 18 → 80, grouped into ranges internally)
  - Biological context selector (e.g. neutral / male model / female model where applicable)
  - Population reference selector (e.g. global baseline vs region-adjusted frequencies)

- [ ] Ensure all simulation inputs are explicitly labeled as:
  - “Hypothetical / simulated interpretation only”

- [ ] Implement side-by-side comparison view:
  - Base interpretation (fixed, derived from DNA only)
  - Simulated interpretation (context-adjusted view)

- [ ] Ensure simulation layer does NOT modify stored user DNA or core trait results
- [ ] Keep simulation logic purely presentation + reinterpretation layer

## Output

- Users can interactively adjust sliders and context options to see how interpretations change
- Users can compare:
  - objective genetic interpretation (fixed baseline)
  - contextual simulation interpretation (hypothetical scenario)

- Users gain intuition that genetic traits are probabilistic and context-sensitive rather than absolute
- Adds a controlled “what-if” reasoning layer to the platform

---

## Design Principle

- Core DNA analysis remains **immutable and context-free**
- Simulation layer is **educational, optional, and non-persistent**
- All contextual controls operate as **user-controlled sliders and toggles**
- No demographic or personal data is stored or inferred
- The system prioritizes **transparency and explainability over personalization**

## Unlocks

- Advanced exploratory learning through **counterfactual reasoning**
- Deeper understanding of how assumptions affect trait interpretation
- Strong differentiation between raw genomic analysis and interpretive modeling layers

---

## Core Data Structures (DO NOT CHANGE LIGHTLY)

Variant:
{ rsid: string, genotype: string, chromosome: string, position: number }

Trait:
{ id: string, name: string, rsids: string[] }

TraitResult:
{ id: string, name: string, result: string }

TraitDetail:
{
id: string,
name: string,
result: string,
description: string,
rsids: [
{ rsid: string, genotype: string, effect: string, description: string }
]
}

---

## Key API Endpoints

POST /upload
→ parses DNA file and stores variants

GET /analyze
→ returns list of TraitResult

GET /trait/{id}
→ returns TraitDetail

GET /search?q=
→ returns traits + rsids

GET /rsid/{id}
→ returns rsID details

GET /explorer
→ returns mock genome

---

Only add traits when ALL of this is true:

1. Each trait has:

- rsID mapping
- genotype interpretation
- consistent logic

2. It improves something in UI:

- drill-down depth
- search usefulness
- exploration richness

## Design Principles

- Always show WHY a trait result exists (traceability)
- Prefer simple, explainable logic over complex models
- Visuals must explain, not decorate
- Build exploration, not static reports
- Avoid premature optimization

---

# 🧠 Final System Vision

By the end, your system should support:

### Flow 1 (User Data)

Upload → Traits → Drill-down → Understand

### Flow 2 (Exploration)

Search → rsID → Trait → Genotype → Meaning

### Flow 3 (Learning Mode)

Explorer → Modify genotype → See effect → Learn causality

---

# ✅ Success Criteria

You are done when:

- Users can trace **trait → variant → genotype → explanation**
- Users can **experiment with genotype changes**
- Visuals **clarify**, not decorate
- System is **modular and explainable**

---
