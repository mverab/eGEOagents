# AGENTS.md

## Project: E-GEO (Generative Engine Optimization)

A zero-effort system to optimize website content for AI-powered search engines (ChatGPT, Perplexity, Claude, Gemini).

## Quick Start

```bash
/geo https://yoursite.com/page
```

That's it. The system handles everything automatically.

## Available Commands

| Command | Description |
|---------|-------------|
| `/geo <url>` | Full optimization pipeline |
| `/geo:audit <url>` | Analysis only |
| `/geo:optimize <file>` | Optimize local file |
| `/geo:batch <folder>` | Process multiple files |
| `/geo:report` | Generate summary report |
| `/geo:compete <query>` | Competitive analysis |

## Code Style

- Markdown for all content files
- JSON-LD for schema markup
- YAML frontmatter for metadata

## MCP Requirements

For **fully validated** results (ground truth competitors + rendered DOM), use these MCP servers. If they're missing, the system should still run but must mark outputs as **Low Confidence**.

| Server | Purpose | Criticality |
|--------|---------|-------------|
| `brave-search` | Market validation (competitor analysis) | 🔴 HIGH |
| `chrome-devtools` | Technical validation (DOM/rendering) | 🔴 HIGH |

Use the `validation-doctor` skill to check or install these dependencies.

## Agent Instructions

### When Optimizing Content

1. **VALIDATE ALWAYS:** Use `brave-search` for competitor ground truth and `chrome-devtools` for rendered DOM when available.
   - If missing, validate with available tools (e.g., `fetch`/raw HTML) and clearly label outputs as **Low Confidence**.
   - Do not claim competitor rankings without Brave data.
2. Always analyze before rewriting
3. Preserve brand voice and factual accuracy
4. Apply the 10 GEO universal features
5. Generate schema markup for all pages
6. Provide before/after comparison

### The 10 GEO Features

Every optimization should incorporate:

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

### Output Files

Generate these in `geo-output/`:

```
geo-output/
├── report.md           # Executive summary
├── analysis.json       # Raw analysis data
├── optimized/          # Rewritten content files
│   └── [filename].md
├── schema/             # JSON-LD markup
│   └── [filename].json
└── checklist.md        # Implementation steps
```

### Quality Standards

- Every output must be immediately usable
- Include specific scores and metrics
- Provide copy-paste ready content
- Mark placeholders clearly: `[FILL: description]`

## Security

- Never fabricate statistics or testimonials
- Preserve all factual claims from original content
- Flag uncertain information for human review

## Testing

To verify the system works:

```bash
# Test with a sample URL
/geo:audit https://example.com

# Test with local content
echo "# My Product\nA great product." > test.md
/geo:optimize test.md
```
