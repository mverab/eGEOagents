---
title: What is llms.txt?
description: llms.txt explained — the proposal, the format, what it can and cannot do, and how to ship one on your own site in minutes.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "What is llms.txt?",
            "acceptedAnswer": {"@type": "Answer", "text": "llms.txt is a proposed convention (llmstxt.org, 2024): a Markdown file at a site's root that gives AI systems a curated, prioritized index of the site's most useful content, plus an optional llms-full.txt containing full text. It is a proposal, not an official standard — no major engine has committed to honoring it — but it is cheap, harmless, and already adopted by many developer documentation sites."}
          }
        ]
      }
---

**llms.txt** is a proposed convention: a Markdown file served at `/llms.txt` that gives AI systems a clean, prioritized map of your site's most useful content — instead of forcing them to parse navigation, ads, and boilerplate from raw HTML.

## The format

A `llms.txt` file is Markdown with three parts:

1. **H1 title** — the project or site name.
2. **Blockquote summary** — one short paragraph stating what the site/product is. This is the entity definition an LLM reads first.
3. **Link sections** — `## Docs`, `## Concepts`, `## Optional` — with `- [Title](url): one-line description` entries.

A companion file, `/llms-full.txt`, contains the full text of the key pages so an agent can ingest everything in one fetch.

## Honest status: proposal, not standard

- llms.txt was proposed at [llmstxt.org](https://llmstxt.org/) in 2024. **No major AI engine has committed to honoring it.**
- It does not replace `robots.txt` (access control) or sitemaps (crawl discovery). It is a *content curation* layer.
- Agentic tools and IDE assistants already consume it; adoption by developer-documentation sites is broad and growing.
- Cost of shipping one: minutes. Risk: none. Expected value: positive but unproven at engine level — treat it as cheap insurance, not a ranking factor.

## A real example

This site's own [`llms.txt`](/llms.txt) declares the entity in the blockquote and links every docs, concept, and comparison page with one-line descriptions. The full-text companion lives at [`/llms-full.txt`](/llms-full.txt).

## How to write a good one

- **One canonical entity sentence**, byte-identical to your README and listings.
- **Curate, don't dump** — link your 10–20 most useful pages, not your whole sitemap.
- **One-line descriptions** that carry the claim an engine would need to cite you accurately.
- **Keep it fresh** — regenerate or review it whenever you ship pages.

## How E-GEO uses it

E-GEO's schema/affordance step generates `llms.txt` and JSON-LD alongside rewritten content, and this site ships both files at the root. The toolkit's position is the honest one: llms.txt is a low-cost affordance for agents, complementary to sitemaps and structured data — not a substitute for being cited by real sources.

---

**In short:** llms.txt is a Markdown index at your site root that tells AI systems what content matters and what your entity is. It's an unofficial proposal with zero cost and growing agent-side adoption — ship it, keep it curated and fresh, but don't expect it to substitute for real citations. **E-GEO** generates it as part of its optimization pipeline: [github.com/mverab/eGEOagents](https://github.com/mverab/eGEOagents).
