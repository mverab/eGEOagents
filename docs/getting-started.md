# Getting Started with E-GEO

> Transform any website into AI-search-optimized content in 3 steps.

---

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed
- A website URL you want to optimize
- Optional: MCP servers configured for validation ([see setup](USAGE.md#mcp-setup))

---

## Installation

### Option 1: Clone the repository

```bash
git clone https://github.com/mverab/eGEOagents.git
cd eGEOagents
```

Copy the `.claude/` folder to your project:

```bash
cp -r eGEOagents/.claude .
```

### Option 2: Install as skills (skills.sh)

```bash
npx skills add https://github.com/mverab/eGEOagents
```

Install a single skill:

```bash
npx skills add https://github.com/mverab/eGEOagents --skill competitive-analysis
```

---

## Quick Start

### Step 1: Activate GEO Mode

In Claude Code, switch to the GEO output style:

```
/output-style geo-optimizer
```

### Step 2: Optimize a Website

Run the full pipeline on any URL:

```
/geo https://yoursite.com
```

### Step 3: Deploy Results

E-GEO generates a complete optimization package in `geo-output/`:

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

---

## What Happens During Optimization

E-GEO runs 4 specialized agents in sequence:

| Agent | What it does | Output |
|:------|:-------------|:-------|
| **Analyzer** | Extracts content, scores GEO signals, finds gaps | `analysis.json` |
| **Ranker** | Simulates AI-engine ranking, predicts position | Baseline score |
| **Rewriter** | Optimizes content while preserving brand voice | `optimized/*.md` |
| **Indexer** | Generates schema markup and technical assets | `schema/*.json` |

---

## Next Steps

- Read [How It Works](how-it-works.md) for a technical deep dive
- Check the [FAQ](faq.md) for common questions
- See [USAGE.md](../USAGE.md) for the complete command reference
- Review the [E-GEO research paper](https://arxiv.org/abs/2511.20867) for methodology

---

## See Also

- [How It Works](how-it-works.md) — Technical architecture and agent design
- [FAQ](faq.md) — Common questions and troubleshooting
- [Skills.sh Playbook](skills-sh-playbook.md) — Listing, ranking, and metadata checklist
- [USAGE.md](../USAGE.md) — Complete command reference
- [Contributing](../CONTRIBUTING.md) — How to contribute to E-GEO

---

*Built for the AI-first web. Based on research from [arXiv:2511.20867](https://arxiv.org/abs/2511.20867).*
