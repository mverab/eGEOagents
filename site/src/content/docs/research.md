---
title: Research Behind E-GEO
description: The research lineage of E-GEO — the Princeton KDD 2024 GEO study, the E-GEO preprint (arXiv:2511.20867), and how the findings map to code.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Research Behind E-GEO",
        "description": "The research lineage of E-GEO: the Princeton KDD 2024 GEO study, the E-GEO preprint, and how findings map to the toolkit's code.",
        "url": "https://egeoagents.com/research/",
        "datePublished": "2026-08-11",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

E-GEO is research-grounded in a specific, verifiable way. This page states exactly what the research says, what status each paper has, and where each finding lands in code.

## The lineage

### 1. Princeton GEO study — the foundation

[Generative Engine Optimization](https://arxiv.org/abs/2311.09735) (Aggarwal et al., **KDD 2024** — a peer-reviewed venue) defined the field: it showed that specific, measurable content changes (adding citations, statistics, authoritative phrasing) shift how generative engines select and rank sources, with visibility improvements measurable against baselines. Every GEO tool, including this one, builds on it.

### 2. E-GEO preprint — the applied layer

The [E-GEO preprint](https://arxiv.org/abs/2511.20867) (arXiv:2511.20867) extends that line with an applied focus. arXiv is a preprint server: the paper is **published research, not peer-reviewed** — we describe it that way everywhere, and you should hold us to it.

What it reports:

1. **Competitive framing** produced the strongest immediate ranking lift among the strategies tested.
2. A **universal strategy** (all 10 features applied together) outperformed individual heuristics by a wide margin.
3. The **10 features** — ranking emphasis, user intent, competitive differentiation, social proof, narrative, authority, USPs, urgency, scannability, factual accuracy — consistently appeared in higher-ranking content across ChatGPT, Perplexity, and Gemini.

## From paper to code

| Research finding | Where it lives in E-GEO |
|---|---|
| 10 GEO features | `GEO_FEATURES` in `egeo/agents.py` — the analyzer's scoring checklist ([explained](/concepts/geo-features/)) |
| Universal strategy > single heuristics | The rewriter applies all features in one pass instead of cherry-picking |
| Competitive framing's outsized lift | Ranker stage: simulates engine ranking against competitors and explains gaps |
| Measurable, not vibes | [Reproducible evaluation harness](/docs/evaluation/) — offline, deterministic, runs in CI |

## Honest limitations

- The evaluation harness measures an **LLM-ranker proxy**, not real engine rankings. It tells you the rewrite moved in the right direction; it cannot prove ChatGPT will cite you. [Full disclosure in the evaluation docs](/docs/evaluation/).
- Engine behavior changes constantly. Findings are snapshots; that is why E-GEO ships a [continuous loop](/docs/geo-loop/) instead of a one-time fix.
- arXiv:2511.20867 is a preprint. The peer-reviewed anchor in this lineage is the Princeton KDD 2024 study.

## Why publish this page at all

Because a GEO tool whose own claims can't be traced to sources is selling the exact disease it claims to cure. Every claim on this site links to its ground truth — code, paper, or measured data — and the [comparison pages](/compare/geo-tools-2026/) credit competitors' real strengths, including the one with more stars than us.

The measurement log of applying that rule to E-GEO itself is the [visibility case study](/case-study/) (weekly Perplexity snapshots from 2026-08-05; head query still false).

---

**In short:** E-GEO stands on the peer-reviewed Princeton GEO study (KDD 2024) plus the project's own applied preprint (arXiv:2511.20867), and every finding maps to a specific, inspectable part of the codebase. Verify, don't trust: [github.com/mverab/eGEOagents](https://github.com/mverab/eGEOagents).
