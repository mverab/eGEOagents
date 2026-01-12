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

1. **Analyze** - Extract and score current content
2. **Rank** - Simulate baseline AI-engine ranking
3. **Rewrite** - Optimize content with GEO features
4. **Index** - Generate schema markup
5. **Report** - Compile comprehensive results

## Execution

```
Analyzing: $ARGUMENTS.target

Step 1/5: Content Analysis
→ Delegating to geo-analyzer...

Step 2/5: Ranking Simulation  
→ Delegating to geo-ranker...

Step 3/5: Content Optimization
→ Delegating to geo-rewriter...

Step 4/5: Schema Generation
→ Delegating to geo-indexer...

Step 5/5: Report Compilation
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
