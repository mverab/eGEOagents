# E-GEO: Generative Engine Optimization System

You are operating the E-GEO system—a zero-effort GEO optimization toolkit for SaaS, B2B, and B2C websites.

## Core Knowledge

### What is GEO?
Generative Engine Optimization (GEO) is the practice of optimizing content to rank higher in AI-powered search engines like ChatGPT, Perplexity, Claude, and Gemini. Unlike traditional SEO, GEO focuses on how LLMs perceive, understand, and recommend content.

### The 10 Universal GEO Features
Based on E-GEO research, these features consistently improve AI-engine rankings:

1. **Ranking Emphasis** - Frame content as the best/top choice
2. **User Intent Alignment** - Directly address what users are looking for
3. **Competitive Differentiation** - Highlight unique advantages vs alternatives
4. **Social Proof** - Include reviews, testimonials, stats, ratings
5. **Compelling Narrative** - Use persuasive, engaging language
6. **Authoritativeness** - Confident, expert tone
7. **Unique Selling Points** - What makes this different
8. **Urgency Signals** - Scarcity or time-sensitivity when appropriate
9. **Scannable Format** - Headings, bullets, clear structure
10. **Factual Accuracy** - Never fabricate; LLMs penalize inaccuracies

### Key Research Findings
- Heuristics alone don't work—optimization beats all 15 common tactics
- "Competitive" framing has highest initial impact (+0.71 rank improvement)
- Optimized prompts converge to similar patterns regardless of starting point
- One universal strategy exists for effective GEO

## System Commands

| Command | Action |
|---------|--------|
| `/geo <url>` | Full audit + optimization of URL |
| `/geo:audit <url>` | Analysis only, no rewrites |
| `/geo:optimize <file>` | Optimize local content file |
| `/geo:batch <folder>` | Process all files in folder |
| `/geo:report` | Generate comprehensive report |
| `/geo:compete <query>` | Competitive analysis for query |
| `/geo:loop [domain]` | One bounded loop-mode iteration over a workspace domain |

## Workflow

When user runs `/geo`:
1. Delegate to **geo-analyzer** for content extraction and gap analysis
2. Delegate to **geo-ranker** for baseline ranking simulation
3. Delegate to **geo-rewriter** for content optimization
4. Delegate to **geo-indexer** for schema markup generation
5. Compile final report with before/after comparison

## Loop Mode

Loop mode is **opt-in** and additive. One-shot behavior (`/geo`, `/geo:audit`,
`/geo:optimize`, `/geo:batch`, `/geo:report`, `/geo:compete`, the `geo-*` agents,
`egeo optimize`, and the `geo-output/` convention) is unchanged and never
requires a workspace.

When the user runs `/geo:loop`:
1. Follow `.claude/skills/geo-loop/SKILL.md` — it is the authoritative procedure.
2. All state lives in `$EGEO_HOME` (default `~/.egeo/`). **Never write loop
   state into the repo tree** — not `prompts/`, not `geo-output/`.
3. `egeo loop run <domain> --dry-run` prints the plan (focus, collector deltas,
   candidate signals) and writes nothing. Start there.
4. Do **one** unit of work, then close the run: exactly one
   `### YYYY-MM-DD run` Timeline entry ending in
   `Outcome: success|partial|failure|no-op`, and exactly one `LOG.md` line.
5. Artifacts follow `SUBSTRATE.md`: `signals/` for evidence (deduped via
   `frequency`), `docs/` for durable knowledge, frontmatter on line 1, sources
   cited. Verify with `python -m egeo.substrate_lint` before exiting.
6. Ground truth comes from `$EGEO_HOME/data/*.jsonl` written by the collectors
   (`egeo loop collect serp|page`). A simulated ranking is `confidence: low`.

## Output Standards

Always produce premium, actionable outputs:
- Use visual formatting (boxes, progress bars, tables)
- Include specific scores and metrics
- Provide copy-paste ready content
- Generate implementation checklists

## File Output Structure

```
geo-output/
├── report.md           # Executive summary
├── analysis.json       # Raw data
├── optimized/          # Rewritten content
├── schema/             # JSON-LD files
└── checklist.md        # Action items
```
