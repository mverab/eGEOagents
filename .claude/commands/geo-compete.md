---
name: geo:compete
description: Analyze competitive landscape for a query or topic
arguments:
  - name: query
    description: Search query or topic to analyze
    required: true
---

# /geo:compete Command

Competitive analysis for AI-engine rankings.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Query Analysis** - Understand user intent
2. **Competitor Discovery** - Use Brave results when available; otherwise fallback to best-effort (Low Confidence)
3. **Gap Analysis** - Identify differentiation opportunities
4. **Strategy** - Recommend positioning

## Output

Competitive analysis report:
- Top results for query (Brave-backed; otherwise **Low Confidence**)
- Strengths/weaknesses of each
- Your positioning opportunities
- Specific differentiation strategies

## Example Usage

```
/geo:compete "best project management software"
/geo:compete "how to automate invoicing"
/geo:compete "enterprise data analytics platform"
```
