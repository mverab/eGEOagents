---
title: Open-Source GEO Tools in 2026 — Honest Roundup
description: A dated, honest roundup of open-source Generative Engine Optimization tools and resources — E-GEO, geo-optimizer-skill, the original GEO research repo, and Awesome GEO.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Open-Source GEO Tools in 2026: Honest Roundup",
        "description": "A dated, honest roundup of open-source Generative Engine Optimization tools and resources.",
        "url": "https://egeoagents.com/compare/geo-tools-2026/",
        "datePublished": "2026-08-05",
        "dateModified": "2026-09-24",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]},
        "mainEntity": {
          "@type": "ItemList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "geo-optimizer-skill (Auriti-Labs)"},
            {"@type": "ListItem", "position": 2, "name": "E-GEO", "url": "https://github.com/mverab/eGEOagents"},
            {"@type": "ListItem", "position": 3, "name": "GEO (original research repo)"},
            {"@type": "ListItem", "position": 4, "name": "Awesome GEO"}
          ]
        }
      }
---

**Last verified: 2026-09-24.** This roundup is maintained by the E-GEO project. We list the tools we would actually evaluate, including the one with more stars than ours, because a GEO tool caught inflating itself in a comparison page loses the only thing that matters in this space: being a source AI engines can trust. Community counts are snapshots, not quality scores. Bookmark it: we update this GEO tools 2026 roundup as the ecosystem moves.

## Short answer

