# E-GEO Claude Code System Blueprint

> **Zero-Effort GEO Optimization System for SaaS, B2B & B2C**  
> One command. Premium results. Indistinguishable from $100M MRR companies.

---

## 1. Product Vision

**Selling Point:** "Type one command, get AI-optimized content that ranks in ChatGPT, Perplexity, and AI search engines."

**Target Users:**
- SaaS founders wanting organic AI-engine traffic
- B2B marketers optimizing landing pages
- B2C e-commerce optimizing product descriptions
- Content creators maximizing AI discoverability

**Core Promise:** Transform any website content into GEO-optimized assets with a single Claude Code command.

---

## 2. System Architecture

```
.claude/
├── CLAUDE.md                    # Project-level memory & GEO context
├── output-styles/
│   └── geo-optimizer.md         # Main output style for GEO workflow
├── agents/
│   ├── analyzer.md              # Content analysis & gap detection
│   ├── rewriter.md              # GEO content optimization
│   ├── ranker.md                # Simulated ranking evaluation
│   └── indexer.md               # Schema markup & technical GEO
├── skills/
│   ├── competitive-analysis/
│   │   └── SKILL.md             # Analyze competitors in AI responses
│   ├── content-scoring/
│   │   └── SKILL.md             # Score content against GEO criteria
│   └── schema-generator/
│       └── SKILL.md             # Generate structured data markup
├── commands/
│   ├── geo-audit.md             # /geo:audit <url>
│   ├── geo-optimize.md          # /geo:optimize <file>
│   ├── geo-batch.md             # /geo:batch <folder>
│   └── geo-report.md            # /geo:report
└── settings.local.json          # Auto-approve safe commands

AGENTS.md                        # Standard agent guidance file
README.md                        # Premium onboarding experience
```

---

## 3. One-Command UX Flow

### Primary Command: `/geo`

```
User: /geo https://mysite.com/pricing

Claude orchestrates automatically:
1. [analyzer] → Scrapes & analyzes current content
2. [ranker]   → Simulates AI-engine ranking position
3. [rewriter] → Rewrites with GEO optimizations
4. [indexer]  → Generates schema markup
5. [reporter] → Outputs beautiful report + files
```

### Command Variations

| Command | Description |
|---------|-------------|
| `/geo <url>` | Full audit + optimization |
| `/geo:audit <url>` | Analysis only, no rewrites |
| `/geo:optimize <file>` | Optimize local content file |
| `/geo:batch <folder>` | Batch process folder of content |
| `/geo:report` | Generate comprehensive GEO report |
| `/geo:compete <url>` | Competitive analysis vs top AI results |

---

## 4. Subagents Design

### 4.1 Analyzer Agent
```yaml
name: geo-analyzer
description: Analyzes content for GEO gaps. Use when auditing URLs or files for AI-engine optimization opportunities.
tools: Read, Bash, WebFetch
model: sonnet
```

**System Prompt Core:**
- Extract page content via curl/fetch
- Identify missing GEO signals (USPs, social proof, user intent)
- Score against 10 universal GEO features
- Output structured JSON analysis

### 4.2 Rewriter Agent
```yaml
name: geo-rewriter
description: Rewrites content for maximum AI-engine ranking. Use after analysis to transform content.
tools: Read, Write
model: opus
```

**System Prompt Core:**
- Apply E-GEO research findings (competitive framing, authority, scannable format)
- Preserve brand voice while adding ranking signals
- Include quantifiable evidence and social proof
- Structure with bullet points and clear hierarchy

### 4.3 Ranker Agent
```yaml
name: geo-ranker
description: Simulates AI-engine ranking to evaluate content quality. Use to test before/after improvements.
tools: Read
model: sonnet
```

**System Prompt Core:**
- Simulate how AI engines perceive and rank content
- Compare against hypothetical competitors
- Return predicted ranking position and confidence
- Identify specific ranking weaknesses

### 4.4 Indexer Agent
```yaml
name: geo-indexer
description: Generates technical GEO assets (schema, metadata). Use after content optimization.
tools: Read, Write
model: haiku
```

**System Prompt Core:**
- Generate JSON-LD schema markup
- Create optimized meta descriptions
- Suggest internal linking opportunities
- Output copy-paste-ready code snippets

---

## 5. Skills Design

### 5.1 Competitive Analysis Skill
```markdown
---
name: competitive-analysis
description: Automatically analyze how competitors rank in AI responses. Triggers on phrases like "analyze competition", "what ranks for", "competitor analysis".
---
When analyzing competition:
1. Query simulated AI responses for the target topic
2. Identify top 3-5 results that would appear
3. Extract their GEO signals and patterns
4. Generate comparison matrix
5. Recommend differentiation strategies
```

### 5.2 Content Scoring Skill
```markdown
---
name: content-scoring
description: Score content against GEO criteria. Triggers on "score this", "rate content", "GEO score".
---
Score content against these 10 criteria (0-10 each):
1. Ranking emphasis
2. User intent alignment
3. Competitive differentiation
4. Social proof presence
5. Compelling narrative
6. Authoritativeness
7. Unique selling points
8. Urgency signals
9. Scannable format
10. Factual accuracy

Output: Overall score /100 + improvement priorities
```

### 5.3 Schema Generator Skill
```markdown
---
name: schema-generator
description: Generate structured data markup. Triggers on "schema", "structured data", "JSON-LD".
---
Generate appropriate schema types:
- Product → Product schema with offers, reviews
- Service → Service schema with provider, area
- Article → Article schema with author, dates
- FAQ → FAQPage schema for Q&A content
- Organization → Organization schema for about pages

Output: Copy-paste JSON-LD + integration instructions
```

