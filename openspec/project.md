# Project Context

## Purpose

E-GEO (Generative Engine Optimization) is a zero-effort system to optimize website content for AI-powered search engines (ChatGPT, Perplexity, Claude, Gemini).

**Core Promise:** Transform any website content into GEO-optimized assets with a single command (`/geo <url>`).

**Target Users:**
- SaaS founders wanting organic AI-engine traffic
- B2B marketers optimizing landing pages
- E-commerce optimizing product descriptions
- Content creators maximizing AI discoverability
- Agencies offering GEO services to clients

## Tech Stack

- **Runtime:** Claude Code (AI-powered IDE)
- **Content Format:** Markdown for all content files
- **Schema Markup:** JSON-LD for structured data
- **Metadata:** YAML frontmatter
- **Python:** `geo_eval.py`, `llm_client.py` for evaluation scripts
- **MCP Servers:** Brave Search, Chrome DevTools (for validation)

## Project Conventions

### Code Style

- Markdown for all content files
- JSON-LD for schema markup
- YAML frontmatter for metadata
- kebab-case for file names
- Clear hierarchy with H1 > H2 > H3 structure
- Placeholders marked as `[FILL: description]`

### Architecture Patterns

- **Multi-Agent System:** 4 specialized AI agents (Analyzer, Ranker, Rewriter, Indexer)
- **Output Style Pattern:** Uses Claude Code output styles for premium formatting
- **Skills Pattern:** Auto-triggered skills for competitive analysis, content scoring, schema generation
- **Validation Layer:** Ground truth via MCP servers (Brave Search, Chrome DevTools)
- **Subagents over Monolith:** Fresh context per task for better results

### Testing Strategy

- Test with sample URLs: `/geo:audit https://example.com`
- Test with local content: `/geo:optimize test.md`
- Validate outputs in `geo-output/` folder
- Use `validation-doctor` skill to verify MCP setup

### Git Workflow

- Main branch for stable releases
- Feature branches for new capabilities
- OpenSpec for change proposals before major changes
- Conventional commits preferred

## Domain Context

### The 10 GEO Features

Every optimization applies these research-based features:

1. **Ranking Emphasis** - Frame as best/top choice
2. **User Intent Alignment** - Address what users seek
3. **Competitive Differentiation** - Unique advantages
4. **Social Proof** - Reviews, testimonials, stats
5. **Compelling Narrative** - Persuasive language
6. **Authoritativeness** - Expert, confident tone
7. **Unique Selling Points** - Clear differentiators
8. **Urgency Signals** - Time/scarcity when appropriate
9. **Scannable Format** - Bullets, headings, structure
10. **Factual Accuracy** - No fabrications

### Agent Roles

| Agent | Role |
|-------|------|
| **geo-analyzer** | Extracts content, scores GEO signals, identifies gaps |
| **geo-ranker** | Simulates AI-engine ranking, predicts positions |
| **geo-rewriter** | Optimizes content while preserving brand voice |
| **geo-indexer** | Generates schema markup and technical assets |

### Output Structure

```
geo-output/
├── report.md           # Executive summary + scores
├── analysis.json       # Raw analysis data
├── optimized/          # Rewritten content files
│   └── [filename].md
├── schema/             # JSON-LD markup
│   └── [filename].json
└── checklist.md        # Implementation steps
```

## Important Constraints

- **Never fabricate statistics or testimonials** - preserve all factual claims
- **Always validate** - use Brave Search for competitor ground truth, Chrome DevTools for DOM
- **Low Confidence labeling** - if MCP servers unavailable, mark outputs as "Low Confidence"
- **Brand voice preservation** - optimize without losing original tone
- **Immediate usability** - all outputs must be copy-paste ready

## External Dependencies

| Dependency | Purpose | Criticality |
|------------|---------|-------------|
| `brave-search` MCP | Market validation (competitor analysis, SERP data) | 🔴 HIGH |
| `chrome-devtools` MCP | Technical validation (DOM/rendering, performance) | 🔴 HIGH |
| `fetch` | Simple text scraping (fallback) | 🟡 MEDIUM |
| `filesystem` | Batch process local files | 🟡 MEDIUM |

Use the `validation-doctor` skill to verify MCP setup and get configuration snippets.
