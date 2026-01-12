---
name: geo:report
description: Generate a comprehensive GEO report from previous analysis
arguments: []
---

# /geo:report Command

Compile a premium PDF-ready report from analysis data.

## Workflow

1. **Gather** - Collect data from `geo-output/`
2. **Compile** - Create executive summary
3. **Format** - Apply premium formatting
4. **Save** - Output final report

## Output

`geo-output/report.md` containing:

```markdown
# GEO Optimization Report
Generated: [date]

## Executive Summary
- Overall Score: XX/100
- Estimated Ranking Improvement: +X positions
- Priority Actions: X items

## Score Breakdown
[Visual breakdown of all criteria]

## Content Analysis
[Detailed findings]

## Optimized Content
[Before/after comparisons]

## Technical Assets
[Schema markup, meta tags]

## Implementation Checklist
[Step-by-step action items]

## Appendix
[Raw data, methodology]
```

## Example Usage

```
/geo:report
```
