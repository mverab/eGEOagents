---
name: geo:audit
description: Analyze content for GEO optimization opportunities without making changes
arguments:
  - name: target
    description: URL or file path to audit
    required: true
---

# /geo:audit Command

Analysis-only mode. Scores content and identifies gaps without rewriting.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Extract** - Get content from URL or file (source of truth)
2. **Score** - Rate against 10 GEO criteria based on analyzer output
3. **Rank** - Estimate AI-engine position based on analyzer output (Brave if available)
4. **Report** - Output findings and recommendations

## Output

Detailed audit report including:
- Overall GEO score (0-100)
- Individual criterion scores
- Identified strengths
- Gap analysis with specific fixes
- Priority action list
- Competitive positioning estimate (Brave-backed; otherwise **Low Confidence**)

## Example Usage

```
/geo:audit https://mysite.com/about
/geo:audit ./pages/services.md
```
