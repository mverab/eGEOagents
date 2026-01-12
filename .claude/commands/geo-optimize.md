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

1. **Read** - Load file content
2. **Rewrite** - Apply GEO optimization
3. **Schema** - Generate appropriate markup
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
