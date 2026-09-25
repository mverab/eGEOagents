---
title: How to Track Whether AI Engines Cite You
description: How to measure if ChatGPT, Perplexity and Gemini cite your site — a free fixed-query method, open-source trackers, and hosted AI visibility tools — and how to act on the results with E-GEO.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "How to Track Whether AI Engines Cite You",
        "description": "Measure AI citations with a fixed query set, open-source trackers or hosted AI visibility tools, then fix the pages that lose with E-GEO.",
        "url": "https://egeoagents.com/guides/track-ai-citations/",
        "datePublished": "2026-09-24",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

**Last verified: 2026-09-24.** E-GEO rewrites pages so answer engines can cite them. It does not ship its own citation tracker. This page covers how to measure the result: the free method we use ourselves, the open-source trackers, and the hosted tools.

## Why measure citations at all

Rankings in Google tell you little about AI answers. An AI engine gives one synthesized answer and names a handful of sources. Your question is binary: **for the queries your customers ask, is your site one of the named sources?** Without measuring that, any GEO work is guesswork.

## Option 1 — A fixed query set (free, what we use)

This is the method behind our [public case study](/case-study/):

1. Pick **10 queries** your customers actually ask. Mix branded (`<your product> github`), category (`best open source <category> tools`) and problem queries (`how to <job your product does>`).
2. Run them against one engine on a **fixed schedule** (we use Perplexity's API weekly) and record, per query: whether you are mentioned, which competitors are mentioned, and which source domains are cited.
3. Store every run as a dated snapshot. **Discard runs with empty answers** — a failed API call looks like "not cited".
4. Read the trend, not a single run. One snapshot can move by 1–2 queries on noise alone.

The cited source domains matter as much as your score: they are the sites you need to be mentioned on (see [how to get cited by Perplexity](/guides/rank-in-perplexity/)).

## Option 2 — Open-source trackers

| Tool | What it does (per its README) | License |
|---|---|---|
| [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | `geo citations` checks real answer engines for your brand and domain; `geo monitor` / `geo track` keep a history | MIT |
| [Elmo](https://github.com/elmohq/elmo) | Self-hostable tracking of mentions and citations across ChatGPT, Claude, Perplexity, Gemini, Copilot, Grok and AI Overviews | MIT |
| [GEORank](https://github.com/yaojingang/GEORank) | GEO ranking and optimization platform | Apache-2.0 |

Expect to bring your own API keys and a machine to run them on. Full list: [open-source GEO tools directory](/compare/geo-tools-2026/).

## Option 3 — Hosted AI visibility tools

If you would rather not run anything, hosted tools track many prompts across engines and show trends in a dashboard:

- [Profound](https://www.tryprofound.com/) — enterprise AI visibility platform.
- [Peec AI](https://peec.ai/) — AI search analytics for marketing teams and agencies.
- [Otterly](https://otterly.ai/) — AI search monitoring with an API.
- [Rankscale](https://rankscale.ai/) — AI search rank tracking with an API.
- [LLM Pulse](https://llmpulse.ai/) — AI visibility tracking with API access.
- [AIclicks](https://aiclicks.io/) — AI visibility tracking; plans listed from $59/month.

We have not benchmarked these against each other. Try two on the same 10 queries before committing.

## Turn measurements into fixes

Tracking only helps if it changes what you publish. The loop:

1. **Measure** with any option above.
2. **Pick the losers**: queries where competitors are cited and you are not.
3. **Fix the page** that should answer that query. For one page:

```bash
pip install egeo
egeo optimize your-page.md --query "best open source geo tools"
```

   Or feed the whole tracker report to [`egeo fix-gaps`](/docs/cli/#egeo-fix-gaps), which maps every uncited query to its page through `project.yaml` and rewrites each losing page once (new in the next release; install from GitHub until then: `pip install git+https://github.com/mverab/eGEOagents`).

4. **Get mentioned on the cited sources** for that query — on-page fixes alone rarely flip a citation.
5. **Re-measure** on the next scheduled run, and keep the dated snapshots.

It is the same loop we run on E-GEO itself; the method and snapshots are in the [case study](/case-study/).
