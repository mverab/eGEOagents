---
title: We Measured Our Own AI-Search Invisibility
description: Three weeks of a fixed Perplexity query set on an open-source GEO tool that did not show up — what moved, what did not, and what we still cannot claim.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "We Measured Our Own AI-Search Invisibility",
        "description": "Weekly Perplexity measurements of E-GEO from 2026-08-05 to 2026-08-24: branded mentions, one fragile generic hit, and a still-false head query.",
        "url": "https://egeoagents.com/case-study/",
        "datePublished": "2026-08-31",
        "dateModified": "2026-08-31",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

**Last verified: 2026-08-24.** Six snapshots. Same 10 queries. Same model (`sonar`). This is not six months of data and it is not a ranking guarantee.

E-GEO is an open-source GEO/AEO toolkit. For a month we optimized the repo (topics, description, README) and still did not appear when Perplexity was asked the category question: *What are the best open-source generative engine optimization (GEO) tools on GitHub in 2026?*

That query is still **false** on every snapshot. This page is the measurement log, not a success story.

## What we measured

A fixed set of 10 queries, weekly, via Perplexity Sonar. A mention is a binary: the answer text referred to E-GEO / eGEOagents. Branded queries are not treated as category wins.

| Date | Mentions | Head query (best OSS GEO tools on GitHub 2026) | Generic (non-branded) hits |
|---|---|---|---|
| 2026-08-05 | 2/10 | false | none |
| 2026-08-09 | 2/10 | false | none |
| 2026-08-10 | 3/10 | false | `GEO evaluation harness open source` |
| 2026-08-11 | 3/10 | false | same |
| 2026-08-17 | 4/10 | false | harness + `open source tool to rank in ChatGPT and Perplexity` |
| 2026-08-24 | 3/10 | false | harness only (the extra 2026-08-17 hit did not hold) |

The two branded queries (`eGEOagents`, `eGEOagents GitHub`) were true from day one. They do not count as category visibility.

Single-run answers vary. 3/10 on 2026-08-24 is one sample, not a trend. We do not launch a course off it.

## What actually changed off-repo

On-repo metadata was already exhausted by 2026-08-05. After that we shipped external surfaces:

| Surface | When | Status |
|---|---|---|
| Docs site [egeoagents.com](https://egeoagents.com) | 2026-08 | live |
| [LibHunt listing](https://www.libhunt.com/r/eGEOagents) | 2026-08-09 | live, auto-approved |
| GitHub Sponsors + a $199 GEO audit | 2026-08 | live |
| [`egeo` on PyPI](https://pypi.org/project/egeo/) | 2026-08-31 | live (`pip install egeo`) |

GitHub stars moved 147 → 168 over the same window. The head query did not. Stars were never the bottleneck — projects with 17–37 stars already appeared in that answer because they were in the sources Perplexity cites.

## What we still cannot claim

- We are **not** in the head-query ranking. geo-optimizer-skill, geo-lint, xanlens, open-geo, GEO-optim/GEO, and the izak-fisher / amplifying-ai lists still are.
- The 2026-08-17 extra generic mention **regressed** the following week.
- PyPI shipped *after* the last snapshot. It cannot be credited for 3/10.
- arXiv:2511.20867 is a **preprint**, not a peer-reviewed paper. The peer-reviewed GEO anchor is Aggarwal et al., KDD 2024 ([arXiv:2311.09735](https://arxiv.org/abs/2311.09735)).
- E-GEO consumes MCP servers as a **client**. It is not an MCP server.
- Indexation, crawl, and citation are different events. We do not claim Google or Perplexity will index or cite a URL because we asked.

## Method, so you can repeat it

1. Freeze 8–10 queries. Do not edit them week to week.
2. Ask the same engine. Record mention yes/no, competitors named, and **cited domains**.
3. Treat cited domains as the distribution list. In this category that was LibHunt first, then awesome-lists and dated comparison pages.
4. Do not read a branded hit as a category win.
5. Re-run a one-week spike before acting on it.

The playbook distilled from this log is in [How to get cited by Perplexity](/guides/rank-in-perplexity/). The research lineage is on [/research/](/research/).

## Next measurement

The next weekly snapshot is 2026-08-31. Gate A in our public plan is **≥3/10 sustained or ≥300 GitHub stars**. Today: 3/10 on one later snapshot, 168 stars. Neither bar is met.

---

**In short:** a GEO tool with a polished README still does not exist to Perplexity until curator sources name it. We measured that on ourselves. The head query remains unanswered by us. [Install `egeo`](https://pypi.org/project/egeo/) or read the [source](https://github.com/mverab/eGEOagents).
