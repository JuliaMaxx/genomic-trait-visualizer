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

I added them in a way that fits your existing structure and tone so you can paste it directly into your thesis objectives.

---

# 🎨 Additional Design Directions (Optional)

These directions define **possible interface paradigms** that can guide the visual and interaction design of the system. They are not separate features, but _overlays that shape how users experience exploration and explanation_.

---

## 🧭 1. Command-Driven Scientific Console (WHOAMI Interface)

Introduce an optional **command-based interaction layer** inspired by scientific terminals.

### Concept

Users can interact with the system through structured commands that reflect genomic reasoning steps.

### Example

```text
whoami > upload genome.vcf
✔ Parsed 632,901 variants

whoami > trait lactose_tolerance
→ Likely tolerant (0.82 confidence)
→ 3 contributing rsIDs found

whoami > explain rs4988235
→ CT genotype increases lactase persistence probability
```

### Purpose

- Reinforces step-by-step analytical thinking
- Makes system interaction feel like structured investigation
- Supports traceability between queries and results

### Design Rule

Command input is an **entry layer only**; all outputs must remain structured, readable, and visually organized.

---

## 🧠 2. Layered Explanation System (Progressive Disclosure Model)

Introduce a **multi-depth explanation structure** for traits and rsIDs.

### Concept

Each piece of information exists in multiple levels of detail:

- **Level 1 – Simple:** intuitive explanation
- **Level 2 – Genetic basis:** rsIDs and genotype effects
- **Level 3 – Technical:** biological or statistical context (optional)

### Purpose

- Supports both beginner and advanced users
- Prevents cognitive overload
- Encourages exploration of deeper genetic reasoning

### Design Rule

Users should progressively expand knowledge rather than navigate away from it.

---

## ⚖️ 3. Dual-Reality Interface (Data vs Interpretation Separation)

Explicitly separate **raw genetic data** from **computed interpretation** in the UI.

### Concept

The interface visually distinguishes:

- **Data Layer (Objective):**
  - rsID
  - genotype
  - chromosome position

- **Interpretation Layer (Derived):**
  - trait association
  - biological meaning
  - confidence level

### Example Layout

```
rs4988235 (CT)
───────────────
DATA            →  INTERPRETATION
CT genotype     →  Likely lactose tolerant
```

### Purpose

- Makes inference process transparent
- Clearly communicates uncertainty and derivation logic
- Strengthens academic credibility of the system

### Design Rule

Interpretations must always be visually or structurally distinguishable from raw genetic data.

---

## 🧩 Design Integration Note

These three directions should be treated as **complementary layers**, not competing paradigms:

- The **Command Console** defines interaction style
- The **Layered Explanation System** defines information depth
- The **Dual-Reality Interface** defines information structure

Together, they reinforce the core thesis goal:

> A transparent, explorable, and explainable genomic interpretation system.

---

# Example UI prototype

```
import { useState } from "react";

export default function DualLayerMock() {
const [command, setCommand] = useState("whoami > trait lactose_tolerance");

return (
<div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
{/_ Header _/}
<div className="flex items-center justify-between mb-4">
<div className="text-xl font-semibold tracking-tight">
whoami <span className="text-zinc-500">/ genomic explorer</span>
</div>
<div className="text-xs text-zinc-500">CLI + Dual-Layer + Progressive Disclosure</div>
</div>

      {/* CLI INPUT LAYER */}
      <div className="mb-6 border border-zinc-800 rounded-xl p-4 bg-zinc-900/30">
        <div className="text-xs text-zinc-500 mb-2">COMMAND INTERFACE</div>

        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-zinc-500">whoami &gt;</span>
          <input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            className="bg-transparent flex-1 outline-none text-zinc-100"
          />
        </div>

        <div className="mt-2 text-xs text-zinc-600">
          Try: trait lactose_tolerance | explain rs4988235 | explore genome
        </div>
      </div>

      {/* Level selector */}
      <div className="flex gap-2 mb-6 text-xs">
        <div className="px-3 py-1 rounded-full bg-zinc-800">Level 1 · Simple</div>
        <div className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-700">Level 2 · Genetic</div>
        <div className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-700">Level 3 · Technical</div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* LEFT: DATA */}
        <div className="border border-zinc-800 rounded-xl p-5 bg-zinc-900/40">
          <div className="text-sm text-zinc-500 mb-4">DATA LAYER (RAW GENETIC INFORMATION)</div>

          <div className="space-y-4 font-mono text-sm">
            <div className="flex justify-between">
              <span>rs4988235</span>
              <span className="text-zinc-400">CT</span>
            </div>

            <div className="flex justify-between">
              <span>chromosome</span>
              <span className="text-zinc-400">2</span>
            </div>

            <div className="flex justify-between">
              <span>position</span>
              <span className="text-zinc-400">136608646</span>
            </div>

            <div className="flex justify-between">
              <span>gene</span>
              <span className="text-zinc-400">LCT</span>
            </div>
          </div>
        </div>

        {/* RIGHT: INTERPRETATION + LAYERS */}
        <div className="border border-orange-500/30 rounded-xl p-5 bg-orange-500/5">
          <div className="text-sm text-orange-300 mb-4">
            INTERPRETATION LAYER (PROGRESSIVE EXPLANATION)
          </div>

          {/* Level 1 */}
          <div className="mb-5">
            <div className="text-xs text-zinc-500 mb-1">Level 1 · Simple</div>
            <div className="text-lg font-medium">
              You are likely lactose tolerant
            </div>
          </div>

          {/* Level 2 */}
          <div className="mb-5 border-t border-orange-500/20 pt-3">
            <div className="text-xs text-zinc-500 mb-1">Level 2 · Genetic basis</div>
            <div className="text-sm text-zinc-300">
              The CT genotype at rs4988235 is associated with continued lactase production in adulthood. One copy of the variant contributes to lactose tolerance.
            </div>
          </div>

          {/* Level 3 */}
          <div className="border-t border-orange-500/20 pt-3">
            <div className="text-xs text-zinc-500 mb-1">Level 3 · Technical context</div>
            <div className="text-sm text-zinc-400">
              rs4988235 is located upstream of the LCT gene and affects regulatory persistence of lactase expression. The allele frequency varies across populations due to evolutionary selection pressures linked to dairy consumption.
            </div>
          </div>

          {/* CLI-driven contextual hint */}
          <div className="mt-6 pt-3 border-t border-orange-500/20">
            <div className="text-xs text-zinc-500">Command-linked interpretation</div>
            <div className="text-sm text-orange-200 font-mono">
              {command.includes("lactose")
                ? "→ Trait context: digestion metabolism pathway"
                : "→ Awaiting genomic query context..."}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-xs text-zinc-600">
        CLI input drives exploration layer; dual-layer view separates raw genetic data from interpretive explanation; progressive disclosure controls depth of understanding.
      </div>
    </div>

);
}
```
