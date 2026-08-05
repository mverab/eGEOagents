---
title: Getting Started
description: Install E-GEO as a Python CLI or as Claude Code skills and run your first GEO optimization in minutes.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "Getting Started with E-GEO",
        "description": "Install E-GEO as a Python CLI or as Claude Code skills and run your first GEO optimization.",
        "url": "https://egeoagents.com/docs/getting-started/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]},
        "about": {"@type": "SoftwareApplication", "name": "E-GEO", "codeRepository": "https://github.com/mverab/eGEOagents"}
      }
---

E-GEO runs in two ways: as a **standalone Python CLI** (`egeo`) or as a set of **Claude Code agents and skills**. Both share the same optimization logic — there is one source of truth.

## Prerequisites

- Python 3 for the standalone CLI, or [Claude Code](https://claude.com/claude-code) for the agent workflow
- A content file or website URL you want to optimize
- Optional: an OpenAI-compatible API key for real model runs (`GEO_EVAL_MOCK=1` works without one)

## Installation

### Option 1: Standalone Python CLI

```bash
git clone https://github.com/mverab/eGEOagents.git
cd eGEOagents
pip install -e .
```

Or run without installing:

```bash
pip install pyyaml jsonschema
python -m egeo --help
```

### Option 2: Claude Code skills (skills.sh)

```bash
npx skills add https://github.com/mverab/eGEOagents
```

Install a single skill:

```bash
npx skills add https://github.com/mverab/eGEOagents --skill competitive-analysis
```

Available skills: `competitive-analysis`, `content-scoring`, `schema-generator`, `validation-doctor`, `geo-loop`. Collection page: [skills.sh/mverab/egeoagents](https://skills.sh/mverab/egeoagents).

### Option 3: Copy the `.claude/` folder

```bash
git clone https://github.com/mverab/eGEOagents.git
cp -r eGEOagents/.claude /path/to/your/project
```

## First optimization

### With the CLI

```bash
# Deterministic offline run — no API key needed
GEO_EVAL_MOCK=1 egeo optimize examples/sample-input.md --out-dir ./geo-output

# Real run (requires OPENAI_API_KEY)
egeo optimize path/to/page.md --query "best geo tool" --schema-type Article
```

### With Claude Code

```
/output-style geo-optimizer
/geo https://yoursite.com
```

## What you get

Both paths write a complete optimization package to `geo-output/`:

```
geo-output/
├── report.md           # Executive summary with scores
├── analysis.json       # Raw analysis data
├── optimized/
│   └── yoursite.md     # Rewritten, GEO-optimized content
├── schema/
│   └── yoursite.json   # JSON-LD schema markup
└── checklist.md        # Step-by-step implementation guide
```

Copy the optimized content and schema to your website.

## What happens during optimization

E-GEO runs 4 specialized agents in sequence:

| Agent | What it does | Output |
|:------|:-------------|:-------|
| **Analyzer** | Extracts content, scores GEO signals, finds gaps | `analysis.json` |
| **Ranker** | Simulates AI-engine ranking, predicts position | Baseline score |
| **Rewriter** | Optimizes content while preserving brand voice | `optimized/*.md` |
| **Indexer** | Generates schema markup and technical assets | `schema/*.json` |

## Next steps

- [How It Works](/docs/how-it-works/) — technical deep dive
- [CLI Reference](/docs/cli/) — every `egeo` subcommand and flag
- [GEO Loop](/docs/geo-loop/) — continuous optimization over time
- [FAQ](/docs/faq/) — common questions
- [E-GEO research paper](https://arxiv.org/abs/2511.20867) — the methodology
