<div align="center">

<!-- HERO BANNER -->
<img src="assets/hero-banner.png" alt="E-GEO: Rank #1 in AI Search Engines" width="100%" />

<br />

# 🌍 E-GEO

### **Generative Engine Optimization (GEO)** & **Answer Engine Optimization (AEO)** for AI-Powered Search

<p>
  <a href="https://github.com/mverab/eGEOagents/actions/workflows/ci.yml"><img src="https://github.com/mverab/eGEOagents/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" /></a>
  <a href="https://github.com/mverab/eGEOagents/stargazers"><img src="https://img.shields.io/github/stars/mverab/eGEOagents?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/mverab/eGEOagents/network/members"><img src="https://img.shields.io/github/forks/mverab/eGEOagents?style=social" alt="GitHub Forks" /></a>
  <a href="https://github.com/mverab/eGEOagents/issues"><img src="https://img.shields.io/github/issues/mverab/eGEOagents" alt="Issues" /></a>
  <a href="https://arxiv.org/abs/2511.20867"><img src="https://img.shields.io/badge/arXiv-2511.20867-b31b1b.svg" alt="Research Paper" /></a>
</p>

<p>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Built%20with-Claude%20Code-8B5CF6?logo=anthropic" alt="Built with Claude Code" /></a>
  <a href="CONTRIBUTING.md#ai-transparency"><img src="https://img.shields.io/badge/🤖-AI--Assisted-blueviolet" alt="AI-Assisted" /></a>
</p>

<br />

> **🚀 One command. Premium results.**<br />
> Rank higher in **ChatGPT**, **Perplexity**, **Claude**, and **Gemini**.

<br />

