---
name: geo:optimize
description: Optimize a local content file for GEO without full audit
arguments:
  - name: file
    description: Path to content file to optimize
    required: true
---

# /geo:optimize Command

Quick optimization of local content files.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Analyze** - Read and score file content (source of truth)
2. **Rewrite** - Apply GEO optimization based on analyzer output
3. **Schema** - Generate appropriate markup based on analyzer output
4. **Save** - Output optimized version

## Output

- Optimized content with before/after comparison
- Schema markup if applicable
- Change summary with impact estimates

## Example Usage

```
/geo:optimize ./content/homepage.md
/geo:optimize ./blog/new-post.md
```
