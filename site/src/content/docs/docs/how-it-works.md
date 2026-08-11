---
title: How It Works
description: A technical deep dive into E-GEO's 4-agent GEO optimization pipeline, the 10 GEO features, and the research behind it.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "How E-GEO Works",
        "description": "Technical deep dive into E-GEO's 4-agent GEO optimization pipeline and the research behind it.",
        "url": "https://egeoagents.com/docs/how-it-works/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]},
        "citation": "https://arxiv.org/abs/2511.20867"
      }
---

## Architecture overview

```
User Input (URL or file)
    ↓
┌─────────────────────────────────────────┐
│         E-GEO Pipeline                  │
│  ┌─────────┐  ┌────────┐  ┌─────────┐  │
│  │Analyzer │→ │ Ranker │→ │Rewriter │  │
│  └─────────┘  └────────┘  └────┬────┘  │
│                                ↓        │
│                          ┌──────────┐  │
│                          │ Indexer  │  │
│                          └──────────┘  │
└─────────────────────────────────────────┘
    ↓
geo-output/ (report, optimized content, schema)
```

The same four agents run either **in-process** through the Python runtime behind the `egeo` CLI, or **host-executed** through Claude Code `/geo` slash commands. A small runtime adapter layer (`egeo/runtimes.py`) keeps the two paths sharing one source of truth.

## The 4 agents

### 1. Analyzer

Extracts content, scores it against the [10 universal GEO features](/concepts/geo-features/), identifies gaps, and writes `analysis.json`:

```json
{
  "url": "https://example.com",
  "geo_score": 67,
  "features": {
    "ranking_emphasis": 5,
    "user_intent": 9,
    "competitive_diff": 4
  },
  "gaps": ["missing social proof", "weak competitive positioning"]
}
```

### 2. Ranker

Simulates how an AI search engine would rank the content against competitors, predicts positions, and explains why competitors rank higher. Per the E-GEO paper (arXiv:2511.20867), competitive framing produces the strongest immediate ranking improvement.

### 3. Rewriter

Rewrites content applying the 10 GEO features while preserving brand voice and factual accuracy — no fabricated statistics, testimonials, or ratings.

| # | Feature | What it means |
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

### 4. Indexer

Generates JSON-LD schema markup (`SoftwareApplication`, `Organization`, `Article`, `Product`, `Service`, `FAQPage`), meta tags, and implementation checklists.

## The research behind E-GEO

E-GEO is based on the paper *"E-GEO: Optimizing Content for Generative Engines"* ([arXiv:2511.20867](https://arxiv.org/abs/2511.20867)), building on the foundational Princeton GEO study ([Aggarwal et al., KDD 2024](https://arxiv.org/abs/2311.09735)).

Key findings the toolkit operationalizes:

- Competitive framing produces the strongest immediate ranking lift among tested GEO strategies.
- A universal strategy (all 10 features together) outperforms individual heuristics.
- The 10 GEO features consistently appear in higher-ranking content across ChatGPT, Perplexity, and Gemini.

See the paper for full methodology; results vary by content quality and competition.

## Validation layer

When run through Claude Code, E-GEO's client workflow validates outputs against ground truth using external MCP servers:

| MCP server | Purpose | Criticality |
|------------|---------|-------------|
| **Brave Search** | Competitor analysis, SERP data, ground truth | High |
| **Chrome DevTools** | Rendered DOM validation, performance metrics | High |
| **fetch** | Simple text scraping (fallback) | Medium |

When MCP servers are unavailable, E-GEO still runs but marks outputs **"Low Confidence"**. See [MCP-based validation](/docs/mcp-server/) for setup.

## Auto-triggered skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **competitive-analysis** | Questions about competitors | Analyze the competitive landscape |
| **content-scoring** | Requests to score content | Evaluate against the 10 GEO features |
| **schema-generator** | Structured data needs | Generate JSON-LD markup |
| **validation-doctor** | MCP setup issues | Verify dependencies and configuration |
| **geo-loop** | `/geo:loop <domain>` | Enforce the loop-mode run contract |

## See also

- [Getting Started](/docs/getting-started/)
- [CLI Reference](/docs/cli/)
- [Evaluation Harness](/docs/evaluation/) — measure prompt quality yourself
- [GEO Loop](/docs/geo-loop/) — continuous optimization
