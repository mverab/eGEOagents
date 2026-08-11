---
title: How to Get Cited by Perplexity (Measured Playbook)
description: A playbook for Perplexity citations built from weekly measurements — which sources Perplexity cites, why stars don't matter, and what to publish.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "How to Get Cited by Perplexity (Measured Playbook)",
        "description": "A Perplexity citation playbook built from weekly measurements: curator sources, PerplexityBot, dated comparison pages, and entity consistency.",
        "url": "https://egeoagents.com/guides/rank-in-perplexity/",
        "datePublished": "2026-08-11",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

**Last verified: 2026-08-11.** This playbook comes from running a fixed query set against Perplexity every week and recording which sources it cites — including a month where our own project had perfect on-page metadata and zero mentions.

## The finding that changes everything

Perplexity does not crawl GitHub and sort by stars. In our measured category (open-source GEO tools), projects with **17–37 stars appeared** in answers while a project with **147 stars did not** — for over a month. The difference was not product quality or README optimization. It was presence in the sources Perplexity synthesizes from:

- **Aggregators** (LibHunt was the top-cited source in our category).
- **Curated lists** (awesome-* repositories with their own authority).
- **Niche blogs and comparison articles** with dates and concrete criteria.

If those sources don't mention you, Perplexity doesn't either.

## Step 1 — Map what Perplexity cites for your queries

1. Write down 8–10 fixed queries your buyers ask (category, comparison, how-to).
2. Run them weekly. Record the **cited domains**, not just whether you appear.
3. The cited domains are your distribution target list. This is observable, not speculative — one query run shows you exactly which curators matter in your niche.

## Step 2 — Get into those sources

- Submit to the aggregators and directories that appear in answers.
- Contribute honest entries to curated lists (read each list's inclusion criteria first; a silently-closed PR is a signal to open an issue asking for criteria, not to spam).
- Publish the kind of third-party-style content yourself: dated comparisons that credit competitors. Pages with a visible "Last verified" date and a stated methodology are easier for an engine to trust and cite.

## Step 3 — Keep PerplexityBot unblocked

```text
User-agent: PerplexityBot
Allow: /
```

Check your CDN/WAF separately — `robots.txt` permission means nothing if a bot-fighting rule blocks the fetch upstream.

## Step 4 — Publish citable pages on your own domain

Perplexity cites pages, not repositories. Each target query deserves a page with:

- a direct answer in the first 50–170 words;
- a stated methodology ("how we built this comparison");
- a visible verification date;
- `Article` or `FAQPage` JSON-LD;
- links to primary sources.

## Step 5 — Entity consistency

Use one identical description of your product across your site, GitHub, package registries, and every listing. Answer engines build entity confidence from repetition across independent surfaces; drift between descriptions reads as uncertainty.

## What our measurements look like

We track 10 fixed queries (2 branded, 8 generic) weekly against Perplexity and snapshot the results. The metric that matters is **% of the fixed set mentioning you**, plus the cited-domain list. One run is a sample; the trend over weeks is the signal.

---

**In short:** Perplexity visibility is earned off your own site first — get into the curator sources it cites, keep `PerplexityBot` unblocked, publish dated citable pages, and measure weekly with a fixed query set. **E-GEO** implements this loop as open-source tooling (fixed query sets, snapshot diffs, content optimization): [github.com/mverab/eGEOagents](https://github.com/mverab/eGEOagents).