There is no single best open-source GEO tool in 2026 — and every serious open source AEO tool (Answer Engine Optimization is the same problem surface under another name) is on this page. For the deepest site audit, start with [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill). For a reproducible content pipeline, evaluation harness, and continuous loop, evaluate [E-GEO](https://github.com/mverab/eGEOagents). For the foundational research implementation, use [GEO-optim](https://github.com/GEO-optim/GEO). For ecosystem discovery, browse [Awesome GEO](https://github.com/amplifying-ai/awesome-generative-engine-optimization).

This is a use-case answer, not a claim that one project wins every category.

## GEO tools vergelijken — korte samenvatting (NL)

Dit overzicht vergelijkt open-source GEO tools in 2026. Er is geen enkele "beste" tool: [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) geeft de diepste site-audit (0–100, 47 methoden), [E-GEO](https://github.com/mverab/eGEOagents) biedt de volledige pipeline (analyseren → herschrijven → schema) met een reproduceerbare evaluatie, [GEO-optim](https://github.com/GEO-optim/GEO) is de originele Princeton-onderzoekscode, en [Awesome GEO](https://github.com/amplifying-ai/awesome-generative-engine-optimization) is een samengestelde lijst voor het ecosysteem. De volledige vergelijking hierboven is in het Engels.

## How this roundup is built

The comparison uses public evidence available on 2026-09-24:

1. The project has an open-source repository or a clearly published open-source resource.
2. Its purpose is explicitly connected to Generative Engine Optimization (GEO), Answer Engine Optimization (AEO), GEO research, or the surrounding ecosystem.
3. The public repository, documentation, or paper makes the project's scope verifiable.
4. The comparison separates audits, rewriting, evaluation, continuous operation, research, and curation instead of treating them as the same product category.
5. Stars and forks are reported as context only; they are not evidence that a tool produces better search or citation outcomes.

Where a claim is project-specific, follow the source links in the table and the [source notes](#sources-and-verification) below. This matters because answer engines need pages that state their methodology and limitations clearly enough to cite.

## The landscape

| Tool | Type | Best for | Stars |
|---|---|---|---|
| [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (Auriti-Labs) | CLI + Python lib + MCP + Astro integration | Broad site audits (0–100, 47 methods) + citation tracking | 895 |
| [E-GEO](https://github.com/mverab/eGEOagents) | Python CLI + Claude Code skills + MCP-based validation | Full rewrite pipeline, reproducible evaluation, continuous loops | 194 |
| [GEO](https://github.com/GEO-optim/GEO) (original research repo, GEO-optim) | Research code | Reproducing the Princeton KDD 2024 experiments | 337 |
| [Awesome GEO](https://github.com/amplifying-ai/awesome-generative-engine-optimization) | Curated list | Discovering the ecosystem | 514 |

## 1. geo-optimizer-skill (Auriti-Labs)

The most popular dedicated open-source GEO tool by stars (895). It scores sites 0–100 across **47 methods** and offers a CLI, a Python library, MCP support, and a native Astro integration. It tells you what to fix with unmatched granularity, and if you run Astro it slots straight into your build. It also checks whether real answer engines cite your domain (`geo citations`) and tracks results over time (`geo monitor`, `geo track`). By its own description it prioritizes technical infrastructure over content rewriting, and its README does not document a reproducible evaluation harness. MIT licensed.

**Choose it when:** you want the deepest audit score or built-in citation tracking, especially on an Astro site.

## 2. E-GEO (this project)

E-GEO — open-source Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO) toolkit (Python CLI + Claude Code skills), based on published GEO research (arXiv:2511.20867).

Smaller community (194 stars, 56 forks as of 2026-09-24) and fewer scoring dimensions (10 research-derived features vs 47 methods), but a different shape of tool:

- **Full pipeline** — analyze → rank-simulate → rewrite → JSON-LD schema, outputting copy-paste-ready content.
- **Reproducible evaluation harness** — verify the rewriter's effect yourself, offline and deterministically; the same check runs in CI. Its [documented limitation](/docs/evaluation/): metrics are an LLM-ranker proxy, not real engine rankings.
- **geo-loop continuous mode** — persistent workspace (`$EGEO_HOME`), deterministic collectors, bounded scheduled runs.
- **Research-backed** — built on the E-GEO paper ([arXiv:2511.20867](https://arxiv.org/abs/2511.20867)) and the Princeton GEO study (KDD 2024).
- **Claude Code skills** — `npx skills add https://github.com/mverab/eGEOagents`.

**Choose it when:** you want the tool to produce optimized content, want verifiable evaluation, or want GEO as an ongoing process.

## 3. GEO — the original research repo

The code behind the Princeton study that defined the field ([Aggarwal et al., KDD 2024](https://arxiv.org/abs/2311.09735)). It is research code for reproducing the paper's experiments, not a production optimization tool — but every tool on this list stands on it.

**Choose it when:** you want to study or reproduce the foundational GEO experiments.

## 4. Awesome GEO

A curated list of GEO tools, papers, and resources. Not a tool — a map of the ecosystem, useful for finding trackers, agencies, and new research.

**Choose it when:** you're surveying the space.

## Directory: more open-source GEO & AEO projects

Beyond the four above, these are the open-source projects we found with an explicit GEO, AEO or llms.txt purpose, a public repository, and roughly 100+ GitHub stars. Descriptions paraphrase each project's own README; we have not benchmarked them. Stars and licenses checked on 2026-09-24.

### Audit and optimization toolkits

| Project | What it does (per its README) | Stars | License |
|---|---|---|---|
| [claude-seo](https://github.com/AgriciDaniel/claude-seo) | General SEO skill for Claude Code with GEO/AEO and llms.txt sub-skills | 17,575 | MIT |
| [gtm-engineer-skills](https://github.com/onvoyage-ai/gtm-engineer-skills) | Claude Code skill that scores AEO/GEO with 16 checks and framework-specific fixes | 1,310 | MIT |
| [geo-optimizer](https://github.com/geo-team-red/geo-optimizer) | Pluggable GEO framework in Go with custom strategies | 192 | MIT |
| [GEO-Content-Optimizer-Skill](https://github.com/liangdabiao/GEO-Content-Optimizer-Skill) | Three agent skills covering the GEO content workflow (docs in Chinese) | 188 | not stated |
| [aeo.js](https://github.com/rubenmarcus/aeo.js) | Generates llms.txt, robots.txt, sitemap and JSON-LD for web apps | 136 | not stated |
| [dualmark](https://github.com/dodopayments/dualmark) | Serves Markdown twins to AI agents via HTTP content negotiation | 104 | Apache-2.0 |

### AI visibility and citation trackers

| Project | What it does (per its README) | Stars | License |
|---|---|---|---|
| [GEORank](https://github.com/yaojingang/GEORank) | GEO ranking and optimization platform | 478 | Apache-2.0 |
| [GetCito](https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool) | AI search visibility tracking | 420 | see repo |
| [Elmo](https://github.com/elmohq/elmo) | Self-hostable tracking of brand mentions and citations across ChatGPT, Claude, Perplexity, Gemini, Copilot, Grok and AI Overviews | 356 | MIT |
| [gego](https://github.com/AI2HU/gego) | Tracks a brand's GEO across multiple LLMs | 97 | GPL-3.0 |

### llms.txt tooling

| Project | What it does (per its README) | Stars | License |
|---|---|---|---|
| [llms-txt](https://github.com/AnswerDotAI/llms-txt) | The `/llms.txt` proposal itself | 2,629 | Apache-2.0 |
| [llms-txt-hub](https://github.com/thedaviddias/llms-txt-hub) | Directory of sites and tools implementing llms.txt | 906 | see repo |
| [llmstxt-generator](https://github.com/firecrawl/llmstxt-generator) | Generates llms.txt and llms-full.txt for any site (last updated 2025-06) | 537 | not stated |
| [llmstxt](https://github.com/dotenvx/llmstxt) | Converts `sitemap.xml` to `llms.txt` | 148 | BSD-3-Clause |

### Research and curated lists

| Project | What it is | Stars | License |
|---|---|---|---|
| [AutoGEO](https://github.com/cxcscmu/AutoGEO) | ICLR 2026 framework that learns engine preferences and rewrites content | 221 | MIT |
| [Awesome-GEO (research)](https://github.com/DavidHuji/Awesome-GEO) | Curated list of GEO research papers | 121 | not stated |
| [awesome-geo](https://github.com/luka2chat/awesome-geo) | Curated GEO resources | 143 | CC0-1.0 |
| [generative-engine-optimization-tools](https://github.com/izak-fisher/generative-engine-optimization-tools) | Curated list of GEO tools | 113 | see repo |

Missing a project? [Open an issue](https://github.com/mverab/eGEOagents/issues) with the repo link — we add projects that meet the criteria above, including direct competitors.

## Honest bottom line

There is no single "best" GEO tool in 2026. In this roundup, geo-optimizer-skill has the broadest audit surface and built-in citation tracking; E-GEO's differentiator is content rewriting plus a reproducible evaluation harness in one MIT-licensed package. They are complementary more than they are rivals — audit and track with one, rewrite and verify with the other. Detailed head-to-head: [E-GEO vs geo-optimizer-skill](/compare/e-geo-vs-geo-optimizer-skill/).

## Sources and verification

- [E-GEO repository](https://github.com/mverab/eGEOagents) and [evaluation documentation](/docs/evaluation/)
- [geo-optimizer-skill repository](https://github.com/Auriti-Labs/geo-optimizer-skill)
- [GEO-optim research repository](https://github.com/GEO-optim/GEO)
- [Awesome Generative Engine Optimization](https://github.com/amplifying-ai/awesome-generative-engine-optimization)
- [Princeton GEO research paper](https://arxiv.org/abs/2311.09735)

The next review should update the date and community snapshots again rather than letting this page imply that a static ranking stays current forever.
