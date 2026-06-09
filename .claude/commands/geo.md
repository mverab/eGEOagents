---
name: geo
description: Full GEO optimization pipeline - analyze, rank, rewrite, and generate schema for any URL or content
arguments:
  - name: target
    description: URL to optimize or path to local file
    required: true
---

# /geo Command

Execute full GEO optimization pipeline.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Frontmatter Detection** - If the target is a local file containing frontmatter (YAML/TOML blocks), extract and preserve it completely unchanged. Only pass the remaining body content to the analyzer and rewriter.
2. **Analyze** - Extract and score current content body (source of truth)
3. **Rank** - Simulate baseline AI-engine ranking based on analyzer output
4. **Rewrite** - Optimize content using analyzer findings. If the target was a local file with frontmatter, prepend the original unmodified frontmatter block to the optimized content body when saving.
5. **Index** - Generate schema markup using analyzer findings
6. **Report** - Compile results using analyzer output + validation status

## Execution

```
Analyzing: $ARGUMENTS.target

Step 0/6: MCP Validation
→ Running validation-doctor...

Step 1/6: Content Analysis
→ Delegating to geo-analyzer...

Step 2/6: Ranking Simulation  
→ Delegating to geo-ranker...

Step 3/6: Content Optimization
→ Delegating to geo-rewriter...

Step 4/6: Schema Generation
→ Delegating to geo-indexer...

Step 5/6: Report Compilation
→ Generating final report...
```

## Output

Save results to `geo-output/` folder:
- `report.md` - Executive summary with scores
- `analysis.json` - Raw analysis data
- `optimized/[name].md` - Rewritten content
- `schema/[name].json` - JSON-LD markup
- `checklist.md` - Implementation steps

## Example Usage

```
/geo https://mysite.com/pricing
/geo ./content/landing-page.md
/geo https://competitor.com/product (analyze only, suggest how to beat)
```
