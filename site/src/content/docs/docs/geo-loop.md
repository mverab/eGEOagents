---
title: GEO Loop
description: Continuous GEO — loop mode watches your domains over time with deterministic collectors and a persistent workspace ($EGEO_HOME).
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "E-GEO Loop Mode: Continuous GEO",
        "description": "Loop mode watches your domains over time with deterministic collectors and a persistent workspace ($EGEO_HOME).",
        "url": "https://egeoagents.com/docs/geo-loop/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

One-shot GEO answers *"how is this page doing today?"*. **Loop mode** answers *"what changed, and what should I do about it?"* — week after week, without you asking. It is fully opt-in: `/geo <url>` and `egeo optimize` behave exactly as before and never need a workspace.

## The workspace (`$EGEO_HOME`)

All loop state lives **outside the repo**, in the workspace resolved from `$EGEO_HOME` (default `~/.egeo/`), so `git pull` never touches your data:

```
$EGEO_HOME/
├── LOG.md                        # append-only activity feed (one line per event)
├── config.yaml                   # cadence, models, budgets, scaling weights
├── project.yaml                  # project identity, targets, guardrails (optional migration)
├── SUBSTRATE.md                  # the contract, vendored on bootstrap
├── signals/<slug>.md             # evidence — deduped, frequency-counted
├── docs/<slug>.md                # durable knowledge — analyses, decisions
├── data/<collector>/*.jsonl      # raw collector output (not artifacts)
├── domains/<loop>/README.md      # charter: focus, backlog, run Timeline
└── prompts/                      # optimized prompts (repo prompts/ stay pristine)
```

The layout and artifact rules are defined by `SUBSTRATE.md` and mechanically enforced by `python -m egeo.substrate_lint`.

### Portable project contract

`project.yaml` is the portability boundary. It describes the active project's
canonical domain, tracked queries, tracked pages, measurement engines, and
anti-spam/canibalization guardrails. `config.yaml` remains the loop machinery
(cadence, models, budgets, and reflection). When `project.yaml` exists, it is
validated before collection and takes precedence over legacy project fields in
`config.yaml`; explicit CLI flags still win. If it is absent, the legacy
configuration remains runnable and `egeo loop doctor` reports the fallback.

Copy the shape from [`examples/project.yaml`](https://github.com/mverab/eGEOagents/blob/main/examples/project.yaml).
The contract contains no API keys, OAuth tokens, or private Search Console data.

`egeo loop decide` ranks **one** next action from that contract plus collector JSONL and `$EGEO_HOME/data/outcomes/ledger.jsonl`. It is LLM-free and never publishes. `--dry-run` writes nothing.

## Commands

| Command | What it does |
|---------|--------------|
| `egeo loop doctor` | Bootstrap the workspace if missing, then health-check it (layout, config, budgets, substrate lint) |
| `egeo loop decide` | Rank exactly one next action from collector JSONL + the outcome ledger (LLM-free; never publishes) |
| `egeo loop collect serp` | Record a search-result snapshot (Brave API) into `data/serp/*.jsonl` |
| `egeo loop collect page` | Record a page snapshot (hash, title, meta, JSON-LD types, word count) into `data/page/*.jsonl` |
| `egeo loop run <domain>` | Resolve and print the run plan — current focus, fresh collector deltas, candidate signals |
| `/geo:loop <domain>` | Execute one bounded loop iteration in Claude Code (the agent does the interpretive work) |

## Walkthrough

```bash
# 1. Create the workspace
egeo loop doctor

# 2. Describe what you want watched: $EGEO_HOME/domains/example-com/README.md
#    (## Charter, ## Cadence, ## Current focus, ## Backlog, ## Timeline)

# 3. Collect ground truth
export BRAVE_API_KEY=<YOUR_BRAVE_API_KEY>
egeo loop collect serp --query "best geo tool" --target-domain example.com
egeo loop collect page --url https://example.com/pricing

# 4. See what a run would do — writes nothing
egeo loop run example-com --dry-run

# 5. Do the run (Claude Code, or headless)
claude -p "/geo:loop example-com"
```

`egeo loop run` is **LLM-free by design** — it is the trigger seam that prepares and validates the plan. The reasoning happens in the `geo-loop` skill, which enforces the run contract.

## The run contract

One wake-up performs at most **one** unit of work from the domain's `## Current focus` or `## Backlog`, appends exactly **one** `### YYYY-MM-DD run` Timeline entry ending in `Outcome: success|partial|failure|no-op`, appends exactly **one** `LOG.md` line, and verifies both writes before exiting.

## Collectors

Collectors are the loop's senses: deterministic, LLM-free, budget-aware, and append-only. Every collector honors the same 10-point contract — write JSONL to `$EGEO_HOME/data/<name>/`, one record per observation with a `schema_version`, respect the daily budget in `config.yaml`, append exactly one `LOG.md` line per pass, and **fail loudly** instead of writing a partial or fabricated record.

| Collector | Needs | Output |
|-----------|-------|--------|
| `serp` | `BRAVE_API_KEY` | Top-10 results per query + your target's position |
| `page` | nothing | `content_hash`, title, meta description, JSON-LD types, word count |

Both accept `--fixture` for offline, deterministic runs — that is how they are tested without touching the network.

## Scheduling

Any scheduler drives the same commands. Pin provider and model per job; jobs more frequent than weekly deliver locally, and one weekly digest does the notifying:

```
# hourly — local delivery only (JSONL + LOG line, no notification)
0 * * * *   egeo loop collect page --url https://example.com/pricing

# daily — one bounded loop run
30 6 * * *  claude -p "/geo:loop example-com"

# weekly — the only job that pings you
0 9 * * 1   claude -p "Summarize $EGEO_HOME/LOG.md for the past 7 days"
```

## See also

- [CLI Reference](/docs/cli/) — full `egeo loop` flag reference
- [MCP Server](/docs/mcp-server/) — the validation layer behind SERP ground truth
- [Evaluation Harness](/docs/evaluation/) — measuring prompt quality over time
