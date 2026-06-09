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
1. **Frontmatter Extraction** - If the target is a local file containing frontmatter (YAML/TOML blocks), extract and preserve it completely unchanged. Only pass the remaining body content to the analyzer and rewriter.
2. **Analyze** - Extract and score current content body (source of truth)
3. **Rank** - Simulate baseline AI-engine ranking based on analyzer output
4. **Rewrite** - Optimize content using analyzer findings. If the target was a local file with frontmatter, prepend the original unmodified frontmatter block to the optimized content body when saving.
5. **Index** - Generate schema markup using analyzer findings
6. **Report** - Compile results using analyzer output + validation status

## Execution

```
Analyzing: $ARGUMENTS.target

Step 0/7: MCP Validation
→ Running validation-doctor...

Step 1/7: Frontmatter Extraction
→ Extracting and preserving frontmatter if present...

Step 2/7: Content Analysis
→ Delegating to geo-analyzer...

Step 3/7: Ranking Simulation
→ Delegating to geo-ranker...

Step 4/7: Content Optimization
→ Delegating to geo-rewriter...

Step 5/7: Schema Generation
→ Delegating to geo-indexer...

Step 6/7: Report Compilation
→ Generating final report...
```

## Output

Save results to `geo-output/` folder:
- `report.md` - Executive summary with scores
- `analysis.json` - Raw analysis data
- `optimized/[name].[ext]` - Rewritten content (`.md` or `.html` depending on format)
- `schema/[name].json` - JSON-LD markup
- `checklist.md` - Implementation steps

## Example Usage

```
/geo https://mysite.com/pricing
/geo ./content/landing-page.md
/geo https://competitor.com/product (analyze only, suggest how to beat)
```
