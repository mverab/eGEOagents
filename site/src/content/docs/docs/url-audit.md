---
title: Free URL Audit
description: How the free URL audit on egeoagents.com works — seven deterministic checks, the 10 GEO features as a heuristic, and one section rewritten under fidelity rules. What it measures and what it does not.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "How the E-GEO Free URL Audit Works",
        "description": "Seven deterministic checks, the 10 GEO features as a heuristic, and one section rewritten under fidelity rules.",
        "url": "https://egeoagents.com/docs/url-audit/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

Paste a URL into the form on the [home page](/) and you get a report in under 30 seconds. You don't need an account or an email. The report link lasts 24 hours, then it is deleted.

## What the report contains

**1. Seven technical checks.** None of them uses an LLM. Each check reports `pass`, `fail` or `unverifiable`, shows the evidence it observed, and gives a one-line fix when it fails.

| Check | Passes when |
|---|---|
| AI crawler access | `robots.txt` lets `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `PerplexityBot` and `Google-Extended` read the page. No `robots.txt` at all also counts as a pass. |
| `/llms.txt` | The site serves a non-HTML [`/llms.txt`](/concepts/what-is-llms-txt/). |
| JSON-LD | At least one JSON-LD block declares an `@type`. |
| `<title>` | The page has a non-empty title. |
| Meta description | The page has a non-empty `<meta name="description">`. |
| One `<h1>` | The page has exactly one `h1`. |
| Visible text | The page shows at least 150 words without running JavaScript. |

`unverifiable` (for example, `robots.txt` timed out) is shown as its own status. It never counts as a pass or a fail.

**2. The [10 GEO features](/concepts/geo-features/), scored 0–10.** These scores come from E-GEO's offline Analyzer, which is a **keyword heuristic**. They tell you which signals the text expresses. They do not predict how ChatGPT, Perplexity or any other engine will rank the page.

**3. One section, rewritten.** The audit picks the weakest section of 40–600 words and rewrites it for your target query. If you leave the query empty, it uses "best" + the page title.

The rewrite goes through the same deterministic fidelity rules as `egeo fix-gaps` section mode. A rewrite fails if it:
- changes the heading;
- adds or removes a link;
- adds or removes a number;
- drops a table row;
- changes a code block;
- changes the length too much.

A rewrite that breaks a rule is **withheld**, and the report lists the rules it broke. No LLM judge checks the rewrite, and the report says so.

## What it does not do

- **No single score.** Each audit tool scores the same site differently because each uses its own rubric. The E-GEO report shows only the breakdown and the evidence behind it.
- **No ranking or citation measurement.** To see whether answer engines actually cite you, use a tracker ([how to track AI citations](/guides/track-ai-citations/)), then turn the gaps it finds into rewrites with `egeo fix-gaps`.
- **No JavaScript rendering.** Pages that render their content in the browser fail the visible-text check, and usually get no rewrite.
- **One page, one section.** To audit a whole site, rewrite whole pages, or generate schema, use the toolkit: `pip install egeo`, or `/geo <url>` in Claude Code.

## Limits and privacy

- **Per-IP limit:** each IP can run 5 audits per UTC day. Running the same URL and query again within an hour returns the cached report, and it doesn't count toward your limit.
- **Rewrite cap:** the number of free rewrites per day is capped for all visitors together. When the cap is reached, the audit still runs and the report says the rewrite was skipped.
- **What is stored:** the audited URL, the query and the report, for 24 hours. IP counters are stored only as a salted hash, and the salt changes daily. No raw IPs, emails or cookies are kept.
- **What is fetched:** the audit fetches only the page, `/robots.txt` and `/llms.txt`, from public addresses. The requests carry the user agent `egeo-audit/1.0`.

The service is open source: `egeo/url_audit.py` and `egeo/audit_service.py` in the [repository](https://github.com/mverab/eGEOagents).
