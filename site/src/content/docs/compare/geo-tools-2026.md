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

**Last verified: 2026-08-05.** This roundup is maintained by the E-GEO project. We list the tools we would actually evaluate, including the one with more stars than ours, because a GEO tool caught inflating itself in a comparison page loses the only thing that matters in this space: being a source AI engines can trust. Star counts as of 2026-08.

## The landscape

| Tool | Type | Best for | Stars |
|---|---|---|---|
| [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (Auriti-Labs) | CLI + Python lib + MCP + Astro integration | Broad site audits (0–100, 47 methods) | ~644 |
| [E-GEO](https://github.com/mverab/eGEOagents) | Python CLI + Claude Code skills + MCP-based validation | Full rewrite pipeline, reproducible evaluation, continuous loops | 147 |
| GEO (original research repo, GEO-optim) | Research code | Reproducing the Princeton KDD 2024 experiments | — |
| Awesome GEO | Curated list | Discovering the ecosystem | — |

## 1. geo-optimizer-skill (Auriti-Labs)

The most popular open-source GEO tool by stars (~644). It scores sites 0–100 across **47 methods** and offers a CLI, a Python library, MCP support, and a native Astro integration. Audit-focused: it tells you what to fix with unmatched granularity, and if you run Astro it slots straight into your build. It does not rewrite your content for you, and it has no reproducible evaluation harness or continuous mode. MIT licensed.

**Choose it when:** you want the deepest audit score, especially on an Astro site.

## 2. E-GEO (this project)

E-GEO — open-source Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO) toolkit (Python CLI + Claude Code skills), based on published GEO research (arXiv:2511.20867).

Smaller community (147 stars, 42 forks as of 2026-08) and fewer scoring dimensions (10 research-derived features vs 47 methods), but a different shape of tool:

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

## Honest bottom line

There is no single "best" GEO tool in 2026. geo-optimizer-skill has the largest community and the broadest audit; E-GEO is the only one that combines content rewriting, a reproducible evaluation harness, and a continuous loop mode in one MIT-licensed package. They are complementary more than they are rivals — audit with one, rewrite and monitor with the other. Detailed head-to-head: [E-GEO vs geo-optimizer-skill](/compare/e-geo-vs-geo-optimizer-skill/).