[**📖 Docs**](docs/getting-started.md) • [**🐛 Issues**](https://github.com/mverab/eGEOagents/issues) • [**💬 Discussions**](https://github.com/mverab/eGEOagents/discussions) • [**📝 Research Paper**](https://arxiv.org/abs/2511.20867)

---

</div>

<!-- AI TRANSPARENCY BADGE -->
<p align="center">
  <sub>🤖 <strong>AI-Assisted Development</strong> — <a href="CONTRIBUTING.md#ai-transparency">See what's AI-generated vs human-authored</a></sub>
</p>

---

## ✨ What is E-GEO?

<table>
<tr>
<td width="60%">

**E-GEO** is an open-source **Generative Engine Optimization (GEO)** and **Answer Engine Optimization (AEO)** toolkit that transforms your website content to rank higher in AI-powered search engines — including **ChatGPT**, **Perplexity**, **Google AI Overviews**, **Claude**, and **Gemini**.

Also known as **AI SEO** or **LLM SEO**, GEO is the practice of optimizing content so that generative AI engines can crawl, understand, cite, and recommend it. E-GEO automates this entire process.

Based on the [E-GEO research paper](https://arxiv.org/abs/2511.20867) (arXiv:2511.20867), it applies the **10 universal features** that consistently improve AI-engine rankings — competitive framing, citation optimization, structured data, and semantic density improvements backed by peer-reviewed findings.

- ✅ **No learning curve** — One command to optimize
- ✅ **Research-backed** — Based on peer-reviewed findings
- ✅ **Production-ready** — Copy-paste optimized content
- ✅ **Multi-engine** — Optimizes for ChatGPT, Perplexity, Gemini, Claude & Google AI Overviews
- ✅ **Full pipeline** — Analyze → Rank → Rewrite → Schema in one command

</td>
<td width="40%">

```bash
/geo https://yoursite.com/pricing
```

↓

```
geo-output/
├── report.md
├── optimized/
│   └── pricing.md
└── schema/
    └── pricing.json
```

</td>
</tr>
</table>

---

## 📈 Why AI Visibility Matters in 2026

AI search engines give one synthesized answer and cite a handful of sources. If your site isn't one of them, you're invisible — even if you rank #1 on Google.

```
User asks ChatGPT: "What's the best GEO tool?"

ChatGPT: "According to [Competitor], the best tool is..."
          ↑ They get cited. You don't.
```

- **ChatGPT serves 900M+ weekly users** — a growing share of sessions that used to be Google searches.
- **28.3% of ChatGPT's most-cited pages have *zero* organic visibility on Google** (Ahrefs) — AI engines reward different signals than classic SEO.
- **Proper JSON-LD schema lifts LLM extraction accuracy from 16% to 54%** (Semrush study on GPT-4).
- **844,000+ sites** already ship an `llms.txt`. Is yours one of them?

Traditional SEO optimizes for blue links. **GEO optimizes for citations in AI-generated answers.** E-GEO is the open-source tool that bridges this gap.

---

## 🚀 Quick Start (3 Steps)

### 1. Install

Copy the `.claude/` folder to your project:

```bash
cp -r /path/to/eGEOagents/.claude .
```

### 2. Activate

In Claude Code, switch to GEO mode:

```
/output-style geo-optimizer
```

### 3. Optimize

Run your first optimization:

```
/geo https://yoursite.com
```

---

## 🧩 Install as Skills (skills.sh)

Install the complete skill collection:

```bash
npx skills add https://github.com/mverab/eGEOagents
```

Install one skill only:

```bash
npx skills add https://github.com/mverab/eGEOagents --skill competitive-analysis
```

Validate parser discovery before shipping updates:

```bash
npx skills add https://github.com/mverab/eGEOagents --list
```

Verify indexing pages:

- Collection: [skills.sh/mverab/egeoagents](https://skills.sh/mverab/egeoagents)
- Owner: [skills.sh/mverab](https://skills.sh/mverab)

---

## 📋 Commands

| Command | What it does |
|---------|--------------|
| `/geo <url>` | **Full pipeline** - Analyze, rank, rewrite, schema |
| `/geo:audit <url>` | Analysis only, no changes |
| `/geo:optimize <file>` | Optimize local content file |
| `/geo:batch <folder>` | Process entire folder |
| `/geo:report` | Generate executive report |
| `/geo:compete <query>` | Competitive analysis |

---

## 📊 What You Get

After running `/geo`:

```
geo-output/
├── report.md           # Executive summary + scores
├── analysis.json       # Raw analysis data
├── optimized/
│   └── pricing.md      # Rewritten content (ready to use)
├── schema/
│   └── pricing.json    # JSON-LD markup (copy to site)
└── checklist.md        # Step-by-step implementation
```

---

## 🎯 Results: Backed by Research

E-GEO is grounded in peer-reviewed research from the [E-GEO research paper](https://arxiv.org/abs/2511.20867) (arXiv:2511.20867), building on foundational work by [Aggarwal et al. (Princeton, KDD 2024)](https://arxiv.org/abs/2311.09735) — the original study that defined Generative Engine Optimization as a discipline.

The E-GEO paper reports that:

1. **Competitive framing** produces the strongest immediate ranking lift among all GEO strategies tested.
2. A **universal optimization strategy** (applying all 10 features together) outperforms individual heuristics by a wide margin.
3. The **10 GEO features** (ranking emphasis, user intent matching, competitive edge, social proof, authority signals, scannability, citation density, structured data, factual language, and freshness) consistently appear in higher-ranking content across ChatGPT, Perplexity, and Gemini.

| Feature | What E-GEO Does |
|---------|-----------------|
| **Ranking Emphasis** | Positions your content as the top choice |
| **User Intent** | Directly answers what users are looking for |
| **Competitive Edge** | Highlights your unique advantages |
| **Social Proof** | Integrates trust signals and testimonials |
| **Authority** | Establishes expert, confident tone |
| **Scannability** | Structures for easy AI parsing |

Results vary by content quality and competition. See the paper for full methodology and findings: [arXiv:2511.20867](https://arxiv.org/abs/2511.20867).

---

## 🧪 Reproducible Results

E-GEO ships an evaluation harness so you can measure prompt quality yourself —
no trust required. It scores whether the GEO rewriter moves a target item *up*
in an LLM-simulated ranking.

```bash
pip install pyyaml jsonschema

# Deterministic, offline smoke run (no API key needed)
GEO_EVAL_MOCK=1 python geo_eval.py evaluate \
  --dataset eval/datasets/geo_smoke.jsonl --limit 5 --verbose
```

This is the exact check that runs in [CI](.github/workflows/ci.yml) on every
pull request. Reported metrics: `avg_rank_improvement`, `win_rate`, and
`stderr_rank_improvement`.

> **Honest scope:** these numbers are a **proxy** produced by an LLM-ranker, not
> a measurement of real ChatGPT/Perplexity rankings. See
> **[docs/evaluation.md](docs/evaluation.md)** for the full methodology,
> metric definitions, and limitations.

---

## 🖥️ Standalone CLI (`egeo`)

Beyond Claude Code, E-GEO ships a **runtime-agnostic command line** so the same
GEO engine runs anywhere Python runs — local shells, notebooks, Docker, or CI.
The CLI is a thin wrapper around the **exact same** `geo_eval.py` and
`llm_client.py` modules used by the Claude Code agents, so there is **no
duplicated optimization logic** — both runtimes share one source of truth.

### Install

```bash
# From the repo root — installs the `egeo` console script + deps
pip install -e .

# ...or run without installing (deps: pip install pyyaml jsonschema)
python -m egeo --help
```

### Commands

| Command | What it does |
|---------|--------------|
| `egeo optimize <file>` | **Full pipeline** — analyze → rank → rewrite → schema, writes `report.md`, `optimized/*.md`, `schema/*.json`, `analysis.json` |
| `egeo evaluate` | Run the evaluation harness (reuses `geo_eval.py`, identical metrics) |
| `egeo optimize-prompts` | Meta-optimize the rewriter prompt (non-destructive by default) |
| `egeo runtimes` | List available runtime adapters and their status |

```bash
# Optimize a local content file (output dir defaults to ./geo-output)
egeo optimize examples/sample-input.md --out-dir ./geo-output

# Score prompt quality on a dataset
egeo evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5

# Inspect the runtime adapters
egeo runtimes
```

### Offline / deterministic mode

Every command honors `GEO_EVAL_MOCK=1`, which swaps in a deterministic mock LLM
client — **no API key required**. This is exactly how the CLI is exercised in
[CI](.github/workflows/ci.yml):

```bash
GEO_EVAL_MOCK=1 egeo optimize examples/sample-input.md --out-dir /tmp/egeo
GEO_EVAL_MOCK=1 egeo evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 3
```

### Supported Runtimes

E-GEO exposes a small **runtime adapter** layer so the same agents (Analyzer,
Ranker, Rewriter, Indexer) can be driven by different execution hosts:

| Runtime | Aliases | Mode | Status | Description |
|---------|---------|------|:------:|-------------|
| **`python`** | `cli`, `local` | in-process | ✅ Available | Pure-Python runtime behind the `egeo` CLI. Runs the full pipeline in-process and honors `GEO_EVAL_MOCK` for offline, deterministic runs. |
| **`claude-code`** | `claude` | host-executed | ✅ Available | Executes the `.claude/` agents through Claude Code `/geo` slash commands on the host. Auto-detected when a `.claude/` directory is present. |

> Run `egeo runtimes` to print the live status of each adapter in your
> environment. Additional hosts (Cursor, Codex, Windsurf, …) can be added by
> implementing the `RuntimeAdapter` interface in
> [`egeo/runtimes.py`](egeo/runtimes.py).

---

## 🆚 E-GEO vs Other GEO Tools

| Feature | E-GEO | GEO Optimizer | GEO-optim/GEO | Awesome GEO | Traditional SEO |
|---------|-------|---------------|---------------|-------------|----------------|
| **Type** | CLI + Claude Code | CLI + MCP | Research repo | Curated list | — |
| **Content Rewriting** | ✅ Full pipeline | ⚠️ Audit only | ❌ | ❌ | ❌ No |
| **AI-Ranking Simulation** | ✅ LLM-based | ❌ | ❌ | ❌ | ❌ No |
| **Schema Generation** | ✅ Auto JSON-LD | ⚠️ Partial | ❌ | ❌ | ❌ Manual |
| **Competitive Analysis** | ✅ Built-in | ❌ | ❌ | ❌ | ❌ No |
| **Academic Foundation** | ✅ [arXiv:2511.20867](https://arxiv.org/abs/2511.20867) | ✅ KDD 2024 | ✅ Original GEO paper | ❌ | ❌ Heuristics |
| **Multi-Runtime** | ✅ Python + Claude Code | ✅ Python + MCP | ❌ | ❌ | ❌ |
| **llms.txt Support** | ✅ | ✅ | ❌ | 📖 Listed | ❌ |
| **Cost** | Free / MIT | Free / MIT | Free | Free | Expensive |

> **E-GEO is the only open-source GEO tool that combines content rewriting, ranking simulation, and schema generation in a single pipeline.** Others focus on auditing or listing — E-GEO does the full optimization.

---

## 💎 Premium Output

E-GEO delivers outputs that look like they came from a $100M company:

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 GEO AUDIT REPORT                                        │
├─────────────────────────────────────────────────────────────┤
│  URL: yoursite.com/pricing                                  │
│  Score: 78/100                                              │
│  Ranking Potential: ████████░░ 78%                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ STRENGTHS                                               │
│  • Clear value proposition                                  │
│  • Good content structure                                   │
│                                                             │
│  ⚠️ GAPS                                                    │
│  • Missing social proof → Add customer count                │
│  • No urgency signals → Add limited-time offer              │
│                                                             │
│  📈 PRIORITY ACTIONS                                        │
│  1. Add testimonials (+15 points)                           │
│  2. Include pricing comparison (+10 points)                 │
│  3. Add schema markup (+5 points)                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 How It Works

<div align="center">

<!-- SYSTEM DIAGRAM -->
<img src="assets/egeo-agents.png" alt="E-GEO Multi-Agent System" width="600" />

</div>

<br />

E-GEO uses **4 specialized AI agents** orchestrated by Claude Code:

| Agent | What it does | Output |
|:------|:-------------|:-------|
| 🔍 **Analyzer** | Extracts content, scores GEO signals, identifies gaps | `analysis.json` |
| 📊 **Ranker** | Simulates AI-engine ranking, predicts positions | Baseline score |
| ✍️ **Rewriter** | Optimizes content while preserving brand voice | `optimized/*.md` |
| 🗂️ **Indexer** | Generates schema markup and technical assets | `schema/*.json` |

---

## 📁 What's Included

```
.claude/
├── CLAUDE.md                    # System knowledge base
├── output-styles/
│   └── geo-optimizer.md         # Premium formatting mode
├── agents/
│   ├── geo-analyzer.md          # Content analysis
│   ├── geo-rewriter.md          # Content optimization
│   ├── geo-ranker.md            # Ranking simulation
│   └── geo-indexer.md           # Schema generation
├── skills/
│   ├── competitive-analysis/    # Auto-triggered competitor analysis
│   ├── content-scoring/         # Auto-triggered scoring
│   └── schema-generator/        # Auto-triggered schema
└── commands/
    ├── geo.md                   # Main command
    ├── geo-audit.md
    ├── geo-optimize.md
    ├── geo-batch.md
    ├── geo-report.md
    └── geo-compete.md
```

---

## 🎁 Perfect For

<table>
<tr>
<td align="center" width="20%">
🚀<br /><strong>SaaS Founders</strong><br /><sub>AI-engine traffic</sub>
</td>
<td align="center" width="20%">
💼<br /><strong>B2B Marketers</strong><br /><sub>Landing pages</sub>
</td>
<td align="center" width="20%">
🛍️<br /><strong>E-commerce</strong><br /><sub>Product descriptions</sub>
</td>
<td align="center" width="20%">
✍️<br /><strong>Content Creators</strong><br /><sub>AI discoverability</sub>
</td>
<td align="center" width="20%">
🏢<br /><strong>Agencies</strong><br /><sub>GEO services</sub>
</td>
</tr>
</table>

---

## 📚 Documentation

| Resource | Description |
|:---------|:------------|
| 📖 **[Getting Started](docs/getting-started.md)** | Step-by-step tutorial |
| ⚙️ **[How It Works](docs/how-it-works.md)** | Technical deep dive |
| ❓ **[FAQ](docs/faq.md)** | Common questions answered |
| 🧩 **[skills.sh Playbook](docs/skills-sh-playbook.md)** | Listing, ranking, and metadata checklist |
| 🧪 **[Evaluation Harness](docs/evaluation.md)** | Dataset format, commands, metrics, and honest limitations |
| 📝 **[Usage Guide](USAGE.md)** | Complete command reference |
| 📝 **[Research Paper](https://arxiv.org/abs/2511.20867)** | The science behind E-GEO |

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick ways to contribute:**
- Report bugs via [issues](https://github.com/mverab/eGEOagents/issues)
- Submit pull requests for features
- Improve documentation
- Share your GEO results

---

## 🔍 SEO & AI Search Glossary

E-GEO covers the full spectrum of AI search optimization. If you're searching for any of these, you're in the right place:

| Term | What it means |
|------|---------------|
| **GEO** (Generative Engine Optimization) | Optimizing content for AI answer engines like ChatGPT, Perplexity, Gemini |
| **AEO** (Answer Engine Optimization) | Structuring content so AI engines can parse and cite it |
| **AI SEO** | Adapting traditional SEO for AI-powered search |
| **LLM SEO** | Optimization specifically for large language model responses |
| **AI Visibility** | How often and how well your brand appears in AI-generated answers |
| **Citation Tracking** | Monitoring whether AI engines cite your site as a source |
| **llms.txt** | A standard file (like robots.txt) that tells AI crawlers what content to prioritize |

---

## 📜 License

MIT License - use it, modify it, sell with it. See [LICENSE](LICENSE) for details.

---

## 🙋 Support & Community

- **Issues:** [GitHub Issues](https://github.com/mverab/eGEOagents/issues)
- **Discussions:** [GitHub Discussions](https://github.com/mverab/eGEOagents/discussions)
- **Research:** [E-GEO Paper (arXiv:2511.20867)](https://arxiv.org/abs/2511.20867)

---

## 🚀 Ready to Rank Higher?

<div align="center">

```bash
# Install
cp -r eGEOagents/.claude .

# Activate (in Claude Code)
/output-style geo-optimizer

# Optimize your first page
/geo https://yoursite.com
```

<br />

<a href="https://github.com/mverab/eGEOagents">
  <img src="https://img.shields.io/badge/⭐-Star%20on%20GitHub-yellow?style=for-the-badge&logo=github" alt="Star on GitHub" />
</a>

<br /><br />

---

**Built for the AI-first web — optimize your content for ChatGPT, Perplexity, Claude, and Gemini with E-GEO, the open-source GEO tool.** 🌐

<sub>Made with ❤️ by <a href="https://verabadias.gumroad.com/">Vera Badias</a> • Based on research from <a href="https://arxiv.org/abs/2511.20867">arXiv:2511.20867</a></sub>

<sub>🤖 This project is AI-assisted. See <a href="CONTRIBUTING.md#ai-transparency">AI Transparency</a> for details.</sub>

</div>
