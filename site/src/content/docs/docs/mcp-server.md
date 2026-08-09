---
title: MCP-Based Validation
description: How E-GEO's Claude Code workflow consumes external MCP servers for validation — Brave Search for competitor ground truth and Chrome DevTools for rendered-DOM checks.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "E-GEO and MCP-Based Validation",
        "description": "How E-GEO's Claude Code workflow consumes external MCP servers for validation: Brave Search for competitor ground truth and Chrome DevTools for rendered-DOM checks.",
        "url": "https://egeoagents.com/docs/mcp-server/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

E-GEO integrates with the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) as a client-side validation workflow. When running through Claude Code, E-GEO consumes external MCP servers as its validation layer; E-GEO is not itself an MCP server.

## Why MCP matters for GEO

A GEO tool that claims competitor rankings without checking real search results is guessing. E-GEO's rule: **do not claim competitor rankings without search ground truth.** The configured external MCP servers provide that ground truth.

## Required servers for fully validated results

| Server | Purpose | Criticality |
|--------|---------|-------------|
| `brave-search` | Market validation — competitor analysis, SERP data | High |
| `chrome-devtools` | Technical validation — rendered DOM, performance | High |
| `fetch` | Simple text scraping (fallback) | Medium |

## Behavior without MCP

E-GEO still runs if these servers are missing. It falls back to available tools (e.g. `fetch` / raw HTML) and clearly labels outputs as **"Low Confidence"**. You get results either way — you just know how much to trust them.

## Setup

1. Add Brave Search and Chrome DevTools MCP servers to your Claude Code MCP configuration.
2. The `serp` collector (used by [loop mode](/docs/geo-loop/)) also talks to the Brave API directly and needs `BRAVE_API_KEY` in the environment.
3. Run the `validation-doctor` skill — it checks your MCP dependencies and prints exact setup commands for anything missing:

```bash
npx skills add https://github.com/mverab/eGEOagents --skill validation-doctor
```

## Validation flow

During a `/geo <url>` run:

1. **Analyzer** fetches the page (MCP fetch or web-reader fallback).
2. **Ranker** pulls real SERP data via `brave-search` to position your content against actual competitors.
3. **Indexer** can verify the rendered DOM via `chrome-devtools` — what AI crawlers actually see after JavaScript runs, not just raw HTML.
4. Any step that had to run without its preferred server marks its section of the report **Low Confidence**.

## See also

- [How It Works](/docs/how-it-works/) — where validation sits in the pipeline
- [GEO Loop](/docs/geo-loop/) — the deterministic collectors that use the same data sources
- [FAQ](/docs/faq/) — troubleshooting MCP warnings