---

## 6. Output Style: GEO Optimizer

```markdown
---
name: geo-optimizer
description: Transform Claude into a GEO specialist with structured outputs and automatic agent orchestration.
keep-coding-instructions: false
---

# GEO Optimizer Mode

You are an elite Generative Engine Optimization specialist. Your outputs follow this premium format:

## Response Structure

### For Audits
┌─────────────────────────────────────┐
│  🎯 GEO AUDIT REPORT                │
├─────────────────────────────────────┤
│  Score: XX/100                      │
│  Ranking Potential: ████████░░ 80%  │
├─────────────────────────────────────┤
│  ✅ Strengths                       │
│  • [identified strength]            │
│                                     │
│  ⚠️ Gaps                            │
│  • [identified gap with fix]        │
│                                     │
│  📈 Priority Actions                │
│  1. [highest impact action]         │
│  2. [second action]                 │
│  3. [third action]                  │
└─────────────────────────────────────┘

### For Optimizations
Output rewritten content with clear before/after sections.
Always include:
- GEO score improvement estimate
- Changed elements highlighted
- Schema markup if applicable

## Automatic Delegation
- Analysis requests → delegate to geo-analyzer
- Rewrites → delegate to geo-rewriter  
- Ranking checks → delegate to geo-ranker
- Technical assets → delegate to geo-indexer
```

---

## 7. AGENTS.md Compatibility

```markdown
# AGENTS.md

## Project: E-GEO (Generative Engine Optimization)

This project optimizes website content for AI-powered search engines (ChatGPT, Perplexity, Claude, Gemini).

## Setup Commands
- No setup required. Claude Code handles everything.
- Optional: Set ANTHROPIC_API_KEY for external agent compatibility

## Code Style
- Markdown for all content files
- JSON-LD for schema markup
- YAML frontmatter for metadata

## Agent Instructions

### When optimizing content:
1. Always analyze before rewriting
2. Preserve brand voice and factual accuracy
3. Apply the 10 GEO universal features
4. Generate schema markup for all pages
5. Provide before/after comparison

### Key GEO Features to Apply:
- Ranking emphasis (frame as best choice)
- User intent alignment (address what users seek)
- Competitive differentiation (unique advantages)
- Social proof (reviews, testimonials, stats)
- Authoritativeness (confident expert tone)
- Scannable format (bullets, headings)

### Files to Generate:
- `geo-report.md` - Analysis summary
- `optimized/` - Rewritten content files
- `schema/` - JSON-LD markup files
```

---

## 8. MCP Integration

Leverage these MCP servers for enhanced capabilities:

| MCP Server | Use Case |
|------------|----------|
| `fetch` | Scrape URLs for analysis |
| `filesystem` | Batch process local files |
| `brave-search` | Competitive research |
| `puppeteer` | Full page rendering |

---

## 9. Premium UX Elements

### Onboarding Experience
```
Welcome to E-GEO ✨

The zero-effort way to rank in AI search engines.

Quick Start:
  /geo https://yoursite.com/page

That's it. I'll analyze, optimize, and deliver.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need help? Try:
  /geo:help     - Full command reference
  /geo:example  - See sample optimization
```

### Progress Indicators
```
🔍 Analyzing content...
   ├── Extracting page content
   ├── Scoring GEO signals
   └── Identifying gaps

✍️ Optimizing...
   ├── Applying GEO features
   ├── Preserving brand voice
   └── Generating schema

📊 Generating report...
   └── Done! See geo-report.md
```

### Report Format
Premium PDF-ready markdown with:
- Executive summary
- Score visualizations (ASCII progress bars)
- Before/after comparisons
- Copy-paste code snippets
- Priority action list

---

## 10. File Deliverables

After running `/geo`:

```
geo-output/
├── report.md           # Executive summary + scores
├── analysis.json       # Raw analysis data
├── optimized/
│   └── [filename].md   # Rewritten content
├── schema/
│   └── [filename].json # JSON-LD markup
└── checklist.md        # Implementation checklist
```

---

## 11. Implementation Phases

### Phase 1: Core System (MVP)
- [ ] CLAUDE.md with GEO context
- [ ] geo-optimizer output style
- [ ] 4 core subagents
- [ ] `/geo` slash command
- [ ] AGENTS.md compatibility

### Phase 2: Skills & Polish
- [ ] 3 auto-triggered skills
- [ ] Premium report templates
- [ ] Batch processing
- [ ] MCP integrations

### Phase 3: Gumroad Ready
- [ ] README with premium onboarding
- [ ] Video-ready demo flow
- [ ] One-click installation script
- [ ] Example outputs for sales page

---

## 12. Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Output Style over full persona | Keeps coding tools available |
| Sonnet for analysis, Opus for rewrites | Cost/quality balance |
| Subagents over monolith | Fresh context per task |
| Skills for auto-triggers | Zero-effort UX |
| Markdown outputs | Universal compatibility |

---

## 13. Pricing Position (Gumroad)

**E-GEO Pro Pack**
- $49 one-time
- Unlimited use
- All agents + skills
- Premium report templates
- Lifetime updates

**Selling Points:**
- "One command optimization"
- "Based on published research"
- "Works with any Claude Code project"
- "Premium outputs from day one"

---

## 14. Next Steps

1. ✅ Blueprint complete
2. → Create `.claude/` folder structure
3. → Write CLAUDE.md with GEO knowledge base
4. → Implement subagents (analyzer, rewriter, ranker, indexer)
5. → Create geo-optimizer output style
6. → Add slash commands
7. → Write AGENTS.md
8. → Test full flow
9. → Polish README for Gumroad

---

*Blueprint v1.0 | Ready for implementation*
