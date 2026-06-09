# How E-GEO Works

> A technical deep dive into the 4-agent GEO optimization system.

---

## Architecture Overview

```
User Input (URL or file)
    ↓
┌─────────────────────────────────────────┐
│         E-GEO Pipeline                  │
│  ┌─────────┐  ┌────────┐  ┌─────────┐ │
│  │Analyzer │→ │ Ranker │→ │Rewriter │ │
│  └─────────┘  └────────┘  └────┬────┘ │
│                                 ↓      │
│                           ┌──────────┐ │
│                           │ Indexer  │ │
│                           └──────────┘ │
└─────────────────────────────────────────┘
    ↓
geo-output/ (report, optimized content, schema)
```

E-GEO is orchestrated by Claude Code and uses a multi-agent architecture. Each agent receives fresh context for optimal results.

---

## The 4 Agents

### 1. geo-analyzer

**Purpose:** Extract content and score GEO signals.

**What it does:**
- Fetches content from the target URL (via MCP fetch or web-reader)
- Scores the content against the 10 universal GEO features
- Identifies gaps and opportunities
- Generates `analysis.json` with structured data

**Output:**
```json
{
  "url": "https://example.com",
  "geo_score": 67,
  "features": {
    "ranking_emphasis": 5,
    "user_intent": 9,
    "competitive_diff": 4,
    ...
  },
  "gaps": ["missing social proof", "weak competitive positioning"]
}
```

### 2. geo-ranker

**Purpose:** Simulate AI-engine ranking.

**What it does:**
- Analyzes the content as an AI search engine would
- Predicts ranking position against competitors
- Identifies why competitors rank higher
- Provides confidence scores for predictions

**Key insight:** Based on the E-GEO research paper (arXiv:2511.20867), competitive framing produces the strongest immediate ranking improvement (+0.71 positions).

### 3. geo-rewriter

**Purpose:** Optimize content while preserving brand voice.

**What it does:**
- Rewrites content applying the 10 GEO features
- Maintains factual accuracy (no fabricated stats)
- Preserves the original brand tone and voice
- Generates copy-paste ready markdown

**The 10 GEO Features applied:**

| # | Feature | What It Means |
|---|---------|---------------|
| 1 | **Ranking Emphasis** | Frame as best/top choice |
| 2 | **User Intent Alignment** | Directly address search intent |
| 3 | **Competitive Differentiation** | Highlight unique advantages |
| 4 | **Social Proof** | Reviews, testimonials, stats |
| 5 | **Compelling Narrative** | Persuasive, engaging language |
| 6 | **Authoritativeness** | Expert, confident tone |
| 7 | **Unique Selling Points** | Clear differentiators |
| 8 | **Urgency Signals** | Scarcity or time-sensitivity |
| 9 | **Scannable Format** | Headings, bullets, structure |
| 10 | **Factual Accuracy** | Never fabricate data |

### 4. geo-indexer

**Purpose:** Generate schema markup and technical assets.

**What it does:**
- Creates JSON-LD schema markup for the content
- Generates meta tags and structured data
- Produces implementation checklists
- Validates schema against Schema.org standards

**Schema types generated:**
- `SoftwareApplication` — for product pages
- `Organization` — for company pages
- `Article` — for blog posts
- `Product` — for product descriptions
- `FAQPage` — for FAQ sections

---

## The Research Behind E-GEO

E-GEO is based on the research paper *"E-GEO: Optimizing Content for Generative Engines"* (arXiv:2511.20867).

### Key Findings

- **One universal strategy** exists for effective GEO — optimization beats all 15 common heuristics
- **"Competitive" framing** has the highest initial impact (+0.71 rank improvement)
- **Optimized prompts** converge to similar patterns regardless of starting point
- **Average improvement:** +25 points on the GEO score (45 → 70)

### Methodology

The research analyzed how AI search engines (ChatGPT, Perplexity, Claude, Gemini) rank and recommend content. It identified 10 features that consistently appear in higher-ranking responses.

---

## Validation Layer

E-GEO includes a validation layer using MCP servers:

| MCP Server | Purpose | Criticality |
|------------|---------|-------------|
| **Brave Search** | Competitor analysis, SERP data, ground truth | 🔴 High |
| **Chrome DevTools** | DOM validation, performance metrics | 🔴 High |
| **fetch** | Simple text scraping (fallback) | 🟡 Medium |

When MCP servers are unavailable, outputs are marked as **"Low Confidence"**.

---

## Skills (Auto-Triggered)

E-GEO includes 4 auto-triggered skills that activate based on context:

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **competitive-analysis** | User asks about competitors | Analyze competitive landscape |
| **content-scoring** | User asks to score content | Evaluate against GEO criteria |
| **schema-generator** | User needs structured data | Generate JSON-LD markup |
| **validation-doctor** | MCP setup issues | Verify dependencies and configuration |

---

## Output Structure

Every `/geo` run produces:

```
geo-output/
├── report.md              # Executive summary with scores and recommendations
├── analysis.json          # Structured analysis data
├── optimized/
│   └── [page-name].md     # GEO-optimized content (copy-paste ready)
├── schema/
│   ├── [page-name].json   # JSON-LD schema markup
│   └── IMPLEMENTATION.md  # Schema setup guide
└── checklist.md           # Priority action items
```

---

## See Also

- [Getting Started](getting-started.md) — Step-by-step tutorial
- [FAQ](faq.md) — Common questions
- [Skills.sh Playbook](skills-sh-playbook.md) — Distribution and metadata
- [USAGE.md](../USAGE.md) — Command reference
- [E-GEO Paper](https://arxiv.org/abs/2511.20867) — Research methodology

---

*Built for the AI-first web. 🤖 AI-assisted development — see [CONTRIBUTING.md](../CONTRIBUTING.md#ai-transparency) for details.*
